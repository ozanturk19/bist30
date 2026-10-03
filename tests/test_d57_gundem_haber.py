"""D-57 Gündem haber derlemesi (gundem_haber.py) — ağsız, Gemini'siz; kayıtlı (sahte) model yanıtlarıyla.

Girdi fikstürü 01.10.2026 VPS `data/gundem_girdi` dosyasından kırpıldı (35 başlık + 1 yapay SEO başlığı);
v1 baskısı aynı günün akşam baskısı; KAP satırları aynı günün gerçek kayıtları. Model yanıtları elle
yazıldı: içine uydurma cümle, yanlış sayı, yasak dil, kopya cümle/başlık, kaynakta olmayan hisse çipi,
gövdede kaynak adı ve yalnız KAP'a dayanan AI şirket cümlesi bilerek kondu.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import gundem_haber as gh  # noqa: E402

FX = os.path.join(ROOT, "tests", "fixtures", "gundem_haber")
NOW = datetime(2026, 10, 1, 21, 45)          # Perşembe, akşam baskısı (19:30 + 2 sa 15 dk)
NAMES = {"ASELS": "Aselsan Elektronik Sanayi", "OTKAR": "Otokar Otomotiv", "KARTN": "Kartonsan Karton Sanayii",
         "TKFEN": "Tekfen Holding A.Ş.", "AKBNK": "Akbank T.A.Ş.", "GARAN": "Garanti BBVA",
         "THYAO": "Türk Hava Yolları", "TUPRS": "Tüpraş Türkiye Petrol Rafinerileri"}
CONTRACT_KEYS = {"id", "kategori", "baslik", "ozet", "hisseler", "kaynaklar", "ai", "onemli"}
PUBS = {"AA": "aa.com.tr", "Dünya": "dunya.com", "TRT Haber": "trthaber.com", "Bloomberg HT": "bloomberght.com"}


def _read(name):
    with open(os.path.join(FX, name), encoding="utf-8") as f:
        return f.read()


def _json(name):
    return json.loads(_read(name))


class FakeModel(object):
    """Sırayla kayıtlı yanıtları döndürür; istemleri saklar. Ağ yok."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.prompts = []

    def __call__(self, prompt, max_tokens):
        self.prompts.append(prompt)
        assert max_tokens == gh.MAX_TOKENS
        return self.answers.pop(0) if self.answers else None


class FakeUsage(object):
    """gemini_budget sayaçlarının taklidi: her çağrı +1 ve +0,0012 $."""

    def __init__(self, model):
        self.model = model

    def __call__(self):
        n = len(self.model.prompts)
        return n, round(0.0012 * n, 6)


OK_BUDGET = {"enabled": True, "calls_today": 10, "daily_cap": 200, "usd_month": 0.02, "monthly_cap_usd": 5}


@pytest.fixture
def out(tmp_path, monkeypatch):
    monkeypatch.setattr(gh, "ENABLED", True)
    gh._CACHE.clear()
    return str(tmp_path / "gundem_haber")


def _run(out, model, **kw):
    args = dict(v1_doc=_json("v1_baski.json"), kap_items=_json("kap_items.json"), names=NAMES,
                universe=set(NAMES), budget_status=OK_BUDGET, cb_state={"open_until": 0.0},
                base_dir=out, input_dir=os.path.join(FX, "girdi"), usage_fn=FakeUsage(model))
    args.update(kw)
    return gh.run_edition(NOW, "aksam", model, **args)


def _ctx_ev():
    al = gh.company_aliases(NAMES, NAMES.keys())
    st = gh.window_start(NOW, "aksam")
    cands = gh.select_candidates(gh.load_inputs(NOW, st, os.path.join(FX, "girdi")), al)
    kaps = gh.kap_facts(_json("kap_items.json"), NAMES, st, NOW, set(t for c in cands for t in c["tickers"]))
    ev = gh.build_evidence(cands, gh.own_facts(_json("v1_baski.json")), kaps)
    return cands, ev, gh.Ctx(ev, gh.allowed_dates_for(NOW), al, NAMES.keys(), year=2026)


def _hid(ev, title_start):
    for k, v in ev.items():
        if v["kind"] == "H" and any(t.startswith(title_start) for t in v["titles"]):
            return k
    raise AssertionError(title_start)


# ----------------------------------------------------------------------------- aday seçimi

def test_window_drops_old_and_future_headlines():
    items = gh.load_inputs(NOW, gh.window_start(NOW, "aksam"), os.path.join(FX, "girdi"))
    titles = [i["title"] for i in items]
    assert not any(t.startswith("Merkez Bankası rezervleri 174,4") for t in titles)   # 24.09 tarihli bayat satır
    assert all(i["_t"] >= datetime(2026, 10, 1, 6, 30) for i in items)
    assert not any("&#039;" in (i["desc"] or "") for i in items)                      # çift kaçış çözüldü


def test_cluster_counts_publishers_not_feeds_and_keeps_events_apart():
    cands, ev, _ = _ctx_ev()
    tcmb = ev[_hid(ev, "TCMB, KOBİ")]
    assert sorted(tcmb["pubs"]) == ["AA", "Bloomberg HT", "Dünya", "TRT Haber"]
    brent_cn = ev[_hid(ev, "Petrol piyasasında Çin şoku")]
    assert list(brent_cn["pubs"]) == ["Dünya"]           # Dünya Ekonomi + Dünya Dünya = tek yayıncı
    ism, pmi = _hid(ev, "ABD'de ISM"), _hid(ev, "Euro Bölgesi imalat")
    assert ism != pmi                                    # ABD ISM ile Euro Bölgesi PMI ayrı olay


def test_seo_and_opinion_headlines_are_not_candidates():
    _, ev, _ = _ctx_ev()
    titles = [t for v in ev.values() for t in v["titles"]]
    assert not any(t.startswith("Dolar bugün ne kadar") for t in titles)
    assert not any(t.startswith("IMF'den kritik uyarı") for t in titles)


def test_previous_edition_headlines_are_skipped():
    al = gh.company_aliases(NAMES, NAMES.keys())
    items = gh.load_inputs(NOW, gh.window_start(NOW, "aksam"), os.path.join(FX, "girdi"))
    used = [i["id"] for i in items if "KOBİ" in i["title"] or i["title"].startswith("Merkez Bankası zorunlu")]
    cands = gh.select_candidates(items, al, used)
    assert not any("KOBİ" in c["rep"]["title"] for c in cands)


def test_prompt_material_ids_no_urls_and_size():
    cands, ev, _ = _ctx_ev()
    p = gh.build_prompt(cands, ev, NOW, "aksam")
    assert "H1 [Türkiye · 4 yayıncı]" in p and "\nF1 " in p and "\nK1 OTKAR" in p
    assert "http" not in p                               # bağlantılar modele gitmez, kod ekler
    assert "grounding" not in p.lower()
    assert len(p) < 40000


# ----------------------------------------------------------------------------- yardımcılar

def test_turkish_number_parsing_and_index_names():
    assert gh.parse_number("4.197,50") == 4197.5
    assert gh.parse_number("1.008.500.000") == 1008500000.0
    assert gh.parse_number("2.5") == 2.5
    assert [v for _, v, _, _ in gh.numbers("BIST100 %2,53, S&P 500 ve G20; 12.249,04 puan")] == [2.53, 12249.04]


def test_banned_language_filter():
    for bad, code in (("Bankacılıkta alım fırsatı", "al_sat"), ("Hisse için hedef fiyat 50 TL", "islem_dili"),
                      ("Stop seviyesi", "islem_dili"), ("Bugün piyasalar", "goreli_zaman"),
                      ("Geçen yıl büyüme", "goreli_zaman"), ("AA'nın haberine göre", "kaynak_govdede"),
                      ("Kulis bilgisine göre", "iddia"), ("Ücretsiz rapor", "gri"), ("THYAO için AL", "al_sat")):
        assert code in gh.banned_hits(bad), bad
    for ok in ("TCMB enflasyon hedefi", "Faiz indirimi beklentisi güçlendi", "Lagarde'dan yapay zeka uyarısı",
               "Rezervlerde düşüş beşinci haftaya uzandı", "Dünya Bankası raporu"):
        assert gh.banned_hits(ok) == [], ok


@pytest.mark.parametrize("bad", [
    "geçen yılın", "bu yılın", "gelecek yılın", "bugünden", "bugünün", "dünden", "yarından", "bu haftaki",
    "geçen haftaki", "geçen ayki", "geçtiğimiz hafta", "haftaya", "önceki gün", "önümüzdeki günlerde",
    "Bugünkü", "dünkü", "geçen sene", "bu sabahki", "şimdiye kadar", "son günlerde", "geçen yıllarda"])
def test_relative_time_inflected_forms_banned(bad):
    """İnceleme P1: göreli zaman yasağı çekimli Türkçe biçimleri de yakalar."""
    assert "goreli_zaman" in gh.banned_hits("Kredi hacmi %s eylül ayında arttı." % bad), bad


@pytest.mark.parametrize("ok", [
    "Dünya Bankası büyüme tahminini açıkladı.", "Dünya genelinde petrol talebi arttı.", "Dünyanın en büyük ekonomisi",
    "Bu gündem maddesi", "Bu ayrıntı açıklandı.", "Aynı dönemde ihracat arttı.", "Düşüş üst üste beşinci haftaya uzandı.",
    "Bir önceki güne göre değişim yüzde 2.", "Dünkirk", "Ocak ayında enflasyon"])
def test_relative_time_ban_has_no_false_positives(ok):
    assert "goreli_zaman" not in gh.banned_hits(ok), ok


def test_relative_time_sentence_on_real_credit_item_dropped():
    """01.10 girdisinde 'bu yılın' 5 kez geçiyor: model yankılarsa cümle düşer (önceden yayına çıkıyordu)."""
    _, ev, _ = _ctx_ev()
    h = _hid(ev, "Bankacılıkta kredi")
    (it, rep), _ = _validate(_item("Kredi hacmi 25 Eylül haftasında 164,6 milyar lira arttı", [
        ("Bankacılık sektöründe toplam kredi hacmi bu yılın eylül ayında büyüyerek 28,4 trilyon lirayı aştı.", [h])]))
    assert it is None and "yasak_dil:goreli_zaman" in rep["cumleler"][0]["ret"]


def test_acceptance_flags_inflected_relative_time(out):
    os.makedirs(out)
    doc = {"baski": "2026-10-01T19:30:00+03:00", "baski_label": "1 Ekim 2026 · 19:30", "maddeler": [
        {"id": "g-20261001-11", "baslik": "Kredi hacmi", "ozet": "Kredi hacmi geçen yılın aynı dönemine göre arttı."}]}
    for name, obj in (("2026-10-01-aksam.json", doc), ("2026-10-01-aksam.audit.json", {"durum": "basildi"})):
        with open(os.path.join(out, name), "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False)
    assert gh.acceptance(out, 7, today=NOW.date())["yasak_dil"] == ["2026-10-01-aksam g-20261001-11 goreli_zaman"]


def test_publisher_and_url_guard():
    assert gh.publisher("Dünya Finans") == ("Dünya", ("dunya.com",))
    assert gh.publisher("TRT Haber Dünya")[0] == "TRT Haber"
    assert gh._url_ok("https://www.aa.com.tr/tr/ekonomi/x/1", ("aa.com.tr",))
    assert not gh._url_ok("https://kotu.example/aa.com.tr", ("aa.com.tr",))
    assert not gh._url_ok("javascript:alert(1)", ())


def test_parse_response_variants():
    body = _read("yanit_az.json")
    assert len(gh.parse_response("```json\n%s\n```" % body)) == 4
    assert len(gh.parse_response("Elbette! İşte yanıt: " + body)) == 4
    assert gh.parse_response("model metni, json yok") is None
    assert gh.parse_response(None) is None
    assert gh.parse_response('{"maddeler": "yanlış tip"}') is None


# ----------------------------------------------------------------------------- doğrulayıcı (tek tek)

def _validate(raw):
    _, ev, ctx = _ctx_ev()
    return gh.validate_item(raw, ctx), ev


def _item(baslik, cumleler, kanit_b=None, hisseler=(), kategori="Türkiye"):
    return {"kategori": kategori, "baslik": baslik, "baslik_kanit": kanit_b or cumleler[0][1],
            "cumleler": [{"metin": m, "kanit": k} for m, k in cumleler], "hisseler": list(hisseler)}


def test_hallucinated_sentence_dropped_item_survives():
    _, ev, _ = _ctx_ev()
    h = _hid(ev, "Şimşek: Sorunlu")
    (it, rep), _ = _validate(_item("Şimşek: Sorunlu fonlarda tasfiye süreci başladı", [
        ("Şimşek'e göre fon piyasalarında sistemik bir sorun bulunmuyor.", [h]),
        ("Analistler, adımların piyasalarda olumlu karşılandığını belirtiyor.", [h])]))
    assert it and "Analistler" not in it["ozet"]
    assert any(r.startswith("dayanak") for r in rep["cumleler"][1]["ret"])


def test_wrong_number_and_unknown_entity_dropped():
    _, ev, _ = _ctx_ev()
    h = _hid(ev, "Bankacılıkta kredi")
    (it, rep), _ = _validate(_item("Kredi hacmi 25 Eylül haftasında 164,6 milyar lira arttı", [
        ("BDDK verilerine göre toplam kredi büyüklüğü 29,1 trilyon liraya çıktı.", [h]),
        ("Akbank'ın kredi büyümesi öne çıktı.", [h])]))
    assert it is None and rep["karar"] == "cumle_kalmadi"
    assert "sayi:29,1" in rep["cumleler"][0]["ret"]
    assert "ad:Akbank" in rep["cumleler"][1]["ret"]


def test_wrong_date_dropped_and_direction_conflict_dropped():
    _, ev, _ = _ctx_ev()
    h = _hid(ev, "ABD-İran")
    (it, rep), _ = _validate(_item("Brent petrolün varili 100 doları geçti", [
        ("Brent'in varil fiyatı 100,89 dolar oldu; değişim %2,92 düşüş.", ["F5"]),
        ("ABD ile İran müzakereleri 5 Ekim'de yeniden başlayacak.", [h])], kanit_b=[h, "F5"], kategori="Emtia"))
    assert it is None
    assert "yon:2,92" in rep["cumleler"][0]["ret"]
    assert "tarih:5 ekim" in rep["cumleler"][1]["ret"]


def test_sentence_initial_names_are_checked():
    al = gh.company_aliases(NAMES, NAMES.keys())
    assert "Akbank" in gh._entity_roots("Akbank'ın kredi büyümesi öne çıktı.", al)
    assert "Powell" in gh._entity_roots("Powell, politika faizini sabit tuttu.", al)
    assert "Otokar" in gh._entity_roots("Otokar yeni sözleşme imzaladı.", al)
    assert gh._entity_roots("Ayrıca, kredi hacmi arttı.", al) == []
    assert gh._entity_roots("Bu adım kredi hacmini artırdı.", al) == []
    # İnceleme P1: cümle başındaki büyük harfli her sözcük denetlenir (virgülsüz "Powell …" dahil)
    assert gh._entity_roots("Powell KOBİ kredilerinde sınırı yükseltti.", al) == ["Powell", "KOBİ"]
    assert gh._entity_roots("Analistler adımları değerlendirdi.", al) == ["Analistler"]


def test_kap_only_company_sentence_rejected_and_chip_rules():
    _, ev, _ = _ctx_ev()
    h = _hid(ev, "Otokar'dan yaklaşık")
    (it, rep), _ = _validate(_item("Otokar'a zırhlı araç ihracatı için 1,5 milyar dolarlık sözleşme", [
        ("Sözleşmenin tutarı şirketin yıllık hasılatının yaklaşık %41,6'sına denk geliyor.", ["K1"]),
        ("Otokar, tekerlekli zırhlı araçların tedariki ve lojistik desteğini kapsayan 1 milyar 472 milyon "
         "80 bin 360 dolarlık bir ihracat sözleşmesi imzaladı.", [h])], kanit_b=[h],
        hisseler=["OTKAR", "ASELS", "XXXXX"], kategori="Şirketler"))
    assert rep["cumleler"][0]["ret"][:2] == ["kanit_yok", "sayi:41,6"]   # AI, KAP'tan şirket olgusu yazamaz
    assert it and it["hisseler"] == ["OTKAR"]              # ASELS kanıtta yok, XXXXX evrende yok
    assert "41,6" not in it["ozet"]
    assert sorted(rep["hisse_ret"]) == ["ASELS", "XXXXX"]


def test_ai_cannot_restate_kap_numbers_even_with_press_citation():
    _, ev, _ = _ctx_ev()
    h = _hid(ev, "Otokar'dan yaklaşık")
    (it, rep), _ = _validate(_item("Otokar'a zırhlı araç ihracatı için 1,5 milyar dolarlık sözleşme", [
        ("Otokar'ın sözleşmesi yıllık hasılatının yaklaşık %41,6'sına denk geliyor.", [h, "K1"])],
        kanit_b=[h], kategori="Şirketler"))
    assert it is None and "sayi:41,6" in rep["cumleler"][0]["ret"]


def test_kap_line_cannot_launder_company_fact_through_press_id():
    """İnceleme P1: H1 (TCMB) + K3 (Kartonsan KAP) birlikte anılınca KAP olgusu basın haberi gibi
    yayımlanıyordu (4 yayıncı kaynağıyla, KARTN çipiyle). Cümle yalnız kendi H/F kanıtıyla denetlenir."""
    _, ev, ctx = _ctx_ev()
    h1 = _hid(ev, "TCMB, KOBİ")
    k3 = [k for k, v in ev.items() if v["kind"] == "K" and v["tickers"] == ["KARTN"]][0]
    kartonsan = "Kartonsan Karton Sanayii yatırımcı ilişkileri yöneticisinin görevinden ayrıldığını duyurdu."
    it, rep = gh.validate_item(_item("TCMB KOBİ kredisi sınırını genişletti", [
        ("Merkez Bankası, zorunlu karşılık düzenlemesi kapsamında KOBİ kredilerinin büyüme sınırını %4,5'ten "
         "%5'e yükseltti.", [h1]),
        (kartonsan, [h1, k3])], kanit_b=[h1], hisseler=["KARTN"]), ctx)
    assert any(r.startswith("dayanak") for r in rep["cumleler"][1]["ret"])
    assert it is None or ("Kartonsan" not in it["ozet"] and it["hisseler"] == [])
    assert rep["hisse_ret"] == ["KARTN"]
    # yalnız KAP'a dayanan başlık da geçmez (K adı kabul ettirir, olguyu değil)
    it2, rep2 = gh.validate_item(_item("Kartonsan'da yatırımcı ilişkileri yöneticisi değişti",
                                       [(kartonsan, [h1, k3])], kanit_b=[h1, k3]), ctx)
    assert it2 is None and rep2["karar"] in ("baslik_ret", "cumle_kalmadi")
    # K satırı bağımsız dayanak sayılmaz: tek yayıncılı H + K = tek dayanak
    h13 = _hid(ev, "Çin yakıt")
    it3, rep3 = gh.validate_item(_item("Çin rafinerileri yakıt ihracatını durdurdu", [
        ("Çin rafinerileri yakıt ihracatını durdurdu ve petrol yeniden 100 doların üzerine çıktı.", [h13, "K1"])],
        kanit_b=[h13]), ctx)
    assert it3 is None and rep3["karar"] == "tek_dayanak"


def test_chip_needs_supporting_press_headline_not_kap_line():
    _, ev, ctx = _ctx_ev()
    h = _hid(ev, "Otokar'dan yaklaşık")
    k_asels = [k for k, v in ev.items() if v["kind"] == "K" and v["tickers"] == ["ASELS"]][0]
    it, rep = gh.validate_item(_item("Otokar'a zırhlı araç ihracatı için 1,5 milyar dolarlık sözleşme", [
        ("Otokar, tekerlekli zırhlı araçların tedariki ve lojistik desteğini kapsayan 1,5 milyar dolarlık bir "
         "ihracat sözleşmesi imzaladı.", [h, k_asels])], kanit_b=[h], hisseler=["OTKAR", "ASELS"],
        kategori="Şirketler"), ctx)
    assert it and it["hisseler"] == ["OTKAR"] and rep["hisse_ret"] == ["ASELS"]


OTOKAR_BASE = ("Otokar, tekerlekli zırhlı araçların tedariki ve lojistik desteğini kapsayan bir ihracat "
               "sözleşmesi imzaladı")


@pytest.mark.parametrize("sentence,code", [
    ("Otokar zırhlı araç ihracat sözleşmesini iptal etti.", "olumsuzluk"),            # imzaladı → iptal
    ("Otokar zırhlı araç ihracat sözleşmesini imzalamadı.", "olumsuzluk"),            # -mA- olumsuzluk
    (OTOKAR_BASE + "; bu, şirketin tarihindeki en büyük sözleşme oldu.", "yargi:en büyük"),
    (OTOKAR_BASE + "; sözleşme şirketin borçluluğunu azaltacak.", "gelecek"),
    (OTOKAR_BASE + " ve güçlü bir başarıya imza attı.", "yargi:güçlü"),
    (OTOKAR_BASE + " ve hisse için yukarı yönlü bir dönem başladı.", "yasak_dil:islem_dili"),
    (OTOKAR_BASE + "; sözleşme şirketin borçluluğunu ve faiz giderini düşürüyor.", "dayanak"),  # uydurma yan cümle
])
def test_planted_meaning_errors_on_otokar_rejected(sentence, code):
    """İnceleme P1: %40 kök örtüşmesi tersine çevrilmiş olguyu, uydurma iddiayı ve yargıyı geçiriyordu."""
    _, ev, ctx = _ctx_ev()
    h = _hid(ev, "Otokar'dan yaklaşık")
    r = gh.check_text(sentence, [h], [h], ctx)
    assert any(x == code or x.startswith(code + ":") or x.startswith(code) for x in r), (sentence, r)


def test_wrong_actor_without_comma_rejected_and_faithful_sentences_pass():
    _, ev, ctx = _ctx_ev()
    h1, h6 = _hid(ev, "TCMB, KOBİ"), _hid(ev, "Otokar'dan yaklaşık")
    assert "ad:Powell" in gh.check_text("Powell KOBİ kredilerinde büyüme sınırını yüzde 4,5 seviyesinden "
                                        "yüzde 5 seviyesine çıkardı.", [h1], [h1], ctx)
    for s, h in ((OTOKAR_BASE + ".", h6),
                 ("TCMB, KOBİ kredilerinde büyüme sınırını yüzde 4,5 seviyesinden yüzde 5 seviyesine çıkardı.", h1),
                 ("Türk lirası zorunlu karşılıklarda bloke tesis oranları da düşürüldü.", h1)):
        assert gh.check_text(s, [h], [h], ctx) == [], s


def test_ozet_skips_overlong_sentence_keeps_next():
    _, ev, _ = _ctx_ev()
    h = _hid(ev, "Bankacılıkta kredi")
    long_s = ("BDDK verilerine göre bankaların toplam kredi büyüklüğü 28,4 trilyon liraya çıktı; tüketici "
              "kredileri ile kredi kartı alacaklarında da artış görüldü ve bu artış bankacılık sektöründe "
              "kredi hacminin büyümeye devam ettiğini gösterdi; toplam hacim 25 Eylül haftasında yeni bir "
              "düzeye ulaştı ve bankaların kredi büyüklüğü ilk kez bu düzeyi geçti.")
    assert len(long_s) > gh.OZET_MAX
    (it, rep), _ = _validate(_item("Kredi hacmi 25 Eylül haftasında 164,6 milyar lira arttı", [
        (long_s, [h]), ("BDDK verilerine göre bankaların toplam kredi büyüklüğü 28,4 trilyon liraya çıktı.", [h])]))
    assert it and it["ozet"].startswith("BDDK verilerine göre bankaların toplam kredi büyüklüğü 28,4")
    assert len(it["ozet"]) <= gh.OZET_MAX


def test_single_publisher_without_own_data_rejected():
    _, ev, _ = _ctx_ev()
    h = _hid(ev, "Petrol piyasasında Çin şoku")       # yalnız Dünya
    (it, rep), _ = _validate(_item("Çinli rafinerilerin yakıt ihracatına ara vermesi petrolü etkiledi", [
        ("Çinli rafineriler ekim ayında yakıt ihracatını askıya aldı.", [h])], kategori="Emtia"))
    assert it is None and rep["karar"] == "tek_dayanak"


def test_kaynaklar_only_from_supporting_headlines():
    _, ev, _ = _ctx_ev()
    h = _hid(ev, "ABD-İran")
    (it, rep), _ = _validate(_item("Brent petrolün varili 100 doları geçti", [
        ("ABD ile İran arasındaki müzakerelerin tıkandığına dair haberler arz endişelerini artırdı ve "
         "Brent'in varil fiyatı 100 doları aştı.", [h])], kategori="Emtia"))
    assert [k["ad"] for k in it["kaynaklar"]] == ["AA", "TRT Haber"]
    for k in it["kaynaklar"]:
        assert re.match(r"^https://(www\.)?%s/" % re.escape(PUBS[k["ad"]]), k["url"])
        assert k["tarih"] == "2026-10-01"


# ----------------------------------------------------------------------------- baskı (uçtan uca)

def test_edition_end_to_end_contract_and_filters(out):
    model = FakeModel(_read("yanit_1.json"))
    res = _run(out, model)
    assert res["durum"] == "basildi" and res["cagri"] == 1 and res["madde"] == 8
    doc = gh.load_latest(out)
    assert set(doc) == {"baski", "baski_label", "maddeler"}
    assert doc["baski"] == "2026-10-01T21:45:00+03:00" and doc["baski_label"] == "1 Ekim 2026 · 21:45"
    ids = [m["id"] for m in doc["maddeler"]]
    assert ids == ["g-20261001-%d" % n for n in range(11, 19)]      # akşam baskısı 11'den başlar
    texts = " ".join(m["baslik"] + " " + m["ozet"] for m in doc["maddeler"])
    for gone in ("Analistler", "2,5 milyar", "bugün", "Powell", "fırsat", "AA'nın", "%41,6",
                 "AB'den enerjide fiyat krizi uyarısı", "karantinaya alındığını açıkladı"):
        assert gone not in texts, gone
    assert sum(1 for m in doc["maddeler"] if m["onemli"]) == 1
    assert doc["maddeler"][0]["onemli"] and doc["maddeler"][0]["baslik"].startswith("Merkez Bankası, KOBİ")
    for m in doc["maddeler"]:
        assert set(m) == CONTRACT_KEYS
        assert m["ai"] is True and m["kategori"] in gh.KATEGORILER
        assert len(m["baslik"]) <= 70 and 0 < len(m["ozet"]) <= 260
        assert m["kaynaklar"] and all(set(k) == {"ad", "url", "tarih"} for k in m["kaynaklar"])
        assert all(k["ad"] in PUBS and PUBS[k["ad"]] in k["url"] for k in m["kaynaklar"])
        assert gh.banned_hits(m["baslik"] + " " + m["ozet"]) == []
        assert set(m["hisseler"]) <= {"OTKAR"}
    by = {m["baslik"][:12]: m for m in doc["maddeler"]}
    assert by["Kredi hacmi "]["hisseler"] == []               # AKBNK/GARAN kanıtta yok → çip yok
    assert by["Brent petrol"]["hisseler"] == []               # TUPRS kanıtta yok
    assert by["Otokar'a zır"]["hisseler"] == ["OTKAR"]


def test_edition_audit_records_every_verdict_and_cost(out):
    model = FakeModel(_read("yanit_1.json"))
    _run(out, model)
    audit = json.load(open(os.path.join(out, "2026-10-01-aksam.audit.json"), encoding="utf-8"))
    assert audit["model"] == "gemini-2.5-flash-lite" and audit["cagri"] == 1
    assert audit["maliyet_usd"] == pytest.approx(0.0012) and audit["gemini_cagri_sayaci"] == 1
    kararlar = [m["karar"] for m in audit["turlar"][0]["maddeler"]]
    assert kararlar.count("yayın") == 9 and len(kararlar) == 12
    # kopya, dayanaksız, 2× göreli zaman/sayı, yalnız K, Fed, AA + "günü tamamladı" (kısa F cümlesinde 2 kanıtsız
    # sözcük; madde başlığı zaten "alım fırsatı" ile düşüyor)
    assert audit["atilan_cumle"] == 8
    assert audit["used_ids"] and audit["yayin"]["maddeler"]
    assert gh.done_keys(out) == {"2026-10-01-aksam"}


def test_retry_when_too_few_items_then_merge(out):
    model = FakeModel(_read("yanit_az.json"), _read("yanit_ek.json"))
    res = _run(out, model)
    assert res["cagri"] == 2 and res["madde"] == 6 and res["durum"] == "basildi"
    second = model.prompts[1]
    assert "Önceki taslakta" in second and "Fed faizi 25 baz puan indirdi" in second
    assert "kaynakta olmayan sayı" in second
    _, ev, _ = _ctx_ev()
    used = _hid(ev, "TCMB, KOBİ")
    assert ("\n%s [" % used) not in second                   # yayımlanan maddenin kanıtı istemden çıktı


def test_call_cap_is_four_and_nothing_published_on_garbage(out):
    model = FakeModel(*(["bozuk yanıt"] * 10))
    res = _run(out, model)
    assert len(model.prompts) == gh.MAX_CALLS == 4
    assert res["durum"] == "yetersiz" and gh.load_latest(out) is None
    assert gh.done_keys(out) == {"2026-10-01-aksam"}         # tavan harcandı → aynı baskı tekrar denenmez


def test_no_response_means_retry_later_not_marked_done(out):
    model = FakeModel()                                     # hep None (sigorta/zaman aşımı)
    res = _run(out, model, usage_fn=lambda: (5, 0.01))      # sayaç artmadı
    assert res["durum"] == "cagri_yapilamadi" and len(model.prompts) == 2
    assert gh.done_keys(out) == set() and gh.load_latest(out) is None


def _bad_types_answer():
    good = json.loads(_read("yanit_1.json"))["maddeler"]
    bad = [dict(good[0], kategori=["Türkiye"]),                                   # liste kategori
           dict(good[5], cumleler=[dict(good[5]["cumleler"][0], kanit=9)]),       # sayı kanıt
           dict(good[6], baslik_kanit=3, kategori=7),                             # sayı başlık kanıtı + kategori
           dict(good[3], baslik=5)]                                               # sayı başlık
    return json.dumps({"maddeler": bad}, ensure_ascii=False)


def test_malformed_types_never_raise():
    _, ev, ctx = _ctx_ev()
    for r in json.loads(_bad_types_answer())["maddeler"]:
        it, rep = gh.validate_item(r, ctx)
        assert isinstance(rep["baslik"], str)
        assert it is None or it["kategori"] in gh.KATEGORILER


def _loop(out, model, start, end, **kw):
    """app.py _gundem_haber_loop taklidi: 5 dk'da bir due → v1_ready → run_edition; istisna yutulur."""
    from datetime import timedelta
    now, errors = start, 0
    while now <= end:
        try:
            slot = gh.due(now, gh.done_keys(out), gh.load_latest(out) is not None)
            if slot and gh.v1_ready(now, slot, {"2026-10-01-aksam"}):
                gh.run_edition(now, slot, model, v1_doc=_json("v1_baski.json"), kap_items=_json("kap_items.json"),
                               names=NAMES, universe=set(NAMES), budget_status=OK_BUDGET,
                               cb_state={"open_until": 0.0}, base_dir=out, input_dir=os.path.join(FX, "girdi"),
                               usage_fn=FakeUsage(model), **kw)
        except Exception:
            errors += 1
        now += timedelta(minutes=5)
    return errors


def test_malformed_model_json_at_most_four_calls_across_loop_ticks(out):
    """İnceleme P1: bozuk tipli madde doğrulamayı patlatıyor, iz yazılmadığı için döngü 5 dk'da bir Gemini'yi
    yeniden çağırıyordu (bir baskıda 22 çağrı; ilk kurulumda sınırsız). Artık ≤4 çağrı, baskı yine basılır."""
    model = FakeModel(*([_bad_types_answer()] * 60))
    errors = _loop(out, model, NOW, datetime(2026, 10, 2, 8, 0))
    assert errors == 0 and len(model.prompts) <= gh.MAX_CALLS
    audit = json.load(open(os.path.join(out, "2026-10-01-aksam.audit.json"), encoding="utf-8"))
    assert audit["durum"] in ("basildi", "yetersiz") and "hata" not in audit


def test_exception_after_call_marks_edition_done(out, monkeypatch):
    """Çağrıdan sonra beklenmedik istisna (ör. doğrulayıcı hatası) baskıyı 'yapıldı' sayar: tekrar çağrı yok."""
    def boom(raw, ctx):
        raise RuntimeError("beklenmedik")
    monkeypatch.setattr(gh, "validate_item", boom)
    model = FakeModel(*([_read("yanit_1.json")] * 60))
    assert _loop(out, model, NOW, datetime(2026, 10, 1, 23, 30)) == 0
    assert len(model.prompts) <= gh.MAX_CALLS
    audit = json.load(open(os.path.join(out, "2026-10-01-aksam.audit.json"), encoding="utf-8"))
    assert audit["turlar"][0]["maddeler"][0]["karar"] == "bicim_hatasi"

    class Crash(FakeModel):
        def __call__(self, prompt, max_tokens):
            FakeModel.__call__(self, prompt, max_tokens)
            raise ValueError("yanıt işlenemedi")       # çağrı yapıldı, sonra çöktü
    out2 = out + "-2"
    crash = Crash()
    assert _loop(out2, crash, NOW, datetime(2026, 10, 2, 8, 0)) == 0
    assert len(crash.prompts) == 1                       # iz işareti: aynı baskı yeniden çağrılmaz
    a2 = json.load(open(os.path.join(out2, "2026-10-01-aksam.audit.json"), encoding="utf-8"))
    assert a2["hata"].startswith("ValueError") and a2["durum"] == "yetersiz"


@pytest.mark.parametrize("budget,cb,why", [
    (dict(OK_BUDGET, enabled=False), {}, "GEMINI_ENABLED=0"),
    (OK_BUDGET, {"manual_hold": "D-P0-2409", "open_until": 0}, "manual_hold"),
    (OK_BUDGET, {"open_until": 4102444800.0}, "kota_sigortasi"),
    (dict(OK_BUDGET, usd_month=4.0), {}, "aylik_esik"),
    (dict(OK_BUDGET, calls_today=197), {}, "gunluk_tavan"),
])
def test_gate_blocks_before_any_call(out, budget, cb, why):
    model = FakeModel(_read("yanit_1.json"))
    res = _run(out, model, budget_status=budget, cb_state=cb)
    assert res == {"durum": "atlandi", "sebep": why}
    assert model.prompts == [] and gh.done_keys(out) == set()


def test_kill_switch(out, monkeypatch):
    monkeypatch.setattr(gh, "ENABLED", False)
    model = FakeModel(_read("yanit_1.json"))
    assert _run(out, model)["sebep"] == "GUNDEM_AI=0" and model.prompts == []


def test_latest_atomic_cache_and_takedown(out):
    _run(out, FakeModel(_read("yanit_1.json")))
    assert gh.load_latest(out)["maddeler"]
    assert not [n for n in os.listdir(out) if n.startswith(".tmp_")]
    os.remove(os.path.join(out, "latest.json"))               # acil kaldırma
    assert gh.load_latest(out) is None
    with open(os.path.join(out, "latest.json"), "w") as f:
        f.write("{bozuk")
    assert gh.load_latest(out) is None
    assert gh.empty_doc() == {"baski": None, "baski_label": None, "maddeler": []}


def test_acceptance_summary(out):
    _run(out, FakeModel(_read("yanit_1.json")))
    r = gh.acceptance(out, 7, today=NOW.date())
    assert r["baski"] == 1 and r["bes_ve_ustu"] == 1 and r["yasak_dil"] == []
    assert r["toplam_usd"] == pytest.approx(0.0012)


# ----------------------------------------------------------------------------- takvim

def test_due_slots():
    d = datetime(2026, 10, 1)        # Perşembe
    at = lambda h, m: d.replace(hour=h, minute=m)
    assert gh.due(at(8, 29), set()) is None
    assert gh.due(at(8, 31), set()) == "sabah"
    assert gh.due(at(12, 29), set()) == "sabah"
    assert gh.due(at(12, 31), set()) is None                 # 4 saatten geç: atlanır
    assert gh.due(at(19, 35), set()) == "aksam"
    assert gh.due(at(19, 35), {"2026-10-01-aksam"}) is None
    sat = datetime(2026, 10, 3, 10, 0)
    assert gh.due(sat, set()) is None
    assert gh.due(sat, set(), has_latest=False) == "sabah"   # ilk kurulum
    assert gh.due(sat, {"2026-10-02-aksam"}, has_latest=False) is None


def test_due_slots_hafta_sonu():
    # CPO-1815 (03.10): Cmt/Paz tek baskı 10:30, ≤4 saat gecikmeyle
    sat = datetime(2026, 10, 3)
    at = lambda h, m: sat.replace(hour=h, minute=m)
    assert gh.due(at(10, 29), set()) is None
    assert gh.due(at(10, 31), set()) == "hafta_sonu"
    assert gh.due(at(14, 29), set()) == "hafta_sonu"
    assert gh.due(at(14, 31), set()) is None                          # 4 saatten geç: atlanır
    assert gh.due(at(10, 31), {"2026-10-03-hafta_sonu"}) is None      # aynı gün ikinci kez basılmaz
    sun = datetime(2026, 10, 4, 10, 31)
    assert gh.due(sun, set()) == "hafta_sonu"


def test_v1_ready_and_window():
    d = datetime(2026, 10, 1, 8, 35)
    assert gh.v1_ready(d, "sabah", {"2026-10-01-sabah"})
    assert not gh.v1_ready(d, "sabah", set())
    assert gh.v1_ready(d.replace(hour=9, minute=0), "sabah", set())
    mon = datetime(2026, 10, 5, 8, 30)
    assert gh.window_start(mon, "sabah") == datetime(2026, 10, 2, 17, 30)   # Cuma akşam baskısından
    assert gh.window_start(datetime(2026, 10, 1, 19, 30), "aksam") == datetime(2026, 10, 1, 5, 30)


def test_v1_ready_and_window_hafta_sonu():
    # Hafta sonu baskısı v1'den bağımsız basar (v1 hafta içi son iş gününde basar, CPO-1815)
    assert gh.v1_ready(datetime(2026, 10, 3, 10, 31), "hafta_sonu", set())
    assert gh.window_start(datetime(2026, 10, 3, 10, 30), "hafta_sonu") == datetime(2026, 10, 2, 17, 30)   # Cmt ← Cuma 19:30
    assert gh.window_start(datetime(2026, 10, 4, 10, 30), "hafta_sonu") == datetime(2026, 10, 3, 8, 30)    # Paz ← Cmt 10:30
