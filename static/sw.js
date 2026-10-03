/* BorsaPusula Service Worker v3.1 — offline fallback + PWA optimize */
const CACHE = 'borsapusula-90fc1f24';

/* Sadece truly static assets — HTML sayfaları ASLA pre-cache yapılmaz (offline.html hariç).
   C-26: CACHE ve STATIC elle yazılmaz — tools/sw_manifest.py üretir (pre-deploy 11. adım). */
const STATIC = [
  '/static/css/data-art.css?v=b3c35048',
  '/static/css/pages/offline.css?v=7729d8da',
  '/static/css/shared.css?v=aedf2343',
  '/static/css/tokens.css?v=dcbecdf8',
  '/static/favicon.svg?v=6834d771',
  '/static/fonts/bricolage-800.woff2?v=c76bd7c0',
  '/static/fonts/space-grotesk.woff2?v=5ac34783',
  '/static/icon-192.png?v=0b40a6a6',
  '/static/icon-512.png?v=265a8cb2',
  '/static/lightweight-charts.min.js?v=86b4c600',
  '/static/manifest.json?v=00de4c25',
  '/offline',
];

/* 20.09 BULGU (elle senkron hash'ler koptu, /offline stilsiz açıldı) C-26 ile
   kapandı: liste /offline'ın render edilmiş static_v URL'lerinden üretilir.
   ignoreSearch yedeği yine de durur: en kötüsü BAYAT CSS olur, HİÇ CSS olmaz. */

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
 * - Static asset (/static/, fontlar dahil — C-13'ten beri kendi sunucumuzda): stale-while-revalidate
 * - HTML ve diğer her şey: NETWORK-ONLY (SW geçmez, browser her zaman taze çeker)
 *
 * Eski SW (v18) HTML'i de cache'liyordu → kullanıcılar bayat sayfa görüyordu.
 * v20 ile bu davranış tamamen kaldırıldı. HTML her zaman taze.
 */
function isStaticAsset(url) {
  if (url.pathname.startsWith('/static/')) return true;
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
          if (res && (res.ok || res.type === 'opaque') &&
              (url.origin === self.location.origin || url.hostname.startsWith('fonts.'))) {
            const clone = res.clone();
            caches.open(CACHE).then(c => c.put(e.request, clone));
          }
          return res;
        }).catch(() =>
          /* Ag yok: once tam eslesme (yoksa zaten undefined), sonra hash'i
             yok sayan yedek. SADECE fetch BASARISIZ olunca devreye girer —
             cevrimici akista tam-eslesme/ag onceligi degismez, yani yeni
             hash yayinlandiginda kullanici bayat CSS gormeye devam etmez. */
          cached || caches.match(e.request, { ignoreSearch: true })
        );
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
