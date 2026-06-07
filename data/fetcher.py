import ccxt
import pandas as pd
import time
import logging
from typing import Dict, Optional

from config import EXCHANGE_ID, EXCHANGE_TYPE, TIMEFRAMES, CANDLE_LIMIT

logger = logging.getLogger(__name__)


class MarketDataFetcher:
    def __init__(self):
        exchange_class = getattr(ccxt, EXCHANGE_ID)
        self.exchange = exchange_class({
            "enableRateLimit": True,
            "options": {"defaultType": EXCHANGE_TYPE},
        })

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = CANDLE_LIMIT) -> Optional[pd.DataFrame]:
        try:
            raw = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            if not raw or len(raw) < 50:
                return None
            df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df = df.set_index("timestamp").astype(float)
            return df
        except Exception as e:
            logger.warning(f"Failed to fetch {symbol} {timeframe}: {e}")
            return None

    def fetch_all_timeframes(self, symbol: str) -> Dict[str, pd.DataFrame]:
        data = {}
        for tf in TIMEFRAMES:
            df = self.fetch_ohlcv(symbol, tf)
            if df is not None:
                data[tf] = df
            time.sleep(0.12)
        return data

    def fetch_funding_rate(self, symbol: str) -> Optional[float]:
        try:
            funding = self.exchange.fetch_funding_rate(symbol)
            return funding.get("fundingRate")
        except Exception as e:
            logger.warning(f"Funding rate unavailable for {symbol}: {e}")
            return None

    def fetch_open_interest(self, symbol: str) -> Optional[float]:
        try:
            oi = self.exchange.fetch_open_interest(symbol)
            return oi.get("openInterestAmount")
        except Exception as e:
            logger.warning(f"OI unavailable for {symbol}: {e}")
            return None

    def fetch_ticker(self, symbol: str) -> Optional[Dict]:
        try:
            return self.exchange.fetch_ticker(symbol)
        except Exception as e:
            logger.warning(f"Ticker unavailable for {symbol}: {e}")
            return None
