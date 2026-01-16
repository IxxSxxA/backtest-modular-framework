from .base_exit import BaseExitStrategy
import logging
from typing import Dict, Any, Tuple, Optional
import pandas as pd

logger = logging.getLogger(__name__)


class HoldBars(BaseExitStrategy):
    """
    Simple exit strategy: Exit after holding for a fixed number of bars.
    
    Parameters:
        bars: Number of bars to hold before exiting (default: 10)
    """
    
    def __init__(self, params: dict = None):
        super().__init__(params)
        
        # Extract parameters with defaults
        self.bars_to_hold = self.params.get('bars', 10)
        
        logger.info(f"Initialized HoldBars: bars={self.bars_to_hold}")
    
    def should_exit(self, data, entry_price: float, entry_time, position_info: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Exit after holding for specified number of bars.
        
        Args:
            data: DataWindow object
            entry_price: Entry price (not used in this strategy)
            entry_time: Entry timestamp
            position_info: Position information including 'entry_index'
        
        Returns:
            (True, 'TIME_EXIT') if held for enough bars, (False, None) otherwise
        """
        try:
            current_time = data.get_timestamp()
            entry_index = position_info.get('entry_index', 0)
            current_index = position_info.get('current_index', 0)
            
            # Calculate how many bars we've held
            bars_held = current_index - entry_index
            
            if bars_held >= self.bars_to_hold:
                logger.debug(f"Exit signal: Held {bars_held} bars (max: {self.bars_to_hold})")
                return True, 'TIME_EXIT'
            
            return False, None
            
        except Exception as e:
            logger.warning(f"Error in HoldBars.should_exit: {e}")
            return False, None
    
    def get_required_indicators(self) -> list:
        """
        Return required indicator names.
        """
        return []  # No indicators required for time-based exit