# strategies/exit/atr_based_exit.py

from .base_exit import BaseExitStrategy
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class ATRBasedExit(BaseExitStrategy):
    """
    Exit strategy based on ATR multiples for take profit and stop loss.

    Parameters:
        atr_period: Period for ATR calculation (default: 14)
        tp_multiplier: Take profit multiplier (default: 9.0)
        sl_multiplier: Stop loss multiplier (default: 5.5)
    """

    def __init__(self, params: dict = None):
        super().__init__(params)

        # Extract parameters
        self.atr_period = self.params.get("atr_period", 14)
        self.tp_multiplier = float(self.params.get("tp_multiplier", 9.0))
        self.sl_multiplier = float(self.params.get("sl_multiplier", 5.5))

        # Column name
        self.atr_column = f"atr_{self.atr_period}"

        logger.info(
            f"Initialized ATRBasedExit: "
            f"ATR({self.atr_period}), TP={self.tp_multiplier}x, SL={self.sl_multiplier}x"
        )

    def should_exit(
        self, data, entry_price: float, entry_time, position_info: Dict[str, Any]
    ):
        """
        Check if we should exit based on ATR multiples.

        For LONG positions:
        - Take Profit: entry_price + (ATR * tp_multiplier)
        - Stop Loss: entry_price - (ATR * sl_multiplier)
        """
        try:
            # Get current ATR value
            if self.atr_column not in data:
                logger.error(f"Required indicator '{self.atr_column}' not found")
                return False, None

            current_atr = data[self.atr_column][0]
            current_price = data["close"][0]

            # Get position type (default to 'long')
            position_type = position_info.get("position_type", "long")

            # Calculate TP and SL levels
            if position_type == "long":
                take_profit = entry_price + (current_atr * self.tp_multiplier)
                stop_loss = entry_price - (current_atr * self.sl_multiplier)

                # Check exit conditions
                if current_price >= take_profit:
                    logger.info(
                        f"Take Profit hit: {current_price:.4f} >= {take_profit:.4f} "
                        f"(ATR={current_atr:.4f}, Entry={entry_price:.4f})"
                    )
                    return True, "TAKE_PROFIT"

                elif current_price <= stop_loss:
                    logger.info(
                        f"Stop Loss hit: {current_price:.4f} <= {stop_loss:.4f} "
                        f"(ATR={current_atr:.4f}, Entry={entry_price:.4f})"
                    )
                    return True, "STOP_LOSS"

            # Future: add short position support
            elif position_type == "short":
                # Inverse logic for short positions
                take_profit = entry_price - (current_atr * self.tp_multiplier)
                stop_loss = entry_price + (current_atr * self.sl_multiplier)

                if current_price <= take_profit:
                    logger.info(f"Take Profit hit (short): {current_price:.4f}")
                    return True, "TAKE_PROFIT"

                elif current_price >= stop_loss:
                    logger.info(f"Stop Loss hit (short): {current_price:.4f}")
                    return True, "STOP_LOSS"

            return False, None

        except (IndexError, KeyError) as e:
            logger.warning(f"Data access error in should_exit: {e}")
            return False, None

    def get_required_indicators(self) -> list:
        """Return required indicator names."""
        return [self.atr_column]
