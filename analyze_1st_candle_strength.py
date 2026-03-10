"""
Analyze the probability of a 15m candle continuing in the direction of the
first 5m candle, broken down by the body strength of that first 5m candle.

Body strength = |close - open| / (high - low)
  - 1.0 = pure marubozu (all body, no wicks)
  - 0.0 = pure doji or spinning top (all wick, no body)

Candles where high == low (zero-range) are excluded.
"""

import sys
import pandas as pd
from data.fetcher import DataFetcher


def body_strength(open_p, high_p, low_p, close_p) -> float:
    full_range = high_p - low_p
    if full_range == 0:
        return None  # exclude zero-range candles
    return abs(close_p - open_p) / full_range


def candle_direction(open_p, close_p) -> int:
    if close_p > open_p:
        return 1
    elif close_p < open_p:
        return -1
    return 0


def build_dataset(df_5m, df_15m) -> pd.DataFrame:
    """
    For each 15m candle, record the first 5m candle's direction,
    body strength, and the 15m candle's direction.
    """
    idx_5m  = set(df_5m.index)
    idx_15m = df_15m.index

    rows = []
    for ts_15m in idx_15m:
        if ts_15m not in idx_5m:
            continue

        c5  = df_5m.loc[ts_15m]
        c15 = df_15m.loc[ts_15m]

        strength = body_strength(c5['Open'], c5['High'], c5['Low'], c5['Close'])
        if strength is None:
            continue

        rows.append({
            'timestamp':  ts_15m,
            'dir_5m':     candle_direction(c5['Open'],  c5['Close']),
            'strength':   strength,
            'dir_15m':    candle_direction(c15['Open'], c15['Close']),
        })

    return pd.DataFrame(rows).set_index('timestamp')


def print_threshold_table(df: pd.DataFrame, thresholds: list[float]):
    """
    For each body-strength threshold, show stats for candles where
    the first 5m candle meets that threshold AND is non-doji.
    """
    header = f"{'Threshold':>10}  {'n':>5}  {'trades/day':>10}  {'15m same dir':>14}  {'15m opposite':>13}  {'15m doji':>9}"
    print(header)
    print("-" * len(header))

    # Approximate trading days in the dataset
    days = max((df.index.max() - df.index.min()).total_seconds() / 86400, 1)

    for t in thresholds:
        subset = df[(df['strength'] >= t) & (df['dir_5m'] != 0)]
        n = len(subset)
        if n == 0:
            print(f"{t:>10.0%}  {'—':>5}")
            continue

        same = (
            ((subset['dir_5m'] == 1)  & (subset['dir_15m'] == 1)) |
            ((subset['dir_5m'] == -1) & (subset['dir_15m'] == -1))
        ).sum()
        opp  = (
            ((subset['dir_5m'] == 1)  & (subset['dir_15m'] == -1)) |
            ((subset['dir_5m'] == -1) & (subset['dir_15m'] == 1))
        ).sum()
        doji = (subset['dir_15m'] == 0).sum()

        print(
            f"{t:>10.0%}  {n:>5}  {n/days:>10.1f}  "
            f"{same:>5} ({100*same/n:5.1f}%)  "
            f"{opp:>4} ({100*opp/n:5.1f}%)  "
            f"{doji:>3} ({100*doji/n:4.1f}%)"
        )


def print_direction_split(df: pd.DataFrame, threshold: float):
    """Show UP vs DOWN breakdown at a given threshold."""
    subset = df[(df['strength'] >= threshold) & (df['dir_5m'] != 0)]

    for direction, label in [(1, "UP"), (-1, "DOWN")]:
        grp = subset[subset['dir_5m'] == direction]
        if len(grp) == 0:
            continue
        same = (grp['dir_15m'] == direction).sum()
        opp  = (grp['dir_15m'] == -direction).sum()
        doji = (grp['dir_15m'] == 0).sum()
        n    = len(grp)
        print(
            f"  1st 5m {label:>4} (n={n:>4}): "
            f"15m continues {same:>4} ({100*same/n:.1f}%)  "
            f"reverses {opp:>4} ({100*opp/n:.1f}%)  "
            f"doji {doji:>2} ({100*doji/n:.1f}%)"
        )


def analyze(ticker: str, start_date: str, end_date: str):
    fetcher = DataFetcher()

    print(f"\nFetching {ticker} from {start_date} to {end_date}")
    df_5m  = fetcher.fetch_ticker(ticker, start_date, end_date, interval='5m')
    df_15m = fetcher.fetch_ticker(ticker, start_date, end_date, interval='15m')

    if df_5m is None or df_15m is None:
        print("Failed to fetch data.")
        return

    for df in (df_5m, df_15m):
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)

    print(f"5m bars: {len(df_5m)}  |  15m bars: {len(df_15m)}")

    data = build_dataset(df_5m, df_15m)
    print(f"Matched candles: {len(data)}\n")

    # ── Baseline ──────────────────────────────────────────────────────────────
    total     = len(data)
    base_up   = (data['dir_15m'] == 1).sum()
    base_down = (data['dir_15m'] == -1).sum()
    print(f"Baseline 15m direction (all {total} candles):")
    print(f"  UP {base_up} ({100*base_up/total:.1f}%)  "
          f"DOWN {base_down} ({100*base_down/total:.1f}%)\n")

    # ── Threshold sweep ───────────────────────────────────────────────────────
    thresholds = [0.0, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    print("First 5m candle body-strength threshold sweep:")
    print_threshold_table(data, thresholds)

    # ── UP/DOWN split at a few interesting thresholds ─────────────────────────
    for t in [0.0, 0.5, 0.7]:
        n = len(data[(data['strength'] >= t) & (data['dir_5m'] != 0)])
        print(f"\nUP / DOWN split at strength >= {t:.0%}  (n={n}):")
        print_direction_split(data, t)


if __name__ == '__main__':
    ticker = sys.argv[1] if len(sys.argv) > 1 else 'BTC-USD'
    start  = sys.argv[2] if len(sys.argv) > 2 else '2026-01-10'
    end    = sys.argv[3] if len(sys.argv) > 3 else '2026-03-10'
    analyze(ticker, start, end)
