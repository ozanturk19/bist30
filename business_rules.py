"""
Faz 12 P1 — Data Quality Validator (CPO-693): BIST business-rule doğrulama
+ Kanonik Etiket/Tarih-Türetme Kütüphanesi (CPO-1196/1321/1335): ADX/sinyal/
giriş-kalitesi etiketleri ve sinyal-tarihi türetme fonksiyonlarının tek kaynağı.
"""

import math
import logging
import re
from datetime import date, datetime

logger = logging.getLogger(__name__)

# BIST circuit breaker: ±10% günlük limit
BIST_DAILY_LIMIT_PCT = 10.5
MIN_PRICE = 0.01


def validate_change_pct(ticker, change_pct):
    """BIST ±10% tavan kuralı — split/corporate action anomali detection."""
    if change_pct is None or (isinstance(change_pct, float) and math.isnan(change_pct)):
        return {"ok": False, "flag": "ANOMAL_NULL_CHANGE_PCT", "ticker": ticker, "value": change_pct}
    try:
        cp = float(change_pct)
    except (TypeError, ValueError):
        return {"ok": False, "flag": "INVALID_CHANGE_PCT", "ticker": ticker, "value": change_pct}
    if abs(cp) > BIST_DAILY_LIMIT_PCT:
        return {
            "ok": False,
            "flag": "ANOMAL",
            "ticker": ticker,
            "value": change_pct,
            "msg": f"change_pct {cp:.2f}% BIST %10 tavan ihlali",
        }
    return {"ok": True, "ticker": ticker, "value": change_pct}


def validate_price(ticker, price, field="price"):
    """Fiyat geçerliliği: pozitif, not None, not NaN."""
    if price is None:
        return {"ok": False, "flag": "NULL_PRICE", "ticker": ticker, "field": field}
    if isinstance(price, float) and (math.isnan(price) or math.isinf(price)):
        return {"ok": False, "flag": "NAN_PRICE", "ticker": ticker, "field": field, "value": price}
    try:
        if float(price) <= 0:
            return {"ok": False, "flag": "NEGATIVE_PRICE", "ticker": ticker, "field": field, "value": price}
    except (TypeError, ValueError):
        return {"ok": False, "flag": "INVALID_PRICE", "ticker": ticker, "field": field, "value": price}
    return {"ok": True, "ticker": ticker, "field": field, "value": price}


def validate_signal_consistency(ticker, signal, signal_price):
    """AL/SAT sinyali için signal_price zorunlu (CPO-DEV2-062: SAT AL ile aynı kapsama alındı)."""
    if isinstance(signal, str) and signal.upper() in ("AL", "SAT"):
        if signal_price is None or (isinstance(signal_price, float) and math.isnan(signal_price)):
            return {
                "ok": False,
                "flag": "MISSING_SIGNAL_PRICE",
                "ticker": ticker,
                "signal": signal,
                "value": signal_price,
                "msg": f"signal={signal} ama signal_price={signal_price!r}",
            }
    return {"ok": True, "ticker": ticker, "signal": signal}


def validate_date_range(ticker, signal_date):
    """Sinyal tarihi ayrıştırılabilir olmalı VE bugün-veya-geçmiş olmalı.

    Tip/format hatası (beklenmeyen tip, ya da DD.MM.YYYY/YYYY-MM-DD dışı bir
    string) -> flag=INVALID_DATE. Ayrıştırma başarılı ama tarih gelecekte ise
    -> flag=FUTURE_DATE.
    """
    if signal_date is None:
        return {"ok": True, "ticker": ticker}
    try:
        if isinstance(signal_date, str):
            s = signal_date[:10]
            # DD.MM.YYYY (uygulama formatı) veya ISO YYYY-MM-DD her ikisini destekle
            try:
                sd = datetime.strptime(s, "%d.%m.%Y").date()
            except ValueError:
                sd = datetime.strptime(s, "%Y-%m-%d").date()
        elif isinstance(signal_date, datetime):
            sd = signal_date.date()
        elif isinstance(signal_date, date):
            sd = signal_date
        else:
            return {"ok": False, "flag": "INVALID_DATE", "ticker": ticker, "error": f"unknown type {type(signal_date)}"}
        today = _today_tr()
        if sd > today:
            return {
                "ok": False,
                "flag": "FUTURE_DATE",
                "ticker": ticker,
                "signal_date": str(sd),
                "today": str(today),
            }
    except Exception as e:
        return {"ok": False, "flag": "INVALID_DATE", "ticker": ticker, "error": str(e)}
    return {"ok": True, "ticker": ticker, "signal_date": str(sd)}


def validate_stock(stock_dict):
    """
    Bir hissenin tüm business rule'larını çalıştır.
    Returns: list[dict] — boş liste = tümü geçti
    """
    ticker = stock_dict.get("ticker", "UNKNOWN")
    errors = []

    r = validate_change_pct(ticker, stock_dict.get("change_pct"))
    if not r["ok"]:
        logger.warning("BRV_FAIL %s: %s change_pct=%s", ticker, r["flag"], stock_dict.get("change_pct"))
        errors.append(r)

    r = validate_price(ticker, stock_dict.get("price"))
    if not r["ok"]:
        logger.warning("BRV_FAIL %s: %s price=%s", ticker, r["flag"], stock_dict.get("price"))
        errors.append(r)

    r = validate_signal_consistency(ticker, stock_dict.get("signal"), stock_dict.get("signal_price"))
    if not r["ok"]:
        logger.warning("BRV_FAIL %s: %s signal=%s", ticker, r["flag"], stock_dict.get("signal"))
        errors.append(r)

    # CPO-DEV2-062: signal_price None degilse (validate_signal_consistency zaten None/NaN zorunlulugunu kontrol ediyor) negatif/sifir/bozuk degeri de yakala.
    if stock_dict.get("signal_price") is not None:
        r = validate_price(ticker, stock_dict.get("signal_price"), field="signal_price")
        if not r["ok"]:
            logger.warning("BRV_FAIL %s: %s signal_price=%s", ticker, r["flag"], stock_dict.get("signal_price"))
            errors.append(r)

    r = validate_date_range(ticker, stock_dict.get("signal_date"))
    if not r["ok"]:
        logger.warning("BRV_FAIL %s: %s signal_date=%s", ticker, r["flag"], stock_dict.get("signal_date"))
        errors.append(r)

    return errors


def validate_stocks_list(stocks):
    """
    Tüm hisse listesini validate et.
    Returns: {"total": N, "errors": [...], "failed_tickers": [...]}
    """
    all_errors = []
    for s in stocks:
        errs = validate_stock(s)
        all_errors.extend(errs)

    failed = list({e["ticker"] for e in all_errors})
    if all_errors:
        logger.warning("BRV: %d violations across %d tickers: %s",
                       len(all_errors), len(failed), failed)

    return {"total": len(stocks), "errors": all_errors, "failed_tickers": failed}


# bug-hunt r66: bu esikler (18/25/40) app.py:~96 icindeki ImportError-fallback kopyasi
# ve templates/hisse.html:~1880 icindeki JS ilk-render fallback'iyle BIREBIR AYNI kalmali.
def derive_adx_label(adx):
    """ADX değerinden tek kaynaklı trend-gücü etiketi (Site Contract v1.2).

    Eşikler: <18 Zayıf · 18-25 Orta · 25-40 Güçlü · >=40 Çok Güçlü.
    CPO-1196 D0 #4: önceden aynı eşik 6 farklı yüzeyde 6 farklı sayı ile
    tanımlıydı (app.py 3 yer + tarama/hisse/karsilastir/metodoloji şablonları).
    Bu fonksiyon kanonik kaynaktır; ancak app.py'nin ImportError-fallback'i ve
    templates/hisse.html'in JS ilk-render fallback'i eşikleri kendi kopyalarında
    tutar (otomatik senkron kilidi yok, elle eşitlenmeli — bkz. üstteki yorum).
    """
    try:
        a = float(adx)
    except (TypeError, ValueError):
        return "Zayıf"
    if a >= 40:
        return "Çok Güçlü"
    if a >= 25:
        return "Güçlü"
    if a >= 18:
        return "Orta"
    return "Zayıf"


# CPO-1656: /api/data (app.py, Faz 1 #3) ve /api/karsilastir farklı eşiklerle
# (kanonik <70 vs karsilastir'in kendi >70) çelişen RSI bölge etiketi
# üretiyordu — aynı TUPRS RSI=70.6 için biri "Dikkatli" biri "(Aşırı Alım)"
# gösteriyordu. derive_adx_label ile aynı desen: tek kaynak burada.
#
# CPO-1745 (22.09): "İdeal Giriş Penceresi" (RSI 45-60) sinyalden BAĞIMSIZ
# üretiliyordu — long-only üründe ancak AL sinyaliyle anlamlı bir vaat, ama
# canlı ölçümde bu adı taşıyan hisselerin çoğu AL değildi (bazıları SAT).
# Frontend zaten bpRsiZoneText() ile bu ismi signal!='AL' iken "Nötr bölge"ye
# çeviriyordu (bp-format.js) — aynı düzeltme artık kaynakta da var, ham
# /api/data tüketicileri (frontend'in üzerinden geçmeyenler) de doğru metni alır.
def derive_rsi_zone(rsi, signal=None):
    """RSI değerinden tek kaynaklı bölge etiketi (Site Contract Bölüm 3.3).

    Eşikler: <30 Aşırı Satım · 30-45 Dip Toparlanması · 45-60 Sağlıklı
    Momentum · 60-70 Trend Güçleniyor · 70-80 Dikkatli · >=80 Aşırı Alım.

    `signal` verilirse (AL/SAT/BEKLE): "Sağlıklı Momentum" yalnız AL
    sinyalinde döner, aksi halde "Nötr Bölge" — bu isim AL olmayan bir
    sinyalde olumlu vaat taşımasın diye (CPO-1745; ad C-60 ile "Sağlıklı Momentum"). Parantezli aralık
    YOK (CPO-1759): diğer beş bölge adının hiçbiri aralık taşımıyor,
    RSI sayısı zaten rozetin yanında basılı.
    """
    try:
        r = float(rsi)
    except (TypeError, ValueError):
        return None
    if r < 30:
        return "Aşırı Satım"
    if r < 45:
        return "Dip Toparlanması"
    if r < 60:
        return "Sağlıklı Momentum" if signal == "AL" else "Nötr Bölge"
    if r < 70:
        return "Trend Güçleniyor"
    if r < 80:
        return "Dikkatli"
    return "Aşırı Alım"


# CPO-1656 EK YANIT: EMA12/EMA99 kriterinde histerezis/ölü-bant YOK, salt
# e12>e99/e12<e99 karşılaştırması — CPO Seçenek A'yı (gerçek dead-band, sinyal
# üretimini değiştirir) Ozan onayı gerektiren ayrı bir konu olarak ayırdı,
# Seçenek B'yi (UI-only rozet, sinyal motoru DEĞİŞMEZ) onayladı. Bu fonksiyon
# SADECE ham fark yüzdesini ve eşik-altı "kararsızlık bölgesi" bayrağını
# hesaplar — app.py'deki e12_bull/e12_bear karşılaştırması bu fonksiyonu
# hiç çağırmaz, sıfır regresyon riski.
EMA_DEADBAND_THRESHOLD_PCT = 0.15


def derive_ema_deadband(e12, e99):
    """EMA12/EMA99 ham fark yüzdesi + kararsızlık-bölgesi bayrağı (Seçenek B).

    Döner: (diff_pct, is_deadband). diff_pct=|e12-e99|/e99*100, is_deadband
    diff_pct < %0.15 ise True (CPO-1656'da CPO'nun önerdiği eşik). Sinyal
    sınıflandırması (AL/SAT/BEKLE) bu eşikten etkilenmez — sadece UI rozeti içindir.
    """
    try:
        e12f = float(e12)
        e99f = float(e99)
    except (TypeError, ValueError):
        return None, False
    if e99f == 0:
        return None, False
    diff_pct = abs(e12f - e99f) / abs(e99f) * 100
    return round(diff_pct, 3), diff_pct < EMA_DEADBAND_THRESHOLD_PCT


# ── T1.1 (CPO-1321 FAZ 1) — kanonik sözlük evi ──────────────────────────────
# derive_adx_label ile aynı desen. NOT (r53 bug-hunt + CPO-DEV2-060 düzeltmesi):
# bu 4 sözlük app.py için tek kaynak ama templates/*.html HÂLÂ kendi bağımsız
# kopyalarını tutuyor (SIGNAL_LABELS 14+ yerde) — değerler
# şu an senkron ama gerçek 'tek kaynağa taşıma' refactor'ü henüz yapılmadı. Yeni bir
# etiket eklerken/değiştirirken template kopyalarını da elle güncellemeyi unutma.
# T1.2 (CPO-1321): SIGNAL_LABELS['SAT'] eski SAT etiketinden "Trend Bozuldu"ya
# app.py, business_rules.py, blog_content.py, manifest.json ve 18 şablonda
# tek commit'te yeniden adlandırıldı (bkz. tests/test_cpo1321_faz1_t1_2_trend_bozuldu_rename.py).

SIGNAL_LABELS = {
    "AL": "Güçlü Trend",
    "SAT": "Trend Bozuldu",
    "BEKLE": "Yatay",
}

# ── D-09 — sinyal kuralı ve Teknik Güç tek kaynak (app.py'den taşındı) ──────
# app.py yerelde (Python 3.9) import edilemediği için bu üç fonksiyon burada
# durur; testler (tests/test_d09_skor_sinyal.py) doğrudan bunları çağırır.
# Tüketiciler: analyze() canlı durum + sinyal başlangıcı, _bar_signal_fast
# (geçmiş barlar/backtest), _load_cache_from_disk (restart köprüsü).
# Kalan kopyalar (grafik uçları) D-47 koşul kaydına taşınacak.
#
# Kanon §3 (O23=A) durumu 5 koşuldan türetir: (1) Supertrend yukarı,
# (2) ADX >= 25, (3) EMA 12 > EMA 99, (4) DI+ > DI-, (5) haftalık EMA 20
# yükseliyor. Motor (2) ile (4)'ü tek oy sayar; (5) ayrı bir kapıdır.
# Güçlü Trend = beşi birden; Trend Bozuldu = tersleri birden; diğer her
# durum Yatay. İç anahtarlar AL / SAT / BEKLE (SIGNAL_LABELS).
TREND_ADX_MIN = 25


def trend_flags(st_dir, adx, di_plus, di_minus, e12, e99):
    """Günlük koşulların iki yönlü oyları (haftalık kapı classify_signal'de).

    st_dir: Supertrend yönü (+1 yukarı, -1 aşağı). NaN karşılaştırmaları
    False döner, yani eksik gösterge hiçbir yöne oy vermez.
    """
    adx_ok = adx >= TREND_ADX_MIN
    return {
        "st_bull":  st_dir == 1,
        "st_bear":  st_dir == -1,
        "adx_bull": adx_ok and di_plus > di_minus,
        "adx_bear": adx_ok and di_minus > di_plus,
        "e12_bull": e12 > e99,
        "e12_bear": e12 < e99,
    }


def classify_signal(flags, weekly_dir):
    """trend_flags() oyları + haftalık yön → (sinyal, bull_score, bear_score).

    weekly_dir: haftalık EMA 20 yönü (+1 / -1 / 0 = hesaplanamadı).
    CPO-DEV2-039/040 + CPO-1496: weekly_dir == 0 gerçek bir "yatay" ölçümü
    değil, _weekly_trend() hiç çağrılmadığında (CB açık) ya da <25 bar /
    hata yolunda üretilen doldurma değeridir; kapı bu durumda iki yönde de
    KAPALI kalır (fail-closed), durum Yatay olur.
    """
    bull = int(flags["st_bull"]) + int(flags["adx_bull"]) + int(flags["e12_bull"])  # max 3
    bear = int(flags["st_bear"]) + int(flags["adx_bear"]) + int(flags["e12_bear"])  # max 3
    if bull >= 3 and weekly_dir != -1 and weekly_dir != 0:
        return "AL", bull, bear
    if bear >= 3 and weekly_dir != 1 and weekly_dir != 0:
        return "SAT", bull, bear
    return "BEKLE", bull, bear


def signal_from_indicators(st_dir, adx, di_plus, di_minus, e12, e99, weekly_dir):
    """Tek bar için durum (AL / SAT / BEKLE) — trend_flags + classify_signal."""
    return classify_signal(trend_flags(st_dir, adx, di_plus, di_minus, e12, e99), weekly_dir)[0]


def compose_score(adx, vol_ratio, bull_score, confirmed, rsi, signal="AL"):
    """Teknik Güç (0-100) — tek skor kaynağı. CPO-535 spec.

    SADECE analyze() içinde çağrılır, sonucu signal_strength olarak cache'e
    yazılır (restart köprüsü _load_cache_from_disk aynı girdilerden yeniden
    türetir). Güçlü Trend listesi ve hisse detay sayfası ikisi de bu TEK
    cache alanını okur — ayrı ayrı yeniden hesaplama YASAK (CPO-983 puanlama
    tutarlılık fix, Site Contract §24). AUDIT-004 tier_score'un yerine geçer
    (CPO-531 #36) — ve SPEC-018 W2'de tier badge ataması da bu skora taşındı
    (CPO-1004).

    CPO-DEV2-053 (2026-08-22): "Yön gücü" bileşeni (bull_or_bear_score/3*25)
    kaldırıldı — 54 aktif sinyalin tamamında bull_score/bear_score istisnasız
    =3 olduğu kanıtlandı (sinyal gate'i zaten 3/3 oybirliği şart koşuyor, ara
    değer hiç yayınlanamıyor), yani bu bileşen aktif bir sinyal için hiçbir
    ayrıştırıcı bilgi taşımıyordu — sabit +25 puanlık bir taban gibi
    davranıyordu. bull_score parametresi imza uyumluluğu için tutuldu ama
    artık skora katkısı yok.

    Bileşenler (ham max 75, 100/75 ile 0-100'e yeniden ölçeklenir):
        ADX       : min(adx, 50) / 50 * 30   → max 30
        Hacim     : min(vol_ratio, 5) / 5 * 25 → max 25
        Teyit     : +10 (signal_bars >= 3)
        RSI bölge : AL  → +10 (50-75) | +5 (>75)
                    SAT → +10 (25-50) | +5 (<25)   → max 10 (P0-2, CPO-DEV2-031/033:
                    önceki sürüm signal parametresi almıyordu, SAT sinyalinde de AL
                    bandını uyguluyordu — düşük RSI'lı bir SAT ayı teyidi almadan
                    bonus alıyor, tier'ı yapay olarak şişiriyordu)

    Tier eşikleri (bkz. app._derive_tier — CPO-DEV2-053/055, 70/56 kesim):
        70+ → Güçlü Sinyal | 56-69 → Standart | <56 → (rozet yok)
        Düşük likidite / yakın bilanço → bir kademe düşürülür (analyze()).
    """
    def _finite(v, default):
        try:
            v = float(v)
        except (TypeError, ValueError):
            return default
        return v if math.isfinite(v) else default

    s = 0.0
    s += min(_finite(adx, 0), 50) / 50 * 30
    s += min(_finite(vol_ratio, 1.0), 5) / 5 * 25
    s += 10 if confirmed else 0
    rsi = _finite(rsi, 50)
    if signal == "SAT":
        if 25 <= rsi <= 50:
            s += 10
        elif rsi < 25:
            s += 5
    else:
        if 50 <= rsi <= 75:
            s += 10
        elif rsi > 75:
            s += 5
    return int(round(s * 100 / 75))

# D-39b: ENTRY_QUALITY_LABELS kalktı (entry_quality üretilmiyor).

# ── D-39 (Ozan O10, kanon §2.2) — teknik hedef / işlem yönetimi dili ────────
# API'lerden kalkan alanlar: analyze() artık üretmez; disk cache'ten gelen eski
# kayıtlardan app._enrich_stock düşürür. Analist hedef fiyatı (temel analiz)
# bu listede DEĞİL — değerleme göstergesi olarak kalır.
RETIRED_TRADE_KEYS = ("tp1", "tp2", "tp_level", "rr_signal", "rr_ratio", "rr_now",
                      "entry_note", "optimal_entry", "entry_quality")

# Üretilen teknik metinde (sinyal açıklaması, e-posta, yorum) olmaması gereken
# dil; varyant ve büyük/küçük harf duyarsız. Haber/analist metnine UYGULANMAZ
# (analist hedef fiyatı meşru).
TRADE_LANG_RE = re.compile(
    r"(?i)\btp[12]\b|\br/r\b|risk/ödül|k[aâ]r al|hedefe ulaş|hedef (seviye|fiyat)|stop[- ]?loss|"
    r"stop (bölge|seviye)|zarar durdur|\bSL\b|ideal giriş|giriş (fiyat|kalite|bölge|pencere)|"
    r"\b(long|short)\b|kazanma oran")

# ── CPO-1335 — göreli tarih etiketi kanonik türetimi ────────────────────────
# KUSUR: "Bugün"/"Dün" etiketi iki DONMUŞ eksenden türetiliyordu:
#   (a) signal_bars — veri setindeki bar sayısı. Ticker o gün tazelenmezse son
#       bar dünün barıdır, dolayısıyla bars=1 "bugün" demek değildir. Canlı
#       kanıt 08.08.2026 (payda 215): bars=1 hem 07.08 hem 06.08 signal_date'ine
#       düşüyordu; bars=2 -> 06.08 ve 05.08; bars=3 -> 04.08 ve 05.08. Sapma tek
#       tip DEĞİL — "hepsini bir gün geri al" düzeltmesi işe yaramaz.
#   (b) is_new_signal — analyze() içinde (signal_date == today_str) olarak
#       hesaplanıp payload'a donduruluyor (app.py:1635). Ticker tazelenmezse
#       eski günün True'su taşınıyor: RYSAS is_new_signal=True, signal_date=
#       06.08, ölçüm günü 08.08 → anasayfa hero'su "bugün güçlü trende geçti"
#       diyordu. Bu alan analyze()'ın (DEV1 alanı) çıktısı; BURADA
#       DEĞİŞTİRİLMİYOR, yalnız TÜKETİM tarafı artık ona güvenmiyor.
#
# KANONİK EKSEN: signal_date — payload'da 215/215 dolu, "DD.MM.YYYY", gerçek bar
# tarihinden türer (app.py:1619/1623). Etiket GERÇEK bugünle (Europe/Istanbul)
# karşılaştırılarak OKUMA/RENDER ANINDA üretilir.
#
# Tarih bilinmiyorsa etiket ÜRETİLMEZ (None) — çağıran nötr bir şey basmalı,
# ASLA "Bugün"e düşmemeli (eski `bars || 1` deseninin tuzağı buydu).
#
# JS aynası: static/bp-format.js (bpSignalDateLabel) — eşikler birebir aynı,
# tests/test_cpo1335_signal_date_label.py ikisini birlikte kilitler.

# Kanon: göreli gün adı ("Bugün"/"Dün") yok; etiket her zaman takvim tarihidir.
TR_MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
             "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

_TZ_TR_NAME = "Europe/Istanbul"


def _today_tr():
    """Europe/Istanbul takvim günü. zoneinfo yoksa sistem yerel gününe düşer."""
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo(_TZ_TR_NAME)).date()
    except Exception as e:
        logger.warning(
            "BRV: zoneinfo/tzdata Europe/Istanbul kullanilamiyor (%s), sistem yerel gunune dusuluyor",
            e,
        )
        return date.today()


def parse_signal_date(signal_date):
    """"DD.MM.YYYY" -> date. Ayrıştırılamazsa None — varsayım YOK."""
    if isinstance(signal_date, datetime):
        return signal_date.date()
    if isinstance(signal_date, date):
        return signal_date
    if not isinstance(signal_date, str):
        return None
    try:
        return datetime.strptime(signal_date.strip(), "%d.%m.%Y").date()
    except (ValueError, TypeError):
        return None


def signal_date_age_days(signal_date, today=None):
    """signal_date ile bugün arasındaki TAKVİM GÜNÜ farkı. Bilinmiyorsa None.

    Pozitif = geçmiş, 0 = bugün, negatif = gelecek (savunma amaçlı ele alınır).
    """
    sd = parse_signal_date(signal_date)
    if sd is None:
        return None
    ref = today if today is not None else _today_tr()
    if isinstance(ref, datetime):
        ref = ref.date()
    if not isinstance(ref, date):
        return None
    return (ref - sd).days


def is_signal_from_today(signal_date, today=None):
    """Sinyal GERÇEKTEN bugüne mi ait.

    Donmuş `is_new_signal` bayrağı yerine bunu kullan — o bayrak analiz anında
    hesaplanıp donuyor, bayat ticker'da eski günün değerini taşıyor.
    """
    return signal_date_age_days(signal_date, today) == 0


def last_eod_day(stocks, today=None):
    """D-06: verideki en yeni seans (EOD) günü — takvimden DEĞİL veriden.

    QA 24.09: /gundem listesi seans içinde takvim gününe (24.09) bakıp boş
    kalıyordu, oysa veri 23.09 kapanışına aitti ve 13 hisse o gün durum
    değiştirmişti. Referans gün artık verinin kendisi: her hissenin son bar
    günü (`bar_date`), yoksa `signal_date` (sinyalin başladığı bar; son bardan
    yeni olamaz, alt sınır). En yenisi alınır. Barlar yalnız işlem günlerinde
    oluştuğu için hafta sonu/tatil güvenlidir. Gelecek tarihli (bozuk) değer
    yok sayılır. Veri yoksa None — çağıran "bugün"e düşmemeli.
    """
    ref = today if today is not None else _today_tr()
    if isinstance(ref, datetime):
        ref = ref.date()
    best = None
    for s in stocks or ():
        if not isinstance(s, dict):
            continue
        d = parse_signal_date(s.get("bar_date")) or parse_signal_date(s.get("signal_date"))
        if d is not None and d <= ref and (best is None or d > best):
            best = d
    return best


def derive_signal_date_label(signal_date, today=None):
    """Kanonik görünen tarih etiketi: her yaşta "23 Eylül" (yıl yalnız içinde
    bulunulan yıldan farklıysa eklenir: "31 Aralık 2025").

    Tarih ayrıştırılamazsa None döner; çağıran nötr bir şey basmalı.
    static/bp-format.js:bpSignalDateLabel() ile birebir aynı.
    """
    if signal_date_age_days(signal_date, today) is None:
        return None
    sd = parse_signal_date(signal_date)
    ref = today if today is not None else _today_tr()
    if isinstance(ref, datetime):
        ref = ref.date()
    label = f"{sd.day} {TR_MONTHS[sd.month - 1]}"
    return label if ref.year == sd.year else f"{label} {sd.year}"


def derive_signal_date_key(signal_date, today=None):
    """Rozet/renk sınıfı için ayrık anahtar: today / yesterday / older / unknown.

    static/bp-format.js:bpSignalDateKey() ile birebir aynı.
    """
    age = signal_date_age_days(signal_date, today)
    if age is None:
        return "unknown"
    if age == 0:
        return "today"
    if age == 1:
        return "yesterday"
    return "older"
