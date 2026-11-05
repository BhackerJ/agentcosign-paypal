"""Prepare a minimized local deployment bundle from a reviewed replay excerpt.

Copies only referenced resources. Fails on credential/contact/path patterns in
structured data or local OCR. Does not contact stores or modify the source.
"""
import argparse,hashlib,json,re,shutil,struct,subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PATTERNS={'credential':r'sk-(?:ant|proj)-[A-Za-z0-9_-]+|Bearer\s+[A-Za-z0-9_-]{15,}|-----BEGIN .*PRIVATE KEY',
          'private_path':r'/Users/|/private/|[A-Z]:\\Users\\',
          'payment_number':r'(?i)(?:card number|credit card number|ccnum|\bPAN\b)[^\n]{0,30}(?:\d[ -]?){13,19}',
          'private_email':r'(?i)(?<![\w.-])[\w.+-]+@(?!nisolo\.com\b|shopify\.com\b|sentry\.io\b)[\w.-]+\.[a-z]{2,}',
          'us_contact':r'(?i)\b\d{1,6}\s+(?:[a-z]+\s+){1,4}(?:street|avenue|road|lane|drive|blvd)\b'}

def check(text,label):
    bad=[kind for kind,pattern in PATTERNS.items() if re.search(pattern,text)]
    if bad:raise ValueError(label+': manual privacy review required ('+', '.join(bad)+'); values omitted')

def png_pixels_only(data):
    assert data[:8]==b'\x89PNG\r\n\x1a\n';out=data[:8];pos=8
    while pos<len(data):
        size=struct.unpack('>I',data[pos:pos+4])[0];kind=data[pos+4:pos+8];chunk=data[pos:pos+size+12]
        if kind in (b'IHDR',b'PLTE',b'tRNS',b'IDAT',b'IEND',b'sRGB',b'gAMA',b'cHRM'):out+=chunk
        pos+=size+12
    return out

def prepare(source,out):
    if out.exists():raise ValueError('Use a fresh output directory; existing bundle is preserved')
    d=json.loads((source/'view.json').read_text());assert len(d['visits'])==1
    visit=d['visits'][0];page=visit['page'];assert page['duration_s']==473
    assert all(f['t']<=473 and f['address'].startswith('nisolo.com/') for f in page['frames'])
    assert all('checkout' not in f['address'].lower() for f in page['frames'])
    # Discard inherited cross-store summary data; preserve the actual visit.
    text=lambda s:{'en':s,'zh':s}
    d['header']={'title':text('Existing shopping replay · October 14 · No payment'),'id':None,'host':'nisolo.com','made':text('October 14, 2026 · historical excerpt')}
    d['store']={'host':'nisolo.com','initial':'N','mark':6,'icon':None}
    lead=d['lead'];lead['done_alone']=0;lead['total']=1
    for step in lead['steps']:step['reached']=0 if step['key']=='checkout' else 1
    lead['lanes']=[{**lane,'count':1 if lane['outcome']=='not_done' else 0,'at_steps':[1,1,1,1,0] if lane['outcome']=='not_done' else [0]*5} for lane in lead['lanes']]
    lead['band_name']=text('One historical excerpt: browsing, product and cart; private checkout excluded')
    lead['wanted']=text('Black leather lace-ups, size 11 Wide, resolable, under $250.')
    # Test identifiers/hashes are retained in evidence, not original template IDs.
    d['findings']=[];d['langs']=['en']
    data=json.dumps(d,ensure_ascii=False);check(data,'view.json')
    replay=out/'replay';(replay/'visits/1').mkdir(parents=True)
    (replay/'view.json').write_text(data+'\n')
    html=(source/'visits/1/index.html').read_text()
    check(html,'report HTML')
    for name in ['index.html','visits/1/index.html']:(replay/name).write_text(html)
    files=set(re.findall(r'(?:src|href)=["\'](/assets/[^"\']+)',html))
    # CSS fonts and lazy renderer imports are included by following local references.
    pending=list(files)
    while pending:
        name=pending.pop();rel=Path(name.lstrip('/'));f=(source/rel).resolve()
        assert f.is_relative_to(source.resolve()) and f.is_file()
        dest=replay/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,dest)
        if f.suffix not in ('.css','.js'):continue
        body=f.read_text();check(body,str(rel))
        for ref in re.findall(r'(?:["\'(])((?:\./|/assets/)[^"\')\s]+\.(?:js|css|woff2?|png|svg))(?:["\')])',body):
            path='/assets/'+ref[2:] if ref.startswith('./') else ref
            if path not in files:files.add(path);pending.append(path)
    pictures=[]
    for frame in page['frames']:
        rel=Path(frame['file']);assert rel.parts[:2]==('pictures','1') and rel.suffix=='.png'
        f=(source/rel).resolve();assert f.is_relative_to(source.resolve())
        target=replay/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(png_pixels_only(f.read_bytes()));pictures.append(target)
    def ocr(f):
        r=subprocess.run(['tesseract',str(f),'stdout'],capture_output=True,text=True,check=True)
        check(r.stdout,str(f.relative_to(out)));return str(f.relative_to(out))
    with ThreadPoolExecutor(max_workers=4) as pool:checked=list(pool.map(ocr,pictures))
    evidence=out/'evidence';evidence.mkdir()
    recovery=json.loads((ROOT/'evidence/recorded-recovery.json').read_text())
    payment=json.loads((ROOT/'evidence/main-payment.json').read_text())
    payment={k:payment[k] for k in ('run','cart_id','verification','capture_post_count','merchant_receipt_count','repeat_capture_ids')}
    payment['verification']={k:payment['verification'][k] for k in ('order_id','capture_id','order_status','capture_status','total_cents','currency','payment_verified')}
    # Source hashes and cart/order IDs are intentional opaque test evidence, not card numbers.
    for name,value in [('recorded-recovery.json',recovery),('main-payment.json',payment)]:
        raw=json.dumps(value,indent=2);(evidence/name).write_text(raw+'\n')
        for kind in ('credential','private_path','private_email'):assert not re.search(PATTERNS[kind],raw),name
    manifest={'source':'Historical Nisolo excerpt, October 14; original captured pixels unchanged','range_seconds':[0,473],'frames':len(pictures),'ocr_checked':len(checked),'removed':['cross-store template metadata','unreferenced assets and images','PNG text/EXIF metadata','private state and browser credentials'],'limits':'Automated/OCR checks support privacy review; merchant imagery/display rights still require owner confirmation before publication. No checkout or payment fields included.','files':{str(f.relative_to(out)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(out.rglob('*')) if f.is_file()}}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Prepared bundle:',out,'frames:',len(pictures),'OCR checked:',len(checked),'files:',len(manifest['files']),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--replay',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();prepare(a.replay,a.out)
