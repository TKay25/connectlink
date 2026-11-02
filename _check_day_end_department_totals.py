"""Prove the day-end report counts each shelf's OWN money.

`/api/transactions/day-end` keeps a receipt's `total` (the whole basket) but
returns only the lines in view, so summing `total` charged one mixed basket to
Hardware's day-end AND Furniture's day-end in full — Hardware + Furniture came
out above what the shop actually took. The money must come from the sale's
lines, exactly as the Sales tab and the transaction list already do.

No database is touched: ConnectLink is booted against a stand-in that answers the
day-end query with rows whose `scoped_total` and `total` deliberately disagree,
and the JSON is read back in all three department views.

Run:  python _check_day_end_department_totals.py
"""
import contextlib
import datetime as dt
import os
import sys
import types

os.environ['DATABASE_URL'] = 'postgresql://nobody@127.0.0.1:9/nodb'
os.environ['APP_ENV'] = 'development'
os.environ['FLASK_ENV'] = 'development'
os.environ.pop('ALLOW_PROD_DB_WRITE', None)

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, '_check_day_end_department_totals_out.txt')
RESULTS = []
sys.path.insert(0, ROOT)

SALES_ROWS = []


def check(name, ok, detail=''):
    RESULTS.append(('PASS  ' if ok else 'FAIL  ') + name + (('  -> ' + str(detail)) if detail else ''))
    print(RESULTS[-1])
    try:
        with open(OUT, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(RESULTS) + '\n')
    except Exception:                                                     # noqa: BLE001
        pass


# ---------------------------------------------------------------------------
# Stand-in database: the day-end sales query answers from SALES_ROWS, and every
# other statement is an empty result.
# ---------------------------------------------------------------------------
class Cur:
    description = None
    rowcount = 0

    def execute(self, sql, params=None):
        self.description = None
        self.rowcount = 0

    def executemany(self, sql, seq):
        pass

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
    flat = ' '.join(str(sql).split())
    if fetch_all and 'scoped_total' in flat:
        return list(SALES_ROWS)
    if fetch_all:
        return []
    if fetch_one:
        return None
    return True


wp = types.ModuleType('weasyprint')
wp.HTML = type('HTML', (), {
    '__init__': lambda self, *a, **k: None,
    'write_pdf': lambda self, *a, **k: b'',
    'render': lambda self, *a, **k: types.SimpleNamespace(pages=[]),
})
wp.CSS = type('CSS', (), {'__init__': lambda self, *a, **k: None})
sys.modules.setdefault('weasyprint', wp)

import db_helper                                                          # noqa: E402

db_helper.get_db = fake_db
db_helper.execute_query = fake_execute_query
db_helper.schema_writes_allowed = lambda: False

import ConnectLink                                                        # noqa: E402

app = ConnectLink.app
app.config['TESTING'] = True

# A mixed basket (USD 300: USD 100 Hardware, USD 200 Furniture) and a sale that
# is entirely Hardware. `scoped_total` is the money on the rows' lines.
MIXED = (1, 'T1', 1, 'Mrs G', 300.0, 'cash', dt.datetime(2026, 11, 2, 10, 0),
         [{'product_name': 'Cement', 'quantity': 1, 'price': 100.0, 'cost_at_time': 60.0}],
         100.0, 1, 'Shurugwi')
HARDWARE_ONLY = (2, 'T2', 1, 'Mrs G', 150.0, 'card', dt.datetime(2026, 11, 2, 11, 0),
                 [{'product_name': 'Nails', 'quantity': 3, 'price': 50.0, 'cost_at_time': 30.0}],
                 150.0, 1, 'Shurugwi')
FURNITURE_ONLY_MIXED = (1, 'T1', 1, 'Mrs G', 300.0, 'cash', dt.datetime(2026, 11, 2, 10, 0),
                        [{'product_name': 'Chair', 'quantity': 2, 'price': 100.0, 'cost_at_time': 50.0}],
                        200.0, 1, 'Shurugwi')
WHOLE_MIXED = (1, 'T1', 1, 'Mrs G', 300.0, 'cash', dt.datetime(2026, 11, 2, 10, 0),
               [{'product_name': 'Cement', 'quantity': 1, 'price': 100.0, 'cost_at_time': 60.0},
                {'product_name': 'Chair', 'quantity': 2, 'price': 100.0, 'cost_at_time': 50.0}],
               300.0, 1, 'Shurugwi')


def day_end(dept):
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['userid'] = 1
        sess['branch_id'] = 1
        sess['branch_name'] = 'Shurugwi'
        sess['branch_chosen'] = True
        sess['department'] = dept
        sess['department_chosen'] = True
    resp = client.get('/api/transactions/day-end?date=2026-11-02')
    return resp.status_code, (resp.get_json() or {})


def rows_of(data):
    return ((data.get('cashiers') or [{}])[0]).get('transactions') or []


# ---------- Hardware: the mixed sale contributes its Hardware line only ------
SALES_ROWS[:] = [MIXED, HARDWARE_ONLY]
status, data = day_end('hardware')
check('the Hardware day-end answers', status == 200 and data.get('success') is True, status)
check('Total Sales is the Hardware share, not both receipts',
      data.get('grand_total') == 250.0, data.get('grand_total'))
check('the cash bucket holds the Hardware line of the mixed sale',
      (data.get('payment_methods') or {}).get('cash') == 100.0, data.get('payment_methods'))
check('the card bucket is untouched',
      (data.get('payment_methods') or {}).get('card') == 150.0, data.get('payment_methods'))
check('the branch total is the share too',
      ((data.get('branches') or [{}])[0]).get('total') == 250.0, data.get('branches'))
check('the report says it is describing Hardware',
      data.get('department_scoped') is True and data.get('department_label') == 'Hardware',
      (data.get('department_scoped'), data.get('department_label')))

by_number = {r['transaction_number']: r for r in rows_of(data)}
mixed_row = by_number.get('T1', {})
check('the mixed row is counted at its Hardware money', mixed_row.get('total') == 100.0, mixed_row)
check("the mixed row still names the customer's receipt total",
      mixed_row.get('receipt_total') == 300.0, mixed_row)
check('the mixed row is flagged as scoped', mixed_row.get('department_scoped') is True)
check('a sale wholly in Hardware is not flagged',
      by_number.get('T2', {}).get('department_scoped') is False, by_number.get('T2'))

# ---------- Furniture: the same receipt, the other shelf's money -------------
SALES_ROWS[:] = [FURNITURE_ONLY_MIXED]
status, data = day_end('furniture')
check('the Furniture day-end counts the Furniture line',
      data.get('grand_total') == 200.0, data.get('grand_total'))
check('and calls itself Furniture',
      data.get('department_label') == 'Furniture', data.get('department_label'))

# ---------- All: whole receipts, and a sale is never split here -------------
SALES_ROWS[:] = [WHOLE_MIXED, HARDWARE_ONLY]
status, data = day_end('all')
check('the All view is the whole shop', data.get('grand_total') == 450.0, data.get('grand_total'))
check('the All view is not marked as department scoped',
      data.get('department_scoped') is False, data.get('department_scoped'))
check('no row is flagged as scoped on All',
      all(r.get('department_scoped') is False for r in rows_of(data)),
      [(r.get('transaction_number'), r.get('department_scoped')) for r in rows_of(data)])

print()
ok = all(r.startswith('PASS') for r in RESULTS)
print('FAILURES: 0' if ok else 'FAILURES: %d' % sum(1 for r in RESULTS if r.startswith('FAIL')))
sys.exit(0 if ok else 1)
