# Changelog

## 2026-03-03 - Bug Fix

### Fixed
- **yfinance compatibility issue**: Removed `show_errors` parameter from `yf.download()` call which is not supported in newer versions of yfinance
  - Changed in `data/fetcher.py` line 104
  - The parameter was causing `TypeError: download() got an unexpected keyword argument 'show_errors'`

### Tested
- All tests passing with venv setup
- Successfully fetches forex data (EURUSD=X)
- Successfully fetches crypto data (BTC-USD)
- Bounce detection working correctly
- Parameter configurability verified

## Initial Release

### Features
- Configurable MA bounce backtesting system
- Support for forex, crypto, and stock data via yfinance
- Multiple MA types (SMA, EMA, WMA)
- Flexible bounce detection criteria
- Support/resistance tracking
- Statistical analysis
- Data caching
- 5 preset configurations
