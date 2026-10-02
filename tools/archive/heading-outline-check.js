#!/usr/bin/env node
// tools/heading-outline-check.js — K-AM: BELGE BAŞLIK HİYERARŞİSİ
// WCAG 2.1 · SC 1.3.1 "Info and Relationships" (A) + SC 2.4.6 "Headings and Labels" (AA)
//
// SORU — bu sitede daha önce HİÇ sorulmadı:
//   Ekran okuyucu kullanıcısının bir veri sayfasında birincil gezinme aracı
//   BAŞLIK LİSTESİDİR (NVDA/JAWS "H" tuşu, VoiceOver rotoru). BorsaPusula'nın
//   sayfaları 17 farklı kabuktan türüyor ve içeriğin çoğu JS ile basılıyor —
//   başlık seviyeleri şablonda değil, ÇALIŞMA ZAMANINDA oluşuyor.
//   Eğer h2'den h4'e atlanıyorsa kullanıcı "bir bölümü kaçırdım mı?" diye
//   geri döner; sayfada iki h1 varsa "hangisi bu sayfa?" belirsizleşir;
//   boş bir başlık rotorda ADSIZ bir satır olur.
//
// ⛔ GENİŞLİĞE BAĞLIDIR: `.hide-mob` / `.hide-mob-narrow` bölümler 375px'te
//   display:none olur — 1280px'te SAĞLAM olan bir zincir 375px'te KIRILABİLİR.
//   Tek genişlikte ölçmek kapsam yalanıdır. [[reference_dedektor_tek_genislik_kapsam_yalani]]
//
// ⛔ ERİŞİLEBİLİRLİK AĞACI ≠ GÖRÜNÜRLÜK: `.sr-only` başlıklar 1px'tir ama
//   ekran okuyucuda VARDIR ve zincirin parçasıdır. Boyut filtresi kullanmak
//   onları düşürür ve OLMAYAN bir atlama uydurur. Ölçüt: display:none değil,
//   visibility:hidden değil, aria-hidden/inert/[hidden] altında değil.
//
// ⛔ GİZLİ SEKME PANELLERİ (K-T dersi): /hisse'de sekme panelleri hidden'dır;
//   içlerindeki başlıklar o an ağaçta YOKTUR ama sekme açılınca zincire girer.
//   Bu yüzden `--tabs` ile her sekme tek tek açılıp AYRI ölçülür.
//
// BULGU SINIFLARI (taban SIFIR):
//   H1_YOK      — sayfada erişilebilir h1 hiç yok
//   H1_COKLU    — birden fazla h1
//   ATLAMA      — önceki başlıktan seviye 1'den fazla artıyor (h2 → h4)
//   BOS         — başlığın erişilebilir adı yok
//   SEVIYESIZ   — role="heading" var, geçerli aria-level yok
// AYRI SINIF (sayılır, bulguyu şişirmez):
//   MUGLAK      — aynı seviyede birebir aynı metin tekrar ediyor (rotor ayırt edemez)
//
// POZİTİF KONTROL (--kill-fix): her h2 h4'e indirilir + ilk h1 h2 yapılır.
//   ATLAMA ve H1_YOK FIRLAMALI. [[feedback_positif_kontrol_checkout_commit_once]]
//
// Kullanım: node tools/heading-outline-check.js [--base=...] [--w=375,1280]
//           [--only=/a,/b] [--tabs] [--kill-fix] [--json=dosya]
const { chromium } = require('playwright');

const BASE = (process.argv.find(a => a.startsWith('--base=')) || '').split('=')[1] || 'https://borsapusula.com';
const WIDTHS = ((process.argv.find(a => a.startsWith('--w=')) || '').split('=')[1] || '375,1280')
  .split(',').map(s => parseInt(s, 10)).filter(Boolean);
const ONLY = (process.argv.find(a => a.startsWith('--only=')) || '').split('=')[1] || '';
const JSON_OUT = (process.argv.find(a => a.startsWith('--json=')) || '').split('=')[1] || '';
const KILL_FIX = process.argv.includes('--kill-fix');
const TABS = process.argv.includes('--tabs');

// color-only / title-tooltip / text-clip / focus-obscured ile AYNI envanter
const PAGES = [
  '/', '/ozet', '/tarama', '/gundem', '/hisseler', '/sektor-harita',
  '/hisse/ASELS', '/hisse/GARAN', '/karsilastir', '/portfolio',
  '/takvim', '/blog', '/blog/rsi-gostergesi-nedir',
  '/metodoloji', '/hakkinda', '/iletisim', '/profil', '/yasal', '/gizlilik',
];
const EXPECT_4XX = new Set(['/profil']);

const PROBE = (opts) => {
  const KILL = opts.kill;

  // ── pozitif kontrol: zinciri KASITLI boz ──────────────────────────────
  if (KILL) {
    const h1 = document.querySelector('h1');
    if (h1) h1.setAttribute('role', 'presentation'), h1.setAttribute('aria-hidden', 'true');
    document.querySelectorAll('h2').forEach(h => { h.setAttribute('role', 'heading'); h.setAttribute('aria-level', '4'); });
  }

  // ── erişilebilirlik ağacında mı? (BOYUT DEĞİL) ────────────────────────
  const inTree = (el) => {
    if (el.closest('[aria-hidden="true"],[inert],[hidden]')) return false;
    let n = el;
    while (n && n.nodeType === 1) {
      const cs = getComputedStyle(n);
      if (cs.display === 'none' || cs.visibility === 'hidden' || cs.visibility === 'collapse') return false;
      if (n.tagName === 'TEMPLATE') return false;
      n = n.parentElement;
    }
    return true;
  };

  const accName = (el) => {
    const al = (el.getAttribute('aria-label') || '').trim();
    if (al) return al;
    const lb = el.getAttribute('aria-labelledby');
    if (lb) {
      const t = lb.split(/\s+/).map(id => {
        const e = document.getElementById(id);
        return e ? (e.textContent || '').trim() : '';
      }).join(' ').trim();
      if (t) return t;
    }
    // aria-hidden alt düğümler ada girmez
    const clone = el.cloneNode(true);
    clone.querySelectorAll('[aria-hidden="true"]').forEach(n => n.remove());
    return (clone.textContent || '').replace(/\s+/g, ' ').trim();
  };

  const desc = (el) => {
    const id = el.id ? '#' + el.id : '';
    const cl = (typeof el.className === 'string' && el.className)
      ? '.' + el.className.trim().split(/\s+/).slice(0, 2).join('.') : '';
    return el.tagName.toLowerCase() + id + cl;
  };

  const levelOf = (el) => {
    const m = /^H([1-6])$/.exec(el.tagName);
    if (m) {
      const al = el.getAttribute('aria-level');
      if (al && /^[1-9]\d*$/.test(al.trim())) return parseInt(al, 10);
      // role ile başlıklıktan çıkarılmışsa zincire girmez
      const r = (el.getAttribute('role') || '').trim().toLowerCase();
      if (r && r !== 'heading') return null;
      return parseInt(m[1], 10);
    }
    const r = (el.getAttribute('role') || '').trim().toLowerCase();
    if (r !== 'heading') return null;
    const al = (el.getAttribute('aria-level') || '').trim();
    if (/^[1-9]\d*$/.test(al)) return parseInt(al, 10);
    return 0; // SEVİYESİZ — role=heading ama aria-level yok
  };

  const all = Array.from(document.querySelectorAll('h1,h2,h3,h4,h5,h6,[role="heading"]'));
  const scanned = all.length;
  const outline = [];
  let hiddenCnt = 0;
  for (const el of all) {
    if (!inTree(el)) { hiddenCnt++; continue; }
    const lvl = levelOf(el);
    if (lvl === null) continue;            // role ile başlıklıktan çıkarılmış
    outline.push({ el: desc(el), lvl, text: accName(el) });
  }

  const findings = [];
  const h1s = outline.filter(o => o.lvl === 1);
  if (h1s.length === 0) findings.push({ k: 'H1_YOK', el: '(belge)', lvl: 0, text: '' });
  if (h1s.length > 1) h1s.slice(1).forEach(o => findings.push({ k: 'H1_COKLU', ...o }));

  let prev = null;
  for (const o of outline) {
    if (o.lvl === 0) { findings.push({ k: 'SEVIYESIZ', ...o }); continue; }
    if (!o.text) findings.push({ k: 'BOS', ...o });
    if (prev !== null && o.lvl > prev + 1) {
      findings.push({ k: 'ATLAMA', ...o, from: prev });
    }
    prev = o.lvl;
  }

  // AYRI SINIF — muğlak (aynı seviye + aynı metin)
  const seen = new Map(); const ambiguous = [];
  for (const o of outline) {
    if (!o.text) continue;
    const key = o.lvl + '|' + o.text.toLowerCase();
    if (seen.has(key)) ambiguous.push({ ...o, dup: seen.get(key) });
    else seen.set(key, o.el);
  }

  return { scanned, hiddenCnt, outline, findings, ambiguous };
};

(async () => {
  const pages = ONLY ? ONLY.split(',') : PAGES;
  const browser = await chromium.launch();
  const report = [];
  let totalF = 0, totalA = 0, totalHeadings = 0, errors = 0;
  const byKind = {};

  for (const w of WIDTHS) {
    const ctx = await browser.newContext({ viewport: { width: w, height: 900 } });
    const page = await ctx.newPage();
    for (const p of pages) {
      let res;
      try {
        res = await page.goto(BASE + p, { waitUntil: 'networkidle', timeout: 45000 });
      } catch (e) {
        console.log(`ERROR  ${w}px ${p} — ${e.message.slice(0, 80)}`); errors++; continue;
      }
      const st = res ? res.status() : 0;
      if (st >= 400 && !EXPECT_4XX.has(p)) {
        console.log(`ERROR  ${w}px ${p} — HTTP ${st} (ölü rota = kapsam yalanı)`); errors++; continue;
      }
      await page.waitForTimeout(1800);

      // sekme varyantları: her panel AYRI bir belge anahattı üretir (K-T dersi)
      const variants = [{ tab: null }];
      if (TABS) {
        const tabs = await page.$$eval('[role="tab"]', els =>
          els.map((e, i) => ({ i, name: (e.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 24) })));
        for (const t of tabs) variants.push({ tab: t });
      }

      for (const v of variants) {
        if (v.tab) {
          try {
            await page.$$eval('[role="tab"]', (els, i) => els[i] && els[i].click(), v.tab.i);
            await page.waitForTimeout(700);
          } catch (e) { /* sekme tıklanamadı; yine de ölç */ }
        }
        let r;
        try {
          r = await page.evaluate(PROBE, { kill: KILL_FIX });
        } catch (e) {
          console.log(`ERROR  ${w}px ${p} — probe: ${e.message.slice(0, 80)}`); errors++; continue;
        }
        const lbl = v.tab ? `${p} «${v.tab.name}»` : p;
        totalF += r.findings.length; totalA += r.ambiguous.length; totalHeadings += r.outline.length;
        for (const f of r.findings) byKind[f.k] = (byKind[f.k] || 0) + 1;
        report.push({ w, p: lbl, ...r });
        const flag = r.findings.length ? 'FAIL' : 'OK  ';
        console.log(`${flag}  ${w}px ${lbl}  bulgu=${r.findings.length} muglak=${r.ambiguous.length} (agacta=${r.outline.length}, gizli=${r.hiddenCnt}, dom=${r.scanned})`);
        for (const f of r.findings.slice(0, 10)) {
          const extra = f.k === 'ATLAMA' ? ` (h${f.from} → h${f.lvl})` : '';
          console.log(`        · ${f.k}${extra}  ${f.el}  "${String(f.text).slice(0, 60)}"`);
        }
        if (v.tab) { /* sonraki varyant için sayfa yeniden yüklenmez; sekme durumu kalıcı */ }
      }
    }
    await ctx.close();
  }
  await browser.close();
  const kinds = Object.entries(byKind).map(([k, n]) => `${k}=${n}`).join(' ') || '(yok)';
  console.log(`\n=== K-AM TOPLAM: bulgu=${totalF} [${kinds}]  muglak=${totalA}  olculen-baslik=${totalHeadings}  hata=${errors} ===`);
  if (JSON_OUT) require('fs').writeFileSync(JSON_OUT, JSON.stringify(report, null, 2));
  process.exit(totalF > 0 || errors > 0 ? 1 : 0);
})();
