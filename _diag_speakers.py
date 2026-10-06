"""Read-only diagnostic: where is the "speaker" stock and how is it scoped?

Answers the report that Shurugwi shows speaker items (and stock) that were
"only added to Chegutu". Purely SELECTs; nothing is written.
"""
import os
import psycopg2

URL = os.getenv(
    'DATABASE_URL',
    "postgresql://connectlinkdata_user:RsYLVxq6lzCBXV7m3e2drdiNMebYBFIC@dpg-d4m0bqggjchc73avg3eg-a.oregon-postgres.render.com/connectlinkdata",
)

conn = psycopg2.connect(URL, connect_timeout=20)
cur = conn.cursor()

out = []
def p(*a):
    out.append(' '.join(str(x) for x in a))

p('=== BRANCHES ===')
cur.execute("SELECT id, code, name FROM branches ORDER BY id")
branches = cur.fetchall()
for r in branches:
    p(r)

p('\n=== SPEAKER PRODUCTS (name ILIKE %speaker%) ===')
cur.execute("""
    SELECT id, name, stock, is_active, buy_price, sell_price
    FROM products
    WHERE name ILIKE '%%speaker%%'
    ORDER BY id
""")
rows = cur.fetchall()
p('count =', len(rows))
for r in rows:
    p(r)

p('\n=== product_stock rows for those products ===')
cur.execute("""
    SELECT ps.product_id, ps.branch_id, b.name, ps.stock
    FROM product_stock ps
    LEFT JOIN branches b ON b.id = ps.branch_id
    WHERE ps.product_id IN (SELECT id FROM products WHERE name ILIKE '%%speaker%%')
    ORDER BY ps.product_id, ps.branch_id
""")
for r in cur.fetchall():
    p(r)

p('\n=== sample: products with NO Shurugwi row but stock elsewhere ===')
cur.execute("""
    SELECT p.id, p.name, p.stock,
           COALESCE((SELECT SUM(stock) FROM product_stock ps WHERE ps.product_id=p.id),0) AS total_branch
    FROM products p
    WHERE p.name ILIKE '%%speaker%%'
      AND NOT EXISTS (SELECT 1 FROM product_stock ps WHERE ps.product_id=p.id AND ps.branch_id=(SELECT id FROM branches WHERE code='SHU'))
      AND EXISTS (SELECT 1 FROM product_stock ps WHERE ps.product_id=p.id)
    ORDER BY p.id
""")
for r in cur.fetchall():
    p(r)

p('\n=== activity_log entries for speaker product creations ===')
cur.execute("""
    SELECT id, action_type, description, branch_id, username, created_at
    FROM activity_log
    WHERE description ILIKE '%%speaker%%'
    ORDER BY id DESC
    LIMIT 40
""")
for r in cur.fetchall():
    p(r)

p('\n=== does activity_log even have a branch_id column? ===')
cur.execute("""
    SELECT column_name, data_type FROM information_schema.columns
    WHERE table_name='activity_log' ORDER BY ordinal_position
""")
for r in cur.fetchall():
    p(r)

conn.close()

with open('_diag_speakers_out.txt', 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(out))
print('done; see _diag_speakers_out.txt')
