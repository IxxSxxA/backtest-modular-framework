#!/usr/bin/env python3
"""
Grid Search Results Analysis
Generates heatmaps and detailed reports from grid search results
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import numpy as np
import yaml

# Set style
plt.style.use("seaborn-v0_8-darkgrid")
sns.set_palette("husl")


def load_results(results_dir: str = "data/grid_results/"):
    """Load grid search results"""
    results_path = Path(results_dir) / "grid_results_matrix.csv"

    if not results_path.exists():
        raise FileNotFoundError(f"Results file not found: {results_path}")

    df = pd.read_csv(results_path)
    return df


def create_heatmap(df: pd.DataFrame, metric: str, title: str, output_path: Path):
    """
    Create heatmap for TP/SL grid

    Args:
        df: DataFrame with results for single timeframe
        metric: Metric to visualize
        title: Plot title
        output_path: Where to save the plot
    """
    # Pivot table for heatmap
    pivot = df.pivot_table(
        index="sl_multiplier", columns="tp_multiplier", values=metric, aggfunc="mean"
    )

    # Sort for better visualization
    pivot = pivot.sort_index(ascending=False)

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 8))

    # Choose colormap based on metric
    if "drawdown" in metric.lower():
        cmap = "RdYlGn_r"  # Reversed: red is bad (high DD)
    else:
        cmap = "RdYlGn"  # Green is good

    # Create heatmap
    sns.heatmap(
        pivot,
        annot=True,
        fmt=".2f",
        cmap=cmap,
        center=pivot.mean().mean(),
        linewidths=0.5,
        cbar_kws={"label": metric},
        ax=ax,
    )

    ax.set_title(title, fontsize=14, fontweight="bold", pad=20)
    ax.set_xlabel("TP Multiplier", fontsize=12, fontweight="bold")
    ax.set_ylabel("SL Multiplier", fontsize=12, fontweight="bold")

    # Find best value
    if "drawdown" in metric.lower():
        best_val = pivot.min().min()
        best_idx = pivot.stack().idxmin()
    else:
        best_val = pivot.max().max()
        best_idx = pivot.stack().idxmax()

    # Add best value annotation
    fig.text(
        0.5,
        0.02,
        f"Best: SL={best_idx[0]}, TP={best_idx[1]} → {metric}={best_val:.2f}",
        ha="center",
        fontsize=10,
        fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="lightblue", alpha=0.7),
    )

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"   ✅ Saved: {output_path}")


def create_comparison_plot(df: pd.DataFrame, output_path: Path):
    """
    Create comparison plot between timeframes
    Shows average performance across all TP/SL combinations
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(
        "Timeframe Comparison - Average Performance", fontsize=16, fontweight="bold"
    )

    metrics = [
        ("total_pnl", "Total PnL ($)"),
        ("win_rate", "Win Rate (%)"),
        ("profit_factor", "Profit Factor"),
        ("max_drawdown", "Max Drawdown (%)"),
    ]

    for ax, (metric, label) in zip(axes.flatten(), metrics):
        # Group by timeframe
        grouped = df.groupby("timeframe")[metric].agg(["mean", "std"])

        # Bar plot
        x = range(len(grouped))
        bars = ax.bar(x, grouped["mean"], yerr=grouped["std"], capsize=5, alpha=0.7)

        # Color bars
        colors = plt.cm.RdYlGn(np.linspace(0.3, 0.9, len(grouped)))
        if "drawdown" in metric:
            colors = colors[::-1]  # Reverse for drawdown

        for bar, color in zip(bars, colors):
            bar.set_color(color)

        ax.set_xticks(x)
        ax.set_xticklabels(grouped.index, fontsize=10, fontweight="bold")
        ax.set_ylabel(label, fontsize=10, fontweight="bold")
        ax.grid(axis="y", alpha=0.3)

        # Add value labels on bars
        for i, (mean_val, std_val) in enumerate(zip(grouped["mean"], grouped["std"])):
            ax.text(
                i,
                mean_val + std_val,
                f"{mean_val:.2f}",
                ha="center",
                va="bottom",
                fontsize=9,
                fontweight="bold",
            )

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"   ✅ Saved: {output_path}")


def create_scatter_plot(df: pd.DataFrame, output_path: Path):
    """
    Create scatter plot: Risk (Max DD) vs Return (Total PnL)
    Colored by timeframe, sized by Sharpe Ratio
    """
    fig, ax = plt.subplots(figsize=(12, 8))

    timeframes = df["timeframe"].unique()
    colors = plt.cm.Set2(np.linspace(0, 1, len(timeframes)))

    for tf, color in zip(timeframes, colors):
        tf_data = df[df["timeframe"] == tf]

        scatter = ax.scatter(
            tf_data["max_drawdown"] * 100,  # Convert to %
            tf_data["total_pnl"],
            s=tf_data["profit_factor"] * 50,  # Size by Profit Factor
            c=[color],
            alpha=0.6,
            edgecolors="black",
            linewidth=0.5,
            label=tf,
        )

    ax.set_xlabel("Max Drawdown (%)", fontsize=12, fontweight="bold")
    ax.set_ylabel("Total PnL ($)", fontsize=12, fontweight="bold")
    ax.set_title(
        "Risk vs Return Analysis\n(Bubble size = Profit Factor)",
        fontsize=14,
        fontweight="bold",
        pad=20,
    )
    ax.legend(title="Timeframe", fontsize=10, title_fontsize=11)
    ax.grid(alpha=0.3)

    # Add quadrant lines
    ax.axhline(y=0, color="red", linestyle="--", alpha=0.3, linewidth=1)
    ax.axvline(
        x=df["max_drawdown"].mean() * 100,
        color="gray",
        linestyle="--",
        alpha=0.3,
        linewidth=1,
    )

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"   ✅ Saved: {output_path}")


def generate_detailed_report(df: pd.DataFrame, output_path: Path):
    """Generate detailed text report with statistics"""

    with open(output_path, "w") as f:
        f.write("=" * 100 + "\n")
        f.write("GRID SEARCH - DETAILED ANALYSIS REPORT\n")
        f.write("=" * 100 + "\n\n")

        # Overall statistics
        f.write("OVERALL STATISTICS\n")
        f.write("-" * 100 + "\n")
        f.write(f"Total Configurations Tested: {len(df)}\n")
        f.write(f"Timeframes: {', '.join(df['timeframe'].unique())}\n")

        # Show indicator parameters by timeframe
        f.write(f"\nIndicator Parameters by Timeframe:\n")
        for tf in df["timeframe"].unique():
            tf_data = df[df["timeframe"] == tf]
            f.write(f"  {tf}:\n")
            f.write(f"    EMA: {tf_data['ema_period'].unique()}\n")
            f.write(f"    SMA: {tf_data['sma_period'].unique()}\n")
            f.write(f"    ATR: {tf_data['atr_period'].unique()}\n")

        f.write(f"\nTP/SL Ranges:\n")
        f.write(f"  TP: {df['tp_multiplier'].min()} - {df['tp_multiplier'].max()}\n")
        f.write(f"  SL: {df['sl_multiplier'].min()} - {df['sl_multiplier'].max()}\n\n")

        # Best configurations
        f.write("=" * 100 + "\n")
        f.write("BEST CONFIGURATIONS\n")
        f.write("=" * 100 + "\n\n")

        metrics_to_rank = [
            ("profit_factor", "Profit Factor", False),
            ("total_pnl", "Total PnL", False),
            ("win_rate", "Win Rate", False),
            ("max_drawdown", "Max Drawdown", True),  # True = lower is better
        ]

        for metric, label, ascending in metrics_to_rank:
            f.write(f"\nBEST BY {label.upper()}:\n")
            f.write("-" * 100 + "\n")

            best = df.nsmallest(3, metric) if ascending else df.nlargest(3, metric)

            for idx, row in best.iterrows():
                f.write(f"\n{row['run_id']}\n")
                f.write(
                    f"  TF: {row['timeframe']} | "
                    f"EMA: {row['ema_period']} | "
                    f"SMA: {row['sma_period']} | "
                    f"ATR: {row['atr_period']}\n"
                )
                f.write(f"  TP: {row['tp_multiplier']} | SL: {row['sl_multiplier']}\n")
                f.write(
                    f"  PnL: ${row['total_pnl']:.2f} ({row['total_pnl_pct']:.2f}%) | "
                )
                f.write(f"Win Rate: {row['win_rate']:.2%} | ")
                f.write(f"Profit Factor: {row['profit_factor']:.2f} | ")
                f.write(f"Max DD: {row['max_drawdown']:.2%}\n")
                f.write(f"  Trades: {row['total_trades']} | ")
                f.write(f"Avg P/L: ${row['avg_pnl_per_trade']:.2f} | ")
                f.write(f"Profit Factor: {row['profit_factor']:.2f}\n")

        # Analysis by timeframe
        f.write("\n" + "=" * 100 + "\n")
        f.write("ANALYSIS BY TIMEFRAME\n")
        f.write("=" * 100 + "\n")

        for tf in df["timeframe"].unique():
            tf_data = df[df["timeframe"] == tf]

            f.write(f"\n{tf} TIMEFRAME ({len(tf_data)} configurations)\n")
            f.write("-" * 100 + "\n")

            f.write(f"\nIndicator Parameters:\n")
            f.write(f"  EMA: {tf_data['ema_period'].unique()}\n")
            f.write(f"  SMA: {tf_data['sma_period'].unique()}\n")
            f.write(f"  ATR: {tf_data['atr_period'].unique()}\n")

            f.write(f"\nAverage Performance:\n")
            f.write(
                f"  Total PnL:      ${tf_data['total_pnl'].mean():.2f} ± ${tf_data['total_pnl'].std():.2f}\n"
            )
            f.write(
                f"  Win Rate:       {tf_data['win_rate'].mean():.2%} ± {tf_data['win_rate'].std():.2%}\n"
            )
            if "profit_factor" in tf_data.columns:
                f.write(
                    f"  Profit Factor:  {tf_data['profit_factor'].mean():.3f} ± {tf_data['profit_factor'].std():.3f}\n"
                )
            f.write(
                f"  Max Drawdown:   {tf_data['max_drawdown'].mean():.2%} ± {tf_data['max_drawdown'].std():.2%}\n"
            )
            f.write(
                f"  Trades:         {tf_data['total_trades'].mean():.0f} ± {tf_data['total_trades'].std():.0f}\n"
            )

            f.write(f"\nBest Configuration:\n")
            if "profit_factor" in tf_data.columns:
                best_config = tf_data.nlargest(1, "profit_factor").iloc[0]
            else:
                best_config = tf_data.nlargest(1, "total_pnl").iloc[0]
            f.write(f"  {best_config['run_id']}\n")
            f.write(
                f"  Indicators: EMA={best_config['ema_period']}, "
                f"SMA={best_config['sma_period']}, "
                f"ATR={best_config['atr_period']}\n"
            )
            f.write(
                f"  TP: {best_config['tp_multiplier']} | SL: {best_config['sl_multiplier']}\n"
            )
            f.write(
                f"  PnL: ${best_config['total_pnl']:.2f} | Profit Factor: {best_config['profit_factor']:.2f}\n"
            )

        # Correlation analysis
        f.write("\n" + "=" * 100 + "\n")
        f.write("CORRELATION ANALYSIS\n")
        f.write("=" * 100 + "\n\n")

        corr_cols = [
            "tp_multiplier",
            "sl_multiplier",
            "total_pnl",
            "win_rate",
            "profit_factor",
            "max_drawdown",
        ]
        corr_cols = [col for col in corr_cols if col in df.columns]

        if len(corr_cols) >= 2:
            corr = df[corr_cols].corr()

            f.write("Correlation Matrix:\n")
            f.write(corr.to_string())
            f.write("\n\n")

            f.write("Key Insights:\n")
            f.write(
                f"  TP vs PnL correlation:  {corr.loc['tp_multiplier', 'total_pnl']:+.3f}\n"
            )
            f.write(
                f"  SL vs PnL correlation:  {corr.loc['sl_multiplier', 'total_pnl']:+.3f}\n"
            )
            if "profit_factor" in corr.index:
                f.write(
                    f"  TP vs Profit Factor correlation: {corr.loc['tp_multiplier', 'profit_factor']:+.3f}\n"
                )
                f.write(
                    f"  SL vs Profit Factor correlation: {corr.loc['sl_multiplier', 'profit_factor']:+.3f}\n"
                )

        f.write("\n" + "=" * 100 + "\n")
        f.write("END OF REPORT\n")
        f.write("=" * 100 + "\n")

    print(f"   ✅ Saved: {output_path}")


def main():
    """Main analysis execution"""

    print("=" * 80)
    print("GRID SEARCH ANALYSIS - Starting")
    print("=" * 80)

    # Load results
    print("\n📂 Loading results...")
    df = load_results()
    print(f"   Loaded {len(df)} configurations")

    # Create output directory
    output_dir = Path("data/grid_results/analysis")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate heatmaps for each timeframe
    print("\n🔥 Generating heatmaps...")

    timeframes = df["timeframe"].unique()
    metrics = [
        ("total_pnl", "Total PnL ($)"),
        ("win_rate", "Win Rate"),
        ("max_drawdown", "Max Drawdown"),
        ("profit_factor", "Profit Factor"),
    ]

    for tf in timeframes:
        print(f"\n   Timeframe: {tf}")
        tf_data = df[df["timeframe"] == tf]

        for metric, label in metrics:
            create_heatmap(
                tf_data,
                metric=metric,
                title=f"{tf} - {label} Heatmap",
                output_path=output_dir / f"heatmap_{tf}_{metric}.png",
            )

    # Generate comparison plots
    print("\n📊 Generating comparison plots...")
    create_comparison_plot(df, output_dir / "comparison_timeframes.png")
    create_scatter_plot(df, output_dir / "risk_return_scatter.png")

    # Generate detailed report
    print("\n📝 Generating detailed report...")
    generate_detailed_report(df, output_dir / "detailed_analysis.txt")

    print("\n" + "=" * 80)
    print("🎉 ANALYSIS COMPLETED")
    print(f"   Output directory: {output_dir}")
    print("=" * 80)


if __name__ == "__main__":
    main()
