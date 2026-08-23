#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from scanner import download_benchmark, download_prices
from price_structure_engine import analyze_stock, market_regime
from price_structure_channels import enhance_analysis_chart
from price_structure_wave import apply_wave_mechanism
from price_execution import build_execution_plan

NY = ZoneInfo("America/New_York")


def load_config(path: str) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def as_bool(v: Any) -> bool:
    if isinstance(v, str):
        return v.strip().lower() in {"1", "true", "yes", "y"}
    return bool(v)


def json_default(obj):
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return None if not np.isfinite(obj) else float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, pd.Timestamp):
        return obj.strftime("%Y-%m-%d")
    raise TypeError(type(obj).__name__)


def blend_benchmark(sp: pd.DataFrame, ndx: pd.DataFrame) -> pd.DataFrame:
    if sp is None or sp.empty:
        return ndx
    if ndx is None or ndx.empty:
        return sp
    common = sp.index.intersection(ndx.index)
    if len(common) < 65:
        return sp
    a = sp.loc[common, "Close"].astype(float)
    b = ndx.loc[common, "Close"].astype(float)
    a = a / max(float(a.iloc[0]), 1e-12)
    b = b / max(float(b.iloc[0]), 1e-12)
    return pd.DataFrame({"Close": (a + b) * 50.0}, index=common)


def choose_benchmark(row: pd.Series, sp: pd.DataFrame, ndx: pd.DataFrame, both: pd.DataFrame):
    in_sp = as_bool(row.get("in_sp500", False))
    in_ndx = as_bool(row.get("in_nasdaq100", False))
    if in_sp and in_ndx:
        return both, "S&P 500 + NASDAQ-100"
    if in_ndx:
        return ndx, "NASDAQ-100"
    return sp, "S&P 500"


def summary_row(meta: Dict[str, Any], r: Dict[str, Any]) -> Dict[str, Any]:
    support = r.get("support") or {}
    resistance = r.get("resistance") or {}
    channel = r.get("parallel_channel") or {}
    rs = r.get("relative_strength") or {}
    bq = r.get("breakout_quality") or {}
    trade = r.get("trade") or {}
    wave = r.get("wave") or {}
    scenario = wave.get("scenario") or {}
    entry_zone = wave.get("entry_zone") or {}
    transition = wave.get("channel_transition") or {}
    plan = r.get("execution_plan") or {}
    return {
        "ticker": meta["ticker"],
        "yf_ticker": meta["yf_ticker"],
        "name": meta["name"],
        "market": meta["market"],
        "sector": meta.get("sector", "Unknown"),
        "asof": r["asof"],
        "price": r["price"],
        "setup": r["setup"],
        "setup_label": r["setup_label"],
        "direction": r["direction"],
        "score": r["score"],
        "grade": r["grade"],
        "hard_filter_pass": r["hard_filter_pass"],
        "structure_code": r["structure"]["code"],
        "support_low": support.get("low"),
        "support_high": support.get("high"),
        "resistance_low": resistance.get("low"),
        "resistance_high": resistance.get("high"),
        "parallel_channel": channel.get("direction"),
        "parallel_channel_label": channel.get("label"),
        "parallel_channel_quality": channel.get("quality"),
        "parallel_channel_status": channel.get("status"),
        "wave_stage": wave.get("stage"),
        "wave_label": wave.get("label"),
        "wave_confidence": wave.get("confidence"),
        "channel_transition": transition.get("label"),
        "channel_transition_score": transition.get("score"),
        "buy_status": plan.get("status"),
        "preferred_buy_low": plan.get("preferred_low"),
        "preferred_buy_high": plan.get("preferred_high"),
        "pullback_buy_low": plan.get("buy_zone_low"),
        "pullback_buy_high": plan.get("buy_zone_high"),
        "breakout_buy": plan.get("breakout_buy"),
        "execution_stop": plan.get("stop"),
        "execution_risk_pct": plan.get("risk_pct"),
        "execution_rr1": plan.get("rr1"),
        "entry_zone_low": entry_zone.get("low"),
        "entry_zone_high": entry_zone.get("high"),
        "confirm_price": scenario.get("confirm_price"),
        "invalidation_price": scenario.get("invalidation_price"),
        "wave_target1": scenario.get("target1"),
        "wave_target2": scenario.get("target2"),
        "breakout_quality": bq.get("score"),
        "rvol": bq.get("rvol"),
        "rs_score": rs.get("score"),
        "entry": trade.get("entry"),
        "stop": trade.get("stop"),
        "target1": trade.get("target1"),
        "target2": trade.get("target2"),
        "rr1": trade.get("rr1"),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="US Elliott-style Price Structure / Parallel Channel Scanner")
    ap.add_argument("--config", default="us_price_structure_config.json")
    ap.add_argument("--universe", default="us_results/universe.csv")
    args = ap.parse_args()

    cfg = load_config(args.config)
    universe_path = Path(args.universe)
    if not universe_path.exists():
        raise SystemExit(
            "us_results/universe.csv not found. Run us_scanner.py first so the chart scanner "
            "uses exactly the same validated S&P 500 / NASDAQ-100 universe."
        )

    universe = pd.read_csv(universe_path, dtype={"ticker": str, "yf_ticker": str})
    if universe.empty:
        raise SystemExit("US universe is empty")

    out_dir = Path("us_price_structure_results")
    detail_dir = out_dir / "details"
    detail_dir.mkdir(parents=True, exist_ok=True)

    lookback_days = int(cfg.get("lookback_days", 1100))
    symbols = universe["yf_ticker"].dropna().astype(str).drop_duplicates().tolist()
    print(f"[us-structure] downloading {len(symbols)} symbols, lookback={lookback_days} days")
    prices = download_prices(symbols, lookback_days=lookback_days)

    sp = download_benchmark(cfg.get("benchmark_sp500", "^GSPC"), lookback_days=lookback_days)
    ndx = download_benchmark(cfg.get("benchmark_nasdaq100", "^NDX"), lookback_days=lookback_days)
    both = blend_benchmark(sp, ndx)

    regimes = {
        "S&P 500": market_regime(sp),
        "NASDAQ-100": market_regime(ndx),
        "S&P 500 + NASDAQ-100": market_regime(both),
    }

    min_dollar_value = float(cfg.get("min_avg20_dollar_volume", 10_000_000))
    summary = []
    errors = []

    for i, row in universe.iterrows():
        yf_ticker = str(row.get("yf_ticker", "")).strip()
        ticker = str(row.get("ticker", "")).strip().upper()
        df = prices.get(yf_ticker)
        if df is None or df.empty:
            errors.append({"ticker": ticker, "error": "price data unavailable"})
            continue

        avg20 = float((df["Close"] * df["Volume"]).tail(20).mean())
        if avg20 < min_dollar_value:
            continue

        bench, bench_name = choose_benchmark(row, sp, ndx, both)
        meta = {
            "ticker": ticker,
            "yf_ticker": yf_ticker,
            "name": str(row.get("name", ticker)),
            "market": str(row.get("market", bench_name)),
            "sector": str(row.get("sector", "Unknown")),
            "benchmark": bench_name,
        }

        try:
            # 1) Existing evidence engine: zones, pivots, triangles, breakout quality.
            r = analyze_stock(df, bench, cfg, regimes[bench_name])
            # 2) Keep the current professional parallel-channel implementation and long chart history.
            r = enhance_analysis_chart(df, r, cfg)
            # 3) New primary mechanism: channel reversal -> Elliott-style 1/2/3/4/5 scenario -> fib targets/invalidation.
            r = apply_wave_mechanism(df, r, cfg)
            # 4) Execution layer: pullback/breakout buy points + structural stop.
            r = build_execution_plan(df, r, cfg)
            detail = {"meta": meta, "analysis": r}
            (detail_dir / f"{ticker}.json").write_text(
                json.dumps(detail, ensure_ascii=False, indent=2, default=json_default, allow_nan=False),
                encoding="utf-8",
            )
            summary.append(summary_row(meta, r))
        except Exception as exc:
            errors.append({"ticker": ticker, "name": meta["name"], "error": str(exc)})

        if (i + 1) % 50 == 0:
            print(f"[us-structure] analyzed {i+1}/{len(universe)}")

    summary.sort(key=lambda x: (x["hard_filter_pass"], x["score"], x.get("wave_confidence") or 0), reverse=True)
    payload = {
        "generated_at": datetime.now(NY).isoformat(timespec="seconds"),
        "count": len(summary),
        "errors": errors,
        "config": cfg,
        "market_regimes": regimes,
        "rows": summary,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=json_default, allow_nan=False),
        encoding="utf-8",
    )
    pd.DataFrame(summary).to_csv(out_dir / "summary.csv", index=False, encoding="utf-8-sig")
    (out_dir / "errors.json").write_text(json.dumps(errors, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[us-structure] complete: {len(summary)} symbols / {len(errors)} errors")


if __name__ == "__main__":
    main()
