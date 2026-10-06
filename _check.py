"""Offline check for _branch_stock_phantom.py + ConnectLink.py.

The live Postgres is unreachable from this machine (DNS to Render is blocked), so
this exercises the parts that can be verified without a database:

  1. both files compile,
  2. find_phantoms() flags ONLY rows with no receipt, no real FIFO layer and no
     sale behind them, and never a row the branch genuinely earned,
  3. report() is strictly read-only,
  4. apply() writes the backups, the two deletes and the products.stock recalc,
     then commits,
  5. the boot seeder in ConnectLink.py carries its NOT EXISTS guard.

Run:  python _check.py   (writes _check_out.txt)
"""
import ast
import io
import sys
import traceback

RESULTS = []
OUT = '_check_out.txt'


def _flush():
    """Write what we have so far, so a hang or crash still leaves evidence."""
    try:
        with open(OUT, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(RESULTS) + '\n')
    except Exception:                                          # noqa: BLE001
        pass


def check(name, ok, detail=''):
    RESULTS.append(f"{'PASS' if ok else 'FAIL'}  {name}"
                   f"{('  -> ' + detail) if detail else ''}")
    _flush()


check('script started', True)

# The module under test. Imported first because it is instant; parsing the 19k-line
# ConnectLink.py is deferred to the end so a teardown can never hide the results.
import _branch_stock_phantom as phantom                      # noqa: E402

check('_branch_stock_phantom imports', True)


# ---------------------------------------------------------------- 1. compiles
# Last: parsing the 19k-line ConnectLink.py is the slowest step here, so it is
# covered by the separate _syntax_check.py instead.
try:
    with open('_branch_stock_phantom.py', encoding='utf-8') as fh:
        ast.parse(fh.read(), filename='_branch_stock_phantom.py')
    check('parses cleanly: _branch_stock_phantom.py', True)
except Exception as exc:                                  # noqa: BLE001
    check('_branch_stock_phantom.py parses cleanly', False, f'{type(exc).__name__}: {exc}')


# ------------------------------------------------------------------ 2. stubs
PHANTOM_ROWS = [
    # pid, name, branch_stock, min, catalogue, other_br, all_br, adds, lots, sales
    (10, 'Speaker A', 5, 10, 10, 5, 10, 0, 0, 0),   # pure phantom      -> FLAG
    (11, 'Speaker B', 3, 10, 6, 3, 6, 2, 0, 0),     # a real receipt    -> keep
    (12, 'Cable', 4, 10, 4, 0, 4, 0, 0, 0),         # only this branch  -> keep
    (13, 'Speaker C', 2, 10, 2, 2, 4, 0, 1, 0),     # a real FIFO layer -> keep
    (14, 'Speaker D', 1, 10, 1, 1, 2, 0, 0, 3),     # it was sold here  -> keep
]


class StubCursor:
    def __init__(self, rows=None):
        self.rows = PHANTOM_ROWS if rows is None else rows
        self.sql = []
        self.rowcount = 0
        self._result = None

    def execute(self, sql, params=None):
        self.sql.append((sql, params))
        if 'information_schema.columns' in sql:
            self._result = [(1,)]
        elif 'to_regclass' in sql:
            self._result = [('public.product_stock',)]
        elif 'FROM branches ORDER BY id' in sql:
            self._result = [(1, 'SHU', 'Shurugwi'), (2, 'CHG', 'Chegutu')]
        elif 'FROM product_stock ps' in sql and 'JOIN branches b' in sql:
            self._result = list(self.rows)
        elif sql.strip().startswith('SELECT COUNT(*)'):
            self._result = [(0,)]
        else:
            self._result = []
        if sql.strip().upper().startswith('DELETE'):
            self.rowcount = 1
        return self

    def fetchall(self):
        return self._result or []

    def fetchone(self):
        return (self._result or [(None,)])[0]

    def executed(self, needle):
        return [s for s, _ in self.sql if needle in s]


class StubConn:
    def __init__(self):
        self.committed = False
        self.rolled_back = False

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


# ------------------------------------------------- 3. find_phantoms decisions
try:
    cur = StubCursor()
    phantoms = phantom.find_phantoms(cur)
    ids = sorted(p['product_id'] for p in phantoms)
    check('find_phantoms flags only the unearned row', ids == [10], f'got {ids}')
    check('find_phantoms keeps the quantity for the report',
          bool(phantoms) and phantoms[0]['branch_stock'] == 5, str(phantoms[:1]))
    check('find_phantoms uses the branch code from BRANCH_FIRST_CODE',
          phantom.FIRST_CODE == 'SHU', phantom.FIRST_CODE)
except Exception:                                              # noqa: BLE001
    check('find_phantoms runs', False, traceback.format_exc(limit=2))

# --------------------------------------------------------- 4. report read-only
try:
    cur = StubCursor()
    buf, sys.stdout = sys.stdout, io.StringIO()
    try:
        phantom.report(cur)
        printed = sys.stdout.getvalue()
    finally:
        sys.stdout = buf
    writes = [s for s, _ in cur.sql
              if any(word in s.upper() for word in ('INSERT', 'UPDATE', 'DELETE'))]
    check('report() issues no writes', not writes, str(writes[:1])[:120])
    check('report() prints the suspect table', 'Speaker A' in printed)
    check('report() omits the rows it must keep',
          'Speaker B' not in printed and 'Cable' not in printed)
except Exception:                                              # noqa: BLE001
    check('report() runs', False, traceback.format_exc(limit=2))

# ------------------------------------------------------------------ 5. apply()
try:
    cur = StubCursor()
    conn = StubConn()
    buf, sys.stdout = sys.stdout, io.StringIO()
    try:
        phantom.apply(cur, conn, phantom.find_phantoms(StubCursor()))
        printed = sys.stdout.getvalue()
    finally:
        sys.stdout = buf
    check('apply() commits', conn.committed)
    check('apply() backs up the rows before deleting',
          bool(cur.executed('INSERT INTO ' + phantom.BACKUP_TABLE))
          and bool(cur.executed('INSERT INTO ' + phantom.LOT_BACKUP_TABLE)))
    check('apply() deletes the row and the untouched opening layers',
          bool(cur.executed('DELETE FROM stock_lots'))
          and bool(cur.executed('DELETE FROM product_stock')))
    check('apply() re-derives products.stock',
          bool(cur.executed('UPDATE products p')))
    flag_ids = [params[2] for _, params in cur.sql
                if isinstance(params, tuple) and len(params) == 3
                and isinstance(params[2], list)]
    check('apply() only touches the flagged product',
          bool(flag_ids) and all(i == [10] for i in flag_ids), str(flag_ids))
    check('apply() reports what it removed', '[ok] removed' in printed)
except Exception:                                              # noqa: BLE001
    check('apply() runs', False, traceback.format_exc(limit=2))

# ----------------------------------------- 6. the ConnectLink boot seed is guarded
try:
    src = open('ConnectLink.py', encoding='utf-8').read()
    marker = ("INSERT INTO product_stock (product_id, branch_id, stock, "
              "min_stock_level)\n                SELECT p.id, %s")
    head = src[src.index(marker):][:700]
    check('the boot seeder is guarded by NOT EXISTS',
          'WHERE NOT EXISTS (' in head
          and 'FROM product_stock ps WHERE ps.product_id = p.id' in head)
    check('the guard sits inside the seed, before its ON CONFLICT',
          head.index('WHERE NOT EXISTS') < head.index('ON CONFLICT'))
except Exception:                                              # noqa: BLE001
    check('read the seed out of ConnectLink.py', False,
          traceback.format_exc(limit=2))

# ------------------------------------ 7. main() behaves with no reachable database
try:
    real_connect = phantom.psycopg2.connect

    def refuse(*_a, **_k):
        raise RuntimeError('could not connect to server: Operation timed out')

    phantom.psycopg2.connect = refuse
    argv, sys.argv = sys.argv, ['_branch_stock_phantom.py', '--dsn',
                                'postgresql://user:pass@host/db']
    buf, sys.stdout = sys.stdout, io.StringIO()
    try:
        rc = phantom.main()
        printed = sys.stdout.getvalue()
    finally:
        sys.stdout = buf
        sys.argv = argv
        phantom.psycopg2.connect = real_connect
    check('main() fails cleanly when the database is unreachable', rc == 2,
          f'rc={rc!r}')
    check('main() promises nothing was changed',
          'Nothing was read and nothing was changed' in printed)
except Exception:                                              # noqa: BLE001
    check('main() runs', False, traceback.format_exc(limit=2))

out = '\n'.join(RESULTS)
_flush()
print(out)
print('\nFAILURES: %d' % sum(1 for r in RESULTS if r.startswith('FAIL')))
