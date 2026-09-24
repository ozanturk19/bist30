"""D-46 — evren dosyası (KAP) ve BIST30_LITERAL'in dosyadan türemesi."""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import build_universe as bu  # noqa: E402


def test_parse_indices_and_sectors():
    text = ('..."code":"XU030","content":[{"stockCode":"THYAO","title":"T","mkkMemberOid":"x"}]...'
            '{"sectorName":"ULAŞTIRMA","sectorOid":"1","stockCode":"THYAO","title":"T"}'
            '{"mainSectorName":"ULAŞTIRMA VE DEPOLAMA","stockCode":"THYAO","title":"T"}')
    assert bu.parse_indices(text)["XU030"][0][0] == "THYAO"
    sec, main = bu.parse_sectors(text)
    assert sec["THYAO"] == "ULAŞTIRMA" and main["THYAO"] == "ULAŞTIRMA VE DEPOLAMA"


def test_seed_file_shape():
    u = json.load(open(os.path.join(ROOT, "universe_seed.json"), encoding="utf-8"))
    assert len(u["indices"]["XU030"]) == 30 and len(u["indices"]["XU100"]) == 100
    assert len(u["indices"]["XUTUM"]) >= 450
    assert u["names_override"]["TUREX"] == "Tureks Turizm"


@pytest.mark.skipif(sys.version_info < (3, 10), reason="app.py 3.10+ ister")
def test_bist30_literal_from_universe_and_not_slice():
    sys.path.insert(0, ROOT)
    import app
    xu030 = set(app.UNIVERSE["indices"]["XU030"])
    assert set(app.BIST30_LITERAL) == xu030 and len(app.BIST30_LITERAL) == 30
    assert app.STOCK_NAMES["TUREX"] == "Tureks Turizm"
