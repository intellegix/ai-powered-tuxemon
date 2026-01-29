// Service Worker for AI-Powered Tuxemon PWA
// Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

const CACHE_NAME = 'tuxemon-v1.0.0';
const OFFLINE_URL = '/offline.html';

// Core files to cache for offline functionality
const CORE_CACHE_FILES = [
  '/',
  '/index.html',
  '/offline.html',
  '/manifest.json',
  // Add core game assets here when available
];

// API endpoints that should be cached
const API_CACHE_PATTERNS = [
  '/api/v1/game/world',
  '/api/v1/npcs/nearby',
  '/api/v1/inventory/',
  '/health'
];

// Install event - cache core files
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker');

  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[SW] Caching core files');
        return cache.addAll(CORE_CACHE_FILES);
      })
      .then(() => {
        console.log('[SW] Core files cached successfully');
        return self.skipWaiting();
      })
      .catch((error) => {
        console.error('[SW] Failed to cache core files:', error);
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker');

  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((cacheName) => cacheName !== CACHE_NAME)
            .map((cacheName) => {
              console.log('[SW] Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            })
        );
      })
      .then(() => {
        console.log('[SW] Service worker activated');
        return self.clients.claim();
      })
  );
});

// Fetch event - network-first strategy with offline fallback
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Handle navigation requests (HTML pages)
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          // Cache successful navigation responses
          if (response.status === 200) {
            const responseClone = response.clone();
            caches.open(CACHE_NAME)
              .then((cache) => cache.put(request, responseClone));
          }
          return response;
        })
        .catch(() => {
          // Offline fallback for navigation
          return caches.match('/index.html')
            .then((cachedResponse) => {
              return cachedResponse || caches.match(OFFLINE_URL);
            });
        })
    );
    return;
  }

  // Handle API requests
  if (url.pathname.startsWith('/api/')) {
    // Network-first for API calls with cache fallback
    event.respondWith(
      fetch(request)
        .then((response) => {
          // Cache successful GET requests for specific endpoints
          if (request.method === 'GET' && response.status === 200) {
            const shouldCache = API_CACHE_PATTERNS.some(pattern =>
              url.pathname.startsWith(pattern)
            );

            if (shouldCache) {
              const responseClone = response.clone();
              caches.open(CACHE_NAME)
                .then((cache) => {
                  cache.put(request, responseClone);
                });
            }
          }
          return response;
        })
        .catch(() => {
          // Return cached API response if available
          return caches.match(request)
            .then((cachedResponse) => {
              if (cachedResponse) {
                console.log('[SW] Serving cached API response:', request.url);
                return cachedResponse;
              }

              // Return offline indicator for failed API calls
              return new Response(
                JSON.stringify({
                  error: 'offline',
                  message: 'API unavailable offline',
                  cached: false
                }),
                {
                  status: 503,
                  headers: {
                    'Content-Type': 'application/json',
                    'X-Offline-Response': 'true'
                  }
                }
              );
            });
        })
    );
    return;
  }

  // Handle static assets - cache-first strategy
  if (request.destination === 'script' ||
      request.destination === 'style' ||
      request.destination === 'image' ||
      request.destination === 'font') {

    event.respondWith(
      caches.match(request)
        .then((cachedResponse) => {
          if (cachedResponse) {
            return cachedResponse;
          }

          return fetch(request)
            .then((response) => {
              if (response.status === 200) {
                const responseClone = response.clone();
                caches.open(CACHE_NAME)
                  .then((cache) => cache.put(request, responseClone));
              }
              return response;
            });
        })
    );
    return;
  }

  // Default: network-first for everything else
  event.respondWith(
    fetch(request)
      .catch(() => caches.match(request))
  );
});

// Background sync for offline actions
self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync triggered:', event.tag);

  if (event.tag === 'sync-game-actions') {
    event.waitUntil(
      syncOfflineActions()
        .then(() => {
          console.log('[SW] Offline actions synced successfully');
        })
        .catch((error) => {
          console.error('[SW] Failed to sync offline actions:', error);
        })
    );
  }
});

// Handle push notifications for game events
self.addEventListener('push', (event) => {
  console.log('[SW] Push notification received');

  let data = {};
  if (event.data) {
    data = event.data.json();
  }

  const options = {
    body: data.body || 'New game event!',
    icon: '/icons/icon-192x192.png',
    badge: '/icons/badge-72x72.png',
    data: {
      url: data.url || '/',
      timestamp: Date.now()
    },
    actions: [
      {
        action: 'open',
        title: 'Open Game'
      },
      {
        action: 'close',
        title: 'Dismiss'
      }
    ],
    requireInteraction: false,
    silent: false
  };

  event.waitUntil(
    self.registration.showNotification(
      data.title || 'AI Tuxemon',
      options
    )
  );
});

// Handle notification clicks
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notification clicked:', event.action);

  event.notification.close();

  if (event.action === 'open') {
    const url = event.notification.data.url || '/';

    event.waitUntil(
      clients.matchAll({ type: 'window' })
        .then((clientList) => {
          // Focus existing window if available
          for (const client of clientList) {
            if (client.url.includes(url) && 'focus' in client) {
              return client.focus();
            }
          }

          // Open new window
          if (clients.openWindow) {
            return clients.openWindow(url);
          }
        })
    );
  }
});

// Sync offline game actions when connection is restored
async function syncOfflineActions() {
  try {
    // Get offline actions from IndexedDB
    const db = await openIndexedDB();
    const actions = await getOfflineActions(db);

    if (actions.length === 0) {
      console.log('[SW] No offline actions to sync');
      return;
    }

    console.log(`[SW] Syncing ${actions.length} offline actions`);

    // Sync each action
    for (const action of actions) {
      try {
        const response = await fetch(action.url, {
          method: action.method,
          headers: {
            'Content-Type': 'application/json',
            'X-Offline-Sync': 'true'
          },
          body: JSON.stringify(action.data)
        });

        if (response.ok) {
          await removeOfflineAction(db, action.id);
          console.log('[SW] Synced offline action:', action.id);
        } else {
          console.warn('[SW] Failed to sync action:', action.id, response.status);
        }
      } catch (error) {
        console.error('[SW] Error syncing action:', action.id, error);
      }
    }

    console.log('[SW] Offline actions sync completed');
  } catch (error) {
    console.error('[SW] Failed to sync offline actions:', error);
    throw error;
  }
}

// IndexedDB helpers for offline action storage
function openIndexedDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('TuxemonOffline', 1);

    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains('actions')) {
        db.createObjectStore('actions', { keyPath: 'id', autoIncrement: true });
      }
    };

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

function getOfflineActions(db) {
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(['actions'], 'readonly');
    const store = transaction.objectStore('actions');
    const request = store.getAll();

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

function removeOfflineAction(db, actionId) {
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(['actions'], 'readwrite');
    const store = transaction.objectStore('actions');
    const request = store.delete(actionId);

    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}