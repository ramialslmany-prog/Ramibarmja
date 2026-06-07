TRADING_PAIRS = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "BNB/USDT",
    "XRP/USDT",
    "AVAX/USDT",
    "LINK/USDT",
    "ARB/USDT",
    "OP/USDT",
    "MATIC/USDT",
]

EXCHANGE_ID = "binance"
EXCHANGE_TYPE = "future"

TIMEFRAMES = ["5m", "15m", "1h", "4h", "1d"]
CANDLE_LIMIT = 200

SIGNAL_FILTERS = {
    "min_confidence": 85,
    "min_rr_ratio": 2.0,
}

RISK_PARAMS = {
    "default_risk_pct": 1.0,
    "max_leverage": 10,
}

INDICATOR_PARAMS = {
    "rsi_period": 14,
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    "ema_periods": [20, 50, 200],
    "atr_period": 14,
    "volume_ma_period": 20,
}

SMC_PARAMS = {
    "swing_lookback": 5,
    "ob_lookback": 100,
    "fvg_min_size_pct": 0.1,
    "equal_highs_lows_tolerance": 0.002,
}

FEAR_GREED_API = "https://api.alternative.me/fng/?limit=1"
