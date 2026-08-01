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


if __name__ == "__main__":
    # CLI kullanım: tools/restart-bist30-refresh-conditional.sh buradan okur.
    print("1" if market_open() else "0")
