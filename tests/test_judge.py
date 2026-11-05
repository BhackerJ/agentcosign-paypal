"""Local synthetic extraction and isolated session contracts; no paid model or PayPal calls."""
import tempfile, unittest, threading, http.client, json
from pathlib import Path
from http.server import ThreadingHTTPServer
from intent_input import extract, parse_model_json, explicit_budget
from judge import Sessions, judge_handler
from shop import Refused, digest
import profile_intent


def draft(text):
    return extract(text, lambda _: {'budget_cents':explicit_budget(text),'requirements':{'color':'black'},'evidence':{'color':'black'},'unsupported':[]})


class IntentTests(unittest.TestCase):
    def test_strict_budget_wording(self):
        self.assertEqual(explicit_budget('total under $220.'),21999)
        self.assertEqual(explicit_budget('total less than $220.'),21999)
        self.assertEqual(explicit_budget('maximum $220.'),22000)
        self.assertEqual(explicit_budget('no more than $130 total'),13000)

    def test_original_requirements_remain_enforced(self):
        text='walking shoes size 9 extra wide within 12 days, maximum $130'
        data={'budget_cents':13000,'requirements':{'shoe_type':'walking','size':'9','width':'extra_wide','delivery_within_days':12},'evidence':{'shoe_type':'walking shoes','size':'9','width':'extra wide','delivery_within_days':'within 12 days'},'unsupported':[]}
        self.assertEqual(extract(text,lambda _:data)['requirements']['shoe_type'],'walking')
        data['requirements']['shoe_type']='invented'
        with self.assertRaises(Refused): extract(text,lambda _:data)

    def test_model_json_fence(self):
        self.assertEqual(parse_model_json('```json\n{"ok": true}\n```'), {'ok': True})
        with self.assertRaises(ValueError): parse_model_json('Here is the result: {"ok": true}')

    def test_three_new_requests(self):
        for text in ('Find a pair of black shoes for less than $250.', 'Please find black shoes, maximum $250.', 'One pair of black shoes under $250 for work.'):
            result = draft(text)
            self.assertEqual(result['request'], text)
            self.assertEqual(result['budget_cents'], explicit_budget(text))
            self.assertEqual(result['source_case_id'], 'natural-language')

    def test_budget_cannot_be_relaxed(self):
        with self.assertRaises(Refused):
            extract('black shoes under $200', lambda _: {'budget_cents':25000,'requirements':{},'evidence':{},'unsupported':[]})

    def test_invalid_model_structure_and_evidence(self):
        for result in (None, [], {'budget_cents':25000,'requirements':{'color':'black'},'evidence':None,'unsupported':[]}, {'budget_cents':25000,'requirements':{'color':'black'},'evidence':{'color':'not in request'},'unsupported':[]}):
            with self.assertRaises(Refused): extract('black shoes under $250',lambda _: result)


class JudgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.sessions = Sessions(Path(self.tmp.name),'http://127.0.0.1',extractor=draft)
        self.cookies = [self.sessions.new(),self.sessions.new()]
        self.rows = [self.sessions.record(c) for c in self.cookies]
        self.apps = [self.sessions.draft(r,'Please find black shoes under $250') for r in self.rows]
        self.http = ThreadingHTTPServer(('127.0.0.1',0),judge_handler(self.sessions))
        self.origin = 'http://127.0.0.1:'+str(self.http.server_port)
        self.sessions.origin = self.origin
        for app in self.apps: app.origin=self.origin
        threading.Thread(target=self.http.serve_forever,daemon=True).start()

    def tearDown(self):
        self.http.shutdown();self.http.server_close();self.sessions.pool.shutdown()
        for app in self.sessions.apps.values(): app.s.db.close()
        self.sessions.db.close();self.tmp.cleanup()

    def request(self,path,headers=None,method='GET',body=None):
        conn=http.client.HTTPConnection('127.0.0.1',self.http.server_port)
        conn.request(method,path,body,headers or {})
        res=conn.getresponse(); data=res.read().decode(); out=(res.status,dict(res.getheaders()),data);conn.close();return out

    def test_keys_and_cart_isolation(self):
        a,b=self.apps
        self.assertNotEqual(a.task,b.task);self.assertNotEqual(a.key,b.key)
        status,_,_=self.request('/api/purchase',{'X-Agent-Session':self.rows[1]['id'],'Authorization':'Bearer '+a.key})
        self.assertEqual(status,403)
        status,_,data=self.request('/api/purchase',{'X-Agent-Session':self.rows[0]['id'],'Authorization':'Bearer '+a.key})
        self.assertEqual(status,200);self.assertEqual(json.loads(data)['cart_id'],a.s.snapshot(a.task)['cart_id'])
        self.assertNotIn(b.task,data)

    def test_buyer_cannot_cross_sessions_and_agent_cannot_confirm(self):
        a,b=self.apps
        buyer_cookie=a.s.buyer_exchange(a.s.buyer_access(a.task))
        buyer=a.s.buyer_session(buyer_cookie)
        headers={'Cookie':'judge='+self.cookies[1]+'; buyer='+buyer_cookie,'Origin':self.origin}
        status,_,_=self.request('/confirm',headers,'POST','csrf='+buyer['csrf']+'&intent_hash='+digest(b.s.snapshot(b.task)['intent']))
        self.assertEqual(status,403)
        headers={'Authorization':'Bearer '+a.key,'X-Agent-Session':self.rows[0]['id'],'Origin':self.origin}
        self.assertEqual(self.request('/confirm',headers,'POST','csrf=x')[0],403)
        self.assertFalse(profile_intent.status(b.s,b.task)['confirmed'])

    def test_browser_entry_and_neutral_return(self):
        headers={'Cookie':'judge='+self.cookies[0]}
        self.assertEqual(self.request('/agent',headers)[0],200)
        status,h,_=self.request('/buyer',headers)
        self.assertEqual(status,303)
        headers['Cookie']+='; '+h['Set-Cookie'].split(';')[0]
        status,_,body=self.request('/buyer',headers)
        self.assertEqual(status,200);self.assertIn('Confirm shopping instructions',body)
        self.assertIn('/agent',body)
        self.assertEqual(self.request('/developer',headers)[0],404)
        self.assertEqual(self.request('/buyer/paypal-return?token=untrusted')[0],200)

    def test_restart_preserves_intent_confirmation(self):
        app=self.apps[0];before=app.s.snapshot(app.task)
        buyer=app.s.buyer_session(app.s.buyer_exchange(app.s.buyer_access(app.task)))
        profile_intent.confirm(app.s,app.task,buyer,digest(before['intent']))
        del self.sessions.apps[self.rows[0]['id']];app.s.db.close()
        restored=self.sessions.app(self.rows[0]['id'])
        self.assertEqual(restored.s.snapshot(restored.task)['intent'],before['intent'])
        self.assertTrue(profile_intent.status(restored.s,restored.task)['confirmed'])

    def test_expired_cookie_does_not_silently_replace_purchase_session(self):
        with self.sessions.db: self.sessions.db.execute('UPDATE sessions SET expires=0 WHERE id=?',(self.rows[0]['id'],))
        self.assertEqual(self.request('/',{'Cookie':'judge='+self.cookies[0]})[0],403)

    def test_isolated_mock_payment_and_repeats(self):
        from payments import Payments
        from test_payments import FakePayPal, CONFIG
        from shop import token_hash
        import time
        a,b = self.apps
        api = FakePayPal(); a.p = Payments(a.s, api, CONFIG)
        b.p = Payments(b.s, FakePayPal(), CONFIG)
        with a.s.db:
            a.s.db.execute('UPDATE carts SET visit_hash=?,visit_expires=? WHERE task_id=?',(token_hash('local-test'),time.time()+60,a.task))
        visit = a.s.exchange('local-test')
        sku = next(sku for sku,p in a.s.catalog['products'].items() if p.get('color') == 'black')
        a.s.mutate(visit,a.s.session(visit)['csrf'],sku,1)
        a.s.runner_finished(a.task,'done'); q=a.s.freeze(a.task)
        cookie=a.s.buyer_exchange(a.s.buyer_access(a.task)); buyer=a.s.buyer_session(cookie)
        profile_intent.confirm(a.s,a.task,buyer,digest(a.s.snapshot(a.task)['intent']))
        a.s.buyer_decide(cookie,buyer['csrf'],q['quote_id'],q['sha256'],'approve')
        a.p.start(cookie,buyer['csrf'],q['quote_id'],q['sha256'],a.origin)
        api.approve()
        for _ in range(3): self.assertTrue(a.p.capture(cookie,buyer['csrf'])['payment_verified'])
        self.assertEqual(sum(m=='POST' and p.endswith('/capture') for m,p,_,_ in api.calls),1)
        self.assertIsNone(b.purchase())
        self.assertEqual(b.s.db.execute('SELECT count(*) FROM merchant_orders').fetchone()[0],0)
        for action in ('approve','capture','check','repeat'):
            headers={'Cookie':'judge='+self.cookies[1]+'; buyer='+cookie,'Origin':self.origin}
            self.assertEqual(self.request('/'+action,headers,'POST','csrf='+buyer['csrf'])[0],403)

    def test_real_browser_form_confirmation(self):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context()
            context.add_cookies([{'name':'judge','value':self.cookies[0],'url':self.origin,'httpOnly':True,'sameSite':'Strict'}])
            page = context.new_page()
            page.goto(self.origin+'/buyer')
            page.get_by_role('button',name='Confirm shopping instructions',exact=True).click()
            page.get_by_role('link',name='Return to your personal agent',exact=True).click()
            self.assertTrue(page.get_by_role('button',name='Start / resume example shopper',exact=True).is_visible())
            self.assertTrue(profile_intent.status(self.apps[0].s,self.apps[0].task)['confirmed'])
            self.assertFalse(profile_intent.status(self.apps[1].s,self.apps[1].task)['confirmed'])
            browser.close()

    def test_shopper_finish_uses_authorization_http_api(self):
        from shopper import review_cart
        from shop import token_hash
        import time
        a=self.apps[0]
        buyer=a.s.buyer_session(a.s.buyer_exchange(a.s.buyer_access(a.task)))
        profile_intent.confirm(a.s,a.task,buyer,digest(a.s.snapshot(a.task)['intent']))
        with a.s.db:a.s.db.execute('UPDATE carts SET visit_hash=?,visit_expires=? WHERE task_id=?',(token_hash('review-test'),time.time()+60,a.task))
        visit=a.s.exchange('review-test');sku=next(iter(a.s.catalog['products']))
        a.s.mutate(visit,a.s.session(visit)['csrf'],sku,1);a.s.runner_finished(a.task,'done')
        a.agent_api_origin=self.origin
        result=review_cart(a)
        self.assertEqual(result['cart_id'],a.s.snapshot(a.task)['cart_id'])
        self.assertEqual(result['assessment']['intent_aware_quote_policy']['gate'],'allow')
        self.assertEqual(result['assessment']['actual_authorization_gate']['gate'],'insufficient_evidence')
        self.assertIsNone(a.s.approval_for(a.task,result['quote']))
        a.agent_headers={'X-Agent-Session':self.rows[1]['id']}
        import urllib.error
        with self.assertRaises(urllib.error.HTTPError):review_cart(a)
