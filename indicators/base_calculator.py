import pandas as pd
import numpy as np
import hashlib
import json
import os
from pathlib import Path
from abc import ABC, abstractmethod
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class BaseCalculator(ABC):
    """
    Abstract base class for all indicator calculators.
    Handles caching and provides common functionality.
    """

    def __init__(self, symbol: str, timeframe: str, cache_dir: str = "data/indicators"):
        """
        Initialize calculator.

        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            timeframe: Data timeframe (e.g., '1m', '5m')
            cache_dir: Directory to store cached indicators
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.cache_dir = Path(cache_dir)

        # Create cache directory structure
        self.symbol_cache_dir = self.cache_dir / symbol
        self.symbol_cache_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def calculate(self, data: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
        """
        Calculate the indicator values.

        Args:
            data: DataFrame with OHLCV data
            params: Dictionary of indicator parameters

        Returns:
            Series with calculated values (same index as data)
        """
        pass

    def get_cache_key(self, params: Dict[str, Any]) -> str:
        """
        FIX #9: Generate unique cache key including ALL parameters.

        Format: indicator_tf_param1_param2_hash
        Example: sma_5m_p200_1a2b3c4d

        Args:
            params: Indicator parameters

        Returns:
            Unique cache key string
        """
        # Create deterministic hash of ALL parameters
        param_str = json.dumps(params, sort_keys=True)
        param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]

        indicator_name = self.__class__.__name__.replace("Calculator", "").lower()

        # Build human-readable key with main parameters
        key_parts = [indicator_name, self.timeframe]

        # Add significant parameters to key for readability
        if "window_minutes" in params:
            key_parts.append(f"w{params['window_minutes']}")
        if "period" in params:
            key_parts.append(f"p{params['period']}")
        if "use_quote" in params:
            key_parts.append(f"q{int(params['use_quote'])}")

        # Add hash of ALL params for uniqueness
        key_parts.append(param_hash)

        cache_key = "_".join(key_parts)

        logger.debug(f"Cache key: {cache_key} (params: {params})")

        return cache_key

    def _resample_to_timeframe(self, data: pd.DataFrame, minutes: int) -> pd.DataFrame:
        """
        Resample 1m OHLC data to specified minute timeframe.
        Returns OHLC data only (no volume for price-based indicators).
        """
        # Resample rules for OHLC
        ohlc_agg = {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
        }

        # Resample
        resampled = (
            data[["open", "high", "low", "close"]].resample(f"{minutes}T").agg(ohlc_agg)
        )

        # Drop rows with NaN (incomplete candles at boundaries)
        resampled = resampled.dropna()

        return resampled

    def _forward_fill_to_1m(
        self,
        indicator_series: pd.Series,
        original_index: pd.DatetimeIndex,
        minutes_per_candle: int,
    ) -> pd.Series:
        """
        Forward-fill higher timeframe indicator values to 1m.
        Each indicator value repeats for N minutes.
        """
        # Create empty Series with original 1m index
        result = pd.Series(index=original_index, dtype=float)

        # For each higher timeframe value, fill for all 1m periods
        for idx, value in indicator_series.items():
            # Calculate start and end of this higher TF candle
            candle_end = idx
            candle_start = candle_end - pd.Timedelta(minutes=minutes_per_candle - 1)

            # Find all 1m timestamps within this candle
            mask = (original_index >= candle_start) & (original_index <= candle_end)

            # Fill with the indicator value
            result.loc[mask] = value

        # Fill any remaining NaN
        result = result.ffill().bfill()

        return result

    # Mapping of timeframe string to minutes
    TF_TO_MINUTES = {
        "1m": 1,
        "5m": 5,
        "15m": 15,
        "30m": 30,
        "1h": 60,
        "2h": 120,
        "4h": 240,
        "12h": 720,
        "1d": 1440,
        "1w": 10080,
    }

    def _params_to_str(self, params: Dict[str, Any]) -> str:
        """
        Convert parameters to string for cache key.

        Args:
            params: Indicator parameters

        Returns:
            String representation
        """
        parts = []
        for key, value in sorted(params.items()):
            parts.append(f"{key}{value}")
        return "_".join(parts)

    def get_cache_filepath(self, params: Dict[str, Any]) -> Path:
        """
        Get full filepath for cached indicator.

        Args:
            params: Indicator parameters

        Returns:
            Path to cache file
        """
        cache_key = self.get_cache_key(params)
        return self.symbol_cache_dir / f"{cache_key}.parquet"

    def is_cached(self, params: Dict[str, Any]) -> bool:
        """
        Check if indicator is already cached.

        Args:
            params: Indicator parameters

        Returns:
            True if cached file exists and is valid
        """
        cache_file = self.get_cache_filepath(params)

        if not cache_file.exists():
            return False

        try:
            # Try to read the file to ensure it's valid
            pd.read_parquet(cache_file)
            return True
        except Exception as e:
            logger.warning(f"Cache file corrupted {cache_file}: {e}")
            # Remove corrupted file
            cache_file.unlink(missing_ok=True)
            return False

    def save_to_cache(
        self, values: pd.Series, params: Dict[str, Any], column_name: str = None
    ):
        """
        Save indicator values to cache with correct column name.

        Args:
            values: Series with calculated values
            params: Indicator parameters used
            column_name: Desired column name (from config)
        """
        cache_file = self.get_cache_filepath(params)

        try:
            # Use column_name if provided, otherwise use series name or 'value'
            if column_name:
                col_name = column_name
            elif values.name and values.name != "value":  # Avoid generic 'value'
                col_name = values.name
            else:
                col_name = "value"

            # Save with correct column name
            df = pd.DataFrame({col_name: values})

            # Save metadata about column name in DataFrame attributes
            df.attrs["column_name"] = col_name
            df.attrs["indicator_name"] = self.__class__.__name__.replace(
                "Calculator", ""
            ).lower()
            df.attrs["params"] = params

            df.to_parquet(cache_file)
            logger.debug(f"Saved to cache: {cache_file.name} (column: {col_name})")

        except Exception as e:
            logger.error(f"Error saving cache {cache_file}: {e}")

    def load_from_cache(self, params: Dict[str, Any]) -> pd.Series:
        """
        Load indicator values from cache.

        Args:
            params: Indicator parameters

        Returns:
            Series with cached values (with correct name)
        """
        cache_file = self.get_cache_filepath(params)

        if not self.is_cached(params):
            raise FileNotFoundError(f"Indicator not cached: {cache_file}")

        try:
            df = pd.read_parquet(cache_file)

            # Determine which column to use
            if len(df.columns) == 1:
                # Single column - use it
                col_name = df.columns[0]
            elif "value" in df.columns:
                # Fallback to 'value' for backward compatibility
                col_name = "value"
            else:
                # Use first column
                col_name = df.columns[0]

            # Get the series
            series = df[col_name]
            series.index = (
                pd.to_datetime(df.index)
                if not isinstance(df.index, pd.DatetimeIndex)
                else df.index
            )

            # Set series name from column name
            series.name = col_name

            # Try to restore original name from metadata if available
            if hasattr(df, "attrs") and "column_name" in df.attrs:
                series.name = df.attrs["column_name"]

            logger.debug(
                f"Loaded from cache: {cache_file.name} (column: {series.name})"
            )
            return series

        except Exception as e:
            logger.error(f"Error loading cache {cache_file}: {e}")
            raise

    def calculate_with_cache(
        self, data: pd.DataFrame, params: Dict[str, Any], column_name: str = None
    ) -> pd.Series:
        """
        Calculate indicator with caching support.

        Args:
            data: DataFrame with OHLCV data
            params: Indicator parameters
            column_name: Desired column name (from config)

        Returns:
            Series with calculated values (with correct name)
        """
        # Check cache first
        if self.is_cached(params):
            try:
                cached_values = self.load_from_cache(params)

                # Ensure cached values align with current data
                if len(cached_values) == len(data) and cached_values.index.equals(
                    data.index
                ):
                    logger.info(
                        f"✅ Using cached indicator: {self.get_cache_key(params)}"
                    )

                    # If column_name is provided and different from cached name, rename
                    if column_name and column_name != cached_values.name:
                        cached_values.name = column_name

                    return cached_values
                else:
                    logger.warning(
                        f"Cache mismatch, recalculating: {self.get_cache_key(params)}"
                    )
            except Exception as e:
                logger.warning(f"Cache error, recalculating: {e}")

        # Calculate fresh
        logger.info(f"🔄 Calculating indicator: {self.get_cache_key(params)}")
        values = self.calculate(data, params)

        # Set column name if provided
        if column_name:
            values.name = column_name

        # Save to cache for future use
        self.save_to_cache(values, params, column_name)

        return values
