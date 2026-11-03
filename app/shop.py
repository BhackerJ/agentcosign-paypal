"""Loopback-only test merchant. Server-owned carts/quotes; no payment endpoints."""
import copy
import hashlib
import html
import json
import secrets
import sqlite3
import threading
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluate import evaluate, evaluate_policy

CATALOG = Path(__file__).with_name('catalog.json')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


class Refused(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


class Store:
    def __init__(self, path, clock=time.time, quote_lifetime_seconds=300):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        self.clock = clock
        self.quote_lifetime_seconds = quote_lifetime_seconds
        self.payments = None
        self.catalog = json.loads(CATALOG.read_text())
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS carts (
          task_id TEXT PRIMARY KEY, visit_id TEXT UNIQUE, cart_id TEXT UNIQUE,
          visit_hash TEXT UNIQUE, visit_expires REAL, session_hash TEXT UNIQUE,
          session_expires REAL, csrf TEXT, intent TEXT, items TEXT,
          version INTEGER, state TEXT, quote TEXT, runner_status TEXT);
        CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY, task_id TEXT, event TEXT, data TEXT);
        CREATE TABLE IF NOT EXISTS buyers (
          task_id TEXT PRIMARY KEY REFERENCES carts(task_id), buyer_id TEXT UNIQUE,
          entry_hash TEXT UNIQUE, entry_expires REAL, session_hash TEXT UNIQUE,
          session_expires REAL, csrf TEXT);
        CREATE TABLE IF NOT EXISTS approvals (
          approval_id TEXT PRIMARY KEY, task_id TEXT, buyer_id TEXT, quote_id TEXT UNIQUE,
          quote_sha256 TEXT, cart_version INTEGER, intent_sha256 TEXT,
          merchant_id TEXT, currency TEXT, total_cents INTEGER,
          created_at REAL, expires_at REAL, status TEXT);
        ''')

    def create(self):
        task, visit, cart = (secrets.token_hex(12) for _ in range(3))
        token = secrets.token_urlsafe(24)
        intent = {'source_case_id': 'walking-width', 'required_width': 'extra_wide',
                  'required_size': '10.5', 'quantity': 1, 'budget_cents': 15000,
                  'allowed_categories': ['footwear'], 'merchant_id': self.catalog['merchant_id'],
                  'currency': 'USD', 'evidence_type': 'new_derived_integration_fixture'}
        with self.lock, self.db:
            self.db.execute('INSERT INTO carts VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                            (task, visit, cart, token_hash(token), self.clock()+600, None, None, None,
                             json.dumps(intent), '{}', 0, 'shopping', None, 'not_started'))
        return {'task_id': task, 'visit_id': visit, 'cart_id': cart, 'visit_token': token}

    def exchange(self, token):
        with self.lock, self.db:
            row = self.db.execute('SELECT * FROM carts WHERE visit_hash=?', (token_hash(token),)).fetchone()
            if not row or row['visit_expires'] <= self.clock():
                raise Refused(403, 'Visit token invalid, expired, or consumed')
            session, csrf = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
            self.db.execute('UPDATE carts SET visit_hash=NULL, session_hash=?,session_expires=?,csrf=? WHERE task_id=?',
                            (token_hash(session), self.clock()+1200, csrf, row['task_id']))
            self.audit(row['task_id'], 'visit_exchanged', {})
            return session

    def session(self, token):
        with self.lock:
            row = self.db.execute('SELECT * FROM carts WHERE session_hash=?', (token_hash(token),)).fetchone()
            if not row or row['session_expires'] <= self.clock():
                raise Refused(403, 'Shopper session required')
            return dict(row)

    def audit(self, task, event, data):
        self.db.execute('INSERT INTO audit(task_id,event,data) VALUES (?,?,?)', (task, event, json.dumps(data)))

    def mutate(self, session, csrf, sku, quantity):
        with self.lock, self.db:
            row = self.session(session)
            if not secrets.compare_digest(csrf, row['csrf']):
                raise Refused(403, 'Invalid form token')
            if row['state'] != 'shopping':
                raise Refused(409, 'Cart frozen; buyer must reopen for changes')
            if sku not in self.catalog['products'] or not isinstance(quantity, int) or not 0 <= quantity <= 5:
                raise Refused(400, 'Invalid product or quantity')
            if not self.catalog['products'][sku]['available']:
                raise Refused(409, 'Unavailable')
            items = json.loads(row['items'])
            if quantity:
                items[sku] = quantity
            else:
                items.pop(sku, None)
            if items != json.loads(row['items']):
                self.db.execute('UPDATE carts SET items=?,version=version+1,quote=NULL WHERE task_id=?',
                                (json.dumps(items), row['task_id']))
                self.audit(row['task_id'], 'cart_changed', {'sku': sku, 'quantity': quantity, 'version': row['version']+1})

    def snapshot(self, task):
        with self.lock:
            row = self.db.execute('SELECT * FROM carts WHERE task_id=?', (task,)).fetchone()
            if not row:
                raise Refused(404, 'Unknown task')
            return {**{k: row[k] for k in ('task_id', 'visit_id', 'cart_id', 'version', 'state', 'runner_status')},
                    'intent': json.loads(row['intent']), 'items': json.loads(row['items']),
                    'quote': json.loads(row['quote']) if row['quote'] else None}

    def runner_finished(self, task, status):
        with self.lock, self.db:
            self.db.execute('UPDATE carts SET runner_status=? WHERE task_id=?', (status, task))
            self.audit(task, 'runner_finished', {'status': status})

    def freeze(self, task):
        with self.lock, self.db:
            state = self.snapshot(task)
            if state['quote']:
                if state['quote']['expires_at'] <= self.clock():
                    raise Refused(409, 'Quote expired; reopen explicitly')
                return state['quote']
            if state['runner_status'] != 'done':
                raise Refused(409, 'Human recovery required before review')
            if not state['items']:
                raise Refused(409, 'Empty cart, regardless of agent report')
            lines = [{'sku': sku, 'quantity': qty, **copy.deepcopy(self.catalog['products'][sku])}
                     for sku, qty in sorted(state['items'].items())]
            subtotal = sum(line['price_cents'] * line['quantity'] for line in lines)
            tax = (subtotal * self.catalog['tax_basis_points'] + 5000) // 10000
            quote = {'quote_id': secrets.token_hex(12), 'task_id': task, 'visit_id': state['visit_id'],
                     'cart_id': state['cart_id'], 'cart_version': state['version'],
                     'candidate_snapshot_id': secrets.token_hex(12),
                     'merchant_id': self.catalog['merchant_id'], 'currency': self.catalog['currency'],
                     'catalog_sha256': digest(self.catalog), 'intent_sha256': digest(state['intent']),
                     'lines': lines, 'subtotal_cents': subtotal, 'discount_cents': 0,
                     'shipping_cents': self.catalog['shipping_cents'], 'tax_cents': tax,
                     'total_cents': subtotal + self.catalog['shipping_cents'] + tax,
                     'expires_at': self.clock()+self.quote_lifetime_seconds, 'evidence_type': 'new_derived_integration_fixture'}
            if self.payments:
                quote['paypal_merchant_id'] = self.payments.config['PAYPAL_MERCHANT_ID']
            quote['sha256'] = digest(quote)
            self.db.execute('UPDATE carts SET state=?,quote=? WHERE task_id=?', ('frozen', json.dumps(quote), task))
            self.audit(task, 'quote_frozen', {'quote_id': quote['quote_id'], 'cart_version': state['version']})
            return quote

    def reopen(self, task):
        """Operator-only recovery in this local harness; no shopper HTTP route."""
        with self.lock, self.db:
            if self.payments:
                self.payments.change_guard(task)
            self.db.execute("UPDATE approvals SET status='invalidated' WHERE task_id=? AND status='approved'", (task,))
            self.db.execute('UPDATE carts SET state=?,quote=NULL,version=version+1,runner_status=? WHERE task_id=?',
                            ('shopping', 'not_started', task))
            self.audit(task, 'operator_reopened', {})

    def facts(self, task, quote):
        with self.lock:
            state = self.snapshot(task)
            intent = state['intent']
            if (not state['quote'] or state['quote'] != quote or quote['expires_at'] <= self.clock()
                    or quote['sha256'] != digest({k: v for k, v in quote.items() if k != 'sha256'})
                    or quote['cart_version'] != state['version'] or quote['catalog_sha256'] != digest(self.catalog)
                    or quote['intent_sha256'] != digest(intent) or quote['merchant_id'] != intent['merchant_id']
                    or quote['currency'] != intent['currency']):
                raise Refused(409, 'Quote stale or inconsistent')
            shoes = [line for line in quote['lines'] if line['category'] == 'footwear']
            constraints = [
                {'operator': 'eq', 'key': 'shoe_quantity', 'required': intent['quantity'], 'observed': sum(x['quantity'] for x in shoes)},
                {'operator': 'subset', 'key': 'item_scope', 'required': intent['allowed_categories'], 'observed': [x['category'] for x in quote['lines']]},
            ]
            for line in shoes:
                requirements = intent.get('requirements', {'size': intent['required_size'], 'width': intent['required_width'], 'unit': 'pair'})
                constraints += [{'operator': 'lte' if field == 'delivery_within_days' else 'eq', 'key': field, 'required': value, 'observed': line.get(field)}
                                for field, value in requirements.items()]
            constraints += [{'operator': 'eq', 'key': 'availability', 'required': True, 'observed': line['available']}
                            for line in quote['lines']]
            return {'budget': {'observed_cents': quote['total_cents'], 'limit_cents': intent['budget_cents'],
                               'basis': 'all_in', 'limit_basis': 'all_in', 'currency': 'USD'},
                    'constraints': constraints, 'quote_complete': True, 'buyer_approval_verified': False}

    def assessment(self, task, quote):
        with self.lock:
            facts = self.facts(task, quote)
            approval = self.approval_for(task, quote)
            facts['buyer_approval_verified'] = approval is not None
            return {'budget_only_quote_policy': evaluate_policy(facts, False),
                    'intent_aware_quote_policy': evaluate_policy(facts, True),
                    'actual_authorization_gate': evaluate(facts, True),
                    'buyer_approval': 'app_approved' if approval else 'not_requested_or_granted',
                    'paypal_approval': 'not_started', 'payment_calls': 0}

    def buyer_access(self, task):
        """Issue one-use owner access via the trusted operator, never to the shopper."""
        with self.lock, self.db:
            self.snapshot(task)
            token = secrets.token_urlsafe(24)
            row = self.db.execute('SELECT buyer_id FROM buyers WHERE task_id=?', (task,)).fetchone()
            if row:
                self.db.execute('UPDATE buyers SET entry_hash=?,entry_expires=?,session_hash=NULL,session_expires=NULL,csrf=NULL WHERE task_id=?',
                                (token_hash(token), self.clock()+600, task))
            else:
                self.db.execute('INSERT INTO buyers VALUES (?,?,?,?,?,?,?)',
                                (task, secrets.token_hex(12), token_hash(token), self.clock()+600, None, None, None))
            return token

    def buyer_exchange(self, token):
        with self.lock, self.db:
            row = self.db.execute('SELECT * FROM buyers WHERE entry_hash=?', (token_hash(token),)).fetchone()
            if not row or row['entry_expires'] <= self.clock():
                raise Refused(403, 'Buyer access invalid, expired, or consumed')
            session = secrets.token_urlsafe(24)
            self.db.execute('UPDATE buyers SET entry_hash=NULL,session_hash=?,session_expires=?,csrf=? WHERE task_id=?',
                            (token_hash(session), self.clock()+1200, secrets.token_urlsafe(24), row['task_id']))
            self.audit(row['task_id'], 'buyer_session_started', {})
            return session

    def buyer_session(self, token):
        with self.lock:
            row = self.db.execute('SELECT * FROM buyers WHERE session_hash=?', (token_hash(token),)).fetchone()
            if not row or row['session_expires'] <= self.clock():
                raise Refused(403, 'Independent buyer session required')
            return dict(row)

    def approval_for(self, task, quote):
        """Return a currently valid app approval; PayPal approval is separate."""
        with self.lock:
            self.facts(task, quote)
            row = self.db.execute('SELECT * FROM approvals WHERE task_id=? AND quote_id=?', (task, quote['quote_id'])).fetchone()
            buyer = self.db.execute('SELECT buyer_id FROM buyers WHERE task_id=?', (task,)).fetchone()
            if (not row or not buyer or row['buyer_id'] != buyer['buyer_id'] or row['status'] != 'approved'
                    or row['expires_at'] <= self.clock()):
                return None
            bindings = {'quote_sha256': quote['sha256'], 'cart_version': quote['cart_version'],
                        'intent_sha256': quote['intent_sha256'], 'merchant_id': quote['merchant_id'],
                        'currency': quote['currency'], 'total_cents': quote['total_cents']}
            if any(row[key] != value for key, value in bindings.items()):
                return None
            return dict(row)

    def buyer_decide(self, session, csrf, quote_id, quote_hash, decision):
        with self.lock, self.db:
            buyer = self.buyer_session(session)
            if self.payments:
                self.payments.change_guard(buyer['task_id'])
            if not secrets.compare_digest(csrf, buyer['csrf']):
                raise Refused(403, 'Invalid buyer form token')
            if decision not in ('approve', 'decline'):
                raise Refused(400, 'Unknown decision')
            state = self.snapshot(buyer['task_id'])
            if state['intent'].get('sources'):
                from profile_intent import require
                require(self, buyer['task_id'])
            quote = state['quote']
            if not quote or quote['quote_id'] != quote_id or quote['sha256'] != quote_hash:
                raise Refused(409, 'Quote changed. Review the current quotation before approving.')
            facts = self.facts(buyer['task_id'], quote)
            if decision == 'approve' and evaluate_policy(facts, True)['gate'] != 'allow':
                raise Refused(409, 'Purchase requirements not satisfied; approval refused')
            previous = self.db.execute('SELECT * FROM approvals WHERE quote_id=?', (quote_id,)).fetchone()
            if previous:
                if previous['buyer_id'] != buyer['buyer_id']:
                    raise Refused(403, 'Different buyer')
                if decision == 'decline':
                    self.db.execute("UPDATE approvals SET status='declined' WHERE quote_id=?", (quote_id,))
                    self.audit(buyer['task_id'], 'buyer_declined', {'quote_id': quote_id})
                elif previous['status'] != 'approved':
                    raise Refused(409, 'This quotation was declined or invalidated; request a new quotation')
                elif self.approval_for(buyer['task_id'], quote) is None:
                    raise Refused(409, 'Saved approval no longer matches this quotation')
                return dict(self.db.execute('SELECT * FROM approvals WHERE quote_id=?', (quote_id,)).fetchone())
            approval_id = secrets.token_hex(12)
            self.db.execute('INSERT INTO approvals VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                            (approval_id, buyer['task_id'], buyer['buyer_id'], quote_id, quote_hash,
                             quote['cart_version'], quote['intent_sha256'], quote['merchant_id'], quote['currency'],
                             quote['total_cents'], self.clock(), quote['expires_at'],
                             'approved' if decision == 'approve' else 'declined'))
            self.audit(buyer['task_id'], 'buyer_'+('approved' if decision == 'approve' else 'declined'),
                       {'approval_id': approval_id, 'quote_id': quote_id})
            return dict(self.db.execute('SELECT * FROM approvals WHERE approval_id=?', (approval_id,)).fetchone())

    def buyer_refresh(self, session, csrf, quote_id, quote_hash):
        """Explicitly replace a quotation without reusing any old approval."""
        with self.lock, self.db:
            buyer = self.buyer_session(session)
            if self.payments:
                self.payments.change_guard(buyer['task_id'])
            if not secrets.compare_digest(csrf, buyer['csrf']):
                raise Refused(403, 'Invalid buyer form token')
            state = self.snapshot(buyer['task_id'])
            if (not state['quote'] or state['quote']['quote_id'] != quote_id
                    or state['quote']['sha256'] != quote_hash or state['state'] != 'frozen'
                    or state['runner_status'] != 'done'):
                raise Refused(409, 'Cart changed; wait for completed shopping before requesting a quotation')
            self.db.execute("UPDATE approvals SET status='invalidated' WHERE task_id=? AND status='approved'", (buyer['task_id'],))
            self.db.execute('UPDATE carts SET quote=NULL WHERE task_id=?', (buyer['task_id'],))
            self.audit(buyer['task_id'], 'buyer_requested_new_quote', {'previous_quote_id': quote_id})
            return self.freeze(buyer['task_id'])


def serve(store, port=0):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Visit capabilities and cookies must not enter access logs.

        def reply(self, status, body='', headers=None):
            self.send_response(status)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            # Chrome sends Origin:null on form POSTs from no-referrer documents.
            # Only the token exchange needs that policy; ordinary same-origin forms do not.
            self.send_header('Referrer-Policy', 'no-referrer' if self.path.startswith(('/visit/', '/buyer/enter/')) else 'same-origin')
            payment_origin = ' https://www.sandbox.paypal.com https://sandbox.paypal.com' if store.payments else ''
            self.send_header('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'"+payment_origin+"; frame-ancestors 'none'")
            for key, value in (headers or {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body.encode())

        def cookie(self, name='shopper'):
            cookies = SimpleCookie(self.headers.get('Cookie', ''))
            return cookies[name].value if name in cookies else ''

        def do_GET(self):
            try:
                path = urlsplit(self.path).path
                if path in ('/buyer/paypal-return', '/buyer/paypal-cancel'):
                    self.reply(200, '<h1>Return to your buyer review</h1><p>The return URL does not prove approval or payment. Check the recorded status in your buyer review.</p><a href="/buyer/review">Open buyer review and check PayPal status</a>')
                    return
                if path.startswith('/buyer/enter/'):
                    session = store.buyer_exchange(path.removeprefix('/buyer/enter/'))
                    self.reply(303, headers={'Location': '/buyer/review', 'Set-Cookie': f'buyer={session}; HttpOnly; SameSite=Strict; Path=/buyer'})
                    return
                if path == '/buyer/review':
                    from buyer_view import render_review
                    buyer = store.buyer_session(self.cookie('buyer'))
                    self.reply(200, render_review(store, buyer))
                    return
                if path.startswith('/visit/'):
                    session = store.exchange(path.removeprefix('/visit/'))
                    self.reply(303, headers={'Location': '/shop', 'Set-Cookie': f'shopper={session}; HttpOnly; SameSite=Strict; Path=/'})
                    return
                if path not in ('/shop', '/cart'):
                    raise Refused(404, 'No such route. No checkout or payment routes exist.')
                row = store.session(self.cookie())
                items = json.loads(row['items'])
                esc = html.escape
                body = '<h1>AgentCoSign Test Shop</h1><p>NEW DERIVED TEST FIXTURE. No real products, orders or payments.</p>'
                body += '<nav><a href="/shop">Products</a> · <a href="/cart">View cart</a></nav>'
                body += '<p>USD. Fixed test shipping $10.00 per cart; test tax 6% of merchandise. No discounts.</p>'
                if path == '/shop':
                    for sku, product in store.catalog['products'].items():
                        body += f'<section><h2>{esc(product["name"])}</h2><p>SKU: {sku}. Price ${product["price_cents"]/100:.2f}.'
                        body += '<ul>'+''.join('<li>'+esc(k.replace('_',' ').title()+': '+('Not documented' if v is None else str(v).replace('_',' ')))+'</li>' for k,v in product.items() if k not in ('name','price_cents','category'))+'</ul>'
                        body += f' Size {product.get("size", "n/a")}; width {product.get("width", "n/a")}. Quantity 1 = one {product["unit"]}. Available.</p>'
                        body += f'<form method="post" action="/cart"><input type="hidden" name="csrf" value="{row["csrf"]}"><input type="hidden" name="sku" value="{sku}"><input type="hidden" name="quantity" value="1"><button>Add {esc(product["name"])} to cart</button></form></section>'
                else:
                    body += f'<h2>Your cart</h2><p>Cart reference: {row["cart_id"]}. Version: {row["version"]}.</p>'
                    if not items:
                        body += '<p>Your cart is empty.</p>'
                    subtotal = 0
                    for sku, qty in items.items():
                        p = store.catalog['products'][sku]
                        subtotal += p['price_cents'] * qty
                        body += f'<section><h3>{esc(p["name"])}</h3><p>SKU {sku}. Quantity {qty}. Size {p.get("size", "n/a")}; width {p.get("width", "n/a")}. Line ${p["price_cents"]*qty/100:.2f}</p></section>'
                    if items:
                        tax = (subtotal*store.catalog['tax_basis_points']+5000)//10000
                        total = subtotal+store.catalog['shipping_cents']+tax
                        body += f'<p>Merchandise ${subtotal/100:.2f}<br>Shipping $10.00<br>Test tax ${tax/100:.2f}<br><strong>Complete test total USD ${total/100:.2f}</strong></p>'
                    intent = json.loads(row['intent'])
                    problems = []
                    for sku in items:
                        product = store.catalog['products'][sku]
                        requirements = intent.get('requirements', {'width': intent['required_width'], 'size': intent['required_size']})
                        for field, expected in requirements.items():
                            observed = product.get(field)
                            if observed is None or (observed > expected if field == 'delivery_within_days' else observed != expected):
                                problems.append(f'{field}: required {expected}; merchant evidence {observed if observed is not None else "unknown"}')
                    if problems:
                        body += '<p><strong>AgentCoSign: not eligible for approval.</strong> '+esc('; '.join(problems))+'</p>'
                    for sku in items:
                        body += f'<form method="post" action="/cart"><input type="hidden" name="csrf" value="{row["csrf"]}"><input type="hidden" name="sku" value="{sku}"><input type="hidden" name="quantity" value="0"><button>Remove {esc(store.catalog["products"][sku]["name"])}</button></form>'
                    body += '<p>Stop here. The buyer will review separately. No checkout or payment action is available.</p>'
                self.reply(200, '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>AgentCoSign Test Shop</title><style>body{font:18px/1.6 system-ui;max-width:850px;margin:40px auto;padding:20px;color:#17332f;background:#eef6f3}section{background:white;padding:20px;margin:16px 0;border-radius:12px}button{font:inherit;padding:12px;background:#176a53;color:white;border:0;border-radius:6px}a{color:#176a53}</style>'+body+'</html>')
            except Refused as error:
                self.reply(error.status, html.escape(error.message))

        def do_POST(self):
            try:
                path = urlsplit(self.path).path
                if path not in ('/cart', '/buyer/approve', '/buyer/decline', '/buyer/requote', '/buyer/paypal-order', '/buyer/capture', '/buyer/reconcile'):
                    raise Refused(404, 'No shopper approval, checkout, or payment route')
                if self.headers.get('Origin') not in (None, self.server.origin):
                    raise Refused(403, 'Origin not allowed')
                size = int(self.headers.get('Content-Length', 0))
                if not 0 < size <= 2048:
                    raise Refused(400, 'Invalid form length')
                form = parse_qs(self.rfile.read(size).decode(), keep_blank_values=True)
                if path in ('/buyer/paypal-order', '/buyer/capture', '/buyer/reconcile'):
                    if not store.payments:
                        raise Refused(404, 'Sandbox integration is not enabled')
                    required = {'csrf', 'quote_id', 'quote_hash'} if path == '/buyer/paypal-order' else {'csrf'}
                    if set(form) != required or any(len(v) != 1 for v in form.values()):
                        raise Refused(400, 'Unexpected sandbox form fields')
                    from paypal_sandbox import ProviderFailure
                    try:
                        if path == '/buyer/paypal-order':
                            purchase = store.payments.start(self.cookie('buyer'), form['csrf'][0], form['quote_id'][0], form['quote_hash'][0], self.server.origin)
                            self.reply(303, headers={'Location': purchase['approval_url'] if purchase['state'] == 'waiting_for_buyer' else '/buyer/review'})
                        elif path == '/buyer/capture':
                            store.payments.capture(self.cookie('buyer'), form['csrf'][0])
                            self.reply(303, headers={'Location': '/buyer/review'})
                        else:
                            buyer = store.payments._buyer(self.cookie('buyer'), form['csrf'][0])
                            store.payments.reconcile(buyer['task_id'])
                            self.reply(303, headers={'Location': '/buyer/review'})
                    except ProviderFailure as error:
                        self.reply(503, f'<h1>Sandbox outcome needs checking</h1><p>{html.escape(str(error))}</p><p>No replacement purchase was created. Use the existing purchase status.</p><a href="/buyer/review">Back to review</a>')
                    return
                if path.startswith('/buyer/'):
                    if set(form) != {'csrf', 'quote_id', 'quote_hash'} or any(len(v) != 1 for v in form.values()):
                        raise Refused(400, 'Unexpected buyer form fields')
                    if path == '/buyer/requote':
                        store.buyer_refresh(self.cookie('buyer'), form['csrf'][0], form['quote_id'][0], form['quote_hash'][0])
                    else:
                        store.buyer_decide(self.cookie('buyer'), form['csrf'][0], form['quote_id'][0], form['quote_hash'][0],
                                           'approve' if path.endswith('/approve') else 'decline')
                    self.reply(303, headers={'Location': '/buyer/review'})
                    return
                if set(form) != {'csrf', 'sku', 'quantity'} or any(len(v) != 1 for v in form.values()):
                    raise Refused(400, 'Unexpected form fields')
                store.mutate(self.cookie(), form['csrf'][0], form['sku'][0], int(form['quantity'][0]))
                self.reply(303, headers={'Location': '/cart'})
            except (ValueError, UnicodeError):
                self.reply(400, 'Invalid input')
            except Refused as error:
                self.reply(error.status, html.escape(error.message))

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.origin = f'http://127.0.0.1:{server.server_port}'
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
