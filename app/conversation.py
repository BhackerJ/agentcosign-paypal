"""Local example personal-agent conversation, backed by existing isolated sessions.
Historical browsing is replay only; current purchases use the existing buyer handler.
"""
import argparse,html,json,mimetypes,secrets
from pathlib import Path
from urllib.parse import urlsplit,unquote
from http.cookies import SimpleCookie
from http.server import ThreadingHTTPServer
from judge import Sessions,judge_handler
from shop import Refused
import profile_intent

STYLE='body{font:17px/1.6 system-ui;background:#edf3ef;color:#183d32;max-width:1100px;margin:30px auto;padding:20px}article,details{background:white;border:1px solid #cfddd4;border-radius:15px;padding:22px;margin:18px 0}small{color:#526b60}iframe{width:100%;border:1px solid #cfddd4;border-radius:10px}button{background:#17664d;color:white;border:0;border-radius:8px;font:inherit;padding:12px}textarea{width:95%;font:inherit}code{overflow-wrap:anywhere}'


REPORT_BRIDGE = r"""<script>
(async()=>{
 const response=await fetch('/conversation?panel=1');
 const doc=new DOMParser().parseFromString(await response.text(),'text/html');
 const panel=document.createElement('section');panel.id='cosign-report-panel';
 panel.className='flex flex-col gap-3 border-t border-border pt-3';
 const title=document.createElement('h3');title.className='text-label text-muted';title.textContent='Current sandbox recovery · separate from historical replay';panel.append(title);
 const note=document.createElement('p');note.className='text-label text-muted';note.textContent='Historical messages above are unchanged. Below: live CoSign checks, model recovery and buyer decisions. No payment.';panel.append(note);
 for(const article of doc.querySelectorAll('article'))panel.append(article);

 const css=document.createElement('style');css.textContent=`#cosign-report-panel article{margin:0;padding:0;border:0;background:transparent}#cosign-report-panel article>small,#cosign-report-panel article>p,#cosign-report-panel article>h2{display:none}#cosign-report-panel #messages p{margin:0 0 12px;padding:8px 12px;border-radius:var(--radius-ctl);background:var(--color-surface-sunk);font:inherit}#cosign-report-panel #messages b{display:block;font-size:var(--text-label);color:var(--color-muted);font-weight:400}#cosign-report-panel textarea{width:100%;min-height:72px;padding:8px;border:1px solid var(--color-border);border-radius:var(--radius-ctl);font:inherit;background:var(--color-surface)}#cosign-report-panel button{font:inherit;padding:8px 12px;border:1px solid var(--color-border-strong);border-radius:var(--radius-ctl);background:var(--color-surface-sunk);color:var(--color-text);cursor:pointer}#cosign-report-panel button:disabled{opacity:.5;cursor:default}#cosign-report-panel iframe{display:block;width:100%;border:0;background:transparent}#cosign-report-panel iframe[hidden]{display:none}`;document.head.append(css);
 for(const iframe of panel.querySelectorAll('iframe:not([hidden])')){
  iframe.style.height='420px';
  iframe.addEventListener('load',()=>{
   const d=iframe.contentDocument;if(!d)return;
   const root=getComputedStyle(document.documentElement);
   for(const name of ['--color-text','--color-muted','--color-surface','--color-surface-sunk','--color-border','--color-border-strong','--radius-ctl','--text-body','--text-body--line-height'])d.documentElement.style.setProperty(name,root.getPropertyValue(name));
   const style=d.createElement('style');style.textContent=`body{margin:0!important;padding:0!important;background:transparent!important;color:var(--color-text)!important;font-family:system-ui!important;font-size:var(--text-body)!important;line-height:var(--text-body--line-height)!important;max-width:none!important}body>small,body>h1,body>p,body>aside{display:none!important}section{margin:0 0 12px!important;padding:12px!important;border:1px solid var(--color-border)!important;border-radius:var(--radius-ctl)!important;background:var(--color-surface-sunk)!important}h2,h3{font-size:14px!important;line-height:20px!important;margin:0 0 8px!important}p,ul{margin:6px 0!important}small{font-size:12px!important;color:var(--color-muted)!important;overflow-wrap:anywhere}button{font:inherit!important;font-weight:500!important;padding:8px 12px!important;border:1px solid var(--color-border-strong)!important;border-radius:var(--radius-ctl)!important;background:var(--color-text)!important;color:var(--color-surface)!important;width:100%!important}details{font-size:12px}a{color:inherit!important}form+small{display:block;margin-top:6px}`;d.head.append(style);
   const details=d.createElement('details'),summary=d.createElement('summary');summary.textContent='Request and evidence';details.append(summary);
   const first=d.querySelector('section');if(first&&first.querySelector('button')===null){first.replaceWith(details);details.append(first);}
   const resize=()=>{iframe.style.height=Math.min(640,Math.max(160,d.body.scrollHeight+12))+'px';};resize();new ResizeObserver(resize).observe(d.body);
  });
 }

 let started=false;const mount=()=>{const chat=document.querySelector('[data-slot="chat"]');if(chat&&!chat.contains(panel))chat.append(panel);if(chat&&!started){started=true;for(const script of doc.querySelectorAll('script')){const active=document.createElement('script');active.textContent=script.textContent;document.body.append(active);}}};
 mount();new MutationObserver(mount).observe(document.body,{childList:true,subtree:true});
})();</script>"""

def conversation_handler(sessions,replay):
    Base=judge_handler(sessions)
    class Handler(Base):
        def parse_request(self):
            ok=super().parse_request()
            if ok:
                cookies=SimpleCookie(self.headers.get('Cookie',''))
                mapped='; '.join(name+'='+cookies['conversation_'+name].value for name in ('judge','buyer') if 'conversation_'+name in cookies)
                if 'Cookie' in self.headers: del self.headers['Cookie']
                if mapped:self.headers['Cookie']=mapped
            return ok
        def set_cookie(self,name,value):
            return super().set_cookie('conversation_'+name,value)
        def send(self,status,body='',location=None,cookie=None,json_body=False):
            if not json_body:body=body.replace('Return to your personal agent','Return to conversation').replace('href="/agent"','href="/conversation"')
            return super().send(status,body,location,cookie,json_body)
        def row(self):
            c=SimpleCookie(self.headers.get('Cookie',''))
            return sessions.record(c['judge'].value if 'judge' in c else '')
        def do_GET(self):
            path=urlsplit(self.path).path
            if path in ('/','/conversation') and 'panel=1' not in self.path:
                self.send(303,location='/visits/1/');return
            if path.startswith(('/replay/','/visits/','/assets/','/pictures/')) or path=='/view.json':
                relative=unquote(path[len('/replay/'):] if path.startswith('/replay/') else path.lstrip('/')) or 'index.html'
                f=(replay/relative).resolve()
                if f.is_dir():f=f/'index.html'
                if not f.is_relative_to(replay.resolve()) or not f.is_file() or f.suffix not in ('.html','.json','.js','.css','.png','.jpg','.svg','.woff','.woff2'):
                    self.send(404,'Replay asset unavailable');return
                data=f.read_bytes()
                if f.suffix=='.html' and path.startswith('/visits/'):
                    data=data.replace(b'</body>', REPORT_BRIDGE.encode()+b'</body>')
                if f.suffix=='.html' and path.startswith('/replay/'):data=data.replace(b'="/assets/',b'="/replay/assets/').replace(b'data-report-root="/"',b'data-report-root="/replay/"')
                self.send_response(200);self.send_header('Content-Type',mimetypes.guess_type(str(f))[0] or 'application/octet-stream');self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data);return
            if path not in ('/','/conversation','/conversation-state'):return super().do_GET()
            try:
                if self.headers.get('Authorization'):raise Refused(403,'Agent keys do not grant conversation or buyer access')
                try:row=self.row()
                except Refused:
                    if self.headers.get('Cookie') and 'judge=' in self.headers['Cookie']:raise
                    if path=='/conversation-state':raise Refused(403,'Buyer session required')
                    c=sessions.new();self.send_response(303);self.set_cookie('judge',c);self.send_header('Location','/conversation?panel=1');self.end_headers();return
                try:app=sessions.app(row['id'])
                except Refused:app=None
                if path=='/conversation-state':
                    result={'phase':'request_needed','messages':[]}
                    if app:
                        st=app.s.snapshot(app.task);tracefile=app.out/'shopper-live.private.json';resultfile=app.out/'shopper-result.json'
                        trace=json.loads(tracefile.read_text()) if tracefile.exists() else json.loads(resultfile.read_text())['actions'] if resultfile.exists() else []
                        job=app.job
                        if st['quote']:
                            with app.s.lock:
                                approved=app.s.db.execute("SELECT expires_at FROM approvals WHERE task_id=? AND quote_sha256=? AND cart_version=? AND intent_sha256=? AND status='approved'",(app.task,st['quote']['sha256'],st['version'],st['quote']['intent_sha256'])).fetchone()
                            if approved:
                                job='Exact purchase approved by the buyer. Payments are disabled; no payment has occurred.' if approved['expires_at']>app.s.clock() else 'Buyer approval is recorded, but has expired. No current permission to pay; payments remain disabled.'
                        messages=[{'role':'You','text':st['intent']['request']},{'role':'Example personal agent','text':job}]
                        review_number=0
                        for action in trace:
                            a=action['action'];gate=action.get('authorization_gate')
                            if gate:
                                review_number+=1
                                if not action.get('requirement_evidence'):
                                    saved=app.out/f'recovery-review-{review_number}.private.json'
                                    if saved.exists():
                                        old=json.loads(saved.read_text())
                                        action={**action,'requirement_evidence':[{'field':k,'required':v,'observed':line.get(k)} for line in old['quote']['lines'] for k,v in st['intent']['requirements'].items()]}
                                facts='; '.join(str(f['field'])+': required '+str(f['required'])+', observed '+('not documented' if f['observed'] is None else str(f['observed'])) for f in action.get('requirement_evidence',[]))
                                messages.append({'role':'AgentCoSign','text':'Quote check: '+gate+'. '+facts+' '+action.get('authorization_feedback','')})
                            elif a.get('action')=='click':messages.append({'role':'Example personal agent · browser action','text':a.get('name','')})
                        result={'phase':'confirmed' if profile_intent.status(app.s,app.task)['confirmed'] else 'confirm_intent','cart_id':st['cart_id'],'version':st['version'],'messages':messages,'quote_ready':bool(st['quote']), 'busy':bool(getattr(app,'queued',False) or (app.worker and app.worker.is_alive()))}
                    self.send(200,json.dumps(result),json_body=True);return
                esc=html.escape
                body='<!doctype html><html lang="en"><meta charset="utf-8"><title>Example personal agent · AgentCoSign</title><style>'+STYLE+'</style><small>EXAMPLE PERSONAL-AGENT CLIENT · LOCAL SANDBOX</small><h1>One conversation. Your purchase decisions.</h1><p>Your agent shops. AgentCoSign checks. Only you confirm and approve.</p>'
                body+='<details open><summary><b>Existing real-store shopping replay · October 14</b></summary><p>Historical run: 20261014T071916Z-openclaw-3b0661 · nisolo.com. Original captured pages and agent messages. Use the timeline to inspect browsing, product details and cart.</p><iframe title="Historical real-store shopping replay" height="650" src="/visits/1/"></iframe><p><b>Post-run finding:</b> resoling remained unverified. This historical run continued; AgentCoSign did not block it live. The excerpt ends before private checkout fields. It is not the current cart below.</p></details>'
                body+='<article><small>CURRENT CONVERSATION · SEPARATE SANDBOX CART</small><p>Channel3 real product data in a test merchant. $10 shipping and 6% tax simulated. No retailer order. Payments disabled.</p><p>Recovery challenge: initial candidate and retry instruction assigned; controller reopens the cart; model chooses its replacement through browser controls.</p><div id="messages"></div><small id="cart"></small></article>'
                if not app:body+='<article><form method="post" action="/request" target="buyer-card"><input type="hidden" name="csrf" value="'+row['csrf']+'"><label>Message your example agent<textarea required name="request" rows="3">Find one pair of leather shoes. My maximum is $900 including shipping and tax.</textarea></label><button>Send purchase request</button></form></article>'
                body+='<article><h2>Your confirmation and approval card</h2><p>This card is rendered by the existing buyer backend. Agent credentials cannot confirm, approve or pay.</p><iframe name="buyer-card" id="buyer-card" title="AgentCoSign buyer confirmation and exact quote approval" height="720"'+(' src="/buyer"' if app else '')+'></iframe></article>'
                body+='<article><form method="post" action="/start-shopper" target="runner"><input type="hidden" name="csrf" value="'+row['csrf']+'"><button id="start" disabled>Start example shopper after confirming instructions</button></form><iframe hidden name="runner"></iframe><p id="notice"></p></article>'
                body+='''<script>let lastPhase='',lastVersion=-1,lastBusy=false;document.querySelector('#buyer-card').addEventListener('load',()=>{const doc=document.querySelector('#buyer-card').contentDocument;if(doc)for(const a of doc.querySelectorAll('a[href="/agent"],a[href="/conversation"]')){a.href='/conversation';a.target='_top';}});async function poll(){try{const r=await fetch('/conversation-state');if(!r.ok)return;const d=await r.json();const box=document.querySelector('#messages');box.replaceChildren();for(const m of d.messages){const p=document.createElement('p'),b=document.createElement('b');b.textContent=m.role+': ';p.append(b,document.createTextNode(m.text));box.append(p);}document.querySelector('#cart').textContent=d.cart_id?'Current cart '+d.cart_id+' · version '+d.version:'';document.querySelector('#start').disabled=d.phase!=='confirmed'||d.busy||d.quote_ready;document.querySelector('#notice').textContent=d.busy?'Real shopper is running. Actions and checks appear here.':'';if((lastBusy&&!d.busy)||(d.phase==='confirm_intent'&&lastPhase==='request_needed'))document.querySelector('#buyer-card').src='/buyer';lastBusy=!!d.busy;lastPhase=d.phase;}catch(e){document.querySelector('#notice').textContent='Connection interrupted. Cart preserved; reload to reconnect.';}}poll();setInterval(poll,2000);</script></html>'''
                self.send(200,body)
            except Refused as e:self.send(e.status,html.escape(e.message))
    return Handler

if __name__=='__main__':
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
    from run_channel3_recovery import RecoverySessions
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--replay',type=Path,required=True);p.add_argument('--port',type=int,default=64331);a=p.parse_args()
    if not (a.replay/'view.json').exists():p.error('Prepared sanitized replay required')
    origin=f'http://127.0.0.1:{a.port}';s=RecoverySessions(a.state,origin,catalog_provider='channel3');print('Local conversation: '+origin,flush=True)
    ThreadingHTTPServer(('127.0.0.1',a.port),conversation_handler(s,a.replay)).serve_forever()
