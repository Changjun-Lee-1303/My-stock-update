
import { GoogleGenAI } from "@google/genai";
import { AIResponse, AppSettings } from "../types";

const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });

const getSystemInstruction = (settings: AppSettings) => `
Role: You are the 'Smart Asset Allocation' AI Judge.
Your architecture consists of three distinct phases to simulate a "Python-based Algo-Trading System".

**⚠️ DATA SOURCE RULE: STRICTLY USE YAHOO FINANCE (finance.yahoo.com)**
All numeric data (Price, PE, Growth, RSI) must be sourced from Yahoo Finance.

**PHASE 1: DATA MINER (Scope: Top 300 Market Cap Stocks)**
- **Target:** Top 100 NASDAQ, Top 100 KOSPI, Top 100 KOSDAQ.
- **Action:** Use 'googleSearch' to find data specifically on Yahoo Finance.
- **Data Gathering:** For selected candidates, find LATEST numeric data from Yahoo Finance:
  1. **Current Data:** Current Price, Today's Open Price.
  2. **Previous Day Data:** Prev Open, Prev High, Prev Low, Prev Close.
  3. **Technical:** MA200, RSI (14-Day).
  4. **Fundamental:** Forward PE, Earnings Growth Estimates, Revenue Growth (YoY).
  5. **Performance:** 1-Month Sector Return %, 1-Month Stock Return %.
  6. **Indices:** Current KOSPI, KOSDAQ, NASDAQ, S&P 500 values.

**PHASE 2: THE CALCULATOR (Simulate Python Code)**
You must mathematically calculate the derived metrics. Do not guess.

1. **Calculate PEG:** (Forward PE) / (Earnings Growth %). 
   - *Example:* PE 30 / Growth 20 = 1.5. (Invalid if Growth < 0).

2. **Calculate Gap:** (Sector 1M Return) - (Stock 1M Return).

3. **Calculate DeMark Pivot Targets (Specific Python Logic):**
   *Variables: P_Open (Prev Open), P_High (Prev High), P_Low (Prev Low), P_Close (Prev Close).*
   - **Step A: Calculate 'Pivot Base'**
     - IF P_Close > P_Open (Bullish Candle): Base = (P_High * 2 + P_Low + P_Close) / 4
     - IF P_Close < P_Open (Bearish Candle): Base = (P_High + P_Low * 2 + P_Close) / 4
     - ELSE (Doji): Base = (P_High + P_Low + P_Close * 2) / 4
   - **Step B: Calculate Targets**
     - DeMark Sell Limit (Target High) = (Base * 2) - P_Low
     - DeMark Buy Limit (Target Low) = (Base * 2) - P_High

**PHASE 3: THE JUDGE (Strict Logic)**
Apply filters to the Calculated Data from Phase 2.

**🛡️ Shield Filter:**
- If VIX >= ${settings.vixThreshold}, Market Status = "Halted".

**🧠 Brain Filter:**
1. **PEG Check:** Pass if PEG < ${settings.pegThreshold} (OR PEG < 3.0 if Revenue Growth >= 30%).
2. **Trend Check:** Price > MA200.
3. **Gap Check:** Gap > ${settings.gapThreshold}%.
4. **RSI Check:** RSI < ${settings.rsiThreshold}.
5. **Growth Check:** Revenue Growth > 0%.

**🎯 DeMark Strategy Check:**
- **Gap Up Warning:** If Today's Open > DeMark Sell Limit -> "Overheated/Gap Up".
- **Bargain Opportunity:** If Today's Open < DeMark Buy Limit -> "Bargain Buy/Gap Down".

**🏆 Grading System:**
- **S Grade:** Passes ALL Brain Filters.
- **A Grade:** Good Fundamentals but fails Gap OR Good Technicals but high PEG.
- **F Grade:** Fails Trend or Revenue Growth.

**Output format:** Return ONLY valid JSON. No Markdown.
`;

export const analyzeTickerWithGemini = async (
  equity: number,
  vix: number,
  tickers: string[],
  settings: AppSettings,
  context?: string // 'RECOMMEND' | 'ANALYZE'
): Promise<AIResponse> => {
  try {
    let prompt = `
[CONTEXT]
User Total Equity: ${equity.toLocaleString()} KRW
Current VIX: ${vix} (User Provided)

[INSTRUCTION]
`;

    if (context === 'RECOMMEND') {
      prompt += `
1. **(Phase 1 - Broad Market Scan)**:
   - Act as an Algo-Trading Bot.
   - Scan the **Top 100 Market Cap companies** in **NASDAQ**, **KOSPI**, and **KOSDAQ**.
   - Identify the **Top 20 candidates** that look like "S-Class" (High Growth, Uptrend, Fair Value) or "A-Class" (Stable).
   - **MANDATORY:** Include a mix of US Tech (NVDA, TSLA, PLTR, etc.) and Korean Leaders (Samsung, SK Hynix, EcoPro, etc.).
   - **DATA SOURCE:** Prioritize "site:finance.yahoo.com" for all data.

2. **(Phase 2 - Code Simulation)**:
   - Search for specific Yahoo Finance data (including Previous Day OHLC) for these 20 candidates.
   - **CALCULATE** PEG, Gap, and **DeMark Targets** for each.

3. **(Phase 3 - Grading)**:
   - Grade them S, A, or F based on your calculations.
   - Return the JSON with 'market_indices' and 'analysis_result'.
   - **S-Grade Amount:** ${(equity * 0.3).toLocaleString()} KRW.
   - **A-Grade Amount:** ${(equity * 0.1).toLocaleString()} KRW.
   - STRICTLY JSON ONLY. No markdown formatting.
`;
    } else {
      prompt += `
1. **(Phase 1)** Search for REAL-TIME data (including Prev OHLC) on **Yahoo Finance** for: [${tickers.join(', ')}].
2. **(Phase 2)** Calculate PEG, Gap, and **DeMark Targets**.
3. **(Phase 3)** Grade each stock (S/A/F).
4. Return JSON with 'analysis_result'.
`;
    }

    // Using gemini-3-pro-preview for complex reasoning and "Calculation" simulation
    const response = await ai.models.generateContent({
      model: 'gemini-3-pro-preview',
      contents: prompt,
      config: {
        systemInstruction: getSystemInstruction(settings),
        tools: [{ googleSearch: {} }],
      }
    });

    if (response.text) {
      let cleanJson = response.text.replace(/```json|```/g, '').trim();
      
      const firstBrace = cleanJson.indexOf('{');
      const lastBrace = cleanJson.lastIndexOf('}');
      
      if (firstBrace !== -1 && lastBrace !== -1) {
        cleanJson = cleanJson.substring(firstBrace, lastBrace + 1);
      }

      const parsed = JSON.parse(cleanJson);

      if (!parsed.analysis_result || !Array.isArray(parsed.analysis_result)) {
        parsed.analysis_result = [];
      }

      parsed.analysis_result = parsed.analysis_result.filter((item: any) => 
        item && 
        item.ticker && 
        item.used_data && 
        typeof item.used_data.price === 'number'
      );

      return parsed as AIResponse;
    } else {
      throw new Error("No response text received from Gemini.");
    }
  } catch (error: any) {
    console.error("Gemini Analysis Error:", error);
    
    const errStr = JSON.stringify(error);
    const isQuotaError = 
        errStr.includes('429') || 
        errStr.includes('quota') || 
        errStr.includes('RESOURCE_EXHAUSTED') ||
        error.message?.includes('quota') || 
        error.message?.includes('429');

    if (isQuotaError) {
        return {
            market_status: "Quota Exceeded",
            vix_used: vix,
            market_indices: [],
            analysis_result: []
        };
    }

    return {
      market_status: "Error/Offline",
      vix_used: vix,
      market_indices: [],
      analysis_result: []
    };
  }
};
