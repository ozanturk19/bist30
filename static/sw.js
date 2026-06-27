/* BorsaPusula Service Worker v3.1 — offline fallback + PWA optimize */
const CACHE = 'borsapusula-v21';

/* Sadece truly static assets — HTML sayfaları ASLA pre-cache yapılmaz (offline.html hariç) */
const STATIC = [
  '/static/lightweight-charts.min.js',
  '/static/manifest.json',
  '/static/icon-192.png',
  '/static/icon-512.png',
  '/offline',
  'https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Manrope:wght@400;500;600;700&display=swap',
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE)
      .then(c => Promise.all(
        STATIC.map(url => c.add(url).catch(err => console.warn('SW cache miss:', url)))
      ))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

/* Strateji:
 * - API + SSE: SW bypass (tarayıcı doğrudan çeksin)
 * - Static asset (/static/, fonts.googleapis.com): stale-while-revalidate
 * - HTML ve diğer her şey: NETWORK-ONLY (SW geçmez, browser her zaman taze çeker)
 *
 * Eski SW (v18) HTML'i de cache'liyordu → kullanıcılar bayat sayfa görüyordu.
 * v20 ile bu davranış tamamen kaldırıldı. HTML her zaman taze.
 */
function isStaticAsset(url) {
  if (url.pathname.startsWith('/static/')) return true;
  if (url.hostname === 'fonts.googleapis.com') return true;
  if (url.hostname === 'fonts.gstatic.com') return true;
  return false;
}

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  /* API + SSE: SW return etmez → tarayıcı normal flow */
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/stream')) {
    return;
  }
  if (e.request.method !== 'GET') return;

  /* Static asset: stale-while-revalidate */
  if (isStaticAsset(url)) {
    e.respondWith(
      caches.match(e.request).then(cached => {
        const fetchPromise = fetch(e.request).then(res => {
          if (res && res.ok &&
              (url.origin === self.location.origin || url.hostname.startsWith('fonts.'))) {
            const clone = res.clone();
            caches.open(CACHE).then(c => c.put(e.request, clone));
          }
          return res;
        }).catch(() => cached);
        return cached || fetchPromise;
      })
    );
    return;
  }

  /* HTML navigation: network-first, /offline fallback when offline */
  if (e.request.mode === 'navigate') {
    e.respondWith(
      fetch(e.request).catch(() =>
        caches.match('/offline').then(r => r || new Response('Offline', { status: 503 }))
      )
    );
    return;
  }

  /* Diğer her şey: SW dokunmaz */
});

/* Push notification handler */
self.addEventListener('push', e => {
  const data = e.data ? e.data.json() : {};
  e.waitUntil(
    self.registration.showNotification(data.title || 'BorsaPusula', {
      body:             data.body || 'Sinyal değişikliği var.',
      icon:             '/static/icon-192.png',
      badge:            '/static/icon-192.png',
      tag:              data.tag || 'borsapusula-signal',
      renotify:         true,
      requireInteraction: false,
      vibrate:          [200, 100, 200],
      data:             { url: data.url || '/' },
    })
  );
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  const url = (e.notification.data && e.notification.data.url) || '/';
  e.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(wins => {
      for (const w of wins) {
        if (w.url.includes(self.location.origin) && 'focus' in w) {
          w.focus();
          if (url !== '/') w.navigate(url);
          return;
        }
      }
      return clients.openWindow(url);
    })
  );
});

/* Debug: manuel cache temizleme (browser console'dan tetiklenebilir) */
self.addEventListener('message', e => {
  if (e.data && e.data.type === 'BP_CLEAR_CACHE') {
    e.waitUntil(
      caches.keys()
        .then(keys => Promise.all(keys.map(k => caches.delete(k))))
        .then(() => {
          if (e.ports && e.ports[0]) e.ports[0].postMessage({ ok: true });
        })
    );
  }
});
