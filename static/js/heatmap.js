/* SPEC-018 BIST Heatmap MVP — Vanilla Squarified Treemap
 * Çar 27 May 2026, Ozan-direktif
 * Algoritma referansı: Bruls/Huijbregts/van Wijk 1999 squarified treemap
 * Boyut: tier_score (v2 market_cap); Renk: tier (Standart/Plus/Premium) + signal
 */
(function () {
  'use strict';

  // ── SPEC-021: Mode state ─────────────────────────────────────────────────
  var _urlMode = new URLSearchParams(location.search).get('mode');
  var currentMode = _urlMode || localStorage.getItem('bp_heatmap_mode') || 'sinyal';
  var allCellRefs = []; // {rect, item} for quick color update on mode switch
  var _toggleInited = false;

  // ── SPEC-021: Piyasa modu renk fonksiyonu (diverging gradient) ───────────
  function piyasaColor(item) {
    var pct = item.change_pct;
    if (pct == null) return '#252b36';
    if (pct <= -5) return '#7d1e1e';
    if (pct <= -3) return '#912525';
    if (pct <= -1) return '#6b3030';
    if (pct < 0)   return '#4a2a2a';
    if (pct === 0) return '#252b36';
    if (pct < 1)   return '#1d3020';
    if (pct < 3)   return '#1d4028';
    if (pct < 5)   return '#207038';
    return '#2da44e';
  }

  function piyasaOpacity() { return 1.0; }

  // ── Tier renk fonksiyonu — G16 satürasyon dengeleme ─────────────────────
  function tierColor(item) {
    var sig = item.signal;
    if (sig === 'SAT') return '#E05550';    // Zayıf Trend: softer kırmızı
    if (sig === 'BEKLE' || sig == null) return '#252b36';  // Yatay: koyu slate
    // AL: tier_score'a göre Premium/Plus/Standart
    var score = item.tier_score || 0;
    if (score >= 70) return '#F0C240';  // Premium: sıcak denge altın
    if (score >= 50) return '#88A8C0';  // Plus: mavi-gümüş
    if (score >= 30) return '#C07838';  // Standart: sıcak bronz
    return '#50506a';  // Çok zayıf AL (nadir)
  }

  function tierLabel(item) {
    var sig = item.signal;
    if (sig === 'SAT') return 'SAT';
    if (sig === 'BEKLE' || sig == null) return 'BEKLE';
    var score = item.tier_score || 0;
    if (score >= 70) return 'Premium';
    if (score >= 50) return 'Plus';
    if (score >= 30) return 'Standart';
    return 'AL (zayıf)';
  }

  function tierOpacity(item) {
    var sig = item.signal;
    if (sig === 'SAT') return 1.0;
    if (sig === 'BEKLE' || sig == null) return 0.40;
    var score = item.tier_score || 0;
    if (score >= 70) return 1.0;   // Premium
    if (score >= 50) return 0.85;  // Plus
    if (score >= 30) return 0.70;  // Standart
    return 0.40;
  }

  // ── Squarified treemap algoritması ──────────────────────────────────────
  // İnput: items array (her item.value pozitif), rect {x,y,w,h}
  // Output: items'a x,y,w,h ekler
  function squarify(items, rect) {
    if (!items.length) return;
    // value'larını rect alanına normalize et
    var totalValue = items.reduce(function(s, it){ return s + it._size; }, 0);
    if (totalValue <= 0) return;
    var area = rect.w * rect.h;
    items.forEach(function(it){ it._area = (it._size / totalValue) * area; });

    // Squarified ana döngü
    var remaining = items.slice();
    var x = rect.x, y = rect.y, w = rect.w, h = rect.h;

    while (remaining.length) {
      var row = [];
      var bestRatio = Infinity;
      // Side: dikey mi yatay mı, kısa kenar
      var side = Math.min(w, h);

      // Greedy: en iyi ratio'lu satırı oluştur
      for (var i = 0; i < remaining.length; i++) {
        row.push(remaining[i]);
        var ratio = worstRatio(row, side);
        if (ratio > bestRatio) {
          // Eklemek kötüleştirdi, son ekleneni geri al
          row.pop();
          break;
        }
        bestRatio = ratio;
      }

      if (!row.length) break;
      // Layout the row
      var rowArea = row.reduce(function(s, it){ return s + it._area; }, 0);
      if (w >= h) {
        // Yatay genişlik daha büyük → satır soldan başlar dikey kolon
        var rowW = rowArea / h;
        var ry = y;
        row.forEach(function(it){
          var ih = it._area / rowW;
          it.x = x; it.y = ry; it.w = rowW; it.h = ih;
          ry += ih;
        });
        x += rowW; w -= rowW;
      } else {
        // Dikey daha büyük → satır üstten başlar yatay
        var rowH = rowArea / w;
        var rx = x;
        row.forEach(function(it){
          var iw = it._area / rowH;
          it.x = rx; it.y = y; it.w = iw; it.h = rowH;
          rx += iw;
        });
        y += rowH; h -= rowH;
      }

      remaining = remaining.slice(row.length);
    }
  }

  function worstRatio(row, side) {
    var sum = row.reduce(function(s, it){ return s + it._area; }, 0);
    var max = row.reduce(function(m, it){ return Math.max(m, it._area); }, 0);
    var min = row.reduce(function(m, it){ return Math.min(m, it._area); }, Infinity);
    var s2 = side * side;
    var sum2 = sum * sum;
    return Math.max((s2 * max) / sum2, sum2 / (s2 * min));
  }

  // ── Render ───────────────────────────────────────────────────────────────
  function render(data) {
    allCellRefs = []; // reset on each re-render (resize)
    var container = document.getElementById('heatmap-container');
    container.innerHTML = '';

    // Sektör bazlı grupla
    var bySector = {};
    data.stocks.forEach(function(s){
      var sec = s.sector || 'Diğer';
      if (!bySector[sec]) bySector[sec] = [];
      bySector[sec].push(s);
    });

    // Sektör listesi — her sektör için toplam tier_score
    var sectors = Object.keys(bySector).map(function(name){
      var stocks = bySector[name];
      var totalScore = stocks.reduce(function(s, st){
        // Minimum boyut için BEKLE'lere de küçük weight
        return s + Math.max(st.tier_score || 0, 10);
      }, 0);
      return { name: name, stocks: stocks, _size: totalScore };
    });
    sectors.sort(function(a, b){ return b._size - a._size; });

    // Konteyner boyutu — responsive
    var W = container.clientWidth || 1200;
    var H = Math.max(600, Math.min(900, W * 0.55));
    var SVG_NS = 'http://www.w3.org/2000/svg';

    var svg = document.createElementNS(SVG_NS, 'svg');
    svg.id = 'heatmap-svg';
    svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
    svg.setAttribute('width', W);
    svg.setAttribute('height', H);

    // Sektörleri squarify
    squarify(sectors, {x: 0, y: 0, w: W, h: H});

    sectors.forEach(function(sec){
      if (!sec.w || !sec.h) return;
      var g = document.createElementNS(SVG_NS, 'g');
      g.setAttribute('class', 'sector-group');

      // Sektör border — G16: daha belirgin ayırıcı
      var bg = document.createElementNS(SVG_NS, 'rect');
      bg.setAttribute('x', sec.x); bg.setAttribute('y', sec.y);
      bg.setAttribute('width', sec.w); bg.setAttribute('height', sec.h);
      bg.setAttribute('fill', '#0e0e12');
      bg.setAttribute('stroke', '#3c3c46');
      bg.setAttribute('stroke-width', '3');
      g.appendChild(bg);

      // Sektör başlığı header strip — G16: ayırıcı şerit + metin
      if (sec.w > 60 && sec.h > 30) {
        // Subtle header background
        var hdrH = 20;
        var hdr = document.createElementNS(SVG_NS, 'rect');
        hdr.setAttribute('x', sec.x + 2); hdr.setAttribute('y', sec.y + 2);
        hdr.setAttribute('width', sec.w - 4); hdr.setAttribute('height', hdrH);
        hdr.setAttribute('fill', 'rgba(60,60,72,0.5)');
        hdr.setAttribute('rx', '2'); hdr.setAttribute('ry', '2');
        g.appendChild(hdr);

        var title = document.createElementNS(SVG_NS, 'text');
        title.setAttribute('class', 'sector-title');
        title.setAttribute('x', sec.x + 6);
        title.setAttribute('y', sec.y + 14);
        title.textContent = sec.name.toUpperCase() + ' (' + sec.stocks.length + ')';
        g.appendChild(title);
      }

      // Hisseleri squarify (sektör içi, başlık + header strip alanı düş)
      var titleH = 24;  /* G16: header strip 20px + buffer */
      var inner = {
        x: sec.x + 2,
        y: sec.y + titleH,
        w: Math.max(0, sec.w - 4),
        h: Math.max(0, sec.h - titleH - 2)
      };

      var stocks = sec.stocks.slice();
      stocks.forEach(function(s){
        // Minimum boyut için BEKLE'lere de weight
        s._size = Math.max(s.tier_score || 0, 10);
      });
      stocks.sort(function(a, b){ return b._size - a._size; });
      squarify(stocks, inner);

      stocks.forEach(function(st){
        if (!st.w || !st.h || st.w < 1 || st.h < 1) return;
        var cell = document.createElementNS(SVG_NS, 'rect');
        cell.setAttribute('class', 'stock-cell');
        cell.setAttribute('x', st.x); cell.setAttribute('y', st.y);
        cell.setAttribute('width', st.w); cell.setAttribute('height', st.h);
        var cellFill = currentMode === 'piyasa' ? piyasaColor(st) : tierColor(st);
        var cellOp   = currentMode === 'piyasa' ? piyasaOpacity() : tierOpacity(st);
        cell.setAttribute('fill', cellFill);
        cell.setAttribute('opacity', cellOp);
        cell.setAttribute('stroke', '#0e0e12');
        cell.setAttribute('stroke-width', '1');
        cell.setAttribute('rx', '3');  /* G16: border-radius */
        cell.setAttribute('ry', '3');
        allCellRefs.push({rect: cell, item: st});
        cell.dataset.ticker = st.ticker;
        cell.addEventListener('click', function(){
          window.location.href = '/hisse/' + st.ticker;
        });
        cell.addEventListener('mouseenter', function(ev){ showTooltip(ev, st); });
        cell.addEventListener('mousemove', function(ev){ moveTooltip(ev); });
        cell.addEventListener('mouseleave', hideTooltip);
        g.appendChild(cell);

        // Ticker label — sadece yeterli alan varsa
        if (st.w > 38 && st.h > 22) {
          var fontSize = Math.min(Math.max(Math.floor(Math.min(st.w / 5, st.h / 2.2)), 9), 16);
          var label = document.createElementNS(SVG_NS, 'text');
          label.setAttribute('class', 'stock-cell-text');
          label.setAttribute('x', st.x + st.w / 2);
          label.setAttribute('y', st.y + st.h / 2);
          label.setAttribute('font-size', fontSize);
          label.textContent = st.ticker;
          g.appendChild(label);
        }
      });

      svg.appendChild(g);
    });

    container.appendChild(svg);

    // Freshness stamp
    var freshTxt = document.getElementById('freshness-text');
    if (freshTxt) {
      freshTxt.textContent = 'BIST ~15dk gecikmeli · Son güncelleme: ' + (data.updated_at || '—');
    }
  }

  function showTooltip(ev, st) {
    var tt = document.getElementById('heatmap-tooltip');
    if (!tt) return;
    var changeColor = (st.change_pct > 0) ? '#00e290' : (st.change_pct < 0 ? '#f85149' : '#909097');
    var changeStr = (st.change_pct == null) ? '—' :
      (st.change_pct > 0 ? '+' : '') + st.change_pct.toFixed(2) + '%';
    tt.innerHTML =
      '<div class="tt-ticker">' + st.ticker + '</div>' +
      '<div class="tt-name">' + (st.name || '') + '</div>' +
      '<div class="tt-row"><span class="tt-label">Sektör:</span><span>' + (st.sector || '—') + '</span></div>' +
      '<div class="tt-row"><span class="tt-label">Sinyal:</span><span>' + tierLabel(st) + '</span></div>' +
      '<div class="tt-row"><span class="tt-label">Skor:</span><span>' + (st.tier_score || 0) + '/100</span></div>' +
      '<div class="tt-row"><span class="tt-label">Fiyat:</span><span>' + (st.price || '—') + ' ₺</span></div>' +
      '<div class="tt-row"><span class="tt-label">Günlük:</span><span style="color:' + changeColor + '">' + changeStr + '</span></div>';
    tt.style.display = 'block';
    moveTooltip(ev);
  }

  function moveTooltip(ev) {
    var tt = document.getElementById('heatmap-tooltip');
    if (!tt) return;
    var x = ev.clientX + 14;
    var y = ev.clientY + 14;
    var rect = tt.getBoundingClientRect();
    if (x + rect.width > window.innerWidth - 10) x = ev.clientX - rect.width - 14;
    if (y + rect.height > window.innerHeight - 10) y = ev.clientY - rect.height - 14;
    tt.style.left = x + 'px';
    tt.style.top = y + 'px';
  }

  function hideTooltip() {
    var tt = document.getElementById('heatmap-tooltip');
    if (tt) tt.style.display = 'none';
  }

  // ── SPEC-021: Mode switch ─────────────────────────────────────────────────
  function switchMode(mode) {
    if (mode === currentMode) return;
    currentMode = mode;
    localStorage.setItem('bp_heatmap_mode', mode);
    history.replaceState(null, '', '?mode=' + mode);

    // Update cell colors in-place (no re-layout)
    allCellRefs.forEach(function(ref) {
      ref.rect.setAttribute('fill',    mode === 'piyasa' ? piyasaColor(ref.item) : tierColor(ref.item));
      ref.rect.setAttribute('opacity', mode === 'piyasa' ? piyasaOpacity() : tierOpacity(ref.item));
    });

    // Text color via body class
    document.body.classList.toggle('mode-piyasa', mode === 'piyasa');

    // Toggle button states
    document.querySelectorAll('.toggle-btn').forEach(function(btn) {
      btn.classList.toggle('active', btn.dataset.mode === mode);
    });

    // Title + subtitle + legends
    var title = document.getElementById('heatmap-title');
    var sub   = document.getElementById('heatmap-subtitle');
    if (title) title.textContent = mode === 'piyasa' ? 'BIST Piyasa Haritası' : 'BIST Sinyal Haritası';
    if (sub)   sub.textContent   = mode === 'piyasa'
      ? '215 hisse — günlük değişim renkleri · sektör bazlı treemap'
      : '215 hisse — sinyal tier renkleri · sektör bazlı treemap';

    var lSinyal  = document.getElementById('legendSinyal');
    var lPiyasa  = document.getElementById('legendPiyasa');
    if (lSinyal)  lSinyal.style.display  = mode === 'piyasa' ? 'none' : '';
    if (lPiyasa)  lPiyasa.style.display  = mode === 'piyasa' ? ''     : 'none';
  }

  function initToggle() {
    // Apply initial mode class
    document.body.classList.toggle('mode-piyasa', currentMode === 'piyasa');
    document.querySelectorAll('.toggle-btn').forEach(function(btn) {
      btn.classList.toggle('active', btn.dataset.mode === currentMode);
      btn.addEventListener('click', function() { switchMode(btn.dataset.mode); });
    });
    // Apply initial legend visibility
    var lSinyal = document.getElementById('legendSinyal');
    var lPiyasa = document.getElementById('legendPiyasa');
    if (lSinyal) lSinyal.style.display = currentMode === 'piyasa' ? 'none' : '';
    if (lPiyasa) lPiyasa.style.display = currentMode === 'piyasa' ? ''     : 'none';
    // Apply initial title/subtitle
    var title = document.getElementById('heatmap-title');
    var sub   = document.getElementById('heatmap-subtitle');
    if (currentMode === 'piyasa') {
      if (title) title.textContent = 'BIST Piyasa Haritası';
      if (sub)   sub.textContent   = '215 hisse — günlük değişim renkleri · sektör bazlı treemap';
    }
  }

  // ── Fetch + init ─────────────────────────────────────────────────────────
  function load() {
    fetch('/api/heatmap', {credentials: 'same-origin'})
      .then(function(r){ return r.json(); })
      .then(function(data){
        if (!data || !data.stocks || !data.stocks.length) {
          document.getElementById('heatmap-container').innerHTML =
            '<div style="text-align:center;padding:80px 20px;color:#909097">Veri henüz yüklenmedi. Sayfa otomatik yenilenecek…</div>';
          setTimeout(load, 5000);
          return;
        }
        render(data);
        if (!_toggleInited) { initToggle(); _toggleInited = true; }
      })
      .catch(function(err){
        console.error('Heatmap load error:', err);
        document.getElementById('heatmap-container').innerHTML =
          '<div style="text-align:center;padding:80px 20px;color:#f85149">Veri yüklenemedi. Lütfen sayfayı yenileyin.</div>';
      });
  }

  // Resize debounce
  var resizeTimer;
  window.addEventListener('resize', function(){
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(load, 250);
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', load);
  } else {
    load();
  }
})();
