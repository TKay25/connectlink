"""Real-browser proof of the POS freshness fix (templates/pos-system.html).

The complaint: a till showed 26 while the branch really held 8, so "remove 23"
was refused by the server. The screen was showing this device's SAVED COPY, and
the page said nothing about it -- and the "live" probe made things worse by
answering out of that same copy.

This starts a throw-away HTTP server that serves the REAL page and shape-correct
stand-ins for the POS API, then drives a real Chromium (Playwright) against it:

  1. a legacy per-product probe entry is pruned out of the saved copy on load,
  2. a probe is never answered out of the saved copy, even when one is present,
  3. a replayed catalogue is MARKED as a saved copy (headers), so the page and
     any stock action can tell it from the server's answer,
  4. a catalogue load that cannot reach the server turns the warning banner on
     and the Inventory header says the figures are NOT confirmed,
  5. a live load turns the banner off and shows the SERVER's figure (8), not the
     saved 26,
  6. opening Subtract on an unconfirmed figure says so, and does NOT block the
     removal locally: the request reaches the server, which answers with its own
     live figure,
  7. opening the Inventory page asks the server again,
  8. a barcode lookup still resolves with no answer from the server, and the
     server's answer wins whenever it can be reached,
  9. the confirmation dialog -- the last screen before money is taken -- says the
     stock behind the order is not the server's own, and goes quiet again once
     the server has answered,
 10. a till that has been LOGGED OUT with sales still on it says how many are
     waiting and that one login files them -- instead of passing a bare session
     error through, which reads as if the money were lost -- keeps the sale, burns
     no retry on it, and hands it over for filing after a login that works.

Not part of the app: delete this file whenever.
Run:  python _pos_freshness_browser.py   (writes _check_pos_browser_out.txt)
"""
import json
import os
import pathlib
import re
import threading
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = pathlib.Path(__file__).parent
PORT = int(os.environ.get('POS_TEST_PORT', '8792'))
TEMPLATE = ROOT / 'templates' / 'pos-system.html'
OUT = '_check_pos_browser_out.txt'

RESULTS = []


def check(name, ok, detail=''):
    RESULTS.append(f"{'PASS' if ok else 'FAIL'}  {name}"
                   f"{('  -> ' + detail) if detail else ''}")
    try:
        with open(OUT, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(RESULTS) + '\n')
    except Exception:                                              # noqa: BLE001
        pass


# The branch figure the SERVER holds (what the refusal quotes), and the stale
# figure a given device's saved copy still claims.
SERVER_STOCK = 8
SAVED_STOCK = 26

PRODUCT = {
    'id': 7, 'name': 'Speaker X', 'category': 'Audio', 'unit_type': 'piece',
    'unit_details': '10W', 'buy_price': 10.0, 'sell_price': 15.0,
    'stock': SERVER_STOCK, 'min_stock_level': 5, 'description': '',
    'barcode': '12345', 'created_at': None, 'updated_at': None,
    'total_stock': SERVER_STOCK, 'branch_sell_price': 15.0,
    'stock_value': 80.0, 'stocked_here': True, 'low_stock': False,
}
SAVED_PRODUCT = dict(PRODUCT, stock=SAVED_STOCK, total_stock=SAVED_STOCK,
                     stock_value=10.0 * SAVED_STOCK)

BRANCH = {'id': 1, 'code': 'SHU', 'name': 'Shurugwi', 'read_only': False}
LOG = []
# What the till actually SENT to /api/transactions/sync: a session refusal must be
# shown to have asked the server for the truth, rather than to have dropped the sale.
SYNC_POSTS = []


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
        if self.command != 'HEAD':
            self.wfile.write(body)

    def _page(self):
        body = TEMPLATE.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        LOG.append(('GET', path))
        if path == '/__log':
            return self._json(LOG)
        if path == '/__clear':
            del LOG[:]
            return self._json({'ok': True})
        if path in ('/', '/pos-system.html', '/pos-system'):
            return self._page()
        if path == '/api/check-auth':
            return self._json({'authenticated': True, 'branch': BRANCH,
                               'needs_branch': False,
                               'user': {'id': 1, 'name': 'Administrator',
                                        'role': 'admin'}})
        if path == '/api/products':
            return self._json({'success': True, 'products': [PRODUCT],
                               'total': 1})
        if path == '/api/products/7':
            return self._json({'success': True, 'product': PRODUCT})
        if path.startswith('/api/products/by-barcode/'):
            code = path.rsplit('/', 1)[-1]
            if code == PRODUCT['barcode']:
                return self._json({'success': True, 'product': PRODUCT})
            return self._json({'success': True})          # the server does not know it
        if path == '/api/categories':
            return self._json({'success': True, 'categories': [
                {'id': 1, 'name': 'Audio'}]})
        if path == '/api/branches':
            return self._json({'success': True, 'branches': [BRANCH],
                               'all_branches': {'id': 0, 'name': 'All Branches'}})
        if path == '/api/dashboard-stats':
            return self._json({'success': True, 'today_sales': 0.0,
                               'items_sold': 0, 'low_stock_count': 0,
                               'total_products': 1, 'total_profit': 0.0})
        if path == '/api/laybys':
            return self._json({'success': True, 'laybys': []})
        if path.startswith('/api/transactions'):
            return self._json({'success': True, 'transactions': [],
                               'todaySales': 0.0, 'itemsSold': 0})
        if path.startswith('/api/'):
            return self._json({'success': True})
        return super().do_GET()          # /static/... straight off the disk

    def do_PUT(self):
        path = urllib.parse.urlsplit(self.path).path
        length = int(self.headers.get('Content-Length') or 0)
        raw = self.rfile.read(length) if length else b''
        body = json.loads(raw or b'{}')
        LOG.append(('PUT', path))
        if path == '/api/products/7/subtract-stock':
            want = int(body.get('quantity') or 0)
            if want > SERVER_STOCK:
                # The real route's refusal: the live figure, its shop and the
                # `stale` flag that makes the till refresh.
                return self._json({
                    'error': ("Shurugwi has %d unit(s) of \"Speaker X\" right now, so %d "
                              "cannot be removed. The figure on your screen was out of "
                              "date; it has been refreshed." % (SERVER_STOCK, want)),
                    'available': SERVER_STOCK, 'total_stock': SERVER_STOCK,
                    'branch_name': 'Shurugwi', 'stale': True}, 400)
            return self._json({'success': True, 'new_stock': SERVER_STOCK - want})
        return self._json({'success': True})

    def do_POST(self):
        path = urllib.parse.urlsplit(self.path).path
        length = int(self.headers.get('Content-Length') or 0)
        body = json.loads(self.rfile.read(length) or b'{}') if length else {}
        LOG.append(('POST', path))
        if path == '/api/transactions/sync':
            SYNC_POSTS.append(body)
            if ctl['sync'] == 'session':
                # The real @login_required answer: the till has no session, so
                # nothing can be filed -- and the sales stay the till's problem.
                return self._json({'error': 'Session not found. Log in again to continue.',
                                   'session_expired': True}, 401)
            if ctl['sync'] == 'readonly':
                return self._json({'error': 'The All Branches view is read-only.'}, 403)
            sales = body.get('sales') or []
            return self._json({'success': True, 'synced': len(sales), 'duplicate': 0,
                               'failed': 0, 'branch_mismatch': 0, 'oversold': 0,
                               'results': [{'client_ref': s.get('client_ref'),
                                            'status': 'synced'} for s in sales]})
        return self._json({'success': True})


def serve():
    httpd = ThreadingHTTPServer(('127.0.0.1', PORT), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


from playwright.sync_api import sync_playwright                      # noqa: E402

BASE = 'http://127.0.0.1:%d' % PORT

# Seeded before any page script runs: a till whose SAVED COPY says 26 while the
# server holds 8 -- the exact state the complaint describes -- including the
# per-product probe entry an older build would have saved.
SEED = """(function () {
  try {
    var origin = window.location.origin;
    localStorage.clear();
    localStorage.setItem('isLoggedIn', 'true');
    localStorage.setItem('posBranch', JSON.stringify({id: 1, name: 'Shurugwi', read_only: false}));
    localStorage.setItem('pos_branch_scope', '1');
    var stale = Date.now() - 3600 * 1000;
    var store = {};
    store[origin + '/api/products'] = {at: stale, branch: '1',
        data: {success: true, products: [%(p)s]}};
    store[origin + '/api/products/7'] = {at: stale, branch: '1',
        data: {success: true, product: %(p)s}};
    localStorage.setItem('pos_api_cache_v1', JSON.stringify(store));
  } catch (e) {}
})();""" % {'p': json.dumps(SAVED_PRODUCT)}

# Enough of Bootstrap's modal API for the boxes to open without the CDN (the CDN
# copy, if it loads, simply replaces this).
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

ctl = {'catalogue': 'abort', 'probe': 'abort', 'barcode': 'live', 'sync': 'live'}

# Put the till back in the complaint's exact position: the copy it holds says 26.
SEED_STALE_COPY = """() => {
    var origin = window.location.origin;
    var store = JSON.parse(localStorage.getItem('pos_api_cache_v1') || '{}');
    store[origin + '/api/products'] = {at: Date.now() - 3600 * 1000, branch: '1',
        data: {success: true, products: [%(p)s]}};
    localStorage.setItem('pos_api_cache_v1', JSON.stringify(store));
}""" % {'p': json.dumps(SAVED_PRODUCT)}


CATALOGUE_HITS = []


def route_catalogue(route):
    # Count EVERY catalogue attempt, including the ones answered here rather than by
    # the stub server (a 500, an abort): those never appear in the server's log, and
    # "was the load retried?" is exactly what step 4c has to answer.
    CATALOGUE_HITS.append(ctl['catalogue'])
    if ctl['catalogue'] == 'abort':
        route.abort()
    elif ctl['catalogue'] == '500':
        route.fulfill(status=500, content_type='application/json',
                      body='{"error": "boom"}')
    else:
        route.continue_()


def route_probe(route):
    if ctl['probe'] == 'abort':
        route.abort()
    elif ctl['probe'] == '500':
        route.fulfill(status=500, content_type='application/json',
                      body='{"error": "boom"}')
    else:
        route.continue_()


def route_barcode(route):
    if ctl['barcode'] == 'abort':
        route.abort()
    else:
        route.continue_()


def log_from_server():
    """The request log, read straight out of this process.

    Deliberately NOT over HTTP: the sandbox lets the browser reach the stub
    server but refuses an outbound socket from Python itself, so the log is read
    from the list the handler appends to.
    """
    return [tuple(e) for e in LOG if not e[1].startswith('/__')]


def clear_log():
    del LOG[:]


def reset_catalogue_hits():
    del CATALOGUE_HITS[:]


httpd = serve()
check('the throw-away POS server is up', True, BASE)

try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context()
        ctx.add_init_script(BOOTSTRAP_STUB)
        ctx.add_init_script(SEED)
        page = ctx.new_page()
        page.set_default_timeout(15000)
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)[:160]))
        # No external network: the page's CDN libraries are irrelevant here (the
        # modal API it needs is stubbed) and reaching for them would only make the
        # run slow and flaky.
        page.route(re.compile(r'https?://(?!127\.0\.0\.1)'), lambda r: r.abort())
        page.route('**/api/products', route_catalogue)
        page.route('**/api/products/by-barcode/*', route_barcode)
        page.route('**/api/products/7', route_probe)

        page.goto(BASE + '/pos-system.html', wait_until='domcontentloaded',
                  timeout=30000)
        page.wait_for_function(
            "typeof showSubtractStockModal === 'function'"
            " && typeof window.refreshCatalogueIfStale === 'function'", timeout=20000)
        check('the page loads with the offline wrapper installed', True)

        # 1. the legacy probe entry is gone from the saved copy
        keys = page.evaluate(
            "Object.keys(JSON.parse(localStorage.getItem('pos_api_cache_v1') || '{}'))")
        check('a saved per-product probe is pruned away on load',
              bool(keys) and not any('/api/products/' in k for k in keys), str(keys))

        # 2. a probe is never answered out of the saved copy, even when present
        page.evaluate("""() => {
            var origin = window.location.origin;
            var store = JSON.parse(localStorage.getItem('pos_api_cache_v1') || '{}');
            store[origin + '/api/products/7'] = {at: Date.now() - 60000, branch: '1',
                data: {success: true, product: {id: 7, stock: 26}}};
            localStorage.setItem('pos_api_cache_v1', JSON.stringify(store));
        }""")
        ctl['probe'] = 'abort'
        probe = page.evaluate("""async () => {
            try {
                const r = await window.fetch(window.location.origin + '/api/products/7');
                const d = await r.json();
                return {answered: true, saved: r.headers.get('X-ConnectLink-Saved-Copy'),
                        stock: (d.product || {}).stock};
            } catch (e) { return {answered: false, error: String(e)}; }
        }""")
        check('the live probe is NOT answered from the saved copy',
              probe.get('answered') is False, json.dumps(probe))

        # 3. a replayed catalogue is marked as a saved copy
        ctl['catalogue'] = 'abort'
        replay = page.evaluate("""async () => {
            const r = await window.fetch(window.location.origin + '/api/products');
            const d = await r.json();
            return {saved: r.headers.get('X-ConnectLink-Saved-Copy'),
                    at: r.headers.get('X-ConnectLink-Saved-At'),
                    seen: savedCopyAt(r), stock: d.products[0].stock};
        }""")
        check("a replayed catalogue is tagged as the device's own copy",
              replay.get('saved') == '1' and replay.get('seen', 0) > 0
              and replay.get('stock') == SAVED_STOCK, json.dumps(replay))
        check("the server's own answer is never tagged",
              page.evaluate("""async () => {
                  const r = await window.fetch(window.location.origin + '/api/categories');
                  return savedCopyAt(r);
              }""") == 0)

        # 4. a load that cannot reach the server says the figures are not live
        stale = page.evaluate("""async () => {
            await fetchProductsFromAPI();
            return {banner: document.getElementById('posStaleDataBanner').style.display,
                    text: document.getElementById('posStaleDataText').innerText,
                    asAt: document.getElementById('inventoryAsAt').innerText,
                    shown: (products.find(p => p.id === 7) || {}).stock};
        }""")
        check('an unreachable catalogue turns the warning banner on',
              stale['banner'] == 'flex', json.dumps(stale))
        check('the banner names the saved copy and its age',
              'saved on this device' in stale['text']
              and 'copy saved at' in stale['text'], stale['text'][:130])
        check('the Inventory header says the figures are NOT confirmed',
              'NOT confirmed' in stale['asAt'], stale['asAt'])
        check("the screen shows the saved figure (26), not the server's (8)",
              stale['shown'] == SAVED_STOCK, str(stale['shown']))

        # 4b. a 500 (or any non-OK answer) is reported too, not swallowed
        ctl['catalogue'] = '500'
        boom = page.evaluate("""async () => {
            await fetchProductsFromAPI();
            return {banner: document.getElementById('posStaleDataBanner').style.display,
                    text: document.getElementById('posStaleDataText').innerText,
                    asAt: document.getElementById('inventoryAsAt').innerText,
                    toasts: Array.from(document.querySelectorAll('.toast-notify'))
                                  .map(t => t.innerText).join(' | ')};
        }""")
        check('a non-OK catalogue answer also turns the banner on',
              boom['banner'] == 'flex' and 'NOT confirmed' in boom['asAt'],
              json.dumps(boom)[:200])
        check('and it says why (HTTP 500), instead of silently keeping old numbers',
              'HTTP 500' in boom['toasts'], boom['toasts'][:160])
        check('the banner says the figures are not confirmed, without blaming the link',
              'not confirmed by the server' in boom['text'].lower()
              and 'could not be reached' not in boom['text'], boom['text'][:140])

        # 4c. the slow sweep retries a refused load, but never polls a live till
        ctl['catalogue'] = '500'
        reset_catalogue_hits()
        page.evaluate("""async () => { await fetchProductsFromAPI();
                                      window.refreshCatalogueIfStale(false); }""")
        page.wait_for_timeout(600)
        check('a refused load is retried (it would otherwise stay stale all session)',
              len(CATALOGUE_HITS) >= 2,
              'GET /api/products attempted %d time(s)' % len(CATALOGUE_HITS))
        ctl['catalogue'] = 'live'
        reset_catalogue_hits()
        clear_log()
        page.evaluate("""async () => { await fetchProductsFromAPI();
                                      window.refreshCatalogueIfStale(false); }""")
        page.wait_for_timeout(600)
        check('a healthy till is not polled (no pointless catalogue traffic)',
              len(CATALOGUE_HITS) == 1
              and [m for m in log_from_server() if m == ('GET', '/api/products')]
                  == [('GET', '/api/products')],
              'attempts=%d, server=%s' % (len(CATALOGUE_HITS),
                                          str(log_from_server()[-3:])))

        # 5. a live load replaces it with the server's figure
        ctl['catalogue'] = 'live'
        live = page.evaluate("""async () => {
            await fetchProductsFromAPI();
            return {banner: document.getElementById('posStaleDataBanner').style.display,
                    asAt: document.getElementById('inventoryAsAt').innerText,
                    shown: (products.find(p => p.id === 7) || {}).stock};
        }""")
        check("a live load hides the banner and shows the server's 8",
              live['banner'] == 'none' and live['shown'] == SERVER_STOCK,
              json.dumps(live))
        check('the Inventory header says when the server confirmed them',
              'confirmed by the server at' in live['asAt'], live['asAt'])
        check('the inventory table shows that figure',
              'Speaker X' in page.inner_text('#inventoryList'))

        # 6. Subtract on a figure this till cannot confirm
        ctl['catalogue'] = 'abort'      # the screen can only show the device's copy
        ctl['probe'] = 'abort'          # ... and the probe cannot reach the server either
        page.evaluate(SEED_STALE_COPY)  # the copy in hand says 26, the server holds 8
        clear_log()
        page.evaluate("fetchProductsFromAPI()")
        page.wait_for_timeout(500)
        sub = page.evaluate("""async () => {
            const shown = (products.find(p => p.id === 7) || {}).stock;
            await showSubtractStockModal(7, shown);
            const fresh = document.getElementById('subtractStockFreshness');
            return {shown: document.getElementById('subtractCurrentStockValue').innerText,
                    tableShown: shown,
                    freshVisible: fresh.style.display !== 'none',
                    freshText: document.getElementById('subtractStockFreshnessText').innerText};
        }""")
        check('the Subtract box shows the saved figure it holds (26)',
              sub['shown'] == str(SAVED_STOCK) and sub['tableShown'] == SAVED_STOCK,
              json.dumps(sub))
        check('and says plainly that the figure is not live',
              sub['freshVisible'] and 'not live' in sub['freshText'],
              sub['freshText'][:130])

        # 30 > the 26 on screen, so the OLD local check would have refused this
        # before it ever left the till. It must now reach the server, which answers
        # with the figure it really holds.
        page.evaluate("document.getElementById('subtractQuantity').value = '30'")
        page.evaluate("confirmSubtractStock()")
        page.wait_for_timeout(1200)
        check('the removal is still sent to the server (no local refusal on a stale figure)',
              ('PUT', '/api/products/7/subtract-stock') in log_from_server(),
              str(log_from_server()[-4:]))
        toasts = page.evaluate(
            "Array.from(document.querySelectorAll('.toast-notify')).map(t => t.innerText).join(' | ')")
        check("the server's own refusal (with its live figure) is shown",
              'Shurugwi has %d unit(s)' % SERVER_STOCK in toasts, toasts[:170])
        check('and the box is closed so the stale number cannot be tried again',
              page.evaluate(
                  "document.getElementById('subtractStockModal').classList.contains('show')")
              is False)

        # 7. opening the Inventory page asks the server again
        ctl['catalogue'] = 'live'
        ctl['probe'] = 'live'
        clear_log()
        page.evaluate("navigateTo('inventory')")
        page.wait_for_timeout(900)
        hits = log_from_server()
        check('opening the Inventory page re-reads the catalogue from the server',
              ('GET', '/api/products') in hits, str(hits[-4:]))

        # 8. a barcode scan still works with no answer from the server
        ctl['barcode'] = 'abort'
        scan = page.evaluate("""async () => {
            const hit = await lookupProductByBarcode('12345');
            const miss = await lookupProductByBarcode('99999');
            return {hit: hit && hit.id, miss: miss && miss.id};
        }""")
        check('an offline scan resolves from the list already on the till',
              scan['hit'] == 7, json.dumps(scan))
        check('an unknown barcode is still unknown, so Quick-create is still offered',
              scan['miss'] is None, json.dumps(scan))

        ctl['barcode'] = 'live'
        scan2 = page.evaluate("""async () => {
            const hit = await lookupProductByBarcode('12345');
            const miss = await lookupProductByBarcode('99999');
            return {hit: hit && hit.id, miss: miss && miss.id};
        }""")
        check('with the server reachable it is the server\'s answer that counts',
              scan2['hit'] == 7 and scan2['miss'] is None, json.dumps(scan2))

        # 9. the confirmation dialog -- the last screen before money is taken --
        # discloses it too. A sale rung on an unconfirmed figure is exactly the
        # sale that can oversell, so the warning cannot live only on the banner.
        ctl['catalogue'] = 'abort'
        page.evaluate("fetchProductsFromAPI()")
        page.wait_for_timeout(500)
        chk = page.evaluate("""() => {
            cart = [{id: 7, name: 'Speaker X', quantity: 1, sell_price: 15, price: 15,
                     category: 'Audio', unit_type: 'piece', unit_details: '10W'}];
            selectedPaymentMethod = 'cash';
            document.getElementById('cashAmount').value = '20';
            updateCartDisplay();
            showPaymentConfirmation();
            const el = document.getElementById('posCheckoutStaleNote');
            return {shown: el.style.display !== 'none',
                    text: document.getElementById('posCheckoutStaleText').innerText};
        }""")
        check('the confirmation dialog warns that the stock behind it is unconfirmed',
              chk['shown'] and 'not confirmed by the server' in chk['text'].lower(),
              chk['text'][:160])
        check('and says the sale is still taken, so it is a warning and not a refusal',
              'still taken' in chk['text'], chk['text'][:160])

        # ...and it goes quiet again the moment the server's own figures are back.
        ctl['catalogue'] = 'live'
        page.evaluate("fetchProductsFromAPI()")
        page.wait_for_timeout(500)
        page.evaluate("showPaymentConfirmation()")
        check('a till showing the server\'s own figures shows no such warning',
              page.evaluate(
                  "document.getElementById('posCheckoutStaleNote').style.display") == 'none')

        # 10. a till that has been LOGGED OUT with sales still on it. The sales are
        # safe on the device; what they need is one login, and the till has to say
        # that in those words -- a bare "session not found" read on a busy counter
        # sounds as if the money were gone, which is how a shop ends up hunting for
        # a fault that does not exist.
        ctl['sync'] = 'session'
        clear_log()
        page.evaluate("""() => {
            window.POSOffline.queueSale({
                items: [{id: 7, name: 'Speaker X', price: 15, quantity: 1}],
                payment_method: 'cash', amount_paid: 15, change_amount: 0,
                subtotal: 15, total: 15});
            Array.from(document.querySelectorAll('.toast-notify')).forEach(t => t.remove());
        }""")
        page.wait_for_timeout(120)
        page.evaluate("() => window.POSOffline.syncNow()")
        page.wait_for_timeout(1500)
        dead = page.evaluate("""() => {
            const q = JSON.parse(localStorage.getItem('pos_offline_sales_v1') || '[]');
            return {toasts: Array.from(document.querySelectorAll('.toast-notify'))
                              .map(t => t.innerText).join(' | '),
                    queued: q.length,
                    attempts: q.length ? (q[0].attempts || 0) : -1};
        }""")
        check('a logged-out till says how many sales are waiting on it',
              '1 sale' in dead['toasts'] and 'log in once' in dead['toasts'],
              dead['toasts'][:180])
        check('and does not pass the raw session error through as a failure',
              'Session not found' not in dead['toasts']
              and 'Log in again to continue' not in dead['toasts'],
              dead['toasts'][:180])
        check('the sale is kept on the till, and no retry is burned on a dead session',
              dead['queued'] == 1 and dead['attempts'] == 0,
              'queued=%d attempts=%s' % (dead['queued'], dead['attempts']))
        check('the batch really was offered to the server before being refused',
              len(SYNC_POSTS) == 1 and len(SYNC_POSTS[0].get('sales') or []) == 1,
              json.dumps(SYNC_POSTS)[:180])

        # ...and one login files it: the till has to prove that, not merely claim it.
        ctl['sync'] = 'live'
        page.evaluate("""() => {
            Array.from(document.querySelectorAll('.toast-notify')).forEach(t => t.remove());
            return window.POSOffline.syncNow();
        }""")
        page.wait_for_timeout(1800)
        filed = page.evaluate("""() => ({
            toasts: Array.from(document.querySelectorAll('.toast-notify'))
                          .map(t => t.innerText).join(' | '),
            queued: JSON.parse(localStorage.getItem('pos_offline_sales_v1') || '[]').length})""")
        check('after ONE login the sale the till was holding files itself',
              filed['queued'] == 0 and 'Synced 1 offline sale(s)' in filed['toasts'],
              json.dumps(filed)[:180])

        # A refusal that is NOT about the session must still reach the operator in
        # the server's own words: the session wording is an addition, not a cover-up.
        ctl['sync'] = 'readonly'
        page.evaluate("""() => {
            window.POSOffline.queueSale({
                items: [{id: 7, name: 'Speaker X', price: 15, quantity: 1}],
                payment_method: 'cash', amount_paid: 15, change_amount: 0,
                subtotal: 15, total: 15});
            Array.from(document.querySelectorAll('.toast-notify')).forEach(t => t.remove());
        }""")
        page.wait_for_timeout(120)
        page.evaluate("() => window.POSOffline.syncNow()")
        page.wait_for_timeout(1500)
        check("any other refusal still shows the server's own words",
              'read-only' in page.evaluate(
                  "Array.from(document.querySelectorAll('.toast-notify'))"
                  ".map(t => t.innerText).join(' | ')"),
              page.evaluate(
                  "Array.from(document.querySelectorAll('.toast-notify'))"
                  ".map(t => t.innerText).join(' | ')")[:180])

        # Leave nothing behind for the next run of this page.
        page.evaluate("() => localStorage.removeItem('pos_offline_sales_v1')")
        ctl['sync'] = 'live'

        browser.close()
except Exception as exc:                                           # noqa: BLE001
    import traceback
    check('the browser run completed', False,
          '%s: %s' % (type(exc).__name__, exc))
    RESULTS.append(traceback.format_exc(limit=3))
    try:
        RESULTS.append('page errors: ' + ' | '.join(errors[:5]))
    except Exception:                                              # noqa: BLE001
        pass
finally:
    httpd.shutdown()

out = '\n'.join(RESULTS)
try:
    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write(out + '\n')
except Exception:                                                  # noqa: BLE001
    pass
print(out)
print('\nFAILURES: %d' % sum(1 for r in RESULTS if r.startswith('FAIL')))



