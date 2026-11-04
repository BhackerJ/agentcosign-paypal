import argparse, json, tempfile, threading, unittest, urllib.request, urllib.parse
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright
from server import App, handler
from shop import token_hash, Refused
from payments import Payments
from test_payments import FakePayPal, CONFIG
import profile_intent


class RecoveryContracts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = App(
            argparse.Namespace(
                state=Path(self.tmp.name), port=0, scenario='walking-width', paypal_config=None
            )
        )
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), handler(self.app))
        self.app.origin = 'http://127.0.0.1:' + str(self.server.server_port)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.entry = json.loads((self.app.out / 'access.private.json').read_text())['url'].replace(
            'http://127.0.0.1:0', self.app.origin
        )

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.app.s.db.close()
        self.tmp.cleanup()

    def test_cross_site_return_and_cancel(self):
        destination = self.app.origin

        class External(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(
                    (
                        '<a href="'
                        + destination
                        + '/buyer/paypal-return?token=UNTRUSTED&PayerID=UNTRUSTED">Return</a><a href="'
                        + destination
                        + '/buyer/paypal-cancel">Cancel</a>'
                    ).encode()
                )

        external = ThreadingHTTPServer(('127.0.0.1', 0), External)
        threading.Thread(target=external.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                ctx = browser.new_context()
                page = ctx.new_page()
                page.goto(self.entry)
                self.assertEqual(ctx.cookies()[0]['sameSite'], 'Strict')
                for label in ['Return', 'Cancel']:
                    page.goto('http://localhost:' + str(external.server_port))
                    page.get_by_role('link', name=label, exact=True).click()
                    self.assertIn(
                        'This return does not prove approval or payment', page.locator('body').inner_text()
                    )
                    page.get_by_role('link', name='Continue to buyer review', exact=True).click()
                    self.assertIn('Confirm shopping instructions', page.locator('body').inner_text())
                ctx.close()
                browser.close()
        finally:
            external.shutdown()
            external.server_close()
        self.assertIsNone(self.app.purchase())
        self.assertEqual(self.app.s.db.execute('select count(*) from provider_calls').fetchone()[0], 0)

    def prepare_order(self):
        app = self.app
        s = app.s
        self.now = [1000]
        s.clock = lambda: self.now[0]
        api = FakePayPal()
        app.p = Payments(s, api, CONFIG)
        with s.db:
            s.db.execute(
                'update carts set visit_hash=?,visit_expires=? where task_id=?',
                (token_hash('test-visit'), 2000, app.task),
            )
        visit = s.exchange('test-visit')
        s.mutate(visit, s.session(visit)['csrf'], 'walk-extra-wide', 1)
        s.runner_finished(app.task, 'done')
        q = s.freeze(app.task)
        session = s.buyer_exchange(s.buyer_access(app.task))
        buyer = s.buyer_session(session)
        profile_intent.confirm(s, app.task, buyer, profile_intent.status(s, app.task)['intent_sha256'])
        s.buyer_decide(session, buyer['csrf'], q['quote_id'], q['sha256'], 'approve')
        purchase = app.p.start(session, buyer['csrf'], q['quote_id'], q['sha256'], app.origin)
        api.approve()
        return api, q, session, buyer, purchase

    def test_expired_existing_order_can_get_but_cannot_capture_or_replace(self):
        api, q, session, buyer, purchase = self.prepare_order()
        self.now[0] = q['expires_at'] + 1
        page = self.app.page(buyer)
        self.assertIn('Check PayPal status', page)
        self.assertIn('quote has expired', page)
        for text in ['Complete approved sandbox payment', 'Get a fresh quote', 'Continue PayPal approval']:
            self.assertNotIn(text, page)
        posts = [x for x in api.calls if x[0] == 'POST']
        request = urllib.request.Request(
            self.app.origin + '/check',
            data=urllib.parse.urlencode({'csrf': buyer['csrf']}).encode(),
            headers={'Origin': self.app.origin, 'Cookie': 'buyer=' + session},
        )
        with urllib.request.urlopen(request) as response:
            self.assertIn('Check PayPal status', response.read().decode())
        self.assertEqual(self.app.purchase()['order_id'], purchase['order_id'])
        with self.assertRaises(Refused):
            self.app.p.capture(session, buyer['csrf'])
        self.assertEqual(posts, [x for x in api.calls if x[0] == 'POST'])

    def test_completed_receipt_survives_quote_expiry(self):
        api, q, session, buyer, purchase = self.prepare_order()
        v = self.app.p.capture(session, buyer['csrf'])
        self.now[0] = q['expires_at'] + 1
        page = self.app.page(buyer)
        self.assertIn('Paid · verified with PayPal', page)
        self.assertIn(v['capture_id'], page)
        self.assertNotIn('quote has expired', page)
