from abc import ABC, abstractmethod
from typing import Dict, Any
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
            params: Dictionary of strategy parameters
        """
        self.params = params or {}
        self.name = self.__class__.__name__
        
        logger.debug(f"Initialized {self.name} with params: {self.params}")
    
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
    
    def get_required_indicators(self) -> list:
        """
        Get list of indicator names required by this strategy.
        
        Returns:
            List of indicator column names (e.g., ['sma_20', 'rsi_14'])
        """
        return []
    
    def __str__(self):
        return f"{self.name}({self.params})"