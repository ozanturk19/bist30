#!/usr/bin/env node
// tools/text-spacing-check.js — K-AE: WCAG 1.4.12 Metin Aralığı (Text Spacing) dedektörü
//
// Neden var: tools/text-clip-check.js metin kırpılmasını SİTENİN KENDİ aralığında
// ölçer. WCAG 2.1 AA 1.4.12 ise KULLANICININ aralığı büyütme hakkını korur:
// kullanıcı satır/paragraf/harf/kelime aralığını aşağıdaki değerlere çektiğinde
// hiçbir içerik veya işlev KAYBOLMAMALIDIR. Bu, sitede hiç ölçülmemiş bir boyut;
// sabit `height`/`max-height` taşıyan her metin kutusu doğal adayı.
//
// Dayatılan değerler (WCAG 1.4.12 metninin birebir karşılığı, standart yer imi CSS'i):
//   line-height   >= 1.5   × yazı boyu
//   paragraf arası>= 2em
//   letter-spacing>= 0.12em
//   word-spacing  >= 0.16em
//
// ⛔ DELTA ÖLÇÜMÜ ZORUNLU: aralık dayatıldığında zaten var olan (K-M/K-AD turlarında
// bilinen veya tasarımca kabul edilmiş) kırpılmalar da raporlanır. Bu betik TABAN
// ölçümü alıp dayatma SONRASI ölçümden çıkarır — yalnız ARALIK YÜZÜNDEN doğan
// yeni kayıplar ihlaldir. Aksi halde bulgu listesi eski turların gürültüsüyle dolar.
//
// Sınıflandırma:
//   FAIL  — tabanda temiz olan metin, aralık sonrası GÖSTERGESİZ kırpılıyor (HARD).
//   WARN  — tabanda tam görünen metin, aralık sonrası ellipsis/line-clamp'e düşüyor.
//           (1.4.12 açısından yine içerik kaybı, ama kullanıcıya sinyal veriliyor.)
//
// Kullanım: node tools/text-spacing-check.js [--base=...] [--w=375] [--only=/a,/b]
const { chromium } = require('playwright');
const { PROBE } = require('./text-clip-check.js');

const BASE = (process.argv.find(a => a.startsWith('--base=')) || '').split('=')[1] || 'https://borsapusula.com';
const W = parseInt((process.argv.find(a => a.startsWith('--w=')) || '').split('=')[1] || '375', 10);
const ONLY = (process.argv.find(a => a.startsWith('--only=')) || '').split('=')[1] || '';

// text-clip-check.js ile AYNI envanter (K-S dersi: ölü rota bir kapsam yalanıdır).
const PAGES = [
  '/', '/ozet', '/tarama', '/gundem', '/hisseler', '/sektor-harita',
  '/hisse/ASELS', '/hisse/GARAN', '/karsilastir', '/portfolio',
  '/takvim', '/blog', '/blog/rsi-gostergesi-nedir',
  '/metodoloji', '/hakkinda', '/iletisim', '/profil', '/yasal', '/gizlilik',
];
const EXPECT_4XX = new Set(['/profil']);

const SPACING_CSS = `
* , *::before, *::after {
  line-height: 1.5 !important;
  letter-spacing: 0.12em !important;
  word-spacing: 0.16em !important;
}
p, li, blockquote, dd, dt, figcaption {
  margin-bottom: 2em !important;
}`;

// Bir bulguyu KİMLİKLENDİREN anahtar. Metin dahil: aynı kutuda farklı metin
// düğümü farklı bulgudur. Taşma MİKTARI dahil DEĞİL — aralık her taşmayı
// büyütür, miktar delta anahtarına girerse taban eşleşmesi çöker ve her şey
// "yeni" görünür (bu betiğin kendi sahte-pozitif sınıfı).
const key = (v) => `${v.kind === 'ELLIP' ? 'E' : v.kind === 'PLACE' ? 'P' : 'H'}|${v.node}|${v.clipper}|${v.text}`;
const baseKey = (v) => `${v.node}|${v.clipper}|${v.text}`;

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: W, height: 900 }, isMobile: false });
  const page = await ctx.newPage();
  const pages = ONLY ? ONLY.split(',') : PAGES;
  let fails = 0, warns = 0, errors = 0;
  const report = [];

  for (const p of pages) {
    const url = BASE + p;
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

    const before = await page.evaluate(PROBE);
    await page.addStyleTag({ content: SPACING_CSS });
    // Düzen yeniden akışı + getComputedStyle bayatlığı: rAF×2 bekle (kalıcı ders).
    await page.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))));
    const after = await page.evaluate(PROBE);

    // Tabanda ZATEN kırpılan kutu+metin çifti (hangi sınıfta olursa olsun) elenir.
    const beforeBoxes = new Set(before.map(baseKey));
    const beforeExact = new Set(before.map(key));
    const fresh = after.filter(v => !beforeExact.has(key(v)) && !beforeBoxes.has(baseKey(v)));

    const f = fresh.filter(v => v.kind === 'HARD');
    const w = fresh.filter(v => v.kind !== 'HARD');
    fails += f.length; warns += w.length;
    const tag = f.length ? 'FAIL' : w.length ? 'WARN' : 'OK  ';
    console.log(`${tag} ${p}  taban=${before.length}  aralık-sonrası=${after.length}  YENİ: ${f.length} FAIL / ${w.length} WARN`);
    for (const v of [...f, ...w]) {
      console.log(`      [${v.kind}] ${v.node}  ⊂ ${v.clipper}   sağ=${v.ovR} sol=${v.ovL} alt=${v.ovB}`);
      console.log(`             "${v.text}"`);
      report.push({ page: p, ...v });
    }
  }

  await browser.close();
  console.log(`\n=== K-AE özet: ${fails} FAIL · ${warns} WARN · ${errors} ERROR · ${pages.length} sayfa @${W}px ===`);
  process.exit(errors || fails ? 2 : warns ? 1 : 0);
})();
