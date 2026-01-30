# strategies/exit/atr_based_exit.py

from .base_exit import BaseExitStrategy
import logging
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)


class ATRBasedExit(BaseExitStrategy):
    """
    Exit strategy based on ATR multiples for take profit and stop loss.

    Config example:
    ```yaml
    exit:
      name: "atr_based_exit"
      params:
        tp_multiplier: 9.0
        sl_multiplier: 5.5
        dynamic: true  # true=TP/SL si aggiornano ogni candela, false=fissi all'entry
    ```
    """

    def __init__(self, params: dict = None):
        super().__init__(params)

        # Extract parameters
        self.tp_multiplier = float(self.params.get("tp_multiplier", 9.0))
        self.sl_multiplier = float(self.params.get("sl_multiplier", 5.5))
        self.dynamic = bool(self.params.get("dynamic", True))  # Default: dynamic

        # Cache per livelli fissi (se dynamic=False)
        self.fixed_levels_cache = {}  # (entry_time, position_type) -> (tp, sl)

        # ATR column name
        self.atr_column = None
        for ind in self.indicators:
            if ind["name"] == "atr":
                period = ind.get("period", 14)
                method = ind.get("method", "wilder")
                self.atr_column = (
                    f"atr_{period}" if method == "wilder" else f"atr_{period}_{method}"
                )
                break

        if not self.atr_column:
            raise ValueError(f"{self.name} requires 'atr' indicator!")

        logger.info(
            f"Initialized ATRBasedExit: TP={self.tp_multiplier}x, SL={self.sl_multiplier}x, "
            f"Dynamic={self.dynamic}, Column={self.atr_column}"
        )

    def _calculate_tp_sl(
        self, entry_price: float, atr_value: float, position_type: str
    ) -> tuple:
        """Calculate TP/SL levels given current ATR."""
        if position_type == "long":
            tp = entry_price + (atr_value * self.tp_multiplier)
            sl = entry_price - (atr_value * self.sl_multiplier)
        else:  # short
            tp = entry_price - (atr_value * self.tp_multiplier)
            sl = entry_price + (atr_value * self.sl_multiplier)
        return tp, sl

    def should_exit(
        self, data, entry_price: float, entry_time, position_info: Dict[str, Any]
    ) -> Tuple[bool, Optional[str], Optional[float], Optional[float]]:
        """
        Check exit conditions.

        Returns:
            (should_exit: bool, reason: str, tp_level: float, sl_level: float)
        """
        try:
            if self.atr_column not in data:
                logger.error(f"ATR column '{self.atr_column}' not found")
                return False, None, None, None

            current_atr = data[self.atr_column][0]
            current_price = data["close"][0]
            position_type = position_info.get("position_type", "long")

            # Calculate TP/SL levels
            if not self.dynamic:
                # Modalità FISSA: usa l'ATR dell'entry, memorizza in cache
                cache_key = (entry_time, position_type)
                if cache_key not in self.fixed_levels_cache:
                    # Prima volta: calcola con ATR dell'entry
                    tp, sl = self._calculate_tp_sl(
                        entry_price, current_atr, position_type
                    )
                    self.fixed_levels_cache[cache_key] = (tp, sl)

                tp_level, sl_level = self.fixed_levels_cache[cache_key]
            else:
                # Modalità DINAMICA: ricalcola ogni candela
                tp_level, sl_level = self._calculate_tp_sl(
                    entry_price, current_atr, position_type
                )

            # Check exit conditions
            if position_type == "long":
                if current_price >= tp_level:
                    return True, "TAKE_PROFIT", tp_level, sl_level
                elif current_price <= sl_level:
                    return True, "STOP_LOSS", tp_level, sl_level
            else:  # short
                if current_price <= tp_level:
                    return True, "TAKE_PROFIT", tp_level, sl_level
                elif current_price >= sl_level:
                    return True, "STOP_LOSS", tp_level, sl_level

            return False, None, tp_level, sl_level

        except Exception as e:
            logger.error(f"Error in should_exit: {e}")
            return False, None, None, None
