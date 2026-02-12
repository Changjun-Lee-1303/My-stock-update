from typing import Dict, Any
from .data_fetcher import get_history, get_quote
from .indicators import ma, rsi, calc_peg, revenue_growth, demark_targets, gap_vs_sector
import pandas as pd


DEFAULTS = {
    'vix_threshold': 30.0,
    'peg_threshold': 1.5,
    'revenue_growth_min': 0.0,
    'rsi_max': 70.0,
    'gap_threshold_pct': 5.0,
    'ma_days': 200,
}


def evaluate_ticker(ticker: str, sector_ma20: float = None, vix: float = None) -> Dict[str, Any]:
    """Returns evaluation dict with grade, reasons, demark targets, and key indicators."""
    hist = get_history(ticker, period='1y')
    quote = get_quote(ticker)
    info = quote.get('info', {})
    close_series = hist['Close'] if not hist.empty else pd.Series()

    indicators = {}
    indicators['last'] = quote.get('last')
    indicators['open'] = quote.get('open')
    indicators['high'] = quote.get('high')
    indicators['low'] = quote.get('low')
    # include sector/sector_ma in indicators if provided
    indicators['sector'] = None
    indicators['sector_ma'] = sector_ma20

    indicators['ma200'] = ma(close_series, window=DEFAULTS['ma_days'])
    indicators['rsi14'] = rsi(close_series, window=14) if len(close_series) > 14 else None
    indicators['peg'] = calc_peg(info)
    indicators['rev_growth'] = revenue_growth(hist, info)

    if indicators['last'] and sector_ma20:
        indicators['gap_pct'] = gap_vs_sector(indicators['last'], sector_ma20)
    else:
        indicators['gap_pct'] = None

    # DeMark using previous day's OHLC
    demark = {}
    if len(hist) >= 2:
        prev = hist.iloc[-2]
        demark = demark_targets(prev['High'], prev['Low'], prev['Close'])
    else:
        demark = demark_targets(indicators.get('high'), indicators.get('low'), indicators.get('last'))

    # Filters
    reasons = []
    grade = 'F'

    # VIX filter
    if vix is not None and vix >= DEFAULTS['vix_threshold']:
        reasons.append(f'VIX {vix:.1f} >= {DEFAULTS["vix_threshold"]} -> trading halted')
        return {'ticker': ticker, 'grade': 'F', 'reasons': reasons, 'indicators': indicators, 'demark': demark}

    # Trend filter MA200
    if indicators['ma200'] is None or indicators['last'] is None:
        reasons.append('Insufficient price history for MA200')
    else:
        if indicators['last'] < indicators['ma200']:
            reasons.append('Price below MA200 -> 추세미달')

    # PEG
    if indicators['peg'] is None:
        reasons.append('PEG 정보 없음')
    else:
        if indicators['peg'] >= DEFAULTS['peg_threshold']:
            reasons.append(f'PEG {indicators["peg"]:.2f} >= {DEFAULTS["peg_threshold"]} -> 고평가')

    # Revenue growth
    if indicators['rev_growth'] is None:
        reasons.append('매출성장률 정보 없음')
    else:
        try:
            if float(indicators['rev_growth']) <= DEFAULTS['revenue_growth_min']:
                reasons.append(f'매출성장률 {indicators["rev_growth"]} <= {DEFAULTS["revenue_growth_min"]} -> 성장성 부족')
        except Exception:
            reasons.append('매출성장률 파싱 실패')

    # RSI
    if indicators['rsi14'] is not None:
        if indicators['rsi14'] >= DEFAULTS['rsi_max']:
            reasons.append(f'RSI {indicators["rsi14"]:.1f} >= {DEFAULTS["rsi_max"]} -> 과열')

    # Gap
    if indicators['gap_pct'] is not None:
        if indicators['gap_pct'] < DEFAULTS['gap_threshold_pct']:
            reasons.append(f'괴리율 {indicators["gap_pct"]:.2f}% < {DEFAULTS["gap_threshold_pct"]}% -> 소외 아님')

    # Decide grade: if any critical reason -> F, else S if strong, else A
    critical_fail = any(x for x in reasons if '추세미달' in x or '고평가' in x or '매출성장률' in x)
    if critical_fail:
        grade = 'F'
    else:
        # S-grade conditions: above MA200, peg<1.5, rev_growth>0, gap>=threshold, rsi<70
        conds = [indicators.get('last') is not None and indicators.get('ma200') is not None and indicators['last'] > indicators['ma200'],
                 indicators.get('peg') is not None and indicators['peg'] < DEFAULTS['peg_threshold'],
                 indicators.get('rev_growth') is not None and float(indicators['rev_growth']) > DEFAULTS['revenue_growth_min'],
                 indicators.get('gap_pct') is not None and indicators['gap_pct'] >= DEFAULTS['gap_threshold_pct'],
                 indicators.get('rsi14') is not None and indicators['rsi14'] < DEFAULTS['rsi_max']]
        if all(conds):
            grade = 'S'
        else:
            # A if majority of positive conditions
            pos = sum(1 for c in conds if c)
            grade = 'A' if pos >= 3 else 'F'

    return {'ticker': ticker, 'grade': grade, 'reasons': reasons, 'indicators': indicators, 'demark': demark}
