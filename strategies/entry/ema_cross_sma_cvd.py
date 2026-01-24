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

    Parameters:
        ema_period: Fast EMA period
        sma_period: Slow SMA period
        cvd_window_minutes: CVD calculation window in minutes
        long_threshold: CVD ratio threshold for LONG entries (default: 20.0)
        short_threshold: CVD ratio threshold for SHORT entries (default: -20.0)

    CVD Ratio Range: -100 (all selling) to +100 (all buying)
    """

    def __init__(self, params: Dict[str, Any]):
        super().__init__(params)

        self.ema_period = params.get("ema_period", 59)
        self.sma_period = params.get("sma_period", 200)
        self.cvd_window_minutes = params.get("cvd_window_minutes", 15)

        # Separate thresholds for LONG/SHORT
        default_threshold = params.get("cvd_ratio_threshold", 20.0)
        self.long_threshold = params.get("long_threshold", default_threshold)
        self.short_threshold = params.get("short_threshold", -default_threshold)

        logger.info(f"Initialized {self.name}")
        logger.info(f"  EMA: {self.ema_period}")
        logger.info(f"  SMA: {self.sma_period}")
        logger.info(f"  CVD Window: {self.cvd_window_minutes} minutes")
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
            # Get required indicators
            ema_col = f"ema_{self.ema_period}"
            sma_col = f"sma_{self.sma_period}"
            cvd_col = f"cvd_ratio_{self.cvd_window_minutes}min_{data.data.columns[0].split('_')[-1]}"

            # Try to find CVD column (handle different naming)
            available_cols = data.get_available_columns()
            cvd_matches = [col for col in available_cols if "cvd_ratio" in col.lower()]

            if not cvd_matches:
                logger.error(f"CVD ratio column not found! Available: {available_cols}")
                return False

            cvd_col = cvd_matches[0]  # Use first match

            # Get current values
            ema_current = data[ema_col][0]
            sma_current = data[sma_col][0]

            ema_prev = data[ema_col][-1]
            sma_prev = data[sma_col][-1]

            cvd_ratio = data[cvd_col][0]

            isCrossBullish = ema_prev <= sma_prev and ema_current > sma_current
            isCrossBearish = ema_prev >= sma_prev and ema_current < sma_current

            # Logging
            if isCrossBullish:
                logger.info(
                    f"EMA({self.ema_period})={ema_current:.4f} > SMA({self.sma_period})={sma_current:.4f} -> Detected Bullish Cross | CVD={cvd_ratio:.1f}%"
                )
            if isCrossBearish:
                logger.info(
                    f"EMA({self.ema_period})={ema_current:.4f} < SMA({self.sma_period})={sma_current:.4f} -> Detected Bearish Cross | CVD={cvd_ratio:.1f}%"
                )

            # Check for LONG signal
            if isCrossBullish and cvd_ratio > self.long_threshold:
                return {
                    "signal": True,
                    "direction": "LONG",
                    "reason": (
                        f"EMA({self.ema_period})={ema_current:.2f} > SMA({self.sma_period})={sma_current:.2f} "
                        f"+ CVD={cvd_ratio:.1f}% > {self.long_threshold}"
                    ),
                }

            # Check for SHORT signal
            elif isCrossBearish and cvd_ratio < self.short_threshold:
                return {
                    "signal": True,
                    "direction": "SHORT",
                    "reason": (
                        f"EMA({self.ema_period})={ema_current:.2f} < SMA({self.sma_period})={sma_current:.2f} "
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
            f"ema={self.ema_period}, "
            f"sma={self.sma_period}, "
            f"cvd_window={self.cvd_window_minutes}min, "
            f"long>{self.long_threshold}, "
            f"short<{self.short_threshold})"
        )
