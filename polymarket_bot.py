"""
Polymarket BTC Up/Down 15-minute trading bot.

Strategy: after the first two 5-minute candles of a 15-minute interval
both close in the same direction, bet that the 15-minute candle will
continue in that direction.

Setup:
  1. Copy .env.example to .env and fill in your credentials
  2. pip install py-clob-client python-dotenv requests
  3. python polymarket_bot.py

Environment variables:
  PRIVATE_KEY      Polygon wallet private key (hex, with or without 0x)
  WALLET_ADDRESS   Polygon wallet public address
  BET_SIZE_USDC    USDC to risk per trade (default: 1.0)
  DRY_RUN          Set to "false" to place real orders (default: true)
"""

import json
import os
import time
import logging
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

CLOB_HOST  = "https://clob.polymarket.com"
GAMMA_API  = "https://gamma-api.polymarket.com"
KRAKEN_API = "https://api.kraken.com"
CHAIN_ID   = 137  # Polygon mainnet

PRIVATE_KEY    = os.getenv("PRIVATE_KEY", "")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS", "")
BET_SIZE_USDC  = float(os.getenv("BET_SIZE_USDC", "1.0"))
DRY_RUN        = os.getenv("DRY_RUN", "true").lower() != "false"

# How long after the 15m interval start to check (T + 10 min + small buffer)
CHECK_DELAY  = 600 + 10   # seconds
# GTD order expiry relative to interval start (14 min gives 1 min before close)
ORDER_EXPIRY = 840        # seconds


# ── Candle helpers ─────────────────────────────────────────────────────────────

def candle_direction(open_price, close_price) -> int:
    """Return 1 for up, -1 for down, 0 for doji."""
    o, c = float(open_price), float(close_price)
    return 1 if c > o else (-1 if c < o else 0)


def get_two_5m_candles(interval_start: int):
    """
    Fetch the first two completed 5m candles from Kraken for a 15m interval.
    Returns (candle0, candle1) or (None, None) on failure.
    Kraken OHLC format: [time, open, high, low, close, vwap, volume, count]
    """
    try:
        resp = requests.get(
            f"{KRAKEN_API}/0/public/OHLC",
            params={"pair": "XBTUSD", "interval": 5, "since": interval_start - 1},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        log.error(f"Kraken API error: {e}")
        return None, None

    if data.get("error"):
        log.error(f"Kraken API error: {data['error']}")
        return None, None

    candles = data.get("result", {}).get("XXBTZUSD", [])
    # Build a lookup by open-time so order doesn't matter
    by_time = {int(c[0]): c for c in candles}

    t0, t1 = interval_start, interval_start + 300
    if t0 not in by_time or t1 not in by_time:
        log.warning(f"Missing Kraken candles for t={t0} or t={t1}")
        return None, None

    c0, c1 = by_time[t0], by_time[t1]

    # Confirm c1 is closed (its close time = open_time + 300s)
    if t1 + 300 > time.time():
        log.warning("Second 5m candle not yet closed — too early")
        return None, None

    return c0, c1


# ── Polymarket helpers ─────────────────────────────────────────────────────────

def get_btc_15m_market(interval_start: int) -> dict | None:
    """Look up the Polymarket BTC 15m market for a given interval start (Unix ts)."""
    slug = f"btc-updown-15m-{interval_start}"
    try:
        resp = requests.get(f"{GAMMA_API}/events", params={"slug": slug}, timeout=10)
        resp.raise_for_status()
        events = resp.json()
    except Exception as e:
        log.error(f"Gamma API error: {e}")
        return None

    if not events:
        log.warning(f"No Polymarket market found for slug: {slug}")
        return None

    markets = events[0].get("markets", [])
    if not markets:
        log.warning(f"Event exists but has no markets for {slug}")
        return None

    m         = markets[0]
    raw_ids   = m.get("clobTokenIds", [])
    # Gamma API returns clobTokenIds as a JSON-encoded string
    if isinstance(raw_ids, str):
        try:
            raw_ids = json.loads(raw_ids)
        except json.JSONDecodeError:
            raw_ids = []
    token_ids = raw_ids
    if len(token_ids) < 2:
        log.warning("Market is missing clobTokenIds")
        return None

    return {
        "slug":         slug,
        "condition_id": m["conditionId"],
        "yes_token_id": token_ids[0],  # "Up" outcome
        "no_token_id":  token_ids[1],  # "Down" outcome
        "tick_size":    str(m.get("minimumTickSize", "0.01")),
        "neg_risk":     bool(m.get("negRisk", False)),
    }


def round_to_tick(value: float, tick_size: str) -> float:
    tick = float(tick_size)
    decimals = (
        len(tick_size.rstrip("0").split(".")[-1])
        if "." in tick_size else 0
    )
    return round(round(value / tick) * tick, decimals)


def get_midpoint_price(client, token_id: str) -> float:
    """Fetch mid price; fall back to 0.5 on any error."""
    try:
        result = client.get_midpoint(token_id)
        return float(result.get("mid", 0.5))
    except Exception as e:
        log.warning(f"Could not fetch midpoint ({e}), using 0.5")
        return 0.5


def place_order(client, token_id: str, price: float, size: float,
                tick_size: str, neg_risk: bool, expiry: int, label: str):
    """Submit a GTD limit buy order."""
    from py_clob_client.clob_types import OrderArgs, OrderType
    from py_clob_client.order_builder.constants import BUY

    price = round_to_tick(price, tick_size)
    size  = round(size, 2)

    if DRY_RUN:
        log.info(
            f"[DRY RUN] Would buy {size} shares of {label} @ ${price:.4f} "
            f"(≈${price * size:.2f} USDC)  expiry={expiry}"
        )
        return {"dry_run": True}

    try:
        result = client.create_and_post_order(
            OrderArgs(
                token_id=token_id,
                price=price,
                size=size,
                side=BUY,
                expiration=expiry,
            ),
            options={"tick_size": tick_size, "neg_risk": neg_risk},
            order_type=OrderType.GTD,
        )
        log.info(
            f"Order placed | {label} | {size} shares @ ${price:.4f} | "
            f"id={result.get('orderID')} | status={result.get('status')}"
        )
        return result
    except Exception as e:
        log.error(f"Order placement failed: {e}")
        return None


# ── Core logic ─────────────────────────────────────────────────────────────────

DIRECTION_LABEL = {1: "UP", -1: "DOWN", 0: "DOJI"}


def process_interval(client, interval_start: int):
    dt = datetime.fromtimestamp(interval_start, tz=timezone.utc)
    log.info(f"=== 15m interval {dt.strftime('%Y-%m-%d %H:%M:%S')} UTC ===")

    # 1. Get the two completed 5m candles from Binance
    c0, c1 = get_two_5m_candles(interval_start)
    if c0 is None:
        log.warning("Could not fetch 5m candles — skipping interval")
        return

    dir0 = candle_direction(c0[1], c0[4])  # indices: [1]=open, [4]=close
    dir1 = candle_direction(c1[1], c1[4])
    log.info(f"5m[0]: {DIRECTION_LABEL[dir0]}  |  5m[1]: {DIRECTION_LABEL[dir1]}")

    # 2. Check for a signal
    if dir0 != dir1 or dir0 == 0:
        log.info("No clear signal (mixed or doji) — skipping trade")
        return

    direction = dir0
    log.info(f"Signal: {DIRECTION_LABEL[direction]} — entering bet")

    # 3. Fetch Polymarket market
    market = get_btc_15m_market(interval_start)
    if market is None:
        return

    # 4. Choose token based on direction
    if direction == 1:
        token_id = market["yes_token_id"]
        outcome  = "UP (YES)"
    else:
        token_id = market["no_token_id"]
        outcome  = "DOWN (NO)"

    # 5. Price: mid + 2 ticks so the order is likely to fill quickly
    mid   = get_midpoint_price(client, token_id)
    price = min(
        round_to_tick(mid + 2 * float(market["tick_size"]), market["tick_size"]),
        0.99,
    )
    size  = BET_SIZE_USDC / price
    log.info(
        f"Market: {market['slug']} | Outcome: {outcome} | "
        f"mid={mid:.4f}  bid={price:.4f}  size={size:.2f} shares"
    )

    # 6. Place GTD order expiring 14 minutes into the interval
    expiry = interval_start + ORDER_EXPIRY
    place_order(
        client, token_id, price, size,
        market["tick_size"], market["neg_risk"], expiry, outcome,
    )


# ── Client setup ───────────────────────────────────────────────────────────────

def build_client():
    from py_clob_client.client import ClobClient

    if not PRIVATE_KEY or not WALLET_ADDRESS:
        raise ValueError(
            "PRIVATE_KEY and WALLET_ADDRESS must be set in your .env file. "
            "In DRY_RUN mode the client is still needed for market data reads."
        )

    log.info("Initialising Polymarket CLOB client (deriving API credentials)...")
    # create_or_derive_api_creds() is deterministic — safe to call on every startup
    temp = ClobClient(CLOB_HOST, key=PRIVATE_KEY, chain_id=CHAIN_ID)
    creds = temp.create_or_derive_api_creds()

    client = ClobClient(
        CLOB_HOST,
        key=PRIVATE_KEY,
        chain_id=CHAIN_ID,
        creds=creds,
        signature_type=0,       # 0 = EOA (standard wallet)
        funder=WALLET_ADDRESS,
    )
    log.info("Client ready.")
    return client


# ── Main loop ──────────────────────────────────────────────────────────────────

def main():
    log.info(
        f"Polymarket BTC 15m bot starting | "
        f"bet_size=${BET_SIZE_USDC:.2f} USDC | dry_run={DRY_RUN}"
    )
    if DRY_RUN:
        log.info("DRY RUN mode — no real orders will be placed. Set DRY_RUN=false to trade.")

    client = build_client()
    traded_intervals: set[int] = set()

    while True:
        now            = time.time()
        interval_start = int(now // 900) * 900
        check_time     = interval_start + CHECK_DELAY

        if now >= check_time and interval_start not in traded_intervals:
            traded_intervals.add(interval_start)
            try:
                process_interval(client, interval_start)
            except Exception as e:
                log.exception(f"Unexpected error in process_interval: {e}")

            # Prune intervals older than 2 hours
            cutoff = interval_start - 7200
            traded_intervals = {t for t in traded_intervals if t >= cutoff}

        # Sleep until just before the next check point
        next_check = interval_start + CHECK_DELAY
        if now >= next_check:
            next_check = interval_start + 900 + CHECK_DELAY

        sleep_sec = max(1.0, next_check - time.time() - 5)
        next_dt   = datetime.fromtimestamp(next_check, tz=timezone.utc)
        log.debug(
            f"Sleeping {sleep_sec:.0f}s — "
            f"next check at {next_dt.strftime('%H:%M:%S')} UTC"
        )
        time.sleep(sleep_sec)


if __name__ == "__main__":
    main()
