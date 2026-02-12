import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

def analyze_stock_logic(ticker, benchmark_ticker="^IXIC"): # 기본 벤치마크: 나스닥
    print(f"\n{'='*60}")
    print(f"🚀 [AI 분석 시작] 종목: {ticker}")
    print(f"{'='*60}")

    # 1. 데이터 가져오기 (yfinance)
    try:
        stock = yf.Ticker(ticker)
        # 과거 데이터 (넉넉하게 1년치)
        hist = stock.history(period="1y")
        
        # 벤치마크(지수) 데이터 (Gap 계산용)
        bench = yf.Ticker(benchmark_ticker)
        bench_hist = bench.history(period="1y")
        
        # VIX 지수 (시장 방어용)
        vix = yf.Ticker("^VIX")
        vix_hist = vix.history(period="5d")
        current_vix = vix_hist['Close'].iloc[-1]
        
        # 재무 정보 (PEG, 성장률)
        info = stock.info
        
    except Exception as e:
        print(f"❌ 데이터 수집 중 오류 발생: {e}")
        return

    # --- 데이터 전처리 ---
    current_price = hist['Close'].iloc[-1]
    
    # MA200 (200일 이동평균선)
    ma200 = hist['Close'].rolling(window=200).mean().iloc[-1]
    
    # RSI (14일)
    delta = hist['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs)).iloc[-1]
    
    # Gap (20일 수익률 괴리율)
    stock_ret_20 = hist['Close'].pct_change(20).iloc[-1]
    bench_ret_20 = bench_hist['Close'].pct_change(20).iloc[-1]
    gap = bench_ret_20 - stock_ret_20 # 지수는 갔는데 내 종목만 못 갔으면 양수(+)

    # PEG & 성장률 (데이터 없을 경우 0 처리)
    peg = info.get('pegRatio', None)
    rev_growth = info.get('revenueGrowth', 0)

    # ---------------------------------------------------------
    # 🕵️‍♂️ [1단계] 논리적 필터링 (Logic Chain)
    # ---------------------------------------------------------
    
    is_s_class = True
    reasons = [] # 탈락 사유 저장
    
    # 1. 🛡️ 방패 (Shield) - VIX 
    print(f"\n1️⃣ [방패] 시장 상황 (VIX)")
    print(f"   - 현재 VIX: {current_vix:.2f} (기준: 30 미만)")
    if current_vix >= 30:
        print("   -> 🚨 FAIL: 시장이 공포 상태입니다. 매매 중단(Cash 100%).")
        is_s_class = False
        reasons.append("시장 위험(VIX > 30)")
    else:
        print("   -> ✅ PASS: 시장 안정적.")

    if is_s_class: # 시장이 통과되어야 종목 분석 시작
        # 2. 🧠 두뇌 (Trend) - 추세 
        print(f"\n2️⃣ [추세] 200일선 검증 (MA200)")
        print(f"   - 현재가: ${current_price:.2f}")
        print(f"   - 200일선: ${ma200:.2f}")
        
        if current_price < ma200:
            print("   -> ❌ FAIL: 역배열(하락 추세). 절대 매수 금지.")
            is_s_class = False
            reasons.append("추세 이탈(200일선 아래)")
        else:
            print("   -> ✅ PASS: 정배열(상승 추세) 유지 중.")

        # 3. 📊 가치 (Value/Growth) - PEG & 성장성 
        print(f"\n3️⃣ [가치] 펀더멘털 점검 (PEG & 성장)")
        if peg is not None:
            print(f"   - PEG 비율: {peg} (기준: 1.5 이하)")
        else:
            print(f"   - PEG 비율: 정보 없음 (보수적 접근 필요)")
            peg = 99 # 데이터 없으면 비싼 걸로 간주
            
        print(f"   - 매출 성장률: {rev_growth*100:.1f}%")

        # 로직: PEG < 1.5 (합격) OR 성장률 > 30% (특례 합격)
        if peg > 1.5 and rev_growth < 0.30:
            print("   -> ⚠️ WARNING: 성장에 비해 주가가 비쌉니다.")
            # S급에서는 탈락이지만, 추세가 좋으면 A급은 가능
            is_s_class = False 
            reasons.append("가치 고평가(PEG 높음)")
        elif peg > 1.5 and rev_growth >= 0.30:
            print("   -> 👑 PASS(특례): 비싸지만 미친 성장(>30%)으로 정당화됨.")
        else:
            print("   -> ✅ PASS: 성장성 대비 저평가 구간.")

        # 4. ⚡ 타이밍 (Timing) - Gap & RSI 
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

    # ---------------------------------------------------------
    # 🎯 [2단계] 디마크 스나이퍼 (DeMark Indicator)
    # 엑셀 공식 적용: 양봉(H가중), 음봉(L가중) 
    # ---------------------------------------------------------
    print(f"\n5️⃣ [스나이퍼] 오늘 얼마에 주문 넣을까? (DeMark)")
    
    # 어제 데이터 (iloc[-2])
    yesterday = hist.iloc[-2]
    y_open = yesterday['Open']
    y_high = yesterday['High']
    y_low = yesterday['Low']
    y_close = yesterday['Close']
    
    # 피벗 포인트 계산 (사용자 엑셀 수정 공식 반영)
    if y_close > y_open: # 양봉 (시장 강세 -> 고가 가중)
        pivot = (y_high * 2 + y_low + y_close) / 4
        candle_type = "🔺양봉 (강세 마감)"
    elif y_close < y_open: # 음봉 (시장 약세 -> 저가 가중)
        pivot = (y_high + y_low * 2 + y_close) / 4
        candle_type = "🟦음봉 (약세 마감)"
    else: # 도지
        pivot = (y_high + y_low + y_close * 2) / 4
        candle_type = "➖도지 (보합)"
        
    target_high = pivot * 2 - y_low  # 저항선 (단타 매도)
    target_low = pivot * 2 - y_high  # 지지선 (최적 매수) 

    print(f"   - 어제 캔들: {candle_type}")
    print(f"   - 🎯 최적 매수가(Support): ${target_low:.2f}")
    print(f"   - 🎯 단타 매도가(Resist):  ${target_high:.2f}")

    # ---------------------------------------------------------
    # 🏆 [3단계] 최종 결론
    # ---------------------------------------------------------
    print(f"\n{'='*60}")
    print(f"📋 [AI 최종 리포트]")
    
    if is_s_class:
        print(f"   👑 등급: S-CLASS (강력 매수)")
        print(f"   💰 비중: 자산의 30% ")
        print(f"   💡 행동: 오늘 장 열리면 ${target_low:.2f} 에 매수 대기하세요.")
    elif current_price > ma200 and "추세 이탈" not in reasons:
        # 추세는 좋은데 PEG나 RSI 같은 게 조금 걸릴 때 -> A급
        print(f"   🥈 등급: A-CLASS (관심/분산)")
        print(f"   💰 비중: 자산의 10% ")
        print(f"   ⚠️ 주의: {', '.join(reasons)}")
        print(f"   💡 행동: 눌림목(${target_low:.2f}) 줄 때만 소액 진입.")
    else:
        print(f"   🗑️ 등급: F-CLASS (매수 금지)")
        print(f"   ❌ 이유: {', '.join(reasons)} ")
        print(f"   💡 행동: 관망하거나 200일선 회복 시까지 대기.")
    print(f"{'='*60}\n")

# --- 실행 예시 ---
# 보고 싶은 종목 티커를 넣으세요 (미국: AAPL, NVDA / 한국: 000660.KS)
if __name__ == "__main__":
    analyze_stock_logic("TSLA", benchmark_ticker="^IXIC") # 엔비디아 vs 나스닥
    # analyze_stock_logic("000660.KS", benchmark_ticker="^KS11") # 하이닉스 vs 코스피

    ## English Version ##
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

def analyze_stock_logic(ticker, benchmark_ticker="^IXIC"): # Default: Nasdaq
    print(f"\n{'='*60}")
    print(f"🚀 [AI ANALYSIS START] Ticker: {ticker}")
    print(f"{'='*60}")

    # 1. Fetch Real Data (yfinance)
    try:
        stock = yf.Ticker(ticker)
        # History for technicals (1 year)
        hist = stock.history(period="1y")
        
        # Benchmark history for Gap calculation
        bench = yf.Ticker(benchmark_ticker)
        bench_hist = bench.history(period="1y")
        
        # VIX Data (Market Shield)
        vix = yf.Ticker("^VIX")
        vix_hist = vix.history(period="5d")
        current_vix = vix_hist['Close'].iloc[-1]
        
        # Financials (PEG, Growth)
        info = stock.info
        
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        return

    # --- Data Pre-processing ---
    if len(hist) < 200:
        print("❌ Not enough data (less than 200 days). Cannot analyze.")
        return

    current_price = hist['Close'].iloc[-1]
    
    # MA200 (200-day Moving Average)
    ma200 = hist['Close'].rolling(window=200).mean().iloc[-1]
    
    # RSI (14-day)
    delta = hist['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs)).iloc[-1]
    
    # Gap (20-day Return Disparity)
    stock_ret_20 = hist['Close'].pct_change(20).iloc[-1]
    bench_ret_20 = bench_hist['Close'].pct_change(20).iloc[-1]
    gap = bench_ret_20 - stock_ret_20 # Positive if benchmark outperformed stock
    
    # PEG & Growth (Handle missing data)
    peg = info.get('pegRatio', None)
    rev_growth = info.get('revenueGrowth', 0)

    # ---------------------------------------------------------
    # 🕵️‍♂️ [Phase 1] Logical Filtering (The 6 Checkpoints)
    # ---------------------------------------------------------
    
    is_s_class = True
    reasons = [] # Store reasons for failure
    
    # 1. 🛡️ SHIELD (VIX Filter)
    print(f"\n1️⃣ [SHIELD] Market Status (VIX)")
    print(f"   - Current VIX: {current_vix:.2f} (Threshold: < 30)")
    if current_vix >= 30:
        print("   -> 🚨 FAIL: Market Panic detected. STOP TRADING (Cash 100%).")
        is_s_class = False
        reasons.append("Market Risk (VIX > 30)")
    else:
        print("   -> ✅ PASS: Market is stable.")

    if is_s_class: # Only proceed if Market is safe
        
        # 2. 🧠 BRAIN (Trend Filter) - MA200
        print(f"\n2️⃣ [TREND] 200-Day SMA Check")
        print(f"   - Current Price: ${current_price:.2f}")
        print(f"   - 200-Day SMA:   ${ma200:.2f}")
        
        if current_price < ma200:
            print("   -> ❌ FAIL: Downtrend (Below MA200). Do not buy.")
            is_s_class = False
            reasons.append("Broken Trend (Below MA200)")
        else:
            print("   -> ✅ PASS: Uptrend (Above MA200).")

        # 3. 📊 VALUE (Fundamental) - PEG & Growth
        print(f"\n3️⃣ [VALUE] Fundamental Check (PEG & Growth)")
        if peg is not None:
            print(f"   - PEG Ratio: {peg} (Threshold: < 1.5)")
        else:
            print(f"   - PEG Ratio: N/A (Assume Expensive)")
            peg = 99 
            
        print(f"   - Revenue Growth: {rev_growth*100:.1f}%")

        # Logic: PEG < 1.5 (Pass) OR Growth > 30% (Exception Pass)
        if peg > 1.5 and rev_growth < 0.30:
            print("   -> ⚠️ WARNING: Expensive relative to growth.")
            is_s_class = False 
            reasons.append("Overvalued (High PEG)")
        elif peg > 1.5 and rev_growth >= 0.30:
            print("   -> 👑 PASS (Exception): High PEG justified by hyper-growth (>30%).")
        else:
            print("   -> ✅ PASS: Undervalued relative to growth.")

        # 4. ⚡ TIMING (Gap & RSI)
        print(f"\n4️⃣ [TIMING] Overheat & Gap Check")
        print(f"   - RSI(14): {rsi:.1f} (Threshold: < 70)")
        print(f"   - Gap Ratio: {gap*100:.1f}% (Threshold: > 5% for Buy Dip)")
        
        if rsi >= 70:
            print("   -> ❌ FAIL: Overheated (RSI > 70). Wait for cool down.")
            is_s_class = False
            reasons.append("Overheated (RSI > 70)")
        elif gap > 0.05:
            print("   -> ⭐ BONUS: Stock lagging market by >5%. (Buying Opportunity/Dip)")
        else:
            print("   -> ✅ PASS: Healthy range.")

    # ---------------------------------------------------------
    # 🎯 [Phase 2] DeMark Sniper (Daily Price Target)
    # ---------------------------------------------------------
    print(f"\n5️⃣ [SNIPER] Daily Price Targets (DeMark Indicator)")
    
    # Yesterday's Data
    yesterday = hist.iloc[-2]
    y_open = yesterday['Open']
    y_high = yesterday['High']
    y_low = yesterday['Low']
    y_close = yesterday['Close']
    
    # DeMark Pivot Calculation
    if y_close > y_open: # Up Day (Bullish) -> High weighted
        pivot = (y_high * 2 + y_low + y_close) / 4
        candle_type = "🔺 Up Day (Bullish)"
    elif y_close < y_open: # Down Day (Bearish) -> Low weighted
        pivot = (y_high + y_low * 2 + y_close) / 4
        candle_type = "🟦 Down Day (Bearish)"
    else: # Doji
        pivot = (y_high + y_low + y_close * 2) / 4
        candle_type = "➖ Doji (Neutral)"
        
    target_high = pivot * 2 - y_low  # Resistance (Sell Target)
    target_low = pivot * 2 - y_high  # Support (Ideal Buy Price)

    print(f"   - Yesterday's Candle: {candle_type}")
    print(f"   - 🎯 Target Buy Price (Support):    ${target_low:.2f}")
    print(f"   - 🎯 Target Sell Price (Resistance): ${target_high:.2f}")

    # ---------------------------------------------------------
    # 🏆 [Phase 3] Final Report
    # ---------------------------------------------------------
    print(f"\n{'='*60}")
    print(f"📋 [FINAL AI REPORT]")
    
    if is_s_class:
        print(f"   👑 RATING:     S-CLASS (Strong Buy)")
        print(f"   💰 ALLOCATION: 30% of Portfolio")
        print(f"   💡 ACTION:     Place limit buy order at ${target_low:.2f}")
    elif current_price > ma200 and "Broken Trend (Below MA200)" not in reasons:
        # Trend is okay, but failed PEG or RSI -> A Class
        print(f"   🥈 RATING:     A-CLASS (Watchlist/Stable)")
        print(f"   💰 ALLOCATION: 10% of Portfolio")
        print(f"   ⚠️ CAUTION:    {', '.join(reasons)}")
        print(f"   💡 ACTION:     Small buy ONLY at dip (${target_low:.2f})")
    else:
        print(f"   🗑️ RATING:     F-CLASS (Do Not Buy)")
        print(f"   ❌ REASONS:    {', '.join(reasons)}")
        print(f"   💡 ACTION:     Stay Cash / Wait for MA200 recovery.")
    print(f"{'='*60}\n")

# --- Execution Example ---
if __name__ == "__main__":
    # You can change the ticker here (e.g., "TSLA", "AAPL", "005930.KS")
    analyze_stock_logic("TSLA", benchmark_ticker="^IXIC")