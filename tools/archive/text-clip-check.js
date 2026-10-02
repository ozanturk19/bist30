#!/usr/bin/env node
// tools/text-clip-check.js — K-M: ELEMAN İÇİ metin kırpılması dedektörü (canlı)
//
// Neden var: tools/mobile-overflow-check.mjs YALNIZ sayfa düzeyi yatay taşmayı
// ölçer (documentElement.scrollWidth > innerWidth). Bir kapsayıcı `overflow:hidden`
// ise sayfa taşmaz — metin SESSİZCE kesilir ve harness yeşil kalır. Bu betik o
// boşluğu kapatır: metin DÜĞÜMÜNÜN kendi kutusunu (Range.getClientRects) en yakın
// kırpan atanın client kutusuyla karşılaştırır.
//
// Sınıflandırma:
//   HARD  — kırpılıyor, hiçbir görsel gösterge YOK (ne ellipsis ne line-clamp) →
//           kullanıcı metnin eksik olduğunu ANLAYAMAZ. Gerçek bug.
//   ELLIP — ellipsis/line-clamp var (bilgi kaybı sinyalleniyor) → tasarım kararı,
//           yalnız raporlanır.
//   PLACE — input/textarea placeholder'ı alana sığmıyor (canvas ölçümü).
//
// Kullanım: node tools/text-clip-check.js [--base=https://borsapusula.com] [--w=375]
// ⛔ ÖLÜ ROTA BİR KAPSAM YALANIDIR (21.09, K-S turunda yakalandı)
// Bu betiğin sayfa listesinde `/portfoy` yazıyordu; gerçek rota `/portfolio`.
// 404 sayfası da 'networkidle' ile sorunsuz YÜKLENİR, üstelik header/footer'ı
// taşır — denetçi hiçbir ihlal görmez ve sayfayı "TEMİZ" raporlar. Sitenin en
// etkileşimli sayfalarından biri böylece hiç ölçülmemiş oldu. Bu yüzden artık
// HTTP durumu kontrol edilir: >=400 dönen rota SESSİZCE GEÇMEZ, ihlal sayılır.
const { chromium } = require('playwright');

// ⚠️ BEKLENEN 4xx: `/profil` tokensiz gelindiginde BILEREK 404 doner ama sitenin
// markali hata varyantini RENDER EDER (app.py profil_page). Yani olu rota degil —
// ama olculen sayfa da adi gecen sayfa DEGILDIR: token'li gercek profil formu bu
// turda hic olculmemistir. Bu yuzden beklenen-4xx listesi olcumu SURDURUR, fakat
// hangi varyantin olculdugunu acikca yazar.
const EXPECT_4XX = new Set(['/profil']);
const BASE = (process.argv.find(a => a.startsWith('--base=')) || '').split('=')[1] || 'https://borsapusula.com';
/* K-AE (21.09): TEK GENISLIK BIR KAPSAM YALANIYDI. Bu betik yalniz 375'te
   kosuyordu; `/bilanco-takvimi` donem basligindaki "43 Bozuldu" cipi @320px'te
   ELLIPSIS OLMADAN kesiliyor, @375'te ise TAM SIGIYORDU -- yani kusur olculen
   tek genisligin ALTINDA yasiyordu. Sayfa duzeyi harness'i (mobile-overflow-
   check.mjs) de goremez: kirpan kutu (`overflow:hidden`) tasmayi YUTAR, sayfa
   tasmaz. Iki dedektorun arasindaki acikti. Artik varsayilan 320 VE 375
   (WCAG 1.4.10'un tanimli tabani + yaygin telefon); `--w=375` verilirse
   davranis AYNEN eskisi gibi tek genisliktir. */
const WIDTHS = ((process.argv.find(a => a.startsWith('--w=')) || '').split('=')[1] || '320,375')
  .split(',').map(n => parseInt(n, 10)).filter(n => n > 0);
const ONLY = (process.argv.find(a => a.startsWith('--only=')) || '').split('=')[1] || '';

const PAGES = [
  '/', '/ozet', '/tarama', '/gundem', '/hisseler', '/sektor-harita',
  '/hisse/ASELS', '/hisse/GARAN', '/karsilastir', '/portfolio',
  '/bilanco-takvimi', '/temettu-takvimi', '/blog', '/blog/rsi-gostergesi-nedir',
  '/metodoloji', '/hakkinda', '/iletisim', '/profil', '/yasal', '/gizlilik',
];

const PROBE = () => {
  const out = [];
  const sel = (el) => {
    if (!el) return '?';
    let s = el.tagName.toLowerCase();
    if (el.id) s += '#' + el.id;
    if (el.className && typeof el.className === 'string') s += '.' + el.className.trim().split(/\s+/).slice(0, 3).join('.');
    return s;
  };
  // sr-only (1x1 clip) ve ANIMASYONLU kaydırıcı (marquee/ticker) kasıtlıdır → elenir
  const isSrOnly = (el) => {
    let p = el;
    while (p && p !== document.body) {
      const cs = getComputedStyle(p);
      if ((cs.clip && cs.clip !== 'auto') || cs.clipPath === 'inset(50%)') return true;
      const r = p.getBoundingClientRect();
      if (r.width <= 1.5 && r.height <= 1.5 && p.textContent.trim().length > 2) return true;
      p = p.parentElement;
    }
    return false;
  };
  const animatedUnder = (clipper, node) => {
    let p = node.parentElement;
    while (p && p !== clipper.parentElement) {
      const cs = getComputedStyle(p);
      if (cs.animationName !== 'none' || (cs.transitionProperty || '').includes('transform')) return true;
      p = p.parentElement;
    }
    return false;
  };
  const clipperOf = (node) => {
    // ÖNEMLİ: kaydırılabilir (auto/scroll) bir ata ÖNCE gelirse içerik ERİŞİLEBİLİR →
    // kırpılma değil. body/html kırpıcı sayılmaz (sayfa düzeyi taşma ayrı harness'ta:
    // mobile-overflow-check.mjs) — `body{overflow-x:hidden}` viewport'a PROPAGATE olur.
    let p = node.parentElement;
    while (p && p !== document.body && p !== document.documentElement) {
      const cs = getComputedStyle(p);
      const ox = cs.overflowX, oy = cs.overflowY;
      if (ox === 'auto' || ox === 'scroll' || oy === 'auto' || oy === 'scroll') return null;
      if (ox === 'hidden' || ox === 'clip' || oy === 'hidden' || oy === 'clip') return { el: p, cs };
      p = p.parentElement;
    }
    return null;
  };
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = walker.nextNode())) {
    const txt = n.nodeValue.replace(/\s+/g, ' ').trim();
    if (!txt) continue;
    const parent = n.parentElement;
    if (!parent) continue;
    const pcs = getComputedStyle(parent);
    if (pcs.display === 'none' || pcs.visibility === 'hidden' || parent.closest('script,style,noscript,template')) continue;
    // ATA zinciri görünürlüğü: display:none ATA + content-visibility (checkVisibility)
    if (parent.checkVisibility && !parent.checkVisibility({ checkVisibilityCSS: true, contentVisibilityAuto: true })) continue;
    // KAPALI <details> içeriği kasıtlı gizlidir; Chromium bu düğümlere yine de
    // kutu döndürür (::details-content / content-visibility:hidden) → sahte kırpılma
    const dt = parent.closest('details');
    if (dt && !dt.open && !parent.closest('summary')) continue;
    if (isSrOnly(parent)) continue;
    const c = clipperOf(n);
    if (!c) continue;
    if (animatedUnder(c.el, n)) continue;
    const ccs = c.cs, ce = c.el;
    const cr = ce.getBoundingClientRect();
    const bl = parseFloat(ccs.borderLeftWidth) || 0, bt = parseFloat(ccs.borderTopWidth) || 0;
    const L = cr.left + bl, T = cr.top + bt, R = L + ce.clientWidth, B = T + ce.clientHeight;
    if (ce.clientWidth === 0 || ce.clientHeight === 0) continue;
    /* ⛔ K-R (21.09) — BESINCI SAHTE-POZITIF SINIFI: DONDURULMUS/DONUSTURULMUS ATA.
       `getClientRects()` viewport uzayinda (transform UYGULANMIS) AABB verir;
       `clientHeight/clientWidth` ise ogenin KENDI yerel uzayindadir. Ikisi
       karsilastirilamaz. Anasayfadaki `.da-scard` kartlari Data-Art efekti
       olarak ~1.3 derece dondurulmus: matrix(0.999743, 0.0226873, ...). 13px
       yuksekligindeki bir satirin AABB'si 170px genislikte 16.86'ya cikiyor ve
       3.9px "kirpilma" gibi gorunuyordu. Sapma METNIN GENISLIGIYLE orantili —
       en uzun sirket adi en buyuk sahte tasmayi uretiyordu (Tupras 3.9 yakalandi,
       kisa isimler 0.3 ile esigin altinda kaldi), yani sinif tutarli bir yanilgi.
       Curutme: `scrollHeight === clientHeight` (13 === 13) -> tasan icerik YOK.
       Donusmus ata varsa Range karsilastirmasi birakilir, transform'dan
       BAGIMSIZ olan scroll/client olcusune dusulur. */
    let xf = null;
    { let a = parent;
      while (a && a !== document.documentElement) {
        const acs = getComputedStyle(a);
        if (acs.transform && acs.transform !== 'none') { xf = sel(a); break; }
        a = a.parentElement; } }
    if (xf) {
      const realY = ce.scrollHeight > ce.clientHeight + 1;
      const realX = ce.scrollWidth > ce.clientWidth + 1;
      if (!realY && !realX) continue;   /* gercek tasma yok -> donme artefakti */
    }
    const rng = document.createRange(); rng.selectNodeContents(n);
    const rects = Array.from(rng.getClientRects()).filter(r => r.width > 0 && r.height > 0);
    if (!rects.length) continue;
    let ovR = 0, ovB = 0, ovL = 0;
    for (const r of rects) {
      ovR = Math.max(ovR, r.right - R);
      ovL = Math.max(ovL, L - r.left);
      ovB = Math.max(ovB, r.bottom - B);
    }
    const scrollableX = ccs.overflowX === 'auto' || ccs.overflowX === 'scroll';
    const scrollableY = ccs.overflowY === 'auto' || ccs.overflowY === 'scroll';
    const hx = (ovR > 2 || ovL > 2) && !scrollableX;
    const hy = ovB > 2 && !scrollableY;
    if (!hx && !hy) continue;
    const tcs = getComputedStyle(parent);
    const hasEllip = tcs.textOverflow === 'ellipsis' || ccs.textOverflow === 'ellipsis';
    const clamp = tcs.webkitLineClamp && tcs.webkitLineClamp !== 'none';
    out.push({
      kind: (hasEllip && hx) || clamp ? 'ELLIP' : 'HARD',
      text: txt.slice(0, 60),
      node: sel(parent),
      clipper: sel(ce),
      ovR: +ovR.toFixed(1), ovL: +ovL.toFixed(1), ovB: +ovB.toFixed(1),
      title: parent.getAttribute('title') || (ce.getAttribute && ce.getAttribute('title')) || '',
    });
  }
  // placeholder ölçümü
  const cv = document.createElement('canvas'); const ctx = cv.getContext('2d');
  document.querySelectorAll('input[placeholder],textarea[placeholder]').forEach(el => {
    const ph = el.getAttribute('placeholder'); if (!ph) return;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || !el.offsetParent) return;
    ctx.font = `${cs.fontStyle} ${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
    const wTxt = ctx.measureText(ph).width;
    const avail = el.clientWidth - (parseFloat(cs.paddingLeft) || 0) - (parseFloat(cs.paddingRight) || 0);
    if (avail > 0 && wTxt > avail + 1) {
      out.push({ kind: 'PLACE', text: ph.slice(0, 60), node: sel(el), clipper: '(placeholder)', ovR: +(wTxt - avail).toFixed(1), ovL: 0, ovB: 0, title: '' });
    }
  });
  return out;
};

/* K-T (21.09): PROBE artik modul olarak da disari verilir — sekme denetcisi
   (tools/tab-panel-check.js) ayni olcutu yeniden turetmesin diye. Dogrudan
   calistirildiginda davranis AYNEN korunur (require.main kapisi). */
module.exports = { PROBE };
if (require.main !== module) return;

(async () => {
  const browser = await chromium.launch();
  const pages = ONLY ? ONLY.split(',') : PAGES;
  let grandHard = 0, grandPlace = 0, grandDead = 0;
  for (const W of WIDTHS) {
  const ctx = await browser.newContext({ viewport: { width: W, height: 812 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
  let hard = 0, ellip = 0, place = 0;
  const deadRoutes = [];
  console.log(`\n########## GENISLIK ${W}px ##########`);
  for (const p of pages) {
    const page = await ctx.newPage();
    try {
      const _resp = await page.goto(BASE + p, { waitUntil: 'networkidle', timeout: 45000 });
      if (_resp && _resp.status() >= 400) {
        if (EXPECT_4XX.has(p)) { console.log(`bilgi  ${p}  HTTP ${_resp.status()} — BEKLENEN hata varyanti olculuyor (gercek sayfa degil)`); }
        else { console.log(`OLU-ROTA  ${p}  HTTP ${_resp.status()} — bu rota HIC olculmuyor`); deadRoutes.push(`${p} HTTP ${_resp.status()}`); await page.close(); continue; }
      }
      await page.waitForTimeout(1200);
      const res = await page.evaluate(PROBE);
      const h = res.filter(r => r.kind === 'HARD'), e = res.filter(r => r.kind === 'ELLIP'), pl = res.filter(r => r.kind === 'PLACE');
      hard += h.length; ellip += e.length; place += pl.length;
      console.log(`\n=== ${p} — HARD:${h.length} ELLIP:${e.length} PLACE:${pl.length}`);
      for (const r of [...h, ...pl]) console.log(`  [${r.kind}] ${r.node} < ${r.clipper}  R+${r.ovR} B+${r.ovB} L+${r.ovL} ${r.title ? '(title var)' : ''}\n        "${r.text}"`);
      if (process.env.SHOW_ELLIP) for (const r of e) console.log(`  [ELLIP] ${r.node} < ${r.clipper} R+${r.ovR} B+${r.ovB}\n        "${r.text}"`);
    } catch (err) {
      console.log(`\n=== ${p} — HATA: ${err.message.split('\n')[0]}`);
    }
    await page.close();
  }
  console.log(`\nTOPLAM @${W}px — HARD:${hard} ELLIP:${ellip} PLACE:${place}` + (deadRoutes.length ? `  OLU-ROTA:${deadRoutes.length} (${deadRoutes.join(', ')})` : ''));
  grandHard += hard; grandPlace += place; grandDead += deadRoutes.length;
  await ctx.close();
  }
  console.log(`\n=== GENEL TOPLAM (${WIDTHS.join('/')}px) — HARD:${grandHard} PLACE:${grandPlace} OLU-ROTA:${grandDead} ===`);
  await browser.close();
  process.exit(grandHard + grandPlace + grandDead > 0 ? 1 : 0);
})();
