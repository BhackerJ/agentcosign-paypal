"""Compare frozen policy outputs with separately authored reviewer labels."""
import sys,json,hashlib,copy
from pathlib import Path
ROOT=Path(__file__).parent;sys.path.insert(0,str(ROOT/'app'))
from evaluate import evaluate_policy
labels=json.loads((ROOT/'evidence/independent-labels.json').read_text());rows=[]
for label in labels['labels']:
 if label['evidence_type'] not in ('new_controlled_candidate_from_existing_task','new_controlled_variant'):continue
 name='resolable-work-shoes' if label.get('variant_of') else label['scenario']
 fixture=json.loads((ROOT/'fixtures'/(name+'.json')).read_text());catalog=json.loads((ROOT/'fixtures'/(name+'-catalog.json')).read_text())
 product=copy.deepcopy(catalog['products'][label.get('variant_of',label['sku'])]);product.update(label.get('candidate_override',{}))
 subtotal=product['price_cents'];total=subtotal+catalog['shipping_cents']+(subtotal*catalog['tax_basis_points']+5000)//10000
 facts={'budget':{'observed_cents':total,'limit_cents':fixture['budget_cents'],'basis':'all_in','limit_basis':'all_in','currency':'USD'},'constraints':[{'key':k,'operator':'lte' if k=='delivery_within_days' else 'eq','required':v,'observed':product.get(k)} for k,v in fixture['requirements'].items()],'quote_complete':True,'buyer_approval_verified':False}
 rows.append({'scenario':label['scenario'],'expected':label['expected_quote_gate'],'budget_only':evaluate_policy(facts,False)['gate'],'intent_aware':evaluate_policy(facts,True)['gate']})
result={'scope':'Independent agent source review; original four not blind, delivery variants labeled before new outputs; not human or holdout. Historical summary labels excluded from these denominators.','labels_sha256':hashlib.sha256((ROOT/'evidence/independent-labels.json').read_bytes()).hexdigest(),'policy_sha256':hashlib.sha256((ROOT/'app/evaluate.py').read_bytes()).hexdigest(),'cases':len(rows),'known_mismatches':sum(r['expected']=='block' for r in rows),'evidence_gaps':sum(r['expected']=='insufficient_evidence' for r in rows),'matching_candidates':sum(r['expected']=='allow' for r in rows),'intent_disagreements':sum(r['expected']!=r['intent_aware'] for r in rows),'results':rows}
(ROOT/'evidence/independent-evaluation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
