from typing import Dict, Any, Optional
from .genai_adapter import GenAIAdapter, make_recommendation_prompt
from .strategy import evaluate_ticker
from .data_fetcher import get_vix
from .genai_adapter import analyze_with_gemini
import re


def ai_allocate_amount(evaluation: Dict[str, Any], total_cash: float, adapter: Optional[GenAIAdapter] = None) -> float:
    """Return allocation amount (absolute) for a single ticker based on evaluation.

    If adapter is provided and configured, ask the model for a recommended percentage.
    Otherwise fallback to heuristic mapping: S->30%, A->10%, F->0% with small modifiers.
    """
    grade = evaluation.get('grade', 'F')
    indicators = evaluation.get('indicators', {})

    # Heuristic base
    base_pct = 0.0
    if grade == 'S':
        base_pct = 0.30
    elif grade == 'A':
        base_pct = 0.10
    else:
        base_pct = 0.0

    # small heuristic modifiers
    mod = 0.0
    gap = indicators.get('gap_pct')
    if gap is not None:
        try:
            if float(gap) >= 10.0:
                mod += 0.05
            elif float(gap) >= 5.0:
                mod += 0.02
        except Exception:
            pass
    rsi = indicators.get('rsi14')
    try:
        if rsi is not None and float(rsi) < 50:
            mod += 0.02
    except Exception:
        pass

    pct = min(base_pct + mod, 0.5)

    # If adapter available, try to get a model-suggested percent
    if adapter is not None and adapter.is_configured():
        prompt = make_recommendation_prompt(evaluation.get('ticker', 'TICKER'), indicators)
        try:
            txt = adapter.generate_text(prompt)
            # try to extract a percentage number from the model output
            import re
            m = re.search(r"(\d{1,2}(?:\.\d+)?)\s*%", txt)
            if m:
                pct_val = float(m.group(1)) / 100.0
                pct = max(0.0, min(pct_val, 0.9))
        except Exception:
            # fall back to heuristic
            pass

    return float(total_cash * pct)


def ai_backtest(tickers, start_cash: float = 10000000) -> Dict[str, Any]:
    """Run a simple AI-allocation backtest: determine allocation per ticker then reuse backtester logic.

    This is a convenience wrapper that imports the enhanced backtest function from backtester.
    """
    from .backtester import simple_backtest
    adapter = GenAIAdapter()

    # If adapter configured, try to ask Gemini for recommended allocations in batch
    allocation_map = {}
    if adapter.is_configured():
        try:
            v = get_vix() or 0
            settings = {
                'vixThreshold': 30.0,
                'pegThreshold': 1.5,
                'gapThreshold': 5.0,
                'rsiThreshold': 70.0,
            }
            # request recommendation for up to first 100 tickers
            parsed = analyze_with_gemini(adapter, equity=start_cash, vix=v, tickers=tickers[:100], settings=settings, context='RECOMMEND')
            results = parsed.get('analysis_result', []) if isinstance(parsed, dict) else []
            # try to parse recommended allocations per ticker
            for item in results:
                tkr = item.get('ticker') or item.get('symbol')
                amt = 0.0
                # possible fields: recommended_amount, recommended_percent, recommended_allocation
                if not tkr:
                    continue
                if 'recommended_amount' in item:
                    try:
                        amt = float(item.get('recommended_amount') or 0.0)
                    except Exception:
                        amt = 0.0
                elif 'recommended_percent' in item:
                    try:
                        pct = float(item.get('recommended_percent') or 0.0)
                        amt = (pct / 100.0) * float(start_cash)
                    except Exception:
                        amt = 0.0
                else:
                    # fallback: search in textual fields
                    text_fields = []
                    if isinstance(item.get('explanation'), str):
                        text_fields.append(item.get('explanation'))
                    if isinstance(item.get('notes'), str):
                        text_fields.append(item.get('notes'))
                    combined = '\n'.join(text_fields)
                    m = re.search(r"(\d{1,3}(?:\.\d+)?)\s*%", combined)
                    if m:
                        try:
                            pct = float(m.group(1))
                            amt = (pct / 100.0) * float(start_cash)
                        except Exception:
                            amt = 0.0

                allocation_map[tkr.upper()] = max(0.0, amt)
        except Exception:
            allocation_map = {}

    # If allocation_map empty, fallback to local heuristic allocations
    if not allocation_map:
        for t in tickers:
            try:
                ev = evaluate_ticker(t, sector_ma20=None, vix=None)
                amt = ai_allocate_amount(ev, start_cash, adapter=adapter)
                allocation_map[t] = amt
            except Exception:
                allocation_map[t] = 0.0

    # Call backtester with allocation_map
    return simple_backtest(tickers, start_cash=start_cash, allocation_map=allocation_map)
