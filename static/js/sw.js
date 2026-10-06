// ConnectLink PWA Service Worker
const CACHE_VERSION = 'v3';
const CACHE_NAME = 'connectlink-' + CACHE_VERSION;
// Separate bucket for things discovered at runtime (static files + CDN libs)
const RUNTIME_CACHE = 'connectlink-runtime-' + CACHE_VERSION;
// The POS page itself, cached as an "app shell" so the till opens with NO
// connection at all (the page then reads its catalogue and queues sales locally).
const POS_SHELL = '/pos-system.html';
const STATIC_ASSETS = [
    '/static/css/design-system.css',
    '/static/css/components-ui.css',
    '/static/images/web-logo.png',
    '/static/images/web-logo-white.png',
    '/static/images/pwa-icon-192.png',
    '/static/images/pwa-icon-512.png'
];

// ---------------------------------------------------------------------------
// READ-ONLY OFFLINE FOR THE PORTAL (the projects pages)
// ---------------------------------------------------------------------------
// The till can work with no connection because it QUEUES its sales and its
// laybys. The portal cannot: an edit there is a whole-row update judged by the
// server (permissions, and whether the branch is read-only), so replaying one
// offline would quietly overwrite whatever happened in the meantime. Nothing in
// this worker queues a change, and no request that changes anything is ever
// answered out of a saved copy -- the fetch handler below returns immediately
// for every method but GET.
//
// What the portal CAN do offline is READ. Exactly two buckets are kept:
//
//   READ_ENDPOINTS  the named project endpoints the projects pages fetch
//   DOC_URLS        contract PDFs, so a contract can still be opened offline
//
// Both are matched on the WHOLE path (never a substring), and both carry the
// time they were saved, so a figure served from a copy can say how old it is
// instead of passing itself off as the server's answer.
const READ_CACHE = 'connectlink-read-' + CACHE_VERSION;
// NOTE: no CACHE_VERSION in this name, deliberately. Figures are disposable and
// a deploy may well change how they are read, but a contract the operator asked
// to keep must survive the deploy -- "Delete saved copies" and logging out are
// what remove those. (The page finds this bucket by its 'connectlink-docs-'
// prefix, so the '-v1' suffix is free to change if the shape of a stored copy
// ever has to change.)
const DOC_CACHE = 'connectlink-docs-v1';

// Named read-only endpoints. A money figure somebody might act on is
// deliberately NOT on this list: a saved copy of it is worse than no answer.
const READ_ENDPOINTS = [
    '/get_project_count',
    '/get_project_months',
    '/get_project_start_months',
    '/api/projects-page'
];
// The same, where the path carries an id.
const READ_PATTERNS = [
    /^\/get_project\/\d+$/,
    /^\/api\/project\/\d+\/has-gantt$/
];
// Documents worth keeping on the device. A contract PDF is append-only in the
// sense that matters here: regenerating one never changes what the last said.
const DOC_PATTERNS = [
    /^\/download_contract\/\d+$/
];

// How much this device keeps. Cache Storage is shared and finite, and contract
// PDFs are the only entries here big enough to matter.
const READ_MAX_ENTRIES = 200;
const DOC_MAX_ENTRIES = 30;
const DOC_MAX_BYTES = 40 * 1024 * 1024;

// Stamped on every copy that is handed back because the server could not be
// reached. The page reads these and tells the operator what it is looking at.
const SAVED_AT = 'X-ConnectLink-Saved-At';
const OFFLINE_FLAG = 'X-ConnectLink-Offline';

function matchesAny(patterns, pathname) {
    for (let i = 0; i < patterns.length; i++) {
        if (patterns[i].test(pathname)) return true;
    }
    return false;
}

// 'read' | 'doc' | null. Whole-path match, so a future /api/projects-page-extra
// is not swept in by the name of a neighbour.
function offlineBucket(pathname) {
    if (READ_ENDPOINTS.indexOf(pathname) !== -1) return 'read';
    if (matchesAny(READ_PATTERNS, pathname)) return 'read';
    if (matchesAny(DOC_PATTERNS, pathname)) return 'doc';
    return null;
}

// A copy handed out in place of the server's answer has to SAY it is a copy.
// The body is read to a Blob rather than wrapped as a stream, so the response
// the page gets is always a whole, readable one.
async function withOfflineMark(response, savedAt) {
    const headers = new Headers(response.headers);
    headers.set(OFFLINE_FLAG, '1');
    if (savedAt) headers.set(SAVED_AT, String(savedAt));
    const body = await response.blob();
    return new Response(body, {
        status: response.status,
        statusText: response.statusText,
        headers: headers
    });
}

// The copy is stored already carrying the time it was saved, because Cache
// Storage has nowhere else to keep that, and a copy with no date is a figure
// nobody can judge. `response` itself is left whole for the page: only the clone
// is read.
async function storeWithStamp(cache, request, response) {
    const copy = response.clone();
    const body = await copy.blob();
    const headers = new Headers(copy.headers);
    headers.set(SAVED_AT, String(Date.now()));
    await cache.put(request, new Response(body, {
        status: copy.status,
        statusText: copy.statusText,
        headers: headers
    }));
}

// Keep the newest entries, and (for documents) within a byte budget. The entry
// just saved is never the one dropped.
async function trimCache(cache, justStoredUrl, maxEntries, maxBytes) {
    const requests = await cache.keys();
    if (requests.length <= maxEntries && maxBytes === 0) return;
    const entries = [];
    let total = 0;
    for (const req of requests) {
        const res = await cache.match(req);
        if (!res) continue;
        const bytes = parseInt(res.headers.get('Content-Length'), 10) || 0;
        const at = parseInt(res.headers.get(SAVED_AT), 10) || 0;
        entries.push({ req: req, at: at, bytes: bytes, newest: req.url === justStoredUrl });
        total += bytes;
    }
    entries.sort((a, b) => a.at - b.at);          // oldest first
    let count = entries.length;
    for (const e of entries) {
        if (count <= maxEntries && (maxBytes === 0 || total <= maxBytes)) break;
        if (e.newest) continue;
        await cache.delete(e.req);
        count -= 1;
        total -= e.bytes;
    }
}

// Read-only endpoints: the server's answer wins whenever it can be reached, and
// only then is it saved. With no answer, the saved copy is served -- marked.
async function readNetworkFirst(request) {
    try {
        const response = await fetch(request);
        if (response && response.status === 200) {
            const cache = await caches.open(READ_CACHE);
            storeWithStamp(cache, request, response)
                .then(() => trimCache(cache, request.url, READ_MAX_ENTRIES, 0))
                .catch(() => {});
        }
        return response;
    } catch (e) {
        const cached = await caches.match(request);
        if (cached) return await withOfflineMark(cached, cached.headers.get(SAVED_AT));
        return new Response(JSON.stringify({
            error: 'There is no connection, and no copy of this on this device.',
            offline: true, offline_no_copy: true
        }), { status: 503, headers: { 'Content-Type': 'application/json' } });
    }
}

// Contract PDFs: cached on the way past (a contract the operator already asked
// for is a copy they already have), and served from the cache when the server
// cannot be reached. Only a real 200 application/pdf is ever kept, so a failure
// page can never become "the contract".
async function docNetworkFirst(request) {
    try {
        const response = await fetch(request);
        const type = response ? (response.headers.get('Content-Type') || '') : '';
        if (response && response.status === 200 && type.indexOf('application/pdf') !== -1) {
            const cache = await caches.open(DOC_CACHE);
            storeWithStamp(cache, request, response)
                .then(() => trimCache(cache, request.url, DOC_MAX_ENTRIES, DOC_MAX_BYTES))
                .catch(() => {});
        }
        return response;
    } catch (e) {
        const cached = await caches.match(request);
        if (cached) return await withOfflineMark(cached, cached.headers.get(SAVED_AT));
        return new Response(
            'There is no connection, and this contract has not been saved on this ' +
            'device.\n\nOpen it once while online (or use "Save for offline") and it ' +
            'will be here next time. Nothing was changed.',
            { status: 503, headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
    }
}

// Install event - cache static assets
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            // Never let one missing file abort the whole install
            return Promise.all(
                STATIC_ASSETS.map((url) => cache.add(url).catch(() => {}))
            ).then(() => cache.add(
                new Request(POS_SHELL, { credentials: 'same-origin' })
            ).catch(() => {}));
        })
    );
    self.skipWaiting();
});

// Activate event - clean old caches
self.addEventListener('activate', (event) => {
    // A cache survives only if this version still uses it by that exact name.
    // The contract bucket is named without CACHE_VERSION on purpose (see above),
    // so it is listed here to make that explicit: a deploy must not throw away
    // the copies the operator asked us to keep.
    const keep = [CACHE_NAME, RUNTIME_CACHE, READ_CACHE, DOC_CACHE];
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((name) => keep.indexOf(name) === -1)
                    .map((name) => caches.delete(name))
            );
        })
    );
    self.clients.claim();
});

// Fetch event - network first, fall back to cache.
// Extended so the POS keeps working with no connection: the POS page, the
// static files it needs and its CDN libraries are all kept in the runtime
// cache, while /api/* is NEVER cached (a stale price or stock level would be
// worse than no answer at all).
function isCacheableRequest(url) {
    if (url.pathname.startsWith('/api/')) return false;
    if (url.pathname.startsWith('/webhook')) return false;
    return url.protocol === 'http:' || url.protocol === 'https:';
}

function isPosUrl(url) {
    return url.pathname === '/pos-system.html' || url.pathname.startsWith('/pos-system');
}

async function networkFirst(request, fallbackUrl) {
    try {
        const response = await fetch(request);
        // status 0 = an opaque cross-origin (CDN) response; those are cacheable too
        if (response && (response.status === 200 || response.type === 'opaque')) {
            const cache = await caches.open(RUNTIME_CACHE);
            cache.put(request, response.clone()).catch(() => {});
        }
        return response;
    } catch (e) {
        const cached = await caches.match(request);
        if (cached) return cached;
        if (fallbackUrl) {
            const shell = await caches.match(fallbackUrl);
            if (shell) return shell;
        }
        return new Response('You are offline and this page has not been saved yet.', {
            status: 503,
            headers: { 'Content-Type': 'text/plain' }
        });
    }
}

self.addEventListener('fetch', (event) => {
    // Only handle GET requests. Nothing that changes anything (POST / PUT /
    // DELETE) is touched by this worker: there is no queue here, and an offline
    // change must fail loudly rather than look as if it had been saved.
    if (event.request.method !== 'GET') return;

    let url;
    try { url = new URL(event.request.url); } catch (e) { return; }
    if (url.protocol !== 'http:' && url.protocol !== 'https:') return;

    // The portal's read-only buckets. Same origin only: a saved copy is only
    // ever handed back for this app's own named endpoints.
    if (url.origin === self.location.origin) {
        const bucket = offlineBucket(url.pathname);
        if (bucket === 'read') {
            event.respondWith(readNetworkFirst(event.request));
            return;
        }
        if (bucket === 'doc') {
            // A contract link can be a plain navigation (target=_blank) or a
            // fetch, so this is settled before the page-shell branch below.
            event.respondWith(docNetworkFirst(event.request));
            return;
        }
    }

    // Page loads: the POS gets its cached shell so the till still opens offline,
    // and any page the operator has already visited can be re-opened from the
    // runtime cache (its figures come from the read bucket above).
    if (event.request.mode === 'navigate') {
        event.respondWith(networkFirst(event.request, isPosUrl(url) ? POS_SHELL : null));
        return;
    }

    if (!isCacheableRequest(url)) return;

    const sameOrigin = url.origin === self.location.origin;
    const isStatic = sameOrigin && url.pathname.startsWith('/static/');
    const isCdnAsset = !sameOrigin;
    if (!isStatic && !isCdnAsset) return;

    event.respondWith(networkFirst(event.request, null));
});
