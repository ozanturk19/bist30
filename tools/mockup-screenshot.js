// tools/mockup-screenshot.js
// Standalone HTML mockup screenshot (file://)
// Çalıştır: node tools/mockup-screenshot.js
// Output: tests/visual/ux1/mockup-3b-<vp>.png

const { chromium } = require('playwright');
const fs = require('fs').promises;
const path = require('path');

const MOCKUP = 'file://' + path.resolve(__dirname, 'mockups/3b-tarama-redesign.html');
const OUT_DIR = path.join(__dirname, '../tests/visual/ux1');

const VIEWPORTS = [
  { name: '375',  width: 375,  height: 900 },
  { name: '768',  width: 768,  height: 900 },
  { name: '1280', width: 1280, height: 900 },
];

(async () => {
  try { await fs.mkdir(OUT_DIR, { recursive: true }); } catch {}
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext();

  for (const vp of VIEWPORTS) {
    const page = await ctx.newPage();
    await page.setViewportSize({ width: vp.width, height: vp.height });
    await page.goto(MOCKUP, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(400);
    const targetPath = path.join(OUT_DIR, `mockup-3b-${vp.name}.png`);
    await page.screenshot({ path: targetPath, fullPage: true });
    console.log(`✓ mockup-3b-${vp.name}.png`);
    await page.close();
  }
  await ctx.close();
  await browser.close();
})();
