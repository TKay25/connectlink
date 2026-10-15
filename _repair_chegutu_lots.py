"""Bring Chegutu's FIFO layers back in line with the corrected shelf counts.

Needed because `_reconcile_chegutu.py` corrected `product_stock.stock` but left
`stock_lots` untouched, so 138 branch rows now disagree:

    shelf (correct) != SUM(quantity_remaining) (stale)

That invariant is what the app's FIFO costing, its "only N in stock" checks and
its own phantom repair all rely on. Left alone, the next sale would cost the
wrong units and future integrity checks would report damage that is really this.

For each affected product the shelf figure is treated as TRUTH (it was derived
from the pre-upload snapshot minus sales) and the layers are adjusted to match:

  * too many layer units  -> trim from the DUPLICATE layers first, newest
                             reference first, because those are the units that
                             should never have arrived. The original
                             'reconcile'/'opening' stock is consumed last.
  * too few layer units   -> top up the OLDEST surviving layer, or create an
                             'adjustment' layer at the product's current cost if
                             none survives. Never invents units on a product
                             whose shelf is 0.

Read-only unless --apply. One transaction. Backup written before commit.

Usage
-----
    python _repair_chegutu_lots.py               # report only
    python _repair_chegutu_lots.py --apply
    python _repair_chegutu_lots.py --apply --dsn <url>     # or set DATABASE_URL
"""
import json
import os
import sys

import psycopg2

DEFAULT_DSN = None

DRIFT_SQL = """
    SELECT ps.product_id, p.name, ps.stock,
           COALESCE((SELECT SUM(sl.quantity_remaining) FROM stock_lots sl
                     WHERE sl.product_id = ps.product_id
                       AND sl.branch_id = ps.branch_id), 0) AS lots
    FROM product_stock ps
    JOIN products p ON p.id = ps.product_id
    WHERE ps.branch_id = %s
      AND ps.stock <> COALESCE((SELECT SUM(sl.quantity_remaining) FROM stock_lots sl
                                WHERE sl.product_id = ps.product_id
                                  AND sl.branch_id = ps.branch_id), 0)
    ORDER BY ps.product_id
"""


def trim_layers(cur, product_id, branch_id, surplus):
    """Take `surplus` units out of the layers, duplicate references first."""
    cur.execute("""
        SELECT id, quantity_remaining, source, reference
        FROM stock_lots
        WHERE product_id = %s AND branch_id = %s AND quantity_remaining > 0
        ORDER BY
            -- A layer created by an upload is a duplicate candidate and goes
            -- first; the shop's own opening/reconcile stock is consumed last.
            CASE WHEN reference LIKE 'UPL-%%' THEN 0 ELSE 1 END,
            -- Newest upload first, so the most recent duplicate is undone first.
            received_at DESC, id DESC
    """, (product_id, branch_id))
    left = surplus
    for lot_id, remaining, _source, _ref in cur.fetchall():
        if left <= 0:
            break
        take = min(int(remaining or 0), left)
        if take:
            cur.execute("UPDATE stock_lots SET quantity_remaining = quantity_remaining - %s "
                        "WHERE id = %s", (take, lot_id))
            left -= take
    return surplus - left


def top_up_layers(cur, product_id, branch_id, deficit):
    """Add `deficit` units back, onto the oldest surviving layer."""
    cur.execute("""
        SELECT id FROM stock_lots
        WHERE product_id = %s AND branch_id = %s
        ORDER BY received_at ASC, id ASC LIMIT 1
    """, (product_id, branch_id))
    row = cur.fetchone()
    if row:
        cur.execute("""UPDATE stock_lots
                       SET quantity_remaining = quantity_remaining + %s,
                           quantity_received = GREATEST(quantity_received,
                                                        quantity_remaining + %s)
                       WHERE id = %s""", (deficit, deficit, row[0]))
        return True
    # No layer at all survives: open one at the product's current cost so the
    # shelf has something behind it. source='adjustment' marks it as a repair,
    # not a delivery, which keeps it out of the phantom-repair's "earned" test.
    cur.execute("""SELECT COALESCE(buy_price, 0) FROM products WHERE id = %s""", (product_id,))
    cost = float((cur.fetchone() or [0])[0] or 0)
    cur.execute("""
        INSERT INTO stock_lots (product_id, branch_id, quantity_received, quantity_remaining,
                               unit_cost, source, reference, received_at)
        VALUES (%s, %s, %s, %s, %s, 'adjustment', 'reconcile-fix', CURRENT_TIMESTAMP)
    """, (product_id, branch_id, deficit, deficit, cost))
    return True


def main():
    apply_changes = '--apply' in sys.argv
    dsn = os.getenv('DATABASE_URL') or DEFAULT_DSN
    if '--dsn' in sys.argv:
        dsn = sys.argv[sys.argv.index('--dsn') + 1]
    if not dsn:
        print('No database given. Set DATABASE_URL, or pass --dsn <url>.')
        return 2
    branch_id = 2                       # Chegutu

    conn = psycopg2.connect(dsn, connect_timeout=30, keepalives=1, keepalives_idle=30,
                            keepalives_interval=10, keepalives_count=5,
                            options='-c statement_timeout=120000')
    cur = conn.cursor()
    try:
        cur.execute(DRIFT_SQL, (branch_id,))
        drift = cur.fetchall()

        print(f'Rows needing repair: {len(drift)}')
        print(f"{'id':<8}{'name':<32}{'shelf':>7}{'lots':>7}{'action':>18}")
        print('-' * 74)
        plan = []
        for pid, name, shelf, lots in drift:
            shelf, lots = int(shelf or 0), int(lots or 0)
            if lots > shelf:
                plan.append((pid, name, shelf, lots, lots - shelf, 'trim'))
                act = f'trim {lots - shelf}'
            else:
                plan.append((pid, name, shelf, lots, shelf - lots, 'topup'))
                act = f'top up {shelf - lots}'
            print(f'#{pid:<7}{(name or "")[:31]:<32}{shelf:>7}{lots:>7}{act:>18}')

        if not apply_changes:
            print('\nDRY RUN - nothing changed.')
            return 0

        payload = {'branch_id': branch_id,
                   'plan': [{'product_id': p[0], 'name': p[1], 'shelf': p[2],
                             'lots_before': p[3], 'delta': p[4], 'action': p[5]} for p in plan]}
        with open('_repair_chegutu_lots_backup.json', 'w', encoding='utf-8') as fh:
            json.dump(payload, fh, indent=2)
        print('\nBackup written: _repair_chegutu_lots_backup.json')

        fixed = 0
        for pid, name, shelf, lots, delta, action in plan:
            if action == 'trim':
                got = trim_layers(cur, pid, branch_id, delta)
                if got != delta:
                    raise RuntimeError(f'#{pid} {name}: trimmed {got} of {delta}; '
                                       f'layers would still not match the shelf')
            else:
                top_up_layers(cur, pid, branch_id, delta)
            fixed += 1

        # Prove the invariant now holds for every row we touched.
        cur.execute("""SELECT COUNT(*) FROM product_stock ps
                       WHERE ps.branch_id = %s AND ps.stock <>
                         COALESCE((SELECT SUM(sl.quantity_remaining) FROM stock_lots sl
                                   WHERE sl.product_id = ps.product_id
                                     AND sl.branch_id = ps.branch_id), 0)""", (branch_id,))
        remaining = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO activity_log (action_type, description, user_name,
                                      reference_type, reference_id, details, branch_id, created_at)
            VALUES ('stock_lots_reconciled', %s, 'System', 'branch', %s, %s, %s, CURRENT_TIMESTAMP)
        """, (f'Reconciled Chegutu FIFO layers to the corrected shelf counts: '
              f'{fixed} product(s), {len(drift)} row(s) were out of step after the '
              f'duplicate-upload correction.', branch_id,
              json.dumps({'products': fixed, 'remaining_drift': remaining}), branch_id))

        conn.commit()
        print(f'\nAPPLIED. {fixed} product(s) reconciled.')
        print(f'Rows still out of step: {remaining} (must be 0)')
        return 0 if remaining == 0 else 1
    except Exception as e:                                    # noqa: BLE001
        try:
            conn.rollback()
        except Exception:                                     # noqa: BLE001
            pass
        print(f'FAILED, nothing changed: {e}')
        return 2
    finally:
        try:
            conn.close()
        except Exception:                                     # noqa: BLE001
            pass


if __name__ == '__main__':
    sys.exit(main())
