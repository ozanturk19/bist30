"""CPO-1152 P0 — Gemini rate-limiter state dosyası 6 saattir bozuk, haber ölü.

Root cause (VPS'te gerçek gevent+monkey-patch ortamında canlı doğrulandı):
_gemini_rate_acquire_blocking() gevent hub threadpool'unda (maxsize=10) GERÇEK
OS thread'lerinde çalışır. flock() kilitleri open file description'a bağlıdır —
AYNI fd'yi paylaşan farklı thread'ler arasında mutual exclusion SAĞLAMAZ
(yalnız farklı process'ler/farklı open() çağrıları arasında sağlar). Sonuç:
threadpool'daki 2+ thread aynı anda seek+truncate+write'a girip yapışık float
üretti (canlı kanıt: 6 saat, 979 hata/24h). Stres testiyle repro edildi: aynı
gevent ortamında kilitsiz ~1200 çağrıda anında corruption; threading.Lock
eklenince 1500+ çağrıda 0 corruption.

Bu testler fix'in varlığını doğrular:
  - threading.Lock ile intra-process (gerçek thread'ler arası) exclusion var —
    flock()'un SAĞLAMADIĞI, asıl eksik olan katman
  - "a+" (O_APPEND) değil "r+" kullanılıyor
  - float(raw) parse'ı ValueError'a karşı self-heal guard'lı (0.0'a sıfırlanıyor)
"""
import os
import re

_APP_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


def _read_app():
    with open(_APP_PY, encoding="utf-8") as f:
        return f.read()


def _gemini_rate_block(src):
    m = re.search(
        r"_GEMINI_RATE_INTERVAL = .*?(?=\ndef _gemini_rate_acquire\(\))",
        src, re.DOTALL,
    )
    assert m, "_gemini_rate_acquire_blocking bloğu bulunamadı"
    return m.group(0)


def _code_only(body):
    """Yorum satırlarını at — sadece çalıştırılabilir kod satırları kalsın."""
    return "\n".join(l for l in body.splitlines() if not l.strip().startswith("#"))


def test_no_lazy_toctou_open():
    code = _code_only(_gemini_rate_block(_read_app()))
    assert "if _gemini_rate_fh is None:" not in code, (
        "lazy `is None` singleton hâlâ mevcut — gevent threadpool'da TOCTOU race'e açık"
    )


def test_threading_lock_guards_critical_section():
    """Asıl fix: flock() gerçek OS thread'leri arasında (aynı fd'yi paylaşırken)
    exclusion sağlamıyor — threading.Lock bunu kapatan katman (VPS'te canlı
    gevent ortamında stres testiyle doğrulandı)."""
    code = _code_only(_gemini_rate_block(_read_app()))
    assert "_gemini_rate_lock = threading.Lock()" in code, (
        "_gemini_rate_lock tanımlı değil — intra-process thread exclusion yok"
    )
    assert "with _gemini_rate_lock:" in code, (
        "kritik bölüm _gemini_rate_lock ile sarılmamış"
    )


def test_fd_opened_once_at_module_load_before_any_request():
    body = _gemini_rate_block(_read_app())
    assert re.search(r'^_gemini_rate_fh = open\(_GEMINI_RATE_PATH, "r\+"\)', body, re.MULTILINE), (
        "_gemini_rate_fh modül seviyesinde koşulsuz (lazy değil) açılmalı"
    )


def test_uses_r_plus_not_append_mode():
    body = _gemini_rate_block(_read_app())
    assert 'open(_GEMINI_RATE_PATH, "a+")' not in body, (
        "O_APPEND ('a+') hâlâ kullanılıyor — write() her zaman EOF'a zorlanır"
    )


def test_corrupt_state_self_heals_instead_of_raising():
    body = _gemini_rate_block(_read_app())
    assert "except ValueError" in body, (
        "float(raw) parse'ı için self-heal guard yok — bozuk state tekrar 6 saat sürebilir"
    )
    assert "last_slot = 0.0" in body
