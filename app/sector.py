from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from .data_fetcher import get_history, get_ticker, get_histories


def compute_sector_stats(tickers: List[str], period: str = '3mo', interval: str = '1d', ma_window: int = 20) -> Dict:
    """Compute per-ticker moving average (ma_window) and group tickers by sector (using yfinance info).

    Parameters:
      - tickers: list of ticker symbols
      - period: history period passed to yfinance (e.g., '1mo', '3mo')
      - interval: data interval (e.g., '1d')
      - ma_window: moving average window (e.g., 20 for MA20)

    Returns a dict with keys:
      - 'ticker_ma': {ticker: ma or None}
      - 'ticker_sector': {ticker: sector_name or 'Unclassified'}
      - 'sector_mean_ma': {sector_name: mean_ma or None}
      - 'sector_overall_mean': overall mean MA across all tickers with MA
    """
    ticker_ma: Dict[str, Optional[float]] = {}
    ticker_sector: Dict[str, str] = {}
    sector_groups: Dict[str, List[float]] = {}

    # fetch histories in batch for efficiency
    histories = get_histories(tickers, period=period, interval=interval)

    for t in tickers:
        sector = 'Unclassified'
        try:
            tk = get_ticker(t)
            info = getattr(tk, 'info', None) or {}
            sec = info.get('sector') or info.get('industry')
            if sec:
                sector = sec
        except Exception:
            sector = 'Unclassified'

        ticker_sector[t] = sector

        try:
            hist = histories.get(t) or histories.get(t.upper()) or histories.get(t.lower()) or pd.DataFrame()
            if hist is None or hist.empty or 'Close' not in hist.columns:
                ticker_ma[t] = None
                continue
            close = hist['Close']
            if len(close) < ma_window:
                ma_val = float(close.mean()) if len(close) > 0 else None
            else:
                ma_val = float(close.rolling(ma_window).mean().iloc[-1])
            ticker_ma[t] = ma_val
            if ma_val is not None:
                sector_groups.setdefault(sector, []).append(ma_val)
        except Exception:
            ticker_ma[t] = None

    sector_mean_ma: Dict[str, Optional[float]] = {}
    all_vals = []
    for sec, vals in sector_groups.items():
        if vals:
            m = float(np.nanmean(vals))
            sector_mean_ma[sec] = m
            all_vals.extend(vals)
        else:
            sector_mean_ma[sec] = None

    sector_overall_mean = float(np.nanmean(all_vals)) if all_vals else None

    return {
        'ticker_ma': ticker_ma,
        'ticker_sector': ticker_sector,
        'sector_mean_ma': sector_mean_ma,
        'sector_overall_mean': sector_overall_mean,
    }
