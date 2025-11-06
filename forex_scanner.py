#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass
from typing import Iterable, List, Tuple

import requests

ALPHA_VANTAGE_ENDPOINT = "https://www.alphavantage.co/query"


@dataclass
class ForexQuote:
    pair: str
    rate: float
    last_refreshed: str
    bid: float | None
    ask: float | None


class ForexScannerError(RuntimeError):
    pass


def parse_pair(pair: str) -> Tuple[str, str]:
    if "/" not in pair:
        raise ForexScannerError(f"Invalid pair '{pair}'. Expected format like EUR/USD.")
    base, quote = pair.split("/", 1)
    base, quote = base.strip().upper(), quote.strip().upper()
    if not base or not quote:
        raise ForexScannerError(f"Invalid pair '{pair}'. Expected format like EUR/USD.")
    return base, quote


def fetch_quote(api_key: str, pair: str, session: requests.Session, timeout: float) -> ForexQuote:
    base, quote = parse_pair(pair)
    params = {
        "function": "CURRENCY_EXCHANGE_RATE",
        "from_currency": base,
        "to_currency": quote,
        "apikey": api_key,
    }

    try:
        response = session.get(ALPHA_VANTAGE_ENDPOINT, params=params, timeout=timeout)
    except requests.RequestException as exc:
        raise ForexScannerError(f"Network error while fetching {pair}: {exc}") from exc

    if response.status_code != 200:
        raise ForexScannerError(f"Alpha Vantage returned status {response.status_code} for {pair}")

    payload = response.json()

    if "Note" in payload:
        raise ForexScannerError(f"Alpha Vantage note for {pair}: {payload['Note']}")

    if "Error Message" in payload:
        raise ForexScannerError(f"Alpha Vantage error for {pair}: {payload['Error Message']}")

    data = payload.get("Realtime Currency Exchange Rate")
    if not data:
        raise ForexScannerError(f"Unexpected response format for {pair}: {payload}")

    rate_str = data.get("5. Exchange Rate")
    last_refreshed = data.get("6. Last Refreshed", "N/A")
    bid_str = data.get("8. Bid Price")
    ask_str = data.get("9. Ask Price")

    if rate_str is None:
        raise ForexScannerError(f"Missing rate data for {pair}: {payload}")

    try:
        rate = float(rate_str)
        bid = float(bid_str) if bid_str is not None else None
        ask = float(ask_str) if ask_str is not None else None
    except ValueError as exc:
        raise ForexScannerError(f"Invalid numeric data for {pair}: {exc}") from exc

    return ForexQuote(pair=f"{base}/{quote}", rate=rate, last_refreshed=last_refreshed, bid=bid, ask=ask)


def render_table(quotes: Iterable[ForexQuote]) -> str:
    headers = ("Pair", "Rate", "Bid", "Ask", "Last Refreshed")
    rows: List[List[str]] = []
    for quote in quotes:
        rows.append(
            [
                quote.pair,
                f"{quote.rate:,.6f}",
                f"{quote.bid:,.6f}" if quote.bid is not None else "—",
                f"{quote.ask:,.6f}" if quote.ask is not None else "—",
                quote.last_refreshed,
            ]
        )

    col_widths = [len(header) for header in headers]
    for row in rows:
        for idx, value in enumerate(row):
            col_widths[idx] = max(col_widths[idx], len(value))

    def fmt_row(values: Iterable[str]) -> str:
        return " | ".join(value.ljust(col_widths[idx]) for idx, value in enumerate(values))

    separator = "-+-".join("-" * width for width in col_widths)
    parts = [fmt_row(headers), separator]
    for row in rows:
        parts.append(fmt_row(row))
    return "\n".join(parts)


def load_pairs(raw_pairs: Iterable[str]) -> List[str]:
    pairs: List[str] = []
    for raw in raw_pairs:
        if not raw:
            continue
        for entry in raw.split(","):
            entry = entry.strip()
            if entry:
                pairs.append(entry.upper())
    if not pairs:
        raise ForexScannerError("At least one currency pair must be provided.")
    return pairs


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch live Forex rates from Alpha Vantage.")
    parser.add_argument(
        "--api-key",
        default=os.environ.get("ALPHAVANTAGE_API_KEY"),
        help="Alpha Vantage API key (or set ALPHAVANTAGE_API_KEY env variable).",
    )
    parser.add_argument(
        "--pairs",
        nargs="+",
        default=["EUR/USD", "GBP/USD", "USD/JPY"],
        help="Currency pairs to fetch (format BASE/QUOTE). Separate multiple pairs with spaces or commas.",
    )
    parser.add_argument(
        "--refresh",
        type=int,
        default=0,
        help="Refresh interval in seconds. Set to 0 to fetch once.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="HTTP request timeout in seconds.",
    )
    return parser.parse_args(argv)


def run_once(api_key: str, pairs: Iterable[str], timeout: float) -> bool:
    session = requests.Session()
    quotes: List[ForexQuote] = []
    for pair in pairs:
        try:
            quote = fetch_quote(api_key, pair, session, timeout)
            quotes.append(quote)
        except ForexScannerError as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
    if not quotes:
        return False
    print(render_table(quotes))
    return True


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    if not args.api_key:
        print(
            "Alpha Vantage API key not provided. Use --api-key or set ALPHAVANTAGE_API_KEY.",
            file=sys.stderr,
        )
        return 1

    try:
        pairs = load_pairs(args.pairs)
    except ForexScannerError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    if args.refresh < 0:
        print("[ERROR] Refresh interval must be zero or positive.", file=sys.stderr)
        return 1

    success = run_once(args.api_key, pairs, args.timeout)

    if args.refresh > 0:
        if not success:
            print("No successful quotes fetched; continuing to refresh.", file=sys.stderr)
        try:
            while True:
                time.sleep(args.refresh)
                print()
                print(time.strftime("=== %Y-%m-%d %H:%M:%S ==="))
                success = run_once(args.api_key, pairs, args.timeout) or success
        except KeyboardInterrupt:
            print("\nStopped by user.")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
