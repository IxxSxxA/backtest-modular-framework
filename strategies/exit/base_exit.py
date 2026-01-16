from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional
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
            params: Dictionary of strategy parameters
        """
        self.params = params or {}
        self.name = self.__class__.__name__
        
        logger.debug(f"Initialized {self.name} with params: {self.params}")
    
    @abstractmethod
    def should_exit(self, data, entry_price: float, entry_time, position_info: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
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
    
    def get_required_indicators(self) -> list:
        """
        Get list of indicator names required by this strategy.
        
        Returns:
            List of indicator column names
        """
        return []
    
    def __str__(self):
        return f"{self.name}({self.params})"