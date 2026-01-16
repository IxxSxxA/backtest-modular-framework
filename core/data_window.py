import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class DataWindow:
    """
    Provides a sliding window view of data with offset access.
    Used by strategies to access current and historical data.
    
    Example:
        data['close'][0]      # Current close price
        data['close'][-1]     # Previous close price
        data['sma_20'][-5]    # SMA 5 candles ago
    """
    
    def __init__(self, data: pd.DataFrame, current_index: int, lookback: int = 100):
        """
        Initialize data window.
        
        Args:
            data: Full DataFrame with all data and indicators
            current_index: Current position in the data (0-based)
            lookback: Maximum number of historical candles to store
        """
        self.data = data
        self.current_index = current_index
        self.lookback = lookback
        
        # Ensure we don't go out of bounds
        self.start_idx = max(0, current_index - lookback)
        self.end_idx = min(len(data), current_index + 1)
        
        # Extract window slice
        self.window = data.iloc[self.start_idx:self.end_idx].copy()
        
        # Current position within window
        self.window_pos = current_index - self.start_idx
        
        logger.debug(f"DataWindow created: idx={current_index}, window={len(self.window)} rows")
    
    def __getitem__(self, key: str) -> 'DataWindowColumn':
        """
        Get access to a specific column with offset support.
        
        Args:
            key: Column name (e.g., 'close', 'sma_20')
            
        Returns:
            DataWindowColumn object that supports offset access
        """
        if key not in self.data.columns:
            raise KeyError(f"Column '{key}' not found in data. Available: {list(self.data.columns)}")
        
        return DataWindowColumn(self.window[key].values, self.window_pos)
    
    def __contains__(self, key: str) -> bool:
        """Check if column exists in data."""
        return key in self.data.columns
    
    def get_current_data(self) -> Dict[str, float]:
        """
        Get all current values as a dictionary.
        
        Returns:
            Dictionary of column_name: current_value
        """
        if self.window_pos >= len(self.window):
            return {}
        
        current_row = self.window.iloc[self.window_pos]
        return current_row.to_dict()
    
    def get_timestamp(self):
        """Get current timestamp."""
        if self.window_pos >= len(self.window):
            return None
        
        return self.window.index[self.window_pos]
    
    def move_next(self, new_index: int) -> 'DataWindow':
        """
        Create a new DataWindow for the next position.
        
        Args:
            new_index: New current index
            
        Returns:
            New DataWindow object
        """
        return DataWindow(self.data, new_index, self.lookback)
    
    def get_available_columns(self) -> list:
        """Get list of available columns."""
        return list(self.data.columns)


class DataWindowColumn:
    """
    Provides offset access to a data column.
    """
    
    def __init__(self, values: np.ndarray, current_pos: int):
        """
        Initialize column access.
        
        Args:
            values: Array of column values
            current_pos: Current position within the array (0-based)
        """
        self.values = values
        self.current_pos = current_pos
    
    def __getitem__(self, offset: int) -> float:
        """
        Get value at offset from current position.
        
        Args:
            offset: 0 = current, -1 = previous, -2 = two candles ago, etc.
                   Positive offsets are not supported (future data)
        
        Returns:
            Value at specified offset
        """
        if offset > 0:
            raise IndexError(f"Positive offset {offset} not allowed. Cannot access future data.")
        
        target_idx = self.current_pos + offset
        
        if target_idx < 0 or target_idx >= len(self.values):
            raise IndexError(
                f"Offset {offset} out of bounds. "
                f"Current position: {self.current_pos}, "
                f"Array length: {len(self.values)}, "
                f"Target index: {target_idx}"
            )
        
        return self.values[target_idx]
    
    def __len__(self) -> int:
        """Get number of values in column."""
        return len(self.values)
    
    def get_values(self, lookback: int = 0) -> np.ndarray:
        """
        Get array of values up to current position.
        
        Args:
            lookback: Number of historical values to include
            
        Returns:
            Array of values
        """
        start_idx = max(0, self.current_pos - lookback)
        end_idx = self.current_pos + 1
        return self.values[start_idx:end_idx]