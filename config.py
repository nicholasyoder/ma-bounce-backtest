"""
Configuration for MA Bounce Backtesting System
All parameters are configurable to test different strategies
"""

from typing import List, Dict, Any
from dataclasses import dataclass, field


@dataclass
class BacktestConfig:
    """Main configuration for the backtesting system"""

    # === Data Settings ===
    tickers: List[str] = field(default_factory=lambda: [
        'EURUSD=X',  # Forex
        'GBPUSD=X',
        'USDJPY=X',
        'BTC-USD',   # Crypto
        'ETH-USD',
    ])

    start_date: str = '2020-01-01'
    end_date: str = '2026-03-01'
    interval: str = '1d'  # Options: '1m', '5m', '15m', '1h', '1d', '1wk', '1mo'

    # === Moving Average Settings ===
    ma_periods: List[int] = field(default_factory=lambda: [10, 20, 30, 50, 100, 200])
    ma_types: List[str] = field(default_factory=lambda: ['SMA', 'EMA', 'WMA'])

    # === Bounce Detection Settings (all configurable) ===
    # How close to MA qualifies as a "touch" (as percentage, e.g., 0.02 = 2%)
    bounce_threshold_pct: float = 0.02

    # Minimum price reversal to count as successful bounce (percentage)
    min_bounce_size_pct: float = 0.02

    # Maximum bars to look ahead for reversal confirmation
    reversal_lookback_bars: int = 5

    # Minimum bars price must hold bounce before invalidation
    min_hold_bars: int = 2

    # === Advanced Bounce Criteria ===
    # Require volume confirmation (higher volume on bounce bar)
    require_volume_confirmation: bool = False

    # Classify bounces by direction
    track_support_vs_resistance: bool = True

    # Require trend context (only count bounces in trending markets)
    require_trend: bool = False
    trend_lookback_bars: int = 50  # Bars to determine trend

    # === Market Condition Filters ===
    # Minimum volatility (ATR) to consider
    min_atr_pct: float = 0.0

    # Maximum spread (for forex) as percentage
    max_spread_pct: float = 0.01

    # === Statistical Settings ===
    # Confidence level for statistical tests
    confidence_level: float = 0.95

    # Minimum sample size for significance
    min_samples: int = 30

    # === Optimization Settings ===
    # Parameter ranges for grid search
    optimize_ma_periods: bool = True
    ma_period_range: tuple = (5, 200, 5)  # (min, max, step)

    optimize_bounce_threshold: bool = True
    bounce_threshold_range: tuple = (0.005, 0.05, 0.005)  # 0.5% to 5%

    optimize_reversal_bars: bool = True
    reversal_bars_range: tuple = (3, 10, 1)

    # === Performance Settings ===
    cache_data: bool = True
    cache_dir: str = 'data/cache'
    parallel_processing: bool = True
    num_workers: int = 4

    # === Output Settings ===
    output_dir: str = 'results'
    generate_html_report: bool = True
    generate_charts: bool = True
    save_raw_results: bool = True
    verbose: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            'tickers': self.tickers,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'interval': self.interval,
            'ma_periods': self.ma_periods,
            'ma_types': self.ma_types,
            'bounce_threshold_pct': self.bounce_threshold_pct,
            'min_bounce_size_pct': self.min_bounce_size_pct,
            'reversal_lookback_bars': self.reversal_lookback_bars,
            'min_hold_bars': self.min_hold_bars,
            'require_volume_confirmation': self.require_volume_confirmation,
            'track_support_vs_resistance': self.track_support_vs_resistance,
            'require_trend': self.require_trend,
            'trend_lookback_bars': self.trend_lookback_bars,
        }

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'BacktestConfig':
        """Create config from dictionary"""
        return cls(**config_dict)


# Preset configurations for common scenarios
PRESETS = {
    'conservative': BacktestConfig(
        bounce_threshold_pct=0.01,  # Must touch MA closely
        min_bounce_size_pct=0.03,   # Require larger bounce
        reversal_lookback_bars=3,   # Quick reversal
        require_volume_confirmation=True,
    ),

    'aggressive': BacktestConfig(
        bounce_threshold_pct=0.03,  # Allow further from MA
        min_bounce_size_pct=0.01,   # Accept smaller bounces
        reversal_lookback_bars=10,  # Give more time
        require_volume_confirmation=False,
    ),

    'trending_only': BacktestConfig(
        require_trend=True,
        trend_lookback_bars=50,
        bounce_threshold_pct=0.02,
        min_bounce_size_pct=0.02,
    ),

    'forex_scalping': BacktestConfig(
        interval='15m',
        ma_periods=[10, 20, 50],
        bounce_threshold_pct=0.005,  # Tight for forex
        min_bounce_size_pct=0.005,
        reversal_lookback_bars=3,
    ),

    'crypto_swing': BacktestConfig(
        interval='4h',
        ma_periods=[20, 50, 100, 200],
        bounce_threshold_pct=0.03,  # Wider for crypto volatility
        min_bounce_size_pct=0.05,
        reversal_lookback_bars=5,
    ),
}


def load_config(preset: str = None, **kwargs) -> BacktestConfig:
    """
    Load configuration with optional preset and custom overrides

    Args:
        preset: Name of preset configuration ('conservative', 'aggressive', etc.)
        **kwargs: Any additional parameters to override

    Returns:
        BacktestConfig object

    Examples:
        # Use default config
        config = load_config()

        # Use preset
        config = load_config(preset='conservative')

        # Use preset with overrides
        config = load_config(preset='forex_scalping', tickers=['EURUSD=X'])

        # Custom config
        config = load_config(
            tickers=['BTC-USD'],
            ma_periods=[20, 50, 100],
            bounce_threshold_pct=0.025
        )
    """
    if preset and preset in PRESETS:
        config = PRESETS[preset]
        # Apply any overrides
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        return config
    else:
        return BacktestConfig(**kwargs)
