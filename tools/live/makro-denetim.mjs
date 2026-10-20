#!/usr/bin/env node
// C-P0-2010 — Makro şerit denetimi (Ozan 20.10, 2. kez: "üst şerit her sayfada aynı, renkli ve sabit değil").
// Her sayfa × genişlikte, ölçerek:
//   M1  şerit var mı (#macroBar tam 1 kez)
//   M2  kaydırınca üstte sabit mi: min(1200, kaydırılabilir) px kaydırınca şeridin üstü 0 (±1);
//       header şeridin hemen altında (|header.top − şerit.alt| ≤ 2). Kaydırılamayan sayfada ölçülmez.
//   M3  gri değişim yok: .mc-pos / .mc-neg rengi gri değil (|r−g| < 20 ve |g−b| < 20 = gri)
//   M4  öğe ≥ 5 (tazelik notu .macro-meta hariç)
//   M5  ana sayfayla aynı: yükseklik, arka plan, etiket ("Piyasalar") aynı genişlikteki /'nin değeriyle eşit
// Yalnız GET; siteye hiçbir şey yazmaz. Service worker kapalı (sunucunun verdiği sayfa ölçülür).
// Yeni npm paketi yok: playwright repo ya da ~/Bist ve BTC/Bist30/node_modules'tan çözülür (gorsel-denetim.mjs gibi).
//
// Kullanım:
//   BASE=https://borsapusula.com node tools/live/makro-denetim.mjs [yol ...] [--vp=1440x900,390x844,375x667]
//       [--out=dosya.json]
//   yol verilmezse aşağıdaki 25 sayfa (offline ve abonelik iptali şeritsiz; listede yok).
// Exit: 0 tümü geçti · 1 en az bir FAIL · 2 sonda çöktü / playwright yok.
//
// NEREDE KOŞAR: deploy sonrası canlıda (CPO kabulü) ve akşam QA'da:
//   BASE=https://borsapusula.com node tools/live/makro-denetim.mjs

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..', '..');
const MOD_DIRS = [REPO, path.join(os.homedir(), 'Bist ve BTC', 'Bist30'),
  ...(process.env.NODE_PATH || '').split(path.delimiter).filter(Boolean).map((p) => path.dirname(p))];
function resolveMod(name) {
  for (const dir of MOD_DIRS) {
    try { return createRequire(path.join(dir, 'package.json'))(name); } catch (e) { /* sıradaki */ }
  }
  return null;
}

const PATHS = ['/', '/tarama', '/hisseler', '/sektor-harita', '/takvim', '/blog',
  '/blog/trend-donus-seviyesi-supertrend-nedir', '/karsilastir', '/metodoloji', '/hakkinda', '/iletisim', '/gizlilik',
  '/yasal', '/kesfet', '/kesfet/istikrarli-temettu', '/haberler', '/haberler/bildirimler', '/bulten/arsiv',
  '/bulten/2026-10-19', '/harita/2026-10-19', '/takip', '/hisse/THYAO', '/hisse/THYAO/bilanco',
  '/hisse/THYAO/bildirim/1682832', '/yok-boyle-sayfa'];
const UA = {
  desk: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 BorsaPusulaQA-makro',
  iphone: 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Mobile/15E148 Safari/604.1 BorsaPusulaQA-makro',
};
const SCROLL = 1200;

function args(argv) {
  const o = { _: [] };
  for (const a of argv) {
    if (!a.startsWith('--')) { o._.push(a); continue; }
    const eq = a.indexOf('=');
    if (eq > 0) o[a.slice(2, eq)] = a.slice(eq + 1); else o[a.slice(2)] = true;
  }
  return o;
}

// Tarayıcıda koşar: şerit verisi gelene kadar bekler (≤ 10 sn), ölçer, kaydırır, yeniden ölçer.
const PROBE = async (scrollPx) => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  for (let i = 0; i < 50 && !document.querySelector('#macroTrack .mc-pos, #macroTrack .mc-neg, #macroTrack .mc-neu'); i++) await sleep(200);
  const bars = document.querySelectorAll('#macroBar');
  const bar = bars[0];
  if (!bar) return { bar: 0 };
  const isGrey = (el) => { const [r, g, b] = getComputedStyle(el).color.match(/\d+/g).map(Number); return Math.abs(r - g) < 20 && Math.abs(g - b) < 20; };
  const items = [...bar.querySelectorAll('.macro-item')].filter((x) => !x.classList.contains('macro-meta'));
  const pos = [...bar.querySelectorAll('.mc-pos')], neg = [...bar.querySelectorAll('.mc-neg')];
  const lbl = bar.querySelector('.macro-live');
  const cs = getComputedStyle(bar);
  const out = {
    bar: bars.length, pos: cs.position, h: Math.round(bar.getBoundingClientRect().height), bg: cs.backgroundColor,
    label: lbl ? lbl.textContent.trim() : '', items: items.length,
    nPos: pos.length, nNeg: neg.length, posGrey: pos.filter(isGrey).length, negGrey: neg.filter(isGrey).length,
    top0: Math.round(bar.getBoundingClientRect().top),
  };
  const de = document.documentElement;
  const max = Math.max(0, de.scrollHeight - innerHeight);
  out.scrolled = Math.min(scrollPx, max);
  if (out.scrolled > 0) {
    window.scrollTo({ top: out.scrolled, behavior: 'instant' });
    await sleep(400);
    out.scrolled = Math.round(scrollY);
    const br = bar.getBoundingClientRect();
    out.topAfter = Math.round(br.top);
    const hdr = document.querySelector('body > header');
    out.hdrGap = hdr ? Math.round(hdr.getBoundingClientRect().top - br.bottom) : null;
  }
  return out;
};

function judge(r, home) {
  const f = [];
  if (!r.bar) { f.push('M1 şerit yok'); return f; }
  if (r.bar !== 1) f.push(`M1 şerit ${r.bar} kez`);
  if (r.scrolled > 0) {
    if (Math.abs(r.topAfter) > 1) f.push(`M2 kaydırınca üstte değil (top=${r.topAfter}, ${r.scrolled} px)`);
    if (r.hdrGap == null || Math.abs(r.hdrGap) > 2) f.push(`M2 header şeridin altında değil (aralık=${r.hdrGap})`);
  }
  if (r.posGrey || r.negGrey) f.push(`M3 gri değişim ${r.posGrey + r.negGrey}/${r.nPos + r.nNeg}`);
  if (r.items < 5) f.push(`M4 öğe ${r.items} < 5`);
  if (home && home.bar) {
    if (r.h !== home.h) f.push(`M5 yükseklik ${r.h} ≠ ana sayfa ${home.h}`);
    if (r.bg !== home.bg) f.push(`M5 arka plan ${r.bg} ≠ ana sayfa ${home.bg}`);
    if (r.label !== home.label) f.push(`M5 etiket "${r.label}" ≠ ana sayfa "${home.label}"`);
  }
  return f;
}

async function main() {
  const a = args(process.argv.slice(2));
  const base = String(process.env.BASE || a.base || 'https://borsapusula.com').replace(/\/$/, '');
  const paths = a._.length ? a._ : PATHS;
  const vps = String(a.vp || '1440x900,390x844,375x667').split(',').map((s) => s.split('x').map(Number));
  const pw = resolveMod('playwright');
  if (!pw) { console.error('playwright bulunamadı (repo ya da ~/Bist ve BTC/Bist30/node_modules)'); process.exit(2); }
  const browser = await pw.chromium.launch();
  const rows = [];
  try {
    for (const [w, h] of vps) {
      const mobile = w < 768;
      const ctx = await browser.newContext({
        viewport: { width: w, height: h }, deviceScaleFactor: mobile ? 2 : 1, isMobile: mobile, hasTouch: mobile,
        userAgent: mobile ? UA.iphone : UA.desk, locale: 'tr-TR', colorScheme: 'dark', timezoneId: 'Europe/Istanbul',
        serviceWorkers: 'block',
      });
      await ctx.addInitScript(() => { try { localStorage.setItem('bp_ga_consent', 'denied'); } catch (e) { /* yok */ } });
      const measure = async (p) => {
        const page = await ctx.newPage();
        let st = 0;
        try { const r = await page.goto(base + p, { waitUntil: 'domcontentloaded', timeout: 45000 }); st = r ? r.status() : 0; } catch (e) { st = -1; }
        let r;
        try { r = await page.evaluate(PROBE, SCROLL); } catch (e) { r = { bar: 0, hata: String(e.message || e).slice(0, 120) }; }
        await page.close();
        return { w, h, p, st, ...r };
      };
      const home = await measure('/');
      for (const p of paths) {
        const r = p === '/' ? home : await measure(p);
        r.fail = judge(r, p === '/' ? null : home);
        rows.push(r);
        const s = r.bar ? `h=${r.h} top→${r.scrolled > 0 ? r.topAfter : '—'} öğe=${r.items} gri=${r.posGrey + r.negGrey}/${r.nPos + r.nNeg} "${r.label}"` : 'ŞERİT YOK';
        console.log(`${r.fail.length ? 'FAIL' : 'ok  '} ${w}x${h} ${p.padEnd(46)} ${String(r.st).padEnd(4)} ${s}${r.fail.length ? '  ← ' + r.fail.join('; ') : ''}`);
      }
      await ctx.close();
    }
  } finally {
    await browser.close();
  }
  const bad = rows.filter((r) => r.fail.length);
  const sc = rows.filter((r) => r.bar && r.scrolled > 0);
  const ozet = {
    base, at: new Date().toISOString(), yuklemeler: rows.length,
    serit_var: rows.filter((r) => r.bar === 1).length,
    sabit: `${sc.filter((r) => Math.abs(r.topAfter) <= 1).length}/${sc.length}`,
    gri: rows.reduce((n, r) => n + (r.posGrey || 0) + (r.negGrey || 0), 0),
    fail: bad.length,
  };
  console.log(`\nÖZET ${JSON.stringify(ozet)}`);
  if (a.out) fs.writeFileSync(String(a.out), JSON.stringify({ ozet, rows }, null, 1));
  process.exit(bad.length ? 1 : 0);
}

main().catch((e) => { console.error('sonda çöktü:', String((e && e.message) || e).split('\n')[0]); process.exit(2); });
