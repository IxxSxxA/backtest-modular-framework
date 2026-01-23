# Component Development Guide

## 🧩 How to Extend the Framework

This guide explains how to create custom indicators, entry/exit strategies, and risk managers for the framework.

## 1. Creating Indicators

### File Structure
Place new indicator calculators in `indicators/` directory:
```
indicators/
├── base_calculator.py    # Base class
├── sma_calculator.py     # Example
├── ema_calculator.py     # Example
└── your_indicator.py     # Your new indicator
```

### Base Class
```python
# indicators/base_calculator.py
class BaseCalculator:
    def __init__(self, symbol=None, timeframe=None):
        self.symbol = symbol
        self.timeframe = timeframe
    
    def calculate(self, data, params):
        """
        Main calculation method.
        
        Args:
            data: DataFrame with OHLCV columns
            params: Dictionary of indicator parameters
        
        Returns:
            Series with calculated values
        """
        raise NotImplementedError("Must implement calculate()")
```

### Example: SMA Calculator
```python
# indicators/sma_calculator.py
import pandas as pd
import talib
from .base_calculator import BaseCalculator

class SMACalculator(BaseCalculator):
    """Simple Moving Average calculator"""
    
    def calculate(self, data, params):
        """
        Calculates SMA on the resampled timeframe data.
        
        Args:
            data: DataFrame with OHLCV (already resampled to target TF)
            params: {"period": 20}
        
        Returns:
            pd.Series with SMA values
        """
        period = params.get('period', 20)
        
        # Calculate SMA on the close prices
        sma_values = talib.SMA(data['close'], timeperiod=period)
        
        return pd.Series(sma_values, index=data.index)
    
    def get_cache_key(self, params):
        """Generate unique cache key including timeframe"""
        period = params.get('period', 20)
        return f"sma_period{period}_{self.timeframe}"
```

### Multi-Timeframe Considerations
```python
class YourIndicatorCalculator(BaseCalculator):
    def calculate(self, data, params):
        # 'data' is already resampled to the target timeframe
        # specified in strategy.timeframe
        
        # For example, if strategy.timeframe = "4h":
        # - data contains 4-hour candles
        # - Indicators are calculated on 4h data
        # - Results are forward-filled to 1m by the framework
        
        # Access OHLCV as usual:
        close_prices = data['close']    # 4h closes
        high_prices = data['high']      # 4h highs
        volume = data['volume']         # 4h aggregated volume
        
        # Your calculation here...
```

## 2. Creating Entry Strategies

### File Location
```
strategies/entry/
├── base_entry.py          # Base class
├── price_above_sma.py     # Example
└── your_strategy.py       # Your new strategy
```

### Base Class
```python
# strategies/entry/base_entry.py
class BaseEntryStrategy:
    def __init__(self, params=None):
        self.params = params or {}
        self.name = self.__class__.__name__
    
    def should_enter(self, data):
        """
        Determine if entry conditions are met.
        
        Args:
            data: DataWindow object with access to current/past values
        
        Returns:
            bool: True if should enter position
        """
        raise NotImplementedError("Must implement should_enter()")
```

### Example: EMA Cross Entry
```python
# strategies/entry/ema_cross.py
from .base_entry import BaseEntryStrategy

class EMACrossEntry(BaseEntryStrategy):
    """
    Entry when fast EMA crosses above slow EMA.
    
    Config example:
    entry:
      name: "ema_cross"
      params:
        fast_column: "ema_12"
        slow_column: "ema_26"
    """
    
    def __init__(self, params=None):
        super().__init__(params)
        self.fast_column = params.get('fast_column', 'ema_12')
        self.slow_column = params.get('slow_column', 'ema_26')
    
    def should_enter(self, data):
        """
        Entry logic: Fast EMA crosses above Slow EMA
        
        Note: data contains values aligned to 1m resolution via forward-fill
        """
        # Access current and previous values
        fast_current = data[self.fast_column][0]
        slow_current = data[self.slow_column][0]
        fast_previous = data[self.fast_column][-1]
        slow_previous = data[self.slow_column][-1]
        
        # Cross-over detection
        cross_above = (fast_current > slow_current and 
                      fast_previous <= slow_previous)
        
        # Additional filters (optional)
        volume_ok = data['volume'][0] > 1000  # Minimum volume
        
        return cross_above and volume_ok
```

### Data Window Access
The `data` object provides sliding window access to all calculated values:

```python
def should_enter(self, data):
    # Price data (always available)
    current_close = data['close'][0]      # Current candle
    previous_close = data['close'][-1]     # Previous candle
    high_5_bars_ago = data['high'][-5]     # 5 bars ago
    
    # Indicator values (from config.yaml)
    sma_current = data['sma_200'][0]      # Current SMA200
    rsi_previous = data['rsi_14'][-1]     # Previous RSI
    atr_value = data['atr_14'][0]         # Current ATR
    
    # Time-based access
    current_time = data.index[0]          # Current timestamp
    hour = current_time.hour              # Extract hour
    
    return your_condition
```

## 3. Creating Exit Strategies

### File Location
```
strategies/exit/
├── base_exit.py           # Base class
├── hold_bars.py           # Example
├── fixed_tp_sl.py         # Example
└── your_exit.py           # Your new strategy
```

### Base Class
```python
# strategies/exit/base_exit.py
class BaseExitStrategy:
    def __init__(self, params=None):
        self.params = params or {}
        self.name = self.__class__.__name__
    
    def should_exit(self, data, entry_price, entry_time, position_type):
        """
        Determine if exit conditions are met.
        
        Args:
            data: DataWindow with current market context
            entry_price: Price at which position was entered
            entry_time: Timestamp of entry
            position_type: "long" or "short"
        
        Returns:
            tuple: (should_exit: bool, reason: str)
        """
        raise NotImplementedError("Must implement should_exit()")
```

### Example: Fixed Take Profit & Stop Loss
```python
# strategies/exit/fixed_tp_sl.py
from .base_exit import BaseExitStrategy

class FixedTPSLExit(BaseExitStrategy):
    """
    Exit with fixed percentage take profit and stop loss.
    
    Config example:
    exit:
      name: "fixed_tp_sl"
      params:
        tp_percent: 0.05    # 5% take profit
        sl_percent: 0.02    # 2% stop loss
    """
    
    def __init__(self, params=None):
        super().__init__(params)
        self.tp_percent = params.get('tp_percent', 0.05)
        self.sl_percent = params.get('sl_percent', 0.02)
    
    def should_exit(self, data, entry_price, entry_time, position_type):
        current_price = data['close'][0]
        
        # Calculate P&L percentage
        if position_type == "long":
            pnl_pct = (current_price / entry_price) - 1
        else:  # short
            pnl_pct = (entry_price / current_price) - 1
        
        # Check Take Profit
        if pnl_pct >= self.tp_percent:
            return True, "TAKE_PROFIT"
        
        # Check Stop Loss
        if pnl_pct <= -self.sl_percent:
            return True, "STOP_LOSS"
        
        # Optional: Time-based exit
        bars_held = len(data) - data.index.get_loc(entry_time)
        if bars_held > 50:  # Exit after 50 bars
            return True, "TIME_EXIT"
        
        return False, None
```

## 4. Creating Risk Managers

### File Location
```
strategies/risk/
├── base_risk.py           # Base class
├── fixed_percent.py       # Example
└── your_risk.py           # Your new manager
```

### Base Class
```python
# strategies/risk/base_risk.py
class BaseRiskManager:
    def __init__(self, params=None):
        self.params = params or {}
        self.name = self.__class__.__name__
    
    def calculate_position_size(self, capital, entry_price, 
                               stop_loss_price, position_type):
        """
        Calculate position size based on risk parameters.
        
        Args:
            capital: Available capital
            entry_price: Intended entry price
            stop_loss_price: Stop loss price
            position_type: "long" or "short"
        
        Returns:
            float: Position size (quantity)
        """
        raise NotImplementedError("Must implement calculate_position_size()")
```

### Example: Fixed Percentage Risk
```python
# strategies/risk/fixed_percent.py
from .base_risk import BaseRiskManager

class FixedPercentRisk(BaseRiskManager):
    """
    Risk fixed percentage of capital per trade.
    
    Config example:
    risk:
      name: "fixed_percent"
      params:
        risk_per_trade: 0.02    # Risk 2% per trade
    """
    
    def __init__(self, params=None):
        super().__init__(params)
        self.risk_per_trade = params.get('risk_per_trade', 0.02)
    
    def calculate_position_size(self, capital, entry_price, 
                               stop_loss_price, position_type):
        # Calculate risk amount
        risk_amount = capital * self.risk_per_trade
        
        # Calculate risk per unit
        if position_type == "long":
            risk_per_unit = entry_price - stop_loss_price
        else:  # short
            risk_per_unit = stop_loss_price - entry_price
        
        # Avoid division by zero
        if risk_per_unit <= 0:
            return 0
        
        # Calculate position size
        position_size = risk_amount / risk_per_unit
        
        return position_size
```

## 5. Complete Example: RSI Strategy

### Configuration
```yaml
# config.yaml
strategy:
  timeframe: "1h"
  
  entry:
    name: "rsi_oversold"
    params:
      rsi_column: "rsi_14"
      oversold_level: 30
  
  exit:
    name: "rsi_overbought"
    params:
      rsi_column: "rsi_14"
      overbought_level: 70
  
  risk:
    name: "fixed_percent"
    params:
      risk_per_trade: 0.01

indicators:
  - name: "rsi"
    params: {period: 14}
    column: "rsi_14"
```

### Entry Strategy
```python
# strategies/entry/rsi_oversold.py
from .base_entry import BaseEntryStrategy

class RSIOversoldEntry(BaseEntryStrategy):
    def __init__(self, params=None):
        super().__init__(params)
        self.rsi_column = params.get('rsi_column', 'rsi_14')
        self.oversold_level = params.get('oversold_level', 30)
    
    def should_enter(self, data):
        # Entry when RSI crosses above oversold level
        current_rsi = data[self.rsi_column][0]
        previous_rsi = data[self.rsi_column][-1]
        
        return (previous_rsi <= self.oversold_level and 
                current_rsi > self.oversold_level)
```

### Exit Strategy
```python
# strategies/exit/rsi_overbought.py
from .base_exit import BaseExitStrategy

class RSIOverboughtExit(BaseExitStrategy):
    def __init__(self, params=None):
        super().__init__(params)
        self.rsi_column = params.get('rsi_column', 'rsi_14')
        self.overbought_level = params.get('overbought_level', 70)
    
    def should_exit(self, data, entry_price, entry_time, position_type):
        current_rsi = data[self.rsi_column][0]
        
        # Exit when RSI reaches overbought level
        if current_rsi >= self.overbought_level:
            return True, "RSI_OVERBOUGHT"
        
        return False, None
```

## 6. Best Practices

### 1. **Keep Strategies Stateless**
- Don't store state between calls
- All conditions should use current data window
- Use `params` for configuration, not instance variables

### 2. **Document Required Indicators**
```python
class YourStrategy(BaseEntryStrategy):
    def get_required_indicators(self):
        """
        Optional: List indicators this strategy needs
        Helps with validation and dependency tracking
        """
        return ['sma_20', 'rsi_14', 'volume_ma']
```

### 3. **Use Descriptive Reason Strings**
```python
# Good:
return True, "TAKE_PROFIT_5_PERCENT"

# Bad:
return True, "exit"
```

### 4. **Handle Edge Cases**
```python
def should_enter(self, data):
    # Check if we have enough data
    if len(data) < 50:
        return False
    
    # Check if indicators are calculated
    if pd.isna(data['sma_200'][0]):
        return False
    
    # Your logic here...
```

### 5. **Add Logging for Debugging**
```python
import logging
logger = logging.getLogger(__name__)

class YourStrategy(BaseEntryStrategy):
    def should_enter(self, data):
        logger.debug(f"Current RSI: {data['rsi'][0]:.2f}")
        
        if condition:
            logger.info(f"Entry signal at {data.index[0]}")
            return True
        
        return False
```

## 7. Testing Your Components

### Quick Test Script
```python
# test_strategy.py
import sys
sys.path.append('.')
from strategies.entry.your_strategy import YourStrategy
import pandas as pd

# Load sample data
data = pd.read_parquet('data/raw/XPLUSDT-1m-2025-2026-01-22.parquet')

# Create strategy instance
strategy = YourStrategy(params={'period': 20})

# Test with data window (simplified)
# In practice, use the framework's DataWindow class
```

### Integration Test
1. Add your component to `config.yaml`
2. Run `python backtest.py` with small date range
3. Check journal output for expected behavior




