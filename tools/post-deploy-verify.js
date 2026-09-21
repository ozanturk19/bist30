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

  /* ── 3d) K-BH: "kopyala" vaadi ile panoya yazilan sey ayni mi? ──────── */
  console.log('\n[3d] K-BH — kopyala vaadi = kopyalanan sey (/portfolio)');
  await step('K-BH bolumu', async () => {
    /* Her adim KENDI sayfasina kendi gider (f381efb dersi). Sunucuya HIC
       yazmadan olculur: sahte token localStorage'a konur, pano cagrisi
       yakalanir -- /api/portfolio/new cagrilmaz. */
    const FAKE = '00000000-1111-2222-3333-444444444444';
    await p.goto(BASE + '/portfolio', { waitUntil: 'domcontentloaded', timeout: 60000 });
    await p.evaluate(t => { try { localStorage.setItem('bp_cloud_token', t); } catch (e) {} }, FAKE);
    await p.reload({ waitUntil: 'domcontentloaded', timeout: 60000 });
    await p.waitForTimeout(2000);
    await p.evaluate(() => {
      window.__copied = null;
      navigator.clipboard.writeText = v => { window.__copied = v; return Promise.resolve(); };
      openCloudSync();
    });
    await p.waitForTimeout(600);

    const promise = await p.evaluate(() => {
      const b = document.querySelector('#cloudActiveSection button[onclick*="opyCloud"]');
      if (!b) return null;
      return { aria: b.getAttribute('aria-label') || '', tip: b.getAttribute('data-tip') || '' };
    });
    if (!promise) return bad('kopyala dugmesi', 'bulunamadi — eski kod servis ediliyor olabilir');

    (promise.aria && promise.aria === promise.tip)
      ? ok('tek kanon ad', '"' + promise.aria + '"')
      : bad('ad/ipucu ayrisiyor', 'aria="' + promise.aria + '" tip="' + promise.tip + '"');

    const saysLink = /bağlant|baglant|link|url/i.test(promise.aria + ' ' + promise.tip);

    await p.evaluate(() => {
      const b = document.querySelector('#cloudActiveSection button[onclick*="opyCloud"]');
      b.click();
    });
    await p.waitForTimeout(800);
    const r = await p.evaluate(() => ({
      copied: window.__copied,
      msg: (document.getElementById('cloudMsg') || {}).textContent || '',
    }));

    const isUrl = /^https?:\/\//i.test(String(r.copied || ''));
    if (saysLink) {
      isUrl ? ok('vaat "baglanti" — panoya URL yazildi', String(r.copied).slice(0, 50))
            : bad('VAAT TUTMUYOR', '"' + promise.tip + '" diyor ama panoya "' + String(r.copied).slice(0, 40) + '" yazildi');
    } else {
      (r.copied === FAKE)
        ? ok('vaat "token" — panoya token yazildi', String(r.copied).slice(0, 20) + '…')
        : bad('token kopyalanmadi', 'panoya "' + String(r.copied).slice(0, 40) + '" yazildi');
    }

    /* Basari mesaji NE kopyalandigini soylemeli — cloudMsg aria-live'dir. */
    /token/i.test(r.msg) ? ok('mesaj kopyalanani adlandiriyor', '"' + r.msg.trim() + '"')
                         : bad('mesaj ne kopyalandigini soylemiyor', '"' + r.msg.trim() + '"');

    /* Pencere metni artik var olmayan bir "baglantiyla paylasim" vaat etmemeli. */
    const lie = await p.evaluate(() => {
      const d = document.getElementById('cloudModalDialog');
      return d ? /bağlantıyla paylaş/i.test(d.textContent || '') : null;
    });
    lie === false ? ok('pencere metninde var olmayan baglanti vaadi yok')
                  : bad('baglanti vaadi hala duruyor', String(lie));

    await p.evaluate(() => { try { localStorage.removeItem('bp_cloud_token'); } catch (e) {} });
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

  /* ── 4c) K-BI: birlestirme sayimi GERCEKTEN eklenen mi? ──────────────── */
  /* Dizge araMAZ -- canli sayfada kanonu CALISTIRIR. Eski (yalanci) kod
     yolunda bulut mesaji gelen listenin uzunlugunu yaziyordu; burada tamamen
     YINELENEN bir liste verilir ve added===0 beklenir. `save()` cagrilmadigi
     icin tarayicinin localStorage'ina dokunulmaz. */
  console.log('\n[4c] K-BI — birlestirme sayimi (/portfolio)');
  await p.goto(BASE + '/portfolio', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await p.waitForTimeout(1500);
  const merge = await p.evaluate(() => {
    if (typeof _pfMergePositions !== 'function') return { err: '_pfMergePositions YOK (kanon servis edilmiyor)' };
    const before = Array.isArray(portfolio) ? portfolio.length : -1;
    if (before < 0) return { err: 'portfolio dizi degil' };
    const yeni  = { ticker: 'ZZTEST', lot: 1, price: 1.23, date: '2026-01-02' };
    const r1 = _pfMergePositions([yeni]);                    // yeni kayit
    const r2 = _pfMergePositions([{ ...yeni }]);             // AYNI kayit tekrar
    const r3 = _pfMergePositions([{ ...yeni, price: '1.23' }]); // string fiyat = yine ayni
    const after = portfolio.length;
    return { before, after, r1, r2, r3 };
  });
  if (merge.err) {
    bad('K-BI birlestirme kanonu', merge.err);
  } else {
    (merge.r1.added === 1 && merge.r1.duplicate === 0)
      ? ok('K-BI yeni kayit eklendi', 'added=1')
      : bad('K-BI yeni kayit', JSON.stringify(merge.r1));
    (merge.r2.added === 0 && merge.r2.duplicate === 1)
      ? ok('K-BI yinelenen kayit EKLENMEDI ve eklenmis SAYILMADI', 'added=0 duplicate=1')
      : bad('K-BI yinelenen kayit', JSON.stringify(merge.r2) + ' (eski yalanci yol added=1 derdi)');
    (merge.r3.added === 0 && merge.r3.duplicate === 1)
      ? ok('K-BI dedupe sayisallastiriyor', 'string fiyat da yinelenen sayildi')
      : bad('K-BI dedupe olcutu', JSON.stringify(merge.r3));
    (merge.after === merge.before + 1)
      ? ok('K-BI dizi uzunlugu tutarli', merge.before + ' -> ' + merge.after)
      : bad('K-BI dizi uzunlugu', merge.before + ' -> ' + merge.after + ' (beklenen +1)');
  }

  /* ── 4d) K-BJ — pozisyon sayisal dogrulamasi tek kanon ─────────────────
     Fix oncesi: hisse detay quick-add fiyat okunamayinca MALIYETI 0 yaziyordu
     (cost=0 -> pozisyonun tam degeri "kar" gorunur) ve CSV disa aktarimi ayni
     K/Z'yi tablo render'inin aksine korumasizca hesapliyordu ("Infinity"/"NaN").
     Adim dizge ARAMAZ: canli sayfada gercek fonksiyonlari CALISTIRIR.
     f381efb dersi: kendi sayfasina KENDI gider, onceki adimin birakigina guvenmez. */
  console.log('\n[4d] K-BJ — pozisyon sayisal dogrulamasi (tek kanon)');
  await p.goto(BASE + '/portfolio', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await p.waitForTimeout(1200);
  const kbj = await p.evaluate(() => {
    if (typeof bpIsValidLot !== 'function' || typeof bpIsValidPrice !== 'function')
      return { err: 'bpIsValidLot/bpIsValidPrice YOK (kanon servis edilmiyor)' };
    const r = {};
    r.kanon = [bpIsValidPrice(0), bpIsValidPrice(-5), bpIsValidPrice(NaN), bpIsValidPrice(undefined),
               bpIsValidLot(0), bpIsValidLot(1.5), bpIsValidLot(2e9)].every(x => x === false)
           && bpIsValidPrice(12.34) === true && bpIsValidLot(3) === true;
    // GERCEK exportCSV()'yi bozuk pozisyonlarla calistir, ciktisini yakala.
    // save() cagrilmaz -> tarayicinin localStorage'ina DOKUNULMAZ.
    const yedek = JSON.parse(JSON.stringify(portfolio));
    const OB = window.Blob, OC = URL.createObjectURL, OR = URL.revokeObjectURL;
    const OK = HTMLAnchorElement.prototype.click;
    let csv = null;
    try {
      window.Blob = function (parts, opts) { csv = String(parts[0]); return new OB(parts, opts); };
      URL.createObjectURL = () => 'blob:stub'; URL.revokeObjectURL = () => {};
      HTMLAnchorElement.prototype.click = function () {};
      portfolio.length = 0;
      portfolio.push({ ticker: 'THYAO', lot: 1, price: 0,   date: '2026-09-21', id: 1 });
      portfolio.push({ ticker: 'GARAN', lot: 1, price: 'x', date: '2026-09-21', id: 2 });
      exportCSV();
      r.csvTemiz = !!csv && !/Infinity|NaN/.test(csv);
      render();
      r.domTemiz = !/Infinity|NaN/.test(document.querySelector('main').innerText);
    } finally {
      window.Blob = OB; URL.createObjectURL = OC; URL.revokeObjectURL = OR;
      HTMLAnchorElement.prototype.click = OK;
      portfolio.length = 0; yedek.forEach(x => portfolio.push(x)); render();
    }
    // POZITIF KONTROL: ayni veri fix ONCESI ifadeden gecerse Infinity/NaN uretmeli,
    // yoksa bu adim kor demektir.
    const eski = (o, cur) => (((cur - o.price) / o.price) * 100).toFixed(2);
    r.pozitifKontrol = eski({ price: 0 }, 293.5) === 'Infinity' && eski({ price: 'x' }, 293.5) === 'NaN';
    return r;
  });
  if (kbj.err) {
    bad('K-BJ kanon', kbj.err);
  } else {
    kbj.kanon ? ok('K-BJ kanon dogru', '0/negatif/NaN/ondalik-lot reddedildi, gecerli kabul')
              : bad('K-BJ kanon', 'bpIsValidLot/bpIsValidPrice beklenen sonucu vermedi');
    kbj.pozitifKontrol ? ok('K-BJ pozitif kontrol', 'fix oncesi ifade ayni veriyle Infinity/NaN uretiyor')
                       : bad('K-BJ POZITIF KONTROL DUSTU', 'senaryo defekti tetiklemiyor, adim kor olabilir');
    kbj.csvTemiz ? ok('K-BJ CSV korumali', 'price=0 ve sayisal-olmayan fiyatta K/Z bos, Infinity/NaN yok')
                 : bad('K-BJ CSV', 'disa aktarimda Infinity/NaN var');
    kbj.domTemiz ? ok('K-BJ tablo korumali', 'bozuk pozisyon DOM\'a Infinity/NaN sizdirmiyor')
                 : bad('K-BJ tablo', 'DOM\'da Infinity/NaN var');
  }

  /* ── 4e) K-BJ — hisse detay quick-add dogrulanmamis fiyat YAZMAMALI ──── */
  console.log('\n[4e] K-BJ — hisse detay hizli-ekleme (/hisse/THYAO)');
  await p.goto(BASE + '/hisse/THYAO', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await p.waitForTimeout(1800);
  const kbj2 = await p.evaluate(() => {
    if (typeof togglePortfolio !== 'function') return { err: 'togglePortfolio YOK' };
    const bas = localStorage.getItem('bp_portfolio');
    const sig = window._bpLastSignalData;
    const el  = document.getElementById('hpPrice');
    const txt = el ? el.textContent : null;
    const r = {};
    try {
      // Fiyatin okunamadigi hal (SSR fiyatsizken hpPrice '—' basar)
      window._bpLastSignalData = null;
      if (el) el.textContent = '—';
      r.donus = _hibCurrentPrice();           // fix oncesi 0 DONUYORDU
      r.nullDonuyor = r.donus === null;
      togglePortfolio();
      r.yazilmadi = localStorage.getItem('bp_portfolio') === bas;
      r.uyariVar  = /yüklenmedi/i.test((document.getElementById('hibToast') || {}).textContent || '');
    } finally {
      window._bpLastSignalData = sig; if (el) el.textContent = txt;
      if (bas === null) localStorage.removeItem('bp_portfolio');
      else localStorage.setItem('bp_portfolio', bas);
    }
    // NEGATIF KONTROL: fiyat okunurken kanon mesru eklemeyi ENGELLEMEMELI
    r.okunurFiyat = _hibCurrentPrice();
    r.mesruGecerli = bpIsValidPrice(r.okunurFiyat);
    return r;
  });
  if (kbj2.err) {
    bad('K-BJ quick-add', kbj2.err);
  } else {
    kbj2.nullDonuyor ? ok('K-BJ fiyat okunamazsa null', '(fix oncesi 0 donup MALIYET olarak yaziliyordu)')
                     : bad('K-BJ _hibCurrentPrice', 'null degil: ' + JSON.stringify(kbj2.donus));
    kbj2.yazilmadi ? ok('K-BJ dogrulanmamis fiyat portfoye YAZILMADI', 'localStorage degismedi')
                   : bad('K-BJ quick-add', 'gecersiz fiyatli pozisyon yazildi');
    kbj2.uyariVar ? ok('K-BJ kullaniciya sebep soylendi', 'uyari mesaji gosterildi')
                  : bad('K-BJ uyari', 'sessizce iptal edildi');
    kbj2.mesruGecerli ? ok('K-BJ negatif kontrol', 'fiyat okunurken mesru ekleme engellenmiyor (' + kbj2.okunurFiyat + ')')
                      : bad('K-BJ negatif kontrol', 'kanon mesru fiyati da reddediyor: ' + kbj2.okunurFiyat);
  }

  /* ── 4c) K-BK: bos /api/data listesi "veri yok" diye sunulmamali ─────── */
  /* ⛔ Bu adimlar KENDI context'lerini acar: route yakalama paylasilan sayfaya
     sizarsa sonraki adimlar bayat/sahte olcum verir
     ([[reference_olcum_sirasi_katmanin_durumunu_bozar]]). */
  console.log('\n[4c] K-BK — soguk baslangic: bos liste != veri yok');
  {
    const COLD = JSON.stringify({ stocks: [], loading: true, data_quality: 'OK',
                                  stocks_age_s: 5, refreshing: true, data_freshness: {} });
    const rd = async (pg, sel) => pg.evaluate(s2 => {
      const e = document.querySelector(s2); if (!e) return '(yok)';
      const cs = getComputedStyle(e);
      return (cs.display === 'none' ? '[GIZLI] ' : '') + e.textContent.replace(/\s+/g, ' ').trim().slice(0, 140);
    }, sel);

    await step('K-BK ana sayfa', async () => {
      const c = await b.newContext({ locale: 'tr-TR', viewport: { width: 1280, height: 900 } });
      const pg = await c.newPage();
      await pg.route('**/api/data', r => r.fulfill({ status: 200, contentType: 'application/json', body: COLD }));
      await pg.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 60000 });
      await pg.waitForTimeout(3500);
      const t = await rd(pg, '#daSpotlightBody');
      (/hazırlanıyor/.test(t) && !/verisi yok/.test(t))
        ? ok('K-BK ana sayfa soguk baslangicta "hazirlaniyor"', '(fix oncesi: "Su an gosterilecek hisse verisi yok.")')
        : bad('K-BK ana sayfa', t);
      await c.close();
    });

    await step('K-BK ana sayfa negatif kontrol', async () => {
      const c = await b.newContext({ locale: 'tr-TR', viewport: { width: 1280, height: 900 } });
      const pg = await c.newPage();
      await pg.route('**/api/data', r => r.fulfill({ status: 200, contentType: 'application/json',
        body: JSON.stringify({ stocks: [], loading: false }) }));
      await pg.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 60000 });
      await pg.waitForTimeout(3000);
      const t = await rd(pg, '#daSpotlightBody');
      /verisi yok/.test(t) ? ok('K-BK negatif kontrol', 'GERCEKTEN bos (loading:false) -> "veri yok" aynen kaldi')
                           : bad('K-BK negatif kontrol', t);
      await c.close();
    });

    await step('K-BK portfoy', async () => {
      const c = await b.newContext({ locale: 'tr-TR', viewport: { width: 1280, height: 900 } });
      await c.addInitScript(() => { try { localStorage.setItem('bp_portfolio', JSON.stringify([
        { id: 'kbk1', ticker: 'THYAO', lot: 10, price: 250, date: '2026-01-02' },
        { id: 'kbk2', ticker: 'GARAN', lot: 5,  price: 100, date: '2026-02-03' }])); } catch (e) {} });
      const pg = await c.newPage();
      await pg.route('**/api/data', r => r.fulfill({ status: 200, contentType: 'application/json', body: COLD }));
      await pg.goto(BASE + '/portfolio', { waitUntil: 'domcontentloaded', timeout: 60000 });
      await pg.waitForTimeout(3500);
      const miss = await rd(pg, '#pfMissingPriceWarn'), ban = await rd(pg, '#pfFetchError');
      (/^\[GIZLI\]/.test(miss) || !/kaldırın/.test(miss))
        ? ok('K-BK portfoy "pozisyonu kaldirin" tavsiyesi bastirildi', '(veri kaybina yol acan tavsiye)')
        : bad('K-BK portfoy yikici tavsiye', miss);
      (!/^\[GIZLI\]/.test(ban) && /hazırlanıyor/.test(ban))
        ? ok('K-BK portfoy banner "hazirlaniyor" diyor')
        : bad('K-BK portfoy banner', ban);
      await c.close();
    });

    await step('K-BK portfoy negatif kontrol (gercek 500)', async () => {
      const c = await b.newContext({ locale: 'tr-TR', viewport: { width: 1280, height: 900 } });
      await c.addInitScript(() => { try { localStorage.setItem('bp_portfolio', JSON.stringify([
        { id: 'kbk1', ticker: 'THYAO', lot: 10, price: 250, date: '2026-01-02' }])); } catch (e) {} });
      const pg = await c.newPage();
      await pg.route('**/api/data', r => r.fulfill({ status: 500, contentType: 'application/json', body: '{}' }));
      await pg.goto(BASE + '/portfolio', { waitUntil: 'domcontentloaded', timeout: 60000 });
      await pg.waitForTimeout(3000);
      const ban = await rd(pg, '#pfFetchError');
      /yüklenemiyor/.test(ban) ? ok('K-BK negatif kontrol', 'gercek hata hala HATA dili kullaniyor (K-U korundu)')
                               : bad('K-BK portfoy 500 dili', ban);
      await c.close();
    });

    await step('K-BK hisse detay', async () => {
      const c = await b.newContext({ locale: 'tr-TR', viewport: { width: 1280, height: 900 } });
      const pg = await c.newPage();
      await pg.route('**/api/data', r => r.fulfill({ status: 200, contentType: 'application/json', body: COLD }));
      await pg.goto(BASE + '/hisse/BIMAS', { waitUntil: 'domcontentloaded', timeout: 60000 });
      await pg.waitForTimeout(7000);
      const t = await rd(pg, '#entryAnalysisGrid');
      (/hazırlanıyor/.test(t) && !/veri yetersiz/.test(t))
        ? ok('K-BK hisse detay "veri yetersiz" kesin hukmu vermiyor')
        : bad('K-BK hisse detay', t);
      await c.close();
    });

    await step('K-BK 404 aramasi — soguk baslangic', async () => {
      const c = await b.newContext({ locale: 'tr-TR', viewport: { width: 1280, height: 900 } });
      const pg = await c.newPage();
      await pg.route('**/api/data', r => r.fulfill({ status: 200, contentType: 'application/json', body: COLD }));
      await pg.goto(BASE + '/bu-sayfa-yok-kbk', { waitUntil: 'domcontentloaded', timeout: 60000 });
      await pg.waitForTimeout(2500);
      await pg.fill('#q404', 'THYAO');
      await pg.click('#q404Form button[type=submit]');
      await pg.waitForTimeout(5000);
      const h = await rd(pg, '#q404Hint');
      (!/bulunamadı/.test(h) && /\/hisse\/THYAO/.test(pg.url()))
        ? ok('K-BK 404 aramasi THYAO icin "bulunamadi" YALANI soylemiyor')
        : bad('K-BK 404 soguk baslangic', h + ' | url=' + pg.url());
      await c.close();
    });

    await step('K-BK 404 aramasi — yaris (ikinci 404 uretmemeli)', async () => {
      const c = await b.newContext({ locale: 'tr-TR', viewport: { width: 1280, height: 900 } });
      const pg = await c.newPage();
      await pg.route('**/api/data', async r => { await new Promise(s2 => setTimeout(s2, 1500)); r.continue(); });
      await pg.goto(BASE + '/bu-sayfa-yok-kbk', { waitUntil: 'domcontentloaded', timeout: 60000 });
      await pg.waitForTimeout(120);
      await pg.fill('#q404', 'ZZQQX');
      await pg.click('#q404Form button[type=submit]');
      await pg.waitForTimeout(6000);
      const h = await rd(pg, '#q404Hint');
      (/bu-sayfa-yok-kbk/.test(pg.url()) && /bulunamadı|demek istediniz/.test(h))
        ? ok('K-BK 404 yaris penceresi kapali', '(fix oncesi: /hisse/ZZQQX -> IKINCI 404)')
        : bad('K-BK 404 yaris', h + ' | url=' + pg.url());
      await c.close();
    });

    await step('K-BK 404 aramasi — onbellek varsa /api/data cekilmez', async () => {
      const c = await b.newContext({ locale: 'tr-TR', viewport: { width: 1280, height: 900 } });
      await c.addInitScript(() => { try {
        sessionStorage.setItem('bp_search_cache_v1', JSON.stringify([{ t: 'THYAO' }, { t: 'GARAN' }]));
        sessionStorage.setItem('bp_search_t_v1', String(Date.now()));
      } catch (e) {} });
      const pg = await c.newPage();
      let hits = 0;
      pg.on('request', r => { if (/\/api\/data(\?|$)/.test(r.url())) hits++; });
      await pg.goto(BASE + '/bu-sayfa-yok-kbk', { waitUntil: 'networkidle', timeout: 60000 });
      await pg.waitForTimeout(2000);
      hits === 0 ? ok('K-BK 404 bp-search onbellegini kullaniyor', '289 KB indirme yapilmadi')
                 : bad('K-BK 404 onbellek', '/api/data istek sayisi=' + hits);
      await c.close();
    });
  }

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
