import pandas as pd
import numpy as np
from .base_calculator import BaseCalculator
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class CVDCalculator(BaseCalculator):
    """
    Cumulative Volume Delta calculator with multi-timeframe support.

    Parameters:
        use_quote: If True, uses quote volume (default: False)
        reset_period_minutes: Reset CVD every N minutes (0 = no reset)
        tf: Target timeframe for calculation (e.g., '1h', '4h', '1d')
            Note: For CVD, 'tf' determines the aggregation period for
            volume data before calculating CVD

    Important: CVD with tf='1h' is DIFFERENT from CVD with tf='1m' + reset_period_minutes=60
    """

    def calculate(self, data: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
        """
        Calculate Cumulative Volume Delta with timeframe support.
        """
        # Get parameters
        use_quote = bool(params.get("use_quote", False))
        reset_period_minutes = int(params.get("reset_period_minutes", 0))
        target_tf = params.get("tf", "1m")

        if reset_period_minutes < 0:
            raise ValueError(
                f"reset_period_minutes must be >= 0, got {reset_period_minutes}"
            )

        logger.info(
            f"Calculating CVD for {self.symbol} "
            f"(target TF: {target_tf}, reset: {reset_period_minutes}min)"
        )

        # Decide calculation method based on target timeframe
        if target_tf == "1m":
            # Direct calculation on 1m data
            cvd_values = self._calculate_cvd_direct(
                data, use_quote, reset_period_minutes
            )
            cvd_values.name = self._generate_cvd_name(
                use_quote, reset_period_minutes, "1m"
            )
        else:
            # Calculate on higher timeframe, then forward-fill to 1m
            cvd_values = self._calculate_cvd_resampled(
                data, use_quote, reset_period_minutes, target_tf
            )
            cvd_values.name = self._generate_cvd_name(
                use_quote, reset_period_minutes, target_tf
            )

        return cvd_values

    def _calculate_cvd_direct(
        self, data: pd.DataFrame, use_quote: bool, reset_minutes: int
    ) -> pd.Series:
        """Calculate CVD directly on 1m data."""
        # Determine volume columns
        if use_quote:
            total_volume_col = "quote_volume"
            taker_buy_col = "taker_buy_quote_volume"
        else:
            total_volume_col = "volume"
            taker_buy_col = "taker_buy_volume"

        # Calculate volume delta per candle
        taker_buy_volume = data[taker_buy_col]
        total_volume = data[total_volume_col]
        taker_sell_volume = total_volume - taker_buy_volume

        volume_delta = taker_buy_volume - taker_sell_volume

        # Apply reset if specified
        if reset_minutes > 0:
            cvd = self._calculate_reset_cvd(volume_delta, data.index, reset_minutes)
        else:
            cvd = volume_delta.cumsum()

        return cvd

    def _calculate_cvd_resampled(
        self, data: pd.DataFrame, use_quote: bool, reset_minutes: int, target_tf: str
    ) -> pd.Series:
        """
        Calculate CVD on resampled data, then forward-fill to 1m.
        """
        # Get minutes per candle for target timeframe
        if target_tf not in self.TF_TO_MINUTES:
            raise ValueError(
                f"Unsupported timeframe: {target_tf}. "
                f"Supported: {list(self.TF_TO_MINUTES.keys())}"
            )

        minutes_per_candle = self.TF_TO_MINUTES[target_tf]

        # Determine volume columns
        if use_quote:
            total_volume_col = "quote_volume"
            taker_buy_col = "taker_buy_quote_volume"
        else:
            total_volume_col = "volume"
            taker_buy_col = "taker_buy_volume"

        # Check required columns
        required = [total_volume_col, taker_buy_col]
        missing = [col for col in required if col not in data.columns]
        if missing:
            raise ValueError(f"Missing columns for CVD: {missing}")

        # 1. Resample volume data to target timeframe (SUM aggregation)
        volume_resample_rules = {total_volume_col: "sum", taker_buy_col: "sum"}

        resampled_volume = (
            data[[total_volume_col, taker_buy_col]]
            .resample(f"{minutes_per_candle}T")
            .agg(volume_resample_rules)
            .dropna()
        )

        # 2. Calculate volume delta on resampled data
        taker_buy_volume = resampled_volume[taker_buy_col]
        total_volume = resampled_volume[total_volume_col]
        taker_sell_volume = total_volume - taker_buy_volume

        volume_delta_resampled = taker_buy_volume - taker_sell_volume

        # 3. Apply reset on resampled data if specified
        if reset_minutes > 0:
            # Note: Reset period in minutes, but data is already resampled
            # We need to adjust reset period to higher timeframe
            reset_candles = max(1, reset_minutes // minutes_per_candle)
            cvd_resampled = self._calculate_reset_cvd(
                volume_delta_resampled,
                resampled_volume.index,
                reset_candles,
                is_candle_count=True,
            )
        else:
            cvd_resampled = volume_delta_resampled.cumsum()

        # 4. Forward-fill CVD values to match original 1m index
        cvd_1m = self._forward_fill_to_1m(
            indicator_series=cvd_resampled,
            original_index=data.index,
            minutes_per_candle=minutes_per_candle,
        )

        return cvd_1m

    def _calculate_reset_cvd(
        self,
        volume_delta: pd.Series,
        index: pd.DatetimeIndex,
        reset_period: int,
        is_candle_count: bool = False,
    ) -> pd.Series:
        """
        Calculate CVD with periodic reset.

        Args:
            is_candle_count: If True, reset_period is in candles, not minutes
        """
        if reset_period <= 0:
            return volume_delta.cumsum()

        if is_candle_count:
            # Reset every N candles
            group_key = (np.arange(len(volume_delta)) // reset_period).astype(int)
        else:
            # Reset every N minutes
            total_minutes = (index - index[0]).total_seconds() / 60
            group_key = (total_minutes // reset_period).astype(int)

        # Calculate cumulative sum within each group
        cvd = volume_delta.groupby(group_key).cumsum()

        return cvd

    def _generate_cvd_name(self, use_quote: bool, reset_minutes: int, tf: str) -> str:
        """Generate descriptive name for CVD series."""
        vol_type = "quote" if use_quote else "volume"
        base_name = f"cvd_{vol_type}"

        if reset_minutes > 0:
            base_name += f"_reset{reset_minutes}min"

        if tf != "1m":
            base_name += f"_{tf}"

        return base_name

    def get_required_columns(self) -> list:
        """Return list of required columns from input data."""
        return ["volume", "taker_buy_volume", "quote_volume", "taker_buy_quote_volume"]
