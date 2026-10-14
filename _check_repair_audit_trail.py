"""Check: the phantom-stock repair reaches BOTH audit surfaces.

The repair writes an activity_log row, but the row alone is not enough to be
seen: the POS Activity Log asks for a whitelist of action types, and the Stock
Audit Report is built from movement tables (which a deletion has no rows in).
This asserts each surface now carries the repair.

    python _check_repair_audit_trail.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TPL = os.path.join(ROOT, 'templates', 'pos-system.html')
APP = os.path.join(ROOT, 'ConnectLink.py')

lines = []


def say(ok, msg):
    lines.append(('PASS  ' if ok else 'FAIL  ') + str(msg))
    return ok


html = open(TPL, encoding='utf-8').read()
app = open(APP, encoding='utf-8').read()

# ---------- 0. the page's JavaScript must still parse ----------
try:
    import esprima
    blocks = re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', html, re.S | re.I)
    for i, js in enumerate(blocks, 1):
        if '{{' in js or '{%' in js:
            continue
        try:
            esprima.parseScript(js)
        except Exception as exc:                            # noqa: BLE001
            say(False, 'pos-system.html block %d SYNTAX ERROR line %s: %s'
                % (i, getattr(exc, 'lineNumber', None), exc))
            break
    else:
        say(True, 'every inline script block parses')
except Exception as exc:                                    # noqa: BLE001
    say(False, 'esprima unavailable: %s' % exc)

# ---------- 1. the repair writes a named, detailed activity entry ----------
say("log_activity('branch_stock_repair'" in app,
    'the repair logs an activity entry')
say("'items': items" in app, 'the activity entry names the affected items')
say('preview' in app, 'the activity description names the items, not just a count')

# ---------- 2. the POS Activity Log shows it ----------
m = re.search(r'const POS_ACTIVITY_TYPES = \[(.*?)\];', html, re.S)
say(m is not None, 'the POS activity-type whitelist was found')
if m:
    say("'branch_stock_repair'" in m.group(1),
        'branch_stock_repair is in the POS Activity Log whitelist')
say("'branch_stock_repair': 'warning'" in html,
    'the activity badge has a colour for it')
say("'branch_stock_repair': 'Stock Repair'" in html,
    'the PDF export has a readable label for it')

# ---------- 3. the Stock Audit Report shows it ----------
say("'repairs': repair_list" in app, 'the stock-movements API returns repairs')
say("action_type = 'branch_stock_repair'" in app,
    'the API reads repairs from the activity log')
say('id="auditRepairsContainer"' in html, 'the audit report has a repairs panel')
say('id="auditRepairsBody"' in html, 'the repairs panel has a body')
say('function renderAuditRepairs(' in html, 'a renderer exists')
say('renderAuditRepairs(auditRepairData)' in html, 'the renderer is called on load')
say('let auditRepairData = [];' in html, 'the repairs payload is stored')
say('auditRepairData = data.repairs || [];' in html, 'the repairs payload is captured')
say("auditRepairData.length" in html, 'the empty-state accounts for repairs')

# The repair panel must be reset when a new report is generated, or a stale
# panel stays on screen.
say("getElementById('auditRepairsContainer').style.display = 'none'"
    in html, 'the repairs panel is reset before each load')

# ---------- 4. the already-repaired history (from the backup table) ----------
say("@app.route('/api/branch-health/phantom-stock/removed', methods=['GET'])" in app,
    'the removed-history endpoint exists')
say('FROM product_stock_repair_backup' in app,
    'the endpoint reads the backup taken before each deletion')
say("session.get('role') != 'admin'" in app, 'the history endpoint is admin-gated')

# The backup table has NO id column, so the query must not select one.
try:
    seg = app[app.index("def phantom_stock_removed("):]
    seg = seg[:seg.index('\n@app.route', 10)]
    say('rb.id' not in seg,
        'the history query does not select a non-existent rb.id column')
    say('rb.product_id' in seg and 'rb.removed_at' in seg,
        'the history query selects columns the backup actually has')
except ValueError:
    say(False, 'phantom_stock_removed() not found')

say('id="phantomRemovedTable"' in html, 'the modal has a repaired-history table')
say('function loadPhantomRemovedHistory(' in html, 'a history loader exists')
say('/api/branch-health/phantom-stock/removed' in html,
    'the loader calls the history endpoint')
say('loadPhantomRemovedHistory();' in html,
    'the history refreshes after a repair runs')

print('\n'.join(lines))
failures = [l for l in lines if l.startswith('FAIL')]
print('')
print('FAILURES: %d' % len(failures))
sys.exit(1 if failures else 0)
