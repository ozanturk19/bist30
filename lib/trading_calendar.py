"""
BIST işlem günü / seans takvimi — tek kanonik kaynak (CPO-1195 §2).

app.py (is_trading_day/_market_open) ve tools/restart-bist30-refresh-conditional.sh
İKİSİ DE buradan okur. Yan etkisiz, saf fonksiyonlar — import thread/IO
tetiklemez, hem app.py'nin ağır import zincirine hem de standalone
shell-script kullanımına güvenli.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

_TZ_TR = ZoneInfo("Europe/Istanbul")

# CPO-1508/1512: EOD-only cadence + freshness eşiği bu iki sabitten türetilir —
# "18:30 TR" gibi bir eşik ikinci bir yerde ayrıca hardcode EDİLMEMELİ, aşağıdaki
# fonksiyonlardan (is_closing_snapshot_window / eod_data_ready_after /
# is_after_market_close) türetilmeli. Kapanış penceresi tekrar ayarlanırsa
# (CPO-1485'te bir kez oldu) tek sabit güncellenir, kayma riski taşımaz.
_CLOSING_WINDOW_HOUR        = 18  # BIST kapanışı (seans 10:00-18:00 TR)
_CLOSING_WINDOW_END_MINUTE  = 20  # kapanış-sonrası final snapshot penceresi biter (18:20 TR)
_EOD_READY_BUFFER_MINUTES   = 10  # pencere bitişine ek tampon (Yahoo settle gecikmesi/retry payı)

try:
    import holidays as _holidays_lib
    _tr_holidays = _holidays_lib.Turkey()
except Exception:
    _tr_holidays = None


def is_trading_day(d=None):
    """BIST işlem günü mü? Hafta sonu (Cmt/Pzr) veya TR resmi tatil → False."""
    d = d or datetime.now(_TZ_TR).date()
    if d.weekday() >= 5:
        return False
    if _tr_holidays is not None and d in _tr_holidays:
        return False
    return True


def market_open(now_tr=None):
    """BIST seansı açık mı? Hafta içi 10:00-18:00 TR + işlem günü."""
    now_tr = now_tr or datetime.now(_TZ_TR)
    if not is_trading_day(now_tr.date()):
        return False
    return 10 <= now_tr.hour < 18


def is_closing_snapshot_window(now_tr=None):
    """CPO-1485: kapanış sonrası (18:00-18:20 TR) TEK bir 'final closing snapshot'
    penceresi mi? Bu pencerede refresh_data() normal 180s soft-cap yerine daha
    cömert bir bütçe kullanmalı — kapanış auction'ının/Yahoo'nun settled fiyatı
    yansıtması için birkaç dakika daha gerekebiliyor (bkz. CPO-1485 kök neden:
    18:05 TR başlayan tur 180s'de 131/215 hisseyi bitirebildi, servis 18:17 TR'de
    durunca kalan tur hiç denenemedi)."""
    now_tr = now_tr or datetime.now(_TZ_TR)
    if not is_trading_day(now_tr.date()):
        return False
    return now_tr.hour == _CLOSING_WINDOW_HOUR and now_tr.minute <= _CLOSING_WINDOW_END_MINUTE


def is_after_market_close(now_tr=None):
    """CPO-1508 Faz 0: EOD-only cadence tetikleyicisi — işlem günü VE kapanış
    saatini (18:00 TR) geçti mi? background_refresh() günde-bir-kez ana refresh'i
    bu pencereden itibaren (18:00-18:20 asıl deneme + sonrası catch-up) çalıştırır.
    _CLOSING_WINDOW_HOUR'ı is_closing_snapshot_window ile paylaşır — iki sabit
    birbirinden bağımsız kaymasın diye."""
    now_tr = now_tr or datetime.now(_TZ_TR)
    if not is_trading_day(now_tr.date()):
        return False
    return now_tr.hour >= _CLOSING_WINDOW_HOUR


def eod_data_ready_after(now_tr=None):
    """CPO-1512: bugünün EOD verisinin hazır OLMASI beklenen an (18:20 pencere
    bitişi + 10dk tampon = 18:30 TR) — ikinci bir yerde ayrıca hardcode edilmez,
    is_closing_snapshot_window ile aynı sabitlerden türetilir."""
    now_tr = now_tr or datetime.now(_TZ_TR)
    if not is_trading_day(now_tr.date()):
        return False
    _ready_total_min = (_CLOSING_WINDOW_HOUR * 60 + _CLOSING_WINDOW_END_MINUTE
                         + _EOD_READY_BUFFER_MINUTES)
    _now_total_min = now_tr.hour * 60 + now_tr.minute
    return _now_total_min >= _ready_total_min


def last_trading_day_on_or_before(d):
    """d dahil, geriye doğru en yakın işlem günü (hafta sonu/tatil atlanır)."""
    while not is_trading_day(d):
        d -= timedelta(days=1)
    return d


def expected_data_date(now_tr=None):
    """CPO-1512 onaylı tasarım: şu an itibarıyla veri hangi işlem gününe ait
    OLMALI (trading-day-bazlı, saat-bazlı DEĞİL)? Basit 'age > sabit_saat' eşiği
    hafta sonu kenarında kırılıyordu (Cuma kapanışı Pazartesi 10:00'da hâlâ
    ~64 saat yaşında ama GEÇERLİ) — bu fonksiyon onun yerine geçer.

    - İşlem günü VE bugünün EOD verisi henüz hazır değilse (eod_data_ready_after
      False) → beklenen tarih BİR ÖNCEKİ işlem günü.
    - Aksi halde (bugünün EOD'u hazır, veya bugün işlem günü değil/hafta sonu)
      → en yakın (geriye doğru) işlem günü.
    """
    now_tr = now_tr or datetime.now(_TZ_TR)
    today = now_tr.date()
    if is_trading_day(today) and not eod_data_ready_after(now_tr):
        return last_trading_day_on_or_before(today - timedelta(days=1))
    return last_trading_day_on_or_before(today)


if __name__ == "__main__":
    # CLI kullanım: tools/restart-bist30-refresh-conditional.sh buradan okur.
    print("1" if market_open() else "0")
