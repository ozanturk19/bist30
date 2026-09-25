/* ═══════════════════════════════════════════════════════════════════════
   static/js/bp-heatmap.js — C-55 (24.09.2026) ana sayfa BIST100 ısı haritası.

   templates/_heatmap.html kutuları SSR basar (yüzde geometri, renk, metin,
   /hisse/<T> bağlantısı). Bu dosya yalnız İYİLEŞTİRİR:
     1) px'te yeniden dizer: sektör kutuları D-42'nin 16:10 geometrisinden,
        hisseler her sektörün iç kutusunda squarify ile (2px aralık, etiket
        şeridi 20px). Kutunun boyu SSR'la aynı (aspect-ratio 16/10) -> kayma yok.
     2) Kap dar ise (<560px; aynı eşik _heatmap CSS'indeki container query)
        sektörler alt alta, her biri kendi haritasıyla (taslak C-M5 telefon düzeni).
     3) Yazı boyu kutu alanından; sığmayan kod/değişim/limit etiketi GİZLENİR
        (kırpılmaz).
     4) Mini kart: masaüstünde üzerine gelince, dokunmatikte ilk dokunuşta
        (ikinci dokunuş hisse sayfasına gider), klavyede odakta; Esc kapatır.
   Güvenli düşüş: JSON yok/bozuksa ya da DOM beklenen biçimde değilse hiçbir
   şeye dokunmaz, SSR kutuları olduğu gibi kalır.

   C-29 (25.09.2026) tam sayfa — YALNIZ kök `data-hm-full` taşıyorsa
   (/sektor-harita). Ana sayfa bu özniteliği taşımaz: oradaki davranış C-55 ile aynı.
     5) Renk modu (Değişim / BP Skoru / Trend) ve dönem (1G/1H/1A/YB/1Y) anahtarları
        yerinde boyar: kutu sınıfı + --k + metin + okunan ad, grup değeri, cümle,
        lejant, açıklama, sektör sıralaması. Kurallar _heatmap.html _paint() ve
        şablon cümleleriyle BİREBİR (biri değişirse öteki de).
     6) Durum adreste: ?renk=degisim|bp|trend&donem=1g|1h|1a|yb|1y; varsayılanlar
        yazılmaz, adresi yalnız publish() yazar (tek yayımcı, replaceState).
     7) Masaüstü haritada grup etiketi sığmazsa önce değeri, sonra kendisi gizlenir;
        grup yeterince yüksekse ad iki satıra kırılır (kırpılmaz).
   Renk ve yön bu dosyada HESAPLANMAZ (SSR'da, token'dan); biçimler
   bp-format.js / bp-vocab.js kanonundan (bpFormatPct, bpDirClass,
   bpMoneyCompact, sigLabel).
   ═══════════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  var root = document.querySelector('[data-hm]');
  var dataEl = document.getElementById('hmData');
  if (!root || !dataEl) return;
  var data;
  try { data = JSON.parse(dataEl.textContent || ''); } catch (e) { return; }
  if (!data || !Array.isArray(data.rows) || !data.rows.length) return;

  var body = root.querySelector('.hm-body');
  var map = root.querySelector('.hm-map');
  var card = root.querySelector('.hm-card');
  var gEls = root.querySelectorAll('.hm-g');
  if (!body || !map || !gEls.length) return;

  var byT = {};
  data.rows.forEach(function (r) { if (r && r.t) byT[r.t] = r; });
  var FULL = root.hasAttribute('data-hm-full');
  var st = { mode: root.getAttribute('data-mode') || 'chg', per: root.getAttribute('data-per') || 'd1' };

  function num(el, prop) {
    var v = parseFloat(el.style.getPropertyValue(prop));
    return isFinite(v) ? v : 0;
  }

  /* Model: sektör sırası ve geometrisi SSR'daki D-42 çıktısından (tek kanon),
     hisseler piyasa değeri büyükten küçüğe. */
  var groups = [], tiles = [], total = 0;
  Array.prototype.forEach.call(gEls, function (gEl) {
    var inner = gEl.querySelector('.hm-gi');
    if (!inner) return;
    var list = [];
    Array.prototype.forEach.call(gEl.querySelectorAll('.hm-t'), function (a) {
      var r = byT[a.getAttribute('data-t')] || null;
      list.push({
        el: a, r: r, value: (r && r.mcap > 0) ? r.mcap : 0,
        tk: a.querySelector('.hm-tk'), v: a.querySelector('.hm-v'), lim: a.querySelector('.hm-lim')
      });
    });
    if (!list.length) return;
    /* Piyasa değeri eksik kutu da dizilir (bağlantı kaybolmasın): grubun en küçüğü kadar. */
    var minV = Infinity;
    list.forEach(function (n) { if (n.value > 0 && n.value < minV) minV = n.value; });
    list.forEach(function (n) { if (!(n.value > 0)) n.value = isFinite(minV) ? minV : 1; });
    list.sort(function (a, b) { return b.value - a.value; });
    var sum = list.reduce(function (s, n) { return s + n.value; }, 0);
    total += sum;
    groups.push({
      el: gEl, lbl: gEl.querySelector('.hm-gl'), inner: inner, tiles: list, value: sum,
      x: num(gEl, '--x'), y: num(gEl, '--y'), w: num(gEl, '--w'), h: num(gEl, '--h')
    });
    tiles = tiles.concat(list);
  });
  if (!groups.length || !total) return;

  /* ── Squarified treemap (Bruls, Huizing & van Wijk 2000), d3-hierarchy
     treemapSquarify'ın oran kuralıyla. nodes büyükten küçüğe; her düğüme
     x0,y0,x1,y1 yazar. ── */
  function squarify(nodes, x0, y0, x1, y1, ratio) {
    var value = 0, i0 = 0, n = nodes.length, i;
    for (i = 0; i < n; i++) value += nodes[i].lv;
    while (i0 < n) {
      var dx = x1 - x0, dy = y1 - y0;
      if (dx <= 0 || dy <= 0 || value <= 0) {
        for (i = i0; i < n; i++) { nodes[i].x0 = nodes[i].x1 = x0; nodes[i].y0 = nodes[i].y1 = y0; }
        return;
      }
      var i1 = i0, sum = nodes[i1++].lv, minV = sum, maxV = sum;
      var alpha = Math.max(dy / dx, dx / dy) / (value * ratio);
      var beta = sum * sum * alpha;
      var best = Math.max(maxV / beta, beta / minV);
      for (; i1 < n; i1++) {
        var v = nodes[i1].lv, s2 = sum + v, mn = Math.min(minV, v), mx = Math.max(maxV, v);
        beta = s2 * s2 * alpha;
        var q = Math.max(mx / beta, beta / mn);
        if (q > best) break;
        sum = s2; minV = mn; maxV = mx; best = q;
      }
      var p, k, j;
      if (dx < dy) {                       /* satır: tam genişlik, üstten kesilir */
        var yb = y0 + dy * sum / value;
        k = dx / sum; p = x0;
        for (j = i0; j < i1; j++) { nodes[j].x0 = p; p += nodes[j].lv * k; nodes[j].x1 = p; nodes[j].y0 = y0; nodes[j].y1 = yb; }
        y0 = yb;
      } else {                             /* sütun: tam yükseklik, soldan kesilir */
        var xb = x0 + dx * sum / value;
        k = dy / sum; p = y0;
        for (j = i0; j < i1; j++) { nodes[j].y0 = p; p += nodes[j].lv * k; nodes[j].y1 = p; nodes[j].x0 = x0; nodes[j].x1 = xb; }
        x0 = xb;
      }
      value -= sum; i0 = i1;
    }
  }

  /* Kutuyu gap/2 büyütüp dizer, her düğümü gap/2 içeri çeker: düğümler arası
     `gap` px, dış kenarlar kutuyla hizalı; px'e yuvarlanır. */
  function tileRect(nodes, W, H, gap, ratio) {
    var h2 = gap / 2;
    squarify(nodes, -h2, -h2, W + h2, H + h2, ratio);
    nodes.forEach(function (n) {
      n.x0 = Math.round(n.x0 + h2); n.y0 = Math.round(n.y0 + h2);
      n.x1 = Math.max(n.x0, Math.round(n.x1 - h2)); n.y1 = Math.max(n.y0, Math.round(n.y1 - h2));
    });
  }

  function place(el, x, y, w, h) {
    el.style.left = x + 'px'; el.style.top = y + 'px';
    el.style.width = w + 'px'; el.style.height = h + 'px';
  }
  function unplace(el) { el.style.left = el.style.top = el.style.width = el.style.height = ''; }

  var LABEL_H = 20, GROUP_GAP = 7, TILE_GAP = 2, STACK_MAX = 560, MIN_T = 6;
  var cq = !!(window.CSS && CSS.supports && CSS.supports('container-type', 'inline-size'));

  /* Aşırı oranlı grupta (Savunma: ASELS 1.708 / ALTNY 14 Mrd) squarify son
     küçük kutuya 1-2px'lik şerit bırakır: bağlantı görünmez olur. Böyle kutunun
     YERLEŞİM ağırlığı (lv) 6px kalınlığa ulaşana dek ikiye katlanır; gerçek
     piyasa değeri (value) grup yüksekliğinde ve kartta aynen kalır. */
  function layoutTiles(g, W, H, ratio) {
    var nodes = g.tiles, it, bad;
    nodes.forEach(function (n) { n.lv = n.value; });
    for (it = 0; it < 6; it++) {
      nodes.sort(function (a, b) { return b.lv - a.lv; });
      tileRect(nodes, W, H, TILE_GAP, ratio);
      bad = false;
      nodes.forEach(function (n) {
        if (n.x1 - n.x0 < MIN_T || n.y1 - n.y0 < MIN_T) { n.lv *= 2; bad = true; }
      });
      if (!bad) break;
    }
    nodes.forEach(function (n) {
      n.w = n.x1 - n.x0; n.h = n.y1 - n.y0;
      place(n.el, n.x0, n.y0, n.w, n.h);
      n.el.classList.toggle('hm-off', n.w < 1 || n.h < 1);
      var fs = Math.max(9, Math.min(24, Math.sqrt(n.w * n.h) / 6.2));
      n.el.style.setProperty('--fs', fs.toFixed(1) + 'px');
    });
  }

  /* Metin sığdırma: önce hepsi görünür, TEK okuma turu, sonra gizleme. */
  function fitText() {
    tiles.forEach(function (n) {
      [n.tk, n.v, n.lim].forEach(function (s) { if (s) s.classList.remove('hm-off'); });
    });
    var m = tiles.map(function (n) {
      return {
        tk: n.tk ? [n.tk.offsetWidth, n.tk.offsetTop + n.tk.offsetHeight] : null,
        v: n.v ? [n.v.offsetWidth, n.v.offsetTop + n.v.offsetHeight] : null,
        lim: n.lim ? [n.lim.offsetWidth, n.lim.offsetTop + n.lim.offsetHeight] : null
      };
    });
    tiles.forEach(function (n, i) {
      var q = m[i], w = n.w || 0, h = n.h || 0;
      var tkOk = !!q.tk && 7 + q.tk[0] <= w - 3 && q.tk[1] <= h - 2;
      var vOk = tkOk && !!q.v && 7 + q.v[0] <= w - 3 && q.v[1] <= h - 3;
      var limOk = tkOk && !!q.lim && 7 + q.tk[0] + 6 + q.lim[0] + 5 <= w && q.lim[1] <= h - 2;
      if (n.tk) n.tk.classList.toggle('hm-off', !tkOk);
      if (n.v) n.v.classList.toggle('hm-off', !vOk);
      if (n.lim) n.lim.classList.toggle('hm-off', !limOk);
    });
  }

  var lastW = -1;
  function layout() {
    var W = body.getBoundingClientRect().width;
    if (!W) return;
    var Wi = Math.floor(W);
    hideCard(true);
    var stack = cq && W < STACK_MAX;
    root.classList.toggle('hm-stack', stack);
    if (!stack) {
      var H = map.clientHeight || Math.round(Wi / 1.6);
      var Wg = Wi + GROUP_GAP, Hg = H + GROUP_GAP;
      groups.forEach(function (g) {
        var x0 = Math.round(g.x / 100 * Wg), y0 = Math.round(g.y / 100 * Hg);
        var x1 = Math.max(x0, Math.round((g.x + g.w) / 100 * Wg - GROUP_GAP));
        var y1 = Math.max(y0, Math.round((g.y + g.h) / 100 * Hg - GROUP_GAP));
        var gw = x1 - x0, gh = y1 - y0;
        var lh = (gh >= 56 && gw >= 64) ? LABEL_H : 0;
        place(g.el, x0, y0, gw, gh);
        if (FULL) lh = fitLabel(g, gw, gh, lh);
        if (g.lbl) g.lbl.classList.toggle('hm-off', !lh);
        g.inner.style.top = lh + 'px';
        g.inner.style.height = '';
        layoutTiles(g, gw, gh - lh, 1.15);
      });
    } else {
      var budget = Math.max(1500, W * 4.6);
      groups.forEach(function (g) {
        var h = Math.round(Math.max(78, Math.min(360, budget * g.value / total)));
        unplace(g.el);
        if (g.lbl) g.lbl.classList.remove('hm-off');
        if (FULL && g.lbl) g.lbl.classList.remove('hm-gl2');
        g.inner.style.top = '';
        g.inner.style.height = h + 'px';
        layoutTiles(g, Wi, h, 1.1);
      });
    }
    fitText();
    lastW = W;
  }

  /* ── Mini kart ─────────────────────────────────────────────────────── */
  var canCard = !!card && typeof bpFormatPct === 'function' && typeof bpDirClass === 'function';
  var pinned = null, shownFor = null, lastPointer = '';
  var PER = [['d1', '1G'], ['w1', '1H'], ['m1', '1A'], ['ytd', 'YB'], ['y1', '1Y']];
  var TR_SIG = { guclu: 'AL', yatay: 'BEKLE', bozuk: 'SAT' };

  function mk(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  function row(label, value) {
    var d = mk('div', 'c-row');
    d.appendChild(mk('span', null, label));
    d.appendChild(mk('b', null, value));
    return d;
  }
  function dirCls(v, frac) { return bpDirClass(v, frac, ['up', 'dn', 'neu']); }
  function trLabel(tr) {
    var sig = TR_SIG[tr];
    if (!sig) return 'Kapsam dışı';
    return (typeof sigLabel === 'function') ? sigLabel(sig) : '—';
  }
  function money(bn) {
    if (typeof bpMoneyCompact !== 'function' || !(bn > 0)) return '—';
    var tl = bn * 1e9;
    return bpMoneyCompact(tl, { frac: tl >= 1e12 ? 2 : (tl >= 1e11 ? 0 : 1) }) || '—';
  }
  function price(p) {
    return (typeof p === 'number' && isFinite(p))
      ? p.toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' ₺' : '—';
  }

  function fillCard(t, r) {
    var ch = r.ch || {};
    while (card.firstChild) card.removeChild(card.firstChild);
    var top = mk('div', 'c-top');
    top.appendChild(mk('b', null, t));
    if (r.n) top.appendChild(mk('span', null, r.n));
    card.appendChild(top);
    var sec = [r.g, r.sub].filter(Boolean).join(' · ');
    if (sec) card.appendChild(mk('div', 'c-sec', sec));
    var sel = FULL ? st.per : 'd1';
    var pr = mk('div', 'c-price');
    pr.appendChild(mk('strong', null, price(r.p)));
    pr.appendChild(mk('span', 'c-ch ' + dirCls(ch[sel], 2), bpFormatPct(ch[sel], 2)));
    var asof = sel === 'd1' ? data.asof_label : perInfo(sel)[1];
    if (asof) pr.appendChild(mk('span', 'c-asof', asof));
    card.appendChild(pr);
    var per = mk('div', 'c-per');
    PER.forEach(function (p) {
      var c = mk('div', (FULL && p[0] === sel) ? 'on' : null);
      c.appendChild(mk('em', null, p[1]));
      var pv = ch[p[0]];   /* 5 dar hücre: |%| >= 100 tam sayı, yoksa 1 ondalık */
      c.appendChild(mk('span', dirCls(pv, 1), bpFormatPct(pv, (typeof pv === 'number' && Math.abs(pv) >= 100) ? 0 : 1)));
      per.appendChild(c);
    });
    card.appendChild(per);
    card.appendChild(row('Piyasa değeri', money(r.mcap)));
    card.appendChild(row('BorsaPusula Skoru', (typeof r.bp === 'number') ? String(r.bp) : '—'));
    card.appendChild(row('Trend', trLabel(r.tr) + ((r.tr && r.days > 0) ? ' · ' + r.days + ' gündür' : '')));
    if (r.lim === 'tavan' || r.lim === 'taban') card.appendChild(row('Günlük limit', r.lim === 'tavan' ? 'Tavan' : 'Taban'));
    if (r.stale) card.appendChild(mk('div', 'c-note', 'Veri gecikmeli'));
    var go = mk('a', 'c-go', 'Hisse sayfası →');
    go.href = '/hisse/' + encodeURIComponent(t);
    card.appendChild(go);
  }

  function showCard(a, cx, cy) {
    if (!canCard) return;
    var t = a.getAttribute('data-t'), r = byT[t];
    if (!r) return;
    if (shownFor !== a) {
      fillCard(t, r);
      if (shownFor) shownFor.removeAttribute('aria-describedby');
      shownFor = a;
      a.setAttribute('aria-describedby', card.id);
    }
    card.hidden = false;
    var R = root.getBoundingClientRect(), cw = card.offsetWidth, chh = card.offsetHeight;
    var x = cx - R.left + 16, y = cy - R.top + 16;
    if (x + cw > R.width - 8) x = cx - R.left - cw - 16;
    if (x < 8) x = Math.max(8, Math.min(R.width - cw - 8, cx - R.left - cw / 2));
    if (y + chh > R.height - 8) y = cy - R.top - chh - 16;
    if (y < 8) y = 8;
    card.style.left = Math.round(x) + 'px';
    card.style.top = Math.round(y) + 'px';
  }
  function hideCard(force) {
    if (!card || (pinned && !force)) return;
    pinned = null;
    card.hidden = true;
    if (shownFor) { shownFor.removeAttribute('aria-describedby'); shownFor = null; }
  }
  function tileOf(t) { return (t && t.closest) ? t.closest('.hm-t') : null; }
  function atTile(a, bottom) {
    var b = a.getBoundingClientRect();
    showCard(a, b.left + b.width / 2, bottom ? b.bottom - 4 : b.top + b.height / 2);
  }

  if (canCard) {
    map.addEventListener('pointerdown', function (e) { lastPointer = e.pointerType || ''; });
    map.addEventListener('pointermove', function (e) {
      if (e.pointerType === 'touch' || pinned) return;
      var a = tileOf(e.target);
      if (a) showCard(a, e.clientX, e.clientY); else hideCard();
    });
    map.addEventListener('pointerleave', function (e) {
      if (e.pointerType !== 'touch') hideCard();
    });
    /* Dokunmatik: ilk dokunuş kartı sabitler, aynı kutuya ikinci dokunuş
       bağlantıyı izler. Fare ve klavye (detail 0) doğrudan gider. */
    map.addEventListener('click', function (e) {
      var a = tileOf(e.target);
      if (!a || e.detail === 0 || lastPointer === 'mouse') return;
      if (lastPointer === '' && window.matchMedia && matchMedia('(hover: hover)').matches) return;
      if (pinned !== a) {
        e.preventDefault(); pinned = null; atTile(a, false); pinned = a;
        /* Kart ekranın altında kalıp alt gezinmenin arkasına düşmesin (scroll-margin CSS'te). */
        var still = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
        try { card.scrollIntoView({ block: 'nearest', behavior: still ? 'auto' : 'smooth' }); } catch (err) { /* eski tarayıcı: kart yerinde kalır */ }
      }
    });
    map.addEventListener('focusin', function (e) {
      var a = tileOf(e.target);
      if (!a || pinned) return;
      var kb = true;
      try { kb = a.matches(':focus-visible'); } catch (err) { kb = true; }
      if (kb) atTile(a, true);
    });
    map.addEventListener('focusout', function (e) {
      if (!pinned && !(e.relatedTarget && card.contains(e.relatedTarget))) hideCard();
    });
    document.addEventListener('click', function (e) {
      if (!pinned || card.contains(e.target) || tileOf(e.target) === pinned) return;
      hideCard(true);
    });
    document.addEventListener('keydown', function (e) {
      if ((e.key === 'Escape' || e.key === 'Esc') && !card.hidden) hideCard(true);
    });
  }

  /* ── C-29: tam sayfa (yalnız data-hm-full) ─────────────────────────── */
  /* (kod, düğme, okunan ad, lejant adı, açıklama cümlesi, cümle öneki, sıralama cümlesi) — _heatmap.html _PER */
  var PERS = [
    ['d1', '1G', '1 gün', 'Gün sonu değişim', 'gün sonu değişimi', '', 'gün sonu değişime'],
    ['w1', '1H', '1 hafta', '1 haftalık değişim', '1 haftalık değişim', '1 haftada ', '1 haftalık değişime'],
    ['m1', '1A', '1 ay', '1 aylık değişim', '1 aylık değişim', '1 ayda ', '1 aylık değişime'],
    ['ytd', 'YB', 'yılbaşından beri', 'Yılbaşından beri değişim', 'yılbaşından beri değişim', 'Yılbaşından beri ', 'yılbaşından beri değişime'],
    ['y1', '1Y', '1 yıl', '1 yıllık değişim', '1 yıllık değişim', '1 yılda ', '1 yıllık değişime']
  ];
  var CAP = { d1: 3, w1: 6, m1: 12, ytd: 50, y1: 80 };
  var MQ = { chg: 'degisim', bp: 'bp', tr: 'trend' }, PQ = { d1: '1g', w1: '1h', m1: '1a', ytd: 'yb', y1: '1y' };
  var PAINT = ['up', 'dn', 'neu', 'na', 'bp-hi', 'bp-lo', 'tr-g', 'tr-y', 'tr-b', 'dark', 'lim', 'tavan', 'taban', 'stale'];
  function perInfo(p) {
    for (var i = 0; i < PERS.length; i++) if (PERS[i][0] === p) return PERS[i];
    return PERS[0];
  }
  function isNum(v) { return typeof v === 'number' && isFinite(v); }
  /* Jinja |round (Python round) ile aynı yuvarlama: tam yarımda çifte (22,25 → 22,2).
     toFixed tam yarımı yukarı atar; SSR metni (bpf.pct_text) ile JS metni ayrışmasın diye
     tam sayfa metinleri önce bununla yuvarlanır. */
  function pyRound(v, f) {
    var m = Math.pow(10, f), x = v * m, fl = Math.floor(x);
    if (x - fl === 0.5) return (fl % 2 === 0 ? fl : fl + 1) / m;
    return parseFloat(v.toFixed(f));
  }
  function esc(x) { return String(x).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  /* Türkçe iyelik eki (_heatmap.html _poss ile aynı): 71'i, 4'ü, 6'sı, 10'u, 100'ü */
  function poss(n) {
    var u = n % 10, t = Math.floor(n / 10) % 10;
    if (n === 0) return 'ı';
    if (u) return ['', 'i', 'si', 'ü', 'ü', 'i', 'sı', 'si', 'i', 'u'][u];
    if (t) return ['', 'u', 'si', 'u', 'ı', 'si', 'ı', 'i', 'i', 'ı'][t];
    return (Math.floor(n / 100) % 10) ? 'ü' : 'i';
  }
  /* Kutu boyası — _heatmap.html _paint() ile BİREBİR */
  function paint(r) {
    r = r || {};
    if (st.mode === 'bp') {
      var b = r.bp;
      if (!isNum(b)) return { cls: 'na', k: 0, dark: false, vt: '—', av: 'BorsaPusula Skoru yok' };
      var bi = Math.floor(b + 0.5), d = (b - 50) / 40, t = Math.min(Math.abs(d), 1), k;
      if (d >= 0) { k = 0.10 + 0.85 * Math.pow(t, 0.9); return { cls: 'bp-hi', k: k, dark: k >= 0.55, vt: 'BP ' + bi, av: 'BorsaPusula Skoru ' + bi }; }
      k = 0.08 + 0.55 * Math.pow(t, 0.9);
      return { cls: 'bp-lo', k: k, dark: false, vt: 'BP ' + bi, av: 'BorsaPusula Skoru ' + bi };
    }
    if (st.mode === 'tr') {
      if (r.tr === 'guclu') return { cls: 'tr-g', k: 0.9, dark: true, vt: 'Güçlü Trend', av: 'Güçlü Trend' };
      if (r.tr === 'yatay') return { cls: 'tr-y', k: 0, dark: false, vt: 'Yatay', av: 'Yatay' };
      if (r.tr === 'bozuk') return { cls: 'tr-b', k: 0, dark: false, vt: 'Trend Bozuldu', av: 'Trend Bozuldu' };
      return { cls: 'na', k: 0, dark: false, vt: '—', av: 'trend verisi yok' };
    }
    var v = r.ch ? r.ch[st.per] : null;
    if (!isNum(v)) return { cls: 'na', k: 0, dark: false, vt: '—', av: 'değişim verisi yok' };
    v = pyRound(v, 2);
    var cls = bpDirClass(v, 2, ['up', 'dn', 'neu']);
    var tt = Math.min(Math.abs(v) / CAP[st.per], 1);
    var kk = cls !== 'neu' ? 0.16 + 0.84 * Math.pow(tt, 0.72) : 0;
    if (r.stale) kk = kk * 0.45;
    var dk = (cls === 'up' && kk >= 0.55) || (cls === 'dn' && kk >= 0.83);
    return { cls: cls, k: kk, dark: dk, vt: bpFormatPct(v, 2), av: bpFormatPct(v, 2) };
  }
  /* Grup değeri (etiket + sıralama): Değişim = piyasa değeriyle ağırlıklı, BP = ortalama, Trend = Güçlü Trend sayısı */
  function gAgg(g) {
    var a = { n: 0, s: 0, w: 0, bs: 0, bn: 0, tg: 0 };
    g.tiles.forEach(function (n) {
      var r = n.r;
      if (!r || !(r.mcap > 0)) return;
      a.n++;
      var v = r.ch ? r.ch[st.per] : null;
      if (isNum(v)) { a.s += v * r.mcap; a.w += r.mcap; }
      if (isNum(r.bp)) { a.bs += r.bp; a.bn++; }
      if (r.tr === 'guclu') a.tg++;
    });
    a.c = a.w ? pyRound(a.s / a.w, 1) : null;
    a.b = a.bn ? Math.floor(a.bs / a.bn + 0.5) : null;
    return a;
  }
  function thesis() {
    var rows = data.rows, n = data.n || rows.length, i, r;
    if (st.mode === 'bp') {
      var bs = rows.filter(function (x) { return isNum(x.bp); }), out = '';
      if (bs.length) {
        var avg = Math.floor(bs.reduce(function (s, x) { return s + x.bp; }, 0) / bs.length + 0.5);
        out = 'Ortalama BorsaPusula Skoru <b class="neu">' + avg + '</b> · <b class="up">' +
          bs.filter(function (x) { return x.bp >= 70; }).length + '</b> hissede 70 ve üstü';
      }
      if (rows.length > bs.length) out += (bs.length ? ' · ' : '') + '<b class="neu">' + (rows.length - bs.length) + '</b> hissede skor yok';
      return out;
    }
    if (st.mode === 'tr') {
      var c = { guclu: 0, yatay: 0, bozuk: 0 };
      rows.forEach(function (x) { if (c.hasOwnProperty(x.tr)) c[x.tr]++; });
      var s = '<b class="up">' + c.guclu + '</b> hisse Güçlü Trend\'de · <b class="neu">' + c.yatay + '</b> Yatay · <b class="neu">' + c.bozuk + '</b> Trend Bozuldu';
      var na = rows.length - c.guclu - c.yatay - c.bozuk;
      return s + (na > 0 ? ' · <b class="neu">' + na + '</b> hissede trend verisi yok' : '');
    }
    var up = 0, dn = 0, fl = 0, tv = 0, tb = 0;
    if (st.per === 'd1' && data.counts) { up = data.counts.up || 0; dn = data.counts.down || 0; fl = data.counts.flat || 0; }
    else {
      for (i = 0; i < rows.length; i++) {
        r = rows[i];
        var v = r.ch ? r.ch[st.per] : null;
        if (!isNum(v)) continue;
        var rv = pyRound(v, 2);
        if (rv > 0) up++; else if (rv < 0) dn++; else fl++;
      }
    }
    if (st.per === 'd1') rows.forEach(function (x) { if (x.lim === 'tavan') tv++; else if (x.lim === 'taban') tb++; });
    var xu = (data.xu100 && data.xu100.ch) ? data.xu100.ch[st.per] : null;
    if (isNum(xu)) xu = pyRound(xu, 2);
    var sep = '', o = perInfo(st.per)[5];
    if (up || dn || fl) {
      o += n + ' hissenin';
      if (up === n) o += ' tamamı <b class="up">yükseldi</b>';
      else if (dn === n) o += ' tamamı <b class="dn">düştü</b>';
      else {
        var sp = '';
        if (up) { o += ' <b class="up">' + up + '</b>\'' + poss(up) + ' yükseldi'; sp = ','; }
        if (dn) { o += sp + ' <b class="dn">' + dn + '</b>\'' + poss(dn) + ' düştü'; sp = ','; }
        if (fl) o += sp + ' <b class="neu">' + fl + '</b>\'' + poss(fl) + ' değişmedi';
      }
      sep = ' · ';
    }
    if (isNum(xu)) { o += sep + 'BIST100 <b class="' + bpDirClass(xu, 2, ['up', 'dn', 'neu']) + '">' + bpFormatPct(xu, 2) + '</b>'; sep = ' · '; }
    if (tv) { o += sep + '<b class="neu">' + tv + '</b> tavan'; sep = ', '; }
    if (tb) o += sep + '<b class="neu">' + tb + '</b> taban';
    return o;
  }
  function href(m, p) {
    var q = [];
    if (m !== 'chg') q.push('renk=' + MQ[m]);
    if (p !== 'd1') q.push('donem=' + PQ[p]);
    return location.pathname + (q.length ? '?' + q.join('&') : '');
  }
  /* Masaüstü grup etiketi: sığdır ya da gizle (kırpma yok). Dönüş: etiket şeridi yüksekliği. */
  function fitLabel(g, gw, gh, lh) {
    var L = g.lbl;
    if (!L) return lh;
    L.classList.remove('hm-gl2');
    var b = L.querySelector('b'), i = L.querySelector('i');
    if (i) i.classList.remove('hm-off');
    if (!lh || !b) return lh;
    L.classList.remove('hm-off');
    if (b.scrollWidth <= b.clientWidth + 0.5) return lh;
    if (i) i.classList.add('hm-off');
    if (b.scrollWidth <= b.clientWidth + 0.5) return lh;
    if (gh >= 110) {
      L.classList.add('hm-gl2');
      var two = Math.ceil(L.getBoundingClientRect().height);
      if (b.scrollWidth <= b.clientWidth + 0.5 && two <= 36) return two + 2;
      L.classList.remove('hm-gl2');
    }
    return 0;
  }
  function repaint() {
    var lon = st.mode === 'chg' && st.per === 'd1', anyNa = false, anyStale = false;
    root.setAttribute('data-mode', st.mode);
    root.setAttribute('data-per', st.per);
    ['chg', 'bp', 'tr'].forEach(function (m) { root.classList.toggle('hm-m-' + m, m === st.mode); });
    root.classList.toggle('hm-lim-on', lon);
    tiles.forEach(function (n) {
      var r = n.r || {}, p = paint(r), el = n.el;
      var stale = !!r.stale && st.mode === 'chg';
      var lim = (lon && (r.lim === 'tavan' || r.lim === 'taban')) ? r.lim : null;
      PAINT.forEach(function (c) { el.classList.remove(c); });
      el.classList.add(p.cls);
      if (p.dark) el.classList.add('dark');
      if (lim) { el.classList.add('lim'); el.classList.add(lim); }
      if (stale) { el.classList.add('stale'); anyStale = true; }
      if (p.cls === 'na') anyNa = true;
      el.style.setProperty('--k', p.k.toFixed(3));
      if (n.v) n.v.textContent = p.vt;
      var t = el.getAttribute('data-t');
      el.setAttribute('aria-label', t + (r.n ? ', ' + r.n : '') + ', ' + p.av + (lim ? ', ' + lim : '') + (stale ? ', veri gecikmeli' : ''));
    });
    /* grup etiketi değeri */
    groups.forEach(function (g) {
      g.agg = gAgg(g);
      var i = g.lbl ? g.lbl.querySelector('i') : null;
      if (!i) return;
      var a = g.agg, cls = 'neu', tx = '';
      if (st.mode === 'bp') tx = a.b != null ? 'ort. ' + a.b : '';
      else if (st.mode === 'tr') { cls = a.tg ? 'up' : 'neu'; tx = a.tg + ' Güçlü Trend'; }
      else { cls = bpDirClass(a.c, 1, ['up', 'dn', 'neu']) || 'neu'; tx = a.c != null ? bpFormatPct(a.c, 1) : ''; }
      i.className = cls;
      i.textContent = tx;
    });
    var th = document.getElementById('hmThesis');
    if (th) th.innerHTML = thesis();
    /* lejant + açıklama */
    var pi = perInfo(st.per), cap = CAP[st.per], half = cap / 2, hf = (half % 1) ? 1 : 0;
    Array.prototype.forEach.call(root.querySelectorAll('[data-lg]'), function (lg) {
      var on = lg.getAttribute('data-lg') === st.mode;
      lg.hidden = !on;
      var na = lg.querySelector('[data-lg-na]');
      if (na) na.hidden = !(on && anyNa);
    });
    var tk = root.querySelector('[data-lg-ticks]');
    if (tk) tk.innerHTML = [bpFormatPct(-cap, 0), bpFormatPct(-half, hf), '0', bpFormatPct(half, hf), bpFormatPct(cap, 0)]
      .map(function (x) { return '<span>' + esc(x) + '</span>'; }).join('');
    var ln = root.querySelector('[data-lg-name]');
    if (ln) ln.textContent = pi[3];
    var ls = root.querySelector('[data-lg-stale]');
    if (ls) ls.hidden = !anyStale;
    var src = document.getElementById('hmSrc');
    if (src) src.textContent = st.mode === 'bp'
      ? 'Kutu büyüklüğü piyasa değeri, renk BorsaPusula Skoru: 50 nötr; 90 ve üstü en koyu yeşil, 10 ve altı en koyu mor.'
      : (st.mode === 'tr' ? 'Kutu büyüklüğü piyasa değeri, renk trend durumu.'
        : 'Kutu büyüklüğü piyasa değeri, renk ' + pi[4] + '; ±%' + cap + ' ve üstü en koyu tonda.');
    /* anahtarlar */
    Array.prototype.forEach.call(root.querySelectorAll('.hm-sw[data-m]'), function (a) {
      var m = a.getAttribute('data-m');
      a.setAttribute('href', href(m, st.per));
      if (m === st.mode) a.setAttribute('aria-current', 'true'); else a.removeAttribute('aria-current');
    });
    var pseg = root.querySelector('.hm-seg-per');
    if (pseg) { if (st.mode === 'chg') pseg.removeAttribute('aria-disabled'); else pseg.setAttribute('aria-disabled', 'true'); }
    Array.prototype.forEach.call(root.querySelectorAll('.hm-sw[data-p]'), function (a) {
      var p = a.getAttribute('data-p');
      if (st.mode === 'chg') { a.setAttribute('href', href('chg', p)); a.removeAttribute('aria-disabled'); }
      else { a.removeAttribute('href'); a.setAttribute('aria-disabled', 'true'); }
      if (p === st.per) a.setAttribute('aria-current', 'true'); else a.removeAttribute('aria-current');
    });
    sortList();
  }
  /* Sektör sıralaması: seçili ölçü, yüksekten düşüğe; eşitlikte piyasa değeri sırası (harita sırası) */
  function sortList() {
    var ol = document.getElementById('hmSl');
    if (!ol) return;
    var byG = {};
    Array.prototype.forEach.call(ol.children, function (li) { byG[li.getAttribute('data-g')] = li; });
    var items = [];
    groups.forEach(function (g, idx) {
      var name = g.el.getAttribute('aria-label'), li = byG[name], a = g.agg;
      if (!li || !a) return;
      var key = st.mode === 'chg' ? (a.c != null ? a.c : -1e9)
        : (st.mode === 'bp' ? (a.b != null ? a.b : -1e9) : a.tg);
      var c = li.querySelector('.hm-sr-chg'), b = li.querySelector('.hm-sr-bp'), t = li.querySelector('.hm-sr-tr');
      if (c) { c.className = 'hm-sr-m hm-sr-chg ' + (bpDirClass(a.c, 1, ['up', 'dn', 'neu']) || '') + (st.mode === 'chg' ? ' on' : ''); c.textContent = bpFormatPct(a.c, 1); }
      if (b) { b.className = 'hm-sr-m hm-sr-bp' + (st.mode === 'bp' ? ' on' : ''); b.textContent = 'BP ort. ' + (a.b != null ? a.b : '—'); }
      if (t) { t.className = 'hm-sr-m hm-sr-tr' + (a.tg ? ' up' : '') + (st.mode === 'tr' ? ' on' : ''); t.textContent = a.tg + ' Güçlü Trend'; }
      items.push({ li: li, key: key, idx: idx });
    });
    items.sort(function (x, y) { return (y.key - x.key) || (x.idx - y.idx); });
    items.forEach(function (it) { ol.appendChild(it.li); });
    var sub = document.getElementById('hmSumSub');
    if (sub) sub.textContent = st.mode === 'bp' ? 'Ortalama BorsaPusula Skoruna göre, yüksekten düşüğe.'
      : (st.mode === 'tr' ? 'Güçlü Trend\'deki hisse sayısına göre, çoktan aza.'
        : 'Piyasa değeriyle ağırlıklı ' + perInfo(st.per)[6] + ' göre, yüksekten düşüğe.');
  }
  /* Adresin TEK yayımcısı: varsayılanlar yazılmaz; eski Karşılaştır parametreleri (tab, s) temizlenir */
  function publish() {
    try {
      var u = new URL(location.href);
      ['renk', 'donem', 'tab', 's'].forEach(function (k) { u.searchParams.delete(k); });
      if (st.mode !== 'chg') u.searchParams.set('renk', MQ[st.mode]);
      if (st.per !== 'd1') u.searchParams.set('donem', PQ[st.per]);
      var next = u.pathname + u.search + u.hash;
      if (next !== location.pathname + location.search + location.hash) history.replaceState(history.state, '', next);
    } catch (e) { /* eski tarayıcı: adres değişmez, harita yine boyanır */ }
  }
  function setState(m, p) {
    if (m === st.mode && p === st.per) return;
    st.mode = m; st.per = p;
    hideCard(true);
    repaint();
    layout();
    publish();
  }
  if (FULL) {
    var MR = { degisim: 'chg', bp: 'bp', trend: 'tr' }, PR = { '1g': 'd1', '1h': 'w1', '1a': 'm1', 'yb': 'ytd', '1y': 'y1' };
    var ctl = root.querySelector('.hm-ctl');
    if (ctl) ctl.addEventListener('click', function (e) {
      var a = (e.target && e.target.closest) ? e.target.closest('.hm-sw') : null;
      if (!a || e.ctrlKey || e.metaKey || e.shiftKey || e.button === 1) return;
      e.preventDefault();
      if (a.hasAttribute('data-m')) setState(a.getAttribute('data-m'), st.per);
      else if (a.hasAttribute('data-p') && st.mode === 'chg') setState('chg', a.getAttribute('data-p'));
    });
    /* Adresten geri yükleme (SSR zaten aynı durumu çizdi; bfcache/önbellek farkına karşı) */
    try {
      var q = new URLSearchParams(location.search);
      var qm = MR[(q.get('renk') || '').toLowerCase()] || 'chg', qp = PR[(q.get('donem') || '').toLowerCase()] || 'd1';
      if (qm !== st.mode || qp !== st.per) { st.mode = qm; st.per = qp; }
    } catch (e) { /* URLSearchParams yok: SSR durumu kalır */ }
    repaint();
    publish();
  }

  root.classList.add('js');
  layout();
  var tmr = null;
  function onResize() {
    var W = body.getBoundingClientRect().width;
    if (Math.abs(W - lastW) < 0.5) return;
    clearTimeout(tmr);
    tmr = setTimeout(layout, 120);
  }
  if (window.ResizeObserver) new ResizeObserver(onResize).observe(body);
  else window.addEventListener('resize', onResize);
})();
