"""Prove the POS header (Today's Sales / Items Sold) follows the All|Hardware|Furniture switch.

Serves the real template against a stand-in POS server whose dashboard figures
depend on the department the session is showing, then clicks the switch the way
a cashier would and reads the two pills back out of the DOM.

Run:  python _check_pos_header_stats.py
"""
import os
import re
import sys

os.environ['DATABASE_URL'] = 'postgresql://u:p@127.0.0.1:9/nodb'
os.environ['APP_ENV'] = 'development'
os.environ['FLASK_ENV'] = 'development'
os.environ.pop('ALLOW_PROD_DB_WRITE', None)

ROOT = os.path.dirname(os.path.abspath(__file__))
POS = os.path.join(ROOT, 'templates', 'pos-system.html')

RESULTS = []


def check(name, ok, detail=''):
    RESULTS.append(('PASS  ' if ok else 'FAIL  ') + name + (('  -> ' + str(detail)) if detail else ''))
    print(RESULTS[-1])


# ---------------------------------------------------------------------------
# Static: the switch must re-read the header figures.
# ---------------------------------------------------------------------------
pos = open(POS, encoding='utf-8').read()

switch_block = pos.split('async function switchDepartment(dept)')[1].split('window.switchDepartment')[0]
check('switching department re-reads the header stats',
      'fetchDashboardStats' in switch_block,
      'switchDepartment must call fetchDashboardStats()')
check('switching department no longer calls a function that does not exist',
      'loadStats(' not in switch_block,
      "typeof loadStats === 'function' is always false - there is no loadStats")
check('the header pills are written by renderPOSHeaderStats',
      "document.getElementById('itemsSoldChip')" in pos
      and "document.getElementById('todaySalesChip')" in pos)

try:
    from playwright.sync_api import sync_playwright
except Exception:                                                  # noqa: BLE001
    sync_playwright = None

if sync_playwright is None:
    check('playwright is available for the browser run', False, 'pip install playwright')
    print('\n'.join(RESULTS))
    sys.exit(0 if all(r.startswith('PASS') for r in RESULTS) else 1)

import json as _json                                               # noqa: E402
import threading                                                   # noqa: E402
import urllib.parse                                                # noqa: E402
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer  # noqa: E402

PAGE_BYTES = open(POS, 'rb').read()

# One shop, two shelves. The numbers a real till would produce: All is the sum.
SALES = {
    'hardware': {'sales': 1000.00, 'items': 4, 'cashiers': [('Mrs G Admin', 1000.00, 4, 2)]},
    'furniture': {'sales': 990.75, 'items': 3, 'cashiers': [('Mrs G Admin', 990.75, 3, 1)]},
}
SALES['all'] = {
    'sales': round(SALES['hardware']['sales'] + SALES['furniture']['sales'], 2),
    'items': SALES['hardware']['items'] + SALES['furniture']['items'],
    'cashiers': [('Mrs G Admin', SALES['hardware']['sales'] + SALES['furniture']['sales'],
                  SALES['hardware']['items'] + SALES['furniture']['items'], 3)],
}

STATE = {'dept': 'all', 'stats_calls': 0, 'seen_depts': []}


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, payload, status=200):
        body = _json.dumps(payload).encode()
        self.send_response(status)
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

    def _body(self):
        length = int(self.headers.get('Content-Length') or 0)
        raw = self.rfile.read(length) if length else b'{}'
        try:
            return _json.loads(raw or b'{}')
        except Exception:                                          # noqa: BLE001
            return {}

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        dept = STATE['dept']
        if path in ('/', '/pos-system.html'):
            return self._page()
        if path == '/api/check-auth':
            return self._json({'authenticated': True, 'needs_branch': False,
                               'branch': {'id': 1, 'name': 'Shurugwi',
                                          'read_only': False, 'is_dispatch': False},
                               'user': {'id': 1, 'name': 'Admin', 'role': 'admin'},
                               'department': {'key': dept}})
        if path == '/api/dashboard/stats':
            STATE['stats_calls'] += 1
            STATE['seen_depts'].append(dept)
            row = SALES[dept]
            return self._json({'success': True, 'stats': {
                'today_sales': row['sales'], 'items_sold': row['items'],
                'low_stock_count': 0, 'total_products': 10, 'total_profit': 250.0}})
        if path == '/api/dashboard/today-by-cashier':
            row = SALES[dept]
            cashiers = [{'cashier': c[0], 'total': c[1], 'items_sold': c[2],
                         'transaction_count': c[3], 'payment_methods': {'cash': c[1]}}
                        for c in row['cashiers']]
            return self._json({'success': True, 'cashiers': cashiers,
                               'grand_total': row['sales']})
        if path.startswith('/api/'):
            return self._json({'success': True, 'products': [], 'transactions': [],
                               'additions': [], 'categories': [], 'laybys': [],
                               'department': {'key': dept}})
        return super().do_GET()

    def do_POST(self):
        path = urllib.parse.urlsplit(self.path).path
        payload = self._body()
        if path == '/api/pos/switch-department':
            dept = str(payload.get('department') or 'all')
            if dept not in ('all', 'hardware', 'furniture'):
                return self._json({'success': False, 'message': 'bad department'}, 400)
            STATE['dept'] = dept
            return self._json({'success': True, 'department': dept,
                               'label': dept.title()})
        return self._json({'success': True})


srv = None
try:
    srv = ThreadingHTTPServer(('127.0.0.1', 8801), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    check('a stand-in POS server is up', True, 'http://127.0.0.1:8801/pos-system.html')
except Exception as exc:                                           # noqa: BLE001
    check('a stand-in POS server is up', False, '%s: %s' % (type(exc).__name__, str(exc)[:200]))

if srv is not None:
    SEED = """try {
        localStorage.clear();
        localStorage.setItem('isLoggedIn', 'true');
        localStorage.setItem('posBranch', JSON.stringify({id:1,name:'Shurugwi',read_only:false}));
        localStorage.setItem('pos_branch_scope', '1');
    } catch (e) {}"""
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
            page.set_default_timeout(25000)
            page.on('pageerror', lambda e: errors.append(str(e)[:200]))
            page.route(re.compile(r'https?://(?!127\.0\.0\.1)'), lambda r: r.abort())

            page.goto('http://127.0.0.1:8801/pos-system.html',
                      wait_until='domcontentloaded', timeout=30000)
            page.wait_for_function("typeof window.fetchDashboardStats === 'function'", timeout=25000)

            def pills():
                return page.evaluate("""() => {
                    const s = document.getElementById('todaySalesChip');
                    const i = document.getElementById('itemsSoldChip');
                    return [s ? s.textContent.trim() : 'MISSING', i ? i.textContent.trim() : 'MISSING'];
                }""")

            # Land on All and read the pills exactly as they are on screen.
            page.evaluate("() => window.fetchDashboardStats()")
            page.wait_for_timeout(400)
            landed = pills()
            check('the header lands on All (whole-shop) figures',
                  landed == ['USD 1,990.75', '7'], landed)

            def click_and_read(dept):
                page.evaluate("d => window.switchDepartment(d)", dept)
                page.wait_for_timeout(1200)
                return pills()

            furn = click_and_read('furniture')
            check("switching to Furniture moves the header to that shelf's figures",
                  furn == ['USD 990.75', '3'], furn)
            check('the request really was re-read for furniture',
                  STATE['seen_depts'][-1] == 'furniture', STATE['seen_depts'][-4:])

            hw = click_and_read('hardware')
            check("switching to Hardware moves the header to that shelf's figures",
                  hw == ['USD 1,000.00', '4'], hw)

            back = click_and_read('all')
            check('switching back to All restores the whole-shop totals',
                  back == ['USD 1,990.75', '7'], back)

            # The breakdown beside the pills must agree with them, on every shelf.
            for dept, expected in (('furniture', 'USD 990.75'), ('all', 'USD 1,990.75')):
                page.evaluate("d => window.switchDepartment(d)", dept)
                page.wait_for_timeout(1200)
                card = page.evaluate("""() => {
                    const c = document.getElementById('cashierBreakdown');
                    return c ? c.textContent.replace(/\\s+/g, ' ').trim() : 'MISSING';
                }""")
                check(f'the cashier breakdown beside the pills agrees on {dept}',
                      expected in card, card[:120])

            check('no page script error was thrown', not errors, errors[:3] or 'clean')
            browser.close()
    except Exception as exc:                                       # noqa: BLE001
        check('the browser run completed', False, '%s: %s' % (type(exc).__name__, str(exc)[:300]))
    finally:
        try:
            srv.shutdown()
        except Exception:                                          # noqa: BLE001
            pass

failures = [r for r in RESULTS if r.startswith('FAIL')]
print('\n%d checks, %d failed' % (len(RESULTS), len(failures)))
sys.exit(1 if failures else 0)
