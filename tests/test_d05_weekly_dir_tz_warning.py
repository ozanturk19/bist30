"""D-05: tz'li kapanış serisi haftalık yön hesabında UserWarning basmaz, sonuç aynı."""
import os
import sys
import warnings

import pytest

if sys.version_info < (3, 10):
    pytest.skip("app.py 3.10+ ister — VPS venv'de çalıştır", allow_module_level=True)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from app import _historical_weekly_dir_series


def _close(tz):
    idx = pd.date_range("2025-01-01", "2026-09-24", freq="B", tz=tz)
    rng = np.random.default_rng(7)
    return pd.Series(100 + np.cumsum(rng.normal(0, 1, len(idx))), index=idx)


def test_tzli_seri_uyari_basmaz():
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        _historical_weekly_dir_series(_close("Europe/Istanbul"))


def test_tzli_ve_tzsiz_ayni_yon():
    a = _historical_weekly_dir_series(_close("Europe/Istanbul"))
    b = _historical_weekly_dir_series(_close(None))
    assert list(a.values) == list(b.values)
    assert (a != 0).any()
