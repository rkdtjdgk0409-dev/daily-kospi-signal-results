#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import requests
import yfinance as yf
from bs4 import BeautifulSoup

try:
    from pykrx import stock
except Exception:
    stock = None


def latest_krx_business_day(market: str, max_lookback: int = 14) -> str:
    if stock is None:
        raise RuntimeError("pykrx unavailable")
    today = datetime.now()
    last_error = None
    for i in range(max_lookback):
        d = (today - timedelta(days=i)).strftime("%Y%m%d")
        try:
            cap = stock.get_market_cap_by_ticker(d, market=market)
            if cap is not None and not cap.empty:
                return d
        except Exception as e:
            last_error = e
    raise RuntimeError(f"KRX unavailable for {market}: {last_error}")


def universe_from_pykrx(market: str, n: int) -> pd.DataFrame:
    asof = latest_krx_business_day(market)
    cap = stock.get_market_cap_by_ticker(asof, market=market).copy()
    if cap.empty or "시가총액" not in cap.columns:
        raise RuntimeError(f"Unexpected pykrx response for {market}")

    cap = cap.sort_values("시가총액", ascending=False).head(n)
    suffix = ".KS" if market == "KOSPI" else ".KQ"

    rows = []
    for ticker, row in cap.iterrows():
        try:
            name = stock.get_market_ticker_name(ticker)
        except Exception:
            name = str(ticker)

        ticker = str(ticker).zfill(6)
        rows.append({
            "ticker": ticker,
            "name": name,
            "market": market,
            "market_cap": float(row["시가총액"]),
            "universe_source": "pykrx",
            "yf_ticker": ticker + suffix,
        })

    return pd.DataFrame(rows)


def universe_from_naver(market: str, n: int) -> pd.DataFrame:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/123 Safari/537.36",
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        "Referer": "https://finance.naver.com/",
    })

    sosok = 0 if market == "KOSPI" else 1
    suffix = ".KS" if market == "KOSPI" else ".KQ"

    rows, seen = [], set()
    pages = max(4, math.ceil(n / 50) + 1)

    for page in range(1, pages + 1):
        url = f"https://finance.naver.com/sise/sise_market_sum.naver?sosok={sosok}&page={page}"
        r = session.get(url, timeout=30)
        r.raise_for_status()
        r.encoding = r.apparent_encoding or "euc-kr"

        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.select_one("table.type_2")
        if table is None:
            continue

        for tr in table.select("tr"):
            a = tr.select_one('a.tltle[href*="code="]')
            if a is None:
                continue

            m = re.search(r"code=(\d{6})", a.get("href", ""))
            if not m:
                continue

            ticker = m.group(1)
            if ticker in seen:
                continue
            seen.add(ticker)

            rows.append({
                "ticker": ticker,
                "name": a.get_text(strip=True),
                "market": market,
                "market_cap": np.nan,
                "universe_source": "naver_finance_market_cap",
                "yf_ticker": ticker + suffix,
            })

            if len(rows) >= n:
                return pd.DataFrame(rows)

        time.sleep(0.25)

    if len(rows) < n:
        raise RuntimeError(f"Naver returned only {len(rows)} symbols for {market}")

    return pd.DataFrame(rows[:n])


def get_one_market_universe(market: str, n: int) -> pd.DataFrame:
    try:
        print(f"[universe] trying KRX/pykrx: {market}")
        u = universe_from_pykrx(market, n)
        if len(u) >= n:
            print(f"[universe] pykrx OK {market}: {len(u)}")
            return u.head(n).reset_index(drop=True)
    except Exception as e:
        print(f"[warn] pykrx failed {market}: {e}")

    print(f"[universe] fallback to Naver Finance: {market}")
    u = universe_from_naver(market, n)
    print(f"[universe] Naver OK {market}: {len(u)}")
    return u.head(n).reset_index(drop=True)


def get_universe(kospi_n: int, kosdaq_n: int) -> pd.DataFrame:
    parts = []
    if kospi_n > 0:
        parts.append(get_one_market_universe("KOSPI", kospi_n))
    if kosdaq_n > 0:
        parts.append(get_one_market_universe("KOSDAQ", kosdaq_n))
    if not parts:
        raise RuntimeError("Universe is empty.")
    return pd.concat(parts, ignore_index=True)


def normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    x = df.copy()
    if isinstance(x.columns, pd.MultiIndex):
        x.columns = x.columns.get_level_values(0)

    cols = ["Open", "High", "Low", "Close", "Volume"]
    if not all(c in x.columns for c in cols):
        return pd.DataFrame()

    x = x[cols].copy()
    for c in cols:
        x[c] = pd.to_numeric(x[c], errors="coerce")
    x = x.dropna(subset=["Open", "High", "Low", "Close"])
    x.index = pd.to_datetime(x.index).tz_localize(None)
    return x[~x.index.duplicated(keep="last")].sort_index()


def download_prices(tickers: List[str], lookback_days: int = 220) -> Dict[str, pd.DataFrame]:
    end = datetime.now() + timedelta(days=1)
    start = end - timedelta(days=lookback_days)
    out = {}
    chunk_size = 40

    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i:i+chunk_size]
        print(f"[prices] {i+1}-{min(i+chunk_size, len(tickers))}/{len(tickers)}")

        try:
            raw = yf.download(
                chunk,
                start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
                group_by="ticker",
                auto_adjust=False,
                progress=False,
                threads=True,
                actions=False,
                timeout=30,
            )
        except Exception as e:
            print(f"[warn] chunk failed: {e}")
            raw = pd.DataFrame()

        for t in chunk:
            try:
                df = raw.copy() if (len(chunk) == 1 and not isinstance(raw.columns, pd.MultiIndex)) else raw[t].copy()
                df = normalize_ohlcv(df)
                if len(df) >= 40:
                    out[t] = df
            except Exception:
                pass

        for t in [x for x in chunk if x not in out]:
            try:
                df = yf.download(
                    t,
                    start=start.strftime("%Y-%m-%d"),
                    end=end.strftime("%Y-%m-%d"),
                    auto_adjust=False,
                    progress=False,
                    actions=False,
                    timeout=20,
                )
                df = normalize_ohlcv(df)
                if len(df) >= 40:
                    out[t] = df
            except Exception as e:
                print(f"[warn] {t}: {e}")

        time.sleep(0.2)

    return out


def cci(df: pd.DataFrame, period: int) -> pd.Series:
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    sma = tp.rolling(period).mean()
    mad = tp.rolling(period).apply(lambda a: np.mean(np.abs(a - np.mean(a))), raw=True)
    return (tp - sma) / (0.015 * mad.replace(0, np.nan))


def wilder(s: pd.Series, period: int) -> pd.Series:
    return s.ewm(alpha=1/period, adjust=False, min_periods=period).mean()


def dmi_adx(df: pd.DataFrame, period: int) -> Tuple[pd.Series, pd.Series, pd.Series]:
    h, l, c = df["High"], df["Low"], df["Close"]
    up = h.diff()
    down = -l.diff()

    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=df.index)

    tr = pd.concat([(h-l), (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)
    atr = wilder(tr, period)
    pdi = 100 * wilder(plus_dm, period) / atr.replace(0, np.nan)
    mdi = 100 * wilder(minus_dm, period) / atr.replace(0, np.nan)
    dx = 100 * (pdi-mdi).abs() / (pdi+mdi).replace(0, np.nan)
    adx = wilder(dx, period)
    return pdi, mdi, adx


def cvd_proxy(df: pd.DataFrame) -> pd.DataFrame:
    signed = df["Volume"].fillna(0) * np.sign(df["Close"] - df["Open"])
    return pd.DataFrame(
        {"signed_volume_proxy": signed, "cvd_proxy": signed.cumsum()},
        index=df.index,
    )


def score_one(df: pd.DataFrame, cci_period: int, dmi_period: int, adx_threshold: float,
              cvd_slope_period: int, cvd_ema_period: int) -> dict | None:
    x = df.copy()
    x["cci"] = cci(x, cci_period)
    x["plus_di"], x["minus_di"], x["adx"] = dmi_adx(x, dmi_period)
    x = x.join(cvd_proxy(x))
    x["cvd_ema"] = x["cvd_proxy"].ewm(span=cvd_ema_period, adjust=False).mean()
    x["cvd_slope"] = x["cvd_proxy"].diff(cvd_slope_period)

    if len(x.dropna(subset=["cci", "plus_di", "minus_di", "adx"])) < 2:
        return None

    r = x.iloc[-1]
    prev = x.iloc[-2]

    # CCI 0선 상향돌파 여부
    x["cci_cross_up"] = (x["cci"] > 0) & (x["cci"].shift(1) <= 0)

    # 오늘 또는 어제, 즉 최근 2거래일 안에 0선을 상향돌파했는지 확인
    recent_cci_cross_up = bool(x["cci_cross_up"].iloc[-2:].any())

    dmi_bull = bool(
        (r["plus_di"] > r["minus_di"])
        and (r["adx"] >= adx_threshold)
    )

    cvd_bull = bool(
        (r["cvd_slope"] > 0)
        and (r["cvd_proxy"] > r["cvd_ema"])
    )

    # 최근 2거래일 내 CCI 0선 상향돌파 + 현재 CCI > 0 + DMI/ADX 조건
    fresh_buy = (
        recent_cci_cross_up
        and (r["cci"] > 0)
        and dmi_bull
    )

    active_trend = (r["cci"] > 0) and dmi_bull

    adx_score = np.clip(r["adx"] / 40.0, 0, 1.5)
    cci_score = np.clip(r["cci"] / 150.0, -1, 1.5)
    signal_score = 100 * (
        0.50 * adx_score
        + 0.35 * max(cci_score, 0)
        + 0.15 * (1.0 if cvd_bull else 0.0)
    )

    avg20_trading_value = float((x["Close"] * x["Volume"]).rolling(20).mean().iloc[-1])

    return {
        "signal_date": x.index[-1].strftime("%Y-%m-%d"),
        "close": float(r["Close"]),
        "avg20_trading_value": avg20_trading_value,
        "daily_return_pct": float((r["Close"] / prev["Close"] - 1) * 100),
        "cci": float(r["cci"]),
        "cci_prev": float(prev["cci"]),
        "plus_di": float(r["plus_di"]),
        "minus_di": float(r["minus_di"]),
        "adx": float(r["adx"]),
        "cvd_bull": cvd_bull,
        "fresh_buy": fresh_buy,
        "active_trend": active_trend,
        "signal_score": float(signal_score),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kospi-n", type=int, default=200)
    ap.add_argument("--kosdaq-n", type=int, default=150)
    ap.add_argument("--kosdaq-min-avg20-value", type=float, default=3000000000)
    ap.add_argument("--cci-period", type=int, default=9)
    ap.add_argument("--dmi-period", type=int, default=14)
    ap.add_argument("--adx-threshold", type=float, default=20)
    ap.add_argument("--cvd-slope-period", type=int, default=5)
    ap.add_argument("--cvd-ema-period", type=int, default=10)
    ap.add_argument("--output-dir", default="results")
    args = ap.parse_args()

    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    universe = get_universe(args.kospi_n, args.kosdaq_n)
    universe.to_csv(outdir / "universe.csv", index=False, encoding="utf-8-sig")

    prices = download_prices(universe["yf_ticker"].tolist())
    meta = universe.set_index("yf_ticker")[["ticker", "name", "market", "universe_source"]].to_dict("index")

    rows = []
    for yf_ticker, df in prices.items():
        sig = score_one(
            df, args.cci_period, args.dmi_period, args.adx_threshold,
            args.cvd_slope_period, args.cvd_ema_period
        )
        if sig is None:
            continue
        m = meta[yf_ticker]
        if m["market"] == "KOSDAQ" and sig.get("avg20_trading_value", 0) < args.kosdaq_min_avg20_value:
            continue

        rows.append({
            "ticker": m["ticker"],
            "name": m["name"],
            "market": m["market"],
            "yf_ticker": yf_ticker,
            "universe_source": m["universe_source"],
            **sig,
        })

    if not rows:
        raise RuntimeError("No symbols could be scored.")

    all_df = pd.DataFrame(rows).sort_values(
        ["fresh_buy", "active_trend", "signal_score"],
        ascending=[False, False, False],
    )

    buy = all_df[all_df["fresh_buy"]].sort_values("signal_score", ascending=False)
    active = all_df[all_df["active_trend"]].sort_values("signal_score", ascending=False)

    all_df.to_csv(outdir / "latest_all_scored.csv", index=False, encoding="utf-8-sig")
    buy.to_csv(outdir / "latest_buy_signals.csv", index=False, encoding="utf-8-sig")
    active.to_csv(outdir / "latest_active_trends.csv", index=False, encoding="utf-8-sig")

    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "symbols_scored": int(len(all_df)),
        "fresh_buy_count": int(len(buy)),
        "active_trend_count": int(len(active)),
        "latest_signal_date": str(all_df["signal_date"].max()),
        "parameters": {
            "kospi_n": args.kospi_n,
            "kosdaq_n": args.kosdaq_n,
            "kosdaq_min_avg20_value": args.kosdaq_min_avg20_value,
            "cci_period": args.cci_period,
            "dmi_period": args.dmi_period,
            "adx_threshold": args.adx_threshold,
        },
        "fresh_buy_count_kospi": int((buy["market"] == "KOSPI").sum()) if not buy.empty else 0,
        "fresh_buy_count_kosdaq": int((buy["market"] == "KOSDAQ").sum()) if not buy.empty else 0,
    }
    (outdir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
