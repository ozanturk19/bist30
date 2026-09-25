"""D-07 — /api/data model alanları: data_completeness, bps_partial, sayısal DI+/DI-.

Python 3.9 app.py'yi import edemez: kaynak AST/regex ile taranır; DI etiket
ayrıştırması aynı kalıpla izole doğrulanır.
"""
import os
import re

_APP_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
with open(_APP_PY, encoding="utf-8") as _f:
    _SRC = _f.read()


def test_analyze_uretir_sayisal_di():
    assert '"di_plus":       round(di_p, 1),' in _SRC
    assert '"di_minus":      round(di_m, 1),' in _SRC


def test_api_data_model_alanlari():
    i = _SRC.index('def api_data():')
    body = _SRC[i:i + 6000]
    assert 's["data_completeness"] = _hs_data.get("data_completeness") if _hs_data else None' in body
    assert 's["bps_partial"]       = _hs_data.get("partial") if _hs_data else None' in body


def test_eski_cache_di_etiketten():
    m = re.search(r'_dm = re\.match\(r"(.+?)", _dv\)', _SRC)
    assert m, "DI etiket ayrıştırıcısı bulunamadı"
    pat = m.group(1)
    g = re.match(pat, "DI+27/DI-15")
    assert g and (float(g.group(1)), float(g.group(2))) == (27.0, 15.0)
    g = re.match(pat, "DI+27.5/DI-15.2")
    assert g and (float(g.group(1)), float(g.group(2))) == (27.5, 15.2)
    assert re.match(pat, "ADX 30") is None
