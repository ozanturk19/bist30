"""§8(b) — bist30 ana process (8003) tamamen hang olsa bile /api/health yanıt versin.

Stdlib http.server ile sıfır bağımlılık — app.py'nin yfinance/gevent import
zincirini hiç yüklemiyor, o yüzden app'in sebep olduğu hiçbir hang'e girmiyor.
Ayrı port + ayrı systemd unit (bist30-health.service), ana process'ten bağımsız.

İç watchdog'lar (health_cron.sh, smoke-watch.sh) DOKUNULMADAN 8003'ü doğrudan
yoklamaya devam eder — sidecar restart-tetikleyici sinyalin yerine geçmez,
sadece dış izleme için "000 timeout" yerine temiz bir 200+body sağlar.

Bkz. ops/specs/bist30-health-sidecar-PLAN.md
"""
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HEARTBEAT_PATH = os.environ.get(
    "HEALTH_HEARTBEAT_PATH",
    "/root/bist30/health_heartbeat.json",
)
STALE_THRESHOLD_S = 30  # 8s snapshot loop + pay
BIND_HOST = "127.0.0.1"
BIND_PORT = int(os.environ.get("HEALTH_SIDECAR_PORT", "8013"))


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/api/health":
            self.send_response(404)
            self.end_headers()
            return
        try:
            with open(HEARTBEAT_PATH) as f:
                snap = json.load(f)
            age = time.time() - snap.get("ts", 0)
            if age > STALE_THRESHOLD_S:
                snap = {
                    "ok": False,
                    "status": "CRITICAL",
                    "message": f"ana process {int(age)}s'dir heartbeat yazmıyor (hung?)",
                    "sidecar": True,
                    "heartbeat_age_s": int(age),
                }
            body = json.dumps(snap).encode()
        except Exception as e:
            body = json.dumps({
                "ok": False,
                "status": "CRITICAL",
                "message": f"heartbeat okunamadı: {e}",
                "sidecar": True,
            }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass  # access log gürültüsü yok


if __name__ == "__main__":
    ThreadingHTTPServer((BIND_HOST, BIND_PORT), Handler).serve_forever()
