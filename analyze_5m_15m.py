"""
Analyze the probability of a 15m candle being up/down
when the first two 5m candles in that interval are both the same direction.
"""

import pandas as pd
import sys
from data.fetcher import DataFetcher


def candle_direction(open_price, close_price):
    """Return 1 for up, -1 for down, 0 for doji"""
    if close_price > open_price:
        return 1
    elif close_price < open_price:
        return -1
    return 0


def align_5m_to_15m(df_5m, df_15m):
    """
    For each 15m candle, find the first two 5m candles within that interval.
    Returns a DataFrame with 15m candle data plus first two 5m directions.
    """
    # Ensure both have tz-naive or consistent tz
    idx_5m = df_5m.index
    idx_15m = df_15m.index

    rows = []
    for ts_15m in idx_15m:
        # The three 5m candles that make up this 15m candle start at:
        # ts_15m, ts_15m+5m, ts_15m+10m
        t0 = ts_15m
        t1 = ts_15m + pd.Timedelta(minutes=5)

        if t0 not in idx_5m or t1 not in idx_5m:
            print('unexpected missing 5m candle')
            continue

        c5_0 = df_5m.loc[t0]
        c5_1 = df_5m.loc[t1]
        c15 = df_15m.loc[ts_15m]


        dir_5m_0 = candle_direction(c5_0['Open'], c5_0['Close'])
        dir_5m_1 = candle_direction(c5_1['Open'], c5_1['Close'])
        dir_15m = candle_direction(c15['Open'], c15['Close'])

        rows.append({
            'timestamp': ts_15m,
            'dir_5m_0': dir_5m_0,
            'dir_5m_1': dir_5m_1,
            'dir_15m': dir_15m,
            'open_15m': c15['Open'],
            'close_15m': c15['Close'],
        })

    return pd.DataFrame(rows).set_index('timestamp')


def analyze(ticker, start_date, end_date):
    fetcher = DataFetcher()

    print(f"\nFetching data for {ticker} from {start_date} to {end_date}")
    df_5m = fetcher.fetch_ticker(ticker, start_date, end_date, interval='5m')
    df_15m = fetcher.fetch_ticker(ticker, start_date, end_date, interval='15m')

    if df_5m is None or df_15m is None:
        print("Failed to fetch data.")
        return

    # Strip timezone for consistent comparison
    df_5m.index = df_5m.index.tz_localize(None) if df_5m.index.tz is not None else df_5m.index
    df_15m.index = df_15m.index.tz_localize(None) if df_15m.index.tz is not None else df_15m.index

    print(f"\n5m bars:  {len(df_5m)}")
    print(f"15m bars: {len(df_15m)}")

    aligned = align_5m_to_15m(df_5m, df_15m)
    print(f"Matched 15m candles with two 5m candles: {len(aligned)}")

    if aligned.empty:
        print("No aligned data found.")
        return

    # Filter: both first two 5m candles are same direction (non-doji)
    both_up = (aligned['dir_5m_0'] == 1) & (aligned['dir_5m_1'] == 1)
    both_down = (aligned['dir_5m_0'] == -1) & (aligned['dir_5m_1'] == -1)
    same_dir = both_up | both_down

    subset = aligned[same_dir].copy()
    print(f"\nCandles where first two 5m bars are same direction: {len(subset)}")
    print(f"  Both up:   {both_up.sum()}")
    print(f"  Both down: {both_down.sum()}")

    if subset.empty:
        print("No matching candles found.")
        return

    # --- When both 5m candles are UP ---
    up_subset = aligned[both_up]
    if len(up_subset) > 0:
        up_15m_up = (up_subset['dir_15m'] == 1).sum()
        up_15m_down = (up_subset['dir_15m'] == -1).sum()
        up_15m_doji = (up_subset['dir_15m'] == 0).sum()
        print(f"\nWhen first two 5m candles are BOTH UP (n={len(up_subset)}):")
        print(f"  15m UP:   {up_15m_up:4d}  ({100*up_15m_up/len(up_subset):.1f}%)")
        print(f"  15m DOWN: {up_15m_down:4d}  ({100*up_15m_down/len(up_subset):.1f}%)")
        print(f"  15m DOJI: {up_15m_doji:4d}  ({100*up_15m_doji/len(up_subset):.1f}%)")

    # --- When both 5m candles are DOWN ---
    down_subset = aligned[both_down]
    if len(down_subset) > 0:
        dn_15m_up = (down_subset['dir_15m'] == 1).sum()
        dn_15m_down = (down_subset['dir_15m'] == -1).sum()
        dn_15m_doji = (down_subset['dir_15m'] == 0).sum()
        print(f"\nWhen first two 5m candles are BOTH DOWN (n={len(down_subset)}):")
        print(f"  15m UP:   {dn_15m_up:4d}  ({100*dn_15m_up/len(down_subset):.1f}%)")
        print(f"  15m DOWN: {dn_15m_down:4d}  ({100*dn_15m_down/len(down_subset):.1f}%)")
        print(f"  15m DOJI: {dn_15m_doji:4d}  ({100*dn_15m_doji/len(down_subset):.1f}%)")

    # --- Combined: same direction ---
    same_15m_matches = (
        ((subset['dir_5m_0'] == 1) & (subset['dir_15m'] == 1)) |
        ((subset['dir_5m_0'] == -1) & (subset['dir_15m'] == -1))
    ).sum()
    same_15m_opposite = (
        ((subset['dir_5m_0'] == 1) & (subset['dir_15m'] == -1)) |
        ((subset['dir_5m_0'] == -1) & (subset['dir_15m'] == 1))
    ).sum()
    same_15m_doji = (subset['dir_15m'] == 0).sum()

    print(f"\nCombined (both 5m same direction, n={len(subset)}):")
    print(f"  15m continues same direction: {same_15m_matches:4d}  ({100*same_15m_matches/len(subset):.1f}%)")
    print(f"  15m reverses direction:        {same_15m_opposite:4d}  ({100*same_15m_opposite/len(subset):.1f}%)")
    print(f"  15m doji:                      {same_15m_doji:4d}  ({100*same_15m_doji/len(subset):.1f}%)")

    # Baseline: overall 15m direction distribution
    total = len(aligned)
    base_up = (aligned['dir_15m'] == 1).sum()
    base_down = (aligned['dir_15m'] == -1).sum()
    base_doji = (aligned['dir_15m'] == 0).sum()
    print(f"\nBaseline 15m direction (all candles, n={total}):")
    print(f"  UP:   {base_up:4d}  ({100*base_up/total:.1f}%)")
    print(f"  DOWN: {base_down:4d}  ({100*base_down/total:.1f}%)")
    print(f"  DOJI: {base_doji:4d}  ({100*base_doji/total:.1f}%)")


if __name__ == '__main__':
    # Default: SPY over last ~55 days (5m/15m data is limited to ~60 days on yfinance)
    ticker = sys.argv[1] if len(sys.argv) > 1 else 'BTC-USD'
    start = sys.argv[2] if len(sys.argv) > 2 else '2026-01-10'
    end = sys.argv[3] if len(sys.argv) > 3 else '2026-03-10'

    analyze(ticker, start, end)
