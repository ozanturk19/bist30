"""D-68 (SEO #4 arka uç): hisse sayfası cevap-önde blok bağlamı (hisse_ozet.py).

Saf modül testleri yerelde (py3.9) koşar; stock_page() bağlam testi app.py ister (VPS, py3.10+).
Sayılar sentetik KAP kaydından: her rakam bir kalemden ya da aynı raporun iki sütunundan gelir.
"""
import re
import sys
from datetime import date

import pytest

import hisse_ozet as ho

NB = " "


def _rep(fy, period, items, fmt="sanayi", basis="tms29", mult=1000, idx=None):
    return {"fy": fy, "period": period, "donem": "%d/%02d" % (fy, period * 3), "format": fmt, "basis": basis,
            "mult": mult, "unit": "1.000 TL", "currency": "TL", "idx": idx or fy * 10 + period,
            "publish": "%d-%02d-15T18:00" % (fy if period < 4 else fy + 1, (period * 3 % 12) + 1),
            "items": {k: dict(zip(("cur", "prev", "q_cur", "q_prev"), v)) for k, v in items.items()}}


def _sanayi():
    reps = [
        _rep(2025, 2, {"revenue": (180, 150, 100, 80), "net_income_parent": (20, 25, 12, 10)}),
        _rep(2025, 3, {"revenue": (290, 240, 110, 90), "net_income_parent": (30, 33, 10, 8)}),
        _rep(2025, 4, {"revenue": (400, 330, None, None), "net_income_parent": (40, 44, None, None),
                       "issued_capital": (100, 100, None, None)}),
        _rep(2026, 1, {"revenue": (120, 100, None, None), "net_income_parent": (-5, 8, None, None)}),
        _rep(2026, 2, {"revenue": (260, 210, 140, 110), "net_income_parent": (6, 15, 11, 7),
                       "total_assets": (900, 800, None, None), "equity_parent": (500, 480, None, None),
                       "st_borrowings": (100, 90, None, None), "lt_borrowings": (50, 40, None, None),
                       "cash": (30, 20, None, None), "current_assets": (300, 280, None, None),
                       "current_liabilities": (200, 210, None, None), "issued_capital": (100, 100, None, None)}),
    ]
    return {"ticker": "TEST", "sector": "X", "reports": reps, "flags": {"banka": False, "sigorta": False},
            "derived": {"format": "sanayi", "basis": "tms29",
                        "temettu_odemeleri": [{"odeme": "2025-09-04", "brut": 1.5}, {"odeme": "2026-04-09", "brut": 2.25},
                                              {"odeme": "2026-11-02", "brut": 0.75}]}}


def _banka():
    rep = _rep(2026, 2, {"net_interest_income": (139_159, 79_883, 67_728, 41_691),
                         "net_income_parent": (63_442, 52_940, 30_288, 27_845),
                         "loans": (2_997_999, 2_715_712, None, None), "deposits": (3_466_148, 3_150_034, None, None),
                         "total_assets": (5_216_482, 4_547_774, None, None), "equity_total": (489_428, 446_636, None, None),
                         "nci": (2_000, 2_000, None, None)}, fmt="banka", basis="banka", mult=1_000_000)
    return {"ticker": "BNK", "reports": [rep], "flags": {"banka": True}, "derived": {"format": "banka", "basis": "banka"}}


def _sigorta():
    rep = _rep(2026, 2, {"net_income_parent": (3.6e9, 2.5e9, 2.0e9, 1.4e9), "total_assets": (4.8e11, 4.4e11, None, None),
                         "equity_total": (1.39e10, 1.36e10, None, None)}, basis="sigorta", mult=1)
    return {"ticker": "SGR", "reports": [rep], "flags": {"sigorta": True}, "derived": {"format": "sanayi", "basis": "sigorta"}}


# ----------------------------------------------------------------------------- biçim

def test_bicim_kanonu():
    assert ho.para(385.2e9) == "385" + NB + "Mrd" + NB + "₺"
    assert ho.para(1.0185e12) == "1,02" + NB + "T" + NB + "₺"
    assert ho.para(44.6e9) == "44,6" + NB + "Mrd" + NB + "₺"
    assert ho.para(456.4e6) == "456,4" + NB + "Mn" + NB + "₺"
    assert ho.para(-2.2e9).startswith("−")
    assert ho.para(383_210_127_360, 2) == "383,21" + NB + "Mrd" + NB + "₺"     # Yahoo yedeği (_fmtMoneyObj)
    assert ho.yuzde(-3.46, 1) == "−%3,5" and ho.yuzde(11.0, 1) == "%11,0" and ho.yuzde(-0.01, 1) == "%0,0"
    assert ho.sayi(1234.5, 1) == "1.234,5"
    assert ho.degisim_metni(43.39) == "+%43,4" and ho.degisim_metni(-24.58) == "−%24,6"
    assert ho.degisim_metni(320.4) == "+%320"


def test_tarih_ekleri():
    assert ho.tarihten(date(2026, 9, 28)) == "28 Eylül 2026'dan"
    assert ho.tarihten(date(2025, 9, 4)) == "4 Eylül 2025'ten"
    assert ho.tarihten(date(2027, 1, 2)) == "2 Ocak 2027'den"
    assert ho.tarihte(date(2026, 4, 9)) == "9 Nisan 2026'da"
    assert ho.tarihte(date(2023, 4, 9)) == "9 Nisan 2023'te"
    assert ho.tarihte(date(2030, 4, 9)) == "9 Nisan 2030'da"
    assert ho.tarihte(date(2040, 4, 9)) == "9 Nisan 2040'ta"


# ----------------------------------------------------------------------------- faaliyet konusu

def test_faaliyet_temizlik_kacis_ve_buyuk_harf():
    akbnk = "Bakanlar\\\\nKurulu'nun 3/6710 sayılı kararıyla verilen izin çerçevesinde, her türlü banka\\\\nişlemleri yapmak."
    assert ho.faaliyet_temizle(akbnk) == ("Bakanlar Kurulu'nun 3/6710 sayılı kararıyla verilen izin çerçevesinde, "
                                         "her türlü banka işlemleri yapmak.")
    assert ho.faaliyet_temizle("Yolcu\\ntaşımacılığı\nve kargo.") == "Yolcu taşımacılığı ve kargo."
    asels = ("HER TÜRLÜ KURUM KURULUŞ VE TÜKETİCİYE YÖNELİK OLARAK KARA, HAVA, DENİZ VE UZAY UYGULAMALARI "
             "KAPSAMINDA HER NEVİ ELEKTRİK, ELEKTRONİK CİHAZ ÜRETİMİ. İHRACAT YAPMAK A.Ş. İLE ORTAKLIK…")
    out = ho.faaliyet_temizle(asels)
    assert out.startswith("Her türlü kurum kuruluş ve tüketiciye yönelik olarak kara, hava, deniz ve uzay uygulamaları")
    assert "elektrik, elektronik cihaz üretimi. İhracat yapmak A.Ş. ile ortaklık…" in out
    assert not re.search(r"[A-ZÇĞİÖŞÜ]{4,}", out.replace("A.Ş.", ""))
    assert ho.faaliyet_temizle("Normal metin, KAP ve BIST kısaltmalarıyla.") == "Normal metin, KAP ve BIST kısaltmalarıyla."
    assert ho.faaliyet_temizle(None) is None and ho.faaliyet_temizle("  ") is None


# ----------------------------------------------------------------------------- son rapor + mini tablo

def test_son_rapor_ayni_raporun_karsilastirmasi():
    r = ho.son_rapor(_sanayi())
    assert r["etiket"] == "2026 ilk yarı" and not r["yillik"]
    hs, nk = r["kalemler"]
    assert hs["etiket"] == "Hasılat" and hs["tl"] == 260_000 and hs["degisim_metin"] == "+%23,8"   # 260/210
    assert nk["etiket"] == "Net kâr" and nk["degisim_metin"] == "−%60,0"                       # 6/15
    rec = _sanayi()
    rec["reports"][-1]["items"]["net_income_parent"]["cur"] = -6
    nk = ho.son_rapor(rec)["kalemler"][1]
    assert nk["etiket"] == "Net zarar" and nk["degisim"] is None and nk["don"] == "zarara_dondu"
    assert ho.son_rapor({"reports": []}) is None and ho.son_rapor(None) is None


def test_son_rapor_banka_ve_sigorta():
    b = ho.son_rapor(_banka())
    assert [k["etiket"] for k in b["kalemler"]] == ["Net faiz geliri", "Net kâr"]
    assert b["kalemler"][0]["metin"] == "139" + NB + "Mrd" + NB + "₺"
    s = ho.son_rapor(_sigorta())
    assert [k["etiket"] for k in s["kalemler"]] == ["Net kâr"] and s["ozkaynak"]["metin"] == "13,9" + NB + "Mrd" + NB + "₺"


def test_mini_tablo_son_dort_ceyrek_dorduncu_turetilmez():
    m = ho.mini_tablo(_sanayi())
    assert [c["ust"] + " " + c["alt"] for c in m["sutunlar"]] == ["Nis–Haz 2026", "Oca–Mar 2026", "Tem–Eyl 2025",
                                                                    "Nis–Haz 2025"]
    hs = m["satirlar"][0]
    assert hs["etiket"] == "Hasılat"
    # Q2/Q3 "3 Aylık" sütunları, Q1 kümülatif = çeyrek; yüzde aynı raporun geçen yıl aynı çeyreği
    assert [h["metin"] for h in hs["hucreler"]] == ["140.000,00" + NB + "₺", "120.000,00" + NB + "₺",
                                                     "110.000,00" + NB + "₺", "100.000,00" + NB + "₺"]
    assert hs["birim"] == "₺" and [h["sayi"] for h in hs["hucreler"]] == ["140.000", "120.000", "110.000", "100.000"]
    assert [h["degisim"] for h in hs["hucreler"]] == ["+%27,3", "+%20,0", "+%22,2", "+%25,0"]
    nk = m["satirlar"][1]["hucreler"]
    assert nk[1]["degisim"] is None and nk[1]["eksi"]          # 8 -> -5: işaret değişti, yüzde yok
    assert nk[1]["don"] == "zarara_dondu" and nk[0]["don"] is None and nk[2]["don"] is None  # CPO-1837
    assert m["soru"] == "Son dört çeyrekte hasılat ve net kâr nasıl değişti?"
    assert any("enflasyon düzeltmeli" in n.lower() for n in m["notlar"])
    bm = ho.mini_tablo(_banka())
    assert bm["soru"] == "Son çeyrekte net faiz geliri ve net kâr nasıl değişti?"
    assert [(r["birim"], r["hucreler"][0]["sayi"]) for r in bm["satirlar"]] == [("Mrd ₺", "67,7"), ("Mrd ₺", "30,3")]
    sg = ho.mini_tablo(_sigorta())
    assert [s["etiket"] for s in sg["satirlar"]] == ["Net kâr", "Özkaynaklar"]
    assert sg["satirlar"][1]["hucreler"][0]["degisim"] is None
    assert ho.mini_tablo({"reports": [_rep(2025, 4, {"revenue": (1, 1, None, None)})]}) is None


# ----------------------------------------------------------------------------- olgular + değerleme (hisse.js ile aynı kural)

def _fund(**kw):
    kap = {"sablon": "sanayi", "yillar": [2025], "oranlar": {"2025": {"net": 12.37, "gider_gelir": 40.0}},
           "degerleme_simdi": {"piyasa_degeri": 385.2e9, "fk": 3.45, "pd_dd": 0.38, "ozsermaye_karliligi": 11.0,
                               "son12ay_kar": 1e10, "pay_uyumsuz": False},
           "temettu": {"odeme_var": False, "brut_toplam": 0, "odemeler": [], "son_odeme": None, "duyurulan": []},
           "basis": "tms29"}
    kap.update(kw.pop("kap", {}))
    f = {"kap_durum": "var", "kap": kap, "sektor_ortanca": {"fk": {"deger": 12.47, "kapsam": "sektor"},
                                                            "pd_dd": {"deger": 1.5, "kapsam": "sektor"}},
         "financial_currency": "TRY", "market_cap": {"value": 3.8e11, "currency": "TRY"}}
    f.update(kw)
    return f


def test_olgular_sablona_gore():
    o = ho.olgular(_fund(), 279.25)
    assert o["piyasa_degeri"]["metin"] == "385" + NB + "Mrd" + NB + "₺"
    assert o["ozsermaye_karliligi"]["metin"] == "%11,0" and o["marj"]["metin"] == "%12,4"
    assert o["temettu"] == {"metin": "Ödeme yok", "soluk": True}
    b = ho.olgular(_fund(kap={"sablon": "banka"}), 100)
    assert b["marj_etiket"] == "Gider / gelir" and b["marj"]["metin"] == "%40,0"
    s = ho.olgular(_fund(kap={"sablon": "sigorta"}), 100)
    assert s["marj_gizli"] and s["marj"] is None
    t = ho.olgular(_fund(kap={"temettu": {"odeme_var": True, "brut_toplam": 5.2668872}}), 130.5)
    assert t["temettu"]["metin"] == "%4,04"
    # KAP kaydı yoksa Yahoo alanları (hisse.js yedeği), değer yoksa None (şablon JS'e bırakır)
    y = ho.olgular({"kap_durum": "hazirlaniyor", "market_cap": {"value": 3.8321e11, "currency": "TRY"}, "roe": 13.1}, 1)
    assert y["piyasa_degeri"]["metin"] == "383,21" + NB + "Mrd" + NB + "₺" and y["temettu"] is None
    assert ho.olgular({}, 1) is None


def test_degerleme_v2_hukmu_ve_esik():
    entry = {"temel_v2": {"degerleme": {"hukum": "ucuz", "kapsam": "sektor"}}}
    d = ho.degerleme(_fund(), entry, 279.25)
    assert d["cevap"] == "Ucuz tarafta" and d["sinif"] == "hx-dot--val"
    assert d["satirlar"] == [{"dt": "F/K", "dd": "3,5", "ortanca": "sektör 12,5"},
                             {"dt": "PD/DD", "dd": "0,38", "ortanca": "sektör 1,50"}]
    # v2 yok: hisse.js tvValuation eşiği (0,80 / 1,25) -- F/K ucuz, PD/DD pahalı -> Karışık
    f = _fund(kap={"degerleme_simdi": {"fk": 5.0, "pd_dd": 2.0, "pay_uyumsuz": False}})
    d = ho.degerleme(f, None, 10)
    assert d["cevap"] == "Karışık" and d["sinif"] == "hx-dot--warn"
    # pay adedi tutarsız: oran yok (JS ile aynı "hesaplanamıyor"), cümle ve SSS yazılmaz
    f = _fund(kap={"degerleme_simdi": {"fk": None, "pd_dd": None, "pay_uyumsuz": True}})
    d = ho.degerleme(f, {"temel_v2": {"degerleme": {"hukum": None}}}, 10)
    assert d["satirlar"] == [{"dt": "F/K ve PD/DD", "dd": "hesaplanamıyor", "ortanca": None}]
    assert ho._degerleme_cumlesi(d) is None and ho._fk_cevabi(d, None) is None
    # yabancı para notu ve analist hedefi (nötr değerleme göstergesi)
    f = _fund(kap={"basis": "yabanci_para"}, financial_currency="USD", analyst_target=461.23, analyst_count=13)
    d = ho.degerleme(f, entry, 279.25)
    assert d["not"] == "Şirket rakamlarını dolar ile açıklıyor; burada TL'ye çevrilmiş hali var."
    assert d["analist"] == {"hedef": "461,23" + NB + "₺", "fark": "%65,2", "yon": "üstünde", "sayi": 13}


def test_zarar_fk_cumlesi():
    f = _fund(kap={"degerleme_simdi": {"fk": None, "pd_dd": 1.2, "son12ay_kar": -5e6, "pay_uyumsuz": False}})
    d = ho.degerleme(f, None, 10)
    assert ho._degerleme_cumlesi(d).startswith("Son 12 ayda net zarar olduğu için F/K hesaplanmıyor; PD/DD 1,20")
    assert ho._fk_cevabi(d, None).startswith("Son 12 ayda net zarar olduğu için F/K hesaplanmıyor.")


# ----------------------------------------------------------------------------- trend, bildirimler

def test_trend_ve_bildirimler():
    tr = ho.trend({"signal": "SAT", "signal_date": "28.09.2026", "price": 279.25, "sl_level": 301.24})
    assert tr["etiket"] == "Trend Bozuldu" and tr["baslangic"] == "2026-09-28"
    assert tr["donus"] == {"metin": "301,24" + NB + "₺", "fark": "%7,9", "yon": "üstünde"}
    assert ho.trend({"signal": "BEKLE", "signal_date": None})["etiket"] == "Yatay"
    assert ho.trend({"signal": "AL"})["etiket"] == "Güçlü Trend"
    items = [{"id": 5, "ts": "2026-10-14T18:10:22", "ticker": "T", "title": "MTN itfası", "rutin": True, "class": "Özel durum"},
             {"id": 4, "ts": "2026-10-08T16:06:22", "ticker": "T", "title": "Eylül Trafik Sonuçları", "rutin": False,
              "class": "Özel durum"},
             {"id": 3, "ts": "2026-09-23T18:19:37", "ticker": "U", "title": "Uçak Siparişleri", "rutin": False,
              "class": "Özel durum"}]
    b = ho.bildirimler(items)
    assert [x["baslik"] for x in b] == ["MTN itfası", "Eylül Trafik Sonuçları", "Uçak Siparişleri"]
    assert b[1] == {"tarih": "2026-10-08", "tarih_metin": "8 Ekim 2026", "baslik": "Eylül Trafik Sonuçları",
                    "tur": "Özel durum", "href": "/hisse/T/bildirim/4"}
    assert b[2]["href"] == "/hisse/U/bildirim/3"     # yayınlayan şirketin kalıcı sayfası
    assert [x["baslik"] for x in ho.bildirimler(items, n=2)] == ["Eylül Trafik Sonuçları", "Uçak Siparişleri"]
    assert ho.bildirimler(None) == []


# ----------------------------------------------------------------------------- uçtan uca + dil kuralları

_YASAK = re.compile(r"\b(AL|SAT|al|sat)\b|[Üü]cretsiz|\bbugün|\bdün\b|\bgünün\b|kâr al|TP1|TP2|potansiyel|"
                    r"\bstop\b|sinyal|tavsiye|\bOrta\b|\bZayıf\b", re.U)


def _build(**kw):
    sig = {"ticker": "TEST", "price": 50.0, "bar_date": "14.10.2026", "signal": "SAT", "signal_date": "28.09.2026",
           "sl_level": 55.0}
    args = dict(rec=_sanayi(), fund=_fund(kap={"temettu": None}), entry={"temel_v2": {"degerleme": {"hukum": "makul", "kapsam": "sektor"}}},
                signal=sig, kap_info={"faaliyet_konusu": "Yolcu ve kargo taşımacılığı."}, items=[],
                today=date(2026, 10, 15))
    args.update(kw)
    return ho.build("TEST", "Test Havayolu", "Ulaştırma", **args)


def test_build_paragraf_tarih_ad_ve_sayilar():
    oz = _build()
    p = " ".join(oz["paragraf"])
    assert 3 <= len(oz["paragraf"]) <= 4
    assert p.startswith("Test Havayolu (TEST) Ulaştırma sektöründe işlem görüyor; 14 Ekim 2026 "
                        "kapanışında hisse fiyatı 50,00" + NB + "₺")
    assert len(re.findall(r"\d[\d.,]*", p)) >= 3
    assert "2026 ilk yarı raporunda hasılat" in p and "fiyat sektörüne göre makul düzeyde" in p
    assert "Son 12 ayda hisse başına brüt 2,25" + NB + "₺ temettü ödedi" in p
    assert "28 Eylül 2026'dan beri Trend Bozuldu durumu sürüyor." in p
    assert oz["meta"].startswith("TEST 14 Ekim 2026 kapanışı 50,00" + NB + "₺, F/K 3,5 (sektör ortancası 12,5), "
                                 "son 12 ay temettü verimi %4,50, 28 Eylül 2026'dan beri Trend Bozuldu")
    for txt in oz["paragraf"] + [oz["meta"]] + [q["q"] + " " + q["a"] for q in oz["sss"]]:
        assert not _YASAK.search(txt), txt


def test_build_sss_sirket_sorulari():
    oz = _build()
    qs = [q["q"] for q in oz["sss"]]
    assert qs == ["Test Havayolu (TEST) hissesi nasıl?", "Test Havayolu ne iş yapar?", "TEST temettü veriyor mu?",
                  "TEST bilançosu nasıl?", "TEST F/K oranı kaç?", "TEST hissesinin teknik görünümü nasıl?"]
    a = {q["tur"]: q["a"] for q in oz["sss"]}
    # Ozan 15.10: tam paragraf H1 altında değil, H1 ile aynı ilk SSS sorusunun cevabı (FAQPage JSON-LD'de de)
    assert a["ozet"] == " ".join(oz["paragraf"])
    assert a["faaliyet"].endswith("Faaliyet konusu: Yolcu ve kargo taşımacılığı.")
    assert a["temettu"].startswith("Son 12 ayda hisse başına brüt 2,25" + NB + "₺ temettü ödendi (9 Nisan 2026)")
    assert "Açıklanan sonraki ödeme 2 Kasım 2026'da, hisse başına brüt 0,75" + NB + "₺." in a["temettu"]
    assert a["bilanco"].startswith("30 Haziran 2026 itibarıyla toplam varlıklar")
    assert "net borç" in a["bilanco"].lower() and "cari oran 1,50" in a["bilanco"]
    assert a["trend"].startswith("14 Ekim 2026 kapanışında trend durumu Trend Bozuldu; bu durum 28 Eylül 2026'da başladı.")
    # faaliyet konusu yoksa soru hiç yok (THYAO); kayıt/temel veri yoksa yalnız olan sorular
    oz = _build(kap_info={"faaliyet_konusu": None}, rec=None, fund={})
    assert [q["tur"] for q in oz["sss"]] == ["ozet", "trend"]
    assert oz["faaliyet"] is None and oz["mini_tablo"] is None and oz["son_rapor"] is None


def test_kisaca_karti_satirlari():
    oz = _build()
    k = oz["kisaca"]
    assert k["baslik"] == "Test Havayolu kısaca" and k["alt"] == "14 Ekim 2026 kapanışı itibarıyla"
    r = {x["anahtar"]: (x["etiket"], x["deger"]) for x in k["satirlar"]}
    assert list(r) == ["faaliyet", "son_rapor", "degerleme", "temettu", "trend"]
    assert r["faaliyet"] == ("Faaliyet", "Ulaştırma sektörü · Yolcu ve kargo taşımacılığı")
    assert r["son_rapor"][0] == "Son rapor (2026 ilk yarı)"
    assert r["son_rapor"][1].startswith("Hasılat 260.000,00" + NB + "₺ (+%23,8) · Net kâr")
    assert r["degerleme"][1] == "F/K 3,5 (sektör ortancası 12,5) · PD/DD 0,38 (1,50) →" + NB + "makul"
    assert r["temettu"] == ("Temettü (son 12 ay)", "Hisse başına brüt 2,25" + NB + "₺ · verim %4,50")
    assert r["trend"] == ("Trend", "28 Eylül 2026'dan beri Trend Bozuldu")
    blob = " ".join(x["deger"] for x in k["satirlar"])
    assert "—" not in blob and "Piyasa değeri" not in blob and "Özsermaye" not in blob   # başlık olguları tekrar edilmez
    # veri yoksa satır yok; hiç satır yoksa kart yok
    oz = _build(kap_info=None, rec=None, fund={}, signal={"price": 1.0})
    assert oz["kisaca"]["satirlar"] == [{"anahtar": "faaliyet", "etiket": "Faaliyet", "deger": "Ulaştırma sektörü"}]
    assert ho.build("YOK", None, "Diğer")["kisaca"] is None
    # yabancı para esası ve "Ödeme yok"
    rec = _sanayi()
    rec["reports"][-1]["basis"] = "yabanci_para"
    k = _build(rec=rec, fund=_fund())["kisaca"]
    r = {x["anahtar"]: (x["etiket"], x["deger"]) for x in k["satirlar"]}
    assert r["son_rapor"][0] == "Son rapor (2026 ilk yarı, TL'ye çevrilmiş)" and r["temettu"][1] == "Ödeme yok"


def test_faaliyet_kisa_tek_satir():
    assert ho.faaliyet_kisa("Şirketin amacı, tıbbi cihaz üretimi ve satışı.") == "Tıbbi cihaz üretimi ve satışı"
    assert ho.faaliyet_kisa("Şirket; tabi olduğu mevzuat uyarınca ham petrol rafine etmek.") == \
        "Tabi olduğu mevzuat uyarınca ham petrol rafine etmek"
    uzun = "Her türlü " + "elektrik elektronik cihaz, " * 12 + "üretimi."
    k = ho.faaliyet_kisa(uzun)
    assert len(k) <= 111 and k.endswith("…") and not k.endswith(",…") and " " not in k[-2:]
    assert ho.faaliyet_kisa(None) is None


def test_build_eksik_veri_patlamaz():
    oz = ho.build("YOK", None, "Diğer", rec=None, fund=None, entry=None, signal=None, kap_info=None, items=None)
    assert oz["paragraf"] == ["YOK Borsa İstanbul'da işlem görüyor."] and oz["sss"] == [] and oz["meta"] is None
    assert oz["sektor"] is None and oz["bildirimler"] == [] and oz["bildirim_listesi"] == [] and oz["olgular"] is None
    # bozuk kayıt bir bölümü düşürür, diğerleri çizilir
    oz = _build(rec={"reports": [{"fy": 2026, "period": 2}]})
    assert oz["son_rapor"] is None and oz["trend"]["etiket"] == "Trend Bozuldu" and oz["paragraf"]


# ----------------------------------------------------------------------------- stock_page bağlamı (VPS)

@pytest.mark.skipif(sys.version_info < (3, 10), reason="app.py 3.10+ ister — VPS venv'de çalıştır")
def test_stock_page_baglami_ozet_ve_sirket_sss():
    import app
    from flask import template_rendered
    seen = []

    def _rec(sender, template, context, **kw):
        if template.name == "hisse.html":
            seen.append(context)

    template_rendered.connect(_rec, app.app)
    try:
        assert app.app.test_client().get("/hisse/THYAO").status_code == 200
    finally:
        template_rendered.disconnect(_rec, app.app)
    ctx = seen[0]
    oz = ctx["ozet"]
    assert oz is None or isinstance(oz, dict)
    blob = " ".join(q["q"] + " " + q["a"] for q in ctx["seo_faq"])
    assert "teknik sinyali nedir" not in blob and "Teknik göstergeler: ADX" not in blob
    if oz:
        assert ctx["seo_faq"] == oz["sss"]
        assert oz["paragraf"] and oz["paragraf"][0].startswith(app.STOCK_NAMES.get("THYAO", "THYAO"))
    # KAP faaliyet konusu temizliği "Hakkında" metnine de uygulanır
    for t in ("AKBNK", "ASELS"):
        cs = app.get_company_summary(t)
        if cs:
            assert "\\n" not in cs and not re.search(r"[A-ZÇĞİÖŞÜ]{6,} [A-ZÇĞİÖŞÜ]{6,}", cs)
