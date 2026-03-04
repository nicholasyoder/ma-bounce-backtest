"""
Data fetcher for historical price data using yfinance
Supports stocks, forex, and cryptocurrency
"""

import yfinance as yf
import pandas as pd
import os
import pickle
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime
import hashlib


class DataFetcher:
    """Fetch and cache historical market data"""

    def __init__(self, cache_dir: str = 'data/cache', use_cache: bool = True):
        """
        Initialize DataFetcher

        Args:
            cache_dir: Directory to store cached data
            use_cache: Whether to use cached data
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.use_cache = use_cache

    def _get_cache_key(self, ticker: str, start_date: str, end_date: str, interval: str) -> str:
        """Generate unique cache key for data request"""
        key_str = f"{ticker}_{start_date}_{end_date}_{interval}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get path to cache file"""
        return self.cache_dir / f"{cache_key}.pkl"

    def _load_from_cache(self, cache_key: str) -> Optional[pd.DataFrame]:
        """Load data from cache if available"""
        if not self.use_cache:
            return None

        cache_path = self._get_cache_path(cache_key)
        if cache_path.exists():
            try:
                with open(cache_path, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"Warning: Failed to load cache: {e}")
                return None
        return None

    def _save_to_cache(self, cache_key: str, data: pd.DataFrame):
        """Save data to cache"""
        if not self.use_cache:
            return

        cache_path = self._get_cache_path(cache_key)
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
        except Exception as e:
            print(f"Warning: Failed to save cache: {e}")

    def fetch_ticker(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        interval: str = '1d',
        validate: bool = True
    ) -> Optional[pd.DataFrame]:
        """
        Fetch historical data for a single ticker

        Args:
            ticker: Ticker symbol (e.g., 'EURUSD=X', 'BTC-USD', 'AAPL')
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            interval: Data interval ('1m', '5m', '15m', '1h', '1d', '1wk', '1mo')
            validate: Whether to validate data quality

        Returns:
            DataFrame with OHLCV data, or None if fetch fails
        """
        # Check cache first
        cache_key = self._get_cache_key(ticker, start_date, end_date, interval)
        cached_data = self._load_from_cache(cache_key)
        if cached_data is not None:
            print(f"Loaded {ticker} from cache")
            return cached_data

        # Fetch from yfinance
        print(f"Fetching {ticker} from {start_date} to {end_date} ({interval})")
        try:
            data = yf.download(
                ticker,
                start=start_date,
                end=end_date,
                interval=interval,
                progress=False
            )

            if data.empty:
                print(f"Warning: No data returned for {ticker}")
                return None

            # Flatten multi-index columns if present
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)

            # Ensure we have required columns
            required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            if not all(col in data.columns for col in required_cols):
                print(f"Warning: Missing required columns for {ticker}")
                return None

            # Add ticker column
            data['Ticker'] = ticker

            if validate:
                data = self._validate_data(data, ticker)
                if data is None or data.empty:
                    return None

            # Save to cache
            self._save_to_cache(cache_key, data)

            print(f"Successfully fetched {len(data)} bars for {ticker}")
            return data

        except Exception as e:
            print(f"Error fetching {ticker}: {e}")
            return None

    def _validate_data(self, data: pd.DataFrame, ticker: str) -> Optional[pd.DataFrame]:
        """
        Validate data quality

        Args:
            data: DataFrame to validate
            ticker: Ticker symbol for error messages

        Returns:
            Cleaned DataFrame or None if validation fails
        """
        original_len = len(data)

        # Remove rows with NaN values
        data = data.dropna()
        if len(data) < original_len:
            print(f"Warning: Removed {original_len - len(data)} rows with NaN values from {ticker}")

        # Check for negative prices
        price_cols = ['Open', 'High', 'Low', 'Close']
        if (data[price_cols] <= 0).any().any():
            print(f"Warning: Found negative prices in {ticker}, removing...")
            data = data[(data[price_cols] > 0).all(axis=1)]

        # Check for extreme outliers (price changes > 50% in one bar)
        data['pct_change'] = data['Close'].pct_change().abs()
        extreme_moves = data['pct_change'] > 0.5
        if extreme_moves.any():
            print(f"Warning: Found {extreme_moves.sum()} extreme price moves in {ticker}")
            # Keep them but flag for review
            data['extreme_move'] = extreme_moves

        data = data.drop('pct_change', axis=1)

        # Check for sufficient data
        if len(data) < 10:
            print(f"Warning: Insufficient data for {ticker} (only {len(data)} bars)")
            return None

        return data

    def fetch_multiple(
        self,
        tickers: List[str],
        start_date: str,
        end_date: str,
        interval: str = '1d',
        validate: bool = True
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch historical data for multiple tickers

        Args:
            tickers: List of ticker symbols
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            interval: Data interval
            validate: Whether to validate data quality

        Returns:
            Dictionary mapping ticker to DataFrame
        """
        results = {}

        for ticker in tickers:
            data = self.fetch_ticker(ticker, start_date, end_date, interval, validate)
            if data is not None:
                results[ticker] = data

        print(f"\nSuccessfully fetched {len(results)}/{len(tickers)} tickers")
        return results

    def get_ticker_info(self, ticker: str) -> dict:
        """
        Get metadata about a ticker

        Args:
            ticker: Ticker symbol

        Returns:
            Dictionary with ticker information
        """
        try:
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info
            return {
                'symbol': ticker,
                'name': info.get('longName', ticker),
                'type': self._detect_asset_type(ticker),
                'currency': info.get('currency', 'USD'),
                'exchange': info.get('exchange', 'Unknown'),
            }
        except Exception as e:
            print(f"Warning: Could not fetch info for {ticker}: {e}")
            return {
                'symbol': ticker,
                'type': self._detect_asset_type(ticker),
            }

    def _detect_asset_type(self, ticker: str) -> str:
        """Detect asset type from ticker format"""
        if '=X' in ticker:
            return 'forex'
        elif '-USD' in ticker or '-BTC' in ticker or '-ETH' in ticker:
            return 'crypto'
        else:
            return 'stock'

    def clear_cache(self):
        """Clear all cached data"""
        for file in self.cache_dir.glob('*.pkl'):
            file.unlink()
        print(f"Cleared cache directory: {self.cache_dir}")


# Example usage
if __name__ == '__main__':
    # Initialize fetcher
    fetcher = DataFetcher()

    # Fetch single ticker
    eurusd = fetcher.fetch_ticker('EURUSD=X', '2023-01-01', '2026-03-01')
    if eurusd is not None:
        print(f"\nEURUSD Data:")
        print(eurusd.head())
        print(f"Shape: {eurusd.shape}")

    # Fetch multiple tickers
    tickers = ['EURUSD=X', 'GBPUSD=X', 'BTC-USD', 'ETH-USD']
    data = fetcher.fetch_multiple(tickers, '2023-01-01', '2026-03-01')

    # Get ticker info
    info = fetcher.get_ticker_info('EURUSD=X')
    print(f"\nTicker Info: {info}")
