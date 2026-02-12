from typing import List, Dict, Any, Optional
import pandas as pd
from .data_fetcher import get_history


def simple_backtest(tickers: List[str], start_cash: float = 10000000, allocation_per_trade: float = 100000, allocation_map: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """Very small backtest skeleton: enters when price > MA200 and holds until -10% stop or MA200 break.

    If allocation_map is provided, it should be a dict {ticker: allocation_amount} overriding allocation_per_trade.
    """
    trades = []
    cash = float(start_cash)
    portfolio = {}
    # track equity points after each realized sell for approximate MDD calculation
    equity_points = [cash]

    for ticker in tickers:
        hist = get_history(ticker, period='1y')
        if hist is None or hist.empty or 'Close' not in hist.columns:
            continue
        close = hist['Close']
        ma200 = close.rolling(200).mean()
        entry_price = None
        shares = 0

        # Determine allocation for this ticker
        alloc_amount = allocation_per_trade
        if allocation_map and ticker in allocation_map:
            try:
                a = float(allocation_map[ticker])
                if a >= 0:
                    alloc_amount = a
            except Exception:
                pass

        for i in range(len(close)):
            price = close.iloc[i]
            if i < 200:
                continue
            if entry_price is None:
                # entry condition: price > ma200
                if price > ma200.iloc[i]:
                    entry_price = price
                    shares = int(alloc_amount // price)
                    if shares <= 0:
                        entry_price = None
                        continue
                    cash -= shares * price
                    trades.append({'ticker': ticker, 'action': 'buy', 'price': price, 'shares': shares})
            else:
                # check stoploss
                if price <= entry_price * 0.9:
                    # sell
                    cash += shares * price
                    trades.append({'ticker': ticker, 'action': 'sell', 'price': price, 'shares': shares, 'reason': 'stoploss'})
                    equity_points.append(cash)
                    entry_price = None
                    shares = 0
                elif price < ma200.iloc[i]:
                    cash += shares * price
                    trades.append({'ticker': ticker, 'action': 'sell', 'price': price, 'shares': shares, 'reason': 'ma200_break'})
                    equity_points.append(cash)
                    entry_price = None
                    shares = 0
        # if holding at the end, sell at last price
        if entry_price is not None and shares > 0:
            final_price = close.iloc[-1]
            cash += shares * final_price
            trades.append({'ticker': ticker, 'action': 'sell', 'price': final_price, 'shares': shares, 'reason': 'end'})
            equity_points.append(cash)

    # Post-process trades into paired buy/sell results to compute win rate
    paired = []
    last_buys: Dict[str, Dict[str, Any]] = {}
    for tr in trades:
        if tr.get('action') == 'buy':
            last_buys[tr['ticker']] = tr
        elif tr.get('action') == 'sell':
            buy = last_buys.pop(tr['ticker'], None)
            if buy:
                pnl = (tr['price'] - buy['price']) * tr['shares']
                paired.append({'ticker': tr['ticker'], 'buy_price': buy['price'], 'sell_price': tr['price'], 'shares': tr['shares'], 'pnl': pnl, 'reason': tr.get('reason')})

    total_pairs = len(paired)
    wins = sum(1 for p in paired if p['pnl'] > 0)
    win_rate = (wins / total_pairs) if total_pairs > 0 else None
    final_cash = cash
    total_profit = final_cash - float(start_cash)
    return_pct = (total_profit / float(start_cash) * 100.0)

    # approximate MDD using equity points recorded after each realized trade
    mdd = None
    try:
        peak = equity_points[0]
        max_dd = 0.0
        for e in equity_points:
            if e > peak:
                peak = e
            dd = (peak - e) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd
        mdd = max_dd * 100.0
    except Exception:
        mdd = None

    summary = {
        'start_cash': float(start_cash),
        'final_cash': final_cash,
        'total_profit': total_profit,
        'return_pct': return_pct,
        'total_trades': len(trades),
        'trade_pairs': total_pairs,
        'wins': wins,
        'win_rate': win_rate,
        'mdd_pct': mdd,
        'paired_trades': paired,
        'trades': trades,
    }

    return summary

