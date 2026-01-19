# core/engine.py

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

from core.data_window import DataWindow
from strategies.entry.base_entry import BaseEntryStrategy
from strategies.exit.base_exit import BaseExitStrategy
from strategies.risk.base_risk import BaseRiskManager


logger = logging.getLogger(__name__)


class BacktestEngine:
    """
    Main backtesting engine.
    Executes trading strategy on historical data.
    """
    
    def __init__(
        self,
        data: pd.DataFrame,
        entry_strategy: BaseEntryStrategy,
        exit_strategy: BaseExitStrategy,
        risk_manager: BaseRiskManager = None,
        initial_capital: float = 10000,
        commission: float = 0.001,  # 0.1%
        lookback_window: int = 100
    ):
        """
        Initialize backtesting engine.
        
        Args:
            data: DataFrame with OHLCV data and indicators
            entry_strategy: Entry strategy instance
            exit_strategy: Exit strategy instance
            risk_manager: Risk manager instance (optional)
            initial_capital: Starting capital
            commission: Trading commission as decimal (0.001 = 0.1%)
            lookback_window: Number of candles to keep in memory window
        """
        self.data = data
        self.entry_strategy = entry_strategy
        self.exit_strategy = exit_strategy
        self.risk_manager = risk_manager
        self.initial_capital = initial_capital
        self.commission = commission
        self.lookback_window = lookback_window
        
        # Trading state
        self.capital = initial_capital
        self.position = None  # None or dict with position info
        self.trades = []
        self.journal = []
        
        # Performance metrics
        self.equity_curve = []
        
        logger.info(f"Initialized BacktestEngine")
        logger.info(f"  Initial capital: ${initial_capital:,.2f}")
        logger.info(f"  Commission: {commission*100:.2f}%")
        logger.info(f"  Lookback window: {lookback_window} candles")
        logger.info(f"  Entry strategy: {entry_strategy}")
        logger.info(f"  Exit strategy: {exit_strategy}")
        logger.info(f"  Risk manager: {self.risk_manager.name}")
    
    def run(self) -> Dict[str, Any]:
        """
        Run the backtest.
        
        Returns:
            Dictionary with backtest results and metrics
        """
        logger.info(f"Starting backtest on {len(self.data)} candles...")
        
        total_candles = len(self.data)
        
        # Main loop
        for i in range(self.lookback_window, total_candles):
            # Create data window for current position
            data_window = DataWindow(self.data, i, self.lookback_window)
            current_time = data_window.get_timestamp()
            current_price = data_window['close'][0]
            
            # Check if trading is allowed (risk management)
            if not self.risk_manager.can_trade(self.capital, 0, None):
                # Still update journal but don't trade
                self._update_journal(i, data_window)
                self._update_equity(i, current_price)
                continue
            
            # Update journal
            self._update_journal(i, data_window)
            
            if self.position is None:
                # Check for entry signal
                if self.entry_strategy.should_enter(data_window):
                    self._enter_position(i, data_window)
            
            else:
                # Check for exit signal
                should_exit, exit_reason = self.exit_strategy.should_exit(
                    data_window,
                    self.position['entry_price'],
                    self.position['entry_time'],
                    {
                        **self.position,  # Include all position fields
                        'current_index': i  # Add current_index!
                    }
                )
                
                if should_exit:
                    self._exit_position(i, data_window, exit_reason)
            
            # Update equity curve
            self._update_equity(i, current_price)
            
            # Progress logging
            if i % 10000 == 0:
                logger.info(f"Processed {i:,}/{total_candles:,} candles")
        
        # Close any open position at the end
        if self.position is not None:
            last_idx = total_candles - 1
            last_data = DataWindow(self.data, last_idx, self.lookback_window)
            self._exit_position(last_idx, last_data, 'END_OF_DATA')
        
        logger.info(f"Backtest completed. Executed {len(self.trades)} trades.")
        
        # Calculate performance metrics
        results = self._calculate_results()
        
        return results
    
    def _enter_position(self, index: int, data_window: DataWindow):
        """
        Enter a new position with risk management.
        """
        entry_price = data_window['close'][0]
        entry_time = data_window.get_timestamp()
        
        # Check if trading is allowed (additional check)
        if not self.risk_manager.can_trade(self.capital, 0, None):
            logger.warning(f"Risk manager blocked entry at {entry_time}")
            return
        
        # Get stop loss price from exit strategy if available
        stop_loss_price = None
        if hasattr(self.exit_strategy, 'sl_percent'):
            # FixedTPSL exit strategy
            stop_loss_price = entry_price * (1 - self.exit_strategy.sl_percent)
        
        # ✅ Rename to risk_amount for clarity
        risk_amount = self.risk_manager.calculate_position_size(
            capital=self.capital,
            entry_price=entry_price,
            stop_loss_price=stop_loss_price,
            direction="LONG",
            volatility=None  # Will add ATR later
        )
        
        # ✅  Convert risk amount to quantity
        quantity = risk_amount / entry_price  # 200$ / 100000$ = 0.002 BTC
        position_value = risk_amount  # position_value = 200$ (già calcolato dal risk manager)
        
        # Check if we have enough capital
        if position_value > self.capital:
            logger.warning(f"Insufficient capital: needed ${position_value:.2f}, have ${self.capital:.2f}")
            return
        
        if quantity <= 0:  # ✅  Check quantity, not risk_amount
            logger.warning(f"Invalid position quantity: {quantity}")
            return
        
        # Calculate commission (based on position value)
        commission_paid = position_value * self.commission
        
        # Store TOTAL EQUITY before entry (for P&L calculations)
        total_equity_before = self.capital  # At this point, all capital is available
        
        # Store position ✅  Store quantity, not risk_amount
        self.position = {
            'entry_index': index,
            'entry_price': entry_price,
            'entry_time': entry_time,
            'position_size': quantity,  # ← Store QUANTITY here
            'position_type': 'long',
            'commission_paid': commission_paid,
            'total_equity_before_entry': total_equity_before,
            'position_value_entry': position_value,
            'available_balance_before': self.capital,
            'risk_amount': risk_amount  # ✅ Optional: store for debugging
        }
        
        # Deduct position value and commission from capital (available balance)
        self.capital -= position_value + commission_paid
        
        # Calculate total equity after entry (available balance + position value)
        total_equity_after = self.capital + position_value
        
        logger.info(
            f"📈 ENTRY at {entry_time} | "
            f"Price: ${entry_price:.2f} | "
            f"Quantity: {quantity:.6f} | "  # ✅  Log quantity
            f"Position Value: ${position_value:.2f} | "
            f"Available Balance: ${self.capital:.2f} | "
            f"Total Equity: ${total_equity_after:.2f} | "
            f"Commission: ${commission_paid:.2f} | "
            f"Equity Change: ${total_equity_after - total_equity_before:+.2f}"
        )
        
        # Record trade entry (✅  Store quantity)
        trade = {
            'entry_index': index,
            'entry_time': entry_time,
            'entry_price': entry_price,
            'position_size': quantity,  # ← Store QUANTITY here
            'position_value': position_value,
            'commission_entry': commission_paid,
            'total_equity_before': total_equity_before,
            'available_balance_after_entry': self.capital,
            'total_equity_after_entry': total_equity_after,
            'risk_amount': risk_amount  # ✅ Optional: store for debugging
        }
        self.trades.append(trade)

    
    def _exit_position(self, index: int, data_window: DataWindow, reason: str):
        """
        Exit current position.
        """
        exit_price = data_window['close'][0]
        exit_time = data_window.get_timestamp()
        
        if self.position is None:
            logger.warning("Attempted to exit but no position is open")
            return
        
        # Get position details
        entry_price = self.position['entry_price']
        position_size = self.position['position_size']
        total_equity_before_entry = self.position['total_equity_before_entry']
        position_value_entry = self.position['position_value_entry']
        available_balance_before = self.position['available_balance_before']
        
        # Calculate exit value
        exit_value = position_size * exit_price
        
        # Exit commission
        exit_commission = exit_value * self.commission
        
        # Net exit value (after commission)
        net_exit_value = exit_value - exit_commission
        
        # Store available balance before exit for calculations
        available_balance_before_exit = self.capital
        
        # Update available balance (return position value + profits/losses)
        self.capital += net_exit_value
        
        # Calculate TOTAL EQUITY after exit (just available balance now, no position)
        total_equity_after_exit = self.capital
        
        # Calculate P&L
        gross_pnl = exit_value - position_value_entry
        total_commission = self.position['commission_paid'] + exit_commission
        net_pnl = gross_pnl - total_commission
        
        # Calculate percentages based on TOTAL EQUITY before entry
        pnl_percent = (exit_price / entry_price - 1) * 100
        net_pnl_percent = (net_pnl / total_equity_before_entry) * 100
        
        # Bars held
        bars_held = index - self.position['entry_index']
        
        logger.info(
            f"📉 EXIT at {exit_time} | "
            f"Price: ${exit_price:.2f} | "
            f"Reason: {reason} | "
            f"Bars held: {bars_held} | "
            f"Position Size: {position_size:.6f} | "
            f"Entry Value: ${position_value_entry:.2f} | "
            f"Exit Value: ${exit_value:.2f} | "
            f"Gross P&L: ${gross_pnl:+.2f} ({pnl_percent:+.2f}%) | "
            f"Net P&L: ${net_pnl:+.2f} ({net_pnl_percent:+.2f}%) | "
            f"Total Commission: ${total_commission:.2f} | "
            f"Available Balance: ${self.capital:.2f} | "
            f"Total Equity: ${total_equity_after_exit:.2f}"
        )
        
        # Complete trade record
        current_trade = self.trades[-1]
        current_trade.update({
            'exit_index': index,
            'exit_time': exit_time,
            'exit_price': exit_price,
            'exit_reason': reason,
            'bars_held': bars_held,
            'gross_pnl': gross_pnl,
            'net_pnl': net_pnl,
            'pnl_percent': pnl_percent,
            'net_pnl_percent': net_pnl_percent,
            'commission_exit': exit_commission,
            'available_balance_before_exit': available_balance_before_exit,
            'available_balance_after': self.capital,
            'total_equity_after': total_equity_after_exit
        })
        
        # Reset position
        self.position = None


    
    def _update_journal(self, index: int, data_window: DataWindow):
        """
        Update trading journal with current state.
        
        Args:
            index: Current data index
            data_window: Current data window
        """
        current_price = data_window['close'][0]
        
        # Always include these basic fields
        journal_entry = {
            'index': index,
            'timestamp': data_window.get_timestamp(),
            'price': current_price,
            'in_position': self.position is not None,
            'available_balance': self.capital,  # RENAMED for clarity - liquid cash
            'total_equity': self.capital,       # Will update if in position
            'position_size': None,
            'entry_price': None,
            'position_value': None,
            'unrealized_pnl': None,
            'unrealized_pnl_percent': None
        }
        
        # Add position info if in position
        if self.position:
            entry_price = self.position['entry_price']
            position_size = self.position['position_size']
            
            # Calculate current position value
            position_value = position_size * current_price
            
            # Calculate unrealized P&L (gross, before commission)
            unrealized_pnl = position_value - (position_size * entry_price)
            unrealized_pnl_percent = (current_price / entry_price - 1) * 100
            
            # Calculate total equity (available balance + position value)
            total_equity = self.capital + position_value
            
            journal_entry.update({
                'position_size': position_size,
                'entry_price': entry_price,
                'position_value': position_value,
                'unrealized_pnl': unrealized_pnl,
                'unrealized_pnl_percent': unrealized_pnl_percent,
                'total_equity': total_equity  # CORRECTED!
            })
        
        self.journal.append(journal_entry)
    
    def _update_equity(self, index: int, current_price: float):
        """
        Update equity curve.
        Equity = available balance + position value (if any)
        """
        if self.position is None:
            equity = self.capital  # Just available balance
        else:
            # Calculate current position value
            position_value = self.position['position_size'] * current_price
            # Equity = available balance + position value
            equity = self.capital + position_value
        
        # Get timestamp from data if available, otherwise use current time
        # For simplicity, we'll store index for now, can add timestamp later if needed
        equity_entry = {
            'index': index,
            'equity': equity,
            'available_balance': self.capital,
            'price': current_price,
            'in_position': self.position is not None
        }
        
        # Add timestamp if we're tracking it separately
        # Note: We don't have easy access to current timestamp here without DataWindow
        # For Phase 2, index is sufficient
        
        self.equity_curve.append(equity_entry)
    
    def _calculate_results(self) -> Dict[str, Any]:
        """
        Calculate performance metrics.
        """
        if not self.trades:
            logger.warning("No trades were executed")
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                
                'initial_capital': self.initial_capital,
                'final_available_balance': self.capital,  # RENAMED
                'final_total_equity': self.capital,       # ADDED
                'total_return_percent': (self.capital / self.initial_capital - 1) * 100,
                'total_net_pnl': 0,
                'total_gross_pnl': 0,
                'total_commission': 0,
                
                'avg_net_pnl': 0,
                'avg_bars_held': 0,
                'profit_factor': 0,
                'max_drawdown_percent': 0,
                
                'trades': self.trades,
                'journal': self.journal,
                'equity_curve': self.equity_curve,
                'message': 'No trades executed'
            }
        
        # Basic metrics
        total_trades = len(self.trades)
        winning_trades = sum(1 for t in self.trades if t['net_pnl'] > 0)
        losing_trades = total_trades - winning_trades
        
        # P&L metrics
        total_net_pnl = sum(t['net_pnl'] for t in self.trades)
        total_gross_pnl = sum(t['gross_pnl'] for t in self.trades)
        total_commission = sum(t['commission_entry'] + t.get('commission_exit', 0) 
                             for t in self.trades)
        
        # Percent returns - use FINAL TOTAL EQUITY from equity curve
        final_equity = self.equity_curve[-1]['equity'] if self.equity_curve else self.capital
        total_return = (final_equity / self.initial_capital - 1) * 100
        
        # Average trade metrics
        avg_net_pnl = total_net_pnl / total_trades if total_trades > 0 else 0
        avg_bars_held = sum(t['bars_held'] for t in self.trades) / total_trades if total_trades > 0 else 0
        
        # Win rate
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Profit factor (Gross Profits / Gross Losses)
        gross_profits = sum(t['gross_pnl'] for t in self.trades if t['gross_pnl'] > 0)
        gross_losses = abs(sum(t['gross_pnl'] for t in self.trades if t['gross_pnl'] < 0))
        profit_factor = gross_profits / gross_losses if gross_losses > 0 else float('inf')
        
        # Max drawdown - calculated on TOTAL EQUITY
        equity_values = [e['equity'] for e in self.equity_curve]
        if equity_values:
            running_max = np.maximum.accumulate(equity_values)
            drawdowns = (equity_values - running_max) / running_max * 100
            max_drawdown = abs(min(drawdowns)) if len(drawdowns) > 0 else 0
        else:
            max_drawdown = 0
        
        # Risk-adjusted metrics (to be implemented in Phase 4)
        sharpe_ratio = 0
        sortino_ratio = 0
        
        results = {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            
            'initial_capital': self.initial_capital,
            'final_available_balance': self.capital,
            'final_total_equity': final_equity,
            'total_return_percent': total_return,
            'total_net_pnl': total_net_pnl,
            'total_gross_pnl': total_gross_pnl,
            'total_commission': total_commission,
            
            'avg_net_pnl': avg_net_pnl,
            'avg_bars_held': avg_bars_held,
            'profit_factor': profit_factor,
            'max_drawdown_percent': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            
            'trades': self.trades,
            'journal': self.journal,
            'equity_curve': self.equity_curve,
            'risk_manager': self.risk_manager.name,

            'data': self.data   # All DataFrame
        }
        
        return results

    
    def print_summary(self, results: Dict[str, Any]):
        """
        Print backtest summary to console.
        
        Args:
            results: Results dictionary from run()
        """
        print("\n" + "="*60)
        print("BACKTEST SUMMARY")
        print("="*60)
        
        if 'message' in results:
            print(f"\n{results['message']}")
            return
        
        print(f"\n📈 Performance:")
        print(f"  Initial Capital:        ${results['initial_capital']:,.2f}")
        print(f"  Final Available Balance: ${results['final_available_balance']:,.2f}")
        print(f"  Final Total Equity:      ${results['final_total_equity']:,.2f}")
        print(f"  Total Return:           {results['total_return_percent']:+.2f}%")
        print(f"  Total P&L:              ${results['total_net_pnl']:+.2f}")
        print(f"  Total Costs:            ${results['total_commission']:,.2f}")
        print(f"  Max Drawdown:           {results['max_drawdown_percent']:.2f}%")
        
        print(f"\n📊 Trade Statistics:")
        print(f"  Total Trades:    {results['total_trades']}")
        print(f"  Winning Trades:  {results['winning_trades']} ({results['win_rate']:.1f}%)")
        print(f"  Losing Trades:   {results['losing_trades']}")
        print(f"  Profit Factor:   {results['profit_factor']:.2f}")
        print(f"  Avg P&L/Trade:  ${results['avg_net_pnl']:+.2f}")
        print(f"  Avg Bars Held:   {results['avg_bars_held']:.1f}")
        
        print(f"\n⚖️  Risk Management:")
        print(f"  Risk Manager:    {results.get('risk_manager', 'None')}")
        
        if results['trades']:
            print(f"\n🔍 Recent Trades:")
            for i, trade in enumerate(results['trades'][-5:], 1):
                symbol = "✅" if trade['net_pnl'] > 0 else "❌"
                print(f"  {symbol} Entry: ${trade['entry_price']:.2f} → "
                    f"Exit: ${trade['exit_price']:.2f} "
                    f"({trade['net_pnl_percent']:+.2f}%) - {trade['exit_reason']}")
        
        print(f"\n💡 Summary:")
        if results['total_return_percent'] > 0:
            print(f"  Strategy was profitable! 🎉")
        else:
            print(f"  Strategy was not profitable. 😔")
        
        if results['max_drawdown_percent'] > 20:
            print(f"  Warning: High drawdown ({results['max_drawdown_percent']:.1f}%)!")
        
        print("="*60)
