#!/usr/bin/env python3
"""Simulate a GenAI recommendation response and run the backtester using the suggested allocations.

This script demonstrates the full pipeline without calling any external AI service.
It produces CSVs and a JSON summary under the project's data/ directory.
"""
import os
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / 'data'
DATA_DIR.mkdir(parents=True, exist_ok=True)

import sys
sys.path.insert(0, str(PROJECT_ROOT))
from app.backtester import simple_backtest


def simulated_genai_response(tickers, start_cash):
    """Return a simulated parsed response similar to analyze_with_gemini output.
    Each item may contain 'ticker' and either 'recommended_percent' or 'recommended_amount'.
    """
    # Simple allocation plan: favour large US tech weights
    percent_map = {
        'NVDA': 20,
        'META': 10,
        'GOOGL': 15,
        'AAPL': 15,
        'MSFT': 15,
        'TSLA': 5,
    }
    resp = {'analysis_result': []}
    for t in tickers:
        pct = percent_map.get(t.upper(), 0)
        resp['analysis_result'].append({'ticker': t.upper(), 'recommended_percent': pct})
    return resp


def build_allocation_map(parsed, start_cash):
    alloc = {}
    for item in parsed.get('analysis_result', []):
        t = item.get('ticker')
        if not t:
            continue
        if 'recommended_amount' in item:
            try:
                amt = float(item['recommended_amount'])
            except Exception:
                amt = 0.0
        elif 'recommended_percent' in item:
            try:
                pct = float(item['recommended_percent'])
                amt = (pct / 100.0) * float(start_cash)
            except Exception:
                amt = 0.0
        else:
            amt = 0.0
        alloc[t.upper()] = max(0.0, amt)
    return alloc


def save_json(obj, path: Path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def main():
    tickers = ['NVDA','META','GOOGL','AAPL','MSFT','TSLA']
    start_cash = 10_000_000

    parsed = simulated_genai_response(tickers, start_cash)
    allocation_map = build_allocation_map(parsed, start_cash)

    print('Simulated allocations:')
    for k,v in allocation_map.items():
        print(f'  {k}: {v:,.0f} KRW')

    summary = simple_backtest(tickers, start_cash=start_cash, allocation_map=allocation_map)

    # Save outputs
    save_json(parsed, DATA_DIR / 'sim_genai_parsed.json')
    save_json(summary, DATA_DIR / 'sim_genai_backtest_summary.json')

    # trades and paired_trades to CSV
    import csv
    trades_path = DATA_DIR / 'sim_genai_trades.csv'
    paired_path = DATA_DIR / 'sim_genai_paired_trades.csv'

    with open(trades_path, 'w', newline='', encoding='utf-8') as f:
        if summary.get('trades'):
            keys = sorted({k for t in summary['trades'] for k in t.keys()})
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for row in summary['trades']:
                writer.writerow(row)

    with open(paired_path, 'w', newline='', encoding='utf-8') as f:
        if summary.get('paired_trades'):
            keys = sorted({k for t in summary['paired_trades'] for k in t.keys()})
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for row in summary['paired_trades']:
                writer.writerow(row)

    print('\nBacktest summary:')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print('\nSaved files:')
    print(' -', DATA_DIR / 'sim_genai_parsed.json')
    print(' -', DATA_DIR / 'sim_genai_backtest_summary.json')
    print(' -', trades_path)
    print(' -', paired_path)


if __name__ == '__main__':
    main()
