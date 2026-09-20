/* K-P  CANLI RENDER KONTRASTI  (CPO, 21.09.2026)  — KAPI DEGIL, canli denetci
 *
 * NEDEN: tools/contrast-check.py (K-I) kendi basliginda kapsam sinirini
 * ACIKCA yaziyor: "YALNIZCA ikisi de AYNI yerde yazili ciftleri gorur
 * (80 cift). MIRAS alinan zemin uzerindeki metni (SAYFADAKI COGU METIN)
 * goremez ... yari saydam degerler ATLANIR."  Bu betik tam da o kor
 * noktayi olcer: gercek render'da her gorunur metin dugumunun computed
 * rengi + gercekten boyanmis zemin zinciri (alfa birlestirme dahil).
 *
 * Browser pane konsolunda calistir; JSON ozet doner.
 */
(() => {
  const clampA = (a) => (isFinite(a) ? Math.min(1, Math.max(0, a)) : 1);
  function parse(c) {
    if (!c) return null;
    const m = c.match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const p = m[1].split(/[,\s/]+/).filter(Boolean).map(Number);
    if (p.length < 3 || p.some((n) => !isFinite(n))) return null;
    return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? clampA(p[3]) : 1 };
  }
  // src'yi dst uzerine ALFA ile yaz
  const over = (src, dst) => ({
    r: src.r * src.a + dst.r * (1 - src.a),
    g: src.g * src.a + dst.g * (1 - src.a),
    b: src.b * src.a + dst.b * (1 - src.a),
    a: 1,
  });
  function lum(c) {
    const f = (v) => {
      v /= 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    };
    return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b);
  }
  const ratio = (a, b) => {
    const l1 = lum(a), l2 = lum(b);
    return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
  };

  function sig(el) {
    let s = el.tagName.toLowerCase();
    if (el.id) s += '#' + el.id;
    const cl = (el.getAttribute('class') || '').trim().split(/\s+/).filter(Boolean);
    if (cl.length) s += '.' + cl.slice(0, 4).join('.');
    return s;
  }

  const SR_ONLY = (cs) => {
    const cp = cs.clipPath || '';
    const cl = cs.clip || '';
    return (cp.includes('inset(50%') || cl.includes('rect(0') || cl.includes('rect(1px'))
      && parseFloat(cs.width) <= 2;
  };

  const out = { violations: [], ambiguous: [], scanned: 0, textNodes: 0, skipped: {} };
  const bump = (k) => (out.skipped[k] = (out.skipped[k] || 0) + 1);

  const all = document.querySelectorAll('*');
  for (const el of all) {
    // yalniz DOGRUDAN metin cocugu olan ogeler
    let txt = '';
    for (const n of el.childNodes) if (n.nodeType === 3) txt += n.nodeValue;
    txt = txt.replace(/\s+/g, ' ').trim();
    if (!txt) continue;
    out.textNodes++;

    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') { bump('gizli'); continue; }
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) { bump('sifir-kutu'); continue; }
    if (SR_ONLY(cs)) { bump('sr-only'); continue; }
    if (el.closest('[aria-hidden="true"]')) { bump('aria-hidden'); continue; }

    // opaklik zinciri
    let opac = 1, p = el;
    while (p && p !== document.documentElement) {
      opac *= parseFloat(getComputedStyle(p).opacity || '1');
      p = p.parentElement;
    }
    if (opac < 0.15) { bump('opaklik<0.15'); continue; }

    const fg0 = parse(cs.color);
    if (!fg0) { bump('renk-cozulemedi'); continue; }

    // ---- ZEMIN ZINCIRI: en ustteki katmandan asagi dogru topla ----
    const layers = [];
    let amb = null, node = el;
    while (node) {
      const s = getComputedStyle(node);
      const bi = s.backgroundImage;
      if (bi && bi !== 'none' && !amb) amb = sig(node) + ' :: ' + bi.slice(0, 60);
      const bc = parse(s.backgroundColor);
      if (bc && bc.a > 0) {
        layers.push(bc);
        if (bc.a >= 0.999) break;
      }
      node = node.parentElement;
    }
    // tabani belirle (hicbir opak katman yoksa canvas)
    let bg = layers.length && layers[layers.length - 1].a >= 0.999
      ? layers.pop()
      : (parse(getComputedStyle(document.documentElement).backgroundColor) || { r: 255, g: 255, b: 255, a: 1 });
    if (bg.a < 0.999) bg = over(bg, { r: 255, g: 255, b: 255, a: 1 });
    for (let i = layers.length - 1; i >= 0; i--) bg = over(layers[i], bg);

    const fg = fg0.a < 0.999 ? over(fg0, bg) : fg0;
    const cr = ratio(fg, bg);

    const fsz = parseFloat(cs.fontSize) || 16;
    const fw = parseInt(cs.fontWeight, 10) || 400;
    const large = fsz >= 24 || (fsz >= 18.66 && fw >= 700);
    const need = large ? 3.0 : 4.5;
    out.scanned++;

    if (cr + 0.005 < need) {
      const rec = {
        sig: sig(el),
        text: txt.slice(0, 44),
        ratio: +cr.toFixed(2),
        need,
        fg: cs.color,
        bg: `rgb(${Math.round(bg.r)}, ${Math.round(bg.g)}, ${Math.round(bg.b)})`,
        px: +fsz.toFixed(1),
        w: fw,
        opac: +opac.toFixed(2),
      };
      if (amb) { rec.bgImage = amb; out.ambiguous.push(rec); }
      else out.violations.push(rec);
    }
  }

  // sinifa gore grupla
  const group = (arr) => {
    const m = new Map();
    for (const v of arr) {
      const k = v.sig + '|' + v.ratio;
      if (!m.has(k)) m.set(k, { ...v, count: 0, samples: [] });
      const g = m.get(k);
      g.count++;
      if (g.samples.length < 2) g.samples.push(v.text);
    }
    return [...m.values()].sort((a, b) => a.ratio - b.ratio);
  };
  return {
    url: location.pathname,
    scanned: out.scanned,
    textNodes: out.textNodes,
    skipped: out.skipped,
    HARD: group(out.violations),
    AMBIG: group(out.ambiguous),
    hardCount: out.violations.length,
    ambigCount: out.ambiguous.length,
  };
})()
