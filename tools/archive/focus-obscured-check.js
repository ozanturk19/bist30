#!/usr/bin/env node
// tools/focus-obscured-check.js — K-AG: KLAVYE ODAĞI YAPIŞKAN BANTLARIN ALTINDA KAYBOLUYOR MU?
// WCAG 2.2 · SC 2.4.11 "Focus Not Obscured (Minimum)" (AA) — odaklanan bileşen
// yazar-kaynaklı içerikle TAMAMEN gizlenmemelidir. (2.4.12 AAA: hiç gizlenmemeli.)
//
// NEDEN AYRI BİR KAT — bu boyut şimdiye kadar HİÇ ÖLÇÜLMEDİ:
//   Odak GÖRÜNÜRLÜĞÜ (focus-visible-check.js) odak halkasının VAR olup olmadığını,
//   kontrastını ve kalınlığını ölçer. Bu betik bambaşka bir soruyu sorar:
//   halka çizildi, peki KULLANICI ONU GÖREBİLİYOR MU?
//
//   Sitenin neredeyse her sayfasında ÜST ÜSTE İKİ yapışkan bant var:
//     makro şerit (top:0, 32px + safe-area) + header (top:32px, ~60px)
//   /hisse'de ÜÇÜNCÜ bir tane daha (.bp-segments, top:92px) ve mobilde
//   ALTTA `position:fixed; bottom:0` navigasyon (shared.css:9).
//   Tarayıcı Tab'da odaklanan elemanı "en yakın kenara" kaydırır. Geriye
//   (Shift+Tab) giderken bu ÜST kenardır — eleman tam da bantların ALTINA
//   yerleşir. İleri giderken ALT kenardır — mobil alt navigasyonun ALTINA.
//
//   Kanonik çare `html{scroll-padding-top/bottom}`'dır ve repoda YOKTUR:
//   yalnızca birkaç elemanda noktasal `scroll-margin-top` var
//   (#main-content:70px, hisse.html'de 3 bölüm:80px) — yani düzeltme
//   ELEMAN ELEMAN yapılmış, KAPSAM yalanı.
//
// ÖLÇÜT (taban SIFIR) — bir bulgu ancak HEPSİ doğruysa:
//   1. Eleman gerçekten odaklanabilir ve görünür (boyut>0, opacity>.05,
//      disabled değil, inert/aria-hidden ata yok),
//   2. `el.focus()` sonrası eleman GÖRÜŞ ALANINA girdi (girmiyorsa ayrı
//      sayılır, bulgu sayılmaz — kapsam yalanı olmasın diye RAPORLANIR),
//   3. Eleman KENDİSİ yapışkan/sabit bir bandın içinde DEĞİL (kendi kendini
//      örtemez),
//   4. Kutusunun örtülen yüzdesi, elemanFromPoint ızgarasıyla ÖLÇÜLDÜ ve
//      örten eleman zincirinde `position: fixed|sticky` VAR.
//   4. koşul bu betiğin kendi sahte-pozitif kapısıdır: normal akışta üst üste
//   binen tasarım (açılır menü açıkken, modal içi) yapışkan bant DEĞİLDİR.
//
// ⛔ SİMÜLASYON DEĞİL: gerçek `el.focus()` çağrılır, tarayıcının KENDİ
//   "odağı görünüre kaydır" davranışı (scroll-padding'e saygı duyan) ölçülür.
//   CSS'ten `scroll-padding` okuyup "var/yok" demek iddiayı dedektörün kendi
//   kopyasından türetirdi (K-T dersi: tek kaynak CANLI davranış).
//
// İKİ YÖN ZORUNLU (K-AD dersi: tek koşul = kapsam yalanı):
//   ileri = sayfa başından DOM sırasıyla → eleman ALT kenara hizalanır,
//   geri  = sayfa sonundan TERS DOM sırasıyla → eleman ÜST kenara hizalanır.
//   Tek yön koşmak üst bantları TAMAMEN ıskalar.
//
// Kullanım: node tools/focus-obscured-check.js [--base=...] [--w=375,1280] [--only=/a,/b]
const { chromium } = require('playwright');

const BASE = (process.argv.find(a => a.startsWith('--base=')) || '').split('=')[1] || 'https://borsapusula.com';
const WIDTHS = ((process.argv.find(a => a.startsWith('--w=')) || '').split('=')[1] || '375,1280')
  .split(',').map(s => parseInt(s, 10)).filter(Boolean);
const ONLY = (process.argv.find(a => a.startsWith('--only=')) || '').split('=')[1] || '';

// reduced-motion / text-clip / text-spacing ile AYNI envanter
// (K-S dersi: ölü rota bir kapsam yalanıdır — ERROR olarak raporlanır).
const PAGES = [
  '/', '/ozet', '/tarama', '/gundem', '/hisseler', '/sektor-harita',
  '/hisse/ASELS', '/hisse/GARAN', '/karsilastir', '/portfolio',
  '/takvim', '/blog', '/blog/rsi-gostergesi-nedir',
  '/metodoloji', '/hakkinda', '/iletisim', '/profil', '/yasal', '/gizlilik',
];
const EXPECT_4XX = new Set(['/profil']);

// Sayfada tek seferde odaklanılacak eleman üst sınırı (uzun listelerde süre).
// ⛔ KAPSAM UYARISI (K-AD dersi): sınır aşıldığında ölçülmeyen eleman sayısı
//   RAPORLANIR — "OK" demek "hepsi ölçüldü" demek değildir. İleri geçiş DOM
//   sırasının BAŞINI, geri geçiş SONUNU örnekler; orta bölge sınır aşılan
//   sayfalarda ölçülmez. Tam kapsam için: --cap=99999 (yavaş).
const MAX_PER_PASS = parseInt((process.argv.find(a => a.startsWith('--cap=')) || '').split('=')[1] || '140', 10);

// POZİTİF KONTROL: fix'i sayfa içinde geri alır (html{scroll-padding:0}).
// Dedektörün kör olmadığını kanıtlamak için — ölçütü kendi kopyasından
// türetmez, K-AG öncesi GERÇEK durumu yeniden üretir.
const KILL_FIX = process.argv.includes('--kill-fix');

const PROBE = async ({ dir, cap }) => {
  const rAF2 = () => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));

  const desc = (el) => {
    if (!el) return '(yok)';
    const id = el.id ? '#' + el.id : '';
    const cls = (typeof el.className === 'string' && el.className.trim())
      ? '.' + el.className.trim().split(/\s+/).slice(0, 2).join('.') : '';
    return el.tagName.toLowerCase() + id + cls;
  };

  const label = (el) => {
    const t = (el.getAttribute('aria-label') || el.textContent || el.value || el.getAttribute('title') || '')
      .trim().replace(/\s+/g, ' ');
    return t.slice(0, 44) || desc(el);
  };

  // Zincirde yapışkan/sabit bir ata var mı? (hem örten hem örtülen için kullanılır)
  const stickyAncestor = (el) => {
    let p = el;
    while (p && p !== document.documentElement) {
      const cs = getComputedStyle(p);
      if (cs.position === 'fixed' || cs.position === 'sticky') return p;
      p = p.parentElement;
    }
    return null;
  };

  const visible = (el) => {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) <= 0.05) return false;
    if (el.closest('[aria-hidden="true"],[inert]')) return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };

  const SEL = 'a[href],button,input,select,textarea,summary,[tabindex],[contenteditable="true"]';
  let list = [...document.querySelectorAll(SEL)].filter(el => {
    if (el.disabled) return false;
    const ti = el.getAttribute('tabindex');
    if (ti !== null && parseInt(ti, 10) < 0) return false;
    if (el.tagName === 'A' && !el.getAttribute('href')) return false;
    if (el.type === 'hidden') return false;
    return visible(el);
  });

  if (dir === 'geri') list = list.reverse();
  const skippedForCap = Math.max(0, list.length - cap);
  const inventory = list.length;
  list = list.slice(0, cap);

  // Başlangıç konumu: ileri → sayfa başı (eleman ALT kenara hizalanır),
  // geri → sayfa sonu (eleman ÜST kenara hizalanır).
  window.scrollTo(0, dir === 'geri' ? document.documentElement.scrollHeight : 0);
  await rAF2();

  const out = [];
  let notScrolled = 0, focusRefused = 0;

  for (const el of list) {
    if (stickyAncestor(el)) continue;                    // koşul 3: kendi bandının içinde
    try { el.focus({ preventScroll: false }); } catch (_) { focusRefused++; continue; }
    if (document.activeElement !== el) { focusRefused++; continue; }
    await rAF2();

    const r = el.getBoundingClientRect();
    const vw = window.innerWidth, vh = window.innerHeight;
    const x0 = Math.max(0, r.left), x1 = Math.min(vw, r.right);
    const y0 = Math.max(0, r.top), y1 = Math.min(vh, r.bottom);
    if (x1 - x0 < 1 || y1 - y0 < 1) { notScrolled++; continue; }   // koşul 2

    // Izgara örnekleme — elemanFromPoint ile GERÇEK üst katman.
    const NX = 5, NY = 5;
    let total = 0, hidden = 0;
    const blockers = new Map();
    for (let i = 0; i < NX; i++) {
      for (let j = 0; j < NY; j++) {
        const px = x0 + ((i + 0.5) / NX) * (x1 - x0);
        const py = y0 + ((j + 0.5) / NY) * (y1 - y0);
        const hit = document.elementFromPoint(px, py);
        total++;
        if (!hit) { hidden++; continue; }
        if (hit === el || el.contains(hit) || hit.contains(el)) continue;
        const sa = stickyAncestor(hit);
        if (!sa) continue;                                // koşul 4 kapısı: yapışkan değilse bulgu DEĞİL
        hidden++;
        blockers.set(desc(sa), (blockers.get(desc(sa)) || 0) + 1);
      }
    }
    if (!hidden) continue;

    const pct = Math.round((hidden / total) * 100);
    out.push({
      node: desc(el),
      etiket: label(el),
      pct,
      tam: pct === 100,
      orten: [...blockers.keys()].join(' + ') || '(bilinmiyor)',
      kutu: `${Math.round(r.top)}..${Math.round(r.bottom)}`,
    });
  }
  return { out, notScrolled, focusRefused, skippedForCap, inventory };
};

(async () => {
  const pages = ONLY ? ONLY.split(',') : PAGES;
  const browser = await chromium.launch();
  let hard = 0, soft = 0, errors = 0;
  const report = [];

  for (const W of WIDTHS) {
    console.log(`\n───────────── @${W}px ─────────────`);
    const ctx = await browser.newContext({ viewport: { width: W, height: 900 } });
    const page = await ctx.newPage();

    for (const p of pages) {
      const url = BASE.replace(/\/$/, '') + p;
      let status = 0;
      try {
        const resp = await page.goto(url, { waitUntil: 'networkidle', timeout: 45000 });
        status = resp ? resp.status() : 0;
      } catch (e) {
        console.log(`ERROR ${p} — yüklenemedi: ${e.message.split('\n')[0]}`);
        errors++; continue;
      }
      if (status >= 400 && !EXPECT_4XX.has(p)) {
        console.log(`ERROR ${p} — HTTP ${status} (ölü rota; kapsam yalanı)`);
        errors++; continue;
      }

      if (KILL_FIX) {
        await page.addStyleTag({ content: 'html{scroll-padding-top:0 !important;scroll-padding-bottom:0 !important}' });
        await page.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))));
      }

      let pHard = 0, pSoft = 0, inv = 0, ns = 0;
      for (const dir of ['ileri', 'geri']) {
        const r = await page.evaluate(PROBE, { dir, cap: MAX_PER_PASS }).catch(e => ({ out: [], err: e.message }));
        inv = Math.max(inv, r.inventory || 0);
        ns += r.notScrolled || 0;
        for (const x of (r.out || [])) {
          if (x.tam) { hard++; pHard++; } else { soft++; pSoft++; }
          report.push({ page: p, w: W, dir, ...x });
        }
        if (r.skippedForCap) console.log(`      (not: ${p} ${dir} — ${r.skippedForCap} eleman üst sınır nedeniyle ölçülmedi)`);
      }

      const tag = pHard ? 'FAIL' : (pSoft ? 'WARN' : 'OK  ');
      console.log(`${tag} ${p}  ${inv} odaklanabilir` +
        (pHard ? ` · ${pHard} TAM ÖRTÜLÜ` : '') + (pSoft ? ` · ${pSoft} kısmen` : '') +
        (ns ? ` · ${ns} görünüre gelmedi` : ''));
      for (const x of report.filter(r => r.page === p && r.w === W).slice(-(pHard + pSoft))) {
        console.log(`      [${x.dir}] ${x.tam ? 'TAM' : x.pct + '%'} örtülü  ${x.node} "${x.etiket}"  ← ${x.orten}  (y ${x.kutu})`);
      }
    }
    await ctx.close();
  }

  await browser.close();
  if (KILL_FIX) console.log('\n⚠ POZİTİF KONTROL modu: fix sayfa içinde geri alındı (--kill-fix).');
  console.log(`\n=== K-AG özet: ${hard} TAM ÖRTÜLÜ (SC 2.4.11 AA ihlali) · ${soft} kısmen örtülü (SC 2.4.12 AAA) · ${errors} ERROR ===`);
  if (!hard && !soft && !errors) console.log('Klavye odağı hiçbir yapışkan bandın altında kaybolmuyor.');
  process.exit(errors || hard ? 2 : 0);
})();
