"""CPO-1818 (C-74 K10 kalanı, 03.10): hisse SSS "Teknik Güç Skoru N/100" kalkar;
/humans.txt "ücretsiz"/"algoritmik" yasak kelimeleri kalkar.
Statik (yerel Mac python 3.9'da app import edilemez); davranış testi
yalnız python>=3.10'da (VPS venv) koşar.
"""
import os
import re
import sys

import pytest

_APP_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
PY310 = pytest.mark.skipif(sys.version_info < (3, 10), reason="app.py python>=3.10 ister")


def _src():
    with open(_APP_PY, encoding="utf-8") as f:
        return f.read()


def test_statik_metinler():
    s = _src()
    assert '"Teknik Güç Skoru {score}/100"' not in s
    assert "ücretsiz, algoritmik" not in s
    assert "Algoritmik teknik analiz" not in s


@PY310
def test_humans_txt_canli():
    import app
    body = app.app.test_client().get("/humans.txt").get_data(as_text=True)
    assert not re.search(r"(?i)ücretsiz|algoritmik", body)


@PY310
def test_hisse_sss_teknik_guc_skoru_yok():
    import app
    body = app.app.test_client().get("/hisse/THYAO").get_data(as_text=True)
    assert "Teknik Güç Skoru" not in body
