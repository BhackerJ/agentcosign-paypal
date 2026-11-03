"""Sandbox-only PayPal Orders client. Credentials and tokens never enter reports."""
import base64
import json
import re
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = 'https://api-m.sandbox.paypal.com'


class ProviderFailure(Exception):
    def __init__(self, status=0, code='NETWORK_OUTCOME_UNKNOWN'):
        self.status, self.code = status, code
        super().__init__(f'PayPal sandbox request failed: {status} {code}')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def load_config(path=Path(__file__).with_name('.env.sandbox')):
    values = {}
    for line in path.read_text().splitlines():
        if line.strip() and not line.lstrip().startswith('#'):
            key, separator, value = line.partition('=')
            if separator:
                values[key.strip()] = value.strip().strip('"').strip("'")
    if values.get('PAYPAL_ENV') != 'sandbox':
        raise ValueError('Only sandbox is supported')
    for key in ('PAYPAL_CLIENT_ID', 'PAYPAL_CLIENT_SECRET', 'PAYPAL_MERCHANT_ID', 'PAYPAL_BUYER_ID'):
        if not values.get(key):
            raise ValueError('Missing sandbox configuration: '+key)
    return values


class SandboxClient:
    def __init__(self, config):
        if config.get('PAYPAL_ENV') != 'sandbox':
            raise ValueError('Only sandbox is supported')
        self.config = config
        self.token = None
        self.token_until = 0
        self.opener = urllib.request.build_opener(NoRedirect(), urllib.request.HTTPSHandler(context=ssl.create_default_context()))

    def _send(self, request):
        try:
            with self.opener.open(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            code = 'HTTP_FAILURE'
            try:
                name = json.loads(error.read()).get('name', '')
                if re.fullmatch(r'[A-Z_]{1,80}', name):
                    code = name
            except (ValueError, UnicodeError):
                pass
            raise ProviderFailure(error.code, code) from None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            raise ProviderFailure() from None

    def access_token(self):
        if not self.token or self.token_until <= time.time():
            basic = base64.b64encode((self.config['PAYPAL_CLIENT_ID']+':'+self.config['PAYPAL_CLIENT_SECRET']).encode()).decode()
            result = self._send(urllib.request.Request(BASE+'/v1/oauth2/token', data=b'grant_type=client_credentials',
                            headers={'Authorization': 'Basic '+basic, 'Content-Type': 'application/x-www-form-urlencoded'}))
            self.token = result['access_token']
            self.token_until = time.time()+int(result['expires_in'])-60
        return self.token

    def request(self, method, path, body=None, request_id=None):
        if not re.fullmatch(r'/v2/(?:checkout/orders(?:/[A-Z0-9]{8,32}(?:/capture)?)?|payments/captures/[A-Z0-9]{8,32})', path):
            raise ValueError('Unsupported sandbox API path')
        headers = {'Authorization': 'Bearer '+self.access_token(), 'Content-Type': 'application/json', 'Prefer': 'return=representation'}
        if request_id:
            headers['PayPal-Request-Id'] = request_id
        data = json.dumps(body).encode() if body is not None else None
        return self._send(urllib.request.Request(BASE+path, data=data, headers=headers, method=method))
