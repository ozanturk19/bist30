#!/usr/bin/env node
// tools/landscape-viewport-check.js — K-AY: TELEFONU YAN ÇEVİREN KULLANICI
// WCAG 2.1 · SC 1.3.4 "Orientation" (AA)  — içerik tek bir yöne kilitlenemez
//            SC 1.4.10 "Reflow"     (AA)  — kısa viewport'ta içerik kaybı olmamalı
//            SC 2.4.11 "Focus Not Obscured" (WCAG 2.2, AA) — odaklanan öge örtülmemeli
//
// SORU — SİTENİN TÜM MOBİL ÖLÇÜMLERİ DİKEY YAPILDI (360/390/320 GENİŞLİK,
//   HEP UZUN EKRAN). KİMSE TELEFONU YAN ÇEVİRMEDİ:
//   Yatayda genişlik sorun değil (667-812px) — YÜKSEKLİK 375px'e düşüyor.
//   Sitenin üstünde makro şerit (32px) + başlık (60px) YAPIŞKAN, altında
//   mobil alt gezinme (72px) SABİT duruyor. Bu üç bandın toplamı 375px'lik
//   bir ekranda içeriğin ~%44'ünü yiyor. Soru şu: geriye kalan pencerede
//   içerik GERÇEKTEN okunabiliyor mu, yoksa bazı ögeler HİÇBİR kaydırma
//   konumunda görünemiyor mu?
//
// ⛔ "ÖRTÜLME"Yİ TAHMİN ETMİYORUM, HESAPLIYORUM: her odaklanabilir öge için
//   onu en iyi ortaya çıkaran kaydırma konumu (targetScroll) hesaplanıyor ve
//   o konumda ögenin içerik penceresi içindeki GÖRÜNÜR YÜKSEKLİĞİ ölçülüyor.
//   Sıfırsa öge, o viewport'ta HİÇBİR ŞEKİLDE görünemez demektir.
//   (Seçilen kaydırma konumu gerçekten uygulanıp DOĞRULANIYOR — analitik
//   sonuç canlı rect ile karşılaştırılıyor.)
//
// ⛔ YAPIŞKAN BANTLARI SINIF ADINDAN DEĞİL DAVRANIŞTAN BULUYORUM: sayfa
//   kaydırıldıktan SONRA position:fixed/sticky olup viewport kenarına
//   yapışmış ve genişliğin ≥%60'ını kaplayan ögeler bant sayılır. Dar bir
//   yüzen düğme içeriği engellemez, bant değildir.
//
// BULGU SINIFLARI (tabanı SIFIR olanlar):
//   F1 KALICI ÖRTÜLME — odaklanabilir öge hiçbir kaydırma konumunda içerik
//      penceresinde görünemiyor (bant altında kalıyor).
//   F2 YATAY TAŞMA — belge yatayda kayıyor (iki yönlü kaydırma).
//   F3 ULAŞILAMAZ ODAK — odaklanabilir öge, overflow:hidden/clip taşıyan bir
//      ataşın kırpma dikdörtgeninin DIŞINDA ve o ata kaydırılamıyor.
//
// AYRI RAPORLANIR (bulgu DEĞİL, bağlam): bant yüzdesi, içerik penceresi.
//
// ⛔ ÖLÇÜM ÇÖKERSE SONUÇ "TEMİZ" DEĞİL "ÖLÇÜLEMEDİ"DİR — ayrı sayılır ve
//   çıkış kodunu bozar. [[K-AX dersi]]
//
// ⛔ YEREL AĞAÇ İKAMESİ: kuyrukta deploy edilmemiş commit varken canlı DOM
//   yerel ağacın GEÇMİŞİDİR. --local ile değişmiş static dosyalar yerelden
//   servis edilir ve İKAME GERÇEKTEN OLDU MU diye doğrulanır.
//
// Kullanım: node tools/landscape-viewport-check.js [--base=...] [--only=/a,/b]
//           [--vp=667x375,812x375] [--local] [--json=dosya] [--settle=ms]
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const arg = k => { const a = process.argv.find(s => s.startsWith('--' + k + '=')); return a ? a.split('=').slice(1).join('=') : null; };
const has = k => process.argv.includes('--' + k);
const BASE = arg('base') || 'https://borsapusula.com';
const ONLY = arg('only');
const SETTLE = Number(arg('settle') || 2600);
const LOCAL = has('local');
const SIM_INSET = arg('sim-inset');
const JSONOUT = arg('json');
const VPS = (arg('vp') || '667x375,812x375').split(',').map(s => {
  const [w, h] = s.split('x').map(Number); return { w, h, name: s };
});

const PAGES = [
  { path: '/' },
  { path: '/tarama' },
  { path: '/hisse/ASELS' },
  { path: '/ozet' },
  { path: '/karsilastir' },
  { path: '/portfolio', seedPortfolio: true },
  { path: '/gundem' },
  { path: '/bilanco-takvimi' },
  { path: '/temettu-takvimi' },
  { path: '/sektor-harita' },
  { path: '/hisseler' },
  { path: '/metodoloji' },
  { path: '/blog' },
];

const SEED = JSON.stringify([
  { id: 1, ticker: 'ASELS', lot: 100, price: 52.30, date: '2026-01-15' },
  { id: 2, ticker: 'GARAN', lot: 250, price: 118.40, date: '2026-02-03' },
  { id: 3, ticker: 'THYAO', lot: 40,  price: 281.00, date: '2026-03-11' },
  { id: 4, ticker: 'AKBNK', lot: 300, price: 64.75,  date: '2026-04-22' },
]);

const ROOT = path.resolve(__dirname, '..');

// --local: /static/** isteklerini YEREL ağaçtan karşıla. Kuyrukta deploy
// edilmemiş commit varken canlı DOM yerel ağacın GEÇMİŞİDİR; ölçüm yerelde
// yapılmalı. --sim-inset ile env(safe-area-inset-top) çentik değeri simüle
// edilir (PWA/standalone'da 0 DEĞİLDİR — tarayıcı sağlar, elle set edilemez).
function localStaticBody(pathname, simInset) {
  const rel = pathname.replace(/^\//, '').split('?')[0];
  const fp = path.join(ROOT, rel);
  if (!fp.startsWith(ROOT) || !fs.existsSync(fp) || !fs.statSync(fp).isFile()) return null;
  let body = fs.readFileSync(fp);
  if (simInset && /\.(css|js)$/.test(rel)) {
    body = Buffer.from(body.toString('utf8')
      .replace(/env\(safe-area-inset-top\s*,\s*0px\)/g, simInset)
      .replace(/env\(safe-area-inset-top\)/g, simInset), 'utf8');
  }
  return body;
}

const MEASURE = (FOCUSABLE) => {
  const vw = window.innerWidth, vh = window.innerHeight;
  const doc = document.documentElement;
  const maxScroll = Math.max(0, doc.scrollHeight - vh);

  // ── 1. YAPIŞKAN BANTLAR (kaydırılmış haldeyken ölçülür) ──────────────
  const bands = { top: 0, bottom: vh, topEls: [], bottomEls: [] };
  const alpha = bg => { const m = /rgba?\(([^)]+)\)/.exec(bg || ''); if (!m) return 0; const p = m[1].split(',').map(s => parseFloat(s)); return p.length < 4 ? 1 : (isNaN(p[3]) ? 1 : p[3]); };
  const cand = [];
  for (const el of Array.from(document.querySelectorAll('body *'))) {
    const cs = getComputedStyle(el);
    if (cs.position !== 'fixed' && cs.position !== 'sticky') continue;
    if (cs.visibility === 'hidden' || cs.display === 'none' || Number(cs.opacity) < 0.5) continue;
    if (cs.pointerEvents === 'none') continue;               // tıklamayı geçiren katman engellemez
    const r = el.getBoundingClientRect();
    if (r.height < 8 || r.width < vw * 0.6) continue;        // dar/yüzen öge bant değil
    if (alpha(cs.backgroundColor) < 0.5) continue;           // saydam bant içeriği gizlemez
    if (r.bottom <= 0 || r.top >= vh) continue;              // ekran dışı (kapalı sheet vb.)
    cand.push({ el, r, cs, sel: el.id ? '#' + el.id : (el.tagName.toLowerCase() + '.' + String(el.className || '').split(/\s+/)[0]) });
  }
  // Üst bant bir ZİNCİRDİR: makro şerit (top:0) + onun altına yapışan başlık.
  // Her turda mevcut bandın dibine değen yeni bir öge var mı diye bakılır.
  for (let pass = 0; pass < 6; pass++) {
    let grew = false;
    for (const c of cand) {
      if (c.usedT) continue;
      if (c.r.top <= bands.top + 2 && c.r.bottom > bands.top) {
        bands.top = c.r.bottom; c.usedT = true; grew = true;
        bands.topEls.push({ sel: c.sel, h: Math.round(c.r.height), pos: c.cs.position });
      }
    }
    if (!grew) break;
  }
  for (let pass = 0; pass < 6; pass++) {
    let grew = false;
    for (const c of cand) {
      if (c.usedB) continue;
      if (c.r.bottom >= bands.bottom - 2 && c.r.top < bands.bottom) {
        bands.bottom = c.r.top; c.usedB = true; grew = true;
        bands.bottomEls.push({ sel: c.sel, h: Math.round(c.r.height), pos: c.cs.position });
      }
    }
    if (!grew) break;
  }
  const win = Math.max(0, bands.bottom - bands.top);

  // ── 2. F2 YATAY TAŞMA ────────────────────────────────────────────────
  const hOverflow = doc.scrollWidth > vw + 1 ? { scrollWidth: doc.scrollWidth, vw } : null;

  // ── 3. ODAKLANABİLİR ÖGELER — belge koordinatında ────────────────────
  const sy = window.scrollY;
  // ⛔ KAPALI <details> BİR KAPSAM YALANIDIR: Chromium kapalı bir <details>'in
  //   çocuklarını `content-visibility:hidden` ile atlar — ÇİZMEZ, odaklanmaz,
  //   ama getBoundingClientRect() HÂLÂ bir kutu döndürür (belgenin dışında bile).
  //   Filtrelenmezse dedektör "belge sonunun altında 23 bağlantı var" diye
  //   yalan söyler. [[reference_canli_dom_dedektoru_kapali_katmana_kordur]]
  const skipped = { closedDetails: 0, invisible: 0, chrome: 0, innerScroll: 0 };
  const bandEls = [];
  for (const c of cand) if (c.usedT || c.usedB) bandEls.push(c.el);
  const focusables = Array.from(document.querySelectorAll(FOCUSABLE)).filter(e => {
    if (!e.getClientRects().length) { skipped.invisible++; return false; }
    const cs = getComputedStyle(e);
    if (cs.visibility === 'hidden' || cs.display === 'none') { skipped.invisible++; return false; }
    if (typeof e.checkVisibility === 'function' &&
        !e.checkVisibility({ contentVisibilityAuto: true, opacityProperty: true, visibilityProperty: true })) {
      skipped.invisible++; return false;
    }
    const d = e.closest('details:not([open])');
    if (d && !e.closest('summary')) { skipped.closedDetails++; return false; }
    // Bandın KENDİ içindeki ögeler "örtülü" sayılmaz — bant zaten onlar.
    if (bandEls.some(b => b.contains(e))) { skipped.chrome++; return false; }
    // Kendi kaydırma kabı olan öge sayfa-kaydırma modeliyle ölçülemez.
    let p2 = e.parentElement, hop = 0;
    while (p2 && p2 !== document.body && hop++ < 10) {
      const pcs = getComputedStyle(p2);
      if (/auto|scroll/.test(pcs.overflowY) && p2.scrollHeight > p2.clientHeight + 2) { skipped.innerScroll++; return false; }
      p2 = p2.parentElement;
    }
    return true;
  });
  const items = focusables.map((e, n) => {
    const r = e.getBoundingClientRect();
    return {
      n,
      docTop: r.top + sy, docBottom: r.bottom + sy, h: r.height,
      name: (e.getAttribute('aria-label') || e.textContent || e.getAttribute('title') || '').replace(/\s+/g, ' ').trim().slice(0, 52),
      sel: e.id ? '#' + e.id : (e.className ? e.tagName.toLowerCase() + '.' + String(e.className).split(/\s+/)[0] : e.tagName.toLowerCase()),
    };
  });

  // F1: her öge için en iyi kaydırma konumunda görünür yükseklik
  const obscured = [];
  for (const it of items) {
    if (it.h <= 0) continue;
    // Odaklanınca görünür hale gelen "atla" bağlantıları belge dışındadır —
    // analitik model onları göremez, AYRI sayılır (bulgu değil).
    if (it.docBottom <= 0) continue;
    const want = Math.min(Math.max(0, it.docTop - bands.top), maxScroll);
    const top = it.docTop - want, bottom = it.docBottom - want;
    const visible = Math.max(0, Math.min(bottom, bands.bottom) - Math.max(top, bands.top));
    if (visible <= 0) obscured.push({ ...it, want, bandTop: bands.top, bandBottom: bands.bottom });
  }

  // ── 4. F3 ULAŞILAMAZ ODAK (kırpma dikdörtgeni dışında) ───────────────
  const clipped = [];
  for (const e of focusables) {
    const r = e.getBoundingClientRect();
    let p = e.parentElement, hops = 0;
    while (p && p !== document.body && hops++ < 12) {
      const cs = getComputedStyle(p);
      const clipsY = /hidden|clip/.test(cs.overflowY), clipsX = /hidden|clip/.test(cs.overflowX);
      if (clipsY || clipsX) {
        const pr = p.getBoundingClientRect();
        const outY = clipsY && (r.bottom <= pr.top + 1 || r.top >= pr.bottom - 1);
        const outX = clipsX && (r.right <= pr.left + 1 || r.left >= pr.right - 1);
        const canScroll = (clipsY && p.scrollHeight > p.clientHeight + 2) || (clipsX && p.scrollWidth > p.clientWidth + 2);
        if ((outY || outX) && !canScroll) {
          clipped.push({
            name: (e.getAttribute('aria-label') || e.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 48),
            sel: e.id ? '#' + e.id : e.tagName.toLowerCase() + '.' + String(e.className || '').split(/\s+/)[0],
            clipper: p.id ? '#' + p.id : '.' + String(p.className || '').split(/\s+/)[0],
            axis: outY ? 'Y' : 'X',
          });
          break;
        }
      }
      p = p.parentElement;
    }
  }

  return {
    vw, vh, maxScroll,
    band: { top: Math.round(bands.top), bottom: Math.round(bands.bottom), win: Math.round(win),
            pct: Math.round((vh - win) / vh * 100), topEls: bands.topEls, bottomEls: bands.bottomEls },
    hOverflow, nFocusable: items.length, obscured, clipped, skipped,
  };
};

const FOCUSABLE = 'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';

async function run() {
  const browser = await chromium.launch();
  const pages = ONLY ? PAGES.filter(p => ONLY.split(',').includes(p.path)) : PAGES;
  const subUsed = new Set();
  const report = [];
  const tot = { obscured: 0, hOverflow: 0, clipped: 0, unmeasured: 0 };

  for (const P of pages) {
    for (const VP of VPS) {
      const ctx = await browser.newContext({
        viewport: { width: VP.w, height: VP.h },
        isMobile: true, hasTouch: true, deviceScaleFactor: 2,
      });
      const page = await ctx.newPage();
      if (P.seedPortfolio) {
        await page.addInitScript(seed => { try { localStorage.setItem('bp_portfolio', seed); } catch (e) {} }, SEED);
      }
      if (LOCAL) {
        await page.route('**/static/**', async route => {
          const u = new URL(route.request().url());
          const body = localStaticBody(u.pathname, SIM_INSET);
          if (!body) return route.continue();
          subUsed.add(u.pathname);
          const ct = u.pathname.endsWith('.css') ? 'text/css'
                   : u.pathname.endsWith('.js') ? 'application/javascript'
                   : u.pathname.endsWith('.json') ? 'application/json'
                   : u.pathname.endsWith('.svg') ? 'image/svg+xml' : 'application/octet-stream';
          return route.fulfill({ status: 200, contentType: ct + '; charset=utf-8', body });
        });
      }
      const out = { path: P.path, vp: VP.name };
      try {
        await page.goto(BASE + P.path, { waitUntil: 'domcontentloaded', timeout: 45000 });
        await page.waitForTimeout(SETTLE);
        // Yapışkan bantlar ancak kaydırıldıktan SONRA yapışır → önce kaydır.
        await page.evaluate(() => window.scrollTo(0, Math.min(700, document.documentElement.scrollHeight)));
        await page.waitForTimeout(450);
        const m = await page.evaluate(MEASURE, FOCUSABLE);
        Object.assign(out, m);

        // ── ANALİTİK SONUCU CANLI OLARAK DOĞRULA ───────────────────────
        // F1 bulgularının ilk 3'ü gerçekten kaydırılıp rect ile sınanır.
        out.verified = [];
        for (const o of (m.obscured || []).slice(0, 3)) {
          const v = await page.evaluate(async ({ want, n, FOCUSABLE }) => {
            window.scrollTo(0, want);
            await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
            const els = Array.from(document.querySelectorAll(FOCUSABLE)).filter(e => {
              if (!e.getClientRects().length) return false;
              const cs = getComputedStyle(e);
              return cs.visibility !== 'hidden' && cs.display !== 'none';
            });
            const e = els[n]; if (!e) return { ok: false, why: 'öge kayboldu' };
            const r = e.getBoundingClientRect();
            return { ok: true, top: Math.round(r.top), bottom: Math.round(r.bottom), scrollY: Math.round(window.scrollY) };
          }, { want: o.want, n: o.n, FOCUSABLE });
          out.verified.push({ sel: o.sel, name: o.name, ...v });
        }

        tot.obscured += (m.obscured || []).length;
        tot.clipped += (m.clipped || []).length;
        if (m.hOverflow) tot.hOverflow++;
      } catch (e) {
        out.error = String(e.message || e).slice(0, 160);
        tot.unmeasured++;
      }
      report.push(out);
      await ctx.close();
    }
  }
  await browser.close();

  // ── ÇIKTI ────────────────────────────────────────────────────────────
  for (const r of report) {
    if (r.error) { console.log(`OLCULEMEDI ${r.path} @${r.vp} — ${r.error}`); continue; }
    const b = r.band;
    console.log(`${r.path} @${r.vp}  bant: ust=${b.top}px alt=${r.vh - b.bottom}px  icerik=${b.win}px (%${100 - b.pct})  odaklanabilir=${r.nFocusable}  F1=${r.obscured.length} F2=${r.hOverflow ? 1 : 0} F3=${r.clipped.length}`);
    if (b.topEls.length) console.log(`    ust bant: ${b.topEls.map(e => e.sel + '(' + e.h + 'px,' + e.pos + ')').join(' + ')}`);
    if (b.bottomEls.length) console.log(`    alt bant: ${b.bottomEls.map(e => e.sel + '(' + e.h + 'px,' + e.pos + ')').join(' + ')}`);
    const sk = r.skipped || {};
    console.log(`    kapsam disi: kapali-details=${sk.closedDetails || 0} gorunmez=${sk.invisible || 0} bant-ici=${sk.chrome || 0} ic-kaydirma=${sk.innerScroll || 0}`);
    if (r.hOverflow) console.log(`    F2 YATAY TASMA: scrollWidth=${r.hOverflow.scrollWidth} > ${r.hOverflow.vw}`);
    for (const o of r.obscured.slice(0, 6)) console.log(`    F1 ORTULU: ${o.sel} "${o.name}" (docTop=${Math.round(o.docTop)} en iyi scroll=${Math.round(o.want)})`);
    for (const v of (r.verified || [])) console.log(`      dogrulama: ${v.sel} -> ${v.ok ? `top=${v.top} bottom=${v.bottom} @scrollY=${v.scrollY}` : v.why}`);
    for (const c of r.clipped.slice(0, 6)) console.log(`    F3 KIRPILMIS: ${c.sel} "${c.name}" <- ${c.clipper} (${c.axis})`);
  }
  if (LOCAL) {
    console.log(`\nIKAME GUARD: yerelden servis edilen static dosya=${subUsed.size}${SIM_INSET ? ' (sim-inset=' + SIM_INSET + ')' : ''}`);
    if (!subUsed.size) { console.log('HATA: --local verildi ama HICBIR ikame olmadi — olcum canli agaci olcuyor.'); process.exitCode = 3; }
  }
  console.log(`\nTOPLAM: F1-kalici-ortulme=${tot.obscured} F2-yatay-tasma=${tot.hOverflow} F3-ulasilamaz=${tot.clipped} OLCULEMEDI=${tot.unmeasured}`);
  if (JSONOUT) fs.writeFileSync(JSONOUT, JSON.stringify(report, null, 2));
  if (tot.unmeasured) process.exitCode = 3;
}
run().catch(e => { console.error(e); process.exit(1); });
