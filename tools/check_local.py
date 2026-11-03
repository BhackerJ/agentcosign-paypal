"""Credential-free startup/API smoke check; never calls a payment provider."""
import argparse,http.cookiejar,json,sys,tempfile,threading,urllib.request,urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
from server import App,handler
from http.server import ThreadingHTTPServer
from paypal_sandbox import SandboxClient

def forbidden(*args,**kwargs):raise AssertionError('Provider calls are forbidden in local smoke check')
SandboxClient.request=forbidden
for scenario in ['walking-width','resolable-work-shoes']:
 with tempfile.TemporaryDirectory() as directory:
  app=App(argparse.Namespace(state=Path(directory),port=0,scenario=scenario,paypal_config=None))
  server=ThreadingHTTPServer(('127.0.0.1',0),handler(app));app.origin='http://127.0.0.1:'+str(server.server_port)
  thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
   entry=json.loads((app.out/'access.private.json').read_text())['url'].replace('http://127.0.0.1:0',app.origin)
   with opener.open(entry) as response:page=response.read().decode()
   assert '<html lang="en">' in page and 'Confirm shopping instructions' in page
   with opener.open(app.origin+'/developer') as response:assert 'Example personal agent' in response.read().decode()
   try:urllib.request.urlopen(app.origin+'/api/purchase');raise AssertionError('API lacked authentication')
   except urllib.error.HTTPError as error:assert error.code==403
   request=urllib.request.Request(app.origin+'/api/purchase',headers={'Authorization':'Bearer '+app.key})
   with urllib.request.urlopen(request) as response:result=json.load(response)
   assert result['intent_confirmation']['status']=='needs_buyer_confirmation' and not result['agent_can_approve']
   assert app.s.db.execute('select count(*) from provider_calls').fetchone()[0]==0
   print(scenario+': English buyer/developer UI, API authentication and pending confirmation verified; provider calls=0')
  finally:server.shutdown();server.server_close();app.s.db.close()
