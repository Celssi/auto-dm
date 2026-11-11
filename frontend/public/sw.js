const CACHE_NAME = 'auto-dm-20261111T092';
const urlsToCache = ['/', '/manifest.json', '/icons/icon-192x192.png', '/icons/icon-512x512.png'];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(urlsToCache))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((cacheNames) =>
        Promise.all(cacheNames.filter((name) => name !== CACHE_NAME).map((name) => caches.delete(name))),
      )
      .then(() => self.clients.claim()),
  );
});

function offlineResponse() {
  return new Response('Offline. Check your connection and try again.', {
    status: 503,
    statusText: 'Service Unavailable',
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  });
}

function putInCache(request, response) {
  const copy = response.clone();
  return caches
    .open(CACHE_NAME)
    .then((cache) => cache.put(request, copy))
    .catch(() => undefined);
}

function isStaticAsset(url) {
  return (
    url.pathname.startsWith('/assets/') ||
    url.pathname.startsWith('/icons/') ||
    url.pathname === '/favicon.svg' ||
    url.pathname === '/favicon.ico' ||
    url.pathname === '/manifest.json'
  );
}

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);

  if (url.origin !== self.location.origin) {
    return;
  }

  if (url.pathname.startsWith('/api') || request.headers.get('accept')?.includes('text/event-stream')) {
    return;
  }

  // Range requests (PDF reader) and book files must go straight to the network.
  if (request.headers.has('range')) return;
  if (/\.(pdf|epub)(\?|$)/i.test(url.pathname)) return;

  if (request.mode === 'navigate' || request.destination === 'document') {
    // Network first; on failure fall back to the cached page, then the cached app shell.
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response.status === 200) void putInCache(request, response);
          return response;
        })
        .catch(() =>
          caches
            .match(request)
            .then((cached) => cached || caches.match('/'))
            .then((cached) => cached || offlineResponse())
            .catch(() => offlineResponse()),
        ),
    );
    return;
  }

  if (isStaticAsset(url)) {
    event.respondWith(
      caches
        .match(request)
        .catch(() => undefined)
        .then((cached) => {
          if (cached) return cached;
          return fetch(request)
            .then((response) => {
              if (response.ok && response.status === 200 && response.type === 'basic') {
                void putInCache(request, response);
              }
              return response;
            })
            .catch(() => offlineResponse());
        }),
    );
    return;
  }

  // Everything else (including unknown same-origin files): network first, no aggressive caching.
  event.respondWith(
    fetch(request)
      .then((response) => response)
      .catch(() =>
        caches
          .match(request)
          .then((cached) => cached || offlineResponse())
          .catch(() => offlineResponse()),
      ),
  );
});

self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  if (event.data && event.data.type === 'GET_VERSION') {
    const version = CACHE_NAME;
    if (event.ports && event.ports[0]) {
      event.ports[0].postMessage({ type: 'SW_VERSION', version });
    }
  }
});
