import pandas as pd
import pyarrow.parquet as pq
import os
from pathlib import Path
import logging
from typing import List, Dict, Optional, Union

logger = logging.getLogger(__name__)


class DataLoader:
    """
    Loads and prepares OHLCV data from parquet files.
    Supports single or multiple symbols.
    """
    
    def __init__(self, config: Dict):
        """
        Initialize DataLoader with configuration.
        
        Args:
            config: Dictionary with configuration from config.yaml
        """
        self.config = config
        self.data_dir = config['data']['source_dir']
        self.symbols = config['data']['symbols']
        self.timeframe = config['data']['timeframe']
        self.filter_start = config['data']['filter'].get('start')
        self.filter_end = config['data']['filter'].get('end')
        
        # Validate data directory exists
        if not os.path.exists(self.data_dir):
            raise FileNotFoundError(f"Data directory not found: {self.data_dir}")
    
    def _find_parquet_file(self, symbol: str) -> str:
        """
        Recursively search for parquet files containing symbol name.
        
        Args:
            symbol: Trading symbol to search for
            
        Returns:
            Full path to the parquet file
        """
        matching_files = []
        
        for root, dirs, files in os.walk(self.data_dir):
            for file in files:
                if file.endswith('.parquet') and symbol in file:
                    # Check if timeframe matches (optional flexibility)
                    if self.timeframe in file or not self.timeframe:
                        full_path = os.path.join(root, file)
                        matching_files.append(full_path)
        
        if not matching_files:
            raise FileNotFoundError(
                f"No parquet file found for symbol '{symbol}' in {self.data_dir} (searched recursively)\n"
                f"Expected file containing '{symbol}' and '.parquet' extension\n"
                f"Please run: python scripts/download_data.py"
            )
        
        # If multiple files match, use the first one
        if len(matching_files) > 1:
            logger.warning(f"Multiple files found for {symbol}:")
            for f in matching_files:
                logger.warning(f"  - {f}")
            logger.warning(f"Using: {matching_files[0]}")
            
            # Try to find one with exact timeframe match first
            exact_matches = [f for f in matching_files if self.timeframe in f]
            if exact_matches:
                return exact_matches[0]
        
        return matching_files[0]
    
    def load_single_symbol(self, symbol: str) -> pd.DataFrame:
        """
        Load data for a single symbol.
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            
        Returns:
            DataFrame with OHLCV data, indexed by timestamp
        """
        # Find the parquet file (recursively)
        file_path = self._find_parquet_file(symbol)
        
        logger.info(f"Loading data from: {file_path}")
        
        # Load parquet file
        try:
            df = pd.read_parquet(file_path)
        except Exception as e:
            raise IOError(f"Error reading parquet file {file_path}: {e}")
        
        # Check if DataFrame is empty
        if len(df) == 0:
            raise ValueError(f"Parquet file is empty: {file_path}")
        
        # CASO 1: DataFrame ha già DatetimeIndex come nel tuo file
        if isinstance(df.index, pd.DatetimeIndex) and df.index.name is not None:
            logger.info(f"DataFrame has DatetimeIndex: {df.index.name}")
            # Already has datetime index, ensure it's sorted
            df.sort_index(inplace=True)
            
            # Try to identify OHLCV columns
            ohlcv_columns = self._identify_ohlcv_columns(df.columns)
            
            # Rename columns if needed
            rename_dict = {}
            for standard_name, possible_names in ohlcv_columns.items():
                for possible in possible_names:
                    if possible in df.columns:
                        rename_dict[possible] = standard_name
                        break
            
            if rename_dict:
                df = df.rename(columns=rename_dict)
                logger.info(f"Renamed columns: {rename_dict}")
        
        # CASO 2: Colonna timestamp separata (come nel tuo file c'è sia indice che colonna)
        elif 'timestamp' in df.columns:
            # Convert timestamp column from milliseconds to datetime
            if df['timestamp'].dtype in [np.int64, np.float64, int, float]:
                logger.info(f"Converting timestamp from milliseconds to datetime")
                # Assuming timestamp is in milliseconds
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            else:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Set as index if not already
            if not isinstance(df.index, pd.DatetimeIndex):
                df.set_index('timestamp', inplace=True)
                df.sort_index(inplace=True)
            
            # Identify and rename OHLCV columns
            ohlcv_columns = self._identify_ohlcv_columns(df.columns)
            rename_dict = {}
            
            for standard_name, possible_names in ohlcv_columns.items():
                for possible in possible_names:
                    if possible in df.columns:
                        rename_dict[possible] = standard_name
                        break
            
            if rename_dict:
                df = df.rename(columns=rename_dict)
                logger.info(f"Renamed columns: {rename_dict}")
        
        # CASO 3: Nessun timestamp trovato
        else:
            raise ValueError(
                f"No timestamp column or DatetimeIndex found in {file_path}\n"
                f"Columns: {list(df.columns)}\n"
                f"Index type: {type(df.index).__name__}"
            )
        
        # Ensure we have required columns after renaming
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            # Try to find alternative volume columns
            volume_alternatives = ['quote_volume', 'taker_buy_volume', 'vol']
            for alt in volume_alternatives:
                if alt in df.columns and 'volume' not in df.columns:
                    df['volume'] = df[alt]
                    logger.info(f"Using {alt} as volume column")
                    break
            
            # Re-check missing columns
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise ValueError(
                    f"Missing required columns after renaming: {missing_columns}\n"
                    f"Available columns: {list(df.columns)}"
                )
        
        # Add symbol column if not present
        if 'symbol' not in df.columns:
            df['symbol'] = symbol
        
        # Filter by date range if specified
        if self.filter_start or self.filter_end:
            start_date = pd.to_datetime(self.filter_start) if self.filter_start else None
            end_date = pd.to_datetime(self.filter_end) if self.filter_end else None
            
            if start_date:
                df = df[df.index >= start_date]
            if end_date:
                df = df[df.index <= end_date]
        
        logger.info(f"Loaded {len(df)} rows for {symbol} from {os.path.basename(file_path)}")
        logger.info(f"Date range: {df.index[0]} to {df.index[-1]}")
        logger.info(f"Columns after processing: {list(df.columns)}")
        
        return df
    
    def _identify_ohlcv_columns(self, columns: List[str]) -> Dict[str, List[str]]:
        """
        Identify OHLCV columns from various naming conventions.
        
        Returns:
            Dictionary mapping standard names to possible column names
        """
        # Common naming conventions (Binance, Kraken, Bybit, etc.)
        return {
            'open': ['open', 'o'],
            'high': ['high', 'h'],
            'low': ['low', 'l'],
            'close': ['close', 'c'],
            'volume': ['volume', 'vol', 'v', 'quote_volume', 'taker_buy_volume'],
            'timestamp': ['timestamp', 'time', 'date', 'datetime', 'open_time']
        }
    
    def _find_parquet_file(self, symbol: str) -> str:
        """
        Recursively search for parquet files containing symbol name.
        
        Args:
            symbol: Trading symbol to search for
            
        Returns:
            Full path to the parquet file
        """
        matching_files = []
        
        # Try exact match first (most common cases)
        possible_filenames = [
            f"{symbol}_{self.timeframe}.parquet",
            f"{symbol}-{self.timeframe}.parquet",
            f"{symbol.lower()}_{self.timeframe}.parquet",
            f"{symbol.lower()}-{self.timeframe}.parquet",
        ]
        
        for filename in possible_filenames:
            file_path = os.path.join(self.data_dir, filename)
            if os.path.exists(file_path):
                logger.info(f"Found exact match: {file_path}")
                return file_path
        
        # If no exact match, search recursively
        for root, dirs, files in os.walk(self.data_dir):
            for file in files:
                if file.endswith('.parquet'):
                    # Case-insensitive search
                    if symbol.lower() in file.lower():
                        full_path = os.path.join(root, file)
                        matching_files.append(full_path)
        
        if not matching_files:
            # List available files for debugging
            available_files = []
            for root, dirs, files in os.walk(self.data_dir):
                for file in files:
                    if file.endswith('.parquet'):
                        available_files.append(os.path.join(root, file))
            
            raise FileNotFoundError(
                f"No parquet file found for symbol '{symbol}' in {self.data_dir}\n"
                f"Searched for files containing '{symbol}' (case-insensitive)\n"
                f"Available parquet files:\n" + 
                "\n".join(f"  - {f}" for f in available_files[:10]) +
                (f"\n  ... and {len(available_files)-10} more" if len(available_files) > 10 else "")
            )
        
        # If multiple files match, use the most recent one
        if len(matching_files) > 1:
            logger.warning(f"Multiple files found for {symbol}:")
            for f in matching_files:
                file_time = os.path.getmtime(f)
                logger.warning(f"  - {f} (modified: {pd.Timestamp(file_time, unit='s')})")
            
            # Sort by modification time (newest first)
            matching_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            logger.warning(f"Using most recent: {matching_files[0]}")
        
        return matching_files[0]
    
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
    
    def validate_data(self, df: pd.DataFrame) -> bool:
        """
        Validate data quality and integrity.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            True if data is valid
        """
        # Check for NaN values in critical columns
        critical_columns = ['open', 'high', 'low', 'close', 'volume']
        
        # Only check columns that exist
        existing_critical = [col for col in critical_columns if col in df.columns]
        
        if existing_critical:
            nan_counts = df[existing_critical].isna().sum()
            
            if nan_counts.any():
                logger.warning(f"NaN values found: {nan_counts.to_dict()}")
                # For Phase 1, we'll fill forward small gaps
                df[existing_critical] = df[existing_critical].ffill()
        
        # Check for duplicates
        duplicates = df.index.duplicated().sum()
        if duplicates > 0:
            logger.warning(f"Found {duplicates} duplicate timestamps. Removing duplicates.")
            df = df[~df.index.duplicated(keep='first')]
        
        # Check for gaps in timeline (optional, just log)
        if len(df) > 1:
            time_diff = df.index.to_series().diff().dropna()
            expected_freq = self._get_expected_frequency()
            
            if expected_freq:
                gaps = time_diff[time_diff > pd.Timedelta(expected_freq) * 1.5]
                if len(gaps) > 0:
                    logger.info(f"Found {len(gaps)} gaps in timeline")
        
        return True
    
    def _get_expected_frequency(self) -> Optional[str]:
        """
        Get expected frequency based on timeframe.
        
        Returns:
            Pandas frequency string or None
        """
        tf_mapping = {
            '1m': '1min',
            '5m': '5min',
            '15m': '15min',
            '1h': '1H',
            '4h': '4H',
            '1d': '1D',
        }
        return tf_mapping.get(self.timeframe)
    
    def get_sample_data(self, symbol: str = None, num_rows: int = 100) -> pd.DataFrame:
        """
        Get a small sample of data for testing.
        
        Args:
            symbol: Specific symbol or first symbol from config
            num_rows: Number of rows to return
            
        Returns:
            DataFrame with sample data
        """
        if symbol is None:
            symbol = self.symbols[0]
        
        df = self.load_single_symbol(symbol)
        return df.head(num_rows).copy()

    def debug_file_structure(self, max_files: int = 20):
        """
        Debug method to show file structure.
        
        Args:
            max_files: Maximum number of files to show
        """
        print(f"\n📁 Debug file structure in: {self.data_dir}")
        print("="*60)
        
        parquet_files = []
        
        for root, dirs, files in os.walk(self.data_dir):
            level = root.replace(self.data_dir, '').count(os.sep)
            indent = ' ' * 2 * level
            print(f"{indent}{os.path.basename(root)}/")
            
            subindent = ' ' * 2 * (level + 1)
            for file in sorted(files):
                if file.endswith('.parquet'):
                    full_path = os.path.join(root, file)
                    file_size = os.path.getsize(full_path) / 1024
                    print(f"{subindent}{file} ({file_size:.1f} KB)")
                    parquet_files.append(full_path)
        
        print(f"\nFound {len(parquet_files)} parquet files")
        
        # Show first few files with details
        for i, file_path in enumerate(parquet_files[:max_files], 1):
            print(f"\n{i}. {os.path.basename(file_path)}")
            try:
                df = pd.read_parquet(file_path)
                print(f"   Rows: {len(df):,}, Columns: {len(df.columns)}")
                print(f"   Index: {type(df.index).__name__}")
                print(f"   Columns: {list(df.columns)[:8]}...") if len(df.columns) > 8 else print(f"   Columns: {list(df.columns)}")
            except Exception as e:
                print(f"   Error reading: {e}")


if __name__ == "__main__":
    # Test the data loader
    import yaml
    
    # Load test config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,  # Changed to DEBUG for more details
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    try:
        loader = DataLoader(config)
        
        # Debug file structure first
        print("\n=== Debug File Structure ===")
        loader.debug_file_structure(max_files=5)
        
        print("\n" + "="*60)
        print("=== Testing DataLoader ===")
        print("="*60)
        
        # Test loading single symbol
        df = loader.load_single_symbol("BTCUSDT")
        
        print(f"\n✅ SUCCESS! Data loaded successfully")
        print(f"\nData shape: {df.shape}")
        print(f"Index: {df.index.name} ({type(df.index).__name__})")
        print(f"Columns: {list(df.columns)}")
        
        print(f"\nFirst 3 rows:")
        print(df[['open', 'high', 'low', 'close', 'volume']].head(3))
        
        print(f"\nLast 3 rows:")
        print(df[['open', 'high', 'low', 'close', 'volume']].tail(3))
        
        print(f"\n📊 Summary for BTCUSDT:")
        print(f"Total rows: {len(df):,}")
        print(f"Date range: {df.index[0]} to {df.index[-1]}")
        print(f"Days: {(df.index[-1] - df.index[0]).days + 1}")
        
        if 'close' in df.columns:
            print(f"Close price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
            print(f"Average daily candles: {len(df) / ((df.index[-1] - df.index[0]).days + 1):.0f}")
        
        # Validate data
        print(f"\n🔍 Validating data...")
        loader.validate_data(df)
        print("✅ Data validation passed")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
        print("\n🔧 Troubleshooting tips:")
        print("1. Check the actual file location and structure")
        print("2. Verify file permissions")
        print("3. Try loading the file directly with pandas:")
        print("   import pandas as pd")
        print("   df = pd.read_parquet('data/raw/BTCUSDT_1m.parquet/BTCUSDT-1m-2025-10.parquet')")
        print("   print(df.head())")