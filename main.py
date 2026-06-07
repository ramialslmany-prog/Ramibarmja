#!/usr/bin/env python3
"""
Institutional-Grade Crypto Trading Signal Generator
Usage:
    python main.py BTC/USDT                    # single pair
    python main.py BTC/USDT ETH/USDT SOL/USDT  # multiple pairs
    python main.py --all                        # all configured pairs
    python main.py BTC/USDT --pretty            # pretty-print JSON
"""
import sys
import json
import logging
import argparse
from typing import Optional

from config import TRADING_PAIRS
from data.fetcher import MarketDataFetcher
from data.sentiment import fetch_fear_greed, estimate_whale_activity, analyze_news_sentiment
from analysis.multi_timeframe import run_multi_timeframe_analysis, check_timeframe_alignment
from analysis.market_structure import find_swing_highs_lows
from signals.generator import (
    determine_signal_direction,
    calculate_confidence,
    apply_filters,
    determine_setup_type,
    classify_risk,
    build_reasoning,
    build_warnings,
)
from signals.risk_manager import (
    calculate_entry_zone,
    calculate_stop_loss,
    calculate_take_profits,
    calculate_rr,
    calculate_leverage,
)
from output.formatter import (
    build_trend_analysis,
    build_smc_analysis,
    build_indicator_analysis,
    build_market_sentiment,
    build_risk_analysis,
    assemble_output,
)

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")


def analyze_pair(pair: str, fetcher: MarketDataFetcher, fear_greed: dict) -> dict:
    print(f"  Fetching data: {pair}", file=sys.stderr)
    data = fetcher.fetch_all_timeframes(pair)

    if len(data) < 3:
        return {"pair": pair, "signal": "HOLD", "reason": "Insufficient timeframe data"}

    funding_rate = fetcher.fetch_funding_rate(pair)
    ticker = fetcher.fetch_ticker(pair)

    analyses = run_multi_timeframe_analysis(data)
    alignment = check_timeframe_alignment(analyses)

    # BTC reference for correlation (skip if analyzing BTC itself)
    btc_ref = None
    if "BTC" not in pair.split("/")[0]:
        btc_data = fetcher.fetch_all_timeframes("BTC/USDT")
        if btc_data:
            btc_analyses = run_multi_timeframe_analysis(btc_data)
            btc_ref = btc_analyses.get("4h")

    # Primary timeframe references: 4H for trade decisions, 1H for entry timing
    htf = analyses.get("4h") or analyses.get("daily") or {}
    ltf = analyses.get("1h") or analyses.get("15m") or {}
    ind = htf.get("indicators", {}) if htf.get("valid") else {}
    smc = htf.get("smc", {}) if htf else {}

    price = ind.get("price", 0) or 0
    atr = ind.get("atr", price * 0.01) or price * 0.01

    # Signal direction
    direction = determine_signal_direction(alignment, htf, ltf)

    # Swing highs/lows for SL anchoring
    tf_key = "4h" if "4h" in data else ("1h" if "1h" in data else list(data.keys())[0])
    highs, lows = find_swing_highs_lows(data[tf_key])

    # Risk parameters
    ob = smc.get("order_blocks", {})
    fvg = smc.get("fvg", {})
    liq = smc.get("liquidity", {})

    entry_zone = calculate_entry_zone(price, direction, ob, fvg, atr)
    entry_mid = entry_zone.get("midpoint", price)
    sl = calculate_stop_loss(direction, entry_mid, ob, lows, highs, atr)
    tp1, tp2, tp3 = calculate_take_profits(direction, entry_mid, sl, liq)
    rr_ratio = calculate_rr(entry_mid, sl, tp1)

    # Confidence + filter
    confidence = calculate_confidence(alignment, htf, ltf, direction)
    direction, filter_result = apply_filters(direction, confidence, rr_ratio, alignment, ind)

    # Risk profile
    atr_pct = atr / price * 100 if price > 0 else 2.0
    risk_level = classify_risk(atr_pct, funding_rate)
    leverage = calculate_leverage(confidence, risk_level, rr_ratio)

    # Sentiment
    vol_ratio = ind.get("volume_ratio", 1.0)
    whale = estimate_whale_activity(ticker, vol_ratio)
    news = analyze_news_sentiment(pair)

    fr_desc = "N/A"
    if funding_rate is not None:
        if funding_rate > 0.001:
            fr_desc = f"{funding_rate:.4%} POSITIVE (crowded longs)"
        elif funding_rate < -0.001:
            fr_desc = f"{funding_rate:.4%} NEGATIVE (crowded shorts)"
        else:
            fr_desc = f"{funding_rate:.4%} NEUTRAL"

    sentiment = {
        "fear_greed": fear_greed,
        "whale_activity": whale,
        "news_sentiment": news,
        "funding_rate": funding_rate,
        "funding_rate_desc": fr_desc,
    }

    setup_type = determine_setup_type(confidence, rr_ratio, htf.get("trend", "UNKNOWN") if htf else "UNKNOWN")
    reasoning = build_reasoning(pair, direction, alignment, htf, ltf, ind, smc, sentiment)
    warnings = build_warnings(direction, confidence, rr_ratio, htf, funding_rate, sentiment)

    # Formatters
    trend_out = build_trend_analysis(alignment.get("timeframe_alignment", {}), analyses)
    smc_out = build_smc_analysis(htf, ltf)
    ind_out = build_indicator_analysis(ind)
    sent_out = build_market_sentiment(fear_greed, whale, news, funding_rate, btc_ref)
    risk_out = build_risk_analysis(risk_level, atr, price, leverage, entry_mid, sl)

    return assemble_output(
        pair=pair,
        signal=direction,
        setup_type=setup_type,
        confidence=confidence,
        entry_zone=entry_zone,
        tps=(tp1, tp2, tp3),
        stop_loss=sl,
        rr=rr_ratio,
        trend_analysis=trend_out,
        smc_analysis=smc_out,
        indicator_analysis=ind_out,
        market_sentiment=sent_out,
        risk_analysis=risk_out,
        reasoning=reasoning,
        warnings=warnings,
    )


def main():
    parser = argparse.ArgumentParser(description="Institutional-Grade Crypto Signal Generator")
    parser.add_argument("pairs", nargs="*", help="Pairs to analyze e.g. BTC/USDT ETH/USDT")
    parser.add_argument("--all", action="store_true", help="Analyze all default pairs")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()

    pairs = args.pairs if args.pairs else (TRADING_PAIRS if args.all else ["BTC/USDT"])

    print("Initializing exchange connection...", file=sys.stderr)
    fetcher = MarketDataFetcher()
    print("Fetching Fear & Greed Index...", file=sys.stderr)
    fear_greed = fetch_fear_greed()

    results = []
    for pair in pairs:
        try:
            sig = analyze_pair(pair, fetcher, fear_greed)
            results.append(sig)
        except Exception as exc:
            results.append({"pair": pair, "signal": "HOLD", "error": str(exc)})

    indent = 2 if args.pretty else None
    output = results[0] if len(results) == 1 else results
    print(json.dumps(output, indent=indent))


if __name__ == "__main__":
    main()
