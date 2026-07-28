"""CPO-1159 şart (b) — §3.2 deadlock stres testi "regresyon olarak saklanmalı".

Gerçek stres testi gevent hub + threadpool + saniyeler süren eşzamanlı yük
gerektirir — hızlı/deterministik yerel pytest suite'inin kapsamı dışında, bu
yüzden `tools/stress_test_gevent_shared_lock.py` olarak ayrı, VPS'te manuel
çalıştırılan bir araç şeklinde saklandı (DEV-1506/CPO-1158/1159). Bu test o
aracın yanlışlıkla silinmediğini/bozulmadığını doğrular — gelecekteki HERHANGİ
bir "threading.Lock+flock paylaşımlı state" tasarımı (§3.2 LOCK_NB revizyonu
dahil) deploy edilmeden önce bu araçla VPS'te test edilmeli.
"""
import ast
import os

_TOOL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tools", "stress_test_gevent_shared_lock.py",
)


def test_stress_tool_exists():
    assert os.path.isfile(_TOOL_PATH), (
        "tools/stress_test_gevent_shared_lock.py eksik — CPO-1159 şart (b) "
        "(deadlock stres testini regresyon olarak sakla) ihlal ediliyor"
    )


def test_stress_tool_is_syntactically_valid():
    with open(_TOOL_PATH, encoding="utf-8") as f:
        src = f.read()
    ast.parse(src)  # SyntaxError fırlatırsa test fail olur


def test_stress_tool_detects_deadlock_and_lost_updates():
    with open(_TOOL_PATH, encoding="utf-8") as f:
        src = f.read()
    assert "stuck_greenlets" in src, "deadlock/stall tespiti eksik görünüyor"
    assert "LOST UPDATES" in src, "lost-update tespiti eksik görünüyor"
    assert "sys.exit(1)" in src, "deadlock/lost-update bulunca fail (exit 1) etmiyor"
