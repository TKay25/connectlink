"""One-off patch: link existing hr_employees to connectlinkusers (FK fix).

Backstory: hr_employees.user_id REFERENCES connectlinkusers(id). A previous bug
wrote admin_users.id there (or nothing), so many employees have no valid link
and the manual "add employee" flow logged:
    insert or update on table "hr_employees" violates foreign key constraint
    "hr_employees_user_id_fkey" ... Key (user_id)=(9013) is not present in
    table "connectlinkusers".

For every employee whose user_id is NULL or points to a non-existent
connectlinkusers row, this patch:
  1. Finds the connectlinkusers row by email (creating one if missing).
  2. Sets hr_employees.user_id = connectlinkusers.id.
  3. Ensures an admin_users row exists and is linked via source_id
     (= the connectlinkusers.id) so HR login + permissions still resolve.
  4. Ensures a user_permissions row exists for the employee.

Safety:
  - Runs in ONE transaction (all-or-nothing).
  - Idempotent: safe to run multiple times.
  - Dry-run by default; pass --apply to actually write.

Usage:
  python patch_link_employees.py                 # dry-run, patches id 39
  python patch_link_employees.py --emp-id 39     # dry-run, specific id
  python patch_link_employees.py --emp-id 2 --emp-id 3   # multiple ids
  python patch_link_employees.py --all           # dry-run, every unlinked emp
  python patch_link_employees.py --all --apply   # COMMIT everything
"""
import argparse
from datetime import date
from db_helper import get_db

DEFAULT_PASSWORD = 'conlink123'


def normalize_email(v):
    return (v or '').strip()


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--apply', action='store_true',
                   help='Actually write changes. Without it, runs in dry-run mode.')
    p.add_argument('--emp-id', type=int, action='append', metavar='ID',
                   help='Only patch this employee id (repeatable).')
    p.add_argument('--all', action='store_true',
                   help='Patch every employee with a missing/invalid user_id link.')
    args = p.parse_args()

    emp_ids = args.emp_id or []
    if not args.all and not emp_ids:
        emp_ids = [39]  # default: the originally reported broken employee

    with get_db() as (cur, conn):
        if args.all:
            cur.execute("""
                SELECT id, first_name, last_name, email, whatsapp, user_id, role
                FROM hr_employees
                WHERE user_id IS NULL
                   OR NOT EXISTS (SELECT 1 FROM connectlinkusers c WHERE c.id = hr_employees.user_id)
                ORDER BY id
            """)
        elif emp_ids:
            placeholders = ','.join(['%s'] * len(emp_ids))
            cur.execute(f"""
                SELECT id, first_name, last_name, email, whatsapp, user_id, role
                FROM hr_employees
                WHERE id IN ({placeholders})
                  AND (user_id IS NULL
                       OR NOT EXISTS (SELECT 1 FROM connectlinkusers c WHERE c.id = hr_employees.user_id))
                ORDER BY id
            """, emp_ids)

        rows = cur.fetchall()
        mode = 'DRY-RUN' if not args.apply else 'APPLY'
        print(f"[{mode}] Found {len(rows)} employee(s) to fix")

        created_cl = created_au = 0
        for (emp_id, first, last, email, whatsapp, user_id, role) in rows:
            full_name = f"{(first or '').strip()} {(last or '').strip()}".strip()
            email = normalize_email(email)
            username = email if email else (whatsapp or f"emp{emp_id}")

            # ---- 1. connectlinkusers row (find or create) ----
            cur.execute("SELECT id FROM connectlinkusers WHERE email = %s ORDER BY id LIMIT 1", (email,))
            clu = cur.fetchone()
            if clu:
                clu_id = clu[0]
                created_here = ''
            else:
                clu_id = None
                created_here = '(create connectlinkusers)'
                if args.apply:
                    cur.execute("""
                        INSERT INTO connectlinkusers (datecreated, name, email, password, whatsapp)
                        VALUES (%s, %s, %s, %s, %s) RETURNING id
                    """, (date.today(), full_name, email, DEFAULT_PASSWORD, whatsapp))
                    clu_id = cur.fetchone()[0]
                created_cl += 1

            # ---- 2. link the employee ----
            if args.apply and clu_id is not None:
                cur.execute("UPDATE hr_employees SET user_id = %s WHERE id = %s", (clu_id, emp_id))

            # ---- 3. admin_users row (find or create), linked via source_id ----
            cur.execute("""
                SELECT id, source_system, source_id FROM admin_users
                WHERE email = %s OR username = %s ORDER BY id LIMIT 1
            """, (email, username))
            au = cur.fetchone()
            if au:
                au_id, au_sys, au_sid = au
                if args.apply and clu_id is not None and (au_sid is None or au_sid != clu_id):
                    cur.execute("""
                        UPDATE admin_users SET source_system = 'projects', source_id = %s
                        WHERE id = %s
                    """, (clu_id, au_id))
            else:
                if args.apply and clu_id is not None:
                    cur.execute("""
                        INSERT INTO admin_users (username, password, full_name, email, source_system, source_id, role, must_reset_password, created_at, subsidiary)
                        VALUES (%s, %s, %s, %s, 'projects', %s, 'operator', TRUE, NOW(), '')
                        RETURNING id
                    """, (username, DEFAULT_PASSWORD, full_name, email, clu_id))
                created_au += 1

            # ---- 4. user_permissions row ----
            is_admin = (role == 'Administrator')
            if args.apply and clu_id is not None:
                cur.execute("""
                    INSERT INTO user_permissions (user_type, user_id, can_manage_hr, hr_access, is_super_admin)
                    VALUES ('projects', %s, %s, TRUE, FALSE)
                    ON CONFLICT (user_type, user_id) DO UPDATE SET
                        can_manage_hr = EXCLUDED.can_manage_hr,
                        hr_access = EXCLUDED.hr_access
                """, (clu_id, is_admin))

            print(f"  - emp {emp_id}: {full_name} ({email or '(no email)'}) -> connectlinkusers id={clu_id} {created_here}")

        if args.apply:
            conn.commit()
            print(f"\n✅ Committed: {len(rows)} linked, {created_cl} connectlinkusers created, {created_au} admin_users created.")
        else:
            print("\nℹ️  DRY-RUN — no changes written. Re-run with --apply to commit.")


if __name__ == '__main__':
    main()
