"""Minimize a completed recovery into read-only display evidence; no credentials."""
import argparse,json,sqlite3,hashlib
from pathlib import Path

def export(state):
    result=json.loads((state/'shopper-result.json').read_text())
    db=sqlite3.connect('file:'+str((state/'cart.sqlite').resolve())+'?mode=ro',uri=True)
    db.row_factory=sqlite3.Row
    cart=db.execute('select * from carts').fetchone();quote=json.loads(cart['quote'])
    assert cart['cart_id']==result['cart_id'] and all(a['cart_id']==result['cart_id'] for a in result['actions'])
    approval=db.execute("select * from approvals where status='approved' and quote_sha256=? and cart_version=? and intent_sha256=?",(quote['sha256'],cart['version'],quote['intent_sha256'])).fetchone()
    assert approval and approval['total_cents']==quote['total_cents']
    calls=db.execute('select count(*) from provider_calls').fetchone()[0];assert calls==0
    intent=json.loads((state/'intent.json').read_text())
    events=[{'action':a['action']['action'],'name':a['action'].get('name',''),'cart_version':a['cart_version'],'elapsed_seconds':a['elapsed_seconds'],'decision':a.get('authorization_gate'),'facts':a.get('requirement_evidence',[])} for a in result['actions']]
    db.close()
    return {'run':'report-recorded-02','cart_id':result['cart_id'],'request':intent['request'],'events':events,'approval':{'quote_id':approval['quote_id'],'quote_sha256':approval['quote_sha256'],'intent_sha256':approval['intent_sha256'],'cart_version':approval['cart_version'],'total_cents':approval['total_cents'],'status':'historical_approved_now_expired','payment_calls':calls},'source_result_sha256':hashlib.sha256((state/'shopper-result.json').read_bytes()).hexdigest()}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():p.error('Output already exists; preserve prior evidence')
    a.out.write_text(json.dumps(export(a.state),indent=2)+'\n')
