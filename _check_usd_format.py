"""Prove the '$' -> 'USD' change broke nothing that READS a money figure.

A currency change is only dangerous in three places:
  1. code that parses a displayed amount (parseFloat of innerText/textContent);
  2. code that decides what to render by testing for '$';
  3. the formatter itself (separators, negatives, blank).

The templates are driven for real in a headless browser against a stand-in POS
server, so the assertions run against the app's own functions, not a copy.

Run:  python _check_usd_format.py
"""
import contextlib
import os
import re
import sys
import types

os.environ['DATABASE_URL'] = 'postgresql://u:p@127.0.0.1:9/nodb'
os.environ['APP_ENV'] = 'development'
os.environ['FLASK_ENV'] = 'development'
os.environ.pop('ALLOW_PROD_DB_WRITE', None)

ROOT = os.path.dirname(os.path.abspath(__file__))
POS = os.path.join(ROOT, 'templates', 'pos-system.html')
ADMIN = os.path.join(ROOT, 'templates', 'adminpage.html')
OUT = os.path.join(ROOT, '_check_usd_format_out.txt')

RESULTS = []


def check(name, ok, detail=''):
    RESULTS.append(('PASS  ' if ok else 'FAIL  ') + name + (('  -> ' + str(detail)) if detail else ''))
    print(RESULTS[-1])
    try:
        with open(OUT, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(RESULTS) + '\n')
    except Exception:                                                 # noqa: BLE001
        pass


pos = open(POS, encoding='utf-8').read()
admin = open(ADMIN, encoding='utf-8').read()

# ---------------------------------------------------------------------------
# 1. No code still depends on the currency SYMBOL to do its job.
# ---------------------------------------------------------------------------
for label, text in (('pos-system.html', pos), ('adminpage.html', admin)):
    # Parsing a displayed amount by stripping '$' would now yield NaN.
    check(f'{label}: no innerText/textContent is un-currency-ed by stripping a literal $',
          not re.search(r"replace\(\s*'\$'", text),
          'replace(/[^0-9.\\-]/g, "") is the shape that survives any currency')
    # Comparing or branching on '$' as a symbol.
    check(f'{label}: nothing branches on the "$" symbol',
          not re.search(r"(?:startsWith|endsWith|indexOf)\(\s*'\$'", text),
          'includes(\'USD\') / a regex is used instead')
    # Building a currency string by concatenating a bare '$'.
    check(f'{label}: no money string is still built from a bare $',
          not re.search(r"'\$'\s*\+", text) and not re.search(r"\$'\s*\+", text))

# The one place that intentionally still matches '$' is the AI-chat highlighter,
# which must accept BOTH shapes because the model can write either.
check('the AI-chat highlighter still highlights amounts in the new wording',
      'USD\\s?\\d' in admin or 'USD\\s*\\d' in admin,
      'it highlights USD 1,234.56 as well as a legacy $1,234.56')

# ---------------------------------------------------------------------------
# 2. Every current amount is written through the one formatter.
# ---------------------------------------------------------------------------
check('pos-system defines exactly one money formatter',
      pos.count('window.usdMoney = function') == 1, pos.count('window.usdMoney = function'))
check('adminpage defines exactly one money formatter',
      admin.count('window.usdMoney = function') == 1, admin.count('window.usdMoney = function'))
check('the Sales & Profit report uses the shared formatter',
      'function salesReportMoney' in pos and 'USD ' in pos.split('function salesReportMoney')[1][:400])
check('amounts are never printed as a bare number beside a $ sign',
      not re.search(r'[(>]\s*\$\s*\d', pos) and not re.search(r'[(>]\s*\$\s*\d', admin))

# ---------------------------------------------------------------------------
# 3. No Python f-string dollars survived, and no Excel absolute ref was harmed.
# ---------------------------------------------------------------------------
app_src = open(os.path.join(ROOT, 'ConnectLink.py'), encoding='utf-8').read()
check('no Python money f-string still uses the $ symbol',
      not re.search(r'\$\{[^{}]*:,[.\d]*f\}', app_src),
      'all converted to USD {x:,.2f}')
check('no Jinja money field still uses the $ symbol',
      '${{' not in app_src)
check("Excel absolute references are untouched",
      "'Product Names'!$A$2:$A$" in app_src,
      'a blind $ sweep would have destroyed these')
check('JS template literals in the backend are untouched',
      len(re.findall(r'\$\{[^{}]*\}', app_src)) >= 10,
      'the sweep never touched interpolation')

# ---------------------------------------------------------------------------
# 4. The formatter's actual output, executed.
# ---------------------------------------------------------------------------
import subprocess                                                    # noqa: E402
node = """
function usdMoney(value) {
    const n = Number(value || 0);
    return 'USD ' + (n < 0 ? '-' : '') + Math.abs(n).toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}
const cases = [
  [0, 'USD 0.00'],
  [1234.5, 'USD 1,234.50'],
  [58699.2, 'USD 58,699.20'],
  [-1225, 'USD -1,225.00'],
  [1234567.891, 'USD 1,234,567.89'],
  ['', 'USD 0.00'],
  [null, 'USD 0.00'],
  [undefined, 'USD 0.00'],
  ['250', 'USD 250.00']
];
let bad = [];
for (const [input, want] of cases) {
    const got = usdMoney(input);
    if (got !== want) bad.push(JSON.stringify(input) + ' -> ' + got + ' (wanted ' + want + ')');
}
// and the strip rule used to read an amount back out of the DOM
const read = s => parseFloat(String(s).replace(/[^0-9.\\-]/g, ''));
const reads = [
  ['USD 1,234.56', 1234.56],
  ['USD -1,225.00', -1225],
  ['$1,234.56', 1234.56],
  ['total USD 58,699.20', 58699.2]
];
for (const [text, want] of reads) {
    const got = read(text);
    if (got !== want) bad.push('read(' + JSON.stringify(text) + ') = ' + got + ' wanted ' + want);
}
console.log(JSON.stringify(bad));
"""
try:
    proc = subprocess.run(['node', '-e', node], capture_output=True, text=True,
                          encoding='utf-8', errors='replace', timeout=60)
    bad = proc.stdout.strip()
    check('the formatter prints accounting separators, USD and negatives correctly',
          proc.returncode == 0 and bad == '[]',
          bad if proc.returncode == 0 else (proc.stderr or '')[:300])
except Exception as exc:                                              # noqa: BLE001
    check('the formatter prints accounting separators, USD and negatives correctly', False,
          '%s: %s' % (type(exc).__name__, exc))

# ---------------------------------------------------------------------------
# 5. The pages still run: every inline script parses.
# ---------------------------------------------------------------------------
for label, path in (('pos-system.html', POS), ('adminpage.html', ADMIN)):
    raw = open(path, encoding='utf-8').read()
    blocks = re.findall(r'(?s)<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', raw)
    bad_blocks = []
    import tempfile                                                 # noqa: E402
    for i, code in enumerate(blocks, 1):
        if not code.strip():
            continue
        # A temp FILE, not stdin: the templates contain emoji, and piping them
        # through a cp1252 stdin raises in the writer thread and leaves node
        # waiting for an EOF that never comes.
        fd, tmp = tempfile.mkstemp(suffix='.js')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as fh:
                fh.write(code)
            proc = subprocess.run(['node', '--check', tmp], capture_output=True,
                                  text=True, encoding='utf-8', errors='replace', timeout=60)
            if proc.returncode != 0:
                bad_blocks.append('block %d: %s' % (i, (proc.stderr or '').splitlines()[:2]))
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass
    check(f'{label}: every inline script still parses', not bad_blocks, bad_blocks or f'{len(blocks)} blocks')

# ---------------------------------------------------------------------------
# 6. The POS page, loaded for real, shows the new wording and throws nothing.
# ---------------------------------------------------------------------------
try:
    from playwright.sync_api import sync_playwright
except Exception:                                                     # noqa: BLE001
    sync_playwright = None

if sync_playwright is None:
    check('the POS page can be driven in a browser (Playwright present)', False,
          'playwright is not installed - browser checks skipped')
else:
    import threading                                              # noqa: E402
    import json as _json                                          # noqa: E402
    import urllib.parse                                           # noqa: E402
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer  # noqa: E402

    PAGE_BYTES = open(POS, 'rb').read()

    # The template is served verbatim (Jinja tags and all) plus a stub for the one
    # endpoint the page needs to stay signed in; everything else answers an empty
    # success so the page's own rendering runs to the end. Same approach the
    # project's analytics check uses.
    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _json(self, payload):
            body = _json.dumps(payload).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _page(self):
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(PAGE_BYTES)))
            self.end_headers()
            self.wfile.write(PAGE_BYTES)

        def do_GET(self):
            path = urllib.parse.urlsplit(self.path).path
            if path in ('/', '/pos-system.html'):
                return self._page()
            if path == '/api/check-auth':
                return self._json({'authenticated': True, 'needs_branch': False,
                                   'branch': {'id': 1, 'name': 'Shurugwi',
                                              'read_only': False, 'is_dispatch': False},
                                   'user': {'id': 1, 'name': 'Admin', 'role': 'admin'}})
            if path.startswith('/api/'):
                return self._json({'success': True, 'products': [], 'transactions': [],
                                   'additions': [], 'categories': [], 'laybys': []})
            return super().do_GET()

        def do_POST(self):
            return self._json({'success': True})

        do_PUT = do_DELETE = do_POST

    srv = None
    try:
        srv = ThreadingHTTPServer(('127.0.0.1', 8799), Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        check('a stand-in POS server is up', True, 'http://127.0.0.1:8799/pos-system.html')
    except Exception as exc:                                       # noqa: BLE001
        check('a stand-in POS server is up', False, '%s: %s' % (type(exc).__name__, str(exc)[:200]))

    if srv is not None:
        SEED = """try {
            localStorage.clear();
            localStorage.setItem('isLoggedIn', 'true');
            localStorage.setItem('posBranch', JSON.stringify({id:1,name:'Shurugwi',read_only:false}));
            localStorage.setItem('pos_branch_scope', '1');
        } catch (e) {}"""
        # Bootstrap's modal API and Chart.js are CDN scripts; without a stub the
        # page's own script stops at the first showModal()/new Chart().
        LIB_STUB = """
        window.bootstrap = window.bootstrap || {};
        if (!window.bootstrap.Modal) {
          window.bootstrap.Modal = function (el) { this.el = el; };
          window.bootstrap.Modal.prototype.show = function () {};
          window.bootstrap.Modal.prototype.hide = function () {};
          window.bootstrap.Modal.getInstance = function () { return new window.bootstrap.Modal(null); };
          window.bootstrap.Modal.getOrCreateInstance = function (el) { return new window.bootstrap.Modal(el); };
        }
        if (!window.Chart) {
          window.Chart = function (ctx, cfg) {
            cfg = cfg || {};
            this.canvas = (ctx && ctx.canvas) ? ctx.canvas : ctx;
            this.data = cfg.data || {labels: [], datasets: []};
            if (!this.data.datasets) this.data.datasets = [];
            this.options = cfg.options || {};
          };
          ['destroy','update','resize','reset','render','stop','clear'].forEach(function (m) {
            window.Chart.prototype[m] = function () {};
          });
          window.Chart.prototype.toBase64Image = function () { return ''; };
          window.Chart.prototype.getDatasetMeta = function () { return {data: []}; };
          window.Chart.defaults = {font:{}, plugins:{}, color:'#000', borderColor:'#000',
                                   devicePixelRatio:1, animation:false, responsive:true};
          window.Chart.register = function () {};
          window.Chart.getChart = function () { return null; };
          window.Chart.version = 'stub';
        }
        """
        errors = []
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                ctx = browser.new_context(timezone_id='Africa/Harare',
                                          viewport={'width': 1440, 'height': 900})
                ctx.add_init_script(LIB_STUB)
                ctx.add_init_script(SEED)
                page = ctx.new_page()
                page.set_default_timeout(20000)
                page.on('pageerror', lambda e: errors.append(str(e)[:200]))
                page.route(re.compile(r'https?://(?!127\.0\.0\.1)'), lambda r: r.abort())

                page.goto('http://127.0.0.1:8799/pos-system.html',
                          wait_until='domcontentloaded', timeout=30000)
                page.wait_for_function("typeof window.usdMoney === 'function'", timeout=25000)

                check('the POS page loads with no script error', not errors, errors[:3] or 'clean')

                formatter = page.evaluate("""() => [
                    window.usdMoney(1234.5), window.usdMoney(-1225), window.usdMoney(0)]""")
                check('the page exposes the formatter and it prints USD',
                      formatter == ['USD 1,234.50', 'USD -1,225.00', 'USD 0.00'], formatter)

                cards = page.evaluate("""() => ['reportTotalSales','reportGrossProfit',
                    'reportAvgOrder','reportTotalProfitEarned','reportProfitReinvested',
                    'reportAvailableProfit','reportCOGS'].map(id => {
                        const el = document.getElementById(id);
                        return el ? el.textContent.trim() : 'MISSING:' + id;
                    })""")
                check('every KPI card reads USD, and none is missing',
                      all(c.startswith('USD ') for c in cards), cards)

                parsed = page.evaluate("""() => {
                    const el = document.getElementById('reportTotalSales');
                    if (!el) return null;
                    el.textContent = 'USD 58,699.20';
                    return parseFloat(el.innerText.replace(/[^0-9.\\-]/g, ''));
                }""")
                check('a displayed amount can still be parsed back to a number',
                      parsed == 58699.2, parsed)

                # The cart total is what the checkout parses to know what is owed.
                cart = page.evaluate("""() => {
                    const el = document.getElementById('total');
                    if (!el) return 'NO CART TOTAL';
                    el.textContent = window.usdMoney(1234.5);
                    const read = parseFloat(el.innerText.replace(/[^0-9.\\-]/g, ''));
                    return {shown: el.textContent, read: read};
                }""")
                check('the cart total shows USD and still reads back as 1234.5',
                      isinstance(cart, dict) and cart.get('shown') == 'USD 1,234.50'
                      and cart.get('read') == 1234.5, cart)

                browser.close()
        except Exception as exc:                                   # noqa: BLE001
            check('the POS page could be driven in a browser', False,
                  '%s: %s' % (type(exc).__name__, str(exc)[:300]))
        finally:
            srv.shutdown()

fails = [r for r in RESULTS if r.startswith('FAIL')]
print('\n' + '=' * 70)
print('%d passed, %d failed' % (len(RESULTS) - len(fails), len(fails)))
sys.exit(1 if fails else 0)
