"""Offline check for the reverted-sale fix in the audit report (ConnectLink.py).

The complaint: the Shurugwi audit showed a speaker going out as a **sale** on the
5th and coming back as an **addition** funded by *VOID* on the 6th -- a sale
Transaction History already showed as reverted, and one that sold nothing.

A revert (and a layby cancellation) does two things at once: it writes the goods
back as a stock_additions row (funding_source 'VOID' / 'LAYBY_CANCEL') AND it
SOFT-deletes the sale, so the transaction_items row survives. The report reads its
sales from transaction_items on purpose -- it is the only source that covers every
sale, including older ones never mirrored into stock_reductions -- so BOTH halves
of one reverted sale were counted: the returned quantity inflated Sale Reductions
and, since the revert had written it back, Additions too.

No database and no browser are needed here. This checks, without one:

  1. the two columns the report now carries only for the match (the voided flag
     and voided_at on the sale, branch_id on the restore) really are at the
     positions the call site reads -- a future column reorder would otherwise
     pair the wrong rows silently,
  2. a voided sale is NOT filtered out in SQL: it is dropped only when its restore
     is inside the same window, because the two halves must move together,
  3. both sides are dropped together -- opening stock is derived as
     closing - additions + reductions, so moving one half alone would shift it by
     the returned quantity,
  4. the pairing itself, by running it: a pair whose two halves are both inside
     the window is dropped; a LONE half is left alone (a sale reverted in a later
     period really did take stock off the shelf during this one); a live sale is
     never half of a reversal; a different branch, quantity or stamp does not
     pair; two identical lines pair one-for-one,
  5. the reversal is still listed somewhere -- /api/transactions/voided -- so
     nothing is hidden by dropping it from the movements,
  6. and the pair is dropped BEFORE the movements, the per-product columns and the
     summary totals are built from these lists.

Run:  python _check_audit_void_reversals.py   (writes _check_audit_void_out.txt)
"""
import sys
import textwrap

RESULTS = []
OUT = '_check_audit_void_out.txt'
SOURCE = 'ConnectLink.py'


def _flush():
    try:
        with open(OUT, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(RESULTS) + '\n')
    except Exception:                                              # noqa: BLE001
        pass


def check(name, ok, detail=''):
    RESULTS.append(f"{'PASS' if ok else 'FAIL'}  {name}"
                   f"{('  -> ' + detail) if detail else ''}")
    _flush()


check('script started', True)

try:
    CL = open(SOURCE, encoding='utf-8').read()
    check('read ConnectLink.py', True, f'{len(CL)} chars')
except Exception as exc:                                           # noqa: BLE001
    check('read ConnectLink.py', False, f'{type(exc).__name__}: {exc}')
    print('\n'.join(RESULTS))
    print('\nFAILURES: 1')
    sys.exit(1)

# The two pieces this change added: the pairing, and where the report calls it.
# (Sliced as text and compiled on their own -- the file is far too large to have
# its parse tree held in memory here, as _check_pos_freshness.py also allows for.)
HELPERS = CL[CL.index('def _cell(row, index):'):CL.index("@app.route('/api/stock-movements'")]
CALL_START = 'sale_reversal_drop, restore_reversal_drop = _drop_finished_reversals('
CALL_BLOCK = CL[CL.index(CALL_START):CL.index('\n    if sale_reversal_drop:',
                                              CL.index(CALL_START))]

try:
    compile(HELPERS, 'ConnectLink.py:pairing', 'exec')
    compile(textwrap.dedent(CALL_BLOCK), 'ConnectLink.py:call-site', 'exec')
    check('both new pieces are valid Python', True)
except SyntaxError as exc:
    check('both new pieces are valid Python', False,
          f'{exc.msg} at line {exc.lineno}')


# ------------------------------------------- 1. the columns the call site reads
def select_columns(block):
    """The comma-separated columns of a SELECT, comments and spacing removed."""
    sql = ' '.join(line.strip() for line in block.splitlines()
                   if not line.strip().startswith('--'))
    sql = sql[sql.upper().index('SELECT ') + len('SELECT '):]
    return [c.strip() for c in sql[:sql.upper().index(' FROM ')].split(',')]


SALES_START = 'SELECT ti.id, ti.product_id, p.name as product_name, p.category,'
SALES_END = 'transaction_sales = execute_query(sales_query'
ADD_START = 'SELECT sa.id, sa.product_id, p.name as product_name, p.category,'
ADD_END = 'additions = execute_query(additions_query'
try:
    sales_block = CL[CL.index(SALES_START):CL.index(SALES_END)]
    add_block = CL[CL.index(ADD_START):CL.index(ADD_END)]
    sales_cols = select_columns(sales_block)
    add_cols = select_columns(add_block)

    check('the sale row carries the voided flag at the position read (14)',
          len(sales_cols) > 14 and sales_cols[14] == 't.voided as is_voided',
          sales_cols[14] if len(sales_cols) > 14 else f'only {len(sales_cols)} cols')
    check('and the moment it was reverted, at 15',
          len(sales_cols) > 15 and sales_cols[15] == 't.voided_at as voided_at',
          sales_cols[15] if len(sales_cols) > 15 else f'only {len(sales_cols)} cols')
    check('and the sale branch at 16, to match the restore branch',
          len(sales_cols) > 16 and sales_cols[16] == 't.branch_id as branch_id',
          sales_cols[16] if len(sales_cols) > 16 else f'only {len(sales_cols)} cols')
    check('the restore row carries the branch at the position read (12)',
          len(add_cols) > 12 and add_cols[12] == 'sa.branch_id as branch_id',
          add_cols[12] if len(add_cols) > 12 else f'only {len(add_cols)} cols')

    # 2. A voided sale is deliberately kept in the rows: the pair is judged in
    # Python, where the restore inside the same window can be seen beside it.
    check('a voided sale is not filtered out in SQL (its restore must be visible)',
          'COALESCE(t.voided' not in sales_block
          and 't.voided = FALSE' not in sales_block
          and 't.voided IS NOT TRUE' not in sales_block)
except Exception as exc:                                           # noqa: BLE001
    check('read the report queries out of ConnectLink.py', False,
          f'{type(exc).__name__}: {exc}')


# ---------------------------- 3. dropped together, and before anything counts it
try:
    report = CL[CL.index('def get_stock_movements():'):]
    report = report[:report.index("@app.route('/api/branches'")]
    call = report.index('_drop_finished_reversals(')
    merge = report.index('# Merge transaction_items sales into sales_reductions')
    movements = report.index('movements = []')
    additions_loop = report.index("'type': 'addition'")
    initial = report.index("calculated = current - period_additions.get(pid, 0)")

    check('the two halves are dropped together, not one at a time',
          'if sale_reversal_drop:' in report and 'if restore_reversal_drop:' in report)
    check('the sale half is dropped before the sales are counted',
          call < merge < movements and call < initial)
    check('the restore half is dropped before the additions are counted',
          call < additions_loop and call < initial)
    check('the reversal is still listed, so nothing is hidden by this',
          'def get_voided_transactions' in CL
          and "'/api/transactions/voided'" in CL)
except Exception as exc:                                           # noqa: BLE001
    check('read the report route out of ConnectLink.py', False,
          f'{type(exc).__name__}: {exc}')


# ------------------------------- 4. the pairing itself, run against real cases
namespace = {}
try:
    exec(compile(HELPERS, 'ConnectLink.py:pairing', 'exec'), namespace)  # noqa: S102
    drop, cell = namespace['_drop_finished_reversals'], namespace['_cell']
    check('the pairing runs on its own', callable(drop) and callable(cell))
except Exception as exc:                                           # noqa: BLE001
    check('the pairing runs on its own', False, f'{type(exc).__name__}: {exc}')
    drop, cell = None, None

# The two stamps one reverting request writes: a revert stamps added_at and
# voided_at inside one database transaction, so they are the same value.
R1 = ('2026-09-05 11:02:07',)
R2 = ('2026-09-19 08:41:55',)


def dropped(sales, restores):
    sales_drop, restore_drop = drop(sales, restores)
    return sorted(sales_drop), sorted(restore_drop)


if drop:
    try:
        check('a revert wholly inside the window is dropped from both sides',
              dropped([(1, 10, 2, R1)], [(1, 10, 2, R1)]) == ([0], [0]))
        check('a sale reverted LATER keeps its reduction (stock really did leave)',
              dropped([(1, 10, 2, R1)], []) == ([], []))
        check('a revert whose sale was EARLIER keeps its restore',
              dropped([], [(1, 10, 2, R1)]) == ([], []))
        check('a live sale is never half of a reversal',
              dropped([(1, 10, 2, None)], [(1, 10, 2, R1)]) == ([], []))
        check('two identical lines of one sale pair one-for-one',
              dropped([(1, 10, 2, R1), (1, 10, 2, R1), (1, 10, 2, R1)],
                      [(1, 10, 2, R1), (1, 10, 2, R1)]) == ([0, 1], [0, 1]))
        check('another branch does not pair',
              dropped([(1, 10, 2, R1)], [(2, 10, 2, R1)]) == ([], []))
        check('a different quantity does not pair',
              dropped([(1, 10, 2, R1)], [(1, 10, 3, R1)]) == ([], []))
        check('a different moment does not pair (two separate reverts)',
              dropped([(1, 10, 2, R1)], [(1, 10, 2, R2)]) == ([], []))
        check('a restore with no moment on it (an older row) is left alone',
              dropped([(1, 10, 2, R1)], [(1, 10, 2, None)]) == ([], []))
        check('nothing is paired by guessing',
              dropped([(1, 10, 2, None)], [(1, 10, 2, None)]) == ([], []))

        # The halves must move TOGETHER: opening stock is closing - additions +
        # reductions, so a one-sided drop would shift it by the returned quantity.
        sales = [(1, 10, 2, R1), (1, 11, 5, R2)]
        restores = [(1, 10, 2, R1), (1, 11, 5, R2), (1, 12, 7, R2)]
        sales_drop, restore_drop = dropped(sales, restores)
        check('and the quantity leaving each side is the same, so opening cannot drift',
              sales_drop == [0, 1] and restore_drop == [0, 1]
              and sum(sales[i][2] for i in sales_drop)
              == sum(restores[i][2] for i in restore_drop) == 7)
    except Exception as exc:                                       # noqa: BLE001
        check('run the pairing cases', False, f'{type(exc).__name__}: {exc}')


# 5. The call site's own expressions, against rows shaped like the queries --
#    so a wrong index in the report is caught, not only a wrong index in a copy.
try:
    def rows(sale_branch, sale_qty, voided, stamp, restore_branch, restore_qty):
        sale = [None] * 17
        sale[1], sale[5], sale[14], sale[15], sale[16] = (10, sale_qty, voided,
                                                         stamp, sale_branch)
        restore = [None] * 13
        restore[1], restore[5], restore[10], restore[12] = (10, restore_qty,
                                                            stamp, restore_branch)
        return [sale], [restore]

    def via_call_site(sales, restores):
        scope = {'_drop_finished_reversals': drop, '_cell': cell,
                 'transaction_sales': sales, 'additions': restores}
        exec(compile(textwrap.dedent(CALL_BLOCK), '<call-site>', 'exec'),  # noqa: S102
             scope)
        return (sorted(scope['sale_reversal_drop']),
                sorted(scope['restore_reversal_drop']))

    check('the report pairs a reverted sale with the goods its revert wrote back',
          via_call_site(*rows(1, 2, True, R1, 1, 2)) == ([0], [0]))
    check('and leaves a voided sale alone when its restore is outside the window',
          via_call_site(*rows(1, 2, True, R1, 1, None)) == ([], []))
except Exception as exc:                                           # noqa: BLE001
    check('run the report call site against shaped rows', False,
          f'{type(exc).__name__}: {exc}')


_flush()
print('\n'.join(RESULTS))
print('\nFAILURES: %d' % sum(1 for r in RESULTS if r.startswith('FAIL')))


