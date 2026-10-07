"""READ-ONLY diagnosis: why a branch shows "Not stocked here" / phantom stock.

Prints, for the live database:
  * every branch (id, code, name) and how many product_stock rows it owns,
  * duplicate branch names (two "Chegutu" rows would split one shop's stock),
  * products with NO row at the other branch (they read "Not stocked here" there),
  * rows at BRANCH_FIRST_CODE that no receipt / FIFO layer / sale ever earned
    (the "Shurugwi holds what Chegutu captured" phantoms),
  * products whose shared total disagrees with the sum of its branch rows.

Nothing here writes: SELECTs only, then rollback. Override with --dsn.
"""
import os
import sys

import psycopg2

DEFAULT_DSN = (
    "postgresql://connectlinkdata_user:RsYLVxq6lzCBXV7m3e2drdiNMebYBFIC"
    "@dpg-d4m0bqggjchc73avg3eg-a.oregon-postgres.render.com/connectlinkdata"
)
FIRST_CODE = (os.getenv('BRANCH_FIRST_CODE') or 'SHU').strip().upper() or 'SHU'


def _has(cur, table, column):
    cur.execute("""SELECT 1 FROM information_schema.columns
                   WHERE table_schema='public' AND table_name=%s
                     AND column_name=%s""", (table, column))
    return cur.fetchone() is not None


def _count(cur, table, scoped, pid, branch):
    if scoped:
        cur.execute('SELECT COUNT(*) FROM %s WHERE product_id = %%s'
                    ' AND branch_id = %%s' % table, (pid, branch))
    else:
        cur.execute('SELECT COUNT(*) FROM %s WHERE product_id = %%s' % table,
                    (pid,))
    return cur.fetchone()[0]


def _lots(cur, pid, branch):
    cur.execute("""SELECT COALESCE(STRING_AGG(COALESCE(source,'?') || ':' ||
                   quantity_remaining, ','), 'none')
                   FROM stock_lots WHERE product_id = %s AND branch_id = %s""",
                (pid, branch))
    return cur.fetchone()[0]


def _sales(cur, scoped, pid, branch):
    if not scoped:
        return '?'
    cur.execute("""SELECT COUNT(*) FROM transaction_items ti
                   JOIN transactions t ON t.id = ti.transaction_id
                   WHERE ti.product_id = %s AND t.branch_id = %s""",
                (pid, branch))
    return cur.fetchone()[0]


def main():
    dsn = os.getenv('DATABASE_URL') or DEFAULT_DSN
    if '--dsn' in sys.argv:
        dsn = sys.argv[sys.argv.index('--dsn') + 1]
    try:
        conn = psycopg2.connect(dsn, connect_timeout=20)
    except Exception as e:                                     # noqa: BLE001
        print('Could not reach the database: %s' % e)
        return 2
    cur = conn.cursor()
    try:
        cur.execute('SELECT to_regclass(%s)', ('public.product_stock',))
        if cur.fetchone()[0] is None:
            print('No product_stock table - this build predates per-branch stock.')
            return 0

        print('== BRANCHES ==')
        cur.execute('SELECT id, code, name FROM branches ORDER BY id')
        branches = cur.fetchall()
        for bid, code, name in branches:
            cur.execute('SELECT COUNT(*), COALESCE(SUM(stock),0) '
                        'FROM product_stock WHERE branch_id = %s', (bid,))
            rows, units = cur.fetchone()
            print('  id=%-3s code=%-6s name=%-12s rows=%-5s units=%s'
                  % (bid, code, name, rows, units))
        cur.execute('SELECT LOWER(name), COUNT(*) FROM branches '
                    'GROUP BY LOWER(name) HAVING COUNT(*) > 1')
        print('  duplicate branch NAMES: %s' % (cur.fetchall() or 'none'))

        cur.execute('SELECT id FROM branches WHERE code = %s', (FIRST_CODE,))
        row = cur.fetchone()
        first = row[0] if row else None
        others = [(b, c, n) for b, c, n in branches if b != first]
        second = others[0] if others else None
        print('  first=%s  second=%s' % (first, second))

        print()
        print('== PRODUCTS WITH NO ROW AT THE OTHER BRANCH '
              '(read "Not stocked here") ==')
        if second:
            cur.execute("""
                SELECT p.id, p.name, p.category, COALESCE(p.stock, 0),
                       COALESCE((SELECT STRING_AGG(b.code || '=' || ps.stock, ' ')
                        FROM product_stock ps
                        JOIN branches b ON b.id = ps.branch_id
                        WHERE ps.product_id = p.id), 'no rows anywhere')
                FROM products p
                WHERE p.is_active = TRUE
                  AND NOT EXISTS (SELECT 1 FROM product_stock ps
                                  WHERE ps.product_id = p.id
                                    AND ps.branch_id = %s)
                ORDER BY p.id
            """, (second[0],))
            missing = cur.fetchall()
            print('  %d active product(s) with no %s row:'
                  % (len(missing), second[1]))
            for pid, name, cat, total, where in missing:
                print('    #%-5s %-26s %-11s products.stock=%-5s rows: %s'
                      % (pid, name, cat, total, where))

        print()
        print('== ROWS AT %s IT NEVER EARNED (phantoms) ==' % FIRST_CODE)
        sa = _has(cur, 'stock_additions', 'branch_id')
        tx = _has(cur, 'transactions', 'branch_id')
        if not first:
            print('  no %s branch row exists' % FIRST_CODE)
        else:
            cur.execute("""
                SELECT p.id, p.name, ps.stock, COALESCE(p.stock, 0)
                FROM product_stock ps
                JOIN products p ON p.id = ps.product_id
                WHERE ps.branch_id = %s
                  AND EXISTS (SELECT 1 FROM product_stock o
                              WHERE o.product_id = p.id AND o.branch_id <> %s)
                ORDER BY p.id
            """, (first, first))
            rows = cur.fetchall()
            print('  %d product(s) held at %s AND elsewhere:'
                  % (len(rows), FIRST_CODE))
            for pid, name, qty, total in rows:
                print('    #%-5s %-26s %s=%-5s total=%-5s receipts=%s lots=%s sales=%s'
                      % (pid, name, FIRST_CODE, qty, total,
                         _count(cur, 'stock_additions', sa, pid, first),
                         _lots(cur, pid, first),
                         _sales(cur, tx, pid, first)))

        print()
        print('== products.stock vs SUM(product_stock) DRIFT ==')
        cur.execute("""
            SELECT p.id, p.name, COALESCE(p.stock, 0),
                   COALESCE((SELECT SUM(ps.stock) FROM product_stock ps
                             WHERE ps.product_id = p.id), 0)
            FROM products p
            WHERE COALESCE(p.stock, 0) <> COALESCE((SELECT SUM(ps.stock)
                     FROM product_stock ps WHERE ps.product_id = p.id), 0)
            ORDER BY p.id
        """)
        drift = cur.fetchall()
        print('  %d product(s) disagree:' % len(drift))
        for pid, name, shared, summed in drift:
            print('    #%-5s %-26s products.stock=%-6s sum(rows)=%s'
                  % (pid, name, shared, summed))
    finally:
        conn.rollback()
        conn.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
