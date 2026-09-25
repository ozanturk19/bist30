"""D-40a1: KAP uretim araci -- cok-oid toplu liste, 429 ustel bekleme, BIST100 once, taze atlama.

Ag yok: requests.Session sahte, sleep/clock enjekte. app.py'yi import etmez.
"""
import json
import os
import sys
from datetime import date

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import build_kap_financials as bk  # noqa: E402

TODAY = date(2026, 9, 25)


class Resp:
    def __init__(self, code=200, body=None):
        self.status_code = code
        self._b = body

    def json(self):
        return self._b

    text = ""


class FakeSession:
    def __init__(self, script):
        self.script = list(script)   # callable(kw) -> Resp | Resp
        self.calls = []
        self.headers = {}

    def request(self, method, url, timeout=None, **kw):
        self.calls.append((method, url, kw))
        nxt = self.script.pop(0)
        return nxt(kw) if callable(nxt) else nxt


def _kap(script):
    sleeps = []
    clock = [1000.0]
    k = bk.Kap(sleep=lambda s: (sleeps.append(s), clock.__setitem__(0, clock[0] + s)), clock=lambda: clock[0])
    k.s = FakeSession(script)
    return k, sleeps


def test_429_ustel_bekleme_15_30_60_sabit_ve_ayni_istek_yeniden_denenir():
    ok = Resp(200, [])
    k, sleeps = _kap([Resp(429), Resp(429), Resp(429), Resp(429), ok])
    k.disclosures("oidA", "2026-01-01", "2026-09-25", "FR")
    waits = [s for s in sleeps if s >= 600]
    assert waits == [15 * 60, 30 * 60, 60 * 60, 60 * 60]
    assert len(k.s.calls) == 5


def test_429_ust_uste_altiyi_asarsa_kapstop():
    k, _ = _kap([Resp(429)] * 7)
    with pytest.raises(bk.KapStop):
        k.disclosures("oidA", "2026-01-01", "2026-09-25", "FR")


def test_liste_istekleri_arasi_en_az_3_sn():
    k, sleeps = _kap([Resp(200, []), Resp(200, [])])
    k.disclosures("a", "2026-01-01", "2026-09-25", "FR")
    k.disclosures("a", "2026-01-01", "2026-09-25", "FR")
    assert any(abs(s - 3.0) < 1e-6 for s in sleeps)


def test_5xx_uc_deneme_sonra_valueerror():
    k, _ = _kap([Resp(500)] * 5)
    with pytest.raises(ValueError):
        k.disclosures("a", "2026-01-01", "2026-09-25", "FR")


def _fr(code, idx):
    return {"stockCodes": code, "subject": "Finansal Rapor", "disclosureIndex": idx}


def test_toplu_sonuc_stockcodes_ile_dagitilir_ve_bos_sirket_yazilmaz(tmp_path, monkeypatch):
    monkeypatch.setattr(bk, "LISTS", str(tmp_path))
    items = [_fr("AAA", 1), _fr("BBB", 2), _fr("AAA", 3),
             {"stockCodes": "AAA", "subject": "Faaliyet Raporu", "disclosureIndex": 9},
             {"stockCodes": None, "subject": "Finansal Rapor", "disclosureIndex": 8},
             {"stockCodes": None, "relatedStocks": "BBB", "subject": "Finansal Rapor", "disclosureIndex": 7}]
    k, _ = _kap([Resp(200, items)])
    oid_of = {"AAA": "o1", "BBB": "o2", "CCC": "o3"}
    bk.fetch_group(k, ["AAA", "BBB", "CCC"], oid_of, "FR", "2026-01-01", "2026-09-25")
    assert len(k.s.calls) == 1
    assert k.s.calls[0][2]["json"]["mkkMemberOidList"] == ["o1", "o2", "o3"]
    a = bk.read_list_cache("AAA", "FR", "2026-01-01", "2026-09-25")
    assert [x["disclosureIndex"] for x in a] == [1, 3]            # yalniz Finansal Rapor
    assert [x["disclosureIndex"] for x in bk.read_list_cache("BBB", "FR", "2026-01-01", "2026-09-25")] == [2, 7]      # 7: relatedStocks (KAP'in sirket adina yayini, stockCodes null)
    assert bk.read_list_cache("CCC", "FR", "2026-01-01", "2026-09-25") is None   # tek sorguyla dogrulanacak


def test_liste_capine_dayanan_grup_ikiye_bolunur(tmp_path, monkeypatch):
    monkeypatch.setattr(bk, "LISTS", str(tmp_path))
    monkeypatch.setattr(bk, "LIST_CAP", 4)
    tks = ["A1", "A2", "A3", "A4"]
    full = [_fr("A1", i) for i in range(4)]                       # cap'e dayandi -> kesilmis sayilir
    half1 = [_fr("A1", 1), _fr("A2", 2)]
    half2 = [_fr("A3", 3), _fr("A4", 4)]
    k, _ = _kap([Resp(200, full), Resp(200, half1), Resp(200, half2)])
    bk.fetch_group(k, tks, {t: "o" + t for t in tks}, "FR", "2025-01-01", "2025-12-31")
    assert [c[2]["json"]["mkkMemberOidList"] for c in k.s.calls] == [["oA1", "oA2", "oA3", "oA4"], ["oA1", "oA2"], ["oA3", "oA4"]]
    for t in tks:
        assert bk.read_list_cache(t, "FR", "2025-01-01", "2025-12-31")


def test_prefetch_yalniz_eksik_pencereleri_ceker(tmp_path, monkeypatch):
    monkeypatch.setattr(bk, "LISTS", str(tmp_path))
    monkeypatch.setattr(bk, "LIST_BATCH", {"FR": 2, "ODA": 2})
    comps = {t: {"mkk": "o" + t} for t in ("A", "B", "C")}
    # A'nin tum FR pencereleri onbellekte: yalniz B, C gerekir
    for frm, to in bk.windows(bk.YEARS, TODAY):
        bk.write_json(bk._list_path("A", "FR", frm), {"to": to, "items": []})

    def answer(kw):
        oids = kw["json"]["mkkMemberOidList"]
        return Resp(200, [_fr(o[1:], 1) for o in oids])
    k, _ = _kap([answer] * 40)
    n, wrote = bk.prefetch_lists(k, ["A", "B", "C"], comps, TODAY)
    fr_calls = [c for c in k.s.calls if c[2]["json"]["disclosureClass"] == "FR"]
    assert len(fr_calls) == bk.YEARS                     # B+C tek grup x 5 yil
    assert all(c[2]["json"]["mkkMemberOidList"] == ["oB", "oC"] for c in fr_calls)
    assert n == len(k.s.calls) and wrote > 0


def test_kapanmis_yil_onbellegi_kalici_acik_yil_yalniz_ayni_gun(tmp_path, monkeypatch):
    monkeypatch.setattr(bk, "LISTS", str(tmp_path))
    bk.write_json(bk._list_path("A", "FR", "2025-01-01"), {"to": "2025-12-31", "items": [1]})
    bk.write_json(bk._list_path("A", "FR", "2026-01-01"), {"to": "2026-09-24", "items": [2]})
    assert bk.read_list_cache("A", "FR", "2025-01-01", "2025-12-31") == [1]
    assert bk.read_list_cache("A", "FR", "2026-01-01", "2026-09-25") is None   # dunku acik pencere bayat


def test_bist100_once_sonra_alfabetik():
    comps = {"ZZZ": {"indices": ["XU100"]}, "AAA": {"indices": ["XUTUM"]}, "MMM": {"indices": ["XU030", "XU100"]},
             "BBB": {}}
    assert bk.order_universe(["AAA", "BBB", "MMM", "ZZZ"], comps) == ["MMM", "ZZZ", "AAA", "BBB"]


def test_taze_hisse_dosyasi_atlanir_eski_atlanmaz(tmp_path, monkeypatch):
    monkeypatch.setattr(bk, "OUT", str(tmp_path))
    rec = {"derived": {"basis": "tms29"}}
    p = tmp_path / "AAA.json"
    p.write_text(json.dumps(rec))
    now = os.path.getmtime(str(p))
    assert bk.fresh_record("AAA", now=now + 3600) == rec
    assert bk.fresh_record("AAA", now=now + 13 * 3600) is None
    assert bk.fresh_record("YOK", now=now) is None
