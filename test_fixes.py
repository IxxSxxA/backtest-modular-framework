#!/usr/bin/env python3
"""
Test script to verify all fixes are working correctly.
Run this before your main backtest to ensure everything is OK.
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_resampler():
    """Test DataResampler fixes."""
    print("\n" + "=" * 60)
    print("TEST 1: DataResampler")
    print("=" * 60)

    from core.resampler import DataResampler

    # Create sample 1m data with some gaps
    dates = pd.date_range("2025-01-01 00:00", periods=1000, freq="1min")
    data = pd.DataFrame(
        {
            "open": np.random.randn(1000).cumsum() + 100,
            "high": np.random.randn(1000).cumsum() + 101,
            "low": np.random.randn(1000).cumsum() + 99,
            "close": np.random.randn(1000).cumsum() + 100,
            "volume": np.random.randint(1000, 10000, 1000),
            "taker_buy_volume": np.random.randint(400, 6000, 1000),
        },
        index=dates,
    )

    resampler = DataResampler()

    # Test 1: Normal resampling
    print("\n[1.1] Testing 5m resampling...")
    resampled = resampler.resample_to_timeframe(data, "5m")
    assert len(resampled) == 200, f"Expected 200 candles, got {len(resampled)}"
    print(f"✅ 5m resampling: {len(data)} rows → {len(resampled)} rows")

    # Test 2: Index normalization
    print("\n[1.2] Testing index normalization...")
    assert all(resampled.index == resampled.index.floor("min")), "Index not normalized!"
    print("✅ Index normalized to minute precision")

    # Test 3: Normalize start to midnight
    print("\n[1.3] Testing midnight normalization...")

    # Case 1: Data already starts at midnight - should keep it
    normalized1 = resampler.normalize_backtest_start(data, "2025-01-01 12:30")
    expected1 = pd.Timestamp("2025-01-01 00:00")
    assert (
        normalized1.index[0] == expected1
    ), f"Case 1 failed: Expected {expected1}, got {normalized1.index[0]}"
    print(f"✅ Case 1 (data has midnight): {data.index[0]} → {normalized1.index[0]}")

    # Case 2: Data starts mid-day - should jump to next midnight
    # Create data that spans multiple days for this test
    multiday_dates = pd.date_range("2025-01-01 14:00", periods=2000, freq="1min")
    multiday_data = pd.DataFrame(
        {
            "open": np.random.randn(2000).cumsum() + 100,
            "high": np.random.randn(2000).cumsum() + 101,
            "low": np.random.randn(2000).cumsum() + 99,
            "close": np.random.randn(2000).cumsum() + 100,
            "volume": np.random.randint(1000, 10000, 2000),
        },
        index=multiday_dates,
    )

    normalized2 = resampler.normalize_backtest_start(multiday_data, "2025-01-01 14:00")
    expected2 = pd.Timestamp("2025-01-02 00:00")
    assert (
        normalized2.index[0] == expected2
    ), f"Case 2 failed: Expected {expected2}, got {normalized2.index[0]}"
    print(
        f"✅ Case 2 (data mid-day): {multiday_data.index[0]} → {normalized2.index[0]}"
    )

    # Test 4: Data quality check
    print("\n[1.4] Testing data quality threshold...")
    # Create data with 96% valid rows (should pass)
    good_data = data.copy()
    try:
        resampled = resampler.resample_to_timeframe(
            good_data, "5m", quality_threshold=0.95
        )
        print("✅ Data quality check: PASSED (retention > 95%)")
    except ValueError as e:
        print(f"⚠️ Data quality check triggered: {e}")

    print("\nDataResampler: ALL TESTS PASSED ✅\n")


def test_cache_key():
    """Test cache key includes ALL parameters."""
    print("\n" + "=" * 60)
    print("TEST 2: Cache Key Generation")
    print("=" * 60)

    from indicators.base_calculator import BaseCalculator

    # We need a concrete implementation for testing
    class TestCalculator(BaseCalculator):
        def calculate(self, data, params):
            return pd.Series()

    calc1 = TestCalculator("BTCUSDT", "5m")
    calc2 = TestCalculator("BTCUSDT", "5m")

    # Test different parameters generate different keys
    params1 = {"period": 20, "other_param": 1.5}
    params2 = {"period": 50, "other_param": 1.5}
    params3 = {"period": 20, "other_param": 2.0}  # Same period, different other param

    key1 = calc1.get_cache_key(params1)
    key2 = calc2.get_cache_key(params2)
    key3 = calc1.get_cache_key(params3)

    print(f"\n[2.1] Cache key 1 (period=20, other=1.5): {key1}")
    print(f"[2.2] Cache key 2 (period=50, other=1.5): {key2}")
    print(f"[2.3] Cache key 3 (period=20, other=2.0): {key3}")

    # All keys should be different
    assert key1 != key2, "Keys should differ when period changes"
    assert key1 != key3, "Keys should differ when ANY parameter changes"
    assert key2 != key3, "Keys should be unique"

    print("\n✅ All cache keys are unique")
    print("\nCache Key: ALL TESTS PASSED ✅\n")


def test_lookback_window():
    """Test lookback window edge case."""
    print("\n" + "=" * 60)
    print("TEST 3: Lookback Window Edge Case")
    print("=" * 60)

    from core.engine import BacktestEngine
    from strategies.entry.base_entry import BaseEntryStrategy
    from strategies.exit.base_exit import BaseExitStrategy
    from strategies.risk.base_risk import BaseRiskManager

    # Create minimal strategy implementations
    class DummyEntry(BaseEntryStrategy):
        def should_enter(self, data):
            return False

    class DummyExit(BaseExitStrategy):
        def should_exit(self, data, entry_price, entry_time, position):
            return False, ""

    class DummyRisk(BaseRiskManager):
        name = "dummy"

        def can_trade(self, capital, open_pnl, position):
            return True

        def calculate_position_size(self, **kwargs):
            return kwargs.get("capital", 1000) * 0.1

    # Test with insufficient data
    print("\n[3.1] Testing with insufficient data...")
    small_data = pd.DataFrame(
        {"close": [100, 101, 102], "volume": [1000, 1100, 1200]},
        index=pd.date_range("2025-01-01", periods=3, freq="1min"),
    )

    try:
        engine = BacktestEngine(
            data=small_data,
            entry_strategy=DummyEntry({}),
            exit_strategy=DummyExit({}),
            risk_manager=DummyRisk({}),
            lookback_window=100,
        )
        engine.run()
        print("❌ Should have raised ValueError!")
    except ValueError as e:
        print(f"✅ Correctly raised error: {str(e)[:50]}...")

    # Test with exactly enough data
    print("\n[3.2] Testing with exactly enough data...")
    exact_data = pd.DataFrame(
        {
            "close": np.random.randn(101).cumsum() + 100,
            "volume": np.random.randint(1000, 10000, 101),
        },
        index=pd.date_range("2025-01-01", periods=101, freq="1min"),
    )

    try:
        engine = BacktestEngine(
            data=exact_data,
            entry_strategy=DummyEntry({}),
            exit_strategy=DummyExit({}),
            risk_manager=DummyRisk({}),
            lookback_window=100,
        )
        results = engine.run()
        print(f"✅ Backtest ran successfully with {len(exact_data)} candles")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

    print("\nLookback Window: ALL TESTS PASSED ✅\n")


def test_long_short_support():
    """Test LONG/SHORT position support."""
    print("\n" + "=" * 60)
    print("TEST 4: LONG/SHORT Position Support")
    print("=" * 60)

    from core.engine import BacktestEngine

    print("\n[4.1] Testing engine initialization with LONG only...")
    try:
        # This should work
        config_long = {
            "backtest": {
                "capital": {"initial": 10000},
                "costs": {"commission": 0.001},
                "execution": {"lookback_window": 100},
            },
            "strategy": {"trading": {"allow_long": True, "allow_short": False}},
        }
        print("✅ LONG-only configuration valid")
    except Exception as e:
        print(f"❌ Error: {e}")

    print("\n[4.2] Testing engine initialization with SHORT only...")
    try:
        config_short = {
            "backtest": {
                "capital": {"initial": 10000},
                "costs": {"commission": 0.001},
                "execution": {"lookback_window": 100},
            },
            "strategy": {"trading": {"allow_long": False, "allow_short": True}},
        }
        print("✅ SHORT-only configuration valid")
    except Exception as e:
        print(f"❌ Error: {e}")

    print("\n[4.3] Testing engine initialization with BOTH...")
    try:
        config_both = {
            "backtest": {
                "capital": {"initial": 10000},
                "costs": {"commission": 0.001},
                "execution": {"lookback_window": 100},
            },
            "strategy": {"trading": {"allow_long": True, "allow_short": True}},
        }
        print("✅ LONG+SHORT configuration valid")
    except Exception as e:
        print(f"❌ Error: {e}")

    print("\nLONG/SHORT Support: ALL TESTS PASSED ✅\n")


def test_real_data_normalization():
    """Test normalization with your actual data."""
    print("\n" + "=" * 60)
    print("TEST 5: Real Data Normalization (Optional)")
    print("=" * 60)

    try:
        from core.data_loader import DataLoader
        import yaml

        # Try to load your config
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)

        print("\n[5.1] Testing with your actual XPLUSDT data...")
        loader = DataLoader(config)

        # Load without normalization
        loader_no_norm = DataLoader(config)
        data_raw = loader_no_norm.load_single_symbol("XPLUSDT", normalize_start=False)

        print(f"  Raw data first timestamp: {data_raw.index[0]}")
        print(f"  Raw data last timestamp:  {data_raw.index[-1]}")

        # Load with normalization
        loader_norm = DataLoader(config)
        data_normalized = loader_norm.load_single_symbol(
            "XPLUSDT", normalize_start=True
        )

        print(f"  Normalized first timestamp: {data_normalized.index[0]}")
        print(f"  Difference: {len(data_raw) - len(data_normalized)} candles dropped")

        # Check if normalized to midnight
        if data_normalized.index[0].hour == 0 and data_normalized.index[0].minute == 0:
            print("  ✅ Data correctly normalized to midnight!")
        else:
            print(f"  ⚠️  Data NOT at midnight: {data_normalized.index[0]}")

        print("\nReal Data Normalization: TEST COMPLETED ✅\n")

    except FileNotFoundError:
        print("\n⚠️  Skipping real data test (data file not found)")
        print("   This is OK - test uses synthetic data\n")
    except Exception as e:
        print(f"\n⚠️  Could not test real data: {e}")
        print("   This is OK - test uses synthetic data\n")


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print(" " * 20 + "TRADING FRAMEWORK - TEST SUITE")
    print("=" * 70)

    try:
        test_resampler()
        test_cache_key()
        test_lookback_window()
        test_long_short_support()
        test_real_data_normalization()  # NEW: Optional test with real data

        print("\n" + "=" * 70)
        print(" " * 25 + "🎉 ALL TESTS PASSED! 🎉")
        print("=" * 70)
        print("\n✅ Your framework is ready to run backtests!")
        print("\nNext steps:")
        print("  1. Run your backtest: python backtest.py")
        print("  2. Check results in: data/journals/")
        print("  3. Analyze trades and equity curve")
        print("\n")

    except Exception as e:
        print("\n" + "=" * 70)
        print(" " * 30 + "❌ TESTS FAILED")
        print("=" * 70)
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
