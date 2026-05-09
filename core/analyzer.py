"""
analyzer.py — Motor de análise técnica multi-indicador
Indicadores: RSI, MACD, EMA 9/21/50/200, BB, Stochastic, ATR, OBV, VWAP, Volume
"""
import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
import pandas_ta as ta

from core.config import Config
from core.fetcher import MarketData

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
#  Tipos de Sinal
# ─────────────────────────────────────────────────────────────────────────────

SIGNAL_BUY = "BUY"
SIGNAL_SELL = "SELL"
SIGNAL_NEUTRAL = "NEUTRAL"

STRENGTH_WEAK = 1
STRENGTH_MEDIUM = 2
STRENGTH_STRONG = 3
STRENGTH_ULTRA = 4


# ─────────────────────────────────────────────────────────────────────────────
#  Resultado da Análise
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class IndicatorSnapshot:
    """Snapshot de todos os indicadores calculados."""
    rsi: float = 0.0
    macd: float = 0.0
    macd_signal: float = 0.0
    macd_hist: float = 0.0
    macd_cross: str = "none"          # bullish_cross | bearish_cross | none

    ema9: float = 0.0
    ema21: float = 0.0
    ema50: float = 0.0
    ema200: float = 0.0
    ema_trend: str = "neutral"        # bullish | bearish | neutral

    bb_upper: float = 0.0
    bb_mid: float = 0.0
    bb_lower: float = 0.0
    bb_pct: float = 0.0               # 0=lower 1=upper
    bb_squeeze: bool = False

    stoch_k: float = 0.0
    stoch_d: float = 0.0
    stoch_cross: str = "none"

    atr: float = 0.0
    atr_pct: float = 0.0              # ATR como % do preço
    volume_ratio: float = 0.0        # vol atual vs média
    obv_trend: str = "neutral"        # rising | falling | neutral

    support: float = 0.0
    resistance: float = 0.0
    near_support: bool = False
    near_resistance: bool = False

    candle_pattern: str = "none"      # hammer, shooting_star, engulfing...

    price: float = 0.0
    price_change_pct: float = 0.0


@dataclass
class TradingSignal:
    """Sinal de trading completo com todos os dados necessários."""
    symbol: str
    timeframe: str
    direction: str               # BUY | SELL | NEUTRAL
    strength: int                # 1-4
    score: float                 # 0-100
    price: float
    entry: float
    take_profit: float
    stop_loss: float
    rr_ratio: float              # Risk/Reward
    indicators: IndicatorSnapshot = field(default_factory=IndicatorSnapshot)
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    trend_1d: str = "neutral"
    trend_4h: str = "neutral"
    market_phase: str = "accumulation"   # accumulation | markup | distribution | markdown

    @property
    def is_valid(self) -> bool:
        return self.direction != SIGNAL_NEUTRAL and self.strength >= Config.MIN_SIGNAL_STRENGTH

    @property
    def strength_label(self) -> str:
        return {1: "FRACO", 2: "MÉDIO", 3: "FORTE", 4: "ULTRA"}.get(self.strength, "?")

    @property
    def strength_stars(self) -> str:
        return "⭐" * self.strength

    @property
    def direction_emoji(self) -> str:
        return "🟢" if self.direction == SIGNAL_BUY else "🔴"


# ─────────────────────────────────────────────────────────────────────────────
#  Motor de Análise
# ─────────────────────────────────────────────────────────────────────────────

class TechnicalAnalyzer:
    """Calcula indicadores e gera sinais de trading."""

    def __init__(self):
        self.cfg = Config()

    def analyze(
        self,
        md: MarketData,
        trend_1d: Optional[str] = None,
        trend_4h: Optional[str] = None,
    ) -> TradingSignal:
        df = md.df.copy()
        df = self._compute_indicators(df)

        snap = self._build_snapshot(df)
        signal = self._generate_signal(snap, md.symbol, md.timeframe, df)

        signal.trend_1d = trend_1d or self._detect_trend(df)
        signal.trend_4h = trend_4h or signal.trend_1d
        signal.market_phase = self._detect_phase(df)

        # TP / SL dinâmicos por ATR
        atr = snap.atr
        if signal.direction == SIGNAL_BUY:
            signal.entry = snap.price
            signal.take_profit = round(snap.price + atr * Config.TP_MULTIPLIER, 2)
            signal.stop_loss = round(snap.price - atr * Config.SL_MULTIPLIER, 2)
        elif signal.direction == SIGNAL_SELL:
            signal.entry = snap.price
            signal.take_profit = round(snap.price - atr * Config.TP_MULTIPLIER, 2)
            signal.stop_loss = round(snap.price + atr * Config.SL_MULTIPLIER, 2)
        else:
            signal.entry = snap.price
            signal.take_profit = snap.price
            signal.stop_loss = snap.price

        potential = abs(signal.take_profit - signal.entry)
        risk = abs(signal.stop_loss - signal.entry)
        signal.rr_ratio = round(potential / risk, 2) if risk > 0 else 0.0

        return signal

    # ── Indicadores ─────────────────────────────────────────────────────────

    def _compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        c = Config

        # RSI
        df["rsi"] = ta.rsi(df["close"], length=c.RSI_PERIOD)

        # MACD
        macd = ta.macd(df["close"], fast=c.MACD_FAST, slow=c.MACD_SLOW, signal=c.MACD_SIGNAL)
        if macd is not None and not macd.empty:
            df["macd"] = macd.iloc[:, 0]
            df["macd_signal"] = macd.iloc[:, 2]
            df["macd_hist"] = macd.iloc[:, 1]

        # EMAs
        df[f"ema{c.EMA_FAST}"] = ta.ema(df["close"], length=c.EMA_FAST)
        df[f"ema{c.EMA_MID}"] = ta.ema(df["close"], length=c.EMA_MID)
        df[f"ema{c.EMA_SLOW}"] = ta.ema(df["close"], length=c.EMA_SLOW)
        df[f"ema{c.EMA_TREND}"] = ta.ema(df["close"], length=c.EMA_TREND)

        # Bollinger Bands
        bb = ta.bbands(df["close"], length=c.BB_PERIOD, std=c.BB_STD)
        if bb is not None and not bb.empty:
            df["bb_lower"] = bb.iloc[:, 0]
            df["bb_mid"] = bb.iloc[:, 1]
            df["bb_upper"] = bb.iloc[:, 2]
            df["bb_pct"] = bb.iloc[:, 4]   # BBP

        # Stochastic
        stoch = ta.stoch(df["high"], df["low"], df["close"],
                         k=c.STOCH_K, d=c.STOCH_D, smooth_k=c.STOCH_SMOOTH)
        if stoch is not None and not stoch.empty:
            df["stoch_k"] = stoch.iloc[:, 0]
            df["stoch_d"] = stoch.iloc[:, 1]

        # ATR
        df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=c.ATR_PERIOD)

        # Volume MA & ratio
        df["vol_ma"] = ta.sma(df["volume"], length=c.VOLUME_MA_PERIOD)
        df["vol_ratio"] = df["volume"] / df["vol_ma"]

        # OBV
        df["obv"] = ta.obv(df["close"], df["volume"])

        # Candlestick patterns via pandas_ta
        try:
            cdl = ta.cdl_pattern(df["open"], df["high"], df["low"], df["close"],
                                  name="all")
            if cdl is not None and not cdl.empty:
                df = pd.concat([df, cdl], axis=1)
        except Exception:
            pass

        return df

    # ── Snapshot ─────────────────────────────────────────────────────────────

    def _build_snapshot(self, df: pd.DataFrame) -> IndicatorSnapshot:
        s = df.iloc[-1]
        prev = df.iloc[-2]
        c = Config

        snap = IndicatorSnapshot()
        snap.price = float(s["close"])
        snap.price_change_pct = float((s["close"] - prev["close"]) / prev["close"] * 100)

        # RSI
        snap.rsi = float(s.get("rsi", 50))

        # MACD
        snap.macd = float(s.get("macd", 0))
        snap.macd_signal = float(s.get("macd_signal", 0))
        snap.macd_hist = float(s.get("macd_hist", 0))
        prev_hist = float(prev.get("macd_hist", 0))
        if snap.macd_hist > 0 and prev_hist <= 0:
            snap.macd_cross = "bullish_cross"
        elif snap.macd_hist < 0 and prev_hist >= 0:
            snap.macd_cross = "bearish_cross"

        # EMAs
        snap.ema9 = float(s.get(f"ema{c.EMA_FAST}", snap.price))
        snap.ema21 = float(s.get(f"ema{c.EMA_MID}", snap.price))
        snap.ema50 = float(s.get(f"ema{c.EMA_SLOW}", snap.price))
        snap.ema200 = float(s.get(f"ema{c.EMA_TREND}", snap.price))

        bullish_stack = (snap.ema9 > snap.ema21 > snap.ema50 > snap.ema200
                         and snap.price > snap.ema200)
        bearish_stack = (snap.ema9 < snap.ema21 < snap.ema50 < snap.ema200
                         and snap.price < snap.ema200)
        snap.ema_trend = "bullish" if bullish_stack else "bearish" if bearish_stack else "neutral"

        # Bollinger
        snap.bb_upper = float(s.get("bb_upper", snap.price * 1.02))
        snap.bb_mid = float(s.get("bb_mid", snap.price))
        snap.bb_lower = float(s.get("bb_lower", snap.price * 0.98))
        snap.bb_pct = float(s.get("bb_pct", 0.5))
        bb_width = snap.bb_upper - snap.bb_lower
        avg_width = float(df["bb_upper"].tail(20).mean() - df["bb_lower"].tail(20).mean()) if "bb_upper" in df else bb_width
        snap.bb_squeeze = bb_width < avg_width * 0.7

        # Stochastic
        snap.stoch_k = float(s.get("stoch_k", 50))
        snap.stoch_d = float(s.get("stoch_d", 50))
        prev_k = float(prev.get("stoch_k", 50))
        prev_d = float(prev.get("stoch_d", 50))
        if snap.stoch_k > snap.stoch_d and prev_k <= prev_d:
            snap.stoch_cross = "bullish"
        elif snap.stoch_k < snap.stoch_d and prev_k >= prev_d:
            snap.stoch_cross = "bearish"

        # ATR
        snap.atr = float(s.get("atr", snap.price * 0.02))
        snap.atr_pct = snap.atr / snap.price * 100

        # Volume
        snap.volume_ratio = float(s.get("vol_ratio", 1.0))

        # OBV trend
        if "obv" in df.columns:
            obv_series = df["obv"].tail(10)
            obv_slope = float(np.polyfit(range(len(obv_series)), obv_series.values, 1)[0])
            snap.obv_trend = "rising" if obv_slope > 0 else "falling"

        # S/R via pivot points (últimas 20 velas)
        highs = df["high"].tail(50)
        lows = df["low"].tail(50)
        snap.resistance = float(highs.max())
        snap.support = float(lows.min())
        snap.near_support = abs(snap.price - snap.support) / snap.price < 0.015
        snap.near_resistance = abs(snap.price - snap.resistance) / snap.price < 0.015

        # Candlestick pattern detection
        snap.candle_pattern = self._detect_candle_pattern(df)

        return snap

    def _detect_candle_pattern(self, df: pd.DataFrame) -> str:
        """Detecção manual dos padrões mais importantes."""
        o, h, l, c = (df["open"].iloc[-1], df["high"].iloc[-1],
                      df["low"].iloc[-1], df["close"].iloc[-1])
        body = abs(c - o)
        total = h - l
        upper_wick = h - max(o, c)
        lower_wick = min(o, c) - l

        if total == 0:
            return "none"

        body_pct = body / total

        # Doji
        if body_pct < 0.1:
            return "doji"

        # Hammer / Inverted hammer
        if lower_wick > body * 2 and upper_wick < body * 0.5 and c > o:
            return "hammer"
        if upper_wick > body * 2 and lower_wick < body * 0.5 and c < o:
            return "shooting_star"

        # Engulfing
        prev_o, prev_c = df["open"].iloc[-2], df["close"].iloc[-2]
        if c > o and c > prev_o and o < prev_c and prev_c < prev_o:
            return "bullish_engulfing"
        if c < o and c < prev_o and o > prev_c and prev_c > prev_o:
            return "bearish_engulfing"

        # Marubozu
        if body_pct > 0.9 and c > o:
            return "bullish_marubozu"
        if body_pct > 0.9 and c < o:
            return "bearish_marubozu"

        return "none"

    # ── Geração de Sinal ─────────────────────────────────────────────────────

    def _generate_signal(
        self,
        snap: IndicatorSnapshot,
        symbol: str,
        timeframe: str,
        df: pd.DataFrame,
    ) -> TradingSignal:
        buy_score = 0.0
        sell_score = 0.0
        reasons_buy: list[str] = []
        reasons_sell: list[str] = []
        warnings: list[str] = []

        # ── RSI ─────────────────────────────────────────
        if snap.rsi < Config.RSI_OVERSOLD:
            buy_score += 15
            reasons_buy.append(f"RSI sobrevendido ({snap.rsi:.1f})")
        elif snap.rsi > Config.RSI_OVERBOUGHT:
            sell_score += 15
            reasons_sell.append(f"RSI sobrecomprado ({snap.rsi:.1f})")
        elif 40 <= snap.rsi <= 55:
            buy_score += 5   # zona neutra levemente bullish

        # ── MACD ────────────────────────────────────────
        if snap.macd_cross == "bullish_cross":
            buy_score += 20
            reasons_buy.append("MACD cruzamento bullish 🔀")
        elif snap.macd_cross == "bearish_cross":
            sell_score += 20
            reasons_sell.append("MACD cruzamento bearish 🔀")
        elif snap.macd_hist > 0:
            buy_score += 8
        elif snap.macd_hist < 0:
            sell_score += 8

        # ── EMA Stack ───────────────────────────────────
        if snap.ema_trend == "bullish":
            buy_score += 18
            reasons_buy.append("EMAs em stack bullish perfeito")
        elif snap.ema_trend == "bearish":
            sell_score += 18
            reasons_sell.append("EMAs em stack bearish")
        
        # EMA 9/21 cross
        if snap.ema9 > snap.ema21 and snap.price > snap.ema50:
            buy_score += 10
        elif snap.ema9 < snap.ema21 and snap.price < snap.ema50:
            sell_score += 10

        # ── Bollinger Bands ──────────────────────────────
        if snap.bb_pct < 0.1:
            buy_score += 12
            reasons_buy.append("Preço na banda inferior de BB")
        elif snap.bb_pct > 0.9:
            sell_score += 12
            reasons_sell.append("Preço na banda superior de BB")

        if snap.bb_squeeze:
            warnings.append("⚠️ BB Squeeze — breakout iminente")
            buy_score += 5
            sell_score += 5  # Sem direção definida ainda

        # ── Stochastic ───────────────────────────────────
        if snap.stoch_cross == "bullish" and snap.stoch_k < 25:
            buy_score += 15
            reasons_buy.append(f"Stoch cruzamento bullish em zona oversold ({snap.stoch_k:.0f})")
        elif snap.stoch_cross == "bearish" and snap.stoch_k > 75:
            sell_score += 15
            reasons_sell.append(f"Stoch cruzamento bearish em zona overbought ({snap.stoch_k:.0f})")

        # ── Volume ───────────────────────────────────────
        if snap.volume_ratio > 1.8:
            label = f"Volume {snap.volume_ratio:.1f}x acima da média"
            buy_score += 8 if buy_score > sell_score else 0
            sell_score += 8 if sell_score > buy_score else 0
            reasons_buy.append(label) if buy_score > sell_score else reasons_sell.append(label)

        # ── OBV ──────────────────────────────────────────
        if snap.obv_trend == "rising":
            buy_score += 8
        elif snap.obv_trend == "falling":
            sell_score += 8

        # ── Suporte / Resistência ─────────────────────────
        if snap.near_support:
            buy_score += 10
            reasons_buy.append(f"Preço próximo ao suporte (${snap.support:,.2f})")
        if snap.near_resistance:
            sell_score += 10
            reasons_sell.append(f"Preço próximo à resistência (${snap.resistance:,.2f})")

        # ── Candlestick Patterns ─────────────────────────
        pattern = snap.candle_pattern
        bullish_candles = {"hammer", "bullish_engulfing", "bullish_marubozu"}
        bearish_candles = {"shooting_star", "bearish_engulfing", "bearish_marubozu"}
        neutral_candles = {"doji"}

        if pattern in bullish_candles:
            buy_score += 12
            reasons_buy.append(f"Padrão de candle: {pattern.replace('_', ' ').title()}")
        elif pattern in bearish_candles:
            sell_score += 12
            reasons_sell.append(f"Padrão de candle: {pattern.replace('_', ' ').title()}")
        elif pattern in neutral_candles:
            warnings.append(f"Doji detectado — indecisão no mercado")

        # ── ATR Volatilidade ─────────────────────────────
        if snap.atr_pct > 5:
            warnings.append(f"⚡ Alta volatilidade (ATR {snap.atr_pct:.1f}%)")

        # ── Decisão Final ─────────────────────────────────
        max_score = 100.0
        net_score = buy_score - sell_score

        if buy_score > sell_score:
            direction = SIGNAL_BUY
            score = min(buy_score, max_score)
            reasons = reasons_buy
        elif sell_score > buy_score:
            direction = SIGNAL_SELL
            score = min(sell_score, max_score)
            reasons = reasons_sell
        else:
            direction = SIGNAL_NEUTRAL
            score = 50.0
            reasons = []

        # ── Força do Sinal ─────────────────────────────────
        if score >= 75:
            strength = STRENGTH_ULTRA
        elif score >= 60:
            strength = STRENGTH_STRONG
        elif score >= 40:
            strength = STRENGTH_MEDIUM
        else:
            strength = STRENGTH_WEAK

        return TradingSignal(
            symbol=symbol,
            timeframe=timeframe,
            direction=direction,
            strength=strength,
            score=round(score, 1),
            price=snap.price,
            entry=snap.price,
            take_profit=snap.price,
            stop_loss=snap.price,
            rr_ratio=0.0,
            indicators=snap,
            reasons=reasons,
            warnings=warnings,
        )

    def _detect_trend(self, df: pd.DataFrame) -> str:
        if "ema200" not in df.columns and f"ema{Config.EMA_TREND}" not in df.columns:
            return "neutral"
        col = f"ema{Config.EMA_TREND}"
        if col not in df.columns:
            return "neutral"
        price = float(df["close"].iloc[-1])
        ema200 = float(df[col].iloc[-1])
        return "bullish" if price > ema200 else "bearish"

    def _detect_phase(self, df: pd.DataFrame) -> str:
        """Identifica fase de mercado via Wyckoff simplificado."""
        close = df["close"].tail(50)
        rsi_latest = float(df["rsi"].iloc[-1]) if "rsi" in df else 50
        vol_ratio = float(df["vol_ratio"].iloc[-1]) if "vol_ratio" in df else 1

        slope = float(np.polyfit(range(len(close)), close.values, 1)[0])
        price_range = close.max() - close.min()

        if slope > 0 and rsi_latest > 55:
            return "markup"
        elif slope < 0 and rsi_latest < 45:
            return "markdown"
        elif vol_ratio > 1.5 and price_range / close.mean() < 0.05:
            return "distribution" if rsi_latest > 60 else "accumulation"
        return "accumulation"
