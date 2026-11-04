"""Verified minimized source fixtures and buyer-confirmed intent."""

import hashlib, json
from pathlib import Path
from shop import Refused, digest

ROOT = Path(__file__).resolve().parents[1]


def load_fixture(name):
    manifest = json.loads((ROOT / 'fixtures/manifest.json').read_text())
    filename = name + '.json'
    if filename not in manifest or name.endswith('-catalog'):
        raise ValueError('Unknown scenario')
    raw = (ROOT / 'fixtures' / filename).read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest[filename]:
        raise ValueError('Source extract changed')
    data = json.loads(raw)
    catalog_raw = (ROOT / 'fixtures' / (name + '-catalog.json')).read_bytes()
    if hashlib.sha256(catalog_raw).hexdigest() != manifest[name + '-catalog.json']:
        raise ValueError('Catalog changed')
    return data, json.loads(catalog_raw)


def install(store, task, fixture):
    with store.lock, store.db:
        store.db.execute(
            'CREATE TABLE IF NOT EXISTS intent_confirmations(task_id TEXT PRIMARY KEY,intent_hash TEXT,buyer_id TEXT,confirmed_at REAL)'
        )
        state = store.snapshot(task)
        if state['intent'].get('sources'):
            if state['intent']['source_case_id'] != fixture['id']:
                raise ValueError('Use a separate state directory for each scenario')
            return
        if state['items'] or state['quote']:
            raise Refused(409, 'Source intent requires a fresh cart')
        intent = {
            k: fixture[k]
            for k in [
                'sources',
                'request',
                'budget_cents',
                'quantity',
                'allowed_categories',
                'requirements',
                'adaptations',
                'field_sources',
            ]
        }
        intent.update(
            source_case_id=fixture['id'],
            source_run=fixture['historical_run'],
            merchant_id=store.catalog['merchant_id'],
            currency='USD',
            required_size=fixture['requirements']['size'],
            required_width=fixture['requirements']['width'],
        )
        store.db.execute('UPDATE carts SET intent=? WHERE task_id=?', (json.dumps(intent), task))


def status(store, task):
    intent = store.snapshot(task)['intent']
    if not intent.get('sources'):
        return {'confirmed': False, 'status': 'legacy_fixture'}
    row = store.db.execute('SELECT * FROM intent_confirmations WHERE task_id=?', (task,)).fetchone()
    confirmed = bool(row and row['intent_hash'] == digest(intent))
    return {
        'confirmed': confirmed,
        'status': 'confirmed' if confirmed else 'needs_buyer_confirmation',
        'intent_sha256': digest(intent),
    }


def require(store, task):
    if not status(store, task)['confirmed']:
        raise Refused(409, 'Confirm the shopping instructions first')


def confirm(store, task, buyer, expected):
    with store.lock, store.db:
        if buyer['task_id'] != task or expected != digest(store.snapshot(task)['intent']):
            raise Refused(409, 'Intent changed; review again')
        store.db.execute(
            'INSERT OR IGNORE INTO intent_confirmations VALUES (?,?,?,?)',
            (task, expected, buyer['buyer_id'], store.clock()),
        )
        require(store, task)
