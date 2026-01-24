# strategies/entry/ema_cross_sma_cvd.py

from .base_entry import BaseEntryStrategy
import logging

logger = logging.getLogger(__name__)


class EMACrossSMACVD(BaseEntryStrategy):
    """
    Entry strategy: EMA crosses above SMA + CVD Ratio confirmation.

    Simple CVD Ratio logic: (BuyVolume - SellVolume) / TotalVolume * 100
    Range: -100 (all selling) to +100 (all buying)

    Parameters:
        ema_period: Period for EMA (default: 59)
        sma_period: Period for SMA (default: 200)
        cvd_window_minutes: Rolling window for CVD ratio (default: 15)
        cvd_ratio_threshold: Minimum CVD ratio for entry (default: 20.0)
                           Entra long se ratio > threshold (es: > +20%)
    """

    def __init__(self, params: dict = None):
        super().__init__(params)

        # Extract parameters
        self.ema_period = self.params.get("ema_period", 59)
        self.sma_period = self.params.get("sma_period", 200)
        self.cvd_window_minutes = int(self.params.get("cvd_window_minutes", 15))
        self.cvd_ratio_threshold = float(self.params.get("cvd_ratio_threshold", 20.0))

        # Column names (must match config.yaml)
        self.ema_column = f"ema_{self.ema_period}"
        self.sma_column = f"sma_{self.sma_period}"
        self.cvd_column = f"cvd_ratio_{self.cvd_window_minutes}m"

        logger.info(
            f"Initialized EMACrossSMACVDRatio: "
            f"EMA({self.ema_period}) × SMA({self.sma_period}) + "
            f"CVD Ratio({self.cvd_window_minutes}min, threshold: +{self.cvd_ratio_threshold}%)"
        )
        logger.info(
            f"Interpretation: Enter LONG when CVD Ratio > {self.cvd_ratio_threshold}% "
            f"(meaning {self.cvd_ratio_threshold}% of recent volume is net buying)"
        )

    def should_enter(self, data) -> bool:
        """
        Check entry conditions:
        1. EMA crosses above SMA (bullish crossover)
        2. CVD Ratio > threshold (recent buying pressure)
        """
        # Check if we have required indicators
        required = [self.ema_column, self.sma_column, self.cvd_column]
        for col in required:
            if col not in data:
                logger.error(f"Required indicator '{col}' not found in data")
                return False

        try:
            # 1. Check EMA/SMA crossover
            current_ema = data[self.ema_column][0]
            current_sma = data[self.sma_column][0]
            prev_ema = data[self.ema_column][-1]
            prev_sma = data[self.sma_column][-1]

            # Bullish crossover: EMA crosses above SMA
            has_crossover = (prev_ema <= prev_sma) and (current_ema > current_sma)

            if not has_crossover:
                return False

            logger.debug(
                f"Crossover detected: EMA {prev_ema:.4f}≤{prev_sma:.4f} → "
                f"{current_ema:.4f}>{current_sma:.4f}"
            )

            # 2. Check CVD Ratio
            current_cvd_ratio = data[self.cvd_column][0]

            # Entra long se CVD ratio indica buying pressure
            if current_cvd_ratio > self.cvd_ratio_threshold:
                logger.info(
                    f"✅ ENTRY: EMA×SMA crossover + CVD Ratio CONFIRMED "
                    f"(ratio: {current_cvd_ratio:+.1f}% > {self.cvd_ratio_threshold:+.1f}%)"
                )
                return True
            else:
                logger.info(
                    f"⏸️  NO ENTRY: EMA×SMA crossover but CVD Ratio WEAK "
                    f"(ratio: {current_cvd_ratio:+.1f}% ≤ {self.cvd_ratio_threshold:+.1f}%)"
                )
                return False

        except (IndexError, KeyError) as e:
            logger.warning(f"Data access error in should_enter: {e}")
            return False

    def get_required_indicators(self) -> list:
        """Return required indicator names."""
        return [self.ema_column, self.sma_column, self.cvd_column]
