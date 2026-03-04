"""
Main entry point for MA Bounce Backtesting
"""

import sys
from pathlib import Path
import pandas as pd
from tabulate import tabulate

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import load_config, PRESETS
from data import DataFetcher
from indicators import add_moving_averages, BounceDetector


def run_backtest(config=None, preset=None, **kwargs):
    """
    Run MA bounce backtest with given configuration

    Args:
        config: BacktestConfig object (optional)
        preset: Name of preset configuration (optional)
        **kwargs: Additional config overrides

    Returns:
        Dictionary with results
    """
    # Load configuration
    if config is None:
        config = load_config(preset=preset, **kwargs)

    print("=" * 80)
    print("MA BOUNCE BACKTESTING SYSTEM")
    print("=" * 80)
    print(f"\nConfiguration:")
    print(f"  Tickers: {', '.join(config.tickers)}")
    print(f"  Date Range: {config.start_date} to {config.end_date}")
    print(f"  Interval: {config.interval}")
    print(f"  MA Periods: {config.ma_periods}")
    print(f"  MA Types: {config.ma_types}")
    print(f"  Bounce Threshold: {config.bounce_threshold_pct * 100:.2f}%")
    print(f"  Min Bounce Size: {config.min_bounce_size_pct * 100:.2f}%")
    print(f"  Reversal Lookback: {config.reversal_lookback_bars} bars")
    print("\n" + "=" * 80 + "\n")

    # Step 1: Fetch data
    print("Step 1: Fetching historical data...")
    fetcher = DataFetcher(cache_dir=config.cache_dir, use_cache=config.cache_data)

    data_dict = fetcher.fetch_multiple(
        config.tickers,
        config.start_date,
        config.end_date,
        config.interval
    )

    if not data_dict:
        print("Error: No data fetched. Exiting.")
        return None

    print(f"\nSuccessfully fetched data for {len(data_dict)} tickers")

    # Step 2: Calculate moving averages
    print("\nStep 2: Calculating moving averages...")
    for ticker, df in data_dict.items():
        data_dict[ticker] = add_moving_averages(
            df,
            config.ma_periods,
            config.ma_types
        )
        print(f"  {ticker}: Added {len(config.ma_periods) * len(config.ma_types)} MAs")

    # Step 3: Detect bounces
    print("\nStep 3: Detecting bounces...")
    detector = BounceDetector(
        bounce_threshold_pct=config.bounce_threshold_pct,
        min_bounce_size_pct=config.min_bounce_size_pct,
        reversal_lookback_bars=config.reversal_lookback_bars,
        min_hold_bars=config.min_hold_bars,
        require_volume_confirmation=config.require_volume_confirmation,
        track_support_vs_resistance=config.track_support_vs_resistance
    )

    all_bounces = []
    results_by_ma = {}

    for ticker, df in data_dict.items():
        print(f"\n  {ticker}:")

        for ma_type in config.ma_types:
            for period in config.ma_periods:
                ma_column = f"{ma_type}_{period}"

                if ma_column in df.columns:
                    bounces = detector.detect_bounces(df, ma_column, ticker)
                    all_bounces.extend(bounces)

                    # Analyze bounces for this MA
                    analysis = detector.analyze_bounces(bounces)

                    key = f"{ticker}_{ma_type}_{period}"
                    results_by_ma[key] = {
                        'ticker': ticker,
                        'ma_type': ma_type,
                        'period': period,
                        **analysis
                    }

                    if config.verbose and bounces:
                        print(f"    {ma_column}: {len(bounces)} touches, "
                              f"{analysis['success_rate']:.1f}% success rate")

    # Step 4: Aggregate results
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80 + "\n")

    if not all_bounces:
        print("No bounces detected with current parameters.")
        return {
            'config': config,
            'bounces': [],
            'results_by_ma': {},
            'summary': {}
        }

    # Convert to DataFrame for analysis
    results_df = pd.DataFrame(results_by_ma.values())

    # Filter to MAs with enough samples
    results_df = results_df[results_df['total_bounces'] >= config.min_samples]

    if results_df.empty:
        print(f"No MAs with sufficient samples (min: {config.min_samples})")
        return {
            'config': config,
            'bounces': all_bounces,
            'results_by_ma': results_by_ma,
            'summary': {}
        }

    # Sort by success rate
    results_df = results_df.sort_values('success_rate', ascending=False)

    # Display top performers
    print(f"Top 10 Moving Averages by Success Rate (min {config.min_samples} samples):\n")

    display_cols = ['ticker', 'ma_type', 'period', 'total_bounces',
                    'success_rate', 'avg_reversal_pct', 'avg_hold_bars']

    top_10 = results_df.head(10)[display_cols].copy()
    top_10['success_rate'] = top_10['success_rate'].apply(lambda x: f"{x:.1f}%")
    top_10['avg_reversal_pct'] = top_10['avg_reversal_pct'].apply(lambda x: f"{x:.2f}%")
    top_10['avg_hold_bars'] = top_10['avg_hold_bars'].apply(lambda x: f"{x:.1f}")

    print(tabulate(top_10, headers='keys', tablefmt='grid', showindex=False))

    # Overall statistics
    print("\n" + "=" * 80)
    print("OVERALL STATISTICS")
    print("=" * 80 + "\n")

    total_bounces = len(all_bounces)
    successful_bounces = len([b for b in all_bounces if b.success])
    overall_success_rate = (successful_bounces / total_bounces * 100) if total_bounces > 0 else 0

    print(f"Total Bounce Events: {total_bounces}")
    print(f"Successful Bounces: {successful_bounces}")
    print(f"Overall Success Rate: {overall_success_rate:.2f}%")

    if config.track_support_vs_resistance:
        support_bounces = [b for b in all_bounces if b.bounce_type == 'support']
        resistance_bounces = [b for b in all_bounces if b.bounce_type == 'resistance']

        if support_bounces:
            support_success = len([b for b in support_bounces if b.success])
            print(f"\nSupport Bounces: {len(support_bounces)} "
                  f"({support_success / len(support_bounces) * 100:.1f}% success)")

        if resistance_bounces:
            resistance_success = len([b for b in resistance_bounces if b.success])
            print(f"Resistance Bounces: {len(resistance_bounces)} "
                  f"({resistance_success / len(resistance_bounces) * 100:.1f}% success)")

    # Best MA by ticker
    print("\n" + "=" * 80)
    print("BEST MA BY TICKER")
    print("=" * 80 + "\n")

    for ticker in config.tickers:
        ticker_results = results_df[results_df['ticker'] == ticker]
        if not ticker_results.empty:
            best = ticker_results.iloc[0]
            print(f"{ticker}: {best['ma_type']}_{best['period']} "
                  f"({best['success_rate']:.1f}% success, {int(best['total_bounces'])} bounces)")

    return {
        'config': config,
        'bounces': all_bounces,
        'results_by_ma': results_by_ma,
        'results_df': results_df,
        'summary': {
            'total_bounces': total_bounces,
            'successful_bounces': successful_bounces,
            'overall_success_rate': overall_success_rate,
        }
    }


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='MA Bounce Backtesting System')
    parser.add_argument('--preset', type=str, help='Configuration preset',
                        choices=list(PRESETS.keys()))
    parser.add_argument('--tickers', type=str, nargs='+',
                        help='Ticker symbols (e.g., EURUSD=X BTC-USD)')
    parser.add_argument('--start-date', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='End date (YYYY-MM-DD)')
    parser.add_argument('--ma-periods', type=int, nargs='+', help='MA periods to test')
    parser.add_argument('--bounce-threshold', type=float,
                        help='Bounce threshold percentage (e.g., 0.02 for 2%%)')
    parser.add_argument('--min-bounce-size', type=float,
                        help='Minimum bounce size percentage')

    args = parser.parse_args()

    # Build kwargs from command line arguments
    kwargs = {}
    if args.tickers:
        kwargs['tickers'] = args.tickers
    if args.start_date:
        kwargs['start_date'] = args.start_date
    if args.end_date:
        kwargs['end_date'] = args.end_date
    if args.ma_periods:
        kwargs['ma_periods'] = args.ma_periods
    if args.bounce_threshold:
        kwargs['bounce_threshold_pct'] = args.bounce_threshold
    if args.min_bounce_size:
        kwargs['min_bounce_size_pct'] = args.min_bounce_size

    # Run backtest
    results = run_backtest(preset=args.preset, **kwargs)

    if results:
        print("\n" + "=" * 80)
        print("Backtest completed successfully!")
        print("=" * 80)


if __name__ == '__main__':
    main()
