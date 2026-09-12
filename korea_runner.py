#!/usr/bin/env python3
from __future__ import annotations

"""
Robust Korea universe runner for GitHub Actions.

Fix in V2
---------
The previous version stopped after exactly ceil(n / 100) Naver pages.
In the 2026-09-12 Actions run, KOSPI page 1~2 produced only 195 unique
symbols while n=200, so the primary source was rejected even though it was
almost complete.

V2:
1) keeps fetching extra Naver pages until n unique symbols are collected,
2) tolerates a small shortfall (>= 90% of requested N) instead of crashing,
3) caches every successful/usable universe,
4) keeps pykrx / legacy Naver / cache as fallbacks,
5) leaves scanner.py and price_structure_scanner.py analysis logic untouched.
"""

import json
import math
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import requests

import scanner as base_scanner


CACHE_PATH = Path("state/korea_universe.json")

NAVER_MOBILE_URL = (
    "https://m.stock.naver.com/api/stocks/marketValue/"
    "{market}?page={page}&pageSize={page_size}&sortType=MARKET_VALUE"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
        "Mobile/15E148 Safari/604.1"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    "Referer": "https://m.stock.naver.com/",
    "Connection": "keep-alive",
}


def _safe_number(value) -> float:
    if value is None:
        return float("nan")
    if isinstance(value, (int, float, np.integer, np.floating)):
        try:
            return float(value)
        except Exception:
            return float("nan")

    s = str(value).strip().replace(",", "")
    if not s or s in {"-", "N/A", "None", "null"}:
        return float("nan")

    s = "".join(ch for ch in s if ch.isdigit() or ch in ".-")
    if not s or s in {"-", ".", "-."}:
        return float("nan")

    try:
        return float(s)
    except Exception:
        return float("nan")


def _minimum_usable_count(n: int) -> int:
    """
    Do not fail the whole daily pipeline for a tiny pagination shortfall.
    90% is enough to keep the screener alive while still rejecting a badly
    broken source.
    """
    if n <= 0:
        return 0
    return max(1, int(math.ceil(n * 0.90)))


def _normalize_universe(
    df: pd.DataFrame,
    market: str,
    n: int,
    source: str,
    allow_partial: bool = True,
) -> pd.DataFrame:
    if df is None or df.empty:
        raise RuntimeError(f"{source} returned an empty universe for {market}")

    x = df.copy()

    required = {"ticker", "name"}
    if not required.issubset(x.columns):
        raise RuntimeError(
            f"{source} response for {market} is missing columns: "
            f"{sorted(required - set(x.columns))}"
        )

    x["ticker"] = (
        x["ticker"]
        .astype(str)
        .str.extract(r"(\d{6})", expand=False)
        .fillna("")
        .str.zfill(6)
    )
    x["name"] = x["name"].astype(str).str.strip()
    x = x[(x["ticker"].str.fullmatch(r"\d{6}")) & (x["name"] != "")].copy()

    if "market_cap" not in x.columns:
        x["market_cap"] = np.nan

    x["market_cap"] = pd.to_numeric(x["market_cap"], errors="coerce")

    # Naver's response is already market-cap ordered. Sorting is harmless when
    # a numeric market_cap is available, and keeps cached / alternate sources tidy.
    if x["market_cap"].notna().any():
        x = x.sort_values("market_cap", ascending=False, na_position="last")

    x = x.drop_duplicates(subset=["ticker"], keep="first").head(n).copy()

    suffix = ".KS" if market == "KOSPI" else ".KQ"
    x["market"] = market
    x["universe_source"] = source
    x["yf_ticker"] = x["ticker"] + suffix

    cols = [
        "ticker",
        "name",
        "market",
        "market_cap",
        "universe_source",
        "yf_ticker",
    ]
    x = x[cols].reset_index(drop=True)

    if len(x) < n:
        minimum = _minimum_usable_count(n)
        if not allow_partial or len(x) < minimum:
            raise RuntimeError(
                f"{source} returned only {len(x)} symbols for {market}; "
                f"need {n}, minimum usable={minimum}"
            )
        print(
            f"[warn] {source} returned {len(x)}/{n} symbols for {market}; "
            "continuing with partial universe instead of aborting the workflow"
        )

    return x


def universe_from_naver_mobile(market: str, n: int) -> pd.DataFrame:
    """
    Fetch Naver mobile market-cap JSON.

    Important V2 change:
    - Do NOT assume exactly ceil(n / page_size) pages are sufficient.
    - Pagination can overlap by a few symbols while rankings update.
    - Keep requesting extra pages until n unique symbols are collected.
    """
    if market not in {"KOSPI", "KOSDAQ"}:
        raise ValueError(f"Unsupported market: {market}")

    session = requests.Session()
    session.headers.update(HEADERS)

    page_size = 100
    nominal_pages = max(1, math.ceil(n / page_size))

    # Extra pages protect against duplicated page-boundary symbols and temporary
    # short pages. For n=200 this checks up to page 6 instead of stopping at page 2.
    max_pages = nominal_pages + 4

    rows: List[dict] = []
    seen = set()
    consecutive_empty_pages = 0

    for page in range(1, max_pages + 1):
        url = NAVER_MOBILE_URL.format(
            market=market,
            page=page,
            page_size=page_size,
        )

        last_error = None
        payload = None

        for attempt in range(1, 4):
            try:
                r = session.get(url, timeout=25)
                r.raise_for_status()
                payload = r.json()
                if not isinstance(payload, dict):
                    raise RuntimeError("JSON root is not an object")
                break
            except Exception as exc:
                last_error = exc
                if attempt < 3:
                    time.sleep(1.0 * attempt)

        if payload is None:
            # If we already have a mostly usable universe, don't throw it away
            # merely because one later extra page failed.
            if len(rows) >= _minimum_usable_count(n):
                print(
                    f"[warn] Naver mobile page {page} request failed after "
                    f"{len(rows)} unique symbols; using collected data: {last_error}"
                )
                break
            raise RuntimeError(
                f"Naver mobile request failed for {market} page {page}: {last_error}"
            )

        stocks = payload.get("stocks") or []

        if not isinstance(stocks, list) or not stocks:
            consecutive_empty_pages += 1
            print(
                f"[warn] Naver mobile empty page {page} for {market}; "
                f"collected={len(rows)}"
            )

            # Once we are beyond the nominal page count and have a usable sample,
            # stop cleanly instead of treating the empty extra page as fatal.
            if (
                page >= nominal_pages
                and len(rows) >= _minimum_usable_count(n)
            ):
                break

            if consecutive_empty_pages >= 2:
                break

            time.sleep(0.25)
            continue

        consecutive_empty_pages = 0
        before = len(rows)

        for item in stocks:
            if not isinstance(item, dict):
                continue

            raw_ticker = str(
                item.get("itemCode")
                or item.get("code")
                or item.get("stockCode")
                or ""
            ).strip()

            digits = "".join(ch for ch in raw_ticker if ch.isdigit())
            if len(digits) < 6:
                continue
            ticker = digits[-6:]

            if ticker in seen:
                continue
            seen.add(ticker)

            name = str(
                item.get("stockName")
                or item.get("name")
                or item.get("itemName")
                or ticker
            ).strip()

            market_cap = _safe_number(
                item.get("marketValue")
                if item.get("marketValue") is not None
                else item.get("marketCap")
            )

            rows.append(
                {
                    "ticker": ticker,
                    "name": name,
                    "market_cap": market_cap,
                }
            )

            if len(rows) >= n:
                break

        added = len(rows) - before
        print(
            f"[universe] Naver {market} page {page}: "
            f"+{added} unique, total={len(rows)}/{n}"
        )

        if len(rows) >= n:
            break

        # If an extra page adds nothing, try one more page before giving up.
        # This handles temporary overlapping pagination without an infinite loop.
        time.sleep(0.20)

    return _normalize_universe(
        pd.DataFrame(rows),
        market,
        n,
        source="naver_mobile_market_cap_v2",
        allow_partial=True,
    )


def _read_cache() -> Dict:
    if not CACHE_PATH.exists():
        return {}
    try:
        data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        print(f"[warn] universe cache unreadable: {exc}")
        return {}


def _write_cache(market_frames: Dict[str, pd.DataFrame]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)

    old = _read_cache()
    markets = old.get("markets") if isinstance(old.get("markets"), dict) else {}

    for market, df in market_frames.items():
        records = []

        for rec in df.to_dict("records"):
            clean = {}
            for k, v in rec.items():
                if isinstance(v, np.integer):
                    v = int(v)
                elif isinstance(v, np.floating):
                    v = None if not np.isfinite(v) else float(v)
                elif pd.isna(v):
                    v = None
                clean[k] = v
            records.append(clean)

        markets[market] = records

    payload = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "markets": markets,
    }

    CACHE_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def universe_from_cache(market: str, n: int) -> pd.DataFrame:
    data = _read_cache()
    records = (data.get("markets") or {}).get(market) or []

    if not records:
        raise RuntimeError(f"No cached universe for {market}")

    return _normalize_universe(
        pd.DataFrame(records),
        market,
        n,
        source="cached_korea_universe",
        allow_partial=True,
    )


def get_one_market_universe_robust(market: str, n: int) -> pd.DataFrame:
    errors = []

    # 1) Primary: Naver mobile JSON
    try:
        print(f"[universe] trying Naver mobile JSON V2: {market}")
        u = universe_from_naver_mobile(market, n)
        print(f"[universe] Naver mobile OK {market}: {len(u)}/{n}")
        _write_cache({market: u})
        return u
    except Exception as exc:
        errors.append(f"Naver mobile: {exc}")
        print(f"[warn] Naver mobile failed {market}: {exc}")

    # 2) Fallback: existing pykrx route
    try:
        print(f"[universe] fallback to KRX/pykrx: {market}")
        u = base_scanner.universe_from_pykrx(market, n)
        u = _normalize_universe(
            u,
            market,
            n,
            source="pykrx",
            allow_partial=True,
        )
        print(f"[universe] pykrx OK {market}: {len(u)}/{n}")
        _write_cache({market: u})
        return u
    except Exception as exc:
        errors.append(f"pykrx: {exc}")
        print(f"[warn] pykrx failed {market}: {exc}")

    # 3) Fallback: legacy Naver desktop parser
    try:
        print(f"[universe] fallback to Naver desktop HTML: {market}")
        u = base_scanner.universe_from_naver(market, n)
        u = _normalize_universe(
            u,
            market,
            n,
            source="naver_finance_market_cap",
            allow_partial=True,
        )
        print(f"[universe] Naver desktop OK {market}: {len(u)}/{n}")
        _write_cache({market: u})
        return u
    except Exception as exc:
        errors.append(f"Naver desktop: {exc}")
        print(f"[warn] Naver desktop failed {market}: {exc}")

    # 4) Last resort: persistent cache
    try:
        print(f"[universe] fallback to persistent cache: {market}")
        u = universe_from_cache(market, n)
        print(f"[universe] cache OK {market}: {len(u)}/{n}")
        return u
    except Exception as exc:
        errors.append(f"cache: {exc}")
        print(f"[warn] cache failed {market}: {exc}")

    raise RuntimeError(
        f"All universe sources failed for {market}: " + " | ".join(errors)
    )


def get_universe_robust(kospi_n: int, kosdaq_n: int) -> pd.DataFrame:
    parts = []

    if kospi_n > 0:
        parts.append(get_one_market_universe_robust("KOSPI", kospi_n))

    if kosdaq_n > 0:
        parts.append(get_one_market_universe_robust("KOSDAQ", kosdaq_n))

    if not parts:
        raise RuntimeError("Universe is empty.")

    universe = pd.concat(parts, ignore_index=True)

    counts = universe.groupby("market").size().to_dict()
    print(f"[universe] final counts: {counts}")

    return universe


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in {"signals", "structure"}:
        raise SystemExit(
            "Usage: python korea_runner.py {signals|structure} [original arguments...]"
        )

    mode = sys.argv[1]
    forwarded_args = sys.argv[2:]

    base_scanner.get_universe = get_universe_robust

    if mode == "signals":
        sys.argv = ["scanner.py", *forwarded_args]
        base_scanner.main()
        return

    import price_structure_scanner as structure_scanner

    structure_scanner.get_universe = get_universe_robust
    sys.argv = ["price_structure_scanner.py", *forwarded_args]
    structure_scanner.main()


if __name__ == "__main__":
    main()
