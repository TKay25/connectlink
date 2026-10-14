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

print('\n'.join(lines))
failures = [l for l in lines if l.startswith('FAIL')]
print('')
print('FAILURES: %d' % len(failures))
sys.exit(1 if failures else 0)
