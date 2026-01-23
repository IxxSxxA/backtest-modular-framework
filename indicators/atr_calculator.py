import pandas as pd
import numpy as np
from .base_calculator import BaseCalculator
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class ATRCalculator(BaseCalculator):
    """
    Average True Range calculator with multi-timeframe support.

    Parameters:
        period: Number of periods for ATR smoothing
        tf: Target timeframe for calculation (e.g., '1h', '4h', '1d')

    Note: Already had tf support, now uses BaseCalculator helpers for consistency.
    """

    def calculate(self, data: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
        """
        Calculate Average True Range with timeframe support.
        """
        period = int(params.get("period", 14))
        target_tf = params.get("tf", "1m")

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
            f"Calculating ATR({period}) for {self.symbol} (target TF: {target_tf})"
        )

        if target_tf == "1m":
            # Direct calculation on 1m data
            atr_values = self._calculate_atr_direct(data, period)
            atr_values.name = f"atr_{period}_1m"
        else:
            # Calculate on higher timeframe, then forward-fill to 1m
            atr_values = self._calculate_atr_resampled(data, period, target_tf)
            atr_values.name = f"atr_{period}_{target_tf}"

        return atr_values

    def _calculate_atr_direct(self, data: pd.DataFrame, period: int) -> pd.Series:
        """Calculate ATR directly on 1m data."""
        # Calculate True Range
        tr = self._calculate_true_range(data)

        # Calculate ATR as EMA (Wilder's smoothing)
        atr = tr.ewm(alpha=1 / period, min_periods=1, adjust=False).mean()

        return atr

    def _calculate_atr_resampled(
        self, data: pd.DataFrame, period: int, target_tf: str
    ) -> pd.Series:
        """
        Calculate ATR on resampled data, then forward-fill to 1m.
        """
        # Get minutes per candle for target timeframe
        if target_tf not in self.TF_TO_MINUTES:
            raise ValueError(
                f"Unsupported timeframe: {target_tf}. "
                f"Supported: {list(self.TF_TO_MINUTES.keys())}"
            )

        minutes_per_candle = self.TF_TO_MINUTES[target_tf]

        # 1. Resample 1m data to target timeframe
        resampled = self._resample_to_timeframe(data, minutes_per_candle)

        # 2. Calculate True Range on resampled data
        tr_resampled = self._calculate_true_range(resampled)

        # 3. Calculate ATR on resampled data
        atr_resampled = tr_resampled.ewm(
            alpha=1 / period, min_periods=1, adjust=False
        ).mean()

        # 4. Forward-fill ATR values to match original 1m index
        atr_1m = self._forward_fill_to_1m(
            indicator_series=atr_resampled,
            original_index=data.index,
            minutes_per_candle=minutes_per_candle,
        )

        return atr_1m

    def _calculate_true_range(self, data: pd.DataFrame) -> pd.Series:
        """Calculate True Range from OHLC data."""
        hl = data["high"] - data["low"]
        h_pc = abs(data["high"] - data["close"].shift(1))
        l_pc = abs(data["low"] - data["close"].shift(1))

        tr = pd.concat([hl, h_pc, l_pc], axis=1).max(axis=1)
        tr.iloc[0] = hl.iloc[0]

        return tr

    def get_required_columns(self) -> list:
        """Return list of required columns from input data."""
        return ["high", "low", "close"]
