"""CPO-1119 §2 — _compute_data_quality() sınır fixture'ı.

SENECA `stale` dalını canlıda doğrulayamadı (bugünkü oran %94, %15-50 bandına
düşmüyor) — bu dal kanıtsız kod olarak işaretlendi. Bu test canlıyı beklemeden
`ok`/`stale`/`critical` sınırlarını ve eşik kenarlarını sentetik fixture ile
doğrular.

CPO-1121 düzeltmesi: 216 tabanında 0.15 kenarı tam sayıya denk gelmiyor
(32/216=0.1481, 33/216=0.1528 — ikisi de ratio==0.15'e değmiyor, yani `>` ile
yanlışlıkla yazılmış bir `>=` bu fixture'la yakalanmazdı). 0.15 kenarı için
total=200 kullanılır (200*0.15=30 tam sayı); 0.50 kenarı 216 tabanında zaten
tam sayı (108) olduğu için değiştirilmedi.

Python 3.9 (yerel Mac) app.py'yi (3.10+ sözdizimi) import edemiyor — fonksiyon
saf/bağımsız olduğu için kaynaktan çıkarılıp izole exec edilir.
"""
import os
import re

import pytest

_APP_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


def _load_compute_data_quality():
    with open(_APP_PY, encoding="utf-8") as f:
        src = f.read()
    m = re.search(r"def _compute_data_quality\(.*?\n\n\n", src, re.DOTALL)
    assert m, "_compute_data_quality() app.py'de bulunamadı — fonksiyon adı/imzası değişmiş olabilir"
    ns = {}
    exec(m.group(0), ns)
    return ns["_compute_data_quality"]


_compute_data_quality = _load_compute_data_quality()


@pytest.mark.parametrize(
    "bad,total,market_open,expected",
    [
        (0,   216, True,  "fresh"),     # ratio=0.00
        (22,  216, True,  "fresh"),     # ratio=0.10
        (30,  200, True,  "fresh"),     # ratio=0.15  tam sınır (200 tabanı) — eşiği KAPSIYOR, fresh kalmalı (strict >)
        (31,  200, True,  "stale"),     # ratio=0.155 sınırın hemen üstü
        (65,  216, True,  "stale"),     # ratio=0.30
        (108, 216, True,  "stale"),     # ratio=0.50  tam sınır — critical DEĞİL (strict >)
        (109, 216, True,  "critical"),  # ratio=0.501 sınırın hemen üstü
        (205, 216, True,  "critical"),  # ratio=0.95
        (999, 216, False, "fresh"),     # market_open=False → her zaman fresh (seans dışı by-design)
        (0,   0,   True,  "critical"),  # total_count=0 → critical (sıfıra bölme guard'ı)
    ],
)
def test_data_quality_boundaries(bad, total, market_open, expected):
    assert _compute_data_quality(bad, total, market_open) == expected
