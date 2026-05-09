"""
sender.py — Formata e envia sinais para o Telegram com emojis profissionais
"""
import logging
from datetime import datetime
from typing import Optional

from telegram import Bot, InputMediaPhoto
from telegram.constants import ParseMode
from telegram.error import TelegramError

from core.analyzer import TradingSignal, SIGNAL_BUY, SIGNAL_SELL, SIGNAL_NEUTRAL
from core.config import Config

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
#  Mapeamentos de Emoji
# ─────────────────────────────────────────────────────────────────────────────

DIRECTION_EMOJI = {
    SIGNAL_BUY:     "🟢",
    SIGNAL_SELL:    "🔴",
    SIGNAL_NEUTRAL: "⚪",
}

DIRECTION_LABEL = {
    SIGNAL_BUY:     "COMPRA  📈",
    SIGNAL_SELL:    "VENDA   📉",
    SIGNAL_NEUTRAL: "NEUTRO  ⚪",
}

STRENGTH_EMOJI = {
    1: "🔹",
    2: "🔷",
    3: "💎",
    4: "🚀",
}

STRENGTH_LABEL = {
    1: "FRACO",
    2: "MÉDIO",
    3: "FORTE",
    4: "ULTRA FORTE",
}

STRENGTH_BAR = {
    1: "▓░░░",
    2: "▓▓░░",
    3: "▓▓▓░",
    4: "▓▓▓▓",
}

TIMEFRAME_LABEL = {
    "1m": "1 Minuto",
    "5m": "5 Minutos",
    "15m": "15 Minutos",
    "1h": "1 Hora",
    "4h": "4 Horas",
    "1d": "Diário",
    "1w": "Semanal",
}

TREND_EMOJI = {
    "bullish": "📈",
    "bearish": "📉",
    "neutral": "➡️",
}

PHASE_EMOJI = {
    "markup": "🚀",
    "markdown": "💣",
    "accumulation": "🔄",
    "distribution": "🏦",
}

PAIR_FLAG = {
    "BTC/USDT": "₿ • USDT",
    "BTC/EUR":  "₿ • EUR 🇪🇺",
    "BTC/USDC": "₿ • USDC",
}

RSI_LABEL = lambda r: (
    "🔥 Extremamente Sobrecomprado" if r > 80 else
    "⚠️ Sobrecomprado" if r > 65 else
    "🧊 Extremamente Sobrevendido" if r < 20 else
    "✅ Sobrevendido" if r < 35 else
    "⚖️ Neutro"
)

OBV_EMOJI = {"rising": "📊↑", "falling": "📊↓", "neutral": "📊→"}


# ─────────────────────────────────────────────────────────────────────────────
#  Formatador de Mensagem
# ─────────────────────────────────────────────────────────────────────────────

class SignalFormatter:
    """Formata TradingSignal em mensagem Markdown para Telegram."""

    def format(self, signal: TradingSignal) -> str:
        ind = signal.indicators
        ts = datetime.utcnow().strftime("%d/%m/%Y  %H:%M UTC")
        dir_emoji = DIRECTION_EMOJI.get(signal.direction, "⚪")
        strength_emoji = STRENGTH_EMOJI.get(signal.strength, "🔹")
        strength_bar = STRENGTH_BAR.get(signal.strength, "░░░░")
        strength_label = STRENGTH_LABEL.get(signal.strength, "?")
        pair_label = PAIR_FLAG.get(signal.symbol, signal.symbol)
        tf_label = TIMEFRAME_LABEL.get(signal.timeframe, signal.timeframe)
        direction_label = DIRECTION_LABEL.get(signal.direction, signal.direction)
        trend1d_emoji = TREND_EMOJI.get(signal.trend_1d, "➡️")
        trend4h_emoji = TREND_EMOJI.get(signal.trend_4h, "➡️")
        phase_emoji = PHASE_EMOJI.get(signal.market_phase, "🔄")
        obv_emoji = OBV_EMOJI.get(ind.obv_trend, "📊→")
        rsi_label = RSI_LABEL(ind.rsi)

        # Score bar visual
        score_filled = int(signal.score / 10)
        score_bar = "█" * score_filled + "░" * (10 - score_filled)

        # Razões do sinal
        reasons_block = ""
        if signal.reasons:
            reasons_block = "\n".join(
                f"   ├─ ✦ {r}" for r in signal.reasons[:5]
            )
        else:
            reasons_block = "   └─ Análise técnica composta"

        # Avisos
        warnings_block = ""
        if signal.warnings:
            warnings_block = "\n".join(
                f"   ⚠️ {w}" for w in signal.warnings
            )
            warnings_block = f"\n\n*Avisos*\n{warnings_block}"

        # Cabeçalho dinâmico por direção
        if signal.direction == SIGNAL_BUY:
            header = "🔔 *SINAL DE COMPRA DETECTADO*"
            action_block = (
                f"╔══════════════════════════╗\n"
                f"║  💰 ENTRADA     `${signal.entry:>12,.2f}`  ║\n"
                f"║  🎯 TAKE PROFIT `${signal.take_profit:>12,.2f}`  ║\n"
                f"║  🛡️ STOP LOSS   `${signal.stop_loss:>12,.2f}`  ║\n"
                f"║  📐 RISCO/RET   `{signal.rr_ratio:>14.2f}x`  ║\n"
                f"╚══════════════════════════╝"
            )
        elif signal.direction == SIGNAL_SELL:
            header = "🔔 *SINAL DE VENDA DETECTADO*"
            action_block = (
                f"╔══════════════════════════╗\n"
                f"║  💸 ENTRADA     `${signal.entry:>12,.2f}`  ║\n"
                f"║  🎯 TAKE PROFIT `${signal.take_profit:>12,.2f}`  ║\n"
                f"║  🛡️ STOP LOSS   `${signal.stop_loss:>12,.2f}`  ║\n"
                f"║  📐 RISCO/RET   `{signal.rr_ratio:>14.2f}x`  ║\n"
                f"╚══════════════════════════╝"
            )
        else:
            header = "📡 *ANÁLISE DE MERCADO*"
            action_block = "_Sem posição recomendada neste momento._"

        msg = f"""
{header}
━━━━━━━━━━━━━━━━━━━━━━━━━━━

{dir_emoji} *{direction_label}*
{strength_emoji} Força: *{strength_label}*  `[{strength_bar}]`

*Par*        `{pair_label}`
*Timeframe*  `{tf_label}`
*Preço*      `${signal.price:,.2f}`

───────────────────────────
📊 *Score de Confiança*
`{score_bar}` `{signal.score:.0f}/100`

───────────────────────────
🏗️ *Contexto de Mercado*
  {trend1d_emoji} Tendência D1:  `{signal.trend_1d.upper()}`
  {trend4h_emoji} Tendência 4H:  `{signal.trend_4h.upper()}`
  {phase_emoji} Fase:           `{signal.market_phase.upper()}`

───────────────────────────
📈 *Indicadores*
  `RSI    {ind.rsi:5.1f}`  {rsi_label}
  `MACD   {'↑ Bullish' if ind.macd_hist > 0 else '↓ Bearish':12}`  `{ind.macd_cross.replace('_', ' ').title()}`
  `EMA    {ind.ema_trend.upper():12}`
  `Stoch  K:{ind.stoch_k:4.0f}  D:{ind.stoch_d:4.0f}`
  `ATR    {ind.atr_pct:.2f}%  ({'Alta' if ind.atr_pct > 4 else 'Normal'} volatilidade)`
  `Vol    {ind.volume_ratio:.1f}x`  {obv_emoji}
  `BB     {ind.bb_pct*100:.0f}%`  {'← Banda inferior' if ind.bb_pct < 0.2 else '→ Banda superior' if ind.bb_pct > 0.8 else 'Zona central'}
  `S/R    ${ind.support:,.0f} / ${ind.resistance:,.0f}`
{'  ⚡ BB SQUEEZE' if ind.bb_squeeze else ''}

───────────────────────────
🎯 *Razões do Sinal*
{reasons_block}
{warnings_block}

───────────────────────────
{action_block}

───────────────────────────
🕐 `{ts}`
🤖 _BTC Signal Bot — Alpha Edition_
""".strip()

        return msg

    def format_startup(self) -> str:
        ts = datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC")
        pairs = "\n".join(f"   • `{p}`" for p in Config.PAIRS)
        tfs = " | ".join(f"`{t}`" for t in Config.TIMEFRAMES)
        return f"""
🚀 *BTC SIGNAL BOT INICIADO*
━━━━━━━━━━━━━━━━━━━━━━━━

📡 *Pares Monitorados:*
{pairs}

⏱️ *Timeframes:* {tfs}
🔄 *Scan:* a cada `{Config.SCAN_INTERVAL}` minutos
⚡ *Modo:* `{'DRY RUN' if Config.DRY_RUN else 'LIVE'}`

✅ Sistema online e operacional
🕐 `{ts}`
""".strip()

    def format_error(self, error: str) -> str:
        ts = datetime.utcnow().strftime("%H:%M UTC")
        return f"⚠️ *ERRO NO BOT*\n`{ts}`\n\n```\n{error[:500]}\n```"

    def format_heartbeat(self, scans: int, signals: int) -> str:
        ts = datetime.utcnow().strftime("%d/%m %H:%M UTC")
        return (
            f"💓 *HEARTBEAT*\n"
            f"`{ts}`\n"
            f"Scans: `{scans}` · Sinais: `{signals}`"
        )


# ─────────────────────────────────────────────────────────────────────────────
#  Sender
# ─────────────────────────────────────────────────────────────────────────────

class TelegramSender:
    """Envia mensagens e gráficos para o Telegram."""

    def __init__(self):
        self.bot = Bot(token=Config.TELEGRAM_TOKEN)
        self.chat_id = Config.TELEGRAM_CHAT_ID
        self.admin_id = Config.TELEGRAM_ADMIN_ID or Config.TELEGRAM_CHAT_ID
        self.formatter = SignalFormatter()

    async def send_signal(
        self,
        signal: TradingSignal,
        chart_bytes: Optional[bytes] = None,
    ) -> bool:
        """Envia o sinal com ou sem gráfico."""
        message = self.formatter.format(signal)
        try:
            if chart_bytes:
                await self.bot.send_photo(
                    chat_id=self.chat_id,
                    photo=chart_bytes,
                    caption=message,
                    parse_mode=ParseMode.MARKDOWN,
                )
            else:
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=message,
                    parse_mode=ParseMode.MARKDOWN,
                )
            logger.info(f"✅ Sinal enviado: {signal.symbol} {signal.direction}")
            return True
        except TelegramError as e:
            logger.error(f"Erro Telegram ao enviar sinal: {e}")
            return False

    async def send_startup(self) -> None:
        msg = self.formatter.format_startup()
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=msg,
                parse_mode=ParseMode.MARKDOWN,
            )
        except TelegramError as e:
            logger.error(f"Erro ao enviar startup: {e}")

    async def send_error(self, error: str) -> None:
        msg = self.formatter.format_error(error)
        try:
            await self.bot.send_message(
                chat_id=self.admin_id,
                text=msg,
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception:
            pass

    async def send_heartbeat(self, scans: int, signals: int) -> None:
        msg = self.formatter.format_heartbeat(scans, signals)
        try:
            await self.bot.send_message(
                chat_id=self.admin_id,
                text=msg,
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception:
            pass
