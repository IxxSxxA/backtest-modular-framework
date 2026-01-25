#!/usr/bin/env python3
"""
Trading Framework - Main Entry Point
"""

import yaml
import logging
from pathlib import Path
import pandas as pd

from core.data_loader import DataLoader
from core.resampler import DataResampler  # NEW IMPORT
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
    level=logging.INFO, format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file."""
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config


# REMOVED: resample_to_timeframe() - Now in core/resampler.py


def create_strategy_components(config: dict):
    """
    Factory function to create entry, exit, and risk strategies.

    Args:
        config: Full configuration dictionary

    Returns:
        Tuple of (entry_strategy, exit_strategy, risk_manager)
    """
    strategy_config = config["strategy"]

    # 1. Entry Strategy
    entry_config = strategy_config["entry"]
    entry_name = entry_config["name"]
    entry_params = entry_config.get("params", {})

    if entry_name == "ema_cross_sma":
        entry_strategy = EMACrossSMA(entry_params)
    elif entry_name == "ema_cross_sma_cvd":
        entry_strategy = EMACrossSMACVD(entry_params)
    else:
        raise ValueError(f"Unknown entry strategy: {entry_name}")

    # 2. Exit Strategy
    exit_config = strategy_config["exit"]
    exit_name = exit_config["name"]
    exit_params = exit_config.get("params", {})

    if exit_name == "atr_based_exit":
        exit_strategy = ATRBasedExit(exit_params)
    else:
        raise ValueError(f"Unknown exit strategy: {exit_name}")

    # 3. Risk Manager
    risk_config = strategy_config.get("risk", {})
    risk_name = risk_config.get("name", "fixed_percent")
    risk_params = risk_config.get("params", {})

    if risk_name == "fixed_percent":
        risk_manager = FixedPercent(risk_params)
    else:
        raise ValueError(f"Unknown risk manager: {risk_name}")

    logger.info(f"✅ Created strategies:")
    logger.info(f"   Entry:  {entry_strategy}")
    logger.info(f"   Exit:   {exit_strategy}")
    logger.info(f"   Risk:   {risk_manager.name}")

    return entry_strategy, exit_strategy, risk_manager


def main():
    """Main execution flow."""

    logger.info("=" * 60)
    logger.info("TRADING FRAMEWORK - Starting Backtest")
    logger.info("=" * 60)

    # 1. Load configuration
    logger.info("📄 Loading configuration...")
    config = load_config("config.yaml")

    strategy_tf = config["strategy"]["timeframe"]
    symbol = config["data"]["symbols"][0]

    logger.info(f"   Symbol: {symbol}")
    logger.info(f"   Strategy TF: {strategy_tf}")

    # NEW: Create resampler instance
    resampler = DataResampler()

    # 2. Load FULL historical data for indicators (without date filters)
    logger.info("📊 Loading FULL historical 1m data for indicators...")
    data_loader_full = DataLoader(config)
    data_loader_full.filter_start = None  # Disable date filters
    data_loader_full.filter_end = None
    full_data_1m = data_loader_full.load_single_symbol(symbol)

    logger.info(f"   Full 1m data: {len(full_data_1m)} rows")
    logger.info(
        f"   Full date range: {full_data_1m.index[0]} to {full_data_1m.index[-1]}"
    )

    # 3. Resample FULL data to strategy timeframe for indicators
    logger.info(f"🔄 Resampling FULL data to {strategy_tf} for indicators...")

    # FIX #1 & #2: Use DataResampler
    full_data_resampled = resampler.resample_to_timeframe(
        full_data_1m,
        strategy_tf,
        normalize_index=True,  # Fix index matching
        quality_threshold=0.95,  # Raise error if >5% data loss
    )

    # 4. Calculate indicators on FULL historical data
    logger.info("📈 Calculating indicators on FULL historical data...")
    indicator_manager = IndicatorManager(config=config)  # Pass config!
    indicator_configs = config.get("indicators", [])

    data_with_indicators_full = indicator_manager.calculate_all_indicators(
        data=full_data_resampled,
        indicator_configs=indicator_configs,
        symbol=symbol,
        strategy_tf=strategy_tf,
    )

    logger.info(f"   Indicators calculated on {len(data_with_indicators_full)} bars")

    # 5. Load backtest window data (with date filters applied)
    logger.info("📊 Loading backtest window data...")
    data_loader_window = DataLoader(config)

    # FIX #6: Normalize backtest start to midnight
    window_data_1m = data_loader_window.load_single_symbol(
        symbol,
        normalize_start=True,  # NEW: Normalize to midnight
    )

    logger.info(f"   Window 1m data: {len(window_data_1m)} rows")
    logger.info(
        f"   Window date range: {window_data_1m.index[0]} to {window_data_1m.index[-1]}"
    )

    # 6. Resample window data to strategy timeframe
    if strategy_tf != "1m":
        logger.info(f"🔄 Resampling window data to {strategy_tf}...")

        # FIX #1 & #2: Use DataResampler
        window_data_resampled = resampler.resample_to_timeframe(
            window_data_1m, strategy_tf, normalize_index=True
        )
    else:
        window_data_resampled = window_data_1m

    # 7. Slice indicators for backtest window
    logger.info("✂️ Slicing indicators for backtest window...")

    # FIX #2: Use reindex with ffill for safer matching
    backtest_data = data_with_indicators_full.reindex(
        window_data_resampled.index, method="ffill"
    )

    # Check for missing data
    missing_rows = backtest_data.isnull().any(axis=1).sum()
    if missing_rows > 0:
        logger.warning(
            f"⚠️ {missing_rows} rows with missing indicator data after slice.\n"
            f"   This might indicate index mismatch. Dropping incomplete rows..."
        )
        backtest_data = backtest_data.dropna()

    logger.info(
        f"   Using {len(backtest_data)}/{len(data_with_indicators_full)} bars for backtest"
    )
    logger.info(
        f"   Backtest date range: {backtest_data.index[0]} to {backtest_data.index[-1]}"
    )

    # 8. Create strategy components
    logger.info("⚙️ Creating strategy components...")
    entry_strategy, exit_strategy, risk_manager = create_strategy_components(config)

    # 9. Create backtest engine
    logger.info("🚀 Creating backtest engine...")
    engine = BacktestEngine.from_config(
        config=config,
        data=backtest_data,
        entry_strategy=entry_strategy,
        exit_strategy=exit_strategy,
        risk_manager=risk_manager,
    )

    # 10. Run backtest
    logger.info("▶️ Running backtest...")
    logger.info("=" * 60)

    results = engine.run()

    logger.info("=" * 60)

    # 11. Save results
    logger.info("💾 Saving results...")
    journal_writer = JournalWriter(config)

    file_paths = journal_writer.save_backtest_results(results=results, config=config)

    logger.info("✅ Results saved:")
    for file_type, path in file_paths.items():
        if path:
            logger.info(f"-> {file_type}: {path}")

    # 12. Print summary
    logger.info("📊 Backtest Results:")
    engine.print_summary(results)

    logger.info("=" * 60)
    logger.info("🎉 BACKTEST COMPLETED SUCCESSFULLY")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
