#!/usr/bin/env python3
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd


EPS = 1e-12


def _fnum(x: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        v = float(x)
        if math.isfinite(v):
            return v
    except Exception:
        pass
    return default


def _clamp(x: float, lo: float, hi: float) -> float:
    return float(max(lo, min(hi, x)))


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h = df["High"].astype(float)
    l = df["Low"].astype(float)
    c = df["Close"].astype(float)
    prev = c.shift(1)
    tr = pd.concat(
        [(h - l).abs(), (h - prev).abs(), (l - prev).abs()],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def _robust_regression(x: np.ndarray, y: np.ndarray) -> Optional[Tuple[float, float, float]]:
    """
    Robust linear centerline.

    This deliberately does NOT connect two highs/lows.  It estimates the
    dominant path of price, trims large outliers, then refits.  Boundary
    touches are used later only to validate the channel.
    """
    if len(x) < 12 or np.ptp(x) <= 0:
        return None

    mask = np.isfinite(x) & np.isfinite(y)
    if mask.sum() < 12:
        return None

    xx = x[mask]
    yy = y[mask]

    slope, intercept = np.polyfit(xx, yy, 1)

    for _ in range(3):
        pred = slope * xx + intercept
        resid = yy - pred
        med = float(np.median(resid))
        mad = float(np.median(np.abs(resid - med)))
        scale = max(1.4826 * mad, float(np.std(resid)) * 0.25, EPS)

        keep = np.abs(resid - med) <= 2.6 * scale
        if keep.sum() < max(12, int(len(xx) * 0.60)):
            order = np.argsort(np.abs(resid - med))
            keep = np.zeros(len(xx), dtype=bool)
            keep[order[: max(12, int(len(xx) * 0.82))]] = True

        slope, intercept = np.polyfit(xx[keep], yy[keep], 1)

    pred = slope * xx + intercept
    resid = yy - pred
    mae = float(np.median(np.abs(resid)))
    return float(slope), float(intercept), mae


def _local_pivots(values: np.ndarray, start_x: int, span: int, mode: str) -> List[int]:
    out: List[int] = []
    n = len(values)
    if n < span * 2 + 1:
        return out

    for i in range(span, n - span):
        window = values[i - span : i + span + 1]
        v = values[i]
        if not np.isfinite(v):
            continue

        if mode == "high":
            if v >= np.nanmax(window) - EPS and v > np.nanmax(
                np.r_[values[i - span : i], values[i + 1 : i + span + 1]]
            ) - EPS:
                out.append(start_x + i)
        else:
            if v <= np.nanmin(window) + EPS and v < np.nanmin(
                np.r_[values[i - span : i], values[i + 1 : i + span + 1]]
            ) + EPS:
                out.append(start_x + i)
    return out


def _separated_count(xs: Sequence[int], min_sep: int) -> Tuple[int, List[int]]:
    if not xs:
        return 0, []
    keep: List[int] = []
    for x in sorted(int(v) for v in xs):
        if not keep or x - keep[-1] >= min_sep:
            keep.append(x)
    return len(keep), keep


def _channel_candidate(
    df: pd.DataFrame,
    atr_s: pd.Series,
    window: int,
    cfg: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    n = len(df)
    if n < window or window < 30:
        return None

    start = n - window
    x = np.arange(start, n, dtype=float)
    sub = df.iloc[start:n]

    high = sub["High"].to_numpy(float)
    low = sub["Low"].to_numpy(float)
    close = sub["Close"].to_numpy(float)
    mid = ((sub["High"] + sub["Low"] + sub["Close"]) / 3.0).to_numpy(float)

    fit = _robust_regression(x, mid)
    if fit is None:
        return None
    slope, intercept, center_mae = fit

    atr_arr = atr_s.iloc[start:n].to_numpy(float)
    finite_atr = atr_arr[np.isfinite(atr_arr) & (atr_arr > 0)]
    current_price = float(close[-1])
    fallback_atr = current_price * 0.02
    med_atr = float(np.median(finite_atr)) if len(finite_atr) else fallback_atr
    med_atr = max(med_atr, current_price * 0.002, EPS)

    slope_pct_20 = float((slope * 20.0) / max(abs(current_price), EPS))
    slope_atr_20 = float((slope * 20.0) / med_atr)

    min_pct = float(cfg.get("channel_min_slope_pct_20", 0.012))
    min_atr = float(cfg.get("channel_min_slope_atr_20", 0.65))
    max_atr = float(cfg.get("channel_max_slope_atr_20", 8.0))

    directional = abs(slope_pct_20) >= min_pct or abs(slope_atr_20) >= min_atr
    if not directional or abs(slope_atr_20) > max_atr:
        return None

    direction = "ASCENDING" if slope > 0 else "DESCENDING"

    center = slope * x + intercept
    low_resid = low - center
    high_resid = high - center

    qlo = float(cfg.get("channel_boundary_quantile_low", 0.10))
    qhi = float(cfg.get("channel_boundary_quantile_high", 0.90))
    lower_offset = float(np.quantile(low_resid[np.isfinite(low_resid)], qlo))
    upper_offset = float(np.quantile(high_resid[np.isfinite(high_resid)], qhi))

    if upper_offset <= lower_offset:
        return None

    width = upper_offset - lower_offset
    width_atr = width / med_atr
    min_width = float(cfg.get("channel_min_width_atr", 1.6))
    max_width = float(cfg.get("channel_max_width_atr", 8.0))
    if not (min_width <= width_atr <= max_width):
        return None

    lower = center + lower_offset
    upper = center + upper_offset

    pivot_span = int(cfg.get("channel_pivot_span", 3))
    piv_hi = _local_pivots(high, start, pivot_span, "high")
    piv_lo = _local_pivots(low, start, pivot_span, "low")

    touch_tol_atr = float(cfg.get("channel_touch_tolerance_atr", 0.50))
    touch_sep = int(cfg.get("channel_touch_separation_bars", 7))

    def atr_at(global_x: int) -> float:
        i = global_x - start
        if 0 <= i < len(atr_arr) and np.isfinite(atr_arr[i]) and atr_arr[i] > 0:
            return float(atr_arr[i])
        return med_atr

    upper_touch_x: List[int] = []
    for gx in piv_hi:
        i = gx - start
        line = upper[i]
        if abs(float(high[i]) - float(line)) <= touch_tol_atr * atr_at(gx):
            upper_touch_x.append(gx)

    lower_touch_x: List[int] = []
    for gx in piv_lo:
        i = gx - start
        line = lower[i]
        if abs(float(low[i]) - float(line)) <= touch_tol_atr * atr_at(gx):
            lower_touch_x.append(gx)

    upper_touches, upper_keep = _separated_count(upper_touch_x, touch_sep)
    lower_touches, lower_keep = _separated_count(lower_touch_x, touch_sep)
    total_touches = upper_touches + lower_touches

    min_primary = int(cfg.get("channel_min_primary_touches", 2))
    min_opposite = int(cfg.get("channel_min_opposite_touches", 1))
    min_total = int(cfg.get("channel_min_total_touches", 4))

    primary_touches = lower_touches if direction == "ASCENDING" else upper_touches
    opposite_touches = upper_touches if direction == "ASCENDING" else lower_touches

    if primary_touches < min_primary or opposite_touches < min_opposite or total_touches < min_total:
        return None

    viol_tol_atr = float(cfg.get("channel_violation_tolerance_atr", 0.65))
    atr_safe = np.where(np.isfinite(atr_arr) & (atr_arr > 0), atr_arr, med_atr)

    within = (low >= lower - viol_tol_atr * atr_safe) & (high <= upper + viol_tol_atr * atr_safe)
    containment = float(np.mean(within))

    min_containment = float(cfg.get("channel_min_containment", 0.82))
    if containment < min_containment:
        return None

    severe_low = low < lower - 1.10 * atr_safe
    severe_high = high > upper + 1.10 * atr_safe
    severe_violations = int(np.sum(severe_low | severe_high))
    violation_ratio = severe_violations / max(window, 1)

    primary_keep = lower_keep if direction == "ASCENDING" else upper_keep
    last_primary_touch = max(primary_keep) if primary_keep else start
    bars_since_primary_touch = (n - 1) - last_primary_touch

    # Quality model: structure first, aesthetics second.
    touch_score = _clamp(
        8.0
        + min(primary_touches, 4) * 5.0
        + min(opposite_touches, 4) * 3.5
        + min(total_touches, 7) * 1.0,
        0,
        32,
    )
    containment_score = _clamp((containment - 0.72) / 0.25, 0, 1) * 22
    trend_score = _clamp(
        max(abs(slope_pct_20) / 0.035, abs(slope_atr_20) / 2.2),
        0,
        1,
    ) * 14
    fit_score = _clamp(1.0 - center_mae / max(width * 0.42, EPS), 0, 1) * 10
    duration_score = _clamp((window - 35) / 125, 0, 1) * 10
    recency_score = _clamp(1.0 - bars_since_primary_touch / max(window * 0.45, 20), 0, 1) * 12
    violation_penalty = min(18.0, severe_violations * 3.0 + violation_ratio * 35.0)

    quality = _clamp(
        touch_score
        + containment_score
        + trend_score
        + fit_score
        + duration_score
        + recency_score
        - violation_penalty,
        0,
        100,
    )

    min_quality = float(cfg.get("channel_min_quality", 62))
    if quality < min_quality:
        return None

    current_lower = float(lower[-1])
    current_upper = float(upper[-1])
    current_center = float(center[-1])
    current_atr = float(atr_safe[-1])
    buffer = 0.22 * current_atr

    if current_price > current_upper + buffer:
        status = "UPSIDE_BREAK"
        status_label = "상단 돌파"
    elif current_price < current_lower - buffer:
        status = "DOWNSIDE_BREAK"
        status_label = "하단 이탈"
    else:
        pos = (current_price - current_lower) / max(current_upper - current_lower, EPS)
        if pos >= 0.82:
            status = "NEAR_UPPER"
            status_label = "채널 상단 접근"
        elif pos <= 0.18:
            status = "NEAR_LOWER"
            status_label = "채널 하단 접근"
        else:
            status = "INSIDE"
            status_label = "채널 내부"

    return {
        "type": "PARALLEL_CHANNEL",
        "direction": direction,
        "label": "상승 평행채널" if direction == "ASCENDING" else "하락 평행채널",
        "window": int(window),
        "x0": int(start),
        "x1": int(n - 1),
        "slope": round(float(slope), 8),
        "slope_pct_20": round(slope_pct_20, 6),
        "slope_atr_20": round(slope_atr_20, 4),
        "lower_y0": round(float(lower[0]), 4),
        "lower_y1": round(float(lower[-1]), 4),
        "center_y0": round(float(center[0]), 4),
        "center_y1": round(float(center[-1]), 4),
        "upper_y0": round(float(upper[0]), 4),
        "upper_y1": round(float(upper[-1]), 4),
        "width": round(float(width), 4),
        "width_atr": round(float(width_atr), 3),
        "upper_touches": int(upper_touches),
        "lower_touches": int(lower_touches),
        "total_touches": int(total_touches),
        "upper_touch_x": [int(x0) for x0 in upper_keep],
        "lower_touch_x": [int(x0) for x0 in lower_keep],
        "containment": round(containment, 4),
        "severe_violations": int(severe_violations),
        "bars_since_primary_touch": int(bars_since_primary_touch),
        "quality": round(float(quality), 1),
        "status": status,
        "status_label": status_label,
        "current_lower": round(current_lower, 4),
        "current_center": round(current_center, 4),
        "current_upper": round(current_upper, 4),
    }


def detect_professional_parallel_channel(
    df: pd.DataFrame,
    cfg: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    Multi-window professional-style parallel channel detector.

    Design intent:
    - Trend is estimated from the body of price action, not by blindly joining
      two extrema.
    - Upper/lower boundaries are parallel by construction.
    - Confirmed local swing touches validate the boundaries.
    - Candidates are rejected for poor containment, too many violations,
      insufficient duration, weak slope, or weak boundary interaction.
    """
    clean = (
        df.copy()
        .dropna(subset=["Open", "High", "Low", "Close", "Volume"])
        .sort_index()
    )
    if len(clean) < 45:
        return None

    atr_s = _atr(clean, int(cfg.get("atr_period", 14)))

    windows = cfg.get(
        "channel_candidate_windows",
        [45, 60, 80, 105, 140, 180, 240],
    )

    candidates: List[Dict[str, Any]] = []
    for raw in windows:
        window = min(int(raw), len(clean))
        if window < 35:
            continue
        obj = _channel_candidate(clean, atr_s, window, cfg)
        if obj:
            candidates.append(obj)

    if not candidates:
        return None

    # Slightly prefer a channel that survives a larger sample without allowing
    # "longest window always wins".
    def rank(c: Dict[str, Any]) -> float:
        duration_bonus = min(4.0, math.log(max(c["window"], 35) / 35.0 + 1.0) * 2.0)
        return float(c["quality"]) + duration_bonus

    return max(candidates, key=rank)


def _full_chart_bars(
    df: pd.DataFrame,
    cfg: Dict[str, Any],
) -> List[Dict[str, Any]]:
    clean = (
        df.copy()
        .dropna(subset=["Open", "High", "Low", "Close", "Volume"])
        .sort_index()
    )
    atr_s = _atr(clean, int(cfg.get("atr_period", 14)))

    history = int(cfg.get("chart_history_bars", 700))
    start = max(0, len(clean) - history)

    out: List[Dict[str, Any]] = []
    for i in range(start, len(clean)):
        row = clean.iloc[i]
        out.append({
            "x": int(i),
            "date": clean.index[i].strftime("%Y-%m-%d"),
            "open": round(float(row["Open"]), 4),
            "high": round(float(row["High"]), 4),
            "low": round(float(row["Low"]), 4),
            "close": round(float(row["Close"]), 4),
            "volume": int(max(0.0, float(row["Volume"]))),
            "atr": round(_fnum(atr_s.iloc[i], 0.0) or 0.0, 4),
        })
    return out


def enhance_analysis_chart(
    df: pd.DataFrame,
    analysis: Dict[str, Any],
    cfg: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Injects:
    - a professional parallel channel
    - long chart history so zooming out reveals older prices

    This intentionally leaves the original engine signals untouched.
    """
    channel = detect_professional_parallel_channel(df, cfg)
    analysis["parallel_channel"] = channel

    chart = analysis.setdefault("chart", {})
    chart["bars"] = _full_chart_bars(df, cfg)
    chart["parallel_channel"] = channel
    chart["history_bars"] = len(chart["bars"])
    chart["initial_mobile_bars"] = int(cfg.get("chart_initial_mobile_bars", 55))
    chart["initial_desktop_bars"] = int(cfg.get("chart_initial_desktop_bars", 100))
    return analysis
