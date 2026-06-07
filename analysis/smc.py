import numpy as np
import pandas as pd
from typing import List, Dict, Optional

from config import SMC_PARAMS


def detect_order_blocks(df: pd.DataFrame, n: int = 100) -> Dict:
    """
    Bullish OB: last bearish candle before a strong impulsive bullish move (>2x ATR).
    Bearish OB: last bullish candle before a strong impulsive bearish move (>2x ATR).
    """
    df_slice = df.iloc[-n:].copy()
    atr = float((df_slice["high"] - df_slice["low"]).rolling(14).mean().iloc[-1])
    if atr == 0:
        atr = float(df_slice["close"].iloc[-1]) * 0.01

    bullish_obs: List[Dict] = []
    bearish_obs: List[Dict] = []

    for i in range(2, len(df_slice) - 3):
        c = df_slice.iloc[i]
        nxt = df_slice.iloc[i + 1: i + 4]

        if float(c["close"]) < float(c["open"]):  # bearish candle
            move_up = float(nxt["close"].max()) - float(c["low"])
            if move_up > 2 * atr:
                bullish_obs.append({
                    "top": float(c["open"]),
                    "bottom": float(c["close"]),
                    "timestamp": str(df_slice.index[i]),
                    "strength": round(move_up / atr, 2),
                    "type": "BULLISH",
                })
        elif float(c["close"]) > float(c["open"]):  # bullish candle
            move_down = float(c["high"]) - float(nxt["close"].min())
            if move_down > 2 * atr:
                bearish_obs.append({
                    "top": float(c["close"]),
                    "bottom": float(c["open"]),
                    "timestamp": str(df_slice.index[i]),
                    "strength": round(move_down / atr, 2),
                    "type": "BEARISH",
                })

    price = float(df["close"].iloc[-1])

    nearest_bull_ob: Optional[Dict] = None
    nearest_bear_ob: Optional[Dict] = None

    # Nearest bullish OB below or at current price
    candidates = [ob for ob in bullish_obs if ob["top"] < price * 1.02]
    if candidates:
        nearest_bull_ob = max(candidates, key=lambda x: x["top"])

    # Nearest bearish OB above or at current price
    candidates = [ob for ob in bearish_obs if ob["bottom"] > price * 0.98]
    if candidates:
        nearest_bear_ob = min(candidates, key=lambda x: x["bottom"])

    at_bull = (
        nearest_bull_ob is not None
        and nearest_bull_ob["bottom"] <= price <= nearest_bull_ob["top"] * 1.005
    )
    at_bear = (
        nearest_bear_ob is not None
        and nearest_bear_ob["bottom"] * 0.995 <= price <= nearest_bear_ob["top"]
    )

    return {
        "bullish_obs": bullish_obs[-5:],
        "bearish_obs": bearish_obs[-5:],
        "nearest_bullish_ob": nearest_bull_ob,
        "nearest_bearish_ob": nearest_bear_ob,
        "at_bullish_ob": at_bull,
        "at_bearish_ob": at_bear,
    }


def detect_fvg(df: pd.DataFrame, min_size_pct: float = 0.1) -> Dict:
    """
    Bullish FVG: candle[i].low > candle[i-2].high — unfilled gap acting as support.
    Bearish FVG: candle[i].high < candle[i-2].low — unfilled gap acting as resistance.
    """
    bullish_fvgs: List[Dict] = []
    bearish_fvgs: List[Dict] = []

    for i in range(2, len(df)):
        gap_bull = float(df["low"].iloc[i]) - float(df["high"].iloc[i - 2])
        if gap_bull > 0:
            pct = gap_bull / float(df["close"].iloc[i]) * 100
            if pct >= min_size_pct:
                bullish_fvgs.append({
                    "top": float(df["low"].iloc[i]),
                    "bottom": float(df["high"].iloc[i - 2]),
                    "size_pct": round(pct, 3),
                    "timestamp": str(df.index[i]),
                })

        gap_bear = float(df["low"].iloc[i - 2]) - float(df["high"].iloc[i])
        if gap_bear > 0:
            pct = gap_bear / float(df["close"].iloc[i]) * 100
            if pct >= min_size_pct:
                bearish_fvgs.append({
                    "top": float(df["low"].iloc[i - 2]),
                    "bottom": float(df["high"].iloc[i]),
                    "size_pct": round(pct, 3),
                    "timestamp": str(df.index[i]),
                })

    price = float(df["close"].iloc[-1])

    # Keep only unfilled gaps near current price (within 3%)
    unfilled_bull = [f for f in bullish_fvgs[-20:] if f["top"] >= price * 0.97 and f["bottom"] <= price * 1.03]
    unfilled_bear = [f for f in bearish_fvgs[-20:] if f["bottom"] <= price * 1.03 and f["top"] >= price * 0.97]

    return {
        "bullish_fvgs": bullish_fvgs[-10:],
        "bearish_fvgs": bearish_fvgs[-10:],
        "unfilled_bullish": unfilled_bull,
        "unfilled_bearish": unfilled_bear,
        "has_bullish_fvg_below": any(f["top"] < price for f in bullish_fvgs[-15:]),
        "has_bearish_fvg_above": any(f["bottom"] > price for f in bearish_fvgs[-15:]),
    }


def detect_liquidity_zones(df: pd.DataFrame) -> Dict:
    tol = SMC_PARAMS["equal_highs_lows_tolerance"]
    n = min(100, len(df))
    ds = df.iloc[-n:]
    lb = 3

    swing_highs = []
    swing_lows = []
    for i in range(lb, len(ds) - lb):
        h_win = ds["high"].iloc[i - lb: i + lb + 1]
        l_win = ds["low"].iloc[i - lb: i + lb + 1]
        if float(ds["high"].iloc[i]) == float(h_win.max()):
            swing_highs.append(float(ds["high"].iloc[i]))
        if float(ds["low"].iloc[i]) == float(l_win.min()):
            swing_lows.append(float(ds["low"].iloc[i]))

    # Equal highs / lows
    def find_equals(prices: list) -> list:
        result = []
        for i, p1 in enumerate(prices):
            for p2 in prices[i + 1:]:
                if abs(p1 - p2) / p1 < tol:
                    result.append(round((p1 + p2) / 2, 6))
        return result

    eq_highs = find_equals(swing_highs)
    eq_lows = find_equals(swing_lows)

    price = float(df["close"].iloc[-1])

    buy_liq = sorted(set([p for p in eq_highs + swing_highs if p > price]))
    sell_liq = sorted(set([p for p in eq_lows + swing_lows if p < price]), reverse=True)

    # Detect recent sweep
    recent_high = float(df["high"].iloc[-3:].max())
    recent_low = float(df["low"].iloc[-3:].min())
    last_close = float(df["close"].iloc[-1])

    swept_buy = bool(buy_liq and recent_high > buy_liq[0] and last_close < buy_liq[0])
    swept_sell = bool(sell_liq and recent_low < sell_liq[0] and last_close > sell_liq[0])

    if swept_buy:
        sweep_desc = f"BUY_SIDE_LIQUIDITY_SWEPT at {buy_liq[0]:.4f} — shorts trapped, potential long reversal"
    elif swept_sell:
        sweep_desc = f"SELL_SIDE_LIQUIDITY_SWEPT at {sell_liq[0]:.4f} — longs trapped, potential short reversal"
    else:
        sweep_desc = "NO_SWEEP_DETECTED — liquidity pools intact"

    return {
        "buy_side_liquidity": buy_liq[:4],
        "sell_side_liquidity": sell_liq[:4],
        "equal_highs": eq_highs[:3],
        "equal_lows": eq_lows[:3],
        "swept_buy_side": swept_buy,
        "swept_sell_side": swept_sell,
        "sweep_description": sweep_desc,
    }


def analyze_smc(df: pd.DataFrame) -> Dict:
    return {
        "order_blocks": detect_order_blocks(df),
        "fvg": detect_fvg(df),
        "liquidity": detect_liquidity_zones(df),
    }
