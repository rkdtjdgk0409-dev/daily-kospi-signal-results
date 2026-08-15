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


# -----------------------------
# Universe / price data
# -----------------------------
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
        time.sleep(0.20)

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


def download_prices(tickers: List[str], lookback_days: int = 320) -> Dict[str, pd.DataFrame]:
    end = datetime.now() + timedelta(days=1)
    start = end - timedelta(days=lookback_days)
    out: Dict[str, pd.DataFrame] = {}
    chunk_size = 40

    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i:i + chunk_size]
        print(f"[prices] {i+1}-{min(i+chunk_size, len(tickers))}/{len(tickers)}")
        try:
            raw = yf.download(
                chunk,
                start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
                group_by="ticker",
                auto_adjust=True,
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
                if len(df) >= 90:
                    out[t] = df
            except Exception:
                pass

        for t in [x for x in chunk if x not in out]:
            try:
                df = yf.download(
                    t,
                    start=start.strftime("%Y-%m-%d"),
                    end=end.strftime("%Y-%m-%d"),
                    auto_adjust=True,
                    progress=False,
                    actions=False,
                    timeout=20,
                )
                df = normalize_ohlcv(df)
                if len(df) >= 90:
                    out[t] = df
            except Exception as e:
                print(f"[warn] {t}: {e}")
        time.sleep(0.15)
    return out


def download_benchmark(ticker: str, lookback_days: int = 320) -> pd.DataFrame:
    end = datetime.now() + timedelta(days=1)
    start = end - timedelta(days=lookback_days)
    try:
        df = yf.download(
            ticker,
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            auto_adjust=True,
            progress=False,
            actions=False,
            timeout=30,
        )
        return normalize_ohlcv(df)
    except Exception as e:
        print(f"[warn] benchmark {ticker}: {e}")
        return pd.DataFrame()


# -----------------------------
# Indicators
# -----------------------------
def cci(df: pd.DataFrame, period: int) -> pd.Series:
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    sma = tp.rolling(period).mean()
    mad = tp.rolling(period).apply(lambda a: np.mean(np.abs(a - np.mean(a))), raw=True)
    return (tp - sma) / (0.015 * mad.replace(0, np.nan))


def wilder(s: pd.Series, period: int) -> pd.Series:
    return s.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def dmi_adx(df: pd.DataFrame, period: int) -> Tuple[pd.Series, pd.Series, pd.Series]:
    h, l, c = df["High"], df["Low"], df["Close"]
    up = h.diff()
    down = -l.diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=df.index)
    tr = pd.concat([(h - l), (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = wilder(tr, period)
    pdi = 100 * wilder(plus_dm, period) / atr.replace(0, np.nan)
    mdi = 100 * wilder(minus_dm, period) / atr.replace(0, np.nan)
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    adx = wilder(dx, period)
    return pdi, mdi, adx


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h, l, c = df["High"], df["Low"], df["Close"]
    tr = pd.concat([(h - l), (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    return wilder(tr, period)


def supertrend(df: pd.DataFrame, period: int = 10, factor: float = 3.0) -> Tuple[pd.Series, pd.Series]:
    """TradingView-style Supertrend using Wilder ATR. Returns (line, bullish_bool)."""
    h, l, c = df["High"], df["Low"], df["Close"]
    atr_v = atr(df, period)
    hl2 = (h + l) / 2.0
    basic_upper = hl2 + factor * atr_v
    basic_lower = hl2 - factor * atr_v

    final_upper = pd.Series(np.nan, index=df.index, dtype=float)
    final_lower = pd.Series(np.nan, index=df.index, dtype=float)
    st = pd.Series(np.nan, index=df.index, dtype=float)
    bull = pd.Series(False, index=df.index, dtype=bool)

    for i in range(len(df)):
        if not np.isfinite(atr_v.iloc[i]):
            continue
        if i == 0 or not np.isfinite(final_upper.iloc[i-1]) or not np.isfinite(final_lower.iloc[i-1]):
            final_upper.iloc[i] = basic_upper.iloc[i]
            final_lower.iloc[i] = basic_lower.iloc[i]
            st.iloc[i] = final_upper.iloc[i]
            bull.iloc[i] = False
            continue

        prev_close = c.iloc[i-1]
        prev_upper = final_upper.iloc[i-1]
        prev_lower = final_lower.iloc[i-1]
        final_upper.iloc[i] = basic_upper.iloc[i] if (basic_upper.iloc[i] < prev_upper or prev_close > prev_upper) else prev_upper
        final_lower.iloc[i] = basic_lower.iloc[i] if (basic_lower.iloc[i] > prev_lower or prev_close < prev_lower) else prev_lower

        prev_st = st.iloc[i-1]
        if not np.isfinite(prev_st):
            prev_st = prev_upper

        if abs(prev_st - prev_upper) < 1e-12:
            if c.iloc[i] <= final_upper.iloc[i]:
                st.iloc[i] = final_upper.iloc[i]
                bull.iloc[i] = False
            else:
                st.iloc[i] = final_lower.iloc[i]
                bull.iloc[i] = True
        else:
            if c.iloc[i] >= final_lower.iloc[i]:
                st.iloc[i] = final_lower.iloc[i]
                bull.iloc[i] = True
            else:
                st.iloc[i] = final_upper.iloc[i]
                bull.iloc[i] = False

    return st, bull


def latest_true_age(flags: pd.Series, lookback: int = 10) -> int:
    recent = flags.iloc[-lookback:].to_numpy(dtype=bool)
    for age, flag in enumerate(recent[::-1]):
        if flag:
            return age
    return 999


def clamp100(v: float) -> float:
    return float(np.clip(v, 0.0, 100.0))


def cci_freshness_score(cross_age: int | None, cci_value: float) -> float:
    if cross_age == 0:
        return 100.0
    if cross_age == 1:
        return 80.0
    if cross_age is not None and cross_age <= 5:
        return 40.0
    if cci_value > 0:
        return 20.0
    return 0.0


def cci_level_score(cci_value: float) -> float:
    # 신규 모멘텀 구간에 높은 점수, 극단적 과열에는 추가 보상하지 않음.
    if not np.isfinite(cci_value) or cci_value <= 0:
        return 0.0
    return clamp100(100.0 - 0.60 * abs(cci_value - 60.0))


def raw_features(df: pd.DataFrame, cci_period: int, dmi_period: int, st_period: int = 10, st_factor: float = 3.0) -> dict | None:
    x = df.copy()
    x["cci"] = cci(x, cci_period)
    x["plus_di"], x["minus_di"], x["adx"] = dmi_adx(x, dmi_period)
    x["atr"] = atr(x, 14)
    x["supertrend"], x["supertrend_bull"] = supertrend(x, st_period, st_factor)
    x["st_bull_flip"] = x["supertrend_bull"] & (~x["supertrend_bull"].shift(1, fill_value=False))
    x["st_bear_flip"] = (~x["supertrend_bull"]) & x["supertrend_bull"].shift(1, fill_value=False)
    x["ret"] = x["Close"].pct_change()
    x["ma20"] = x["Close"].rolling(20).mean()
    x["ma60"] = x["Close"].rolling(60).mean()
    x["cci_cross_up"] = (x["cci"] > 0) & (x["cci"].shift(1) <= 0)

    signed_volume = x["Volume"].fillna(0) * np.sign(x["Close"] - x["Open"])
    x["cvd_proxy"] = signed_volume.cumsum()
    x["cvd_ema10"] = x["cvd_proxy"].ewm(span=10, adjust=False).mean()
    x["cvd_slope5"] = x["cvd_proxy"].diff(5)
    x["avg_volume20"] = x["Volume"].rolling(20).mean()
    x["trading_value"] = x["Close"] * x["Volume"]
    x["avg20_trading_value"] = x["trading_value"].rolling(20).mean()

    valid = x.dropna(subset=["cci", "plus_di", "minus_di", "adx", "atr", "ma60", "supertrend"])
    if len(valid) < 10:
        return None

    r = x.iloc[-1]
    prev = x.iloc[-2]
    if not np.isfinite(r["Close"]):
        return None

    cross_age = None
    recent_crosses = x["cci_cross_up"].iloc[-6:].to_numpy()
    for age, flag in enumerate(recent_crosses[::-1]):
        if bool(flag):
            cross_age = age
            break

    pdi = float(r["plus_di"])
    mdi = float(r["minus_di"])
    adx_v = float(r["adx"])
    direction = (pdi - mdi) / (pdi + mdi) if (pdi + mdi) > 0 else 0.0
    dmi_ratio = (pdi / mdi) if mdi > 0 else (10.0 if pdi > 0 else 1.0)
    direction_long = max(direction, 0.0)
    direction_score = clamp100(direction_long * 200.0)  # +DI가 -DI보다 충분히 클수록 포화
    adx_strength_score = clamp100((adx_v - 15.0) / 25.0 * 100.0)  # ADX 40에서 포화
    adx_delta3 = float(r["adx"] - x["adx"].iloc[-4]) if len(x) >= 4 and np.isfinite(x["adx"].iloc[-4]) else 0.0
    adx_accel_score = clamp100((adx_delta3 + 5.0) / 10.0 * 100.0)

    st_good = bool(r["supertrend_bull"])
    st_bull_flip_age = latest_true_age(x["st_bull_flip"], 10)
    st_bear_flip_age = latest_true_age(x["st_bear_flip"], 10)
    if st_good:
        # Current bullish regime matters most; a fresh flip gets a modest timing bonus.
        supertrend_score = 100.0 if st_bull_flip_age <= 3 else 80.0
    else:
        supertrend_score = 0.0

    # Supertrend receives 25% of Trend, not a separate Alpha bucket, to avoid double-counting trend.
    trend_score = (
        0.35 * direction_score
        + 0.30 * adx_strength_score
        + 0.10 * adx_accel_score
        + 0.25 * supertrend_score
    )

    cci_v = float(r["cci"])
    cci_delta3 = float(r["cci"] - x["cci"].iloc[-4]) if len(x) >= 4 and np.isfinite(x["cci"].iloc[-4]) else 0.0
    freshness = cci_freshness_score(cross_age, cci_v)
    cci_slope_score = clamp100(50.0 + cci_delta3 / 2.0)
    level_score = cci_level_score(cci_v)
    momentum_score = 0.40 * freshness + 0.35 * cci_slope_score + 0.25 * level_score

    avg_vol20 = float(r["avg_volume20"]) if np.isfinite(r["avg_volume20"]) and r["avg_volume20"] > 0 else np.nan
    cvd_slope_ratio = float(r["cvd_slope5"] / avg_vol20) if np.isfinite(avg_vol20) else 0.0
    cvd_pos_ratio = float((r["cvd_proxy"] - r["cvd_ema10"]) / avg_vol20) if np.isfinite(avg_vol20) else 0.0
    rel_dollar_volume = float(r["trading_value"] / r["avg20_trading_value"]) if np.isfinite(r["avg20_trading_value"]) and r["avg20_trading_value"] > 0 else 0.0

    flow_slope_score = clamp100(50.0 + 10.0 * cvd_slope_ratio)
    flow_position_score = clamp100(50.0 + 10.0 * cvd_pos_ratio)
    volume_score = clamp100(rel_dollar_volume * 50.0)
    flow_score = 0.40 * flow_slope_score + 0.30 * flow_position_score + 0.30 * volume_score

    st_line = float(r["supertrend"])
    st_distance_atr = float((r["Close"] - st_line) / r["atr"]) if np.isfinite(r["atr"]) and r["atr"] > 0 else 0.0
    extension_penalty = max(cci_v - 120.0, 0.0) * 0.70 + max(st_distance_atr - 3.0, 0.0) * 20.0
    extension_score = clamp100(100.0 - extension_penalty)
    dmi_entry_score = 0.60 * direction_score + 0.40 * adx_accel_score
    entry_score = clamp100(
        0.30 * freshness
        + 0.25 * supertrend_score
        + 0.20 * dmi_entry_score
        + 0.15 * flow_score
        + 0.10 * extension_score
    )

    ret20 = float(r["Close"] / x["Close"].iloc[-21] - 1.0) if len(x) >= 21 and x["Close"].iloc[-21] > 0 else np.nan
    ret60 = float(r["Close"] / x["Close"].iloc[-61] - 1.0) if len(x) >= 61 and x["Close"].iloc[-61] > 0 else np.nan
    atr_pct = float(r["atr"] / r["Close"] * 100.0)
    vol20_ann_pct = float(x["ret"].rolling(20).std().iloc[-1] * np.sqrt(252) * 100.0)

    return {
        "signal_date": x.index[-1].strftime("%Y-%m-%d"),
        "close": float(r["Close"]),
        "daily_return_pct": float((r["Close"] / prev["Close"] - 1.0) * 100.0),
        "avg20_trading_value": float(r["avg20_trading_value"]) if np.isfinite(r["avg20_trading_value"]) else 0.0,
        "relative_dollar_volume": rel_dollar_volume,
        "cci": cci_v,
        "cci_prev": float(prev["cci"]),
        "cci_delta3": cci_delta3,
        "cci_cross_age": cross_age if cross_age is not None else 999,
        "plus_di": pdi,
        "minus_di": mdi,
        "adx": adx_v,
        "adx_delta3": adx_delta3,
        "dmi_direction": float(direction),
        "dmi_ratio": float(dmi_ratio),
        "supertrend": st_line,
        "supertrend_good": st_good,
        "supertrend_status": "GOOD" if st_good else "BAD",
        "supertrend_score": float(supertrend_score),
        "supertrend_bull_flip_age": int(st_bull_flip_age),
        "supertrend_bear_flip_age": int(st_bear_flip_age),
        "supertrend_flip_age": int(st_bull_flip_age if st_good else st_bear_flip_age),
        "supertrend_distance_atr": st_distance_atr,
        "entry_score": float(entry_score),
        "extension_score": float(extension_score),
        "trend_score": float(trend_score),
        "momentum_score": float(momentum_score),
        "flow_score": float(flow_score),
        "cvd_slope_ratio": cvd_slope_ratio,
        "cvd_position_ratio": cvd_pos_ratio,
        "ret20": ret20,
        "ret60": ret60,
        "atr_pct": atr_pct,
        "vol20_ann_pct": vol20_ann_pct,
        "above_ma20": bool(r["Close"] > r["ma20"]),
        "above_ma60": bool(r["Close"] > r["ma60"]),
    }


def benchmark_snapshot(df: pd.DataFrame) -> dict:
    if df is None or len(df) < 61:
        return {"ret20": 0.0, "ret60": 0.0, "close": np.nan, "ma20": np.nan, "ma60": np.nan}
    c = df["Close"]
    return {
        "ret20": float(c.iloc[-1] / c.iloc[-21] - 1.0),
        "ret60": float(c.iloc[-1] / c.iloc[-61] - 1.0),
        "close": float(c.iloc[-1]),
        "ma20": float(c.rolling(20).mean().iloc[-1]),
        "ma60": float(c.rolling(60).mean().iloc[-1]),
    }


def classify_regime(index_snap: dict, breadth20: float, breadth60: float) -> Tuple[str, int]:
    close = index_snap.get("close", np.nan)
    ma20 = index_snap.get("ma20", np.nan)
    ma60 = index_snap.get("ma60", np.nan)
    conditions = [
        bool(np.isfinite(close) and np.isfinite(ma20) and close > ma20),
        bool(np.isfinite(close) and np.isfinite(ma60) and close > ma60),
        bool(np.isfinite(ma20) and np.isfinite(ma60) and ma20 > ma60),
        breadth20 >= 0.55,
        breadth60 >= 0.50,
    ]
    score = int(sum(conditions))
    if score >= 4:
        return "RISK-ON", score
    if score <= 1:
        return "RISK-OFF", score
    return "NEUTRAL", score


def percentile_0_100(s: pd.Series) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce")
    if s.notna().sum() <= 1:
        return pd.Series(50.0, index=s.index)
    return s.rank(pct=True, method="average") * 100.0


def signal_state(alpha: float) -> str:
    if alpha >= 80:
        return "STRONG LONG"
    if alpha >= 70:
        return "LONG"
    if alpha >= 60:
        return "POSITIVE"
    if alpha >= 45:
        return "NEUTRAL"
    if alpha >= 30:
        return "WEAK"
    return "BEARISH"


def risk_label(score: float) -> str:
    if score <= 35:
        return "LOW"
    if score <= 70:
        return "MED"
    return "HIGH"


def setup_grade(row: pd.Series) -> str:
    # 단계는 상호배타적: Confirmed > Fresh > Early > Watch
    if bool(row.get("confirmed_buy", False)):
        if (
            float(row["alpha_score"]) >= 85
            and float(row.get("entry_score", 0)) >= 80
            and bool(row.get("supertrend_good", False))
            and float(row["rs_score"]) >= 80
            and float(row["flow_score"]) >= 65
            and row["regime"] == "RISK-ON"
        ):
            return "A+"
        return "A"
    if bool(row.get("fresh_buy", False)):
        return "B"
    if bool(row.get("early_setup", False)):
        return "EARLY"
    if float(row["alpha_score"]) >= 60:
        return "WATCH"
    return "-"


# -----------------------------
# Main
# -----------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kospi-n", type=int, default=200)
    ap.add_argument("--kosdaq-n", type=int, default=150)
    ap.add_argument("--kospi-min-avg20-value", type=float, default=0.0)
    ap.add_argument("--kosdaq-min-avg20-value", type=float, default=3_000_000_000)
    ap.add_argument("--cci-period", type=int, default=9)
    ap.add_argument("--dmi-period", type=int, default=14)
    ap.add_argument("--supertrend-period", type=int, default=10)
    ap.add_argument("--supertrend-factor", type=float, default=3.0)
    ap.add_argument("--adx-threshold", type=float, default=20.0)
    ap.add_argument("--confirmed-alpha-threshold", type=float, default=75.0)
    ap.add_argument("--fresh-alpha-threshold", type=float, default=60.0)
    ap.add_argument("--early-alpha-threshold", type=float, default=50.0)
    # Backward-compatible alias. If supplied by an older workflow, it overrides Confirmed only.
    ap.add_argument("--buy-alpha-threshold", type=float, default=None, help=argparse.SUPPRESS)
    ap.add_argument("--output-dir", default="results")
    args = ap.parse_args()
    if args.buy_alpha_threshold is not None:
        args.confirmed_alpha_threshold = float(args.buy_alpha_threshold)

    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    universe = get_universe(args.kospi_n, args.kosdaq_n)
    universe.to_csv(outdir / "universe.csv", index=False, encoding="utf-8-sig")

    prices = download_prices(universe["yf_ticker"].tolist())
    benchmarks = {
        "KOSPI": benchmark_snapshot(download_benchmark("^KS11")),
        "KOSDAQ": benchmark_snapshot(download_benchmark("^KQ11")),
    }

    meta = universe.set_index("yf_ticker")[["ticker", "name", "market", "universe_source"]].to_dict("index")
    rows = []
    for yf_ticker, df in prices.items():
        feat = raw_features(df, args.cci_period, args.dmi_period, args.supertrend_period, args.supertrend_factor)
        if feat is None:
            continue
        m = meta[yf_ticker]
        min_value = args.kospi_min_avg20_value if m["market"] == "KOSPI" else args.kosdaq_min_avg20_value
        if feat["avg20_trading_value"] < min_value:
            continue
        rows.append({
            "ticker": m["ticker"],
            "name": m["name"],
            "market": m["market"],
            "yf_ticker": yf_ticker,
            "universe_source": m["universe_source"],
            **feat,
        })

    if not rows:
        raise RuntimeError("No symbols could be scored.")

    all_df = pd.DataFrame(rows)

    # 상대강도: 각 시장 벤치마크 대비 초과수익률 → 같은 시장 내 percentile.
    all_df["benchmark_ret20"] = all_df["market"].map(lambda m: benchmarks[m]["ret20"])
    all_df["benchmark_ret60"] = all_df["market"].map(lambda m: benchmarks[m]["ret60"])
    all_df["rs20_excess_pct"] = (all_df["ret20"] - all_df["benchmark_ret20"]) * 100.0
    all_df["rs60_excess_pct"] = (all_df["ret60"] - all_df["benchmark_ret60"]) * 100.0

    all_df["rs20_percentile"] = all_df.groupby("market")["rs20_excess_pct"].transform(percentile_0_100)
    all_df["rs60_percentile"] = all_df.groupby("market")["rs60_excess_pct"].transform(percentile_0_100)
    all_df["rs_score"] = 0.60 * all_df["rs20_percentile"] + 0.40 * all_df["rs60_percentile"]

    # Risk는 Alpha에서 분리. 높은 값일수록 위험이 큼.
    all_df["atr_risk_pctile"] = all_df.groupby("market")["atr_pct"].transform(percentile_0_100)
    all_df["vol_risk_pctile"] = all_df.groupby("market")["vol20_ann_pct"].transform(percentile_0_100)
    all_df["risk_score"] = 0.60 * all_df["atr_risk_pctile"] + 0.40 * all_df["vol_risk_pctile"]
    all_df["risk_level"] = all_df["risk_score"].map(risk_label)

    # Market regime = index trend + breadth. Alpha에는 직접 곱하지 않고 별도 정보로 유지.
    regimes = {}
    for market in ["KOSPI", "KOSDAQ"]:
        g = all_df[all_df["market"] == market]
        if g.empty:
            regimes[market] = {"regime": "NEUTRAL", "score": 0, "breadth20": 0.0, "breadth60": 0.0}
            continue
        breadth20 = float(g["above_ma20"].mean())
        breadth60 = float(g["above_ma60"].mean())
        regime, regime_score = classify_regime(benchmarks[market], breadth20, breadth60)
        regimes[market] = {
            "regime": regime,
            "score": regime_score,
            "breadth20": breadth20,
            "breadth60": breadth60,
            "benchmark_ret20_pct": benchmarks[market]["ret20"] * 100.0,
            "benchmark_ret60_pct": benchmarks[market]["ret60"] * 100.0,
        }

    all_df["regime"] = all_df["market"].map(lambda m: regimes[m]["regime"])
    all_df["regime_score"] = all_df["market"].map(lambda m: regimes[m]["score"])

    # Hedge-fund-style long alpha composite. 모든 하위 점수는 0~100.
    all_df["alpha_score"] = (
        0.30 * all_df["trend_score"]
        + 0.25 * all_df["momentum_score"]
        + 0.20 * all_df["flow_score"]
        + 0.25 * all_df["rs_score"]
    ).clip(0, 100)

    # ------------------------------------------------------------------
    # Three-stage signal ladder
    # 1) CONFIRMED: strict confirmation. Quality first, frequency low.
    # 2) FRESH:     relaxed entry. No ADX>=20 hard filter; ranking absorbs it.
    # 3) EARLY:     pre-cross watchlist. CCI is still <=0 but accelerating.
    # Stages are mutually exclusive so the same stock is not duplicated.
    # ------------------------------------------------------------------
    all_df["dmi_positive"] = all_df["plus_di"] > all_df["minus_di"]
    all_df["dmi_bull"] = all_df["dmi_positive"] & (all_df["adx"] >= args.adx_threshold)

    confirmed_raw = (
        (all_df["cci_cross_age"] <= 1)
        & (all_df["cci"] > 0)
        & all_df["dmi_bull"]
        & all_df["supertrend_good"]
        & (all_df["entry_score"] >= 70)
        & (all_df["flow_score"] >= 50)
        & (all_df["alpha_score"] >= args.confirmed_alpha_threshold)
    )

    # Fresh deliberately does NOT hard-filter Supertrend. BAD is penalized through Entry Score,
    # preserving early signals that may flip bullish shortly after the CCI trigger.
    fresh_raw = (
        (all_df["cci_cross_age"] <= 3)
        & (all_df["cci"] > 0)
        & all_df["dmi_positive"]
        & (all_df["entry_score"] >= 60)
        & (all_df["flow_score"] >= 40)
        & (all_df["alpha_score"] >= args.fresh_alpha_threshold)
    )

    # Early Setup deliberately uses a lower Alpha threshold. Before the CCI cross,
    # the Momentum and Trend components are structurally lower, so Alpha>=60 would
    # make this bucket almost empty. RS>=50 and DMI proximity protect quality.
    early_raw = (
        (all_df["cci"] > -30)
        & (all_df["cci"] <= 0)
        & (all_df["cci_delta3"] >= 25)
        & (all_df["dmi_ratio"] >= 0.85)
        & (all_df["flow_score"] >= 40)
        & (all_df["rs_score"] >= 50)
        & (all_df["entry_score"] >= 45)
        & (all_df["alpha_score"] >= args.early_alpha_threshold)
    )

    all_df["confirmed_buy"] = confirmed_raw
    all_df["fresh_buy"] = fresh_raw & ~confirmed_raw
    all_df["early_setup"] = early_raw & ~confirmed_raw & ~fresh_raw
    all_df["actionable_buy"] = all_df["confirmed_buy"] | all_df["fresh_buy"]

    all_df["signal_tier"] = "RANK"
    all_df.loc[all_df["early_setup"], "signal_tier"] = "EARLY"
    all_df.loc[all_df["fresh_buy"], "signal_tier"] = "FRESH"
    all_df.loc[all_df["confirmed_buy"], "signal_tier"] = "CONFIRMED"

    all_df["active_trend"] = (all_df["cci"] > 0) & all_df["dmi_bull"] & all_df["supertrend_good"]
    all_df["signal_state"] = all_df["alpha_score"].map(signal_state)
    all_df["setup_grade"] = all_df.apply(setup_grade, axis=1)

    tier_order = pd.Categorical(
        all_df["signal_tier"],
        categories=["CONFIRMED", "FRESH", "EARLY", "RANK"],
        ordered=True,
    )
    all_df = (
        all_df.assign(_tier_order=tier_order)
        .sort_values(["_tier_order", "alpha_score"], ascending=[True, False])
        .drop(columns=["_tier_order"])
        .reset_index(drop=True)
    )

    confirmed = all_df[all_df["confirmed_buy"]].sort_values(["entry_score", "alpha_score"], ascending=False)
    fresh = all_df[all_df["fresh_buy"]].sort_values(["entry_score", "alpha_score"], ascending=False)
    early = all_df[all_df["early_setup"]].sort_values(["entry_score", "alpha_score"], ascending=False)
    actionable = all_df[all_df["actionable_buy"]].sort_values(["confirmed_buy", "alpha_score"], ascending=[False, False])
    active = all_df[all_df["active_trend"]].sort_values("alpha_score", ascending=False)
    top_alpha = all_df.sort_values("alpha_score", ascending=False)

    all_df.to_csv(outdir / "latest_all_scored.csv", index=False, encoding="utf-8-sig")
    actionable.to_csv(outdir / "latest_buy_signals.csv", index=False, encoding="utf-8-sig")  # backward-compatible union
    confirmed.to_csv(outdir / "latest_confirmed_buy.csv", index=False, encoding="utf-8-sig")
    fresh.to_csv(outdir / "latest_fresh_buy.csv", index=False, encoding="utf-8-sig")
    early.to_csv(outdir / "latest_early_setups.csv", index=False, encoding="utf-8-sig")
    active.to_csv(outdir / "latest_active_trends.csv", index=False, encoding="utf-8-sig")
    top_alpha.to_csv(outdir / "latest_top_alpha.csv", index=False, encoding="utf-8-sig")

    summary = {
        "model_version": "HF_TECH_V2_3_SUPERTREND_ENTRY",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "symbols_scored": int(len(all_df)),
        "actionable_buy_count": int(len(actionable)),
        "confirmed_buy_count": int(len(confirmed)),
        "fresh_buy_count": int(len(fresh)),
        "early_setup_count": int(len(early)),
        "active_trend_count": int(len(active)),
        "latest_signal_date": str(all_df["signal_date"].max()),
        "confirmed_buy_count_kospi": int((confirmed["market"] == "KOSPI").sum()) if not confirmed.empty else 0,
        "confirmed_buy_count_kosdaq": int((confirmed["market"] == "KOSDAQ").sum()) if not confirmed.empty else 0,
        "fresh_buy_count_kospi": int((fresh["market"] == "KOSPI").sum()) if not fresh.empty else 0,
        "fresh_buy_count_kosdaq": int((fresh["market"] == "KOSDAQ").sum()) if not fresh.empty else 0,
        "parameters": {
            "kospi_n": args.kospi_n,
            "kosdaq_n": args.kosdaq_n,
            "kospi_min_avg20_value": args.kospi_min_avg20_value,
            "kosdaq_min_avg20_value": args.kosdaq_min_avg20_value,
            "cci_period": args.cci_period,
            "dmi_period": args.dmi_period,
            "supertrend_period": args.supertrend_period,
            "supertrend_factor": args.supertrend_factor,
            "adx_threshold": args.adx_threshold,
            "confirmed_alpha_threshold": args.confirmed_alpha_threshold,
            "fresh_alpha_threshold": args.fresh_alpha_threshold,
            "early_alpha_threshold": args.early_alpha_threshold,
            "confirmed_flow_threshold": 50,
            "fresh_flow_threshold": 40,
            "early_flow_threshold": 40,
            "fresh_cross_days": 3,
            "early_cci_floor": -30,
            "early_cci_delta3_min": 25,
            "early_dmi_ratio_min": 0.85,
            "early_rs_min": 50,
            "confirmed_entry_threshold": 70,
            "fresh_entry_threshold": 60,
            "early_entry_threshold": 45,
        },
        "weights": {"trend": 30, "momentum": 25, "flow": 20, "relative_strength": 25},
        "trend_subweights": {"dmi_direction": 35, "adx_strength": 30, "adx_acceleration": 10, "supertrend": 25},
        "entry_weights": {"cci_timing": 30, "supertrend": 25, "dmi_adx": 20, "flow": 15, "extension": 10},
        "regimes": regimes,
    }
    (outdir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
