# EXECUTION PIPELINE - Backtest Flow

## 🔄 COMPLETE FLOW (Single or Multi-Asset)

```txt
[USER] → python backtest.py
↓
[PHASE 1: CONFIGURATION]
├─ Reads config.yaml
├─ Validates all parameters
├─ Loads strategy classes (entry/exit)
└─ If error → STOP with clear message
↓
[PHASE 2: DATA PREPARATION] (For each symbol in config['symbols'])
├─ Loads: data/raw/{SYMBOL}{TIMEFRAME}.parquet
├─ Filters dates (start/end from config)
├─ Calculates/retrieves indicators (intelligent cache)
│ ├─ If exists: data/indicators/{SYMBOL}/{INDICATOR}{PARAMS}.parquet → load
│ └─ If doesn't exist: calculate → save cache → load
└─ Merge: OHLCV + all indicators → complete dataset
↓
[PHASE 3: ENGINE INITIALIZATION]
├─ Creates BacktestEngine with:
│ ├─ Complete dataset
│ ├─ Entry strategy (from config)
│ ├─ Exit strategy (from config)
│ ├─ Risk/commission parameters
│ └─ Initial state (capital, positions)
└─ Initializes journal writer
↓
[PHASE 4: BACKTEST LOOP] (For each candle, ordered timestamps)
│
├─ [4.1: ENTRY CHECK] If NOT in position:
│ ├─ Calls: entry_strategy.should_enter(current_data_window)
│ └─ If True → Engine.enter_position():
│ ├─ Calculates position size (risk manager)
│ ├─ Records entry price/time
│ ├─ Updates portfolio state
│ └─ Logs: "ENTER at {price}"
│
├─ [4.2: EXIT CHECK] If IN position:
│ ├─ Calls: exit_strategy.should_exit(current_data_window, entry_price)
│ └─ If True → Engine.exit_position():
│ ├─ Calculates realized P&L
│ ├─ Applies commissions
│ ├─ Updates capital
│ ├─ Records complete trade
│ └─ Logs: "EXIT at {price}, P&L: {X}%"
│
└─ [4.3: JOURNAL WRITING] For each candle:
├─ Writes row to: data/journals/{SYMBOL}{STRAT}{TIMESTAMP}.parquet
└─ Fields: timestamp, symbol, price, signals, position, capital, indicators*
↓
[PHASE 5: POST-PROCESSING]
├─ Closes any open positions (end of period)
├─ Calculates performance metrics:
│ ├─ Total Return %
│ ├─ Sharpe Ratio
│ ├─ Max Drawdown %
│ ├─ Win Rate %
│ ├─ Profit Factor
│ └─ Number of trades
└─ Generates structured output
↓
[PHASE 6: OUTPUT & VISUALIZATION]
├─ Prints summary to screen
├─ Saves result files:
│ ├─ Trades CSV: results/{SYMBOL}{STRAT}{TIMESTAMP}/trades.csv
│ ├─ Equity curve: results/{SYMBOL}{STRAT}{TIMESTAMP}/equity.png
│ ├─ Report HTML: results/{SYMBOL}{STRAT}{TIMESTAMP}/report.html
│ └─ Metrics JSON: results/{SYMBOL}{STRAT}{TIMESTAMP}/metrics.json
└─ If UI active → updates live dashboard
↓
[END] ✅ Backtest completed
```

## ⏱️ TYPICAL TIMELINE (525k 1m candles = 1 year)
First Execution (indicators to calculate):
T+0s: python backtest.py
T+1s: Config loaded ✓
T+2s: Data loaded (525k candles) ✓
T+2-60s: Calculating indicators... (depends on quantity and complexity)
T+60s: Starting backtest loop...
T+180s: [===============>] 100% (2,900 candles/sec)
T+181s: Calculating metrics...
T+182s: Generating plots...
T+185s: ✅ Backtest completed!

Subsequent Executions (everything cached):
T+0s: python backtest.py
T+1s: Config loaded ✓
T+2s: Data + indicators from cache ✓
T+3s: Backtest loop (525k candles in 2s)
T+5s: ✅ Backtest completed! (5 seconds total)

## 🎯 KEY INPUT/OUTPUT
INPUT (config.yaml):
yaml
symbols: ["BTCUSDT", "ETHUSDT"]      # Assets to test
timeframe: "1m"                      # Engine timeframe
strategy:
  entry:
    name: "ema_cross"               # File: strategies/entry/ema_cross.py
    params: {fast: 20, slow: 50}    # Strategy parameters
  exit:
    name: "fixed_tp_sl"             # File: strategies/exit/fixed_tp_sl.py
    params: {tp: 0.05, sl: 0.02}    # TP 5%, SL 2%
indicators:                         # List of required indicators
  - sma_20_1m
  - rsi_14_1m
  - ema_50_4h

OUTPUT (per symbol):
```text
data/journals/BTCUSDT_ema_cross_fixed_tp_sl_20250116_143025.parquet
├── 525,600 rows (1 row per 1m candle)
├── Columns: timestamp, symbol, price, entry_signal, exit_signal, 
│           in_position, position_size, capital, drawdown, 
│           ema_fast, ema_slow, rsi, ... (all indicators)
└── Format: Parquet (fast, compressed)

results/BTCUSDT_ema_cross_fixed_tp_sl_20250116_143025/
├── trades.csv           # Trade list with P&L
├── equity.png          # Equity curve chart
├── drawdown.png        # Drawdown chart
├── report.html         # Interactive HTML report
└── metrics.json        # Metrics in JSON format
```

## 🔄 INTELLIGENT CACHE
Indicator calculation flow:

Receives request: "sma_20_1m" for "BTCUSDT"

Searches: data/indicators/BTCUSDT/sma_20_1m.parquet

```txt
If FOUND: loads and returns (instant)
If NOT FOUND:
├─ Calculates SMA(20) on 1m data
├─ Saves: data/indicators/BTCUSDT/sma_20_1m.parquet
└─ Returns result
```

Cache valid until raw data changes
(check via hash or last modified timestamp)

## 🚨 ERROR HANDLING
Common errors and recovery:

Data file not found → "Run scripts/download_data.py"

Strategy not found → "Create strategies/entry/{name}.py"

Indicator not implemented → "Create indicators/{name}_calculator.py"

Cache corrupted → "Run scripts/cleanup_cache.py"

Invalid config → Message with problematic field

## 📈 SCALABILITY
From Single to Multi-Asset:

Single: symbols: ["BTCUSDT"]

Multi: symbols: ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

Cross-asset: (future) strategies comparing assets

From 1 to N Timeframes:

Base: timeframe: "1m"

Multi-TF: indicators on different TFs (sma_20_5m, ema_50_1h)

Multi-TF strategies: entry on 5m, exit on 15m

## 🎨 VISUALIZATION PIPELINE (Future)
Journal Parquet → Plotter → Visualizations:

Reads: data/journals/{SYMBOL}{STRAT}{TIMESTAMP}.parquet

Aggregates to TF for plotting (1m → 1h for equity curve)

Generates:

Equity curve with drawdown

Entry/exit points on price chart

P&L distribution

Performance heatmap over time

Output: PNG, interactive HTML, PDF report