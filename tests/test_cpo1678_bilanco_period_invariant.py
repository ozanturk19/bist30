"""CPO-1678 — `_BILANCO_PERIODS` kalıcı lag invariant testi.

Kök neden (20.09.2026): tablo elle giriliyor ve Q2/Q3 2026 satırları
sayfanın kendi info-banner'ıyla ("çeyrek bitiminden 3-7 hafta içinde KAP'a
bildirir", templates/bilanco_takvimi.html:44) çelişen bir `pencere_baslangici`
kullanıyordu (Q2: 9 gün, Q3: 1 gün lag — banner 21-49 gün diyor). CPO
onayıyla Q1/Q4-yıllık emsaline (39 gün) hizalandı.

Bu test, tablo bir sonraki yıl için elle genişletilirken aynı hata sınıfının
sessizce geri dönmesini engeller: her satırın `pencere_baslangici`sı, o
dönemin takvim bitişine göre 21-70 gün içinde olmalı. app.py Python 3.9
(yerel Mac) altında import edilemediği için (3.10+ sözdizimi kullanıyor,
bkz. test_cpo1587_tarama_ssr.py) `_BILANCO_PERIODS` listesi kaynaktan
regex+ast.literal_eval ile izole okunur — tam app.py import'una gerek yok.
"""
import ast
import os
import re
from datetime import date, timedelta

_APP_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")

with open(_APP_PY, encoding="utf-8") as _f:
    _SRC = _f.read()

_MIN_LAG_DAYS = 21
_MAX_LAG_DAYS = 70

# CPO-1678: yıllık/denetimli (Q4) raporlar çeyreklik olanlardan daha uzun
# sürebilir; üst sınırı genel banttan ayrı tutmak gerekirse etiketi buraya
# ekle. Şu an tüm satırlar (yıllık dahil, 60 gün lag) genel bandın (21-70)
# içinde kaldığı için boş.
_WIDER_UPPER_BOUND_LABELS = {}  # {"Q4 2026 (Yıllık)": 100, ...}


def _load_periods():
    m = re.search(r"_BILANCO_PERIODS\s*=\s*(\[.*?\n\])", _SRC, re.DOTALL)
    assert m, "_BILANCO_PERIODS literali bulunamadi / regex sinir guncellenmeli"
    return ast.literal_eval(m.group(1))


def _quarter_end_date(label: str) -> date:
    """'Q1 2026' / 'Q2 2026 (H1)' / 'Q4 2025 (Yıllık)' -> o dönemin (H1 için
    yarıyılın, Yıllık için mali yılın) takvim bitiş tarihi."""
    m = re.match(r"Q(\d) (\d{4})", label)
    assert m, f"beklenmeyen donem etiketi: {label!r}"
    q, year = int(m.group(1)), int(m.group(2))
    end_month = q * 3
    if end_month == 12:
        return date(year, 12, 31)
    return date(year, end_month + 1, 1) - timedelta(days=1)


def test_bilanco_periods_window_start_within_kap_lag_bounds():
    periods = _load_periods()
    assert periods, "_BILANCO_PERIODS bos olamaz"

    for qlabel, start_str, _end_str, _desc in periods:
        quarter_end = _quarter_end_date(qlabel)
        window_start = date.fromisoformat(start_str)
        lag_days = (window_start - quarter_end).days
        max_bound = _WIDER_UPPER_BOUND_LABELS.get(qlabel, _MAX_LAG_DAYS)

        assert lag_days >= _MIN_LAG_DAYS, (
            f"{qlabel}: pencere_baslangici ({start_str}) ceyrek/yil bitisinden "
            f"({quarter_end.isoformat()}) sadece {lag_days} gun sonra — alt sinir "
            f"{_MIN_LAG_DAYS} gun ihlal edildi (bkz. /bilanco-takvimi banner'i: "
            f"'3-7 hafta', CPO-1678)"
        )
        assert lag_days <= max_bound, (
            f"{qlabel}: pencere_baslangici ({start_str}) ceyrek/yil bitisinden "
            f"({quarter_end.isoformat()}) {lag_days} gun sonra — ust sinir {max_bound} "
            f"gun ihlal edildi (bkz. /bilanco-takvimi banner'i: '3-7 hafta', CPO-1678)"
        )
