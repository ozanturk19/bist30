#!/usr/bin/env node
// tools/autorefresh-focus-check.js — K-AX: PERİYODİK YENİLEME KULLANICININ YERİNİ SİLİYOR
// WCAG 2.1 · SC 2.2.2 "Pause, Stop, Hide" (A) — otomatik güncellenen bilgi
//            SC 2.4.3 "Focus Order" (A)      — odak sırası anlamı/işletilebilirliği korumalı
//
// SORU — SİTE 15 SAYFADA KENDİ KENDİNİ YENİLİYOR, KİMSE "KULLANICI O SIRADA
// NEREDEYDİ?" DİYE SORMADI:
//   /portfolio 60sn'de bir `tbody.innerHTML = ...` ile TÜM satırları baştan
//   yazıyor. O satırların içinde `<a class="ticker-link">`, `✎ düzenle` ve
//   `✕ kaldır` düğmeleri var. Klavyeyle "✕ ASELS pozisyonunu kaldır"a gelen
//   kullanıcı bir saniye duraksarsa düğme YOK EDİLİR, `document.activeElement`
//   `<body>`ye düşer: Enter hiçbir şey yapmaz, Tab belgenin EN BAŞINDAN
//   yeniden başlar. 20 pozisyonluk bir portföyde bu ~45 Tab demek — ve 60
//   saniyede bir TEKRARLIYOR. Yavaş bir klavye kullanıcısı alt satırlara
//   yapısal olarak HİÇ ulaşamayabilir.
//
//   Hata yok, konsol çıktısı yok, ekranda görsel fark yok. Fare kullanıcısı
//   hiçbir şey fark etmez. Tam da bu yüzden 20 tur denetimden geçti.
//
// ⛔ ZAMANLAYICIYI TAHMİN ETMİYORUM, SAYFADAN ALIYORUM: `setInterval` sayfa
//   betikleri çalışmadan ÖNCE sarmalanıyor; ölçümde çağırdığım `fn`, saniyesi
//   gelince tarayıcının çağıracağı fonksiyon REFERANSININ TA KENDİSİ. "Bence
//   şu fonksiyon yeniler" diye bir varsayım yok. (<1sn'lik zamanlayıcılar
//   animasyon/sayaçtır, kapsam dışı.)
//
// ⛔ ODAK KAYBINI ÇIKARSAMIYORUM, ÖLÇÜYORUM: yok edilen öğeyi bulmak için
//   işaretleme kullanılıyor (A fazı), ama "odak gerçekten düştü mü" ayrı bir
//   fazda (B) öğeye GERÇEKTEN odaklanıp yenileme çalıştırılarak ve sonra
//   `document.activeElement` okunarak kanıtlanıyor. İşaretin kaybolması
//   odak kaybının KANITI değil, göstergesidir; ikisini karıştırmak
//   [[feedback_bayragin_varligi_olcum_kaniti_degildir]] hatasıdır.
//
// BULGU SINIFLARI (ikisinin de tabanı SIFIR):
//   A) ODAK İMHASI — periyodik yenileme, o an odakta olan öğeyi yok ediyor ve
//      odak <body>ye düşüyor. (B fazında canlı kanıtlanır.)
//   B) KAYDIRMA SIFIRLANMASI — yenileme, kullanıcının elle kaydırdığı bir
//      kabın `scrollLeft/scrollTop` konumunu başa sarıyor. (K-AF sonrası makro
//      şerit `prefers-reduced-motion` altında ELLE kaydırılabilir; 180sn'de
//      bir başa sararsa kullanıcı NASDAQ'ı görmeye asla yetişemez.)
//
// AYRI SAYILIR (bulgu DEĞİL):
//   · Yenilemenin yok ettiği ama odakta OLMAYAN öğeler — innerHTML yeniden
//     yazımı tek başına kusur değildir; kusur, kullanıcının yerinin silinmesi.
//     Kaç öğenin risk altında olduğu ayrıca raporlanır (gürültü yapmaz).
//   · Odağı <body>ye değil de MANTIKLI bir yere taşıyan yenileme — ölçülür,
//     ayrı raporlanır, sapma sayılmaz.
//
// ⛔ VERİSİZ SAYFA BİR KAPSAM YALANI: boş bir /portfolio'da `tbody` BOŞTUR —
//   yok edilecek odaklanabilir öğe olmadığı için dedektör "temiz" der. Bu
//   yüzden ölçümden önce localStorage'a gerçek pozisyonlar tohumlanıyor.
//   ("Mutlu yol kapsam yalanı"nın tersi: burada mutsuz yol değil, BOŞ yol
//   yalan söylüyordu.)
//
// POZİTİF KONTROL (--kill-fix): bir fix'in gerçekten ölçülüp ölçülmediğini
//   sınamak için, ölçümden hemen önce sayfaya odak-koruma kodunu SÖKEN bir
//   yama enjekte edilir. Dedektör bunu yakalamazsa kördür.
//
// Kullanım: node tools/autorefresh-focus-check.js [--base=...] [--only=/a,/b]
//           [--kill-fix] [--json=dosya] [--settle=ms]
const { chromium } = require('playwright');

const arg = n => (process.argv.find(a => a.startsWith('--' + n + '=')) || '').split('=')[1] || '';
const BASE = arg('base') || 'https://borsapusula.com';
const ONLY = arg('only');
const JSON_OUT = arg('json');
const SETTLE = parseInt(arg('settle') || '2600', 10);
const KILL_FIX = process.argv.includes('--kill-fix');
// --sim-fix: K-AX fix'inin CANLI sayfadaki doğrulaması. Fix henüz deploy
//   edilmediği için YEREL `static/bp-search.js` canlı sayfaya enjekte edilir
//   (bpPreserveFocus'u tanımlar) ve zamanlayıcı `fn()` yerine deploy sonrası
//   çalışacak olan `bpPreserveFocus(fn)()` ile çağrılır. Şablonlardaki
//   değişiklik tam olarak budur — yani bu, fix'in kendisinin ölçümüdür,
//   benzeri değil.
const SIM_FIX = process.argv.includes('--sim-fix');
// Yardimci, YEREL bp-search.js'ten KESILEREK alinir -- yeniden yazilmaz. Olculen
// sey, deploy edilecek kaynagin TA KENDISIDIR. (Once HTTP ikamesi denendi:
// B fazi sayfayi yeniden yukluyor ve ikinci gezinmede betik TARAYICI
// ONBELLEGINDEN geliyor, route hic cagrilmiyordu -- yani sessizce fix'siz
// canli dosya olculuyordu. addInitScript her gezinmede calisir, onbellekten
// etkilenmez.)
const HELPER_SRC = (() => {
  if (!SIM_FIX) return '';
  const src = require('fs').readFileSync(
    require('path').join(__dirname, '..', 'static', 'bp-search.js'), 'utf8');
  const a = src.indexOf('function bpFocusKey(');
  const b = src.indexOf('window.bpStartMacroTicker');
  if (a < 0 || b < 0 || b <= a) throw new Error('bp-search.js icinde K-AX yardimcisi bulunamadi');
  const cut = src.slice(a, b);
  if (cut.indexOf('window.bpPreserveFocus') < 0) throw new Error('kesilen blok bpPreserveFocus tanimlamiyor');
  return cut;
})();

// Periyodik zamanlayıcısı OLAN sayfalar. (Yalnız 180sn makro şeridi taşıyan
// sayfalar da dahil: şerit reduce-motion altında elle kaydırılabilir, yani
// B ekseninde ölçülmeleri gerekir.)
const PAGES = [
  { path: '/portfolio',        seedPortfolio: true },
  { path: '/sektor-harita' },
  { path: '/gundem' },
  { path: '/bilanco-takvimi' },
  { path: '/temettu-takvimi' },
  { path: '/' },
  { path: '/tarama' },
  { path: '/hisse/ASELS' },
  { path: '/ozet' },
  { path: '/karsilastir' },
];

// Tohumlanan portföy — gerçek BIST kodları, gerçek satır sayısı.
const SEED = JSON.stringify([
  { id: 1, ticker: 'ASELS', lot: 100, price: 52.30, date: '2026-01-15' },
  { id: 2, ticker: 'GARAN', lot: 250, price: 118.40, date: '2026-02-03' },
  { id: 3, ticker: 'THYAO', lot: 40,  price: 281.00, date: '2026-03-11' },
  { id: 4, ticker: 'AKBNK', lot: 300, price: 64.75,  date: '2026-04-22' },
]);

const INIT = () => {
  // Sayfa betikleri çalışmadan ÖNCE: periyodik zamanlayıcıları yakala.
  window.__bpTimers = [];
  const orig = window.setInterval;
  window.setInterval = function (fn, delay) {
    // <1sn = animasyon/sayaç, kapsam dışı. Yalnız fonksiyon referansları.
    if (typeof fn === 'function' && Number(delay) >= 1000) {
      window.__bpTimers.push({ fn: fn, delay: Number(delay) });
    }
    return orig.apply(this, arguments);
  };
};

const FOCUSABLE = 'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';

async function run() {
  const browser = await chromium.launch();
  const pages = ONLY ? PAGES.filter(p => ONLY.split(',').includes(p.path)) : PAGES;
  const report = [];
  const tot = { destroyed: 0, scrollReset: 0, atRisk: 0, timers: 0, moved: 0, errors: 0 };

  for (const P of pages) {
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    const page = await ctx.newPage();
    if (SIM_FIX) {
      await page.addInitScript(src => { (0, eval)(src); }, HELPER_SRC);
    }
    await page.addInitScript(INIT);
    if (P.seedPortfolio) {
      await page.addInitScript(seed => {
        try { localStorage.setItem('bp_portfolio', seed); } catch (e) {}
      }, SEED);
    }
    if (KILL_FIX) {
      // Pozitif kontrol: odak-koruma yardımcısını sök.
      await page.addInitScript(() => { window.__bpKillFocusRestore = true; });
    }

    const out = { path: P.path, timers: [], destroyed: [], scrollReset: [], moved: [], atRisk: 0 };
    try {
      await page.goto(BASE + P.path, { waitUntil: 'domcontentloaded', timeout: 45000 });
      await page.waitForTimeout(SETTLE);

      const nTimers = await page.evaluate(() => (window.__bpTimers || []).length);
      tot.timers += nTimers;
      out.timers = await page.evaluate(() => (window.__bpTimers || []).map(t => t.delay));

      for (let i = 0; i < nTimers; i++) {
        // ── A FAZI: yenileme NEYİ yok ediyor? ──────────────────────────────
        const a = await page.evaluate(async ({ i, FOCUSABLE }) => {
          const els = Array.from(document.querySelectorAll(FOCUSABLE))
            .filter(e => e.offsetParent !== null || e.getClientRects().length);
          els.forEach((e, n) => e.setAttribute('data-bpfx', String(n)));
          const before = els.map((e, n) => ({
            n,
            tag: e.tagName.toLowerCase(),
            name: (e.getAttribute('aria-label') || e.textContent || '').trim().slice(0, 48),
            sel: e.id ? '#' + e.id : e.className ? '.' + String(e.className).split(/\s+/)[0] : e.tagName.toLowerCase(),
          }));
          // Elle kaydırılabilir kaplar — kaydırma konumunu bozuyor mu?
          const scrollers = Array.from(document.querySelectorAll('*')).filter(e =>
            (e.scrollWidth > e.clientWidth + 4 || e.scrollHeight > e.clientHeight + 4) &&
            /auto|scroll/.test(getComputedStyle(e).overflowX + getComputedStyle(e).overflowY)
          ).slice(0, 40);
          scrollers.forEach((e, n) => {
            e.setAttribute('data-bpsc', String(n));
            // Kullanıcının elle kaydırdığını taklit et (başta değil, ortada).
            if (e.scrollWidth > e.clientWidth + 4) e.scrollLeft = Math.floor(e.scrollWidth / 3);
            else e.scrollTop = Math.floor(e.scrollHeight / 3);
          });
          const scBefore = scrollers.map((e, n) => ({ n, left: e.scrollLeft, top: e.scrollTop,
            sel: e.id ? '#' + e.id : e.className ? '.' + String(e.className).split(/\s+/)[0] : e.tagName.toLowerCase() }));
          try { await window.__bpTimers[i].fn(); } catch (err) {}
          return { before, scBefore };
        }, { i, FOCUSABLE });

        await page.waitForTimeout(SETTLE);

        const b = await page.evaluate(({ before, scBefore }) => {
          const gone = before.filter(x => !document.querySelector('[data-bpfx="' + x.n + '"]'));
          const scMoved = scBefore.filter(x => {
            const e = document.querySelector('[data-bpsc="' + x.n + '"]');
            if (!e) return false;           // kabın kendisi yok edildiyse A ekseninde sayılır
            return (x.left > 0 && e.scrollLeft === 0) || (x.top > 0 && e.scrollTop === 0);
          });
          return { gone, scMoved };
        }, a);

        out.atRisk += b.gone.length;

        // ── B FAZI: odak GERÇEKTEN düşüyor mu? (çıkarım değil, ölçüm) ──────
        if (b.gone.length) {
          // Temiz sayfa: işaretleri ve yenileme yan etkilerini taşımamak için.
          await page.goto(BASE + P.path, { waitUntil: 'domcontentloaded', timeout: 45000 });
          await page.waitForTimeout(SETTLE);
          const victim = b.gone[0];
          const proof = await page.evaluate(async ({ i, sel, name, FOCUSABLE, simFix }) => {
            const cand = Array.from(document.querySelectorAll(FOCUSABLE)).find(e =>
              (e.getAttribute('aria-label') || e.textContent || '').trim().slice(0, 48) === name
            ) || document.querySelector(sel);
            if (!cand || !cand.focus) return { ok: false, why: 'kurban bulunamadi' };
            cand.focus();
            if (document.activeElement !== cand) return { ok: false, why: 'odaklanamadi' };
            // --sim-fix: sablonlarin deploy sonrasi yapacagi cagrinin TA KENDISI.
            var fn = window.__bpTimers[i].fn;
            var call = (simFix && window.bpPreserveFocus) ? window.bpPreserveFocus(fn) : fn;
            try { await call(); } catch (e) {}
            return { ok: true, sarmalandi: !!(simFix && window.bpPreserveFocus) };
          }, { i, sel: victim.sel, name: victim.name, FOCUSABLE, simFix: SIM_FIX });

          if (SIM_FIX && proof.ok && !proof.sarmalandi) {
            console.log('      !! --sim-fix istendi ama bpPreserveFocus sayfada YOK (ikame basarisiz) — olcum GECERSIZ');
          }
          if (proof.ok) {
            await page.waitForTimeout(SETTLE);
            const after = await page.evaluate(() => ({
              tag: document.activeElement ? document.activeElement.tagName.toLowerCase() : '(yok)',
              name: document.activeElement
                ? (document.activeElement.getAttribute('aria-label') || document.activeElement.textContent || '').trim().slice(0, 48)
                : '',
            }));
            if (after.tag === 'body' || after.tag === 'html' || after.tag === '(yok)') {
              out.destroyed.push({ delay: out.timers[i], victim: victim.name || victim.sel, landed: after.tag, count: b.gone.length });
            } else {
              out.moved.push({ delay: out.timers[i], victim: victim.name || victim.sel, landed: after.tag + ' "' + after.name + '"' });
            }
          }
          // Sonraki zamanlayıcı ölçümü için sayfayı tazele.
          await page.goto(BASE + P.path, { waitUntil: 'domcontentloaded', timeout: 45000 });
          await page.waitForTimeout(SETTLE);
        }

        b.scMoved.forEach(s => out.scrollReset.push({ delay: out.timers[i], sel: s.sel }));
      }
    } catch (e) {
      /* ⛔ Bir olcum COKERSE sonuc "temiz" DEGILDIR, "olculemedi"dir. Ilk
         yazimda bu catch hatayi yutuyor, altindaki satir yine de "OK ...
         odak-imhasi=0" basiyordu — B fazi bir ReferenceError yuzunden hic
         calismamisken arac YESIL gorunuyordu. Kapinin sifiri artik olcum
         tamamlandiysa anlamli. */
      out.error = String(e.message).split('\n')[0];
      console.log('  !! ' + P.path + ' → ' + out.error);
    }
    await ctx.close();

    tot.destroyed += out.destroyed.length;
    tot.scrollReset += out.scrollReset.length;
    tot.moved += out.moved.length;
    tot.atRisk += out.atRisk;
    if (out.error) tot.errors++;
    const bad = out.destroyed.length + out.scrollReset.length;
    console.log((out.error ? '!!' : bad ? 'X ' : 'OK') + '  ' + P.path.padEnd(22) +
      ' odak-imhasi=' + out.destroyed.length + ' kaydirma-sifirlama=' + out.scrollReset.length +
      '  (zamanlayici=' + out.timers.length + ', risk-altinda-oge=' + out.atRisk + ', mantikli-tasima=' + out.moved.length + ')');
    out.destroyed.forEach(d => console.log('      ODAK IMHASI  ' + (d.delay / 1000) + 'sn  "' + d.victim + '" -> <' + d.landed + '>  (ayni yenilemede ' + d.count + ' oge yok edildi)'));
    out.scrollReset.forEach(s => console.log('      KAYDIRMA SIFIRLANDI  ' + (s.delay / 1000) + 'sn  ' + s.sel));
    out.moved.forEach(m => console.log('      (mantikli tasima)  ' + (m.delay / 1000) + 'sn  "' + m.victim + '" -> ' + m.landed));
    report.push(out);
  }

  await browser.close();
  console.log('\nTOPLAM: odak-imhasi=' + tot.destroyed + '  kaydirma-sifirlama=' + tot.scrollReset);
  console.log('OLCULDU: periyodik-zamanlayici=' + tot.timers + '  risk-altinda-oge=' + tot.atRisk + '  mantikli-tasima=' + tot.moved + '  OLCULEMEDI=' + tot.errors);
  if (JSON_OUT) require('fs').writeFileSync(JSON_OUT, JSON.stringify({ tot, report }, null, 2));
  process.exit(tot.destroyed + tot.scrollReset + tot.errors ? 1 : 0);
}
run();
