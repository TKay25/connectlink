"""The audit log must record USER actions, not Meta's webhook traffic.

Every inbound WhatsApp message, delivery receipt and Meta retry POSTs /webhook.
The catch-all after_request hook logged each one as "System / System Change /
Completed POST Webhook", so a single chat buried every real action in the POS
activity log. This drives the real app and asserts:

  * POST /webhook writes NO activity row (delivery receipts and messages alike);
  * a genuine write endpoint still does (the hook itself is not broken);
  * the read-only endpoints already excluded stay excluded.

Run:  python _check_activity_log_noise.py
"""
import contextlib
import json
import os
import sys
import types

os.environ['DATABASE_URL'] = 'postgresql://u:p@127.0.0.1:9/nodb'
os.environ['APP_ENV'] = 'development'
os.environ['FLASK_ENV'] = 'development'
os.environ.pop('ALLOW_PROD_DB_WRITE', None)

ROOT = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(ROOT, 'ConnectLink.py')
OUT = os.path.join(ROOT, '_check_activity_log_noise_out.txt')
RESULTS = []
SEEN = []


def check(name, ok, detail=''):
    RESULTS.append(('PASS  ' if ok else 'FAIL  ') + name + (('  -> ' + str(detail)) if detail else ''))
    print(RESULTS[-1])
    try:
        with open(OUT, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(RESULTS) + '\n')
    except Exception:                                                      # noqa: BLE001
        pass


class Cur:
    description = None
    rowcount = 0

    def execute(self, sql, params=None):
        SEEN.append((str(sql), params))
        self.description = None
        self.rowcount = 0

    def executemany(self, sql, seq):
        for p in seq:
            self.execute(sql, p)

    def fetchone(self):
        return None

    def fetchall(self):
        return []

    def close(self):
        pass


class Conn:
    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


@contextlib.contextmanager
def fake_db():
    yield Cur(), Conn()


def fake_execute_query(sql, params=None, fetch_all=False, fetch_one=False, commit=False):
    SEEN.append((str(sql), params))
    if fetch_all:
        return []
    if fetch_one:
        return None
    return True


wp = types.ModuleType('weasyprint')


class _HTML:
    def __init__(self, *a, **k):
        pass

    def write_pdf(self, *a, **k):
        return b''

    def render(self, *a, **k):
        return types.SimpleNamespace(pages=[])


wp.HTML = _HTML
wp.CSS = type('CSS', (), {'__init__': lambda self, *a, **k: None})
sys.modules.setdefault('weasyprint', wp)

import db_helper                                                           # noqa: E402

db_helper.get_db = fake_db
db_helper.execute_query = fake_execute_query
db_helper.schema_writes_allowed = lambda: False

import ConnectLink                                                        # noqa: E402

app = ConnectLink.app
app.config['TESTING'] = True


@app.route('/api/__check_write_that_logs_nothing', methods=['POST'])
def __check_write_that_logs_nothing():
    """A write that does not record its own activity: the hook must cover it."""
    return ConnectLink.jsonify({'success': True})


def activity_rows():
    rows = []
    for sql, params in SEEN:
        if 'INSERT INTO activity_log' in ' '.join(str(sql).split()):
            rows.append(params)
    return rows


def post(path, payload):
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['userid'] = 1
        sess['user_uuid'] = 'test-uuid'
        sess['user_name'] = 'Mrs G Admin'
    SEEN.clear()
    resp = client.post(path, json=payload)
    return resp, activity_rows()


ORIGIN = {'display_phone_number': '263771234567', 'phone_number_id': '1234567890'}

DELIVERY = {
    'object': 'whatsapp_business_account',
    'entry': [{'id': 'WABA', 'changes': [{'field': 'messages', 'value': {
        'messaging_product': 'whatsapp',
        'metadata': ORIGIN,
        'statuses': [{'id': 'wamid.CHECK', 'status': 'delivered',
                      'timestamp': '1730000000', 'recipient_id': '263771234567'}],
    }}]}],
}

INBOUND = {
    'object': 'whatsapp_business_account',
    'entry': [{'id': 'WABA', 'changes': [{'field': 'messages', 'value': {
        'messaging_product': 'whatsapp',
        'metadata': ORIGIN,
        'contacts': [{'profile': {'name': 'Test Client'}, 'wa_id': '263771234567'}],
        'messages': [{'from': '263771234567', 'id': 'wamid.CHECK2', 'timestamp': '1730000001',
                      'type': 'text', 'text': {'body': 'hello'}}],
    }}]}],
}

for label, payload in (('a delivery receipt', DELIVERY), ('an inbound message', INBOUND)):
    resp, rows = post('/webhook', payload)
    check(f'{label} on /webhook leaves the activity log alone',
          resp.status_code < 400 and not rows,
          {'status': resp.status_code, 'activity_rows': len(rows)})

resp, rows = post('/api/__check_write_that_logs_nothing', {})
check('a real write still lands in the activity log (the hook is not disabled)',
      resp.status_code == 200 and len(rows) == 1, {'status': resp.status_code, 'rows': rows})
check('...and it is recorded as a system_change naming the endpoint',
      bool(rows) and rows[0][0] == 'system_change' and 'Check Write That Logs Nothing' in rows[0][1],
      rows[:1])

src = open(APP, encoding='utf-8').read()
hook = src.split('def log_untracked_system_change(')[1].split('\ndef ')[0]
for endpoint in ('handle_activity_log', 'pos_stock_audit_run', 'pos_stock_audit_columns',
                 'pos_upload_stock_analyze', 'webhook'):
    check(f'the hook deliberately skips {endpoint}', f"'{endpoint}'" in hook)

failures = [r for r in RESULTS if r.startswith('FAIL')]
print('\n%d checks, %d failed' % (len(RESULTS), len(failures)))
sys.exit(1 if failures else 0)
