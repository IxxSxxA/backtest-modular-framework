import pandas as pd
import importlib
import inspect
import pkgutil
from pathlib import Path
from typing import Dict, List, Any, Optional  # Aggiungi questa riga
import logging
from indicators.base_calculator import BaseCalculator

logger = logging.getLogger(__name__)


class IndicatorManager:
    """
    Manages indicator calculation and caching.
    Discovers and loads all indicator calculators automatically.
    """
    
    def __init__(self, indicators_dir: str = "indicators"):
        """
        Initialize indicator manager.
        
        Args:
            indicators_dir: Directory containing indicator calculators
        """
        self.indicators_dir = Path(indicators_dir)
        self.calculators = {}
        
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
                if is_pkg or module_name == 'base_calculator':
                    continue
                
                try:
                    # Import the module
                    module = importlib.import_module(f"indicators.{module_name}")
                    
                    # Find all classes that inherit from BaseCalculator
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and 
                            issubclass(obj, BaseCalculator) and 
                            obj != BaseCalculator):
                            
                            # Extract indicator name from class (e.g., SMACalculator -> sma)
                            indicator_name = obj.__name__.replace('Calculator', '').lower()
                            self.calculators[indicator_name] = obj
                            
                            logger.debug(f"Discovered indicator: {indicator_name} -> {obj.__name__}")
                            
                except Exception as e:
                    logger.warning(f"Failed to load indicator module {module_name}: {e}")
        
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
    
    def calculate_indicator(self, data: pd.DataFrame, indicator_config: Dict[str, Any], 
                        symbol: str, timeframe: str) -> pd.Series:

        """
        Calculate indicator based on configuration.
        
        Args:
            data: OHLCV DataFrame
            indicator_config: Dictionary with indicator configuration
                Example: {'name': 'sma', 'params': {'period': 20}, 'tf': '1m', 'column': 'sma_20'}
            symbol: Trading symbol
            timeframe: Data timeframe
            
        Returns:
            Series with indicator values
        """
        indicator_name = indicator_config['name']
        params = indicator_config.get('params', {})
        
        # Get calculator
        CalculatorClass = self.calculators.get(indicator_name)
        if CalculatorClass is None:
            raise ValueError(f"Indicator '{indicator_name}' not implemented.")
        
        calculator = CalculatorClass(symbol=symbol, timeframe=timeframe)
        
        # Calculate with caching
        values = calculator.calculate_with_cache(data, params)
        
        # 🔍 DEBUG 1
        print(f"🔍 After calculate_with_cache:")
        print(f"   values.name = {values.name}")
        
        # Rename series if column name specified
        column_name = indicator_config.get('column')
        
        # 🔍 DEBUG 2
        print(f"🔍 column_name from config = {column_name}")
        
        if column_name:
            values.name = column_name
            # 🔍 DEBUG 3
            print(f"🔍 After rename: values.name = {values.name}")
        
        return values
    
    def calculate_all_indicators(
        self,
        data: pd.DataFrame,
        indicator_configs: List[Dict[str, Any]],
        symbol: str,
        timeframe: str
    ) -> pd.DataFrame:
        """
        Calculate multiple indicators and add them to the DataFrame.
        
        Args:
            data: Original OHLCV DataFrame
            indicator_configs: List of indicator configurations
            symbol: Trading symbol
            timeframe: Data timeframe
            
        Returns:
            DataFrame with original data + indicator columns
        """
        result_df = data.copy()
        
        for config in indicator_configs:
            try:
                indicator_name = config['name']
                logger.info(f"Calculating indicator: {indicator_name} for {symbol}")
                
                values = self.calculate_indicator(data, config, symbol, timeframe)
                
                # 🔍 DEBUG COMPLETO
                column_name = config.get('column', indicator_name)
                print(f"\n{'='*60}")
                print(f"🔍 ADDING INDICATOR TO DATAFRAME:")
                print(f"{'='*60}")
                print(f"Indicator name: {indicator_name}")
                print(f"Column name from config: {config.get('column')}")
                print(f"Column name final: {column_name}")
                print(f"values.name: {values.name}")
                print(f"values shape: {values.shape}")
                print(f"values index type: {type(values.index)}")
                print(f"result_df index type: {type(result_df.index)}")
                print(f"Index match: {values.index.equals(result_df.index)}")
                print(f"\nBEFORE: result_df.shape = {result_df.shape}")
                print(f"BEFORE: result_df.columns = {list(result_df.columns)}")
                
                # Aggiungi colonna
                result_df[column_name] = values
                
                print(f"\nAFTER: result_df.shape = {result_df.shape}")
                print(f"AFTER: result_df.columns = {list(result_df.columns)}")
                print(f"Column '{column_name}' in DataFrame: {column_name in result_df.columns}")
                
                if column_name in result_df.columns:
                    print(f"✅ SUCCESS! First 3 values: {result_df[column_name].head(3).tolist()}")
                else:
                    print(f"❌ FAILED! Column not added!")
                
                print(f"{'='*60}\n")
                
            except Exception as e:
                logger.error(f"Failed to calculate indicator {config.get('name', 'unknown')}: {e}")
                raise
        
        return result_df
    
    def list_available_indicators(self) -> List[str]:
        """Return list of available indicator names."""
        return sorted(list(self.calculators.keys()))