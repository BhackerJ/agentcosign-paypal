"""Session-isolated judge entry. Existing payment logic remains in server/payments."""
import argparse, html, json, os, secrets, sqlite3, threading, time
from concurrent.futures import ThreadPoolExecutor
from http.cookies import SimpleCookie
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from server import App, handler, STYLE
from shop import Refused, token_hash
from intent_input import extract
import profile_intent


class Sessions:
    def __init__(self, state, origin, paypal_config=None, extractor=extract, slots=1, max_runs=40, api_origin=None):
        os.umask(0o077)
        self.state, self.origin, self.paypal_config = Path(state), origin.rstrip('/'), paypal_config
        if urlsplit(origin).scheme != 'https' and urlsplit(origin).hostname not in ('localhost','127.0.0.1'):
            raise ValueError('Public deployment requires HTTPS origin')
        self.state.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock(); self.apps = {}; self.extractor = extractor
        self.pool = ThreadPoolExecutor(max_workers=slots)
        self.max_runs = max_runs
        self.api_origin = api_origin or self.origin
        self.db = sqlite3.connect(self.state/'sessions.sqlite', check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, cookie_hash TEXT UNIQUE, csrf TEXT, expires REAL, runs INTEGER DEFAULT 0); CREATE TABLE IF NOT EXISTS usage(id INTEGER PRIMARY KEY, kind TEXT);')

    def new(self):
        with self.lock, self.db:
            if self.db.execute('SELECT count(*) FROM sessions').fetchone()[0] >= 200:
                raise Refused(429, 'Session capacity reached. Please contact the demo owner.')
            sid, cookie, csrf = secrets.token_hex(16), secrets.token_urlsafe(32), secrets.token_urlsafe(24)
            self.db.execute('INSERT INTO sessions VALUES (?,?,?,?,0)', (sid, token_hash(cookie), csrf, time.time()+86400))
            return cookie

    def record(self, cookie):
        with self.lock:
            row = self.db.execute('SELECT * FROM sessions WHERE cookie_hash=? AND expires>?', (token_hash(cookie),time.time())).fetchone()
        if not row: raise Refused(403, 'Judge session expired. Start a new session; an existing order must not be retried as a new purchase.')
        return dict(row)

    def reserve(self, kind):
        with self.lock, self.db:
            if self.db.execute('SELECT count(*) FROM usage WHERE kind=?',(kind,)).fetchone()[0] >= self.max_runs:
                raise Refused(429, 'Demo usage limit reached. No result was generated. Contact the demo owner.')
            self.db.execute('INSERT INTO usage(kind) VALUES (?)',(kind,))

    def app(self, sid):
        with self.lock:
            if sid not in self.apps:
                state = self.state/sid
                if not (state/'intent.json').exists(): raise Refused(409, 'Submit a shopping request first')
                intent = json.loads((state/'intent.json').read_text())
                fixture = dict(intent, id='natural-language', historical_run='new-judge-session',
                    source_disclosure='New buyer-written request. Model-extracted draft, confirmed separately by the buyer.', challenge_first_sku=None)
                app = App(argparse.Namespace(state=state, port=0, scenario='resolable-work-shoes', paypal_config=self.paypal_config, fixture=fixture))
                _, walking_catalog = profile_intent.load_fixture('walking-width')
                app.s.catalog['products'].update(walking_catalog['products'])
                app.buyer_review_path = '/buyer'
                app.origin = self.origin
                app.agent_api_origin = self.api_origin
                app.agent_headers = {'X-Agent-Session':sid}
                app.record_video = False
                app.shopper_max_tokens = 80000
                app.shopper_max_seconds = 180
                app.job = 'Ready. Confirm instructions on the AgentCoSign buyer page before shopping.'
                if (state/'job.json').exists():
                    app.job = json.loads((state/'job.json').read_text())['message']
                self.apps[sid] = app
            return self.apps[sid]

    def draft(self, row, request):
        with self.lock:
            target = self.state/row['id']
            if (target/'intent.json').exists(): raise Refused(409, 'This session already has a request. Start a new session for another task.')
            self.reserve('intent')
            intent = self.extractor(request)
            target.mkdir(exist_ok=True)
            (target/'intent.json').write_text(json.dumps(intent), encoding='utf-8')
            return self.app(row['id'])

    def launch(self, row):
        app = self.app(row['id'])
        profile_intent.require(app.s, app.task)
        with self.lock:
            if getattr(app,'queued',False) or (app.worker and app.worker.is_alive()): raise Refused(409,'Shopper already queued or running')
            if app.purchase(): raise Refused(409,'An order already exists. Review its status before further actions.')
            self.reserve('shopper')
            app.queued = True; app.job = 'Queued for the example browser shopper.'
            def work():
                try:
                    app.launch()
                    app.worker.join()
                except Exception:
                    app.job = 'Shopper could not start. Cart preserved; retry from the example agent.'
                finally: app.queued = False
            self.pool.submit(work)


def judge_handler(sessions):
    def cookie(h):
        c = SimpleCookie(h.headers.get('Cookie','')); return c['judge'].value if 'judge' in c else ''
    def resolve(h):
        if h.path.startswith('/api/'):
            sid = h.headers.get('X-Agent-Session','')
            with sessions.lock:
                row = sessions.db.execute('SELECT id FROM sessions WHERE id=? AND expires>?',(sid,time.time())).fetchone()
            if not row: raise Refused(403,'Agent session required')
            app = sessions.app(sid)
            if not secrets.compare_digest(h.headers.get('Authorization',''),'Bearer '+app.key): raise Refused(403,'Agent credential required')
            return app
        row = sessions.record(cookie(h)); return sessions.app(row['id'])
    Base = handler(None, resolve)
    class JudgeHandler(Base):
        def session(self):
            # Buyer cookie belongs to this isolated Store; the agent key cannot exchange it.
            return super().session()

        def send(self, status, body='', location=None, cookie=None, json_body=False):
            if location == '/': location = '/buyer'
            if location == '/developer': location = '/agent'
            if not json_body:
                if '<title>AgentCoSign' in body:
                    body += '<p><a href="/agent">Return to your personal agent</a></p>'
                body = body.replace('href="/"','href="/buyer"')
                body = body.replace('Shopper stopped. Cart preserved; resume from the developer console.','Shopper stopped. Cart preserved; return to the example agent to resume.')
                body = body.replace('restart the local service and open the new one-use buyer URL from your private state directory.','return to the example agent and open the buyer page again.')
            self.send_response(status)
            self.send_header('Content-Length', str(len(body.encode())))
            self.send_header('Content-Type','application/json' if json_body else 'text/html; charset=utf-8')
            self.send_header('Cache-Control','no-store'); self.send_header('Referrer-Policy','same-origin')
            self.send_header('X-Content-Type-Options','nosniff')
            if location: self.send_header('Location',location)
            if cookie: self.set_cookie('buyer',cookie)
            self.end_headers(); self.wfile.write(body.encode())

        def set_cookie(self, name, value):
            secure = '; Secure' if sessions.origin.startswith('https:') else ''
            self.send_header('Set-Cookie',f'{name}={value}; Path=/; HttpOnly; SameSite=Strict'+secure)

        def do_GET(self):
            path = urlsplit(self.path).path
            if path in ('/health',): self.send(200,'ok'); return
            if path.startswith('/api/') or path in ('/buyer/paypal-return','/buyer/paypal-cancel'):
                # Return page is neutral and cannot authorize a purchase, even without a cookie.
                if path.startswith('/buyer/paypal-'):
                    self.send(200,'<h1>Return to your purchase</h1><p>This return does not prove payment.</p><a href="/buyer">Continue to buyer review</a>'); return
                return super().do_GET()
            try:
                if path in ('/', '/agent'):
                    try: row = sessions.record(cookie(self))
                    except Refused:
                        if cookie(self): raise
                        c = sessions.new(); self.send_response(303);self.set_cookie('judge',c);self.send_header('Location','/');self.end_headers();return
                    esc = html.escape
                    body = '<!doctype html><html lang="en"><meta charset="utf-8"><title>Example personal agent</title><style>'+STYLE+'</style><small>EXAMPLE PERSONAL-AGENT CLIENT · SANDBOX</small><h1>Tell your agent what you need.</h1><p>One pair of shoes. Your agent shops; AgentCoSign asks you to confirm and approve.</p>'
                    try: app = sessions.app(row['id'])
                    except Refused:
                        body += '<form method="post" action="/request"><input type="hidden" name="csrf" value="'+row['csrf']+'"><label>Shopping request<br><textarea name="request" rows="5" cols="60" maxlength="2000" required placeholder="One pair of black leather lace-up shoes, size 11 wide, resoleable, under $250, within 14 days."></textarea></label><p>Include one explicit USD maximum. Fixed test shipping and tax are included in that maximum.</p><button>Send draft to AgentCoSign</button></form>'
                    else:
                        busy = getattr(app,'queued',False) or (app.worker and app.worker.is_alive())
                        if busy: body += '<meta http-equiv="refresh" content="3">'
                        body += '<section><p>'+esc(app.s.snapshot(app.task)['intent']['request'])+'</p><p>'+esc(app.job)+'</p><a href="/buyer">Open AgentCoSign approval and receipt</a></section>'
                        if profile_intent.status(app.s,app.task)['confirmed'] and not app.purchase() and not busy:
                            body += '<form method="post" action="/start-shopper"><input type="hidden" name="csrf" value="'+row['csrf']+'"><button>Start / resume example shopper</button></form>'
                    self.send(200,body+'</html>');return
                if path == '/buyer':
                    app = resolve(self)
                    try: app.s.buyer_session(self.session())
                    except Refused:
                        token = app.s.buyer_access(app.task)
                        self.send(303,location='/buyer',cookie=app.s.buyer_exchange(token));return
                    self.path = '/'
                    return super().do_GET()
                raise Refused(404,'Unknown page')
            except Refused as e: self.send(e.status,html.escape(e.message))

        def do_POST(self):
            # Supplying an agent token never grants a buyer operation, even alongside cookies.
            if self.headers.get('Authorization') and self.path != '/api/review':
                self.send(403,'Agent cannot confirm, approve, or pay');return
            if self.path == '/api/review': return super().do_POST()
            try:
                if self.headers.get('Origin') != sessions.origin: raise Refused(403,'Origin rejected')
                if self.path in ('/request','/start-shopper'):
                    n = int(self.headers.get('Content-Length',0))
                    if not 0 < n < 8192: raise Refused(400,'Invalid request')
                    f = parse_qs(self.rfile.read(n).decode()); row = sessions.record(cookie(self))
                    if not secrets.compare_digest(f.get('csrf',[''])[0],row['csrf']): raise Refused(403,'Invalid form token')
                    if self.path == '/request': sessions.draft(row,f.get('request',[''])[0])
                    else: sessions.launch(row)
                    self.send(303,location='/buyer' if self.path == '/request' else '/agent');return
                if self.path not in ('/confirm','/approve','/refresh','/pay','/check','/capture','/repeat'):
                    raise Refused(404,'Unknown action')
                return super().do_POST()
            except Refused as e: self.send(e.status,html.escape(e.message)+'<p><a href="/agent">Return to your agent</a></p>')
            except (ValueError,KeyError): self.send(400,'Invalid request')
            except Exception: self.send(503,'Request stopped. No approval or payment was granted. Return to the example agent.')
    return JudgeHandler


def main():
    p = argparse.ArgumentParser();p.add_argument('--state',type=Path,default=Path('state/judges'));p.add_argument('--port',type=int,default=int(os.getenv('PORT','64300')))
    p.add_argument('--origin',default=os.getenv('PUBLIC_ORIGIN'));p.add_argument('--paypal-config',type=Path,default=os.getenv('PAYPAL_CONFIG') or None);p.add_argument('--host',default='127.0.0.1')
    a = p.parse_args(); sessions = Sessions(a.state,a.origin or f'http://127.0.0.1:{a.port}',a.paypal_config, api_origin=f'http://127.0.0.1:{a.port}')
    print('Judge entry: '+sessions.origin,flush=True)
    ThreadingHTTPServer((a.host,a.port),judge_handler(sessions)).serve_forever()

if __name__ == '__main__': main()
