"""D-24: /api/takvim saf cekirdegi (takvim.py). app.py import edilmez (yerel py3.9'da da kosar).

Fixture: tests/fixtures/takvim/kap_fin_ornek.json -- D-40a0 kayit bicimi; temettuler
24.09.2026'da cekilmis 12 gercek kar payi bildiriminden (kap_financials ayristiricisi).
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import takvim as tk  # noqa: E402

FIX = os.path.join(ROOT, "tests", "fixtures", "takvim", "kap_fin_ornek.json")
TODAY = date(2026, 9, 24)
NAMES = {"TUPRS": "Tüpraş", "THYAO": "Türk Hava Yolları", "GARAN": "Garanti BBVA", "EREGL": "Erdemir"}
# 24.09.2026 kapanislari (canli /api/data, 19:11)
PRICES = {"TUPRS": 410.75, "LKMNH": 12.18, "TCELL": 100.6, "BIMAS": 434.75}


def _recs():
    with open(FIX, encoding="utf-8") as f:
        return json.load(f)["records"]


def _universe(recs):
    return sorted(set(recs) | {"AKBNK", "ADEL", "EREGL"})


def _build(recs=None, estimates=None, today=TODAY):
    recs = _recs() if recs is None else recs
    return tk.build(_universe(recs), NAMES, recs, estimates or {}, PRICES, today,
                    fiyat_tarihi="2026-09-24", updated_at="24.09.2026 19:40")


def _ev(p, kind, ticker=None, date_=None):
    return [e for e in p["events"] if e["kind"] == kind and (ticker is None or e.get("ticker") == ticker)
            and (date_ is None or e["date"] == date_)]


def test_temettu_siradaki_odeme_ve_verim():
    p = _build()
    tu = _ev(p, "temettu", "TUPRS")
    assert len(tu) == 1, tu  # 16.03 odemesi gecmiste; yalniz 30.09 taksiti
    e = tu[0]
    assert (e["date"], e["ex_date"], e["pay_date"]) == ("2026-09-30", "2026-09-30", "2026-10-02")
    assert e["brut_tl"] == 6.7469533 and e["taksit"] == "2/2" and e["date_kind"] == "kesin"
    assert e["yield_pct"] == round(6.7469533 / 410.75 * 100, 2) == 1.64
    assert _ev(p, "temettu", "EREGL") == []  # 15.12 yalniz "en gec baslama"; tarihli odeme yok


def test_temettu_kapsam_bist30_disi():
    p = _build()
    have = {(e["ticker"], e["date"]) for e in _ev(p, "temettu")}
    for need in [("LKMNH", "2026-09-28"), ("MEDTR", "2026-10-27"), ("MEDTR", "2026-12-28"),
                 ("GOKNR", "2026-11-09"), ("NTHOL", "2026-12-16"), ("TCELL", "2026-12-09"),
                 ("BIMAS", "2026-12-16"), ("ASTOR", "2026-10-15"), ("TRALT", "2026-10-06"),
                 ("AEFES", "2026-10-05"), ("ASELS", "2026-11-24")]:
        assert need in have, need
    medtr = {e["date"]: e["taksit"] for e in _ev(p, "temettu", "MEDTR")}
    assert medtr == {"2026-10-27": "2/3", "2026-12-28": "3/3"}
    assert {e["taksit"] for e in _ev(p, "temettu", "GOKNR")} == {"2/4", "3/4", "4/4"}
    assert _ev(p, "temettu", "MEDTR")[0]["yield_pct"] is None  # fiyat yoksa verim uydurulmaz


def test_temettu_genel_kurul_oncesi_tahmini():
    recs = {"XYZ": {"schema_version": 1, "derived": {"temettu_odemeleri": [
        {"taksit": "Peşin", "brut": 1.0, "net": 0.85, "hak_kullanim": "2026-11-02", "odeme": "2026-11-04",
         "kaynak": {"rapor": 9, "donem": "2026-10-15"}}]}, "flags": {}}}
    e = tk.temettu_olaylari(recs, {}, {}, TODAY)[0]
    assert e["date_kind"] == "tahmini" and e["taksit"] == "tek"


def test_temettu_ozeti_24_ay_siniri():
    recs = {"OLD": {"schema_version": 1, "derived": {"temettu_odemeleri": [
        {"brut": 0.4, "hak_kullanim": "2023-06-01", "odeme": "2023-06-05", "kaynak": {"rapor": 1}},
        {"brut": 0.5, "hak_kullanim": "2025-06-01", "odeme": "2025-06-05", "kaynak": {"rapor": 2}}]}}}
    oz = tk.temettu_ozeti(recs, TODAY)
    assert oz["OLD"]["last"]["pay"] == "2025-06-05" and oz["OLD"]["next"] is None
    oz2 = tk.temettu_ozeti({"X": {"derived": {"temettu_odemeleri": [
        {"brut": 0.4, "hak_kullanim": "2023-06-01", "odeme": "2023-06-05", "kaynak": {"rapor": 1}}]}}}, TODAY)
    assert oz2 == {}
    tu = tk.temettu_ozeti(_recs(), TODAY)["TUPRS"]
    assert tu["next"]["brut"] == 6.7469533 and tu["last"]["brut"] == 10.3799282


def test_bilanco_aciklanan_rapor_ve_tahmini_tarih():
    recs = _recs()
    recs["AKBNK"] = {"schema_version": 1, "derived": {"son_rapor": {"donem": "2026/09", "yayin": "2026-09-22T18:30"}},
                     "flags": {"banka": True}}
    est = {"THYAO": "2026-11-05", "GARAN": "2026-10-28", "TUPRS": "2026-09-01", "AKBNK": "2026-10-27"}
    p = _build(recs, est)
    th = _ev(p, "bilanco", "THYAO")
    assert len(th) == 1 and th[0]["date_kind"] == "tahmini" and th[0]["donem"] == "2026/09"
    assert th[0]["son_rapor"] == {"donem": "2026/06", "date": "2026-08-05"}
    assert _ev(p, "bilanco", "GARAN")[0]["banka"] is True
    und = {u["ticker"]: u for u in p["undated"]}
    assert "TUPRS" in und and und["TUPRS"]["son_rapor"]["date"] == "2026-08-04"  # gecmis tahmin atildi
    assert "AKBNK" not in und and _ev(p, "bilanco", "AKBNK") == []  # donem aciklandi
    oz = p["bilanco_donemi"]
    assert oz["donem"] == "2026/09" and oz["aciklandi"] == 1 and oz["tahmini"] == 2
    assert oz["son_aciklananlar"][0] == {"ticker": "AKBNK", "name": "AKBNK", "date": "2026-09-22"}
    assert oz["tarihsiz"] == len(p["undated"])
    assert all(e["date_kind"] == "tahmini" for e in _ev(p, "bilanco") if e["sub"] == "rapor")


def test_bilanco_yasal_son_gunler():
    p = _build()
    sg = [e for e in _ev(p, "bilanco") if e["sub"] == "son_gun"]
    assert [e["date"] for e in sg] == ["2026-10-30", "2026-11-09", "2026-11-19"]
    assert all(e["date_kind"] == "kesin" and e["title"] == "9 aylık rapor için son gün" for e in sg)
    p2 = _build(today=date(2026, 11, 20))
    assert p2["bilanco_donemi"] is None and p2["undated"] == []


def test_makro_resmi_takvim():
    p = _build()
    m = _ev(p, "makro")
    assert len(m) == 15 and all(e["date"] >= "2026-09-24" for e in m)
    tufe = [e["date"] for e in m if e["region"] == "TR" and e["title"] == "Enflasyon (TÜFE)"]
    assert tufe == ["2026-10-05", "2026-11-03", "2026-12-03"]
    assert [e["date"] for e in m if e["title"] == "TCMB faiz kararı"] == ["2026-10-22", "2026-12-10"]
    assert [e["time"] for e in m if e["title"] == "Fed faiz kararı"] == ["21:00", "22:00"]  # yaz saati
    assert len(_ev(_build(today=date(2026, 12, 11)), "makro")) == 0


def test_siralama_sayac_ve_gunler():
    p = _build(estimates={"THYAO": "2026-11-05"})
    ds = [e["date"] for e in p["events"]]
    assert ds == sorted(ds) and ds[0] >= "2026-09-24"
    c = p["counts"]
    assert c["all"] == len(p["events"]) == c["temettu"] + c["bilanco"] + c["makro"]
    assert set(p["days"]) == {"2026-10-28", "2026-10-29"}
    d30 = [e["kind"] for e in p["events"] if e["date"] == "2026-09-30"]
    assert d30 == ["temettu", "makro"]
    assert p["kap_kayit"] == 14 and p["kapsam"] == len(_universe(_recs()))


def test_kayit_yoksa_bos_uydurma_yok():
    p = tk.build(["TUPRS", "THYAO"], NAMES, {}, {"THYAO": "2026-11-05"}, PRICES, TODAY)
    assert _ev(p, "temettu") == [] and p["kap_kayit"] == 0
    assert [e["ticker"] for e in _ev(p, "bilanco") if e["sub"] == "rapor"] == ["THYAO"]
    assert [u["ticker"] for u in p["undated"]] == ["TUPRS"]


def test_load_kap_records(tmp_path):
    (tmp_path / "AAA.json").write_text(json.dumps({"schema_version": 1, "derived": {}}), encoding="utf-8")
    (tmp_path / "BBB.json").write_text(json.dumps({"schema_version": 2, "derived": {}}), encoding="utf-8")
    (tmp_path / "CCC.json").write_text("{bozuk", encoding="utf-8")
    assert list(tk.load_kap_records(["AAA", "BBB", "CCC", "DDD"], base_dir=str(tmp_path))) == ["AAA"]


def test_donem_ozeti():
    it = tk.donem_ozeti(TODAY)
    assert len(it) == 1 and it[0]["status"] == "upcoming" and it[0]["days_label"] == "7 gün sonra"
    assert it[0]["end"] == "2026-11-19" and it[0]["label"] == "3. çeyrek raporları"
    assert tk.donem_ozeti(date(2026, 11, 1))[0]["days_label"] == "18 gün kaldı"
    assert tk.donem_ozeti(date(2026, 11, 20)) == []


def test_ssr_context():
    p = _build(estimates={"THYAO": "2026-11-05"})
    stocks = {"TUPRS": {"change_pct": -0.06, "borsapusula_skoru": 59, "signal": "BEKLE"},
              "THYAO": {"change_pct": 1.2, "borsapusula_skoru": 61, "signal": "AL"}}
    s = tk.ssr_context(p, stocks, TODAY)
    assert s["asof_label"] == "24 Eylül Perşembe"
    g = {x["date"]: x for x in s["groups"]}
    assert g["2026-10-29"]["events"] == [] and g["2026-10-29"]["not"]["not"] == "Borsa kapalı"
    assert g["2026-09-30"]["gun"] == "30 Eylül" and g["2026-09-30"]["hafta_gunu"] == "Çarşamba"
    tu = g["2026-09-30"]["events"][0]
    assert tu["hisse"] == {"change_pct": -0.06, "bp": 59, "durum": "y"} and tu["kalan"] == 6
    assert g["2026-11-05"]["events"][0]["hisse"]["durum"] == "g"
    assert s["more_after"] == "2026-11-15" and s["more_label"] == "16 Kasım"
    assert g["2026-11-19"]["late"] and not g["2026-11-09"]["late"]
    assert s["late_n"] == sum(len(x["events"]) for x in s["groups"] if x["late"])
    w0 = s["weeks"][0]
    assert w0["label"] == "21–25 Eyl" and [d["gun_no"] for d in w0["days"]] == [21, 22, 23, 24, 25]
    assert w0["days"][3]["now"] and w0["days"][0]["past"]
    wk = {d["date"]: d for w in s["weeks"] for d in w["days"]}
    assert wk["2026-10-29"]["off"] and wk["2026-10-28"]["half"]
    assert wk["2026-09-30"]["kinds"] == ["t", "m"]
    assert len(s["weeks"]) <= tk.SERIT_HAFTA
    empty = tk.ssr_context({}, {}, TODAY)
    assert empty["groups"] == [] and empty["counts"]["all"] == 0 and empty["weeks"]


_YASAK = re.compile(r"\b(AL|SAT|BEKLE)\b|Bugün|bugün|Yarın|yarın|Hak kullanım|Ücretsiz|KAP|Yahoo|hedef|Hedef|tavsiye")


def test_dil_kanonu_api_metni():
    p = _build(estimates={"THYAO": "2026-11-05"})
    s = tk.ssr_context(p, {}, TODAY)
    for blob in (json.dumps(p, ensure_ascii=False), json.dumps(s, ensure_ascii=False)):
        assert not _YASAK.search(blob), _YASAK.search(blob).group(0)


def test_donemler_invariant():
    """Eski CPO-1678 tablo testinin yerine: yasal son gunler donem bitiminden sonra ve sirali."""
    for d in tk.DONEMLER:
        y, m = tk._donem_key(d["donem"])
        donem_sonu = date(y + (1 if m == 12 else 0), 1 if m == 12 else m + 1, 1)
        assert d["baslangic"] == donem_sonu.isoformat()
        gunler = [g for g, _ in d["son_gunler"]]
        assert gunler == sorted(gunler) and gunler[0] > d["baslangic"]
