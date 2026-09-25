/* BPAccount — hesap istemcisi (C-41, D-50 sozlesmesi v1).

   Takip listesi ve portfoy TARAYICIDA degil HESAPTA durur (O16g=B); giris
   sifresiz: e-posta + 6 haneli kod (O24=A). Bu dosya /takip, hisse sayfasi
   ve Piyasa seridinin paylastigi TEK istemcidir:
     - API cagrilari (sozlesmedeki uclar, baska uc yok),
     - `bp_li` ipucu cerezi (HttpOnly DEGIL, sir tasimaz; yalniz "bu
       tarayicida oturum var mi" sorusunu cevaplar — oturumu olmayan
       ziyaretci SIFIR hesap istegi yapar),
     - giris paneli (e-posta + KVKK -> kod -> hesap hazir).

   CSRF kurali (sozlesme): GET disindaki her cagri JSON govde +
   `Content-Type: application/json` + `credentials:'same-origin'` ile gider,
   DELETE dahil (`{}`). 401 gelince ipucu cerezi silinir: oturum dusmustur.

   Yerel kayitlar (`bp_watchlist_v2`, `bp_portfolio`) SILINMEZ ve
   DEGISTIRILMEZ: girisli kullanicida yedek, girissizde tek kaynak olarak
   kalirlar. Ilk giriste (bu tarayicida `bp_acct_imported` isareti yoksa)
   hesaba aktarilirlar; sunucu birlestirir, sayimi SUNUCU verir. */
(function () {
  'use strict';
  if (window.BPAccount) return;

  var HINT_RE = /(?:^|;\s*)bp_li=/;
  var FLAG_KEY = 'bp_acct_imported';
  var WATCH_KEY = 'bp_watchlist_v2';
  var PF_KEY = 'bp_portfolio';
  var EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
  var RESEND_S = 30;
  var uid = 0;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function hasHint() { return HINT_RE.test(document.cookie || ''); }
  function clearHint() {
    document.cookie = 'bp_li=; Max-Age=0; Path=/; Secure; SameSite=Lax';
    /* Secure'suz yazilmis bir ipucu (yerel gelistirme) da silinsin. */
    if (hasHint()) document.cookie = 'bp_li=; Max-Age=0; Path=/; SameSite=Lax';
  }

  /* Tek cagri kalibi. Donus hep cozulur: {ok, status, data, error, message}.
     ok = HTTP 2xx VE govdede ok:true (K-BK: 200 + bos/bozuk govde basari
     degildir). status 0 = ag hatasi. */
  function call(method, url, body) {
    var opt = { method: method, credentials: 'same-origin', headers: { 'Accept': 'application/json' } };
    if (method !== 'GET') {
      opt.headers['Content-Type'] = 'application/json';
      opt.body = JSON.stringify(body || {});
    }
    return fetch(url, opt).then(function (r) {
      return r.json().then(function (j) { return j; }, function () { return null; }).then(function (j) {
        var d = (j && typeof j === 'object') ? j : {};
        if (r.status === 401) clearHint();
        return {
          ok: r.ok && d.ok === true, status: r.status, data: d,
          error: d.error || (r.ok ? '' : 'http_' + r.status), message: d.message || ''
        };
      });
    }, function () {
      return { ok: false, status: 0, data: {}, error: 'network', message: '' };
    });
  }

  function tk(t) { return encodeURIComponent(String(t || '').toUpperCase()); }

  function me() {
    return call('GET', '/api/me').then(function (res) {
      if (res.status === 200 && res.data.logged_in === false) clearHint();
      return res;
    });
  }

  /* Yerel kayit okuyucu: bozuk kayit null doner, DOKUNULMAZ (K-BM). */
  function readLocal(key) {
    try {
      var v = JSON.parse(localStorage.getItem(key) || 'null');
      return Array.isArray(v) ? v : null;
    } catch (e) {
      console.warn('yerel kayit okunamadi:', key, e);
      return null;
    }
  }

  function importDone() {
    try { return !!localStorage.getItem(FLAG_KEY); } catch (e) { return false; }
  }
  function markImported() {
    try { localStorage.setItem(FLAG_KEY, '1'); } catch (e) { console.warn('aktarim isareti yazilamadi:', e); }
  }
  function resetImported() {
    try { localStorage.removeItem(FLAG_KEY); } catch (e) { console.warn('aktarim isareti silinemedi:', e); }
  }

  /* Ilk giriste gonderilecek yerel liste. Isaret varsa ya da iki kayit da
     bossa null. Diziler sunucuya OLDUGU GIBI gider (sozlesme: ham
     `bp_watchlist_v2` ve ham `bp_portfolio` kabul edilir). */
  function localImportPayload() {
    if (importDone()) return null;
    var w = readLocal(WATCH_KEY) || [];
    var p = readLocal(PF_KEY) || [];
    if (!w.length && !p.length) return null;
    return { watchlist: w, portfolio: p };
  }

  function localCount() {
    var seen = {};
    (readLocal(WATCH_KEY) || []).forEach(function (t) { if (typeof t === 'string') seen[t] = 1; });
    (readLocal(PF_KEY) || []).forEach(function (x) { if (x && typeof x.ticker === 'string') seen[x.ticker] = 1; });
    return Object.keys(seen).length;
  }

  /* Aktarim bildirimi: sayim SUNUCUNUN cevabindan (K-BI). Hicbir sey
     eklenmediyse bos metin. */
  function importMessage(imp) {
    if (!imp) return '';
    var w = +imp.watchlist_added || 0, p = +imp.portfolio_added || 0;
    if (w > 0) return 'Tarayıcındaki ' + w + ' hisse hesabına aktarıldı' + (p > 0 ? ' · ' + p + ' pozisyon' : '');
    if (p > 0) return 'Tarayıcındaki ' + p + ' pozisyon hesabına aktarıldı';
    return '';
  }

  function maskEmail(e) {
    var p = String(e || '').split('@');
    if (p.length < 2 || !p[0]) return String(e || '');
    return p[0].slice(0, 2) + '•••@' + p[1];
  }

  /* ── Giris paneli ─────────────────────────────────────────────────────
     Tek adimda satir ici acilir (modal yok). Adimlar: e-posta -> kod.
     opts: contextTicker, title, sub, onSuccess(me, imported),
           localLabel + onLocal (istege bagli ikincil eylem). */
  function mountLogin(el, opts) {
    opts = opts || {};
    var id = 'acc' + (++uid);
    var st = { step: 'email', email: '', kvkk: false, busy: false, sent: 0, locked: false };
    var timer = null;

    function defTitle() { return opts.contextTicker ? 'E-postayla takip' : 'Takip listen hesabında'; }
    function defSub() {
      return opts.contextTicker
        ? esc(opts.contextTicker) + ' takip listene eklenir; trend durumu değişince e-posta gelir. Listen hesabında durur, her cihazda aynı.'
        : 'Takip listen, istersen portföyün ve e-posta bildirimlerin her cihazda aynı. Şifre yok: e-postana gelen kodla girersin.';
    }

    function emailHTML() {
      var n = localImportPayload() ? localCount() : 0;
      return '<form class="acc-f" id="' + id + '-f" novalidate aria-labelledby="' + id + '-t">' +
        '<p class="acc-t" id="' + id + '-t">' + esc(opts.title || defTitle()) + '</p>' +
        '<p class="acc-s">' + (opts.sub || defSub()) + '</p>' +
        '<label class="sr-only" for="' + id + '-e">E-posta adresin</label>' +
        '<input class="acc-in" id="' + id + '-e" type="email" inputmode="email" autocomplete="email" spellcheck="false" placeholder="E-posta adresin" value="' + esc(st.email) + '">' +
        '<p class="acc-err" id="' + id + '-er" role="alert" hidden></p>' +
        '<label class="acc-kv"><input type="checkbox" class="da-check" id="' + id + '-k"' + (st.kvkk ? ' checked' : '') + '>' +
        '<span><a href="/gizlilik" target="_blank" rel="noopener" class="da-link">KVKK aydınlatma metnini<span class="sr-only"> (yeni sekmede açılır)</span></a> okudum; bu adrese e-posta gönderilmesini onaylıyorum.</span></label>' +
        '<button type="submit" class="acc-b"' + (st.kvkk ? '' : ' disabled') + '>Kod gönder</button>' +
        '<p class="acc-n">Şifre yok: e-postana 6 haneli bir kod gelir. Oturum bu cihazda 90 gün açık kalır.' +
        (n ? ' Bu tarayıcıdaki ' + n + ' hisse oturum açınca hesabına aktarılır.' : '') + '</p>' +
        (opts.localLabel ? '<button type="button" class="acc-lnk acc-local" data-acc="local">' + esc(opts.localLabel) + '</button>' : '') +
        '</form>';
    }

    function codeHTML() {
      return '<form class="acc-f acc-f--code" id="' + id + '-f" novalidate aria-labelledby="' + id + '-t">' +
        '<p class="acc-t" id="' + id + '-t">Kodu gir</p>' +
        '<p class="acc-s">6 haneli kodu <b>' + esc(maskEmail(st.email)) + '</b> adresine gönderdik. 10 dakika geçerli.</p>' +
        '<label class="sr-only" for="' + id + '-c">6 haneli kod</label>' +
        '<input class="acc-in acc-code" id="' + id + '-c" type="text" inputmode="numeric" autocomplete="one-time-code" maxlength="6" pattern="[0-9]{6}" placeholder="000000">' +
        '<p class="acc-err" id="' + id + '-er" role="alert" hidden></p>' +
        '<button type="submit" class="acc-b"' + (st.locked ? ' disabled' : '') + '>Oturum aç</button>' +
        '<p class="acc-lnks"><button type="button" class="acc-lnk" data-acc="fix">Adresi düzelt</button>' +
        '<span aria-hidden="true">·</span><button type="button" class="acc-lnk" data-acc="resend">Kodu yeniden gönder</button></p>' +
        '<p class="acc-n">Birkaç dakikada gelmezse istenmeyen e-posta klasörüne bak.</p>' +
        '</form>';
    }

    function q(sel) { return el.querySelector(sel); }

    function setErr(msg, field) {
      var er = q('.acc-err');
      if (!er) return;
      er.textContent = msg || '';
      er.hidden = !msg;
      var inp = field ? q(field) : null;
      [].forEach.call(el.querySelectorAll('.acc-in'), function (x) {
        if (msg && x === inp) { x.setAttribute('aria-invalid', 'true'); x.setAttribute('aria-describedby', id + '-er'); }
        else { x.removeAttribute('aria-invalid'); x.removeAttribute('aria-describedby'); }
      });
    }

    function setBusy(on, label) {
      st.busy = on;
      var b = q('.acc-b');
      if (!b) return;
      if (on) { b.dataset.l = b.textContent; b.textContent = label; b.disabled = true; b.setAttribute('aria-busy', 'true'); }
      else {
        if (b.dataset.l) b.textContent = b.dataset.l;
        b.removeAttribute('aria-busy');
        b.disabled = st.step === 'email' ? !st.kvkk : st.locked;
      }
    }

    function tickResend() {
      var b = q('[data-acc="resend"]');
      if (!b) return;
      var left = Math.ceil((st.sent + RESEND_S * 1000 - Date.now()) / 1000);
      if (left > 0) { b.disabled = true; b.textContent = 'Kodu yeniden gönder · ' + left + ' sn'; }
      else { b.disabled = false; b.textContent = 'Kodu yeniden gönder'; clearInterval(timer); timer = null; }
    }
    function armResend() {
      clearInterval(timer);
      tickResend();
      timer = setInterval(tickResend, 1000);
    }

    function render(focusSel) {
      el.innerHTML = '<div class="acc acc--' + st.step + '">' + (st.step === 'email' ? emailHTML() : codeHTML()) + '</div>';
      if (st.step === 'code') armResend();
      if (focusSel) { var f = q(focusSel); if (f) f.focus({ preventScroll: true }); }
    }

    function serverMsg(res, fallback) {
      if (res.status === 0) return 'Bağlantı kurulamadı. Birazdan yeniden dene.';
      return res.message || fallback;
    }

    function sendCode(isResend) {
      if (st.busy) return;
      setErr('');
      setBusy(true, 'Gönderiliyor…');
      A.requestCode(st.email, true).then(function (res) {
        setBusy(false);
        if (res.ok) {
          st.sent = Date.now(); st.locked = false;
          if (st.step !== 'code') { st.step = 'code'; render('.acc-code'); }
          else { armResend(); var c = q('.acc-code'); if (c) { c.value = ''; c.focus(); } }
          if (isResend) setErr('');
          return;
        }
        if (res.error === 'email_invalid' && st.step !== 'email') { st.step = 'email'; render(); }
        setErr(serverMsg(res, 'Kod gönderilemedi. Birazdan yeniden dene.'), res.error === 'email_invalid' ? '.acc-in' : null);
      });
    }

    function verifyCode() {
      if (st.busy || st.locked) return;
      var inp = q('.acc-code');
      var code = String(inp && inp.value || '').replace(/\D/g, '');
      if (code.length !== 6) { setErr('6 haneli kodu yaz.', '.acc-code'); return; }
      setErr('');
      setBusy(true, 'Oturum açılıyor…');
      var payload = localImportPayload();
      A.verify(st.email, code, payload).then(function (res) {
        setBusy(false);
        if (res.ok) {
          clearInterval(timer);
          markImported();
          var m = res.data.me || {};
          if (typeof opts.onSuccess === 'function') opts.onSuccess(m, res.data.imported || null);
          return;
        }
        var msg;
        if (res.error === 'code_invalid' && typeof res.data.attempts_left === 'number') {
          msg = 'Kod yanlış. ' + res.data.attempts_left + ' deneme hakkın kaldı.';
        } else if (res.error === 'locked') {
          st.locked = true; setBusy(false);
          msg = serverMsg(res, 'Çok fazla yanlış deneme. Bir süre sonra yeni kod iste.');
        } else if (res.error === 'code_expired') {
          st.sent = 0; tickResend();
          msg = serverMsg(res, 'Kod geçersiz ya da süresi doldu. Yeni kod iste.');
        } else {
          msg = serverMsg(res, 'Oturum açılamadı. Birazdan yeniden dene.');
        }
        if (inp) inp.select();
        setErr(msg, '.acc-code');
      });
    }

    el.addEventListener('submit', function (e) {
      if (!e.target.closest || !e.target.closest('.acc-f')) return;
      e.preventDefault();
      if (st.step === 'email') {
        var inp = q('.acc-in');
        st.email = String(inp && inp.value || '').trim();
        if (!st.kvkk) return;
        if (!EMAIL_RE.test(st.email)) { setErr('Geçerli bir e-posta adresi yaz.', '.acc-in'); if (inp) inp.focus(); return; }
        sendCode(false);
      } else {
        verifyCode();
      }
    });
    el.addEventListener('change', function (e) {
      if (e.target && e.target.id === id + '-k') {
        st.kvkk = !!e.target.checked;
        var b = q('.acc-b');
        if (b && !st.busy) b.disabled = !st.kvkk;
      }
    });
    el.addEventListener('input', function (e) {
      var t = e.target;
      if (!t || !t.classList) return;
      if (t.id === id + '-e') { st.email = t.value; if (t.getAttribute('aria-invalid')) setErr(''); }
      if (t.classList.contains('acc-code')) {
        var v = t.value.replace(/\D/g, '').slice(0, 6);
        if (v !== t.value) t.value = v;
        if (v.length === 6 && !st.busy) verifyCode();
      }
    });
    el.addEventListener('click', function (e) {
      var a = e.target.closest && e.target.closest('[data-acc]');
      if (!a || !el.contains(a)) return;
      var k = a.getAttribute('data-acc');
      if (k === 'fix') { clearInterval(timer); st.step = 'email'; st.locked = false; render('.acc-in'); }
      else if (k === 'resend') sendCode(true);
      else if (k === 'local' && typeof opts.onLocal === 'function') opts.onLocal();
    });

    render();
    return {
      el: el,
      focus: function () { var f = q('.acc-in'); if (f) f.focus(); },
      destroy: function () { clearInterval(timer); el.innerHTML = ''; }
    };
  }

  var A = window.BPAccount = {
    hasHint: hasHint,
    clearHint: clearHint,
    me: me,
    requestCode: function (email, kvkk) { return call('POST', '/api/auth/code', { email: email, kvkk: kvkk === true }); },
    verify: function (email, code, importData) {
      var b = { email: email, code: code };
      if (importData) b['import'] = importData;
      return call('POST', '/api/auth/verify', b);
    },
    logout: function (all) {
      return call('POST', '/api/auth/logout', all ? { all: true } : {}).then(function (r) { if (r.ok) clearHint(); return r; });
    },
    watchlist: function () { return call('GET', '/api/me/watchlist'); },
    add: function (t) { return call('POST', '/api/me/watchlist', { ticker: String(t || '').toUpperCase() }); },
    remove: function (t) { return call('DELETE', '/api/me/watchlist/' + tk(t), {}); },
    replace: function (list, portfolio) {
      var b = { watchlist: list };
      if (portfolio) b.portfolio = portfolio;
      return call('PUT', '/api/me/watchlist', b);
    },
    portfolio: function () { return call('GET', '/api/me/portfolio'); },
    setPosition: function (t, qty, cost) { return call('PUT', '/api/me/portfolio/' + tk(t), { qty: qty, cost: cost }); },
    removePosition: function (t) { return call('DELETE', '/api/me/portfolio/' + tk(t), {}); },
    importData: function (payload) { return call('POST', '/api/me/import', payload || {}); },
    prefs: function (obj) { return call('POST', '/api/me/prefs', obj || {}); },
    deleteAccount: function () {
      return call('DELETE', '/api/me', {}).then(function (r) { if (r.ok) clearHint(); return r; });
    },
    localImportPayload: localImportPayload,
    resetImported: resetImported,
    importMessage: importMessage,
    maskEmail: maskEmail,
    mountLogin: mountLogin
  };
})();
