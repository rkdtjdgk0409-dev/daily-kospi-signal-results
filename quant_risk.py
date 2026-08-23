#!/usr/bin/env python3
"""Institution-style risk layer for the alpha screeners.

This module does not copy Goldman Sachs proprietary models.  It implements
standard public quantitative risk measures commonly used in institutional
portfolio workflows: annualized volatility, market beta, maximum drawdown,
historical VaR/Expected Shortfall, a risk-quality score, a risk-adjusted
quant score, and a volatility-aware model position size.
"""
from __future__ import annotations

import math
from typing import Mapping

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def _finite(value: object, default: float = float("nan")) -> float:
    try:
        x = float(value)
        return x if math.isfinite(x) else default
    except Exception:
        return default


def _close_series(frame: pd.DataFrame | None) -> pd.Series:
    if frame is None or frame.empty or "Close" not in frame.columns:
        return pd.Series(dtype=float)
    s = pd.to_numeric(frame["Close"], errors="coerce").dropna().copy()
    s.index = pd.to_datetime(s.index).tz_localize(None)
    return s[~s.index.duplicated(keep="last")].sort_index()


def _linear_quality(value: float, good: float, bad: float) -> float:
    """100 at/below good, 0 at/above bad, linear in between."""
    if not math.isfinite(value):
        return 50.0
    if value <= good:
        return 100.0
    if value >= bad:
        return 0.0
    return 100.0 * (bad - value) / (bad - good)


def compute_risk_metrics(
    stock_frame: pd.DataFrame,
    benchmark_frame: pd.DataFrame,
    *,
    vol_window: int = 60,
    beta_window: int = 120,
    drawdown_window: int = 120,
    var_window: int = 60,
) -> dict[str, float]:
    """Return trailing risk metrics using regular daily close-to-close returns.

    VaR and Expected Shortfall are reported as positive one-day loss magnitudes
    in percent. MDD is reported as a negative percentage.
    """
    stock_close = _close_series(stock_frame)
    bench_close = _close_series(benchmark_frame)
    if len(stock_close) < 30:
        return {
            "vol60_ann_pct": float("nan"),
            "beta120": float("nan"),
            "mdd120_pct": float("nan"),
            "var95_60_pct": float("nan"),
            "es95_60_pct": float("nan"),
            "downside_vol60_ann_pct": float("nan"),
        }

    sret = stock_close.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
    vol_slice = sret.tail(vol_window)
    vol = float(vol_slice.std(ddof=1) * np.sqrt(TRADING_DAYS) * 100.0) if len(vol_slice) >= 20 else float("nan")

    neg = vol_slice[vol_slice < 0]
    downside = float(neg.std(ddof=1) * np.sqrt(TRADING_DAYS) * 100.0) if len(neg) >= 8 else vol

    # Beta on overlapping trading dates only.
    bret = bench_close.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
    aligned = pd.concat([sret.rename("stock"), bret.rename("bench")], axis=1, join="inner").dropna().tail(beta_window)
    if len(aligned) >= 30 and float(aligned["bench"].var(ddof=1)) > 1e-12:
        beta = float(aligned["stock"].cov(aligned["bench"]) / aligned["bench"].var(ddof=1))
    else:
        beta = float("nan")

    dd_close = stock_close.tail(drawdown_window)
    if len(dd_close) >= 20:
        drawdown = dd_close / dd_close.cummax() - 1.0
        mdd = float(drawdown.min() * 100.0)
    else:
        mdd = float("nan")

    var_slice = sret.tail(var_window)
    if len(var_slice) >= 20:
        q05 = float(np.nanquantile(var_slice, 0.05))
        var95 = max(0.0, -q05 * 100.0)
        tail = var_slice[var_slice <= q05]
        es95 = max(0.0, -float(tail.mean()) * 100.0) if len(tail) else var95
    else:
        var95 = float("nan")
        es95 = float("nan")

    return {
        "vol60_ann_pct": vol,
        "beta120": beta,
        "mdd120_pct": mdd,
        "var95_60_pct": var95,
        "es95_60_pct": es95,
        "downside_vol60_ann_pct": downside,
    }


def risk_quality_score(metrics: Mapping[str, object]) -> float:
    """0-100 score where higher means a safer risk profile.

    Thresholds are deliberately transparent, not fitted to future returns.
    They can later be calibrated by walk-forward validation.
    """
    vol = _finite(metrics.get("vol60_ann_pct"))
    beta = abs(_finite(metrics.get("beta120"), 1.0))
    mdd = abs(_finite(metrics.get("mdd120_pct")))
    var95 = _finite(metrics.get("var95_60_pct"))
    es95 = _finite(metrics.get("es95_60_pct"))

    subscores = {
        "vol": _linear_quality(vol, good=18.0, bad=60.0),
        "beta": _linear_quality(beta, good=0.80, bad=2.00),
        "mdd": _linear_quality(mdd, good=8.0, bad=40.0),
        "var": _linear_quality(var95, good=1.50, bad=5.00),
        "es": _linear_quality(es95, good=2.00, bad=7.00),
    }
    score = (
        0.30 * subscores["vol"]
        + 0.20 * subscores["beta"]
        + 0.25 * subscores["mdd"]
        + 0.15 * subscores["var"]
        + 0.10 * subscores["es"]
    )
    return round(float(np.clip(score, 0.0, 100.0)), 2)


def final_quant_score(alpha_score: object, risk_quality: object, alpha_weight: float = 0.70) -> float:
    alpha = float(np.clip(_finite(alpha_score, 0.0), 0.0, 100.0))
    rq = float(np.clip(_finite(risk_quality, 50.0), 0.0, 100.0))
    aw = float(np.clip(alpha_weight, 0.0, 1.0))
    return round(aw * alpha + (1.0 - aw) * rq, 2)


def model_position_size_pct(
    *,
    alpha_score: object,
    risk_quality: object,
    vol60_ann_pct: object,
    signal_tier: str,
    regime: str,
    max_weight_pct: float = 15.0,
) -> float:
    """Standalone model size using a simple volatility budget.

    This is not a personalized portfolio recommendation. It intentionally does
    not use account value, leverage, correlations, taxes, or existing holdings.
    RANK-only names receive 0%; Early/Fresh are scaled below Confirmed.
    """
    tier = str(signal_tier or "RANK").upper()
    if tier == "RANK":
        return 0.0

    vol = _finite(vol60_ann_pct, 40.0)
    vol = max(vol, 8.0)
    # 3% standalone annualized volatility contribution before conviction scaling.
    base_weight = 100.0 * 0.03 / (vol / 100.0)

    alpha = float(np.clip(_finite(alpha_score, 50.0), 0.0, 100.0))
    rq = float(np.clip(_finite(risk_quality, 50.0), 0.0, 100.0))
    conviction = 0.55 + 0.45 * (alpha / 100.0)
    quality = 0.65 + 0.35 * (rq / 100.0)
    tier_mult = {"CONFIRMED": 1.00, "FRESH": 0.75, "EARLY": 0.40}.get(tier, 0.0)
    regime_mult = {"RISK-ON": 1.00, "NEUTRAL": 0.82, "RISK-OFF": 0.55}.get(str(regime or "NEUTRAL").upper(), 0.82)

    size = base_weight * conviction * quality * tier_mult * regime_mult
    return round(float(np.clip(size, 0.0, max_weight_pct)), 1)


def risk_snapshot(frame: pd.DataFrame) -> dict[str, float | str]:
    """Cross-sectional dashboard summary for a scored universe."""
    if frame is None or frame.empty:
        return {}

    def med(col: str) -> float:
        if col not in frame:
            return float("nan")
        x = pd.to_numeric(frame[col], errors="coerce")
        return round(float(x.median()), 2) if x.notna().any() else float("nan")

    out: dict[str, float | str] = {
        "median_vol60_ann_pct": med("vol60_ann_pct"),
        "median_beta120": med("beta120"),
        "median_mdd120_pct": med("mdd120_pct"),
        "median_var95_60_pct": med("var95_60_pct"),
        "median_es95_60_pct": med("es95_60_pct"),
        "median_risk_quality": med("risk_quality_score"),
        "median_final_quant_score": med("final_quant_score"),
    }
    if "final_quant_score" in frame and pd.to_numeric(frame["final_quant_score"], errors="coerce").notna().any():
        idx = pd.to_numeric(frame["final_quant_score"], errors="coerce").idxmax()
        out["top_quant_name"] = str(frame.loc[idx].get("name", frame.loc[idx].get("ticker", "-")))
        out["top_quant_score"] = round(float(frame.loc[idx, "final_quant_score"]), 2)
    return out
