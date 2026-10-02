"""Ortak test yardımcıları (D-09).

- Depo kökü sys.path'te: testler üretim modüllerini doğrudan import eder
  (business_rules, financial_health_score, _alerts, _guards, _health_extras).
  tools/ altındaki aynı adlı kopyalar D-09'da silindi; gölgeleme riski yok.
- `app_module`: app.py Python 3.10+ ister (PEP 604). Yerel Mac'te (3.9) test
  atlanır, VPS venv'de (3.12) koşar — 93d01dc deseninin fixture hali.
- `app_source` / `app_function`: app.py'yi import etmeden statik kaynak testleri.
- `stock_pool`: temel skor testleri için sektör havuzu kurucu.
"""
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


@pytest.fixture
def app_module():
    """app.py modülü; Python < 3.10'da testi atlar (yerel), VPS'te koşar."""
    if sys.version_info < (3, 10):
        pytest.skip("app.py 3.10+ ister — VPS venv'de çalıştır")
    import app
    return app


@pytest.fixture(scope="session")
def app_source():
    with open(os.path.join(ROOT, "app.py"), encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="session")
def app_function(app_source):
    """app_function("analyze") → üst düzey fonksiyonun kaynak metni (yoksa None)."""
    def _get(name):
        m = re.search(rf"\ndef {name}\(.*?(?=\ndef |\Z)", app_source, re.S)
        return m.group(0) if m else None
    return _get


@pytest.fixture
def stock_pool():
    """stock_pool(sektor, [{metrik: değer}, ...], ticker_prefix) → fundamentals listesi.

    Her satıra ticker + sector eklenir (compute_health_score'un beklediği biçim).
    """
    def _make(sector, rows, prefix="T"):
        out = []
        for i, row in enumerate(rows):
            d = {"ticker": row.get("ticker") or f"{prefix}{i}", "sector": sector}
            d.update({k: v for k, v in row.items() if k != "ticker"})
            out.append(d)
        return out
    return _make
