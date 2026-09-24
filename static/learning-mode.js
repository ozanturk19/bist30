/* SPEC-015 Öğrenme Modu v1 — SENECA Öneri 1 (Stock Unlock "Learn Mode")
 * Açık iken: sayfada .jargon-term span'lerinin yanına "?" butonu enjekte edilir.
 * Tıklanınca popover ile glossary tanımı gösterilir.
 * Kapalı iken: butonlar görünmez. Mevcut layout/UX değişmez.
 * Durum localStorage'da saklanır.
 */
(function () {
  'use strict';

  var GLOSSARY = {
    'adx': 'Trend gücü göstergesi (0–100). 25 üstü güçlü trend demek, 18 altı zayıf/yatay piyasa, arası orta güçte.',
    /* K-CH (22.09): bu tanim "45-60 ideal giris penceresi"ni KOSULSUZ yaziyordu.
       Urun K-BS/CPO-1745'ten beri o adi YALNIZ Guclu Trend sinyalinde basiyor
       (app.py:116, bp-format.js:396, metodoloji.html:145). Canli olcum 22.09:
       RSI 45-60 bandinda 46 hisse var, 45'i Guclu Trend DEGIL -- yani Ogrenme
       Modu'nu acan kullanici ekranda "Notr Bolge" yazarken sozlukten "ideal
       giris penceresi" okuyordu. Vaat iceren ad, onu doguran kosulla yazilir. */
    'rsi': 'Göreceli Güç Endeksi (0–100). 30 altı aşırı satım, 30-45 dip toparlanması, 45-60 Güçlü Trend sinyalinde Sağlıklı Momentum — diğer tüm sinyallerde Nötr Bölge, 60-70 trend güçleniyor, 70-80 dikkatli, 80 üstü aşırı alım.',
    'ema12': 'Üstel hareketli ortalama (12 gün). Kısa vadeli trend yönünü gösterir.',
    'ema99': 'Üstel hareketli ortalama (99 gün). Uzun vadeli trend yönünü gösterir.',
    'ema': 'Üstel hareketli ortalama — son verilere daha çok ağırlık verir. EMA12 kısa, EMA99 uzun vadeyi temsil eder.',
    'supertrend': 'Trend yönünü ve trend dönüş seviyesini veren indikatör. Renk değiştirdiğinde sinyal döner.',
    'di+': 'Pozitif yön göstergesi — yukarı yönlü hareketin gücü.',
    'di-': 'Negatif yön göstergesi — aşağı yönlü hareketin gücü. DI+ üstündeyse trend aşağı.',
    /* K-CH (22.09): 'tier_score' anahtari SILINDI -- K-CA'daki 'rr_ratio' ile ayni
       sinif (sitede `data-term="tier_score"` YOK, hicbir element ulasamiyordu) ama
       tanimi ayrica UC kanon ihlali tasiyordu: (1) "Premium" 22.08'de emekli edildi
       ve bu, urunun TUM yayimlanan metninde kalan TEK canli ornegiydi (sablonlardaki
       isabetlerin hepsi yorum); (2) "Plus" diye bir katman hic olmadi -- kanon iki
       katman: Guclu Sinyal / Standart (hisse.html:634); (3) "Sinyal kalite puani"
       skorun UCUNCU adiydi, kanon "Teknik Guc Skoru" (metodoloji.html:215) ve bu
       dosyanin kendi 'sinyal' tanimi zaten dogru adi kullaniyor. `tier_score` alani
       app.py:1563'e gore de emekli (AUDIT-004 yerine gecti). */
    'kovalama': 'Fiyat sinyal başlangıcına göre belirgin yükselmişken alım yapma riski. Genelde geri çekilme beklemek daha güvenli.',
    /* K-CA: `data-term="sinyal"` sitedeki EN YAYGIN jargon-linki (bp-vocab.js
       her sinyal cipini bununla sariyor) ama sozlukte karsiligi YOKTU -- yani
       Ogrenme Modu acikken bu terimde "?" dugmesi HIC cikmiyordu. Ustelik
       /metodoloji'nin "Karistirilmamasi Gerekenler" bolumu tam da bu terimi
       aciklamak icin yazilmis. Tanim o bolumun kanonuyla birebir. */
    'sinyal': 'Sinyalin YÖNÜ — yalnızca Güçlü Trend, Trend Bozuldu ya da Yatay olur; sayı değildir. Gücü/kalitesi ayrı anılır: Teknik Güç Skoru ve BorsaPusula Skoru.'
  };

  var STORAGE_KEY = 'bp_learning_mode';
  var STATE = (function () {
    try { return localStorage.getItem(STORAGE_KEY) === '1'; } catch (e) { return false; }
  })();

  function persistState(on) {
    try { localStorage.setItem(STORAGE_KEY, on ? '1' : '0'); } catch (e) { /* best-effort onbellek yazimi (private tarama/quota hata verebilir) */ }
  }

  function ensureStyles() {
    if (document.getElementById('bp-lm-style')) return;
    /* K-DH (22.09): bu blok 11 HAM HEX tasiyordu (js-palette ratchet'inde
       muaf duruyordu, tavan degil SIFIR kurali geregi kapatildi). Hepsi
       tokens.css'te zaten tanimli; ayrica "acik" noktasi AL yesiliydi --
       o renk urunde "Guclu Trend / AL" ANLAMI tasir (K-CZ), bir ozelligin
       acik olmasini anlatamaz. Nokta artik marka aksani. */
    var css =
      '.bp-lm-btn{display:none;margin-left:4px;width:16px;height:16px;line-height:14px;text-align:center;' +
      'border:1px solid rgba(var(--bp-brand-rgb),.45);border-radius:50%;background:rgba(var(--bp-brand-rgb),.10);' +
      'color:var(--bp-brand);font-size:10px;font-weight:700;cursor:help;vertical-align:baseline;padding:0;font-family:inherit}' +
      '.bp-lm-btn:hover{background:rgba(var(--bp-brand-rgb),.25)}' +
      'body.learning-on .bp-lm-btn{display:inline-block}' +
      '.bp-lm-pop{position:absolute;z-index:var(--bp-z-toast);max-width:280px;background:var(--bp-surface2);' +
      'border:1px solid var(--bp-border);' +
      'border-radius:8px;padding:10px 12px;font-size:12px;line-height:1.55;color:var(--bp-text);' +
      'box-shadow:0 6px 24px rgba(0,0,0,.5)}' +
      '.bp-lm-pop b{color:var(--bp-brand);display:block;margin-bottom:4px;font-size:11px;text-transform:uppercase;letter-spacing:.6px}' +
      '.bp-lm-toggle{display:inline-flex;align-items:center;gap:6px;background:transparent;border:1px solid var(--bp-ctl-border);' +
      'color:var(--bp-text2);font-size:11px;padding:5px 10px;border-radius:6px;cursor:pointer;font-family:inherit;white-space:nowrap}' +
      '.bp-lm-toggle:hover{border-color:var(--bp-brand);color:var(--bp-text)}' +
      '.bp-lm-toggle .bp-lm-dot{width:7px;height:7px;border-radius:50%;background:var(--bp-text3);display:inline-block}' +
      'body.learning-on .bp-lm-toggle .bp-lm-dot{background:var(--bp-brand)}' +
      /* K-DH: dar ekranda kontrol MOBIL MENU SAYFASINA tasinir.
         Eskiden yalniz `header .bp-lm-toggle{display:none}` vardi ve baska
         hicbir yerde kontrol YOKTU -- Ogrenme Modu telefonda hic
         acilamiyordu (urunun trafigi agirlikli mobil). Basligi daraltip
         yerinde birakmak DA calismiyor: 320px'te olculdu, baslik sagi
         (arama + yenile) 300px'te bitiyor, 43px'lik cip `bp-refresh-btn`i
         ekran disina itiyordu. Bu yuzden kontrol "Menu" sayfasindaki
         "Daha" izgarasina, sitenin kendi `.mbn-sheet-item` kartiyla ayni
         dille ekleniyor (mountSheetToggle). */
      '@media (max-width:600px){header .bp-lm-toggle{display:none}}' +
      /* Sayfadaki (sheet) varyant: temel .bp-lm-toggle kurallarini ezer,
         gorunumu sitenin kendi menu kartiyla ayni olur. */
      '.bp-lm-toggle.bp-lm-sheet{display:flex;flex-direction:column;justify-content:center;' +
      'gap:7px;background:var(--bp-surface2);border:1px solid var(--bp-border);' +
      'border-radius:var(--bp-radius-lg);color:var(--bp-text);font-size:var(--bp-text-xs);' +
      'font-weight:600;padding:14px 6px;min-height:70px;white-space:normal;text-align:center;line-height:1.3}' +
      '.bp-lm-toggle.bp-lm-sheet:hover{border-color:var(--bp-border);color:var(--bp-text)}' +
      'body.learning-on .bp-lm-toggle.bp-lm-sheet{border-color:rgba(var(--bp-brand-rgb),.55)}' +
      '.bp-lm-toggle.bp-lm-sheet .bp-lm-ico{font-size:20px;line-height:1}' +
      '.bp-lm-toggle.bp-lm-sheet .bp-lm-label{display:block}';
    var s = document.createElement('style');
    s.id = 'bp-lm-style';
    s.textContent = css;
    document.head.appendChild(s);
  }

  var openPop = null;
  var openPopOwner = null;

  function closePop() {
    if (openPop) { openPop.remove(); openPop = null; }
    if (openPopOwner) {
      openPopOwner.setAttribute('aria-expanded', 'false');
      /* K-AJ (21.09): showPop() anchor'a aria-controls="<id>-pop" yaziyordu ama
         kapanista SILMIYORDU — popup DOM'dan kalkiyor, oznitelik kaliyor. Sonuc:
         bir kez acilip kapanmis her "?" dugmesi, HICBIR ZAMAN cozulmeyen bir
         IDREF tasiyor (canli olcum: acik=1 cozulen / kapali=1 cozulmeyen).
         Kirik IDREF sessizdir: hata yok, konsol yok, gorsel fark yok. */
      openPopOwner.removeAttribute('aria-controls');
      openPopOwner = null;
    }
    document.removeEventListener('click', onceClose, true);
    document.removeEventListener('keydown', onKeydownClose, true);
  }

  function onKeydownClose(e) {
    if (e.key === 'Escape' || e.keyCode === 27) {
      closePop();
    }
  }

  function showPop(anchor, term, def) {
    closePop();
    var pop = document.createElement('div');
    pop.className = 'bp-lm-pop';
    pop.setAttribute('role', 'tooltip');
    if (anchor.id) {
      pop.id = anchor.id + '-pop';
      anchor.setAttribute('aria-controls', pop.id);
    }
    pop.innerHTML = '<b>' + term + '</b>' + def;
    document.body.appendChild(pop);
    var r = anchor.getBoundingClientRect();
    var top = window.scrollY + r.bottom + 6;
    var left = window.scrollX + r.left;
    if (left + 280 > window.innerWidth - 8) left = window.innerWidth - 288;
    pop.style.top = top + 'px';
    pop.style.left = Math.max(8, left) + 'px';
    openPop = pop;
    openPopOwner = anchor;
    anchor.setAttribute('aria-expanded', 'true');
    setTimeout(function () {
      document.addEventListener('click', onceClose, true);
      document.addEventListener('keydown', onKeydownClose, true);
    }, 0);
  }

  function onceClose(e) {
    if (openPop && !openPop.contains(e.target) && !(e.target.classList && e.target.classList.contains('bp-lm-btn'))) {
      closePop();
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
      btn.id = 'bp-lm-btn-' + i;
      btn.setAttribute('aria-label', term + ' tanımı');
      btn.setAttribute('aria-haspopup', 'true');
      btn.setAttribute('aria-expanded', 'false');
      btn.title = term + ' — Öğrenme Modu açıklaması';
      btn.textContent = '?';
      btn.addEventListener('click', function (t, d) {
        return function (ev) {
          ev.preventDefault();
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

  function createToggleButton(variant) {
    var b = document.createElement('button');
    b.type = 'button';
    b.className = variant === 'sheet' ? 'bp-lm-toggle bp-lm-sheet' : 'bp-lm-toggle';
    b.setAttribute('aria-label', 'Öğrenme Modu');
    b.setAttribute('aria-pressed', STATE ? 'true' : 'false');
    b.title = 'Öğrenme Modu — teknik terimlerin yanında ? açıklaması';
    /* K-DH: ikon ve gorunur metin ayri span'lerde -- sayfadaki (sheet)
       varyant ikonu buyutup metni alt satira alabiliyor. Eriselebilir ad
       her iki varyantta da `aria-label`dan gelir (ikon tek basina ad
       DEGILDIR); durum noktasi dekoratiftir, rengi tek basina anlam
       tasimaz (a32bfdc dersi) -- `aria-pressed` durumu bildirir. */
    b.innerHTML = '<span class="bp-lm-dot"></span><span class="bp-lm-ico" aria-hidden="true">📚</span>'
                + '<span class="bp-lm-label"> Öğrenme Modu</span>';
    b.addEventListener('click', toggle);
    return b;
  }

  function mountToggle() {
    /* K-DH: eskiden tek bir `if (querySelector('.bp-lm-toggle')) return;`
       vardi; iki varyant olunca bu erken cikis ikincisini de engellerdi. */
    if (!document.querySelector('.bp-lm-toggle:not(.bp-lm-sheet)')) {
      // Header'da arama butonunun yanına eklemeyi dene
      var anchor = document.querySelector('.header-search-btn');
      if (anchor && anchor.parentNode) {
        anchor.parentNode.insertBefore(createToggleButton(), anchor);
      } else {
        var header = document.querySelector('header');
        if (header) header.appendChild(createToggleButton());
      }
    }
    mountSheetToggle();
  }

  /* Dar ekranin kontrolu: mobil "Menü" sayfasindaki son ("Daha") izgaraya
     bir kart olarak eklenir. Sayfa `_mobile_nav_partial.html` ile gelir;
     yoksa sessizce atlanir (masaustu-only sablonlar). */
  function mountSheetToggle() {
    var sheet = document.getElementById('mbnSheet');
    if (!sheet || sheet.querySelector('.bp-lm-sheet')) return;
    var grids = sheet.querySelectorAll('.mbn-sheet-grid');
    var grid = grids[grids.length - 1];
    if (!grid) return;
    grid.appendChild(createToggleButton('sheet'));
  }

  function init() {
    ensureStyles();
    mountToggle();
    injectHints();
    applyBody();
    /* Gec eklenen icerik (JS render) icin observer.
       K-DH: geri cagirma ONCEDEN her mutasyonda dogrudan injectHints()
       kosturuyordu -- her cagri `querySelectorAll('.jargon-term')` demek.
       Motor 3 sayfadayken tasiniyordu; 8 sayfaya yayilinca (makro seridi
       3 dakikada bir, isi haritasi/portfoy grafikleri sik sik DOM
       degistiriyor) bu sessiz bir maliyet olurdu. Ayni kare icindeki
       mutasyonlar tek taramada birlestiriliyor -- davranis ayni, is
       kat kat az. */
    var pending = false;
    var mo = new MutationObserver(function () {
      if (pending) return;
      pending = true;
      (window.requestAnimationFrame || window.setTimeout)(function () {
        pending = false;
        injectHints();
      }, 0);
    });
    mo.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // DEV2-bughunt-r7: cok-sekme senkronu — baska sekmede degisen STORAGE_KEY'i yansit.
  // persistState() BILEREK cagrilmiyor (zaten diger sekme yazdi, feedback loop olusmasin).
  window.addEventListener('storage', function (e) {
    if (e.key !== STORAGE_KEY) return;
    STATE = e.newValue === '1';
    applyBody();
    closePop();
    var btns = document.querySelectorAll('.bp-lm-toggle');
    for (var i = 0; i < btns.length; i++) {
      btns[i].setAttribute('aria-pressed', STATE ? 'true' : 'false');
    }
  });

  // Global API
  window.bpLearningMode = { toggle: toggle, get state() { return STATE; } };
})();
