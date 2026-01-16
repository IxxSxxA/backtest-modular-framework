# 🧩 COME SCRIVERE COMPONENTI PER IL FRAMEWORK

## **1. COME SCRIVERE UN INDICATORE**

**File:** `indicators/sma_calculator.py`
```python
from .base_calculator import BaseCalculator
import talib

class SMACalculator(BaseCalculator):
    """
    Calcola Simple Moving Average
    Config example: {name: "sma", params: {period: 20}, tf: "1m", column: "sma_20"}
    """
    
    def calculate(self, data, params):
        """
        data: DataFrame con OHLCV + altre colonne
        params: dict con parametri (es: {"period": 20})
        Restituisce: Series con valori SMA
        """
        period = params.get('period', 20)
        
        # Se c'è tf_multiplier (indicatore su TF diverso)
        if hasattr(self, 'tf_multiplier'):
            period = period * self.tf_multiplier
        
        # Calcola SMA usando TA-Lib (o tua implementazione)
        sma_values = talib.SMA(data['close'], timeperiod=period)
        
        return sma_values
```

Registrazione automatica: Il sistema trova tutti i file in indicators/ e li registra automaticamente.

## 2. COME SCRIVERE UNA STRATEGIA ENTRY

File: strategies/entry/ema_cross.py

```python
from .base_entry import BaseEntryStrategy

class EMACrossEntry(BaseEntryStrategy):
    """
    Entra quando EMA veloce incrocia sopra EMA lenta
    Config: {name: "ema_cross", params: {fast: 20, slow: 50}}
    """
    
    def __init__(self, params=None):
        super().__init__(params)
        self.fast_period = params.get('fast_period', 20)
        self.slow_period = params.get('slow_period', 50)
    
    def should_enter(self, data):
        """
        data: oggetto speciale che permette accesso con offset
               data['ema_fast'][0] = valore corrente
               data['ema_fast'][-1] = valore candela precedente
               data['ema_fast'][-2] = due candele fa
        
        Restituisce: True se condizioni entry soddisfatte
        """
        # Accedi agli indicatori PRECALCOLATI
        # I nomi ('ema_fast', 'ema_slow') vengono da config.yaml
        ema_fast = data['ema_fast']
        ema_slow = data['ema_slow']
        
        # Logica di entry
        current_cross = ema_fast[0] > ema_slow[0]
        previous_cross = ema_fast[-1] <= ema_slow[-1]
        
        # Eventuali condizioni aggiuntive
        volume_ok = data['volume'][0] > data['volume_sma'][0]
        
        return current_cross and previous_cross and volume_ok
```

### L'oggetto data - Come funziona:

```python
# Dentro should_enter(), hai accesso a:
data['close'][0]      # Prezzo close corrente
data['close'][-1]     # Close candela precedente
data['close'][-5]     # Close 5 candele fa

data['sma_20'][0]     # SMA20 corrente (già calcolata)
data['rsi_14'][-1]    # RSI14 candela precedente

data['volume']        # Tutti i volumi (lista/array)
data['high']          # Tutti gli high
# ... qualsiasi colonna presente nei dati

# L'engine fornisce una "finestra scorrevole" di dati
# così puoi accedere a valori passati con offset negativo
```

## 3. COME SCRIVERE UNA STRATEGIA EXIT

File: strategies/exit/fixed_tp_sl.py

```python
from .base_exit import BaseExitStrategy

class FixedTPSLExit(BaseExitStrategy):
    """
    Exit con Take Profit e Stop Loss fissi
    Config: {name: "fixed_tp_sl", params: {tp_percent: 0.05, sl_percent: 0.02}}
    """
    
    def __init__(self, params=None):
        super().__init__(params)
        self.tp_percent = params.get('tp_percent', 0.05)  # +5%
        self.sl_percent = params.get('sl_percent', 0.02)  # -2%
    
    def should_exit(self, data, entry_price, entry_time):
        """
        data: stesso oggetto delle entry strategies
        entry_price: prezzo a cui siamo entrati (fornito dall'engine)
        entry_time: timestamp dell'entry (fornito dall'engine)
        
        Restituisce: (should_exit, reason)
        - should_exit: True se uscire
        - reason: stringa motivo ("TP", "SL", "TRAILING", etc.)
        """
        current_price = data['close'][0]
        
        # Calcola P&L percentuale
        pnl_pct = (current_price / entry_price) - 1
        
        # Check Take Profit
        if pnl_pct >= self.tp_percent:
            return True, "TAKE_PROFIT"
        
        # Check Stop Loss
        if pnl_pct <= -self.sl_percent:
            return True, "STOP_LOSS"
        
        # Altre condizioni di exit (es: segnale contrario)
        if data['rsi'][0] > 70:  # RSI ipercomprato
            return True, "RSI_OVERBOUGHT"
        
        return False, None
```

## 4. COME SCRIVERE RISK MANAGEMENT

File: strategies/risk/fixed_percent.py

```python
from .base_risk import BaseRiskManager

class FixedPercentRisk(BaseRiskManager):
    """
    Rischia percentuale fissa del capitale per trade
    Config: {name: "fixed_percent", params: {risk_per_trade: 0.02}}
    """
    
    def __init__(self, params=None):
        super().__init__(params)
        self.risk_per_trade = params.get('risk_per_trade', 0.02)  # 2%
    
    def calculate_position_size(self, capital, entry_price, stop_loss_price):
        """
        Calcola quanto comprare/vendere
        
        Formula: position_size = (capital * risk_per_trade) / (entry_price - stop_loss_price)
        
        capital: capitale disponibile
        entry_price: prezzo di entry
        stop_loss_price: prezzo di stop loss (dal exit strategy)
        
        Restituisce: quantità da tradare (es: 0.5 BTC)
        """
        risk_amount = capital * self.risk_per_trade
        risk_per_unit = abs(entry_price - stop_loss_price)
        
        if risk_per_unit <= 0:
            return 0  # Evita divisione per zero
        
        position_size = risk_amount / risk_per_unit
        
        return position_size
```

## 5. IL FLUSSO COMPLETO DI UNA CANDELA

```text
Per ogni candela (timestamp ordinato):
    ↓
1. Engine prepara "data window":
   - Prende OHLCV corrente
   - Aggiunge tutti gli indicatori calcolati
   - Crea oggetto con accesso a offset (data['ind'][0], [-1], etc.)
    ↓
2. Se NON in posizione:
   - Chiama entry_strategy.should_enter(data)
   - Se True: calcola position size → entra
    ↓
3. Se IN posizione:
   - Chiama exit_strategy.should_exit(data, entry_price, entry_time)
   - Se True: esegue exit → calcola P&L
    ↓
4. Scrivi nel journal:
   - Timestamp, symbol, price
   - entry_signal (True/False)
   - exit_signal (True/False + reason)
   - in_position, position_size, capital
   - valori indicatori (opzionale)
```

## 6. ESEMPIO COMPLETO: SMA CROSS STRATEGY

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

### strategies/entry/sma_cross.py:

```python
class SMACrossEntry:
    def should_enter(self, data):
        # Condizione: SMA20 incrocia sopra SMA50
        return (
            data['sma_fast'][0] > data['sma_slow'][0] and 
            data['sma_fast'][-1] <= data['sma_slow'][-1]
        )
```

### strategies/exit/fixed_tp_sl.py:

```python
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

## 7. CLASSI BASE (template da seguire)

strategies/entry/base_entry.py:

```python
class BaseEntryStrategy:
    """Classe base per tutte le entry strategies"""
    
    def __init__(self, params=None):
        self.params = params or {}
        self.name = self.__class__.__name__
    
    def should_enter(self, data):
        """
        DA IMPLEMENTARE nelle classi figlie
        data: oggetto con accesso a dati e indicatori
        Restituisce: True se entry conditions soddisfatte
        """
        raise NotImplementedError("Devi implementare should_enter()")
    
    def get_required_indicators(self):
        """
        Opzionale: lista indicatori richiesti
        Es: ['sma_20', 'rsi_14', 'volume_ma']
        """
        return []
```

### strategies/exit/base_exit.py:

```python
class BaseExitStrategy:
    """Classe base per tutte le exit strategies"""
    
    def __init__(self, params=None):
        self.params = params or {}
        self.name = self.__class__.__name__
    
    def should_exit(self, data, entry_price, entry_time):
        """
        DA IMPLEMENTARE
        Restituisce: (should_exit: bool, reason: str)
        """
        raise NotImplementedError("Devi implementare should_exit()")
```

### indicators/base_calculator.py:

```python
class BaseCalculator:
    """Classe base per tutti gli indicatori"""
    
    def __init__(self, symbol=None, timeframe=None):
        self.symbol = symbol
        self.timeframe = timeframe
    
    def calculate(self, data, params):
        """
        DA IMPLEMENTARE
        data: DataFrame con OHLCV
        params: dict con parametri indicatore
        Restituisce: Series con valori calcolati
        """
        raise NotImplementedError("Devi implementare calculate()")
    
    def get_cache_key(self, params):
        """
        Genera chiave univoca per cache
        Es: "sma_20_1m" per SMA periodo 20 su TF 1m
        """
        param_str = "_".join(f"{k}{v}" for k, v in sorted(params.items()))
        return f"{self.__class__.__name__.lower()}_{param_str}_{self.timeframe}"
```

## 8. CONVENZIONI E BUONE PRATICHE

- Nomi indicatori nel config = nomi colonne in data
- Offset negativi per valori passati: [0] corrente, [-1] precedente
- Le strategie non gestiscono stato - solo condizioni booleane
- Tutto configurabile via YAML - niente hardcoded
- Cache intelligente - riutilizza indicatori tra strategie

## 9. DEBUGGING E LOGGING

Nelle strategie puoi aggiungere logging:

```python 
import logging
logger = logging.getLogger(__name__)

class MyStrategy(BaseEntryStrategy):
    def should_enter(self, data):
        # Logga valori per debugging
        logger.debug(f"SMA fast: {data['sma_fast'][0]:.2f}, SMA slow: {data['sma_slow'][0]:.2f}")
        
        if condition:
            logger.info(f"ENTRY SIGNAL at {data['timestamp'][0]}")
            return True
        
        return False
```

- Il journal parquet contiene TUTTI i dati per analisi post-trade.
- Con questa guida, scrivere una nuova strategia è:
- Definire indicatori in config.yaml
- Scrivere 10-20 righe in strategies/entry/nuova_strategia.py
- Eseguire python backtest.py