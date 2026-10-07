"""Check that the POS management brief always describes the period its figures came
from (templates/pos-system.html).

What was on the screen:

    Across This month the shop rang up 1 sale(s) for $105.00 in revenue and $38.76
    gross profit ... The strongest trading day was 2026-10-07 ...

-- a sentence that named a MONTH over one day's takings, and named the day in UTC.
The brief is written on the Analytics tab, from the same report data as the Sales
Report, but it took its period from the Analytics selector -- which was pre-set to
"This month" and never applied. So the words came from one period and every figure
from another: the one thing a brief must never do.

What keeps the two in step now:
  * ONE applied scope (`window.__reportScope`), written by loadSalesReport -- the one
    function that filters the report -- so it can only ever name a range that was
    really applied, and it is written before the fetch so no figure outruns its name;
  * the brief names THAT scope, never a selector's unapplied choice;
  * the Analytics selector is pointed at the applied scope on every load, and picking
    a period or a custom date there applies it at once (no second click to wait for);
  * a period that traded nothing says so, rather than leaving the previous period's
    brief and KPIs on screen under the new period's name;
  * the day the brief names is bucketed on the shop's own clock (toLocalISODate), not
    a UTC one: a sale made at 00:30 in Harare is filed under the day the shop traded,
    not under the UTC day that had already rolled over.

Run:  python _check_analytics_period_scope.py    (writes _check_analytics_period_scope_out.txt)

The rule half needs only the standard library. The last section drives the real page
in a real browser against stand-in POS API answers, so use the project's environment:

    .venv\\Scripts\\python.exe _check_analytics_period_scope.py
"""
import http.client
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import threading
import urllib.parse
import uuid
from datetime import date, datetime, timedelta, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = pathlib.Path(__file__).parent
PORT = int(os.environ.get('POS_SCOPE_PORT', '8798'))
TEMPLATE = 'templates/pos-system.html'
PAGE_PATH = '/pos-system.html'          # the URL the page is served on below
OUT = '_check_analytics_period_scope_out.txt'
RESULTS = []
# This process's own name for its server. Two copies of this script can both bind
# 127.0.0.1:PORT on Windows (the sockets set SO_REUSEADDR and Windows honours it for
# a second bind), and the browser then talks to whichever copy bound last -- a dead
# or dying copy turns a healthy page load into a 30s goto timeout with nothing on
# screen to explain it. The token lets the server check below say plainly whether the
# server answering is THIS run's.
RUN_TOKEN = uuid.uuid4().hex[:12]
# How many rows the movers panel prints before it stops: the brief's own lists are
# the ones that have to name every line, so this is the number they must beat.
MOVERS_SHOW = 8


def _flush():
    try:
        with open(OUT, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(RESULTS) + '\n')
    except Exception:                                                  # noqa: BLE001
        pass


def check(name, ok, detail=''):
    RESULTS.append(f"{'PASS' if ok else 'FAIL'}  {name}"
                   f"{('  -> ' + detail) if detail else ''}")
    _flush()


check('script started', True)

try:
    NEW = (ROOT / TEMPLATE).read_text(encoding='utf-8')
    check('read the POS page', True, '%d chars' % len(NEW))
except Exception as exc:                                               # noqa: BLE001
    check('read the POS page', False, '%s: %s' % (type(exc).__name__, exc))
    print('\n'.join(RESULTS))
    print('\nFAILURES: 1')
    sys.exit(1)

# git is not always on the PATH of a detached process, so find it properly.
GIT = shutil.which('git')
if not GIT:
    for cand in (r'C:\Program Files\Git\cmd\git.exe',
                 r'C:\Program Files (x86)\Git\cmd\git.exe',
                 os.path.expandvars(r'%LOCALAPPDATA%\Programs\Git\cmd\git.exe'),
                 os.path.expandvars(r'%ProgramFiles%\Git\bin\git.exe')):
        if cand and os.path.exists(cand):
            GIT = cand
            break
GIT = GIT or 'git'

OLD = None
try:
    proc = subprocess.run([GIT, 'show', 'HEAD:' + TEMPLATE],
                          capture_output=True, cwd=str(ROOT))
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or b'').decode('utf-8', 'replace').strip()
                           or 'git show failed')
    OLD = proc.stdout.decode('utf-8', 'replace')
    check('read the committed POS page for comparison', True, '%d chars' % len(OLD))
except Exception as exc:                                               # noqa: BLE001
    check('read the committed POS page for comparison', False,
          '%s: %s -- HEAD comparison skipped' % (type(exc).__name__, exc))


def first_error(body):
    """(message, line-within-the-block) of the first syntax error, or None.

    `?.` is normalised to `.` first: the console's esprima is an ES2017 parser and the
    page has used optional chaining long before this change, so that one construct
    would otherwise hide every line after it.
    """
    try:
        import esprima
    except Exception as exc:                                           # noqa: BLE001
        return 'no-parser: %s' % exc, 0
    try:
        esprima.parseScript(body.replace('?.', '.'))
        return None, 0
    except Exception as exc:                                           # noqa: BLE001
        return getattr(exc, 'message', str(exc)), getattr(exc, 'lineNumber', 0)


def _skip(src, i):
    """Index just past the comment / string / template literal that starts at i."""
    two = src[i:i + 2]
    if two == '//':
        j = src.find('\n', i)
        return len(src) if j < 0 else j + 1
    if two == '/*':
        j = src.find('*/', i)
        return len(src) if j < 0 else j + 2
    quote = src[i]
    j = i + 1
    while j < len(src):
        if src[j] == '\\':
            j += 2
            continue
        if src[j] == quote:
            return j + 1
        if quote == '`' and src[j] == '\n':
            return j + 1
        j += 1
    return len(src)


def extract(src, start_marker, last=False):
    """The whole declaration whose text starts at `start_marker`, brace-matched."""
    i = src.rindex(start_marker) if last else src.index(start_marker)
    if src[max(0, i - 6):i] == 'async ':
        i -= 6                     # keep the keyword, or `await` will not parse
    j = src.index('{', i)
    depth = 0
    while j < len(src):
        ch = src[j]
        if ch in '\'"`' or src[j:j + 2] in ('//', '/*'):
            j = _skip(src, j)
            continue
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return src[i:j + 1]
        j += 1
    raise ValueError('unbalanced braces for ' + start_marker)


def between(src, start_marker, end_marker):
    """The text from `start_marker` up to `end_marker` (for slices of long functions)."""
    i = src.index(start_marker)
    return src[i:src.index(end_marker, i)]


def count(src, needle):
    return src.count(needle)


# ---------------------------------------------------------------------------
# 1. The touched code parses.
#    Only the functions this change rewrote are parsed, so that syntax trouble in
#    unrelated, long-standing code stays out of the signal.
# ---------------------------------------------------------------------------
TOUCHED = [
    ('function loadSalesReport(', False),
    ('function updateReportDateRange(', False),
    ('function renderSalesReport(', False),
    ('function applyAnalyticsPeriod(', False),
    ('function renderAnalytics(', False),
    ('function reportScopeLabel(', False),
    ('function syncAnalyticsScope(', False),
    ('function onAnalyticsPeriodChange(', False),
    ('function onAnalyticsDateChange(', False),
    ('function toLocalISODate(', False),
    ('function fmtDayLong(', False),
]

for marker, last in TOUCHED:
    name = marker.replace('function ', '').rstrip('(')
    try:
        body = extract(NEW, marker, last=last)
    except ValueError as exc:
        check('%s() could be read from the page' % name, False, str(exc))
        continue
    msg, line = first_error(body)
    check('%s() parses' % name, msg is None,
          'line %d of the function: %s' % (line, msg) if msg else
          '%d chars (lines %d-%d)'
          % (len(body), NEW.count('\n', 0, NEW.index(marker)) + 1,
             NEW.count('\n', 0, NEW.index(marker) + len(body)) + 1))

_fetch_probe = extract(NEW, 'function renderAnalytics(')
check('the analytics page is drawn from one filtered report, not its own fetch',
      'fetch(' not in _fetch_probe and 'currentReportData' in _fetch_probe,
      'renderAnalytics() draws currentReportData (%d fetch( inside it); the report '
      'itself is fetched once, in loadSalesReport'
      % count(_fetch_probe, 'fetch('))

# ---------------------------------------------------------------------------
# 2. One applied scope, written before the figures it names.
# ---------------------------------------------------------------------------
load = extract(NEW, 'function loadSalesReport(')
check('loadSalesReport() publishes the applied scope',
      '__reportScope' in load,
      'window.__reportScope present' if '__reportScope' in load else 'not found')
scope_set = load.find('__reportScope')
fetch_at = load.find('/api/transactions?limit=2000')
check('the scope is published BEFORE the fetch, never after it',
      0 <= scope_set < fetch_at,
      'scope at %d, fetch at %d' % (scope_set, fetch_at))

brief = between(NEW, '// ---- Automated management brief ----',
                '// ---- Advanced retail intelligence ----')
check("the brief's period comes from the applied scope",
      'const periodLabel = reportScopeLabel();' in brief
      and "'Across ' + periodLabel" in brief
      and 'briefEl.innerHTML' in brief,
      'the sentence is composed from reportScopeLabel() and written into the brief '
      '(%d chars)' % len(brief))
check("the brief does NOT read its period from the analytics selector",
      "getElementById('anPeriod')" not in brief and 'anPeriod' not in brief,
      'no selector read inside the brief block'
      if 'anPeriod' not in brief else 'the brief still reads the analytics selector')

# The counts mean nothing without the names: "112 product(s) are holding stock"
# tells the operator how bad it is, not which 112 to walk the shelf with. So each
# count is followed by the list of what it counted, in a box that opens and shuts.
check('the brief follows its counts with the products and lines themselves',
      '<details class="an-brief-items ' in brief and '<summary>' in brief
      and '</details>' in brief,
      'each count is followed by a collapsible list' if '<details' in brief
      else 'the brief counts the offenders but never names them')
check('the dead-stock list is built from the same lines the sentence counted',
      'deadStock.map(' in brief and "' product(s) are holding stock" in brief
      and 'deadRows.length' in brief,
      'the list is deadStock itself, and the box repeats its length')
check('the slow-moving list is built from the same filter the count uses',
      'ranked.filter(r => r.qty < 5)' in brief and "' sold'" in brief,
      'the same qty < 5 filter, so the list and the count cannot drift apart')
check('the brief lists EVERY line, not the handful the movers panel caps at',
      'deadStock.slice(' not in brief,
      'the movers panel above is the one that shows %d and stops; the brief lists '
      'them all' % MOVERS_SHOW
      if 'deadStock.slice(' not in brief else 'the list is truncated like the panel')
dead_rows_fn = between(brief, 'const deadRows = deadStock.map(', 'const slowRows =')
check('a listed product carries what it holds and what that stock is worth',
      "' in stock'" in dead_rows_fn and 'buy_price' in dead_rows_fn
      and '.toFixed(2)' in dead_rows_fn,
      'stock on hand plus cash tied up at cost')
slow_rows_fn = between(brief, 'const slowRows = ranked.filter', 'const briefBoxes =')
check('a listed slow line carries what it sold and what is left',
      "r.qty + ' sold'" in slow_rows_fn and 'r.stock + ' in slow_rows_fn,
      'units sold plus stock on hand')
box_fn = between(brief, 'const briefBox = (tone, head, rows) =>', '// Cash tied up')
check('the box is built closed, so the brief still reads as a brief',
      ' open>' not in box_fn and '<summary>' in box_fn,
      'no open attribute: the operator opens the list they want')
check('a list is only rendered when there is something in it',
      'deadRows.length' in brief and 'slowRows.length' in brief,
      'empty counts leave no empty box behind')

print_fn = between(NEW, 'function exportAnalyticsBrief(', 'w.document.close();')
check('the printed brief styles the lists too',
      '.an-brief-row' in print_fn and 'details{' in print_fn
      and 'summary{' in print_fn,
      'the print sheet carries the row and detail styles' if '.an-brief-row' in print_fn
      else 'the printed brief would show the rows as one run-on line')

label_fn = extract(NEW, 'function reportScopeLabel(')
check('reportScopeLabel() names a range from the applied scope',
      '__reportScope' in label_fn and 'REPORT_PERIOD_NAMES' in label_fn,
      'reads the applied scope only' if '__reportScope' in label_fn
      else 'does not read the applied scope')
check('reportScopeLabel() spells out both ends of a multi-day range',
      "' to '" in label_fn)
check('reportScopeLabel() reaches the selector ONLY when no scope has been applied yet',
      'if (!scope)' in label_fn and label_fn.index('__reportScope') < label_fn.index('.value'),
      'selector is a pre-load fallback' if 'if (!scope)' in label_fn else 'no fallback')

# ---------------------------------------------------------------------------
# 3. Picking a period on the Analytics tab actually applies it.
# ---------------------------------------------------------------------------
sel_at = NEW.index('id="anPeriod"')
# Wide enough for the whole control: the selector, its options and BOTH date boxes.
# (The `index('<select')` this replaces started looking at the id, which is already
# past the tag it wanted, and stopped 700 chars in -- half way through the date boxes.)
sel = NEW[sel_at - 40:sel_at + 1200]
check('the analytics period selector carries no pre-selected option',
      '<option value="today" selected' not in sel
      and re.search(r'<option[^>]*value="today"[^>]*\bselected\b', sel) is None,
      'no hard-coded `selected`' if 'selected' not in sel else 'a default is still set')
tag = re.search(r'<select[^<>]*onchange="onAnalyticsPeriodChange[^<>]*>', sel)
check('the analytics period selector applies on change',
      tag is not None,
      tag.group(0) if tag else 'the selector has no onchange')
check('the analytics date boxes apply on change too',
      count(sel, 'onAnalyticsDateChange') == 2,
      '%d onAnalyticsDateChange handlers' % count(sel, 'onAnalyticsDateChange'))

sys_edit = extract(NEW, 'function syncAnalyticsScope(')
ap = extract(NEW, 'function applyAnalyticsPeriod(')
check('syncAnalyticsScope() mirrors the applied scope back onto the selector',
      "getElementById('anPeriod')" in sys_edit
      and 'anP.value' in sys_edit and 'scope.period' in sys_edit,
      'points the selector at scope.period'
      if 'scope.period' in sys_edit else 'does not sync the selector')
check('loadSalesReport() calls syncAnalyticsScope()',
      'syncAnalyticsScope(' in load)
check('the analytics period applies with ONE filter pass (no second fetch)',
      'loadSalesReport(' in ap and 'updateReportDateRange(false)' in ap,
      'loadSalesReport + updateReportDateRange(false)'
      if 'updateReportDateRange(false)' in ap else 'updateReportDateRange(false) missing')
check('applyAnalyticsPeriod() refuses a half-filled custom range',
      '!s.value' in ap and '!e.value' in ap,
      'guards on the date boxes' if '!s.value' in ap and '!e.value' in ap
      else 'no guard on the date boxes')
check('applyAnalyticsPeriod() refuses a backwards range',
      's.value > e.value' in ap,
      'checks the ends are in order' if 's.value > e.value' in ap else 'no order check')

picker = extract(NEW, 'function onAnalyticsDateChange(')
check('a custom date applies as soon as both ends are filled',
      'applyAnalyticsPeriod(' in picker,
      'calls applyAnalyticsPeriod()' if 'applyAnalyticsPeriod(' in picker
      else 'waits for another click')



# ---------------------------------------------------------------------------
# 4. The brief names a day on the shop's clock, and an empty period says so.
# ---------------------------------------------------------------------------
UTC_KEY = "toISOString().split('T')[0]"
check('no UTC day key is left in the page (%s)' % UTC_KEY,
      count(NEW, UTC_KEY) == 0, '%d left' % count(NEW, UTC_KEY))
check('the local-day key is what the page uses instead',
      count(NEW, 'toLocalISODate(') >= 15, '%d uses' % count(NEW, 'toLocalISODate('))

report_body = extract(NEW, 'function renderSalesReport(')
check('the report daily buckets are keyed on the shop clock',
      'toLocalISODate(' in report_body and 'dailyData[' in report_body,
      'toLocalISODate in the report daily pass')

analytics_body = extract(NEW, 'function renderAnalytics(')
an_daily = between(analytics_body, 'const dailySales = {};', 'if (bestDay) s.push(')
check('the analytics daily buckets are keyed on the shop clock',
      'toLocalISODate(' in an_daily,
      'toLocalISODate in the analytics daily pass' if 'toLocalISODate(' in an_daily
      else 'still a UTC key')
check('the brief names the strongest day readably, not as a raw key',
      'fmtDayLong(bestDay)' in brief, 'fmtDayLong(bestDay)')
check('the brief says which period its figures cover',
      "'Across ' + periodLabel" in brief and 'sale(s) for $' in brief,
      'the sentence opens with the applied period')

check('an empty period is written as empty, not left as the last period on screen',
      'the shop rang up no sales' in analytics_body,
      'renderAnalytics writes an empty brief instead of returning quietly')
empty_block = between(analytics_body, 'The period WAS applied and really traded nothing',
                      'const categorySales')
check('the empty brief still names the applied period',
      'reportScopeLabel()' in empty_block,
      'uses reportScopeLabel()' if 'reportScopeLabel()' in empty_block
      else 'does not name the period')
check("the empty page clears the previous period's figures",
      all(n in empty_block for n in ("'analyticsKpis'", "'analyticsIntel'",
                                     "'analyticsActions'", "'moversList'",
                                     "'topProductsListReport'", "'topProfitProductsList'")),
      'clears KPI / intel / action / mover / top-product containers')

nav = NEW[NEW.index("if (page === 'analytics')"):
          NEW.index("if (page === 'analytics')") + 600]
check('a first visit to Analytics draws the page on the data it just loaded',
      'loadSalesReport(' in nav and 'renderAnalytics()' in nav,
      'loadSalesReport(...).then(... renderAnalytics())' if 'then(' in nav
      else 'fetches but never draws')

# ---------------------------------------------------------------------------
# 5. What the committed page did, for context.
#    These three checks are what the bug looked like at HEAD -- the reason the
#    checks above read the way they do -- so they are reported while HEAD still
#    shows it. Once the fix is committed, HEAD no longer shows anything to compare
#    against (the working copy may then differ by anything at all), and saying so
#    is the honest result rather than calling the fixed page a failure.
# ---------------------------------------------------------------------------
if OLD is not None and OLD != NEW:
    try:
        old_analytics = extract(OLD, 'function renderAnalytics(')
    except ValueError:
        # The committed function cannot be brace-walked (its brief holds a regex
        # literal that reads as a quote), so take a bounded slice from the marker
        # instead. It is only searched for the one expression below, which is in it.
        old_analytics = OLD[OLD.index('function renderAnalytics('):][:40000]
    old_sel = ''
    if 'id="anPeriod"' in OLD:
        old_sel = OLD[OLD.index('id="anPeriod"'):OLD.index('id="anPeriod"') + 400]
    old_read_selector = "getElementById('anPeriod')" in old_analytics
    old_preset = bool(re.search(r'<option[^>]*value="today"[^>]*\bselected\b', old_sel)
                      or 'selected' in old_sel)
    old_utc = count(OLD, UTC_KEY) >= 2
    if old_read_selector or old_preset or old_utc:
        check("the committed brief took its period from the analytics selector",
              old_read_selector,
              "the words and the figures could disagree at HEAD: %s"
              % ("the brief read the analytics selector's own option text"
                 if old_read_selector
                 else 'the committed brief already used an applied scope'))
        check('the committed analytics selector was pre-set to a period nobody applied',
              old_preset,
              'a hard-coded default sat on the selector at HEAD')
        check('the committed page keyed days by UTC in more than one place',
              old_utc,
              '%d UTC day keys at HEAD, %d now'
              % (count(OLD, UTC_KEY), count(NEW, UTC_KEY)))
    else:
        check('the fix is committed, so HEAD holds no earlier page to compare against',
              True,
              'HEAD already applies its scope, pre-selects nothing and keys days on '
              'the shop clock; the working copy differs from it only by the lists the '
              'brief now carries (%d chars)' % (len(NEW) - len(OLD)))
elif OLD is not None:
    check('baseline is identical to the working copy (this change is committed)', True)


# ---------------------------------------------------------------------------
# 6. The page, driven for real. Stand-in POS answers, built around the shop's own
#    clock: two sales TODAY (one at 00:30, one at 17:00 -- the early one is the
#    sale a UTC day key files under yesterday), a third on the 1st of the month
#    when that day is at least two back, and NOTHING yesterday, so an empty
#    period can be checked too.
# ---------------------------------------------------------------------------
SHOP_TZ = 'Africa/Harare'                    # what the browser below is pinned to
SHOP_TZINFO = timezone(timedelta(hours=2))   # Zimbabwe: UTC+2, all year, no DST
SHOP_NOW = datetime.now(timezone.utc).astimezone(SHOP_TZINFO)
DAY = SHOP_NOW.date()
MONTH_START = DAY.replace(day=1)
YESTERDAY = DAY - timedelta(days=1)
# JS getDay(): Sunday is 0. "This week" starts on the Sunday on or before today.
WEEK_START = DAY - timedelta(days=(DAY.weekday() + 1) % 7)
MONTH_SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
               'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
DAY_LONG = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']


def stamp(day, hour, minute):
    """A "now"-shaped timestamp on the shop's clock.

    GET /api/transactions sends created_at as a plain isoformat() -- the server's own
    clock, with no timezone suffix -- so this is the same shape. Like the real thing,
    it is the SHOP's clock the page has to read it with: the 00:30 sale below is the
    one a UTC-keyed day would file under yesterday.
    """
    return datetime(day.year, day.month, day.day, hour, minute, 0).isoformat()


def sale(number, day, hour, minute, items, total, category):
    """One transaction: items carry the line detail the brief's movers read.

    Every line carries `buy_price`, because that is what the page recomputes each
    sale's profit and the margin from. An item without it reads as zero cost, and
    every sale in the brief would show a 100% margin.
    """
    return {
        'transaction_number': number,
        'created_at': stamp(day, hour, minute),
        'total': total,
        'profit': round(sum((p - c) * q for n, q, p, c in items), 2),
        'subtotal': total,
        'payment_method': 'Cash',
        'status': 'completed',
        'items': [{'product_name': n, 'quantity': q, 'price': p, 'cost_price': c,
                   'buy_price': c, 'category': category, 'subtotal': p * q}
                  for n, q, p, c in items],
    }


# Two sales TODAY: one half an hour into the shop's day (the sale a UTC day key
# files under yesterday) and one in the afternoon.
TODAY_SALES = [
    sale('T-0001', DAY, 0, 30, [('Cement 50kg', 5, 15.0, 9.0)], 75.0, 'DIY'),
    sale('T-0002', DAY, 17, 0, [('Roof Paint 5L', 2, 15.0, 9.12)], 30.0, 'DIY'),
]
# One sale earlier in the month -- only when it is at least two days back, so that
# a longer period has something extra to show while YESTERDAY stays empty (the
# empty-period step below needs a day that really rang up nothing).
EARLIER_SALES = []
if DAY - MONTH_START >= timedelta(days=2):
    EARLIER_SALES = [sale('T-0000A', MONTH_START, 11, 0,
                          [('Cement 50kg', 2, 10.0, 6.0)], 20.0, 'DIY')]

STUB_TXNS = TODAY_SALES + EARLIER_SALES
STUB_DATES = [datetime.fromisoformat(t['created_at']).date() for t in STUB_TXNS]


def revenue_on(first, last):
    """What a period starting at `first` and ending at `last` must total (shop clock)."""
    return round(sum(t['total'] for t in STUB_TXNS
                     if first <= datetime.fromisoformat(t['created_at']).date() <= last), 2)


TODAY_REV = revenue_on(DAY, DAY)
MONTH_REV = revenue_on(MONTH_START, DAY)
WEEK_REV = revenue_on(WEEK_START, DAY)
CUSTOM_REV = revenue_on(MONTH_START, YESTERDAY)          # used when EARLIER_SALES exist


def fmt_day(d):
    """The page's fmtDay(): \"7 Oct 2026\"."""
    return '%d %s %d' % (d.day, MONTH_SHORT[d.month - 1], d.year)


def fmt_day_long(d):
    """The page's fmtDayLong(): \"Wednesday, 7 Oct 2026\"."""
    return DAY_LONG[d.weekday()] + ', ' + fmt_day(d)


TODAY_LABEL = 'Today (%s)' % fmt_day(DAY)
MONTH_LABEL = ('This month (%s)' % fmt_day(MONTH_START)) if MONTH_START == DAY \
    else ('This month (%s to %s)' % (fmt_day(MONTH_START), fmt_day(DAY)))
WEEK_LABEL = ('This week (%s)' % fmt_day(WEEK_START)) if WEEK_START == DAY \
    else ('This week (%s to %s)' % (fmt_day(WEEK_START), fmt_day(DAY)))
CUSTOM_LABEL = ('Custom range (%s)' % fmt_day(MONTH_START)) if MONTH_START == YESTERDAY \
    else ('Custom range (%s to %s)' % (fmt_day(MONTH_START), fmt_day(YESTERDAY)))

# Stock for the movers panel: two lines that sell and -- more of them than that
# panel cares to show -- lines that hold stock and never move. The movers panel
# lists the top 8 of those; the brief's list has to name every one of them, so
# there is deliberately one more than the panel can show, and the line that sorts
# last ('Garden Fork') is the one to look for in the brief and NOT in the panel.
STUB_PRODUCTS = [
    {'id': 11, 'name': 'Cement 50kg', 'category': 'DIY', 'stock': 40, 'sell_price': 15.0,
     'buy_price': 9.0, 'unit_type': 'bag', 'unit_details': '50kg', 'low_stock': False,
     'barcode': '111'},
    {'id': 13, 'name': 'Roof Paint 5L', 'category': 'DIY', 'stock': 6, 'sell_price': 18.0,
     'buy_price': 11.0, 'unit_type': 'tin', 'unit_details': '5L', 'low_stock': False,
     'barcode': '222'},
    {'id': 14, 'name': 'Garden Fork', 'category': 'DIY', 'stock': 9, 'sell_price': 22.0,
     'buy_price': 14.0, 'unit_type': 'piece', 'unit_details': '', 'low_stock': False,
     'barcode': '333'},
]
STUB_PRODUCTS += [
    {'id': 20 + i, 'name': 'Shelf Warmer %02d' % i, 'category': 'Hardware',
     'stock': 30 - i, 'sell_price': 12.0, 'buy_price': 8.0, 'unit_type': 'piece',
     'unit_details': '', 'low_stock': False, 'barcode': '9%03d' % i}
    for i in range(1, 10)
]

# The two lines the stand-in sales actually ring up, so everything else is stock
# that sat still in every period the run selects.
SOLDS = ('Cement 50kg', 'Roof Paint 5L')
DEAD_STOCK = [p for p in STUB_PRODUCTS if p['name'] not in SOLDS]
DEAD_N = len(DEAD_STOCK)                       # what the brief's sentence counts
DEAD_CASH = round(sum(p['stock'] * p['buy_price'] for p in DEAD_STOCK), 2)
NEVER_SOLD = 'Garden Fork'                     # sorts last: beyond the panel's top 8
NEVER_SOLD_STOCK = next(p['stock'] for p in STUB_PRODUCTS if p['name'] == NEVER_SOLD)
NEVER_SOLD_HELD = round(next(p['stock'] * p['buy_price'] for p in STUB_PRODUCTS
                             if p['name'] == NEVER_SOLD), 2)


def money(v):
    """The page's number shape for an amount -- its overridden .toFixed(2).

    pos-system.html replaces Number.prototype.toFixed app-wide, so every amount it
    prints comes out as ###,###.## -- which is why a stock figure of $1,926 is read
    back off the page with its comma. This returns that shape without a symbol;
    call sites add the '$' where the page prints one.
    """
    whole, _, cents = ('%.2f' % round(float(v), 2)).partition('.')
    sign = '-' if whole.startswith('-') else ''
    return sign + re.sub(r'\B(?=(\d{3})+(?!\d))', ',', whole.lstrip('-')) + '.' + cents


BRANCH = {'id': 1, 'code': 'POS', 'name': 'Shop', 'read_only': False}


class Handler(SimpleHTTPRequestHandler):
    """Serves the real page, and stands in for the POS APIs it asks for.

    Shapes are copied from the Flask routes (GET /api/transactions and friends), so the
    code under test runs unmodified: the page is not being rewritten to suit the test.
    """

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def log_message(self, *a):
        pass                                          # keep the console quiet

    def _json(self, payload, code=200):
        body = json.dumps(payload).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('X-Scope-Run', RUN_TOKEN)     # says which copy answered
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def _page(self):
        body = (ROOT / TEMPLATE).read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('X-Scope-Run', RUN_TOKEN)     # says which copy answered
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        if path in ('/', '/pos-system.html', '/pos-system'):
            return self._page()
        if path == '/api/check-auth':
            return self._json({'authenticated': True, 'branch': BRANCH,
                               'needs_branch': False,
                               'user': {'id': 1, 'name': 'Administrator',
                                        'role': 'admin'}})
        if path == '/api/transactions':
            return self._json({'success': True, 'transactions': STUB_TXNS})
        if path == '/api/stock-additions':
            return self._json({'success': True, 'additions': []})
        if path == '/api/products':
            return self._json({'success': True, 'products': STUB_PRODUCTS,
                               'total': len(STUB_PRODUCTS)})
        if path == '/api/categories':
            return self._json({'success': True, 'categories': [{'id': 1, 'name': 'DIY'},
                                                               {'id': 2, 'name': 'Electricals'}]})
        if path == '/api/branches':
            return self._json({'success': True, 'branches': [BRANCH],
                               'all_branches': {'id': 0, 'name': 'All Branches'}})
        if path == '/api/dashboard-stats':
            return self._json({'success': True, 'today_sales': TODAY_REV,
                               'items_sold': sum(i['quantity'] for t in TODAY_SALES
                                                 for i in t['items']),
                               'low_stock_count': 0,
                               'total_products': len(STUB_PRODUCTS),
                               'total_profit': round(sum(t['profit'] for t in TODAY_SALES), 2)})
        if path == '/api/laybys':
            return self._json({'success': True, 'laybys': []})
        if path.startswith('/api/'):
            return self._json({'success': True})       # nothing else here is under test
        return super().do_GET()                        # /static/... off the disk

    def do_POST(self):
        return self._json({'success': True})           # nothing here writes anything

    do_PUT = do_DELETE = do_POST


def serve():
    httpd = ThreadingHTTPServer(('127.0.0.1', PORT), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


from playwright.sync_api import sync_playwright                      # noqa: E402

BASE = 'http://127.0.0.1:%d' % PORT

# Seeded before any page script runs: a till already signed in to one shop.
SEED = """(function () {
  try {
    localStorage.clear();
    localStorage.setItem('isLoggedIn', 'true');
    localStorage.setItem('posBranch', JSON.stringify({id: 1, name: 'Shop', read_only: false}));
    localStorage.setItem('pos_branch_scope', '1');
  } catch (e) {}
})();"""

# The page is served without its CDNs, so Bootstrap's modal API and Chart.js are
# stubbed just enough for the page's own code to run to the end: without them the
# first showModal() or new Chart(...) throws and stops the script part way through
# the very rendering this check is about.
LIBRARY_STUB = """
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
  ['destroy', 'update', 'resize', 'reset', 'render', 'stop', 'clear'].forEach(function (m) {
    window.Chart.prototype[m] = function () {};
  });
  window.Chart.prototype.toBase64Image = function () { return ''; };
  window.Chart.prototype.getDatasetMeta = function () { return {data: []}; };
  window.Chart.defaults = {font: {}, plugins: {}, color: '#000', borderColor: '#000',
                           devicePixelRatio: 1, animation: false, responsive: true};
  window.Chart.register = function () {};
  window.Chart.getChart = function () { return null; };
  window.Chart.version = 'stub';
}
"""

httpd = serve()
# A real probe, not a label: the check has to say that the server answering on PORT
# is THIS run's, because the browser will be sent to whatever copy answers there.
# http.client, not urllib: urllib honours proxy environment variables, so with a
# proxy configured it asks the proxy to fetch 127.0.0.1 and reports the proxy's own
# error instead of the page. A direct connection is the only honest probe here.
try:
    _conn = http.client.HTTPConnection('127.0.0.1', PORT, timeout=10)
    try:
        _conn.request('GET', PAGE_PATH)
        _resp = _conn.getresponse()
        _answered_by, _status = _resp.getheader('X-Scope-Run'), _resp.status
    finally:
        _conn.close()
    _served_by_us = _answered_by == RUN_TOKEN and _status == 200
    _probe_note = 'HTTP %s, answered by run %s' % (_status, _answered_by or '?')
except Exception as _probe_exc:                                            # noqa: BLE001
    _served_by_us = False
    _probe_note = '%s: %s' % (type(_probe_exc).__name__, _probe_exc)
check("the stand-in POS server is up, and is this run's own", _served_by_us,
      _probe_note if _served_by_us
      else 'port %d: %s -- this run is %s, so the browser may be talking to another '
           'copy of the script' % (PORT, _probe_note, RUN_TOKEN))


def read_analytics(page):
    """What the Analytics tab is showing, read off the page itself."""
    return page.evaluate("""() => {
        const txt = id => {
            const el = document.getElementById(id);
            return el ? el.innerText.replace(/\\s+/g, ' ').trim() : '';
        };
        const scope = window.__reportScope;
        return {
            onScreen: document.getElementById('analyticsPage').style.display,
            analyticsPeriod: document.getElementById('anPeriod').value,
            reportPeriod: document.getElementById('reportPeriod').value,
            applied: scope ? scope.period : null,
            label: reportScopeLabel(),
            brief: txt('analyticsBrief'),
            kpis: txt('analyticsKpis')
        };
    }""")


def read_brief_boxes(page):
    """The brief's expandable lists: what they say, and whether they are open.

    `shown` counts the rows whose text is really rendered. A row height cannot stand
    in for that: in this Chromium the rows of a SHUT <details> still report a
    non-zero rect, while their text is not rendered at all, so innerText is the
    honest signal for "the operator is looking at these rows".
    """
    return page.evaluate("""() => Array.from(
        document.querySelectorAll('#analyticsBrief details.an-brief-items')
    ).map(d => {
        const rows = Array.from(d.querySelectorAll('.an-brief-row'));
        const head = d.querySelector('summary');
        return {
            tone: d.classList.contains('dead') ? 'dead'
                  : (d.classList.contains('slow') ? 'slow' : ''),
            open: d.open === true,
            head: head ? head.innerText.replace(/\\s+/g, ' ').trim() : '',
            rows: rows.map(r => r.innerText.replace(/\\s+/g, ' ').trim()),
            shown: rows.filter(r => r.innerText.trim() !== '').length
        };
    })""")


def settle(page, period, needle, timeout=25000):
    """Wait until `period` has really been applied AND the brief says `needle`.

    Both halves matter: the brief is written from the fetched data, so a run that
    waited only for the period would read the previous period's sentence under it.
    """
    page.wait_for_function(
        """([period, needle]) => {
            const b = document.getElementById('analyticsBrief');
            const l = document.getElementById('globalLoader');
            const busy = l && getComputedStyle(l).display !== 'none';
            const applied = window.__reportScope && window.__reportScope.period === period;
            const named = !!b && b.innerText.replace(/\\s+/g, ' ').indexOf(needle) >= 0;
            return applied && named && !busy;
        }""", arg=[period, needle], timeout=timeout)


def strongest_day(brief):
    m = re.search(r'The strongest trading day was ([^(.]+)', brief)
    return m.group(1).strip() if m else ''


def count_on(first, last):
    return sum(1 for d in STUB_DATES if first <= d <= last)


errors = []
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context(timezone_id=SHOP_TZ,
                                  viewport={'width': 1440, 'height': 900})
        ctx.add_init_script(LIBRARY_STUB)
        ctx.add_init_script(SEED)
        page = ctx.new_page()
        page.set_default_timeout(20000)
        page.on('pageerror', lambda e: errors.append(str(e)[:160]))
        # No external network: the CDN libraries are irrelevant here (Bootstrap's
        # modal API and Chart.js are stubbed) and reaching for them would only make
        # the run slow and flaky.
        page.route(re.compile(r'https?://(?!127\.0\.0\.1)'), lambda r: r.abort())

        page.goto(BASE + PAGE_PATH, wait_until='domcontentloaded', timeout=30000)
        page.wait_for_function(
            "typeof navigateTo === 'function'"
            " && typeof reportScopeLabel === 'function'", timeout=25000)
        check('the real page loads in a real browser', True, BASE + PAGE_PATH)
        check("the browser is on the shop's clock",
              page.evaluate('Intl.DateTimeFormat().resolvedOptions().timeZone') == SHOP_TZ,
              page.evaluate('Intl.DateTimeFormat().resolvedOptions().timeZone'))

        # ---- Today, the way the operator gets there: the sidebar, first visit ----
        page.click('.menu-item[data-page="analytics"]')
        settle(page, 'today', 'Across ' + TODAY_LABEL + ' the shop rang up')
        today = read_analytics(page)
        check('a first visit to Analytics draws the tab on the data it just loaded',
              today['onScreen'] == 'block'
              and 'Across ' + TODAY_LABEL + ' the shop rang up' in today['brief'],
              'display=%s  %s' % (today['onScreen'], today['brief'][:150]))
        check("the brief's figures are the applied period's figures",
              '$%.2f in revenue' % TODAY_REV in today['brief']
              and '%d sale(s)' % count_on(DAY, DAY) in today['brief'],
              'today = $%.2f over %d sale(s)' % (TODAY_REV, count_on(DAY, DAY)))
        # The 00:30 sale is the trap: a UTC day key files it under yesterday, and
        # the brief would then name a day the shop never traded on.
        check("the day the brief names is the shop's day, not the UTC day",
              strongest_day(today['brief']) == fmt_day_long(DAY)
              and fmt_day_long(YESTERDAY) not in today['brief'],
              'strongest trading day: %r (a UTC key would say %r)'
              % (strongest_day(today['brief']), fmt_day_long(YESTERDAY)))
        check('the two selectors and the applied scope all read the same period',
              today['applied'] == today['analyticsPeriod'] == today['reportPeriod'] == 'today',
              'scope=%s analytics=%s sales=%s'
              % (today['applied'], today['analyticsPeriod'], today['reportPeriod']))

        # ---- The brief's counts, and the names behind them ----
        # "10 product(s) are holding stock but sold nothing this period" is only
        # actionable if the products are named, so the sentence is followed by the
        # list of what it counted: every one of them, in a box that opens on the
        # brief itself. The movers panel above shows the top 8 and stops, so the
        # line that sorts last (Garden Fork) is the one that tells the two apart.
        boxes = read_brief_boxes(page)
        by_tone = {b['tone']: b for b in boxes}
        panel = page.evaluate(
            "() => { const el = document.getElementById('moversList');"
            " return el ? el.textContent.replace(/\\s+/g, ' ') : ''; }")
        check('the "holding stock but sold nothing" sentence is followed by the '
              'products themselves',
              'dead' in by_tone
              and ('Show the %d product(s) holding stock' % DEAD_N)
              in by_tone['dead']['head']
              and ('$' + money(DEAD_CASH) + ' at cost') in by_tone['dead']['head'],
              'the box reads %r' % by_tone.get('dead', {}).get('head', '(no box at all)'))
        check('and the slow-moving line is followed by the lines themselves',
              'slow' in by_tone
              and 'Show the 1 line(s) that moved under 5 units' in by_tone['slow']['head'],
              'the box reads %r' % by_tone.get('slow', {}).get('head', '(no box at all)'))
        check('neither list puts itself in the way until it is asked for',
              len(boxes) == 2 and all(not b['open'] and b['shown'] == 0 for b in boxes)
              and NEVER_SOLD not in today['brief'],
              '%d box(es), %d open, %d row(s) rendered, and the shut rows stay out '
              'of the brief' % (len(boxes), sum(1 for b in boxes if b['open']),
                                sum(b['shown'] for b in boxes)))

        # The box is the operator's to open, and what it opens onto has to be the
        # whole list: every product the sentence counted, with what it is holding.
        dead_summary = '#analyticsBrief details.an-brief-items.dead > summary'
        page.click(dead_summary)
        page.wait_for_function(
            """() => {
                const d = document.querySelector('#analyticsBrief details.an-brief-items.dead');
                return !!d && d.open === true;
            }""", timeout=5000)
        dead = [b for b in read_brief_boxes(page) if b['tone'] == 'dead'][0]
        check('opening it shows one row for every product the sentence counted',
              dead['open'] and dead['shown'] == DEAD_N and len(dead['rows']) == DEAD_N,
              '%d of %d row(s) rendered, open=%s'
              % (dead['shown'], len(dead['rows']), dead['open']))
        check('and it names the products the movers panel above leaves out, rather '
              'than the same 8',
              any(NEVER_SOLD in r for r in dead['rows'])
              and NEVER_SOLD not in panel and 'Shelf Warmer 01' in panel,
              'the brief names %r at row %d of %d; the panel shows the top %d and stops'
              % (NEVER_SOLD, DEAD_N, DEAD_N, MOVERS_SHOW))
        check('each listed product shows what it holds and what that stock is worth',
              any(NEVER_SOLD in r and ('%d in stock' % NEVER_SOLD_STOCK) in r
                  and ('$' + money(NEVER_SOLD_HELD)) in r for r in dead['rows']),
              'expected a row reading "%s ... %d in stock $%s"; the last one reads %r'
              % (NEVER_SOLD, NEVER_SOLD_STOCK, money(NEVER_SOLD_HELD), dead['rows'][-1:]))

        # The slow-moving box opens onto the lines themselves: what each moved, and
        # what is still on the shelf behind it.
        page.click('#analyticsBrief details.an-brief-items.slow > summary')
        page.wait_for_function(
            """() => {
                const d = document.querySelector('#analyticsBrief details.an-brief-items.slow');
                return !!d && d.open === true;
            }""", timeout=5000)
        slow = [b for b in read_brief_boxes(page) if b['tone'] == 'slow'][0]
        check('the slow-moving box opens onto the lines that moved under 5 units',
              any('Roof Paint 5L' in r and '2 sold' in r and '6 in stock' in r
                  for r in slow['rows']),
              'slow rows: %r' % slow['rows'])

        # Shut again, and the brief is back to being one paragraph with a count in it.
        page.click(dead_summary)
        page.click('#analyticsBrief details.an-brief-items.slow > summary')
        page.wait_for_function(
            """() => Array.from(
                document.querySelectorAll('#analyticsBrief details.an-brief-items')
            ).every(d => d.open === false)""", timeout=5000)
        shut = read_brief_boxes(page)
        check('both shut again, leaving the brief reading as it did',
              len(shut) == 2 and all(not b['open'] and b['shown'] == 0 for b in shut)
              and NEVER_SOLD not in read_analytics(page)['brief'],
              '%d box(es), %d still open, %d row(s) rendered'
              % (len(shut), sum(1 for b in shut if b['open']),
                 sum(b['shown'] for b in shut)))

        # ---- This month, picked on the Analytics tab ----
        page.select_option('#anPeriod', 'month')
        settle(page, 'month', 'Across ' + MONTH_LABEL + ' the shop rang up')
        month = read_analytics(page)
        check('picking a period on the Analytics tab applies it at once, and the brief '
              'names it',
              'Across ' + MONTH_LABEL + ' the shop rang up' in month['brief'],
              month['brief'][:170])
        check("and the month's money is the month's, not a single day's",
              '$%.2f in revenue' % MONTH_REV in month['brief']
              and '%d sale(s)' % count_on(MONTH_START, DAY) in month['brief'],
              'month = $%.2f over %d sale(s)'
              % (MONTH_REV, count_on(MONTH_START, DAY)))
        if EARLIER_SALES:
            check('the shorter period it came from is no longer quoted, so the words '
                  'and the figures moved together',
                  '$%.2f in revenue' % TODAY_REV not in month['brief'],
                  'today $%.2f is gone from a month brief' % TODAY_REV)
        check('the Analytics choice is the same scope the Sales Report is on',
              month['reportPeriod'] == 'month' and month['applied'] == 'month',
              'sales selector=%s applied=%s' % (month['reportPeriod'], month['applied']))

        # ---- This week ----
        page.select_option('#anPeriod', 'week')
        settle(page, 'week', 'Across ' + WEEK_LABEL + ' the shop rang up')
        week = read_analytics(page)
        check('changing the period again moves the words and the money together',
              'Across ' + WEEK_LABEL + ' the shop rang up' in week['brief']
              and '$%.2f in revenue' % WEEK_REV in week['brief'],
              'week = $%.2f over %d sale(s)'
              % (WEEK_REV, count_on(WEEK_START, DAY)))
        earlier_in_week = any(WEEK_START <= d < DAY for d in STUB_DATES)
        if earlier_in_week:
            check("the week's own total is not simply today's",
                  '$%.2f in revenue' % TODAY_REV not in week['brief'],
                  "today's $%.2f dropped from the week's total" % TODAY_REV)
        else:
            check('the week holds nothing but today here, so its total is the day\'s',
                  WEEK_REV == TODAY_REV, 'week = today = $%.2f' % WEEK_REV)

        # ---- Custom range: the half-chosen state, then the dates ----
        page.select_option('#anPeriod', 'custom')
        page.wait_for_timeout(500)
        half = read_analytics(page)
        # Reproducing the original bug as a step: the selector now says Custom while
        # the figures below it are the week's. Naming that choice would be a lie.
        check('a half-made choice does not get named in the brief',
              'Across ' + WEEK_LABEL + ' the shop rang up' in half['brief']
              and half['applied'] == 'week',
              'selector=%s but the figures are still %s'
              % (half['analyticsPeriod'], half['applied']))
        if EARLIER_SALES:
            page.fill('#anStartDate', MONTH_START.isoformat())
            page.fill('#anEndDate', YESTERDAY.isoformat())
            settle(page, 'custom', 'Across ' + CUSTOM_LABEL + ' the shop rang up')
            # Picking the two dates applies the range TWICE: the box that is not being
            # typed into is filled in from the scope the page is already on, so the
            # first date alone already applies a (too wide) range -- and the scope is
            # published before its fetch. The words can therefore be a moment ahead of
            # the figures, which is a reading artefact rather than the words/figures
            # disagreement this file is about. So wait for the custom range's own money
            # before judging it, and report a failure of its own if it never arrives.
            try:
                page.wait_for_function(
                    "([label, amount]) => {"
                    " const b = document.getElementById('analyticsBrief');"
                    " return !!b && b.innerText.indexOf(label) >= 0"
                    " && b.innerText.indexOf(amount) >= 0; }",
                    arg=['Across ' + CUSTOM_LABEL + ' the shop rang up',
                         '$%.2f in revenue' % CUSTOM_REV], timeout=20000)
            except Exception as exc:                                      # noqa: BLE001
                check('the custom range redrew its figures, not just its words', False,
                      '%s: the brief still reads %r'
                      % (type(exc).__name__, read_analytics(page)['brief'][:140]))
            custom = read_analytics(page)
            check('once the dates are picked the brief follows the dates that were applied',
                  'Across ' + CUSTOM_LABEL + ' the shop rang up' in custom['brief'],
                  custom['brief'][:170])
            check("and the custom range's money is its own",
                  '$%.2f in revenue' % CUSTOM_REV in custom['brief'],
                  'custom ($%.2f over %d sale(s)) is not today ($%.2f)'
                  % (CUSTOM_REV, count_on(MONTH_START, YESTERDAY), TODAY_REV))
            check('a custom range moves the Sales Report onto the same dates',
                  custom['reportPeriod'] == 'custom' and custom['applied'] == 'custom',
                  'sales selector=%s applied=%s' % (custom['reportPeriod'], custom['applied']))
        else:
            check('nothing earlier than today exists in this month, so there is no '
                  'custom range to select (skipped, with the reason)',
                  MONTH_START > YESTERDAY,
              'today is day %d of the month, so no custom range exists' % DAY.day)

        # ---- Yesterday, a day the shop really did not trade ----
        before_empty = read_analytics(page)
        page.select_option('#anPeriod', 'yesterday')
        settle(page, 'yesterday', 'the shop rang up no sales')
        empty = read_analytics(page)
        check('a period that traded nothing says so instead of leaving the last '
              "period's brief up",
              'Across Yesterday (' + fmt_day(YESTERDAY) + ') the shop rang up no sales.'
              in empty['brief'], empty['brief'][:170])
        check("the previous period's figures go with it, so no stale money is left "
              'under the new period',
              before_empty['kpis'].strip() != '' and empty['kpis'].strip() == ''
              and '$' not in empty['brief'],
              'kpis were %r, now %r' % (before_empty['kpis'][:60], empty['kpis'][:60]))

        # ---- Changed on the Sales Report, then read back here ----
        # The brief must describe the period that is now applied, not the one this
        # tab's selector happened to be left on. The Sales Report's own selector only
        # exists while that page is on screen, so go there to change the period.
        page.click('.menu-item[data-page="sales"]')
        page.select_option('#reportPeriod', 'today')
        page.wait_for_function(
            "() => !!window.__reportScope && window.__reportScope.period === 'today'",
            timeout=20000)
        page.click('.menu-item[data-page="analytics"]')
        settle(page, 'today', 'Across ' + TODAY_LABEL + ' the shop rang up')
        back = read_analytics(page)
        check('after the period is changed on the Sales Report, coming back to the '
              'Analytics tab re-writes the brief for the period now applied',
              'Across ' + TODAY_LABEL + ' the shop rang up' in back['brief']
              and '$%.2f in revenue' % TODAY_REV in back['brief']
              and back['analyticsPeriod'] == 'today',
              'selector=%s applied=%s :: %s'
              % (back['analyticsPeriod'], back['applied'], back['brief'][:130]))
        check('no page script threw while all of that was driven',
              not errors, '; '.join(errors[:3]) or 'clean run')
except Exception as exc:                                               # noqa: BLE001
    check('the browser run reached the end', False,
          '%s: %s' % (type(exc).__name__, exc))
finally:
    try:
        httpd.shutdown()
    except Exception:                                                  # noqa: BLE001
        pass

print('\n'.join(RESULTS))
FAILURES = sum(1 for r in RESULTS if r.startswith('FAIL'))
print('\nFAILURES: %d' % FAILURES)
sys.exit(1 if FAILURES else 0)






