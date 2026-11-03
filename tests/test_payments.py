import copy
import json
import unittest
import http.cookiejar
import urllib.request
import urllib.error
import urllib.parse

import test_bridge
from shop import Refused, Store, serve
from payments import Payments
from paypal_sandbox import ProviderFailure, SandboxClient

CONFIG = {'PAYPAL_ENV': 'sandbox', 'PAYPAL_MERCHANT_ID': 'MERCHANT00001', 'PAYPAL_BUYER_ID': 'BUYER00000001'}


class FakePayPal:
    def __init__(self):
        self.body = None
        self.order = None
        self.capture = None
        self.calls = []
        self.timeout_create = False
        self.timeout_capture = False

    def request(self, method, path, body=None, request_id=None):
        self.calls.append((method, path, copy.deepcopy(body), request_id))
        if method == 'POST' and path == '/v2/checkout/orders':
            if self.order is None:
                self.body = copy.deepcopy(body)
                self.order = {'id': 'ORDER000000000001', 'intent': 'CAPTURE', 'status': 'PAYER_ACTION_REQUIRED',
                              'purchase_units': copy.deepcopy(body['purchase_units']),
                              'links': [{'rel': 'payer-action', 'href': 'https://www.sandbox.paypal.com/checkoutnow?token=ORDER000000000001'}]}
            if self.timeout_create:
                self.timeout_create = False
                raise ProviderFailure()
            return copy.deepcopy(self.order)
        if method == 'GET' and path.startswith('/v2/checkout/orders/'):
            return copy.deepcopy(self.order)
        if method == 'POST' and path.endswith('/capture'):
            self.capture = {'id': 'CAPTURE0000000001', 'status': 'COMPLETED', 'final_capture': True,
                            'amount': copy.deepcopy(self.order['purchase_units'][0]['amount']),
                            'supplementary_data': {'related_ids': {'order_id': self.order['id']}}}
            self.order['status'] = 'COMPLETED'
            self.order['purchase_units'][0]['payments'] = {'captures': [copy.deepcopy(self.capture)]}
            if self.timeout_capture:
                self.timeout_capture = False
                raise ProviderFailure()
            return copy.deepcopy(self.order)
        if method == 'GET' and path.startswith('/v2/payments/captures/'):
            return copy.deepcopy(self.capture)
        raise AssertionError('Unexpected provider call')

    def approve(self):
        self.order['status'] = 'APPROVED'
        self.order['payer'] = {'payer_id': CONFIG['PAYPAL_BUYER_ID']}


class SandboxPaymentContracts(unittest.TestCase):
    setUp = test_bridge.BridgeContracts.setUp
    tearDown = test_bridge.BridgeContracts.tearDown
    cart = test_bridge.BridgeContracts.cart
    quote = test_bridge.BridgeContracts.quote

    def prepare(self, sku='walk-extra-wide', approve=True):
        self.api = FakePayPal()
        self.payments = Payments(self.store, self.api, CONFIG)
        task, _, _ = self.cart(sku)
        quote = self.quote(task)
        session = self.store.buyer_exchange(self.store.buyer_access(task['task_id']))
        csrf = self.store.buyer_session(session)['csrf']
        if approve:
            self.store.buyer_decide(session, csrf, quote['quote_id'], quote['sha256'], 'approve')
        return task, quote, session, csrf

    def start(self, q, session, csrf):
        return self.payments.start(session, csrf, q['quote_id'], q['sha256'], 'http://127.0.0.1:64110')

    def test_create_capture_get_mapping_and_duplicate_requests(self):
        task, q, session, csrf = self.prepare()
        purchase = self.start(q, session, csrf)
        self.assertEqual(self.start(q, session, csrf)['order_id'], purchase['order_id'])
        self.assertEqual(len(self.api.calls), 1)
        self.assertEqual(self.api.body['purchase_units'][0]['amount']['value'], '114.94')
        self.assertEqual(self.api.body['purchase_units'][0]['items'][0]['sku'], 'walk-extra-wide')
        self.api.approve()
        first = self.payments.capture(session, csrf)
        second = self.payments.capture(session, csrf)
        self.assertTrue(first['payment_verified'] and second['payment_verified'])
        self.assertEqual(sum(method == 'POST' and path.endswith('/capture') for method, path, _, _ in self.api.calls), 1)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM merchant_orders').fetchone()[0], 1)

    def test_wrong_product_or_no_app_approval_never_calls_paypal(self):
        for sku in ('walk-standard', 'walk-extra-wide'):
            _, q, session, csrf = self.prepare(sku, approve=False)
            with self.assertRaises(Refused):
                self.start(q, session, csrf)
            self.assertEqual(self.api.calls, [])

    def test_create_timeout_reuses_request_id_and_body(self):
        _, q, session, csrf = self.prepare()
        self.api.timeout_create = True
        with self.assertRaises(ProviderFailure):
            self.start(q, session, csrf)
        self.start(q, session, csrf)
        self.assertEqual(self.api.calls[0][2:], self.api.calls[1][2:])

    def test_capture_timeout_reconciles_without_another_capture(self):
        _, q, session, csrf = self.prepare()
        self.start(q, session, csrf)
        self.api.approve()
        self.api.timeout_capture = True
        with self.assertRaises(ProviderFailure):
            self.payments.capture(session, csrf)
        self.assertTrue(self.payments.capture(session, csrf)['payment_verified'])
        self.assertEqual(sum(m == 'POST' and p.endswith('/capture') for m, p, _, _ in self.api.calls), 1)

    def test_mismatched_payee_payer_items_or_total_prevent_capture(self):
        _, q, session, csrf = self.prepare()
        self.start(q, session, csrf)
        self.api.approve()
        original = copy.deepcopy(self.api.order)
        for field in ('payer', 'payee', 'amount', 'items'):
            self.api.order = copy.deepcopy(original)
            unit = self.api.order['purchase_units'][0]
            if field == 'payer':self.api.order['payer']['payer_id'] = 'WRONG'
            elif field == 'payee':unit['payee']['merchant_id'] = 'WRONG'
            elif field == 'amount':unit['amount']['value'] = '1.00'
            else:unit['items'][0]['sku'] = 'walk-standard'
            with self.assertRaises(Refused):
                self.payments.capture(session, csrf)
        self.assertFalse(any(m == 'POST' and p.endswith('/capture') for m, p, _, _ in self.api.calls))

    def test_expired_or_withdrawn_app_approval_cannot_capture(self):
        _, q, session, csrf = self.prepare()
        self.start(q, session, csrf)
        self.api.approve()
        self.now += 301
        with self.assertRaises(Refused):self.payments.capture(session, csrf)
        self.now -= 301
        self.store.buyer_decide(session, csrf, q['quote_id'], q['sha256'], 'decline')
        with self.assertRaises(Refused):self.payments.capture(session, csrf)

    def test_restart_recovers_same_purchase_without_new_order(self):
        task, q, session, csrf = self.prepare()
        first = self.start(q, session, csrf)
        self.store.db.close()
        self.store = Store(self.path, clock=lambda: self.now)
        self.payments = Payments(self.store, self.api, CONFIG)
        second = self.start(q, session, csrf)
        self.assertEqual(first['purchase_id'], second['purchase_id'])
        self.assertEqual(first['create_request_id'], second['create_request_id'])
        self.assertEqual(sum(m == 'POST' for m, _, _, _ in self.api.calls), 1)

    def test_provider_breakdown_mismatch_and_missing_recorded_capture_rejected(self):
        task, q, session, csrf = self.prepare()
        self.start(q, session, csrf)
        self.api.approve()
        amount = self.api.order['purchase_units'][0]['amount']
        amount['breakdown']['shipping']['value'] = '9.00'
        with self.assertRaises(Refused):self.payments.capture(session, csrf)
        amount['breakdown']['shipping']['value'] = '10.00'
        self.payments.capture(session, csrf)
        del self.api.order['purchase_units'][0]['payments']
        with self.assertRaises(Refused):self.payments.reconcile(task['task_id'])

    def test_wrong_quote_or_shopper_never_creates_provider_order(self):
        task, q, session, csrf = self.prepare()
        with self.assertRaises(Refused):self.payments.start(session, csrf, q['quote_id'], 'tampered', 'http://127.0.0.1:64110')
        with self.assertRaises(Refused):self.payments.start('shopper', csrf, q['quote_id'], q['sha256'], 'http://127.0.0.1:64110')
        self.assertEqual(self.api.calls, [])

    def test_http_payment_handoff_capture_and_spoofed_return(self):
        task, q, _, _ = self.prepare()
        server = serve(self.store)
        class StopExternalRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, request, fp, code, msg, headers, newurl):
                if newurl.startswith('https://'):
                    return None
                return super().redirect_request(request, fp, code, msg, headers, newurl)
        browser = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()), StopExternalRedirect())
        try:
            entry = self.store.buyer_access(task['task_id'])
            browser.open(server.origin+'/buyer/enter/'+entry).read()
            row = self.store.db.execute('SELECT csrf FROM buyers WHERE task_id=?', (task['task_id'],)).fetchone()
            def post(path, values):
                return browser.open(urllib.request.Request(server.origin+path, data=urllib.parse.urlencode(values).encode(), headers={'Origin':server.origin}))
            browser.open(server.origin+'/buyer/paypal-return?token=WRONG').read()
            self.assertEqual(self.api.calls, [])
            with self.assertRaises(urllib.error.HTTPError) as redirected:
                post('/buyer/paypal-order', {'csrf':row['csrf'],'quote_id':q['quote_id'],'quote_hash':q['sha256']})
            self.assertEqual(redirected.exception.code, 303)
            self.assertTrue(redirected.exception.headers['Location'].startswith('https://www.sandbox.paypal.com/'))
            self.api.approve()
            post('/buyer/reconcile', {'csrf':row['csrf']}).read()
            body = post('/buyer/capture', {'csrf':row['csrf']}).read().decode()
            self.assertIn('Sandbox payment verified', body)
            self.assertIn('Test merchant order confirmed', body)
        finally:
            server.shutdown()
            server.server_close()

    def test_paid_task_cannot_be_reopened_or_approved_again(self):
        task, q, session, csrf = self.prepare()
        self.start(q, session, csrf)
        self.api.approve()
        self.payments.capture(session, csrf)
        with self.assertRaises(Refused):self.store.reopen(task['task_id'])
        with self.assertRaises(Refused):self.store.buyer_refresh(session, csrf, q['quote_id'], q['sha256'])

    def test_unapproved_paypal_order_cannot_capture(self):
        _, q, session, csrf = self.prepare()
        self.start(q, session, csrf)
        with self.assertRaises(Refused):self.payments.capture(session, csrf)

    def test_live_environment_rejected(self):
        with self.assertRaises(ValueError):SandboxClient({'PAYPAL_ENV': 'live'})
