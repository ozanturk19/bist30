"""CPO-1140 P1 — Yahoo circuit breaker'ın subprocess.TimeoutExpired kör noktası.

27 Tem 2026 13:15 TR: CPO-1139 canlı ölçümünde (13:05 TR) 183/215 ticker hiç
tazelenmemiş bulundu. Kök neden zincirinin bir halkası: `_yahoo_cb_record()`
yalnız subprocess normal dönünce (returncode + stderr) çağrılıyordu; 6 fetch
fonksiyonunun `except subprocess.TimeoutExpired:` dalı hiç çağırmıyordu. Yani
yavaşlık kaynaklı timeout'lar (o gün ölçülen 13-34s fetch'ler) devreye hiç
görünmüyor, breaker açılmıyor, her ticker 180s bütçeyi 3 ardışık subprocess'le
yakmaya devam ediyordu.

Bu test, timeout'un artık 429 ile aynı sayaca/eşiğe dahil olduğunu ve normal
başarı ile sayaç/devrenin sıfırlandığını doğrular. Python 3.9 (yerel Mac)
app.py'yi (3.10+ sözdizimi) import edemediği için fonksiyon kaynaktan izole
exec edilir (bkz. test_cpo1137_canonical_freshness.py).
"""
import logging
import os
import re
import time

import pytest

_APP_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


def _load_yahoo_cb():
    with open(_APP_PY, encoding="utf-8") as f:
        src = f.read()

    const_m = re.search(
        r"_YAHOO_CB_THRESHOLD = .*?\n_YAHOO_CB_COOLDOWN_BASE = .*?\n_YAHOO_CB_COOLDOWN_CAP = .*?\n_yahoo_cb = .*?\n",
        src,
    )
    assert const_m, "_yahoo_cb sabitleri/state dict bulunamadı"

    blocked_m = re.search(r"def _yahoo_cb_blocked\(\).*?\n\n\n", src, re.DOTALL)
    assert blocked_m, "_yahoo_cb_blocked() bulunamadı"

    record_m = re.search(r"def _yahoo_cb_record\(.*?\n\n\n", src, re.DOTALL)
    assert record_m, "_yahoo_cb_record() app.py'de bulunamadı — imza değişmiş olabilir"
    assert "timeout: bool = False" in record_m.group(0), (
        "_yahoo_cb_record() timeout parametresi kaybolmuş — CPO-1140 P1 fix'i regresyona uğramış"
    )

    ns = {"time": time, "logger": logging.getLogger("test_cpo1140")}
    exec(const_m.group(0) + blocked_m.group(0) + record_m.group(0), ns)
    return ns


def _fresh_cb_ns():
    ns = _load_yahoo_cb()
    ns["_yahoo_cb"]["fails"] = 0
    ns["_yahoo_cb"]["open_until"] = 0.0
    ns["_yahoo_cb"]["opens"] = 0
    return ns


def test_timeout_alone_trips_breaker():
    """CPO-1140 çekirdek regresyonu: sadece TimeoutExpired'lar (stderr yok) devreyi açmalı."""
    ns = _fresh_cb_ns()
    record = ns["_yahoo_cb_record"]
    blocked = ns["_yahoo_cb_blocked"]
    for _ in range(3):
        record(False, timeout=True)
    assert blocked(), "3 ardışık timeout breaker'ı açmalı (fix öncesi: hiçbir etkisi yoktu)"


def test_empty_stderr_without_timeout_flag_does_not_count():
    """Eski davranış korunmalı: stderr boş VE timeout=False ise sayılmamalı (gerçek 429 filtresi)."""
    ns = _fresh_cb_ns()
    record = ns["_yahoo_cb_record"]
    blocked = ns["_yahoo_cb_blocked"]
    for _ in range(5):
        record(False, stderr_text="")
    assert not blocked(), "boş stderr + timeout yok → 429 değil, breaker açılmamalı"


def test_429_and_timeout_share_same_counter():
    """429 ile timeout karışık gelse bile ortak eşiğe (3) birlikte sayılmalı."""
    ns = _fresh_cb_ns()
    record = ns["_yahoo_cb_record"]
    blocked = ns["_yahoo_cb_blocked"]
    record(False, stderr_text="HTTP Error 429: Too Many Requests")
    record(False, timeout=True)
    assert not blocked(), "2 hata eşiğin (3) altında, henüz açılmamalı"
    record(False, timeout=True)
    assert blocked(), "3. hata (kaynağı fark etmeksizin) eşiği geçmeli"


def test_success_resets_after_timeouts():
    ns = _fresh_cb_ns()
    record = ns["_yahoo_cb_record"]
    blocked = ns["_yahoo_cb_blocked"]
    record(False, timeout=True)
    record(False, timeout=True)
    record(True)
    assert ns["_yahoo_cb"]["fails"] == 0
    record(False, timeout=True)
    record(False, timeout=True)
    assert not blocked(), "reset sonrası yeniden 2 hata eşiğin altında kalmalı"
