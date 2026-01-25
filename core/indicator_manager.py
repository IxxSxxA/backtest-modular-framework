import pandas as pd
import importlib
import inspect
import pkgutil
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from indicators.base_calculator import BaseCalculator

logger = logging.getLogger(__name__)


class IndicatorManager:
    """
    Manages indicator calculation and caching.
    Discovers and loads all indicator calculators automatically.
    """

    def __init__(
        self, indicators_dir: str = "indicators", config: Dict[str, Any] = None
    ):
        """
        Initialize indicator manager.

        Args:
            indicators_dir: Directory containing indicator calculators
            config: Configuration dictionary (needed for CVD file path)
        """
        self.indicators_dir = Path(indicators_dir)
        self.calculators = {}
        self.config = config  # Store config

        # Discover and load all calculators
        self._discover_calculators()

    def _discover_calculators(self):
        """Discover all indicator calculator classes."""
        try:
            # Import indicators module
            import indicators

            # Get all modules in indicators package
            package_path = indicators.__path__

            for _, module_name, is_pkg in pkgutil.iter_modules(package_path):
                if is_pkg or module_name == "base_calculator":
                    continue

                try:
                    # Import the module
                    module = importlib.import_module(f"indicators.{module_name}")

                    # Find all classes that inherit from BaseCalculator
                    for name, obj in inspect.getmembers(module):
                        if (
                            inspect.isclass(obj)
                            and issubclass(obj, BaseCalculator)
                            and obj != BaseCalculator
                        ):

                            # Extract indicator name from class (e.g., SMACalculator -> sma)
                            indicator_name = obj.__name__.replace(
                                "Calculator", ""
                            ).lower()
                            self.calculators[indicator_name] = obj

                            logger.debug(
                                f"Discovered indicator: {indicator_name} -> {obj.__name__}"
                            )

                except Exception as e:
                    logger.warning(
                        f"Failed to load indicator module {module_name}: {e}"
                    )

        except Exception as e:
            logger.error(f"Failed to discover indicators: {e}")

    def get_calculator(self, indicator_name: str) -> BaseCalculator:
        """
        Get calculator instance for indicator.

        Args:
            indicator_name: Name of indicator (e.g., 'sma', 'ema')

        Returns:
            Calculator instance

        Raises:
            ValueError if indicator not found
        """
        if indicator_name not in self.calculators:
            available = list(self.calculators.keys())
            raise ValueError(
                f"Indicator '{indicator_name}' not found. "
                f"Available indicators: {available}\n"
                f"Create file: indicators/{indicator_name}_calculator.py"
            )

        return self.calculators[indicator_name]

    def calculate_indicator(
        self,
        data: pd.DataFrame,
        indicator_config: Dict[str, Any],
        symbol: str,
        strategy_tf: str,
    ) -> pd.Series:
        """
        Calculate indicator based on configuration.

        Args:
            data: DataFrame with OHLCV data (already resampled to strategy_tf)
            indicator_config: Config dict with name, params, column
            symbol: Trading symbol
            strategy_tf: Strategy timeframe (e.g., "5m")

        Returns:
            Series with indicator values
        """
        indicator_name = indicator_config["name"]
        params = indicator_config.get("params", {}).copy()  # Copy to avoid mutation
        column_name = indicator_config.get("column")

        # Get calculator class
        CalculatorClass = self.calculators.get(indicator_name)
        if CalculatorClass is None:
            raise ValueError(f"Indicator '{indicator_name}' not implemented.")

        # Create calculator instance
        calculator = CalculatorClass(symbol=symbol, timeframe=strategy_tf)

        # Special handling for CVD: pass data file path
        if indicator_name == "cvdratio":
            if self.config is None:
                raise ValueError(
                    "Config required for CVD calculator but not provided to IndicatorManager!"
                )

            data_config = self.config["data"]
            source_dir = data_config["source_dir"]
            source_file = data_config["source_file"]
            file_path = Path(source_dir) / source_file

            if not file_path.suffix:
                file_path = file_path.with_suffix(".parquet")

            # Add to params
            params["data_file_path"] = str(file_path)

            logger.debug(f"CVD data file path: {file_path}")

        # Calculate with caching
        values = calculator.calculate_with_cache(data, params, column_name)

        return values

    def calculate_all_indicators(
        self,
        data: pd.DataFrame,
        indicator_configs: List[Dict[str, Any]],
        symbol: str,
        strategy_tf: str,
    ) -> pd.DataFrame:
        """
        Calculate multiple indicators and add them to the DataFrame.

        Args:
            data: Original OHLCV DataFrame (already resampled to strategy_tf)
            indicator_configs: List of indicator configurations from config.yaml
            symbol: Trading symbol
            strategy_tf: Strategy timeframe (from config.strategy.timeframe)

        Returns:
            DataFrame with original data + indicator columns
        """
        result_df = data.copy()

        for config in indicator_configs:
            if "params" not in config:
                config["params"] = {}

            try:
                indicator_name = config["name"]
                column_name = config.get("column", indicator_name)

                logger.info(
                    f"Calculating {indicator_name} on {strategy_tf} → '{column_name}'"
                )

                # Calculate (uses caching)
                values = self.calculate_indicator(
                    data=data,
                    indicator_config=config,
                    symbol=symbol,
                    strategy_tf=strategy_tf,
                )

                # Add to DataFrame
                result_df[column_name] = values

                logger.info(f"✅ Added column '{column_name}' to DataFrame")

            except Exception as e:
                logger.error(f"Failed to calculate indicator {config}: {e}")
                raise

        return result_df

    def list_available_indicators(self) -> List[str]:
        """Return list of available indicator names."""
        return sorted(list(self.calculators.keys()))
