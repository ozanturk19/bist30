/* /takip sayfasi (C-41, onayli taslak C-M8 + O16g=B hesap).

   Sunucu sablonu KISISEL BAGLAM TASIMAZ; her sey hesap API'sinden gelir
   (static/js/bp-account.js). Durumlar:
     out      — `bp_li` yok ya da oturum dusmus: giris paneli (SIFIR hesap istegi)
     loading  — ipucu var, API yolda: iskelet
     error    — ag/5xx: hata + "Yeniden dene" (bos liste DEMEZ, K-BK)
     in       — liste (masaustu tablo / telefon 72px satir) ya da bos kart

   Piyasa verisi /api/me/watchlist `items`inden; "Hisse ekle" aramasinin evreni
   yalniz panel acilinca /api/tarama'dan (tembel). /api/data DEGIL: o yayin
   XU030 endeksini hisse gibi tasir (K-DC) ve yeni tuketicisi envantere
   islenmek zorunda; /api/tarama ayni satir alanlarini (+ BP Skoru) endekssiz
   verir. Siralama taslaktaki gibi:
   son seansta degisen once, sonra BP Skoru, sonra kod. */
(function () {
  'use strict';
  var A = window.BPAccount;
  var app = document.getElementById('tkApp');
  if (!A || !app) return;
  var statEl = document.getElementById('tkStat');
  var ctlEl = document.getElementById('tkCtl');
  var layerEl = document.getElementById('tkLayer');
  var toastEl = document.getElementById('tkToast');
  var liveEl = document.getElementById('tkLive');
  var fileEl = document.getElementById('tkFile');
  var MQ = window.matchMedia('(max-width: 819.98px)');
  var MODE_KEY = 'bp_takip_mode';
  var MINUS = '−';
  var KEY = { AL: 'g', BEKLE: 'y', SAT: 'b' };
  var ORDER = 'gybn';
  var nf2 = new Intl.NumberFormat('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  var nf0 = new Intl.NumberFormat('tr-TR', { maximumFractionDigits: 0 });

  var S = {
    phase: 'boot', me: null, items: [], asof: null, mode: null,
    menu: false, confirmClear: false, add: false, q: '', pick: null,
    edit: null, editMode: false, confirmDel: false, busy: false,
    uni: null, uniState: 'idle', enter: false
  };
  var toast = null, tTimer = null, tTick = null, login = null, sheetRelease = null, lastStat = null;

  /* ── bicim ── */
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function fin(v) { return typeof v === 'number' && isFinite(v); }
  function pct(v) { return fin(v) ? bpFormatPct(v, 2).replace(/^-/, MINUS) : '—'; }
  function tl(v) { return fin(v) ? nf2.format(v) + ' ₺' : '—'; }
  function stl(v) {
    if (!fin(v)) return '—';
    var d = bpDir(v, 2);
    return (d === 1 ? '+' : (d === -1 ? MINUS : '')) + nf2.format(Math.abs(bpZero(v, 2))) + ' ₺';
  }
  function cls(v) { return fin(v) ? bpDirClass(v, 2, ['u', 'd', 'n']) : 'n'; }
  /* Turkce iyelik/bulunma eki (sayidan sonra): 1'i 2'si 3'u 6'si 9'u 10'u 40'i */
  function poss(n) {
    n = Math.abs(Math.round(n));
    if (n === 0) return "'ı";
    var U = ['', 'i', 'si', 'ü', 'ü', 'i', 'sı', 'si', 'i', 'u'], T = ['', 'u', 'si', 'u', 'ı', 'si', 'ı', 'i', 'i', 'ı'];
    if (n % 10) return "'" + U[n % 10];
    if (n % 100) return "'" + T[(n % 100) / 10];
    if (n % 1000) return "'ü";
    return "'i";
  }
  function loc(n) { var p = poss(n), v = p.slice(-1); return p + 'n' + ('iü'.indexOf(v) >= 0 ? 'de' : 'da'); }
  function dayMonth(asof) {
    var m = /^(\d{1,2})\.(\d{1,2})\.(\d{4})/.exec(String(asof || ''));
    if (!m || +m[2] < 1 || +m[2] > 12) return '';
    return (+m[1]) + ' ' + BP_TR_MONTHS[+m[2] - 1];
  }
  function isoDate(ts) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(ts || ''));
    return m ? m[3] + '.' + m[2] + '.' + m[1] : '';
  }
  function label(r) { return sigLabel(r.sig); }

  function svg(p, w) { return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="' + (w || 1.8) + '" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + p + '</svg>'; }
  var IC = {
    search: svg('<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>'),
    plus: svg('<path d="M12 5v14M5 12h14"/>', 2),
    more: '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="5" cy="12" r="1.9"/><circle cx="12" cy="12" r="1.9"/><circle cx="19" cy="12" r="1.9"/></svg>',
    x: svg('<path d="M6 6l12 12M18 6L6 18"/>', 2),
    pencil: svg('<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13.5 6.5l4 4"/>'),
    trash: svg('<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>'),
    star: svg('<path d="M12 3l2.6 5.6 6 .7-4.4 4.1 1.2 6L12 16.9 6.6 19.4l1.2-6L3.4 9.3l6-.7z"/>'),
    down: svg('<path d="M12 4v11M7 10l5 5 5-5M5 20h14"/>'),
    up: svg('<path d="M12 20V9M7 14l5-5 5 5M5 4h14"/>'),
    check: svg('<path d="M5 12.5l4.5 4.5L19 7.5"/>', 2.2)
  };

  function pill(r, xs) {
    var k = r.k, m = { g: 'da-signal--strong', y: 'da-signal--flat', b: 'da-signal--broken', n: 'da-signal--flat' };
    return '<span class="da-signal ' + m[k] + ' tk-pill' + (xs ? ' tk-pill--xs' : '') + '">' + esc(label(r)) + '</span>';
  }
  function pillSig(sig, xs) { return pill({ k: KEY[sig] || 'n', sig: sig }, xs); }
  function ring(bp, size, soft) {
    var ok = fin(bp), v = ok ? Math.max(0, Math.min(100, Math.round(bp))) : 0;
    return '<span class="da-ring da-ring--bp tk-ring tk-ring--' + size + (soft ? ' tk-ring--soft' : '') + '" role="img" aria-label="' +
      (ok ? 'BorsaPusula Skoru ' + v + ' / 100' : 'BorsaPusula Skoru yok') + '"><svg viewBox="0 0 100 100" aria-hidden="true">' +
      '<circle class="da-ring-track" cx="50" cy="50" r="44"/>' +
      (ok ? '<circle class="da-ring-arc" cx="50" cy="50" r="44" pathLength="100" stroke-dasharray="' + v + ' 100"/>' : '') +
      '</svg><b class="da-ring-num" aria-hidden="true">' + (ok ? v : '—') + '</b></span>';
  }

  /* ── model ── */
  function num(v) { return (v === null || v === undefined || v === '') ? null : (fin(+v) ? +v : null); }
  function norm(it) {
    return {
      t: String(it.ticker || '').toUpperCase(), n: it.name || '', sig: it.signal || null, k: KEY[it.signal] || 'n',
      p: num(it.price), c: num(it.change_pct), bars: num(it.signal_bars), sd: it.signal_date || null, prev: it.prev_signal || null,
      bp: num(it.bp != null ? it.bp : it.borsapusula_skoru), q: num(it.qty), cost: num(it.cost)
    };
  }
  function isPos(r) { return r.q > 0 && r.cost > 0; }
  function changed(r) { return r.bars !== null && r.bars <= 1; }
  function val(r) { return fin(r.p) ? r.q * r.p : null; }
  function prevP(r) { return (fin(r.p) && fin(r.c)) ? Math.round(r.p / (1 + r.c / 100) * 100) / 100 : null; }
  function order(a, b) {
    return ((changed(b) ? 1 : 0) - (changed(a) ? 1 : 0)) || ((fin(b.bp) ? b.bp : -1) - (fin(a.bp) ? a.bp : -1)) || a.t.localeCompare(b.t, 'tr');
  }
  function find(t) { for (var i = 0; i < S.items.length; i++) if (S.items[i].t === t) return S.items[i]; return null; }
  function positions() { return S.items.filter(isPos); }
  function totals(P) {
    var v = 0, c = 0, pv = 0, n = 0;
    P.forEach(function (r) { var x = val(r), pp = prevP(r); if (x === null || pp === null) return; v += x; c += r.q * r.cost; pv += r.q * pp; n++; });
    return { n: n, v: v, kz: v - c, kzp: c ? (v / c - 1) * 100 : null, ss: v - pv, ssp: pv ? (v / pv - 1) * 100 : null };
  }
  function roundPct(ws) {
    var s = ws.reduce(function (a, b) { return a + b; }, 0);
    if (!s) return ws.map(function () { return 0; });
    var raw = ws.map(function (w) { return w / s * 100; }), fl = raw.map(Math.floor), rest = 100 - fl.reduce(function (a, b) { return a + b; }, 0);
    raw.map(function (x, i) { return [x - fl[i], i]; }).sort(function (a, b) { return b[0] - a[0]; }).slice(0, rest).forEach(function (x) { fl[x[1]]++; });
    return fl;
  }
  function stateShares(rows, w) {
    var ks = ['g', 'y', 'b'], sums = ks.map(function (k) { return rows.filter(function (r) { return r.k === k; }).reduce(function (a, r) { return a + (w(r) || 0); }, 0); });
    var p = roundPct(sums), o = {};
    ks.forEach(function (k, i) { o[k] = p[i]; });
    return o;
  }
  var PH = { g: "Güçlü Trend'de", y: "Yatay'da", b: "Trend Bozuldu'da" };
  function capHTML(Sh, pf, n) {
    var pre = pf ? '%' : '';
    var lead = Sh.g ? '<b>' + (pf ? 'Portföyün ' : n + ' hisseden ') + pre + Sh.g + poss(Sh.g) + ' ' + PH.g + '</b>'
      : '<b>' + (pf ? 'Portföyde' : 'Listede') + " Güçlü Trend'de hisse yok</b>";
    var rest = ['y', 'b'].filter(function (k) { return Sh[k]; }).map(function (k) { return pre + Sh[k] + poss(Sh[k]) + ' ' + PH[k]; });
    return lead + (rest.length ? ' · ' + rest.join(' · ') : '');
  }
  function trSub(r) {
    if (changed(r)) return 'son seansta' + (r.prev ? ' · önceki: ' + esc(sigLabel(r.prev)) : '');
    return (r.sd && typeof bpSinceText === 'function') ? bpSinceText(r.sd) : '';
  }
  function phone() { return MQ.matches; }
  function modeNow() {
    if (S.mode) return S.mode;
    return positions().length ? 'pf' : 'list';
  }

  /* ── sayfa basi ── */
  function statHTML() {
    if (S.phase === 'out') return '';
    if (S.phase === 'loading' || S.phase === 'boot') return '<span class="da-skel da-skel--line tk-skl"></span>';
    if (S.phase === 'error') return 'Takip listen yüklenemedi.';
    var L = S.items;
    if (!L.length) return 'Listen boş · takip ettiğin hisseler burada toplanır';
    var ch = L.filter(changed).length, d = dayMonth(S.asof);
    return '<b>' + L.length + ' hisse takipte</b> · ' + (ch ? ch + loc(ch) + ' son seansta durum değişti' : 'son seansta durum değişen yok') +
      (d && !phone() ? ' · ' + d + ' kapanışı' : '');
  }
  function mi(act, ic, l, s) {
    return '<button type="button" role="menuitem" tabindex="-1" data-act="' + act + '">' + ic + '<span>' + l + '</span>' + (s ? '<span class="tk-ms">' + s + '</span>' : '') + '</button>';
  }
  function menuHTML() {
    var n = S.items.length, np = positions().length;
    if (S.confirmClear) {
      return '<div class="tk-menu" id="tkMenu" role="menu" aria-label="Liste işlemleri"><div class="tk-cf" role="none"><b>Liste temizlensin mi?</b>' +
        n + ' hisse' + (np ? ' ve ' + np + ' pozisyon' : '') + ' silinir; 5 saniye içinde geri alabilirsin.<div class="tk-cfb" role="none">' +
        '<button type="button" role="menuitem" tabindex="-1" class="tk-gb" data-act="clear-no">Vazgeç</button>' +
        '<button type="button" role="menuitem" tabindex="-1" class="tk-okb" data-act="clear-yes">Temizle</button></div></div></div>';
    }
    return '<div class="tk-menu" id="tkMenu" role="menu" aria-label="Liste işlemleri">' +
      mi('exp-json', IC.down, 'JSON olarak indir', 'yedek') + mi('exp-csv', IC.down, 'CSV olarak indir', 'Excel için') +
      mi('imp', IC.up, 'İçe aktar', 'JSON yedeğinden') + '<hr role="separator">' + mi('clear', IC.trash, 'Listeyi temizle', '') + '</div>';
  }
  function ctlHTML() {
    if (S.phase !== 'in' || !S.items.length) return '';
    var m = phone(), md = modeNow();
    var seg = '<div class="tk-seg" role="group" aria-label="Görünüm">' + [['list', 'Liste'], ['pf', 'Portföy']].map(function (o) {
      return '<button type="button" data-act="mode" data-v="' + o[0] + '" aria-pressed="' + (md === o[0]) + '">' + o[1] + '</button>';
    }).join('') + '</div>';
    var add = '<button type="button" class="tk-btnp" data-act="add" aria-haspopup="dialog" aria-expanded="' + !!S.add + '">' + IC.plus + (m ? 'Ekle' : 'Hisse ekle') + '</button>';
    var more = '<button type="button" class="tk-ibtn" data-act="menu" aria-haspopup="menu" aria-expanded="' + !!S.menu + '"' + (S.menu ? ' aria-controls="tkMenu"' : '') + ' aria-label="Liste işlemleri">' + IC.more + '</button>';
    return seg + add + more + (S.menu ? menuHTML() : '') + (S.add && !m ? popHTML() : '');
  }

  /* ── hisse ekle (evren tembel: /api/tarama) ── */
  function loadUniverse() {
    if (S.uniState === 'loading' || S.uniState === 'ok') return;
    S.uniState = 'loading';
    fetch('/api/tarama', { credentials: 'same-origin' }).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    }).then(function (j) {
      /* K-BK: bos/bozuk govde "hisse yok" demek degildir. */
      if (!j || !Array.isArray(j.results) || !j.results.length) throw new Error('beklenmeyen govde');
      S.uni = j.results.filter(function (s) { return s && s.ticker; }).map(function (s) {
        var r = norm(s);
        r.sec = s.sector || '';
        r.ft = bpTrFold(r.t); r.fn = bpTrFold(r.n);
        return r;
      });
      S.uniState = 'ok';
    }).catch(function (e) {
      console.warn('hisse evreni yuklenemedi:', e);
      S.uniState = 'error';
    }).then(function () { renderRes(); });
  }
  function search(q) {
    var qf = bpTrFold(q.trim());
    if (!qf || !S.uni) return [];
    var out = [];
    S.uni.forEach(function (r) {
      var sc = null;
      if (r.ft.indexOf(qf) === 0) sc = 0;
      else if (r.ft.indexOf(qf) > 0) sc = 1;
      else if ((' ' + r.fn).indexOf(' ' + qf) >= 0) sc = 2;
      else if (r.fn.indexOf(qf) >= 0) sc = 3;
      if (sc !== null) out.push([sc, r]);
    });
    out.sort(function (a, b) { return a[0] - b[0] || (b[1].bp || 0) - (a[1].bp || 0) || a[1].t.localeCompare(b[1].t, 'tr'); });
    return out.slice(0, 6).map(function (x) { return x[1]; });
  }
  /* Oneriler: kapsamda BorsaPusula Skoru en yuksek, listede olmayan ve
     Trend Bozuldu olmayan hisseler (long-only: dusen hisse onerilmez). */
  function suggest(n) {
    if (!S.uni) return [];
    return S.uni.filter(function (r) { return !find(r.t) && r.k !== 'b' && fin(r.bp); })
      .sort(function (a, b) { return b.bp - a.bp || a.t.localeCompare(b.t, 'tr'); }).slice(0, n);
  }
  function uniStateHTML() {
    if (S.uniState === 'error') {
      return '<div class="da-empty da-empty--error tk-uerr" role="alert"><span>Hisse listesi yüklenemedi.</span><button type="button" class="da-retry" data-act="uni-retry">Yeniden dene</button></div>';
    }
    return '<p class="tk-rh">Hisseler yükleniyor…</p><div class="tk-rskel"><span class="da-skel"></span><span class="da-skel"></span><span class="da-skel"></span></div>';
  }
  function resRow(r) {
    var inList = !!find(r.t), pf = modeNow() === 'pf', on = S.pick === r.t && !inList;
    var h = '<li class="tk-ri' + (on ? ' on' : '') + '"><div class="tk-rim"><span class="tk-rit">' + esc(r.t) + pill(r, true) + '</span><span class="tk-rin">' + esc(r.n) + '</span></div>' +
      ring(r.bp, 34, r.k === 'b') +
      (inList ? '<span class="tk-inl">' + IC.check + 'Listede</span>'
        : '<button type="button" class="tk-rb" data-act="pick" data-t="' + esc(r.t) + '"' + (pf ? ' aria-expanded="' + on + '"' : '') + ' aria-label="Ekle: ' + esc(r.t) + '">Ekle</button>');
    if (on) {
      h += '<div class="tk-rif" role="group" aria-label="' + esc(r.t) + ' için adet ve maliyet">' +
        '<label class="tk-fld">Adet<input class="tk-inp" data-in="aq" inputmode="numeric" autocomplete="off" placeholder="örn. 100"></label>' +
        '<label class="tk-fld">Maliyet (₺)<input class="tk-inp" data-in="ac" inputmode="decimal" autocomplete="off" placeholder="örn. ' + esc(fin(r.p) ? nf2.format(r.p) : '10,00') + '"></label>' +
        '<button type="button" class="tk-okb" data-act="addgo" data-t="' + esc(r.t) + '">Listeye ekle</button>' +
        '<p class="tk-ferr" role="alert" hidden></p></div>';
    }
    return h + '</li>';
  }
  function resHTML() {
    if (S.uniState !== 'ok') return uniStateHTML();
    var q = S.q.trim(), rows, head;
    if (q) { rows = search(q); head = rows.length ? rows.length + ' sonuç' : '“' + esc(q) + '” ile eşleşen hisse yok'; }
    else { rows = suggest(3); head = "BorsaPusula Skoru en yüksek hisseler<span>Listende olmayan, Trend Bozuldu durumunda olmayan</span>"; }
    return '<p class="tk-rh">' + head + '</p><ul class="tk-res">' + rows.map(resRow).join('') + '</ul>';
  }
  function addBody() {
    return '<label class="tk-srch">' + IC.search + '<input type="search" class="tk-q" data-in="q" value="' + esc(S.q) + '" placeholder="Kod ya da şirket adı" aria-label="Hisse ara" autocomplete="off" spellcheck="false"></label>' +
      '<div class="tk-resw" aria-live="polite">' + resHTML() + '</div>' +
      (modeNow() === 'pf' ? '<p class="tk-ahint">Portföy açık: "Ekle"den sonra adet ve maliyet isteğe bağlı; boş bırakırsan hisse yalnız takip edilir.</p>' : '');
  }
  function popHTML() {
    return '<div class="tk-pop" role="dialog" aria-modal="false" aria-labelledby="tkAddH"><div class="tk-pop-h"><h2 id="tkAddH">Hisse ekle</h2>' +
      '<span class="tk-esc"><kbd>Esc</kbd> ile kapanır</span><button type="button" class="tk-xbtn" data-act="close" aria-label="Kapat">' + IC.x + '</button></div>' +
      '<div class="tk-ab">' + addBody() + '</div></div>';
  }
  function sheetHTML() {
    if (!S.add || !phone()) return '';
    return '<div class="tk-scrim" data-act="close"></div><div class="tk-sheet' + (S.enter ? ' enter' : '') + '" role="dialog" aria-modal="true" aria-labelledby="tkAddH">' +
      '<div class="tk-grab" aria-hidden="true"></div><div class="tk-sh-h"><h2 id="tkAddH">Hisse ekle</h2><button type="button" class="tk-xbtn" data-act="close" aria-label="Kapat">' + IC.x + '</button></div>' +
      '<div class="tk-sh-b">' + addBody() + '</div></div>';
  }
  function renderRes() {
    var w = document.querySelector('.tk-resw');
    if (w) w.innerHTML = resHTML();
    var o = app.querySelector('.tk-ores');
    if (o) o.innerHTML = oresHTML();
  }

  /* ── ozet (portfoy) / durum seridi ── */
  function heroHTML() {
    var P = positions(), T = totals(P), m = phone(), d = dayMonth(S.asof);
    var parts = T.n ? nf2.format(T.v).split(',') : ['—', ''];
    var segs = P.filter(function (r) { return val(r) !== null; }).sort(function (a, b) { return ORDER.indexOf(a.k) - ORDER.indexOf(b.k) || val(b) - val(a); });
    var W = roundPct(segs.map(val)), Sh = stateShares(P, val), cap = capHTML(Sh, true);
    return '<section class="tk-hero" aria-label="Portföy özeti"><div class="tk-hero-top"><div><span class="tk-lab">Portföy değeri' + (d ? ' · ' + d + ' kapanışı' : '') + '</span>' +
      '<b class="tk-big">' + parts[0] + (T.n ? '<small>,' + parts[1] + ' ₺</small>' : '') + '</b></div>' +
      '<div class="tk-kpis"><div class="tk-kpi"><span class="tk-lab">Toplam kâr/zarar</span><b class="' + cls(T.kz) + '">' + (T.n ? stl(T.kz) : '—') + '</b><span class="tk-kp ' + cls(T.kzp) + '">' + pct(T.kzp) + '</span></div>' +
      '<div class="tk-kpi"><span class="tk-lab">Son seans</span><b class="' + cls(T.ss) + '">' + (T.n ? stl(T.ss) : '—') + '</b><span class="tk-kp ' + cls(T.ssp) + '">' + pct(T.ssp) + '</span></div></div></div>' +
      '<div class="tk-alloc" role="img" aria-label="' + esc(cap.replace(/<[^>]+>/g, '')) + '">' + segs.map(function (r, i) {
        var w = W[i];
        return '<i class="' + r.k + '" data-w="' + Math.round(val(r)) + '">' + (w >= (m ? 15 : 8) ? esc(r.t) + (m ? '' : '<em>%' + w + '</em>') : '') + '</i>';
      }).join('') + '</div><p class="tk-acap">' + cap + '</p></section>';
  }
  function countHTML() {
    var L = S.items, Sh = { g: 0, y: 0, b: 0 };
    L.forEach(function (r) { if (Sh[r.k] !== undefined) Sh[r.k]++; });
    var cap = capHTML(Sh, false, L.length);
    var segs = L.slice().sort(function (a, b) { return ORDER.indexOf(a.k) - ORDER.indexOf(b.k) || (b.bp || 0) - (a.bp || 0); });
    return '<section class="tk-lhead" aria-label="Durum dağılımı"><div class="tk-alloc" role="img" aria-label="' + esc(cap.replace(/<[^>]+>/g, '')) + '">' +
      segs.map(function (r) { return '<i class="' + r.k + '">' + (L.length <= 12 ? esc(r.t) : '') + '</i>'; }).join('') + '</div><p class="tk-acap">' + cap + '</p>' +
      (modeNow() === 'pf' ? '<p class="tk-acap">Adet ve maliyet girdiğin hisseler burada portföy özetine girer: kalem ya da "Adet ve maliyet ekle".</p>' : '') + '</section>';
  }
  function chsHTML() {
    var ch = S.items.filter(changed).sort(order);
    if (!ch.length) return '';
    return '<div class="tk-chs" role="note" aria-label="Son seansta değişenler"><span class="tk-tl">' + IC.star + 'Son seansta değişenler</span>' +
      ch.map(function (r, i) {
        var lab = r.prev ? esc(r.t) + ': ' + esc(sigLabel(r.prev)) + ' durumundan ' + esc(label(r)) + ' durumuna geçti' : esc(r.t) + ': son seansta ' + esc(label(r)) + ' durumuna geçti';
        return (i ? '<span class="tk-dsep" aria-hidden="true">·</span>' : '') + '<a class="tk-chi" href="/hisse/' + esc(r.t) + '" aria-label="' + lab + '"><b>' + esc(r.t) + '</b>' +
          (r.prev ? pillSig(r.prev, true) + '<span class="tk-ar" aria-hidden="true">→</span>' : '') + pill(r, true) + '</a>';
      }).join('') + '</div>';
  }

  /* ── masaustu tablo ── */
  function editRow(r, ncol) {
    return '<tr class="tk-er"><td colspan="' + ncol + '"><div class="tk-erow" role="group" aria-label="' + esc(r.t) + ' için adet ve maliyet"><span class="tk-erl"><b>' + esc(r.t) + '</b> · adet ve maliyet</span>' +
      '<label class="tk-fld">Adet<input class="tk-inp" data-in="eq" inputmode="numeric" autocomplete="off" value="' + (isPos(r) ? r.q : '') + '" placeholder="örn. 100"></label>' +
      '<label class="tk-fld">Maliyet (₺)<input class="tk-inp" data-in="ec" inputmode="decimal" autocomplete="off" value="' + (isPos(r) ? nf2.format(r.cost) : '') + '" placeholder="örn. ' + esc(fin(r.p) ? nf2.format(r.p) : '10,00') + '"></label>' +
      '<span class="tk-ehint">Adedi boş bırakırsan hisse yalnız takipte kalır.</span>' +
      '<button type="button" class="tk-gb" data-act="cancel">Vazgeç</button><button type="button" class="tk-okb" data-act="save" data-t="' + esc(r.t) + '">Kaydet</button>' +
      '<p class="tk-ferr" role="alert" hidden></p></div></td></tr>';
  }
  function rowD(r, ncol, pf) {
    var pos = isPos(r), ed = S.edit === r.t;
    var h = '<tr class="tk-r ' + r.k + (changed(r) ? ' ch' : '') + (ed ? ' ed' : '') + '"><td class="c-hs"><a class="tk-rl" href="/hisse/' + esc(r.t) + '"><b>' + esc(r.t) + '</b></a><span class="tk-nm">' + esc(r.n) + '</span></td>' +
      '<td class="c-bp">' + ring(r.bp, 36, r.k === 'b') + '</td><td class="c-tr">' + pill(r) + '<span class="tk-sl">' + trSub(r) + '</span></td>' +
      '<td class="num">' + tl(r.p) + '<span class="tk-sl ' + cls(r.c) + '">' + pct(r.c) + '</span></td>';
    if (pf) {
      if (pos) {
        var kz = fin(r.p) ? r.q * (r.p - r.cost) : null, kzp = fin(r.p) ? (r.p / r.cost - 1) * 100 : null;
        h += '<td class="num">' + nf0.format(r.q) + '</td><td class="num">' + tl(r.cost) + '</td><td class="num"><span class="' + cls(kz) + '">' + stl(kz) + '</span><span class="tk-sl ' + cls(kzp) + '">' + pct(kzp) + '</span></td>';
      } else {
        h += '<td class="num" colspan="3">' + (ed ? '' : '<button type="button" class="tk-gb tk-gb--sm" data-act="edit" data-t="' + esc(r.t) + '" aria-expanded="false">' + IC.plus + 'Adet ve maliyet ekle</button>') + '</td>';
      }
    }
    h += '<td class="c-act">' + (pf && pos ? '<button type="button" class="tk-ib" data-act="edit" data-t="' + esc(r.t) + '" aria-expanded="' + ed + '" aria-label="Adet ve maliyeti düzenle: ' + esc(r.t) + '">' + IC.pencil + '</button>' : '') +
      '<button type="button" class="tk-ib" data-act="del" data-t="' + esc(r.t) + '" aria-label="Listeden çıkar: ' + esc(r.t) + '">' + IC.x + '</button></td></tr>';
    return h + (ed ? editRow(r, ncol) : '');
  }
  function tableHTML() {
    var pf = modeNow() === 'pf', L = S.items, ncol = pf ? 8 : 5, body = '';
    var th = '<thead><tr><th scope="col">Hisse</th><th scope="col">Skor</th><th scope="col">Trend</th><th scope="col" class="num">Fiyat<span class="tk-ths">son seans</span></th>' +
      (pf ? '<th scope="col" class="num">Adet</th><th scope="col" class="num">Maliyet</th><th scope="col" class="num">Kâr/zarar</th>' : '') + '<th scope="col"><span class="sr-only">İşlemler</span></th></tr></thead>';
    function rows(Ar) { return Ar.slice().sort(order).map(function (r) { return rowD(r, ncol, pf); }).join(''); }
    if (pf) {
      var P = L.filter(isPos), W = L.filter(function (r) { return !isPos(r); });
      if (P.length) body += '<tbody><tr class="tk-gh"><th scope="rowgroup" colspan="' + ncol + '"><b>Portföyde</b><span>' + P.length + ' hisse · ' + tl(totals(P).v) + '</span></th></tr>' + rows(P) + '</tbody>';
      if (W.length) body += '<tbody><tr class="tk-gh"><th scope="rowgroup" colspan="' + ncol + '"><b>Yalnız takipte</b><span>' + W.length + ' hisse · adet ve maliyet girersen portföye geçer</span></th></tr>' + rows(W) + '</tbody>';
    } else body = '<tbody>' + rows(L) + '</tbody>';
    return '<div class="tk-tbw"><table class="tk-tb' + (pf ? ' tk-tb--pf' : '') + '"><caption class="sr-only">Takip listesi</caption>' + th + body + '</table></div>';
  }

  /* ── telefon listesi ── */
  function editBlockM(r) {
    return '<div class="tk-erow tk-erow--m" role="group" aria-label="' + esc(r.t) + ' için adet ve maliyet">' +
      '<label class="tk-fld">Adet<input class="tk-inp" data-in="eq" inputmode="numeric" autocomplete="off" value="' + (isPos(r) ? r.q : '') + '" placeholder="örn. 100"></label>' +
      '<label class="tk-fld">Maliyet (₺)<input class="tk-inp" data-in="ec" inputmode="decimal" autocomplete="off" value="' + (isPos(r) ? nf2.format(r.cost) : '') + '" placeholder="örn. ' + esc(fin(r.p) ? nf2.format(r.p) : '10,00') + '"></label>' +
      '<span class="tk-ehint">Adedi boş bırakırsan hisse yalnız takipte kalır.</span>' +
      '<button type="button" class="tk-gb" data-act="cancel">Vazgeç</button><button type="button" class="tk-okb" data-act="save" data-t="' + esc(r.t) + '">Kaydet</button>' +
      '<p class="tk-ferr" role="alert" hidden></p></div>';
  }
  function rowM(r, pf) {
    var pos = pf && isPos(r), em = S.editMode;
    var l2 = pos ? nf0.format(r.q) + ' adet · maliyet ' + tl(r.cost) : (r.prev && changed(r) ? 'önceki: ' + esc(sigLabel(r.prev)) : esc(r.n));
    var l3 = '';
    if (pos) {
      var kz = fin(r.p) ? r.q * (r.p - r.cost) : null, kzp = fin(r.p) ? (r.p / r.cost - 1) * 100 : null;
      l3 = '<span class="tk-mk">Kâr/zarar <b class="' + cls(kz) + '">' + stl(kz) + ' · ' + pct(kzp) + '</b></span>';
    }
    var inner = ring(r.bp, 40, r.k === 'b') + '<span class="tk-mt"><b>' + esc(r.t) + pill(r, true) + '</b><span>' + l2 + '</span></span>' +
      (em ? '' : '<span class="tk-mp"><b>' + tl(r.p) + '</b><span class="' + cls(r.c) + '">' + pct(r.c) + '</span></span>') + l3;
    var k = 'tk-mr ' + r.k + (changed(r) ? ' ch' : '') + (pos ? ' p3' : '');
    if (em) {
      return '<li class="tk-mli"><div class="' + k + ' em">' + inner + '<span class="tk-mbtns">' +
        (pf ? '<button type="button" class="tk-mdel" data-act="edit" data-t="' + esc(r.t) + '" aria-expanded="' + (S.edit === r.t) + '" aria-label="Adet ve maliyeti düzenle: ' + esc(r.t) + '">' + IC.pencil + '</button>' : '') +
        '<button type="button" class="tk-mdel" data-act="del" data-t="' + esc(r.t) + '" aria-label="Listeden çıkar: ' + esc(r.t) + '">' + IC.x + '</button></span></div>' +
        (S.edit === r.t ? editBlockM(r) : '') + '</li>';
    }
    return '<li class="tk-mli"><a class="' + k + '" href="/hisse/' + esc(r.t) + '">' + inner + '</a></li>';
  }
  function listM() {
    var L = S.items, pf = modeNow() === 'pf', h = '', first = true;
    var groups = pf ? [['Portföyde', L.filter(isPos)], ['Yalnız takipte', L.filter(function (r) { return !isPos(r); })]] : [['Takip listesi', L]];
    groups.forEach(function (g) {
      var rows = g[1].slice().sort(order);
      if (!rows.length) return;
      h += '<section class="tk-mg" aria-label="' + g[0] + '"><div class="tk-mgh"><b>' + g[0] + '</b><span>' + rows.length + ' hisse</span>' +
        (first ? '<button type="button" class="tk-lnk" data-act="emode" aria-pressed="' + !!S.editMode + '">' + (S.editMode ? 'Bitti' : 'Düzenle') + '</button>' : '') +
        '</div><ul class="tk-mrows">' + rows.map(function (r) { return rowM(r, pf); }).join('') + '</ul></section>';
      first = false;
    });
    return '<div class="tk-ml">' + h + '</div>';
  }

  /* ── bildirimler + hesap ── */
  function swRow(k, t, s) {
    var nt = (S.me && S.me.notify) || {}, on = !!nt[k], id = 'tkSw-' + k;
    return '<div class="tk-swr"><div><b id="' + id + '">' + t + '</b><span id="' + id + '-d">' + s + '</span></div>' +
      '<button type="button" class="tk-sw" role="switch" aria-checked="' + on + '" aria-labelledby="' + id + '" aria-describedby="' + id + '-d" data-act="sw" data-k="' + k + '"><i></i></button></div>';
  }
  function prefsHTML() {
    var m = S.me || {}, kv = isoDate(m.kvkk_consent_ts);
    var acct = S.confirmDel
      ? '<div class="tk-ucf" role="group" aria-labelledby="tkDelH"><b id="tkDelH">Hesap silinsin mi?</b>Takip listen, pozisyonların ve bildirim tercihlerin kalıcı olarak silinir; geri alınamaz.' +
        '<div class="tk-cfb"><button type="button" class="tk-gb" data-act="del-no">Vazgeç</button><button type="button" class="tk-okb tk-okb--del" data-act="del-yes">Hesabı sil</button></div></div>'
      : '<div class="tk-accb"><button type="button" class="tk-gb" data-act="logout">Çıkış yap</button><button type="button" class="tk-lnk tk-lnk--mut" data-act="del-acc">Hesabı sil</button></div>';
    return '<section class="tk-prefs" aria-labelledby="tkPrH"><h2 id="tkPrH">Bildirimler</h2>' +
      '<p class="tk-em"><span>E-posta</span><b>' + esc(m.email_masked || '') + '</b>' + (m.confirmed_at ? '<span class="tk-okt">' + IC.check + 'onaylı</span>' : '') + '</p>' +
      swRow('trend', 'Durum değişince e-posta', 'Takip ettiğin bir hissenin trend durumu değişince, o akşam kapanıştan sonra tek e-posta.') +
      swRow('bulten', 'Akşam Bülteni', 'Her işlem günü kapanıştan sonra seansın özeti; takip ettiklerin en üstte.') +
      '<p class="tk-kvn">E-posta adresin yalnız giriş kodu ve bu bildirimler için kullanılır. ' + (kv ? 'KVKK onayı ' + kv + ' · ' : '') +
      '<a class="da-link" href="/gizlilik">Aydınlatma metni</a></p>' + acct + '</section>';
  }
  function storeHTML() {
    return '<p class="tk-store">Liste <b>' + esc((S.me && S.me.email_masked) || '') + '</b> hesabına bağlı · girdiğin her cihazda aynı liste görünür.</p>';
  }

  /* ── bos liste ── */
  function oresHTML() {
    if (S.uniState !== 'ok') return uniStateHTML();
    var q = (S.q || '').trim(), rows, head;
    if (q) { rows = search(q).slice(0, 5); head = rows.length ? 'Arama sonuçları' : '“' + esc(q) + '” ile eşleşen hisse yok'; }
    else { rows = suggest(3); head = "BorsaPusula Skoru en yüksek üç hisse"; }   /* C-41: Keşfet liste API'si gelince taslaktaki "Keşfet'ten üç öneri" + liste adı */
    return '<h3>' + head + '</h3><ul class="tk-sug">' + rows.map(function (r) {
      return '<li><div class="tk-sgr">' + ring(r.bp, 40, r.k === 'b') + '<div class="tk-rim"><span class="tk-sgt">' + esc(r.t) + pill(r, true) + '</span><span class="tk-sgn">' + esc(r.n) + '</span>' +
        (r.sec ? '<span class="tk-sgl">' + esc(r.sec) + '</span>' : '') + '</div>' +
        (find(r.t) ? '<span class="tk-inl">' + IC.check + 'Listede</span>' : '<button type="button" class="tk-fbtn2" data-act="ofollow" data-t="' + esc(r.t) + '" aria-label="Takip et: ' + esc(r.t) + '">Takip et</button>') +
        '</div></li>';
    }).join('') + '</ul>';
  }
  function onbHTML() {
    return '<section class="tk-onb" aria-labelledby="tkOnbH"><h2 id="tkOnbH">İlk hisseni ekle</h2><p>Takip ettiğin hissenin trend durumu değişince o akşam e-posta gelir. İstersen adet ve maliyet girip portföyünü de burada izlersin.</p>' +
      '<label class="tk-osrch">' + IC.search + '<input type="search" data-in="oq" value="' + esc(S.q || '') + '" placeholder="Takip etmek istediğin hisseyi ara…" aria-label="Takip etmek istediğin hisseyi ara" autocomplete="off" spellcheck="false"></label>' +
      '<div class="tk-ores" aria-live="polite">' + oresHTML() + '</div></section>';
  }

  function skelHTML() {
    var r = '';
    for (var i = 0; i < 6; i++) r += '<span class="da-skel tk-skr"></span>';
    return '<div class="tk-skel" aria-busy="true" aria-label="Takip listen yükleniyor"><span class="da-skel tk-skh"></span><div class="tk-skl2">' + r + '</div></div>';
  }
  function errHTML() {
    return '<div class="da-empty da-empty--error tk-err" role="alert"><span><b>Takip listen yüklenemedi.</b> Bağlantını kontrol edip yeniden dene; listen hesabında duruyor.</span>' +
      '<button type="button" class="da-retry" data-act="retry">Yeniden dene</button></div>';
  }

  function appHTML() {
    if (S.phase === 'boot' || S.phase === 'loading') return skelHTML();
    if (S.phase === 'error') return errHTML();
    if (S.phase === 'out') return '<div class="tk-login"></div>';
    var L = S.items, h = '';
    if (!L.length) return '<div class="tk-grid"><div class="tk-main">' + onbHTML() + '</div><aside class="tk-rail" aria-label="Bildirim tercihleri ve hesap">' + prefsHTML() + '</aside></div>';
    h += (modeNow() === 'pf' && positions().length) ? heroHTML() : countHTML();
    if (phone()) return h + chsHTML() + listM() + storeHTML() + prefsHTML();
    return h + '<div class="tk-grid"><div class="tk-main">' + chsHTML() + tableHTML() + storeHTML() + '</div><aside class="tk-rail" aria-label="Bildirim tercihleri ve hesap">' + prefsHTML() + '</aside></div>';
  }

  /* ── cizim + odak koruma ── */
  function fkey(el) {
    var a = el && el.closest && el.closest('[data-act],[data-in]');
    if (!a) return null;
    var d = a.dataset;
    return [d.act || '', d.v || '', d.k || '', d.t || '', d['in'] || ''].join('|');
  }
  function byKey(key) {
    var els = document.querySelectorAll('#main-content [data-act], #main-content [data-in], #tkLayer [data-act], #tkLayer [data-in]');
    for (var i = 0; i < els.length; i++) if (fkey(els[i]) === key) return els[i];
    return null;
  }
  function focusSel(sel) {
    var t = typeof sel === 'string' ? document.querySelector(sel) : sel;
    if (t) t.focus({ preventScroll: false });
  }
  function render(sel) {
    var ae = document.activeElement, key = (!sel && ae && ae !== document.body) ? fkey(ae) : null;
    var shb = document.querySelector('.tk-sh-b'), sb = shb ? shb.scrollTop : 0;
    var sh = statHTML();
    if (statEl && sh !== lastStat) { statEl.innerHTML = sh; lastStat = sh; }
    if (ctlEl) ctlEl.innerHTML = ctlHTML();
    app.innerHTML = appHTML();
    renderLayer();
    var shb2 = document.querySelector('.tk-sh-b');
    if (shb2) shb2.scrollTop = sb;
    S.enter = false;
    applyWidths();
    if (S.phase === 'out') mountLoginPanel();
    if (sel) focusSel(sel);
    else if (key) { var t = byKey(key); if (t) t.focus({ preventScroll: true }); }
  }
  function renderLayer() {
    if (!layerEl) return;
    var want = S.add && phone() && S.phase === 'in';
    if (!want) {
      if (sheetRelease) { var rel = sheetRelease; sheetRelease = null; rel(); }
      layerEl.innerHTML = '';
      document.body.classList.remove('tk-lock');
      return;
    }
    /* Acik paneli yeniden kurma: odak tuzagi ve arama kutusu yerinde kalir. */
    if (layerEl.querySelector('.tk-sheet')) { renderRes(); return; }
    layerEl.innerHTML = sheetHTML();
    document.body.classList.add('tk-lock');
  }
  function applyWidths() {
    [].forEach.call(app.querySelectorAll('.tk-alloc i[data-w]'), function (i) { i.style.flexGrow = i.getAttribute('data-w'); });
  }
  function mountLoginPanel() {
    var el = app.querySelector('.tk-login');
    if (!el) return;
    login = A.mountLogin(el, {
      onSuccess: function (me, imported) {
        S.me = me;
        var msg = A.importMessage(imported);
        load(msg);
      }
    });
  }

  /* ── bildirim (toast) ── */
  function say(msg) { if (liveEl) { liveEl.textContent = ''; setTimeout(function () { liveEl.textContent = msg; }, 30); } }
  function toastHTML(T) {
    var left = Math.max(1, Math.ceil((T.paused ? T.left : T.end - Date.now()) / 1000));
    return '<div class="tk-toast' + (T.undo ? ' und' : '') + (T.err ? ' err' : '') + (T.paused ? ' paused' : '') + '"><span class="tk-tm">' + esc(T.msg) + '</span>' +
      (T.undo ? '<span class="tk-tsec" aria-hidden="true">' + left + ' sn</span><button type="button" class="tk-ub" data-act="undo">Geri al</button><i class="tk-bar" aria-hidden="true"></i>' : '') + '</div>';
  }
  function clearToast() { clearTimeout(tTimer); clearInterval(tTick); toast = null; if (toastEl) toastEl.innerHTML = ''; }
  function armToast() {
    clearTimeout(tTimer); clearInterval(tTick);
    if (!toast) return;
    tTimer = setTimeout(function () {
      var had = toastEl && toastEl.contains(document.activeElement);
      clearToast();
      if (had) focusSel(phone() ? '[data-act="add"]' : '.tk-rl, [data-act="add"], [data-in="oq"]');
    }, Math.max(0, toast.end - Date.now()));
    if (toast.undo) tTick = setInterval(function () {
      var s = toastEl && toastEl.querySelector('.tk-tsec');
      if (s && toast) s.textContent = Math.max(1, Math.ceil((toast.end - Date.now()) / 1000)) + ' sn';
    }, 250);
  }
  function showToast(T) {
    clearToast();
    T.end = Date.now() + (T.undo ? 5000 : 3600);
    toast = T;
    if (toastEl) toastEl.innerHTML = toastHTML(T);
    armToast();
    say(T.msg + (T.undo ? '. 5 saniye içinde geri alabilirsin.' : ''));
  }
  function pauseToast(on) {
    if (!toast || !toast.undo) return;
    var el = toastEl && toastEl.querySelector('.tk-toast');
    if (on && !toast.paused) { toast.paused = true; toast.left = Math.max(0, toast.end - Date.now()); clearTimeout(tTimer); clearInterval(tTick); if (el) el.classList.add('paused'); }
    else if (!on && toast.paused) { toast.paused = false; toast.end = Date.now() + toast.left; if (el) el.classList.remove('paused'); armToast(); }
  }
  function fail(res, what) {
    var msg = res && res.status === 0 ? what + ' Bağlantı kurulamadı.' : ((res && res.message) || what + ' Yeniden dene.');
    showToast({ msg: msg, err: true });
    if (res && res.status === 401) { S.phase = 'out'; S.items = []; render(); }
  }

  /* ── yukleme ── */
  function load(msg) {
    S.phase = 'loading';
    render();
    var pMe = S.me ? Promise.resolve({ ok: true, status: 200, data: S.me }) : A.me();
    Promise.all([pMe, A.watchlist()]).then(function (rs) {
      var me = rs[0], wl = rs[1];
      if (me.status === 401 || wl.status === 401 || (me.status === 200 && me.data.logged_in === false)) {
        A.clearHint(); S.me = null; S.phase = 'out'; render(); return;
      }
      if (!me.ok || !wl.ok || !Array.isArray(wl.data.items)) { S.phase = 'error'; render(); return; }
      S.me = me.data;
      S.asof = wl.data.asof || null;
      S.items = wl.data.items.map(norm).filter(function (r) { return r.t; });
      S.phase = 'in';
      if (!S.items.length) loadUniverse();
      render();
      if (msg) showToast({ msg: msg });
    });
  }

  /* ── eylemler ── */
  function closeAll() {
    if (S.menu || S.add) {
      var was = S.menu ? 'menu' : 'add';
      S.menu = false; S.add = false; S.confirmClear = false; S.pick = null;
      render('[data-act="' + was + '"]');
      return true;
    }
    if (S.edit) { var et = S.edit; S.edit = null; render('[data-act="edit"][data-t="' + et + '"]'); return true; }
    if (S.confirmDel) { S.confirmDel = false; render('[data-act="del-acc"]'); return true; }
    if (S.editMode) { S.editMode = false; render('[data-act="emode"]'); return true; }
    return false;
  }
  function uniRow(t) { if (!S.uni) return null; for (var i = 0; i < S.uni.length; i++) if (S.uni[i].t === t) return S.uni[i]; return null; }
  function fieldErr(box, msg, inpSel) {
    var p = box && box.querySelector('.tk-ferr');
    if (p) { p.textContent = msg; p.hidden = !msg; }
    [].forEach.call(box ? box.querySelectorAll('.tk-inp') : [], function (x) { x.removeAttribute('aria-invalid'); });
    var inp = inpSel && box ? box.querySelector(inpSel) : null;
    if (inp) { inp.setAttribute('aria-invalid', 'true'); inp.focus(); }
  }
  /* Adet/maliyet okuma: TR ondalik tek kanon (K-BA) + pozisyon dogrulama tek
     kanon (K-BJ). Donus {qty, cost, note} | {err, sel} | null (adet bos). */
  function readPos(box, qSel, cSel, price) {
    var qv = box.querySelector(qSel).value.trim(), cv = box.querySelector(cSel).value.trim();
    if (!qv) return null;
    var qty = bpParseTrNumber(qv);
    if (!bpIsValidLot(qty)) return { err: 'Adet 1 ya da daha büyük bir tam sayı olmalı.', sel: qSel };
    var note = '', cost;
    if (!cv) {
      if (!bpIsValidPrice(price)) return { err: 'Maliyeti yaz (hisse başına ₺).', sel: cSel };
      cost = price; note = ' (maliyet: son kapanış)';
    } else {
      cost = bpParseTrNumber(cv);
      if (!bpIsValidPrice(cost)) return { err: "Maliyet 0'dan büyük bir tutar olmalı (ör. 317,00).", sel: cSel };
    }
    return { qty: qty, cost: Math.round(cost * 10000) / 10000, note: note };
  }

  function addStock(t, qty, cost, note, box) {
    if (S.busy || find(t)) return;
    var u = uniRow(t);
    S.busy = true;
    var req = qty ? A.setPosition(t, qty, cost) : A.add(t);
    req.then(function (res) {
      S.busy = false;
      if (!res.ok) { if (box) fieldErr(box, res.message || 'Eklenemedi. Yeniden dene.'); else fail(res, t + ' eklenemedi.'); return; }
      var r = u ? JSON.parse(JSON.stringify(u)) : norm({ ticker: t });
      r.q = qty || null; r.cost = qty ? cost : null;
      S.items.push(r);
      S.pick = null;
      var wasEmpty = S.items.length === 1;
      if (wasEmpty) { S.q = ''; S.add = false; }
      render(S.add ? '.tk-q' : '.tk-rl[href="/hisse/' + t + '"], .tk-mr[href="/hisse/' + t + '"]');
      showToast({ msg: t + ' listeye eklendi' + (qty ? ' · ' + nf0.format(qty) + ' adet' + (note || '') : '') });
    });
  }
  function delStock(t) {
    var idx = -1;
    S.items.forEach(function (r, i) { if (r.t === t) idx = i; });
    if (idx < 0 || S.busy) return;
    var row = S.items.splice(idx, 1)[0];
    if (S.edit === t) S.edit = null;
    render();
    S.busy = true;
    A.remove(t).then(function (res) {
      S.busy = false;
      if (!res.ok) {
        S.items.splice(Math.min(idx, S.items.length), 0, row);
        render();
        fail(res, t + ' listeden çıkarılamadı.');
        return;
      }
      showToast({ msg: t + ' listeden çıkarıldı', undo: { kind: 'del', row: row, idx: idx } });
      focusSel('.tk-ub');
    });
  }
  function undo() {
    if (!toast || !toast.undo || S.busy) return;
    var u = toast.undo;
    clearToast();
    S.busy = true;
    if (u.kind === 'del') {
      var r = u.row, p = isPos(r) ? A.setPosition(r.t, r.q, r.cost) : A.add(r.t);
      p.then(function (res) {
        S.busy = false;
        if (!res.ok) { fail(res, r.t + ' geri alınamadı.'); return; }
        if (!find(r.t)) S.items.splice(Math.min(u.idx, S.items.length), 0, r);
        render(S.editMode && phone() ? '[data-act="del"][data-t="' + r.t + '"]' : '.tk-rl[href="/hisse/' + r.t + '"], .tk-mr[href="/hisse/' + r.t + '"]');
        say('Geri alındı.');
      });
    } else if (u.kind === 'clear') {
      A.replace(u.list.map(function (x) { return x.t; }), u.list.filter(isPos).map(function (x) { return { ticker: x.t, qty: x.q, cost: x.cost }; })).then(function (res) {
        S.busy = false;
        if (!res.ok) { fail(res, 'Liste geri alınamadı.'); return; }
        S.items = u.list; S.q = '';
        render('[data-act="menu"]');
        say('Geri alındı.');
      });
    }
  }
  function saveEdit(t, box) {
    var r = find(t);
    if (!r || !box || S.busy) return;
    var v = readPos(box, '[data-in="eq"]', '[data-in="ec"]', r.p);
    if (v && v.err) { fieldErr(box, v.err, v.sel); return; }
    S.busy = true;
    if (!v) {
      if (!isPos(r)) { S.busy = false; S.edit = null; render('[data-act="edit"][data-t="' + t + '"]'); return; }
      A.removePosition(t).then(function (res) {
        S.busy = false;
        if (!res.ok) { fieldErr(box, res.message || 'Kaydedilemedi. Yeniden dene.'); return; }
        r.q = null; r.cost = null; S.edit = null;
        render('.tk-rl[href="/hisse/' + t + '"], [data-act="edit"][data-t="' + t + '"]');
        showToast({ msg: t + ' yalnız takipte' });
      });
      return;
    }
    A.setPosition(t, v.qty, v.cost).then(function (res) {
      S.busy = false;
      if (!res.ok) { fieldErr(box, res.message || 'Kaydedilemedi. Yeniden dene.'); return; }
      var pos = res.data.position || {};
      r.q = num(pos.qty) || v.qty; r.cost = num(pos.cost) || v.cost; S.edit = null;
      render('.tk-rl[href="/hisse/' + t + '"], [data-act="edit"][data-t="' + t + '"]');
      showToast({ msg: t + ' güncellendi · ' + nf0.format(r.q) + ' adet' + v.note });
    });
  }
  function clearList() {
    if (S.busy) return;
    var bk = S.items.slice();
    S.busy = true;
    A.replace([], []).then(function (res) {
      S.busy = false;
      if (!res.ok) { S.menu = false; S.confirmClear = false; render('[data-act="menu"]'); fail(res, 'Liste temizlenemedi.'); return; }
      S.items = []; S.menu = false; S.confirmClear = false; S.edit = null; S.editMode = false; S.q = '';
      loadUniverse();
      render('[data-in="oq"]');
      showToast({ msg: 'Liste temizlendi', undo: { kind: 'clear', list: bk } });
    });
  }
  function setPref(k) {
    if (!S.me) return;
    var nt = S.me.notify = S.me.notify || {}, was = !!nt[k], body = {};
    nt[k] = !was; body[k] = !was;
    render('[data-act="sw"][data-k="' + k + '"]');
    A.prefs(body).then(function (res) {
      if (res.ok && res.data.notify) { S.me.notify = res.data.notify; }
      else { nt[k] = was; fail(res, 'Tercih kaydedilemedi.'); }
      render('[data-act="sw"][data-k="' + k + '"]');
    });
  }
  function logout() {
    if (S.busy) return;
    S.busy = true;
    A.logout(false).then(function (res) {
      S.busy = false;
      if (!res.ok) { fail(res, 'Çıkış yapılamadı.'); return; }
      S.me = null; S.items = []; S.phase = 'out'; S.confirmDel = false;
      render();
      showToast({ msg: 'Çıkış yapıldı' });
    });
  }
  function deleteAccount() {
    if (S.busy) return;
    S.busy = true;
    A.deleteAccount().then(function (res) {
      S.busy = false;
      if (!res.ok) { fail(res, 'Hesap silinemedi.'); return; }
      S.me = null; S.items = []; S.phase = 'out'; S.confirmDel = false;
      render();
      showToast({ msg: 'Hesabın ve takip listen silindi' });
    });
  }

  /* ── disa/ice aktarim ── */
  function download(name, text, type) {
    var blob = new Blob([text], { type: type });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url; a.download = name;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  }
  function csvCell(v) {
    v = String(v == null ? '' : v);
    if (/^[=+\-@−]/.test(v)) v = "'" + v;
    return '"' + v.replace(/"/g, '""') + '"';
  }
  function exportJSON() {
    var L = S.items.slice().sort(order);
    var data = { tur: 'borsapusula-takip', surum: 1, tarih: bpTodayTrIso(),
      watchlist: L.map(function (r) { return r.t; }),
      portfolio: L.filter(isPos).map(function (r) { return { ticker: r.t, qty: r.q, cost: r.cost }; }) };
    download('takip-listesi-' + bpTodayTrIso() + '.json', JSON.stringify(data, null, 2), 'application/json');
    showToast({ msg: 'JSON yedeği indirildi' });
  }
  function exportCSV() {
    var L = S.items.slice().sort(order);
    var head = ['Hisse', 'Şirket', 'Trend', 'Fiyat', 'Son seans', 'Adet', 'Maliyet', 'Kâr/zarar', 'Kâr/zarar (%)'];
    var rows = L.map(function (r) {
      var pos = isPos(r), kz = pos && fin(r.p) ? r.q * (r.p - r.cost) : null, kzp = pos && fin(r.p) ? (r.p / r.cost - 1) * 100 : null;
      return [r.t, r.n, label(r), tl(r.p), pct(r.c), pos ? nf0.format(r.q) : '', pos ? tl(r.cost) : '', pos ? stl(kz) : '', pos ? pct(kzp) : ''].map(csvCell).join(';');
    });
    download('takip-listesi-' + bpTodayTrIso() + '.csv', '﻿' + [head.map(csvCell).join(';')].concat(rows).join('\r\n'), 'text/csv;charset=utf-8');
    showToast({ msg: 'CSV indirildi' });
  }
  function importFile(file) {
    if (!file) return;
    if (file.size > 200 * 1024) { showToast({ msg: 'Dosya çok büyük (en çok 200 KB).', err: true }); return; }
    var rd = new FileReader();
    rd.onload = function () {
      var data;
      try { data = JSON.parse(rd.result); } catch (e) { showToast({ msg: 'Dosya okunamadı: geçerli bir JSON yedeği seç.', err: true }); return; }
      var w = [], p = [];
      if (Array.isArray(data)) {
        data.forEach(function (x) { if (typeof x === 'string') w.push(x); else if (x && x.ticker) p.push(x); });
      } else if (data && typeof data === 'object') {
        if (Array.isArray(data.watchlist)) w = data.watchlist.filter(function (x) { return typeof x === 'string'; });
        if (Array.isArray(data.portfolio)) p = data.portfolio.filter(function (x) { return x && x.ticker; });
        else if (Array.isArray(data.positions)) p = data.positions.filter(function (x) { return x && x.ticker; });
      }
      if (!w.length && !p.length) { showToast({ msg: 'Dosyada hisse bulunamadı.', err: true }); return; }
      A.importData({ watchlist: w, portfolio: p }).then(function (res) {
        if (!res.ok) { fail(res, 'İçe aktarılamadı.'); return; }
        var imp = res.data.imported || {}, wa = +imp.watchlist_added || 0, pa = +imp.portfolio_added || 0;
        var msg = (wa || pa) ? (wa ? wa + ' hisse eklendi' : '') + (wa && pa ? ' · ' : '') + (pa ? pa + ' pozisyon eklendi' : '') : 'Yeni hisse yok; hepsi zaten listende';
        load(msg);
      });
    };
    rd.onerror = function () { showToast({ msg: 'Dosya okunamadı.', err: true }); };
    rd.readAsText(file);
  }

  function act(a) {
    var d = a.dataset, t = d.t;
    switch (d.act) {
      case 'mode':
        if (modeNow() === d.v) return;
        S.mode = d.v; S.edit = null; S.pick = null;
        try { localStorage.setItem(MODE_KEY, d.v); } catch (e) { console.warn('gorunum tercihi yazilamadi:', e); }
        render('[data-act="mode"][data-v="' + d.v + '"]'); return;
      case 'menu':
        S.menu = !S.menu; S.confirmClear = false; S.add = false;
        render(S.menu ? '.tk-menu [role="menuitem"]' : '[data-act="menu"]'); return;
      case 'add':
        S.menu = false;
        loadUniverse();
        if (phone()) { S.add = true; S.enter = true; S.q = ''; S.pick = null; render('.tk-sheet .tk-q'); trapSheet(); return; }
        S.add = !S.add;
        if (S.add) { S.q = ''; S.pick = null; }
        render(S.add ? '.tk-pop .tk-q' : '[data-act="add"]'); return;
      case 'close': closeAll(); return;
      case 'pick':
        if (modeNow() === 'pf') {
          S.pick = (S.pick === t) ? null : t;
          renderRes();
          focusSel(S.pick ? '.tk-ri.on [data-in="aq"]' : '[data-act="pick"][data-t="' + t + '"]');
          return;
        }
        addStock(t, null, null, ''); return;
      case 'addgo': {
        var ri = a.closest('.tk-ri'), u = uniRow(t), v = readPos(ri, '[data-in="aq"]', '[data-in="ac"]', u && u.p);
        if (v && v.err) { fieldErr(ri, v.err, v.sel); return; }
        addStock(t, v ? v.qty : null, v ? v.cost : null, v ? v.note : '', ri); return;
      }
      case 'ofollow': addStock(t, null, null, ''); return;
      case 'del': delStock(t); return;
      case 'undo': undo(); return;
      case 'edit':
        S.edit = (S.edit === t) ? null : t;
        render(S.edit ? '[data-in="eq"]' : '[data-act="edit"][data-t="' + t + '"]'); return;
      case 'cancel': { var et = S.edit; S.edit = null; render('[data-act="edit"][data-t="' + et + '"]'); return; }
      case 'save': saveEdit(t, a.closest('.tk-erow')); return;
      case 'exp-json': S.menu = false; render('[data-act="menu"]'); exportJSON(); return;
      case 'exp-csv': S.menu = false; render('[data-act="menu"]'); exportCSV(); return;
      case 'imp': S.menu = false; render('[data-act="menu"]'); if (fileEl) { fileEl.value = ''; fileEl.click(); } return;
      case 'clear': S.confirmClear = true; render('.tk-menu [data-act="clear-no"]'); return;
      case 'clear-no': S.confirmClear = false; render('.tk-menu [data-act="clear"]'); return;
      case 'clear-yes': clearList(); return;
      case 'sw': setPref(d.k); return;
      case 'logout': logout(); return;
      case 'del-acc': S.confirmDel = true; render('[data-act="del-no"]'); return;
      case 'del-no': S.confirmDel = false; render('[data-act="del-acc"]'); return;
      case 'del-yes': deleteAccount(); return;
      case 'emode': S.editMode = !S.editMode; S.edit = null; render('[data-act="emode"]'); return;
      case 'retry': load(); return;
      case 'uni-retry': S.uniState = 'idle'; loadUniverse(); renderRes(); return;
    }
  }
  function trapSheet() {
    var sh = layerEl && layerEl.querySelector('.tk-sheet');
    if (sh && window.bpTrapFocus && !sheetRelease) {
      var q = sh.querySelector('.tk-q');
      /* Esc'yi belge dinleyicisi kapatir (closeAll); tuzak yalniz Tab dongusu. */
      sheetRelease = window.bpTrapFocus(sh);
      if (q) q.focus();
    }
  }

  /* ── olaylar ── */
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('[data-act]');
    var inUi = a && (app.contains(a) || (ctlEl && ctlEl.contains(a)) || (layerEl && layerEl.contains(a)) || (toastEl && toastEl.contains(a)));
    if (S.menu && !(e.target.closest && (e.target.closest('.tk-menu') || e.target.closest('[data-act="menu"]')))) {
      S.menu = false; S.confirmClear = false;
      if (!inUi) { render(); return; }
    }
    if (S.add && !phone() && !(e.target.closest && (e.target.closest('.tk-pop') || e.target.closest('[data-act="add"]')))) {
      S.add = false; S.pick = null;
      if (!inUi) { render(); return; }
    }
    if (inUi) act(a);
  });
  document.addEventListener('keydown', function (e) {
    var tg = e.target;
    if (e.key === 'Escape') { if (S.phase === 'in' && closeAll()) e.preventDefault(); return; }
    var mn = tg.closest && tg.closest('.tk-menu');
    if (mn && ['ArrowDown', 'ArrowUp', 'Home', 'End'].indexOf(e.key) >= 0) {
      var it = [].slice.call(mn.querySelectorAll('[role="menuitem"]')), j = it.indexOf(tg);
      e.preventDefault();
      var k = e.key === 'Home' ? 0 : (e.key === 'End' ? it.length - 1 : (j + (e.key === 'ArrowDown' ? 1 : it.length - 1)) % it.length);
      it[k].focus();
      return;
    }
    if (mn && e.key === 'Tab') { S.menu = false; S.confirmClear = false; e.preventDefault(); render('[data-act="menu"]'); return; }
    if (tg.matches && tg.matches('[data-act="menu"]') && e.key === 'ArrowDown' && !S.menu) { e.preventDefault(); act(tg); return; }
    if ((e.key === 'ArrowRight' || e.key === 'ArrowLeft') && tg.closest && tg.closest('.tk-seg')) {
      e.preventDefault();
      var nv = modeNow() === 'pf' ? 'list' : 'pf';
      act({ dataset: { act: 'mode', v: nv } });
      return;
    }
    if (e.key === 'Enter' && tg.matches) {
      if (tg.matches('[data-in="q"]')) { e.preventDefault(); var f = document.querySelector('.tk-res [data-act="pick"]'); if (f) f.click(); return; }
      if (tg.matches('[data-in="oq"]')) { e.preventDefault(); var g = app.querySelector('.tk-ores [data-act="ofollow"]'); if (g) g.click(); return; }
      if (tg.matches('[data-in="aq"],[data-in="ac"]')) { e.preventDefault(); var b = tg.closest('.tk-ri').querySelector('[data-act="addgo"]'); if (b) b.click(); return; }
      if (tg.matches('[data-in="eq"],[data-in="ec"]')) { e.preventDefault(); var s = tg.closest('.tk-erow').querySelector('[data-act="save"]'); if (s) s.click(); }
    }
  });
  document.addEventListener('input', function (e) {
    var t = e.target, k = t.dataset && t.dataset['in'];
    if (!k) return;
    if (k === 'q') { S.q = t.value; S.pick = null; var w = document.querySelector('.tk-resw'); if (w) w.innerHTML = resHTML(); }
    else if (k === 'oq') { S.q = t.value; var o = app.querySelector('.tk-ores'); if (o) o.innerHTML = oresHTML(); }
    else if (t.getAttribute('aria-invalid')) { t.removeAttribute('aria-invalid'); }
  });
  if (toastEl) {
    toastEl.addEventListener('mouseover', function () { pauseToast(true); });
    toastEl.addEventListener('mouseleave', function () { pauseToast(false); });
    toastEl.addEventListener('focusin', function () { pauseToast(true); });
    toastEl.addEventListener('focusout', function (e) { if (!(e.relatedTarget && toastEl.contains(e.relatedTarget))) pauseToast(false); });
  }
  if (fileEl) fileEl.addEventListener('change', function () { importFile(fileEl.files && fileEl.files[0]); });
  var onMQ = function () { if (S.phase === 'in') { if (S.add) { S.add = false; S.pick = null; } render(); } };
  if (MQ.addEventListener) MQ.addEventListener('change', onMQ); else if (MQ.addListener) MQ.addListener(onMQ);

  /* ── acilis ── */
  try { var sm = localStorage.getItem(MODE_KEY); if (sm === 'pf' || sm === 'list') S.mode = sm; } catch (e) { console.warn('gorunum tercihi okunamadi:', e); }
  if (A.hasHint()) load();
  else { S.phase = 'out'; render(); }
})();
