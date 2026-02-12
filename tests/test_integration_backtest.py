import pandas as pd
import numpy as np
import datetime as dt
import pytest

from app import data_fetcher, backtester, strategy


def make_series(start=100.0, days=252, drift=0.0005):
    import pandas as pd
    import numpy as np
    import datetime as dt
    import pytest

    from app import data_fetcher, backtester, strategy


    def make_series(start=100.0, days=252, drift=0.0005):
        # simple geometric walk
        dates = pd.date_range(end=dt.datetime.today(), periods=days, freq='B')
        returns = np.random.normal(loc=drift, scale=0.01, size=days)
        price = start * np.cumprod(1 + returns)
        df = pd.DataFrame({
            'Open': price * (1 - 0.002),
            'High': price * (1 + 0.002),
            'Low': price * (1 - 0.003),
            'Close': price,
            'Volume': np.random.randint(1000, 10000, size=days)
        }, index=dates)
        return df


    @pytest.fixture(autouse=True)
    def patch_data(monkeypatch):
        # Patch data_fetcher.get_history / get_histories to return deterministic small data
        def fake_get_history(ticker, period='1y', interval='1d'):
            return make_series(start=50.0 + (abs(hash(ticker)) % 100), days=252)

        def fake_get_histories(tickers, period='1mo', interval='1d'):
            out = {}
            for t in tickers:
                out[t] = make_series(start=50.0 + (abs(hash(t)) % 100), days=252)
            return out

        monkeypatch.setattr(data_fetcher, 'get_history', fake_get_history)
        monkeypatch.setattr(data_fetcher, 'get_histories', fake_get_histories)
        yield


    def test_integration_backtest_runs():
        # simple integration: evaluate two tickers and run a backtest with equal allocation
        tickers = ['AAA', 'BBB']
        # evaluate (strategy.evaluate_ticker should not crash)
        results = {}
        for t in tickers:
            res = strategy.evaluate_ticker(t, sector_ma20=None, vix=12.0)
            assert 'grade' in res
            results[t] = res

        # create allocations: equal 50/50
        equity = 100000
        allocation_map = {t: equity * 0.5 for t in tickers}

        # run a simple backtest: buy at first day's close, sell at last day's close
        histories = data_fetcher.get_histories(tickers, period='1y', interval='1d')
        summary = backtester.simple_backtest(histories=histories, allocation_map=allocation_map, start_cash=equity)

        assert 'final_cash' in summary
        assert summary['final_cash'] >= 0
        assert 'total_trades' in summary
        assert isinstance(summary['total_trades'], int)