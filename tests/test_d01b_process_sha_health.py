"""D-01b — /api/health `processes` alanı: web + macro + refresh süreçlerinin git sha'sı.

Yardımcılar app.py'den çıkarılıp izole çalıştırılır (app import'u ağır).
Kabul: canlı süreçler listelenir, ölü pid elenir, roller ayrı dosyada.
"""
import hashlib
import json
import os
import re
import tempfile

_APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


def _load(tmp_role_env=None):
    src = open(_APP, encoding="utf-8").read()
    start = src.index("_PROC_SHA_ROLE = (")
    end = src.index("_register_process_sha()\n", start)
    block = src[start:end]
    ns = {"os": os, "json": json, "time": __import__("time"),
          "__file__": _APP, "_GIT_SHA": "abc1234"}
    exec(block, ns)
    return ns


def test_web_role_by_default(monkeypatch):
    monkeypatch.delenv("BP_ROLE", raising=False)
    monkeypatch.delenv("REFRESH_WORKER", raising=False)
    assert _load()["_PROC_SHA_ROLE"] == "web"


def test_macro_role_wins_over_refresh_flag(monkeypatch):
    monkeypatch.setenv("BP_ROLE", "macro")
    monkeypatch.setenv("REFRESH_WORKER", "1")
    assert _load()["_PROC_SHA_ROLE"] == "macro"


def test_refresh_role(monkeypatch):
    monkeypatch.delenv("BP_ROLE", raising=False)
    monkeypatch.setenv("REFRESH_WORKER", "1")
    assert _load()["_PROC_SHA_ROLE"] == "refresh"


def test_collect_lists_live_and_drops_dead(monkeypatch):
    monkeypatch.delenv("BP_ROLE", raising=False)
    monkeypatch.delenv("REFRESH_WORKER", raising=False)
    ns = _load()
    macro_path = ns["_proc_sha_path"]("macro")
    refresh_path = ns["_proc_sha_path"]("refresh")
    try:
        json.dump({"role": "macro", "pid": os.getpid(), "git_sha": "abc1234"}, open(macro_path, "w"))
        json.dump({"role": "refresh", "pid": 2 ** 22 + 12345, "git_sha": "old0000"}, open(refresh_path, "w"))
        roles = {p["role"]: p for p in ns["_collect_process_shas"]()}
        assert set(roles) == {"web", "macro"}
        assert len({p["git_sha"] for p in roles.values()}) == 1
    finally:
        for p in (macro_path, refresh_path):
            if os.path.exists(p):
                os.remove(p)


def test_path_isolated_per_app_dir():
    ns = _load()
    h = hashlib.md5(os.path.dirname(_APP).encode()).hexdigest()[:8]
    assert h in ns["_proc_sha_path"]("macro")


def test_health_route_exposes_processes():
    src = open(_APP, encoding="utf-8").read()
    assert re.search(r'resp\["processes"\]\s*=\s*_collect_process_shas\(\)', src)
