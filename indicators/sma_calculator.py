import pandas as pd
import numpy as np
from .base_calculator import BaseCalculator
import logging
from typing import Dict, Any  # Aggiungi questa riga

logger = logging.getLogger(__name__)


class SMACalculator(BaseCalculator):
    """
    Simple Moving Average calculator.
    
    Parameters:
        period: Number of periods for the moving average (default: 20)
    """
    
    def calculate(self, data: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
        """
        Calculate Simple Moving Average.
        
        Args:
            data: DataFrame with OHLCV data
            params: Must contain 'period' (int)
            
        Returns:
            Series with SMA values
        """
        # Get parameters
        period = params.get('period', 20)
        price_column = params.get('column', 'close')
        
        if period <= 0:
            raise ValueError(f"Invalid period for SMA: {period}")
        
        if price_column not in data.columns:
            raise ValueError(f"Price column '{price_column}' not found in data. Available: {list(data.columns)}")
        
        logger.debug(f"Calculating SMA({period}) on {price_column} for {self.symbol} {self.timeframe}")
        
        # Calculate SMA
        sma_values = data[price_column].rolling(window=period, min_periods=1).mean()
        
        # For the first period-1 values, we could use expanding mean or leave NaN
        # Let's use expanding mean to avoid NaN values
        if period > 1:
            # Fill first period-1 values with expanding mean
            sma_values.iloc[:period-1] = data[price_column].expanding(min_periods=1).mean().iloc[:period-1]
        
        return sma_values
    
    def get_required_columns(self) -> list:
        """Return list of required columns from input data."""
        return ['close']  # Default, can be overridden by params['column']