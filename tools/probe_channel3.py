"""Private feasibility probe: 20 fixed queries, no shopper/model/payment calls.

Run with CHANNEL3_API_KEY in the environment. Never commit the output directory.
Coverage is an integration diagnostic, not accuracy or authorization evidence.
"""
import argparse
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
from channel3 import Client, Channel3Error, evidence

QUERIES = [
 'black leather lace up shoes size 11 wide', 'resoleable black leather shoes',
 'walking shoes size 9 extra wide', 'walking shoes size 10.5 extra wide',
 'black leather shoes under 200 dollars', 'brown leather lace up shoes',
 'black walking shoes', 'white walking shoes', 'wide walking shoes',
 'extra wide walking shoes', 'leather walking shoes', 'suede shoes',
 'black loafers', 'brown loafers', 'black oxford shoes', 'brown derby shoes',
 'resoleable oxford shoes', 'wide black leather shoes',
 'comfortable lace up walking shoes', 'leather shoes size 11',
]


def run(client, out):
    os.umask(0o077)
    out.mkdir(parents=True, exist_ok=False)
    rows = []
    cache = {}
    try:
        for i, query in enumerate(QUERIES, 1):
            products = client.search(query, limit=3)
            facts = []
            for product in products:
                pid = product.get('id')
                if not isinstance(pid, str):
                    raise Channel3Error('Search result missing product ID')
                if pid not in cache:
                    cache[pid] = client.product(pid)
                facts.append(evidence(cache[pid]))
            row = {'query': query, 'products': facts}
            rows.append(row)
            (out/f'query-{i:02}.private.json').write_text(json.dumps(row,indent=2))
            print(f'Query {i}/20: {len(facts)} products',flush=True)
    finally:
        all_facts = [p for row in rows for p in row['products']]
        summary = {'completed_queries':len(rows), 'requested_queries':20,
            'returned_product_occurrences':len(all_facts), 'unique_products':len(cache),
            'selection_mode':'Default resolved details; requested-variant matching not yet tested',
            'coverage_counts':{key:sum(bool(p['selected_options'].get(key)) for p in all_facts) for key in ('size','width','color')},
            'priced_available_offer_occurrences':sum(any(o['price_cents'] is not None and o['available'] is True for o in p['offers']) for p in all_facts),
            'new_payments':0, 'shopper_runs':0,
            'limitations':'Private feasibility diagnostic only. No product correctness labels or approved purchase. Missing shipping, tax, delivery or resoling facts are not filled from the buyer request.'}
        (out/'summary.private.json').write_text(json.dumps(summary,indent=2))


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    try: run(Client(),a.out)
    except Channel3Error as error: sys.exit(str(error))
