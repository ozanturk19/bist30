#!/usr/bin/env node
// C-71 — Kalıcı görsel sonda (görsel denetim 27.09 RAPOR §2). Canlı sitede, ölçerek:
//   K1  halka/gösterge metni merkezde mi (Range kutusu ↔ halka merkezi, |dx|,|dy| ≤ 1,5 px, iç yarıçap içinde)
//   K2  kırpık ve kutu dışı metin: (a) kartın/ekranın dışına taşan metin, (b) üç noktasız kırpma,
//       (c) line-clamp penceresinde yarım satır, (d) "…" ile gizlenen kısımda rakam/%/₺/gün
//   K3  üst üste binen metin kutuları (farklı öğeler, em kutusu kesişimi > 2×2 px)
//   K4  kayan çip satırında (a) kenarda yarım kalmış çip (görünen oran 0–0,6, solma yok),
//       (b) etkin çip tam görünmüyor, (d) sarılan çip satırında son satırda tek çip (WARN)
//   K5  yatay sayfa taşması
//   K6  telefonda dokunma hedefi (etkin alan elementFromPoint ile; < 24 FAIL, < 40 WARN)
//   K7  konsol hatası, pageerror, aynı kaynakta ≥ 400 yanıt, başarısız istek
//   K8  yarı saydam fixed/sticky yüzey (WARN)
//   K9  görünür metin ve JSON-LD biçimi: yüzde sonda (+0,09%), "%-0,75", "25.09 kapanışı" (FAIL);
//       İngilizce/jargon ve UI emojisi (WARN)
//   K11 takılı iskelet ve hata metni (Bağlantı sorunu, alınamadı, yüklenemedi, yükleniyor)
//
// Yalnız GET; siteye hiçbir şey yazmaz. Yeni npm paketi yok: playwright, tools/live/shots.mjs'teki gibi
// repo ya da ~/Bist ve BTC/Bist30/node_modules'tan çözülür.
//
// Kullanım:
//   node tools/live/gorsel-denetim.mjs [--base=https://borsapusula.com] [--sayfa=tarama,hisse-THYAO:temel]
//       [--vp=1440,820,390,320] [--ek-vp=360,700] [--out=~/ops/plans/qa/gorsel-<tarih>/oto]
//       [--kontrol=K1,K2,...] [--inject] [--css='<kural>'] [--yerel-static] [--muafsiz] [--kirpinti=6] [--liste]
//   --inject   pozitif kontrol: her yüklemeye bilinen kusurlar enjekte edilir; biri yakalanmazsa exit 2
//   --css      ölçümden önce sayfaya CSS enjekte et (eski bir hatayı yeniden üretmek ya da düzeltmeyi
//              canlıda denemek için; ör. --css='.tv-tb .c-bp .tv-bp{place-content:normal}' K01'i geri getirir)
//   --yerel-static  canlı HTML'deki /static/* istekleri bu ağaçtaki dosyalardan karşılanır (service worker kapalı):
//              CSS/JS düzeltmesi deploy ÖNCESİ canlı sayfada ölçülür (şablon değişikliği SSR olduğu için kapsanmaz)
//   --muafsiz  tools/live/gorsel-denetim.muaf.json uygulanmaz (açık bulguların hepsi FAIL sayılır)
//   --liste    yapılandırmadaki sayfa:durum adlarını yazar
// Çıktı (--out): <sayfa>__<durum>__<vp>.json · _ozet.json · _ozet.md (PASS/WARN/FAIL tablosu) ·
//   fail__<K>__<sayfa>__<durum>__<vp>__<n>.png (kırmızı çerçeveli, ~3× kırpıntı — Read ile açılıp bakılır)
// Exit: 0 temiz · 1 yalnız WARN · 2 FAIL ya da ölçülemeyen durum (ölçülemeyen durum asla yeşil sayılmaz)
//
// Sayfa × durum matrisi: tools/live/gorsel-denetim.sayfalar.json (halka kaydı da orada).
// Muafiyet: tools/live/gorsel-denetim.muaf.json — {kontrol, sayfa (regex|*), secici (alt dize), metin?,
//   azami?, gerekce, son_tarih}. Süresi geçen kayıt uygulanmaz; azami'yi aşan eşleşmeler FAIL olur (ratchet).
//
// NEREDE KOŞAR (yazılı sözleşme; deploy kapısı DEĞİL — canlı URL ister, ~10–20 dk):
//   1. Akşam QA (scheduled-task borsapusula-qa-aksam §5 "Görsel geometri"): elle ölçüm yerine tam matris
//        NODE_PATH="$HOME/Bist ve BTC/Bist30/node_modules" node tools/live/gorsel-denetim.mjs \
//          --out ~/ops/plans/qa/gorsel-$(date +%F)/oto
//      exit 2 → bulgu; _ozet.md'deki FAIL kırpıntıları Read ile açılır, P1 olarak plana yazılır.
//   2. CPO görsel kabul paketi (borsapusula-cpo-loop 5. adım): görsel madde [x] olmadan önce, deploy
//      sonrası canlıda etkilenen sayfalar için
//        node tools/live/gorsel-denetim.mjs --sayfa=<etkilenen> --out ~/ops/plans/shots/<ID>/gorsel
//      0 FAIL (exit 0 ya da 1) gerekir; K1/K2/K3 değerleri kabul notuna yazılır. Yerelde (deploy öncesi)
//      düzeltmeyi denemek için aynı komut --css='<yeni kural>' ile canlı sayfaya enjekte edilerek koşulur.
//   3. pre-deploy-check.sh: yalnız İSTEĞE BAĞLI adım — GORSEL_DENETIM_BASE tanımlıysa koşar
//      (GORSEL_DENETIM_SAYFA ile daraltılır), tanımsızsa "atlandı" yazar.

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
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

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const today = () => new Date().toLocaleDateString('sv-SE', { timeZone: 'Europe/Istanbul' });
const expandHome = (p) => (p && p.startsWith('~') ? path.join(os.homedir(), p.slice(1)) : p);

function args(argv) {
  const o = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith('--')) { o._.push(a); continue; }
    const eq = a.indexOf('=');
    if (eq > 0) { o[a.slice(2, eq)] = a.slice(eq + 1); continue; }
    const k = a.slice(2), next = argv[i + 1];
    if (next === undefined || next.startsWith('--')) o[k] = true; else { o[k] = next; i++; }
  }
  return o;
}

// ── Bağlamlar (RAPOR §2.2; telefon DPR 3, isMobile, gerçek tarayıcı UA — HeadlessChrome çerez bandını görmez) ──
const UA = {
  desk: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
  ipad: 'Mozilla/5.0 (iPad; CPU OS 18_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Mobile/15E148 Safari/604.1',
  iphone: 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Mobile/15E148 Safari/604.1',
};
function profile(w) {
  if (w >= 1024) return { viewport: { width: w, height: 900 }, deviceScaleFactor: 1, isMobile: false, hasTouch: false, userAgent: UA.desk };
  if (w >= 768) return { viewport: { width: w, height: 1180 }, deviceScaleFactor: 2, isMobile: false, hasTouch: false, userAgent: UA.ipad };
  return { viewport: { width: w, height: w <= 340 ? 640 : 844 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true, userAgent: UA.iphone };
}

const ALL_K = ['K1', 'K2', 'K3', 'K4', 'K5', 'K6', 'K7', 'K8', 'K9', 'K11'];
const JARGON = ['analytics', '(EOD)', 'Trend Gate', 'TL;DR', 'Cloud Sync', 'localStorage', 'canlı gör', ' AND ', 'long-only'];

// ── Sayfa içi ölçüm (tek evaluate; sayfa betiği değil, tarayıcıda koşar) ──────────────────────────────────────
const PROBE = (opt) => {
  const de = document.documentElement, vw = de.clientWidth, vh = innerHeight, SY = scrollY;
  const out = [], errors = [], stats = {};
  const has = (k) => opt.kontrol.includes(k);
  const CS = new Map();
  const cs = (el) => { let s = CS.get(el); if (!s) { s = getComputedStyle(el); CS.set(el, s); } return s; };
  const r1 = (v) => Math.round(v * 10) / 10;
  const visible = (el) => {
    if (!el || !el.isConnected) return false;
    if (el.checkVisibility) return el.checkVisibility({ opacityProperty: true, visibilityProperty: true, checkOpacity: true, checkVisibilityCSS: true });
    const s = cs(el); return s.display !== 'none' && s.visibility !== 'hidden' && s.opacity !== '0';
  };
  const desc = (el) => {
    if (!el || !el.tagName) return '?';
    const one = (e) => {
      const c = (e.className && e.className.baseVal !== undefined) ? e.className.baseVal : (e.className || '');
      return e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + String(c).trim().split(/\s+/).filter(Boolean).slice(0, 2).map((x) => '.' + x).join('');
    };
    const p = el.parentElement;
    return (p && p !== document.body ? one(p) + ' > ' : '') + one(el);
  };
  const injOf = (el) => { const x = el && el.closest && (el.closest('[id^="__gd_inj_"]') || el.closest('#__gd_inj')); return x ? x.id : null; };
  const fixedC = new Map();
  const isFixed = (el) => {
    if (!el || el === de || el === document.body) return false;
    if (fixedC.has(el)) return fixedC.get(el);
    const v = cs(el).position === 'fixed' || isFixed(el.parentElement);
    fixedC.set(el, v); return v;
  };
  const animC = new Map();
  const animated = (el) => {
    if (!el || el === de) return false;
    if (animC.has(el)) return animC.get(el);
    const v = (cs(el).animationName && cs(el).animationName !== 'none') || animated(el.parentElement);
    animC.set(el, v); return v;
  };
  const snippet = (el) => ((el && (el.innerText || el.textContent || (el.getAttribute && el.getAttribute('aria-label')))) || '').replace(/\s+/g, ' ').trim().slice(0, 48);
  const add = (k, sev, el, r, detail) => out.push({
    k, sev, sel: desc(el), inj: injOf(el), text: snippet(el),
    rect: r ? { x: r1(r.left), y: r1(r.top + SY), vy: r1(r.top), w: r1(r.width || (r.right - r.left)), h: r1(r.height || (r.bottom - r.top)) } : null,
    fixed: isFixed(el), detail: detail || {},
  });
  const guard = (k, fn) => { try { fn(); } catch (e) { errors.push(k + ': ' + String(e && e.message || e).slice(0, 160)); } };

  // Kırpma kutusu: öğe + atalarının overflow≠visible padding kutularının kesişimi (html/body hariç; fixed kökü sıfırlar).
  const ROOT = { l: -Infinity, t: -Infinity, r: Infinity, b: Infinity, lEl: null, rEl: null, tEl: null, bEl: null };
  const CC = new Map();
  const clipFor = (el) => {
    if (!el || el === document.body || el === de) return ROOT;
    if (CC.has(el)) return CC.get(el);
    const s = cs(el);
    let c = s.position === 'fixed' ? ROOT : clipFor(el.parentElement);
    if (s.overflowX !== 'visible' || s.overflowY !== 'visible') {
      const b = el.getBoundingClientRect();
      const pb = { l: b.left + parseFloat(s.borderLeftWidth), r: b.right - parseFloat(s.borderRightWidth), t: b.top + parseFloat(s.borderTopWidth), b: b.bottom - parseFloat(s.borderBottomWidth) };
      c = { ...c };
      if (s.overflowX !== 'visible') {
        if (pb.l > c.l) { c.l = pb.l; c.lEl = el; }
        if (pb.r < c.r) { c.r = pb.r; c.rEl = el; }
      }
      if (s.overflowY !== 'visible') {
        if (pb.t > c.t) { c.t = pb.t; c.tEl = el; }
        if (pb.b < c.b) { c.b = pb.b; c.bEl = el; }
      }
    }
    CC.set(el, c); return c;
  };
  const scrolls = (el, ax) => el && /auto|scroll/.test(ax === 'x' ? cs(el).overflowX : cs(el).overflowY);
  const inter = (r, c) => {
    const l = Math.max(r.left, c.l), t = Math.max(r.top, c.t), rr = Math.min(r.right, c.r), b = Math.min(r.bottom, c.b);
    return (rr - l > 0.5 && b - t > 0.5) ? { left: l, top: t, right: rr, bottom: b, width: rr - l, height: b - t } : null;
  };

  // Metin düğümleri (görünür, boş olmayan).
  const items = [];
  guard('metin', () => {
    const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
      acceptNode(n) {
        if (!n.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
        const p = n.parentElement;
        if (!p || p.closest('script,style,noscript,template,title')) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      },
    });
    const rg = document.createRange();
    let n;
    while ((n = tw.nextNode())) {
      const el = n.parentElement;
      if (!visible(el)) continue;
      const own = el.getBoundingClientRect();
      if (own.width <= 1 || own.height <= 1) continue; // sr-only
      rg.selectNodeContents(n);
      const rects = [...rg.getClientRects()].filter((r) => r.width > 0.5 && r.height > 0.5);
      if (rects.length) items.push({ n, el, rects, fs: parseFloat(cs(el).fontSize) || 14 });
    }
  });
  const allEls = [...document.body.querySelectorAll('*')];

  // ── K1 halka metni merkezi ──
  if (has('K1')) guard('K1', () => {
    const hosts = new Map();
    for (const h of opt.halkalar || []) for (const el of document.querySelectorAll(h.secici)) if (!hosts.has(el)) hosts.set(el, h);
    const inHost = (el) => { for (const h of hosts.keys()) if (h.contains(el)) return true; return false; };
    for (const svg of document.querySelectorAll('svg')) {
      if (!svg.querySelector('circle') || inHost(svg) || !svg.parentElement) continue;
      const b = svg.getBoundingClientRect();
      if (Math.abs(b.width - b.height) <= 2 && b.width >= 16 && b.width <= 120) hosts.set(svg.parentElement, { auto: 'svg' });
    }
    const pctR = (s, w) => { const v = parseFloat(s.borderTopLeftRadius); return /%/.test(s.borderTopLeftRadius) ? v >= 50 : v >= w / 2 - 1; };
    for (const el of allEls) {
      if (hosts.has(el) || inHost(el)) continue;
      const b = el.getBoundingClientRect();
      if (Math.abs(b.width - b.height) > 2 || b.width < 16 || b.width > 120) continue;
      const s = cs(el);
      let ring = pctR(s, b.width) && (parseFloat(s.borderTopWidth) >= 2 || /conic-gradient/.test(s.backgroundImage));
      if (!ring) for (const ps of ['::before', '::after']) {
        const p = getComputedStyle(el, ps);
        if (p.content !== 'none' && /conic-gradient/.test(p.backgroundImage) && pctR(p, b.width)) { ring = true; break; }
      }
      if (ring) hosts.set(el, { auto: 'css' });
    }
    const rg = document.createRange();
    stats.halka = 0;
    for (const [host, reg] of hosts) {
      if (!visible(host)) continue;
      const hb = host.getBoundingClientRect();
      let cx, cy, rOut, rIn;
      const circles = [...host.querySelectorAll('svg circle')];
      if (circles.length) {
        const c = circles.reduce((a, x) => (x.r.baseVal.value > a.r.baseVal.value ? x : a));
        const svg = c.ownerSVGElement, sb = svg.getBoundingClientRect();
        if (sb.width < 8 || Math.abs(sb.width - sb.height) > 2) continue;
        const vb = svg.viewBox && svg.viewBox.baseVal && svg.viewBox.baseVal.width ? svg.viewBox.baseVal : { x: 0, y: 0, width: sb.width, height: sb.height };
        const k = sb.width / vb.width;
        cx = sb.left + (c.cx.baseVal.value - vb.x) * k; cy = sb.top + (c.cy.baseVal.value - vb.y) * k;
        const sw = Math.max(...circles.map((x) => parseFloat(getComputedStyle(x).strokeWidth) || 0)) * k;
        rOut = c.r.baseVal.value * k + sw / 2; rIn = c.r.baseVal.value * k - sw / 2;
      } else {
        if (Math.abs(hb.width - hb.height) > 2 || hb.width < 16 || hb.width > 120) continue;
        const s = cs(host);
        cx = hb.left + hb.width / 2; cy = hb.top + hb.height / 2; rOut = Math.min(hb.width, hb.height) / 2;
        rIn = rOut - (reg.cizgi || parseFloat(s.borderTopWidth) || 4);
      }
      const scope = reg.metin ? host.querySelector(reg.metin) : host;
      if (!scope) continue;
      let u = null, digits = '', fs = 14;
      const tw = document.createTreeWalker(scope, NodeFilter.SHOW_TEXT);
      let n;
      while ((n = tw.nextNode())) {
        if (!/\d/.test(n.nodeValue) || !visible(n.parentElement)) continue;
        rg.selectNodeContents(n);
        const b = rg.getBoundingClientRect();
        if (b.width < 0.5) continue;
        digits += n.nodeValue.trim(); fs = parseFloat(cs(n.parentElement).fontSize) || fs;
        u = u ? { left: Math.min(u.left, b.left), top: Math.min(u.top, b.top), right: Math.max(u.right, b.right), bottom: Math.max(u.bottom, b.bottom) } : { left: b.left, top: b.top, right: b.right, bottom: b.bottom };
      }
      if (!u || !/^\D*\d{1,3}\D*$/.test(digits)) continue;
      const tcx = (u.left + u.right) / 2, tcy = (u.top + u.bottom) / 2;
      const dx = tcx - cx, dy = tcy - cy;
      // Otomatik keşifte (kayıtsız) metin halkanın içinde olmalı: yanındaki "ikon + sayı" deseni halka metni değildir.
      if (reg.auto && !(u.right > cx - rOut && u.left < cx + rOut && u.bottom > cy - rOut && u.top < cy + rOut)) continue;
      stats.halka++;
      stats.halkaMaksDx = Math.max(stats.halkaMaksDx || 0, r1(Math.abs(dx))); stats.halkaMaksDy = Math.max(stats.halkaMaksDy || 0, r1(Math.abs(dy)));
      // Köşe: Range genişliği × rakam yüksekliği (≈ 0,72 em) — Range'in satır yüksekliği payı halka çizgisine sayılmaz.
      const corner = Math.hypot(Math.abs(dx) + (u.right - u.left) / 2, Math.abs(dy) + fs * 0.36);
      const d = { dx: r1(dx), dy: r1(dy), kose: r1(corner), icYaricap: r1(rIn), metin: digits, kayit: reg.secici || 'oto-' + reg.auto };
      const box = { left: cx - rOut, top: cy - rOut, width: rOut * 2, height: rOut * 2 };
      if (Math.abs(dx) > 1.5 || Math.abs(dy) > 1.5 || corner > rIn + 0.5) add('K1', 'FAIL', host, box, d);
      else if (Math.abs(dx) > 1.0 || Math.abs(dy) > 1.0) add('K1', 'WARN', host, box, d);
    }
  });

  // ── K2 kırpık ve kutu dışı metin ──
  if (has('K2')) guard('K2', () => {
    const contC = new Map();
    const visualBox = (el) => { // en yakın görsel kap: arka plan, kenarlık ya da gölge; inline değil
      if (!el || el === document.body || el === de) return null;
      if (contC.has(el)) return contC.get(el);
      const s = cs(el);
      let v = null;
      if (s.position === 'fixed') v = null;
      else {
        const bg = s.backgroundColor.match(/[\d.]+/g);
        const hasBg = (bg && (bg.length < 4 || parseFloat(bg[3]) > 0.05)) || s.backgroundImage !== 'none';
        const hasBd = ['Top', 'Right', 'Bottom', 'Left'].some((x) => parseFloat(s['border' + x + 'Width']) > 0 && s['border' + x + 'Style'] !== 'none');
        const blockish = !/^(inline|contents)$/.test(s.display) && el.tagName !== 'svg' && !(el instanceof SVGElement);
        v = (blockish && (hasBg || hasBd)) ? el : visualBox(el.parentElement);
      }
      contC.set(el, v); return v;
    };
    const clampEls = new Set();
    const rg = document.createRange();
    for (const it of items) {
      if (animated(it.el) || it.el.closest('svg')) continue;
      const c = clipFor(it.el);
      for (const r of it.rects) {
        // (b)/(d) kırpma kenarını yarıp geçen metin
        const edges = [
          ['r', r.right > c.r + 1 && r.left < c.r - 1, c.rEl, 'x'],
          ['l', r.left < c.l - 1 && r.right > c.l + 1, c.lEl, 'x'],
          ['b', r.bottom > c.b + 1 && r.top < c.b - 1, c.bEl, 'y'],
          ['t', r.top < c.t - 1 && r.bottom > c.t + 1, c.tEl, 'y'],
        ];
        let clipped = false;
        for (const [side, hit, clipEl, ax] of edges) {
          if (!hit || !clipEl || scrolls(clipEl, ax)) continue;
          // Arada gerçekten kayan bir kap varsa içerik erişilebilir (yarım çip K4'ün işi).
          let reach = false;
          for (let p = it.el; p && p !== clipEl; p = p.parentElement) {
            if (scrolls(p, ax) && (ax === 'x' ? p.scrollWidth > p.clientWidth + 1 : p.scrollHeight > p.clientHeight + 1)) { reach = true; break; }
          }
          if (reach) { clipped = true; continue; }
          const cb = clipEl.getBoundingClientRect();
          if (cb.width <= 2 || cb.height <= 2) continue; // sr-only kutusu
          clipped = true;
          const s = cs(clipEl);
          if (ax === 'y' && s.webkitLineClamp && s.webkitLineClamp !== 'none') { clampEls.add(clipEl); continue; }
          if (ax === 'x' && s.textOverflow === 'ellipsis') {
            // (d) gizli kısımda anlamlı içerik var mı (ikili arama ile ilk taşan karakter)
            const txt = it.n.nodeValue;
            let lo = 0, hi = txt.length;
            while (lo < hi) { const m = (lo + hi) >> 1; rg.setStart(it.n, 0); rg.setEnd(it.n, m + 1); if (rg.getBoundingClientRect().right > c.r + 0.5) hi = m; else lo = m + 1; }
            const hidden = txt.slice(lo).trim();
            if (/[\d%₺]|\bgün\b|temettü|bilanço|genel kurul/i.test(hidden)) add('K2d', 'FAIL', it.el, r, { gizli: hidden.slice(0, 40), kap: desc(clipEl) });
            continue;
          }
          add('K2b', 'FAIL', it.el, r, { kenar: side, tasma: r1(side === 'r' ? r.right - c.r : side === 'l' ? c.l - r.left : side === 'b' ? r.bottom - c.b : c.t - r.top), kap: desc(clipEl) });
        }
        if (clipped) continue;
        const v = inter(r, c);
        if (!v) continue;
        // (a) ekran kenarını yarıp geçen, kaydırılamayan metin (Kapı 83 sınıfı)
        if (!isFixed(it.el) && ((v.right > vw + 1 && v.left < vw - 1) || (v.left < -1 && v.right > 1))) {
          add('K2a', 'FAIL', it.el, v, { kap: 'ekran', tasma: r1(Math.max(v.right - vw, -v.left)) });
          continue;
        }
        // (a) görsel kabın (kart/çip) dışına taşan metin
        const box = visualBox(it.el);
        if (box) {
          const bb = box.getBoundingClientRect();
          const ox = Math.max(bb.left - v.left, v.right - bb.right);
          if (ox > 1) add('K2a', 'FAIL', it.el, v, { kap: desc(box), tasma: r1(ox) });
        }
      }
    }
    // (c) line-clamp penceresi: kırpılan ilk satırın padding kutusunda görünen kısmı
    for (const el of clampEls) {
      const n = parseInt(cs(el).webkitLineClamp, 10);
      if (!n) continue;
      rg.selectNodeContents(el);
      const tops = [];
      for (const r of rg.getClientRects()) if (r.height > 1 && !tops.some((t) => Math.abs(t - r.top) < r.height / 2)) tops.push(r.top);
      tops.sort((a, b) => a - b);
      if (tops.length <= n) continue;
      const b = el.getBoundingClientRect();
      const vis = (b.bottom - parseFloat(cs(el).borderBottomWidth)) - tops[n];
      if (vis > 0.5) add('K2c', 'FAIL', el, b, { gorunenFazlaSatir: r1(vis), satir: n });
    }
  });

  // ── K3 üst üste binen metin ──
  if (has('K3')) guard('K3', () => {
    const L = [];
    for (const it of items) {
      if (isFixed(it.el) || animated(it.el)) continue;
      const c = clipFor(it.el);
      for (const r of it.rects) {
        const v = inter(r, c);
        if (!v) continue;
        const mid = (r.top + r.bottom) / 2, half = Math.min(r.height, it.fs) / 2; // em kutusu (satır yüksekliği payı yok)
        const t = Math.max(v.top, mid - half), b = Math.min(v.bottom, mid + half);
        if (b - t > 0.5) L.push({ it, l: v.left, r: v.right, t, b });
      }
    }
    L.sort((a, b) => a.t - b.t);
    const seen = new Set();
    // Opak bir katmanın (açılır panel, popover, yapışkan çubuk) üstündeki metin altındakini örter: çakışma değil.
    const covers = (el, r, other) => {
      let opaque = false;
      for (let p = el; p && p !== document.body; p = p.parentElement) {
        if (p.contains(other)) return false;
        const s = cs(p);
        if (!opaque) {
          const m = s.backgroundColor.match(/[\d.]+/g);
          const al = m ? (m.length >= 4 ? parseFloat(m[3]) : 1) : 0;
          if (al >= 0.99 || s.backgroundImage !== 'none') {
            const b = p.getBoundingClientRect();
            if (b.left <= r.l + 1 && b.right >= r.r - 1 && b.top <= r.t + 1 && b.bottom >= r.b - 1) opaque = true;
          }
        }
        if (opaque && (/absolute|fixed|sticky/.test(s.position) || (s.position === 'relative' && s.zIndex !== 'auto'))) return true;
      }
      return false;
    };
    for (let i = 0; i < L.length; i++) {
      const a = L[i];
      for (let j = i + 1; j < L.length && L[j].t < a.b - 2; j++) {
        const b = L[j];
        if (a.it.el === b.it.el || a.it.el.contains(b.it.el) || b.it.el.contains(a.it.el)) continue;
        const w = Math.min(a.r, b.r) - Math.max(a.l, b.l), h = Math.min(a.b, b.b) - Math.max(a.t, b.t);
        if (w <= 2 || h <= 2) continue;
        const ir = { l: Math.max(a.l, b.l), r: Math.min(a.r, b.r), t: Math.max(a.t, b.t), b: Math.min(a.b, b.b) };
        if (covers(a.it.el, ir, b.it.el) || covers(b.it.el, ir, a.it.el)) continue;
        const key = desc(a.it.el) + '|' + desc(b.it.el) + '|' + Math.round(a.t);
        if (seen.has(key)) continue;
        seen.add(key);
        const u = { left: Math.min(a.l, b.l), top: Math.min(a.t, b.t), right: Math.max(a.r, b.r), bottom: Math.max(a.b, b.b) };
        u.width = u.right - u.left; u.height = u.bottom - u.top;
        add('K3', 'FAIL', a.it.el, u, { diger: desc(b.it.el), digerMetin: b.it.n.nodeValue.trim().slice(0, 30), kesisim: r1(w) + '×' + r1(h) });
      }
    }
  });

  // ── K4 çip satırları ──
  if (has('K4')) guard('K4', () => {
    const ACT = '[aria-pressed="true"],[aria-current]:not([aria-current="false"]),[aria-selected="true"],.on,.active,.is-active';
    const faded = (el) => {
      for (let p = el, i = 0; p && i < 3; p = p.parentElement, i++) {
        const s = cs(p);
        if ((s.maskImage && s.maskImage !== 'none') || (s.webkitMaskImage && s.webkitMaskImage !== 'none')) return true;
        for (const ps of ['::before', '::after']) { const q = getComputedStyle(p, ps); if (q.content !== 'none' && /gradient/.test(q.backgroundImage) && /absolute|fixed|sticky/.test(q.position)) return true; }
      }
      return false;
    };
    // Kenarda yarıp geçen metin var mı (ör. "3 Bila", "St"); hücre sınırından temiz kesilen grup (takvim haftası) yarım parça değildir.
    const rgc = document.createRange();
    const cutText = (k, L, R) => {
      const tw = document.createTreeWalker(k, NodeFilter.SHOW_TEXT);
      let n;
      while ((n = tw.nextNode())) {
        if (!n.nodeValue.trim()) continue;
        rgc.selectNodeContents(n);
        for (const r of rgc.getClientRects()) if ((r.left < L - 1 && r.right > L + 1) || (r.left < R - 1 && r.right > R + 1)) return true;
      }
      return false;
    };
    for (const el of allEls) {
      const s = cs(el);
      if (/auto|scroll/.test(s.overflowX) && el.scrollWidth > el.clientWidth + 1 && el.clientHeight < 140 && visible(el)) {
        let kids = [...el.children].filter(visible);
        if (kids.length === 1 && kids[0].children.length >= 2) kids = [...kids[0].children].filter(visible);
        if (kids.length < 2) continue;
        const b = el.getBoundingClientRect();
        const L = Math.max(b.left + parseFloat(s.borderLeftWidth), 0), R = Math.min(b.right - parseFloat(s.borderRightWidth), vw);
        const fade = faded(el);
        for (const k of kids) {
          const kb = k.getBoundingClientRect();
          if (kb.width < 4) continue;
          const frac = Math.max(0, Math.min(kb.right, R) - Math.max(kb.left, L)) / kb.width;
          const act = k.matches(ACT) ? k : k.querySelector(ACT);
          let afrac = 1, ab = null;
          if (act && visible(act)) {
            ab = act.getBoundingClientRect();
            if (ab.width >= 4) afrac = Math.max(0, Math.min(ab.right, R) - Math.max(ab.left, L)) / ab.width;
          }
          if (act && afrac < 0.98) add('K4b', 'FAIL', act, ab, { gorunen: Math.round(afrac * 100) + '%', kap: desc(el) });
          else if (frac > 0 && frac < 0.6 && !fade && cutText(k, L, R)) add('K4a', 'FAIL', k, kb, { gorunen: Math.round(frac * 100) + '%', kap: desc(el) });
        }
      } else if (s.display.includes('flex') && s.flexWrap === 'wrap' && el.children.length >= 3 && visible(el)) {
        const kids = [...el.children].filter((k) => visible(k) && k.getBoundingClientRect().height < 60 && cs(k).position !== 'absolute');
        if (kids.length < 3) continue;
        const tops = [];
        for (const k of kids) { const t = k.getBoundingClientRect().top; const row = tops.find((x) => Math.abs(x.t - t) < 4); if (row) row.n++; else tops.push({ t, n: 1, k }); }
        if (tops.length >= 2) {
          tops.sort((a, b) => a.t - b.t);
          const last = tops[tops.length - 1];
          if (last.n === 1) add('K4d', 'WARN', last.k, last.k.getBoundingClientRect(), { satir: tops.length, kap: desc(el) });
        }
      }
    }
  });

  // ── K5 yatay taşma ──
  if (has('K5')) guard('K5', () => {
    const d = de.scrollWidth - de.clientWidth;
    if (d > 0) add('K5', 'FAIL', de, { left: 0, top: 0, width: vw, height: 1 }, { tasma: d });
  });

  // ── K8 yarı saydam krom ──
  if (has('K8')) guard('K8', () => {
    for (const el of allEls) {
      const s = cs(el);
      if (s.position !== 'fixed' && s.position !== 'sticky') continue;
      const b = el.getBoundingClientRect();
      if (b.width < 40 || b.height < 20 || !visible(el)) continue;
      const m = s.backgroundColor.match(/[\d.]+/g);
      const a = m && m.length >= 4 ? parseFloat(m[3]) : 1;
      if (a > 0 && a < 1 && (!s.backdropFilter || s.backdropFilter === 'none') && s.backgroundImage === 'none') add('K8', 'WARN', el, b, { alfa: a });
    }
  });

  // ── K9 görünür metin ve JSON-LD biçimi ──
  if (has('K9')) guard('K9', () => {
    // Blok başına yalnız kendi satır içi metni (iç bloklar ayrı sayılır; "+0,09" + "%" ayrı span'lerde olsa da birleşir).
    const blocks = new Map();
    for (const it of items) {
      if (it.el.closest('svg,pre,code,.formula-box')) continue;
      let b = it.el;
      while (b.parentElement && /^(inline|contents)$/.test(cs(b).display)) b = b.parentElement;
      blocks.set(b, (blocks.get(b) || '') + it.n.nodeValue);
    }
    const dedup = new Set();
    const add9 = (sev, b, r, d) => { const key = desc(b) + '|' + d.kural + '|' + d.bulunan; if (dedup.has(key)) return; dedup.add(key); add('K9', sev, b, r, d); };
    const RULES = [
      ['FAIL', 'yuzde-sonda', /(^|[^\w%,.])([+\-−]?\d+(?:[.,]\d+)?\s?%)(?![\d\wçğıöşü])/],
      ['FAIL', 'yuzde-eksi', /%-\d/],
      ['FAIL', 'kisa-tarih-kapanis', /\b\d{2}\.\d{2} kapanışı/],
    ];
    const emo = /(?![©®™])\p{Extended_Pictographic}/u;
    for (const [b, raw] of blocks) {
      const t = raw.replace(/\s+/g, ' ');
      if (!t.trim()) continue;
      for (const [sev, ad, re] of RULES) { const m = t.match(re); if (m) add9(sev, b, b.getBoundingClientRect(), { kural: ad, bulunan: t.slice(Math.max(0, m.index - 12), m.index + m[0].length + 8).trim() }); }
      for (const j of opt.jargon) if (t.includes(j)) add9('WARN', b, b.getBoundingClientRect(), { kural: 'jargon', bulunan: j.trim() });
      if (!b.closest('article, .prose, .blog-body, .art-body')) {
        const m = t.match(emo);
        if (m) add9('WARN', b, b.getBoundingClientRect(), { kural: 'emoji', bulunan: m[0] });
      }
    }
    for (const s of document.querySelectorAll('script[type="application/ld+json"]')) {
      const t = s.textContent || '';
      for (const [sev, ad, re] of RULES) { const m = t.match(re); if (m) add('K9', sev, s, null, { kural: ad + ' (JSON-LD)', bulunan: t.slice(Math.max(0, m.index - 20), m.index + m[0].length + 10) }); }
    }
  });

  // ── K11 takılı iskelet ve hata metni ──
  if (has('K11')) guard('K11', () => {
    for (const el of document.querySelectorAll('.da-skel, .skeleton, [aria-busy="true"]')) {
      const b = el.getBoundingClientRect();
      if (b.width > 2 && b.height > 2 && visible(el)) add('K11', 'FAIL', el, b, { tur: 'iskelet' });
    }
    const re = /Bağlantı sorunu|alınamadı|alınamıyor|yüklenemedi|[Yy]ükleniyor/;
    const seen = new Set();
    for (const it of items) {
      const t = it.n.nodeValue;
      if (!re.test(t) || seen.has(it.el)) continue;
      seen.add(it.el);
      add('K11', 'FAIL', it.el, it.rects[0], { tur: 'metin', bulunan: t.trim().slice(0, 60) });
    }
  });

  stats.metin = items.length; stats.oge = allEls.length;
  return { vw, vh, findings: out, errors, stats };
};

// ── K6 dokunma hedefi (yalnız telefon): sayfa kaydırılarak her hedef görünür alanda ölçülür ──
const TAP = async (opt) => {
  const SEL = 'a[href],button,input:not([type=hidden]),select,textarea,summary,[role=button],[role=tab],[role=link],[role=checkbox],[role=switch],[tabindex="0"]';
  const vis = (el) => (el.checkVisibility ? el.checkVisibility({ opacityProperty: true, visibilityProperty: true, checkOpacity: true, checkVisibilityCSS: true }) : true);
  const one = (e) => {
    const c = (e.className && e.className.baseVal !== undefined) ? e.className.baseVal : (e.className || '');
    return e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + String(c).trim().split(/\s+/).filter(Boolean).slice(0, 2).map((x) => '.' + x).join('');
  };
  const desc = (el) => (el.parentElement && el.parentElement !== document.body ? one(el.parentElement) + ' > ' : '') + one(el);
  const fixed = (el) => { for (let p = el; p && p !== document.documentElement; p = p.parentElement) if (getComputedStyle(p).position === 'fixed') return true; return false; };
  const prose = (el) => { // düzyazı içindeki satır içi bağlantı (WCAG 2.5.8 istisnası)
    if (el.tagName !== 'A' || !/^inline/.test(getComputedStyle(el).display) || getComputedStyle(el).display === 'inline-block') return false;
    const p = el.parentElement;
    return !!p && [...p.childNodes].some((n) => n !== el && n.nodeType === 3 && /[A-Za-zÇĞİÖŞÜçğıöşü]{2}/.test(n.nodeValue));
  };
  const exempt = (el) => prose(el) || el.matches(opt.muafSecici || '.hm-t') || el.closest('[aria-hidden="true"]') || el.getAttribute('tabindex') === '-1';
  const cands = [...document.querySelectorAll(SEL)].filter((el) => {
    if (el.disabled || !vis(el)) return false;
    const r = el.getBoundingClientRect();
    return r.width > 1 && r.height > 1 && !exempt(el);
  });
  const mine = (el, hit) => !!hit && (hit === el || el.contains(hit) || (el.labels && [...el.labels].some((l) => l === hit || l.contains(hit))));
  const raf = () => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
  const res = new Map();
  const H = Math.min(document.documentElement.scrollHeight, 40000);
  const step = Math.max(200, Math.round(innerHeight * 0.5));
  const CAP = 30;
  for (let y = 0; ; y += step) {
    window.scrollTo(0, y);
    await raf();
    for (const el of cands) {
      const prev = res.get(el);
      if (prev && Math.min(prev.w, prev.h) >= 40) continue; // en iyi konum yeterli; yoksa her kaydırma konumunda yeniden ölç
      const r = el.getBoundingClientRect();
      const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
      if (cy < 1 || cy >= innerHeight - 1 || cx < 1 || cx >= innerWidth - 1) continue;
      if (!mine(el, document.elementFromPoint(cx, cy))) continue;
      const walk = (ddx, ddy) => {
        let i = 1;
        for (; i <= CAP; i++) {
          const x = cx + ddx * i, yy = cy + ddy * i;
          if (x < 0 || x >= innerWidth || yy < 0 || yy >= innerHeight) break;
          if (!mine(el, document.elementFromPoint(x, yy))) break;
        }
        return i - 1;
      };
      const w = walk(-1, 0) + walk(1, 0) + 1, h = walk(0, -1) + walk(0, 1) + 1;
      if (prev && Math.min(prev.w, prev.h) >= Math.min(w, h)) continue;
      res.set(el, { w, h, rect: { x: Math.round(r.left), y: Math.round(r.top + scrollY), vy: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height) } });
    }
    if (y + innerHeight >= H) break;
  }
  window.scrollTo(0, 0);
  const out = [];
  for (const [el, m] of res) {
    const mn = Math.min(m.w, m.h);
    if (mn >= 40) continue;
    const inj = el.closest('[id^="__gd_inj_"]');
    out.push({ k: 'K6', sev: mn < 24 ? 'FAIL' : 'WARN', sel: desc(el), inj: inj ? inj.id : null,
      text: ((el.innerText || el.getAttribute('aria-label') || el.value || '') + '').replace(/\s+/g, ' ').trim().slice(0, 48),
      rect: m.rect, fixed: fixed(el), detail: { etkin: m.w + '×' + m.h } });
  }
  return { findings: out, measured: res.size, unmeasured: cands.length - res.size };
};

// ── Pozitif kontrol: bilinen kusurlar (RAPOR §2.5) ──
const INJECT = (mobile) => {
  const host = document.createElement('div');
  host.id = '__gd_inj';
  host.style.cssText = 'position:relative;padding:12px;display:block;font:14px/1.3 sans-serif;color:#eee';
  host.innerHTML = ''
    + '<div id="__gd_inj_k1" style="width:40px;height:40px;border-radius:50%;border:4px solid #3c3;display:inline-flex;align-items:center;justify-content:flex-end;box-sizing:border-box;font:700 14px sans-serif">87</div>'
    + '<div id="__gd_inj_k2a" style="width:120px;background:#223;padding:4px;margin-top:8px"><span style="white-space:nowrap">FİNANSALLAR DEĞERLEME UZUN</span></div>'
    + '<div id="__gd_inj_k2b" style="width:120px;overflow:hidden;white-space:nowrap;margin-top:8px">Kesik metin üç noktasız uzun satır</div>'
    + '<div id="__gd_inj_k2c" style="display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden;padding:6px 0;width:150px;line-height:16px;font-size:14px;margin-top:8px">Bir iki üç dört beş altı yedi sekiz dokuz on on bir on iki on üç on dört on beş on altı on yedi</div>'
    + '<div style="position:relative;height:24px;margin-top:8px"><span id="__gd_inj_k3" style="position:absolute;left:0;top:0">28 Ağustos</span><span style="position:absolute;left:30px;top:2px">Özel durum</span></div>'
    + '<div id="__gd_inj_k4" style="display:flex;gap:8px;overflow-x:auto;width:200px;margin-top:8px">'
    + '<span style="flex:none;width:90px;background:#333">Birinci</span><span style="flex:none;width:90px;background:#333">İkinci</span>'
    + '<span style="flex:none;width:90px;background:#333">Üçüncü</span><span aria-pressed="true" style="flex:none;width:90px;background:#333">Etkin</span></div>'
    + (mobile ? '<button id="__gd_inj_k6" type="button" style="width:16px;height:16px;padding:0;margin:20px;font-size:10px">x</button>' : '')
    + '<p id="__gd_inj_k9" style="margin-top:8px">Değişim +0,09% oldu</p>'
    + '<div id="__gd_inj_k11" class="da-skel" style="width:100px;height:12px;background:#333;margin-top:8px"></div>'
    + '<div id="__gd_inj_k8" style="position:fixed;left:0;top:45%;width:100px;height:30px;background:rgba(0,0,0,.5);z-index:5"></div>';
  const main = document.querySelector('main') || document.body;
  main.insertBefore(host, main.firstChild);
  console.error('__gd_inj_k7 pozitif kontrol konsol hatası');
  return ['K1', 'K2a', 'K2b', 'K2c', 'K3', 'K4a', 'K4b', ...(mobile ? ['K6'] : []), 'K7', 'K8', 'K9', 'K11'];
};
const INJ_ID = { K1: '__gd_inj_k1', K2a: '__gd_inj_k2a', K2b: '__gd_inj_k2b', K2c: '__gd_inj_k2c', K3: '__gd_inj_k3', K4a: '__gd_inj_k4', K4b: '__gd_inj_k4', K6: '__gd_inj_k6', K8: '__gd_inj_k8', K9: '__gd_inj_k9', K11: '__gd_inj_k11' };

// ── Yapılandırma ──────────────────────────────────────────────────────────────────────────────────────────
function loadJson(p, fallback) { try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch (e) { if (fallback !== undefined) return fallback; throw e; } }

async function resolvePath(base, yol, cache) {
  // "{api:/api/haberler|items[?onem].href}" → çalışma anında API'den (yalnız GET)
  const m = /\{api:([^|}]+)\|([^}]+)\}/.exec(yol);
  if (!m) return yol;
  if (!cache[m[1]]) { const r = await fetch(base + m[1], { headers: { 'User-Agent': UA.desk } }); cache[m[1]] = await r.json(); }
  let v = cache[m[1]];
  for (const part of m[2].split('.')) {
    if (v == null) break;
    const q = /^(\w+)\[\?(\w+)\]$/.exec(part);
    if (q) { v = (v[q[1]] || []).find((x) => x && x[q[2]]); continue; }
    v = /^\d+$/.test(part) ? v[Number(part)] : v[part];
  }
  if (typeof v !== 'string') throw new Error('çözülemedi: ' + yol);
  return yol.replace(m[0], v);
}

function muafMatch(muaf, page, f) {
  for (const m of muaf) {
    if (!f.k.startsWith(m.kontrol)) continue;
    if (m.sayfa && m.sayfa !== '*' && !new RegExp(m.sayfa).test(page)) continue;
    if (m.secici && !(f.sel || '').includes(m.secici)) continue;
    if (m.metin && !(f.text || '').includes(m.metin) && !JSON.stringify(f.detail || {}).includes(m.metin)) continue;
    return m;
  }
  return null;
}

// ── Tek yükleme ──────────────────────────────────────────────────────────────────────────────────────────
async function measure(browser, o, pg, st, width, outDir, apiCache) {
  const prof = profile(width);
  const mobile = prof.isMobile;
  const name = `${pg.ad}__${st.ad}__${width}`;
  const rec = { sayfa: pg.ad, durum: st.ad, vp: width, url: null, status: null, findings: [], k7: [], errors: [], notlar: [], at: new Date().toISOString() };
  let ctx;
  try {
    rec.url = o.base + await resolvePath(o.base, st.yol || pg.yol, apiCache);
    ctx = await browser.newContext({ ...prof, locale: 'tr-TR', colorScheme: 'dark', timezoneId: 'Europe/Istanbul', ...(o.yerelStatic ? { serviceWorkers: 'block' } : {}) });
    if (o.yerelStatic) {
      // Canlı HTML + bu ağaçtaki static/ (CSS/JS düzeltmesini deploy öncesi canlı sayfada denemek için).
      const org = new URL(o.base).origin;
      await ctx.route('**/static/**', async (route) => {
        const u = new URL(route.request().url());
        const fp = path.join(REPO, decodeURIComponent(u.pathname));
        if (u.origin === org && fp.startsWith(path.join(REPO, 'static')) && fs.existsSync(fp)) return route.fulfill({ path: fp });
        return route.continue();
      });
    }
    if (!st.ilk_ziyaret) await ctx.addInitScript(() => { try { localStorage.setItem('bp_ga_consent', 'denied'); } catch (e) { /* yok */ } });
    const page = await ctx.newPage();
    const origin = new URL(o.base).origin;
    page.on('console', (m) => {
      if (m.type() !== 'error') return;
      // Beklenen hata belgesinin (404 sayfası) kendi "Failed to load resource" satırı bulgu değildir.
      if (st.beklenen_durum && /^Failed to load resource/.test(m.text()) && (m.location() || {}).url === rec.url) return;
      rec.k7.push({ tur: 'console', metin: (m.text() + ' @' + ((m.location() || {}).url || '').replace(o.base, '')).slice(0, 220) });
    });
    page.on('pageerror', (e) => rec.k7.push({ tur: 'pageerror', metin: String(e).slice(0, 200) }));
    page.on('response', (r) => {
      const u = r.url();
      if (!u.startsWith(origin) || r.status() < 400) return;
      if (r.request().resourceType() === 'document' && st.beklenen_durum && r.status() === st.beklenen_durum) return;
      rec.k7.push({ tur: 'http ' + r.status(), metin: u.replace(origin, '').slice(0, 160) });
    });
    page.on('requestfailed', (r) => {
      const u = r.url(), err = (r.failure() && r.failure().errorText) || '';
      if (!u.startsWith(origin) || /ERR_ABORTED/.test(err)) return;
      rec.k7.push({ tur: 'requestfailed ' + err, metin: u.replace(origin, '').slice(0, 160) });
    });
    if (st.geciktir) await page.route(st.geciktir.desen, async (route) => { await sleep(st.geciktir.ms); try { await route.continue(); } catch (e) { /* kapandı */ } });
    for (let attempt = 0; attempt < 3; attempt++) {
      try { const r = await page.goto(rec.url, { waitUntil: 'load', timeout: 45000 }); rec.status = r ? r.status() : null; }
      catch (e) { rec.status = 'ERR ' + String(e.message || e).slice(0, 80); }
      if (rec.status === 429 || rec.status === 502 || rec.status === 503 || rec.status === 504) { rec.k7 = []; rec.notlar.push('HTTP ' + rec.status + ', yeniden deneme'); await sleep(15000 * (attempt + 1)); continue; }
      break;
    }
    const okStatus = st.beklenen_durum || 200;
    if (rec.status !== okStatus) { rec.olculemedi = 'HTTP ' + rec.status; return rec; }
    if (!st.geciktir) { try { await page.waitForLoadState('networkidle', { timeout: 10000 }); } catch (e) { /* uzun istek */ } }
    await page.evaluate(() => document.fonts && document.fonts.ready);
    await sleep(st.olcum_ms || 1500);
    for (const a of st.adimlar || []) {
      if (a.tikla) { await page.click(a.tikla, { timeout: 5000 }).catch((e) => rec.errors.push('adım tıkla ' + a.tikla + ': ' + String(e.message).slice(0, 80))); }
      if (a.tikla_hepsi) {
        for (let i = 0; i < 12; i++) {
          const n = await page.evaluate((s) => { const el = document.querySelector(s); if (!el) return 0; el.click(); return 1; }, a.tikla_hepsi);
          if (!n) break;
          await sleep(350);
        }
      }
      if (a.ac_details) await page.evaluate(() => document.querySelectorAll('details').forEach((d) => { d.open = true; }));
      if (a.kaydir) await page.evaluate((s) => { const el = document.querySelector(s); if (el) el.scrollIntoView({ block: 'center' }); }, a.kaydir);
      await sleep(a.bekle || 600);
    }
    // Tembel yüklenen bloklar (ör. hisse "Son haberler") için sayfa bir kez baştan sona kaydırılır.
    if (!st.geciktir) {
      await page.evaluate(async () => {
        const H = Math.min(document.documentElement.scrollHeight, 30000);
        for (let y = 0; y < H; y += Math.round(innerHeight * 0.9)) { window.scrollTo(0, y); await new Promise((r) => setTimeout(r, 120)); }
        window.scrollTo(0, 0);
      });
      try { await page.waitForLoadState('networkidle', { timeout: 6000 }); } catch (e) { /* uzun istek */ }
      await sleep(800);
    }
    if (o.css) { await page.addStyleTag({ content: o.css }); await sleep(400); }
    let expect = [];
    if (o.inject) { expect = await page.evaluate(INJECT, mobile); await sleep(300); }
    // Animasyonlar donar (makro şerit), ölçüm üstte başlar.
    await page.evaluate(() => { try { document.getAnimations().forEach((a) => a.pause()); } catch (e) { /* yok */ } window.scrollTo(0, 0); });
    await sleep(200);
    const pr = await Promise.race([
      page.evaluate(PROBE, { kontrol: o.kontrol.filter((k) => !(st.kontrol_haric || []).includes(k)), halkalar: o.cfg.halkalar || [], jargon: JARGON }),
      sleep(90000).then(() => ({ timeout: true })),
    ]);
    if (pr.timeout) { rec.olculemedi = 'ölçüm zaman aşımı'; return rec; }
    rec.findings.push(...pr.findings); rec.errors.push(...pr.errors); rec.olcum = pr.stats;
    if (mobile && o.kontrol.includes('K6') && !(st.kontrol_haric || []).includes('K6')) {
      const tp = await Promise.race([page.evaluate(TAP, { muafSecici: (o.cfg.k6_muaf || ['.hm-t']).join(',') }), sleep(120000).then(() => ({ timeout: true }))]);
      if (tp.timeout) rec.errors.push('K6: zaman aşımı');
      else { rec.findings.push(...tp.findings); rec.olcum.hedef = tp.measured; rec.olcum.hedefOlculemeyen = tp.unmeasured; }
    }
    if (o.kontrol.includes('K7')) for (const e of rec.k7) {
      const inj = /__gd_inj_k7/.test(e.metin) ? '__gd_inj_k7' : null;
      rec.findings.push({ k: 'K7', sev: 'FAIL', sel: e.tur, inj, text: e.metin, rect: null, fixed: false, detail: {} });
    }
    // Muafiyet, gruplama, pozitif kontrol
    const mu = o.muaf;
    for (const f of rec.findings) {
      if (f.inj) continue;
      const m = mu && muafMatch(mu, `${pg.ad}:${st.ad}`, f);
      if (m) { f.muaf = m.gerekce; m._n = (m._n || 0) + 1; }
    }
    if (o.inject) {
      rec.pozitif = {};
      for (const k of expect) rec.pozitif[k] = rec.findings.some((f) => f.k === k && f.inj && (k === 'K7' || f.inj === INJ_ID[k]));
    }
    // FAIL kırpıntıları (grup başına ilk örnek)
    const groups = group(rec.findings.filter((f) => !f.inj && !f.muaf && f.sev === 'FAIL' && f.rect));
    let n = 0;
    for (const g of groups) {
      if (n >= o.kirpinti) break;
      const f = g.ornek;
      const file = path.join(outDir, `fail__${f.k}__${pg.ad}__${st.ad}__${width}__${++n}.png`);
      try { await crop(page, f, file, prof); g.kirpinti = path.basename(file); f.kirpinti = g.kirpinti; } catch (e) { n--; rec.notlar.push('kırpıntı yok: ' + f.sel + ' — ' + String(e.message).split('\n')[0].slice(0, 80)); }
    }
  } catch (e) {
    rec.olculemedi = String(e && e.message || e).slice(0, 160);
  } finally {
    if (ctx) await ctx.close().catch(() => {});
    fs.writeFileSync(path.join(outDir, name + '.json'), JSON.stringify(rec, null, 1));
  }
  return rec;
}

async function crop(page, f, file, prof) {
  const { width: vw, height: vh } = prof.viewport;
  const vy = await page.evaluate((f) => {
    let top;
    if (f.fixed) { window.scrollTo(0, 0); top = f.rect.vy; } else { window.scrollTo(0, Math.max(0, f.rect.y - innerHeight / 3)); top = f.rect.y - scrollY; }
    const o = document.createElement('div');
    o.id = '__gd_box';
    o.style.cssText = `position:fixed;left:${f.rect.x - 3}px;top:${top - 3}px;width:${f.rect.w + 6}px;height:${f.rect.h + 6}px;border:2px solid #ff2d2d;z-index:2147483647;pointer-events:none;box-sizing:border-box`;
    document.documentElement.appendChild(o);
    return top;
  }, f);
  await sleep(120);
  if (f.rect.x >= vw || f.rect.x + f.rect.w <= 0 || vy >= vh || vy + f.rect.h <= 0) {
    await page.evaluate(() => { const o = document.getElementById('__gd_box'); if (o) o.remove(); });
    throw new Error('öğe görünür alanın dışında (ör. kayan şerit), kırpıntı yok');
  }
  const x0 = Math.max(0, Math.floor(f.rect.x - 24)), y0 = Math.max(0, Math.floor(vy - 24));
  const w = Math.max(8, Math.min(vw - x0, Math.ceil(f.rect.w + 48))), h = Math.max(8, Math.min(vh - y0, Math.ceil(f.rect.h + 48)));
  await page.screenshot({ path: file, clip: { x: x0, y: y0, width: w, height: h } });
  await page.evaluate(() => { const o = document.getElementById('__gd_box'); if (o) o.remove(); });
  const k = 3 / prof.deviceScaleFactor;
  if (k > 1) { try { execFileSync('magick', [file, '-resize', `${Math.round(k * 100)}%`, file]); } catch (e) { /* magick yoksa 1× kalır */ } }
}

function group(findings) {
  const m = new Map();
  for (const f of findings) {
    const key = f.k + '|' + f.sev + '|' + f.sel + '|' + (f.detail && (f.detail.kural || f.detail.kap || f.detail.kayit || '') || '');
    const g = m.get(key) || { k: f.k, sev: f.sev, sel: f.sel, n: 0, ornek: f, ornekler: [] };
    g.n++;
    if (g.ornekler.length < 3) g.ornekler.push({ text: f.text, detail: f.detail });
    if (f.kirpinti && !g.kirpinti) g.kirpinti = f.kirpinti;
    m.set(key, g);
  }
  return [...m.values()].sort((a, b) => (a.sev === b.sev ? b.n - a.n : a.sev === 'FAIL' ? -1 : 1));
}

function fmtDetail(d) { return Object.entries(d || {}).map(([k, v]) => `${k} ${v}`).join(', '); }
const mdEsc = (s) => String(s == null ? '' : s).replace(/\|/g, '\\|').replace(/\n/g, ' ');

function writeReport(o, recs, outDir) {
  const sum = { base: o.base, at: new Date().toISOString(), vp: o.vps, kontrol: o.kontrol, inject: !!o.inject, css: o.css || null, yuklemeler: [] };
  let fail = 0, warn = 0, olcm = 0, injMiss = 0;
  for (const r of recs) {
    const real = r.findings.filter((f) => !f.inj);
    const F = real.filter((f) => f.sev === 'FAIL' && !f.muaf), W = real.filter((f) => f.sev === 'WARN' && !f.muaf), M = real.filter((f) => f.muaf);
    const by = (arr) => arr.reduce((a, f) => { a[f.k] = (a[f.k] || 0) + 1; return a; }, {});
    const miss = r.pozitif ? Object.entries(r.pozitif).filter(([, v]) => !v).map(([k]) => k) : [];
    const ozet = { sayfa: r.sayfa, durum: r.durum, vp: r.vp, url: r.url, status: r.status, olculemedi: r.olculemedi || (r.errors.length ? 'ölçüm hatası: ' + r.errors.join(' · ') : null),
      fail: F.length, warn: W.length, muaf: M.length, failK: by(F), warnK: by(W), olcum: r.olcum || null, pozitifEksik: miss, gruplar: group(F).map((g) => ({ ...g, ornek: undefined })) };
    fail += F.length; warn += W.length; if (ozet.olculemedi) olcm++; injMiss += miss.length;
    sum.yuklemeler.push(ozet);
  }
  sum.toplam = { fail, warn, olculemedi: olcm, pozitifEksik: injMiss };
  sum.yerelStatic = !!o.yerelStatic;
  const expired = (o.muaf || []).filter((m) => m.son_tarih && m.son_tarih < today());
  const over = (o.muaf || []).filter((m) => m.azami != null && (m._n || 0) > m.azami);
  sum.muaf = (o.muaf || []).map((m) => ({ kontrol: m.kontrol, sayfa: m.sayfa, secici: m.secici, gerekce: m.gerekce, son_tarih: m.son_tarih, eslesen: m._n || 0, azami: m.azami ?? null }));
  sum.muafSuresiDolan = expired.map((m) => m.secici);
  const exit = (fail || olcm || injMiss || over.length) ? 2 : warn ? 1 : 0;
  sum.exit = exit;
  fs.writeFileSync(path.join(outDir, '_ozet.json'), JSON.stringify(sum, null, 1));

  // Markdown: tablo (sayfa:durum × vp) + FAIL listesi
  const keys = [...new Set(recs.map((r) => r.sayfa + ':' + r.durum))];
  let md = `# Görsel denetim — ${today()}\n\n\`node tools/live/gorsel-denetim.mjs${o.argv ? ' ' + o.argv : ''}\` · ${o.base} · ${new Date().toLocaleString('tr-TR', { timeZone: 'Europe/Istanbul' })}\n\n`;
  md += `**Sonuç: ${exit === 0 ? 'PASS' : exit === 1 ? 'WARN' : 'FAIL'}** (exit ${exit}) · FAIL ${fail} · WARN ${warn} · ölçülemeyen ${olcm}` + (o.inject ? ` · pozitif kontrolde yakalanmayan ${injMiss}` : '') + (o.css ? ` · enjekte CSS: \`${mdEsc(o.css)}\`` : '') + (o.yerelStatic ? ' · static/ yerel ağaçtan' : '') + '\n\n';
  md += `| sayfa:durum | ${o.vps.join(' | ')} |\n|---|${o.vps.map(() => '---').join('|')}|\n`;
  for (const key of keys) {
    md += `| ${key} |`;
    for (const vp of o.vps) {
      const z = sum.yuklemeler.find((y) => y.sayfa + ':' + y.durum === key && y.vp === vp);
      if (!z) { md += ' — |'; continue; }
      if (z.olculemedi) { md += ` ⛔ ${mdEsc(z.olculemedi).slice(0, 40)} |`; continue; }
      const s = z.fail ? `FAIL ${Object.entries(z.failK).map(([k, v]) => k + '×' + v).join(' ')}` : z.warn ? 'WARN' : 'PASS';
      md += ` ${s}${z.warn && z.fail ? ` · W${z.warn}` : z.warn ? ' ' + z.warn : ''}${z.muaf ? ` · muaf ${z.muaf}` : ''}${z.pozitifEksik.length ? ' · ✗poz ' + z.pozitifEksik.join(',') : ''} |`;
    }
    md += '\n';
  }
  const failRows = [];
  for (const z of sum.yuklemeler) for (const g of z.gruplar) failRows.push({ z, g });
  if (failRows.length) {
    md += `\n## FAIL ayrıntısı (gruplanmış; kırpıntılar bu dizinde)\n\n| K | sayfa:durum@vp | öğe | adet | örnek | kırpıntı |\n|---|---|---|---|---|---|\n`;
    for (const { z, g } of failRows.slice(0, 300)) {
      const e = g.ornekler[0] || {};
      md += `| ${g.k} | ${z.sayfa}:${z.durum}@${z.vp} | \`${mdEsc(g.sel)}\` | ${g.n} | ${mdEsc((e.text || '').slice(0, 40))} — ${mdEsc(fmtDetail(e.detail))} | ${g.kirpinti || ''} |\n`;
    }
  }
  const muafUsed = sum.muaf.filter((m) => m.eslesen);
  if (muafUsed.length) {
    md += `\n## Muaf tutulan açık bulgular (ratchet; ${'tools/live/gorsel-denetim.muaf.json'})\n\n| K | seçici | eşleşen | azami | gerekçe | son tarih |\n|---|---|---|---|---|---|\n`;
    for (const m of muafUsed) md += `| ${m.kontrol} | \`${mdEsc(m.secici)}\` | ${m.eslesen} | ${m.azami ?? '—'} | ${mdEsc(m.gerekce)} | ${m.son_tarih || '—'} |\n`;
  }
  if (expired.length) md += `\n**Süresi dolan muafiyet (uygulanmadı):** ${expired.map((m) => '`' + m.secici + '`').join(', ')}\n`;
  if (over.length) md += `\n**Ratchet aşıldı (azami < eşleşen → FAIL):** ${over.map((m) => '`' + m.secici + '` ' + m._n + '>' + m.azami).join(', ')}\n`;
  fs.writeFileSync(path.join(outDir, '_ozet.md'), md);
  return sum;
}

// ── Ana akış ─────────────────────────────────────────────────────────────────────────────────────────────
const a = args(process.argv.slice(2));
const cfg = loadJson(path.join(HERE, 'gorsel-denetim.sayfalar.json'));
if (a.liste) {
  for (const p of cfg.sayfalar) for (const s of p.durumlar || [{ ad: 'varsayilan' }]) console.log(`${p.ad}:${s.ad}`.padEnd(34), s.yol || p.yol);
  process.exit(0);
}
const o = {
  base: String(a.base || process.env.GORSEL_DENETIM_BASE || 'https://borsapusula.com').replace(/\/$/, ''),
  vps: [...String(a.vp || '1440,820,390,320').split(','), ...(a['ek-vp'] ? String(a['ek-vp']).split(',') : [])].map(Number).filter(Boolean),
  kontrol: a.kontrol ? String(a.kontrol).split(',').map((x) => x.trim().toUpperCase()) : ALL_K,
  inject: !!a.inject, css: typeof a.css === 'string' ? a.css : null, yerelStatic: !!a['yerel-static'],
  kirpinti: a.kirpinti ? Number(a.kirpinti) : 6, cfg,
  muaf: a.muafsiz ? [] : loadJson(path.join(HERE, 'gorsel-denetim.muaf.json'), { muaf: [] }).muaf || [],
  argv: process.argv.slice(2).join(' '),
};
const outDir = expandHome(a.out || path.join('~', 'ops', 'plans', 'qa', `gorsel-${today()}`, 'oto'));
fs.mkdirSync(outDir, { recursive: true });
const want = a.sayfa ? String(a.sayfa).split(',').map((x) => x.trim()).filter(Boolean) : null;
const plan = [];
for (const p of cfg.sayfalar) for (const s of p.durumlar || [{ ad: 'varsayilan' }]) {
  if (want && !want.some((w) => w === p.ad || w === `${p.ad}:${s.ad}`)) continue;
  plan.push([p, s]);
}
if (!plan.length) { console.error('eşleşen sayfa yok (--liste)'); process.exit(2); }

const pw = resolveMod('playwright');
if (!pw) { console.error('playwright bulunamadı (repo ya da ~/Bist ve BTC/Bist30/node_modules)'); process.exit(2); }
const browser = await pw.chromium.launch();
const recs = [];
const apiCache = {};
try {
  for (const [p, s] of plan) {
    for (const w of o.vps) {
      const t0 = Date.now();
      const r = await measure(browser, o, p, s, w, outDir, apiCache);
      recs.push(r);
      const real = r.findings.filter((f) => !f.inj && !f.muaf);
      const F = real.filter((f) => f.sev === 'FAIL'), W = real.filter((f) => f.sev === 'WARN');
      const ks = Object.entries(F.reduce((acc, f) => { acc[f.k] = (acc[f.k] || 0) + 1; return acc; }, {})).map(([k, v]) => k + '×' + v).join(' ');
      const poz = r.pozitif ? ' poz ' + Object.entries(r.pozitif).map(([k, v]) => k + (v ? '✓' : '✗')).join(' ') : '';
      console.log(`${(p.ad + ':' + s.ad).padEnd(30)} ${String(w).padStart(4)} ${r.olculemedi ? 'ÖLÇÜLEMEDİ ' + r.olculemedi : (F.length ? 'FAIL ' + ks : W.length ? 'WARN' : 'PASS')}`
        + `${W.length ? ' W' + W.length : ''}${r.errors.length ? ' hata ' + r.errors.length : ''}${poz} ${((Date.now() - t0) / 1000).toFixed(1)}s`);
      await sleep(Number(a.ara || 700));
    }
  }
} finally {
  await browser.close();
}
const sum = writeReport(o, recs, outDir);
console.log(`\n${sum.exit === 0 ? 'PASS' : sum.exit === 1 ? 'WARN' : 'FAIL'} · FAIL ${sum.toplam.fail} · WARN ${sum.toplam.warn} · ölçülemeyen ${sum.toplam.olculemedi}`
  + (o.inject ? ` · pozitif kontrolde yakalanmayan ${sum.toplam.pozitifEksik}` : '') + ` → ${path.join(outDir, '_ozet.md')}`);
process.exit(sum.exit);
