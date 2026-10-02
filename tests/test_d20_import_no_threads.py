"""D-20: BP_ROLE=batch|shadow ile `import app` hiçbir daemon thread başlatmaz."""
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_CODE = (
    "import threading, app; "
    "print('THREADS', threading.active_count(), "
    "sorted(t.name for t in threading.enumerate()))"
)


@pytest.mark.skipif(sys.version_info < (3, 10), reason="app.py Python 3.10+ ister")
@pytest.mark.parametrize("role", ["batch", "shadow"])
def test_import_thread_baslatmaz(role):
    env = dict(os.environ, BP_ROLE=role)
    env.pop("REFRESH_WORKER", None)
    r = subprocess.run([sys.executable, "-c", _CODE], cwd=ROOT, env=env,
                       capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stderr[-800:]
    line = [ln for ln in r.stdout.splitlines() if ln.startswith("THREADS")][-1]
    assert line.startswith("THREADS 1 "), line


def test_modul_duzeyi_thread_start_kalmadi():
    """Modül düzeyinde çıplak `threading.Thread(...).start()` kalmamalı (`_bg_start` ile sarılı)."""
    import ast
    src = open(os.path.join(ROOT, "app.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    bulunan = []

    def gez(node, fonk):
        for c in ast.iter_child_nodes(node):
            f = fonk or isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef))
            if (not f and isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                    and c.func.attr == "start"):
                bulunan.append(c.lineno)
            gez(c, f)

    gez(tree, False)
    assert bulunan == [], "modül düzeyi .start(): satır %s" % bulunan
