"""Explicit local recovery challenge. Real data/actions; assigned first candidate.

Set CHANNEL3_API_KEY and ANTHROPIC_API_KEY privately. No PayPal configuration.
Use a fresh state directory; this is not a natural-error-rate evaluation.
"""
import argparse
import sys
from pathlib import Path
from http.server import ThreadingHTTPServer
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from judge import Sessions, judge_handler
from shop import Refused

LABEL = 'RECOVERY CHALLENGE: the initial missing-evidence candidate is deliberately assigned. The real shopper chooses the replacement through browser controls. No retailer order or payment.'


class RecoverySessions(Sessions):
    def app(self, sid):
        app = super().app(sid)
        if not getattr(app, 'challenge_wrapped', False):
            original = app.launch
            def launch():
                intent = app.s.snapshot(app.task)['intent']
                if intent['requirements'] != {'material':'leather','unit':'pair'}:
                    raise Refused(409, 'This challenge requires leather shoes with an explicit budget and no other attributes')
                catalog = app.s.catalog
                def within_budget(product):
                    subtotal = product['price_cents']
                    tax = (subtotal*catalog['tax_basis_points']+5000)//10000
                    return subtotal+tax+catalog['shipping_cents'] <= intent['budget_cents']
                bad = [sku for sku,p in catalog['products'].items() if p['material'] is None and p['available'] is True and within_budget(p)]
                good = [sku for sku,p in catalog['products'].items() if p['material'] == 'leather' and p['available'] is True and within_budget(p)]
                if not bad or not good:
                    raise Refused(409, 'Current real data does not support this challenge; no fabricated fallback')
                app.fixture['challenge_first_sku'] = bad[0]
                app.recovery_evidence = True
                app.record_video = getattr(self, 'record_video', False)
                original()
            app.launch = launch
            app.challenge_wrapped = True
        return app


def recovery_handler(sessions):
    Base = judge_handler(sessions)
    class Handler(Base):
        def send(self, status, body='', location=None, cookie=None, json_body=False):
            if not json_body:
                body = body.replace('<h1>', '<aside>'+LABEL+'</aside><h1>',1)
            return super().send(status,body,location,cookie,json_body)
    return Handler


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--port',type=int,default=64325);p.add_argument('--record-video',action='store_true')
    a=p.parse_args();origin=f'http://127.0.0.1:{a.port}'
    sessions=RecoverySessions(a.state,origin,catalog_provider='channel3')
    sessions.record_video=a.record_video
    print('Local labeled recovery challenge: '+origin,flush=True)
    ThreadingHTTPServer(('127.0.0.1',a.port),recovery_handler(sessions)).serve_forever()
