from .base_exit import BaseExitStrategy
import logging
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)


class FixedTPSL(BaseExitStrategy):
    """
    Exit with fixed Take Profit and Stop Loss levels.
    
    Parameters:
        tp_percent: Take profit percentage (e.g., 0.05 for 5%)
        sl_percent: Stop loss percentage (e.g., 0.02 for 2%)
    """
    
    def __init__(self, params: dict = None):
        super().__init__(params)
        
        # Extract parameters with defaults
        self.tp_percent = self.params.get('tp_percent', 0.05)  # 5%
        self.sl_percent = self.params.get('sl_percent', 0.02)  # 2%
        
        logger.info(f"Initialized FixedTPSL: TP={self.tp_percent*100:.1f}%, SL={self.sl_percent*100:.1f}%")
    
    def should_exit(self, data, entry_price: float, entry_time, position_info: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Check for Take Profit or Stop Loss conditions.
        
        Args:
            data: DataWindow object
            entry_price: Price at which we entered
            entry_time: Entry timestamp
            position_info: Position information including 'position_type'
        
        Returns:
            (True, 'TAKE_PROFIT') if TP hit, (True, 'STOP_LOSS') if SL hit, (False, None) otherwise
        """
        try:
            position_type = position_info.get('position_type', 'long')
            current_price = data['close'][0]
            
            # Calculate profit/loss percentage
            if position_type == 'long':
                pnl_pct = (current_price / entry_price) - 1
            elif position_type == 'short':
                pnl_pct = (entry_price / current_price) - 1
            else:
                logger.warning(f"Unknown position type: {position_type}")
                return False, None
            
            # Check Take Profit
            if pnl_pct >= self.tp_percent:
                logger.debug(f"Take Profit hit: {pnl_pct*100:.2f}% >= {self.tp_percent*100:.1f}%")
                return True, 'TAKE_PROFIT'
            
            # Check Stop Loss
            if pnl_pct <= -self.sl_percent:
                logger.debug(f"Stop Loss hit: {pnl_pct*100:.2f}% <= -{self.sl_percent*100:.1f}%")
                return True, 'STOP_LOSS'
            
            return False, None
            
        except Exception as e:
            logger.warning(f"Error in FixedTPSL.should_exit: {e}")
            return False, None