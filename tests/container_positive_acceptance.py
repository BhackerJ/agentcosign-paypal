"""Run INSIDE the no-network acceptance container; no external services.
Two phases surround an actual docker restart. Tokens stay in private /var/data.
"""
import argparse,json,sqlite3,http.cookiejar,urllib.request,urllib.error,os
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlencode

class Forms(HTMLParser):
    def __init__(self,html):
        super().__init__();self.forms={};self.current=None;self.feed(html)
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='form':self.current=a.get('action');self.forms[self.current]={}
        if tag=='input' and self.current and 'name' in a:self.forms[self.current][a['name']]=a.get('value','')
    def handle_endtag(self,tag):
        if tag=='form':self.current=None

root=Path('/var/data');state=root/'offline-positive';origin=os.environ['PUBLIC_ORIGIN'];run=os.environ.get('OFFLINE_RUN_ID','offline-container-positive-01')
cookies=http.cookiejar.MozillaCookieJar(str(root/'offline-cookies.private.txt'))
opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))
def get(path,headers=None):return opener.open(urllib.request.Request(origin+path,headers=headers or {}))
def post(path,data,headers=None):
    h={'Origin':origin,'Content-Type':'application/x-www-form-urlencoded',**(headers or {})}
    return opener.open(urllib.request.Request(origin+path,urlencode(data).encode(),headers=h))
def api(sid,key):return json.load(get('/api/purchase',{'Authorization':'Bearer '+key,'X-Agent-Session':sid}))
def identities():
    d=sqlite3.connect(state/'sessions.sqlite');rows=d.execute('select id from sessions').fetchall();d.close();assert len(rows)==1
    sid=rows[0][0];return sid,(state/sid/'agent-key.private.txt').read_text().strip()
def return_same(before,sid,key):
    for path in ('/conversation','/agent'):
        r=get(path);page=r.read().decode();assert r.geturl()==origin+'/visits/1/?mode=live'
        assert "fetch('/conversation?panel=1')" in page
        current=api(sid,key)
        for field in ('cart_id','cart_version','intent'):assert current[field]==before[field]
        if before['quote']:assert current['quote']==before['quote']
def snapshot(sid,key):
    a=api(sid,key);d=sqlite3.connect(state/sid/'cart.sqlite');d.row_factory=sqlite3.Row
    approval=d.execute("select * from approvals where status='approved'").fetchone();assert approval
    q=a['quote'];assert approval['quote_sha256']==q['sha256'] and approval['intent_sha256']==q['intent_sha256'] and approval['cart_version']==a['cart_version']
    assert d.execute('select count(*) from approvals').fetchone()[0]==1
    assert d.execute('select count(*) from provider_calls').fetchone()[0]==0;d.close()
    return {'run':run,'basis':'Synthetic fixture extraction; scripted merchant HTTP forms; automated test buyer approval. Not a real shopper or human approval.','cart_id':a['cart_id'],'cart_version':a['cart_version'],'quote_id':q['quote_id'],'quote_sha256':q['sha256'],'intent_sha256':q['intent_sha256'],'approval_id':approval['approval_id'],'total_cents':q['total_cents'],'eligibility':a['assessment']['intent_aware_quote_policy']['gate'],'authorization':a['assessment']['actual_authorization_gate']['gate'],'intent_confirmed':a['intent_confirmation']['confirmed'],'payment_calls':0}

p=argparse.ArgumentParser();p.add_argument('phase',choices=['before','after']);phase=p.parse_args().phase
if phase=='before':
    assert not (root/'positive-before.json').exists(),'Use fresh state for a new offline acceptance run'
    consent=Forms(get('/live/new').read().decode()).forms['/accept-terms']
    consent['agree']='yes';post('/accept-terms',consent).read()
    panel=get('/conversation?panel=1').read().decode();request=Forms(panel).forms['/request']
    request['request']='Find one pair of black leather shoes. My maximum is $250.'
    buyer=post('/request',request).read().decode();sid,key=identities()
    before=api(sid,key);assert not before['intent_confirmation']['confirmed']
    confirm=Forms(buyer).forms['/confirm'];post('/confirm',confirm).read()
    before=api(sid,key);assert before['intent_confirmation']['confirmed'];return_same(before,sid,key)
    start=Forms(get('/conversation?panel=1').read().decode()).forms['/start-shopper']
    post('/start-shopper',start).read()
    before=api(sid,key);assert before['assessment']['intent_aware_quote_policy']['gate']=='allow'
    assert before['assessment']['actual_authorization_gate']['gate']=='insufficient_evidence'
    assert before['assessment']['buyer_approval']=='not_requested_or_granted'
    buyer=get('/buyer').read().decode();approve=Forms(buyer).forms['/approve']
    try:post('/approve',approve,{'Authorization':'Bearer '+key,'X-Agent-Session':sid});raise AssertionError('Agent gained approval authority')
    except urllib.error.HTTPError as e:assert e.code==403
    post('/approve',approve).read()
    result=snapshot(sid,key);assert result['authorization']=='allow'
    return_same(api(sid,key),sid,key)
    judge_cookie=next(c.value for c in cookies if c.name=='conversation_judge')
    (root/'offline-browser.private.json').write_text(json.dumps({'judge_cookie':judge_cookie}))
    cookies.save(ignore_discard=True,ignore_expires=True)
    (root/'positive-before.json').write_text(json.dumps(result,indent=2)+'\n')
else:
    cookies.load(ignore_discard=True,ignore_expires=True);sid,key=identities();result=snapshot(sid,key)
    before=json.loads((root/'positive-before.json').read_text());assert result==before
    return_same(api(sid,key),sid,key)
    d=sqlite3.connect(state/'sessions.sqlite');assert d.execute('select count(*) from sessions').fetchone()[0]==1;d.close()
    result={**result,'restart_verified':True,'same_cart_return_verified':True,'same_session_count':1,'external_network':'Docker network=none; only container-loopback HTTP was available'}
    (root/'positive-after.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'phase':phase,'cart_id':result['cart_id'],'authorization':result['authorization'],'approval_id':result['approval_id'],'payment_calls':0,'run':result['run']}))
