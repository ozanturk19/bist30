// tools/ux2-screenshot.js — UX-2 Task #23 tarama kolon redesign screenshots
const { chromium } = require('playwright');
const fs = require('fs').promises;
const path = require('path');

const BASE = process.env.VTEST_BASE || 'http://localhost:18008';
const OUT_DIR = path.join(__dirname, '../tests/visual/ux2');

const VIEWPORTS = [
  { name: '375',  width: 375,  height: 900 },
  { name: '768',  width: 768,  height: 900 },
  { name: '1280', width: 1280, height: 900 },
];

const SCENES = [
  { name: 'tarama-default',        path: '/tarama',              scroll: 0 },
  { name: 'tarama-scroll-300',     path: '/tarama',              scroll: 300 },
  { name: 'tarama-scroll-700',     path: '/tarama',              scroll: 700 },
  { name: 'tarama-sort-rvol',      path: '/tarama?sort=vol_ratio', scroll: 0 },
  { name: 'tarama-sort-trend',     path: '/tarama?sort=adx',       scroll: 0 },
  { name: 'tarama-filter-al',      path: '/tarama?signal=AL',     scroll: 0 },
];

(async () => {
  try { await fs.mkdir(OUT_DIR, { recursive: true }); } catch {}
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext();

  let total = 0, errors = 0;
  for (const vp of VIEWPORTS) {
    for (const s of SCENES) {
      total++;
      const fileName = `${vp.name}-${s.name}.png`;
      try {
        const page = await ctx.newPage();
        await page.setViewportSize({ width: vp.width, height: vp.height });
        await page.goto(BASE + s.path, { waitUntil: 'domcontentloaded', timeout: 25000 });
        try { await page.waitForLoadState('networkidle', { timeout: 8000 }); } catch {}
        await page.waitForTimeout(900);  // tablo render + data
        if (s.scroll) {
          await page.evaluate((y) => window.scrollTo({ top: y, behavior: 'instant' }), s.scroll);
          await page.waitForTimeout(300);
        }
        await page.screenshot({ path: path.join(OUT_DIR, fileName), fullPage: false });
        console.log(`✓ ${fileName}`);
        await page.close();
      } catch (e) {
        errors++;
        console.error(`✗ ${fileName}: ${e.message}`);
      }
    }
  }
  await ctx.close(); await browser.close();
  console.log(`\nToplam: ${total}, hata: ${errors}`);
  process.exit(errors > 0 ? 1 : 0);
})();
