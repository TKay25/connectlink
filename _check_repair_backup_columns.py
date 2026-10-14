"""Check the removed-history query against the real backup-table schema.

The backup tables are created by the repair itself, so a column that does not
exist there is a runtime failure the first time an admin opens the history -- the
worst moment to find out. This parses the CREATE TABLE for each backup, then
extracts every rb.<column> the history query selects and confirms it exists.

    python _check_repair_backup_columns.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(ROOT, 'ConnectLink.py')

lines = []


def say(ok, msg):
    lines.append(('PASS  ' if ok else 'FAIL  ') + str(msg))
    return ok


src = open(APP, encoding='utf-8').read()


def table_columns(name):
    """Column names from CREATE TABLE IF NOT EXISTS <name> ( ... )."""
    m = re.search(r'CREATE TABLE IF NOT EXISTS\s+' + name + r'\s*\((.*?)\)',
                  src, re.S)
    if not m:
        return None
    body = m.group(1)
    cols = []
    for part in body.split(','):
        part = part.strip()
        if not part:
            continue
        first = part.split()[0].strip()
        if first.upper() in ('PRIMARY', 'UNIQUE', 'FOREIGN', 'CONSTRAINT', 'CHECK'):
            continue
        cols.append(first)
    return cols


stock_cols = table_columns('product_stock_repair_backup')
lots_cols = table_columns('stock_lots_repair_backup')

say(stock_cols is not None, 'product_stock_repair_backup CREATE TABLE was found')
say(lots_cols is not None, 'stock_lots_repair_backup CREATE TABLE was found')

if stock_cols:
    say('id' not in stock_cols,
        'product_stock_repair_backup really has NO id column (got: %s)' % ', '.join(stock_cols))

# The history endpoint: every rb.<col> it references must exist on the table.
try:
    seg = src[src.index('def phantom_stock_removed('):]
    seg = seg[:seg.index('\n@app.route', 10)]
except ValueError:
    seg = ''
    say(False, 'phantom_stock_removed() was found')

if seg and stock_cols:
    referenced = sorted(set(re.findall(r'\brb\.([a-z_]+)', seg)))
    # 'rb' aliases product_stock_repair_backup in this query.
    missing = [c for c in referenced if c not in stock_cols]
    say(not missing,
        'every rb.<column> in the history query exists on the backup table'
        + (' (missing: %s)' % ', '.join(missing) if missing else
           ' -> ' + ', '.join(referenced)))

    # The join to branches must key off a column the backup really has.
    m_join = re.search(r'LEFT JOIN branches b ON b\.id = (\w+)\.(\w+)', seg)
    say(m_join is not None and m_join.group(2) in stock_cols,
        'the query joins branches on a real backup column'
        + (' -> ' + m_join.group(0) if m_join else ''))

# The repair write path: the INSERT must name only real columns.
try:
    ins = src[src.index('INSERT INTO product_stock_repair_backup'):]
    ins = ins[:ins.index('""",')]
    insert_cols = re.findall(r'\(([^)]*)\)', ins)
    named = [c.strip() for c in insert_cols[0].split(',')] if insert_cols else []
    if named and stock_cols:
        bad = [c for c in named if c and c not in stock_cols]
        say(not bad,
            'the repair INSERT names only real backup columns'
            + (' (bad: %s)' % ', '.join(bad) if bad else ''))
except ValueError:
    say(False, 'the repair INSERT into product_stock_repair_backup was found')

print('\n'.join(lines))
failures = [l for l in lines if l.startswith('FAIL')]
print('')
print('FAILURES: %d' % len(failures))
sys.exit(1 if failures else 0)
