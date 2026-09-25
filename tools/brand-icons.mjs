// C-06: favicon.svg, logo.svg, icon-192/512.png'yi logo v2 A geometrisinden
// (D-54: + assets/brand/mark-256.png ve mark-sade-256.png — saydam zemin, isi haritasi
// paylasim gorseli heatmap_image.py bunlari kucultur; sade = <=32 px kalin surum)
// (templates/_brand.html ile ayni, docs/URUN-VE-TASARIM.md §5.7) uretir.
// Kullanim: NODE_PATH="$HOME/Bist ve BTC/Bist30/node_modules" node tools/brand-icons.mjs
import { mkdirSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const BG = '#0e0e12', UP = '#00e290';
const mark = (small) => `<defs><linearGradient id="bpg" x1="18" y1="18" x2="102" y2="102" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#7c5cff"/><stop offset="1" stop-color="#22d3ee"/></linearGradient></defs><circle cx="60" cy="60" r="44" fill="none" stroke="url(#bpg)" stroke-width="${small ? 11 : 7}" stroke-linecap="round" stroke-dasharray="232 44.5" transform="rotate(-18 60 60)"/><path d="M60 25 C62.8 50.5 69.5 57.2 95 60 C69.5 62.8 62.8 69.5 60 95 C57.2 69.5 50.5 62.8 25 60 C50.5 57.2 57.2 50.5 60 25 Z" fill="url(#bpg)" stroke="url(#bpg)" stroke-width="${small ? 7 : 5}" stroke-linejoin="round"/><circle cx="91.1" cy="28.9" r="${small ? 9 : 6.5}" fill="${UP}"/>`;
// Sekme simgesi: koyu karo (acik sekme cubugunda da okunur) + kalin sade surum
const tile = (small, scale, rx) => `<svg width="120" height="120" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg"><rect width="120" height="120" rx="${rx}" fill="${BG}"/><g transform="translate(${60 - 60 * scale} ${60 - 60 * scale}) scale(${scale})">${mark(small)}</g></svg>\n`;
writeFileSync('static/favicon.svg', tile(true, 1, 26));
writeFileSync('static/logo.svg', `<svg width="120" height="120" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">${mark(false)}</svg>\n`);
// PWA/maskable: tam dolu koyu zemin, isaret %72 (guvenli bolge r<=%40 icinde)
const pwa = tile(false, 0.72, 0);
const b = await chromium.launch();
for (const px of [192, 512]) {
  const p = await b.newPage({ viewport: { width: px, height: px } });
  await p.setContent(`<body style="margin:0">${pwa.replace('width="120" height="120"', `width="${px}" height="${px}"`)}</body>`);
  await p.screenshot({ path: `static/icon-${px}.png`, omitBackground: false });
}
mkdirSync('assets/brand', { recursive: true });
for (const [name, small] of [['mark-256', false], ['mark-sade-256', true]]) {
  const p = await b.newPage({ viewport: { width: 256, height: 256 } });
  await p.setContent(`<body style="margin:0;background:transparent"><svg width="256" height="256" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">${mark(small)}</svg></body>`);
  await p.screenshot({ path: `assets/brand/${name}.png`, omitBackground: true });
}
await b.close();
