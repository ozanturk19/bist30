// tools/visual-test.js
// Playwright headless visual regression test — CPO-359 Tier 0 standardı
//
// Kurulum (bir kez): cd ~/ops && npm install -D playwright @playwright/test
//                    npx playwright install chromium
// Çalıştır: node tools/visual-test.js [--update-baseline]
// Output: tests/visual/current/*.png (60 PNG = 3 vp × 5 sayfa × 4 tab/varyasyon)

const { chromium } = require('playwright');
const fs = require('fs').promises;
const path = require('path');

const BASE = process.env.VTEST_BASE || 'http://localhost:8003';
const OUT_DIR = path.join(__dirname, '../tests/visual/current');
const BASELINE_DIR = path.join(__dirname, '../tests/visual/baseline');

const VIEWPORTS = [
  { name: '375',  width: 375,  height: 812 },   // iPhone 12 Pro
  { name: '768',  width: 768,  height: 1024 },  // iPad
  { name: '1280', width: 1280, height: 800 },   // Desktop
];

const PAGES = [
  { name: 'home',         path: '/' },
  { name: 'hisse-thyao',  path: '/hisse/THYAO' },
  { name: 'hisse-thyao-ozet',     path: '/hisse/THYAO?tab=ozet' },
  { name: 'hisse-thyao-grafik',   path: '/hisse/THYAO?tab=grafik' },
  { name: 'hisse-thyao-ai',       path: '/hisse/THYAO?tab=ai' },
  { name: 'hisse-thyao-haberler', path: '/hisse/THYAO?tab=haberler' },
  { name: 'heatmap',      path: '/heatmap' },
  { name: 'tarama',       path: '/tarama' },
  { name: 'gundem',       path: '/gundem' },
];

const UPDATE_BASELINE = process.argv.includes('--update-baseline');

async function ensureDir(d) {
  try { await fs.mkdir(d, { recursive: true }); } catch {}
}

(async () => {
  await ensureDir(OUT_DIR);
  if (UPDATE_BASELINE) await ensureDir(BASELINE_DIR);

  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext();

  let total = 0, errors = 0;

  for (const vp of VIEWPORTS) {
    for (const p of PAGES) {
      total++;
      const fileName = `${vp.name}-${p.name}.png`;
      const targetDir = UPDATE_BASELINE ? BASELINE_DIR : OUT_DIR;
      const targetPath = path.join(targetDir, fileName);
      try {
        const page = await ctx.newPage();
        await page.setViewportSize({ width: vp.width, height: vp.height });
        await page.goto(BASE + p.path, { waitUntil: 'networkidle', timeout: 15000 });
        // Sayfa biraz yerleşsin (lazy load, font, animation)
        await page.waitForTimeout(800);
        await page.screenshot({ path: targetPath, fullPage: true });
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
  console.log(`\nToplam: ${total} screenshot, ${errors} hata`);
  process.exit(errors > 0 ? 1 : 0);
})();
