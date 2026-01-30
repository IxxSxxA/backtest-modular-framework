"""
Plot Helper Functions

Utility functions for creating backtest visualizations.
Includes candlestick plotting, trade markers, SL/TP zones, and formatting.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle, FancyBboxPatch
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


def plot_candlesticks_basic(
    ax: plt.Axes,
    data: pd.DataFrame,
    up_color: str = "#26A69A",
    down_color: str = "#EF5350",
    wick_color: str = "#000000",
    alpha: float = 0.8,
):
    """
    Plot candlesticks using basic matplotlib (no mplfinance dependency).

    Args:
        ax: Matplotlib axis
        data: DataFrame with OHLC columns
        up_color: Color for bullish candles
        down_color: Color for bearish candles
        wick_color: Color for wicks
        alpha: Transparency
    """
    # Convert timestamps to matplotlib dates
    dates = mdates.date2num(data.index.to_pydatetime())

    # Calculate bar width (80% of time interval)
    if len(dates) > 1:
        time_delta = dates[1] - dates[0]
        width = time_delta * 0.8
    else:
        width = 0.0003  # Fallback

    # Iterate through candles
    for i, (idx, row) in enumerate(data.iterrows()):
        date = dates[i]
        open_price = row["open"]
        high_price = row["high"]
        low_price = row["low"]
        close_price = row["close"]

        # Determine color
        color = up_color if close_price >= open_price else down_color

        # Draw wick (high-low line)
        ax.plot(
            [date, date],
            [low_price, high_price],
            color=wick_color,
            linewidth=1,
            alpha=alpha,
            solid_capstyle="round",
        )

        # Draw body (open-close rectangle)
        body_height = abs(close_price - open_price)
        body_bottom = min(open_price, close_price)

        rect = Rectangle(
            (date - width / 2, body_bottom),
            width,
            body_height,
            facecolor=color,
            edgecolor=color,
            alpha=alpha,
            linewidth=0.5,
        )
        ax.add_patch(rect)

    # Set limits with padding
    ax.set_xlim(dates[0] - width, dates[-1] + width)

    price_range = data["high"].max() - data["low"].min()
    ax.set_ylim(
        data["low"].min() - price_range * 0.05, data["high"].max() + price_range * 0.05
    )


def plot_trades_markers(
    ax: plt.Axes,
    data: pd.DataFrame,
    trades: List[Dict[str, Any]],
    show_pnl: bool = True,
):
    """Plot entry and exit markers for trades."""
    for trade in trades:
        entry_time = pd.to_datetime(trade["entry_time"])
        exit_time = pd.to_datetime(trade["exit_time"])
        entry_price = trade["entry_price"]
        exit_price = trade["exit_price"]

        # FIX: Use 'position_type' field (lowercase values)
        position_type = trade.get("position_type", "long")  # ← Correct field name
        direction = position_type.upper()  # ← Convert to uppercase for display

        pnl_pct = trade.get("net_pnl_percent", 0)

        # Colors based on direction
        if direction == "LONG":
            entry_color = "#27AE60"
            entry_marker = "^"
            exit_marker = "v"
        else:  # SHORT
            entry_color = "#E74C3C"
            entry_marker = "v"
            exit_marker = "^"

        # Exit color based on P&L
        exit_color = "#27AE60" if pnl_pct > 0 else "#E74C3C"

        # Plot entry marker
        ax.scatter(
            entry_time,
            entry_price,
            marker=entry_marker,
            s=100,
            color=entry_color,
            edgecolors="black",
            linewidths=1.5,
            zorder=10,
            alpha=0.9,
        )

        # Plot exit marker
        ax.scatter(
            exit_time,
            exit_price,
            marker=exit_marker,
            s=100,
            color=exit_color,
            edgecolors="black",
            linewidths=1.5,
            zorder=10,
            alpha=0.9,
        )

        # Add P&L label if enabled
        if show_pnl:
            # Position label above/below based on direction
            y_offset = 20 if direction == "LONG" else -20

            ax.annotate(
                f"{pnl_pct:+.2f}%",
                xy=(exit_time, exit_price),
                xytext=(0, y_offset),
                textcoords="offset points",
                fontsize=7,
                color=exit_color,
                fontweight="bold",
                bbox=dict(
                    boxstyle="round,pad=0.3",
                    facecolor="white",
                    edgecolor=exit_color,
                    alpha=0.8,
                    linewidth=1.5,
                ),
                ha="center",
            )


def plot_sl_tp_zones(
    ax: plt.Axes,
    data: pd.DataFrame,
    trades: List[Dict[str, Any]],
    sl_tp_config: Dict[str, Any],
):
    """
    Plot dynamic TP/SL zones.
    """
    style = sl_tp_config.get("style", {})

    for trade in trades:
        entry_time = pd.to_datetime(trade["entry_time"])
        exit_time = pd.to_datetime(trade["exit_time"])

        # Get trade data
        mask = (data.index >= entry_time) & (data.index <= exit_time)
        trade_data = data.loc[mask]

        if trade_data.empty:
            continue

        # Get TP/SL series
        tp_series = trade_data["take_profit"].dropna()
        sl_series = trade_data["stop_loss"].dropna()

        if tp_series.empty or sl_series.empty:
            continue

        # Plot TP line
        ax.plot(
            tp_series.index,
            tp_series.values,
            color=style.get("tp_color", "#27AE60"),
            linestyle=style.get("line_style", "--"),
            linewidth=style.get("line_width", 1.5),
            alpha=0.8,
            label="Take Profit" if trade == trades[0] else "",
            zorder=5,
        )

        # Plot SL line
        ax.plot(
            sl_series.index,
            sl_series.values,
            color=style.get("sl_color", "#E74C3C"),
            linestyle=style.get("line_style", "--"),
            linewidth=style.get("line_width", 1.5),
            alpha=0.8,
            label="Stop Loss" if trade == trades[0] else "",
            zorder=5,
        )

        # Fill zones
        if style.get("fill_zones", True):
            entry_price = trade["entry_price"]
            position_type = trade.get("position_type", "long")

            if position_type == "long":  # LONG
                # Zone TP
                ax.fill_between(
                    tp_series.index,
                    entry_price,
                    tp_series.values,
                    where=(tp_series.values > entry_price),
                    color=style.get("tp_color", "#27AE60"),
                    alpha=style.get("zone_alpha", 0.1),
                    zorder=2,
                )

                # Zone SL
                ax.fill_between(
                    sl_series.index,
                    sl_series.values,
                    entry_price,
                    where=(sl_series.values < entry_price),
                    color=style.get("sl_color", "#E74C3C"),
                    alpha=style.get("zone_alpha", 0.1),
                    zorder=2,
                )

            else:  # SHORT
                # Zone TP green belove
                ax.fill_between(
                    tp_series.index,
                    tp_series.values,
                    entry_price,
                    where=(tp_series.values < entry_price),
                    color=style.get("tp_color", "#27AE60"),
                    alpha=style.get("zone_alpha", 0.1),
                    zorder=2,
                )

                # Zone SL red above
                ax.fill_between(
                    sl_series.index,
                    entry_price,
                    sl_series.values,
                    where=(sl_series.values > entry_price),
                    color=style.get("sl_color", "#E74C3C"),
                    alpha=style.get("zone_alpha", 0.1),
                    zorder=2,
                )


def format_date_axis(ax: plt.Axes):
    """
    Format x-axis for datetime display.

    Args:
        ax: Matplotlib axis
    """
    # Auto-format based on date range
    locator = mdates.AutoDateLocator(minticks=5, maxticks=15)
    formatter = mdates.ConciseDateFormatter(locator)

    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)

    # Rotate labels for better readability
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")


def add_text_box(
    ax: plt.Axes,
    text: str,
    position: str = "top_right",
    fontsize: int = 9,
    facecolor: str = "white",
    alpha: float = 0.8,
    **kwargs,
):
    """
    Add text box to plot.

    Args:
        ax: Matplotlib axis
        text: Text to display
        position: Position ('top_right', 'top_left', 'bottom_right', 'bottom_left')
        fontsize: Font size
        facecolor: Background color
        alpha: Transparency
        **kwargs: Additional text properties
    """
    positions = {
        "top_right": (0.98, 0.98),
        "top_left": (0.02, 0.98),
        "bottom_right": (0.98, 0.02),
        "bottom_left": (0.02, 0.02),
    }

    x, y = positions.get(position, (0.98, 0.98))

    ha = "right" if "right" in position else "left"
    va = "top" if "top" in position else "bottom"

    ax.text(
        x,
        y,
        text,
        transform=ax.transAxes,
        fontsize=fontsize,
        verticalalignment=va,
        horizontalalignment=ha,
        bbox=dict(
            boxstyle="round,pad=0.5",
            facecolor=facecolor,
            alpha=alpha,
            edgecolor="gray",
        ),
        **kwargs,
    )


def plot_hlines_with_labels(
    ax: plt.Axes,
    levels: List[float],
    labels: Optional[List[str]] = None,
    colors: Optional[List[str]] = None,
    linestyle: str = "--",
    linewidth: float = 1.0,
    alpha: float = 0.5,
):
    """
    Plot multiple horizontal lines with optional labels.

    Args:
        ax: Matplotlib axis
        levels: List of y-values for lines
        labels: Optional list of labels
        colors: Optional list of colors
        linestyle: Line style
        linewidth: Line width
        alpha: Transparency
    """
    if labels is None:
        labels = [None] * len(levels)

    if colors is None:
        colors = ["gray"] * len(levels)

    for level, label, color in zip(levels, labels, colors):
        ax.axhline(
            level,
            color=color,
            linestyle=linestyle,
            linewidth=linewidth,
            alpha=alpha,
            label=label,
        )


def calculate_optimal_figure_size(
    n_panels: int,
    base_width: float = 16.0,
    price_height: float = 6.0,
    panel_height: float = 2.0,
) -> tuple:
    """
    Calculate optimal figure size based on number of panels.

    Args:
        n_panels: Number of panels
        base_width: Base width
        price_height: Height of price chart
        panel_height: Height of each indicator panel

    Returns:
        Tuple of (width, height)
    """
    total_height = price_height + (n_panels - 1) * panel_height
    return (base_width, total_height)


def create_grid_background(
    ax: plt.Axes,
    grid_color: str = "#E0E0E0",
    grid_alpha: float = 0.2,
    grid_style: str = "-",
):
    """
    Create custom grid background.

    Args:
        ax: Matplotlib axis
        grid_color: Grid line color
        grid_alpha: Grid transparency
        grid_style: Grid line style
    """
    ax.grid(
        True,
        which="major",
        color=grid_color,
        linestyle=grid_style,
        linewidth=0.8,
        alpha=grid_alpha,
    )

    ax.grid(
        True,
        which="minor",
        color=grid_color,
        linestyle=":",
        linewidth=0.5,
        alpha=grid_alpha * 0.5,
    )


def add_watermark(
    fig: plt.Figure,
    text: str = "Backtest",
    alpha: float = 0.1,
    fontsize: int = 60,
    color: str = "gray",
):
    """
    Add watermark to figure.

    Args:
        fig: Matplotlib figure
        text: Watermark text
        alpha: Transparency
        fontsize: Font size
        color: Text color
    """
    fig.text(
        0.5,
        0.5,
        text,
        fontsize=fontsize,
        color=color,
        alpha=alpha,
        ha="center",
        va="center",
        rotation=30,
        transform=fig.transFigure,
    )


def save_plot_with_metadata(
    fig: plt.Figure,
    save_path: str,
    metadata: Optional[Dict[str, Any]] = None,
    dpi: int = 150,
):
    """
    Save plot with embedded metadata.

    Args:
        fig: Matplotlib figure
        save_path: Path to save
        metadata: Optional metadata dictionary
        dpi: Resolution
    """
    if metadata is None:
        metadata = {}

    # Add default metadata
    import datetime

    metadata.setdefault("creation_date", datetime.datetime.now().isoformat())
    metadata.setdefault("software", "Trading Framework")

    # Save with metadata
    fig.savefig(
        save_path,
        dpi=dpi,
        bbox_inches="tight",
        metadata=metadata,
    )

    logger.debug(f"Saved plot to {save_path} with metadata: {metadata}")


def style_axis_professional(
    ax: plt.Axes,
    ylabel: str,
    xlabel: str = "",
    title: str = "",
    legend: bool = True,
    grid: bool = True,
):
    """
    Apply professional styling to axis.

    Args:
        ax: Matplotlib axis
        ylabel: Y-axis label
        xlabel: X-axis label
        title: Axis title
        legend: Show legend
        grid: Show grid
    """
    if title:
        ax.set_title(title, fontsize=12, fontweight="bold", pad=10)

    if ylabel:
        ax.set_ylabel(ylabel, fontsize=10, fontweight="bold")

    if xlabel:
        ax.set_xlabel(xlabel, fontsize=10, fontweight="bold")

    if legend:
        ax.legend(
            loc="upper left",
            fontsize=9,
            framealpha=0.9,
            edgecolor="gray",
        )

    if grid:
        ax.grid(True, alpha=0.2, color="#E0E0E0")

    # Style spines
    for spine in ax.spines.values():
        spine.set_edgecolor("#CCCCCC")
        spine.set_linewidth(1.0)

    # Tick parameters
    ax.tick_params(
        axis="both",
        which="major",
        labelsize=9,
        colors="#2C3E50",
    )
