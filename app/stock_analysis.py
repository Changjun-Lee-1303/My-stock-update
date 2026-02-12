import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List


def analyze_stock_logic(ticker: str, benchmark_ticker: str = "^KS11") -> Dict[str, Any]:
    """Run technical + simple fundamental checks for a ticker (yfinance) and return a summary dict.

    This function prints the human-friendly report (same style as original) and also
    returns a dictionary with key metrics so callers can aggregate results programmatically.
    """
    print(f"\n{'='*60}")
    print(f"🚀 [AI ANALYSIS START] Ticker: {ticker}")
    print(f"{'='*60}")

    # Prepare default summary
    summary: Dict[str, Any] = {
        'ticker': ticker,
        'rating': None,
        'is_s_class': False,
        'reasons': [],
        'current_price': None,
        'ma200': None,
        'rsi': None,
        'peg': None,
        'rev_growth': None,
        'marketCap': None,
    }

    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        bench = yf.Ticker(benchmark_ticker)
        bench_hist = bench.history(period="1y")
        vix = yf.Ticker("^VIX")
        vix_hist = vix.history(period="5d")
        current_vix = None
        if not vix_hist.empty:
            current_vix = float(vix_hist['Close'].iloc[-1])
        info = stock.info or {}
    except Exception as e:
        print(f"❌ Error fetching data for {ticker}: {e}")
        summary['reasons'].append(f"data_error: {e}")
        summary['rating'] = 'ERROR'
        return summary

    if len(hist) < 30:
        print("❌ Not enough history data (need >= 30 days). Skipping.")
        summary['reasons'].append('insufficient_history')
        summary['rating'] = 'SKIPPED'
        return summary

    current_price = float(hist['Close'].iloc[-1])
    summary['current_price'] = current_price

    ma200 = float(hist['Close'].rolling(window=200).mean().iloc[-1]) if len(hist) >= 200 else float(hist['Close'].rolling(window=len(hist)).mean().iloc[-1])
    summary['ma200'] = ma200

    delta = hist['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = float((100 - (100 / (1 + rs))).iloc[-1])
    summary['rsi'] = rsi

    stock_ret_20 = hist['Close'].pct_change(20).iloc[-1] if len(hist) > 20 else 0.0
    bench_ret_20 = bench_hist['Close'].pct_change(20).iloc[-1] if not bench_hist.empty and len(bench_hist) > 20 else 0.0
    gap = float(bench_ret_20 - stock_ret_20)

    peg = info.get('pegRatio', None)
    rev_growth = info.get('revenueGrowth', None)
    summary['peg'] = peg
    summary['rev_growth'] = rev_growth
    summary['marketCap'] = info.get('marketCap', None)

    # Logical filters
    is_s_class = True
    reasons: List[str] = []

    # VIX shield (optional)
    if current_vix is not None:
        print(f"1️⃣ [SHIELD] VIX: {current_vix:.2f} (threshold <30)")
        if current_vix >= 30:
            is_s_class = False
            reasons.append('vix_high')
    else:
        print("1️⃣ [SHIELD] VIX: not available")

    # Trend: MA200
    print(f"2️⃣ [TREND] price={current_price:.2f}, ma200={ma200:.2f}")
    if current_price < ma200:
        is_s_class = False
        reasons.append('below_ma200')

    # Value: PEG & growth
    if peg is None:
        peg_for_logic = 99
    else:
        peg_for_logic = peg

    if peg_for_logic > 1.5 and (rev_growth is None or rev_growth < 0.30):
        is_s_class = False
        reasons.append('high_peg')

    # Timing: RSI & gap
    print(f"3️⃣ [TIMING] RSI={rsi:.1f}, gap={gap*100:.1f}%")
    if rsi >= 70:
        is_s_class = False
        reasons.append('rsi_overbought')

    # DeMark pivot (yesterday)
    if len(hist) >= 2:
        yesterday = hist.iloc[-2]
        y_open = yesterday['Open']
        y_high = yesterday['High']
        y_low = yesterday['Low']
        y_close = yesterday['Close']
        if y_close > y_open:
            pivot = (y_high * 2 + y_low + y_close) / 4
        elif y_close < y_open:
            pivot = (y_high + y_low * 2 + y_close) / 4
        else:
            pivot = (y_high + y_low + y_close * 2) / 4
        target_high = pivot * 2 - y_low
        target_low = pivot * 2 - y_high
    else:
        target_high = None
        target_low = None

    # Final rating
    if is_s_class:
        rating = 'S-CLASS'
    elif current_price > ma200:
        rating = 'A-CLASS'
    else:
        rating = 'F-CLASS'

    # Print concise report
    print(f"\n📋 [REPORT] {ticker} -> {rating}")
    if reasons:
        print(f"   Reasons: {', '.join(reasons)}")
    if target_low is not None:
        print(f"   Target Buy: {target_low:.2f}, Target Sell: {target_high:.2f}")

    summary.update({
        'rating': rating,
        'is_s_class': is_s_class,
        'reasons': reasons,
        'target_low': float(target_low) if target_low is not None else None,
        'target_high': float(target_high) if target_high is not None else None,
    })

    return summary


if __name__ == '__main__':
    # Quick local test
    print(analyze_stock_logic('005930.KS', benchmark_ticker='^KS11'))
