#!/usr/bin/env node
/* ─────────────────────────────────────────────────────────────────────────
   K-T — GIZLI SEKME PANELLERI (CPO, 21.09.2026)   KAPI DEGIL, canli denetci.

   ⛔ NEDEN VAR: GIZLI SEKME BIR KAPSAM YALANIDIR
   ----------------------------------------------
   `/hisse/<t>` dort sekmelidir (Ozet · Grafik · AI Analiz · Haberler) ve
   `/tarama` ikilidir (Teknik · Temel). Sayfa YALNIZ ilk sekme acikken yuklenir;
   digerlerinin panelleri `display:none` olur. Bugune kadarki ALTI canli denetci
   (K-L dokunma hedefi · K-M metin kirpilmasi · K-N canli bolge · K-O odak
   gorunurlugu · K-P metin kontrasti · K-Q metin-disi kontrast) sayfayi acip
   OLDUGU GIBI olcer; hepsi `display:none` / `rect 0x0` ogeleri eler. Yani
   hisse sayfasinin sekmelerinin 3/4'u ve taramanin 1/2'si HIC olculmedi ve
   her turda "TEMIZ" raporlandi.

   Bu, K-S'te yakalanan "OLU ROTA BIR KAPSAM YALANIDIR" dersinin KARDESIDIR:
   orada listedeki satir sayfayi acmiyordu, burada sayfa aciliyor ama
   ICERIGININ COGU render edilmemis oluyor. Ikisinin ortak dersi:
   **kapsam listesi bir sayfa adi degil, GERCEKTEN OLCULEN PIKSELDIR.**

   YONTEM
   ------
   Her (yuzey × genislik × sekme) icin AYRI TEMIZ YUKLEME yapilir (faz
   izolasyonu — K-S'in "olcum sirasi durumu bozar" dersi: tek sayfada sekmeler
   arasi gezinmek tembel yuklemeyi ve odagi kirletir). Sekme tiklanir, panel
   gorunur olana kadar beklenir, sonra DORT+BIR eksenin canli problari
   oldugu gibi yeniden kullanilir (yeniden turetilmez):
     T1 dokunma hedefi   -> tools/tap-target-check.js       (elementFromPoint)
     T2 odak gorunurlugu -> tools/focus-visible-check.js    (A/B boyama)
     T3 metin kontrasti  -> tools/live-contrast-check.js    (kendi tint zemini)
     T4 metin-disi kontr.-> tools/nontext-contrast-check.js (1.4.11)
     T5 metin kirpilmasi -> tools/text-clip-check.js PROBE  (HARD/PLACE)

   TABAN → SEKME → DELTA: ilk sekmenin (Ozet/Teknik) bulgu anahtarlari TABAN
   sayilir; diger sekmelerde ayni anahtar cikarsa "zaten biliniyordu" diye
   isaretlenir, YENI anahtarlar sekmenin kendi bulgusudur. Delta OLCUMU
   DARALTMAZ — her iki sayi da yazilir (K-R dersi: delta bir sunum bicimi,
   kapsam kisitlamasi degil).

   Kullanim:
     node tools/tab-panel-check.js [--base=https://borsapusula.com]
                                   [--w=390,1280] [--only=/hisse/ASELS]
   Hedef: her sekmede YENI ihlal = 0.
   ───────────────────────────────────────────────────────────────────────── */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const arg = (k, d) => (process.argv.find(a => a.startsWith(`--${k}=`)) || '').split('=')[1] || d;
const BASE = arg('base', 'https://borsapusula.com');
const WIDTHS = arg('w', '390,1280').split(',').map(n => parseInt(n, 10));
const ONLY = arg('only', '');

const SURFACES = [
  { page: '/hisse/ASELS', tabs: ['ozet', 'grafik', 'ai', 'haberler'] },
  { page: '/hisse/GARAN', tabs: ['ozet', 'grafik', 'ai', 'haberler'] },
  { page: '/tarama', tabs: ['teknik', 'temel'] },
];

const SRC = f => fs.readFileSync(path.join(__dirname, f), 'utf8');
const TAP = SRC('tap-target-check.js');
const FOCUS = SRC('focus-visible-check.js');
const TEXTC = SRC('live-contrast-check.js');
const NONTEXT = SRC('nontext-contrast-check.js');
const { PROBE: CLIP } = require('./text-clip-check.js');

/* Her eksen icin: (ham sonuc) -> [{key, line}] — key delta icin, line rapor icin */
const AXES = [
  {
    id: 'T1-TAP', run: async p => JSON.parse(await p.evaluate(TAP)),
    rows: r => (r.agg || []).map(a => ({
      key: 'TAP|' + a.sel,
      line: `${a.sel}  ${a.w}x${a.h}  n=${a.n}  "${a.txt}"`,
    })),
  },
  {
    id: 'T2-FOCUS', run: async p => JSON.parse(await p.evaluate(FOCUS)),
    rows: r => [
      ...(r.Aagg || []).map(a => ({ key: 'FOCUS-A|' + a.k, line: `[A hic halka yok] ${a.k}  n=${a.n}` })),
      ...(r.Bagg || []).map(a => ({ key: 'FOCUS-B|' + a.k, line: `[B halka boguluyor] ${a.k}  gorunen kenar=${a.d.vis}  n=${a.n}` })),
    ],
  },
  {
    id: 'T3-TEXT', run: async p => p.evaluate(TEXTC),
    rows: r => (r.HARD || []).map(v => ({
      key: 'TEXT|' + v.sig + '|' + v.ratio,
      line: `${v.sig}  ${v.ratio}:1 (gereken ${v.need})  fg=${v.fg} bg=${v.bg}  "${v.text}"`,
    })),
  },
  {
    id: 'T4-NONTEXT', run: async p => p.evaluate(NONTEXT),
    rows: r => [
      ...(r.HARD || []).map(v => ({ key: 'NONTEXT|' + v.sig, line: `${v.sig}  skor=${v.score}  n=${v.count}` })),
      ...(r.ICONS || []).map(v => ({ key: 'ICON|' + v.sig, line: `[ikon] ${v.sig}  en iyi=${v.best}  ${v.box}` })),
    ],
  },
  {
    id: 'T5-CLIP', run: async p => p.evaluate(CLIP),
    rows: r => (r || []).filter(x => x.kind === 'HARD' || x.kind === 'PLACE').map(v => ({
      key: 'CLIP|' + v.kind + '|' + v.node + '|' + v.text.slice(0, 24),
      line: `[${v.kind}] ${v.node} < ${v.clipper}  R+${v.ovR} B+${v.ovB}  "${v.text}"`,
    })),
  },
];

async function measure(ctx, url, tabId, isBase) {
  const page = await ctx.newPage();
  /* ⛔ K-T'nin 2. sahte-pozitif sinifi: SEKME SECIMI SAYFALAR ARASI SIZAR.
     hisse.html secimi `localStorage['bp_hisse_tab']`e yazar ve bir sonraki
     ziyarette geri yukler (tasarim geregi). Ayni tarayici baglaminda once
     ASELS/Haberler olculup sonra GARAN acilinca GARAN da HABERLER sekmesiyle
     aciliyordu — yani "Ozet TABANI" aslinda Haberler'di ve o sekmenin gercek
     ihlalleri "zaten tabanda vardi" diye SESSIZCE dusuyordu (canli: GARAN
     tabani 3 anahtarla acildi, haberler sekmesi YENI 0 raporladi). Her olcum
     kendi temiz durumundan baslar; ayrica asagida aktif sekme DOGRULANIR. */
  await page.addInitScript(() => { try { localStorage.removeItem('bp_hisse_tab'); } catch (e) {} });
  const resp = await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
  if (resp && resp.status() >= 400) { await page.close(); throw new Error(`HTTP ${resp.status()} — OLU ROTA`); }
  await page.waitForTimeout(1200);
  /* Aktif sekme GERCEKTEN beklenen mi? (kapsam yalanina karsi sert kapi) */
  const active = await page.evaluate(() => {
    const a = document.querySelector('.bp-seg-item.active,[role="tab"][aria-selected="true"]');
    return a ? a.id : null;
  });
  let panelPx = 0;
  if (isBase && active !== `tab-${tabId}`) {
    await page.close();
    throw new Error(`TABAN KIRLI: aktif sekme ${active}, beklenen tab-${tabId}`);
  }
  if (!isBase) {
    const sel = `#tab-${tabId}`;
    if (!(await page.$(sel))) { await page.close(); throw new Error(`sekme dugmesi yok: ${sel}`); }
    await page.click(sel);
    await page.waitForTimeout(1800);           // grafik/haber tembel yuklemesi
    /* ⛔ SEKMEYI ACAN TIKLAMA, ODAK EKSENINI ZEHIRLER (K-T'nin 1. sahte-pozitif
       sinifi — K-R2'nin ":focus-visible SON GIRIS MODUNA baglidir" dersinin
       kardesi). Tarayici giris modunu "isaretleyici"ye cevirir; bundan sonraki
       PROGRAMATIK `el.focus()` `:focus-visible` eslesmez ve K-O probu sayfadaki
       HER kontrolu "hic halka yok" (A sinifi) sanir. Canli pozitif kontrol
       (/hisse/ASELS @390): tiklamasiz A=0 · AKTIF sekmeye tiklandi A=58 ·
       tiklandi+gercek Tab A=0. Tek bir GERCEK klavye olayi modu geri alir. */
    await page.keyboard.press('Tab');
    await page.waitForTimeout(250);
    panelPx = await page.evaluate(t => {
      /* `[role=tab]` DISLANIR: /tarama'da sekme DUGMESININ kendisi `data-tab`
         tasir; onu sayinca panel 5487px² gorunuyordu (gercek panel 24.000px²) —
         "panel acildi" kapisi dugmenin kendi alanindan gecerdi. */
      const sel = `[data-tab-content~="${t}"],[data-tab~="${t}"]`;
      let a = 0;
      document.querySelectorAll(sel).forEach(el => {
        if (el.getAttribute('role') === 'tab' || el.classList.contains('bp-seg-item')) return;
        const r = el.getBoundingClientRect(); a += Math.round(r.width * r.height);
      });
      // /tarama farkli bir kalipta: aria-controls ile isaret edilen panel
      if (!a) {
        const btn = document.getElementById('tab-' + t);
        const ids = (btn && btn.getAttribute('aria-controls') || '').split(/\s+/).filter(Boolean);
        ids.forEach(id => { const el = document.getElementById(id); if (el) { const r = el.getBoundingClientRect(); a += Math.round(r.width * r.height); } });
      }
      return a;
    }, tabId);
    if (!panelPx) { await page.close(); throw new Error(`panel HALA 0px — sekme acilmadi (kapsam yalani!)`); }
  }
  const out = {};
  for (const ax of AXES) {
    try { out[ax.id] = ax.rows(await ax.run(page)); }
    catch (e) { out[ax.id] = [{ key: 'ERR|' + ax.id, line: 'PROB HATASI: ' + e.message.split('\n')[0] }]; }
  }
  await page.close();
  return { out, panelPx };
}

(async () => {
  const browser = await chromium.launch();
  let totalNew = 0;
  const surfaces = ONLY ? SURFACES.filter(s => ONLY.split(',').includes(s.page)) : SURFACES;
  for (const W of WIDTHS) {
    const ctx = await browser.newContext({
      viewport: { width: W, height: W < 768 ? 844 : 900 },
      deviceScaleFactor: 2, isMobile: W < 768, hasTouch: W < 768,
    });
    for (const s of surfaces) {
      const url = BASE + s.page;
      console.log(`\n████ ${s.page} @${W}px`);
      let baseKeys = new Set();
      for (let i = 0; i < s.tabs.length; i++) {
        const t = s.tabs[i], isBase = i === 0;
        let r;
        try { r = await measure(ctx, url, t, isBase); }
        catch (e) { console.log(`  ✖ ${t}: ${e.message}`); continue; }
        const rows = [].concat(...AXES.map(a => r.out[a.id].map(x => ({ ...x, ax: a.id }))));
        if (isBase) { rows.forEach(x => baseKeys.add(x.key)); console.log(`  ── ${t} (TABAN): ${rows.length} bulgu anahtari kaydedildi`); continue; }
        const fresh = rows.filter(x => !baseKeys.has(x.key));
        totalNew += fresh.length;
        console.log(`  ── ${t}: panel ${r.panelPx}px² · toplam ${rows.length} · YENI ${fresh.length}`);
        const byAx = {};
        fresh.forEach(x => { (byAx[x.ax] = byAx[x.ax] || []).push(x.line); });
        for (const [ax, lines] of Object.entries(byAx)) {
          console.log(`     ${ax} (${lines.length})`);
          lines.slice(0, 12).forEach(l => console.log(`       • ${l}`));
          if (lines.length > 12) console.log(`       … +${lines.length - 12}`);
        }
      }
    }
    await ctx.close();
  }
  console.log(`\nTOPLAM YENI (gizli sekmelerde) = ${totalNew}`);
  await browser.close();
  process.exit(totalNew > 0 ? 1 : 0);
})();
