/* C-44 (26.09): hata sayfalarındaki hisse arama kutusu (404/410/429/500 ortak).
   Kod listesi bp-search.js'in oturum önbelleğinden, yoksa /api/stocks/list'ten
   (kanonik evren, XU030 yok, `loading` durumu yok). Liste gelmeden gönderilirse
   en çok 3 sn beklenir; liste hiç yoksa doğrudan /hisse/<KOD>'a gidilir. */
(function () {
  var form = document.getElementById('q404Form');
  var hint = document.getElementById('q404Hint');
  if (!form || !hint) return;
  var tickers = null;
  function fromCache() {
    try {
      var c = sessionStorage.getItem('bp_search_cache_v1');
      var t = sessionStorage.getItem('bp_search_t_v1');
      if (!c || !t || Date.now() - parseInt(t, 10) >= 300000) return null;
      var a = JSON.parse(c);
      if (!Array.isArray(a)) return null;
      var ts = a.map(function (s) { return s && s.t; }).filter(function (x) { return typeof x === 'string' && x; });
      return ts.length ? ts : null;
    } catch (e) { console.warn('err-search: önbellek okunamadı', e); return null; }
  }
  var ready = (function () {
    var cached = fromCache();
    if (cached) { tickers = cached; return Promise.resolve(); }
    var opt = {};
    if (typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function') opt.signal = AbortSignal.timeout(8000);
    return fetch('/api/stocks/list', opt).then(function (r) { return r.ok ? r.json() : null; }).then(function (d) {
      if (!d || !Array.isArray(d.stocks)) return;
      var ts = d.stocks.map(function (s) { return s && s.ticker; }).filter(Boolean);
      if (ts.length) tickers = ts;
    }).catch(function (e) { console.warn('err-search: kod listesi alınamadı', e); });
  })();
  function go(v) { window.location.href = '/hisse/' + encodeURIComponent(v); }
  function decide(v) {
    if (!tickers || tickers.indexOf(v) !== -1) { go(v); return; }
    var starts = tickers.filter(function (t) { return t.indexOf(v) === 0; }).slice(0, 5);
    if (starts.length) {
      hint.innerHTML = 'Bunu mu demek istediniz? ' + starts.map(function (t) {
        return '<a href="/hisse/' + encodeURIComponent(t) + '" class="da-link">' + t + '</a>';
      }).join(' ');
    } else {
      hint.textContent = '"' + v + '" ile eşleşen bir hisse bulunamadı. ';
      hint.insertAdjacentHTML('beforeend', '<a href="/tarama" class="da-link">Keşfet sayfasından göz atın</a>.');
    }
  }
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var v = document.getElementById('q404').value.trim().toUpperCase();
    if (!v) return;
    if (tickers) { decide(v); return; }
    hint.textContent = 'Kontrol ediliyor…';
    var done = false;
    var guard = setTimeout(function () { if (!done) { done = true; decide(v); } }, 3000);
    ready.then(function () { if (!done) { done = true; clearTimeout(guard); decide(v); } });
  });
})();
