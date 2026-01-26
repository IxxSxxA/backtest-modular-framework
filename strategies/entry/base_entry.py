from abc import ABC, abstractmethod
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class BaseEntryStrategy(ABC):
    """
    Abstract base class for all entry strategies.
    Entry strategies decide WHEN to enter a position.
    """

    def __init__(self, params: Dict[str, Any] = None):
        """
        Initialize entry strategy.

        Args:
            params: Dictionary of strategy parameters including:
                    - Strategy-specific params (thresholds, etc.)
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
    def should_enter(self, data) -> bool:
        """
        Determine if we should enter a position.

        Args:
            data: DataWindow object providing access to price data and indicators
                  with offset support (data['close'][0], data['sma_20'][-1], etc.)

        Returns:
            True if entry conditions are met, False otherwise
        """
        pass

    def get_required_indicators(self) -> List[str]:
        """
        DEPRECATED: Use self.indicators instead.

        Returns:
            List of indicator column names (e.g., ['sma_20', 'rsi_14'])
        """
        # Generate column names from self.indicators
        # This is mainly for backward compatibility
        if not self.indicators:
            return []

        from core.indicator_manager import IndicatorManager

        manager = IndicatorManager()

        return [manager.generate_column_name(ind) for ind in self.indicators]

    def __str__(self):
        return f"{self.name}({self.params})"
