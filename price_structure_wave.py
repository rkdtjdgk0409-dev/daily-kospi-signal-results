#!/usr/bin/env python3
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from price_structure_engine import atr, confirmed_pivots, clamp, fnum

EPS = 1e-12


def _fmt_point(kind: str, p: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "kind": kind,
        "x": int(p["x"]),
        "date": p.get("date"),
        "price": float(p["price"]),
    }


def _alternating_swings(
    highs: Sequence[Dict[str, Any]],
    lows: Sequence[Dict[str, Any]],
    max_points: int = 18,
) -> List[Dict[str, Any]]:
    """Merge confirmed pivots and keep the most extreme pivot when equal types repeat."""
    raw = [_fmt_point("H", p) for p in highs] + [_fmt_point("L", p) for p in lows]
    raw.sort(key=lambda p: (p["x"], 0 if p["kind"] == "L" else 1))
    out: List[Dict[str, Any]] = []
    for p in raw:
        if not out:
            out.append(p)
            continue
        prev = out[-1]
        if p["x"] == prev["x"]:
            # Rare outside bar: keep the pivot that extends farther from the prior swing.
            if len(out) >= 2:
                anchor = out[-2]["price"]
                if abs(p["price"] - anchor) > abs(prev["price"] - anchor):
                    out[-1] = p
            continue
        if p["kind"] == prev["kind"]:
            better = p["price"] > prev["price"] if p["kind"] == "H" else p["price"] < prev["price"]
            if better:
                out[-1] = p
        else:
            out.append(p)
    return out[-max_points:]


def _point_age(n: int, p: Dict[str, Any]) -> int:
    return max(0, n - 1 - int(p["x"]))


def _bull_lhl_candidates(swings: Sequence[Dict[str, Any]], n: int) -> List[Tuple[float, Dict[str, Any], Dict[str, Any], Dict[str, Any]]]:
    """Bullish 0-1-2 candidates: low -> high -> higher low."""
    cands = []
    for i in range(len(swings) - 2):
        p0, p1, p2 = swings[i : i + 3]
        if [p0["kind"], p1["kind"], p2["kind"]] != ["L", "H", "L"]:
            continue
        impulse = p1["price"] - p0["price"]
        if impulse <= EPS or p2["price"] <= p0["price"]:
            continue
        retr = (p1["price"] - p2["price"]) / impulse
        if not (0.18 <= retr <= 0.88):
            continue
        age = _point_age(n, p2)
        if age > 100:
            continue
        retr_score = 1.0 - min(abs(retr - 0.55) / 0.45, 1.0)
        recency = 1.0 - min(age / 100.0, 1.0)
        duration = min((p2["x"] - p0["x"]) / 55.0, 1.0)
        score = retr_score * 0.45 + recency * 0.40 + duration * 0.15
        cands.append((score, p0, p1, p2))
    return sorted(cands, key=lambda x: x[0], reverse=True)


def _bull_lhlhl_candidates(swings: Sequence[Dict[str, Any]], n: int) -> List[Tuple[float, List[Dict[str, Any]]]]:
    """Bullish 0-1-2-3-4 candidates: L H L H L."""
    cands = []
    for i in range(len(swings) - 4):
        pts = list(swings[i : i + 5])
        if [p["kind"] for p in pts] != ["L", "H", "L", "H", "L"]:
            continue
        p0, p1, p2, p3, p4 = pts
        w1 = p1["price"] - p0["price"]
        w3 = p3["price"] - p2["price"]
        if w1 <= EPS or w3 <= EPS:
            continue
        if p2["price"] <= p0["price"] or p3["price"] <= p1["price"]:
            continue
        # Wave 4 should generally hold above origin and avoid an extremely deep collapse.
        if p4["price"] <= p0["price"]:
            continue
        retr2 = (p1["price"] - p2["price"]) / w1
        retr4 = (p3["price"] - p4["price"]) / w3
        if not (0.18 <= retr2 <= 0.88 and 0.10 <= retr4 <= 0.78):
            continue
        age = _point_age(n, p4)
        if age > 90:
            continue
        # Elliott guideline: wave 3 should not be the weakest-looking leg.
        momentum = min(w3 / max(w1, EPS), 2.0) / 2.0
        overlap_penalty = 0.25 if p4["price"] < p1["price"] else 0.0
        score = (1.0 - min(age / 90, 1.0)) * 0.45 + momentum * 0.35 + (1.0 - abs(retr4 - 0.33) / 0.55) * 0.20 - overlap_penalty
        cands.append((score, pts))
    return sorted(cands, key=lambda x: x[0], reverse=True)


def _fib_wave1(p0: Dict[str, Any], p1: Dict[str, Any]) -> Dict[str, Any]:
    lo, hi = float(p0["price"]), float(p1["price"])
    rng = max(hi - lo, EPS)
    retr = {
        "0.382": hi - 0.382 * rng,
        "0.500": hi - 0.500 * rng,
        "0.618": hi - 0.618 * rng,
        "0.786": hi - 0.786 * rng,
    }
    return {
        "anchor_low": lo,
        "anchor_high": hi,
        "retracement": {k: round(v, 4) for k, v in retr.items()},
    }


def _fib_extensions(p0: Dict[str, Any], p1: Dict[str, Any], p2: Dict[str, Any]) -> Dict[str, float]:
    w1 = max(float(p1["price"] - p0["price"]), EPS)
    base = float(p2["price"])
    return {
        "1.000": round(base + 1.000 * w1, 4),
        "1.272": round(base + 1.272 * w1, 4),
        "1.618": round(base + 1.618 * w1, 4),
        "2.000": round(base + 2.000 * w1, 4),
    }


def _zone_overlap_score(zone: Optional[Dict[str, Any]], low: float, high: float, atr_value: float) -> float:
    if not zone:
        return 0.0
    zlo, zhi = float(zone["low"]), float(zone["high"])
    overlap = max(0.0, min(high, zhi) - max(low, zlo))
    span = max(high - low, zhi - zlo, 0.30 * atr_value, EPS)
    direct = overlap / span
    dist = 0.0
    if overlap <= 0:
        dist = min(abs(zhi - low), abs(zlo - high)) / max(atr_value, EPS)
    proximity = max(0.0, 1.0 - dist / 1.25)
    strength = float(zone.get("strength", 50)) / 100.0
    return clamp((direct * 0.65 + proximity * 0.35) * (0.65 + 0.35 * strength), 0, 1)


def _channel_transition(analysis: Dict[str, Any]) -> Dict[str, Any]:
    ch = analysis.get("parallel_channel") or {}
    desc = analysis.get("descending_trendline") or {}
    events = analysis.get("events") or {}
    direction = ch.get("direction")
    status = ch.get("status")

    breakout = False
    label = "추세 전환 확인 전"
    score = 25.0
    if direction == "DESCENDING" and status == "UPSIDE_BREAK":
        breakout = True
        label = "하락 평행채널 상단 돌파"
        score = 95.0
    elif analysis.get("setup") == "TRENDLINE_BREAKOUT":
        breakout = True
        label = "하락 추세선 돌파"
        score = 82.0
    elif events.get("resistance_breakout"):
        label = "핵심 저항 돌파"
        score = 72.0
    elif direction == "DESCENDING" and status == "NEAR_UPPER":
        label = "하락 채널 상단 테스트"
        score = 60.0
    elif direction == "ASCENDING":
        label = "상승 채널 유지"
        score = 72.0
    elif desc and fnum(desc.get("quality"), 0) and fnum(desc.get("quality"), 0) >= 60:
        label = "하락 추세선 유효"
        score = 42.0

    return {
        "breakout": breakout,
        "label": label,
        "score": round(score, 1),
        "channel_direction": direction,
        "channel_status": status,
    }


def _resistance_pause(analysis: Dict[str, Any], price: float, atr_value: float) -> Tuple[bool, Optional[float]]:
    res = analysis.get("resistance") or {}
    if not res:
        return False, None
    rlow = float(res["low"])
    dist = (rlow - price) / max(atr_value, EPS)
    rs = analysis.get("relative_strength") or {}
    strong_recent = float(rs.get("stock_return", 0)) > 0.06
    return bool(-0.10 <= dist <= 0.65 and strong_recent), rlow


def _pick_target(
    price: float,
    extensions: Dict[str, float],
    resistance: Optional[Dict[str, Any]],
) -> Tuple[Optional[float], Optional[float]]:
    candidates = [float(v) for v in extensions.values() if float(v) > price * 1.005]
    if resistance and float(resistance.get("low", 0)) > price * 1.005:
        candidates.append(float(resistance["low"]))
    candidates = sorted(set(round(v, 4) for v in candidates))
    if not candidates:
        return None, None
    t1 = candidates[0]
    t2 = candidates[1] if len(candidates) > 1 else t1 * 1.06
    return t1, t2


def detect_wave_structure(df: pd.DataFrame, analysis: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    clean = df.copy().dropna(subset=["Open", "High", "Low", "Close", "Volume"]).sort_index()
    atr_s = atr(clean, int(cfg.get("atr_period", 14)))
    price = float(clean["Close"].iloc[-1])
    a = fnum(atr_s.iloc[-1], price * 0.02) or price * 0.02
    highs, lows = confirmed_pivots(
        clean,
        atr_s,
        left=int(cfg.get("wave_pivot_left", cfg.get("pivot_left", 4))),
        right=int(cfg.get("wave_pivot_right", cfg.get("pivot_right", 4))),
        min_prominence_atr=float(cfg.get("wave_pivot_prominence_atr", 0.50)),
    )
    swings = _alternating_swings(highs, lows, max_points=int(cfg.get("wave_max_swings", 18)))
    channel = _channel_transition(analysis)
    support = analysis.get("support") or None
    resistance = analysis.get("resistance") or None
    rs = analysis.get("relative_strength") or {}
    bq = analysis.get("breakout_quality") or {}
    legacy_setup = str(analysis.get("setup", "NEUTRAL"))

    stage = "BASE_BUILDING"
    label = "바닥/구조 전환 관찰"
    direction = "WATCH"
    confidence = 35.0
    wave_points: List[Dict[str, Any]] = []
    fib: Dict[str, Any] = {}
    extensions: Dict[str, float] = {}
    entry_zone = None
    invalidation = None
    confirm_price = None
    target1 = target2 = None
    thesis = "하락 구조가 끝나는지 확인하는 구간입니다."
    action = "추격보다 구조 확인"

    lhlhl = _bull_lhlhl_candidates(swings, len(clean))
    lhl = _bull_lhl_candidates(swings, len(clean))

    if lhlhl:
        base_score, pts = lhlhl[0]
        p0, p1, p2, p3, p4 = pts
        fib = _fib_wave1(p0, p1)
        extensions = _fib_extensions(p0, p1, p2)
        wave_points = [
            {**p0, "wave": "0"},
            {**p1, "wave": "1"},
            {**p2, "wave": "2"},
            {**p3, "wave": "3"},
            {**p4, "wave": "4"},
        ]
        w3 = p3["price"] - p2["price"]
        confirm_price = float(p3["price"] + 0.10 * a)
        invalidation = float(max(p1["price"] - 0.20 * a, p4["price"] - 0.80 * a))
        stage = "WAVE4_PULLBACK" if price <= p3["price"] + 0.15 * a else "WAVE5_ADVANCE"
        if price > p3["price"] + 0.15 * a:
            stage = "WAVE5_ADVANCE"
            label = "5파 상승 / 연장 구간"
            direction = "BULLISH"
            thesis = "3파 고점을 다시 넘기며 5파 또는 연장 파동을 시도하는 구조입니다."
            action = "눌림 보유 · 신규 추격은 저항 확인"
            confidence = 58 + base_score * 25
            w5_candidates = [p4["price"] + 0.618 * w3, p4["price"] + 1.000 * w3]
            t = sorted(v for v in w5_candidates if v > price)
            target1 = t[0] if t else p4["price"] + 1.000 * w3
            target2 = t[1] if len(t) > 1 else p4["price"] + 1.272 * w3
        else:
            label = "4파 조정 · 5파 대기"
            direction = "WATCH"
            thesis = "강한 3파 뒤 조정으로 해석되는 구간입니다. 3파 고점 재돌파가 5파 확인 신호입니다."
            action = "지지 확인 후 재상승 대기"
            confidence = 55 + base_score * 25
            ez_low = max(float(p1["price"]), float(p3["price"] - 0.50 * w3))
            ez_high = float(p3["price"] - 0.236 * w3)
            if ez_high > ez_low:
                entry_zone = {"low": round(ez_low, 4), "high": round(ez_high, 4), "label": "4파 눌림 후보"}
            target1 = float(p3["price"])
            target2 = float(p4["price"] + 0.618 * w3)

    elif lhl:
        base_score, p0, p1, p2 = lhl[0]
        fib = _fib_wave1(p0, p1)
        extensions = _fib_extensions(p0, p1, p2)
        wave_points = [
            {**p0, "wave": "0"},
            {**p1, "wave": "1"},
            {**p2, "wave": "2"},
        ]
        w1 = p1["price"] - p0["price"]
        retr2 = (p1["price"] - p2["price"]) / max(w1, EPS)
        fib38 = p1["price"] - 0.382 * w1
        fib62 = p1["price"] - 0.618 * w1
        fib79 = p1["price"] - 0.786 * w1
        zone_low, zone_high = min(fib62, fib38), max(fib62, fib38)
        confluence = _zone_overlap_score(support, zone_low, zone_high, a)
        confirm_price = float(p1["price"] + 0.12 * a)
        invalidation = float(p0["price"] - 0.20 * a)
        target1, target2 = _pick_target(price, extensions, resistance)

        if price > p1["price"] + 0.12 * a:
            stage = "WAVE3_ADVANCE"
            label = "3파 상승 진행"
            direction = "BULLISH"
            thesis = "2파 저점을 지킨 뒤 1파 고점을 돌파해 3파 진행 조건을 충족한 구조입니다."
            action = "눌림 보유 · 1파 고점 재이탈 주의"
            confidence = 58 + base_score * 18 + confluence * 8 + channel["score"] * 0.10
            invalidation = float(max(p2["price"] - 0.35 * a, p0["price"] - 0.15 * a))
        else:
            stage = "WAVE2_PULLBACK"
            label = "2파 눌림 · 3파 대기"
            direction = "BULLISH" if (0.30 <= retr2 <= 0.72 and confluence >= 0.25) else "WATCH"
            thesis = "1파 상승 뒤 되돌림을 소화하는 구간으로, 2파 저점을 지키고 1파 고점을 넘으면 3파 시나리오가 강화됩니다."
            action = "눌림 분할 접근 · 1파 고점 돌파 확인"
            confidence = 50 + base_score * 20 + confluence * 12 + channel["score"] * 0.10
            entry_zone = {
                "low": round(min(fib62, fib38), 4),
                "high": round(max(fib62, fib38), 4),
                "deep": round(fib79, 4),
                "label": "2파 38.2~61.8% 눌림 후보",
            }

    elif channel["breakout"]:
        stage = "CHANNEL_REVERSAL"
        label = "하락채널 돌파 · 1파 탐색"
        direction = "BULLISH"
        confidence = 66 + min(channel["score"] - 75, 20) * 0.5
        thesis = "하락 채널 상단을 벗어나 기존 하락 구조가 약화된 상태입니다. 첫 상승파와 리테스트 형성을 확인합니다."
        action = "돌파 추격보다 리테스트 대기"
        res = resistance or {}
        confirm_price = fnum(res.get("high"), price + 0.8 * a)
        invalidation = float(price - 1.6 * a)
        target1 = fnum(res.get("low")) if res and fnum(res.get("low"), 0) > price else price + 2.5 * a
        target2 = price + 4.0 * a

    pause, pause_res = _resistance_pause(analysis, price, a)
    if pause and stage in {"WAVE3_ADVANCE", "WAVE5_ADVANCE", "CHANNEL_REVERSAL", "BASE_BUILDING"}:
        stage = "RESISTANCE_PAUSE"
        label = "저항 앞 숨 고르기"
        direction = "WATCH"
        confidence = max(confidence, 64.0)
        thesis = "상승 구조는 유지되지만 단기 저항/매물대 바로 아래라 추격 매수의 손익비가 불리한 구간입니다."
        action = "횡보·눌림 또는 돌파 후 리테스트 대기"
        confirm_price = pause_res
        target1 = pause_res
        if resistance:
            target2 = max(float(resistance["high"] + 2.0 * a), price + 3.0 * a)

    # Legacy downside events override bullish narratives.
    if legacy_setup in {"FAILED_BREAKOUT", "SUPPORT_BREAKDOWN", "TRENDLINE_BREAKDOWN", "TRIANGLE_BREAKDOWN"}:
        stage = "STRUCTURE_RISK"
        label = "구조 훼손 / 리스크"
        direction = "BEARISH"
        confidence = max(70.0, confidence)
        thesis = "핵심 지지 또는 돌파 구조가 훼손되어 상승 파동 카운트를 우선 보류합니다."
        action = "신규 진입 보류 · 무효화 확인"
        invalidation = fnum((support or {}).get("low"), price - 1.0 * a)
        confirm_price = None

    confidence += clamp((float(rs.get("score", 50)) - 50) * 0.10, -5, 5)
    confidence += clamp((float(bq.get("rvol", 1.0)) - 1.0) * 4.0, -3, 5)
    confidence = clamp(confidence, 0, 96)

    if target1 is None and extensions:
        target1, target2 = _pick_target(price, extensions, resistance)

    scenario = {
        "title": label,
        "thesis": thesis,
        "action": action,
        "confirm_price": round(confirm_price, 4) if confirm_price is not None else None,
        "invalidation_price": round(invalidation, 4) if invalidation is not None else None,
        "target1": round(target1, 4) if target1 is not None else None,
        "target2": round(target2, 4) if target2 is not None else None,
    }

    forecast = []
    x_now = len(clean) - 1
    if stage == "WAVE2_PULLBACK" and confirm_price and target1:
        forecast = [
            {"x": x_now, "price": price, "label": "현재"},
            {"x": x_now + 8, "price": max(float(entry_zone["low"]), min(price, float(entry_zone["high"]))), "label": "2파"},
            {"x": x_now + 28, "price": float(target1), "label": "3파"},
        ]
    elif stage == "WAVE4_PULLBACK" and confirm_price and target2:
        forecast = [
            {"x": x_now, "price": price, "label": "현재"},
            {"x": x_now + 10, "price": float(entry_zone["low"]) if entry_zone else price - a, "label": "4파"},
            {"x": x_now + 28, "price": float(target2), "label": "5파"},
        ]
    elif stage in {"CHANNEL_REVERSAL", "RESISTANCE_PAUSE"} and target2:
        mid = confirm_price if confirm_price else price
        forecast = [
            {"x": x_now, "price": price, "label": "현재"},
            {"x": x_now + 10, "price": float(mid), "label": "확인"},
            {"x": x_now + 28, "price": float(target2), "label": "목표"},
        ]

    return {
        "stage": stage,
        "label": label,
        "direction": direction,
        "confidence": round(confidence, 1),
        "swings": swings,
        "points": wave_points,
        "fib": fib,
        "extensions": extensions,
        "entry_zone": entry_zone,
        "channel_transition": channel,
        "scenario": scenario,
        "forecast": forecast,
    }


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


def apply_wave_mechanism(df: pd.DataFrame, analysis: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Make the Instagram-style price-structure mechanism the primary ranking layer.

    Existing zone/channel/triangle calculations are preserved as raw evidence, but the
    public setup/score/grade now prioritize: channel reversal -> 1/2 wave -> 3 wave,
    4/5 wave continuation, resistance pause, and invalidation.
    """
    wave = detect_wave_structure(df, analysis, cfg)
    analysis["legacy_setup"] = analysis.get("setup")
    analysis["legacy_setup_label"] = analysis.get("setup_label")
    analysis["legacy_score"] = analysis.get("score")
    analysis["legacy_grade"] = analysis.get("grade")
    analysis["wave"] = wave

    direction = wave["direction"]
    stage = wave["stage"]
    conf = float(wave["confidence"])
    rs = analysis.get("relative_strength") or {}
    bq = analysis.get("breakout_quality") or {}
    tr = analysis.get("trade") or {}
    ch = wave.get("channel_transition") or {}
    support = analysis.get("support") or {}

    score = conf * 0.52
    score += float(ch.get("score", 50)) * 0.16
    score += float(support.get("strength", 50)) * 0.10 if support else 5.0
    score += float(rs.get("score", 50)) * 0.08
    score += clamp((float(bq.get("rvol", 1.0)) - 0.65) / 1.15, 0, 1) * 7.0
    score += clamp(float(tr.get("rr1", 0)) / 3.0, 0, 1) * 7.0

    stage_bonus = {
        "WAVE2_PULLBACK": 8.0,
        "WAVE3_ADVANCE": 10.0,
        "WAVE4_PULLBACK": 3.0,
        "WAVE5_ADVANCE": 2.0,
        "CHANNEL_REVERSAL": 5.0,
        "RESISTANCE_PAUSE": -2.0,
        "STRUCTURE_RISK": -18.0,
        "BASE_BUILDING": -4.0,
    }.get(stage, 0.0)
    score = clamp(score + stage_bonus, 0, 100)

    # 2-wave candidates need adequate R/R or a very strong confluence score.
    hard_pass = bool(
        direction == "BULLISH"
        and stage in {"WAVE2_PULLBACK", "WAVE3_ADVANCE", "CHANNEL_REVERSAL"}
        and score >= float(cfg.get("wave_min_trade_score", 68))
        and (float(tr.get("rr1", 0)) >= float(cfg.get("wave_min_rr", 1.5)) or conf >= 78)
    )

    analysis["setup"] = stage
    analysis["setup_label"] = wave["label"]
    analysis["direction"] = direction
    analysis["score"] = round(score, 1)
    analysis["grade"] = _grade(score)
    analysis["hard_filter_pass"] = hard_pass

    chart = analysis.setdefault("chart", {})
    chart["wave"] = wave
    return analysis
