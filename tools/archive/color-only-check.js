#!/usr/bin/env node
// tools/color-only-check.js — K-AL: RENK TEK BAŞINA ANLAM TAŞIYOR MU?
// WCAG 2.1 · SC 1.4.1 "Use of Color" (A)
//
// SORU — bu sitede daha önce HİÇ sorulmadı, oysa burası renkle KONUŞAN bir ürün:
//   BorsaPusula'nın tüm veri dili üç renge dayanıyor:
//     --bp-al  #00e290 (yükseliş/olumlu) · --bp-sat #f85149 (düşüş/olumsuz)
//     --bp-bkl #909097 (nötr) · --bp-warn #d29922 (dikkat)
//   Kırmızı-yeşil ayrımı, erkeklerin ~%8'i (deuteranopi/protanopi) için YOKTUR.
//   O kullanıcı için "-1,67" ile "1,67" aynı ekranda aynı görünür; ayrımı
//   TAŞIYAN tek şey renkse, bilgi KAYBOLUR. Bu bir stil tercihi değil, A seviyesi.
//
// ÖLÇÜT (taban SIFIR) — bir eleman ancak HEPSİ doğruysa BULGU sayılır:
//   1. Görünür (boyut>0, opacity>.05, checkVisibility ata zinciriyle),
//   2. Metni/zemini SEMANTİK palete ait bir renkte (al/sat/warn),
//   3. Kendi metninde işaret/ok/durum sözcüğü YOK,
//   4. ::before / ::after içeriğinde ok/işaret glifi YOK,
//   5. Erişilebilir adında (aria-label / data-tip / title) işaret YOK,
//   6. EN YAKIN anlamlı kapsayıcısının metninde de işaret YOK  ← K-AH dersi:
//      [[reference_bilgi_kardes_elemanda_olabilir]] — işaret kardeşte olabilir
//      (`<span>+</span><span class="up">2,15</span>` kalıbı bulgu DEĞİLDİR),
//   7. Kardeş/torun bir ikonun erişilebilir adı yön bildirmiyor.
//   3-7 bu betiğin KENDİ sahte-pozitif kapılarıdır.
//
// AYRI SINIF (ayrıca sayılır, bulgu sayısını şişirmez):
//   · GRAFİK: semantik renkli SVG şekli (path/rect/circle/polygon) — değeri
//     metin olarak SUNULUYOR mu? (K-AI ad verdi; bu tur DEĞERİ soruyor.)
//   · ZEMİN-ISI: yalnız arka plan rengiyle kodlanmış ısı kutusu.
//
// ⛔ STATİK GREP YETMEZ: renklerin çoğu JS ile sınıf/inline-style olarak
//   atanıyor (`chg-up`/`chg-down`, ısı kutuları, radar eksenleri) — şablonda
//   `${...}` durur. Canlı DOM + getComputedStyle ZORUNLU.
//   [[reference_client_side_render_grep_kor]]
//
// POZİTİF KONTROL (--kill-fix): sayfadaki TÜM işaret/ok karakterlerini ve
//   ::before ok'larını görünür metinden siler → sayı FIRLAMALI. Fix sonrası
//   dedektörün kör olmadığını kanıtlar. [[feedback_positif_kontrol_checkout_commit_once]]
//
// Kullanım: node tools/color-only-check.js [--base=...] [--w=375,1280]
//           [--only=/a,/b] [--kill-fix] [--json=dosya] [--cap=N]
const { chromium } = require('playwright');

const BASE = (process.argv.find(a => a.startsWith('--base=')) || '').split('=')[1] || 'https://borsapusula.com';
const WIDTHS = ((process.argv.find(a => a.startsWith('--w=')) || '').split('=')[1] || '375,1280')
  .split(',').map(s => parseInt(s, 10)).filter(Boolean);
const ONLY = (process.argv.find(a => a.startsWith('--only=')) || '').split('=')[1] || '';
const JSON_OUT = (process.argv.find(a => a.startsWith('--json=')) || '').split('=')[1] || '';
const KILL_FIX = process.argv.includes('--kill-fix');
// [[reference_dedektor_ust_siniri_kapsam_yalani_uretir]] — üst sınır AÇIKÇA raporlanır
const CAP = parseInt(((process.argv.find(a => a.startsWith('--cap=')) || '').split('=')[1] || '400'), 10);

// title-tooltip / reduced-motion / text-clip / text-spacing / focus-obscured ile AYNI envanter
const PAGES = [
  '/', '/ozet', '/tarama', '/gundem', '/hisseler', '/sektor-harita',
  '/hisse/ASELS', '/hisse/GARAN', '/karsilastir', '/portfolio',
  '/takvim', '/blog', '/blog/rsi-gostergesi-nedir',
  '/metodoloji', '/hakkinda', '/iletisim', '/profil', '/yasal', '/gizlilik',
];
const EXPECT_4XX = new Set(['/profil']);

const PROBE = (opts) => {
  const CAP = opts.cap, KILL = opts.kill;

  // ---- semantik palet (tokens.css) + JS'in ürettiği yakın tonlar ----
  const SEM = [
    { name: 'al',   rgb: [0, 226, 144] },   // --bp-al
    { name: 'sat',  rgb: [248, 81, 73] },   // --bp-sat
    { name: 'sat',  rgb: [255, 123, 114] }, // --bp-sat-on-tint
    { name: 'sat',  rgb: [218, 54, 51] },   // --bp-sat-bd
    { name: 'warn', rgb: [210, 153, 34] },  // --bp-warn
    { name: 'warn', rgb: [227, 179, 65] },  // --bp-accent-yellow
    { name: 'warn', rgb: [245, 158, 11] },  // --bp-gold
  ];
  const parseRGB = (s) => {
    const m = /rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:[,/\s]+([\d.]+))?/.exec(s || '');
    if (!m) return null;
    return { r: +m[1], g: +m[2], b: +m[3], a: m[4] === undefined ? 1 : +m[4] };
  };
  // tolerans: aynı tokenin opaklık/karışım türevlerini yakala, nötrleri yakalama
  const semOf = (cssColor) => {
    const c = parseRGB(cssColor);
    if (!c || c.a < 0.35) return null;
    for (const s of SEM) {
      const d = Math.abs(c.r - s.rgb[0]) + Math.abs(c.g - s.rgb[1]) + Math.abs(c.b - s.rgb[2]);
      if (d <= 60) return s.name;
    }
    return null;
  };

  // ---- renk-DIŞI ipucu: işaret, ok glifi, yön/durum sözcüğü ----
  const SIGN_RE = /[+\-−–—▲▼△▽▴▾↑↓⬆⬇⇧⇩✓✔✗✘×]/;
  const WORD_RE = new RegExp(
    '(artı|arti|eksi|yüksel|yuksel|düş|dus|düşüş|yukarı|yukari|aşağı|asagi|'
    + 'pozitif|negatif|kâr|kar\\b|zarar|kazanç|kazanc|kayıp|kayip|güçlü|guclu|zayıf|zayif|'
    + 'iyi\\b|kötü|kotu|risk|uyarı|uyari|dikkat|hata|başarı|basari|tamam|geçti|gecti|'
    + 'kaldı|kaldi|bozuldu|aktif|pasif|açık|acik|kapalı|kapali|var\\b|yok\\b|'
    + 'gecikme|gecikmeli|bayat|güncel|guncel|taze|yükleni|yukleni|hazır|hazir|'
    + 'onaylı|onayli|prim|trend|sinyal|yeni\\b|eski|hedef|stop|seviye|'
    + 'bekle|nötr|notr|yeşil|yesil|kırmızı|kirmizi|alım|alim|satım|satim|'
    + 'primli|iskontolu|ucuz|pahalı|pahali|fazla|az\\b|eksik|tam\\b)', 'i');
  const hasCue = (t) => !!t && (SIGN_RE.test(t) || WORD_RE.test(t));

  const pseudoCue = (el) => {
    for (const p of ['::before', '::after']) {
      let c = '';
      try { c = getComputedStyle(el, p).content || ''; } catch (e) { }
      if (!c || c === 'none' || c === 'normal') continue;
      // content: "▲" / "\2191" → tarayıcı çözülmüş glifi döndürür
      if (hasCue(c.replace(/^["']|["']$/g, ''))) return true;
    }
    return false;
  };

  const visible = (el) => {
    try {
      if (el.checkVisibility && !el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })) return false;
    } catch (e) { }
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) return false;
    if (el.closest('[aria-hidden="true"],[inert],[hidden]')) return false;
    return true;
  };

  const norm = (s) => (s || '').replace(/\s+/g, ' ').trim();

  const accName = (el) => norm(
    (el.getAttribute && (el.getAttribute('aria-label') || el.getAttribute('data-tip') || el.getAttribute('title'))) || ''
  );

  const desc = (el) => {
    const cn = el.getAttribute ? (el.getAttribute('class') || '') : '';  // [[reference_svg_classname_string_degildir]]
    const id = el.id ? '#' + el.id : '';
    const cls = cn.trim() ? '.' + cn.trim().split(/\s+/).slice(0, 2).join('.') : '';
    return (el.tagName || '?').toLowerCase() + id + cls;
  };

  // KILL-FIX: görünür metinden ve erişilebilir addan TÜM işaretleri sil.
  // ::before ok'ları da silinir. Dedektör kör değilse sayı fırlamalı.
  if (KILL) {
    const st = document.createElement('style');
    st.textContent = '*::before,*::after{content:none !important}';
    document.documentElement.appendChild(st);
    const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (w.nextNode()) nodes.push(w.currentNode);
    for (const n of nodes) n.nodeValue = n.nodeValue.replace(/[+\-−–—▲▼△▽▴▾↑↓⬆⬇✓✔✗✘×]/g, '');
    for (const el of document.querySelectorAll('[aria-label],[data-tip],[title]')) {
      for (const a of ['aria-label', 'data-tip', 'title']) {
        const v = el.getAttribute(a);
        if (v) el.setAttribute(a, v.replace(/[+\-−–—▲▼△▽▴▾↑↓⬆⬇✓✔✗✘×]/g, ''));
      }
    }
  }

  const out = { findings: [], graphics: [], heat: [], scanned: 0, semTotal: 0, capped: false };
  const all = document.querySelectorAll('body *');

  for (const el of all) {
    const tag = (el.tagName || '').toLowerCase();
    if (tag === 'script' || tag === 'style' || tag === 'noscript') continue;
    if (!visible(el)) continue;
    out.scanned++;

    let cs; try { cs = getComputedStyle(el); } catch (e) { continue; }
    const semText = semOf(cs.color);
    const semBg = semOf(cs.backgroundColor);
    const semFill = semOf(cs.fill) || semOf(cs.stroke);
    const sem = semText || semBg || semFill;
    if (!sem) continue;

    // --- SVG şekilleri ayrı sınıf: değer metin olarak var mı? ---
    const isSvgShape = ['path', 'rect', 'circle', 'polygon', 'polyline', 'line', 'ellipse'].includes(tag);
    if (isSvgShape) {
      const host = el.closest('svg');
      const hostTxt = host ? norm(host.textContent) : '';
      const around = host && host.parentElement ? norm(host.parentElement.innerText || '') : '';
      if (!hasCue(hostTxt) && !hasCue(around) && !hasCue(accName(host || el))) {
        if (out.graphics.length < CAP) out.graphics.push({ el: desc(el), sem, host: host ? desc(host) : '-', around: around.slice(0, 60) });
      }
      continue;
    }

    // KAPI 0a — MARKA/LOGO: --bp-al burada DEKORATİF (anlam taşımıyor).
    if (el.closest('[class*="logo"],[class*="brand"],[class*="wordmark"]')) continue;
    // KAPI 0b — aria-current: "hangi sayfadayım" durumu renk-DIŞI kanalda da var
    //   (ayrıca dolgulu zemin + font-weight farkı = renk olmayan görsel fark).
    if (el.closest('[aria-current]')) continue;

    // --- metin taşıyan eleman mı? en İÇTEKİ sahibi al (ata zinciri şişmesin) ---
    const own = norm(el.innerText || el.textContent || '');
    const childCarries = Array.from(el.children || []).some(c => {
      try {
        const ccs = getComputedStyle(c);
        return !!(semOf(ccs.color) || semOf(ccs.backgroundColor));
      } catch (e) { return false; }
    });
    if (childCarries && own.length > 0) continue;   // ata: çocuk zaten raporlayacak

    out.semTotal++;

    // --- ZEMİN-ISI ayrı sınıf: metni yok, yalnız renkli kutu ---
    if (!own && (semBg || semFill)) {
      if (!hasCue(accName(el))) {
        let q = el.parentElement, hit = false, par = '';
        for (let i = 0; i < 3 && q && q !== document.body; i++, q = q.parentElement) {
          par = norm(q.innerText || q.textContent || '');
          if (par.length > 300) break;
          if (hasCue(par) || hasCue(accName(q))) { hit = true; break; }
        }
        if (!hit && out.heat.length < CAP) out.heat.push({ el: desc(el), sem, parent: par.slice(0, 60) });
      }
      continue;
    }
    if (!own) continue;

    // --- KAPILAR ---
    if (hasCue(own)) continue;                                   // 3
    if (pseudoCue(el)) continue;                                 // 4
    if (hasCue(accName(el))) continue;                           // 5
    // 6 — K-AH dersi: işaret KARDEŞTE/ATADA olabilir. En yakın 2 atayı oku.
    let p = el.parentElement, ctxHit = false, ctx = '';
    for (let i = 0; i < 3 && p && p !== document.body; i++, p = p.parentElement) {
      const t = norm(p.innerText || p.textContent || '');       // SVG'de innerText BOŞ döner
      if (t.length > 300) break;                                 // ata çok geniş: bağlam değil
      ctx = t;
      if (hasCue(t) || hasCue(accName(p)) || pseudoCue(p)) { ctxHit = true; break; }
    }
    if (ctxHit) continue;
    // 7 — kardeş/torun ikonun erişilebilir adı yön bildiriyor mu?
    let iconHit = false;
    const scope = el.parentElement || el;
    for (const ic of scope.querySelectorAll('svg,img,i,[class*="icon"],[class*="arrow"],[class*="caret"],[class*="chevron"]')) {
      if (hasCue(accName(ic)) || /arrow|caret|chevron|up|down/i.test(ic.getAttribute('class') || '')) { iconHit = true; break; }
    }
    if (iconHit) continue;

    if (out.findings.length >= CAP) { out.capped = true; continue; }
    out.findings.push({ el: desc(el), sem, text: own.slice(0, 70), ctx: ctx.slice(0, 80) });
  }
  return out;
};

(async () => {
  const pages = ONLY ? ONLY.split(',') : PAGES;
  const browser = await chromium.launch();
  const report = [];
  let totalF = 0, totalG = 0, totalH = 0, errors = 0;

  for (const w of WIDTHS) {
    const ctx = await browser.newContext({ viewport: { width: w, height: 900 } });
    const page = await ctx.newPage();
    for (const p of pages) {
      let res;
      try {
        res = await page.goto(BASE + p, { waitUntil: 'networkidle', timeout: 45000 });
      } catch (e) {
        console.log(`ERROR  ${w}px ${p} — ${e.message.slice(0, 80)}`); errors++; continue;
      }
      const st = res ? res.status() : 0;
      if (st >= 400 && !EXPECT_4XX.has(p)) {
        console.log(`ERROR  ${w}px ${p} — HTTP ${st} (ölü rota = kapsam yalanı)`); errors++; continue;
      }
      await page.waitForTimeout(1500);
      let r;
      try {
        r = await page.evaluate(PROBE, { cap: CAP, kill: KILL_FIX });
      } catch (e) {
        console.log(`ERROR  ${w}px ${p} — probe: ${e.message.slice(0, 80)}`); errors++; continue;
      }
      totalF += r.findings.length; totalG += r.graphics.length; totalH += r.heat.length;
      report.push({ w, p, ...r });
      const flag = r.findings.length ? 'FAIL' : 'OK  ';
      console.log(`${flag}  ${w}px ${p}  bulgu=${r.findings.length} grafik=${r.graphics.length} isi=${r.heat.length} (semantik eleman=${r.semTotal}, taranan=${r.scanned})${r.capped ? ' ⚠️CAP' : ''}`);
      for (const f of r.findings.slice(0, 8)) {
        console.log(`        · [${f.sem}] ${f.el}  "${f.text}"   ctx="${f.ctx}"`);
      }
    }
    await ctx.close();
  }
  await browser.close();
  console.log(`\n=== K-AL TOPLAM: bulgu=${totalF}  grafik=${totalG}  isi-kutusu=${totalH}  hata=${errors} ===`);
  if (JSON_OUT) require('fs').writeFileSync(JSON_OUT, JSON.stringify(report, null, 2));
  process.exit(totalF > 0 || errors > 0 ? 1 : 0);
})();
