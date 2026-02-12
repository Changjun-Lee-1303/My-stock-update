import logging
import json
import os
import pandas as pd
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)

# ensure logs dir
_LOG_DIR = os.path.join(os.getcwd(), 'logs')
os.makedirs(_LOG_DIR, exist_ok=True)
_PEG_LOG = os.path.join(_LOG_DIR, 'peg_revenue.log')

# setup rotating JSONL logger for PEG/revenue decisions
_PEG_LOGGER = logging.getLogger('peg_logger')
if not _PEG_LOGGER.handlers:
    from logging.handlers import RotatingFileHandler
    rh = RotatingFileHandler(_PEG_LOG, maxBytes=2_000_000, backupCount=5, encoding='utf-8')
    rh.setLevel(logging.INFO)
    # handler will receive a JSON string as the message
    formatter = logging.Formatter('%(message)s')
    rh.setFormatter(formatter)
    _PEG_LOGGER.addHandler(rh)
    _PEG_LOGGER.setLevel(logging.INFO)


def _append_decision_log(kind: str, info: dict, used_field: str, value, note: str = ''):
    try:
        symbol = None
        if isinstance(info, dict):
            symbol = info.get('symbol') or info.get('ticker') or info.get('shortName')
        rec = {
            'ts': time_fmt(),
            'kind': kind,
            'symbol': symbol,
            'used_field': used_field,
            'value': value,
            'note': note,
        }
        # write as a single JSON line via the rotating logger
        _PEG_LOGGER.info(json.dumps(rec, ensure_ascii=False))
    except Exception:
        # best-effort logging - avoid crashing indicators
        logger.debug('failed to append decision log')


def time_fmt():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def ma(series: pd.Series, window: int = 200) -> Optional[float]:
    if series is None or len(series) < window:
        return None
    return float(series.rolling(window).mean().iloc[-1])


def rsi(series: pd.Series, window: int = 14) -> Optional[float]:
    if series is None or len(series) < window:
        return None
    # Compute RSI using Wilder's EMA method to avoid external deps
    delta = series.diff().dropna()
    if delta.empty:
        return None
    up = delta.clip(lower=0.0)
    down = -delta.clip(upper=0.0)
    # Wilder's smoothing (EMA with alpha=1/window)
    roll_up = up.ewm(alpha=1.0/window, adjust=False).mean()
    roll_down = down.ewm(alpha=1.0/window, adjust=False).mean()
    # Avoid division by zero
    rs = roll_up / roll_down.replace(0, np.nan)
    rsi_series = 100.0 - (100.0 / (1.0 + rs))
    val = rsi_series.iloc[-1]
    if pd.isna(val):
        return None
    return float(val)


def calc_peg(info: dict) -> Optional[float]:
    # Robust PEG extraction/estimation.
    # Priority: info['pegRatio'] if valid positive number.
    if not info or not isinstance(info, dict):
        return None

    peg = info.get('pegRatio')
    try:
        if peg is not None:
            peg = float(peg)
            # treat non-finite or NaN as None
            if peg != peg or peg == float('inf') or peg == float('-inf'):
                peg = None
            else:
                logger.debug("calc_peg: using pegRatio=%s", peg)
                _append_decision_log('peg', info, 'pegRatio', peg, 'used pegRatio directly')
                return peg
    except Exception:
        peg = None

    # fallback: try forwardPE / earnings growth estimate or revenue growth
    # attempt to estimate using PE and a variety of growth fields
    try:
        pe = None
        for pe_field in ('forwardPE', 'forwardPE1', 'trailingPE', 'peRatio'):
            if pe_field in info and info.get(pe_field) is not None:
                try:
                    pe = float(info.get(pe_field))
                    break
                except Exception:
                    continue

        # growth candidates: try multiple fields and parse string percentages if present
        growth_candidates_raw = [
            info.get('earningsQuarterlyGrowth'),
            info.get('earningsGrowth'),
            info.get('revenueGrowth'),
            info.get('earningsEstimateGrowth'),
            info.get('earningsGrowthYoY'),
            info.get('revenueGrowthYoY'),
        ]
        growth = None
        for g in growth_candidates_raw:
            if g is None:
                continue
            try:
                gv = _parse_numeric_maybe_percent(g)
                # gv now is decimal or percent? _parse returns decimal (0.12) when percent-like or plain decimal
                # convert to percent scale (0-100) for PEG formula
                if abs(gv) <= 1.0:
                    gv_pct = gv * 100.0
                else:
                    gv_pct = gv
                growth = gv_pct
                _append_decision_log('peg', info, 'growth_candidate', gv, f'used field value {g}')
                break
            except Exception:
                continue

        if pe is not None and growth is not None and growth > 0:
            pe_val = float(pe)
            if pe_val > 0:
                peg_est = pe_val / growth
                logger.debug("calc_peg: estimated peg using pe=%s growth=%s => %s", pe_val, growth, peg_est)
                _append_decision_log('peg', info, 'estimated', {'pe': pe_val, 'growth_pct': growth, 'peg_est': peg_est}, 'estimated from PE and growth')
                return float(peg_est)
    except Exception:
        pass

    return None


def revenue_growth(ticker_history: pd.DataFrame, info: dict) -> Optional[float]:
    # Best-effort: return revenue growth as a decimal (e.g., 0.12 means +12%).
    if info and isinstance(info, dict):
        # Prefer explicit revenueGrowth if present; try many candidate fields and robust parsing
        for key in ('revenueGrowth', 'revenueGrowthYoY', 'earningsQuarterlyGrowth', 'earningsGrowth', 'earningsEstimateGrowth'):
            if key in info and info.get(key) is not None:
                try:
                    val = _parse_numeric_maybe_percent(info.get(key))
                    # _parse returns decimal (e.g., 0.12 for 12%) or raw decimal
                    # ensure we return decimal representation
                    if abs(val) > 1.0 and abs(val) <= 1000.0:
                        # if still >1, interpret as percent and convert
                        _append_decision_log('revenue', info, key, val, 'interpreted as percent-like; converting')
                        return val / 100.0
                    _append_decision_log('revenue', info, key, val, 'interpreted as decimal')
                    return val
                except Exception:
                    continue

    # Fallback: attempt to estimate from historical revenue if ticker_history contains 'Revenue' (rare)
    # No good revenue field found
    return None


def _parse_numeric_maybe_percent(x) -> float:
    """Parse a value that may be numeric, a percent string like '12%' or '0.12', or with commas.

    Returns a float where percents like '12%' -> 0.12, strings '0.12' -> 0.12, and plain 12 -> 12.0.
    Caller must interpret scale: for growth fields we commonly expect decimals (0.12) or percentages (12).
    This helper returns numeric value preserving scale, but if input is percent string it returns decimal (0.12).
    """
    if x is None:
        raise ValueError('None')
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip()
    if s.endswith('%'):
        try:
            num = float(s[:-1].replace(',', '').strip())
            return num / 100.0
        except Exception:
            raise
    # remove commas
    s2 = s.replace(',', '')
    try:
        return float(s2)
    except Exception:
        # maybe it's like '+12.3%' or contains other chars
        import re
        m = re.search(r"([-+]?[0-9]*\.?[0-9]+)", s2)
        if m:
            return float(m.group(1))
        raise


def gap_vs_sector(current_price: float, sector_mean_ma20: float) -> Optional[float]:
    if current_price is None or sector_mean_ma20 is None or sector_mean_ma20 == 0:
        return None
    return (current_price / sector_mean_ma20 - 1.0) * 100.0


def demark_targets(prev_high: float, prev_low: float, prev_close: float) -> dict:
    # Using X = High + Low + Close as a simple approach
    X = (prev_high or 0) + (prev_low or 0) + (prev_close or 0)
    pivot = X / 4.0
    support = X / 2.0 - (prev_high or 0)
    resistance = X / 2.0 - (prev_low or 0)
    return {
        'pivot': pivot,
        'support': support,
        'resistance': resistance,
    }
