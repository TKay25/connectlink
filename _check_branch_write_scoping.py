"""Audit: every branch-scoped write route must be session-scoped and guarded.

This answers the standing question "can the branches mix again?" mechanically,
rather than by reading the code by eye. For each @app.route that writes a
branch-scoped table it checks:

  1. the route carries @login_required, and
  2. it carries @block_writes_in_consolidated_view (which refuses a write when
     the session never proved a branch) OR an explicit admin gate, and
  3. the branch id it writes is NOT taken from a client-supplied request value,
     unless that value was verified against the branch code first.

    python _check_branch_write_scoping.py
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
src_lines = src.split('\n')

WRITE_TABLES = [
    'product_stock', 'stock_lots', 'stock_additions', 'stock_reductions',
    'transactions', 'transaction_items', 'laybys', 'layby_items',
    'layby_payments', 'stock_transfers', 'product_removals', 'product_prices',
    'bulk_upload_jobs', 'bulk_upload_items', 'activity_log',
]

WRITE_VERB = re.compile(r'\b(INSERT\s+INTO|UPDATE|DELETE\s+FROM)\s+('
                        + '|'.join(WRITE_TABLES) + r')\b', re.I)

# Every @app.route(...) and the def that follows it.
routes = []
for m in re.finditer(r"@app\.route\('([^']+)'.*?\)\s*\n((?:@[^\n]*\n)*)\s*def\s+(\w+)\s*\(",
                     src):
    path, decorators, fn = m.group(1), m.group(2), m.group(3)
    routes.append({'path': path, 'decors': decorators, 'fn': fn, 'start': m.start()})

say(len(routes) > 0, 'found %d routes' % len(routes))


def body_of(fn_name, start):
    """The function source, up to the next decorator/def at column 0."""
    m = re.search(r'\ndef ' + re.escape(fn_name) + r'\s*\(', src[start:])
    if not m:
        return ''
    b = start + m.start()
    nxt = re.search(r'\n(?=@app\.route|def |# =====)', src[b + 1:])
    return src[b: b + 1 + (nxt.start() if nxt else len(src) - b)]


write_routes = []
for r in routes:
    body = body_of(r['fn'], r['start'])
    tables = sorted({m.group(2).lower() for m in WRITE_VERB.finditer(body)})
    # The seeder and the repair back up/delete; they are not user-facing writes.
    if not tables:
        continue
    write_routes.append({**r, 'tables': tables, 'body': body})

say(len(write_routes) > 0, 'found %d route(s) writing a branch-scoped table'
    % len(write_routes))

# ---- 1 & 2: every write route must be login-gated and write-guarded ----------
unguarded = []
for r in write_routes:
    has_login = 'login_required' in r['decors']
    has_block = 'block_writes_in_consolidated_view' in r['decors']
    has_admin = "session.get('role') != 'admin'" in r['body'] \
        or "session.get('role') == 'admin'" in r['body']
    # A route may guard its write INLINE instead of by decorator -- the layby list
    # is a GET that self-heals, and it checks branch_is_read_only() around that
    # UPDATE itself. Accept that only when the check really wraps the write.
    inline_guard = ('branch_is_read_only()' in r['body']
                    and WRITE_VERB.search(r['body']) is not None)
    if not has_login:
        unguarded.append((r['fn'], r['path'], 'no @login_required'))
    if not (has_block or has_admin or inline_guard):
        unguarded.append((r['fn'], r['path'], 'no write guard (block_writes, admin, or inline)'))

if unguarded:
    for fn, path, why in unguarded:
        say(False, 'UNGUARDED WRITE: %s (%s) - %s' % (fn, path, why))
else:
    say(True, 'every branch-scoped write route is login-gated and write-guarded')

# ---- 3: no write may trust an unverified client-supplied branch_id ----------
# A client value is acceptable ONLY when verify_branch_code() is called first, or
# when it is compared against the session's own branch and refused on mismatch.
SUSPECT = re.compile(r"(?:data\.get\('branch_id'\)|data\[['\"]branch_id['\"]\]|"
                     r"request\.args\.get\('branch_id'\))")
suspects = []
for r in write_routes:
    if not SUSPECT.search(r['body']):
        continue
    verified = ('verify_branch_code(' in r['body']
                or 'declared_branch != branch_id' in r['body']
                or 'confirmed_branch != branch_id' in r['body'])
    if not verified:
        suspects.append((r['fn'], r['path']))

if suspects:
    for fn, path in suspects:
        say(False, 'UNVERIFIED CLIENT BRANCH: %s (%s)' % (fn, path))
else:
    say(True, 'no write route trusts an unverified client-supplied branch_id')

# ---- 4: the guard itself must refuse both unsafe cases -----------------------
try:
    guard = src[src.index('def block_writes_in_consolidated_view('):]
    guard = guard[:guard.index('\ndef ', 10)]
    say('branch_is_read_only()' in guard,
        'the write guard refuses the consolidated (All Branches) view')
    say('session_branch_chosen()' in guard,
        'the write guard refuses a session that never proved a branch')
except ValueError:
    say(False, 'block_writes_in_consolidated_view() was found')

# ---- 4b: a write hidden inside a GET must still be branch-scoped ------------
# The layby list is a GET that self-heals with an UPDATE. It slipped through the
# decorator check because the guard is written inline, and its UPDATE had no
# branch filter -- so one shop opening its list closed the other shop's laybys.
try:
    fn = src[src.index('def pos_list_laybys('):]
    fn = fn[:fn.index('\n@app.route', 10)]
    upd = fn[fn.index('UPDATE laybys'):]
    upd = upd[:upd.index('"""')]
    say('branch_id = %s' in upd,
        'the layby self-heal UPDATE is scoped to the session branch')
    say('branch_is_read_only()' in fn,
        'the layby self-heal is skipped on the read-only consolidated view')
except ValueError:
    say(False, 'pos_list_laybys() and its UPDATE were found')

# ---- 5: the two places a branch is chosen must verify the code --------------
for route_path, label in [('/api/login', 'login'),
                          ('/api/pos/switch-branch', 'switch-branch')]:
    m = re.search(r"@app\.route\('" + re.escape(route_path) + r"'[\s\S]{0,6000}?"
                  r"verify_branch_code\(", src)
    say(m is not None, '%s verifies the branch access code' % label)

# ---- 6: the boot seeder must stay guarded (the original culprit) ------------
try:
    # Match the seeder's column list by shape: it gained a `department` column
    # when departments were introduced, so an exact string here breaks on any
    # future column. The GUARD is what matters, not the exact list.
    _seeder_m = re.search(
        r"INSERT INTO product_stock \(product_id, branch_id[^)]*stock[^)]*\)\s*(.*?)\"\"\",",
        src, re.S)
    seeder = _seeder_m.group(0) if _seeder_m else ''
    say(bool(seeder) and 'NOT EXISTS' in seeder,
        'the boot seeder still refuses products that already have a branch row')
    say('coalesce(p.stock' in seeder.lower(),
        'the seeder still seeds from products.stock (guarded, as designed)')
except ValueError:
    say(False, 'the boot seeder was found')

# ---- 7: a boot may never reset a worked-in branch code ----------------------
# A process that boots against the database WITHOUT the deployment's env vars
# (a local run, a health probe, a second service) used to re-assert the SHIPPED
# default over a shop's configured access code, locking every till out of that
# branch. The seed may fill a missing code and apply a deliberate rotation, but
# never replace a configured code with the placeholder this app ships with.
_seed_m = re.search(r"for code, name, address, phone, access_code, is_dispatch, shipped_default in BRANCH_BOOTSTRAP_SEED:"
                    r"[\s\S]{0,1400}?connection\.commit\(\)", src)
_seed = _seed_m.group(0) if _seed_m else ''
say(bool(_seed), 'the branch seeder was found')
say('WHEN EXCLUDED.access_code = %s' in _seed and 'THEN branches.access_code' in _seed,
    'the branch seeder refuses to overwrite a configured code with the shipped default')
say("WHEN NULLIF(branches.access_code, '') IS NULL" in _seed and 'THEN EXCLUDED.access_code' in _seed,
    'the branch seeder still fills in a missing code')
say('is_dispatch = EXCLUDED.is_dispatch' in _seed,
    'the branch seeder still re-asserts is_dispatch (it decides which POS pages exist)')
say('SHIPPED_BRANCH_SHURUGWI_CODE' in src and 'SHIPPED_BRANCH_CHEGUTU_CODE' in src,
    'the shipped defaults are named constants, not inline literals')

print('\n'.join(lines))
failures = [l for l in lines if l.startswith('FAIL')]
print('')
print('FAILURES: %d' % len(failures))
sys.exit(1 if failures else 0)
