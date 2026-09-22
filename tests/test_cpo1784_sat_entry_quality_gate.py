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
    """`risk_lvl` -- opt/eq metni yalniz `if signal == "AL":` govdesinde (8
    bosluk girinti) olmali; fonksiyonun kendi seviyesinde (4 bosluk, yon
    kapisi disinda) tekrar bulunmamali."""
    src = _read()
    assert not re.search(r'\n    if opt:\n        risk_lvl \+= f" İdeal giriş', src), (
        "risk_lvl opt/eq metni yon kapisi DISINDA (4 bosluk girinti) bulundu -- "
        "CPO-1784 regresyonu"
    )
    assert re.search(
        r'\n    if signal == "AL":\n(?:[^\n]*\n)*?        if opt:\n'
        r'            risk_lvl \+= f" İdeal giriş bölgesi \{_fmt_tl\(opt\)\} civarı\."\n'
        r'        elif isinstance\(eq, str\) and eq:\n'
        r'            risk_lvl \+= f" Giriş kalitesi: \{ENTRY_QUALITY_LABELS\.get\(eq, eq\)\}\."',
        src,
    ), "risk_lvl opt/eq metni signal == \"AL\" bloguna (8 bosluk girinti) tasinmamis"


def test_api_news_fallback_entry_quality_gated_on_al():
    """`/api/news` algoritmik yedek metninin iki kopyasi da entry_q'yu
    sig == "AL" degilse bos birakmali (CPO-1740 tp_val orneginin aynisi)."""
    src = _read()
    occurrences = re.findall(
        r'entry_q = s\.get\("entry_quality", ""\)(?:\s*if sig == "AL" else "")?',
        src,
    )
    assert len(occurrences) == 2, (
        f"app.py'de beklenen 2 entry_q atama satiri yerine {len(occurrences)} bulundu"
    )
    for occ in occurrences:
        assert 'if sig == "AL" else ""' in occ, (
            "entry_q atamasi yon kapisi olmadan bulundu -- SAT'ta 'ideal giris bolgesi' "
            "metne sizabilir (CPO-1784 regresyonu)"
        )
