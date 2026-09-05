"""
BIST işlem günü / seans takvimi — tek kanonik kaynak (CPO-1195 §2).

app.py (is_trading_day/_market_open) ve tools/restart-bist30-refresh-conditional.sh
İKİSİ DE buradan okur. Yan etkisiz, saf fonksiyonlar — import thread/IO
tetiklemez, hem app.py'nin ağır import zincirine hem de standalone
shell-script kullanımına güvenli.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

_TZ_TR = ZoneInfo("Europe/Istanbul")

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
    return now_tr.hour == 18 and now_tr.minute <= 20


if __name__ == "__main__":
    # CLI kullanım: tools/restart-bist30-refresh-conditional.sh buradan okur.
    print("1" if market_open() else "0")
