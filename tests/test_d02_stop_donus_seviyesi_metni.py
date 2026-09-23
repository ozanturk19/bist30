"""D-02 (23.09) — "stop bölgesi" yalnız AL sinyalinde; RSI 45-60 "ideal giriş"
yalnız AL'de; RYSAS unvanı; bozuk cümle; SSS "prim potansiyeli" (O8) kalktı.
Statik (yerel Mac python 3.9'da app import edilemez); davranış testi
yalnız python>=3.10'da (VPS venv) koşar."""
import os
import sys

import pytest

_APP_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


def _src():
    with open(_APP_PY, encoding="utf-8") as f:
        return f.read()


def test_statik_metinler():
    s = _src()
    assert '"RYSAS": "Reysaş Taşımacılık ve Lojistik"' in s
    assert "Supertrend ve EMA düşen ancak" not in s
    assert "prim potansiyeli nedir" not in s
    assert "teknik görünümü nasıl?" in s
    assert "R/R oranı 1:" not in s


@pytest.mark.skipif(sys.version_info < (3, 10), reason="app.py python>=3.10 ister")
def test_stop_bolgesi_yalniz_al():
    import app
    base = {"price": 100.0, "signal_price": 90.0, "signal_bars": 3, "rsi": 50, "adx": 25,
            "sl_level": 105.0}
    for sig in ("SAT", "BEKLE"):
        out = app.build_signal_summary(dict(base, signal=sig))
        blob = " ".join(p["text"] + " " + p["tip"] for p in out["points"]) + out["verdict"]
        assert "stop bölgesi" not in blob.lower()
        assert "ideal giriş" not in blob.lower()
        assert "Trend dönüş seviyesi (Supertrend)" in blob
        assert "fiyatın %5,0 üstünde" in blob
    # CPO-1793: AL'de de "stop bölgesi" yok; tek dil "Trend dönüş seviyesi (Supertrend)"
    out = app.build_signal_summary(dict(base, signal="AL", sl_level=95.0))
    assert "stop bölgesi" not in out["points"][-1]["text"].lower()
    assert "Trend dönüş seviyesi (Supertrend)" in out["points"][-1]["text"]
    assert "ideal giriş" not in out["points"][-1]["tip"].lower()
