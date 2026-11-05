"""Synthetic API-shaped inputs; never presented as Channel3 live evidence."""
import unittest
from unittest.mock import patch
from channel3 import Client, Channel3Error, evidence

class Channel3Tests(unittest.TestCase):
    def test_unknown_stock_and_variant_do_not_become_true(self):
        p={'id':'synthetic','title':'Wide leather shoes size 11','structured_attributes':{'size':['11','12']},'offers':[{'price':{'price':100,'currency':'USD'}}]}
        e=evidence(p)
        self.assertEqual(e['selected_options'],{})
        self.assertIsNone(e['offers'][0]['available'])
        self.assertIsNone(e['resolable'])
        self.assertIsNone(e['delivery_within_days'])
        self.assertIsNone(e['retailer_tax_cents'])

    def test_actual_selected_option_preserved_even_if_not_requested(self):
        p={'id':'synthetic','variants':{'selected':[{'name':'Size','label':'12'}]},'offers':[{'price':{'price':99.99,'currency':'USD'},'availability':'InStock'}]}
        e=evidence(p)
        self.assertEqual(e['selected_options']['size'],'12')
        self.assertEqual(e['offers'][0]['price_cents'],9999)
        self.assertTrue(e['offers'][0]['available'])

    def test_unusable_prices_remain_unknown(self):
        for price,currency in [('NaN','USD'),(-1,'USD'),(0,'USD'),(1.001,'USD'),(100,'EUR')]:
            self.assertIsNone(evidence({'offers':[{'price':{'price':price,'currency':currency}}]})['offers'][0]['price_cents'])

    def test_selected_options_sent_and_identity_checked(self):
        c=Client('synthetic-test-key')
        with patch.object(c,'request',return_value={'id':'p/1'}) as request:
            c.product('p/1',{'Size':'11 Wide'})
            self.assertIn('p%2F1?',request.call_args.args[0])
            self.assertIn('option_Size=11+Wide',request.call_args.args[0])
        with patch.object(c,'request',return_value={'id':'wrong'}):
            with self.assertRaises(Channel3Error): c.product('p/1')

    def test_search_does_not_trust_legacy_or_malformed_payload(self):
        c=Client('synthetic-test-key')
        with patch.object(c,'request',return_value={'products':[]}): self.assertEqual(c.search('shoes'),[])
        with patch.object(c,'request',return_value={'items':[]}):
            with self.assertRaises(Channel3Error): c.search('shoes')

class CatalogTests(unittest.TestCase):
    def record(self):
        return evidence({'id':'synthetic-1','title':'Synthetic shoe',
            'category':{'slug':'shoes','path':[]},
            'structured_attributes':{'upper-material':['Leather']},
            'offers':[{'domain':'example.test','price':{'price':100,'currency':'USD'},'availability':'InStock'}]})

    def test_import_never_fills_requested_size_or_resoling(self):
        from channel3 import catalog_from_evidence
        c=catalog_from_evidence([self.record()]);p=next(iter(c['products'].values()))
        self.assertEqual(p['material'],'leather')
        self.assertIsNone(p['size']);self.assertIsNone(p['width']);self.assertIsNone(p['resolable'])
        self.assertEqual(p['source']['unit_basis'],'test merchant sells one pair')
        self.assertIn('not retailer charges',c['disclosure'])

    def test_missing_material_is_not_taken_from_title(self):
        from channel3 import catalog_from_evidence
        r=self.record();r['title']='Leather Shoe';r['structured_attributes']={}
        self.assertIsNone(next(iter(catalog_from_evidence([r])['products'].values()))['material'])

    def test_404_detail_skipped_but_rate_limit_not_swallowed(self):
        from channel3 import discover
        c=Client('synthetic')
        with patch.object(c,'search',return_value=[{'id':'missing'}]),patch.object(c,'product',side_effect=Channel3Error('not found',404)):
            with self.assertRaisesRegex(Channel3Error,'No usable'):discover(c,{'requirements':{}})
        with patch.object(c,'search',return_value=[{'id':'missing'}]),patch.object(c,'product',side_effect=Channel3Error('limited',429)):
            with self.assertRaisesRegex(Channel3Error,'limited'):discover(c,{'requirements':{}})

    def test_real_catalog_gate_uses_same_policy_and_approval(self):
        import tempfile,time
        from pathlib import Path
        from judge import Sessions
        from shop import digest,token_hash,Refused
        from channel3 import catalog_from_evidence
        from test_judge import draft
        import profile_intent
        with tempfile.TemporaryDirectory() as tmp:
            sessions=Sessions(Path(tmp),'http://127.0.0.1',extractor=draft,catalog_provider='channel3')
            row=sessions.record(sessions.new());app=sessions.draft(row,'black shoes under $250')
            self.assertEqual(app.s.catalog['products'],{})
            r=self.record();r['selected_options']={'color':'black'}
            unknown=self.record();unknown['product_id']='synthetic-2'
            app.s.catalog=catalog_from_evidence([unknown,r])
            (app.out/'channel3-catalog.private.json').write_text(__import__('json').dumps(app.s.catalog))
            cookie=app.s.buyer_exchange(app.s.buyer_access(app.task));buyer=app.s.buyer_session(cookie)
            profile_intent.confirm(app.s,app.task,buyer,digest(app.s.snapshot(app.task)['intent']))
            with app.s.db:app.s.db.execute('UPDATE carts SET visit_hash=?,visit_expires=? WHERE task_id=?',(token_hash('test'),time.time()+60,app.task))
            visit=app.s.exchange('test');csrf=app.s.session(visit)['csrf']
            bad,good=list(app.s.catalog['products'])
            app.s.mutate(visit,csrf,bad,1);app.s.runner_finished(app.task,'done');q=app.s.freeze(app.task)
            self.assertEqual(app.s.assessment(app.task,q)['intent_aware_quote_policy']['gate'],'insufficient_evidence')
            with self.assertRaises(Refused):app.s.buyer_decide(cookie,buyer['csrf'],q['quote_id'],q['sha256'],'approve')
            app.s.reopen(app.task);app.s.mutate(visit,csrf,bad,0);app.s.mutate(visit,csrf,good,1)
            app.s.runner_finished(app.task,'done');q=app.s.freeze(app.task)
            self.assertEqual(app.s.assessment(app.task,q)['intent_aware_quote_policy']['gate'],'allow')
            app.s.buyer_decide(cookie,buyer['csrf'],q['quote_id'],q['sha256'],'approve')
            self.assertIsNotNone(app.s.approval_for(app.task,q));self.assertIsNone(app.p)
            self.assertIn('Payments are disabled for this Channel3 acceptance',app.page(buyer))
            self.assertNotIn('Configure PayPal sandbox',app.page(buyer))
            before=app.s.catalog;app.s.db.close();del sessions.apps[row['id']]
            restored=sessions.app(row['id']);self.assertEqual(restored.s.catalog,before)
            self.assertIsNotNone(restored.s.approval_for(restored.task,q))
            restored.s.clock=lambda:q['expires_at']+1
            with self.assertRaises(Refused):restored.s.approval_for(restored.task,q)
            page=restored.page(buyer)
            self.assertIn('Previously approved',page)
            self.assertIn('not permission to pay',page)
            self.assertNotIn('Approve exact purchase',page)
            with restored.s.db:restored.s.db.execute("UPDATE approvals SET quote_sha256='other'")
            self.assertNotIn('Previously approved',restored.page(buyer))
            restored.s.db.close();sessions.pool.shutdown();sessions.db.close()

    def test_payment_config_rejected_in_channel3_mode(self):
        from judge import Sessions
        with self.assertRaisesRegex(ValueError,'payment-disabled'):
            Sessions('/unused','http://127.0.0.1',paypal_config='private',catalog_provider='channel3')

    def test_variant_request_does_not_overwrite_relaxed_response(self):
        from channel3 import discover
        c=Client('synthetic')
        detail={'id':'p','title':'Shoe','category':{'slug':'shoes'},'structured_attributes':{},
            'variants':{'options':[{'name':'Size','values':[{'label':'11','exists':True}]}],'selected':[{'name':'Size','label':'12'}]},
            'offers':[{'domain':'example.test','price':{'price':100,'currency':'USD'},'availability':'InStock'}]}
        with patch.object(c,'search',return_value=[{'id':'p'}]),patch.object(c,'product',return_value=detail) as get:
            catalog=discover(c,{'requirements':{'size':'11'}})
            self.assertEqual(get.call_args.args,('p',{'Size':'11'}))
            self.assertEqual(next(iter(catalog['products'].values()))['size'],'12')

    def test_external_variant_labels_are_escaped_on_shop_and_cart(self):
        import tempfile,urllib.request
        from pathlib import Path
        from channel3 import catalog_from_evidence
        from shop import Store,serve
        with tempfile.TemporaryDirectory() as tmp:
            store=Store(Path(tmp)/'test.sqlite');r=self.record()
            r['selected_options']={'size':'<img src=x onerror=alert(1)>'}
            store.catalog=catalog_from_evidence([r]);created=store.create()
            session=store.exchange(created['visit_token']);row=store.session(session)
            store.mutate(session,row['csrf'],next(iter(store.catalog['products'])),1)
            server=serve(store)
            try:
                for path in ('/shop','/cart'):
                    req=urllib.request.Request(server.origin+path,headers={'Cookie':'shopper='+session})
                    with urllib.request.urlopen(req) as response:body=response.read().decode()
                    self.assertNotIn('<img src=x',body);self.assertIn('&lt;img src=x',body)
            finally:server.shutdown();server.server_close();store.db.close()
