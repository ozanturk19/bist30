"""Smoke + regression tests for indicators.py"""
import numpy as np
import pandas as pd
import pytest
from indicators import (
    compute_ema, compute_adx, compute_rsi,
    compute_atr, compute_supertrend,
)

# Minimal synthetic OHLC (50 bars, yeterli warmup)
N = 50
np.random.seed(42)
_close = pd.Series(100 + np.cumsum(np.random.randn(N) * 0.5))
_high  = _close + np.abs(np.random.randn(N) * 0.3)
_low   = _close - np.abs(np.random.randn(N) * 0.3)


class TestComputeEma:
    def test_length(self):
        result = compute_ema(_close, 12)
        assert len(result) == N

    def test_type(self):
        assert isinstance(compute_ema(_close, 12), pd.Series)

    def test_ema12_gt_ema99_in_uptrend(self):
        """Yükselen seri: EMA12 > EMA99 (daha hızlı yakınsama)."""
        up = pd.Series(range(N), dtype=float)
        ema12 = compute_ema(up, 12).iloc[-1]
        ema99 = compute_ema(up, 99).iloc[-1]
        assert ema12 > ema99


class TestComputeAdx:
    def test_returns_three_series(self):
        adx, dip, dim = compute_adx(_high, _low, _close)
        assert all(isinstance(s, pd.Series) for s in [adx, dip, dim])

    def test_adx_nonnegative(self):
        adx, _, _ = compute_adx(_high, _low, _close)
        assert (adx.dropna() >= 0).all()

    def test_length(self):
        adx, dip, dim = compute_adx(_high, _low, _close)
        assert len(adx) == N


class TestComputeRsi:
    def test_range(self):
        rsi = compute_rsi(_close, 14)
        assert (rsi.dropna() >= 0).all() and (rsi.dropna() <= 100).all()

    def test_fillna_default(self):
        """fillna(50) — NaN olmamalı."""
        rsi = compute_rsi(_close, 14)
        assert not rsi.isna().any()

    def test_length(self):
        assert len(compute_rsi(_close, 14)) == N


class TestComputeAtr:
    def test_type(self):
        assert isinstance(compute_atr(_high, _low, _close), pd.Series)

    def test_nonnegative(self):
        atr = compute_atr(_high, _low, _close)
        assert (atr.dropna() >= 0).all()

    def test_warmup_nan(self):
        """İlk period-1 bar NaN olmalı."""
        atr = compute_atr(_high, _low, _close, period=14)
        assert np.isnan(atr.iloc[0])


class TestComputeSupertrend:
    def test_returns_two_series(self):
        direction, st_line = compute_supertrend(_high, _low, _close)
        assert isinstance(direction, pd.Series)
        assert isinstance(st_line, pd.Series)

    def test_direction_values(self):
        direction, _ = compute_supertrend(_high, _low, _close)
        unique = set(direction.dropna().unique())
        assert unique.issubset({1, -1})

    def test_length(self):
        direction, st_line = compute_supertrend(_high, _low, _close)
        assert len(direction) == len(st_line) == N
