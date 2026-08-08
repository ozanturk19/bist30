/* CPO-1125 İş Kolu B — kanonik stale banner render + polling.
   Kaynak: index.html'in mevcut renk/metin mantığı (DEV-1474 spec), 6 sayfaya
   merkezileştirildi. Kanonik veri: data_quality + stocks_age_s — /api/health.status
   BANNER'A GİRMEZ (SENECA drift bulgusunun kökü, tarama.html'de düzeltildi).
   CPO-1151 §3: ageS bilinmediğinde '?' yerine dürüst metin; "Yenileniyor..."
   yalnız /api/data.refreshing===true iken eklenir (refreshing 3. parametre,
   /api/data-quality'yi kullanan çağıranlarda undefined → ek metin yok). */
function bpUpdateStaleBanner(dq, ageS, refreshing) {
  var banner = document.getElementById('staleBanner');
  var bTxt   = document.getElementById('staleBannerText');
  if (!banner) return;
  var hasAge = ageS != null && !isNaN(ageS);
  var mins   = hasAge ? Math.floor(ageS / 60) : null;
  var suffix = refreshing === true ? ' Yenileniyor...' : '';
  if (dq === 'critical') {
    var critTxt = hasAge
      ? 'Veriler ' + mins + ' dakikadır güncellenemiyor.'
      : 'Veriler güncellenemiyor — son güncelleme zamanı doğrulanamıyor.';
    if (bTxt) bTxt.textContent = critTxt + suffix;
    banner.style.background  = 'rgba(248,81,73,0.12)';
    banner.style.borderColor = '#f85149';
    banner.style.display     = 'block';
  } else if (dq === 'stale') {
    var staleTxt = hasAge
      ? 'Veriler ' + mins + ' dk önce güncellendi.'
      : 'Veriler güncellendi — son güncelleme zamanı doğrulanamıyor.';
    if (bTxt) bTxt.textContent = staleTxt + suffix;
    banner.style.background  = '';
    banner.style.borderColor = '';
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
  fetch('/api/data-quality', {cache: 'no-store'})
    .then(function(r) { return r.json(); })
    .then(function(j) { bpUpdateStaleBanner(j.data_quality, j.stocks_age_s); })
    .catch(function() {});
}
function bpStartDataQualityPolling() {
  bpPollDataQuality();
  setInterval(bpPollDataQuality, 60000);
}
