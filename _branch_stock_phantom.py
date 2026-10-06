"""Find (and optionally remove) Shurugwi product_stock rows it never earned.

WHY THIS EXISTS
---------------
`ensure_branches_schema()` seeds a Shurugwi `product_stock` row for every product
that pre-dates per-branch stock. That seed had no per-database guard, and
`_ensure_db_initialized()`'s flag is per WORKER (a fresh False on every process
start and every Render deploy), so the seed re-ran on every boot. Any product
created at Chegutu therefore picked up a Shurugwi row on the next deploy, seeded
from `products.stock` -- the COMPANY total -- so Shurugwi appeared to hold stock it
had never received, and its till stopped hiding the item (see run1hardware:
stocked_here is "does this branch have a product_stock row at all").

The code is fixed: the seed now only touches products with NO branch rows at all.
This script cleans up the rows the old code already wrote.

Default mode is READ-ONLY: it prints the suspects and the evidence for each one.
Nothing is changed until you pass --apply, and even then every deleted row and FIFO
layer is copied into a backup table first.

USAGE
-----
    python _branch_stock_phantom.py                 # report only
    python _branch_stock_phantom.py --apply         # remove the confirmed phantoms
    python _branch_stock_phantom.py --dsn "postgresql://..."   # override the URL

Exit codes: 0 = done, 1 = stopped on an error (nothing was changed), 2 = the
database could not be reached (Render only accepts whitelisted addresses).

A row is only ever removed when it is a row for the first branch on a product that
OTHER branches stock AND the first branch has no evidence of ever receiving it:

    * no stock_additions row for that branch,
    * no FIFO layer there other than the 'opening'/'backfill' pair the same buggy
      boot created,
    * no sale containing the product at that branch.

An item that genuinely arrived (a POS Add Stock, a transfer, a bulk upload) or was
genuinely sold there is never touched.
"""

import os
import sys

import psycopg2

DEFAULT_DSN = (
    "postgresql://connectlinkdata_user:RsYLVxq6lzCBXV7m3e2drdiNMebYBFIC"
    "@dpg-d4m0bqggjchc73avg3eg-a.oregon-postgres.render.com/connectlinkdata"
)

# The branch the buggy boot seeded into. Everything here is about that one shop.
FIRST_CODE = (os.getenv('BRANCH_FIRST_CODE') or 'SHU').strip().upper() or 'SHU'

BACKUP_TABLE = 'product_stock_repair_backup'
LOT_BACKUP_TABLE = 'stock_lots_repair_backup'


def line(text=''):
    print(text)


def has_column(cur, table, column):
    """Is `column` on `table`? branch_id is added by a migration that can fail."""
    cur.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s AND column_name = %s
    """, (table, column))
    return cur.fetchone() is not None


def has_table(cur, table):
    cur.execute("SELECT to_regclass(%s)", ('public.' + table,))
    return cur.fetchone()[0] is not None


def find_phantoms(cur):
    """Return the phantom rows: the first branch holds it, only others earned it.

    Evidence checks degrade gracefully: if `stock_additions.branch_id` or
    `transactions.branch_id` is missing (an older database where that part of the
    migration never applied) the check falls back to "the product has no such row
    at all", which flags FEWER rows, never more.
    """
    sa_branch = has_column(cur, 'stock_additions', 'branch_id')
    tx_branch = has_column(cur, 'transactions', 'branch_id')
    tx_voided = has_column(cur, 'transactions', 'voided')

    additions_where = "sa.branch_id = ps.branch_id" if sa_branch else "TRUE"
    sales_where = "t.branch_id = ps.branch_id" if tx_branch else "TRUE"
    if tx_voided:
        sales_where += " AND COALESCE(t.voided, FALSE) = FALSE"

    cur.execute(f"""
        SELECT p.id,
               p.name,
               ps.stock                       AS branch_stock,
               ps.min_stock_level,
               p.stock                        AS catalogue_total,
               COALESCE((SELECT SUM(a.stock) FROM product_stock a
                         WHERE a.product_id = p.id
                           AND a.branch_id <> ps.branch_id), 0) AS other_branches,
               COALESCE((SELECT SUM(a.stock) FROM product_stock a
                         WHERE a.product_id = p.id), 0) AS all_branches,
               (SELECT COUNT(*) FROM stock_additions sa
                WHERE sa.product_id = p.id AND ({additions_where})) AS additions_here,
               (SELECT COUNT(*) FROM stock_lots sl
                WHERE sl.product_id = p.id AND sl.branch_id = ps.branch_id
                  AND COALESCE(sl.source, '') NOT IN ('opening', 'backfill'))
                                                   AS real_lots_here,
               (SELECT COUNT(*) FROM transactions t
                JOIN transaction_items ti ON ti.transaction_id = t.id
                WHERE ti.product_id = p.id AND ({sales_where})) AS sales_here
        FROM product_stock ps
        JOIN products p ON p.id = ps.product_id
        JOIN branches b ON b.id = ps.branch_id
        WHERE b.code = %s
        ORDER BY p.name
    """, (FIRST_CODE,))

    phantoms = []
    for row in cur.fetchall():
        (pid, name, branch_stock, min_level, catalogue_total, other_branches,
         all_branches, additions_here, real_lots_here, sales_here) = row
        if other_branches <= 0:
            continue          # nothing else stocks it: this row is its real home
        if additions_here or real_lots_here or sales_here:
            continue          # this branch earned it somehow - leave it alone
        phantoms.append({
            'product_id': pid,
            'name': name or '',
            'branch_stock': int(branch_stock or 0),
            'min_stock_level': int(min_level or 10),
            'catalogue_total': int(catalogue_total or 0),
            'other_branches': int(other_branches or 0),
            'all_branches': int(all_branches or 0),
        })
    return phantoms


def report(cur):
    line('=' * 78)
    line(f'Phantom {FIRST_CODE} product_stock rows (read-only report)')
    line('=' * 78)

    cur.execute('SELECT id, code, name FROM branches ORDER BY id')
    for bid, code, name in cur.fetchall():
        line(f'  branch {bid:>3}  {code:<6} {name}')

    phantoms = find_phantoms(cur)

    line('')
    line(f'Suspects: {len(phantoms)} product(s) that only OTHER branches stock,')
    line(f'with no {FIRST_CODE} receipt, FIFO layer or sale behind the row.')
    line('')
    if phantoms:
        line('%-7s %-34s %7s %5s %10s %9s %7s' % (
            'id', 'product', FIRST_CODE, 'min', 'catalogue', 'other br', 'all br'))
        line('-' * 78)
        for p in phantoms:
            line('%-7d %-34s %7d %5d %10d %9d %7d' % (
                p['product_id'], p['name'][:34], p['branch_stock'],
                p['min_stock_level'], p['catalogue_total'],
                p['other_branches'], p['all_branches']))
    else:
        line('  (none - the branch holds only stock it actually received)')

    cur.execute("""
        SELECT COUNT(*) FROM products p
        WHERE p.stock IS DISTINCT FROM COALESCE(
            (SELECT SUM(ps.stock) FROM product_stock ps
             WHERE ps.product_id = p.id), 0)
    """)
    drifted = cur.fetchone()[0]
    line('')
    line(f'products.stock rows that disagree with SUM(product_stock): {drifted}')
    line('  (the boot-time recalc repairs these on the next start)')

    line('')
    line('Run with --apply to delete the suspects above and re-derive the totals.')
    return phantoms


def apply(cur, conn, phantoms):
    if not phantoms:
        line('Nothing to apply - no phantom rows found.')
        return

    ids = [p['product_id'] for p in phantoms]
    reason = ('seeded by ensure_branches_schema on a later boot: no receipt, '
              'no FIFO layer and no sale at this branch')

    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {BACKUP_TABLE} (
            product_id INTEGER,
            branch_id INTEGER,
            stock INTEGER,
            min_stock_level INTEGER,
            updated_at TIMESTAMP,
            removed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reason TEXT
        )
    """)
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {LOT_BACKUP_TABLE} (
            id INTEGER,
            product_id INTEGER,
            branch_id INTEGER,
            quantity_received INTEGER,
            quantity_remaining INTEGER,
            unit_cost DECIMAL(10,2),
            source VARCHAR(20),
            reference VARCHAR(60),
            received_at TIMESTAMP,
            removed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reason TEXT
        )
    """)

    cur.execute(f"""
        INSERT INTO {BACKUP_TABLE}
            (product_id, branch_id, stock, min_stock_level, updated_at, reason)
        SELECT ps.product_id, ps.branch_id, ps.stock, ps.min_stock_level,
               ps.updated_at, %s
        FROM product_stock ps
        JOIN branches b ON b.id = ps.branch_id
        WHERE b.code = %s AND ps.product_id = ANY(%s)
    """, (reason, FIRST_CODE, ids))

    # Only the layers that boot itself created, and only while they are untouched.
    cur.execute(f"""
        INSERT INTO {LOT_BACKUP_TABLE}
            (id, product_id, branch_id, quantity_received, quantity_remaining,
             unit_cost, source, reference, received_at, reason)
        SELECT sl.id, sl.product_id, sl.branch_id, sl.quantity_received,
               sl.quantity_remaining, sl.unit_cost, sl.source, sl.reference,
               sl.received_at, %s
        FROM stock_lots sl
        JOIN branches b ON b.id = sl.branch_id
        WHERE b.code = %s
          AND sl.product_id = ANY(%s)
          AND COALESCE(sl.source, '') IN ('opening', 'backfill')
          AND sl.quantity_remaining = sl.quantity_received
    """, (reason, FIRST_CODE, ids))

    cur.execute("""
        DELETE FROM stock_lots sl
        USING branches b
        WHERE b.id = sl.branch_id
          AND b.code = %s
          AND sl.product_id = ANY(%s)
          AND COALESCE(sl.source, '') IN ('opening', 'backfill')
          AND sl.quantity_remaining = sl.quantity_received
    """, (FIRST_CODE, ids))
    lots_removed = cur.rowcount

    cur.execute("""
        DELETE FROM product_stock ps
        USING branches b
        WHERE b.id = ps.branch_id
          AND b.code = %s
          AND ps.product_id = ANY(%s)
    """, (FIRST_CODE, ids))
    rows_removed = cur.rowcount

    # product_stock is the truth again: re-derive the shared-catalogue total.
    cur.execute("""
        UPDATE products p
        SET stock = COALESCE((SELECT SUM(ps.stock) FROM product_stock ps
                              WHERE ps.product_id = p.id), 0),
            updated_at = CURRENT_TIMESTAMP
        WHERE p.id = ANY(%s)
    """, (ids,))

    conn.commit()

    line('')
    line(f'[ok] removed {rows_removed} phantom {FIRST_CODE} product_stock row(s)')
    line(f'[ok] removed {lots_removed} opening FIFO layer(s) at {FIRST_CODE}')
    line(f'[ok] re-derived products.stock for {len(ids)} product(s)')
    line(f'[ok] originals saved in {BACKUP_TABLE} and {LOT_BACKUP_TABLE}')
    line('')
    line('Those products now read "not stocked here" at this branch, which is what')
    line('the till and the inventory expect for an item this branch never carried.')


def main():
    dsn = os.getenv('DATABASE_URL') or DEFAULT_DSN
    if '--dsn' in sys.argv:
        try:
            dsn = sys.argv[sys.argv.index('--dsn') + 1]
        except IndexError:
            line('--dsn must be followed by a connection URL.')
            return 2
    do_apply = '--apply' in sys.argv

    # An unreachable database must read as a network problem, not a traceback.
    # The usual cause is that Render only accepts connections from whitelisted
    # addresses, so a run from a laptop cannot reach it at all.
    try:
        conn = psycopg2.connect(dsn, connect_timeout=20)
    except Exception as e:                                    # noqa: BLE001
        line(f'Could not reach the database: {e}')
        line('Nothing was read and nothing was changed.')
        line('Re-run from a whitelisted address, or point it at a reachable')
        line('database with  --dsn "postgresql://user:pass@host/db"')
        return 2

    try:
        cur = conn.cursor()

        if not has_table(cur, 'product_stock') or not has_table(cur, 'branches'):
            line('This database has no multi-branch schema yet - nothing to do.')
            return 0

        phantoms = report(cur)
        if do_apply:
            apply(cur, conn, phantoms)
        else:
            # Read-only really is read-only: report() only ever SELECTs, and
            # this closes the implicit transaction the SELECTs opened.
            conn.rollback()
    except Exception as e:                                    # noqa: BLE001
        # apply() commits once, after every step has succeeded, so a failure
        # anywhere before that leaves both tables exactly as they were.
        try:
            conn.rollback()
        except Exception:                                     # noqa: BLE001
            pass
        line('')
        line(f'Stopped: {e}')
        line('Nothing was changed (the changes commit only after every step '
             'succeeds).')
        return 1
    finally:
        conn.close()

    return 0


if __name__ == '__main__':
    sys.exit(main())
