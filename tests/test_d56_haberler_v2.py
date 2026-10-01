"""D-56 Haberler v2 (O28=A): tur kurallari, cumle duzeni, /haberler/bildirimler akisi,
gunun hikayesi, Gundem sirket kartlari, D-57 sozlesmesi, Gundem/Bulten ayni hisse kumesi.
Kayitli ornekler (tests/fixtures/haber_v2): KAP akisi 25.09-01.10 (canli depodan, ic iz
silinmis) ve 01.10 donmus isi haritasi. Ag yok, app.py import edilmez (Python 3.9)."""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import date, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import bulten  # noqa: E402
import haber_gundem as hg  # noqa: E402
import haber_v2 as hv  # noqa: E402

FX = os.path.join(ROOT, "tests", "fixtures", "haber_v2")
FORBIDDEN = re.compile(r"\b(AL|SAT|BEKLE|TP1|TP2|hedef|potansiyel|tavsiye|fırsat|kâr al|bugün|dün|yarın|"
                       r"Ücretsiz|Kısmi|Sınırlı veri|hazırlanıyor|veri tamlığı)\b", re.I)


def _items():
    with open(os.path.join(FX, "kap_items_0925_1001.json"), encoding="utf-8") as f:
        return json.load(f)


def _snap():
    with open(os.path.join(FX, "heatmap_20261001.json"), encoding="utf-8") as f:
        return json.load(f)


def _it(subject, title, kap_class="ODA", **kw):
    d = {"id": 1, "ts": "2026-09-28T16:56:00", "ticker": "FONET", "tickers": ["FONET"], "class": "Özel durum",
         "subject": subject, "kap_class": kap_class, "title": title, "rutin": False, "onem": None}
    d.update(kw)
    return d


# ----------------------------------------------------------------------------- tur

def test_filing_type_turkish_lowercase_ihale_not_missed():
    # str.lower() 'İhale' -> 'i̇hale' (birlesik nokta) ve 'ihale' aramasi kaciriyordu
    assert "ihale" not in "İhalenin Sonucu".lower()
    gen = "Özel Durum Açıklaması (Genel)"
    assert hv.filing_type(_it(gen, "Batman İl Sağlık Müdürlüğü Tarafından Yapılan İhalenin Sonucu Hakkında")) == "is"
    assert hv.filing_type(_it(gen, "İHALE SONUCU HAKKINDA")) == "is"
    assert hv.filing_type(_it(gen, "Milsoft tarafından sipariş alınması")) == "is"
    assert hv.filing_type(_it("İhale Süreci / Sonucu", "x")) == "is"


def test_filing_type_rules():
    gen = "Özel Durum Açıklaması (Genel)"
    assert hv.filing_type(_it("Finansal Rapor", "x", kap_class="FR")) == "finansal"
    assert hv.filing_type(_it("Kar Payı Dağıtım İşlemlerine İlişkin Bildirim", "x")) == "temettu"
    assert hv.filing_type(_it(gen, "01.06.2025-31.05.2026 Hesap Dönemine İlişkin Kar Dağıtımı")) == "ozel"
    assert hv.filing_type(_it(gen, "Kâr Payı Dağıtımı Hakkında")) == "temettu"
    assert hv.filing_type(_it("Kredi Derecelendirmesi", "KREDİ DERECELENDİRME BİLDİRİMİ")) == "kredi"
    assert hv.filing_type(_it(gen, "Kurumsal Yönetim Derecelendirme Notuna İlişkin Açıklama")) == "yonetim"
    assert hv.filing_type(_it(gen, "Özel Denetçi Tayin Edilmesi Talebine İlişkin Dava Açılması")) == "dava"
    assert hv.filing_type(_it(gen, "Ağrı İdare Mahkemesi 2026/1355 Esas Numaralı Ara Karar")) == "dava"
    assert hv.filing_type(_it(gen, "Genel Kurula Davet")) == "yonetim"      # 'davet' dava degil
    assert hv.filing_type(_it(gen, "Şirketimiz Ortağı Doğanlar Yatırım Holding A.Ş. Pay Alımı Hakkında")) == "sermaye"
    assert hv.filing_type(_it(gen, "Bedelsiz Sermaye Artırımı Spk Onaylı Belgeler")) == "sermaye"
    assert hv.filing_type(_it(gen, "Bağımsız Yönetim Kurulu Üyelerinin Görevinden Ayrılması")) == "yonetim"
    assert hv.filing_type(_it(gen, "Yatırımcı İlişkileri Bölümü hakkında")) == "yonetim"
    assert hv.filing_type(_it(gen, "Basında Yer Alan Haberler Hakkında Açıklama")) == "ozel"
    assert hv.filing_type(_it("Payların Geri Alınmasına İlişkin Bildirim", "Pay Geri Alım Programı Başlatılması")) == "sermaye"
    # recorded feed: every listed filing gets one of the 8 types; no exceptions
    ks = set(hv.filing_type(x) for x in _items() if hv.is_listed(x))
    assert ks <= set(k for k, _, _ in hv.TYPES) and {"is", "kredi", "ozel", "sermaye"} <= ks


def test_tur_args_and_legacy():
    assert hv.tur_from_arg("temettu") == ("temettu", None)
    assert hv.tur_from_arg("ihale") == ("is", None)
    assert hv.tur_from_arg("bilanco") == ("finansal", "finansal-rapor")
    assert hv.tur_from_arg("ozel") == ("ozel", "ozel-durum")
    assert hv.tur_from_arg("xx") == (None, None) and hv.tur_from_arg(None) == (None, None)
    assert [s for _, _, s in hv.TYPES] == ["finansal-rapor", "temettu", "sermaye", "genel-kurul", "ihale",
                                           "kredi-notu", "dava", "ozel-durum"]


# ----------------------------------------------------------------------------- baslik

def test_sentence_case_all_caps_turkish():
    assert hv.sentence_case("KREDİ DERECELENDİRME BİLDİRİMİ") == "Kredi derecelendirme bildirimi"
    assert hv.sentence_case("MADDİ DURAN VARLIK SATIŞI HAKKINDA") == "Maddi duran varlık satışı hakkında"
    assert hv.sentence_case("İHALE SONUCU") == "İhale sonucu"
    assert hv.sentence_case("IŞIK HOLDİNG SPK ONAYI") == "Işık holding SPK onayı"
    assert hv.sentence_case("FITCH NOTU HAKKINDA", keep=["ZOREN"]) == "Fitch notu hakkında"
    assert hv.sentence_case("ZOREN A.Ş. II. TERTİP", keep=["ZOREN"]) == "ZOREN A.Ş. II. tertip"
    # buyuk harf degilse dokunulmaz
    t = "Fitch Ratings Kredi Derecelendirme Notu"
    assert hv.sentence_case(t) == t
    caps = [x for x in _items() if hv._is_caps(x["title"])]
    assert caps and all(not hv._is_caps(hv.display_title(x)) for x in caps)


# ----------------------------------------------------------------------------- onem

def test_onem_view_structured():
    o = {"pct": 16.11, "txt": "%16,1", "approx": False, "basis": "İhale bedeli / 2025 hasılatı",
         "formula": "ihale bedeli / yıllık hasılat = %16,1", "amount_txt": "137.712.000 ₺",
         "amount_try": 137712000, "rev_year": 2025, "rev": 855100000.0, "fx": None}
    v = hv.onem_view(o)
    assert v["big"] == "%16,1" and v["basis"] == "İhale bedeli" and v["year"] == 2025
    assert v["lab"] == "İhale bedeli, 2025 hasılatına oranı"
    assert v["calc"] == "137,7 Mn ₺ ÷ 855,1 Mn ₺ (2025 hasılatı)"
    assert v["w"] == 32.2
    fx = dict(o, approx=True, txt="~%4,1", amount_txt="700.000 $", amount_try=34286000, fx={"cur": "USD"})
    assert hv.onem_view(fx)["calc"].startswith("700.000 $ ≈ 34,3 Mn ₺ ÷") and hv.onem_view(fx)["big"] == "~%16,1"
    assert hv.onem_view(None) is None and hv.onem_view({"pct": None}) is None
    assert hv.onem_view(dict(o, pct=0.3))["w"] == 2.0 and hv.onem_view(dict(o, pct=80))["w"] == 100.0


# ----------------------------------------------------------------------------- akis

def test_feed_window_pagination_counts_and_grouping():
    items = _items()
    fd = hv.feed(items, "2026-10-01", page=1, names={"FONET": "Fonet Bilgi Teknolojileri"})
    listed = [x for x in items if hv.is_listed(x)]
    assert fd["total"] == len(listed) and fd["per_page"] == 30
    assert fd["pages"] == (len(listed) + 29) // 30 and fd["shown_from"] == 1 and fd["shown_to"] == 30
    assert fd["counts"]["all"] == len(listed) == sum(fd["counts"][k] for k, _, _ in hv.TYPES)
    assert fd["range_label"] == "25 Eylül – 1 Ekim"
    days = [d["day"] for d in fd["days"]]
    assert days == sorted(days, reverse=True) and days[0] == "2026-10-01"
    n = sum(1 + len(r["more"]) for d in fd["days"] for r in d["rows"])
    assert n == 30                                          # gruplama sayfa basina 30 bildirimi bozmaz
    d0 = fd["days"][0]
    assert d0["label"] == "1 Ekim" and d0["w"] == "Perşembe"
    assert d0["total"] == sum(1 for x in listed if x["ts"][:10] == "2026-10-01")
    assert d0["routine"] == sum(1 for x in items if x["ts"][:10] == "2026-10-01" and x.get("rutin")
                                and x["kap_class"] in ("ODA", "FR", "DG"))
    assert sum(m["n"] for m in d0["mix"]) == d0["total"]
    for d in fd["days"]:
        for r in d["rows"]:
            for m in r["more"]:
                assert (m["day"], m["ticker"], m["k"]) == (r["day"], r["ticker"], r["k"])
            assert r["href"].startswith("/hisse/%s/bildirim/" % r["ticker"])
    # son sayfa ve sayfa sinirlari
    last = hv.feed(items, "2026-10-01", page=99)
    assert last["page"] == last["pages"] and last["shown_to"] == last["total"]
    # tur filtresi: sayac ayni (tum turler), liste yalniz o tur, rutin sayilmaz
    kr = hv.feed(items, "2026-10-01", tur="kredi")
    assert kr["total"] == fd["counts"]["kredi"] and kr["counts"] == fd["counts"]
    assert all(r["k"] == "kredi" for d in kr["days"] for r in d["rows"]) and all(d["routine"] == 0 for d in kr["days"])
    # gun gorunumu + rutin dahil
    rt = hv.feed(items, "2026-10-01", day="2026-09-29", include_rutin=True, per_page=100)
    assert rt["total"] == sum(1 for x in items if x["ts"][:10] == "2026-09-29" and x["kap_class"] in ("ODA", "FR", "DG"))
    # pencere disi (30 gun) eleniyor
    assert hv.feed(items, "2026-11-20")["total"] == 0


def test_feed_rows_text_rules():
    fd = hv.feed(_items(), "2026-10-01", per_page=100)
    text = json.dumps(fd, ensure_ascii=False)
    assert not FORBIDDEN.search(text)
    assert "kap.org.tr" not in text and "http" not in text      # kaynak etiketi/dis baglanti yok
    assert "_src" not in text


# ----------------------------------------------------------------------------- spark

def test_spark_points_and_chart_file(tmp_path):
    sp = hv.spark([10, 12, 11, 14])
    assert sp["up"] is True and sp["pts"].startswith("0.0,") and sp["pts"].split()[-1].startswith("100.0,")
    ys = [float(p.split(",")[1]) for p in sp["pts"].split()]
    assert min(ys) == 6.0 and max(ys) == 94.0 and sp["ly"] == 6.0
    assert hv.spark([5]) is None and hv.spark([]) is None and hv.spark([3, 3])["ly"] == 50.0
    p = tmp_path / "chart_FONET.json"
    p.write_text(json.dumps({"ohlc": [{"time": "d%d" % i, "close": float(i)} for i in range(40)]}))
    assert hv.closes_from_chart_file(str(p)) == [float(i) for i in range(10, 40)]
    assert hv.closes_from_chart_file(str(tmp_path / "yok.json")) == []


# ----------------------------------------------------------------------------- gunun hikayesi

def test_lead_story_bist100_same_as_bulten():
    snap = _snap()
    secs = bulten.isi_haritasi_ozet(snap)
    ld = hv.lead_story(snap, secs, [12000 + i * 10 for i in range(29)] + [12249.04])
    assert ld["day"] == "2026-10-01" and ld["day_label"] == "1 Ekim"
    assert ld["up"] == 81 and ld["down"] == 17 and ld["n"] == 100       # BIST100 (Bulten/harita), 233 degil
    assert ld["title"].startswith("BIST100 %2,53 yükseldi; 81 hisse değer kazandı")
    assert ld["text"].startswith("Endeks 12.249,04 puanda kapandı; 1 aylık değişim −%13,91.")
    hi, lo = secs[0], secs[-1]
    assert ld["sector_hi"]["sektor"] == hi["sektor"] and ld["sector_lo"]["sektor"] == lo["sektor"]
    assert hi["sektor"] in ld["text"] and lo["sektor"] in ld["text"]
    assert ld["hot"] is True and ld["sp"]["up"] is True and len(ld["movers"]) == 2
    assert not FORBIDDEN.search(ld["title"] + ld["text"])
    down = json.loads(json.dumps(snap))
    down["xu100"]["ch"]["d1"] = -2.38
    down["counts"] = {"up": 9, "down": 91, "flat": 0}
    for i, r in enumerate(down["rows"]):
        r["lim"] = "taban" if i < 25 else None
    t = hv.lead_story(down, secs, [])["title"]
    assert t == "BIST100 %2,38 düştü; 91 hisse değer kaybetti, 25 hisse tabanda kapandı"
    assert hv.lead_story(None, secs, []) is None and hv.lead_story({"xu100": {}, "rows": []}, [], []) is None


def test_gundem_print_uses_bist100_and_bulten_sectors():
    snap = _snap()
    secs = bulten.isi_haritasi_ozet(snap)
    members = [r["t"] for r in snap["rows"]]
    # 233 hisselik evren: BIST100 disi hisseler tersi yonde (eski hata: sayim/sektor bunlardan)
    stocks = [{"ticker": r["t"], "change_pct": r["ch"]["d1"], "sector": r["g"], "signal": "BEKLE"} for r in snap["rows"]]
    stocks += [{"ticker": "X%03d" % i, "change_pct": -5.0, "sector": "Orman, Kağıt ve Basım", "signal": "BEKLE"}
               for i in range(133)]
    macro = [{"label": "USDTRY", "price": 49.03, "change": 0.01}, {"label": "SP500", "price": 7645.64, "change": -0.1},
             {"label": "PETROL", "price": 100.89, "change": 2.92}]
    now = datetime(2026, 10, 1, 19, 30)
    doc = hg.build_print(stocks, macro, {"close": 12249.04, "change_pct": 2.53}, [], {}, [], now, date(2026, 10, 1),
                         "aksam", members=members, sectors=secs, counts=snap["counts"])
    tr = {x["id"]: x for x in doc["groups"][0]["items"]}
    assert "BIST100 hisselerinden 81 yükselen, 17 düşen, 2 değişmeyen" in tr["bist"]["p"]
    assert secs[0]["sektor"] in tr["sektor"]["h"] and secs[-1]["sektor"] in tr["sektor"]["h"]
    assert "Orman" not in json.dumps(doc, ensure_ascii=False)
    # snapshot yoksa: yalniz BIST100 uyeleri sayilir
    doc2 = hg.build_print(stocks, macro, {"close": 12249.04, "change_pct": 2.53}, [], {}, [], now, date(2026, 10, 1),
                          "aksam", members=members)
    p = {x["id"]: x for x in doc2["groups"][0]["items"]}["bist"]["p"]
    up = sum(1 for r in snap["rows"] if r["ch"]["d1"] > 0)
    assert "BIST100 hisselerinden %d yükselen" % up in p and "Orman" not in json.dumps(doc2, ensure_ascii=False)
    # gorsel alanlar (v) ve kategori (cat) baskiya yazilir
    kinds = {x["id"]: (x.get("cat"), (x.get("v") or {}).get("k")) for g in doc["groups"] for x in g["items"]}
    assert kinds["bist"] == ("piyasa", "breadth") and kinds["kur"] == ("doviz", "fx")
    assert kinds["abd"] == ("dunya", "fx") and kinds["emtia"] == ("doviz", "fx") and kinds["sektor"][1] == "bars"


# ----------------------------------------------------------------------------- sirket kartlari

def test_company_cards_rule_based():
    items = _items()
    cards = hv.company_cards(items, "2026-10-01", {"OTKAR": "Otokar Otomotiv"}, n=6)
    assert 1 <= len(cards) <= 6 and len(set(c["ticker"] for c in cards)) == len(cards)
    days = set(c["day"] for c in cards)
    assert days <= {"2026-10-01", "2026-09-30"}
    with_onem = [c for c in cards if c["onem"]]
    assert with_onem and cards[0]["onem"] and cards[0]["onem"]["pct"] == max(c["onem"]["pct"] for c in with_onem)
    assert all(c["k"] != "ozel" or c["onem"] for c in cards)
    assert all(c["hot"] == bool(c["onem"] and c["onem"]["pct"] >= 5) for c in cards)
    assert cards[0]["time_label"].startswith(hv.day_label(cards[0]["day"]) + " · ")
    assert not FORBIDDEN.search(json.dumps(cards, ensure_ascii=False))


# ----------------------------------------------------------------------------- D-57

def test_clean_gundem_haber_contract():
    doc = {"baski": "2026-10-02T08:30:00+03:00", "baski_label": "2 Ekim 2026 · 08:30", "maddeler": [
        {"id": "g-1", "kategori": "Türkiye", "baslik": "Başlık", "ozet": "Özet.", "hisseler": ["THYAO", "bad!"],
         "kaynaklar": [{"ad": "AA", "url": "https://www.aa.com.tr/x"}, {"ad": "Kötü", "url": "javascript:alert(1)"}],
         "ai": True, "onemli": True},
        {"id": "g-2", "kategori": "Uzay", "baslik": "x", "ozet": "y"},
        {"id": "g-3", "kategori": "Emtia", "baslik": "", "ozet": "y"},
        "bozuk"]}
    c = hv.clean_gundem_haber(doc)
    assert c["baski_label"] == "2 Ekim 2026 · 08:30" and len(c["maddeler"]) == 1
    m = c["maddeler"][0]
    assert m["hisseler"] == ["THYAO"] and m["kaynaklar"] == [{"ad": "AA", "url": "https://www.aa.com.tr/x"}]
    assert m["ai"] is True and m["onemli"] is True
    assert hv.clean_gundem_haber({"maddeler": []}) is None and hv.clean_gundem_haber(None) is None


def test_labels():
    assert hv.range_label("2026-09-25", "2026-09-28") == "25–28 Eylül"
    assert hv.range_label("2026-09-28", "2026-09-28") == "28 Eylül"
    assert hv.tr_pct(-0.5) == "−%0,50" and hv.tr_pct(2.531, 1, False) == "%2,5" and hv.big_try(1.26e9) == "1,3 Mrd ₺"


def test_gundem_haber_source_falls_back_to_d57_module():
    """D-57 dali `_gundem_haber_payload` tanimlamaz; `import gundem_haber` + context processor kullanir.
    /haberler `gundem_haber`i acikca gecirdigi icin kaynak D-56 kancasinda bulunmali (yoksa None ezer)."""
    import types
    doc = {"baski_label": "2 Ekim 2026 · 08:30", "maddeler": [
        {"id": "g-1", "kategori": "Dünya", "baslik": "B", "ozet": "Ö", "hisseler": [],
         "kaynaklar": [{"ad": "AA", "url": "https://www.aa.com.tr/x", "tarih": "2026-10-02"}], "ai": True}]}
    mod = types.SimpleNamespace(load_latest=lambda: doc)
    assert hv.gundem_haber_source({}) is None and hv.gundem_haber_from({}) is None
    assert hv.gundem_haber_source({"gundem_haber": mod}) is mod.load_latest
    got = hv.gundem_haber_from({"gundem_haber": mod})
    assert got["maddeler"][0]["kaynaklar"] == [{"ad": "AA", "url": "https://www.aa.com.tr/x"}]
    # acik kanca varsa o once gelir; hata -> None (+ log)
    assert hv.gundem_haber_from({"gundem_haber": mod, "_gundem_haber_payload": lambda: {"maddeler": []}}) is None
    logs = []
    assert hv.gundem_haber_from({"gundem_haber": types.SimpleNamespace(load_latest=lambda: 1 / 0)}, logs.append) is None
    assert logs and "okunamadı" in logs[0]
    # D-57 modulu baski yokken None dondurur
    assert hv.gundem_haber_from({"gundem_haber": types.SimpleNamespace(load_latest=lambda: None)}) is None


def test_feed_ticker_filter_and_urls():
    items = _items()
    t = "GARAN"
    mine = [x for x in items if t in (x.get("tickers") or [x["ticker"]]) and x["kap_class"] in ("ODA", "FR", "DG")]
    fd = hv.feed(items, "2026-10-01", ticker=t, per_page=100)
    assert fd["total"] == sum(1 for x in mine if not x.get("rutin")) > 0
    assert all(r["ticker"] == t or t in r["tickers"] for d in fd["days"] for r in d["rows"])
    assert fd["counts"]["all"] == fd["total"]
    assert all(d["routine"] == sum(1 for x in mine if x["ts"][:10] == d["day"] and x.get("rutin")) for d in fd["days"])
    # hisse gorunumu 30 gun penceresiyle sinirli degil (depodaki tum gecmis)
    assert hv.feed(items, "2026-12-31", ticker=t)["total"] == fd["total"]
    assert hv.feed(items, "2026-12-31")["total"] == 0
    # gun + hisse
    d = hv.feed(items, "2026-10-01", ticker=t, day="2026-09-30", include_rutin=True)
    assert d["total"] == sum(1 for x in mine if x["ts"][:10] == "2026-09-30")
    # adresler
    assert hv.bildirimler_url() == "/haberler/bildirimler"
    assert hv.bildirimler_url("kredi-notu", "THYAO", 3) == "/haberler/bildirimler?hisse=THYAO&tur=kredi-notu&sayfa=3"
    assert hv.bildirimler_url(tarih="2026-10-01", rutin=True, page=2) == \
        "/haberler/bildirimler?tarih=2026-10-01&rutin=1&sayfa=2"
    lr = hv.legacy_haberler_redirect
    assert lr({}) is None
    assert lr({"hisse": "thyao"}) == "/haberler/bildirimler?hisse=THYAO"
    assert lr({"hisse": "THYAO", "tur": "bilanco", "sayfa": "2"}) == \
        "/haberler/bildirimler?hisse=THYAO&tur=finansal-rapor&sayfa=3"
    assert lr({"tur": "temettu"}) == "/haberler/bildirimler?tur=temettu"
    assert lr({"tur": "xx", "sayfa": "abc"}) == "/haberler/bildirimler"
    assert lr({"hisse": "<script>"}) == "/haberler/bildirimler"


def test_gundem_kap_item_has_no_internal_rule_wording():
    """O29/C-74: 'kapsamdaki' ve '(rutin duyurular hariç)' iç kural dili Gündem'de görünmez."""
    items = _items()
    snap = _snap()
    stocks = [{"ticker": r["t"], "change_pct": r["ch"]["d1"], "sector": r["g"], "signal": "BEKLE"} for r in snap["rows"]]
    macro = [{"label": "USDTRY", "price": 49.03, "change": 0.01}, {"label": "SP500", "price": 7645.64, "change": -0.1},
             {"label": "PETROL", "price": 100.89, "change": 2.92}]
    now = datetime(2026, 10, 1, 19, 30)
    doc = hg.build_print(stocks, macro, {"close": 12249.04, "change_pct": 2.53}, items, {}, [], now,
                         date(2026, 10, 1), "aksam", members=[r["t"] for r in snap["rows"]],
                         sectors=bulten.isi_haritasi_ozet(snap), counts=snap["counts"])
    kap = [x for g in doc["groups"] for x in g["items"] if x["id"] == "bildirim"][0]
    n = sum(1 for x in items if x["ts"][:10] == "2026-10-01" and not x.get("rutin"))
    assert kap["p"].startswith("1 Ekim tarihinde %d şirket bildirimi. " % n)
    assert not re.search(r"kapsam|rutin|hariç|elendi|gizli", json.dumps(doc, ensure_ascii=False), re.I)


# ----------------------------------------------------------------------------- inceleme P1-6 (taslak gorselleri)

def _kredi_docs():
    with open(os.path.join(FX, "kredi_docs.json"), encoding="utf-8") as f:
        return {int(k): v for k, v in json.load(f).items()}


def test_rating_view_from_filing_text():
    """Kredi notu basamaklari bildirimin kendi metninden (kod; 28.09-01.10 canli KAP metinleri)."""
    docs = _kredi_docs()
    z = hv.rating_view(docs[1669189]["text"])            # ZOREN Fitch B- revize + RWN
    assert z["agency"] == "Fitch" and z["at"] == "B−" and z["scale"][z["at_i"]] == "B−" and len(z["scale"]) == 7
    assert z["tag"] == "Negatif izleme" and z["tag_dir"] == "down" and z["changed"] is True
    assert z["dir"] is None and z["prev"] is None        # yon metinde yok -> yazilmaz
    v = hv.rating_view(docs[1671026]["text"])            # VESTL Moody's Caa3 -> Ca
    assert v["agency"] == "Moody's" and (v["prev"], v["at"], v["dir"]) == ("Caa3", "Ca", "down")
    assert v["scale"][v["prev_i"]] == "Caa3" and v["tag"] == "Görünüm negatif" and v["changed"] is True
    g = hv.rating_view(docs[1670455]["text"])            # GARAN JCR AAA (tr) teyit
    assert g["at"] == "AAA (tr)" and g["national"] and g["at_i"] == 0 and g["changed"] is False
    assert g["lab"] == "JCR · ulusal not basamakları" and g["tag"] == "Görünüm stabil"
    assert hv.rating_view(docs[1670442]["text"]) is None  # not yalniz ekte (PDF)
    assert hv.rating_view("") is None and hv.rating_view("Fitch notu hakkında") is None


def test_company_cards_kredi_rating_and_hot_rule():
    docs = _kredi_docs()
    items = [_it("Kredi Derecelendirmesi", "Fitch Ratings Kredi Derecelendirme Notu", id=1669189, ticker="ZOREN",
                 tickers=["ZOREN"], ts="2026-09-28T19:32:16"),
             _it("Kredi Derecelendirmesi", "JCR Kredi Derecelendirme Notu Hakkında", id=1670455, ticker="GARAN",
                 tickers=["GARAN"], ts="2026-09-28T18:23:30")]
    cards = hv.company_cards(items, "2026-09-28", {}, n=6, doc_fn=lambda i: docs.get(i))
    by = {c["ticker"]: c for c in cards}
    assert by["ZOREN"]["rating"]["at"] == "B−" and by["ZOREN"]["hot"] is True     # degisiklik -> Öne çıkan
    assert by["GARAN"]["rating"]["at"] == "AAA (tr)" and by["GARAN"]["hot"] is False  # teyit
    assert [c["ticker"] for c in cards] == ["ZOREN", "GARAN"]                    # Öne çıkan once
    # metin okunamazsa kart yine cikar (cizgiyle)
    cards2 = hv.company_cards(items, "2026-09-28", {}, n=6, doc_fn=lambda i: 1 / 0)
    assert all(c["rating"] is None and c["hot"] is False for c in cards2)
    # Öne çıkan (degisen not) onemsiz sozlesme bildirimlerinin onunde
    small = [_it("Yeni İş İlişkisi", "Sözleşme imzalanması", id=7, ticker="QUAGR", tickers=["QUAGR"],
                 ts="2026-09-28T20:00:00", onem={"pct": 0.9})]
    order = [c["ticker"] for c in hv.company_cards(small + items, "2026-09-28", {}, doc_fn=lambda i: docs.get(i))]
    assert order == ["ZOREN", "QUAGR", "GARAN"]


def test_onem_two_bar_view_when_ratio_exceeds_scale():
    o = {"pct": 290.4, "approx": False, "basis": "Sözleşme tutarı / 2025 hasılatı", "amount_txt": "1.000.000.000 ₺",
         "amount_try": 1.0e9, "rev_year": 2025, "rev": 344.4e6, "fx": None}
    v = hv.onem_view(o)
    assert v["vis"] == "bars" and [b["l"] for b in v["bars"]] == ["Sözleşme tutarı", "2025 hasılatı"]
    assert v["bars"][0]["w"] == 100.0 and v["bars"][1]["w"] == 34.4 and v["bars"][1]["t"] == "344,4 Mn ₺"
    assert hv.onem_view(dict(o, pct=16.1, amount_try=137.7e6, rev=855.1e6))["vis"] == "ratio"


def test_gundem_states_flow_from_bulten_transitions():
    trans = [{"ticker": "THYAO", "onceki": "Güçlü Trend", "yeni": "Trend Bozuldu"},
             {"ticker": "TSKB", "onceki": "Güçlü Trend", "yeni": "Trend Bozuldu"},
             {"ticker": "AHGAZ", "onceki": "Güçlü Trend", "yeni": "Yatay"},
             {"ticker": "ASELS", "onceki": "Yatay", "yeni": "Güçlü Trend"},
             {"ticker": "X", "onceki": "Yatay", "yeni": "Yatay"}]
    stocks = [{"ticker": "ASELS", "change_pct": 3.1, "borsapusula_skoru": 70}]
    it = hg._item_states(stocks, date(2026, 9, 28), trans)
    assert it["v"]["k"] == "flow" and it["h"] == "28 Eylül kapanışında 4 hissenin trend durumu değişti"
    assert it["v"]["rows"][0] == {"a": "Güçlü Trend", "as": "g", "b": "Trend Bozuldu", "bs": "b", "n": 2}
    assert sum(r["n"] for r in it["v"]["rows"]) == 4 and it["chips"][0]["t"] == "ASELS"
    assert "Güçlü Trend'e geçen: 1 · Yatay'a dönen: 1 · Trend Bozuldu'ya geçen: 2." == it["p"]
    assert not FORBIDDEN.search(it["h"] + it["p"])
    # degisim yoksa eski (sinyal tarihli) madde
    assert hg._item_states([], date(2026, 9, 28), []) is None
