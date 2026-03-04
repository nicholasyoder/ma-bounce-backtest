"""
Configurable bounce detection for moving averages
Detects when price bounces off MA levels
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class BounceEvent:
    """Data class for bounce events"""
    index: int
    date: pd.Timestamp
    ticker: str
    ma_type: str
    ma_period: int
    bounce_type: str  # 'support' or 'resistance'
    touch_price: float
    ma_value: float
    distance_pct: float
    reversal_size_pct: float
    reversal_bars: int
    hold_bars: int
    success: bool
    max_favorable_move_pct: float
    volume_confirmed: bool


class BounceDetector:
    """Detect and analyze price bounces off moving averages"""

    def __init__(
        self,
        bounce_threshold_pct: float = 0.02,
        min_bounce_size_pct: float = 0.02,
        reversal_lookback_bars: int = 5,
        min_hold_bars: int = 2,
        require_volume_confirmation: bool = False,
        track_support_vs_resistance: bool = True
    ):
        """
        Initialize BounceDetector with configurable parameters

        Args:
            bounce_threshold_pct: How close to MA qualifies as touch (e.g., 0.02 = 2%)
            min_bounce_size_pct: Minimum reversal size to count as bounce
            reversal_lookback_bars: Bars to look ahead for reversal
            min_hold_bars: Minimum bars bounce must hold
            require_volume_confirmation: Require volume spike on bounce
            track_support_vs_resistance: Track bounce direction separately
        """
        self.bounce_threshold_pct = bounce_threshold_pct
        self.min_bounce_size_pct = min_bounce_size_pct
        self.reversal_lookback_bars = reversal_lookback_bars
        self.min_hold_bars = min_hold_bars
        self.require_volume_confirmation = require_volume_confirmation
        self.track_support_vs_resistance = track_support_vs_resistance

    def detect_bounces(
        self,
        df: pd.DataFrame,
        ma_column: str,
        ticker: str = 'Unknown'
    ) -> List[BounceEvent]:
        """
        Detect all bounce events in the data

        Args:
            df: DataFrame with OHLCV and MA data
            ma_column: Name of moving average column
            ticker: Ticker symbol for labeling

        Returns:
            List of BounceEvent objects
        """
        bounces = []
        df = df.copy()

        # Parse MA column name to get type and period
        ma_type, ma_period = self._parse_ma_column(ma_column)

        # Calculate distance to MA
        df['distance_pct'] = ((df['Close'] - df[ma_column]) / df[ma_column]) * 100

        # Calculate average volume for comparison
        if self.require_volume_confirmation and 'Volume' in df.columns:
            df['avg_volume'] = df['Volume'].rolling(window=20, min_periods=1).mean()

        # Iterate through data looking for MA touches
        for i in range(len(df) - self.reversal_lookback_bars):
            # Check if price is near MA
            distance = abs(df.iloc[i]['distance_pct'])

            if distance <= (self.bounce_threshold_pct * 100) and not pd.isna(df.iloc[i][ma_column]):
                # Determine bounce type (support vs resistance)
                bounce_type = self._determine_bounce_type(df, i, ma_column)

                if not self.track_support_vs_resistance or bounce_type is not None:
                    # Check for reversal
                    bounce_event = self._check_reversal(
                        df, i, ma_column, ticker, ma_type, ma_period, bounce_type
                    )

                    if bounce_event is not None:
                        bounces.append(bounce_event)

        return bounces

    def _parse_ma_column(self, ma_column: str) -> Tuple[str, int]:
        """Parse MA column name to extract type and period"""
        parts = ma_column.split('_')
        if len(parts) >= 2:
            ma_type = parts[0]
            try:
                ma_period = int(parts[1])
                return ma_type, ma_period
            except ValueError:
                return 'Unknown', 0
        return 'Unknown', 0

    def _determine_bounce_type(
        self,
        df: pd.DataFrame,
        index: int,
        ma_column: str
    ) -> Optional[str]:
        """
        Determine if bounce is support (from below) or resistance (from above)

        Args:
            df: DataFrame
            index: Current index
            ma_column: MA column name

        Returns:
            'support', 'resistance', or None
        """
        current_price = df.iloc[index]['Close']
        ma_value = df.iloc[index][ma_column]

        # Look at previous bars to determine approach direction
        lookback = min(3, index)
        if lookback == 0:
            return None

        prev_prices = df.iloc[index - lookback:index]['Close']
        prev_ma = df.iloc[index - lookback:index][ma_column]

        # Check if price was consistently above or below MA before touch
        if (prev_prices < prev_ma).mean() > 0.6:
            return 'support'  # Coming from below
        elif (prev_prices > prev_ma).mean() > 0.6:
            return 'resistance'  # Coming from above
        else:
            return None  # Unclear direction

    def _check_reversal(
        self,
        df: pd.DataFrame,
        touch_index: int,
        ma_column: str,
        ticker: str,
        ma_type: str,
        ma_period: int,
        bounce_type: Optional[str]
    ) -> Optional[BounceEvent]:
        """
        Check if price reverses after touching MA

        Args:
            df: DataFrame
            touch_index: Index where price touched MA
            ma_column: MA column name
            ticker: Ticker symbol
            ma_type: Type of MA
            ma_period: MA period
            bounce_type: 'support' or 'resistance'

        Returns:
            BounceEvent if bounce detected, None otherwise
        """
        touch_bar = df.iloc[touch_index]
        future_bars = df.iloc[touch_index + 1:touch_index + 1 + self.reversal_lookback_bars]

        if len(future_bars) < self.min_hold_bars:
            return None

        # Determine expected direction based on bounce type
        if bounce_type == 'support':
            # Expect price to move up
            expected_direction = 1
            reversal_prices = future_bars['Close'] - touch_bar['Close']
        elif bounce_type == 'resistance':
            # Expect price to move down
            expected_direction = -1
            reversal_prices = touch_bar['Close'] - future_bars['Close']
        else:
            # No clear direction - just look for any reversal
            reversal_prices = (future_bars['Close'] - touch_bar['Close']).abs()
            expected_direction = 0

        # Calculate reversal size as percentage
        reversal_pct = (reversal_prices / touch_bar['Close']) * 100

        # Find maximum favorable move
        max_reversal_idx = reversal_pct.idxmax() if len(reversal_pct) > 0 else None
        max_reversal_pct = reversal_pct.max() if len(reversal_pct) > 0 else 0

        # Check if meets minimum bounce size
        success = max_reversal_pct >= (self.min_bounce_size_pct * 100)

        # Check volume confirmation if required
        volume_confirmed = True
        if self.require_volume_confirmation and 'Volume' in df.columns:
            touch_volume = touch_bar['Volume']
            avg_volume = touch_bar.get('avg_volume', touch_volume)
            volume_confirmed = touch_volume > avg_volume

            if not volume_confirmed:
                return None  # Skip this bounce

        # Find how many bars the bounce held
        if success and max_reversal_idx is not None:
            hold_bars = df.index.get_loc(max_reversal_idx) - touch_index
            reversal_bars = hold_bars
        else:
            hold_bars = 0
            reversal_bars = 0

        # Check minimum hold requirement
        if success and hold_bars < self.min_hold_bars:
            success = False

        return BounceEvent(
            index=touch_index,
            date=touch_bar.name,
            ticker=ticker,
            ma_type=ma_type,
            ma_period=ma_period,
            bounce_type=bounce_type or 'unknown',
            touch_price=touch_bar['Close'],
            ma_value=touch_bar[ma_column],
            distance_pct=touch_bar['distance_pct'],
            reversal_size_pct=max_reversal_pct,
            reversal_bars=reversal_bars,
            hold_bars=hold_bars,
            success=success,
            max_favorable_move_pct=max_reversal_pct,
            volume_confirmed=volume_confirmed
        )

    def analyze_bounces(self, bounces: List[BounceEvent]) -> Dict:
        """
        Analyze bounce statistics

        Args:
            bounces: List of BounceEvent objects

        Returns:
            Dictionary with analysis results
        """
        if not bounces:
            return {
                'total_bounces': 0,
                'success_rate': 0.0,
                'avg_reversal_pct': 0.0,
                'avg_hold_bars': 0.0,
            }

        successful_bounces = [b for b in bounces if b.success]

        analysis = {
            'total_bounces': len(bounces),
            'successful_bounces': len(successful_bounces),
            'success_rate': len(successful_bounces) / len(bounces) * 100,
            'avg_reversal_pct': np.mean([b.reversal_size_pct for b in successful_bounces]) if successful_bounces else 0,
            'avg_hold_bars': np.mean([b.hold_bars for b in successful_bounces]) if successful_bounces else 0,
            'max_reversal_pct': max([b.reversal_size_pct for b in bounces]) if bounces else 0,
        }

        # Breakdown by bounce type if tracking
        if self.track_support_vs_resistance:
            support_bounces = [b for b in bounces if b.bounce_type == 'support']
            resistance_bounces = [b for b in bounces if b.bounce_type == 'resistance']

            analysis['support_count'] = len(support_bounces)
            analysis['resistance_count'] = len(resistance_bounces)

            if support_bounces:
                successful_support = [b for b in support_bounces if b.success]
                analysis['support_success_rate'] = len(successful_support) / len(support_bounces) * 100
            else:
                analysis['support_success_rate'] = 0

            if resistance_bounces:
                successful_resistance = [b for b in resistance_bounces if b.success]
                analysis['resistance_success_rate'] = len(successful_resistance) / len(resistance_bounces) * 100
            else:
                analysis['resistance_success_rate'] = 0

        return analysis

    def bounces_to_dataframe(self, bounces: List[BounceEvent]) -> pd.DataFrame:
        """Convert list of BounceEvent objects to DataFrame"""
        if not bounces:
            return pd.DataFrame()

        return pd.DataFrame([
            {
                'date': b.date,
                'ticker': b.ticker,
                'ma_type': b.ma_type,
                'ma_period': b.ma_period,
                'bounce_type': b.bounce_type,
                'touch_price': b.touch_price,
                'ma_value': b.ma_value,
                'distance_pct': b.distance_pct,
                'reversal_size_pct': b.reversal_size_pct,
                'reversal_bars': b.reversal_bars,
                'hold_bars': b.hold_bars,
                'success': b.success,
                'volume_confirmed': b.volume_confirmed,
            }
            for b in bounces
        ])


# Example usage
if __name__ == '__main__':
    # Create sample data
    dates = pd.date_range('2024-01-01', periods=200, freq='D')
    np.random.seed(42)

    # Generate price data that bounces off moving average
    base_trend = np.linspace(100, 150, 200)
    noise = np.random.randn(200) * 3
    prices = base_trend + noise

    df = pd.DataFrame({
        'Close': prices,
        'Volume': np.random.randint(1000, 10000, 200)
    }, index=dates)

    # Calculate MA
    df['SMA_20'] = df['Close'].rolling(window=20).mean()

    # Initialize detector with custom parameters
    detector = BounceDetector(
        bounce_threshold_pct=0.02,  # 2%
        min_bounce_size_pct=0.015,  # 1.5%
        reversal_lookback_bars=5,
        min_hold_bars=2,
        require_volume_confirmation=False,
        track_support_vs_resistance=True
    )

    # Detect bounces
    bounces = detector.detect_bounces(df, 'SMA_20', ticker='TEST')

    # Analyze results
    analysis = detector.analyze_bounces(bounces)

    print(f"Analysis Results:")
    for key, value in analysis.items():
        print(f"  {key}: {value}")

    print(f"\nFound {len(bounces)} bounce events")
    if bounces:
        print(f"First bounce: {bounces[0]}")
