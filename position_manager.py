#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

KST = ZoneInfo("Asia/Seoul")


def n(v, default=0.0):
    try:
        x = float(v)
        return x if np.isfinite(x) else default
    except Exception:
        return default


def b(v):
    if isinstance(v, str):
        return v.strip().lower() in {"true", "1", "yes", "good"}
    return bool(v)


def load_state(path: Path) -> dict:
    if not path.exists():
        return {"version": "3.0", "positions": {}, "closed": []}
    try:
        x = json.loads(path.read_text(encoding="utf-8"))
        x.setdefault("version", "3.0")
        x.setdefault("positions", {})
        x.setdefault("closed", [])
        return x
    except Exception:
        return {"version": "3.0", "positions": {}, "closed": []}


def calc_exit_risk(r):
    st_good = b(r.get("supertrend_good", str(r.get("supertrend_status", "")).upper() == "GOOD"))
    bear_age = int(n(r.get("supertrend_bear_flip_age", 999), 999))
    pdi, mdi = n(r.get("plus_di")), n(r.get("minus_di"))
    adx, adx_d = n(r.get("adx")), n(r.get("adx_delta3"))
    cci, cci_d = n(r.get("cci")), n(r.get("cci_delta3"))
    alpha = n(r.get("alpha_score"), 50)
    regime = str(r.get("regime", "NEUTRAL")).upper()

    st = 30 if (not st_good and bear_age <= 1) else 25 if not st_good else 0

    if mdi > pdi:
        dmi = min(20.0, 12.0 + (mdi / max(pdi, 1e-9) - 1.0) * 12.0)
    elif pdi - mdi < 3:
        dmi = 7.0
    else:
        dmi = 0.0

    adx_r = 15 if adx_d <= -8 else 11 if adx_d <= -4 else 6 if adx_d < 0 else 5 if adx < 18 else 0
    cci_r = 10 if cci < -50 else 8 if cci < 0 else 7 if cci_d <= -80 else 4 if cci_d <= -40 else 0
    alpha_r = 15 if alpha < 40 else 11 if alpha < 50 else 7 if alpha < 60 else 3 if alpha < 70 else 0
    regime_r = {"RISK-OFF": 10, "NEUTRAL": 4, "RISK-ON": 0}.get(regime, 4)

    total = min(100.0, st + dmi + adx_r + cci_r + alpha_r + regime_r)
    return {
        "exit_risk": round(total, 1),
        "exit_st_risk": round(st, 1),
        "exit_dmi_risk": round(dmi, 1),
        "exit_adx_risk": round(adx_r, 1),
        "exit_cci_risk": round(cci_r, 1),
        "exit_alpha_risk": round(alpha_r, 1),
        "exit_regime_risk": round(regime_r, 1),
    }


def stop_levels(r, entry, highest):
    close = n(r.get("close"))
    atr_pct = max(n(r.get("atr_pct"), 2.0), 0.3)
    st = n(r.get("supertrend"))

    initial = entry * (1 - max(2.2 * atr_pct, 4.0) / 100)
    atr_trail = highest * (1 - max(2.8 * atr_pct, 5.0) / 100)

    trail = max(initial, atr_trail)
    if 0 < st < close:
        trail = max(trail, st)

    # Today close itself must not create an impossible stop above close.
    trail = min(trail, close * 0.999)
    return round(initial, 2), round(trail, 2)


def classify(r, pnl, risk, trail):
    close = n(r.get("close"))
    st_good = b(r.get("supertrend_good", str(r.get("supertrend_status", "")).upper() == "GOOD"))
    pdi, mdi = n(r.get("plus_di")), n(r.get("minus_di"))
    alpha = n(r.get("alpha_score"), 50)
    cci, cci_d = n(r.get("cci")), n(r.get("cci_delta3"))

    if close <= trail:
        return "STOP", "종가가 변동성 조정 Trailing Stop 이하"

    if risk >= 75 or ((not st_good) and mdi > pdi and alpha < 55):
        return "EXIT", "추세 반전 + DMI/Alpha 약화가 중첩"

    if pnl >= 6 and (risk >= 55 or (cci >= 140 and cci_d < 0) or not st_good):
        return "TAKE PROFIT", "수익 구간에서 추세 둔화: 25~50% 분할익절 후보"

    if risk >= 45:
        return "WATCH", "추세 약화 신호 증가: 추가매수보다 방어 우선"

    if risk < 20 and st_good and pdi > mdi and alpha >= 70:
        return "STRONG HOLD", "상승 추세·DMI·Alpha가 동시에 양호"

    return "HOLD", "핵심 추세 유지: Trailing Stop 기준 보유"


def is_confirmed(r):
    return b(r.get("confirmed_buy", False)) or str(r.get("signal_tier", "")).upper() == "CONFIRMED"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="results/latest_all_scored.csv")
    ap.add_argument("--state", default="state/position_state.json")
    ap.add_argument("--output", default="results/latest_position_management.csv")
    a = ap.parse_args()

    input_path = Path(a.input)
    state_path = Path(a.state)
    output_path = Path(a.output)

    df = pd.read_csv(input_path)
    df["ticker"] = df["ticker"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(6)

    state = load_state(state_path)
    positions = state["positions"]
    closed = state["closed"]
    rows = {r["ticker"]: r for _, r in df.iterrows()}

    # Confirmed Buy가 처음 등장한 날의 종가를 가상 진입가로 기록.
    for ticker, r in rows.items():
        if ticker not in positions and is_confirmed(r):
            px = n(r.get("close"))
            positions[ticker] = {
                "ticker": ticker,
                "name": str(r.get("name", ticker)),
                "market": str(r.get("market", "")),
                "entry_date": str(r.get("signal_date", "")),
                "entry_price": round(px, 2),
                "highest_close": round(px, 2),
                "tp1_done": False,
            }

    out = []
    for ticker in list(positions):
        if ticker not in rows:
            # Current universe/data failure alone does not auto-close.
            continue

        r = rows[ticker]
        p = positions[ticker]
        close = n(r.get("close"))
        entry = max(n(p.get("entry_price")), 1e-9)
        highest = max(n(p.get("highest_close"), entry), close)
        p["highest_close"] = round(highest, 2)

        pnl = (close / entry - 1) * 100
        peak_gain = (highest / entry - 1) * 100
        drawdown = (close / highest - 1) * 100 if highest > 0 else 0.0

        initial_stop, trailing_stop = stop_levels(r, entry, highest)
        er = calc_exit_risk(r)
        status, reason = classify(r, pnl, er["exit_risk"], trailing_stop)

        if status == "TAKE PROFIT" and not p.get("tp1_done", False):
            p["tp1_done"] = True
            p["tp1_date"] = str(r.get("signal_date", ""))

        rec = {
            "ticker": ticker,
            "name": p.get("name"),
            "market": p.get("market"),
            "entry_date": p.get("entry_date"),
            "entry_price": round(entry, 2),
            "close": round(close, 2),
            "pnl_pct": round(pnl, 2),
            "highest_close": round(highest, 2),
            "peak_gain_pct": round(peak_gain, 2),
            "drawdown_from_peak_pct": round(drawdown, 2),
            "position_status": status,
            "position_reason": reason,
            "initial_stop": initial_stop,
            "trailing_stop": trailing_stop,
            "tp1_done": bool(p.get("tp1_done", False)),
            **er,
            "alpha_score": round(n(r.get("alpha_score")), 1),
            "entry_score": round(n(r.get("entry_score")), 1),
            "cci": round(n(r.get("cci")), 1),
            "cci_delta3": round(n(r.get("cci_delta3")), 1),
            "plus_di": round(n(r.get("plus_di")), 1),
            "minus_di": round(n(r.get("minus_di")), 1),
            "adx": round(n(r.get("adx")), 1),
            "adx_delta3": round(n(r.get("adx_delta3")), 1),
            "supertrend_status": str(r.get("supertrend_status", "")),
            "regime": str(r.get("regime", "")),
        }
        out.append(rec)

        p["last_status"] = status
        p["last_exit_risk"] = er["exit_risk"]
        p["last_close"] = round(close, 2)
        p["trailing_stop"] = trailing_stop
        p["updated_date"] = str(r.get("signal_date", ""))

        # Exit/Stop history is saved; position removed for next run.
        if status in {"EXIT", "STOP"}:
            closed.append({
                **p,
                "exit_date": str(r.get("signal_date", "")),
                "exit_price": round(close, 2),
                "exit_status": status,
                "realized_return_pct": round(pnl, 2),
                "exit_reason": reason,
            })
            del positions[ticker]

    odf = pd.DataFrame(out)
    if not odf.empty:
        order = {"STOP": 0, "EXIT": 1, "TAKE PROFIT": 2, "WATCH": 3, "HOLD": 4, "STRONG HOLD": 5}
        odf["_ord"] = odf["position_status"].map(order).fillna(99)
        odf = odf.sort_values(["_ord", "exit_risk"], ascending=[True, False]).drop(columns="_ord")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    odf.to_csv(output_path, index=False, encoding="utf-8-sig")

    state["updated_at"] = datetime.now(KST).isoformat(timespec="seconds")
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    print("[position] rows:", len(odf))
    if not odf.empty:
        print("[position] status:", odf["position_status"].value_counts().to_dict())


if __name__ == "__main__":
    main()
