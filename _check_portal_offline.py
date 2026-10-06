"""Offline check for the portal's read-only offline copy.

The POS works with no connection because it QUEUES its sales and laybys. The
portal cannot: an edit there is a whole-row update the server judges (permissions,
read-only branch), so replaying one offline would quietly overwrite whatever
happened in the meantime. What the portal got instead is a READ-ONLY copy: a
small, named set of project figures and any contract the operator has kept, each
stamped with when it was saved, so the screen can say what it is really showing.

No database and no browser are needed here. What this checks, without either:

  1. static/js/sw.js and every <script> block in templates/adminpage.html still
     parse (esprima), and the page is compared against the COMMITTED page so a
     pre-existing quirk is not blamed on this change,
  2. only the named project endpoints may be saved and replayed -- matched on
     the WHOLE path (an anchored pattern, never a substring), never a money
     endpoint, and never a route that changes anything,
  3. a change (POST/PUT/DELETE) is never handled at all: the handler returns
     before it even looks at a URL,
  4. a copy handed out instead of the server's answer is marked as a copy and
     carries the time it was saved,
  5. both buckets are bounded (entries, plus bytes for contracts) and the entry
     just saved is never the one dropped,
  6. a contract is only ever kept when the server really answered 200 with a
     PDF -- a failure page can never become "the contract",
  7. the page says what it is showing: a banner quoting the saved time, a plain
     "Not Saved" when a change could not be sent, and nothing queued anywhere,
  8. the contract modal offers Save for offline and Delete saved copies, and
     logging out clears the copies (they carry client details, so they must not
     outlive the login that fetched them),
  9. and the POS behaviour is untouched (the shell, and /api/* still never
     cached in the runtime bucket).

Run:  python _check_portal_offline.py   (writes _check_portal_out.txt)
"""
import re
import subprocess
import sys

RESULTS = []
OUT = '_check_portal_out.txt'
SW = 'static/js/sw.js'
PAGE = 'templates/adminpage.html'


def _flush():
    """Write what we have so far, so a crash still leaves evidence."""
    try:
        with open(OUT, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(RESULTS) + '\n')
    except Exception:                                              # noqa: BLE001
        pass


def check(name, ok, detail=''):
    RESULTS.append(f"{'PASS' if ok else 'FAIL'}  {name}"
                   f"{('  -> ' + detail) if detail else ''}")
    _flush()


def read(path):
    with open(path, encoding='utf-8') as fh:
        return fh.read()


def committed(path):
    """The same file as committed, or None when git cannot say."""
    try:
        proc = subprocess.run(['git', 'show', 'HEAD:' + path],
                              capture_output=True)
    except Exception:                                              # noqa: BLE001
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.decode('utf-8', 'replace')


def script_blocks(src):
    """(page line of the body, body) for every INLINE <script> block."""
    out = []
    for m in re.finditer(r'<script\b[^>]*>(.*?)</script>', src, re.S | re.I):
        opener = src[m.start():src.index('>', m.start()) + 1]
        if re.search(r'\bsrc\s*=', opener):
            continue
        out.append((src.count('\n', 0, m.start(1)) + 1, m.group(1)))
    return out


def first_error(body):
    """esprima's first complaint about a script body, or (None, 0).

    `?.` is normalised to `.` first, exactly as the POS checker does: the
    console's esprima is an ES2017 parser and the page has used optional chaining
    since long before this change, so that one construct would otherwise hide
    every line after it.
    """
    try:
        import esprima
    except Exception as exc:                                       # noqa: BLE001
        return 'no-parser: %s' % exc, 0
    try:
        esprima.parseScript(body.replace('?.', '.'))
        return None, 0
    except Exception as exc:                                       # noqa: BLE001
        return getattr(exc, 'message', str(exc)), getattr(exc, 'lineNumber', 0)


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


def list_literal(src, name):
    """The body of `const NAME = [ ... ];`."""
    m = re.search(r'const\s+' + re.escape(name) + r'\s*=\s*\[(.*?)\];',
                  src, re.S)
    return m.group(1) if m else ''


def quoted(text):
    return re.findall(r"'([^']*)'", text)


def const_int(src, name):
    m = re.search(r'const\s+' + re.escape(name) + r'\s*=\s*([0-9]+)', src)
    return int(m.group(1)) if m else -1


def anchored_patterns(src):
    """Every `/^...$/` literal in a source file, with \\/ unescaped."""
    return [b.replace('\\/', '/') for b in re.findall(r'/(\^.+?\$)/', src)]


check('script started', True)

try:
    SW_SRC = read(SW)
    check('read the service worker', True, '%d chars' % len(SW_SRC))
except Exception as exc:                                           # noqa: BLE001
    check('read the service worker', False, f'{type(exc).__name__}: {exc}')
    print('\n'.join(RESULTS))
    print('\nFAILURES: %d' % sum(1 for r in RESULTS if r.startswith('FAIL')))
    sys.exit(1)

try:
    PAGE_SRC = read(PAGE)
    check('read the portal page', True, '%d chars' % len(PAGE_SRC))
except Exception as exc:                                           # noqa: BLE001
    check('read the portal page', False, f'{type(exc).__name__}: {exc}')
    print('\n'.join(RESULTS))
    print('\nFAILURES: %d' % sum(1 for r in RESULTS if r.startswith('FAIL')))
    sys.exit(1)

OLD_SW = committed(SW)
OLD_PAGE = committed(PAGE)


# ---------- 1. everything still parses ----------
_sw_err, _sw_line = first_error(SW_SRC)
check('the service worker is syntactically valid', _sw_err is None, str(_sw_err))

new_blocks = script_blocks(PAGE_SRC)
old_blocks = script_blocks(OLD_PAGE) if OLD_PAGE else []
check('the page still has its script blocks',
      len(new_blocks) == len(old_blocks) and len(new_blocks) >= 4,
      'new=%d old=%d' % (len(new_blocks), len(old_blocks)))

worse = []
for i, (start, body) in enumerate(new_blocks):
    msg_new, line_new = first_error(body)
    if msg_new is None:
        continue
    msg_old = first_error(old_blocks[i][1])[0] if i < len(old_blocks) else None
    if msg_old != msg_new:
        lines = body.splitlines()
        snippet = lines[line_new - 1].strip()[:70] if 0 < line_new <= len(lines) else ''
        worse.append('block %d at page line %d: %s  |%s|'
                     % (i, start + line_new - 1, msg_new, snippet))
check('no script block gained a syntax error (vs the committed page)',
      not worse, '; '.join(worse[:3]))


# ---------- 2. the read-only whitelist ----------
_old_ver = re.search(r"const CACHE_VERSION = '(\w+)'", OLD_SW) if OLD_SW else None
check('the cache version was bumped, so a stale worker cannot survive the deploy',
      "const CACHE_VERSION = 'v3';" in SW_SRC
      and (not _old_ver or _old_ver.group(1) != 'v3'),
      'was: ' + (_old_ver.group(1) if _old_ver else '?'))

READS = quoted(list_literal(SW_SRC, 'READ_ENDPOINTS'))
EXPECTED = ['/get_project_count', '/get_project_months',
            '/get_project_start_months', '/api/projects-page']
check('exactly the named project endpoints may be replayed offline',
      sorted(READS) == sorted(EXPECTED), str(READS))
check('the named endpoints are matched exactly, never as a substring',
      'READ_ENDPOINTS.indexOf(pathname) !== -1'
      in extract(SW_SRC, 'function offlineBucket(pathname) {'))

PATS = anchored_patterns(SW_SRC)
check('the id-carrying read endpoints are anchored on the whole path',
      '^/get_project/\\d+$' in PATS and '^/api/project/\\d+/has-gantt$' in PATS,
      str(PATS))
check('the contract pattern is anchored on the whole path',
      '^/download_contract/\\d+$' in PATS)
check('a receipt route is not treated as a document (they are POSTs)',
      not [p for p in PATS if 'receipt' in p])
EVERY = READS + PATS
check('no money endpoint is readable offline (nor anywhere in the worker)',
      not [p for p in EVERY if 'overcost' in p] and 'overcost' not in SW_SRC)
check('no route that changes something is in any bucket',
      not [p for p in EVERY if any(k in p.lower() for k in
                                   ('update', 'save', 'delete', 'create',
                                    'export', 'logout', 'send'))],
      str(EVERY))
check('the bucket is chosen from the path, never the whole href',
      'offlineBucket(url.pathname)' in SW_SRC)
check('a saved copy is only ever handed back for this app\'s own origin',
      'url.origin === self.location.origin' in SW_SRC)


# ---------- 3. nothing that changes anything is ever handled ----------
FETCH = SW_SRC[SW_SRC.index("self.addEventListener('fetch'"):]
_GUARD = FETCH.index("if (event.request.method !== 'GET') return;")
check('anything but GET is dropped before the URL is even looked at',
      _GUARD < FETCH.index('let url;'))
check('...and before any response is decided', _GUARD < FETCH.index('respondWith'))
check('the two read-only buckets are settled before the static-file gate',
      FETCH.index("bucket === 'read'") < FETCH.index('isCacheableRequest(url)')
      and FETCH.index("bucket === 'doc'") < FETCH.index('isCacheableRequest(url)'))
check('a contract link is settled before the page-shell branch',
      FETCH.index("bucket === 'doc'") < FETCH.index("mode === 'navigate'"))
check('the old rule still stands: /api/* is never cached in the runtime bucket',
      "url.pathname.startsWith('/api/')" in SW_SRC)
check('/webhook is still refused outright',
      "url.pathname.startsWith('/webhook')" in SW_SRC)
check('the worker keeps no queue of changes of its own',
      'indexedDB' not in SW_SRC and 'localStorage' not in SW_SRC)
check('the POS shell is still installed and still answers a POS navigation',
      'new Request(POS_SHELL' in SW_SRC
      and 'isPosUrl(url) ? POS_SHELL : null' in SW_SRC)


# ---------- 4. a copy handed out describes itself ----------
MARK = extract(SW_SRC, 'function withOfflineMark(response, savedAt) {')
check('a copy served instead of the server\'s answer is marked as a copy',
      "headers.set(OFFLINE_FLAG, '1')" in MARK)
STORE = extract(SW_SRC, 'async function storeWithStamp(cache, request, response) {')
check('the saved copy carries the time it was saved',
      'headers.set(SAVED_AT, String(Date.now()))' in STORE
      and STORE.index('headers.set(SAVED_AT') < STORE.index('cache.put('))
check('a replay of saved figures says when it was saved',
      'withOfflineMark(cached, cached.headers.get(SAVED_AT))'
      in extract(SW_SRC, 'async function readNetworkFirst(request) {'))
check('a replay of a saved contract says when it was saved',
      'withOfflineMark(cached, cached.headers.get(SAVED_AT))'
      in extract(SW_SRC, 'async function docNetworkFirst(request) {'))
READ = extract(SW_SRC, 'async function readNetworkFirst(request) {')
check('with no copy at all, a read is refused rather than answered empty',
      'offline_no_copy' in READ and 'status: 503' in READ)
DOC = extract(SW_SRC, 'async function docNetworkFirst(request) {')
check('with no copy at all, a contract is refused with instructions',
      'has not been saved on this' in DOC and 'status: 503' in DOC)
check('a contract is only kept when the server really answered with a PDF',
      'response.status === 200' in DOC
      and "indexOf('application/pdf') !== -1" in DOC)


# ---------- 5. both buckets are bounded ----------
check('the read bucket is bounded', const_int(SW_SRC, 'READ_MAX_ENTRIES') > 0,
      str(const_int(SW_SRC, 'READ_MAX_ENTRIES')))
BYTES = re.search(r'const\s+DOC_MAX_BYTES\s*=\s*([^;]+);', SW_SRC)
check('the contract bucket is bounded by count AND by bytes',
      const_int(SW_SRC, 'DOC_MAX_ENTRIES') > 0 and bool(BYTES),
      '%d entries / max %s bytes' % (const_int(SW_SRC, 'DOC_MAX_ENTRIES'),
                                     BYTES.group(1).strip() if BYTES else '?'))
TRIM = extract(SW_SRC, 'async function trimCache(cache, justStoredUrl, maxEntries, maxBytes) {')
check('trimming drops the oldest first', 'entries.sort((a, b) => a.at - b.at)' in TRIM)
check('trimming never drops the copy just saved', 'if (e.newest) continue;' in TRIM)
check('trimming is applied to both buckets',
      'trimCache(cache, request.url, READ_MAX_ENTRIES, 0)' in SW_SRC
      and 'trimCache(cache, request.url, DOC_MAX_ENTRIES, DOC_MAX_BYTES)' in SW_SRC)
check('the read and contract buckets are only written through storeWithStamp',
      SW_SRC.count('caches.open(READ_CACHE)') == 1
      and SW_SRC.count('caches.open(DOC_CACHE)') == 1
      and SW_SRC.count('storeWithStamp(') == 3)
check('the runtime bucket still saves exactly what it did before',
      'cache.put(request, response.clone())' in SW_SRC)


# ---------- 6. the page says what it is showing ----------
_BANNER = re.search(r'<div id="clOfflineBanner"[^>]*>.*?</div>', PAGE_SRC, re.S)
check('the page has an offline banner, hidden until it is needed',
      bool(_BANNER) and 'display:none' in _BANNER.group(0))
MARKP = extract(PAGE_SRC, 'function clOfflineMark(savedMs) {')
check('the banner quotes the time the copy on screen was saved',
      'clClock(CL_OLDEST_SAVED)' in MARKP and 'saved on this device at' in MARKP)
check('and says plainly that nothing can be sent or saved',
      'Nothing here can be sent or saved' in MARKP)
check('and the copy quoted is the OLDEST one shown, never a fresher one',
      'savedMs < CL_OLDEST_SAVED' in MARKP)
CLEAR = extract(PAGE_SRC, 'function clOfflineClear() {')
check('a live answer takes the notice away',
      "clBanner('')" in CLEAR and 'CL_OLDEST_SAVED = 0' in CLEAR)
NOSAVE = extract(PAGE_SRC, 'function clNothingSaved() {')
check('a change that could not be sent says it was not saved',
      'Nothing was saved and nothing was sent' in NOSAVE and "'Not Saved'" in NOSAVE)
check('and says nothing was queued on the device',
      'been queued on this device' in NOSAVE and 'localStorage' not in NOSAVE)
check('that notice is not repeated for every failed request in a burst',
      '< 20000' in NOSAVE)

WRAP = extract(PAGE_SRC, 'window.fetch = function(){')
check('the page notices a saved figure through the worker stamp',
      "headers.get(CL_OFFLINE_FLAG) === '1'" in WRAP and 'clOfflineMark(' in WRAP)
check('and reads the time it was saved out of the stamp',
      'headers.get(CL_SAVED_AT)' in WRAP)
check('a live answer clears the notice only while the browser is online',
      'else if(navigator.onLine)' in WRAP and 'clOfflineClear()' in WRAP)
check('a failed READ says what is on screen; a failed CHANGE says nothing was saved',
      "String(method).toUpperCase() === 'GET'" in WRAP and 'clOfflineMark(0)' in WRAP
      and 'clNothingSaved()' in WRAP)
check('the method is read from the call itself, not assumed (the page posts a plain url)',
      'var init = args[1] || {};' in WRAP and 'init.method' in WRAP)
check('the 401 session handling that was there before is untouched',
      'Session Expired' in WRAP)
check('a notice can never break a request',
      '/* a notice must never break a request */' in WRAP)
check('the offline module writes nothing to the browsers own storage',
      'localStorage' not in PAGE_SRC[
          PAGE_SRC.index('// ===== READ-ONLY OFFLINE SUPPORT ====='):
          PAGE_SRC.index('function clDeleteSavedCopies() {')])


# ---------- 7. keeping, and deleting, contract copies ----------
check('the contract modal offers Save for offline',
      'onclick="saveContractForOffline(this)"' in PAGE_SRC
      and 'id="dcSaveOfflineBtn"' in PAGE_SRC)
check('and says a contract that is downloaded is kept automatically',
      'Contracts you download are kept automatically' in PAGE_SRC)
check('and warns that the copies carry client details',
      'carry client details' in PAGE_SRC)
check('the modal footer offers to delete the saved copies',
      'onclick="deleteSavedContracts()"' in PAGE_SRC)
check('opening the modal reports what is kept, and whether it is this contract',
      'refreshContractOfflineStatus(projectId);' in PAGE_SRC
      and "'/download_contract/' + projectId" in PAGE_SRC)
SAVE = extract(PAGE_SRC, 'function saveContractForOffline(btn) {')
check('a copy that could not be saved says so rather than pretending',
      "'Not Saved'" in SAVE and "throw new Error('the server answered '" in SAVE)
check('a saved copy is reported with its size and the time it was saved',
      'blob.size' in SAVE and 'clClock(Date.now())' in SAVE)
DL = PAGE_SRC[PAGE_SRC.index('function performContractDownload('):
              PAGE_SRC.index('function downloadContractDirect(')]
check('a contract served from the device says the server has no record of it',
      "headers.get(CL_OFFLINE_FLAG) === '1'" in DL
      and 'has no record of this download' in DL)
DELETE = extract(PAGE_SRC, 'function clDeleteSavedCopies() {')
check('deleting empties the saved copies and then removes the bucket',
      'cache.delete(r)' in DELETE and 'caches.delete(name)' in DELETE)
check('the page finds the contract bucket by its prefix, as the worker names it',
      "var CL_DOC_CACHE_PREFIX = 'connectlink-docs-';" in PAGE_SRC
      and re.search(r"const DOC_CACHE = 'connectlink-docs-[^']*'", SW_SRC) is not None)
ACTIVATE = SW_SRC[SW_SRC.index("self.addEventListener('activate'"):]
check('a deploy cannot throw away the contracts the operator asked us to keep',
      "const DOC_CACHE = 'connectlink-docs-v1';" in SW_SRC
      and 'keep.indexOf(name) === -1' in ACTIVATE and 'DOC_CACHE]' in ACTIVATE)
check('though the previous read bucket is still swept away by the version in its name',
      'READ_CACHE' in ACTIVATE
      and "const READ_CACHE = 'connectlink-read-' + CACHE_VERSION;" in SW_SRC)
LOGOUT = extract(PAGE_SRC, 'function handleLogout() {')
check('logging out clears the saved copies',
      'clDeleteSavedCopies()' in LOGOUT and '.then(leave)' in LOGOUT)
check('but a slow clear can never hold the logout up',
      'setTimeout(leave, 700)' in LOGOUT)
check('logging out still goes to /logout exactly once',
      LOGOUT.count('window.location.href = ') == 1 and "'/logout'" in LOGOUT)


out = '\n'.join(RESULTS)
_flush()
print(out)
print('\nFAILURES: %d' % sum(1 for r in RESULTS if r.startswith('FAIL')))
