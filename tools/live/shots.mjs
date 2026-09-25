#!/usr/bin/env node
// C-05a — Canlı ölçüm altyapısı I: çekim (fold + kesit + __data.json), doğru CLS/LCP, piksel farkı, yan yana çekim.
// Kaynak: denetim 23.09 kanit/capture.js (K-00). Yeni npm paketi yok; fark ImageMagick `compare -metric AE`.
//
// Kullanım:
//   node tools/live/shots.mjs <ID> [--faz once|sonra] [--sayfa tarama,anasayfa] [--vp 1440,820,390,320] [--base URL]
//       → ~/ops/plans/shots/<ID>/<faz>/<sayfa>__<vp>__{00-fold,NN-kesit}.png + __data.json + _ozet.json
//   node tools/live/shots.mjs --diff <once_dizini> <sonra_dizini>
//       → aynı adlı PNG'ler için AE (farklı piksel sayısı); <sonra>/_diff/*.png + _diff.json
//   node tools/live/shots.mjs --pair <mockup.html> <url|/yol> [--out dizin] [--vp ...]
//       → her genişlikte mockup | canlı yan yana tek PNG
//   node tools/live/shots.mjs --list   → tanımlı sayfa adları
//   node tools/live/shots.mjs <ID> ... --kapi83   → çekimden sonra kapı 83 (clipped-content-check) aynı dizine
//   node tools/live/shots.mjs --north-star [--out dosya.md]
//       → §3.1 N2-N20 + N31 tek markdown tablo: ~/ops/plans/olcum/<tarih>.md (otomatik ölçülemeyenler "—" + yöntem)
//
// C-05b: her çekimde axe-core serious/critical sayımı (a11y), mobilde 390×844 sabit krom (fixed|sticky yükseklik
// birleşimi, tasarim-hisse-ozet §6 chrome.js yöntemi), DOM düğüm sayısı ve TBT (long task − 50 ms, kaydırmadan önce).
//
// CLS/LCP: gözlemci sayfa betiklerinden ÖNCE (addInitScript) kurulur ve kaydırmadan önce okunur;
// kaydırma sonrası kaymalar ayrı alanda (clsAfterScroll) raporlanır. Font-render: CDP CSS.getPlatformFontsForNode.

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..', '..');
const MOD_DIRS = [REPO, path.join(os.homedir(), 'Bist ve BTC', 'Bist30'),
  ...(process.env.NODE_PATH || '').split(path.delimiter).filter(Boolean).map((p) => path.dirname(p))];

function resolveMod(name, sub) {
  for (const dir of MOD_DIRS) {
    try {
      const req = createRequire(path.join(dir, 'package.json'));
      return sub ? req.resolve(name + '/' + sub) : req(name);
    } catch (e) { /* sıradaki */ }
  }
  return null;
}

function loadPlaywright() {
  const pw = resolveMod('playwright');
  if (pw) return pw;
  console.error('playwright bulunamadı (repo ya da ~/Bist ve BTC/Bist30/node_modules)');
  process.exit(2);
}
const AXE_PATH = resolveMod('axe-core', 'axe.min.js');

const PAGES = {
  anasayfa: '/',
  'hisse-THYAO': '/hisse/THYAO',
  'hisse-THYAO-grafik': '/hisse/THYAO?tab=grafik',
  'hisse-THYAO-temel': '/hisse/THYAO?tab=temel',
  'hisse-THYAO-haberler': '/hisse/THYAO?tab=haberler',
  'hisse-GARAN': '/hisse/GARAN',
  tarama: '/tarama',
  'sektor-harita': '/sektor-harita',
  karsilastir: '/karsilastir?t=THYAO,GARAN,ASELS',
  hisseler: '/hisseler',
  gundem: '/gundem',
  ozet: '/ozet',
  'bilanco-takvimi': '/bilanco-takvimi',
  'temettu-takvimi': '/temettu-takvimi',
  portfolio: '/portfolio',
  blog: '/blog',
  metodoloji: '/metodoloji',
  hakkinda: '/hakkinda',
};
const VP_H = { 1440: 900, 820: 1180, 390: 844, 320: 700 };
const MAX_SLICES = 8;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function args(argv) {
  const o = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) {
      const k = a.slice(2);
      const next = argv[i + 1];
      if (next === undefined || next.startsWith('--')) o[k] = true;
      else { o[k] = next; i++; }
    } else o._.push(a);
  }
  return o;
}

// Sayfa betiklerinden önce çalışır: kaymaları ve LCP'yi baştan toplar.
const INIT = () => {
  const m = { cls: 0, clsAfterScroll: 0, scrolled: false, lcp: null, lcpEl: null, shifts: [], tbt: 0 };
  window.__bpMetrics = m;
  try {
    new PerformanceObserver((l) => {
      for (const e of l.getEntries()) if (!m.scrolled) m.tbt += Math.max(0, e.duration - 50);
    }).observe({ type: 'longtask', buffered: true });
  } catch (e) { /* desteklenmiyor */ }
  try {
    new PerformanceObserver((l) => {
      for (const e of l.getEntries()) {
        if (e.hadRecentInput) continue;
        if (m.scrolled) { m.clsAfterScroll += e.value; continue; }
        m.cls += e.value;
        if (m.shifts.length < 12) {
          const src = (e.sources || []).map((s) => {
            const n = s.node;
            if (!n || !n.tagName) return '?';
            return n.tagName.toLowerCase() + (n.id ? '#' + n.id : '') + (n.classList && n.classList[0] ? '.' + n.classList[0] : '');
          });
          m.shifts.push({ t: Math.round(e.startTime), v: Math.round(e.value * 1000) / 1000, src: src.slice(0, 3) });
        }
      }
    }).observe({ type: 'layout-shift', buffered: true });
  } catch (e) { /* desteklenmiyor */ }
  try {
    new PerformanceObserver((l) => {
      for (const e of l.getEntries()) {
        m.lcp = e.startTime;
        const n = e.element;
        m.lcpEl = n ? n.tagName.toLowerCase() + (n.id ? '#' + n.id : '') + (n.classList && n.classList[0] ? '.' + n.classList[0] : '') : null;
      }
    }).observe({ type: 'largest-contentful-paint', buffered: true });
  } catch (e) { /* desteklenmiyor */ }
};

async function fontRender(page) {
  // Başlık ve gövde metninin gerçekte hangi fontla çizildiği (yedek font kaçağı tespiti).
  const out = {};
  try {
    const cdp = await page.context().newCDPSession(page);
    await cdp.send('DOM.enable');
    await cdp.send('CSS.enable');
    const { root } = await cdp.send('DOM.getDocument', { depth: 0 });
    for (const sel of ['h1', 'body', '.da-num, .num, [class*="price"]']) {
      const { nodeId } = await cdp.send('DOM.querySelector', { nodeId: root.nodeId, selector: sel });
      if (!nodeId) continue;
      const { fonts } = await cdp.send('CSS.getPlatformFontsForNode', { nodeId });
      out[sel] = fonts.map((f) => `${f.familyName}${f.isCustomFont ? ' (web)' : ''}×${f.glyphCount}`);
    }
    await cdp.detach();
  } catch (e) { out.error = String(e).slice(0, 120); }
  return out;
}

// Sabit krom: kaydırılmış sayfada görünen fixed|sticky öğelerin dikey birleşimi (üst üste binenler bir kez sayılır).
const CHROME = () => {
  const els = [...document.querySelectorAll('body *')].filter((e) => {
    const s = getComputedStyle(e);
    if (s.position !== 'fixed' && s.position !== 'sticky') return false;
    const b = e.getBoundingClientRect();
    return b.height > 20 && b.width > 200 && b.bottom > 0 && b.top < innerHeight && s.visibility !== 'hidden' && s.display !== 'none' && s.opacity !== '0';
  }).map((e) => { const b = e.getBoundingClientRect(); return { el: e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + (e.classList[0] ? '.' + e.classList[0] : ''), top: Math.max(0, Math.round(b.top)), bottom: Math.min(innerHeight, Math.round(b.bottom)) }; });
  const iv = els.map((e) => [e.top, e.bottom]).sort((a, b) => a[0] - b[0]);
  let px = 0, cur = null;
  for (const [a, b] of iv) {
    if (!cur || a > cur[1]) { if (cur) px += cur[1] - cur[0]; cur = [a, b]; } else cur[1] = Math.max(cur[1], b);
  }
  if (cur) px += cur[1] - cur[0];
  return { px, pct: Math.round((px / innerHeight) * 1000) / 10, els };
};

async function runAxe(page) {
  if (!AXE_PATH) return { error: 'axe-core yok (npm i -D axe-core)' };
  try {
    await page.addScriptTag({ path: AXE_PATH });
    return await page.evaluate(async () => {
      const r = await window.axe.run(document, { resultTypes: ['violations'] });
      const v = r.violations.filter((x) => x.impact === 'serious' || x.impact === 'critical');
      return { serious: v.filter((x) => x.impact === 'serious').reduce((n, x) => n + x.nodes.length, 0),
        critical: v.filter((x) => x.impact === 'critical').reduce((n, x) => n + x.nodes.length, 0),
        rules: v.map((x) => `${x.id}(${x.impact[0]})×${x.nodes.length}`) };
    });
  } catch (e) { return { error: String(e).slice(0, 120) }; }
}

async function capturePage(browser, base, slug, url, width, outDir) {
  const vp = { width, height: VP_H[width] || 900 };
  const mobile = width < 768;
  const ctx = await browser.newContext({ viewport: vp, deviceScaleFactor: 1, isMobile: mobile, hasTouch: mobile, locale: 'tr-TR', colorScheme: 'dark' });
  await ctx.addInitScript(INIT);
  const page = await ctx.newPage();
  const consoleErrors = [];
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 200)); });
  page.on('pageerror', (e) => consoleErrors.push('pageerror: ' + String(e).slice(0, 200)));
  let status = null;
  const full = /^https?:|^file:/.test(url) ? url : base + url;
  for (let attempt = 0; attempt < 2; attempt++) {
    try { const r = await page.goto(full, { waitUntil: 'load', timeout: 45000 }); status = r ? r.status() : null; }
    catch (e) { status = 'ERR ' + String(e).slice(0, 80); }
    if (status === 429) { await sleep(30000); continue; }
    break;
  }
  try { await page.waitForLoadState('networkidle', { timeout: 8000 }); } catch (e) { /* uzun sorgu olabilir */ }
  await sleep(1500);
  // Kaydırmadan önce: yükleme CLS'i ve LCP (kaydırma LCP'yi dondurur).
  const pre = await page.evaluate(() => {
    const m = window.__bpMetrics || {};
    m.scrolled = true;
    const nav = performance.getEntriesByType('navigation')[0] || {};
    return {
      cls: Math.round((m.cls || 0) * 1000) / 1000, lcp: m.lcp && Math.round(m.lcp), lcpEl: m.lcpEl, shifts: m.shifts || [],
      ttfb: Math.round(nav.responseStart || 0), dcl: Math.round(nav.domContentLoadedEventEnd || 0), load: Math.round(nav.loadEventEnd || 0),
      htmlKB: Math.round((nav.transferSize || 0) / 1024), requests: performance.getEntriesByType('resource').length + 1,
      tbt: Math.round(m.tbt || 0), dom: document.getElementsByTagName('*').length,
    };
  });
  const base0 = path.join(outDir, `${slug}__${width}`);
  await page.screenshot({ path: `${base0}__00-fold.png` });
  const h = await page.evaluate(() => document.documentElement.scrollHeight);
  let chrome = null;
  if (mobile) {
    await page.evaluate(() => window.scrollTo(0, 1500));
    await sleep(800);
    chrome = await page.evaluate(CHROME);
  }
  for (let y = 0; y < h; y += vp.height) { await page.evaluate((yy) => window.scrollTo(0, yy), y); await sleep(150); }
  await page.evaluate(() => window.scrollTo(0, 0));
  await sleep(600);
  const fullH = await page.evaluate(() => document.documentElement.scrollHeight);
  const sliceH = Math.round(vp.height * 1.5);
  const slices = [];
  for (let i = 0, y = 0; y < fullH && i < MAX_SLICES; i++, y += sliceH) {
    const f = `${base0}__${String(i + 1).padStart(2, '0')}-kesit.png`;
    await page.screenshot({ path: f, fullPage: true, clip: { x: 0, y, width: vp.width, height: Math.min(sliceH, fullH - y) } });
    slices.push(path.basename(f));
  }
  const post = await page.evaluate(() => ({
    clsAfterScroll: Math.round(((window.__bpMetrics || {}).clsAfterScroll || 0) * 1000) / 1000,
    horizOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    title: document.title,
    h1: [...document.querySelectorAll('h1')].map((x) => x.textContent.trim().slice(0, 80)),
  }));
  const fonts = await fontRender(page);
  const a11y = await runAxe(page);
  const rec = { slug, url: full, width, status, fullHeight: fullH, slicesTruncated: fullH > sliceH * MAX_SLICES, slices,
    perf: pre, ...post, chrome, a11y, fonts, consoleErrors: consoleErrors.slice(0, 10), at: new Date().toISOString() };
  fs.writeFileSync(`${base0}__data.json`, JSON.stringify(rec, null, 1));
  await ctx.close();
  return rec;
}

function aeDiff(a, b, out) {
  // compare çıkış kodu: 0 aynı, 1 farklı, 2 hata; AE değeri stderr'e yazılır.
  try {
    execFileSync('compare', ['-metric', 'AE', '-fuzz', '2%', a, b, out], { stdio: ['ignore', 'ignore', 'pipe'] });
    return 0;
  } catch (e) {
    const s = String(e.stderr || '').trim();
    const n = parseFloat(s);
    if (e.status === 1 && !Number.isNaN(n)) return Math.round(n);
    return 'hata: ' + (s.split('\n')[0] || 'boyut farkı').slice(0, 80);
  }
}

function runDiff(onceDir, sonraDir) {
  const outDir = path.join(sonraDir, '_diff');
  fs.mkdirSync(outDir, { recursive: true });
  const rows = [];
  for (const f of fs.readdirSync(onceDir).filter((x) => x.endsWith('.png')).sort()) {
    const b = path.join(sonraDir, f);
    if (!fs.existsSync(b)) { rows.push({ file: f, ae: 'sonra yok' }); continue; }
    rows.push({ file: f, ae: aeDiff(path.join(onceDir, f), b, path.join(outDir, f)) });
  }
  fs.writeFileSync(path.join(sonraDir, '_diff.json'), JSON.stringify(rows, null, 1));
  for (const r of rows) console.log(String(r.ae).padStart(10), r.file);
  const changed = rows.filter((r) => r.ae !== 0).length;
  console.log(`\n${rows.length} çekim, ${changed} farklı → ${outDir}`);
}

async function runPair(browser, mockup, url, base, widths, outDir) {
  fs.mkdirSync(outDir, { recursive: true });
  const murl = /^https?:|^file:/.test(mockup) ? mockup : pathToFileURL(path.resolve(mockup)).href;
  for (const w of widths) {
    const a = await capturePage(browser, base, 'mockup', murl, w, outDir);
    const b = await capturePage(browser, base, 'canli', url, w, outDir);
    const out = path.join(outDir, `pair__${w}.png`);
    execFileSync('magick', [path.join(outDir, `mockup__${w}__00-fold.png`), path.join(outDir, `canli__${w}__00-fold.png`),
      '-background', '#333', '-splice', '8x0', '+append', '+repage', out]);
    console.log(w, 'mockup', a.status, 'canlı', b.status, '→', out);
  }
}

function runKapi83(base, widths, out) {
  // Kapı 83: kırpılmış ama kaydırılamayan içerik. Çıkış 0 temiz, 2 ihlal.
  const w = (widths.length ? widths : [320, 360]).join(',');
  try {
    execFileSync('node', [path.join(REPO, 'tools', 'clipped-content-check.mjs'), `--base=${base}`, `--widths=${w}`, `--out=${out}`], { stdio: 'inherit', cwd: REPO });
    return 'temiz';
  } catch (e) { return e.status === 2 ? 'ihlal' : 'hata'; }
}

// --- Kuzey Yıldızı (§3.1) -------------------------------------------------------------------------------
const NS_PAGES = {
  tarama: '/tarama', 'sektor-harita': '/sektor-harita', karsilastir: '/karsilastir', hisseler: '/hisseler', gundem: '/gundem',
  ozet: '/ozet', 'bilanco-takvimi': '/bilanco-takvimi', 'temettu-takvimi': '/temettu-takvimi', portfolio: '/portfolio',
  profil: '/profil', iletisim: '/iletisim', blog: '/blog', makale: '/blog/supertrend-indikatoru-nedir', metodoloji: '/metodoloji',
  hakkinda: '/hakkinda', yasal: '/yasal', gizlilik: '/gizlilik', hata: '/bu-sayfa-yok-ns', hisse: '/hisse/THYAO',
};
const NS_EXTRA = { anasayfa: '/', 'hisse-grafik': '/hisse/THYAO?tab=grafik', 'hisse-temel': '/hisse/THYAO?tab=temel', 'hisse-haberler': '/hisse/THYAO?tab=haberler' };
const SLOW4G = { offline: false, latency: 562.5, downloadThroughput: (1.6 * 1024 * 1024 * 0.9) / 8, uploadThroughput: (750 * 1024 * 0.9) / 8 };

async function nsMeasure(browser, base, url, width, { throttle = false } = {}) {
  const mobile = width < 768;
  const ctx = await browser.newContext({ viewport: { width, height: VP_H[width] || 900 }, deviceScaleFactor: 1, isMobile: mobile, hasTouch: mobile, locale: 'tr-TR', colorScheme: 'dark' });
  await ctx.addInitScript(INIT);
  const page = await ctx.newPage();
  const fonts = [];
  page.on('response', async (r) => {
    if (r.request().resourceType() !== 'font') return;
    try { fonts.push({ url: r.url().slice(0, 90), bytes: (await r.body()).length }); } catch (e) { fonts.push({ url: r.url().slice(0, 90), bytes: 0 }); }
  });
  if (throttle) {
    const cdp = await ctx.newCDPSession(page);
    await cdp.send('Network.enable');
    await cdp.send('Network.emulateNetworkConditions', SLOW4G);
    await cdp.send('Emulation.setCPUThrottlingRate', { rate: 4 });
  }
  let status = null;
  try { const r = await page.goto(base + url, { waitUntil: 'load', timeout: throttle ? 90000 : 45000 }); status = r ? r.status() : null; }
  catch (e) { status = 'ERR'; }
  try { await page.waitForLoadState('networkidle', { timeout: throttle ? 20000 : 8000 }); } catch (e) { /* uzun sorgu */ }
  await sleep(1500);
  const r = await page.evaluate(() => {
    const m = window.__bpMetrics || {};
    m.scrolled = true;
    const vis = (e) => { const b = e.getBoundingClientRect(); const s = getComputedStyle(e); return b.width > 2 && b.height > 2 && s.visibility !== 'hidden' && s.display !== 'none' && s.opacity !== '0' && !/rect\(0/.test(s.clip) && s.clipPath !== 'inset(50%)'; };
    const price = document.getElementById('hpPrice');
    const pb = price && price.getBoundingClientRect();
    const hrefs = (sel) => new Set([...document.querySelectorAll(sel)].map((a) => a.getAttribute('href')).filter((h) => h && h !== '#' && !h.startsWith('javascript')));
    return {
      cls: Math.round((m.cls || 0) * 1000) / 1000, lcp: m.lcp && Math.round(m.lcp), tbt: Math.round(m.tbt || 0),
      dom: document.getElementsByTagName('*').length, height: document.documentElement.scrollHeight,
      h1Visible: [...document.querySelectorAll('h1')].some(vis),
      price: price ? { px: parseFloat(getComputedStyle(price).fontSize), y: Math.round(pb.top + scrollY) } : null,
      navDesk: hrefs('.bp-main-nav a[href]').size, navMob: hrefs('.mobile-bottom-nav a[href]').size,
      navDeskSet: [...hrefs('.bp-main-nav a[href]')], navMobSet: [...hrefs('.mobile-bottom-nav a[href]')],
    };
  });
  const f = await fontRender(page);
  r.h1System = Array.isArray(f.h1) && f.h1.some((x) => !x.includes('(web)'));
  if (mobile) { await page.evaluate(() => window.scrollTo(0, 1500)); await sleep(800); r.chrome = await page.evaluate(CHROME); }
  r.status = status;
  r.fonts = fonts;
  await ctx.close();
  return r;
}

function nsStatic() {
  // N15: şablonlarda emoji ve satır-içi style="" (JS dosyaları hariç).
  const dir = path.join(REPO, 'templates');
  let emoji = 0, style = 0;
  const EMO = /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{2B50}\u{2705}\u{274C}]/gu;
  for (const f of fs.readdirSync(dir).filter((x) => x.endsWith('.html'))) {
    const t = fs.readFileSync(path.join(dir, f), 'utf8');
    emoji += (t.match(EMO) || []).length;
    style += (t.match(/\sstyle="/g) || []).length;
  }
  return { emoji, style };
}

function brSize(url) {
  try { return Math.round(Number(execFileSync('curl', ['-s', '-o', '/dev/null', '-H', 'Accept-Encoding: br', '-w', '%{size_download}', url]).toString()) / 102.4) / 10; }
  catch (e) { return null; }
}

function planRows() {
  // §3.1 tablosundan ölçüt ve hedef (tek kaynak plan; burada kopya yok).
  const out = {};
  try {
    const t = fs.readFileSync(path.join(os.homedir(), 'ops', 'plans', '2026-09-23-MASTER-PLAN.md'), 'utf8');
    const sec = t.split('### 3.1')[1].split('### 3.2')[0];
    for (const line of sec.split('\n')) {
      const c = line.split('|').map((x) => x.trim());
      if (/^N\d+$/.test(c[1] || '')) out[c[1]] = { olcut: c[3], hedef: c[5] };
    }
  } catch (e) { /* plan yoksa boş */ }
  return out;
}

async function runNorthStar(browser, base, outFile) {
  const m390 = {}, m1440 = {};
  for (const [k, u] of Object.entries({ anasayfa: '/', ...NS_PAGES })) { m390[k] = await nsMeasure(browser, base, u, 390); console.log('390 ', k, m390[k].status); await sleep(800); }
  for (const [k, u] of Object.entries({ ...NS_PAGES, ...NS_EXTRA })) { m1440[k] = await nsMeasure(browser, base, u, 1440); console.log('1440', k, m1440[k].status); await sleep(800); }
  for (const k of ['hisse-grafik', 'hisse-temel', 'hisse-haberler']) m390[k] = await nsMeasure(browser, base, NS_EXTRA[k], 390);
  const lab = {};
  for (const k of ['anasayfa', 'hisse', 'tarama']) { lab[k] = await nsMeasure(browser, base, k === 'anasayfa' ? '/' : NS_PAGES[k], 390, { throttle: true }); console.log('lab ', k, lab[k].lcp); }
  const st = nsStatic();
  const tpl = Object.keys(NS_PAGES);
  const all = [...Object.entries(m390).map(([k, v]) => [k + '@390', v]), ...Object.entries(m1440).map(([k, v]) => [k + '@1440', v])];
  const worst = (f) => all.reduce((a, [k, v]) => (v[f] != null && (!a || v[f] > a[1]) ? [k, v[f]] : a), null);
  const ok = (b) => (b ? '✅' : '❌');
  const h = m390.hisse, home1440 = m1440['anasayfa'], home390 = m390.anasayfa;
  const same = JSON.stringify([...home1440.navDeskSet].sort()) === JSON.stringify([...home390.navMobSet].sort());
  const h1ok = tpl.filter((k) => m390[k].h1Visible && m1440[k].h1Visible).length;
  const sysFont = all.filter(([, v]) => v.h1System).map(([k]) => k);
  const fontSet = new Map(); for (const [, v] of all) for (const f of v.fonts) fontSet.set(f.url, f.bytes);
  const fontKB = Math.round([...fontSet.values()].reduce((a, b) => a + b, 0) / 1024);
  const htmlBr = Math.max(...['/', '/hisse/THYAO', '/tarama'].map((u) => brSize(base + u) || 0));
  const domW = worst('dom'), tbtW = worst('tbt'), clsW = worst('cls');
  const lcpW = Object.entries(lab).reduce((a, [k, v]) => (!a || (v.lcp || 1e9) > a[1] ? [k, v.lcp || null] : a), null);
  const R = {
    N3: [`${home1440.navDesk} / ${home390.navMob}, ${same ? 'aynı' : 'farklı'}`, ok(home1440.navDesk <= 5 && home390.navMob <= 5 && same), 'ana sayfa `.bp-main-nav` / `.mobile-bottom-nav` benzersiz href'],
    N11: [`${h1ok}/${tpl.length}`, ok(h1ok === tpl.length), 'görünür H1 hem 390 hem 1440 (sr-only sayılmaz)'],
    N12: [`${sysFont.length}`, ok(sysFont.length === 0), 'soğuk bağlamda H1 CDP platform fontu' + (sysFont.length ? ': ' + sysFont.slice(0, 6).join(', ') : '')],
    N15: [`${st.emoji} / ${st.style}`, ok(st.emoji === 0 && st.style <= 150), 'templates/*.html statik sayım'],
    N16: [`${h.height} / ${home390.height} / ${m390.tarama.height} px`, ok(h.height <= 3400 && home390.height <= 4300 && m390.tarama.height <= 5000), '390px scrollHeight'],
    N17: [h.price ? `${h.price.px}px / y=${h.price.y}; krom ${h.chrome.px}px (%${h.chrome.pct})` : `fiyat yok; krom ${h.chrome.px}px`, ok(h.price && h.price.px >= 40 && h.price.y <= 200 && h.chrome.px <= 152), '/hisse/THYAO 390×844 `#hpPrice`; krom = 1500px kaydırmada fixed|sticky birleşimi'],
    N18: [`${lcpW && lcpW[1] != null ? (lcpW[1] / 1000).toFixed(2) + ' s (' + lcpW[0] + ')' : '?'}`, ok(lcpW && lcpW[1] != null && lcpW[1] <= 2000), 'Slow4G (562 ms, 1,44 Mbit) + 4× CPU, 390, soğuk; /, /hisse/THYAO, /tarama en kötüsü'],
    N19: [`${clsW[1]} (${clsW[0]})`, ok(clsW[1] <= 0.05), `${all.length} yükleme (390+1440, hisse sekmeleri dahil), kaydırmadan önce`],
    N20: [`${tbtW[1]} ms / ${fontKB} KB, ${fontSet.size} dosya / ${htmlBr} KB / ${domW[1]} (${domW[0]})`, ok(tbtW[1] <= 150 && fontKB <= 70 && fontSet.size <= 3 && htmlBr <= 30 && all.every(([k, v]) => v.dom <= (k.startsWith('tarama') ? 2500 : 1500))), 'TBT long task (throttle yok), font yanıt gövdeleri, HTML br (/, hisse, tarama en büyüğü), DOM en büyüğü'],
  };
  const MAN = { N2: 'elle sayım (varsayılan görünür kavram)', N4: 'model verisi — DEV (/api/data)', N5: '217 sayfa taraması — DEV', N6: 'veri kaydı — DEV', N7: '217 hisse fiyat/grafik — DEV',
    N8: 'metin denetimi — elle', N9: 'akış testi — elle', N10: 'mail logu — DEV', N13: 'CSS token sayımı — ayrı araç (Faz 3)', N14: 'bileşen kanonu — ayrı araç (Faz 3)', N31: 'last_fresh_ts × JS kapalı uyarı — DEV' };
  const P = planRows();
  const order = ['N2', 'N3', 'N4', 'N5', 'N6', 'N7', 'N31', 'N8', 'N9', 'N10', 'N11', 'N12', 'N13', 'N14', 'N15', 'N16', 'N17', 'N18', 'N19', 'N20'];
  const tarih = new Date().toISOString().slice(0, 10);
  let md = `# Kuzey Yıldızı ölçümü — ${tarih}\n\n\`node tools/live/shots.mjs --north-star\` · ${base} · ${new Date().toLocaleString('tr-TR')}\n\n`;
  md += `| # | Ölçüt | Hedef | Ölçülen | Durum | Yöntem |\n|---|---|---|---|---|---|\n`;
  for (const n of order) {
    const p = P[n] || { olcut: '', hedef: '' };
    const r = R[n] || ['—', '—', MAN[n] || 'otomatik değil'];
    md += `| ${n} | ${p.olcut} | ${p.hedef} | ${r[0]} | ${r[1]} | ${r[2]} |\n`;
  }
  const kr = h.chrome.els.map((e) => `${e.el} ${e.top}-${e.bottom}`).join(', ');
  md += `\nKrom öğeleri (hisse 390): ${kr || 'yok'}\n`;
  fs.mkdirSync(path.dirname(outFile), { recursive: true });
  fs.writeFileSync(outFile, md);
  fs.writeFileSync(outFile.replace(/\.md$/, '.json'), JSON.stringify({ m390, m1440, lab, st }, null, 1));
  console.log(md);
  console.log('→', outFile);
}

const o = args(process.argv.slice(2));
const base = (o.base || 'https://borsapusula.com').replace(/\/$/, '');
const widths = String(o.vp || '1440,820,390,320').split(',').map(Number).filter(Boolean);

if (o.list) { for (const [k, v] of Object.entries(PAGES)) console.log(k.padEnd(22), v); process.exit(0); }
if (o.diff) {
  const [a, b] = [o.diff, o._[0]];
  if (!a || !b) { console.error('--diff <once> <sonra>'); process.exit(2); }
  runDiff(a, b);
  process.exit(0);
}

const { chromium } = loadPlaywright();
const browser = await chromium.launch();
try {
  if (o['north-star']) {
    const tarih = new Date().toISOString().slice(0, 10);
    await runNorthStar(browser, base, o.out || path.join(os.homedir(), 'ops', 'plans', 'olcum', `${tarih}.md`));
  } else if (o.pair) {
    const url = o._[0];
    if (!url) { console.error('--pair <mockup.html> <url>'); process.exit(2); }
    await runPair(browser, o.pair, url, base, widths, o.out || path.join(os.tmpdir(), 'bp-pair'));
  } else {
    const id = o._[0];
    if (!id) { console.error('Kullanım: shots.mjs <ID> [--faz once|sonra] [--sayfa a,b] [--vp 1440,390]'); process.exit(2); }
    const faz = o.faz || 'once';
    const outDir = path.join(o.out || path.join(os.homedir(), 'ops', 'plans', 'shots', id), faz);
    fs.mkdirSync(outDir, { recursive: true });
    const slugs = o.sayfa ? String(o.sayfa).split(',') : Object.keys(PAGES);
    const summary = [];
    for (const slug of slugs) {
      const url = PAGES[slug] || (slug.startsWith('/') ? slug : null);
      if (!url) { console.error('bilinmeyen sayfa:', slug, '(--list)'); continue; }
      const name = PAGES[slug] ? slug : slug.replace(/[^a-z0-9]+/gi, '-').replace(/^-|-$/g, '') || 'kok';
      for (const w of widths) {
        const r = await capturePage(browser, base, name, url, w, outDir);
        summary.push({ slug: name, width: w, status: r.status, cls: r.perf.cls, clsAfterScroll: r.clsAfterScroll, lcp: r.perf.lcp,
          lcpEl: r.perf.lcpEl, horizOverflow: r.horizOverflow, consoleErrors: r.consoleErrors.length,
          axeSerious: r.a11y.serious, axeCritical: r.a11y.critical, chromePx: r.chrome && r.chrome.px });
        console.log(`${name.padEnd(20)} ${String(w).padStart(4)} ${r.status} CLS ${r.perf.cls} (+${r.clsAfterScroll} kaydırma) LCP ${r.perf.lcp}ms ${r.perf.lcpEl || ''} taşma ${r.horizOverflow}`
          + ` axe s${r.a11y.serious ?? '?'}/c${r.a11y.critical ?? '?'}` + (r.chrome ? ` krom ${r.chrome.px}px` : ''));
        await sleep(1000);
      }
    }
    fs.writeFileSync(path.join(outDir, '_ozet.json'), JSON.stringify(summary, null, 1));
    if (o.kapi83) summary.kapi83 = runKapi83(base, widths.filter((w) => w < 768), path.join(outDir, '_kapi83.json'));
    console.log('→', outDir);
  }
} finally {
  await browser.close();
}
