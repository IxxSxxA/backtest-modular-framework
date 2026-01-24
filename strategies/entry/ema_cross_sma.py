# strategies/entry/ema_cross_sma.py

from .base_entry import BaseEntryStrategy
import logging

logger = logging.getLogger(__name__)


class EMACrossSMA(BaseEntryStrategy):
    """
    Entry strategy: Enter when EMA crosses above SMA.

    Parameters:
        ema_period: Period for EMA (default: 59)
        sma_period: Period for SMA (default: 200)
    """

    def __init__(self, params: dict = None):
        super().__init__(params)

        # Extract parameters
        self.ema_period = self.params.get("ema_period", 59)
        self.sma_period = self.params.get("sma_period", 200)

        # Column names (must match config.yaml)
        self.ema_column = f"ema_{self.ema_period}"
        self.sma_column = f"sma_{self.sma_period}"

        logger.info(
            f"Initialized EMACrossSMA: "
            f"EMA({self.ema_period}), SMA({self.sma_period})"
        )

    def should_enter(self, data) -> bool:
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
                    f"Entry signal: EMA({self.ema_period}) crossed above SMA({self.sma_period}) - "
                    f"{prev_ema:.4f}≤{prev_sma:.4f} → {current_ema:.4f}>{current_sma:.4f}"
                )
                return True

            return False

        except (IndexError, KeyError) as e:
            logger.warning(f"Data access error in should_enter: {e}")
            return False

    def get_required_indicators(self) -> list:
        """Return required indicator names."""
        return [self.ema_column, self.sma_column]
