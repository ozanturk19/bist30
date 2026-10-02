#!/usr/bin/env node
// tools/link-purpose-check.js — K-AS: BAĞLANTI AMACI & TUTARLI TANIMLAMA
// WCAG 2.1 · SC 2.4.4 "Link Purpose (In Context)" (A)
//            SC 3.2.4 "Consistent Identification" (AA)
//            SC 4.1.2 (adsız bağlantı = rolü var, adı yok)
//
// SORU — 30+ tur ARIA/kontrast/odak ölçtük, "KULLANICI BU BAĞLANTININ NEREYE
//   GİTTİĞİNİ ANLIYOR MU?" diye hiç sormadık. Ekran okuyucu kullanıcısı
//   bağlantı listesini (NVDA: INSERT+F7) açtığında SADECE erişilebilir adları
//   görür — sayfa gövdesini değil. O listede beş tane "Detay" varsa sayfa
//   kullanılamaz. Bu, hiçbir kontrast/ARIA dedektörünün göremediği bir sınıf.
//
// BULGU SINIFLARI:
//   A) ADSIZ BAĞLANTI      — erişilebilir ad BOŞ. Ekran okuyucu href'i harf
//                            harf okur. Taban SIFIR.
//   B) JENERİK AD, BAĞLAMSIZ — adı sözlükteki jenerik kalıplardan biri VE
//                            programatik bağlamında (en yakın li/td/tr/article/
//                            figure/[role=listitem]) ayırt edici başka metin YOK.
//                            Taban SIFIR.
//   C) AYNI AD → FARKLI HEDEF — aynı sayfada aynı erişilebilir ada sahip iki
//                            bağlantı farklı yere gidiyor. Bağlantı listesinde
//                            ayırt EDİLEMEZ. Taban SIFIR.
//   D) AYNI HEDEF → FARKLI AD (yalnız SİTE KABUĞU: header/nav/footer) —
//                            SC 3.2.4. Kabukta aynı sayfaya giden bağlantı
//                            sayfadan sayfaya başka adla anılıyorsa kullanıcı
//                            iki ayrı yer sanır. Taban SIFIR.
//   E) target=_blank + rel eksik — `noopener` yoksa açılan sekme
//                            `window.opener` ile kaynağı yönlendirebilir.
//                            Taban SIFIR (güvenlik; a11y değil, ayrı sayılır).
//
// ⛔ ELEME GEREKÇELERİ (bulgu DEĞİL — gerekçe bilginin TAMAMINI kapsamalı):
//   1. D ekseni BİLEREK yalnız kabukla sınırlı. Gövdede aynı hedefin farklı
//      adla anılması MEŞRUDUR: `/hisse/ASELS` bir yerde "ASELS", başka yerde
//      "Aselsan" olabilir — SC 3.2.4 "aynı İŞLEVİ gören bileşenler" der,
//      aynı hedefe giden her metin değil. Gövde farkları AYRI raporlanır
//      (gürültü katmanı), bulgu sayılmaz.
//   2. B ekseninde bağlam İSTİSNASI spec'in kendisidir: SC 2.4.4 "in context"
//      A seviyesidir — bağlam varsa GEÇER. Bağlamlı jenerikler ayrı sayılır
//      (yalnız SC 2.4.9 AAA'yı kaçırır) ve bulgu DEĞİLDİR.
//   3. `aria-hidden="true"` altındaki bağlantı ekran okuyucuda YOKTUR; ama
//      klavyeyle odaklanabiliyorsa AYRI bir kusurdur → ayrı sayılır.
//   4. Türkçe küçültme: `toLocaleLowerCase('tr')` ZORUNLU. Düz `.toLowerCase()`
//      "İ" için i+U+0307 (iki kod noktası) üretir → "İncele" sözlükte eşleşmez.
//      [[reference_python_turkce_i_lower_iki_kod_noktasi]] (JS'te de aynı tuzak)
//
// KULLANIM:
//   node tools/link-purpose-check.js [--base=URL] [--only=/a,/b] [--json=f]
//        [--interact]   → açılır katmanları açar (gizli bağlantılar da ölçülür)
//        [--kill-fix]   → POZİTİF KONTROL: ilk 8 bağlantının adını siler/kopyalar

const { chromium } = require('playwright');

const BASE = (process.argv.find(a => a.startsWith('--base=')) || '').split('=')[1] || 'https://borsapusula.com';
const ONLY = (process.argv.find(a => a.startsWith('--only=')) || '').split('=')[1] || '';
const JSON_OUT = (process.argv.find(a => a.startsWith('--json=')) || '').split('=')[1] || '';
const INTERACT = process.argv.includes('--interact');
const KILL_FIX = process.argv.includes('--kill-fix');

const PAGES = [
  '/', '/ozet', '/tarama', '/gundem', '/hisseler', '/sektor-harita',
  '/hisse/ASELS', '/hisse/GARAN', '/karsilastir', '/portfolio',
  '/takvim', '/blog', '/blog/rsi-gostergesi-nedir',
  '/metodoloji', '/hakkinda', '/iletisim', '/profil', '/yasal', '/gizlilik',
];

async function openLayers(page) {
  await page.evaluate(() => {
    document.querySelectorAll('[aria-expanded="false"], details:not([open])').forEach(el => {
      try { if (el.tagName === 'DETAILS') el.open = true; else el.click(); } catch (e) {}
    });
  });
  await page.waitForTimeout(600);
}

async function scan(page) {
  return page.evaluate(() => {
    const TR = s => (s || '').toLocaleLowerCase('tr');
    const norm = s => (s || '').replace(/\s+/g, ' ').trim();

    // Erişilebilir ad — spec sırası: aria-labelledby > aria-label > içerik > title
    const nameOf = (el) => {
      const lb = el.getAttribute('aria-labelledby');
      if (lb) {
        const parts = lb.trim().split(/\s+/).map(id => {
          const t = document.getElementById(id);
          return t ? norm(t.textContent) : '';
        }).filter(Boolean);
        if (parts.length) return norm(parts.join(' '));
      }
      const al = el.getAttribute('aria-label');
      if (norm(al)) return norm(al);
      // içerik: metin + img[alt] + svg>title
      let txt = '';
      const walk = (n) => {
        for (const c of n.childNodes) {
          if (c.nodeType === 3) txt += c.nodeValue;
          else if (c.nodeType === 1) {
            if (c.getAttribute && c.getAttribute('aria-hidden') === 'true') continue;
            if (c.tagName === 'IMG') txt += ' ' + (c.getAttribute('alt') || '');
            else if (c.tagName === 'svg') {
              const t = c.querySelector('title');
              txt += ' ' + (t ? t.textContent : (c.getAttribute('aria-label') || ''));
            } else walk(c);
          }
        }
      };
      walk(el);
      if (norm(txt)) return norm(txt);
      return norm(el.getAttribute('title'));
    };

    const GENERIC = new Set([
      'detay', 'detaylar', 'detayı gör', 'detaya git', 'devam', 'devamı',
      'devamını oku', 'tümü', 'tümünü gör', 'hepsi', 'daha fazla',
      'daha fazlası', 'buraya', 'buraya tıklayın', 'tıklayın', 'tıkla',
      'git', 'oku', 'incele', 'bak', 'gör', 'link', 'bağlantı', 'aç',
      'more', 'read more', 'click here', 'here', 'link here', 'view',
      '→', '»', '>>', '›', '>', '+', '...', '…',
    ]);

    const SHELL = 'header, nav, footer, [role="navigation"], [role="banner"], [role="contentinfo"]';

    const abs = (h) => { try { return new URL(h, location.href).href.replace(/\/$/, ''); } catch (e) { return h; } };

    const out = [];
    document.querySelectorAll('a[href], [role="link"][href], [role="link"]').forEach(el => {
      const href = el.getAttribute('href') || '';
      if (/^(javascript:|#$)/i.test(href)) return;
      const name = nameOf(el);
      const ariaHidden = !!el.closest('[aria-hidden="true"]');
      const focusable = el.tabIndex >= 0;
      const inShell = !!el.closest(SHELL);
      const r = el.getBoundingClientRect();
      // programatik bağlam: linkin kendi adı DIŞINDA ayırt edici metin
      const ctxEl = el.closest('li, td, th, tr, article, figure, [role="listitem"], [role="row"], .card, .bp-card, .da-panel');
      let ctxText = '';
      if (ctxEl) {
        const clone = ctxEl.cloneNode(true);
        clone.querySelectorAll('a[href]').forEach(a => a.remove());
        ctxText = norm(clone.textContent);
      }
      out.push({
        href, abs: abs(href), name, low: TR(name),
        ariaHidden, focusable, inShell,
        hasCtx: ctxText.length >= 3,
        ctx: ctxText.slice(0, 60),
        blank: el.getAttribute('target') === '_blank',
        rel: TR(el.getAttribute('rel') || ''),
        external: /^https?:/i.test(href) && !abs(href).startsWith(location.origin),
        visible: r.width > 0 && r.height > 0,
        sel: el.tagName.toLowerCase() + (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\s+/).slice(0, 2).join('.') : ''),
        generic: GENERIC.has(TR(name)),
      });
    });
    return out;
  });
}

async function run() {
  const browser = await chromium.launch();
  const pages = ONLY ? ONLY.split(',') : PAGES;
  const report = [];
  const shellMap = new Map();   // abs -> Map(name -> [pages])
  const bodyMap = new Map();
  let tot = { links: 0, A: 0, B: 0, Bctx: 0, C: 0, E: 0, hidFocus: 0 };

  for (const path of pages) {
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    const page = await ctx.newPage();
    try {
      const resp = await page.goto(BASE + path, { waitUntil: 'networkidle', timeout: 45000 });
      const status = resp ? resp.status() : 0;
      if (status >= 400) { console.log(`  !! ${path} → HTTP ${status}`); await ctx.close(); continue; }
      await page.waitForTimeout(900);
      if (INTERACT) await openLayers(page);
      if (KILL_FIX) {
        await page.evaluate(() => {
          const as = [...document.querySelectorAll('a[href]')].filter(a => a.textContent.trim());
          as.slice(0, 4).forEach(a => { a.setAttribute('aria-label', ''); a.textContent = ''; a.querySelectorAll('*').forEach(c => c.remove()); });
          as.slice(4, 8).forEach(a => { a.setAttribute('aria-label', 'Detay'); });
        });
        await page.waitForTimeout(200);
      }

      const links = await scan(page);
      tot.links += links.length;
      const findings = [];

      // A) adsız
      for (const l of links) {
        if (l.ariaHidden) { if (l.focusable && l.visible) { tot.hidFocus++; findings.push({ ax: 'H', ...l }); } continue; }
        if (!l.name) { tot.A++; findings.push({ ax: 'A', ...l }); }
        else if (l.generic) {
          if (l.hasCtx) tot.Bctx++;
          else { tot.B++; findings.push({ ax: 'B', ...l }); }
        }
        if (l.blank && !/noopener|noreferrer/.test(l.rel)) { tot.E++; findings.push({ ax: 'E', ...l }); }
      }

      // C) aynı ad → farklı hedef (aynı sayfa)
      const byName = new Map();
      for (const l of links) {
        if (!l.name || l.ariaHidden) continue;
        if (!byName.has(l.low)) byName.set(l.low, new Set());
        byName.get(l.low).add(l.abs);
      }
      for (const [n, hrefs] of byName) {
        if (hrefs.size > 1) { tot.C++; findings.push({ ax: 'C', name: n, targets: [...hrefs] }); }
      }

      // D verisi topla
      for (const l of links) {
        if (!l.name || l.ariaHidden) continue;
        const m = l.inShell ? shellMap : bodyMap;
        if (!m.has(l.abs)) m.set(l.abs, new Map());
        const nm = m.get(l.abs);
        if (!nm.has(l.name)) nm.set(l.name, []);
        nm.get(l.name).push(path);
      }

      report.push({ path, links: links.length, findings });
      const bad = findings.filter(f => f.ax !== 'H').length;
      console.log(`  ${bad ? '✗' : '✓'} ${path.padEnd(28)} ${String(links.length).padStart(4)} bağlantı  ${bad ? bad + ' bulgu' : ''}`);
      for (const f of findings) {
        if (f.ax === 'C') console.log(`      [C] "${f.name}" → ${f.targets.length} FARKLI hedef: ${f.targets.map(t => t.replace(BASE, '')).join(' | ')}`);
        else if (f.ax === 'A') console.log(`      [A] ADSIZ  ${f.sel}  href=${f.href}`);
        else if (f.ax === 'B') console.log(`      [B] JENERİK "${f.name}"  href=${f.href}  (bağlam YOK)`);
        else if (f.ax === 'E') console.log(`      [E] _blank rel="${f.rel}"  href=${f.href}`);
        else if (f.ax === 'H') console.log(`      [H] aria-hidden AMA odaklanabilir  ${f.sel} href=${f.href}`);
      }
    } catch (e) {
      console.log(`  !! ${path} → ${e.message.split('\n')[0]}`);
    }
    await ctx.close();
  }

  // D) kabukta aynı hedef → farklı ad
  const D = [];
  for (const [abs, nm] of shellMap) {
    if (nm.size > 1) D.push({ abs, names: [...nm.entries()].map(([n, ps]) => ({ n, pages: ps.length })) });
  }
  const Dbody = [];
  for (const [abs, nm] of bodyMap) {
    if (nm.size > 1) Dbody.push({ abs, names: [...nm.keys()] });
  }

  console.log('\n──────── K-AS ÖZET ────────');
  console.log(`  taranan bağlantı : ${tot.links}`);
  console.log(`  A) ADSIZ                    : ${tot.A}`);
  console.log(`  B) JENERİK + bağlamsız      : ${tot.B}   (bağlamlı, bulgu DEĞİL: ${tot.Bctx})`);
  console.log(`  C) aynı ad → farklı hedef   : ${tot.C}`);
  console.log(`  D) KABUKTA aynı hedef→çok ad: ${D.length}`);
  console.log(`  E) _blank rel eksik         : ${tot.E}`);
  console.log(`  H) aria-hidden+odaklanabilir: ${tot.hidFocus}`);
  for (const d of D) console.log(`      [D] ${d.abs.replace(BASE, '') || '/'} → ${d.names.map(x => `"${x.n}"(${x.pages})`).join(' vs ')}`);
  console.log(`  (gürültü katmanı — gövdede aynı hedef farklı ad, bulgu DEĞİL: ${Dbody.length})`);

  if (JSON_OUT) require('fs').writeFileSync(JSON_OUT, JSON.stringify({ tot, report, D, Dbody }, null, 2));
  await browser.close();
  const fail = tot.A + tot.B + tot.C + D.length + tot.E;
  process.exit(fail ? 1 : 0);
}
run();
