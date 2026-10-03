// ConnectLink PWA Service Worker
const CACHE_VERSION = 'v2';
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
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((name) => name !== CACHE_NAME && name !== RUNTIME_CACHE)
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
    // Only handle GET requests
    if (event.request.method !== 'GET') return;

    let url;
    try { url = new URL(event.request.url); } catch (e) { return; }
    if (url.protocol !== 'http:' && url.protocol !== 'https:') return;

    // Page loads: the POS gets its cached shell so the till still opens offline
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
