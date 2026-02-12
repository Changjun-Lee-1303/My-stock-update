import os
import csv
from typing import List

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, 'data')


def _ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)


def load_market_list(market: str) -> List[str]:
    """Load market ticker list from data/ directory. If not present, return a small default sample."""
    _ensure_data_dir()
    fname = None
    if market.lower() == 'nasdaq':
        fname = os.path.join(DATA_DIR, 'nasdaq_top100.csv')
    elif market.lower() == 'kospi':
        fname = os.path.join(DATA_DIR, 'kospi_top100.csv')
    else:
        return []

    if os.path.exists(fname):
        tickers = []
        with open(fname, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if not row:
                    continue
                tickers.append(row[0].strip())
        return tickers

    # fallback small sample
    if market.lower() == 'nasdaq':
        return ['NVDA', 'AAPL', 'MSFT', 'AMZN', 'GOOGL', 'META', 'TSLA', 'NVDA']
    if market.lower() == 'kospi':
        # Korean tickers require .KS suffix on yfinance (example)
        return ['005930.KS', '000660.KS', '035420.KS', '207940.KS']
    return []


def save_example_lists():
    _ensure_data_dir()
    nasdaq = ['NVDA','AAPL','MSFT','AMZN','GOOGL','META','TSLA','NFLX','ADBE','INTC']
    kospi = ['005930.KS','000660.KS','035420.KS','207940.KS','051910.KS','035720.KS']
    with open(os.path.join(DATA_DIR, 'nasdaq_top100.csv'), 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        for t in nasdaq:
            writer.writerow([t])
    with open(os.path.join(DATA_DIR, 'kospi_top100.csv'), 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        for t in kospi:
            writer.writerow([t])
