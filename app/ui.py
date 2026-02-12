from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QTextEdit, QSizePolicy, QComboBox, QFileDialog, QTableView, QProgressBar)
from PyQt6.QtWidgets import QHeaderView
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QAbstractTableModel, QModelIndex, QTimer
from PyQt6.QtGui import QFont
import json
from .strategy import evaluate_ticker
from .data_fetcher import get_vix
from .market_lists import load_market_list, save_example_lists
from .sector import compute_sector_stats
import time
import csv


SAMPLE_TICKERS = ['NVDA', 'META', 'GOOGL', 'AAPL', 'MSFT', 'TSLA']


class WorkerThread(QThread):
    update = pyqtSignal(object)

    def __init__(self, tickers, parent=None):
        super().__init__(parent)
        self.tickers = tickers
        self._running = True

    def run(self):
        while self._running:
            vix = get_vix()
            results = []
            try:
                stats = compute_sector_stats(self.tickers, period='3mo', interval='1d', ma_window=20)
            except Exception:
                # backward compatible: try calling compute_sector_stats
                try:
                    from .sector import compute_sector_stats as _css
                    stats = _css(self.tickers)
                except Exception:
                    stats = None

            # stats structure: ticker_ma20, ticker_sector, sector_mean_ma20, sector_overall_mean
            total = len(self.tickers)
            for idx, t in enumerate(self.tickers):
                try:
                    sector_ma = None
                    sector_ma = None
                    sector_name = None
                    if stats:
                        sec = stats.get('ticker_sector', {}).get(t)
                        sector_name = sec
                        if sec:
                            sector_ma = stats.get('sector_mean_ma', {}).get(sec) or stats.get('sector_overall_mean')
                        else:
                            sector_ma = stats.get('sector_overall_mean')
                    r = evaluate_ticker(t, sector_ma20=sector_ma, vix=vix)
                    # attach sector info to indicators for UI display
                    try:
                        if isinstance(r, dict) and 'indicators' in r and isinstance(r['indicators'], dict):
                            r['indicators']['sector'] = sector_name
                            r['indicators']['sector_ma'] = sector_ma
                    except Exception:
                        pass
                    results.append(r)
                except Exception as e:
                    results.append({'ticker': t, 'grade': 'F', 'reasons': [str(e)], 'indicators': {}, 'demark': {}})

                # emit incremental progress after each ticker
                try:
                    self.update.emit({'vix': vix, 'results': list(results), 'progress': (idx + 1, total)})
                except Exception:
                    pass

            # final emit
            try:
                self.update.emit({'vix': vix, 'results': results, 'progress': (total, total)})
            except Exception:
                pass
            # refresh every 60 seconds
            for _ in range(60):
                if not self._running:
                    break
                time.sleep(1)

    def stop(self):
        self._running = False


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Stock Filter - PyQt 프로토타입')
        self.resize(1000, 700)
        self._apply_dark_theme()

        container = QWidget()
        self.setCentralWidget(container)
        layout = QHBoxLayout()
        container.setLayout(layout)

        # left: table (use model/view for better sorting and performance)
        left = QVBoxLayout()

        class ResultsTableModel(QAbstractTableModel):
            def __init__(self, parent=None):
                super().__init__(parent)
                self._results = []
                self._columns = ['Ticker', 'Grade', 'Last', 'Sector', 'Sector_MA', 'Gap %', 'DeMark_Support']

            def rowCount(self, parent=QModelIndex()):
                return len(self._results)

            def columnCount(self, parent=QModelIndex()):
                return len(self._columns)

            def headerData(self, section, orientation, role=Qt.DisplayRole):
                if role != Qt.DisplayRole:
                    return None
                if orientation == Qt.Horizontal:
                    return self._columns[section]
                return section + 1

            def data(self, index, role=Qt.DisplayRole):
                if not index.isValid():
                    return None
                row = index.row()
                col = index.column()
                item = self._results[row]
                cols = self._columns
                if role == Qt.DisplayRole:
                    if col == 0:
                        return item.get('ticker', '')
                    if col == 1:
                        return item.get('grade', '')
                    if col == 2:
                        v = item.get('indicators', {}).get('last')
                        return f"{v:.2f}" if isinstance(v, (int, float)) else (str(v) if v is not None else '')
                    if col == 3:
                        return item.get('indicators', {}).get('sector') or ''
                    if col == 4:
                        v = item.get('indicators', {}).get('sector_ma')
                        return f"{v:.2f}" if isinstance(v, (int, float)) else ''
                    if col == 5:
                        v = item.get('indicators', {}).get('gap_pct')
                        return f"{v:.2f}" if isinstance(v, (int, float)) else ''
                    if col == 6:
                        v = item.get('demark', {}).get('support')
                        return f"{v:.2f}" if isinstance(v, (int, float)) else ''
                if role == Qt.EditRole:
                    # return raw numeric values for sorting
                    if col == 2:
                        return item.get('indicators', {}).get('last')
                    if col == 4:
                        return item.get('indicators', {}).get('sector_ma')
                    if col == 5:
                        return item.get('indicators', {}).get('gap_pct')
                    if col == 6:
                        return item.get('demark', {}).get('support')
                    return None
                return None

            def sort(self, column, order=Qt.SortOrder.AscendingOrder):
                key_map = {
                    0: lambda r: r.get('ticker', ''),
                    1: lambda r: r.get('grade', ''),
                    2: lambda r: r.get('indicators', {}).get('last') or 0,
                    3: lambda r: r.get('indicators', {}).get('sector') or '',
                    4: lambda r: r.get('indicators', {}).get('sector_ma') or 0,
                    5: lambda r: r.get('indicators', {}).get('gap_pct') or 0,
                    6: lambda r: r.get('demark', {}).get('support') or 0,
                }
                reverse = (order == Qt.SortOrder.DescendingOrder)
                try:
                    self.layoutAboutToBeChanged.emit()
                    self._results.sort(key=key_map.get(column, lambda r: r.get('ticker', '')), reverse=reverse)
                    self.layoutChanged.emit()
                except Exception:
                    pass

            def set_results(self, results):
                self.beginResetModel()
                self._results = results or []
                self.endResetModel()

            def get_row(self, row):
                if 0 <= row < len(self._results):
                    return self._results[row]
                return None

        self._model = ResultsTableModel(self)
        self.table = QTableView()
        self.table.setModel(self._model)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSortingEnabled(True)
        left.addWidget(self.table)

        # market selection
        market_row = QHBoxLayout()
        self.market_combo = QComboBox()
        self.market_combo.addItems(['sample', 'nasdaq', 'kospi'])
        self.load_market_btn = QPushButton('Load Market')
        self.save_example_btn = QPushButton('Save Example Lists')
        market_row.addWidget(self.market_combo)
        market_row.addWidget(self.load_market_btn)
        market_row.addWidget(self.save_example_btn)
        left.addLayout(market_row)

        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton('Start')
        self.stop_btn = QPushButton('Stop')
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        # CSV export
        self.export_btn = QPushButton('Export CSV')
        btn_layout.addWidget(self.export_btn)
        # progress and cancel
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        btn_layout.addWidget(self.progress_bar)
        self.cancel_btn = QPushButton('Cancel')
        self.cancel_btn.setEnabled(False)
        btn_layout.addWidget(self.cancel_btn)
        left.addLayout(btn_layout)

        layout.addLayout(left, 2)

        # right: details
        right = QVBoxLayout()
        self.info_label = QLabel('Status: Ready')
        self.info_label.setFont(QFont('Arial', 11))
        right.addWidget(self.info_label)

        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        right.addWidget(self.details, 1)

        layout.addLayout(right, 3)

        # connections
        self.worker = None
        self.start_btn.clicked.connect(self.start)
        self.stop_btn.clicked.connect(self.stop)
        self.load_market_btn.clicked.connect(self.load_market)
        self.save_example_btn.clicked.connect(lambda: save_example_lists())
        self.export_btn.clicked.connect(self.export_csv)
        self.cancel_btn.clicked.connect(self.stop)

        # AI recommend/backtest buttons
        self.ai_btn = QPushButton('AI Recommend')
        btn_layout.addWidget(self.ai_btn)
        self.ai_btn.clicked.connect(self.on_ai_recommend)
        # AI backtest button
        self.ai_backtest_btn = QPushButton('AI Backtest')
        btn_layout.addWidget(self.ai_backtest_btn)
        self.ai_backtest_btn.clicked.connect(self.on_ai_backtest)

        # current tickers
        self.current_tickers = SAMPLE_TICKERS

    def start(self):
        if self.worker and self.worker.isRunning():
            return
        self.worker = WorkerThread(self.current_tickers)
        self.worker.update.connect(self.on_update)
        self.worker.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.info_label.setText('Status: Running (refresh every 60s)')

    def stop(self):
        if self.worker:
            self.worker.stop()
            self.worker.wait(2000)
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.info_label.setText('Status: Stopped')

    def on_update(self, payload):
        vix = payload.get('vix')
        results = payload.get('results', [])
        progress = payload.get('progress')

        # update model with latest results
        try:
            self._model.set_results(results)
        except Exception:
            pass

        # save latest results for selection-detail view
        self._latest_results = results

        # update progress bar if provided
        if progress:
            try:
                cur, total = progress
                if total > 0:
                    pct = int((cur / total) * 100)
                    self.progress_bar.setMaximum(100)
                    self.progress_bar.setValue(pct)
            except Exception:
                pass

        # Show a compact recommendation area: list S-grade and their DeMark support
        s_items = [r for r in results if r.get('grade') == 'S']
        txt = f'VIX: {vix}\n\n'
        if s_items:
            for it in s_items:
                dem = it.get('demark', {})
                support = dem.get('support')
                indicators = it.get('indicators', {})
                sector = indicators.get('sector') or 'N/A'
                sector_ma = indicators.get('sector_ma')
                gap = indicators.get('gap_pct')
                try:
                    gap_str = f"{gap:.2f}%" if isinstance(gap, (int, float)) else 'N/A'
                    support_str = f"{support:.2f}" if isinstance(support, (int, float)) else 'N/A'
                except Exception:
                    gap_str = 'N/A'
                    support_str = 'N/A'
                txt += f"{it['ticker']} - S급입니다. 섹터: {sector} 섹터_MA: {sector_ma if sector_ma else 'N/A'} 괴리율: {gap_str} 권장 디마크 저가: {support_str}\n"
        else:
            txt += '현재 S급 종목 없음\n'

        # also append details for first ticker
        if results:
            r0 = results[0]
            txt += '\n--- 상세(예시: 첫번째 종목) ---\n'
            txt += f"Ticker: {r0['ticker']}\nGrade: {r0.get('grade')}\nReasons:\n"
            for rr in r0.get('reasons', []):
                txt += f" - {rr}\n"
            txt += '\nIndicators:\n'
            for k, v in r0.get('indicators', {}).items():
                txt += f" - {k}: {v}\n"

        self.details.setPlainText(txt)

    def _on_selection_changed(self):
        try:
            indexes = self.table.selectionModel().selectedIndexes()
            if not indexes:
                return
            # take the row of first selected index
            row = indexes[0].row()
            if not hasattr(self, '_latest_results') or row >= len(self._latest_results):
                return
            obj = self._latest_results[row]
        except Exception:
            return
        try:
            import json
            pretty = json.dumps(obj, ensure_ascii=False, indent=2)
        except Exception:
            pretty = str(obj)
        self.details.setPlainText(pretty)

    def on_ai_recommend(self):
        # fire off a simple AI call for the first selected ticker
        if not hasattr(self, 'current_tickers') or not self.current_tickers:
            self.info_label.setText('No tickers loaded')
            return
        ticker = self.current_tickers[0]
        self.info_label.setText(f'AI: Generating recommendation for {ticker}...')

        # run in separate thread to avoid blocking UI
        from threading import Thread
        def _worker():
            try:
                # quick attempt: if GenAI configured, run the multi-ticker analyzer (mirrors geminiService.ts)
                from .genai_adapter import GenAIAdapter, make_recommendation_prompt, analyze_with_gemini
                from .strategy import DEFAULTS

                adapter = GenAIAdapter()
                if adapter.is_configured():
                    # prepare settings mapping expected by the system instruction
                    settings = {
                        'vixThreshold': DEFAULTS.get('vix_threshold', 30.0),
                        'pegThreshold': DEFAULTS.get('peg_threshold', 1.5),
                        'gapThreshold': DEFAULTS.get('gap_threshold_pct', 5.0),
                        'rsiThreshold': DEFAULTS.get('rsi_max', 70.0)
                    }
                    v = get_vix() or 0
                    tickers = self.current_tickers[:50]
                    parsed = analyze_with_gemini(adapter, equity=10000000, vix=v, tickers=tickers, settings=settings, context='ANALYZE')
                    out = json.dumps(parsed, ensure_ascii=False, indent=2)
                else:
                    # fallback: single-ticker prompt using local indicators
                    res = evaluate_ticker(ticker, sector_ma20=None, vix=None)
                    prompt = make_recommendation_prompt(ticker, res.get('indicators'))
                    out = 'AI 미구성: 환경변수 GEMINI_API_KEY 를 설정하거나 google-generative-ai 클라이언트를 설치하세요.\n예시 프롬프트:\n' + prompt
            except Exception as e:
                out = f'AI 호출 실패: {e}'
            # update UI in main thread
            def _done():
                self.details.setPlainText(out)
                self.info_label.setText('AI: 완료')
            QTimer.singleShot(0, _done)

        import json
        Thread(target=_worker, daemon=True).start()

    def on_ai_backtest(self):
        if not hasattr(self, 'current_tickers') or not self.current_tickers:
            self.info_label.setText('No tickers loaded')
            return
        self.info_label.setText('AI Backtest: running...')

        from threading import Thread
        def _worker():
            try:
                from .ai_portfolio import ai_backtest
                res = ai_backtest(self.current_tickers, start_cash=10000000)
                # res is the summary dict from simple_backtest
                final = res.get('final_cash')
                total_trades = res.get('total_trades') or 0
                trade_pairs = res.get('trade_pairs') or 0
                wins = res.get('wins') or 0
                win_rate = res.get('win_rate')
                mdd = res.get('mdd_pct')
                total_profit = res.get('total_profit')
                return_pct = res.get('return_pct')
                out_lines = [
                    'AI Backtest 완료',
                    f'시작자산: {res.get("start_cash", 0):,.0f} 원',
                    f'최종 현금: {final:,.0f} 원',
                    f'총 트레이드 이벤트: {total_trades}',
                    f'완료된 거래(매수-매도 쌍): {trade_pairs}',
                    f'승수: {wins}',
                    f'승률: {win_rate:.2%}' if win_rate is not None else '승률: N/A',
                    f'총손익: {total_profit:,.0f} 원',
                    f'수익률: {return_pct:.2f} %',
                    f'MDD(근사): {mdd:.2f} %' if mdd is not None else 'MDD: N/A'
                ]
                out = '\n'.join(out_lines)
            except Exception as e:
                out = f'AI Backtest 실패: {e}'

            def _done():
                self.details.setPlainText(out)
                self.info_label.setText('AI Backtest: 완료')
            QTimer.singleShot(0, _done)

        Thread(target=_worker, daemon=True).start()

    def load_market(self):
        market = self.market_combo.currentText()
        if market == 'sample':
            self.current_tickers = SAMPLE_TICKERS
        else:
            tlist = load_market_list(market)
            if not tlist:
                self.info_label.setText(f'경고: {market} 리스트를 찾을 수 없습니다. 예시를 저장하려면 Save Example Lists 클릭')
                self.current_tickers = SAMPLE_TICKERS
            else:
                self.current_tickers = tlist
        # compute sector stats for info
        try:
            sector_info = compute_sector_stats(self.current_tickers)
            sector_mean = sector_info.get('sector_overall_mean')
            if sector_mean:
                self.info_label.setText(f'Loaded {len(self.current_tickers)} tickers. 섹터 평균 MA: {sector_mean:.2f}')
            else:
                self.info_label.setText(f'Loaded {len(self.current_tickers)} tickers. 섹터 평균 MA: N/A')
        except Exception:
            self.info_label.setText(f'Loaded {len(self.current_tickers)} tickers. 섹터 계산 실패')

    def export_csv(self):
        # export current table to CSV
        path, _ = QFileDialog.getSaveFileName(self, 'Export CSV', filter='CSV Files (*.csv)')
        if not path:
            return
        # use model data for export
        headers = self._model._columns
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for row_obj in getattr(self._model, '_results', []):
                row = [
                    row_obj.get('ticker', ''),
                    row_obj.get('grade', ''),
                    row_obj.get('indicators', {}).get('last', ''),
                    row_obj.get('indicators', {}).get('sector', ''),
                    row_obj.get('indicators', {}).get('sector_ma', ''),
                    row_obj.get('indicators', {}).get('gap_pct', ''),
                    row_obj.get('demark', {}).get('support', ''),
                ]
                writer.writerow(row)


    def _apply_dark_theme(self):
        dark = """
        QWidget { background-color: #111217; color: #e6e6e6; }
        QTableWidget { background-color: #0f1720; gridline-color: #222; }
        QHeaderView::section { background-color: #0b1220; color: #ddd; }
        QPushButton { background-color: #1f2937; color: #e6e6e6; padding: 6px; border-radius:4px }
        QTextEdit { background-color: #0b1220; color: #e6e6e6 }
        QLabel { color: #cbd5e1 }
        """
        self.setStyleSheet(dark)
