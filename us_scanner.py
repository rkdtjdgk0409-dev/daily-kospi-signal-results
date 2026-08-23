#!/usr/bin/env python3
"""S&P 500 + Nasdaq-100 technical alpha screener.

The indicator implementation is intentionally shared with scanner.py so the US
and Korea pages use the same model.  This module owns only the US universe,
membership history, benchmark-relative scoring, and output files.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup

from quant_risk import compute_risk_metrics, final_quant_score, model_position_size_pct, risk_quality_score, risk_snapshot

from scanner import (
    benchmark_snapshot,
    classify_regime,
    download_benchmark,
    download_prices,
    percentile_0_100,
    raw_features,
    risk_label,
    setup_grade,
    signal_state,
)


NY = ZoneInfo("America/New_York")
INDEX_SP500 = "S&P 500"
INDEX_NDX100 = "NASDAQ-100"
WIKI_SP500 = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
NASDAQ_API = "https://api.nasdaq.com/api/quote/list-type/nasdaq100"
EXPECTED_RANGES = {INDEX_SP500: (490, 515), INDEX_NDX100: (95, 110)}


def now_ny() -> datetime:
    return datetime.now(NY)


def clean_text(value: object) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split())


def yf_symbol(symbol: str) -> str:
    """Translate index notation (BRK.B) to Yahoo notation (BRK-B)."""
    return clean_text(symbol).upper().replace(".", "-")


def normalize_symbol(symbol: str) -> str:
    return clean_text(symbol).upper().replace("-", ".")


def _headers() -> dict[str, str]:
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
        "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }


def _table_rows(url: str, table_id: str | None = None) -> list[dict[str, str]]:
    response = requests.get(url, headers=_headers(), timeout=35)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", id=table_id) if table_id else None
    if table is None:
        candidates = soup.select("table.wikitable")
        table = next(
            (
                t
                for t in candidates
                if any(k in t.get_text(" ", strip=True).lower() for k in ("symbol", "ticker"))
            ),
            None,
        )
    if table is None:
        raise RuntimeError(f"No constituent table found at {url}")

    headers = [clean_text(x.get_text(" ", strip=True)) for x in table.select("tr th")]
    first_row = table.select_one("tr")
    if first_row:
        headers = [clean_text(x.get_text(" ", strip=True)) for x in first_row.select("th,td")]

    rows: list[dict[str, str]] = []
    for tr in table.select("tr")[1:]:
        cells = [clean_text(x.get_text(" ", strip=True)) for x in tr.select("th,td")]
        if len(cells) < 2:
            continue
        rows.append({headers[i]: cells[i] for i in range(min(len(headers), len(cells)))})
    return rows


def _first(row: dict[str, str], names: Iterable[str]) -> str:
    lowered = {clean_text(k).lower(): v for k, v in row.items()}
    for name in names:
        if name.lower() in lowered and clean_text(lowered[name.lower()]):
            return clean_text(lowered[name.lower()])
    return ""


def fetch_sp500() -> tuple[list[dict], str]:
    rows = _table_rows(WIKI_SP500, "constituents")
    out = []
    for row in rows:
        symbol = _first(row, ("Symbol", "Ticker"))
        if not symbol:
            continue
        out.append(
            {
                "ticker": normalize_symbol(symbol),
                "yf_ticker": yf_symbol(symbol),
                "name": _first(row, ("Security", "Company")) or normalize_symbol(symbol),
                "sector": _first(row, ("GICS Sector", "Sector")) or "Unknown",
            }
        )
    return dedupe(out), WIKI_SP500


def fetch_nasdaq100_official() -> tuple[list[dict], str]:
    headers = _headers()
    headers.update({"Accept": "application/json, text/plain, */*", "Referer": "https://www.nasdaq.com/"})
    response = requests.get(NASDAQ_API, headers=headers, timeout=35)
    response.raise_for_status()
    payload = response.json()
    data = (payload or {}).get("data") or {}
    rows = ((data.get("data") or {}).get("rows") or data.get("rows") or [])
    out = []
    for row in rows:
        symbol = clean_text(row.get("symbol") or row.get("Symbol"))
        if not symbol:
            continue
        out.append(
            {
                "ticker": normalize_symbol(symbol),
                "yf_ticker": yf_symbol(symbol),
                "name": clean_text(row.get("companyName") or row.get("name") or symbol),
                "sector": clean_text(row.get("sector") or "Unknown"),
            }
        )
    return dedupe(out), NASDAQ_API


def dedupe(rows: list[dict]) -> list[dict]:
    unique = {}
    for row in rows:
        ticker = normalize_symbol(row.get("ticker", ""))
        if ticker:
            unique[ticker] = {**row, "ticker": ticker, "yf_ticker": yf_symbol(row.get("yf_ticker") or ticker)}
    return sorted(unique.values(), key=lambda x: x["ticker"])


def validate(index_name: str, rows: list[dict]) -> None:
    low, high = EXPECTED_RANGES[index_name]
    if not low <= len(rows) <= high:
        raise RuntimeError(f"{index_name}: rejected suspicious constituent count {len(rows)} (expected {low}-{high})")
    if len({r["ticker"] for r in rows}) != len(rows):
        raise RuntimeError(f"{index_name}: duplicate symbols after normalization")


def load_state(path: Path) -> dict:
    if not path.exists():
        return {"schema_version": 1, "constituents": {}, "history": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data.get("constituents"), dict):
            raise ValueError("missing constituents")
        return data
    except Exception as exc:
        raise RuntimeError(f"Invalid universe state {path}: {exc}") from exc


def rows_from_state(state: dict, index_name: str) -> list[dict]:
    rows = state.get("constituents", {}).get(index_name, [])
    return dedupe(rows if isinstance(rows, list) else [])


def guarded_fetch(index_name: str, fetchers: list, previous: list[dict]) -> tuple[list[dict], str, list[str]]:
    errors: list[str] = []
    previous_symbols = {x["ticker"] for x in previous}
    for fetcher in fetchers:
        try:
            rows, source = fetcher()
            validate(index_name, rows)
            current_symbols = {x["ticker"] for x in rows}
            turnover = len(previous_symbols ^ current_symbols) if previous_symbols else 0
            if previous_symbols and turnover > 30:
                raise RuntimeError(f"safety guard rejected {turnover} simultaneous membership changes")
            return rows, source, errors
        except Exception as exc:
            errors.append(f"{fetcher.__name__}: {exc}")
    if previous:
        validate(index_name, previous)
        errors.append("all live sources failed; retained last validated snapshot")
        return previous, "saved snapshot fallback", errors
    raise RuntimeError(f"Unable to initialize {index_name}: {' | '.join(errors)}")


def change_event(index_name: str, previous: list[dict], current: list[dict], detected_at: str) -> dict | None:
    if not previous:
        return None
    old = {x["ticker"]: x for x in previous}
    new = {x["ticker"]: x for x in current}
    added = [new[s] for s in sorted(new.keys() - old.keys())]
    removed = [old[s] for s in sorted(old.keys() - new.keys())]
    if not added and not removed:
        return None
    return {"detected_at": detected_at, "index": index_name, "added": added, "removed": removed}


def build_universe(state_path: Path) -> tuple[pd.DataFrame, dict, dict]:
    state = load_state(state_path)
    detected_at = now_ny().isoformat(timespec="seconds")
    previous_sp = rows_from_state(state, INDEX_SP500)
    previous_ndx = rows_from_state(state, INDEX_NDX100)

    sp, sp_source, sp_errors = guarded_fetch(INDEX_SP500, [fetch_sp500], previous_sp)
    ndx, ndx_source, ndx_errors = guarded_fetch(INDEX_NDX100, [fetch_nasdaq100_official], previous_ndx)

    events = []
    for event in (
        change_event(INDEX_SP500, previous_sp, sp, detected_at),
        change_event(INDEX_NDX100, previous_ndx, ndx, detected_at),
    ):
        if event:
            events.append(event)

    persisted_sources = {
        INDEX_SP500: state.get("sources", {}).get(INDEX_SP500, sp_source)
        if sp_source == "saved snapshot fallback"
        else sp_source,
        INDEX_NDX100: state.get("sources", {}).get(INDEX_NDX100, ndx_source)
        if ndx_source == "saved snapshot fallback"
        else ndx_source,
    }
    new_state = {
        "schema_version": 1,
        "snapshot_at": detected_at,
        "sources": persisted_sources,
        "constituents": {INDEX_SP500: sp, INDEX_NDX100: ndx},
        "history": (state.get("history", []) + events)[-100:],
    }
    # Avoid timestamp-only commits: persist only initial state or actual membership/source changes.
    state_changed = not previous_sp or not previous_ndx or bool(events)
    if state_changed:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(new_state, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        new_state = state

    merged: dict[str, dict] = {}
    for index_name, rows in ((INDEX_SP500, sp), (INDEX_NDX100, ndx)):
        for row in rows:
            ticker = row["ticker"]
            item = merged.setdefault(ticker, {**row, "indices": []})
            item["indices"].append(index_name)
            if item.get("sector") in (None, "", "Unknown") and row.get("sector") not in (None, "", "Unknown"):
                item["sector"] = row["sector"]
            if item.get("name") == ticker and row.get("name") != ticker:
                item["name"] = row["name"]

    universe = pd.DataFrame(merged.values()).sort_values("ticker").reset_index(drop=True)
    universe["market"] = universe["indices"].map(lambda xs: " + ".join(xs))
    universe["in_sp500"] = universe["indices"].map(lambda xs: INDEX_SP500 in xs)
    universe["in_nasdaq100"] = universe["indices"].map(lambda xs: INDEX_NDX100 in xs)
    diagnostics = {
        "sources": {INDEX_SP500: sp_source, INDEX_NDX100: ndx_source},
        "source_errors": {INDEX_SP500: sp_errors, INDEX_NDX100: ndx_errors},
        "changes": events,
        "history": new_state.get("history", []),
        "counts": {INDEX_SP500: len(sp), INDEX_NDX100: len(ndx), "unique": len(universe)},
        "state_changed": state_changed,
    }
    return universe, new_state, diagnostics


def combined_regime(row: pd.Series) -> str:
    values = []
    if bool(row["in_sp500"]):
        values.append(row["regime_sp500"])
    if bool(row["in_nasdaq100"]):
        values.append(row["regime_nasdaq100"])
    if values and all(x == "RISK-ON" for x in values):
        return "RISK-ON"
    if values and all(x == "RISK-OFF" for x in values):
        return "RISK-OFF"
    return "NEUTRAL"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cci-period", type=int, default=9)
    parser.add_argument("--dmi-period", type=int, default=14)
    parser.add_argument("--supertrend-period", type=int, default=10)
    parser.add_argument("--supertrend-factor", type=float, default=3.0)
    parser.add_argument("--adx-threshold", type=float, default=20.0)
    parser.add_argument("--confirmed-alpha-threshold", type=float, default=75.0)
    parser.add_argument("--fresh-alpha-threshold", type=float, default=60.0)
    parser.add_argument("--early-alpha-threshold", type=float, default=50.0)
    parser.add_argument("--min-avg20-dollar-volume", type=float, default=10_000_000.0)
    parser.add_argument("--output-dir", default="us_results")
    parser.add_argument("--state-file", default="state/us_universe.json")
    args = parser.parse_args()

    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    universe, _, universe_info = build_universe(Path(args.state_file))
    universe.assign(indices=universe["indices"].map(" | ".join)).to_csv(
        outdir / "universe.csv", index=False, encoding="utf-8-sig"
    )

    prices = download_prices(universe["yf_ticker"].tolist(), lookback_days=360)
    benchmark_prices = {
        INDEX_SP500: download_benchmark("^GSPC", lookback_days=360),
        INDEX_NDX100: download_benchmark("^NDX", lookback_days=360),
    }
    meta = universe.set_index("yf_ticker").to_dict("index")
    rows = []
    for symbol, frame in prices.items():
        feat = raw_features(
            frame,
            args.cci_period,
            args.dmi_period,
            args.supertrend_period,
            args.supertrend_factor,
        )
        if feat is None or feat["avg20_trading_value"] < args.min_avg20_dollar_volume:
            continue
        m = meta[symbol]
        primary_benchmark = benchmark_prices[INDEX_SP500] if bool(m.get("in_sp500")) else benchmark_prices[INDEX_NDX100]
        risk_metrics = compute_risk_metrics(frame, primary_benchmark)
        rows.append(
            {
                "ticker": m["ticker"],
                "name": m["name"],
                "sector": m.get("sector", "Unknown"),
                "market": m["market"],
                "indices": " | ".join(m["indices"]),
                "in_sp500": bool(m["in_sp500"]),
                "in_nasdaq100": bool(m["in_nasdaq100"]),
                "yf_ticker": symbol,
                **feat,
                **risk_metrics,
            }
        )
    if not rows:
        raise RuntimeError("No US symbols could be scored")

    scored = pd.DataFrame(rows)
    counts = scored["signal_date"].value_counts().sort_index()
    latest_date = str(counts.index.max())
    dominant_date = str(counts.idxmax())
    minimum = max(1, int(math.ceil(len(scored) * 0.70)))
    selected_date = latest_date if int(counts.loc[latest_date]) >= minimum else dominant_date
    before_alignment = len(scored)
    scored = scored[scored["signal_date"] == selected_date].copy().reset_index(drop=True)
    if scored.empty:
        raise RuntimeError("No US symbols remain after close-date alignment")

    benchmark = {}
    cutoff = pd.Timestamp(selected_date)
    for index_name, frame in benchmark_prices.items():
        aligned = frame[frame.index <= cutoff].copy() if frame is not None and not frame.empty else pd.DataFrame()
        benchmark[index_name] = benchmark_snapshot(aligned)

    for horizon in (20, 60):
        scored[f"benchmark_ret{horizon}_sp500"] = benchmark[INDEX_SP500][f"ret{horizon}"]
        scored[f"benchmark_ret{horizon}_nasdaq100"] = benchmark[INDEX_NDX100][f"ret{horizon}"]
        excess_sp = scored[f"ret{horizon}"] - scored[f"benchmark_ret{horizon}_sp500"]
        excess_ndx = scored[f"ret{horizon}"] - scored[f"benchmark_ret{horizon}_nasdaq100"]
        memberships = scored[["in_sp500", "in_nasdaq100"]].sum(axis=1).clip(lower=1)
        scored[f"rs{horizon}_excess_pct"] = (
            (excess_sp * scored["in_sp500"].astype(int) + excess_ndx * scored["in_nasdaq100"].astype(int))
            / memberships
            * 100.0
        )
        scored[f"rs{horizon}_percentile"] = percentile_0_100(scored[f"rs{horizon}_excess_pct"])
    scored["rs_score"] = 0.60 * scored["rs20_percentile"] + 0.40 * scored["rs60_percentile"]

    scored["atr_risk_pctile"] = percentile_0_100(scored["atr_pct"])
    scored["vol_risk_pctile"] = percentile_0_100(scored["vol60_ann_pct"])
    scored["risk_quality_score"] = scored.apply(lambda r: risk_quality_score(r), axis=1)
    scored["risk_score"] = (100.0 - scored["risk_quality_score"]).clip(0, 100)
    scored["risk_level"] = scored["risk_score"].map(risk_label)

    regimes = {}
    for index_name, flag in ((INDEX_SP500, "in_sp500"), (INDEX_NDX100, "in_nasdaq100")):
        group = scored[scored[flag]]
        breadth20 = float(group["above_ma20"].mean()) if not group.empty else 0.0
        breadth60 = float(group["above_ma60"].mean()) if not group.empty else 0.0
        label, score = classify_regime(benchmark[index_name], breadth20, breadth60)
        regimes[index_name] = {
            "regime": label,
            "score": score,
            "breadth20": breadth20,
            "breadth60": breadth60,
            "benchmark_ret20_pct": benchmark[index_name]["ret20"] * 100.0,
            "benchmark_ret60_pct": benchmark[index_name]["ret60"] * 100.0,
            "signal_date": benchmark[index_name].get("signal_date"),
        }
    scored["regime_sp500"] = regimes[INDEX_SP500]["regime"]
    scored["regime_nasdaq100"] = regimes[INDEX_NDX100]["regime"]
    scored["regime"] = scored.apply(combined_regime, axis=1)
    scored["regime_score"] = 0

    scored["alpha_score"] = (
        0.30 * scored["trend_score"]
        + 0.25 * scored["momentum_score"]
        + 0.20 * scored["flow_score"]
        + 0.25 * scored["rs_score"]
    ).clip(0, 100)
    scored["final_quant_score"] = scored.apply(
        lambda r: final_quant_score(r.get("alpha_score"), r.get("risk_quality_score"), alpha_weight=0.70), axis=1
    )
    scored["dmi_positive"] = scored["plus_di"] > scored["minus_di"]
    scored["dmi_bull"] = scored["dmi_positive"] & (scored["adx"] >= args.adx_threshold)

    confirmed = (
        (scored["cci_cross_age"] <= 1)
        & (scored["cci"] > 0)
        & scored["dmi_bull"]
        & scored["supertrend_good"]
        & (scored["entry_score"] >= 70)
        & (scored["flow_score"] >= 50)
        & (scored["alpha_score"] >= args.confirmed_alpha_threshold)
    )
    fresh = (
        (scored["cci_cross_age"] <= 3)
        & (scored["cci"] > 0)
        & scored["dmi_positive"]
        & (scored["entry_score"] >= 60)
        & (scored["flow_score"] >= 40)
        & (scored["alpha_score"] >= args.fresh_alpha_threshold)
    )
    early = (
        (scored["cci"] > -30)
        & (scored["cci"] <= 0)
        & (scored["cci_delta3"] >= 25)
        & (scored["dmi_ratio"] >= 0.85)
        & (scored["flow_score"] >= 40)
        & (scored["rs_score"] >= 50)
        & (scored["entry_score"] >= 45)
        & (scored["alpha_score"] >= args.early_alpha_threshold)
    )
    scored["confirmed_buy"] = confirmed
    scored["fresh_buy"] = fresh & ~confirmed
    scored["early_setup"] = early & ~confirmed & ~fresh
    scored["actionable_buy"] = scored["confirmed_buy"] | scored["fresh_buy"]
    scored["signal_tier"] = "RANK"
    scored.loc[scored["early_setup"], "signal_tier"] = "EARLY"
    scored.loc[scored["fresh_buy"], "signal_tier"] = "FRESH"
    scored.loc[scored["confirmed_buy"], "signal_tier"] = "CONFIRMED"
    scored["active_trend"] = (scored["cci"] > 0) & scored["dmi_bull"] & scored["supertrend_good"]
    scored["signal_state"] = scored["alpha_score"].map(signal_state)
    scored["setup_grade"] = scored.apply(setup_grade, axis=1)

    scored["model_weight_pct"] = scored.apply(
        lambda r: model_position_size_pct(
            alpha_score=r.get("alpha_score"),
            risk_quality=r.get("risk_quality_score"),
            vol60_ann_pct=r.get("vol60_ann_pct"),
            signal_tier=r.get("signal_tier", "RANK"),
            regime=r.get("regime", "NEUTRAL"),
        ),
        axis=1,
    )

    ranked = scored.sort_values(["final_quant_score", "alpha_score"], ascending=False).reset_index(drop=True)
    ranked["alpha_rank_all"] = np.arange(1, len(ranked) + 1)
    ranked["rank_sp500"] = np.nan
    ranked["rank_nasdaq100"] = np.nan
    for flag, column in (("in_sp500", "rank_sp500"), ("in_nasdaq100", "rank_nasdaq100")):
        members = ranked[ranked[flag]].sort_values(["final_quant_score", "alpha_score"], ascending=False).index
        ranked.loc[members, column] = np.arange(1, len(members) + 1)

    tier_order = pd.Categorical(
        ranked["signal_tier"], categories=["CONFIRMED", "FRESH", "EARLY", "RANK"], ordered=True
    )
    scored = ranked.assign(_tier=tier_order).sort_values(["_tier", "final_quant_score", "alpha_score"], ascending=[True, False, False]).drop(columns="_tier")
    actionable = scored[scored["actionable_buy"]].copy()
    confirmed_df = scored[scored["confirmed_buy"]].copy()
    fresh_df = scored[scored["fresh_buy"]].copy()
    early_df = scored[scored["early_setup"]].copy()
    active_df = scored[scored["active_trend"]].copy()

    outputs = {
        "latest_all_scored.csv": scored,
        "latest_top_alpha.csv": ranked,  # backward-compatible alias
        "latest_top_quant.csv": ranked,
        "latest_buy_signals.csv": actionable,
        "latest_confirmed_buy.csv": confirmed_df,
        "latest_fresh_buy.csv": fresh_df,
        "latest_early_setups.csv": early_df,
        "latest_active_trends.csv": active_df,
    }
    for filename, frame in outputs.items():
        frame.to_csv(outdir / filename, index=False, encoding="utf-8-sig")

    summary = {
        "model_version": "US_TECH_ALPHA_RISK_V2_0",
        "generated_at": now_ny().isoformat(timespec="seconds"),
        "generated_timezone": "America/New_York",
        "price_basis": "US regular-session adjusted daily OHLCV via Yahoo Finance",
        "auto_refresh_schedule": "Weekdays 22:05 UTC (17:05 ET standard time; 18:05 ET daylight time)",
        "latest_signal_date": selected_date,
        "symbols_scored": int(len(scored)),
        "universe_counts": universe_info["counts"],
        "universe_sources": universe_info["sources"],
        "universe_source_errors": universe_info["source_errors"],
        "constituent_changes": universe_info["changes"],
        "constituent_history": universe_info["history"],
        "actionable_buy_count": int(len(actionable)),
        "confirmed_buy_count": int(len(confirmed_df)),
        "fresh_buy_count": int(len(fresh_df)),
        "early_setup_count": int(len(early_df)),
        "active_trend_count": int(len(active_df)),
        "close_date_alignment": {
            "selected_date": selected_date,
            "symbols_before_alignment": int(before_alignment),
            "symbols_after_alignment": int(len(scored)),
            "coverage_pct": round(100 * len(scored) / max(before_alignment, 1), 1),
        },
        "regimes": regimes,
        "parameters": vars(args),
        "weights": {"trend": 30, "momentum": 25, "flow": 20, "relative_strength": 25},
        "quant_weights": {"alpha": 70, "risk_quality": 30},
        "risk_model": {
            "volatility": "60D annualized",
            "beta": "120D vs primary broad index",
            "max_drawdown": "120D",
            "historical_var": "95% / 60D",
            "expected_shortfall": "95% / 60D",
            "interpretation": "risk_score: higher=riskier; risk_quality_score: higher=safer",
        },
        "risk_snapshot": risk_snapshot(scored),
    }
    (outdir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
