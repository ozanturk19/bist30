#!/usr/bin/env node
// KAPI 83 — "KIRPILMIŞ AMA KAYDIRILAMAYAN İÇERİK" (K-DQ, 22.09)
//
// NEDEN VAR — günlük 320px harness'ın YAPISAL kör noktası.
// `tools/mobile-overflow-check.mjs` tek bir sayı ölçer:
//     document.documentElement.scrollWidth - clientWidth
// Bu sayı, sitede `html{overflow-x:clip}` + `body{overflow-x:clip}` bulunduğu
// sürece TANIMI GEREĞİ 0'dır (bkz. o dosyanın 232-235. satırlarındaki not:
// guard bilerek html'e taşınmıştı). Yani viewport'tan geniş bir öge artık
// scrollWidth'e sızmıyor — ama EKRANDAN DA KAYBOLUYOR. Harness'ın "110/110
// temiz, 0 taşma" çıktısı bu sınıf için bir ölçüm değil, bir TANIMDIR.
//
// İlk koşumda yakalanan gerçek kırılma (K-DQ): /hisse Özet sekmesindeki
// `.history-table` 320px'te 336px'e kadar uzanıyordu — "Getiri" sütunu
// (tablonun var oluş sebebi olan sayı) 16px dışarıda, `overflow-x:clip`
// yüzünden yatay kaydırma da İMKÂNSIZ. Kullanıcı o sayıyı hiçbir şekilde
// göremiyordu.
//
// ÖLÇÜLEN ŞEY: bir ögenin metni viewport'un sağ (ya da sol) sınırını aşıyor
// VE atalarından hiçbiri onu kaydırarak erişilebilir kılmıyor.
//   - Atada overflow-x auto|scroll VE gerçekten kaydırılabilir (scrollWidth >
//     clientWidth) ise → içerik ERİŞİLEBİLİR, ihlal değil.
//   - Atada overflow-x hidden|clip ise ya da hiç kaydırma yolu yoksa
//     (html/body clip) → içerik AMPUTE, ihlal.
// Metin kutusu (Range) ölçülür, kutu değil: 56px'lik bir hücrenin 6px'i
// dışarıdaysa ama metni içerideyse kullanıcı bir şey kaybetmez.
//
// MUAFİYET: yalnızca bilerek animasyonlu şerit (marquee) — atalarından biri
// `animation-name != none` taşıyan ögeler. Makro bar şeridi bu sınıftandır:
// içeriği zaten zamanla ekrana giriyor, "kayıp" değil.
//
// Kullanım:  node tools/clipped-content-check.mjs [--base=...] [--widths=320,360]
//            [--out=path.json] [--inject]   (--inject = pozitif kontrol)
// Exit: 0 temiz · 2 ihlal/yükleme hatası

import { chromium } from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.join(__dirname, '..');

const arg = (k, d) => (process.argv.find(a => a.startsWith(`--${k}=`)) || '').split('=')[1] || d;
const BASE = arg('base', process.env.MOC_BASE || 'https://borsapusula.com');
const WIDTHS = arg('widths', '320,360').split(',').map(n => parseInt(n, 10));
const OUT = arg('out', path.join(REPO_ROOT, 'tests', 'mobile-overflow', 'clipped-latest.json'));
const INJECT = process.argv.includes('--inject');
const HEIGHT = 800;

// Envanter: mobile-overflow-check.mjs'in benzersiz sayfa listesiyle aynı
// (yönlendirme/ölü rota ayıklaması orada yapıldı, tekrar edilmiyor).
const PAGES = [
  { name: 'home', path: '/' },
  { name: 'tarama', path: '/tarama' },
  { name: 'tarama-temel', path: '/tarama?tab=temel' },
  { name: 'gundem', path: '/gundem' },
  { name: 'karsilastir', path: '/karsilastir' },
  { name: 'ozet', path: '/ozet' },
  { name: 'metodoloji', path: '/metodoloji' },
  { name: 'hakkinda', path: '/hakkinda' },
  { name: 'gizlilik', path: '/gizlilik' },
  { name: 'iletisim', path: '/iletisim' },
  { name: 'yasal', path: '/yasal' },
  { name: 'portfolio', path: '/portfolio' },
  { name: 'hisseler', path: '/hisseler' },
  { name: 'sektor-harita', path: '/sektor-harita' },
  { name: 'takvim', path: '/takvim' },
  { name: 'blog', path: '/blog' },
  { name: 'blog-article', path: '/blog/supertrend-indikatoru-nedir' },
  { name: 'hisse-thyao', path: '/hisse/THYAO' },
  { name: 'hisse-thyao-grafik', path: '/hisse/THYAO?tab=grafik' },
  { name: 'hisse-thyao-ai', path: '/hisse/THYAO?tab=ai' },
  { name: 'hisse-thyao-haberler', path: '/hisse/THYAO?tab=haberler' },
  { name: 'hisse-akbnk', path: '/hisse/AKBNK' },
];

const PROBE = (inject) => {
  const de = document.documentElement;
  const vw = de.clientWidth;

  if (inject) {
    // POZİTİF KONTROL (164. ders): kapının KORUMAK İÇİN yazıldığı hatayı
    // birebir enjekte et — kaydırma yolu olmayan, viewport'tan geniş bir tablo.
    // Patoloji, "geniş öge" DEĞİL; "geniş öge + kaydırma yolu yok" bileşimidir.
    // Sayfaların yalnız yarısında `html{overflow-x:clip}` var (K-DQ bulgusu),
    // kalanında enjekte edilen öge belgeyi yatay kaydırılabilir yapar ve
    // ERİŞİLEBİLİR olur -- yani kapı onu haklı olarak ihlal saymaz. Kontrolün
    // her sayfada geçerli olması için kırpma koşulu da enjekte edilir.
    de.style.overflowX = 'clip';
    document.body.style.overflowX = 'clip';
    const d = document.createElement('div');
    d.id = '__clip_probe__';
    d.style.cssText = 'width:' + (vw + 40) + 'px;white-space:nowrap;font-size:14px';
    d.textContent = 'KAPI-83 POZITIF KONTROL — bu metin ekrandan tasmali ve kaydirilamaz olmali';
    document.body.appendChild(d);
  }

  // ETKİN GÖRÜNÜR SINIR.
  // Bir kırpma kutusu SAYFANIN İÇİNDEYSE bu tasarlanmış bir kısaltmadır
  // (`text-overflow:ellipsis` ile "…" gösterilir, kullanıcı devamı olduğunu
  // BİLİR) — ihlal değil. Kırpma tam VIEWPORT KENARINDA oluyorsa, yani
  // metni kesen tek şey `html/body{overflow-x:clip}` ise, kullanıcıya hiçbir
  // işaret verilmeden sayı/kelime yok edilir — patoloji tam olarak budur.
  // Bu yüzden yürüyüş html ve body'yi KIRPMA KUTUSU SAYMAZ.
  // Dönüş: {reachable} ya da {right,left} etkin sınırlar.
  const effectiveBounds = (el, own) => {
    let right = Infinity, left = -Infinity;
    const selfCs = getComputedStyle(el);
    if (/hidden|clip/.test(selfCs.overflowX)) { right = own.right; left = own.left; }
    let p = el.parentElement;
    while (p && p !== document.body && p !== de) {
      const c = getComputedStyle(p);
      if (/auto|scroll/.test(c.overflowX) && p.scrollWidth > p.clientWidth + 1) return { reachable: true };
      if (/hidden|clip/.test(c.overflowX)) {
        const pr = p.getBoundingClientRect();
        right = Math.min(right, pr.right); left = Math.max(left, pr.left);
      }
      p = p.parentElement;
    }
    // Belge yatay kayabiliyorsa içerik yine erişilebilirdir.
    if (de.scrollWidth > de.clientWidth + 1) return { reachable: true };
    return { reachable: false, right, left };
  };
  const animated = (el) => {
    let p = el;
    while (p) {
      const c = getComputedStyle(p);
      if (c.animationName && c.animationName !== 'none') return true;
      p = p.parentElement;
    }
    return false;
  };

  const out = [];
  const seen = new Set();
  for (const el of document.querySelectorAll('body *')) {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || cs.opacity === '0') continue;
    if (el.closest('[aria-hidden="true"]')) continue;
    // yalnız kendi metnini taşıyan yaprak benzeri ögeler (ata kutuları tekrar sayılmasın)
    const ownText = [...el.childNodes].filter(n => n.nodeType === 3 && n.textContent.trim()).length > 0;
    if (!ownText) continue;
    // YANLIŞ-POZİTİF SINIFI 1 — ekran-okuyucu metni. `.sr-only` bilerek
    // görüş alanının DIŞINA konur (clip-rect / 1px kutu); "kırpıldı" demek
    // anlamsız. Kutunun kendisi 1px'e çökmüşse de aynı teknik.
    const own = el.getBoundingClientRect();
    if (own.width <= 1 || own.height <= 1) continue;
    if (el.closest('.sr-only')) continue;

    // YANLIŞ-POZİTİF SINIFI 3 — ögenin İÇİNDEKİ sr-only alt düğüm. Kutuyu
    // `selectNodeContents` ile ölçersek o alt düğümün ekran dışı kutusu
    // birleşime karışır ve GÖRÜNEN metin taşmış gibi okunur (ilk koşumda
    // `a.jargon-term` bu yüzden -107px raporluyordu). Ölçülen şey ögenin
    // KENDİ metin düğümleridir, alt ağacı değil.
    let r = null;
    for (const n of el.childNodes) {
      if (n.nodeType !== 3 || !n.textContent.trim()) continue;
      const tr = document.createRange(); tr.selectNodeContents(n);
      const b = tr.getBoundingClientRect();
      if (b.width === 0 && b.height === 0) continue;
      r = r ? { left: Math.min(r.left, b.left), right: Math.max(r.right, b.right), width: 1, height: 1 } : { left: b.left, right: b.right, width: b.width, height: b.height };
    }
    if (!r) continue;
    const eb = effectiveBounds(el, own);
    if (eb.reachable) continue;
    const visRight = Math.min(r.right, eb.right);
    const visLeft = Math.max(r.left, eb.left);
    const over = Math.round(visRight - vw);
    const under = Math.round(-visLeft);
    if (over <= 1 && under <= 1) continue;

    // YANLIŞ-POZİTİF SINIFI 2 — off-canvas panel (kapalı mobil menü, sheet).
    // Ayırt edici ölçüt: AMPUTE bir öge sınırı YARIP GEÇER (bir kısmı içeride,
    // bir kısmı dışarıda). Tamamen dışarıdaki öge kırpılmış değil, SAHNE
    // DIŞINDADIR — transform ile itilmiş bir panelin içeriğidir.
    const straddlesRight = over > 1 && visLeft < vw - 1;
    const straddlesLeft  = under > 1 && visRight > 1;
    if (!straddlesRight && !straddlesLeft) continue;

    if (animated(el)) continue;
    const cls = ((el.className && el.className.baseVal !== undefined) ? el.className.baseVal : (el.className || '')).toString().trim().slice(0, 60);
    const key = el.tagName + '|' + cls + '|' + (el.id || '') + '|' + Math.max(over, under);
    if (seen.has(key)) continue;
    seen.add(key);
    out.push({
      tag: el.tagName.toLowerCase(), id: el.id || '', cls,
      cutPx: Math.max(over, under), side: over > under ? 'sag' : 'sol',
      text: (el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 48),
    });
  }
  return { vw, docScrollW: de.scrollWidth, findings: out.sort((a, b) => b.cutPx - a.cutPx) };
};

async function run() {
  const browser = await chromium.launch();
  const report = { base: BASE, widths: WIDTHS, inject: INJECT, ts: new Date().toISOString(), pages: [] };
  let violations = 0, loadFailures = 0;

  for (const p of PAGES) {
    for (const width of WIDTHS) {
      const ctx = await browser.newContext({ viewport: { width, height: HEIGHT }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 });
      const page = await ctx.newPage();
      let rec = { name: p.name, path: p.path, width };
      try {
        const resp = await page.goto(BASE + p.path, { waitUntil: 'networkidle', timeout: 45000 });
        rec.httpStatus = resp ? resp.status() : 0;
        if (rec.httpStatus >= 400) { loadFailures++; rec.error = 'HTTP ' + rec.httpStatus; }
        else {
          // CPO-1198 dersi: kapalı <details> ölçmek kapsamı yalan söyler
          await page.evaluate(() => document.querySelectorAll('details').forEach(d => { d.open = true; }));
          await page.waitForTimeout(900);
          const m = await page.evaluate(PROBE, INJECT);
          rec = { ...rec, ...m };
          violations += m.findings.length;
        }
      } catch (e) {
        loadFailures++; rec.error = String(e && e.message || e);
      }
      await ctx.close();
      report.pages.push(rec);
      const n = rec.findings ? rec.findings.length : '-';
      if (rec.findings && rec.findings.length) {
        console.log(`FAIL ${p.name}@${width}: ${n} kirpilmis oge`);
        rec.findings.slice(0, 6).forEach(f => console.log(`     -${f.cutPx}px ${f.tag}${f.id ? '#' + f.id : ''}${f.cls ? '.' + f.cls.split(' ')[0] : ''}  "${f.text}"`));
      } else if (!rec.error) {
        console.log(`ok   ${p.name}@${width}`);
      } else {
        console.log(`ERR  ${p.name}@${width}: ${rec.error}`);
      }
    }
  }
  await browser.close();
  report.violations = violations; report.loadFailures = loadFailures;
  await fs.mkdir(path.dirname(OUT), { recursive: true });
  await fs.writeFile(OUT, JSON.stringify(report, null, 2));
  console.log(`\nKAPI 83 — kirpilmis-kaydirilamaz oge: ${violations} | yuklenemeyen: ${loadFailures} | rapor: ${OUT}`);
  if (violations > 0 || loadFailures > 0) process.exit(2);
}
run();
