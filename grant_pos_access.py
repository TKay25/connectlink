r"""Give one POS (Hardware) user the same portal rights as another POS user.

Requested: give leonyaruwanga@connectlinkproperties.co.zw everything the
MrsGAdmin POS user has, so the Inventory and Analytics tabs appear.

WHY THIS IS NEEDED
------------------
The POS sidebar is gated in templates/pos-system.html by
`applyRoleBasedAccess(userRole)`, which reads the value that POS login put in the
session (`/api/login` -> `session['role'] = admin_users.role`). The rule is:

    role == 'operator'  -> only "POS Terminal" + "Transactions"
    any other role      -> all five (POS Terminal, Inventory, Sales Report,
                                      Transactions, Analytics)

So the ONE thing that decides whether the Inventory and Analytics tabs show is
`admin_users.role`. MrsGAdmin is the seeded full-access POS user
(`hardware_users` 'mrsgadmin' ... role 'admin'), which is why she sees them.

WARNING: this is not a read-only grant. A non-operator POS user can also WRITE
(create/edit products, add/subtract stock, remove all stock, void/revert
transactions). There is no view-only POS role in this codebase.

USAGE
-----
    # dry run first - prints a plan and changes NOTHING
    .\.venv\Scripts\python.exe grant_pos_access.py

    # apply it
    .\.venv\Scripts\python.exe grant_pos_access.py --apply

Optional overrides:
    --target   <hint>   username / email / name fragment of the user to change
    --reference<hint>   fragment identifying the user to copy rights FROM
    --role     <role>   force a specific role instead of copying the reference's

Safe to re-run: it only writes what actually differs, and reports a before/after.
"""

import argparse
import sys

from db_helper import get_db

DEFAULT_TARGET = "leonyaruwanga"
DEFAULT_REFERENCE = "gadmin"

ADMIN_COLS = "id, username, full_name, email, source_system, source_id, role, is_active"


def _rows(cursor):
    return cursor.fetchall()


def find_admin_users(cursor, hint):
    """All admin_users rows whose username/email/full_name contains the hint."""
    like = f"%{hint.lower()}%"
    cursor.execute(
        f"""SELECT {ADMIN_COLS} FROM admin_users
            WHERE lower(username) LIKE %s OR lower(email) LIKE %s OR lower(full_name) LIKE %s
            ORDER BY id""",
        (like, like, like),
    )
    return _rows(cursor)


def find_hardware_users(cursor, hint):
    like = f"%{hint.lower()}%"
    cursor.execute(
        """SELECT id, username, full_name, role FROM hardware_users
           WHERE lower(username) LIKE %s OR lower(full_name) LIKE %s
           ORDER BY id""",
        (like, like),
    )
    return _rows(cursor)


def find_permissions(cursor, user_type, user_id):
    cursor.execute(
        """SELECT id, user_type, user_id, is_super_admin, can_manage_hardware
           FROM user_permissions WHERE user_type = %s AND user_id = %s""",
        (user_type, user_id),
    )
    return _rows(cursor)


def show(label, rows, cols):
    print(f"\n{label}")
    if not rows:
        print("   (none)")
        return
    for r in rows:
        print("   " + " | ".join(f"{c}={r[i]}" for i, c in enumerate(cols)))


def main():
    ap = argparse.ArgumentParser(description="Copy POS portal rights between users.")
    ap.add_argument("--target", default=DEFAULT_TARGET,
                    help="username/email/name fragment of the user to change")
    ap.add_argument("--reference", default=DEFAULT_REFERENCE,
                    help="fragment identifying the user to copy rights from")
    ap.add_argument("--role", default=None,
                    help="force this role instead of copying the reference's")
    ap.add_argument("--apply", action="store_true", help="actually write the change")
    args = ap.parse_args()

    admin_cols = ["id", "username", "full_name", "email", "source_system", "source_id", "role", "is_active"]

    with get_db() as (cursor, connection):
        targets = find_admin_users(cursor, args.target)
        references = find_admin_users(cursor, args.reference)
        hw_targets = find_hardware_users(cursor, args.target)
        hw_references = find_hardware_users(cursor, args.reference)

        print("=" * 78)
        print("POS ACCESS PARITY")
        print("=" * 78)
        show(f"TARGET admin_users (hint {args.target!r})", targets, admin_cols)
        show(f"REFERENCE admin_users (hint {args.reference!r})", references, admin_cols)
        show("TARGET hardware_users (legacy)", hw_targets, ["id", "username", "full_name", "role"])
        show("REFERENCE hardware_users (legacy)", hw_references, ["id", "username", "full_name", "role"])

        if len(targets) != 1:
            print(f"\n!! Expected exactly ONE target admin_users row, found {len(targets)}.")
            print("   Re-run with a more specific --target (e.g. the full email).")
            return 2
        if len(references) != 1:
            print(f"\n!! Expected exactly ONE reference admin_users row, found {len(references)}.")
            print("   Re-run with a more specific --reference.")
            return 2

        target = targets[0]
        reference = references[0]
        t_id, t_username = target[0], target[1]
        t_source_system, t_source_id = target[4], target[5]
        t_role = target[6]
        r_role = reference[6]

        desired_role = args.role or r_role
        target_perm_ids = [t_source_id, t_id]

        print("\n" + "-" * 78)
        print(f"Role: {t_username!r} has {t_role!r} -> must become {desired_role!r}")
        if str(desired_role).lower() == "operator":
            print("   !! NOTE: 'operator' shows ONLY POS Terminal + Transactions.")
            print("      The reference itself would not see Inventory/Analytics.")
        elif desired_role != t_role:
            print("   -> this is what reveals Inventory + Analytics (+ Sales Report).")
        else:
            print("   -> role already correct; nothing to change here.")

        perm_rows = find_permissions(cursor, "hardware", t_source_id) if t_source_id else []
        perm_ok = any(r[4] for r in perm_rows)
        show(f"TARGET user_permissions (hardware, user_id={t_source_id})",
             perm_rows, ["id", "user_type", "user_id", "is_super_admin", "can_manage_hardware"])
        if perm_ok:
            print("   -> already has can_manage_hardware (can log into POS).")
        else:
            print("   !! no can_manage_hardware row found for the hardware user_type.")
            print("      If she cannot log into POS at all, this must be granted too.")

        hw_target = hw_targets[0] if len(hw_targets) == 1 else None
        hw_reference = hw_references[0] if len(hw_references) == 1 else None
        hw_desired = hw_reference[3] if hw_reference else None
        hw_role_old = hw_target[3] if hw_target else None
        hw_needed = bool(hw_target and hw_desired and hw_role_old != hw_desired)
        if hw_needed:
            print(f"\nLegacy hardware_users.role: {hw_role_old!r} -> {hw_desired!r}")
        elif hw_target:
            print("\nLegacy hardware_users.role: already matches / nothing to do.")

        if not args.apply:
            print("\n" + "=" * 78)
            print("DRY RUN - nothing was written. Re-run with --apply to make it so.")
            print("=" * 78)
            return 0

        print("\n" + "=" * 78)
        print("APPLYING")
        print("=" * 78)
        changed = 0

        if desired_role != t_role:
            cursor.execute(
                "UPDATE admin_users SET role = %s, updated_at = NOW() WHERE id = %s",
                (desired_role, t_id),
            )
            print(f"[ok] admin_users.role: {t_role!r} -> {desired_role!r}  (id={t_id})")
            changed += 1
        else:
            print("[--] admin_users.role already correct")

        if hw_needed:
            cursor.execute("UPDATE hardware_users SET role = %s WHERE id = %s",
                           (hw_desired, hw_target[0]))
            print(f"[ok] hardware_users.role: {hw_role_old!r} -> {hw_desired!r}  (id={hw_target[0]})")
            changed += 1

        connection.commit()

        # verify
        print("\nVERIFY")
        after = find_admin_users(cursor, args.target)
        show("TARGET admin_users after", after, admin_cols)

        print(f"\nDone. {changed} row(s) updated.")
        print("The user must LOG INTO POS AGAIN for the new role to take effect")
        print("(the role is captured in the session at login and cached in the browser).")
        return 0


if __name__ == "__main__":
    sys.exit(main())
