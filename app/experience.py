"""One-link local report experience: read-only recorded evidence or a new live run."""
import argparse,hashlib,html,json,mimetypes,os,secrets,sys,time
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from http.cookies import SimpleCookie
from http.server import ThreadingHTTPServer
from conversation import conversation_handler,REPORT_BRIDGE
from shop import Refused
ROOT=Path(__file__).resolve().parents[1]
ASSETS=Path(__file__).with_suffix('')
TERMS_VERSION='2026-11-04-v1'

def experience_handler(sessions,replay,evidence=None):
    Base=conversation_handler(sessions,replay)
    terms_hash=hashlib.sha256((ASSETS/'terms.html').read_bytes()).hexdigest()
    with sessions.lock,sessions.db:
        sessions.db.execute('CREATE TABLE IF NOT EXISTS terms_acceptance(session_id TEXT PRIMARY KEY, version TEXT NOT NULL, document_sha256 TEXT NOT NULL, accepted_at REAL NOT NULL)')
    evidence=evidence or ROOT/'evidence'
    class Handler(Base):
        def consent_row(self):
            cookies=SimpleCookie(self.headers.get('Cookie',''))
            return sessions.record(cookies['judge'].value if 'judge' in cookies else '')
        def accepted(self,row):
            with sessions.lock:
                return sessions.db.execute('SELECT 1 FROM terms_acceptance WHERE session_id=? AND version=? AND document_sha256=?',(row['id'],TERMS_VERSION,terms_hash)).fetchone() is not None
        def consent_form(self,row):
            return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Start a live shopper · AgentCoSign</title>'
                    '<body style="max-width:680px;margin:48px auto;padding:0 20px;font:16px/1.6 system-ui"><h1>Start a new live shopper</h1><p>Review the <a href="/demo-terms" target="_blank" rel="noopener">Demo terms and data notice</a> before continuing. Product requirements are processed by the configured model and Channel3. Do not enter personal or payment information.</p><p>We may earn a commission when you buy through product links. This demo places no retailer order or payment.</p><form method="post" action="/accept-terms">'
                    '<input type="hidden" name="csrf" value="'+html.escape(row['csrf'])+'"><input type="hidden" name="version" value="'+TERMS_VERSION+'"><input type="hidden" name="document_sha256" value="'+terms_hash+'">'
                    '<label><input type="checkbox" name="agree" value="yes" required> I have read and agree to the Demo terms.</label><p><button>Agree to terms and start</button></p></form><p>Terms version: '+TERMS_VERSION+'. Your agreement version and time are saved for this session. This does not approve any purchase.</p><a href="/visits/1/?mode=recorded">Return to recorded experience</a></body></html>')
        def do_GET(self):
            path=urlsplit(self.path).path
            if path=='/review-terms':
                try:self.send(200,self.consent_form(self.consent_row()))
                except Refused:self.send(303,location='/live/new')
                return
            if path=='/demo-terms':
                self.send(200,(ASSETS/'terms.html').read_text());return
            if path=='/visits/1/':
                f=replay/'visits/1/index.html'
                if not f.is_file():self.send(404,'Prepared replay unavailable');return
                mode='live' if parse_qs(urlsplit(self.path).query).get('mode')==['live'] else 'recorded'
                bridge=REPORT_BRIDGE if mode=='live' else ''
                data=f.read_text().replace('</body>',bridge+'<link rel="stylesheet" href="/experience.css"><script src="/experience.js" defer></script></body>').encode()
                self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data);return
            if path=='/agent' or (path=='/conversation' and parse_qs(urlsplit(self.path).query).get('panel')!=['1']):
                self.send(303,location='/visits/1/?mode=live');return
            if path=='/':self.send(303,location='/visits/1/?mode=recorded');return
            if path=='/live/new':
                if self.headers.get('Authorization'):self.send(403,'Agent cannot create a buyer session');return
                try:c=sessions.new()
                except Refused as error:
                    self.send(error.status,'<!doctype html><html lang="en"><title>Live sessions unavailable</title><h1>Live sessions temporarily unavailable</h1><p>'+html.escape(error.message)+'</p><p><a href="/">Explore the recorded experience</a></p><p><a href="/visits/1/?mode=live">Return to your existing live session</a></p></html>');return
                body=self.consent_form(sessions.record(c)).encode()
                self.send_response(200);self.set_cookie('judge',c);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body);return
            if path in ('/experience.js','/experience.css','/recorded-evidence'):
                if path=='/recorded-evidence':
                    recorded=json.loads((evidence/'recorded-recovery.json').read_text())
                    payment=json.loads((evidence/'main-payment.json').read_text())
                    # Explicit allowlist: no raw provider responses, state or credentials.
                    data=json.dumps({'recovery':recorded,'payment':{'run':payment['run'],'cart_id':payment['cart_id'],'verification':{k:payment['verification'][k] for k in ('order_id','capture_id','order_status','capture_status','total_cents','currency','payment_verified')},'capture_post_count':payment['capture_post_count'],'merchant_receipt_count':payment['merchant_receipt_count'],'repeat_capture_ids':payment['repeat_capture_ids']}}).encode();content_type='application/json'
                else:
                    f=ASSETS/('experience.js' if path.endswith('.js') else 'experience.css');data=f.read_bytes();content_type=mimetypes.guess_type(str(f))[0]
                self.send_response(200);self.send_header('Content-Type',content_type);self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(data);return
            return super().do_GET()
        def do_POST(self):
            path=urlsplit(self.path).path
            if path=='/accept-terms':
                try:
                    if self.headers.get('Authorization') or self.headers.get('Origin')!=sessions.origin:raise Refused(403,'Buyer consent and same-origin request required')
                    n=int(self.headers.get('Content-Length',0))
                    if not 0<n<4096:raise Refused(400,'Invalid agreement form')
                    f=parse_qs(self.rfile.read(n).decode());row=self.consent_row()
                    if not secrets.compare_digest(f.get('csrf',[''])[0],row['csrf']):raise Refused(403,'Invalid form token')
                    if f.get('agree')!=['yes'] or f.get('version')!=[TERMS_VERSION] or f.get('document_sha256')!=[terms_hash]:raise Refused(400,'Review and agree to the current terms')
                    with sessions.lock,sessions.db:
                        sessions.db.execute('INSERT INTO terms_acceptance VALUES (?,?,?,?) ON CONFLICT(session_id) DO UPDATE SET version=excluded.version,document_sha256=excluded.document_sha256,accepted_at=excluded.accepted_at WHERE version!=excluded.version OR document_sha256!=excluded.document_sha256',(row['id'],TERMS_VERSION,terms_hash,time.time()))
                    self.send(303,location='/visits/1/?mode=live');return
                except Refused as e:self.send(e.status,html.escape(e.message));return
                except (ValueError,UnicodeError):self.send(400,'Invalid agreement form');return
            if path in ('/request','/start-shopper','/confirm','/approve'):
                try:
                    if not self.accepted(self.consent_row()):raise Refused(403,'Agree to the current Demo terms before live use')
                except Refused as e:self.send(e.status,html.escape(e.message)+'<p><a href="/review-terms">Review terms and continue</a></p>');return
            if urlsplit(self.path).path in ('/pay','/capture','/repeat','/check','/refresh'):
                self.send(403,'Payments and payment-provider requests are disabled in this experience. Historical evidence is read-only.');return
            return super().do_POST()
    return Handler

def parse_args(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--state',type=Path,default=Path(os.getenv('STATE_DIR','state/experience')))
    p.add_argument('--replay',type=Path,default=Path(os.getenv('REPLAY_DIR',str(ROOT/'replay'))))
    p.add_argument('--port',type=int,default=int(os.getenv('PORT','64340')))
    p.add_argument('--host',default='127.0.0.1')
    p.add_argument('--origin',default=os.getenv('PUBLIC_ORIGIN'))
    p.add_argument('--max-runs',type=int,default=int(os.getenv('MAX_LIVE_RUNS','40')))
    p.add_argument('--max-sessions',type=int,default=int(os.getenv('MAX_ACTIVE_SESSIONS','200')))
    a=p.parse_args(argv)
    if not 1<=a.port<=65535 or a.max_runs<0 or a.max_sessions<1:p.error('Invalid port or live usage limits')
    if a.host not in ('127.0.0.1','localhost') and not a.origin:p.error('PUBLIC_ORIGIN is required when listening beyond loopback')
    origin=urlsplit(a.origin or f'http://127.0.0.1:{a.port}')
    if origin.scheme not in ('http','https') or not origin.hostname or origin.username or origin.password or origin.path not in ('','/') or origin.query or origin.fragment:p.error('PUBLIC_ORIGIN must be an origin, without credentials or a path')
    if origin.scheme!='https' and origin.hostname not in ('127.0.0.1','localhost'):p.error('Public deployments require HTTPS')
    a.origin=(a.origin or f'http://127.0.0.1:{a.port}').rstrip('/')
    if os.getenv('PAYPAL_CONFIG'):p.error('This experience never accepts PayPal configuration')
    return a

def main():
    sys.path.insert(0,str(ROOT/'tools'))
    from run_channel3_recovery import RecoverySessions
    a=parse_args()
    if not (a.replay/'visits/1/index.html').is_file():raise SystemExit('Prepared sanitized replay required')
    for name in ('recorded-recovery.json','main-payment.json'):
        if not (ROOT/'evidence'/name).is_file():raise SystemExit('Required recorded evidence is missing')
    s=RecoverySessions(a.state,a.origin,catalog_provider='channel3',api_origin=f'http://127.0.0.1:{a.port}',max_runs=a.max_runs,max_sessions=a.max_sessions)
    print('Judge experience: '+a.origin,flush=True)
    ThreadingHTTPServer((a.host,a.port),experience_handler(s,a.replay)).serve_forever()

if __name__=='__main__':main()
