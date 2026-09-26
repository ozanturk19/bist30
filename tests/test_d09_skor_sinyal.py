"""D-09 — skor ve sinyal fonksiyonları: bilinen girdi → bilinen çıktı.

Kapsam (plan N25): compose_score (Teknik Güç), sinyal koşulları (kanon §3,
O23=A: Supertrend, ADX >= 25, EMA 12 > EMA 99, DI+ > DI-, haftalık EMA 20
yönü), compute_health_score (Temel skor), compute_borsapusula_score (BP) ve
bant eşikleri. D-21: BP testleri BP_DIRECTIONAL bayrağının iki durumunda da
koşar (kapalı = bugünkü formül birebir, açık = kanon §3 yönlü formül; D-10
kâhiniyle tam alan karşılaştırması). Hepsi üretim modüllerini import eder;
yerelde (Python 3.9) ve VPS venv'de (3.12) koşar. app.py'yi import eden 4 test
(dosyanın sonu) yerelde atlanır (conftest.app_module), VPS'te koşar.

Beklenen değerlerin hesabı her vakanın yanında yazılıdır; gerçek veri
vakaları 22-24.09 gün sonu kayıtlarından (VPS snapshots/ + scores/).
"""
import math

import pytest

import business_rules as br
import financial_health_score as fhs

NAN = float("nan")


# ── compose_score: Teknik Güç (ADX 30 + hacim 25 + teyit 10 + RSI 10) × 100/75 ──
@pytest.mark.parametrize("adx, vol, confirmed, rsi, signal, expected", [
    (50, 5, True, 60, "AL", 100),        # 30 + 25 + 10 + 10 = 75 → 100
    (0, 0, False, 40, "AL", 0),          # hiçbir bileşen yok
    (25, 1, True, 55, "AL", 53),         # 15 + 5 + 10 + 10 = 40 → 53,3
    (30, 2.5, False, 80, "AL", 47),      # 18 + 12,5 + 0 + 5 = 35,5 → 47,3
    (80, 12, True, 75, "AL", 100),       # ADX 50'de, hacim 5'te kırpılır; RSI 75 bant içi
    (25, 1, True, 75.1, "AL", 47),       # RSI > 75 → +5: 35 → 46,7
    (25, 1, True, 49.9, "AL", 40),       # RSI < 50 → +0: 30 → 40
    (40, 1.5, True, 30, "SAT", 69),      # 24 + 7,5 + 10 + 10 = 51,5 → 68,7
    (40, 1.5, True, 20, "SAT", 62),      # RSI < 25 → +5: 46,5 → 62
    (40, 1.5, True, 60, "SAT", 55),      # RSI > 50 → +0: 41,5 → 55,3
    (40, 1.5, True, 25, "SAT", 69),      # alt sınır dahil
    (40.7, 2.03, True, 15.4, "SAT", 66),  # SMRTG 24.09 (snapshot signal_strength 66)
    (37.4, 0.83, True, 27.9, "SAT", 62),  # ECZYT 24.09 (snapshot signal_strength 62)
])
def test_compose_score_known_values(adx, vol, confirmed, rsi, signal, expected):
    assert br.compose_score(adx=adx, vol_ratio=vol, bull_score=3, confirmed=confirmed,
                            rsi=rsi, signal=signal) == expected


def test_compose_score_missing_inputs_use_neutral_defaults():
    # None/NaN/inf: ADX → 0, hacim oranı → 1,0 (5 puan), RSI → 50 (AL bandı +10)
    assert br.compose_score(None, None, 3, False, None) == 20              # 0 + 5 + 0 + 10 = 15 → 20
    assert br.compose_score(NAN, float("inf"), 3, True, NAN) == 33         # 0 + 5 + 10 + 10 = 25 → 33,3
    assert br.compose_score("x", -math.inf, 0, False, "y", "SAT") == 20    # RSI 50 SAT bandında (25-50) → +10


def test_compose_score_ignores_bull_score():
    # CPO-DEV2-053: bull_score imzada kaldı ama skora katkısı yok
    # 18 + 10 + 10 + 10 = 48 → 64
    assert br.compose_score(30, 2, 0, True, 60) == br.compose_score(30, 2, 3, True, 60) == 64


# ── Sinyal koşulları (kanon §3): 5 koşul, motor ADX + DI'yi tek oy sayar ──────
# signal_from_indicators(st_dir, adx, di_plus, di_minus, e12, e99, weekly_dir)
BULL = dict(st_dir=1, adx=30.0, di_plus=25.0, di_minus=15.0, e12=110.0, e99=100.0, weekly_dir=1)
BEAR = dict(st_dir=-1, adx=30.0, di_plus=15.0, di_minus=25.0, e12=90.0, e99=100.0, weekly_dir=-1)


@pytest.mark.parametrize("base, change, expected", [
    (BULL, {}, "AL"),                                   # 5/5 koşul → Güçlü Trend
    (BULL, {"weekly_dir": 0}, "BEKLE"),                 # haftalık hesaplanamadı → Yatay (fail-closed)
    (BULL, {"weekly_dir": -1}, "BEKLE"),                # haftalık aşağı
    (BULL, {"adx": 24.9}, "BEKLE"),                     # ADX < 25
    (BULL, {"adx": 25.0}, "AL"),                        # ADX = 25 dahil
    (BULL, {"di_plus": 20.0, "di_minus": 20.0}, "BEKLE"),  # DI eşit → iki yöne de oy yok
    (BULL, {"di_plus": 15.0, "di_minus": 25.0}, "BEKLE"),  # DI- > DI+
    (BULL, {"e12": 100.0}, "BEKLE"),                    # EMA eşit
    (BULL, {"st_dir": -1}, "BEKLE"),                    # Supertrend aşağı
    (BULL, {"adx": NAN}, "BEKLE"),                      # eksik ADX oy vermez
    (BEAR, {}, "SAT"),                                  # tersleri birden → Trend Bozuldu
    (BEAR, {"weekly_dir": 1}, "BEKLE"),
    (BEAR, {"weekly_dir": 0}, "BEKLE"),
    (BEAR, {"e12": 110.0}, "BEKLE"),
    (BEAR, {"di_minus": NAN}, "BEKLE"),
])
def test_signal_conditions(base, change, expected):
    kw = dict(base, **change)
    assert br.signal_from_indicators(**kw) == expected


def test_classify_signal_scores_thyao_2309():
    # THYAO 23.09 (metodoloji taslağı verisi): ST aşağı, ADX 23,3, DI+ 19 < DI- 30,
    # EMA12 293,81 < EMA99 305,93, haftalık aşağı → ayı oyu 2 (ADX eşik altı) → Yatay
    flags = br.trend_flags(-1, 23.3, 19.0, 30.0, 293.81, 305.93)
    assert flags == {"st_bull": False, "st_bear": True, "adx_bull": False,
                     "adx_bear": False, "e12_bull": False, "e12_bear": True}
    assert br.classify_signal(flags, -1) == ("BEKLE", 0, 2)
    assert br.classify_signal(br.trend_flags(**{k: v for k, v in BULL.items() if k != "weekly_dir"}), 1) == ("AL", 3, 0)


# ── compute_health_score: sektör içi yüzdelik, kategori ağırlıkları 30/30/25/15 ──
POOL5 = [
    # profit_margin, roe, gross_margin, fcf_to_sales, ocf_stability_cv, pe_ratio, revenue_growth
    {"ticker": "AAAA", "profit_margin": .30, "roe": .10, "gross_margin": .30, "fcf_to_sales": .05,
     "ocf_positive_quarters": 2, "ocf_stability_cv": .5, "pe_ratio": 5, "revenue_growth": .2},
    {"ticker": "BBBB", "profit_margin": .10, "roe": .20, "gross_margin": .10, "fcf_to_sales": .01,
     "ocf_stability_cv": .1, "pe_ratio": 10, "revenue_growth": .1},
    {"ticker": "CCCC", "profit_margin": .20, "roe": .30, "gross_margin": .20, "fcf_to_sales": .02,
     "ocf_stability_cv": .2, "pe_ratio": 15, "revenue_growth": .3},
    {"ticker": "DDDD", "profit_margin": .05, "roe": .40, "gross_margin": .40, "fcf_to_sales": .03,
     "ocf_stability_cv": .3, "pe_ratio": 20, "revenue_growth": .4},
    {"ticker": "EEEE", "profit_margin": .15, "roe": .50, "gross_margin": .50, "fcf_to_sales": .04,
     "ocf_stability_cv": .4, "pe_ratio": 25, "revenue_growth": .5},
]


def test_health_score_known_pool(stock_pool):
    pool = stock_pool("Sanayi", POOL5)
    r = fhs.compute_health_score(pool[0], "Sanayi", pool)
    # Kârlılık: marj 5/5=100, ÖK kârlılığı 1/5=20, brüt marj 3/5=60 → 60
    # Nakit: FCF 5/5=100, pozitif çeyrek 2/4=50, CV 5/5 → ters 0 → 50
    # Kaldıraç: veri yok → ağırlık kalanlara dağılır
    # Değerleme: F/K 1/5=20 → ters 80, büyüme 2/5=40 → 60
    # (60×30 + 50×30 + 60×15) / 75 = 56
    assert r["temel_analiz_skoru"] == 56
    assert r["categories"] == {"karlilik": 60.0, "nakit_akisi": 50.0, "degerleme_buyume": 60.0}
    assert r["data_completeness"] == 0.57        # 8 / 14 metrik
    assert r["categories_complete"] is False
    assert r["band"] == "sari"
    assert r["categories_na"] == []


def test_health_score_leverage_na_bank(stock_pool):
    rows = [dict(POOL5[0], ticker="GARAN")] + POOL5[1:]
    pool = stock_pool("Bankacılık", rows)
    r = fhs.compute_health_score(pool[0], "Bankacılık", pool)
    assert r["temel_analiz_skoru"] == 56
    assert r["categories_na"] == ["kaldirac"]    # mevduat bankası: yapısal olarak yok


def test_health_score_suppressed_below_min_metrics(stock_pool):
    pool = stock_pool("Sanayi", [{"profit_margin": .2, "roe": .1}] + POOL5[1:])
    r = fhs.compute_health_score(pool[0], "Sanayi", pool)
    assert r["temel_analiz_skoru"] is None and r["band"] is None and r["categories"] == {}
    assert r["data_completeness"] == 0.14        # 2 / 14 < MIN_METRICS_FOR_SCORE (3)


def test_health_score_small_sector_falls_back_to_whole_pool(stock_pool):
    small = stock_pool("Kucuk", [{"ticker": "KUC1", "profit_margin": .12, "roe": .35, "gross_margin": .45},
                                 {"ticker": "KUC2", "profit_margin": .50, "roe": .60, "gross_margin": .60}])
    pool = stock_pool("Sanayi", POOL5) + small
    r = fhs.compute_health_score(small[0], "Kucuk", pool)
    # Kucuk'ta 2 değer < 5 → 7 hisselik genel havuz: 3/7, 4/7, 5/7 → ort. 57,1
    assert r["categories"] == {"karlilik": 57.1}
    assert r["temel_analiz_skoru"] == 57


# ── compute_borsapusula_score: bayrak kapalı = bugünkü formül (0,6 T + 0,4 TG, ──
# Yatay'da BP = Temel), açık = yönlü (D-21, kanon §3: 0,6 T + 0,4 × trend payı;
# pay GT max(50, TG) · Yatay 50 · TB min(50, 100 − TG)). Durum iç anahtarla gelir.
@pytest.fixture(params=[False, True], ids=["bayrak-kapali", "bayrak-acik"])
def bp_flag(request, monkeypatch):
    if request.param:
        monkeypatch.setenv("BP_DIRECTIONAL", "1")
    else:
        monkeypatch.delenv("BP_DIRECTIONAL", raising=False)
    return request.param


BP_CASES = [
    # teknik, temel, durum, bayrak kapalı → (BP, partial), bayrak açık → (BP, partial)
    (60, 50, "AL", (54, False), (54, False)),        # GT, TG ≥ 50: iki formül aynı (30 + 24)
    (40, 60, "AL", (52, False), (56, False)),        # GT, TG < 50: pay 50 → 36 + 20
    (86, 54, "SAT", (67, False), (38, False)),       # ECZYT 22.09: eski 66,8 (N4 bulgusu); pay 14 → 38
    (61, 52, "SAT", (56, False), (47, False)),       # MGROS 22.09: kanon §3 "56 → 47"
    (62, 52, "SAT", (56, False), (46, False)),       # ECZYT 24.09: pay 38 → 46,4
    (66, 47, "SAT", (55, False), (42, False)),       # SMRTG 24.09: pay 34 → 41,8
    (None, 61, "BEKLE", (61, True), (57, False)),    # THYAO 22.09: kanon "61 → 57" (iki eşit halka kalkar)
    (None, 63, "BEKLE", (63, True), (58, False)),    # THYAO 24.09: 37,8 + 20
    (None, 60, "SAT", (60, True), (56, True)),       # yön var, güç yok → nötr pay 50, partial
    (55, 60, None, (58, False), (56, True)),         # durum bilinmiyor → nötr pay 50, partial
    (70, None, "AL", (70, True), (None, True)),      # Temel yok → yönlüde skor yok (Sınırlı veri)
    (None, None, "BEKLE", (None, True), (None, True)),
]


@pytest.mark.parametrize("teknik, temel, state, off, on", BP_CASES)
def test_borsapusula_score_both_flag_states(bp_flag, teknik, temel, state, off, on):
    r = fhs.compute_borsapusula_score(teknik, temel, state=state)
    assert (r["borsapusula_skoru"], r["partial"]) == (on if bp_flag else off)
    if bp_flag and temel is not None:
        assert r["trend_payi"] == fhs.trend_share(state, teknik)[0]
    else:
        assert set(r) == {"borsapusula_skoru", "partial"}      # kapalıyken sözlük eskisiyle aynı


def test_borsapusula_score_custom_weights(monkeypatch):
    monkeypatch.delenv("BP_DIRECTIONAL", raising=False)
    assert fhs.compute_borsapusula_score(60, 40, {"temel": .5, "teknik": .5})["borsapusula_skoru"] == 50
    assert fhs.compute_borsapusula_score(60, 40, {"temel": .5, "teknik": .5}, state="AL",
                                         directional=True)["borsapusula_skoru"] == 50


@pytest.mark.parametrize("value, enabled", [
    (None, False), ("", False), ("0", False), ("1", True), (" 1 ", True), ("true", False), ("yes", False),
])
def test_bp_directional_flag_parsing(monkeypatch, value, enabled):
    if value is None:
        monkeypatch.delenv("BP_DIRECTIONAL", raising=False)
    else:
        monkeypatch.setenv("BP_DIRECTIONAL", value)
    assert fhs.bp_directional_enabled() is enabled


def test_directional_grid_acceptance():
    """D-21 kabulü, tüm tamsayı alanında (Temel ve Teknik Güç üretimde 0-100 tamsayı).

    - GT ≥ Yatay ≥ TB (monoton) → "TB'de BP, Yatay karşılığını geçmez" (long-only)
    - GT'de Teknik Güç artınca BP düşmez, TB'de artınca BP artmaz (ECZYT sınıfı kapanır)
    - Yatay'da BP = Temel yalnız Temel 49-51'de (0,6 T + 20 aritmetiği; yapısal kopya yok)
    """
    def bp(t, s, g):
        return fhs.compute_borsapusula_score(g, t, state=s, directional=True)["borsapusula_skoru"]
    yatay_esit = set()
    for t in range(101):
        y = bp(t, "BEKLE", None)
        if y == t:
            yatay_esit.add(t)
        prev = None
        for g in range(101):
            gt, tb = bp(t, "AL", g), bp(t, "SAT", g)
            assert gt >= y >= tb, (t, g)
            if prev is not None:
                assert gt >= prev[0] and tb <= prev[1], (t, g)
            prev = (gt, tb)
    assert yatay_esit == {49, 50, 51}


def _load_sim():
    import importlib.util
    import os
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "bp_yonlu_sim.py")
    spec = importlib.util.spec_from_file_location("bp_yonlu_sim", path)
    sim = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sim)
    return sim


def test_directional_matches_d10_oracle():
    """Üretim (financial_health_score) == D-10 simülasyonunun bağımsız kâhini."""
    sim = _load_sim()
    values = list(range(101)) + [None]
    for t in values:
        for s in ("AL", "BEKLE", "SAT", None):
            for g in values:
                got = fhs.compute_borsapusula_score(g, t, state=s, directional=True)["borsapusula_skoru"]
                assert got == sim.bp_yonlu(t, s, g), (t, s, g)
                assert fhs.compute_borsapusula_score(g, t, state=s, directional=False)["borsapusula_skoru"] \
                    == sim.bp_bugun(t, g), (t, s, g)


ENTRY_KEYS = ["teknik_analiz_skoru", "temel_analiz_skoru", "borsapusula_skoru", "data_completeness",
              "categories_complete", "partial", "band", "categories", "categories_na"]


def test_build_score_entry_both_flag_states(bp_flag, stock_pool):
    pool = stock_pool("Sanayi", POOL5)
    tb = fhs.build_score_entry(pool[0], "Sanayi", pool, 62, "SAT")     # Temel 56, TG 62
    ya = fhs.build_score_entry(pool[1], "Sanayi", pool, None, "BEKLE")  # Temel 41
    assert (tb["temel_analiz_skoru"], ya["temel_analiz_skoru"]) == (56, 41)
    if bp_flag:
        assert (tb["borsapusula_skoru"], tb["partial"]) == (49, False)   # 33,6 + 0,4 × 38 = 48,8
        assert (ya["borsapusula_skoru"], ya["partial"]) == (45, False)   # 24,6 + 20 = 44,6
        assert tb["bp_trend"] == {"durum": "SAT", "pay": 38.0}
        assert ya["bp_trend"] == {"durum": "BEKLE", "pay": 50.0}
        assert list(tb) == ENTRY_KEYS + ["bp_trend", "temel_analiz_aciklamasi"]
    else:
        assert (tb["borsapusula_skoru"], tb["partial"]) == (58, False)   # 33,6 + 24,8 = 58,4
        assert (ya["borsapusula_skoru"], ya["partial"]) == (41, True)    # Yatay: BP = Temel
        assert list(tb) == ENTRY_KEYS + ["temel_analiz_aciklamasi"]      # kayıt biçimi eskisiyle aynı
    assert tb["temel_analiz_aciklamasi"].endswith(" Yatırım tavsiyesi değildir.")


def test_canli_check_flags_bad_and_legacy_entries(stock_pool, tmp_path):
    """tools/bp_yonlu_sim.py --canli: bayrak sonrası kayıtları kâhine karşı denetler."""
    import json
    sim = _load_sim()
    pool = stock_pool("Sanayi", POOL5)
    ok = {"AAAA": fhs.build_score_entry(pool[0], "Sanayi", pool, 62, "SAT", directional=True),
          "BBBB": fhs.build_score_entry(pool[1], "Sanayi", pool, None, "BEKLE", directional=True)}
    bozuk = dict(fhs.build_score_entry(pool[2], "Sanayi", pool, 70, "AL", directional=True))
    bozuk["borsapusula_skoru"] += 1
    eski = fhs.build_score_entry(pool[3], "Sanayi", pool, None, "BEKLE", directional=False)
    p = tmp_path / "last_health_scores.json"
    p.write_text(json.dumps({t: {"data": e, "ts": 0} for t, e in
                             dict(ok, CCCC=bozuk, DDDD=eski).items()}), encoding="utf-8")
    r = sim.canli(str(p))
    assert r["hata"] == ["CCCC"] and r["bp_trend_eksik"] == 1
    assert r["tb_bp_gt_yatay"] == 0 and r["yapisal_kopya"] == 0


def test_eod_pass_passes_state_to_entry(app_function):
    body = app_function("_run_eod_scoring_pass")
    assert 'signal_by_ticker = {r.get("ticker"): r.get("signal") for r in results}' in body
    assert "signal_strength_by_ticker.get(tk), signal_by_ticker.get(tk))" in body
    assert "_fhs.build_score_entry(" in body and "compute_borsapusula_score(" not in body


@pytest.mark.parametrize("score, band", [
    (None, None), (0, "kirmizi"), (49, "kirmizi"), (50, "sari"), (69, "sari"), (70, "yesil"), (100, "yesil"),
])
def test_band_thresholds(score, band):
    assert fhs._band(score) == band


# ── Tek kaynak: app.py kopya tutmaz (statik) ─────────────────────────────────
def test_app_uses_business_rules_single_source(app_source, app_function):
    assert "def compose_score(" not in app_source
    assert "from business_rules import compose_score, trend_flags, classify_signal, signal_from_indicators" in app_source
    analyze = app_function("analyze")
    assert "classify_signal(_flags, weekly_dir)" in analyze
    assert "bull_score >= 3" not in analyze          # satır içi kopya kalmadı
    assert "signal_from_indicators(" in app_function("_bar_signal_fast")


# ── VPS (Python 3.12): app.py import edilerek aynı nesne ve aynı sonuç ─────────
def test_app_reexports_same_functions(app_module):
    assert app_module.compose_score is br.compose_score
    assert app_module.signal_from_indicators is br.signal_from_indicators


def test_app_bar_signal_fast_matches_rule(app_module):
    import pandas as pd
    s = lambda v: pd.Series(v)
    # bar 0: 5/5 → AL · bar 1: haftalık 0 → BEKLE · bar 2: tersleri → SAT
    args = (s([110.0, 110.0, 90.0]), s([100.0, 100.0, 100.0]), s([30.0, 30.0, 30.0]),
            s([25.0, 25.0, 15.0]), s([15.0, 15.0, 25.0]), s([1, 1, -1]), s([1, 0, -1]))
    assert [app_module._bar_signal_fast(*args, i) for i in range(3)] == ["AL", "BEKLE", "SAT"]


@pytest.mark.parametrize("flag", [False, True], ids=["bayrak-kapali", "bayrak-acik"])
def test_eod_pass_writes_bp_for_flag_state(app_module, monkeypatch, tmp_path, stock_pool, flag):
    """D-21 uçtan uca (VPS): _run_eod_scoring_pass durumu kayda taşır; önbellek ve
    scores/<gün>.json aynı BP'yi yazar. Disk/ağ yan etkileri monkeypatch ile kapalı."""
    import json
    app = app_module
    if flag:
        monkeypatch.setenv("BP_DIRECTIONAL", "1")
    else:
        monkeypatch.delenv("BP_DIRECTIONAL", raising=False)
    pool = stock_pool("Sanayi", POOL5)
    fund = {d["ticker"]: {"data": {k: v for k, v in d.items() if k not in ("ticker", "sector")}, "ts": 0}
            for d in pool}

    class _FixedNow(app.datetime):
        @classmethod
        def now(cls, tz=None):
            return app.datetime(2026, 9, 24, 15, 30, tzinfo=tz)

    monkeypatch.setattr(app, "datetime", _FixedNow)
    monkeypatch.setattr(app, "_SCORES_DIR", str(tmp_path))
    monkeypatch.setattr(app, "_build_sector_map", lambda results: {"Sanayi": [{"ticker": d["ticker"]} for d in pool]})
    monkeypatch.setattr(app, "_fundamentals_cache", fund)
    monkeypatch.setattr(app, "_sector_stats_cache", {})
    monkeypatch.setattr(app, "_financial_health_cache", {})
    monkeypatch.setattr(app, "_save_sector_stats_to_disk", lambda: None)
    monkeypatch.setattr(app, "_save_health_scores_to_disk", lambda: None)

    app._run_eod_scoring_pass([{"ticker": "AAAA", "signal": "SAT", "signal_strength": 62},
                               {"ticker": "BBBB", "signal": "BEKLE", "signal_strength": None}])

    cache = app._financial_health_cache
    assert cache["AAAA"]["data"]["borsapusula_skoru"] == (51 if flag else 61)
    assert cache["BBBB"]["data"]["borsapusula_skoru"] == (47 if flag else 45)
    assert ("bp_trend" in cache["AAAA"]["data"]) is flag
    with open(tmp_path / "2026-09-24.json", encoding="utf-8") as f:
        saved = json.load(f)["scores"]
    assert {t: e["borsapusula_skoru"] for t, e in saved.items()} == \
        {t: w["data"]["borsapusula_skoru"] for t, w in cache.items()}
