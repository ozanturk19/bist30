/* BorsaPusula global tooltip — [data-tip] icin dokunmatik+klavye erisilebilir tooltip (T5.5, native title= yerine).
   hover(masaustu) + focus(klavye) + tap(dokunmatik, toggle) + Escape/disari-tiklama ile kapanma + viewport tasma onleme. */
(function() {
  var ID = 'bp-tooltip';
  var activeTarget = null;
  var showTimer = null;
  var focusShowGuard = false;
  var tip;

  function ensureStyle() {
    if (document.getElementById('bp-tooltip-style')) return;
    var s = document.createElement('style');
    s.id = 'bp-tooltip-style';
    s.textContent =
      '.bp-tooltip{position:fixed;z-index:var(--bp-z-tooltip);background:#161618;border:1px solid var(--bp-border);' +
      'color:#e5e1e4;font-size:12px;line-height:1.45;font-weight:500;padding:8px 11px;border-radius:var(--bp-radius);' +
      'box-shadow:var(--bp-shadow-md);max-width:260px;opacity:0;transform:translateY(4px) scale(.97);' +
      'transition:opacity .14s ease,transform .14s ease;pointer-events:none}' +
      '.bp-tooltip.bp-tooltip-show{opacity:1;transform:translateY(0) scale(1)}' +
      '.bp-tooltip::after{content:"";position:absolute;width:8px;height:8px;background:inherit;' +
      'border:inherit;border-top:none;border-left:none;left:var(--bp-tip-arrow-x,50%);margin-left:-4px}' +
      '.bp-tooltip[data-pos="top"]::after{bottom:-5px;transform:rotate(45deg)}' +
      '.bp-tooltip[data-pos="bottom"]::after{top:-5px;transform:rotate(225deg)}' +
      '@media(prefers-reduced-motion:reduce){.bp-tooltip{transition:none}}';
    document.head.appendChild(s);
  }

  function getTip() {
    if (!tip) {
      tip = document.createElement('div');
      tip.className = 'bp-tooltip';
      tip.setAttribute('role', 'tooltip');
      tip.id = ID;
      document.body.appendChild(tip);
    }
    return tip;
  }

  function position(target) {
    var t = getTip();
    var r = target.getBoundingClientRect();
    var tw = t.offsetWidth, th = t.offsetHeight;
    var vw = document.documentElement.clientWidth;
    var top = r.top - th - 10;
    var pos = 'top';
    if (top < 8) { top = r.bottom + 10; pos = 'bottom'; }
    var left = r.left + r.width / 2 - tw / 2;
    left = Math.max(8, Math.min(left, vw - tw - 8));
    var arrowX = (r.left + r.width / 2 - left);
    arrowX = Math.max(12, Math.min(arrowX, tw - 12));
    t.style.setProperty('--bp-tip-arrow-x', arrowX + 'px');
    t.style.top = top + 'px';
    t.style.left = left + 'px';
    t.setAttribute('data-pos', pos);
  }

  function show(target) {
    var text = target.getAttribute('data-tip');
    if (!text) return;
    clearTimeout(showTimer);
    var t = getTip();
    t.textContent = text;
    if (activeTarget && activeTarget !== target) activeTarget.removeAttribute('aria-describedby');
    activeTarget = target;
    target.setAttribute('aria-describedby', ID);
    t.style.left = '-9999px';
    t.classList.add('bp-tooltip-show');
    requestAnimationFrame(function() { position(target); });
  }

  function hide() {
    if (!activeTarget) return;
    activeTarget.removeAttribute('aria-describedby');
    activeTarget = null;
    if (tip) tip.classList.remove('bp-tooltip-show');
  }

  function closest(el) {
    return el && el.closest ? el.closest('[data-tip]') : null;
  }

  function onEnter(e) {
    var target = closest(e.target);
    if (!target) return;
    clearTimeout(showTimer);
    showTimer = setTimeout(function() { show(target); }, 120);
  }
  function onLeave(e) {
    var target = closest(e.target);
    if (!target || target !== activeTarget) return;
    clearTimeout(showTimer);
    hide();
  }
  function onFocusIn(e) {
    var target = closest(e.target);
    if (target) { show(target); focusShowGuard = true; }
  }
  function onFocusOut(e) {
    var target = closest(e.target);
    if (target === activeTarget) hide();
    focusShowGuard = false;
  }
  function onClick(e) {
    var target = closest(e.target);
    if (!target) { if (activeTarget) hide(); return; }
    if (target === activeTarget) {
      if (focusShowGuard) { focusShowGuard = false; return; }
      hide();
      return;
    }
    e.stopPropagation();
    show(target);
  }
  function onKeydown(e) {
    if (e.key === 'Escape' && activeTarget) hide();
  }
  function onReflow() {
    if (activeTarget) position(activeTarget);
  }

  ensureStyle();
  document.addEventListener('mouseover', onEnter, true);
  document.addEventListener('mouseout', onLeave, true);
  document.addEventListener('focusin', onFocusIn, true);
  document.addEventListener('focusout', onFocusOut, true);
  document.addEventListener('click', onClick, true);
  document.addEventListener('keydown', onKeydown);
  window.addEventListener('scroll', onReflow, true);
  window.addEventListener('resize', onReflow);
})();
