import os
import json
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class GenAIAdapter:
    def __init__(self, api_key: Optional[str] = None, model: str = 'models/text-bison-001'):
        self.api_key = api_key or os.environ.get('GEMINI_API_KEY')
        self.model = model
        self.client = None
        # Try to import google generative ai client if available
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.client = genai
        except Exception as e:
            logger.info('google.generativeai not available or failed to configure: %s', e)

    def is_configured(self) -> bool:
        return bool(self.api_key and self.client)

    def _generate_raw(self, prompt: str, max_output_tokens: int = 1024, system_instruction: Optional[str] = None) -> str:
        """Internal: call the configured gen ai client in a defensive way and return text."""
        if not self.client:
            raise RuntimeError('Generative AI client not configured. Install google-generative-ai and set GEMINI_API_KEY')

        try:
            # Prefer generate_text if available
            if hasattr(self.client, 'generate_text'):
                # Some client versions accept a 'prompt' string, others accept more structured params.
                params = {
                    'model': self.model,
                    'prompt': prompt,
                    'max_output_tokens': max_output_tokens,
                }
                # Some clients support a system instruction via 'system_instruction' or similar; include if supported.
                if system_instruction:
                    params['system_instruction'] = system_instruction

                resp = self.client.generate_text(**params)
                # Try common response shapes
                if isinstance(resp, dict):
                    return resp.get('output', '') or resp.get('text', '') or json.dumps(resp)
                return getattr(resp, 'text', str(resp))

            # fallback: try models.generate or models.generate_content
            if hasattr(self.client, 'models') and hasattr(self.client.models, 'generate'):
                resp = self.client.models.generate(model=self.model, prompt=prompt)
                return getattr(resp, 'text', str(resp))

            # last resort: call str()
            return str(self.client)
        except Exception as e:
            logger.exception('GenAI generation failed: %s', e)
            raise


def get_system_instruction(settings: Dict[str, Any]) -> str:
    """Port of the TypeScript getSystemInstruction(settings) used in the original AI Studio app.

    Expects settings dict with keys: vixThreshold, pegThreshold, gapThreshold, rsiThreshold
    """
    return f"""
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
- If VIX >= {settings.get('vixThreshold', 30)}, Market Status = "Halted".

**🧠 Brain Filter:**
1. **PEG Check:** Pass if PEG < {settings.get('pegThreshold', 1.5)} (OR PEG < 3.0 if Revenue Growth >= 30%).
2. **Trend Check:** Price > MA200.
3. **Gap Check:** Gap > {settings.get('gapThreshold', 5)}%.
4. **RSI Check:** RSI < {settings.get('rsiThreshold', 70)}.
5. **Growth Check:** Revenue Growth > 0%.

**🎯 DeMark Strategy Check:**
- **Gap Up Warning:** If Today's Open > DeMark Sell Limit -> "Overheated/Gap Up".
- **Bargain Opportunity:** If Today's Open < DeMark Buy Limit -> "Bargain Buy/Gap Down".

**🏆 Grading System:**
- **S Grade:** Passes ALL Brain Filters.
- **A Grade:** Good Fundamentals but fails Gap OR Good Technicals but high PEG.
- **F Grade:** Fails Trend or Revenue Growth.

**Output format:** Return ONLY valid JSON. No Markdown.
"""


def analyze_with_gemini(adapter: GenAIAdapter,
                        equity: int,
                        vix: float,
                        tickers: List[str],
                        settings: Dict[str, Any],
                        context: Optional[str] = None) -> Dict[str, Any]:
    """Replicates the TypeScript analyzeTickerWithGemini behavior.

    Builds a prompt according to the 3-phase workflow and calls the GenAI client. Parses JSON and returns the dict.
    This function is defensive: if the client is not available or parsing fails, it returns an error-shaped dict.
    """
    try:
        system_instruction = get_system_instruction(settings)

        prompt = []
        prompt.append(f"[CONTEXT]\nUser Total Equity: {equity} KRW\nCurrent VIX: {vix} (User Provided)\n")
        prompt.append("[INSTRUCTION]\n")

        if context == 'RECOMMEND':
            prompt.append(
                """
1. (Phase 1 - Broad Market Scan):
   - Act as an Algo-Trading Bot.
   - Scan the Top 100 Market Cap companies in NASDAQ, KOSPI, and KOSDAQ.
   - Identify the Top 20 candidates that look like S-Class or A-Class.
   - MANDATORY: Include a mix of US Tech and Korean Leaders.
   - DATA SOURCE: Prioritize site:finance.yahoo.com for all data.

2. (Phase 2 - Code Simulation):
   - Search for specific Yahoo Finance data (including Previous Day OHLC) for these 20 candidates.
   - CALCULATE PEG, Gap, and DeMark Targets for each.

3. (Phase 3 - Grading):
   - Grade them S, A, or F based on your calculations.
   - Return the JSON with 'market_indices' and 'analysis_result'.
   - S-Grade Amount: {int(equity * 0.3)} KRW.
   - A-Grade Amount: {int(equity * 0.1)} KRW.
STRICTLY JSON ONLY. No markdown formatting.
"""
            )
        else:
            prompt.append(
                f"1. (Phase 1) Search for REAL-TIME data on Yahoo Finance for: [{', '.join(tickers)}].\n"
                "2. (Phase 2) Calculate PEG, Gap, and DeMark Targets.\n"
                "3. (Phase 3) Grade each stock (S/A/F).\n"
                "4. Return JSON with 'analysis_result'.\n"
            )

        full_prompt = "\n".join(prompt)

        raw = adapter._generate_raw(full_prompt, max_output_tokens=2048, system_instruction=system_instruction)

        text = raw or ''
        clean = text.replace('```json', '').replace('```', '').strip()
        first = clean.find('{')
        last = clean.rfind('}')
        if first != -1 and last != -1:
            clean = clean[first:last+1]

        parsed = json.loads(clean)

        # sanitize
        if 'analysis_result' not in parsed or not isinstance(parsed['analysis_result'], list):
            parsed['analysis_result'] = []

        filtered = []
        for item in parsed['analysis_result']:
            try:
                if item and item.get('ticker') and isinstance(item.get('used_data', {}).get('price'), (int, float)):
                    filtered.append(item)
            except Exception:
                continue

        parsed['analysis_result'] = filtered
        return parsed

    except Exception as e:
        logger.exception('Gemini Analysis Error: %s', e)
        err_str = str(e)
        is_quota = '429' in err_str or 'quota' in err_str.lower() or 'RESOURCE_EXHAUSTED' in err_str
        if is_quota:
            return {
                'market_status': 'Quota Exceeded',
                'vix_used': vix,
                'market_indices': [],
                'analysis_result': []
            }
        return {
            'market_status': 'Error/Offline',
            'vix_used': vix,
            'market_indices': [],
            'analysis_result': []
        }


def parse_allocations_from_analysis(parsed: Dict[str, Any], equity: int) -> Dict[str, float]:
    """Given a parsed Gemini analysis (parsed JSON), extract recommended allocations.

    Supports these shapes per item in parsed['analysis_result']:
      - item['recommended_amount'] (absolute number)
      - item['recommended_percent'] (0-100 or 0-1 scale)
      - item['allocation'] = {'percent': ..} or {'amount': ..}

    Returns a mapping {ticker: amount_in_currency}. Invalid/missing values are skipped.
    """
    out = {}
    if not parsed or 'analysis_result' not in parsed:
        return out
    rows = parsed.get('analysis_result') or []
    total_assigned = 0.0
    for item in rows:
        try:
            ticker = (item.get('ticker') or '').upper()
            if not ticker:
                continue
            amt = None
            if 'recommended_amount' in item and item.get('recommended_amount') is not None:
                amt = float(item.get('recommended_amount'))
            elif 'recommended_percent' in item and item.get('recommended_percent') is not None:
                p = float(item.get('recommended_percent'))
                # normalize percent in 0-1
                if p > 1:
                    p = p / 100.0
                amt = p * equity
            elif 'allocation' in item and isinstance(item.get('allocation'), dict):
                a = item.get('allocation')
                if 'amount' in a and a.get('amount') is not None:
                    amt = float(a.get('amount'))
                elif 'percent' in a and a.get('percent') is not None:
                    p = float(a.get('percent'))
                    if p > 1:
                        p = p / 100.0
                    amt = p * equity

            if amt is None or not (amt > 0):
                continue
            out[ticker] = amt
            total_assigned += amt
        except Exception:
            continue

    # If allocations exceed equity, normalize proportionally
    if total_assigned > 0 and total_assigned > equity:
        factor = equity / total_assigned
        for k in list(out.keys()):
            out[k] = out[k] * factor

    return out


def simulated_equal_allocations(tickers: List[str], equity: int) -> Dict[str, float]:
    """Simple fallback: equal-weight allocations across tickers (non-zero)."""
    out = {}
    if not tickers:
        return out
    valid = [t for t in tickers if t]
    n = len(valid)
    if n == 0:
        return out
    per = equity / n
    for t in valid:
        out[t.upper()] = float(per)
    return out


def make_recommendation_prompt(ticker: str, indicators: dict) -> str:
    """Builds a prompt for the AI model to provide buy recommendation and sizing.

    Example: include grade, demark support, key indicators.
    Returns Korean instruction text.
    """
    parts = [f"티커: {ticker}"]
    for k, v in (indicators or {}).items():
        parts.append(f"{k}: {v}")
    parts.append("위의 지표를 바탕으로 이 종목의 등급(S/A/F)과 권장 매수비중(자산비율)을 한국어로 간결하게 제시하세요. 또한 디마크 저가 근처에서의 주문 권장 문구를 제공하세요.")
    return "\n".join(parts)


if __name__ == '__main__':
    # quick local test (no-op) - prints guidance
    print('GenAIAdapter module loaded. Set GEMINI_API_KEY to enable calls.')
