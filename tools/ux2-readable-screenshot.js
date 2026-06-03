// tools/ux2-readable-screenshot.js — Okunabilir close-up table screenshot
// 1280 viewport, 2x device scale, tablonun üst 10 satırına focus
const { chromium } = require('playwright');
const path = require('path');

const BASE = process.env.VTEST_BASE || 'http://localhost:18008';
const OUT = path.join(__dirname, '../tests/visual/ux2');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ deviceScaleFactor: 2 });  // 2x retina
  const page = await ctx.newPage();
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(`${BASE}/tarama`, { waitUntil: 'domcontentloaded', timeout: 25000 });
  try { await page.waitForLoadState('networkidle', { timeout: 10000 }); } catch {}
  await page.waitForTimeout(1500);  // tablo render + data

  // Scroll table'a göster
  await page.evaluate(() => {
    const t = document.getElementById('resultTable');
    if (t) t.scrollIntoView({ block: 'start' });
  });
  await page.waitForTimeout(500);

  // Tablonun bounding box'ını al, clip et
  const tableBox = await page.evaluate(() => {
    const t = document.getElementById('resultTable');
    if (!t) return null;
    const r = t.getBoundingClientRect();
    return { x: r.left, y: r.top, w: r.width, h: Math.min(r.height, 700) };
  });

  if (tableBox) {
    await page.screenshot({
      path: path.join(OUT, '1280-tarama-readable.png'),
      clip: { x: Math.max(0, tableBox.x - 10), y: Math.max(0, tableBox.y - 10),
              width: tableBox.w + 20, height: tableBox.h + 20 }
    });
    console.log(`✓ 1280-tarama-readable.png (2x scale, clip ${tableBox.w}x${tableBox.h})`);
  } else {
    console.error('✗ resultTable bulunamadı');
  }

  // Ek: 1280 default tam viewport (yeni screenshot — eski stale değil)
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(300);
  await page.screenshot({ path: path.join(OUT, '1280-tarama-default.png'), fullPage: false });
  console.log(`✓ 1280-tarama-default.png (fresh, 2x scale)`);

  await ctx.close();
  await browser.close();
})();
