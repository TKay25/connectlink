"""Link duplicate employees between hr_employees and admin_users by email.
Does NOT delete admin_users (login depends on them)."""
from db_helper import get_db

with get_db() as (cursor, connection):
    # Find hr_employees that have matching emails in admin_users but no user_id link
    cursor.execute("""
        SELECT h.id, h.email, h.first_name, h.last_name, h.user_id,
               a.id as au_id, a.username
        FROM hr_employees h
        JOIN admin_users a ON LOWER(TRIM(h.email)) = LOWER(TRIM(a.email))
        WHERE h.email IS NOT NULL AND h.email != ''
          AND (h.user_id IS NULL OR h.user_id != a.id)
    """)
    matches = cursor.fetchall()
    
    linked = 0
    for m in matches:
        h_id = m[0]
        email = m[1]
        first = m[2]
        last = m[3]
        au_id = m[5]
        cursor.execute("UPDATE hr_employees SET user_id = %s WHERE id = %s", (au_id, h_id))
        linked += 1
        print(f"Linked: {first} {last} ({email}) hr_emp_id={h_id} admin_user_id={au_id}")
    
    connection.commit()
    
    print(f"\nDone! {linked} employee(s) linked. No admin accounts were deleted.")
