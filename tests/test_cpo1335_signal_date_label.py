"""CPO-1335 (08.08) — göreli tarih etiketi kanonik türetimi.

Arayüz "Bugün"/"Dün" etiketini iki DONMUŞ eksenden türetiyordu: `signal_bars`
(bar sayacı) ve `is_new_signal` (analiz anında hesaplanıp payload'a donan
boolean). Ticker o gün tazelenmezse ikisi de bir veya daha fazla gün kayıyor —
canlı ölçüm 08.08.2026'da signal_bars=1'in hem 07.08 hem 06.08 signal_date'ine
düştüğünü gösterdi (payda 215).

Bu test üç şeyi kilitler:
  1. Kanonik türetim doğru: bugün→"Bugün", dün→"Dün", daha eski→GERÇEK tarih.
  2. Bilinmeyen tarih "Bugün"e DÜŞMEZ (eski `bars || 1` tuzağının regresyonu).
  3. Sunucu (business_rules.py) ve istemci (static/bp-format.js) eşikleri
     AYRIŞMAZ — iki dilde iki kopya kural var; biri değişip diğeri kalırsa
     etiket yüzeyden yüzeye çatallanır. Parite testi JS'i node ile gerçekten
     çalıştırır, kaynak grep'iyle yetinmez.

Ayrıca donmuş eksenlerin geri sızmasını statik olarak yakalar (şablonlarda
signal_bars'tan Bugün/Dün türetimi, api_market_summary'de is_new_signal).
"""
import json
import os
import re
import shutil
import subprocess
from datetime import date

import pytest

import business_rules as br

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BP_FORMAT_JS = os.path.join(_ROOT, "static", "bp-format.js")
_PROBE_JS = os.path.join(_ROOT, "tests", "bp_format_probe.js")
_APP_PY = os.path.join(_ROOT, "app.py")
_TEMPLATES_DIR = os.path.join(_ROOT, "templates")

_TODAY = date(2026, 8, 8)


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _strip_py_comments(src):
    """Tam satır `#` yorumlarını at — guard koda baksın, açıklamaya değil."""
    return "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))


def _strip_tpl_comments(src):
    """JS `/* */` ve Jinja `{# #}` yorum bloklarını at.

    Aksi hâlde düzeltmenin KENDİ açıklaması guard'ı tetikliyor: bir kuralın
    kendi gerekçesini yasaklaması, kaldırdığımız sabit-satır tuzağıyla aynı
    sınıftan bir kırılganlık.
    """
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    src = re.sub(r"\{#.*?#\}", "", src, flags=re.S)
    return src


# ── 1. Kanonik türetim ──────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "signal_date,expected_label,expected_key",
    [
        ("08.08.2026", "Bugün", "today"),
        ("07.08.2026", "Dün", "yesterday"),
        # CPO-1335'in tam vakası: RYSAS/PARSN bars=1 ama signal_date 06.08 idi;
        # ekranda "Bugün" yazıyordu. Artık gerçek tarihini yazmalı.
        ("06.08.2026", "06.08.2026", "older"),
        ("05.08.2026", "05.08.2026", "older"),
        ("24.06.2026", "24.06.2026", "older"),
        # Yıl/ay sınırı
        ("31.12.2025", "31.12.2025", "older"),
    ],
)
def test_derive_label(signal_date, expected_label, expected_key):
    assert br.derive_signal_date_label(signal_date, today=_TODAY) == expected_label
    assert br.derive_signal_date_key(signal_date, today=_TODAY) == expected_key


def test_gun_sinirlari():
    """Sınır günleri kaymasın — ay ve yıl geçişi dahil."""
    assert br.derive_signal_date_label("01.08.2026", today=date(2026, 8, 1)) == "Bugün"
    assert br.derive_signal_date_label("31.07.2026", today=date(2026, 8, 1)) == "Dün"
    assert br.derive_signal_date_label("01.01.2026", today=date(2026, 1, 1)) == "Bugün"
    assert br.derive_signal_date_label("31.12.2025", today=date(2026, 1, 1)) == "Dün"


def test_is_signal_from_today_donmus_bayrak_yerine():
    """Donmuş is_new_signal yerine kullanılan okuma-anı yordamı."""
    assert br.is_signal_from_today("08.08.2026", today=_TODAY) is True
    assert br.is_signal_from_today("07.08.2026", today=_TODAY) is False
    # RYSAS vakası: payload'da is_new_signal=True idi, gerçekte bugüne ait değil.
    assert br.is_signal_from_today("06.08.2026", today=_TODAY) is False
    assert br.is_signal_from_today(None, today=_TODAY) is False


# ── 2. Bilinmeyen "Bugün"e düşmez (bars || 1 tuzağının regresyonu) ──────────

@pytest.mark.parametrize(
    "bad",
    [None, "", "   ", "yok", "2026-08-08", "8/8/2026", "31.02.2026", "00.00.0000", 0, 1, [], {}],
)
def test_bilinmeyen_tarih_bugune_dusmez(bad):
    """Ayrıştırılamayan tarih ETİKET ÜRETMEZ — sessizce "Bugün" olmaz."""
    assert br.derive_signal_date_label(bad, today=_TODAY) is None
    assert br.derive_signal_date_key(bad, today=_TODAY) == "unknown"
    assert br.signal_date_age_days(bad, today=_TODAY) is None
    assert br.is_signal_from_today(bad, today=_TODAY) is False


def test_gelecek_tarih_bugun_demez():
    """Saat kayması/bozuk veri gelecek tarih üretirse "Bugün" yazma."""
    assert br.derive_signal_date_label("09.08.2026", today=_TODAY) == "09.08.2026"
    assert br.derive_signal_date_key("09.08.2026", today=_TODAY) == "older"


# ── 3. Sunucu ↔ istemci paritesi (JS gerçekten çalıştırılır) ────────────────

_PARITY_CASES = [
    {"signal_date": "08.08.2026", "today": [2026, 8, 8]},
    {"signal_date": "07.08.2026", "today": [2026, 8, 8]},
    {"signal_date": "06.08.2026", "today": [2026, 8, 8]},
    {"signal_date": "05.08.2026", "today": [2026, 8, 8]},
    {"signal_date": "24.06.2026", "today": [2026, 8, 8]},
    {"signal_date": "31.07.2026", "today": [2026, 8, 1]},
    {"signal_date": "01.08.2026", "today": [2026, 8, 1]},
    {"signal_date": "31.12.2025", "today": [2026, 1, 1]},
    {"signal_date": "01.01.2026", "today": [2026, 1, 1]},
    {"signal_date": "09.08.2026", "today": [2026, 8, 8]},
    {"signal_date": "", "today": [2026, 8, 8]},
    {"signal_date": "yok", "today": [2026, 8, 8]},
    {"signal_date": "2026-08-08", "today": [2026, 8, 8]},
    {"signal_date": "31.02.2026", "today": [2026, 8, 8]},
]


def test_sunucu_istemci_paritesi(tmp_path):
    """business_rules.py ile static/bp-format.js AYNI sonucu vermeli.

    JS kaynağını grep'lemek yetmez (feedback_kural_da_kanitlanmali) — node ile
    gerçekten çalıştırıp değer karşılaştırıyoruz.
    """
    node = shutil.which("node") or shutil.which("nodejs")
    if not node:
        pytest.skip("node yok — parite testi çalıştırılamıyor")
    assert os.path.exists(_BP_FORMAT_JS), "static/bp-format.js bulunamadı"
    assert os.path.exists(_PROBE_JS), "tests/bp_format_probe.js bulunamadı"

    cases_file = tmp_path / "cases.json"
    cases_file.write_text(json.dumps(_PARITY_CASES), encoding="utf-8")

    proc = subprocess.run(
        [node, _PROBE_JS, _BP_FORMAT_JS, str(cases_file)],
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, f"node koşumu başarısız: {proc.stderr}"
    js_out = json.loads(proc.stdout)
    assert len(js_out) == len(_PARITY_CASES)

    for case, js in zip(_PARITY_CASES, js_out):
        today = date(*case["today"])
        sd = case["signal_date"]
        py_label = br.derive_signal_date_label(sd, today=today)
        py_key = br.derive_signal_date_key(sd, today=today)
        py_age = br.signal_date_age_days(sd, today=today)
        py_today = br.is_signal_from_today(sd, today=today)
        ctx = f"signal_date={sd!r} today={today}"
        assert js["label"] == py_label, f"etiket ayrıştı ({ctx}): js={js['label']!r} py={py_label!r}"
        assert js["key"] == py_key, f"anahtar ayrıştı ({ctx}): js={js['key']!r} py={py_key!r}"
        assert js["age"] == py_age, f"yaş ayrıştı ({ctx}): js={js['age']!r} py={py_age!r}"
        assert js["today"] == py_today, f"bugün-mü ayrıştı ({ctx}): js={js['today']!r} py={py_today!r}"


def test_js_kanonik_sozluk_esittir():
    """Etiket dizeleri iki tarafta da aynı yazılmış olmalı."""
    js = _read(_BP_FORMAT_JS)
    for value in br.SIGNAL_DATE_LABELS.values():
        assert f"'{value}'" in js, f"bp-format.js kanonik etiketi taşımıyor: {value}"


# ── 4. Donmuş eksenlerin geri sızması ───────────────────────────────────────

def test_market_summary_donmus_is_new_signal_kullanmaz():
    """api_market_summary hero'yu donmuş is_new_signal'den üretmemeli.

    Kök neden: bayrak analiz anında donuyor; bayat ticker'da eski günün True'su
    taşınıyordu (RYSAS 06.08 → hero "bugün güçlü trende geçti" diyordu).
    """
    src = _read(_APP_PY)
    start = src.index("def api_market_summary(")
    end = src.index("\n@app.route", start)
    body = _strip_py_comments(src[start:end])
    assert "is_new_signal" not in body, (
        "api_market_summary hâlâ donmuş is_new_signal filtreliyor — "
        "business_rules.is_signal_from_today(signal_date) kullanılmalı"
    )
    assert "is_signal_from_today" in body, (
        "api_market_summary okuma-anı tarih kontrolü kullanmıyor"
    )


def test_sablonlar_bars_uzerinden_bugun_dun_turetmez():
    """Şablonlar göreli etiketi bar sayacından türetmemeli.

    Kapsam elle taşınmaz — templates/ dizini taranır (feedback:
    yuzey_kapsami_route_tablosundan). .bak dosyaları ölü, hariç.
    """
    offenders = []
    for name in sorted(os.listdir(_TEMPLATES_DIR)):
        if not name.endswith(".html") or ".bak" in name:
            continue
        src = _strip_tpl_comments(_read(os.path.join(_TEMPLATES_DIR, name)))
        # bar sayacını sessizce 1'e düşüren fallback (bilinmeyen -> "Bugün")
        for needle in ("bars || 1", "bars||1", "signal_bars or 1"):
            if needle in src:
                offenders.append(f"{name}: `{needle}` sessiz fallback")
    assert not offenders, "Donmuş bar ekseni geri sızdı:\n" + "\n".join(offenders)
