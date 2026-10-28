"""Pre-deployment guard: every query the POS builds must fit its parameters.

A placeholder/parameter mismatch does not fail at import -- it fails the moment a
cashier opens the till, with a 500 on the header cards. psycopg2 also adapts a
Python list to an ARRAY, so passing a LIST into a scalar `department = %s` raises
"operator does not exist: character varying = text[]".

This boots ConnectLink against a recording stand-in for the database (no socket
is ever opened), drives every department-aware read in all three views, and for
each statement asserts:

  * the number of %s placeholders equals the number of parameters;
  * no query compares a department column against the literal 'all';
  * the All view really passes BOTH departments (and a single view passes one).

Run:  python _check_department_queries.py
"""
import contextlib
import os
import re
import sys
import types

os.environ['DATABASE_URL'] = 'postgresql://u:p@127.0.0.1:9/nodb'
os.environ['APP_ENV'] = 'development'
os.environ['FLASK_ENV'] = 'development'
os.environ.pop('ALLOW_PROD_DB_WRITE', None)

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, '_check_department_queries_out.txt')
RESULTS = []
SEEN = []


def check(name, ok, detail=''):
    RESULTS.append(('PASS  ' if ok else 'FAIL  ') + name + (('  -> ' + str(detail)) if detail else ''))
    print(RESULTS[-1])
    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(RESULTS) + '\n')


# ---------------------------------------------------------------------------
# Recording stand-in for the database
# ---------------------------------------------------------------------------
def record(sql, params):
    SEEN.append((' '.join(str(sql).split()), params))


class Cur:
    description = None
    rowcount = 0

    def __init__(self):
        self._rows = []

    def execute(self, sql, params=None):
        record(sql, params)
        flat = ' '.join(str(sql).split()).upper()
        if 'LASTVAL' in flat or 'RETURNING' in flat:
            self._rows = [(1,)]
        elif flat.startswith('SELECT'):
            self._rows = []
        else:
            self._rows = []
        self.description = None
        self.rowcount = 0

    def executemany(self, sql, seq):
        for p in seq:
            self.execute(sql, p)

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)

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
    record(sql, params)
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

import db_helper                                                    # noqa: E402

db_helper.get_db = fake_db
db_helper.execute_query = fake_execute_query
db_helper.schema_writes_allowed = lambda: False

import ConnectLink                                                 # noqa: E402

app = ConnectLink.app
app.config['TESTING'] = True

# ---------------------------------------------------------------------------
# 1. Placeholder / parameter parity, and 'all' never reaching SQL
# ---------------------------------------------------------------------------
bad_arity = []
bad_all = []
view_params = {}

def audit_statements(where):
    """Check every recorded statement; return (arity_failures, all-leaks)."""
    arity, leaks = [], []
    for sql, params in SEEN:
        if params is None:
            continue
        if not isinstance(params, (list, tuple)):
            params = [params]
        expected = sql.count('%s')
        if expected != len(params):
            arity.append((where, expected, len(params), sql[:160]))
        if re.search(r"COALESCE\(\s*[\w.]*department[^)]*\)\s*=\s*'all'", sql, re.I):
            leaks.append((where, sql[:160]))
    return arity, leaks


CALLS = [
    ('/api/products', 'the catalogue'),
    ('/api/products/1', 'one product'),
    ('/api/transactions?limit=10', 'the transactions tab'),
    ('/api/transactions/voided', 'voided sales'),
    ('/api/transactions/daily-summary', 'the day summary'),
    ('/api/transactions/day-end?date=2026-10-26', 'the day-end report'),
    ('/api/dashboard/stats', 'the dashboard header'),
    ('/api/dashboard/today-by-cashier', 'the cashier header'),
    ('/api/stock-additions', 'reinvestment'),
    ('/api/categories', 'categories'),
    ('/api/pos/reconciliation', 'the reconciliation report'),
]

for dept in ('all', 'hardware', 'furniture'):
    for path, human in CALLS:
        SEEN.clear()
        client = app.test_client()
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['userid'] = 1
            sess['user_uuid'] = 'test-uuid'
            sess['branch_id'] = 1
            sess['branch_name'] = 'Shurugwi'
            sess['branch_chosen'] = True
            sess['department'] = dept
        try:
            resp = client.get(path)
            status = resp.status_code
        except Exception as exc:                                    # noqa: BLE001
            status = '%s: %s' % (type(exc).__name__, str(exc)[:120])
        arity, leaks = audit_statements(path)
        if arity:
            bad_arity.extend(arity)
        if leaks:
            bad_all.extend(leaks)
        # A 500 at this point means the endpoint itself blew up building SQL.
        if status == 500:
            bad_arity.append((path, '500', '-', dept))
        view_params.setdefault(dept, []).append((path, len(SEEN)))

check('no query is given the wrong number of parameters (all views, every read)',
      not bad_arity, bad_arity[:4] or 'every statement matched')
check("the literal 'all' never reaches a department comparison", not bad_all,
      bad_all[:3] or 'the view is translated to a department list before SQL')

# ---------------------------------------------------------------------------
# 2. The list really is the departments in view
# ---------------------------------------------------------------------------
for dept in ('all', 'hardware', 'furniture'):
    SEEN.clear()
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['userid'] = 1
        sess['branch_id'] = 1
        sess['branch_chosen'] = True
        sess['department'] = dept
    client.get('/api/transactions?limit=5')
    sql = ' '.join(s for s, _ in SEEN)
    lists = [p for _, p in SEEN if isinstance(p, (list, tuple))
             and any(isinstance(x, (list, tuple)) for x in p)]
    flat = [x for p in lists for x in p if isinstance(x, (list, tuple))]
    want = ['hardware', 'furniture'] if dept == 'all' else [dept]
    check('the %s view hands the query %s' % (dept, want),
          any(sorted(x) == sorted(want) for x in flat),
          [x for x in flat][:3])

# ---------------------------------------------------------------------------
# 3. The three-way switch accepts All and refuses nonsense
# ---------------------------------------------------------------------------
client = app.test_client()
with client.session_transaction() as sess:
    sess['user_id'] = 1
    sess['userid'] = 1
for dept, want_ok in (('all', True), ('hardware', True), ('furniture', True),
                      ('everything', False), ('', False)):
    resp = client.post('/api/pos/switch-department', json={'department': dept})
    body = resp.get_json() or {}
    check('the switch %s %r' % ('accepts' if want_ok else 'refuses', dept),
          (resp.status_code == 200 and body.get('success') is True
           and body.get('department') == dept) if want_ok
          else resp.status_code == 400,
          body)

# ---------------------------------------------------------------------------
# 4. The statements that actually carried the bug are reached and are correct
#    (a harness that never runs a query would pass everything above for free)
# ---------------------------------------------------------------------------
for path, marker in (('/api/transactions/daily-summary', 'items_sold'),
                     ('/api/dashboard/stats', 'items_sold'),
                     ('/api/dashboard/today-by-cashier', 'items_sold')):
    SEEN.clear()
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['userid'] = 1
        sess['branch_id'] = 1
        sess['branch_chosen'] = True
        sess['department'] = 'all'
    client.get(path)
    hits = [s for s, _ in SEEN if marker in s]
    check('%s really runs its %r query, over both departments' % (path, marker),
          bool(hits) and any('= ANY(%s)' in s for s in hits),
          '%d statement(s); ANY used: %s' % (len(hits), any('= ANY(%s)' in s for s in hits)))

# check-auth must echo whatever the session holds, including All.
client = app.test_client()
with client.session_transaction() as sess:
    sess['user_id'] = 1
    sess['userid'] = 1
    sess['branch_id'] = 1
    sess['branch_chosen'] = True
    sess['department'] = 'all'
resp = client.get('/api/check-auth')
body = resp.get_json() or {}
check('check-auth reports the All view and offers all three positions',
      (body.get('department') or {}).get('key') == 'all'
      and [o['key'] for o in (body.get('department') or {}).get('options', [])]
      == ['all', 'hardware', 'furniture'],
      body.get('department'))

for dept in ('hardware', 'furniture'):
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['branch_id'] = 1
        sess['branch_chosen'] = True
        sess['department'] = dept
    body = (client.get('/api/check-auth').get_json() or {}).get('department') or {}
    check('check-auth echoes the %s view' % dept, body.get('key') == dept, body.get('key'))

fails = [r for r in RESULTS if r.startswith('FAIL')]
print('\n' + '=' * 70)
print('%d passed, %d failed' % (len(RESULTS) - len(fails), len(fails)))
sys.exit(1 if fails else 0)
