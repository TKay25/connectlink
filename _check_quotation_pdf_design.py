"""The quotation PDFs must look like the contract, and must not carry the blue rule.

This drives the REAL generators (extracted from templates/adminpage.html, together
with the shared CLQPdf design kit and the helpers they call) against the real
html2pdf build in a headless browser, rasterises the PDFs, and checks them:

  * every generator still produces a PDF (nothing blank, nothing clipped away);
  * no horizontal blue rule under the title (the admin page's global
    `h1 { border-bottom: 2px solid #007bff }` used to leak into the document);
  * the contract palette is present (navy section bars / cards);
  * the design kit is what all three builders use.

Run:  python _check_quotation_pdf_design.py
"""
import functools
import http.server
import json
import os
import re
import shutil
import socketserver
import sys
import tempfile
import threading

ROOT = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(ROOT, 'templates', 'adminpage.html')
OUT = os.path.join(ROOT, '_check_quotation_pdf_design_out.txt')
RESULTS = []
SRC = open(TEMPLATE, encoding='utf-8').read()

CDN = 'https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js'
LOCAL = os.path.join(ROOT, '.tmp-qpdf', 'html2pdf.bundle.min.js')


def check(name, ok, detail=''):
    RESULTS.append(('PASS  ' if ok else 'FAIL  ') + name + (('  -> ' + str(detail)) if detail else ''))
    print(RESULTS[-1])


def extract_function(text, header):
    i = text.index(header)
    depth = 0
    started = False
    for k in range(i, len(text)):
        if text[k] == '{':
            depth += 1
            started = True
        elif text[k] == '}':
            depth -= 1
            if started and depth == 0:
                return text[i:k + 1]
    raise ValueError(header)


def slice_between(text, start, end):
    i = text.index(start)
    j = text.index(end, i)
    return text[i:j]


# ---------------------------------------------------------------------------
# 1. Static: one design kit, used by every quotation builder, no blue rule
# ---------------------------------------------------------------------------
check('the shared design kit exists', 'window.CLQPdf = (function () {' in SRC)

kit = slice_between(SRC, 'window.CLQPdf = (function () {', '\n})();') + '\n})();'
check('the kit carries the contract palette',
      '#1E2A56' in kit and '#2A3A78' in kit and '#d1d9f0' in kit)
title_rule = kit.split('.clq-title')[1].split('}')[0]
check('the kit neutralises the page rule under the title',
      'border:0' in title_rule.replace(' ', ''),
      title_rule.strip()[:90])

for builder, header in (('project quotation', 'async function generateQuotationPDF('),
                        ('kitchen quotation', 'async function generateKitchenPDF('),
                        ('portal download', 'window.downloadQuotationPDFFromPortal = window.downloadQuotationPDFFromPortal || async function(qId) {')):
    body = extract_function(SRC, header)
    check(f'the {builder} is built with the design kit', 'CLQPdf' in body or 'Q.' in body)
    check(f'the {builder} no longer draws a 100x2px navy rule',
          'width:100px;height:2px' not in body.replace(' ', '')
          and 'width: 100px; height: 2px' not in body)
    check(f'the {builder} renders through the shared renderer',
          'Q.render(' in body or 'CLQPdf.render(' in body)

check('no builder still prints the old "Project Quotation" 16px header',
      'font-size:16px;font-weight:900' not in SRC)

# ---------------------------------------------------------------------------
# 2. Render for real
# ---------------------------------------------------------------------------
PROJECT = {
    'clientName': 'Takudzwa Zvakasikwa', 'category': 'construction_single', 'size': '180',
    'quotationDate': '2026-10-29', 'totalCost': 48250.00, 'markup': 30,
    'vat': {'enabled': True, 'rate': 15.5, 'mode': 'exclusive'},
    'notes': '<p>Includes all finishings except burglar bars, kitchen units and gutters.</p>',
    'items': [
        {'item': 'Land Clearing and Setting Out', 'sqm': 180, 'inhouseRate': 3.2, 'clientPrice': 748.80, 'days': 5},
        {'item': 'Excavation and Footing', 'sqm': 180, 'inhouseRate': 6.48, 'clientPrice': 1516.32, 'days': 8},
        {'item': 'Slab and Deck Pouring', 'sqm': 180, 'inhouseRate': 19.2, 'clientPrice': 4492.80, 'days': 12},
        {'item': 'Roofing - Trusses, Sheeting and Finishing', 'sqm': 180, 'inhouseRate': 32.0, 'clientPrice': 7488.00, 'days': 14},
    ],
    'schedules': [
        {'workScope': 'Land clearing & setting out', 'startDate': '2026-11-03', 'endDate': '2026-11-07', 'days': 5},
        {'workScope': 'Excavation & footing', 'startDate': '2026-11-08', 'endDate': '2026-11-15', 'days': 8},
    ],
}

KITCHEN = {
    'clientName': 'Rudo Moyo', 'quotationDate': '2026-10-29', 'totalCost': 7200.00,
    'vat': {'enabled': True, 'rate': 15.5, 'mode': 'exclusive'},
    'notes': '<p>Worktop and splashback included. Appliances excluded.</p>',
    'items': [
        {'name': 'Base Units (Melamine, soft-close)', 'quantity': 8, 'amount': 210.00, 'totalPrice': 1680.00, 'days': 6},
        {'name': 'Wall Units', 'quantity': 6, 'amount': 185.00, 'totalPrice': 1110.00, 'days': 4},
        {'name': 'Granite Worktop', 'quantity': 1, 'amount': 1450.00, 'totalPrice': 1450.00, 'days': 3},
    ],
}

HELPERS = '\n\n'.join(
    extract_function(SRC, h) for h in (
        'function formatCurrency(value) {',
        'function escapeHtml(text) {',
        'function getQuotationVatSettings() {',
        'function computeQuotationVat(amount, vat) {',
        'function formatCategoryName(category, customCategory) {',
    ))

GEN_PROJECT = slice_between(SRC, 'async function generateQuotationPDF(',
                            '// Assign to window immediately after function definition')
GEN_KITCHEN = slice_between(SRC, 'async function generateKitchenPDF(',
                            '// Expose kitchen functions globally')

HARNESS = """<!doctype html><html><head><meta charset="utf-8">
<style>
  /* the admin page's own rule that used to leak into the PDF */
  h1 { border-bottom: 2px solid #007bff; padding-bottom: 10px; }
</style>
<script src="%s"></script>
<script>
%s
%s
%s
%s
window.runBuilders = async function () {
    const out = {};
    try {
        window.quotationData = %s;
        window.ganttChartData = window.quotationData.schedules || [];
        window.quotationPdfTablePlacement = 'default';
        out.project = await window.generateQuotationPDF('datauri', 'default');
    } catch (e) { out.projectError = String(e && e.message); }
    try {
        window.kitchenQuotationData = %s;
        out.kitchen = await window.generateKitchenPDF('datauri');
    } catch (e) { out.kitchenError = String(e && e.message); }
    return out;
};
</script></head><body><div id="host"></div></body></html>
""" % (CDN, kit, HELPERS, GEN_PROJECT, GEN_KITCHEN,
       json.dumps(PROJECT), json.dumps(KITCHEN))

HARNESS_PATH = os.path.join(ROOT, '_check_quotation_pdf_design_harness.html')
open(HARNESS_PATH, 'w', encoding='utf-8').write(HARNESS)
PDF_DIR = tempfile.mkdtemp(prefix='clq_pdf_')

try:
    from playwright.sync_api import sync_playwright
except Exception:                                                          # noqa: BLE001
    sync_playwright = None

if sync_playwright is None:
    check('playwright is available', False, 'pip install playwright')
else:
    def render_and_inspect(page):
        """Return {name: {'pages', 'blue_rule', 'navy'}} for each builder."""
        started = __import__('time').time()
        data = page.evaluate("() => window.runBuilders()")
        elapsed = __import__('time').time() - started
        report = {'_seconds': round(elapsed, 1)}
        for name in ('project', 'kitchen'):
            uri = data.get(name)
            if not uri:
                report[name] = {'error': data.get(name + 'Error', 'no pdf')}
                continue
            raw = __import__('base64').b64decode(uri.split(',', 1)[1])
            path = os.path.join(PDF_DIR, '_check_quotation_%s.pdf' % name)
            open(path, 'wb').write(raw)
            doc = fitz.open(stream=raw, filetype='pdf')
            first = doc[0].get_pixmap(dpi=110)
            width, height = first.width, first.height
            # A horizontal rule under the title: one row with a long run of
            # #007bff pixels near the top of the page.
            blue_run = 0
            for y in range(int(height * 0.06), int(height * 0.22)):
                run = best = 0
                for x in range(width):
                    r, g, b = first.pixel(x, y)[:3]
                    if abs(r - 0x00) < 40 and abs(g - 0x7b) < 40 and abs(b - 0xff) < 45:
                        run += 1
                        best = max(best, run)
                    else:
                        run = 0
                blue_run = max(blue_run, best)
            navy = 0
            for y in range(0, height, 3):
                for x in range(0, width, 3):
                    r, g, b = first.pixel(x, y)[:3]
                    if abs(r - 0x1e) < 30 and abs(g - 0x2a) < 30 and abs(b - 0x56) < 30:
                        navy += 1
            # The logo (navy mark + big grey swoosh) must actually be drawn.
            grey = 0
            for y in range(0, int(height * 0.20)):
                for x in range(0, width):
                    r, g, b = first.pixel(x, y)[:3]
                    if abs(r - g) < 14 and abs(g - b) < 14 and 55 < r < 190:
                        grey += 1
            # A tail page that holds only the footer looks like a bug in the deliverable.
            last_ink = 1.0
            stray = []
            if doc.page_count > 1:
                for y in range(height - 16, height):
                    ink = 0
                    for x in range(0, width, 2):
                        r, g, b = first.pixel(x, y)[:3]
                        if not (r > 248 and g > 248 and b > 248):
                            ink += 1
                    if ink > width * 0.2:                    # a rule, not text
                        stray.append(y)
                last = doc[-1].get_pixmap(dpi=110)
                bottom = 0
                for y in range(last.height - 1, -1, -1):
                    row_has_ink = False
                    for x in range(0, last.width, 4):
                        r, g, b = last.pixel(x, y)[:3]
                        if not (r > 245 and g > 245 and b > 245):
                            row_has_ink = True
                            break
                    if row_has_ink:
                        bottom = y
                        break
                last_ink = bottom / float(last.height)
            report[name] = {'pages': doc.page_count, 'blue_rule': blue_run, 'navy': navy,
                            'logo': grey, 'last_ink': round(last_ink, 3),
                            'stray_bottom': stray, 'bytes': len(raw)}
            doc.close()
        return report

    try:
        import fitz
    except Exception:                                                      # noqa: BLE001
        import pymupdf as fitz

    # Serve the repo over HTTP so the PDF's `/static/images/web-logo.png` resolves
    # exactly as it does inside the app (over file:// the logo would silently vanish).
    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    httpd = socketserver.ThreadingTCPServer(
        ('127.0.0.1', 0), functools.partial(QuietHandler, directory=ROOT))
    httpd.daemon_threads = True
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    harness_url = 'http://127.0.0.1:%d/_check_quotation_pdf_design_harness.html' % port
    logo_url = 'http://127.0.0.1:%d/static/images/web-logo.png' % port

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={'width': 1200, 'height': 900})
            page.set_default_timeout(60000)
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)[:180]))
            page.goto(harness_url, wait_until='load', timeout=60000)
            logo_width = page.evaluate(
                "url => new Promise(r => { const i = new Image();"
                " i.onload = () => r(i.naturalWidth); i.onerror = () => r(0); i.src = url; })",
                logo_url)
            check('the logo the PDFs embed is reachable', logo_width > 0, logo_width)
            loaded = page.evaluate("() => typeof window.html2pdf")
            check('the real html2pdf build is available for the render',
                  loaded == 'function',
                  'offline: static checks only' if loaded != 'function' else '')
            if loaded == 'function':
                report = render_and_inspect(page)
                check('both quotations render quickly (no download hang)',
                      report['_seconds'] < 30, '%ss' % report['_seconds'])
                for name in ('project', 'kitchen'):
                    info = report[name]
                    if 'error' in info:
                        check(f'the {name} quotation renders a PDF', False, info['error'])
                        continue
                    check(f'the {name} quotation renders a PDF', info['bytes'] > 20000, info)
                    check(f'the {name} quotation has no blue rule under the title',
                          info['blue_rule'] < 60, f"{info['blue_rule']} px in a row")
                    check(f'the {name} quotation uses the contract navy',
                          info['navy'] > 200, info['navy'])
                    check(f'the {name} quotation shows the ConnectLink logo',
                          info['logo'] > 200, info['logo'])
                    check(f'the {name} quotation does not end on a near-empty tail page',
                          info['last_ink'] > 0.15, info['last_ink'])
                    check(f'the {name} quotation has no stray rule at a page edge',
                          not info['stray_bottom'], info['stray_bottom'])
                check('no script error while building the documents', not errors, errors[:3])
            browser.close()
    except Exception as exc:                                                # noqa: BLE001
        check('the browser run completed', False, '%s: %s' % (type(exc).__name__, str(exc)[:200]))
    finally:
        httpd.shutdown()
        httpd.server_close()

with open(OUT, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(RESULTS) + '\n')

for leftover in (HARNESS_PATH, PDF_DIR):
    try:
        shutil.rmtree(leftover) if os.path.isdir(leftover) else os.remove(leftover)
    except OSError:
        pass

failures = [r for r in RESULTS if r.startswith('FAIL')]
print('\n%d checks, %d failed' % (len(RESULTS), len(failures)))
sys.exit(1 if failures else 0)
