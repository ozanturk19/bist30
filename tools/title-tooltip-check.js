#!/usr/bin/env node
// tools/title-tooltip-check.js — K-AH: SADECE FARE İLE ULAŞILABİLEN İÇERİK
// WCAG 2.1 · SC 1.4.13 "Content on Hover or Focus" (AA) + SC 1.1.1/4.1.2 komşuluğu
//
// SORU — daha önce HİÇ sorulmadı:
//   Bir `title="..."` içinde YALNIZCA orada bulunan bir bilgi varsa, o bilgiye
//   DOKUNMATİK bir cihazda veya KLAVYEYLE ulaşmanın YOLU YOKTUR.
//   Bu, tarayıcıların yerleşik davranışıdır, bir stil tercihi değil:
//     · iOS Safari / Android Chrome: native `title` tooltip HİÇ gösterilmez.
//     · Hiçbir büyük tarayıcı `title`'ı klavye ODAĞINDA göstermez (yalnız hover).
//     · Gösterildiğinde de Esc ile kapatılamaz, üzerine gelinemez (1.4.13 ihlali).
//   Yani `title` bir tooltip DEĞİL, yalnızca-fare bir yan kanaldır.
//
// REPO ZATEN BUNU BİLİYOR — kanonik çare YAZILMIŞ ama GENELLEŞTİRİLMEMİŞ:
//   `static/js/bp-tooltip.js` başlığı birebir şöyle: "[data-tip] icin
//   dokunmatik+klavye erisilebilir tooltip (T5.5, native title= yerine)".
//   hover + focus + tap(toggle) + Escape + dışarı-tıklama destekler.
//   Ama 7 şablonda yüklü, 2 ağır şablonda (index.html, portfolio.html) YOK;
//   yüklü olan şablonlarda bile hâlâ native `title` kullanan yerler var.
//   K-AG'nin birebir kalıbı: çare repoda duruyor, kapsamı eksik.
//
// ÖLÇÜT (taban SIFIR) — bir `title` ancak HEPSİ doğruysa BULGU sayılır:
//   1. Eleman görünür (boyut>0, opacity>.05, aria-hidden/inert ata yok),
//   2. `title` metni elemanın GÖRÜNEN metninde YOK (yani metnin kopyası değil),
//   3. `aria-label`/`aria-describedby` metnini KAPSAMIYOR (ek bilgi taşıyor),
//   4. Elemanda (veya atasında) `[data-tip]` YOK (erişilebilir kanal yok),
//   5. Eleman `<iframe>` DEĞİL (orada `title` ZORUNLUDUR, SC 4.1.2).
//   2-3-4 bu betiğin KENDİ sahte-pozitif kapılarıdır: bilgi başka bir kanaldan
//   da sunuluyorsa kayıp YOKTUR, bulgu DEĞİLDİR.
//
// AYRI SINIF (bulgu değil, ayrıca sayılır) — "kırpık-kurtarma":
//   `title` elemanın KENDİ metninin tam hâliyse ve metin gerçekten kırpılmışsa
//   (scrollWidth > clientWidth), bu K-AE'nin alanıdır. Dokunmatikte yine
//   ulaşılamaz ama sınıfı farklıdır (kayıp = kırpılan kuyruk, tüm bilgi değil).
//   AYRI raporlanır ki bu turun sayısı şişmesin.
//
// ⛔ STATİK GREP YETMEZ, CANLI DOM ZORUNLU: `title`lerin bir kısmı JS ile
//   üretiliyor (`hisse.html` bilanço barları, `index.html` ısı kutucukları,
//   `portfolio.html` satırları) — şablon kaynağında `${...}` olarak durur,
//   grep içeriğini ÇÖZEMEZ. Tersi de doğru: şablondaki `title` ölü dalda olabilir.
//
// POZİTİF KONTROL (--kill-fix): sayfadaki TÜM `[data-tip]`leri native `title`a
//   geri çevirir. Fix sonrası dedektörün kör olmadığını kanıtlar.
//
// Kullanım: node tools/title-tooltip-check.js [--base=...] [--w=375,1280]
//           [--only=/a,/b] [--kill-fix] [--json=dosya]
const { chromium } = require('playwright');

const BASE = (process.argv.find(a => a.startsWith('--base=')) || '').split('=')[1] || 'https://borsapusula.com';
const WIDTHS = ((process.argv.find(a => a.startsWith('--w=')) || '').split('=')[1] || '375,1280')
  .split(',').map(s => parseInt(s, 10)).filter(Boolean);
const ONLY = (process.argv.find(a => a.startsWith('--only=')) || '').split('=')[1] || '';
const JSON_OUT = (process.argv.find(a => a.startsWith('--json=')) || '').split('=')[1] || '';
const KILL_FIX = process.argv.includes('--kill-fix');

// reduced-motion / text-clip / text-spacing / focus-obscured ile AYNI envanter
// (K-S dersi: ölü rota bir kapsam yalanıdır — ERROR olarak raporlanır).
const PAGES = [
  '/', '/ozet', '/tarama', '/gundem', '/hisseler', '/sektor-harita',
  '/hisse/ASELS', '/hisse/GARAN', '/karsilastir', '/portfolio',
  '/takvim', '/blog', '/blog/rsi-gostergesi-nedir',
  '/metodoloji', '/hakkinda', '/iletisim', '/profil', '/yasal', '/gizlilik',
];
const EXPECT_4XX = new Set(['/profil']);

const PROBE = () => {
  const norm = (s) => (s || '').replace(/\s+/g, ' ').trim().toLocaleLowerCase('tr');

  const desc = (el) => {
    const id = el.id ? '#' + el.id : '';
    const cls = (typeof el.className === 'string' && el.className.trim())
      ? '.' + el.className.trim().split(/\s+/).slice(0, 2).join('.') : '';
    return el.tagName.toLowerCase() + id + cls;
  };

  // ⛔ ATA ZİNCİRİ FARKINDA: kendi display/visibility'sine bakmak yetmez —
  //   kapalı <details>, gizli sekme paneli, gizli açılır katman içindeki eleman
  //   "görünür" ölçülüp innerText'i BOŞ döner ve sahte-pozitif üretir.
  //   checkVisibility() ata zincirini de değerlendirir (Chromium 105+).
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return false;
    // ⛔ contentVisibilityAuto GEÇİLMEZ: `content-visibility:auto` olan bir
    //   kapsayıcının EKRAN DIŞINDAKİ çocuğu için checkVisibility false döner.
    //   Ama kullanıcı oraya KAYDIRABİLİR — eleman görünürdür. İlk koşumda bu
    //   bayrak ana sayfanın 13 sektör kutucuğunun HEPSİNİ "ölçülmedi"ye attı.
    if (el.checkVisibility && !el.checkVisibility({
      checkOpacity: true, checkVisibilityCSS: true,
    })) return false;
    if (parseFloat(getComputedStyle(el).opacity) < 0.05) return false;
    if (el.closest('[aria-hidden="true"],[inert]')) return false;
    if (el.closest('details:not([open])')) return false;
    if (el.offsetParent === null && getComputedStyle(el).position !== 'fixed') return false;
    return true;
  };

  // aria adı: kendi aria-label'ı + aria-describedby'nin metni + atadaki aria-label
  const ariaText = (el) => {
    let out = el.getAttribute('aria-label') || '';
    const db = el.getAttribute('aria-describedby');
    if (db) {
      db.split(/\s+/).forEach((id) => {
        const n = document.getElementById(id);
        if (n) out += ' ' + (n.textContent || '');
      });
    }
    const anc = el.parentElement && el.parentElement.closest('[aria-label]');
    if (anc) out += ' ' + (anc.getAttribute('aria-label') || '');
    return out;
  };

  const clipped = (el) => el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 1;

  // ⛔ BİLGİ KARDEŞTE OLABİLİR (K-AE dersinin TERSİ yönü).
  //   /hisse bilanço grafiğinde `title="Ciro 2024: 287,2 Mr ₺"` içi BOŞ bir
  //   bar <div>'indedir; AYNI değer barın ÜSTÜNDEKİ KARDEŞ <div>'de GÖRÜNÜR
  //   olarak basılır. Yalnız `el.innerText`e bakmak bunu "gizli bilgi" sanar.
  //   Bu betiğin ilk koşumunda tam olarak bu oldu ve 32 sahte-pozitif üretti.
  //   Kıyas metni: eleman + en yakın 4 ata kuşağının GÖRÜNEN metni (sabit).
  //   ⛔ PENCERE BİLİNEN CEVABA GÖRE AYARLANMAZ. Denendi: "kutusu 2 kat büyük
  //   ilk ata" penceresi bilanço barını mazur göstermek için genişletiliyordu —
  //   yani dedektör beklenen sonuca kalibre ediliyordu. Geri alındı.
  //   Bu yüzden bu sayı bir ADAY listesidir, bulgu listesi DEĞİL: kalan
  //   kalıplar ELLE ve gerekçeli hükme bağlanır (bkz. K-AH memory kaydı).
  //   Bilinen sahte-pozitif: /hisse bilanço barları (%67) — değer barın
  //   ÜSTÜNDEKİ kardeşte GÖRÜNÜR, seri adı grafiğin göstergesinde yazıyor.
  const STOP = new Set(['ve','ile','bir','bu','için','olarak','daha','tüm','göster',
    'gizle','aç','kapat','teknik','analiz','—','·']);
  const tokens = (s) => norm(s).split(/[^0-9a-zçğıöşü%₺.,+-]+/i)
    .filter(t => t.length >= 3 && !STOP.has(t));
  // title'ın bilgi belirteçlerinin kaçı çevredeki GÖRÜNEN metinde var?
  const coverage = (el, t) => {
    let scope = el, up = 0;
    while (scope.parentElement && up < 4) { scope = scope.parentElement; up++; }
    const hay = ' ' + norm(scope.innerText || '') + ' ';
    const tk = tokens(t);
    if (!tk.length) return 1;
    return tk.filter(x => hay.includes(x)).length / tk.length;
  };

  const rows = [];
  let skippedHidden = 0;

  document.querySelectorAll('[title]').forEach((el) => {
    const t = (el.getAttribute('title') || '').trim();
    if (!t) return;
    const tag = el.tagName.toLowerCase();
    // 5. koşul: iframe'de title ZORUNLU (SC 4.1.2) — muafiyet, bulgu değil.
    if (tag === 'iframe' || tag === 'link' || tag === 'style' || tag === 'meta') return;
    if (!visible(el)) { skippedHidden++; return; }

    const nt = norm(t);
    const own = norm(el.innerText || el.textContent || '');
    const aria = norm(ariaText(el));
    const hasTip = !!el.closest('[data-tip]');

    const cov = coverage(el, t);
    let cls;
    if (hasTip) cls = 'ERISILEBILIR-KANAL-VAR';          // 4. kapı
    else if (own && own.includes(nt)) cls = clipped(el) ? 'KIRPIK-KURTARMA' : 'METIN-KOPYASI'; // 2. kapı
    else if (aria && aria.includes(nt)) cls = 'ARIA-KOPYASI';   // 3. kapı
    else if (cov >= 0.7) cls = 'KOMSU-METINDE';          // 2b. kapı — kardeş/ata metni
    else cls = 'YALNIZ-FARE';                                    // BULGU

    rows.push({
      cls, cov: Math.round(cov * 100), sel: desc(el), title: t.slice(0, 90),
      text: (el.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 40),
      aria: (el.getAttribute('aria-label') || '').slice(0, 40),
    });
  });

  return {
    rows, skippedHidden,
    tipScript: !!document.querySelector('script[src*="bp-tooltip"]'),
    tipCount: document.querySelectorAll('[data-tip]').length,
  };
};

// Pozitif kontrol: erişilebilir kanalı SÖKER (data-tip -> title).
const KILL = () => {
  document.querySelectorAll('[data-tip]').forEach((el) => {
    el.setAttribute('title', el.getAttribute('data-tip'));
    el.removeAttribute('data-tip');
  });
  document.querySelectorAll('script[src*="bp-tooltip"]').forEach((s) => s.remove());
};

(async () => {
  const pages = ONLY ? ONLY.split(',') : PAGES;
  const browser = await chromium.launch();
  const findings = [];
  const other = { 'KIRPIK-KURTARMA': 0, 'METIN-KOPYASI': 0, 'ARIA-KOPYASI': 0, 'KOMSU-METINDE': 0, 'ERISILEBILIR-KANAL-VAR': 0 };
  let errors = 0, hiddenTotal = 0;
  const noScript = [];

  for (const w of WIDTHS) {
    const ctx = await browser.newContext({ viewport: { width: w, height: 800 } });
    for (const p of pages) {
      const page = await ctx.newPage();
      let res;
      try {
        res = await page.goto(BASE + p, { waitUntil: 'networkidle', timeout: 45000 });
      } catch (e) {
        console.log(`ERROR  @${w} ${p} — yüklenemedi: ${e.message.split('\n')[0]}`);
        errors++; await page.close(); continue;
      }
      const st = res ? res.status() : 0;
      if (st >= 400 && !EXPECT_4XX.has(p)) {
        console.log(`ERROR  @${w} ${p} — HTTP ${st} (ÖLÜ ROTA, kapsam yalanı)`);
        errors++; await page.close(); continue;
      }
      // JS ile üretilen title'lar için: ağ boşaldıktan sonra iki kare bekle
      // (⛔ getComputedStyle/classList aynı-tick bayatlığı dersi).
      await page.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))));
      if (KILL_FIX) await page.evaluate(KILL);

      const out = await page.evaluate(PROBE);
      hiddenTotal += out.skippedHidden;

      const bad = out.rows.filter(r => r.cls === 'YALNIZ-FARE');
      out.rows.forEach(r => { if (r.cls !== 'YALNIZ-FARE') other[r.cls]++; });

      if (bad.length && !out.tipScript) noScript.push(`${p}@${w}`);

      const tag = bad.length ? `${String(bad.length).padStart(3)} YALNIZ-FARE` : '     OK      ';
      console.log(`${tag}  @${w} ${p}  (data-tip:${out.tipCount}${out.tipScript ? '' : ' ⛔SCRIPT-YOK'}${out.skippedHidden ? ', gizli:' + out.skippedHidden : ''})`);
      bad.forEach(r => {
        console.log(`        ${r.sel}  title="${r.title}"${r.aria ? `  [aria-label="${r.aria}"]` : ''}`);
        findings.push({ page: p, w, ...r });
      });
      await page.close();
    }
    await ctx.close();
  }
  await browser.close();

  console.log('\n──────── ÖZET ────────');
  console.log(`BULGU (YALNIZ-FARE, dokunmatik+klavyede ERİŞİLEMEZ): ${findings.length}`);
  console.log(`Ayrı sınıf — kırpık-kurtarma (K-AE alanı): ${other['KIRPIK-KURTARMA']}`);
  console.log(`Kapı ile elenen — metin kopyası: ${other['METIN-KOPYASI']}, aria kopyası: ${other['ARIA-KOPYASI']}, komşu metinde: ${other['KOMSU-METINDE']}, data-tip var: ${other['ERISILEBILIR-KANAL-VAR']}`);
  console.log(`Ölçülmedi (gizli/kapalı katman): ${hiddenTotal} · ERROR (ölü rota): ${errors}`);
  if (noScript.length) console.log(`⛔ bp-tooltip.js YÜKLÜ DEĞİL ama bulgusu olan: ${[...new Set(noScript)].join(', ')}`);
  if (KILL_FIX) console.log('(--kill-fix açık: erişilebilir kanal SÖKÜLDÜ, bu sayılar pozitif kontroldür)');

  if (JSON_OUT) require('fs').writeFileSync(JSON_OUT, JSON.stringify({ findings, other, errors, hiddenTotal }, null, 2));
  process.exit(findings.length || errors ? 1 : 0);
})();
