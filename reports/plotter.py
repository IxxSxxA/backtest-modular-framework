"""
Backtest Plotter - Dynamic visualization system

Automatically generates plots based on config.yaml indicator declarations.
Supports dynamic panel creation, overlay indicators, and visual customization.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
from matplotlib.gridspec import GridSpec
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import logging

try:
    import mplfinance as mpf

    MPLFINANCE_AVAILABLE = True
except ImportError:
    MPLFINANCE_AVAILABLE = False
    logging.warning("mplfinance not available. Candlestick plotting will be limited.")

from reports.plot_helpers import (
    plot_candlesticks_basic,
    plot_trades_markers,
    plot_sl_tp_zones,
    format_date_axis,
    add_text_box,
)

logger = logging.getLogger(__name__)


class BacktestPlotter:
    """
    Creates publication-quality backtest visualization plots.

    Features:
    - Auto-scans indicators from config
    - Dynamic panel creation based on overlay settings
    - SL/TP visualization with zones
    - Trade annotations with P&L
    - Position timeline
    - Equity curve with drawdown
    - Trade distribution statistics
    """

    def __init__(self):
        """Initialize plotter with default style settings."""
        # Set matplotlib style
        plt.style.use("seaborn-v0_8-darkgrid")

        # Default colors
        self.colors = {
            "background": "#f5f5f5",
            "grid": "#E0E0E0",
            "text": "#2C3E50",
            "candle_up": "#26A69A",
            "candle_down": "#EF5350",
            "long": "#27AE60",
            "short": "#E74C3C",
            "flat": "#95A5A6",
        }

        logger.info("BacktestPlotter initialized")

    def create_all_plots(
        self,
        results: Dict[str, Any],
        run_dir: Path,
        config: Dict[str, Any],
        full_data_df: pd.DataFrame,
    ) -> Dict[str, Path]:
        """
        Create all backtest plots.

        Args:
            results: Results dictionary from BacktestEngine
            run_dir: Directory to save plots
            config: Full configuration dictionary
            full_data_df: DataFrame with OHLCV + indicators

        Returns:
            Dictionary mapping plot names to file paths
        """
        plot_paths = {}

        # Check if we have data
        if full_data_df is None or full_data_df.empty:
            logger.warning("No data available for plotting")
            return plot_paths

        # ✅ Let's try to use data_with_indicators
        if (
            "data_with_indicators" in results
            and not results["data_with_indicators"].empty
        ):
            plot_data = results["data_with_indicators"]
            logger.info(
                f"Using data_with_indicators for plotting ({len(plot_data)} rows)"
            )
        else:
            # Fallback to original data
            plot_data = full_data_df
            logger.info(f"Using original data for plotting (no TP/SL columns)")

        # 1. Price signals (main chart)
        try:
            logger.info("Creating price_signals.png...")
            path = self.create_price_signals(
                data=plot_data,
                trades=results.get("trades", []),
                config=config,
                save_path=run_dir / "price_signals.png",
            )
            plot_paths["price_signals"] = path
        except Exception as e:
            logger.error(f"Failed to create price signals plot: {e}", exc_info=True)

        # 2. Equity curve
        try:
            logger.info("Creating equity_curve.png...")
            path = self.create_equity_curve(
                equity_data=results.get("equity_curve", []),
                trades=results.get("trades", []),
                config=config,
                save_path=run_dir / "equity_curve.png",
            )
            plot_paths["equity_curve"] = path
        except Exception as e:
            logger.error(f"Failed to create equity curve plot: {e}", exc_info=True)

        # 3. Trade distribution
        try:
            logger.info("Creating trade_distribution.png...")
            path = self.create_trade_distribution(
                trades=results.get("trades", []),
                config=config,
                save_path=run_dir / "trade_distribution.png",
            )
            plot_paths["trade_distribution"] = path
        except Exception as e:
            logger.error(
                f"Failed to create trade distribution plot: {e}", exc_info=True
            )

        return plot_paths

    def create_price_signals(
        self,
        data: pd.DataFrame,
        trades: List[Dict],
        config: Dict[str, Any],
        save_path: Path,
    ) -> Path:
        """
        Create main price chart with dynamic panels.

        Layout:
        - Price chart with overlays (EMA, SMA, etc)
        - SL/TP zones
        - Separate panels for oscillators (CVD, RSI, etc)
        - Position timeline at bottom

        Args:
            data: DataFrame with OHLCV + indicators
            trades: List of trade dictionaries
            config: Configuration dictionary
            save_path: Path to save plot

        Returns:
            Path to saved plot
        """
        # Extract plot config
        plot_config = config.get("plot_config", {})
        layout = plot_config.get("layout", {})
        style = plot_config.get("style", {})

        # Get height ratios
        price_ratio = layout.get("price_height_ratio", 3)
        panel_ratio = layout.get("panel_height_ratio", 1)
        position_ratio = layout.get("position_height_ratio", 1)

        # Collect indicators to plot
        overlays, panels = self._collect_plot_indicators(config, data)

        logger.info(
            f"Plotting {len(overlays)} overlay indicators, {len(panels)} panel indicators"
        )

        # Calculate number of subplots
        n_panels = 1 + len(panels) + 1  # price + indicator panels + position

        # Create height ratios
        height_ratios = [price_ratio] + [panel_ratio] * len(panels) + [position_ratio]

        # Create figure
        fig_width, fig_height = layout.get("figure_size", [16, 10])
        fig = plt.figure(figsize=(fig_width, fig_height))

        gs = GridSpec(
            n_panels,
            1,
            height_ratios=height_ratios,
            hspace=0.05,
            left=0.08,
            right=0.95,
            top=0.95,
            bottom=0.05,
        )

        axes = []
        for i in range(n_panels):
            if i == 0:
                ax = fig.add_subplot(gs[i])
            else:
                ax = fig.add_subplot(gs[i], sharex=axes[0])
            axes.append(ax)

        # Set background color
        bg_color = style.get("background_color", self.colors["background"])
        fig.patch.set_facecolor(bg_color)
        for ax in axes:
            ax.set_facecolor(bg_color)

        # --- PANEL 0: Price Chart ---
        ax_price = axes[0]

        # Plot candlesticks
        candle_colors = style.get("candlestick", {})
        plot_candlesticks_basic(
            ax_price,
            data,
            up_color=candle_colors.get("up_color", self.colors["candle_up"]),
            down_color=candle_colors.get("down_color", self.colors["candle_down"]),
        )

        # Plot overlay indicators
        for ind_info in overlays:
            col_name = ind_info["column"]
            if col_name in data.columns:
                ax_price.plot(
                    data.index,
                    data[col_name],
                    label=ind_info["label"],
                    color=ind_info["color"],
                    linewidth=ind_info.get("linewidth", 1.5),
                    alpha=ind_info.get("alpha", 0.8),
                )
                logger.debug(f"Plotted overlay: {col_name}")
            else:
                logger.warning(f"Column {col_name} not found in data")

        # Plot SL/TP zones
        exit_visual = config.get("strategy", {}).get("exit", {}).get("visual", {})
        sl_tp_config = exit_visual.get("sl_tp", {})

        # DEBUG
        logger.info(f"SL/TP config found: {sl_tp_config}")
        logger.info(f"SL/TP enabled: {sl_tp_config.get('enabled', False)}")
        if trades:
            logger.info(
                f"First trade has TP/SL: {trades[0].get('take_profit')}, {trades[0].get('stop_loss')}"
            )

        if sl_tp_config.get("enabled", False) and trades:
            if "take_profit" in data.columns and "stop_loss" in data.columns:
                plot_sl_tp_zones(
                    ax_price,
                    data,
                    trades,
                    sl_tp_config,
                )
                logger.info("Plotted dynamic TP/SL zones")
            else:
                logger.warning("Data missing TP/SL columns, cannot plot zones")

        # Plot trade markers
        if trades:
            # DEBUG: Print first trade structure
            logger.info(f"First trade keys: {trades[0].keys()}")
            logger.info(f"First trade: {trades[0]}")
            plot_trades_markers(
                ax_price,
                data,
                trades,
                show_pnl=sl_tp_config.get("annotations", {}).get("show_pnl", True),
            )

        # Style price chart
        ax_price.set_ylabel("Price", fontsize=10, fontweight="bold")
        ax_price.legend(loc="upper left", fontsize=8, framealpha=0.9)
        ax_price.grid(
            True,
            alpha=style.get("grid_alpha", 0.2),
            color=style.get("grid_color", self.colors["grid"]),
        )
        ax_price.tick_params(labelbottom=False)

        # --- PANEL 1+: Indicator Panels ---
        for i, panel_info in enumerate(panels):
            ax_panel = axes[i + 1]
            col_name = panel_info["column"]

            if col_name not in data.columns:
                logger.warning(f"Column {col_name} not found in data")
                continue

            # Plot indicator
            ax_panel.plot(
                data.index,
                data[col_name],
                label=panel_info["label"],
                color=panel_info["color"],
                linewidth=panel_info.get("linewidth", 1.5),
                alpha=panel_info.get("alpha", 0.8),
            )

            # Apply panel settings
            panel_config = panel_info.get("panel", {})

            # Y-axis limits
            if "ylim" in panel_config:
                ax_panel.set_ylim(panel_config["ylim"])

            # Zero line
            if panel_config.get("zero_line", False):
                ax_panel.axhline(
                    0, color="gray", linestyle="-", linewidth=0.8, alpha=0.5
                )

            # Horizontal lines (thresholds)
            if "hlines" in panel_config:
                for hline in panel_config["hlines"]:
                    if isinstance(hline, dict):
                        ax_panel.axhline(
                            hline["value"],
                            color=hline.get("color", "gray"),
                            linestyle=hline.get("linestyle", "--"),
                            linewidth=hline.get("linewidth", 0.8),
                            alpha=hline.get("alpha", 0.5),
                            label=hline.get("label", ""),
                        )
                    else:
                        # Simple format: just value
                        ax_panel.axhline(
                            hline,
                            color="gray",
                            linestyle="--",
                            linewidth=0.8,
                            alpha=0.5,
                        )

            # Style
            ax_panel.set_ylabel(panel_info["label"], fontsize=9, fontweight="bold")
            ax_panel.legend(loc="upper left", fontsize=7, framealpha=0.9)
            ax_panel.grid(
                True,
                alpha=style.get("grid_alpha", 0.2),
                color=style.get("grid_color", self.colors["grid"]),
            )

            # Hide x-axis labels except last panel
            if i < len(panels) - 1:
                ax_panel.tick_params(labelbottom=False)

        # --- LAST PANEL: Position Timeline ---
        ax_position = axes[-1]
        self._plot_position_timeline(ax_position, data, trades)

        ax_position.set_ylabel("Position", fontsize=9, fontweight="bold")
        ax_position.set_ylim(-1.5, 1.5)
        ax_position.set_yticks([-1, 0, 1])
        ax_position.set_yticklabels(["SHORT", "FLAT", "LONG"])
        ax_position.grid(
            True,
            alpha=style.get("grid_alpha", 0.2),
            color=style.get("grid_color", self.colors["grid"]),
        )

        # Format x-axis (only on bottom panel)
        format_date_axis(ax_position)
        ax_position.set_xlabel("Time", fontsize=10, fontweight="bold")

        # Add title
        symbol = config.get("data", {}).get("symbols", ["UNKNOWN"])[0]
        strategy_name = (
            config.get("strategy", {}).get("entry", {}).get("name", "Strategy")
        )
        timeframe = config.get("strategy", {}).get("timeframe", "1m")

        fig.suptitle(
            f"{symbol} - {strategy_name} ({timeframe})",
            fontsize=14,
            fontweight="bold",
            y=0.98,
        )

        # Save
        plt.savefig(save_path, dpi=150, bbox_inches="tight", facecolor=bg_color)
        plt.close(fig)

        logger.info(f"✅ Saved price_signals.png")
        return save_path

    def create_equity_curve(
        self,
        equity_data: List[Dict],
        trades: List[Dict],
        config: Dict[str, Any],
        save_path: Path,
    ) -> Path:
        """Create equity curve with drawdown panel."""
        if not equity_data:
            logger.warning("No equity data to plot")
            return None

        # Convert to DataFrame
        df = pd.DataFrame(equity_data)

        # Handle index (equity data has 'index' field, not timestamp)
        if "index" in df.columns:
            df = df.set_index("index")

        # FIX: Use 'equity' field (not 'total_equity')
        equity_col = "equity"  # ← Exact field name from engine

        if equity_col not in df.columns:
            logger.error(
                f"Cannot find '{equity_col}' column. Available: {df.columns.tolist()}"
            )
            return None

        logger.debug(f"Using equity column: {equity_col}")

        # Calculate drawdown
        df["peak"] = df[equity_col].cummax()
        df["drawdown"] = (df[equity_col] - df["peak"]) / df["peak"] * 100

        # Create figure
        plot_config = config.get("plot_config", {})
        style = plot_config.get("style", {})
        bg_color = style.get("background_color", self.colors["background"])

        fig, (ax_equity, ax_dd) = plt.subplots(
            2,
            1,
            figsize=(14, 8),
            height_ratios=[3, 1],
            sharex=True,
        )

        fig.patch.set_facecolor(bg_color)
        ax_equity.set_facecolor(bg_color)
        ax_dd.set_facecolor(bg_color)

        # --- Equity curve ---
        ax_equity.plot(
            df.index,
            df[equity_col],  # ← Use variable
            label="Equity",
            color="#2E86AB",
            linewidth=2,
        )

        ax_equity.plot(
            df.index,
            df["peak"],
            label="Peak Equity",
            color="#06A77D",
            linewidth=1,
            linestyle="--",
            alpha=0.6,
        )

        # Mark trades (if any)
        if trades:
            # We need to map entry_index to equity curve
            trade_indices = []
            trade_equity = []

            for trade in trades:
                entry_idx = trade.get("entry_index")
                if entry_idx is not None and entry_idx in df.index:
                    trade_indices.append(entry_idx)
                    trade_equity.append(df.loc[entry_idx, equity_col])  # ← Use variable

            if trade_indices:
                ax_equity.scatter(
                    trade_indices,
                    trade_equity,
                    marker="^",
                    s=50,
                    color="#F77F00",
                    alpha=0.6,
                    label="Trades",
                    zorder=5,
                )

        # Find max drawdown point
        max_dd_idx = df["drawdown"].idxmin()
        max_dd_value = df.loc[max_dd_idx, "drawdown"]

        ax_equity.annotate(
            f"Max DD: {max_dd_value:.2f}%",
            xy=(max_dd_idx, df.loc[max_dd_idx, equity_col]),  # ← FIX: Use variable!
            xytext=(10, -20),
            textcoords="offset points",
            fontsize=9,
            color="#E74C3C",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="white", alpha=0.8),
            arrowprops=dict(arrowstyle="->", color="#E74C3C", lw=1.5),
        )

        ax_equity.set_ylabel("Equity ($)", fontsize=11, fontweight="bold")
        ax_equity.legend(loc="upper left", fontsize=9)
        ax_equity.grid(True, alpha=0.2)
        ax_equity.set_title("Equity Curve", fontsize=12, fontweight="bold", pad=10)

        # --- Drawdown ---
        ax_dd.fill_between(
            df.index,
            df["drawdown"],
            0,
            where=(df["drawdown"] < 0),
            color="#E74C3C",
            alpha=0.3,
            label="Drawdown",
        )

        ax_dd.plot(
            df.index,
            df["drawdown"],
            color="#C0392B",
            linewidth=1.5,
        )

        ax_dd.axhline(0, color="gray", linestyle="-", linewidth=0.8, alpha=0.5)

        ax_dd.set_ylabel("Drawdown (%)", fontsize=10, fontweight="bold")
        ax_dd.set_xlabel(
            "Bar Index", fontsize=10, fontweight="bold"
        )  # ← Note: using index, not time
        ax_dd.legend(loc="lower left", fontsize=8)
        ax_dd.grid(True, alpha=0.2)

        # Save
        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches="tight", facecolor=bg_color)
        plt.close(fig)

        logger.info(f"✅ Saved equity_curve.png")
        return save_path

    def create_trade_distribution(
        self,
        trades: List[Dict],
        config: Dict[str, Any],
        save_path: Path,
    ) -> Path:
        """
        Create trade distribution statistics plots.

        4-panel layout:
        - P&L histogram
        - Win/Loss pie chart
        - Trade duration distribution
        - Entry/Exit reasons

        Args:
            trades: List of trades
            config: Configuration
            save_path: Path to save plot

        Returns:
            Path to saved plot
        """
        if not trades:
            logger.warning("No trades to plot")
            return None

        # Convert to DataFrame
        df = pd.DataFrame(trades)

        # Create figure
        plot_config = config.get("plot_config", {})
        style = plot_config.get("style", {})
        bg_color = style.get("background_color", self.colors["background"])

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.patch.set_facecolor(bg_color)

        for ax in axes.flat:
            ax.set_facecolor(bg_color)

        # --- Panel 1: P&L Histogram ---
        ax_pnl = axes[0, 0]

        # Calculate bins
        pnl_values = df["net_pnl_percent"].values
        bins = np.linspace(pnl_values.min(), pnl_values.max(), 30)

        colors_hist = ["#27AE60" if x > 0 else "#E74C3C" for x in pnl_values]

        ax_pnl.hist(
            pnl_values,
            bins=bins,
            color="#3498DB",
            alpha=0.7,
            edgecolor="black",
        )

        ax_pnl.axvline(0, color="black", linestyle="--", linewidth=1.5, alpha=0.8)
        ax_pnl.axvline(
            pnl_values.mean(),
            color="#F39C12",
            linestyle="-",
            linewidth=2,
            label=f"Mean: {pnl_values.mean():.2f}%",
        )

        ax_pnl.set_xlabel("P&L (%)", fontsize=10, fontweight="bold")
        ax_pnl.set_ylabel("Frequency", fontsize=10, fontweight="bold")
        ax_pnl.set_title("P&L Distribution", fontsize=11, fontweight="bold")
        ax_pnl.legend(fontsize=9)
        ax_pnl.grid(True, alpha=0.2)

        # --- Panel 2: Win/Loss Pie ---
        ax_pie = axes[0, 1]

        wins = (df["net_pnl"] > 0).sum()
        losses = (df["net_pnl"] <= 0).sum()

        labels = [f"Wins ({wins})", f"Losses ({losses})"]
        sizes = [wins, losses]
        colors_pie = ["#27AE60", "#E74C3C"]

        wedges, texts, autotexts = ax_pie.pie(
            sizes,
            labels=labels,
            colors=colors_pie,
            autopct="%1.1f%%",
            startangle=90,
            textprops={"fontsize": 10, "fontweight": "bold"},
        )

        ax_pie.set_title("Win/Loss Ratio", fontsize=11, fontweight="bold")

        # --- Panel 3: Trade Duration ---
        ax_duration = axes[1, 0]

        if "trade_duration_minutes" in df.columns:
            durations = df["trade_duration_minutes"].values

            ax_duration.hist(
                durations,
                bins=20,
                color="#9B59B6",
                alpha=0.7,
                edgecolor="black",
            )

            ax_duration.axvline(
                durations.mean(),
                color="#F39C12",
                linestyle="-",
                linewidth=2,
                label=f"Mean: {durations.mean():.0f} min",
            )

            ax_duration.set_xlabel("Duration (minutes)", fontsize=10, fontweight="bold")
            ax_duration.set_ylabel("Frequency", fontsize=10, fontweight="bold")
            ax_duration.set_title(
                "Trade Duration Distribution", fontsize=11, fontweight="bold"
            )
            ax_duration.legend(fontsize=9)
            ax_duration.grid(True, alpha=0.2)
        else:
            ax_duration.text(
                0.5,
                0.5,
                "Duration data not available",
                ha="center",
                va="center",
                fontsize=12,
                transform=ax_duration.transAxes,
            )
            ax_duration.set_title("Trade Duration", fontsize=11, fontweight="bold")

        # --- Panel 4: Exit Reasons ---
        ax_reasons = axes[1, 1]

        if "exit_reason" in df.columns:
            exit_counts = df["exit_reason"].value_counts()

            colors_reasons = ["#3498DB", "#E74C3C", "#F39C12", "#9B59B6", "#1ABC9C"]

            ax_reasons.barh(
                exit_counts.index,
                exit_counts.values,
                color=colors_reasons[: len(exit_counts)],
                alpha=0.7,
                edgecolor="black",
            )

            ax_reasons.set_xlabel("Count", fontsize=10, fontweight="bold")
            ax_reasons.set_title("Exit Reasons", fontsize=11, fontweight="bold")
            ax_reasons.grid(True, alpha=0.2, axis="x")
        else:
            ax_reasons.text(
                0.5,
                0.5,
                "Exit reason data not available",
                ha="center",
                va="center",
                fontsize=12,
                transform=ax_reasons.transAxes,
            )
            ax_reasons.set_title("Exit Reasons", fontsize=11, fontweight="bold")

        # Add summary stats box
        stats_text = (
            f"Total Trades: {len(df)}\n"
            f"Win Rate: {wins/len(df)*100:.1f}%\n"
            f"Avg P&L: {df['net_pnl_percent'].mean():+.2f}%\n"
            f"Best Trade: {df['net_pnl_percent'].max():+.2f}%\n"
            f"Worst Trade: {df['net_pnl_percent'].min():+.2f}%"
        )

        fig.text(
            0.99,
            0.01,
            stats_text,
            fontsize=9,
            verticalalignment="bottom",
            horizontalalignment="right",
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
        )

        # Overall title
        fig.suptitle(
            "Trade Distribution & Statistics", fontsize=14, fontweight="bold", y=0.98
        )

        # Save
        plt.tight_layout(rect=[0, 0.03, 1, 0.96])
        plt.savefig(save_path, dpi=150, bbox_inches="tight", facecolor=bg_color)
        plt.close(fig)

        logger.info(f"✅ Saved trade_distribution.png")
        return save_path

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _collect_plot_indicators(
        self,
        config: Dict[str, Any],
        data: pd.DataFrame,
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Scan config and collect indicators to plot.
        """
        overlays = []
        panels = []

        # Scan entry indicators
        entry_indicators = (
            config.get("strategy", {}).get("entry", {}).get("indicators", [])
        )
        for ind_config in entry_indicators:
            self._process_indicator_config(ind_config, overlays, panels, data)

        # Scan exit indicators
        exit_indicators = (
            config.get("strategy", {}).get("exit", {}).get("indicators", [])
        )
        for ind_config in exit_indicators:
            self._process_indicator_config(ind_config, overlays, panels, data)

        # Scan analysis indicators - FIX HERE
        analysis_indicators = (
            config.get("analysis_indicators") or []
        )  # ← Force empty list if None
        for ind_config in analysis_indicators:
            self._process_indicator_config(ind_config, overlays, panels, data)

        return overlays, panels

    def _process_indicator_config(
        self,
        ind_config: Dict[str, Any],
        overlays: List[Dict],
        panels: List[Dict],
        data: pd.DataFrame,
    ):
        """Process single indicator config and add to appropriate list."""
        visual = ind_config.get("visual", {})

        if not visual.get("plot", False):
            return  # Not plotted

        # Generate column name (same logic as IndicatorManager)
        column_name = self._generate_column_name(ind_config)

        # Check if column exists in data
        if column_name not in data.columns:
            logger.warning(f"Column {column_name} not found in data, skipping")
            return

        # Extract visual properties
        ind_info = {
            "column": column_name,
            "label": visual.get("label", column_name.upper()),
            "color": visual.get("color", "#3498DB"),
            "linewidth": visual.get("linewidth", 1.5),
            "alpha": visual.get("alpha", 0.8),
        }

        # Check if overlay or panel
        if visual.get("overlay", False):
            overlays.append(ind_info)
        else:
            # Add panel-specific config
            ind_info["panel"] = visual.get("panel", {})
            panels.append(ind_info)

    def _generate_column_name(self, indicator_config: Dict[str, Any]) -> str:
        """
        Generate column name from indicator config.

        Replicates IndicatorManager.generate_column_name() logic.
        """
        name = indicator_config["name"]

        # Special handling
        if name == "cvdratio":
            name = "cvd_ratio"

        # Extract parameters
        params = {
            k: v for k, v in indicator_config.items() if k not in ["name", "visual"]
        }

        # Build suffix
        parts = []

        param_order = [
            "period",
            "cumulative_period_minutes",
            "signal_period_minutes",
            "fast_period",
            "slow_period",
            "signal_period",
            "multiplier",
            "method",
            "std",
            "use_quote",
        ]

        for key in param_order:
            if key in params:
                value = params[key]

                if key == "cumulative_period_minutes":
                    parts.append(str(value))
                elif key == "signal_period_minutes":
                    parts.append(str(value))
                elif key == "use_quote":
                    if value:
                        parts.append("quote")
                elif key == "method":
                    if value != "wilder":
                        parts.append(str(value))
                else:
                    parts.append(str(value))

        # Add remaining parameters
        for key, value in sorted(params.items()):
            if key not in param_order:
                parts.append(f"{key}_{value}")

        # Combine
        if parts:
            return f"{name}_{'_'.join(parts)}"
        else:
            return name

    def _plot_position_timeline(
        self,
        ax: plt.Axes,
        data: pd.DataFrame,
        trades: List[Dict],
    ):
        """
        Plot position timeline (LONG/SHORT/FLAT).

        Args:
            ax: Matplotlib axis
            data: DataFrame with price data
            trades: List of trades
        """
        if not trades:
            ax.text(
                0.5,
                0.5,
                "No positions",
                ha="center",
                va="center",
                fontsize=12,
                transform=ax.transAxes,
            )
            return

        # Create position series
        position = pd.Series(0, index=data.index)

        for trade in trades:
            entry_time = pd.to_datetime(trade["entry_time"])
            exit_time = pd.to_datetime(trade["exit_time"])

            # Find indices
            mask = (data.index >= entry_time) & (data.index <= exit_time)

            # FIX: Use 'position_type' field (lowercase)
            position_type = trade["position_type"]  # ← Correct field

            # Set position value
            if position_type == "long":  # ← lowercase comparison
                position.loc[mask] = 1
            elif position_type == "short":  # ← lowercase comparison
                position.loc[mask] = -1

        # Plot as filled area
        ax.fill_between(
            data.index,
            0,
            position,
            where=(position > 0),
            color=self.colors["long"],
            alpha=0.3,
            label="LONG",
            step="post",
        )

        ax.fill_between(
            data.index,
            0,
            position,
            where=(position < 0),
            color=self.colors["short"],
            alpha=0.3,
            label="SHORT",
            step="post",
        )

        # Plot line
        ax.plot(
            data.index,
            position,
            color="black",
            linewidth=1,
            alpha=0.5,
            drawstyle="steps-post",
        )

        ax.legend(loc="upper left", fontsize=8, ncol=2)
