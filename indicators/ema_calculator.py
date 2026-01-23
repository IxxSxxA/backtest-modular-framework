import pandas as pd
import numpy as np
from .base_calculator import BaseCalculator
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class EMACalculator(BaseCalculator):
    """
    Exponential Moving Average calculator with multi-timeframe support.

    Parameters:
        period: Number of periods for EMA
        column: Price column to use (default: 'close')
        tf: Target timeframe for calculation (e.g., '1h', '4h', '1d')

    Calculation Logic:
        - If tf='1m' or not specified: EMA calculated directly on 1m data
        - If tf='1h':
          1. Resample 1m data to 1h OHLC
          2. Calculate EMA on resampled 1h data
          3. Forward-fill values to 1m (constant for 60 minutes)
    """

    def calculate(self, data: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
        """
        Calculate Exponential Moving Average with timeframe support.
        """
        # Get parameters
        period = int(params.get("period", 14))
        price_column = str(params.get("column", "close"))
        target_tf = params.get("tf", "1m")

        if period <= 0:
            raise ValueError(f"Invalid period for EMA: {period}")

        if price_column not in data.columns:
            available = list(data.columns)
            raise ValueError(
                f"Price column '{price_column}' not found in data. "
                f"Available columns: {available}"
            )

        logger.info(
            f"Calculating EMA({period}) on {price_column} "
            f"for {self.symbol} (target TF: {target_tf})"
        )

        # Decide calculation method based on target timeframe
        if target_tf == "1m":
            # Direct calculation on 1m data
            ema_values = self._calculate_ema_direct(data, price_column, period)
            ema_values.name = f"ema_{period}_1m"
        else:
            # Calculate on higher timeframe, then forward-fill to 1m
            ema_values = self._calculate_ema_resampled(
                data, price_column, period, target_tf
            )
            ema_values.name = f"ema_{period}_{target_tf}"

        return ema_values

    def _calculate_ema_direct(
        self, data: pd.DataFrame, price_column: str, period: int
    ) -> pd.Series:
        """Calculate EMA directly on 1m data."""
        ema = data[price_column].ewm(span=period, min_periods=1, adjust=False).mean()

        return ema

    def _calculate_ema_resampled(
        self, data: pd.DataFrame, price_column: str, period: int, target_tf: str
    ) -> pd.Series:
        """
        Calculate EMA on resampled data, then forward-fill to 1m.
        """
        # Get minutes per candle for target timeframe
        if target_tf not in self.TF_TO_MINUTES:
            raise ValueError(
                f"Unsupported timeframe: {target_tf}. "
                f"Supported: {list(self.TF_TO_MINUTES.keys())}"
            )

        minutes_per_candle = self.TF_TO_MINUTES[target_tf]

        # 1. Resample 1m data to target timeframe
        logger.debug(f"Resampling 1m → {target_tf} ({minutes_per_candle} minutes)")
        resampled = self._resample_to_timeframe(data, minutes_per_candle)

        # 2. Calculate EMA on resampled data
        ema_resampled = (
            resampled["close"].ewm(span=period, min_periods=1, adjust=False).mean()
        )

        # 3. Forward-fill EMA values to match original 1m index
        ema_1m = self._forward_fill_to_1m(
            indicator_series=ema_resampled,
            original_index=data.index,
            minutes_per_candle=minutes_per_candle,
        )

        return ema_1m

    def get_required_columns(self) -> list:
        """Return list of required columns from input data."""
        return ["close"]  # Default, can be overridden by params['column']
