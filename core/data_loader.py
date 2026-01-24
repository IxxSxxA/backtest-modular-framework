import pandas as pd
import os
from pathlib import Path
import logging
from typing import Dict, List, Optional
import numpy as np
from core.resampler import DataResampler  # NEW IMPORT

logger = logging.getLogger(__name__)


class DataLoader:
    """
    Loads and prepares OHLCV data from parquet files.
    Clean and simplified version with direct file specification.
    """

    def __init__(self, config: Dict):
        """
        Initialize DataLoader with configuration.

        Args:
            config: Dictionary with configuration from config.yaml
        """
        self.config = config
        self.data_dir = config["data"]["source_dir"]
        self.symbols = config["data"]["symbols"]
        self.timeframe = config["data"]["timeframe"]

        # Get source file (optional - for backward compatibility)
        self.source_file = config["data"].get("source_file")

        # Date filtering
        backtest_config = config.get("backtest", {})
        period_config = backtest_config.get("period", {})
        self.filter_start = period_config.get("start")
        self.filter_end = period_config.get("end")

        # NEW: Create resampler instance
        self.resampler = DataResampler()

        # Validate data directory exists
        if not os.path.exists(self.data_dir):
            raise FileNotFoundError(f"Data directory not found: {self.data_dir}")

    def load_single_symbol(
        self, symbol: str, normalize_start: bool = False
    ) -> pd.DataFrame:
        """
        Load data for a single symbol.

        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            normalize_start: If True, normalize start to midnight

        Returns:
            DataFrame with OHLCV data, indexed by timestamp
        """
        # Determine file path
        if self.source_file:
            # Use specified source file
            file_path = os.path.join(self.data_dir, f"{self.source_file}.parquet")
        else:
            # Fallback to auto-discovery (simplified)
            file_path = self._find_parquet_file_fallback(symbol)

        logger.info(f"Loading data from: {file_path}")

        # Load parquet file
        try:
            df = pd.read_parquet(file_path)
        except Exception as e:
            raise IOError(f"Error reading parquet file {file_path}: {e}")

        # Check if DataFrame is empty
        if len(df) == 0:
            raise ValueError(f"Parquet file is empty: {file_path}")

        # Process DataFrame based on its structure
        df = self._process_dataframe(df, symbol)

        # Filter by date range if specified
        df = self._filter_by_date(df)

        # FIX #6: Normalize start if requested
        if normalize_start and len(df) > 0:
            df = self.resampler.normalize_backtest_start(df, self.filter_start)

        logger.info(f"Loaded {len(df)} rows for {symbol}")
        if len(df) > 0:
            logger.info(f"Date range: {df.index[0]} to {df.index[-1]}")

        return df

    def _process_dataframe(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """
        Process raw DataFrame to standard format.

        Args:
            df: Raw DataFrame from parquet
            symbol: Trading symbol

        Returns:
            Standardized DataFrame
        """
        # Case 1: Already has DatetimeIndex
        if isinstance(df.index, pd.DatetimeIndex):
            logger.info("DataFrame has DatetimeIndex")
            df.sort_index(inplace=True)
        # Case 2: Has timestamp column
        elif "timestamp" in df.columns:
            logger.info("Converting timestamp column to DatetimeIndex")
            # Convert timestamp (assuming milliseconds)
            if df["timestamp"].dtype in [np.int64, np.float64, int, float]:
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            else:
                df["timestamp"] = pd.to_datetime(df["timestamp"])

            df.set_index("timestamp", inplace=True)
            df.sort_index(inplace=True)
        # Case 3: Other datetime column
        else:
            # Try to find datetime columns
            datetime_cols = [
                col
                for col in df.columns
                if "time" in col.lower() or "date" in col.lower()
            ]
            if datetime_cols:
                logger.info(f"Found datetime column: {datetime_cols[0]}")
                df[datetime_cols[0]] = pd.to_datetime(df[datetime_cols[0]])
                df.set_index(datetime_cols[0], inplace=True)
                df.sort_index(inplace=True)
            else:
                raise ValueError(
                    f"No datetime column found in DataFrame. Columns: {list(df.columns)}"
                )

        # Standardize column names
        df = self._standardize_column_names(df)

        # Add symbol column if not present
        if "symbol" not in df.columns:
            df["symbol"] = symbol

        return df

    def _standardize_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Rename columns to standard OHLCV names.

        Args:
            df: DataFrame with possibly non-standard column names

        Returns:
            DataFrame with standardized column names
        """
        # Mapping of common column name variations
        column_mapping = {
            # OHLC
            "open": ["open", "o"],
            "high": ["high", "h"],
            "low": ["low", "l"],
            "close": ["close", "c", "last"],
            "volume": ["volume", "vol", "v", "quote_volume", "taker_buy_volume"],
            # Timestamp (already handled)
            "timestamp": ["timestamp", "time", "date", "datetime", "open_time"],
        }

        rename_dict = {}
        for standard_name, possible_names in column_mapping.items():
            if standard_name in df.columns:  # Already standard
                continue

            for possible in possible_names:
                if possible in df.columns:
                    rename_dict[possible] = standard_name
                    break

        if rename_dict:
            logger.info(f"Renaming columns: {rename_dict}")
            df = df.rename(columns=rename_dict)

        # Ensure we have at least close and volume
        required = ["close", "volume"]
        for col in required:
            if col not in df.columns:
                logger.warning(f"Required column '{col}' not found after renaming")

        return df

    def _filter_by_date(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter DataFrame by date range if specified in config.

        Args:
            df: Input DataFrame

        Returns:
            Filtered DataFrame
        """
        if self.filter_start or self.filter_end:
            start_date = (
                pd.to_datetime(self.filter_start) if self.filter_start else None
            )
            end_date = pd.to_datetime(self.filter_end) if self.filter_end else None

            original_len = len(df)

            if start_date:
                df = df[df.index >= start_date]
            if end_date:
                df = df[df.index <= end_date]

            if len(df) != original_len:
                logger.info(f"Filtered data: {original_len} → {len(df)} rows")

        return df

    def _find_parquet_file_fallback(self, symbol: str) -> str:
        """
        Fallback method to find parquet file (for backward compatibility).
        Only used if source_file is not specified in config.

        Args:
            symbol: Trading symbol

        Returns:
            Full path to parquet file
        """
        # Simple patterns to try
        patterns = [
            f"{symbol}_{self.timeframe}.parquet",
            f"{symbol}-{self.timeframe}.parquet",
            f"{symbol}_{self.timeframe}-*.parquet",
            f"{symbol}-{self.timeframe}-*.parquet",
            f"*.parquet",  # Any parquet file in directory
        ]

        for pattern in patterns:
            import glob

            matches = glob.glob(os.path.join(self.data_dir, pattern))
            if matches:
                # Return first match
                return matches[0]

        # List available files for error message
        available = [f for f in os.listdir(self.data_dir) if f.endswith(".parquet")]

        raise FileNotFoundError(
            f"No parquet file found for symbol '{symbol}' in {self.data_dir}\n"
            f"Available files: {available}\n"
            f"Please specify 'source_file' in config.yaml"
        )

    def load_all_symbols(self) -> Dict[str, pd.DataFrame]:
        """
        Load data for all symbols specified in config.

        Returns:
            Dictionary with symbol as key and DataFrame as value
        """
        all_data = {}

        for symbol in self.symbols:
            try:
                df = self.load_single_symbol(symbol)
                all_data[symbol] = df
            except Exception as e:
                logger.error(f"Failed to load data for {symbol}: {e}")
                raise

        return all_data

    def get_data_info(self, symbol: str = None) -> Dict:
        """
        Get information about loaded data.

        Args:
            symbol: Specific symbol or first symbol from config

        Returns:
            Dictionary with data information
        """
        if symbol is None:
            symbol = self.symbols[0]

        df = self.load_single_symbol(symbol)

        info = {
            "symbol": symbol,
            "rows": len(df),
            "columns": list(df.columns),
            "date_range": (df.index[0], df.index[-1]),
            "timeframe": self.timeframe,
            "has_ohlcv": all(
                col in df.columns for col in ["open", "high", "low", "close", "volume"]
            ),
        }

        if "close" in df.columns:
            info.update(
                {
                    "price_range": (df["close"].min(), df["close"].max()),
                    "price_avg": df["close"].mean(),
                }
            )

        return info
