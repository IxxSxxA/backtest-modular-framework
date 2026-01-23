# Quick Start Guide

## 🚀 Get Running in 5 Minutes

### Prerequisites
- Python 3.8+
- 1-minute OHLCV Parquet files

### Step 1: Prepare Data
Place your 1-minute Parquet files in the data directory:
```bash
# Create directory structure
mkdir -p data/raw

# Add your data file (example: XPLUSDT 1-minute data)
# File naming: {SYMBOL}-1m-{DATE_RANGE}.parquet
# Example: data/raw/XPLUSDT-1m-2025-2026-01-22.parquet
```

### Step 2: Configure Your Strategy
Edit `config.yaml`:

```yaml
# === BACKTEST PERIOD ===
backtest:
  period:
    start: "2026-01-10"
    end: "2026-01-22"
  capital:
    initial: 10000
  costs:
    commission: 0.001  # 0.1% commission

# === DATA SOURCE ===
data:
  symbols: ["XPLUSDT"]
  timeframe: "1m"      # Raw data is always 1m
  source_dir: "data/raw"
  source_file: "XPLUSDT-1m-2025-2026-01-22"  # No .parquet extension

# === STRATEGY ===
strategy:
  timeframe: "4h"      # Strategy operates on 4-hour candles
  
  entry:
    name: "price_above_sma"
    params:
      sma_column: "sma_200"  # References indicator column
      lookback: 1
  
  exit:
    name: "hold_bars"
    params:
      bars: 100
  
  risk:
    name: "fixed_percent"
    params:
      risk_per_trade: 0.02  # Risk 2% per trade

# === INDICATORS ===
indicators:
  - name: "sma"
    params: {period: 200}
    column: "sma_200"       # Column name for reference

# === OUTPUT ===
output:
  journal:
    save_dir: "data/journals/"
  plots:
    enabled: true
    overlays:
      - column: "sma_200"
        color: "#ff0000"
```

### Step 3: Run the Backtest
```bash
python backtest.py
```

### Step 4: Analyze Results
Results are saved in timestamped directories:
```
data/journals/XPLUSDT_4h_price_above_sma_20260122_143022/
├── metrics.json          # Performance metrics
├── trades.parquet       # Trade list
├── journal.parquet      # Tick-by-tick log
├── equity_curve.png     # Equity chart
└── price_signals.png    # Price with indicators and signals
```

## 📋 Key Concepts

### Timeframe Handling
- **Raw Data**: Always 1-minute (`data.timeframe: "1m"`)
- **Strategy Timeframe**: Configured in `strategy.timeframe` (e.g., "4h")
- **Automatic Resampling**: Framework resamples 1m → target TF for indicators
- **Forward-fill**: Indicators calculated on target TF, forward-filled to 1m for alignment

### Indicator Caching
- **First Run**: Calculates and caches indicators (~5-60 seconds)
- **Subsequent Runs**: Loads from cache (<0.1 seconds)
- **Cache Location**: `data/indicators/{SYMBOL}/`
- **Auto-invalidation**: Cache invalidated if parameters change

### Data Access in Strategies
```python
# In your strategy's should_enter() or should_exit() methods:
data['close'][0]      # Current close price
data['close'][-1]     # Previous close
data['sma_200'][0]    # Current SMA200 value
data['sma_200'][-5]   # SMA200 5 bars ago
```

## 🎯 Example: SMA Cross Strategy

```yaml
# config.yaml
strategy:
  timeframe: "1h"
  
  entry:
    name: "sma_cross"
    params:
      fast_column: "sma_20"
      slow_column: "sma_50"
  
  exit:
    name: "fixed_tp_sl"
    params:
      tp_percent: 0.03
      sl_percent: 0.015

indicators:
  - name: "sma"
    params: {period: 20}
    column: "sma_20"
  
  - name: "sma"
    params: {period: 50}
    column: "sma_50"
```

```python
# strategies/entry/sma_cross.py
class SMACrossEntry(BaseEntryStrategy):
    def should_enter(self, data):
        # SMA20 crosses above SMA50
        return (
            data['sma_20'][0] > data['sma_50'][0] and 
            data['sma_20'][-1] <= data['sma_50'][-1]
        )
```

## ❓ Frequently Asked Questions

**Q: Where do I get 1-minute Parquet files?**  
A: You can convert from CSV or use data download scripts (coming in Phase 5).

**Q: How do I change the strategy timeframe?**  
A: Modify `strategy.timeframe` in config.yaml. Supports: 1m, 5m, 15m, 30m, 1h, 2h, 3h, 4h, 6h, 8h, 12h, 1d.

**Q: How do I add a new indicator?**  
A: Add an entry in the `indicators:` section of config.yaml and create the calculator in `indicators/` folder.

**Q: Why are results saved in Parquet format?**  
A: Parquet is columnar, compressed, and fast for analysis. You can easily load it with pandas for post-analysis.

**Q: How do I visualize results?**  
A: Check the PNG charts in the output directory, or load the journal.parquet file for custom analysis.

## ⚠️ Common Issues & Solutions

**Issue**: "File not found: data/raw/..."  
**Solution**: Ensure your Parquet file exists and matches the `source_file` name in config.yaml (without .parquet extension).

**Issue**: "Unknown indicator: ..."  
**Solution**: Check that the indicator calculator exists in `indicators/` folder.

**Issue**: "Strategy class not found"  
**Solution**: Ensure your strategy file is in the correct folder (`strategies/entry/` or `strategies/exit/`).

**Issue**: "Cache not working"  
**Solution**: Delete the `data/indicators/` folder and let the framework recreate it.

---

**Next Steps**:  
- Learn how to write custom components: [Components Guide](components.md)  
- Understand the execution flow: [Pipeline Guide](pipeline.md)  
- Dive deep into multi-timeframe system: [Multi-TF Guide](multitf-system.md)
```

