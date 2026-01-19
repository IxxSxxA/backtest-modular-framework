
# PROJECT STRUCTURE

## 📁 File and Folder Organization

```txt
trading_framework/
│
├── 📁 data/ # ALL data (NOT versioned in git)
│ ├── 📁 raw/ # Raw exchange data
│ │ ├── BTCUSDT_1m.parquet # Format: {SYMBOL}{TIMEFRAME}.parquet
│ │ ├── ETHUSDT_1m.parquet
│ │ └── .gitkeep
│ │
│ ├── 📁 indicators/ # Precalculated indicators (organized cache)
│ │ ├── BTCUSDT/ # Folder per symbol
│ │ │ ├── sma_20_1m.parquet # Format: {INDICATOR}{PARAMS}_{TF}.parquet
│ │ │ ├── rsi_14_1m.parquet
│ │ │ └── ema_50_1h.parquet
│ │ ├── ETHUSDT/
│ │ │ └── ...
│ │ └── .gitkeep
│ │
│ ├── 📁 journals/ # Complete backtest journals
│ │ ├── BTCUSDT_ema_cross_fixed_tp_sl_20250116_143025.parquet
│ │ ├── ETHUSDT_rsi_oversold_trailing_20250116_143030.parquet
│ │ └── .gitkeep
│ │
│ └── 📁 strategy_ready/ # Strategy-ready datasets (final merge)
│ └── .gitkeep
│
├── 📁 core/ # CORE CODE (not modified often)
│ ├── init.py
│ ├── engine.py # Main BacktestEngine
│ ├── indicator_manager.py # Intelligent indicator cache management
│ ├── journal_writer.py # Parquet journal writing
│ ├── risk_manager.py # Risk management and position sizing
│ └── data_loader.py # Multi-TF data loading/aggregation
│
├── 📁 strategies/ # STRATEGIES (you always work here)
│ ├── 📁 entry/ # ENTRY strategies (True/False)
│ │ ├── init.py
│ │ ├── base_entry.py # Abstract base class
│ │ ├── ema_cross.py # Example: Fast/slow EMA cross
│ │ ├── rsi_oversold.py # Example: RSI < 30
│ │ └── bollinger_squeeze.py # Example: Bollinger Bands squeeze
│ │
│ ├── 📁 exit/ # EXIT strategies -> ALL ARE TP/SL (True/False + reason)
│ │ ├── init.py
│ │ ├── base_exit.py # Abstract base class
│ │ ├── fixed_tp_sl.py # Fixed Take Profit / Stop Loss
│ │ ├── trailing_stop.py # Dynamic trailing stop
│ │ ├── time_based.py # Exit after N candles
│ │ └── atr_stop.py # ATR-based stop
│ │
│ └── 📁 risk/ # Risk management - How much capital
│ ├── init.py
│ ├── base_risk.py
│ ├── fixed_percent.py # Risk X% per trade
│ └── kelly_criterion.py # Kelly Criterion
│
├── 📁 indicators/ # INDICATOR calculators (extensible)
│ ├── init.py
│ ├── base_calculator.py # Base class for indicators
│ ├── sma_calculator.py # Simple Moving Average
│ ├── ema_calculator.py # Exponential Moving Average
│ ├── rsi_calculator.py # Relative Strength Index
│ ├── macd_calculator.py # MACD
│ ├── bollinger_calculator.py # Bollinger Bands
│ ├── cvd_calculator.py # Cumulative Volume Delta
│ └── atr_calculator.py # Average True Range
│
├── 📁 utils/ # Utilities and helper functions
│ ├── init.py
│ ├── time_utils.py # Timeframe conversion, date calculations
│ ├── file_utils.py # Parquet file management, cache
│ ├── validation.py # Config and data validation
│ └── logging_config.py # Structured logging configuration
│
├── 📁 reports/ # Report generation and visualization
│ ├── init.py
│ ├── metrics_calculator.py # Sharpe, drawdown, win rate, etc.
│ ├── plotter.py # Chart creation (equity, drawdown)
│ ├── html_report.py # HTML report generation
│ └── 📁 templates/ # Report templates
│ └── report_template.html
│
├── 📁 scripts/ # Standalone scripts for operations
│ ├── download_data.py # Downloads data from exchange
│ ├── calculate_indicators.py # Calculates all indicators (batch)
│ ├── cleanup_cache.py # Cleans old cache
│ └── optimize_strategy.py # Parameter optimization (future)
│
├── 📁 ui/ # WEB INTERFACE (future, optional)
│ ├── init.py
│ ├── app.py # Main Streamlit/Dash app
│ ├── 📁 components/ # Reusable UI components
│ │ ├── strategy_builder.py
│ │ ├── param_controls.py
│ │ └── results_display.py
│ └── 📁 assets/ # Static resources
│ └── style.css
│
├── 📄 config.yaml # MAIN CONFIGURATION (always modify here)
├── 📄 backtest.py # MAIN ENTRY POINT
├── 📄 requirements.txt # Python dependencies (pandas, pyarrow, talib, yaml)
├── 📄 .gitignore # Ignores data/, pycache/, .parquet
├── 📄 README.md # User documentation
└── 📄 .env.example # Example environment variables (API keys)
```

## 📄 File Naming Conventions

Data Files:
Raw data: {SYMBOL}_{TIMEFRAME}.parquet (e.g., BTCUSDT_1m.parquet)

Indicator cache: {INDICATOR}_{PARAMS}_{TF}.parquet (e.g., sma_20_1m.parquet)

Journal: {SYMBOL}_{ENTRY_STRAT}_{EXIT_STRAT}_{TIMESTAMP}.parquet

Results: {SYMBOL}_{ENTRY_STRAT}_{EXIT_STRAT}_{TIMESTAMP}/

Code Files:
Entry strategies: strategies/entry/{strategy_name}.py

Exit strategies: strategies/exit/{strategy_name}.py

Indicators: indicators/{indicator_name}_calculator.py

## 🔧 Main Dependencies
pandas - Data manipulation

pyarrow - Parquet read/write

TA-Lib - Indicator calculation

PyYAML - Configuration reading

numpy - Numerical calculations

## 🚫 What's NOT Included
Complex databases (only parquet files)

Microservices (organized monolith)

Over-engineering (only what's needed)