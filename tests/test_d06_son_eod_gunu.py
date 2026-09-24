"""D-06 — "Son seansta değişenler" son EOD gününe bağlı + göreli zaman yok.

QA 24.09: /gundem listesi seans içinde takvim gününe (24.09) bakıp boştu, oysa
veri 23.09 kapanışınındı ve o gün 13 hisse durum değiştirmişti (8 Trend Bozuldu
+ 5 Yatay'a dönüş; Yatay'a dönüş CPO-1666 #3 gereği listelenmez).
Referans gün takvimden değil veriden (son bar günü) türer; hafta sonu/tatil güvenli.

Python 3.9 app.py'yi import edemediği için fonksiyonlar kaynaktan izole exec
edilir (bkz. test_cpo1587_sektor_gundem_index_ssr.py).
"""
import ast
import os
import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

import business_rules as br
import takvim

_APP_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
with open(_APP_PY, encoding="utf-8") as _f:
    _SRC = _f.read()

_RELATIVE = re.compile(r"(?i)\b(bugün\w*|dün(kü|den|e)?|yarın\w*|günün)\b")
_TR_MONTHS = dict(enumerate(("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
                             "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"), start=1))
_THU = date(2026, 9, 24)   # 23.09 (Çar) verisi, 24.09 seans içi
_SAT = date(2026, 9, 26)   # hafta sonu


def _qa_2409_stocks():
    """Canlı 24.09 16:11 dağılımı: son bar 23.09; 23.09'da 8 SAT + 5 BEKLE değişti."""
    rows = [{"ticker": f"S{i}", "signal": "SAT", "signal_date": "23.09.2026"} for i in range(8)]
    rows += [{"ticker": f"B{i}", "signal": "BEKLE", "signal_date": "23.09.2026"} for i in range(5)]
    rows += [{"ticker": f"O{i}", "signal": "AL", "signal_date": "22.09.2026"} for i in range(4)]
    for r in rows:
        r["bar_date"] = "23.09.2026"
    return rows


# ── business_rules.last_eod_day ──────────────────────────────────────────────

def test_last_eod_day_is_last_bar_day_not_calendar():
    assert br.last_eod_day(_qa_2409_stocks(), today=_THU) == date(2026, 9, 23)


def test_last_eod_day_weekend_uses_friday_data():
    stocks = [{"signal_date": "22.09.2026", "bar_date": "25.09.2026"},
              {"signal_date": "25.09.2026", "bar_date": "25.09.2026"}]
    assert br.last_eod_day(stocks, today=_SAT) == date(2026, 9, 25)


def test_last_eod_day_no_change_on_last_session_still_that_session():
    # Son seansta hiç değişim yoksa liste boş kalmalı, bir önceki güne kaymamalı.
    stocks = [{"signal_date": "22.09.2026", "bar_date": "23.09.2026"}]
    assert br.last_eod_day(stocks, today=_THU) == date(2026, 9, 23)


def test_last_eod_day_falls_back_to_signal_date_and_ignores_future_and_junk():
    # bar_date'siz eski önbellek: signal_date alt sınırdır; gelecek/bozuk değer yok sayılır.
    stocks = [{"signal_date": "23.09.2026"}, {"signal_date": "30.09.2026"},
              {"signal_date": "bozuk"}, "not-a-dict", {}]
    assert br.last_eod_day(stocks, today=_THU) == date(2026, 9, 23)
    assert br.last_eod_day([], today=_THU) is None
    assert br.last_eod_day(None, today=_THU) is None


# ── app.py fonksiyonları (kaynaktan izole exec) ─────────────────────────────

class _FakeLock:
    def __enter__(self):
        return None

    def __exit__(self, *a):
        return False


def _extract(func_name):
    m = re.search(r"def " + re.escape(func_name) + r"\(.*?\n\n\n", _SRC, re.DOTALL)
    assert m, f"{func_name} bulunamadı"
    return m.group(0)


def _ns(**extra):
    ns = {
        "datetime": datetime, "date": date, "_TZ_TR": ZoneInfo("Europe/Istanbul"),
        "_TR_MONTHS": _TR_MONTHS,
        "parse_signal_date": br.parse_signal_date,
        "signal_date_age_days": br.signal_date_age_days,
        "is_signal_from_today": br.is_signal_from_today,
        "derive_signal_date_label": br.derive_signal_date_label,
        "last_eod_day": br.last_eod_day,
    }
    ns.update(extra)
    for fn in ("_tr_month", "_tr_day_month"):
        exec(_extract(fn), ns)
    return ns


def test_gundem_new_signals_tied_to_last_eod_day_qa_2409():
    ns = _ns(_lock=_FakeLock(), _cache={"data": _qa_2409_stocks()}, INDEX_TICKERS={"XU030", "XU100"},
             _takvim=takvim, _market_open=lambda now: True,
             _data_quality_snapshot=lambda stocks: {"updated_at": "23.09.2026 18:14:35"})
    exec(_extract("_compute_gundem_data"), ns)
    g = ns["_compute_gundem_data"]()
    assert len(g["new_signals"]) == 8                      # önce: 0 (takvim 24.09)
    assert all(s["signal"] == "SAT" for s in g["new_signals"])
    assert g["eod_date"] == "2026-09-23" and g["eod_label"] == "23 Eylül"
    assert g["closed_message"] == "23 Eylül kapanışında trend durumu değişen hisse yok."


def test_commentary_uses_date_not_relative_words():
    ns = _ns()
    exec(_extract("_signal_dur_text"), ns)
    dur = ns["_signal_dur_text"]
    today = datetime.now(ZoneInfo("Europe/Istanbul")).date()
    txt = dur(today.strftime("%d.%m.%Y"), 1, "Trend Bozuldu")   # önce: "Bugün Trend Bozuldu sinyali oluştu"
    assert txt == f"{today.day} {_TR_MONTHS[today.month]} kapanışında Trend Bozuldu sinyali oluştu"
    assert not _RELATIVE.search(txt)
    assert dur("", 1, "Güçlü Trend") == "Son seansta Güçlü Trend sinyali oluştu"
    assert dur("", 5, "Güçlü Trend") == "Son 5 gündür Güçlü Trend sinyali aktif"
    assert dur("01.01.2020", 3, "Güçlü Trend").startswith("Son ")


def test_chart_commentary_regenerated_every_request():
    # Diskteki grafik yorumu eski kodun "Bugün/Dün" metnini taşıyabilir; yorum
    # artık yalnız sinyal uyuşmazlığında değil her istekte yeniden üretilir.
    fn = next(n for n in ast.walk(ast.parse(_SRC))
              if isinstance(n, ast.FunctionDef) and n.name == "api_stock_chart")
    calls = [n for n in ast.walk(fn) if isinstance(n, ast.Call)
             and getattr(n.func, "id", "") == "_generate_commentary"]
    assert len(calls) == 1
    for node in ast.walk(fn):
        if isinstance(node, ast.If) and "chart_sig" in ast.dump(node.test):
            assert "_generate_commentary" not in ast.dump(node), "yorum yine uyuşmazlığa bağlandı"
    ns = _ns()
    exec(_extract("_signal_dur_text"), ns)
    assert ns["_signal_dur_text"](None, None, "Güçlü Trend") == "Son seansta Güçlü Trend sinyali oluştu"


def test_signal_age_phrase_recent_is_dated():
    ns = _ns()
    exec(_extract("signal_age_phrase_filter"), ns)
    phrase = ns["signal_age_phrase_filter"]
    assert phrase("23.09.2026", today="2026-09-24") == "23 Eylül kapanışında oluştu"
    assert phrase("24.09.2026", today="2026-09-24") == "24 Eylül kapanışında oluştu"
    assert phrase("20.09.2026", today="2026-09-24") == "4 gün önce oluştu"
    assert phrase("bozuk", today="2026-09-24") == "—"


# ── Üretilen metin taraması (app.py string sabitleri) ───────────────────────

# Bilinçli istisnalar: kullanıcıya giden metin DEĞİL.
_ALLOWED = (
    "Bugün", "Dün",            # SIGNAL_DATE_LABELS yedeği: business_rules + static/bp-format.js ortak kanonu (CPO)
    "bugünün tarihi",          # model çıktısı ayıklama öneki (_skip_prefixes)
)


def _is_prompt(text):
    # Gemini istemleri (modele talimat/tarih bağlamı), sayfaya basılmaz.
    return "KURAL" in text or text.startswith("KIMLIK:") or "(son 7 gün)\nBugün: " in text


def test_app_generated_strings_have_no_relative_time_words():
    tree = ast.parse(_SRC)
    skip = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list) and body and isinstance(body[0], ast.Expr) \
                and isinstance(body[0].value, ast.Constant):
            skip.add(id(body[0].value))                   # docstring
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "logger":
            skip.update(id(n) for n in ast.walk(node))    # log satırı
    hits = sorted({(n.lineno, n.value[:80]) for n in ast.walk(tree)
                   if isinstance(n, ast.Constant) and isinstance(n.value, str)
                   and id(n) not in skip and n.value not in _ALLOWED
                   and not _is_prompt(n.value) and _RELATIVE.search(n.value)})
    assert hits == [], f"göreli zaman sözcüğü üreten metin: {hits}"
