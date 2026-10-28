"""Prove the POS header's per-department money adds up.

The header used to charge a whole receipt to every department it touched: ring
one Hardware item and one Furniture item on the same basket and both shelves were
credited the full total. Hardware + Furniture then came to more than the shop
took, and the department figures disagreed with the Sales & Profit report.

This bootstraps ConnectLink against a recording stand-in (no socket is opened),
captures the SQL that /api/dashboard/stats, /api/dashboard/today-by-cashier and
the branch+department summary really build for each of the three views, runs
that SQL against a seeded SQLite copy of the same tables, and asserts the money:

  * Hardware + Furniture == All (whole-shop takings, never double counted);
  * a mixed basket is SPLIT between the two departments;
  * the header agrees with the branch+department summary the PDF is built from;
  * voided, layby and other-branch rows stay out.

Run:  python _check_dashboard_department_totals.py
"""
import contextlib
import os
import re
import sqlite3
import sys
import types

os.environ['DATABASE_URL'] = 'postgresql://u:p@127.0.0.1:9/nodb'
os.environ['APP_ENV'] = 'development'
os.environ['FLASK_ENV'] = 'development'
os.environ.pop('ALLOW_PROD_DB_WRITE', None)

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, '_check_dashboard_department_totals_out.txt')
RESULTS = []
SEEN = []


def check(name, ok, detail=''):
    RESULTS.append(('PASS  ' if ok else 'FAIL  ') + name + (('  -> ' + str(detail)) if detail else ''))
    print(RESULTS[-1])
    try:
        with open(OUT, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(RESULTS) + '\n')
    except Exception:                                                     # noqa: BLE001
        pass


# ---------------------------------------------------------------------------
# Recording stand-in for the database (never opens a socket)
# ---------------------------------------------------------------------------
class Cur:
    description = None
    rowcount = 0

    def execute(self, sql, params=None):
        SEEN.append((str(sql), tuple(params) if params is not None else None))
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
    SEEN.append((str(sql), tuple(params) if params is not None else None))
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

import db_helper                                                        # noqa: E402

db_helper.get_db = fake_db
db_helper.execute_query = fake_execute_query
db_helper.schema_writes_allowed = lambda: False

import ConnectLink                                                     # noqa: E402

app = ConnectLink.app
app.config['TESTING'] = True


# ---------------------------------------------------------------------------
# A seeded SQLite copy of the tables these queries touch, and a translator
# ---------------------------------------------------------------------------
def build_db():
    import datetime as _dt
    today = _dt.date.today().isoformat()
    yday = (_dt.date.today() - _dt.timedelta(days=1)).isoformat()
    db = sqlite3.connect(':memory:')
    db.executescript("""
        CREATE TABLE products (id INTEGER PRIMARY KEY, buy_price REAL);
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY, transaction_number TEXT, user_id INTEGER,
            payment_method TEXT, status TEXT, total REAL, subtotal REAL,
            created_at TEXT, branch_id INTEGER, voided INTEGER DEFAULT 0);
        CREATE TABLE transaction_items (
            id INTEGER PRIMARY KEY, transaction_id INTEGER, product_id INTEGER,
            quantity INTEGER, price_at_time REAL, subtotal REAL, department TEXT,
            cost_at_time REAL);
        CREATE TABLE admin_users (id INTEGER PRIMARY KEY, full_name TEXT);
        CREATE TABLE branches (id INTEGER PRIMARY KEY, name TEXT);
        INSERT INTO admin_users (id, full_name) VALUES (7, 'Mrs G Admin');
        INSERT INTO branches (id, name) VALUES (1, 'Shurugwi'), (2, 'Chegutu');
        INSERT INTO products (id, buy_price) VALUES (10, 400.00), (20, 250.00);
    """)
    rows = [
        # -- transactions: (id, num, user, method, status, total, subtotal, date, branch, voided)
        (1, 'T1', 7, 'cash', 'completed', 1000.00, 1000.00, today + ' 09:00:00', 1, 0),
        (2, 'T2', 7, 'cash', 'completed', 990.75, 990.75, today + ' 10:00:00', 1, 0),
        # MIXED basket: USD 100 hardware + USD 200 furniture = USD 300
        (3, 'T3', 7, 'ecocash', 'completed', 300.00, 300.00, today + ' 11:00:00', 1, 0),
        (4, 'T4', 7, 'cash', 'completed', 50.00, 50.00, today + ' 12:00:00', 1, 1),   # voided
        (5, 'T5', 7, 'layby', 'layby', 40.00, 40.00, today + ' 13:00:00', 1, 0),      # layby
        (6, 'T6', 7, 'cash', 'completed', 70.00, 70.00, yday + ' 13:00:00', 1, 0),    # yesterday
        (7, 'T7', 7, 'cash', 'completed', 500.00, 500.00, today + ' 14:00:00', 2, 0),  # other shop
        # a completed receipt with no lines at all (a migrated row)
        (8, 'T8', 7, 'cash', 'completed', 25.00, 25.00, today + ' 15:00:00', 1, 0),
    ]
    items = [
        (1, 1, 10, 2, 500.00, 1000.00, 'hardware', 400.00),
        (2, 2, 20, 3, 330.25, 990.75, 'furniture', 250.00),
        (3, 3, 10, 1, 100.00, 100.00, 'hardware', 400.00),
        (4, 3, 20, 2, 100.00, 200.00, 'furniture', 250.00),
        (5, 4, 10, 5, 10.00, 50.00, 'hardware', 400.00),
        (6, 5, 10, 1, 40.00, 40.00, 'hardware', 400.00),
        (7, 6, 10, 1, 70.00, 70.00, 'hardware', 400.00),
        (8, 7, 10, 4, 125.00, 500.00, 'hardware', 400.00),
    ]
    db.executemany('INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?,?,?)', rows)
    db.executemany('INSERT INTO transaction_items VALUES (?,?,?,?,?,?,?,?)', items)
    db.commit()
    return db, today


ANY_RE = re.compile(r"COALESCE\(\s*([\w.]*department)\s*,\s*'hardware'\s*\)\s*=\s*ANY\(\?\)", re.I)


def to_sqlite(sql, params):
    """Turn one captured PostgreSQL statement into (sqlite_sql, sqlite_params)."""
    flat = re.sub(r'--[^\n]*', ' ', sql)     # the app's SQL carries -- comments
    flat = ' '.join(flat.split())
    flat = re.sub(r'%s::date', 'date(%s)', flat)
    flat = re.sub(r'([\w.]+)::date', r'date(\1)', flat)
    sqlite_params = []
    for p in params or ():
        if isinstance(p, (list, tuple)):
            sqlite_params.extend(p)
        else:
            sqlite_params.append(p)

    res = ''
    idx = 0
    i = 0
    while i < len(flat):
        if flat.startswith('ANY(%s)', i):
            is_in = re.search(r"COALESCE\(\s*[\w.]*department\s*,\s*'hardware'\s*\)\s*=\s*$",
                              res[-200:], re.I)
            count = len(params[idx]) if isinstance(params[idx], (list, tuple)) else 1
            if is_in:
                # sqlite has no ANY(array): it is an IN list
                res = re.sub(r'=\s*$', '', res)
                res += 'IN (%s)' % ', '.join(['?'] * count)
            else:
                res += 'ANY(%s)' % ', '.join(['?'] * count)
            idx += 1
            i += len('ANY(%s)')
            continue
        if flat.startswith('%s', i):
            res += '?'
            idx += 1
            i += 2
            continue
        res += flat[i]
        i += 1
    return res, sqlite_params


def run_captured(path, session_dept, branch_id=1, expect='stats'):
    """Ask the real endpoint to build its SQL, then run that SQL on SQLite."""
    SEEN.clear()
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = 7
        sess['userid'] = 7
        sess['user_uuid'] = 'test-uuid'
        sess['branch_id'] = branch_id
        sess['branch_name'] = 'Shurugwi'
        sess['branch_chosen'] = True
        sess['department'] = session_dept
        sess['department_chosen'] = True
    client.get(path)
    wanted = [(s, p) for s, p in SEEN
              if expect in ' '.join(s.split())]
    return wanted


db, TODAY = build_db()

# ---------------------------------------------------------------------------
# 1. /api/dashboard/stats -- the two header pills
# ---------------------------------------------------------------------------
stats = {}
for dept in ('all', 'hardware', 'furniture'):
    found = run_captured('/api/dashboard/stats', dept, expect='items_sold')
    check(f'{dept}: the dashboard runs one query', len(found) == 1, len(found))
    if not found:
        continue
    sql, params = to_sqlite(*found[0])
    try:
        row = db.execute(sql, params).fetchone()
    except Exception as exc:                                            # noqa: BLE001
        check(f'{dept}: the dashboard query runs', False, '%s: %s' % (type(exc).__name__, str(exc)[:200]))
        continue
    stats[dept] = {'sales': round(float(row[0] or 0), 2), 'items': int(row[1] or 0)}

check('All shows what the shop took (voided/layby/other-day/other-branch excluded)',
      stats.get('all') == {'sales': 2315.75, 'items': 8}, stats.get('all'))
check('Hardware shows only its own lines',
      stats.get('hardware') == {'sales': 1100.0, 'items': 3}, stats.get('hardware'))
check('Furniture shows only its own lines',
      stats.get('furniture') == {'sales': 1190.75, 'items': 5}, stats.get('furniture'))
check('a mixed basket is SPLIT, not charged in full to each shelf',
      stats.get('hardware', {}).get('sales') != 1300.0
      and stats.get('furniture', {}).get('sales') != 1290.75,
      f"hardware={stats.get('hardware')} furniture={stats.get('furniture')}")
check('Hardware + Furniture is the shop total (the itemless receipt is All-only)',
      round(stats.get('hardware', {}).get('sales', 0)
            + stats.get('furniture', {}).get('sales', 0), 2) == 2290.75
      and round(stats.get('all', {}).get('sales', 0) - 2290.75, 2) == 25.0,
      stats)
check('the itemless receipt still shows on All, with no phantom items',
      stats.get('all', {}).get('sales') == 2315.75 and stats.get('all', {}).get('items') == 8,
      stats.get('all'))

# ---------------------------------------------------------------------------
# 2. The cashier breakdown must agree with the pills, on every shelf
# ---------------------------------------------------------------------------
for dept in ('all', 'hardware', 'furniture'):
    found = run_captured('/api/dashboard/today-by-cashier', dept, expect='items_sold')
    if not found:
        check(f'{dept}: the cashier breakdown runs its totals query', False, 'not captured')
        continue
    sql, params = to_sqlite(*found[0])
    try:
        row = db.execute(sql, params).fetchone()
        total = round(float(row[1] or 0), 2) if row else 0.0
        items = int(row[3] or 0) if row else 0
    except Exception as exc:                                            # noqa: BLE001
        check(f'{dept}: the cashier breakdown query runs', False, '%s: %s' % (type(exc).__name__, str(exc)[:200]))
        continue
    check(f'{dept}: the cashier card equals the header pill',
          (total, items) == (stats.get(dept, {}).get('sales'), stats.get(dept, {}).get('items')),
          {'card': (total, items), 'pill': stats.get(dept)})

# ---------------------------------------------------------------------------
# 3. The header must agree with the branch+department summary the PDF uses
# ---------------------------------------------------------------------------
found = run_captured(f'/api/transactions/branch-department-summary?start={TODAY}&end={TODAY}',
                     'all', expect='GROUP BY t.branch_id, b.name')
if not found:
    check('the report summary query is reached', False, 'not captured')
else:
    sql, params = to_sqlite(*found[0])
    try:
        rows = db.execute(sql, params).fetchall()
    except Exception as exc:                                            # noqa: BLE001
        check('the report summary query runs', False, '%s: %s' % (type(exc).__name__, str(exc)[:250]))
        rows = []
    report = {}
    for r in rows:
        if r[0] != 'Shurugwi':
            continue
        report[r[1]] = {'revenue': round(float(r[4] or 0), 2), 'items': int(r[3] or 0)}
    check('the PDF summary reports Shurugwi Hardware at the header figure',
          report.get('hardware', {}).get('revenue') == stats.get('hardware', {}).get('sales'),
          {'report': report.get('hardware'), 'header': stats.get('hardware')})
    check('the PDF summary reports Shurugwi Furniture at the header figure',
          report.get('furniture', {}).get('revenue') == stats.get('furniture', {}).get('sales'),
          {'report': report.get('furniture'), 'header': stats.get('furniture')})
    check('the report lists both shelves of the branch',
          len(rows) >= 2 and {r[1] for r in rows} == {'hardware', 'furniture'},
          [(r[0], r[1]) for r in rows])

# ---------------------------------------------------------------------------
# 4. The All Branches view adds the shops together
# ---------------------------------------------------------------------------
SEEN.clear()
client = app.test_client()
with client.session_transaction() as sess:
    sess['user_id'] = 7
    sess['userid'] = 7
    sess['branch_id'] = 0
    sess['branch_name'] = 'All Branches'
    sess['branch_chosen'] = True
    sess['department'] = 'all'
    sess['department_chosen'] = True
client.get('/api/dashboard/stats')
found = [(s, p) for s, p in SEEN if 'items_sold' in ' '.join(s.split())]
if found:
    sql, params = to_sqlite(*found[0])
    row = db.execute(sql, params).fetchone()
    check('All Branches is both shops, and still not double counted',
          (round(float(row[0] or 0), 2), int(row[1] or 0)) == (2815.75, 12),
          {'sales': float(row[0] or 0), 'items': int(row[1] or 0)})
else:
    check('All Branches is both shops, and still not double counted', False, 'not captured')

db.close()

failures = [r for r in RESULTS if r.startswith('FAIL')]
print('\n%d checks, %d failed' % (len(RESULTS), len(failures)))
sys.exit(1 if failures else 0)
