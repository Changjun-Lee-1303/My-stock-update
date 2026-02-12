import pytest
from app.indicators import demark_targets, calc_peg, revenue_growth, rsi, gap_vs_sector
import pandas as pd


def test_demark_simple():
    d = demark_targets(10, 5, 8)
    assert 'support' in d and 'resistance' in d


def test_calc_peg_from_info():
    info = {'pegRatio': 1.2}
    assert calc_peg(info) == 1.2


def test_calc_peg_estimate():
    info = {'forwardPE': 30, 'earningsQuarterlyGrowth': 0.2}
    p = calc_peg(info)
    assert p is not None


def test_rsi_on_constant_series():
    s = pd.Series([1.0] * 30)
    val = rsi(s, window=14)
    assert val is None or (0.0 <= val <= 100.0)


def test_gap_vs_sector():
    g = gap_vs_sector(110, 100)
    assert abs(g - 10.0) < 0.0001
