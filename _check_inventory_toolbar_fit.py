"""Regression check: the Inventory toolbar must always be able to wrap.

The toolbar holds many tools (Add Product ... Remove All Items & History). It was
a single non-wrapping flex row, so on a narrower screen the last buttons ran off
the right edge -- 'Remove All Items & History' was truncated and unreachable.

This asserts the markup keeps the row wrappable, and can additionally render a
faithful harness (_preview_inventory_toolbar.html) for a browser to measure.

    python _check_inventory_toolbar_fit.py          # static assertions
    python _check_inventory_toolbar_fit.py --render # also write the harness
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'templates', 'pos-system.html')
OUT = os.path.join(ROOT, '_preview_inventory_toolbar.html')

lines = []


def say(ok, msg):
    lines.append(('PASS  ' if ok else 'FAIL  ') + str(msg))
    return ok


html = open(SRC, encoding='utf-8').read()

start = html.find('<div id="inventoryPage"')
say(start != -1, 'the Inventory page exists')

end = html.find('Inventory Summary Cards', start)
seg = html[start:end]
say(end != -1 and len(seg) > 0, 'the Inventory toolbar block was located')

# The toolbar row: everything from the tools wrapper to the summary cards.
row = seg.find('d-flex gap-2 align-items-center')
say(row != -1, 'the tools row wrapper was found')
toolbar_open = seg[row:seg.find('>', row) + 1]

# ---------- 1. the row must be allowed to wrap ----------
say('flex-wrap' in toolbar_open,
    'the tools row declares flex-wrap (buttons reflow instead of overflowing)')
say('justify-content-end' in toolbar_open,
    'the tools row keeps the buttons aligned to the end when they wrap')

# ---------- 2. the search box must not force a fixed width on small screens ----
search_open = seg[seg.rfind('<div', 0, seg.find('id="inventorySearch"')):]
search_open = search_open[:search_open.find('>') + 1]
say('max-width: 100%' in search_open or 'max-width:100%' in search_open,
    'the search box may shrink (max-width:100%)')

# ---------- 3. both buttons are still present ----------
say('openRemoveAllStockModal()' in seg, 'the Remove All Items & History button is present')
say('openPhantomStockRepairModal()' in seg, 'the Repair Phantom Stock button is present')
say('Repair Phantom Stock' in seg, 'the repair button is labelled')

# ---------- 4. and the critical one: nothing forbids wrapping ----------
for bad in ['flex-nowrap']:
    say(bad not in toolbar_open, 'the tools row does not force a single line (%s)' % bad)

# ---------- 5. the last button is neither hidden nor out of flow ----------
tail = seg[seg.find('openRemoveAllStockModal()'):]
tail = tail[:tail.find('</button>')]
say('position:absolute' not in tail and 'd-none' not in tail,
    'the last button is not hidden or taken out of flow')

# ---------- 6. optional: write the browser harness ----------
if '--render' in sys.argv:
    styles = re.findall(r'<style[^>]*>(.*?)</style>', html, re.S | re.I)
    css = '\n'.join(s for s in styles if '{{' not in s and '{%' not in s)

    # #inventoryPage is display:none until its tab is opened; open it here so the
    # toolbar actually lays out in the harness.
    body = seg.replace('<div id="inventoryPage" style="display: none;">',
                       '<div id="inventoryPage">')

    page = (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<title>Inventory toolbar fit</title>\n'
        '<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">\n'
        '<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">\n'
        '<style>' + css + '</style>\n'
        '<style>html, body { margin:0; padding:0; }</style>\n'
        '</head>\n<body>\n'
        '<div id="posPage" class="container-fluid" style="padding:0; opacity:1;">\n'
        + body +
        '</div>\n</body>\n</html>\n'
    )
    open(OUT, 'w', encoding='utf-8').write(page)
    say(os.path.exists(OUT), 'the browser harness was written: %s' % os.path.basename(OUT))

print('\n'.join(lines))
failures = [l for l in lines if l.startswith('FAIL')]
print('')
print('FAILURES: %d' % len(failures))
sys.exit(1 if failures else 0)

