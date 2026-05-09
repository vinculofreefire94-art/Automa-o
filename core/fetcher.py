"""
fetcher.py — Busca dados de mercado via ccxt com cache inteligente
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional

import ccxt
import pandas as pd

from core.config import Config

logger = logging.getLogger(__name__)


class MarketData:
    """Encapsula os dados de mercado para um par/timeframe."""

    def __init__(self, symbol: str, timeframe: str, df: pd.DataFrame):
        self.symbol = symbol
        self.timeframe = timeframe
        self.df = df
        self.fetched_at = datetime.utcnow()

    @property
    def latest(self) -> pd.Series:
        return self.df.iloc[-1]

    @property
    def price(self) -> float:
        return float(self.df["close"].iloc[-1])

    @property
    def volume(self) -> float:
        return float(self.df["volume"].iloc[-1])


class DataFetcher:
    """Gerencia conexão com exchange e busca de candles OHLCV."""

    _OHLCV_COLS = ["timestamp", "open", "high", "low", "close", "volume"]

    def __init__(self):
        exchange_class = getattr(ccxt, Config.EXCHANGE)
        self.exchange: ccxt.Exchange = exchange_class(
            {
                "apiKey": Config.API_KEY or None,
                "secret": Config.API_SECRET or None,
                "enableRateLimit": True,
                "options": {"defaultType": "spot"},
            }
        )
        self._cache: dict[str, MarketData] = {}

    def _cache_key(self, symbol: str, timeframe: str) -> str:
        return f"{symbol}::{timeframe}"

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "4h",
        limit: int = 300,
    ) -> Optional[MarketData]:
        """Busca candles e retorna MarketData com DataFrame enriquecido."""
        try:
            raw = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            if not raw or len(raw) < 50:
                logger.warning(f"Dados insuficientes para {symbol} [{timeframe}]")
                return None

            df = pd.DataFrame(raw, columns=self._OHLCV_COLS)
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df = df.set_index("timestamp")
            df = df.astype(float)

            md = MarketData(symbol, timeframe, df)
            self._cache[self._cache_key(symbol, timeframe)] = md
            logger.info(f"✅ {symbol} [{timeframe}] — {len(df)} candles carregados")
            return md

        except ccxt.NetworkError as e:
            logger.error(f"Erro de rede ao buscar {symbol}: {e}")
        except ccxt.ExchangeError as e:
            logger.error(f"Erro da exchange para {symbol}: {e}")
        except Exception as e:
            logger.error(f"Erro inesperado em fetch_ohlcv({symbol}): {e}")
        return None

    def fetch_ticker(self, symbol: str) -> Optional[dict]:
        """Busca ticker atual (bid/ask/last/vol 24h)."""
        try:
            return self.exchange.fetch_ticker(symbol)
        except Exception as e:
            logger.error(f"Erro ao buscar ticker de {symbol}: {e}")
            return None

    def fetch_all_pairs(self) -> dict[str, dict[str, MarketData]]:
        """Busca todos os pares em todos os timeframes configurados."""
        result: dict[str, dict[str, MarketData]] = {}
        for symbol in Config.PAIRS:
            result[symbol] = {}
            for tf in Config.TIMEFRAMES:
                md = self.fetch_ohlcv(symbol, tf, limit=Config.CHART_CANDLES + 200)
                if md:
                    result[symbol][tf] = md
        return result
