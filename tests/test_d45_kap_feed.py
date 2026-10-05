"""D-45: KAP akisi (kap_feed) + Gundem (haber_gundem) birim testleri -- ag yok.

Fixture'lar 24.09.2026 gercek KAP yanitlarindan (tests/fixtures/kap_feed):
- kap_liste_ornek.json: byCriteria satirlari (evren sorgusu 23-24.09 + AHGAZ 07-09.2026 + GARAN FR)
- flat_<id>.txt.gz: bildirim sayfasinin kap_financials._flat ciktisi (govde kesiti)
- kap_fin/<T>.json: D-40a0 sema-1 kaydinin en kucuk hali (hasilat = onayli taslak verisi, 2025)
- rss/*.xml: AA ekonomi, TRT dunya, Dunya finans beslemelerinden ilk maddeler
"""
from __future__ import annotations

import gzip
import json
import os
import re
import sys
from datetime import date, datetime

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import haber_gundem as hg  # noqa: E402
import kap_feed as kf  # noqa: E402

FX = os.path.join(ROOT, "tests", "fixtures", "kap_feed")
KAP_FIN = os.path.join(FX, "kap_fin")
UNIVERSE = {"AHGAZ", "ENERY", "ULKER", "KATMR", "PEKGY", "AKBNK", "AKCNS", "ASTOR", "EKGYO", "FORTE",
            "THYAO", "MIATK", "ORGE", "ESCOM", "ZOREN", "NTHOL", "USAK", "ANELE", "ASELS", "LINK", "GARAN",
            "HEKTS", "CWENE", "BERA", "QUAGR", "TCKRC", "MAKTK", "KARTN", "FORMT", "SASA", "MRGYO", "PSGYO",
            "LKMNH", "TBORG", "ESCOM", "FZLGY", "YKBNK", "ZOREN", "AKSA", "TUPRS", "BIMAS", "GUBRF",
            "BOSSA", "MERCN", "ISMEN"}
FORBIDDEN = re.compile(r"\b(AL|SAT|BEKLE|TP1|TP2|hedef|potansiyel|tavsiye|fırsat|kâr al|bugün|dün|yarın|"
                       r"Ücretsiz|Kaynak:|KAP'ta aç)\b", re.I)


def _rows():
    with open(os.path.join(FX, "kap_liste_ornek.json"), encoding="utf-8") as f:
        return json.load(f)


def _row(idx):
    return next(r for r in _rows() if r["disclosureIndex"] == idx)


def _detail(idx):
    with gzip.open(os.path.join(FX, "flat_%d.txt.gz" % idx), "rt", encoding="utf-8") as f:
        return kf.parse_detail(f.read())


# ----------------------------------------------------------------------------- kodlama temizligi

def test_encoding_apostrophe_and_trailing_newline():
    raw = _row(1625024)["summary"]
    assert "?nin" in raw and raw.endswith("\n")          # KAP'in kendi verisi boyle
    t = kf.clean_title(raw)
    assert t == "Dünya Katılım Bankası A.Ş.'nin Halka Arz Çalışmalarının Başlatılması hakkında"
    assert kf.clean_text("TSK Bulut Bilişim 2?nci Veri Merkezi") == "TSK Bulut Bilişim 2'nci Veri Merkezi"
    assert kf.clean_text("Türkiye?de yatırım") == "Türkiye'de yatırım"
    assert kf.clean_text("Görüşüldü mü? Evet") == "Görüşüldü mü? Evet"   # gercek soru isareti kalir
    assert kf.clean_text("24.09.2026 Tarihli Pay Geri Alım İşlemleri\n") == "24.09.2026 Tarihli Pay Geri Alım İşlemleri"
    # K20(c): KAP'ın en-tiresi bazı basliklarda "?" olarak geliyor (ARENA/GARAN, 21.120 kayittan 2'si)
    assert kf.clean_title("Finansal Rapor Dönemi: 1 Nisan 2025 ? 31 Mart 2026 hk.") == \
        "Finansal Rapor Dönemi: 1 Nisan 2025 – 31 Mart 2026 hakkında"


# ----------------------------------------------------------------------------- uye esleme

def test_member_mapping_other_members_notice_not_attached():
    # Dunya Katilim Bankasi'nin sube bildirimi AHGAZ/ENERY'yi "ilgili sirket" listeler: hisseye yazilmaz
    r = _row(1648987)
    assert r["relatedStocks"] == "AHGAZ, ENERY" and r["stockCodes"] == "ADA"
    assert kf.normalize(r, UNIVERSE) is None
    # AHGAZ'in kendi bildirimi (Dunya Katilim hakkinda olsa da) AHGAZ'indir
    it = kf.normalize(_row(1625024), UNIVERSE)
    assert it["ticker"] == "AHGAZ" and it["via"] == "own"
    # ucuncu taraf ama sirketin KENDISI hakkinda: kredi notu (JCR), pay alim teklifi (TEB -> AKCNS)
    jcr = kf.normalize(_row(1667330), UNIVERSE)
    assert jcr["ticker"] == "ULKER" and jcr["via"] == "related" and jcr["class"] == "Kredi notu"
    teklif = kf.normalize(_row(1667902), UNIVERSE)
    assert teklif["ticker"] == "AKCNS" and not teklif["rutin"] and teklif["class"] == "Pay alım teklifi"
    # ucuncu tarafin genel ozel durum aciklamasi (Dogru Varlik -> Akbank portfoyu) hisseye yazilmaz
    assert kf.normalize(_row(1667792), UNIVERSE) is None


def test_member_mapping_publisher_codes_win_and_evren_disi_dropped():
    r = dict(_row(1666965), stockCodes="XXXXX", relatedStocks=None)
    assert kf.normalize(r, UNIVERSE) is None
    garan = kf.normalize(next(r for r in _rows() if r.get("stockCodes") == "GARAN, TGB"), UNIVERSE)
    assert garan["ticker"] == "GARAN" and garan["tickers"] == ["GARAN"]


# ----------------------------------------------------------------------------- sinif / rutin

def test_routine_and_filters():
    by = {}
    for r in _rows():
        it = kf.normalize(r, UNIVERSE)
        if it:
            by[it["id"]] = it
    geri = by[1667897]
    assert geri["rutin"] and geri["group"] == "Pay geri alımı işlemleri" and geri["filter"] is None
    assert by[1667135]["rutin"]            # "Pay Geri Alim Programi hakkinda" (baslatma degil)
    temerrut = [x for x in by.values() if x["subject"] == "Temerrüt İşlemi"][0]
    assert temerrut["rutin"] and temerrut["group"] == "Borsa duyuruları" and temerrut["ticker"] == "LINK"
    devre = [x for x in by.values() if x["subject"].startswith("Pay Bazında Devre Kesici")][0]
    assert devre["rutin"]
    form = [x for x in by.values() if x["kap_class"] == "DG"][0]
    assert form["rutin"] and form["group"] == "Formlar ve raporlar"
    tsrs = [x for x in by.values() if x["subject"].startswith("TSRS")][0]
    assert tsrs["rutin"]
    fr = [x for x in by.values() if x["subject"] == "Finansal Rapor"][0]
    assert not fr["rutin"] and fr["filter"] == "bilanco" and fr["class"] == "Finansal rapor"
    assert by[1667900]["filter"] == "temettu" and by[1667900]["class"] == "Temettü"
    assert by[1667046]["rutin"] and by[1667046]["group"] == "Borçlanma aracı işlemleri"  # itfa/kupon
    assert by[1666965]["filter"] == "ozel" and by[1666965]["class"] == "Yeni iş ilişkisi"
    assert kf.routine_group("ODA", "Payların Geri Alınmasına İlişkin Bildirim",
                            "Pay Geri Alım Programının Başlatılması hakkında") is None


# ----------------------------------------------------------------------------- metin + tutar + onem

def test_parse_detail_fields_text_and_turkish_only():
    d = _detail(1667023)
    labels = dict(d["fields"])
    assert labels["İhale Bedeli"] == "31.900.000 TL"
    assert labels["İhale Sonucu"] == "Şirketimiz uhdesinde kalmıştır."
    assert "The material procurement" not in d["text"]        # Ingilizce kisim atilir
    assert d["resp"].startswith("Yukarıdaki açıklamalarımızın")
    astor = _detail(1666965)
    assert dict(astor["fields"])["Yeni İş İlişkisine Başlanan/Başlanacak Kişinin Niteliği"] == "Müşteri"
    assert "Our Company" not in astor["text"] and "33.781.500 ABD Doları" in astor["text"]
    kar = _detail(1667900)                                      # alansiz form: satirlar
    assert not kar["fields"] and "Nakit Kar Payı Ödeme Şekli" in kar["lines"]
    assert d["ekler"] == []                                     # fixture onceden flatten edilmis (href yok)


def test_parse_attachments_extracts_from_raw_html_and_dedupes():
    # CPO-1824: ek (PDF) baglantilari _flat() tarafindan silinir -- bu yuzden parse_attachments
    # ham page_html uzerinde calisir. Her ek sayfada genellikle 2 kez gorunur (ust panel + liste).
    html = (
        '<a class="x" target="_blank" href="https://www.kap.org.tr/tr/api/file/download/abc123">'
        'Ek_1_AKCNS Pay Alım Formu.pdf</a>'
        '<a class="y" target="_blank" href="https://www.kap.org.tr/tr/api/file/download/abc123">'
        'Ek_1_AKCNS Pay Alım Formu.pdf</a>'
        '<a class="z" target="_blank" href="https://www.kap.org.tr/tr/api/file/download/def456">'
        'AKCNS - PAT Bilgilendirme Formu.pdf</a>'
    )
    assert kf.parse_attachments(html) == [
        {"ad": "Ek_1_AKCNS Pay Alım Formu.pdf", "url": "https://www.kap.org.tr/tr/api/file/download/abc123"},
        {"ad": "AKCNS - PAT Bilgilendirme Formu.pdf", "url": "https://www.kap.org.tr/tr/api/file/download/def456"},
    ]
    assert kf.parse_detail(html)["ekler"] == kf.parse_attachments(html)


def test_parse_detail_inlines_data_tables_and_merges_bullets():
    # K20(a): oda_ alani olmayan bildirimlerde (Pay Alim Teklifi/Birlesme/Sermaye Artirimi)
    # gelen <table border="1"> govdesi flat() ile once tum basliklar sonra tum degerler
    # olarak tek tek satira dusuyordu (BERA/AKCNS 30.09 canli ornekleri). Artik "Baslik:
    # Deger" tek satira cevrilir; coklu veri satirlari '•' ile ayrilir.
    html = (
        '<div>Özet Bilgi</div><div>x</div>'
        '<table border="1"><tbody>'
        '<tr><td><div>Pay Grup Bilgileri</div></td><td><div>Nevi</div></td>'
        '<td><div>Fiyat</div></td></tr>'
        '<tr><td><div>AKCNS</div></td><td><div>Nâma</div></td><td><div>274,24</div></td></tr>'
        '</tbody></table>'
        '<div>Sermaye Artırımı</div>'
        '<table class="totalTableStyle mTB20"><tbody>'
        '<tr><td><div></div></td><td><div>Mevcut Sermaye</div></td><td><div>Ulaşılacak</div></td></tr>'
        '<tr><td><div>TOPLAM</div></td><td><div>1.400.000.000</div></td><td><div>3.780.000.000</div></td></tr>'
        '</tbody></table>'
        '<div>•</div><div>Bağlayıcı Sözleşme uyarınca fiyat belirlenmiştir.</div>'
        '<div>Kamuoyuna saygıyla duyurulur.</div>'
    )
    d = kf.parse_detail(html)
    assert not d["fields"]                              # oda_ alani yok -> "lines" yolu
    assert "Pay Grup Bilgileri: AKCNS; Nevi: Nâma; Fiyat: 274,24" in d["lines"]
    assert "TOPLAM; Mevcut Sermaye: 1.400.000.000; Ulaşılacak: 3.780.000.000" in d["lines"]
    assert "• Bağlayıcı Sözleşme uyarınca fiyat belirlenmiştir." in d["lines"]
    # eski davranista her hucre ayri satirdi (baslik/deger karisik) -- artik tek basina yok
    assert "Pay Grup Bilgileri" not in d["lines"]
    assert "Nevi" not in d["lines"]


@pytest.mark.parametrize("idx,subject,title,exp", [
    (1666965, "Yeni İş İlişkisi", "Yeni İş İlişkisi", (1646250192.45, "TRY", "tl_karsiligi")),
    (1667396, "Özel Durum Açıklaması (Genel)", "İstanbul Eyüpsultan Hasdal 2. Etap İhalesi 2. Oturum Sonucu",
     (17013200000.0, "TRY", "sirket_payi")),
    (1667023, "İhale Süreci / Sonucu", "İhale bildirimi", (31900000.0, "TRY", "alan")),
    (1666913, "Özel Durum Açıklaması (Genel)", "TSK Bulut Bilişim 2'nci Veri Merkezi Yapım İşi Projesi Kapsamında "
     "Sözleşme İmzalanması hakkında", (931200.0, "USD", "metin")),
    (1667919, "Yeni İş İlişkisi", "Bodrum Hillside Hotel Projesine ilişkin sözleşme bedeli artışı", None),
    (1667339, "Özel Durum Açıklaması (Genel)", "Ortaklığımızın Stratejik Planı Çerçevesindeki Uçak Siparişleri", None),
    (1625024, "Özel Durum Açıklaması (Genel)", "Dünya Katılım Bankası A.Ş.'nin Halka Arz Çalışmalarının Başlatılması", None),
])
def test_pick_amount(idx, subject, title, exp):
    got = kf.pick_amount(subject, title, _detail(idx))
    if exp is None:
        assert got is None                     # belirsiz (ORGE: 3 tutar) ya da tutarsiz -> tahmin yok
    else:
        assert (round(got["value"], 2), got["cur"], got["kind"]) == exp


def test_pick_amount_prefers_toplam_over_nominal_beher():
    # K20(b): Nominal/Beher/Sermaye alanlari toplam tutarin onune gecmemeli (BERA %0,0 -> %1,3 vakasi).
    detail = {"fields": [["Nominal Bedeli", "10 TL"], ["Beher Pay Fiyatı", "12,50 TL"],
                          ["Toplam Tutar", "228.000.000 TL"]], "text": ""}
    got = kf.pick_amount("Yeni İş İlişkisi", "x", detail)
    assert (got["value"], got["cur"]) == (228000000.0, "TRY")
    # Toplam alani yoksa Nominal/Beher HARIC ilk uygun alana duser (once buldugu duzeltilmis)
    detail2 = {"fields": [["Nominal Bedeli", "10 TL"], ["İhale Bedeli", "31.900.000 TL"]], "text": ""}
    got2 = kf.pick_amount("İhale Süreci / Sonucu", "x", detail2)
    assert (got2["value"], got2["cur"]) == (31900000.0, "TRY")


def test_onem_ratio_try_fx_and_missing():
    rev = kf.annual_revenue("ASTOR", KAP_FIN)
    assert rev == {"fy": 2025, "value": 35290000.0 * 1000}
    am = kf.pick_amount("Yeni İş İlişkisi", "Yeni İş İlişkisi", _detail(1666965))
    o = kf.compute_onem(am, rev, "Yeni İş İlişkisi")
    assert o["txt"] == "%4,7" and not o["approx"] and o["rev_year"] == 2025
    assert o["formula"] == "sözleşme / yıllık hasılat = %4,7"
    assert o["basis"] == "Sözleşme tutarı / 2025 hasılatı" and o["rev_txt"] == "35,3 Mrd ₺"
    ek = kf.compute_onem(kf.pick_amount("Özel Durum Açıklaması (Genel)", "İhalesi", _detail(1667396)),
                         kf.annual_revenue("EKGYO", KAP_FIN), "Özel Durum Açıklaması (Genel)")
    assert ek["txt"] == "%17,0" and ek["formula"].startswith("şirket payı / yıllık hasılat")
    usd = kf.pick_amount("Özel Durum Açıklaması (Genel)", "Sözleşme İmzalanması", _detail(1666913))
    assert kf.compute_onem(usd, kf.annual_revenue("MIATK", KAP_FIN), "Özel Durum Açıklaması (Genel)") is None
    mi = kf.compute_onem(usd, kf.annual_revenue("MIATK", KAP_FIN), "Özel Durum Açıklaması (Genel)",
                         fx_rate=48.7499, fx_date="2026-09-23")
    assert mi["approx"] and mi["txt"] == "~%1,6" and mi["fx"]["rate_txt"] == "48,75"
    assert kf.annual_revenue("GARAN", KAP_FIN) is None          # banka: hasilat yok -> oran yok
    assert kf.annual_revenue("YOKYOK", KAP_FIN) is None         # kayit yok -> None (tahmin yok)
    assert kf.compute_onem(am, None, "Yeni İş İlişkisi") is None


def test_bilanco_for_cpo1816_3_sayi_tek_cumle():
    # Sanayi (ASTOR idx 4): hasilat + net kar + faaliyet nakit dolu, net kar cumlesi oncelikli.
    b = kf.bilanco_for("ASTOR", 4, KAP_FIN)
    assert b["donem"] == "2026 ilk yarı"
    assert b["hasilat"] == 21174000000 and b["net_kar"] == 3000000000 and b["faaliyet_nakit"] == 2800000000
    assert b["degisim"]["net_kar_pct"] == 20.0
    assert b["cumle"] == "Net kâr önceki yılın aynı dönemine göre %20,0 arttı."
    # Banka (GARAN idx 4): net kar yok -> cumle "net faiz geliri" etiketiyle, faaliyet_nakit None.
    bk = kf.bilanco_for("GARAN", 4, KAP_FIN)
    assert bk["hasilat"] == 5000000000 and bk["net_kar"] is None and bk["faaliyet_nakit"] is None
    assert bk["cumle"] == "Net faiz geliri önceki yılın aynı dönemine göre %25,0 arttı."
    # Kismi veri (EKGYO idx 2): hasilat var, karsilastirma/net kar yok -> genel cumle, 500 yok.
    part = kf.bilanco_for("EKGYO", 2, KAP_FIN)
    assert part["hasilat"] == 99829173000 and part["net_kar"] is None
    assert part["degisim"] == {"hasilat_pct": None, "net_kar_pct": None}
    assert part["cumle"] == "2025 dönemi finansal raporu yayımlandı."
    # Rapor bulunamadi / kayit yok -> None (kart cizilmez).
    assert kf.bilanco_for("ASTOR", 999, KAP_FIN) is None
    assert kf.bilanco_for("YOKYOK", 1, KAP_FIN) is None


def test_bilanco_for_cpo1820_onceki_ve_etiket():
    # Sanayi (ASTOR idx 4): onceki donem TL'ye cevrilmis, etiket "Hasılat".
    b = kf.bilanco_for("ASTOR", 4, KAP_FIN)
    assert b["onceki"] == {"hasilat": 18000000000, "net_kar": 2500000000}
    assert b["etiket"] == "Hasılat"
    # Banka (GARAN idx 4): etiket "Net faiz geliri", net kar yok -> onceki.net_kar None.
    bk = kf.bilanco_for("GARAN", 4, KAP_FIN)
    assert bk["onceki"] == {"hasilat": 4000000000, "net_kar": None}
    assert bk["etiket"] == "Net faiz geliri"
    # Kismi veri (EKGYO idx 2): prev None -> onceki tamami None.
    part = kf.bilanco_for("EKGYO", 2, KAP_FIN)
    assert part["onceki"] == {"hasilat": None, "net_kar": None}


def test_public_item_attaches_bilanco_only_for_finansal_rapor():
    it = kf.normalize(_row(1666965), UNIVERSE)   # Yeni İş İlişkisi -- Finansal Rapor degil
    assert "bilanco" not in kf.public_item(it, {}, KAP_FIN)
    fr = dict(it, subject="Finansal Rapor", ticker="ASTOR", id=4, tickers=["ASTOR"])
    pub = kf.public_item(fr, {}, KAP_FIN)
    assert pub["bilanco"]["net_kar"] == 3000000000
    missing = dict(it, subject="Finansal Rapor", ticker="ASTOR", id=12345, tickers=["ASTOR"])
    assert kf.public_item(missing, {}, KAP_FIN)["bilanco"] is None


def test_summary_sentence_rule_based_descriptive():
    it = kf.normalize(_row(1666965), UNIVERSE)
    am = kf.pick_amount(it["subject"], it["title"], _detail(1666965))
    o = kf.compute_onem(am, kf.annual_revenue("ASTOR", KAP_FIN), it["subject"])
    s = kf.summary_sentence(it, "Astor Enerji", o)
    assert s.startswith("Astor Enerji, 23 Eylül 2026 tarihinde yeni iş ilişkisi bildirimi yayımladı.")
    assert "1.646.250.192,45 ₺" in s and "2025 hasılatına oranı %4,7" in s
    assert not FORBIDDEN.search(s)
    # K20(d): baslik sayfa H1'inde zaten gorundugu icin ozette yinelenmez
    th = kf.normalize(_row(1667339), UNIVERSE)
    s2 = kf.summary_sentence(th, "Türk Hava Yolları")
    assert s2 == "Türk Hava Yolları, 23 Eylül 2026 tarihinde özel durum bildirimi yayımladı."
    assert "Ortaklığımızın Stratejik Planı" not in s2 and not FORBIDDEN.search(s2)


# ----------------------------------------------------------------------------- depo + sorgu + eski bicim

def _store(tmp_path):
    st = kf.Store(str(tmp_path / "kap_feed"))
    items = [x for x in (kf.normalize(r, UNIVERSE) for r in _rows()) if x]
    st.merge(items, today=date(2026, 9, 25))
    return st, items


def test_store_merge_sorted_atomic_and_keeps_enrichment(tmp_path):
    st, items = _store(tmp_path)
    assert st.available()
    got = st.all_items()
    assert [x["ts"] for x in got] == sorted([x["ts"] for x in got], reverse=True)
    assert {x["id"] for x in got} == {x["id"] for x in items}
    one = dict(st.get(1666965), onem={"pct": 4.66}, ozet="x", doc=True)
    st.merge([one], today=date(2026, 9, 25))
    again = kf.normalize(_row(1666965), UNIVERSE)            # yeni tur: liste kaydi zenginlestirmesiz gelir
    st.merge([again], today=date(2026, 9, 25))
    assert st.get(1666965)["onem"] == {"pct": 4.66} and st.get(1666965)["ozet"] == "x"
    assert not [n for n in os.listdir(st.items_dir) if n.startswith(".tmp_")]


def test_store_prune_duy_after_30_days_and_old_months(tmp_path):
    st, _ = _store(tmp_path)
    assert [x for x in st.all_items() if x["kap_class"] == "DKB"]  # DUY sorgusu 'DKB' sinifiyla doner
    st.prune(date(2026, 11, 1))                             # borsa duyurulari 30 gunden eski -> duser
    assert not [x for x in st.all_items() if x["kap_class"] not in kf.COMPANY_CLASSES]
    assert [x for x in st.all_items() if x["kap_class"] == "ODA"]
    st.prune(date(2027, 12, 1))                             # 400 gunden eski parca silinir
    assert st.all_items() == [] or all(x["ts"] >= "2026-10" for x in st.all_items())


def test_query_pagination_filters_and_routine_hidden(tmp_path):
    st, _ = _store(tmp_path)
    allx = st.all_items()
    q = kf.query(allx, page=1, per_page=5)
    assert q["total"] == len([x for x in allx if not x["rutin"]]) and len(q["items"]) == 5
    assert q["routine_hidden"] == len([x for x in allx if x["rutin"]])
    assert all(x["filter"] == "temettu" for x in kf.query(allx, filt="temettu")["items"])
    assert kf.query(allx, tickers=["AHGAZ"], include_rutin=True)["total"] >= 2
    last = kf.query(allx, page=99, per_page=5)
    assert last["page"] == last["pages"]
    pub = kf.public_item(allx[0], {"ASTOR": "Astor Enerji"})
    assert "_src" not in pub and "via" not in pub and pub["href"].startswith("/hisse/")
    assert "kap.org.tr" not in json.dumps(pub)                # akis API'sinde dis baglanti yok


def test_for_ticker_one_year_and_legacy_shape(tmp_path):
    st, _ = _store(tmp_path)
    rows = kf.legacy_rows(kf.for_ticker(st.all_items(), "AHGAZ", days=365, today=date(2026, 9, 25)))
    ids = [r["index"] for r in rows]
    assert 1625024 in ids and 1648987 not in ids              # Temmuz kaydi var (90 gun sinirini asar)
    r = next(r for r in rows if r["index"] == 1625024)
    assert r["date"] == "06.07.2026 16:31:26" and r["summary"].endswith("hakkında")
    assert set(r) >= {"date", "summary", "subject", "class", "type", "index", "url", "late", "href", "rutin"}
    assert kf.for_ticker(st.all_items(), "AHGAZ", days=30, today=date(2026, 9, 25)) != []
    assert all(x["kap_class"] in ("ODA", "FR") for x in kf.for_ticker(st.all_items(), "LINK"))


def test_day_counts_company_classes_only(tmp_path):
    st, _ = _store(tmp_path)
    c = kf.day_counts(st.all_items(), "2026-09-24")
    raw = [x for x in st.all_items() if x["ts"][:10] == "2026-09-24"]
    assert c["total"] == len([x for x in raw if x["kap_class"] in kf.COMPANY_CLASSES]) < len(raw)
    assert c["routine"] == len([x for x in raw if x["kap_class"] in kf.COMPANY_CLASSES and x["rutin"]])


def test_day_counts_respects_active_filt_and_tickers(tmp_path):
    # K40: '?hisse=THYAO' sayfasinda gun basligi butun akisin toplamini degil,
    # o hissenin (ve aktif ?tur= filtresinin) o gunku satir sayisini gostermeli.
    st, _ = _store(tmp_path)
    allx = st.all_items()
    day = next(x["ts"][:10] for x in allx if x["kap_class"] in kf.COMPANY_CLASSES)
    unfiltered = kf.day_counts(allx, day)
    only_ahgaz = kf.day_counts(allx, day, tickers=["AHGAZ"])
    expect = len([x for x in allx if x["ts"][:10] == day and x["kap_class"] in kf.COMPANY_CLASSES
                  and "AHGAZ" in (x.get("tickers") or [x["ticker"]])])
    assert only_ahgaz["total"] == expect < unfiltered["total"]
    only_temettu = kf.day_counts(allx, day, filt="temettu")
    assert only_temettu["total"] == len([x for x in allx if x["ts"][:10] == day
                                         and x["kap_class"] in kf.COMPANY_CLASSES and x["filter"] == "temettu"])


def test_day_labels_absolute_dates():
    assert kf.day_label("2026-09-24") == "24 Eylül Perşembe"
    assert kf.date_long("2026-09-23T09:15:00") == "23 Eylül 2026"
    days = kf.group_by_day([{"ts": "2026-09-24T10:00:00"}, {"ts": "2026-09-24T09:00:00"}, {"ts": "2026-09-23T18:00:00"}])
    assert [d["label"] for d in days] == ["24 Eylül Perşembe", "23 Eylül Çarşamba"]


def test_tcmb_parse():
    xml = ('<Currency CrossOrder="0" Kod="USD" CurrencyCode="USD"><Unit>1</Unit><ForexBuying>48.7499</ForexBuying>'
           '</Currency><Currency CrossOrder="9" Kod="EUR" CurrencyCode="EUR"><ForexBuying>55.6521</ForexBuying></Currency>')
    assert kf.parse_tcmb(xml) == {"USD": 48.7499, "EUR": 55.6521}


class _FakeClient:
    def __init__(self, rows, pages):
        self.rows, self.pages, self.count = rows, pages, 0

    def disclosures(self, oids, frm, to, cls):
        self.count += 1
        return [r for r in self.rows if (r.get("disclosureClass") or "") == cls or
                (cls == "DUY" and r.get("disclosureClass") not in kf.COMPANY_CLASSES)]

    def page(self, idx):
        self.count += 1
        with gzip.open(os.path.join(FX, "flat_%d.txt.gz" % idx), "rt", encoding="utf-8") as f:
            return f.read()


def test_poll_once_enriches_new_nonroutine_with_docs(tmp_path):
    rows = [r for r in _rows() if r["disclosureIndex"] in (1666965, 1667023, 1667897, 1648987)]
    st = kf.Store(str(tmp_path / "kap_feed"))
    cl = _FakeClient(rows, None)
    stats = kf.poll_once(st, cl, ["oid"], UNIVERSE, {"ASTOR": "Astor Enerji", "FORTE": "Forte Bilgi"},
                         now=datetime(2026, 9, 24, 12, 0), max_docs=5, kap_fin_dir=KAP_FIN)
    assert stats["listed"] == 3 and stats["docs"] == 2          # rutin geri alim metni cekilmez
    astor = st.get(1666965)
    assert astor["onem"]["txt"] == "%4,7" and astor["doc"] and "Astor Enerji" in astor["ozet"]
    assert st.get(1667023)["onem"]["txt"] == "%1,3"
    assert st.doc(1666965)["fields"] and st.meta()["updated_at"] == "2026-09-24T12:00:00"
    kf.poll_once(st, cl, ["oid"], UNIVERSE, {}, now=datetime(2026, 9, 24, 12, 10), kap_fin_dir=KAP_FIN)
    assert cl.count == 4 + 2 + 4                                   # ikinci turda metin yeniden cekilmez


def test_backfill_months_resumes_after_stop(tmp_path):
    wins = kf.month_windows(12, date(2026, 9, 25))
    assert len(wins) == 13 and wins[0] == ("2025-09-01", "2025-09-30") and wins[-1] == ("2026-09-01", "2026-09-25")

    class Stopper(_FakeClient):
        def disclosures(self, oids, frm, to, cls):
            if frm == "2026-03-01":
                raise kf.KapStop("KAP HTTP 429")
            return super().disclosures(oids, frm, to, cls)
    st = kf.Store(str(tmp_path / "kap_feed"))
    with pytest.raises(kf.KapStop):
        kf.backfill_months(st, Stopper(_rows(), None), ["oid"], UNIVERSE, months=12, today=date(2026, 9, 25))
    assert st.meta()["backfilled"][-1] == "2026-02" and not st.meta().get("backfill_done")
    cl = _FakeClient(_rows(), None)
    kf.backfill_months(st, cl, ["oid"], UNIVERSE, months=12, today=date(2026, 9, 25))
    assert cl.count == 7 * 3 and st.meta()["backfill_done"]            # yalniz kalan 6 kapali ay + bu ay


# ----------------------------------------------------------------------------- Gundem

def _feed(name):
    with open(os.path.join(FX, "rss", name), "rb") as f:
        return f.read()


def test_gundem_input_parse_classify_and_sources_internal(tmp_path):
    aa = hg.parse_feed(_feed("aa_ekonomi.xml"), hg.SOURCES[0])
    dn = hg.parse_feed(_feed("dunya_finans.xml"), hg.SOURCES[3])
    assert aa and dn and all(x["src"]["url"].startswith("https://") for x in aa + dn)
    groups = {x["title"]: x["group"] for x in dn}
    assert groups["New York borsası düşüşle açıldı"] == "dunya"
    assert groups["Borsa İstanbul günü düşüşle tamamladı"] == "turkiye"
    trt = hg.parse_feed(_feed("trt_dunya.xml"), hg.SOURCES[6])
    assert all(hg._MARKET_RE.search(hg._lower_tr(x["title"] + " " + x["desc"])) for x in trt)  # siyaset elenir
    merged = hg.merge_input([], aa + dn)
    borsa = [x for x in merged if "günü düşüşle tamamladı" in x["title"]]
    assert borsa and max(x["independent_sources"] for x in borsa) == 2   # AA + Dunya ayni olay
    calls = []

    def get(url):
        calls.append(url)
        for n, f in (("aa.com.tr", "aa_ekonomi.xml"), ("trthaber", "trt_dunya.xml"), ("dunya.com", "dunya_finans.xml")):
            if n in url:
                return _feed(f)
        raise IOError("yok")
    status = hg.collect_input(get, now=datetime(2026, 9, 24, 20, 0), base_dir=str(tmp_path))
    assert len(calls) == len(hg.SOURCES) and str(status["Bloomberg HT"]).startswith("hata")
    assert hg.load_input("2026-09-24", str(tmp_path))["items"]


def _stocks():
    base = [("THYAO", "Ulaşım", 0.17, "BEKLE", "23.09.2026", 61), ("PGSUS", "Ulaşım", -0.73, "SAT", "24.09.2026", 50),
            ("TUPRS", "Enerji", 4.03, "AL", "24.09.2026", 70), ("AYGAZ", "Enerji", 1.10, "BEKLE", "01.09.2026", 55),
            ("ENJSA", "Enerji", 0.20, "BEKLE", "01.09.2026", 52), ("GARAN", "Bankacılık", -0.22, "BEKLE", "01.09.2026", 60),
            ("AKBNK", "Bankacılık", -0.27, "SAT", "24.09.2026", 48), ("YKBNK", "Bankacılık", -1.2, "BEKLE", "02.09.2026", 47),
            ("TAVHL", "Ulaşım", 0.0, "BEKLE", "02.09.2026", 58)]
    return [{"ticker": t, "sector": s, "change_pct": c, "signal": g, "signal_date": d, "borsapusula_skoru": b}
            for t, s, c, g, d, b in base]


MACRO = [{"label": "USDTRY", "price": 48.91, "change": 0.14}, {"label": "EURTRY", "price": 55.65, "change": -0.09},
         {"label": "ALTIN", "price": 4310.1, "change": -0.2}, {"label": "GUMUS", "price": 64.28, "change": -0.51},
         {"label": "PETROL", "price": 100.32, "change": 2.1}, {"label": "SP500", "price": 7704.13, "change": -0.02},
         {"label": "NASDAQ", "price": 26939.37, "change": 0.01}]
CAL = [{"date": "2026-10-22", "event": "TCMB Para Politikası Kurulu"}, {"date": "2026-10-28", "event": "Fed Faiz Kararı"},
       {"date": "2026-09-16", "event": "Fed Faiz Kararı"}]


def test_gundem_print_own_data_no_sources_no_relative_time(tmp_path):
    items = [x for x in (kf.normalize(r, UNIVERSE) for r in _rows()) if x]
    for x in items:
        if x["id"] == 1666965:
            x["onem"] = {"pct": 4.66, "formula": "sözleşme / yıllık hasılat = %4,7"}
    doc = hg.build_print(_stocks(), MACRO, {"close": 13251.85, "change_pct": 0.40}, items,
                         {"ASTOR": "Astor Enerji"}, CAL, datetime(2026, 9, 23, 19, 30), date(2026, 9, 23), "aksam")
    tr, world = doc["groups"][0]["items"], doc["groups"][1]["items"]
    assert 5 <= len(tr) + len(world) <= 8 and len(tr) >= 4 and len(world) >= 2
    assert doc["date_label"] == "23 Eylül" and doc["edition_label"] == "akşam baskısı" and doc["time"] == "19:30"
    assert tr[0]["h"] == "BIST100 %0,40 yükselişle 13.251,85 puanda kapandı"
    kap = [x for x in tr if x["id"] == "bildirim"][0]
    assert "Astor Enerji" in kap["h"] and "%4,7" in kap["p"]
    assert any(c["href"] == "/hisse/ASTOR/bildirim/1666965" for c in kap["chips"])
    assert [x for x in world if x["id"] == "abd"][0]["h"].startswith("ABD borsaları gün içinde")
    text = json.dumps(doc, ensure_ascii=False)
    assert not FORBIDDEN.search(text)
    assert not re.search(r"\b(AA|Anadolu Ajansı|TRT|Bloomberg|Reuters|KAP|Yahoo|kaynak)\b", text, re.I)
    assert "http" not in text                                  # dis baglanti yok; cipler site ici
    assert doc["next_label"] == "24 Eylül Perşembe 08:30"
    assert hg.next_print_label(datetime(2026, 9, 25, 19, 30), "aksam") == "28 Eylül Pazartesi 08:30"
    assert hg.next_print_label(datetime(2026, 9, 25, 8, 30), "sabah") == "25 Eylül Cuma 19:30"
    # K19: hafta sonu ilk kurulum baskısı "sabah" edition'ıyla gelebilir (app.py
    # load_latest() is None dalı takvim kontrolsüz basar) — aynı gün 19:30 hiç
    # gelmeyeceği için sonraki hafta içi 08:30'a düşmeli.
    assert hg.next_print_label(datetime(2026, 9, 26, 8, 56), "sabah") == "28 Eylül Pazartesi 08:30"  # cumartesi
    assert hg.next_print_label(datetime(2026, 9, 27, 10, 0), "sabah") == "28 Eylül Pazartesi 08:30"  # pazar
    assert hg.next_print_label(datetime(2026, 9, 27, 10, 0), "aksam") == "28 Eylül Pazartesi 08:30"  # pazar
    hg.save_print(doc, str(tmp_path))
    assert hg.load_latest(str(tmp_path))["edition"] == "aksam"
    assert hg.printed_keys(str(tmp_path)) == {"2026-09-23-aksam"}


def test_gundem_central_bank_item_both_calendar_shapes():
    old = [{"date": "2026-10-22", "event": "TCMB Para Politikası Kurulu"}, {"date": "2026-10-28", "event": "Fed Faiz Kararı"}]
    d24 = [{"date": "2026-10-07", "event": "Fed toplantı tutanağı"}, {"date": "2026-10-22", "event": "TCMB faiz kararı"},
           {"date": "2026-10-28", "event": "Fed faiz kararı"}]
    for cal in (old, d24):
        it = hg._item_cb(cal, date(2026, 9, 25))
        assert it["p"] == "Fed'in sonraki faiz kararı 28 Ekim; TCMB'nin sonraki faiz kararı 22 Ekim."
    assert hg._item_cb([], date(2026, 9, 25)) is None


def test_gundem_commod_weekend_wording():
    # K19: hafta sonu "gün içinde" değil "son kapanışta" (piyasa kapalı).
    it_wd = hg._item_commod(MACRO, datetime(2026, 9, 25, 19, 30))   # cuma
    it_we = hg._item_commod(MACRO, datetime(2026, 9, 26, 8, 56))    # cumartesi
    assert it_wd["h"].startswith("Brent petrol gün içinde")
    assert it_we["h"].startswith("Brent petrol son kapanışta")


def test_gundem_due_slot():
    assert hg.due_slot(datetime(2026, 9, 24, 8, 0), set()) is None
    assert hg.due_slot(datetime(2026, 9, 24, 8, 31), set()) == "sabah"
    assert hg.due_slot(datetime(2026, 9, 24, 19, 31), {"2026-09-24-sabah"}) == "aksam"
    assert hg.due_slot(datetime(2026, 9, 24, 21, 0), {"2026-09-24-aksam"}) is None
    assert hg.due_slot(datetime(2026, 9, 26, 10, 0), set()) is None       # cumartesi
