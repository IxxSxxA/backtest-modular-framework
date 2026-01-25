# indicators/cvd_ratio_calculator.py - REFACTORED VERSION

import pandas as pd
import numpy as np
from .base_calculator import BaseCalculator
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class CVDRatioCalculator(BaseCalculator):
    """
    CVD Signal Calculator (PineScript-compatible)

    Replicates PineScript logic:
    ```pine
    [openCVD, maxCVD, minCVD, lastCVD] = ta_lib.requestVolumeDelta(...)
    cvdRange = maxCVD - minCVD
    cvdSignal = cvdRange != 0 ? (lastCVD - minCVD) / cvdRange * 100 : 50
    ```

    Returns 0-100% signal where:
      - 0% = CVD at minimum of rolling window (extreme selling)
      - 50% = Neutral (range is zero or CVD at midpoint)
      - 100% = CVD at maximum of rolling window (extreme buying)
    """

    def __init__(self, symbol: str, timeframe: str, cache_dir: str = "data/indicators"):
        """Initialize CVD calculator."""
        super().__init__(symbol, timeframe, cache_dir)
        self.data_1m_cache = None  # Cache 1m data for performance

    def calculate(self, data: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
        """
        Calculate CVD signal using 1m granular data.

        Parameters:
        -----------
        data : pd.DataFrame
            Strategy timeframe data (for alignment)
        params : Dict[str, Any]
            - cumulative_period_minutes: Window for CVD accumulation (default: 15)
            - signal_period_minutes: Window for min/max (default: same as cumulative)
            - use_quote: Use quote volume (default: False)
            - data_file_path: Path to 1m parquet file (required!)

        Returns:
        --------
        pd.Series : CVD signal (0-100%)
        """
        # Get parameters
        cumulative_minutes = int(params.get("cumulative_period_minutes", 15))
        signal_minutes = int(params.get("signal_period_minutes", cumulative_minutes))
        use_quote = bool(params.get("use_quote", False))
        data_file_path = params.get("data_file_path")

        if not data_file_path:
            raise ValueError("data_file_path is required in params!")

        logger.info(
            f"Calculating CVD signal: cumulative={cumulative_minutes}min, "
            f"signal={signal_minutes}min, use_quote={use_quote}"
        )

        # Load 1m data (with smart filtering for performance)
        df_1m = self._load_1m_data(
            file_path=Path(data_file_path),
            start=data.index[0],
            end=data.index[-1],
            padding_minutes=max(cumulative_minutes, signal_minutes) * 2,
        )

        # Calculate volume delta
        volume_delta = self._calculate_volume_delta(df_1m, use_quote)

        # Calculate CVD signal
        signal_1m = self._calculate_cvd_signal(
            volume_delta, cumulative_minutes, signal_minutes
        )

        # Resample to strategy timeframe
        signal_tf = self._resample_to_strategy_tf(signal_1m, self.timeframe)

        # Align with input data index
        result = signal_tf.reindex(data.index, method="ffill")

        # Clip to 0-100 range (safety)
        result = result.clip(0, 100)

        # Set name
        result.name = f"cvd_{cumulative_minutes}"

        # Log statistics
        logger.info(
            f"CVD Signal: min={result.min():.1f}%, max={result.max():.1f}%, "
            f"mean={result.mean():.1f}%, std={result.std():.1f}%"
        )

        return result

    def _load_1m_data(
        self,
        file_path: Path,
        start: pd.Timestamp,
        end: pd.Timestamp,
        padding_minutes: int = 30,
    ) -> pd.DataFrame:
        """
        Load 1m data with smart filtering for performance.

        Only loads the time range needed for the backtest + padding.
        """
        # Add padding for rolling window calculations
        padding = pd.Timedelta(minutes=padding_minutes)
        filter_start = start - padding
        filter_end = end + padding

        logger.info(f"Loading 1m data from: {file_path}")
        logger.info(f"Time range: {filter_start} to {filter_end} (with padding)")

        # Load with timestamp filtering if possible
        try:
            df = pd.read_parquet(
                file_path,
                filters=[
                    ("timestamp", ">=", int(filter_start.timestamp() * 1000)),
                    ("timestamp", "<=", int(filter_end.timestamp() * 1000)),
                ],
            )
            logger.info(f"Loaded {len(df):,} rows (filtered)")
        except Exception:
            # Fallback: load all and filter in memory
            df = pd.read_parquet(file_path)
            logger.info(f"Loaded {len(df):,} rows (unfiltered)")

            # Convert timestamp
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                df.set_index("timestamp", inplace=True)

            # Filter in memory
            df = df[(df.index >= filter_start) & (df.index <= filter_end)]
            logger.info(f"Filtered to {len(df):,} rows")
        else:
            # Convert timestamp for filtered data
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                df.set_index("timestamp", inplace=True)

        df.sort_index(inplace=True)
        return df

    def _calculate_volume_delta(self, df: pd.DataFrame, use_quote: bool) -> pd.Series:
        """Calculate volume delta (buy_volume - sell_volume)."""
        if use_quote and "taker_buy_quote_volume" in df.columns:
            buy_vol = df["taker_buy_quote_volume"]
            total_vol = df["quote_volume"]
            logger.info("Using quote volume for CVD")
        elif "taker_buy_volume" in df.columns:
            buy_vol = df["taker_buy_volume"]
            total_vol = df["volume"]
            logger.info("Using base volume for CVD")
        else:
            raise KeyError(f"Missing volume columns. Available: {df.columns.tolist()}")

        sell_vol = total_vol - buy_vol
        volume_delta = buy_vol - sell_vol

        logger.debug(
            f"Volume delta: min={volume_delta.min():.0f}, "
            f"max={volume_delta.max():.0f}, mean={volume_delta.mean():.0f}"
        )

        return volume_delta

    def _calculate_cvd_signal(
        self,
        volume_delta: pd.Series,
        cumulative_minutes: int,
        signal_minutes: int,
    ) -> pd.Series:
        """
        Calculate CVD signal (0-100%).

        Logic:
        1. Cumulative CVD = rolling sum of volume_delta over cumulative_minutes
        2. Min/Max CVD = rolling min/max over signal_minutes
        3. Range = max - min
        4. Signal = (current - min) / range * 100 (or 50 if range == 0)
        """
        # Step 1: Cumulative CVD
        cumulative_cvd = volume_delta.rolling(
            window=cumulative_minutes, min_periods=1
        ).sum()

        # Step 2: Min/Max over signal window
        min_cvd = cumulative_cvd.rolling(window=signal_minutes, min_periods=1).min()
        max_cvd = cumulative_cvd.rolling(window=signal_minutes, min_periods=1).max()

        # Step 3: Range
        cvd_range = max_cvd - min_cvd

        # Log statistics
        zero_range_count = (cvd_range == 0).sum()
        logger.info(
            f"CVD range: min={cvd_range.min():.0f}, max={cvd_range.max():.0f}, "
            f"zero={zero_range_count:,}/{len(cvd_range):,} "
            f"({zero_range_count/len(cvd_range)*100:.1f}%)"
        )

        # Step 4: Normalize to 0-100%
        signal = pd.Series(50.0, index=cumulative_cvd.index)  # Default: 50%

        mask = cvd_range > 0
        if mask.sum() > 0:
            signal[mask] = (
                (cumulative_cvd[mask] - min_cvd[mask]) / cvd_range[mask] * 100
            )

        return signal

    def _resample_to_strategy_tf(
        self, signal_1m: pd.Series, timeframe: str
    ) -> pd.Series:
        """Resample 1m signal to strategy timeframe."""
        if timeframe == "1m":
            return signal_1m

        # Map timeframe to minutes
        minutes_map = {
            "5m": 5,
            "15m": 15,
            "30m": 30,
            "1h": 60,
            "4h": 240,
            "1d": 1440,
        }

        minutes = minutes_map.get(timeframe)
        if not minutes:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        # Resample: take last value of each period
        signal_tf = signal_1m.resample(
            f"{minutes}min", label="left", closed="left"
        ).last()

        return signal_tf
