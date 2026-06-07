from typing import Dict, Optional, Tuple

from config import SIGNAL_FILTERS


# ---------------------------------------------------------------------------
# Direction determination
# ---------------------------------------------------------------------------

def determine_signal_direction(alignment: Dict, htf: Dict, ltf: Dict) -> str:
    bias = alignment.get("overall_bias", "NEUTRAL")
    if not alignment.get("aligned"):
        return "HOLD"

    htf_trend = htf.get("trend", "UNKNOWN") if htf else "UNKNOWN"

    if bias == "BULLISH" and "UPTREND" in htf_trend:
        return "BUY"
    elif bias == "BEARISH" and "DOWNTREND" in htf_trend:
        return "SELL"
    return "HOLD"


# ---------------------------------------------------------------------------
# Confidence scoring (0–100)
# ---------------------------------------------------------------------------

def calculate_confidence(alignment: Dict, htf: Dict, ltf: Dict, direction: str) -> int:
    score = 45

    # MTF alignment (max +20)
    strength = alignment.get("strength", 50)
    tf_align = alignment.get("timeframe_alignment", {})
    aligned_tfs = sum(
        1 for tf, tr in tf_align.items()
        if (direction == "BUY" and "UPTREND" in tr)
        or (direction == "SELL" and "DOWNTREND" in tr)
    )
    score += min(20, aligned_tfs * 5)

    ind = htf.get("indicators", {}) if htf else {}
    smc = htf.get("smc", {}) if htf else {}
    ob = smc.get("order_blocks", {})
    fvg = smc.get("fvg", {})
    liq = smc.get("liquidity", {})
    bos = htf.get("bos", {}) if htf else {}
    choch_ltf = ltf.get("choch", {}) if ltf else {}

    # Order Block confluence (+10)
    if direction == "BUY" and ob.get("at_bullish_ob"):
        score += 10
    elif direction == "SELL" and ob.get("at_bearish_ob"):
        score += 10

    # FVG support (+5)
    if direction == "BUY" and fvg.get("has_bullish_fvg_below"):
        score += 5
    elif direction == "SELL" and fvg.get("has_bearish_fvg_above"):
        score += 5

    # Liquidity sweep confirmation (+8)
    if direction == "BUY" and liq.get("swept_sell_side"):
        score += 8
    elif direction == "SELL" and liq.get("swept_buy_side"):
        score += 8

    # Volume (+8 / -8)
    vol = ind.get("volume_strength", "NORMAL")
    if vol in ("HIGH", "VERY_HIGH"):
        score += 8
    elif vol == "LOW":
        score -= 8

    # MACD alignment (+5)
    macd_bias = ind.get("macd_bias", "NEUTRAL")
    if direction == "BUY" and macd_bias == "BULLISH":
        score += 5
    elif direction == "SELL" and macd_bias == "BEARISH":
        score += 5
    elif macd_bias not in ("NEUTRAL",):
        score -= 3

    # RSI zone (+5 / -8)
    rsi = ind.get("rsi", 50)
    if direction == "BUY":
        if 30 < rsi < 55:
            score += 5
        elif rsi >= 70:
            score -= 8
    elif direction == "SELL":
        if 45 < rsi < 70:
            score += 5
        elif rsi <= 30:
            score -= 8

    # BOS confirmation (+5)
    if direction == "BUY" and bos.get("type") == "BULLISH_BOS":
        score += 5
    elif direction == "SELL" and bos.get("type") == "BEARISH_BOS":
        score += 5

    # CHOCH on LTF (+4)
    if direction == "BUY" and choch_ltf.get("type") == "BULLISH_CHOCH":
        score += 4
    elif direction == "SELL" and choch_ltf.get("type") == "BEARISH_CHOCH":
        score += 4

    # Opposing structure penalty (-10)
    struct = htf.get("structure", {}) if htf else {}
    if direction == "BUY" and "DOWNTREND" in struct.get("trend", ""):
        score -= 10
    elif direction == "SELL" and "UPTREND" in struct.get("trend", ""):
        score -= 10

    return max(0, min(100, score))


# ---------------------------------------------------------------------------
# Signal filtering
# ---------------------------------------------------------------------------

def apply_filters(
    direction: str,
    confidence: int,
    rr: float,
    alignment: Dict,
    indicators: Dict,
) -> Tuple[str, str]:
    if direction == "HOLD":
        return "HOLD", "No valid directional bias"

    min_conf = SIGNAL_FILTERS.get("min_confidence", 85)
    min_rr = SIGNAL_FILTERS.get("min_rr_ratio", 2.0)

    if confidence < min_conf:
        return "HOLD", f"Confidence {confidence}% below threshold {min_conf}%"
    if rr < min_rr:
        return "HOLD", f"R:R {rr:.1f} below minimum {min_rr}"
    if indicators.get("volume_strength") == "LOW":
        return "HOLD", "Volume too low for institutional confirmation"
    if not alignment.get("aligned"):
        return "HOLD", "Insufficient multi-timeframe alignment"

    return direction, "PASSED_ALL_FILTERS"


# ---------------------------------------------------------------------------
# Setup type
# ---------------------------------------------------------------------------

def determine_setup_type(confidence: int, rr: float, htf_trend: str) -> str:
    if confidence >= 90 and rr >= 3.0:
        return "SWING"
    elif confidence >= 87:
        return "INTRADAY"
    return "SCALP"


# ---------------------------------------------------------------------------
# Risk classification
# ---------------------------------------------------------------------------

def classify_risk(atr_pct: float, funding_rate: Optional[float]) -> str:
    rs = 0
    if atr_pct > 5:
        rs += 3
    elif atr_pct > 3:
        rs += 2
    elif atr_pct > 1.5:
        rs += 1
    if funding_rate is not None and abs(funding_rate) > 0.001:
        rs += 2
    return "HIGH" if rs >= 4 else "MEDIUM" if rs >= 2 else "LOW"


# ---------------------------------------------------------------------------
# Narrative generators
# ---------------------------------------------------------------------------

def build_reasoning(
    pair: str,
    direction: str,
    alignment: Dict,
    htf: Dict,
    ltf: Dict,
    indicators: Dict,
    smc: Dict,
    sentiment: Dict,
) -> list:
    tf_align = alignment.get("timeframe_alignment", {})
    struct = htf.get("structure", {}) if htf else {}
    ob = smc.get("order_blocks", {})
    liq = smc.get("liquidity", {})
    bos = htf.get("bos", {}) if htf else {}
    rsi = indicators.get("rsi", 50)
    ema_align = indicators.get("ema_alignment", "N/A")
    vol_str = indicators.get("volume_strength", "N/A")
    fg = sentiment.get("fear_greed", {})
    whale = sentiment.get("whale_activity", "UNKNOWN")

    reasons = [
        (
            f"Multi-timeframe consensus: {alignment.get('overall_bias')} at {alignment.get('strength')}% strength. "
            f"Daily={tf_align.get('daily','N/A')} | 4H={tf_align.get('4h','N/A')} | "
            f"1H={tf_align.get('1h','N/A')} | 15M={tf_align.get('15m','N/A')}. "
            f"Higher timeframe dominance confirms directional bias."
        ),
        (
            f"SMC footprint: {struct.get('description','N/A')}. "
            f"{'OB reaction: price at institutional ' + ('demand' if direction=='BUY' else 'supply') + ' zone. ' if (ob.get('at_bullish_ob') or ob.get('at_bearish_ob')) else ''}"
            f"BOS status: {bos.get('description','none')}. "
            f"Liquidity: {liq.get('sweep_description','N/A')}."
        ),
        (
            f"Technical confluence: RSI({rsi:.1f}) {indicators.get('rsi_signal','')}, "
            f"MACD {indicators.get('macd_signal','')}, EMA alignment {ema_align}, "
            f"volume {vol_str} ({indicators.get('volume_ratio',1.0):.2f}x avg). "
            f"Momentum: {indicators.get('momentum','')}."
        ),
        (
            f"Market environment: Fear & Greed {fg.get('value',50)} ({fg.get('classification','N/A')}), "
            f"contrarian read={fg.get('contrarian_bias','N/A')}. "
            f"Whale footprint: {whale}. "
            f"Funding rate: {sentiment.get('funding_rate_desc','N/A')}."
        ),
    ]
    return reasons


def build_warnings(
    direction: str,
    confidence: int,
    rr: float,
    htf: Dict,
    funding_rate: Optional[float],
    sentiment: Dict,
) -> list:
    warnings = []
    choch = htf.get("choch", {}) if htf else {}
    fg_val = sentiment.get("fear_greed", {}).get("value", 50)

    if confidence < 90:
        warnings.append(
            f"Confidence at {confidence}% — just above minimum threshold. Reduce position size by 30-50%."
        )
    if rr < 2.5:
        warnings.append(
            f"R:R of {rr:.1f}:1 is acceptable but sub-optimal. Wait for price to reach lower entry or pass."
        )
    if funding_rate is not None and abs(funding_rate) > 0.0005:
        sign = "positive" if funding_rate > 0 else "negative"
        warnings.append(
            f"Elevated funding rate ({funding_rate:.4%} {sign}). Holding overnight carries elevated carry cost."
        )
    if fg_val >= 75:
        warnings.append(
            "Extreme Greed territory — euphoria-driven markets reverse sharply. Use tighter stops."
        )
    elif fg_val <= 25:
        warnings.append(
            "Extreme Fear territory — high volatility, wide spreads, stop-hunts common. Size down."
        )
    if choch.get("detected"):
        warnings.append(f"CHOCH active: {choch.get('description','')}. Monitor for trend invalidation.")

    if not warnings:
        warnings.append("No critical warnings. Execute with standard institutional risk parameters.")

    return warnings
