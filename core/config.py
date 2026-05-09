"""
config.py — Centraliza todas as configurações do bot
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ── Telegram ────────────────────────────────────────────────────────────
    TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
    TELEGRAM_ADMIN_ID: str = os.getenv("TELEGRAM_ADMIN_ID", "")

    # ── Exchange ─────────────────────────────────────────────────────────────
    EXCHANGE: str = os.getenv("EXCHANGE", "binance")
    API_KEY: str = os.getenv("API_KEY", "")
    API_SECRET: str = os.getenv("API_SECRET", "")

    # ── Pares & Timeframes ──────────────────────────────────────────────────
    PAIRS: list[str] = os.getenv("PAIRS", "BTC/USDT,BTC/EUR,BTC/USDC").split(",")
    TIMEFRAMES: list[str] = os.getenv("TIMEFRAMES", "1h,4h,1d").split(",")
    PRIMARY_TF: str = "4h"

    # ── Scheduler ────────────────────────────────────────────────────────────
    SCAN_INTERVAL: int = int(os.getenv("SCAN_INTERVAL_MINUTES", "15"))

    # ── Sinais ───────────────────────────────────────────────────────────────
    MIN_SIGNAL_STRENGTH: int = int(os.getenv("MIN_SIGNAL_STRENGTH", "2"))
    SEND_ALL_SIGNALS: bool = os.getenv("SEND_ALL_SIGNALS", "true").lower() == "true"

    # ── Gráfico ──────────────────────────────────────────────────────────────
    CHART_STYLE: str = os.getenv("CHART_STYLE", "dark")
    CHART_CANDLES: int = int(os.getenv("CHART_CANDLES", "100"))

    # ── Sistema ──────────────────────────────────────────────────────────────
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    DRY_RUN: bool = os.getenv("DRY_RUN", "true").lower() == "true"

    # ── Parâmetros dos Indicadores ───────────────────────────────────────────
    RSI_PERIOD: int = 14
    RSI_OVERSOLD: float = 35.0
    RSI_OVERBOUGHT: float = 65.0

    EMA_FAST: int = 9
    EMA_MID: int = 21
    EMA_SLOW: int = 50
    EMA_TREND: int = 200

    MACD_FAST: int = 12
    MACD_SLOW: int = 26
    MACD_SIGNAL: int = 9

    BB_PERIOD: int = 20
    BB_STD: float = 2.0

    STOCH_K: int = 14
    STOCH_D: int = 3
    STOCH_SMOOTH: int = 3

    ATR_PERIOD: int = 14
    VOLUME_MA_PERIOD: int = 20

    # ── Risk Management ──────────────────────────────────────────────────────
    TP_MULTIPLIER: float = 2.0
    SL_MULTIPLIER: float = 1.0

    @classmethod
    def validate(cls) -> list[str]:
        errors = []
        if not cls.TELEGRAM_TOKEN:
            errors.append("TELEGRAM_BOT_TOKEN não configurado")
        if not cls.TELEGRAM_CHAT_ID:
            errors.append("TELEGRAM_CHAT_ID não configurado")
        return errors
