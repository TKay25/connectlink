"""Repair mojibake already stored in the WhatsApp chat history.

The bot used to SEND the corrupted text (a waving hand arrived as four cp1252
characters), so the copies in `whatsapp_messages` are corrupted too, and the
admin chat panel reads them back verbatim. The source is fixed; this cleans up
what was already written.

Idempotent and dry-run by default: it prints what it would change and writes
nothing until you pass --apply.

    python _repair_whatsapp_mojibake.py                # show what would change
    python _repair_whatsapp_mojibake.py --apply        # write the repair

Run it where DATABASE_URL can reach the database (Render shell, or a machine
allowed through the database's access rules).
"""
import argparse
import os
import re
import sys

# A Windows console is cp1252: printing an emoji would raise instead of showing
# the row it is describing. Degrade to '?' like the app does.
try:
    sys.stdout.reconfigure(errors='replace')
    sys.stderr.reconfigure(errors='replace')
except Exception:                                                         # noqa: BLE001
    pass

LEADERS = 'ðâÃïÂŸ'
RUN = re.compile(r'[^\x00-\x7f]{1,}')

# Only the chat text: it is the column the panel shows and the one the bot wrote.
TARGETS = [
    ('whatsapp_messages', 'message_text', 'id'),
    ('whatsapp_messages', 'sender_name', 'id'),
    ('activity_log', 'description', 'id'),
]


def repair_text(text):
    """Return (fixed_text, changed) for one string; never raises on odd bytes."""
    if not text or not any(ch in LEADERS for ch in text):
        return text, False

    def fix_run(m):
        chunk = m.group(0)
        fixed = None
        for enc in ('cp1252', 'latin-1'):
            try:
                fixed = chunk.encode(enc).decode('utf-8')
            except (UnicodeEncodeError, UnicodeDecodeError):
                continue
            break
        if fixed is None:
            # Some fragments lost a byte to a substituted 0xA0; rebuild byte by byte.
            raw = b''
            for ch in chunk:
                try:
                    raw += ch.encode('cp1252')
                except UnicodeEncodeError:
                    if ord(ch) <= 0xFF:
                        raw += bytes([ord(ch)])
                    else:
                        return chunk      # cannot be reconstructed: leave it
            try:
                fixed = raw.decode('utf-8')
            except UnicodeDecodeError:
                return chunk
        # EF B8 8F is a variation selector (U+FE0F). When its last byte had been
        # replaced by 0xA0 the sequence decodes to a combining half mark instead,
        # so put the selector back and let "⚠"/"ℹ" render as emoji.
        for wrong in ('\ufe20', '\ufe21', '\uf8e0', '\uf8e1'):
            fixed = fixed.replace(wrong, '\ufe0f')
        return fixed

    fixed = RUN.sub(fix_run, text)
    return fixed, fixed != text


def connect():
    url = os.getenv('DATABASE_URL')
    if not url:
        sys.exit('DATABASE_URL is not set. Point it at the database you want to repair.')
    try:
        import psycopg2
    except ImportError:
        sys.exit('psycopg2 is not installed: pip install psycopg2-binary')
    try:
        return psycopg2.connect(url, connect_timeout=30)
    except Exception as exc:                                              # noqa: BLE001
        sys.exit(f'Could not connect: {exc}')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true',
                        help='write the repair (default is a dry run)')
    parser.add_argument('--limit', type=int, default=5000,
                        help='rows to scan per table (default 5000)')
    args = parser.parse_args(argv)

    conn = connect()
    conn.autocommit = False
    total_found = 0
    total_fixed = 0
    try:
        with conn.cursor() as cur:
            for table, column, key in TARGETS:
                cur.execute(
                    f"SELECT {key}, {column} FROM {table} "
                    f"WHERE {column} ~ '[\\u00c3\\u00e2\\u00f0\\u00ef]' "
                    f"ORDER BY {key} DESC LIMIT %s",
                    (args.limit,))
                rows = cur.fetchall()
                if not rows:
                    print(f'{table}.{column}: nothing to repair')
                    continue
                fixed_rows = []
                for row_id, value in rows:
                    try:
                        fixed, changed = repair_text(value)
                    except Exception as exc:                             # noqa: BLE001
                        print(f'  ! {table}.{column} {row_id}: {exc}')
                        continue
                    if changed:
                        fixed_rows.append((row_id, value, fixed))
                total_found += len(rows)
                total_fixed += len(fixed_rows)
                print(f'{table}.{column}: {len(rows)} suspicious row(s), '
                      f'{len(fixed_rows)} repairable')
                for row_id, before, after in fixed_rows[:10]:
                    print(f'  {row_id}: {before[:90]!r}')
                    print(f'      -> {after[:90]!r}')
                if args.apply and fixed_rows:
                    for row_id, _before, after in fixed_rows:
                        cur.execute(f'UPDATE {table} SET {column} = %s WHERE {key} = %s',
                                    (after, row_id))
                    print(f'  wrote {len(fixed_rows)} row(s)')
        if args.apply:
            conn.commit()
            print(f'\nCommitted. {total_fixed} row(s) repaired.')
        else:
            conn.rollback()
            print(f'\nDry run: {total_fixed} row(s) WOULD be repaired. '
                  f'Re-run with --apply to write them.')
    finally:
        conn.close()


if __name__ == '__main__':
    main()
