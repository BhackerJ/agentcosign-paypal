"""One sandbox purchase per task, exact app approval, capture and GET reconciliation."""
import json
import re
import secrets
import uuid
from decimal import Decimal
from urllib.parse import urlsplit

from shop import Refused
from paypal_sandbox import ProviderFailure


def money(cents):
    return f'{cents//100}.{cents%100:02d}'


def cents(amount):
    value = Decimal(amount['value'])*100
    if amount.get('currency_code') != 'USD' or value != value.to_integral_value():
        raise Refused(409, 'Provider currency or amount invalid')
    return int(value)


class Payments:
    def __init__(self, store, client, config):
        self.store, self.client, self.config = store, client, config
        store.payments = self
        with store.lock, store.db:
            store.db.executescript('''
            CREATE TABLE IF NOT EXISTS purchases (
              purchase_id TEXT PRIMARY KEY, task_id TEXT UNIQUE, approval_id TEXT UNIQUE,
              quote TEXT, state TEXT, create_request_id TEXT UNIQUE, capture_request_id TEXT UNIQUE,
              create_body TEXT, order_id TEXT UNIQUE, capture_id TEXT UNIQUE,
              approval_url TEXT, verification TEXT, created_at REAL);
            CREATE TABLE IF NOT EXISTS merchant_orders (
              purchase_id TEXT PRIMARY KEY, capture_id TEXT UNIQUE, quote_sha256 TEXT,
              lines TEXT, total_cents INTEGER, status TEXT);
            ''')

    def get(self, task):
        with self.store.lock:
            row = self.store.db.execute('SELECT * FROM purchases WHERE task_id=?', (task,)).fetchone()
            return dict(row) if row else None

    def change_guard(self, task):
        purchase = self.get(task)
        if purchase and purchase['state'] in ('capturing', 'payment_pending', 'payment_verified', 'reconciliation_required'):
            raise Refused(409, 'Payment is in flight or recorded; reconcile this purchase before changing it')

    def _buyer(self, session, csrf):
        buyer = self.store.buyer_session(session)
        if not secrets.compare_digest(csrf, buyer['csrf']):
            raise Refused(403, 'Invalid buyer form token')
        return buyer

    def _approved(self, task):
        state = self.store.snapshot(task)
        if not state['quote']:
            raise Refused(409, 'Current quotation required')
        quote = state['quote']
        if quote.get('paypal_merchant_id') != self.config['PAYPAL_MERCHANT_ID']:
            raise Refused(409, 'Quote must bind the configured sandbox merchant; request a fresh quotation')
        approval = self.store.approval_for(task, quote)
        if not approval or self.store.assessment(task, quote)['actual_authorization_gate']['gate'] != 'allow':
            raise Refused(409, 'Valid exact buyer approval required')
        return quote, approval

    def _body(self, purchase_id, quote, origin):
        amounts = {'currency_code': 'USD', 'value': money(quote['total_cents']),
                   'breakdown': {key: {'currency_code': 'USD', 'value': money(quote[source])}
                                  for key, source in [('item_total', 'subtotal_cents'), ('shipping', 'shipping_cents'),
                                                      ('tax_total', 'tax_cents'), ('discount', 'discount_cents')]}}
        items = [{'name': line['name'], 'sku': line['sku'], 'quantity': str(line['quantity']),
                  'unit_amount': {'currency_code': 'USD', 'value': money(line['price_cents'])}}
                 for line in quote['lines']]
        return {'intent': 'CAPTURE', 'purchase_units': [{'reference_id': purchase_id, 'custom_id': purchase_id,
                    'invoice_id': purchase_id, 'payee': {'merchant_id': self.config['PAYPAL_MERCHANT_ID']},
                    'amount': amounts, 'items': items}],
                'payment_source': {'paypal': {'experience_context': {'user_action': 'PAY_NOW',
                    'shipping_preference': 'NO_SHIPPING',
                    'return_url': origin+'/buyer/paypal-return', 'cancel_url': origin+'/buyer/paypal-cancel'}}}}

    def start(self, session, csrf, quote_id, quote_hash, origin):
        with self.store.lock, self.store.db:
            buyer = self._buyer(session, csrf)
            quote, approval = self._approved(buyer['task_id'])
            if quote['quote_id'] != quote_id or quote['sha256'] != quote_hash:
                raise Refused(409, 'Quotation changed before PayPal order creation')
            purchase = self.get(buyer['task_id'])
            if purchase:
                if purchase['approval_id'] != approval['approval_id']:
                    raise Refused(409, 'A purchase already exists for this task; resolve it before starting another')
                if purchase['order_id']:
                    return purchase
                if self.store.clock()-purchase['created_at'] > 600:
                    raise Refused(409, 'Creation retry window closed; manual reconciliation required')
            else:
                purchase_id = secrets.token_hex(12)
                body = self._body(purchase_id, quote, origin)
                self.store.db.execute('INSERT INTO purchases VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                        (purchase_id, buyer['task_id'], approval['approval_id'], json.dumps(quote), 'creating',
                         str(uuid.uuid4()), str(uuid.uuid4()), json.dumps(body), None, None, None, None, self.store.clock()))
                purchase = self.get(buyer['task_id'])
        # Persist request identity/body before network I/O. Retries reuse both.
        order = self.client.request('POST', '/v2/checkout/orders', json.loads(purchase['create_body']), purchase['create_request_id'])
        order_id = order.get('id', '')
        links = [link['href'] for link in order.get('links', []) if link.get('rel') in ('approve', 'payer-action')]
        if not re.fullmatch(r'[A-Z0-9]{8,32}', order_id) or len(links) != 1:
            raise Refused(409, 'Unexpected PayPal order response; retain request ID for reconciliation')
        parsed = urlsplit(links[0])
        if parsed.scheme != 'https' or parsed.hostname not in ('www.sandbox.paypal.com', 'sandbox.paypal.com') or parsed.username:
            raise Refused(409, 'Unexpected approval destination')
        with self.store.lock, self.store.db:
            current = self.get(buyer['task_id'])
            if current['order_id']:
                if current['order_id'] != order_id:
                    raise Refused(409, 'Creation retry returned a different provider order')
                return current
            self.store.db.execute('UPDATE purchases SET order_id=?,approval_url=?,state=? WHERE purchase_id=?',
                                 (order_id, links[0], 'waiting_for_buyer', purchase['purchase_id']))
            self.store.audit(buyer['task_id'], 'sandbox_order_created', {'purchase_id': purchase['purchase_id'], 'order_id': order_id})
        return self.get(buyer['task_id'])

    def _check_order(self, purchase, order):
        quote = json.loads(purchase['quote'])
        units = order.get('purchase_units', [])
        if order.get('id') != purchase['order_id'] or order.get('intent') != 'CAPTURE' or len(units) != 1:
            raise Refused(409, 'Provider order identity mismatch')
        unit = units[0]
        if (unit.get('custom_id') != purchase['purchase_id'] or unit.get('reference_id') != purchase['purchase_id']
                or unit.get('payee', {}).get('merchant_id') != self.config['PAYPAL_MERCHANT_ID']
                or cents(unit['amount']) != quote['total_cents']):
            raise Refused(409, 'Provider payee, amount, or purchase binding mismatch')
        for key, source in [('item_total', 'subtotal_cents'), ('shipping', 'shipping_cents'), ('tax_total', 'tax_cents'), ('discount', 'discount_cents')]:
            value = unit['amount'].get('breakdown', {}).get(key, {'currency_code': 'USD', 'value': '0.00'})
            if cents(value) != quote[source]:
                raise Refused(409, 'Provider amount breakdown mismatch')
        expected = sorted((line['sku'], line['name'], line['quantity'], line['price_cents']) for line in quote['lines'])
        actual = sorted((line['sku'], line['name'], int(line['quantity']), cents(line['unit_amount'])) for line in unit.get('items', []))
        if actual != expected:
            raise Refused(409, 'Provider item mapping mismatch')
        payer = order.get('payer', {}).get('payer_id') or order.get('payment_source', {}).get('paypal', {}).get('account_id')
        if (order.get('status') in ('APPROVED', 'COMPLETED') or unit.get('payments', {}).get('captures')) and payer != self.config['PAYPAL_BUYER_ID']:
            raise Refused(409, 'Unexpected sandbox buyer account')
        return unit

    def reconcile(self, task):
        purchase = self.get(task)
        if not purchase or not purchase['order_id']:
            raise Refused(409, 'No provider order to reconcile')
        order = self.client.request('GET', '/v2/checkout/orders/'+purchase['order_id'])
        unit = self._check_order(purchase, order)
        captures = unit.get('payments', {}).get('captures', [])
        if not captures:
            if purchase['capture_id']:
                raise Refused(409, 'Previously recorded capture missing from provider order')
            result = {'order_status': order['status'], 'payment_verified': False, 'checked_at': self.store.clock()}
            with self.store.lock, self.store.db:
                current = self.get(task)
                if current['capture_id']:
                    raise Refused(409, 'Previously recorded capture missing from this provider response')
                state = current['state'] if current['state'] == 'capturing' else ('ready_to_capture' if order['status'] == 'APPROVED' else 'waiting_for_buyer')
                self.store.db.execute('UPDATE purchases SET state=?,verification=? WHERE purchase_id=?', (state, json.dumps(result), purchase['purchase_id']))
            return result
        if len(captures) != 1:
            raise Refused(409, 'Multiple captures require manual reconciliation')
        capture_id = captures[0]['id']
        if purchase['capture_id'] and purchase['capture_id'] != capture_id:
            raise Refused(409, 'Capture identity changed')
        capture = self.client.request('GET', '/v2/payments/captures/'+capture_id)
        if (capture.get('id') != capture_id or cents(capture['amount']) != json.loads(purchase['quote'])['total_cents']
                or capture.get('supplementary_data', {}).get('related_ids', {}).get('order_id') != purchase['order_id']):
            raise Refused(409, 'Capture amount or order binding mismatch')
        complete = order['status'] == 'COMPLETED' and capture.get('status') == 'COMPLETED' and capture.get('final_capture') is True
        verification = {'order_id': purchase['order_id'], 'capture_id': capture_id,
                        'order_status': order['status'], 'capture_status': capture.get('status'),
                        'total_cents': json.loads(purchase['quote'])['total_cents'], 'currency': 'USD',
                        'payee_matches': True, 'payer_matches': True, 'items_match': True,
                        'payment_verified': complete, 'checked_at': self.store.clock()}
        with self.store.lock, self.store.db:
            current = self.get(task)
            if current['state'] == 'payment_verified' and not complete:
                return json.loads(current['verification'])
            self.store.db.execute('UPDATE purchases SET capture_id=?,state=?,verification=? WHERE purchase_id=?',
                                 (capture_id, 'payment_verified' if complete else 'payment_pending', json.dumps(verification), purchase['purchase_id']))
            if complete:
                quote = json.loads(purchase['quote'])
                self.store.db.execute('INSERT OR IGNORE INTO merchant_orders VALUES (?,?,?,?,?,?)',
                        (purchase['purchase_id'], capture_id, quote['sha256'], json.dumps(quote['lines']), quote['total_cents'], 'test_paid'))
                self.store.audit(task, 'sandbox_payment_verified', verification)
        return verification

    def capture(self, session, csrf):
        buyer = self._buyer(session, csrf)
        task = buyer['task_id']
        purchase = self.get(task)
        if not purchase or not purchase['order_id']:
            raise Refused(409, 'Create and approve the PayPal order first')
        # Always read back first; an earlier timed-out call may already have captured.
        checked = self.reconcile(task)
        if checked.get('payment_verified') or checked.get('capture_id'):
            return checked
        if checked.get('order_status') != 'APPROVED':
            raise Refused(409, 'PayPal buyer approval not yet verified')
        with self.store.lock, self.store.db:
            quote, approval = self._approved(task)
            if approval['approval_id'] != purchase['approval_id'] or quote != json.loads(purchase['quote']):
                raise Refused(409, 'Application approval changed')
            current = self.get(task)
            if current['state'] == 'capturing':
                raise Refused(409, 'Capture outcome unknown or in progress; use reconciliation, do not create another purchase')
            self.store.db.execute("UPDATE purchases SET state='capturing' WHERE purchase_id=?", (purchase['purchase_id'],))
        try:
            self.client.request('POST', '/v2/checkout/orders/'+purchase['order_id']+'/capture', {}, purchase['capture_request_id'])
        except ProviderFailure:
            # Keep capturing: a timeout/error is not evidence that no charge happened.
            raise
        return self.reconcile(task)


def render_payment(store, buyer):
    import html
    esc = html.escape
    service = store.payments
    if not service:
        return ''
    purchase = service.get(buyer['task_id'])
    state = store.snapshot(buyer['task_id'])
    quote = state['quote']
    csrf = f'<input type="hidden" name="csrf" value="{esc(buyer["csrf"])}">'
    body = '<section><h2>PayPal sandbox · test funds only</h2><p>Fictional merchandise; no real fulfillment or delivery address. You approve the PayPal order in your own browser.</p>'
    try:
        approved_quote, _ = service._approved(buyer['task_id'])
    except Refused:
        approved_quote = None
    if purchase:
        body += f'<p>Purchase reference: {esc(purchase["purchase_id"])}<br>State: {esc(purchase["state"])}</p>'
        if purchase['order_id']:
            body += f'<p>PayPal order: {esc(purchase["order_id"])}</p>'
            verification = json.loads(purchase['verification']) if purchase['verification'] else {}
            if verification.get('payment_verified'):
                body += f'<h3>Sandbox payment verified</h3><p>Capture: {esc(verification["capture_id"])}<br>USD {money(verification["total_cents"])} · {esc(verification["capture_status"])}</p><p>Payee, buyer, items, amount and purchase association matched PayPal GET responses.</p>'
                merchant = store.db.execute('SELECT status FROM merchant_orders WHERE purchase_id=?', (purchase['purchase_id'],)).fetchone()
                body += '<p>'+('Test merchant order confirmed.' if merchant else 'Merchant confirmation pending; do not pay again.')+'</p>'
            else:
                body += '<p>PayPal approval or payment is not yet verified.</p>'
                if verification:
                    body += f'<p>Provider order status: {esc(verification.get("order_status", "unknown"))}</p>'
                if purchase['approval_url'] and purchase['state'] == 'waiting_for_buyer':
                    body += f'<p><a href="{esc(purchase["approval_url"])}">Open the existing PayPal sandbox approval</a></p>'
                if approved_quote and purchase['state'] == 'ready_to_capture':
                    body += f'<form method="post" action="/buyer/capture">{csrf}<button>Capture sandbox USD {money(quote["total_cents"])}</button></form>'
            body += f'<form method="post" action="/buyer/reconcile">{csrf}<button class="secondary">Check existing PayPal payment status</button></form>'
    if approved_quote and (not purchase or not purchase['order_id']):
        hidden = csrf+f'<input type="hidden" name="quote_id" value="{esc(quote["quote_id"])}"><input type="hidden" name="quote_hash" value="{esc(quote["sha256"])}">'
        body += f'<form method="post" action="/buyer/paypal-order">{hidden}<button>Continue to PayPal sandbox · USD {money(quote["total_cents"])}</button></form>'
    elif not purchase:
        body += '<p>Review and approve the exact quotation above before continuing.</p>'
    return body+'</section>'
