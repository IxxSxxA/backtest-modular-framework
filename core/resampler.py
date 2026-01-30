# core/resampler.py
"""
Data resampling utilities for trading framework.
Handles OHLCV aggregation across different timeframes.
"""

import pandas as pd
import numpy as np
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class DataResampler:
    """
    Handles resampling of OHLCV data to different timeframes.
    """

    # Timeframe mapping
    TF_MAP = {
        "1m": "1min",
        "3m": "3min",
        "5m": "5min",
        "15m": "15min",
        "30m": "30min",
        "1h": "1h",
        "2h": "2h",
        "3h": "3h",
        "4h": "4h",
        "6h": "6h",
        "8h": "8h",
        "12h": "12h",
        "1d": "1D",
    }

    @staticmethod
    def resample_to_timeframe(
        df: pd.DataFrame,
        target_tf: str,
        normalize_index: bool = True,
        quality_threshold: float = 0.95,
    ) -> pd.DataFrame:
        """
        Resample 1m data to target timeframe with ALL required columns.

        Args:
            df: DataFrame with 1m OHLCV data
            target_tf: Target timeframe (e.g., '5m', '1h')
            normalize_index: If True, floor index to minute precision
            quality_threshold: Minimum data retention ratio (default: 95%)

        Returns:
            Resampled DataFrame

        Raises:
            ValueError: If data quality is below threshold
        """
        if target_tf == "1m":
            logger.info("Target timeframe is 1m, no resampling needed")
            return df.copy()

        logger.info(f"Resampling from 1m to {target_tf}...")

        pandas_tf = DataResampler.TF_MAP.get(target_tf)
        if not pandas_tf:
            raise ValueError(
                f"Unsupported timeframe: {target_tf}. "
                f"Supported: {list(DataResampler.TF_MAP.keys())}"
            )

        # Define aggregation rules
        agg_dict = {
            # OHLC
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            # Volume columns (SUM aggregation)
            "volume": "sum",
            "quote_volume": "sum",
            "taker_buy_volume": "sum",
            "taker_buy_quote_volume": "sum",
            # Others
            "count": "sum",
            "ignore": "sum",
        }

        # Filter only existing columns
        existing_cols = [col for col in agg_dict.keys() if col in df.columns]
        filtered_agg_dict = {col: agg_dict[col] for col in existing_cols}

        # Resample with label='left', closed='left'
        resampled = df.resample(pandas_tf, label="left", closed="left").agg(
            filtered_agg_dict
        )

        # FIX #2: Normalize index to minute precision
        if normalize_index:
            resampled.index = resampled.index.floor("min")
            logger.debug("Index normalized to minute precision")

        # Forward-fill NaN values for OHLC
        ohlc_cols = ["open", "high", "low", "close"]
        existing_ohlc = [col for col in ohlc_cols if col in resampled.columns]
        if existing_ohlc:
            resampled[existing_ohlc] = resampled[existing_ohlc].ffill()

        # FIX #3: Check data quality before dropping NaN
        original_len = len(resampled)
        resampled = resampled.dropna()
        dropped_count = original_len - len(resampled)

        if dropped_count > 0:
            retention_ratio = len(resampled) / original_len
            logger.info(
                f"Dropped {dropped_count} incomplete {target_tf} candles "
                f"(retention: {retention_ratio:.1%})"
            )

            # FIX #3: Raise error if too much data lost
            if retention_ratio < quality_threshold:
                raise ValueError(
                    f"❌ Data quality check FAILED!\n"
                    f"   Dropped {dropped_count}/{original_len} candles "
                    f"({(1-retention_ratio):.1%} loss)\n"
                    f"   Threshold: {(1-quality_threshold):.1%}\n"
                    f"   Check your data for gaps or quality issues!"
                )

        logger.info(
            f"Resampled: {len(df):,} rows (1m) → {len(resampled):,} rows ({target_tf})"
        )
        logger.debug(f"Columns after resampling: {list(resampled.columns)}")

        return resampled

    @staticmethod
    def normalize_backtest_start(
        df: pd.DataFrame, start_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        FIX #6: Normalize backtest start to midnight (00:00) of the day.

        Args:
            df: Input DataFrame
            start_date: Optional start date from config

        Returns:
            DataFrame starting from midnight or next day's midnight
        """
        if start_date:
            start_dt = pd.to_datetime(start_date)
        else:
            start_dt = df.index[0]

        # Floor to midnight
        midnight_start = start_dt.floor("D")

        # Check if we have data from midnight
        if midnight_start in df.index:
            logger.info(f"✅ Data starts at midnight: {midnight_start}")
            return df[df.index >= midnight_start]
        else:
            # Move to next day's midnight
            next_midnight = midnight_start + pd.Timedelta(days=1)
            logger.warning(
                f"⚠️ Data doesn't start at midnight {midnight_start}\n"
                f"   Moving start to next day: {next_midnight}\n"
                f"   (Dropping partial day - this is expected for backtests)"
            )
            return df[df.index >= next_midnight]
