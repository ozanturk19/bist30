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
    var pr = mk('div', 'c-price');
    pr.appendChild(mk('strong', null, price(r.p)));
    pr.appendChild(mk('span', 'c-ch ' + dirCls(ch.d1, 2), bpFormatPct(ch.d1, 2)));
    if (data.asof_label) pr.appendChild(mk('span', 'c-asof', data.asof_label));
    card.appendChild(pr);
    var per = mk('div', 'c-per');
    PER.forEach(function (p) {
      var c = mk('div');
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
