/* BorsaPusula /tarama v2 (C-34, onaylı taslak O16c=A; C-33 performans ilkeleri).
   Tek tablo, [Genel | Teknik | Temel] sütun seti, BP ilk sütun ve varsayılan sıralama,
   Yatay / Trend Bozuldu katlanmış grup, 5 hazır liste (paylaşılabilir adres), tek Temizle.
   - Veri tek kez çekilir: /api/tarama (+ BP/Temel alanları /api/tarama/temel'den, /api/tarama
     bu alanları taşıyana kadar; D-21 ile BP yönlü olur, arayüz değişmez). Sıralama ve filtre
     istemcide (216 satır, 4x CPU'da <100 ms).
   - Tek temsil: tek <table>; dar ekran düzeni CSS'le aynı işaretlemeden çıkar (ikiz yok).
   - Her grupta ilk 50 satır + "Daha fazla göster".
   Bağımlılık: bp-vocab.js (escapeHtml, bpTrFold), bp-format.js (bpFormatPct, bpDirClass,
   bpFormatTrDateLong), js/focus-trap.js (bpTrapFocus). */
(function () {
  'use strict';
  var OUT = document.getElementById('tvOut');
  if (!OUT) return;
  var $ = function (id) { return document.getElementById(id); };
  var WIDE = window.matchMedia('(min-width: 820px)');
  var nf2 = new Intl.NumberFormat('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  var nf1 = new Intl.NumberFormat('tr-TR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  var PAGE = 50;
  var COLL = new Intl.Collator('tr');  /* localeCompare(…, 'tr') her çağrıda sıralayıcı kuruyordu (4x CPU'da sıralamanın yarısı) */
  var cmp = COLL.compare;
  var esc = function (s) { return escapeHtml(s == null ? '' : String(s)); };
  var SIG = { AL: 'g', BEKLE: 'y', SAT: 'b' };
  var TR = { g: 'Güçlü Trend', y: 'Yatay', b: 'Trend Bozuldu' };
  var GROUPS = [
    { k: 'g', d: 'Trend koşullarının hepsi sağlanıyor' },
    { k: 'y', d: 'Koşulların bir kısmı sağlanıyor; yön henüz belli değil' },
    { k: 'b', d: 'Yükseliş trendi bozuldu; trend desteklemiyor' }];
  var SLUG = { g: 'guclu-trend', y: 'yatay', b: 'trend-bozuldu' };
  var CHEV = '<svg class="chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg>';
  var XIC = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>';

  var ROWS = [], COUNT = { g: 0, y: 0, b: 0 }, SEK = [], ASOF = '', LOADED = false, FAILED = false;

  /* ── "Finansalları nasıl?" betimi: kategori skorlarından, şirkete yargı yok (kanon §2.4) ── */
  var CATN = { karlilik: 'kârlılık', nakit_akisi: 'nakit akışı', kaldirac: 'borç durumu', degerleme_buyume: 'değerleme/büyüme' };
  function cap(t) { return t.charAt(0).toLocaleUpperCase('tr-TR') + t.slice(1); }
  function finAns(c) {
    if (!c) return null;
    var a = Object.keys(CATN).filter(function (k) { return c[k] != null; })
      .map(function (k) { return [CATN[k], c[k]]; }).sort(function (x, y) { return y[1] - x[1]; });
    if (!a.length) return null;
    var st = a.filter(function (x) { return x[1] >= 70; }), wk = a.filter(function (x) { return x[1] < 50; });
    if (st.length && wk.length) return cap(st[0][0]) + ' güçlü, ' + wk[wk.length - 1][0] + ' zayıf';
    if (st.length >= 2) return cap(st[0][0]) + ' ve ' + st[1][0] + ' güçlü';
    if (st.length) return cap(st[0][0]) + ' öne çıkıyor';
    if (wk.length) return cap(wk[wk.length - 1][0]) + ' zayıf, diğerleri dengeli';
    return 'Dengeli; belirgin zayıf alan yok';
  }
  function pick(a, b, k) { return a[k] != null ? a[k] : (b[k] != null ? b[k] : null); }
  function mapRows(tr, tm) {
    var M = {};
    (tm || []).forEach(function (m) { M[m.ticker] = m; });
    return tr.map(function (s) {
      var m = M[s.ticker] || {};
      var te = pick(s, m, 'temel_analiz_skoru'), dc = pick(s, m, 'data_completeness');
      var cat = s.categories || m.categories || null;
      return {
        t: s.ticker, n: (s.name || '').replace(' A.Ş.', ''), g: s.sector || 'Diğer', s: SIG[s.signal] || 'y',
        d: s.signal_bars, p: s.price, c: s.change_pct, bp: pick(s, m, 'borsapusula_skoru'), te: te,
        sv: te != null && dc != null && dc < 0.8, cat: cat, na: s.categories_na || m.categories_na || [],
        fa: te != null ? finAns(cat) : null, adx: s.adx, sl: s.sl_level, rv: s.rvol, ho: !!s.is_premium,
        stale: !!(s.stale_reason || s.data_quality === 'stale')
      };
    });
  }

  /* ── Hazır listeler: her biri paylaşılabilir adres (?liste=…) ── */
  var PRESETS = [
    { id: 'hacim-onayli', l: 'Güçlü Trend + Hacim Onaylı', rule: 'Trend koşullarının hepsi sağlanıyor; 5 günlük ortalama hacim, 20 günlük ortalamanın en az 1,2 katı (RVOL ≥ 1,20).', set: { durum: ['g'] }, x: function (r) { return r.ho; } },
    { id: 'bp-70', l: 'BP ≥ 70', rule: 'BorsaPusula Skoru 70 ve üstü; skor finansallardan %60, trendden %40 pay alıyor.', set: { bp: 70 } },
    { id: 'yeni-sinyal', l: 'Yeni sinyal (≤3 seans)', rule: 'Trend durumu son 3 seans içinde değişen hisseler.', x: function (r) { return r.d != null && r.d <= 3; } },
    { id: 'trend-bozuldu-son-seans', l: 'Son seansta Trend Bozuldu', rule: function () { return 'Yükseliş trendi ' + (ASOF || 'son') + ' seansında bozulan hisseler.'; }, set: { durum: ['b'] }, x: function (r) { return r.d != null && r.d <= 1; } },
    { id: 'kaliteli-trend-bekliyor', l: 'Kaliteli, trend bekliyor', rule: 'Temel skor 70 ve üstü, finansal verisi tam; trend henüz Yatay.', set: { durum: ['y'], temel: 70 }, x: function (r) { return !r.sv; } }];
  var PRE = {};
  PRESETS.forEach(function (p) { PRE[p.id] = p; });

  /* ── Sütunlar ── */
  function mut(t) { return '<span class="mut">' + t + '</span>'; }
  function bar(v, cls, soft, sup) {
    return '<span class="tv-bp' + (cls ? ' ' + cls : '') + (soft ? ' soft' : '') + '" style="--v:' + Math.max(0, Math.min(100, v)) + '"><b>' + v + (sup ? '<sup>*</sup>' : '') + '</b><i></i></span>';
  }
  function catCol(key, h) {
    return { h: h, num: 1, tip: CATN[key].charAt(0).toLocaleUpperCase('tr-TR') + CATN[key].slice(1) + ' kategorisinin skoru (0–100).',
      v: function (r) { return r.cat ? r.cat[key] : null; },
      cell: function (r) { var v = r.cat ? r.cat[key] : null; if (v != null) return String(Math.round(v)); return mut(r.te == null ? 'Sınırlı veri' : (r.na.indexOf(key) >= 0 ? 'Uygulanmaz' : 'Veri yok')); } };
  }
  function cush(r) { return (r.p && r.sl != null) ? (r.p - r.sl) / r.p * 100 : null; }
  var C = {
    bp: { h: 'BP Skoru', num: 1, tip: 'BorsaPusula Skoru (0–100): finansallar %60, trend %40; trend skoru olmayan hissede yalnız finansallar.', v: function (r) { return r.bp; },
      cell: function (r) { return r.bp == null ? mut('Sınırlı veri') : '<span class="sr-only">BorsaPusula Skoru </span>' + bar(r.bp, '', r.s === 'b'); } },
    tr: { h: 'Trend', tip: 'Trend durumu ve kaç işlem günüdür sürdüğü.', v: function (r) { return r.d; },
      cell: function (r) { return '<span class="pill ' + r.s + '">' + TR[r.s] + '</span>' + (r.d ? '<span class="sub">' + (r.d <= 1 ? 'son seansta' : r.d + ' gündür') + '</span>' : ''); } },
    p: { h: 'Fiyat', num: 1, v: function (r) { return r.p; }, cell: function (r) { return r.p == null ? mut('Fiyat yok') : nf2.format(r.p) + ' ' + mut('₺'); } },
    c: { h: 'Değişim', num: 1, tip: 'Son seansın bir önceki kapanışa göre değişimi.', v: function (r) { return r.c; },
      cell: function (r) { return '<span class="' + bpDirClass(r.c, 2, ['u', 'd', '']) + '">' + bpFormatPct(r.c, 2) + '</span>'; } },
    g: { h: 'Sektör', cls: 'hide-t', v: function (r) { return r.g; }, cell: function (r) { return esc(r.g); } },
    adx: { h: 'ADX', num: 1, tip: 'Trend gücü. 25 ve üstü, Güçlü Trend koşullarından biri.', v: function (r) { return r.adx; }, cell: function (r) { return r.adx == null ? mut('Veri yok') : nf1.format(r.adx); } },
    dist: { h: 'Trend dönüş seviyesi', tip: 'Supertrend çizgisi: trend durumunun değiştiği fiyat.', v: cush,
      cell: function (r) { var q = cush(r); if (q == null) return mut('Veri yok'); return nf2.format(r.sl) + ' ' + mut('₺') + '<span class="sub">fiyatın %' + nf1.format(Math.abs(q)) + ' ' + (r.sl < r.p ? 'altında' : 'üstünde') + '</span>'; } },
    rv: { h: 'RVOL', num: 1, tip: '5 günlük ortalama hacim / 20 günlük ortalama hacim.', v: function (r) { return r.rv; }, cell: function (r) { return r.rv == null ? mut('Veri yok') : nf2.format(r.rv) + '×'; } },
    d: { h: 'Durum yaşı', num: 1, tip: 'Hisse kaç işlem günüdür bu trend durumunda.', v: function (r) { return r.d; }, cell: function (r) { return r.d == null ? mut('Veri yok') : (r.d <= 1 ? 'son seans' : r.d + ' gün'); } },
    te: { h: 'Temel skor', tip: 'Kârlılık, nakit akışı, borç durumu, değerleme ve büyüme (0–100). * Sınırlı veri.', v: function (r) { return r.te; },
      cell: function (r) { return r.te == null ? mut('Sınırlı veri') : bar(r.te, 'cy', false, r.sv) + (r.fa ? '<span class="sub">' + esc(r.fa) + '</span>' : ''); } },
    kar: catCol('karlilik', 'Kârlılık'),
    nak: catCol('nakit_akisi', 'Nakit akışı'),
    kal: catCol('kaldirac', 'Borç durumu'),
    deg: catCol('degerleme_buyume', 'Değerleme / büyüme')
  };
  var COLS = { genel: ['bp', 'tr', 'p', 'c', 'g'], teknik: ['bp', 'adx', 'dist', 'rv', 'd'], temel: ['bp', 'te', 'kar', 'nak', 'kal', 'deg'] };
  var ASC = { t: 1, g: 1 };
  var SORTL = { t: 'Hisse kodu', bp: 'BorsaPusula Skoru', tr: 'Durum yaşı', d: 'Durum yaşı', p: 'Fiyat', c: 'Değişim', g: 'Sektör', adx: 'ADX', dist: 'Dönüş seviyesine uzaklık', rv: 'RVOL', te: 'Temel skor', kar: 'Kârlılık', nak: 'Nakit akışı', kal: 'Borç durumu', deg: 'Değerleme / büyüme' };
  var SSLUG = { t: 'kod', bp: 'bp', tr: 'durum-yasi', d: 'durum-yasi', p: 'fiyat', c: 'degisim', g: 'sektor', adx: 'adx', dist: 'donus-seviyesi', rv: 'rvol', te: 'temel', kar: 'karlilik', nak: 'nakit-akisi', kal: 'borc-durumu', deg: 'degerleme-buyume' };
  function slug(s) { return bpTrFold(String(s)).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, ''); }

  /* ── Durum ── */
  function blank() { return { preset: null, durum: [], bp: 0, temel: 0, sektor: [] }; }
  function withPreset(id) {
    var f = blank(), p = PRE[id]; f.preset = id;
    if (p.set) { if (p.set.durum) f.durum = p.set.durum.slice(); if (p.set.bp) f.bp = p.set.bp; if (p.set.temel) f.temel = p.set.temel; }
    return f;
  }
  var st = { f: blank(), sort: { k: 'bp', dir: -1 }, cols: 'genel', open: {}, more: { g: PAGE, y: PAGE, b: PAGE }, panel: false };
  function pass(f, r) {
    if (f.durum.length && f.durum.indexOf(r.s) < 0) return false;
    if (f.bp && !(r.bp >= f.bp)) return false;
    if (f.temel && !(r.te >= f.temel)) return false;
    if (f.sektor.length && f.sektor.indexOf(r.g) < 0) return false;
    if (f.preset && PRE[f.preset].x && !PRE[f.preset].x(r)) return false;
    return true;
  }
  function nAct(f) { return (f.durum.length ? 1 : 0) + (f.bp ? 1 : 0) + (f.temel ? 1 : 0) + (f.sektor.length ? 1 : 0) + (f.preset && PRE[f.preset].x ? 1 : 0); }
  function isOpen(k) {
    if (Object.prototype.hasOwnProperty.call(st.open, k)) return st.open[k];
    if (k === 'g') return true;
    if (k === 'y') return nAct(st.f) > 0;
    return st.f.durum.indexOf('b') >= 0;
  }
  /* sütun seti tercihi (izleyici başına kolaylık; eski sekme değerleri 'teknik'/'temel' önekiz, yok sayılır) */
  var LSK = 'bp_tarama_tab';
  function saveCols() { try { localStorage.setItem(LSK, 'v2:' + st.cols); } catch (e) { /* özel pencere: tercih tutulmaz */ } }
  function resetView() { st.open = {}; st.more = { g: PAGE, y: PAGE, b: PAGE }; }
  /* C-35: dar ekranda satır [kod | BP | fiyat/değişim] tek biçim; sütun seti yalnız ≥820px'te */
  function cols() { return WIDE.matches ? st.cols : 'genel'; }
  function sorter() {
    var k = st.sort.k, dir = st.sort.dir, f = k === 't' ? function (r) { return r.t; } : C[k].v;
    return function (a, b) {
      var x = f(a), y = f(b), xn = x == null, yn = y == null;
      if (xn || yn) return xn && yn ? cmp(a.t, b.t) : (xn ? 1 : -1);
      var c = typeof x === 'string' ? cmp(x, y) : x - y;
      return dir * c || (b.bp || 0) - (a.bp || 0) || cmp(a.t, b.t);
    };
  }

  /* ── Adres: paylaşılabilir durum (+ eski bağlantılar: ?signal=AL, ?sector=…, ?tab=temel, ?sort=…) ── */
  function qs() {
    var f = st.f, p = [];
    if (f.preset) p.push('liste=' + f.preset);
    else {
      if (f.durum.length) p.push('durum=' + f.durum.map(function (v) { return SLUG[v]; }).join(','));
      if (f.bp) p.push('bp=' + f.bp);
      if (f.temel) p.push('temel=' + f.temel);
      if (f.sektor.length) p.push('sektor=' + f.sektor.map(slug).join(','));
    }
    if (st.cols !== 'genel') p.push('gorunum=' + st.cols);
    if (st.sort.k !== 'bp' || st.sort.dir !== -1) p.push('sirala=' + SSLUG[st.sort.k] + (st.sort.dir > 0 ? '-artan' : ''));
    return p.length ? '?' + p.join('&') : '';
  }
  function writeUrl() {
    try {
      var u = location.pathname + qs();
      if (u !== location.pathname + location.search) history.replaceState(null, '', u);
    } catch (e) { /* adres senkronu en iyi çaba */ }
  }
  var RAWQ = null;
  function readUrl() {
    var q = new URLSearchParams(location.search), f = blank();
    var li = q.get('liste');
    if (li && PRE[li]) f = withPreset(li);
    else {
      var inv = {}; Object.keys(SLUG).forEach(function (k) { inv[SLUG[k]] = k; });
      (q.get('durum') || '').split(',').forEach(function (v) { if (inv[v] && f.durum.indexOf(inv[v]) < 0) f.durum.push(inv[v]); });
      var sg = { AL: 'g', BEKLE: 'y', SAT: 'b' }[(q.get('signal') || '').toUpperCase()];
      if (sg && f.durum.indexOf(sg) < 0) f.durum.push(sg);
      if (q.get('only_premium') === '1' || (q.get('signal') || '').toUpperCase() === 'PREMIUM') f = withPreset('hacim-onayli');
      var bp = +q.get('bp'), te = +q.get('temel');
      if ([50, 60, 70].indexOf(bp) >= 0) f.bp = bp;
      if ([50, 70].indexOf(te) >= 0) f.temel = te;
    }
    var sek = (q.get('sektor') || q.get('sector') || '').split(',').filter(Boolean);
    var g = q.get('gorunum') || (q.get('tab') === 'temel' ? 'temel' : null);
    if (!g) { try { var ls = localStorage.getItem(LSK) || ''; if (ls.indexOf('v2:') === 0) g = ls.slice(3); } catch (e) { /* tercih okunamadı: varsayılan */ } }
    if (g && COLS[g]) st.cols = g;
    var so = q.get('sirala'), old = { signal_strength: 'bp', borsapusula_score: 'bp', temel_score: 'te', adx: 'adx', price: 'p', change_pct: 'c', signal_bars: 'd', karlilik: 'kar', nakit_akisi: 'nak', kaldirac: 'kal', degerleme_buyume: 'deg' }[q.get('sort') || ''];
    if (so) { var asc = /-artan$/.test(so), key = so.replace(/-artan$/, ''); Object.keys(SSLUG).forEach(function (k) { if (SSLUG[k] === key && k !== 'tr') st.sort = { k: k, dir: asc ? 1 : -1 }; }); }
    else if (old) st.sort = { k: old, dir: old === 'd' ? 1 : -1 };
    st.f = f;
    RAWQ = sek;  // sektör adları veri gelince çözülür (slug ya da ad)
  }
  function resolveSectors() {
    if (!RAWQ || !RAWQ.length) return;
    var want = RAWQ.map(function (v) { return slug(v); });
    st.f.sektor = SEK.map(function (s) { return s[0]; }).filter(function (n) { return want.indexOf(slug(n)) >= 0; });
    if (st.f.sektor.length && st.f.preset) st.f.preset = null;
    RAWQ = null;
  }

  /* ── Parçalar ── */
  function thHTML(k, label, cl, tip) {
    var s = st.sort, on = s.k === k;
    return '<th scope="col" class="' + cl + ' th-sortable" aria-sort="' + (on ? (s.dir < 0 ? 'descending' : 'ascending') : 'none') + '"><button type="button" class="thb th-sort-btn" data-act="sort" data-k="' + k + '"' + (tip ? ' data-tip="' + esc(tip) + '"' : '') + '>' + label + '<span class="ar" aria-hidden="true">' + (on ? (s.dir < 0 ? '↓' : '↑') : '↕') + '</span></button></th>';
  }
  function emptyHTML() { return '<div class="tv-empty"><b>Bu seçimle eşleşen hisse yok</b>Filtrelerden birini gevşet ya da Temizle ile baştan başla.</div>'; }
  function tableHTML(rows) {
    var cs = COLS[cols()], ncol = cs.length + 1, body = '', srt = sorter();
    GROUPS.forEach(function (G) {
      var list = rows.filter(function (r) { return r.s === G.k; });
      if (!list.length) return;
      list.sort(srt);
      var open = isOpen(G.k);
      body += '<tbody class="grp ' + G.k + (open ? ' open' : '') + '"><tr class="gh"><th scope="rowgroup" colspan="' + ncol + '"><button type="button" class="ghb" data-act="grp" data-k="' + G.k + '" aria-expanded="' + open + '">' + CHEV + '<span class="pill ' + G.k + '">' + TR[G.k] + '</span><span class="gn">' + list.length + ' hisse</span><span class="gd">' + G.d + '</span>' + (open ? '' : '<span class="go">Göster</span>') + '</button></th></tr>';
      if (open) {
        var lm = st.more[G.k];
        list.slice(0, lm).forEach(function (r) {
          body += '<tr class="r ' + r.s + '"><td class="c-hs"><a class="rl" href="/hisse/' + esc(r.t) + '"><b>' + esc(r.t) + '</b></a><span class="nm">' + esc(r.n) + '</span>' +
            (r.stale ? '<span class="tv-stale" tabindex="0" data-tip="Bu hissenin verisi güncellenmiyor; fiyat ve puan son alınan veriye aittir.">Güncellenmiyor</span>' : '') + '</td>' +
            cs.map(function (k) { var c = C[k]; return '<td class="c-' + k + (c.num ? ' num' : '') + (c.cls ? ' ' + c.cls : '') + '">' + c.cell(r) + '</td>'; }).join('') + '</tr>';
        });
        if (list.length > lm) body += '<tr class="more"><td colspan="' + ncol + '"><button type="button" class="tv-moreb" data-act="more" data-k="' + G.k + '">Daha fazla göster · ' + (list.length - lm) + ' hisse daha</button></td></tr>';
      }
      body += '</tbody>';
    });
    if (!body) body = '<tbody><tr class="none"><td colspan="' + ncol + '">' + emptyHTML() + '</td></tr></tbody>';
    return '<div class="tv-tbw"><table class="tv-tb"><caption class="sr-only">Tarama sonuçları, trend durumuna göre gruplu</caption><thead><tr>' + thHTML('t', 'Hisse', 'c-hs') +
      cs.map(function (k) { var c = C[k]; return thHTML(k, c.h, 'c-' + k + (c.num ? ' num' : '') + (c.cls ? ' ' + c.cls : ''), c.tip); }).join('') + '</tr></thead>' + body + '</table></div>';
  }
  function fg(title, sub, body, cls) { return '<fieldset class="tv-fg' + (cls ? ' ' + cls : '') + '"><legend>' + title + (sub ? '<span>' + sub + '</span>' : '') + '</legend>' + body + '</fieldset>'; }
  function one(fk, opts, cur) {
    return '<div class="tv-opts">' + opts.map(function (o) { return '<button type="button" class="tv-opt" data-act="set" data-f="' + fk + '" data-v="' + o[0] + '" aria-pressed="' + (String(cur) === String(o[0])) + '">' + o[1] + '</button>'; }).join('') + '</div>';
  }
  function many(fk, opts, arr) {
    return '<div class="tv-opts">' + opts.map(function (o) {
      return '<button type="button" class="tv-opt" data-act="tog" data-f="' + fk + '" data-v="' + esc(o[0]) + '" aria-pressed="' + (arr.indexOf(o[0]) >= 0) + '">' + esc(o[1]) + '<span class="oc">' + o[2] + '</span></button>';
    }).join('') + '</div>';
  }
  function panelBody() {
    var f = st.f, h = '';
    if (f.preset) h += '<div class="tv-pp"><span>Hazır liste</span><b>' + esc(PRE[f.preset].l) + '</b><button type="button" class="tv-ppx" data-act="preset" data-id="' + f.preset + '" aria-label="Hazır listeyi kaldır">' + XIC + '</button></div>';
    h += '<div class="tv-pcols"><div>';
    h += fg('BorsaPusula Skoru', 'finansallar %60 · trend %40', one('bp', [[0, 'Tümü'], [50, '50+'], [60, '60+'], [70, '70+']], f.bp));
    h += fg('Finansalları nasıl?', 'Temel skor', one('temel', [[0, 'Tümü'], [50, '50+'], [70, '70+']], f.temel));
    h += fg('Trend destekliyor mu?', '', many('durum', [['g', 'Güçlü Trend', COUNT.g], ['y', 'Yatay', COUNT.y], ['b', 'Trend Bozuldu', COUNT.b]], f.durum));
    h += fg('Sırala', '', one('sort', [['bp', 'BP Skoru'], ['c', 'Değişim'], ['te', 'Temel skor'], ['t', 'Ada göre']], st.sort.k), 'tv-fg-sort');
    h += '</div><div>' + fg('Sektör', '', many('sektor', SEK, f.sektor)) + '</div></div>';
    return h;
  }
  function panelFoot(n) {
    return '<span class="tv-pn"><b>' + n + '</b> hisse eşleşiyor</span><button type="button" class="tv-clr2" data-act="clear"' + (nAct(st.f) ? '' : ' disabled') + '>Temizle</button><button type="button" class="tv-pri" data-act="close">' + n + ' hisseyi göster</button>';
  }

  /* ── Çizim ── */
  function head() {
    $('tvStamp').innerHTML = (ASOF ? '<b>' + esc(ASOF) + ' kapanışı</b>' : '') + '<span class="n"> · ' + ROWS.length + ' hisse</span>';
    $('tvLeg').innerHTML = '<span><i class="k g"></i><b>' + COUNT.g + '</b> Güçlü Trend</span><span><i class="k y"></i><b>' + COUNT.y + '</b> Yatay</span><span><i class="k b"></i><b>' + COUNT.b + '</b> Trend Bozuldu</span><span class="hl" id="tvLegHl"></span>';
    var strip = ROWS.slice().sort(function (a, b) { return 'gyb'.indexOf(a.s) - 'gyb'.indexOf(b.s) || (b.bp || 0) - (a.bp || 0) || cmp(a.t, b.t); });
    $('tvStrip').innerHTML = strip.map(function (r) { return '<i class="' + r.s + '" data-t="' + esc(r.t) + '"></i>'; }).join('');
    PRESETS.forEach(function (p) {
      var f = withPreset(p.id), n = ROWS.filter(function (r) { return pass(f, r); }).length;
      var a = document.querySelector('.tv-chip[data-id="' + p.id + '"] .cn');
      if (a) a.textContent = n;
    });
  }
  function strip(rows) {
    var any = nAct(st.f) > 0, on = {};
    rows.forEach(function (r) { on[r.t] = 1; });
    [].forEach.call($('tvStrip').children, function (i) { i.classList.toggle('off', any && !on[i.getAttribute('data-t')]); });
    $('tvStrip').setAttribute('aria-label', ROWS.length + ' hissenin trend durumu: ' + COUNT.g + ' Güçlü Trend, ' + COUNT.y + ' Yatay, ' + COUNT.b + ' Trend Bozuldu' + (any ? '; ' + rows.length + ' hisse filtreyle eşleşiyor' : ''));
    var hl = $('tvLegHl');
    if (hl) hl.innerHTML = any ? '<i class="k on"></i><b>' + rows.length + '</b> hisse filtreyle eşleşiyor' : 'Her çizgi bir hisse; sıralama tablodaki gibi';
  }
  function bar2(rows) {
    var f = st.f, n = nAct(f);
    [].forEach.call(document.querySelectorAll('.tv-chip'), function (a) {
      var on = f.preset === a.getAttribute('data-id');
      a.classList.toggle('on', on);
      if (on) a.setAttribute('aria-current', 'true'); else a.removeAttribute('aria-current');
    });
    var fn = $('tvFn');
    fn.hidden = !n; fn.textContent = n || '';
    $('tvFbtn').setAttribute('aria-label', n ? 'Filtre, ' + n + ' açık filtre' : 'Filtre');
    $('tvClr').hidden = !n;
    var rule = f.preset ? PRE[f.preset].rule : null;
    if (typeof rule === 'function') rule = rule();
    $('tvInfo').innerHTML = '<b>' + rows.length + ' hisse</b> · ' + (rule ? esc(rule) : 'Sıralama: ' + SORTL[st.sort.k] + ' ' + (st.sort.dir < 0 ? '↓' : '↑'));
    [].forEach.call(document.querySelectorAll('.tv-seg button'), function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-v') === st.cols)); });
    $('tvFnote').hidden = !(WIDE.matches && st.cols === 'temel');
  }
  function fkey(el) { var a = el && el.closest && el.closest('[data-act]'); return a ? [a.getAttribute('data-act'), a.getAttribute('data-k') || '', a.getAttribute('data-f') || '', a.getAttribute('data-v') || '', a.getAttribute('data-id') || ''].join('|') : null; }
  function byKey(scope, key) { var els = scope.querySelectorAll('[data-act]'); for (var i = 0; i < els.length; i++) if (fkey(els[i]) === key) return els[i]; return null; }
  function render() {
    if (!LOADED) return;
    var ae = document.activeElement, inOut = ae && OUT.contains(ae), inPanel = ae && $('tvPanel').contains(ae), key = (inOut || inPanel) ? fkey(ae) : null;
    var rows = ROWS.filter(function (r) { return pass(st.f, r); });
    OUT.innerHTML = rows.length ? tableHTML(rows) : '<div class="tv-tbw">' + emptyHTML() + '</div>';
    bar2(rows);
    strip(rows);
    if (st.panel) {
      var b = $('tvPanelB'), top = b.scrollTop;
      b.innerHTML = panelBody();
      b.scrollTop = top;
      $('tvPanelF').innerHTML = panelFoot(rows.length);
    }
    if (key) { var t = byKey(inPanel ? $('tvPanel') : OUT, key); if (t) t.focus({ preventScroll: true }); }
    writeUrl();
  }

  /* ── Filtre paneli: masaüstünde açılır kutu, dar ekranda alt panel; odak tuzağı + Esc ── */
  var release = null;
  function openPanel() {
    if (st.panel) return;
    st.panel = true;
    var bar = $('tvBar');
    $('tvPanel').style.setProperty('--tv-pop-top', (bar.offsetTop + bar.offsetHeight - 2) + 'px');  // masaüstü: çubuğun hemen altı
    $('tvPanel').hidden = false;
    $('tvFbtn').setAttribute('aria-expanded', 'true');
    render();
    if (!LOADED) { $('tvPanelB').innerHTML = '<div class="tv-empty">Veriler yükleniyor…</div>'; $('tvPanelF').innerHTML = ''; }
    var sh = $('tvPanel').querySelector('.tv-sheet');
    release = window.bpTrapFocus ? window.bpTrapFocus(sh, closePanel) : null;
    var x = sh.querySelector('.tv-xbtn'); if (x) x.focus();
  }
  function closePanel() {
    if (!st.panel) return;
    st.panel = false;
    $('tvPanel').hidden = true;
    $('tvFbtn').setAttribute('aria-expanded', 'false');
    if (release) { var r = release; release = null; r(); } else $('tvFbtn').focus();
  }

  /* ── Olaylar ── */
  function act(a, e) {
    var d = a.dataset, f = st.f;
    switch (d.act) {
      case 'preset': if (e) e.preventDefault(); st.f = (f.preset === d.id) ? blank() : withPreset(d.id); resetView(); break;
      case 'panel': if (st.panel) closePanel(); else openPanel(); return;
      case 'close': closePanel(); return;
      case 'set':
        if (d.f === 'sort') st.sort = { k: d.v, dir: ASC[d.v] ? 1 : -1 };
        else { f[d.f] = +d.v; resetView(); }
        break;
      case 'tog': var arr = f[d.f], i = arr.indexOf(d.v); if (i < 0) arr.push(d.v); else arr.splice(i, 1); resetView(); break;
      case 'clear': st.f = blank(); resetView(); break;
      case 'grp': st.open[d.k] = !isOpen(d.k); break;
      case 'more': st.more[d.k] += PAGE; break;
      case 'cols': st.cols = d.v; saveCols(); break;
      case 'sort': st.sort = (st.sort.k === d.k) ? { k: d.k, dir: -st.sort.dir } : { k: d.k, dir: ASC[d.k] ? 1 : -1 }; break;
      default: return;
    }
    render();
  }
  document.querySelector('main.tv').addEventListener('click', function (e) {
    var a = e.target.closest('[data-act]');
    if (!a || !this.contains(a)) return;
    if (a.tagName === 'A' && (e.metaKey || e.ctrlKey || e.shiftKey || e.button > 0)) return;  // yeni sekmede aç: tarayıcıya bırak
    act(a, e);
  });
  document.querySelector('.tv-seg').addEventListener('keydown', function (e) {
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
    var bs = [].slice.call(this.querySelectorAll('button')), j = bs.indexOf(document.activeElement);
    if (j < 0) return;
    e.preventDefault();
    var nx = bs[(j + (e.key === 'ArrowRight' ? 1 : bs.length - 1)) % bs.length];
    st.cols = nx.getAttribute('data-v'); saveCols(); render(); nx.focus();
  });
  WIDE.addEventListener('change', function () { render(); });

  /* ── Yükleme: tek /api/tarama (+ /api/tarama/temel, BP ve Temel alanları için) ── */
  function getJson(u) {
    return fetch(u, { signal: AbortSignal.timeout ? AbortSignal.timeout(15000) : undefined }).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    });
  }
  function load() {
    FAILED = false;
    var tp = getJson('/api/tarama');
    var mp = tp.then(function (d) {
      var r0 = (d.results || [])[0];
      if (r0 && r0.borsapusula_skoru !== undefined && r0.temel_analiz_skoru !== undefined) return null;  // D-21 sonrası: tek istek yeter
      return getJson('/api/tarama/temel').then(function (m) { return m.results || []; }, function () { return []; });
    });
    Promise.all([tp, mp]).then(function (res) {
      var d = res[0];
      ROWS = mapRows(d.results || [], res[1]);
      COUNT = { g: 0, y: 0, b: 0 };
      var sc = {};
      ROWS.forEach(function (r) { COUNT[r.s]++; sc[r.g] = (sc[r.g] || 0) + 1; });
      SEK = Object.keys(sc).sort(function (a, b) { if (a === 'Diğer') return 1; if (b === 'Diğer') return -1; return sc[b] - sc[a] || cmp(a, b); }).map(function (k) { return [k, k, sc[k]]; });
      ASOF = (typeof bpFormatTrDateLong === 'function' && d.updated_at) ? (bpFormatTrDateLong(String(d.updated_at).split(' ')[0]) || '') : '';
      LOADED = true;
      resolveSectors();
      head();
      render();
    }).catch(function () {
      FAILED = true;
      OUT.insertAdjacentHTML('afterbegin', '<div class="da-empty da-empty--error" role="alert"><span>Veri yüklenemedi.</span><button type="button" class="da-retry" id="tvRetry">Tekrar dene</button></div>');
      var b = $('tvRetry'); if (b) b.addEventListener('click', function () { b.parentNode.remove(); load(); });
    });
  }
  readUrl();
  load();
  window.__tarama = {
    rows: function () { return ROWS; }, state: st,
    /* "—" oranı: üç sütun setinin tüm hücreleri (taslaktaki ölçümle aynı yöntem) */
    dash: function () {
      var cells = 0, dash = 0, box = document.createElement('div');
      Object.keys(COLS).forEach(function (s) { COLS[s].forEach(function (k) { ROWS.forEach(function (r) { cells++; box.innerHTML = C[k].cell(r); var t = box.textContent.trim(); if (t === '' || t === '—' || t === '-') dash++; }); }); });
      return { cells: cells, dash: dash, pct: cells ? +(dash / cells * 100).toFixed(2) : null };
    }
  };
})();
