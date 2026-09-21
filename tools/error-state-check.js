#!/usr/bin/env node
/* ─────────────────────────────────────────────────────────────────────────
   K-U — HATA VE BOS DURUM YUZEYLERI (CPO, 21.09.2026)  KAPI DEGIL, canli denetci.

   ⛔ NEDEN VAR: MUTLU YOL BIR KAPSAM YALANIDIR
   -------------------------------------------
   K-S "olu rota", K-T "gizli sekme" dersini verdi; ikisi de ayni ailenin
   uyesiydi: *kapsam listesi bir sayfa adi degil, GERCEKTEN OLCULEN PIKSELDIR.*
   Bugune kadarki YEDI canli denetci (K-L/K-M/K-N/K-O/K-P/K-Q/K-T) sayfayi
   HER ZAMAN API'ler 200 donerken ve veri doluyken olctu. Oysa bu sablonlarda
   ~40 ayri HATA/BOS DURUM dali var (`.empty-box` · `.empty-state` · `.ac-empty`
   · `.cmp-empty-state` · `.kap-empty` · `.news-error` · `.pf-fetch-error` ·
   `.empty-msg` · `.loading-msg` + satir-ici yazilmis olanlar) ve bu daldaki
   DOM hicbir denetcide HIC render edilmedi. K-T'nin kendi itirafi da buydu:
   `.news-retry-btn` ihlali ancak ELLE kurulan hata durumunda gorulebilmisti.

   YONTEM — DURUMU ZORLA, SONRA AYNI PROBLARI KOSTUR
   -------------------------------------------------
   Her senaryo icin AYRI TEMIZ YUKLEME (faz izolasyonu). `page.route` ile ilgili
   API'ler 500 / bos payload'a cevrilir ya da bir eylem (filtre/arama) bos
   sonuca zorlanir. Sonra BES eksenin canli problari OLDUGU GIBI yeniden
   kullanilir (yeniden turetilmez) — K-T ile birebir ayni AXES tablosu:
     U1 dokunma hedefi   -> tools/tap-target-check.js       (elementFromPoint)
     U2 odak gorunurlugu -> tools/focus-visible-check.js    (A/B boyama)
     U3 metin kontrasti  -> tools/live-contrast-check.js    (kendi tint zemini)
     U4 metin-disi kontr.-> tools/nontext-contrast-check.js (1.4.11)
     U5 metin kirpilmasi -> tools/text-clip-check.js PROBE  (HARD/PLACE)

   TABAN → SENARYO → DELTA: ayni sayfanin MUTLU YOL olcumu TABAN'dir; hata
   durumunda cikan YENI anahtarlar senaryonun kendi bulgusudur. Delta bir
   SUNUM bicimidir, kapsam kisitlamasi degil — iki sayi da yazilir (K-R dersi).

   SERT KAPI: senaryo, beklenen hata/bos ogeyi GERCEKTEN ekrana getirmediyse
   (`expect` seciciyle 0px² ya da yok) olcum "KAPSAM YALANI" diye REDDEDILIR —
   sessizce "TEMIZ" raporlanmaz.

   Kullanim:
     node tools/error-state-check.js [--base=https://borsapusula.com]
                                     [--w=390,1280] [--only=gundem-api-500]
   Hedef: her senaryoda YENI ihlal = 0.
   ───────────────────────────────────────────────────────────────────────── */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const arg = (k, d) => (process.argv.find(a => a.startsWith(`--${k}=`)) || '').split('=')[1] || d;
const BASE = arg('base', 'https://borsapusula.com');
const WIDTHS = arg('w', '390,1280').split(',').map(n => parseInt(n, 10));
const ONLY = arg('only', '');

const SRC = f => fs.readFileSync(path.join(__dirname, f), 'utf8');
const TAP = SRC('tap-target-check.js');
const FOCUS = SRC('focus-visible-check.js');
const TEXTC = SRC('live-contrast-check.js');
const NONTEXT = SRC('nontext-contrast-check.js');
const { PROBE: CLIP } = require('./text-clip-check.js');

const AXES = [
  { id: 'U1-TAP', run: async p => JSON.parse(await p.evaluate(TAP)),
    rows: r => (r.agg || []).map(a => ({ key: 'TAP|' + a.sel, line: `${a.sel}  ${a.w}x${a.h}  n=${a.n}  "${a.txt}"` })) },
  { id: 'U2-FOCUS', run: async p => JSON.parse(await p.evaluate(FOCUS)),
    rows: r => [
      ...(r.Aagg || []).map(a => ({ key: 'FOCUS-A|' + a.k, line: `[A hic halka yok] ${a.k}  n=${a.n}` })),
      ...(r.Bagg || []).map(a => ({ key: 'FOCUS-B|' + a.k, line: `[B halka boguluyor] ${a.k}  gorunen kenar=${a.d.vis}  n=${a.n}` })),
    ] },
  { id: 'U3-TEXT', run: async p => p.evaluate(TEXTC),
    rows: r => (r.HARD || []).map(v => ({ key: 'TEXT|' + v.sig + '|' + v.ratio,
      line: `${v.sig}  ${v.ratio}:1 (gereken ${v.need})  fg=${v.fg} bg=${v.bg}  "${v.text}"` })) },
  { id: 'U4-NONTEXT', run: async p => p.evaluate(NONTEXT),
    rows: r => [
      ...(r.HARD || []).map(v => ({ key: 'NONTEXT|' + v.sig, line: `${v.sig}  skor=${v.score}  n=${v.count}` })),
      ...(r.ICONS || []).map(v => ({ key: 'ICON|' + v.sig, line: `[ikon] ${v.sig}  en iyi=${v.best}  ${v.box}` })),
    ] },
  { id: 'U5-CLIP', run: async p => p.evaluate(CLIP),
    rows: r => (r || []).filter(x => x.kind === 'HARD' || x.kind === 'PLACE').map(v => ({
      key: 'CLIP|' + v.kind + '|' + v.node + '|' + v.text.slice(0, 24),
      line: `[${v.kind}] ${v.node} < ${v.clipper}  R+${v.ovR} B+${v.ovB}  "${v.text}"` })) },
];

/* ── Yardimcilar ───────────────────────────────────────────────────────── */
const fail500 = pats => pats.map(p => ({ pat: p, status: 500, body: '{"error":"forced"}' }));
const emptyJson = (pat, body) => ({ pat, status: 200, body });

/* ── SENARYOLAR ────────────────────────────────────────────────────────────
   page      : rota
   routes    : [{pat, status, body}] — pat bir substring; istek URL'i icerirse uygulanir
   act       : opsiyonel async (page) => {}   (filtre/arama ile bos sonuca zorlama)
   expect    : senaryonun GERCEKTEN ekrana getirdigi ogenin secicisi (sert kapi)
   clicks    : act tiklama iceriyorsa true  → odak ekseni icin gercek Tab basilir
   ────────────────────────────────────────────────────────────────────────── */
const SCENARIOS = [
  { id: 'gundem-api-500', page: '/gundem',
    routes: fail500(['/api/gundem', '/api/market-news', '/api/economic-calendar', '/api/macro-news', '/api/macro-summary']),
    expect: '.empty-box' },

  { id: 'karsilastir-api-500', page: '/karsilastir?t=ASELS,GARAN',
    routes: fail500(['/api/karsilastir']), expect: '.empty-state' },

  /* ⛔ GECICI DURUM: `.ac-empty` acilir liste INPUT ODAKTA KALDIGI SURECE yasar
     (blur -> closeDropdown 150ms). Bu yuzden TIKLAMA + sonradan `Tab` yaklasimi
     durumu OLCUMDEN ONCE KAPATIR. Cozum: hic tiklamadan `focus()` + GERCEK tus
     olaylari -> giris modu zaten "klavye", telafi Tab'ina gerek YOK. */
  { id: 'karsilastir-ac-bos', page: '/karsilastir',
    act: async p => { await p.focus('#t1'); await p.keyboard.type('ZZZ', { delay: 90 }); await p.waitForTimeout(1200); },
    expect: '.ac-empty' },

  { id: 'bilanco-filtre-bos', page: '/bilanco-takvimi',
    routes: [emptyJson('/api/bilanco-takvimi', '{"periods":["2026/Q2"],"current_period":"2026/Q2","stocks":[]}')],
    expect: '.empty-state, .loading-msg' },

  { id: 'bilanco-api-500', page: '/bilanco-takvimi',
    routes: fail500(['/api/bilanco-takvimi']), expect: '.empty-state, .loading-msg' },

  { id: 'temettu-bos', page: '/temettu-takvimi',
    routes: [emptyJson('/api/temettu-takvimi', '{"stocks":[]}')],
    expect: '.empty-state, .loading-msg' },

  { id: 'temettu-api-500', page: '/temettu-takvimi',
    routes: fail500(['/api/temettu-takvimi']), expect: '.empty-state, .loading-msg' },

  { id: 'portfolio-bos', page: '/portfolio', expect: '#emptyMsg' },

  { id: 'portfolio-fetch-hata', page: '/portfolio',
    /* ⚠️ `id` SAYISAL olmali: sablon `onclick="removePosition(${p.id})"` uretir,
       string bir id tirnaksiz gomulunce ReferenceError'a duser ve dugmeler
       SESSIZCE olu kalir — bu, ✎/✕ isabet hatasini YANLIS NEGATIF gostermisti. */
    seed: () => { try { localStorage.setItem('bp_portfolio', JSON.stringify([
      { id: 1758400001, ticker: 'ASELS', lot: 10, price: 50 },
      { id: 1758400002, ticker: 'GARAN', lot: 5, price: 120 }])); } catch (e) {} },
    routes: fail500(['/api/data', '/api/tarama']), expect: '#pfFetchError' },

  /* ⛔ DOLU PORTFOY DE BIR KAPSAM BOSLUGUDUR: `localStorage` temiz baslar, bu
     yuzden yedi canli denetci /portfolio'yu HEP bos durumda (`#emptyMsg`)
     gordu; tablo/kart satirlari hic var olmadi. Mutlu yolda da olculur. */
  { id: 'portfolio-dolu', page: '/portfolio',
    seed: () => { try { localStorage.setItem('bp_portfolio', JSON.stringify([
      { id: 1758400001, ticker: 'ASELS', lot: 10, price: 50 },
      { id: 1758400002, ticker: 'GARAN', lot: 5, price: 120 }])); } catch (e) {} },
    expect: '#pfBody tr, .pf-mcard' },

  { id: 'sektor-compare-hata', page: '/sektor-harita',
    routes: fail500(['/api/sektor-compare']),
    act: async p => {
      await p.click('#sektTabBtnCmp'); await p.waitForTimeout(1200);
      const chips = await p.$$('#sectorChips .sector-chip, #sectorChips button, #sectorChips [role="button"]');
      if (chips.length >= 2) { await chips[0].click(); await chips[1].click(); await p.waitForTimeout(300); }
      await p.click('#compareBtn'); await p.waitForTimeout(1600);
    },
    clicks: true, expect: '.cmp-empty-state' },

  { id: 'sektor-summary-500', page: '/sektor-harita',
    routes: fail500(['/api/sektor-summary']),
    act: async p => { await p.click('#sektTabBtnCmp'); await p.waitForTimeout(1200); },
    clicks: true, expect: '#sectorChips span' },

  { id: 'tarama-filtre-bos', page: '/tarama',
    routes: [emptyJson('/api/tarama', '{"stocks":[],"total":0}')],
    expect: '.empty-state' },

  { id: 'hisse-haber-hata', page: '/hisse/ASELS',
    routes: fail500(['/news']), tab: 'haberler', clicks: true, expect: '.news-error' },

  { id: 'hisse-kap-bos', page: '/hisse/ASELS',
    routes: [emptyJson('/kap', '{"disclosures":[]}')], tab: 'haberler', clicks: true, expect: '.kap-empty' },

  { id: 'hisse-grafik-hata', page: '/hisse/ASELS',
    routes: fail500(['/chart', '/mtf']), tab: 'grafik', clicks: true, expect: '#chart-section' },

  { id: 'hisse-ai-hata', page: '/hisse/ASELS',
    routes: fail500(['/signal-explanation', '/signal-story']), tab: 'ai', clicks: true, expect: '#tabpanel-ai, [data-tab-content~="ai"]' },

  /* NOT: `/fundamentals` bos donunce `#fundSection` `.da-fund-empty` ile
     `display:none` olur (TASARIM GEREGI — bos kabuk gostermez), olculecek bir
     hata yuzeyi YOKTUR. Onun yerine Ozet sekmesindeki gercek bos-durum metni
     ("Gecmis bulunamadi") `/chart` payload'i ile zorlanir. */
  { id: 'hisse-gecmis-bos', page: '/hisse/ASELS',
    routes: [emptyJson('/chart', '{"chart":{"signal_history":[],"summary":{}}}')],
    expect: '#historyBody' },

  { id: 'blog-arama-bos', page: '/blog',
    act: async p => { await p.focus('#blogSearch'); await p.keyboard.type('zzzqqq', { delay: 60 }); await p.waitForTimeout(900); },
    expect: '#noResults' },

  { id: '404-hisse-bulunamadi', page: '/bu-sayfa-yok-zzz', expect4xx: true,
    act: async p => { await p.focus('#q404'); await p.keyboard.type('ZZZZZZ', { delay: 60 });
      await p.keyboard.press('Enter');                    // ipucu yalnizca SUBMIT'te yazilir
      await p.waitForTimeout(900); },
    expect: '#q404Hint' },
];

async function applyRoutes(page, routes) {
  if (!routes || !routes.length) return;
  await page.route('**/api/**', async route => {
    const u = route.request().url();
    const hit = routes.find(r => u.includes(r.pat));
    if (hit) return route.fulfill({ status: hit.status, contentType: 'application/json', body: hit.body });
    return route.continue();
  });
}

async function measure(ctx, sc, isBase) {
  const page = await ctx.newPage();
  await page.addInitScript(() => {
    try { localStorage.removeItem('bp_hisse_tab'); localStorage.removeItem('bp_portfolio'); } catch (e) {}
  });
  if (!isBase && sc.seed) await page.addInitScript(sc.seed);
  if (!isBase) await applyRoutes(page, sc.routes);

  const resp = await page.goto(BASE + sc.page, { waitUntil: 'networkidle', timeout: 60000 });
  const st = resp ? resp.status() : 0;
  if (st >= 400 && !sc.expect4xx) { await page.close(); throw new Error(`HTTP ${st} — OLU ROTA`); }
  await page.waitForTimeout(1400);

  let clicked = false;
  if (sc.tab) {
    const sel = `#tab-${sc.tab}`;
    if (!(await page.$(sel))) { await page.close(); throw new Error(`sekme dugmesi yok: ${sel}`); }
    await page.click(sel); clicked = true;
    await page.waitForTimeout(1800);
  }
  if (!isBase && sc.act) { await sc.act(page); clicked = clicked || !!sc.clicks; }

  /* ⛔ K-T 1. sahte-pozitif sinifi: tiklama giris modunu "isaretleyici"ye
     cevirir → programatik focus() :focus-visible eslesmez → U2 sayfadaki HER
     kontrolu "halka yok" sanir. Tek GERCEK klavye olayi modu geri alir. */
  if (clicked) { await page.keyboard.press('Tab'); await page.waitForTimeout(250); }

  /* SERT KAPI — durum gercekten ekranda mi? */
  let px = 0;
  if (!isBase) {
    px = await page.evaluate(sel => {
      let a = 0;
      document.querySelectorAll(sel).forEach(el => {
        const r = el.getBoundingClientRect();
        const cs = getComputedStyle(el);
        if (cs.display === 'none' || cs.visibility === 'hidden') return;
        a += Math.round(r.width * r.height);
      });
      return a;
    }, sc.expect);
    if (!px) { await page.close(); throw new Error(`durum EKRANA GELMEDI (${sc.expect} = 0px²) — KAPSAM YALANI`); }
  }

  const out = {};
  for (const ax of AXES) {
    try { out[ax.id] = ax.rows(await ax.run(page)); }
    catch (e) { out[ax.id] = [{ key: 'ERR|' + ax.id, line: 'PROB HATASI: ' + e.message.split('\n')[0] }]; }
  }
  await page.close();
  return { out, px };
}

(async () => {
  const browser = await chromium.launch();
  let totalNew = 0, rejected = 0;
  const list = ONLY ? SCENARIOS.filter(s => ONLY.split(',').includes(s.id)) : SCENARIOS;
  for (const W of WIDTHS) {
    const ctx = await browser.newContext({
      viewport: { width: W, height: W < 768 ? 844 : 900 },
      deviceScaleFactor: 2, isMobile: W < 768, hasTouch: W < 768,
    });
    /* Ayni rotanin MUTLU YOL tabani bir kez olculur, senaryolar arasi paylasilir. */
    const baseCache = new Map();
    for (const sc of list) {
      console.log(`\n████ ${sc.id}  (${sc.page}) @${W}px`);
      let baseKeys = baseCache.get(sc.page);
      if (!baseKeys) {
        try {
          const b = await measure(ctx, { ...sc, routes: null, act: null, seed: null, tab: null }, true);
          baseKeys = new Set([].concat(...AXES.map(a => b.out[a.id].map(x => x.key))));
        } catch (e) { console.log(`  ⚠ TABAN alinamadi: ${e.message} — delta YOK, tum bulgular yeni sayilir`); baseKeys = new Set(); }
        baseCache.set(sc.page, baseKeys);
      }
      let r;
      try { r = await measure(ctx, sc, false); }
      catch (e) { console.log(`  ✖ REDDEDILDI: ${e.message}`); rejected++; continue; }
      const rows = [].concat(...AXES.map(a => r.out[a.id].map(x => ({ ...x, ax: a.id }))));
      const fresh = rows.filter(x => !baseKeys.has(x.key));
      totalNew += fresh.length;
      console.log(`  ── durum ${r.px}px² · toplam ${rows.length} · YENI ${fresh.length}`);
      const byAx = {};
      fresh.forEach(x => { (byAx[x.ax] = byAx[x.ax] || []).push(x.line); });
      for (const [ax, lines] of Object.entries(byAx)) {
        console.log(`     ${ax} (${lines.length})`);
        lines.slice(0, 14).forEach(l => console.log(`       • ${l}`));
        if (lines.length > 14) console.log(`       … +${lines.length - 14}`);
      }
    }
    await ctx.close();
  }
  console.log(`\nTOPLAM YENI (hata/bos durumlarda) = ${totalNew}   ·   REDDEDILEN senaryo = ${rejected}`);
  await browser.close();
  process.exit(totalNew > 0 ? 1 : 0);
})();
