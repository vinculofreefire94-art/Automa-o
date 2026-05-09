"""
main.py — Orquestrador principal do BTC Signal Bot
Combina: Fetcher → Analyzer → ChartGenerator → TelegramSender
"""
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

# ── Imports internos ────────────────────────────────────────────────────────
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from core.config import Config
from core.fetcher import DataFetcher
from core.analyzer import TechnicalAnalyzer, SIGNAL_NEUTRAL
from charts.generator import EliteChartGenerator
from telegram.sender import TelegramSender

# ── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if Config.DEBUG else logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("main")


# ─────────────────────────────────────────────────────────────────────────────
#  Orquestrador
# ─────────────────────────────────────────────────────────────────────────────

class SignalBot:
    def __init__(self):
        self.fetcher   = DataFetcher()
        self.analyzer  = TechnicalAnalyzer()
        self.charter   = EliteChartGenerator()
        self.sender    = TelegramSender()
        self.scheduler = AsyncIOScheduler(timezone="UTC")

        self._scan_count  = 0
        self._signal_count = 0
        self._last_signals: dict[str, tuple[str, datetime]] = {}  # Evita duplicatas

    # ── Scan Principal ───────────────────────────────────────────────────────

    async def scan(self):
        """Executa um ciclo completo de análise para todos os pares."""
        self._scan_count += 1
        logger.info(f"═══ SCAN #{self._scan_count} — {datetime.utcnow():%H:%M:%S UTC} ═══")

        for symbol in Config.PAIRS:
            try:
                await self._analyze_pair(symbol)
            except Exception as e:
                logger.error(f"Erro ao analisar {symbol}: {e}", exc_info=True)
                await self.sender.send_error(f"{symbol}: {e}")

    async def _analyze_pair(self, symbol: str):
        logger.info(f"  Analisando {symbol}...")

        # Busca dados em múltiplos timeframes
        data: dict[str, any] = {}
        for tf in Config.TIMEFRAMES:
            limit = Config.CHART_CANDLES + 220
            md = self.fetcher.fetch_ohlcv(symbol, tf, limit=limit)
            if md:
                data[tf] = md

        if not data:
            logger.warning(f"  ✗ Sem dados para {symbol}")
            return

        # Tendências de referência
        trend_1d = self._get_trend(data, "1d")
        trend_4h = self._get_trend(data, "4h")

        # Analisa no timeframe primário
        primary_md = data.get(Config.PRIMARY_TF) or next(iter(data.values()))
        signal = self.analyzer.analyze(
            primary_md,
            trend_1d=trend_1d,
            trend_4h=trend_4h,
        )

        logger.info(
            f"  {symbol} [{Config.PRIMARY_TF}] → "
            f"{signal.direction} | Score {signal.score:.0f} | "
            f"Força {signal.strength}"
        )

        # Filtro: ignora neutro e sinais fracos (se configurado)
        if signal.direction == SIGNAL_NEUTRAL:
            logger.debug(f"  ↳ Sinal neutro — ignorado")
            return

        if not Config.SEND_ALL_SIGNALS and signal.strength < Config.MIN_SIGNAL_STRENGTH:
            logger.debug(f"  ↳ Força {signal.strength} abaixo do mínimo — ignorado")
            return

        # Anti-duplicata: evita reenviar o mesmo sinal em < 2h
        key = f"{symbol}::{Config.PRIMARY_TF}"
        last_dir, last_ts = self._last_signals.get(key, (None, None))
        if last_dir == signal.direction and last_ts:
            elapsed = (datetime.utcnow() - last_ts).total_seconds() / 3600
            if elapsed < 2.0:
                logger.debug(f"  ↳ Sinal repetido ({elapsed:.1f}h atrás) — ignorado")
                return

        # Gera gráfico
        chart_bytes = self.charter.generate(signal, primary_md.df)
        if chart_bytes:
            logger.info(f"  ↳ Gráfico gerado ({len(chart_bytes)/1024:.0f} KB)")
        else:
            logger.warning(f"  ↳ Falha ao gerar gráfico")

        # Envia para Telegram
        sent = await self.sender.send_signal(signal, chart_bytes)
        if sent:
            self._signal_count += 1
            self._last_signals[key] = (signal.direction, datetime.utcnow())
            logger.info(f"  ✅ Sinal enviado com sucesso!")

    def _get_trend(self, data: dict, tf: str) -> str:
        md = data.get(tf)
        if not md:
            return "neutral"
        df = md.df
        if f"ema{Config.EMA_TREND}" in df.columns:
            ema200 = float(df[f"ema{Config.EMA_TREND}"].iloc[-1])
            price = float(df["close"].iloc[-1])
            return "bullish" if price > ema200 else "bearish"
        return "neutral"

    # ── Heartbeat ────────────────────────────────────────────────────────────

    async def heartbeat(self):
        await self.sender.send_heartbeat(self._scan_count, self._signal_count)

    # ── Start ────────────────────────────────────────────────────────────────

    async def start(self):
        logger.info("🚀 BTC Signal Bot iniciando...")

        # Valida configuração
        errors = Config.validate()
        if errors:
            for e in errors:
                logger.critical(f"  ✗ {e}")
            sys.exit(1)

        logger.info(f"  Pares:      {Config.PAIRS}")
        logger.info(f"  Timeframes: {Config.TIMEFRAMES}")
        logger.info(f"  Interval:   {Config.SCAN_INTERVAL}min")
        logger.info(f"  DRY RUN:    {Config.DRY_RUN}")

        # Mensagem de startup no Telegram
        await self.sender.send_startup()

        # Primeiro scan imediato
        await self.scan()

        # Scheduler
        self.scheduler.add_job(
            self.scan,
            trigger=IntervalTrigger(minutes=Config.SCAN_INTERVAL),
            id="scan",
            name="Market Scan",
            max_instances=1,
            coalesce=True,
        )
        # Heartbeat a cada 6h
        self.scheduler.add_job(
            self.heartbeat,
            trigger=IntervalTrigger(hours=6),
            id="heartbeat",
            name="Heartbeat",
        )

        self.scheduler.start()
        logger.info(f"✅ Scheduler iniciado — próximo scan em {Config.SCAN_INTERVAL} min")

        # Loop infinito
        try:
            while True:
                await asyncio.sleep(60)
        except (KeyboardInterrupt, SystemExit):
            logger.info("🛑 Bot encerrado pelo utilizador.")
            self.scheduler.shutdown()


# ─────────────────────────────────────────────────────────────────────────────
#  Entry Point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    bot = SignalBot()
    asyncio.run(bot.start())
