import copy
import http.cookiejar
import json
import re
import tempfile
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from shop import Store, Refused, serve
from handoff import single_turn, report_status


def answer(*args, **kwargs):
    raise AssertionError('Original panelist must not run')


def driver_boundary(report, *, runner=None):
    turns = []
    reply = answer(runner, 'task', None, report, turns, 60, t=1)
    if reply is not None:
        raise AssertionError('No second model turn allowed')
    return turns


class BridgeContracts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.now = 1000.0
        self.path = Path(self.tmp.name) / 'cart.sqlite'
        self.store = Store(self.path, clock=lambda: self.now)

    def tearDown(self):
        self.store.db.close()
        self.tmp.cleanup()

    def cart(self, sku='walk-extra-wide'):
        task = self.store.create()
        session = self.store.exchange(task['visit_token'])
        csrf = self.store.session(session)['csrf']
        self.store.mutate(session, csrf, sku, 1)
        return task, session, csrf

    def quote(self, task):
        self.store.runner_finished(task['task_id'], 'done')
        return self.store.freeze(task['task_id'])

    def test_wrong_and_right_same_price_quote_pair(self):
        totals = []
        for sku, expected in [('walk-standard', 'block'), ('walk-extra-wide', 'allow')]:
            task, _, _ = self.cart(sku)
            q = self.quote(task)
            totals.append(q['total_cents'])
            r = self.store.assessment(task['task_id'], q)
            self.assertEqual(r['budget_only_quote_policy']['gate'], 'allow')
            self.assertEqual(r['intent_aware_quote_policy']['gate'], expected)
            self.assertNotEqual(r['actual_authorization_gate']['gate'], 'allow')
            self.assertEqual(q['total_cents'], q['subtotal_cents']+q['shipping_cents']+q['tax_cents']-q['discount_cents'])
        self.assertEqual(totals, [11494, 11494])

    def test_extra_item_then_removed(self):
        task, session, csrf = self.cart()
        self.store.mutate(session, csrf, 'care-kit', 1)
        q = self.quote(task)
        self.assertEqual(self.store.assessment(task['task_id'], q)['intent_aware_quote_policy']['gate'], 'block')
        self.store.reopen(task['task_id'])
        self.store.mutate(session, csrf, 'care-kit', 0)
        with self.assertRaises(Refused):
            self.store.facts(task['task_id'], q)
        self.assertEqual(self.store.assessment(task['task_id'], self.quote(task))['intent_aware_quote_policy']['gate'], 'allow')

    def test_freeze_is_idempotent_and_prevents_shopper_edit(self):
        task, session, csrf = self.cart()
        q = self.quote(task)
        self.assertEqual(self.store.freeze(task['task_id']), q)
        with self.assertRaises(Refused):
            self.store.mutate(session, csrf, 'care-kit', 1)

    def test_tamper_expiry_and_catalog_change(self):
        task, _, _ = self.cart()
        q = self.quote(task)
        for field, value in [('total_cents', 1), ('merchant_id', 'other'), ('currency', 'EUR'), ('cart_version', 99)]:
            bad = copy.deepcopy(q)
            bad[field] = value
            with self.assertRaises(Refused):
                self.store.facts(task['task_id'], bad)
        self.store.catalog['products']['walk-extra-wide']['price_cents'] += 1
        with self.assertRaises(Refused):
            self.store.facts(task['task_id'], q)
        self.store.catalog['products']['walk-extra-wide']['price_cents'] -= 1
        self.now += 301
        with self.assertRaises(Refused):
            self.store.facts(task['task_id'], q)

    def test_timeout_preserves_cart_but_does_not_freeze(self):
        task, _, _ = self.cart()
        self.store.runner_finished(task['task_id'], 'timeout')
        with self.assertRaises(Refused):
            self.store.freeze(task['task_id'])
        self.assertEqual(self.store.snapshot(task['task_id'])['items'], {'walk-extra-wide': 1})

    def test_done_with_empty_cart_is_not_success(self):
        task = self.store.create()
        self.store.runner_finished(task['task_id'], 'done')
        with self.assertRaises(Refused):
            self.store.freeze(task['task_id'])

    def test_visit_replay_expiry_and_cart_isolation(self):
        task, session, csrf = self.cart()
        other = self.store.create()
        with self.assertRaises(Refused):
            self.store.exchange(task['visit_token'])
        self.assertEqual(self.store.snapshot(other['task_id'])['items'], {})
        with self.assertRaises(Refused):
            self.store.mutate(session, 'wrong', 'care-kit', 1)
        self.now += 601
        with self.assertRaises(Refused):
            self.store.exchange(other['visit_token'])

    def test_restart_keeps_same_quote_and_ids(self):
        task, _, _ = self.cart()
        q = self.quote(task)
        self.store.db.close()
        self.store = Store(self.path, clock=lambda: self.now)
        self.assertEqual(self.store.freeze(task['task_id']), q)

    def test_panelist_never_called_for_approval(self):
        result = single_turn(driver_boundary)('NEEDS_APPROVAL: May I buy this?')
        self.assertEqual(result[0]['panelist']['key'], 'end')
        self.assertEqual(driver_boundary.__globals__['answer'], answer)

    def test_markdown_report_status_without_approving_purchase(self):
        self.assertEqual(report_status('ok', 'Cart verified.\n\n**DONE**\n\nOne pair in cart.'), 'done')
        self.assertEqual(report_status('ok', 'Cart verified.\n\nDONE. One pair is in the cart.'), 'done')
        self.assertEqual(report_status('ok', 'DONEish'), 'unrecognized_report')
        self.assertEqual(report_status('ok', '**NEEDS_APPROVAL**\nMay I continue?'), 'needs_human')
        self.assertEqual(report_status('timeout', '**DONE**'), 'timeout')

    def test_ambiguous_report_does_not_become_done(self):
        self.assertEqual(report_status('ok', 'DONE\nNEEDS_APPROVAL'), 'unrecognized_report')
        self.assertEqual(report_status('ok', 'It is not DONE yet.'), 'unrecognized_report')

    def test_browser_form_binds_cart_and_refuses_forged_fields(self):
        server = serve(self.store)
        try:
            task = self.store.create()
            jar = http.cookiejar.CookieJar()
            browser = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
            response = browser.open(server.origin+'/visit/'+task['visit_token'])
            self.assertEqual(response.url, server.origin+'/shop')
            body = response.read().decode()
            csrf = re.search(r'name="csrf" value="([^"]+)"', body)[1]
            form = {'csrf': csrf, 'sku': 'walk-extra-wide', 'quantity': '1'}
            def post(path, values):
                return browser.open(urllib.request.Request(server.origin+path,
                    data=urllib.parse.urlencode(values).encode(), headers={'Origin': server.origin}))
            page = post('/cart', form).read().decode()
            self.assertIn(task['cart_id'], page)
            second = self.store.create()
            other = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
            other.open(server.origin+'/visit/'+second['visit_token']).read()
            other_cart = other.open(server.origin+'/cart?task_id='+task['task_id']).read().decode()
            self.assertNotIn(task['cart_id'], other_cart)
            self.assertIn(second['cart_id'], other_cart)
            with self.assertRaises(urllib.error.HTTPError) as caught:
                other.open(urllib.request.Request(server.origin+'/cart', data=urllib.parse.urlencode(form).encode()))
            self.assertEqual(caught.exception.code, 403)
            with self.assertRaises(urllib.error.HTTPError) as caught:
                browser.open(urllib.request.Request(server.origin+'/cart', data=urllib.parse.urlencode(form).encode(),
                             headers={'Origin': 'null'}))
            self.assertEqual(caught.exception.code, 403)
            for field in ('cart_id', 'price_cents', 'buyer_approval_verified'):
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    post('/cart', {**form, field: 'forged'})
                self.assertEqual(caught.exception.code, 400)
            with self.assertRaises(urllib.error.HTTPError) as caught:
                post('/approve', form)
            self.assertEqual(caught.exception.code, 404)
        finally:
            server.shutdown()
            server.server_close()


if __name__ == '__main__':
    unittest.main()
