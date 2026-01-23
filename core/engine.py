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

    @classmethod
    def from_config(
        cls,
        config: Dict[str, Any],
        data: pd.DataFrame,
        entry_strategy: BaseEntryStrategy,
        exit_strategy: BaseExitStrategy,
        risk_manager: BaseRiskManager,
    ):
        """
        ✅ Factory method to create engine from config.yaml

        Args:
            config: Full config dictionary
            data: DataFrame with OHLCV + indicators
            entry_strategy: Entry strategy instance
            exit_strategy: Exit strategy instance
            risk_manager: Risk manager instance

        Returns:
            BacktestEngine instance
        """
        # ✅ Extract from new config structure
        backtest_config = config.get("backtest", {})

        initial_capital = backtest_config.get("capital", {}).get("initial", 10000)
        commission = backtest_config.get("costs", {}).get("commission", 0.001)
        lookback_window = backtest_config.get("execution", {}).get(
            "lookback_window", 100
        )

        logger.info("Creating BacktestEngine from config:")
        logger.info(f"  Initial Capital: ${initial_capital:,.2f}")
        logger.info(f"  Commission: {commission*100:.3f}%")
        logger.info(f"  Lookback Window: {lookback_window} bars")

        return cls(
            data=data,
            entry_strategy=entry_strategy,
            exit_strategy=exit_strategy,
            risk_manager=risk_manager,
            initial_capital=initial_capital,
            commission=commission,
            lookback_window=lookback_window,
        )

    def __init__(
        self,
        data: pd.DataFrame,
        entry_strategy: BaseEntryStrategy,
        exit_strategy: BaseExitStrategy,
        risk_manager: BaseRiskManager = None,
        initial_capital: float = 10000,
        commission: float = 0.001,
        lookback_window: int = 100,
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
        self.position = None
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
            current_price = data_window["close"][0]

            # Check if trading is allowed (risk management)
            if not self.risk_manager.can_trade(self.capital, 0, None):
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
                    self.position["entry_price"],
                    self.position["entry_time"],
                    {**self.position, "current_index": i},
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
            self._exit_position(last_idx, last_data, "END_OF_DATA")

        logger.info(f"Backtest completed. Executed {len(self.trades)} trades.")

        # Calculate performance metrics
        results = self._calculate_results()

        return results

    def _enter_position(self, index: int, data_window: DataWindow):
        """Enter a new position with risk management."""
        entry_price = data_window["close"][0]
        entry_time = data_window.get_timestamp()

        if not self.risk_manager.can_trade(self.capital, 0, None):
            logger.warning(f"Risk manager blocked entry at {entry_time}")
            return

        # Get stop loss price from exit strategy if available
        stop_loss_price = None
        if hasattr(self.exit_strategy, "sl_percent"):
            stop_loss_price = entry_price * (1 - self.exit_strategy.sl_percent)

        risk_amount = self.risk_manager.calculate_position_size(
            capital=self.capital,
            entry_price=entry_price,
            stop_loss_price=stop_loss_price,
            direction="LONG",
            volatility=None,
        )

        quantity = risk_amount / entry_price
        position_value = risk_amount

        if position_value > self.capital:
            logger.warning(
                f"Insufficient capital: needed ${position_value:.2f}, have ${self.capital:.2f}"
            )
            return

        if quantity <= 0:
            logger.warning(f"Invalid position quantity: {quantity}")
            return

        commission_paid = position_value * self.commission
        total_equity_before = self.capital

        self.position = {
            "entry_index": index,
            "entry_price": entry_price,
            "entry_time": entry_time,
            "position_size": quantity,
            "position_type": "long",
            "commission_paid": commission_paid,
            "total_equity_before_entry": total_equity_before,
            "position_value_entry": position_value,
            "available_balance_before": self.capital,
            "risk_amount": risk_amount,
        }

        self.capital -= position_value + commission_paid
        total_equity_after = self.capital + position_value

        logger.info(
            f"📈 ENTRY at {entry_time} | "
            f"Price: ${entry_price:.2f} | "
            f"Quantity: {quantity:.6f} | "
            f"Position Value: ${position_value:.2f} | "
            f"Available Balance: ${self.capital:.2f} | "
            f"Total Equity: ${total_equity_after:.2f} | "
            f"Commission: ${commission_paid:.2f}"
        )

        trade = {
            "entry_index": index,
            "entry_time": entry_time,
            "entry_price": entry_price,
            "position_size": quantity,
            "position_value": position_value,
            "commission_entry": commission_paid,
            "total_equity_before": total_equity_before,
            "available_balance_after_entry": self.capital,
            "total_equity_after_entry": total_equity_after,
            "risk_amount": risk_amount,
        }
        self.trades.append(trade)

    def _exit_position(self, index: int, data_window: DataWindow, reason: str):
        """Exit current position."""
        exit_price = data_window["close"][0]
        exit_time = data_window.get_timestamp()

        if self.position is None:
            logger.warning("Attempted to exit but no position is open")
            return

        entry_price = self.position["entry_price"]
        position_size = self.position["position_size"]
        total_equity_before_entry = self.position["total_equity_before_entry"]
        position_value_entry = self.position["position_value_entry"]

        exit_value = position_size * exit_price
        exit_commission = exit_value * self.commission
        net_exit_value = exit_value - exit_commission

        available_balance_before_exit = self.capital
        self.capital += net_exit_value
        total_equity_after_exit = self.capital

        gross_pnl = exit_value - position_value_entry
        total_commission = self.position["commission_paid"] + exit_commission
        net_pnl = gross_pnl - total_commission

        pnl_percent = (exit_price / entry_price - 1) * 100
        net_pnl_percent = (net_pnl / total_equity_before_entry) * 100
        bars_held = index - self.position["entry_index"]

        logger.info(
            f"📉 EXIT at {exit_time} | "
            f"Price: ${exit_price:.2f} | "
            f"Reason: {reason} | "
            f"Bars held: {bars_held} | "
            f"Net P&L: ${net_pnl:+.2f} ({net_pnl_percent:+.2f}%)"
        )

        current_trade = self.trades[-1]
        current_trade.update(
            {
                "exit_index": index,
                "exit_time": exit_time,
                "exit_price": exit_price,
                "exit_reason": reason,
                "bars_held": bars_held,
                "gross_pnl": gross_pnl,
                "net_pnl": net_pnl,
                "pnl_percent": pnl_percent,
                "net_pnl_percent": net_pnl_percent,
                "commission_exit": exit_commission,
                "available_balance_before_exit": available_balance_before_exit,
                "available_balance_after": self.capital,
                "total_equity_after": total_equity_after_exit,
            }
        )

        self.position = None

    def _update_journal(self, index: int, data_window: DataWindow):
        """Update trading journal with current state."""
        current_price = data_window["close"][0]

        journal_entry = {
            "index": index,
            "timestamp": data_window.get_timestamp(),
            "price": current_price,
            "in_position": self.position is not None,
            "available_balance": self.capital,
            "total_equity": self.capital,
            "position_size": None,
            "entry_price": None,
            "position_value": None,
            "unrealized_pnl": None,
            "unrealized_pnl_percent": None,
        }

        if self.position:
            entry_price = self.position["entry_price"]
            position_size = self.position["position_size"]
            position_value = position_size * current_price
            unrealized_pnl = position_value - (position_size * entry_price)
            unrealized_pnl_percent = (current_price / entry_price - 1) * 100
            total_equity = self.capital + position_value

            journal_entry.update(
                {
                    "position_size": position_size,
                    "entry_price": entry_price,
                    "position_value": position_value,
                    "unrealized_pnl": unrealized_pnl,
                    "unrealized_pnl_percent": unrealized_pnl_percent,
                    "total_equity": total_equity,
                }
            )

        self.journal.append(journal_entry)

    def _update_equity(self, index: int, current_price: float):
        """Update equity curve."""
        if self.position is None:
            equity = self.capital
        else:
            position_value = self.position["position_size"] * current_price
            equity = self.capital + position_value

        equity_entry = {
            "index": index,
            "equity": equity,
            "available_balance": self.capital,
            "price": current_price,
            "in_position": self.position is not None,
        }

        self.equity_curve.append(equity_entry)

    def _calculate_results(self) -> Dict[str, Any]:
        """Calculate performance metrics."""
        if not self.trades:
            logger.warning("No trades were executed")
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0,
                "initial_capital": self.initial_capital,
                "final_available_balance": self.capital,
                "final_total_equity": self.capital,
                "total_return_percent": (self.capital / self.initial_capital - 1) * 100,
                "total_net_pnl": 0,
                "total_gross_pnl": 0,
                "total_commission": 0,
                "avg_net_pnl": 0,
                "avg_bars_held": 0,
                "profit_factor": 0,
                "max_drawdown_percent": 0,
                "trades": self.trades,
                "journal": self.journal,
                "equity_curve": self.equity_curve,
                "data": self.data,
                "message": "No trades executed",
            }

        total_trades = len(self.trades)
        winning_trades = sum(1 for t in self.trades if t["net_pnl"] > 0)
        losing_trades = total_trades - winning_trades

        total_net_pnl = sum(t["net_pnl"] for t in self.trades)
        total_gross_pnl = sum(t["gross_pnl"] for t in self.trades)
        total_commission = sum(
            t["commission_entry"] + t.get("commission_exit", 0) for t in self.trades
        )

        final_equity = (
            self.equity_curve[-1]["equity"] if self.equity_curve else self.capital
        )
        total_return = (final_equity / self.initial_capital - 1) * 100

        avg_net_pnl = total_net_pnl / total_trades if total_trades > 0 else 0
        avg_bars_held = (
            sum(t["bars_held"] for t in self.trades) / total_trades
            if total_trades > 0
            else 0
        )
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        gross_profits = sum(t["gross_pnl"] for t in self.trades if t["gross_pnl"] > 0)
        gross_losses = abs(
            sum(t["gross_pnl"] for t in self.trades if t["gross_pnl"] < 0)
        )
        profit_factor = (
            gross_profits / gross_losses if gross_losses > 0 else float("inf")
        )

        equity_values = [e["equity"] for e in self.equity_curve]
        if equity_values:
            running_max = np.maximum.accumulate(equity_values)
            drawdowns = (equity_values - running_max) / running_max * 100
            max_drawdown = abs(min(drawdowns)) if len(drawdowns) > 0 else 0
        else:
            max_drawdown = 0

        results = {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "initial_capital": self.initial_capital,
            "final_available_balance": self.capital,
            "final_total_equity": final_equity,
            "total_return_percent": total_return,
            "total_net_pnl": total_net_pnl,
            "total_gross_pnl": total_gross_pnl,
            "total_commission": total_commission,
            "avg_net_pnl": avg_net_pnl,
            "avg_bars_held": avg_bars_held,
            "profit_factor": profit_factor,
            "max_drawdown_percent": max_drawdown,
            "sharpe_ratio": 0,
            "sortino_ratio": 0,
            "trades": self.trades,
            "journal": self.journal,
            "equity_curve": self.equity_curve,
            "risk_manager": self.risk_manager.name,
            "data": self.data,
        }

        return results

    def print_summary(self, results: Dict[str, Any]):
        """Print backtest summary to console."""
        print("\n" + "=" * 60)
        print("BACKTEST SUMMARY")
        print("=" * 60)

        if "message" in results:
            print(f"\n{results['message']}")
            return

        print(f"\n📈 Performance:")
        print(f"  Initial Capital:        ${results['initial_capital']:,.2f}")
        print(f"  Final Total Equity:     ${results['final_total_equity']:,.2f}")
        print(f"  Total Return:           {results['total_return_percent']:+.2f}%")
        print(f"  Max Drawdown:           {results['max_drawdown_percent']:.2f}%")

        print(f"\n📊 Trade Statistics:")
        print(f"  Total Trades:    {results['total_trades']}")
        print(
            f"  Winning Trades:  {results['winning_trades']} ({results['win_rate']:.1f}%)"
        )
        print(f"  Profit Factor:   {results['profit_factor']:.2f}")

        print("=" * 60)
