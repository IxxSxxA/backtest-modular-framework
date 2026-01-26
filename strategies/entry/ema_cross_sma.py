# strategies/entry/ema_cross_sma.py

from .base_entry import BaseEntryStrategy
import logging

logger = logging.getLogger(__name__)


class EMACrossSMA(BaseEntryStrategy):
    """
    Entry strategy: Enter when EMA crosses above SMA.

    Config example:
    ```yaml
    entry:
      name: "ema_cross_sma"
      params: {}  # No strategy-specific params needed
      indicators:
        - name: "ema"
          period: 59
        - name: "sma"
          period: 200
    ```

    Column names are auto-generated: ema_59, sma_200
    """

    def __init__(self, params: dict = None):
        super().__init__(params)

        # Extract indicator configs (already stored in self.indicators by base class)
        # Build column names for easy access
        self.ema_column = None
        self.sma_column = None

        for ind in self.indicators:
            if ind["name"] == "ema":
                period = ind.get("period")
                self.ema_column = f"ema_{period}"
            elif ind["name"] == "sma":
                period = ind.get("period")
                self.sma_column = f"sma_{period}"

        if not self.ema_column or not self.sma_column:
            raise ValueError(
                f"{self.name} requires 'ema' and 'sma' indicators in config! "
                f"Got: {self.indicators}"
            )

        logger.info(
            f"Initialized EMACrossSMA: "
            f"Columns: {self.ema_column}, {self.sma_column}"
        )

    def should_enter(self, data) -> bool:
        """Check for EMA crossover above SMA."""
        # Check if we have required indicators
        required = [self.ema_column, self.sma_column]
        for col in required:
            if col not in data:
                logger.error(f"Required indicator '{col}' not found in data")
                return False

        try:
            # Current values
            current_ema = data[self.ema_column][0]
            current_sma = data[self.sma_column][0]

            # Previous values (for crossover detection)
            prev_ema = data[self.ema_column][-1]
            prev_sma = data[self.sma_column][-1]

            # Crossover detection: EMA crosses above SMA
            if (prev_ema <= prev_sma) and (current_ema > current_sma):
                logger.info(
                    f"Entry signal: EMA crossed above SMA - "
                    f"{prev_ema:.4f}≤{prev_sma:.4f} → {current_ema:.4f}>{current_sma:.4f}"
                )
                return True

            return False

        except (IndexError, KeyError) as e:
            logger.warning(f"Data access error in should_enter: {e}")
            return False
