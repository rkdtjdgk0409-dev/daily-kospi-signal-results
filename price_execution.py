#!/usr/bin/env python3
from __future__ import annotations

import math
from typing import Any, Dict, Optional, Tuple

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


def _valid_zone(z: Any) -> Optional[Tuple[float, float]]:
    if not isinstance(z, dict):
        return None
    lo = _fnum(z.get("low"))
    hi = _fnum(z.get("high"))
    if lo is None or hi is None or lo <= 0 or hi <= 0:
        return None
    lo, hi = min(lo, hi), max(lo, hi)
    if hi <= lo:
        return None
    return float(lo), float(hi)


def _zone_distance(price: float, zone: Tuple[float, float]) -> float:
    lo, hi = zone
    if lo <= price <= hi:
        return 0.0
    if price < lo:
        return lo - price
    return price - hi


def build_execution_plan(
    df: pd.DataFrame,
    analysis: Dict[str, Any],
    cfg: Dict[str, Any],
) -> Dict[str, Any]:
    """Create actionable *technical reference* entry/stop levels from the price-structure evidence.

    This is intentionally separate from the alpha/risk ranking layer.  It answers:
    - where a pullback entry is structurally attractive,
    - where a breakout entry is confirmed,
    - where the long thesis is invalidated,
    - whether the current price is buyable, chasey, or should be avoided.

    It is deterministic and only uses already-computed support/wave/channel/ATR evidence.
    """
    clean = df.copy().dropna(subset=["Open", "High", "Low", "Close"]).sort_index()
    if clean.empty:
        return {}

    price = _fnum(analysis.get("price"), float(clean["Close"].iloc[-1])) or float(clean["Close"].iloc[-1])
    atr = _fnum(analysis.get("atr"), max(price * 0.02, EPS)) or max(price * 0.02, EPS)
    atr = max(atr, price * 0.001, EPS)

    wave = analysis.get("wave") or {}
    scenario = wave.get("scenario") or {}
    wave_zone = _valid_zone(wave.get("entry_zone"))
    support = analysis.get("support") or {}
    support_zone = _valid_zone(support)
    channel = analysis.get("parallel_channel") or {}
    trade = analysis.get("trade") or {}
    bq = analysis.get("breakout_quality") or {}
    direction = str(analysis.get("direction", "NEUTRAL"))
    stage = str(wave.get("stage") or analysis.get("setup") or "NEUTRAL")

    # ----- Pullback buy zone -----
    # Prefer an Elliott/Fibonacci entry zone.  If it overlaps a high-quality support
    # zone, use the overlap as the highest-confluence sub-zone.
    buy_zone: Optional[Tuple[float, float]] = None
    buy_source = ""
    reasons = []

    if wave_zone and support_zone:
        overlap_lo = max(wave_zone[0], support_zone[0])
        overlap_hi = min(wave_zone[1], support_zone[1])
        if overlap_lo < overlap_hi:
            buy_zone = (overlap_lo, overlap_hi)
            buy_source = "파동 눌림 + 지지 매물대 합류"
            reasons.append("파동 되돌림 구간과 지지/매물대가 겹치는 가격대")
        else:
            # If they do not overlap, take the closer of the two but only when it is
            # within a practical distance from current price.
            candidates = [(wave_zone, "파동 눌림 구간"), (support_zone, "지지 매물대")]
            candidates.sort(key=lambda x: _zone_distance(price, x[0]))
            if _zone_distance(price, candidates[0][0]) <= 3.2 * atr:
                buy_zone, buy_source = candidates[0]
    elif wave_zone:
        if _zone_distance(price, wave_zone) <= 3.2 * atr:
            buy_zone, buy_source = wave_zone, "파동 눌림 구간"
    elif support_zone:
        if _zone_distance(price, support_zone) <= 3.2 * atr:
            buy_zone, buy_source = support_zone, "지지 매물대"

    # Ascending-channel lower boundary can refine a pullback zone or provide a fallback.
    ch_lower = _fnum(channel.get("current_lower"))
    if channel.get("direction") == "ASCENDING" and ch_lower and ch_lower > 0:
        ch_zone = (ch_lower - 0.20 * atr, ch_lower + 0.28 * atr)
        if buy_zone:
            olo, ohi = max(buy_zone[0], ch_zone[0]), min(buy_zone[1], ch_zone[1])
            if olo < ohi:
                buy_zone = (olo, ohi)
                buy_source += " + 상승채널 하단"
                reasons.append("상승 평행채널 하단과 가격 지지가 합류")
        elif abs(price - ch_lower) <= 2.6 * atr:
            buy_zone, buy_source = ch_zone, "상승채널 하단 리테스트"
            reasons.append("상승 평행채널 하단 리테스트 가격대")

    # Do not invent a long buy zone when structure is explicitly bearish.
    if direction == "BEARISH" or stage == "STRUCTURE_RISK":
        buy_zone = None
        buy_source = ""

    # ----- Breakout buy trigger -----
    confirm = _fnum(scenario.get("confirm_price"))
    resistance = analysis.get("resistance") or {}
    res_hi = _fnum(resistance.get("high"))
    ch_upper = _fnum(channel.get("current_upper"))

    breakout = confirm
    breakout_source = "파동 확인 가격" if confirm else ""
    if breakout is None and res_hi and res_hi > 0:
        breakout = res_hi + float(cfg.get("breakout_buffer_atr", 0.25)) * atr
        breakout_source = "저항 매물대 상단 + ATR 버퍼"
    if breakout is None and channel.get("direction") == "DESCENDING" and ch_upper and ch_upper > 0:
        breakout = ch_upper + 0.15 * atr
        breakout_source = "하락채널 상단 돌파"

    if breakout and breakout <= 0:
        breakout = None

    # ----- Preferred entry/status -----
    preferred_low = preferred_high = None
    preferred_type = "WAIT"
    status = "대기"
    status_detail = "구조가 명확해질 때까지 신규 진입을 보류합니다."

    if direction == "BEARISH" or stage == "STRUCTURE_RISK":
        status = "신규 매수 보류"
        preferred_type = "NO_ENTRY"
        status_detail = "핵심 지지/상승 구조가 훼손된 상태라 매수 가격을 제시하지 않습니다."
    elif buy_zone and buy_zone[0] <= price <= buy_zone[1]:
        preferred_low, preferred_high = buy_zone
        preferred_type = "PULLBACK"
        status = "눌림 매수 구간"
        status_detail = "현재가가 지지·파동 합류 매수 구간 안에 있습니다. 분할 접근이 우선입니다."
    elif buy_zone and price < buy_zone[0]:
        preferred_low, preferred_high = buy_zone
        preferred_type = "RECLAIM"
        status = "회복 확인 대기"
        status_detail = "현재가가 매수 구간 아래에 있어, 가격대 회복 확인 전에는 진입을 서두르지 않습니다."
    elif breakout and price < breakout:
        # Pullback is still preferred if it is close; otherwise wait for confirmed breakout.
        if buy_zone and _zone_distance(price, buy_zone) <= 1.8 * atr:
            preferred_low, preferred_high = buy_zone
            preferred_type = "PULLBACK"
            status = "눌림 매수 대기"
            status_detail = "지지 구간 눌림 또는 돌파 확인 중 더 유리한 쪽을 기다립니다."
        else:
            preferred_low = preferred_high = breakout
            preferred_type = "BREAKOUT"
            status = "돌파 매수 대기"
            status_detail = "확인 가격을 종가 기준으로 넘어서는지 확인한 뒤 진입하는 방식입니다."
    elif breakout and price >= breakout:
        dist = (price - breakout) / atr
        q = _fnum(bq.get("score"), 50.0) or 50.0
        rvol = _fnum(bq.get("rvol"), 1.0) or 1.0
        if dist <= 0.45 and q >= 55 and rvol >= 0.9:
            preferred_low = breakout - 0.12 * atr
            preferred_high = breakout + 0.22 * atr
            preferred_type = "BREAKOUT_RETEST"
            status = "돌파 확인 매수"
            status_detail = "돌파 가격과 가깝고 돌파 품질이 양호해, 돌파선 리테스트를 매수 기준으로 사용합니다."
        else:
            preferred_low = breakout - 0.25 * atr
            preferred_high = breakout + 0.10 * atr
            preferred_type = "RETEST_ONLY"
            status = "추격 금지 · 리테스트 대기"
            status_detail = "확인 가격에서 이미 멀어진 상태라 추격보다 돌파선 재확인을 기다립니다."
    elif buy_zone:
        preferred_low, preferred_high = buy_zone
        preferred_type = "PULLBACK"
        status = "눌림 매수 대기"
        status_detail = "지지/파동 구간 접근 시 분할 진입을 검토합니다."

    # ----- Stop / invalidation -----
    ref_entry = price
    if preferred_low is not None and preferred_high is not None:
        ref_entry = (preferred_low + preferred_high) / 2.0
    elif breakout:
        ref_entry = breakout

    stop_candidates = []
    trade_stop = _fnum(trade.get("stop"))
    invalid = _fnum(scenario.get("invalidation_price"))
    support_low = _fnum(support.get("low"))

    # Only structural levels below the reference entry are eligible.
    if trade_stop and trade_stop < ref_entry:
        stop_candidates.append((trade_stop, "지지/최근 스윙 기반 기존 구조 손절"))
    if invalid and invalid < ref_entry:
        stop_candidates.append((invalid, "엘리어트/파동 시나리오 무효화"))
    if support_low and support_low < ref_entry:
        stop_candidates.append((support_low - 0.22 * atr, "핵심 지지 매물대 하단 이탈"))
    if channel.get("direction") == "ASCENDING" and ch_lower and ch_lower < ref_entry:
        stop_candidates.append((ch_lower - 0.28 * atr, "상승채널 하단 이탈"))
    if buy_zone:
        stop_candidates.append((buy_zone[0] - 0.30 * atr, "매수 합류구간 하단 이탈"))

    # The nearest *valid* structural invalidation is used, but never tighter than
    # 0.70 ATR from the reference entry to avoid noise stops.
    stop = None
    stop_reason = ""
    valid = [(p, r) for p, r in stop_candidates if p > 0 and p < ref_entry]
    if valid:
        p, r = max(valid, key=lambda x: x[0])
        stop = min(p, ref_entry - 0.70 * atr)
        stop_reason = r
    elif direction != "BEARISH":
        stop = ref_entry - 1.15 * atr
        stop_reason = "구조 기준이 부족해 ATR 기반 방어선 사용"

    if stop is not None and stop <= 0:
        stop = None

    # ----- Risk / R:R using existing take-profit targets -----
    target1 = _fnum(scenario.get("target1"), _fnum(trade.get("target1")))
    target2 = _fnum(scenario.get("target2"), _fnum(trade.get("target2")))
    risk_pct = None
    rr1 = rr2 = None
    if stop is not None and ref_entry > stop:
        risk = ref_entry - stop
        risk_pct = risk / ref_entry * 100.0
        if target1 and target1 > ref_entry:
            rr1 = (target1 - ref_entry) / risk
        if target2 and target2 > ref_entry:
            rr2 = (target2 - ref_entry) / risk

    if buy_zone and not reasons:
        reasons.append(f"{buy_source}을 1차 매수 후보로 사용")
    if breakout:
        reasons.append(f"{breakout_source}을 돌파 매수 확인선으로 사용")
    if stop is not None:
        reasons.append(f"손절은 {stop_reason} 기준")

    # Keep the card concise.
    reasons = reasons[:3]

    # Relative distances are useful for deciding whether to wait or chase.
    to_buy_pct = None
    if buy_zone:
        zone_mid = (buy_zone[0] + buy_zone[1]) / 2.0
        to_buy_pct = (zone_mid / price - 1.0) * 100.0
    to_breakout_pct = (breakout / price - 1.0) * 100.0 if breakout else None

    plan = {
        "status": status,
        "status_detail": status_detail,
        "preferred_type": preferred_type,
        "preferred_low": round(preferred_low, 4) if preferred_low is not None else None,
        "preferred_high": round(preferred_high, 4) if preferred_high is not None else None,
        "buy_zone_low": round(buy_zone[0], 4) if buy_zone else None,
        "buy_zone_high": round(buy_zone[1], 4) if buy_zone else None,
        "buy_zone_source": buy_source or None,
        "breakout_buy": round(breakout, 4) if breakout is not None else None,
        "breakout_source": breakout_source or None,
        "stop": round(stop, 4) if stop is not None else None,
        "stop_reason": stop_reason or None,
        "risk_pct": round(risk_pct, 2) if risk_pct is not None else None,
        "rr1": round(rr1, 2) if rr1 is not None else None,
        "rr2": round(rr2, 2) if rr2 is not None else None,
        "target1": round(target1, 4) if target1 is not None else None,
        "target2": round(target2, 4) if target2 is not None else None,
        "to_buy_pct": round(to_buy_pct, 2) if to_buy_pct is not None else None,
        "to_breakout_pct": round(to_breakout_pct, 2) if to_breakout_pct is not None else None,
        "reasons": reasons,
    }

    analysis["execution_plan"] = plan
    chart = analysis.setdefault("chart", {})
    chart["execution_plan"] = plan
    return analysis
