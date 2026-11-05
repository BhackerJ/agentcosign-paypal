"""Read-only Channel3 discovery. Never infers purchase facts from search rank."""
import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

API = 'https://api.trychannel3.com'


class Channel3Error(Exception):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


class Client:
    def __init__(self, key=None):
        self.key = key or os.getenv('CHANNEL3_API_KEY')
        if not self.key:
            raise Channel3Error('CHANNEL3_API_KEY is not configured')

    def request(self, path, payload=None):
        req = urllib.request.Request(API + path,
            data=json.dumps(payload).encode() if payload is not None else None,
            headers={'x-api-key': self.key, 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            # Provider response bodies may contain query data; do not echo them.
            raise Channel3Error(f'Channel3 HTTP {error.code}; no automatic retry', error.code) from None
        except (OSError, ValueError):
            raise Channel3Error('Channel3 request failed; no automatic retry') from None

    def search(self, query, limit=3):
        data = self.request('/v1/search', {'query': query, 'limit': limit,
            'config': {'country': 'US', 'currency': 'USD', 'mode': 'default'}})
        if not isinstance(data, dict) or not isinstance(data.get('products'), list):
            raise Channel3Error('Unexpected Channel3 search response')
        return data['products']

    def product(self, product_id, options=None):
        params = {'country': 'US', 'currency': 'USD'}
        params.update({'option_'+k: v for k, v in (options or {}).items()})
        data = self.request('/v1/products/'+urllib.parse.quote(product_id, safe='')+'?'+urllib.parse.urlencode(params))
        if not isinstance(data, dict) or data.get('id') != product_id:
            raise Channel3Error('Channel3 product identity mismatch')
        return data


def evidence(product, retrieved_at=None):
    """Return documented facts only, keeping variant and merchant offer scope.

    Family materials/attributes do not establish selected-variant facts. Delivery,
    resoling, unit, footwear category and landed totals are not invented here.
    """
    selected = (product.get('variants') or {}).get('selected') or []
    options = {}
    for option in selected:
        name = str(option.get('name', '')).lower()
        label = option.get('label')
        if name in options: options[name] = None  # ambiguous duplicate
        else: options[name] = label
    offers = []
    for offer in product.get('offers') or []:
        price = offer.get('price') or {}
        cents = None
        try:
            value = Decimal(str(price.get('price')))*100
            if price.get('currency') == 'USD' and value.is_finite() and value > 0 and value == value.to_integral_value():
                cents = int(value)
        except (InvalidOperation, TypeError, ValueError):
            pass
        offers.append({'domain': offer.get('domain'), 'url': offer.get('url'),
            'price_cents': cents, 'currency': price.get('currency'),
            'available': {'InStock': True, 'OutOfStock': False}.get(offer.get('availability'))})
    return {'provider': 'channel3', 'product_id': product.get('id'), 'title': product.get('title'),
        'retrieved_at': retrieved_at or datetime.now(timezone.utc).isoformat(),
        'response_sha256': hashlib.sha256(json.dumps(product,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
        'selected_options': options, 'structured_attributes': product.get('structured_attributes') or {},
        'materials': product.get('materials'), 'category': product.get('category'), 'offers': offers,
        'delivery_within_days': None, 'resolable': None,
        'retailer_shipping_cents': None, 'retailer_tax_cents': None,
        'disclosure': 'Real product data. Sandbox demonstration only; no retailer order or fulfillment.'}


def catalog_from_evidence(records):
    """Import offer-scoped evidence into the fictional merchant, never a retailer cart."""
    products = {}
    for record in records:
        category = record.get('category') or {}
        if 'shoes' not in [category.get('slug'), *[p.get('slug') for p in category.get('path', [])]]:
            continue
        options = record['selected_options']
        attrs = record['structured_attributes']
        def single(key):
            values = attrs.get(key) or []
            return values[0].lower() if len(values) == 1 else None
        for index, offer in enumerate(record['offers']):
            if offer['price_cents'] is None or not offer['domain']:
                continue
            sku = 'c3-'+hashlib.sha256((str(record['product_id'])+'|'+str(index)+'|'+offer['domain']).encode()).hexdigest()[:20]
            products[sku] = {'name':record['title'], 'category':'footwear',
                'price_cents':offer['price_cents'], 'available':offer['available'],
                'size':options.get('size'),
                'width':{'Regular':'standard','Wide':'wide','Extra Wide':'extra_wide'}.get(options.get('width')),
                'color':options.get('color','').lower() or None,
                'material':single('upper-material'),
                'style':'lace_up' if single('closure-type') == 'lace-up' else None,
                'resolable':None, 'delivery_within_days':None,
                'unit':'pair',  # Test merchant sales unit, not a retailer variant claim.
                'source':{'provider':'channel3','product_id':record['product_id'],
                    'domain':offer['domain'],'retrieved_at':record['retrieved_at'],
                    'response_sha256':record['response_sha256'],
                    'field_mapping':{'material':'structured_attributes.upper-material (single value)', 'size':'variants.selected.Size', 'width':'variants.selected.Width', 'color':'variants.selected.Color', 'availability':'selected offer.availability'},
                    'selected_options':options, 'unit_basis':'test merchant sells one pair',
                    'retailer_shipping_cents':None,'retailer_tax_cents':None}}
    return {'merchant_id':'agentcosign-local-test-merchant', 'currency':'USD',
        'shipping_cents':1000,'tax_basis_points':600,'products':products,
        'provider':'channel3', 'disclosure':'Real product data from Channel3. Sandbox test merchant only; no retailer order or fulfillment. Shipping $10 and 6% test tax are simulated, not retailer charges. Size, width and delivery remain unknown unless documented.'}


def discover(client, intent):
    # Submit only supported structured product requirements, not raw profiles/PII.
    req = intent['requirements']
    query = 'shoes ' + ' '.join(str(req[k]) for k in ('color','material','style','shoe_type','size','width') if k in req)
    records, missing = [], []
    for product in client.search(query, limit=5):
        try:
            detail = client.product(product['id'])
            selection = {}
            for option in (detail.get('variants') or {}).get('options') or []:
                key = option['name'].lower()
                wanted = req.get(key)
                if wanted is None: continue
                for value in option.get('values') or []:
                    label = value.get('label', '')
                    if value.get('exists') is True and label.lower().replace(' ', '_') == str(wanted).lower():
                        selection[option['name']] = label
                        break
            if selection: detail = client.product(product['id'], selection)
            records.append(evidence(detail))
        except Channel3Error as error:
            if error.status != 404: raise
            missing.append(product['id'])
    catalog = catalog_from_evidence(records)
    catalog['unavailable_product_ids'] = missing
    if not catalog['products']:
        raise Channel3Error('No usable USD shoe offers returned; no fixture fallback')
    return catalog
