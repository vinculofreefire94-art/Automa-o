"""
charts.py — Geração de gráficos nível elite com tema dark profissional
Estilo: Trading Terminal futurista com gradientes, grid customizado e multi-painel
"""
import io
import logging
from datetime import datetime
from typing import Optional

import matplotlib
matplotlib.use("Agg")  # Backend sem GUI

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyArrowPatch
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

from core.analyzer import TradingSignal, SIGNAL_BUY, SIGNAL_SELL
from core.config import Config

logger = logging.getLogger(__name__)

PALETTE = {
    "bg_main":       "#0A0E1A",
    "bg_panel":      "#0F1629",
    "bg_chart":      "#0B1120",
    "grid":          "#1A2040",
    "text_primary":  "#E8ECFF",
    "text_secondary": "#6B7A99",
    "text_accent":   "#A0B4FF",
    "bull_body":     "#00E676",
    "bull_wick":     "#00E676",
    "bear_body":     "#FF3D57",
    "bear_wick":     "#FF3D57",
    "ema9":          "#FFD600",
    "ema21":         "#FF6D00",
    "ema50":         "#00B0FF",
    "ema200":        "#AA00FF",
    "bb_upper":      "#546E7A",
    "bb_lower":      "#546E7A",
    "bb_fill":       "#1A2535",
    "macd_pos":      "#00E676",
    "macd_neg":      "#FF3D57",
    "macd_line":     "#29B6F6",
    "macd_signal":   "#FFA726",
    "rsi_line":      "#B39DDB",
    "rsi_ob":        "#FF3D57",
    "rsi_os":        "#00E676",
    "vol_bull":      "#1B5E20",
    "vol_bear":      "#B71C1C",
    "signal_buy":    "#00E676",
    "signal_sell":   "#FF3D57",
    "signal_tp":     "#00BCD4",
    "signal_sl":     "#FF9800",
    "border":        "#1E2D50",
}

FONT_FAMILY = "monospace"


class EliteChartGenerator:

    def __init__(self):
        self._setup_matplotlib()

    def _setup_matplotlib(self):
        plt.rcParams.update({
            "figure.facecolor":    PALETTE["bg_main"],
            "axes.facecolor":      PALETTE["bg_chart"],
            "axes.edgecolor":      PALETTE["border"],
            "axes.labelcolor":     PALETTE["text_secondary"],
            "text.color":          PALETTE["text_primary"],
            "xtick.color":         PALETTE["text_secondary"],
            "ytick.color":         PALETTE["text_secondary"],
            "grid.color":          PALETTE["grid"],
            "grid.linewidth":      0.5,
            "grid.alpha":          0.6,
            "font.family":         FONT_FAMILY,
            "font.size":           8,
            "axes.titlesize":      9,
            "axes.labelsize":      8,
            "legend.fontsize":     7,
            "legend.framealpha":   0.15,
            "legend.edgecolor":    PALETTE["border"],
            "legend.facecolor":    PALETTE["bg_panel"],
        })

    def generate(self, signal: TradingSignal, df: pd.DataFrame) -> Optional[bytes]:
        try:
            n = min(Config.CHART_CANDLES, len(df))
            df = df.tail(n).copy()
            df.index = pd.to_datetime(df.index)

            fig = plt.figure(figsize=(16, 11), facecolor=PALETTE["bg_main"])
            fig.patch.set_alpha(1)

            gs = gridspec.GridSpec(
                4, 1,
                figure=fig,
                height_ratios=[6, 2, 2, 1.5],
                hspace=0.04,
                left=0.06, right=0.97,
                top=0.91, bottom=0.06,
            )

            ax_price  = fig.add_subplot(gs[0])
            ax_macd   = fig.add_subplot(gs[1], sharex=ax_price)
            ax_rsi    = fig.add_subplot(gs[2], sharex=ax_price)
            ax_vol    = fig.add_subplot(gs[3], sharex=ax_price)

            self._draw_candles(ax_price, df)
            self._draw_emas(ax_price, df)
            self._draw_bollinger(ax_price, df)
            self._draw_signal_levels(ax_price, signal, df)
            self._style_price_panel(ax_price, signal, df)

            self._draw_macd(ax_macd, df)
            self._draw_rsi(ax_rsi, df)
            self._draw_volume(ax_vol, df)

            plt.setp(ax_price.get_xticklabels(), visible=False)
            plt.setp(ax_macd.get_xticklabels(), visible=False)
            plt.setp(ax_rsi.get_xticklabels(), visible=False)

            self._format_x_axis(ax_vol, df)
            self._draw_header(fig, signal)
            self._draw_footer(fig, signal)

            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=130, bbox_inches="tight",
                        facecolor=PALETTE["bg_main"], edgecolor="none")
            plt.close(fig)
            buf.seek(0)
            return buf.read()

        except Exception as e:
            logger.error(f"Erro ao gerar gráfico: {e}", exc_info=True)
            return None

    def _draw_candles(self, ax, df: pd.DataFrame):
        x = np.arange(len(df))
        for i, (idx, row) in enumerate(df.iterrows()):
            bull = row["close"] >= row["open"]
            color = PALETTE["bull_body"] if bull else PALETTE["bear_body"]
            ax.plot([x[i], x[i]], [row["low"], row["high"]],
                    color=color, linewidth=0.8, alpha=0.9, zorder=2)
            body_bot = min(row["open"], row["close"])
            body_h = abs(row["close"] - row["open"]) or row["close"] * 0.001
            rect = mpatches.FancyBboxPatch(
                (x[i] - 0.35, body_bot), 0.7, body_h,
                boxstyle="square,pad=0",
                facecolor=color, edgecolor=color,
                linewidth=0, alpha=0.95, zorder=3,
            )
            ax.add_patch(rect)

    def _draw_emas(self, ax, df: pd.DataFrame):
        c = Config
        x = np.arange(len(df))
        ema_cfg = [
            (f"ema{c.EMA_FAST}", f"EMA{c.EMA_FAST}", PALETTE["ema9"], 1.2),
            (f"ema{c.EMA_MID}", f"EMA{c.EMA_MID}", PALETTE["ema21"], 1.2),
            (f"ema{c.EMA_SLOW}", f"EMA{c.EMA_SLOW}", PALETTE["ema50"], 1.5),
            (f"ema{c.EMA_TREND}", f"EMA{c.EMA_TREND}", PALETTE["ema200"], 2.0),
        ]
        for col, label, color, lw in ema_cfg:
            if col in df.columns:
                vals = df[col].values
                mask = ~np.isnan(vals)
                if mask.any():
                    ax.plot(x[mask], vals[mask], color=color,
                            linewidth=lw, alpha=0.85, label=label, zorder=4)

    def _draw_bollinger(self, ax, df: pd.DataFrame):
        if "bb_upper" not in df.columns:
            return
        x = np.arange(len(df))
        upper = df["bb_upper"].values
        lower = df["bb_lower"].values
        mid = df["bb_mid"].values
        mask = ~(np.isnan(upper) | np.isnan(lower))
        if not mask.any():
            return
        ax.fill_between(x[mask], upper[mask], lower[mask],
                        color=PALETTE["bb_fill"], alpha=0.25, zorder=1)
        ax.plot(x[mask], upper[mask], color=PALETTE["bb_upper"],
                linewidth=0.7, alpha=0.5, linestyle="--")
        ax.plot(x[mask], lower[mask], color=PALETTE["bb_lower"],
                linewidth=0.7, alpha=0.5, linestyle="--")
        ax.plot(x[mask], mid[mask], color=PALETTE["bb_upper"],
                linewidth=0.5, alpha=0.3, linestyle=":")

    def _draw_signal_levels(self, ax, signal: TradingSignal, df: pd.DataFrame):
        if signal.direction not in (SIGNAL_BUY, SIGNAL_SELL):
            return
        x_end = len(df) - 1
        ax.axhline(signal.entry, color="#FFFFFF", linewidth=0.8,
                   linestyle="--", alpha=0.5, zorder=5)
        ax.text(x_end + 0.5, signal.entry, f" ENTRY\n ${signal.entry:,.2f}",
                color="#FFFFFF", fontsize=7, va="center", alpha=0.8)
        ax.axhline(signal.take_profit, color=PALETTE["signal_tp"],
                   linewidth=1.0, linestyle="-.", alpha=0.8, zorder=5)
        ax.text(x_end + 0.5, signal.take_profit,
                f" TP\n ${signal.take_profit:,.2f}",
                color=PALETTE["signal_tp"], fontsize=7, va="center")
        ax.axhline(signal.stop_loss, color=PALETTE["signal_sl"],
                   linewidth=1.0, linestyle="-.", alpha=0.8, zorder=5)
        ax.text(x_end + 0.5, signal.stop_loss,
                f" SL\n ${signal.stop_loss:,.2f}",
                color=PALETTE["signal_sl"], fontsize=7, va="center")
        color = PALETTE["signal_buy"] if signal.direction == SIGNAL_BUY else PALETTE["signal_sell"]
        ax.axhspan(
            min(signal.entry, signal.take_profit),
            max(signal.entry, signal.take_profit),
            alpha=0.04, color=color, zorder=1
        )
        dy = (signal.take_profit - signal.entry) * 0.3
        ax.annotate(
            "",
            xy=(x_end, signal.entry + dy),
            xytext=(x_end, signal.entry - dy),
            arrowprops=dict(arrowstyle="->", color=color, lw=2),
            zorder=10,
        )

    def _style_price_panel(self, ax, signal: TradingSignal, df: pd.DataFrame):
        ax.set_xlim(-1, len(df) + 8)
        ax.grid(True, axis="y", color=PALETTE["grid"], linewidth=0.4, alpha=0.5)
        ax.grid(True, axis="x", color=PALETTE["grid"], linewidth=0.2, alpha=0.3)
        price_color = (PALETTE["signal_buy"] if signal.direction == SIGNAL_BUY
                       else PALETTE["signal_sell"] if signal.direction == SIGNAL_SELL
                       else PALETTE["text_primary"])
        ax.text(0.005, 0.97,
                f"◆ {signal.symbol}  [{signal.timeframe.upper()}]  ${signal.price:,.2f}",
                transform=ax.transAxes, color=price_color,
                fontsize=10, fontweight="bold", va="top", fontfamily=FONT_FAMILY)
        handles, labels = ax.get_legend_handles_labels()
        if handles:
            ax.legend(handles, labels, loc="upper right",
                      ncol=4, handlelength=1.2, columnspacing=0.8,
                      borderpad=0.4, labelspacing=0.2)
        ax.yaxis.set_label_position("right")
        ax.yaxis.tick_right()
        ax.tick_params(axis="y", labelsize=7)
        for spine in ax.spines.values():
            spine.set_color(PALETTE["border"])

    def _draw_macd(self, ax, df: pd.DataFrame):
        ax.set_facecolor(PALETTE["bg_chart"])
        if "macd" not in df.columns:
            return
        x = np.arange(len(df))
        hist = df["macd_hist"].fillna(0).values
        colors = [PALETTE["macd_pos"] if v >= 0 else PALETTE["macd_neg"] for v in hist]
        ax.bar(x, hist, color=colors, alpha=0.65, width=0.7, zorder=2)
        ax.plot(x, df["macd"].values, color=PALETTE["macd_line"],
                linewidth=1.2, label="MACD", zorder=3)
        ax.plot(x, df["macd_signal"].values, color=PALETTE["macd_signal"],
                linewidth=1.0, linestyle="--", label="Signal", zorder=3)
        ax.axhline(0, color=PALETTE["border"], linewidth=0.6)
        ax.set_ylabel("MACD", color=PALETTE["text_secondary"], fontsize=7)
        ax.legend(loc="upper left", fontsize=6)
        ax.grid(True, color=PALETTE["grid"], linewidth=0.3, alpha=0.4)
        ax.yaxis.tick_right()
        ax.tick_params(axis="y", labelsize=6)
        for spine in ax.spines.values():
            spine.set_color(PALETTE["border"])

    def _draw_rsi(self, ax, df: pd.DataFrame):
        ax.set_facecolor(PALETTE["bg_chart"])
        if "rsi" not in df.columns:
            return
        x = np.arange(len(df))
        rsi = df["rsi"].values
        ax.plot(x, rsi, color=PALETTE["rsi_line"], linewidth=1.3, zorder=3)
        ax.fill_between(x, rsi, 30, where=(rsi < 30), color=PALETTE["rsi_os"], alpha=0.2)
        ax.fill_between(x, rsi, 70, where=(rsi > 70), color=PALETTE["rsi_ob"], alpha=0.2)
        ax.axhline(70, color=PALETTE["rsi_ob"], linewidth=0.7, linestyle="--", alpha=0.6)
        ax.axhline(50, color=PALETTE["border"], linewidth=0.5, linestyle=":", alpha=0.5)
        ax.axhline(30, color=PALETTE["rsi_os"], linewidth=0.7, linestyle="--", alpha=0.6)
        ax.set_ylim(0, 100)
        ax.set_ylabel("RSI", color=PALETTE["text_secondary"], fontsize=7)
        ax.yaxis.tick_right()
        ax.tick_params(axis="y", labelsize=6)
        ax.set_yticks([30, 50, 70])
        rsi_now = float(df["rsi"].iloc[-1])
        color = (PALETTE["rsi_ob"] if rsi_now > 70
                 else PALETTE["rsi_os"] if rsi_now < 30
                 else PALETTE["rsi_line"])
        ax.text(len(df) - 1, rsi_now, f"  {rsi_now:.1f}",
                color=color, fontsize=7, va="center")
        ax.grid(True, color=PALETTE["grid"], linewidth=0.3, alpha=0.4)
        for spine in ax.spines.values():
            spine.set_color(PALETTE["border"])

    def _draw_volume(self, ax, df: pd.DataFrame):
        ax.set_facecolor(PALETTE["bg_chart"])
        x = np.arange(len(df))
        colors = [
            PALETTE["vol_bull"] if row["close"] >= row["open"] else PALETTE["vol_bear"]
            for _, row in df.iterrows()
        ]
        ax.bar(x, df["volume"].values, color=colors, alpha=0.75, width=0.7)
        if "vol_ma" in df.columns:
            ax.plot(x, df["vol_ma"].values, color="#FFA726",
                    linewidth=0.9, linestyle="--", alpha=0.7)
        ax.set_ylabel("VOL", color=PALETTE["text_secondary"], fontsize=7)
        ax.yaxis.tick_right()
        ax.tick_params(axis="y", labelsize=5)
        ax.yaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(
                lambda v, _: f"{v/1e6:.1f}M" if v > 1e6 else f"{v/1e3:.0f}K"
            )
        )
        ax.grid(True, axis="y", color=PALETTE["grid"], linewidth=0.3, alpha=0.3)
        for spine in ax.spines.values():
            spine.set_color(PALETTE["border"])

    def _format_x_axis(self, ax, df: pd.DataFrame):
        n = len(df)
        step = max(1, n // 8)
        ticks = list(range(0, n, step))
        labels = [df.index[i].strftime("%d/%m %H:%M") for i in ticks]
        ax.set_xticks(ticks)
        ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=6)

    def _draw_header(self, fig, signal: TradingSignal):
        dir_color = (PALETTE["signal_buy"] if signal.direction == SIGNAL_BUY
                     else PALETTE["signal_sell"] if signal.direction == SIGNAL_SELL
                     else PALETTE["text_secondary"])
        dir_emoji = "▲ COMPRA" if signal.direction == SIGNAL_BUY else "▼ VENDA" if signal.direction == SIGNAL_SELL else "◆ NEUTRO"
        phase_map = {
            "markup": "📈 MARKUP", "markdown": "📉 MARKDOWN",
            "accumulation": "🔄 ACUMULAÇÃO", "distribution": "🔁 DISTRIBUIÇÃO",
        }
        phase = phase_map.get(signal.market_phase, signal.market_phase)
        strength_bar = "█" * signal.strength + "░" * (4 - signal.strength)
        title = (f"  {dir_emoji}  ·  Score {signal.score:.0f}/100  ·  "
                 f"Força [{strength_bar}]  ·  {phase}  ·  R/R {signal.rr_ratio:.2f}x  ")
        fig.text(0.5, 0.96, title, ha="center", va="top",
                 fontsize=9, fontweight="bold", color=dir_color,
                 fontfamily=FONT_FAMILY, transform=fig.transFigure)
        line = plt.Line2D([0.04, 0.96], [0.935, 0.935],
                          transform=fig.transFigure,
                          color=PALETTE["border"], linewidth=0.8)
        fig.add_artist(line)

    def _draw_footer(self, fig, signal: TradingSignal):
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        reasons_text = "  |  ".join(signal.reasons[:3]) or "Análise técnica composta"
        fig.text(0.5, 0.025,
                 f"📡 BTC Signal Bot  ·  {ts}  ·  {reasons_text}",
                 ha="center", va="bottom", fontsize=6.5,
                 color=PALETTE["text_secondary"], fontfamily=FONT_FAMILY)
