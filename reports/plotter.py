# reports/plotter.py

"""
Basic plotting module for backtest results.
Phase 2: Simple matplotlib visualizations.
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class BacktestPlotter:
    """
    Creates basic visualizations for backtest results.
    """

    def __init__(self, output_dir: str = ""):
        """
        Initialize plotter.

        Args:
            output_dir: Directory to save plots
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Set matplotlib style
        plt.style.use("seaborn-v0_8-darkgrid")

        logger.info(f"BacktestPlotter initialized. Output directory: {self.output_dir}")

    def plot_equity_curve(
        self, equity_curve: List[Dict[str, Any]], save_path: Optional[Path] = None
    ) -> Path:
        """
        Plot equity curve with drawdown.

        Args:
            equity_curve: List of equity values from BacktestEngine
            save_path: Optional specific path to save plot

        Returns:
            Path to saved plot
        """
        if not equity_curve:
            logger.warning("No equity curve data to plot")
            return None

        # Convert to DataFrame
        df = pd.DataFrame(equity_curve)

        if "timestamp" not in df.columns and "index" in df.columns:
            # Use index as x-axis if no timestamp
            df["x"] = df["index"]
        elif "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df["x"] = df["timestamp"]
        else:
            df["x"] = np.arange(len(df))

        # Create figure with subplots
        fig, (ax1, ax2) = plt.subplots(
            2, 1, figsize=(12, 8), gridspec_kw={"height_ratios": [3, 1]}
        )

        # Plot 1: Equity curve
        ax1.plot(
            df["x"], df["equity"], label="Portfolio Equity", color="blue", linewidth=2
        )

        # Add initial capital line
        if len(df) > 0:
            initial_equity = df["equity"].iloc[0]
            ax1.axhline(
                y=initial_equity,
                color="green",
                linestyle="--",
                alpha=0.5,
                label="Initial Capital",
            )

        ax1.set_title("Portfolio Equity Curve", fontsize=14, fontweight="bold")
        ax1.set_ylabel("Equity ($)", fontsize=12)
        ax1.legend(loc="best")
        ax1.grid(True, alpha=0.3)

        # Format x-axis if datetime
        if "timestamp" in df.columns:
            ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
            plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)

        # Plot 2: Drawdown
        if "equity" in df.columns and len(df) > 0:
            # Calculate drawdown
            equity_series = df["equity"].values
            running_max = np.maximum.accumulate(equity_series)
            drawdown = (equity_series - running_max) / running_max * 100

            ax2.fill_between(
                df["x"],
                drawdown,
                0,
                where=drawdown < 0,
                color="red",
                alpha=0.3,
                label="Drawdown",
            )
            ax2.plot(df["x"], drawdown, color="red", linewidth=1, alpha=0.7)

            # Highlight max drawdown
            max_dd_idx = np.argmin(drawdown)
            max_dd_value = drawdown[max_dd_idx]

            if max_dd_value < 0:
                ax2.plot(
                    df["x"].iloc[max_dd_idx],
                    max_dd_value,
                    "ro",
                    markersize=8,
                    label=f"Max DD: {max_dd_value:.1f}%",
                )

        ax2.set_title("Drawdown (%)", fontsize=12)
        ax2.set_ylabel("Drawdown %", fontsize=10)
        ax2.set_xlabel(
            "Time" if "timestamp" in df.columns else "Candle Index", fontsize=10
        )
        ax2.legend(loc="best")
        ax2.grid(True, alpha=0.3)

        # Format x-axis for drawdown plot
        if "timestamp" in df.columns:
            ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
            plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)

        plt.tight_layout()

        # Save plot
        if save_path is None:
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            save_path = self.output_dir / f"equity_curve_{timestamp}.png"
        else:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)

        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        logger.info(f"Equity curve plot saved to: {save_path}")
        return save_path

    def plot_trade_distribution(
        self, trades: List[Dict[str, Any]], save_path: Optional[Path] = None
    ) -> Path:
        """
        Plot trade P&L distribution.

        Args:
            trades: List of trades from BacktestEngine
            save_path: Optional specific path to save plot

        Returns:
            Path to saved plot
        """
        if not trades:
            logger.warning("No trade data to plot")
            return None

        # Convert to DataFrame
        df = pd.DataFrame(trades)

        if "net_pnl" not in df.columns:
            logger.warning("No P&L data in trades")
            return None

        # Create figure
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        # Plot 1: Histogram of P&L
        ax1 = axes[0, 0]
        profits = df[df["net_pnl"] > 0]["net_pnl"]
        losses = df[df["net_pnl"] < 0]["net_pnl"]

        if len(profits) > 0:
            ax1.hist(
                profits,
                bins=30,
                alpha=0.7,
                color="green",
                label=f"Profits ({len(profits)})",
                edgecolor="black",
            )
        if len(losses) > 0:
            ax1.hist(
                losses,
                bins=30,
                alpha=0.7,
                color="red",
                label=f"Losses ({len(losses)})",
                edgecolor="black",
            )

        ax1.set_title("Distribution of Trade P&L", fontsize=12, fontweight="bold")
        ax1.set_xlabel("P&L ($)", fontsize=10)
        ax1.set_ylabel("Frequency", fontsize=10)
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Plot 2: Cumulative P&L
        ax2 = axes[0, 1]
        df_sorted = df.sort_values(
            "exit_time" if "exit_time" in df.columns else "entry_time"
        )
        cumulative_pnl = df_sorted["net_pnl"].cumsum()

        ax2.plot(
            range(len(cumulative_pnl)),
            cumulative_pnl,
            color="blue",
            linewidth=2,
            label="Cumulative P&L",
        )
        ax2.fill_between(
            range(len(cumulative_pnl)),
            0,
            cumulative_pnl,
            where=cumulative_pnl > 0,
            color="green",
            alpha=0.3,
        )
        ax2.fill_between(
            range(len(cumulative_pnl)),
            0,
            cumulative_pnl,
            where=cumulative_pnl < 0,
            color="red",
            alpha=0.3,
        )

        ax2.set_title("Cumulative P&L Over Trades", fontsize=12, fontweight="bold")
        ax2.set_xlabel("Trade Number", fontsize=10)
        ax2.set_ylabel("Cumulative P&L ($)", fontsize=10)
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # Plot 3: Win/Loss by exit reason
        ax3 = axes[1, 0]
        if "exit_reason" in df.columns:
            reason_stats = (
                df.groupby("exit_reason")
                .agg({"net_pnl": ["count", "sum", "mean"], "bars_held": "mean"})
                .round(2)
            )

            if not reason_stats.empty:
                reasons = reason_stats.index.tolist()
                counts = reason_stats[("net_pnl", "count")].values

                bars = ax3.bar(
                    range(len(reasons)), counts, color="skyblue", edgecolor="black"
                )
                ax3.set_title("Trades by Exit Reason", fontsize=12, fontweight="bold")
                ax3.set_xlabel("Exit Reason", fontsize=10)
                ax3.set_ylabel("Number of Trades", fontsize=10)
                ax3.set_xticks(range(len(reasons)))
                ax3.set_xticklabels(reasons, rotation=45, ha="right")

                # Add count labels on bars
                for bar, count in zip(bars, counts):
                    height = bar.get_height()
                    ax3.text(
                        bar.get_x() + bar.get_width() / 2.0,
                        height,
                        f"{int(count)}",
                        ha="center",
                        va="bottom",
                    )

        # Plot 4: Scatter plot of trade performance
        ax4 = axes[1, 1]
        if "bars_held" in df.columns and "net_pnl" in df.columns:
            winning_trades = df[df["net_pnl"] > 0]
            losing_trades = df[df["net_pnl"] < 0]

            if len(winning_trades) > 0:
                ax4.scatter(
                    winning_trades["bars_held"],
                    winning_trades["net_pnl"],
                    color="green",
                    alpha=0.6,
                    label="Winning Trades",
                    s=30,
                )
            if len(losing_trades) > 0:
                ax4.scatter(
                    losing_trades["bars_held"],
                    losing_trades["net_pnl"],
                    color="red",
                    alpha=0.6,
                    label="Losing Trades",
                    s=30,
                )

            ax4.axhline(y=0, color="black", linestyle="-", linewidth=0.5, alpha=0.5)
            ax4.set_title("Trade P&L vs Holding Period", fontsize=12, fontweight="bold")
            ax4.set_xlabel("Bars Held", fontsize=10)
            ax4.set_ylabel("P&L ($)", fontsize=10)
            ax4.legend()
            ax4.grid(True, alpha=0.3)

        plt.tight_layout()

        # Save plot
        if save_path is None:
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            save_path = self.output_dir / f"trade_distribution_{timestamp}.png"
        else:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)

        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        logger.info(f"Trade distribution plot saved to: {save_path}")
        return save_path

    def plot_price_with_signals(
        self,
        journal: List[Dict[str, Any]],
        trades: List[Dict[str, Any]],
        config: Dict[str, Any],
        save_path: Optional[Path] = None,
        full_data_df: pd.DataFrame = None,
    ) -> Path:
        """
        Plot price with indicators and signals - NOW WITH SEPARATE PANELS.

        Args:
            journal: Trading journal entries
            trades: Trade history
            config: Configuration dictionary
            save_path: Where to save the plot
            full_data_df: Optional DataFrame with all data (pre-aligned, from engine)

        Returns:
            Path to saved plot
        """
        if not journal:
            logger.warning("No journal data for price signals plot")
            return None

        # Convert journal to DataFrame
        journal_df = pd.DataFrame(journal)

        if "price" not in journal_df.columns:
            logger.warning("No price data in journal")
            return None

        # Store full data if provided (for indicator loading)
        if full_data_df is not None:
            self.full_data_df = full_data_df
            logger.info(
                f"Using pre-loaded DataFrame with {len(full_data_df)} rows, "
                f"{len(full_data_df.columns)} columns"
            )
        else:
            logger.warning(
                "No full data DataFrame provided - indicators may not plot correctly"
            )

        # Create save path if not provided
        if save_path is None:
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            save_path = self.output_dir / f"price_signals_{timestamp}.png"

        run_dir = Path(save_path).parent
        run_dir.mkdir(parents=True, exist_ok=True)

        # Get plotting configuration
        plotting_config = config.get("plotting", {})

        # Calculate number of panels
        separate_panels = plotting_config.get("separate_panels", [])
        n_panels = 2  # Price + Position (base panels)
        if separate_panels:
            n_panels += len(separate_panels)

        # Define height ratios
        # Price panel gets 3, position gets 1, each separate panel gets 1
        height_ratios = [3, 1] + [1] * len(separate_panels)

        fig, axes = plt.subplots(
            n_panels,
            1,
            figsize=(14, 3 * n_panels),
            gridspec_kw={"height_ratios": height_ratios},
            sharex=True,
        )

        # Ensure axes is always a list
        if n_panels == 1:
            axes = [axes]

        # Plot 1: Price chart with indicators OVERLAID
        ax_price = axes[0]
        self._plot_price_chart_with_indicators(ax_price, journal_df, trades, config)

        # Plot 2: Position chart
        ax_position = axes[1]
        self._plot_position_chart(ax_position, journal_df, trades)

        # Plot 3+: Separate panels for oscillators
        for i, panel_config in enumerate(separate_panels):
            ax_panel = axes[2 + i]
            self._plot_separate_panel(ax_panel, journal_df, panel_config, config)

        # Format x-axis for bottom plot only
        ax_bottom = axes[-1]
        if "timestamp" in journal_df.columns:
            ax_bottom.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M"))
            plt.setp(ax_bottom.xaxis.get_majorticklabels(), rotation=45, ha="right")
            ax_bottom.set_xlabel("Time", fontsize=10)
        else:
            ax_bottom.set_xlabel("Candle Index", fontsize=10)

        plt.tight_layout()

        # Save plot
        save_path = Path(save_path)
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        logger.info(f"✅ Price signals plot saved to: {save_path}")

        # Clean up
        self.full_data_df = None

        return save_path

    def _plot_separate_panel(self, ax, journal_df, panel_config, config):
        """
        Plot a separate panel for oscillators or other indicators.

        Args:
            ax: Matplotlib axis
            journal_df: Journal DataFrame
            panel_config: Configuration for this panel
            config: Full configuration dict
        """
        # Determine x-axis (timestamp or index)
        if "timestamp" in journal_df.columns:
            journal_df["timestamp"] = pd.to_datetime(journal_df["timestamp"])
            x_axis = journal_df["timestamp"]
        else:
            x_axis = journal_df.index

        # Get indicator column name
        column_name = panel_config.get("column")
        label = panel_config.get("label", column_name)

        if not column_name:
            logger.warning(f"Panel config missing column name: {panel_config}")
            return

        # Get indicator data
        indicator_data = self._load_indicator_data_for_panel(
            journal_df, panel_config, config
        )

        if indicator_data is None or indicator_data.empty:
            logger.warning(f"No data for panel indicator: {column_name}")
            ax.text(
                0.5,
                0.5,
                f"No data: {label}",
                transform=ax.transAxes,
                ha="center",
                va="center",
            )
            return

        # Plot the indicator
        color = panel_config.get("color", "#8E44AD")
        linewidth = panel_config.get("linewidth", 1.5)
        alpha = panel_config.get("alpha", 0.7)

        ax.plot(
            x_axis,
            indicator_data,
            color=color,
            linewidth=linewidth,
            alpha=alpha,
            label=label,
        )

        # Add zero line for oscillators
        if panel_config.get("zero_line", False):
            ax.axhline(y=0, color="gray", linestyle="--", alpha=0.5, linewidth=0.8)

        # Add threshold line if this is CVD ratio
        if "cvd_ratio" in column_name.lower():
            # Try to get threshold from strategy config
            strategy_config = config.get("strategy", {})
            entry_config = strategy_config.get("entry", {})
            params = entry_config.get("params", {})

            if "cvd_ratio_threshold" in params:
                threshold = params["cvd_ratio_threshold"]
                ax.axhline(
                    y=threshold,
                    color="orange",
                    linestyle=":",
                    alpha=0.7,
                    linewidth=1.2,
                    label=f"Threshold ({threshold}%)",
                )

        # Set Y limits if specified
        ylim = panel_config.get("ylim")
        if ylim:
            if isinstance(ylim, list):
                if ylim[1] == "auto":
                    # Auto-scale with some padding
                    data_min = indicator_data.min()
                    data_max = indicator_data.max()
                    padding = (data_max - data_min) * 0.1
                    ax.set_ylim(ylim[0], data_max + padding)
                else:
                    ax.set_ylim(ylim[0], ylim[1])

        # Configure axis
        ax.set_ylabel(label, fontsize=10)
        ax.legend(loc="upper left", fontsize=8)
        ax.grid(True, alpha=0.3)

    def _plot_price_chart_with_indicators(self, ax, journal_df, trades, config):
        """
        Plot price chart with entry/exit signals AND indicators on same axis.
        EXCLUDE indicators that are marked for separate panels.
        """
        # Determine x-axis (timestamp or index)
        if "timestamp" in journal_df.columns:
            journal_df["timestamp"] = pd.to_datetime(journal_df["timestamp"])
            x_axis = journal_df["timestamp"]
            use_timestamps = True
        else:
            x_axis = journal_df.index
            use_timestamps = False

        # Plot price line
        (price_line,) = ax.plot(
            x_axis,
            journal_df["price"],
            label="Price",
            color="black",
            linewidth=1.5,
            alpha=0.8,
            zorder=5,
        )

        logger.debug(f"Plotted price line: {len(journal_df['price'])} points")

        # Load indicators from pre-loaded DataFrame
        indicator_data = self._load_indicator_data(journal_df, config)

        # Get list of indicators that should be in separate panels
        plotting_config = config.get("plotting", {})
        separate_panels = plotting_config.get("separate_panels", [])
        separate_columns = [panel.get("column") for panel in separate_panels]

        # Plot each indicator (EXCLUDING those in separate panels)
        indicators_to_plot = plotting_config.get("indicators_to_plot", [])

        for idx, indicator_config in enumerate(indicators_to_plot):
            column_name = indicator_config.get("column")
            expected_label = indicator_config.get("label", column_name)

            # Skip if this indicator goes in separate panel
            if column_name in separate_columns:
                logger.debug(f"Skipping '{column_name}' - goes in separate panel")
                continue

            if expected_label in indicator_data:
                indicator_series = indicator_data[expected_label]

                # Skip if all NaN
                if indicator_series.isna().all():
                    logger.warning(f"Indicator '{expected_label}' is all NaN, skipping")
                    continue

                # Get styling from config or use defaults
                color = indicator_config.get("color", f"C{idx}")
                linewidth = indicator_config.get("linewidth", 2.0)
                alpha = indicator_config.get("alpha", 0.8)
                linestyle = indicator_config.get("linestyle", "-")

                logger.debug(
                    f"Plotting indicator '{expected_label}' with {len(indicator_series)} values"
                )

                # Plot indicator
                ax.plot(
                    x_axis,
                    indicator_series,
                    color=color,
                    linewidth=linewidth,
                    alpha=alpha,
                    linestyle=linestyle,
                    label=expected_label,
                    zorder=4,
                )
            else:
                logger.warning(f"Indicator '{expected_label}' not found in data")

        # Plot trade signals
        self._plot_trade_signals(ax, trades, x_axis)

        # Configure axis
        ax.set_title(
            "Price Chart with Indicators & Entry/Exit Signals",
            fontsize=14,
            fontweight="bold",
        )
        ax.set_ylabel("Price ($)", fontsize=12)

        # Add legend
        handles, labels = ax.get_legend_handles_labels()
        if handles:  # Only add legend if we have items
            ax.legend(handles, labels, loc="upper left", fontsize=9, framealpha=0.9)

        ax.grid(True, alpha=0.3)

        # Hide x-axis labels for top plot (shared with bottom)
        ax.tick_params(labelbottom=False)  # Hide x-labels for top plot

    def _plot_trade_signals(self, ax, trades, x_axis):
        """
        Plot trade entry/exit signals on price chart.
        """
        if not trades:
            return

        trades_df = pd.DataFrame(trades)

        # Plot entry and exit points
        entry_points = []
        exit_points = []

        for _, trade in trades_df.iterrows():
            # Entry point
            if "entry_time" in trade and "entry_price" in trade:
                entry_time = (
                    pd.to_datetime(trade["entry_time"])
                    if isinstance(trade["entry_time"], str)
                    else trade["entry_time"]
                )
                entry_points.append((entry_time, trade["entry_price"]))

            # Exit point
            if "exit_time" in trade and "exit_price" in trade:
                exit_time = (
                    pd.to_datetime(trade["exit_time"])
                    if isinstance(trade["exit_time"], str)
                    else trade["exit_time"]
                )
                exit_points.append((exit_time, trade["exit_price"]))

        # Plot markers with high zorder to be visible
        if entry_points:
            entry_times, entry_prices = zip(*entry_points)
            ax.scatter(
                entry_times,
                entry_prices,
                color="green",
                marker="^",
                s=100,
                label="Entry",
                zorder=100,
                edgecolors="black",
                linewidth=1,
            )

        if exit_points:
            exit_times, exit_prices = zip(*exit_points)
            ax.scatter(
                exit_times,
                exit_prices,
                color="red",
                marker="v",
                s=100,
                label="Exit",
                zorder=100,
                edgecolors="black",
                linewidth=1,
            )

        # Connect entry-exit pairs
        for _, trade in trades_df.iterrows():
            if all(
                k in trade
                for k in ["entry_time", "entry_price", "exit_time", "exit_price"]
            ):
                entry_time = (
                    pd.to_datetime(trade["entry_time"])
                    if isinstance(trade["entry_time"], str)
                    else trade["entry_time"]
                )
                exit_time = (
                    pd.to_datetime(trade["exit_time"])
                    if isinstance(trade["exit_time"], str)
                    else trade["exit_time"]
                )

                # Color based on P&L
                if "net_pnl" in trade and trade["net_pnl"] > 0:
                    line_color = "green"
                    line_style = "--"
                else:
                    line_color = "red"
                    line_style = ":"

                ax.plot(
                    [entry_time, exit_time],
                    [trade["entry_price"], trade["exit_price"]],
                    color=line_color,
                    alpha=0.5,
                    linewidth=1,
                    linestyle=line_style,
                    zorder=50,
                )

    # Rimuovi i metodi non più necessari:
    # - _plot_indicator() non serve più (indicatori nello stesso panel)
    # - _plot_price_chart() originale sostituito con _plot_price_chart_with_indicators()

    # plotter.py, metodo _load_indicator_data()

    def _load_indicator_data(
        self, journal_df: pd.DataFrame, config: Dict[str, Any]
    ) -> Dict[str, pd.Series]:
        """
        Load indicator data from pre-loaded DataFrame (in memory).

        Args:
            journal_df: Journal DataFrame (for length reference)
            config: Configuration dict

        Returns:
            Dictionary of {label: indicator_series}
        """
        indicator_data = {}

        if self.full_data_df is None:
            return indicator_data

        # Get journal timeline
        if "timestamp" in journal_df.columns:
            x_axis = pd.to_datetime(journal_df["timestamp"])
        else:
            x_axis = journal_df.index

        plotting_config = config.get("plotting", {})
        indicators_to_plot = plotting_config.get("indicators_to_plot", [])

        for plot_config in indicators_to_plot:
            column_name = plot_config.get("column")
            label = plot_config.get("label", column_name)

            if column_name not in self.full_data_df.columns:
                continue

            # Get indicator values
            indicator_series = self.full_data_df[column_name]

            # CRITICAL: Align to journal timeline
            aligned_series = pd.Series(index=x_axis, dtype=float)

            for i, ts in enumerate(x_axis):
                if ts in indicator_series.index:
                    aligned_series.iloc[i] = indicator_series[ts]
                else:
                    # Find nearest value
                    idx = indicator_series.index.get_indexer([ts], method="nearest")[0]
                    aligned_series.iloc[i] = indicator_series.iloc[idx]

            # Fill any remaining NaN
            aligned_series = aligned_series.ffill().bfill()

            indicator_data[label] = aligned_series

            logger.debug(f"Aligned '{label}' to {len(aligned_series)} journal points")

        return indicator_data

    def _load_indicator_data_for_panel(self, journal_df, panel_config, config):
        """
        Load indicator data specifically for separate panel plotting.

        Args:
            journal_df: Journal DataFrame (for length reference)
            panel_config: Panel configuration dict
            config: Full configuration dict

        Returns:
            pandas Series with indicator data aligned to journal timeline
        """
        if self.full_data_df is None:
            logger.warning("No full data DataFrame available for panel plotting")
            return None

        column_name = panel_config.get("column")

        if column_name not in self.full_data_df.columns:
            logger.warning(f"Indicator column '{column_name}' not found in data")
            return None

        # Get journal timeline
        if "timestamp" in journal_df.columns:
            x_axis = pd.to_datetime(journal_df["timestamp"])
        else:
            x_axis = journal_df.index

        # Get indicator values
        indicator_series = self.full_data_df[column_name]

        # Align to journal timeline
        aligned_series = pd.Series(index=x_axis, dtype=float)

        for i, ts in enumerate(x_axis):
            if ts in indicator_series.index:
                aligned_series.iloc[i] = indicator_series[ts]
            else:
                # Find nearest value
                try:
                    idx = indicator_series.index.get_indexer([ts], method="nearest")[0]
                    aligned_series.iloc[i] = indicator_series.iloc[idx]
                except:
                    aligned_series.iloc[i] = np.nan

        # Fill any remaining NaN
        aligned_series = aligned_series.ffill().bfill()

        logger.debug(f"Aligned '{column_name}' to {len(aligned_series)} journal points")

        return aligned_series

    def _plot_position_chart(self, ax, journal_df, trades):
        """
        Plot position status.
        """
        if "timestamp" in journal_df.columns:
            x_axis = pd.to_datetime(journal_df["timestamp"])
        else:
            x_axis = journal_df.index

        # Plot position indicator
        if "in_position" in journal_df.columns:
            position_signal = journal_df["in_position"].astype(float)

            ax.fill_between(
                x_axis,
                0,
                position_signal,
                where=position_signal > 0,
                color="blue",
                alpha=0.3,
                label="In Position",
            )
            ax.plot(x_axis, position_signal, color="blue", linewidth=1)

        # Add trade markers if available
        trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()
        if not trades_df.empty:
            entry_times = []
            exit_times = []

            for _, trade in trades_df.iterrows():
                if "entry_time" in trade:
                    entry_time = (
                        pd.to_datetime(trade["entry_time"])
                        if isinstance(trade["entry_time"], str)
                        else trade["entry_time"]
                    )
                    entry_times.append(entry_time)

                if "exit_time" in trade:
                    exit_time = (
                        pd.to_datetime(trade["exit_time"])
                        if isinstance(trade["exit_time"], str)
                        else trade["exit_time"]
                    )
                    exit_times.append(exit_time)

            if entry_times:
                ax.scatter(
                    entry_times,
                    [1] * len(entry_times),
                    color="green",
                    marker="^",
                    s=50,
                    zorder=5,
                    label="Entry",
                )

            if exit_times:
                ax.scatter(
                    exit_times,
                    [0] * len(exit_times),
                    color="red",
                    marker="v",
                    s=50,
                    zorder=5,
                    label="Exit",
                )

        ax.set_title("Position Status", fontsize=12)
        ax.set_xlabel("Time", fontsize=10)
        ax.set_ylabel("Position", fontsize=10)
        ax.set_yticks([0, 1])
        ax.set_yticklabels(["Out", "In"])
        ax.legend(loc="best")
        ax.grid(True, alpha=0.3)

        # Format x-axis
        if "timestamp" in journal_df.columns:
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

    def _find_indicator_file(
        self, indicators_dir: Path, symbol: str, indicator_name: str, params: Dict
    ) -> Optional[Path]:
        """
        Find the correct indicator Parquet file based on parameters.
        """
        indicator_dir = indicators_dir / symbol
        if not indicator_dir.exists():
            logger.warning(f"Indicator directory does not exist: {indicator_dir}")
            return None

        logger.info(f"Searching in: {indicator_dir}")

        # Crea un pattern basato sui parametri
        # Es: sma_period200_1m_*.parquet
        param_str = "_".join([f"{k}{v}" for k, v in sorted(params.items())])

        # Pattern 1: Con parametri specifici
        if param_str:
            pattern = f"{indicator_name}_{param_str}_*.parquet"
            logger.info(f"Trying pattern 1: {pattern}")
            matching_files = list(indicator_dir.glob(pattern))

            if matching_files:
                logger.info(f"Found {len(matching_files)} files with pattern 1")
                # Prendi il file più recente (per timestamp o modifica)
                return max(matching_files, key=lambda x: x.stat().st_mtime)

        # Pattern 2: Con timeframe (dalla config)
        if "tf" in params:
            pattern = f"{indicator_name}_*{params['tf']}*.parquet"
            logger.info(f"Trying pattern 2: {pattern}")
            matching_files = list(indicator_dir.glob(pattern))

            if matching_files:
                logger.info(f"Found {len(matching_files)} files with pattern 2")
                return max(matching_files, key=lambda x: x.stat().st_mtime)

        # Pattern 3: Qualsiasi file con il nome dell'indicatore
        pattern = f"{indicator_name}_*.parquet"
        logger.info(f"Trying pattern 3: {pattern}")
        matching_files = list(indicator_dir.glob(pattern))

        if matching_files:
            logger.info(f"Found {len(matching_files)} files with pattern 3")
            return max(matching_files, key=lambda x: x.stat().st_mtime)

        logger.warning(f"No files found for indicator: {indicator_name}")
        return None

    # plotter.py

    def create_all_plots(
        self,
        results: Dict[str, Any],
        run_dir: Path,
        config: Dict[str, Any],
        full_data_df: pd.DataFrame = None,
    ) -> Dict[str, Path]:
        """Create all plots with optional pre-loaded DataFrame."""
        plot_paths = {}

        # Store the DataFrame for use in plotting methods
        self.full_data_df = full_data_df

        try:
            # 1. Equity curve plot
            if results.get("equity_curve"):
                equity_plot_path = run_dir / "equity_curve.png"
                plot_paths["equity"] = self.plot_equity_curve(
                    results["equity_curve"], equity_plot_path
                )

            # 2. Trade distribution plot
            if results.get("trades"):
                trade_plot_path = run_dir / "trade_distribution.png"
                plot_paths["trades"] = self.plot_trade_distribution(
                    results["trades"], trade_plot_path
                )

            # 3. Price with signals plot - PASSA full_data_df!
            if results.get("journal") and results.get("trades"):
                price_plot_path = run_dir / "price_signals.png"
                plot_paths["price"] = self.plot_price_with_signals(
                    journal=results["journal"],
                    trades=results["trades"],
                    config=config,
                    save_path=price_plot_path,
                    full_data_df=full_data_df,  # ← QUI!
                )

            logger.info(f"Created {len(plot_paths)} plots in {run_dir}")

        except Exception as e:
            logger.error(f"Error creating plots: {e}")
        finally:
            # Clean up
            self.full_data_df = None

        return plot_paths
