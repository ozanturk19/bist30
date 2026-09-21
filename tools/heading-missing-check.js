#!/usr/bin/env node
// tools/heading-missing-check.js — K-AM (2. yarı): GÖRSEL BÖLÜM VAR, BAŞLIK YOK
// WCAG 2.1 · SC 1.3.1 "Info and Relationships" (A)
//
// ⛔ NEDEN AYRI BİR DEDEKTÖR: `heading-outline-check.js` "VAR OLAN başlıklar
//   düzgün sıralı mı?" diye sordu ve 20 sayfada 0 bulgu verdi. Ama o sıfır bir
//   TEMİZLİK KANITI DEĞİLDİ: /ozet, /tarama, /gundem, /bilanco-takvimi ve
//   /temettu-takvimi'nde erişilebilirlik ağacında TEK bir başlık vardı (sr-only
//   h1). Zincir kırık değildi — zincir YOKTU. Ekran okuyucu kullanıcısı bu
//   sayfalarda "H" tuşuna bastığında tek durak alır; görsel olarak 6 bölüme
//   ayrılmış sayfa onun için TEK bir metin yığınıdır.
//   → [[reference_tanimsiz_sinif_ayri_bir_denetim_boyutu]]
//
// SORU: Görsel olarak bir bölümü BAŞLATAN ama ağaçta başlık OLMAYAN öğe var mı?
//
// ADAY ÖLÇÜTÜ (hepsi doğru olmalı):
//   1. Erişilebilirlik ağacında (display/visibility/aria-hidden/inert gateleri),
//   2. Başlık DEĞİL (h1-h6 / role=heading değil) ve bir denetimin kendi metni değil
//      (button/a/label/summary/th/legend/option içinde ya da kendisi değil),
//   3. Kendi doğrudan metni 2–60 karakter,
//   4. Tipografik olarak öne çıkıyor: gövde puntosunun ≥1.15 katı, VEYA
//      kalınlık ≥600 & punto ≥ gövde, VEYA büyük-harf + harf aralığı ≥0.5px & ≥600
//      (sitenin "eyebrow" bölüm etiketi kalıbı),
//   5. Bir BÖLGE başlatıyor: tanıttığı kutu ≥150px yüksek.
//
// BÖLÜM mü KART mı (ayrım ölçülür, varsayılmaz):
//   Tanıttığı bölge BAŞKA bir aday içeriyorsa ya da ≥6 bağlantı/satır taşıyorsa
//   → BOLUM (bulgu). Aksi halde → KART (ayrı sınıf, bulguyu şişirmez).
//
// SAHTE-POZİTİF KAPILARI:
//   · Ata bir bölge/section `aria-labelledby` ile BU öğeyi gösteriyorsa yapı
//     zaten programatik olarak aktarılıyor → bulgu DEĞİL,
//   · Ata `aria-label` taşıyan bir landmark ise → bulgu DEĞİL,
//   · Öğenin kendisi `<caption>` / `<figcaption>` / `<dt>` ise → bulgu DEĞİL,
//   · `<th>` ise → tablo başlığı, kendi semantiği var.
//
// POZİTİF KONTROL (--demote): sayfadaki TÜM h2/h3'ler düz div'e çevrilir
//   (stil korunur). BOLUM sayısı FIRLAMALI — dedektörün kör olmadığını kanıtlar.
//   [[feedback_positif_kontrol_checkout_commit_once]]
//
// Kullanım: node tools/heading-missing-check.js [--base=] [--w=375,1280]
//           [--only=/a,/b] [--demote] [--json=dosya]
const { chromium } = require('playwright');

const BASE = (process.argv.find(a => a.startsWith('--base=')) || '').split('=')[1] || 'https://borsapusula.com';
const WIDTHS = ((process.argv.find(a => a.startsWith('--w=')) || '').split('=')[1] || '375,1280')
  .split(',').map(s => parseInt(s, 10)).filter(Boolean);
const ONLY = (process.argv.find(a => a.startsWith('--only=')) || '').split('=')[1] || '';
const JSON_OUT = (process.argv.find(a => a.startsWith('--json=')) || '').split('=')[1] || '';
const DEMOTE = process.argv.includes('--demote');

const PAGES = [
  '/', '/ozet', '/tarama', '/gundem', '/hisseler', '/sektor-harita',
  '/hisse/ASELS', '/hisse/GARAN', '/karsilastir', '/portfolio',
  '/bilanco-takvimi', '/temettu-takvimi', '/blog', '/blog/rsi-gostergesi-nedir',
  '/metodoloji', '/hakkinda', '/iletisim', '/profil', '/yasal', '/gizlilik',
];
const EXPECT_4XX = new Set(['/profil']);

const PROBE = (opts) => {
  // ── pozitif kontrol: gerçek başlıkları düz div'e indir ────────────────
  if (opts.demote) {
    for (const h of Array.from(document.querySelectorAll('h2,h3'))) {
      const d = document.createElement('div');
      d.setAttribute('style', getComputedStyle(h).cssText || '');
      d.className = h.className; d.innerHTML = h.innerHTML;
      h.parentNode.replaceChild(d, h);
    }
  }

  const inTree = (el) => {
    if (el.closest('[aria-hidden="true"],[inert],[hidden]')) return false;
    let n = el;
    while (n && n.nodeType === 1) {
      const cs = getComputedStyle(n);
      if (cs.display === 'none' || cs.visibility === 'hidden' || cs.visibility === 'collapse') return false;
      n = n.parentElement;
    }
    return true;
  };
  const desc = (el) => {
    const id = el.id ? '#' + el.id : '';
    const cl = (typeof el.className === 'string' && el.className)
      ? '.' + el.className.trim().split(/\s+/).slice(0, 2).join('.') : '';
    return el.tagName.toLowerCase() + id + cl;
  };
  // yalnız DOĞRUDAN metin düğümleri (alt bloklarınki değil)
  const ownText = (el) => {
    let t = '';
    for (const n of el.childNodes) {
      if (n.nodeType === 3) t += n.nodeValue;
      else if (n.nodeType === 1 && ['SPAN', 'STRONG', 'B', 'EM', 'I'].includes(n.tagName)
        && !n.hasAttribute('aria-hidden')) t += n.textContent;
    }
    return t.replace(/\s+/g, ' ').trim();
  };

  const bodyFS = parseFloat(getComputedStyle(document.body).fontSize) || 16;
  const CONTROL = 'button,a,label,summary,th,legend,option,select,input,textarea';

  const cands = [];
  const cards = [];
  const repeated = [];
  let scanned = 0;

  for (const el of Array.from(document.querySelectorAll('main div, main span, main p, main strong'))) {
    scanned++;
    if (!inTree(el)) continue;
    if (/^H[1-6]$/.test(el.tagName) || (el.getAttribute('role') || '') === 'heading') continue;
    if (el.closest(CONTROL) || el.matches(CONTROL)) continue;
    if (el.closest('caption,figcaption,dt')) continue;

    const txt = ownText(el);
    if (txt.length < 2 || txt.length > 60) continue;
    // KAPI-A: salt sayı / para / yüzde / emoji — bir bölümü ADLANDIRMAZ.
    // ⛔ `\p{L}{2}` (BİTİŞİK iki harf) yazımı yanlıştı: "Q2 2026 (H1)" dönem
    //    başlığında bitişik iki harf YOKTUR ve gerçek bulgu sessizce düşüyordu.
    //    Ölçüt bitişiklik değil, metinde TOPLAM en az iki harf olmasıdır.
    if ((txt.match(/\p{L}/gu) || []).length < 2) continue;

    // KAPI-A2: ROZET/DURUM/DEĞER bileşenleri başlık değildir — bir bölümü
    // ADLANDIRMAZLAR, bir durumu GÖSTERİRLER (/hisse hero'sundaki "⏸ YATAY"
    // rozeti gibi). Öğenin kendisi ya da rozet kabının içindeyse elenir.
    const BADGEY = /badge|chip|pill|\btag\b|status|value|price|count|\bnum\b|metric|\bstat\b|ticker|rozet/i;
    let badgey = false;
    for (let a = el; a && a !== document.body; a = a.parentElement) {
      if (typeof a.className === 'string' && BADGEY.test(a.className)) { badgey = true; break; }
      if (a.parentElement && a.parentElement.tagName === 'MAIN') break;
    }
    if (badgey) continue;

    const cs = getComputedStyle(el);
    // KAPI-B: satır içi vurgu başlık değildir (<strong>üzerinde</strong> cümle içinde)
    if (!['block', 'flex', 'grid', 'flow-root', 'list-item', 'table-caption'].includes(cs.display)) continue;

    const fs = parseFloat(cs.fontSize) || 0;
    const fw = parseInt(cs.fontWeight, 10) || 400;
    const ls = parseFloat(cs.letterSpacing) || 0;
    const upper = cs.textTransform === 'uppercase';
    const prominent = (fs >= bodyFS * 1.15)
      || (fw >= 600 && fs >= bodyFS)
      || (upper && ls >= 0.5 && fw >= 600);
    if (!prominent) continue;

    // BÖLGE: yukarı doğru SINIRSIZ yürümek küçük kartlara dev bölge uydurur —
    // bölge, öğenin kendi bölümsel kapsayıcısıdır (yoksa ebeveyni).
    // BÖLGE — iki tuzak birden var:
    //  ⛔ closest() ÖĞENİN KENDİSİNİ de döndürür: `.section-title` sınıfı
    //     [class*="section"]'a UYAR; bu tam olarak aranan kusurun imzasıydı.
    //  ⛔ ebeveynden closest() ise `.section-hdr` gibi SADECE başlık satırını
    //     saran küçük kutuyu döndürür (yükseklik ~30px) ve gerçek bölüm
    //     görünmez olur. Bu yüzden: ata zincirinde yukarı YÜRÜ, bölümsel VE
    //     yeterince büyük ilk kutuyu al. [[reference_dedektor_tek_genislik_kapsam_yalani]]
    const SECT = 'section,article,aside,[class*="section"],[class*="panel"],[class*="card"],[class*="block"],[class*="grid"],[class*="wrap"]';
    // Bölge, başlığın TANITTIĞI kutudur. İki uçlu tuzak:
    //  · Çok yakın durursan `.section-hdr` gibi SADECE başlık satırını saran
    //    kutuyu alırsın (yükseklik ~ başlık yüksekliği) — bölüm görünmez olur.
    //  · Çok yukarı çıkarsan TÜM bölümleri saran kabı alırsın; o zaman KAPI-D
    //    (aynı imzadan ≥3) gerçek bölüm başlıklarını "bileşen" sanıp eler.
    // Ölçüt: başlığın kendi yüksekliğinin 1.8 katından BÜYÜK ilk bölümsel ata.
    const er0 = el.getBoundingClientRect();
    const eh = er0.height || 16;
    let region = null;
    let n = el.parentElement, up = 0;
    while (n && n !== document.body && up++ < 7) {
      const h = n.getBoundingClientRect().height;
      if (h > eh * 1.8 && (n.matches(SECT) || (n.parentElement && n.parentElement.tagName === 'MAIN'))) { region = n; break; }
      n = n.parentElement;
    }
    // ⛔ KÖR NOKTA (21.09 ikinci dalga): başlık, içeriğin YANINDAKİ bir başlık
    //    PANELİNDE durabilir — /bilanco-takvimi'nde `.period-label`,
    //    `.period-header.da-panel` içindedir ve asıl içerik onun KARDEŞİ olan
    //    `.period-section`'dadır. İlk uyan atada durup "altında 60px içerik
    //    yok" diye elemek, tam da aranan sınıfı düşürür (`.section-hdr`
    //    tuzağının ikinci yüzü). Bu yüzden: içerik yetmiyorsa YUKARI DEVAM ET.
    let rr = null;
    while (region && region !== document.body) {
      const cand = region.getBoundingClientRect();
      if (cand.bottom - er0.bottom >= 60) { rr = cand; break; }
      region = region.parentElement;
    }
    if (!region || !rr) continue;

    // KAPI-C: BAŞLIK BÖLGENİN TEPESİNDE DURUR. Ortada duran kalın metin
    // gövde vurgusudur ya da ızgaradaki N. kartın adıdır, bölüm adı değildir.
    if (er0.top - rr.top > Math.max(60, rr.height * 0.25)) continue;

    // KAPI-D: AYNI bölgede aynı imzadan ≥3 tane varsa bu bir BİLEŞEN adıdır
    // (ızgaradaki kart başlığı), bölümün başlığı değildir.
    const sig = el.tagName + '.' + (typeof el.className === 'string' ? el.className.trim().split(/\s+/)[0] : '');
    let twins = 0;
    if (sig.endsWith('.')) twins = 0;
    else { try { twins = region.querySelectorAll(el.tagName + '.' + CSS.escape(el.className.trim().split(/\s+/)[0])).length; } catch (e) { twins = 0; } }
    if (twins >= 3) { repeated.push({ el: desc(el), text: txt, twins }); continue; }

    // KAPI: ata bir bölge bu öğeyi aria-labelledby ile zaten adlandırıyor mu?
    if (el.id) {
      const ref = document.querySelector(`[aria-labelledby~="${CSS.escape(el.id)}"]`);
      if (ref && ref.contains(el)) continue;
    }
    // KAPI: ata landmark kendi aria-label'ını taşıyor mu?
    if (el.closest('[role="region"][aria-label],section[aria-label],nav[aria-label],aside[aria-label]')) continue;

    // BÖLÜM mü KART mı — ölçülür:
    //  · derinlik: bölge <main> altında kaç kat aşağıda? Bölümler üst katta
    //    durur (≤3); ızgara içindeki kartlar daha derinde.
    //  · bölgenin İÇİNDE zaten gerçek bir başlık varsa yapı aktarılıyordur.
    let depth = 0; let q = region;
    while (q && q.parentElement && q.tagName !== 'MAIN') { q = q.parentElement; depth++; if (depth > 12) break; }
    // ⛔ "bölgede başlık var mı" sorusunu BÖLGEYE sormak yetmez: /metodoloji'nin
    //    kriter kartları kendi kutularında başlıksızdır ama onları KAPSAYAN bölümün
    //    h2'si zaten o içeriği adlandırır. Soru şudur: öğe ile <main> ARASINDAKİ
    //    atalardan herhangi biri gerçek bir başlık taşıyor mu? Taşıyorsa bu bir
    //    ALT-ETİKETTİR, bölüm adı değildir. <main>'in kendisi sayılmaz (yoksa
    //    tek bir sayfa başlığı TÜM bulguları siler = kapsam yalanı).
    let hasH = false;
    for (let a = el.parentElement; a && a.tagName !== 'MAIN' && a !== document.body; a = a.parentElement) {
      if (a.querySelector('h1,h2,h3,h4,h5,h6,[role="heading"]')) { hasH = true; break; }
    }
    cands.push({ el, desc: desc(el), text: txt, fs: Math.round(fs), fw, region, rh: Math.round(rr.height), depth, hasH });
  }

  // BOLUM / KART ayrımı — ölçülerek
  const findings = [];
  for (const c of cands) {
    if (!c.hasH) findings.push({ k: 'BOLUM', el: c.desc, text: c.text, fs: c.fs, fw: c.fw, rh: c.rh, depth: c.depth });
    else cards.push({ el: c.desc, text: c.text, depth: c.depth, hasH: c.hasH });
  }
  const headings = Array.from(document.querySelectorAll('h1,h2,h3,h4,h5,h6,[role="heading"]')).filter(inTree).length;
  return { scanned, headings, findings, cards, repeated };
};

(async () => {
  const pages = ONLY ? ONLY.split(',') : PAGES;
  const browser = await chromium.launch();
  const report = []; let totalF = 0, totalK = 0, totalR = 0, errors = 0;
  for (const w of WIDTHS) {
    const ctx = await browser.newContext({ viewport: { width: w, height: 900 } });
    const page = await ctx.newPage();
    for (const p of pages) {
      let res;
      try { res = await page.goto(BASE + p, { waitUntil: 'networkidle', timeout: 45000 }); }
      catch (e) { console.log(`ERROR  ${w}px ${p} — ${e.message.slice(0, 80)}`); errors++; continue; }
      const st = res ? res.status() : 0;
      if (st >= 400 && !EXPECT_4XX.has(p)) { console.log(`ERROR  ${w}px ${p} — HTTP ${st}`); errors++; continue; }
      await page.waitForTimeout(1800);
      let r;
      try { r = await page.evaluate(PROBE, { demote: DEMOTE }); }
      catch (e) { console.log(`ERROR  ${w}px ${p} — probe: ${e.message.slice(0, 90)}`); errors++; continue; }
      totalF += r.findings.length; totalK += r.cards.length; totalR += (r.repeated||[]).length;
      report.push({ w, p, ...r });
      console.log(`${r.findings.length ? 'FAIL' : 'OK  '}  ${w}px ${p}  BOLUM=${r.findings.length} kart=${r.cards.length} bilesen=${(r.repeated||[]).length} (agactaki-baslik=${r.headings}, taranan=${r.scanned})`);
      for (const f of r.findings.slice(0, 12)) {
        console.log(`        · ${f.el}  "${f.text}"  ${f.fs}px/${f.fw}  bolge=${f.rh}px derinlik=${f.depth}`);
      }
    }
    await ctx.close();
  }
  await browser.close();
  console.log(`\n=== K-AM/2 TOPLAM: BOLUM(bulgu)=${totalF}  kart(ayri-sinif)=${totalK}  bilesen-adi(elenen)=${totalR}  hata=${errors} ===`);
  if (JSON_OUT) require('fs').writeFileSync(JSON_OUT, JSON.stringify(report, null, 2));
  process.exit(totalF > 0 || errors > 0 ? 1 : 0);
})();
