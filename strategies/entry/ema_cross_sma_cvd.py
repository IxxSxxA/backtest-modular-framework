# strategies/entry/ema_cross_sma_cvd.py

from typing import Dict, Any, Union
import logging
from core.data_window import DataWindow
from .base_entry import BaseEntryStrategy

logger = logging.getLogger(__name__)


class EMACrossSMACVD(BaseEntryStrategy):
    """
    Entry strategy: EMA cross SMA + CVD confirmation.

    LONG Signal:
        - EMA > SMA (bullish trend)
        - CVD Ratio > long_threshold (buying pressure)

    SHORT Signal:
        - EMA < SMA (bearish trend)
        - CVD Ratio < short_threshold (selling pressure)

    Config example:
    ```yaml
    entry:
      name: "ema_cross_sma_cvd"
      params:
        long_threshold: 50.0   # CVD ratio threshold for LONG entries
        short_threshold: 50.0  # CVD ratio threshold for SHORT entries
      indicators:
        - name: "ema"
          period: 54
        - name: "sma"
          period: 200
        - name: "cvdratio"
          cumulative_period_minutes: 1
          signal_period_minutes: 15
          use_quote: false
    ```

    CVD Ratio Range: 0 (all selling) to 100 (all buying)
    """

    def __init__(self, params: Dict[str, Any]):
        super().__init__(params)

        # Extract strategy-specific params
        self.long_threshold = params.get("long_threshold", 50.0)
        self.short_threshold = params.get("short_threshold", 50.0)

        # Build column names from indicator configs
        self.ema_column = None
        self.sma_column = None
        self.cvd_column = None

        for ind in self.indicators:
            if ind["name"] == "ema":
                period = ind.get("period")
                self.ema_column = f"ema_{period}"
            elif ind["name"] == "sma":
                period = ind.get("period")
                self.sma_column = f"sma_{period}"
            elif ind["name"] == "cvdratio":
                # Auto-generated: cvd_ratio_cumulative_signal
                cumulative = ind.get("cumulative_period_minutes", 1)
                signal = ind.get("signal_period_minutes", 15)
                self.cvd_column = f"cvd_ratio_{cumulative}_{signal}"

        if not all([self.ema_column, self.sma_column, self.cvd_column]):
            raise ValueError(
                f"{self.name} requires 'ema', 'sma', and 'cvdratio' indicators! "
                f"Got: {self.indicators}"
            )

        logger.info(f"Initialized {self.name}")
        logger.info(
            f"  Columns: {self.ema_column}, {self.sma_column}, {self.cvd_column}"
        )
        logger.info(f"  LONG threshold: CVD > {self.long_threshold}")
        logger.info(f"  SHORT threshold: CVD < {self.short_threshold}")

    def should_enter(self, data: DataWindow) -> Union[bool, Dict[str, Any]]:
        """
        Check for entry signal.

        Args:
            data: DataWindow with current market data

        Returns:
            dict with 'signal', 'direction', 'reason' if signal found
            False if no signal
        """
        try:
            # Get current values
            ema_current = data[self.ema_column][0]
            sma_current = data[self.sma_column][0]
            ema_prev = data[self.ema_column][-1]
            sma_prev = data[self.sma_column][-1]

            # Try to get CVD column (handle any naming variations)
            cvd_ratio = None
            available_cols = data.get_available_columns()

            # Try exact match first
            if self.cvd_column in available_cols:
                cvd_ratio = data[self.cvd_column][0]
            else:
                # Fallback: find any column containing "cvd_ratio"
                cvd_matches = [
                    col for col in available_cols if "cvd_ratio" in col.lower()
                ]
                if cvd_matches:
                    self.cvd_column = cvd_matches[0]  # Update column name
                    cvd_ratio = data[self.cvd_column][0]
                    logger.debug(f"Using CVD column: {self.cvd_column}")
                else:
                    logger.error(f"CVD column not found! Available: {available_cols}")
                    return False

            # Detect crosses
            isCrossBullish = ema_prev < sma_prev and ema_current >= sma_current
            isCrossBearish = ema_prev > sma_prev and ema_current <= sma_current

            # Logging
            if isCrossBullish:
                logger.info(
                    f"EMA={ema_current:.4f} > SMA={sma_current:.4f} -> Bullish Cross | CVD={cvd_ratio:.1f}%"
                )
            if isCrossBearish:
                logger.info(
                    f"EMA={ema_current:.4f} < SMA={sma_current:.4f} -> Bearish Cross | CVD={cvd_ratio:.1f}%"
                )

            # Check for LONG signal
            if isCrossBullish and cvd_ratio > self.long_threshold:
                return {
                    "signal": True,
                    "direction": "LONG",
                    "reason": (
                        f"EMA={ema_current:.2f} > SMA={sma_current:.2f} "
                        f"+ CVD={cvd_ratio:.1f}% > {self.long_threshold}"
                    ),
                }

            # Check for SHORT signal
            elif isCrossBearish and cvd_ratio < self.short_threshold:
                return {
                    "signal": True,
                    "direction": "SHORT",
                    "reason": (
                        f"EMA={ema_current:.2f} < SMA={sma_current:.2f} "
                        f"+ CVD={cvd_ratio:.1f}% < {self.short_threshold}"
                    ),
                }

            return False

        except KeyError as e:
            logger.error(f"Required indicator not found: {e}")
            logger.error(f"Available columns: {data.get_available_columns()}")
            return False
        except Exception as e:
            logger.error(f"Error in should_enter: {e}")
            return False

    def __str__(self):
        return (
            f"EMACrossSMACVD("
            f"{self.ema_column}, {self.sma_column}, {self.cvd_column}, "
            f"long>{self.long_threshold}, short<{self.short_threshold})"
        )
