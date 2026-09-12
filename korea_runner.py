#!/usr/bin/env python3
from __future__ import annotations

"""
GitHub Actions hotfix for the Korea universe loader.

Why this exists
---------------
The original scanner first asks pykrx/KRX for the current KOSPI/KOSDAQ
market-cap universe and then falls back to the legacy Naver desktop HTML page.
Both can fail in GitHub Actions:
  * pykrx/KRX: API/response schema errors
  * legacy Naver HTML: returns no rows from a runner IP / changed markup

This runner keeps the existing signal/price-structure logic untouched and only
replaces get_universe() at runtime.

Source order
------------
1. Naver mobile JSON market-value API (primary)
2. pykrx/KRX (fallback)
3. legacy Naver desktop parser from scanner.py (fallback)
4. state/korea_universe.json cache (last resort)

Usage
-----
python korea_runner.py signals [scanner.py arguments...]
python korea_runner.py structure [price_structure_scanner.py arguments...]
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
    """Parse Naver numeric strings defensively."""
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

    # Keep digits, decimal point and minus sign only.
    s = "".join(ch for ch in s if ch.isdigit() or ch in ".-")
    if not s or s in {"-", ".", "-."}:
        return float("nan")
    try:
        return float(s)
    except Exception:
        return float("nan")


def _normalize_universe(df: pd.DataFrame, market: str, n: int, source: str) -> pd.DataFrame:
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

    # If market cap exists, preserve market-cap order.
    if x["market_cap"].notna().any():
        x = x.sort_values("market_cap", ascending=False, na_position="last")

    x = x.drop_duplicates(subset=["ticker"], keep="first").head(n).copy()

    suffix = ".KS" if market == "KOSPI" else ".KQ"
    x["market"] = market
    x["universe_source"] = source
    x["yf_ticker"] = x["ticker"] + suffix

    cols = ["ticker", "name", "market", "market_cap", "universe_source", "yf_ticker"]
    x = x[cols].reset_index(drop=True)

    if len(x) < n:
        raise RuntimeError(f"{source} returned only {len(x)} symbols for {market}; need {n}")
    return x


def universe_from_naver_mobile(market: str, n: int) -> pd.DataFrame:
    """
    Read the current market-cap ranking from Naver's mobile JSON endpoint.
    This is substantially more reliable in GitHub Actions than scraping
    finance.naver.com's desktop HTML table.
    """
    if market not in {"KOSPI", "KOSDAQ"}:
        raise ValueError(f"Unsupported market: {market}")

    session = requests.Session()
    session.headers.update(HEADERS)

    page_size = 100
    pages = max(1, math.ceil(n / page_size))
    rows: List[dict] = []
    seen = set()

    for page in range(1, pages + 1):
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
            raise RuntimeError(
                f"Naver mobile request failed for {market} page {page}: {last_error}"
            )

        stocks = payload.get("stocks") or []
        if not isinstance(stocks, list) or not stocks:
            raise RuntimeError(
                f"Naver mobile returned no stocks for {market} page {page}"
            )

        for item in stocks:
            if not isinstance(item, dict):
                continue

            ticker = str(
                item.get("itemCode")
                or item.get("code")
                or item.get("stockCode")
                or ""
            ).strip()

            # Naver's normal value is six digits. Extract defensively.
            digits = "".join(ch for ch in ticker if ch.isdigit())
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

        if len(rows) >= n:
            break

        time.sleep(0.15)

    return _normalize_universe(
        pd.DataFrame(rows),
        market,
        n,
        source="naver_mobile_market_cap",
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
                if isinstance(v, (np.integer,)):
                    v = int(v)
                elif isinstance(v, (np.floating,)):
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
    )


def get_one_market_universe_robust(market: str, n: int) -> pd.DataFrame:
    errors = []

    # 1) Primary: Naver mobile JSON.
    try:
        print(f"[universe] trying Naver mobile JSON: {market}")
        u = universe_from_naver_mobile(market, n)
        print(f"[universe] Naver mobile OK {market}: {len(u)}")
        _write_cache({market: u})
        return u
    except Exception as exc:
        errors.append(f"Naver mobile: {exc}")
        print(f"[warn] Naver mobile failed {market}: {exc}")

    # 2) Fallback: original pykrx route.
    try:
        print(f"[universe] fallback to KRX/pykrx: {market}")
        u = base_scanner.universe_from_pykrx(market, n)
        u = _normalize_universe(u, market, n, source="pykrx")
        print(f"[universe] pykrx OK {market}: {len(u)}")
        _write_cache({market: u})
        return u
    except Exception as exc:
        errors.append(f"pykrx: {exc}")
        print(f"[warn] pykrx failed {market}: {exc}")

    # 3) Fallback: original desktop Naver parser.
    try:
        print(f"[universe] fallback to Naver desktop HTML: {market}")
        u = base_scanner.universe_from_naver(market, n)
        u = _normalize_universe(u, market, n, source="naver_finance_market_cap")
        print(f"[universe] Naver desktop OK {market}: {len(u)}")
        _write_cache({market: u})
        return u
    except Exception as exc:
        errors.append(f"Naver desktop: {exc}")
        print(f"[warn] Naver desktop failed {market}: {exc}")

    # 4) Last resort: persistent cache from a previous successful Actions run.
    try:
        print(f"[universe] fallback to persistent cache: {market}")
        u = universe_from_cache(market, n)
        print(f"[universe] cache OK {market}: {len(u)}")
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

    return pd.concat(parts, ignore_index=True)


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in {"signals", "structure"}:
        raise SystemExit(
            "Usage: python korea_runner.py {signals|structure} [original arguments...]"
        )

    mode = sys.argv[1]
    forwarded_args = sys.argv[2:]

    # Patch scanner.get_universe before invoking either program.
    # price_structure_scanner imports get_universe from scanner, so patch first.
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
