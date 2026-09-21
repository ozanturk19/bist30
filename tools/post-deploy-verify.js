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

  /* ── 4) K-AX: periyodik yenileme odagi koruyor mu? ───────────────────── */
  console.log('\n[4] K-AX — periyodik yenileme odagi (/portfolio, 65 sn)');
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
