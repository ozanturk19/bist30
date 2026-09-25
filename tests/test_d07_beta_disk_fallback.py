"""D-07 (25.09) -- beta 234/234 kayıtta None'du: `_compute_beta_vs_xu030` yalnız süreç-içi
`_stock_chart_cache`/`_chart_cache`'e bakıyordu; fundamentals'ı üreten refresh işçisinde
ikisi de boş. Düzeltme: data/charts/chart_<T>.json + chart_XU030.json yedek kaynak, ve
önbellekten dönen kayıt beta'sızsa `_with_beta` yerinde doldurur.

app.py py3.10+ ister (yerel 3.9) -> ilgili fonksiyonlar kaynaktan çıkarılıp izole exec edilir."""
import json
import logging
import os
import re
import threading

import numpy as np

_APP_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


def _src(name):
    with open(_APP_PY, encoding="utf-8") as f:
        src = f.read()
    m = re.search(rf"^def {name}\(.*?(?=^\S)", src, re.S | re.M)
    assert m, name
    return m.group(0)


def _ns(chart_dir):
    ns = {
        "np": np, "os": os, "logger": logging.getLogger("t"),
        "_lock": threading.Lock(),
        "_stock_chart_cache": {}, "_chart_cache": {"data": None},
        "_PHASE3_CHART_DIR": str(chart_dir),
        "_BETA_MIN_OVERLAP_DAYS": 60, "_beta_disk_close": {},
        "_FUND_SANITY": {"beta": (-1.0, 5.0)},
        "_tp_read_json": lambda p, default=None: json.load(open(p)),
    }
    for fn in ("_beta_close_map", "_compute_beta_vs_xu030", "_with_beta"):
        exec(_src(fn), ns)
    return ns


def _write(dirpath, key, closes):
    ohlc = [{"time": "2026-01-%02d" % (i + 1) if i < 28 else "2026-%02d-%02d" % (2 + (i - 28) // 28, (i - 28) % 28 + 1),
             "close": c} for i, c in enumerate(closes)]
    (dirpath / f"chart_{key}.json").write_text(json.dumps({"ohlc": ohlc}))


def test_beta_diskten_hesaplanir_bellek_bos(tmp_path):
    rng = np.random.default_rng(1)
    rm = rng.normal(0, 0.01, 100)
    rs = 1.5 * rm + rng.normal(0, 0.001, 100)
    mkt = 100 * np.cumprod(1 + np.r_[0, rm])
    stk = 50 * np.cumprod(1 + np.r_[0, rs])
    _write(tmp_path, "XU030", mkt)
    _write(tmp_path, "TEST", stk)
    ns = _ns(tmp_path)
    data = {"beta": None, "beta_benchmark": None, "beta_window_days": None}
    out = ns["_with_beta"]("TEST", data)
    assert out["beta"] is not None and abs(out["beta"] - 1.5) < 0.15
    assert out["beta_benchmark"] == "XU030" and out["beta_window_days"] == 100


def test_beta_dosya_yoksa_none_ve_dolu_beta_korunur(tmp_path):
    ns = _ns(tmp_path)
    d = {"beta": None}
    assert ns["_with_beta"]("YOK", d)["beta"] is None
    d2 = {"beta": 0.9}
    assert ns["_with_beta"]("YOK", d2)["beta"] == 0.9


def test_get_fundamentals_with_beta_kilit_disinda():
    src = _src("_get_fundamentals")
    # _with_beta _lock alır (Lock reentrant değil): `with _lock:` bloğunun içinde çağrılmamalı
    lock_block = re.search(r"    with _lock:\n(?:        .*\n|\n)+", src).group(0)
    assert "_with_beta" not in lock_block
