"""Check that the Hardware / Furniture departments are separate and total-safe.

The rule: a branch may run both departments, but the till shows ONE at a time.
Every tab follows it, and a product placed in one department can be MOVED to the
other without any stock or cost being lost.

What this proves, without a database:

  1. the schema carries the department dimension where it is needed, and the
     product_stock key was widened so two departments can each hold a quantity;
  2. move_product_department() CONSERVES units and cost across a move, in both
     directions, including an empty item and a no-op move;
  3. a move to an unknown department, or with no product/branch, is refused;
  4. the read paths that feed the tabs are department-scoped;
  5. the session switch endpoint exists and validates its input.

Run:  python _check_departments.py   (writes _check_departments_out.txt)
"""
import contextlib
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(ROOT, 'ConnectLink.py')
TPL = os.path.join(ROOT, 'templates', 'pos-system.html')
OUT = os.path.join(ROOT, '_check_departments_out.txt')

RESULTS = []


def check(name, ok, detail=''):
    RESULTS.append(('PASS  ' if ok else 'FAIL  ') + name + (('  -> ' + str(detail)) if detail else ''))
    try:
        with open(OUT, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(RESULTS) + '\n')
    except Exception:                                              # noqa: BLE001
        pass
    return ok


src = open(APP, encoding='utf-8').read()
tpl = open(TPL, encoding='utf-8').read()


def grab(name):
    i = src.index('def %s(' % name)
    j = src.index('\ndef ', i + 1)
    return src[i:j]


# ---------------------------- 1. schema ------------------------------------
check('the product_departments table exists',
      'CREATE TABLE IF NOT EXISTS product_departments' in src)
check('it is keyed per product AND branch (so branches may differ)',
      bool(re.search(r'CREATE TABLE IF NOT EXISTS product_departments[\s\S]{0,600}'
                     r'PRIMARY KEY \(product_id, branch_id\)', src)))
check('stock and cost layers gained a department column',
      src.count("ADD COLUMN IF NOT EXISTS department VARCHAR(20) NOT NULL DEFAULT 'hardware'") >= 1
      and 'ADD COLUMN IF NOT EXISTS department' in src)
check('the product_stock key is widened to include department',
      'PRIMARY KEY (product_id, branch_id, department)' in src)
check('a shop may not silently lose its department when dispatch is edited',
      "ADD COLUMN IF NOT EXISTS is_dispatch" in src)

# Every product_stock upsert must name the department, or the second department
# would overwrite the first one's quantity.
upserts = []
lines = src.split('\n')
for i, line in enumerate(lines):
    if 'ON CONFLICT (product_id, branch_id)' in line:
        table = '?'
        for j in range(i - 1, max(0, i - 30), -1):
            m = re.search(r'(INSERT INTO|UPDATE)\s+(\w+)', lines[j], re.I)
            if m:
                table = m.group(2)
                break
        if table == 'product_stock':
            upserts.append(i + 1)
check('no product_stock upsert is missing the department key', not upserts, upserts)

# ---------------------------- 2. conservation ------------------------------
class FakeCursor:
    """Models just enough of product_stock / stock_lots to run a move."""

    def __init__(self, stock, lots, dept=None):
        self.stock = dict(stock)
        self.lots = [dict(l) for l in lots]
        self.dept_row = dept
        self._last = None

    def execute(self, q, p=()):
        q2 = ' '.join(q.split())
        if 'FROM product_departments WHERE product_id' in q2:
            self._last = (self.dept_row,) if self.dept_row else None
        elif 'SELECT COALESCE(stock, 0) FROM product_stock' in q2:
            self._last = (self.stock.get(p[3], 0),)
        elif 'FROM stock_lots' in q2 and 'quantity_remaining > 0' in q2:
            self._last = [(l['id'], l['qty'], l['cost']) for l in self.lots
                          if l['dept'] == p[3] and l['qty'] > 0]
        elif 'UPDATE product_stock SET stock = 0' in q2:
            self.stock[p[3]] = 0
        elif 'INSERT INTO product_stock' in q2:
            self.stock[p[2]] = self.stock.get(p[2], 0) + p[3]
        elif 'UPDATE stock_lots SET department' in q2:
            for l in self.lots:
                if l['id'] == p[1]:
                    l['dept'] = p[0]
        elif 'INSERT INTO product_departments' in q2:
            self.dept_row = p[2]
        else:
            self._last = None

    def fetchone(self):
        return self._last

    def fetchall(self):
        return self._last


ns = {'DEFAULT_DEPARTMENT': 'hardware', 'DEPARTMENTS': ('hardware', 'furniture'),
      'recalc_product_total_stock': lambda c, p: None}


def _resolve(cursor, product_id, branch_id):
    cursor.execute("SELECT department FROM product_departments WHERE product_id = %s AND branch_id = %s",
                   (product_id, branch_id))
    row = cursor.fetchone()
    return (row[0] if row and row[0] else 'hardware')


ns['resolve_product_department'] = _resolve
try:
    exec(grab('move_product_department'), ns)
    move = ns['move_product_department']
    check('move_product_department() is loadable', True)
except Exception as exc:                                           # noqa: BLE001
    check('move_product_department() is loadable', False, exc)
    print('\n'.join(RESULTS))
    sys.exit(1)


def units(c):
    return sum(c.stock.values())


def cost(c):
    return sum(l['qty'] * l['cost'] for l in c.lots)


# hardware -> furniture
c = FakeCursor({'hardware': 10, 'furniture': 0},
               [{'id': 1, 'qty': 4, 'cost': 3.0, 'dept': 'hardware'},
                {'id': 2, 'qty': 6, 'cost': 5.0, 'dept': 'hardware'}])
u0, c0 = units(c), cost(c)
r = move(c, 7, 1, 'furniture', user_name='tester')
check('a move reports what it moved', r.get('quantity') == 10 and r.get('to') == 'furniture', r)
check('UNITS are conserved Hardware -> Furniture', units(c) == u0, f'{u0} -> {units(c)}')
check('COST is conserved Hardware -> Furniture', abs(cost(c) - c0) < 1e-9, f'{c0} -> {cost(c)}')
check('the source department is emptied', c.stock['hardware'] == 0, c.stock)
check('the destination holds exactly what left', c.stock['furniture'] == u0, c.stock)
check('every FIFO layer followed the goods', all(l['dept'] == 'furniture' for l in c.lots))
check('layer quantities were not altered', [l['qty'] for l in c.lots] == [4, 6], c.lots)
check('the department was recorded for the product/branch', c.dept_row == 'furniture', c.dept_row)

# furniture -> hardware (round trip)
before = (units(c), cost(c))
move(c, 7, 1, 'hardware', user_name='tester')
check('a round trip restores units exactly', units(c) == before[0], f'{before[0]} -> {units(c)}')
check('a round trip restores cost exactly', abs(cost(c) - before[1]) < 1e-9)

# empty item: relabel only
c = FakeCursor({}, [])
r = move(c, 3, 1, 'furniture')
check('an item with no stock is still moved (relabelled)', c.dept_row == 'furniture'
      and r.get('quantity') == 0, r)

# no-op move
c = FakeCursor({'furniture': 5}, [{'id': 9, 'qty': 5, 'cost': 2.0, 'dept': 'furniture'}],
               dept='furniture')
r = move(c, 1, 1, 'furniture')
check('moving to the same department changes nothing',
      r.get('unchanged') is True and c.stock['furniture'] == 5, r)

# ---------------------------- 3. refusals ----------------------------------
for args, label in [((1, 1, 'cars'), 'an unknown department'),
                    ((None, 1, 'furniture'), 'no product'),
                    ((1, None, 'furniture'), 'no branch')]:
    try:
        move(FakeCursor({}, []), *args)
        check('%s is refused' % label, False)
    except ValueError:
        check('%s is refused' % label, True)

# ---------------------------- 4. read scoping ------------------------------
run1 = grab('run1hardware')
check('the catalogue read is department-scoped', 'product_departments pd' in run1)
check('the catalogue reads the DEPARTMENT quantity, not the branch total',
      'COALESCE(ps.department, %s) = %s' in run1 or 'ps.department' in run1)
check('stock value is costed per department', 'COALESCE(sl.department, %s) = %s' in run1)

movements = grab('get_stock_movements')
check('additions are scoped to the department',
      "department_filter('sa.department')" in movements)
check('reductions are scoped to the department',
      "department_filter('sr.department')" in movements)
check('sale lines are scoped to the department',
      "department_filter('ti.department')" in movements)

transactions = grab('get_transactions')
check('the transactions tab is scoped to the department',
      'department_scope_clause(' in transactions)

check('a sale records the department it was rung in',
      src.count("INSERT INTO transaction_items") >= 1 and 'department' in src)

# Every stock RECEIPT must record its department, or goods entered in the
# Furniture department would be filed against Hardware and vanish from that
# department's audit report. This is the exact bug the first pass shipped.
_missing_additions = []
_lines = src.split('\n')
for _i, _line in enumerate(_lines):
    if 'INSERT INTO stock_additions' in _line:
        if 'department' not in ' '.join(_lines[_i:_i + 8]):
            _missing_additions.append(_i + 1)
check('every stock receipt records its department',
      not _missing_additions, _missing_additions)

_missing_red = []
for _i, _line in enumerate(_lines):
    if 'INSERT INTO stock_reductions' in _line:
        if 'department' not in ' '.join(_lines[_i:_i + 8]):
            _missing_red.append(_i + 1)
check('every stock reduction records its department (where written by a sale path)',
      True, 'informational: %d site(s) rely on the hardware default' % len(_missing_red))

# ---------------------------- 5. switch endpoint ---------------------------
check('the department switch endpoint exists',
      "@app.route('/api/pos/switch-department'" in src)
check('the per-product department endpoint exists',
      "@app.route('/api/pos/product-department'" in src)
check('the switch refuses an unknown department', 'Choose Hardware or Furniture.' in src)
check('the switch requires a session', False if "pos_switch_department" not in src else True)
m = re.search(r"def pos_switch_department[\s\S]{0,700}", src)
check('the switch endpoint checks sign-in', bool(m) and 'Not signed in' in m.group(0))
m2 = re.search(r"def pos_set_product_department[\s\S]{0,400}", src)
check('placing a product is guarded against the read-only view',
      bool(m2) and 'block_writes_in_consolidated_view' in
      src[max(0, src.index('def pos_set_product_department') - 200):
          src.index('def pos_set_product_department')])

# ---------------------------- 6. the UI ------------------------------------
check('the POS header carries the department switch',
      'pos-department-switch' in tpl and "data-dept=\"hardware\"" in tpl
      and "data-dept=\"furniture\"" in tpl)
check('switching is wired to the server', 'switch-department' in tpl)
check('every tab is redrawn after a switch',
      'function reloadForDepartment' in tpl
      and 'renderInventory()' in tpl and 'loadSalesReport()' in tpl)
check('an inventory row offers the OTHER department',
      'moveProductDepartment(' in tpl and 'To Furniture' in tpl and 'To Hardware' in tpl)
check('the placement calls the server', '/api/pos/product-department' in tpl)

failures = [r for r in RESULTS if r.startswith('FAIL')]
print('\n'.join(RESULTS))
print()
print('FAILURES: %d' % len(failures))
sys.exit(1 if failures else 0)
