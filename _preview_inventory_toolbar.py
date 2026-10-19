"""Render just the Inventory toolbar to a standalone HTML page for a layout check.

The full pos-system.html cannot be served here (no database, no login), but the
toolbar's overflow is pure markup + CSS. This extracts the Inventory page block
and the stylesheet so a browser can tell us whether the last button sits inside
the viewport.

    python _preview_inventory_toolbar.py   ->  _preview_inventory_toolbar.html
"""
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'templates', 'pos-system.html')
OUT = os.path.join(ROOT, '_preview_inventory_toolbar.html')

html = open(SRC, encoding='utf-8').read()

# Every <style> block on the page, so the real .section-card / #inventoryPage
# rules apply exactly as they do in production.
styles = re.findall(r'<style[^>]*>(.*?)</style>', html, re.S | re.I)
css = '\n'.join(s for s in styles if '{{' not in s and '{%' not in s)

# The Inventory page block: from its div to the Inventory Summary Cards marker.
start = html.find('<div id="inventoryPage"')
end = html.find('Inventory Summary Cards', start)
# Close at the end of the toolbar row, which is enough to test the wrap.
seg = html[start:end]
row_start = seg.find('<div class="d-flex gap-2 align-items-center flex-wrap')
seg = seg[:row_start] + seg[row_start:]
# Trim to just after the Remove All Items button's closing div.
tail = seg.find('Remove All Items &amp; History')
close = seg.find('</div>', seg.find('</button>', tail))
seg = seg[:close + len('</div>')] + '\n                    </div>\n                </div>\n            </div>'

page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Inventory toolbar preview</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
<style>{css}</style>
</head>
<body>
<div class="container-fluid" id="posPage" style="padding:0">
{seg}
</div>
</body>
</html>
"""

open(OUT, 'w', encoding='utf-8').write(page)
print('wrote', OUT)
print('bytes:', len(page))
# The whole point: the toolbar must be able to wrap.
print('toolbar wraps:', 'flex-wrap' in seg)
print('has repair button:', 'openPhantomStockRepairModal()' in seg)
print('has remove-all button:', 'openRemoveAllStockModal()' in seg)
