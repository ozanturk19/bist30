"""§8(b) health_sidecar.py — 3 senaryo: taze / stale / missing heartbeat.

engineering_discipline checklist madde 4a: standalone unit test.
"""
import json
import os
import socket
import sys
import threading
import time
import urllib.error
import urllib.request

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture
def sidecar(tmp_path):
    heartbeat_path = tmp_path / "health_heartbeat.json"
    port = _free_port()
    os.environ["HEALTH_HEARTBEAT_PATH"] = str(heartbeat_path)
    os.environ["HEALTH_SIDECAR_PORT"] = str(port)
    sys.modules.pop("health_sidecar", None)
    import health_sidecar
    server = health_sidecar.ThreadingHTTPServer(
        (health_sidecar.BIND_HOST, health_sidecar.BIND_PORT), health_sidecar.Handler
    )
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.1)
    try:
        yield heartbeat_path, port
    finally:
        server.shutdown()
        server.server_close()


def _get(port):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=2) as r:
        return r.status, json.loads(r.read())


def test_fresh_heartbeat_passthrough(sidecar):
    heartbeat_path, port = sidecar
    heartbeat_path.write_text(json.dumps({"ok": True, "status": "OK", "ts": time.time()}))
    status, body = _get(port)
    assert status == 200
    assert body["status"] == "OK"
    assert "sidecar" not in body  # taze heartbeat aynen geçiyor, sidecar override yok


def test_stale_heartbeat_returns_critical(sidecar):
    heartbeat_path, port = sidecar
    heartbeat_path.write_text(json.dumps({"ok": True, "status": "OK", "ts": time.time() - 60}))
    status, body = _get(port)
    assert status == 200
    assert body["status"] == "CRITICAL"
    assert body["sidecar"] is True
    assert body["heartbeat_age_s"] >= 30


def test_missing_heartbeat_returns_critical(sidecar):
    heartbeat_path, port = sidecar
    status, body = _get(port)
    assert status == 200
    assert body["status"] == "CRITICAL"
    assert body["sidecar"] is True


def test_unknown_path_returns_404(sidecar):
    _, port = sidecar
    req = urllib.request.Request(f"http://127.0.0.1:{port}/other")
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(req, timeout=2)
    assert exc.value.code == 404
