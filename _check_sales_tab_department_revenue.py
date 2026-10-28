"""Prove the Sales tab reports each shelf's OWN money.

GET /api/transactions keeps a receipt's `total` (the whole basket) but returns
only the department's lines inside it. Summing `total` therefore charged a mixed
basket to Hardware and to Furniture in full, while COGS and profit came from the
shelf's lines alone -- an inflated margin, and a figure the exported PDF (built
from the line-level summary) could never match.

This drives the real template in a headless browser against a stand-in POS server
that answers exactly like the real endpoint does, and reads the KPI cards back.

Run:  python _check_sales_tab_department_revenue.py
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
OUT = os.path.join(ROOT, '_check_sales_tab_department_revenue_out.txt')
RESULTS = []


def check(name, ok, detail=''):
    RESULTS.append(('PASS  ' if ok else 'FAIL  ') + name + (('  -> ' + str(detail)) if detail else ''))
    print(RESULTS[-1])
    try:
        with open(OUT, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(RESULTS) + '\n')
    except Exception:                                                     # noqa: BLE001
        pass


pos = open(POS, encoding='utf-8').read()
report = pos.split('function renderSalesReport(')[1].split('\n    const grossMargin')[0]
check('the Sales tab no longer sums the whole receipt for a department view',
      'totalRevenue += t.total;' not in report and 'totalRevenue += revenue;' in report)
check('the Sales tab prices each sale from its own LINES',
      'lineRevenue' in report and 't.revenue = revenue' in report)
check('a receipt with no lines still counts at its total',
      'Number(t.total) || 0' in report)

try:
    from playwright.sync_api import sync_playwright
except Exception:                                                         # noqa: BLE001
    sync_playwright = None

if sync_playwright is None:
    check('playwright is available for the browser run', False, 'pip install playwright')
    print('\n'.join(RESULTS))
    sys.exit(0 if all(r.startswith('PASS') for r in RESULTS) else 1)

import datetime as _dt                                                    # noqa: E402
import json as _json                                                      # noqa: E402
import threading                                                          # noqa: E402
import urllib.parse                                                       # noqa: E402
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer      # noqa: E402

PAGE_BYTES = open(POS, 'rb').read()

# One mixed basket plus one furniture-only sale. `total` is always the whole
# receipt, exactly as /api/transactions returns it.
MIXED = {
    'id': 1, 'transaction_number': 'T1', 'user_id': 7, 'cashier': 'Mrs G Admin',
    'subtotal': 300.0, 'tax': 0.0, 'total': 300.0, 'payment_method': 'cash',
    'amount_paid': 300.0, 'change_amount': 0.0, 'status': 'completed',
    'branch_name': 'Shurugwi',
    'items': [
        {'product_id': 10, 'product_name': 'Cement', 'quantity': 1, 'price': 100.0,
         'subtotal': 100.0, 'buy_price': 60.0, 'cost_at_time': 60.0, 'category': 'DIY'},
        {'product_id': 20, 'product_name': 'Chair', 'quantity': 2, 'price': 100.0,
         'subtotal': 200.0, 'buy_price': 50.0, 'cost_at_time': 50.0, 'category': 'Furniture'},
    ],
}
FURN = {
    'id': 2, 'transaction_number': 'T2', 'user_id': 7, 'cashier': 'Mrs G Admin',
    'subtotal': 990.75, 'tax': 0.0, 'total': 990.75, 'payment_method': 'cash',
    'amount_paid': 990.75, 'change_amount': 0.0, 'status': 'completed',
    'branch_name': 'Shurugwi',
    'items': [
        {'product_id': 21, 'product_name': 'Desk', 'quantity': 3, 'price': 330.25,
         'subtotal': 990.75, 'buy_price': 200.0, 'cost_at_time': 200.0, 'category': 'Furniture'},
    ],
}
# A layby deposit: money in the till, not a sale.
LAYB = {
    'id': 3, 'transaction_number': 'T3', 'user_id': 7, 'cashier': 'Mrs G Admin',
    'subtotal': 40.0, 'tax': 0.0, 'total': 40.0, 'payment_method': 'layby',
    'amount_paid': 40.0, 'change_amount': 0.0, 'status': 'layby',
    'branch_name': 'Shurugwi',
    'items': [
        {'product_id': 10, 'product_name': 'Cement', 'quantity': 1, 'price': 40.0,
         'subtotal': 40.0, 'buy_price': 30.0, 'cost_at_time': 30.0, 'category': 'DIY'},
    ],
}

NOW = _dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
for row in (MIXED, FURN, LAYB):
    row['created_at'] = NOW

STATE = {'dept': 'all'}


def transactions_for(dept):
    """Mirror /api/transactions: only in-scope lines, only receipts that have one."""
    out = []
    for row in (MIXED, FURN, LAYB):
        lines = [i for i in row['items']
                 if dept == 'all' or ('furniture' if i['category'] == 'Furniture' else 'hardware') == dept]
        if not lines:
            continue
        clone = dict(row)
        clone['items'] = lines
        out.append(clone)
    return out


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

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        dept = STATE['dept']
        if path in ('/', '/pos-system.html'):
            return self._page()
        if path == '/api/check-auth':
            return self._json({'authenticated': True, 'needs_branch': False,
                               'branch': {'id': 1, 'name': 'Shurugwi',
                                          'read_only': False, 'is_dispatch': False},
                               'user': {'id': 7, 'name': 'Mrs G Admin', 'role': 'admin'},
                               'department': {'key': dept}})
        if path == '/api/transactions':
            return self._json({'success': True, 'transactions': transactions_for(dept)})
        if path == '/api/dashboard/stats':
            return self._json({'success': True, 'stats': {
                'today_sales': 0, 'items_sold': 0, 'low_stock_count': 0,
                'total_products': 0, 'total_profit': 0}})
        if path.startswith('/api/'):
            return self._json({'success': True, 'products': [], 'transactions': [],
                               'additions': [], 'categories': [], 'laybys': []})
        return super().do_GET()

    def do_POST(self):
        path = urllib.parse.urlsplit(self.path).path
        length = int(self.headers.get('Content-Length') or 0)
        try:
            payload = _json.loads(self.rfile.read(length) or b'{}')
        except Exception:                                                 # noqa: BLE001
            payload = {}
        if path == '/api/pos/switch-department':
            STATE['dept'] = payload.get('department') or 'all'
            return self._json({'success': True, 'department': STATE['dept'],
                               'label': STATE['dept'].title()})
        return self._json({'success': True})


srv = None
try:
    srv = ThreadingHTTPServer(('127.0.0.1', 8802), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    check('a stand-in POS server is up', True, 'http://127.0.0.1:8802/pos-system.html')
except Exception as exc:                                                  # noqa: BLE001
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

            page.goto('http://127.0.0.1:8802/pos-system.html',
                      wait_until='domcontentloaded', timeout=30000)
            page.wait_for_function("typeof window.navigateTo === 'function'", timeout=25000)

            # The report period defaults to today in the app's own markup.
            page.evaluate("""() => {
                const p = document.getElementById('reportPeriod');
                if (p) p.value = 'today';
            }""")

            def read_after(dept):
                if dept != STATE['dept']:
                    page.evaluate("d => window.switchDepartment(d)", dept)
                    page.wait_for_timeout(900)
                else:
                    page.evaluate("() => window.switchDepartment('all')")
                    page.wait_for_timeout(900)
                page.evaluate("() => window.navigateTo('sales')")
                page.wait_for_timeout(1800)
                return page.evaluate("""() => {
                    const t = id => {
                        const el = document.getElementById(id);
                        return el ? el.textContent.replace(/\\s+/g, ' ').trim() : 'MISSING:' + id;
                    };
                    return {sales: t('reportTotalSales'), items: t('reportItemsSold'),
                            profit: t('reportGrossProfit'), tx: t('reportTransactionCount')};
                }""")

            page.evaluate("() => window.navigateTo('sales')")
            page.wait_for_timeout(1800)
            all_view = page.evaluate("""() => {
                const t = id => {
                    const el = document.getElementById(id);
                    return el ? el.textContent.replace(/\\s+/g, ' ').trim() : 'MISSING:' + id;
                };
                return {sales: t('reportTotalSales'), items: t('reportItemsSold'),
                        profit: t('reportGrossProfit'), tx: t('reportTransactionCount')};
            }""")
            check('All view: the tab reports the whole shop (mixed basket once)',
                  all_view == {'sales': 'USD 1,290.75', 'items': '6',
                               'profit': 'USD 530.75', 'tx': '2'},
                  all_view)

            hw = read_after('hardware')
            check('Hardware view: only the Hardware lines of the mixed basket count',
                  hw == {'sales': 'USD 100.00', 'items': '1',
                         'profit': 'USD 40.00', 'tx': '1'},
                  hw)

            fur = read_after('furniture')
            check('Furniture view: its own lines, and the furniture-only sale',
                  fur == {'sales': 'USD 1,190.75', 'items': '5',
                          'profit': 'USD 490.75', 'tx': '2'},
                  fur)

            check('the layby deposit never reaches the sales report',
                  '40' not in all_view['sales'].replace('1,290.75', ''), all_view['sales'])
            check('no page script error was thrown', not errors, errors[:3] or 'clean')
            browser.close()
    except Exception as exc:                                              # noqa: BLE001
        check('the browser run completed', False, '%s: %s' % (type(exc).__name__, str(exc)[:300]))
    finally:
        try:
            srv.shutdown()
        except Exception:                                                 # noqa: BLE001
            pass

failures = [r for r in RESULTS if r.startswith('FAIL')]
print('\n%d checks, %d failed' % (len(RESULTS), len(failures)))
sys.exit(1 if failures else 0)
