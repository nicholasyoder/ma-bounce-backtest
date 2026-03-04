# Getting Started with MA Bounce Backtesting

## Installation

1. **Install Python packages:**
```bash
cd ma-bounce-backtest
pip install -r requirements.txt
```

## First Run

### Option 1: Quick Test (Recommended)

Run the test script to verify everything works:

```bash
python test_example.py
```

This will:
- Test data fetching for forex (EURUSD=X) and crypto (BTC-USD)
- Verify bounce detection works
- Confirm parameters are configurable
- Show sample output

### Option 2: Basic Backtest

Run a basic backtest with default settings:

```bash
python main.py
```

This will test:
- EUR/USD, GBP/USD, USD/JPY (forex)
- BTC-USD, ETH-USD (crypto)
- MA periods: 10, 20, 30, 50, 100, 200
- MA types: SMA, EMA, WMA
- From 2020-01-01 to 2026-03-01

## Common Use Cases

### 1. Test a Single Forex Pair

```bash
python main.py --tickers EURUSD=X --ma-periods 20 50 100
```

### 2. Test Bitcoin with Different MA Periods

```bash
python main.py --tickers BTC-USD --ma-periods 10 20 30 40 50 60 70 80 90 100
```

### 3. Intraday Forex Scalping (15-minute)

```bash
python main.py --preset forex_scalping --tickers EURUSD=X GBPUSD=X
```

### 4. Crypto Swing Trading (4-hour)

```bash
python main.py --preset crypto_swing --tickers BTC-USD ETH-USD
```

### 5. Conservative Strategy

```bash
python main.py --preset conservative --tickers EURUSD=X
```

## Understanding the Output

### Success Rate
The percentage of times price bounced after touching the MA vs. continuing through it.

- **>70%**: Strong bounce tendency at this MA
- **50-70%**: Moderate bounce tendency
- **<50%**: Weak or unreliable bounce

### Average Reversal %
How far price typically moves after bouncing.

- Higher values = stronger bounces
- Useful for setting profit targets

### Hold Bars
How many bars the bounce typically lasts before reversing.

- Higher values = more sustained bounces
- Useful for setting time exits

### Support vs Resistance
- **Support Bounces**: Price approaches MA from below and bounces up
- **Resistance Bounces**: Price approaches MA from above and bounces down

Often one direction has higher success rate than the other.

## Customizing Parameters

All parameters can be adjusted via command line or Python API:

### Via Command Line

```bash
# Adjust bounce sensitivity (how close to MA)
python main.py --bounce-threshold 0.01  # 1% (tighter)
python main.py --bounce-threshold 0.03  # 3% (looser)

# Adjust minimum bounce size
python main.py --min-bounce-size 0.01  # 1% (smaller bounces)
python main.py --min-bounce-size 0.05  # 5% (larger bounces only)

# Custom date range
python main.py --start-date 2024-01-01 --end-date 2025-12-31
```

### Via Python API

```python
from main import run_backtest

# Full control over all parameters
results = run_backtest(
    tickers=['EURUSD=X', 'BTC-USD'],
    start_date='2023-01-01',
    end_date='2026-03-01',
    interval='1d',

    ma_periods=[20, 50, 100, 200],
    ma_types=['SMA', 'EMA'],

    # Bounce detection parameters
    bounce_threshold_pct=0.02,      # 2%
    min_bounce_size_pct=0.02,       # 2%
    reversal_lookback_bars=5,       # Look ahead 5 bars
    min_hold_bars=2,                # Must hold 2 bars

    # Advanced options
    require_volume_confirmation=False,
    track_support_vs_resistance=True,
    require_trend=False,

    # Statistical filtering
    min_samples=30,                 # Need 30+ samples
    confidence_level=0.95,

    # Performance
    cache_data=True,
    verbose=True
)

# Access results
print(f"Total bounces: {results['summary']['total_bounces']}")
print(f"Success rate: {results['summary']['overall_success_rate']:.2f}%")

# Get best performing MA
best_ma = results['results_df'].iloc[0]
print(f"Best MA: {best_ma['ma_type']}_{best_ma['period']}")
print(f"Success rate: {best_ma['success_rate']:.1f}%")

# Export results
results['results_df'].to_csv('backtest_results.csv')
```

## Tips for Best Results

1. **Start with longer periods** (2+ years) for statistical significance
2. **Use at least 30 samples** per MA for reliable results
3. **Test multiple timeframes** (1d, 4h, 1h) to find best fit
4. **Compare forex vs crypto** - different characteristics
5. **Watch support vs resistance** - often one works better
6. **Try different MA types** - EMA often more responsive than SMA
7. **Adjust for volatility** - crypto needs wider thresholds

## Next Steps

1. Run tests with your favorite currency pairs/cryptos
2. Experiment with different parameters
3. Compare results across timeframes
4. Identify best MAs for your trading style
5. Consider implementing trade simulation (coming soon)

## Troubleshooting

### No bounces detected
- Increase `bounce_threshold_pct` (allow more distance from MA)
- Decrease `min_bounce_size_pct` (accept smaller bounces)
- Increase `reversal_lookback_bars` (give more time for reversal)

### Too many false signals
- Decrease `bounce_threshold_pct` (require closer to MA)
- Increase `min_bounce_size_pct` (require larger bounces)
- Set `require_volume_confirmation=True`
- Set `require_trend=True`

### Insufficient data
- Increase date range
- Use daily or longer intervals (intraday has limited history)
- Check ticker symbol is correct

## Available Presets

| Preset | Description | Best For |
|--------|-------------|----------|
| `conservative` | Tight tolerances, large bounces | High probability trades |
| `aggressive` | Wide tolerances, small bounces | More opportunities |
| `trending_only` | Only in trending markets | Trend followers |
| `forex_scalping` | 15m timeframe, tight stops | Forex day trading |
| `crypto_swing` | 4h timeframe, wide stops | Crypto swing trading |

Use: `python main.py --preset <name>`

## Need Help?

- Check `README.md` for full documentation
- Review `test_example.py` for code examples
- Examine `config.py` for all available parameters

Happy backtesting! 📈
