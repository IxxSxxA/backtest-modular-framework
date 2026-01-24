# indicators/cvd_ratio_calculator.py

import pandas as pd
import numpy as np
from .base_calculator import BaseCalculator
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


# indicators/cvd_ratio_calculator.py - VERSIONE CORRETTA


class CVDRatioCalculator(BaseCalculator):
    """
    CVD Ratio Calculator: Simple Buy/Sell ratio over rolling window.
    CALCOLATO DIRETTAMENTE SUL TIMEFRAME DELLA STRATEGIA!

    Parameters:
        window_minutes: Rolling window in REAL MINUTES (not candles)
        use_quote: Use quote volume instead of base volume
    """

    def calculate(self, data: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
        """
        Calculate CVD Ratio on strategy timeframe data.
        """
        # Get parameters - NO tf parameter!
        window_minutes = int(params.get("window_minutes", 15))
        use_quote = bool(params.get("use_quote", False))

        # VERIFICA: I dati in input sono già nel timeframe giusto!
        logger.info(
            f"Calculating CVD Ratio for {self.symbol} "
            f"(window: {window_minutes}min, data TF: {self.timeframe})"
        )

        # IMPORTANT -> window_minutes are real minutes, not candles
        # If we're on 5m timeframe, 15 minutes = 3 candles
        minutes_per_candle = self.TF_TO_MINUTES.get(self.timeframe, 1)
        window_candles = max(1, window_minutes // minutes_per_candle)

        logger.info(
            f"  Strategy TF: {self.timeframe} = {minutes_per_candle} min/candle"
            f"  → {window_minutes} min = {window_candles} candles"
        )

        # Determine volume columns
        if use_quote:
            buy_col = "taker_buy_quote_volume"
            total_col = "quote_volume"
        else:
            buy_col = "taker_buy_volume"
            total_col = "volume"

        # Check required columns
        required = [buy_col, total_col]
        missing = [col for col in required if col not in data.columns]
        if missing:
            raise ValueError(f"Missing columns for CVD Ratio: {missing}")

        # Calculate sell volume
        buy_vol = data[buy_col]
        total_vol = data[total_col]
        sell_vol = total_vol - buy_vol

        # Volume delta per candle
        volume_delta = buy_vol - sell_vol

        # Rolling sum over window (in CANDLES, not minutes)
        rolling_delta = volume_delta.rolling(window=window_candles, min_periods=1).sum()
        rolling_total = total_vol.rolling(window=window_candles, min_periods=1).sum()

        # Calculate ratio: (net buying volume) / (total volume) * 100
        ratio = pd.Series(index=data.index, dtype=float)

        # Avoid division by zero
        mask = rolling_total > 0
        ratio[mask] = (rolling_delta[mask] / rolling_total[mask]) * 100
        ratio[~mask] = 0.0

        # Naming
        ratio.name = f"cvd_ratio_{window_minutes}min_{self.timeframe}"

        logger.debug(
            f"CVD Ratio stats: min={ratio.min():.1f}%, "
            f"max={ratio.max():.1f}%, mean={ratio.mean():.1f}%"
        )

        # DEBUG LOGGING
        logger.info(f"============= CVD RATIO DEBUG DATA ===============")
        logger.info(f"Data shape: {data.shape}")
        logger.info(f"Data columns: {list(data.columns)}")
        logger.info(f"First few timestamps: {data.index[:5]}")
        logger.info(f"Minutes per candle: {minutes_per_candle}")
        logger.info(f"Window candles: {window_candles}")

        # Sample calculation for verification
        if len(data) > window_candles:
            sample_idx = window_candles
            sample_data = {
                "buy_vol": buy_vol.iloc[sample_idx - window_candles : sample_idx].sum(),
                "total_vol": total_vol.iloc[
                    sample_idx - window_candles : sample_idx
                ].sum(),
                "ratio": ratio.iloc[sample_idx] if sample_idx < len(ratio) else None,
            }
            logger.info(f"Sample window calculation: {sample_data}")

        return ratio
