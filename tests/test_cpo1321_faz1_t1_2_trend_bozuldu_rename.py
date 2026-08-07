"""CPO-1321 FAZ 1 T1.2 (07.08) — SAT sinyal etiketi yeniden adlandırması.

"Zayıf Trend" → "Trend Bozuldu": SIGNAL_LABELS['SAT'] ve tüm çağıranlar
(app.py, business_rules.py, blog_content.py, manifest.json, 18 şablon)
tek commit'te değişti. Bu, canlı ürün yüzeyinde eski etiketin geri
sızmasını (kısmi rename / yeni kod eklerken eski string kopyalama)
statik olarak yakalar.

ADX trend-gücü etiketi ("Zayıf"/"Orta"/"Güçlü"/"Çok Güçlü",
business_rules.derive_adx_label) bu rename'in KAPSAMI DIŞINDA — ayrı bir
eksen (gösterge gücü, sinyal yönü değil), kasıtlı olarak "Zayıf" kalıyor.
Bu yüzden test tam ifadeyi ("Zayıf Trend") arıyor, tek başına "Zayıf"ı değil.

Bu test kod tabanını statik olarak inceler (regex/grep) — sunucu import
gerektirmez (feedback_local_mac_no_python310).
"""
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_APP_PY = os.path.join(_ROOT, "app.py")
_BUSINESS_RULES_PY = os.path.join(_ROOT, "business_rules.py")
_BLOG_CONTENT_PY = os.path.join(_ROOT, "blog_content.py")
_MANIFEST_JSON = os.path.join(_ROOT, "static", "manifest.json")
_TEMPLATES_DIR = os.path.join(_ROOT, "templates")

_STALE_LABEL = "Zayıf Trend"


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def test_app_py_no_stale_sat_label():
    src = _read(_APP_PY)
    assert _STALE_LABEL not in src, "app.py'de eski 'Zayıf Trend' etiketi kalmış"
    assert "Trend Bozuldu" in src


def test_business_rules_signal_labels_updated():
    src = _read(_BUSINESS_RULES_PY)
    assert _STALE_LABEL not in src
    assert '"SAT": "Trend Bozuldu"' in src


def test_blog_content_no_stale_sat_label():
    src = _read(_BLOG_CONTENT_PY)
    assert _STALE_LABEL not in src


def test_manifest_json_no_stale_sat_label():
    src = _read(_MANIFEST_JSON)
    assert _STALE_LABEL not in src
    assert "Trend Bozuldu" in src


def test_templates_no_stale_sat_label():
    violations = []
    for name in sorted(os.listdir(_TEMPLATES_DIR)):
        if not name.endswith(".html"):
            continue
        path = os.path.join(_TEMPLATES_DIR, name)
        if _STALE_LABEL in _read(path):
            violations.append(name)
    assert not violations, f"şablonlarda eski 'Zayıf Trend' etiketi kalmış: {violations}"
