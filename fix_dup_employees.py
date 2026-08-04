"""Link duplicate employees between hr_employees and connectlinkusers by email.
hr_employees.user_id REFERENCES connectlinkusers(id), so we link to the
connectlinkusers row (NOT admin_users.id). admin_users stays for login only."""
from db_helper import get_db

with get_db() as (cursor, connection):
    # Find hr_employees that have matching emails in connectlinkusers but no user_id link
    cursor.execute("""
        SELECT h.id, h.email, h.first_name, h.last_name, h.user_id,
               c.id as clu_id, c.name
        FROM hr_employees h
        JOIN connectlinkusers c ON LOWER(TRIM(h.email)) = LOWER(TRIM(c.email))
        WHERE h.email IS NOT NULL AND h.email != ''
          AND (h.user_id IS NULL OR h.user_id != c.id)
    """)
    matches = cursor.fetchall()

    linked = 0
    for m in matches:
        h_id = m[0]
        email = m[1]
        first = m[2]
        last = m[3]
        clu_id = m[5]
        cursor.execute("UPDATE hr_employees SET user_id = %s WHERE id = %s", (clu_id, h_id))
        linked += 1
        print(f"Linked: {first} {last} ({email}) hr_emp_id={h_id} connectlinkusers_id={clu_id}")

    connection.commit()

    print(f"\nDone! {linked} employee(s) linked. No admin accounts were deleted.")
