"""The construction-items choice must reach BOTH tables in the PDF.

The options dialog asks where the Construction Items table goes, and one of its
answers -- "Include after the work schedule" -- only makes sense if there is a
work schedule to come after. The builder used to ignore the answer entirely: it
printed the items and then the schedule whatever was chosen, so a PDF the shop
had asked to keep bare still carried a full task list, and "after the work
schedule" changed nothing but the heading.

The rule now: for a construction quotation the schedule prints ONLY for
"after the work schedule" (and the items are placed under it); the other two
answers print neither the items nor the schedule. Kitchen quotations print no
schedule at all -- they are priced per item and every line already carries its
own Days. Quotations that are never asked -- TV units, Other -- keep their
schedule, because no option was ever put to the operator.

This runs the REAL shipped functions (extracted from the template by brace
matching) under node with nothing but the PDF kit stubbed, so what is measured is
the code that ships. No browser and no npm package needed.

Run:  python _check_quotation_pdf_table_placement.py
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(ROOT, 'templates', 'adminpage.html')
OUT = os.path.join(ROOT, '_check_quotation_pdf_table_placement_out.txt')
RESULTS = []


def check(name, ok, detail=''):
    RESULTS.append(('PASS  ' if ok else 'FAIL  ') + name + (('  -> ' + str(detail)) if detail else ''))
    print(RESULTS[-1])
    try:
        with open(OUT, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(RESULTS) + '\n')
    except Exception:                                                     # noqa: BLE001
        pass


src = io.open(TEMPLATE, encoding='utf-8').read()

# ---------- the shape of the change, readable without running anything ----------
check('the placement rule is one shared function',
      'function quotationShowsWorkSchedule(' in src)
check('the PDF builder consults it',
      'quotationShowsWorkSchedule(category, normalizedPlacement)' in src)
check('the early fallback builder consults it too',
      'quotationShowsWorkSchedule(category, tablePlacement)' in src)
check('the items table is built, not pushed in a fixed order',
      'var constructionItemsBlockHtml' in src and 'var workScheduleBlockHtml' in src)
check('"after schedule" places the items under the schedule',
      "if (normalizedPlacement === 'after_schedule' && workScheduleBlockHtml)" in src)

if shutil.which('node') is None:
    check('node is available to run the shipped functions', False, 'install node')
    ok = all(r.startswith('PASS') for r in RESULTS)
    print('\nFAILURES: %d' % sum(1 for r in RESULTS if r.startswith('FAIL')))
    sys.exit(0 if ok else 1)

HARNESS = r"""
const fs = require('fs');
const vm = require('vm');
const src = fs.readFileSync(process.argv[2], 'utf8');

function extract(name) {
  const start = src.indexOf('function ' + name + '(');
  if (start === -1) throw new Error('not found: ' + name);
  let depth = 0;
  for (let i = src.indexOf('{', start); i < src.length; i++) {
    if (src[i] === '{') depth++;
    else if (src[i] === '}') { depth--; if (depth === 0) return src.slice(start, i + 1); }
  }
  throw new Error('unbalanced: ' + name);
}

const out = [];
const check = (n, ok, d) => out.push((ok ? 'PASS  ' : 'FAIL  ') + n + (d !== undefined ? '  -> ' + d : ''));

let captured = '';
const base = {
  money: v => 'USD ' + Number(v || 0).toFixed(2),
  doc: body => '<!doctype html><html><body>' + body + '</body></html>',
  table: (cols, rows) => '<table><thead><tr>' +
    cols.map(c => '<th>' + c.label + '</th>').join('') + '</tr></thead><tbody>' +
    rows.map(r => '<tr>' + r.map(c => '<td>' + (c.h === undefined ? '' : c.h) + '</td>').join('') + '</tr>').join('') +
    '</tbody></table>',
  render: async h => { captured = h; return 'rendered'; },
  palette: {},
};
const CLQ = new Proxy(base, {
  get(t, p) {
    if (p in t) return t[p];
    if (typeof p === 'symbol') return undefined;
    return (...a) => '<' + String(p) + '>' + a.map(x => String(x == null ? '' : x)).join('') + '</' + String(p) + '>';
  },
});

// Minimal page stubs: these functions only touch the DOM to find a loader.
const win = { CLQPdf: CLQ, alert: () => {}, quotationData: null, ganttChartData: [] };
const doc = {
  getElementById: () => null,
  querySelector: () => null,
  body: { appendChild: () => {} },
  createElement: () => ({ style: {}, appendChild: () => {} }),
};

const sandbox = {
  window: win, document: doc, console: { log: () => {}, error: () => {}, warn: () => {} },
  escapeHtml: s => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'),
  computeQuotationVat: net => ({ enabled: false, rate: 0, mode: 'exclusive', net, vat: 0, total: net }),
  quotationVatFromRecord: () => ({ enabled: false }),
  getQuotationVatSettings: () => ({ enabled: false }),
  formatCategoryName: c => c,
  formatCurrency: v => 'USD ' + Number(v || 0).toFixed(2),
  usdMoney: v => 'USD ' + Number(v || 0).toFixed(2),
  showLoader: () => {}, hideLoader: () => {}, closeModal: () => {},
  quotationRatesCache: [],
};
const ctx = vm.createContext(sandbox);
vm.runInContext(extract('quotationShowsWorkSchedule'), ctx);
vm.runInContext(extract('generateQuotationPDF'), ctx);

const CONSTRUCTION = {
  clientName: 'Tendai Chirwa', category: 'construction_single', size: 80, totalCost: 45000,
  quotationDate: '2026-10-20', notes: '', vat: { enabled: false },
  items: [{ name: 'Foundation', quantity: 30, unitRate: 120, totalPrice: 3600, days: 30 }],
};
const KITCHEN = {
  clientName: 'Nyasha Moyo', category: 'kitchen', size: 12, totalCost: 1500,
  quotationDate: '2026-11-01', notes: '', vat: { enabled: false },
  items: [{ name: 'Base cabinets', quantity: 6, amount: 100, days: 10 }],
};
const SCHEDULES = [{ workScope: 'Foundation', startDate: '2026-10-20', endDate: '2026-11-18', days: 30 }];

async function build(data, placement) {
  captured = '';
  win.quotationData = data;
  win.ganttChartData = SCHEDULES;
  await sandbox.generateQuotationPDF('datauri', placement);
  return captured;
}

(async () => {
  const rule = sandbox.quotationShowsWorkSchedule;
  check('construction + exclude: no schedule', rule('construction_single', 'exclude') === false);
  check('construction + below summary: no schedule', rule('construction_single', 'default') === false);
  check('construction + after schedule: schedule', rule('construction_single', 'after_schedule') === true);
  check('kitchen prints no schedule', rule('kitchen', 'default') === false);
  check('saved kitchen prints no schedule', rule('kitchen_cabinets', 'after_schedule') === false);
  check('a quotation never asked keeps its schedule', rule('tv_units', 'default') === true);
  check('an unknown answer falls back to below-summary', rule('construction_single', 'banana') === false);

  let html = await build(CONSTRUCTION, 'exclude');
  check('PDF exclude: no Work Schedule', !/Work Schedule/.test(html));
  check('PDF exclude: no Construction Items', !/Construction Items/.test(html));
  check('PDF exclude: still a whole document', /Tendai Chirwa/.test(html) && html.length > 500, html.length);

  html = await build(CONSTRUCTION, 'default');
  check('PDF below summary: items, no schedule',
        /Construction Items/.test(html) && !/Work Schedule/.test(html));

  html = await build(CONSTRUCTION, 'after_schedule');
  check('PDF after schedule: both tables present',
        /Work Schedule/.test(html) && /Construction Items/.test(html));
  check('PDF after schedule: schedule comes first',
        html.indexOf('Work Schedule') < html.indexOf('Construction Items'),
        [html.indexOf('Work Schedule'), html.indexOf('Construction Items')]);

  html = await build(KITCHEN, 'default');
  check('PDF kitchen: no Work Schedule, no construction items table',
        !/Work Schedule/.test(html) && !/Construction Items/.test(html));

  html = await build(KITCHEN, 'after_schedule');
  check('PDF kitchen + after schedule: still no Work Schedule',
        !/Work Schedule/.test(html));

  console.log(out.join('\n'));
  process.exit(out.some(l => l.startsWith('FAIL')) ? 1 : 0);
})().catch(e => { console.log('FAIL  the builder threw: ' + e.message); process.exit(1); });
"""

work = tempfile.mkdtemp(prefix='clq_place_')
js_path = os.path.join(work, 'harness.js')
with io.open(js_path, 'w', encoding='utf-8') as fh:
    fh.write(HARNESS)

proc = subprocess.run(['node', js_path, TEMPLATE], capture_output=True, text=True)
lines = [l for l in (proc.stdout or '').splitlines() if l.strip()]
if proc.returncode not in (0, 1) or not lines:
    check('the shipped builder ran', False, (proc.stderr or proc.stdout or '').strip()[:300])
else:
    for line in lines:
        if line.startswith(('PASS  ', 'FAIL  ')):
            RESULTS.append(line)
            print(line)
        elif line.startswith('FAIL '):
            RESULTS.append(line)
            print(line)
    check('the shipped builder ran to completion', proc.returncode == 0,
          (proc.stderr or '').strip()[:200] if proc.returncode else '')

try:
    shutil.rmtree(work, ignore_errors=True)
except Exception:                                                         # noqa: BLE001
    pass

print()
ok = all(r.startswith('PASS') for r in RESULTS)
print('FAILURES: %d' % sum(1 for r in RESULTS if r.startswith('FAIL')))
sys.exit(0 if ok else 1)
