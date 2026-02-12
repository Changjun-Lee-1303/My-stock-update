import os
import time
import yfinance as yf
import pandas as pd
from typing import Optional
import sqlite3
import logging
from logging.handlers import RotatingFileHandler
import queue
import pickle
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import math

# simple in-memory cache for histories: { (ticker, period, interval): (timestamp, df) }
_HISTORY_CACHE = {}
_CACHE_TTL = int(os.getenv('YF_CACHE_TTL', '60'))  # seconds (env override)
_USE_SQLITE_CACHE = os.getenv('YF_USE_SQLITE_CACHE', '0') == '1'
_SQLITE_CACHE_PATH = os.path.join(os.getcwd(), '.cache', 'yf_cache.sqlite')
os.makedirs(os.path.dirname(_SQLITE_CACHE_PATH), exist_ok=True)

# logging for data_fetcher
_LOG_DIR = os.path.join(os.getcwd(), 'logs')
os.makedirs(_LOG_DIR, exist_ok=True)
_DF_LOG_PATH = os.path.join(_LOG_DIR, 'data_fetcher.log')
_logger = logging.getLogger('data_fetcher')
if not _logger.handlers:
    rh = RotatingFileHandler(_DF_LOG_PATH, maxBytes=2 * 1024 * 1024, backupCount=3, encoding='utf-8')
    fmt = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    rh.setFormatter(fmt)
    _logger.addHandler(rh)
    _logger.setLevel(logging.INFO)

# simple sqlite connection pool
_SQLITE_POOL_SIZE = int(os.getenv('YF_SQLITE_POOL_SIZE', '4'))
_conn_pool = queue.Queue(maxsize=_SQLITE_POOL_SIZE)
_pool_lock = threading.Lock()

# metrics
_metrics = {
    'cache_hits': 0,
    'cache_misses': 0,
    'chunk_successes': 0,
    'chunk_failures': 0,
    'per_chunk_retries': 0,
}


def get_cache_stats():
    return dict(_metrics)


def _get_conn():
    """Get a sqlite connection from pool or create a new one."""
    try:
        conn = _conn_pool.get_nowait()
        return conn
    except Exception:
        # create new connection
        conn = sqlite3.connect(_SQLITE_CACHE_PATH, timeout=_SQLITE_BUSY_TIMEOUT_MS/1000.0, check_same_thread=False)
        try:
            c = conn.cursor()
            c.execute(f'PRAGMA busy_timeout = {_SQLITE_BUSY_TIMEOUT_MS}')
        except Exception:
            pass
        return conn


def _release_conn(conn):
    try:
        # try to return to pool
        if conn is None:
            return
        with _pool_lock:
            if not _conn_pool.full():
                _conn_pool.put_nowait(conn)
                return
        # else close
        try:
            conn.close()
        except Exception:
            pass
    except Exception:
        pass

# sqlite concurrency tuning
_SQLITE_BUSY_TIMEOUT_MS = int(os.getenv('YF_SQLITE_BUSY_TIMEOUT_MS', '5000'))
_SQLITE_MAX_RETRIES = int(os.getenv('YF_SQLITE_MAX_RETRIES', '5'))
_SQLITE_RETRY_DELAY = float(os.getenv('YF_SQLITE_RETRY_DELAY', '0.08'))
_YF_MAX_WORKERS = int(os.getenv('YF_MAX_WORKERS', '6'))
_YF_BATCH_SIZE = int(os.getenv('YF_BATCH_SIZE', '20'))

# rate limiter settings
_RATE_LIMIT_PER_SEC = float(os.getenv('YF_RATE_LIMIT_PER_SEC', '5'))
_tokens = _RATE_LIMIT_PER_SEC
_last_refill = time.time()
_token_lock = threading.Lock()


def _acquire_token():
    """Simple token bucket: block until a token is available."""
    global _tokens, _last_refill
    with _token_lock:
        now = time.time()
        elapsed = now - _last_refill
        # refill
        refill = elapsed * _RATE_LIMIT_PER_SEC
        if refill > 0:
            _tokens = min(_RATE_LIMIT_PER_SEC, _tokens + refill)
            _last_refill = now
        if _tokens >= 1:
            _tokens -= 1
            return
    # if no token, sleep small increments until available
    while True:
        time.sleep(0.2)
        with _token_lock:
            now = time.time()
            elapsed = now - _last_refill
            refill = elapsed * _RATE_LIMIT_PER_SEC
            if refill > 0:
                _tokens = min(_RATE_LIMIT_PER_SEC, _tokens + refill)
                _last_refill = now
            if _tokens >= 1:
                _tokens -= 1
                return


def _init_sqlite_cache():
    try:
        os.makedirs(os.path.dirname(_SQLITE_CACHE_PATH), exist_ok=True)
        conn = sqlite3.connect(_SQLITE_CACHE_PATH, timeout=_SQLITE_BUSY_TIMEOUT_MS/1000.0, check_same_thread=False)
        c = conn.cursor()
        # enable WAL for better concurrent readers/writers
        try:
            c.execute('PRAGMA journal_mode=WAL')
        except Exception:
            pass
        try:
            c.execute(f'PRAGMA busy_timeout = {_SQLITE_BUSY_TIMEOUT_MS}')
        except Exception:
            pass
        c.execute('''CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, ts REAL, blob BLOB)''')
        conn.commit()
        conn.close()
    except Exception:
        pass


def _get_sqlite_cache(key_str: str):
    # retry loop for transient busy/lock errors
    last_exc = None
    for attempt in range(max(1, _SQLITE_MAX_RETRIES)):
        try:
            conn = _get_conn()
            c = conn.cursor()
            c.execute('SELECT ts, blob FROM cache WHERE key = ?', (key_str,))
            row = c.fetchone()
            _release_conn(conn)
            if row is None:
                _metrics['cache_misses'] += 1
                return None
            ts, blob = row
            try:
                df = pickle.loads(blob)
            except Exception:
                df = pickle.loads(bytes(blob)) if blob is not None else pd.DataFrame()
            _metrics['cache_hits'] += 1
            return (ts, df)
        except sqlite3.OperationalError as e:
            last_exc = e
            # brief backoff
            time.sleep(_SQLITE_RETRY_DELAY * (1 + attempt))
            continue
        except Exception as e:
            last_exc = e
            break
    return None

def _set_sqlite_cache(key_str: str, ts: float, df):
    blob = pickle.dumps(df)
    last_exc = None
    for attempt in range(max(1, _SQLITE_MAX_RETRIES)):
        try:
            conn = _get_conn()
            c = conn.cursor()
            c.execute('REPLACE INTO cache (key, ts, blob) VALUES (?, ?, ?)', (key_str, ts, sqlite3.Binary(blob)))
            conn.commit()
            _release_conn(conn)
            return
        except sqlite3.OperationalError as e:
            _metrics['per_chunk_retries'] += 1
            last_exc = e
            time.sleep(_SQLITE_RETRY_DELAY * (1 + attempt))
            continue
        except Exception as e:
            last_exc = e
            break
    # swallow exceptions but preserve last exception in logs if needed
    return


def _clean_sqlite_cache():
    if not _USE_SQLITE_CACHE:
        return
    now = time.time()
    cutoff = now - _CACHE_TTL
    for attempt in range(max(1, _SQLITE_MAX_RETRIES)):
        try:
            conn = _get_conn()
            c = conn.cursor()
            c.execute('DELETE FROM cache WHERE ts < ?', (cutoff,))
            conn.commit()
            _release_conn(conn)
            return
        except sqlite3.OperationalError:
            time.sleep(_SQLITE_RETRY_DELAY * (1 + attempt))
            continue
        except Exception:
            break
    return


# run a quick cleanup at import time when sqlite cache enabled
if _USE_SQLITE_CACHE:
    try:
        _init_sqlite_cache()
        _clean_sqlite_cache()
    except Exception:
        pass


def get_ticker(ticker: str):
    return yf.Ticker(ticker)


def get_history(ticker: str, period: str = '1y', interval: str = '1d') -> pd.DataFrame:
    key = (ticker, period, interval)
    now = time.time()
    if key in _HISTORY_CACHE:
        ts, df = _HISTORY_CACHE[key]
        if now - ts < _CACHE_TTL:
            return df.copy()
    # try sqlite cache
    key_str = f"{ticker}|{period}|{interval}"
    if _USE_SQLITE_CACHE:
        try:
            r = _get_sqlite_cache(key_str)
            if r is not None:
                ts, df = r
                if now - ts < _CACHE_TTL:
                    _HISTORY_CACHE[key] = (ts, df)
                    return df.copy()
        except Exception:
            pass

    # respect rate limit before network call
    try:
        _acquire_token()
    except Exception:
        pass
    t = get_ticker(ticker)
    df = t.history(period=period, interval=interval, auto_adjust=False)
    if df is None:
        df = pd.DataFrame()
    _HISTORY_CACHE[key] = (now, df)
    if _USE_SQLITE_CACHE:
        try:
            _set_sqlite_cache(key_str, now, df)
        except Exception:
            pass
    return df


def get_histories(tickers: list, period: str = '1mo', interval: str = '1d') -> dict:
    """Fetch histories for multiple tickers using yfinance.download for efficiency.

    Returns a dict {ticker: DataFrame}.
    """
    # Normalize tickers
    tlist = [t.strip().upper() for t in tickers if t]
    if not tlist:
        return {}
    # first, check sqlite cache for available tickers and skip them
    result = {}
    remaining = []
    for t in tlist:
        key_str = f"{t}|{period}|{interval}"
        if _USE_SQLITE_CACHE:
            try:
                r = _get_sqlite_cache(key_str)
                if r is not None:
                    ts, df = r
                    if time.time() - ts < _CACHE_TTL:
                        result[t] = df
                        continue
            except Exception:
                pass
        remaining.append(t)

    if not remaining:
        return result

    # attempt batch download for the remaining tickers
    # try batched download with simple retry/backoff
    max_attempts = 3
    delay = 1
    last_exc = None
    # We'll split remaining tickers into chunks and try downloading chunks in parallel.
    chunks = [remaining[i:i + _YF_BATCH_SIZE] for i in range(0, len(remaining), _YF_BATCH_SIZE)]
    def _download_chunk(chunk):
        # each chunk download respects the global token bucket
        for attempt in range(1, max_attempts + 1):
            try:
                try:
                    _acquire_token()
                except Exception:
                    pass
                df_chunk = yf.download(chunk, period=period, interval=interval, group_by='ticker', auto_adjust=False, threads=True)
                _metrics['chunk_successes'] += 1
                return df_chunk, None
            except Exception as e:
                msg = str(e).lower()
                if '429' in msg or 'too many' in msg or 'quota' in msg:
                    time.sleep(delay * (2 ** (attempt - 1)))
                else:
                    time.sleep(delay * (2 ** (attempt - 1)))
                last = e
                continue
        return None, last

    # run chunk downloads in parallel but limit overall concurrency
    with ThreadPoolExecutor(max_workers=min(_YF_MAX_WORKERS, len(chunks))) as ex:
        futures = {ex.submit(_download_chunk, c): c for c in chunks}
        for fut in as_completed(futures):
            chunk = futures[fut]
            df_chunk, exc = fut.result()
            if exc is not None or df_chunk is None:
                # on failure, fall back to per-ticker get_history for this chunk
                _metrics['chunk_failures'] += 1
                for t in chunk:
                    try:
                        df = get_history(t, period=period, interval=interval)
                        result[t] = df
                    except Exception:
                        result[t] = pd.DataFrame()
                continue
            # parse df_chunk for tickers
            if len(chunk) == 1:
                # single-ticker download may return plain DataFrame
                tname = chunk[0]
                result[tname] = df_chunk
                # cache it
                if _USE_SQLITE_CACHE:
                    try:
                        _set_sqlite_cache(f"{tname}|{period}|{interval}", time.time(), df_chunk)
                    except Exception:
                        pass
                continue
            for t in chunk:
                try:
                    sub = df_chunk[t]
                    sub.columns = df_chunk.columns.levels[0] if hasattr(df_chunk.columns, 'levels') else df_chunk.columns
                    df_sub = sub.dropna(how='all')
                except Exception:
                    df_sub = pd.DataFrame()
                result[t] = df_sub
                if _USE_SQLITE_CACHE:
                    try:
                        _set_sqlite_cache(f"{t}|{period}|{interval}", time.time(), df_sub)
                    except Exception:
                        pass
    return result
    


def get_quote(ticker: str) -> dict:
    t = get_ticker(ticker)
    info = t.info or {}
    quote = {}
    hist = None
    try:
        hist = t.history(period='5d')
    except Exception:
        hist = None
    quote['info'] = info
    if hist is not None and not hist.empty:
        quote['last'] = hist['Close'].iloc[-1]
        quote['open'] = hist['Open'].iloc[-1]
        quote['high'] = hist['High'].iloc[-1]
        quote['low'] = hist['Low'].iloc[-1]
    else:
        quote['last'] = info.get('regularMarketPrice')
        quote['open'] = info.get('open')
        quote['high'] = info.get('dayHigh')
        quote['low'] = info.get('dayLow')
    return quote


def get_vix() -> Optional[float]:
    # VIX ticker on Yahoo: ^VIX
    try:
        t = yf.Ticker('^VIX')
        h = t.history(period='5d')
        if h is not None and not h.empty:
            return float(h['Close'].iloc[-1])
    except Exception:
        return None
    return None
