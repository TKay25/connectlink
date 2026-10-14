"""Offline check for the in-app phantom branch-stock repair.

Verifies the new endpoints in ConnectLink.py against the SAME cases the vetted
standalone script (_branch_stock_phantom.py) is tested with, so the two can never
disagree about what a phantom is.

The heavy part -- importing ConnectLink.py -- needs a database only at request
time, so we build a fake cursor, point the helper at it, and assert the decisions.

    python _check_app_phantom_repair.py
"""
import io
import os
import re
import sys
import traceback

ROOT = os.path.dirname(os.path.abspath(__file__))

lines = []


def check(label, ok, detail=''):
    label = str(label)
    lines.append(('PASS  ' if ok else 'FAIL  ') + label + (('  -> ' + str(detail)) if detail else ''))
    return ok


# ------------------------------------------------------------------ 1. source
src = None
try:
    with open(os.path.join(ROOT, 'ConnectLink.py'), encoding='utf-8') as fh:
        src = fh.read()
    check('ConnectLink.py read', True)
except Exception as exc:                                       # noqa: BLE001
    check('ConnectLink.py read', False, f'{type(exc).__name__}: {exc}')

if src:
    try:
        import ast
        ast.parse(src)
        check('ConnectLink.py parses cleanly', True)
    except Exception as exc:                                    # noqa: BLE001
        check('ConnectLink.py parses cleanly', False, f'{type(exc).__name__}: {exc}')

    for needle, label in [
        ("@app.route('/api/branch-health/phantom-stock', methods=['GET'])",
         'the read-only report route exists'),
        ("@app.route('/api/branch-health/phantom-stock/repair', methods=['POST'])",
         'the repair route exists'),
        ("@app.route('/branch-stock-repair', methods=['GET'])",
         'the repair console page route exists'),
        ('def find_phantom_branch_stock(', 'the finder is defined'),
    ]:
        check(needle in src, label)

    # The console page must exist on disk too.
    page = os.path.join(ROOT, 'templates', 'branch_stock_repair.html')
    check('templates/branch_stock_repair.html exists', os.path.exists(page))
    if os.path.exists(page):
        with open(page, encoding='utf-8') as fh:
            html = fh.read()
        check('the console posts to the repair API',
              '/api/branch-health/phantom-stock/repair' in html)
        check('the console asks for explicit confirmation',
              "'remove'" in html or '"remove"' in html)

    # Both repair endpoints must be admin-gated.
    for route, label in [
        ('phantom_stock_report', 'the report endpoint checks for admin'),
        ('phantom_stock_repair', 'the repair endpoint checks for admin'),
    ]:
        try:
            body = src[src.index('def ' + route + '('):]
            body = body[:body.index('\n@app.route') if '\n@app.route' in body else len(body)]
            check(label, "session.get('role') != 'admin'" in body)
        except ValueError:
            check(label, False, 'function not found')

    # The runtime warning must not raise: a transfer writes its receipt after.
    try:
        fn = src[src.index('def add_branch_stock('):]
        fn = fn[:fn.index('def _branch_can_hold_stock(')]
        check('add_branch_stock warns but never raises on an unbacked credit',
              '_branch_can_hold_stock' in fn and not re.search(r'^\s*raise\b', fn, re.M))
    except ValueError:
        check('add_branch_stock warns but never raises on an unbacked credit',
              False, 'sections not found')


# --------------------------------------------- 2. finder decisions vs the stubs
# Same table the standalone script is tested with. The in-app finder reads a
# slightly different projection, so adapt it into the rows the finder expects:
#   pid, name, stock, min, other_branches, additions_here, real_lots, sales_here
CASES = [
    (10, 'Speaker A', 5, 10, 5, 0, 0, 0, True),    # pure phantom
    (11, 'Speaker B', 3, 10, 3, 2, 0, 0, False),   # a real receipt
    (12, 'Cable', 4, 10, 0, 0, 0, 0, False),       # only this branch holds it
    (13, 'Speaker C', 2, 10, 2, 0, 1, 0, False),   # a real FIFO layer
    (14, 'Speaker D', 1, 10, 1, 0, 0, 3, False),   # it was sold here
]


class StubCursor:
    """Answers the finder's queries with the case table above."""

    def __init__(self, cases=None):
        self.cases = CASES if cases is None else cases
        self.sql = []
        self.rowcount = 0
        self._last = None

    def execute(self, sql, params=None):
        self.sql.append((sql, params))
        upper = ' '.join(sql.split()).upper()
        if 'INFORMATION_SCHEMA.COLUMNS' in upper:
            self._last = 'has_column'
        elif 'FROM BRANCHES WHERE CODE' in upper:
            self._last = 'branch'
        elif 'FROM PRODUCT_STOCK PS' in upper and 'ORDER BY P.NAME' in upper:
            self._last = 'rows'
        else:
            self._last = None

    def fetchone(self):
        if self._last == 'has_column':
            return (1,)
        if self._last == 'branch':
            return (1, 'SHU', 'Shurugwi')
        return None

    def fetchall(self):
        if self._last != 'rows':
            return []
        # ps.branch_id = %s  -> only the Shurugwi rows are in scope here
        return [(pid, name, stock, mn, other, adds, lots, sales)
                for pid, name, stock, mn, other, adds, lots, sales, _flag in self.cases]

    def close(self):
        pass


# ------------------------------------------------------------------ 3. exercise
try:
    # Pull the finder out of the app WITHOUT importing it (importing ConnectLink
    # runs the app's module-level work). Re-exec just the functions we need.
    ns = {
        'BRANCH_FIRST_CODE': 'SHU',
    }
    for fn_name in ('_phantom_first_branch', '_phantom_column', 'find_phantom_branch_stock'):
        start = src.index('def ' + fn_name + '(')
        # Walk to the next top-level def / decorator.
        m = re.search(r'\n(?=def |@app\.|# =)', src[start + 1:])
        end = start + 1 + (m.start() if m else len(src) - start - 1)
        exec(compile(src[start:end], fn_name, 'exec'), ns)          # noqa: S102

    cur = StubCursor()
    first, phantoms = ns['find_phantom_branch_stock'](cur)
    ids = sorted(p['product_id'] for p in phantoms)
    check('find_phantom_branch_stock flags ONLY the unearned row', ids == [10], f'got {ids}')
    check('it keeps the quantity for the report',
          bool(phantoms) and phantoms[0]['branch_stock'] == 5, str(phantoms[:1]))
    check('it reports the branch it checked',
          first and first[1] == 'SHU', str(first))
except Exception:                                              # noqa: BLE001
    check('find_phantom_branch_stock runs', False, traceback.format_exc(limit=2))


# --------------------------------------------- 4. a legitimate transfer is safe
try:
    # A destination branch receiving a transfer is NOT a phantom: the movement is
    # real. We assert the finder returns nothing when the branch has the receipt,
    # and that add_branch_stock only warns (never raises) when it does not yet.
    cases = [
        (20, 'Travelling Speaker', 5, 10, 0, 1, 0, 0, False),  # received by transfer
    ]
    ns2 = {'BRANCH_FIRST_CODE': 'SHU'}
    for fn_name in ('_phantom_first_branch', '_phantom_column', 'find_phantom_branch_stock'):
        start = src.index('def ' + fn_name + '(')
        m = re.search(r'\n(?=def |@app\.|# =)', src[start + 1:])
        end = start + 1 + (m.start() if m else len(src) - start - 1)
        exec(compile(src[start:end], fn_name, 'exec'), ns2)         # noqa: S102
    _f, transfer_phantoms = ns2['find_phantom_branch_stock'](StubCursor(cases))
    check('a branch that received a transfer is never flagged',
          transfer_phantoms == [], str(transfer_phantoms))
except Exception:                                              # noqa: BLE001
    check('a branch that received a transfer is never flagged', False,
          traceback.format_exc(limit=2))


print('\n'.join(lines))
failures = [l for l in lines if l.startswith('FAIL')]
print('')
print(f'FAILURES: {len(failures)}')
sys.exit(1 if failures else 0)
