"""MT5 Bridge — runs on Windows (outside Docker), polls MetaTrader5 and POSTs to Oracle.

Usage:
    python scripts/mt5_bridge.py

Requires: MetaTrader5, requests
    pip install MetaTrader5 requests
"""

import time
import json
import sys
import os
import logging
from datetime import datetime, timezone

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [mt5-bridge] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("mt5_bridge")

# ── Config ────────────────────────────────────────────────────────────────────

ORACLE_BASE_URL = os.getenv("ORACLE_URL", "http://localhost:8000")
INGEST_ENDPOINT = f"{ORACLE_BASE_URL}/api/v1/market/ingest"

MT5_PATH = os.getenv(
    "MT5_PATH",
    r"C:\Users\<user>\AppData\Roaming\MetaTrader 5 - ActivTrades\terminal64.exe",
)

SYMBOLS = [
    "PETR4", "VALE3", "WINQ25", "DOLFUT",
    "EURUSD", "XAUUSD", "US100", "USDJPY",
]

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "5"))  # seconds


# ── MT5 helpers ───────────────────────────────────────────────────────────────

def connect_mt5():
    try:
        import MetaTrader5 as mt5
    except ImportError:
        log.error("MetaTrader5 package not found. Install it: pip install MetaTrader5")
        sys.exit(1)

    # Try with explicit path first (reuses the already-logged-in terminal).
    # Fall back to no arguments if the path is wrong or MT5 is in PATH.
    initialized = False
    if MT5_PATH and os.path.exists(MT5_PATH):
        log.info(f"Initializing MT5 with path: {MT5_PATH}")
        initialized = mt5.initialize(path=MT5_PATH)
        if not initialized:
            log.warning(f"MT5 initialize with path failed ({mt5.last_error()}) — retrying without path")

    if not initialized:
        log.info("Initializing MT5 without explicit path")
        initialized = mt5.initialize()

    if not initialized:
        log.error(f"MT5 initialize failed: {mt5.last_error()}")
        sys.exit(1)

    info = mt5.account_info()
    if info:
        log.info(f"Connected: {info.server} | account {info.login} | {info.currency}")
    else:
        log.warning("Connected but no account info returned — terminal may not be logged in")

    return mt5


def get_tick(mt5, symbol: str) -> dict | None:
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return None
    return {
        "symbol": symbol,
        "price": round((tick.bid + tick.ask) / 2, 5),
        "bid": round(tick.bid, 5),
        "ask": round(tick.ask, 5),
        "spread": round(tick.ask - tick.bid, 5),
        "volume": float(tick.volume),
        "timestamp": datetime.fromtimestamp(tick.time, tz=timezone.utc).isoformat(),
    }


# ── Ingest POST ───────────────────────────────────────────────────────────────

_session = requests.Session()
_session.headers.update({"Content-Type": "application/json"})


def post_ingest(payload: dict) -> bool:
    try:
        r = _session.post(INGEST_ENDPOINT, json=payload, timeout=3)
        r.raise_for_status()
        return True
    except requests.RequestException as exc:
        log.warning(f"Ingest POST failed for {payload['symbol']}: {exc}")
        return False


# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    log.info(f"Starting MT5 Bridge → {INGEST_ENDPOINT}")
    log.info(f"Symbols: {', '.join(SYMBOLS)}")
    log.info(f"Poll interval: {POLL_INTERVAL}s")

    mt5 = connect_mt5()

    ok_count = 0
    fail_count = 0

    try:
        while True:
            for sym in SYMBOLS:
                tick = get_tick(mt5, sym)
                if tick is None:
                    log.debug(f"No tick for {sym}")
                    fail_count += 1
                    continue
                if post_ingest(tick):
                    ok_count += 1
                else:
                    fail_count += 1

            log.info(f"Tick cycle done | ok={ok_count} fail={fail_count}")
            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        log.info("Interrupted by user")
    finally:
        mt5.shutdown()
        log.info("MT5 shutdown. Bridge stopped.")


if __name__ == "__main__":
    main()
