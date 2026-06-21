/* BorsaPusula global toast notification — showToast(msg, type, duration) */
(function() {
  var CONTAINER_ID = 'bp-toast-container';

  function getContainer() {
    var c = document.getElementById(CONTAINER_ID);
    if (!c) {
      c = document.createElement('div');
      c.id = CONTAINER_ID;
      c.style.cssText = 'position:fixed;bottom:24px;right:20px;z-index:9999;display:flex;flex-direction:column;gap:8px;pointer-events:none';
      document.body.appendChild(c);
    }
    return c;
  }

  var COLORS = {
    success: { border: 'rgba(0,226,144,0.4)',   icon: '✓' },
    error:   { border: 'rgba(248,81,73,0.4)',    icon: '✕' },
    warn:    { border: 'rgba(255,200,80,0.4)',    icon: '⚠' },
    info:    { border: 'rgba(184,195,255,0.35)', icon: 'ℹ' }
  };

  window.showToast = function(msg, type, duration) {
    var dur = duration || 3000;
    var col = COLORS[type] || COLORS.info;
    var el = document.createElement('div');
    el.style.cssText = [
      'background:#161618',
      'border:1px solid ' + col.border,
      'border-left:3px solid ' + col.border,
      'color:#e5e1e4',
      'padding:10px 16px',
      'border-radius:8px',
      'font-size:13px',
      'font-weight:600',
      'box-shadow:0 4px 20px rgba(0,0,0,0.45)',
      'max-width:300px',
      'opacity:0',
      'transform:translateX(16px)',
      'transition:opacity .2s,transform .2s',
      'pointer-events:auto',
      'display:flex',
      'align-items:center',
      'gap:8px'
    ].join(';');
    el.innerHTML = '<span style="font-size:11px;opacity:0.8">' + col.icon + '</span><span>' + msg + '</span>';
    getContainer().appendChild(el);
    requestAnimationFrame(function() {
      el.style.opacity = '1';
      el.style.transform = 'translateX(0)';
    });
    setTimeout(function() {
      el.style.opacity = '0';
      el.style.transform = 'translateX(16px)';
      setTimeout(function() { el.remove(); }, 220);
    }, dur);
  };
})();
