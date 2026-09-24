"""D-46b — şirket adı/açıklaması KAP'tan; Gemini şirket özeti yok."""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KAP = json.load(open(os.path.join(ROOT, "kap_sirket_bilgileri.json"), encoding="utf-8"))
PY310 = pytest.mark.skipif(sys.version_info < (3, 10), reason="app.py 3.10+ ister")


def test_kap_file_shape():
    assert len(KAP) >= 215
    for t, k in KAP.items():
        assert k["unvan"] and k["kisa_ad"], t
        f = k.get("faaliyet_konusu")
        assert f is None or 8 <= len(f) <= 420, t


def test_fetch_tool_parser():
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import fetch_kap_faaliyet as ff
    page = ('..."itemKey":"kpy41_acc2_faaliyet_konu","value":"\\u003cp\\u003e\\u003cspan style=\\\\"a: b\\\\"\\u003e'
            'Yolcu ve kargo ta\\u015f\\u0131mac\\u0131l\\u0131\\u011f\\u0131\\u003c/span\\u003e\\u003c/p\\u003e",'
            '"disclosureIndex":1,"creationDate":"14/07/2016 14:41:13"}')
    m = ff._RE.search(page.replace('\\"', '"'))
    assert ff._clean(m.group(1)) == "Yolcu ve kargo taşımacılığı"
    assert ff._is_sector_chain("ULAŞTIRMA VE DEPOLAMA / ULAŞTIRMA / HAVA TAŞIMACILIĞI")
    text, note = ff._trim("Bir; " * 200)
    assert len(text) <= ff.MAX_LEN and text.endswith("…") and note == "kısaltıldı"


@PY310
def test_names_from_kap_and_summary_without_gemini():
    sys.path.insert(0, ROOT)
    import app
    for t, k in KAP.items():
        if t in app.BIST100:
            assert app.STOCK_NAMES[t] == k["kisa_ad"], t
    assert app.STOCK_NAMES["SMART"] == "Smartiks Yazılım"
    enery = app.get_company_summary("ENERY")
    assert enery and "— KAP faaliyet konusu:" in enery and "gaz" in enery.lower()
    assert app.get_company_summary("YOKBOYLEBIR") is None
    assert not hasattr(app, "_generate_company_summary")
    nof = [t for t, k in KAP.items() if not k.get("faaliyet_konusu")]
    for t in nof:
        assert app.get_company_summary(t) is None
