"""Render the WORKSHOP STOCK PDF from the real ConnectLink code, with realistic data.

Usage:  python _t_ws_render.py <output.pdf>

Only `_workshop_ledger`, `_cl_company_branding` and `get_db` are faked; everything else
(styles, header, summary, boxes, table, signatures, footer) is the shipped code, so what
comes out is what the user would download. Used to LOOK at the design.
"""
import ast, io, sys, datetime

WS = r"c:\Users\tzvakasikwa\OneDrive - CBZ Bank Limited\Documents\GitHub\connectlink"
SRC = WS + r"\ConnectLink.py"
OUT = sys.argv[1] if len(sys.argv) > 1 else WS + r"\_preview_workshop_stock.pdf"

src = open(SRC, encoding='utf-8').read()
tree = ast.parse(src)

PREFIXES = ('_proc_', '_cl_', '_ws_', '_workshop_', '_req_', '_render_')
ns = {'io': io, 'datetime': datetime.datetime, 'os': __import__('os'), 're': __import__('re'),
      'timedelta': datetime.timedelta, 'date': datetime.date}
for m in tree.body:
    if isinstance(m, ast.Assign) and isinstance(m.targets[0], ast.Name):
        try:
            ns[m.targets[0].id] = ast.literal_eval(m.value)
        except Exception:
            pass
loaded = 0
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name.startswith(PREFIXES):
        try:
            exec(compile(ast.get_source_segment(src, node), node.name, 'exec'), ns)
            loaded += 1
        except Exception as e:
            print('  skipped', node.name, e)
print('loaded', loaded, 'functions')

# ---- the user's own shape: 11 boards, opening stock in halves, a couple of issues ----
LEDGER = [
    {'id': 1, 'name': 'Black Gloss', 'category': 'Boards', 'opening': 0, 'received': 0.5, 'issued': 0, 'closing': 0.5},
    {'id': 2, 'name': 'Congo', 'category': 'Boards', 'opening': 0, 'received': 1, 'issued': 1, 'closing': 0},
    {'id': 3, 'name': 'Dublin', 'category': 'Boards', 'opening': 0, 'received': 0.5, 'issued': 0, 'closing': 0.5},
    {'id': 4, 'name': 'Dublin Gloss', 'category': 'Boards', 'opening': 0, 'received': 1, 'issued': 0, 'closing': 1},
    {'id': 5, 'name': 'Kitchen Unit Base 600mm', 'category': 'Kitchen', 'opening': 2, 'received': 4, 'issued': 3, 'closing': 3},
    {'id': 6, 'name': 'Marine Ply 12mm', 'category': 'Timber', 'opening': 0, 'received': 24.5, 'issued': 6, 'closing': 18.5},
    {'id': 7, 'name': 'MDF Board 16mm', 'category': 'Boards', 'opening': 6, 'received': 0, 'issued': 5, 'closing': 1},
    {'id': 8, 'name': 'Melamine Board 18mm White', 'category': 'Boards', 'opening': 24, 'received': 0, 'issued': 20, 'closing': 4},
    {'id': 9, 'name': 'Granite Top 2.4m', 'category': 'Kitchen', 'opening': 3, 'received': 0, 'issued': 1, 'closing': 2},
    {'id': 10, 'name': 'Edging Tape 22mm', 'category': 'Fittings', 'opening': 2, 'received': 0, 'issued': 0, 'closing': 2},
    {'id': 11, 'name': 'Clip-on Hinge 35mm', 'category': 'Fittings', 'opening': 148, 'received': 0, 'issued': 36, 'closing': 112},
]
STOCK = [
    {'id': 1, 'name': 'Black Gloss', 'category': 'Boards', 'unit': 'sheet', 'stock': 0.5, 'min_level': 0, 'low': False, 'active': True},
    {'id': 2, 'name': 'Congo', 'category': 'Boards', 'unit': 'sheet', 'stock': 0, 'min_level': 0, 'low': False, 'active': True},
    {'id': 3, 'name': 'Dublin', 'category': 'Boards', 'unit': 'sheet', 'stock': 0.5, 'min_level': 0, 'low': False, 'active': True},
    {'id': 4, 'name': 'Dublin Gloss', 'category': 'Boards', 'unit': 'sheet', 'stock': 1, 'min_level': 0, 'low': False, 'active': True},
    {'id': 5, 'name': 'Kitchen Unit Base 600mm', 'category': 'Kitchen', 'unit': 'unit', 'stock': 3, 'min_level': 2, 'low': False, 'active': True},
    {'id': 6, 'name': 'Marine Ply 12mm', 'category': 'Timber', 'unit': 'sheet', 'stock': 18.5, 'min_level': 5, 'low': False, 'active': True},
    {'id': 7, 'name': 'MDF Board 16mm', 'category': 'Boards', 'unit': 'sheet', 'stock': 1, 'min_level': 12, 'low': True, 'active': True},
    {'id': 8, 'name': 'Melamine Board 18mm White', 'category': 'Boards', 'unit': 'sheet', 'stock': 4, 'min_level': 10, 'low': True, 'active': True},
    {'id': 9, 'name': 'Granite Top 2.4m', 'category': 'Kitchen', 'unit': 'length', 'stock': 2, 'min_level': 1, 'low': False, 'active': True},
    {'id': 10, 'name': 'Edging Tape 22mm', 'category': 'Fittings', 'unit': 'roll', 'stock': 2, 'min_level': 5, 'low': True, 'active': True},
    {'id': 11, 'name': 'Clip-on Hinge 35mm', 'category': 'Fittings', 'unit': 'piece', 'stock': 112, 'min_level': 50, 'low': False, 'active': True},
]
MOVES = [
    {'id': 1, 'date': datetime.datetime(2026, 9, 20, 8, 40), 'reference': 'Opening', 'item': 'Melamine Board 18mm White',
     'category': 'Boards', 'type': 'in', 'label': 'Opening stock', 'reason': 'opening', 'undoable': False,
     'qty_in': 24, 'qty_out': 0, 'by': 'T. Chikerema', 'notes': ''},
    {'id': 2, 'date': datetime.datetime(2026, 9, 20, 8, 45), 'reference': 'Opening', 'item': 'Clip-on Hinge 35mm',
     'category': 'Fittings', 'type': 'in', 'label': 'Opening stock', 'reason': 'opening', 'undoable': False,
     'qty_in': 148, 'qty_out': 0, 'by': 'T. Chikerema', 'notes': ''},
    {'id': 3, 'date': datetime.datetime(2026, 9, 20, 9, 10), 'reference': 'PO-0004', 'item': 'Marine Ply 12mm',
     'category': 'Timber', 'type': 'in', 'label': 'Goods received', 'reason': 'received', 'undoable': False,
     'qty_in': 20, 'qty_out': 0, 'by': 'T. Chikerema', 'notes': ''},
    {'id': 4, 'date': datetime.datetime(2026, 9, 20, 9, 30), 'reference': 'PO-0007', 'item': 'Marine Ply 12mm',
     'category': 'Timber', 'type': 'in', 'label': 'Goods received', 'reason': 'received', 'undoable': False,
     'qty_in': 4.5, 'qty_out': 0, 'by': 'T. Chikerema', 'notes': ''},
    {'id': 5, 'date': datetime.datetime(2026, 9, 20, 10, 15), 'reference': 'REQ-0009', 'item': 'Marine Ply 12mm',
     'category': 'Timber', 'type': 'out', 'label': 'Requisition issued', 'reason': 'requisition_in_stock',
     'undoable': False, 'qty_in': 0, 'qty_out': 4, 'by': 'Mrs G', 'notes': ''},
    {'id': 6, 'date': datetime.datetime(2026, 9, 20, 11, 0), 'reference': 'REQ-0012', 'item': 'Marine Ply 12mm',
     'category': 'Timber', 'type': 'out', 'label': 'Requisition issued', 'reason': 'requisition_in_stock',
     'undoable': False, 'qty_in': 0, 'qty_out': 2, 'by': 'Mrs G', 'notes': ''},
    {'id': 7, 'date': datetime.datetime(2026, 9, 20, 12, 20), 'reference': 'JOB-0007', 'item': 'Melamine Board 18mm White',
     'category': 'Boards', 'type': 'out', 'label': 'Cut / used in production', 'reason': 'cut', 'undoable': True,
     'qty_in': 0, 'qty_out': 20, 'by': 'Workshop', 'notes': ''},
    {'id': 8, 'date': datetime.datetime(2026, 9, 20, 13, 5), 'reference': 'JOB-0007', 'item': 'Clip-on Hinge 35mm',
     'category': 'Fittings', 'type': 'out', 'label': 'Cut / used in production', 'reason': 'cut', 'undoable': True,
     'qty_in': 0, 'qty_out': 36, 'by': 'Workshop', 'notes': ''},
    {'id': 9, 'date': datetime.datetime(2026, 9, 20, 14, 0), 'reference': 'REQ-0015', 'item': 'MDF Board 16mm',
     'category': 'Boards', 'type': 'out', 'label': 'Requisition issued', 'reason': 'requisition_in_stock',
     'undoable': False, 'qty_in': 0, 'qty_out': 5, 'by': 'Mrs G', 'notes': ''},
    {'id': 10, 'date': datetime.datetime(2026, 9, 20, 15, 30), 'reference': 'JOB-0008', 'item': 'Granite Top 2.4m',
     'category': 'Kitchen', 'type': 'out', 'label': 'Cut / used in production', 'reason': 'cut', 'undoable': True,
     'qty_in': 0, 'qty_out': 1, 'by': 'Workshop', 'notes': ''},
    {'id': 11, 'date': datetime.datetime(2026, 9, 20, 16, 0), 'reference': 'REQ-0016', 'item': 'Kitchen Unit Base 600mm',
     'category': 'Kitchen', 'type': 'out', 'label': 'Requisition issued', 'reason': 'requisition_in_stock',
     'undoable': False, 'qty_in': 0, 'qty_out': 3, 'by': 'Mrs G', 'notes': ''},
    {'id': 12, 'date': datetime.datetime(2026, 9, 20, 16, 20), 'reference': 'REQ-0018', 'item': 'Congo',
     'category': 'Boards', 'type': 'out', 'label': 'Requisition issued', 'reason': 'requisition_in_stock',
     'undoable': False, 'qty_in': 0, 'qty_out': 1, 'by': 'Mrs G', 'notes': ''},
]
TOTALS = {
    'items': len(LEDGER),
    'opening': sum(x['opening'] for x in LEDGER),
    'received': sum(x['received'] for x in LEDGER),
    'issued': sum(x['issued'] for x in LEDGER),
    'closing': sum(x['closing'] for x in LEDGER),
    'on_hand_items': sum(1 for x in LEDGER if x['closing'] > 0),
    'low_stock': sum(1 for s in STOCK if s['low']),
    'movements': len(MOVES),
}

ns['_workshop_ledger'] = lambda a, b: {'ledger': LEDGER, 'movements': MOVES, 'stock': STOCK, 'totals': TOTALS}
ns['_cl_company_branding'] = lambda: ({
    'name': 'ConnectLink Properties', 'tagline': 'Building & Property Development',
    'address': '38A Coronation Avenue Greendale Harare',
    'phone_intl': '+263 773 368 558', 'phone2_intl': '+263 718 047 602',
    'phone3_intl': '+263 781 959 700',
    'email': 'info@connectlinkproperties.co.zw', 'tin': '2000608068'},
    # the REAL logo file, exactly as _cl_company_branding loads it
    __import__('base64').b64encode(
        open(WS + r"\static\images\web-logo.png", 'rb').read()).decode('utf-8'))


class _Cur:
    def execute(self, sql, params=None):
        self.sql = sql

    def fetchall(self):
        return [('REQ-0009', '7--Rainham Park--Harare--CBZ'),
                ('REQ-0012', '9--Belvedere Clinic--Bulawayo--CBZ'),
                ('REQ-0015', '12--Mount Pleasant Housing Scheme--Harare--CBZ'),
                ('REQ-0016', '3--Chisipite House--Chisipite--A. Ncube')]


class _CM:
    def __enter__(self):
        return (_Cur(), type('C', (), {'commit': lambda s: None})())

    def __exit__(self, *a):
        return False


ns['get_db'] = lambda: _CM()

pdf = ns['_render_workshop_pdf'](datetime.datetime(2026, 9, 20), datetime.datetime(2026, 9, 20),
                                 '20 Sep 2026', 'Takudzwa Zvakasikwa')
open(OUT, 'wb').write(pdf)
print('wrote', OUT, len(pdf), 'bytes')
