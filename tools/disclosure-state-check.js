#!/usr/bin/env node
// tools/disclosure-state-check.js — K-AO: AÇILIR KONTROLÜN DURUM BİLDİRİMİ
// WCAG 2.1 · SC 4.1.2 "Name, Role, Value" (A)
//
// SORU — bu sitede daha önce hiç sorulmadı:
//   Bir düğmeye basınca sayfada gizli bir bölüm AÇILIYORSA, ekran okuyucu
//   kullanıcısı bunu yalnızca `aria-expanded` üzerinden bilir. Öznitelik
//   yoksa düğme sıradan bir buton gibi duyurulur: kullanıcı ne açılabilir
//   bir şey olduğunu bilir, ne de ŞU AN açık mı kapalı mı olduğunu. Gözle
//   gören kullanıcı "Detayları gizle ▴" yazısından anlar — o metin ekran
//   okuyucuda da okunur ama ROL/DURUM makine tarafından okunabilir değildir
//   (ör. NVDA'nın "genişletilmiş/daraltılmış" duyurusu hiç çıkmaz).
//
// ⛔ BU BOYUTU BULMA HİKÂYESİ (kayıt): K-AN sayı-biçimi dedektörü /hisse'de
//   D1'i "temiz" ilan etti. Ölçüldü: temiz değildi — "EMA12: 130.4" KAPALI
//   bir gövdedeydi ve dedektörün "aç" adımı yalnızca <details> ve
//   [aria-expanded=false] tanıyordu. O düğmede aria-expanded YOKTU.
//   Yani dedektörün kör noktasının KÖK NEDENİ bir erişilebilirlik kusuruydu.
//
// ⚠️ BU DOSYA İKİNCİL (CANLI TEYİT) ARAÇTIR. Bu boyutun BİRİNCİL ölçümü
//   `tools/disclosure-state-scan.py`dir (şablon kaynağından görünürlük
//   çeviren işleyicileri türetir). Sebep ÖLÇÜLDÜ: canlı "her şeye tıkla"
//   yaklaşımında sayfanın kendi JS'i bölümleri innerHTML ile yeniden basıyor
//   ve arama katmanı açılınca geri kalan her şey görünmez oluyor — 32 adayın
//   28'i KAYBOLUYOR ve araç bunu "acilir=2/32, temiz" diye raporluyordu.
//   O yüzden KAYIP artık SESSİZ DEĞİL: varsa çıkış kodu 2 (hata) olur.
//
// YÖNTEM (davranış ölçülür):
//   1. Tıklanabilir her öğe için ÖNCE sayfanın görünür-metin parmak izi alınır
//   2. tıklanır, 500ms beklenir, parmak izi yeniden alınır
//   3. görünür metin ANLAMLI ölçüde arttıysa (≥ MIN_DELTA karakter) bu öğe
//      bir AÇILIR KONTROLdür → aria-expanded taşımalıdır
//   4. yeniden tıklanıp durum geri alınır (sonraki ölçümü kirletmemek için)
//
// BULGU SINIFLARI (taban SIFIR):
//   YOK        — bölge açtı, aria-expanded hiç yok
//   YANLIS     — aria-expanded var ama açıldıktan sonra hâlâ "false"
//                (ya da kapandıktan sonra hâlâ "true") — SABİT yazılmış
//   ADSIZ      — açılır kontrolün erişilebilir adı yok
//
// ⛔ <details>/<summary> BULGU DEĞİLDİR: tarayıcı `open` özniteliğinden
//   genişletilmiş durumu KENDİSİ duyurur; aria-expanded eklemek gereksizdir.
//   Bu yüzden summary öğeleri kapsam DIŞI (ama sayılır, saydamlık için).
//
// POZİTİF KONTROL (--kill-fix): var olan her aria-expanded SİLİNİR.
//   YOK sınıfı FIRLAMALI. [[feedback_positif_kontrol_checkout_commit_once]]
//
// Kullanım: node tools/disclosure-state-check.js [--base=...] [--w=375,1280]
//           [--only=/a,/b] [--min=40] [--kill-fix] [--json=dosya]
const { chromium } = require('playwright');

const BASE = (process.argv.find(a => a.startsWith('--base=')) || '').split('=')[1] || 'https://borsapusula.com';
const WIDTHS = ((process.argv.find(a => a.startsWith('--w=')) || '').split('=')[1] || '1280')
  .split(',').map(s => parseInt(s, 10)).filter(Boolean);
const ONLY = (process.argv.find(a => a.startsWith('--only=')) || '').split('=')[1] || '';
const JSON_OUT = (process.argv.find(a => a.startsWith('--json=')) || '').split('=')[1] || '';
const MIN_DELTA = parseInt(((process.argv.find(a => a.startsWith('--min=')) || '').split('=')[1] || '40'), 10);
const KILL_FIX = process.argv.includes('--kill-fix');
const LIST = process.argv.includes('--list');

const PAGES = [
  '/', '/ozet', '/tarama', '/gundem', '/hisseler', '/sektor-harita',
  '/hisse/ASELS', '/hisse/GARAN', '/karsilastir', '/portfolio',
  '/bilanco-takvimi', '/temettu-takvimi', '/blog', '/blog/rsi-gostergesi-nedir',
  '/metodoloji', '/hakkinda', '/iletisim', '/yasal', '/gizlilik',
];

const PREP = (opts) => {
  if (opts.kill) {
    document.querySelectorAll('[aria-expanded]').forEach(e => e.removeAttribute('aria-expanded'));
  }
  const vis = (el) => {
    for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
      if (n.hasAttribute('hidden') || n.hasAttribute('inert')) return false;
      const cs = getComputedStyle(n);
      if (cs.display === 'none' || cs.visibility === 'hidden') return false;
    }
    return true;
  };
  // ⛔ SABIT `data-kao` ETIKETI CALISMAZ — OLCULDU: sayfanin kendi JS'i
  //   bolumleri `innerHTML = ...` ile yeniden bastigi icin etiketler
  //   siliniyordu; 32 adayin 28'i ikinci turda KAYIP oluyordu ve dedektor
  //   bunu sessizce "acilir degil" diye rapor ediyordu (kapsam yalani).
  //   Cozum: her adimda listeyi YENIDEN uret, k'inci ogeyi belge sirasindan
  //   al. window.__kaoList() bunu yapar.
  window.__kaoList = () => {
    const out = [];
    document.querySelectorAll('button,[role="button"],summary,a[href="#"],[onclick]').forEach((el) => {
      if (!vis(el)) return;
      const r = el.getBoundingClientRect();
      if (r.width < 4 || r.height < 4) return;
      out.push(el);
    });
    window.__kaoCur = out;
    return out.length;
  };
  const n = window.__kaoList();
  window.__kaoFingerprint = () => (document.body.innerText || '').replace(/\s+/g, ' ').length;
  // Modal/dialog tetikleyicisi aria-expanded ALMAZ (kalip: haspopup + odak
  // yonetimi). Tiklamadan sonra gorunur bir dialog belirdiyse bu oge
  // "acilir bolum" degildir — bulgu sayilmaz, ayri sayilir.
  window.__kaoDialogOpen = () => {
    let n = 0;
    document.querySelectorAll('[role="dialog"],[aria-modal="true"],dialog[open]').forEach(d => {
      const cs = getComputedStyle(d);
      if (cs.display !== 'none' && cs.visibility !== 'hidden' && !d.hasAttribute('hidden')) n++;
    });
    return n;
  };
  window.__kaoInfo = (k) => {
    window.__kaoList();
    const el = window.__kaoCur[k];
    if (!el) return null;
    const name = (el.getAttribute('aria-label') || el.textContent || '').replace(/\s+/g, ' ').trim();
    const cls = (typeof el.className === 'string' ? el.className : (el.getAttribute('class') || '')).trim().split(/\s+/).filter(Boolean).slice(0, 2).join('.');
    return {
      tag: el.tagName.toLowerCase(),
      id: el.id || '',
      cls,
      name: name.slice(0, 44),
      aexp: el.hasAttribute('aria-expanded') ? el.getAttribute('aria-expanded') : null,
      inSummary: el.tagName.toLowerCase() === 'summary',
      onclick: (el.getAttribute('onclick') || '').slice(0, 50),
    };
  };
  return n;
};

(async () => {
  const pages = ONLY ? ONLY.split(',') : PAGES;
  const browser = await chromium.launch();
  const report = [];
  let totalF = 0, errors = 0, totalCtl = 0, totalDisc = 0, summaries = 0, dialogs = 0, lostTotal = 0;
  const byKind = {};

  for (const w of WIDTHS) {
    const ctx = await browser.newContext({ viewport: { width: w, height: 900 } });
    const page = await ctx.newPage();
    for (const p of pages) {
      let res;
      try { res = await page.goto(BASE + p, { waitUntil: 'networkidle', timeout: 45000 }); }
      catch (e) { console.log(`ERROR  ${w}px ${p} — ${e.message.slice(0, 70)}`); errors++; continue; }
      if (res && res.status() >= 400) { console.log(`ERROR  ${w}px ${p} — HTTP ${res.status()}`); errors++; continue; }
      await page.waitForTimeout(1800);

      // ⛔ KAPALI <details> ICINDEKI TOGGLE ADAY OLAMAZ: /hisse'nin "Detayli
      //   goster" dugmesi kapali bir <details>'in icindedir. Once hepsi acilir
      //   — aksi halde bu dedektor tam da kendisini doguran kusuru goremez.
      //   AYRI bir evaluate + bekleme sart: `d.open=true` ile AYNI TICK'te
      //   okunan getComputedStyle BAYAT doner.
      //   [[reference_getcomputedstyle_ayni_tick_classlist_bayat]]
      try {
        await page.evaluate(() => { document.querySelectorAll('details:not([open])').forEach(d => { d.open = true; }); });
        await page.waitForTimeout(500);
      } catch (e) { /* details yok */ }

      let nCands;
      try { nCands = await page.evaluate(PREP, { kill: KILL_FIX }); }
      catch (e) { console.log(`ERROR  ${w}px ${p} — prep: ${e.message.slice(0, 70)}`); errors++; continue; }
      const cands = Array.from({ length: nCands }, (_, i) => i);

      const findings = [];
      let disc = 0, nullInfo = 0, heals = 0;

      // ⛔ KENDINI IYILESTIRME — OLCULDU: arama dugmesine basinca acilan
      //   tam-ekran katman sayfanin geri kalanini gorunmez yapiyor; sonraki
      //   adaylarin TAMAMI (32'nin 28'i) "yok" olup sessizce atlaniyordu.
      //   Tikladiktan sonra aday sayisi baslangictakinden AZ ise once Esc,
      //   olmazsa sayfa yeniden yuklenir. Aksi halde "acilir=2/32" diye
      //   temiz gorunen bir KAPSAM YALANI uretilir.
      const heal = async () => {
        let n2 = await page.evaluate(() => window.__kaoList ? window.__kaoList() : -1);
        if (n2 >= nCands) return;
        try { await page.keyboard.press('Escape'); await page.waitForTimeout(350); } catch (e) {}
        n2 = await page.evaluate(() => window.__kaoList ? window.__kaoList() : -1);
        if (n2 >= nCands) { heals++; return; }
        try {
          await page.goto(BASE + p, { waitUntil: 'networkidle', timeout: 45000 });
          await page.waitForTimeout(1800);
          await page.evaluate(() => { document.querySelectorAll('details:not([open])').forEach(d => { d.open = true; }); });
          await page.waitForTimeout(400);
          await page.evaluate(PREP, { kill: KILL_FIX });
          heals++;
        } catch (e) { /* yeniden yukleme basarisiz */ }
      };
      for (const id of cands) {
        let info, before, after, aexpAfter;
        try {
          info = await page.evaluate((i) => window.__kaoInfo(i), id);
          if (!info) { nullInfo++; continue; }
          before = await page.evaluate(() => window.__kaoFingerprint());
          var dlgBefore = await page.evaluate(() => window.__kaoDialogOpen());
          await page.evaluate((k) => { const e = window.__kaoCur[k]; if (e) e.click(); }, id);
          await page.waitForTimeout(450);
          after = await page.evaluate(() => window.__kaoFingerprint());
          var dlgAfter = await page.evaluate(() => window.__kaoDialogOpen());
          aexpAfter = await page.evaluate((k) => {
            const e = window.__kaoCur[k];
            return e && e.hasAttribute('aria-expanded') ? e.getAttribute('aria-expanded') : null;
          }, id);
        } catch (e) { nullInfo++; continue; }

        const delta = after - before;
        if (LIST) console.log(`        [liste] ${String(delta).padStart(6)}  <${info.tag}${info.id ? '#' + info.id : ''}${info.cls ? '.' + info.cls : ''}> "${info.name.slice(0,30)}"  aexp=${info.aexp}`);
        if (delta < MIN_DELTA) {
          // bolge acmadi; durumu geri almak icin yine de tekrar tikla (idempotent degilse zararsiz)
          if (delta !== 0) { try { await page.evaluate((k) => { const e = window.__kaoCur[k]; if (e) e.click(); }, id); await page.waitForTimeout(200); } catch (e) {} }
          await heal();
          continue;
        }
        if (dlgAfter > dlgBefore) {
          dialogs++;
          try { await page.keyboard.press('Escape'); await page.waitForTimeout(250); } catch (e) {}
          continue;
        }
        disc++;
        if (info.inSummary) { summaries++; }
        else if (aexpAfter === null) findings.push({ k: 'YOK', ...info, delta });
        else if (aexpAfter !== 'true') findings.push({ k: 'YANLIS', ...info, delta, aexpAfter });
        if (!info.inSummary && !info.name) findings.push({ k: 'ADSIZ', ...info, delta });
        // geri kapat
        try { await page.evaluate((k) => { const e = window.__kaoCur[k]; if (e) e.click(); }, id); await page.waitForTimeout(250); } catch (e) {}
        await heal();
      }

      totalCtl += cands.length; totalDisc += disc; totalF += findings.length; lostTotal += nullInfo;
      for (const f of findings) byKind[f.k] = (byKind[f.k] || 0) + 1;
      report.push({ w, p, findings, cands: cands.length, disc });
      console.log(`${findings.length ? 'FAIL' : 'OK  '}  ${w}px ${p}  bulgu=${findings.length}  (acilir=${disc}/${cands.length} kontrol${nullInfo ? `, KAYIP=${nullInfo}` : ''}${heals ? `, onarim=${heals}` : ''})`);
      for (const f of findings.slice(0, 10)) {
        console.log(`        · ${f.k}  <${f.tag}${f.id ? '#' + f.id : ''}${f.cls ? '.' + f.cls : ''}>  "${f.name}"  +${f.delta} krkt${f.onclick ? '  onclick=' + f.onclick : ''}`);
      }
    }
    await ctx.close();
  }
  await browser.close();

  console.log(`\nTOPLAM  bulgu=${totalF}  ${JSON.stringify(byKind)}`);
  console.log(`        acilir kontrol=${totalDisc} (${summaries} <summary>, kapsam disi) · modal tetikleyici=${dialogs} (kapsam disi) / taranan tiklanabilir=${totalCtl}  hata=${errors}`);
  if (JSON_OUT) { require('fs').writeFileSync(JSON_OUT, JSON.stringify({ report, byKind, totalF, totalDisc, errors }, null, 2)); console.log(`JSON → ${JSON_OUT}`); }
  // ⛔ KAPSAM KAYBI SESSİZ GEÇMEZ: ölçülemeyen aday "temiz" demek değildir.
  if (lostTotal > 0) {
    console.log(`\n⛔ KAPSAM KAYBI: ${lostTotal} aday ölçülemedi (DOM yeniden basıldı / katman açık kaldı).`);
    console.log(`   Bu çalıştırmanın "temiz" sayfaları KANIT DEĞİLDİR. Birincil ölçüm: tools/disclosure-state-scan.py`);
    process.exit(2);
  }
  process.exit(errors > 0 ? 2 : (totalF > 0 ? 1 : 0));
})();
