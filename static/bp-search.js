/* ============================================================
   BorsaPusula Site Search v1.0 — self-contained module
   ------------------------------------------------------------
   • Auto-injects CSS + overlay HTML on first run
   • Exposes: window.bpOpenSearch(), window.bpCloseSearch()
   • Trigger: any element with class "header-search-btn" OR
              any element with onclick="bpOpenSearch()"
   • Keyboard: Cmd/Ctrl+K opens, Esc closes, ↑↓ Enter navigate
   • Data: /api/data → sessionStorage 5min cache
   • Idempotent: safe to load multiple times (no-op if mounted)
   ============================================================ */
(function(){
  'use strict';
  if (window.__bpSearchMounted) return;
  window.__bpSearchMounted = true;

  // ---- CSS (hardcoded hex so it works on any page) ----
  var CSS = ''
    + '.header-search-btn{display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;background:transparent;border:1px solid #2a2a2c;border-radius:6px;color:#c7c5cd;cursor:pointer;transition:all .15s;flex-shrink:0;padding:0;font-family:inherit}'
    + '.header-search-btn:hover{background:#1c1b1f;border-color:#46464d;color:#e5e1e4}'
    + '.bp-search-overlay{display:none;position:fixed;inset:0;z-index:300;background:rgba(0,0,0,0.65);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);align-items:flex-start;justify-content:center;padding-top:80px}'
    + '.bp-search-overlay.open{display:flex}'
    + '.bp-search-modal{width:min(560px,calc(100vw - 32px));background:#141416;border:1px solid #2a2a2c;border-radius:12px;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,0.6);max-height:calc(100vh - 120px);display:flex;flex-direction:column}'
    + '.bp-search-input-wrap{display:flex;align-items:center;gap:10px;padding:16px;border-bottom:1px solid #2a2a2c}'
    + '.bp-search-input-icon{width:18px;height:18px;color:#909097;flex-shrink:0}'
    + '#bpSearchInput{flex:1;background:none;border:none;outline:none;font-size:15px;color:#e5e1e4;font-family:Manrope,system-ui,sans-serif;min-width:0;padding:0;margin:0}'
    + '#bpSearchInput::placeholder{color:#909097}'
    + '.bp-search-close{background:#1c1b1f;border:1px solid #2a2a2c;color:#c7c5cd;width:28px;height:28px;border-radius:6px;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0;font-family:inherit;padding:0}'
    + '.bp-search-close:hover{background:#201f21;color:#e5e1e4}'
    + '.bp-search-results{flex:1;overflow-y:auto;padding:6px 6px 12px}'
    + '.bp-search-empty{padding:24px;text-align:center;color:#909097;font-size:13px}'
    + '.bp-search-section-title{font-family:"Space Grotesk",system-ui,sans-serif;font-size:10px;font-weight:700;color:#909097;text-transform:uppercase;letter-spacing:0.5px;padding:10px 12px 6px}'
    + '.bp-search-result{display:grid;grid-template-columns:64px 14px 1fr auto auto;align-items:center;gap:8px;padding:9px 12px;text-decoration:none;color:#e5e1e4;border-radius:8px;transition:background .12s;font-size:13px}'
    + '.bp-search-result:hover,.bp-search-result.bp-sel{background:#1c1b1f}'
    + '.bp-sr-tk{font-family:"Space Grotesk",system-ui,sans-serif;font-weight:700;color:#e5e1e4;font-size:13px}'
    + '.bp-sr-sig.bp-al{color:#00e290;font-weight:700}'
    + '.bp-sr-sig.bp-sat{color:#f85149;font-weight:700}'
    + '.bp-sr-sig.bp-bekle{color:#909097}'
    + '.bp-sr-name{color:#c7c5cd;font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}'
    + '.bp-sr-price{font-variant-numeric:tabular-nums;font-size:12px;color:#c7c5cd}'
    + '.bp-sr-chg{font-variant-numeric:tabular-nums;font-size:12px;font-weight:600;min-width:56px;text-align:right}'
    + '.bp-sr-chg.bp-pos{color:#00e290}.bp-sr-chg.bp-neg{color:#f85149}.bp-sr-chg.bp-neu{color:#909097}'
    + '.bp-search-topic{display:block;padding:9px 12px;text-decoration:none;color:#e5e1e4;border-radius:8px;font-size:13px;transition:background .12s}'
    + '.bp-search-topic:hover,.bp-search-topic.bp-sel{background:#1c1b1f}'
    + '@media (max-width:600px){.bp-search-overlay{padding-top:0;align-items:stretch}.bp-search-modal{width:100vw;height:100vh;max-height:100vh;border-radius:0;border:none}.bp-search-result{grid-template-columns:56px 14px 1fr auto}.bp-sr-price{display:none}}'
    /* ── Anti-CLS: reserve space for async-loaded sections ── */
    + '#gundemSec{min-height:230px}'
    + '#statsBar,.stats-bar{min-height:78px}'
    /* ── Mobile bottom-nav thumb-friendly: bigger inner + breathing room ── */
    + '@media (max-width:768px){.mbn-inner{height:72px !important;padding-bottom:8px !important}.mbn-item{padding-top:6px !important}body{padding-bottom:calc(72px + 8px + env(safe-area-inset-bottom)) !important}}'
    /* ── Trend Strip (dynamic ticker chips replacing static "Popüler") ── */
    + '.bp-trend-strip{display:flex;align-items:center;gap:6px;padding:7px 16px;background:rgba(14,14,18,0.85);border-bottom:1px solid #2a2a2c;overflow-x:auto;scrollbar-width:none;-ms-overflow-style:none;white-space:nowrap;position:relative;z-index:5;min-height:40px}'
    + '.bp-trend-strip::-webkit-scrollbar{display:none}'
    + '.bp-trend-label{flex-shrink:0;font-family:"Space Grotesk",system-ui,sans-serif;font-size:9px;font-weight:700;color:#5a5a62;text-transform:uppercase;letter-spacing:1.2px;margin-right:8px;padding:0;background:none;border:none;display:inline-flex;align-items:center;gap:5px}'
    + '.bp-trend-label::before{content:"";display:inline-block;width:14px;height:1px;background:#3a3a42}'
    + '.bp-trend-chip{flex-shrink:0;display:inline-flex;align-items:center;gap:5px;padding:4px 10px;border-radius:12px;font-size:11.5px;font-weight:600;text-decoration:none;transition:transform .12s,background .15s;font-family:Manrope,system-ui,sans-serif;font-variant-numeric:tabular-nums;background:rgba(28,27,31,0.7);border:1px solid #2a2a2c;color:#e5e1e4}'
    + '.bp-trend-chip:hover{background:#1c1b1f;transform:translateY(-1px)}'
    + '.bp-trend-chip .tc-tk{font-family:"Space Grotesk",system-ui,sans-serif;font-weight:700;color:#e5e1e4;font-size:11px}'
    + '.bp-trend-chip .tc-arrow{font-size:9px}'
    + '.bp-trend-chip .tc-chg{font-size:10.5px;font-weight:600}'
    + '.bp-trend-chip.up{border-color:rgba(0,226,144,0.32)}'
    + '.bp-trend-chip.up .tc-arrow,.bp-trend-chip.up .tc-chg{color:#00e290}'
    + '.bp-trend-chip.down{border-color:rgba(248,81,73,0.32)}'
    + '.bp-trend-chip.down .tc-arrow,.bp-trend-chip.down .tc-chg{color:#f85149}'
    + '@media (max-width:768px){.bp-trend-strip{padding:7px 12px}.bp-trend-label{display:none}}'
    /* ── Unified Logo (replaces .back-btn variants across pages) ── */
    + '.logo-link{display:inline-flex;align-items:center;text-decoration:none;flex-shrink:0;padding:0;margin:0;background:none;border:none}'
    + '.logo-link .bp-logo{display:block;width:260px;height:68px;flex-shrink:0}'
    + '@media (max-width:1024px){.logo-link .bp-logo{width:230px;height:60px}}'
    + '@media (max-width:768px){.logo-link .bp-logo{width:200px;height:52px}}'
    + '@media (max-width:420px){.logo-link .bp-logo{width:170px;height:44px}}'
    /* ── Header consistency: hide page-title/header-name from header so nav stays centered ── */
    + 'header h1.page-title,header h1.header-name,header .page-sub,header .header-sub{display:none !important}'
    /* ── Unified header dimensions: 60px tall, 12px 20px padding (force across all pages) ── */
    + 'header{padding:10px 20px !important;min-height:60px !important;max-height:60px !important;display:flex !important;align-items:center !important;gap:14px !important;box-sizing:border-box !important;transform:translateZ(0) !important}'
    + 'header > *{max-height:48px}'
    + 'header > .header-info,header > div:has(> h1.page-title),header > div:has(> h1.header-name),header > div:has(> .page-sub),header > div:has(> .header-sub){display:none !important}'
    + 'header div[style]:has(> h1.page-title),header div[style]:has(> h1.header-name){display:none !important}'
    /* ── Unified Nav (bp-main-nav) — v2.1: UPPERCASE, safe-center, scaled ── */
    + '.bp-main-nav{display:flex;align-items:center;justify-content:safe center;gap:5px;flex-wrap:nowrap;flex:1;min-width:0;overflow-x:auto;scrollbar-width:none;-ms-overflow-style:none}'
    + '.bp-main-nav::-webkit-scrollbar{display:none}'
    + '.bp-nav-item{display:inline-flex;align-items:center;gap:6px;padding:8px 13px;border-radius:8px;font-size:11px;font-weight:600;letter-spacing:0.6px;text-transform:uppercase;color:#c7c5cd;text-decoration:none;transition:background .18s ease,color .18s ease,box-shadow .18s ease;white-space:nowrap;font-family:"Space Grotesk",system-ui,sans-serif;background:none;border:none;cursor:pointer;line-height:1;flex-shrink:0}'
    + '.bp-nav-item svg{width:13px;height:13px;opacity:0.65;flex-shrink:0}'
    + '.bp-nav-item:hover{background:rgba(255,255,255,0.045);color:#e5e1e4}'
    + '.bp-nav-item:hover svg{opacity:1}'
    + '.bp-nav-item.active{background:rgba(0,226,144,0.12);color:#00e290;font-weight:700;box-shadow:inset 0 0 0 1px rgba(0,226,144,0.18)}'
    + '.bp-nav-item.active svg{opacity:1}'
    + '.bp-nav-more-wrap{position:relative;flex-shrink:0}'
    + '.bp-nav-chev{width:11px !important;height:11px !important;transition:transform .18s ease;opacity:0.6}'
    + '.bp-nav-more-btn[aria-expanded="true"] .bp-nav-chev{transform:rotate(180deg);opacity:1}'
    + '.bp-nav-more-btn[aria-expanded="true"]{background:rgba(184,195,255,0.12);color:#b8c3ff}'
    /* Dropdown rendered as fixed/portal to body to escape stacking context */
    + '.bp-nav-more-menu{display:none;position:fixed;min-width:220px;background:#1c1b1f;border:1px solid #46464d;border-radius:10px;padding:6px;box-shadow:0 14px 50px rgba(0,0,0,0.7),0 0 0 1px rgba(255,255,255,0.04);z-index:9999}'
    + '.bp-nav-more-menu.open{display:block;animation:bpNavMoreIn .15s ease}'
    + '@keyframes bpNavMoreIn{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:translateY(0)}}'
    + '.bp-nav-more-menu a{display:flex;align-items:center;gap:10px;padding:9px 12px;font-size:12px;font-weight:500;letter-spacing:0.3px;text-transform:uppercase;color:#e5e1e4;text-decoration:none;border-radius:6px;transition:background .12s;font-family:"Space Grotesk",system-ui,sans-serif}'
    + '.bp-nav-more-menu a:hover{background:#1c1b1f}'
    + '.bp-nav-more-menu a svg{width:14px;height:14px;opacity:0.7;flex-shrink:0}'
    + '.bp-nav-sep{height:1px;background:#2a2a2c;margin:5px 8px}'
    /* On wider screens: bump up padding/font slightly */
    + '@media (min-width:1500px){.bp-nav-item{padding:9px 16px;font-size:11.5px;letter-spacing:0.7px;gap:7px}.bp-main-nav{gap:6px}}'
    /* On tighter screens: shrink */
    + '@media (max-width:1100px){.bp-nav-item{padding:7px 10px;letter-spacing:0.4px;gap:4px}.bp-main-nav{gap:3px}}'
    + '@media (max-width:1000px){.bp-nav-item{padding:7px 8px;font-size:10.5px;gap:3px}}'
    + '@media (max-width:900px){.bp-main-nav{display:none}}'
    /* ── Header-right uniform actions: live time + refresh + search (all pages) ── */
    + '.bp-header-right{display:inline-flex;align-items:center;gap:6px;flex-shrink:0;margin-left:auto}'
    + '.bp-live-time{display:inline-flex;align-items:center;gap:5px;background:rgba(0,226,144,0.06);border:1px solid rgba(0,226,144,0.20);color:#00e290;font-size:11px;font-weight:700;padding:5px 9px;border-radius:6px;font-family:"Space Grotesk",system-ui,sans-serif;font-variant-numeric:tabular-nums;letter-spacing:0.3px;white-space:nowrap}'
    + '.bp-live-dot{width:6px;height:6px;border-radius:50%;background:#00e290;animation:bpLivePulse 2s infinite;flex-shrink:0}'
    + '@keyframes bpLivePulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:0.4;transform:scale(0.8)}}'
    + '.bp-refresh-btn{display:inline-flex;align-items:center;gap:5px;background:transparent;border:1px solid #2a2a2c;color:#c7c5cd;font-size:11px;font-weight:600;padding:5px 11px;border-radius:6px;cursor:pointer;transition:background .15s,border-color .15s;text-transform:uppercase;letter-spacing:0.4px;font-family:"Space Grotesk",system-ui,sans-serif;flex-shrink:0;line-height:1}'
    + '.bp-refresh-btn:hover{background:rgba(184,195,255,0.08);border-color:#46464d;color:#e5e1e4}'
    + '.bp-refresh-btn.spinning svg{animation:bpRefreshSpin 0.8s linear infinite}'
    + '@keyframes bpRefreshSpin{from{transform:rotate(0)}to{transform:rotate(360deg)}}'
    + '.bp-refresh-btn svg{width:12px;height:12px;flex-shrink:0}'
    + '@media (max-width:768px){.bp-live-time{font-size:10px;padding:4px 7px}.bp-live-time .bp-live-time-text{display:none}.bp-refresh-btn .bp-refresh-label{display:none}.bp-refresh-btn{padding:5px 8px}}'
    + '@media (max-width:480px){.bp-live-time{display:none}}';

  // Inject CSS
  if (!document.getElementById('bp-search-css')) {
    var style = document.createElement('style');
    style.id = 'bp-search-css';
    style.textContent = CSS;
    document.head.appendChild(style);
  }

  // ---- Data layer ----
  var _syms = null;
  var _sel = 0;

  function loadSyms() {
    if (_syms) return Promise.resolve(_syms);
    try {
      var c = sessionStorage.getItem('bp_search_cache_v1');
      var t = sessionStorage.getItem('bp_search_t_v1');
      if (c && t && Date.now() - parseInt(t, 10) < 300000) {
        _syms = JSON.parse(c);
        return Promise.resolve(_syms);
      }
    } catch(e) {}
    return fetch('/api/data', { cache: 'no-store' })
      .then(function(r){ return r.json(); })
      .then(function(d){
        _syms = (d.stocks || [])
          .filter(function(s){ return s.ticker && s.ticker !== 'XU030' && s.ticker !== 'XU100'; })
          .map(function(s){ return { t:s.ticker, n:s.name||'', sec:s.sector||'', sig:s.signal, p:s.price, c:s.change_pct }; });
        try {
          sessionStorage.setItem('bp_search_cache_v1', JSON.stringify(_syms));
          sessionStorage.setItem('bp_search_t_v1', Date.now().toString());
        } catch(e) {}
        return _syms;
      })
      .catch(function(){ return []; });
  }

  function escHtml(s){
    return String(s||'').replace(/[&<>"']/g, function(m){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m];
    });
  }

  function filter(q) {
    if (!_syms) return [];
    var Q = q.toLowerCase().trim();
    if (!Q) return [];
    var out = [];
    for (var i = 0; i < _syms.length; i++) {
      var s = _syms[i];
      var t = s.t.toLowerCase();
      var n = (s.n || '').toLowerCase();
      var score = 0;
      if (t === Q) score = 100;
      else if (t.indexOf(Q) === 0) score = 60;
      else if (n.indexOf(Q) === 0) score = 40;
      else if (t.indexOf(Q) >= 0) score = 25;
      else if (n.indexOf(Q) >= 0) score = 15;
      if (score) out.push({ s: s, score: score });
    }
    out.sort(function(a,b){ return b.score - a.score; });
    return out.slice(0, 10).map(function(x){ return x.s; });
  }

  var TOPICS = [
    { h:'/gucu-yuksek',       i:'⚡', t:'Güçlü Trend Hisseler' },
    { h:'/tarama',            i:'🔍', t:'Hisse Tarama' },
    { h:'/bilanco-takvimi',   i:'📅', t:'Bilanço Takvimi' },
    { h:'/sektor-harita',     i:'🗺️', t:'Sektör Haritası' },
    { h:'/sinyal-performans', i:'📈', t:'Sinyal Performansı' },
    { h:'/karsilastir',       i:'⚖️', t:'Hisse Karşılaştır' },
    { h:'/kripto',            i:'₿',  t:'Kripto Piyasaları' },
    { h:'/abd',               i:'🌍', t:'ABD Piyasaları' }
  ];

  function render(q) {
    var res = document.getElementById('bpSearchResults');
    if (!res) return;
    if (!q.trim()) {
      res.innerHTML = '<div class="bp-search-section-title">Popüler Konular</div>'
        + TOPICS.map(function(it, i){
            return '<a href="' + it.h + '" class="bp-search-topic ' + (i===0?'bp-sel':'') + '" data-idx="' + i + '"><span style="margin-right:8px">' + it.i + '</span>' + it.t + '</a>';
          }).join('');
      _sel = 0;
      return;
    }
    var m = filter(q);
    if (!m.length) {
      res.innerHTML = '<div class="bp-search-empty">Hiç eşleşme yok. Farklı bir kelime deneyin.</div>';
      _sel = -1;
      return;
    }
    var html = '<div class="bp-search-section-title">Hisseler</div>';
    m.forEach(function(s, i){
      var arr = s.sig === 'AL' ? '▲' : s.sig === 'SAT' ? '▼' : '●';
      var sigCls = s.sig === 'AL' ? 'bp-al' : s.sig === 'SAT' ? 'bp-sat' : 'bp-bekle';
      var c = (typeof s.c === 'number') ? s.c : null;
      var cCls = c == null ? 'bp-neu' : c > 0 ? 'bp-pos' : c < 0 ? 'bp-neg' : 'bp-neu';
      var cSign = c == null ? '—' : (c > 0 ? '+' : '') + c.toFixed(2) + '%';
      var priceStr = (typeof s.p === 'number' && s.p > 0) ? s.p.toLocaleString('tr-TR', {minimumFractionDigits:2, maximumFractionDigits:2}) + ' ₺' : '';
      html += '<a href="/hisse/' + escHtml(s.t) + '" class="bp-search-result ' + (i===0?'bp-sel':'') + '" data-idx="' + i + '">'
            + '<span class="bp-sr-tk">' + escHtml(s.t) + '</span>'
            + '<span class="bp-sr-sig ' + sigCls + '">' + arr + '</span>'
            + '<span class="bp-sr-name">' + escHtml(s.n) + '</span>'
            + '<span class="bp-sr-price">' + priceStr + '</span>'
            + '<span class="bp-sr-chg ' + cCls + '">' + cSign + '</span>'
            + '</a>';
    });
    res.innerHTML = html;
    _sel = 0;
  }

  function getItems() {
    return document.querySelectorAll('.bp-search-result, .bp-search-topic');
  }

  // ---- Overlay HTML injection (idempotent) ----
  function ensureOverlay() {
    if (document.getElementById('bpSearchOverlay')) return;
    var wrap = document.createElement('div');
    wrap.innerHTML = ''
      + '<div class="bp-search-overlay" id="bpSearchOverlay" aria-hidden="true">'
      +   '<div class="bp-search-modal" role="dialog" aria-label="Site içi arama">'
      +     '<div class="bp-search-input-wrap">'
      +       '<svg class="bp-search-input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>'
      +       '<input id="bpSearchInput" type="text" placeholder="Hisse, sektör veya konu ara…" autocomplete="off" spellcheck="false">'
      +       '<button class="bp-search-close" type="button" id="bpSearchClose" aria-label="Kapat">✕</button>'
      +     '</div>'
      +     '<div class="bp-search-results" id="bpSearchResults"></div>'
      +   '</div>'
      + '</div>';
    document.body.appendChild(wrap.firstElementChild);

    var ov = document.getElementById('bpSearchOverlay');
    if (ov) {
      ov.addEventListener('click', function(e){ if (e.target === ov) closeSearch(); });
    }
    var cl = document.getElementById('bpSearchClose');
    if (cl) cl.addEventListener('click', closeSearch);

    var inp = document.getElementById('bpSearchInput');
    if (inp) {
      var dt;
      inp.addEventListener('input', function(){
        clearTimeout(dt);
        dt = setTimeout(function(){ render(inp.value); }, 100);
      });
    }
  }

  function openSearch() {
    ensureOverlay();
    var ov = document.getElementById('bpSearchOverlay');
    if (!ov) return;
    ov.classList.add('open');
    ov.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    loadSyms().then(function(){
      var inp = document.getElementById('bpSearchInput');
      if (inp && !inp.value) render('');
    });
    setTimeout(function(){
      var i = document.getElementById('bpSearchInput');
      if (i) { i.focus(); i.select(); }
    }, 60);
    render('');
  }

  function closeSearch() {
    var ov = document.getElementById('bpSearchOverlay');
    if (!ov) return;
    ov.classList.remove('open');
    ov.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }

  window.bpOpenSearch = openSearch;
  window.bpCloseSearch = closeSearch;

  // ---- Keyboard shortcuts ----
  document.addEventListener('keydown', function(e){
    // Cmd/Ctrl+K → open
    if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')) {
      e.preventDefault();
      openSearch();
      return;
    }
    var ov = document.getElementById('bpSearchOverlay');
    if (!ov || !ov.classList.contains('open')) return;
    if (e.key === 'Escape') {
      e.preventDefault();
      closeSearch();
    } else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      var items = getItems();
      if (!items.length) return;
      items.forEach(function(it){ it.classList.remove('bp-sel'); });
      _sel += (e.key === 'ArrowDown' ? 1 : -1);
      if (_sel < 0) _sel = items.length - 1;
      if (_sel >= items.length) _sel = 0;
      items[_sel].classList.add('bp-sel');
      items[_sel].scrollIntoView({ block: 'nearest' });
    } else if (e.key === 'Enter') {
      var sel = document.querySelector('.bp-search-result.bp-sel, .bp-search-topic.bp-sel');
      if (sel && sel.href) {
        e.preventDefault();
        window.location.href = sel.href;
      }
    }
  });

  // ---- Nav: auto-activate current route + Daha dropdown ----
  function activateNav() {
    var path = location.pathname;
    var items = document.querySelectorAll('.bp-nav-item[data-route]');
    items.forEach(function(el){
      var route = el.getAttribute('data-route');
      if (route === '/' ? path === '/' : path.indexOf(route) === 0) {
        el.classList.add('active');
      }
    });
  }

  function positionMenu() {
    var menu = document.querySelector('.bp-nav-more-menu');
    var btn = document.querySelector('.bp-nav-more-btn');
    if (!menu || !btn) return;
    var br = btn.getBoundingClientRect();
    // Position below button, right-aligned with button's right edge
    menu.style.top = (br.bottom + 8) + 'px';
    menu.style.left = '';
    menu.style.right = (window.innerWidth - br.right) + 'px';
  }

  function bindNavMore() {
    // Portal: move menu to body (escapes stacking contexts/backdrop-filter clipping)
    var menu = document.querySelector('.bp-nav-more-menu');
    if (menu && menu.parentElement !== document.body) {
      document.body.appendChild(menu);
    }

    function closeMenu(){
      var m = document.querySelector('.bp-nav-more-menu');
      if (!m) return;
      m.classList.remove('open');
      var b = document.querySelector('.bp-nav-more-btn');
      if (b) b.setAttribute('aria-expanded', 'false');
    }

    document.addEventListener('click', function(e){
      var btn = e.target.closest && e.target.closest('.bp-nav-more-btn');
      var menu = document.querySelector('.bp-nav-more-menu');
      if (btn && menu) {
        e.preventDefault();
        var open = menu.classList.contains('open');
        if (!open) positionMenu();
        menu.classList.toggle('open', !open);
        btn.setAttribute('aria-expanded', !open);
        return;
      }
      // Outside click → close (must NOT include menu itself or its descendants)
      if (menu && menu.classList.contains('open')
          && !(e.target.closest && (e.target.closest('.bp-nav-more-wrap') || e.target.closest('.bp-nav-more-menu')))) {
        closeMenu();
      }
    });
    // Close on Esc
    document.addEventListener('keydown', function(e){
      if (e.key === 'Escape') {
        var menu = document.querySelector('.bp-nav-more-menu');
        if (menu && menu.classList.contains('open')) closeMenu();
      }
    });
    // Reposition on resize/scroll while open
    window.addEventListener('resize', function(){
      var m = document.querySelector('.bp-nav-more-menu');
      if (m && m.classList.contains('open')) positionMenu();
    });
    window.addEventListener('scroll', function(){
      var m = document.querySelector('.bp-nav-more-menu');
      if (m && m.classList.contains('open')) positionMenu();
    }, { passive: true });
  }

  // ---- Trend Strip removed (Strategy 1: Hareketliler widget anasayfada bunun yerini alıyor) ----
  function ensureTrendStrip() {
    // Sadece eski static "popüler" chip kalıntılarını ve eski trend strip'i temizle
    document.querySelectorAll('nav.quick-topics, .bp-trend-strip').forEach(function(el){ el.remove(); });
  }

  // ---- Header right actions: live time + refresh button (uniform across all pages) ----
  function ensureHeaderRight() {
    var hdr = document.querySelector('header');
    if (!hdr) return;

    // Check if header-right wrapper already exists from template
    var existingRight = hdr.querySelector('.header-right, .bp-header-right');

    // Find existing search button (it should be already in header from template inline CSS)
    var searchBtn = hdr.querySelector('.header-search-btn, .bp-search-button');

    // Build new uniform wrapper
    var wrapper = document.createElement('div');
    wrapper.className = 'bp-header-right';

    // Live time
    var liveTime = document.createElement('span');
    liveTime.className = 'bp-live-time';
    liveTime.id = 'bpLiveTime';
    liveTime.innerHTML = '<span class="bp-live-dot"></span><span class="bp-live-time-text" id="bpLiveTimeText">CANLI</span>';
    wrapper.appendChild(liveTime);

    // Move/append search button into wrapper
    if (searchBtn) {
      wrapper.appendChild(searchBtn);
    }

    // Refresh button
    var refreshBtn = document.createElement('button');
    refreshBtn.className = 'bp-refresh-btn';
    refreshBtn.id = 'bpRefreshBtn';
    refreshBtn.title = 'Sayfayı yenile';
    refreshBtn.setAttribute('aria-label', 'Yenile');
    refreshBtn.onclick = function() { window.bpSmartRefresh(); };
    refreshBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">' +
      '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/>' +
      '<path d="M21 3v5h-5"/>' +
      '<path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/>' +
      '<path d="M8 16H3v5"/>' +
      '</svg><span class="bp-refresh-label">Yenile</span>';
    wrapper.appendChild(refreshBtn);

    // Replace existing or append
    if (existingRight) {
      existingRight.parentNode.replaceChild(wrapper, existingRight);
    } else {
      hdr.appendChild(wrapper);
    }

    // Tick live time every second
    var tickEl = document.getElementById('bpLiveTimeText');
    function tick() {
      var d = new Date();
      var hh = String(d.getHours()).padStart(2, '0');
      var mm = String(d.getMinutes()).padStart(2, '0');
      var ss = String(d.getSeconds()).padStart(2, '0');
      if (tickEl) tickEl.textContent = hh + ':' + mm + ':' + ss;
    }
    tick();
    setInterval(tick, 1000);
  }

  // Smart refresh — page-specific manualRefresh() if exists, else location.reload()
  window.bpSmartRefresh = function() {
    var btn = document.getElementById('bpRefreshBtn');
    if (btn) btn.classList.add('spinning');
    if (typeof window.manualRefresh === 'function') {
      try { window.manualRefresh(); } catch(e) { location.reload(); }
      setTimeout(function(){ if (btn) btn.classList.remove('spinning'); }, 1500);
    } else {
      location.reload();
    }
  };

  // ---- Frontend error tracking — stealth bug detection ----
  function reportClientError(payload) {
    try {
      navigator.sendBeacon
        ? navigator.sendBeacon('/api/log-error', JSON.stringify(payload))
        : fetch('/api/log-error', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify(payload),
            keepalive: true
          }).catch(function(){});
    } catch(_) {}
  }

  if (typeof window.__bpErrorHooked === 'undefined') {
    window.__bpErrorHooked = true;
    window.addEventListener('error', function(e) {
      if (!e || !e.message) return;
      // GA / 3rd-party noise filter
      var msg = String(e.message);
      if (msg.includes('Script error') || msg.includes('region1.google-analytics')) return;
      reportClientError({
        msg:   msg.slice(0, 500),
        src:   (e.filename || '').slice(-200),
        line:  e.lineno,
        col:   e.colno,
        page:  location.pathname,
        stack: (e.error && e.error.stack || '').slice(0, 1000)
      });
    });
    window.addEventListener('unhandledrejection', function(e) {
      var reason = e.reason || {};
      var msg = String(reason.message || reason || 'Unhandled promise rejection');
      if (msg.includes('region1.google-analytics')) return;
      reportClientError({
        msg:   ('PromiseRejection: ' + msg).slice(0, 500),
        page:  location.pathname,
        stack: (reason.stack || '').slice(0, 1000)
      });
    });
  }

  // ---- Subscribe state: kullanıcı tanı + UI personalize ----
  function readBpSubCookie() {
    var m = document.cookie.match(/(?:^|;\s*)bp_sub=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : null;
  }

  function getCachedUser() {
    try {
      var raw = localStorage.getItem('bp_sub_user');
      if (!raw) return null;
      var u = JSON.parse(raw);
      // 7 gün cache (sonra refresh)
      if (Date.now() - (u.cachedAt || 0) > 7 * 86400000) return null;
      return u;
    } catch(_) { return null; }
  }

  function saveUserCache(user) {
    try {
      localStorage.setItem('bp_sub_user', JSON.stringify(Object.assign({}, user, { cachedAt: Date.now() })));
    } catch(_) {}
  }

  function clearUserCache() {
    try { localStorage.removeItem('bp_sub_user'); } catch(_) {}
  }

  function applyKnownUserUI(user) {
    if (!user || !user.subscribed) return;

    // 1) Subscribe bar'ı gizle (zaten abone)
    var bar = document.getElementById('subscribeBar');
    if (bar && !bar.dataset.bpUserApplied) {
      bar.dataset.bpUserApplied = '1';
      // SPEC-009 Aksiyon 1 ek: "Hoş geldin abonelik aktif" üst banner KALDIRILDI —
      // alt premium CTA bağlamsal mesajı (B durumu) zaten "Aboneliğin aktif" diyor,
      // çift banner aynı bilgiyi tekrarlıyordu. Profil eksikse yalnız CTA kalır.
      if (user.profile_done) {
        bar.style.display = 'none';
      } else {
        bar.innerHTML =
          '<a href="/profil?t=' + encodeURIComponent(user.token || readBpSubCookie() || '') + '" style="color:#b8c3ff;font-size:12px;text-decoration:none;border:1px solid rgba(184,195,255,0.3);padding:5px 11px;border-radius:6px;font-weight:600;margin-left:auto;flex-shrink:0">Profili Tamamla →</a>';
      }
    }

    // 2) Sub-toast popup'ı kapat (abone ise gösterme)
    var toast = document.getElementById('subToast');
    if (toast) toast.style.display = 'none';
    try { localStorage.setItem('bp_sub_dismissed_v2', String(Date.now())); } catch(_) {}
  }

  function recognizeUser() {
    var cached = getCachedUser();
    if (cached && cached.subscribed) {
      applyKnownUserUI(cached);
    }
    // Cookie/token varsa server'dan refresh
    var t = readBpSubCookie();
    if (!t) return;
    fetch('/api/me?cb=' + Date.now(), { credentials: 'include' })
      .then(function(r){ return r.json(); })
      .then(function(d){
        if (d && d.ok && d.subscribed) {
          d.token = t;
          saveUserCache(d);
          applyKnownUserUI(d);
        } else {
          clearUserCache();
        }
      })
      .catch(function(){});
  }

  // Public API: subscribe success'te çağrılır
  window.bpRecordSubscribe = function(payload) {
    if (!payload || !payload.token) return;
    var user = {
      subscribed: true,
      email: payload.email,
      name: payload.name || '',
      first_name: payload.name ? payload.name.split(' ')[0] : '',
      token: payload.token,
      profile_done: false,
    };
    saveUserCache(user);
    // Cookie zaten server tarafından set edildi (Set-Cookie header)
    setTimeout(function(){ applyKnownUserUI(user); }, 200);
  };


  // ── bpStartMacroTicker — KALICI çözüm, JS RAF tabanlı constant pixel-per-second
  // Tüm sayfalarda aynı hızı garanti eder (CSS animation duration hesabı kullanma!)
  window.bpStartMacroTicker = function(opts) {
    opts = opts || {};
    var pps = opts.pps || 55;          // pixels-per-second (sabit)
    var track = opts.track || document.getElementById('macroTrack');
    if (!track) return;
    if (track._bpTickerStarted) return;
    track._bpTickerStarted = true;

    // CSS animasyonunu kapat (override)
    track.style.animation = 'none';
    track.style.willChange = 'transform';

    var offset = 0, last = 0, paused = false;
    track.addEventListener('mouseenter', function(){ paused = true; });
    track.addEventListener('mouseleave', function(){ paused = false; });

    function step(now) {
      if (last && !paused && !document.hidden) {
        var dt = (now - last) / 1000;       // saniye
        if (dt > 0.1) dt = 0.1;             // tab değiştirme jump'ını önle
        offset += pps * dt;
        var half = track.scrollWidth / 2;
        if (half > 0 && offset >= half) offset -= half;
        track.style.transform = 'translateX(' + (-offset).toFixed(1) + 'px)';
      }
      last = now;
      requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  };


  // ── View Transitions API + perceived performance polish ──
  function bpEnableTransitions() {
    // 1. CSS injection: cross-fade
    if (!document.getElementById('bp-vt-css')) {
      const s = document.createElement('style');
      s.id = 'bp-vt-css';
      s.textContent = `
        @view-transition { navigation: auto; }
        ::view-transition-old(root), ::view-transition-new(root) { animation-duration: .18s; }
        @keyframes bp-fade-in  { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
        ::view-transition-new(root) { animation: bp-fade-in .22s ease-out; }
        a[href^="/"] { -webkit-tap-highlight-color: transparent; }
      `;
      document.head.appendChild(s);
    }
    // 2. Pre-fetch on hover (instant.page-style, only same-origin)
    let _prefetched = new Set();
    document.addEventListener('mouseover', function(e) {
      const a = e.target.closest('a[href]');
      if (!a) return;
      const href = a.href;
      if (!href || _prefetched.has(href)) return;
      const url = new URL(href, location.href);
      if (url.origin !== location.origin) return;
      if (a.hasAttribute('download') || a.target === '_blank') return;
      _prefetched.add(href);
      const link = document.createElement('link');
      link.rel = 'prefetch';
      link.href = href;
      document.head.appendChild(link);
    }, { passive: true });
  }
  bpEnableTransitions();

  // ---- Init: ensure overlay on DOM ready (so Cmd+K works even before button click) ----
  function init() {
    ensureOverlay();
    activateNav();
    bindNavMore();
    ensureTrendStrip();
    ensureHeaderRight();
    recognizeUser();
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
