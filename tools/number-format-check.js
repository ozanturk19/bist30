#!/usr/bin/env node
// tools/number-format-check.js — K-AN: SAYI & BİRİM BİÇİMİ TUTARLILIĞI (CANLI)
//
// SORU — bu sitede daha önce CANLI olarak hiç sorulmadı:
//   BorsaPusula bir FİNANS sitesidir; kullanıcının gördüğü hemen her şey bir
//   sayıdır. Aynı sayfada "1.234,56" ile "1,234.56", "%3,40" ile "3.40%",
//   "×1,24" ile "1,24x", "₺12,50" ile "12,50 TL" yan yana duruyorsa bu bir
//   üslup meselesi değil — TR biçiminde "1,234" BİN İKİ YÜZ OTUZ DÖRT değil
//   BİR TAM İKİ YÜZ OTUZ DÖRT'tür. Okuyucu sayıyı 1000 kat yanlış okur.
//
// ⛔ NEDEN CANLI: `tools/format-lint.sh` (K6) aynı sınıfı ŞABLONDA tarar.
//   Ama kullanıcıya giden sayıların çoğu JS ile basılır (toLocaleString,
//   elle string birleştirme) — şablonda HİÇ GÖRÜNMEZ.
//   [[feedback_client_side_render_grep_kor]]  Bu dedektör DOM'u ölçer.
//
// ⛔ TARİH/SAAT TUZAĞI: "21.09.2026" ve "19:00" sayı gibi görünür ama biçim
//   ekseni farklıdır. Önce maskelenir; maskelenmezse her sayfada sahte
//   "EN binlik ayracı" bulgusu üretirler.
//
// ⛔ GİZLİ SEKMELER: /hisse panelleri hidden'dır; --tabs ile tek tek açılır
//   (K-T dersi). Grafik / AI Analiz panelleri sayının EN YOĞUN olduğu yer.
//
// ⛔ K-T DERSİNİN BİR ALT KATI — AÇILIR KUTULAR: sekmeyi açmak YETMEZ.
//   /hisse «Özet» panelinin içinde KAPALI bir <details> ve onun içinde de
//   display:none bir "Detay" gövdesi var. İlk ölçümüm D1'i "tek sınıf
//   TR_ONDALIK" ilan etti; oysa o gövdede canlı "EMA12: 130.4" duruyordu.
//   Görünürlük kapısı DOĞRU çalışıyordu — ölçülmeyen yüzey kapsam yalanıdır.
//   --expand tüm <details>'leri açar ve [aria-expanded=false] düğmelerine
//   basar. [[reference_dedektor_ust_siniri_kapsam_yalani]]
//
// BOYUTLAR (her biri bağımsız; taban = sayfa başına TEK sınıf):
//   D1 ONDALIK   TR_ONDALIK (3,40)        ⟷ EN_ONDALIK (3.40)
//   D2 BINLIK    TR_BINLIK (1.234)        ⟷ EN_BINLIK (1,234)
//   D3 YUZDE     ONEK (%3,40)             ⟷ SONEK (3,40%)
//   D4 CARPAN    ONEK (×1,24)             ⟷ SONEK (1,24x)
//   D5 PARA      ONEK (₺12,50)            ⟷ SONEK (12,50 ₺) ⟷ TL (12,50 TL)
//   D6 KISALTMA  Mn / Mr / M / B / K / bin / milyon / milyar ...
//
// BULGU = bir boyutta aynı yüzeyde (sayfa+genişlik) BİRDEN FAZLA sınıf.
// Ayrıca SITE geneli çarpışma ayrı raporlanır (sayfalar arası tutarsızlık).
//
// POZİTİF KONTROL (--kill-fix): gerçek metin düğümlerinde ilk 6 TR ondalık
//   "," → "." çevrilir. D1 ÇARPIŞMASI FIRLAMALI; fırlamıyorsa yürüyücü
//   gerçek içeriği görmüyor demektir. [[feedback_positif_kontrol_checkout_commit_once]]
//
// Kullanım: node tools/number-format-check.js [--base=...] [--w=375,1280]
//           [--only=/a,/b] [--tabs] [--expand] [--kill-fix] [--json=dosya] [--cap=N]
const { chromium } = require('playwright');

const BASE = (process.argv.find(a => a.startsWith('--base=')) || '').split('=')[1] || 'https://borsapusula.com';
const WIDTHS = ((process.argv.find(a => a.startsWith('--w=')) || '').split('=')[1] || '375,1280')
  .split(',').map(s => parseInt(s, 10)).filter(Boolean);
const ONLY = (process.argv.find(a => a.startsWith('--only=')) || '').split('=')[1] || '';
const JSON_OUT = (process.argv.find(a => a.startsWith('--json=')) || '').split('=')[1] || '';
const CAP = parseInt(((process.argv.find(a => a.startsWith('--cap=')) || '').split('=')[1] || '40'), 10);
const KILL_FIX = process.argv.includes('--kill-fix');
const TABS = process.argv.includes('--tabs');
const EXPAND = process.argv.includes('--expand');

// color-only / heading-outline / title-tooltip / focus-obscured ile AYNI envanter
const PAGES = [
  '/', '/ozet', '/tarama', '/gundem', '/hisseler', '/sektor-harita',
  '/hisse/ASELS', '/hisse/GARAN', '/karsilastir', '/portfolio',
  '/bilanco-takvimi', '/temettu-takvimi', '/blog', '/blog/rsi-gostergesi-nedir',
  '/metodoloji', '/hakkinda', '/iletisim', '/profil', '/yasal', '/gizlilik',
];
const EXPECT_4XX = new Set(['/profil']);

const EXPAND_ALL = () => {
  let opened = 0;
  // ⛔ İLK SÜRÜM SADECE <details> + [aria-expanded=false] AÇIYORDU ve
  //   /hisse'nin "Detaylı göster ▾" düğmesini KAÇIRDI: o düğmede
  //   aria-expanded YOK (kendi başına bir 4.1.2 kusuru) ve gövdeyi satır-içi
  //   style.display ile gizliyor. Açılmayan yüzey ÖLÇÜLMEMİŞ yüzeydir.
  const looksDisclosure = (el) => {
    const oc = (el.getAttribute('onclick') || '');
    if (/toggle|detay|expand|ac(ik)?|goster/i.test(oc) && !/portfolio|watch|fav|bildirim|theme|menu|modal/i.test(oc)) return true;
    const tx = (el.textContent || '').trim();
    return /^(detayl[ıi]|detay|ayr[ıi]nt[ıi]|daha fazla|t[üu]m[üu]n[üu])/i.test(tx);
  };
  for (let pass = 0; pass < 3; pass++) {
    document.querySelectorAll('details:not([open])').forEach(d => { d.open = true; opened++; });
    document.querySelectorAll('[aria-expanded="false"]').forEach(b => {
      try { b.click(); opened++; } catch (e) { /* tıklanamayan düğme */ }
    });
    document.querySelectorAll('button,[role="button"]').forEach(b => {
      if (!looksDisclosure(b)) return;
      try { b.click(); opened++; } catch (e) { /* tıklanamayan düğme */ }
    });
  }
  return opened;
};

const PROBE = (opts) => {
  const KILL = opts.kill;

  // ── erişilebilirlik ağacında / görünür mü? ────────────────────────────
  const visible = (el) => {
    for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
      if (n.hasAttribute('hidden') || n.hasAttribute('inert')) return false;
      if (n.getAttribute('aria-hidden') === 'true') return false;
      const cs = getComputedStyle(n);
      if (cs.display === 'none' || cs.visibility === 'hidden') return false;
    }
    return true;
  };

  const sel = (el) => {
    if (!el) return '?';
    let s = el.tagName.toLowerCase();
    if (el.id) return s + '#' + el.id;
    const c = (typeof el.className === 'string' ? el.className : (el.getAttribute('class') || ''))
      .trim().split(/\s+/).filter(Boolean).slice(0, 2).join('.');
    return c ? s + '.' + c : s;
  };

  // ── metin düğümlerini topla ───────────────────────────────────────────
  const nodes = [];
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let t;
  while ((t = w.nextNode())) {
    const raw = t.nodeValue;
    if (!raw || !/\d/.test(raw)) continue;
    const el = t.parentElement;
    if (!el) continue;
    const tag = el.tagName;
    if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'NOSCRIPT') continue;
    if (!visible(el)) continue;
    nodes.push({ node: t, el });
  }

  // ── POZİTİF KONTROL: gerçek içerikte TR ondalığı EN'e çevir ───────────
  let killed = 0;
  if (KILL) {
    for (const n of nodes) {
      if (killed >= 6) break;
      const v = n.node.nodeValue;
      if (/\d,\d/.test(v)) { n.node.nodeValue = v.replace(/(\d),(\d)/g, '$1.$2'); killed++; }
    }
  }

  // ── maskeleme: tarih / saat / sürüm / ticker-sayı ─────────────────────
  const mask = (s) => s
    .replace(/\b\d{1,2}[./]\d{1,2}[./]\d{2,4}\b/g, ' ')      // 21.09.2026 · 21/09/26
    .replace(/\b\d{4}-\d{2}-\d{2}\b/g, ' ')                   // ISO
    .replace(/\b\d{1,2}:\d{2}(:\d{2})?\b/g, ' ')              // 19:00
    .replace(/\bv?\d+\.\d+\.\d+\b/g, ' ')                     // sürüm
    // ⛔ İLK SÜRÜM BURADA `\d{1,2}.\d{1,2}` MASKELİYORDU — yani "48.3" (RSI),
    //   "18.6" (ADX), "62.9" (radar ekseni) gibi GERÇEK EN-ondalıkların tamamı
    //   "gün.ay sanıldı" diye sessizce siliniyordu. Dedektörün kendi kapısı
    //   aranan kusur sınıfının yarısını eliyordu (K-AM dersinin aynısı).
    //   Tarih maskesi artık SIFIR-DOLGULU gün.ay ister: "17.09" ✓, "48.3" ✗.
    .replace(/\b(?:0[1-9]|[12]\d|3[01])\.(?:0[1-9]|1[0-2])\b(?!\d)/g, ' ');

  const dims = {
    D1_ONDALIK: {}, D2_BINLIK: {}, D3_YUZDE: {},
    D4_CARPAN: {}, D5_PARA: {}, D6_KISALTMA: {},
  };
  const push = (d, cls, txt, el) => {
    const b = dims[d];
    if (!b[cls]) b[cls] = { n: 0, ex: [] };
    b[cls].n++;
    if (b[cls].ex.length < 4) b[cls].ex.push({ t: txt.slice(0, 40), el: sel(el) });
  };

  let scanned = 0;
  for (const n of nodes) {
    const s = mask(n.node.nodeValue.replace(/ /g, ' '));
    if (!/\d/.test(s)) continue;
    scanned++;
    const el = n.el;

    // D2 BİNLİK — önce, çünkü ondalık sınıflandırmasını yanıltır
    let m;
    const reTRk = /\b\d{1,3}(?:\.\d{3})+(?:,\d+)?\b/g;
    while ((m = reTRk.exec(s))) push('D2_BINLIK', 'TR_BINLIK', m[0], el);
    // ⛔ "1,805 ₺/hisse" TUZAĞI: TEK gruplu `\d{1,3},\d{3}` biçimsel olarak
    //   AYIRT EDİLEMEZ — TR'de 3 ondalıklı bir sayı ("1,805" = bir tam
    //   sekiz yüz beş binde), EN'de binlik ("1805"). İlk sürüm bunu
    //   EN_BINLIK sayıp /temettu-takvimi'nde 3 SAHTE bulgu üretti.
    //   Kesin kanıt ancak ≥2 grup ("1,234,567") ya da ardından nokta-ondalık
    //   ("1,234.56") gelmesidir. Tek grup ondalık regex'ine bırakılır.
    const reENk = /\b\d{1,3}(?:,\d{3}){2,}(?:\.\d+)?\b|\b\d{1,3}(?:,\d{3})+\.\d+\b/g;
    while ((m = reENk.exec(s))) push('D2_BINLIK', 'EN_BINLIK', m[0], el);

    // binlik eşleşmelerini çıkar, kalan ondalıkları sınıflandır
    const rest = s.replace(reTRk, ' ').replace(reENk, ' ');

    // D1 ONDALIK
    const reTRd = /(?<![\d.,])\d{1,4},\d{1,4}(?![\d.,])/g;
    while ((m = reTRd.exec(rest))) push('D1_ONDALIK', 'TR_ONDALIK', m[0], el);
    const reENd = /(?<![\d.,])\d{1,4}\.\d{1,4}(?![\d.,])/g;
    while ((m = reENd.exec(rest))) push('D1_ONDALIK', 'EN_ONDALIK', m[0], el);

    // D3 YÜZDE
    const rePre = /%\s?[+\-−]?\d/g;
    while ((m = rePre.exec(s))) push('D3_YUZDE', 'ONEK', m[0], el);
    const reSuf = /\d\s?%/g;
    while ((m = reSuf.exec(s))) push('D3_YUZDE', 'SONEK', m[0], el);

    // D4 ÇARPAN — ⛔ "Toplam × 100" bir ÇARPMA OPERATÖRÜDÜR, çarpan biçimi
    //   değildir: boşluklu ve ondalıksız "× 100" elenir, "×1,24" kalır.
    const reMp = /[×x](?:\s?\d+[.,]\d+|\d+(?:[.,]\d+)?)/g;
    while ((m = reMp.exec(s))) push('D4_CARPAN', 'ONEK', m[0], el);
    const reMs = /\d(?:[.,]\d+)?\s?[×x](?![a-zA-Z0-9])/g;
    while ((m = reMs.exec(s))) push('D4_CARPAN', 'SONEK', m[0], el);

    // D5 PARA
    const reCp = /[₺$€]\s?\d/g;
    while ((m = reCp.exec(s))) push('D5_PARA', m[0][0] === '₺' ? 'TL_ONEK' : 'DOVIZ_ONEK', m[0], el);
    const reCs = /\d\s?₺/g;
    while ((m = reCs.exec(s))) push('D5_PARA', 'TL_SONEK', m[0], el);
    const reTL = /\d\s?TL\b/g;
    while ((m = reTL.exec(s))) push('D5_PARA', 'TL_HARF', m[0], el);

    // D6 KISALTMA — sayıdan hemen sonraki büyüklük eki
    const reAb = /\d\s?(Mn|mn|Mr|mr|Milyon|milyon|Milyar|milyar|Bin|bin|[MBKmk])\b/g;
    while ((m = reAb.exec(s))) push('D6_KISALTMA', m[1], m[0], el);
  }

  // ── çarpışmalar ───────────────────────────────────────────────────────
  const findings = [];
  for (const d of Object.keys(dims)) {
    const classes = Object.keys(dims[d]);
    if (classes.length > 1) {
      findings.push({
        d,
        classes: classes.map(c => ({ c, n: dims[d][c].n, ex: dims[d][c].ex })),
      });
    }
  }
  return { findings, dims, scanned, nodeCnt: nodes.length, killed };
};

(async () => {
  const pages = ONLY ? ONLY.split(',') : PAGES;
  const browser = await chromium.launch();
  const report = [];
  const siteWide = {};
  let totalF = 0, errors = 0, totalScanned = 0;

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
            await page.waitForTimeout(800);
          } catch (e) { /* sekme tıklanamadı; yine de ölç */ }
        }
        let expanded = 0;
        if (EXPAND) {
          try {
            expanded = await page.evaluate(EXPAND_ALL);
            await page.waitForTimeout(900);
          } catch (e) { /* açılamadı; yine de ölç */ }
        }
        let r;
        try { r = await page.evaluate(PROBE, { kill: KILL_FIX }); }
        catch (e) { console.log(`ERROR  ${w}px ${p} — probe: ${e.message.slice(0, 90)}`); errors++; continue; }

        const lbl = v.tab ? `${p} «${v.tab.name}»` : p;
        totalF += r.findings.length; totalScanned += r.scanned;
        for (const d of Object.keys(r.dims)) {
          if (!siteWide[d]) siteWide[d] = {};
          for (const c of Object.keys(r.dims[d])) {
            if (!siteWide[d][c]) siteWide[d][c] = { n: 0, pages: new Set(), ex: [] };
            siteWide[d][c].n += r.dims[d][c].n;
            siteWide[d][c].pages.add(lbl);
            for (const e of r.dims[d][c].ex) if (siteWide[d][c].ex.length < 4) siteWide[d][c].ex.push(e);
          }
        }
        report.push({ w, p: lbl, findings: r.findings, dims: r.dims, scanned: r.scanned, killed: r.killed });
        const flag = r.findings.length ? 'FAIL' : 'OK  ';
        console.log(`${flag}  ${w}px ${lbl}  carpisma=${r.findings.length} (sayili dugum=${r.scanned}/${r.nodeCnt}${EXPAND ? `, acildi=${expanded}` : ''}${KILL_FIX ? `, kill=${r.killed}` : ''})`);
        for (const f of r.findings.slice(0, CAP)) {
          console.log(`        · ${f.d}: ` + f.classes.map(c => `${c.c}×${c.n}`).join('  ⟷  '));
          for (const c of f.classes) {
            const e = c.ex[0];
            if (e) console.log(`             ${c.c.padEnd(12)} "${e.t}"  @${e.el}`);
          }
        }
      }
    }
    await ctx.close();
  }
  await browser.close();

  console.log('\n=== SİTE GENELİ BOYUT DAĞILIMI ===');
  let siteF = 0;
  for (const d of Object.keys(siteWide)) {
    const cls = Object.keys(siteWide[d]);
    if (!cls.length) continue;
    const collide = cls.length > 1;
    if (collide) siteF++;
    console.log(`${collide ? 'ÇARPIŞMA' : 'tek sınıf'}  ${d}`);
    for (const c of cls.sort((a, b) => siteWide[d][b].n - siteWide[d][a].n)) {
      const o = siteWide[d][c];
      console.log(`    ${c.padEnd(12)} ${String(o.n).padStart(5)}×  ${o.pages.size} yüzey  ör: "${o.ex[0] ? o.ex[0].t : ''}" @${o.ex[0] ? o.ex[0].el : ''}`);
      if (o.pages.size <= 4) console.log(`                 yüzeyler: ${[...o.pages].join(', ')}`);
    }
  }

  console.log(`\nTOPLAM  sayfa-içi çarpışma=${totalF}  site-geneli çarpışan boyut=${siteF}  taranan düğüm=${totalScanned}  hata=${errors}`);
  if (JSON_OUT) {
    const fs = require('fs');
    const ser = {};
    for (const d of Object.keys(siteWide)) { ser[d] = {}; for (const c of Object.keys(siteWide[d])) ser[d][c] = { ...siteWide[d][c], pages: [...siteWide[d][c].pages] }; }
    fs.writeFileSync(JSON_OUT, JSON.stringify({ report, siteWide: ser, totalF, siteF, errors }, null, 2));
    console.log(`JSON → ${JSON_OUT}`);
  }
  process.exit(errors > 0 ? 2 : (totalF + siteF > 0 ? 1 : 0));
})();
