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
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE = (process.argv.find(a => a.startsWith('--base=')) || '').split('=')[1] || 'https://borsapusula.com';
const W = parseInt((process.argv.find(a => a.startsWith('--w=')) || '').split('=')[1] || '1280', 10);
const ONLY = (process.argv.find(a => a.startsWith('--only=')) || '').split('=')[1] || '';

const read = (f) => fs.readFileSync(path.join(__dirname, f), 'utf8');
const KP = read('live-contrast-check.js');   // K-P metin kontrastı
const KQ = read('nontext-contrast-check.js'); // K-Q metin-dışı kontrast
const KL = read('tap-target-check.js');       // K-L dokunma hedefi

// ── Katman açma reçeteleri ────────────────────────────────────────────────
// Her reçete: { ad, sayfalar, aç(page), minW/maxW }
const LAYERS = [
  {
    name: 'arama-overlay (boş)',
    pages: ['/', '/tarama', '/hisse/ASELS', '/portfoy'],
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
    pages: ['/portfoy'],
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
        await page.goto(BASE + p, { waitUntil: 'networkidle', timeout: 45000 });
        await page.waitForTimeout(1200);

        const base = {
          KP: await runProbe(page, KP),
          KQ: await runProbe(page, KQ),
          KL: await runProbe(page, KL),
        };
        const opened = await layer.open(page);

        // katman gerçekten açıldı mı? görünür düğüm sayısı artmalı
        const grew = await page.evaluate(() => {
          let n = 0;
          document.querySelectorAll('*').forEach(e => { const r = e.getBoundingClientRect(); if (r.width > 0 && r.height > 0) n++; });
          return n;
        });

        const after = {
          KP: await runProbe(page, KP),
          KQ: await runProbe(page, KQ),
          KL: await runProbe(page, KL),
        };

        const bk = new Set([...keysKP(base.KP), ...keysKQ(base.KQ), ...keysKL(base.KL)]);
        const ak = [...keysKP(after.KP), ...keysKQ(after.KQ), ...keysKL(after.KL)];
        const delta = ak.filter(k => !bk.has(k));

        const rec = {
          page: p, layer: layer.name, w: W, visNodes: grew, opened: opened ?? null,
          baseCounts: { KP: base.KP.hardCount, KQ: base.KQ.hardCount, KL: base.KL.bad },
          afterCounts: { KP: after.KP.hardCount, KQ: after.KQ.hardCount, KL: after.KL.bad },
          delta,
          deltaDetail: {
            KP: (after.KP.HARD || []).filter(v => !bk.has(`KP|${v.sig}|${v.ratio}|${(v.text || '').slice(0, 24)}`)),
            KQ: (after.KQ.HARD || []).filter(v => !bk.has(`KQ|${v.sig}|${v.score !== undefined ? v.score : v.best}`)),
            KL: (after.KL.agg || []).filter(v => !(base.KL.agg || []).some(b => b.sel === v.sel && b.n >= v.n)),
          },
        };
        totalFind += delta.length;
        results.push(rec);
        const d = rec.deltaDetail;
        console.log(`${p} [${layer.name}] @${W}px  KP:${base.KP.hardCount}->${after.KP.hardCount}  KQ:${base.KQ.hardCount}->${after.KQ.hardCount}  KL:${base.KL.bad}->${after.KL.bad}  YENI:${d.KP.length}/${d.KQ.length}/${d.KL.length}`);
        for (const v of d.KP) console.log(`    [KP metin] ${v.sig} ${v.ratio}:1 (gerek ${v.need}) fg=${v.fg} bg=${v.bg} ${v.px}px "${v.text}"`);
        for (const v of d.KQ) console.log(`    [KQ sınır] ${v.sig} ${v.score !== undefined ? v.score : v.best}:1 ${v.box || ''} ${v.paint || ''}`);
        for (const v of d.KL) console.log(`    [KL tap]   ${v.sel} ${v.w}x${v.h} n=${v.n} "${v.txt}"`);
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
