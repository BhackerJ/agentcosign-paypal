"""Local personal-agent authorization service. One isolated task per process."""

import argparse, html, json, os, secrets, threading, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from shop import Store, Refused, digest
from payments import Payments
from paypal_sandbox import SandboxClient, load_config, ProviderFailure
import profile_intent

STYLE = 'body{font:18px/1.6 system-ui;background:#edf3ef;color:#183d32;max-width:960px;margin:35px auto;padding:24px}section{background:white;border:1px solid #ceddd3;border-radius:16px;padding:24px;margin:18px 0}button{font:inherit;background:#17664d;color:white;padding:12px;border:0;border-radius:8px}small{color:#526b60}a{color:#17664d}code{overflow-wrap:anywhere}'


class App:
    def __init__(self, args):
        os.umask(0o077)
        self.out = args.state.resolve()
        self.out.mkdir(parents=True, exist_ok=True)
        self.origin = f'http://127.0.0.1:{args.port}'
        self.s = Store(self.out / 'cart.sqlite', quote_lifetime_seconds=900)
        self.fixture, self.s.catalog = profile_intent.load_fixture(args.scenario)
        self.p = None
        with self.s.db:
            self.s.db.execute('CREATE TABLE IF NOT EXISTS provider_calls(method TEXT,path TEXT)')
        if args.paypal_config:
            config = load_config(args.paypal_config)
            store = self.s

            class Client(SandboxClient):
                def request(self, method, path, *a):
                    with store.lock, store.db:
                        store.db.execute('INSERT INTO provider_calls VALUES (?,?)', (method, path))
                    return super().request(method, path, *a)

            self.p = Payments(self.s, Client(config), config)
        row = self.s.db.execute('SELECT task_id FROM carts').fetchone()
        self.task = row[0] if row else self.s.create()['task_id']
        profile_intent.install(self.s, self.task, self.fixture)
        key = self.out / 'agent-key.private.txt'
        if not key.exists():
            key.write_text(secrets.token_urlsafe(32))
        self.key = key.read_text().strip()
        with self.s.db:
            self.s.db.execute('CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,message TEXT)')
        self.worker = None
        self.worker_lock = threading.Lock()
        self.job = 'Ready to start the example personal agent.'
        token = self.s.buyer_access(self.task)
        (self.out / 'access.private.json').write_text(json.dumps({'url': self.origin + '/enter/' + token}))

    def event(self, message):
        with self.s.lock, self.s.db:
            self.s.db.execute('INSERT INTO events(message) VALUES (?)', (message,))

    def purchase(self):
        return self.p.get(self.task) if self.p else None

    def api(self):
        with self.s.lock:
            st = self.s.snapshot(self.task)
            q = st['quote']
            purchase = self.purchase()
            try:
                assessment = self.s.assessment(self.task, q) if q else None
            except Refused:
                assessment = {'status': 'quote_expired'}
            return {
                'cart_id': st['cart_id'],
                'cart_version': st['version'],
                'intent': st['intent'],
                'intent_confirmation': profile_intent.status(self.s, self.task),
                'quote': q,
                'assessment': assessment,
                'payment': json.loads(purchase['verification'] or '{}') if purchase else None,
                'buyer_review_path': '/',
                'agent_can_approve': False,
            }

    def launch(self):
        profile_intent.require(self.s, self.task)
        with self.worker_lock:
            if self.worker and self.worker.is_alive():
                raise Refused(409, 'Shopper already running')
            if self.purchase():
                raise Refused(409, 'Resolve the recorded payment before shopping again')

            def run():
                self.job = 'Browser shopper is running. This page refreshes automatically.'
                try:
                    from shopper import run_shopper

                    run_shopper(self)
                    from client import call

                    current = call(self.origin, self.key, '/api/purchase')
                    review = call(
                        self.origin,
                        self.key,
                        '/api/review',
                        {
                            'cart_version': current['cart_version'],
                            'intent_sha256': current['intent_confirmation']['intent_sha256'],
                        },
                    )
                    (self.out / 'agent-review.json').write_text(json.dumps(review, indent=2))
                    gate = review['assessment']['intent_aware_quote_policy']['gate']
                    self.job = (
                        'Quote eligibility: ' + gate + '. Purchase approval pending; payment not started.'
                    )
                    self.event('Personal agent requested quote review: ' + gate + '.')
                except Exception as e:
                    self.job = 'Shopper stopped. Cart preserved; resume from the developer console.'
                    self.event(
                        'Shopper stopped: ' + type(e).__name__ + '. No payment was initiated by the shopper.'
                    )
                finally:
                    (self.out / 'job.json').write_text(json.dumps({'message': self.job}))

            self.worker = threading.Thread(target=run, daemon=True)
            self.worker.start()

    def page(self, buyer, developer=False):
        st = self.s.snapshot(self.task)
        intent = st['intent']
        q = st['quote']
        esc = html.escape
        c = profile_intent.status(self.s, self.task)

        def form(action, label, extra=''):
            return f'<form method="post" action="/{action}"><input type="hidden" name="csrf" value="{buyer["csrf"]}">{extra}<button>{esc(label)}</button></form>'

        def hidden(k, v):
            return f'<input type="hidden" name="{k}" value="{esc(str(v))}">'

        h = (
            '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>AgentCoSign · '
            + ('Developer console' if developer else 'Buyer approval')
            + '</title><style>'
            + STYLE
            + '</style>'
        )
        if self.worker and self.worker.is_alive():
            h += '<meta http-equiv="refresh" content="3">'
        h += (
            '<small>AGENTCOSIGN / '
            + ('DEVELOPER CONSOLE' if developer else 'PURCHASE AUTHORIZATION')
            + '</small><h1>'
            + ('Your agent. One authorized purchase.' if developer else 'Your instructions. Your approval.')
            + '</h1>'
        )
        h += (
            '<section><h2>Purchase request</h2><p>'
            + esc(intent['request'])
            + '</p><p>Maximum $'
            + f'{intent["budget_cents"]/100:.2f}'
            + ' including shipping and test tax.</p><ul>'
        )
        for k, v in intent['requirements'].items():
            h += (
                '<li>'
                + esc(
                    k.replace('_', ' ').title()
                    + ': '
                    + (
                        ('within ' + str(v) + ' days')
                        if k == 'delivery_within_days'
                        else str(v).replace('_', ' ')
                    )
                )
                + '</li>'
            )
        h += (
            '</ul><details><summary>Source and adaptations</summary><p>'
            + esc(self.fixture['source_disclosure'])
            + '</p>'
        )
        for kind, source in intent['sources'].items():
            h += '<h3>' + esc(kind.title() + ': ' + source['id']) + '</h3>'
            for excerpt in source['excerpts']:
                h += '<p>' + esc(excerpt['text']) + '</p>'
        h += '<p>' + esc(' '.join(intent['adaptations'])) + '</p></details>'
        if not c['confirmed']:
            h += (
                form('confirm', 'Confirm shopping instructions', hidden('intent_hash', c['intent_sha256']))
                + '<small>Instructions are not permission to pay.</small>'
            )
        else:
            h += '<p>✓ Confirmed by buyer. The agent cannot change these instructions.</p>'
        h += '</section>'
        if not q:
            h += (
                '<section><h2>'
                + esc(self.job)
                + '</h2><p>Your agent will send the selected items here for approval.</p></section>'
            )
        else:
            h += '<section><h2>Your agent selected</h2>'
            for line in q['lines']:
                h += '<p>' + esc(line['name']) + ' · Quantity ' + str(line['quantity']) + '</p>'
            h += f'<h2>Total ${q["total_cents"]/100:.2f} USD</h2><p>Items ${q["subtotal_cents"]/100:.2f} · Shipping ${q["shipping_cents"]/100:.2f} · Test tax ${q["tax_cents"]/100:.2f}</p><small>Fictional sandbox merchandise. No fulfillment.</small></section>'
            purchase = self.purchase()
            v = json.loads(purchase['verification'] or '{}') if purchase else {}
            if v.get('payment_verified'):
                capture_posts = self.s.db.execute(
                    "SELECT count(*) FROM provider_calls WHERE method='POST' AND path LIKE '%/capture'"
                ).fetchone()[0]
                receipts = self.s.db.execute('SELECT count(*) FROM merchant_orders').fetchone()[0]
                repeats = self.s.db.execute(
                    "SELECT count(*) FROM events WHERE message=?",
                    ('Repeat returned receipt ' + v['capture_id'],),
                ).fetchone()[0]
                h += (
                    '<section id="payment-result"><h2>Paid · verified with PayPal</h2><h3>$'
                    + f'{v["total_cents"]/100:.2f}'
                    + ' USD · Sandbox</h3><p>Order: '
                    + esc(v['order_status'])
                    + ' · Capture: '
                    + esc(v['capture_status'])
                    + '</p><p>'
                    + str(repeats)
                    + ' sequential repeat requests · Same receipt</p><p>'
                    + str(capture_posts)
                    + ' capture POST · '
                    + str(receipts)
                    + ' merchant receipt</p><small>Receipt '
                    + esc(v['capture_id'])
                    + '<br>Cart '
                    + esc(st['cart_id'])
                    + '</small></section>'
                )
            else:
                try:
                    gate = self.s.assessment(self.task, q)['intent_aware_quote_policy']['gate']
                    approved = bool(self.s.approval_for(self.task, q))
                except Refused:
                    gate = 'expired'
                    approved = False
                h += '<section>'
                if purchase:
                    h += (
                        '<h2>Existing PayPal order</h2><p>Status checks read the existing order; they never create or capture a payment.</p>'
                        + form('check', 'Check PayPal status')
                    )
                    if gate == 'expired':
                        h += '<p>The quote has expired. Capture is disabled; your existing order and approval remain recorded for reconciliation. Check its status before taking any further action. This prototype does not automatically renew or replace an existing order. Do not create another order as a retry.</p>'
                    elif gate != 'allow' or not approved:
                        h += '<p>Capture is unavailable because exact purchase approval or matching quote evidence is missing. Check the existing order status; no replacement order will be created.</p>'
                    elif purchase['state'] in ('ready_to_capture', 'reconciliation_required'):
                        if v.get('capture_rejected'):
                            h += (
                                '<p>PayPal declined this payment ('
                                + esc(v['capture_rejected'])
                                + '). <a href="'
                                + esc(purchase['approval_url'])
                                + '">Choose another payment method in PayPal</a>, or try again.</p>'
                            )
                        elif purchase['state'] == 'reconciliation_required':
                            h += '<p>The last payment attempt did not report a result. Trying again checks PayPal first and cannot charge twice for this order.</p>'
                        h += form('capture', 'Complete approved sandbox payment')
                    elif purchase['state'] == 'waiting_for_buyer':
                        h += '<a href="' + esc(purchase['approval_url']) + '">Continue PayPal approval</a>'
                elif gate == 'expired':
                    h += '<h2>Quote expired</h2>' + form(
                        'refresh', 'Get a fresh quote', hidden('quote', q['quote_id'])
                    )
                elif gate != 'allow':
                    h += '<h2>Purchase needs attention</h2><p>Required facts are missing or do not match. No payment is permitted.</p>'
                elif not approved:
                    h += form(
                        'approve',
                        f'Approve exact purchase · ${q["total_cents"]/100:.2f}',
                        hidden('quote', q['quote_id']),
                    )
                elif not self.p:
                    h += '<p>Purchase approved. Configure PayPal sandbox to enable payment; no payment has occurred.</p>'
                else:
                    h += form('pay', 'Continue to PayPal sandbox', hidden('quote', q['quote_id']))
                h += '</section>'
        if developer:
            purchase_now = self.purchase()
            live_status = (
                'Payment verified; receipt available.'
                if purchase_now and purchase_now['state'] == 'payment_verified'
                else 'Exact purchase approved; awaiting payment verification.' if purchase_now else self.job
            )
            h += (
                '<section><h2>Example personal agent</h2><p>'
                + esc(live_status)
                + '</p><p>Cart '
                + st['cart_id']
                + '</p>'
            )
            if c['confirmed'] and not self.purchase():
                h += form('shopper', 'Start / resume browser shopper')
            h += '<p>Deliberately assigned initial candidate; browser-only recovery. New run, separate from historical evidence.</p><ul>'
            for row in self.s.db.execute(
                "SELECT data FROM audit WHERE task_id=? AND event='cart_changed' ORDER BY id", (self.task,)
            ):
                change = json.loads(row[0])
                h += '<li>' + esc(('Added ' if change['quantity'] else 'Removed ') + change['sku']) + '</li>'
            h += '</ul><h2>Authorization and payment evidence</h2><ul>'
            for row in self.s.db.execute('SELECT message FROM events ORDER BY id'):
                h += '<li>' + esc(row[0]) + '</li>'
            h += '</ul>'
            if self.purchase() and self.purchase()['state'] == 'payment_verified':
                count = self.s.db.execute(
                    "SELECT count(*) FROM provider_calls WHERE method='POST' AND path LIKE '%/capture'"
                ).fetchone()[0]
                h += (
                    '<p>'
                    + str(count)
                    + ' capture POST · '
                    + str(self.s.db.execute('SELECT count(*) FROM merchant_orders').fetchone()[0])
                    + ' merchant receipt</p>'
                    + form('repeat', 'Repeat request; verify same receipt')
                )
            h += '<a href="/">Buyer approval and receipt</a></section>'
        return h + '</html>'


def handler(app):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def send(self, status, body='', location=None, cookie=None, json_body=False):
            self.send_response(status)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Type', 'application/json' if json_body else 'text/html; charset=utf-8')
            if location:
                self.send_header('Location', location)
            if cookie:
                self.send_header('Set-Cookie', 'buyer=' + cookie + '; HttpOnly; SameSite=Strict; Path=/')
            self.end_headers()
            self.wfile.write(body.encode())

        def session(self):
            c = SimpleCookie(self.headers.get('Cookie', ''))
            return c['buyer'].value if 'buyer' in c else ''

        def agent(self):
            if not secrets.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + app.key):
                raise Refused(403, 'Agent credential required')

        def do_GET(self):
            try:
                path = urlsplit(self.path).path
                if path.startswith('/enter/'):
                    self.send(303, location='/', cookie=app.s.buyer_exchange(path[7:]))
                    return
                if path in ('/buyer/paypal-return', '/buyer/paypal-cancel'):
                    self.send(
                        200,
                        '<!doctype html><html lang="en"><meta charset="utf-8"><title>Return to your purchase</title><h1>Return to your purchase</h1><p>This return does not prove approval or payment. Continue to your buyer page, then check the existing PayPal order.</p><a href="/">Continue to buyer review</a><p>If your buyer session has expired, restart the local service and open the new one-use buyer URL from your private state directory. The recorded order is preserved.</p></html>',
                    )
                    return
                if path == '/api/purchase':
                    self.agent()
                    self.send(200, json.dumps(app.api()), json_body=True)
                    return
                if path not in ('/', '/developer'):
                    raise Refused(404, 'Unknown page')
                buyer = app.s.buyer_session(self.session())
                self.send(200, app.page(buyer, path == '/developer'))
            except Refused as e:
                self.send(e.status, html.escape(e.message))

        def do_POST(self):
            try:
                n = int(self.headers.get('Content-Length', 0))
                if not 0 < n < 4096:
                    raise Refused(400, 'Invalid request')
                raw = self.rfile.read(n)
                if self.path == '/api/review':
                    self.agent()
                    profile_intent.require(app.s, app.task)
                    d = json.loads(raw)
                    st = app.s.snapshot(app.task)
                    if (
                        set(d) != {'cart_version', 'intent_sha256'}
                        or d['cart_version'] != st['version']
                        or d['intent_sha256'] != digest(st['intent'])
                    ):
                        raise Refused(409, 'Cart or intent changed')
                    if not st['quote']:
                        app.s.freeze(app.task)
                    self.send(200, json.dumps(app.api()), json_body=True)
                    return
                if self.headers.get('Origin') != app.origin:
                    raise Refused(403, 'Origin rejected')
                f = parse_qs(raw.decode())
                session = self.session()
                buyer = app.s.buyer_session(session)
                if not secrets.compare_digest(f['csrf'][0], buyer['csrf']):
                    raise Refused(403, 'Invalid form token')
                if self.path == '/confirm':
                    profile_intent.confirm(app.s, app.task, buyer, f['intent_hash'][0])
                    app.event('Buyer confirmed source-linked intent.')
                    self.send(303, location='/')
                    return
                profile_intent.require(app.s, app.task)
                if self.path == '/shopper':
                    app.launch()
                    self.send(303, location='/developer')
                    return
                q = app.s.snapshot(app.task)['quote']
                if not q:
                    raise Refused(409, 'Shopper has not supplied a quote')
                if self.path in ('/approve', '/pay', '/refresh') and f['quote'][0] != q['quote_id']:
                    raise Refused(409, 'Quote changed')
                if self.path == '/approve':
                    app.s.buyer_decide(session, buyer['csrf'], q['quote_id'], q['sha256'], 'approve')
                    app.event('Buyer approved the exact quote.')
                elif self.path == '/refresh':
                    app.s.buyer_refresh(session, buyer['csrf'], q['quote_id'], q['sha256'])
                elif not app.p:
                    raise Refused(409, 'PayPal sandbox is not configured')
                elif self.path == '/pay':
                    existed = bool(app.purchase())
                    purchase = app.p.start(session, buyer['csrf'], q['quote_id'], q['sha256'], app.origin)
                    app.event(
                        'Reused existing PayPal order.' if existed else 'Created one PayPal sandbox order.'
                    )
                    self.send(303, location=purchase['approval_url'])
                    return
                elif self.path == '/check':
                    v = app.p.reconcile(app.task)
                    app.event('PayPal GET order: ' + v['order_status'])
                elif self.path in ('/capture', '/repeat'):
                    if self.path == '/repeat' and (
                        not app.purchase() or app.purchase()['state'] != 'payment_verified'
                    ):
                        raise Refused(409, 'Verify the first payment before repeating')
                    v = app.p.capture(session, buyer['csrf'])
                    app.event(
                        ('Repeat returned receipt ' if self.path == '/repeat' else 'Verified capture ')
                        + v.get('capture_id', 'pending')
                    )
                else:
                    raise Refused(404, 'Unknown action')
                self.send(303, location='/developer' if self.path == '/repeat' else '/')
            except (Refused, ProviderFailure) as e:
                self.send(
                    getattr(e, 'status', 409) or 503,
                    '<h1>Purchase needs attention</h1><p>'
                    + html.escape(str(e))
                    + '</p><a href="/">Return to review</a>',
                )
            except (ValueError, KeyError):
                self.send(400, 'Invalid request')

    return Handler


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--scenario', default='walking-width', choices=['walking-width', 'resolable-work-shoes'])
    p.add_argument('--state', type=Path, default=Path('state/default'))
    p.add_argument('--port', type=int, default=64200)
    p.add_argument('--paypal-config', type=Path)
    args = p.parse_args()
    app = App(args)
    print(
        'Local service: ' + app.origin + '; buyer entry is stored in ' + str(app.out / 'access.private.json'),
        flush=True,
    )
    ThreadingHTTPServer(('127.0.0.1', args.port), handler(app)).serve_forever()


if __name__ == '__main__':
    main()
