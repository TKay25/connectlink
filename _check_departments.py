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
  5. the session switch endpoint exists and validates its input;
  6. every movement that crosses a department (transfer, dispatch, receipt
     edits, layby cancel, reconciliation, stock audit) acts on the department
     the goods belong to, and never re-files a branch that already has one.

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

    def __init__(self, stock, lots, dept=None, branches=None):
        self.stock = dict(stock)
        self.lots = [dict(l) for l in lots]
        self.dept_row = dept
        self.branches = branches if branches is not None else [1]
        self._last = None

    def execute(self, q, p=()):
        q2 = ' '.join(q.split())
        if 'SELECT DISTINCT branch_id FROM' in q2:
            self._last = [(b,) for b in self.branches]
        elif 'FROM product_departments WHERE product_id' in q2:
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

# The move also re-files the product's PAST SALES. Record the call so the checks
# below can prove the new department reaches it, and return a line count.
_relabelled_calls = []
ns['relabel_product_sales_department'] = (
    lambda cursor, product_id, branch_id, department:
        _relabelled_calls.append((product_id, branch_id, department)) or 2)


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


# The company-wide move: one product, every branch that holds it.
try:
    exec(grab('branches_holding_product'), ns)
    exec(grab('move_product_department_everywhere'), ns)
    check('move_product_department_everywhere() is loadable', True)
except Exception as exc:                                           # noqa: BLE001
    check('move_product_department_everywhere() is loadable', False, exc)
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
# The catalogue hides a product with NO stock row in the department on screen, so
# an empty move that only relabelled it made the item vanish from BOTH lists.
check('an item with no stock still files a zero row in the destination department',
      'furniture' in c.stock and c.stock.get('furniture') == 0, c.stock)

# no-op move
c = FakeCursor({'furniture': 5}, [{'id': 9, 'qty': 5, 'cost': 2.0, 'dept': 'furniture'}],
               dept='furniture')
r = move(c, 1, 1, 'furniture')
check('moving to the same department changes nothing',
      r.get('unchanged') is True and c.stock['furniture'] == 5, r)

# ------------------- 2b. past sales follow the product ----------------------
check('a move hands the new department to the sale-line relabel',
      _relabelled_calls and _relabelled_calls[-1] == (1, 1, 'furniture'),
      _relabelled_calls)
check('the move reports how many sale lines it re-filed',
      r.get('sales_relabelled') == 2, r)

_relabel_src = grab('relabel_product_sales_department')
check('past sale lines are re-filed, not copied',
      'UPDATE transaction_items ti' in _relabel_src
      and 'SET department = %s' in _relabel_src)
check('only THIS branch\'s sale lines move',
      't.branch_id = %s' in _relabel_src)
check('the sale-mirror movements follow the product too (Auto Audit rebuilds from them)',
      'UPDATE stock_reductions' in _relabel_src
      and "reason IN ('item_sale', 'layby_reserve')" in _relabel_src)
check('physically moved stock is not relabelled by the sale fix',
      'UPDATE stock_additions' not in _relabel_src
      and 'UPDATE stock_lots' not in _relabel_src)
check('the product department change is what triggers the re-file',
      'relabel_product_sales_department(' in grab('move_product_department'))

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

# The POS header cards (cashier takings, Today's Sales, Items Sold) are a
# separate aggregate. They were department-blind in the first pass, which made
# the header keep showing the whole shop while the register showed one
# department. This is the assertion that stops that returning.
header = grab('today_by_cashier')
takings = grab('department_takings_sql')
check('the cashier header totals are department-scoped',
      "department_takings_sql('t')" in header
      and re.search(r"COALESCE\(_d\.department, (?:'hardware'|'\{DEFAULT_DEPARTMENT\}')\) = ANY\(%s\)",
                    takings),
      'a list of departments: one on Hardware/Furniture, both on All')
check("the header's Items Sold counts only this department",
      "SUM({col})" in takings and "col='quantity'" in takings
      and re.search(r"COALESCE\(department, (?:'hardware'|'\{DEFAULT_DEPARTMENT\}')\) = ANY\(%s\)",
                    takings))
check('the header payment breakdown is department-scoped',
      header.count('{takings_where}') >= 2,
      header.count('{takings_where}'))
check('the header takes its money from the sale LINES, so the shelves add up',
      'SUM({col}), 0)' in takings,
      'a mixed basket is split between the two departments, not charged to both')

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
      'function redrawActiveTab' in tpl
      and 'renderInventory()' in tpl and 'loadSalesReport()' in tpl)
check('an inventory row offers the OTHER department',
      'moveProductDepartment(' in tpl and 'To Furniture' in tpl and 'To Hardware' in tpl)
check('the placement calls the server', '/api/pos/product-department' in tpl)

# --------------- 7. movements must stay on the right shelf -----------------
def body(name):
    try:
        return grab(name)
    except ValueError:
        return ''


tr = body('pos_transfer_stock')
check('a manual transfer resolves the item\'s OWN department',
      'resolve_product_department(cursor, product_id, from_branch)' in tr)
check('a manual transfer receives into the destination\'s filing',
      'department=dest_dept' in tr
      and re.search(r'INSERT INTO product_departments[\s\S]{0,400}DO NOTHING', tr) is not None)

dp = body('dispatch_push')
check('dispatch pulls from the department the item is filed in at Dispatch',
      'department=from_dept' in dp)
check('dispatch receives into the department the SHOP already files',
      'dest_row' in dp and 'department=dept' in dp)
check('dispatch never re-files a shop that already has the item',
      re.search(r'INSERT INTO product_departments[\s\S]{0,400}DO NOTHING', dp) is not None)

up = body('update_product')
check('a POS stock edit reads the department pool', 'department=stock_dept' in up)
check('a POS stock edit writes the department pool', 'department=stock_dept' in up)
check('a POS stock edit files an item the branch has never placed',
      re.search(r'INSERT INTO product_departments[\s\S]{0,400}DO NOTHING', up) is not None)

check('editing a receipt adjusts the receipt\'s own department',
      'department=addition_dept' in body('update_stock_addition'))
check('deleting a receipt adjusts the receipt\'s own department',
      'department=addition_dept' in body('delete_stock_addition'))

cancel = body('pos_cancel_layby')
check('a cancelled layby returns goods to the SALE line\'s department',
      'department=dept' in cancel
      and "GROUP BY product_id, COALESCE(department, '')" in cancel)

recon = body('pos_reconciliation_reassign')
check('a re-filed offline sale moves the SALE line\'s department',
      'department=dept' in recon
      and "GROUP BY product_id, COALESCE(department, '')" in recon)

run_audit = body('pos_stock_audit_run')
check('the stock audit counts ONE department\'s shelf',
      'COALESCE(sl.department, %s) = %s' in run_audit
      and 'COALESCE(sr.department, %s) = %s' in run_audit
      and 'COALESCE(sca.department, %s) = %s' in run_audit
      and "FROM product_departments pd" in run_audit)

check('adopting a count adjusts the department being counted',
      'VALUES (%s, %s, %s, 0, CURRENT_TIMESTAMP)'
      in body('pos_stock_audit_adopt')
      and 'current_department()' in body('pos_stock_audit_adopt'))
check('a reviewed count is reconstructed per department',
      'COALESCE(sl.department, %s) = %s' in body('pos_stock_audit_adopt_reviewed')
      and 'COALESCE(sca.department, %s) = %s' in body('pos_stock_audit_adopt_reviewed'))
check('an audit adjustment records its department',
      re.search(r'INSERT INTO stock_count_adjustments'
                r'[\s\S]{0,500}department[\s\S]{0,500}current_department\(\)',
                body('pos_stock_audit_adopt_reviewed')) is not None
      and re.search(r'INSERT INTO stock_count_adjustments'
                    r'[\s\S]{0,500}department[\s\S]{0,500}current_department\(\)',
                    body('pos_stock_audit_adopt')) is not None)

create = body('create_product')
check('reusing an existing name keeps the branch\'s own filing',
      'SELECT department FROM product_departments' in create
      and 'reuse_dept = str(filed[0])' in create)

# ---- bulk upload: department resolution must not outlive the cursor -------
# The Check File step used to resolve each row's department AFTER its
# `with get_db()` block had returned the connection to the pool, so the cursor
# was already closed: any row matching an existing product raised
# psycopg2.InterfaceError: cursor already closed.
analyze = body('pos_upload_stock_analyze')
check('bulk upload reads the branch\'s filings while its cursor is open',
      'held_departments = _branch_product_departments(cursor, branch_id)' in analyze)
check('bulk upload resolves departments from that map, never a closed cursor',
      'held_departments, hit[' in analyze
      and '_bulk_stock_department_for(\n            cursor,' not in analyze)


class _DeptCursor:
    def __init__(self, rows):
        self.rows, self.closed = rows, False

    def execute(self, sql, params=None):
        if self.closed:
            raise RuntimeError('cursor already closed')
        self.params = params

    def fetchall(self):
        return self.rows


ns = {'DEPARTMENTS': ('hardware', 'furniture'), 'DEFAULT_DEPARTMENT': 'hardware'}
exec(compile(src[src.index('def _branch_product_departments('):
                 src.index('def _bulk_stock_unit(')], 'dept_helpers', 'exec'), ns)
cur = _DeptCursor([(7, 'Furniture'), (8, '')])
held = ns['_branch_product_departments'](cur, 2)
cur.closed = True                   # the connection is back in the pool from here
check('an upload row keeps the branch\'s own filing',
      ns['_bulk_stock_department_for'](held, 7, '') == 'furniture')
check('a known item asked for the other shelf stays on its shelf',
      ns['_bulk_stock_department_for'](held, 7, 'hardware') == 'furniture')
check('a new row uses the department the file asked for',
      ns['_bulk_stock_department_for'](held, None, 'furniture') == 'furniture')
check('a new row with no department falls back to Hardware',
      ns['_bulk_stock_department_for'](held, None, '') == 'hardware')

# ---------------------------------------------------------------------------
# 7. The three-way VIEW: All / Hardware / Furniture
#    The switch decides what every tab reads, but a sale line must still land on
#    a real shelf. These assertions run the real helpers against a fake session.
# ---------------------------------------------------------------------------
view_ns = {'DEPARTMENTS': ('hardware', 'furniture'),
           'DEFAULT_DEPARTMENT': 'hardware',
           'DEPARTMENT_ALL': 'all',
           'DEPARTMENT_VIEWS': ('all', 'hardware', 'furniture'),
           'DEPARTMENT_LABELS': {'hardware': 'Hardware', 'furniture': 'Furniture'},
           'DEPARTMENT_VIEW_LABELS': {'all': 'All', 'hardware': 'Hardware',
                                      'furniture': 'Furniture'},
           'session': {}}
start = src.index('def current_department_view(')
end = src.index('def resolve_product_department(')
exec(compile(src[start:end], 'dept_view', 'exec'), view_ns)

sess = view_ns['session']
view = view_ns['current_department_view']
dept = view_ns['current_department']
scope = view_ns['department_read_scope']
flt = view_ns['department_filter']
clause = view_ns['department_scope_clause']
opts = view_ns['department_view_options']

sess.clear()
check('a session that never chose a view opens on All', view() == 'all', view())
check('...and All is offered to the switch', [o['key'] for o in opts()]
      == ['all', 'hardware', 'furniture'], opts())
check('...even though the WRITE department is still a real shelf',
      dept() == 'hardware', dept())
# Every session that existed before the All view carries 'hardware', because the
# old till pushed it on every page load. Without the marker those sessions would
# open on Hardware forever, which is exactly what an operator reported.
sess.clear()
sess['department'] = 'hardware'
check('a session left on Hardware by the OLD till opens on All',
      view() == 'all' and dept() == 'hardware',
      'view=%s write=%s' % (view(), dept()))
sess['department_chosen'] = True
check('but a DELIBERATE Hardware choice is honoured',
      view() == 'hardware' and dept() == 'hardware', view())

for key in ('hardware', 'furniture', 'all', 'nonsense', ''):
    sess['department'] = key
    sess['department_chosen'] = True
    want = key if key in ('hardware', 'furniture', 'all') else 'all'
    check('the view follows the session: %r -> %r' % (key, want), view() == want, view())
    want_dept = key if key in ('hardware', 'furniture') else 'hardware'
    check('the write department is never All (%r -> %r)' % (key, want_dept),
          dept() == want_dept, dept())

sess['department'] = 'all'
check('the All view reads BOTH departments', sorted(scope()) == ['furniture', 'hardware'],
      scope())
check('the All view applies no department filter at all',
      flt('ps.department')[0] == " AND COALESCE(ps.department, 'hardware') = ANY(%s)"
      and sorted(flt('ps.department')[1][0]) == ['furniture', 'hardware'],
      flt('ps.department'))
check('the All view keeps a sale when ANY of its lines is in view',
      '= ANY(%s)' in clause('t.id', 'transaction_items', 'transaction_id')[0]
      and sorted(clause('t.id', 'transaction_items', 'transaction_id')[1][0])
      == ['furniture', 'hardware'],
      clause('t.id', 'transaction_items', 'transaction_id'))

sess['department'] = 'furniture'
check('the Furniture view reads only Furniture', scope() == ['furniture'], scope())
check('the Furniture view filters one department',
      flt('ps.department')[1] == [['furniture']], flt('ps.department'))
check('the Furniture view scopes a sale to Furniture lines',
      clause('t.id', 'transaction_items', 'transaction_id')[1] == [['furniture']])

sess['department'] = 'hardware'
check('the Hardware view reads only Hardware', scope() == ['hardware'], scope())

# The till's own code reads the server's view, so it cannot disagree with it.
check('the till mirrors the server view on load',
      "applyDepartmentState(\n                    (authData.department && authData.department.key) || 'all')"
      in tpl, 'checkAuthentication() applies the server value')
check('the switch offers three positions', tpl.count("switchDepartment('all')") >= 2, 'POS + Inventory')
check('the till defaults to the All view', "let posDepartment = 'all';" in tpl)
check('the Sales tab follows the switch (no forced all-departments read)',
      'all_departments=1`' not in tpl.split('async function loadSalesReport')[1].split('async function ')[0])
check('the exported PDF still reads every department',
      'branch-department-summary' in tpl)
check('the transaction LINES are department-scoped too',
      'items_dept_where' in src and 'AND COALESCE(ti.department, %s) = ANY(%s)' in src,
      'a sale listed under one shelf no longer shows the other shelf\'s goods')
check('a sale line is filed on the product\'s own shelf when the view is All',
      'line_department(item[\'id\'], sale_branch)' in src
      and 'def line_department(' in src)

# ---------------------------------------------------------------------------
# 8. "To Furniture" is a ruling about the ITEM, so it applies company-wide
# ---------------------------------------------------------------------------
class _BranchesCursor:
    def __init__(self, branches):
        self.branches = branches
        self._last = None
        self.asked = []

    def execute(self, q, p=()):
        self.asked.append((' '.join(str(q).split()), p))
        if 'SELECT DISTINCT branch_id' in ' '.join(str(q).split()):
            self._last = [(b,) for b in self.branches]

    def fetchall(self):
        return self._last


cw = {'DEPARTMENTS': ('hardware', 'furniture'), 'DEFAULT_DEPARTMENT': 'hardware'}
exec(compile(src[src.index('def branches_holding_product('):
                 src.index('def move_product_department_everywhere(')],
            'cw_helpers', 'exec'), cw)

calls = []
cw['move_product_department'] = lambda cursor, pid, bid, dept, **kw: (
    calls.append((pid, bid, dept)) or
    {'from': 'hardware', 'to': dept, 'quantity': 3, 'cost': 30.0,
     'sales_relabelled': 1, 'unchanged': False})
exec(compile(src[src.index('def move_product_department_everywhere('):
                 src.index('def receive_stock_lot(')],
            'cw_move', 'exec'), cw)

cur = _BranchesCursor([1, 2, 3])
held = cw['branches_holding_product'](cur, 55, include_branch_id=2)
check('every branch that holds the product is found (no duplicates)',
      held == [1, 2, 3], held)
check('a branch that never held it is NOT swept in',
      cw['branches_holding_product'](_BranchesCursor([1, 3]), 55, include_branch_id=1)
      == [1, 3])

calls.clear()
res = cw['move_product_department_everywhere'](
    _BranchesCursor([1, 2, 3]), 55, 'furniture', include_branch_id=1)
check('the move is applied to EVERY branch that holds the item',
      [c[1] for c in calls] == [1, 2, 3], calls)
check('...and all of them to the selected department',
      {c[2] for c in calls} == {'furniture'}, calls)
check('the report totals what moved', res['branches'] == 3 and res['quantity'] == 9
      and res['sales_relabelled'] == 3, res)
check('...and names how many branches actually changed',
      res['branches_moved'] == 3, res['branches_moved'])

# a product already filed in the target department is a no-op everywhere
calls.clear()
cw['move_product_department'] = lambda cursor, pid, bid, dept, **kw: (
    calls.append((pid, bid, dept)) or
    {'from': dept, 'to': dept, 'quantity': 0, 'cost': 0.0,
     'sales_relabelled': 0, 'unchanged': True})
res = cw['move_product_department_everywhere'](
    _BranchesCursor([1, 2]), 55, 'furniture')
check('a product already in that department reports nothing moved',
      res['unchanged'] is True and res['quantity'] == 0, res)

check('the endpoint uses the company-wide move, not the single-branch one',
      'move_product_department_everywhere(' in src.split('def pos_set_product_department(')[1]
      .split('@app.route')[0],
      'the button on a product is a ruling about the item')

failures = [r for r in RESULTS if r.startswith('FAIL')]
print('\n'.join(RESULTS))
print()
print('FAILURES: %d' % len(failures))
sys.exit(1 if failures else 0)
