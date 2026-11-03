import http.cookiejar
import re
import urllib.error
import urllib.parse
import urllib.request
import unittest

import test_bridge
from shop import Refused, Store, serve


class BuyerContracts(unittest.TestCase):
    setUp = test_bridge.BridgeContracts.setUp
    tearDown = test_bridge.BridgeContracts.tearDown
    cart = test_bridge.BridgeContracts.cart
    quote = test_bridge.BridgeContracts.quote

    def owner(self, task):
        entry = self.store.buyer_access(task['task_id'])
        session = self.store.buyer_exchange(entry)
        return session, self.store.buyer_session(session)['csrf']

    def decide(self, task, quote, decision='approve', owner=None):
        session, csrf = owner or self.owner(task)
        return self.store.buyer_decide(session, csrf, quote['quote_id'], quote['sha256'], decision)

    def test_approval_binds_exact_quote_and_duplicate_is_same_record(self):
        task, _, _ = self.cart()
        quote = self.quote(task)
        owner = self.owner(task)
        approval = self.decide(task, quote, owner=owner)
        self.assertEqual(approval, self.decide(task, quote, owner=owner))
        self.assertEqual(approval['quote_sha256'], quote['sha256'])
        result = self.store.assessment(task['task_id'], quote)
        self.assertEqual(result['actual_authorization_gate']['gate'], 'allow')
        self.assertEqual(result['paypal_approval'], 'not_started')
        self.assertEqual(result['payment_calls'], 0)

    def test_wrong_specification_cannot_be_overridden_by_approval(self):
        task, _, _ = self.cart('walk-standard')
        with self.assertRaises(Refused):
            self.decide(task, self.quote(task))
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM approvals').fetchone()[0], 0)

    def test_shopper_cannot_impersonate_buyer_even_with_quote_and_csrf(self):
        task, shopper, _ = self.cart()
        quote = self.quote(task)
        _, buyer_csrf = self.owner(task)
        with self.assertRaises(Refused):
            self.store.buyer_decide(shopper, buyer_csrf, quote['quote_id'], quote['sha256'], 'approve')

    def test_other_buyer_cannot_approve_this_quote(self):
        task, _, _ = self.cart()
        quote = self.quote(task)
        other = self.store.create()
        with self.assertRaises(Refused):
            self.decide(task, quote, owner=self.owner(other))

    def test_buyer_csrf_and_quote_hash_are_required(self):
        task, _, _ = self.cart()
        quote = self.quote(task)
        session, csrf = self.owner(task)
        for wrong_csrf, wrong_hash in [('wrong', quote['sha256']), (csrf, 'tampered')]:
            with self.assertRaises(Refused):
                self.store.buyer_decide(session, wrong_csrf, quote['quote_id'], wrong_hash, 'approve')

    def test_reopen_invalidates_approval_and_stale_form(self):
        task, shopper, csrf = self.cart()
        quote = self.quote(task)
        owner = self.owner(task)
        self.decide(task, quote, owner=owner)
        self.store.reopen(task['task_id'])
        self.store.mutate(shopper, csrf, 'care-kit', 1)
        with self.assertRaises(Refused):
            self.decide(task, quote, owner=owner)
        self.assertEqual(self.store.db.execute('SELECT status FROM approvals').fetchone()[0], 'invalidated')
        new_quote = self.quote(task)
        self.assertNotEqual(new_quote['quote_id'], quote['quote_id'])
        self.assertEqual(self.store.assessment(task['task_id'], new_quote)['actual_authorization_gate']['gate'], 'block')

    def test_expired_quote_and_changed_catalog_invalidate_approval(self):
        task, _, _ = self.cart()
        quote = self.quote(task)
        owner = self.owner(task)
        self.decide(task, quote, owner=owner)
        self.store.catalog['shipping_cents'] += 1
        with self.assertRaises(Refused):
            self.store.approval_for(task['task_id'], quote)
        self.store.catalog['shipping_cents'] -= 1
        self.now += 301
        with self.assertRaises(Refused):
            self.store.approval_for(task['task_id'], quote)
        with self.assertRaises(Refused):
            self.decide(task, quote, owner=owner)

    def test_withdrawal_and_decline_cannot_be_reactivated(self):
        for initially_approve in (False, True):
            task, _, _ = self.cart()
            quote = self.quote(task)
            owner = self.owner(task)
            if initially_approve:
                self.decide(task, quote, owner=owner)
            self.decide(task, quote, decision='decline', owner=owner)
            self.assertIsNone(self.store.approval_for(task['task_id'], quote))
            with self.assertRaises(Refused):
                self.decide(task, quote, owner=owner)

    def test_approval_survives_restart_with_same_buyer_binding(self):
        task, _, _ = self.cart()
        quote = self.quote(task)
        approval = self.decide(task, quote)
        self.store.db.close()
        self.store = Store(self.path, clock=lambda: self.now)
        self.assertEqual(self.store.approval_for(task['task_id'], quote), approval)

    def test_buyer_entry_is_one_use_and_session_expires(self):
        task = self.store.create()
        entry = self.store.buyer_access(task['task_id'])
        session = self.store.buyer_exchange(entry)
        with self.assertRaises(Refused):
            self.store.buyer_exchange(entry)
        self.now += 1201
        with self.assertRaises(Refused):
            self.store.buyer_session(session)

    def test_fresh_quote_requires_new_approval_and_rejects_old_form(self):
        task, _, _ = self.cart()
        quote = self.quote(task)
        owner = self.owner(task)
        self.decide(task, quote, owner=owner)
        self.now += 301
        fresh = self.store.buyer_refresh(*owner, quote['quote_id'], quote['sha256'])
        self.assertNotEqual(fresh['quote_id'], quote['quote_id'])
        self.assertIsNone(self.store.approval_for(task['task_id'], fresh))
        with self.assertRaises(Refused):
            self.decide(task, quote, owner=owner)
        self.decide(task, fresh, owner=owner)
        self.assertIsNotNone(self.store.approval_for(task['task_id'], fresh))

    def test_new_quote_rechecks_changed_price_and_stock(self):
        task, _, _ = self.cart()
        quote = self.quote(task)
        owner = self.owner(task)
        self.store.catalog['products']['walk-extra-wide']['available'] = False
        fresh = self.store.buyer_refresh(*owner, quote['quote_id'], quote['sha256'])
        with self.assertRaises(Refused):
            self.decide(task, fresh, owner=owner)

    def test_http_buyer_review_and_approval_are_separate_from_shopper(self):
        task, _, _ = self.cart()
        quote = self.quote(task)
        server = serve(self.store)
        try:
            owner = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
            entry = self.store.buyer_access(task['task_id'])
            response = owner.open(server.origin+'/buyer/enter/'+entry)
            self.assertEqual(response.url, server.origin+'/buyer/review')
            body = response.read().decode()
            self.assertIn('$114.94', body)
            self.assertIn('Extra Wide', body)
            self.assertIn(quote['merchant_id'], body)
            fields = dict(re.findall(r'name="([^"]+)" value="([^"]+)"', body))
            with self.assertRaises(urllib.error.HTTPError):
                owner.open(server.origin+'/cart')
            def post(values, origin=server.origin):
                return owner.open(urllib.request.Request(server.origin+'/buyer/approve',
                        data=urllib.parse.urlencode(values).encode(), headers={'Origin': origin}))
            for values, origin in [({**fields, 'total_cents': '1'}, server.origin), (fields, 'https://unrelated.example')]:
                with self.assertRaises(urllib.error.HTTPError):
                    post(values, origin)
            approved = post(fields).read().decode()
            self.assertIn('Quotation approved', approved)
            self.assertIn('no payment has been made', approved)
            self.assertIsNotNone(self.store.approval_for(task['task_id'], quote))
        finally:
            server.shutdown()
            server.server_close()
