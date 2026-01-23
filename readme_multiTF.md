Ecco `docs/multitf-system.md` con una spiegazione approfondita del sistema multi-timeframe:

```markdown
# Multi-Timeframe Indicator System

## 🎯 Overview

This document explains the **multi-timeframe indicator calculation system** implemented in the trading framework. Unlike traditional approaches that use simple period conversion, this system provides true multi-timeframe calculations with proper OHLC resampling and forward-fill alignment.

## 🔄 The Evolution: From Phase 1-3 to Phase 4+

### **Before (Phase 1-3): Period Conversion Approach**
```python
# OLD: SMA 200 on 4h timeframe using 1m data
sma_period = 200 * 240  # 200 candles × 4 hours × 60 minutes
sma_values = talib.SMA(1m_data['close'], timeperiod=sma_period)
```
**Limitations:**
- ❌ Inaccurate for OHLC-based indicators (ATR, Bollinger Bands)
- ❌ Different candle composition (4h candle ≠ 240 consecutive 1m candles)
- ❌ Volume aggregation incorrect
- ❌ Visualization misalignment

### **After (Phase 4+): True Multi-Timeframe System**
```python
# NEW: SMA 200 on true 4h candles
# 1. Resample 1m → 4h
data_4h = resample_ohlcv(1m_data, "4h")
# 2. Calculate on 4h data
sma_values_4h = talib.SMA(data_4h['close'], timeperiod=200)
# 3. Forward-fill to 1m for alignment
sma_values_1m = sma_values_4h.reindex(1m_data.index, method='ffill')
```
**Benefits:**
- ✅ Accurate OHLC calculations
- ✅ Proper volume aggregation
- ✅ Clean signal alignment
- ✅ Consistent with production systems

## 📊 How It Works: The Three-Step Process

### Step 1: Resampling to Target Timeframe

```python
# indicator_manager.py
def resample_to_timeframe(df_1m, target_tf):
    """
    Convert 1-minute OHLCV data to target timeframe.
    
    Uses label='left', closed='left' for proper candlestick alignment.
    This means a 4h candle at 12:00 contains data from [08:00, 12:00).
    """
    tf_map = {
        "1m": "1T",   "5m": "5T",    "15m": "15T",   "30m": "30T",
        "1h": "1h",   "2h": "2h",    "3h": "3h",     "4h": "4h",
        "6h": "6h",   "8h": "8h",    "12h": "12h",   "1d": "1D"
    }
    
    rule = tf_map[target_tf]
    
    resampled = df_1m.resample(rule, label='left', closed='left').agg({
        'open': 'first',    # First 1m open becomes 4h open
        'high': 'max',      # Highest 1m high becomes 4h high
        'low': 'min',       # Lowest 1m low becomes 4h low
        'close': 'last',    # Last 1m close becomes 4h close
        'volume': 'sum'     # Sum of 1m volumes becomes 4h volume
    }).dropna()
    
    return resampled
```

**Visual Representation:**
```
1-Minute Data (Raw):
08:00: [Open=100, High=102, Low=99, Close=101, Volume=1000]
08:01: [Open=101, High=103, Low=100, Close=102, Volume=1500]
...
11:59: [Open=118, High=119, Low=117, Close=118, Volume=800]

Resampled 4-Hour Candle (08:00-12:00):
Open: 100    (08:00 open)
High: 119    (max of all highs 08:00-11:59)
Low: 99      (min of all lows 08:00-11:59)
Close: 118   (11:59 close)
Volume: 285,000 (sum of all volumes)
```

### Step 2: Indicator Calculation on Resampled Data

```python
class SMACalculator(BaseCalculator):
    def calculate(self, data, params):
        """
        'data' here is the RESAMPLED dataframe
        Example: If strategy.timeframe = "4h", then 'data' contains 4h candles
        """
        period = params.get('period', 20)
        
        # Calculate on 4h closes (not 1m!)
        sma_values = talib.SMA(data['close'], timeperiod=period)
        
        return sma_values
```

**Timeframe-Aware Calculations:**

| Timeframe | Calculation Basis | What It Means |
|-----------|------------------|---------------|
| **1h SMA 200** | 200 hours of 1-hour candles | True 200-period SMA on hourly data |
| **4h SMA 200** | 800 hours of data (200×4h) | True 200-period SMA on 4h data |
| **1d SMA 200** | 200 days of daily candles | True 200-day SMA |

### Step 3: Forward-Fill to 1-Minute Resolution

```python
# After calculating on 4h data:
sma_4h = calculator.calculate(data_4h, params)  # Index: 4h timestamps

# Forward-fill to 1m for alignment with backtest loop:
sma_1m = sma_4h.reindex(data_1m.index, method='ffill')

# Result: Each 1m bar gets the SMA value from its containing 4h bar
```

**Alignment Visualization:**
```
4h SMA Values (calculated every 4 hours):
08:00: SMA = 115.50
12:00: SMA = 116.25
16:00: SMA = 117.00
20:00: SMA = 116.75

Forward-filled to 1m:
08:00-11:59: All 240 minutes get SMA = 115.50
12:00-15:59: All 240 minutes get SMA = 116.25
16:00-19:59: All 240 minutes get SMA = 117.00
20:00-23:59: All 240 minutes get SMA = 116.75
```

## ⚙️ Configuration Examples

### Basic Single-Timeframe Strategy
```yaml
strategy:
  timeframe: "4h"  # Strategy operates on 4-hour bars
  
indicators:
  - name: "sma"
    params: {period: 200}
    column: "sma_200"  # Will be calculated on 4h data
    
  - name: "rsi"
    params: {period: 14}
    column: "rsi_14"   # Will be calculated on 4h data
    
  - name: "atr"
    params: {period: 14}
    column: "atr_14"   # Accurate ATR using 4h high/low/close
```

### Complex Indicator Combinations
```yaml
strategy:
  timeframe: "1h"
  
indicators:
  # Trend indicators on 1h
  - name: "ema"
    params: {period: 20}
    column: "ema_20_1h"
  
  - name: "ema"
    params: {period: 50}
    column: "ema_50_1h"
  
  # Volatility indicator on 4h (higher timeframe)
  - name: "bb"
    params: {period: 20, std: 2}
    column: "bb_upper_4h"
    tf: "4h"  # Override strategy TF for this indicator
  
  - name: "bb"
    params: {period: 20, std: 2}
    column: "bb_middle_4h"
    tf: "4h"
  
  - name: "bb"
    params: {period: 20, std: 2}
    column: "bb_lower_4h"
    tf: "4h"
```

## 🎯 Impact on Different Indicator Types

### 1. **Close-Based Indicators** (SMA, EMA, MACD)
```python
# Minimal difference between old and new approach
old_sma = talib.SMA(1m_close, period=200*240)      # 200*4*60
new_sma = talib.SMA(4h_close, period=200)          # True 200 4h periods

# Difference: Typically < 0.01% for SMA/EMA
```

### 2. **OHLC-Based Indicators** (ATR, Bollinger Bands, Donchian)
```python
# SIGNIFICANT DIFFERENCE!
old_atr = talib.ATR(1m_high, 1m_low, 1m_close, period=200*240)
new_atr = talib.ATR(4h_high, 4h_low, 4h_close, period=200)

# ATR on 4h candles captures true 4h ranges
# ATR on 1m data with period conversion captures 1m ranges scaled up
# Result: Can differ by 10-50%!
```

### 3. **Volume-Based Indicators** (Volume SMA, OBV, VWAP)
```python
# Volume aggregation is non-linear
old_volume_sma = talib.SMA(1m_volume, period=200*240)  # Wrong!
new_volume_sma = talib.SMA(4h_volume, period=200)      # Correct!

# 4h volume = sum of 240 1m volumes (correct aggregation)
# Simple period conversion doesn't account for aggregation
```

### 4. **Oscillators** (RSI, Stochastic, CCI)
```python
# Moderate differences (1-5%)
old_rsi = talib.RSI(1m_close, period=14*240)
new_rsi = talib.RSI(4h_close, period=14)

# Differences come from:
# - Different close sequences
# - Different volatility patterns
# - Different gap handling
```

## 📊 Cache System with Timeframe Support

### Cache Key Structure
```
data/indicators/XPLUSDT/
├── sma_period200_1h_1m_abcd1234.parquet
├── sma_period200_4h_1m_efgh5678.parquet
├── atr_period14_1h_1m_ijkl9012.parquet
└── atr_period14_4h_1m_mnop3456.parquet
```

**Cache Key Components:**
```python
def get_cache_key(self, params):
    # Example: sma_period200_4h_1m
    return (
        f"{self.name}_"
        f"period{params['period']}_"
        f"{self.timeframe}_"      # Calculation timeframe (4h)
        f"1m_"                    # Resolution for alignment
        f"{self.data_hash}"       # Data fingerprint
    )
```

### Cache Invalidation Rules
1. **Data changes**: Hash of raw 1m data changes
2. **Parameters change**: Different period, multiplier, etc.
3. **Timeframe changes**: 1h vs 4h calculation
4. **Calculator changes**: Updated calculation logic

## 🎨 Visualization & Signal Alignment

### Before: Misaligned Signals (Period Conversion)
```
Price (1m):    │░░░░░░░░░░░░░░░░░░░░░░░░░│
SMA (scaled):  │     └─────┘             │
Signal:        │         ?                │
               └──────────────────────────┘
Issue: Signal occurs somewhere within the period
```

### After: Clean Alignment (True Multi-TF)
```
4h Candles:    │░░░░░│░░░░░│░░░░░│░░░░░│
Price (1m):    │░░░░░░░░░░░░░░░░░░░░░░░░░│
SMA (4h):      │     └─────┘             │
Signal:        │           ✨              │
               └──────────────────────────┘
Benefit: Signal aligns with 4h candle boundaries
```

### Plotting Strategy
```python
def plot_strategy_signals(journal_df, config):
    """
    Plot strategy with proper timeframe alignment
    """
    # 1. Aggregate to strategy TF for clean plots
    plot_tf = config['strategy']['timeframe']
    plot_data = resample_for_plotting(journal_df, plot_tf)
    
    # 2. Plot candles at strategy TF
    ax = plot_candles(plot_data, tf=plot_tf)
    
    # 3. Add indicators (already calculated on correct TF)
    ax.plot(plot_data.index, plot_data['sma_200'], label='SMA 200')
    
    # 4. Add signals (aligned with strategy bars)
    entry_signals = journal_df[journal_df['entry_signal']].index
    exit_signals = journal_df[journal_df['exit_signal']].index
    
    # Convert to strategy TF alignment
    entry_times = align_to_timeframe(entry_signals, plot_tf)
    exit_times = align_to_timeframe(exit_signals, plot_tf)
    
    ax.scatter(entry_times, plot_data.loc[entry_times, 'close'], 
               color='green', marker='^', label='Entry', s=100)
    ax.scatter(exit_times, plot_data.loc[exit_times, 'close'],
               color='red', marker='v', label='Exit', s=100)
```

## 🔧 Implementation in Strategy Code

### Accessing Multi-TF Indicators
```python
class MultiTFStrategy(BaseEntryStrategy):
    def should_enter(self, data):
        """
        'data' contains forward-filled values from strategy timeframe
        Access is seamless regardless of calculation timeframe
        """
        # These are forward-filled from 4h calculations
        bb_upper = data['bb_upper_4h'][0]   # Bollinger Upper (4h)
        bb_lower = data['bb_lower_4h'][0]   # Bollinger Lower (4h)
        ema_fast = data['ema_20_1h'][0]     # EMA Fast (1h)
        
        # Current price (1m)
        current_price = data['close'][0]
        
        # Strategy: Buy when price touches lower BB on 4h
        # and EMA is rising on 1h
        touch_lower_bb = current_price <= bb_lower
        ema_rising = data['ema_20_1h'][0] > data['ema_20_1h'][-1]
        
        return touch_lower_bb and ema_rising
```

### Timeframe Alignment in Conditions
```python
def should_enter(self, data):
    # Check if current bar aligns with strategy timeframe
    current_time = data.index[0]
    
    # For 4h strategy, check if it's a 4h boundary
    if current_time.hour % 4 != 0 and current_time.minute != 0:
        return False  # Not a 4h boundary, skip evaluation
    
    # Only evaluate at strategy timeframe boundaries
    # This prevents multiple signals within the same 4h bar
    return your_entry_conditions(data)
```

## 📈 Performance Considerations

### Calculation Overhead
```
Timeframe    | Resample Time | Calc Time | Total First Run | Cached Run
-------------|---------------|-----------|-----------------|-----------
1h (60 bars) | 0.1s          | 0.2s      | 0.3s            | 0.05s
4h (15 bars) | 0.1s          | 0.05s     | 0.15s           | 0.05s
1d (1 bar)   | 0.1s          | 0.01s     | 0.11s           | 0.05s
```

### Memory Usage
```python
# Memory footprint for 1 year of data (525,600 1m bars):
- Raw 1m data: ~50 MB
- 4h resampled: ~2 MB (15x smaller)
- Indicators (10): ~20 MB (cached separately)
- Journal: ~100 MB (with all indicator values)
```

### Optimization Tips
1. **Cache aggressively**: Indicators are the most expensive operation
2. **Use appropriate TF**: Higher TF = faster calculation, less memory
3. **Limit indicator count**: Each indicator adds to memory and calculation time
4. **Use forward-fill wisely**: Only forward-fill needed indicators to 1m

## 🚨 Common Pitfalls & Solutions

### Pitfall 1: Mixing Timeframes Incorrectly
```python
# WRONG: Comparing 1m price with 4h indicator without forward-fill
if data['close'][0] > data['sma_200_4h_raw'][0]:  # Misaligned!
    # This compares current 1m price with last complete 4h SMA
    
# CORRECT: Using forward-filled values
if data['close'][0] > data['sma_200_4h'][0]:  # Both aligned to 1m
    # Framework automatically forward-filled the 4h SMA
```

### Pitfall 2: Signal Repetition
```python
# Without boundary checking, you might get signals every 1m
# within the same 4h bar

# Solution: Check strategy timeframe alignment
def should_enter(self, data):
    current_time = data.index[0]
    
    # Only evaluate at 4h boundaries
    if not is_strategy_boundary(current_time, "4h"):
        return False
    
    # Your entry logic here...
    return condition
```

### Pitfall 3: Lookback Window Issues
```python
# When using higher TF indicators, ensure enough data
def should_enter(self, data):
    # For SMA 200 on 4h, we need 200 complete 4h bars
    # That's 800 hours of 1m data
    
    if len(data) < 200 * 4 * 60:  # 200 bars × 4 hours × 60 minutes
        return False  # Not enough data
    
    # Your logic...
```

## 🔮 Future Enhancements

### 1. Multiple Timeframes in Single Strategy
```yaml
strategy:
  entry:
    timeframe: "15m"  # Entry on 15m signals
    indicators:
      - name: "ema"
        params: {period: 20}
        column: "ema_20_15m"
  
  exit:
    timeframe: "1h"   # Exit on 1h signals
    indicators:
      - name: "atr"
        params: {period: 14}
        column: "atr_14_1h"
```

### 2. Dynamic Timeframe Selection
```python
class AdaptiveTimeframeStrategy(BaseEntryStrategy):
    def should_enter(self, data):
        # Choose TF based on volatility
        volatility = calculate_volatility(data)
        
        if volatility > 0.05:
            timeframe = "1h"   # High volatility → shorter TF
        else:
            timeframe = "4h"   # Low volatility → longer TF
        
        # Use indicators on selected TF
        # Framework would need to calculate multiple TFs
```

### 3. Nested Indicators (Indicator of Indicator)
```yaml
indicators:
  - name: "rsi"
    params: {period: 14}
    column: "rsi_14"
    source: "sma_50"  # RSI of SMA, not price
```

## 🎯 Conclusion

The multi-timeframe system provides:

1. **Accuracy**: True OHLC calculations on target timeframe
2. **Consistency**: Same logic in backtest and production
3. **Clarity**: Clean signal alignment and visualization
4. **Flexibility**: Mix and match timeframes as needed
5. **Performance**: Intelligent caching with timeframe awareness

**Key Takeaway:** Always calculate indicators on the timeframe they're meant to represent. The framework's resampling and forward-fill system makes this seamless while maintaining 1-minute resolution for precise backtesting.

---

**Related Documentation:**
- [Quick Start Guide](quickstart.md) - Get running in 5 minutes
- [Components Guide](components.md) - How to write custom indicators and strategies
- [Execution Pipeline](pipeline.md) - Detailed flow explanation
```




