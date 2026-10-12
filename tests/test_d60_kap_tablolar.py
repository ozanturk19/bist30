"""D-60 (C-59): finansal tablo sayfalari -- kap_tablolar (saf modul, py3.9 yerel kapida kosar).

Fixture'lar VPS'ten salt-okur kopya (12.10.2026):
  rec_<T>.json.gz      data/kap_fin/<T>.json (D-40a0/D-40a2 kaydi, 5 yillik + 5 ara donem raporu)
  <T>.json.gz          bu kayitlarin raporlari icin kap_tablolar onbellegi (ham sayfalardan parse_statements)
  raw_<idx>.html.gz    data/kap_fin/raw/<idx>.html.gz: THYAO 2025 yillik (sanayi), GARAN 2025 yillik (banka)
"""
import gzip
import json
import os
import re
import shutil
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import kap_tablolar as kt  # noqa: E402

FIX = os.path.join(ROOT, "tests", "fixtures", "kap_tablolar")
NM = {"THYAO": "Türk Hava Yolları", "TUPRS": "Tüpraş Türkiye Petrol Rafinerileri", "GARAN": "Garanti BBVA",
      "ANHYT": "Anadolu Hayat Emeklilik"}


def _rec(t):
    with gzip.open(os.path.join(FIX, "rec_%s.json.gz" % t), "rt", encoding="utf-8") as f:
        return json.load(f)


def _raw(idx):
    with gzip.open(os.path.join(FIX, "raw_%s.html.gz" % idx), "rt", encoding="utf-8") as f:
        return f.read()


def _parsed(t):
    return kt.load_parsed(t, _rec(t), raw_dir=os.path.join(FIX, "yok"), cache_dir=FIX, write=False)


def _view(t, slug, tur):
    return kt.gorunum(_rec(t), _parsed(t), slug, tur)


def _sayfa(t, slug):
    return kt.sayfa(t, slug, _rec(t), name=NM[t], raw_dir=os.path.join(FIX, "yok"), cache_dir=FIX, write=False)


def _row(view, key):
    return next(s for s in view["satirlar"] if s["anahtar"] == key)


def _raw_row(t, idx, st, key):
    return next(r for r in _parsed(t)[str(idx)][st]["satirlar"] if r[0] == key)


# ----------------------------------------------------------------------------- ayristirma

def test_ham_sayfa_ayristirmasi_onbellek_fixture_ile_ayni():
    """Onbellek fixture'i gercekten ham sayfadan uretilmis (sanayi + banka)."""
    assert kt.parse_statements(_raw(1565996)) == _parsed("THYAO")["1565996"]
    assert kt.parse_statements(_raw(1552588)) == _parsed("GARAN")["1552588"]


def test_banka_bilancosunda_toplam_sutunu_tp_yp_degil():
    bs = kt.parse_statements(_raw(1552588))["BS"]
    assert bs["basliklar"]["cur"].endswith("/ Toplam") and bs["birim"] == "1.000 TL"
    r = next(x for x in bs["satirlar"] if x[0] == "ifrs-full_Assets")
    assert (r[4], r[5]) == (4547773680.0, 3002579379.0)        # VARLIKLAR TOPLAMI (TP + YP)


def test_kalem_sirasi_ve_adi_raporun_kendisinden():
    v = _view("THYAO", "gelir-tablosu", "yillik")
    keys = [s["anahtar"] for s in v["satirlar"]]
    newest = [r[0] for r in _parsed("THYAO")["1565996"]["IS"]["satirlar"]]
    assert [k for k in newest if k in keys] == [k for k in keys if k in newest]
    assert keys[:5] == ["ifrs-full_ProfitLossAbstract", "ifrs-full_Revenue", "ifrs-full_CostOfSales",
                        "kap-fr_GrossProfitLossFromCommercialOperations", "ifrs-full_GrossProfit"]
    assert _row(v, "ifrs-full_Revenue")["etiket"] == "Hasılat"
    assert _row(v, "ifrs-full_ProfitLoss")["etiket"] == "DÖNEM KARI (ZARARI)"


# ----------------------------------------------------------------------------- aciklanan veri ilkesi

def test_her_sutun_tek_rapor_ve_yuzde_ayni_raporun_karsilastirmasindan():
    """TMS 29: 2024 sutunu 2024 raporunun cari sutunu; 2025 raporundaki (yeniden yazilmis) 2024 rakami
    kullanilmaz. Yuzde her sutunda kendi raporunun karsilastirma sutunundan."""
    v = _view("TUPRS", "gelir-tablosu", "yillik")
    assert [c["rapor"] for c in v["sutunlar"]] == [1554106, 1393446, 1254613, 1111634, 1002149]
    rev = _row(v, "ifrs-full_Revenue")
    assert [h["metin"] for h in rev["hucreler"]] == ["830.356", "810.386", "686.529", "481.765", "150.972"]
    r25 = _raw_row("TUPRS", 1554106, "IS", "ifrs-full_Revenue")
    r24 = _raw_row("TUPRS", 1393446, "IS", "ifrs-full_Revenue")
    assert r25[5] == 1060729904.0 and r24[4] == 810385588.0          # ayni yil, iki rapor, iki rakam
    assert rev["hucreler"][0]["degisim"] == kt._pct_text(kt.degisim(r25[4], r25[5])) == "−%21,7"
    assert rev["hucreler"][1]["degisim"] == kt._pct_text(kt.degisim(r24[4], r24[5])) == "−%18,2"


@pytest.mark.parametrize("t", sorted(NM))
def test_tum_hucreler_kendi_raporundan(t):
    rec, parsed = _rec(t), _parsed(t)
    reps = {r["idx"]: r for r in rec["reports"]}
    for slug in kt.SIRA:
        for tur in ("yillik", "ceyreklik"):
            v = kt.gorunum(rec, parsed, slug, tur)
            st = kt.TABLOLAR[slug][0]
            bolen = 1e6 if v["birim"].startswith("Milyon") else 1e3
            for j, c in enumerate(v["sutunlar"]):
                rep = reps[c["rapor"]]
                assert c["donem"] == rep["donem"]
                rows = {r[0]: r for r in parsed[str(c["rapor"])][st]["satirlar"]}
                ki = 6 if (st == "IS" and tur == "ceyreklik" and rep["period"] in (2, 3)) else 4
                for s in v["satirlar"]:
                    h = s["hucreler"][j] if s["hucreler"] else None
                    if not h:
                        continue
                    r = rows[s["anahtar"]]
                    assert h["deger"] == round(r[ki] * rep["mult"] / bolen, 3)
                    assert h["degisim"] == kt._pct_text(kt.degisim(r[ki], r[ki + 1]))


def test_garan_farkli_birimli_raporlar_ayni_olcekte():
    """GARAN 2026/06 raporu 1.000.000 TL, oncekiler 1.000 TL: tek olcege (Milyon TL) cevrilir."""
    rec = _rec("GARAN")
    assert {r["donem"]: r["unit"] for r in rec["reports"]}["2026/06"] == "1.000.000 TL"
    v = _view("GARAN", "bilanco", "ceyreklik")
    assert v["birim"] == "Milyon TL" and v["birim_notu"] == "Milyon TL · nominal"
    assert [h["metin"] for h in _row(v, "ifrs-full_Assets")["hucreler"][:3]] == ["5.216.482", "4.783.750", "4.547.774"]


def test_birim_ve_esas_basligi():
    thy = _view("THYAO", "bilanco", "yillik")
    assert thy["birim_notu"] == "Milyon TL · işlevsel para birimi ABD doları, TL'ye çevrilmiş"
    assert thy["esas_gruplari"] == []
    tup = _view("TUPRS", "bilanco", "yillik")
    assert tup["birim_notu"] == "Milyon TL · enflasyon düzeltmeli sütunlar kendi rapor tarihinin parasıyla"
    assert [(g["etiket"], g["kapsam"]) for g in tup["esas_gruplari"]] == [("Enflasyon düzeltmeli", 3), ("Nominal", 2)]
    assert [c["esas"] for c in tup["sutunlar"]] == ["enflasyon"] * 3 + ["nominal"] * 2
    tq = _view("TUPRS", "gelir-tablosu", "ceyreklik")
    assert tq["birim_notu"] == "Milyon TL · enflasyon düzeltmeli; her sütun kendi rapor tarihinin parasıyla"
    assert _view("ANHYT", "bilanco", "yillik")["birim_notu"] == "Milyon TL · nominal"


def test_donem_etiketleri_ve_sutun_sayisi():
    def lab(slug, tur):
        v = _view("THYAO", slug, tur)
        return [(c["etiket"]["ust"], c["etiket"]["alt"]) for c in v["sutunlar"]]
    assert lab("bilanco", "yillik") == [(y, "") for y in ("2025", "2024", "2023", "2022", "2021")]
    assert lab("gelir-tablosu", "ceyreklik") == [("Nis–Haz", "2026"), ("Oca–Mar", "2026"), ("Tem–Eyl", "2025"),
                                                  ("Nis–Haz", "2025"), ("Oca–Mar", "2025")]
    assert lab("bilanco", "ceyreklik")[:3] == [("30 Haz", "2026"), ("31 Mar", "2026"), ("31 Ara", "2025")]
    assert lab("nakit-akis", "ceyreklik")[:3] == [("Oca–Haz", "2026"), ("Oca–Mar", "2026"), ("Oca–Ara", "2025")]
    assert len(lab("bilanco", "ceyreklik")) == 10 <= kt.CEYREK_AZAMI
    v = _view("THYAO", "gelir-tablosu", "ceyreklik")
    assert v["sutunlar"][0]["etiket"]["tam"] == "Nisan–Haziran 2026"
    assert v["sutunlar"][0]["karsilastirma"] == "30 Haziran 2025"


def test_degisim_notu_tabloya_gore():
    assert "önceki yıl sonu" in _view("THYAO", "bilanco", "ceyreklik")["degisim_notu"]
    assert "aynı çeyreğine" in _view("THYAO", "gelir-tablosu", "ceyreklik")["degisim_notu"]
    assert "aynı dönemine" in _view("THYAO", "nakit-akis", "ceyreklik")["degisim_notu"]
    assert "önceki yıl sütununa" in _view("THYAO", "nakit-akis", "yillik")["degisim_notu"]


# ----------------------------------------------------------------------------- gizleme, sade gorunum, sablon

@pytest.mark.parametrize("t", sorted(NM))
def test_bos_satir_ve_bos_baslik_yok(t):
    for slug in kt.SIRA:
        for tur in ("yillik", "ceyreklik"):
            v = _view(t, slug, tur)
            for i, s in enumerate(v["satirlar"]):
                if s["baslik"]:
                    nxt = v["satirlar"][i + 1]
                    assert nxt["seviye"] > s["seviye"]
                else:
                    assert any(h and h["deger"] != 0 for h in s["hucreler"]) or \
                        any(h and h["metin"] != "0" for h in s["hucreler"])
                    assert len(s["hucreler"]) == len(v["sutunlar"])


def test_ara_toplam_tekrari_ve_tablo_basligi_gizli():
    v = _view("THYAO", "bilanco", "yillik")
    labels = [s["etiket"] for s in v["satirlar"]]
    assert "ARA TOPLAM" not in labels and "TOPLAM DÖNEN VARLIKLAR" in labels
    assert "Finansal Durum Tablosu (Bilanço)" not in labels       # seviye 0 tablo basligi


def test_sade_gorunum_derinligi_ve_her_zaman_gorunen():
    v = _view("THYAO", "gelir-tablosu", "yillik")
    assert not _row(v, "ifrs-full_ProfitLossAttributableToOwnersOfParent")["detay"]
    assert _row(v, "kap-fr_CurrentPeriodTaxExpenseContinuingOperations")["detay"]
    assert _row(v, "ifrs-full_ProfitLoss")["toplam"] and not _row(v, "ifrs-full_CostOfSales")["toplam"]
    g = _view("GARAN", "bilanco", "yillik")
    assert not _row(g, "kap-fr_Loans")["detay"] and _row(g, "kap-fr_Loans")["toplam"]
    assert v["detay_sayisi"] == sum(1 for s in v["satirlar"] if s["detay"] and not s["baslik"]) > 0


def test_sigortada_yinelenen_kalem_ayri_satir():
    v = _view("ANHYT", "gelir-tablosu", "yillik")
    keys = [s["anahtar"] for s in v["satirlar"]]
    dup = [k for k in keys if "#2" in k]
    assert dup and all(k.split("#")[0] in keys for k in dup)
    assert kt.sablon_of(_rec("ANHYT")) == "sigorta" and kt.sablon_of(_rec("GARAN")) == "banka"
    assert kt.sablon_of(_rec("THYAO")) == kt.sablon_of(_rec("TUPRS")) == "sanayi"


# ----------------------------------------------------------------------------- olgular ve sayfa baglami

def _sp(x):
    return x.replace("\u00a0", " ")


def test_olgu_cumleleri_betimleyici():
    assert _sp(_sayfa("THYAO", "gelir-tablosu")["olgu"]["cumle"]) == (
        "2025 yılında hasılat 955 Mrd ₺ (önceki yıla göre +%28,2), esas faaliyet kârı 90,1 Mrd ₺, "
        "dönem kârı 118 Mrd ₺ oldu.")
    assert _sp(_sayfa("THYAO", "bilanco")["olgu"]["cumle"]) == (
        "30 Haziran 2026 itibarıyla toplam varlıklar 2,36 T ₺ (önceki yıl sonuna göre +%18,2), "
        "toplam yükümlülükler 1,34 T ₺, toplam özkaynaklar 1,02 T ₺.")
    assert _sp(_sayfa("THYAO", "nakit-akis")["olgu"]["cumle"]) == (
        "2025 yılında işletme faaliyetlerinden 186 Mrd ₺ nakit girişi, yatırım faaliyetlerinden 145 Mrd ₺ "
        "nakit çıkışı, finansman faaliyetlerinden 49,2 Mrd ₺ nakit çıkışı oldu.")
    assert _sp(_sayfa("GARAN", "bilanco")["olgu"]["cumle"]) == (
        "30 Haziran 2026 itibarıyla toplam varlıklar 5,22 T ₺ (önceki yıl sonuna göre +%14,7), "
        "krediler 3,00 T ₺, mevduat 3,47 T ₺.")
    ol = _sayfa("THYAO", "gelir-tablosu")["olgu"]
    assert [(k["etiket"], k["pay"]) for k in ol["kalemler"]] == [
        ("Hasılat", 100.0), ("Brüt kâr", 16.3), ("Esas faaliyet kârı", 9.4), ("Dönem kârı", 12.4)]
    assert ol["rapor"] == 1565996


def test_sigorta_gelir_olgulari_ve_kucuk_kalem_seritte_yok():
    ol = _sayfa("ANHYT", "gelir-tablosu")["olgu"]
    assert [k["etiket"] for k in ol["kalemler"]] == [
        "Hayat teknik gelir", "Emeklilik teknik gelir", "Genel teknik bölüm dengesi", "Dönem net kârı"]
    assert _sp(ol["cumle"]) == ("2025 yılında genel teknik bölüm dengesi 3,6 Mrd ₺ (önceki yıla göre +%67,2), "
                                "dönem net kârı 6,0 Mrd ₺ oldu.")
    v = _view("ANHYT", "gelir-tablosu", "yillik")                 # tablo tam: hayat disi teknik gelir duruyor
    assert _row(v, "kap-fr_NonlifeTechnicalIncome")["hucreler"][0]["metin"] == "2"


def test_zarar_kalemi_zarar_diye_yazilir():
    rec, parsed = _rec("THYAO"), json.loads(json.dumps(_parsed("THYAO")))
    for r in parsed["1565996"]["IS"]["satirlar"]:
        if r[0] == "ifrs-full_ProfitLoss":
            r[4] = -5000.0
    ol = kt.olgular(rec, parsed, "gelir-tablosu")
    k = next(x for x in ol["kalemler"] if x["anahtar"] == "ifrs-full_ProfitLoss")
    assert (k["etiket"], _sp(k["metin"]), k["eksi"]) == ("Dönem zararı", "5,0 Mrd ₺", True)
    assert _sp(ol["cumle"]).endswith("dönem zararı 5,0 Mrd ₺ oldu.")


def test_sayfa_baglami_soru_sekmeler_kanonik():
    c = _sayfa("THYAO", "bilanco")
    assert c["soru"] == "Türk Hava Yolları'nın bilançosu nasıl?"
    assert _sayfa("ANHYT", "nakit-akis")["soru"] == "Anadolu Hayat Emeklilik'in nakit akışı nasıl?"
    assert _sayfa("GARAN", "gelir-tablosu")["soru"] == "Garanti BBVA'nın gelir tablosu nasıl?"
    assert [s["href"] for s in c["sekmeler"]] == ["/hisse/THYAO/bilanco", "/hisse/THYAO/gelir-tablosu",
                                                   "/hisse/THYAO/nakit-akis"]
    assert [s["aktif"] for s in c["sekmeler"]] == [True, False, False]
    assert c["kanonik"] == "https://borsapusula.com/hisse/THYAO/bilanco" and c["varsayilan"] == "yillik"
    assert c["sablon"] == "sanayi" and c["son_yayin"] and len(c["son_yayin"]) == 10


def test_404_kosullari():
    assert kt.sayfa("THYAO", "ozkaynak", _rec("THYAO"), cache_dir=FIX, write=False) is None
    assert kt.sayfa("THYAO", "bilanco", None) is None
    assert kt.sayfa("THYAO", "bilanco", {"reports": []}) is None
    # kayit var, ham sayfa ve onbellek yok -> sutun yok -> 404
    assert kt.sayfa("THYAO", "bilanco", _rec("THYAO"), raw_dir="/yok", cache_dir="/yok", write=False) is None


_YASAK = re.compile(r"\b(AL|SAT|al|sat|hedef|potansiyel|[üÜ]cretsiz|bugün|dün|yarın|geçen hafta|KAP|kaynak|"
                    r"zayıf|güçlü|sağlam|kötü|iyi|tavsiye|belki|tahmini|yaklaşık|[kK]ısmi)\b", re.U)


@pytest.mark.parametrize("t", sorted(NM))
def test_gorunen_metinde_yasak_dil_yok(t):
    for slug in kt.SIRA:
        c = _sayfa(t, slug)
        texts = [c["soru"], c["olgu"]["cumle"]] + [k["etiket"] for k in c["olgu"]["kalemler"]]
        for tur in ("yillik", "ceyreklik"):
            v = c[tur]
            texts += [v["birim_notu"], v["degisim_notu"]] + [g["etiket"] for g in v["esas_gruplari"]]
            texts += [x["etiket"][k] for x in v["sutunlar"] for k in ("ust", "alt", "tam")]
        for s in texts:
            assert not _YASAK.search(s), (slug, s)


# ----------------------------------------------------------------------------- bicim ve dil

def test_bicim_kanonu():
    assert kt._pct_text(12.345) == "+%12,3" and kt._pct_text(-3.06) == "−%3,1" and kt._pct_text(0.01) == "%0,0"
    assert kt._pct_text(216.4) == "+%216" and kt._pct_text(25355.0) == "+%25.355" and kt._pct_text(None) is None
    assert kt._fmt(-799912.0) == "−799.912" and kt._fmt(-0.2) == "0"
    assert kt.para_kisa(2.36e12) == "2,36\u00a0T\u00a0₺" and _sp(kt.para_kisa(955.472e9)) == "955 Mrd ₺"
    assert _sp(kt.para_kisa(90.129e9)) == "90,1 Mrd ₺" and _sp(kt.para_kisa(-144e6)) == "−144 Mn ₺"
    assert kt._hucre(0.36) == "0,4" and kt._hucre(-0.04) == "0" and kt._hucre(1234.6) == "1.235" and kt._hucre(0.0) == "0"


def test_degisim_ayni_isaretli_buyukluk_isaret_degisince_yok():
    assert kt.degisim(120.0, 100.0) == 20.0
    assert kt.degisim(-120.0, -100.0) == 20.0           # gider buyudu
    assert kt.degisim(5.0, -3.0) is None and kt.degisim(-5.0, 3.0) is None
    assert kt.degisim(5.0, 0.0) is None and kt.degisim(None, 1.0) is None
    assert kt.degisim(0.0, 10.0) == -100.0


@pytest.mark.parametrize("ad,ek", [
    ("Türk Hava Yolları", "'nın"), ("Garanti BBVA", "'nın"), ("THY", "'nin"), ("THYAO", "'nun"),
    ("Anadolu Hayat Emeklilik", "'in"), ("Tüpraş Türkiye Petrol Rafinerileri", "'nin"),
    ("Aselsan Elektronik Sanayi", "'nin"), ("BİM Birleşik Mağazalar", "'ın"), ("Koç Holding", "'in"),
    ("Ford Otosan", "'ın"), ("Ülker Bisküvi", "'nin"), ("Şok Marketler", "'in"), ("TÜPRAŞ", "'ın"),
    ("Pegasus", "'un"), ("Türk Telekom", "'un"), ("Coca-Cola İçecek", "'in"), ("Doğuş Otomotiv", "'in"),
    ("BİM", "'in"), ("GARAN", "'ın"), ("TUPRS", "'nin")])
def test_turkce_tamlayan_eki(ad, ek):
    assert kt.iyelik(ad) == ek


# ----------------------------------------------------------------------------- onbellek, baglanti, site haritasi

def _tmp_raw(tmp_path, idxs):
    d = tmp_path / "raw"
    d.mkdir()
    for i in idxs:
        shutil.copy(os.path.join(FIX, "raw_%s.html.gz" % i), str(d / ("%s.html.gz" % i)))
    return str(d)


def test_onbellek_rapor_listesi_degisince_yeniden_kurulur(tmp_path):
    rec = _rec("THYAO")
    raw = _tmp_raw(tmp_path, [1565996])
    cache = tmp_path / "cache"
    cache.mkdir()
    stale = {"imza": [kt.SCHEMA, 1], "ticker": "THYAO", "raporlar": {}}
    with gzip.open(str(cache / "THYAO.json.gz"), "wt", encoding="utf-8") as f:
        json.dump(stale, f)
    p = kt.load_parsed("THYAO", rec, raw_dir=raw, cache_dir=str(cache))
    assert p["1565996"] == _parsed("THYAO")["1565996"]
    assert sum(1 for v in p.values() if v) == 1                     # yalniz ham sayfasi olan rapor
    with gzip.open(str(cache / "THYAO.json.gz"), "rt", encoding="utf-8") as f:
        assert json.load(f)["imza"] == kt._imza(rec)
    c = kt.sayfa("THYAO", "bilanco", rec, name="Türk Hava Yolları", raw_dir=raw, cache_dir=str(cache))
    assert [x["rapor"] for x in c["yillik"]["sutunlar"]] == [1565996]   # eksik raporun sutunu yok, bos sutun yok


def test_baglantilar_ve_site_haritasi(tmp_path):
    raw = _tmp_raw(tmp_path, [1565996])
    recs = {"THYAO": _rec("THYAO"), "GARAN": _rec("GARAN")}
    assert [b["href"] for b in kt.baglantilar("THYAO", recs["THYAO"], raw_dir=raw)] == [
        "/hisse/THYAO/bilanco", "/hisse/THYAO/gelir-tablosu", "/hisse/THYAO/nakit-akis"]
    assert kt.baglantilar("GARAN", recs["GARAN"], raw_dir=raw) == []    # ham sayfa yok
    assert kt.baglantilar("SAHOL", None, raw_dir=raw) == []
    sm = kt.sitemap_girdileri(["THYAO", "GARAN", "SAHOL"], load_record=recs.get, raw_dir=raw)
    assert [g["loc"] for g in sm] == ["/hisse/THYAO/bilanco", "/hisse/THYAO/gelir-tablosu", "/hisse/THYAO/nakit-akis"]
    son = max(recs["THYAO"]["reports"], key=lambda r: (r["fy"], r["period"]))
    assert {g["lastmod"] for g in sm} == {son["publish"][:10]}
