"""Example client: review a confirmed cart or retrieve its verified receipt."""

import argparse, json, urllib.request
from pathlib import Path


def call(origin, key, path, data=None):
    req = urllib.request.Request(
        origin + path,
        data=json.dumps(data).encode() if data is not None else None,
        headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--origin', default='http://127.0.0.1:64200')
    p.add_argument('--key-file', type=Path, required=True)
    p.add_argument('--review', action='store_true')
    a = p.parse_args()
    key = a.key_file.read_text().strip()
    result = call(a.origin, key, '/api/purchase')
    if a.review:
        result = call(
            a.origin,
            key,
            '/api/review',
            {
                'cart_version': result['cart_version'],
                'intent_sha256': result['intent_confirmation']['intent_sha256'],
            },
        )
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
