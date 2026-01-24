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
- Forward-fill alignment for consistent 1m resolution backtesting
- Support for accurate OHLC-based indicators

### **📋 PHASE 4.B: DOCUMENTATION REORGANIZATION** 
**CURRENT PHASE**
- ✅ Reorganize main README structure
- ✅ Update all code references
- ✅ Add examples/concepts for future new multi-TF system

### **📋 PHASE 4.C: ENHANCED FEATURES** 
- ✅ Advanced strategies -> ema_cross_sma_cvd.py
- [ ] Walk-forward testing
- [ ] Monte Carlo simulations
- [ ] Parameter optimization
- [ ] Advanced risk metrics

### **📋 PHASE 4.D: ENHANCED FEATURES** 
- [ ] Multiple entry/exit strategies
- [ ] Multi-asset support

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

## 🔗 USEFUL LINKS

- **[Quick Start Guide](docs/quickstart.md)** - Get running in 5 minutes
- **[Component Writing Guide](docs/components.md)** - How to create indicators and strategies
- **[Execution Pipeline](docs/pipeline.md)** - Detailed flow explanation
- **[Multi-TF System](docs/multitf-system.md)** - Deep dive into timeframe handling
- **[Calculations Reference](docs/calculations.md)** - Formulas and verification

## 📊 CURRENT STATUS

**Framework:** ✅ Stable with multi-TF support  
**Performance:** ~5s for subsequent runs (cached)  
**Data:** 1-minute Parquet files, auto-resampled  
**Output:** Journals in Parquet, PNG charts, JSON metrics  

**Mantra:** *"Write strategies, not boilerplate"*

---

## 🆕 LATEST IMPROVEMENTS (v4.0)

- **Multi-Timeframe System**: True resampling for accurate indicator calculation
- **Forward-fill Alignment**: Clean signal visualization across timeframes
- **Enhanced Caching**: Separate cache files per timeframe/parameter combination
- **Accurate OHLC Indicators**: Proper ATR, Bollinger Bands on target timeframe
- **Simplified Configuration**: `strategy.timeframe` controls everything


