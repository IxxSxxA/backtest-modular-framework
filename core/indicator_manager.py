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

    NEW: Auto-discovers indicators from strategy declarations.
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
        self.config = config

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

    def generate_column_name(self, indicator_config: Dict[str, Any]) -> str:
        """
        Auto-generate unique column name from indicator config.

        Strategy: Use indicator name + all significant parameters

        Examples:
            {name: "ema", period: 54} → "ema_54"
            {name: "atr", period: 21, method: "wilder"} → "atr_21_wilder"
            {name: "cvdratio", cumulative_period_minutes: 1, signal_period_minutes: 15}
                → "cvd_ratio_1_15"

        Args:
            indicator_config: Config dict with name and params

        Returns:
            Unique column name string
        """
        name = indicator_config["name"]

        # Special handling for readability
        if name == "cvdratio":
            name = "cvd_ratio"  # More readable

        # Extract parameters (everything except 'name')
        params = {k: v for k, v in indicator_config.items() if k != "name"}

        # Build suffix from significant parameters
        parts = []

        # Common parameters with abbreviations
        param_order = [
            "period",
            "cumulative_period_minutes",
            "signal_period_minutes",
            "multiplier",
            "method",
            "std",
            "use_quote",
        ]

        for key in param_order:
            if key in params:
                value = params[key]

                # Format based on parameter type
                if key == "cumulative_period_minutes":
                    parts.append(str(value))
                elif key == "signal_period_minutes":
                    parts.append(str(value))
                elif key == "use_quote":
                    # Skip use_quote=False (default), only show if True
                    if value:
                        parts.append("quote")
                elif key == "method":
                    # Only add method if not default
                    if value != "wilder":  # 'wilder' is common default
                        parts.append(str(value))
                else:
                    # Standard format: just the value
                    parts.append(str(value))

        # Add any remaining parameters not in param_order
        for key, value in sorted(params.items()):
            if key not in param_order:
                parts.append(f"{key}_{value}")

        # Combine into column name
        if parts:
            column_name = f"{name}_{'_'.join(parts)}"
        else:
            column_name = name

        logger.debug(f"Generated column name: {column_name} from {indicator_config}")

        return column_name

    def calculate_indicator(
        self,
        data: pd.DataFrame,
        indicator_config: Dict[str, Any],
        symbol: str,
        strategy_tf: str,
    ) -> tuple[pd.Series, str]:
        """
        Calculate indicator based on configuration.

        Args:
            data: DataFrame with OHLCV data (already resampled to strategy_tf)
            indicator_config: Config dict with name and parameters
            symbol: Trading symbol
            strategy_tf: Strategy timeframe (e.g., "5m")

        Returns:
            Tuple of (Series with indicator values, column_name)
        """
        indicator_name = indicator_config["name"]
        params = indicator_config.copy()  # Copy to avoid mutation
        params.pop("name")  # Remove name, keep only actual parameters

        # Generate column name
        column_name = self.generate_column_name(indicator_config)

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

        return values, column_name

    def collect_indicators_from_strategies(
        self, entry, exit, risk, extra_indicators: List[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Collect all indicators needed by strategies + extra indicators.
        Automatically deduplicates identical indicator configs.

        Args:
            entry: Entry strategy instance
            exit: Exit strategy instance
            risk: Risk manager instance
            extra_indicators: Optional list of extra indicator configs for plotting

        Returns:
            List of unique indicator configurations
        """
        all_indicators = []

        # Collect from entry strategy
        if hasattr(entry, "indicators") and entry.indicators:
            all_indicators.extend(entry.indicators)
            logger.debug(f"Entry strategy needs {len(entry.indicators)} indicators")

        # Collect from exit strategy
        if hasattr(exit, "indicators") and exit.indicators:
            all_indicators.extend(exit.indicators)
            logger.debug(f"Exit strategy needs {len(exit.indicators)} indicators")

        # Collect from risk manager
        if hasattr(risk, "indicators") and risk.indicators:
            all_indicators.extend(risk.indicators)
            logger.debug(f"Risk manager needs {len(risk.indicators)} indicators")

        # Add extra indicators for plotting/analysis
        if extra_indicators:
            all_indicators.extend(extra_indicators)
            logger.debug(f"Extra indicators for plotting: {len(extra_indicators)}")

        # Deduplicate based on config content
        unique_indicators = []
        seen = set()

        for config in all_indicators:
            # Create hashable key from config
            config_key = self._config_to_key(config)

            if config_key not in seen:
                seen.add(config_key)
                unique_indicators.append(config)

        logger.info(
            f"Collected {len(all_indicators)} indicators, "
            f"{len(unique_indicators)} unique after deduplication"
        )

        return unique_indicators

    def _config_to_key(self, config: Dict[str, Any]) -> str:
        """
        Convert indicator config to hashable key for deduplication.

        Args:
            config: Indicator configuration dict

        Returns:
            Hashable string key
        """
        import json

        # Sort keys for consistent hashing
        return json.dumps(config, sort_keys=True)

    def calculate_from_strategies(
        self,
        data: pd.DataFrame,
        entry,
        exit,
        risk,
        symbol: str,
        strategy_tf: str,
        extra_indicators: List[Dict] = None,
    ) -> pd.DataFrame:
        """
        Calculate all indicators needed by strategies (auto-discovery).

        This is the main entry point replacing calculate_all_indicators().

        Args:
            data: Original OHLCV DataFrame (already resampled to strategy_tf)
            entry: Entry strategy instance
            exit: Exit strategy instance
            risk: Risk manager instance
            symbol: Trading symbol
            strategy_tf: Strategy timeframe
            extra_indicators: Optional extra indicators for plotting

        Returns:
            DataFrame with original data + all indicator columns
        """
        # Step 1: Collect all needed indicators
        indicator_configs = self.collect_indicators_from_strategies(
            entry, exit, risk, extra_indicators
        )

        if not indicator_configs:
            logger.warning("No indicators to calculate!")
            return data.copy()

        # Step 2: Calculate each unique indicator
        result_df = data.copy()

        for config in indicator_configs:
            try:
                indicator_name = config["name"]

                logger.info(f"Calculating {indicator_name} on {strategy_tf}")

                # Calculate (uses caching)
                values, column_name = self.calculate_indicator(
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
