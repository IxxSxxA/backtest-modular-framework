# reports/plotter.py

"""
Enhanced plotting module with SL/TP visualization.
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
    Creates visualizations for backtest results.
    """

    def __init__(self, output_dir: str = ""):
        """Initialize plotter."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        plt.style.use("seaborn-v0_8-darkgrid")
        logger.info(f"BacktestPlotter initialized. Output directory: {self.output_dir}")

    def plot_price_with_signals(
        self,
        journal: List[Dict[str, Any]],
        trades: List[Dict[str, Any]],
        config: Dict[str, Any],
        save_path: Optional[Path] = None,
        full_data_df: pd.DataFrame = None,
    ) -> Path:
        """
        Plot price with indicators, signals, and SL/TP levels.
        NO POSITION PANEL - Only price + separate indicator panels.

        Args:
            journal: Trading journal entries
            trades: Trade history
            config: Configuration dictionary
            save_path: Where to save the plot
            full_data_df: DataFrame with all data (from engine)

        Returns:
            Path to saved plot
        """
        if not journal:
            logger.warning("No journal data for price signals plot")
            return None

        # Store trades for use in panel plotting
        self.current_trades = trades

        # Convert journal to DataFrame
        journal_df = pd.DataFrame(journal)

        if "price" not in journal_df.columns:
            logger.warning("No price data in journal")
            return None

        # Store full data if provided
        if full_data_df is not None:
            self.full_data_df = full_data_df
            logger.info(
                f"Using pre-loaded DataFrame with {len(full_data_df)} rows, "
                f"{len(full_data_df.columns)} columns"
            )
        else:
            logger.warning("No full data DataFrame provided")

        # Create save path if not provided
        if save_path is None:
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            save_path = self.output_dir / f"price_signals_{timestamp}.png"

        run_dir = Path(save_path).parent
        run_dir.mkdir(parents=True, exist_ok=True)

        # Get plotting configuration
        plotting_config = config.get("plotting", {})

        # Calculate number of panels (NO POSITION PANEL)
        separate_panels = plotting_config.get("separate_panels", [])
        n_panels = 1 + len(separate_panels)  # Price + separate panels

        # Define height ratios - Price panel gets more space (4 instead of 3)
        height_ratios = [4] + [1] * len(separate_panels)

        fig, axes = plt.subplots(
            n_panels,
            1,
            figsize=(16, 4 * n_panels),  # Wider and taller
            gridspec_kw={"height_ratios": height_ratios},
            sharex=True,
        )

        # Ensure axes is always a list
        if n_panels == 1:
            axes = [axes]

        # Plot 1: Price chart with indicators, signals, and SL/TP
        ax_price = axes[0]
        self._plot_price_chart_with_sl_tp(ax_price, journal_df, trades, config)

        # Plot 2+: Separate panels for oscillators
        for i, panel_config in enumerate(separate_panels):
            ax_panel = axes[1 + i]
            self._plot_separate_panel(ax_panel, journal_df, panel_config, config)

        # Format x-axis for bottom plot only
        ax_bottom = axes[-1]
        if "timestamp" in journal_df.columns:
            ax_bottom.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M"))
            plt.setp(ax_bottom.xaxis.get_majorticklabels(), rotation=45, ha="right")
            ax_bottom.set_xlabel("Time", fontsize=11)
        else:
            ax_bottom.set_xlabel("Candle Index", fontsize=11)

        plt.tight_layout()

        # Save plot
        save_path = Path(save_path)
        plt.savefig(save_path, dpi=200, bbox_inches="tight")  # Higher DPI
        plt.close(fig)

        logger.info(f"✅ Price signals plot saved to: {save_path}")

        # Clean up
        self.current_trades = None
        self.full_data_df = None

        return save_path

    def _plot_price_chart_with_sl_tp(self, ax, journal_df, trades, config):
        """
        Plot price chart with:
        - Entry/exit signals
        - Indicators overlaid
        - SL/TP levels for each trade
        """
        # Determine x-axis
        if "timestamp" in journal_df.columns:
            journal_df["timestamp"] = pd.to_datetime(journal_df["timestamp"])
            x_axis = journal_df["timestamp"]
        else:
            x_axis = journal_df.index

        # Plot price line
        ax.plot(
            x_axis,
            journal_df["price"],
            label="Price",
            color="#2C3E50",  # Dark blue-gray
            linewidth=2,
            alpha=0.9,
            zorder=5,
        )

        # Load and plot indicators (EXCLUDING separate panel indicators)
        indicator_data = self._load_indicator_data(journal_df, config)
        plotting_config = config.get("plotting", {})
        separate_panels = plotting_config.get("separate_panels", [])
        separate_columns = [panel.get("column") for panel in separate_panels]

        indicators_to_plot = plotting_config.get("indicators_to_plot", [])

        for idx, indicator_config in enumerate(indicators_to_plot):
            column_name = indicator_config.get("column")
            expected_label = indicator_config.get("label", column_name)

            # Skip if this indicator goes in separate panel
            if column_name in separate_columns:
                continue

            if expected_label in indicator_data:
                indicator_series = indicator_data[expected_label]

                if indicator_series.isna().all():
                    logger.warning(f"Indicator '{expected_label}' is all NaN, skipping")
                    continue

                # Get styling
                color = indicator_config.get("color", f"C{idx}")
                linewidth = indicator_config.get("linewidth", 2.0)
                alpha = indicator_config.get("alpha", 0.8)
                linestyle = indicator_config.get("linestyle", "-")

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

        # Plot SL/TP levels and trade signals
        self._plot_sl_tp_levels(ax, trades, journal_df, config)  # Pass config!
        self._plot_trade_signals(ax, trades, x_axis)

        # Configure axis
        ax.set_title(
            "Price Chart with Indicators, Entry/Exit Signals & SL/TP Levels",
            fontsize=15,
            fontweight="bold",
        )
        ax.set_ylabel("Price ($)", fontsize=13)

        # Legend with better positioning
        handles, labels = ax.get_legend_handles_labels()
        if handles:
            ax.legend(
                handles,
                labels,
                loc="upper left",
                fontsize=10,
                framealpha=0.95,
                ncol=2,  # Two columns for cleaner layout
            )

        ax.grid(True, alpha=0.3, linestyle="--")
        ax.tick_params(labelbottom=False)  # Hide x-labels (shared with bottom)

    def _plot_sl_tp_levels(self, ax, trades, journal_df, config):
        """
        Plot dynamic SL/TP levels that move with ATR over time.
        Shows trailing levels during the trade duration.
        """
        if not trades:
            return

        trades_df = pd.DataFrame(trades)

        # Determine x-axis type
        if "timestamp" in journal_df.columns:
            use_timestamps = True
            journal_df["timestamp"] = pd.to_datetime(journal_df["timestamp"])
        else:
            use_timestamps = False

        # Get exit config
        exit_config = config.get("strategy", {}).get("exit", {}).get("params", {})
        tp_mult = exit_config.get("tp_multiplier", 9.0)
        sl_mult = exit_config.get("sl_multiplier", 5.5)

        for idx, trade in trades_df.iterrows():
            # Skip if trade doesn't have required data
            if not all(
                k in trade for k in ["entry_time", "entry_price", "position_type"]
            ):
                continue

            # Get trade timing and position
            entry_time = trade["entry_time"]
            entry_price = trade["entry_price"]
            position_type = trade.get("position_type", "long")

            # Convert to datetime if needed
            if use_timestamps and isinstance(entry_time, str):
                entry_time = pd.to_datetime(entry_time)

            # Determine exit time
            if "exit_time" in trade and pd.notna(trade["exit_time"]):
                exit_time = trade["exit_time"]
                if use_timestamps and isinstance(exit_time, str):
                    exit_time = pd.to_datetime(exit_time)
            else:
                # Trade still open or no exit time - use last journal entry
                exit_time = (
                    journal_df["timestamp"].iloc[-1]
                    if use_timestamps
                    else len(journal_df) - 1
                )

            # Find all journal entries within trade duration
            if use_timestamps:
                mask = (journal_df["timestamp"] >= entry_time) & (
                    journal_df["timestamp"] <= exit_time
                )
            else:
                entry_idx = trade.get("entry_index", 0)
                exit_idx = trade.get("exit_index", len(journal_df) - 1)
                mask = (journal_df.index >= entry_idx) & (journal_df.index <= exit_idx)

            trade_period_df = journal_df[mask]

            if trade_period_df.empty:
                continue

            # Get timestamps for this trade period
            if use_timestamps:
                trade_times = trade_period_df["timestamp"]
            else:
                trade_times = trade_period_df.index

            # Calculate dynamic SL/TP levels for each point in time
            tp_levels = []
            sl_levels = []

            for i, time_point in enumerate(trade_times):
                # Get ATR value at this time point
                atr_value = self._get_atr_at_time(time_point, use_timestamps)

                if atr_value and not np.isnan(atr_value):
                    if position_type == "long":
                        tp_level = entry_price + (atr_value * tp_mult)
                        sl_level = entry_price - (atr_value * sl_mult)
                    else:  # SHORT
                        tp_level = entry_price - (atr_value * tp_mult)
                        sl_level = entry_price + (atr_value * sl_mult)

                    tp_levels.append(tp_level)
                    sl_levels.append(sl_level)
                else:
                    # Use previous value or entry price if ATR not available
                    if i > 0:
                        tp_levels.append(tp_levels[-1])
                        sl_levels.append(sl_levels[-1])
                    else:
                        # Fallback to static calculation
                        if position_type == "long":
                            tp_levels.append(entry_price * 1.02)  # +2%
                            sl_levels.append(entry_price * 0.98)  # -2%
                        else:
                            tp_levels.append(entry_price * 0.98)  # -2%
                            sl_levels.append(entry_price * 1.02)  # +2%

            # Plot dynamic TP line (green)
            ax.plot(
                trade_times,
                tp_levels,
                color="green",
                linestyle="--",
                alpha=0.6,
                linewidth=1.5,
                label="TP (trailing)" if idx == 0 else "",
                zorder=3,
            )

            # Plot dynamic SL line (red)
            ax.plot(
                trade_times,
                sl_levels,
                color="red",
                linestyle="--",
                alpha=0.6,
                linewidth=1.5,
                label="SL (trailing)" if idx == 0 else "",
                zorder=3,
            )

            # Add fill between SL and TP for visual clarity
            if len(trade_times) > 1 and len(tp_levels) == len(sl_levels) == len(
                trade_times
            ):
                ax.fill_between(
                    trade_times,
                    sl_levels,
                    tp_levels,
                    alpha=0.1,
                    color="gray",
                    label="SL-TP Zone" if idx == 0 else "",
                    zorder=2,
                )

            # Mark entry and exit points
            self._mark_trade_levels(ax, trade, entry_time, exit_time, position_type)

    def _plot_trade_signals(self, ax, trades, x_axis):
        """Plot entry/exit signals on price chart."""
        if not trades:
            return

        trades_df = pd.DataFrame(trades)

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

        # Plot entry markers
        if entry_points:
            entry_times, entry_prices = zip(*entry_points)
            ax.scatter(
                entry_times,
                entry_prices,
                color="limegreen",
                marker="^",
                s=150,
                label="Entry",
                zorder=100,
                edgecolors="darkgreen",
                linewidth=2,
            )

        # Plot exit markers
        if exit_points:
            exit_times, exit_prices = zip(*exit_points)
            ax.scatter(
                exit_times,
                exit_prices,
                color="orangered",
                marker="v",
                s=150,
                label="Exit",
                zorder=100,
                edgecolors="darkred",
                linewidth=2,
            )

        # Connect entry-exit pairs with lines
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
                    line_alpha = 0.4
                else:
                    line_color = "red"
                    line_alpha = 0.4

                ax.plot(
                    [entry_time, exit_time],
                    [trade["entry_price"], trade["exit_price"]],
                    color=line_color,
                    alpha=line_alpha,
                    linewidth=2,
                    linestyle=":",
                    zorder=50,
                )

    def _plot_separate_panel(self, ax, journal_df, panel_config, config):
        """Plot separate panel for oscillators/indicators with trade signals."""
        if "timestamp" in journal_df.columns:
            journal_df["timestamp"] = pd.to_datetime(journal_df["timestamp"])
            x_axis = journal_df["timestamp"]
        else:
            x_axis = journal_df.index

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

        # Plot indicator
        color = panel_config.get("color", "#8E44AD")
        linewidth = panel_config.get("linewidth", 2)
        alpha = panel_config.get("alpha", 0.8)

        ax.plot(
            x_axis,
            indicator_data,
            color=color,
            linewidth=linewidth,
            alpha=alpha,
            label=label,
            zorder=10,
        )

        # Zero line for oscillators
        if panel_config.get("zero_line", False):
            ax.axhline(y=0, color="gray", linestyle="--", alpha=0.5, linewidth=1)

        # Add threshold lines (from config)
        strategy_config = config.get("strategy", {})
        entry_config = strategy_config.get("entry", {})
        params = entry_config.get("params", {})

        # CVD specific thresholds
        if "cvd" in column_name.lower():
            if "long_threshold" in params:
                long_thresh = params["long_threshold"]
                ax.axhline(
                    y=long_thresh,
                    color="#27AE60",  # Green
                    linestyle=":",
                    alpha=0.7,
                    linewidth=1.5,
                    label=f"LONG Threshold ({long_thresh:+.1f}%)",
                    zorder=5,
                )

            if "short_threshold" in params:
                short_thresh = params["short_threshold"]
                ax.axhline(
                    y=short_thresh,
                    color="#E74C3C",  # Red
                    linestyle=":",
                    alpha=0.7,
                    linewidth=1.5,
                    label=f"SHORT Threshold ({short_thresh:+.1f}%)",
                    zorder=5,
                )

            # Plot CVD trade signals if trades are available
            # We need to get trades from the calling context
            # This assumes trades are stored in self.trades_for_plotting
            # Alternatively, modify method signature to accept trades

            # For now, we'll check if we can get trades from config or store them
            # We'll add a method call here:
            if hasattr(self, "current_trades"):
                self._plot_cvd_signals_on_panel(
                    ax, self.current_trades, journal_df, panel_config
                )

        # Set Y limits
        ylim = panel_config.get("ylim")
        if ylim and isinstance(ylim, list):
            ax.set_ylim(ylim[0], ylim[1])

        # Configure axis
        ax.set_ylabel(label, fontsize=11)

        # Get unique legend items
        handles, labels = ax.get_legend_handles_labels()
        unique_labels = []
        unique_handles = []
        for handle, label in zip(handles, labels):
            if label not in unique_labels:
                unique_labels.append(label)
                unique_handles.append(handle)

        if unique_handles:
            ax.legend(
                unique_handles,
                unique_labels,
                loc="upper left",
                fontsize=8,
                framealpha=0.95,
                ncol=2,
            )

        ax.grid(True, alpha=0.3, linestyle="--")

    def _load_indicator_data(
        self, journal_df: pd.DataFrame, config: Dict[str, Any]
    ) -> Dict[str, pd.Series]:
        """Load indicator data from pre-loaded DataFrame."""
        indicator_data = {}

        if self.full_data_df is None:
            return indicator_data

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

            indicator_series = self.full_data_df[column_name]

            # Align to journal timeline
            aligned_series = pd.Series(index=x_axis, dtype=float)

            for i, ts in enumerate(x_axis):
                if ts in indicator_series.index:
                    aligned_series.iloc[i] = indicator_series[ts]
                else:
                    idx = indicator_series.index.get_indexer([ts], method="nearest")[0]
                    aligned_series.iloc[i] = indicator_series.iloc[idx]

            aligned_series = aligned_series.ffill().bfill()
            indicator_data[label] = aligned_series

        return indicator_data

    def _load_indicator_data_for_panel(self, journal_df, panel_config, config):
        """Load indicator data for separate panel."""
        if self.full_data_df is None:
            return None

        column_name = panel_config.get("column")

        if column_name not in self.full_data_df.columns:
            return None

        if "timestamp" in journal_df.columns:
            x_axis = pd.to_datetime(journal_df["timestamp"])
        else:
            x_axis = journal_df.index

        indicator_series = self.full_data_df[column_name]

        # Align to journal timeline
        aligned_series = pd.Series(index=x_axis, dtype=float)

        for i, ts in enumerate(x_axis):
            if ts in indicator_series.index:
                aligned_series.iloc[i] = indicator_series[ts]
            else:
                try:
                    idx = indicator_series.index.get_indexer([ts], method="nearest")[0]
                    aligned_series.iloc[i] = indicator_series.iloc[idx]
                except:
                    aligned_series.iloc[i] = np.nan

        aligned_series = aligned_series.ffill().bfill()

        return aligned_series

    def _get_atr_at_time(self, time_point, use_timestamps=True):
        """Get ATR value at specific time point from full_data_df."""
        if self.full_data_df is None:
            return None

        # Try to find ATR column
        atr_col = None
        for col in self.full_data_df.columns:
            if "atr" in col.lower():
                atr_col = col
                break

        if not atr_col:
            return None

        try:
            if use_timestamps:
                # Try exact match
                if time_point in self.full_data_df.index:
                    return self.full_data_df.loc[time_point, atr_col]
                # Try nearest
                else:
                    idx = self.full_data_df.index.get_indexer(
                        [time_point], method="nearest"
                    )[0]
                    return self.full_data_df[atr_col].iloc[idx]
            else:
                # Use integer index
                idx = int(time_point)
                if idx < len(self.full_data_df):
                    return self.full_data_df[atr_col].iloc[idx]
                else:
                    return None
        except Exception as e:
            logger.debug(f"Error getting ATR at {time_point}: {e}")
            return None

    def _mark_trade_levels(self, ax, trade, entry_time, exit_time, position_type):
        """Mark key levels on the plot."""
        entry_price = trade.get("entry_price")
        exit_price = trade.get("exit_price")

        # Mark entry with arrow
        ax.annotate(
            f"Entry\n${entry_price:.4f}",
            xy=(entry_time, entry_price),
            xytext=(0, 20 if position_type == "long" else -20),
            textcoords="offset points",
            arrowprops=dict(arrowstyle="->", color="blue", alpha=0.7),
            fontsize=8,
            ha="center",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8),
        )

        # Mark exit if exists
        if exit_price and "exit_time" in trade:
            ax.annotate(
                f"Exit\n${exit_price:.4f}\n({trade.get('net_pnl_percent', 0):+.2f}%)",
                xy=(exit_time, exit_price),
                xytext=(0, -20 if position_type == "long" else 20),
                textcoords="offset points",
                arrowprops=dict(
                    arrowstyle="->",
                    color="green" if trade.get("net_pnl", 0) > 0 else "red",
                    alpha=0.7,
                ),
                fontsize=8,
                ha="center",
                bbox=dict(
                    boxstyle="round,pad=0.3",
                    facecolor=(
                        "lightgreen" if trade.get("net_pnl", 0) > 0 else "lightcoral"
                    ),
                    alpha=0.8,
                ),
            )

    def _plot_cvd_signals_on_panel(self, ax_panel, trades, journal_df, panel_config):
        """Plot CVD markers for entry/exit signals on the CVD panel."""
        if not trades:
            return

        trades_df = pd.DataFrame(trades)
        cvd_column = panel_config.get("column", "cvd_ratio_15m")

        # Check if this panel is for CVD
        if "cvd" not in cvd_column.lower():
            return

        # Get journal timestamps
        if "timestamp" in journal_df.columns:
            journal_df["timestamp"] = pd.to_datetime(journal_df["timestamp"])

        for idx, trade in trades_df.iterrows():
            # Get entry time
            entry_time = trade.get("entry_time")
            if not entry_time:
                continue

            # Convert to datetime if string
            if isinstance(entry_time, str):
                entry_time = pd.to_datetime(entry_time)

            # Find nearest journal entry for this time
            if "timestamp" in journal_df.columns:
                # Find closest timestamp in journal
                time_diff = (journal_df["timestamp"] - entry_time).abs()
                closest_idx = time_diff.idxmin()
                closest_time = journal_df.loc[closest_idx, "timestamp"]

                # Get CVD value at that time from full_data_df
                if (
                    self.full_data_df is not None
                    and cvd_column in self.full_data_df.columns
                ):
                    # Find CVD value at closest_time
                    if closest_time in self.full_data_df.index:
                        cvd_value = self.full_data_df.loc[closest_time, cvd_column]
                    else:
                        # Try nearest
                        try:
                            cvd_idx = self.full_data_df.index.get_indexer(
                                [closest_time], method="nearest"
                            )[0]
                            cvd_value = self.full_data_df[cvd_column].iloc[cvd_idx]
                        except:
                            continue

                    # Plot entry marker on CVD panel
                    position_type = trade.get("position_type", "long")
                    marker_color = (
                        "limegreen" if position_type == "long" else "orangered"
                    )
                    marker_shape = "^" if position_type == "long" else "v"

                    ax_panel.scatter(
                        closest_time,
                        cvd_value,
                        color=marker_color,
                        marker=marker_shape,
                        s=120,
                        edgecolors="black",
                        linewidth=1.5,
                        zorder=100,
                        label=(
                            "Entry (LONG)"
                            if position_type == "long" and idx == 0
                            else None
                        ),
                    )

                    # Add text annotation
                    ax_panel.annotate(
                        f"ENTRY\n{cvd_value:.1f}%",
                        xy=(closest_time, cvd_value),
                        xytext=(0, 15 if position_type == "long" else -15),
                        textcoords="offset points",
                        fontsize=7,
                        ha="center",
                        bbox=dict(
                            boxstyle="round,pad=0.2",
                            facecolor=marker_color,
                            alpha=0.8,
                            edgecolor="black",
                        ),
                        color="white",
                        fontweight="bold",
                    )

            # Plot exit marker if available
            # exit_time = trade.get("exit_time")
            # if exit_time and "exit_price" in trade:
            #     if isinstance(exit_time, str):
            #         exit_time = pd.to_datetime(exit_time)

            #     # Find closest journal entry
            #     if "timestamp" in journal_df.columns:
            #         time_diff = (journal_df["timestamp"] - exit_time).abs()
            #         closest_idx = time_diff.idxmin()
            #         closest_time = journal_df.loc[closest_idx, "timestamp"]

            #         # Get CVD value at exit
            #         if (
            #             self.full_data_df is not None
            #             and cvd_column in self.full_data_df.columns
            #         ):
            #             if closest_time in self.full_data_df.index:
            #                 cvd_value = self.full_data_df.loc[closest_time, cvd_column]
            #             else:
            #                 try:
            #                     cvd_idx = self.full_data_df.index.get_indexer(
            #                         [closest_time], method="nearest"
            #                     )[0]
            #                     cvd_value = self.full_data_df[cvd_column].iloc[cvd_idx]
            #                 except:
            #                     continue

            #             # Plot exit marker
            #             pnl = trade.get("net_pnl", 0)
            #             marker_color = "green" if pnl > 0 else "red"

            #             ax_panel.scatter(
            #                 closest_time,
            #                 cvd_value,
            #                 color=marker_color,
            #                 marker="X",  # Different marker for exit
            #                 s=100,
            #                 edgecolors="black",
            #                 linewidth=1.5,
            #                 zorder=100,
            #                 label="Exit (Profit)" if pnl > 0 and idx == 0 else None,
            #             )

            #             # Add exit annotation
            #             ax_panel.annotate(
            #                 f"EXIT\n{cvd_value:.1f}%\n({pnl:+.2f}$)",
            #                 xy=(closest_time, cvd_value),
            #                 xytext=(0, -15 if pnl > 0 else 15),
            #                 textcoords="offset points",
            #                 fontsize=7,
            #                 ha="center",
            #                 bbox=dict(
            #                     boxstyle="round,pad=0.2",
            #                     facecolor=marker_color,
            #                     alpha=0.8,
            #                     edgecolor="black",
            #                 ),
            #                 color="white",
            #                 fontweight="bold",
            #             )

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

    def create_all_plots(self, results, run_dir, config, full_data_df=None):
        """Create all plots."""
        plot_paths = {}
        self.full_data_df = full_data_df

        try:
            # Equity curve
            if results.get("equity_curve"):
                equity_plot_path = run_dir / "equity_curve.png"
                plot_paths["equity"] = self.plot_equity_curve(
                    results["equity_curve"], equity_plot_path
                )

            # Trade distribution
            if results.get("trades"):
                trade_plot_path = run_dir / "trade_distribution.png"
                plot_paths["trades"] = self.plot_trade_distribution(
                    results["trades"], trade_plot_path
                )

            # Price with signals + SL/TP
            if results.get("journal") and results.get("trades"):
                price_plot_path = run_dir / "price_signals.png"
                plot_paths["price"] = self.plot_price_with_signals(
                    journal=results["journal"],
                    trades=results["trades"],
                    config=config,
                    save_path=price_plot_path,
                    full_data_df=full_data_df,
                )

            logger.info(f"Created {len(plot_paths)} plots in {run_dir}")

        except Exception as e:
            logger.error(f"Error creating plots: {e}")
            import traceback

            traceback.print_exc()
        finally:
            self.full_data_df = None

        return plot_paths
