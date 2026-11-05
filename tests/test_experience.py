import json,tempfile,threading,http.client,unittest,re
from urllib.parse import urlencode
from pathlib import Path
from http.server import ThreadingHTTPServer
from judge import Sessions
from experience import experience_handler
from test_judge import draft

class ExperienceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();root=Path(self.tmp.name);replay=root/'replay';(replay/'visits/1').mkdir(parents=True)
        (replay/'visits/1/index.html').write_text('<html><body>Original report</body></html>')
        self.sessions=Sessions(root/'state','http://127.0.0.1',extractor=draft)
        self.server=ThreadingHTTPServer(('127.0.0.1',0),experience_handler(self.sessions,replay))
        threading.Thread(target=self.server.serve_forever,daemon=True).start()
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.sessions.pool.shutdown();self.sessions.db.close();self.tmp.cleanup()
    def request(self,path,method='GET',headers=None,body=None):
        c=http.client.HTTPConnection('127.0.0.1',self.server.server_port);c.request(method,path,body=body,headers=headers or {});r=c.getresponse();out=(r.status,dict(r.getheaders()),r.read().decode());c.close();return out
    def new_live(self):
        status,h,page=self.request('/live/new')
        if status!=200:return status,h,page
        cookie=h['Set-Cookie'].split(';')[0]
        fields=dict(re.findall(r'name="(csrf|version|document_sha256)" value="([^"]+)"',page));fields['agree']='yes'
        status,reply,body=self.request('/accept-terms','POST',{'Cookie':cookie,'Origin':self.sessions.origin,'Content-Type':'application/x-www-form-urlencoded'},urlencode(fields))
        return status,dict(reply,**{'Set-Cookie':h['Set-Cookie']}),body

    def test_consent_is_required_and_records_current_version_hash_once(self):
        status,h,page=self.request('/live/new');self.assertEqual(status,200)
        cookie=h['Set-Cookie'].split(';')[0];fields=dict(re.findall(r'name="(csrf|version|document_sha256)" value="([^"]+)"',page))
        headers={'Cookie':cookie,'Origin':self.sessions.origin,'Content-Type':'application/x-www-form-urlencoded'}
        self.assertIn('Agree to terms and start',page)
        self.assertEqual(self.request('/request','POST',headers,'request=test')[0],403)
        self.assertEqual(self.request('/accept-terms','POST',headers,urlencode(fields))[0],400)
        fields['agree']='yes'
        bad=dict(headers,Origin='https://evil.example')
        self.assertEqual(self.request('/accept-terms','POST',bad,urlencode(fields))[0],403)
        wrong=dict(fields,csrf='wrong')
        self.assertEqual(self.request('/accept-terms','POST',headers,urlencode(wrong))[0],403)
        wrong=dict(fields,version='old')
        self.assertEqual(self.request('/accept-terms','POST',headers,urlencode(wrong))[0],400)
        self.assertEqual(self.request('/accept-terms','POST',headers,urlencode(fields))[0],303)
        row=dict(self.sessions.db.execute('SELECT * FROM terms_acceptance').fetchone())
        self.assertEqual(row['version'],fields['version']);self.assertEqual(row['document_sha256'],fields['document_sha256']);self.assertGreater(row['accepted_at'],0)
        self.assertEqual(self.request('/accept-terms','POST',headers,urlencode(fields))[0],303)
        self.assertEqual(dict(self.sessions.db.execute('SELECT * FROM terms_acceptance').fetchone()),row)
        self.assertEqual(self.sessions.db.execute('select count(*) from usage').fetchone()[0],0)
        self.assertEqual(self.request('/review-terms',headers=headers)[0],200)
        self.assertEqual(self.sessions.db.execute('select count(*) from sessions').fetchone()[0],1)
        from experience import experience_handler
        # Rebuilding the handler reads the existing persisted agreement, without renewing it.
        experience_handler(self.sessions,Path(self.tmp.name)/'replay')
        self.assertEqual(dict(self.sessions.db.execute('SELECT * FROM terms_acceptance').fetchone()),row)

    def test_recorded_is_session_free_and_only_live_injects_buyer_bridge(self):
        status,h,_=self.request('/');self.assertEqual(status,303);self.assertEqual(h['Location'],'/visits/1/?mode=recorded')
        _,_,page=self.request('/visits/1/?mode=recorded');self.assertIn('/experience.js',page);self.assertNotIn("fetch('/conversation?panel=1')",page)
        _,_,live=self.request('/visits/1/?mode=live');self.assertIn("fetch('/conversation?panel=1')",live)
        self.assertEqual(self.sessions.db.execute('select count(*) from sessions').fetchone()[0],0)
        self.assertEqual(self.sessions.db.execute('select count(*) from usage').fetchone()[0],0)
        evidence=json.loads(self.request('/recorded-evidence')[2]);self.assertEqual(evidence['recovery']['run'],'report-recorded-02');self.assertEqual(evidence['recovery']['approval']['total_cents'],8208);self.assertEqual(evidence['payment']['run'],'recorded-work-01');self.assertEqual(evidence['payment']['verification']['total_cents'],21034)
        self.assertNotIn('provider_calls',evidence['payment']);self.assertNotIn('payer',evidence['payment']['verification'])
    def test_terms_and_disclosure_are_available_without_session_or_provider(self):
        status,_,terms=self.request('/demo-terms')
        self.assertEqual(status,200)
        for phrase in ('Demo terms','significant portion','train or improve','prior written consent','may earn a commission'):
            self.assertIn(phrase,terms)
        script=self.request('/experience.js')[2]
        self.assertIn('/demo-terms',script)
        self.assertIn('We may earn a commission',script)
        self.assertEqual(self.sessions.db.execute('select count(*) from sessions').fetchone()[0],0)
        self.assertEqual(self.sessions.db.execute('select count(*) from usage').fetchone()[0],0)

    def test_payments_and_historical_writes_are_rejected_and_live_sessions_are_new(self):
        for path in ('/pay','/capture','/repeat','/check','/refresh'):
            self.assertEqual(self.request(path,'POST')[0],403)
        self.assertEqual(self.request('/recorded-evidence','POST')[0],403)
        self.assertEqual(self.request('/live/new',headers={'Authorization':'Bearer fake'})[0],403)
        one=self.new_live();two=self.new_live()
        self.assertNotEqual(one[1]['Set-Cookie'],two[1]['Set-Cookie']);self.assertEqual(one[1]['Location'],'/visits/1/?mode=live')
        self.assertEqual(self.sessions.db.execute('select count(*) from sessions').fetchone()[0],2)
        self.assertEqual(self.sessions.db.execute('select count(*) from usage').fetchone()[0],0)
        self.assertEqual(self.request('/experience/../.env')[0],404)
        self.assertEqual(self.request('/offline/open-result')[0],404)

    def test_capacity_is_friendly_recorded_stays_available_and_expired_state_is_preserved(self):
        self.sessions.max_sessions=1
        one=self.new_live();self.assertEqual(one[0],303)
        full=self.request('/live/new');self.assertEqual(full[0],429)
        self.assertIn('Explore the recorded experience',full[2]);self.assertNotIn('Set-Cookie',full[1])
        self.assertEqual(self.request('/recorded-evidence')[0],200)
        with self.sessions.db:self.sessions.db.execute('UPDATE sessions SET expires=0')
        self.assertEqual(self.new_live()[0],303)
        self.assertEqual(self.sessions.db.execute('select count(*) from sessions').fetchone()[0],2)
        self.assertEqual(self.sessions.db.execute('select count(*) from usage').fetchone()[0],0)

    def test_cumulative_usage_limit_refuses_without_recording_an_extra_attempt(self):
        from shop import Refused
        self.sessions.max_runs=1;self.sessions.reserve('intent')
        with self.assertRaises(Refused):self.sessions.reserve('intent')
        self.assertEqual(self.sessions.db.execute('select count(*) from usage').fetchone()[0],1)

    def test_public_https_origin_produces_secure_buyer_session_cookie(self):
        self.sessions.origin='https://demo.example'
        status,headers,_=self.new_live()
        self.assertEqual(status,303)
        cookie=headers['Set-Cookie']
        self.assertIn('; Secure',cookie);self.assertIn('; HttpOnly',cookie);self.assertIn('SameSite=Strict',cookie)

    def test_live_return_keeps_the_existing_cart_and_does_not_create_a_session(self):
        cookie=self.sessions.new();row=self.sessions.record(cookie)
        app=self.sessions.draft(row,'Please find black shoes under $250')
        before=app.s.snapshot(app.task)
        headers={'Cookie':'conversation_judge='+cookie}
        status,response,_=self.request('/conversation',headers=headers)
        self.assertEqual(self.request('/agent',headers=headers)[1]['Location'],'/visits/1/?mode=live')
        self.assertEqual(status,303);self.assertEqual(response['Location'],'/visits/1/?mode=live')
        self.assertNotIn('Set-Cookie',response)
        self.assertIn("fetch('/conversation?panel=1')",self.request(response['Location'],headers=headers)[2])
        state=json.loads(self.request('/conversation-state',headers=headers)[2])
        self.assertEqual(state['cart_id'],before['cart_id']);self.assertEqual(state['version'],before['version'])
        self.assertEqual(self.sessions.db.execute('select count(*) from sessions').fetchone()[0],1)
        self.assertEqual(app.s.snapshot(app.task)['intent'],before['intent'])

class HostingConfigTests(unittest.TestCase):
    def test_hosted_port_https_origin_and_limits_are_explicit(self):
        import os
        from unittest.mock import patch
        from experience import parse_args
        with patch.dict(os.environ,{'PORT':'10000','PUBLIC_ORIGIN':'https://demo.example','MAX_LIVE_RUNS':'12','MAX_ACTIVE_SESSIONS':'8'},clear=True):
            args=parse_args(['--host','0.0.0.0'])
        self.assertEqual((args.port,args.origin,args.max_runs,args.max_sessions),(10000,'https://demo.example',12,8))

    def test_public_origin_and_payment_misconfiguration_fail_closed(self):
        import os,contextlib,io
        from unittest.mock import patch
        from experience import parse_args
        for env,args in [({},['--host','0.0.0.0']),({'PUBLIC_ORIGIN':'http://public.example'},[]),({'PUBLIC_ORIGIN':'https://user:secret@demo.example'},[]),({'PAYPAL_CONFIG':'private.env'},[])]:
            with patch.dict(os.environ,env,clear=True),contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):parse_args(args)
