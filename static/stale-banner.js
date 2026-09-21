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
function bpFmtUpdateDate(ageS) {
  var d = new Date(Date.now() - ageS * 1000);
  var dd = String(d.getDate()).padStart(2, '0');
  var mm = String(d.getMonth() + 1).padStart(2, '0');
  return dd + '.' + mm;
}

function bpUpdateStaleBanner(dq, ageS, refreshing) {
  var banner = document.getElementById('staleBanner');
  var bTxt   = document.getElementById('staleBannerText');
  if (!banner) return;
  var hasAge = ageS != null && !isNaN(ageS);
  var dateTxt = hasAge ? bpFmtUpdateDate(ageS) : null;
  var suffix = refreshing === true ? ' Yenileniyor...' : '';
  if (dq === 'critical') {
    var critTxt = hasAge
      ? dateTxt + ' gün sonu verileri gösterilmektedir — güncel veri şu an alınamıyor.'
      : 'Veriler güncellenemiyor — son güncelleme zamanı doğrulanamıyor.';
    if (bTxt) { bTxt.textContent = critTxt + suffix; bTxt.style.color = '#f85149'; }
    banner.style.background  = 'rgba(248,81,73,0.12)';
    banner.style.borderColor = '#f85149';
    banner.style.display     = 'block';
  } else if (dq === 'stale') {
    var staleTxt = hasAge
      ? dateTxt + ' gün sonu verileri gösterilmektedir.'
      : 'Veriler bayat olabilir — son güncelleme zamanı doğrulanamıyor.';
    if (bTxt) { bTxt.textContent = staleTxt + suffix; bTxt.style.color = '#f5c949'; }
    banner.style.background  = 'rgba(245,201,73,.10)';
    banner.style.borderColor = 'rgba(245,201,73,.4)';
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
      ? dateTxt + ' gün sonu verileri gösterilmektedir — son işlem gününün kapanışı henüz alınamadı.'
      : 'Son işlem gününün kapanışı henüz alınamadı — gösterilen veriler daha eski.';
    if (bTxt) { bTxt.textContent = eksikTxt + suffix; bTxt.style.color = '#f5c949'; }
    banner.style.background  = 'rgba(245,201,73,.10)';
    banner.style.borderColor = 'rgba(245,201,73,.4)';
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
   /api/data-quality endpoint'ini (CPO-1121 §1) 60s'de bir çekip aynı fonksiyona post eder. */
var _dqEverLoaded = false;
function bpPollDataQuality() {
  /* bughunt-13.09: bpLoadMacroBar'daki AYNI kilit bug'ı burada da vardı —
     hidden iken KOŞULSUZ atlanıyordu, sayfa hidden yüklenip visibilitychange
     hiç ateşlenmezse stale-banner hiçbir zaman ilk kontrolünü yapamıyordu
     (bkz. bpLoadMacroBar fix'i, aynı prensip: hiç veri gelmediyse hidden'dan
     bağımsız dene, zaten yüklendiyse hidden'da boşa pil harcama). */
  if (document.hidden && _dqEverLoaded) return;
  fetch('/api/data-quality', {cache: 'no-store', signal: AbortSignal.timeout(10000)})
    .then(function(r) { return r.json(); })
    .then(function(j) { bpUpdateStaleBanner(j.data_quality, j.stocks_age_s); _dqEverLoaded = true; })
    .catch(function(e) { console.error('data-quality polling basarisiz', e); });
}
var _dqPollInterval = null;
var _dqVisListenerAdded = false;
function bpStartDataQualityPolling() {
  if (_dqPollInterval) return;
  bpPollDataQuality();
  _dqPollInterval = setInterval(bpPollDataQuality, 60000);
  /* bughunt-12.09: bpLoadMacroBar ile ayni desendeki bug — sayfa document.hidden
     iken yuklenirse ilk poll no-op donuyordu, sekme gorunur olunca da hicbir
     yerde tekrar denenmiyordu (60s'lik interval de arka planda tarayicilar
     tarafindan suspend edilebiliyor). Tum 8 sayfa bu fonksiyonu TEK cagri
     noktasindan kullandigi icin fix burada merkezi, sablon basina tekrar
     gerekmiyor (r98/bpLoadMacroBar fix'iyle ayni ilke). */
  if (!_dqVisListenerAdded) {
    _dqVisListenerAdded = true;
    document.addEventListener('visibilitychange', function() {
      if (!document.hidden) bpPollDataQuality();
    });
  }
}
