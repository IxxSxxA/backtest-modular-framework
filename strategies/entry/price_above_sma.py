from .base_entry import BaseEntryStrategy
import logging

logger = logging.getLogger(__name__)


class PriceAboveSMA(BaseEntryStrategy):
    """
    Simple entry strategy: Enter when price closes above SMA.
    
    Parameters:
        sma_period: Period for SMA calculation (default: 20)
        lookback: Number of previous candles to check (default: 1)
    """
    
    def __init__(self, params: dict = None):
        super().__init__(params)
        
        # Extract parameters with defaults
        self.sma_period = self.params.get('period', 20)
        self.lookback = self.params.get('lookback', 1)
        self.sma_column = f"sma_{self.sma_period}"
        
        logger.info(f"Initialized PriceAboveSMA: period={self.sma_period}, lookback={self.lookback}")
    
    def should_enter(self, data) -> bool:
        """
        Check if current close price is above SMA.
        
        Args:
            data: DataWindow object
            
        Returns:
            True if close > SMA for lookback candles
        """
        # Check if we have required indicators
        if self.sma_column not in data:
            logger.error(f"Required indicator '{self.sma_column}' not found in data")
            return False
        
        try:
            # Get current and previous values
            current_close = data['close'][0]
            current_sma = data[self.sma_column][0]
            
            # Simple condition: price above SMA
            if current_close > current_sma:
                # Optional: Check that price was below SMA in previous candle
                if self.lookback > 0:
                    for i in range(1, self.lookback + 1):
                        prev_close = data['close'][-i]
                        prev_sma = data[self.sma_column][-i]
                        
                        if prev_close > prev_sma:
                            # Price was already above SMA, not a fresh crossover
                            return False
                
                logger.debug(f"Entry signal: {current_close:.2f} > {current_sma:.2f}")
                return True
            
            return False
            
        except (IndexError, KeyError) as e:
            logger.warning(f"Data access error in should_enter: {e}")
            return False
    
    def get_required_indicators(self) -> list:
        """
        Return required indicator names.
        """
        return [self.sma_column]