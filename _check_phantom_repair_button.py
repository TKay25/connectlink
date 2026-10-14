"""Syntax + wiring check for the Inventory-page Phantom Stock Repair button.

Parses every inline JavaScript block of templates/pos-system.html with esprima
(the project's checker dependency) and asserts the button, modal and handlers are
wired to each other and to the app's repair API.

    python _check_phantom_repair_button.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(ROOT, 'templates', 'pos-system.html')

lines = []


def say(ok, msg):
    lines.append(('PASS  ' if ok else 'FAIL  ') + str(msg))
    return ok


html = open(TEMPLATE, encoding='utf-8').read()
blocks = [b for b in re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', html, re.S | re.I)]
js_all = '\n'.join(blocks)

say(len(blocks) > 0, '%d inline script block(s) found' % len(blocks))

# ---------- 1. the page's own JavaScript must still parse ----------
try:
    import esprima
    for i, js in enumerate(blocks, 1):
        if '{{' in js or '{%' in js:
            say(True, 'block %d skipped (Jinja template syntax)' % i)
            continue
        try:
            esprima.parseScript(js)
        except Exception as exc:                            # noqa: BLE001
            say(False, 'block %d SYNTAX ERROR at line %s: %s'
                % (i, getattr(exc, 'lineNumber', None), exc))
            break
    else:
        say(True, 'every inline script block parses')
except Exception as exc:                                    # noqa: BLE001
    say(False, 'esprima unavailable: %s' % exc)

# ---------- 2. the button sits on the Inventory tab ----------
inv_start = html.find('id="inventoryPage"')
inv_end = html.find('Inventory Summary Cards', inv_start)
inv_block = html[inv_start:inv_end] if inv_start != -1 and inv_end != -1 else ''
say(inv_start != -1, 'the Inventory page exists')
say('openPhantomStockRepairModal()' in inv_block,
    'the Repair Phantom Stock button is on the Inventory tab')
say('Repair Phantom Stock' in inv_block, 'the button is labelled')

# ---------- 3. the modal exists with its parts ----------
for needle, label in [
    ('id="phantomStockRepairModal"', 'the repair modal exists'),
    ('id="phantomRepairTable"', 'the modal has a results table'),
    ('id="phantomRepairBranch"', 'the modal names the branch it checked'),
    ('id="phantomRepairConfirm"', 'the modal has a confirm box'),
    ('id="phantomRepairApplyBtn"', 'the modal has an apply button'),
    ('onclick="applyPhantomStockRepair()"', 'the apply button runs the repair'),
    ('onclick="loadPhantomStockReport()"', 'the modal can re-check'),
]:
    say(needle in html, label)

# ---------- 4. the behaviour is wired ----------
for fn in ['openPhantomStockRepairModal', 'loadPhantomStockReport',
           'applyPhantomStockRepair', 'phantomEscapeHtml']:
    say(re.search(r'\bfunction\s+' + fn + r'\s*\(', js_all) is not None,
        'function %s() is defined' % fn)

say('/api/branch-health/phantom-stock`' in js_all or
    "/api/branch-health/phantom-stock'" in js_all or
    '/api/branch-health/phantom-stock"' in js_all,
    'the report API is called')
say('/api/branch-health/phantom-stock/repair' in js_all, 'the repair API is called')

# The repair must be gated on typing "remove" before it is sent.
apply_fn = js_all[js_all.index('async function applyPhantomStockRepair'):]
apply_fn = apply_fn[:apply_fn.index('// ==================== REMOVE ALL STOCK')]
say("!== 'remove'" in apply_fn, 'the repair refuses without the typed confirmation')
say('confirm: \'remove\'' in apply_fn or 'confirm: "remove"' in apply_fn,
    'the repair sends the confirmation the API expects')

# The grid has to be refreshed, or the operator keeps looking at stale rows.
say('fetchProductsFromAPI' in apply_fn, 'the repair reloads the product grid')

print('\n'.join(lines))
failures = [l for l in lines if l.startswith('FAIL')]
print('')
print('FAILURES: %d' % len(failures))
sys.exit(1 if failures else 0)
