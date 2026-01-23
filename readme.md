# Modular Backtesting Framework in Python

## NOTE ON TIMEFRAME AND INDICATOR CALCULATION

This framework adopts a pragmatic approach to calculating indicators across multiple timeframes.

### Fundamental Principle: Backtest-Production Consistency
- **Base data**: All backtesting is performed on 1-minute (1m TF) data
- **Multi-TF indicators**: Indicators that normally require higher timeframes (e.g., 15m, 1h, 4h) are calculated by converting the period
- **Philosophy**: What matters is that the **same logic** is used in both backtesting and production

### Period Conversion for Different Timeframes
Example: SMA 200 on 15-minute data using 1-minute data:
```
SMA_15m_period_200 = 200 candles × 15 minutes = 3000 minutes
                   = SMA_1m_period_3000
```

### Advantages of This Approach
1. **Architectural simplification**: No need to implement data resampling
2. **Performance**: Direct calculations on 1m data already in memory
3. **Consistency**: Same calculation in backtest and production
4. **Sufficient accuracy** for many close-based indicators

### Limitations and Considerations
#### Indicators that work well with conversion:
- **SMA/EMA/MACD** (close-based) → minimal differences (<0.01%)
- **RSI/Stochastic** → small differences (1-2%) generally acceptable

#### Indicators that may have significant differences:
- **ATR (Average True Range)** → uses candle high/low, resampling can yield different results
- **Bollinger Bands** → depends on price standard deviation
- **Volume-based indicators** → volume aggregation is non-linear

### Documentation of Implementation Choices
Each strategy should document:
```yaml
strategy:
  indicators:
    - name: "sma"
      tf: "15m"
      calculated_as: "sma_3000_1m"  # Converted period
      note: "Equivalent to SMA 200 15m for consistency"
```

### Why This Choice is Valid
1. **Practical realism**: In production, you'll use the same simplified calculations
2. **Focus on edge**: If a strategy has edge, it will manifest even with approximate calculations
3. **Reduced complexity**: Avoids multi-TF synchronization issues

### When to Consider True Resampling
Consider implementing true resampling if:
1. You heavily use OHLC-based indicators (ATR, Donchian, etc.)
2. You need millimeter precision for result publication
3. The strategy is extremely sensitive to exact signal timing

### Conclusion
This approach offers a good compromise between implementation simplicity and sufficient accuracy for most trading strategies. The key is maintaining **absolute consistency** between the backtesting and production environments.

**Remember**: A backtest that uses different logic from production is useless, even if it's "more accurate" according to external standards.

## 🎯 OBJECTIVE

A **simple, modular, and fast** backtesting system that allows you to:
1. **Write strategies in minutes** – without boilerplate code
2. **Test ideas quickly** – with intelligent caching for performance
3. **Stay extensible** – easily add indicators, strategies, assets
4. **Keep structured data** – full journal for post-trade analysis
5. **Prepare for the future** – architecture ready for UI and live trading

**Philosophy:** A strategy is a **pure function** that, given a market context (prices, indicators), returns True/False. Everything else (money management, positions, commissions) is handled by the framework.

## 🛠️ HOW WE ACHIEVE OUR GOAL

### Design Principles:
1. **Separation of Concerns**:
   - Strategy: only True/False logic
   - Engine: state management and execution
   - Data: standard format (Parquet) with caching
2. **Configuration over Code**:
   - Everything configurable via `config.yaml`
   - No hardcoded parameters
3. **Cache First**:
   - Indicators calculated once, used infinitely
   - Instant performance after the first run
4. **Modularity**:
   - Entry/exit strategies are interchangeable
   - Add indicators without modifying the core
5. **Simple First**:
   - Start with basic functionality
   - Extend gradually

## 📋 IMPLEMENTATION PHASES

### **✅ PHASE 1: FOUNDATION** (MINIMUM VIABLE PRODUCT) – **COMPLETED!**
- ✅ Basic folder structure
- ✅ Minimal `config.yaml` schema
- ✅ Data loader for 1m Parquet files
- ✅ 1 Basic indicator (SMA) with caching
- ✅ 1 Simple entry strategy (price > SMA)
- ✅ 1 Simple exit strategy (fixed bars)
- ✅ Basic engine loop (without risk management)
- ✅ Basic journal writer (simple CSV)
- ✅ Basic console output

**Goal reached:** `python backtest.py` runs and produces basic results! 🎉

### **✅ PHASE 2: CORE FEATURES** – **COMPLETED!**
- ✅ Risk manager (position sizing) – `FixedPercentRisk`
- ✅ Commissions and slippage
- ✅ **Journal in Parquet** (not CSV) – performance optimization
- ✅ **Advanced basic metrics** – detailed summary with verification
- ✅ **Basic equity chart** (matplotlib) – 3 plot types
- ✅ Full integration of risk management into the engine

### **✅ PHASE 3: DEBUG & STABILIZATION** – **COMPLETED!**
- ✅ **Fixed output directory** – now taken from config
- ✅ **Debugged risk management calculations** – verified position sizing consistency
- ✅ **Verified calculation accuracy** – P&L, commissions, equity
- ✅ **Automatic consistency checks** in results
- ✅ **Detailed logging** for calculation debugging
- ✅ **Calculation documentation** – explanation of formulas used → in English → Document name: **`readme_calcs_reference.md`**

**Goal reached:** Stable framework with risk management and visualization! 📊

========================================================================================
========================================================================================
# BREAKING CHANGES

# Trading Framework - Multi-Timeframe Indicator System

## Overview

This document explains the **multi-timeframe indicator calculation system** implemented in the trading framework. The system allows strategies to operate on any timeframe (1h, 4h, etc.) while calculating indicators correctly for that timeframe.

## Core Concept

Instead of calculating indicators directly on 1-minute data and hoping they work on higher timeframes, we now:

1. **Resample 1m data** to the target strategy timeframe (e.g., 1h, 4h)
2. **Calculate indicators** on the resampled timeframe data
3. **Forward-fill** indicator values back to 1-minute resolution for consistent alignment

## Architecture

### 1. Data Flow

```
Raw 1m Data (Parquet)
    ↓
Resample to Strategy TF (e.g., 4h)
    ↓
Calculate Indicators (on 4h data)
    ↓
Forward-fill to 1m (for alignment)
    ↓
Backtest Engine (uses 4h bars with indicators)
```

### 2. Configuration Example

```yaml
strategy:
  timeframe: "4h"  # Strategy operates on 4-hour candles

indicators:
  - name: "sma"
    params: 
      period: 200
      tf: "4h"     # Calculate SMA on 4h data
    column: "sma_200"
```

### 3. Key Components

#### **Resampling (`backtest.py`)**
```python
def resample_to_timeframe(df, target_tf: str):
    """
    Convert 1m OHLCV data to target timeframe.
    Uses label='left', closed='left' for proper candlestick alignment.
    """
```

#### **Indicator Calculation (`indicator_manager.py`)**
- Each calculator (SMA, EMA, ATR, CVD) supports `tf` parameter
- Calculates on resampled data, then forward-fills to 1m
- Caching includes timeframe in cache key (e.g., `sma_period200_4h_1m_xxxxxx.parquet`)

#### **Timeframe Support**
```python
tf_map = {
    "1m": "1T",
    "5m": "5T",
    "15m": "15T",
    "30m": "30T",
    "1h": "1h",
    "2h": "2h",
    "3h": "3h",
    "4h": "4h",
    "6h": "6h",
    "8h": "8h",
    "12h": "12h",
    "1d": "1D",
}
```

## Benefits

### 1. **Accurate Indicator Calculation**
- SMA 200 on 4h data uses true 4-hour candles (800 hours of data)
- Not just SMA 200 on 1m data (which would be 200 minutes)

### 2. **Consistent Timeframe Alignment**
- All indicators calculated on the same resampled data
- No mismatch between strategy timeframe and indicator timeframe

### 3. **Efficient Caching**
- Separate cache files for each timeframe
- `sma_period200_1h_1m_xxxxxx.parquet` vs `sma_period200_4h_1m_yyyyyy.parquet`

### 4. **Flexible Strategy Design**
- Easy to test same strategy on different timeframes
- Compare 1h vs 4h performance directly

## Example: SMA 200 on Different Timeframes

| Timeframe | Calculation Basis | Cache File |
|-----------|------------------|------------|
| 1h | 200 hours of 1-hour candles | `sma_period200_1h_1m_xxxxxx.parquet` |
| 4h | 200 periods of 4-hour candles (800 hours) | `sma_period200_4h_1m_yyyyyy.parquet` |
| 1d | 200 days of daily candles | `sma_period200_1d_1m_zzzzzz.parquet` |

## Plotting Improvements

The forward-fill approach makes plotting straightforward:

1. **Price chart**: Resampled OHLC data (e.g., 4h candles)
2. **Indicators**: Calculated on same 4h data, forward-filled for alignment
3. **Signals**: Entry/exit points aligned with 4h candle timestamps

No more misaligned indicators on charts!

## Usage

### 1. Configure Strategy Timeframe
```yaml
strategy:
  timeframe: "4h"  # Change this to test different timeframes
```

### 2. Define Indicators
```yaml
indicators:
  - name: "sma"
    params: 
      period: 200
      # tf is automatically added from strategy.timeframe
    column: "sma_200"
```

### 3. Run Backtest
```bash
python backtest.py
```

The system automatically:
- Loads 1m data
- Resamples to configured timeframe
- Calculates indicators on resampled data
- Runs strategy on the target timeframe

## Performance Considerations

1. **Memory**: Loading full historical data for indicator calculation
2. **Cache Size**: Separate cache files for each timeframe/parameter combination
3. **Calculation Time**: Initial calculation on full data, then cached

## Future Enhancements

1. **Indicator-on-indicator**: Calculate RSI of SMA, etc.
2. **Multiple timeframes in one strategy**: Use 1h for entries, 4h for trend
3. **Dynamic timeframe selection**: Strategy chooses optimal timeframe

## Conclusion

The multi-timeframe system provides accurate, consistent indicator calculation across any timeframe, enabling robust strategy testing and clear visualization of results.

========================================================================================
========================================================================================

### **📋 PHASE 4.A: ENHANCED FEATURES**
- ✅ Multiple indicators (EMA, CVD, ATR) -> Make considerations about 1m TF constrains

### **📋 PHASE 4.B: ENHANCED FEATURES**
- [ ] Improve documentation -> Make it easier to read and use

### **📋 PHASE 4.C: ENHANCED FEATURES**
- [ ] Multiple entry/exit strategies
- [ ] Multi-asset support
- [ ] Walk-forward testing
- [ ] Monte Carlo simulations
- [ ] Parameter optimization (grid search)
- [ ] Multi-timeframe indicators
- [ ] Advanced risk metrics (Sharpe, Sortino, Calmar)

Papers to read:
- https://people.duke.edu/~charvey/Research/Published_Papers/P116_Evaluating_trading_strategies.pdf
- https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf

### **📋 PHASE 5: PRODUCTION READY**
- [ ] Robust error handling
- [ ] Config and data validation
- [ ] Structured logging
- [ ] Complete HTML report
- [ ] Utility scripts (download data, cleanup)
- [ ] Basic web UI (Streamlit)

### **📋 PHASE 6: ADVANCED ECOSYSTEM**
- [ ] Plugin system for indicators/strategies
- [ ] Cloud storage for data/journal
- [ ] REST API for automation
- [ ] Live trading bridge (future)
- [ ] Comprehensive documentation

## 🔄 DEVELOPMENT WORKFLOW

For each phase:
1. **Dedicated chat** for that specific phase
2. **Incremental implementation**:
   - Modify `config.yaml` schema if needed
   - Implement feature in isolated modules
   - Test with sample data
   - Integrate into main flow
3. **Update documentation**:
   - Update `readme.md` with progress
   - Document new features
   - Update examples
4. **Consistency verification**:
   - All modules work together
   - Cache works correctly
   - Output is as expected

## 📁 KEY STRUCTURE (summary)

```txt
trading_framework/
├── config.yaml              # CONTROL CENTER
├── backtest.py              # ENTRY POINT
├── core/                    # Engine (rarely modified)
│   ├── data_loader.py
│   ├── data_window.py
│   ├── engine.py
│   ├── indicator_manager.py
│   └── journal_writer.py
├── strategies/              # Trading logic (often modified)
│   ├── entry/
│   │   ├── base_entry.py
│   │   └── price_above_sma.py
│   ├── exit/
│   │   ├── base_exit.py
│   │   ├── hold_bars.py
│   │   └── fixed_tp_sl.py
│   └── risk/
│       ├── base_risk.py
│       └── fixed_percent.py
├── indicators/              # Indicator calculations
│   ├── base_calculator.py
│   └── sma_calculator.py
├── reports/                 # Visualizations
│   ├── plotter.py
│   └── __init__.py
└── data/                    # Raw data + Precomputed Indicators (cache) + Journal Output → No hardcode → Read from config.yaml
```

## 📝 DEVELOPMENT NOTES

**Priorities:**
1. Works → Correct → Fast → Beautiful
2. Start with minimal working examples
3. Test each component in isolation
4. Maintain backward compatibility

**Mantra:** “Write strategies, not boilerplate”

## 🎯 ARCHITECTURAL DECISIONS

- **Parquet (and CSV/DB if required)**: performance, compression, schema evolution
- **YAML over JSON/INI**: human-readable, comments, hierarchy
- **Classes over functions**: for strategies, but with simple interfaces
- **Cache on disk**: across executions, not just in memory

## 📊 CURRENT PERFORMANCE

- **First run**: ~2–60s (indicator calculation)
- **Subsequent runs**: ~5s (everything cached)
- **Data format**: Parquet (fast, compressed)
- **Visualizations**: Matplotlib PNG (compact, universal)

## 🔧 HOW TO ADD NEW FEATURES

### New risk manager:
1. Create `strategies/risk/manager_name.py`
2. Extend `BaseRiskManager`
3. Implement `calculate_position_size()`
4. Add to `config.yaml` in the `strategy.risk` section

### New plot type:
1. Create a method in `reports/plotter.py`
2. Add it to `create_all_plots()`
3. `JournalWriter` will include it automatically

## 🆕 LATEST IMPROVEMENTS

- **Dual‑line summary chart** now implemented – clearly shows both equity and benchmark/strategy comparison.
- All Phase 3 debugging and stabilization tasks completed.
- Output directory is now fully config‑driven.
- Calculation consistency verified; logging enhanced for transparency.
- Reference document **`calculation_reference.md`** created (in English) explaining all formulas used in the framework.

