#!/usr/bin/env node
// tools/aria-ref-check.js — K-AJ: KIRIK KİMLİK REFERANSLARI
// WCAG 2.1 · SC 1.3.1 "Info and Relationships" (A) + SC 4.1.2 "Name, Role, Value" (A)
//                    + SC 2.4.1/2.4.4 (ölü iç bağlantı, kullanıcının gittiği yer YOK)
//
// SORU — 20 tur ARIA EKLENDİ, HİÇ KİMSE "BU REFERANSLAR ÇÖZÜLÜYOR MU?" DİYE SORMADI:
//   K-N/K-R/K-S/K-T/K-AC/K-AH/K-AI turları sayfaya `aria-labelledby`,
//   `aria-controls`, `aria-describedby`, `label[for]` yazdı. Bunların HEPSİ
//   **IDREF**'tir: hedef id yoksa tarayıcı sessizce YOK SAYAR. Hata yok,
//   konsol çıktısı yok, görsel fark yok. Ekran okuyucu adı/açıklamayı
//   duyurmaz — biz "erişilebilir yaptık" diye kaydederiz. Sessiz başarısızlık.
//
//   Üçüncü eksen ise KANITLANMIŞ GERÇEK bir kusur sınıfı: /hisseler'in
//   `#letter-X` derin bağlantıları hedefleri olmadığı için ÖLÜYDÜ (fix
//   `1c88c44`). O tek sayfada elle bulunmuştu; bu tur 20 sayfanın HEPSİNDE
//   ölçer.
//
// ⛔ REFERANSI KENDİM ÇÖZMÜYORUM, BELGEYE SORUYORUM: `document.getElementById`
//   (HTML spec'in çözdüğü şekilde: ilk eşleşen düğüm, ağaç sırası). Elle
//   querySelector('#'+id) yazmak, id'de nokta/iki nokta/rakam-başlangıcı
//   olduğunda KENDİ sahte-pozitif kaynağım olurdu (`#12ay`, `#p/e` gibi).
//
// BULGU SINIFLARI (hepsinin tabanı SIFIR):
//   A) KIRIK IDREF   — ARIA/label özniteliğindeki token hiçbir id'ye denk gelmiyor.
//   B) YİNELENEN id  — aynı id birden fazla düğümde VE bir yerden referans veriliyor
//                      (çözüm belirsiz: ilk düğüm kazanır, yazar ikinciyi kastetmiş olabilir).
//   C) ÖLÜ İÇ BAĞLANTI — `href="#x"` hedefi yok (`#` ve `#top` hariç: spec'te geçerli).
//   D) SESSİZ BAŞARISIZLIK — referans ÇÖZÜLÜYOR ama anlamsız:
//      · `aria-labelledby`/`aria-describedby` hedefinin metni BOŞ → ad/açıklama YOK
//        (kırık IDREF taraması bunu göremez: hedef VAR, içi boştur).
//      · `aria-expanded` bir açılır listeyi/katmanı "açık" ilan ediyor ama hedefte
//        seçenek/görünür içerik YOK → ekran okuyucu "genişletilmiş" der, kullanıcı
//        Aşağı Ok'a basar, hiçbir şey olmaz.
//      ⛔ `role="tab"` BU EKSENİN DIŞINDADIR: sekmenin durum özniteliği
//         `aria-selected`'tır, `aria-expanded` DEĞİL. İlk yazımım bunu ayırmadığı
//         için /hisseler, /sektor-harita ve /hisse/* sekmelerinde 8 SAHTE-POZİTİF
//         üretti (hepsi ölçümle çürütüldü: role=tab + aria-selected doğruydu).
//
// AYRI SAYILIR (bulgu DEĞİL): referans verilmeyen yinelenen id'ler — geçersiz
//   HTML ama hiçbir kullanıcı yüzeyini kırmıyor; ayrı raporlanır, gürültü yapmaz.
//
// ⛔ AÇILIŞ DURUMU BİR KAPSAM YALANI (K-AI dersi): JS ile açılışta yaratılan
//   bir panel kapalıyken DOM'da YOKTUR → ona işaret eden `aria-controls`
//   "kırık" görünür. --interact katmanları AÇAR, sonra ölçer; iki koşum
//   arasındaki fark sahte-pozitifi ayıklar.
//
// POZİTİF KONTROL (--kill-fix): sayfadaki ÇÖZÜLEN ilk 10 referansın hedef
//   id'sini bozar. Dedektör onları yakalamazsa kördür.
//
// Kullanım: node tools/aria-ref-check.js [--base=...] [--only=/a,/b]
//           [--interact] [--kill-fix] [--json=dosya]
const { chromium } = require('playwright');

const BASE = (process.argv.find(a => a.startsWith('--base=')) || '').split('=')[1] || 'https://borsapusula.com';
const ONLY = (process.argv.find(a => a.startsWith('--only=')) || '').split('=')[1] || '';
const JSON_OUT = (process.argv.find(a => a.startsWith('--json=')) || '').split('=')[1] || '';
const INTERACT = process.argv.includes('--interact');
const KILL_FIX = process.argv.includes('--kill-fix');
// --sim-fix: K-AJ fix'inin CANLI sayfadaki pozitif kontrolü. Fix henüz deploy
//   edilmediği için, canlı sayfaya YEREL (düzeltilmiş) bp-search.js ve
//   learning-mode.js servis edilir — gerçek dosya, gerçek sayfa. Bulgular
//   sıfıra inmiyorsa çare yanlış yerdedir.
const SIM_FIX = process.argv.includes('--sim-fix');
const LOCAL_JS = { 'bp-search.js': 'static/bp-search.js', 'learning-mode.js': 'static/learning-mode.js' };

// reduced-motion / text-clip / focus-obscured / title-tooltip / accessible-name ile AYNI envanter.
const PAGES = [
  '/', '/ozet', '/tarama', '/gundem', '/hisseler', '/sektor-harita',
  '/hisse/ASELS', '/hisse/GARAN', '/karsilastir', '/portfolio',
  '/bilanco-takvimi', '/temettu-takvimi', '/blog', '/blog/rsi-gostergesi-nedir',
  '/metodoloji', '/hakkinda', '/iletisim', '/profil', '/yasal', '/gizlilik',
];
const EXPECT_4XX = new Set(['/profil']);

const IDREF_SINGLE = ['aria-activedescendant', 'aria-errormessage', 'aria-details'];
const IDREF_LIST = ['aria-labelledby', 'aria-describedby', 'aria-controls', 'aria-owns', 'aria-flowto'];

async function measure(page) {
  return page.evaluate(({ IDREF_SINGLE, IDREF_LIST }) => {
    const out = { broken: [], dupRefd: [], dupSilent: [], deadHash: [], silent: [], resolved: 0, hashOk: 0 };

    const label = el => {
      const t = (el.tagName || '').toLowerCase();
      const cls = typeof el.className === 'string' ? el.className.trim().split(/\s+/).slice(0, 2).join('.') : '';
      const txt = (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 40);
      return t + (el.id ? '#' + el.id : '') + (cls ? '.' + cls : '') + (txt ? ' «' + txt + '»' : '');
    };

    // --- id envanteri (yinelenenleri say) ---
    const idCount = Object.create(null);
    document.querySelectorAll('[id]').forEach(el => {
      const id = el.getAttribute('id');
      if (!id) return;
      idCount[id] = (idCount[id] || 0) + 1;
    });
    const referenced = new Set();

    const checkTokens = (el, attr, tokens) => {
      tokens.forEach(id => {
        referenced.add(id);
        // ⛔ getElementById: HTML spec'in kendi çözümü. querySelector('#'+id)
        //    `#12ay` gibi id'lerde ATAR — kendi sahte-pozitifim olurdu.
        const target = document.getElementById(id);
        if (!target) out.broken.push({ attr, id, on: label(el) });
        else out.resolved++;
      });
    };

    IDREF_LIST.forEach(attr => {
      document.querySelectorAll('[' + attr + ']').forEach(el => {
        const raw = (el.getAttribute(attr) || '').trim();
        if (!raw) return;   // boş öznitelik ≠ kırık referans, ayrı kusur
        checkTokens(el, attr, raw.split(/\s+/).filter(Boolean));
      });
    });
    IDREF_SINGLE.forEach(attr => {
      document.querySelectorAll('[' + attr + ']').forEach(el => {
        const raw = (el.getAttribute(attr) || '').trim();
        if (raw) checkTokens(el, attr, [raw]);
      });
    });
    // label[for] / output[for] — `for` yalnız BU iki elemanda IDREF'tir.
    document.querySelectorAll('label[for], output[for]').forEach(el => {
      const raw = (el.getAttribute('for') || '').trim();
      if (raw) checkTokens(el, el.tagName.toLowerCase() + '[for]', [raw]);
    });

    // --- D) SESSİZ BAŞARISIZLIK: referans çözülüyor ama anlamsız ---
    ['aria-labelledby', 'aria-describedby'].forEach(attr => {
      document.querySelectorAll('[' + attr + ']').forEach(el => {
        (el.getAttribute(attr) || '').trim().split(/\s+/).filter(Boolean).forEach(id => {
          const t = document.getElementById(id);
          if (!t) return;                       // kırık = A sınıfı, burada sayma
          const name = (t.getAttribute('aria-label') || t.textContent || '').trim();
          if (!name) out.silent.push({ kind: 'BOS-AD-KAYNAGI', attr, id, on: label(el) });
        });
      });
    });
    document.querySelectorAll('[aria-expanded="true"][aria-controls]').forEach(el => {
      // ⛔ role=tab'ın durum özniteliği aria-selected'tır; bu eksen onu KAPSAMAZ.
      if (el.getAttribute('role') === 'tab') return;
      (el.getAttribute('aria-controls') || '').trim().split(/\s+/).filter(Boolean).forEach(id => {
        const t = document.getElementById(id);
        if (!t) return;
        const cs = getComputedStyle(t);
        const empty = t.querySelectorAll('[role="option"],[role="menuitem"],[role="treeitem"]').length === 0
                      && !(t.textContent || '').trim();
        if (cs.display === 'none' || cs.visibility === 'hidden' || empty)
          out.silent.push({ kind: 'ACIK-AMA-BOS', attr: 'aria-expanded=true', id, on: label(el) });
      });
    });

    // --- yinelenen id'ler ---
    Object.keys(idCount).forEach(id => {
      if (idCount[id] < 2) return;
      const rec = { id, count: idCount[id], on: label(document.getElementById(id)) };
      if (referenced.has(id)) out.dupRefd.push(rec); else out.dupSilent.push(rec);
    });

    // --- ölü iç bağlantı ---
    document.querySelectorAll('a[href^="#"]').forEach(a => {
      const h = a.getAttribute('href') || '';
      const frag = h.slice(1);
      if (!frag || frag.toLowerCase() === 'top') return;  // spec'te geçerli: sayfa başı
      let id;
      try { id = decodeURIComponent(frag); } catch (e) { id = frag; }
      const target = document.getElementById(id) || document.getElementsByName(id)[0];
      if (!target) out.deadHash.push({ href: h, on: label(a) });
      else out.hashOk++;
    });

    return out;
  }, { IDREF_SINGLE, IDREF_LIST });
}

// Sayfadaki bilinen katman dillerini açar (K-R/K-S/K-T/K-AC envanteri).
async function openLayers(page) {
  await page.evaluate(() => {
    document.querySelectorAll('details').forEach(d => { d.open = true; });
    document.querySelectorAll('[role="tab"],.tab-btn,.gnm-tab,[data-tab]').forEach(t => {
      try { t.click(); } catch (e) {}
    });
    document.querySelectorAll('[aria-expanded="false"]').forEach(t => {
      try { t.click(); } catch (e) {}
    });
  });
  await page.waitForTimeout(500);
}

async function run() {
  const browser = await chromium.launch();
  const pages = ONLY ? ONLY.split(',') : PAGES;
  const report = [];
  let tot = { broken: 0, dupRefd: 0, dupSilent: 0, deadHash: 0, silent: 0, resolved: 0, hashOk: 0 };

  for (const path of pages) {
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    if (SIM_FIX) {
      for (const [name, file] of Object.entries(LOCAL_JS)) {
        await ctx.route('**/static/' + name + '*', r =>
          r.fulfill({ contentType: 'application/javascript', body: require('fs').readFileSync(file, 'utf8') }));
      }
    }
    const page = await ctx.newPage();
    try {
      const resp = await page.goto(BASE + path, { waitUntil: 'networkidle', timeout: 45000 });
      const status = resp ? resp.status() : 0;
      if (status >= 400 && !EXPECT_4XX.has(path)) {
        console.log(`  !! ${path} → HTTP ${status}`);
        await ctx.close(); continue;
      }
      await page.waitForTimeout(900);
      if (INTERACT) await openLayers(page);
      if (KILL_FIX) {
        // POZİTİF KONTROL: ÇÖZÜLEN ilk 10 referansın hedefini bozar.
        await page.evaluate(() => {
          const attrs = ['aria-labelledby', 'aria-describedby', 'aria-controls', 'aria-owns'];
          let n = 0;
          for (const a of attrs) {
            for (const el of document.querySelectorAll('[' + a + ']')) {
              if (n >= 10) break;
              const ids = (el.getAttribute(a) || '').trim().split(/\s+/).filter(Boolean);
              for (const id of ids) {
                const t = document.getElementById(id);
                if (t) { t.id = id + '-KILLED'; n++; break; }
              }
            }
          }
        });
      }
      const r = await measure(page);
      tot.resolved += r.resolved; tot.hashOk += r.hashOk;
      tot.broken += r.broken.length; tot.dupRefd += r.dupRefd.length;
      tot.dupSilent += r.dupSilent.length; tot.deadHash += r.deadHash.length;
      tot.silent += r.silent.length;
      const bad = r.broken.length + r.dupRefd.length + r.deadHash.length + r.silent.length;
      console.log(`${bad ? 'X' : 'OK'}  ${path.padEnd(30)} kirik=${r.broken.length} yin-ref=${r.dupRefd.length} olu-link=${r.deadHash.length} sessiz=${r.silent.length}  (cozulen=${r.resolved}, hash-ok=${r.hashOk}, yin-sessiz=${r.dupSilent.length})`);
      r.broken.forEach(b => console.log(`      KIRIK ${b.attr}="${b.id}"  ->  ${b.on}`));
      r.dupRefd.forEach(d => console.log(`      YINELENEN id="${d.id}" x${d.count} (REFERANS VERILIYOR)  ilk: ${d.on}`));
      r.deadHash.forEach(d => console.log(`      OLU LINK ${d.href}  ->  ${d.on}`));
      r.silent.forEach(d => console.log(`      SESSIZ ${d.kind} ${d.attr} -> "${d.id}"  ->  ${d.on}`));
      report.push({ path, ...r });
    } catch (e) {
      console.log(`  !! ${path} → ${e.message.split('\n')[0]}`);
    }
    await ctx.close();
  }
  await browser.close();
  console.log(`\nTOPLAM: kirik-idref=${tot.broken}  yinelenen-id(referansli)=${tot.dupRefd}  olu-ic-baglanti=${tot.deadHash}  sessiz-basarisizlik=${tot.silent}`);
  console.log(`OLCULDU: cozulen-idref=${tot.resolved}  calisan-hash=${tot.hashOk}  yinelenen-id(sessiz)=${tot.dupSilent}`);
  if (JSON_OUT) require('fs').writeFileSync(JSON_OUT, JSON.stringify({ tot, report }, null, 2));
  process.exit(tot.broken + tot.dupRefd + tot.deadHash + tot.silent ? 1 : 0);
}
run();
