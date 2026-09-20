/* ─────────────────────────────────────────────────────────────────────────
   K-L (CANLI) — Dokunma hedefi denetçisi · WCAG 2.5.8 Target Size Minimum (AA)
   21.09 (CPO). Bu bir pre-deploy KAPISI DEĞİL: ihlal statik CSS'te görünmez,
   yalnız render edilmiş sayfada ölçülebilir. Browser pane'de 375×812
   (resize_window preset:"mobile") ile sayfayı açıp bu dosyanın içeriğini
   javascript_tool ile çalıştır.

   ÖLÇÜT: kutunun boyu DEĞİL — merkezden ±12px'teki 4 noktanın
   `document.elementFromPoint` ile gerçekten o ögeye isabet edip etmediği.
   Sebebi: sözde-öğe halosu (`::before` 44×44) kutuyu büyütmeden hedefi
   büyütebilir; salt `getBoundingClientRect` bunu göremez ve yanlış alarm verir.

   MUAFİYETLER (hepsi WCAG'de tanımlı, üçü de canlı turda gerçek çıktı):
     1) labelOK        — <label> sarmalı ≥24px olan onay kutusu/radyo
     2) equivAncestor  — AYNI hedefe giden ≥24px bir ata (örn. bilanco
                         `.stock-card` role="link" tüm kartı /hisse/<t>'ye
                         götürüyor; içindeki `.sc-ticker-link` muaf)
     3) inlineInSentence — cümle içi satır-içi bağlantı (WCAG "inline")

   ⚠️ HALO EVRENSEL DEĞİL: portfolio `.ls-warning-close` halosu 6/6 prob ile
   isabet alırken hisse `.ind-help` halosu 0/6 aldı (ata kırpması / üste
   boyama). Şüphe varsa ögenin KENDİSİNİ 24px yap — bkz. commit 76ab16e.

   Çıktı: {page, cand, bad, agg:[{sel,n,w,h,txt}]}. Hedef: bad = 0.
   ───────────────────────────────────────────────────────────────────────── */
(() => {
  const sel = 'a[href],button,input:not([type=hidden]),select,textarea,' +
              '[role="button"],[role="tab"],[role="link"],summary';
  const R = 12;

  function owns(el, x, y) {
    const n = document.elementFromPoint(x, y);
    if (!n) return false;                    // viewport dışı -> ölçüm geçersiz
    if (n === el || el.contains(n)) return true;
    const lab = el.closest('label');
    return !!(lab && (n === lab || lab.contains(n)));
  }

  function labelOK(el) {
    if (el.tagName !== 'INPUT') return false;
    const l = el.closest('label') ||
              (el.id && document.querySelector('label[for="' + CSS.escape(el.id) + '"]'));
    if (!l) return false;
    const lr = l.getBoundingClientRect();
    return Math.min(lr.width, lr.height) >= 24;
  }

  function equivAncestor(el) {
    const href = el.getAttribute && el.getAttribute('href');
    let p = el.parentElement;
    while (p && p !== document.body) {
      const isTarget = p.matches('a[href],[role="link"],[role="button"],button') ||
                       p.hasAttribute('onclick');
      if (isTarget) {
        const pr = p.getBoundingClientRect();
        if (Math.min(pr.width, pr.height) >= 24) {
          const ph = (p.getAttribute('href') || '') +
                     (p.getAttribute('onclick') || '') +
                     ((p.dataset && p.dataset.ticker) || '');
          if (!href) return p.tagName;
          if (ph.includes(href)) return p.tagName;
          const seg = href.split('/').filter(Boolean).pop();
          if (seg && ph.includes(seg)) return p.tagName;
        }
      }
      p = p.parentElement;
    }
    return null;
  }

  function inlineInSentence(el) {
    if (getComputedStyle(el).display !== 'inline') return false;
    const p = el.parentElement;
    if (!p) return false;
    let txt = 0;
    p.childNodes.forEach(n => { if (n.nodeType === 3 && n.textContent.trim().length > 2) txt++; });
    return txt > 0;
  }

  const els = [...document.querySelectorAll(sel)].filter(el => {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || cs.pointerEvents === 'none') return false;
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) return false;
    return Math.min(r.width, r.height) < 24;
  });

  // elementFromPoint yalnız viewport içinde çalışır -> sayfayı adım adım kaydır
  const seen = new Set(), bad = [];
  const H = innerHeight, total = document.documentElement.scrollHeight;
  for (let y = 0; y < total + H; y += H * 0.8) {
    window.scrollTo(0, y);
    els.forEach(el => {
      if (seen.has(el)) return;
      const r = el.getBoundingClientRect();
      if (r.top < 4 || r.bottom > H - 4) return;   // tam görünür değilse sonraki adımda
      seen.add(el);
      const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
      if (owns(el, cx, cy - R + 1) && owns(el, cx, cy + R - 1) &&
          owns(el, cx - R + 1, cy) && owns(el, cx + R - 1, cy)) return;
      if (labelOK(el) || equivAncestor(el) || inlineInSentence(el)) return;
      bad.push({
        t: el.tagName.toLowerCase(),
        c: ((el.className && el.className.baseVal !== undefined ? el.className.baseVal : el.className) || '').toString().slice(0, 28),
        id: el.id || '',
        txt: (el.textContent || el.getAttribute('aria-label') || '').trim().slice(0, 20),
        w: +r.width.toFixed(1),
        h: +r.height.toFixed(1),
      });
    });
  }
  window.scrollTo(0, 0);

  const agg = {};
  bad.forEach(b => {
    const k = b.t + '.' + (b.c || '(none)') + (b.id ? '#' + b.id : '');
    agg[k] = agg[k] || { n: 0, ex: b };
    agg[k].n++;
  });
  return JSON.stringify({
    page: location.pathname,
    cand: els.length,
    bad: bad.length,
    agg: Object.entries(agg).map(([k, v]) => ({ sel: k, n: v.n, w: v.ex.w, h: v.ex.h, txt: v.ex.txt })),
  });
})()
