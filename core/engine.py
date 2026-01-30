# core/engine.py

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
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
    Supports LONG and SHORT positions.

    BALANCE TRACKING:
    - available_balance: Cash available for new trades (excluding margin/collateral)
    - margin_used: Amount locked as collateral for SHORT positions
    - total_equity: available_balance + position_value
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
        """Factory method to create engine from config.yaml"""
        backtest_config = config.get("backtest", {})

        initial_capital = backtest_config.get("capital", {}).get("initial", 10000)
        commission = backtest_config.get("costs", {}).get("commission", 0.001)
        lookback_window = backtest_config.get("execution", {}).get(
            "lookback_window", 100
        )

        trading_config = config.get("strategy", {}).get("trading", {})
        allow_long = trading_config.get("allow_long", True)
        allow_short = trading_config.get("allow_short", False)
        allow_reversal = trading_config.get("allow_reversal", False)

        logger.info("Creating BacktestEngine from config:")
        logger.info(f"  Initial Capital: ${initial_capital:,.2f}")
        logger.info(f"  Commission: {commission*100:.3f}%")
        logger.info(f"  Lookback Window: {lookback_window} bars")
        logger.info(f"  Trading: LONG={allow_long}, SHORT={allow_short}")
        logger.info(f"  Reversal: {allow_reversal}")

        return cls(
            data=data,
            entry_strategy=entry_strategy,
            exit_strategy=exit_strategy,
            risk_manager=risk_manager,
            initial_capital=initial_capital,
            commission=commission,
            lookback_window=lookback_window,
            allow_long=allow_long,
            allow_short=allow_short,
            allow_reversal=allow_reversal,
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
        allow_long: bool = True,
        allow_short: bool = False,
        allow_reversal: bool = False,
    ):
        """Initialize backtesting engine."""
        self.data = data
        self.entry_strategy = entry_strategy
        self.exit_strategy = exit_strategy
        self.risk_manager = risk_manager
        self.initial_capital = initial_capital
        self.commission = commission
        self.lookback_window = lookback_window

        self.allow_long = allow_long
        self.allow_short = allow_short
        self.allow_reversal = allow_reversal

        if not allow_long and not allow_short:
            raise ValueError(
                "At least one trading direction (LONG or SHORT) must be enabled!"
            )

        self.capital = initial_capital
        self.margin_used = 0  # ✅ NEW: Track margin for SHORT positions
        self.position = None
        self.trades = []
        self.journal = []
        self.equity_curve = []

        logger.info(f"Initialized BacktestEngine")
        logger.info(f"  Initial capital: ${initial_capital:,.2f}")
        logger.info(f"  Commission: {commission*100:.2f}%")
        logger.info(f"  Lookback window: {lookback_window} candles")
        logger.info(f"  Entry strategy: {entry_strategy}")
        logger.info(f"  Exit strategy: {exit_strategy}")
        logger.info(f"  Risk manager: {self.risk_manager.name}")
        logger.info(f"  Trading directions: LONG={allow_long}, SHORT={allow_short}")
        logger.info(f"  Position reversal: {allow_reversal}")

    def run(self) -> Dict[str, Any]:
        """Run the backtest."""
        logger.info(f"Starting backtest on {len(self.data)} candles...")

        total_candles = len(self.data)
        start_index = min(self.lookback_window, max(1, total_candles - 1))

        if start_index >= total_candles:
            raise ValueError(
                f"Not enough data for backtest!\n"
                f"  Lookback window: {self.lookback_window}\n"
                f"  Total candles: {total_candles}\n"
                f"  Need at least {self.lookback_window + 1} candles"
            )

        logger.info(
            f"Starting backtest from candle {start_index}/{total_candles} "
            f"(lookback: {self.lookback_window})"
        )

        for i in range(start_index, total_candles):
            data_window = DataWindow(self.data, i, self.lookback_window)
            current_time = data_window.get_timestamp()
            current_price = data_window["close"][0]

            if not self.risk_manager.can_trade(self.capital, 0, None):
                self._update_journal(i, data_window)
                self._update_equity(i, current_price)
                continue

            self._update_journal(i, data_window)

            if self.position is None:
                entry_signal = self.entry_strategy.should_enter(data_window)

                if entry_signal:
                    if isinstance(entry_signal, dict):
                        direction = entry_signal.get("direction", "LONG")
                    else:
                        direction = "LONG"

                    if (direction == "LONG" and self.allow_long) or (
                        direction == "SHORT" and self.allow_short
                    ):
                        self._enter_position(i, data_window, direction)
                    else:
                        logger.debug(
                            f"Skipping {direction} entry at {current_time} "
                            f"(direction not enabled)"
                        )

            else:
                current_position_type = self.position["position_type"]

                if self.allow_reversal:
                    entry_signal = self.entry_strategy.should_enter(data_window)

                    if entry_signal:
                        if isinstance(entry_signal, dict):
                            new_direction = entry_signal.get("direction", "LONG")
                        else:
                            new_direction = "LONG"

                        is_opposite = (
                            current_position_type == "long" and new_direction == "SHORT"
                        ) or (
                            current_position_type == "short" and new_direction == "LONG"
                        )

                        if is_opposite:
                            logger.info(
                                f"🔄 REVERSAL SIGNAL: {current_position_type.upper()} → {new_direction}"
                            )
                            self._reverse_position(i, data_window, new_direction)
                            self._update_equity(i, current_price)
                            continue

                # ✅ MODIFICATO: Ora should_exit restituisce 4 valori
                should_exit, exit_reason, tp_level, sl_level = (
                    self.exit_strategy.should_exit(
                        data_window,
                        self.position["entry_price"],
                        self.position["entry_time"],
                        {**self.position, "current_index": i},
                    )
                )

                if should_exit:
                    # ✅ NUOVO: Aggiorna TP/SL nel trade corrente prima di uscire
                    if self.trades:
                        self.trades[-1].update(
                            {
                                "take_profit": tp_level,
                                "stop_loss": sl_level,
                            }
                        )
                    self._exit_position(i, data_window, exit_reason)

            self._update_equity(i, current_price)

            if i % 1440 == 0:
                logger.info(f"Processed {i:,}/{total_candles:,} candles")

        if self.position is not None:
            last_idx = total_candles - 1
            last_data = DataWindow(self.data, last_idx, self.lookback_window)
            # ✅ NUOVO: Ottieni TP/SL finali
            should_exit, exit_reason, tp_level, sl_level = (
                self.exit_strategy.should_exit(
                    last_data,
                    self.position["entry_price"],
                    self.position["entry_time"],
                    {**self.position, "current_index": last_idx},
                )
            )
            # Aggiorna TP/SL nel trade
            if self.trades:
                self.trades[-1].update(
                    {
                        "take_profit": tp_level,
                        "stop_loss": sl_level,
                    }
                )
            self._exit_position(last_idx, last_data, "END_OF_DATA")

        logger.info(f"Backtest completed. Executed {len(self.trades)} trades.")

        results = self._calculate_results()

        # ✅ New -> TP SL data
        self._enhance_results_with_tp_sl_data(results)

        return results

    def _enhance_results_with_tp_sl_data(self, results: Dict[str, Any]):
        """
        Enhance results with TP/SL data for plotting.

        Crea un DataFrame con tutte le candele e aggiunge colonne per TP/SL
        basate sui dati del journal.
        """
        try:
            if not self.journal:
                logger.warning("No journal data available for TP/SL enhancement")
                return

            # Crea DataFrame dal journal
            journal_df = pd.DataFrame(self.journal)

            # Crea Series per TP/SL
            tp_series = pd.Series(
                journal_df["take_profit"].values, index=journal_df["timestamp"]
            )

            sl_series = pd.Series(
                journal_df["stop_loss"].values, index=journal_df["timestamp"]
            )

            # Crea una copia del data originale con indicatori
            enhanced_data = self.data.copy()

            # Aggiungi colonne TP/SL al DataFrame principale
            # Nota: potrebbero esserci timestamp mancanti, quindi usiamo reindex
            enhanced_data["take_profit"] = tp_series.reindex(enhanced_data.index)
            enhanced_data["stop_loss"] = sl_series.reindex(enhanced_data.index)

            # Aggiungi altre informazioni utili dal journal
            enhanced_data["in_position"] = pd.Series(
                journal_df["in_position"].values, index=journal_df["timestamp"]
            ).reindex(enhanced_data.index)

            enhanced_data["position_type"] = pd.Series(
                [
                    j.get("position_type") if j.get("in_position") else None
                    for j in self.journal
                ],
                index=journal_df["timestamp"],
            ).reindex(enhanced_data.index)

            # Salva nel risultato
            results["data_with_indicators"] = enhanced_data

            logger.info(
                f"Enhanced data with TP/SL columns. Shape: {enhanced_data.shape}"
            )
            logger.info(
                f"Columns added: {[c for c in enhanced_data.columns if 'take' in c or 'stop' in c or 'position' in c]}"
            )

            # Log di esempio per debug
            if not enhanced_data["take_profit"].isna().all():
                tp_count = enhanced_data["take_profit"].notna().sum()
                logger.info(f"TP values available for {tp_count} candles")

                # Mostra alcuni valori di esempio
                sample_tp = enhanced_data["take_profit"].dropna().head(3)
                if len(sample_tp) > 0:
                    logger.info(f"Sample TP values:\n{sample_tp}")

        except Exception as e:
            logger.error(f"Error enhancing results with TP/SL data: {e}")
            # Fallback: usa il data originale senza TP/SL
            results["data_with_indicators"] = self.data

    def _enter_position(
        self, index: int, data_window: DataWindow, direction: str = "LONG"
    ):
        """
        Enter a new position with risk management.

        BALANCE TRACKING:
        - LONG: capital -= (position_value + commission)
        - SHORT: capital -= (margin_used + commission), margin_used = position_value
        """
        entry_price = data_window["close"][0]
        entry_time = data_window.get_timestamp()

        initial_tp = None
        initial_sl = None

        try:
            # Chiama should_exit solo per ottenere i livelli (senza exit check)
            _, _, tp_level, sl_level = self.exit_strategy.should_exit(
                data_window,
                entry_price,
                entry_time,
                {"position_type": direction.lower()},
            )
            initial_tp = tp_level
            initial_sl = sl_level
        except Exception as e:
            logger.warning(f"Could not calculate initial TP/SL: {e}")

        if not self.risk_manager.can_trade(self.capital, 0, None):
            logger.warning(f"Risk manager blocked entry at {entry_time}")
            return

        stop_loss_price = None

        if hasattr(self.exit_strategy, "sl_percent"):
            if direction == "LONG":
                stop_loss_price = entry_price * (1 - self.exit_strategy.sl_percent)
            else:
                stop_loss_price = entry_price * (1 + self.exit_strategy.sl_percent)

        risk_amount = self.risk_manager.calculate_position_size(
            capital=self.capital,
            entry_price=entry_price,
            stop_loss_price=stop_loss_price,
            direction=direction,
            volatility=None,
        )

        quantity = risk_amount / entry_price
        position_value = risk_amount

        if position_value > self.capital:
            logger.warning(
                f"Insufficient capital: needed ${position_value:.2f}, "
                f"have ${self.capital:.2f}"
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
            "position_type": direction.lower(),
            "commission_paid": commission_paid,
            "total_equity_before_entry": total_equity_before,
            "position_value_entry": position_value,
            "available_balance_before": self.capital,
            "risk_amount": risk_amount,
            "take_profit": initial_tp,
            "stop_loss": initial_sl,
        }

        # ✅ IMPROVED: Clearer balance tracking
        if direction == "LONG":
            # LONG: Pay for asset + commission
            self.capital -= position_value + commission_paid
            self.margin_used = 0
            total_equity_after = self.capital + position_value

        else:  # SHORT
            # SHORT: Lock margin as collateral + pay commission
            # Margin = amount we need to buy back the borrowed asset
            self.margin_used = position_value
            self.capital -= (
                commission_paid  # Only pay commission from available balance
            )
            total_equity_after = self.capital  # Equity stays same (we have debt)

        # ✅ IMPROVED: Calculate truly available balance
        available_for_new_trades = self.capital - self.margin_used

        direction_emoji = "📈" if direction == "LONG" else "📉"

        logger.info(
            f"{direction_emoji} ENTRY {direction} at {entry_time} | "
            f"Price: ${entry_price:.4f} | "
            f"Quantity: {quantity:.6f} | "
            f"Position Value: ${position_value:.2f} | "
            f"Cash Balance: ${self.capital:.2f} | "
            f"Margin Used: ${self.margin_used:.2f} | "
            f"Available for New Trades: ${available_for_new_trades:.2f} | "
            f"Total Equity: ${total_equity_after:.2f} | "
            f"Commission: ${commission_paid:.2f}"
        )

        trade = {
            "entry_index": index,
            "entry_time": entry_time,
            "entry_price": entry_price,
            "position_size": quantity,
            "position_type": direction.lower(),
            "position_value": position_value,
            "commission_entry": commission_paid,
            "total_equity_before": total_equity_before,
            "cash_balance_after_entry": self.capital,  # ✅ RENAMED for clarity
            "margin_used": self.margin_used,  # ✅ NEW
            "available_for_new_trades": available_for_new_trades,  # ✅ NEW
            "total_equity_after_entry": total_equity_after,
            "risk_amount": risk_amount,
            "take_profit": initial_tp,
            "stop_loss": initial_sl,
        }
        self.trades.append(trade)

    def _exit_position(self, index: int, data_window: DataWindow, reason: str):
        """
        Exit current position.

        BALANCE TRACKING:
        - LONG: capital += (exit_value - commission)
        - SHORT: capital += (margin_used - exit_value - commission), margin_used = 0
        """
        exit_price = data_window["close"][0]
        exit_time = data_window.get_timestamp()

        if self.position is None:
            logger.warning("Attempted to exit but no position is open")
            return

        entry_price = self.position["entry_price"]
        position_size = self.position["position_size"]
        position_type = self.position["position_type"]
        entry_time = self.position["entry_time"]
        entry_index = self.position["entry_index"]

        exit_value = position_size * exit_price
        commission_paid = exit_value * self.commission

        # ✅ IMPROVED: Different cash flow for LONG vs SHORT
        if position_type == "long":
            # LONG: Sell asset, receive cash minus commission
            gross_pnl = exit_value - (position_size * entry_price)
            self.capital += exit_value - commission_paid

        else:  # SHORT
            # SHORT: Buy back borrowed asset, release margin
            entry_value = position_size * entry_price
            gross_pnl = entry_value - exit_value

            # Return margin minus cost to buy back asset and commission
            self.capital += self.margin_used - exit_value - commission_paid
            self.margin_used = 0  # Release margin

        net_pnl = gross_pnl - self.position["commission_paid"] - commission_paid
        net_pnl_percent = (net_pnl / self.position["position_value_entry"]) * 100

        bars_held = index - entry_index

        direction_emoji = "✅" if net_pnl > 0 else "❌"
        logger.info(
            f"{direction_emoji} EXIT {position_type.upper()} at {exit_time} | "
            f"Price: ${exit_price:.4f} | "
            f"P&L: ${net_pnl:+.2f} ({net_pnl_percent:+.2f}%) | "
            f"Reason: {reason} | "
            f"Held: {bars_held} bars | "
            f"New Balance: ${self.capital:.2f}"
        )

        if self.trades:
            self.trades[-1].update(
                {
                    "exit_index": index,
                    "exit_time": exit_time,
                    "exit_price": exit_price,
                    "exit_value": exit_value,
                    "gross_pnl": gross_pnl,
                    "commission_exit": commission_paid,
                    "total_commission": self.position["commission_paid"]
                    + commission_paid,
                    "net_pnl": net_pnl,
                    "net_pnl_percent": net_pnl_percent,
                    "bars_held": bars_held,
                    "exit_reason": reason,
                    "cash_balance_after_exit": self.capital,  # ✅ RENAMED
                    "margin_after_exit": self.margin_used,  # ✅ NEW
                }
            )

        self.position = None

    def _reverse_position(
        self, index: int, data_window: DataWindow, new_direction: str
    ):
        """Reverse position from LONG to SHORT or vice versa."""
        if self.position is None:
            logger.warning("Cannot reverse position - no position open")
            return

        current_type = self.position["position_type"]
        logger.info(f"🔄 Reversing position: {current_type.upper()} → {new_direction}")

        self._exit_position(index, data_window, f"REVERSAL_TO_{new_direction}")
        self._enter_position(index, data_window, new_direction)

    def _update_journal(self, index: int, data_window: DataWindow):
        """Update journal with current state INCLUDING TP/SL levels."""
        current_price = data_window["close"][0]
        current_time = data_window.get_timestamp()

        journal_entry = {
            "index": index,
            "timestamp": current_time,
            "price": current_price,
            "in_position": self.position is not None,
            "available_balance": self.capital,
            "margin_used": self.margin_used,
            "total_equity": self.capital,  # sarà aggiornato se in posizione
            "position_size": None,
            "entry_price": None,
            "position_value": None,
            "unrealized_pnl": None,
            "unrealized_pnl_percent": None,
            "take_profit": None,
            "stop_loss": None,
            "position_type": None,
        }

        if self.position:
            entry_price = self.position["entry_price"]
            position_size = self.position["position_size"]
            position_type = self.position["position_type"]

            if position_type == "long":
                position_value = position_size * current_price
                unrealized_pnl = position_value - (position_size * entry_price)
                unrealized_pnl_percent = (current_price / entry_price - 1) * 100
            else:  # SHORT
                position_value = -(position_size * current_price)
                unrealized_pnl = (entry_price - current_price) * position_size
                unrealized_pnl_percent = (1 - current_price / entry_price) * 100

            total_equity = self.capital + position_value

            # ✅ New: Get current TP/SL levels from exit strategy
            try:
                _, _, tp_level, sl_level = self.exit_strategy.should_exit(
                    data_window,
                    entry_price,
                    self.position["entry_time"],
                    {**self.position, "current_index": index},
                )
                journal_entry["take_profit"] = (
                    float(tp_level) if tp_level is not None else None
                )
                journal_entry["stop_loss"] = (
                    float(sl_level) if sl_level is not None else None
                )
            except Exception as e:
                logger.debug(f"Could not get TP/SL levels: {e}")

            journal_entry.update(
                {
                    "position_size": float(position_size),
                    "entry_price": float(entry_price),
                    "position_value": float(position_value),
                    "unrealized_pnl": float(unrealized_pnl),
                    "unrealized_pnl_percent": float(unrealized_pnl_percent),
                    "total_equity": float(total_equity),
                    "position_type": position_type,
                }
            )

        self.journal.append(journal_entry)

    def _update_equity(self, index: int, current_price: float):
        """
        Update equity curve considering position direction.

        For LONG: position_value is positive (we own the asset)
        For SHORT: position_value is negative (we owe the asset - it's a liability)
        """
        if self.position is None:
            equity = self.capital
        else:
            position_type = self.position["position_type"]
            position_size = self.position["position_size"]

            if position_type == "long":
                # LONG: We own the asset (positive value)
                position_market_value = position_size * current_price
            else:  # SHORT
                # SHORT: We owe the asset (negative value = liability)
                # capital already includes the sale proceeds
                # position_market_value (negative) represents what we owe
                position_market_value = -(position_size * current_price)

            equity = self.capital + position_market_value

        equity_entry = {
            "index": index,
            "equity": equity,
            "available_balance": self.capital,
            "margin_used": self.margin_used,
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

        reversal_trades = sum(
            1 for t in self.trades if "REVERSAL" in t.get("exit_reason", "")
        )
        reversal_pnl = sum(
            t["net_pnl"] for t in self.trades if "REVERSAL" in t.get("exit_reason", "")
        )

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

        # ✅ IMPORTANT: Max Drawdown calculation
        # This measures the largest peak-to-trough decline in equity
        # It's NOT limited by risk per trade -> Consecutive losses accumulate!
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
            "reversal_trades": reversal_trades,
            "reversal_pnl": reversal_pnl,
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

        print(f"\n📄 Backtest period")
        print(f"  Start Date:             {self.data.index[0]}")
        print(f"  End Date:               {self.data.index[-1]}")
        print(f"  Duration:               {self.data.index[-1] - self.data.index[0]}")

        print(f"\n📊 Trade Statistics:")
        print(f"  Total Trades:    {results['total_trades']}")
        print(
            f"  Winning Trades:  {results['winning_trades']} ({results['win_rate']:.1f}%)"
        )
        print(f"  Profit Factor:   {results['profit_factor']:.2f}")

        if results.get("reversal_trades", 0) > 0:
            print(f"\n🔄 Reversal Statistics:")
            print(f"  Reversal Trades: {results['reversal_trades']}")
            print(f"  Reversal P&L:    ${results['reversal_pnl']:+.2f}")

        print("=" * 60)
