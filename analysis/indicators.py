import numpy as np
import pandas as pd
from typing import Dict

from config import INDICATOR_PARAMS


def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.inf)
    return 100 - (100 / (1 + rs))


def calculate_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
    ema_fast = calculate_ema(series, fast)
    ema_slow = calculate_ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    return {
        "macd": macd_line,
        "signal": signal_line,
        "histogram": macd_line - signal_line,
    }


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    hl = df["high"] - df["low"]
    hc = (df["high"] - df["close"].shift(1)).abs()
    lc = (df["low"] - df["close"].shift(1)).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


def calculate_delta_volume(df: pd.DataFrame) -> pd.Series:
    midpoint = (df["high"] + df["low"]) / 2
    direction = np.where(df["close"] >= midpoint, 1, -1)
    return pd.Series(direction * df["volume"].values, index=df.index)


def run_indicators(df: pd.DataFrame) -> Dict:
    p = INDICATOR_PARAMS

    rsi_series = calculate_rsi(df["close"], p["rsi_period"])
    macd_data = calculate_macd(df["close"], p["macd_fast"], p["macd_slow"], p["macd_signal"])
    ema20 = calculate_ema(df["close"], 20)
    ema50 = calculate_ema(df["close"], 50)
    ema200 = calculate_ema(df["close"], 200)
    atr = calculate_atr(df, p["atr_period"])
    vol_ma = df["volume"].rolling(p["volume_ma_period"]).mean()
    delta_vol = calculate_delta_volume(df)

    price = df["close"].iloc[-1]
    rsi = float(rsi_series.iloc[-1])
    macd_val = float(macd_data["macd"].iloc[-1])
    macd_sig = float(macd_data["signal"].iloc[-1])
    macd_hist = float(macd_data["histogram"].iloc[-1])
    macd_hist_prev = float(macd_data["histogram"].iloc[-2])

    vol_ratio = float(df["volume"].iloc[-1] / vol_ma.iloc[-1]) if float(vol_ma.iloc[-1]) > 0 else 1.0

    # RSI interpretation
    if rsi < 30:
        rsi_signal, rsi_bias = "OVERSOLD", "BULLISH"
    elif rsi < 45:
        rsi_signal, rsi_bias = "BEARISH_ZONE", "MILD_BEARISH"
    elif rsi < 55:
        rsi_signal, rsi_bias = "NEUTRAL", "NEUTRAL"
    elif rsi < 70:
        rsi_signal, rsi_bias = "BULLISH_ZONE", "MILD_BULLISH"
    else:
        rsi_signal, rsi_bias = "OVERBOUGHT", "BEARISH"

    # MACD interpretation
    if macd_val > macd_sig:
        macd_str = "BULLISH_MOMENTUM_INCREASING" if macd_hist > macd_hist_prev else "BULLISH_MOMENTUM_WANING"
        macd_bias = "BULLISH"
    elif macd_val < macd_sig:
        macd_str = "BEARISH_MOMENTUM_INCREASING" if macd_hist < macd_hist_prev else "BEARISH_MOMENTUM_WANING"
        macd_bias = "BEARISH"
    else:
        macd_str = "CROSSOVER_ZONE"
        macd_bias = "NEUTRAL"

    # EMA alignment
    e20, e50, e200 = float(ema20.iloc[-1]), float(ema50.iloc[-1]), float(ema200.iloc[-1])
    if price > e20 > e50 > e200:
        ema_align, ema_bias = "STRONGLY_BULLISH", "BULLISH"
    elif price > e50 > e200:
        ema_align, ema_bias = "BULLISH", "BULLISH"
    elif price < e20 < e50 < e200:
        ema_align, ema_bias = "STRONGLY_BEARISH", "BEARISH"
    elif price < e50 < e200:
        ema_align, ema_bias = "BEARISH", "BEARISH"
    else:
        ema_align, ema_bias = "MIXED", "NEUTRAL"

    # Volume strength
    if vol_ratio > 2.0:
        vol_strength = "VERY_HIGH"
    elif vol_ratio > 1.5:
        vol_strength = "HIGH"
    elif vol_ratio > 0.8:
        vol_strength = "NORMAL"
    else:
        vol_strength = "LOW"

    # Short-term momentum (5-candle)
    lookback = min(5, len(df) - 1)
    recent_change = (price - float(df["close"].iloc[-lookback - 1])) / float(df["close"].iloc[-lookback - 1]) * 100
    if recent_change > 3:
        momentum = "STRONG_BULLISH"
    elif recent_change > 1:
        momentum = "MILD_BULLISH"
    elif recent_change < -3:
        momentum = "STRONG_BEARISH"
    elif recent_change < -1:
        momentum = "MILD_BEARISH"
    else:
        momentum = "NEUTRAL"

    return {
        "price": price,
        "rsi": rsi,
        "rsi_signal": rsi_signal,
        "rsi_bias": rsi_bias,
        "macd": macd_val,
        "macd_signal_line": macd_sig,
        "macd_histogram": macd_hist,
        "macd_signal": macd_str,
        "macd_bias": macd_bias,
        "ema20": e20,
        "ema50": e50,
        "ema200": e200,
        "ema_alignment": ema_align,
        "ema_bias": ema_bias,
        "atr": float(atr.iloc[-1]),
        "volume_ratio": vol_ratio,
        "volume_strength": vol_strength,
        "delta_volume": float(delta_vol.iloc[-10:].sum()),
        "momentum": momentum,
    }
