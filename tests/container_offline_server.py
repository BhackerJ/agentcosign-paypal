"""Mount-only acceptance launcher, never copied into the production image.

Synthetic extraction and scripted merchant forms exercise the real HTTP handlers.
No model shopper, Channel3 request or payment is permitted. All outbound DNS and
connections are refused except container loopback.
"""
import os,sys,json,socket,threading,secrets,time,re,urllib.request,http.cookiejar
from pathlib import Path
from urllib.parse import urlencode
sys.path.insert(0,'/app/app')
from judge import Sessions
from experience import experience_handler
from intent_input import extract,explicit_budget
from shop import serve,token_hash,Refused
from shopper import review_cart
from http.server import ThreadingHTTPServer

RUN=os.environ.get('OFFLINE_RUN_ID','offline-container-positive-01')
for key in ('ANTHROPIC_API_KEY','CHANNEL3_API_KEY','PAYPAL_CONFIG'):
    if os.environ.get(key):raise RuntimeError('Offline acceptance refuses provider credentials')
original_connect=socket.socket.connect;original_dns=socket.getaddrinfo

def local_host(host):return host in ('127.0.0.1','localhost','::1')
def guarded_connect(sock,address):
    if not isinstance(address,tuple) or not local_host(address[0]):raise RuntimeError('Outbound connection forbidden in offline acceptance')
    return original_connect(sock,address)
def guarded_dns(host,*args,**kwargs):
    if not local_host(host):raise RuntimeError('Outbound DNS forbidden in offline acceptance')
    return original_dns(host,*args,**kwargs)
socket.socket.connect=guarded_connect;socket.getaddrinfo=guarded_dns

def draft(request):
    if not all(x in request.lower() for x in ('black','leather','pair')):raise Refused(400,'Offline fixture requires one pair of black leather shoes')
    result=extract(request,lambda _: {'budget_cents':explicit_budget(request),'requirements':{'color':'black','material':'leather','unit':'pair'},'evidence':{'color':'black','material':'leather','unit':'pair'},'unsupported':[]})
    result['adaptations'].insert(0,'OFFLINE ACCEPTANCE: synthetic fixture extraction and scripted form actions, not a model or Channel3 run. Buyer approval is a test action. No external services or payment.')
    return result

class OfflineSessions(Sessions):
    def launch(self,row):
        import profile_intent
        app=self.app(row['id']);profile_intent.require(app.s,app.task)
        if app.s.snapshot(app.task)['quote']:raise Refused(409,'Offline quote already exists; inspect the existing cart')
        token=secrets.token_urlsafe(24)
        with app.s.lock,app.s.db:
            app.s.db.execute('UPDATE carts SET visit_hash=?,visit_expires=? WHERE task_id=?',(token_hash(token),time.time()+600,app.task))
        merchant=serve(app.s);threading.Thread(target=merchant.serve_forever,daemon=True).start()
        try:
            opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
            page=opener.open(merchant.origin+'/visit/'+token).read().decode()
            csrf=re.search('name="csrf" value="([^"]+)"',page).group(1)
            data=urlencode({'csrf':csrf,'sku':'work-resolable','quantity':1}).encode()
            opener.open(urllib.request.Request(merchant.origin+'/cart',data,headers={'Origin':merchant.origin})).read()
            app.s.runner_finished(app.task,'done')
            review=review_cart(app)
            assert review['assessment']['intent_aware_quote_policy']['gate']=='allow'
            assert review['assessment']['actual_authorization_gate']['gate']=='insufficient_evidence'
            app.job='OFFLINE ACCEPTANCE: scripted fixture forms and authenticated authorization API completed. Awaiting test buyer approval. Not a model run.'
            (app.out/'job.json').write_text(json.dumps({'message':app.job}))
            (app.out/'offline-review.private.json').write_text(json.dumps(review))
        finally:merchant.shutdown();merchant.server_close()

port=int(os.environ.get('PORT','10000'));origin=os.environ['PUBLIC_ORIGIN']
sessions=OfflineSessions('/var/data/offline-positive',origin,extractor=draft,api_origin=f'http://127.0.0.1:{port}',max_runs=10)
Base=experience_handler(sessions,Path('/app/replay'))
NOTICE='''<script>document.addEventListener('DOMContentLoaded',()=>{const mark=()=>{const h=document.querySelector('.experience-bar strong');if(h&&h.textContent!=='OFFLINE ACCEPTANCE · Synthetic fixtures · No external services')h.textContent='OFFLINE ACCEPTANCE · Synthetic fixtures · No external services';};mark();new MutationObserver(mark).observe(document.body,{childList:true,subtree:true});});</script>'''
class Handler(Base):
    def send(self,status,body='',location=None,cookie=None,json_body=False):
        if not json_body:
            body=body.replace('Configure PayPal sandbox to enable payment; no payment has occurred.','OFFLINE ACCEPTANCE: automated test buyer approval only. External services and payments are disabled.')
            body=body.replace('Below: live CoSign checks, model recovery and buyer decisions. No payment.','Below: offline synthetic authorization and automated test buyer approval. No model, Channel3 or payment.')
            body=body.replace('Find one pair of leather shoes. My maximum is $900 including shipping and tax.','Find one pair of black leather shoes. My maximum is $250.')
            body=body.replace('Channel3 real product data in a test merchant. $10 shipping and 6% tax simulated. No retailer order. Payments disabled.','Offline synthetic fixture catalog. No model, Channel3 or payment calls.')
        return super().send(status,body,location,cookie,json_body)
    def do_GET(self):
        if self.path=='/experience.js':
            data=Path('/app/app/experience/experience.js').read_text().replace('NEW LIVE RUN','NEW OFFLINE TEST RUN').replace('a NEW live Channel3 test cart','a NEW offline synthetic test cart').encode()
            self.send_response(200);self.send_header('Content-Type','application/javascript');self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data);return
        if self.path=='/offline/open-result':
            # Local fixture-only preview; this launcher/route is not in the image.
            saved=Path('/var/data/offline-browser.private.json')
            if not saved.exists():self.send(404,'Offline acceptance has not completed');return
            cookie=json.loads(saved.read_text())['judge_cookie'];sessions.record(cookie)
            self.send_response(303);self.set_cookie('judge',cookie);self.send_header('Location','/visits/1/?mode=live');self.end_headers();return
        if self.path.startswith('/visits/1/'):
            # Same production renderer and bridge, with a visible acceptance-only label.
            from conversation import REPORT_BRIDGE
            from urllib.parse import urlsplit,parse_qs
            live=parse_qs(urlsplit(self.path).query).get('mode')==['live']
            body=Path('/app/replay/visits/1/index.html').read_text().replace('</body>',NOTICE+(REPORT_BRIDGE if live else '')+'<link rel="stylesheet" href="/experience.css"><script src="/experience.js" defer></script></body>')
            self.send(200,body);return
        return super().do_GET()
print('Offline acceptance only: '+RUN,flush=True)
ThreadingHTTPServer(('0.0.0.0',port),Handler).serve_forever()
