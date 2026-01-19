from .base_entry import BaseEntryStrategy
import logging

logger = logging.getLogger(__name__)


class PriceAboveSMA(BaseEntryStrategy):
    """
    Simple entry strategy: Enter when price closes above SMA.
    
    Parameters:
        sma_period: Period for SMA calculation
        lookback: Number of previous candles to check
    """
    
    def __init__(self, params: dict = None):
        super().__init__(params)
        
        # Extract parameters with defaults
        self.sma_period = self.params.get('period')
        self.lookback = self.params.get('lookback')
        self.sma_column = f"sma_{self.sma_period}"
        
        logger.info(f"Initialized PriceAboveSMA: period={self.sma_period}, lookback={self.lookback}")
    
    def should_enter(self, data) -> bool:
        # Check if we have required indicators
        if self.sma_column not in data:
            logger.error(f"Required indicator '{self.sma_column}' not found in data")
            return False
        
        try:
            current_close = data['close'][0]
            current_sma = data[self.sma_column][0]
            
            # Check crossover: current price above SMA AND previous price below SMA
            prev_close = data['close'][-1]  # Candela immediatamente precedente
            prev_sma = data[self.sma_column][-1]
            
            # Crossover detection
            if current_close > current_sma and prev_close <= prev_sma:
                logger.info(f"Entry signal: Crossover detected - {prev_close:.2f}≤{prev_sma:.2f} → {current_close:.2f}>{current_sma:.2f}")
                return True
            
            # Optional: Check for lookback confirmation
            if self.lookback > 1:
                # Verify price stayed above SMA for lookback periods
                for i in range(1, min(self.lookback, len(data))):
                    if data['close'][-i] <= data[self.sma_column][-i]:
                        return False
            
            return False
            
        except (IndexError, KeyError) as e:
            logger.warning(f"Data access error in should_enter: {e}")
            return False
    
    def get_required_indicators(self) -> list:
        """
        Return required indicator names.
        """
        return [self.sma_column]