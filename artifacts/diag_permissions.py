"""
Diagnostic: Why are ALL admins seeing the basic HR interface?
Run with:  .venv\\Scripts\\python.exe artifacts\\diag_permissions.py
"""
import psycopg2
import os

url = os.getenv(
    'DATABASE_URL',
    "postgresql://connectlinkdata_user:RsYLVxq6lzCBXV7m3e2drdiNMebYBFIC@dpg-d4m0bqggjchc73avg3eg-a.oregon-postgres.render.com/connectlinkdata"
)

conn = psycopg2.connect(url, connect_timeout=20)
cur = conn.cursor()

print("=" * 70)
print("1) USER_PERMISSIONS - rows with HR permissions")
print("=" * 70)
cur.execute("""
    SELECT user_type, user_id, can_manage_hr, hr_access, is_super_admin
    FROM user_permissions
    ORDER BY can_manage_hr DESC, is_super_admin DESC, user_type, user_id
""")
rows = cur.fetchall()
print(f"TOTAL ROWS: {len(rows)}")
for r in rows:
    flag = " <-- HR ADMIN" if (r[2] or r[4]) else ""
    print(f"  user_type={r[0]!r:12} user_id={r[1]!r:6} can_manage_hr={r[2]} hr_access={r[3]} is_super_admin={r[4]}{flag}")

print()
print("=" * 70)
print("2) ADMIN_USERS (logins) - source_system / source_id linking")
print("=" * 70)
cur.execute("""
    SELECT id, username, full_name, source_system, source_id
    FROM admin_users ORDER BY id
""")
for r in cur.fetchall():
    print(f"  id={r[0]!r:5} user={r[1]!r:25} source_system={r[3]!r:10} source_id={r[4]!r}")

print()
print("=" * 70)
print("3) HR_EMPLOYEES - user_id linking (admin link)")
print("=" * 70)
cur.execute("""
    SELECT id, user_id, role, first_name, last_name
    FROM hr_employees ORDER BY id
""")
for r in cur.fetchall():
    link = f"user_id={r[1]!r}" if r[1] is not None else "user_id=NULL (auto-created)"
    print(f"  emp_id={r[0]!r:5} {r[3]} {r[4]:30} role={r[2]!r:15} {link}")

print()
print("=" * 70)
print("4) Columns present in user_permissions (must include can_manage_hr, hr_access)")
print("=" * 70)
cur.execute("""
    SELECT column_name FROM information_schema.columns
    WHERE table_name='user_permissions' ORDER BY ordinal_position
""")
cols = [r[0] for r in cur.fetchall()]
print("  " + ", ".join(cols))
print()
missing = [c for c in ('can_manage_hr', 'hr_access', 'is_super_admin') if c not in cols]
if missing:
    print(f"  !! MISSING COLUMNS: {missing}  <-- this would make the HR role lookup FAIL for everyone")
else:
    print("  All required columns present.")

cur.close()
conn.close()
print("\nDone.")

