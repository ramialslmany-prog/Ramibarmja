import requests
import logging
from typing import Optional, Dict

from config import FEAR_GREED_API

logger = logging.getLogger(__name__)


def fetch_fear_greed() -> Dict:
    try:
        resp = requests.get(FEAR_GREED_API, timeout=6)
        data = resp.json()
        value = int(data["data"][0]["value"])
        classification = data["data"][0]["value_classification"]

        if value <= 25:
            sentiment = "EXTREME_FEAR"
            bias = "BULLISH_CONTRARIAN"
        elif value <= 45:
            sentiment = "FEAR"
            bias = "MILD_BULLISH"
        elif value <= 55:
            sentiment = "NEUTRAL"
            bias = "NEUTRAL"
        elif value <= 75:
            sentiment = "GREED"
            bias = "MILD_BEARISH_CONTRARIAN"
        else:
            sentiment = "EXTREME_GREED"
            bias = "BEARISH_CONTRARIAN"

        return {
            "value": value,
            "classification": classification,
            "sentiment": sentiment,
            "contrarian_bias": bias,
        }
    except Exception as e:
        logger.warning(f"Fear & Greed fetch failed: {e}")
        return {
            "value": 50,
            "classification": "Neutral",
            "sentiment": "NEUTRAL",
            "contrarian_bias": "NEUTRAL",
        }


def estimate_whale_activity(ticker: Optional[Dict], volume_ratio: float) -> str:
    if not ticker:
        return "UNKNOWN"

    price_change_pct = abs(ticker.get("percentage") or 0)

    if volume_ratio > 3.0 and price_change_pct > 5:
        return "HIGH_WHALE_ACTIVITY - Large directional flow detected"
    elif volume_ratio > 2.0:
        return "MODERATE_ACCUMULATION - Elevated institutional interest"
    elif volume_ratio < 0.5:
        return "POTENTIAL_DISTRIBUTION - Below-average participation"
    else:
        return "NORMAL_ACTIVITY - No anomalous whale prints"


def analyze_news_sentiment(pair: str) -> str:
    # Stub — wire to CryptoPanic or LunarCrush API for live data
    return "NEUTRAL_TO_POSITIVE - No major adverse events detected"
