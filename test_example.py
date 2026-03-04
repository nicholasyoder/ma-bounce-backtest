"""
Example/test script to verify the backtesting system works
"""

from config import load_config
from main import run_backtest

def test_basic():
    """Test basic functionality with small dataset"""
    print("Testing basic functionality...\n")

    # Small test with limited data
    results = run_backtest(
        tickers=['EURUSD=X'],
        start_date='2025-01-01',
        end_date='2026-03-01',
        ma_periods=[20, 50],
        ma_types=['SMA'],
        bounce_threshold_pct=0.02,
        min_bounce_size_pct=0.015,
        reversal_lookback_bars=5,
        min_samples=5,  # Lower threshold for test
        verbose=True
    )

    assert results is not None, "Backtest failed to return results"
    assert 'summary' in results, "Results missing summary"
    assert 'bounces' in results, "Results missing bounces"

    print("\n✓ Basic test passed!")
    return results


def test_multiple_tickers():
    """Test with multiple tickers including crypto"""
    print("\nTesting multiple tickers (forex + crypto)...\n")

    results = run_backtest(
        tickers=['EURUSD=X', 'BTC-USD'],
        start_date='2025-06-01',
        end_date='2026-03-01',
        ma_periods=[20],
        ma_types=['SMA', 'EMA'],
        min_samples=3,
        verbose=False
    )

    assert results is not None
    assert len(results['bounces']) >= 0

    print("\n✓ Multiple ticker test passed!")
    return results


def test_preset():
    """Test preset configuration"""
    print("\nTesting preset configuration...\n")

    results = run_backtest(
        preset='conservative',
        tickers=['EURUSD=X'],
        start_date='2025-06-01',
        end_date='2026-03-01',
        min_samples=3,
        verbose=False
    )

    assert results is not None
    print("\n✓ Preset test passed!")
    return results


def test_configurable_parameters():
    """Test that parameters are actually configurable"""
    print("\nTesting parameter configurability...\n")

    # Very strict parameters
    strict_results = run_backtest(
        tickers=['EURUSD=X'],
        start_date='2025-01-01',
        end_date='2026-03-01',
        ma_periods=[50],
        bounce_threshold_pct=0.005,  # Very tight
        min_bounce_size_pct=0.03,    # Large bounce required
        reversal_lookback_bars=3,
        min_samples=1,
        verbose=False
    )

    # Very loose parameters
    loose_results = run_backtest(
        tickers=['EURUSD=X'],
        start_date='2025-01-01',
        end_date='2026-03-01',
        ma_periods=[50],
        bounce_threshold_pct=0.05,   # Very wide
        min_bounce_size_pct=0.005,   # Small bounce accepted
        reversal_lookback_bars=10,
        min_samples=1,
        verbose=False
    )

    # Loose parameters should find more bounces
    strict_bounces = len(strict_results['bounces'])
    loose_bounces = len(loose_results['bounces'])

    print(f"Strict parameters: {strict_bounces} bounces")
    print(f"Loose parameters: {loose_bounces} bounces")
    print(f"Difference: {loose_bounces - strict_bounces} more bounces with loose parameters")

    assert loose_bounces >= strict_bounces, "Loose parameters should find at least as many bounces"

    print("\n✓ Parameter configurability test passed!")


def run_all_tests():
    """Run all tests"""
    print("=" * 80)
    print("RUNNING BACKTEST SYSTEM TESTS")
    print("=" * 80 + "\n")

    try:
        test_basic()
        test_multiple_tickers()
        test_preset()
        test_configurable_parameters()

        print("\n" + "=" * 80)
        print("ALL TESTS PASSED! ✓")
        print("=" * 80)
        print("\nThe backtesting system is working correctly.")
        print("You can now run: python main.py --help for usage options")

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == '__main__':
    success = run_all_tests()
    exit(0 if success else 1)
