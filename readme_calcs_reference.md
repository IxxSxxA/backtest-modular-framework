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

## EQUITY & BALANCE

Total Equity
```python
total_equity = available_balance + sum(open_positions_value)

# Available Balance Updates
# On Entry:
available_balance -= (position_value + entry_commission)

#On Exit:
available_balance += (position_value + net_pnl - exit_commission)
```

## P&L CALCULATIONS

### Gross P&L

```python
gross_pnl = (exit_price - entry_price) × quantity × direction_multiplier
# Where: LONG = 1, SHORT = -1
```

### Net P&L
```python
net_pnl = gross_pnl - total_commission
```

## PERFORMANCE METRICS

### Percent Returns

```python
gross_return = gross_pnl ÷ entry_value
net_return = net_pnl ÷ entry_value
```

### COMMISSIONS

Per Trade
```python
entry_commission = position_value × commission_rate
exit_commission = exit_value × commission_rate
total_commission = entry_commission + exit_commission
```

### MAX DRAWDOWN

DRAWDOWN
Peak-to-Trough
```python
current_drawdown = (peak_equity - current_equity) ÷ peak_equity
max_drawdown = max(all_current_drawdowns)
```

### RISK METRICS

Risk per Trade
```python
risk_amount = position_value
risk_percent = risk_amount ÷ total_equity

# Position Limits

max_position_value = total_equity × max_position_percent (default: 90%)

# VALIDATION CHECKS
# Capital Sufficiency: position_value ≤ available_balance
# Non-negative: quantity > 0, commission ≥ 0
# Drawdown Protection: Trading halted if current_drawdown > max_allowed
# Equity Consistency: |calculated_equity - reported_equity| < tolerance
```
