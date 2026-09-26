// tools/ux1-screenshot.js
// UX-1 (CPO-463/464/465/468) screenshot paketi
// 3 viewport × tab-state + scroll-state + tarama focus-state
//
// Çalıştır:
//   VTEST_BASE=http://135.181.206.109:8008 node tools/ux1-screenshot.js
// Output: tests/visual/ux1/<viewport>-<scene>.png

const { chromium } = require('playwright');
const fs = require('fs').promises;
const path = require('path');

const BASE = process.env.VTEST_BASE || 'http://localhost:8008';
const OUT_DIR = path.join(__dirname, '../tests/visual/ux1');

const VIEWPORTS = [
  { name: '375',  width: 375,  height: 812 },   // iPhone mobil
  { name: '768',  width: 768,  height: 1024 },  // tablet
  { name: '1280', width: 1280, height: 800 },   // desktop
];

// Senaryolar — UX-1 madde-spesifik + CPO-469 scroll-state matrisi (0/300/700)
const SCENES = [
  // === Madde 1A + 2: üst sekme bar (her tab × scroll=0) ===
  { name: 'hisse-tab-ozet',         path: '/hisse/THYAO?tab=ozet',     scroll: 0 },
  { name: 'hisse-tab-grafik',       path: '/hisse/THYAO?tab=grafik',   scroll: 0 },
  { name: 'hisse-tab-ai',           path: '/hisse/THYAO?tab=ai',       scroll: 0 },
  { name: 'hisse-tab-haberler',     path: '/hisse/THYAO?tab=haberler', scroll: 0 },

  // === Sticky scroll-state matrisi (CPO-469 görsel kapı, sticky-header dersi) ===
  { name: 'hisse-scroll-300',       path: '/hisse/THYAO?tab=ozet',     scroll: 300 },  // ara state
  { name: 'hisse-scroll-700',       path: '/hisse/THYAO?tab=ozet',     scroll: 700 },  // derin scroll
  { name: 'hisse-scroll-down',      path: '/hisse/THYAO?tab=ozet',     scroll: 600 },  // (eski 600, koru)

  // === Madde 1B: alt bar (mobil tipik view) — scroll içinde teyit edilir ===

  // === Madde 3a: tarama search (default + focus + scroll-state) ===
  { name: 'tarama-default',         path: '/tarama',                   scroll: 0 },
  { name: 'tarama-search-focus',    path: '/tarama',                   scroll: 0,   focus: '#fSearch' },
  { name: 'tarama-scroll-300',      path: '/tarama',                   scroll: 300 },
];

async function ensureDir(d) {
  try { await fs.mkdir(d, { recursive: true }); } catch {}
}

(async () => {
  await ensureDir(OUT_DIR);

  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext();

  let total = 0, errors = 0;
  const startTime = Date.now();

  for (const vp of VIEWPORTS) {
    for (const s of SCENES) {
      total++;
      const fileName = `${vp.name}-${s.name}.png`;
      const targetPath = path.join(OUT_DIR, fileName);
      try {
        const page = await ctx.newPage();
        await page.setViewportSize({ width: vp.width, height: vp.height });
        await page.goto(BASE + s.path, { waitUntil: 'domcontentloaded', timeout: 20000 });
        // Networkidle olmaya çalış (chart vb. tamamlansın), max 6s
        try { await page.waitForLoadState('networkidle', { timeout: 6000 }); } catch {}
        await page.waitForTimeout(700);  // animasyon/font yerleşmesi

        if (s.scroll) {
          await page.evaluate((y) => window.scrollTo({ top: y, behavior: 'instant' }), s.scroll);
          await page.waitForTimeout(300);
        }

        if (s.focus) {
          try {
            await page.focus(s.focus);
            await page.waitForTimeout(250);
          } catch (e) { /* selector yoksa atla */ }
        }

        await page.screenshot({ path: targetPath, fullPage: false });
        console.log(`✓ ${fileName}`);
        await page.close();
      } catch (e) {
        errors++;
        console.error(`✗ ${fileName}: ${e.message}`);
      }
    }
  }

  await ctx.close();
  await browser.close();

  const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
  console.log(`\nToplam: ${total} screenshot, ${errors} hata (${elapsed}s)`);
  process.exit(errors > 0 ? 1 : 0);
})();
