#!/usr/bin/env python3
from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd


EPS = 1e-12


def clamp(x: float, lo: float, hi: float) -> float:
    return float(max(lo, min(hi, x)))


def fnum(x: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        v = float(x)
        if math.isfinite(v):
            return v
    except Exception:
        pass
    return default


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h, l, c = df["High"], df["Low"], df["Close"]
    prev = c.shift(1)
    tr = pd.concat([(h - l).abs(), (h - prev).abs(), (l - prev).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def relative_volume(df: pd.DataFrame, period: int = 20) -> float:
    if len(df) < period + 1:
        return 1.0
    base = float(df["Volume"].iloc[-period-1:-1].median())
    if base <= 0:
        return 1.0
    return float(df["Volume"].iloc[-1] / base)


def close_location_value(df: pd.DataFrame) -> float:
    row = df.iloc[-1]
    rng = float(row["High"] - row["Low"])
    if rng <= EPS:
        return 0.5
    return clamp((float(row["Close"]) - float(row["Low"])) / rng, 0.0, 1.0)


def range_expansion(df: pd.DataFrame, atr_series: pd.Series) -> float:
    a = fnum(atr_series.iloc[-1], 0.0) or 0.0
    if a <= EPS:
        return 1.0
    return float((df["High"].iloc[-1] - df["Low"].iloc[-1]) / a)


def confirmed_pivots(
    df: pd.DataFrame,
    atr_series: pd.Series,
    left: int = 4,
    right: int = 4,
    min_prominence_atr: float = 0.55,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Confirmed pivots only. A pivot at i is not usable until i+right exists."""
    highs: List[Dict[str, Any]] = []
    lows: List[Dict[str, Any]] = []
    h = df["High"].to_numpy(float)
    l = df["Low"].to_numpy(float)
    a = atr_series.to_numpy(float)
    n = len(df)

    for i in range(left, n - right):
        if np.isfinite(a[i]) and a[i] > 0:
            ai = a[i]
        else:
            hist = a[max(0, i-20):i+1]
            hist = hist[np.isfinite(hist) & (hist > 0)]
            if len(hist) == 0:
                continue
            ai = float(np.median(hist))
        hw = h[i-left:i+right+1]
        lw = l[i-left:i+right+1]
        is_high = h[i] >= np.nanmax(hw) - EPS and h[i] > np.nanmax(np.r_[h[i-left:i], h[i+1:i+right+1]]) - EPS
        is_low = l[i] <= np.nanmin(lw) + EPS and l[i] < np.nanmin(np.r_[l[i-left:i], l[i+1:i+right+1]]) + EPS
        local_mid = (np.nanmedian(hw) + np.nanmedian(lw)) / 2.0
        if is_high and (h[i] - local_mid) >= min_prominence_atr * ai:
            highs.append({"x": i, "date": df.index[i].strftime("%Y-%m-%d"), "price": float(h[i]), "confirmed_x": i + right})
        if is_low and (local_mid - l[i]) >= min_prominence_atr * ai:
            lows.append({"x": i, "date": df.index[i].strftime("%Y-%m-%d"), "price": float(l[i]), "confirmed_x": i + right})
    return highs, lows


def classify_market_structure(highs: Sequence[Dict[str, Any]], lows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    if len(highs) < 2 or len(lows) < 2:
        return {"state": "INSUFFICIENT", "label": "구조 부족", "code": "NA", "score": 45}

    h1, h2 = highs[-2]["price"], highs[-1]["price"]
    l1, l2 = lows[-2]["price"], lows[-1]["price"]
    h_up, l_up = h2 > h1, l2 > l1
    h_dn, l_dn = h2 < h1, l2 < l1

    if h_up and l_up:
        return {"state": "BULL_TREND", "label": "상승 구조", "code": "HH / HL", "score": 95}
    if h_dn and l_dn:
        return {"state": "BEAR_TREND", "label": "하락 구조", "code": "LH / LL", "score": 15}
    if h_up and l_dn:
        return {"state": "EXPANDING_RANGE", "label": "변동성 확대", "code": "HH / LL", "score": 45}
    if h_dn and l_up:
        return {"state": "COMPRESSION", "label": "수렴 구조", "code": "LH / HL", "score": 65}
    return {"state": "RANGE", "label": "박스/중립", "code": "MIXED", "score": 50}


def approximate_volume_profile(df: pd.DataFrame, bins: int = 72) -> Dict[str, Any]:
    """Daily OHLCV approximation: each bar's volume is distributed over its high-low range."""
    if df.empty:
        return {"centers": [], "volumes": [], "poc": None, "hvn": [], "lvn": []}
    lo = float(df["Low"].min())
    hi = float(df["High"].max())
    if hi <= lo:
        return {"centers": [lo], "volumes": [float(df["Volume"].sum())], "poc": lo, "hvn": [lo], "lvn": []}

    edges = np.linspace(lo, hi, bins + 1)
    centers = (edges[:-1] + edges[1:]) / 2.0
    volumes = np.zeros(bins, dtype=float)
    typ = ((df["High"] + df["Low"] + df["Close"]) / 3.0).to_numpy(float)

    for j, row in enumerate(df.itertuples()):
        low = float(row.Low)
        high = float(row.High)
        vol = max(0.0, float(row.Volume))
        if vol <= 0:
            continue
        idx = np.where((centers >= low) & (centers <= high))[0]
        if len(idx) == 0:
            idx = np.array([int(np.argmin(np.abs(centers - typ[j])))])
        # Triangular weighting around typical price gives a better daily-bar approximation than close-only.
        dist = np.abs(centers[idx] - typ[j])
        scale = max((high - low) / 2.0, (hi - lo) / bins)
        weights = np.maximum(0.20, 1.0 - dist / max(scale, EPS))
        weights = weights / weights.sum()
        volumes[idx] += vol * weights

    poc_i = int(np.argmax(volumes))
    q_hi = float(np.quantile(volumes, 0.76))
    q_lo = float(np.quantile(volumes, 0.24))
    hvn, lvn = [], []
    for i in range(1, bins - 1):
        if volumes[i] >= q_hi and volumes[i] >= volumes[i-1] and volumes[i] >= volumes[i+1]:
            hvn.append(float(centers[i]))
        if volumes[i] <= q_lo and volumes[i] <= volumes[i-1] and volumes[i] <= volumes[i+1]:
            lvn.append(float(centers[i]))
    return {
        "centers": [float(x) for x in centers],
        "volumes": [float(x) for x in volumes],
        "poc": float(centers[poc_i]),
        "hvn": hvn,
        "lvn": lvn,
    }


def _cluster_levels(candidates: List[Dict[str, Any]], tolerance: float) -> List[Dict[str, Any]]:
    if not candidates:
        return []
    candidates = sorted(candidates, key=lambda x: x["price"])
    groups: List[List[Dict[str, Any]]] = []
    for c in candidates:
        if not groups:
            groups.append([c])
            continue
        g = groups[-1]
        center = np.average([x["price"] for x in g], weights=[x["weight"] for x in g])
        if abs(c["price"] - center) <= tolerance:
            g.append(c)
        else:
            groups.append([c])

    out = []
    for g in groups:
        w = np.array([x["weight"] for x in g], dtype=float)
        p = np.array([x["price"] for x in g], dtype=float)
        center = float(np.average(p, weights=w))
        out.append({
            "center": center,
            "raw_weight": float(w.sum()),
            "sources": sorted(set(x["source"] for x in g)),
            "members": len(g),
        })
    return out


def build_price_zones(
    df: pd.DataFrame,
    atr_series: pd.Series,
    highs: Sequence[Dict[str, Any]],
    lows: Sequence[Dict[str, Any]],
    cfg: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    close = float(df["Close"].iloc[-1])
    a = fnum(atr_series.iloc[-1], close * 0.02) or close * 0.02
    candidates: List[Dict[str, Any]] = []
    profiles: Dict[str, Any] = {}
    windows = list(cfg.get("profile_windows", [60, 120, 250]))
    bins = int(cfg.get("profile_bins", 72))

    for rank, window in enumerate(windows):
        x = df.tail(min(int(window), len(df)))
        prof = approximate_volume_profile(x, bins=bins)
        profiles[str(window)] = prof
        window_weight = 3.0 + rank * 1.5
        if prof.get("poc") is not None:
            candidates.append({"price": prof["poc"], "weight": window_weight + 2.0, "source": f"POC{window}"})
        for p in prof.get("hvn", []):
            candidates.append({"price": p, "weight": window_weight, "source": f"HVN{window}"})

    for p in list(highs)[-8:]:
        rec = clamp(1.0 - (len(df) - 1 - p["x"]) / 140.0, 0.25, 1.0)
        candidates.append({"price": p["price"], "weight": 2.8 * rec, "source": "PIVOT_HIGH"})
    for p in list(lows)[-8:]:
        rec = clamp(1.0 - (len(df) - 1 - p["x"]) / 140.0, 0.25, 1.0)
        candidates.append({"price": p["price"], "weight": 2.8 * rec, "source": "PIVOT_LOW"})

    tol = max(float(cfg.get("zone_cluster_atr", 0.7)) * a, close * 0.005)
    half = max(float(cfg.get("zone_half_width_atr", 0.32)) * a, close * 0.0025)
    clustered = _cluster_levels(candidates, tol)
    zones = []
    recent = df.tail(min(120, len(df)))
    for z in clustered:
        zlo, zhi = z["center"] - half, z["center"] + half
        touches = int(((recent["Low"] <= zhi) & (recent["High"] >= zlo)).sum())
        profile_bonus = sum(1 for s in z["sources"] if s.startswith("POC") or s.startswith("HVN")) * 7
        pivot_bonus = sum(1 for s in z["sources"] if s.startswith("PIVOT")) * 5
        strength = clamp(18 + z["raw_weight"] * 5 + min(touches, 6) * 4 + profile_bonus + pivot_bonus, 0, 100)
        zones.append({
            "low": float(zlo),
            "high": float(zhi),
            "center": float(z["center"]),
            "strength": round(strength, 1),
            "touches": touches,
            "sources": z["sources"],
        })

    zones = sorted(zones, key=lambda z: z["center"])
    # Reduce nearly duplicate final zones after half-width expansion.
    compact: List[Dict[str, Any]] = []
    for z in zones:
        if compact and z["low"] <= compact[-1]["high"]:
            prev = compact[-1]
            if z["strength"] > prev["strength"]:
                prev["center"] = z["center"]
                prev["strength"] = z["strength"]
            prev["low"] = min(prev["low"], z["low"])
            prev["high"] = max(prev["high"], z["high"])
            prev["touches"] = max(prev["touches"], z["touches"])
            prev["sources"] = sorted(set(prev["sources"] + z["sources"]))
        else:
            compact.append(z)
    return compact, profiles


def nearest_zones(zones: Sequence[Dict[str, Any]], price: float) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    supports = [z for z in zones if z["center"] < price]
    resistances = [z for z in zones if z["center"] > price]
    support = max(supports, key=lambda z: z["center"]) if supports else None
    resistance = min(resistances, key=lambda z: z["center"]) if resistances else None
    return support, resistance


def _fit_line(points: Sequence[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if len(points) < 2:
        return None
    xs = np.array([p["x"] for p in points], dtype=float)
    ys = np.array([p["price"] for p in points], dtype=float)
    if np.ptp(xs) <= 0:
        return None
    slope, intercept = np.polyfit(xs, ys, 1)
    pred = slope * xs + intercept
    ss_res = float(np.sum((ys - pred) ** 2))
    ss_tot = float(np.sum((ys - ys.mean()) ** 2))
    r2 = 1.0 - ss_res / (ss_tot + EPS) if ss_tot > EPS else 1.0
    return {"slope": float(slope), "intercept": float(intercept), "r2": clamp(r2, -1.0, 1.0)}


def best_trendline(
    df: pd.DataFrame,
    atr_series: pd.Series,
    pivots: Sequence[Dict[str, Any]],
    kind: str,
    cfg: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    n = len(df)
    lookback = int(cfg.get("trendline_lookback_bars", 120))
    pts = [p for p in pivots if p["x"] >= n - lookback][-7:]
    if len(pts) < 3:
        return None
    a = fnum(atr_series.iloc[-1], float(df["Close"].iloc[-1]) * 0.02) or 1.0
    touch_tol = float(cfg.get("trendline_touch_tolerance_atr", 0.55)) * a
    viol_tol = float(cfg.get("trendline_violation_tolerance_atr", 0.75)) * a
    price = float(df["Close"].iloc[-1])
    candidates = []

    max_r = min(5, len(pts))
    for r in range(3, max_r + 1):
        for combo in itertools.combinations(pts, r):
            fit = _fit_line(combo)
            if not fit:
                continue
            slope_norm = fit["slope"] / max(price, EPS)
            if kind == "descending_resistance" and slope_norm >= -0.00012:
                continue
            if kind == "ascending_support" and slope_norm <= 0.00012:
                continue
            first_x = int(combo[0]["x"])
            last_x = int(combo[-1]["x"])
            if last_x - first_x < 12:
                continue
            residuals = [abs(p["price"] - (fit["slope"] * p["x"] + fit["intercept"])) for p in combo]
            touches = sum(r0 <= touch_tol for r0 in residuals)
            if touches < int(cfg.get("trendline_min_touches", 3)):
                continue

            xs = np.arange(first_x, n, dtype=float)
            line = fit["slope"] * xs + fit["intercept"]
            if kind == "descending_resistance":
                actual = df["High"].iloc[first_x:n].to_numpy(float)
                violations = int(np.sum(actual > line + viol_tol))
            else:
                actual = df["Low"].iloc[first_x:n].to_numpy(float)
                violations = int(np.sum(actual < line - viol_tol))

            duration = n - 1 - first_x
            recency = n - 1 - last_x
            fit_score = max(0.0, fit["r2"]) * 28
            touch_score = min(24.0, touches * 6.0)
            duration_score = min(18.0, duration / 4.0)
            recency_score = max(0.0, 18.0 - recency * 1.5)
            violation_score = max(0.0, 12.0 - violations * 4.0)
            quality = clamp(fit_score + touch_score + duration_score + recency_score + violation_score, 0, 100)
            candidates.append({
                **fit,
                "kind": kind,
                "touches": int(touches),
                "violations": int(violations),
                "quality": round(quality, 1),
                "first_x": first_x,
                "last_pivot_x": last_x,
                "current": float(fit["slope"] * (n - 1) + fit["intercept"]),
                "previous": float(fit["slope"] * (n - 2) + fit["intercept"]),
                "points": list(combo),
            })
    if not candidates:
        return None
    return max(candidates, key=lambda x: x["quality"])


def _recent_pivot_regression(pivots: Sequence[Dict[str, Any]], n: int, lookback: int = 90) -> Optional[Dict[str, Any]]:
    pts = [p for p in pivots if p["x"] >= n - lookback][-5:]
    if len(pts) < 3:
        return None
    # Favor a recent contiguous set but choose size with best normalized residual.
    best = None
    for size in range(3, min(5, len(pts)) + 1):
        subset = pts[-size:]
        fit = _fit_line(subset)
        if not fit:
            continue
        ys = np.array([p["price"] for p in subset], dtype=float)
        xs = np.array([p["x"] for p in subset], dtype=float)
        pred = fit["slope"] * xs + fit["intercept"]
        mae_pct = float(np.mean(np.abs(ys - pred)) / max(np.mean(ys), EPS))
        score = max(0.0, fit["r2"]) * 0.6 + max(0.0, 1.0 - mae_pct / 0.03) * 0.4
        obj = {**fit, "points": list(subset), "fit_score": score, "mae_pct": mae_pct}
        if best is None or obj["fit_score"] > best["fit_score"]:
            best = obj
    return best


def detect_triangle(
    df: pd.DataFrame,
    atr_series: pd.Series,
    highs: Sequence[Dict[str, Any]],
    lows: Sequence[Dict[str, Any]],
    cfg: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    n = len(df)
    upper = _recent_pivot_regression(highs, n)
    lower = _recent_pivot_regression(lows, n)
    if not upper or not lower:
        return None
    price = float(df["Close"].iloc[-1])
    a = fnum(atr_series.iloc[-1], price * 0.02) or price * 0.02
    su = upper["slope"] / max(price, EPS)
    sl = lower["slope"] / max(price, EPS)
    trend_thr = 0.00018
    flat_thr = 0.00022

    if su < -trend_thr and sl > trend_thr:
        ptype = "SYMMETRICAL_TRIANGLE"
        label = "대칭 삼각수렴"
    elif abs(su) <= flat_thr and sl > trend_thr:
        ptype = "ASCENDING_TRIANGLE"
        label = "상승 삼각수렴"
    elif su < -trend_thr and abs(sl) <= flat_thr:
        ptype = "DESCENDING_TRIANGLE"
        label = "하락 삼각수렴"
    else:
        return None

    x_now = n - 1
    up_now = upper["slope"] * x_now + upper["intercept"]
    lo_now = lower["slope"] * x_now + lower["intercept"]
    width_now = up_now - lo_now
    if width_now <= max(0.18 * a, price * 0.002):
        return None

    start_x = int(min(upper["points"][0]["x"], lower["points"][0]["x"]))
    up_start = upper["slope"] * start_x + upper["intercept"]
    lo_start = lower["slope"] * start_x + lower["intercept"]
    width_start = max(up_start - lo_start, EPS)
    shrink = clamp(1.0 - width_now / width_start, 0.0, 1.0)

    denom = upper["slope"] - lower["slope"]
    apex_x = None
    progress = None
    if abs(denom) > EPS:
        apex_x = float((lower["intercept"] - upper["intercept"]) / denom)
        if apex_x > start_x:
            progress = (x_now - start_x) / (apex_x - start_x)

    atr5 = fnum(atr_series.tail(5).mean(), a) or a
    atr20 = fnum(atr_series.tail(20).mean(), a) or a
    atr_ratio = atr5 / max(atr20, EPS)
    vol_recent = float(df["Volume"].tail(5).median())
    vol_prev = float(df["Volume"].iloc[-25:-5].median()) if len(df) >= 25 else float(df["Volume"].median())
    volume_dry = vol_recent / max(vol_prev, EPS)

    compression = 0.0
    compression += clamp(shrink / 0.60, 0, 1) * 45
    compression += clamp((1.05 - atr_ratio) / 0.35, 0, 1) * 35
    compression += clamp((1.10 - volume_dry) / 0.45, 0, 1) * 20

    prog_score = 50.0
    if progress is not None:
        ideal_lo = float(cfg.get("triangle_ideal_progress_low", 0.60))
        ideal_hi = float(cfg.get("triangle_ideal_progress_high", 0.85))
        if ideal_lo <= progress <= ideal_hi:
            prog_score = 100.0
        elif progress < ideal_lo:
            prog_score = clamp(100 - (ideal_lo - progress) * 170, 20, 100)
        else:
            prog_score = clamp(100 - (progress - ideal_hi) * 300, 0, 100)

    pattern_quality = clamp(
        upper["fit_score"] * 25 + lower["fit_score"] * 25 + compression * 0.35 + prog_score * 0.15,
        0, 100,
    )

    buffer = float(cfg.get("breakout_buffer_atr", 0.25)) * a
    current_close = float(df["Close"].iloc[-1])
    breakout = current_close > up_now + buffer
    breakdown = current_close < lo_now - buffer

    return {
        "type": ptype,
        "label": label,
        "upper": {**upper, "current": float(up_now)},
        "lower": {**lower, "current": float(lo_now)},
        "width_now": float(width_now),
        "width_shrink": round(shrink, 4),
        "apex_x": fnum(apex_x),
        "progress": fnum(progress),
        "atr_ratio_5_20": round(float(atr_ratio), 4),
        "volume_dry_ratio": round(float(volume_dry), 4),
        "compression_score": round(clamp(compression, 0, 100), 1),
        "quality": round(pattern_quality, 1),
        "breakout": bool(breakout),
        "breakdown": bool(breakdown),
    }


def benchmark_relative_strength(df: pd.DataFrame, bench: Optional[pd.DataFrame], period: int = 20) -> Dict[str, float]:
    if len(df) <= period:
        return {"stock_return": 0.0, "benchmark_return": 0.0, "excess_return": 0.0, "score": 50.0}
    sret = float(df["Close"].iloc[-1] / df["Close"].iloc[-period-1] - 1.0)
    bret = 0.0
    if bench is not None and not bench.empty:
        common = df.index.intersection(bench.index)
        if len(common) > period:
            b = bench.loc[common, "Close"]
            bret = float(b.iloc[-1] / b.iloc[-period-1] - 1.0)
    excess = sret - bret
    score = clamp(50 + excess * 350, 0, 100)
    return {
        "stock_return": round(sret, 6),
        "benchmark_return": round(bret, 6),
        "excess_return": round(excess, 6),
        "score": round(score, 1),
    }


def market_regime(bench: Optional[pd.DataFrame]) -> Dict[str, Any]:
    if bench is None or len(bench) < 65:
        return {"state": "NEUTRAL", "label": "중립", "score": 50}
    c = bench["Close"]
    ret20 = float(c.iloc[-1] / c.iloc[-21] - 1)
    ret60 = float(c.iloc[-1] / c.iloc[-61] - 1)
    ma20 = float(c.tail(20).mean())
    ma60 = float(c.tail(60).mean())
    px = float(c.iloc[-1])
    points = 0
    points += 1 if ret20 > 0 else -1
    points += 1 if ret60 > 0 else -1
    points += 1 if px > ma20 else -1
    points += 1 if ma20 > ma60 else -1
    if points >= 3:
        return {"state": "RISK_ON", "label": "Risk On", "score": 85, "ret20": ret20, "ret60": ret60}
    if points <= -3:
        return {"state": "RISK_OFF", "label": "Risk Off", "score": 20, "ret20": ret20, "ret60": ret60}
    return {"state": "NEUTRAL", "label": "중립", "score": 50, "ret20": ret20, "ret60": ret60}


def detect_zone_events(
    df: pd.DataFrame,
    atr_series: pd.Series,
    zones: Sequence[Dict[str, Any]],
    cfg: Dict[str, Any],
) -> Dict[str, Any]:
    price = float(df["Close"].iloc[-1])
    a = fnum(atr_series.iloc[-1], price * 0.02) or price * 0.02
    buf = float(cfg.get("breakout_buffer_atr", 0.25)) * a
    retest_window = int(cfg.get("retest_window_bars", 10))
    fail_window = int(cfg.get("failed_break_window_bars", 5))
    closes = df["Close"].to_numpy(float)
    lows = df["Low"].to_numpy(float)
    highs = df["High"].to_numpy(float)

    events = {
        "resistance_breakout": False,
        "support_breakdown": False,
        "retest_confirmed": False,
        "support_bounce": False,
        "failed_breakout": False,
        "failed_breakdown": False,
        "event_zone": None,
    }

    for z in sorted(zones, key=lambda q: q["strength"], reverse=True):
        if z["strength"] < 48:
            continue
        hi, lo = float(z["high"]), float(z["low"])
        # Fresh resistance breakout.
        if len(closes) >= 2 and closes[-1] > hi + buf and closes[-2] <= hi + 0.10 * a:
            events.update({"resistance_breakout": True, "event_zone": z})
            break
        # Fresh support breakdown.
        if len(closes) >= 2 and closes[-1] < lo - buf and closes[-2] >= lo - 0.10 * a:
            events.update({"support_breakdown": True, "event_zone": z})
            break

    for z in sorted(zones, key=lambda q: q["strength"], reverse=True):
        if z["strength"] < 55:
            continue
        hi, lo = float(z["high"]), float(z["low"])
        # Breakout -> retest within recent window -> latest close accepted above zone.
        start = max(1, len(df) - retest_window - 3)
        cross_idx = None
        for i in range(start, len(df) - 1):
            if closes[i] > hi + 0.15 * a and closes[i-1] <= hi + 0.05 * a:
                cross_idx = i
        if cross_idx is not None:
            post_lows = lows[cross_idx+1:]
            if len(post_lows) and np.min(post_lows) <= hi + 0.35 * a and np.min(post_lows) >= lo - 0.45 * a and closes[-1] > hi:
                events.update({"retest_confirmed": True, "event_zone": z})
                break

    # Failed breakout / breakdown.
    for z in sorted(zones, key=lambda q: q["strength"], reverse=True):
        if z["strength"] < 55:
            continue
        hi, lo = float(z["high"]), float(z["low"])
        recent_c = closes[-(fail_window+1):]
        if np.any(recent_c[:-1] > hi + 0.15*a) and closes[-1] < hi - 0.05*a:
            events.update({"failed_breakout": True, "event_zone": z})
            break
        if np.any(recent_c[:-1] < lo - 0.15*a) and closes[-1] > lo + 0.05*a:
            events.update({"failed_breakdown": True, "event_zone": z})
            break

    support, _ = nearest_zones(zones, price)
    if support:
        touched = float(df["Low"].iloc[-1]) <= support["high"] + 0.20*a and float(df["Low"].iloc[-1]) >= support["low"] - 0.45*a
        recovered = price >= support["center"] and close_location_value(df) >= 0.62
        if touched and recovered:
            events.update({"support_bounce": True, "event_zone": support})

    return events


def breakout_quality(
    df: pd.DataFrame,
    atr_series: pd.Series,
    trigger: Optional[float],
    resistance: Optional[Dict[str, Any]],
    rs: Dict[str, Any],
    cfg: Dict[str, Any],
) -> Dict[str, Any]:
    price = float(df["Close"].iloc[-1])
    a = fnum(atr_series.iloc[-1], price * 0.02) or price * 0.02
    rvol = relative_volume(df, int(cfg.get("relative_volume_period", 20)))
    clv = close_location_value(df)
    rngx = range_expansion(df, atr_series)
    dist_atr = (price - trigger) / a if trigger is not None else 0.0
    next_space_atr = ((resistance["low"] - price) / a) if resistance and resistance["low"] > price else 4.0

    distance_score = clamp(dist_atr / 0.60, 0, 1) * 20
    volume_score = clamp((rvol - 0.8) / 1.2, 0, 1) * 20
    candle_score = clamp((clv - 0.45) / 0.50, 0, 1) * 15
    range_score = clamp((rngx - 0.7) / 1.0, 0, 1) * 15
    space_score = clamp(next_space_atr / 3.0, 0, 1) * 20
    rs_score = clamp(float(rs.get("score", 50)) / 100.0, 0, 1) * 10
    total = distance_score + volume_score + candle_score + range_score + space_score + rs_score
    return {
        "score": round(clamp(total, 0, 100), 1),
        "distance_atr": round(float(dist_atr), 3),
        "rvol": round(float(rvol), 3),
        "clv": round(float(clv), 3),
        "range_atr": round(float(rngx), 3),
        "next_space_atr": round(float(next_space_atr), 3),
        "components": {
            "distance": round(distance_score, 1),
            "volume": round(volume_score, 1),
            "candle": round(candle_score, 1),
            "range": round(range_score, 1),
            "space": round(space_score, 1),
            "relative_strength": round(rs_score, 1),
        },
    }


def trade_structure(
    df: pd.DataFrame,
    atr_series: pd.Series,
    support: Optional[Dict[str, Any]],
    resistance: Optional[Dict[str, Any]],
    lows: Sequence[Dict[str, Any]],
    triangle: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    entry = float(df["Close"].iloc[-1])
    a = fnum(atr_series.iloc[-1], entry * 0.02) or entry * 0.02
    candidates = []
    if support and support["low"] < entry:
        candidates.append(float(support["low"] - 0.20*a))
    if lows:
        p = float(lows[-1]["price"] - 0.20*a)
        if p < entry:
            candidates.append(p)
    if triangle:
        p = float(triangle["lower"]["current"] - 0.20*a)
        if p < entry:
            candidates.append(p)
    stop = max(candidates) if candidates else entry - 1.25*a
    if entry - stop < 0.60*a:
        stop = entry - 0.80*a
    if stop <= 0 or stop >= entry:
        stop = entry - 1.25*a
    risk = entry - stop

    if resistance and resistance["low"] > entry + 0.40*a:
        target1 = float(resistance["low"])
    else:
        target1 = entry + 3.0*risk
    target2 = max(entry + 3.0*risk, target1 + 1.5*a)
    rr1 = (target1 - entry) / max(risk, EPS)
    rr2 = (target2 - entry) / max(risk, EPS)
    return {
        "entry": round(entry, 4),
        "stop": round(stop, 4),
        "risk": round(risk, 4),
        "risk_atr": round(risk / a, 3),
        "target1": round(target1, 4),
        "target2": round(target2, 4),
        "rr1": round(rr1, 3),
        "rr2": round(rr2, 3),
    }


def _breakout_ready(
    price: float,
    atr_value: float,
    resistance: Optional[Dict[str, Any]],
    triangle: Optional[Dict[str, Any]],
    rs: Dict[str, Any],
    cfg: Dict[str, Any],
) -> Tuple[bool, Optional[float], Optional[float]]:
    triggers = []
    if resistance and resistance["low"] > price:
        triggers.append(float(resistance["low"]))
    if triangle and triangle["upper"]["current"] > price:
        triggers.append(float(triangle["upper"]["current"]))
    if not triggers:
        return False, None, None
    trigger = min(triggers)
    dist = (trigger - price) / max(atr_value, EPS)
    lo = float(cfg.get("breakout_ready_min_atr", 0.05))
    hi = float(cfg.get("breakout_ready_max_atr", 0.65))
    compression_ok = triangle is None or float(triangle["compression_score"]) >= 58
    rs_ok = float(rs.get("score", 50)) >= 48
    return bool(lo <= dist <= hi and compression_ok and rs_ok), trigger, dist


def _grade(score: float) -> str:
    if score >= 85:
        return "A+"
    if score >= 75:
        return "A"
    if score >= 65:
        return "B"
    if score >= 55:
        return "C"
    return "D"


def analyze_stock(
    df: pd.DataFrame,
    benchmark: Optional[pd.DataFrame],
    cfg: Dict[str, Any],
    market_regime_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    df = df.copy().dropna(subset=["Open", "High", "Low", "Close", "Volume"]).sort_index()
    if len(df) < int(cfg.get("min_bars", 120)):
        raise ValueError("not enough bars")

    atr_s = atr(df, int(cfg.get("atr_period", 14)))
    price = float(df["Close"].iloc[-1])
    a = fnum(atr_s.iloc[-1], price * 0.02) or price * 0.02
    highs, lows = confirmed_pivots(
        df, atr_s,
        left=int(cfg.get("pivot_left", 4)),
        right=int(cfg.get("pivot_right", 4)),
        min_prominence_atr=float(cfg.get("pivot_min_prominence_atr", 0.55)),
    )
    structure = classify_market_structure(highs, lows)
    zones, profiles = build_price_zones(df, atr_s, highs, lows, cfg)
    support, resistance = nearest_zones(zones, price)
    desc = best_trendline(df, atr_s, highs, "descending_resistance", cfg)
    asc = best_trendline(df, atr_s, lows, "ascending_support", cfg)
    triangle = detect_triangle(df, atr_s, highs, lows, cfg)
    rs = benchmark_relative_strength(df, benchmark, 20)
    regime = market_regime_info or market_regime(benchmark)
    events = detect_zone_events(df, atr_s, zones, cfg)

    buffer = float(cfg.get("breakout_buffer_atr", 0.25)) * a
    desc_break = False
    asc_breakdown = False
    if desc and desc["quality"] >= float(cfg.get("trendline_min_quality", 60)):
        desc_break = price > desc["current"] + buffer and float(df["Close"].iloc[-2]) <= desc["previous"] + 0.10*a
    if asc and asc["quality"] >= float(cfg.get("trendline_min_quality", 60)):
        asc_breakdown = price < asc["current"] - buffer and float(df["Close"].iloc[-2]) >= asc["previous"] - 0.10*a

    ready, ready_trigger, ready_dist = _breakout_ready(price, a, resistance, triangle, rs, cfg)

    bullish_trigger = None
    if triangle and triangle.get("breakout"):
        bullish_trigger = float(triangle["upper"]["current"])
    elif desc_break and desc:
        bullish_trigger = float(desc["current"])
    elif events["resistance_breakout"] and events["event_zone"]:
        bullish_trigger = float(events["event_zone"]["high"])
    elif ready_trigger:
        bullish_trigger = float(ready_trigger)

    bq = breakout_quality(df, atr_s, bullish_trigger, resistance, rs, cfg)
    trade = trade_structure(df, atr_s, support, resistance, lows, triangle)

    # Setup priority: failures/risk first, then confirmed entries, then watchlist.
    if events["failed_breakout"]:
        setup, setup_label, direction = "FAILED_BREAKOUT", "실패 돌파 / Bull Trap", "BEARISH"
    elif events["failed_breakdown"]:
        setup, setup_label, direction = "FAILED_BREAKDOWN", "하방 이탈 실패 / 복귀", "BULLISH"
    elif events["retest_confirmed"]:
        setup, setup_label, direction = "RETEST_ENTRY", "돌파 후 리테스트 확인", "BULLISH"
    elif triangle and triangle["breakout"]:
        setup, setup_label, direction = "TRIANGLE_BREAKOUT", "삼각수렴 상방 돌파", "BULLISH"
    elif triangle and triangle["breakdown"]:
        setup, setup_label, direction = "TRIANGLE_BREAKDOWN", "삼각수렴 하방 이탈", "BEARISH"
    elif desc_break:
        setup, setup_label, direction = "TRENDLINE_BREAKOUT", "하락 추세선 돌파", "BULLISH"
    elif events["resistance_breakout"]:
        setup, setup_label, direction = "CONFIRMED_BREAKOUT", "매물대 저항 돌파", "BULLISH"
    elif asc_breakdown:
        setup, setup_label, direction = "TRENDLINE_BREAKDOWN", "상승 추세선 이탈", "BEARISH"
    elif events["support_breakdown"]:
        setup, setup_label, direction = "SUPPORT_BREAKDOWN", "핵심 지지 이탈", "BEARISH"
    elif events["support_bounce"]:
        setup, setup_label, direction = "SUPPORT_BOUNCE", "핵심 지지 반등", "BULLISH"
    elif ready:
        setup, setup_label, direction = "BREAKOUT_READY", "돌파 임박", "WATCH"
    elif triangle:
        setup, setup_label, direction = "COMPRESSION_WATCH", "수렴 관찰", "WATCH"
    else:
        setup, setup_label, direction = "NEUTRAL", "뚜렷한 셋업 없음", "NEUTRAL"

    # Position/location score (20)
    pos_score = 8.0
    if support:
        dist_sup = (price - support["high"]) / a
        pos_score += clamp((2.2 - max(dist_sup, 0)) / 2.2, 0, 1) * 5
        pos_score += float(support["strength"]) / 100 * 3
    if resistance:
        space = (resistance["low"] - price) / a
        pos_score += clamp(space / 3.0, 0, 1) * 4
    else:
        pos_score += 4
    pos_score = clamp(pos_score, 0, 20)

    structure_score = clamp(float(structure["score"]) / 10.0, 0, 10)
    pattern_score = 5.0
    if triangle:
        pattern_score = float(triangle["quality"]) / 100 * 15
    elif desc or asc:
        q = max(float(desc["quality"]) if desc else 0, float(asc["quality"]) if asc else 0)
        pattern_score = q / 100 * 15
    pattern_score = clamp(pattern_score, 0, 15)

    if setup in {"BREAKOUT_READY", "COMPRESSION_WATCH"}:
        breakout_component = (float(triangle["compression_score"]) / 100 * 14 + 4) if triangle else 8
    elif direction == "BULLISH":
        breakout_component = float(bq["score"]) / 100 * 20
    elif direction == "BEARISH":
        breakout_component = max(0.0, 8.0 - float(bq["score"]) / 100 * 4)
    else:
        breakout_component = 7.0
    breakout_component = clamp(breakout_component, 0, 20)

    vol_score = clamp((float(bq["rvol"]) - 0.65) / 1.35, 0, 1) * 10
    rs_score = clamp(float(rs["score"]) / 100 * 10, 0, 10)
    risk_score = clamp(float(trade["rr1"]) / 3.0, 0, 1) * 10
    regime_score = clamp(float(regime.get("score", 50)) / 100 * 5, 0, 5)
    total = pos_score + structure_score + pattern_score + breakout_component + vol_score + rs_score + risk_score + regime_score

    # Explicit penalties for structural failures and downside breaks.
    if setup == "FAILED_BREAKOUT":
        total -= 22
    elif setup in {"SUPPORT_BREAKDOWN", "TRENDLINE_BREAKDOWN", "TRIANGLE_BREAKDOWN"}:
        total -= 18
    elif setup == "FAILED_BREAKDOWN":
        total += 7
    total = clamp(total, 0, 100)
    grade = _grade(total)

    breakout_type = setup in {"CONFIRMED_BREAKOUT", "TRENDLINE_BREAKOUT", "TRIANGLE_BREAKOUT", "RETEST_ENTRY"}
    hard_pass = (
        direction == "BULLISH"
        and total >= float(cfg.get("min_final_trade_score", 65))
        and float(trade["rr1"]) >= float(cfg.get("min_rr", 1.8))
        and (not breakout_type or float(bq["score"]) >= float(cfg.get("min_breakout_quality", 60)))
    )
    if setup == "BREAKOUT_READY":
        hard_pass = False

    poc_candidates = []
    for _, prof in profiles.items():
        if prof.get("poc") is not None:
            poc_candidates.append(prof["poc"])
    primary_poc = min(poc_candidates, key=lambda x: abs(x-price)) if poc_candidates else None

    return {
        "asof": df.index[-1].strftime("%Y-%m-%d"),
        "price": round(price, 4),
        "atr": round(a, 4),
        "avg20_value": round(float((df["Close"] * df["Volume"]).tail(20).mean()), 2),
        "structure": structure,
        "support": support,
        "resistance": resistance,
        "zones": zones,
        "profiles": {
            k: {"poc": v.get("poc"), "hvn": v.get("hvn", []), "lvn": v.get("lvn", [])}
            for k, v in profiles.items()
        },
        "primary_poc": fnum(primary_poc),
        "descending_trendline": desc,
        "ascending_trendline": asc,
        "triangle": triangle,
        "relative_strength": rs,
        "market_regime": regime,
        "events": events,
        "breakout_quality": bq,
        "trade": trade,
        "setup": setup,
        "setup_label": setup_label,
        "direction": direction,
        "score": round(total, 1),
        "grade": grade,
        "hard_filter_pass": bool(hard_pass),
        "breakout_ready_distance_atr": fnum(ready_dist),
        "chart": make_chart_payload(df, atr_s, highs, lows, desc, asc, triangle, support, resistance, primary_poc, int(cfg.get("chart_bars", 140))),
    }


def make_chart_payload(
    df: pd.DataFrame,
    atr_series: pd.Series,
    highs: Sequence[Dict[str, Any]],
    lows: Sequence[Dict[str, Any]],
    desc: Optional[Dict[str, Any]],
    asc: Optional[Dict[str, Any]],
    triangle: Optional[Dict[str, Any]],
    support: Optional[Dict[str, Any]],
    resistance: Optional[Dict[str, Any]],
    poc: Optional[float],
    bars: int = 140,
) -> Dict[str, Any]:
    start = max(0, len(df) - bars)
    out_bars = []
    for i in range(start, len(df)):
        row = df.iloc[i]
        out_bars.append({
            "x": i,
            "date": df.index[i].strftime("%Y-%m-%d"),
            "open": round(float(row["Open"]), 4),
            "high": round(float(row["High"]), 4),
            "low": round(float(row["Low"]), 4),
            "close": round(float(row["Close"]), 4),
            "volume": int(max(0, float(row["Volume"]))),
            "atr": round(fnum(atr_series.iloc[i], 0.0) or 0.0, 4),
        })

    def line_payload(obj: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not obj:
            return None
        x0 = max(start, int(obj.get("first_x", obj.get("points", [{}])[0].get("x", start))))
        x1 = len(df) - 1
        return {
            "x0": x0,
            "y0": float(obj["slope"] * x0 + obj["intercept"]),
            "x1": x1,
            "y1": float(obj["slope"] * x1 + obj["intercept"]),
            "quality": fnum(obj.get("quality")),
        }

    tri = None
    if triangle:
        up, lo = triangle["upper"], triangle["lower"]
        x0 = max(start, min(up["points"][0]["x"], lo["points"][0]["x"]))
        x1 = len(df)-1
        tri = {
            "type": triangle["type"],
            "upper": {"x0": x0, "y0": up["slope"]*x0+up["intercept"], "x1": x1, "y1": up["slope"]*x1+up["intercept"]},
            "lower": {"x0": x0, "y0": lo["slope"]*x0+lo["intercept"], "x1": x1, "y1": lo["slope"]*x1+lo["intercept"]},
        }
    return {
        "bars": out_bars,
        "pivot_highs": [p for p in highs if p["x"] >= start],
        "pivot_lows": [p for p in lows if p["x"] >= start],
        "descending_trendline": line_payload(desc),
        "ascending_trendline": line_payload(asc),
        "triangle": tri,
        "support": support,
        "resistance": resistance,
        "poc": fnum(poc),
    }
