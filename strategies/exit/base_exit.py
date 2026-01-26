from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional, List
import logging

logger = logging.getLogger(__name__)


class BaseExitStrategy(ABC):
    """
    Abstract base class for all exit strategies.
    Exit strategies decide WHEN to exit a position and WHY.
    """

    def __init__(self, params: Dict[str, Any] = None):
        """
        Initialize exit strategy.

        Args:
            params: Dictionary of strategy parameters including:
                    - Strategy-specific params (tp_multiplier, sl_multiplier, etc.)
                    - 'indicators': List of indicator configs needed by this strategy
        """
        self.params = params or {}
        self.name = self.__class__.__name__

        # NEW: Extract indicator declarations from params
        self.indicators = self.params.get("indicators", [])

        logger.debug(f"Initialized {self.name} with params: {self.params}")
        if self.indicators:
            logger.debug(f"  Requires {len(self.indicators)} indicators")

    @abstractmethod
    def should_exit(
        self, data, entry_price: float, entry_time, position_info: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Determine if we should exit a position.

        Args:
            data: DataWindow object providing access to price data and indicators
            entry_price: Price at which we entered the position
            entry_time: Timestamp when we entered
            position_info: Additional position information (e.g., position_type: 'long'/'short')

        Returns:
            Tuple of (should_exit: bool, reason: str or None)
            Reason examples: 'TAKE_PROFIT', 'STOP_LOSS', 'TRAILING_STOP', 'TIME_EXIT', 'SIGNAL_REVERSAL'
        """
        pass

    def get_required_indicators(self) -> List[str]:
        """
        DEPRECATED: Use self.indicators instead.

        Returns:
            List of indicator column names
        """
        # Generate column names from self.indicators
        if not self.indicators:
            return []

        from core.indicator_manager import IndicatorManager

        manager = IndicatorManager()

        return [manager.generate_column_name(ind) for ind in self.indicators]

    def __str__(self):
        return f"{self.name}({self.params})"
