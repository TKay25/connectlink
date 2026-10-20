"""Reconcile Chegutu stock after two duplicate bulk uploads (2026-10-05).

READ-ONLY BY DEFAULT. Writes a spreadsheet; changes no stock unless --apply.

What happened
-------------
`Inventory_ConnectLink_2026-10-05.xlsx` was uploaded to Chegutu twice (job 10 at
08:40, job 11 at 13:03). For 143 of the 145 products, `prev_branch_stock` for
job 10 EQUALS the uploaded quantity - the file restated stock that was already
there, and the upload ADDED it anyway (`stock = stock + qty`, never `=`).

So the legitimate figure is the stock Chegutu held BEFORE the uploads, and every
unit both jobs added was a duplicate.

The correct figure, and why sales matter
----------------------------------------
    correct = stock_before_uploads - units_sold_since_the_uploads

Removing only the duplicate while leaving the shelf figure at the pre-upload
number would silently refund sales that genuinely happened - units that left the
shop would reappear as stock. A sale is real; only the duplicate is not.

`stock_before_uploads` is `bulk_upload_items.prev_branch_stock` for job 10, the
snapshot the app took immediately before the first upload added anything.

Usage
-----
    python _reconcile_chegutu.py                 # writes the sheet, changes nothing
    python _reconcile_chegutu.py --apply         # applies the correction
    python _reconcile_chegutu.py --dsn <url>     # or set DATABASE_URL

A backup of every changed value is written before the transaction commits. The
whole correction runs in ONE transaction: if anything fails, nothing changes.

No credential is stored in this file on purpose - see the note below.
"""
import json
import os
import sys

import psycopg2

DEFAULT_DSN = None          # set DATABASE_URL, or pass --dsn

JOB_GOOD = 10               # the first upload; the second is the pure duplicate
JOB_BAD = 11                # the repeat
SHEET = '_reconcile_chegutu.xlsx'
BACKUP = '_reconcile_chegutu_backup.json'


def build_rows(cur, branch_id):
    """One row per affected product: before, now, sold, and the proposed figure."""
    # prev_branch_stock for job 10 is the snapshot taken BEFORE the first upload
    # added anything, i.e. the stock the shop genuinely held.
    #
    # "Stock now" is this product's HARDWARE stock. This reconciles a job from
    # before departments existed, so everything it touched is Hardware, and the
    # before/sold figures alongside it are Hardware too. Reading Hardware only
    # (rather than the branch total) keeps the three figures on one basis and
    # stops a later Furniture row from leaking into the comparison.
    cur.execute("""
        SELECT i.product_id, i.product_name, i.quantity, i.prev_branch_stock,
               COALESCE((SELECT SUM(ps.stock) FROM product_stock ps
                         WHERE ps.product_id = i.product_id AND ps.branch_id = %s
                           AND COALESCE(ps.department, 'hardware') = 'hardware'), 0)
        FROM bulk_upload_items i
        WHERE i.job_id = %s
        ORDER BY i.id
    """, (branch_id, JOB_GOOD))
    base = cur.fetchall()

    rows = []
    for pid, name, qty, prev, now in base:
        before = int(prev or 0)
        now_i = int(now or 0)

        # Units of this product sold at this branch since the uploads. Counted from
        # the FIRST upload onwards so the figure lines up with `before`.
        cur.execute("""
            SELECT COALESCE(SUM(ti.quantity), 0)
            FROM transaction_items ti
            JOIN transactions t ON t.id = ti.transaction_id
            WHERE ti.product_id = %s AND t.branch_id = %s
              AND COALESCE(t.voided, FALSE) = FALSE
              AND t.created_at >= (SELECT created_at FROM bulk_upload_jobs WHERE id = %s)
        """, (pid, branch_id, JOB_GOOD))
        sold = int(cur.fetchone()[0] or 0)

        # What this job (and the repeat) added, so the proposal can explain itself.
        cur.execute("""
            SELECT COALESCE(SUM(quantity), 0) FROM bulk_upload_items
            WHERE product_id = %s AND job_id = %s
        """, (pid, JOB_BAD))
        added_by_repeat = int(cur.fetchone()[0] or 0)

        want = max(0, before - sold)
        rows.append({
            'product_id': pid, 'name': name or '', 'uploaded_qty': int(qty or 0),
            'stock_before': before, 'stock_now': now_i, 'sold_since': sold,
            'added_by_repeat': added_by_repeat, 'want': want,
            'delta': now_i - want,
        })
    return rows


def write_sheet(rows, branch_name):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    head_font = Font(bold=True, color='FFFFFF', size=11)
    head_fill = PatternFill('solid', fgColor='1E293B')
    bold = Font(bold=True)
    thin = Side(style='thin', color='D0D5DD')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    over_fill = PatternFill('solid', fgColor='FDE7E9')     # too much stock
    under_fill = PatternFill('solid', fgColor='FFF4CE')    # too little

    ws = wb.active
    ws.title = 'Reconciliation'
    ws.append(['Chegutu stock reconciliation — duplicate bulk uploads of 2026-10-05'])
    ws['A1'].font = Font(bold=True, size=13)
    ws.append([])
    ws.append([
        'The same file was uploaded twice (UPL-20261005-45C149 then '
        'UPL-20261005-59D0BF). For most products the file restated the stock '
        'already held, and the upload added it again.'])
    ws.cell(row=3, column=1).font = Font(italic=True, size=10)
    ws.append([])

    cols = ['Product ID', 'Product Name', 'Stock Before Uploads', 'Stock Now',
            'Sold Since', 'Added by Repeat', 'CORRECT FIGURE', 'Change Needed']
    ws.append(cols)
    hr = ws.max_row
    for c in range(1, len(cols) + 1):
        cell = ws.cell(row=hr, column=c)
        cell.font = head_font
        cell.fill = head_fill
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

    for r in rows:
        ws.append([r['product_id'], r['name'], r['stock_before'], r['stock_now'],
                   r['sold_since'], r['added_by_repeat'], r['want'], -r['delta']])
        row = ws.max_row
        fill = over_fill if r['delta'] > 0 else (under_fill if r['delta'] < 0 else None)
        for c in range(1, len(cols) + 1):
            ws.cell(row=row, column=c).border = border
            if fill:
                ws.cell(row=row, column=c).fill = fill
        ws.cell(row=row, column=7).font = bold

    tr = ws.max_row + 1
    ws.cell(row=tr, column=1, value='TOTAL').font = bold
    ws.cell(row=tr, column=3, value=sum(r['stock_before'] for r in rows)).font = bold
    ws.cell(row=tr, column=4, value=sum(r['stock_now'] for r in rows)).font = bold
    ws.cell(row=tr, column=5, value=sum(r['sold_since'] for r in rows)).font = bold
    ws.cell(row=tr, column=7, value=sum(r['want'] for r in rows)).font = bold
    for c in range(1, len(cols) + 1):
        ws.cell(row=tr, column=c).fill = PatternFill('solid', fgColor='E7EAF0')

    for i, w in enumerate([10, 34, 18, 12, 12, 16, 16, 14], 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = f'A{hr + 1}'

    ws2 = wb.create_sheet('How to read this')
    for line in [
        'CORRECT FIGURE = Stock Before Uploads - Sold Since',
        '',
        'Stock Before Uploads  what Chegutu held immediately before the first upload',
        '                      added anything (the app recorded this itself).',
        'Stock Now             what it holds today.',
        'Sold Since            units of this product sold at Chegutu since the uploads.',
        'Added by Repeat       what the SECOND upload added (the pure duplicate).',
        'CORRECT FIGURE        before minus sold. A sale is real; only the duplicate',
        '                      is not, so sales are NOT refunded.',
        'Change Needed         positive = remove this many units.',
        '',
        'Pink rows are over-stocked. Amber rows are under-stocked, which the',
        'earlier partial correction caused; those need stock ADDING back.',
        '',
        'Nothing has been changed by producing this sheet.',
    ]:
        ws2.append([line])
    ws2.column_dimensions['A'].width = 90

    bio = __import__('io').BytesIO()
    wb.save(bio)
    return bio.getvalue()


def main():
    apply_changes = '--apply' in sys.argv
    dsn = os.getenv('DATABASE_URL') or DEFAULT_DSN
    if '--dsn' in sys.argv:
        dsn = sys.argv[sys.argv.index('--dsn') + 1]
    if not dsn:
        print('No database given. Set DATABASE_URL, or pass --dsn <url>.')
        return 2

    conn = psycopg2.connect(
        dsn, connect_timeout=30, keepalives=1, keepalives_idle=30,
        keepalives_interval=10, keepalives_count=5,
        options='-c statement_timeout=120000')
    cur = conn.cursor()
    try:
        cur.execute("SELECT branch_id FROM bulk_upload_jobs WHERE id = %s", (JOB_GOOD,))
        r = cur.fetchone()
        if not r:
            print(f'Job {JOB_GOOD} not found.')
            return 1
        branch_id = r[0]
        cur.execute("SELECT name FROM branches WHERE id = %s", (branch_id,))
        branch_name = (cur.fetchone() or ['?'])[0]

        rows = build_rows(cur, branch_id)
        over = [r for r in rows if r['delta'] > 0]
        under = [r for r in rows if r['delta'] < 0]
        excess = sum(r['delta'] for r in rows if r['delta'] > 0)
        short = -sum(r['delta'] for r in rows if r['delta'] < 0)

        blob = write_sheet(rows, branch_name)
        with open(SHEET, 'wb') as fh:
            fh.write(blob)

        print(f'Branch           : {branch_name}')
        print(f'Products affected: {len(rows)}')
        print(f'  over-stocked   : {len(over)}  (remove {excess} units)')
        print(f'  under-stocked  : {len(under)}  (add back {short} units)')
        print(f'Sheet written    : {SHEET}')
        print()
        print('Sample (first 15 needing change):')
        shown = 0
        for r in rows:
            if r['delta'] != 0 and shown < 15:
                shown += 1
                print(f"  #{r['product_id']:<6}{r['name'][:28]:<30} before={r['stock_before']:<5}"
                      f"now={r['stock_now']:<5}sold={r['sold_since']:<4}"
                      f"correct={r['want']:<5}change={-r['delta']:+d}")

        if not apply_changes:
            print()
            print('DRY RUN - nothing changed. Review the sheet, then re-run with --apply.')
            return 0

        payload = {'branch_id': branch_id, 'branch_name': branch_name,
                   'job_good': JOB_GOOD, 'job_bad': JOB_BAD,
                   'products': rows}
        with open(BACKUP, 'w', encoding='utf-8') as fh:
            json.dump(payload, fh, indent=2)
        print(f'\nBackup written: {BACKUP}')

        changed = 0
        for r in rows:
            if r['delta'] == 0:
                continue
            cur.execute("""
                INSERT INTO product_stock (product_id, branch_id, department, stock, min_stock_level, updated_at)
                VALUES (%s, %s, 'hardware', %s, 10, CURRENT_TIMESTAMP)
                ON CONFLICT (product_id, branch_id, department) DO UPDATE
                    SET stock = EXCLUDED.stock, updated_at = CURRENT_TIMESTAMP
            """, (r['product_id'], branch_id, r['want']))
            changed += 1

        cur.execute("""
            UPDATE products p SET stock = COALESCE((SELECT SUM(ps.stock) FROM product_stock ps
                                                    WHERE ps.product_id = p.id), 0),
                                  updated_at = CURRENT_TIMESTAMP
            WHERE p.id = ANY(%s)
        """, ([r['product_id'] for r in rows],))

        cur.execute("""
            INSERT INTO activity_log (action_type, description, user_name,
                                      reference_type, reference_id, details, branch_id, created_at)
            VALUES ('stock_upload_duplicate_fix', %s, 'System', 'branch', %s, %s, %s, CURRENT_TIMESTAMP)
        """, (f'Corrected duplicate bulk-upload stock in {branch_name}: {len(over)} product(s) '
              f'reduced ({excess} unit(s)), {len(under)} restored ({short} unit(s)). '
              f'The 2026-10-05 file was uploaded twice.',
              branch_id, json.dumps({'excess_units': excess, 'restored_units': short,
                                     'products_changed': changed}), branch_id))

        conn.commit()
        print(f'\nAPPLIED. {changed} product(s) corrected '
              f'({excess} units removed, {short} restored).')
        return 0
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
