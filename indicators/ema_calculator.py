import pandas as pd
import numpy as np
from .base_calculator import BaseCalculator
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class EMACalculator(BaseCalculator):
    """
    Exponential Moving Average calculator.

    Calculates EMA on the data's current timeframe (already resampled by framework).

    Parameters:
        period: Number of periods for EMA calculation
        adjust: Use adjusted calculation (default: False)

    Note: Data is already resampled to strategy timeframe by the framework.
    """

    def calculate(self, data: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
        """
        Calculate Exponential Moving Average.

        Args:
            data: DataFrame with OHLC data (already at strategy timeframe)
            params: Dictionary with 'period' and optional 'adjust'

        Returns:
            Series with EMA values
        """
        period = int(params.get("period", 20))
        adjust = params.get("adjust", False)  # Standard EMA uses adjust=False

        if period <= 0:
            raise ValueError(f"Invalid period for EMA: {period}")

        if period > len(data):
            logger.warning(
                f"EMA period ({period}) is larger than data length ({len(data)}). "
                f"First {period} values will be NaN."
            )

        # Check for required column
        if "close" not in data.columns:
            raise ValueError(
                f"Column 'close' not found in data. " f"Available: {list(data.columns)}"
            )

        logger.info(
            f"Calculating EMA({period}) for {self.symbol} on {self.timeframe} "
            f"(adjust={adjust})"
        )

        # Calculate EMA
        # span=period gives same smoothing as alpha = 2/(period+1)
        ema = data["close"].ewm(span=period, min_periods=period, adjust=adjust).mean()

        # Set name
        ema.name = f"ema_{period}"

        logger.debug(
            f"EMA stats: min={ema.min():.4f}, "
            f"max={ema.max():.4f}, "
            f"mean={ema.mean():.4f}, "
            f"first_valid={ema.first_valid_index()}"
        )

        return ema

        def get_required_columns(self) -> list:
            """Return list of required columns from input data."""
            return ["high", "low", "close"]
