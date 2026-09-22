"""CPO-1755 -- MTF paneli (/hisse Zaman Dilimleri) hisselerin ~%95'inde
"veri yok" gösteriyordu, canlı ve sürekli.

Kök neden: `_mtf_warmup_daemon()` (leader process, REFRESH_WORKER=1) her
başladığında `_mtf_cache` BOŞ'tan başlıyordu -- disk cache'i asla
yüklemiyordu (`_load_mtf_cache_from_disk()` çağrısı yalnız `background_refresh`
web/non-leader dallarında vardı, daemon'da yoktu). Daemon 5 ticker'da bir
`_save_mtf_cache_to_disk()` çağırıyor; bu fonksiyon `dict(_mtf_cache)`'i
TÜMÜYLE diske yazıyor (merge değil, overwrite). Yani her leader restart'ında
(CPO-1670 kuralı gereği her deploy'da restart oluyor, bir gecede 7+ kez)
diskteki önceden birikmiş 217 kayıt, yeni turun ilk birkaç kaydıyla
EZİLİYORDU. Canlı ölçüm: last_mtf_cache.json 217 ↔ ~35 kayıt arası
salınıyordu (CPO-1755 raporu, 22.09 ~03:3x TR).

Fix: daemon, turuna başlamadan önce diski belleğe yükler
(`_load_mtf_cache_from_disk()`) -- artık her `_save` çağrısı disk+memory
merge'ini yazıyor, saf overwrite değil.
"""
import json
import logging
import os
import re
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_APP_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


def _read_app():
    with open(_APP_PY, encoding="utf-8") as f:
        return f.read()


def _extract_function_body(src, func_name):
    pattern = rf"def {func_name}\(.*?(?=\ndef |\Z)"
    m = re.search(pattern, src, re.DOTALL)
    return m.group(0) if m else None


# ── statik: daemon turdan önce diski yüklüyor mu ───────────────────────────

def test_warmup_daemon_loads_disk_before_loop():
    src = _read_app()
    body = _extract_function_body(src, "_mtf_warmup_daemon")
    assert body, "_mtf_warmup_daemon() bulunamadı"

    load_idx = body.find("_load_mtf_cache_from_disk()")
    loop_idx = body.find("while True:")
    assert load_idx != -1, (
        "_mtf_warmup_daemon() artık başlamadan önce _load_mtf_cache_from_disk() "
        "çağırmalı -- restart sonrası _mtf_cache boş başlayıp disk overwrite ediyor"
    )
    assert loop_idx != -1, "_mtf_warmup_daemon() içinde 'while True:' bulunamadı"
    assert load_idx < loop_idx, (
        "_load_mtf_cache_from_disk() 'while True:' döngüsünden ÖNCE çağrılmalı "
        "(döngü içinde her turda tekrar çağırmak farklı bir tasarım, bu regresyon "
        "en az turdan-önce-bir-kez garantisini istiyor)"
    )


# ── işlevsel: gerçek _save/_load fonksiyonları restart senaryosunda veri kaybetmiyor mu ──

def _load_disk_bridge_functions(tmp_path):
    """_save_mtf_cache_to_disk / _load_mtf_cache_from_disk'i app.py'den çıkarıp
    izole bir namespace'te çalıştırır (app.py import'u 3.10+ gerektirir, local
    Mac 3.9'da çalışmaz -- bkz. feedback_local_mac_no_python310 memory notu)."""
    src = _read_app()
    save_body = _extract_function_body(src, "_save_mtf_cache_to_disk")
    load_body = _extract_function_body(src, "_load_mtf_cache_from_disk")
    assert save_body and load_body, "_save_mtf_cache_to_disk / _load_mtf_cache_from_disk bulunamadı"

    disk_path = os.path.join(str(tmp_path), "last_mtf_cache.json")

    def _atomic_write_json(path, obj):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f)

    ns = {
        "os": os,
        "json": json,
        "logger": logging.getLogger("test_cpo1755"),
        "_lock": threading.Lock(),
        "_mtf_cache": {},
        "_MTF_CACHE_DISK_PATH": disk_path,
        "_atomic_write_json": _atomic_write_json,
    }
    exec(save_body, ns)
    exec(load_body, ns)
    return ns


def test_restart_then_partial_round_does_not_erase_disk(tmp_path):
    """CPO-1755'in canlıda gözlemlediği 217 -> ~35 salınımını taklit eder."""
    ns = _load_disk_bridge_functions(tmp_path)
    save = ns["_save_mtf_cache_to_disk"]
    load = ns["_load_mtf_cache_from_disk"]

    # Tur 1 (restart öncesi): 217 ticker'ın tamamı işlenmiş, diske yazılmış.
    ns["_mtf_cache"] = {f"TICK{i}": {"data": {"ticker": f"TICK{i}"}, "ts": 1000.0} for i in range(217)}
    save()
    with open(ns["_MTF_CACHE_DISK_PATH"], encoding="utf-8") as f:
        assert len(json.load(f)) == 217

    # Restart: process yeniden başlar, _mtf_cache BOŞ.
    ns["_mtf_cache"] = {}

    # FIX'in sağladığı davranış: daemon turdan önce diski yükler.
    load()
    assert len(ns["_mtf_cache"]) == 217, "restart sonrası disk yüklenmeliydi"

    # Yeni tur: ilk 5 ticker yeniden hesaplanır (daha yeni ts), 5'te bir diske yazılır.
    now = 2000.0
    for i in range(5):
        ns["_mtf_cache"][f"TICK{i}"] = {"data": {"ticker": f"TICK{i}", "fresh": True}, "ts": now}
    save()

    with open(ns["_MTF_CACHE_DISK_PATH"], encoding="utf-8") as f:
        on_disk = json.load(f)
    assert len(on_disk) == 217, (
        f"restart+partial-round sonrası disk {len(on_disk)} kayda düştü -- "
        "CPO-1755'in gözlemlediği 217->~35 salınımı düzelmemiş"
    )
    assert on_disk["TICK0"]["ts"] == now
    assert on_disk["TICK216"]["ts"] == 1000.0


def test_restart_without_load_reproduces_the_bug(tmp_path):
    """Negatif kontrol: fix YOKSA (restart sonrası load() atlanırsa) bug canlanır --
    testin gerçekten fix'i doğruladığını, tesadüfen geçmediğini kanıtlar."""
    ns = _load_disk_bridge_functions(tmp_path)
    save = ns["_save_mtf_cache_to_disk"]

    ns["_mtf_cache"] = {f"TICK{i}": {"data": {}, "ts": 1000.0} for i in range(217)}
    save()

    # Restart, ama _load_mtf_cache_from_disk() ÇAĞRILMIYOR (eski/buggy davranış).
    ns["_mtf_cache"] = {}
    for i in range(5):
        ns["_mtf_cache"][f"TICK{i}"] = {"data": {}, "ts": 2000.0}
    save()

    with open(ns["_MTF_CACHE_DISK_PATH"], encoding="utf-8") as f:
        on_disk = json.load(f)
    assert len(on_disk) == 5, "load() atlanınca disk 5 kayda düşmeliydi (regresyonun kanıtı)"
