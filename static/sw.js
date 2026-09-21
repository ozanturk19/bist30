/* BorsaPusula Service Worker v3.1 — offline fallback + PWA optimize */
const CACHE = 'borsapusula-v40';

/* Sadece truly static assets — HTML sayfaları ASLA pre-cache yapılmaz (offline.html hariç) */
const STATIC = [
  '/static/lightweight-charts.min.js?v=1',
  '/static/manifest.json?v=162d10e6',
  '/static/icon-192.png?v=933a8452',
  '/static/icon-512.png?v=e9ec3ef2',
  '/static/favicon.svg?v=6ef6d5a3',
  '/static/css/tokens.css?v=6450b4ce',
  '/static/css/shared.css?v=5761378a',
  '/static/css/data-art.css?v=f1bd0cc1',
  '/static/css/pages/offline.css?v=34a9a271',
  '/offline',
];

/* 20.09 BULGU: bu listedeki cache-bust hash'leri templates/offline.html'dekilerle
   ELLE senkron tutuluyordu ve ikisi birbirinden kopmustu (tokens.css burada
   ?v=1eabd653, sablonda ?v=a9ea1d38). `caches.match` varsayilan olarak query
   string'i de ANAHTARIN PARCASI sayar -> cevrimdisi kullanici offline.html'i
   aliyor ama sayfanin ISTEDIGI iki CSS de cache'te BULUNAMIYOR, fetch de
   basarisiz oluyordu: sayfa tam da ise yarayacagi anda STILSIZ aciliyordu.
   Iki katli onlem: (1) hash'ler duzeltildi + CACHE surumu artirildi,
   (2) asagidaki ignoreSearch YEDEGI ile ileride yeniden kopsa bile en
   kotusu BAYAT CSS olur, HIC CSS olmaz. */

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
  /* fonts.googleapis.com KASITLI olarak DIŞARIDA: sayfalar bu CSS'i <link rel=preload as=style>
     ile önceden ısıtıyor (CPO-06.09) — SW burayı intercept ederse tarayıcı preload'ı "cross-world
     service worker resource mismatch" diye reddedip ikinci kez ağdan çekiyor, preload boşa gidiyor.
     15.09 fresh-ground-audit bulgusu. Asıl font dosyaları (gstatic) SW cache'inde kalmaya devam eder. */
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
