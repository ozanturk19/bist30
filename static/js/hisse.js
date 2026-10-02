/* ── Sinyal görünen etiketleri ───────────────────── */
window.toggleIndDetails = function() {
  const det = document.getElementById('indTechDetails');
  const btn = document.getElementById('indDetailToggle');
  if (!det || !btn) return;
  const open = det.style.display !== 'none';
  det.style.display = open ? 'none' : 'block';
  btn.innerHTML = open ? 'Detaylı göster ▾' : 'Detayları gizle ▴';
  /* K-AO: gorsel ok isareti (▾/▴) makine tarafindan okunabilir bir durum
     DEGILDIR — aria-expanded tek kanonik kaynaktir. */
  btn.setAttribute('aria-expanded', open ? 'false' : 'true');
};

let LC = null;
function _loadChartLib() {
  if (LC) return Promise.resolve();
  return new Promise(function(res, rej) {
    var s = document.createElement('script');
    s.src = '/static/lightweight-charts.min.js?v=86b4c600';
    s.onload  = function() { LC = LightweightCharts; res(); };
    s.onerror = function() { s.remove(); rej(new Error('lightweight-charts yuklenemedi')); };
    document.head.appendChild(s);
  });
}

/* ── Grafik eksen label formatı ─────────────────────────
   Sorunlar çözülüyor:
   1. DayOfMonth tick'i "10" → "Nis 10" (bağlam kazanıyor)
   2. timeVisible:false ile crosshair'de "00:00:00" kalkıyor
   3. setVisibleLogicalRange from değeri -260 ile sol label kırpılması engelleniyor */
const _MTHS = ['Oca','Şub','Mar','Nis','May','Haz','Tem','Ağu','Eyl','Eki','Kas','Ara'];
/* K-BL (21.09) — ÖLÜ KOPYA KALDIRILDI. Burada `_tickFmt(time, type)` adıyla,
   `static/js/bp-chart-common.js` içindeki `fmtTickDate` ile SATIR SATIR aynı
   fonksiyon duruyordu. bp-chart-common.js'in kendi dosya başlığı bu dosyayla
   arasındaki kopya-bakım riskini gerekçe göstererek yazılmıştı; konsolidasyon
   sırasında bu kopya silinmemiş. Üstelik çağrılmıyordu da: bu sayfa hafta
   sonu boşluğu olmasın diye sequential-index eksenini ve kendi
   `_tickFmtIdx`ini kullanıyor (K-BE ile aynı aile: hisse.html'de duran, ama
   yürümeyen ikinci bir yazım). `_MTHS` KALIYOR — `_tickFmtIdx` ve
   `_fmtDateShort` onu kullanıyor. Tarih ekseni formatı gerekirse kanon
   `BPChart.fmtTickDate`tır. */

const TICKER  = window.BP.ticker;
/* K-AN (21.09) TR SAYI BIÇIMI — KANONIK. Ham bir JS sayısı string'e
   eklendiğinde "130.4" yazılır; sitenin her yerinde kanonik biçim "130,4"tür.
   Ölçüldü: aynı ADX değeri görünür rozette "36,8" iken "Detaylı göster"
   gövdesinde "36.8" idi — tek satır arayla, aynı kartta. DUYARLILIK
   DEĞIŞMEZ: yalnızca ayraç çevrilir, yuvarlama/dolgu yapılmaz.
   (Sabit 2 ondalık gerektiğinde toLocaleString('tr-TR') kalıbı kullanılır.) */
const _trNum = (v) => (v == null || v === '') ? '\u2014' : String(v).replace('.', ',');

const HISSE_NAME = window.BP.name;
/* C-19 (25.09): sayfanin kendi SSR kaydi (/api/data satirinin aynisi, app.py stock_page
   ssr_signal). Eskiden grafik yuklenince /api/data (~290 KB, 216 hisse) indirilip bu
   kayit client'ta aranirdi; artik istek yok, ayni veri sunucudan gelir. */
const BP_SSR = window.BP.ssr;
window._bpLastSignalData = BP_SSR.ticker ? BP_SSR : null;

/* ── ⭐ Portfolio + 🔔 Watchlist toggle (LOCAL STORAGE) ── */
const HIB_PF_KEY    = 'bp_portfolio';
const HIB_WATCH_KEY = 'bp_watchlist_v2';        // Faz 1 #2: versionleme (yalnız bu sayfada; giriş yoksa TEK kaynak)
const HIB_WATCH_KEY_LEGACY = 'bp_watchlist';    // migration kaynağı

/* ── C-41 (25.09): TAKİP DURUMUNUN SAHİBİ HESAPTIR ─────────────────────
   K-CU (22.09) durumu sunucudaki e-posta alarmından okuyordu ama oturumu
   `bp_sub` çerezinden anlıyordu — o çerez HttpOnly, JS onu HİÇ göremez:
   eski `_hibLoggedIn()` her ziyaretçide false dönüyordu, sunucu dalı hiç
   yürümüyordu. Artık (O16g=B, D-50 sözleşmesi) liste HESAPTA durur:
     • `bp_li` ipucu çerezi yoksa hesap isteği YOK; durum yerel listeden
       (bp_watchlist_v2) okunur, düğme satır içi oturum panelini açar.
     • İpucu varsa GET /api/me/watchlist gerçeğin sahibidir; ekle/çıkar
       POST/DELETE /api/me/watchlist (iyimser, !ok ise geri alınır).
   Durumu okuyan TEK yer yine `_hibWatchState()` ([[K-CT]] 111. ders). */
let _hibAcct = null;          // Set: hesaptaki liste (yalnız _hibAcctState === 'ok')
let _hibAcctState = 'out';    // 'out' | 'pending' | 'ok' | 'failed'

/* Takip durumunun TEK OKUYUCUSU → 'on' | 'off' | 'pending' | 'unknown' */
function _hibWatchState() {
  if (_hibAcctState === 'pending') return 'pending';
  if (_hibAcctState === 'ok') return (_hibAcct && _hibAcct.has(TICKER)) ? 'on' : 'off';
  if (_hibAcctState === 'failed') return 'unknown';   // K-BW: okunamayan ≠ "takipte değil"
  let w;
  try { w = JSON.parse(localStorage.getItem(HIB_WATCH_KEY) || '[]'); }
  catch (e) { console.warn('takip listesi okunamadi:', e); return 'unknown'; }
  if (!Array.isArray(w)) return 'unknown';
  return w.includes(TICKER) ? 'on' : 'off';
}

/* Hesaptaki listeyi oku (yalnız ipucu çerezi varsa; yoksa istek yok). */
function _hibLoadAccount() {
  if (!window.BPAccount || !BPAccount.hasHint()) { _hibAcctState = 'out'; updateHibBellBtn(); return; }
  _hibAcctState = 'pending';
  updateHibBellBtn();
  BPAccount.watchlist().then(res => {
    if (res.ok && Array.isArray(res.data.watchlist)) { _hibAcct = new Set(res.data.watchlist); _hibAcctState = 'ok'; }
    else if (res.status === 401) { _hibAcct = null; _hibAcctState = 'out'; }
    else { console.warn('hesap takip listesi okunamadi:', res.status, res.error); _hibAcctState = 'failed'; }
    updateHibBellBtn();
  });
}

/* Faz 1 #2: v1 → v2 migration (idempotent, ilk ziyarette tetiklenir) */
(function _hibMigrateWatch() {
  try {
    if (localStorage.getItem(HIB_WATCH_KEY) !== null) return;
    const legacy = localStorage.getItem(HIB_WATCH_KEY_LEGACY);
    if (!legacy) return;
    const parsed = JSON.parse(legacy);
    if (Array.isArray(parsed) && parsed.length > 0) {
      localStorage.setItem(HIB_WATCH_KEY, JSON.stringify(parsed));
    }
  } catch (e) { console.warn('hisse.html watch migration fail:', e); }
})();

function _hibToast(msg, type) {
  const t = document.getElementById('hibToast');
  if (!t) return;
  t.textContent = msg;
  t.className = 'hib-toast show' + (type ? ' ' + type : '');
  // CPO-DEV2-090: kanonik toast suresi - basari/standart=3000ms, hata=4000ms (2 kategori);
  // 'warn' bu dosyada hep basarisizlik/hata mesajlari icin kullaniliyor (kaydedilemedi/okunamadi)
  const ms = (type === 'warn') ? 4000 : 3000;
  clearTimeout(t._timer);
  t._timer = setTimeout(() => { t.classList.remove('show'); }, ms);
}

function _hibCurrentPrice() {
  // window._bpLastSignalData — renderSummary() en son çağrıldığında set edilir (bkz. renderSummary)
  try {
    if (window._bpLastSignalData && window._bpLastSignalData.price != null && isFinite(+window._bpLastSignalData.price)) return +window._bpLastSignalData.price;
  } catch(_) { /* henuz hazir olmayabilir (sayfa yuklenirken) - DOM fallback asagida devrede */ }
  // Fallback: header'daki gösterilen fiyat
  const txt = document.getElementById('hpPrice')?.textContent || '';
  const num = parseFloat(txt.replace(/\./g,'').replace(',','.'));
  // K-BJ: fiyat okunamadiginda 0 DONUYORDU ve bu 0 dogrudan portfoye MALIYET
  // olarak yaziliyordu (hpPrice SSR'da fiyat yoksa '—' basar, o an quick-add'e
  // basmak mumkun). Maliyeti 0 olan pozisyon /portfolio'da cost=0 uretir, K/Z
  // pozisyonun TAM degerini "kar" gosterir ve toplam K/Z kutusunu sisirir.
  // "Fiyat yok" ile "fiyat sifir" ayri seylerdir -> null.
  return isFinite(num) ? num : null;
}

function togglePortfolio() {
  let pf;
  try {
    pf = JSON.parse(localStorage.getItem(HIB_PF_KEY) || '[]');
  } catch (e) {
    console.warn('hisse portfolio read fail, islem iptal (veri korundu):', e);
    _hibToast('Portföy verisi okunamadı, işlem iptal edildi — mevcut verin korundu', 'warn');
    return;
  }
  if (!Array.isArray(pf)) {
    console.warn('hisse portfolio beklenmeyen format, islem iptal (veri korundu)');
    _hibToast('Portföy verisi bozuk görünüyor, işlem iptal edildi — mevcut verin korundu', 'warn');
    return;
  }

  const idx = pf.findIndex(x => x && x.ticker === TICKER);
  if (idx >= 0) {
    pf.splice(idx, 1);
    if (_hibSafeWritePortfolio(pf)) {
      _hibToast(TICKER + ' portföyden çıkarıldı', 'warn');
      updateHibStarBtn();
    }
  } else {
    const price = _hibCurrentPrice();
    // K-BJ: pozisyon yazan diger UC yol (form / dosya / sunucu) lot+fiyati
    // dogruluyordu, bu yol HIC dogrulamiyordu — tek kanon bp-format.js.
    if (!bpIsValidPrice(price)) {
      _hibToast('Güncel fiyat henüz yüklenmedi — portföye eklenmedi. Birkaç saniye sonra tekrar deneyin veya /portfolio\'dan elle ekleyin.', 'warn');
      return;
    }
    pf.push({
      ticker: TICKER,
      lot:    1,
      price:  price,
      date:   bpTodayTrIso(),  // K-BD: tek kanon (bp-format.js)
      id:     Date.now(),
      source: 'hisse-detail-quick',
    });
    if (_hibSafeWritePortfolio(pf)) {
      _hibToast(TICKER + ' portföye eklendi (1 lot · ' + price.toLocaleString('tr-TR', {minimumFractionDigits:2,maximumFractionDigits:2}) + '₺) · /portfolio\'da düzenle', 'success');
      updateHibStarBtn();
    }
  }
}

/* Faz 1 #2: Safe write + read-back verify (bkz. _hibSafeWriteWatch ile aynı desen) */
function _hibSafeWritePortfolio(arr) {
  try {
    const json = JSON.stringify(arr);
    localStorage.setItem(HIB_PF_KEY, json);
    if (localStorage.getItem(HIB_PF_KEY) !== json) {
      console.warn('hisse portfolio write verify FAIL (quota? private mode?)');
      _hibToast('Portföy kaydedilemedi (tarayıcı kısıtı)', 'warn');
      return false;
    }
    return true;
  } catch (e) {
    console.warn('hisse portfolio write fail:', e);
    _hibToast('Portföy kaydedilemedi', 'warn');
    return false;
  }
}

/* Faz 1 #2: Safe write + read-back verify */
function _hibSafeWriteWatch(arr) {
  try {
    const json = JSON.stringify(arr);
    localStorage.setItem(HIB_WATCH_KEY, json);
    if (localStorage.getItem(HIB_WATCH_KEY) !== json) {
      console.warn('hisse watch write verify FAIL (quota? private mode?)');
      _hibToast('Takip listesi kaydedilemedi (tarayıcı kısıtı)', 'warn');
      return false;
    }
    return true;
  } catch (e) {
    console.warn('hisse watch write fail:', e);
    _hibToast('Takip listesi kaydedilemedi', 'warn');
    return false;
  }
}

let _hibWatchToggleInFlight = false;
function toggleHisseWatch() {
  // bug-hunt-r126/r143 async guard: istek bitene kadar ikinci cagri no-op.
  if (_hibWatchToggleInFlight) return;
  const st = _hibWatchState();
  if (st === 'pending') { _hibToast('Takip durumun kontrol ediliyor, bir saniye…', 'warn'); return; }
  if (_hibAcctState === 'failed') { _hibLoadAccount(); return; }          // okunamadı → yeniden dene
  if (_hibAcctState === 'ok') { _hibAccountToggle(st === 'on'); return; }
  /* Oturum yok: yerelde takipteyse (eski davranış) bu cihazdan çıkar; değilse
     oturum paneli açılır/kapanır. */
  if (st === 'unknown') { _hibToast('Takip listesi okunamadı, işlem iptal edildi — mevcut verin korundu', 'warn'); return; }
  if (st === 'on') { _hibLocalToggle(false); return; }
  _hibOpenLogin();
}

/* Hesaptaki listeye ekle/çıkar — iyimser; sunucu reddederse geri alınır (K-CU):
   düğme sunucuda olmayan bir durumu göstermez. */
function _hibAccountToggle(remove) {
  const btn = document.getElementById('hibBellBtn');
  _hibWatchToggleInFlight = true;
  if (btn) btn.disabled = true;
  if (remove) _hibAcct.delete(TICKER); else _hibAcct.add(TICKER);
  updateHibBellBtn();
  (remove ? BPAccount.remove(TICKER) : BPAccount.add(TICKER)).then(res => {
    if (res.ok && Array.isArray(res.data.watchlist)) {
      _hibAcct = new Set(res.data.watchlist);
      _hibToast(TICKER + (remove ? ' takip listenden çıkarıldı' : ' takip listene eklendi'), remove ? 'warn' : 'success');
      return;
    }
    if (remove) _hibAcct.add(TICKER); else _hibAcct.delete(TICKER);
    if (res.status === 401) { _hibAcct = null; _hibAcctState = 'out'; _hibToast('Oturumun kapanmış; yeniden oturum aç.', 'warn'); return; }
    _hibToast(res.message || (TICKER + (remove ? ' listeden çıkarılamadı' : ' listene eklenemedi') + (res.status === 0 ? ' (bağlantı hatası)' : '')), 'warn');
  }).finally(() => {
    _hibWatchToggleInFlight = false;
    const b2 = document.getElementById('hibBellBtn');
    if (b2) b2.disabled = false;
    updateHibBellBtn();
  });
}

/* Oturumsuz yedek: yalnız bu cihazın listesi (eski davranış). Eklerken hesaba
   aktarım işareti sıfırlanır: sonraki oturum açışta liste hesaba aktarılır. */
function _hibLocalToggle(add) {
  let w;
  try { w = JSON.parse(localStorage.getItem(HIB_WATCH_KEY) || '[]'); }
  catch (e) {
    console.warn('hisse watch read fail, islem iptal (veri korundu):', e);
    _hibToast('Takip listesi okunamadı, işlem iptal edildi — mevcut verin korundu', 'warn');
    return;
  }
  if (!Array.isArray(w)) { _hibToast('Takip listesi bozuk görünüyor, işlem iptal edildi — mevcut verin korundu', 'warn'); return; }
  const idx = w.indexOf(TICKER);
  if (add && idx < 0) w.push(TICKER);
  if (!add && idx !== -1) w.splice(idx, 1);
  if (_hibSafeWriteWatch(w)) {
    if (add && window.BPAccount) BPAccount.resetImported();
    _hibToast(add ? TICKER + ' bu cihazda takipte · oturum açınca hesabına aktarılır' : TICKER + ' bu cihazdaki takipten çıkarıldı', add ? 'success' : 'warn');
  }
  updateHibBellBtn();
}

/* Oturum paneli (BPAccount.mountLogin) eylem satırının hemen altında; tek adım,
   modal yok. İkinci dokunuş ya da Esc kapatır. */
let _hibLoginCtl = null;
function _hibOpenLogin(open) {
  const slot = document.getElementById('hibLogin');
  if (!slot || !window.BPAccount) return;
  if (open === undefined) open = slot.hidden;
  if (!open) {
    if (_hibLoginCtl) { _hibLoginCtl.destroy(); _hibLoginCtl = null; }
    slot.hidden = true;
    updateHibBellBtn();
    return;
  }
  slot.hidden = false;
  _hibLoginCtl = BPAccount.mountLogin(slot, {
    contextTicker: TICKER,
    localLabel: 'Şimdilik yalnız bu cihazda takip et',
    onLocal: () => { _hibOpenLogin(false); _hibLocalToggle(true); const b = document.getElementById('hibBellBtn'); if (b) b.focus(); },
    onSuccess: (me, imported) => { _hibAfterLogin(imported); }
  });
  updateHibBellBtn();
  _hibLoginCtl.focus();
}
function _hibAfterLogin(imported) {
  const note = BPAccount.importMessage(imported);
  _hibOpenLogin(false);
  _hibAcctState = 'pending';
  updateHibBellBtn();
  BPAccount.add(TICKER).then(res => {
    if (!(res.ok && Array.isArray(res.data.watchlist))) {
      _hibToast(res.message || (TICKER + ' listene eklenemedi; yeniden dene.'), 'warn');
      _hibLoadAccount();
      return;
    }
    _hibAcct = new Set(res.data.watchlist);
    _hibAcctState = 'ok';
    updateHibBellBtn();
    _hibToast(TICKER + ' takip listene eklendi' + (note ? ' · ' + note : ''), 'success');
    const b = document.getElementById('hibBellBtn');
    if (b) b.focus();
  });
}
document.addEventListener('keydown', e => {
  if (e.key !== 'Escape') return;
  const slot = document.getElementById('hibLogin');
  if (!slot || slot.hidden || !slot.contains(document.activeElement)) return;
  _hibOpenLogin(false);
  const b = document.getElementById('hibBellBtn');
  if (b) b.focus();
});

/* K-BM: kayit okunamadiginda durum BILINMIYOR demektir — "bu hissede
   pozisyonun yok" demek degil. Eski kod catch'te bos dizi ile devam edip
   dugmeyi "Portföye ekle / aria-pressed=false" durumuna getiriyordu, yani
   olcemedigi bir seyi kesin olarak iddia ediyordu ([[K-BK]]: bos != bilinmiyor).
   Artik dugme notr kalir, aria-pressed HIC bildirilmez ve kullaniciya nereden
   kurtaracagi soylenir (/portfolio bozuk kaydi yedekleyip indirtiyor). */
/* ── K-CX (22.09): DURUM DEGISINCE ERISILEBILIR KANAL DA GUNCELLENMELI ──────
   K-AH native `title=`i yasaklamisti cunku dokunmatikte ve klavye odaginda HIC
   gosterilmez; kanonik kanal [data-tip] (bp-tooltip.js: hover+focus+tap+Escape).
   Ama JS ile DURUMA gore yazilan aciklamalar hala `el.title`a gidiyordu ve
   statik `data-tip` ACILIS metninde DONUP kaliyordu. Canli olcum 22.09
   (/hisse/ASELS, izleme listesi dolu): buton "Takipte ✓" gosterirken
   data-tip HALA "Sinyal degisiminde bildirim al" diyordu -- dokunmatik/klavye
   kullanicisina YIKICI eylem (listeden cikarma) TERS tarif ediliyordu.
   K-AH kapisi (title-tooltip-check.js) bunu goremez: `data-tip` VARLIGI onun
   sahte-pozitif muafiyetidir, TAZELIGI degil; ustelik durum/hata/gizli-sekme
   dallari o kosuda hic tetiklenmiyor.
   Tek yazar: aciklama data-tip'e gider, native title HER ZAMAN silinir. */
function _bpTip(el, text) {
  if (!el) return;
  if (text) el.setAttribute('data-tip', text); else el.removeAttribute('data-tip');
  el.removeAttribute('title');   // iki kanal = iki kanon; fare-only kanal kapali
}

function _hibMarkUnknown(btn, ne) {
  if (!btn) return;
  btn.classList.remove('active-portfolio', 'active-star', 'active-bell');
  btn.removeAttribute('aria-pressed');
  const t = ne + ' kaydın okunamadı (bozuk olabilir) — durum bilinmiyor. /portfolio sayfasından kurtarabilirsin.';
  _bpTip(btn, t);
  btn.setAttribute('aria-label', t);
}

function updateHibStarBtn() {
  const btn = document.getElementById('hibStarBtn');
  if (!btn) return;
  let pf = [];
  try {
    pf = JSON.parse(localStorage.getItem(HIB_PF_KEY) || '[]');
    if (!Array.isArray(pf)) throw new Error('not an array');
  } catch(_) {
    console.warn('updateHibStarBtn: portfoy okunamadi', _);
    _hibMarkUnknown(btn, 'Portföy');
    return;
  }
  const inPf = pf.some(x => x && x.ticker === TICKER);
  const lbl = btn.querySelector('.hib-action-lbl');
  if (inPf) {
    btn.classList.add('active-portfolio');
    btn.classList.remove('active-star');
    _bpTip(btn, 'Portföyde — çıkarmak için tıkla');
    if (lbl) lbl.textContent = 'Portföyde ✓';
  } else {
    btn.classList.remove('active-portfolio', 'active-star');
    _bpTip(btn, 'Portföye ekle');
    if (lbl) lbl.textContent = 'Portföye ekle';
  }
  btn.setAttribute('aria-pressed', String(inPf));
  btn.setAttribute('aria-label', inPf ? 'Portföyde' : 'Portföye ekle');
}

function updateHibBellBtn() {
  const btn = document.getElementById('hibBellBtn');
  if (!btn) return;
  /* K-CU: durum tek okuyucudan. 'pending' = hesap cevabı yolda:
     K-BW/K-BM ilkesi — ölçülmemiş bir şey "takipte değil" diye iddia edilmez. */
  const st = _hibWatchState();
  const slot = document.getElementById('hibLogin');
  btn.removeAttribute('aria-expanded');
  btn.removeAttribute('aria-controls');
  if (st === 'unknown') {
    btn.removeAttribute('aria-busy');
    if (!_hibWatchToggleInFlight) btn.disabled = false;
    if (_hibAcctState === 'failed') {
      const t = 'Takip durumun okunamadı; yeniden denemek için dokun';
      btn.classList.remove('active-bell');
      btn.removeAttribute('aria-pressed');
      _bpTip(btn, t);
      btn.setAttribute('aria-label', t);
      const lblF = btn.querySelector('.hib-action-lbl');
      if (lblF) lblF.textContent = 'Takip et';
      return;
    }
    _hibMarkUnknown(btn, 'Takip listesi');   // K-BM: bilinmiyor != takipte degil
    return;
  }
  if (st === 'pending') {
    const lblP = btn.querySelector('.hib-action-lbl');
    btn.classList.remove('active-bell');
    btn.disabled = true;
    btn.setAttribute('aria-busy', 'true');
    btn.removeAttribute('aria-pressed');     // bilinmeyen durum bildirilmez
    _bpTip(btn, 'Takip durumun kontrol ediliyor…');
    btn.setAttribute('aria-label', 'Takip durumu kontrol ediliyor');
    if (lblP) lblP.textContent = 'Kontrol ediliyor…';
    return;
  }
  const inW = (st === 'on');
  const acct = (_hibAcctState === 'ok');
  if (!_hibWatchToggleInFlight) btn.disabled = false;
  btn.removeAttribute('aria-busy');
  const lbl = btn.querySelector('.hib-action-lbl');
  if (inW) {
    btn.classList.add('active-bell');
    /* Hesapta: her cihazda geçerli liste. Oturumsuz: yalnız bu cihazın listesi. */
    _bpTip(btn, acct
      ? 'Takip listende (hesabında, her cihazda) — çıkarmak için tıkla'
      : 'Takipte (yalnız bu cihazda, e-posta gönderilmez) — çıkarmak için tıkla');
    if (lbl) lbl.textContent = 'Takipte ✓';
    btn.setAttribute('aria-pressed', 'true');
    btn.setAttribute('aria-label', 'Takipte');
  } else {
    btn.classList.remove('active-bell');
    _bpTip(btn, 'Durum değişince e-postayla haber al');
    if (lbl) lbl.textContent = 'Takip et';
    btn.setAttribute('aria-label', 'Takip et');
    if (acct) btn.setAttribute('aria-pressed', 'false');
    else {
      /* Oturumsuz ve takipte değil: düğme oturum panelini açar (açılır bölüm). */
      btn.removeAttribute('aria-pressed');
      btn.setAttribute('aria-expanded', String(!!(slot && !slot.hidden)));
      btn.setAttribute('aria-controls', 'hibLogin');
    }
  }
}

// CPO-DEV2-088(A) / r121: cok-sekme senkronizasyonu — index.html'deki storage event
// deseniyle ayni ilke, portfolio.html'deki r37 yorumundaki asil kaynak. Bu sayfada
// updateHibBellBtn() zaten cagrildiginda localStorage'dan taze okuyor (mutate yok,
// sadece render) — eksik olan tek sey diger sekme yazinca bu render'i tetiklemekti.
window.addEventListener('storage', e => {
  if (e.key === HIB_WATCH_KEY) updateHibBellBtn();
  if (e.key === HIB_PF_KEY) updateHibStarBtn();
});

// Init when DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => { updateHibStarBtn(); _hibLoadAccount(); });
} else {
  updateHibStarBtn(); _hibLoadAccount();
}

/* C-07 (25.09): hero "Paylaş" cihazın paylaşım menüsünü açar; destek yoksa
   bağlantıyı kopyalar. Eski "Sinyali Paylaş" paneli (WhatsApp/X/kopyala) kalktı. */
function shareStock() {
  const url = 'https://borsapusula.com/hisse/' + TICKER;
  const title = TICKER + ' · ' + HISSE_NAME;
  if (navigator.share) {
    navigator.share({ title: title, url: url }).catch(() => { /* kullanici paylasimi kapatti */ });
    return;
  }
  const done = ok => _hibToast(ok ? 'Bağlantı kopyalandı' : 'Kopyalanamadı: ' + url, ok ? 'success' : 'warn');
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(url).then(() => done(true), () => done(false));
  } else {
    done(false);
  }
}

/* ── Grafik kurulumu ─────────────────────────────────── */
let _hisseChart = null;        // r140: onceki instance/RO/listener temizligi icin (index.html chartMain deseniyle simetrik)
/* 52-hafta seridindeki guncel-fiyat rozetini imlecin GERCEK pikseline kenetler.
   Yuzde tabanli bir esik (pct<=8 / >=92) rozet genisligi ekran boyuna gore
   degistigi icin ucta 5-7px tasma birakiyordu; burada rozetin kendi genisligi
   olculup pozisyon parcanin icine kirpiliyor. Sekme gizliyken (display:none)
   clientWidth 0 doner — o durumda yuzde-tabanli ilk yerlesim korunur ve sekme
   acilinca bpChartResize/ResizeObserver bu fonksiyonu yeniden cagirir. */
function _syncW52Cap() {
  const cap = document.getElementById('w52cap');
  const tr  = document.querySelector('.week52-track');
  if (!cap || !tr) return;
  const pct = parseFloat(cap.dataset.pct);
  if (!isFinite(pct)) return;
  const trW = tr.clientWidth, capW = cap.offsetWidth;
  if (!trW || !capW) return;
  const half = capW / 2;
  const cx = Math.min(Math.max((trW * pct) / 100, half), Math.max(trW - half, half));
  cap.style.left = cx + 'px';
  cap.style.transform = 'translateX(-50%)';
}

let _hisseChartRO = null;
let _hisseResizeHandler = null;
let _chartResizeT = null;   // r157: resize debounce (sparkline'daki _sparkResizeTimer desenine hizali)

function buildChart(d) {
  /* C-23 (25.09, C-M10 taslagi): sade grafik. Periwinkle kapanis alani (mum/hacim yok --
     Ozan 31.08, kanon §5.3 "grafik cizgisi notr"), mor kademeli trend donus seviyesi
     (st_line; yon degistigi yerde kesilir), son 6 durum degisimi icin etiketsiz oklar
     (signal_history: baslangic + closed_at_date = Yatay'a donus), EMA 12/99 varsayilan
     kapali. 1A/3A/6A/1Y/2Y ciplerle pencere; #chartPeriod GORUNEN pencereyi yazar. */
  if ((d.ohlc || []).length < 2) {
    _showChartStatus('Bu hisse için yeterli grafik verisi yok.', false);
    return;
  }
  if (_hisseChart) { try { _hisseChart.remove(); } catch(_) { console.warn('eski chart instance temizlenemedi', _); } _hisseChart = null; }
  if (_hisseChartRO) { try { _hisseChartRO.disconnect(); } catch(_) { /* zaten disconnect olabilir */ } _hisseChartRO = null; }
  if (_hisseResizeHandler) { window.removeEventListener('resize', _hisseResizeHandler); _hisseResizeHandler = null; }
  document.getElementById('chartLoading').style.display = 'none';
  document.getElementById('chartsInner').style.display  = 'block';

  /* Sirali indeks zaman ekseni (tatil/hafta sonu boslugu yok). */
  var _idxToDay = d.ohlc.map(function(b){ return b.time; });
  var _dayToIdx = {};
  _idxToDay.forEach(function(day, i){ _dayToIdx[day] = i; });
  function _tickFmtIdx(idx, type) {
    var dateStr = _idxToDay[Math.round(+idx)];
    if (!dateStr) return '';
    var p = dateStr.split('-');
    if (type === 0) return p[0];
    if (type === 1) return _MTHS[+p[1] - 1] || '';
    if (type === 2) return (_MTHS[+p[1] - 1] || '') + ' ' + (+p[2]);
    return '';
  }
  function _fmtDay(idx, withYear) {
    var raw = _idxToDay[Math.round(+idx)];
    if (!raw) return '';
    var pts = raw.split('-');
    return (+pts[2]) + ' ' + (_MTHS[+pts[1]-1] || '') + (withYear ? ' ' + pts[0] : '');
  }
  function _reidx(arr) {
    return (arr || []).map(function(p){ var i = _dayToIdx[p.time]; return i !== undefined ? Object.assign({}, p, {time: i}) : null; }).filter(Boolean);
  }
  var n = d.ohlc.length;
  var bars = d.ohlc.map(function(b, i){ return Object.assign({}, b, {time: i}); });
  var closes = bars.map(function(b){ return {time: b.time, value: b.close}; });
  var ema12 = _reidx(d.ema12), ema99 = _reidx(d.ema99), st = _reidx(d.st_line);

  var fmtP = function(v){ return v == null ? '—' : (+v).toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); };
  var fmtPct = function(v){ return (v > 0 ? '+' : v < 0 ? '−' : '') + '%' + Math.abs(v).toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); };

  const elMain   = document.getElementById('chartMain');
  elMain.innerHTML = '';
  const _chartH = function(){ return window.innerWidth < 768 ? 360 : Math.max(420, Math.min(640, Math.round(window.innerHeight * 0.6))); };
  const chartW   = elMain.clientWidth || elMain.parentElement.clientWidth || 900;
  elMain.style.height = _chartH() + 'px';

  const chart = _hisseChart = LC.createChart(elMain, {
    ...BPChart.baseOpts(LC, false),
    width:     chartW,
    height:    _chartH(),
    timeScale: { borderColor: BPChart.tok('--bp-border', '#2a2a2c'), timeVisible: false, visible: true, rightOffset: 6, tickMarkFormatter: _tickFmtIdx },
    /* G26: sirali indeks -> dikey imlec etiketi epoch tarihi basardi; tarih lejantta. */
    crosshair: { mode: LC.CrosshairMode.Magnet, vertLine: { color: BPChart.tok('--bp-chart-crosshair', '#3d5a80'), width: 1, style: 0, labelVisible: false }, horzLine: { color: BPChart.tok('--bp-chart-crosshair', '#3d5a80'), labelBackgroundColor: BPChart.tok('--bp-brand', '#b8c3ff'), width: 1, style: 0 } },
  });

  /* 52-haftalık bar */
  if (d.week52) {
    const lo = d.week52.low, hi = d.week52.high;
    const cur = d.summary.price;
    const pct = hi > lo ? Math.round(((cur - lo) / (hi - lo)) * 100) : 0;
    const fmt = v => v.toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    document.getElementById('w52low').textContent    = fmt(lo) + ' ₺';
    document.getElementById('w52high').textContent   = fmt(hi) + ' ₺';
    document.getElementById('w52cur').textContent    = fmt(cur) + ' ₺';
    document.getElementById('w52fill').style.width   = pct + '%';
    document.getElementById('w52cursor').style.left  = pct + '%';
    /* Fiyat rozeti imlece kenetli (bkz. _syncW52Cap). Once kaba yuzde yerlesimi —
       sekme gizliyken olcum yapilamadigi icin bu fallback gerekli. */
    const w52cap = document.getElementById('w52cap');
    if (w52cap) {
      w52cap.dataset.pct = pct;
      w52cap.style.left = pct + '%';
      w52cap.style.transform = pct <= 8 ? 'translateX(0)'
                             : pct >= 92 ? 'translateX(-100%)'
                             : 'translateX(-50%)';
      requestAnimationFrame(_syncW52Cap);
    }
    const w52pos = document.getElementById('w52pos');
    if (w52pos) w52pos.textContent = hi > lo ? 'Aralığın %' + pct + ' seviyesinde' : '';
    /* CPO-1653 P2: az-geçmişli hisselerde "52 Haftalık" yanlış — backend'in
       fiilen kullandığı bar sayısını (bars_used) dürüstçe göster. */
    const w52label = document.getElementById('w52label');
    if (w52label) {
      /* K-CB (22.09): `bars_used` bir BAR (seans) sayacidir — "Günlük Aralık"
         onu takvim gunuymus gibi sunuyordu (252 bar ~ 365 takvim gunu, yani
         kisa gecmiste de sapma ayni yonde). Canli 22.09 olcumu: 215/215
         hissede bars_used=252 -> is_partial hep false, yani bu dal SU AN OLU;
         yazim yine de kanona (seans) cekildi, canlanirsa dogru cikacak. */
      w52label.textContent = d.week52.is_partial
        ? bpBarWindowText(d.week52.bars_used) + 'lık Aralık (halka arzdan bu yana)'
        : '52 Haftalık Aralık';
    }
    document.getElementById('week52Bar').style.display = '';
  }

  /* Kapanis alani: notr periwinkle + gradyan (kanon §5.3). */
  const brandRgb = BPChart.tok('--bp-brand-rgb', '184,195,255');
  const area = chart.addAreaSeries({
    lineColor: BPChart.tok('--bp-brand', '#b8c3ff'), lineWidth: 2,
    topColor: 'rgba(' + brandRgb + ',0.22)', bottomColor: 'rgba(' + brandRgb + ',0)',
    priceLineVisible: false, lastValueVisible: true, crosshairMarkerRadius: 3,
  });
  area.setData(closes);

  /* Trend donus seviyesi: tek mor kademeli seri; yon degistigi barda segment seffaf
     (LC 4.1'de bosluk noktasi cizgiyi kesmiyor, olculdu) -> cizgi orada kesilir. */
  const violet = BPChart.tok('--bp-art-violet', '#7c5cff');
  if (st.length) {
    const stSer = chart.addLineSeries({ color: violet, lineWidth: 2, lineType: 1, priceLineVisible: false,
      lastValueVisible: true, crosshairMarkerVisible: false });
    stSer.setData(st.map(function(p, i){
      return (i > 0 && !!st[i - 1].bull !== !!p.bull) ? {time: p.time, value: p.value, color: 'rgba(0,0,0,0)'} : {time: p.time, value: p.value};
    }));
    document.getElementById('chStVal').textContent = fmtP(st[st.length - 1].value) + ' ₺';
    document.getElementById('chKeySt').hidden = false;
  }

  /* Son 6 durum degisimi: signal_history'den (AL/SAT baslangici, closed_at_date = Yatay). */
  const _iso = function(tr){ var p = String(tr || '').split('.'); return p.length === 3 ? p[2] + '-' + p[1] + '-' + p[0] : null; };
  const _stName = { up: 'Güçlü Trend', flat: 'Yatay', down: 'Trend Bozuldu' };
  let evs = [];
  (d.signal_history || []).forEach(function(h){
    const s0 = h.signal === 'AL' ? 'up' : h.signal === 'SAT' ? 'down' : null;
    if (s0) evs.push({ day: _iso(h.date), st: s0, pri: 1 });
    if (h.closed_at_date) evs.push({ day: _iso(h.closed_at_date), st: 'flat', pri: 0 });
  });
  evs = evs.filter(function(e){ return e.day && _dayToIdx[e.day] !== undefined; })
           .sort(function(x, y){ return x.day < y.day ? -1 : x.day > y.day ? 1 : x.pri - y.pri; });
  const byDay = {};
  evs.forEach(function(e){ byDay[e.day] = e; });           /* ayni gun: baslangic Yatay'i ezer */
  evs = Object.keys(byDay).sort().map(function(k){ return byDay[k]; })
           .filter(function(e, i, arr){ return i === 0 || arr[i - 1].st !== e.st; }).slice(-6);
  const evAt = {};
  const markers = evs.map(function(e){
    const t = _dayToIdx[e.day]; evAt[t] = e;
    return e.st === 'up'
      ? { time: t, position: 'belowBar', shape: 'arrowUp',   color: BPChart.tok('--bp-al', '#00e290'), size: 1 }
      : e.st === 'down'
      ? { time: t, position: 'aboveBar', shape: 'arrowDown', color: BPChart.tok('--bp-state-broken-text', '#b9b7c0'), size: 1 }
      : { time: t, position: 'aboveBar', shape: 'circle',    color: BPChart.tok('--bp-text3', '#909097'), size: 0.6 };
  });
  area.setMarkers(markers);
  if (evs.length) {
    document.getElementById('chEvN').textContent = evs.length;
    document.getElementById('chKeyEv').hidden = false;
    document.getElementById('chEvList').innerHTML = evs.map(function(e){
      return '<li>' + _fmtDay(_dayToIdx[e.day], true) + ': ' + _stName[e.st] + '</li>';
    }).join('');
  }
  document.getElementById('chKeys').hidden = false;

  /* OHLC lejanti (sol ust): uzerine gelinen gun, yoksa son seans. */
  const legEl = document.getElementById('chLegend');
  function updateLeg(i) {
    const b = d.ohlc[i]; if (!b) return;
    const prev = i > 0 ? d.ohlc[i - 1].close : null;
    const ch = prev ? (b.close / prev - 1) * 100 : null;
    const ev = evAt[i];
    legEl.innerHTML = '<span class="ch-l-date">' + _fmtDay(i, true) + '</span>'
      + '<span>A <b>' + fmtP(b.open) + '</b></span><span>Y <b>' + fmtP(b.high) + '</b></span>'
      + '<span>D <b>' + fmtP(b.low) + '</b></span><span>K <b>' + fmtP(b.close) + '</b></span>'
      + (ch != null ? '<span class="' + (ch > 0 ? 'bp-al-text' : ch < 0 ? 'bp-sat-text' : '') + '">' + fmtPct(ch) + '</span>' : '')
      + (ev ? '<span class="ch-l-ev">' + _stName[ev.st] + ' başladı</span>' : '');
  }
  updateLeg(n - 1);
  chart.subscribeCrosshairMove(function(p){
    updateLeg(p && p.time != null ? Math.round(+p.time) : n - 1);   /* G26: time 0 gecerli */
  });

  /* Getiri seridi: 1H · 1A · 3A · YB · 1Y (son kapanisa gore). */
  (function(){
    const last = d.ohlc[n - 1].close, yr = _idxToDay[n - 1].slice(0, 4);
    let ybIdx = -1;
    for (let i = n - 1; i >= 0; i--) { if (_idxToDay[i].slice(0, 4) !== yr) { ybIdx = i; break; } }
    const cells = [['1H', n - 1 - 5], ['1A', n - 1 - 21], ['3A', n - 1 - 63], ['YB', ybIdx], ['1Y', n - 1 - 252]]
      .filter(function(c){ return c[1] >= 0; })
      .map(function(c){
        const v = (last / d.ohlc[c[1]].close - 1) * 100;
        return '<span class="ch-ret"><span class="ch-ret-k">' + c[0] + '</span><b class="' + (v > 0 ? 'bp-al-text' : v < 0 ? 'bp-sat-text' : '') + '">' + fmtPct(v) + '</b></span>';
      });
    const el = document.getElementById('chReturns');
    el.innerHTML = cells.join('');
    el.hidden = !cells.length;
  })();

  /* EMA 12/99: varsayilan kapali, dugmeyle eklenir/kaldirilir. */
  let emaPair = null;
  const emaBtn = document.getElementById('chEma');
  emaBtn.setAttribute('aria-pressed', 'false');
  emaBtn.onclick = function(){
    if (emaPair) { chart.removeSeries(emaPair.e12); chart.removeSeries(emaPair.e99); emaPair = null; }
    else { emaPair = BPChart.addEmaPair(chart, ema12, ema99); }
    emaBtn.setAttribute('aria-pressed', emaPair ? 'true' : 'false');
  };

  /* Donem cipleri + gorunen pencere etiketi (#chartPeriod ve aria-label ayni kaynaktan). */
  const elP = document.getElementById('chartPeriod');
  function syncPeriod(r) {
    if (!r) return;
    const i0 = Math.max(0, Math.ceil(r.from)), i1 = Math.min(n - 1, Math.floor(r.to));
    if (i1 < i0) return;
    const txt = _fmtDay(i0, true) + ' – ' + _fmtDay(i1, true) + ' · ' + (i1 - i0 + 1) + ' seans';
    if (elP) elP.textContent = txt;
    elMain.setAttribute('aria-label', TICKER + ' kapanış fiyatı grafiği, ' + txt);
  }
  chart.timeScale().subscribeVisibleLogicalRangeChange(syncPeriod);
  const chips = Array.prototype.slice.call(document.querySelectorAll('#chChips button'));
  function setWin(N) {
    chips.forEach(function(c){ c.setAttribute('aria-pressed', +c.dataset.n === N ? 'true' : 'false'); });
    chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, n - N), to: n - 1 + 6 });
  }
  chips.forEach(function(c){
    c.disabled = +c.dataset.n > n * 1.9 && +c.dataset.n !== 21;   /* cok kisa gecmiste anlamsiz cip */
    c.onclick = function(){ setWin(+c.dataset.n); };
  });
  const N0 = window.innerWidth < 768 ? 63 : 252;
  requestAnimationFrame(function(){ try { setWin(N0); } catch(_) { console.warn('grafik penceresi ayarlanamadi', _); } });

  function _syncChartSize() {
    _syncW52Cap();
    const w = elMain.clientWidth;
    if (!w || !chart) return;
    const h = _chartH();
    elMain.style.height = h + 'px';
    chart.applyOptions({ width: w, height: h });
  }

  _hisseResizeHandler = function(){ clearTimeout(_chartResizeT); _chartResizeT = setTimeout(_syncChartSize, 150); };
  window.addEventListener('resize', _hisseResizeHandler);

  // SPEC-017 Faz F Bug 3: ResizeObserver — sekme gecisinde (display:none→block) yeniden boyutla
  try {
    if (typeof ResizeObserver !== 'undefined') {
      _hisseChartRO = new ResizeObserver(_syncChartSize);
      _hisseChartRO.observe(elMain);
    }
  } catch(_) { console.warn('ResizeObserver kurulumu basarisiz (sekme degisince grafik yeniden boyutlanmayacak)', _); }
  window.bpChartResize = function(){
    setTimeout(_syncChartSize, 80);
  };
}

/* ── 52-hafta + commentary render ──────────────────── */
/* ── SPEC-014 B2/B3 + CPO-551 A5 — Veri yaşı göstergesi + stale banner ──── */
/* C-19: renderFreshness kalkti -- tek girdisi /api/data idi (artik istenmiyor). Bayat
   veri uyarisi stale-banner.js /api/data-quality yoklamasinda; kapanis gunu hero'da SSR. */

function renderCommentary(commentary) {
  if (!commentary) return;
  const el = document.getElementById('commentaryText') || document.getElementById('commentaryTextFallback');
  const sec = document.getElementById('commentarySection') || document.getElementById('commentarySectionFallback');
  if (el && sec) {
    el.textContent = commentary;
    sec.style.display = '';
  }
}

/* ── Özet kartları doldur ──────────────────────────── */
// CPO-1558: renderEntryAnalysis'in placeholder dalları (yükleniyor/veri yok/
// sinyal yok) #entryAnalysisGrid'in TÜM innerHTML'ini bir mesajla değiştiriyordu
// — bu, grid'in içindeki #eqBadge/#eqNote/#rrBarContainer/#rrLevels çocuk
// elementlerini KALICI OLARAK yok ediyordu. renderSummary ikinci kez gerçek
// veriyle (signalData dolu) çağrıldığında "başarı" dalı bu ID'leri
// getElementById ile arıyor ama artık DOM'da yoklar — sessizce hiçbir şey
// yazmıyor, placeholder metni sonsuza dek ekranda kalıyor. Canlı ölçümle
// doğrulandı (AGHOL, entry_quality:"IDEAL" olmasına rağmen "yükleniyor" takılı
// kalıyordu). Grid'in orijinal (bozulmamış) HTML'i ilk çağrıda BİR KEZ
// yakalanıp, başarı daline girmeden hemen önce geri yükleniyor.
let _pristineEntryGridHtml = null;
function renderSummary(s, signalData) {
  window._bpLastSignalData = signalData || null;   // _hibCurrentPrice() icin
  /* C-20: baslik fiyati/degisimi SSR (hero, tek fiyat); durum hapi, info-grid ve
     Trend Durumu kalkti -- ayni bilgi 3 Soruda'nin Q3'unde (SSR). */
  (function renderVolumeProfile() {
    if (!signalData) return;   /* ilk cizim: /api/data henuz gelmedi, satirlar gizli kalir */
    const vr = signalData.signal_vol_ratio;
    const rvolVal = signalData.rvol;
    const isPremium = signalData.is_premium === true;

    /* Üst satır: 5g/20g momentum (RVOL) — backtest desteği var */
    const hpRvolRow = document.getElementById('hpRvolRow');
    const hpRvolVal = document.getElementById('hpRvolVal');
    if (hpRvolRow && hpRvolVal && rvolVal != null) {
      /* C-74 K10 (02.10): renk (ok/weak/bad) ve "Hacim Onaylı" rozeti yargiydi -- yalniz sayi. */
      hpRvolVal.className = 'hp-row-val';
      hpRvolVal.textContent = `${rvolVal.toFixed(2).replace('.', ',')}×`;
      hpRvolRow.style.display = '';
    }

    /* Alt satır: Sinyal günü patlama (signal_vol_ratio) — bilgi amaçlı */
    const hpSvolRow = document.getElementById('hpSvolRow');
    const hpSvolVal = document.getElementById('hpSvolVal');
    if (hpSvolRow && hpSvolVal && vr != null) {
      hpSvolVal.className = 'hp-row-val';
      hpSvolVal.textContent = `${vr.toFixed(2).replace('.', ',')}×`;
      hpSvolRow.style.display = '';
    }

    /* C-74 K10 (02.10): "zayif/guclu/kivilcim/birikim" yorumlari yerine betim.
       `vr == null` bilinmiyor demektir (K-BT), cumle kurulmaz. */
    const hpSummary = document.getElementById('hpSummary');
    if (hpSummary) {
      const x = (v) => v.toFixed(2).replace('.', ',');
      let txt = rvolVal != null ? `Son 5 günün hacmi 20 günlük ortalamanın ${x(rvolVal)} katı.` : '';
      if (vr != null) txt += (txt ? ' ' : '') + `Sinyal günündeki hacim ortalamanın ${x(vr)} katıydı.`;
      hpSummary.textContent = txt;
    }
  })();

  /* İndikatörler — Sade dil + teknik detay */
  // Etiket sunucudan gelir (signalData.adx_label, business_rules.derive_adx_label — CPO-1196 D0 #4).
  // /api/data henüz dönmediyse (ilk render) aynı kanonik eşiklerle geçici fallback.
  // bug-hunt r66: esikler (18/25/40) business_rules.py:derive_adx_label ile BIREBIR AYNI kalmali,
  // orada degisirse burasi da elle guncellenmeli (otomatik kilit yok).
  const adxStrength = (signalData && signalData.adx_label) ? signalData.adx_label
    : (s.adx >= 40 ? 'Çok Güçlü' : s.adx >= 25 ? 'Güçlü' : s.adx >= 18 ? 'Orta' : 'Zayıf');
  // adxStrength (etiket) gibi ADX SAYISI da mümkünse taze signalData'dan (/api/data)
  // okunmalı — s.adx chart endpoint'inden gelir, günlerce geride kalabilir.
  const adxNum = (signalData && signalData.adx != null) ? signalData.adx : s.adx;
  const _IND_TOOLTIPS = {
    'Trend Yönü':  'Supertrend(10,3) indikatörü fiyatın ATR bazlı dinamik bandın üzerinde mi altında mı olduğunu belirler. Fiyat üst bandın üzerinde kapanırsa yükseliş, altında kapanırsa düşüş yönü onaylanır. Örnek: 3 ardışık kapanış Supertrend bandı üzerinde → güçlü yükseliş trendi.',
    'Momentum':    'ADX (Ortalama Yön Endeksi) trendin gücünü 0-100 arası ölçer — yön değil güç verir. ADX ≥ 25 güçlü trend, 18-25 orta, < 18 zayıf/yatay piyasa anlamına gelir. DI+ > DI− ise alıcılar baskın, DI− > DI+ ise satıcılar baskın.',
    'Vade Uyumu':  'EMA12 (12 günlük) ve EMA99 (99 günlük) hareketli ortalama karşılaştırılır. EMA12 > EMA99 kısa vadenin uzun vadenin üzerinde olduğunu — yani yükseliş eğilimini — gösterir. Örnek: Her iki EMA aynı yönde ise tüm vadeler uyumlu, sinyal güvenilirliği artar. "Kararsızlık bölgesi" notu: fark %0,15\'in altındaysa iki ortalama neredeyse çakışıyor demektir, sinyal sınıflandırmasını DEĞİŞTİRMEZ — sadece şeffaflık için gösterilir.',
  };
  // CPO-1656 EK YANIT Seçenek B: ham EMA12/EMA99 fark yüzdesi eşik-altıysa
  // (business_rules.derive_ema_deadband, %0.15) sadece bilgilendirici bir not
  // eklenir — e12_bull/e12_bear karşılaştırması (dolayısıyla ok/AL-SAT-BEKLE)
  // DEĞİŞMEZ, sıfır regresyon riski.
  const _emaDb = signalData && signalData.indicators && signalData.indicators.ema1299;
  // CPO-1665 orta öncelik #2: Trend Yönü/Vade Uyumu (ve ADX'in kendi ok checkmark'ı)
  // hâlâ SADECE chart endpoint'inin (s.*) kendi bağımsız hesabını kullanıyordu —
  // ADX sayı/etiket fix'i (yukarıda) gibi ana cache'e (signalData.indicators, otoritelif
  // kaynak) fallback yapmıyordu. GUBRF'de canlı yön-flip kanıtlandı (chart ↑ derken
  // ana cache ↓ diyordu, rozet chart'a göre renkleniyordu). Aynı "tek kaynak" ilkesini
  // üç göstergenin bull/bear durumuna da genişlet.
  const _siInd = signalData && signalData.indicators;
  const stBull  = (_siInd && _siInd.supertrend) ? _siInd.supertrend.bull : s.st_bull;
  const stBear  = (_siInd && _siInd.supertrend) ? _siInd.supertrend.bear : s.st_bear;
  const adxBull = (_siInd && _siInd.adx)        ? _siInd.adx.bull        : s.adx_bull;
  const adxBear = (_siInd && _siInd.adx)        ? _siInd.adx.bear        : s.adx_bear;
  const e12Bull = (_siInd && _siInd.ema1299)    ? _siInd.ema1299.bull    : s.e12_bull;
  const e12Bear = (_siInd && _siInd.ema1299)    ? _siInd.ema1299.bear    : s.e12_bear;
  /* K-BS (22.09): `techDetail` satirlari CPO-1665'in TERK ETTIGI kaynaktan
     okumaya devam ediyordu. CPO-1665 rozetin metnini (`detail`) ve isaretini
     (`ok`) otoriter kaynaga (signalData.indicators) tasidi, ama AYNI NESNENIN
     kardes alani `techDetail` chart ozetinde (`s.*`) kaldi — yani duzeltilen
     GUBRF celiskisi bir satir asagida hayatta kaldi. Canli kanit 22.09
     /hisse/TAVHL: rozet "Trend Yönü — ↓ Düşüş" (otoriter: ST SHORT) derken
     teknik detay satiri "Supertrend(10,3): LONG" basiyordu (chart ozeti
     st_bull=true). Sonuc cumlesi HER ZAMAN rozetle ayni kaynaktan gelir. */
  const _emaDir = e12Bull ? 1 : (e12Bear ? -1 : 0);
  const _adxDir = adxBull ? 1 : (adxBear ? -1 : 0);
  const _e12s = bpIndNum(s.e12), _e99s = bpIndNum(s.e99);
  const _dips = bpIndNum(s.di_plus), _dims = bpIndNum(s.di_minus);
  const inds = [
    {
      label: 'Trend Yönü',
      detail: stBull ? '↑ Yükseliş' : stBear ? '↓ Düşüş' : '— Net değil',
      techDetail: 'Supertrend(10,3): ' + (stBull ? 'Yukarı' : stBear ? 'Aşağı' : 'Yatay'),
      ok: s.signal === 'SAT' ? stBear : stBull,
      blog: '/blog/supertrend-indikatoru-nedir', blogLabel: 'Supertrend'
    },
    {
      label: 'Momentum',
      // 17.09 bughunt: chart endpoint'in summary'si (s.adx) /api/data'dan (signalData.adx)
      // günlerce geride kalabiliyor (ayrı önbellek döngüleri) — aynı ADX metriği için
      // sayfada iki farklı sayı görünüyordu (ör. KONTR: 36.8 vs 38.7). adxStrength
      // etiketi zaten signalData'yı önceliklendiriyordu (satır üstte), sayı da aynı
      // kaynağa hizalandı.
      detail: adxStrength + (adxNum ? ' (' + Number(adxNum).toFixed(1).replace('.', ',') + ')' : ''),
      techDetail: 'ADX(14): ' + bpIndNum(adxNum) + ' · DI+: ' + _dips + ' · DI−: ' + _dims +
        bpNumPairNote(_dips, _dims, _adxDir),
      ok: s.signal === 'SAT' ? adxBear : adxBull,
      blog: '/blog/adx-indikatoru-nedir', blogLabel: 'ADX'
    },
    {
      label: 'Vade Uyumu',
      detail: (e12Bull ? 'Kısa > Uzun' : e12Bear ? 'Kısa < Uzun' : 'Eşit') +
        (_emaDb && _emaDb.deadband ? ' · ⚠️ kararsızlık bölgesi' : ''),
      techDetail: 'EMA12: ' + _e12s + ' · EMA99: ' + _e99s +
        /* K-BS: basilan cift, yazilan sonucu desteklemeli. */
        bpNumPairNote(_e12s, _e99s, _emaDir) +
        /* K-BR ek: `String(diff_pct)` HAM HASSASIYETI ekrana siziyordu —
           canli ISDMR "fark: %11,055" (3 ondalik), sitenin baska hicbir
           yuzeyinde olmayan bir bicim. Deadband esigi %0,15 oldugu icin
           kanon 2 ondalik. Fark bir BUYUKLUKTUR: yonu zaten "Kısa > Uzun"
           satiri soyluyor, sayi isaret tasimaz (K-BP/K-BQ dersi). */
        (_emaDb && _emaDb.diff_pct != null
          ? ' · fark: %' + Math.abs(_emaDb.diff_pct).toFixed(2).replace('.', ',') : ''),
      ok: s.signal === 'SAT' ? e12Bear : e12Bull,
      blog: '/blog/ema-hareketli-ortalama-nedir', blogLabel: 'EMA'
    },
  ].map(i => Object.assign(i, { tooltip: _IND_TOOLTIPS[i.label] || '' }));

  // Tech details for expandable section — renk-kodlu satırlar (ind-badge ile aynı bull/bear/neutral mantığı)
  /* 21.09 (K-AT): `blog:` alani bugune kadar SADECE olu `data-link` ozniteligine
     yaziliyordu, hicbir JS onu okumuyordu -> gostergeleri anlatan 4 blog yazisi
     /hisse/* sayfasindan HIC erisilemiyordu. Artik teknik detay satirinda gercek
     bir baglanti; adi hedefin konusudur (K-AS: SC 2.4.4). */
  const _indLink = (href, label) =>
    href ? ' <a class="tech-row-link" href="' + href + '">' + label + ' nedir?</a>' : '';
  let techDetailsHtml = inds.map(i => {
    const stateCls = i.ok ? (s.signal === 'SAT' ? 'tech-row-bear' : 'tech-row-bull') : 'tech-row-neutral';
    return '<div class="tech-row ' + stateCls + '"><span class="tech-row-dot"></span>' + i.techDetail +
           _indLink(i.blog, i.blogLabel) + '</div>';
  }).join('');
  if (signalData && signalData.rsi != null) {
    techDetailsHtml += '<div class="tech-row tech-row-neutral"><span class="tech-row-dot"></span>RSI(14): ' +
      bpIndNum(signalData.rsi) + _indLink('/blog/rsi-gostergesi-nedir', 'RSI') + '</div>';
  }
  const techContentEl = document.getElementById('indTechContent');
  if (techContentEl) techContentEl.innerHTML = techDetailsHtml;
  let indHtml = inds.map(ind => {
    const cls = ind.ok
      ? (s.signal === 'SAT' ? 'ind-badge ind-bear' : 'ind-badge ind-bull')
      : 'ind-badge ind-neutral';
    return `<span class="${cls}">${ind.label}<span class="ind-detail">${ind.detail}</span></span>` +
      `<button type="button" class="ind-help" data-tip="${(ind.tooltip||'Bu gösterge hakkında detayl\u0131 bilgi i\u00e7in metodolojiye bakın.').replace(/"/g,'&quot;')}" aria-label="${ind.label} açıklamasını göster">?</button>`;
  }).join('');

  /* RSI14 badge — Faz 1 #3: 6-zone */
  if (signalData && signalData.rsi != null) {
    const rsi = signalData.rsi;
    /* K-BS (22.09): P0-2 "İdeal Giriş" RENGINI notrlemisti, KELIMELERI kalmisti.
       `rsi_zone` backend'de sinyalden BAGIMSIZ turetilir; long-only bir urunde
       "İdeal Giriş Penceresi" ancak AL sinyaliyle bir vaat tasir. Canli 22.09:
       bu bolge adini tasiyan 46 hissenin **45'i AL DEGIL** — 3'u SAT (FROTO
       46,5 · MGROS 47,1 · MAVI 51,0), yani "trend bozuldu" denen hissede
       "İdeal Giriş Penceresi" yaziyordu. Tek kanon: bp-format.js
       `bpRsiZoneText` (/karsilastir ayni fonksiyonu kullanir). */
    /* C-74 K10 (02.10): bolge adi (Dip Toparlanmasi, Asiri Alim, Dikkatli...) ve
       yesil/kirmizi rozet yone beklenti yukluyordu -- /karsilastir gibi yalniz sayi. */
    indHtml += `<span class="ind-badge ind-neutral">RSI ${bpIndNum(rsi)}</span>` +
      `<button type="button" class="ind-help" data-tip="RSI: 0-100 arası momentum göstergesi; son günlerdeki yükseliş ve düşüşlerin büyüklüğünü karşılaştırır." aria-label="RSI açıklamasını göster">?</button>`;
  }

  /* Günlük Hacim Oranı badge (sadece dikkat çekici olduğunda göster)
     K-BS (22.09) — IKI KUSUR BIRDEN:
     (a) K-BO ihlali SINIF ADI uzerinden hayatta kalmisti. Hacim YON-BAGIMSIZ
         bir buyukluktur; `ind-bull` ise hisse.css'te `--bp-al` (yukselis
         yesili). Kapi 34 token/ham-hex ariyordu, SINIF ADINI degil — bu yuzden
         gormemisti. Canli 22.09: vol_ratio >= 3 olan 4 hisse (SASA 7,35 ·
         USAK 4,45 · ANHYT 3,41 · TUKAS 3,40); DORDU DE BEKLE ve IKISI O GUN
         DUSMUS (SASA −1,70% · USAK −3,85%) — yani "yesil" rozet dusen bir
         hissede "olumlu" okunuyordu. Hacim ekseninin kanonik rengi
         --bp-volume (tokens.css CPO-1149/1150) -> `.ind-volume`.
     (b) ETIKET "Hacim" JENERIK. Bu alan `vol_ratio` (bugun / 20g ort.), ama
         AYNI SAYFANIN Hacim Profili paneli RVOL (5g/20g) basiyor ve
         /metodoloji acikca "ikisini karistirmayin, ayni sayi degildir" diyor.
         Canli: rozetin gorundugu 37 hissenin 37'sinde iki sayi FARKLI
         (DURDO rozet 1,83× · RVOL 1,52×). Kanonik ad /tarama ve /metodoloji'de
         zaten yazili: "Günlük Hacim Oranı" (CPO-1687). */
  if (signalData && signalData.vol_ratio != null) {
    const vr = signalData.vol_ratio;
    if (vr >= 1.5) {
      const vrTip = 'Günlük Hacim Oranı — son seans hacmi / 20 günlük ortalama. Hacim Profili’ndeki 5 günlük oran farklı bir sayıdır.';
      indHtml += `<span class="ind-badge ind-volume" data-tip="${vrTip}" tabindex="0">Hacim Oranı ${_trNum(vr)}×<span class="ind-detail">${vr >= 3 ? 'Çok yüksek hacim' : 'Yüksek hacim'}</span></span>`;
    }
  }

  const indRowEl = document.getElementById('indRow');
  if (indRowEl) indRowEl.innerHTML = indHtml;
  window._bpApplyTooltips && window._bpApplyTooltips();

  /* C-20: AI sekmesiyle birlikte cakisma notu (#sigConflictNote) kalkti. */
}

/* ── Veri yükle — chart + /api/data paralel ─────────── */
/* SPEC-008 L2 — Frontend Fail-Safe: bozuk/eksik chart ASLA render edilmez,
   sınırlı retry + kullanıcıya görünür durum mesajı. */
const _MAX_CHART_RETRY = 3;
function _showChartStatus(msg, withRetryBtn) {
  const el = document.getElementById('chartLoading');
  if (!el) return;
  /* 21.09 (K-W): burada `display:'block'` YAZILIYDI ve konteynerin kanonik
     `.da-loading` (flex) yerlesimini inline olarak eziyordu. Yukleniyor dali
     artik stil katmanina birakiliyor; HATA dali ise bilerek blok kaliyor
     (hata kutusu tam genislik ister) — degisiklik yok, sadece acik yazildi. */
  el.style.display = '';
  el.className = withRetryBtn ? 'da-loading--block' : 'da-loading da-loading--block';
  document.getElementById('chartsInner').style.display = 'none';
  /* 21.09 (K-V): hata dali kanonik `.da-empty--error` + `.da-retry` diline
     gecti — bu sayfada ucuncu, sitede besinci elle-yazilmis "Tekrar dene"
     dugmesiydi. Yukleniyor dali (spinner) aynen kaldi: o bir HATA degil. */
  el.innerHTML = withRetryBtn
    ? '<div class="da-empty da-empty--error" role="alert"><span><span aria-hidden="true">⚠️</span> ' +
      msg + '</span><button type="button" class="da-retry" onclick="loadChart(0)">Tekrar dene</button></div>'
    : '<div class="da-spin"></div> ' + msg;
  // C-20: baslikta durum hapi (#hpSignal) yok; nihai hatada yalniz gecmis/gostergeler isaretlenir.
  if (withRetryBtn) {
    if (window.showToast) showToast(msg, 'error');
    const indRow = document.getElementById('indRow');
    if (indRow) indRow.innerHTML = '<span class="ind-badge ind-neutral">Veri yüklenemedi</span>';
  }
}

let _chartSeq = 0;
/* C-19 (25.09): /api/hisse/<T>/chart TEK istek -- Ozet (alan grafigi, gecmis, gostergeler)
   ve Grafik (mum grafigi) ayni promise'i paylasir. Basarisizlikta promise sifirlanir,
   "Tekrar dene" yeniden ister. Eskiden sayfa acilir acilmaz her sekmede istenirdi ve
   ardindan /api/data (~290 KB) gelirdi; ikisi de artik yalniz ihtiyac duyan sekmede. */
/* C-20: Ozet ile Temel/Haberler ayni uclari kullanir -> tek istek, paylasilan promise. */
const _bpOnce = {};
function _bpGetJSON(key, url, ms) {
  if (!_bpOnce[key]) {
    _bpOnce[key] = fetch(url, { signal: AbortSignal.timeout(ms || 15000) })
      .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .catch(err => { delete _bpOnce[key]; throw err; });
  }
  return _bpOnce[key];
}
const _bpFundJSON = () => _bpGetJSON('fund', '/api/hisse/' + TICKER + '/fundamentals');
const _bpDivJSON  = () => _bpGetJSON('div', '/api/temettu-takvimi', 8000);
const _bpKapJSON  = () => _bpGetJSON('kap', '/api/hisse/' + TICKER + '/kap');
/* C-25c (27.09): /api/temettu-takvimi (tum evrenin takvimi) yalniz KAP temettu
   verisi (fundamentals.kap.temettu) yoksa istenir; varsa divRow kullanilmaz.
   fj: basarisizlikta null; dj: istenmediyse null, alinamadiysa undefined. */
function _bpFundDivJSON() {
  return _bpFundJSON().catch(() => null).then(fj => {
    const f = fj && fj.fundamentals;
    if (f && f.kap_durum === 'var' && f.kap && f.kap.temettu) return [fj, null];
    return _bpDivJSON().catch(() => undefined).then(dj => [fj, dj]);
  });
}

let _bpChartP = null;
function _bpChartJSON() {
  if (_bpChartP) return _bpChartP;
  const attempt = async (retry) => {
    const res = await fetch('/api/hisse/' + TICKER + '/chart', { signal: AbortSignal.timeout(15000) });
    const json = await res.json();
    if (json.integrity_error) console.warn('[chart] integrity_error:', json.integrity_error);
    /* CPO-1653 P1: yapisal "yeterli gecmisi yok" -- retry ise yaramaz. */
    if (json.unavailable) return { unavailable: true };
    if (!res.ok || json.loading || json.integrity_error || !json.chart) {
      if (retry < _MAX_CHART_RETRY) {
        await new Promise(r => setTimeout(r, 3000));
        return attempt(retry + 1);
      }
      throw new Error('chart unavailable');
    }
    return json;
  };
  _bpChartP = attempt(0).catch(err => { _bpChartP = null; throw err; });
  return _bpChartP;
}

/* Ozet'in grafik verisinden beslenen parcalari (gecmis tablosu, gostergeler, paylasim). */
let _bpOzetChartDone = false;
function _bpRenderOzetFromChart(ch) {
  if (_bpOzetChartDone || !ch) return;
  _bpOzetChartDone = true;
  try { hxChartSetData((ch.ohlc || []).map(b => [b.time, +b.close])); } catch (e) { console.warn('hx chart', e); }
  try { hxFillDI(ch.summary); } catch (e) { console.warn('hx di', e); }
  renderCommentary(ch.commentary);
  if (ch.summary) renderSummary(ch.summary, BP_SSR.ticker ? BP_SSR : null);
}

/* ══ C-20 (25.09) — Ozet hero v2 ═══════════════════════════════════════════════
   Alan grafigi (SVG, kutuphane yok), 4 temel gosterge, Q2 degerleme, DI satiri,
   Son haberler. Veri: Ozet'in /chart, /fundamentals, /temettu-takvimi, /kap
   yanitlari (hepsi paylasilan tek istek). Baslik fiyati SSR (#hpPrice) tek kaynak. */
/* C-22c: D-40c Temel v2 -- degerleme hukmu gun sonu turundan (tek kaynak, istemcide yeniden hesaplanmaz) */
const HX_TV2 = window.BP.tv2;
const HX_PRICE = (BP_SSR && BP_SSR.price != null && isFinite(+BP_SSR.price)) ? +BP_SSR.price : null;
const _hxNF2 = new Intl.NumberFormat('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const _hxNF1 = new Intl.NumberFormat('tr-TR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const _HX_AY = ['Ocak','Şubat','Mart','Nisan','Mayıs','Haziran','Temmuz','Ağustos','Eylül','Ekim','Kasım','Aralık'];
function _hxDate(iso) { const p = String(iso || '').split('-'); return p.length === 3 ? (+p[2]) + ' ' + _HX_AY[+p[1] - 1] + ' ' + p[0] : iso; }
let _hxSeries = null, _hxDays = 30;
function hxChartSetData(rows) {
  rows = (rows || []).filter(r => r && r[0] && isFinite(r[1]) && r[1] > 0);
  if (rows.length < 2) return;
  /* Tek fiyat: son nokta = baslik fiyati. Grafik ucu ayni gunun resmi kapanisindan
     sapmissa (D-04 oncesi 17:59 fiyati) baslik esas alinir; %2'den buyuk fark
     (bayat grafik) duzeltilmez. */
  if (HX_PRICE != null) {
    const last = rows[rows.length - 1];
    if (Math.abs(last[1] - HX_PRICE) / HX_PRICE < 0.02) last[1] = HX_PRICE;
  }
  _hxSeries = rows;
  hxChartDraw();
}
function _hxWindow() {
  if (!_hxSeries) return [];
  const end = new Date(_hxSeries[_hxSeries.length - 1][0] + 'T00:00:00Z').getTime();
  const from = end - _hxDays * 864e5;
  const w = _hxSeries.filter(r => new Date(r[0] + 'T00:00:00Z').getTime() > from);
  return w.length >= 2 ? w : _hxSeries.slice(-2);
}
function hxChartDraw() {
  const cv = document.getElementById('hxChartCv'), pc = document.getElementById('hxChartPc');
  if (!cv || !_hxSeries) return;
  const W = Math.round(cv.clientWidth), H = Math.round(cv.clientHeight);
  if (!W || !H) return;                       /* gizli sekmede olculemez; applyTab('ozet') yeniden cizer */
  const c = _hxWindow(), vals = c.map(r => r[1]);
  let mn = Math.min.apply(null, vals), mx = Math.max.apply(null, vals);
  const pad = (mx - mn) * 0.12 || mx * 0.01 || 1; mn -= pad; mx += pad;
  const X = i => (i / (c.length - 1)) * W, Y = v => H - ((v - mn) / (mx - mn)) * H;
  const d = c.map((r, i) => (i ? 'L' : 'M') + X(i).toFixed(1) + ' ' + Y(r[1]).toFixed(1)).join(' ');
  const base = Y(c[0][1]).toFixed(1), last = c[c.length - 1];
  cv.innerHTML = '<svg viewBox="0 0 ' + W + ' ' + H + '" width="' + W + '" height="' + H + '" aria-hidden="true" focusable="false">' +
    '<defs><linearGradient id="hxGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0" class="hx-g0"/><stop offset="1" class="hx-g1"/></linearGradient></defs>' +
    '<line class="hx-base" x1="0" x2="' + W + '" y1="' + base + '" y2="' + base + '"/>' +
    '<path class="hx-area" d="' + d + ' L' + W + ' ' + H + ' L0 ' + H + ' Z"/>' +
    '<path class="hx-line" d="' + d + '"/>' +
    '<circle class="hx-end" cx="' + X(c.length - 1).toFixed(1) + '" cy="' + Y(last[1]).toFixed(1) + '" r="4"/></svg>';
  const chg = (last[1] / c[0][1] - 1) * 100;
  /* K-CB: pencere beyani cizilen veriden (ilk-son tarih + seans sayisi). */
  const lbl = _hxDays === 30 ? 'Son 1 ay' : (_hxDays === 90 ? 'Son 3 ay' : 'Son 1 yıl');
  if (pc) pc.innerHTML = lbl + ': <b class="' + bpDirClass(chg, 1, 'up,down,neu') + '">' + bpFormatPct(chg, 1) + '</b>';
  cv.setAttribute('aria-label', TICKER + ' kapanış grafiği, ' + _hxDate(c[0][0]) + ' – ' + _hxDate(last[0]) + ', ' + c.length + ' seans, dönem değişimi ' + bpFormatPct(chg, 1));
}
(function hxChartWire() {
  const box = document.getElementById('hxChart');
  if (!box) return;
  box.querySelector('.hx-chips').addEventListener('click', ev => {
    const b = ev.target.closest('button[data-days]'); if (!b) return;
    _hxDays = +b.dataset.days;
    box.querySelectorAll('.hx-chips button').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
    hxChartDraw();
  });
  const cv = document.getElementById('hxChartCv'), tip = document.getElementById('hxChartTip');
  const move = ev => {
    if (!_hxSeries) return;
    const c = _hxWindow(), r = cv.getBoundingClientRect();
    const i = Math.max(0, Math.min(c.length - 1, Math.round((ev.clientX - r.left) / r.width * (c.length - 1))));
    tip.hidden = false;
    tip.textContent = _hxDate(c[i][0]) + ' · ' + _hxNF2.format(c[i][1]) + ' ₺';
    const bx = box.getBoundingClientRect();
    tip.style.left = Math.max(6, Math.min(bx.width - tip.offsetWidth - 6, ev.clientX - bx.left - tip.offsetWidth / 2)) + 'px';
  };
  cv.addEventListener('pointermove', move);
  cv.addEventListener('pointerdown', move);
  cv.addEventListener('pointerleave', () => { tip.hidden = true; });
  let t = null;
  if (typeof ResizeObserver === 'function') new ResizeObserver(() => { clearTimeout(t); t = setTimeout(hxChartDraw, 60); }).observe(cv);
  /* D-18b: closes_30 SSR'da varsa ilk cizim fetch beklemez. */
  const j = document.getElementById('hxCloses30');
  if (j) { try { hxChartSetData(JSON.parse(j.textContent)); } catch (e) { console.warn('closes_30', e); } }
})();

/* Q3'un DI satiri: SSR'da sayi yok (yalniz etiket metninde), /chart ozetinden. */
function hxFillDI(sum) {
  const li = document.getElementById('q3Di'), v = document.getElementById('q3DiV'), sr = document.getElementById('q3DiSr');
  if (!li || !sum || sum.di_plus == null || sum.di_minus == null) return;
  const ok = +sum.di_plus > +sum.di_minus;
  li.className = ok ? 'ok' : 'no';
  li.querySelector('i').textContent = ok ? '✓' : '–';
  if (sr) sr.textContent = ok ? ': sağlanıyor' : ': sağlanmıyor';
  v.textContent = _hxNF1.format(+sum.di_plus) + ' / ' + _hxNF1.format(+sum.di_minus);
}

/* 4 temel gosterge + Q2 (Fiyati makul mu?). C-22b: Temel sekmesiyle tek kanon --
   `kap` varsa ozsermaye karliligi O22=B son 12 ay, temettu son 12 ay KAP odemeleri / fiyat,
   Q2 hukmu tvValuation (sektor ortancasina oran 0,80 / 1,25; ortanca yoksa hukum yok). */
function hxFillFund(f, divRow) {
  const set = (id, txt, dim) => { const el = document.getElementById(id); if (el) { el.textContent = txt; el.classList.toggle('hx-dim', !!dim); } };
  const k = f && f.kap_durum === 'var' ? f.kap : null;
  const now = k && k.degerleme_simdi;
  if (f) {
    set('hxfMcap', now && now.piyasa_degeri ? _tvMoney(now.piyasa_degeri) : (f.market_cap && f.market_cap.value != null ? (_fmtMoneyObj(f.market_cap) || '—') : '—'));
    set('hxfRoe', now && now.ozsermaye_karliligi != null ? bpPctLevel(now.ozsermaye_karliligi, 1) : (f.roe != null ? bpPctLevel(f.roe, 1) : '—'));
    set('hxfMargin', f.profit_margin != null ? bpPctLevel(f.profit_margin, 1) : '—');
  }
  if (k && k.temettu) {
    set('hxfDiv', k.temettu.odeme_var && HX_PRICE ? bpPctLevel(k.temettu.brut_toplam / HX_PRICE * 100, 2) : 'Ödeme yok', !k.temettu.odeme_var);
  } else if (divRow === undefined) { /* takvim alinamadi: dokunma */ }
  else if (!divRow) set('hxfDiv', 'Veri yok', true);
  else {
    const last = divRow.last_div_date ? new Date(divRow.last_div_date + 'T00:00:00') : null;
    const asof = _hxSeries ? new Date(_hxSeries[_hxSeries.length - 1][0] + 'T00:00:00') : new Date();
    const recent = last && (asof - last) <= 365 * 864e5 && divRow.last_div_amount != null;
    set('hxfDiv', recent && HX_PRICE ? bpPctLevel(divRow.last_div_amount / HX_PRICE * 100, 2) : 'Ödeme yok', !recent);
  }
  if (!f) return;
  const kv = document.getElementById('q2Kv'), ans = document.getElementById('q2Ans'), dot = document.getElementById('q2Dot');
  const V = tvValuation(f);
  const rows = V ? V.rows.filter(r => r.v != null) : [];
  if (kv) kv.innerHTML = rows.length
    ? rows.map(r => '<div><dt>' + r.l + '</dt><dd>' + _tvX(r.v, r.fr) + (r.m ? ' <small>· ' + escHtml(_tvMedTxt(r.m, r.fr)) + '</small>' : '') + '</dd></div>').join('')
    : '<div><dt>F/K ve PD/DD</dt><dd>hesaplanamıyor</dd></div>';
  let a = rows.length ? rows.map(r => r.l + ' ' + _tvX(r.v, r.fr)).join(' · ') : 'Veri yok', cls = 'hx-dot--na';
  if (V && V.word) {
    a = V.word;
    cls = V.word === 'Karışık' || V.word === 'Pahalı tarafta' ? 'hx-dot--warn' : (V.word === 'Ucuz tarafta' ? 'hx-dot--val' : 'hx-dot--brand');
  }
  if (ans) ans.textContent = a;
  if (dot) dot.className = 'hx-dot ' + cls;
  const an = document.getElementById('q2An');
  if (an && f.analyst_target != null && f.analyst_count && HX_PRICE) {
    const up = (f.analyst_target / HX_PRICE - 1) * 100;
    an.innerHTML = 'Analist hedef ortalaması <b>' + _hxNF2.format(f.analyst_target) + ' ₺</b>\u00a0· fiyatın <b>' + bpPctLevel(Math.abs(up), 1) + '</b> ' + (up > 0 ? 'üstünde' : (up < 0 ? 'altında' : 'düzeyinde')) + '\u00a0· ' + f.analyst_count + '\u00a0analist';   /* C-71 K32: ayırıcı satır başına düşmez */
    an.hidden = false;
  }
  const note = document.getElementById('q2Note');
  if (note) {
    const _cn = { USD: 'dolar', EUR: 'euro', GBP: 'sterlin' }[f.financial_currency] || 'döviz';   /* C-74 K6 */
    const basis = k && k.basis === 'yabanci_para' ? 'Şirket rakamlarını ' + _cn + ' ile açıklıyor; burada TL\'ye çevrilmiş hali var.' : null;
    const noMed = V && rows.length && !V.hasMed ? (V.v2 ? 'Sektörde karşılaştırma için yeterli şirket yok.' : 'Sektörde karşılaştırma için yeterli şirket yok; bu yüzden ucuz ya da pahalı denmiyor.') : (V && V.wide ? 'Sektörde yeterli şirket olmadığı için piyasa geneline göre.' : null);
    const cur = f.financial_currency || 'TRY';
    const txt = basis || noMed || (cur !== 'TRY' && !rows.length ? 'Şirket finansallarını ' + cur + ' cinsinden raporluyor; F/K ve PD/DD bu yüzden hesaplanmıyor.' : null);
    if (txt) { note.textContent = txt; note.hidden = false; }
  }
}

/* Son haberler: /kap'in ilk 3 bildirimi (dis baglanti yok; satir -> Haberler sekmesi) */
function hxFillNews(data) {
  const ul = document.getElementById('hxNewsL');
  if (!ul) return;
  const items = (data && data.disclosures) || [];
  if (!items.length) { const sec = document.getElementById('hxNews'); if (sec) sec.style.display = 'none'; return; }
  const fmtD = s => { const p = String(s || '').split(' ')[0].split('.'); return p.length === 3 ? (+p[0]) + ' ' + _HX_AY[+p[1] - 1] : ''; };
  ul.innerHTML = items.slice(0, 3).map(d =>
    '<li><time>' + escHtml(fmtD(d.date)) + '</time><div><b>' + escHtml((d.summary || d.subject || '').trim()) + '</b>' +
    (d.subject && d.summary ? '<span>' + escHtml(d.subject.trim()) + '</span>' : '') + '</div></li>').join('');
}

function loadOzetExtras() {
  _bpFundDivJSON().then(([fj, dj]) => {
    const f = fj && fj.fundamentals && Object.keys(fj.fundamentals).length ? fj.fundamentals : null;
    const row = dj === undefined ? undefined : (((dj && dj.stocks) || []).find(x => x.ticker === TICKER) || null);
    hxFillFund(f, row);
    if (!f) { const a = document.getElementById('q2Ans'); if (a) a.textContent = 'Temel skor hesaplanmadı'; }
  });
  /* C-25c: "Son haberler" ilk ekranin altinda -- /kap blok yaklasinca istenir */
  const ul = document.getElementById('hxNewsL');
  const load = () => _bpKapJSON().then(hxFillNews).catch(() => {
    const sec = document.getElementById('hxNews'); if (sec) sec.style.display = 'none';
  });
  if (!ul || !('IntersectionObserver' in window)) { load(); return; }
  const io = new IntersectionObserver(es => {
    if (es.some(e => e.isIntersecting)) { io.disconnect(); load(); }
  }, { rootMargin: '200px 0px' });
  io.observe(ul);
}

function loadOzetChart() {
  return _bpChartJSON().then(json => {
    if (json && json.chart) _bpRenderOzetFromChart(json.chart);
  }).catch(err => {
    console.warn('[ozet] grafik verisi alinamadi', err);
  });
}

/* Grafik sekmesi: kutuphane (lightweight-charts) + ayni /chart verisi. */
async function loadChart(retry) {
  const _mySeq = ++_chartSeq;   /* bug-hunt r54: hizli "Tekrar dene" tiklamalarinda bayat yanit atlanir */
  try {
    await _loadChartLib();
  } catch (e) {
    console.warn('[chart] lightweight-charts yuklenemedi', e);
    _showChartStatus('Grafik kütüphanesi yüklenemedi, sayfayı yenileyin.', true);
    return;
  }
  try {
    const json = await _bpChartJSON();
    if (_mySeq !== _chartSeq) return;
    if (json.unavailable) {
      _showChartStatus('Bu hisse için grafik verisi henüz yeterli değil.', false);
      return;
    }
    buildChart(json.chart);
  } catch (e) {
    if (_mySeq !== _chartSeq) return;
    _showChartStatus('Bağlantı sorunu — grafik yüklenemedi.', true);
  }
}

/* ── KAP Bildirimleri ───────────────────────────────── */
/* C-24: sinyal durumunun basladigi gun (zaman cizelgesinde ayrac). */
const _HX_SIG = window.BP.sig;
async function loadKapDisclosures() {
  const loadEl = document.getElementById('kapLoading');
  const listEl = document.getElementById('kapList');
  if (!loadEl || !listEl) return;

  try {
    /* /kap (son 90 gun) + sinyal donemi bildirimleri tek listede; story hatasi sessiz. */
    const [data, story] = await Promise.all([
      _bpKapJSON(),
      fetch('/api/hisse/' + TICKER + '/signal-story').then(r => r.ok ? r.json() : null).catch(() => null)
    ]);
    loadEl.style.display = 'none';

    const seen = new Set(), items = [];
    [].concat((data && data.disclosures) || [], (story && story.events) || []).forEach(d => {
      const k = d.index || (d.date + '|' + d.summary);
      if (seen.has(k)) return;
      const p = bpParseTrDate(String(d.date || '').split(' ')[0]);
      if (!p) return;
      seen.add(k);
      items.push({ d, y: p.y, m: p.m, g: p.d, t: String(d.date || '').split(' ')[1] || '', key: p.y * 10000 + p.m * 100 + p.d });
    });

    if (!items.length) {
      /* C-P1-2509: bos liste cogu zaman eslesme eksigi (D-45); "bildirim yok" iddiasi yazilmaz. */
      listEl.innerHTML = '<p class="kap-empty">Bu hisse için listelenecek bildirim şu an yok.</p>';
      listEl.style.display = '';
      return;
    }
    items.sort((a, b) => (b.key - a.key) || (b.t < a.t ? -1 : b.t > a.t ? 1 : 0));

    /* Ayni gunun finansal rapor belgeleri ve ayni ozetli tekrarlar (MTN itfa vb.) tek satirda katlanir. */
    const norm = d => String(d.summary || d.subject || '').trim().toLocaleLowerCase('tr');
    const rows = [];
    items.forEach(it => {
      const last = rows.find(r => r.key === it.key && r.d.class === it.d.class && (it.d.class === 'FR' || norm(r.d) === norm(it.d)));
      if (last) last.docs.push(it.d);
      else rows.push(Object.assign({}, it, { docs: [it.d] }));
    });

    const LBL = { ODA: 'Özel durum', FR: 'Finansal rapor' };
    const SIG = { AL: 'Güçlü Trend', SAT: 'Trend Bozuldu' };
    const sp = _HX_SIG && _HX_SIG.d ? bpParseTrDate(String(_HX_SIG.d).split(' ')[0]) : null;
    const sigKey = sp ? sp.y * 10000 + sp.m * 100 + sp.d : null;
    const sigName = SIG[_HX_SIG && _HX_SIG.s] || 'Yatay durum';
    const dayTxt = r => r.g + ' ' + _HX_AY[r.m - 1];
    const one = d => escHtml(String(d.summary || d.subject || '').trim());
    let html = '', month = null, sigDone = sigKey === null || sigKey > rows[0].key;
    const CAP = 25;

    rows.forEach((r, i) => {
      if (i === CAP) html += '<div class="kap-more" hidden>';
      const mk = r.y * 100 + r.m;
      if (!sigDone && r.key < sigKey) {
        const smk = sp.y * 100 + sp.m;
        if (smk !== month) { html += '<h3 class="kap-month">' + _HX_AY[sp.m - 1] + ' ' + sp.y + '</h3>'; month = smk; }
        html += '<div class="kap-sig" role="separator"><span>' + escHtml(sigName) + ' başladı · ' + sp.d + ' ' + _HX_AY[sp.m - 1] + ' ' + sp.y + '</span></div>';
        sigDone = true;
      }
      if (mk !== month) { html += '<h3 class="kap-month">' + _HX_AY[r.m - 1] + ' ' + r.y + '</h3>'; month = mk; }
      if (!sigDone && r.key === sigKey) {
        html += '<div class="kap-sig" role="separator"><span>' + escHtml(sigName) + ' başladı · ' + dayTxt(r) + ' ' + r.y + '</span></div>';
        sigDone = true;
      }
      const lbl = LBL[r.d.class] || 'Bildirim';
      let body;
      if (r.docs.length > 1 && r.d.class === 'FR') {
        body = '<details class="kap-fold"><summary><span class="kap-summary">' + r.docs.length + ' finansal rapor belgesi</span></summary><ul>' +
          r.docs.map(x => '<li>' + one(x) + '</li>').join('') + '</ul></details>';
      } else if (r.docs.length > 1) {
        body = '<span class="kap-summary">' + one(r.d) + ' <span class="kap-n">· ' + r.docs.length + ' bildirim</span></span>';
      } else {
        const sub = r.d.subject && r.d.summary && r.d.subject.trim() !== r.d.summary.trim() && !/^Özel Durum Açıklaması/i.test(r.d.subject.trim())
          ? '<span class="kap-sub">' + escHtml(r.d.subject.trim()) + '</span>' : '';
        body = '<span class="kap-summary">' + one(r.d) + '</span>' + sub;
      }
      html += '<div class="kap-item"><time class="kap-day">' + dayTxt(r) + '</time><div class="kap-body">' +
        '<span class="kap-class-badge">' + lbl + '</span>' + body + '</div></div>';
    });
    if (!sigDone && sp) html += '<div class="kap-sig" role="separator"><span>' + escHtml(sigName) + ' başladı · ' + sp.d + ' ' + _HX_AY[sp.m - 1] + ' ' + sp.y + '</span></div>';
    if (rows.length > CAP) html += '</div><button type="button" class="hx-link kap-all" onclick="this.previousElementSibling.hidden=false;this.remove()">Tümünü göster (' + rows.length + ')</button>';

    listEl.innerHTML = html;
    listEl.style.display = '';

  } catch(e) {
    loadEl.innerHTML = '<div class="da-empty da-empty--error" role="alert" style="width:100%"><span><span aria-hidden="true">⚠️</span> Bildirimler yüklenemedi.</span><button type="button" class="da-retry" onclick="loadKapDisclosures()">Tekrar dene</button></div>';
  }
}

function escHtml(s) {
  if (!s) return '';
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}
/* K-BE (21.09) — BU KOPYA SILINDI, OLCUM OLU OLDUGUNU GOSTERDI.
   `safeHref` hem burada hem KANONIK bp-vocab.js'te UST DUZEY (global) tanimliydi.
   bp-vocab.js `defer` ile yuklendigi icin belge ayristirmasi BITTIKTEN sonra
   calisir ve bu satir-ici tanimi EZER: asagidaki 4 cagri (KAP/haber linkleri,
   hepsi async fetch sonrasi calisir) zaten bp-vocab.js'in surumunu kullaniyordu.
   Yani hangi surumun kazandigina `defer` zamanlamasi karar veriyordu — iki
   uygulama bugun ayni davransa da, birini degistiren bir sonraki tur icin
   sessiz bir tuzakti. Kanon: bp-vocab.js (tools/global-collision-check.py). */

/* ── Para birimi yardimcilari (Ozet 4 gosterge ve Temel ortak) ───────────
   KAP finansal raporlari TL sunar (USD/EUR raporlayanlar dahil, "TL'ye cevrilmis");
   Yahoo alanlari {value, currency} nesnesi olarak gelir. Olcek kisaltmasi tek
   kanon: bp-format.js bpMoneyCompact (K-BV). */
const _CUR_SYM = { TRY: '₺', USD: '$', EUR: '€', GBP: '£' };
function _curSym(c){ return _CUR_SYM[c] || (c ? ' ' + c : '₺'); }
function _fmtMoneyObj(m, perShare){
  if (typeof m === 'string') return m || null;
  if (!m || m.value == null) return null;
  const sym = _curSym(m.currency);
  const v = m.value;
  if (perShare) {
    return (v < 0 ? '-' : '') + Math.abs(v).toLocaleString('tr-TR', {minimumFractionDigits:2, maximumFractionDigits:2}) + ' ' + sym;
  }
  return bpMoneyCompact(v, { sym: sym });
}

/* ══ C-22 + C-22b (25.09) — Temel sekmesi v2 ════════════════════════════════
   Onayli taslak v3 (C-M6; O16e=B hizalama, O22=B son 12 ay). Veri: /fundamentals
   `kap` blogu (D-40a0 + D-40a2, aciklanan veri: her yilin degisimi kendi raporundan,
   farkli raporlarin tutarlari tek seride yok, kendi TUFE duzeltmemiz yok) + ust duzey
   `sektor_ortanca` (D-51 kurali) + `kap_durum`. `kap` yoksa bugunku alanlarla sade
   gorunum + "ayrintili veri hazirlaniyor" notu; verisi olmayan panel gizlenir.
   Fiyati makul mu? kanon §5.6: oran = deger / ortanca; <0,80 ucuz, >1,25 pahali,
   biri ucuz biri pahaliysa Karisik. Ortanca yoksa deger yazilir, hukum yazilmaz
   (Ozet Q2 ayni fonksiyonu kullanir: tvValuation). */
const TV_LBL = { revenue: 'Hasılat', gross_profit: 'Brüt kâr', operating_profit: 'Esas faaliyet kârı', ebitda: 'FAVÖK',
  net_income_parent: 'Net kâr', fcf: 'Serbest nakit akışı', equity_parent: 'Özkaynak', net_interest_income: 'Net faiz geliri',
  net_fees: 'Ücret ve komisyon', operating_income: 'Faaliyet geliri', loans: 'Krediler', deposits: 'Mevduat',
  total_assets: 'Varlıklar', cfo: 'İşletme nakit akışı' };
const TV_GROWTH = { sanayi: ['revenue', 'net_income_parent', 'fcf'], gyo: ['revenue', 'net_income_parent', 'fcf'],
  banka: ['net_interest_income', 'net_fees', 'net_income_parent', 'loans', 'deposits'],
  sigorta: ['net_income_parent', 'equity_parent', 'total_assets'] };
const TV_BASIS = { tms29: 'enflasyon düzeltmeli TL', nominal: 'TL', banka: 'TL', sigorta: 'TL',
  yabanci_para: 'TL\'ye çevrilmiş' };
const TV_CUT = 0.80, TV_EXP = 1.25;                  /* kanon §5.6 (C-M1): ucuz / pahali esigi */
const TV = { f: null, k: null, per: 'y', met: null, wired: false };

function _tvEl(id) { return document.getElementById(id); }
function _tvMoney(v) {
  if (v == null || !isFinite(v)) return '—';
  const a = Math.abs(v);
  return bpMoneyCompact(v, { frac: a >= 1e12 ? 2 : (a >= 1e11 ? 0 : 1) }) || '—';
}
/* Isaretten sonra U+2060 (kelime birlestirici): "-%66,7" satir sonunda bolunmesin */
function _tvNb(t) { return String(t).replace(/^([+-])%/, '$1\u2060%'); }
function _tvChg(v) { return v == null ? '—' : _tvNb(bpFormatPct(v, 1)); }        /* degisim: +%12,3 */
function _tvLvl(v) { return v == null ? '—' : _tvNb(bpPctLevel(v, 1)); }         /* seviye: %12,3 */
function _tvX(v, d) { return v == null ? '—' : v.toLocaleString('tr-TR', { minimumFractionDigits: d == null ? 2 : d, maximumFractionDigits: d == null ? 2 : d }); }
function _tvDate(iso) { return _hxDate(iso); }
function _tvHide(id, hide) { const el = _tvEl(id); if (el) el.hidden = !!hide; }
function _tvYearKey(k) { return k && k.son_yillik ? String(k.son_yillik).slice(0, 4) : null; }

/* ── Fiyati makul mu? (Temel + Ozet Q2 tek kanon) ─────────────────────────── */
function tvValuation(f) {
  if (!f) return null;
  const k = f.kap_durum === 'var' ? f.kap : null;
  const now = k && k.degerleme_simdi;
  const med = f.sektor_ortanca || null;
  /* O22=B: KAP son 12 ay F/K ve son aciklanan ozkaynakla PD/DD; kayit yoksa bugunku alanlar */
  const pe = now && !now.pay_uyumsuz ? now.fk : (k ? null : f.pe_ratio);
  const pb = now && !now.pay_uyumsuz ? now.pd_dd : (k ? null : f.pb_ratio);
  const rows = [['F/K', pe, med && med.fk, 1], ['PD/DD', pb, med && med.pd_dd, 2]].map(r => {
    const v = r[1], m = r[2];
    const ok = v != null && v > 0 && m && m.deger > 0;
    const q = ok ? v / m.deger : null;
    return { l: r[0], v: (v != null && v > 0) ? v : null, neg: v != null && !(v > 0), m: m || null, q: q, fr: r[3],
             t: q == null ? null : (q < TV_CUT ? -1 : (q > TV_EXP ? 1 : 0)) };
  });
  const scored = rows.filter(r => r.t !== null);
  let word = null;
  if (HX_TV2) {
    const W = { ucuz: 'Ucuz tarafta', makul: 'Makul', pahali: 'Pahalı tarafta', karisik: 'Karışık' };
    return { rows: rows, word: W[HX_TV2.h] || null, hasMed: !!HX_TV2.h, v2: true, wide: HX_TV2.kap === 'piyasa' };
  }
  if (scored.length) {
    const s = scored.reduce((a, r) => a + r.t, 0);
    const mixed = scored.length === 2 && scored[0].t * scored[1].t === -1;
    word = mixed ? 'Karışık' : (s < 0 ? 'Ucuz tarafta' : (s > 0 ? 'Pahalı tarafta' : 'Makul'));
  }
  return { rows: rows, word: word, hasMed: !!(med && (med.fk || med.pd_dd)) };
}
function _tvMedTxt(m, fr) { return m ? (m.kapsam === 'sektor' ? 'sektör ' : 'BIST ') + _tvX(m.deger, fr == null ? 2 : fr) : null; }

/* ── Grafikler (SVG, kutuphane yok; renk yalniz sinifla -> tokens.css) ─────── */
function _tvBars(items, W, H, label) {
  const CAP = 150;
  const clip = v => Math.max(-CAP, Math.min(CAP, v));
  const vals = items.filter(d => d.v != null).map(d => clip(d.v));
  if (!vals.length) return '';
  let mx = Math.max(0, Math.max.apply(null, vals)), mn = Math.min(0, Math.min.apply(null, vals));
  if (mx - mn < 20) { const e = (20 - (mx - mn)) / 2; if (mx > 0) mx += e; if (mn < 0) mn -= e; if (mx - mn < 20) mx = mn + 20; }
  const sp = mx - mn; mx += sp * 0.16; mn -= sp * 0.16;
  const top = 8, bot = H - 22, Y = v => top + (mx - v) / (mx - mn) * (bot - top);
  const n = items.length, gw = W / n, bw = Math.min(56, gw * 0.56);
  let s = '<svg class="tv-svg" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="' + escHtml(label) + '">' +
    '<line class="tv-zero" x1="0" x2="' + W + '" y1="' + Y(0).toFixed(1) + '" y2="' + Y(0).toFixed(1) + '"/>';
  items.forEach((d, i) => {
    const cx = gw * i + gw / 2;
    if (d.v == null) {
      s += '<text x="' + cx.toFixed(1) + '" y="' + (Y(0) - 6).toFixed(1) + '" text-anchor="middle">veri yok</text>';
    } else {
      const cv = clip(d.v), y0 = Y(0), y1 = Y(cv), y = Math.min(y0, y1), h = Math.max(2, Math.abs(y1 - y0));
      const cls = d.v < 0 ? 'tv-bar tv-bar--neg' : (d.v > 0 ? 'tv-bar' : 'tv-bar tv-bar--zero');
      s += '<rect class="' + cls + '" x="' + (cx - bw / 2).toFixed(1) + '" y="' + y.toFixed(1) + '" width="' + bw.toFixed(1) + '" height="' + h.toFixed(1) + '" rx="5"/>';
      if (cv !== d.v) {
        const zy = cv > 0 ? y + 10 : y + h - 10;
        s += '<path class="tv-cut" d="M' + (cx - bw / 2 - 2).toFixed(1) + ' ' + (zy + 3).toFixed(1) + ' l' + (bw / 4 + 1).toFixed(1) + ' -6 l' + (bw / 4 + 1).toFixed(1) + ' 6 l' + (bw / 4 + 1).toFixed(1) + ' -6 l' + (bw / 4 + 1).toFixed(1) + ' 6"/>';
      }
      s += '<text class="tv-vl" x="' + cx.toFixed(1) + '" y="' + (cv < 0 ? y1 + 15 : y1 - 6).toFixed(1) + '" text-anchor="middle">' + bpFormatPct(d.v, Math.abs(d.v) >= 1000 ? 0 : 1) + '</text>';
    }
    s += '<text x="' + cx.toFixed(1) + '" y="' + (H - 4) + '" text-anchor="middle">' + escHtml(String(d.k)) + '</text>';
  });
  return s + '</svg>';
}
function _tvLines(years, series, W, H) {
  const all = [];
  series.forEach(se => se.v.forEach(v => { if (v != null) all.push(v); }));
  if (!all.length) return '';
  let mx = Math.max.apply(null, all), mn = Math.min(0, Math.min.apply(null, all));
  mx = mx + (mx - mn) * 0.12 || 1;
  const L = 40, R = W - 16, T = 10, B = H - 22;   /* sol 40px: eksen etiketi sutunu (nokta ile cakismasin) */
  const X = i => L + (years.length === 1 ? 0 : i / (years.length - 1) * (R - L)), Y = v => T + (mx - v) / (mx - mn) * (B - T);
  let s = '<svg class="tv-svg" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="' + escHtml(series.map(se => se.n).join(', ')) + ', yıllara göre">';
  [0, 0.5, 1].forEach(fr => {
    const v = mn + (mx - mn) * fr, y = Y(v);
    s += '<line class="tv-grid-l" x1="' + L + '" x2="' + R + '" y1="' + y.toFixed(1) + '" y2="' + y.toFixed(1) + '"/>';
    s += '<text x="0" y="' + (y + 4).toFixed(1) + '">' + bpPctLevel(v, 0) + '</text>';
  });
  if (mn < 0) s += '<line class="tv-zero" x1="' + L + '" x2="' + R + '" y1="' + Y(0).toFixed(1) + '" y2="' + Y(0).toFixed(1) + '"/>';
  years.forEach((y, i) => { s += '<text x="' + X(i).toFixed(1) + '" y="' + (H - 4) + '" text-anchor="middle">' + escHtml(String(y)) + '</text>'; });
  series.forEach((se, si) => {
    const pts = [];
    se.v.forEach((v, i) => { if (v != null) pts.push([X(i), Y(v)]); });
    if (!pts.length) return;
    const lastIsInterim = se.interim && se.v[se.v.length - 1] != null;
    const main = lastIsInterim ? pts.slice(0, -1) : pts;
    if (main.length > 1) s += '<path class="tv-ln tv-ln--' + si + '" d="' + main.map((p, i) => (i ? 'L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join(' ') + '"/>';
    if (lastIsInterim && main.length) {
      const a = main[main.length - 1], b = pts[pts.length - 1];
      s += '<path class="tv-ln tv-ln--' + si + ' tv-ln--dash" d="M' + a[0].toFixed(1) + ' ' + a[1].toFixed(1) + ' L' + b[0].toFixed(1) + ' ' + b[1].toFixed(1) + '"/>';
    }
    pts.forEach(p => { s += '<circle class="tv-dot tv-dot--' + si + '" cx="' + p[0].toFixed(1) + '" cy="' + p[1].toFixed(1) + '" r="3.2"/>'; });
  });
  const lgd = '<div class="tv-lgd">' + series.map((se, si) => {
    let lv = null, li = -1;
    for (let i = se.v.length - 1; i >= 0; i--) { if (se.v[i] != null) { lv = se.v[i]; li = i; break; } }
    return '<span><i class="tv-sw tv-sw--' + si + '" aria-hidden="true"></i>' + escHtml(se.n) + (lv == null ? '' : ' <b>' + bpPctLevel(lv, 1) + '</b> <small>' + escHtml(String(years[li])) + '</small>') + '</span>';
  }).join('') + '</div>';
  return lgd + s + '</svg>';
}
function _tvBand(b, W) {
  const pts = b.band.filter(x => x.v != null && x.v > 0);
  const vals = pts.map(x => x.v);
  if (b.now != null) vals.push(b.now);
  if (b.med != null) vals.push(b.med);
  if (!vals.length) return '';
  const mx = Math.max.apply(null, vals) * 1.12, L = 8, R = W - 8, X = v => L + v / mx * (R - L);
  let s = '<svg class="tv-svg tv-band" viewBox="0 0 ' + W + ' 58" role="img" aria-label="' + escHtml(b.n + ': yıl sonu değerleri, son kapanış ve sektörün orta değeri') + '">' +
    '<rect class="tv-band-bg" x="' + L + '" y="22" width="' + (R - L) + '" height="10" rx="5"/>';
  if (pts.length) {
    const lo = Math.min.apply(null, pts.map(x => x.v)), hi = Math.max.apply(null, pts.map(x => x.v));
    s += '<rect class="tv-band-rg" x="' + X(lo).toFixed(1) + '" y="22" width="' + Math.max(4, X(hi) - X(lo)).toFixed(1) + '" height="10" rx="5"/>';
    pts.forEach(x => { s += '<circle class="tv-band-y" cx="' + X(x.v).toFixed(1) + '" cy="27" r="3.4"><title>' + x.y + ' sonu: ' + _tvX(x.v, 1) + '</title></circle>'; });
    s += '<text x="' + X(lo).toFixed(1) + '" y="50" text-anchor="middle">' + _tvX(lo, 1) + '</text>';
    if (X(hi) - X(lo) > 26) s += '<text x="' + X(hi).toFixed(1) + '" y="50" text-anchor="middle">' + _tvX(hi, 1) + '</text>';
  }
  if (b.med != null) {
    const mxp = Math.min(R - 30, Math.max(L + 30, X(b.med)));
    s += '<line class="tv-band-med" x1="' + X(b.med).toFixed(1) + '" x2="' + X(b.med).toFixed(1) + '" y1="14" y2="40"/><text x="' + mxp.toFixed(1) + '" y="10" text-anchor="middle">' + escHtml(b.medLbl) + '</text>';
  }
  if (b.now != null) s += '<circle class="tv-band-now" cx="' + X(b.now).toFixed(1) + '" cy="27" r="7.5"/>';
  return s + '</svg>';
}
function _tvDivBars(ys, W, H) {
  const mx = Math.max.apply(null, ys.map(d => d.v || 0)) || 1, n = ys.length, gw = W / n, bw = Math.min(28, gw * 0.6), T = 18, B = H - 20;
  let s = '<svg class="tv-svg" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="Hisse başına brüt temettü, yıllara göre"><line class="tv-zero" x1="0" x2="' + W + '" y1="' + B + '" y2="' + B + '"/>';
  ys.forEach((d, i) => {
    const cx = gw * i + gw / 2, h = Math.max(2, d.v / mx * (B - T));
    s += '<rect class="tv-bar" x="' + (cx - bw / 2).toFixed(1) + '" y="' + (B - h).toFixed(1) + '" width="' + bw.toFixed(1) + '" height="' + h.toFixed(1) + '" rx="4"><title>' + d.y + ': ' + _tvX(d.v) + ' ₺</title></rect>';
    s += '<text class="tv-vl" x="' + cx.toFixed(1) + '" y="' + (B - h - 5).toFixed(1) + '" text-anchor="middle">' + _tvX(d.v) + '</text>';
    s += '<text x="' + cx.toFixed(1) + '" y="' + (H - 4) + '" text-anchor="middle">' + d.y + '</text>';
  });
  return s + '</svg>';
}
function _tvW(el, mobile, desk) { const w = el && el.clientWidth; return w ? Math.max(260, Math.round(w)) : (window.innerWidth < 600 ? mobile : desk); }

/* ── kv tablosu: etiket + sabit genislikli 1-2 sayi sutunu (O16e=B hizalama) ── */
function _tvKv(head, rows, cls) {
  const two = head.length === 3;
  return '<div class="tv-kv-t' + (two ? '' : ' tv-kv-t--1') + (cls ? ' ' + cls : '') + '" role="table">' +
    '<div class="tv-kv-h" role="row">' + head.map((h, i) => '<span role="' + (i ? 'columnheader' : 'rowheader') + '">' + escHtml(h) + '</span>').join('') + '</div>' +
    rows.map(r => '<div class="tv-kv-r" role="row"><span role="rowheader">' + escHtml(r[0]) + '</span><b role="cell">' + r[1] + '</b>' + (two ? '<b role="cell" class="tv-p">' + r[2] + '</b>' : '') + '</div>').join('') + '</div>';
}

/* ── Buyume ─────────────────────────────────────────────────────────────── */
function _tvGrowthDraw() {
  const k = TV.k, sb = k.sablon, basis = TV_BASIS[k.basis] || 'TL';
  const ann = k.yillik_seri || [], qs = k.ceyrek_seri || [];
  const src = TV.per === 'q' ? qs.map(q => ({ k: q.ceyrek, d: q.degisim })) : ann.map(a => ({ k: a.yil, d: a.degisim }));
  const has = key => src.some(x => x.d && x.d[key] != null);
  let mets = TV_GROWTH[sb].filter(has);
  if (!mets.length) mets = TV_GROWTH[sb];
  if (mets.indexOf(TV.met) < 0) TV.met = mets[0];
  const seg = _tvEl('tvBuyumeSeg');
  seg.innerHTML = '<span class="tv-seg" role="group" aria-label="Kalem">' + TV_GROWTH[sb].map(m =>
      '<button type="button" data-m="' + m + '" aria-pressed="' + (m === TV.met) + '"' + (has(m) ? '' : ' disabled') + '>' + TV_LBL[m] + '</button>').join('') + '</span>' +
    (qs.length ? '<span class="tv-seg" role="group" aria-label="Dönem"><button type="button" data-p="y" aria-pressed="' + (TV.per === 'y') + '">Yıllık</button><button type="button" data-p="q" aria-pressed="' + (TV.per === 'q') + '">Çeyreklik</button></span>' : '');
  _tvEl('tvBuyumeU').textContent = (TV.per === 'q' ? 'Çeyreklik değişim · geçen yılın aynı çeyreğine göre · ' : 'Yıllık değişim · ') + basis;
  const tvChEl = _tvEl('tvBuyumeCh');
  tvChEl.innerHTML = _tvBars(src.map(x => ({ k: x.k, v: x.d ? x.d[TV.met] : null })), _tvW(tvChEl, 330, 520), window.innerWidth < 380 ? 136 : (window.innerWidth < 600 ? 150 : 190),
    TV_LBL[TV.met] + (TV.per === 'q' ? ' çeyreklik değişim' : ' yıllık değişim'));
}
function _tvGrowth(k) {
  const sb = k.sablon, ann = k.yillik_seri || [], qs = k.ceyrek_seri || [];
  if (!ann.length && !qs.length) return false;
  TV.met = TV_GROWTH[sb][0];
  const last = ann[ann.length - 1], lq = qs[qs.length - 1];
  const g = TV_GROWTH[sb];
  const parts = [];
  if (last) parts.push(last.yil + ' yılında ' + g.slice(0, 2).filter(m => last.degisim[m] != null).map(m => TV_LBL[m].toLocaleLowerCase('tr-TR') + ' ' + _tvChg(last.degisim[m])).join(', '));
  if (lq) {
    const qm = g.filter(m => lq.degisim[m] != null).slice(0, 2);
    if (qm.length) parts.push('son çeyrekte (' + lq.ceyrek + ') ' + qm.map(m => TV_LBL[m].toLocaleLowerCase('tr-TR') + ' ' + _tvChg(lq.degisim[m])).join(', '));
  }
  const say = parts.join('; ');
  _tvEl('tvBuyumeS').textContent = say ? say.charAt(0).toLocaleUpperCase('tr-TR') + say.slice(1) + '.' : '';
  const t = k.tutarlar;
  if (t && t.kalemler) {
    const title = k.basis === 'tms29' ? 'Tutar · ' + t.yil + ' sonu alım gücüyle' : 'Tutar · ' + (TV_BASIS[k.basis] || 'TL');
    const rows = Object.keys(t.kalemler).map(key => [TV_LBL[key] || key, _tvMoney(t.kalemler[key].cur), _tvMoney(t.kalemler[key].prev)]);
    _tvEl('tvBuyumeT').innerHTML = _tvKv([title, String(t.yil), String(t.onceki_yil)], rows);
  }
  const notes = ['Her yılın değişimi, şirketin o yılki raporundaki kendi karşılaştırmasından.'];
  if ((k.dusen_yillar || []).length) notes.push(Math.max.apply(null, k.dusen_yillar) + ' ve öncesi raporlar enflasyon düzeltmesi içermediği için grafikte yok.');
  if (qs.length) notes.push('Şirketler 4. çeyreği ayrıca açıklamaz; yıllık rapordan hesaplanır.');
  const n = _tvEl('tvBuyumeN'); n.textContent = notes.join(' '); n.hidden = false;
  _tvGrowthDraw();
  return true;
}

/* ── Karlilik ───────────────────────────────────────────────────────────── */
function _tvProfit(k) {
  const sb = k.sablon, o = k.oranlar || {}, yrs = Object.keys(o).sort();
  if (!yrs.length) return false;
  const ara = k.ara_donem, cy = yrs[yrs.length - 1], py = yrs[yrs.length - 2];
  const sv = key => yrs.map(y => (o[y] || {})[key] == null ? null : o[y][key]);
  let series, unit, kv, say;
  const labels = yrs.slice();
  if (sb === 'banka') {
    series = [{ n: 'Özsermaye kârlılığı', v: sv('ozsermaye_karliligi') }, { n: 'Gider / gelir', v: sv('gider_gelir') }];
    unit = 'Oran, % · yıllara göre';
    kv = [['Özsermaye kârlılığı', 'ozsermaye_karliligi'], ['Gider / gelir', 'gider_gelir'], ['Net faiz geliri / ort. varlık', 'net_faiz_marji'], ['Ücret ve komisyon payı', 'ucret_payi']];
    say = 'Özsermaye kârlılığı ' + cy + ' yılında ' + _tvLvl(o[cy].ozsermaye_karliligi) + ', gider / gelir oranı ' + _tvLvl(o[cy].gider_gelir) + '.';
  } else if (sb === 'sigorta') {
    series = [{ n: 'Özsermaye kârlılığı', v: sv('ozsermaye_karliligi') }];
    unit = 'Oran, % · yıllara göre';
    kv = [['Özsermaye kârlılığı', 'ozsermaye_karliligi'], ['Özkaynak değişimi', 'ozkaynak_degisim'], ['Varlık değişimi', 'varlik_degisim']];
    say = 'Özsermaye kârlılığı ' + cy + ' yılında ' + _tvLvl(o[cy].ozsermaye_karliligi) + (py ? ' (' + py + ': ' + _tvLvl(o[py].ozsermaye_karliligi) + ')' : '') + '.';
  } else {
    const withAra = ara && (ara.brut != null || ara.net != null);
    series = [{ n: 'Brüt', v: sv('brut'), interim: withAra }, { n: 'Net', v: sv('net'), interim: withAra }];
    if (withAra) { labels.push(ara.kisa); series[0].v.push(ara.brut); series[1].v.push(ara.net); }
    unit = 'Brüt ve net marj, % · yıllara göre' + (withAra ? ' ve ' + ara.etiket : '');
    kv = [['Özsermaye kârlılığı', 'ozsermaye_karliligi'], ['Net kâr / hasılat', 'net'], ['FAVÖK marjı', 'favok']];
    const c = o[cy] || {};
    say = cy + ' yılında brüt marj ' + _tvLvl(c.brut) + ', net marj ' + _tvLvl(c.net) + (withAra && ara.net != null ? '; ' + ara.etiket + ' net marj ' + _tvLvl(ara.net) : '') + '.';
  }
  _tvEl('tvKarlilikU').textContent = unit;
  _tvEl('tvKarlilikS').textContent = say;
  const tvChEl = _tvEl('tvKarlilikCh');
  tvChEl.innerHTML = _tvLines(labels, series, _tvW(tvChEl, 330, 520), window.innerWidth < 380 ? 136 : (window.innerWidth < 600 ? 150 : 200));
  const fmt = key => (key.indexOf('degisim') >= 0 ? _tvChg : _tvLvl);
  _tvEl('tvKarlilikT').innerHTML = _tvKv(['', cy, py || ''], kv.filter(r => (o[cy] || {})[r[1]] != null)
    .map(r => [r[0], fmt(r[1])(o[cy][r[1]]), py ? fmt(r[1])((o[py] || {})[r[1]]) : '—']));
  return true;
}

/* ── Degerleme ──────────────────────────────────────────────────────────── */
function _tvValue(f, k) {
  const V = tvValuation(f);
  if (!V) return false;
  const rows = V.rows.filter(r => r.v != null || r.neg);
  if (!rows.length && !(f.analyst_target != null && f.analyst_count)) return false;
  const chip = _tvEl('tvDegerlemeA');
  if (V.word) { chip.textContent = V.word; chip.className = 'tv-chip' + (V.word === 'Ucuz tarafta' ? ' tv-chip--u' : (V.word === 'Pahalı tarafta' ? ' tv-chip--p' : '')); chip.hidden = false; }
  const band = k ? (k.degerleme_bandi_v2 || []) : [];
  const inBand = (r, key) => {
    const b = band.map(x => x[key]).filter(v => v != null && v > 0);
    if (r.v == null || b.length < 2) return null;
    const lo = Math.min.apply(null, b), hi = Math.max.apply(null, b);
    return r.v < lo ? 'altında' : (r.v > hi ? 'üstünde' : 'içinde');
  };
  const sent = rows.map(r => {
    if (r.neg) return r.l + ' hesaplanmıyor (son 12 ayda zarar)';
    return r.l + ' ' + _tvX(r.v, r.fr) + (r.m ? ' · ' + _tvMedTxt(r.m, r.fr) : '');
  });
  let say = sent.join('; ');
  if (band.length) {
    const pos = [['F/K', 'fk'], ['PD/DD', 'pd_dd']].map(p => {
      const r = V.rows.filter(x => x.l === p[0])[0];
      const w = r ? inBand(r, p[1]) : null;
      return w ? p[0] + ' kendi yıl sonu bandının ' + w : null;
    }).filter(Boolean);
    if (pos.length) say += '. ' + pos.join(', ');
  }
  if (!V.hasMed) say += (say ? '. ' : '') + 'Sektörde karşılaştırma için yeterli şirket yok; bu yüzden ucuz ya da pahalı denmiyor';
  _tvEl('tvDegerlemeS').textContent = say ? say + '.' : '';
  const tvBox = _tvEl('tvDegerlemeB');
  const now = k && k.degerleme_simdi;
  if (band.length && now && !now.pay_uyumsuz) {
    const W = _tvW(tvBox, 330, 520);
    const defs = [['F/K', 'fk', V.rows[0]], ['PD/DD', 'pd_dd', V.rows[1]]];
    if (k.sablon === 'gyo' || k.sablon === 'banka') defs.reverse();   /* GYO/bankada PD/DD one */
    tvBox.innerHTML = defs.map(d => {
      const b = { n: d[0], now: d[2].v, med: d[2].m ? d[2].m.deger : null, medLbl: _tvMedTxt(d[2].m, d[2].fr) || '', band: band.map(x => ({ y: x.yil, v: x[d[1]] })) };
      if (!b.band.some(x => x.v != null && x.v > 0) && b.now == null) return '';
      return '<div class="tv-bd"><div class="tv-bd-h"><b>' + d[0] + '</b><span>' + (b.now != null ? 'Son kapanış ' + _tvX(b.now, d[2].fr) : 'Son 12 ayda zarar') + '</span></div>' + _tvBand(b, W) + '</div>';
    }).join('');
  } else tvBox.innerHTML = '';
  const an = _tvEl('tvDegerlemeAn');
  if (f.analyst_target != null && f.analyst_count && HX_PRICE) {
    const up = (f.analyst_target / HX_PRICE - 1) * 100;
    const dt = document.querySelector('.hx-dt');
    an.innerHTML = 'Analist hedef ortalaması <b>' + _hxNF2.format(f.analyst_target) + ' ₺</b> · fiyatın <b>' + bpPctLevel(Math.abs(up), 1) + '</b> ' +
      (up > 0 ? 'üstünde' : (up < 0 ? 'altında' : 'düzeyinde')) + ' · ' + f.analyst_count + ' analist' + (dt ? ' · ' + escHtml(dt.textContent.trim()) + 'na göre' : '');
    an.hidden = false;
  }
  const foot = _tvEl('tvDegerlemeN');
  if (now) {
    const ttm = now.son12ay_yontem === 'son12ay' ? 'son 12 ayın kârı (son yıllık kâr + ' + now.son12ay_etiket + ' raporunda açıklanan fark)' : 'son yıllık kâr';
    foot.textContent = 'F/K: piyasa değeri ÷ ' + ttm + '. PD/DD: piyasa değeri ÷ son açıklanan özkaynak.' + (band.length ? ' Bant: yıl sonu değerleri.' : '');
    foot.hidden = false;
  }
  return true;
}

/* ── Saglamlik kontrolu ─────────────────────────────────────────────────── */
const TV_CHK = {
  aktif_karliligi_pozitif: ['Aktif kârlılığı pozitif', 'lvl'], isletme_nakit_akisi_pozitif: ['İşletme nakit akışı pozitif', 'money1'],
  aktif_karliligi_artti: ['Aktif kârlılığı arttı', 'lvl2'], nakit_akisi_kardan_buyuk: ['Nakit akışı kârdan büyük', 'cmp'],
  uv_borc_orani_dustu: ['Uzun vadeli borç oranı düştü', 'lvl2'], cari_oran_artti: ['Cari oran arttı', 'x2'],
  yeni_pay_yok: ['Yeni pay çıkarılmadı', 'pay'], brut_marj_artti: ['Brüt marj arttı', 'lvl2'], aktif_devir_artti: ['Aktif devir hızı arttı', 'x2'],
  net_kar_pozitif: ['Net kâr pozitif', 'money1'], ozsermaye_karliligi_ortanca_ustu: ['Özsermaye kârlılığı bankaların orta değerinin üstünde', 'med'],
  kredi_mevduat_100_alti: ['Krediler mevduatı aşmıyor', 'lvl'], ozkaynak_varliktan_hizli: ['Özkaynak büyümesi varlık büyümesine yetişti', 'grow'],
  gider_gelir_40_alti: ['Gider / gelir oranı %40 veya altı', 'lvl'] };
const TV_CHK_KISA = { aktif_karliligi_pozitif: 'aktif kârlılığı', isletme_nakit_akisi_pozitif: 'işletme nakit akışı', aktif_karliligi_artti: 'aktif kârlılığındaki değişim',
  nakit_akisi_kardan_buyuk: 'nakit akışı ile kâr karşılaştırması', uv_borc_orani_dustu: 'uzun vadeli borç oranı', cari_oran_artti: 'cari oran',
  yeni_pay_yok: 'pay sayısı', brut_marj_artti: 'brüt marj', aktif_devir_artti: 'aktif devir hızı', net_kar_pozitif: 'net kâr',
  ozsermaye_karliligi_ortanca_ustu: 'özsermaye kârlılığı', kredi_mevduat_100_alti: 'kredi / mevduat oranı',
  ozkaynak_varliktan_hizli: 'özkaynak büyümesi', gider_gelir_40_alti: 'gider / gelir oranı' };
const TV_CHK_GRP = {
  piotroski: [['Kârlılık', ['aktif_karliligi_pozitif', 'isletme_nakit_akisi_pozitif', 'aktif_karliligi_artti', 'nakit_akisi_kardan_buyuk']],
    ['Borç ve likidite', ['uv_borc_orani_dustu', 'cari_oran_artti', 'yeni_pay_yok']], ['Verimlilik', ['brut_marj_artti', 'aktif_devir_artti']]],
  banka5: [['Kârlılık', ['net_kar_pozitif', 'ozsermaye_karliligi_ortanca_ustu']], ['Fonlama ve sermaye', ['kredi_mevduat_100_alti', 'ozkaynak_varliktan_hizli']],
    ['Verimlilik', ['gider_gelir_40_alti']]] };
function _tvChkVal(it, kind) {
  const c = it.cur, p = it.prev;
  if (kind === 'lvl') return _tvLvl(c);
  if (kind === 'lvl2') return _tvLvl(c) + ' ← ' + _tvLvl(p);
  if (kind === 'x2') return _tvX(c) + ' ← ' + _tvX(p);
  if (kind === 'money1') return _tvMoney(c);
  if (kind === 'cmp') return it.gecti ? 'nakit > kâr' : 'nakit ≤ kâr';
  if (kind === 'pay') return it.gecti ? 'sermaye aynı' : 'sermaye arttı';
  if (kind === 'med') return _tvLvl(c) + ' · bankaların orta değeri ' + _tvLvl(p);
  if (kind === 'grow') return _tvChg(c) + ' · varlık ' + _tvChg(p);
  return '';
}
function _tvChecks(k) {
  const s = k.saglamlik;
  if (!s || !s.maddeler || !s.toplam) return false;
  const by = {}; s.maddeler.forEach(m => { by[m.k] = m; });
  /* C-74 K9: .tv-unit büyük harf + lang=tr → "PİOTROSKİ"; özel ad lang=en ile korunur. */
  _tvEl('tvSaglamlikU').innerHTML = (s.yontem === 'piotroski' ? '9 maddelik bilinen yöntem (<span lang="en">Piotroski</span>) · ' : 'Bankaya uygun 5 madde · ') + (+s.yil) + ' ile ' + (s.yil - 1);
  _tvEl('tvSaglamlikP').innerHTML = '<b>' + s.puan + '</b><span>/ ' + s.toplam + '</span>';
  const grp = TV_CHK_GRP[s.yontem] || [];
  const okN = g => g[1].filter(x => by[x] && by[x].gecti === true).length, allN = g => g[1].filter(x => by[x] && by[x].gecti != null).length;
  const full = grp.filter(g => allN(g) && okN(g) === allN(g)).map(g => g[0].toLocaleLowerCase('tr-TR'));
  const miss = s.maddeler.filter(m => m.gecti === false).map(m => TV_CHK_KISA[m.k] || (TV_CHK[m.k] || [m.k])[0].toLocaleLowerCase('tr-TR'));
  let say = s.toplam + ' maddenin ' + s.puan + ' tanesi geçiyor';
  if (full.length) say += '; ' + full.join(' ve ') + ' maddelerinin hepsi geçiyor';
  if (miss.length && miss.length <= 3) say += '. Geçmeyen: ' + (miss.length > 1 ? miss.slice(0, -1).join(', ') + ' ve ' + miss[miss.length - 1] : miss[0]);
  if (s.eksik && s.eksik.length) say += '. ' + s.eksik.length + ' madde veri olmadığı için sayılmadı';
  _tvEl('tvSaglamlikS').textContent = say + '.';
  _tvEl('tvSaglamlikL').innerHTML = grp.map(g => {
    const its = g[1].filter(x => by[x] && by[x].gecti != null);
    if (!its.length) return '';
    return '<div><h4>' + g[0] + '</h4><ul>' + its.map(x => {
      const m = by[x], d = TV_CHK[x] || [x, ''];
      return '<li class="' + (m.gecti ? 'ok' : 'no') + '"><i aria-hidden="true">' + (m.gecti ? '✓' : '–') + '</i><span>' + escHtml(d[0]) +
        '<span class="sr-only">' + (m.gecti ? ': geçti' : ': geçmedi') + '</span></span><b>' + escHtml(_tvChkVal(m, d[1])) + '</b></li>';
    }).join('') + '</ul></div>';
  }).join('');
  return true;
}

/* ── Bilanco sagligi ────────────────────────────────────────────────────── */
function _tvBalance(f, k) {
  if (k && k.bilanco && _tvBalanceKap(k)) return true;
  return _tvBalanceLite(f);
}
function _tvBalanceKap(k) {
  {
    const b = k.bilanco, c = b.cur || {}, p = b.prev || {}, sb = k.sablon;
    let rows, say;
    if (sb === 'banka') {
      rows = [['Krediler', _tvMoney(c.krediler), _tvMoney(p.krediler)], ['Mevduat', _tvMoney(c.mevduat), _tvMoney(p.mevduat)],
        ['Kredi / mevduat', _tvLvl(c.kredi_mevduat), _tvLvl(p.kredi_mevduat)], ['Özkaynak', _tvMoney(c.ozkaynak), _tvMoney(p.ozkaynak)]];
      const o = (k.oranlar || {})[String(b.yil)] || {};
      say = 'Kredi / mevduat oranı ' + _tvLvl(c.kredi_mevduat) + (o.ozkaynak_degisim != null && o.varlik_degisim != null
        ? '; özkaynak ' + _tvChg(o.ozkaynak_degisim) + ', varlıklar ' + _tvChg(o.varlik_degisim) + ' değişti' : '') + '.';
    } else if (sb === 'sigorta') {
      rows = [['Özkaynak', _tvMoney(c.ozkaynak), _tvMoney(p.ozkaynak)], ['Toplam varlık', _tvMoney(c.toplam_varlik), _tvMoney(p.toplam_varlik)],
        ['Nakit', _tvMoney(c.nakit), _tvMoney(p.nakit)], ['Cari oran', _tvX(c.cari_oran), _tvX(p.cari_oran)]];
      say = 'Özkaynak ' + b.yil + ' sonunda ' + _tvMoney(c.ozkaynak) + '; kısa vadeli varlıklar kısa vadeli borçların ' + _tvX(c.cari_oran) + ' katı.';
    } else {
      const nbf = (x) => x.net_borc == null ? '—' : (x.net_borc < 0 ? 'net nakit' : _tvX(x.net_borc_favok));
      rows = [['Net borç (kiralamalar dahil)', _tvMoney(c.net_borc), _tvMoney(p.net_borc)], ['Net borç / FAVÖK', nbf(c), nbf(p)],
        ['Cari oran', _tvX(c.cari_oran), _tvX(p.cari_oran)], ['Nakit', _tvMoney(c.nakit), _tvMoney(p.nakit)]];
      say = (c.net_borc == null ? '' : (c.net_borc < 0 ? 'Nakdi borcundan fazla (net nakit ' + _tvMoney(-c.net_borc) + ')' : 'Net borç FAVÖK\'ün ' + _tvX(c.net_borc_favok) + ' katı')) +
        (c.cari_oran != null ? (c.net_borc == null ? 'K' : '; k') + 'ısa vadeli varlıklar kısa vadeli borçların ' + _tvX(c.cari_oran) + ' katı' : '') + '.';
    }
    rows = rows.filter(r => r[1] !== '—' || r[2] !== '—');     /* eslenmeyen kalem (ornek: faktoring) satir olmaz */
    if (!rows.length) return false;
    _tvEl('tvBilancoU').textContent = 'Dönem sonu · ' + (k.basis === 'tms29' ? b.yil + ' sonu alım gücüyle' : (TV_BASIS[k.basis] || 'TL'));
    _tvEl('tvBilancoS').textContent = say === '.' ? '' : say;
    _tvEl('tvBilancoT').innerHTML = _tvKv(['', String(b.yil), String(b.onceki_yil)], rows);
    return true;
  }
}
function _tvBalanceLite(f) {
  /* kap yok: bugunku alanlar (tek sutun) */
  const de = f.debt_to_equity != null ? f.debt_to_equity / 100 : null;   /* K-BX: yfinance YUZDE doner */
  const rows = [['Borç / özkaynak', de != null ? _tvX(de) : null], ['Cari oran', f.current_ratio != null ? _tvX(f.current_ratio) : null],
    ['Nakit ve benzerleri', _fmtMoneyObj(f.total_cash)]].filter(r => r[1]);
  if (!rows.length) return false;
  _tvEl('tvBilancoU').textContent = 'Son bilanço';
  _tvEl('tvBilancoS').textContent = '';
  _tvEl('tvBilancoS').hidden = true;
  _tvEl('tvBilancoT').innerHTML = _tvKv(['', 'Son'], rows);
  return true;
}

/* ── Temettu ────────────────────────────────────────────────────────────── */
function _tvDividend(f, k, divRow) {
  const tvBox = _tvEl('tvTemettuK'), tvChEl = _tvEl('tvTemettuCh');
  if (k && k.temettu) {
    const t = k.temettu, ys = (k.temettu_yillar || []).map(x => ({ y: x.yil, v: x.brut }));
    const stats = [];
    stats.push(['Son 12 ay verim', t.odeme_var && HX_PRICE ? bpPctLevel(t.brut_toplam / HX_PRICE * 100, 2) : 'Ödeme yok']);
    if (t.son_odeme) stats.push(['Son ödeme', _tvDate(t.son_odeme.odeme) + ' · ' + _tvX(t.son_odeme.brut) + ' ₺']);
    if ((t.duyurulan || []).length) stats.push(['Duyurulan', _tvDate(t.duyurulan[0].odeme) + ' · ' + _tvX(t.duyurulan[0].brut) + ' ₺']);
    tvBox.innerHTML = stats.map(s => '<div><span>' + s[0] + '</span><b>' + s[1] + '</b></div>').join('');
    _tvEl('tvTemettuS').textContent = t.odeme_var
      ? 'Son 12 ayda ' + t.odemeler.length + ' ödeme; hisse başına toplam ' + _tvX(t.brut_toplam) + ' ₺ brüt.' + ((t.duyurulan || []).length ? ' Duyurulan ödeme son 12 ay verimine girmez.' : '')
      : 'Son 12 ayda ödeme yok.' + (t.son_odeme ? ' Son ödeme ' + _tvDate(t.son_odeme.odeme) + '.' : '');
    tvChEl.innerHTML = ys.length >= 2 ? _tvDivBars(ys, _tvW(tvChEl, 330, 520), window.innerWidth < 380 ? 104 : (window.innerWidth < 600 ? 118 : 140)) : '';
    _tvEl('tvTemettuU').textContent = 'Hisse başına brüt ödeme · TL, ödendiği yılın parasıyla';
    return true;
  }
  if (divRow === undefined || divRow === null) return false;
  const last = divRow.last_div_date ? new Date(divRow.last_div_date + 'T00:00:00') : null;
  const asof = _hxSeries ? new Date(_hxSeries[_hxSeries.length - 1][0] + 'T00:00:00') : new Date();
  const recent = last && (asof - last) <= 365 * 864e5 && divRow.last_div_amount != null;
  tvBox.innerHTML = '<div><span>Son 12 ay</span><b>' + (recent ? 'Son ödeme ' + _tvDate(divRow.last_div_date) : 'Ödeme yok') + '</b></div>' +
    (recent ? '<div><span>Tutar</span><b>' + _tvX(divRow.last_div_amount) + ' ₺</b></div>' : '');
  _tvEl('tvTemettuS').textContent = recent ? '' : 'Son 12 ayda ödeme yok.';
  _tvEl('tvTemettuS').hidden = !!recent;
  tvChEl.innerHTML = '';
  return true;
}

/* ── Eksen satirlari (Temel skorun 4 alani; v2'de 5 eksen ve cumleleri SSR'dan gelir) ── */
function _tvAxes(f, k) {
  if (HX_TV2) return;  /* C-22c: v2 eksen cumleleri SSR'da (D-40c `eksenler[k].cumle`) */
  /* Satir: ilk ifade her zaman, digerleri telefonda gizli (taslak v3: mobilde tek ifade) */
  const set = (key, txt) => {
    const el = _tvEl('tvAx-' + key); if (!el || !txt) return;
    const parts = String(txt).split(/ · |; /);
    el.innerHTML = '<span>' + escHtml(parts[0]) + '</span>' + (parts.length > 1 ? '<span class="tv-ax-x"> · ' + escHtml(parts.slice(1).join(' · ')) + '</span>' : '');
  };
  const V = tvValuation(f), ve = V ? V.rows.filter(r => r.v != null).map(r => r.l + ' ' + _tvX(r.v, r.fr) + (r.m ? ' · ' + _tvMedTxt(r.m, r.fr) : '')) : [];
  if (k) {
    const now = k.degerleme_simdi || {}, cy = _tvYearKey(k), o = (k.oranlar || {})[cy] || {}, sb = k.sablon;
    const roe = now.ozsermaye_karliligi != null ? 'Özsermaye kârlılığı son 12 ayda ' + _tvLvl(now.ozsermaye_karliligi) : null;
    const yl = (k.yillik_seri || []).slice(-1)[0], b = (k.bilanco || {}).cur || {};
    if (sb === 'banka') {
      set('karlilik', [roe, cy + ' gider / gelir ' + _tvLvl(o.gider_gelir)].filter(Boolean).join(' · '));
      set('nakit_akisi', yl ? cy + ' yılında krediler ' + _tvChg(yl.degisim.loans) + ', mevduat ' + _tvChg(yl.degisim.deposits) : null);
      set('kaldirac', b.kredi_mevduat != null ? 'Kredi / mevduat ' + _tvLvl(b.kredi_mevduat) : null);
    } else if (sb === 'sigorta') {
      set('karlilik', [roe, cy + ' yılı ' + _tvLvl(o.ozsermaye_karliligi)].filter(Boolean).join(' · '));
      set('nakit_akisi', yl && yl.degisim.cfo != null ? cy + ' yılında işletme nakit akışı ' + _tvChg(yl.degisim.cfo) : null);
      set('kaldirac', b.cari_oran != null ? 'Cari oran ' + _tvX(b.cari_oran) + (o.ozkaynak_degisim != null ? ' · özkaynak ' + _tvChg(o.ozkaynak_degisim) : '') : null);
    } else {
      set('karlilik', [roe, cy + ' net marj ' + _tvLvl(o.net), 'FAVÖK marjı ' + _tvLvl(o.favok)].filter(Boolean).join(' · '));
      const t = (k.tutarlar || {}).kalemler || {}, sn = k.saglamlik && k.saglamlik.maddeler ? k.saglamlik.maddeler.filter(m => m.k === 'isletme_nakit_akisi_pozitif')[0] : null;
      set('nakit_akisi', [sn && sn.cur != null ? cy + ' işletme nakit akışı ' + _tvMoney(sn.cur) : null,
        t.fcf && t.fcf.cur != null ? 'serbest nakit akışı ' + _tvMoney(t.fcf.cur) : null].filter(Boolean).join(' · '));
      set('kaldirac', b.net_borc == null ? null : (b.net_borc < 0 ? 'Net nakit ' + _tvMoney(-b.net_borc) : 'Net borç / FAVÖK ' + _tvX(b.net_borc_favok)) + (b.cari_oran != null ? ' · cari oran ' + _tvX(b.cari_oran) : ''));
    }
    const g = yl ? TV_GROWTH[sb].filter(m => yl.degisim[m] != null)[0] : null;
    set('degerleme_buyume', [ve.join('; '), g ? cy + ' ' + TV_LBL[g].toLocaleLowerCase('tr-TR') + ' ' + _tvChg(yl.degisim[g]) : null].filter(Boolean).join(' · '));
    return;
  }
  set('karlilik', [f.roe != null ? 'Özsermaye kârlılığı ' + _tvLvl(f.roe) : null, f.profit_margin != null ? 'net kâr marjı ' + _tvLvl(f.profit_margin) : null].filter(Boolean).join(' · '));
  set('kaldirac', f.current_ratio != null ? 'Cari oran ' + _tvX(f.current_ratio) : null);
  set('degerleme_buyume', ve.join('; '));
}

/* ── Giris: sekme acilinca bir kez ──────────────────────────────────────── */
function _tvRender(f, divRow) {
  const k = f.kap_durum === 'var' && f.kap ? f.kap : null;
  _tvEl('tvGrid').hidden = false;
  TV.f = f; TV.k = k;
  const show = (id, ok) => { const el = _tvEl(id); if (el) el.hidden = !ok; };
  if (k) {
    const per = _tvEl('tvPer');
    const _b = TV_BASIS[k.basis] || 'TL';   /* C-74 K2: şablon adı + 'nominal' iç dil, gösterilmez */
    per.textContent = 'Son rapor: ' + (k.son_rapor_etiket || '') + (_b !== 'TL' ? ' · ' + _b : '');
    per.hidden = false;
    if (k.son_rapor_etiket) {
      _tvEl('tvDisc').textContent = 'Finansallar son açıklanan ' + k.son_rapor_etiket + ' dönemine kadar.';
      _tvEl('tvDisc').hidden = false;
    }
  } else {
    _tvHide('tvPrep', false);
  }
  show('tvBuyume', k ? _tvGrowth(k) : false);
  show('tvKarlilik', k ? _tvProfit(k) : _tvProfitLite(f));
  show('tvDegerleme', _tvValue(f, k));
  show('tvSaglamlik', k ? _tvChecks(k) : false);
  show('tvBilanco', _tvBalance(f, k));
  show('tvTemettu', _tvDividend(f, k, divRow));
  _tvAxes(f, k);
  _tvEl('tvGrid').setAttribute('aria-busy', 'false');
  _tvEl('tvGrid').classList.toggle('tv-grid--lite', !k);
}
function _tvProfitLite(f) {
  const rows = [['Özsermaye kârlılığı', f.roe], ['Net kâr marjı', f.profit_margin], ['Faaliyet marjı', f.operating_margin]].filter(r => r[1] != null);
  if (!rows.length) return false;
  _tvEl('tvKarlilikU').textContent = 'Oran, % · son 12 ay';
  _tvEl('tvKarlilikS').hidden = true;
  _tvEl('tvKarlilikT').innerHTML = _tvKv(['', 'Son'], rows.map(r => [r[0], _tvLvl(r[1])]));
  return true;
}
function _tvWire() {
  if (TV.wired) return;
  TV.wired = true;
  _tvEl('tvBuyumeSeg').addEventListener('click', ev => {
    const b = ev.target.closest('button'); if (!b || b.disabled || !TV.k) return;
    if (b.dataset.m) TV.met = b.dataset.m;
    if (b.dataset.p) TV.per = b.dataset.p;
    _tvGrowthDraw();
  });
  let t = null;
  if (typeof ResizeObserver === 'function') new ResizeObserver(() => { clearTimeout(t); t = setTimeout(() => { if (TV.k) { _tvGrowthDraw(); _tvProfit(TV.k); if (TV.f) _tvValue(TV.f, TV.k); } }, 120); }).observe(_tvEl('tvGrid'));
  _tvEl('tvRetry').addEventListener('click', () => { _tvEl('tvErr').hidden = true; loadFundamentals(); });
}
let _tvDone = false;
async function loadFundamentals() {
  if (_tvDone) return;
  _tvWire();
  try {
    const [fj, dj] = await _bpFundDivJSON();
    if (!fj) throw new Error('fundamentals');
    const f = fj && fj.fundamentals;
    const divRow = dj === undefined ? undefined : (((dj && dj.stocks) || []).find(x => x.ticker === TICKER) || null);
    if (!f || !Object.keys(f).length) {       /* hisse icin temel veri yok: hata degil, sessiz not */
      _tvEl('tvGrid').hidden = true;
      _tvEl('tvGrid').setAttribute('aria-busy', 'false');
      const pr = _tvEl('tvPrep'); pr.textContent = 'Bu hisse için finansal veri henüz yok.'; pr.hidden = false;
      _tvDone = true;
      return;
    }
    _tvRender(f, divRow);
    _tvDone = true;
  } catch (e) {
    _tvEl('tvGrid').hidden = true;
    _tvEl('tvErr').hidden = false;
  }
}

/* ── Diğer Hisseler Accordion ──────────────────── */

/* Makro şerit: bp-search.js'te kendiliğinden başlar (C-15). */

/* 21.09 (K-AU): `.ind-help` sayfa-yerel tap-toggle + Escape dinleyicileri
   SILINDI. `.ind-help` artik kanonik [data-tip] mekanizmasini kullaniyor;
   bp-tooltip.js (yukarida yuklu) tap-toggle, Escape, disari-tiklama,
   aria-describedby VE viewport cevirmesi/yatay kelepceyi zaten yapiyor.
   Eski CSS-yalniz `::after` sabit yonlu aciliyordu, bkz. hisse.css ~582. */

/* F3 — Eğitim Tooltip toggle (localStorage bp_show_tooltips) */
const _TIPS_KEY = 'bp_show_tooltips';
function _applyTooltipVisibility() {
  // DEV2-bughunt-r7: dosyadaki diger anahtarlarin (bp_hisse_tab vb.) aksine
  // guardsizdi — private-mode/quota hatasinda throw edip zincirleme kirilirdi.
  let show = true;
  try { show = localStorage.getItem(_TIPS_KEY) !== 'false'; } catch (e) { /* varsayilan: goster */ }
  document.querySelectorAll('.ind-help').forEach(el => { el.style.display = show ? '' : 'none'; });
  const tb = document.getElementById('tooltipToggle');
  if (tb) {
    tb.textContent = show ? '? Kapat' : '? Açıkla';
    tb.setAttribute('aria-pressed', show ? 'true' : 'false');  /* K-AO */
    tb.style.color = show ? 'var(--bp-brand)' : 'var(--bp-text3)';
    tb.style.borderColor = show ? 'rgba(184,195,255,0.35)' : 'var(--bp-border)';
  }
}
function toggleTooltips() {
  try {
    const cur = localStorage.getItem(_TIPS_KEY) !== 'false';
    localStorage.setItem(_TIPS_KEY, String(!cur));
  } catch (e) { /* private-mode/quota — sessizce yut, gorsel toggle yine de calissin */ }
  _applyTooltipVisibility();
}
_applyTooltipVisibility();
/* Re-apply after indicators render (called from renderSummary flow) */
window._bpApplyTooltips = _applyTooltipVisibility;

/* SPEC-017 v2 — Tab-switch (gerçek gizle/göster) — Ozan direktifi 23:55 TR
 * Anchor scroll yerine: aktif tab dışındaki içerikler display:none → sayfa KISALIR.
 * Özet (default): chart/ai/news gizli, sadece signal info + mini stats + history görünür.
 * Grafik/AI/Haberler: sadece o panel görünür.
 */
(function(){
  var segments = document.querySelectorAll('.da-tabs [role="tab"]');
  if (!segments.length) return;

  /* Sekme -> panel gorunurlugu TEK kanondan yonetilir: her panelin kendi
     `data-tab-content` niteligi (asagida). K-CP (22.09): burada ayrica bir
     ALL_PANELS/SHOW_FOR_TAB ID listesi vardi -- ayni is icin IKINCI bir kanon.
     Uc ID sayiyordu (chart-section · sigExplainSection · newsSection) ama ai
     sekmesinin `aiFundSection`ini ve haberler sekmesinin `kapSection`ini hic
     bilmiyordu; ucunun de `data-tab-content`i oldugu icin ikinci adim zaten
     birincinin yazdigini eziyordu, yani liste hem eksik hem etkisizdi. Bir
     panel eklendiginde guncellenmeyi bekleyen ikinci bir yer birakmamak icin
     kaldirildi. Sekme adlari artik tek yerde. */
  var VALID_TABS = ['ozet', 'grafik', 'temel', 'haberler'];
  /* C-19: eski sekme adlari. AI sekmesinin icerigi Ozet'te ("Ne anlama geliyor?"). */
  var TAB_ALIAS = { ai: 'ozet' };
  function _normTab(t) { t = TAB_ALIAS[t] || t; return VALID_TABS.indexOf(t) === -1 ? 'ozet' : t; }

  /* C-19: sekme basina tembel veri. Her sekme ilk acildiginda bir kez yukler;
     Grafik /kap, /news, /fundamentals istemez. MTF (Coklu Zaman Dilimi) Ozet'teki
     "Teknik" akordeonu acilinca istenir. */
  var _tabLoaded = {};
  function _loadTabData(tab) {
    if (_tabLoaded[tab]) return;
    _tabLoaded[tab] = true;
    try {
      if (tab === 'ozet') { loadOzetChart(); loadOzetExtras(); }
      else if (tab === 'grafik') { loadChart(); }
      else if (tab === 'temel') { loadFundamentals(); }
      else if (tab === 'haberler') { loadKapDisclosures(); }
    } catch (e) { console.warn('sekme verisi yuklenemedi: ' + tab, e); }
  }

  function applyTab(tab, opts) {
    opts = opts || {};
    tab = _normTab(tab);
    // SPEC-017 v2 Faz A — data-tab-content attribute (true tab-switch)
    /* C-25a: gorunurluk hisse.css'teki [data-hx-tab] kuralindan; ilk deger SSR'da gelir. */
    var _main = document.getElementById('main-content');
    if (_main) _main.setAttribute('data-hx-tab', tab);
    segments.forEach(function(s){
      var isActive = s.dataset.segment === tab;
      s.classList.toggle('active', isActive);
      s.setAttribute('aria-selected', isActive ? 'true' : 'false');
      s.tabIndex = isActive ? 0 : -1;
      /* C-07: dar ekranda sekme seridi kayarsa aktif sekme gorunur kalir
         (scrollIntoView({inline:'nearest'}) esdegeri, yalniz yatay: sayfa dikey kaymaz) */
      var bar = s.parentElement;
      if (isActive && bar && bar.scrollWidth > bar.clientWidth) {
        var l = s.getBoundingClientRect().left - bar.getBoundingClientRect().left + bar.scrollLeft, r = l + s.offsetWidth;
        if (l < bar.scrollLeft) bar.scrollLeft = l;
        else if (r > bar.scrollLeft + bar.clientWidth) bar.scrollLeft = r - bar.clientWidth;
      }
    });
    // URL state (SPEC-017 v2 Faz A P0-1)
    if (!opts.skipUrl) {
      try {
        /* K-CR (22.09): VARSAYILAN SEKME URL'DE GORUNMEZ. Onceki hal her sekme
           icin `set('tab', tab)` yaziyordu, yani temiz `/hisse/ASELS` acilisi
           adres cubugunu `/hisse/ASELS?tab=ozet` yapiyordu -- sayfanin KENDI
           ilan ettigi kanonik adresten (link rel=canonical ve og:url, ikisi de
           parametresiz; canli olcum 22.09) farkli bir URL. Kullanicinin
           kopyalayip paylastigi adres bu oldugu icin ayni icerik iki adresle
           yayiliyordu. Kanon /tarama'nin kurali: varsayilan deger silinir,
           varsayilan-disi deger yazilir. */
        var url = new URL(window.location.href);
        var _cur = url.searchParams.get('tab');
        var _want = (tab === 'ozet') ? null : tab;
        if (_cur !== _want) {
          if (_want === null) url.searchParams.delete('tab');
          else url.searchParams.set('tab', _want);
          history.replaceState({tab: tab}, '', url.toString());
        }
      } catch(e) { console.warn('URL sekme durumu senkronizasyonu basarisiz', e); }
    }
    // GA4
    try { if (typeof gtag === 'function') gtag('event','tab_switch',{ticker: typeof TICKER!=='undefined'?TICKER:'', tab: tab}); } catch(e) { /* gtag best-effort analitik - ad-blocker/consent durumunda tanimsiz olabilir, sekme gecisini bozmamali */ }
    _loadTabData(tab);
    if (tab === 'ozet' && typeof hxChartDraw === 'function') { try { hxChartDraw(); } catch (e) { /* olculemezse ResizeObserver cizer */ } }
    // SPEC-017 Faz F Bug 3: Grafik tab açıldığında chart resize (display:none→block sonrası width sync)
    if (tab === 'grafik') {
      try { if (typeof window.bpChartResize === 'function') window.bpChartResize(); } catch(e) { console.warn('bpChartResize cagrisi basarisiz (grafik sekmesi acilirken)', e); }
    }
  }
  window.applyTab = applyTab;

  segments.forEach(function(s){
    s.addEventListener('click', function(e){
      e.preventDefault();
      var tab = s.dataset.segment || 'ozet';
      applyTab(tab);
      window.bpScrollTop();
    });
    s.addEventListener('keydown', function(e){
      if (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') {
        e.preventDefault();
        var tab = s.dataset.segment || 'ozet';
        applyTab(tab);
        window.bpScrollTop();
        return;
      }
      // CPO-DEV2-078(A): ARIA APG tablist roving-focus — ok tuslari SADECE odagi
      // tasir, aktive etmez (aktivasyon icerik-agir: AI fetch/chart resize tetikler,
      // bu yuzden manual-activation deseni bilinçli tercih)
      var idx = Array.prototype.indexOf.call(segments, s);
      var nextIdx = -1;
      if (e.key === 'ArrowRight') nextIdx = (idx + 1) % segments.length;
      else if (e.key === 'ArrowLeft') nextIdx = (idx - 1 + segments.length) % segments.length;
      else if (e.key === 'Home') nextIdx = 0;
      else if (e.key === 'End') nextIdx = segments.length - 1;
      if (nextIdx !== -1) {
        e.preventDefault();
        segments[nextIdx].focus();
      }
    });
  });

  // Browser back/forward popstate handling
  window.addEventListener('popstate', function(ev){
    try {
      var url = new URL(window.location.href);
      applyTab(_normTab(url.searchParams.get('tab') || 'ozet'), {skipUrl: true});
    } catch(e) { console.warn('popstate sekme geri yukleme basarisiz', e); }
  });

  /* Ilk yukleme: sekme SSR'da secili gelir (C-25a, ?tab= > 'ozet'). Eski localStorage
     hatirlama kalkti: sunucu onu bilemez, ilk boyamadan sonra sekme degistirip kayma uretiyordu. */
  var _m0 = document.getElementById('main-content');
  applyTab(_normTab((_m0 && _m0.getAttribute('data-hx-tab')) || 'ozet'), {skipUrl: false});
})();
