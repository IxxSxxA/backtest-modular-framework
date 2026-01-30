#!/usr/bin/env python3
"""
Grid Search Backtesting
Runs multiple backtests with different parameter combinations
"""

import yaml
import logging
from pathlib import Path
import pandas as pd
from datetime import datetime
from itertools import product
import copy

from core.data_loader import DataLoader
from core.resampler import DataResampler
from core.indicator_manager import IndicatorManager
from core.engine import BacktestEngine
from core.journal_writer import JournalWriter

# Import strategy components
from strategies.entry.ema_cross_sma import EMACrossSMA
from strategies.entry.ema_cross_sma_cvd import EMACrossSMACVD
from strategies.exit.atr_based_exit import ATRBasedExit
from strategies.risk.fixed_percent import FixedPercent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
)

logger = logging.getLogger(__name__)


def load_configs():
    """Load base config and grid config"""
    with open("config.yaml", "r") as f:
        base_config = yaml.safe_load(f)

    with open("config_grid.yaml", "r") as f:
        grid_config = yaml.safe_load(f)

    return base_config, grid_config


def create_strategy_components(config: dict):
    """Factory function to create entry, exit, and risk strategies"""
    strategy_config = config["strategy"]

    # Entry Strategy
    entry_config = strategy_config["entry"]
    entry_name = entry_config["name"]
    entry_params = {
        **entry_config.get("params", {}),
        "indicators": entry_config.get("indicators", []),
    }

    if entry_name == "ema_cross_sma":
        entry_strategy = EMACrossSMA(entry_params)
    elif entry_name == "ema_cross_sma_cvd":
        entry_strategy = EMACrossSMACVD(entry_params)
    else:
        raise ValueError(f"Unknown entry strategy: {entry_name}")

    # Exit Strategy
    exit_config = strategy_config["exit"]
    exit_name = exit_config["name"]
    exit_params = {
        **exit_config.get("params", {}),
        "indicators": exit_config.get("indicators", []),
    }

    if exit_name == "atr_based_exit":
        exit_strategy = ATRBasedExit(exit_params)
    else:
        raise ValueError(f"Unknown exit strategy: {exit_name}")

    # Risk Manager
    risk_config = strategy_config.get("risk", {})
    risk_name = risk_config.get("name", "fixed_percent")
    risk_params = {
        **risk_config.get("params", {}),
        "indicators": risk_config.get("indicators", []),
    }

    if risk_name == "fixed_percent":
        risk_manager = FixedPercent(risk_params)
    else:
        raise ValueError(f"Unknown risk manager: {risk_name}")

    return entry_strategy, exit_strategy, risk_manager


def run_single_backtest(config: dict, run_id: str) -> dict:
    """
    Run a single backtest with given configuration

    Returns:
        Dictionary with results metrics
    """
    strategy_tf = config["strategy"]["timeframe"]
    symbol = config["data"]["symbols"][0]

    # Create resampler
    resampler = DataResampler()

    # Load FULL historical data for indicators
    data_loader_full = DataLoader(config)
    data_loader_full.filter_start = None
    data_loader_full.filter_end = None
    full_data_1m = data_loader_full.load_single_symbol(symbol)

    # Resample to strategy timeframe
    full_data_resampled = resampler.resample_to_timeframe(
        full_data_1m,
        strategy_tf,
        normalize_index=True,
        quality_threshold=0.95,
    )

    # Create strategy components
    entry_strategy, exit_strategy, risk_manager = create_strategy_components(config)

    # Calculate indicators
    indicator_manager = IndicatorManager(config=config)
    extra_indicators = config.get("extra_indicators", [])

    data_with_indicators_full = indicator_manager.calculate_from_strategies(
        data=full_data_resampled,
        entry=entry_strategy,
        exit=exit_strategy,
        risk=risk_manager,
        symbol=symbol,
        strategy_tf=strategy_tf,
        extra_indicators=extra_indicators,
    )

    # Load backtest window data
    data_loader_window = DataLoader(config)
    window_data_1m = data_loader_window.load_single_symbol(
        symbol,
        normalize_start=True,
    )

    # Resample window data
    if strategy_tf != "1m":
        window_data_resampled = resampler.resample_to_timeframe(
            window_data_1m, strategy_tf, normalize_index=True
        )
    else:
        window_data_resampled = window_data_1m

    # Slice indicators for backtest window
    backtest_data = data_with_indicators_full.reindex(
        window_data_resampled.index, method="ffill"
    )
    backtest_data = backtest_data.dropna()

    # Create and run backtest engine
    engine = BacktestEngine.from_config(
        config=config,
        data=backtest_data,
        entry_strategy=entry_strategy,
        exit_strategy=exit_strategy,
        risk_manager=risk_manager,
    )

    results = engine.run()

    # Extract key metrics (directly from results, not results["summary"])
    metrics = {
        "run_id": run_id,
        "timeframe": strategy_tf,
        "ema_period": config["strategy"]["entry"]["indicators"][0][
            "period"
        ],  # First indicator is EMA
        "sma_period": config["strategy"]["entry"]["indicators"][1][
            "period"
        ],  # Second indicator is SMA
        "atr_period": config["strategy"]["exit"]["indicators"][0][
            "period"
        ],  # Exit indicator is ATR
        "tp_multiplier": config["strategy"]["exit"]["params"]["tp_multiplier"],
        "sl_multiplier": config["strategy"]["exit"]["params"]["sl_multiplier"],
        "total_trades": results.get("total_trades", 0),
        "win_rate": results.get("win_rate", 0) / 100,  # Convert to decimal (0-1)
        "total_pnl": results.get("total_net_pnl", 0),
        "total_pnl_pct": results.get("total_return_percent", 0),
        # "sharpe_ratio": results.get("sharpe_ratio", 0),
        "max_drawdown": results.get("max_drawdown_percent", 0)
        / 100,  # Convert to decimal
        "avg_pnl_per_trade": results.get("avg_net_pnl", 0),
        "profit_factor": results.get("profit_factor", 0),
        "final_capital": results.get(
            "final_total_equity", results.get("initial_capital", 0)
        ),
    }

    return metrics, results


def main():
    """Main grid search execution"""

    logger.info("=" * 80)
    logger.info("GRID SEARCH BACKTESTING - Starting")
    logger.info("=" * 80)

    # Load configurations
    base_config, grid_config = load_configs()

    # Extract grid configurations
    configurations = grid_config["grid"]["configurations"]

    # Calculate total combinations
    total_runs = sum(
        len(cfg["tp_multipliers"]) * len(cfg["sl_multipliers"])
        for cfg in configurations
    )

    logger.info(f"📊 Grid Configuration:")
    logger.info(f"   Configurations: {len(configurations)}")
    for cfg in configurations:
        logger.info(
            f"   - {cfg['timeframe']}: "
            f"EMA={cfg['indicators']['ema_period']}, "
            f"SMA={cfg['indicators']['sma_period']}, "
            f"ATR={cfg['indicators']['atr_period']}"
        )
    logger.info(f"   Total Runs: {total_runs}")
    logger.info("=" * 80)

    # Create output directory
    output_dir = Path(grid_config["output"]["results_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    # Store all results
    all_results = []

    # Generate all combinations from configurations
    run_number = 0
    for cfg in configurations:
        tf = cfg["timeframe"]
        indicator_params = cfg["indicators"]
        tp_multipliers = cfg["tp_multipliers"]
        sl_multipliers = cfg["sl_multipliers"]

        for tp_mult, sl_mult in product(tp_multipliers, sl_multipliers):
            run_number += 1
            run_id = (
                f"TF{tf}_"
                f"EMA{indicator_params['ema_period']}_"
                f"SMA{indicator_params['sma_period']}_"
                f"ATR{indicator_params['atr_period']}_"
                f"TP{tp_mult}_SL{sl_mult}"
            )

            logger.info(f"\n{'='*80}")
            logger.info(f"▶️  RUN {run_number}/{total_runs}: {run_id}")
            logger.info(f"{'='*80}")

            # Create config for this run
            run_config = copy.deepcopy(base_config)
            run_config["strategy"]["timeframe"] = tf

            # Update indicator parameters in entry strategy
            for indicator in run_config["strategy"]["entry"]["indicators"]:
                if indicator["name"] == "ema":
                    indicator["period"] = indicator_params["ema_period"]
                elif indicator["name"] == "sma":
                    indicator["period"] = indicator_params["sma_period"]

            # Update indicator parameters in exit strategy
            for indicator in run_config["strategy"]["exit"]["indicators"]:
                if indicator["name"] == "atr":
                    indicator["period"] = indicator_params["atr_period"]

            # Update TP/SL multipliers
            run_config["strategy"]["exit"]["params"]["tp_multiplier"] = tp_mult
            run_config["strategy"]["exit"]["params"]["sl_multiplier"] = sl_mult

            # Disable plotting for grid runs (too many plots)
            run_config["output"]["plots"]["enabled"] = False

            try:
                # Run backtest
                metrics, full_results = run_single_backtest(run_config, run_id)

                # Log summary
                logger.info(f"✅ Completed: {run_id}")
                logger.info(f"   Trades: {metrics['total_trades']}")
                logger.info(f"   Win Rate: {metrics['win_rate']:.2%}")
                logger.info(
                    f"   Total PnL: ${metrics['total_pnl']:.2f} ({metrics['total_pnl_pct']:.2f}%)"
                )
                logger.info(f"   Profit Factor: {metrics['profit_factor']:.2f}")
                logger.info(f"   Max DD: {metrics['max_drawdown']:.2%}")

                # Save individual results if enabled
                if grid_config["output"]["save_individual"]:
                    journal_writer = JournalWriter(run_config)
                    journal_writer.save_backtest_results(
                        results=full_results,
                        config=run_config,
                        strategy_name=run_id,  # Use run_id as strategy_name
                    )

                all_results.append(metrics)

            except Exception as e:
                import traceback

                logger.error(f"❌ Failed: {run_id}")
                logger.error(f"   Error: {str(e)}")
                logger.error(f"   Full traceback:")
                logger.error(traceback.format_exc())
                continue

    # Save aggregated results
    logger.info("\n" + "=" * 80)
    logger.info("💾 Saving aggregated results...")

    # Check if we have any successful results
    if not all_results:
        logger.error("❌ No successful backtests! All runs failed.")
        logger.error("   Check the error messages above for details.")
        return

    results_df = pd.DataFrame(all_results)

    # Verify required columns exist (SENZA sharpe_ratio)
    required_cols = [
        "total_pnl",
        "win_rate",
        "max_drawdown",
        "profit_factor",
    ]  # Rimuovi sharpe_ratio
    missing_cols = [col for col in required_cols if col not in results_df.columns]

    if missing_cols:
        logger.error(f"❌ Missing required columns: {missing_cols}")
        logger.error(f"   Available columns: {list(results_df.columns)}")
        logger.error("   Saving partial results only...")

    # Save matrix CSV
    matrix_path = output_dir / grid_config["output"]["matrix_file"]
    results_df.to_csv(matrix_path, index=False)
    logger.info(f"   Matrix saved: {matrix_path}")

    # Generate summary report only if we have all required data
    if not missing_cols:
        summary_path = output_dir / grid_config["output"]["summary_file"]
        with open(summary_path, "w") as f:
            f.write("=" * 80 + "\n")
            f.write("GRID SEARCH SUMMARY\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Total Runs: {len(results_df)}\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # TOP 5 BY PROFIT FACTOR (invece di Sharpe)
            f.write("=" * 80 + "\n")
            f.write("TOP 5 CONFIGURATIONS BY PROFIT FACTOR\n")
            f.write("=" * 80 + "\n")
            top_pf = results_df.nlargest(5, "profit_factor")
            f.write(top_pf.to_string(index=False))
            f.write("\n\n")

            f.write("=" * 80 + "\n")
            f.write("TOP 5 CONFIGURATIONS BY TOTAL PNL\n")
            f.write("=" * 80 + "\n")
            top_pnl = results_df.nlargest(5, "total_pnl")
            f.write(top_pnl.to_string(index=False))
            f.write("\n\n")

            f.write("=" * 80 + "\n")
            f.write("TOP 5 CONFIGURATIONS BY WIN RATE\n")
            f.write("=" * 80 + "\n")
            top_winrate = results_df.nlargest(5, "win_rate")
            f.write(top_winrate.to_string(index=False))
            f.write("\n\n")

            f.write("=" * 80 + "\n")
            f.write("STATISTICS BY TIMEFRAME\n")
            f.write("=" * 80 + "\n")

            # Get unique timeframes from results
            unique_timeframes = results_df["timeframe"].unique()

            for tf in unique_timeframes:
                tf_data = results_df[results_df["timeframe"] == tf]
                if len(tf_data) == 0:
                    continue
                f.write(f"\n{tf} Timeframe:\n")
                f.write(f"  Configurations tested: {len(tf_data)}\n")
                f.write(f"  Avg PnL: ${tf_data['total_pnl'].mean():.2f}\n")
                f.write(f"  Avg Win Rate: {tf_data['win_rate'].mean():.2%}\n")
                f.write(
                    f"  Avg Profit Factor: {tf_data['profit_factor'].mean():.3f}\n"
                )  # Cambiato qui
                f.write(f"  Avg Max DD: {tf_data['max_drawdown'].mean():.2%}\n")

                # Show indicator parameters used
                f.write(f"  Indicator params:\n")
                f.write(f"    EMA: {tf_data['ema_period'].unique()}\n")
                f.write(f"    SMA: {tf_data['sma_period'].unique()}\n")
                f.write(f"    ATR: {tf_data['atr_period'].unique()}\n")

        logger.info(f"   Summary saved: {summary_path}")
    else:
        logger.warning("   Skipping summary report due to missing data")

    logger.info("\n" + "=" * 80)
    logger.info(f"🎉 GRID SEARCH COMPLETED - {len(results_df)}/{total_runs} successful")
    logger.info(f"   Results: {matrix_path}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
