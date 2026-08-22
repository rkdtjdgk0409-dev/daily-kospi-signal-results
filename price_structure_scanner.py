#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import traceback
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd

from scanner import get_universe, download_prices, download_benchmark, now_kst
from price_structure_engine import analyze_stock, market_regime
from price_structure_channels import enhance_analysis_chart


def load_config(path: str) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


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


def summary_row(meta: Dict[str, Any], r: Dict[str, Any]) -> Dict[str, Any]:
    support = r.get("support") or {}
    resistance = r.get("resistance") or {}
    tri = r.get("triangle") or {}
    desc = r.get("descending_trendline") or {}
    asc = r.get("ascending_trendline") or {}
    channel = r.get("parallel_channel") or {}
    rs = r.get("relative_strength") or {}
    bq = r.get("breakout_quality") or {}
    trade = r.get("trade") or {}

    return {
        "ticker": meta["ticker"],
        "yf_ticker": meta["yf_ticker"],
        "name": meta["name"],
        "market": meta["market"],
        "asof": r["asof"],
        "price": r["price"],
        "setup": r["setup"],
        "setup_label": r["setup_label"],
        "direction": r["direction"],
        "score": r["score"],
        "grade": r["grade"],
        "hard_filter_pass": r["hard_filter_pass"],
        "structure": r["structure"]["state"],
        "structure_label": r["structure"]["label"],
        "structure_code": r["structure"]["code"],
        "support_low": support.get("low"),
        "support_high": support.get("high"),
        "support_strength": support.get("strength"),
        "resistance_low": resistance.get("low"),
        "resistance_high": resistance.get("high"),
        "resistance_strength": resistance.get("strength"),
        "trendline_down_quality": desc.get("quality"),
        "trendline_up_quality": asc.get("quality"),
        "parallel_channel": channel.get("direction"),
        "parallel_channel_label": channel.get("label"),
        "parallel_channel_quality": channel.get("quality"),
        "parallel_channel_status": channel.get("status"),
        "parallel_channel_touches": channel.get("total_touches"),
        "triangle": tri.get("type"),
        "triangle_quality": tri.get("quality"),
        "compression_score": tri.get("compression_score"),
        "triangle_progress": tri.get("progress"),
        "breakout_quality": bq.get("score"),
        "rvol": bq.get("rvol"),
        "clv": bq.get("clv"),
        "range_atr": bq.get("range_atr"),
        "space_atr": bq.get("next_space_atr"),
        "rs20_excess": rs.get("excess_return"),
        "rs_score": rs.get("score"),
        "entry": trade.get("entry"),
        "stop": trade.get("stop"),
        "target1": trade.get("target1"),
        "target2": trade.get("target2"),
        "rr1": trade.get("rr1"),
        "rr2": trade.get("rr2"),
        "avg20_value": r.get("avg20_value"),
        "market_regime": r.get("market_regime", {}).get("state"),
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Korea Price Structure / Chart Pattern Scanner"
    )
    ap.add_argument("--config", default="price_structure_config.json")
    ap.add_argument("--kospi-n", type=int, default=200)
    ap.add_argument("--kosdaq-n", type=int, default=150)
    ap.add_argument("--kospi-min-avg20-value", type=float, default=None)
    ap.add_argument("--kosdaq-min-avg20-value", type=float, default=None)
    args = ap.parse_args()

    cfg = load_config(args.config)
    if args.kospi_min_avg20_value is not None:
        cfg["kospi_min_avg20_value"] = args.kospi_min_avg20_value
    if args.kosdaq_min_avg20_value is not None:
        cfg["kosdaq_min_avg20_value"] = args.kosdaq_min_avg20_value

    out_dir = Path("price_structure_results")
    detail_dir = out_dir / "details"
    detail_dir.mkdir(parents=True, exist_ok=True)

    print("[structure] loading universe")
    universe = get_universe(args.kospi_n, args.kosdaq_n)
    tickers = universe["yf_ticker"].tolist()

    lookback_days = int(cfg.get("lookback_days", 1100))
    print(
        f"[structure] downloading {len(tickers)} symbols "
        f"(lookback_days={lookback_days})"
    )
    prices = download_prices(tickers, lookback_days=lookback_days)

    print("[structure] downloading benchmarks")
    kospi_bench = download_benchmark(
        cfg.get("benchmark_kospi", "^KS11"),
        lookback_days=lookback_days,
    )
    kosdaq_bench = download_benchmark(
        cfg.get("benchmark_kosdaq", "^KQ11"),
        lookback_days=lookback_days,
    )
    regimes = {
        "KOSPI": market_regime(kospi_bench),
        "KOSDAQ": market_regime(kosdaq_bench),
    }

    summary = []
    errors = []

    for i, row in universe.iterrows():
        yf_ticker = row["yf_ticker"]
        df = prices.get(yf_ticker)

        if df is None or df.empty:
            errors.append({
                "ticker": row["ticker"],
                "name": row["name"],
                "error": "price data unavailable",
            })
            continue

        avg20_value = float(
            (df["Close"] * df["Volume"]).tail(20).mean()
        )
        min_value = float(
            cfg.get(
                "kospi_min_avg20_value"
                if row["market"] == "KOSPI"
                else "kosdaq_min_avg20_value",
                0,
            )
        )
        if avg20_value < min_value:
            continue

        bench = kospi_bench if row["market"] == "KOSPI" else kosdaq_bench
        meta = {
            "ticker": str(row["ticker"]),
            "yf_ticker": yf_ticker,
            "name": row["name"],
            "market": row["market"],
        }

        try:
            r = analyze_stock(df, bench, cfg, regimes[row["market"]])

            # V2: professional parallel channel + long interactive chart history.
            r = enhance_analysis_chart(df, r, cfg)

            detail = {"meta": meta, "analysis": r}
            (detail_dir / f"{row['ticker']}.json").write_text(
                json.dumps(
                    detail,
                    ensure_ascii=False,
                    indent=2,
                    default=json_default,
                    allow_nan=False,
                ),
                encoding="utf-8",
            )
            summary.append(summary_row(meta, r))

        except Exception as e:
            errors.append({
                "ticker": row["ticker"],
                "name": row["name"],
                "error": str(e),
            })
            print(f"[warn] {row['ticker']} {row['name']}: {e}")
            if len(errors) <= 3:
                traceback.print_exc(limit=1)

        if (i + 1) % 25 == 0:
            print(f"[structure] analyzed {i+1}/{len(universe)}")

    summary.sort(
        key=lambda x: (x["hard_filter_pass"], x["score"]),
        reverse=True,
    )

    generated = now_kst().isoformat(timespec="seconds")
    payload = {
        "generated_at": generated,
        "config": cfg,
        "market_regimes": regimes,
        "count": len(summary),
        "errors": errors,
        "rows": summary,
    }

    (out_dir / "summary.json").write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            default=json_default,
            allow_nan=False,
        ),
        encoding="utf-8",
    )
    pd.DataFrame(summary).to_csv(
        out_dir / "summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    (out_dir / "errors.json").write_text(
        json.dumps(errors, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(
        f"[structure] complete: {len(summary)} symbols / "
        f"{len(errors)} errors"
    )
    if summary:
        print("[structure] top setups")
        for x in summary[:12]:
            ch = x.get("parallel_channel_label") or "-"
            cq = x.get("parallel_channel_quality")
            print(
                f"  {x['ticker']} {x['name']}: "
                f"{x['grade']} {x['score']:.1f} {x['setup']} "
                f"RR={x.get('rr1')} CHANNEL={ch} Q={cq}"
            )


if __name__ == "__main__":
    main()
