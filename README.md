# MA Bounce Backtesting System

A configurable backtesting system to test the reliability of price bounces off moving averages. Supports forex, cryptocurrency, and stock data.

## Features

- **Fully Configurable**: All parameters adjustable via config
- **Multiple Asset Classes**: Forex (EURUSD=X), Crypto (BTC-USD), Stocks
- **Multiple MA Types**: SMA, EMA, WMA
- **Flexible Bounce Detection**: Configure threshold, reversal criteria, hold time
- **Support/Resistance Tracking**: Separate analysis for bounces from above vs below
- **Statistical Analysis**: Success rates, confidence intervals, sample sizes
- **Data Caching**: Avoid repeated API calls
- **Preset Configurations**: Pre-configured strategies (conservative, aggressive, scalping, etc.)

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## Quick Start

### Basic Usage

```bash
# Run with default configuration
python main.py

# Use a preset configuration
python main.py --preset forex_scalping

# Test specific tickers
python main.py --tickers EURUSD=X GBPUSD=X BTC-USD

# Custom date range
python main.py --start-date 2023-01-01 --end-date 2026-01-01

# Custom MA periods
python main.py --ma-periods 20 50 100 200

# Adjust bounce sensitivity
python main.py --bounce-threshold 0.01 --min-bounce-size 0.025
```

### Python API

```python
from config import load_config
from main import run_backtest

# Use default config
results = run_backtest()

# Use preset
results = run_backtest(preset='conservative')

# Custom configuration
results = run_backtest(
    tickers=['EURUSD=X', 'BTC-USD'],
    ma_periods=[20, 50, 100],
    bounce_threshold_pct=0.02,
    min_bounce_size_pct=0.025,
    reversal_lookback_bars=5
)

# Access results
print(f"Success rate: {results['summary']['overall_success_rate']:.2f}%")
print(f"Total bounces: {results['summary']['total_bounces']}")

# Get top performing MAs
top_mas = results['results_df'].head(10)
```

## Configuration

### Key Parameters

All parameters can be configured via the `BacktestConfig` class:

```python
from config import BacktestConfig

config = BacktestConfig(
    # Data settings
    tickers=['EURUSD=X', 'GBPUSD=X', 'BTC-USD', 'ETH-USD'],
    start_date='2020-01-01',
    end_date='2026-03-01',
    interval='1d',  # '1m', '5m', '15m', '1h', '1d', '1wk', '1mo'

    # MA settings
    ma_periods=[10, 20, 30, 50, 100, 200],
    ma_types=['SMA', 'EMA', 'WMA'],

    # Bounce detection settings
    bounce_threshold_pct=0.02,        # 2% - how close to MA counts as "touch"
    min_bounce_size_pct=0.02,         # 2% - minimum reversal to count as bounce
    reversal_lookback_bars=5,         # Look ahead 5 bars for reversal
    min_hold_bars=2,                  # Bounce must hold for 2 bars minimum

    # Advanced options
    require_volume_confirmation=False,  # Require volume spike
    track_support_vs_resistance=True,   # Track direction separately
    require_trend=False,                # Only count bounces in trending markets

    # Performance
    cache_data=True,
    verbose=True
)
```

### Preset Configurations

Five pre-configured strategies are available:

1. **conservative**: Tight tolerances, larger bounces required, volume confirmation
2. **aggressive**: Wider tolerances, smaller bounces accepted
3. **trending_only**: Only count bounces in clear trends
4. **forex_scalping**: Optimized for 15m forex trading
5. **crypto_swing**: Optimized for 4h crypto swing trading

```python
from config import load_config

# Load preset
config = load_config(preset='conservative')

# Load preset with overrides
config = load_config(
    preset='forex_scalping',
    tickers=['EURUSD=X'],
    bounce_threshold_pct=0.01
)
```

## Ticker Formats

### Forex
```python
'EURUSD=X'   # EUR/USD
'GBPUSD=X'   # GBP/USD
'USDJPY=X'   # USD/JPY
'AUDUSD=X'   # AUD/USD
```

### Cryptocurrency
```python
'BTC-USD'    # Bitcoin
'ETH-USD'    # Ethereum
'SOL-USD'    # Solana
```

### Stocks
```python
'AAPL'       # Apple
'SPY'        # S&P 500 ETF
'QQQ'        # Nasdaq ETF
```

## Data Intervals

Available intervals (from yfinance):
- `'1m'` - 1 minute (limited history, ~7 days)
- `'5m'` - 5 minutes
- `'15m'` - 15 minutes
- `'1h'` - 1 hour
- `'1d'` - Daily (default)
- `'1wk'` - Weekly
- `'1mo'` - Monthly

**Note**: Intraday data (< 1d) has limited historical availability (typically 60 days max).

## Output

The backtest returns:
- **Bounce events**: List of all detected bounces with details
- **Results by MA**: Success rates for each MA period/type combination
- **Summary statistics**: Overall success rate, bounce counts
- **Top performers**: Best performing MAs sorted by success rate

Example output:
```
Top 10 Moving Averages by Success Rate (min 30 samples):

╒══════════╤═══════════╤══════════╤═════════════════╤════════════════╤══════════════════════╤════════════════════╕
│ ticker   │ ma_type   │   period │   total_bounces │ success_rate   │ avg_reversal_pct     │ avg_hold_bars      │
╞══════════╪═══════════╪══════════╪═════════════════╪════════════════╪══════════════════════╪════════════════════╡
│ EURUSD=X │ EMA       │       50 │              45 │ 73.3%          │ 2.45%                │ 3.2                │
│ BTC-USD  │ SMA       │      100 │              38 │ 71.1%          │ 4.12%                │ 4.5                │
│ EURUSD=X │ SMA       │       20 │              52 │ 69.2%          │ 2.15%                │ 2.8                │
└──────────┴───────────┴──────────┴─────────────────┴────────────────┴──────────────────────┴────────────────────┘

OVERALL STATISTICS
Total Bounce Events: 342
Successful Bounces: 238
Overall Success Rate: 69.59%

Support Bounces: 178 (72.5% success)
Resistance Bounces: 164 (66.5% success)
```

## Project Structure

```
ma-bounce-backtest/
├── config.py              # Configuration system
├── main.py                # Main entry point
├── requirements.txt       # Dependencies
├── README.md             # This file
├── data/
│   ├── __init__.py
│   ├── fetcher.py        # Data fetching with yfinance
│   └── cache/            # Cached data files
├── indicators/
│   ├── __init__.py
│   ├── moving_averages.py  # MA calculations
│   └── bounce_detector.py  # Bounce detection logic
├── backtest/
│   ├── engine.py         # Backtesting engine (future)
│   ├── metrics.py        # Performance metrics (future)
│   └── optimizer.py      # Parameter optimization (future)
└── analysis/
    ├── visualizer.py     # Charts and graphs (future)
    └── reporter.py       # Report generation (future)
```

## Future Enhancements

Planned features:
- Parameter optimization (grid search)
- Visualization (charts, heatmaps)
- HTML/PDF reports
- Market regime detection (trending vs ranging)
- Trade simulation (full entry/exit/position sizing)
- Walk-forward analysis
- Monte Carlo simulation
- Multi-timeframe analysis

## Example Use Cases

### 1. Find Best MA for EUR/USD
```python
results = run_backtest(
    tickers=['EURUSD=X'],
    ma_periods=list(range(10, 201, 10)),  # Test 10, 20, ..., 200
    start_date='2020-01-01'
)

# Get best MA
best = results['results_df'].iloc[0]
print(f"Best MA: {best['ma_type']}_{best['period']}")
print(f"Success Rate: {best['success_rate']:.1f}%")
```

### 2. Compare Forex vs Crypto
```python
results = run_backtest(
    tickers=['EURUSD=X', 'BTC-USD'],
    ma_periods=[20, 50, 100]
)

# Analyze by asset type
for ticker in ['EURUSD=X', 'BTC-USD']:
    ticker_data = results['results_df'][results['results_df']['ticker'] == ticker]
    avg_success = ticker_data['success_rate'].mean()
    print(f"{ticker}: {avg_success:.1f}% average success")
```

### 3. Test Different Timeframes
```python
for interval in ['1h', '4h', '1d']:
    print(f"\nTesting {interval} timeframe:")
    results = run_backtest(
        tickers=['BTC-USD'],
        interval=interval,
        ma_periods=[20, 50],
        verbose=False
    )
    print(f"Success rate: {results['summary']['overall_success_rate']:.1f}%")
```

## Data Sources

- **Primary**: yfinance (Yahoo Finance)
  - Free, unlimited access
  - Forex: Available since ~2003
  - Crypto: Available since listing
  - No API key required

## Limitations

- yfinance is unofficial and subject to changes
- Intraday data has limited history (60 days max)
- Data quality depends on Yahoo Finance
- For research/educational purposes only

## License

MIT License - Free to use for research and educational purposes.

## Credits

Built with:
- yfinance - Market data
- pandas - Data manipulation
- numpy - Numerical computations
- matplotlib/seaborn - Visualization (future)
