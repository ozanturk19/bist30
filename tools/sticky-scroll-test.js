// tools/sticky-scroll-test.js
// CPO-372 B5: Sticky bar tab/header scroll behavior KESIN test
// Kullanım: VTEST_BASE=https://borsapusula.com node tools/sticky-scroll-test.js

const { chromium } = require('playwright');

const BASE = process.env.VTEST_BASE || 'http://localhost:8003';
const VIEWPORTS = [
  { name: 'mobile-375',  width: 375,  height: 812 },
  { name: 'tablet-768',  width: 768,  height: 1024 },
  { name: 'desktop-1280', width: 1280, height: 800 },
];
const PATH = '/hisse/THYAO';
const SCROLL_POSITIONS = [0, 300, 800, 1500, 3000];

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext();
  let total = 0, pass = 0, fail = 0;
  const results = [];

  for (const vp of VIEWPORTS) {
    const page = await ctx.newPage();
    await page.setViewportSize({ width: vp.width, height: vp.height });
    await page.goto(BASE + PATH, { waitUntil: 'domcontentloaded', timeout: 20000 });
    await page.waitForTimeout(2000);

    for (const scrollY of SCROLL_POSITIONS) {
      total++;
      try {
        await page.evaluate(y => window.scrollTo(0, y), scrollY);
        await page.waitForTimeout(400);

        // 3 elementi kontrol et:
        // - header (üst nav)
        // - bp-segments (tab bar)
        // - bp-sticky-hdr (kompakt scroll bar — scrollY > 120'da visible olmalı)
        const data = await page.evaluate(() => {
          const h = document.querySelector('header');
          const seg = document.querySelector('.bp-segments');
          const stk = document.querySelector('.bp-sticky-hdr');
          const box = el => el ? el.getBoundingClientRect() : null;
          const styl = el => el ? window.getComputedStyle(el) : null;
          return {
            header: box(h) && { y: box(h).y, height: box(h).height, pos: styl(h).position },
            segments: box(seg) && { y: box(seg).y, height: box(seg).height, pos: styl(seg).position, visible: box(seg).bottom > 0 && box(seg).top < window.innerHeight },
            stickyHdr: stk && { visible: stk.classList.contains('visible'), y: box(stk) ? box(stk).y : null, pos: styl(stk).position }
          };
        });

        // ASSERT: bp-segments her zaman görünür (sticky çalışıyor)
        const segVisible = data.segments && data.segments.visible;
        const segTopOK = data.segments && data.segments.y < 200; // viewport'un üst 200px'inde
        const ok = segVisible && segTopOK;
        const status = ok ? '✓' : '✗';
        if (ok) pass++; else fail++;

        console.log(`${status} ${vp.name} scrollY=${scrollY}: header.y=${data.header?.y.toFixed(0)} seg.y=${data.segments?.y?.toFixed(0)} (vis=${data.segments?.visible}) stkVisible=${data.stickyHdr?.visible}`);
        results.push({ vp: vp.name, scrollY, ok, data });
      } catch (e) {
        fail++;
        console.error(`✗ ${vp.name} scrollY=${scrollY} ERR: ${e.message}`);
      }
    }
    await page.close();
  }

  await ctx.close();
  await browser.close();

  console.log(`\nToplam: ${total}, PASS: ${pass}, FAIL: ${fail}`);
  process.exit(fail > 0 ? 1 : 0);
})();
