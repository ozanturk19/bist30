"""D-66: /ozet/<gün> → /bulten/<gün> tek 301 (bülten olan gün); eski günler noindex, follow.

Yerel (py3.9): seo_yonlendirme.ozet_hedefi + app.py kaynağı. VPS (py3.10+): uç, geçici klasörlerle.
"""
import json
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import seo_yonlendirme as sy  # noqa: E402

PY310 = pytest.mark.skipif(sys.version_info < (3, 10), reason="app.py 3.10+ ister")


def test_ozet_hedefi():
    gunler = ["2026-09-25", "2026-10-14"]
    assert sy.ozet_hedefi("2026-10-14", gunler) == "/bulten/2026-10-14"
    assert sy.ozet_hedefi("2026-06-19", gunler) is None
    assert sy.ozet_hedefi("2026-10-14", []) is None


def test_app_kaynagi_301_once_noindex_sonra():
    src = open(os.path.join(ROOT, "app.py"), encoding="utf-8").read()
    body = re.search(r'@app\.route\("/ozet/<tarih>"\)\ndef ozet_gecmis(.*?)\n\n\n', src, re.S).group(1)
    i301 = body.index("return redirect(_hedef, code=301)")
    assert i301 < body.index("_SNAPSHOTS_DIR")          # bülten günü snapshot okunmadan yönlenir
    assert 'resp.headers["X-Robots-Tag"] = "noindex, follow"' in body


@PY310
def test_app_ozet_ucu(tmp_path, monkeypatch):
    import app
    bdir, sdir = tmp_path / "bulten", tmp_path / "snapshots"
    bdir.mkdir()
    sdir.mkdir()
    (bdir / "2026-10-14.json").write_text("{}", encoding="utf-8")
    for d in ("2026-10-14", "2026-06-19"):
        (sdir / (d + ".json")).write_text(json.dumps({"stocks": [], "date_tr": d}), encoding="utf-8")
    monkeypatch.setattr(app, "_BULTEN_DIR", str(bdir))
    monkeypatch.setattr(app, "_SNAPSHOTS_DIR", str(sdir))
    monkeypatch.setattr(app, "render_template", lambda name, **ctx: "ok:" + name)
    c = app.app.test_client()
    if not app._bulten_page_ready():
        pytest.skip("bulten.html yok")
    r = c.get("/ozet/2026-10-14")
    assert r.status_code == 301 and r.headers["Location"].endswith("/bulten/2026-10-14")
    r = c.get("/ozet/2026-06-19")
    assert r.status_code == 200 and r.headers["X-Robots-Tag"] == "noindex, follow"
    assert c.get("/ozet/2026-06-20").status_code == 404
    assert c.get("/ozet/2026-6-19").status_code == 404
