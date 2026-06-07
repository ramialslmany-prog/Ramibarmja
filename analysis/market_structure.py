import pandas as pd
from typing import List, Tuple, Dict

from config import SMC_PARAMS


def find_swing_highs_lows(df: pd.DataFrame, lookback: int = None) -> Tuple[List, List]:
    lookback = lookback or SMC_PARAMS["swing_lookback"]
    highs, lows = [], []
    n = len(df)

    for i in range(lookback, n - lookback):
        window_h = df["high"].iloc[i - lookback: i + lookback + 1]
        window_l = df["low"].iloc[i - lookback: i + lookback + 1]

        if float(df["high"].iloc[i]) == float(window_h.max()):
            highs.append({"index": i, "timestamp": df.index[i], "price": float(df["high"].iloc[i])})

        if float(df["low"].iloc[i]) == float(window_l.min()):
            lows.append({"index": i, "timestamp": df.index[i], "price": float(df["low"].iloc[i])})

    return highs, lows


def classify_market_structure(highs: List, lows: List) -> Dict:
    if len(highs) < 2 or len(lows) < 2:
        return {"trend": "UNKNOWN", "description": "Insufficient swing data", "hh_count": 0, "hl_count": 0, "lh_count": 0, "ll_count": 0}

    rh = sorted(highs[-4:], key=lambda x: x["index"])
    rl = sorted(lows[-4:], key=lambda x: x["index"])

    hh = sum(1 for i in range(1, len(rh)) if rh[i]["price"] > rh[i - 1]["price"])
    hl = sum(1 for i in range(1, len(rl)) if rl[i]["price"] > rl[i - 1]["price"])
    lh = sum(1 for i in range(1, len(rh)) if rh[i]["price"] < rh[i - 1]["price"])
    ll = sum(1 for i in range(1, len(rl)) if rl[i]["price"] < rl[i - 1]["price"])

    bull_score = hh + hl
    bear_score = lh + ll

    if bull_score >= 3:
        trend = "UPTREND"
        desc = f"HH({hh}) + HL({hl}) — confirmed bullish market structure"
    elif bear_score >= 3:
        trend = "DOWNTREND"
        desc = f"LH({lh}) + LL({ll}) — confirmed bearish market structure"
    elif bull_score == 2:
        trend = "MILD_UPTREND"
        desc = "Developing bullish structure — needs further confirmation"
    elif bear_score == 2:
        trend = "MILD_DOWNTREND"
        desc = "Developing bearish structure — needs further confirmation"
    else:
        trend = "RANGING"
        desc = "No clear directional structure — avoid directional bias"

    return {
        "trend": trend,
        "description": desc,
        "recent_highs": [h["price"] for h in rh[-2:]],
        "recent_lows": [l["price"] for l in rl[-2:]],
        "hh_count": hh,
        "hl_count": hl,
        "lh_count": lh,
        "ll_count": ll,
    }


def detect_bos(df: pd.DataFrame, highs: List, lows: List) -> Dict:
    if not highs or not lows:
        return {"detected": False, "type": None, "level": None, "description": "No swing points for BOS detection"}

    last_high = highs[-1]["price"]
    last_low = lows[-1]["price"]
    recent = df.iloc[-5:]

    if float(recent["close"].max()) > last_high:
        return {
            "detected": True,
            "type": "BULLISH_BOS",
            "level": last_high,
            "description": f"Bullish BOS: close broke above swing high {last_high:.4f} — institutional buying confirmed",
        }
    elif float(recent["close"].min()) < last_low:
        return {
            "detected": True,
            "type": "BEARISH_BOS",
            "level": last_low,
            "description": f"Bearish BOS: close broke below swing low {last_low:.4f} — institutional selling confirmed",
        }

    return {"detected": False, "type": None, "level": None, "description": "No recent BOS — structure intact"}


def detect_choch(df: pd.DataFrame, structure: Dict, highs: List, lows: List) -> Dict:
    if len(highs) < 2 or len(lows) < 2:
        return {"detected": False, "type": None, "description": "Insufficient data for CHOCH"}

    trend = structure.get("trend", "UNKNOWN")

    if "UPTREND" in trend and lows[-1]["price"] < lows[-2]["price"]:
        return {
            "detected": True,
            "type": "BEARISH_CHOCH",
            "level": lows[-1]["price"],
            "description": f"Bearish CHOCH: first LL at {lows[-1]['price']:.4f} in uptrend — early reversal warning",
        }
    elif "DOWNTREND" in trend and highs[-1]["price"] > highs[-2]["price"]:
        return {
            "detected": True,
            "type": "BULLISH_CHOCH",
            "level": highs[-1]["price"],
            "description": f"Bullish CHOCH: first HH at {highs[-1]['price']:.4f} in downtrend — early reversal signal",
        }

    return {"detected": False, "type": None, "description": "No CHOCH — trend character unchanged"}


def classify_trend_simple(df: pd.DataFrame) -> str:
    if len(df) < 50:
        return "UNKNOWN"

    ema20 = df["close"].ewm(span=20, adjust=False).mean()
    ema50 = df["close"].ewm(span=50, adjust=False).mean()
    price = float(df["close"].iloc[-1])
    slope = (float(ema20.iloc[-1]) - float(ema20.iloc[-5])) / float(ema20.iloc[-5]) * 100

    if price > float(ema20.iloc[-1]) > float(ema50.iloc[-1]) and slope > 0.3:
        return "UPTREND"
    elif price < float(ema20.iloc[-1]) < float(ema50.iloc[-1]) and slope < -0.3:
        return "DOWNTREND"
    elif price > float(ema50.iloc[-1]):
        return "MILD_UPTREND"
    elif price < float(ema50.iloc[-1]):
        return "MILD_DOWNTREND"
    return "RANGING"
