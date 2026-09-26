/* CPO-1125 İş Kolu B — kanonik stale banner render + polling.
   Kaynak: index.html'in mevcut renk/metin mantığı (DEV-1474 spec), 6 sayfaya
   merkezileştirildi. Kanonik veri: data_quality + stocks_age_s — /api/health.status
   BANNER'A GİRMEZ (SENECA drift bulgusunun kökü, tarama.html'de düzeltildi).
   CPO-1151 §3: ageS bilinmediğinde '?' yerine dürüst metin; "Yenileniyor..."
   yalnız /api/data.refreshing===true iken eklenir (refreshing 3. parametre,
   /api/data-quality'yi kullanan çağıranlarda undefined → ek metin yok). */
/* CPO-1555: "X dk/sa önce güncellendi" göreli ifadesi EOD mimarisiyle
   (günde bir kez, gün-sonu kapanışı) çelişiyordu — Ozan'ın notu: mutlak
   tarih ("08.09 gün sonu verileri gösterilmektedir") her zaman daha doğru.
   ageS'ten geriye doğru gerçek takvim tarihini hesaplar. */
/* K-BL (21.09): bu fonksiyon takvim gününü getDate()/getMonth() ile, yani
   KULLANICININ CİHAZ SAAT DİLİMİNDE hesaplıyordu. Banner'ın söylediği şey
   ("18.09 gün sonu verileri gösterilmektedir") bir BIST işlem günüdür; TR
   gününden başka bir takvimde üretilemez. K-BD'de aynı hata dışa aktarım
   dosya adında bulunup bp-format.js'te kanona bağlanmıştı — bu İKİNCİ çağrı
   yeri o taramada görülmemişti (orada `toISOString`, burada `getDate()`:
   aynı hata, farklı yazım).
   Kanon yüklenmemişse (bp-format.js sayfada yoksa) TARİH ÜRETİLMEZ: null
   döner ve çağıran zaten var olan "son güncelleme zamanı doğrulanamıyor"
   dürüst metnine düşer — yanlış bir günü basmaktansa hiç basmamak. */
function bpFmtUpdateDate(ageS) {
  if (typeof bpTrDatePartsAt !== 'function') return null;
  var t = bpTrDatePartsAt(Date.now() - ageS * 1000);
  if (!t) return null;
  var p2 = function (n) { return (n < 10 ? '0' : '') + n; };
  return p2(t.d) + '.' + p2(t.m);
}

function bpUpdateStaleBanner(dq, ageS, refreshing) {
  var banner = document.getElementById('staleBanner');
  var bTxt   = document.getElementById('staleBannerText');
  if (!banner) return;
  var hasAge = ageS != null && !isNaN(ageS);
  var dateTxt = hasAge ? bpFmtUpdateDate(ageS) : null;
  /* K-BL: tarih üretilemediyse (kanon yok) "bilinmiyor" dalı kullanılır —
     aşağıdaki üç dal da dateTxt'i yalnız hasAge ile koşulluyordu. */
  if (!dateTxt) hasAge = false;
  var suffix = refreshing === true ? ' Yenileniyor...' : '';
  if (dq === 'critical') {
    var critTxt = hasAge
      ? dateTxt + ' gün sonu verileri gösterilmektedir — güncel veri şu an alınamıyor.'
      : 'Veriler güncellenemiyor — son güncelleme zamanı doğrulanamıyor.';
    if (bTxt) { bTxt.textContent = critTxt + suffix; bTxt.style.color = 'var(--bp-sat)'; }
    banner.style.background  = 'rgba(var(--bp-sat-rgb),0.12)';
    banner.style.borderColor = 'var(--bp-sat)';
    banner.style.display     = 'block';
  } else if (dq === 'stale') {
    var staleTxt = hasAge
      ? dateTxt + ' gün sonu verileri gösterilmektedir.'
      : 'Veriler bayat olabilir — son güncelleme zamanı doğrulanamıyor.';
    if (bTxt) { bTxt.textContent = staleTxt + suffix; bTxt.style.color = 'var(--bp-stale)'; }
    banner.style.background  = 'rgba(var(--bp-stale-rgb),.10)';
    banner.style.borderColor = 'rgba(var(--bp-stale-rgb),.4)';
    banner.style.display     = 'block';
  } else if (dq === 'seans_disi_eksik') {
    /* CPO-1680 FRONTEND YARISI (21.09, K-AB). DEV1 backend yarısını yapmıştı:
       `_compute_data_quality` artık "normal seans dışı" (seans_disi) ile
       "seans dışı AMA son işlem gününün verisi GELMEDİ" (seans_disi_eksik)
       ayrımını üretiyor ve docstring'i açıkça "frontend bu değere göre ayrı
       banner açabilir" diyor. O dal HİÇ YAZILMAMIŞTI: yeni değer buradaki
       son `else`e düşüyor ve banner GİZLİ kalıyordu.
       ⛔ CANLI KANIT (21.09 Pzt 07:30): /api/data-quality
       `seans_disi_eksik` + `stocks_age_s` 306514 (**85.1 saat**) döndürürken
       ana sayfa 17.09 Perşembe kapanışını hiçbir uyarı olmadan, /hisse ise
       nötr gri "Piyasa kapalı" çipiyle servis ediyordu. Kullanıcı için
       "hafta sonu, normal" ile "Cuma seansı hiç işlenmedi" ayırt edilemezdi.
       RENK: `stale` ile aynı kehribar — bu bir arıza ama `critical` (kırmızı,
       "veri şu an hiç alınamıyor") değil; gösterilen fiyat GERÇEK, sadece
       beklenen işlem gününden eski. */
    var eksikTxt = hasAge
      ? dateTxt + ' gün sonu verileri gösterilmektedir — son işlem günü kapanışı henüz alınamadı.'
      : 'Son işlem günü kapanışı henüz alınamadı — gösterilen veriler daha eski.';
    if (bTxt) { bTxt.textContent = eksikTxt + suffix; bTxt.style.color = 'var(--bp-stale)'; }
    banner.style.background  = 'rgba(var(--bp-stale-rgb),.10)';
    banner.style.borderColor = 'rgba(var(--bp-stale-rgb),.4)';
    banner.style.display     = 'block';
  } else if (dq === 'seans_disi') {
    /* CPO-1338: seans dışı stale by-design — banner KASITLI gizli (fresh ile
       karıştığı için değil, bu dal açıkça o kararı veriyor).
       DİKKAT: bu dal artık YALNIZ gerçekten normal olan seans dışını kapsar;
       gerçek gecikme yukarıdaki `seans_disi_eksik` dalına gider. */
    banner.style.display = 'none';
  } else {
    banner.style.display = 'none';
  }
}

/* tarama/hisseler/sinyal_performans — /api/data (216 kayıt) çekmiyorlar, hafif
   /api/data-quality endpoint'ini (CPO-1121 §1) okuyup aynı fonksiyona post eder.
   C-09 (26.09): 60 sn'lik setInterval kalktı (EOD: veri günde bir değişir).
   Yüklemede bir kez + sekme görünür olunca en fazla 15 dk'da bir okunur.
   Sayfa gizli yüklenirse ilk okuma görünür olunca yapılır (bughunt-12/13.09). */
var _dqEverLoaded = false;
var _dqLastFetch = 0;
function bpPollDataQuality() {
  _dqLastFetch = Date.now();
  fetch('/api/data-quality', {cache: 'no-store', signal: AbortSignal.timeout(10000)})
    .then(function(r) { return r.json(); })
    .then(function(j) { bpUpdateStaleBanner(j.data_quality, j.stocks_age_s); _dqEverLoaded = true; })
    .catch(function(e) { console.error('data-quality okunamadi', e); });
}
var _dqStarted = false;
function bpStartDataQualityPolling() {
  if (_dqStarted) return;
  _dqStarted = true;
  bpPollDataQuality();
  document.addEventListener('visibilitychange', function() {
    if (document.hidden) return;
    if (!_dqEverLoaded || Date.now() - _dqLastFetch >= 15 * 60 * 1000) bpPollDataQuality();
  });
}
