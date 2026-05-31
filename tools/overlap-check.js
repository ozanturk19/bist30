// tools/overlap-check.js — Ozan overlap bug (16:13 screenshot) doğrulama
// header.bot vs macro-bar.top vs bp-segments.bot overlap assert

const { chromium } = require('playwright');
const BASE = process.env.VTEST_BASE || 'https://borsapusula.com';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext();
  const VPS = [{n:'375',w:375,h:812},{n:'768',w:768,h:1024},{n:'1280',w:1280,h:800}];
  let pass=0, fail=0;
  for (const vp of VPS) {
    const page = await ctx.newPage();
    await page.setViewportSize({width:vp.w, height:vp.h});
    await page.goto(`${BASE}/hisse/ALFAS`, {waitUntil:'domcontentloaded', timeout:20000});
    await page.waitForTimeout(2000);
    const r = await page.evaluate(() => {
      const h = document.querySelector('header');
      const seg = document.querySelector('.bp-segments');
      const mb = document.querySelector('.macro-bar');
      const idb = document.querySelector('.hisse-id-bar');
      const box = el => el ? el.getBoundingClientRect() : null;
      return {
        header: box(h) && {top: box(h).top, bot: box(h).bottom, height: box(h).height},
        seg: box(seg) && {top: box(seg).top, bot: box(seg).bottom},
        macro: box(mb) && {top: box(mb).top, bot: box(mb).bottom},
        idbar: box(idb) && {top: box(idb).top, bot: box(idb).bottom},
      };
    });
    // Overlap testleri
    const segBelowHeader = r.header && r.seg && r.seg.top >= r.header.bot - 1;  // segments header sonrası (sticky top:60)
    const macroAfterHeader = r.header && r.macro && r.macro.top >= r.header.bot - 1;  // macro header sonrasi
    const noOverlapSegMacro = r.seg && r.macro && r.seg.bot <= r.macro.top + 1;
    const ok = segBelowHeader && macroAfterHeader && noOverlapSegMacro;
    if (ok) pass++; else fail++;
    const status = ok ? '✓' : '✗';
    console.log(`${status} ${vp.n}: header.bot=${r.header?.bot.toFixed(1)} seg.bot=${r.seg?.bot.toFixed(1)} macro.top=${r.macro?.top.toFixed(1)} idbar.top=${r.idbar?.top.toFixed(1)} | segBelowHdr=${segBelowHeader} macroAfter=${macroAfterHeader} noOvlp=${noOverlapSegMacro}`);
    await page.close();
  }
  await browser.close();
  console.log(`\n${pass}/${pass+fail} PASS`);
  process.exit(fail>0?1:0);
})();
