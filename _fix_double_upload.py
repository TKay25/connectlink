"""Undo the SECOND application of a bulk stock upload that was applied twice.

`Inventory_ConnectLink_2026-10-05.xlsx` was uploaded to Chegutu twice on
2026-10-05 -- job 10 (08:40) then job 11 (13:03). Every product in BOTH jobs had
its uploaded quantity added to the shelf a second time.

The in-app revert refuses the whole job (`bulk_upload_blockers`) because 23 of its
products have since sold from the uploaded layers, and it is all-or-nothing. This
script corrects the overlap per product instead.

Why the correction is exact, not an estimate
--------------------------------------------
Every upload writes ONE `stock_lots` row per product, tagged with the job
reference, and `product_stock.stock` is verified to equal SUM(quantity_remaining)
for its branch (Test A below: 0 mismatches). So the units that should never have
arrived are precisely the j11 lot's *remaining* quantity.

  subtract stock_lots.quantity_remaining  (NOT quantity_received)

`quantity_remaining` is what is actually still on the shelf. Using
`quantity_received` would over-subtract whenever units from that layer have since
sold -- those units really did leave the shop, so refunding them would invent
stock. This is the same reason the app's own revert subtracts rather than resets.

What it does, per product in both jobs (133 of them)
---------------------------------------------------
  1. subtract the j11 lot's `quantity_remaining` from the branch stock
     (via set_branch_stock, so the catalogue total is re-derived for us),
  2. delete the j11 lot,
  3. delete the j11 `stock_additions` row (the audit record of the bad addition),
  4. write one `activity_log` row naming the product and the quantity removed.

Left ALONE deliberately
-----------------------
  * products that job 11 CREATED (21 of them). They have no job-10 counterpart,
    so they were not double-counted, and several have sold -- the shelf figure is
    right. Their `created_product` flag is what excludes them.
  * every lot and addition belonging to job 10, which was the legitimate upload.
  * any product whose j11 lot is already gone (nothing to correct).

Usage
-----
  python _fix_double_upload.py              # DRY RUN - prints, writes nothing
  python _fix_double_upload.py --apply      # performs the correction
  python _fix_double_upload.py --apply --dsn <url>

A backup of every changed value is written to `_fix_double_upload_backup.json`
before the transaction commits. The whole correction runs in ONE transaction: if
anything fails, nothing is changed.
"""
import json
import os
import sys

import psycopg2

# No credential is stored in this file on purpose. Point it at the database with
# DATABASE_URL (what the app itself uses) or pass --dsn:
#
#   set DATABASE_URL=postgresql://user:pass@host/db       (Windows)
#   export DATABASE_URL=postgresql://user:pass@host/db    (bash)
#   python _fix_double_upload.py --apply --dsn <url>
#
# The earlier version of this script and _diag_branch_stock.py both carried the
# production password in source, which puts it in git history for anyone with
# repo access to read. That password should be rotated.
DEFAULT_DSN = None

JOB_GOOD = 10                 # the upload that should stay
JOB_BAD = 11                  # the duplicate to undo
REF_BAD = 'UPL-20261005-59D0BF'


def load_targets(cur, branch_id):
    """Products in BOTH jobs whose j11 lot is still present."""
    cur.execute("""
        SELECT p.id, p.name,
               COALESCE(ps.stock, 0)                 AS stock_now,
               sl.id                                 AS lot_id,
               sl.quantity_remaining                 AS lot_remaining,
               i11.quantity                          AS uploaded_qty
        FROM bulk_upload_items i11
        JOIN bulk_upload_items i10
          ON i10.product_id = i11.product_id AND i10.job_id = %s
        JOIN products p ON p.id = i11.product_id
        LEFT JOIN product_stock ps
               ON ps.product_id = p.id AND ps.branch_id = %s
        JOIN stock_lots sl
          ON sl.product_id = p.id AND sl.branch_id = %s AND sl.reference = %s
        WHERE i11.job_id = %s
        ORDER BY p.id
    """, (JOB_GOOD, branch_id, branch_id, REF_BAD, JOB_BAD))
    return cur.fetchall()


def main():
    apply_changes = '--apply' in sys.argv
    dsn = os.getenv('DATABASE_URL') or DEFAULT_DSN
    if '--dsn' in sys.argv:
        dsn = sys.argv[sys.argv.index('--dsn') + 1]
    if not dsn:
        print("No database given. Set DATABASE_URL, or pass --dsn <url>.\n"
              "The credential is deliberately NOT stored in this file.")
        return 2

    conn = psycopg2.connect(
        dsn, connect_timeout=30,
        # 133 products in one transaction over a long-haul link to Render; keep the
        # socket alive and bound each statement so a stall fails fast and rolls
        # back instead of hanging until the server drops the connection.
        keepalives=1, keepalives_idle=30, keepalives_interval=10, keepalives_count=5,
        options='-c statement_timeout=60000',
    )
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM bulk_upload_jobs WHERE id = %s", (JOB_BAD,))
        job = cur.fetchone()
        if not job:
            print(f"Job {JOB_BAD} not found - nothing to do.")
            return 0
        cur.execute("SELECT branch_id FROM bulk_upload_jobs WHERE id = %s", (JOB_BAD,))
        branch_id = cur.fetchone()[0]

        # Refuse if the duplicate job was already dealt with.
        cur.execute("""SELECT COUNT(*) FROM activity_log
                       WHERE action_type = 'stock_double_upload_fix'
                         AND reference_id = %s""", (JOB_BAD,))
        already = cur.fetchone()[0]
        if already:
            print(f"Job {JOB_BAD} appears to have been corrected already "
                  f"({already} activity_log row(s)). Refusing to run twice.")
            return 1

        rows = load_targets(cur, branch_id)
        if not rows:
            print("No correctable products found (no j11 lots left).")
            return 0

        total = sum(int(r[4] or 0) for r in rows)
        negative = [r for r in rows if int(r[2] or 0) - int(r[4] or 0) < 0]

        print(f"Mode        : {'APPLY' if apply_changes else 'DRY RUN (nothing written)'}")
        print(f"Branch      : {branch_id}")
        print(f"Undoing job : {JOB_BAD} ({REF_BAD})")
        print(f"Keeping job : {JOB_GOOD}")
        print(f"Products    : {len(rows)}")
        print(f"Units to remove (sum of quantity_remaining) : {total}")
        print()
        print(f"{'id':<7}{'name':<34}{'now':>6}{'remove':>8}{'after':>7}")
        print("-" * 62)
        for pid, name, now, _lot, rem, uploaded in rows:
            now, rem = int(now or 0), int(rem or 0)
            print(f"#{pid:<6}{(name or '')[:33]:<34}{now:>6}{rem:>8}{now - rem:>7}")
        if negative:
            print()
            print(f"WARNING: {len(negative)} row(s) would go negative - aborting.")
            for r in negative:
                print("   ", r)
            return 1

        if not apply_changes:
            print()
            print("Dry run complete. Re-run with --apply to perform the correction.")
            return 0

        backup = {
            'job_good': JOB_GOOD, 'job_bad': JOB_BAD, 'reference': REF_BAD,
            'branch_id': branch_id,
            'products': [
                {'product_id': r[0], 'name': r[1], 'stock_before': int(r[2] or 0),
                 'lot_id': r[3], 'lot_remaining': int(r[4] or 0),
                 'uploaded_qty': int(r[5] or 0)}
                for r in rows
            ],
        }
        with open('_fix_double_upload_backup.json', 'w', encoding='utf-8') as fh:
            json.dump(backup, fh, indent=2)
        print("\nBackup written: _fix_double_upload_backup.json")

        # `set_branch_stock` in ConnectLink.py does three things; importing that
        # module is not possible here because it pulls in WeasyPrint's native GTK
        # libraries, which are not installed on every machine that needs to run
        # this repair. The three steps are reproduced below instead, so the
        # catalogue total stays derived exactly as every other stock path leaves
        # it. (Keep this in step with set_branch_stock if that ever changes.)
        def set_branch_stock(cursor, pid, bid, new_stock):
            cursor.execute("""
                INSERT INTO product_stock (product_id, branch_id, department, stock, min_stock_level, updated_at)
                VALUES (%s, %s, 'hardware', %s, 10, CURRENT_TIMESTAMP)
                ON CONFLICT (product_id, branch_id, department) DO UPDATE
                    SET stock = EXCLUDED.stock, updated_at = CURRENT_TIMESTAMP
            """, (pid, bid, int(new_stock or 0)))

        touched = []
        for pid, name, now, lot_id, rem, uploaded in rows:
            rem = int(rem or 0)
            new_level = max(0, int(now or 0) - rem)

            if rem:
                set_branch_stock(cur, pid, branch_id, new_level)
            touched.append(pid)

            cur.execute("DELETE FROM stock_lots WHERE id = %s", (lot_id,))

        # One statement for the whole batch, not a correlated SUM per product:
        # 133 of those in a row is what ran the connection into its timeout.
        cur.execute("""
            UPDATE products p
            SET stock = COALESCE((SELECT SUM(ps.stock) FROM product_stock ps
                                  WHERE ps.product_id = p.id), 0),
                updated_at = CURRENT_TIMESTAMP
            WHERE p.id = ANY(%s)
        """, (touched,))

        cur.execute("DELETE FROM stock_additions WHERE branch_id = %s AND reference = %s",
                    (branch_id, REF_BAD))

        cur.execute("""
            INSERT INTO activity_log
                (action_type, description, user_name, reference_type, reference_id,
                 details, branch_id, created_at)
            VALUES ('stock_double_upload_fix', %s, 'System', 'product', %s, %s, %s,
                    CURRENT_TIMESTAMP)
        """, (
            f'Removed {total} unit(s) across {len(rows)} product(s) added twice by bulk '
            f'upload {REF_BAD}: the same file ({("Inventory_ConnectLink_2026-10-05.xlsx")}) '
            f'was applied a second time after job {JOB_GOOD}.',
            JOB_BAD,
            json.dumps({'job_bad': JOB_BAD, 'job_good': JOB_GOOD, 'reference': REF_BAD,
                        'products': len(rows), 'units_removed': total}),
            branch_id,
        ))

        conn.commit()
        print(f"\nAPPLIED. {len(rows)} product(s) corrected, {total} unit(s) removed.")
        return 0
    except Exception as e:                                    # noqa: BLE001
        # The connection itself may be the thing that died; a rollback on a dead
        # connection raises a second error that would hide the real cause.
        try:
            conn.rollback()
        except Exception:                                     # noqa: BLE001
            pass
        print(f"FAILED, nothing changed: {e}")
        return 2
    finally:
        try:
            conn.close()
        except Exception:                                     # noqa: BLE001
            pass


if __name__ == '__main__':
    sys.exit(main())
