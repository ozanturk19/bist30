#!/usr/bin/env node
// Mobile horizontal-overflow harness — CPO-1201 §5 (M1-d, stop-the-line deliverable)
//
// Neden var: DEV üç turdur (DEV-1544/1545/1546) bu harness'ı yazmadan tek-seferlik
// manuel ölçümle "0 taşma" raporladı, iki kez yanlış çıktı:
//   1. CPO-1198: details/summary KAPALI durumda ölçüldü, lejant AÇIKKEN +92px taşma kaçtı.
//   2. CPO-1200/1201 §3: ham scrollWidth-clientWidth kullanıldı, klasik (overlay olmayan)
//      scrollbar genişliği (~11px) her ölçümde sahte "taşma" olarak raporlandı.
// Bu script ikisini de yapısal olarak imkansız kılmak için var — nokta ölçüm değil.
//
// Kullanım:
//   node tools/mobile-overflow-check.mjs [--base=https://borsapusula.com] [--out=path.json]
//
// Exit code (CPO-1204 §1, üçlü): 0 = temiz, 1 = yalnız allowlisted WARN (pinlenmiş
// dirty-ground, tam açıklanmış — bkz. DIRTY_GROUND_ALLOWLIST), 2 = FAIL (taşma,
// yüklenemeyen sayfa veya açıklanmamış/allowlist-dışı kirli ölçüm zemini — bu
// durumda "0 taşma" asla yeşil raporlanmaz). CI/cron hangi eşikte kırmızıya
// döneceğini kendi seçer.

import { chromium } from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.join(__dirname, '..');

const BASE = (process.argv.find(a => a.startsWith('--base=')) || '').split('=')[1]
  || process.env.MOC_BASE || 'https://borsapusula.com';
const OUT = (process.argv.find(a => a.startsWith('--out=')) || '').split('=')[1]
  || path.join(REPO_ROOT, 'tests', 'mobile-overflow', 'latest.json');

// K-AD (21.09, CPO): 320 EKSIKTI. WCAG 1.4.10 Reflow'un tanimli genisligi
// 320 CSS px'tir; liste 360'tan basliyordu ve aradaki bant hic olculmedi.
// Ilk 320 kosumunda ana sayfanin abonelik formu (.da-sub-form min-width:280px)
// +3px tasma verdi -- 360/375/390/414'te GORUNMUYOR, yani bu aciga yerlesmisti.
const WIDTHS = [320, 360, 375, 390, 414];
const HEIGHT = 800;

// Sayfa envanteri: app.py'deki GET/HTML route'lardan türetildi (API/webhook/static
// hariç). Parametreli route'lar için sabit, gerçek örnek değer kullanıldı (THYAO/AKBNK
// visual-test.js ile aynı — mevcut baseline'la tutarlı).
const PAGES = [
  { name: 'home', path: '/' },
  { name: 'tarama', path: '/tarama' },
  { name: 'gundem', path: '/gundem' },
  { name: 'karsilastir', path: '/karsilastir' },
  { name: 'ozet', path: '/ozet' },
  { name: 'ozet-gecmis', path: '/ozet/2026-05-10' },
  { name: 'metodoloji', path: '/metodoloji' },
  { name: 'hakkinda', path: '/hakkinda' },
  { name: 'gizlilik', path: '/gizlilik' },
  { name: 'iletisim', path: '/iletisim' },
  { name: 'yasal', path: '/yasal' },
  { name: 'portfolio', path: '/portfolio' },
  // 'dow' (/dow) BILEREK YOK: Dow verisi motorda yok, T0.7 kapsaminda route
  // zaten kaldirilmis (canli kanit: httpStatus=404, T9.1 kosumunda yakalandi).
  // 'djia' hic PAGES listesinde degildi, ek islem yok.
  { name: 'hisseler', path: '/hisseler' },
  { name: 'sektor-harita', path: '/sektor-harita' },
  { name: 'bilanco-takvimi', path: '/bilanco-takvimi' },
  // 'profil' (/profil) BILEREK YOK: Kucuk temizlik (Master Program,
  // DEV2-139/140) ile tokensiz erisim artik BILEREK 404 donuyor (icerik
  // ayni markali sayfa, yalniz HTTP status 200->404, zaten noindex,nofollow
  // tasiyordu). Bu harness tokensiz sabit /profil'i tarardi ve httpStatus>=400
  // guard'i (T9.1) bunu FAIL sayardi -- 'dow'/'abd-tarama' ile ayni desen.
  { name: 'blog', path: '/blog' },
  { name: 'blog-article', path: '/blog/supertrend-indikatoru-nedir' },
  // 'abd-tarama' (/abd/tarama) BILEREK YOK: f9e4ac8 (T4.1) ile kaldirildi,
  // 0 ic link / yetim sayfa, trafik tamami bot/agent idi. Bu harness hic
  // calistirilmadigi icin kaldirmadan sonra guncellenmemisti (T9.1 kanit:
  // ilk canli kosuda httpStatus=404 dondu, ama script bunu FAIL SAYMIYORDU
  // -- asagidaki httpStatus kontrolu bu korlugu da kapatiyor).
  { name: 'hisse-thyao', path: '/hisse/THYAO' },
  { name: 'hisse-thyao-grafik', path: '/hisse/THYAO?tab=grafik' },
  { name: 'hisse-thyao-ai', path: '/hisse/THYAO?tab=ai' },
  { name: 'hisse-thyao-haberler', path: '/hisse/THYAO?tab=haberler' },
  { name: 'hisse-akbnk', path: '/hisse/AKBNK' },
  // K-AD ikinci dalga: 7 kayit daha cikarildi. Yeni yonlendirme muhafizi,
  // ilk turda cikarilan 16'nin YANINDA 6 sunucu-tarafi 301 daha ortaya
  // cikardi (curl ile dogrulandi): /sinyaller /sinyal-performans /backtest
  // -> /tarama · /sektorler /sektor -> /sektor-harita · /virtual-portfolio
  // -> /portfolio. Yani harness /tarama'yi 4, /sektor-harita'yi 3,
  // /portfolio'yu 2 kez olcuyordu. Ayrica 'hisse-thyao-ozet' cikarildi:
  // ciplak /hisse/THYAO zaten ?tab=ozet'e normalize oluyor, AYNI DOM.
  // Listelenen 45 kaydin 23'u ayni sayfanin tekrariydi; gercek kapsam
  // 22 benzersiz sayfa. 'Kapsam sayisi = envanter uzunlugu' varsayimi
  // olculene kadar bir iddiadir, olcu degil.
  // K-AD (21.09): 16 kayit BILEREK CIKARILDI -- /nasdaq /sp500 /kripto
  // /emtialar /btc /eth /sol /bnb /altin /gumus /petrol /dogalgaz /abd
  // /abd/sp500 /abd/nasdaq /abd/AAPL. Hepsi 19.08 BIST Odakli Sadelesme
  // (CPO-DEV2-036) ile kaldirildi ve bugun 301 ile '/' adresine gidiyor.
  // Harness bunlari 'ok' sayiyordu cunku Playwright yonlendirmeyi izler:
  // gerceklesen sey, ana sayfanin her genislikte 17 kez olculmesiydi
  // (gunluk kosumun ~%35'i bos is). '/dow' ve '/abd/tarama' ile AYNI emsal.
];

// CPO-1201 §5(b) kapsamı: details/summary bu turda GENERİK olarak destekleniyor
// (tüm <details> elemanları .open=true yapılıyor — badge-legend +92px sınıfının
// aynısını yakalar). dropdown/modal/sheet açık-durumu ve "uzun metin" durumu bu
// SELECTOR_OVERRIDES ile sayfa-bazlı eklenir; boşsa o state o sayfa için atlanır
// ve JSON'da `skippedStates` alanında AÇIKÇA loglanır — sessizce "kapsandı"
// denmez (CPO'nun "sessiz tavan" dersi, §4).
const SELECTOR_OVERRIDES = {
  // path adı -> { modalTrigger: 'selector', dropdownTrigger: 'selector' }
  // Şu an boş: hiçbir sayfada modal/dropdown tetikleyicisi kayıtlı değil.
};

async function measureState(page) {
  const m = await page.evaluate(() => {
    const de = document.documentElement;
    return {
      innerWidth: window.innerWidth,
      clientWidth: de.clientWidth,
      scrollWidth: de.scrollWidth,
    };
  });
  const scrollbarSlack = m.innerWidth - m.clientWidth;
  // Ölçüm zemini integrity assert'i (CPO-1201 §5a): gerçek mobilde (overlay
  // scrollbar) bu sıfır olmalı. Sıfır değilse bu koşunun "0 taşma" sonucu
  // GÜVENİLMEZ — measurementClean=false ile işaretlenir, harness bunu FAIL eder.
  const measurementClean = scrollbarSlack === 0;
  const rawOverflow = m.scrollWidth - m.clientWidth;
  // K-AD: slack ARTIK CIKARILMIYOR. Orijinal cikarma (CPO-1201 §3) klasik
  // scrollbar'i elemek icindi, ama checkPage artik `isMobile:true` +
  // `hasTouch:true` ile kosuyor -> Chromium OVERLAY scrollbar kullanir ve
  // gercek slack HER ZAMAN 0'dir. Bu baglamda slack>0'in tek sebebi, icerik
  // tastigi icin layout viewport'unun GENISLEMESIDIR. Yani cikarma islemi
  // tam da yakalamak icin var oldugu tasmayi siliyordu: ana sayfa @320'de
  // iw=323/cw=320/sw=323 olcuyordu ve overflowPx=0 basiyordu (gercek: +3px).
  const overflowPx = Math.max(0, rawOverflow);
  return { ...m, scrollbarSlack, measurementClean, rawOverflow, overflowPx };
}

async function checkPage(browser, pageDef, width) {
  const context = await browser.newContext({
    viewport: { width, height: HEIGHT },
    isMobile: true,
    hasTouch: true,
    deviceScaleFactor: 2,
  });
  const page = await context.newPage();
  const jsErrors = [];
  page.on('pageerror', e => jsErrors.push(String(e && e.message || e)));

  const result = {
    page: pageDef.name, path: pageDef.path, width,
    httpStatus: null, jsErrors, states: {}, skippedStates: [],
  };

  try {
    // 'networkidle' KULLANMA: canlı fiyat sayfaları (/ws/prices websocket,
    // /api/stream polling) hiçbir zaman idle olmuyor — ilk sürümde bu yüzden
    // 204 kontrolün 96'sı (%47) sessizce ERROR'a düştü ve harness yine de
    // "PASS: temiz" bastı (ölçülmeyen sayfalar bulgu sayılmadığı için).
    // 'load' + sabit settle bekleme kullanıyoruz — bu sınıf sayfalarda güvenilir.
    const resp = await page.goto(BASE + pageDef.path, { waitUntil: 'load', timeout: 20000 });
    result.httpStatus = resp ? resp.status() : null;
    // T9.1: httpStatus ONCEDEN kaydediliyordu ama HICBIR YERDE kontrol
    // edilmiyordu -- 404/500 donen bir sayfa, tasma olmadigi surece 'ok'
    // basiyordu (canli kanit: /abd/tarama 404 donuyordu, harness 'ok'
    // yaziyordu). 4xx/5xx artik yuklenemedi sayilir, olcum atlanir.
    if (result.httpStatus && result.httpStatus >= 400) {
      throw new Error('HTTP ' + result.httpStatus);
    }
    // K-AD: 3xx KORLUGU. Playwright yonlendirmeyi SESSIZCE izler ve
    // resp.status() HEDEF sayfanin 200'unu doner -- yani yukaridaki 4xx/5xx
    // muhafizi (T9.1) olu rotalari yakalamaz. Canli kanit: PAGES'teki 45
    // kaydin 16'si (/kripto /emtialar /btc /eth /sol /bnb /altin /gumus
    // /petrol /dogalgaz /abd /abd/sp500 /abd/nasdaq /abd/AAPL /nasdaq /sp500)
    // 301 ile '/' adresine gidiyordu; harness 'ok' basiyor ama gercekte ANA
    // SAYFAYI 17 kez olcuyordu. "45 sayfa kapsandi" iddiasi yanlisti.
    // Karsilastirma YOL duzeyinde: /hisse/<t> sayfasi ilk boyamada kendini
    // `?tab=ozet`e normalize eder (history.replaceState, sunucu 301'i DEGIL,
    // curl ile dogrulandi: HTTP 200). Bu AYNI sayfadir, bulgu degil. Sunucu
    // tarafi 301'ler ise yolu degistirir ve burada yakalanir.
    const norm = u => new URL(u).pathname.replace(/\/+$/, '') || '/';
    const gotPath = norm(page.url());
    const wantPath = norm(BASE + pageDef.path);
    if (gotPath !== wantPath) {
      throw new Error(`YONLENDIRME: ${pageDef.path} -> ${page.url()} (listelenen sayfa olculmedi)`);
    }
    await page.waitForTimeout(1200);

    result.states.closed = await measureState(page);

    const detailsCount = await page.evaluate(() => document.querySelectorAll('details').length);
    if (detailsCount > 0) {
      await page.evaluate(() => {
        document.querySelectorAll('details').forEach(d => { d.open = true; });
      });
      await page.waitForTimeout(80);
      result.states['details-open'] = await measureState(page);
    } else {
      result.skippedStates.push('details-open (sayfada <details> yok)');
    }

    const override = SELECTOR_OVERRIDES[pageDef.name];
    if (override && override.modalTrigger) {
      try {
        await page.click(override.modalTrigger, { timeout: 3000 });
        await page.waitForTimeout(150);
        result.states['modal-open'] = await measureState(page);
      } catch (e) {
        result.skippedStates.push(`modal-open (tetikleyici bulunamadı/tıklanamadı: ${e.message})`);
      }
    } else {
      result.skippedStates.push('modal-open (SELECTOR_OVERRIDES kaydı yok)');
    }
    if (override && override.dropdownTrigger) {
      try {
        await page.click(override.dropdownTrigger, { timeout: 3000 });
        await page.waitForTimeout(150);
        result.states['dropdown-open'] = await measureState(page);
      } catch (e) {
        result.skippedStates.push(`dropdown-open (tetikleyici bulunamadı/tıklanamadı: ${e.message})`);
      }
    } else {
      result.skippedStates.push('dropdown-open (SELECTOR_OVERRIDES kaydı yok)');
    }
    result.skippedStates.push('long-text (sentetik veri enjeksiyonu bu turda yok — gerçek içerikle ölçülüyor)');
  } catch (e) {
    result.error = String(e && e.message || e);
  } finally {
    await context.close();
  }
  return result;
}

// CPO-1204 §1 — pinlenmis allowlist (DEV-1547/1548), DEV2-T-MOBOVF-1'de BOSALTILDI.
// Eski 6 kayit (hisse-thyao/-ozet@360/390, hisse-akbnk@360/390) kok nedeni
// hisse.html:1095'teki body{overflow-x:clip} guard'inin html'e uygulanmamasi
// idi (CSS overflow-propagation: html overflow-x:visible kaldigi surece
// body'nin clip'i viewport'a tasinmiyor, .ind-help::after tooltipi gizliyken
// bile scrollWidth'e siziyordu). html{overflow-x:clip} eklenince (commit 2e33799)
// 6 kaydin 6'si da PASS'e dondu (Warn: 12->0, dogrulandi). Mekanizma canli
// tutulur (gelecekte gercek bir aciklanmis kalinti cikarsa buraya eklenir),
// ama su an bos - kirli-zemin kumesinin kucculmesi aracin kendi felsefesiyle
// tutarli (bkz. yukaridaki yorum: buyumesi regresyon sinyali, kucculmesi duzelme).
const DIRTY_GROUND_ALLOWLIST = new Set([]);

// K-AD: ESKI TANIM BIR TUZAKTI -- `slack === rawOverflow && overflowPx === 0`
// kosulu, mobil emulasyonda GERCEK TASMANIN imzasinin TA KENDISIDIR (viewport
// icerik genisligine kadar genisler: iw-cw == sw-cw). Yani allowlist'e alinan
// her sayfada gercek bir tasma kalici olarak "aciklanmis kirli zemin" diye
// gorunmez olurdu. Overlay scrollbar altinda mesru bir kirli zemin YOKTUR;
// slack>0 daima bulgudur, mazeret degil.
function isExplainedDirty(_s) {
  return false;
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const results = [];
  let integrityFailures = 0;
  let warnFindings = 0;
  let overflowFindings = 0;
  let loadFailures = 0;

  for (const pageDef of PAGES) {
    for (const width of WIDTHS) {
      const r = await checkPage(browser, pageDef, width);
      results.push(r);
      if (r.error) loadFailures++;
      const allowlisted = DIRTY_GROUND_ALLOWLIST.has(`${pageDef.name}@${width}`);
      let hasFailDirty = false;
      let hasWarnDirty = false;
      for (const [stateName, s] of Object.entries(r.states)) {
        if (!s.measurementClean) {
          if (allowlisted && isExplainedDirty(s)) {
            warnFindings++;
            hasWarnDirty = true;
          } else {
            integrityFailures++;
            hasFailDirty = true;
          }
        }
        if (s.overflowPx > 0) overflowFindings++;
      }
      const findings = Object.entries(r.states)
        .filter(([, s]) => s.overflowPx > 0)
        .map(([name, s]) => `${name}:+${s.overflowPx}px`);
      const tag = r.error ? `ERROR ${r.error}` : (findings.length ? `OVERFLOW ${findings.join(',')}` : 'ok');
      const dirtyTag = hasFailDirty ? ' [DIRTY-MEASUREMENT]' : (hasWarnDirty ? ' [WARN-DIRTY-ALLOWLISTED]' : '');
      console.log(`[${width}px] ${pageDef.path.padEnd(38)} ${tag}${dirtyTag}`);
    }
  }

  await browser.close();

  const summary = {
    generatedAt: new Date().toISOString(),
    base: BASE,
    widths: WIDTHS,
    totalPages: PAGES.length,
    totalChecks: results.length,
    integrityFailures,
    warnFindings,
    overflowFindings,
    loadFailures,
  };

  const out = { summary, results };
  await fs.mkdir(path.dirname(OUT), { recursive: true });
  await fs.writeFile(OUT, JSON.stringify(out, null, 2));
  console.log(`\nJSON: ${OUT}`);
  console.log(`Sayfa: ${PAGES.length} x Genişlik: ${WIDTHS.length} = ${results.length} kontrol`);
  // CPO-1204 §1 kural #4: WARN sayısı sıfır olsa bile her koşumda basılır —
  // "görünürlük ertelenmez".
  console.log(`Integrity failures: ${integrityFailures} | Warn (allowlisted dirty-ground): ${warnFindings} | Overflow findings: ${overflowFindings} | Load failures: ${loadFailures}`);

  // Yüklenemeyen sayfalar "ölçülmedi" demektir, "0 taşma" değil — bunları
  // integrity failures'tan ayrı ama aynı ciddiyette FAIL ediyoruz. İlk sürümde
  // (networkidle) bu kontrol yoktu ve 96/204 kontrol sessizce atlanıp yine de
  // PASS basılmıştı.
  if (loadFailures > 0) {
    console.error(`\nFAIL: ${loadFailures} kontrol sayfa yüklenemediği için hiç ölçülmedi (bkz. ERROR satırları). Bunlar "0 taşma"ya dahil DEĞİL — kapsam eksik demek.`);
    process.exit(2);
  }
  if (integrityFailures > 0) {
    console.error('\nFAIL: ölçüm zemini kirli ve ya açıklanmamış ya da allowlist dışı (bkz. DIRTY-MEASUREMENT satırları). "0 taşma" iddiası GEÇERSİZ.');
    process.exit(2);
  }
  if (overflowFindings > 0) {
    console.error('\nFAIL: yatay taşma bulundu.');
    process.exit(2);
  }
  if (warnFindings > 0) {
    console.warn(`\nWARN: ${warnFindings} ölçüm allowlisted dirty-ground (tam açıklanmış, bkz. WARN-DIRTY-ALLOWLISTED satırları). Taşma yok.`);
    process.exit(1);
  }
  console.log('\nPASS: temiz.');
  process.exit(0);
}

main().catch(e => { console.error(e); process.exit(2); });
