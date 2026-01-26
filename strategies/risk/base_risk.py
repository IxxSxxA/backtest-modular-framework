"""
Base class for risk management.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class BaseRiskManager(ABC):
    """
    Template for risk management and position sizing.

    Determines HOW MUCH to risk per trade.
    """

    def __init__(self, params: Dict[str, Any] = None):
        """
        Args:
            params: Parameters from config.yaml including:
                    - Risk-specific params (risk_per_trade, max_drawdown, etc.)
                    - 'indicators': List of indicator configs needed (optional)
        """
        self.params = params or {}
        self.name = self.__class__.__name__

        # NEW: Extract indicator declarations from params (usually empty for risk managers)
        self.indicators = self.params.get("indicators", [])

        logger.debug(f"Initialized {self.name} with params: {self.params}")
        if self.indicators:
            logger.debug(f"  Requires {len(self.indicators)} indicators")

    @abstractmethod
    def calculate_position_size(
        self,
        capital: float,
        entry_price: float,
        stop_loss_price: Optional[float] = None,
        direction: str = "LONG",
        volatility: Optional[float] = None,
    ) -> float:
        """
        Calculate position size.

        Args:
            capital: Available capital
            entry_price: Proposed entry price
            stop_loss_price: Stop loss price (if available)
            direction: "LONG" or "SHORT"
            volatility: Current volatility (e.g., ATR)

        Returns:
            Amount to risk (monetary value, e.g., $500)
        """
        raise NotImplementedError(
            f"Risk manager {self.__class__.__name__} must implement calculate_position_size()"
        )

    def can_trade(
        self,
        capital: float,
        current_drawdown: float,
        market_conditions: Optional[Dict] = None,
    ) -> bool:
        """
        (Optional) Determine if new trades are allowed.

        Args:
            capital: Current capital
            current_drawdown: Current drawdown as percentage
            market_conditions: Optional market conditions dict

        Returns:
            True if new trades can be opened
        """
        # Example: block trading if drawdown > 10%
        if current_drawdown > 0.10:
            logger.warning(f"Trading blocked: drawdown {current_drawdown:.1%} > 10%")
            return False

        return True

    def adjust_for_volatility(
        self, base_position_size: float, volatility: float, avg_volatility: float
    ) -> float:
        """
        (Optional) Adjust position size based on volatility.

        Example: reduce position size if volatility is high.
        """
        if volatility and avg_volatility:
            volatility_ratio = volatility / avg_volatility
            # If volatility is 2x the average, reduce position size by 50%
            if volatility_ratio > 2.0:
                return base_position_size * 0.5

        return base_position_size

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
