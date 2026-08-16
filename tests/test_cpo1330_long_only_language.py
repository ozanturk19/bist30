"""CPO-1330 (07.08) — long-only ihlali: SAT entry_note'ta "kısa pozisyon" dili.

Canlı P0: app.py:1708 SAT/IDEAL entry_note'u "...kısa pozisyon için avantajlı
bölge" diyordu — CPO-1191 long-only kararının (blur/paywall kalksa da yön
tavsiyesi hâlâ yalnız AL) canlı ürün yüzeyinde ihlaliydi. Bu, aynı ihlal
sınıfının welcome-email (app.py:2395, önceden düzeltildi) ve blog_content.py
(T0.3, FAZ 0) dışında üçüncü kez bulunmasıydı — kapsam dışı kalmasın diye
statik regresyon testi olarak sabitleniyor (vocab-lint henüz yok).

Bu test kod tabanını statik olarak inceler (regex/grep) — sunucu import
gerektirmez (feedback_local_mac_no_python310).
"""
import os
import re

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_APP_PY = os.path.join(_ROOT, "app.py")
_TEMPLATES_DIR = os.path.join(_ROOT, "templates")

_SHORT_POSITION_PHRASES = ("kısa pozisyon", "kisa pozisyon")


def _signed_ret_block_lines(src):
    """`_signed_ret` fonksiyonunun satır numaraları (1-tabanlı).

    CPO-1335: bu muafiyet eskiden `i == 9925` diye SABİT bir satır numarasıydı.
    app.py'ye üstten satır eklendiğinde kayıyor, deploy gate'i alakasız yerden
    patlatıyordu. Artık fonksiyon kaynaktan bulunuyor — satır numarasından
    bağımsız. Fonksiyon silinirse küme boşalır, yani test GEVŞEMEZ, sıkılaşır.
    """
    lines = src.splitlines()
    start = None
    for idx, line in enumerate(lines):
        if line.startswith("def _signed_ret("):
            start = idx
            break
    if start is None:
        return set()
    end = start + 1
    while end < len(lines):
        cur = lines[end]
        if cur.strip() and not cur.startswith((" ", "\t")):
            break
        end += 1
    return set(range(start + 1, end + 1))


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def test_app_py_no_short_position_language_in_user_facing_strings():
    """entry_note/f-string üretimi kısa-pozisyon dili içermemeli.

    `_signed_ret` docstring'i bilinçli olarak muaf: kullanıcıya hiç render
    edilmeyen dahili backtest yorumu, ürün yüzeyi değil. Muafiyet CPO-1335'te
    sabit satır numarasından (9925) fonksiyon kaynağına taşındı.
    """
    src = _read(_APP_PY)
    exempt = _signed_ret_block_lines(src)
    violations = []
    for i, line in enumerate(src.splitlines(), start=1):
        low = line.lower()
        if any(p in low for p in _SHORT_POSITION_PHRASES):
            if i in exempt:  # _signed_ret — dahili, kullanıcıya render edilmiyor
                continue
            violations.append((i, line.strip()))
    assert not violations, f"kısa pozisyon dili kullanıcı yüzeyine sızmış: {violations}"


_JINJA_COMMENT_RE = re.compile(r"\{#.*?#\}", re.DOTALL)


def test_templates_no_short_position_language():
    """Jinja `{# ... #}` yorumları tarayıcıya hiç render edilmez — dahili
    geliştirici notu, ürün yüzeyi değil (bkz. sinyal_performans.html:168,
    T3.7 kaldırma kararını açıklayan yorum). Taramadan önce çıkarılır."""
    for name in sorted(os.listdir(_TEMPLATES_DIR)):
        if not name.endswith(".html"):
            continue
        path = os.path.join(_TEMPLATES_DIR, name)
        low = _JINJA_COMMENT_RE.sub("", _read(path)).lower()
        for p in _SHORT_POSITION_PHRASES:
            assert p not in low, f"{name}: kısa pozisyon dili bulundu"


def test_sat_entry_note_ideal_branch_is_informational():
    """CPO-1330 kabul ölçütü: SAT/IDEAL entry_note artık R/R diliyle, pozisyon
    tavsiyesi değil — regresyonu önlemek için tam metni sabitliyoruz."""
    src = _read(_APP_PY)
    assert "SL yakın — R/R en avantajlı bölge" in src
    assert "kısa pozisyon için avantajlı bölge" not in src
