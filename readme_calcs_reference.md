# 📄 Calculation_Reference.md

## POSITION SIZING

### Fixed Percent Risk
```python
position_value = current_equity × risk_percent
quantity = position_value ÷ entry_price
```

Example:
Equity: $10,000
Risk %: 2%
Entry price: $100,000

position_value = 10,000 × 0.02 = $200
quantity = 200 ÷ 100,000 = 0.002 units

### Position Size from Risk Manager
```python
# From Risk Manager calculation
risk_amount = risk_manager.calculate_position_size(
    capital=current_capital,
    entry_price=entry_price,
    stop_loss_price=stop_loss_price,
    direction="LONG",
    volatility=None
)

# Convert to quantity
quantity = risk_amount / entry_price
position_value = risk_amount  # Same as risk_amount from risk manager
```

### Position Validation
```python
# Capital sufficiency check
if position_value > available_balance:
    logger.warning(f"Insufficient capital")

# Quantity validation
if quantity <= 0:
    logger.warning(f"Invalid position quantity")
```

## EQUITY & BALANCE

### Total Equity Calculation
```python
# When NOT in position:
total_equity = available_balance

# When IN position:
position_value = position_size × current_price
total_equity = available_balance + position_value
```

### Available Balance Updates

#### On Entry:
```python
entry_commission = position_value × commission_rate
available_balance -= (position_value + entry_commission)
```

#### On Exit:
```python
exit_value = position_size × exit_price
exit_commission = exit_value × commission_rate
net_exit_value = exit_value - exit_commission
available_balance += net_exit_value
```

### Equity Curve Update
```python
def update_equity(current_price):
    if not in_position:
        equity = available_balance
    else:
        position_value = position_size × current_price
        equity = available_balance + position_value
    return equity
```

## P&L CALCULATIONS

### Gross P&L
```python
# For a single position
gross_pnl = exit_value - entry_value
# or
gross_pnl = (exit_price - entry_price) × quantity

# Percentage return
pnl_percent = (exit_price / entry_price - 1) × 100
```

### Net P&L
```python
# Per trade
total_commission = entry_commission + exit_commission
net_pnl = gross_pnl - total_commission

# Percentage based on total equity before entry
net_pnl_percent = (net_pnl / total_equity_before_entry) × 100
```

### Unrealized P&L
```python
# While position is open
current_position_value = position_size × current_price
entry_value = position_size × entry_price
unrealized_pnl = current_position_value - entry_value
unrealized_pnl_percent = (current_price / entry_price - 1) × 100
```

### Cumulative P&L
```python
# Total across all trades
total_gross_pnl = sum(gross_pnl for trade in trades)
total_net_pnl = sum(net_pnl for trade in trades)
total_commission = sum(commission_entry + commission_exit for trade in trades)
```

## PERFORMANCE METRICS

### Total Return
```python
final_equity = equity_curve[-1]['equity']
total_return_percent = (final_equity / initial_capital - 1) × 100
```

### Win Rate & Trade Statistics
```python
total_trades = len(trades)
winning_trades = sum(1 for t in trades if t['net_pnl'] > 0)
losing_trades = total_trades - winning_trades
win_rate = (winning_trades / total_trades × 100) if total_trades > 0 else 0

# Average metrics
avg_net_pnl = total_net_pnl / total_trades if total_trades > 0 else 0
avg_bars_held = sum(t['bars_held'] for t in trades) / total_trades if total_trades > 0 else 0
```

### Profit Factor
```python
gross_profits = sum(t['gross_pnl'] for t in trades if t['gross_pnl'] > 0)
gross_losses = abs(sum(t['gross_pnl'] for t in trades if t['gross_pnl'] < 0))
profit_factor = gross_profits / gross_losses if gross_losses > 0 else float('inf')
```

## COMMISSIONS

### Commission Calculations
```python
commission_rate = 0.001  # 0.1%

# Entry commission
entry_commission = position_value × commission_rate

# Exit commission
exit_commission = exit_value × commission_rate

# Total per trade
total_commission = entry_commission + exit_commission
```

### Net Value After Commission
```python
# On exit
net_exit_value = exit_value - exit_commission
```

## MAX DRAWDOWN

### Equity-Based Drawdown
```python
# From equity curve
equity_values = [e['equity'] for e in equity_curve]
running_max = np.maximum.accumulate(equity_values)
drawdowns = (equity_values - running_max) / running_max × 100
max_drawdown = abs(min(drawdowns)) if len(drawdowns) > 0 else 0
```

### Current Drawdown
```python
peak_equity = max(equity_curve)
current_equity = equity_curve[-1]['equity']
current_drawdown = (peak_equity - current_equity) / peak_equity × 100
```

## TRADE LOGGING & JOURNAL

### Journal Entry Structure
```python
journal_entry = {
    'timestamp': current_time,
    'price': current_price,
    'in_position': bool(position),
    'available_balance': available_balance,
    'total_equity': total_equity,
    'position_size': position_size if in_position else None,
    'entry_price': entry_price if in_position else None,
    'position_value': position_value if in_position else None,
    'unrealized_pnl': unrealized_pnl if in_position else None,
    'unrealized_pnl_percent': unrealized_pnl_percent if in_position else None
}
```

### Trade Record (Completed)
```python
trade_record = {
    # Entry
    'entry_index': entry_index,
    'entry_time': entry_time,
    'entry_price': entry_price,
    'position_size': quantity,
    'position_value': position_value,
    'commission_entry': entry_commission,
    'total_equity_before': total_equity_before_entry,
    'available_balance_after_entry': available_balance,
    'total_equity_after_entry': total_equity_after_entry,
    
    # Exit
    'exit_index': exit_index,
    'exit_time': exit_time,
    'exit_price': exit_price,
    'exit_reason': reason,
    'bars_held': bars_held,
    'gross_pnl': gross_pnl,
    'net_pnl': net_pnl,
    'pnl_percent': pnl_percent,
    'net_pnl_percent': net_pnl_percent,
    'commission_exit': exit_commission,
    'available_balance_after': available_balance_after_exit,
    'total_equity_after': total_equity_after_exit
}
```

## VALIDATION CHECKS

### Position Entry Validation
```python
# Capital sufficiency
if position_value > available_balance:
    logger.warning(f"Insufficient capital")

# Quantity validation
if quantity <= 0:
    logger.warning(f"Invalid position quantity")

# Risk management check
if not risk_manager.can_trade(available_balance, 0, None):
    logger.warning(f"Risk manager blocked entry")
```

### State Consistency Checks
```python
# Equity consistency
calculated_equity = available_balance + (position_value if in_position else 0)
if abs(calculated_equity - reported_equity) > tolerance:
    logger.error(f"Equity mismatch detected")

# Position consistency
if in_position and position_size <= 0:
    logger.error(f"Invalid position size while in position")
```

## PERFORMANCE SUMMARY METRICS

### Key Metrics Dictionary
```python
results = {
    # Trade statistics
    'total_trades': total_trades,
    'winning_trades': winning_trades,
    'losing_trades': losing_trades,
    'win_rate': win_rate,
    
    # Capital evolution
    'initial_capital': initial_capital,
    'final_available_balance': final_available_balance,
    'final_total_equity': final_total_equity,
    'total_return_percent': total_return_percent,
    
    # P&L totals
    'total_net_pnl': total_net_pnl,
    'total_gross_pnl': total_gross_pnl,
    'total_commission': total_commission,
    
    # Performance metrics
    'avg_net_pnl': avg_net_pnl,
    'avg_bars_held': avg_bars_held,
    'profit_factor': profit_factor,
    'max_drawdown_percent': max_drawdown,
    
    # Additional metrics (placeholder for Phase 4)
    'sharpe_ratio': 0,
    'sortino_ratio': 0,
    
    # Raw data
    'trades': trades,
    'journal': journal,
    'equity_curve': equity_curve
}
```

## NOTES & CONVENTIONS

### Variable Naming
- `available_balance`: Liquid cash available for trading
- `total_equity`: available_balance + position_value (if in position)
- `position_size`: Quantity of asset (e.g., 0.002 BTC)
- `position_value`: Dollar value of position (e.g., $200)
- `risk_amount`: Maximum dollar amount to risk on a trade

### Commission Model
- Commission is percentage-based on trade value
- Applied both on entry and exit
- Deducted from available balance immediately

### P&L Reference Points
- Percent returns based on total equity before entry
- Drawdown calculated on total equity curve
- Unrealized P&L calculated against entry price

---

*Document updated with calculations extracted from `engine.py`*


Ho organizzato i calcoli in queste categorie principali:
1. **Position Sizing** - Come viene calcolata la dimensione della posizione
2. **Equity & Balance** - Gestione del capitale disponibile e dell'equity totale
3. **P&L Calculations** - Calcoli di profitto e perdita (realizzati e non realizzati)
4. **Performance Metrics** - Metriche di performance come win rate, profit factor
5. **Commissions** - Calcolo delle commissioni
6. **Max Drawdown** - Calcolo del drawdown
7. **Trade Logging** - Struttura dei dati per journal e trade records
8. **Validation Checks** - Controlli di validazione
9. **Performance Summary** - Metrica riassuntive

Tutti i calcoli sono presi direttamente dal codice `engine.py` e rappresentano esattamente come funziona il tuo framework.