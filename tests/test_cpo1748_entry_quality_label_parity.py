"""CPO-1748 (22.09) — giris kalitesi UZAK etiketi iki ayri kelime tasiyordu.

business_rules.ENTRY_QUALITY_LABELS (kaynak) + app.py'deki import-basarisiz
fallback kopyasi + static/bp-vocab.js BP_EQ_LABELS (frontend) ayni 4 anahtar
icin (IDEAL/IYI/DIKKATLI/UZAK) ayni goruntu metnini tasimali. UZAK ozelinde
"Uzak" (Python) / "Kovalama" (JS) sapmasi canliya sizmisti (/tarama "Kovalama"
derken /hisse "Uzak" diyordu) -- SIGNAL_LABELS icin CPO-1321'de yapilan
"tek commit'te her yerde" deseninin bu sozlukte eksik kalmis hali.

Statik regex/grep testi -- sunucu import gerektirmez
(feedback_local_mac_no_python310).

C-61/C-63 (24.09, CPO karari, kanon §2.2): giris kalitesi etiketleri
("Ideal/Kovalama") islem zamanlama dilidir; frontend sozlugu (BP_EQ_LABELS)
C-61'de, son tuketici (hisse Trend Durumu rozeti) C-63'te kalkti. Frontend
paritesi yerine artik YOKLUK kilitlenir. Python tarafi (business_rules +
app.py yedegi) DEV1'in D-39 devaminda kalkana kadar kendi arasinda esit kalir.
"""
import os
import re

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BUSINESS_RULES_PY = os.path.join(_ROOT, "business_rules.py")
_APP_PY = os.path.join(_ROOT, "app.py")
_BP_VOCAB_JS = os.path.join(_ROOT, "static", "bp-vocab.js")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _extract_py_dict(src, var_name):
    m = re.search(re.escape(var_name) + r"\s*=\s*\{([^}]*)\}", src)
    assert m, f"{var_name} sozlugu bulunamadi"
    body = m.group(1)
    return dict(re.findall(r"['\"](\w+)['\"]\s*:\s*['\"]([^'\"]+)['\"]", body))


def test_business_rules_and_app_fallback_match():
    br = _extract_py_dict(_read(_BUSINESS_RULES_PY), "ENTRY_QUALITY_LABELS")
    app_fallback = _extract_py_dict(_read(_APP_PY), "ENTRY_QUALITY_LABELS")
    assert br == app_fallback, (
        f"business_rules.py ve app.py fallback ENTRY_QUALITY_LABELS uyusmuyor: "
        f"{br} != {app_fallback}"
    )


def test_frontend_giris_kalitesi_sozlugu_yok():
    """C-61/C-63: frontend giris kalitesi etiketi tasimaz (yorumlar haric)."""
    js = re.sub(r"/\*.*?\*/", "", _read(_BP_VOCAB_JS), flags=re.S)
    assert "BP_EQ_LABELS" not in js
    assert "Kovalama" not in js


def test_uzak_label_is_kovalama_everywhere():
    br = _extract_py_dict(_read(_BUSINESS_RULES_PY), "ENTRY_QUALITY_LABELS")
    app_fallback = _extract_py_dict(_read(_APP_PY), "ENTRY_QUALITY_LABELS")
    assert br.get("UZAK") == "Kovalama"
    assert app_fallback.get("UZAK") == "Kovalama"
