// tools/sticky-v3-scroll-test.js
// SPEC-STICKY-HEADER-v3 KABUL TESTİ
// 3 viewport × 4 scroll position × 2 ticker = 24 PNG + gap/bleed assert

const { chromium } = require('playwright');
const fs = require('fs').promises;
const path = require('path');

const BASE = process.env.VTEST_BASE || 'https://borsapusula.com';
const OUT = path.join(__dirname, '../tests/visual/sticky-v3');
const VIEWPORTS = [
  { name: '375',  width: 375,  height: 812 },
  { name: '768',  width: 768,  height: 1024 },
  { name: '1280', width: 1280, height: 800 },
];
const TICKERS = ['THYAO', 'ISDMR'];
const SCROLLS = [0, 300, 700, 1200];

(async () => {
  await fs.mkdir(OUT, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext();
  let total = 0, pass = 0, fail = 0;

  for (const vp of VIEWPORTS) {
    for (const tk of TICKERS) {
      const page = await ctx.newPage();
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto(`${BASE}/hisse/${tk}`, { waitUntil: 'domcontentloaded', timeout: 20000 });
      await page.waitForTimeout(2000);

      for (const y of SCROLLS) {
        total++;
        try {
          await page.evaluate(yy => window.scrollTo(0, yy), y);
          await page.waitForTimeout(400);

          const result = await page.evaluate(() => {
            const h = document.querySelector('header');
            const seg = document.querySelector('.bp-segments');
            const hbox = h ? h.getBoundingClientRect() : null;
            const sbox = seg ? seg.getBoundingClientRect() : null;
            const hStyle = h ? window.getComputedStyle(h) : null;
            // Gap check: header bottom & segments top (segments artık header İÇİNDE olduğu için bağımsız değil)
            const segInHeader = h && seg && h.contains(seg);
            return {
              header: hbox && { top: hbox.top, bottom: hbox.bottom, height: hbox.height },
              segments: sbox && { top: sbox.top, height: sbox.height },
              segInHeader,
              headerBg: hStyle ? hStyle.backgroundColor : null,
              headerOpaque: hStyle && /rgba?\(14,\s*14,\s*18,\s*1\)|#0e0e12/i.test(hStyle.backgroundColor.replace(/\s/g, '')),
            };
          });

          // ASSERTS
          const headerTop0 = result.header && Math.abs(result.header.top) < 2;
          const segInHdr = result.segInHeader === true;
          const gap = result.segments && result.header && (result.segments.top - result.header.top >= 0);
          const ok = headerTop0 && segInHdr && gap;
          if (ok) pass++; else fail++;
          const status = ok ? '✓' : '✗';
          console.log(`${status} ${vp.name}-${tk} y=${y}: header.top=${result.header?.top.toFixed(1)} h.bot=${result.header?.bottom.toFixed(1)} seg.top=${result.segments?.top.toFixed(1)} segInHdr=${result.segInHeader} bg=${result.headerBg}`);

          await page.screenshot({ path: path.join(OUT, `${vp.name}-${tk}-y${y}.png`), fullPage: false });
        } catch (e) {
          fail++;
          console.error(`✗ ${vp.name}-${tk} y=${y}: ${e.message}`);
        }
      }
      await page.close();
    }
  }

  await ctx.close();
  await browser.close();
  console.log(`\nToplam: ${total}, PASS: ${pass}, FAIL: ${fail}`);
  process.exit(fail > 0 ? 1 : 0);
})();
