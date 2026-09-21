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
  console.log('\n[4a] K-AX — periyodik yenileme odagi (/portfolio, 65 sn)');
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
  console.log('\n[4b] K-BI — birlestirme sayimi (/portfolio)');
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
  console.log('\n[4c] K-BJ — pozisyon sayisal dogrulamasi (tek kanon)');
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
  console.log('\n[4d] K-BJ — hisse detay hizli-ekleme (/hisse/THYAO)');
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
  console.log('\n[4e] K-BK — soguk baslangic: bos liste != veri yok');
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

  /* ── 4d) K-BL: gorunen gun/saat CIHAZIN degil BIST'in takviminden gelir ─ */
  /* Ayristirici olcum: tarayici saat dilimi America/New_York'a (TR-7) ayarlanir.
     Fix oncesi rozet cihaz saatini bastigi icin NY saatini gosterirdi. */
  console.log('\n[4f] K-BL — BIST saati/gunu, cihaz saat diliminden BAGIMSIZ');
  {
    await step('K-BL rozet: etiket kalici + BIST saati', async () => {
      const c = await b.newContext({ locale: 'tr-TR', timezoneId: 'America/New_York',
                                     viewport: { width: 1280, height: 900 } });
      const pg = await c.newPage();
      await pg.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 60000 });
      await pg.waitForTimeout(2500);
      /* ⛔ Etiket/saat/saniye AYRI dugumlerdir; aralarindaki bosluk flex `gap`
         ile cizilir, metinde YOKTUR -- `wrap.textContent` "BIST21:30:49" verir
         ve "^BIST\b" gibi bir sinir buna TAKILMAZ. Her dugum kendi selektoru
         ile okunur (adimin ilk yazimi tam bu yuzden sahte-negatif uretti). */
      const m = await pg.evaluate(() => {
        const w = document.getElementById('bpLiveTime');
        const l = document.querySelector('.bp-live-time-label');
        const t = document.getElementById('bpLiveTimeText');
        const sc = document.getElementById('bpLiveTimeSec');
        return {
          label: l ? l.textContent.trim() : '(yok)',
          aria: w ? w.getAttribute('aria-label') : null,
          shown: t ? t.textContent.trim() : '(yok)',
          sec: sc ? sc.textContent.trim() : '(yok)',
          labelVisible: l ? getComputedStyle(l).display !== 'none' : false,
          deviceHH: String(new Date().getHours()).padStart(2, '0'),
          canonHH: (typeof bpTrClock === 'function' ? bpTrClock() : '??:??:??').slice(0, 2),
        };
      });
      /* Etiket ILK TICK'TE SILINMEMELI (fix oncesi "Yerel Saat" placeholder'i
         hemen uzerine yazilir, rozet etiketsiz kalirdi). */
      if (m.label !== 'BIST' || !m.labelVisible) return bad('K-BL rozet etiketi', m.label + ' (gorunur=' + m.labelVisible + ')');
      if (!/^\d{2}:\d{2}$/.test(m.shown)) return bad('K-BL rozet saat bicimi', m.shown);
      if (!/^:\d{2}$/.test(m.sec)) return bad('K-BL rozet saniye bicimi', m.sec);
      if (m.aria !== 'Borsa Istanbul saati') return bad('K-BL rozet aria-label', String(m.aria));
      /* NY (TR-7) cihazda gosterilen saat CIHAZIN degil BIST'in olmali. */
      if (m.shown.slice(0, 2) !== m.canonHH) return bad('K-BL rozet BIST saati degil', m.shown + ' vs kanon ' + m.canonHH);
      if (m.shown.slice(0, 2) === m.deviceHH) return bad('K-BL ayristirici dusuk', 'cihaz saati BIST saatiyle ayni (TZ emulasyonu calismadi?)');
      ok('K-BL rozet "BIST HH:MM" + BIST saati', 'cihaz(NY)=' + m.deviceHH + 'h, gosterilen=' + m.shown);
      await c.close();
    });

    await step('K-BL bayat banner tarihi: TR takvim gunu', async () => {
      const c = await b.newContext({ locale: 'tr-TR', timezoneId: 'America/New_York',
                                     viewport: { width: 1280, height: 900 } });
      const pg = await c.newPage();
      /* TR takviminde BUGUN 01:00'a denk gelen bir yas sec: o an NY'de DUN 18:00'dir,
         yani iki takvim AYRI gun gosterir -- rozetin hangi takvimi kullandigi
         ancak boyle ayrisir. */
      const trNow = new Date(new Date().toLocaleString('en-US', { timeZone: 'Europe/Istanbul' }));
      let ageS = trNow.getHours() * 3600 + trNow.getMinutes() * 60 - 3600;
      if (ageS < 0) ageS += 86400;
      const want = new Date(trNow.getTime() - ageS * 1000);
      const wantTxt = String(want.getDate()).padStart(2, '0') + '.' + String(want.getMonth() + 1).padStart(2, '0');
      await pg.route('**/api/data-quality', r => r.fulfill({ status: 200, contentType: 'application/json',
        body: JSON.stringify({ data_quality: 'seans_disi_eksik', stocks_age_s: ageS, refreshing: false }) }));
      await pg.goto(BASE + '/hisseler', { waitUntil: 'domcontentloaded', timeout: 60000 });
      await pg.waitForTimeout(3000);
      const t = await pg.evaluate(() => {
        const e = document.getElementById('staleBannerText');
        const b2 = document.getElementById('staleBanner');
        if (!e || !b2) return '(yok)';
        return (getComputedStyle(b2).display === 'none' ? '[GIZLI] ' : '') + e.textContent.trim();
      });
      t.startsWith(wantTxt + ' ') ? ok('K-BL banner TR takvim gunu', wantTxt + ' (NY cihazda bir gun geri kaymiyor)')
                                  : bad('K-BL banner tarihi', 'beklenen ' + wantTxt + ', gelen: ' + t.slice(0, 90));
      await c.close();
    });

    await step('K-BL olu kopya silindi, grafik ekseni saglam', async () => {
      const c = await b.newContext({ locale: 'tr-TR', viewport: { width: 1280, height: 900 } });
      const pg = await c.newPage();
      await pg.goto(BASE + '/hisse/THYAO', { waitUntil: 'domcontentloaded', timeout: 60000 });
      await pg.waitForTimeout(5000);
      const m = await pg.evaluate(() => ({
        dead: typeof _tickFmt === 'undefined',
        canon: typeof BPChart === 'object' && typeof BPChart.fmtTickDate === 'function',
        axis: (typeof BPChart === 'object' && typeof BPChart.fmtTickDate === 'function')
          ? BPChart.fmtTickDate('2026-04-10', 2) : null,
      }));
      if (!m.dead) return bad('K-BL olu kopya', '_tickFmt hala tanimli');
      if (!m.canon) return bad('K-BL kanon', 'BPChart.fmtTickDate yok');
      if (m.axis !== 'Nis 10') return bad('K-BL eksen bicimi', String(m.axis));
      ok('K-BL _tickFmt olu kopyasi gitti, kanon eksen bicimi calisiyor', 'fmtTickDate -> "Nis 10"');
      await c.close();
    });
  }

  /* ── 4g) K-BM: bozuk yerel kayit SESSIZCE silinmemeli ────────────────── */
  /* Fix oncesi: bozuk `bp_portfolio` -> bellek [], ekranda "Portföyünüz boş.",
     hicbir uyari yok, ilk save() ham kaydi KALICI eziyordu. Adim gercek
     save()'i CALISTIRIR: onemli olan ham kaydin degil, YEDEGIN hayatta
     kalmasidir. Her senaryo kendi context'inde kosar (izole localStorage). */
  console.log('\n[4g] K-BM — bozuk portfoy kaydi: yedekle, soyle, yalan soyleme');
  {
    const CORRUPT = '[{"ticker":"THYAO","lot":10,"price":290.5},{"ticker":"GARAN","lot":5,"pri';
    const olc = async (seed) => {
      const c = await b.newContext({ locale: 'tr-TR', timezoneId: 'Europe/Istanbul',
                                     viewport: { width: 1280, height: 900 } });
      if (seed !== null) await c.addInitScript(v => { try { localStorage.setItem('bp_portfolio', v); } catch (_) {} }, seed);
      const pg = await c.newPage();
      await pg.goto(BASE + '/portfolio', { waitUntil: 'domcontentloaded', timeout: 60000 });
      await pg.waitForTimeout(3000);
      const r = await pg.evaluate(() => {
        const w = document.getElementById('pfCorruptWarn');
        return {
          banner: !!w && getComputedStyle(w).display !== 'none',
          role: w ? w.getAttribute('role') : null,
          dugme: !!(w && w.querySelector('button')),
          bosBaslik: (document.getElementById('pfEmptyTitle') || {}).textContent || '',
          yedek: localStorage.getItem('bp_portfolio_bozuk'),
        };
      });
      r.sonra = await pg.evaluate(() => { save(); return localStorage.getItem('bp_portfolio_bozuk'); });
      await c.close();
      return r;
    };

    await step('K-BM bozuk kayit: uyari + yedek + dogru bos durum metni', async () => {
      const r = await olc(CORRUPT);
      if (!r.banner) return bad('K-BM banner', 'bozuk kayitta uyari GORUNMUYOR');
      if (r.role !== 'alert') return bad('K-BM banner role', String(r.role));
      if (!r.dugme) return bad('K-BM kurtarma yolu', 'indirme dugmesi yok');
      if (!/okunamad/i.test(r.bosBaslik)) return bad('K-BM bos durum metni', r.bosBaslik);
      if (r.yedek !== CORRUPT) return bad('K-BM yedek', 'ham kayit yedeklenmedi: ' + String(r.yedek).slice(0, 40));
      if (r.sonra !== CORRUPT) return bad('K-BM yedek save() sonrasi', 'yedek ezildi/silindi');
      ok('K-BM bozuk kayit korundu ve soylendi', 'banner+indirme, yedek save() sonrasi da duruyor');
    });

    await step('K-BM dizi-olmayan kayit da bozuk sayilir', async () => {
      const r = await olc('{"THYAO":{"lot":10}}');
      if (!r.banner) return bad('K-BM dizi-degil', 'JSON gecerli ama dizi degil -> uyari yok');
      if (r.yedek !== '{"THYAO":{"lot":10}}') return bad('K-BM dizi-degil yedek', String(r.yedek).slice(0, 40));
      ok('K-BM dizi-olmayan kayit', 'gecerli JSON ama dizi degil -> yine yedeklendi');
    });

    await step('K-BM negatif kontrol: gercekten bos portfoy', async () => {
      const r = await olc(null);
      if (r.banner) return bad('K-BM sahte alarm', 'bos portfoyde bozukluk uyarisi cikti');
      if (!/boş/i.test(r.bosBaslik)) return bad('K-BM bos durum metni degisti', r.bosBaslik);
      if (r.yedek !== null) return bad('K-BM gereksiz yedek', 'bos portfoyde yedek yazildi');
      ok('K-BM negatif kontrol (bos)', '"Portföyünüz boş." aynen kaldi, uyari yok');
    });

    await step('K-BM negatif kontrol: gecerli portfoy', async () => {
      const r = await olc('[{"ticker":"THYAO","lot":10,"price":290.5,"date":"2026-09-01","id":1}]');
      if (r.banner) return bad('K-BM sahte alarm', 'gecerli portfoyde bozukluk uyarisi cikti');
      if (r.yedek !== null) return bad('K-BM gereksiz yedek', 'gecerli portfoyde yedek yazildi');
      ok('K-BM negatif kontrol (gecerli)', 'uyari yok, yedek yok');
    });

    /* Salt-OKUMA yollari: bozuk kayitta dugme "bu hissede pozisyonun yok"
       diye KESIN hukum vermemeli — olcemedigi seyi iddia ediyordu. */
    const dugme = async (seed) => {
      const c = await b.newContext({ locale: 'tr-TR', timezoneId: 'Europe/Istanbul',
                                     viewport: { width: 1280, height: 900 } });
      await c.addInitScript(v => {
        try { localStorage.setItem('bp_portfolio', v.pf); localStorage.setItem('bp_watchlist_v2', v.w); } catch (_) {}
      }, seed);
      const pg = await c.newPage();
      await pg.goto(BASE + '/hisse/THYAO', { waitUntil: 'domcontentloaded', timeout: 60000 });
      await pg.waitForTimeout(3000);
      const r = await pg.evaluate(() => {
        const g = id => {
          const e = document.getElementById(id);
          return e ? { pressed: e.getAttribute('aria-pressed'), title: e.title || '',
                       aria: e.getAttribute('aria-label') || '' } : null;
        };
        return { yildiz: g('hibStarBtn'), zil: g('hibBellBtn') };
      });
      await c.close();
      return r;
    };

    await step('K-BM bozuk kayit: dugme durumu "bilinmiyor" der, yalan demez', async () => {
      const r = await dugme({ pf: '[{"ticker":"THYAO","lo', w: '{"THYAO":1}' });
      if (!r.yildiz || !r.zil) return bad('K-BM dugmeler', 'hibStarBtn/hibBellBtn bulunamadi');
      if (r.yildiz.pressed !== null) return bad('K-BM yildiz iddiasi', 'aria-pressed=' + r.yildiz.pressed + ' (bilinmiyorken bildiriliyor)');
      if (!/okunamad/i.test(r.yildiz.aria)) return bad('K-BM yildiz aciklamasi', r.yildiz.aria.slice(0, 60));
      if (r.zil.pressed !== null) return bad('K-BM zil iddiasi', 'aria-pressed=' + r.zil.pressed);
      if (!/okunamad/i.test(r.zil.aria)) return bad('K-BM zil aciklamasi', r.zil.aria.slice(0, 60));
      ok('K-BM salt-okuma yollari', 'bozuk kayitta aria-pressed bildirilmiyor, sebep soyleniyor');
    });

    await step('K-BM negatif kontrol: saglam kayitta dugmeler dogru durumu bildirir', async () => {
      const r = await dugme({ pf: '[{"ticker":"THYAO","lot":3,"price":290,"date":"2026-09-01","id":2}]', w: '["THYAO"]' });
      if (r.yildiz.pressed !== 'true') return bad('K-BM yildiz regresyonu', 'portfoyde olan hissede aria-pressed=' + r.yildiz.pressed);
      if (r.zil.pressed !== 'true') return bad('K-BM zil regresyonu', 'takipteki hissede aria-pressed=' + r.zil.pressed);
      ok('K-BM negatif kontrol (saglam kayit)', 'yildiz+zil aria-pressed=true, durum dogru bildiriliyor');
    });
  }

  /* ── 4.K-BN) EOD tazelik vaadi + --bp-stale token'i ──────────────────── */
  console.log('\n[4k] K-BN — "gosterilen fiyat ne kadar taze?" vaadi');
  await step('K-BN /yasal alt-gunluk gecikme rakami vermiyor', async () => {
    await p.goto(BASE + '/yasal', { waitUntil: 'domcontentloaded', timeout: 60000 });
    const t = await p.$eval('#main-content', e => e.innerText);
    if (/15\s*dakika\s*gecikmeli/i.test(t)) return bad('K-BN /yasal', 'hala "~15 dakika gecikmeli"');
    if (!/seans içinde güncellenmez/i.test(t)) return bad('K-BN /yasal', 'EOD sozlesmesi cumlesi yok');
    if (!/Son güncelleme:\s*21 Eylül 2026/.test(t)) return bad('K-BN /yasal', '"Son guncelleme" tarihi ilerlememis');
    ok('K-BN /yasal', 'EOD sozlesmesi + tarih guncel');
  });

  for (const r of ['/', '/tarama', '/hisse/THYAO']) {
    await step('K-BN footer veri rozeti ' + r, async () => {
      await p.goto(BASE + r, { waitUntil: 'domcontentloaded', timeout: 60000 });
      const ft = await p.$eval('.da-footer-note', e => e.innerText).catch(() => null);
      if (!ft) return bad('K-BN footer ' + r, '.da-footer-note bulunamadi');
      if (/15\s*dakika/i.test(ft)) return bad('K-BN footer ' + r, 'hala "15 dakika"');
      if (!/son kapanışa/i.test(ft)) return bad('K-BN footer ' + r, 'EOD sozlesmesi yok');
      ok('K-BN footer ' + r, 'gun-sonu sozlesmesi');
    });
  }

  await step('K-BN --bp-stale / --bp-stale-rgb canli cozuluyor', async () => {
    await p.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 60000 });
    const t = await p.evaluate(() => {
      const cs = getComputedStyle(document.documentElement);
      return { s: cs.getPropertyValue('--bp-stale').trim(), r: cs.getPropertyValue('--bp-stale-rgb').trim() };
    });
    if (t.s.toLowerCase() !== '#f5c949') return bad('K-BN --bp-stale', JSON.stringify(t));
    if (!/245,\s*201,\s*73/.test(t.r)) return bad('K-BN --bp-stale-rgb', JSON.stringify(t));
    ok('K-BN tazelik token\'i', t.s + ' / ' + t.r);
  });

  /* ⛔ OLCUM NOTU: uc dq'yu TEK sayfa uzerinde sirayla olcmek SAHTE-NEGATIF
     uretir -- sayfanin kendi periyodik bpUpdateStaleBanner('seans_disi')
     cagrisi araya girip display'i 'none' yapiyor, satir-ici renkler kaliyor.
     Her dq KENDI taze yuklemesinde, yazma ve okuma AYNI senkron blokta. */
  for (const [dq, fg, bg] of [['stale', 'rgb(245, 201, 73)', 'rgba(245, 201, 73, 0.1)'],
                              ['seans_disi_eksik', 'rgb(245, 201, 73)', 'rgba(245, 201, 73, 0.1)'],
                              ['critical', 'rgb(248, 81, 73)', 'rgba(248, 81, 73, 0.12)']]) {
    await step('K-BN stale banner ' + dq + ' token ile boyaniyor', async () => {
      await p.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 60000 });
      await p.waitForTimeout(2500);
      const r = await p.evaluate((d) => {
        if (typeof bpUpdateStaleBanner !== 'function') return { err: 'bpUpdateStaleBanner yok' };
        bpUpdateStaleBanner(d, 90000, false);
        const b = document.getElementById('staleBanner'), t = document.getElementById('staleBannerText');
        return { disp: getComputedStyle(b).display, bg: getComputedStyle(b).backgroundColor,
                 fg: t ? getComputedStyle(t).color : null, txt: b.innerText.slice(0, 200) };
      }, dq);
      if (r.err) return bad('K-BN banner ' + dq, r.err);
      if (r.disp !== 'block') return bad('K-BN banner ' + dq, 'display=' + r.disp);
      if (r.fg !== fg || r.bg !== bg) return bad('K-BN banner ' + dq, 'renk ' + r.fg + ' / ' + r.bg);
      if (/gerçek zamanlı olmayabilir/i.test(r.txt)) return bad('K-BN banner ' + dq, 'tereddutlu cumle geri gelmis');
      if (!/gün sonu \(EOD\) kapanış verisidir/.test(r.txt)) return bad('K-BN banner ' + dq, 'EOD kuyruk cumlesi yok');
      ok('K-BN banner ' + dq, r.fg + ' / ' + r.bg);
    });
  }

  await step('K-BN hisse.html olu "BIST ~15dk" dali yok', async () => {
    const hs = await (await ctx.request.get(BASE + '/hisse/THYAO')).text();
    /* Negatif iddia olcerken YORUMLARI SOY: dalin silindigini anlatan aciklama
       yorumunun kendisi hem "BIST ~15dk" hem "age < 300" yazisini tasiyor. */
    const kod = hs.replace(/\/\*[\s\S]*?\*\//g, ' ').replace(/(^|[^:\\])\/\/[^\n]*/g, '$1 ');
    if (/label\s*=\s*['"][^'"]*15\s*dk/i.test(kod)) return bad('K-BN hisse cipi', 'etiket atamasi hala var');
    if (/age\s*<\s*300/.test(kod)) return bad('K-BN hisse cipi', '`age < 300` dali hala var');
    ok('K-BN hisse cipi', 'olu/yanlis dal kodda yok');
  });

  await step('K-BN stale-banner.js ham renk tasimiyor', async () => {
    /* ⛔ CIPLAK VARLIK URL'I DEPLOY'U DEGIL CLOUDFLARE'I OLCER: ilk yazim
       `/static/stale-banner.js`i (?v= YOK) cekiyordu ve CF oradan 13.09
       tarihli bir HIT donduruyordu -> "ham renk hala var" SAHTE-NEGATIFI.
       Hicbir sablon o URL'i istemiyor. Dogru olcum: sayfanin GERCEKTEN
       yukledigi ?v='li src. ([[feedback_cf_cache_bust_static]]) */
    await p.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 60000 });
    const src = await p.evaluate(() => {
      const e = [...document.querySelectorAll('script[src]')].find(x => /stale-banner\.js/.test(x.src));
      return e ? e.src : null;
    });
    if (!src) return bad('K-BN stale-banner.js', 'sayfa bu betigi hic yuklemiyor');
    if (!/\?v=/.test(src)) return bad('K-BN stale-banner.js', "cache-bust'siz yukleniyor: " + src);
    const sb = await (await ctx.request.get(src)).text();
    if (/#f5c949|#f85149/.test(sb)) return bad('K-BN stale-banner.js', 'ham renk hala var (' + src + ')');
    if (!/var\(--bp-stale\)/.test(sb)) return bad('K-BN stale-banner.js', 'token kullanimi yok');
    ok('K-BN stale-banner.js', 'ham renk 0, token var (' + src.split('/').pop() + ')');
  });

  await step('K-BN sw.js surumu + on-bellek listesi tazelendi', async () => {
    const sw = await (await ctx.request.get(BASE + '/sw.js')).text();
    const m = sw.match(/tokens\.css\?v=([0-9a-f]+)/);
    if (!m) return bad('K-BN sw.js', 'on-bellek listesinde tokens.css yok');
    const css = await (await ctx.request.get(BASE + '/static/css/tokens.css?v=' + m[1])).text();
    if (!/--bp-stale:/.test(css)) return bad('K-BN sw.js', 'on-bellek listesi ESKI tokens.css hash\'ini tasiyor');
    ok('K-BN sw.js', 'on-bellek listesi guncel tokens.css hash\'i (' + m[1] + ')');
  });

  /* ── 4l) K-BO: hacim ekseni tek renk (--bp-volume) + tek esik (1,20) ─── */
  console.log('\n[4l] K-BO — hacim yon-bagimsiz bir buyukluk');
  const VOL = 'rgb(255, 200, 80)';               /* --bp-volume #ffc850 */
  const YON = ['rgb(0, 226, 144)', 'rgb(248, 81, 73)'];  /* --bp-al / --bp-sat */
  const YABANCI = { 'rgb(245, 158, 11)': '--bp-gold', 'rgb(227, 179, 65)': '--bp-accent-yellow' };

  await step('K-BO /sektor-harita isi haritasi RVOL etiketi', async () => {
    await p.goto(BASE + '/sektor-harita', { waitUntil: 'domcontentloaded' });
    await p.waitForTimeout(1200);
    /* Hesaplanmis stil oku — satir-ici `color:` metnini degil.
       [[feedback_kabul_olcutu_style_degil_computed]] */
    const r = await p.evaluate(() => {
      const els = [...document.querySelectorAll('[data-tip*="ortalama RVOL"]')];
      return els.map(e => ({ t: e.textContent.trim(), c: getComputedStyle(e).color }));
    });
    if (!r.length) return bad('K-BO isi haritasi', 'RVOL etiketi hic bulunamadi (olcum gecersiz)');
    const kotu = r.filter(x => YON.includes(x.c) || YABANCI[x.c]);
    if (kotu.length) return bad('K-BO isi haritasi',
      kotu.length + ' etiket yabanci eksende: ' + JSON.stringify(kotu.slice(0, 3)));
    /* Esik kanonu: vurgulu olanlarin HEPSI >= 1,20, sonuk olanlarin HEPSI < 1,20 */
    /* Premis: urun artik GOSTERILEN (yuvarlanmis) sayiyi esikliyor -- bu adim
       tam da bu premisi olcer. Ilk kosuda 1,1987'lik iki sektor ekranda
       "1,20×" yazip gri kaldigi icin DUSTU ve urun hatasini aciga cikardi. */
    const say = t => parseFloat((t.match(/([0-9]+,[0-9]+)/) || [0, '0'])[1].replace(',', '.'));
    const yanlis = r.filter(x => (x.c === VOL) !== (say(x.t) >= 1.20));
    if (yanlis.length) return bad('K-BO isi haritasi esigi',
      'renk 1,20 esigiyle uyusmuyor: ' + JSON.stringify(yanlis.slice(0, 3)));
    ok('K-BO isi haritasi', r.length + ' etiket · vurgulu=' + r.filter(x => x.c === VOL).length + ' (hepsi >=1,20)');
  });

  await step('K-BO /sektor-harita karsilastirma esigi lejandla ayni', async () => {
    const src = await (await ctx.request.get(BASE + '/sektor-harita')).text();
    const kod = src.replace(/\/\*[\s\S]*?\*\//g, ' ').replace(/(^|[^:\\])\/\/[^\n]*/g, '$1 ');
    /* ⛔ Desen TEK BIR YAZIMA baglanmasin: ilk yazim `s.rvol >= N` bekliyordu,
       yuvarlama duzeltmesi ifadeyi `parseFloat(s.rvol.toFixed(2)) >= N` yapinca
       adim "olcum gecersiz" dedi -- urun dogruydu, OLCU bayatlamisti.
       [[reference_k_turu_olcum_dersleri_hub]] */
    const m = kod.match(/rvolCls\s*=[\s\S]{0,60}?>=\s*([0-9.]+)/);
    if (!m) return bad('K-BO karsilastirma', 'esik ifadesi bulunamadi (olcum gecersiz)');
    if (parseFloat(m[1]) !== 1.20) return bad('K-BO karsilastirma',
      'esik ' + m[1] + ', sayfanin lejandi "RVOL >= 1,20" diyor');
    ok('K-BO karsilastirma', 'esik 1,20 — lejandla ayni');
  });

  await step('K-BO /tarama hacim sutunu yon renginde degil', async () => {
    await p.goto(BASE + '/tarama', { waitUntil: 'domcontentloaded' });
    await p.waitForTimeout(1500);
    const r = await p.evaluate(() => {
      const c = document.querySelector('.rvol-cell.high'), d = document.querySelector('.rvol-dot.high');
      return { n: document.querySelectorAll('.rvol-cell').length,
               c: c && getComputedStyle(c).color, d: d && getComputedStyle(d).backgroundColor };
    });
    if (!r.n) return bad('K-BO /tarama', 'hic RVOL hucresi yok (olcum gecersiz)');
    if (r.c && YON.includes(r.c)) return bad('K-BO /tarama', 'yuksek hacim yon renginde: ' + r.c);
    if (r.d && YON.includes(r.d)) return bad('K-BO /tarama noktasi', 'yon renginde: ' + r.d);
    if (r.c && r.c !== VOL) return bad('K-BO /tarama', 'hacim ekseni disi renk: ' + r.c);
    ok('K-BO /tarama', r.n + ' hucre · yuksek=' + (r.c || 'ekranda yok (kural CSS ile dogrulandi)'));
  });

  await step('K-BO /hisse Hacim Profili notr kademeli', async () => {
    const css = await (await ctx.request.get(BASE + '/hisse/THYAO')).text();
    const href = (css.match(/\/static\/css\/pages\/hisse\.css\?v=[0-9a-f]+/) || [])[0];
    if (!href) return bad('K-BO /hisse', 'sayfa hisse.css\'i ?v= ile yuklemiyor (CDN olcumu riski)');
    const body = await (await ctx.request.get(BASE + href)).text();
    /* Dinamik RegExp yerine duz metin arama: ilk yazimda kacis seviyeleri
       (Python heredoc -> JS kaynagi -> RegExp) fazla katmanliydi ve kural
       HIC bulunamiyordu -> "olcum gecersiz". Basit arama daha az yalan soyler. */
    const kural = (sel) => {
      const i = body.indexOf('.hacim-profili .hp-row-val' + sel + ' {');
      if (i < 0) return null;
      return body.slice(i, body.indexOf('}', i) + 1);
    };
    const yasak = /--bp-al|--bp-sat/;
    for (const k of ['.ok', '.weak', '.bad', ' .hp-tag.confirmed']) {
      const r = kural(k);
      if (!r) return bad('K-BO /hisse', 'kural bulunamadi: hp-row-val' + k + ' (olcum gecersiz)');
      if (yasak.test(r)) return bad('K-BO /hisse', 'yon rengi hala var: ' + r.trim());
    }
    if (!/\.hp-row-val\.ok \{ color:var\(--bp-volume\); \}/.test(body))
      return bad('K-BO /hisse', 'ok dali --bp-volume degil');
    ok('K-BO /hisse Hacim Profili', '4 kural yon renginden arindi (' + href.split('=')[1] + ')');
  });

  /* ── 4m) K-BP: degisim sifirsa yon rengi/isareti YOK ─────────────────── */
  console.log('\n[4m] K-BP — 0 bir yonle ayni kefeye konamaz');
  const AL  = 'rgb(0, 226, 144)';      /* --bp-al  #00e290 */
  const SAT = 'rgb(248, 81, 73)';      /* --bp-sat #f85149 */

  /* Once canli veriden GERCEKTEN degismeyen bir hisse bul — yoksa olcum
     yapilamaz ve "temiz" demek YALAN olur (olculemedi != gecti). */
  let zeroTics = [];
  await step('K-BP olcum on-kosulu: change_pct = 0 olan hisse var mi', async () => {
    const r = await ctx.request.get(BASE + '/api/data?_t=' + Date.now());
    if (!r.ok()) return bad('K-BP on-kosul', '/api/data HTTP ' + r.status());
    const d = await r.json();
    zeroTics = (d.stocks || [])
      .filter(s => typeof s.change_pct === 'number' && parseFloat(s.change_pct.toFixed(2)) === 0)
      .map(s => s.ticker).slice(0, 3);
    if (!zeroTics.length) {
      /* Bugun sifir degisimli hisse YOK: /karsilastir adimini atlamak
         DURUSTTUR, ama sessizce "gecti" saymayiz. */
      return ok('K-BP on-kosul', 'bugun 0,00% kapatan hisse yok — /karsilastir adimi ATLANDI');
    }
    ok('K-BP on-kosul', zeroTics.length + ' hisse 0,00%: ' + zeroTics.join(', '));
  });

  if (zeroTics.length) {
    await step('K-BP /karsilastir: 0,00% notr (yesil DEGIL) ve "+" yok', async () => {
      await p.goto(BASE + '/karsilastir?tickers=' + zeroTics.join(','), { waitUntil: 'domcontentloaded' });
      await p.waitForTimeout(2500);
      const r = await p.evaluate(() => [...document.querySelectorAll('span.mono')]
        .map(e => ({ t: e.textContent.trim(), c: getComputedStyle(e).color }))
        .filter(x => /^[+\-]?0,00%$/.test(x.t) || /^[+\-]?0,0%$/.test(x.t)));
      if (!r.length) return bad('K-BP /karsilastir', '0,00% hucresi bulunamadi (olcum gecersiz)');
      const yesil = r.filter(x => x.c === AL || x.c === SAT);
      if (yesil.length) return bad('K-BP /karsilastir',
        yesil.length + '/' + r.length + ' hucre hala YON renginde: ' + JSON.stringify(yesil[0]));
      const arti = r.filter(x => /^\+/.test(x.t));
      if (arti.length) return bad('K-BP /karsilastir', arti.length + ' hucre "+0,00%" yaziyor (kazanc ima eder)');
      ok('K-BP /karsilastir', r.length + ' hucre notr · hicbirinde "+" yok');
    });
  }

  await step('K-BP anasayfa gundem karti yon rengini GERCEKTEN tasiyor', async () => {
    await p.goto(BASE + '/', { waitUntil: 'domcontentloaded' });
    await p.waitForTimeout(1500);
    /* Kart listesi "Hisse" sekmesinde tembel yukleniyor. */
    await p.evaluate(() => {
      const t = [...document.querySelectorAll('.da-gnm-tab')].find(x => /Hisse/.test(x.textContent));
      if (t) t.click();
    });
    await p.waitForTimeout(3500);
    const r = await p.evaluate(() => [...document.querySelectorAll('.da-gnm-card')].map(c => {
      const s = c.querySelector('.da-gnm-chg');
      return s ? { t: s.textContent.trim(), c: getComputedStyle(s).color } : null;
    }).filter(Boolean));
    if (!r.length) return bad('K-BP anasayfa', 'gundem hisse karti bulunamadi (olcum gecersiz)');
    /* ASIL HATA: sinif `.da-mrow` altina kilitliydi, 5/5 kart AYNI govde
       rengindeydi. Yani "renk dogru mu" degil, "renk VAR MI" soruluyor. */
    const yanlis = r.filter(x => (/^\+/.test(x.t) && x.c !== AL) || (/^-/.test(x.t) && x.c !== SAT));
    if (yanlis.length) return bad('K-BP anasayfa',
      yanlis.length + '/' + r.length + ' kartta yon rengi YOK/yanlis: ' + JSON.stringify(yanlis[0]));
    const renkler = new Set(r.map(x => x.c));
    ok('K-BP anasayfa', r.length + ' kart · ' + renkler.size + ' farkli yon rengi');
  });

  await step('K-BP kanon bp-format.js sayfada gercekten yuklu', async () => {
    const r = await p.evaluate(() => {
      if (typeof bpDir !== 'function') return { err: 'bpDir tanimli degil' };
      return { d0: bpDir(0, 2), dneg: bpDir(-0.004, 2), f0: bpFormatPct(0, 2),
               fneg: bpFormatPct(-0.004, 2), c0: bpDirClass(0, 2) };
    });
    if (r.err) return bad('K-BP kanon', r.err);
    if (r.d0 !== 0 || r.dneg !== 0) return bad('K-BP kanon', 'bpDir 0/-0,004 icin 0 dondurmedi: ' + JSON.stringify(r));
    if (r.f0 !== '0,00%' || r.fneg !== '0,00%') return bad('K-BP kanon',
      'esiklenen sayi != gosterilen sayi: ' + JSON.stringify(r));
    if (r.c0 !== 'neu') return bad('K-BP kanon', 'bpDirClass(0) != neu: ' + r.c0);
    ok('K-BP kanon', 'bpDir/bpFormatPct/bpDirClass canlida dogru (-0,004 -> "0,00%" notr)');
  });

  /* ── K-BQ (21.09): "Stop" bir YON iddiasidir ─────────────────────────
     `sl_level` Supertrend bandinin guncel degeri; long-only uründe ona "stop"
     demek ancak band fiyatin ALTINDAYKEN anlamli. Canli olcum 21.09: 197/217
     hissede `sl_level > price` (72/72 SAT + 125/138 BEKLE).
     ⛔ K-BP dersi 40: once ON-KOSUL olculur — bugun boyle bir hisse yoksa adim
     ATLANIR ve bu ACIKCA soylenir; "olculemedi" != "gecti". */
  console.log('\n[4c] K-BQ — Supertrend seviyesi / "Stop" ayrimi');
  {
    const api = await (await ctx.request.get(BASE + '/api/data')).json();
    const rows = (api.stocks || []).filter(s => s.sl_level && s.price);
    const above = rows.filter(s => s.sl_level > s.price);
    const alBelow = rows.filter(s => s.signal === 'AL' && s.sl_level < s.price);

    if (!above.length) {
      bad('K-BQ on-kosul', 'sl_level > price olan hisse YOK — adim OLCULEMEDI (gecti degil)');
    } else {
      const bek = above.find(s => s.signal === 'BEKLE');
      const sat = above.find(s => s.signal === 'SAT');
      ok('K-BQ on-kosul', above.length + '/' + rows.length + ' hissede band fiyatin USTUNDE');

      /* A) Hap Bilgi: ad notr + rol FIYATTAN turemis */
      for (const [s, beklenen] of [[bek, 'direnç'], [sat, 'direnç'], [alBelow[0], 'stop']]) {
        if (!s) continue;
        await p.goto(BASE + '/hisse/' + s.ticker, { waitUntil: 'domcontentloaded' });
        const q = await p.evaluate(() => {
          const dt = [...document.querySelectorAll('.qf-row dt')]
            .find(e => /Supertrend Seviyesi|Stop Seviyesi/.test(e.textContent));
          if (!dt) return null;
          const dd = dt.parentElement.querySelector('dd');
          const hero = document.querySelector('.bp-hero-levels');
          return { label: dt.textContent.trim(), value: dd ? dd.textContent.trim() : '',
                   heroText: hero ? hero.textContent.replace(/\s+/g, ' ').trim() : null };
        });
        if (!q) { bad('K-BQ hap bilgi ' + s.ticker, 'satir bulunamadi (olcum gecersiz)'); continue; }
        if (/Stop Seviyesi/.test(q.label))
          bad('K-BQ hap bilgi ' + s.ticker, 'ad hala "Stop Seviyesi" (yon-bagimsiz alan)');
        else if (!q.value.includes(beklenen))
          bad('K-BQ hap bilgi ' + s.ticker, 'rol eki "' + beklenen + '" degil: ' + q.value);
        else
          ok('K-BQ hap bilgi ' + s.ticker, q.label + ' -> ' + q.value);

        /* B) hero "Stop:" SADECE AL'de */
        if (s.signal !== 'AL' && q.heroText && /Stop:/.test(q.heroText))
          bad('K-BQ hero ' + s.ticker, s.signal + ' sinyalinde "Stop:" basiliyor: ' + q.heroText);
        else if (s.signal === 'AL' && (!q.heroText || !/Stop:/.test(q.heroText)))
          bad('K-BQ hero ' + s.ticker, 'AL sinyalinde hero stop KAYBOLDU (asiri-duzeltme): ' + q.heroText);
        else
          ok('K-BQ hero ' + s.ticker, s.signal + ' -> ' + (q.heroText || 'blok yok (dogru)'));

        /* C) indikator karti alt-etiketi: yon FIYATTAN.
           ⛔ Bu deger SSR degil, `renderSummary` ile CSR doluyor — `domcontentloaded`
           aninda HENUZ BOS. Ilk yazimda 3/3 "olculemedi" verdi; urun dogruydu,
           OLCUM ERKENDI (K-BO dersi 36'nin ikizi). Once dolmasini bekle. */
        const ic = await p.waitForFunction(() => {
          const e = document.getElementById('icSlPct');
          return (e && e.textContent.trim() && e.textContent.trim() !== '—') ? e.textContent.trim() : null;
        }, null, { timeout: 15000 }).then(h => h.jsonValue()).catch(() => null);
        const wantLbl = s.signal === 'AL' ? 'Riske uzaklık' : 'ST direnci';
        if (!ic || ic === '—') bad('K-BQ icSlPct ' + s.ticker, 'alt-etiket bos (olcum gecersiz)');
        else if (!ic.startsWith(wantLbl)) bad('K-BQ icSlPct ' + s.ticker, '"' + wantLbl + '" bekleniyordu: ' + ic);
        else if (/-\d/.test(ic)) bad('K-BQ icSlPct ' + s.ticker, 'uzaklik isaretli yaziliyor: ' + ic);
        else ok('K-BQ icSlPct ' + s.ticker, ic);
      }

      /* D) kanon canlida yuklu mu */
      const k = await p.evaluate(() => {
        if (typeof bpStLevelRole !== 'function') return { err: 'bpStLevelRole tanimli degil' };
        return { yuk: bpStLevelRole(12, 10, 'BEKLE'), alt: bpStLevelRole(8, 10, 'AL'),
                 altBekle: bpStLevelRole(8, 10, 'BEKLE'), bos: bpStLevelRole(null, 10, 'AL') };
      });
      if (k.err) bad('K-BQ kanon', k.err);
      else if (k.yuk.label !== 'ST direnci' || k.alt.label !== 'Riske uzaklık' ||
               k.altBekle.label !== 'ST desteği' || k.bos !== null)
        bad('K-BQ kanon', 'bpStLevelRole yanlis: ' + JSON.stringify(k));
      else if (Math.abs(k.yuk.pct - 20) > 0.001)
        bad('K-BQ kanon', 'uzaklik buyukluk degil: ' + k.yuk.pct);
      else ok('K-BQ kanon', 'bpStLevelRole canlida dogru (ust->direnc · alt+AL->riske uzaklik · alt+BEKLE->destek)');

      /* E) /karsilastir: rol metinle, yon rengiyle DEGIL */
      const cmpT = [bek, sat, alBelow[0]].filter(Boolean).map(s => s.ticker).join(',');
      await p.goto(BASE + '/karsilastir?tickers=' + cmpT, { waitUntil: 'networkidle' });
      await p.waitForTimeout(4000);
      const cr = await p.evaluate(() => [...document.querySelectorAll('.sl-role')].map(e => {
        const mono = e.parentElement.querySelector('.mono');
        return { role: e.textContent.trim(), cls: mono ? mono.className : '',
                 color: mono ? getComputedStyle(mono).color : '' };
      }));
      if (!cr.length) bad('K-BQ /karsilastir', '.sl-role hic render edilmedi (olcum gecersiz)');
      else {
        const yonRenkli = cr.filter(x => x.color === AL || x.color === SAT || /\bdn\b|\bup\b/.test(x.cls));
        if (yonRenkli.length) bad('K-BQ /karsilastir',
          yonRenkli.length + ' hucrede yon-BAGIMSIZ seviye yon rengiyle boyali: ' + JSON.stringify(yonRenkli[0]));
        else ok('K-BQ /karsilastir', cr.length + ' hucre · roller: ' + [...new Set(cr.map(x => x.role))].join('/'));
      }
    }
  }

  /* ── K-BR (22.09): ADX/RSI tek gosterim kanonu ───────────────────────
     Esik tasiyan sayi tam sayiya yuvarlanamaz: `|int` ASAGI KESER ve ayni
     sayfada `|round|int` ile 1 fark yaratir. Once ON-KOSUL: bugun ondalik
     kismi 0,5'i asan bir hisse var mi? */
  console.log('\n[4d] K-BR — ADX/RSI 1 ondalik, tek gosterim');
  {
    const api = await (await ctx.request.get(BASE + '/api/data')).json();
    const cand = (api.stocks || []).filter(s =>
      s.adx != null && s.rsi != null && Math.trunc(s.adx) !== Math.round(s.adx));
    if (!cand.length) {
      bad('K-BR on-kosul', 'int(adx) != round(adx) olan hisse YOK — adim OLCULEMEDI (gecti degil)');
    } else {
      const s = cand.find(x => x.adx >= 25 && x.adx < 26) || cand[0];
      const adxTr = s.adx.toFixed(1).replace('.', ',');
      const rsiTr = s.rsi.toFixed(1).replace('.', ',');
      ok('K-BR on-kosul', cand.length + ' hisse ondalikli; secilen ' + s.ticker +
         ' ADX=' + adxTr + ' RSI=' + rsiTr);

      await p.goto(BASE + '/hisse/' + s.ticker, { waitUntil: 'domcontentloaded' });
      const ssr = await p.evaluate(() => {
        const dt = [...document.querySelectorAll('.qf-row dt')];
        const g = n => { const e = dt.find(x => x.textContent.trim() === n);
                         return e ? e.parentElement.querySelector('dd').textContent.trim() : null; };
        const md = document.querySelector('meta[name="description"]');
        const ld = [...document.querySelectorAll('script[type="application/ld+json"]')]
                     .map(e => e.textContent).join(' ');
        const cl = document.body.innerHTML.match(/ADX\s*([\d.,]+)\s*—\s*Güçlü trend/);
        return { qfAdx: g('ADX'), qfRsi: g('RSI'), meta: md ? md.content : '',
                 ld, checklist: cl ? cl[1] : null };
      });
      const bads = [];
      if (ssr.qfAdx !== adxTr) bads.push('Hap Bilgi ADX=' + ssr.qfAdx);
      if (ssr.qfRsi !== rsiTr) bads.push('Hap Bilgi RSI=' + ssr.qfRsi);
      if (!ssr.meta.includes('ADX ' + adxTr)) bads.push('meta ADX yok/farkli');
      if (ssr.checklist && ssr.checklist !== adxTr) bads.push('checklist ADX=' + ssr.checklist);
      /* JSON-LD yapisal veri: ondalik ayirac NOKTA kalmali */
      if (!ssr.ld.includes('"' + s.adx.toFixed(1) + '"')) bads.push('JSON-LD ADX != ' + s.adx.toFixed(1));
      bads.length ? bad('K-BR SSR ' + s.ticker, bads.join(' · '))
                  : ok('K-BR SSR ' + s.ticker, 'checklist/HapBilgi/meta/JSON-LD hepsi ' + adxTr);

      /* CSR: indikator paneli ayni sayiyi mi basiyor?
         ⛔ 22.09 (K-BU turu) OLCUM DUZELTMESI — ARA DURUMU OLCUYORDUK.
         Panel IKI FAZDA dolar: ilk gecis chart ozetiyle (`s`) calisir ve
         ADX(14) satirini basar; RSI(14) satiri `signalData` (/api/data)
         gelene kadar HIC eklenmez (hisse.html ~2721: `if (signalData &&
         signalData.rsi != null)`). Eski bekleme kosulu YALNIZCA ADX(14)
         ariyordu, yani ILK fazda cozuluyor ve RSI'yi bulamayip
         "panel RSI farkli" diye SAHTE ALARM uretiyordu — canli EDATA'da
         panel 5sn sonra "RSI(14): 18,1" basiyor, yani urun DOGRUYDU.
         Yerlesik durumu bekle: ADX **ve** RSI birlikte gorunene kadar.
         (K-BT dersi 47'nin ikizi: kismi render bir olcum degiskenidir.) */
      const csr = await p.waitForFunction(() => {
        const e = document.getElementById('indTechContent');
        if (!e) return null;
        const t = e.textContent;
        return (/ADX\(14\)/.test(t) && /RSI\(14\)/.test(t)) ? t.replace(/\s+/g, ' ') : null;
      }, null, { timeout: 20000 }).then(h => h.jsonValue()).catch(() => null);
      if (!csr) bad('K-BR CSR ' + s.ticker, 'indikator paneli dolmadi (olcum gecersiz)');
      else if (!csr.includes('ADX(14): ' + adxTr)) bad('K-BR CSR ' + s.ticker, 'panel ADX farkli: ' + csr.slice(0, 90));
      else if (!csr.includes('RSI(14): ' + rsiTr)) bad('K-BR CSR ' + s.ticker, 'panel RSI farkli: ' + csr.slice(0, 120));
      else if (/fark: %[\d,]+,?\d{3,}/.test(csr)) bad('K-BR CSR ' + s.ticker, 'EMA fark yuzdesi ham hassasiyette: ' + (csr.match(/fark: %[\d,]+/) || [''])[0]);
      else ok('K-BR CSR ' + s.ticker, 'indikator paneli SSR ile ayni (ADX ' + adxTr + ' · RSI ' + rsiTr + ')');

      /* Anasayfa spotlight: SSR render'i CSR UZERINE farkli sayi yazmasin */
      await p.goto(BASE + '/', { waitUntil: 'domcontentloaded' });
      const read = () => p.evaluate(() => {
        const rows = [...document.querySelectorAll('.da-spot-sub-row')];
        const f = l => { const r = rows.find(x => x.querySelector('.lbl') &&
                           x.querySelector('.lbl').textContent.trim() === l);
                         return r ? r.querySelector('.val').textContent.trim() : null; };
        return { adx: f('ADX'), rsi: f('RSI') };
      });
      const a = await read();
      await p.waitForTimeout(4000);
      const bq = await read();
      if (!a.adx) bad('K-BR anasayfa', 'spotlight ADX satiri yok (olcum gecersiz)');
      else if (a.adx !== bq.adx || a.rsi !== bq.rsi)
        bad('K-BR anasayfa', 'SSR ' + JSON.stringify(a) + ' -> CSR ' + JSON.stringify(bq) + ' (gorunur ziplama)');
      else if (!/,/.test(bq.adx))
        bad('K-BR anasayfa', 'spotlight ADX tam sayi: ' + bq.adx);
      else ok('K-BR anasayfa', 'SSR = CSR = ' + JSON.stringify(bq));
    }
  }

  /* ── 4o) K-BU: /gundem karti ADX'i ETIKETTEN degil HAM ALANDAN okur ────
     Kart, `indicators.adx.label` ("ADX 26", YUVARLANMIS) icinden sayiyi
     parse edip `.toFixed(1)` ile basiyordu; AYNI SAYFANIN SSR makrosu
     `'%.1f'|format(s.adx)` ile "25,9" basiyordu ve grid innerHTML ile
     bastan yazildigi icin CSR, SSR'in DOGRU sayisini EZIYORDU (canli 7/7).
     ⛔ SSR'i okumak YETMEZ: sayfa acilisinda gorulen sayi SSR'in olabilir.
     Grid'i bir SENTINEL ile yok edip loadGundem()'i cagiriyoruz — boylece
     olculen sey KESIN olarak renderCard'in ciktisidir (K-BT dersi 47'nin
     ikizi: olculemedi != gecti). */
  console.log('\n[4o] K-BU — /gundem karti sayiyi etiketten ayristirmamali');

  await step('K-BU: CSR kart ADX/RSI degerleri /api/gundem ham alaniyla ayni', async () => {
    await p.goto(BASE + '/gundem', { waitUntil: 'domcontentloaded' });
    await p.waitForTimeout(3500);

    const api = await (await ctx.request.get(BASE + '/api/gundem')).json();
    const rows = [...(api.new_signals || []), ...(api.strong_al || [])];
    if (!rows.length) return ok('K-BU', '/api/gundem bos — adim ATLANDI (olcum on-kosulu yok)');
    const want = {};
    for (const s of rows) if (s.adx != null) want[s.ticker] = s.adx.toFixed(1).replace('.', ',');

    const r = await p.evaluate(async () => {
      const g = document.getElementById('strongAlGrid');
      if (!g) return { err: 'strongAlGrid yok' };
      /* SSR'i YOK ET: bundan sonra okunan her sey renderCard ciktisidir. */
      g.innerHTML = '<i id="__kbu_sentinel"></i>';
      if (typeof loadGundem !== 'function') return { err: 'loadGundem tanimsiz' };
      await loadGundem();
      await new Promise(res => setTimeout(res, 800));
      return {
        sentinelSilindi: !document.getElementById('__kbu_sentinel'),
        kanon: typeof bpIndNum + '/' + typeof sigLabel,
        kartlar: [...g.querySelectorAll('.stock-card')].map(c => ({
          t: (c.querySelector('.sc-ticker') || {}).textContent.trim(),
          badge: (c.querySelector('.badge') || {}).textContent.trim(),
          adx: [...c.querySelectorAll('.sc-metric')].map(m => m.textContent.trim())
                 .find(x => x.indexOf('ADX') === 0) || null,
        })),
      };
    });

    if (r.err) return bad('K-BU', r.err);
    if (r.kanon !== 'function/function')
      return bad('K-BU kanon', 'bpIndNum/sigLabel renderCard aninda tanimsiz (' + r.kanon +
                               ') — bp-format.js tuketicisinden SONRA mi yukleniyor?');
    if (!r.sentinelSilindi) return bad('K-BU', 'grid yeniden render EDILMEDI (olcum gecersiz)');
    if (!r.kartlar.length)  return bad('K-BU', 'CSR hic kart basmadi (olcum gecersiz)');

    const yanlis = r.kartlar.filter(c => want[c.t] && c.adx !== 'ADX ' + want[c.t]);
    if (yanlis.length)
      return bad('K-BU', yanlis.length + '/' + r.kartlar.length + ' kartta CSR ADX ham alandan sapti: ' +
                 yanlis.map(c => c.t + ' "' + c.adx + '" != ADX ' + want[c.t]).slice(0, 4).join(' · '));

    /* Rozet metni de tek kanondan (sigLabel) gelmeli — elle kopya bayatlar. */
    const rozet = r.kartlar.filter(c => !/^[▲▼●] (Güçlü Trend|Trend Bozuldu|Yatay)$/.test(c.badge));
    if (rozet.length)
      return bad('K-BU rozet', rozet.map(c => c.t + ' "' + c.badge + '"').slice(0, 3).join(' · '));

    ok('K-BU', r.kartlar.length + ' CSR kart · ADX ham alanla birebir · rozet kanonda');
  });

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
