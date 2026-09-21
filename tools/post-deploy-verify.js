#!/usr/bin/env node
/* tools/post-deploy-verify.js — DEPLOY SONRASI CANLI DOGRULAMA
 *
 * ⛔ "Tek curl yetmez" (feedback_deploy_dogrulama_tek_curl_yetmez_12_09):
 *    200 donmesi kodun yuklendigini KANITLAMAZ. Bu betik her fix icin
 *    fix'in DAVRANISINI olcer, varligini degil.
 *
 * Her madde, ilgili turun hafizadaki "deploy sonrasi dogrulama" notundan gelir.
 * Kullanim: node tools/post-deploy-verify.js [--base=https://borsapusula.com]
 */
const { chromium } = require('playwright');
const BASE = (process.argv.find(a => a.startsWith('--base=')) || '').split('=')[1] || 'https://borsapusula.com';

const results = [];
const ok   = (n, d) => { results.push({ n, pass: true,  d }); console.log('  ✓ ' + n + (d ? '  — ' + d : '')); };
const bad  = (n, d) => { results.push({ n, pass: false, d }); console.log('  ✗ ' + n + '  — ' + d); };

const step = async (ad, fn) => {
  try { await fn(); }
  catch (e) { bad(ad, 'OLCULEMEDI (adim cokti): ' + String(e.message).split('\n')[0]); }
};

(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ locale: 'tr-TR', viewport: { width: 1280, height: 900 } });
  const p = await ctx.newPage();
  const pageErrors = [];
  p.on('pageerror', e => pageErrors.push(e.message));

  /* ── 0) SURUM: canli gercekten yeni kodu mu kosuyor? ─────────────────── */
  console.log('\n[0] Surum');
  const health = await (await ctx.request.get(BASE + '/api/health')).json().catch(() => null);
  if (health) ok('/api/health cevap veriyor', 'stocks age_s=' + (health.stocks && health.stocks.age_s));
  else bad('/api/health', 'JSON alinamadi');

  /* ── 1) K-BA: TR ondalik girdi ───────────────────────────────────────── */
  console.log('\n[1] K-BA — TR ondalik girdi (/tarama)');
  await p.goto(BASE + '/tarama', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await p.waitForTimeout(2500);
  const typ = await p.$eval('#fMinP', el => el.type).catch(() => null);
  typ === 'text' ? ok('#fMinP type=text') : bad('#fMinP type', 'beklenen text, gelen ' + typ);
  await p.click('#fMinP'); await p.type('#fMinP', '12,50'); await p.waitForTimeout(2500);
  const v = await p.$eval('#fMinP', el => el.value);
  v === '12,50' ? ok('virgul korunuyor', '"' + v + '"') : bad('virgul korunuyor', 'okunan "' + v + '"');
  const url = p.url();
  /min_price=12\.5(\D|$)/.test(url) ? ok('URL min_price=12.5', url.split('?')[1] || '')
                                    : bad('URL min_price', 'beklenen 12.5, URL: ' + url);
  const chip = await p.evaluate(() => (document.body.innerText.match(/Min [\d.,]+ ₺/) || [''])[0]);
  /Min 12,5 ₺/.test(chip) ? ok('cip TR bicimi', chip) : bad('cip TR bicimi', 'gelen "' + chip + '"');
  /* ⛔ Bu adim deploy ONCESI (type=number) fill ile COKER. Coken bir olcum
     "temiz" degil "olculemedi"dir ve KALAN maddeleri de sessizce yutar —
     bu yuzden her adim kendi icinde yakalanir ve rapora islenir. */
  try {
    await p.fill('#fMinP', 'abc'); await p.waitForTimeout(2200);
    const inv = await p.$eval('#fMinP', el => el.getAttribute('aria-invalid'));
    inv === 'true' ? ok('gecersiz girdi aria-invalid') : bad('gecersiz girdi aria-invalid', 'deger: ' + inv);
  } catch (e) {
    bad('gecersiz girdi aria-invalid', 'OLCULEMEDI: ' + e.message.split('\n')[0]);
  }

  /* ── 2) K-BB: ARIA bos durum (/karsilastir) ──────────────────────────── */
  console.log('\n[2] K-BB — ARIA bos durum (/karsilastir)');
  await step('K-BB bolumu', async () => {
    await p.goto(BASE + '/karsilastir', { waitUntil: 'domcontentloaded', timeout: 60000 });
    await p.waitForTimeout(2800);
    (await p.$('#acStatus')) ? ok('#acStatus canli bolgesi var') : bad('#acStatus', 'bulunamadi');
    await p.click('#t1'); await p.type('#t1', 'ZZZZQQ', { delay: 50 }); await p.waitForTimeout(1500);
    const s1 = await p.evaluate(() => ({
      exp: document.getElementById('t1').getAttribute('aria-expanded'),
      opt: document.querySelectorAll('#ac1 [role="option"]').length,
      say: (document.getElementById('acStatus') || {}).textContent || '',
    }));
    s1.exp === 'false' && s1.opt === 0 ? ok('eslesme yok -> expanded=false, option=0')
                                       : bad('eslesme yok durumu', JSON.stringify(s1));
    /bulunamad|yuklenemedi|yüklenemedi/i.test(s1.say) ? ok('bos mesaj duyuruluyor', '"' + s1.say + '"')
                                                      : bad('bos mesaj duyurusu', '"' + s1.say + '"');
    await p.fill('#t1', ''); await p.type('#t1', 'AK', { delay: 50 }); await p.waitForTimeout(1500);
    const s2 = await p.evaluate(() => ({
      exp: document.getElementById('t1').getAttribute('aria-expanded'),
      opt: document.querySelectorAll('#ac1 [role="option"]').length,
      say: (document.getElementById('acStatus') || {}).textContent || '',
    }));
    s2.exp === 'true' && s2.opt > 0 ? ok('eslesme VAR -> expanded=true, option=' + s2.opt)
                                    : bad('REGRESYON: dolu liste bildirilmiyor', JSON.stringify(s2));
    s2.say === '' ? ok('bayat duyuru temizlendi') : bad('bayat duyuru', '"' + s2.say + '"');
  });

  /* ── 3) K-BC: portfoyde sessiz kod kabulu ────────────────────────────── */
  console.log('\n[3] K-BC — portfoyde sessiz kod kabulu (/portfolio)');
  await step('K-BC bolumu', async () => {
    await p.goto(BASE + '/portfolio', { waitUntil: 'domcontentloaded', timeout: 60000 });
    await p.waitForTimeout(3000);
    const dl = await p.$$eval('#bistTickerList option', o => o.length).catch(() => 0);
    dl > 0 ? ok('evren yuklendi', dl + ' kod') : bad('evren', 'datalist bos — dogrulama yapilamaz');
    await p.fill('#addTicker', 'ZZZQQ'); await p.fill('#addLot', '10'); await p.fill('#addPrice', '12,50');
    const beforeRows = await p.$$eval('#pfTable tbody tr', r => r.length).catch(() => 0);
    await p.click('.btn-add'); await p.waitForTimeout(3000);
    const r3 = await p.evaluate(() => ({
      msg: (document.getElementById('addErr') || {}).textContent || '',
      rows: document.querySelectorAll('#pfTable tbody tr').length,
    }));
    /bulunamad/i.test(r3.msg) ? ok('gecersiz kod uyariliyor', '"' + r3.msg.slice(0, 60) + '…"')
                              : bad('gecersiz kod uyarisi', '"' + r3.msg + '"');
    r3.rows > beforeRows ? ok('ENGELLEMIYOR — satir yine eklendi') : bad('engelledi', 'satir eklenmedi');
    await p.fill('#addTicker', 'GARAN'); await p.fill('#addLot', '5'); await p.fill('#addPrice', '100,00');
    await p.click('.btn-add'); await p.waitForTimeout(3000);
    const r4 = await p.evaluate(() => (document.getElementById('addErr') || {}).textContent || '');
    r4.trim() === '' ? ok('GECERLI kodda yanlis uyari yok') : bad('gecerli kodda uyari', '"' + r4 + '"');
  });

  /* ── 3b) K-BD: "bugun" TR takvim gunu mu, UTC mi? ───────────────────── */
  console.log('\n[3b] K-BD — TR takvim gunu kanonu (/portfolio)');
  await step('K-BD bolumu', async () => {
    const r = await p.evaluate(() => {
      if (typeof bpTodayTrIso !== 'function') return { yok: true };
      const RealDate = Date;
      // TR 01:30 (ertesi gun) = UTC 22:30 (onceki gun) — kanonun ayristigi an
      const fake = new RealDate('2026-09-20T22:30:00Z');
      const Patched = class extends RealDate {
        constructor(...a) { return a.length ? new RealDate(...a) : new RealDate(fake); }
      };
      Patched.UTC = RealDate.UTC; Patched.now = () => fake.getTime();
      // eslint-disable-next-line no-global-assign
      Date = Patched;
      const tr = bpTodayTrIso();
      const utc = new Date().toISOString().slice(0, 10);
      Date = RealDate;
      return { tr, utc, bugun: bpTodayTrIso() };
    });
    if (r.yok) return bad('bpTodayTrIso', 'sayfada TANIMLI DEGIL — eski kod servis ediliyor');
    /^\d{4}-\d{2}-\d{2}$/.test(r.bugun) ? ok('bpTodayTrIso bicimi', r.bugun)
                                        : bad('bpTodayTrIso bicimi', String(r.bugun));
    (r.tr === '2026-09-21' && r.utc === '2026-09-20')
      ? ok('TR gunu UTC gununden ayrisiyor', 'TR=' + r.tr + ' UTC=' + r.utc + ' (kanon TR yaniti veriyor)')
      : bad('TR/UTC ayrimi', 'TR=' + r.tr + ' UTC=' + r.utc + ' (beklenen 2026-09-21 / 2026-09-20)');
    // Disa aktarim dosya adi gercekten kanondan mi turuyor?
    const dl = await p.evaluate(() => {
      const a = [...document.querySelectorAll('button,a')].find(e => /CSV/i.test(e.textContent || ''));
      return a ? true : false;
    });
    dl ? ok('CSV disa aktarim dugmesi var') : bad('CSV dugmesi', 'bulunamadi — ad dogrulanamadi');
  });

  /* ── 3c) K-BE/K-BF: hisse sayfasi (global cakisma + sekme<->panel) ───── */
  console.log('\n[3c] K-BE/K-BF — /hisse/GARAN');
  await step('K-BE/K-BF bolumu', async () => {
    await p.goto(BASE + '/hisse/GARAN', { waitUntil: 'domcontentloaded', timeout: 60000 });
    await p.waitForTimeout(3000);
    // K-BE: safeHref TEK kaynaktan gelmeli (bp-vocab.js) ve calisir olmali
    const se = await p.evaluate(() => {
      if (typeof safeHref !== 'function') return { yok: true };
      return {
        gecerli: safeHref('https://kap.org.tr/x'),
        cop: safeHref('javascript:alert(1)'),
        bos: safeHref(''),
      };
    });
    if (se.yok) return bad('safeHref', 'sayfada TANIMLI DEGIL');
    se.gecerli === 'https://kap.org.tr/x' ? ok('safeHref http(s) gecirir', se.gecerli)
                                          : bad('safeHref http(s)', String(se.gecerli));
    (se.cop === '#' && se.bos === '#') ? ok('safeHref http(s) disini engeller', "javascript: -> '#'")
                                       : bad('safeHref engelleme', 'javascript:->' + se.cop + ' bos->' + se.bos);
    // K-BF: her sekmenin bildirdigi TUM paneller var ve tabpanel mi?
    const tp = await p.evaluate(() => {
      const out = [];
      document.querySelectorAll('[role="tab"][aria-controls]').forEach(t => {
        (t.getAttribute('aria-controls') || '').split(/\s+/).filter(Boolean).forEach(id => {
          const el = document.getElementById(id);
          out.push({ tab: t.id, id, var: !!el, rol: el ? el.getAttribute('role') : null,
                     etiket: el ? el.getAttribute('aria-labelledby') : null });
        });
      });
      return out;
    });
    const kirik = tp.filter(x => !x.var || x.rol !== 'tabpanel' || x.etiket !== x.tab);
    kirik.length === 0
      ? ok('sekme<->panel bagi', tp.length + ' bildirim, hepsi tabpanel ve dogru sekmeye bagli')
      : bad('sekme<->panel bagi', JSON.stringify(kirik.slice(0, 3)));
    const aiPanel = tp.filter(x => x.tab === 'tab-ai').length;
    const ozPanel = tp.filter(x => x.tab === 'tab-ozet').length;
    (aiPanel >= 2 && ozPanel >= 2)
      ? ok('K-BF ikinci paneller bildirildi', 'tab-ai=' + aiPanel + ' tab-ozet=' + ozPanel)
      : bad('K-BF ikinci paneller', 'tab-ai=' + aiPanel + ' tab-ozet=' + ozPanel + ' (beklenen >=2/>=2)');
  });

  /* ── 4) K-AX: periyodik yenileme odagi koruyor mu? ───────────────────── */
  /* ⛔ OLCUM SIRASI KATMANIN DURUMUNU BOZAR (K-S dersi): bu adim eskiden
     "onceki adim /portfolio'da birakti" varsayimiyla calisiyordu. 3c adimi
     eklendiginde sayfa /hisse/GARAN'da kaldi ve adim "DUZENLE DUGMESI YOK"
     dedi -- yani K-AX regresyonu gibi GORUNEN sey aslinda OLCUM arizasiydi.
     Her adim artik kendi sayfasina KENDISI gider. */
  console.log('\n[4] K-AX — periyodik yenileme odagi (/portfolio, 65 sn)');
  await p.goto(BASE + '/portfolio', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await p.waitForTimeout(3000);
  const focusKept = await p.evaluate(async () => {
    const btn = document.querySelector('#pfTable tbody .btn-edit');
    if (!btn) return 'DUZENLE DUGMESI YOK';
    btn.focus();
    const id = btn.getAttribute('onclick');
    await new Promise(r => setTimeout(r, 65000));
    const now = document.activeElement;
    return (now && now.getAttribute && now.getAttribute('onclick') === id) ? 'KORUNDU'
         : 'KAYBOLDU -> ' + (now ? now.tagName : 'null');
  });
  focusKept === 'KORUNDU' ? ok('60 sn yenileme sonrasi odak korundu')
                          : bad('odak korunmadi', focusKept);

  /* ── 5) Cache-bust: sayfadaki ?v= diskteki hash ile ayni mi? ─────────── */
  console.log('\n[5] Cache-bust (?v= <-> servis edilen dosyanin md5i)');
  const assets = await p.evaluate(() =>
    [...document.querySelectorAll('script[src*="?v="],link[href*="?v="]')]
      .map(e => e.src || e.href).filter(u => /\/static\//.test(u)).slice(0, 12));
  const crypto = require('crypto');
  let cbBad = 0;
  for (const u of assets) {
    const res = await ctx.request.get(u);
    if (!res.ok()) { bad('asset ' + u.split('/').pop(), 'HTTP ' + res.status()); cbBad++; continue; }
    const body = Buffer.from(await res.body());
    const md5 = crypto.createHash('md5').update(body).digest('hex').slice(0, 8);
    const want = (u.match(/\?v=([0-9a-f]+)/) || [])[1];
    if (md5 !== want) { bad('cache-bust ' + u.split('/').pop().split('?')[0], '?v=' + want + ' ama md5=' + md5); cbBad++; }
  }
  if (!cbBad) ok('cache-bust tutarli', assets.length + ' asset');

  /* ── 6) Konsol hatasi ────────────────────────────────────────────────── */
  console.log('\n[6] Konsol');
  pageErrors.length === 0 ? ok('sayfa hatasi yok') : bad('sayfa hatasi', JSON.stringify(pageErrors.slice(0, 3)));

  const fails = results.filter(r => !r.pass);
  console.log('\n' + '='.repeat(60));
  console.log(fails.length ? ('❌ DEPLOY DOGRULAMA: ' + fails.length + '/' + results.length + ' BASARISIZ')
                           : ('✅ DEPLOY DOGRULAMA: ' + results.length + '/' + results.length + ' GECTI'));
  await b.close();
  process.exit(fails.length ? 1 : 0);
})().catch(e => { console.error('DOGRULAMA COKTU (sonuc "temiz" DEGIL):', e.message); process.exit(2); });
