#!/usr/bin/env node
// tools/overlay-layer-check.js — K-R: AÇILABİLİR KATMAN denetimi (canlı)
//
// NEDEN AYRI BİR ÖLÇÜM
// --------------------
// K-I/K-M/K-N/K-O/K-P/K-Q ve dokunma-hedefi denetçilerinin HEPSİ görünürlük
// filtresiyle başlar: `rect 0x0` veya `display:none` düğüm elenir. Bu, tüm
// açılabilir katmanları (arama overlay'i, nav "Daha" menüsü, mobil sheet,
// cloud modal, kapalı <details>) ölçümün DIŞINDA bırakır.
// K-Q'nun kendi kapanış notu bunu itiraf ediyor:
//   "Ölçülmeyen: overlay/modal içindeki alanlar — #bpSearchInput kapalı
//    katmanda (rect 0x0), 12 taramanın hiçbirinde görünmedi."
// Bu betik o kapsamı açar: katmanı GERÇEKTEN açar, sonra aynı üç doğrulanmış
// ölçütü çalıştırır.
//
// YÖNTEM: TABAN → AÇ → DELTA
// --------------------------
// Denetçiler tüm sayfayı tarar. Katman kapalıyken bir kez koşturulur (taban),
// katman açıkken ikinci kez (sonra). DELTA = yalnızca katmanın getirdiği
// ihlaller. Taban zaten 0 olduğu için delta doğrudan bulgudur; taban 0
// değilse de yöntem bozulmaz (fark alınır), ve tabanın kendisi raporlanır.
//
// Kullanım: node tools/overlay-layer-check.js [--base=...] [--w=1280] [--only=/tarama]
// ⛔ ÖLÜ ROTA BİR KAPSAM YALANIDIR (21.09, K-S turunda yakalandı)
// Bu betiğin sayfa listesinde `/portfoy` yazıyordu; gerçek rota `/portfolio`.
// 404 sayfası da 'networkidle' ile sorunsuz YÜKLENİR, üstelik header/footer'ı
// taşır — denetçi hiçbir ihlal görmez ve sayfayı "TEMİZ" raporlar. Sitenin en
// etkileşimli sayfalarından biri böylece hiç ölçülmemiş oldu. Bu yüzden artık
// HTTP durumu kontrol edilir: >=400 dönen rota SESSİZCE GEÇMEZ, ihlal sayılır.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// ⛔ BU HARNESS'IN SAHTE-POZITIF SINIFI: ACIK KATMAN ARKA PLANIN ISABET TESTINI
// ZEHIRLER (21.09, K-S turunda yakalandi). K-L olcutu `elementFromPoint` ile
// calisir; tam ekran bir overlay acikken SAYFADAKI HER arka plan ogesi "ulasilamaz"
// dondurur. Delta yontemi bunu normalde sifirlar (taban==sonra) — AMA oge tabandan
// SONRA gorunur hale geliyorsa (async render) tabanda yoktur, sonrada vardir ve
// YENI IHLAL diye raporlanir. Canli ornek: /portfolio `.ls-warning-close` (13.3x16)
// iki katmanda da "yeni ihlal" gorundu; katman KAPALIYKEN olculunce KL bad=0 —
// 44x44 halosu 5/5 isabet ediyor, yani belgelenmis muafiyet gecerli.
// COZUM: taban IKI KEZ alinir (yukleme sonrasi + katmani ACMADAN hemen once) ve
// birlesimi kullanilir; gec gelen arka plan ogeleri boylece "yeni" sayilmaz.
const BASE = (process.argv.find(a => a.startsWith('--base=')) || '').split('=')[1] || 'https://borsapusula.com';
const W = parseInt((process.argv.find(a => a.startsWith('--w=')) || '').split('=')[1] || '1280', 10);
const ONLY = (process.argv.find(a => a.startsWith('--only=')) || '').split('=')[1] || '';

const read = (f) => fs.readFileSync(path.join(__dirname, f), 'utf8');
const KP = read('live-contrast-check.js');   // K-P metin kontrastı
const KQ = read('nontext-contrast-check.js'); // K-Q metin-dışı kontrast
const KL = read('tap-target-check.js');       // K-L dokunma hedefi
const KO = read('focus-visible-check.js');    // K-O klavye odak halkasi
// K-M metin kirpilmasi: text-clip-check.js bir Playwright harness'i; icindeki
// PROBE fonksiyonunu ayiklayip page.evaluate'e veriyoruz (tek kaynak korunur).
const KM = (() => {
  const src = read('text-clip-check.js');
  const i = src.indexOf('const PROBE = () => {');
  const j = src.indexOf('\n};', i);
  if (i < 0 || j < 0) throw new Error('text-clip-check.js PROBE ayiklanamadi');
  return '(' + src.slice(i + 'const PROBE = '.length, j + 2) + ')()';
})();

// ── Katman açma reçeteleri ────────────────────────────────────────────────
// Her reçete: { ad, sayfalar, aç(page), minW/maxW }
const LAYERS = [
  {
    name: 'arama-overlay (boş)',
    pages: ['/', '/tarama', '/hisse/ASELS', '/portfolio'],
    open: async (page) => {
      await page.evaluate(() => { if (window.bpOpenSearch) window.bpOpenSearch(); });
      await page.waitForTimeout(500);
    },
  },
  {
    name: 'arama-overlay (sonuçlu)',
    pages: ['/'],
    open: async (page) => {
      await page.evaluate(() => { if (window.bpOpenSearch) window.bpOpenSearch(); });
      await page.waitForTimeout(600);
      await page.fill('#bpSearchInput', 'A').catch(() => {});
      await page.waitForTimeout(900);
    },
  },
  {
    name: 'nav-daha-menusu',
    pages: ['/', '/tarama', '/hisse/ASELS'],
    minW: 1000,
    open: async (page) => {
      await page.click('.bp-nav-more-btn', { timeout: 3000 }).catch(() => {});
      await page.waitForTimeout(400);
    },
  },
  {
    name: 'mobil-sheet',
    pages: ['/', '/tarama', '/hisse/ASELS'],
    maxW: 768,
    open: async (page) => {
      await page.evaluate(() => { if (window.toggleMbnSheet) window.toggleMbnSheet(); });
      await page.waitForTimeout(400);
    },
  },
  {
    name: 'cloud-modal',
    pages: ['/portfolio'],
    open: async (page) => {
      await page.evaluate(() => {
        if (window.openCloudSync) window.openCloudSync();
        else { const m = document.getElementById('cloudModal'); if (m) m.style.display = 'flex'; }
      });
      await page.waitForTimeout(400);
    },
  },
  {
    name: 'kapali-details',
    pages: ['/gundem', '/ozet', '/hisse/ASELS', '/hisse/GARAN'],
    open: async (page) => {
      const n = await page.evaluate(() => {
        const d = [...document.querySelectorAll('details:not([open])')];
        d.forEach(x => { x.open = true; });
        return d.length;
      });
      await page.waitForTimeout(400);
      return n;
    },
  },
];

const runProbe = async (page, src) => {
  const raw = await page.evaluate(src);
  return typeof raw === 'string' ? JSON.parse(raw) : raw;
};

// KP/KQ: HARD listesi; KL: agg listesi. Ortak anahtar üret.
const keysKP = (r) => (r.HARD || []).map(v => `KP|${v.sig}|${v.ratio}|${(v.text || '').slice(0, 24)}`);
const keysKQ = (r) => (r.HARD || []).map(v => `KQ|${v.sig}|${v.score !== undefined ? v.score : v.best}`);
const keysKL = (r) => (r.agg || []).flatMap(v => Array.from({ length: v.n }, (_, i) => `KL|${v.sel}|${v.w}x${v.h}|${i}`));
// K-O: A = hic gorsel degisiklik yok, B = halka <=1 kenarda gorunuyor
const keysKO = (r) => [
  ...(r.Aagg || []).flatMap(v => Array.from({ length: v.n }, (_, i) => `KO-A|${v.k}|${i}`)),
  ...(r.Bagg || []).flatMap(v => Array.from({ length: v.n }, (_, i) => `KO-B|${v.k}|${i}`)),
];
// K-M: yalniz HARD (gostergesiz kirpilma) + PLACE; ELLIP kasitlidir
const keysKM = (r) => (r || []).filter(v => v.kind === 'HARD' || v.kind === 'PLACE')
  .map(v => `KM|${v.kind}|${v.node}|${(v.text || '').slice(0, 30)}`);

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: W, height: 900 } });
  const results = [];
  let totalFind = 0;

  for (const layer of LAYERS) {
    if (layer.minW && W < layer.minW) continue;
    if (layer.maxW && W > layer.maxW) continue;
    for (const p of layer.pages) {
      if (ONLY && p !== ONLY) continue;
      const page = await ctx.newPage();
      try {
        const _resp = await page.goto(BASE + p, { waitUntil: 'networkidle', timeout: 45000 });
        if (_resp && _resp.status() >= 400) { console.log(`${p} [${layer.name}] OLU-ROTA HTTP ${_resp.status()} — bu katman HIC olculmuyor`); totalFind++; await page.close(); continue; }
        await page.waitForTimeout(1200);

        /* ⛔ K-O'nun BELGELENMEMIS ON KOSULU: `:focus-visible` tarayicinin SON
           GIRIS MODUNA baglidir. Fare tiklamasindan sonra `el.focus()` cagrisi
           `:focus-visible`i ESLESTIRMEZ, yani her odak halkasi "yok" gorunur.
           Canli olcum (/, 67 aday, 4/4 deterministik):
             temiz yukleme -> A=0 · fare tiklamasi -> A=55 · Tab -> A=0 ·
             tekrar fare -> A=55.
           Katmani ACAN her tiklama olcumu bu sekilde zehirler. Her K-O
           kosumundan once tarayiciyi KLAVYE moduna geri al. */
        const probeAll = async () => ({
          KP: await runProbe(page, KP),
          KQ: await runProbe(page, KQ),
          KL: await runProbe(page, KL),
          KO: await (async () => { await page.keyboard.press('Tab'); await page.waitForTimeout(80); return runProbe(page, KO); })(),
          KM: await runProbe(page, KM),
        });
        const base = await probeAll();
        // ikinci taban: gec render olan arka plan ogeleri (ornegin /portfolio
        // localStorage uyarisi) icin — bkz. yukaridaki sahte-pozitif notu
        await page.waitForTimeout(1500);
        const base2 = await probeAll();
        const opened = await layer.open(page);

        // katman gerçekten açıldı mı? görünür düğüm sayısı artmalı
        const grew = await page.evaluate(() => {
          let n = 0;
          document.querySelectorAll('*').forEach(e => { const r = e.getBoundingClientRect(); if (r.width > 0 && r.height > 0) n++; });
          return n;
        });

        const after = await probeAll();

        const bk = new Set([...keysKP(base.KP), ...keysKQ(base.KQ), ...keysKL(base.KL),
          ...keysKO(base.KO), ...keysKM(base.KM),
          ...keysKP(base2.KP), ...keysKQ(base2.KQ), ...keysKL(base2.KL),
          ...keysKO(base2.KO), ...keysKM(base2.KM)]);
        const ak = [...keysKP(after.KP), ...keysKQ(after.KQ), ...keysKL(after.KL),
          ...keysKO(after.KO), ...keysKM(after.KM)];
        const delta = ak.filter(k => !bk.has(k));

        const rec = {
          page: p, layer: layer.name, w: W, visNodes: grew, opened: opened ?? null,
          baseCounts: { KP: base.KP.hardCount, KQ: base.KQ.hardCount, KL: base.KL.bad,
            KO: base.KO.A + base.KO.B, KM: keysKM(base.KM).length },
          afterCounts: { KP: after.KP.hardCount, KQ: after.KQ.hardCount, KL: after.KL.bad,
            KO: after.KO.A + after.KO.B, KM: keysKM(after.KM).length },
          delta,
          deltaDetail: {
            KP: (after.KP.HARD || []).filter(v => !bk.has(`KP|${v.sig}|${v.ratio}|${(v.text || '').slice(0, 24)}`)),
            KQ: (after.KQ.HARD || []).filter(v => !bk.has(`KQ|${v.sig}|${v.score !== undefined ? v.score : v.best}`)),
            KL: (after.KL.agg || []).filter(v => ![...(base.KL.agg || []), ...(base2.KL.agg || [])].some(b => b.sel === v.sel && b.n >= v.n)),
            KO: [
              ...(after.KO.Aagg || []).filter(v => ![...(base.KO.Aagg || []), ...(base2.KO.Aagg || [])].some(b => b.k === v.k && b.n >= v.n)).map(v => ({ ...v, tip: 'A-gosterge-yok' })),
              ...(after.KO.Bagg || []).filter(v => ![...(base.KO.Bagg || []), ...(base2.KO.Bagg || [])].some(b => b.k === v.k && b.n >= v.n)).map(v => ({ ...v, tip: 'B-halka-bogulmus' })),
            ],
            KM: (after.KM || []).filter(v => (v.kind === 'HARD' || v.kind === 'PLACE') &&
              !bk.has(`KM|${v.kind}|${v.node}|${(v.text || '').slice(0, 30)}`)),
          },
        };
        totalFind += delta.length;
        results.push(rec);
        const d = rec.deltaDetail;
        console.log(`${p} [${layer.name}] @${W}px  KP:${rec.baseCounts.KP}->${rec.afterCounts.KP}  KQ:${rec.baseCounts.KQ}->${rec.afterCounts.KQ}  KL:${rec.baseCounts.KL}->${rec.afterCounts.KL}  KO:${rec.baseCounts.KO}->${rec.afterCounts.KO}  KM:${rec.baseCounts.KM}->${rec.afterCounts.KM}  YENI:${d.KP.length}/${d.KQ.length}/${d.KL.length}/${d.KO.length}/${d.KM.length}`);
        for (const v of d.KP) console.log(`    [KP metin] ${v.sig} ${v.ratio}:1 (gerek ${v.need}) fg=${v.fg} bg=${v.bg} ${v.px}px "${v.text}"`);
        for (const v of d.KQ) console.log(`    [KQ sınır] ${v.sig} ${v.score !== undefined ? v.score : v.best}:1 ${v.box || ''} ${v.paint || ''}`);
        for (const v of d.KL) console.log(`    [KL tap]   ${v.sel} ${v.w}x${v.h} n=${v.n} "${v.txt}"`);
        for (const v of d.KO) console.log(`    [KO odak]  ${v.tip} ${v.k} n=${v.n} ${v.d && v.d.txt ? '"' + v.d.txt + '"' : ''}`);
        for (const v of d.KM) console.log(`    [KM kirp]  ${v.kind} ${v.node} < ${v.clipper} R+${v.ovR} B+${v.ovB} "${(v.text || '').slice(0, 40)}"`);
      } catch (e) {
        console.log(`${p} [${layer.name}] HATA: ${e.message.split('\n')[0]}`);
      }
      await page.close();
    }
  }
  await browser.close();
  fs.writeFileSync('/tmp/kr-overlay-' + W + '.json', JSON.stringify(results, null, 2));
  console.log(`\nTOPLAM @${W}px — yeni ihlal: ${totalFind}   (ayrıntı: /tmp/kr-overlay-${W}.json)`);
  process.exit(totalFind > 0 ? 1 : 0);
})();
