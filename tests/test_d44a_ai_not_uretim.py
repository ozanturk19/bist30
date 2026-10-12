"""D-44b ilk adım — AI Analist Notu (şirket notu) üretim yolu: olgu kurucu, cümle denetimi, gün sonu işi,
pilot bütçesi, okuma yolu. Ağ yok, Gemini yok: fikstürler 12.10.2026 canlı /api/data + /fundamentals + /kap
salt-okur kopyasından kırpıldı; model yanıtları kayıtlı sahte yanıtlardır (tests/fixtures/d44a_ai_not/yanit_*).
Üretim sayaç dosyalarına (gemini_usage.json, /tmp/bp_gemini_quota_cb.json, data/ai_not) dokunulmaz.
"""
import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from pipeline import ai_notes as an  # noqa: E402
from pipeline import ai_not_job as job  # noqa: E402

FX = os.path.join(ROOT, "tests", "fixtures", "d44a_ai_not")
DAY = "2026-10-12"
TZ = timezone(timedelta(hours=3))
NAMES = {"TUPRS": "Tüpraş Türkiye Petrol Rafinerileri", "GARAN": "Garanti BBVA", "THYAO": "Türk Hava Yolları"}


def _j(name):
    with open(os.path.join(FX, name), encoding="utf-8") as f:
        return json.load(f)


def _raw(name):
    with open(os.path.join(FX, name), encoding="utf-8") as f:
        return f.read()


ROWS = {r["ticker"]: r for r in _j("api_data.json")["stocks"]}


def facts_for(t, fund=None):
    return an.build_company_facts(t, ROWS[t], fund or _j("%s.fundamentals.json" % t)["fundamentals"],
                                  _j("%s.kap.json" % t)["disclosures"], today=DAY)


def check(t, note, facts=None):
    return an.validate_sentences(json.dumps({"note": note, "facts_used": []}), facts or facts_for(t),
                                 name=NAMES[t], ticker=t)


def rets(res):
    return [c["ret"] for c in res["cumleler"]]


# ----------------------------------------------------------------------------- olgu kurucu

def test_facts_tuprs_kap_only_and_formatted():
    f = {x["id"]: x for x in facts_for("TUPRS")}
    assert f["F1"]["t"] == "Hasılat, 2025 yıllık değişim (enflasyon düzeltmeli)" and f["F1"]["v"] == "−%21,7"
    assert f["F2"]["v"] == "+%23,1"
    assert f["F3"]["t"].startswith("Hasılat değişimi, 2026 2. çeyrek") and f["F3"]["v"] == "+%59,7"
    assert f["F5"]["t"] == "Net nakit, 2025 sonu" and f["F5"]["v"] == "57,0 Mrd ₺"
    assert f["F6"]["v"] == "1,40"
    assert f["F7"]["v"] == "9 maddenin 7'si"
    vals = {x["t"]: x["v"] for x in f.values()}
    assert vals["F/K (son 12 ay kârıyla)"] == "11,0" and vals["Sektör ortancası F/K"] == "11,7"
    assert vals["PD/DD (son açıklanan özkaynakla)"] == "1,63" and vals["Sektör ortancası PD/DD"] == "0,91"
    assert vals["Özsermaye kârlılığı (son 12 ay)"] == "%14,8"
    assert vals["F/K'da sektör sırası (en düşük F/K birinci)"] == "10 şirket arasında 4. sırada"
    # hisse sayfası Q2 ile aynı kural (kanon §5.6): F/K 0,94 makul + PD/DD 1,79 pahalı → pahalı tarafta
    assert vals["Değerleme (F/K ve PD/DD, ortancaya göre)"] == "pahalı tarafta"
    assert vals["Trend durumu"] == "Yatay" and vals["Trend durumunun başladığı tarih"] == "22 Eylül 2026"
    assert vals["Sağlanan trend koşulu"] == "5 koşuldan 4'ü"
    # yalnız rutin dışı ve son 30 gün; finansal tablo duyurusu ve rutin borçlanma bildirimi girmez
    kap = [x for x in f.values() if x["_k"] == "bildirim"]
    assert [x["v"] for x in kap] == ["Kurumsal Yönetim Derecelendirme Notu"]
    assert kap[0]["t"] == "Şirket bildirimi, 2 Ekim 2026"


def test_facts_never_use_yahoo_or_analyst_fields():
    fund = _j("TUPRS.fundamentals.json")["fundamentals"]
    assert fund["roe"] is not None and fund["analyst_target"]   # fikstürde Yahoo alanları duruyor
    text = " ".join("%s %s" % (x["t"], x["v"]) for x in facts_for("TUPRS"))
    assert "17,6" not in text and "1,35" not in text   # Yahoo ROE ve cari oran
    assert "analist" not in text.lower() and "hedef" not in text.lower()


def test_facts_bank_and_foreign_currency_templates():
    g = {x["t"]: x["v"] for x in facts_for("GARAN")}
    assert g["Net faiz geliri, 2025 yıllık değişim (nominal)"] == "+%62,5"
    assert g["Kredi/mevduat oranı, 2025 sonu"] == "%86,2" and g["Gider/gelir oranı, 2025"] == "%43,5"
    assert not any("Hasılat" in k or "Cari oran" in k for k in g)
    assert "KREDİ DERECELENDİRME BİLDİRİMİ" not in g.values()   # tamamı büyük harf başlık girmez
    t = {x["t"]: x["v"] for x in facts_for("THYAO")}
    assert t["Hasılat, 2025 yıllık değişim (USD cinsinden rapor)"] == "+%28,2"
    assert not any("Mrd ₺" in v for v in t.values())          # döviz raporlayanda tutar yok, oran var
    assert t["Net borç/FAVÖK, 2025"] == "2,68" and t["Trend durumu"] == "Trend Bozuldu"
    assert t["Değerleme (F/K ve PD/DD, ortancaya göre)"] == "ucuz tarafta"


def test_facts_share_mismatch_drops_valuation():
    fund = _j("TUPRS.fundamentals.json")["fundamentals"]
    fund["kap"]["degerleme_simdi"]["pay_uyumsuz"] = True
    t = " ".join(x["t"] for x in facts_for("TUPRS", fund))
    assert "F/K" not in t and "PD/DD" not in t and "Değerleme" not in t
    assert "Özsermaye kârlılığı (son 12 ay)" in t     # pay adedinden bağımsız


def test_facts_without_kap_record():
    fund = {"kap_durum": "hazirlaniyor", "kap": None}
    f = an.build_company_facts("TUPRS", ROWS["TUPRS"], fund, [], today=DAY)
    assert [x["t"] for x in f] == ["Trend durumu", "Trend durumunun başladığı tarih", "Sağlanan trend koşulu"]


def test_facts_block_and_signature():
    facts = facts_for("TUPRS")
    for line in an.facts_block(facts).splitlines():
        assert set(json.loads(line)) == {"id", "t", "v"}         # iç alanlar modele gitmez
    s1 = an.facts_signature(facts)
    assert s1 == an.facts_signature(facts_for("TUPRS"))
    fund = _j("TUPRS.fundamentals.json")["fundamentals"]
    fund["kap"]["degerleme_simdi"]["fk"] = 11.24
    assert an.facts_signature(facts_for("TUPRS", fund)) != s1
    assert an.facts_signature(facts, prompt="başka istem") != s1


def test_tr_helpers():
    assert an._tr_chg(-21.72) == "−%21,7" and an._tr_chg(23.08) == "+%23,1" and an._tr_chg(0.01) == "%0,0"
    assert an._tr_date("22.09.2026") == "22 Eylül 2026" and an._tr_date("2026-10-02T09:24") == "2 Ekim 2026"
    assert an._quarter_label("2026/06") == "2026 2. çeyrek" and an._quarter_label("2025/12") is None
    assert [an._poss(n) for n in (0, 1, 2, 3, 4, 5, 6, 7, 9, 10, 40)] == \
        ["'ı", "'i", "'si", "'ü", "'ü", "'i", "'sı", "'si", "'u", "'u", "'ı"]


# ----------------------------------------------------------------------------- cümle denetimi

def test_good_response_publishes_all_sentences():
    res = an.validate_sentences(_raw("yanit_TUPRS_iyi.json"), facts_for("TUPRS"), name=NAMES["TUPRS"], ticker="TUPRS")
    assert res["ok"] and all(not r for r in rets(res))
    assert res["not"] == ("Tüpraş'ın hasılatı 2025'te geriledi (−%21,7), net kâr arttı (+%23,1). 2026 2. çeyrekte "
                          "hasılat (+%59,7) ve net kâr (+%290,9) yükseldi. Bilançoda net nakit var (57,0 Mrd ₺) ve "
                          "cari oran 1,40. F/K 11,0, sektör ortancası 11,7; değerleme pahalı tarafta. Trend durumu "
                          "Yatay; 5 koşuldan 4'ü sağlanıyor.")
    assert len(res["not"]) <= an.NOTE_MAX_LEN
    assert "{F" not in res["not"]
    assert res["facts_used"] == ["F1", "F2", "F3", "F4", "F5", "F6", "F8", "F9", "F16", "F17", "F19"]


def test_mixed_response_drops_hallucination_wrong_number_and_banned():
    res = an.validate_sentences(_raw("yanit_TUPRS_karisik.json"), facts_for("TUPRS"), name=NAMES["TUPRS"],
                                ticker="TUPRS")
    by = {c["metin"]: c["ret"] for c in res["cumleler"]}
    assert any(r.startswith("dayanak") for r in by["Şirket, yeni rafineri yatırımıyla ihracatını artırdı (+%59,7)."])
    assert by["Net kâr %25,4 arttı (+%23,1)."] == ["ciplak_rakam"]          # verideki sayı değil, çıplak
    assert "yasak_dil" in by["Bu seviyeler uzun vadeli yatırımcı için alım fırsatı sunuyor (pahalı tarafta)."]
    assert res["ok"]
    assert res["not"] == ("Tüpraş'ın hasılatı 2025'te geriledi (−%21,7), net kâr arttı (+%23,1). Bilançoda net nakit "
                          "var (57,0 Mrd ₺). Özsermaye kârlılığı %14,8, sektör ortancası %5,9. Trend durumu Yatay.")
    for bad in ("rafineri", "25,4", "fırsat"):
        assert bad not in res["not"]


def test_bad_response_rejected_whole_note():
    res = an.validate_sentences(_raw("yanit_TUPRS_kotu.json"), facts_for("TUPRS"), name=NAMES["TUPRS"], ticker="TUPRS")
    assert not res["ok"] and res["not"] is None and res["sebep"] == "cumle_az:0"
    r = rets(res)
    assert r[0] == ["yon:F1"]                      # "Hasılat arttı" ama olgu −%21,7
    assert r[1] == ["ciplak_rakam"]                # 2024 olguda yok (olgu 2025)
    assert r[2] == ["karsilastirma:F8/F9"]         # 11,0 "üstünde" 11,7 değil
    assert "yasak_dil" in r[3] and "yasak_dil" in r[4]


def test_pilot_style_judgments_and_average_dropped():
    res = an.validate_sentences(_raw("yanit_TUPRS_pilot_uslubu.json"), facts_for("TUPRS"), name=NAMES["TUPRS"],
                                ticker="TUPRS")
    r = rets(res)
    assert r[1] == ["yargi:makul", "yargi:güçlü"]  # olguda olmayan yorum sıfatı
    assert r[2] == ["ortalama"]                    # veri ortanca; "ortalama" yanlış terim
    assert res["ok"] and res["not"].count(".") == 3


@pytest.mark.parametrize("sentence,code", [
    ("Hasılat geriledi.", "olgu_yok"),
    ("Hasılat geriledi ({F99}).", "tanimsiz_olgu"),
    ("Hasılat %21,7 geriledi ({F1}).", "ciplak_rakam"),
    ("Hasılat 2024'te geriledi ({F1}).", "ciplak_rakam"),
    ("Net kâr 12 Ekim'de arttı ({F2}).", "ciplak_rakam"),
    ("Hasılat geriledi (%{F1}).", "bicim"),
    ("Net kâr geriledi ({F2}).", "yon"),
    ("Hasılat ({F1}) ve net kâr ({F2}) arttı.", "yon"),
    ("Özsermaye kârlılığı {F12}, sektör ortancası {F13} altında.", "karsilastirma"),
    ("F/K {F8}, sektör ortancasına {F9} yakın.", None),
    ("Cari oran ({F6}) kısa vadeli borçları karşılamıyor.", "karsilama"),
    ("Net nakit ({F5}) bilançoyu sağlam kılıyor.", "yargi"),
    ("Borçluluk yüksek ({F6}).", "yargi"),
    ("Hasılat artışı net kârı destekledi ({F2}).", "neden_sonuc"),
    ("Net kâr önümüzdeki dönemde artacak ({F2}).", "tahmin"),
    ("Hasılat beklentilerin altında kaldı ({F1}).", "yasak_dil"),
    ("Bu hisse için AL sinyali var ({F17}).", "yasak_dil"),
    ("Hedef fiyat yukarıda ({F8}).", "yasak_dil"),
    ("Dün trend durumu {F17} oldu.", "yasak_dil"),
    ("KAP'a göre hasılat geriledi ({F1}).", "yasak_dil"),
    ("Tüpraş, Türkiye'nin en büyük rafinerisidir ({F5}).", "yasak_dil"),
    ("Tüpraş zayıf bir şirket ({F1}).", "yasak_dil"),
    ("Aramco ile ortaklık sürüyor ({F20}).", "ad"),
    ("Şirket, yeni tesis yatırımları için kredi kullandı ({F5}).", "dayanak"),
    ("Değerleme sektör ortalamasına göre {F16}.", "ortalama"),
])
def test_sentence_rules(sentence, code):
    res = check("TUPRS", sentence + " Trend durumu {F17}. Hasılat 2025'te geriledi ({F1}). Cari oran {F6}.")
    first = res["cumleler"][0]["ret"]
    if code is None:
        assert first == [], first
    else:
        assert any(r.split(":")[0] == code for r in first), first
    assert all(c["ret"] == [] for c in res["cumleler"][1:])


def test_bare_years_dates_quarters_allowed_only_from_referenced_fact():
    ok = check("TUPRS", "2026 2. çeyrekte hasılat yükseldi ({F3}). Trend durumu 22 Eylül 2026'dan beri {F17} ({F18}). "
                        "F/K son 12 ay kârıyla {F8}.")
    assert rets(ok) == [[], [], []]
    bad = check("TUPRS", "2025 3. çeyrekte hasılat yükseldi ({F3}). Trend durumu 21 Eylül'den beri {F17} ({F18}). "
                         "PD/DD son 12 ay kârıyla {F10}.")
    assert rets(bad) == [["ciplak_rakam"], ["ciplak_rakam"], ["ciplak_rakam"]]


def test_trims_to_five_sentences_and_length():
    s = " ".join(["Trend durumu {F17}."] * 7)
    res = check("TUPRS", s)
    assert res["ok"] and res["not"].count("Trend durumu") == 5
    assert [c["ret"] for c in res["cumleler"]][5:] == [["fazla_cumle"], ["fazla_cumle"]]
    long_s = " ".join(["Hasılat {F1}, net kâr {F2} ve çeyrek hasılat {F3}; şirket bildirimi {F20}."] * 5)
    res2 = check("TUPRS", long_s)
    assert res2["ok"] and len(res2["not"]) <= an.NOTE_MAX_LEN
    assert [c["ret"] for c in res2["cumleler"]] == [[], [], [], ["uzunluk"], ["uzunluk"]]


def test_note_level_rejections():
    facts = facts_for("TUPRS")
    assert an.validate_sentences("bu JSON değil", facts)["sebep"] == "json"
    assert an.validate_sentences(json.dumps({"note": "Trend durumu {F17}.", "facts_used": ["F99"]}),
                                 facts)["sebep"] == "facts_used"
    assert an.validate_sentences(json.dumps({"note": "", "facts_used": []}), facts)["sebep"] == "bos_not"


def test_rendered_kap_title_with_banned_word_never_offered():
    kap = [{"date": "05.10.2026 10:00:00", "summary": "Yeni hedef fiyat açıklaması", "class": "ODA", "rutin": False},
           {"date": "06.10.2026 10:00:00", "summary": "Yatırım teşvik belgesi alınması", "class": "ODA",
            "rutin": False},
           {"date": "01.08.2026 10:00:00", "summary": "Eski bildirim", "class": "ODA", "rutin": False}]
    f = an.build_company_facts("TUPRS", ROWS["TUPRS"], _j("TUPRS.fundamentals.json")["fundamentals"], kap, today=DAY)
    assert [x["v"] for x in f if x["_k"] == "bildirim"] == ["Yatırım teşvik belgesi alınması"]


def test_feedback_lists_reasons():
    res = an.validate_sentences(_raw("yanit_TUPRS_kotu.json"), facts_for("TUPRS"), name=NAMES["TUPRS"], ticker="TUPRS")
    fb = an.feedback_for(res)
    assert "yasak sözcük" in fb and "çıplak" in fb and "{Fn}" in fb


def test_prompt_keeps_recipe_rules():
    p = an.SYSTEM_PROMPT
    for must in ("AL / SAT / BEKLE", "420 karakter", "{Fn}", "ortanca", "Neden-sonuç", "trend durumu tek cümle"):
        assert must in p
    assert an.URETIM_MODEL == "gemini-2.5-flash-lite"


# ----------------------------------------------------------------------------- iş (tur)

class FakeBudget(object):
    def __init__(self, calls_today=0, usd_month=0.0, enabled=True, refuse=None):
        self.st = {"enabled": enabled, "calls_today": calls_today, "daily_cap": 200, "usd_month": usd_month,
                   "monthly_cap_usd": 5.0}
        self.refuse = refuse
        self.recorded = []

    def status(self):
        return dict(self.st)

    def reserve(self):
        if self.refuse:
            return False, self.refuse
        self.st["calls_today"] += 1
        return True, None

    def record(self, model, pt, ot):
        c = (pt * 0.10 + ot * 0.40) / 1e6
        self.recorded.append((model, pt, ot))
        self.st["usd_month"] += c
        return c


@pytest.fixture()
def env(tmp_path, monkeypatch):
    root = tmp_path / "root"
    (root / "data" / "bulten").mkdir(parents=True)
    (root / "data" / "bulten" / ("%s.json" % DAY)).write_text("{}")
    (root / "data" / "universe.json").write_text(json.dumps({"indices": {"XU030": ["TUPRS", "GARAN", "THYAO"]}}))
    base = tmp_path / "ai_not"
    monkeypatch.setenv("AI_NOT_ENABLED", "1")
    monkeypatch.setattr(job, "PILOT_USD", 1.0)
    return {"root": str(root), "base": str(base)}


def make_fetch(funds=None, data=None, log=None):
    def fetch(path):
        if log is not None:
            log.append(path)
        if path == "/api/data":
            return data or _j("api_data.json")
        m = re.match(r"^/api/hisse/([A-Z0-9]+)/(fundamentals|kap)$", path)
        t, kind = m.group(1), m.group(2)
        if kind == "fundamentals":
            return {"fundamentals": (funds or {}).get(t) or _j("%s.fundamentals.json" % t)["fundamentals"]}
        return _j("%s.kap.json" % t)
    return fetch


def make_call(script, log):
    """Kayıtlı yanıtları sırayla döndüren sahte model: {ticker: [dosya, ...]}; maliyet sabit."""
    def call(system, user):
        t = re.search(r"\(([A-Z0-9]+)\)\nOlgular:", user).group(1)
        log.append((t, user))
        name = script[t].pop(0)
        return (_raw(name) if name else None), 0.0003, (None if name else "HTTP 503: x")
    return call


def run(env, call, fetch=None, now=None, **kw):
    kw.setdefault("budget_status", {"enabled": True, "calls_today": 0, "daily_cap": 200, "usd_month": 0.0,
                                    "monthly_cap_usd": 5})
    kw.setdefault("cb_state", {})
    return job.run(now=now or datetime(2026, 10, 12, 20, 5, tzinfo=TZ), call=call, fetch=fetch or make_fetch(),
                   base=env["base"], root=env["root"], log=lambda s: None, **kw)


def test_flag_off_does_nothing(env, monkeypatch):
    monkeypatch.setenv("AI_NOT_ENABLED", "0")
    calls, fetched = [], []
    res = run(env, make_call({}, calls), make_fetch(log=fetched))
    assert res == {"durum": "kapali"} and calls == [] and fetched == []
    assert not os.path.exists(env["base"])
    assert job.public_note("TUPRS", base=env["base"]) is None


def test_full_run_publishes_atomically_and_is_once_per_day(env):
    calls = []
    script = {"TUPRS": ["yanit_TUPRS_iyi.json"], "GARAN": ["yanit_GARAN.json"], "THYAO": ["yanit_THYAO.json"]}
    res = run(env, make_call(script, calls))
    assert res["durum"] == "tamam" and res["yayin"] == 3 and res["cagri"] == 3
    doc = json.load(open(job.note_path("TUPRS", env["base"]), encoding="utf-8"))
    assert doc["ticker"] == "TUPRS" and doc["kapanis"] == DAY and doc["kapanis_label"] == "12 Ekim 2026"
    assert doc["etiket"] == "Yapay zekâ ile derlendi" and doc["model"] == "gemini-2.5-flash-lite"
    assert doc["not"].startswith("Tüpraş'ın hasılatı 2025'te geriledi (−%21,7)")
    assert [f["id"] for f in doc["olgular"]] == ["F1", "F2", "F3", "F4", "F5", "F6", "F8", "F9", "F16", "F17", "F19"]
    assert not [n for n in os.listdir(env["base"]) if n.startswith(".tmp_")]
    audit = json.load(open(os.path.join(env["base"], "audit", DAY + ".json"), encoding="utf-8"))
    assert set(audit["hisseler"]) == {"TUPRS", "GARAN", "THYAO"}
    # aynı gün ikinci tur: çağrı yok
    res2 = run(env, make_call({}, calls))
    assert res2 == {"durum": "yapildi", "gun": DAY} and len(calls) == 3
    pub = job.public_note("TUPRS", base=env["base"], today=date(2026, 10, 12))
    assert pub == {"ticker": "TUPRS", "not": doc["not"], "kapanis": DAY, "kapanis_label": "12 Ekim 2026",
                   "etiket": "Yapay zekâ ile derlendi"}


def test_next_day_unchanged_facts_no_call_and_date_advances(env):
    calls = []
    script = {"TUPRS": ["yanit_TUPRS_iyi.json"], "GARAN": ["yanit_GARAN.json"], "THYAO": ["yanit_THYAO.json"]}
    run(env, make_call(script, calls))
    day2 = "2026-10-13"
    open(os.path.join(env["root"], "data", "bulten", day2 + ".json"), "w").write("{}")
    data = _j("api_data.json")
    for r in data["stocks"]:
        r["bar_date"] = "13.10.2026"
    fund = _j("TUPRS.fundamentals.json")["fundamentals"]
    fund["kap"]["degerleme_simdi"]["fk"] = 11.31          # yalnız TUPRS'te olgu değişti
    script2 = {"TUPRS": ["yanit_TUPRS_iyi.json"]}
    res = run(env, make_call(script2, calls), make_fetch(funds={"TUPRS": fund}, data=data),
              now=datetime(2026, 10, 13, 20, 5, tzinfo=TZ))
    assert res["degismedi"] == 2 and res["yayin"] == 1 and res["cagri"] == 1
    assert [c[0] for c in calls[3:]] == ["TUPRS"]
    g = json.load(open(job.note_path("GARAN", env["base"]), encoding="utf-8"))
    assert g["kapanis"] == day2 and g["kapanis_label"] == "13 Ekim 2026"     # not geçerli, tarih ilerledi
    assert "11,3" in json.load(open(job.note_path("TUPRS", env["base"]), encoding="utf-8"))["not"]


def test_rejected_first_draft_retries_with_feedback(env):
    calls = []
    script = {"TUPRS": ["yanit_TUPRS_kotu.json", "yanit_TUPRS_karisik.json"], "GARAN": ["yanit_GARAN.json"],
              "THYAO": ["yanit_THYAO.json"]}
    res = run(env, make_call(script, calls), tickers=["TUPRS"])
    assert res["yayin"] == 1 and res["cagri"] == 2
    assert "kurallara uymadığı" in calls[1][1] and "kurallara uymadığı" not in calls[0][1]
    doc = json.load(open(job.note_path("TUPRS", env["base"]), encoding="utf-8"))
    assert "rafineri" not in doc["not"] and "fırsat" not in doc["not"] and doc["cumle"] == 4


def test_twice_rejected_note_not_stored_previous_kept(env):
    calls = []
    prev = {"ticker": "TUPRS", "not": "Önceki not.", "kapanis": "2026-10-09", "kapanis_label": "9 Ekim 2026"}
    job._atomic_write(job.note_path("TUPRS", env["base"]), prev)
    res = run(env, make_call({"TUPRS": ["yanit_TUPRS_kotu.json", "yanit_TUPRS_kotu.json"]}, calls),
              tickers=["TUPRS"])
    assert res["ret"] == 1 and res["yayin"] == 0 and res["cagri"] == 2
    assert json.load(open(job.note_path("TUPRS", env["base"]), encoding="utf-8")) == prev
    st = json.load(open(os.path.join(env["base"], "durum.json"), encoding="utf-8"))
    assert st["hisseler"]["TUPRS"]["sonuc"] == "ret" and st["hisseler"]["TUPRS"]["gun"] == DAY


@pytest.mark.parametrize("kw,why", [
    ({"cb_state": {"manual_hold": "D-P0-2409", "open_until": 0}}, "manual_hold"),
    ({"cb_state": {"open_until": 4102444800}}, "kota_sigortasi"),
    ({"budget_status": {"enabled": False, "calls_today": 0, "daily_cap": 200, "usd_month": 0}}, "GEMINI_ENABLED=0"),
    ({"budget_status": {"enabled": True, "calls_today": 150, "daily_cap": 200, "usd_month": 0}}, "gunluk_tavan"),
    ({"budget_status": {"enabled": True, "calls_today": 0, "daily_cap": 200, "usd_month": 5.0,
                        "monthly_cap_usd": 5}}, "aylik_tavan"),
])
def test_gate_blocks_before_any_call(env, kw, why):
    calls, fetched = [], []
    res = run(env, make_call({}, calls), make_fetch(log=fetched), **kw)
    assert res["durum"] == "atlandi" and res["sebep"] == why
    assert calls == [] and fetched == []


def test_pilot_budget_exhausted_blocks_and_hides(env):
    calls = []
    run(env, make_call({"TUPRS": ["yanit_TUPRS_iyi.json"], "GARAN": ["yanit_GARAN.json"],
                        "THYAO": ["yanit_THYAO.json"]}, calls))
    assert job.public_note("TUPRS", base=env["base"], today=date(2026, 10, 12)) is not None
    job._atomic_write(os.path.join(env["base"], "butce.json"), {"usd": 0.9985, "cagri": 4000})
    assert job.budget_exhausted(env["base"])
    assert job.public_note("TUPRS", base=env["base"], today=date(2026, 10, 12)) is None   # gizli, gri ifade yok
    open(os.path.join(env["root"], "data", "bulten", "2026-10-13.json"), "w").write("{}")
    res = run(env, make_call({}, calls), now=datetime(2026, 10, 13, 20, 5, tzinfo=TZ))
    assert res["durum"] == "atlandi" and res["sebep"] == "pilot_butce" and len(calls) == 3


def test_real_call_path_counts_cost_and_never_exceeds_pilot_cap(env, monkeypatch):
    fb = FakeBudget()
    http = []

    def fake_http(model, system, user, api_key, timeout=25):
        http.append((model, api_key))
        return _raw("yanit_TUPRS_iyi.json"), {"promptTokenCount": 2400, "candidatesTokenCount": 180}, None

    monkeypatch.setattr(an, "call_gemini", fake_http)
    os.makedirs(env["base"], exist_ok=True)
    job._atomic_write(os.path.join(env["base"], "butce.json"), {"usd": 0.9970, "cagri": 10})
    call = job.make_gemini_call("TESTKEY", env["base"], sleep=lambda s: None, budget=fb)
    text, cost, err = call("sistem", "kullanıcı")
    assert text and err is None and http == [("gemini-2.5-flash-lite", "TESTKEY")]
    assert cost == round((2400 * 0.10 + 180 * 0.40) / 1e6, 6)
    st = job.budget_state(env["base"])
    assert st["cagri"] == 11 and abs(st["usd"] - (0.9970 + cost)) < 1e-6
    assert fb.recorded == [("gemini-2.5-flash-lite", 2400, 180)]
    # kalan < CALL_RESERVE_USD → HTTP isteği atılmadan durur
    job._atomic_write(os.path.join(env["base"], "butce.json"), {"usd": 0.9985, "cagri": 11})
    with pytest.raises(job.Stop) as e:
        call("sistem", "kullanıcı")
    assert str(e.value) == "pilot_butce" and len(http) == 1
    # paylaşımlı tavan reddi (reserve) da HTTP'siz durdurur
    job._atomic_write(os.path.join(env["base"], "butce.json"), {"usd": 0.0, "cagri": 0})
    fb.refuse = "daily_cap"
    with pytest.raises(job.Stop):
        call("sistem", "kullanıcı")
    assert len(http) == 1


def test_unmeasured_call_charged_worst_case(env, monkeypatch):
    fb = FakeBudget()
    monkeypatch.setattr(an, "call_gemini", lambda *a, **k: (None, None, "HTTP 429: kota"))
    os.makedirs(env["base"], exist_ok=True)
    call = job.make_gemini_call("TESTKEY", env["base"], sleep=lambda s: None, budget=fb)
    text, cost, err = call("s", "u")
    assert text is None and cost == job.CALL_RESERVE_USD and err.startswith("HTTP 429")
    assert job.budget_state(env["base"])["usd"] == job.CALL_RESERVE_USD and fb.recorded == []


def test_gemini_error_stops_run_and_ticker_retried_next_turn(env):
    calls = []
    res = run(env, make_call({"GARAN": [None], "THYAO": ["yanit_THYAO.json"], "TUPRS": ["yanit_TUPRS_iyi.json"]},
                             calls))
    assert res["durum"] == "durdu" and res["sebep"].startswith("gemini_hata")
    st = json.load(open(os.path.join(env["base"], "durum.json"), encoding="utf-8"))
    assert "GARAN" not in st["hisseler"]                      # iz geri alındı
    assert [c[0] for c in calls] == ["GARAN"]                 # tur ilk hatada durdu (BIST30 alfabetik)
    res2 = run(env, make_call({"GARAN": ["yanit_GARAN.json"], "THYAO": ["yanit_THYAO.json"],
                               "TUPRS": ["yanit_TUPRS_iyi.json"]}, calls))
    assert res2["yayin"] == 3


def test_data_not_ready_until_official_close(env):
    data = _j("api_data.json")
    for r in data["stocks"]:
        r["bar_date"] = "09.10.2026"
    calls = []
    res = run(env, make_call({}, calls), make_fetch(data=data))
    assert res["durum"] == "veri_hazir_degil" and calls == []
    assert job.latest_close_day(env["root"]) == DAY


def test_dry_run_writes_samples_only(env, monkeypatch):
    monkeypatch.setenv("AI_NOT_ENABLED", "0")                   # kuru koşu bayraktan bağımsız
    calls = []
    res = run(env, make_call({"TUPRS": ["yanit_TUPRS_karisik.json"], "GARAN": ["yanit_GARAN.json"]}, calls),
              tickers=["TUPRS", "GARAN"], kuru=True)
    assert res["yayin"] == 2
    assert not os.path.exists(job.note_path("TUPRS", env["base"]))
    assert not os.path.exists(os.path.join(env["base"], "durum.json"))
    k = json.load(open(os.path.join(env["base"], "kuru", "TUPRS.json"), encoding="utf-8"))
    assert k["yayin"]["not"].startswith("Tüpraş'ın") and k["olgular"]
    md = open(os.path.join(env["base"], "kuru", "ozet.md"), encoding="utf-8").read()
    assert "Yapay zekâ ile derlendi" in md and "Atılan cümleler" in md and "rafineri" in md


def test_lock_prevents_parallel_runs(env):
    lock = job._lock(env["base"])
    try:
        res = run(env, make_call({}, []))
        assert res["durum"] == "calisiyor"
    finally:
        lock.close()


def test_public_note_guards(env, monkeypatch):
    job._atomic_write(job.note_path("TUPRS", env["base"]),
                      {"ticker": "TUPRS", "not": "Trend durumu Yatay.", "kapanis": "2026-10-01"})
    assert job.public_note("TUPRS", base=env["base"], today=date(2026, 10, 11))["kapanis_label"] == "1 Ekim 2026"
    assert job.public_note("TUPRS", base=env["base"], today=date(2026, 10, 12)) is None   # 11 gün eski
    assert job.public_note("../etc", base=env["base"]) is None
    assert job.public_note("GARAN", base=env["base"]) is None
    job._atomic_write(job.note_path("GARAN", env["base"]), {"ticker": "THYAO", "not": "x", "kapanis": DAY})
    assert job.public_note("GARAN", base=env["base"], today=date(2026, 10, 12)) is None   # dosya başka hisse
    monkeypatch.setenv("AI_NOT_ENABLED", "0")
    assert job.public_note("TUPRS", base=env["base"], today=date(2026, 10, 2)) is None


def test_bist30_from_universe_file(env):
    assert job.bist30(env["root"]) == ["GARAN", "THYAO", "TUPRS"]
    assert len(job.bist30(ROOT)) == 30


def test_systemd_units_point_to_job_and_flag():
    d = os.path.join(ROOT, "pipeline", "systemd")
    svc = open(os.path.join(d, "bp-ai-not.service"), encoding="utf-8").read()
    tmr = open(os.path.join(d, "bp-ai-not.timer"), encoding="utf-8").read()
    assert "-m pipeline.ai_not_job" in svc and "EnvironmentFile=/root/bist30/.env" in svc
    assert "Type=oneshot" in svc and "TimeoutStartSec=" in svc
    assert "OnCalendar=" in tmr and "Mon..Fri" in tmr
