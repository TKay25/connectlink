"""Real-browser proof of the portal's READ-ONLY offline copy.

The POS works with no connection because it QUEUES its sales and its laybys. The
portal cannot -- an edit there is a whole-row update the server judges -- so what
it got is a copy of a small, named set of read-only figures plus any contract the
operator has kept, each stamped with when it was saved.

The portal page is a Jinja template, so it cannot be served as it stands. This
therefore serves the REAL static/js/sw.js and a stand-in page assembled from the
REAL page's own offline code: the banner element, the offline module, the
contract helpers, the fetch wrapper and handleLogout are sliced verbatim out of
templates/adminpage.html, so the code running here is the code that ships (only
showToast, closeUserDropdown and showLoader -- which live elsewhere in that
2MB page -- are stubbed, the first one recording what it was told).

It then drives a real Chromium (Playwright) against a throw-away server:

  1. with a connection, a figure is the server's own answer (no stamp), and the
     page claims nothing about saved copies,
  2. only the named endpoints are kept: a money endpoint (project-overcosts) and
     the portfolio export are never replayed offline,
  3. with no connection, a kept figure is replayed MARKED as a copy, carrying the
     time it was saved, and the page says so -- with that time -- in the banner,
  4. an endpoint with no saved copy is refused (503 offline_no_copy) rather than
     answered with a stale figure, and the banner says there is no copy,
  5. a change (POST) with no connection is never queued and never looks saved:
     the page says plainly that nothing was saved and nothing was sent,
  6. a contract that has been through once still opens with no connection, byte
     for byte, marked as the device's copy, and the page says the server has no
     record of that download,
  7. a contract that was never fetched is refused with instructions,
  8. "Save for offline" keeps a copy while online, and with no connection and no
     copy it fails loudly instead of pretending,
  9. Delete saved copies really removes them, and logging out takes them with it,
 10. and the connection coming back puts the server's own figures back.

Not part of the app: delete this file whenever.
Run:  python _portal_offline_browser.py   (writes _check_portal_browser_out.txt)
"""
import json
import os
import pathlib
import re
import threading
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = pathlib.Path(__file__).parent
PORT = int(os.environ.get('PORTAL_TEST_PORT', '8793'))
PAGE_FILE = ROOT / 'templates' / 'adminpage.html'
SW_FILE = ROOT / 'static' / 'js' / 'sw.js'
OUT = '_check_portal_browser_out.txt'
BASE = 'http://127.0.0.1:%d' % PORT

RESULTS = []
LOG = []              # every request the stub server saw, in order


def check(name, ok, detail=''):
    RESULTS.append(f"{'PASS' if ok else 'FAIL'}  {name}"
                   f"{('  -> ' + detail) if detail else ''}")
    try:
        with open(OUT, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(RESULTS) + '\n')
    except Exception:                                              # noqa: BLE001
        pass


def extract(src, marker):
    """The text from marker to the brace that balances its opening brace."""
    body = src[src.index(marker):]
    depth = 0
    started = False
    for n, ch in enumerate(body):
        if ch == '{':
            depth += 1
            started = True
        elif ch == '}':
            depth -= 1
            if started and depth == 0:
                return body[:n + 1]
    return body


# ---- the real code under test, sliced verbatim out of the real page --------
REAL = PAGE_FILE.read_text(encoding='utf-8')
_START = REAL.index('// ===== READ-ONLY OFFLINE SUPPORT =====')
_END = REAL.index('})();', REAL.index('window.fetch = function(){', _START)) + len('})();')
OFFLINE_CODE = REAL[_START:_END]
LOGOUT_CODE = extract(REAL, 'function handleLogout() {')
_BANNER = re.search(r'<div id="clOfflineBanner".*?</div>', REAL, re.S)
BANNER_HTML = _BANNER.group(0) if _BANNER else ''

HARNESS = """<!doctype html>
<html><head><meta charset="utf-8"><title>portal offline harness</title></head>
<body>
%s
<script>
// Stubs for three page helpers that live elsewhere in the real 2MB page. The
// offline code only ever calls showToast, and this one records what it was told
// so the test can read it back.
window.clToasts = [];
function showToast(message, type, title) {
    window.clToasts.push([type || '', title || '', message || ''].join(' | '));
}
function closeUserDropdown() {}
function showLoader() {}
function hideLoader() {}
</script>
<script>
%s
</script>
<script>
%s
</script>
<script>
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function () { navigator.serviceWorker.register('/sw.js'); });
}
</script>
</body></html>
""" % (BANNER_HTML, OFFLINE_CODE, LOGOUT_CODE)

PROJECT_PAGE = {'success': True, 'total': 1,
                'projects': [{'id': 7, 'client_name': 'Acme', 'name': 'Bridge'}]}
COUNT = {'count': 3, 'month': '2026-10'}
MONTHS = ['2026-10', '2026-09']
GANTT = {'has_gantt': True}
OVERCOSTS = {'success': True, 'total_overcost': 12345.67}
PROJECT = {'id': 7, 'name': 'Bridge'}
CONTRACT = b'%PDF-1.7\n' + (b'contract body ' * 300) + b'\ntrailer\n%%EOF\n'

LOGOUT_PAGE = """<!doctype html>
<html><body><script>
window.__docCaches = null;
(async () => {
    const names = await caches.keys();
    window.__docCaches = names.filter(n => n.indexOf('connectlink-docs-') === 0);
})();
</script></body></html>"""


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def log_message(self, *a):
        pass  # keep the console quiet

    def _send(self, body, ctype, code=200, extra=None):
        if not isinstance(body, bytes):
            body = body.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def _json(self, payload, code=200):
        self._send(json.dumps(payload), 'application/json', code)

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        LOG.append(('GET', self.path))
        if path in ('/', '/adminpage.html', '/admin'):
            return self._send(HARNESS, 'text/html; charset=utf-8')
        if path == '/logout':
            return self._send(LOGOUT_PAGE, 'text/html; charset=utf-8')
        if path == '/sw.js':
            return self._send(SW_FILE.read_bytes(), 'application/javascript')
        if path == '/get_project_count':
            return self._json(COUNT)
        if path in ('/get_project_months', '/get_project_start_months'):
            return self._json(MONTHS)
        if path == '/api/projects-page':
            return self._json(PROJECT_PAGE)
        if path == '/api/project-overcosts':
            return self._json(OVERCOSTS)
        if path == '/export-projects-portfolio':
            return self._send('id,client\n7,Acme\n', 'text/csv')
        if re.match(r'^/get_project/\d+$', path):
            return self._json(PROJECT)
        if re.match(r'^/api/project/\d+/has-gantt$', path):
            return self._json(GANTT)
        if re.match(r'^/download_contract/\d+$', path):
            return self._send(CONTRACT, 'application/pdf',
                              extra={'Content-Disposition':
                                     'attachment; filename="contract-%s.pdf"'
                                     % path.rsplit('/', 1)[1]})
        if path.startswith('/static/'):
            return super().do_GET()
        return self._json({'success': True})

    def do_POST(self):
        length = int(self.headers.get('Content-Length') or 0)
        if length:
            self.rfile.read(length)
        LOG.append(('POST', urllib.parse.urlsplit(self.path).path))
        return self._json({'success': True})


def serve():
    httpd = ThreadingHTTPServer(('127.0.0.1', PORT), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


# One fetch, reported in a shape the test can assert on: the status, the two
# stamps the worker adds, and the body (JSON, text, or just its size).
FETCH_JS = """
async (opts) => {
    const out = {ok: false, status: 0, headers: {}, body: null, error: null};
    try {
        const res = await fetch(opts.url, opts.init || {credentials: 'include'});
        out.ok = res.ok;
        out.status = res.status;
        out.headers = {
            offline: res.headers.get('X-ConnectLink-Offline'),
            savedAt: res.headers.get('X-ConnectLink-Saved-At'),
            disposition: res.headers.get('Content-Disposition'),
            type: res.headers.get('Content-Type')
        };
        if (opts.as === 'json') {
            try { out.body = await res.json(); } catch (e) { out.body = null; }
        } else if (opts.as === 'text') {
            out.body = await res.text();
        } else {
            out.body = (await res.blob()).size;
        }
    } catch (e) {
        out.error = String(e && (e.message || e));
    }
    return out;
}
"""

# What is actually on the device right now, straight out of Cache Storage.
AUDIT_JS = """
async () => {
    const names = await caches.keys();
    const out = {names: names, doc: 0, read: 0, money: [], contracts: []};
    for (const name of names) {
        const cache = await caches.open(name);
        const keys = await cache.keys();
        for (const key of keys) {
            if (name.indexOf('connectlink-docs-') === 0) out.doc++;
            if (name.indexOf('connectlink-read-') === 0) out.read++;
            if (key.url.indexOf('overcost') !== -1
                || key.url.indexOf('export-projects') !== -1) out.money.push(key.url);
            if (key.url.indexOf('/download_contract/') !== -1) out.contracts.push(key.url);
        }
    }
    return out;
}
"""


# --------------------------------------------------------------- the test
try:
    from playwright.sync_api import sync_playwright
except Exception as exc:                                           # noqa: BLE001
    check('the browser driver is installed', False,
          '%s: %s' % (type(exc).__name__, exc))
    print('\n'.join(RESULTS))
    print('\nFAILURES: %d' % sum(1 for r in RESULTS if r.startswith('FAIL')))
    raise SystemExit(1)

check('the code under test is the real page code, sliced verbatim',
      'function clOfflineMark(savedMs) {' in OFFLINE_CODE
      and 'window.fetch = function(){' in OFFLINE_CODE
      and 'function saveContractForOffline(btn) {' in OFFLINE_CODE
      and 'function clDeleteSavedCopies() {' in OFFLINE_CODE
      and BANNER_HTML.startswith('<div id="clOfflineBanner"')
      and 'clDeleteSavedCopies()' in LOGOUT_CODE)

httpd = serve()
check('the throw-away portal server is up', True, BASE)

try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context()
        page = ctx.new_page()
        page.set_default_timeout(20000)
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)[:200]))
        page.goto(BASE + '/adminpage.html', wait_until='domcontentloaded',
                  timeout=30000)
        state = page.evaluate("""async () => {
            if (!('serviceWorker' in navigator)) return 'no-sw';
            const reg = await navigator.serviceWorker.ready;
            for (let i = 0; i < 100; i++) {
                if (reg.active && reg.active.state === 'activated'
                    && navigator.serviceWorker.controller) return 'activated';
                await new Promise(r => setTimeout(r, 100));
            }
            return reg.active ? reg.active.state : 'none';
        }""")
        check('the real service worker takes charge of the page',
              state == 'activated', str(state))
        check('the banner starts hidden',
              page.evaluate("getComputedStyle(document.getElementById('clOfflineBanner')).display")
              == 'none')

        # ---- 1. with a connection: the server's own answers ---------------
        del LOG[:]
        live = page.evaluate(FETCH_JS, {'url': '/get_project_count?month=2026-10',
                                        'as': 'json'})
        check('with a connection a figure is the server own answer',
              live['ok'] and (live['body'] or {}).get('count') == 3, str(live)[:140])
        check('and no saved time is claimed for it',
              live['headers']['offline'] is None
              and live['headers']['savedAt'] is None, str(live['headers']))
        check('the banner stays quiet while the server is answering',
              page.evaluate("getComputedStyle(document.getElementById('clOfflineBanner')).display")
              == 'none')
        check('the server really was asked',
              ('GET', '/get_project_count?month=2026-10') in LOG, str(LOG[:3]))

        for path in ('/api/projects-page', '/get_project/7',
                     '/api/project/7/has-gantt', '/get_project_months'):
            page.evaluate(FETCH_JS, {'url': path, 'as': 'json'})
        first = page.evaluate(FETCH_JS, {'url': '/download_contract/7', 'as': 'blob'})
        check('a contract comes down from the server with its filename',
              first['ok']
              and (first['headers']['type'] or '').startswith('application/pdf')
              and 'contract-7.pdf' in (first['headers']['disposition'] or ''),
              str(first['headers']))

        audit = page.evaluate(AUDIT_JS)
        check('the named figures are now kept on the device',
              audit['read'] >= 4, str(audit['read']))
        check('a contract that has been through once is kept on the device',
              audit['doc'] == 1 and len(audit['contracts']) == 1, str(audit['contracts']))
        check('the buckets are the POS shell, the runtime one, the read one and the contract one',
              all(n in ('connectlink-v3', 'connectlink-runtime-v3',
                        'connectlink-read-v3', 'connectlink-docs-v1')
                  for n in audit['names']), str(audit['names']))

        page.evaluate(FETCH_JS, {'url': '/api/project-overcosts', 'as': 'json'})
        page.evaluate(FETCH_JS, {'url': '/export-projects-portfolio', 'as': 'text'})
        audit = page.evaluate(AUDIT_JS)
        check('a money endpoint and the portfolio export are kept NOWHERE',
              audit['money'] == [], str(audit['money']))
        check('and nothing beyond the named figures and contracts is saved',
              audit['doc'] == 1 and audit['read'] >= 4, str(audit))

        # ---- 2. no connection at all ---------------------------------------
        ctx.set_offline(True)
        del LOG[:]
        saved = page.evaluate(FETCH_JS, {'url': '/get_project_count?month=2026-10',
                                         'as': 'json'})
        check('with no connection the figure that was kept is served',
              saved['ok'] and (saved['body'] or {}).get('count') == 3, str(saved)[:140])
        check('and it says it is a copy rather than the server answer',
              saved['headers']['offline'] == '1', str(saved['headers']))
        check('and it carries the time it was saved',
              bool(saved['headers']['savedAt'])
              and saved['headers']['savedAt'].isdigit(), str(saved['headers']))
        check('the server was never asked -- that answer came off the device',
              LOG == [], str(LOG[:3]))

        text = page.evaluate("document.getElementById('clOfflineBannerText').textContent")
        check('the page says the figures are a copy, and when they were saved',
              text.startswith('No connection. The figures on this screen are a copy '
                              'saved on this device at '), text)
        check('and that nothing can be sent or saved',
              'Nothing here can be sent or saved' in text)
        check('and the notice is actually on screen',
              page.evaluate("getComputedStyle(document.getElementById('clOfflineBanner')).display")
              == 'block')

        for path in ('/api/projects-page', '/get_project/7',
                     '/api/project/7/has-gantt'):
            got = page.evaluate(FETCH_JS, {'url': path, 'as': 'json'})
            check('a kept endpoint replays, marked as a copy: ' + path,
                  got['ok'] and got['headers']['offline'] == '1', str(got)[:140])
        missing = page.evaluate(FETCH_JS, {'url': '/get_project/999', 'as': 'json'})
        check('an endpoint with no saved copy is refused, not guessed',
              missing['status'] == 503
              and (missing['body'] or {}).get('offline_no_copy') is True, str(missing))

        money = page.evaluate(FETCH_JS, {'url': '/api/project-overcosts', 'as': 'json'})
        check('a money figure is never replayed offline',
              money['status'] != 200 and not money['ok'], str(money)[:140])
        export = page.evaluate(FETCH_JS, {'url': '/export-projects-portfolio',
                                          'as': 'text'})
        check('the portfolio export is never replayed offline',
              export['status'] != 200 and not export['ok'], str(export)[:140])

        # ---- 3. a change with no connection is never queued ----------------
        del LOG[:]
        write = page.evaluate(FETCH_JS, {
            'url': '/update_project', 'as': 'json',
            'init': {'method': 'POST',
                     'headers': {'Content-Type': 'application/json'},
                     'body': '{"project_id": 7, "total_bill": "9999"}'}})
        check('a change with no connection fails',
              bool(write['error']) or not write['ok'], str(write)[:140])
        check('and is never sent, even later', LOG == [], str(LOG[:3]))
        toasts = page.evaluate("window.clToasts.join(' || ')")
        check('the page says the change was NOT saved, and that nothing was queued',
              'Not Saved' in toasts
              and 'Nothing was saved and nothing was sent' in toasts
              and 'been queued on this device' in toasts, toasts[:200])
        check('nothing is queued on the device either (no store of its own)',
              page.evaluate('Object.keys(localStorage).length') == 0)

        # ---- 4. contracts with no connection -------------------------------
        got = page.evaluate(FETCH_JS, {'url': '/download_contract/7', 'as': 'blob'})
        check('a contract that has been through once still opens with no connection',
              got['ok'] and got['body'] == len(CONTRACT), str(got)[:140])
        check('and it is marked as the device copy',
              got['headers']['offline'] == '1', str(got['headers']))
        check('and the download still has its filename',
              'contract-7.pdf' in (got['headers']['disposition'] or ''))
        never = page.evaluate(FETCH_JS, {'url': '/download_contract/999', 'as': 'text'})
        check('a contract that was never fetched is refused with instructions',
              never['status'] == 503
              and 'has not been saved on this device' in (never['body'] or ''),
              str(never)[:160])

        # the real Save for offline button, wired to the real modal inputs
        page.evaluate("""() => {
            const url = document.createElement('input');
            url.id = 'dcModalContractUrl';
            const status = document.createElement('span');
            status.id = 'dcOfflineStatus';
            document.body.appendChild(url);
            document.body.appendChild(status);
            url.value = '/download_contract/8';
        }""")
        SAVE_WAIT = """(needle) => new Promise(res => {
            saveContractForOffline(null);
            const started = Date.now();
            const tick = () => {
                const t = document.getElementById('dcOfflineStatus').textContent;
                if (t.indexOf(needle) !== -1 || Date.now() - started > 15000) return res(t);
                setTimeout(tick, 100);
            };
            tick();
        })"""
        failed = page.evaluate(SAVE_WAIT, 'Could not save')
        check('Save for offline with no connection and no copy fails loudly',
              'Could not save' in failed, failed)
        check('and no copy is pretended to exist',
              page.evaluate(AUDIT_JS)['doc'] == 1)

        # ---- 5. the connection coming back ---------------------------------
        ctx.set_offline(False)
        live = page.evaluate(FETCH_JS, {'url': '/get_project_count?month=2026-11',
                                        'as': 'json'})
        check('the connection coming back puts the server own answer back',
              live['ok'] and live['headers']['offline'] is None, str(live)[:140])
        check('and the notice goes',
              page.evaluate("getComputedStyle(document.getElementById('clOfflineBanner')).display")
              == 'none')
        kept = page.evaluate(SAVE_WAIT, 'Kept on this device')
        check('Save for offline while online keeps a copy, and says so',
              'Kept on this device' in kept, kept)
        audit = page.evaluate(AUDIT_JS)
        check('and the second contract really is on the device',
              audit['doc'] == 2 and len(audit['contracts']) == 2,
              str(audit['contracts']))

        deleted = page.evaluate("""() => new Promise(res => {
            deleteSavedContracts();
            const started = Date.now();
            const tick = () => {
                const t = document.getElementById('dcOfflineStatus').textContent;
                if (t.indexOf('Deleted') !== -1 || Date.now() - started > 15000) return res(t);
                setTimeout(tick, 100);
            };
            tick();
        })""")
        check('Delete saved copies removes them, and says how many',
              'Deleted 2 contract(s)' in deleted, deleted)
        audit = page.evaluate(AUDIT_JS)
        check('and the device really is clear of them',
              audit['doc'] == 0 and audit['contracts'] == [], str(audit))

        ctx.set_offline(True)
        gone = page.evaluate(FETCH_JS, {'url': '/download_contract/7', 'as': 'text'})
        check('so that contract is refused again with no connection',
              gone['status'] == 503
              and 'has not been saved on this device' in (gone['body'] or ''),
              str(gone)[:160])
        ctx.set_offline(False)

        # ---- 6. logging out takes the copies with it -----------------------
        page.evaluate(FETCH_JS, {'url': '/download_contract/7', 'as': 'blob'})
        check('a contract fetched again is kept again',
              page.evaluate(AUDIT_JS)['doc'] == 1)
        page.evaluate('handleLogout()')
        page.wait_for_url(BASE + '/logout', timeout=15000)
        page.wait_for_function('() => window.__docCaches !== null', timeout=15000)
        check('logging out takes the copies with it',
              page.evaluate('window.__docCaches') == [])

        check('nothing in the page threw while all this happened', not errors,
              '; '.join(errors[:3]))
        browser.close()
except Exception as exc:                                           # noqa: BLE001
    check('the browser run completed', False,
          '%s: %s' % (type(exc).__name__, exc))
finally:
    try:
        httpd.shutdown()
    except Exception:                                              # noqa: BLE001
        pass

out = '\n'.join(RESULTS)
print(out)
print('\nFAILURES: %d' % sum(1 for r in RESULTS if r.startswith('FAIL')))
