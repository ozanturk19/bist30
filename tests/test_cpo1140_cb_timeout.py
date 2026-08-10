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
        r"_YAHOO_CB_THRESHOLD = .*?\n_yahoo_cb = \{.*?\}.*?\n",
        src, re.DOTALL,
    )
    assert const_m, "_yahoo_cb sabitleri/state dict bulunamadı"
    assert "_YAHOO_CB_RESET_WINDOW" in const_m.group(0), (
        "_YAHOO_CB_RESET_WINDOW sabiti kaybolmuş — CPO-1141 opens-reset fix'i regresyona uğramış"
    )
    assert '"last_open_ts"' in const_m.group(0), (
        "_yahoo_cb['last_open_ts'] state alanı kaybolmuş — CPO-1141 opens-reset fix'i regresyona uğramış"
    )
    assert '"window_skips"' in const_m.group(0), (
        "_yahoo_cb['window_skips'] state alanı kaybolmuş — CPO-1317 §4(a) telemetri fix'i regresyona uğramış"
    )

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
    ns["_yahoo_cb"]["last_open_ts"] = 0.0
    return ns


def test_timeout_alone_trips_breaker():
    """CPO-1140 çekirdek regresyonu: sadece TimeoutExpired'lar (stderr yok) devreyi açmalı."""
    ns = _fresh_cb_ns()
    record = ns["_yahoo_cb_record"]
    blocked = ns["_yahoo_cb_blocked"]
    for _ in range(ns["_YAHOO_CB_THRESHOLD"]):
        record(False, timeout=True)
    assert blocked(), "eşik kadar ardışık timeout breaker'ı açmalı (fix öncesi: hiçbir etkisi yoktu)"


def test_empty_stderr_without_timeout_flag_does_not_count():
    """Eski davranış korunmalı: stderr boş VE timeout=False ise sayılmamalı (gerçek 429 filtresi)."""
    ns = _fresh_cb_ns()
    record = ns["_yahoo_cb_record"]
    blocked = ns["_yahoo_cb_blocked"]
    for _ in range(5):
        record(False, stderr_text="")
    assert not blocked(), "boş stderr + timeout yok → 429 değil, breaker açılmamalı"


def test_429_and_timeout_share_same_counter():
    """429 ile timeout karışık gelse bile ortak eşiğe birlikte sayılmalı."""
    ns = _fresh_cb_ns()
    record = ns["_yahoo_cb_record"]
    blocked = ns["_yahoo_cb_blocked"]
    threshold = ns["_YAHOO_CB_THRESHOLD"]
    record(False, stderr_text="HTTP Error 429: Too Many Requests")
    for _ in range(threshold - 2):
        record(False, timeout=True)
    assert not blocked(), "eşiğin altında, henüz açılmamalı"
    record(False, timeout=True)
    assert blocked(), "eşiği tamamlayan hata (kaynağı fark etmeksizin) devreyi açmalı"


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


def test_lone_success_does_not_collapse_escalation():
    """CPO-1141 canlı kanıt: 4 paralel worker'dan TEK başarı, devam eden degradasyon
    sırasında "opens" escalation seviyesini sıfırlamamalı (eski davranış: opens
    3->1->2->3 döngüsüne giriyordu, backoff hiç derinleşmiyordu)."""
    ns = _fresh_cb_ns()
    record = ns["_yahoo_cb_record"]
    for _ in range(ns["_YAHOO_CB_THRESHOLD"]):
        record(False, timeout=True)
    assert ns["_yahoo_cb"]["opens"] == 1

    record(True)  # 4 worker'dan biri şans eseri başarılı oldu
    assert ns["_yahoo_cb"]["opens"] == 1, "izole başarı escalation seviyesini silmemeli"

    for _ in range(ns["_YAHOO_CB_THRESHOLD"]):
        record(False, timeout=True)
    assert ns["_yahoo_cb"]["opens"] == 2, "escalation 1'den devam etmeli, 1'den değil sıfırdan"


def test_opens_resets_after_true_recovery_window():
    """RESET_WINDOW süresi (gerçek toparlanma) geçtikten sonra başarı escalation'ı sıfırlamalı."""
    ns = _fresh_cb_ns()
    record = ns["_yahoo_cb_record"]
    for _ in range(ns["_YAHOO_CB_THRESHOLD"]):
        record(False, timeout=True)
    assert ns["_yahoo_cb"]["opens"] == 1

    ns["_yahoo_cb"]["last_open_ts"] = time.time() - ns["_YAHOO_CB_RESET_WINDOW"] - 100  # aşıldı
    record(True)
    assert ns["_yahoo_cb"]["opens"] == 0, "uzun sessizlik sonrası başarı gerçek toparlanma sayılmalı"


def test_window_skips_resets_alongside_opens_on_true_recovery():
    """CPO-1317 §4(a) APPROVE: window_skips (devre açıkken atlanan fetch sayısı,
    6 fetch fonksiyonunda _yahoo_cb_blocked() dalında artırılır — bu harness'ın
    dışında, app.py'de) gerçek toparlanmada opens ile BİRLİKTE sıfırlanmalı,
    aksi halde bir sonraki pencerenin sayacı öncekinden devralınır (yanlış N)."""
    ns = _fresh_cb_ns()
    record = ns["_yahoo_cb_record"]
    for _ in range(ns["_YAHOO_CB_THRESHOLD"]):
        record(False, timeout=True)
    assert ns["_yahoo_cb"]["opens"] == 1

    # 6 fetch fonksiyonunun _yahoo_cb_blocked() dalında yapacağı artırımı simüle et
    ns["_yahoo_cb"]["window_skips"] = 211

    ns["_yahoo_cb"]["last_open_ts"] = time.time() - ns["_YAHOO_CB_RESET_WINDOW"] - 100  # aşıldı
    record(True)
    assert ns["_yahoo_cb"]["window_skips"] == 0, (
        "gerçek toparlanmada window_skips sıfırlanmalı — aksi halde sonraki pencereye sızar"
    )


def test_window_skips_survives_transient_lone_success():
    """opens gibi window_skips de İZOLE bir başarıyla (RESET_WINDOW dolmadan) silinmemeli —
    aksi halde 4 paralel worker'dan şans eseri gelen tek başarı sayaçı gerçek dışı sıfırlar."""
    ns = _fresh_cb_ns()
    record = ns["_yahoo_cb_record"]
    for _ in range(ns["_YAHOO_CB_THRESHOLD"]):
        record(False, timeout=True)
    ns["_yahoo_cb"]["window_skips"] = 42

    record(True)  # RESET_WINDOW dolmadı — izole başarı
    assert ns["_yahoo_cb"]["window_skips"] == 42, "izole başarı window_skips'i silmemeli"
