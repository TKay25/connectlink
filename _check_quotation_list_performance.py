"""Prove the Quotations tab no longer drags the whole history to the browser.

The tab used to call /api/get-quotations with no arguments, which returned EVERY
quotation with EVERY line item and EVERY Gantt task, purely so two counts could be
shown -- so the tab got slower with each quotation ever saved. The endpoint now
also answers:

  * ?summary=1 - headers plus item/task counts (no item or schedule arrays);
  * ?id=N      - one quotation in full, for the details modal and its PDF.

Both answer `data: [ ... ]`, so the existing `.find(x => x.id === id)` callers are
untouched, and the no-argument form still returns everything.

This boots ConnectLink against a recording stand-in for the database (no socket is
ever opened) and reads the JSON back. It also asserts the generation path is
still whole: save endpoints and the PDF generator are present, and the full shape
still carries `items` and `schedules`, which the editor and PDF depend on.

Run:  python _check_quotation_list_performance.py
"""
import contextlib
import io
import os
import re
import sys
import types
from datetime import date

os.environ['DATABASE_URL'] = 'postgresql://nobody@127.0.0.1:9/nodb'
os.environ['APP_ENV'] = 'development'
os.environ['FLASK_ENV'] = 'development'
os.environ.pop('ALLOW_PROD_DB_WRITE', None)

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, '_check_quotation_list_performance_out.txt')
RESULTS = []
STATEMENTS = []
sys.path.insert(0, ROOT)


def check(name, ok, detail=''):
    RESULTS.append(('PASS  ' if ok else 'FAIL  ') + name + (('  -> ' + str(detail)) if detail else ''))
    print(RESULTS[-1])
    try:
        with open(OUT, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(RESULTS) + '\n')
    except Exception:                                                     # noqa: BLE001
        pass


# ---------------------------------------------------------------------------
# Fixture: three quotations, two of them with lines and Gantt tasks.
# Header row order matches SELECT id, client_name, client_whatsapp,
# quotation_date, category, project_size, total_cost, markup_percentage, notes,
# created_by, custom_category, vat_enabled, vat_rate, vat_mode
# ---------------------------------------------------------------------------
QUOTATIONS = [
    (3, 'Nyasha Moyo', '263771000001', date(2026, 11, 1), 'kitchen', 12.5, 1500.0, 20,
     'Please confirm tiles', 'Admin', '', True, 15.5, 'exclusive'),
    (2, 'Tendai Chirwa', '', date(2026, 10, 20), 'construction_single', 80.0, 45000.0, 15,
     '', 'Admin', '', False, 15.5, 'exclusive'),
    (1, 'Rudo Banda', '263771000002', date(2026, 9, 5), 'other', 0.0, 900.0, 30,
     '', 'Admin', 'Carport', False, 15.5, 'exclusive'),
]
KITCHEN_ITEMS = [(3, 'Base cabinets', 6, 100.0, 10, 1), (3, 'Wall units', 4, 80.0, 6, 2)]
CONSTRUCTION_ITEMS = [(2, 'Foundation', 30.0, 120.0, 3600.0, 1), (2, 'Walling', 60.0, 150.0, 9000.0, 2)]
SCHEDULES = [
    (3, 'Kitchen', date(2026, 11, 1), date(2026, 11, 10), 10, 1),
    (2, 'Foundation', date(2026, 10, 20), date(2026, 11, 18), 30, 1),
    (2, 'Walling', date(2026, 11, 19), date(2026, 12, 18), 30, 2),
]


def _flat(sql):
    return ' '.join(str(sql).split())


def _quotation_rows(sql_upper, args):
    """Apply the tab's own predicates to the fixture, so the stand-in answers
    exactly what the real query would for that WHERE/LIMIT."""
    rows = list(QUOTATIONS)
    if ' WHERE ID = ' in sql_upper:
        ids = [a for a in args if isinstance(a, int)]
        rows = [r for r in rows if r[0] in ids]
    elif ' ILIKE ' in sql_upper:
        likes = [a for a in args if isinstance(a, str)]
        if likes:
            needle = likes[0].strip('%').lower()
            rows = [r for r in rows
                    if needle in str(r[1]).lower()
                    or needle in str(r[4]).lower()
                    or needle in str(r[10]).lower()
                    or needle == str(r[0])]
    if ' LIMIT ' in sql_upper:
        caps = [a for a in args if isinstance(a, int)]
        if caps:
            rows = rows[:caps[-1]]
    return rows


class Cur:
    def __init__(self):
        self._rows = []
        self.description = None
        self.rowcount = 0

    def execute(self, sql, params=None):
        STATEMENTS.append((_flat(sql), params))
        q = _flat(sql)
        up = q.upper()
        self._rows = []
        self.description = None
        self.rowcount = 0
        args = list(params) if isinstance(params, (list, tuple)) else (
            [] if params is None else [params])

        if 'INFORMATION_SCHEMA.TABLES' in up:
            self._rows = [(True,)]
        elif 'COUNT(*)' in up and 'ANY(' in up:
            ids = list(args[0]) if args and isinstance(args[0], (list, tuple)) else []
            if 'KITCHEN_ITEMS' in up:
                source = KITCHEN_ITEMS
            elif 'SCHEDULES' in up:
                source = SCHEDULES
            else:
                source = CONSTRUCTION_ITEMS
            agg = {}
            for row in source:
                if row[0] in ids:
                    agg[row[0]] = agg.get(row[0], 0) + 1
            self._rows = list(agg.items())
        elif 'COUNT(*)' in up and ' FROM QUOTATIONS' in up:
            self._rows = [(len(_quotation_rows(up, args)),)]
        elif 'NOT EXISTS' in up and 'QUOTATION_SCHEDULES' in up:
            self._rows = []
        elif ' FROM QUOTATIONS' in up:
            self._rows = _quotation_rows(up, args)
        elif ' FROM QUOTATION_ITEMS' in up:
            self._rows = self._scoped(CONSTRUCTION_ITEMS, params)
        elif ' FROM QUOTATION_KITCHEN_ITEMS' in up:
            self._rows = self._scoped(KITCHEN_ITEMS, params)
        elif ' FROM QUOTATION_SCHEDULES' in up:
            self._rows = self._scoped(SCHEDULES, params)

    @staticmethod
    def _scoped(source, params):
        if params:
            wanted = params[0]
            if isinstance(wanted, (list, tuple)):
                return [r for r in source if r[0] in list(wanted)]
            if isinstance(wanted, int):
                return [r for r in source if r[0] == wanted]
        return list(source)

    def executemany(self, sql, seq):
        pass

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
    STATEMENTS.append((_flat(sql), params))
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


def get(path):
    STATEMENTS.clear()
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['userid'] = 1
    resp = client.get(path)
    try:
        body = resp.get_json()
    except Exception:                                                     # noqa: BLE001
        body = None
    return resp.status_code, body, list(STATEMENTS)


# ---------- the summary the tab asks for ------------------------------------
status, body, stmts = get('/api/get-quotations?summary=1&limit=500')
check('summary=1 answers', status == 200 and (body or {}).get('success') is True, status)
rows = (body or {}).get('data') or []
check('summary returns every header row', len(rows) == 3, len(rows))
check('summary carries the two counts',
      all('itemCount' in r and 'taskCount' in r for r in rows),
      [(r.get('id'), r.get('itemCount'), r.get('taskCount')) for r in rows])
by_id = {r['id']: r for r in rows}
check('a kitchen quotation counts its kitchen items',
      by_id.get(3, {}).get('itemCount') == 2, by_id.get(3))
check('a construction quotation counts its line items',
      by_id.get(2, {}).get('itemCount') == 2, by_id.get(2))
check('task counts come from the Gantt schedule',
      by_id.get(2, {}).get('taskCount') == 2 and by_id.get(3, {}).get('taskCount') == 1,
      (by_id.get(2, {}).get('taskCount'), by_id.get(3, {}).get('taskCount')))
check('summary sends NO item arrays (that is the payload that grew)',
      all('items' not in r for r in rows))
check('summary sends NO schedule arrays', all('schedules' not in r for r in rows))
check('summary states the size of the history it drew from',
      (body or {}).get('all_total') == 3 and (body or {}).get('total') == 3,
      ((body or {}).get('count'), (body or {}).get('total'), (body or {}).get('all_total')))
check('summary did not read the item tables for filtering',
      not any('ORDER BY quotation_id, item_order' in s for s, _ in stmts),
      [s[:60] for s, _ in stmts][:4])

# ---------- limit is honoured, and is the tab's bound -----------------------
status, body, _ = get('/api/get-quotations?summary=1&limit=2')
check('limit caps the summary', len((body or {}).get('data') or []) == 2,
      len((body or {}).get('data') or []))
check('the real total is still reported beside the window',
      (body or {}).get('all_total') == 3, (body or {}).get('all_total'))

# ---------- search runs on the server, over the whole history --------------
status, body, _ = get('/api/get-quotations?summary=1&q=rudo')
rows = (body or {}).get('data') or []
check('search finds a quotation that the window would not draw',
      len(rows) == 1 and rows[0]['id'] == 1, [(r.get('id'), r.get('clientName')) for r in rows])
check('search reports how many matched',
      (body or {}).get('total') == 1, (body or {}).get('total'))
status, body, _ = get('/api/get-quotations?summary=1&q=carport')
check('search matches the custom (Other) category name',
      [r['id'] for r in (body or {}).get('data') or []] == [1],
      [r.get('id') for r in (body or {}).get('data') or []])
status, body, _ = get('/api/get-quotations?summary=1&q=3')
check('search matches a quotation id',
      [r['id'] for r in (body or {}).get('data') or []] == [3],
      [r.get('id') for r in (body or {}).get('data') or []])

# ---------- one quotation, in full -----------------------------------------
status, body, stmts = get('/api/get-quotations?id=2')
rows = (body or {}).get('data') or []
check('?id= answers', status == 200 and (body or {}).get('success') is True, status)
check('?id= returns exactly that quotation', [r['id'] for r in rows] == [2],
      [r.get('id') for r in rows])
check('?id= returns it in FULL (items and schedules, for the PDF)',
      bool(rows) and len(rows[0].get('items') or []) == 2
      and len(rows[0].get('schedules') or []) == 2,
      (len(rows[0].get('items') or []) if rows else None,
       len(rows[0].get('schedules') or []) if rows else None))
check('?id= reads only that quotation\'s lines',
      all(('quotation_id = %s' in s) or 'ANY(' in s or 'INFORMATION_SCHEMA' in s.upper()
          for s, p in stmts
          if 'QUOTATION_ITEMS' in s.upper() or 'QUOTATION_SCHEDULES' in s.upper()),
      [s[:70] for s, _ in stmts if 'quotation_items' in s or 'quotation_schedules' in s])
check('?id= carries the money fields the modal formats',
      bool(rows) and rows[0].get('totalCost') == 45000.0 and rows[0].get('markup') == 15.0,
      {k: rows[0].get(k) for k in ('totalCost', 'markup', 'vatRate')} if rows else None)

status, body, _ = get('/api/get-quotations?id=999')
check('?id= for a quotation that does not exist is an empty list, not an error',
      status == 200 and (body or {}).get('data') == [], (status, body))

status, body, _ = get('/api/get-quotations?id=abc')
check('?id= refuses a non-numeric id', status == 400 and (body or {}).get('success') is False,
      (status, body))

# ---------- the old no-argument form still returns everything --------------
status, body, _ = get('/api/get-quotations')
rows = (body or {}).get('data') or []
check('the no-argument form still returns every quotation', len(rows) == 3, len(rows))
check('the no-argument form still carries items and schedules',
      all('items' in r and 'schedules' in r for r in rows))
check('the no-argument form keeps the money fields the callers .find() on',
      all('totalCost' in r and 'id' in r for r in rows))

# ---------- generation, save and PDF are still whole -----------------------
src = io.open(os.path.join(ROOT, 'ConnectLink.py'), encoding='utf-8').read()
html = io.open(os.path.join(ROOT, 'templates', 'adminpage.html'), encoding='utf-8').read()
check('the save endpoint still exists', "@app.route('/api/save-quotation'" in src
      or "/api/save-quotation" in src)
check('the quotation PDF generator is still defined client-side',
      'function generateQuotationPDF' in html)
check('the download path still reads one quotation fully',
      "get-quotations?id=" in html)
check('the editor still loads the full record (items + schedules)',
      "loadExistingQuotationForEdit" in html and 'items' in html)
check('the tab asks for the summary, not the history',
      'get-quotations?summary=1&limit=' in html)
check('the endpoint exposes the health line the log prints',
      'get-quotations: summary' in src and 'get-quotations: full' in src)

print()
ok = all(r.startswith('PASS') for r in RESULTS)
print('FAILURES: 0' if ok else 'FAILURES: %d' % sum(1 for r in RESULTS if r.startswith('FAIL')))
sys.exit(0 if ok else 1)
