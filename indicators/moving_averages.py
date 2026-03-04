"""
Moving Average calculations
Supports SMA, EMA, and WMA
"""

import pandas as pd
import numpy as np
from typing import Union, List


class MovingAverage:
    """Calculate various types of moving averages"""

    @staticmethod
    def sma(prices: Union[pd.Series, np.ndarray], period: int) -> pd.Series:
        """
        Simple Moving Average

        Args:
            prices: Price series
            period: Number of periods

        Returns:
            SMA series
        """
        if isinstance(prices, np.ndarray):
            prices = pd.Series(prices)

        return prices.rolling(window=period, min_periods=period).mean()

    @staticmethod
    def ema(prices: Union[pd.Series, np.ndarray], period: int) -> pd.Series:
        """
        Exponential Moving Average

        Args:
            prices: Price series
            period: Number of periods

        Returns:
            EMA series
        """
        if isinstance(prices, np.ndarray):
            prices = pd.Series(prices)

        return prices.ewm(span=period, adjust=False, min_periods=period).mean()

    @staticmethod
    def wma(prices: Union[pd.Series, np.ndarray], period: int) -> pd.Series:
        """
        Weighted Moving Average
        More recent prices have higher weight

        Args:
            prices: Price series
            period: Number of periods

        Returns:
            WMA series
        """
        if isinstance(prices, np.ndarray):
            prices = pd.Series(prices)

        weights = np.arange(1, period + 1)

        def weighted_mean(x):
            if len(x) < period:
                return np.nan
            return np.dot(x, weights) / weights.sum()

        return prices.rolling(window=period).apply(weighted_mean, raw=True)

    @staticmethod
    def calculate_ma(
        prices: Union[pd.Series, np.ndarray],
        period: int,
        ma_type: str = 'SMA'
    ) -> pd.Series:
        """
        Calculate moving average of specified type

        Args:
            prices: Price series
            period: Number of periods
            ma_type: Type of MA ('SMA', 'EMA', 'WMA')

        Returns:
            MA series

        Raises:
            ValueError: If ma_type is not supported
        """
        ma_type = ma_type.upper()

        if ma_type == 'SMA':
            return MovingAverage.sma(prices, period)
        elif ma_type == 'EMA':
            return MovingAverage.ema(prices, period)
        elif ma_type == 'WMA':
            return MovingAverage.wma(prices, period)
        else:
            raise ValueError(f"Unsupported MA type: {ma_type}. Use 'SMA', 'EMA', or 'WMA'")


def add_moving_averages(
    df: pd.DataFrame,
    periods: List[int],
    ma_types: List[str] = ['SMA'],
    price_column: str = 'Close'
) -> pd.DataFrame:
    """
    Add moving averages to DataFrame

    Args:
        df: DataFrame with OHLCV data
        periods: List of MA periods to calculate
        ma_types: List of MA types ('SMA', 'EMA', 'WMA')
        price_column: Column to calculate MA on

    Returns:
        DataFrame with MA columns added
    """
    df = df.copy()

    for ma_type in ma_types:
        for period in periods:
            col_name = f'{ma_type}_{period}'
            df[col_name] = MovingAverage.calculate_ma(
                df[price_column],
                period,
                ma_type
            )

    return df


def calculate_distance_to_ma(
    df: pd.DataFrame,
    ma_column: str,
    price_column: str = 'Close',
    as_percentage: bool = True
) -> pd.Series:
    """
    Calculate distance from price to moving average

    Args:
        df: DataFrame with price and MA data
        ma_column: Name of MA column
        price_column: Name of price column
        as_percentage: Return as percentage (True) or absolute (False)

    Returns:
        Series with distance values
    """
    distance = df[price_column] - df[ma_column]

    if as_percentage:
        distance = (distance / df[ma_column]) * 100

    return distance


def is_price_near_ma(
    df: pd.DataFrame,
    ma_column: str,
    threshold_pct: float = 2.0,
    price_column: str = 'Close'
) -> pd.Series:
    """
    Check if price is near moving average

    Args:
        df: DataFrame with price and MA data
        ma_column: Name of MA column
        threshold_pct: Threshold percentage (e.g., 2.0 for 2%)
        price_column: Name of price column

    Returns:
        Boolean series indicating if price is near MA
    """
    distance_pct = calculate_distance_to_ma(df, ma_column, price_column, as_percentage=True)
    return distance_pct.abs() <= threshold_pct


def calculate_ma_slope(df: pd.DataFrame, ma_column: str, lookback: int = 5) -> pd.Series:
    """
    Calculate slope/direction of moving average

    Args:
        df: DataFrame with MA data
        ma_column: Name of MA column
        lookback: Number of periods to calculate slope over

    Returns:
        Series with slope values (positive = uptrend, negative = downtrend)
    """
    ma_values = df[ma_column]
    slope = ma_values.diff(lookback) / lookback
    return slope


def detect_ma_crossover(
    df: pd.DataFrame,
    fast_ma_column: str,
    slow_ma_column: str
) -> pd.DataFrame:
    """
    Detect moving average crossovers

    Args:
        df: DataFrame with MA data
        fast_ma_column: Name of faster MA column
        slow_ma_column: Name of slower MA column

    Returns:
        DataFrame with crossover signals
    """
    df = df.copy()

    # Calculate position relative to each other
    df['fast_above_slow'] = df[fast_ma_column] > df[slow_ma_column]

    # Detect crossovers
    df['bullish_cross'] = (
        (df['fast_above_slow'] == True) &
        (df['fast_above_slow'].shift(1) == False)
    )

    df['bearish_cross'] = (
        (df['fast_above_slow'] == False) &
        (df['fast_above_slow'].shift(1) == True)
    )

    return df


# Example usage
if __name__ == '__main__':
    # Create sample data
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    np.random.seed(42)
    prices = 100 + np.cumsum(np.random.randn(100) * 2)

    df = pd.DataFrame({
        'Date': dates,
        'Close': prices
    })

    # Calculate different MAs
    df['SMA_20'] = MovingAverage.sma(df['Close'], 20)
    df['EMA_20'] = MovingAverage.ema(df['Close'], 20)
    df['WMA_20'] = MovingAverage.wma(df['Close'], 20)

    # Or use helper function
    df = add_moving_averages(df, [20, 50], ['SMA', 'EMA'])

    # Check distance to MA
    df['distance_to_sma20'] = calculate_distance_to_ma(df, 'SMA_20')
    df['near_sma20'] = is_price_near_ma(df, 'SMA_20', threshold_pct=2.0)

    print(df.tail(10))
    print(f"\nBars near SMA(20): {df['near_sma20'].sum()}")
