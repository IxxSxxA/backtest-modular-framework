# backtest.py

"""
Main backtesting script.
Loads config, prepares data, and runs backtest.
"""
import sys
import os
import yaml
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.data_loader import DataLoader
from core.indicator_manager import IndicatorManager
from core.engine import BacktestEngine
from core.journal_writer import JournalWriter

# Strategy factories
from strategies.entry.price_above_sma import PriceAboveSMA
from strategies.exit.hold_bars import HoldBars
from strategies.exit.fixed_tp_sl import FixedTPSL
from strategies.risk.fixed_percent import FixedPercent


def setup_logging(level=logging.INFO):
    """Configure logging."""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('backtest.log')
        ]
    )


def load_config(config_path: str = 'config.yaml') -> dict:
    """Load and validate configuration."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Basic validation
    required_sections = ['engine', 'data', 'strategy']
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required config section: {section}")
    
    return config


def create_entry_strategy(config: dict):
    """Create entry strategy instance from config."""
    entry_config = config['strategy']['entry']
    strategy_name = entry_config['name']
    params = entry_config.get('params', {})
    
    # Strategy mapping (will be auto-discovered in future phases)
    strategy_map = {
        'price_above_sma': PriceAboveSMA,
    }
    
    if strategy_name not in strategy_map:
        raise ValueError(
            f"Entry strategy '{strategy_name}' not found. "
            f"Available: {list(strategy_map.keys())}"
        )
    
    StrategyClass = strategy_map[strategy_name]
    return StrategyClass(params)


def create_exit_strategy(config: dict):
    """Create exit strategy instance from config."""
    exit_config = config['strategy']['exit']
    strategy_name = exit_config['name']
    params = exit_config.get('params', {})
    
    # Strategy mapping (will be auto-discovered in future phases)
    strategy_map = {
        'hold_bars': HoldBars,
        'fixed_tp_sl': FixedTPSL,
    }
    
    if strategy_name not in strategy_map:
        raise ValueError(
            f"Exit strategy '{strategy_name}' not found. "
            f"Available: {list(strategy_map.keys())}"
        )
    
    StrategyClass = strategy_map[strategy_name]
    return StrategyClass(params)


def create_risk_manager(config: dict):
    """Create risk manager instance from config."""

    
    risk_config = config['strategy']['risk']
    strategy_name = risk_config['name']
    params = risk_config.get('params', {})
    
    # Risk manager mapping
    risk_map = {
        'fixed_percent': FixedPercent,
    }
    
    if strategy_name not in risk_map:
        raise ValueError(
            f"Risk manager '{strategy_name}' not found. "
            f"Available: {list(risk_map.keys())}"
        )
    
    StrategyClass = risk_map[strategy_name]
    return StrategyClass(params)


def prepare_data(config: dict) -> pd.DataFrame:
    """Load data and calculate indicators."""
    logger = logging.getLogger(__name__)
    
    # Load data
    logger.info("Loading data...")
    data_loader = DataLoader(config)
    data = data_loader.load_single_symbol(config['data']['symbols'][0])
    
    # Calculate indicators
    logger.info("Calculating indicators...")
    indicator_manager = IndicatorManager()
    
    if 'indicators' in config:
        data = indicator_manager.calculate_all_indicators(
            data=data,
            indicator_configs=config['indicators'],
            symbol=config['data']['symbols'][0],
            timeframe=config['data']['timeframe']
        )
    
    logger.info(f"Data prepared: {len(data):,} rows, {len(data.columns)} columns")
    return data


def main():
    """Main backtest execution."""
    print("\n" + "="*60)
    print("TRADING FRAMEWORK - Backtest Engine")
    print("="*60)
    
    try:
        # Setup
        setup_logging()
        logger = logging.getLogger(__name__)
        
        # Load config
        logger.info("Loading configuration...")
        config = load_config()
        
        print(f"\n📋 Configuration:")
        print(f"  Symbol: {config['data']['symbols'][0]}")
        print(f"  Timeframe: {config['data']['timeframe']}")
        print(f"  Initial Capital: ${config['engine']['initial_capital']:,.2f}")
        print(f"  Commission: {config['engine']['commission']*100:.2f}%")
        print(f"  Entry Strategy: {config['strategy']['entry']['name']}")
        print(f"  Exit Strategy: {config['strategy']['exit']['name']}")
        
        if 'risk' in config['strategy']:
            risk_params = config['strategy']['risk']['params']
            risk_pct = risk_params.get('risk_per_trade', 0.02) * 100
            print(f"  Risk Manager: {config['strategy']['risk']['name']} ({risk_pct:.1f}% risk per trade)")
        
        # Prepare data
        data = prepare_data(config)
        
        # Create strategies
        logger.info("Creating strategies...")
        entry_strategy = create_entry_strategy(config)
        exit_strategy = create_exit_strategy(config)
        risk_manager = create_risk_manager(config)
        
        # Create and run engine
        logger.info("Initializing backtest engine...")
        engine = BacktestEngine(
            data=data,
            entry_strategy=entry_strategy,
            exit_strategy=exit_strategy,
            risk_manager=risk_manager,
            initial_capital=config['engine']['initial_capital'],
            commission=config['engine']['commission'],
            lookback_window=config['engine']['lookback_window']
        )
        
        # Run backtest
        logger.info("Running backtest...")
        results = engine.run()
        
        # Print summary to console
        engine.print_summary(results)
        
        # Save results using JournalWriter - FIXED: pass config parameter
        logger.info("Saving results...")
        journal_writer = JournalWriter(config)  # <-- QUI È IL FIX!
        saved_files = journal_writer.save_backtest_results(results, config)
        
        print(f"\n💾 Results saved to: {list(saved_files.keys())}")
        for file_type, file_path in saved_files.items():
            if file_path:
                print(f"  {file_type}: {file_path}")
        
        logger.info("Backtest completed successfully!")
        return 0
        
    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
