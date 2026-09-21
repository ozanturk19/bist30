#!/usr/bin/env node
// tools/reduced-motion-check.js — K-AF: "hareketi azalt" modunda İÇERİK KAYBI dedektörü
//
// NEDEN AYRI BİR KAT:
//   tokens.css'teki global `*` kuralı (FAZ8) `prefers-reduced-motion: reduce`
//   altında her animasyonu 0.01ms'e indirip tek yinelemeye düşürür. Bu, SÜSLEME
//   niteliğindeki hareket için doğru davranıştır (nabız, shimmer, dönen halka).
//
//   ⛔ Ama bazı desenlerde hareket bir süsleme DEĞİL, İÇERİĞİ TAŞIMA GÖREVİdir:
//   marquee/ticker/carousel. Orada içerik, görüş alanından geniş bir şeride
//   basılır ve kullanıcıya TEK TEK hareketle getirilir; kapsayıcı `overflow:hidden`
//   olduğu için elle kaydırma da yoktur. Hareketi durdurmak o yüzeyde
//   erişilebilirliği ARTIRMAZ — içeriği YOK EDER.
//
//   Gerçek bulgu (21.09, canlı): makro şerit 13 şablonda, 9 kalem.
//   reduce altında @1280px 2/9, @375px 7/9 kalem KALICI erişilemez hale geliyordu.
//   `data-art.css` "prefers-reduced-motion: ÖLÇÜLDÜ, AYRI KURAL GEREKMİYOR"
//   diyordu — global kuralın VARLIĞI, o kuralın her yüzeyde DOĞRU olduğunun
//   kanıtı değildi (kalıcı ders: "kural da kanıtlanmalı").
//
// ÖLÇÜT (taban SIFIR) — bir bulgu ancak ÜÇÜ birden doğruysa:
//   1. Eleman CSS animasyonu taşıyor (hareketin TAŞIYICI olma adayı),
//   2. En yakın kırpan atası kullanıcı tarafından KAYDIRILAMIYOR
//      (ilgili eksende overflow hidden|clip — `auto`/`scroll` bulguyu düşürür),
//   3. reduce altında o animasyonlu alt ağacın METNİ kutunun TAMAMEN dışında.
//   Metni olmayan animasyonlar (shimmer parıltısı, nabız noktası) 3. koşulda
//   elenir — bu betiğin kendi sahte-pozitif sınıfının kapısı.
//
// ⛔ SİMÜLASYON DEĞİL: Playwright `emulateMedia({reducedMotion:'reduce'})` ile
//   GERÇEK medya sorgusu açılır. Kuralın gövdesini elle enjekte etmek ölçütü
//   dedektörün kendi kopyasından türetirdi (K-T'de öğrenilen "tek kaynak" dersi).
//
// Kullanım: node tools/reduced-motion-check.js [--base=...] [--w=375,1280] [--only=/a,/b]
const { chromium } = require('playwright');

const BASE = (process.argv.find(a => a.startsWith('--base=')) || '').split('=')[1] || 'https://borsapusula.com';
const WIDTHS = ((process.argv.find(a => a.startsWith('--w=')) || '').split('=')[1] || '375,1280')
  .split(',').map(s => parseInt(s, 10)).filter(Boolean);
const ONLY = (process.argv.find(a => a.startsWith('--only=')) || '').split('=')[1] || '';

// text-clip-check.js / text-spacing-check.js ile AYNI envanter
// (K-S dersi: ölü rota bir kapsam yalanıdır — ERROR olarak raporlanır, sessizce atlanmaz).
const PAGES = [
  '/', '/ozet', '/tarama', '/gundem', '/hisseler', '/sektor-harita',
  '/hisse/ASELS', '/hisse/GARAN', '/karsilastir', '/portfolio',
  '/bilanco-takvimi', '/temettu-takvimi', '/blog', '/blog/rsi-gostergesi-nedir',
  '/metodoloji', '/hakkinda', '/iletisim', '/profil', '/yasal', '/gizlilik',
];
const EXPECT_4XX = new Set(['/profil']);

const PROBE = () => {
  const out = [];
  const SKIP = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE', 'HEAD']);

  const desc = (el) => {
    if (!el) return '(yok)';
    const id = el.id ? '#' + el.id : '';
    const cls = (typeof el.className === 'string' && el.className.trim())
      ? '.' + el.className.trim().split(/\s+/).slice(0, 2).join('.') : '';
    return el.tagName.toLowerCase() + id + cls;
  };

  // En yakın KIRPAN ata + hangi eksende kırptığı.
  const clipper = (el) => {
    let p = el.parentElement;
    while (p && p !== document.documentElement) {
      const cs = getComputedStyle(p);
      const cx = cs.overflowX, cy = cs.overflowY;
      const hx = cx === 'hidden' || cx === 'clip';
      const hy = cy === 'hidden' || cy === 'clip';
      if (hx || hy) return { el: p, hx, hy, cx, cy };
      p = p.parentElement;
    }
    return null;
  };

  // Görünür metin taşıyan yaprak düğümler.
  const textLeaves = (root) => {
    const res = [];
    const walk = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT);
    let n = root;
    do {
      if (SKIP.has(n.tagName)) continue;
      const own = [...n.childNodes].some(c => c.nodeType === 3 && c.textContent.trim());
      if (own) {
        const cs = getComputedStyle(n);
        if (cs.visibility !== 'hidden' && cs.display !== 'none' && parseFloat(cs.opacity) > 0.05) res.push(n);
      }
    } while ((n = walk.nextNode()));
    return res;
  };

  for (const el of document.querySelectorAll('*')) {
    if (SKIP.has(el.tagName)) continue;
    const cs = getComputedStyle(el);
    if (cs.animationName === 'none' || !cs.animationName) continue;   // koşul 1

    const c = clipper(el);
    if (!c) continue;                                                  // kırpılmıyor → kayıp yok
    const cb = c.el.getBoundingClientRect();
    // koşul 2: kullanıcı o eksende KAYDIRABİLİYORSA kayıp yok.
    const overflowsX = c.el.scrollWidth  > c.el.clientWidth  + 1;
    const overflowsY = c.el.scrollHeight > c.el.clientHeight + 1;
    const trappedX = c.hx && overflowsX;
    const trappedY = c.hy && overflowsY;
    if (!trappedX && !trappedY) continue;

    // koşul 3: animasyonlu alt ağacın METNİ kutunun TAMAMEN dışında mı?
    const lost = [];
    for (const t of textLeaves(el)) {
      const r = t.getBoundingClientRect();
      if (r.width === 0 && r.height === 0) continue;
      const outX = trappedX && (r.left >= cb.right - 1 || r.right <= cb.left + 1);
      const outY = trappedY && (r.top  >= cb.bottom - 1 || r.bottom <= cb.top + 1);
      if (outX || outY) lost.push((t.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 40));
    }
    if (!lost.length) continue;   // metinsiz hareket (shimmer/nabız) → sahte-pozitif kapısı

    out.push({
      node: desc(el),
      anim: cs.animationName,
      clipper: desc(c.el),
      overflow: `x:${c.cx} y:${c.cy}`,
      eksen: trappedX ? 'yatay' : 'dikey',
      lostCount: lost.length,
      lost: lost.slice(0, 12),
    });
  }
  return out;
};

(async () => {
  const pages = ONLY ? ONLY.split(',') : PAGES;
  const browser = await chromium.launch();
  let fails = 0, errors = 0;
  const report = [];

  for (const W of WIDTHS) {
    console.log(`\n───────────── @${W}px ─────────────`);
    // ⛔ GERÇEK medya sorgusu — enjekte edilmiş kopya DEĞİL.
    const ctx = await browser.newContext({ viewport: { width: W, height: 900 }, reducedMotion: 'reduce' });
    const page = await ctx.newPage();

    for (const p of pages) {
      const url = BASE.replace(/\/$/, '') + p;
      let status = 0;
      try {
        const resp = await page.goto(url, { waitUntil: 'networkidle', timeout: 45000 });
        status = resp ? resp.status() : 0;
      } catch (e) {
        console.log(`ERROR ${p} — yüklenemedi: ${e.message.split('\n')[0]}`);
        errors++; continue;
      }
      if (status >= 400 && !EXPECT_4XX.has(p)) {
        console.log(`ERROR ${p} — HTTP ${status} (ölü rota; kapsam yalanı)`);
        errors++; continue;
      }
      // classList/animasyon sonrası getComputedStyle bayatlığı: rAF×2 (kalıcı ders).
      await page.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))));

      const v = await page.evaluate(PROBE);
      fails += v.length;
      console.log(`${v.length ? 'FAIL' : 'OK  '} ${p}${v.length ? `  ${v.length} taşıyıcı-hareket` : ''}`);
      for (const x of v) {
        console.log(`      ${x.node} [${x.anim}]  ⊂ ${x.clipper} (${x.overflow}, ${x.eksen})  → ${x.lostCount} metin erişilemez`);
        console.log(`             ${x.lost.map(s => `"${s}"`).join(' · ')}`);
        report.push({ page: p, w: W, ...x });
      }
    }
    await ctx.close();
  }

  await browser.close();
  console.log(`\n=== K-AF özet: ${fails} FAIL · ${errors} ERROR · ${pages.length} sayfa × ${WIDTHS.length} genişlik ===`);
  if (!fails && !errors) console.log('Hareketi azalt modunda taşıyıcı-hareket kaynaklı içerik kaybı YOK.');
  process.exit(errors || fails ? 2 : 0);
})();
