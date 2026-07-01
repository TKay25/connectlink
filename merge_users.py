import sys
sys.path.insert(0, r'c:\Users\tzvakasikwa\OneDrive - CBZ Bank Limited\Documents\GitHub\connectlink')
from db_helper import get_db

with get_db() as (cursor, conn):
    # Find Mrs G (Projects) and Mrs G Admin (Hardware)
    cursor.execute("SELECT id, name, email FROM connectlinkusers WHERE email LIKE '%gogwe%' OR name LIKE '%Mrs G%'")
    print('Projects users:', cursor.fetchall())
    
    cursor.execute("SELECT id, username, full_name, role FROM hardware_users WHERE username LIKE '%gadmin%' OR full_name LIKE '%Mrs G%'")
    print('Hardware users:', cursor.fetchall())
    
    cursor.execute("SELECT id, username, full_name, source_system FROM admin_users WHERE username LIKE '%gogwe%' OR username LIKE '%gadmin%' OR full_name LIKE '%Mrs G%'")
    print('Admin users:', cursor.fetchall())
