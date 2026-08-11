/* BorsaPusula focus-trap — modal/dialog/sheet icin Tab dongusu + Escape kapama + odak iadesi (WCAG 2.4.3) */
(function() {
  var FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

  function focusables(container) {
    return Array.prototype.filter.call(
      container.querySelectorAll(FOCUSABLE),
      function(el) { return el.offsetParent !== null; }
    );
  }

  /* container: acik modal/sheet elementi. onEscape: opsiyonel, Escape'te cagrilir (kapatma islevini modal kendi yonetir). Donus: release() — kapanista cagrilmali. */
  window.bpTrapFocus = function(container, onEscape) {
    if (!container) return function() {};
    var returnEl = document.activeElement;
    if (!container.hasAttribute('tabindex')) container.setAttribute('tabindex', '-1');

    var list = focusables(container);
    (list[0] || container).focus();

    function onKeydown(e) {
      if (e.key === 'Escape') {
        if (onEscape) { e.preventDefault(); onEscape(); }
        return;
      }
      if (e.key !== 'Tab') return;
      var els = focusables(container);
      if (!els.length) return;
      var first = els[0], last = els[els.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault(); last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault(); first.focus();
      }
    }
    container.addEventListener('keydown', onKeydown);

    return function release() {
      container.removeEventListener('keydown', onKeydown);
      if (returnEl && typeof returnEl.focus === 'function') returnEl.focus();
    };
  };
})();
