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

### **📋 PHASE 4: ENHANCED FEATURES**
- [ ] Multiple indicators (EMA, RSI, ATR)
- [ ] Multiple entry/exit strategies
- [ ] Multi-asset support
- [ ] Multi-timeframe indicators
- [ ] Advanced risk metrics (Sharpe, Sortino, Calmar)
- [ ] Walk-forward testing
- [ ] Monte Carlo simulations
- [ ] Parameter optimization (grid search)

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

