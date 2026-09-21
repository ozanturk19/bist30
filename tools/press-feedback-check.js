/* ─────────────────────────────────────────────────────────────────────────
   K-AA (CANLI) — DOKUNMA (BASMA) GERİ BİLDİRİMİ denetçisi
   21.09 (CPO). K-Z'nin kendi itirafındaki 1. madde: ":active = dokunma geri
   bildirimi ve bu eksende neredeyse HİÇ kural yok. Gerçek soru ölçülmedi:
   dokunulabilir kontrollerin kaçında basma geri bildirimi VAR?"

   SORU: 375px'te bir kontrole BASARKEN (parmak ekranda, henüz kalkmadı)
   kullanıcı bir şeyin olduğunu GÖRÜYOR mu?

   Masaüstünde bu soruyu :hover cevaplar. Dokunmatikte :hover YOKTUR — ve
   bu sitede hover kurallarının çoğu zaten `@media (hover:hover)` arkasında,
   yani mobilde HİÇ uygulanmaz. Geriye iki kaynak kalır:
     (A) `:active` CSS kuralı
     (B) tarayıcının varsayılan `-webkit-tap-highlight-color` vurgusu

   ⚠️ (B) BU SİTEDE MİTİGASYON DEĞİL — iki ayrı sebeple, ikisi de ölçülür:
     1) `bp-search.js` site geneline `a[href^="/"]{...:transparent}` enjekte
        eder + 6 CSS dosyası kendi kontrollerinde kapatır.
     2) Kapatılmamış olanlarda bile varsayılan rgba(0,0,0,.18) KOYU zemin
        (#0e0e12) üzerinde ~1.0:1 — görünmez. Denetçi bunu VARSAYMAZ, ölçer.

   ÖLÇÜM TUZAKLARI (K-Z'de ikisi de ilk koşumda yalan söyledi):
     ⛔ Chrome'da CSSStyleRule ARTIK `cssRules` taşır (iç içe CSS). Gruplayıcı
        ayırt edici `r.cssRules` DEĞİL, `r.style`in YOKLUĞUdur.
     ⛔ Eşleşmeyen @media içindeki kurallar harmanlanırsa yanlış viewport
        raporlanır → matchMedia(conditionText) kapısı.
   ⛔ CSP: connect-src 'self' + unsafe-eval yok. fetch/eval BLOKE.
      Çalışan yol: kaynağı bir kez localStorage'a yaz, her sayfada
      <script> etiketiyle enjekte et (unsafe-inline AÇIK).

   Çıktı: {page, vw, cand, none, activeCovered, hoverOnly, thlKilled,
           thlUseless, agg:[{sel,n,why,txt}]}. Hedef: none = 0.
   ───────────────────────────────────────────────────────────────────────── */
(() => {
  const SEL = 'a[href],button,input:not([type=hidden]),select,textarea,' +
              '[role="button"],[role="tab"],[role="link"],summary,[onclick]';

  /* ── 1. CSSOM'dan :active ve :hover kurallarını topla ── */
  const activeTriggers = [];   // {stripped, raw}
  const hoverSels      = [];   // {stripped, raw, mediaGated}
  let rulesSeen = 0, mediaSkipped = 0;

  function head(part, pseudo) {
    const i = part.indexOf(pseudo);
    if (i < 0) return null;
    // :active/:hover taşıyan BİLEŞİĞİN sonuna kadar al (torun seçiciler
    // `.mbn-item:active .mbn-icon` gibi — TETİKLEYİCİ atadır, torun değil).
    let s = part.slice(0, i + pseudo.length);
    s = s.replace(new RegExp(pseudo, 'g'), '').trim();
    return s || '*';
  }

  function harvest(list, gated) {
    for (const r of list) {
      // ⛔ TUZAK: r.cssRules ile gruplayıcı ayırma HER KURALI yutar.
      if (r.style && typeof r.selectorText === 'string') {
        rulesSeen++;
        for (const part of r.selectorText.split(',')) {
          const p = part.trim();
          if (!p) continue;
          if (p.includes(':active')) {
            const s = head(p, ':active');
            if (s) activeTriggers.push({ stripped: s, raw: p });
          }
          if (p.includes(':hover')) {
            const s = head(p, ':hover');
            if (s) hoverSels.push({ stripped: s, raw: p, mediaGated: gated });
          }
        }
      }
      if (r.cssRules) {
        // @media / @supports / iç içe
        let ok = true, isMedia = false;
        const cond = r.conditionText || (r.media && r.media.mediaText) || '';
        if (!r.style && cond) {
          isMedia = true;
          try { ok = matchMedia(cond).matches; } catch (e) { ok = true; }
        }
        if (!ok) { mediaSkipped++; continue; }
        // Eşleşen `hover:hover` bloğu masaüstünde AÇIK olabilir; denetim
        // 375px'te koşar, orada bu bloklar zaten elenir.
        harvest(r.cssRules, gated || (isMedia && /hover/.test(cond)));
      }
    }
  }
  for (const ss of document.styleSheets) {
    try { harvest(ss.cssRules, false); } catch (e) { /* cross-origin */ }
  }

  /* ── 2. Zemin/alfa yardımcıları (K-Y dersi: alfa kompozit EDİLMELİ) ── */
  const px = c => { const m = String(c).match(/[\d.]+/g); return m ? m.map(Number) : null; };
  function groundOf(el) {
    let n = el;
    while (n && n !== document.documentElement) {
      const b = px(getComputedStyle(n).backgroundColor);
      if (b && (b.length < 4 || b[3] > 0.92)) return [b[0], b[1], b[2]];
      n = n.parentElement;
    }
    const b = px(getComputedStyle(document.documentElement).backgroundColor);
    return b ? [b[0], b[1], b[2]] : [14, 14, 18];
  }
  const over = (fg, bg) => fg.length < 4 || fg[3] === undefined
    ? fg.slice(0, 3)
    : [0, 1, 2].map(i => fg[i] * fg[3] + bg[i] * (1 - fg[3]));
  const lum = c => {
    const f = c.map(v => { v /= 255; return v <= .03928 ? v / 12.92 : Math.pow((v + .055) / 1.055, 2.4); });
    return .2126 * f[0] + .7152 * f[1] + .0722 * f[2];
  };
  const ratio = (a, b) => { const l1 = lum(a), l2 = lum(b); return ((Math.max(l1, l2) + .05) / (Math.min(l1, l2) + .05)); };

  /* ── 3. Adayları tara ── */
  const rows = [];
  let cand = 0, none = 0, activeCovered = 0, hoverOnly = 0, thlKilled = 0, thlUseless = 0;

  for (const el of document.querySelectorAll(SEL)) {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity === 0) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 4 || r.height < 4) continue;
    if (el.disabled) continue;
    // metin girişi kendi imleci ile geri bildirim verir
    if (el.matches('input:not([type=submit]):not([type=button]):not([type=checkbox]):not([type=radio]),textarea,select')) continue;
    cand++;

    const hasActive = activeTriggers.some(t => { try { return !!el.closest(t.stripped); } catch (e) { return false; } });
    const hv = hoverSels.filter(h => { try { return !!el.closest(h.stripped); } catch (e) { return false; } });

    // tap-highlight: kapatıldı mı, kapatılmadıysa GÖRÜNÜR mü?
    const thl = px(cs.webkitTapHighlightColor || 'rgba(0,0,0,0.18)') || [0, 0, 0, .18];
    const alpha = thl.length > 3 ? thl[3] : 1;
    const bg = groundOf(el);
    const hl = over(thl, bg);
    const thlR = ratio(hl, bg);
    const killed = alpha < 0.02;
    const useless = !killed && thlR < 1.08;   // gözle ayırt edilemez

    if (hasActive) { activeCovered++; continue; }
    if (killed) thlKilled++; else if (useless) thlUseless++;
    if (!killed && !useless) continue;        // varsayılan vurgu GERÇEKTEN görünür
    if (hv.length) hoverOnly++;
    none++;

    const id = (el.className && typeof el.className === 'string'
      ? '.' + el.className.trim().split(/\s+/).slice(0, 2).join('.')
      : el.tagName.toLowerCase()) + (el.id ? '#' + el.id : '');
    rows.push({
      sel: id, tag: el.tagName.toLowerCase(),
      why: killed ? 'thl-kapali' : 'thl-gorunmez(' + thlR.toFixed(2) + ':1)',
      hoverOnly: hv.length > 0,
      hoverGated: hv.some(h => h.mediaGated),
      txt: (el.textContent || el.getAttribute('aria-label') || '').trim().slice(0, 28)
    });
  }

  const agg = {};
  for (const x of rows) {
    const k = x.sel + '|' + x.why + '|' + (x.hoverOnly ? 'hoverVar' : 'hoverYok');
    (agg[k] = agg[k] || { sel: x.sel, why: x.why, hoverOnly: x.hoverOnly, hoverGated: x.hoverGated, n: 0, txt: x.txt }).n++;
  }
  return {
    page: location.pathname, vw: innerWidth,
    rulesSeen, mediaSkipped, activeRules: activeTriggers.length,
    cand, activeCovered, none, hoverOnly, thlKilled, thlUseless,
    agg: Object.values(agg).sort((a, b) => b.n - a.n)
  };
})()
