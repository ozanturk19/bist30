"""C-63 (24.09) — D-06 / D-39'un şablon tarafı ("önce tüketici").

Kilitler:
  1. Sinyal yaşı metni SSR'da (_fmt_macros.html `signal_age`) ve istemcide
     (static/bp-format.js `bpSignalAgeText`) aynı girdi için AYNI çıkar. JS node
     ile gerçekten koşar (kaynak grep'i yetmez). Gündem kartı SSR'dan sonra JS
     ile yeniden çizildiği için ayrışma ekranda "flaş" olarak görünür.
  2. gundem.html ve ozet.html, D-06 alanı (`eod_label`) VARKEN ve YOKKEN render
     olur: başlık "Son seansta değişenler · 24 Eylül" / tarihsiz; D-06 öncesi
     closed_message (göreli zamanlı) basılmaz.
  3. Kabul taraması: gundem/ozet/hisse/metodoloji şablonları + bp-format.js
     görünür metin, öznitelik, meta ve JS dizelerinde göreli gün adı 0; hisse'de
     giriş / SL / ideal / kovalama 0 (yorumlar hariç).

Not: app.py py3.9'da içe aktarılamaz; filtreler burada app.py'deki gövdenin
birebir kopyasıdır ve `signal_age_days` sözleşmesi (-10**6 = bilinmiyor) ayrıca
app.py kaynağından kilitlenir.
"""
import json
import os
import re
import shutil
import subprocess
from datetime import date

import pytest

import business_rules as br

jinja2 = pytest.importorskip("jinja2")

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TPL = os.path.join(_ROOT, "templates")
_BP_FORMAT_JS = os.path.join(_ROOT, "static", "bp-format.js")
_APP_PY = os.path.join(_ROOT, "app.py")
_TODAY = date(2026, 9, 24)


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


# ── Filtre kopyaları (app.py) ────────────────────────────────────────────────

def _age_days_filter(today):
    def f(sd):  # app.py signal_age_days_filter
        age = br.signal_date_age_days(sd, today=today)
        return -10**6 if age is None else age
    return f


def _age_text_filter(today):
    def f(sd, ref=None):  # app.py signal_age_text_filter (D-06 sonrası da aynı)
        age = br.signal_date_age_days(sd, today=today)
        if age is None:
            return "—"
        if age == 0:
            return "Bugün"
        if age == 1:
            return "Dün"
        if age < 0:
            return br.derive_signal_date_label(sd, today=today) or "—"
        return f"{age} gün"
    return f


def _env(today=_TODAY):
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(_TPL),
                             autoescape=jinja2.select_autoescape(["html"]))
    for n in re.findall(r"@app\.template_filter\(\s*['\"]([A-Za-z0-9_]+)['\"]", _read(_APP_PY)):
        env.filters[n] = lambda v, *a, **k: v
    env.filters["signal_label"] = lambda c: br.SIGNAL_LABELS.get(c, c)
    env.filters["tr_price"] = lambda v: ("%.2f" % v).replace(".", ",")
    env.filters["signal_age_days"] = _age_days_filter(today)
    env.filters["signal_age_text"] = _age_text_filter(today)
    return env


def test_signal_age_days_sozlesmesi_app_py():
    """Makro "bilinmiyor"u -1000000 ile tanır; app.py filtresi aynı değeri döndürmeli."""
    src = _read(_APP_PY)
    start = src.index("def signal_age_days_filter(")
    body = src[start:src.index("\ndef ", start + 10)]
    assert "-10**6 if age is None else age" in body


# ── 1. SSR makrosu ↔ bpSignalAgeText paritesi ───────────────────────────────

_CASES = [
    ("24.09.2026", (2026, 9, 24)),   # 0 gün -> Son seans
    ("23.09.2026", (2026, 9, 24)),   # 1 gün
    ("22.09.2026", (2026, 9, 24)),
    ("01.01.2026", (2026, 9, 24)),
    ("25.09.2026", (2026, 9, 24)),   # gelecek (veri hatası) -> "25 Eylül"
    ("1.10.2026", (2026, 9, 24)),    # gelecek, dolgusuz
    ("31.12.2025", (2026, 1, 1)),    # yıl sınırı
    ("01.01.2026", (2026, 1, 1)),
    ("02.01.2026", (2026, 1, 1)),
    ("01.01.2027", (2026, 12, 31)),  # gelecek + başka yıl -> "1 Ocak 2027"
    ("05.03.2028", (2026, 9, 24)),
    ("", (2026, 9, 24)),
    ("yok", (2026, 9, 24)),
    ("31.02.2026", (2026, 9, 24)),
    ("2026-09-24", (2026, 9, 24)),
    (None, (2026, 9, 24)),
]

_PROBE = r"""
const fs = require('fs');
const src = fs.readFileSync(process.argv[1], 'utf8');
const cases = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const out = cases.map(function (c) {
  const run = new Function('__T', src +
    '\nbpTodayTr = function () { return __T; };\nreturn bpSignalAgeText(' + JSON.stringify(c[0]) + ');');
  return run({ y: c[1][0], m: c[1][1], d: c[1][2] });
});
console.log(JSON.stringify(out));
"""


def test_ssr_makro_js_paritesi(tmp_path):
    node = shutil.which("node") or shutil.which("nodejs")
    if not node:
        pytest.skip("node yok — parite testi çalıştırılamıyor")
    cases_file = tmp_path / "cases.json"
    cases_file.write_text(json.dumps(_CASES), encoding="utf-8")
    proc = subprocess.run([node, "-e", _PROBE, _BP_FORMAT_JS, str(cases_file)],
                          capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    js_out = json.loads(proc.stdout)

    for (sd, today), js in zip(_CASES, js_out):
        tpl = _env(date(*today)).from_string(
            "{% import '_fmt_macros.html' as bpf %}{{ bpf.signal_age(sd) }}")
        ssr = tpl.render(sd=sd)
        assert ssr == js, f"SSR/JS ayrıştı sd={sd!r} today={today}: ssr={ssr!r} js={js!r}"
    assert js_out[:2] == ["Son seans", "1 gün"]
    assert "25 Eylül" in js_out and "1 Ocak 2027" in js_out


# ── 2. Render: D-06 alanı var / yok ─────────────────────────────────────────

def _stock(t, sig, sd, sector="Banka"):
    return {"ticker": t, "name": t + " A.Ş.", "signal": sig, "signal_date": sd, "sector": sector,
            "price": 10.5, "change_pct": 1.23, "adx": 30.1, "rsi": 55.5, "signal_price": 9.8}


_GLOBALS = {"og_image_url": "/og-image.png", "should_track": False, "cf_beacon_token": ""}


def _gundem(**kw):
    ctx = dict(_GLOBALS,
               ssr_new_signals=[_stock("AAA", "AL", "24.09.2026"), _stock("BBB", "SAT", "24.09.2026")],
               ssr_strong_al=[_stock("CCC", "AL", "23.09.2026"), _stock("DDD", "AL", "10.09.2026")],
               ssr_signal_summary={"al": 40, "sat": 60, "bekle": 115, "total": 215},
               ssr_bilanco_upcoming=[], ssr_market_open=False,
               # D-06 öncesi sunucu metni (göreli zaman taşır, basılmamalı)
               ssr_closed_message="BIST seansı kapandı — yarınki seansta yeni sinyaller görünecek.",
               ssr_updated_at="24.09.2026 19:11:26")
    ctx.update(kw)
    return _env().get_template("gundem.html").render(**ctx)


def _visible(html):
    html = re.sub(r"<script\b[^>]*>.*?</script>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<style\b[^>]*>.*?</style>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<!--.*?-->", " ", html, flags=re.S)
    return re.sub(r"\s+", " ", html)


def _text(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", _visible(html)))


_REL = re.compile(r"(?i)(?<!\w)(bugün\w*|dün(?:kü|den|ün|ü)?|günün|yarın\w*)(?!\w)")


def test_gundem_d06_oncesi_tarihsiz():
    html = _gundem()
    txt = _text(html)
    assert "Son seansta değişenler 2 hisse" in txt
    assert "Süre Son seans" in txt and "Süre 1 gün" in txt and "Süre 14 gün" in txt
    assert "Son seansta BIST'te 40 güçlü trend var; 2 hissenin trend durumu değişti." in html
    assert not _REL.findall(_visible(html)), _REL.findall(_visible(html))


def test_gundem_d06_oncesi_bos_liste_eski_metni_basmaz():
    html = _gundem(ssr_new_signals=[])
    assert "yarınki" not in _visible(html)
    assert "Son seansta durum değiştiren hisse yok" in _text(html)
    assert 'content="Son seansta BIST\'te 40 güçlü trend var; trend durumu değişen hisse yok."' in html


def test_gundem_d06_sonrasi_tarihli():
    html = _gundem(ssr_eod_label="24 Eylül",
                   ssr_closed_message="24 Eylül kapanışında trend durumu değişen hisse yok.")
    assert "Son seansta değişenler · 24 Eylül 2 hisse" in _text(html)
    assert "24 Eylül kapanışında BIST'te 40 güçlü trend var" in html
    assert not _REL.findall(_visible(html))
    bos = _gundem(ssr_new_signals=[], ssr_eod_label="24 Eylül",
                  ssr_closed_message="24 Eylül kapanışında trend durumu değişen hisse yok.")
    assert "24 Eylül kapanışında trend durumu değişen hisse yok." in _text(bos)


def _ozet(**kw):
    al = [_stock("AAA", "AL", "24.09.2026"), _stock("CCC", "AL", "23.09.2026")]
    sat = [_stock("BBB", "SAT", "24.09.2026"), _stock("EEE", "SAT", "10.09.2026", "Enerji")]
    ctx = dict(_GLOBALS, stocks=al + sat, loading=False, al_list=al, sat_list=sat, bekle_list=[],
               new_signals=[al[0], sat[0]], today_str="24.09.2026",
               stock_names={s["ticker"]: s["name"] for s in al + sat})
    ctx.update(kw)
    return _env().get_template("ozet.html").render(**ctx)


def test_ozet_son_seans_ve_arsiv():
    html = _ozet()
    txt = _text(html)
    assert "Son seansta değişenler · 24.09.2026" in txt
    assert "24.09.2026 kapanışında oluştu" in txt
    assert "Son seans · 24.09.2026" in txt and "1 gün · 23.09.2026" in txt
    assert "Sinyal fiyatı: 9,80 ₺" in txt and "Giriş" not in txt
    assert not _REL.findall(_visible(html)), _REL.findall(_visible(html))
    arsiv = _text(_ozet(historical_date="2026-09-18", today_str="18.09.2026"))
    assert "18.09.2026 kapanışında değişenler" in arsiv


# ── 3. Kabul taraması (kaynak) ──────────────────────────────────────────────

_JS_STR = re.compile(r"'(?:\\.|[^'\\\n])*'|\"(?:\\.|[^\"\\\n])*\"|`(?:\\.|[^`\\])*`", re.S)


def _strip_js_comments(js):
    js = re.sub(r"/\*.*?\*/", " ", js, flags=re.S)
    return re.sub(r"(?<![:'\"\\/])//[^\n]*", " ", js)


def _surfaces(path):
    """Görünür yüzeyler: HTML metni + öznitelikler + meta + Jinja ifadeleri ve
    betiklerdeki dize sabitleri. Jinja/HTML/JS yorumları hariç."""
    src = _read(path)
    if path.endswith(".js"):
        return _JS_STR.findall(_strip_js_comments(src))
    src = re.sub(r"\{#.*?#\}", " ", src, flags=re.S)
    src = re.sub(r"<!--.*?-->", " ", src, flags=re.S)
    parts = []

    def _script(m):
        parts.extend(_JS_STR.findall(_strip_js_comments(m.group(1))))
        return " "
    src = re.sub(r"<script\b[^>]*>(.*?)</script>", _script, src, flags=re.S | re.I)
    src = re.sub(r"<style\b[^>]*>.*?</style>", " ", src, flags=re.S | re.I)
    return parts + [src]


@pytest.mark.parametrize("rel", ["templates/gundem.html", "templates/ozet.html",
                                 "templates/hisse.html", "templates/metodoloji.html",
                                 "static/bp-format.js"])
def test_goreli_gun_adi_yok(rel):
    hits = [m.group(0) for part in _surfaces(os.path.join(_ROOT, rel)) for m in _REL.finditer(part)]
    assert not hits, f"{rel}: göreli gün adı {hits}"


def test_hisse_islem_dili_yok():
    trade = re.compile(r"(?i)giriş|\bSL\b|ideal|kovalama")
    hits = [m.group(0) for part in _surfaces(os.path.join(_TPL, "hisse.html"))
            for m in trade.finditer(part)]
    assert not hits, f"hisse.html işlem dili: {hits}"


def test_entry_quality_tuketicisi_yok():
    """D-39: DEV1 `entry_quality` üretmeyi bırakabilsin — hiçbir yüzey okumasın."""
    offenders = []
    for base, ext in (("templates", ".html"), ("static", ".js")):
        for dp, _, fns in os.walk(os.path.join(_ROOT, base)):
            for fn in fns:
                if fn.endswith(ext) and ".bak" not in fn:
                    p = os.path.join(dp, fn)
                    src = re.sub(r"\{#.*?#\}|<!--.*?-->", " ", _read(p), flags=re.S)
                    if re.search(r"(?:\.|['\"])entry_quality\b", _strip_js_comments(src)):
                        offenders.append(os.path.relpath(p, _ROOT))
    assert not offenders, offenders
