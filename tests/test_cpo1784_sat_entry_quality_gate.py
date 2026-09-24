"""CPO-1784 (22.09) — SAT sinyalinde "ideal giriş" vaadi app.py'nin iki
metin kanalında açıktı.

Canlı ölçüm: `build_signal_summary()` (Katman B, 3. madde) SAT hissesinde de
"İdeal giriş bölgesi X ₺ civarı." / "Giriş kalitesi: İdeal." yazıyordu — aynı
sayfanın Katman A metni "somut giriş/hedef seviyesi bu sinyal tipinde
gösterilmez" derken. `/api/news` algoritmik yedek metninde de (iki kopya,
"kayda değer gelişme yok" fallback + boş-snippet guard) aynı ihlal vardı:
"... sinyali aktif, ideal giriş bölgesi. SL: ...".

Kural (ürünün kendi /metodoloji sayfası): BorsaPusula long-only bir üründür,
"ideal giriş" ancak AL sinyalinin yanında bir şey vaat eder. Frontend tarafı
kapı 74 (`tools/long-only-surface-check.py`) ile kilitli; bu test app.py'nin
Python f-string kanallarını kilitler (sunucu import gerektirmez, statik
regex/grep — feedback_local_mac_no_python310).
"""
import os
import re

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_APP_PY = os.path.join(_ROOT, "app.py")


def _read():
    with open(_APP_PY, encoding="utf-8") as f:
        return f.read()


def test_build_signal_summary_entry_quality_gated_on_al():
    """CPO-1793 (kanon §2.2): `risk_lvl` artik hicbir sinyalde "ideal giris
    bolgesi" / "Giris kalitesi" cumlesi uretmez (CPO-1784 AL kapisinin yerini
    tamamen kaldirma aldi)."""
    src = _read()
    assert 'risk_lvl += f" İdeal giriş bölgesi' not in src, "risk_lvl ideal giris cumlesi geri gelmis"
    assert 'risk_lvl += f" Giriş kalitesi:' not in src, "risk_lvl giris kalitesi cumlesi geri gelmis"


def test_api_news_fallback_entry_quality_gated_on_al():
    """`/api/news` algoritmik yedek metni. D-39 (O10, 24.09): giriş kalitesi /
    "giriş bölgesi" / "SL:" / "Hedef:" bu metinden tamamen kalktı (tek kopya,
    betimleyici "Trend dönüş seviyesi (Supertrend)") — CPO-1784'ün AL kapısı
    yerini kaldırmaya bıraktı."""
    src = _read()
    assert not re.findall(r'entry_q = s\.get\("entry_quality"', src), "entry_q geri gelmiş"
    start = src.index("def api_market_news(")
    body = "\n".join(ln for ln in src[start:src.index("\n@app.route", start)].splitlines()
                     if not ln.strip().startswith("#"))   # yorumlar render edilmez
    for bad in (" giriş bölgesi", "SL: ", "| Hedef: ", 's.get("tp1")'):
        assert bad not in body, f"market-news yedek metninde {bad!r} geri gelmiş"
    assert "Trend dönüş seviyesi (Supertrend): " in body
