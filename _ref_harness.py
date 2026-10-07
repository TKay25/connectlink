"""Check that the Inventory tab lists ONLY what this branch carries
(templates/pos-system.html) -- and that the NAMES are still offered where a name is
typed (templates/pos-system.html + ConnectLink.py).

The rule: the catalogue is SHARED, so an item created for another shop used to fill
this shop's Inventory table with a row reading "Not stocked here" -- a line nobody
here can sell, count or correct. An item this branch carries has a row in
product_stock; NO row means it has never been here. The Inventory table, its metrics
and its two exports (which follow the table) now list only the former. There is no
switch back: the consolidated read-only All Branches view is the place where every
item really is the company's own, and it still lists everything.

The one thing that must NOT break is the reason those rows were reachable at all: the
NAME of such an item has to stay available, or the same product gets created a second
time under a second spelling -- and the same product then carries two names across the
branches. So both name surfaces must still carry EVERY catalogue name:
  * the Add-Product form's name hints (setupAutocomplete -> productNameSuggestions),
    which now mark such a name "already in the catalogue at another branch - use this
    exact name";
  * the "Upload New Stock" Excel template's Product Names pick-list (built server-side
    in ConnectLink.py from the whole products table), whose Product Name cell carries
    that rule as an input hint.

Run:  python _check_inventory_stocked_only.py   (writes _check_inventory_stocked_only_out.txt)

The rule half needs nothing but the standard library. The browser half (the last
section) needs the project's virtual environment -- esprima for the syntax checks and
Playwright + Chromium for the run -- so use:

    .venv\\Scripts\\python.exe _check_inventory_stocked_only.py
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
APP = 'ConnectLink.py'
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
    APP_SRC = (ROOT / APP).read_text(encoding='utf-8')
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

OLD = None
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
    check('read the committed POS page for comparison', False,
          'no baseline, syntax diff skipped (%s)' % exc)

def blocks(html):
    """(first line number, body) for every inline <script> in the page."""
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


# =====================================================================
# 1. the rule: the table lists this branch's stock, and only that
# =====================================================================
TOUCHED = [
    ('let inventorySearchTerm', False),
    ('function filterInventory(', False),
    ('function inventoryEmptyNote(', False),
    ('function stockedInThisBranch(', False),
    ('function renderInventory(', True),
    ('function setupAutocomplete(', False),
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
check('all of the touched declarations were found', len(TOUCHED) == 6)

check('the opt-in switch is gone from the page entirely',
      'inventoryStockedOnly' not in NEW
      and 'Stocked in this branch only' not in NEW)
check('so the old "list the whole catalogue" default cannot come back',
      '? products.filter(stockedInThisBranch) : products' not in NEW
      and 'let inventoryStockedOnly' not in NEW)

filter_fn = extract(NEW, 'function filterInventory(')
check('filterInventory narrows to what this branch carries, with no way round it',
      'const rows = products.filter(stockedInThisBranch);' in filter_fn)
check('and it still applies the search box on top of that',
      'inventorySearchTerm.toLowerCase()' in filter_fn
      and 'p.name.toLowerCase().includes(term)' in filter_fn)
check('filterInventory only ever READS the catalogue (never reassigns it)',
      'products =' not in filter_fn and 'products.push' not in filter_fn)
narrowing = [m.group(0).strip() for m in re.finditer(r'products\s*=\s*[^;\n]*', NEW)
             if '.filter(' in m.group(0) or '.slice(' in m.group(0)]
check('nothing narrows the catalogue ITSELF (products is only replaced by a payload)',
      not narrowing, '; '.join(narrowing[:3]))
check('the catalogue still comes straight from the API payload',
      'products = productsData.products;' in NEW)
winning = extract(NEW, 'function renderInventory(', last=True)
check('the renderInventory that RUNS lists the narrowed set',
      'const filteredProducts = filterInventory();' in winning)
check('the page still defines renderInventory twice (a pre-existing duplicate)',
      NEW.count('function renderInventory(') == 2
      and (OLD is None or OLD.count('function renderInventory(') == 2))
check('the winning render has no trace of the removed switch',
      'inventoryStockedOnly' not in winning
      and 'syncInventoryStockedSwitch' not in winning)
check('the empty table says why, and names the way in',
      'inventoryEmptyNote()' in winning)
note_fn = extract(NEW, 'function inventoryEmptyNote(')
check('the empty note offers Upload New Stock, or the exact existing name',
      'Upload New Stock' in note_fn and 'exact name' in note_fn
      and 'stockedInThisBranch' in note_fn)
check('the note covers both real cases (nothing stocked here / no such search hit)',
      'Nothing is stocked in this branch yet' in note_fn
      and 'No products found matching your search.' in note_fn)
check('the metrics can never disagree with the table (the same branch rule)',
      'products.filter(stockedInThisBranch)'
      in extract(NEW, 'function updateInventoryMetrics('))


# ------------------- 2. the two inventory exports follow the table
SITE = 'const filteredProducts = filterInventory();'
xl_export = NEW[NEW.index("getElementById('downloadInventoryExcelBtn')"):][:6000]
pdf_export = NEW[NEW.index('function downloadInventoryPDF('):][:6000]
check('both inventory exports export the table as it is shown',
      SITE in xl_export and SITE in pdf_export,
      'excel=%s pdf=%s' % (SITE in xl_export, SITE in pdf_export))
check('the exports call sites are unchanged by this change',
      OLD is not None and OLD.count(SITE) == NEW.count(SITE) == 4,
      'now=%d before=%s (2 renders + 2 exports)'
      % (NEW.count(SITE), OLD.count(SITE) if OLD else '?'))

# The consolidated view is the one place where every item really is the company's own,
# so the server reports every row as stocked there -- and the rule above lists them all.
check('the All Branches view still reports every item as the company\'s',
      'TRUE AS stocked_here' in APP_SRC
      and '(ps.product_id IS NOT NULL) AS stocked_here' in APP_SRC)


# ------------------- 3. the Add-Product name hints still offer EVERY name
auto = extract(NEW, 'function setupAutocomplete(')
check('the Add-Product name hints still read the WHOLE catalogue',
      'products.map(p => p.name)' in auto
      and 'const matches = existingNames.filter(name => '
          'name.toLowerCase().includes(inputValue));' in auto)
check('a name this branch has never stocked is marked as such in the hints',
      '!stockedInThisBranch(existingProduct)' in auto
      and 'already in the catalogue at another branch - use this exact name' in auto)
check('and picking it still fills the form from the product it names',
      'productNameInput.value = match;' in auto and 'if (existingProduct) {' in auto)
check('the marker is the only thing this change did to the hints',
      OLD is not None
      and 'another branch' not in extract(OLD, 'function setupAutocomplete('),
      'marks a name that is only in the other branch\'s catalogue')
check('the hints element is still on the Add-Product form',
      'id="productNameSuggestions"' in NEW and 'id="productName"' in NEW)
check('the till\'s own empty search points at the two ways in',
      'Upload New Stock, or Add Product with that exact name' in NEW)
check('the Upload New Stock steps point at the pick-list',
      'Product Names' in NEW
      and 'pick an existing name to add stock to that product' in NEW)


# -------- 4. the Excel template still carries every catalogue product name
try:
    tpl = APP_SRC[APP_SRC.index('def pos_stock_upload_template()'):]
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
    check('and the Product Name cell now carries the one-name rule as an input hint',
          'dv.promptTitle = ' in tpl and 'creates a NEW product' in tpl
          and 'name the catalogue already uses' in tpl)
except Exception as exc:                                              # noqa: BLE001
    check('read the stock-upload template route out of ConnectLink.py', False,
          '%s: %s' % (type(exc).__name__, exc))


# =====================================================================
# 5. the real page, in a real browser, against stand-in POS API answers
# =====================================================================
def product(pid, name, stock, stocked_here):
    return {'id': pid, 'name': name, 'category': 'Audio', 'unit_type': 'piece',
            'unit_details': '', 'buy_price': 10.0, 'sell_price': 15.0,
            'stock': stock, 'min_stock_level': 5, 'description': '',
            'barcode': 'bc%d' % pid, 'created_at': None, 'updated_at': None,
            'total_stock': stock, 'branch_sell_price': 15.0,
            'stock_value': 10.0 * stock, 'stocked_here': stocked_here,
            'low_stock': False}


HERE_A = product(7, 'Stocked Speaker', 8, True)          # this branch carries it
HERE_B = product(8, 'Stocked Cable', 3, True)            # this branch carries it
ELSEWHERE = product(9, 'Chegutu-Only Speaker', 0, False)  # never stocked here
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

# What the table is showing, in one read: the row names, the words actually in the
# rows (no row may read "Not stocked here"), and what the catalogue itself holds.
READ = """() => ({
    names: Array.from(document.querySelectorAll('#inventoryList tr'))
        .map(tr => (tr.querySelectorAll('td')[1] || {}).innerText || '')
        .map(s => s.trim().split('\\n')[0]).filter(Boolean),
    words: document.getElementById('inventoryList').innerText.replace(/\\s+/g, ' ').trim().slice(0, 300),
    empty: document.getElementById('inventoryList').innerText.trim().slice(0, 220),
    catalogue: products.length,
    elsewhere: products.filter(p => !stockedInThisBranch(p)).length,
    switchOnPage: !!document.getElementById('inventoryStockedOnly'),
})"""

HINTS = """() => document.getElementById('productNameSuggestions').innerText"""

SET = """(args) => {
    const el = document.querySelector(args.sel);
    el.value = args.v;
    el.dispatchEvent(new Event('input', {bubbles: true}));
}"""

try:
    from playwright.sync_api import sync_playwright                      # noqa: E402
except Exception as exc:                                                 # noqa: BLE001
    # Everything above is a rule read out of the two files and needs no browser; it is
    # reported even when the driver is missing, so a bare `python` still says what it
    # checked instead of dying in a traceback.
    check('the browser driver (Playwright) is installed', False,
          '%s: %s -- run this with .venv\\Scripts\\python.exe'
          % (type(exc).__name__, exc))
    _out = '\n'.join(RESULTS)
    try:
        with open(OUT, 'w', encoding='utf-8') as fh:
            fh.write(_out + '\n')
    except Exception:                                                    # noqa: BLE001
        pass
    print(_out)
    print('\nFAILURES: %d' % sum(1 for r in RESULTS if r.startswith('FAIL')))
    raise SystemExit(1)

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
            " && typeof inventoryEmptyNote === 'function'"
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

        # 1. THE requirement: the table lists this branch's stock, and nothing else
        check('the table lists exactly what this branch carries',
              sorted(started['names']) == sorted(['Stocked Speaker', 'Stocked Cable']),
              json.dumps(started['names']))
        check('the item this branch has NEVER stocked is not listed',
              'Chegutu-Only Speaker' not in started['names'])
        check('no row reads "Not stocked here" any more',
              'Not stocked here' not in started['words'], started['words'][:160])
        check('and there is no switch left to bring such a row back',
              started['switchOnPage'] is False)
        check('the CATALOGUE is untouched (only the view narrowed)',
              started['catalogue'] == 3 and started['elsewhere'] == 1,
              'catalogue=%s elsewhere=%s' % (started['catalogue'],
                                             started['elsewhere']))

        # 2. the search box still works within the branch's own items
        page.evaluate(SET, {'sel': '#inventorySearch', 'v': 'cable'})
        page.wait_for_timeout(400)
        found = page.evaluate(READ)
        check("searching finds this branch's own item",
              found['names'] == ['Stocked Cable'], json.dumps(found['names']))

        # 3. a search for a name only the other branch carries says so, and points at
        #    the way in (the alternative being a second product for the same thing)
        page.evaluate(SET, {'sel': '#inventorySearch', 'v': 'chegutu'})
        page.wait_for_timeout(400)
        missed = page.evaluate(READ)
        check('searching for a never-stocked item finds no row',
              missed['names'] == [], json.dumps(missed['names']))
        check('and the table says why, and how to start stocking it',
              'Upload New Stock' in missed['empty'] and 'exact name' in missed['empty'],
              missed['empty'][:160])
        page.evaluate(SET, {'sel': '#inventorySearch', 'v': ''})
        page.wait_for_timeout(400)

        # 4. THE hint that makes the hiding safe: the name is still offered where a
        #    product is being added by name.
        page.evaluate(SET, {'sel': '#productName', 'v': 'Chegutu'})
        page.wait_for_timeout(250)
        hints = page.evaluate(HINTS)
        check('the Add-Product name hints still offer a never-stocked product',
              'Chegutu-Only Speaker' in hints, hints[:120])
        check("and say that the name is already the catalogue's, at another branch",
              'another branch' in hints and 'exact name' in hints, hints[:170])
        page.evaluate(SET, {'sel': '#productName', 'v': ''})
        page.wait_for_timeout(200)

        # 5. the read-only All Branches view: every item really is the company's own
        page.evaluate("""async () => {
            await fetch('/__consolidated');
            applyPOSBranch(%s);
            await fetchProductsFromAPI();
            renderInventory();
        }""" % json.dumps(ALL_BRANCHES))
        page.wait_for_timeout(700)
        consolidated = page.evaluate(READ)
        check('on the read-only All Branches view every product is listed again',
              sorted(consolidated['names']) == sorted(['Stocked Speaker',
                                                       'Stocked Cable',
                                                       'Chegutu-Only Speaker']),
              json.dumps(consolidated['names']))
        check("because the server there reports every item as the company's",
              consolidated['elsewhere'] == 0)

        check('no page error was raised (the page can see stockedInThisBranch)',
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
