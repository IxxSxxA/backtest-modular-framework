import pandas as pd
import numpy as np
from .base_calculator import BaseCalculator
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


# ============================================================================
# SMA Calculator
# ============================================================================


class SMACalculator(BaseCalculator):
    """
    Simple Moving Average calculator.

    Calculates SMA on the data's current timeframe (already resampled by framework).

    Parameters:
        period: Number of periods for SMA calculation

    Note: Data is already resampled to strategy timeframe by the framework.
    """

    def calculate(self, data: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
        """
        Calculate Simple Moving Average.

        Args:
            data: DataFrame with OHLC data (already at strategy timeframe)
            params: Dictionary with 'period'

        Returns:
            Series with SMA values
        """
        period = int(params.get("period", 20))

        if period <= 0:
            raise ValueError(f"Invalid period for SMA: {period}")

        if period > len(data):
            logger.warning(
                f"SMA period ({period}) is larger than data length ({len(data)}). "
                f"First {period} values will be NaN."
            )

        # Check for required column
        if "close" not in data.columns:
            raise ValueError(
                f"Column 'close' not found in data. " f"Available: {list(data.columns)}"
            )

        logger.info(f"Calculating SMA({period}) for {self.symbol} on {self.timeframe}")

        # Calculate SMA
        sma = data["close"].rolling(window=period, min_periods=period).mean()

        # Set name
        sma.name = f"sma_{period}"

        logger.debug(
            f"SMA stats: min={sma.min():.4f}, "
            f"max={sma.max():.4f}, "
            f"mean={sma.mean():.4f}, "
            f"first_valid={sma.first_valid_index()}"
        )

        return sma

        def get_required_columns(self) -> list:
            """Return list of required columns from input data."""
            return ["high", "low", "close"]
