import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import io
from contextlib import redirect_stdout

# Import the analysis function from the original file
sys.path.append(r"c:\Users\USER\Downloads\StockCode\My stock\My stock")
try:
    from import_yfinance_as_yf import analyze_stock_logic
except ImportError:
    # If import fails, we'll define it here
    pass

class StockAnalyzerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Stock Analyzer - AI Analysis Tool")
        self.root.geometry("1200x800")
        self.root.configure(bg='#f0f0f0')
        
        # Style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Create Notebook for tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tab 1: Single Stock Analysis
        self.single_frame = tk.Frame(self.notebook, bg='#f0f0f0')
        self.notebook.add(self.single_frame, text="📊 Single Stock Analysis")
        
        # Tab 2: Multi-Stock Comparison
        self.multi_frame = tk.Frame(self.notebook, bg='#f0f0f0')
        self.notebook.add(self.multi_frame, text="📈 Stock Comparison")
        
        # Main container for single stock
        main_frame = tk.Frame(self.single_frame, bg='#f0f0f0', padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = tk.Label(
            main_frame, 
            text="🚀 Stock Analyzer", 
            font=('Arial', 24, 'bold'),
            bg='#f0f0f0',
            fg='#2c3e50'
        )
        title_label.pack(pady=(0, 20))
        
        # Input Frame
        input_frame = tk.Frame(main_frame, bg='#f0f0f0')
        input_frame.pack(fill=tk.X, pady=10)
        
        # Stock Ticker Input
        ticker_frame = tk.Frame(input_frame, bg='#f0f0f0')
        ticker_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(
            ticker_frame, 
            text="Stock Ticker:", 
            font=('Arial', 12, 'bold'),
            bg='#f0f0f0',
            width=15,
            anchor='w'
        ).pack(side=tk.LEFT, padx=5)
        
        self.ticker_entry = tk.Entry(
            ticker_frame, 
            font=('Arial', 12),
            width=20
        )
        self.ticker_entry.pack(side=tk.LEFT, padx=5)
        self.ticker_entry.insert(0, "TSLA")
        
        # Quick select buttons for popular stocks
        quick_frame = tk.Frame(ticker_frame, bg='#f0f0f0')
        quick_frame.pack(side=tk.LEFT, padx=10)
        
        tk.Label(quick_frame, text="Quick:", font=('Arial', 10), bg='#f0f0f0').pack(side=tk.LEFT)
        for ticker in ["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL"]:
            btn = tk.Button(
                quick_frame, 
                text=ticker, 
                command=lambda t=ticker: self.ticker_entry.delete(0, tk.END) or self.ticker_entry.insert(0, t),
                font=('Arial', 9),
                bg='#3498db',
                fg='white',
                relief=tk.FLAT,
                padx=5,
                pady=2
            )
            btn.pack(side=tk.LEFT, padx=2)
        
        # Benchmark Selection
        benchmark_frame = tk.Frame(input_frame, bg='#f0f0f0')
        benchmark_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(
            benchmark_frame, 
            text="Benchmark Index:", 
            font=('Arial', 12, 'bold'),
            bg='#f0f0f0',
            width=15,
            anchor='w'
        ).pack(side=tk.LEFT, padx=5)
        
        self.benchmark_var = tk.StringVar(value="^IXIC")
        benchmark_combo = ttk.Combobox(
            benchmark_frame,
            textvariable=self.benchmark_var,
            values=["^IXIC", "^GSPC", "^DJI", "^KS11", "^NKX"],
            state="readonly",
            width=18,
            font=('Arial', 11)
        )
        benchmark_combo.pack(side=tk.LEFT, padx=5)
        
        # Benchmark labels
        labels_frame = tk.Frame(benchmark_frame, bg='#f0f0f0')
        labels_frame.pack(side=tk.LEFT, padx=10)
        tk.Label(
            labels_frame, 
            text="(Nasdaq | S&P500 | Dow | KOSPI | Nikkei)", 
            font=('Arial', 9),
            bg='#f0f0f0',
            fg='#7f8c8d'
        ).pack()
        
        # Analyze Button
        button_frame = tk.Frame(main_frame, bg='#f0f0f0')
        button_frame.pack(pady=15)
        
        self.analyze_button = tk.Button(
            button_frame,
            text="🔍 Analyze Stock",
            command=self.analyze_stock,
            font=('Arial', 14, 'bold'),
            bg='#27ae60',
            fg='white',
            relief=tk.FLAT,
            padx=30,
            pady=10,
            cursor='hand2'
        )
        self.analyze_button.pack()
        
        # Results Display
        results_label = tk.Label(
            main_frame,
            text="Analysis Results:",
            font=('Arial', 12, 'bold'),
            bg='#f0f0f0',
            anchor='w'
        )
        results_label.pack(fill=tk.X, pady=(20, 5))
        
        # Scrolled Text for results
        self.results_text = scrolledtext.ScrolledText(
            main_frame,
            font=('Consolas', 10),
            bg='#2c3e50',
            fg='#ecf0f1',
            wrap=tk.WORD,
            relief=tk.FLAT,
            padx=10,
            pady=10
        )
        self.results_text.pack(fill=tk.BOTH, expand=True)
        
        # Status bar
        self.status_label = tk.Label(
            main_frame,
            text="Ready. Enter a stock ticker and click Analyze.",
            font=('Arial', 9),
            bg='#f0f0f0',
            fg='#7f8c8d',
            anchor='w'
        )
        self.status_label.pack(fill=tk.X, pady=(5, 0))
    
        # ========== MULTI-STOCK COMPARISON TAB ==========
        multi_main = tk.Frame(self.multi_frame, bg='#f0f0f0', padx=20, pady=20)
        multi_main.pack(fill=tk.BOTH, expand=True)
        
        # Title
        multi_title = tk.Label(
            multi_main,
            text="📈 Multi-Stock Comparison",
            font=('Arial', 24, 'bold'),
            bg='#f0f0f0',
            fg='#2c3e50'
        )
        multi_title.pack(pady=(0, 20))
        
        # Input section for multi-stock
        multi_input_frame = tk.Frame(multi_main, bg='#f0f0f0')
        multi_input_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(
            multi_input_frame,
            text="Stock Tickers (comma-separated):",
            font=('Arial', 12, 'bold'),
            bg='#f0f0f0',
            anchor='w'
        ).pack(side=tk.LEFT, padx=5)
        
        self.multi_ticker_entry = tk.Entry(
            multi_input_frame,
            font=('Arial', 12),
            width=40
        )
        self.multi_ticker_entry.pack(side=tk.LEFT, padx=5)
        
        # Predefined top 10 stocks for default display
        top_10_stocks = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "BRK-B", "V", "JNJ"]
        self.multi_ticker_entry.insert(0, ", ".join(top_10_stocks))
        
        # Quick load buttons
        quick_multi_frame = tk.Frame(multi_input_frame, bg='#f0f0f0')
        quick_multi_frame.pack(side=tk.LEFT, padx=10)
        
        tk.Button(
            quick_multi_frame,
            text="Load Top 10 Tech",
            command=lambda: self.multi_ticker_entry.delete(0, tk.END) or self.multi_ticker_entry.insert(0, ", ".join(["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "AMD", "INTC", "CRM"])),
            font=('Arial', 9),
            bg='#3498db',
            fg='white',
            relief=tk.FLAT,
            padx=5,
            pady=2
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            quick_multi_frame,
            text="Load Top 10 S&P",
            command=lambda: self.multi_ticker_entry.delete(0, tk.END) or self.multi_ticker_entry.insert(0, ", ".join(top_10_stocks)),
            font=('Arial', 9),
            bg='#3498db',
            fg='white',
            relief=tk.FLAT,
            padx=5,
            pady=2
        ).pack(side=tk.LEFT, padx=2)
        
        # Benchmark for multi-stock
        multi_bench_frame = tk.Frame(multi_main, bg='#f0f0f0')
        multi_bench_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(
            multi_bench_frame,
            text="Benchmark:",
            font=('Arial', 12, 'bold'),
            bg='#f0f0f0',
            width=15,
            anchor='w'
        ).pack(side=tk.LEFT, padx=5)
        
        self.multi_benchmark_var = tk.StringVar(value="^IXIC")
        ttk.Combobox(
            multi_bench_frame,
            textvariable=self.multi_benchmark_var,
            values=["^IXIC", "^GSPC", "^DJI", "^KS11", "^NKX"],
            state="readonly",
            width=18,
            font=('Arial', 11)
        ).pack(side=tk.LEFT, padx=5)
        
        # Analyze button for multi-stock
        multi_button_frame = tk.Frame(multi_main, bg='#f0f0f0')
        multi_button_frame.pack(pady=15)
        
        self.multi_analyze_button = tk.Button(
            multi_button_frame,
            text="🔍 Compare Stocks",
            command=self.analyze_multiple_stocks,
            font=('Arial', 14, 'bold'),
            bg='#9b59b6',
            fg='white',
            relief=tk.FLAT,
            padx=30,
            pady=10,
            cursor='hand2'
        )
        self.multi_analyze_button.pack()
        
        # Filter section (placed before canvas)
        filter_frame = tk.Frame(multi_main, bg='#f0f0f0')
        filter_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(
            filter_frame,
            text="Filter by Rating:",
            font=('Arial', 12, 'bold'),
            bg='#f0f0f0',
            anchor='w'
        ).pack(side=tk.LEFT, padx=5)
        
        self.filter_var = tk.StringVar(value="ALL")
        filter_buttons_frame = tk.Frame(filter_frame, bg='#f0f0f0')
        filter_buttons_frame.pack(side=tk.LEFT, padx=10)
        
        filter_colors = {
            "ALL": "#3498db",
            "S": "#27ae60",
            "A": "#f39c12",
            "F": "#e74c3c"
        }
        
        self.filter_buttons = {}
        for rating in ["ALL", "S", "A", "F"]:
            btn = tk.Button(
                filter_buttons_frame,
                text=rating,
                command=lambda r=rating: self.apply_filter(r),
                font=('Arial', 11, 'bold'),
                bg=filter_colors[rating],
                fg='white',
                relief=tk.RAISED,
                bd=2,
                padx=15,
                pady=5,
                width=5,
                cursor='hand2'
            )
            btn.pack(side=tk.LEFT, padx=3)
            self.filter_buttons[rating] = btn
        
        # Set initial active button
        self.filter_buttons["ALL"].config(relief=tk.SUNKEN, bd=3)
        
        # Store all results
        self.all_results = []
        self.current_filter = "ALL"
        
        # Canvas for scrollable results
        canvas_frame = tk.Frame(multi_main, bg='#f0f0f0')
        canvas_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.multi_canvas = tk.Canvas(
            canvas_frame,
            bg='#f0f0f0',
            highlightthickness=0
        )
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.multi_canvas.yview)
        self.multi_scrollable_frame = tk.Frame(self.multi_canvas, bg='#f0f0f0')
        
        # Update scroll region when frame size changes
        def configure_scroll_region(event):
            self.multi_canvas.configure(scrollregion=self.multi_canvas.bbox("all"))
        self.multi_scrollable_frame.bind("<Configure>", configure_scroll_region)
        
        self.multi_canvas_window = self.multi_canvas.create_window((0, 0), window=self.multi_scrollable_frame, anchor="nw")
        self.multi_canvas.configure(yscrollcommand=scrollbar.set)
        
        # Make canvas window resize with canvas
        def on_canvas_configure(event):
            canvas_width = event.width
            self.multi_canvas.itemconfig(self.multi_canvas_window, width=canvas_width)
        self.multi_canvas.bind('<Configure>', on_canvas_configure)
        
        # Mouse wheel scrolling
        def _on_mousewheel(event):
            self.multi_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.multi_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        self.multi_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Add initial placeholder message
        self.show_placeholder()
        
        # Status for multi-stock
        self.multi_status_label = tk.Label(
            multi_main,
            text="Enter stock tickers (comma-separated) and click Compare.",
            font=('Arial', 9),
            bg='#f0f0f0',
            fg='#7f8c8d',
            anchor='w'
        )
        self.multi_status_label.pack(fill=tk.X, pady=(5, 0))
    
    def analyze_stock(self):
        ticker = self.ticker_entry.get().strip().upper()
        benchmark = self.benchmark_var.get()
        
        if not ticker:
            messagebox.showerror("Error", "Please enter a stock ticker.")
            return
        
        # Disable button during analysis
        self.analyze_button.config(state=tk.DISABLED, text="⏳ Analyzing...")
        self.root.update()
        
        # Clear previous results
        self.results_text.delete(1.0, tk.END)
        self.status_label.config(text=f"Analyzing {ticker}...")
        
        try:
            # Capture output from the analysis function
            output = io.StringIO()
            with redirect_stdout(output):
                analyze_stock_logic(ticker, benchmark_ticker=benchmark)
            
            result = output.getvalue()
            
            # Display results
            self.results_text.insert(tk.END, result)
            self.results_text.see(tk.END)
            self.status_label.config(text=f"Analysis complete for {ticker}!")
            
        except Exception as e:
            error_msg = f"❌ Error analyzing {ticker}:\n{str(e)}\n\n"
            error_msg += "Please check:\n"
            error_msg += "1. Ticker symbol is correct (e.g., AAPL, TSLA, 005930.KS)\n"
            error_msg += "2. Internet connection is working\n"
            error_msg += "3. Stock data is available on Yahoo Finance"
            
            self.results_text.insert(tk.END, error_msg)
            self.status_label.config(text=f"Error analyzing {ticker}")
            messagebox.showerror("Analysis Error", f"Failed to analyze {ticker}:\n{str(e)}")
        
        finally:
            # Re-enable button
            self.analyze_button.config(state=tk.NORMAL, text="🔍 Analyze Stock")
    
    def get_stock_rating(self, ticker, benchmark_ticker="^IXIC"):
        """Get just the rating (S/A/F) and key metrics for a stock"""
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1y")
            
            if len(hist) < 200:
                return {
                    'ticker': ticker,
                    'rating': 'N/A',
                    'price': 0,
                    'rsi': 0,
                    'ma200': 0,
                    'error': 'Insufficient data'
                }
            
            bench = yf.Ticker(benchmark_ticker)
            bench_hist = bench.history(period="1y")
            
            vix = yf.Ticker("^VIX")
            vix_hist = vix.history(period="5d")
            current_vix = vix_hist['Close'].iloc[-1]
            
            info = stock.info
            
            current_price = hist['Close'].iloc[-1]
            ma200 = hist['Close'].rolling(window=200).mean().iloc[-1]
            
            # RSI
            delta = hist['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs)).iloc[-1]
            
            # Gap
            stock_ret_20 = hist['Close'].pct_change(20).iloc[-1]
            bench_ret_20 = bench_hist['Close'].pct_change(20).iloc[-1]
            gap = bench_ret_20 - stock_ret_20
            
            # PEG & Growth
            peg = info.get('pegRatio', None)
            if peg is None:
                peg = 99
            rev_growth = info.get('revenueGrowth', 0)
            
            # Determine rating
            is_s_class = True
            reasons = []
            
            if current_vix >= 30:
                is_s_class = False
                reasons.append("VIX > 30")
            
            if is_s_class:
                if current_price < ma200:
                    is_s_class = False
                    reasons.append("Below MA200")
                
                if peg > 1.5 and rev_growth < 0.30:
                    is_s_class = False
                    reasons.append("High PEG")
                
                if rsi >= 70:
                    is_s_class = False
                    reasons.append("RSI > 70")
            
            # Determine final rating
            if is_s_class:
                rating = 'S'
            elif current_price > ma200 and "Below MA200" not in reasons:
                rating = 'A'
            else:
                rating = 'F'
            
            return {
                'ticker': ticker,
                'rating': rating,
                'price': current_price,
                'rsi': rsi,
                'ma200': ma200,
                'vix': current_vix,
                'peg': peg,
                'growth': rev_growth * 100,
                'reasons': reasons
            }
            
        except Exception as e:
            return {
                'ticker': ticker,
                'rating': 'ERROR',
                'price': 0,
                'rsi': 0,
                'ma200': 0,
                'error': str(e)
            }
    
    def analyze_multiple_stocks(self):
        """Analyze multiple stocks in background (quietly)"""
        tickers_str = self.multi_ticker_entry.get().strip()
        benchmark = self.multi_benchmark_var.get()
        
        if not tickers_str:
            messagebox.showerror("Error", "Please enter stock tickers.")
            return
        
        # Parse tickers
        tickers = [t.strip().upper() for t in tickers_str.split(',') if t.strip()]
        
        if not tickers:
            messagebox.showerror("Error", "No valid tickers found.")
            return
        
        # Limit to 10 stocks
        if len(tickers) > 10:
            tickers = tickers[:10]
            messagebox.showinfo("Info", "Limited to first 10 stocks.")
        
        # Disable button
        self.multi_analyze_button.config(state=tk.DISABLED, text="⏳ Analyzing...")
        self.root.update()
        
        # Clear previous results
        for widget in self.multi_scrollable_frame.winfo_children():
            widget.destroy()
        
        self.multi_status_label.config(text=f"Analyzing {len(tickers)} stocks in background...")
        
        # Analyze each stock quietly (no printing)
        results = []
        for i, ticker in enumerate(tickers):
            self.multi_status_label.config(text=f"Analyzing {i+1}/{len(tickers)}: {ticker}...")
            self.root.update()
            result = self.get_stock_rating(ticker, benchmark)
            results.append(result)
        
        # Store all results
        self.all_results = results
        
        # Display filtered results
        self.apply_filter(self.current_filter)
        
        # Re-enable button
        self.multi_analyze_button.config(state=tk.NORMAL, text="🔍 Compare Stocks")
        
        # Count by rating
        s_count = sum(1 for r in results if r['rating'] == 'S')
        a_count = sum(1 for r in results if r['rating'] == 'A')
        f_count = sum(1 for r in results if r['rating'] == 'F')
        error_count = sum(1 for r in results if r['rating'] in ['ERROR', 'N/A'])
        
        self.multi_status_label.config(
            text=f"✓ Analysis complete! S: {s_count} | A: {a_count} | F: {f_count} | Errors: {error_count}"
        )
    
    def apply_filter(self, rating_filter):
        """Apply rating filter and display results"""
        self.current_filter = rating_filter
        
        # Update button states (show which is active)
        for rating, btn in self.filter_buttons.items():
            if rating == rating_filter:
                btn.config(relief=tk.SUNKEN, bd=3)
            else:
                btn.config(relief=tk.RAISED, bd=2)
        
        # Clear current display
        for widget in self.multi_scrollable_frame.winfo_children():
            widget.destroy()
        
        if not self.all_results:
            self.show_placeholder()
            return
        
        # Filter results
        if rating_filter == "ALL":
            filtered_results = self.all_results
        else:
            filtered_results = [r for r in self.all_results if r['rating'] == rating_filter]
        
        # Display filtered results
        self.display_stock_cards(filtered_results)
        
        # Update status
        count = len(filtered_results)
        filter_text = "All Ratings" if rating_filter == "ALL" else f"{rating_filter}-Class Only"
        self.multi_status_label.config(
            text=f"Showing {count} stocks ({filter_text})"
        )
    
    def show_placeholder(self):
        """Show placeholder message when no analysis has been run"""
        # Clear current display
        for widget in self.multi_scrollable_frame.winfo_children():
            widget.destroy()
        
        placeholder_frame = tk.Frame(self.multi_scrollable_frame, bg='#f0f0f0')
        placeholder_frame.pack(fill=tk.BOTH, expand=True, pady=100)
        
        tk.Label(
            placeholder_frame,
            text="📊 Stock Comparison",
            font=('Arial', 24, 'bold'),
            bg='#f0f0f0',
            fg='#2c3e50'
        ).pack(pady=20)
        
        tk.Label(
            placeholder_frame,
            text="1. Enter stock tickers (comma-separated) or click 'Load Top 10 S&P' / 'Load Top 10 Tech'\n"
                 "2. Click 'Compare Stocks' to analyze\n"
                 "3. Use filter buttons (ALL, S, A, F) to view specific ratings",
            font=('Arial', 12),
            bg='#f0f0f0',
            fg='#7f8c8d',
            justify=tk.LEFT
        ).pack(pady=10)
    
    def display_stock_cards(self, results):
        """Display stock ratings as visual cards"""
        if not results:
            no_results_frame = tk.Frame(self.multi_scrollable_frame, bg='#f0f0f0', pady=50)
            no_results_frame.pack(fill=tk.BOTH, expand=True)
            tk.Label(
                no_results_frame,
                text="No stocks match the current filter.",
                font=('Arial', 14),
                bg='#f0f0f0',
                fg='#7f8c8d'
            ).pack()
            return
        
        # Sort by rating (S > A > F)
        rating_order = {'S': 0, 'A': 1, 'F': 2, 'ERROR': 3, 'N/A': 4}
        results.sort(key=lambda x: (rating_order.get(x['rating'], 99), x['ticker']))
        
        # Create header with summary
        header_frame = tk.Frame(self.multi_scrollable_frame, bg='#34495e', pady=10)
        header_frame.pack(fill=tk.X, padx=10, pady=5)
        
        title_label = tk.Label(
            header_frame,
            text="📊 Stock Ratings Comparison",
            font=('Arial', 16, 'bold'),
            bg='#34495e',
            fg='white'
        )
        title_label.pack()
        
        # Summary counts
        s_count = sum(1 for r in results if r['rating'] == 'S')
        a_count = sum(1 for r in results if r['rating'] == 'A')
        f_count = sum(1 for r in results if r['rating'] == 'F')
        
        summary_text = f"👑 S-Class: {s_count}  |  🥈 A-Class: {a_count}  |  🗑️ F-Class: {f_count}  |  Total: {len(results)}"
        summary_label = tk.Label(
            header_frame,
            text=summary_text,
            font=('Arial', 11),
            bg='#34495e',
            fg='#ecf0f1'
        )
        summary_label.pack(pady=(5, 0))
        
        # Create cards in grid
        cards_frame = tk.Frame(self.multi_scrollable_frame, bg='#f0f0f0')
        cards_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Color scheme
        colors = {
            'S': {'bg': '#27ae60', 'fg': 'white', 'icon': '👑'},
            'A': {'bg': '#f39c12', 'fg': 'white', 'icon': '🥈'},
            'F': {'bg': '#e74c3c', 'fg': 'white', 'icon': '🗑️'},
            'ERROR': {'bg': '#95a5a6', 'fg': 'white', 'icon': '❌'},
            'N/A': {'bg': '#7f8c8d', 'fg': 'white', 'icon': '⚠️'}
        }
        
        # Create cards in 2 columns
        for idx, result in enumerate(results):
            row = idx // 2
            col = idx % 2
            
            rating = result['rating']
            color = colors.get(rating, colors['N/A'])
            
            # Card frame
            card = tk.Frame(
                cards_frame,
                bg=color['bg'],
                relief=tk.RAISED,
                bd=2,
                padx=15,
                pady=15
            )
            card.grid(row=row, column=col, padx=10, pady=10, sticky='nsew')
            
            # Ticker and Rating
            ticker_frame = tk.Frame(card, bg=color['bg'])
            ticker_frame.pack(fill=tk.X, pady=(0, 10))
            
            tk.Label(
                ticker_frame,
                text=f"{color['icon']} {result['ticker']}",
                font=('Arial', 18, 'bold'),
                bg=color['bg'],
                fg=color['fg']
            ).pack(side=tk.LEFT)
            
            tk.Label(
                ticker_frame,
                text=f"{rating}-CLASS",
                font=('Arial', 14, 'bold'),
                bg=color['bg'],
                fg=color['fg']
            ).pack(side=tk.RIGHT)
            
            # Metrics
            metrics_frame = tk.Frame(card, bg=color['bg'])
            metrics_frame.pack(fill=tk.X)
            
            if result.get('error'):
                tk.Label(
                    metrics_frame,
                    text=f"Error: {result['error']}",
                    font=('Arial', 10),
                    bg=color['bg'],
                    fg=color['fg'],
                    wraplength=200
                ).pack(anchor='w', pady=2)
            else:
                metrics = [
                    f"💰 Price: ${result['price']:.2f}",
                    f"📈 RSI: {result['rsi']:.1f}",
                    f"📊 MA200: ${result['ma200']:.2f}",
                ]
                
                if result.get('peg') and result['peg'] != 99:
                    metrics.append(f"💎 PEG: {result['peg']:.2f}")
                
                if result.get('growth') is not None:
                    metrics.append(f"📈 Growth: {result['growth']:.1f}%")
                
                for metric in metrics:
                    tk.Label(
                        metrics_frame,
                        text=metric,
                        font=('Arial', 10),
                        bg=color['bg'],
                        fg=color['fg'],
                        anchor='w'
                    ).pack(anchor='w', pady=1)
                
                if result.get('reasons'):
                    reasons_text = "⚠️ " + ", ".join(result['reasons'])
                    tk.Label(
                        metrics_frame,
                        text=reasons_text,
                        font=('Arial', 9, 'italic'),
                        bg=color['bg'],
                        fg=color['fg'],
                        anchor='w',
                        wraplength=200
                    ).pack(anchor='w', pady=(5, 0))
        
        # Configure grid weights
        cards_frame.grid_columnconfigure(0, weight=1)
        cards_frame.grid_columnconfigure(1, weight=1)


# Define the analysis function here if import fails
def analyze_stock_logic(ticker, benchmark_ticker="^IXIC"):
    print(f"\n{'='*60}")
    print(f"🚀 [AI 분석 시작] 종목: {ticker}")
    print(f"{'='*60}")

    # 1. 데이터 가져오기 (yfinance)
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        
        if len(hist) < 200:
            print("❌ 데이터가 부족합니다 (200일 미만). 분석 불가.")
            return
        
        bench = yf.Ticker(benchmark_ticker)
        bench_hist = bench.history(period="1y")
        
        vix = yf.Ticker("^VIX")
        vix_hist = vix.history(period="5d")
        current_vix = vix_hist['Close'].iloc[-1]
        
        info = stock.info
        
    except Exception as e:
        print(f"❌ 데이터 수집 중 오류 발생: {e}")
        return

    # 데이터 전처리
    current_price = hist['Close'].iloc[-1]
    ma200 = hist['Close'].rolling(window=200).mean().iloc[-1]
    
    # RSI
    delta = hist['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs)).iloc[-1]
    
    # Gap
    stock_ret_20 = hist['Close'].pct_change(20).iloc[-1]
    bench_ret_20 = bench_hist['Close'].pct_change(20).iloc[-1]
    gap = bench_ret_20 - stock_ret_20

    # PEG & 성장률
    peg = info.get('pegRatio', None)
    rev_growth = info.get('revenueGrowth', 0)

    # 논리적 필터링
    is_s_class = True
    reasons = []
    
    # 1. VIX
    print(f"\n1️⃣ [방패] 시장 상황 (VIX)")
    print(f"   - 현재 VIX: {current_vix:.2f} (기준: 30 미만)")
    if current_vix >= 30:
        print("   -> 🚨 FAIL: 시장이 공포 상태입니다. 매매 중단(Cash 100%).")
        is_s_class = False
        reasons.append("시장 위험(VIX > 30)")
    else:
        print("   -> ✅ PASS: 시장 안정적.")

    if is_s_class:
        # 2. 추세
        print(f"\n2️⃣ [추세] 200일선 검증 (MA200)")
        print(f"   - 현재가: ${current_price:.2f}")
        print(f"   - 200일선: ${ma200:.2f}")
        
        if current_price < ma200:
            print("   -> ❌ FAIL: 역배열(하락 추세). 절대 매수 금지.")
            is_s_class = False
            reasons.append("추세 이탈(200일선 아래)")
        else:
            print("   -> ✅ PASS: 정배열(상승 추세) 유지 중.")

        # 3. 가치
        print(f"\n3️⃣ [가치] 펀더멘털 점검 (PEG & 성장)")
        if peg is not None:
            print(f"   - PEG 비율: {peg} (기준: 1.5 이하)")
        else:
            print(f"   - PEG 비율: 정보 없음 (보수적 접근 필요)")
            peg = 99
            
        print(f"   - 매출 성장률: {rev_growth*100:.1f}%")

        if peg > 1.5 and rev_growth < 0.30:
            print("   -> ⚠️ WARNING: 성장에 비해 주가가 비쌉니다.")
            is_s_class = False 
            reasons.append("가치 고평가(PEG 높음)")
        elif peg > 1.5 and rev_growth >= 0.30:
            print("   -> 👑 PASS(특례): 비싸지만 미친 성장(>30%)으로 정당화됨.")
        else:
            print("   -> ✅ PASS: 성장성 대비 저평가 구간.")

        # 4. 타이밍
        print(f"\n4️⃣ [타이밍] 과열 및 소외 여부")
        print(f"   - RSI(14): {rsi:.1f} (기준: 70 미만)")
        print(f"   - Gap(괴리율): {gap*100:.1f}% (기준: 5% 이상이면 줍줍 기회)")
        
        if rsi >= 70:
            print("   -> ❌ FAIL: 단기 과열(RSI > 70). 조정 기다리세요.")
            is_s_class = False
            reasons.append("단기 과열(RSI)")
        elif gap > 0.05:
            print("   -> ⭐ BONUS: 시장 대비 5% 이상 덜 올랐습니다. (저평가/눌림목)")
        else:
            print("   -> ✅ PASS: 진입하기 양호한 구간.")

    # DeMark 스나이퍼
    print(f"\n5️⃣ [스나이퍼] 오늘 얼마에 주문 넣을까? (DeMark)")
    
    yesterday = hist.iloc[-2]
    y_open = yesterday['Open']
    y_high = yesterday['High']
    y_low = yesterday['Low']
    y_close = yesterday['Close']
    
    if y_close > y_open:
        pivot = (y_high * 2 + y_low + y_close) / 4
        candle_type = "🔺양봉 (강세 마감)"
    elif y_close < y_open:
        pivot = (y_high + y_low * 2 + y_close) / 4
        candle_type = "🟦음봉 (약세 마감)"
    else:
        pivot = (y_high + y_low + y_close * 2) / 4
        candle_type = "➖도지 (보합)"
        
    target_high = pivot * 2 - y_low
    target_low = pivot * 2 - y_high

    print(f"   - 어제 캔들: {candle_type}")
    print(f"   - 🎯 최적 매수가(Support): ${target_low:.2f}")
    print(f"   - 🎯 단타 매도가(Resist):  ${target_high:.2f}")

    # 최종 결론
    print(f"\n{'='*60}")
    print(f"📋 [AI 최종 리포트]")
    
    if is_s_class:
        print(f"   👑 등급: S-CLASS (강력 매수)")
        print(f"   💰 비중: 자산의 30% ")
        print(f"   💡 행동: 오늘 장 열리면 ${target_low:.2f} 에 매수 대기하세요.")
    elif current_price > ma200 and "추세 이탈" not in reasons:
        print(f"   🥈 등급: A-CLASS (관심/분산)")
        print(f"   💰 비중: 자산의 10% ")
        print(f"   ⚠️ 주의: {', '.join(reasons)}")
        print(f"   💡 행동: 눌림목(${target_low:.2f}) 줄 때만 소액 진입.")
    else:
        print(f"   🗑️ 등급: F-CLASS (매수 금지)")
        print(f"   ❌ 이유: {', '.join(reasons)} ")
        print(f"   💡 행동: 관망하거나 200일선 회복 시까지 대기.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    root = tk.Tk()
    app = StockAnalyzerGUI(root)
    root.mainloop()

