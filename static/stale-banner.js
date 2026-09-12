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
  } else if (dq === 'seans_disi') {
    /* CPO-1338: seans dışı stale by-design — banner KASITLI gizli (fresh ile
       karıştığı için değil, bu dal açıkça o kararı veriyor). */
    banner.style.display = 'none';
  } else {
    banner.style.display = 'none';
  }
}

/* tarama/hisseler/sinyal_performans — /api/data (216 kayıt) çekmiyorlar, hafif
   /api/data-quality endpoint'ini (CPO-1121 §1) 60s'de bir çekip aynı fonksiyona post eder. */
function bpPollDataQuality() {
  if (document.hidden) return; /* sekme arka plandayken /api/data-quality cekilmez (bp-search.js bpLoadMacroBar ile ayni desen) */
  fetch('/api/data-quality', {cache: 'no-store', signal: AbortSignal.timeout(10000)})
    .then(function(r) { return r.json(); })
    .then(function(j) { bpUpdateStaleBanner(j.data_quality, j.stocks_age_s); })
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
