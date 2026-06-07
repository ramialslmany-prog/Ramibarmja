from typing import Dict, List, Optional, Tuple


def calculate_entry_zone(
    price: float,
    signal: str,
    ob_data: Dict,
    fvg_data: Dict,
    atr: float,
) -> Dict:
    if signal == "BUY":
        ob = ob_data.get("nearest_bullish_ob")
        fvgs = fvg_data.get("unfilled_bullish", [])
        if ob and ob["bottom"] < price * 1.01:
            lo, hi = ob["bottom"] * 0.9995, ob["top"] * 1.0005
        elif fvgs:
            lo, hi = fvgs[0]["bottom"], fvgs[0]["top"]
        else:
            lo, hi = price - atr * 0.35, price + atr * 0.15
    elif signal == "SELL":
        ob = ob_data.get("nearest_bearish_ob")
        fvgs = fvg_data.get("unfilled_bearish", [])
        if ob and ob["top"] > price * 0.99:
            lo, hi = ob["bottom"] * 0.9995, ob["top"] * 1.0005
        elif fvgs:
            lo, hi = fvgs[0]["bottom"], fvgs[0]["top"]
        else:
            lo, hi = price - atr * 0.15, price + atr * 0.35
    else:
        lo = hi = price

    return {"from": f"{lo:.6g}", "to": f"{hi:.6g}", "midpoint": (lo + hi) / 2}


def calculate_stop_loss(
    signal: str,
    entry: float,
    ob_data: Dict,
    lows: List,
    highs: List,
    atr: float,
    buffer: float = 0.003,
) -> float:
    if signal == "BUY":
        ob = ob_data.get("nearest_bullish_ob")
        if ob:
            return ob["bottom"] * (1 - buffer)
        if lows:
            recent = sorted(lows[-3:], key=lambda x: x["price"])
            return recent[0]["price"] * (1 - buffer)
        return entry - atr * 1.8

    elif signal == "SELL":
        ob = ob_data.get("nearest_bearish_ob")
        if ob:
            return ob["top"] * (1 + buffer)
        if highs:
            recent = sorted(highs[-3:], key=lambda x: x["price"], reverse=True)
            return recent[0]["price"] * (1 + buffer)
        return entry + atr * 1.8

    return entry


def calculate_take_profits(
    signal: str,
    entry: float,
    stop_loss: float,
    liquidity: Dict,
) -> Tuple[float, float, float]:
    risk = abs(entry - stop_loss)
    if risk == 0:
        risk = entry * 0.01

    if signal == "BUY":
        buy_liq = liquidity.get("buy_side_liquidity", [])
        above = [p for p in buy_liq if p > entry]
        tp1 = above[0] * 0.999 if len(above) >= 1 else entry + risk * 1.5
        tp2 = above[1] * 0.999 if len(above) >= 2 else entry + risk * 2.5
        tp3 = above[2] * 0.999 if len(above) >= 3 else entry + risk * 4.0
    elif signal == "SELL":
        sell_liq = liquidity.get("sell_side_liquidity", [])
        below = [p for p in sell_liq if p < entry]
        tp1 = below[0] * 1.001 if len(below) >= 1 else entry - risk * 1.5
        tp2 = below[1] * 1.001 if len(below) >= 2 else entry - risk * 2.5
        tp3 = below[2] * 1.001 if len(below) >= 3 else entry - risk * 4.0
    else:
        tp1 = tp2 = tp3 = entry

    return tp1, tp2, tp3


def calculate_rr(entry: float, stop_loss: float, tp1: float) -> float:
    risk = abs(entry - stop_loss)
    reward = abs(tp1 - entry)
    return round(reward / risk, 2) if risk > 0 else 0.0


def calculate_leverage(confidence: int, risk_level: str, rr: float) -> int:
    base = {"HIGH": 2, "MEDIUM": 3, "LOW": 5}.get(risk_level, 3)
    conf_mult = 1.5 if confidence >= 92 else 1.2 if confidence >= 87 else 1.0
    rr_mult = 1.2 if rr > 3 else 0.8 if rr < 2 else 1.0
    return max(1, min(10, int(base * conf_mult * rr_mult)))
