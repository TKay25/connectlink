/**
 * ConnectLink WhatsApp - Service Worker
 * Handles push notifications and caching for the WhatsApp app PWA
 */

const CACHE_NAME = 'connectlink-whatsapp-v1';

// Assets to cache on install
const PRECACHE_URLS = [];

self.addEventListener('install', event => {
    self.skipWaiting();
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(PRECACHE_URLS))
    );
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys => Promise.all(
            keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
        ))
    );
    self.clients.claim();
});

// Network-first strategy
self.addEventListener('fetch', event => {
    event.respondWith(
        fetch(event.request)
            .then(response => {
                const clone = response.clone();
                caches.open(CACHE_NAME).then(cache => {
                    if (event.request.method === 'GET') {
                        cache.put(event.request, clone);
                    }
                });
                return response;
            })
            .catch(() => caches.match(event.request))
    );
});

// Handle push events (for future server push)
self.addEventListener('push', event => {
    if (!event.data) return;
    try {
        const data = event.data.json();
        const options = {
            body: data.body || 'New update',
            icon: '/static/images/reqlogo.png',
            badge: '/static/images/reqlogo.png',
            vibrate: [200, 100, 200],
            requireInteraction: true,
            data: { url: data.url || '/whatsapp-app' }
        };
        event.waitUntil(
            self.registration.showNotification(data.title || 'ConnectLink', options)
        );
    } catch (e) {
        // Plain text push
        event.waitUntil(
            self.registration.showNotification('ConnectLink', { body: event.data.text() })
        );
    }
});

// Handle notification click
self.addEventListener('notificationclick', event => {
    event.notification.close();
    const urlToOpen = event.notification.data?.url || '/whatsapp-app';
    const action = event.notification.data?.action || '';
    
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then(clientList => {
                // Try to focus existing window first
                for (const client of clientList) {
                    if (client.url.includes('/whatsapp-app') && 'focus' in client) {
                        // If there's a specific tab to open (enquiries vs chats)
                        if (action === 'enquiries') {
                            client.postMessage({ type: 'switchTab', tab: 'enquiries' });
                        } else {
                            client.postMessage({ type: 'switchTab', tab: 'chats' });
                        }
                        return client.focus();
                    }
                }
                return clients.openWindow(urlToOpen);
            })
    );
});

// Handle messages from the page (to show notifications from page polling)
self.addEventListener('message', event => {
    const data = event.data;
    if (!data) return;
    
    if (data.type === 'showNotification') {
        const options = {
            body: data.body || 'New message',
            icon: '/static/images/reqlogo.png',
            badge: '/static/images/reqlogo.png',
            vibrate: [200, 100, 200],
            requireInteraction: true,
            data: { url: data.url || '/whatsapp-app', action: data.action || '' },
            tag: data.tag || 'whatsapp'
        };
        self.registration.showNotification(data.title || 'ConnectLink', options);
    }
});
            })
    );
});
