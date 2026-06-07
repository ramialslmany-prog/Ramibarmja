import pandas as pd
from typing import Dict

from analysis.indicators import run_indicators
from analysis.market_structure import (
    find_swing_highs_lows,
    classify_market_structure,
    detect_bos,
    detect_choch,
    classify_trend_simple,
)
from analysis.smc import analyze_smc


def analyze_single_timeframe(df: pd.DataFrame, timeframe: str) -> Dict:
    if df is None or len(df) < 50:
        return {"timeframe": timeframe, "valid": False, "trend": "UNKNOWN"}

    indicators = run_indicators(df)
    highs, lows = find_swing_highs_lows(df)
    structure = classify_market_structure(highs, lows)
    bos = detect_bos(df, highs, lows)
    choch = detect_choch(df, structure, highs, lows)
    smc = analyze_smc(df)
    trend = classify_trend_simple(df)

    return {
        "timeframe": timeframe,
        "valid": True,
        "trend": trend,
        "structure": structure,
        "bos": bos,
        "choch": choch,
        "smc": smc,
        "indicators": indicators,
        "highs": highs,
        "lows": lows,
        "current_price": float(df["close"].iloc[-1]),
        "current_high": float(df["high"].iloc[-1]),
        "current_low": float(df["low"].iloc[-1]),
    }


_TF_DISPLAY = {"5m": "5m", "15m": "15m", "1h": "1h", "4h": "4h", "1d": "daily"}


def run_multi_timeframe_analysis(data: Dict[str, pd.DataFrame]) -> Dict[str, Dict]:
    analyses = {}
    for tf_key, df in data.items():
        display = _TF_DISPLAY.get(tf_key, tf_key)
        analyses[display] = analyze_single_timeframe(df, display)
    return analyses


def check_timeframe_alignment(analyses: Dict[str, Dict]) -> Dict:
    priority = ["daily", "4h", "1h", "15m", "5m"]
    weights = {"daily": 3, "4h": 2, "1h": 1, "15m": 1, "5m": 1}
    scores = {"UPTREND": 2, "MILD_UPTREND": 1, "RANGING": 0, "MILD_DOWNTREND": -1, "DOWNTREND": -2, "UNKNOWN": 0}

    bull_total = 0
    bear_total = 0
    alignments = {}

    for tf in priority:
        if tf in analyses and analyses[tf].get("valid"):
            trend = analyses[tf].get("trend", "UNKNOWN")
            score = scores.get(trend, 0)
            w = weights.get(tf, 1)
            if score > 0:
                bull_total += score * w
            elif score < 0:
                bear_total += abs(score) * w
            alignments[tf] = trend

    denom = bull_total + bear_total + 1
    if bull_total > bear_total * 1.5:
        bias = "BULLISH"
        strength = min(100, int(bull_total / denom * 100))
    elif bear_total > bull_total * 1.5:
        bias = "BEARISH"
        strength = min(100, int(bear_total / denom * 100))
    else:
        bias = "NEUTRAL"
        strength = 50

    return {
        "overall_bias": bias,
        "strength": strength,
        "timeframe_alignment": alignments,
        "bullish_score": bull_total,
        "bearish_score": bear_total,
        "aligned": bull_total > 5 or bear_total > 5,
    }
