#!/usr/bin/env node
// tools/live-region-check.js — CANLI BÖLGE (aria-live / role=status|alert) denetçisi
//
// Neden var: `role="status"` ARIA'da varsayılan olarak `aria-atomic="true"` demektir.
// Bu rol, içi JS'le doldurulan BÜYÜK bir kapsayıcıya konduğunda her yeniden render
// (filtre değişimi, periyodik yenileme) TÜM alt ağacı ekran okuyucuya baştan okutur.
// 21.09 ölçümü: /bilanco-takvimi #periodsContainer 190, /temettu-takvimi
// #stocksContainer 112 odaklanabilir denetim taşıyordu ve iki sayfa da kendini
// periyodik yeniliyordu. Statik şablon taraması bunu GÖREMEZ — kapsayıcı şablonda
// boştur, denetimler çalışma anında gelir. Bu yüzden canlı ölçüm.
//
// Ölçüt: canlı bölgenin İÇİNDE odaklanabilir denetim sayısı. 0 = temiz.
// Kısa mesaj kutuları (1 buton/link taşıyan boş-durum, "yeniden dene" linki)
// kasıtlıdır → BILGI olarak raporlanır, eşik LIMIT ile ayarlanır.
//
// Kullanım: node tools/live-region-check.js [--base=...] [--limit=1]
// ⛔ ÖLÜ ROTA BİR KAPSAM YALANIDIR (21.09, K-S turunda yakalandı)
// Bu betiğin sayfa listesinde `/portfoy` yazıyordu; gerçek rota `/portfolio`.
// 404 sayfası da 'networkidle' ile sorunsuz YÜKLENİR, üstelik header/footer'ı
// taşır — denetçi hiçbir ihlal görmez ve sayfayı "TEMİZ" raporlar. Sitenin en
// etkileşimli sayfalarından biri böylece hiç ölçülmemiş oldu. Bu yüzden artık
// HTTP durumu kontrol edilir: >=400 dönen rota SESSİZCE GEÇMEZ, ihlal sayılır.
const { chromium } = require('playwright');
// ⚠️ BEKLENEN 4xx: `/profil` tokensiz gelindiginde BILEREK 404 doner ama sitenin
// markali hata varyantini RENDER EDER (app.py profil_page). Yani olu rota degil —
// ama olculen sayfa da adi gecen sayfa DEGILDIR: token'li gercek profil formu bu
// turda hic olculmemistir. Bu yuzden beklenen-4xx listesi olcumu SURDURUR, fakat
// hangi varyantin olculdugunu acikca yazar.
const EXPECT_4XX = new Set(['/profil']);
const BASE = (process.argv.find(a => a.startsWith('--base=')) || '').split('=')[1] || 'https://borsapusula.com';
const LIMIT = parseInt((process.argv.find(a => a.startsWith('--limit=')) || '').split('=')[1] || '1', 10);
const PAGES = ['/', '/ozet', '/tarama', '/gundem', '/hisseler', '/sektor-harita', '/hisse/ASELS',
  '/karsilastir', '/portfolio', '/bilanco-takvimi', '/temettu-takvimi', '/blog', '/iletisim',
  '/profil', '/metodoloji', '/hakkinda', '/yasal', '/gizlilik'];

const FOCUSABLE = 'a[href],button,input,select,textarea,[tabindex]:not([tabindex="-1"]),summary,[role="link"],[role="button"]';

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true });
  let fail = 0, info = 0;
  for (const path of PAGES) {
    const page = await ctx.newPage();
    try {
      const _resp = await page.goto(BASE + path, { waitUntil: 'networkidle', timeout: 45000 });
      if (_resp && _resp.status() >= 400) {
        if (EXPECT_4XX.has(path)) { console.log(`bilgi  ${path}  HTTP ${_resp.status()} — BEKLENEN hata varyanti olculuyor (gercek sayfa degil)`); }
        else { console.log(`OLU-ROTA  ${path}  HTTP ${_resp.status()} — bu rota HIC olculmuyor`); fail++; await page.close(); continue; }
      }
      await page.waitForTimeout(1000);
      const rows = await page.evaluate((F) => {
        const out = [];
        document.querySelectorAll('[role="status"],[role="alert"],[aria-live]').forEach(el => {
          const n = el.querySelectorAll(F).length;
          if (!n) return;
          const sel = el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') +
            (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\s+/)[0] : '');
          out.push({ sel, role: el.getAttribute('role') || '', live: el.getAttribute('aria-live') || '', n });
        });
        return out;
      }, FOCUSABLE);
      for (const r of rows) {
        const bad = r.n > LIMIT;
        if (bad) fail++; else info++;
        console.log(`${bad ? 'FAIL' : 'bilgi'}  ${path}  ${r.sel} role=${r.role || '-'} live=${r.live || '-'} → ${r.n} odaklanabilir`);
      }
    } catch (e) {
      console.log(`HATA  ${path}  ${e.message.split('\n')[0]}`);
      fail++;
    }
    await page.close();
  }
  console.log(`\nTOPLAM — FAIL:${fail} bilgi:${info} (eşik: canlı bölge içinde >${LIMIT} odaklanabilir denetim)`);
  await browser.close();
  process.exit(fail > 0 ? 1 : 0);
})();
