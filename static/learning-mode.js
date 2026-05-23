/* SPEC-015 Öğrenme Modu v1 — SENECA Öneri 1 (Stock Unlock "Learn Mode")
 * Açık iken: sayfada .jargon-term span'lerinin yanına "?" butonu enjekte edilir.
 * Tıklanınca popover ile glossary tanımı gösterilir.
 * Kapalı iken: butonlar görünmez. Mevcut layout/UX değişmez.
 * Durum localStorage'da saklanır.
 */
(function () {
  'use strict';

  var GLOSSARY = {
    'adx': 'Trend gücü göstergesi (0–100). 25 üstü güçlü trend demek, 20 altı zayıf/yatay piyasa.',
    'rsi': 'Göreceli Güç Endeksi (0–100). 70 üstü aşırı alım, 30 altı aşırı satım bölgesi sinyali verir.',
    'ema12': 'Üstel hareketli ortalama (12 gün). Kısa vadeli trend yönünü gösterir.',
    'ema99': 'Üstel hareketli ortalama (99 gün). Uzun vadeli trend yönünü gösterir.',
    'ema': 'Üstel hareketli ortalama — son verilere daha çok ağırlık verir. EMA12 kısa, EMA99 uzun vadeyi temsil eder.',
    'supertrend': 'Trend yönü ve dinamik stop seviyesi veren indikatör. Renk değiştirdiğinde sinyal döner.',
    'di+': 'Pozitif yön göstergesi — yukarı yönlü hareketin gücü.',
    'di-': 'Negatif yön göstergesi — aşağı yönlü hareketin gücü. DI+ üstündeyse trend aşağı.',
    'stop loss': 'Pozisyondan çıkış yapılacak fiyat seviyesi. Risk yönetiminin temel taşı.',
    'stop bölgesi': 'Sinyalin geçersiz sayılacağı, pozisyon çıkışına işaret eden fiyat aralığı.',
    'tier_score': 'Sinyal kalite puanı (0–100). Bronz/Gümüş/Altın sınıflandırması bu skora göre yapılır.',
    'kovalama': 'Fiyat sinyal başlangıcına göre belirgin yükselmişken alım yapma riski. Genelde geri çekilme beklemek daha güvenli.',
    'r/r': 'Risk/Ödül oranı — potansiyel kazanç ÷ kabul edilen risk. 1:2 ve üstü genellikle anlamlı bulunur.',
    'rr_ratio': 'Risk/Ödül oranı — pozisyondan potansiyel kazanç ile stop\'a uzaklığın oranı.'
  };

  var STORAGE_KEY = 'bp_learning_mode';
  var STATE = (function () {
    try { return localStorage.getItem(STORAGE_KEY) === '1'; } catch (e) { return false; }
  })();

  function persistState(on) {
    try { localStorage.setItem(STORAGE_KEY, on ? '1' : '0'); } catch (e) { }
  }

  function ensureStyles() {
    if (document.getElementById('bp-lm-style')) return;
    var css =
      '.bp-lm-btn{display:none;margin-left:4px;width:16px;height:16px;line-height:14px;text-align:center;' +
      'border:1px solid rgba(184,195,255,.45);border-radius:50%;background:rgba(184,195,255,.10);' +
      'color:#b8c3ff;font-size:10px;font-weight:700;cursor:help;vertical-align:baseline;padding:0;font-family:inherit}' +
      '.bp-lm-btn:hover{background:rgba(184,195,255,.25)}' +
      'body.learning-on .bp-lm-btn{display:inline-block}' +
      '.bp-lm-pop{position:absolute;z-index:9999;max-width:280px;background:#1c1b1f;border:1px solid #2a2a2c;' +
      'border-radius:8px;padding:10px 12px;font-size:12px;line-height:1.55;color:#e5e1e4;' +
      'box-shadow:0 6px 24px rgba(0,0,0,.5)}' +
      '.bp-lm-pop b{color:#b8c3ff;display:block;margin-bottom:4px;font-size:11px;text-transform:uppercase;letter-spacing:.6px}' +
      '.bp-lm-toggle{display:inline-flex;align-items:center;gap:6px;background:transparent;border:1px solid #2a2a2c;' +
      'color:#c7c5cd;font-size:11px;padding:5px 10px;border-radius:6px;cursor:pointer;font-family:inherit;white-space:nowrap}' +
      '.bp-lm-toggle:hover{border-color:#b8c3ff;color:#e5e1e4}' +
      '.bp-lm-toggle .bp-lm-dot{width:7px;height:7px;border-radius:50%;background:#6b7280;display:inline-block}' +
      'body.learning-on .bp-lm-toggle .bp-lm-dot{background:#00e290}';
    var s = document.createElement('style');
    s.id = 'bp-lm-style';
    s.textContent = css;
    document.head.appendChild(s);
  }

  var openPop = null;

  function closePop() {
    if (openPop) { openPop.remove(); openPop = null; }
  }

  function showPop(anchor, term, def) {
    closePop();
    var pop = document.createElement('div');
    pop.className = 'bp-lm-pop';
    pop.innerHTML = '<b>' + term + '</b>' + def;
    document.body.appendChild(pop);
    var r = anchor.getBoundingClientRect();
    var top = window.scrollY + r.bottom + 6;
    var left = window.scrollX + r.left;
    if (left + 280 > window.innerWidth - 8) left = window.innerWidth - 288;
    pop.style.top = top + 'px';
    pop.style.left = Math.max(8, left) + 'px';
    openPop = pop;
    setTimeout(function () {
      document.addEventListener('click', onceClose, true);
    }, 0);
  }

  function onceClose(e) {
    if (openPop && !openPop.contains(e.target) && !(e.target.classList && e.target.classList.contains('bp-lm-btn'))) {
      closePop();
      document.removeEventListener('click', onceClose, true);
    }
  }

  function injectHints() {
    var nodes = document.querySelectorAll('.jargon-term');
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      if (el.dataset.lmInjected === '1') continue;
      el.dataset.lmInjected = '1';
      var term = (el.dataset.term || el.textContent || '').trim().toLowerCase();
      var def = GLOSSARY[term];
      if (!def) continue;
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'bp-lm-btn';
      btn.setAttribute('aria-label', term + ' tanımı');
      btn.title = term + ' — Öğrenme Modu açıklaması';
      btn.textContent = '?';
      btn.addEventListener('click', function (t, d) {
        return function (ev) {
          ev.stopPropagation();
          showPop(this, t, d);
        };
      }(term, def));
      el.appendChild(btn);
    }
  }

  function applyBody() {
    if (STATE) document.body.classList.add('learning-on');
    else document.body.classList.remove('learning-on');
  }

  function toggle() {
    STATE = !STATE;
    persistState(STATE);
    applyBody();
    closePop();
    var btns = document.querySelectorAll('.bp-lm-toggle');
    for (var i = 0; i < btns.length; i++) {
      btns[i].setAttribute('aria-pressed', STATE ? 'true' : 'false');
    }
  }

  function createToggleButton() {
    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'bp-lm-toggle';
    b.setAttribute('aria-label', 'Öğrenme Modu');
    b.setAttribute('aria-pressed', STATE ? 'true' : 'false');
    b.title = 'Öğrenme Modu — teknik terimlerin yanında ? açıklaması';
    b.innerHTML = '<span class="bp-lm-dot"></span>📚 Öğrenme Modu';
    b.addEventListener('click', toggle);
    return b;
  }

  function mountToggle() {
    if (document.querySelector('.bp-lm-toggle')) return;
    // Header'da arama butonunun yanına eklemeyi dene
    var anchor = document.querySelector('.header-search-btn');
    if (anchor && anchor.parentNode) {
      anchor.parentNode.insertBefore(createToggleButton(), anchor);
      return;
    }
    // Yoksa header sonuna
    var header = document.querySelector('header');
    if (header) header.appendChild(createToggleButton());
  }

  function init() {
    ensureStyles();
    mountToggle();
    injectHints();
    applyBody();
    // Geç eklenen içerik (JS render) için observer
    var mo = new MutationObserver(function () { injectHints(); });
    mo.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Global API
  window.bpLearningMode = { toggle: toggle, get state() { return STATE; } };
})();
