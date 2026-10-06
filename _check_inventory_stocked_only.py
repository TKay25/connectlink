"""Check for the Inventory tab's opt-in "Stocked in this branch only" switch
(templates/pos-system.html).

The background: the till hides an item this branch has NEVER stocked (the catalogue
is shared, so without that rule the other shop's whole list fills the grid), while
the Inventory tab deliberately lists every product -- that is where an item is
given a branch row again, and the audit report and the exports are read from the
same place. That default is KEPT. This adds a switch, OFF by default, so the tab
can be narrowed to what the branch actually carries.

The one thing that must NOT change: the names of those never-stocked products must
still be offered where a product is being added by NAME
  * the Add-Product form's name hints (setupAutocomplete -> productNameSuggestions),
  * the "Upload New Stock" Excel template's Product Name pick-list (built
    server-side in ConnectLink.py from the whole products table).
So this checks both halves: the switch really narrows the table (and its two
exports, which follow the table), and the hints and the template still carry every
catalogue name -- including an item this branch has never stocked.

Run:  python _check_inventory_stocked_only.py   (writes _check_inventory_stocked_only_out.txt)
"""
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import threading
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = pathlib.Path(__file__).parent
PORT = int(os.environ.get('POS_TOGGLE_PORT', '8796'))
TEMPLATE = 'templates/pos-system.html'
OUT = '_check_inventory_stocked_only_out.txt'

RESULTS = []


def _flush():
    try:
        with open(OUT, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(RESULTS) + '\n')
    except Exception:                                                  # noqa: BLE001
        pass


def check(name, ok, detail=''):
    RESULTS.append(f"{'PASS' if ok else 'FAIL'}  {name}"
                   f"{('  -> ' + detail) if detail else ''}")
    _flush()


check('script started', True)

try:
    NEW = (ROOT / TEMPLATE).read_text(encoding='utf-8')
    check('read the POS page', True, '%d chars' % len(NEW))
except Exception as exc:                                               # noqa: BLE001
    check('read the POS page', False, '%s: %s' % (type(exc).__name__, exc))
    print('\n'.join(RESULTS))
    print('\nFAILURES: 1')
    sys.exit(1)

# git is not always on the PATH of a detached process (the file lives in OneDrive and
# the console may resolve `git` through its own profile), so find it properly.
GIT = shutil.which('git')
if not GIT:
    for cand in (r'C:\Program Files\Git\cmd\git.exe',
                 r'C:\Program Files (x86)\Git\cmd\git.exe',
                 os.path.expandvars(r'%LOCALAPPDATA%\Programs\Git\cmd\git.exe'),
                 os.path.expandvars(r'%ProgramFiles%\Git\bin\git.exe')):
        if cand and os.path.exists(cand):
            GIT = cand
            break
GIT = GIT or 'git'

try:
    proc = subprocess.run([GIT, 'show', 'HEAD:' + TEMPLATE],
                          capture_output=True, cwd=str(ROOT))
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or b'').decode('utf-8', 'replace').strip()
                           or 'git show failed')
    # Decoded by hand: the page holds bytes that are not valid in the console's own
    # code page, and git hands back the blob verbatim.
    OLD = proc.stdout.decode('utf-8', 'replace')
    check('read the committed POS page for comparison', True,
          '%d chars via %s' % (len(OLD), GIT))
except Exception as exc:                                               # noqa: BLE001
    OLD = None
    check('read the committed POS page for comparison', False,
          '%s: %s' % (type(exc).__name__, exc))



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
    construct would otherwise hide every line after it.
    """
    try:
        import esprima
    except Exception as exc:                                           # noqa: BLE001
        return 'no-parser: %s' % exc, 0
    try:
        esprima.parseScript(body.replace('?.', '.'))
        return None, 0
    except Exception as exc:                                           # noqa: BLE001
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


def extract(src, start_marker, last=False):
    """The whole declaration whose text starts at `start_marker`, brace-matched.

    Comments, strings and template literals are skipped, so a brace inside any of
    them cannot end the declaration early. `last=True` reads the final occurrence
    (the page defines renderInventory twice; the later one is the one that runs).
    """
    i = src.rindex(start_marker) if last else src.index(start_marker)
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


TOUCHED = [
    ('let inventoryStockedOnly', False),
    ('function filterInventory(', False),
    ('function inventoryStockedOnlyUsable(', False),
    ('function syncInventoryStockedSwitch(', False),
    ('function renderInventory(', True),
]
bad = []
for marker, last in TOUCHED:
    try:
        snippet = extract(NEW, marker, last)
        msg, _line = first_error(snippet)
        if msg is not None:
            bad.append('%s: %s' % (marker, msg))
    except Exception as exc:                                           # noqa: BLE001
        bad.append('%s: %s' % (marker, exc))
check('every declaration this change touched parses on its own',
      not bad, '; '.join(bad[:3]))
check('all of the touched declarations were found', len(TOUCHED) == 5)


# ------------------------------- 2. the switch exists, is off, and is wired
check('the switch is declared OFF by default (the tab keeps listing everything)',
      NEW.count('let inventoryStockedOnly = ') == 1
      and 'let inventoryStockedOnly = false;' in NEW)
check('the toolbar carries the switch, hidden until the page says otherwise',
      'id="inventoryStockedOnlyWrap"' in NEW
      and 'form-check form-switch mb-0 d-none' in NEW)
check('the switch says what it does, in words',
      'Stocked in this branch only' in
      NEW[NEW.index('id="inventoryStockedOnlyWrap"'):][:900])
check('the switch sits in the toolbar, before the search box',
      NEW.index('id="inventoryStockedOnlyWrap"') < NEW.index('id="inventorySearch"'))
wiring = extract(NEW, 'function setupEventListeners(')
check('the switch is wired to the flag and to a re-render',
      "document.getElementById('inventoryStockedOnly')" in wiring
      and 'inventoryStockedOnly = !!e.target.checked;' in wiring
      and 'renderInventory();' in wiring)

# ------------------------------- 3. the table narrows; the catalogue does not
filter_fn = extract(NEW, 'function filterInventory(')
check('filterInventory narrows by this branch only when the switch is on',
      'inventoryStockedOnly ? products.filter(stockedInThisBranch) : products'
      in filter_fn)
check('and it still applies the search box on top',
      'inventorySearchTerm.toLowerCase()' in filter_fn)
check('filterInventory never reassigns the catalogue',
      'products =' not in filter_fn and 'products.push' not in filter_fn)
narrowing = [m.group(0).strip() for m in re.finditer(r'products\s*=\s*[^;\n]*', NEW)
             if '.filter(' in m.group(0) or '.slice(' in m.group(0)]
check('nothing narrows the catalogue ITSELF (products is only replaced by a payload)',
      not narrowing, '; '.join(narrowing[:3]))
check('the catalogue still comes straight from the API payload',
      'products = productsData.products;' in NEW)
winning = extract(NEW, 'function renderInventory(', last=True)
check('the renderInventory that RUNS is the one that consults the switch',
      'syncInventoryStockedSwitch();' in winning)
check('the page still defines renderInventory twice (a pre-existing duplicate)',
      NEW.count('function renderInventory(') == 2
      and (OLD is None or OLD.count('function renderInventory(') == 2))
check('the empty-table message explains the switch instead of blaming the search',
      'untick "Stocked in this branch only"' in winning)


# ------------------- 4. the Add-Product name hints still offer EVERY name
auto = extract(NEW, 'function setupAutocomplete(')
check('the Add-Product name hints still read the WHOLE catalogue',
      'products.map(p => p.name)' in auto)
check('the hints are byte-for-byte what they were before this change',
      OLD is not None and extract(OLD, 'function setupAutocomplete(') == auto)
check("the hints are not narrowed to this branch (that is the point of them)",
      'stockedInThisBranch' not in auto and 'stocked_here' not in auto)
check('the hints element is still on the Add-Product form',
      'id="productNameSuggestions"' in NEW and 'id="productName"' in NEW)


# ------------------- 5. the two inventory exports follow the table
SITE = 'const filteredProducts = filterInventory();'
xl_export = NEW[NEW.index("getElementById('downloadInventoryExcelBtn')"):][:6000]
pdf_export = NEW[NEW.index('function downloadInventoryPDF('):][:6000]
check('both inventory exports export the table as it is shown',
      SITE in xl_export and SITE in pdf_export,
      'excel=%s pdf=%s' % (SITE in xl_export, SITE in pdf_export))
check('the exports' + " call sites are unchanged by this change",
      OLD is not None and OLD.count(SITE) == NEW.count(SITE) == 4,
      'now=%d before=%s (2 renders + 2 exports)'
      % (NEW.count(SITE), OLD.count(SITE) if OLD else '?'))


# -------- 6. the Excel template still carries every catalogue product name
try:
    CL = (ROOT / 'ConnectLink.py').read_text(encoding='utf-8')
    tpl = CL[CL.index('def pos_stock_upload_template()'):]
    tpl = tpl[:tpl.index('\n@app.route', 10)]
    check('read the stock-upload template route out of ConnectLink.py', True,
          '%d chars' % len(tpl))
    check('the Product Names sheet is still built from the whole products table',
          "ws2.append(['Existing product name', 'Category', 'Buying Price', "
          "'Selling Price'])" in tpl)
    check('the template still lists EVERY active product name (no branch filter)',
          'FROM products WHERE is_active = TRUE ORDER BY name' in tpl
          and 'stocked_here' not in tpl
          and 'product_stock' not in tpl
          and 'branch_id' not in tpl)
    check('that sheet is still the pick-list behind the Product Name column',
          "'Product Names'!$A$2:$A$" in tpl and "dv.add('A2:A%d'" in tpl)
except Exception as exc:                                              # noqa: BLE001
    check('read the stock-upload template route out of ConnectLink.py', False,
          '%s: %s' % (type(exc).__name__, exc))


# =====================================================================
# 7. the real page, in a real browser, against stand-in POS API answers
# =====================================================================
def product(pid, name, stock, stocked_here):
    return {'id': pid, 'name': name, 'category': 'Audio', 'unit_type': 'piece',
            'unit_details': '', 'buy_price': 10.0, 'sell_price': 15.0,
            'stock': stock, 'min_stock_level': 5, 'description': '',
            'barcode': 'bc%d' % pid, 'created_at': None, 'updated_at': None,
            'total_stock': stock, 'branch_sell_price': 15.0,
            'stock_value': 10.0 * stock, 'stocked_here': stocked_here,
            'low_stock': False}


HERE_A = product(7, 'Stocked Speaker', 8, True)        # this branch carries it
HERE_B = product(8, 'Stocked Cable', 3, True)          # this branch carries it
ELSEWHERE = product(9, 'Chegutu-Only Speaker', 0, False)   # never stocked here
BRANCH = {'id': 1, 'code': 'SHU', 'name': 'Shurugwi', 'read_only': False}
ALL_BRANCHES = {'id': 0, 'name': 'All Branches', 'read_only': True}

# Consolidated view: no single branch, so the server reports the company total and
# every item counts as "stocked" (see ConnectLink.py: TRUE AS stocked_here).
ctl = {'consolidated': False}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def log_message(self, *a):
        pass  # keep the console quiet

    def _json(self, payload, code=200):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _page(self):
        body = (ROOT / TEMPLATE).read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        if path in ('/', '/pos-system.html', '/pos-system'):
            return self._page()
        if path == '/__consolidated':
            ctl['consolidated'] = True
            return self._json({'ok': True})
        if path == '/api/check-auth':
            branch = ALL_BRANCHES if ctl['consolidated'] else BRANCH
            return self._json({'authenticated': True, 'branch': branch,
                               'needs_branch': False,
                               'user': {'id': 1, 'name': 'Administrator',
                                        'role': 'admin'}})
        if path == '/api/products':
            if ctl['consolidated']:
                rows = [dict(p, stocked_here=True) for p in
                        (HERE_A, HERE_B, ELSEWHERE)]
            else:
                rows = [HERE_A, HERE_B, ELSEWHERE]
            return self._json({'success': True, 'products': rows, 'total': len(rows)})
        if path == '/api/dashboard-stats' or path == '/api/dashboard/stats':
            return self._json({'success': True, 'today_sales': 0.0, 'items_sold': 0,
                               'low_stock_count': 0, 'total_products': 3,
                               'total_profit': 0.0})
        if path.startswith('/api/transactions'):
            return self._json({'success': True, 'transactions': [],
                               'todaySales': 0.0, 'itemsSold': 0})
        if path.startswith('/api/'):
            return self._json({'success': True})
        return super().do_GET()          # /static/... straight off the disk

    def do_POST(self):
        length = int(self.headers.get('Content-Length') or 0)
        if length:
            self.rfile.read(length)
        self._json({'success': True})


def serve():
    httpd = ThreadingHTTPServer(('127.0.0.1', PORT), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


# Enough of Bootstrap's modal API for the page to finish booting without the CDN.
BOOTSTRAP_STUB = """
window.bootstrap = window.bootstrap || {};
if (!window.bootstrap.Modal) {
  window.bootstrap.Modal = function (el) { this.el = el; };
  window.bootstrap.Modal.prototype.show = function () {};
  window.bootstrap.Modal.prototype.hide = function () {};
  window.bootstrap.Modal.getInstance = function () { return new window.bootstrap.Modal(null); };
  window.bootstrap.Modal.getOrCreateInstance = function (el) { return new window.bootstrap.Modal(el); };
}
"""

# What the table is showing, in one read: the row names, what the catalogue itself
# holds, and the switch's own state.
READ = """() => ({
    names: Array.from(document.querySelectorAll('#inventoryList tr'))
        .map(tr => (tr.querySelectorAll('td')[1] || {}).innerText || '')
        .map(s => s.trim().split('\\n')[0]).filter(Boolean),
    empty: document.getElementById('inventoryList').innerText.trim().slice(0, 120),
    catalogue: products.length,
    flag: inventoryStockedOnly,
    hidden: document.getElementById('inventoryStockedOnlyWrap').classList.contains('d-none'),
    checked: document.getElementById('inventoryStockedOnly').checked,
    label: (document.querySelector('label[for="inventoryStockedOnly"]') || {}).innerText || '',
})"""

HINTS = """() => document.getElementById('productNameSuggestions').innerText"""

from playwright.sync_api import sync_playwright                          # noqa: E402

BASE = 'http://127.0.0.1:%d' % PORT

httpd = serve()
check('the throw-away POS server is up', True, BASE)

try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context()
        ctx.add_init_script(BOOTSTRAP_STUB)
        page = ctx.new_page()
        page.set_default_timeout(20000)
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)[:160]))
        # No external network: the page's CDN libraries are irrelevant here (the
        # modal API it needs is stubbed) and reaching for them only makes the run
        # slow and flaky.
        page.route(re.compile(r'https?://(?!127\.0\.0\.1)'), lambda r: r.abort())

        page.goto(BASE + '/pos-system.html', wait_until='domcontentloaded',
                  timeout=30000)
        page.wait_for_function(
            "typeof filterInventory === 'function'"
            " && typeof window.refreshCatalogueIfStale === 'function'", timeout=20000)
        check('the page loads with this change installed', True)

        # init() ends with navigateTo('pos') after four awaited fetches, so let it
        # settle first -- otherwise it re-hides the tab a moment after it is opened.
        page.wait_for_timeout(1500)
        shown = False
        for _ in range(6):
            page.evaluate("() => navigateTo('inventory')")
            page.wait_for_timeout(300)
            if page.evaluate("getComputedStyle("
                             "document.getElementById('inventoryPage')).display") == 'block':
                shown = True
                break
        check('the Inventory tab opens (the page is really shown)', shown)
        started = page.evaluate(READ)

        # 1. the default is unchanged: the tab lists the whole catalogue
        check('with the switch OFF the tab still lists EVERY product',
              sorted(started['names']) == sorted(['Stocked Speaker', 'Stocked Cable',
                                                  'Chegutu-Only Speaker']),
              json.dumps(started['names']))
        check('including the item this branch has NEVER stocked',
              'Chegutu-Only Speaker' in started['names'])
        check('the switch is offered on a real branch, unticked, and named in words',
              started['hidden'] is False and started['checked'] is False
              and started['label'].strip() == 'Stocked in this branch only',
              json.dumps({k: started[k] for k in ('hidden', 'checked', 'label')}))
        check('the switch starts from the OFF default in code too',
              started['flag'] is False)

        # 2. ticking it narrows the table to what this branch carries. The probe is
        #    deliberately separate from the click: the switch must be really laid out
        #    (an operator has to be able to tick it), and the toggle below drives the
        #    very same 'change' listener a mouse click fires.
        probe = page.evaluate("""() => {
            const el = document.getElementById('inventoryStockedOnly');
            const r = el.getBoundingClientRect();
            const cs = getComputedStyle(el);
            const chain = [];
            for (let n = el; n && n !== document.body; n = n.parentElement) {
                const s = getComputedStyle(n);
                chain.push((n.id || n.tagName) + ':' + s.display + '/' + s.visibility);
            }
            return {w: Math.round(r.width), h: Math.round(r.height),
                    disp: cs.display, vis: cs.visibility,
                    inline: el.getAttribute('style'),
                    page: getComputedStyle(document.getElementById('inventoryPage')).display,
                    rows: document.querySelectorAll('#inventoryList tr').length,
                    chain: chain.join(' < ')};
        }""")
        check('the switch is really laid out on the page, not hidden in a wrapper',
              probe['w'] > 0 and probe['h'] > 0 and probe['disp'] != 'none'
              and probe['vis'] != 'hidden', json.dumps(probe))

        TOGGLE = """(want) => {
            const el = document.getElementById('inventoryStockedOnly');
            if (el.checked !== want) el.click();   // fires the switch's own listener
            return el.checked;
        }"""
        SET = """(args) => {
            const el = document.querySelector(args.sel);
            el.value = args.v;
            el.dispatchEvent(new Event('input', {bubbles: true}));
        }"""
        check('ticking the switch is what narrows the table (a real change event)',
              page.evaluate(TOGGLE, True) is True)
        page.wait_for_timeout(400)
        on = page.evaluate(READ)
        check('ticking it drops the item this branch has never stocked',
              'Chegutu-Only Speaker' not in on['names'],
              json.dumps(on['names']))
        check('and keeps the items this branch does carry',
              sorted(on['names']) == sorted(['Stocked Speaker', 'Stocked Cable']),
              json.dumps(on['names']))
        check('the CATALOGUE itself is untouched (only the view narrowed)',
              on['catalogue'] == 3 and on['flag'] is True
              and page.evaluate('products.length') == 3,
              'catalogue=%s flag=%s' % (on['catalogue'], on['flag']))

        # 3. THE requirement: the never-stocked name is still offered as a hint when
        #    a product is being added by name -- even with the switch ON.
        page.evaluate(SET, {'sel': '#productName', 'v': 'Chegutu'})
        page.wait_for_timeout(250)
        hints = page.evaluate(HINTS)
        check('the Add-Product name hints still offer a never-stocked product, '
              'with the switch ON',
              'Chegutu-Only Speaker' in hints, hints[:120])

        # 4. the search box and the switch work together
        page.evaluate(SET, {'sel': '#inventorySearch', 'v': 'chegutu'})
        page.wait_for_timeout(400)
        searched = page.evaluate(READ)
        check('searching for a never-stocked item with the switch ON finds nothing',
              searched['names'] == [], json.dumps(searched['names']))
        page.evaluate(TOGGLE, False)
        page.wait_for_timeout(400)
        back = page.evaluate(READ)
        check('unticking the switch brings it straight back',
              back['names'] == ['Chegutu-Only Speaker'], json.dumps(back['names']))
        page.evaluate(SET, {'sel': '#inventorySearch', 'v': ''})
        page.wait_for_timeout(400)

        # 5. the read-only All Branches view: no switch, and no hidden filter
        page.evaluate("""async () => {
            await fetch('/__consolidated');
            applyPOSBranch(%s);
            await fetchProductsFromAPI();
            inventoryStockedOnly = true;   // as if left on in the branch view
            renderInventory();
        }""" % json.dumps(ALL_BRANCHES))
        page.wait_for_timeout(700)
        consolidated = page.evaluate(READ)
        check('on the read-only All Branches view the switch is hidden',
              consolidated['hidden'] is True, json.dumps(consolidated['hidden']))
        check('and a switch left on cannot go on filtering from behind it',
              consolidated['flag'] is False)
        check('so the consolidated view lists every product, as it always did',
              sorted(consolidated['names']) == sorted(['Stocked Speaker',
                                                       'Stocked Cable',
                                                       'Chegutu-Only Speaker']),
              json.dumps(consolidated['names']))

        check('no page error was raised (the switch can see stockedInThisBranch)',
              not errors, ' | '.join(errors[:3]))

        browser.close()
except Exception as exc:                                                 # noqa: BLE001
    import traceback
    check('the browser run completed', False,
          '%s: %s' % (type(exc).__name__, exc))
    RESULTS.append(traceback.format_exc(limit=3))
    try:
        RESULTS.append('page errors: ' + ' | '.join(errors[:5]))
    except Exception:                                                    # noqa: BLE001
        pass
finally:
    httpd.shutdown()

out = '\n'.join(RESULTS)
try:
    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write(out + '\n')
except Exception:                                                        # noqa: BLE001
    pass
print(out)
print('\nFAILURES: %d' % sum(1 for r in RESULTS if r.startswith('FAIL')))



