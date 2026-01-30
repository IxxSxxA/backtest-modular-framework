Ecco il README aggiornato con le nuove funzionalità TP/SL dinamiche aggiunte a PHASE 4.E:

```markdown:readme.md
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

### **Dynamic TP/SL Visualization**
- **ATR-based Take Profit and Stop Loss** with dynamic or fixed levels
- **Real-time TP/SL calculation** updated every candle or fixed at entry
- **Visual zones plotting** with proper color coding for LONG/SHORT positions
- **Comprehensive journaling** of TP/SL evolution for analysis

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
- **Visualization**: Equity curves, drawdown charts, entry/exit signals, TP/SL zones
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

### **Dynamic TP/SL System**

The framework supports **both dynamic and fixed TP/SL levels** based on ATR:

**Configuration:**
```yaml
exit:
  name: "atr_based_exit"
  params:
    tp_multiplier: 7
    sl_multiplier: 6
    dynamic: true  # true=TP/SL update every candle, false=fixed at entry
    
  visual:
    sl_tp:
      enabled: true
      style:
        tp_color: "#27AE60"  # Green for profit
        sl_color: "#E74C3C"  # Red for loss
        zone_alpha: 0.1
```

**Visual Zones:**
- **LONG positions**: TP zone (green) above entry, SL zone (red) below entry
- **SHORT positions**: TP zone (green) below entry, SL zone (red) above entry
- **Dynamic lines**: TP/SL levels that move with ATR when `dynamic: true`
- **Fixed lines**: Horizontal TP/SL levels when `dynamic: false`

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

### **✅ PHASE 4.B: DOCUMENTATION REORGANIZATION** 
- Reorganize main README structure
- Update all code references
- Add examples/concepts for future new multi-TF system

### **✅ PHASE 4.C: ENHANCED ENTRY STRATEGIES** 
- Advanced strategies -> ema_cross_sma_cvd.py

### **✅ PHASE 4.D: FRAMEWORK REFACTORING** 
**Unified indicator declaration** - eliminated redundancy between strategy and indicators sections
- Single source of truth for indicator parameters
- Auto-generated column names
- Strategy self-contained declaration

### **✅ PHASE 4.E: DYNAMIC TP/SL VISUALIZATION** 
**Enhanced exit strategies with visual TP/SL zones**
- ATR-based TP/SL with dynamic/fixed modes
- Real-time TP/SL calculation every candle
- Visual zones plotting for both LONG and SHORT positions
- Complete journaling of TP/SL evolution
- Color-coded zones (green for TP, red for SL)

---

## 🔧 Framework Refactoring Summary 

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

### 2. **Dynamic TP/SL Configuration**

```yaml
exit:
  name: "atr_based_exit"
  params:
    tp_multiplier: 7
    sl_multiplier: 6
    dynamic: true  # ✅ New parameter: true=dynamic, false=fixed
    
  indicators:
    - name: "atr"
      period: 21
      method: "wilder"
    
  # Visual configuration for SL/TP levels
  visual:
    sl_tp:
      enabled: true
      style:
        tp_color: "#27AE60"
        sl_color: "#E74C3C"
        zone_color: "#F1C40F"
        zone_alpha: 0.1
        line_width: 1.5
        line_style: "--"
      annotations:
        show_entry_exit: true
        show_pnl: true
        font_size: 8
        box_style: "round,pad=0.3"
```

**Features:**
- ✅ **Dynamic mode**: TP/SL update every candle based on current ATR
- ✅ **Fixed mode**: TP/SL calculated once at entry and remain constant
- ✅ **Visual zones**: Color-coded areas between entry and TP/SL levels
- ✅ **Position-aware**: Different zones for LONG vs SHORT positions

---

### 3. **Auto-Generated Column Names**

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

### 4. **Strategy Base Classes** - New `indicators` Property

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

### 5. **IndicatorManager** - Auto-Discovery

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

### 6. **Enhanced Journaling with TP/SL Data**

The journal now includes TP/SL levels for each candle when in position:

```python
journal_entry = {
    "timestamp": current_time,
    "price": current_price,
    "in_position": True,
    "take_profit": tp_level,    # ✅ NEW
    "stop_loss": sl_level,      # ✅ NEW
    "position_type": "short",   # ✅ NEW
    # ... other fields
}
```

**Benefits:**
- ✅ Complete historical record of TP/SL evolution
- ✅ Enables accurate dynamic plotting
- ✅ Supports analysis of TP/SL behavior

---

### 7. **Advanced Plotting with TP/SL Zones**

```python
# reports/plot_helpers.py
def plot_sl_tp_zones(ax, data, trades, sl_tp_config):
    """
    Plot dynamic TP/SL zones with proper LONG/SHORT handling.
    
    LONG:  TP zone (green) above entry, SL zone (red) below entry
    SHORT: TP zone (green) below entry, SL zone (red) above entry
    """
```

**Visual Features:**
- ✅ Color-coded zones based on position direction
- ✅ Dynamic lines when `dynamic: true`
- ✅ Fixed lines when `dynamic: false`
- ✅ Proper legend handling

---

## 📊 NEXT PHASES

### **📋 PHASE 5: ENHANCED FEATURES** 
- [ ] Multiple entry/exit strategies
- [ ] Multi-asset support
- [ ] Walk-forward testing
- [ ] Monte Carlo simulations
- [ ] Parameter optimization
- [ ] Advanced risk metrics

### **📋 PHASE 6: PRODUCTION READY**
- [ ] Robust error handling
- [ ] Config and data validation
- [ ] Structured logging
- [ ] Complete HTML report
- [ ] Utility scripts
- [ ] Basic web UI

### **📋 PHASE 7: ADVANCED ECOSYSTEM**
- [ ] Plugin system
- [ ] Cloud storage 
- [ ] REST API
- [ ] Live trading bridge
- [ ] Comprehensive documentation

---

## 📊 CURRENT STATUS

**Framework:** ✅ Stable with multi-TF support  
**TP/SL System:** ✅ Dynamic/Fixed modes with visualization  
**Performance:** ~5s for subsequent runs (cached)  
**Data:** 1-minute Parquet files, auto-resampled  
**Output:** Journals with TP/SL data, PNG charts with zones, JSON metrics  

---

## 📖 GLOSSARY

**Capital / Cash Balance**
- Physical cash in account
- Can increase (SHORT) or decrease (LONG) on entry

**Margin Used**
- Amount locked as collateral for SHORT positions
- Must be available to close position
- Reduces available capital for new trades

**Available for New Trades**
- Capital actually usable for new positions
- Formula: cash_balance - margin_used
- Most important metric for position sizing

**Total Equity**
- Net account value including positions
- Formula: cash_balance + position_value
- What you'd have if you closed everything

**Max Drawdown**
- Largest peak-to-trough equity decline (%)
- Cumulative effect of losing trades
- Independent of per-trade risk percentage

**Dynamic TP/SL**
- Take Profit and Stop Loss levels that update every candle
- Based on current ATR value (when using ATR-based exit)
- Visualized as moving lines on price chart

**Fixed TP/SL**
- TP/SL levels calculated once at entry
- Remain constant throughout the position
- Visualized as horizontal lines on price chart

**TP/SL Zones**
- Colored areas between entry price and TP/SL levels
- Green zone: path to profit (TP direction)
- Red zone: path to loss (SL direction)
- Helps visualize risk/reward ratio


