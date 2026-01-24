import pandas as pd
import numpy as np
from .base_calculator import BaseCalculator
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class ATRCalculator(BaseCalculator):
    """
    Average True Range (ATR) calculator.

    Calculates ATR on the data's current timeframe (already resampled by framework).
    Uses Wilder's smoothing method for authentic ATR calculation.

    Parameters:
        period: Number of periods for ATR smoothing (default: 14)
        method: Smoothing method - 'wilder' (default) or 'ema'

    Note: Data is already resampled to strategy timeframe by the framework.
          No need for internal resampling or tf parameter.
    """

    def calculate(self, data: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
        """
        Calculate Average True Range.

        Args:
            data: DataFrame with OHLC data (already at strategy timeframe)
            params: Dictionary with 'period' and optional 'method'

        Returns:
            Series with ATR values
        """
        period = int(params.get("period", 14))
        method = params.get("method", "wilder")  # 'wilder' or 'ema'

        if period <= 0:
            raise ValueError(f"Invalid period for ATR: {period}")

        # Check required columns
        required = ["high", "low", "close"]
        missing = [col for col in required if col not in data.columns]
        if missing:
            available = list(data.columns)
            raise ValueError(
                f"Missing columns for ATR: {missing}. "
                f"Available columns: {available}"
            )

        logger.info(
            f"Calculating ATR({period}) for {self.symbol} on {self.timeframe} "
            f"(method: {method})"
        )

        # Calculate True Range
        tr = self._calculate_true_range(data)

        # Calculate ATR based on method
        if method == "wilder":
            # Wilder's original smoothing (more common)
            atr = self._calculate_atr_wilder(tr, period)
        elif method == "ema":
            # Standard EMA smoothing
            atr = self._calculate_atr_ema(tr, period)
        else:
            raise ValueError(f"Unknown ATR method: {method}. Use 'wilder' or 'ema'")

        # Set name
        atr.name = f"atr_{period}"

        logger.debug(
            f"ATR stats: min={atr.min():.4f}, "
            f"max={atr.max():.4f}, mean={atr.mean():.4f}"
        )

        return atr

    def _calculate_true_range(self, data: pd.DataFrame) -> pd.Series:
        """
        Calculate True Range (TR).

        TR = max(high - low, |high - prev_close|, |low - prev_close|)

        Args:
            data: DataFrame with high, low, close

        Returns:
            Series with True Range values
        """
        # Three components of True Range
        hl = data["high"] - data["low"]  # Current high-low range
        h_pc = abs(data["high"] - data["close"].shift(1))  # High vs prev close
        l_pc = abs(data["low"] - data["close"].shift(1))  # Low vs prev close

        # TR is the maximum of the three
        tr = pd.concat([hl, h_pc, l_pc], axis=1).max(axis=1)

        # For first row (no previous close), use simple high-low
        tr.iloc[0] = hl.iloc[0]

        tr.name = "true_range"

        return tr

    def _calculate_atr_wilder(self, tr: pd.Series, period: int) -> pd.Series:
        """
        Calculate ATR using Wilder's smoothing method.

        Wilder's smoothing formula:
        ATR[i] = (ATR[i-1] * (period - 1) + TR[i]) / period

        This is equivalent to EWM with alpha = 1/period, but more explicit.

        Args:
            tr: True Range series
            period: Smoothing period

        Returns:
            Series with ATR values
        """
        # Initialize ATR array
        atr = pd.Series(index=tr.index, dtype=float)

        # First ATR value is SMA of first 'period' TRs
        atr.iloc[0:period] = tr.iloc[0:period].expanding().mean()

        # Apply Wilder's smoothing for remaining values
        for i in range(period, len(tr)):
            atr.iloc[i] = (atr.iloc[i - 1] * (period - 1) + tr.iloc[i]) / period

        return atr

    def _calculate_atr_ema(self, tr: pd.Series, period: int) -> pd.Series:
        """
        Calculate ATR using standard EMA smoothing.

        This is faster but slightly different from Wilder's original method.

        Args:
            tr: True Range series
            period: EMA period

        Returns:
            Series with ATR values
        """
        # EMA with span=period
        atr = tr.ewm(span=period, min_periods=period, adjust=False).mean()

        return atr

    def get_required_columns(self) -> list:
        """Return list of required columns from input data."""
        return ["high", "low", "close"]
