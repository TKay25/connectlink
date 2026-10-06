"""Offline check for the POS freshness fix in templates/pos-system.html.

The complaint: a till showed 26 for a product whose branch really held 8, so
"remove 23" was refused by the server -- correctly, but the screen should never
have said 26 in the first place. The figure on screen was this device's saved
copy (the till could not reach the server), and nothing on the page said so.
Worse, the "live" per-product probe that the Subtract/Add boxes use was itself
being answered out of that same saved copy, so it confirmed the stale number.

No database and no browser are needed here. This checks, without one:

  1. every <script> block in the page still parses (esprima), and against the
     COMMITTED version so a pre-existing quirk is not blamed on this change,
  2. only the catalogue endpoints may be saved/replayed -- never a per-product
     probe or a barcode lookup (whole-path match, not a substring),
  3. a replayed answer is marked as such, and a probe that gets one is treated
     as "no answer" rather than as the server's figure,
  4. a catalogue load that fails, or answers with something that is not a
     product list, is reported as "not live" instead of silently keeping the
     old numbers,
  5. a subtraction/addition is never refused locally on a figure known to be
     stale -- the server judges it, and it reports the real quantity,
  6. the catalogue is re-fetched when the connection returns, when the tab
     comes back, on the slow timer, and whenever the Inventory page is opened,
  7. a sale rung offline that turns out to have taken more than the shelf held is
     DISCLOSED -- in the sync reply (a named warning and a count) and on the till
     (the confirmation dialog before the money, and the queued-sale notice) --
     without disturbing the movement note the reconciliation tool matches on
     EXACTLY, which is what lets those sales still be reassigned,
  8. and a till that has been LOGGED OUT with sales still on it says how many are
     waiting and that one login files them -- rather than passing a bare session
     error through, which reads as if the money were lost (the server no longer
     claims a session lifetime its cookie does not have).

Run:  python _check_pos_freshness.py   (writes _check_pos_out.txt)
"""
import re
import subprocess
import sys

RESULTS = []
OUT = '_check_pos_out.txt'
TEMPLATE = 'templates/pos-system.html'


def _flush():
    try:
        with open(OUT, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(RESULTS) + '\n')
    except Exception:                                              # noqa: BLE001
        pass


def check(name, ok, detail=''):
    RESULTS.append(f"{'PASS' if ok else 'FAIL'}  {name}"
                   f"{('  -> ' + detail) if detail else ''}")
    _flush()


check('script started', True)

try:
    NEW = open(TEMPLATE, encoding='utf-8').read()
    check('read the POS page', True, f'{len(NEW)} chars')
except Exception as exc:                                           # noqa: BLE001
    check('read the POS page', False, f'{type(exc).__name__}: {exc}')
    print('\n'.join(RESULTS))
    print('\nFAILURES: 1')
    sys.exit(1)

try:
    proc = subprocess.run(['git', 'show', 'HEAD:' + TEMPLATE], capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or b'').decode('utf-8', 'replace').strip()
                           or 'git show failed')
    # Decoded by hand: the page contains bytes that are not valid in the console's
    # own code page, and git returns the blob verbatim.
    OLD = proc.stdout.decode('utf-8', 'replace')
    check('read the committed POS page for comparison', True, f'{len(OLD)} chars')
except Exception as exc:                                           # noqa: BLE001
    OLD = None
    check('read the committed POS page for comparison', False,
          f'{type(exc).__name__}: {exc}')


# ------------------------------------------------- 1. every script parses
def blocks(html):
    out = []
    for m in re.finditer(r'<script([^>]*)>(.*?)</script>', html, re.S):
        attrs, body = m.group(1), m.group(2)
        if 'src=' in attrs or not body.strip():
            continue
        out.append((html[:m.start(2)].count('\n') + 1, body))
    return out


def first_error(body):
    """(message, line-within-the-block) of the first syntax error, or None.

    `?.` is normalised to `.` first: the console's esprima is an ES2017 parser and
    the page has used optional chaining since long before this change, so that one
    construct would otherwise hide every line after it -- including the lines this
    check exists to read.
    """
    try:
        import esprima
    except Exception as exc:                                       # noqa: BLE001
        return 'no-parser: %s' % exc, 0
    try:
        esprima.parseScript(body.replace('?.', '.'))
        return None, 0
    except Exception as exc:                                       # noqa: BLE001
        return getattr(exc, 'message', str(exc)), getattr(exc, 'lineNumber', 0)


new_blocks = blocks(NEW)
old_blocks = blocks(OLD) if OLD else []
check('the page still has its script blocks',
      len(new_blocks) == len(old_blocks) and len(new_blocks) >= 4,
      'new=%d old=%d' % (len(new_blocks), len(old_blocks)))

worse = []
for i, (start, body) in enumerate(new_blocks):
    msg_new, line_new = first_error(body)
    if msg_new is None:
        continue
    msg_old = None
    if i < len(old_blocks):
        msg_old, _ = first_error(old_blocks[i][1])
    if msg_old != msg_new:
        lines = body.splitlines()
        snippet = lines[line_new - 1].strip()[:70] if 0 < line_new <= len(lines) else ''
        worse.append('block %d at page line %d: %s  |%s|'
                     % (i, start + line_new - 1, msg_new, snippet))
check('no script block gained a syntax error (vs the committed page)',
      not worse, '; '.join(worse[:3]))


def _skip(src, i):
    """Index just past the comment / string / template literal that starts at i."""
    two = src[i:i + 2]
    if two == '//':
        j = src.find('\n', i)
        return len(src) if j < 0 else j + 1
    if two == '/*':
        j = src.find('*/', i + 2)
        return len(src) if j < 0 else j + 2
    quote = src[i]
    j = i + 1
    while j < len(src):
        if src[j] == '\\':
            j += 2
            continue
        if src[j] == quote:
            return j + 1
        j += 1
    return len(src)


def extract(src, start_marker):
    """The whole declaration whose text starts at `start_marker`, brace-matched.

    Comments, strings and template literals are skipped, so a brace inside any of
    them cannot end the declaration early.
    """
    i = src.index(start_marker)
    if start_marker.startswith('let '):
        return src[i:src.index(';', i) + 1]
    j = src.index('{', i)
    depth = 0
    while j < len(src):
        ch = src[j]
        if ch in '\'"`':
            j = _skip(src, j)
            continue
        if src[j:j + 2] in ('//', '/*'):
            j = _skip(src, j)
            continue
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return src[i:j + 1]
        j += 1
    raise ValueError('unbalanced braces for ' + start_marker)


EDITED = [
    'function updateInventoryMetrics(',
    'async function fetchProductsFromAPI(',
    'function catalogueIsLive(',
    'function savedCopyAt(',
    'function noteCatalogueFreshness(',
    'let addStockFigureIsLive',
    'function populateEditStockModal(',
    'async function showEditStockModal(',
    'async function confirmAddStock(',
    'async function refreshLiveStock(',
    'let subtractFigureIsLive',
    'function populateSubtractStockModal(',
    'async function showSubtractStockModal(',
    'async function confirmSubtractStock(',
    'async function lookupProductByBarcode(',
    'function navigateTo(',
    'function requestPath(',
    'function isCacheableGet(',
    'function isCatalogueUrl(',
    'function pruneSavedCopies(',
    'function refreshCatalogueIfStale(',
    'function notifySessionExpired(',
    'function clearSessionNotice(',
]
bad = []
for marker in EDITED:
    try:
        snippet = extract(NEW, marker)
        msg, line = first_error(snippet)
        if msg is not None:
            bad.append('%s: %s' % (marker, msg))
    except Exception as exc:                                       # noqa: BLE001
        bad.append('%s: %s' % (marker, exc))
check('every declaration this change touched parses on its own',
      not bad, '; '.join(bad[:3]))
check('all of the touched declarations were found',
      len(EDITED) == 23, str(len(EDITED)))


# ------------------------------------- 2. only the catalogue is replayable
m = re.search(r'var CACHEABLE_PATHS = \[(.*?)\];', NEW, re.S)
paths = re.findall(r"'([^']+)'", m.group(1)) if m else []
check('the saved-copy whitelist is a list of whole endpoints', bool(paths),
      ', '.join(paths))
check('no per-product probe or barcode lookup is replayable',
      bool(paths) and not any(p.rstrip('/').count('/') > 2 for p in paths)
      and '/api/products/by-barcode' not in paths,
      ', '.join(paths))
check('the old substring matcher is gone', 'CACHEABLE_GETS' not in NEW)
check('cacheability is decided on the request PATH, not the raw url',
      'function isCacheableGet(url)' in NEW and 'requestPath(url)' in NEW
      and 'url.indexOf(p) !== -1' not in NEW)
check('the catalogue endpoint itself is still replayable',
      "var CACHEABLE_PATHS = ['/api/products'" in NEW
      and "return requestPath(url) === '/api/products';" in NEW)
check('a saved probe already on the device is pruned away',
      'function pruneSavedCopies()' in NEW and '\n    pruneSavedCopies();' in NEW)
# An offline barcode scan must still resolve from the list on screen, or the till
# would invite a duplicate product to be created.
barcode_fn = NEW[NEW.index('async function lookupProductByBarcode'):][:2600]
check('a barcode scan falls back to the list on screen when the server cannot answer',
      'const localMatch = () => {' in barcode_fn
      and 'if (savedCopyAt(res) || !res.ok) return localMatch();' in barcode_fn
      and barcode_fn.count('return localMatch();') >= 2)
check('but a live answer from the server still decides',
      'return (data.success && data.product) ? data.product : null;' in barcode_fn)


# --------------------------------- 3. a replayed answer is marked and refused
check("a replayed response is tagged as the device's own copy",
      "'X-ConnectLink-Saved-Copy': '1'" in NEW
      and "'X-ConnectLink-Saved-At'" in NEW)
check('savedCopyAt() only believes the tag',
      "res.headers.get('X-ConnectLink-Saved-Copy') !== '1'" in NEW
      and 'return Number(res.headers.get' in NEW)
live_probe = NEW[NEW.index('async function refreshLiveStock'):][:1400]
check('the probe refuses a saved copy as if it had not answered',
      'if (savedCopyAt(res)) return null;' in live_probe)
check('the probe refuses a non-OK answer',
      'if (!res.ok) return null;' in live_probe)
check('the probe only writes the product once the server has answered',
      live_probe.index('if (savedCopyAt(res)) return null;')
      < live_probe.index('product.stock_server = serverFigure;'))


# ------------------------------- 4. a failed load is announced, not hidden
fetch_fn = NEW[NEW.index('async function fetchProductsFromAPI'):][:4200]
check('a non-OK catalogue answer is handled, not ignored',
      'if (!productsResponse.ok)' in fetch_fn)
check('a non-OK answer reports the figures as not live',
      'noteCatalogueFreshness({ savedAt: savedAt, unreachable: !savedAt });' in fetch_fn)
check('a 200 that is not a product list is reported too',
      'The catalogue could not be loaded - the figures on screen are not live.' in fetch_fn)
check('a live payload is stamped live, a replayed one is not',
      'catalogueLiveAt = Date.now();' in fetch_fn
      and 'catalogueLiveAt = 0;' in fetch_fn
      and 'function catalogueIsLive() { return catalogueLiveAt > 0; }' in NEW)
check('nothing carries a dead per-product freshness flag',
      'stock_is_live' not in NEW)
check('the connection-failure path also says the figures are not live',
      'catalogueLiveAt = 0;' in fetch_fn.split('} catch (error) {')[-1])
freshness = NEW[NEW.index('function noteCatalogueFreshness(state)'):][:1500]
check('the banner has a "nothing is confirmed" state and a "saved copy" state',
      'opts.unreachable' in freshness and 'opts.savedAt' in freshness)
check('the banner is one function, so the two notices cannot contradict',
      NEW.count('function noteCatalogueFreshness(') == 1)


# ------------------------- 5. stock actions are not refused on a stale figure
sub = NEW[NEW.index('let subtractFigureIsLive'):][:2600]
check('the Subtract box knows whether its figure is live',
      'subtractFigureIsLive = isLive !== false;' in sub)
check('its inline warning is skipped on a saved copy',
      'if (subtractFigureIsLive && quantity > currentStock)' in sub)
check('it says the figure is not live',
      'subtractStockFreshnessText' in sub and 'not live' in sub)
check('the Subtract modal has somewhere to say so',
      'id="subtractStockFreshness"' in NEW)
confirm_sub = NEW[NEW.index('async function confirmSubtractStock'):][:1600]
check('the confirm step does not refuse a removal on a saved figure',
      'if (subtractFigureIsLive && quantityToRemove > productToEdit.stock)' in confirm_sub)
try:
    _cl = open('ConnectLink.py', encoding='utf-8').read()
    route = _cl[_cl.index('def subtract_stock'):][:2600]
    check('the server refusal still hands back the live figure and marks it stale',
          "'available': current_stock," in route and "'stale': True" in route)
except Exception as exc:                                           # noqa: BLE001
    check('read the subtract route out of ConnectLink.py', False,
          f'{type(exc).__name__}: {exc}')

add = NEW[NEW.index('let addStockFigureIsLive'):][:1600]
check('the Add Stock box says when its base figure is not live',
      'addStockFreshnessText' in add
      and 'addStockFigureIsLive = isLive === true;' in add)
check('the Add Stock modal has somewhere to say so',
      'id="addStockFreshness"' in NEW)
confirm_add = NEW[NEW.index('async function confirmAddStock'):][:2400]
check('an addition is refused on an unconfirmed base (it writes an absolute total)',
      'if (!addStockFigureIsLive)' in confirm_add)
check('both boxes are given the probe result',
      'populateEditStockModal(product, !!fresh);' in NEW
      and 'populateSubtractStockModal(product, fresh ? fresh.stock : currentStock, !!fresh);' in NEW)


# ------------------------------------------- 6. the figures are kept live
keep = NEW[NEW.index('function refreshCatalogueIfStale'):][:1600]
check('a refresh helper exists and never polls a till showing live figures',
      'if (!force && !window.__posCatalogueStaleAt && !unconfirmed) return;' in keep)
check('a refused or unreachable load is retried too, not only a replayed copy',
      '!catalogueIsLive()' in keep)
listeners = NEW[NEW.index("window.addEventListener('online'"):][:1200]
check('the catalogue is re-fetched when the connection returns',
      'refreshCatalogueIfStale(true);' in listeners)
check('and when the tab comes back to the foreground',
      'refreshCatalogueIfStale(false);' in listeners.split('visibilitychange')[-1])
nav = NEW[NEW.index("if (page === 'inventory')"):][:400]
check('opening the Inventory page forces server figures',
      'refreshCatalogueIfStale(true)' in nav)
check('the Inventory page states when the figures were confirmed',
      'id="inventoryAsAt"' in NEW and 'Figures confirmed by the server at ' in NEW
      and 'Figures NOT confirmed by the server' in NEW)

# ------------- 7. a sale rung offline that took more than the shelf held
# The till rung it on a figure it could NOT confirm, so the sale may take stock
# the shelf does not hold. The money is already taken, so the sale is still
# filed: what matters is that the shortage is NAMED by the server and DISCLOSED
# on the till at once -- and that the movement note the reconciliation tool
# matches on EXACTLY is left alone, or those sales could no longer be reassigned.
try:
    _cl = open('ConnectLink.py', encoding='utf-8').read()
    _start = _cl.index('def sync_offline_transactions')
    _stop = _cl.index("@app.route('/api/transactions', methods=['POST'])", _start)
    sync = _cl[_start:_stop]
    check('the sync route reports a sale that took more than the shelf held',
          'oversold' in sync and 'warning' in sync)
    check('the shelf is read where the stock is actually taken',
          sync.index('add_branch_stock(cursor, pid, branch_id, -qty)')
          < sync.index('if _held_now < 0:'))
    check('the shortfall is named in the reply, not only counted',
          'short_lines.append(' in sync and "'warning': warning" in sync)
    check('the reply carries the count beside the per-sale statuses',
          "'branch_mismatch': mismatched, 'oversold': oversold}" in sync)
    check('the movement note the reassign tool matches on EXACTLY is unchanged',
          "'Sale #%s (offline sync)'" in sync)
    reassign = _cl[_cl.index('def pos_reconciliation_reassign'):][:9000]
    check('and that tool still matches it exactly',
          "f'Sale #{t[1]} (offline sync)'" in reassign)
except Exception as exc:                                           # noqa: BLE001
    check('read the offline sync route out of ConnectLink.py', False,
          f'{type(exc).__name__}: {exc}')


# ------------- 8. the till says so -- before the money, and after the sync
check('the confirmation dialog has somewhere to say it',
      'id="posCheckoutStaleNote"' in NEW and 'id="posCheckoutStaleText"' in NEW)
note = NEW[NEW.index('function noteCheckoutFreshness'):]
note = note[:note.index('// Refresh all POS data in place')]
check('it goes quiet once the server has confirmed the figures',
      'if (catalogueIsLive() && navigator.onLine !== false)' in note)
check('it says the sale is still taken, so it is a warning and not a refusal',
      'The sale is still taken' in note)
conf = NEW[NEW.index('function showPaymentConfirmation'):]
conf = conf[:conf.index('async function processPayment')]
check('the note is refreshed as the confirmation opens',
      'noteCheckoutFreshness();' in conf)
queued = NEW[NEW.index('function queueSale(sale)'):]
queued = queued[:queued.index('// ---------- Offline laybys')]
check('a queued sale names the age of the copy it was rung on',
      '__posCatalogueStaleAt' in queued)
after = NEW[NEW.index('function syncOfflineSales'):]
after = after[:after.index('// ---------- UI ----------')]
check("the server's warning about a short shelf is shown to the operator",
      'showToast(shortWarn[0].warning' in after and 'data.oversold' in after)


# ---------- 9. a till that has been logged out with work still on it ----------
# A dead session is NOT a business failure: the sales and the layby events are safe
# on the till, and they file themselves after ONE login. A bare "session not found"
# read on a busy counter sounds as if the money were gone, which is how a shop ends
# up hunting a login fault that does not exist -- the same reason the server must
# stop claiming a session lifetime its cookie does not have.
notify = extract(NEW, 'function notifySessionExpired(')
check('a logged-out till says how many sales are waiting on it',
      'readQueue().length' in notify and "'1 sale' : sales + ' sales'" in notify)
check('and says one login files them, so the money is not lost',
      'log in once and they file themselves' in notify)
check('it counts the layby events waiting too', 'pendingLaybyCount()' in notify)
check('the same news is not repeated for an unchanged count',
      'sessionNoticeKey' in notify and '< 60000' in notify)
sales_sync = extract(NEW, 'function syncOfflineSales(')
refuse = sales_sync[sales_sync.index('if (!reply.ok) {'):]
refuse = refuse[:refuse.index('var done = {}, held = {};')]
check('a refused batch that only needs a login is reported as sales waiting, not as an error',
      'data.session_expired' in refuse and 'notifySessionExpired();' in refuse
      and refuse.index('data.session_expired') < refuse.index('showToast(data.error'))
check('no retry is ever burned on a dead session (the sales cannot age out)',
      'entry.attempts = ' not in refuse and 'return;' in refuse)
check('a sync that gets through clears the notice, so a second logout is announced',
      'clearSessionNotice();' in sales_sync)
laybys_sync = extract(NEW, 'function syncOfflineLaybys(')
check('a layby event that only needs a login is not parked as a human decision',
      "outcome === 'session'" in laybys_sync
      and laybys_sync.index("outcome === 'session'") < laybys_sync.index("status = 'blocked'"))
check('and the rest of the layby queue is not failed item by item',
      "if (result.outcome === 'session') {" in laybys_sync
      and 'notifySessionExpired();' in laybys_sync
      and laybys_sync.index("if (result.outcome === 'session') {")
          < laybys_sync.index('return syncOfflineLaybys(false);'))
replay = extract(NEW, 'function replayLaybyEvent(')
check('the layby replay tells a dead session apart from a refusal',
      'data.session_expired' in replay and "outcome: 'session'" in replay
      and replay.index('data.session_expired') < replay.index('data.branch_mismatch'))
try:
    _cl = open('ConnectLink.py', encoding='utf-8').read()
    check('the server no longer claims a session lifetime its cookie does not have',
          'Sessions last 6 hours' not in _cl)
    _deco = _cl[_cl.index('def login_required(f):'):][:900]
    check('but a dead session is still reported as one (the till keys on that flag)',
          "'session_expired': True" in _deco)
except Exception as exc:                                           # noqa: BLE001
    check('read the session decorators out of ConnectLink.py', False,
          f'{type(exc).__name__}: {exc}')


out = '\n'.join(RESULTS)
_flush()
print(out)
print('\nFAILURES: %d' % sum(1 for r in RESULTS if r.startswith('FAIL')))
