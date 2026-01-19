# 🧩 HOW TO WRITE COMPONENTS FOR THE FRAMEWORK

## 1. HOW TO WRITE AN INDICATOR

**File:** `indicators/sma_calculator.py`

```python
from .base_calculator import BaseCalculator
import talib

class SMACalculator(BaseCalculator):
    """
    Calculates Simple Moving Average
    Config example: {name: "sma", params: {period: 20}, tf: "1m", column: "sma_20"}
    """
    
    def calculate(self, data, params):
        """
        data: DataFrame with OHLCV + other columns
        params: dict with parameters (e.g., {"period": 20})
        Returns: Series with SMA values
        """
        period = params.get('period', 20)
        
        # If there's tf_multiplier (indicator on different timeframe)
        if hasattr(self, 'tf_multiplier'):
            period = period * self.tf_multiplier
        
        # Calculate SMA using TA-Lib (or your own implementation)
        sma_values = talib.SMA(data['close'], timeperiod=period)
        
        return sma_values
```

Automatic registration: The system finds all files in indicators/ and registers them automatically.

## 2. HOW TO WRITE AN ENTRY STRATEGY

File: strategies/entry/ema_cross.py

```python
from .base_entry import BaseEntryStrategy

class EMACrossEntry(BaseEntryStrategy):
    """
    Enters when fast EMA crosses above slow EMA
    Config: {name: "ema_cross", params: {fast: 20, slow: 50}}
    """
    
    def __init__(self, params=None):
        super().__init__(params)
        self.fast_period = params.get('fast_period', 20)
        self.slow_period = params.get('slow_period', 50)
    
    def should_enter(self, data):
        """
        data: special object that allows access with offset
               data['ema_fast'][0] = current value
               data['ema_fast'][-1] = previous candle value
               data['ema_fast'][-2] = two candles ago
        
        Returns: True if entry conditions are satisfied
        """
        # Access PRECALCULATED indicators
        # Names ('ema_fast', 'ema_slow') come from config.yaml
        ema_fast = data['ema_fast']
        ema_slow = data['ema_slow']
        
        # Entry logic
        current_cross = ema_fast[0] > ema_slow[0]
        previous_cross = ema_fast[-1] <= ema_slow[-1]
        
        # Additional conditions if needed
        volume_ok = data['volume'][0] > data['volume_sma'][0]
        
        return current_cross and previous_cross and volume_ok
```

The data object - How it works:
```python
# Inside should_enter(), you have access to:
data['close'][0]      # Current close price
data['close'][-1]     # Previous close
data['close'][-5]     # Close 5 candles ago

data['sma_20'][0]     # Current SMA20 (already calculated)
data['rsi_14'][-1]    # RSI14 previous candle

data['volume']        # All volumes (list/array)
data['high']          # All highs
# ... any column present in the data

# The engine provides a "sliding window" of data
# so you can access past values with negative offset
```

## 3. HOW TO WRITE AN EXIT STRATEGY

File: strategies/exit/fixed_tp_sl.py

```python
from .base_exit import BaseExitStrategy

class FixedTPSLExit(BaseExitStrategy):
    """
    Exit with fixed Take Profit and Stop Loss
    Config: {name: "fixed_tp_sl", params: {tp_percent: 0.05, sl_percent: 0.02}}
    """
    
    def __init__(self, params=None):
        super().__init__(params)
        self.tp_percent = params.get('tp_percent', 0.05)  # +5%
        self.sl_percent = params.get('sl_percent', 0.02)  # -2%
    
    def should_exit(self, data, entry_price, entry_time):
        """
        data: same object as entry strategies
        entry_price: price at which we entered (provided by engine)
        entry_time: entry timestamp (provided by engine)
        
        Returns: (should_exit, reason)
        - should_exit: True to exit
        - reason: string reason ("TP", "SL", "TRAILING", etc.)
        """
        current_price = data['close'][0]
        
        # Calculate P&L percentage
        pnl_pct = (current_price / entry_price) - 1
        
        # Check Take Profit
        if pnl_pct >= self.tp_percent:
            return True, "TAKE_PROFIT"
        
        # Check Stop Loss
        if pnl_pct <= -self.sl_percent:
            return True, "STOP_LOSS"
        
        # Other exit conditions (e.g., contrary signal)
        if data['rsi'][0] > 70:  # RSI overbought
            return True, "RSI_OVERBOUGHT"
        
        return False, None
```

## 4. HOW TO WRITE RISK MANAGEMENT

File: strategies/risk/fixed_percent.py

```python
from .base_risk import BaseRiskManager

class FixedPercentRisk(BaseRiskManager):
    """
    Risks fixed percentage of capital per trade
    Config: {name: "fixed_percent", params: {risk_per_trade: 0.02}}
    """
    
    def __init__(self, params=None):
        super().__init__(params)
        self.risk_per_trade = params.get('risk_per_trade', 0.02)  # 2%
    
    def calculate_position_size(self, capital, entry_price, stop_loss_price):
        """
        Calculate how much to buy/sell
        
        Formula: position_size = (capital * risk_per_trade) / (entry_price - stop_loss_price)
        
        capital: available capital
        entry_price: entry price
        stop_loss_price: stop loss price (from exit strategy)
        
        Returns: quantity to trade (e.g., 0.5 BTC)
        """
        risk_amount = capital * self.risk_per_trade
        risk_per_unit = abs(entry_price - stop_loss_price)
        
        if risk_per_unit <= 0:
            return 0  # Avoid division by zero
        
        position_size = risk_amount / risk_per_unit
        
        return position_size
```

## 5. COMPLETE CANDLE-FLOW

For each candle (ordered timestamp):
    ↓
1. Engine prepares "data window":
   - Takes current OHLCV
   - Adds all calculated indicators
   - Creates object with offset access (data['ind'][0], [-1], etc.)
    ↓
2. If NOT in position:
   - Calls entry_strategy.should_enter(data)
   - If True: calculates position size → enters
    ↓
3. If IN position:
   - Calls exit_strategy.should_exit(data, entry_price, entry_time)
   - If True: executes exit → calculates P&L
    ↓
4. Writes to journal:
   - Timestamp, symbol, price
   - entry_signal (True/False)
   - exit_signal (True/False + reason)
   - in_position, position_size, capital
   - indicator values (optional)
6. COMPLETE EXAMPLE: SMA CROSS STRATEGY

config.yaml:
```yaml
strategy:
  entry:
    name: "sma_cross"
    params:
      fast_period: 20
      slow_period: 50
  
  exit:
    name: "fixed_tp_sl"
    params:
      tp_percent: 0.03
      sl_percent: 0.015

indicators:
  - name: "sma"
    params: {period: 20}
    tf: "1m"
    column: "sma_fast"
  
  - name: "sma"
    params: {period: 50}
    tf: "1m"
    column: "sma_slow"
```

### strategies/EXAMPLES
```python
class SMACrossEntry:
    def should_enter(self, data):
        # Condition: SMA20 crosses above SMA50
        return (
            data['sma_fast'][0] > data['sma_slow'][0] and 
            data['sma_fast'][-1] <= data['sma_slow'][-1]
        )



class FixedTPSLExit:
    def should_exit(self, data, entry_price, entry_time):
        current_price = data['close'][0]
        pnl = (current_price / entry_price) - 1
        
        if pnl >= 0.03:    # TP +3%
            return True, "TAKE_PROFIT"
        elif pnl <= -0.015: # SL -1.5%
            return True, "STOP_LOSS"
        
        return False, None
```

## 7. BASE CLASSES (templates to follow)

### strategies/entry/base_entry.py:

```python
class BaseEntryStrategy:
    """Base class for all entry strategies"""
    
    def __init__(self, params=None):
        self.params = params or {}
        self.name = self.__class__.__name__
    
    def should_enter(self, data):
        """
        TO BE IMPLEMENTED by child classes
        data: object with access to data and indicators
        Returns: True if entry conditions satisfied
        """
        raise NotImplementedError("Must implement should_enter()")
    
    def get_required_indicators(self):
        """
        Optional: list of required indicators
        Example: ['sma_20', 'rsi_14', 'volume_ma']
        """
        return []
```

### strategies/exit/base_exit.py:

```python
class BaseExitStrategy:
    """Base class for all exit strategies"""
    
    def __init__(self, params=None):
        self.params = params or {}
        self.name = self.__class__.__name__
    
    def should_exit(self, data, entry_price, entry_time):
        """
        TO BE IMPLEMENTED
        Returns: (should_exit: bool, reason: str)
        """
        raise NotImplementedError("Must implement should_exit()")
```

### indicators/base_calculator.py:

```python
class BaseCalculator:
    """Base class for all indicators"""
    
    def __init__(self, symbol=None, timeframe=None):
        self.symbol = symbol
        self.timeframe = timeframe
    
    def calculate(self, data, params):
        """
        TO BE IMPLEMENTED
        data: DataFrame with OHLCV
        params: dict with indicator parameters
        Returns: Series with calculated values
        """
        raise NotImplementedError("Must implement calculate()")
    
    def get_cache_key(self, params):
        """
        Generate unique key for cache
        Example: "sma_20_1m" for SMA period 20 on TF 1m
        """
        param_str = "_".join(f"{k}{v}" for k, v in sorted(params.items()))
        return f"{self.__class__.__name__.lower()}_{param_str}_{self.timeframe}"
```

## 8. CONVENTIONS AND BEST PRACTICES

Indicator names in config = column names in data
Negative offsets for past values: [0] current, [-1] previous
Strategies don't manage state - only boolean conditions
Everything configurable via YAML - no hardcoded values
Intelligent caching - reuses indicators between strategies

## 9. DEBUGGING AND LOGGING
In strategies you can add logging:

```python
import logging
logger = logging.getLogger(__name__)

class MyStrategy(BaseEntryStrategy):
    def should_enter(self, data):
        # Log values for debugging
        logger.debug(f"SMA fast: {data['sma_fast'][0]:.2f}, SMA slow: {data['sma_slow'][0]:.2f}")
        
        if condition:
            logger.info(f"ENTRY SIGNAL at {data['timestamp'][0]}")
            return True
        
        return False
```

The Parquet journal contains ALL data for post-trade analysis.

With this guide, writing a new strategy is:
- Define indicators in config.yaml
- Write 10-20 lines in strategies/entry/new_strategy.py
- Run python backtest.py