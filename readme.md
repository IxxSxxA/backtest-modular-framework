# Modular Backtesting Framework in Python

## 🎯 OVERVIEW

A **simple, modular, and fast** backtesting system designed for trading strategy development. The framework separates trading logic from execution mechanics, allowing you to focus on strategy ideas rather than boilerplate code.

**Core Philosophy:** A strategy is a **pure function** that, given market context (prices, indicators), returns True/False. Everything else (money management, positions, commissions) is handled by the framework.

## ✨ KEY FEATURES

### **Multi-Timeframe System**
- **True multi-TF indicator calculation** - not just period conversion
- **Automatic resampling** from 1-minute base data to any strategy timeframe
- **Forward-fill alignment** for consistent 1-minute resolution backtesting
- **Accurate OHLC-based indicators** (ATR, Bollinger Bands, etc.) on target timeframe

### **Performance & Caching**
- **Intelligent disk caching** - indicators calculated once, used infinitely
- **Parquet format** for fast I/O and compression
- **Sub-second subsequent runs** after initial calculation

### **Modular Architecture**
- **Separate concerns**: Strategy vs Engine vs Data
- **Pluggable components**: Entry/Exit/Risk managers as interchangeable modules
- **Configuration-driven**: Everything via `config.yaml`, no hardcoded values

### **Professional Output**
- **Comprehensive journaling** in Parquet format
- **Advanced metrics**: Sharpe, Sortino, Max Drawdown, Win Rate, Profit Factor
- **Visualization**: Equity curves, drawdown charts, entry/exit signals
- **Structured results**: JSON, CSV, and HTML reports

## 🚀 QUICK START

1. **Prepare data**: Place 1-minute Parquet files in `data/raw/`
2. **Configure**: Edit `config.yaml` with your strategy
3. **Run**: Execute `python backtest.py`
4. **Analyze**: Check results in `data/journals/[timestamp]/`

For detailed instructions, see the [Quick Start Guide](docs/quickstart.md).

## 📁 PROJECT STRUCTURE

```txt
trading_framework/
├── config.yaml              # Main configuration
├── backtest.py              # Entry point
├── docs/                    # Documentation
├── core/                    # Engine (rarely modified)
│   ├── data_loader.py
│   ├── data_window.py
│   ├── engine.py
│   ├── indicator_manager.py
│   └── journal_writer.py
├── strategies/              # Trading logic
│   ├── entry/
│   ├── exit/
│   └── risk/
├── indicators/              # Indicator calculations
├── reports/                 # Visualizations
└── data/                    # Raw data + Cache + Journals
    ├── raw/                 # 1m Parquet files
    ├── indicators/          # Precomputed indicators (cache)
    └── journals/            # Backtest results
```

## 🔧 ARCHITECTURAL DECISIONS

### **Multi-Timeframe Indicator System**

The framework implements a **true multi-timeframe calculation system** instead of simple period conversion:

**Before (Phase 1-3):**
- Indicators calculated directly on 1m data with period conversion
- Example: SMA 200 on 4h = SMA 3000 on 1m

**After (Phase 4+):**
1. **Resample** 1m data to target strategy timeframe (e.g., 4h)
2. **Calculate indicators** on the resampled data
3. **Forward-fill** values back to 1m resolution for alignment

**Benefits:**
- ✅ Accurate OHLC-based indicators (ATR, Bollinger Bands)
- ✅ Consistent timeframe alignment
- ✅ Proper candlestick calculations
- ✅ Easy visualization and signal alignment

**Configuration Example:**
```yaml
strategy:
  timeframe: "4h"  # Strategy operates on 4-hour candles

indicators:
  - name: "sma"
    params: {period: 200}
    # Automatically calculated on 4h data
    column: "sma_200"
```

### **Consistency Principle**
- **Backtest-Production Parity**: Same calculation logic in both environments
- **No magic numbers**: All parameters configurable via YAML
- **Transparent caching**: Clear cache keys and invalidation rules

## 📋 IMPLEMENTATION PHASES

### **✅ PHASE 1: FOUNDATION** (MINIMUM VIABLE PRODUCT)
Basic structure, data loading, simple SMA strategy, basic engine.

### **✅ PHASE 2: CORE FEATURES**
Risk management, commissions, journal in Parquet, advanced metrics, visualization.

### **✅ PHASE 3: DEBUG & STABILIZATION**
Fixed calculations, consistency checks, detailed logging, calculation reference.

### **✅ PHASE 4.A: MULTI-TIMEFRAME SYSTEM** 
**BREAKING CHANGE:** Implemented true multi-TF indicator calculation with resampling
- Added proper resampling from 1m to any strategy timeframe
- Updated indicator calculators to work with resampled data
- Support for accurate OHLC-based indicators

### **📋 PHASE 4.B: DOCUMENTATION REORGANIZATION** 
**CURRENT PHASE**
- ✅ Reorganize main README structure
- ✅ Update all code references
- ✅ Add examples/concepts for future new multi-TF system

### **📋 PHASE 4.C: ENHANCED FEATURES** 
- ✅ Advanced strategies -> ema_cross_sma_cvd.py

=========================================================================

## BREAKING CHANGES TO CONFIG.YAML

### **📋 PHASE 4.F: FRAMEWORK REFACTORING** 
🔧 Framework Refactoring Summary 

### ✅ Main Goal Achieved
**Unified indicator declaration in strategy config** - eliminated redundancy between `strategy` and `indicators` sections.

---

## 🎯 Key Changes

### 1. **config.yaml** - New Structure

**BEFORE:**
```yaml
strategy:
  entry:
    params:
      ema_period: 54  # ❌ Declared here
      sma_period: 200

indicators:
  - name: "ema"      # ❌ AND declared here again!
    params: {period: 54}
```

**AFTER:**
```yaml
strategy:
  entry:
    name: "ema_cross_sma_cvd"
    params:
      long_threshold: 50.0  # Only strategy logic params
    indicators:             # ✅ Indicators declared here!
      - name: "ema"
        period: 54
      - name: "sma"
        period: 200
```

**Benefits:**
- ✅ **Single source of truth** - change `period: 54` in one place
- ✅ **Clear ownership** - entry/exit strategies declare what they need
- ✅ **No sync issues** - impossible to forget updating both places

---

### 2. **Auto-Generated Column Names**

The framework now automatically generates column names from indicator configs:

| Config | Generated Column Name |
|--------|----------------------|
| `{name: "ema", period: 54}` | `ema_54` |
| `{name: "sma", period: 200}` | `sma_200` |
| `{name: "atr", period: 21, method: "wilder"}` | `atr_21` |
| `{name: "cvdratio", cumulative_period_minutes: 1, signal_period_minutes: 15}` | `cvd_ratio_1_15` |

**Smart naming logic:**
- Includes all significant parameters
- Skips default values (e.g., `method: "wilder"` is default for ATR)
- Human-readable format

---

### 3. **Strategy Base Classes** - New `indicators` Property

All strategy base classes now have:

```python
class BaseEntryStrategy(ABC):
    def __init__(self, params: Dict[str, Any] = None):
        self.params = params or {}
        self.indicators = self.params.get('indicators', [])  # ← NEW!
```

**Each strategy declares its needs:**
```python
# Entry strategy needs: EMA, SMA, CVD
self.indicators = [
    {name: "ema", period: 54},
    {name: "sma", period: 200},
    {name: "cvdratio", cumulative_period_minutes: 1, ...}
]

# Exit strategy needs: ATR
self.indicators = [
    {name: "atr", period: 21, method: "wilder"}
]

# Risk manager usually needs nothing
self.indicators = []
```

---

### 4. **IndicatorManager** - Auto-Discovery

**New method:** `calculate_from_strategies()`

```python
# OLD WAY (removed):
indicator_configs = config.get("indicators", [])
data_with_indicators = indicator_manager.calculate_all_indicators(
    data, indicator_configs, symbol, strategy_tf
)

# NEW WAY:
data_with_indicators = indicator_manager.calculate_from_strategies(
    data=data,
    entry=entry_strategy,      # ← Reads .indicators property
    exit=exit_strategy,        # ← Reads .indicators property
    risk=risk_manager,         # ← Reads .indicators property (usually empty)
    symbol=symbol,
    strategy_tf=strategy_tf,
    extra_indicators=extra_indicators  # ← Optional, for plotting only
)
```

**What it does:**
1. Collects all `indicators` from entry/exit/risk strategies
2. Adds optional `extra_indicators` from config (for plotting)
3. **Automatically deduplicates** - if entry and exit both need ATR(21), calculates once
4. Generates column names automatically
5. Calculates and caches as before

---

### 5. **backtest.py** - Simplified Flow

**Key changes:**
1. Create strategies **before** calculating indicators
2. Pass `indicators` list inside params to each strategy
3. Use `calculate_from_strategies()` instead of `calculate_all_indicators()`

```python
# Step 1: Create strategies
entry_strategy, exit_strategy, risk_manager = create_strategy_components(config)

# Step 2: Auto-calculate their indicators
data_with_indicators = indicator_manager.calculate_from_strategies(
    data, entry_strategy, exit_strategy, risk_manager, symbol, strategy_tf
)
```

---

## 📋 Files Modified

### Core Files:
- ✅ `config.yaml` - new structure
- ✅ `backtest.py` - uses new strategy->indicator flow
- ✅ `core/indicator_manager.py` - auto-naming + deduplication

### Strategy Files:
- ✅ `strategies/entry/base_entry.py` - added `self.indicators`
- ✅ `strategies/entry/ema_cross_sma.py` - extracts column names from indicators
- ✅ `strategies/entry/ema_cross_sma_cvd.py` - extracts column names from indicators
- ✅ `strategies/exit/base_exit.py` - added `self.indicators`
- ✅ `strategies/exit/atr_based_exit.py` - extracts column names from indicators
- ✅ `strategies/risk/base_risk.py` - added `self.indicators`

---

## 🎨 Optional: Extra Indicators for Plotting

You can calculate indicators for visualization without using them in strategy logic:

```yaml
strategy:
  entry:
    indicators:
      - name: "ema"
        period: 54  # Used by strategy

# Optional: indicators ONLY for analysis/plotting
extra_indicators:
  - name: "supertrend"
    period: 10
    multiplier: 3
  - name: "rsi"
    period: 14

plotting:
  indicators_to_plot:
    - column: "ema_54"         # From entry strategy
    - column: "supertrend_10_3"  # From extra_indicators
    - column: "rsi_14"          # From extra_indicators
```

---

## 🚀 Benefits Summary

1. **Zero Redundancy** - each parameter declared once
2. **Maintainability** - change indicator period in one place
3. **Self-Documenting** - strategy config shows exactly what it needs
4. **Automatic Deduplication** - shared indicators calculated once
5. **Scalability** - easy to add new strategies without config bloat
6. **Flexibility** - supports extra indicators for plotting

---

## 🔄 Migration Guide

### Old Config → New Config:

```yaml
# OLD:
strategy:
  entry:
    params:
      ema_period: 54
indicators:
  - name: "ema"
    params: {period: 54}

# NEW:
strategy:
  entry:
    params: {}  # Strategy logic params only
    indicators:
      - name: "ema"
        period: 54  # No more 'params' wrapper!
```

### Old Strategy → New Strategy:

```python
# OLD:
class MyStrategy(BaseEntryStrategy):
    def __init__(self, params):
        self.ema_period = params.get("ema_period")
        self.ema_column = f"ema_{self.ema_period}"

# NEW:
class MyStrategy(BaseEntryStrategy):
    def __init__(self, params):
        super().__init__(params)  # Sets self.indicators!
        
        # Extract column names
        for ind in self.indicators:
            if ind['name'] == 'ema':
                self.ema_column = f"ema_{ind['period']}"
```

---

## ✅ Testing Checklist

- [ ] Run backtest with new config format
- [ ] Verify indicators are calculated correctly
- [ ] Check column names match expectations
- [ ] Confirm deduplication works (check logs)
- [ ] Test with extra_indicators (optional)
- [ ] Validate cached indicators still work

---

## 📝 Notes

- **Backward compatibility:** Not maintained - this is a breaking change
- **Cache keys:** Updated to include ALL parameters (more robust)
- **Column naming:** Consistent across all indicators
- **No override option:** Decided against `column:` override to keep it simple

---

## 🎉 Result

A cleaner, more maintainable framework where:
- Strategies are **self-contained** (declare their own needs)
- Config is **DRY** (Don't Repeat Yourself)
- System is **smart** (auto-deduplication, auto-naming)
- Code is **scalable** (easy to add new strategies/indicators)

=========================================================================

### **📋 PHASE 4.E: ENHANCED FEATURES** 
- [ ] Multiple entry/exit strategies
- [ ] Multi-asset support
- [ ] Walk-forward testing
- [ ] Monte Carlo simulations
- [ ] Parameter optimization
- [ ] Advanced risk metrics

### **📋 PHASE 5: PRODUCTION READY**
- [ ] Robust error handling
- [ ] Config and data validation
- [ ] Structured logging
- [ ] Complete HTML report
- [ ] Utility scripts
- [ ] Basic web UI

### **📋 PHASE 6: ADVANCED ECOSYSTEM**
- [ ] Plugin system
- [ ] Cloud storage
- [ ] REST API
- [ ] Live trading bridge
- [ ] Comprehensive documentation

=========================================================================

## 📊 CURRENT STATUS

**Framework:** ✅ Stable with multi-TF support  
**Performance:** ~5s for subsequent runs (cached)  
**Data:** 1-minute Parquet files, auto-resampled  
**Output:** Journals in Parquet, PNG charts, JSON metrics  
