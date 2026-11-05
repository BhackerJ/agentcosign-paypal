import tempfile,threading,http.client,json,unittest
from pathlib import Path
from http.server import ThreadingHTTPServer
from judge import Sessions
from conversation import conversation_handler
from test_judge import draft
class ConversationTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();root=Path(self.tmp.name);self.replay=root/'replay';self.replay.mkdir();(self.replay/'view.json').write_text('{}');(self.replay/'index.html').write_text('Historical replay')
  self.sessions=Sessions(root/'state','http://127.0.0.1',extractor=draft);self.server=ThreadingHTTPServer(('127.0.0.1',0),conversation_handler(self.sessions,self.replay));threading.Thread(target=self.server.serve_forever,daemon=True).start()
 def tearDown(self):
  self.server.shutdown();self.server.server_close();self.sessions.pool.shutdown();self.sessions.db.close();self.tmp.cleanup()
 def get(self,path,headers=None):
  c=http.client.HTTPConnection('127.0.0.1',self.server.server_port);c.request('GET',path,headers=headers or {});r=c.getresponse();v=(r.status,dict(r.getheaders()),r.read().decode());c.close();return v
 def test_cookie_isolation_and_agent_cannot_read_conversation(self):
  code,h,_=self.get('/conversation?panel=1',{'Cookie':'judge=other-demo-cookie'});self.assertEqual(code,303);self.assertIn('conversation_judge=',h['Set-Cookie']);cookie=h['Set-Cookie'].split(';')[0]
  self.assertEqual(self.get('/conversation-state')[0],403);self.assertEqual(self.get('/conversation-state',{'Cookie':cookie,'Authorization':'Bearer fake'})[0],403)
  code,_,body=self.get('/conversation-state',{'Cookie':cookie});self.assertEqual(code,200);self.assertEqual(json.loads(body)['phase'],'request_needed')
  self.assertIn('target="buyer-card"',self.get('/conversation?panel=1',{'Cookie':cookie})[2])
 def test_replay_paths_cannot_read_private_files(self):
  self.assertEqual(self.get('/view.json')[0],200);self.assertEqual(self.get('/replay/')[0],200)
  self.assertEqual(self.get('/replay/%2e%2e/private.env')[0],404);self.assertEqual(self.get('/replay/%2e%2e/state/sessions.sqlite')[0],404)
