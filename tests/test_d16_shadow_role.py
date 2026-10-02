"""D-16: BP_ROLE=shadow kilit tutmaz, prod kilit/durum dosyalarını açmaz; shadow_compare yardımcıları."""
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

_CODE = r"""
import os, app
fns = [app._is_notify_leader_blocking, app._is_bg_leader_blocking, app._is_digest_leader_blocking,
       app._is_gemini_leader_blocking, app._is_macro_leader_blocking]
print('LEADERS', [f() for f in fns])
fds = [os.readlink('/proc/self/fd/' + x) for x in os.listdir('/proc/self/fd') if os.path.exists('/proc/self/fd/' + x)]
print('FDS', [p for p in fds if '/bp_' in p and p.endswith('.lock') or p.endswith('news_inflight.json')])
"""


@pytest.mark.skipif(sys.version_info < (3, 10) or not os.path.isdir("/proc/self/fd"),
                    reason="app.py Python 3.10+ ve /proc ister")
def test_shadow_kilit_tutmaz():
    env = dict(os.environ, BP_ROLE="shadow")
    env.pop("REFRESH_WORKER", None)
    r = subprocess.run([sys.executable, "-c", _CODE], cwd=ROOT, env=env,
                       capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stderr[-800:]
    out = dict(ln.split(" ", 1) for ln in r.stdout.splitlines() if ln.startswith(("LEADERS", "FDS")))
    assert out["LEADERS"] == "[False, False, False, False, False]"
    assert out["FDS"] == "[]"


def test_shadow_compare_norm_ve_diff():
    import shadow_compare as sc
    a = {"ts": 1, "stocks_age_s": 5, "x": {"macro_age_seconds": 9, "v": [1, 2.5]}, "updated_at": "a"}
    b = {"ts": 2, "stocks_age_s": 9, "x": {"macro_age_seconds": 1, "v": [1, 2.5]}, "updated_at": "b"}
    assert sc.diff(sc.norm(a), sc.norm(b)) == []
    b["x"]["v"][1] = 2.6
    assert sc.diff(sc.norm(a), sc.norm(b)) == ["$.x.v[1]"]
    assert sc.diff({"a": 1}, {"b": 1})  # anahtar farkı yakalanır
    assert sc.html_view("<p data-a=\"1\">Merhaba <b>dünya</b></p><script>x()</script>") == \
        ("Merhaba dünya", [' data-a="1"'])
