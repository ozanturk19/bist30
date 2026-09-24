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

function loadPlaywright() {
  const cands = [REPO, path.join(os.homedir(), 'Bist ve BTC', 'Bist30'),
    ...(process.env.NODE_PATH || '').split(path.delimiter).filter(Boolean).map((p) => path.dirname(p))];
  for (const dir of cands) {
    try { return createRequire(path.join(dir, 'package.json'))('playwright'); } catch (e) { /* sıradaki */ }
  }
  console.error('playwright bulunamadı (repo ya da ~/Bist ve BTC/Bist30/node_modules)');
  process.exit(2);
}

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
  const m = { cls: 0, clsAfterScroll: 0, scrolled: false, lcp: null, lcpEl: null, shifts: [] };
  window.__bpMetrics = m;
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
    };
  });
  const base0 = path.join(outDir, `${slug}__${width}`);
  await page.screenshot({ path: `${base0}__00-fold.png` });
  const h = await page.evaluate(() => document.documentElement.scrollHeight);
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
  const rec = { slug, url: full, width, status, fullHeight: fullH, slicesTruncated: fullH > sliceH * MAX_SLICES, slices,
    perf: pre, ...post, fonts, consoleErrors: consoleErrors.slice(0, 10), at: new Date().toISOString() };
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
  if (o.pair) {
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
          lcpEl: r.perf.lcpEl, horizOverflow: r.horizOverflow, consoleErrors: r.consoleErrors.length });
        console.log(`${name.padEnd(20)} ${String(w).padStart(4)} ${r.status} CLS ${r.perf.cls} (+${r.clsAfterScroll} kaydırma) LCP ${r.perf.lcp}ms ${r.perf.lcpEl || ''} taşma ${r.horizOverflow}`);
        await sleep(1000);
      }
    }
    fs.writeFileSync(path.join(outDir, '_ozet.json'), JSON.stringify(summary, null, 1));
    console.log('→', outDir);
  }
} finally {
  await browser.close();
}
