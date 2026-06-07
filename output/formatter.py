from typing import Dict, Optional, Tuple


def build_trend_analysis(alignment: Dict, analyses: Dict) -> Dict:
    tf_order = ["daily", "4h", "1h", "15m"]
    result = {}
    for tf in tf_order:
        a = analyses.get(tf)
        if a and a.get("valid"):
            ind = a.get("indicators", {})
            st = a.get("structure", {})
            result[tf] = (
                f"{a.get('trend','N/A')} | "
                f"EMA: {ind.get('ema_alignment','N/A')} | "
                f"RSI: {ind.get('rsi',0):.0f} | "
                f"Structure: {st.get('trend','N/A')}"
            )
        else:
            result[tf] = "DATA_UNAVAILABLE"
    return result


def build_smc_analysis(htf: Dict, ltf: Dict) -> Dict:
    smc = htf.get("smc", {}) if htf else {}
    ob = smc.get("order_blocks", {})
    fvg = smc.get("fvg", {})
    liq = smc.get("liquidity", {})
    bos = htf.get("bos", {}) if htf else {}
    choch = htf.get("choch", {}) if htf else {}
    struct = htf.get("structure", {}) if htf else {}

    bull_ob = ob.get("nearest_bullish_ob")
    bear_ob = ob.get("nearest_bearish_ob")
    if ob.get("at_bullish_ob") and bull_ob:
        ob_desc = f"At bullish OB [{bull_ob['bottom']:.4f} – {bull_ob['top']:.4f}] — institutional demand zone active"
    elif ob.get("at_bearish_ob") and bear_ob:
        ob_desc = f"At bearish OB [{bear_ob['bottom']:.4f} – {bear_ob['top']:.4f}] — institutional supply zone active"
    elif bull_ob:
        ob_desc = f"Nearest bullish OB below: [{bull_ob['bottom']:.4f} – {bull_ob['top']:.4f}]"
    elif bear_ob:
        ob_desc = f"Nearest bearish OB above: [{bear_ob['bottom']:.4f} – {bear_ob['top']:.4f}]"
    else:
        ob_desc = "No significant order block in proximity"

    unfilled_bull = fvg.get("unfilled_bullish", [])
    unfilled_bear = fvg.get("unfilled_bearish", [])
    if unfilled_bull:
        fvg_desc = f"Bullish FVG [{unfilled_bull[0]['bottom']:.4f} – {unfilled_bull[0]['top']:.4f}] ({unfilled_bull[0]['size_pct']:.2f}%) — imbalance acting as support"
    elif unfilled_bear:
        fvg_desc = f"Bearish FVG [{unfilled_bear[0]['bottom']:.4f} – {unfilled_bear[0]['top']:.4f}] ({unfilled_bear[0]['size_pct']:.2f}%) — imbalance acting as resistance"
    else:
        fvg_desc = "No significant FVG near current price"

    if ob.get("at_bullish_ob"):
        inst_bias = "ACCUMULATION — institutional demand being absorbed at current levels"
    elif ob.get("at_bearish_ob"):
        inst_bias = "DISTRIBUTION — institutional supply being offloaded at current levels"
    else:
        inst_bias = "NEUTRAL — no confirmed institutional footprint at current price"

    return {
        "market_structure": struct.get("description", "N/A"),
        "bos": bos.get("description", "No recent BOS"),
        "choch": choch.get("description", "No CHOCH detected"),
        "liquidity_sweep": liq.get("sweep_description", "NO_SWEEP_DETECTED"),
        "order_block": ob_desc,
        "fvg": fvg_desc,
        "institutional_bias": inst_bias,
    }


def build_indicator_analysis(ind: Dict) -> Dict:
    hist = ind.get("macd_histogram", 0)
    hist_trend = "EXPANDING" if abs(hist) > 0 else "CONTRACTING"
    return {
        "rsi": (
            f"RSI({ind.get('rsi',50):.1f}) — {ind.get('rsi_signal','N/A')} | "
            f"Bias: {ind.get('rsi_bias','N/A')}"
        ),
        "macd": (
            f"MACD: {ind.get('macd_signal','N/A')} | "
            f"Histogram {hist_trend} ({hist:.4f})"
        ),
        "ema_alignment": (
            f"{ind.get('ema_alignment','N/A')} | "
            f"EMA20={ind.get('ema20',0):.4f} | "
            f"EMA50={ind.get('ema50',0):.4f} | "
            f"EMA200={ind.get('ema200',0):.4f}"
        ),
        "volume_strength": (
            f"{ind.get('volume_strength','N/A')} | "
            f"{ind.get('volume_ratio',1.0):.2f}x 20-period average"
        ),
        "momentum": (
            f"{ind.get('momentum','N/A')} | "
            f"Delta volume: {'POSITIVE_ABSORPTION' if ind.get('delta_volume',0) > 0 else 'NEGATIVE_DISTRIBUTION'}"
        ),
    }


def build_market_sentiment(
    fear_greed: Dict,
    whale: str,
    news: str,
    funding_rate: Optional[float],
    btc_analysis: Optional[Dict],
) -> Dict:
    if btc_analysis and btc_analysis.get("valid"):
        btc_ind = btc_analysis.get("indicators", {})
        btc_desc = (
            f"BTC trend: {btc_analysis.get('trend','N/A')} | "
            f"RSI: {btc_ind.get('rsi',50):.0f} | "
            f"EMA: {btc_ind.get('ema_alignment','N/A')} | "
            f"Positive correlation — BTC direction governs altcoin risk"
        )
    else:
        btc_desc = "BTC reference data unavailable — assess correlation manually"

    if funding_rate is not None:
        if funding_rate > 0.001:
            fr_desc = f"{funding_rate:.4%} POSITIVE — longs paying shorts (crowded long, elevated reversal risk)"
        elif funding_rate < -0.001:
            fr_desc = f"{funding_rate:.4%} NEGATIVE — shorts paying longs (crowded short, squeeze risk elevated)"
        else:
            fr_desc = f"{funding_rate:.4%} NEUTRAL — balanced derivatives market"
    else:
        fr_desc = "N/A — futures data unavailable"

    return {
        "btc_correlation": btc_desc,
        "fear_greed": (
            f"Index: {fear_greed.get('value',50)} ({fear_greed.get('classification','N/A')}) | "
            f"Contrarian signal: {fear_greed.get('contrarian_bias','N/A')}"
        ),
        "news_sentiment": news,
        "whale_activity": whale,
        "funding_rate": fr_desc,
    }


def build_risk_analysis(
    risk_level: str,
    atr: float,
    price: float,
    leverage: int,
    entry: float,
    stop_loss: float,
) -> Dict:
    atr_pct = atr / price * 100 if price > 0 else 0
    risk_pct = abs(entry - stop_loss) / entry * 100 if entry > 0 else 0
    liq_dist = 100 / leverage * 0.8 if leverage > 0 else 100
    liq_risk = (
        "HIGH" if risk_pct > liq_dist * 0.5
        else "MEDIUM" if risk_pct > liq_dist * 0.25
        else "LOW"
    )

    vol_label = (
        "HIGH_VOLATILITY" if atr_pct > 3
        else "NORMAL_VOLATILITY" if atr_pct > 1
        else "LOW_VOLATILITY"
    )

    return {
        "risk_level": risk_level,
        "volatility_risk": f"ATR={atr:.4f} ({atr_pct:.2f}% of price) — {vol_label}",
        "liquidation_risk": (
            f"{liq_risk} | At {leverage}x, theoretical liquidation ~{liq_dist:.1f}% from entry. "
            f"Trade SL consumes {risk_pct:.2f}% of capital per 1% account risk."
        ),
        "recommended_leverage": (
            f"{leverage}x recommended | Hard cap {min(leverage * 2, 10)}x — "
            f"never exceed without proportionally reduced position size"
        ),
    }


def assemble_output(
    pair: str,
    signal: str,
    setup_type: str,
    confidence: int,
    entry_zone: Dict,
    tps: Tuple,
    stop_loss: float,
    rr: float,
    trend_analysis: Dict,
    smc_analysis: Dict,
    indicator_analysis: Dict,
    market_sentiment: Dict,
    risk_analysis: Dict,
    reasoning: list,
    warnings: list,
) -> Dict:
    tp1, tp2, tp3 = tps
    return {
        "pair": pair,
        "signal": signal,
        "setup_type": setup_type,
        "confidence": confidence,
        "entry_zone": {"from": entry_zone.get("from", ""), "to": entry_zone.get("to", "")},
        "take_profit": [f"{tp1:.6g}", f"{tp2:.6g}", f"{tp3:.6g}"],
        "stop_loss": f"{stop_loss:.6g}",
        "risk_reward_ratio": f"1:{rr:.1f}",
        "trend_analysis": trend_analysis,
        "smart_money_analysis": smc_analysis,
        "indicator_analysis": indicator_analysis,
        "market_sentiment": market_sentiment,
        "risk_analysis": risk_analysis,
        "trade_reasoning": reasoning,
        "warnings": warnings,
    }
