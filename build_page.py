#!/usr/bin/env python3
from __future__ import annotations

import html
import json
from pathlib import Path

import pandas as pd


def esc(x):
    return html.escape(str(x))


def fmt(v, d=1):
    try:
        return f"{float(v):,.{d}f}"
    except Exception:
        return "-"


def fmt_price(v):
    try:
        return f"{int(round(float(v))):,}"
    except Exception:
        return "-"


def fmt_bn(v):
    try:
        return f"{float(v)/100_000_000:,.0f}억"
    except Exception:
        return "-"


def score_cell(v):
    try:
        x = max(0.0, min(100.0, float(v)))
    except Exception:
        x = 0.0
    return (
        f"<div class='metric'><span>{x:.1f}</span>"
        f"<div class='bar'><i style='width:{x:.1f}%'></i></div></div>"
    )


def badge(text, kind="muted"):
    return f"<span class='badge {kind}'>{esc(text)}</span>"


def regime_badge(value):
    if value == "RISK-ON":
        return badge("RISK-ON", "good")
    if value == "RISK-OFF":
        return badge("RISK-OFF", "bad")
    return badge("NEUTRAL", "warn")


def supertrend_badge(value):
    v = str(value).upper()
    return badge("GOOD", "good") if v == "GOOD" else badge("BAD", "bad")


def risk_badge(value):
    if value == "LOW":
        return badge("LOW", "good")
    if value == "HIGH":
        return badge("HIGH", "bad")
    return badge("MED", "warn")


def state_badge(value):
    if value == "STRONG LONG":
        return badge(value, "strong")
    if value in ("LONG", "POSITIVE"):
        return badge(value, "good")
    if value in ("WEAK", "BEARISH"):
        return badge(value, "bad")
    return badge(value, "muted")


def grade_badge(value):
    if value == "A+":
        return badge("A+", "strong")
    if value == "A":
        return badge("A", "good")
    if value == "B":
        return badge("B", "fresh")
    if value == "EARLY":
        return badge("EARLY", "warn")
    if value == "WATCH":
        return badge("WATCH", "muted")
    return badge("-", "muted")


def tier_badge(value):
    if value == "CONFIRMED":
        return badge("CONFIRMED", "strong")
    if value == "FRESH":
        return badge("FRESH", "fresh")
    if value == "EARLY":
        return badge("EARLY", "warn")
    return badge("RANK", "muted")


def freshness_label(age):
    try:
        age = int(age)
    except Exception:
        return "-"
    if age == 0:
        return "TODAY"
    if age == 1:
        return "1D"
    if age <= 5:
        return f"{age}D"
    return "OLD"


def detail_html(r):
    return (
        "<details><summary>보기</summary><div class='detail-grid'>"
        f"<div><b>CCI</b><span>{fmt(r.get('cci'))}</span></div>"
        f"<div><b>CCI 3D Δ</b><span>{fmt(r.get('cci_delta3'))}</span></div>"
        f"<div><b>CCI Cross</b><span>{freshness_label(r.get('cci_cross_age'))}</span></div>"
        f"<div><b>+DI / -DI</b><span>{fmt(r.get('plus_di'))} / {fmt(r.get('minus_di'))}</span></div>"
        f"<div><b>DMI Ratio</b><span>{fmt(r.get('dmi_ratio'),2)}x</span></div>"
        f"<div><b>ADX</b><span>{fmt(r.get('adx'))}</span></div>"
        f"<div><b>ADX 3D Δ</b><span>{fmt(r.get('adx_delta3'))}</span></div>"
        f"<div><b>Supertrend</b><span>{supertrend_badge(r.get('supertrend_status','BAD'))}</span></div>"
        f"<div><b>ST Flip</b><span>{freshness_label(r.get('supertrend_flip_age'))}</span></div>"
        f"<div><b>ST Dist / ATR</b><span>{fmt(r.get('supertrend_distance_atr'),2)}x</span></div>"
        f"<div><b>Entry Score</b><span>{fmt(r.get('entry_score'))}</span></div>"
        f"<div><b>Dollar Vol</b><span>{fmt(r.get('relative_dollar_volume'),2)}x</span></div>"
        f"<div><b>ADV20</b><span>{fmt_bn(r.get('avg20_trading_value'))}</span></div>"
        f"<div><b>RS20 excess</b><span>{fmt(r.get('rs20_excess_pct'),2)}%</span></div>"
        f"<div><b>RS60 excess</b><span>{fmt(r.get('rs60_excess_pct'),2)}%</span></div>"
        f"<div><b>ATR%</b><span>{fmt(r.get('atr_pct'),2)}%</span></div>"
        f"<div><b>20D vol ann.</b><span>{fmt(r.get('vol20_ann_pct'),1)}%</span></div>"
        "</div></details>"
    )


def table_rows(df):
    out = []
    for i, (_, r) in enumerate(df.iterrows(), start=1):
        ret = float(r.get("daily_return_pct", 0) or 0)
        ret_class = "up" if ret > 0 else ("down" if ret < 0 else "")
        out.append(
            f"<tr data-market='{esc(r.get('market',''))}' data-alpha='{fmt(r.get('alpha_score'),2)}' "
            f"data-name='{esc(str(r.get('name','')).lower())}' data-ticker='{esc(str(r.get('ticker','')).zfill(6))}'>"
            f"<td>{i}</td>"
            f"<td class='name'><b>{esc(r.get('name','-'))}</b><small>{str(r.get('ticker','')).zfill(6)} · {esc(r.get('market','-'))}</small></td>"
            f"<td>{tier_badge(str(r.get('signal_tier','RANK')))}</td>"
            f"<td>{fmt_price(r.get('close'))}</td>"
            f"<td class='{ret_class}'>{fmt(ret,2)}%</td>"
            f"<td class='alpha'>{score_cell(r.get('alpha_score'))}</td>"
            f"<td>{score_cell(r.get('entry_score'))}</td>"
            f"<td>{supertrend_badge(str(r.get('supertrend_status','BAD')))}</td>"
            f"<td>{score_cell(r.get('trend_score'))}</td>"
            f"<td>{score_cell(r.get('momentum_score'))}</td>"
            f"<td>{score_cell(r.get('flow_score'))}</td>"
            f"<td>{score_cell(r.get('rs_score'))}</td>"
            f"<td>{risk_badge(str(r.get('risk_level','MED')))}</td>"
            f"<td>{regime_badge(str(r.get('regime','NEUTRAL')))}</td>"
            f"<td>{state_badge(str(r.get('signal_state','NEUTRAL')))}</td>"
            f"<td>{grade_badge(str(r.get('setup_grade','-')))}</td>"
            f"<td>{detail_html(r)}</td>"
            "</tr>"
        )
    return "".join(out)


def make_table(df, table_id, empty_text="조건을 만족한 종목이 없습니다."):
    if df.empty:
        return f"<div class='empty'>{esc(empty_text)}</div>"
    return (
        f"<div class='table-wrap'><table id='{table_id}'><thead><tr>"
        "<th>#</th><th>종목</th><th>Tier</th><th>종가</th><th>등락</th><th>Alpha</th>"
        "<th>Entry</th><th>Supertrend</th><th>Trend</th><th>Momentum</th><th>Flow</th><th>RS</th><th>Risk</th>"
        "<th>Regime</th><th>State</th><th>Setup</th><th>상세</th>"
        "</tr></thead><tbody>" + table_rows(df) + "</tbody></table></div>"
    )


def regime_card(market, info):
    regime = info.get("regime", "NEUTRAL")
    return (
        "<div class='regime-card'>"
        f"<div class='regime-head'><b>{esc(market)}</b>{regime_badge(regime)}</div>"
        f"<div class='regime-score'>{int(info.get('score',0))}/5</div>"
        f"<div class='muted'>Breadth 20D {float(info.get('breadth20',0))*100:.0f}% · 60D {float(info.get('breadth60',0))*100:.0f}%</div>"
        f"<div class='muted'>Index 20D {float(info.get('benchmark_ret20_pct',0)):+.1f}% · 60D {float(info.get('benchmark_ret60_pct',0)):+.1f}%</div>"
        "</div>"
    )


def safe_read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def build_search_dataset(all_df: pd.DataFrame) -> str:
    x = all_df.copy()
    x["ticker"] = x["ticker"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(6)
    x["alpha_rank_all"] = x["alpha_score"].rank(method="min", ascending=False).astype(int)
    x["alpha_rank_market"] = x.groupby("market")["alpha_score"].rank(method="min", ascending=False).astype(int)

    keep = [
        "ticker", "name", "market", "signal_date", "close", "daily_return_pct",
        "alpha_score", "entry_score", "trend_score", "momentum_score", "flow_score", "rs_score",
        "risk_score", "risk_level", "regime", "regime_score", "signal_state",
        "setup_grade", "signal_tier", "cci", "cci_prev", "cci_delta3",
        "cci_cross_age", "plus_di", "minus_di", "dmi_ratio", "dmi_direction",
        "adx", "adx_delta3", "supertrend", "supertrend_good", "supertrend_status",
        "supertrend_score", "supertrend_bull_flip_age", "supertrend_bear_flip_age", "supertrend_flip_age",
        "supertrend_distance_atr", "extension_score", "relative_dollar_volume", "avg20_trading_value",
        "rs20_excess_pct", "rs60_excess_pct", "rs20_percentile", "rs60_percentile",
        "atr_pct", "vol20_ann_pct", "above_ma20", "above_ma60",
        "confirmed_buy", "fresh_buy", "early_setup", "active_trend",
        "alpha_rank_all", "alpha_rank_market",
    ]
    keep = [c for c in keep if c in x.columns]
    x = x[keep].replace([float("inf"), float("-inf")], pd.NA)
    # pandas emits missing numeric values as JSON null, keeping the embedded dataset strict JSON.
    payload = x.to_json(orient="records", force_ascii=False)
    # Prevent an unlikely literal </script> inside a stock name from terminating the script tag.
    return payload.replace("</", "<\\/")


def main():
    results = Path("results")
    docs = Path("docs")
    docs.mkdir(exist_ok=True)

    summary = json.loads((results / "summary.json").read_text(encoding="utf-8"))
    all_df = pd.read_csv(results / "latest_all_scored.csv")
    confirmed = safe_read_csv(results / "latest_confirmed_buy.csv")
    fresh = safe_read_csv(results / "latest_fresh_buy.csv")
    early = safe_read_csv(results / "latest_early_setups.csv")
    top = all_df.sort_values("alpha_score", ascending=False).head(60)
    stock_data_json = build_search_dataset(all_df)

    p = summary["parameters"]
    w = summary.get("weights", {})
    regimes = summary.get("regimes", {})
    close_align = summary.get("close_date_alignment", {})

    confirmed_html = make_table(confirmed, "confirmed-table", "오늘 Confirmed Buy 조건을 만족한 종목이 없습니다.")
    fresh_html = make_table(fresh, "fresh-table", "오늘 Fresh Buy 조건을 만족한 종목이 없습니다.")
    early_html = make_table(early, "early-table", "현재 Early Setup 조건을 만족한 종목이 없습니다.")
    top_html = make_table(top, "rank-table")

    page = f'''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#080b10">
<meta name="data-generated-at" content="{esc(summary.get('generated_at','-'))}">
<meta name="data-signal-date" content="{esc(summary.get('latest_signal_date','-'))}">
<title>Korea Equity Alpha Screener V2.4</title>
<style>
:root{{--bg:#080b10;--panel:#0f151d;--panel2:#131c27;--line:#233042;--text:#edf3f8;--muted:#91a1b2;--accent:#83b8ff;--green:#53d49a;--red:#ff7b86;--yellow:#f1c66a;--purple:#bd8cff;--cyan:#65d4e8}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font-family:Inter,Pretendard,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
.wrap{{max-width:1540px;margin:0 auto;padding:24px}}.hero{{background:linear-gradient(145deg,#121c28,#0c1118);border:1px solid var(--line);border-radius:22px;padding:24px;box-shadow:0 20px 50px rgba(0,0,0,.22)}}
.hero-top{{display:flex;align-items:flex-start;justify-content:space-between;gap:18px}}.hero-copy{{min-width:0}}.refresh-box{{display:flex;flex-direction:column;align-items:flex-end;gap:8px;flex:0 0 auto}}.refresh-btn{{display:inline-flex;align-items:center;gap:8px;padding:11px 14px;border-radius:12px;border:1px solid rgba(83,212,154,.38);background:rgba(83,212,154,.10);color:var(--green);font-weight:900;white-space:nowrap}}.refresh-btn:hover{{background:rgba(83,212,154,.17)}}.refresh-btn.loading{{opacity:.7;pointer-events:none}}.refresh-icon{{font-size:17px;line-height:1}}.update-chip{{font-size:10px;font-weight:900;letter-spacing:.05em;color:var(--green);border:1px solid rgba(83,212,154,.25);background:rgba(83,212,154,.07);border-radius:999px;padding:5px 8px}}.update-meta{{font-size:10px;color:var(--muted);text-align:right;line-height:1.45}}.refresh-toast{{position:fixed;right:18px;bottom:18px;z-index:1000;background:#111a24;border:1px solid var(--line);border-radius:12px;padding:11px 14px;font-size:12px;font-weight:700;box-shadow:0 18px 50px rgba(0,0,0,.38);opacity:0;transform:translateY(8px);pointer-events:none;transition:.2s}}.refresh-toast.show{{opacity:1;transform:translateY(0)}}
.eyebrow{{font-size:12px;letter-spacing:.14em;color:var(--accent);font-weight:800}}h1{{font-size:30px;margin:7px 0 8px}}h2{{font-size:20px;margin:30px 0 12px}}.sub,.muted{{color:var(--muted);font-size:13px;line-height:1.65}}
.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:18px}}.stat{{background:#0b1118;border:1px solid var(--line);border-radius:15px;padding:15px}}.stat .v{{font-size:25px;font-weight:800}}.stat .k{{font-size:12px;color:var(--muted);margin-top:4px}}
.regime-grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:14px}}.regime-card{{background:#0b1118;border:1px solid var(--line);border-radius:15px;padding:15px}}.regime-head{{display:flex;justify-content:space-between;align-items:center}}.regime-score{{font-size:26px;font-weight:800;margin:10px 0 4px}}
.model-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:12px}}.model-card{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:14px}}.model-card strong{{font-size:18px}}.model-card p{{margin:6px 0 0;color:var(--muted);font-size:12px;line-height:1.5}}
.ladder{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:12px 0 2px}}.ladder-card{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:14px}}.ladder-card h3{{font-size:14px;margin:0 0 7px}}.ladder-card p{{font-size:12px;color:var(--muted);line-height:1.55;margin:0}}.ladder-card.confirmed{{border-color:rgba(189,140,255,.4)}}.ladder-card.fresh{{border-color:rgba(101,212,232,.35)}}.ladder-card.early{{border-color:rgba(241,198,106,.35)}}
.toolbar{{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 12px}}input,select,button{{font:inherit}}input,select{{background:#0d141d;border:1px solid var(--line);color:var(--text);border-radius:10px;padding:9px 11px;outline:none}}input{{min-width:240px}}button{{border:1px solid rgba(131,184,255,.35);background:rgba(131,184,255,.10);color:var(--accent);border-radius:10px;padding:10px 15px;font-weight:800;cursor:pointer}}button:hover{{background:rgba(131,184,255,.16)}}.table-wrap{{overflow:auto;border:1px solid var(--line);border-radius:16px;background:var(--panel)}}table{{width:100%;border-collapse:collapse;min-width:1660px}}th,td{{padding:11px 9px;border-bottom:1px solid #1e2a38;text-align:right;white-space:nowrap;vertical-align:middle}}th{{font-size:11px;color:var(--muted);background:#0b1118;position:sticky;top:0;z-index:2}}td{{font-size:12px}}th:nth-child(2),td.name{{text-align:left}}td.name b{{display:block;font-size:13px}}td.name small{{display:block;color:var(--muted);margin-top:3px}}tr:hover td{{background:#111a24}}tr:last-child td{{border-bottom:none}}
.search-panel{{background:linear-gradient(145deg,#101923,#0c1219);border:1px solid var(--line);border-radius:18px;padding:18px}}.search-row{{display:flex;gap:9px;align-items:center;flex-wrap:wrap}}.search-wrap{{position:relative;flex:1;min-width:280px}}.search-wrap input{{width:100%;min-width:0;padding:12px 13px;font-size:14px}}.suggestions{{position:absolute;left:0;right:0;top:calc(100% + 6px);z-index:50;background:#0a1017;border:1px solid var(--line);border-radius:12px;overflow:hidden;box-shadow:0 18px 50px rgba(0,0,0,.42);display:none;max-height:330px;overflow-y:auto}}.suggestion{{display:flex;justify-content:space-between;gap:12px;padding:11px 12px;cursor:pointer;border-bottom:1px solid #1b2633}}.suggestion:last-child{{border-bottom:none}}.suggestion:hover,.suggestion.active{{background:#121d28}}.suggestion b{{font-size:13px}}.suggestion small{{color:var(--muted);font-size:11px}}.result-empty{{margin-top:14px;border:1px dashed var(--line);border-radius:14px;padding:22px;text-align:center;color:var(--muted)}}.stock-card{{margin-top:15px;border:1px solid var(--line);border-radius:18px;background:#0b1118;overflow:hidden}}.stock-head{{display:flex;justify-content:space-between;gap:16px;align-items:flex-start;padding:18px;border-bottom:1px solid var(--line)}}.stock-title h3{{font-size:22px;margin:0 0 5px}}.stock-title .meta{{color:var(--muted);font-size:12px}}.stock-price{{text-align:right}}.stock-price strong{{display:block;font-size:24px}}.score-grid{{display:grid;grid-template-columns:repeat(7,1fr);gap:9px;padding:14px 18px}}.score-box{{border:1px solid #1e2b3a;background:#0e1620;border-radius:13px;padding:11px}}.score-box .k{{color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:.06em}}.score-box .v{{font-size:20px;font-weight:850;margin-top:5px}}.score-box.alpha-box .v{{color:var(--accent)}}.result-grid{{display:grid;grid-template-columns:repeat(5,1fr);gap:0;border-top:1px solid var(--line)}}.result-item{{padding:12px 15px;border-right:1px solid #1e2a38;border-bottom:1px solid #1e2a38}}.result-item:nth-child(5n){{border-right:none}}.result-item b{{display:block;color:var(--muted);font-size:10px;margin-bottom:5px}}.result-item span{{font-size:13px;font-weight:750}}.rank-pill{{display:inline-flex;border-radius:999px;padding:5px 9px;border:1px solid var(--line);font-size:11px;color:#c7d4df;margin-right:5px}}.search-hint{{margin-top:9px;color:var(--muted);font-size:11px}}
.metric{{min-width:72px}}.metric>span{{font-weight:800}}.alpha .metric>span{{color:var(--accent);font-size:14px}}.bar{{height:3px;background:#1b2735;border-radius:99px;margin-top:5px;overflow:hidden}}.bar i{{display:block;height:100%;background:linear-gradient(90deg,#5f91d9,#9ec8ff)}}
.badge{{display:inline-flex;align-items:center;border:1px solid var(--line);border-radius:999px;padding:4px 8px;font-size:10px;font-weight:800;letter-spacing:.03em}}.badge.good{{color:var(--green);border-color:rgba(83,212,154,.35);background:rgba(83,212,154,.07)}}.badge.bad{{color:var(--red);border-color:rgba(255,123,134,.35);background:rgba(255,123,134,.07)}}.badge.warn{{color:var(--yellow);border-color:rgba(241,198,106,.35);background:rgba(241,198,106,.07)}}.badge.strong{{color:var(--purple);border-color:rgba(189,140,255,.40);background:rgba(189,140,255,.09)}}.badge.fresh{{color:var(--cyan);border-color:rgba(101,212,232,.38);background:rgba(101,212,232,.08)}}.badge.muted{{color:#aeb9c6}}.up{{color:var(--green)}}.down{{color:var(--red)}}
details{{text-align:left}}summary{{cursor:pointer;color:var(--accent)}}.detail-grid{{position:absolute;right:26px;z-index:20;margin-top:8px;display:grid;grid-template-columns:repeat(3,150px);gap:8px;background:#0c121a;border:1px solid var(--line);border-radius:13px;padding:12px;box-shadow:0 16px 45px rgba(0,0,0,.45)}}.detail-grid div{{display:flex;flex-direction:column;gap:4px}}.detail-grid b{{font-size:10px;color:var(--muted)}}.detail-grid span{{font-size:12px}}
.note{{margin-top:24px;background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:17px;color:var(--muted);font-size:12px;line-height:1.8}}.empty{{padding:24px;text-align:center;color:var(--muted);background:var(--panel);border:1px dashed var(--line);border-radius:16px}}
@media(max-width:1100px){{.score-grid{{grid-template-columns:repeat(3,1fr)}}.result-grid{{grid-template-columns:repeat(3,1fr)}}.result-item:nth-child(5n){{border-right:1px solid #1e2a38}}.result-item:nth-child(3n){{border-right:none}}}}
@media(max-width:900px){{.wrap{{padding:12px 12px 82px}}h1{{font-size:24px}}.grid,.model-grid,.ladder,.regime-grid{{grid-template-columns:1fr 1fr}}.detail-grid{{position:fixed;left:12px;right:12px;bottom:12px;grid-template-columns:repeat(2,1fr);max-height:72vh;overflow:auto}}.stock-head{{flex-direction:column}}.stock-price{{text-align:left}}.hero-top{{gap:10px}}.refresh-box{{gap:6px}}.refresh-btn{{padding:10px 12px}}}}
@media(max-width:700px){{.hero{{padding:16px}}.hero-top{{align-items:flex-start}}.hero .sub{{font-size:11px;line-height:1.55}}.refresh-btn .refresh-label{{display:none}}.refresh-btn{{width:44px;height:44px;justify-content:center;padding:0;border-radius:50%}}.refresh-icon{{font-size:21px}}.update-meta{{display:none}}.grid,.model-grid,.ladder,.regime-grid{{grid-template-columns:1fr}}.search-row,.toolbar{{display:grid;grid-template-columns:1fr;gap:8px}}input,select{{width:100%;min-width:0}}.score-grid{{grid-template-columns:repeat(2,1fr)}}.result-grid{{grid-template-columns:repeat(2,1fr)}}.result-item:nth-child(3n){{border-right:1px solid #1e2a38}}.result-item:nth-child(2n){{border-right:none}}
.table-wrap{{overflow:visible;border:none;background:transparent}}table{{display:block;min-width:0;width:100%}}thead{{display:none}}tbody{{display:grid;gap:10px}}tr{{display:grid;grid-template-columns:1fr auto;gap:0;background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:12px;overflow:hidden}}tr:hover td{{background:transparent}}td{{display:none;border:0;padding:4px 0;white-space:normal;text-align:right}}td:nth-child(2),td:nth-child(3),td:nth-child(4),td:nth-child(5),td:nth-child(6),td:nth-child(7),td:nth-child(8),td:nth-child(13),td:nth-child(17){{display:block}}td:nth-child(2){{grid-column:1/2;text-align:left;padding-bottom:9px}}td:nth-child(3){{grid-column:2/3;grid-row:1;text-align:right}}td:nth-child(4){{grid-column:1/2;text-align:left;font-size:18px;font-weight:900}}td:nth-child(4)::after{{content:'원';font-size:11px;color:var(--muted);margin-left:3px;font-weight:600}}td:nth-child(5){{grid-column:2/3;font-weight:800;align-self:center}}td:nth-child(6),td:nth-child(7),td:nth-child(8),td:nth-child(13){{grid-column:1/3;display:flex;align-items:center;justify-content:space-between;border-top:1px solid #1e2a38;padding:8px 0}}td:nth-child(6)::before{{content:'Alpha';color:var(--muted);font-size:11px;font-weight:800}}td:nth-child(7)::before{{content:'Entry';color:var(--muted);font-size:11px;font-weight:800}}td:nth-child(8)::before{{content:'Supertrend';color:var(--muted);font-size:11px;font-weight:800}}td:nth-child(13)::before{{content:'Risk';color:var(--muted);font-size:11px;font-weight:800}}td:nth-child(17){{grid-column:1/3;text-align:left;padding-top:8px}}.metric{{min-width:110px}}.note{{font-size:11px}}.refresh-toast{{left:12px;right:12px;bottom:16px;text-align:center}}}}
@media(max-width:420px){{h1{{font-size:21px}}.eyebrow{{font-size:10px}}.score-grid,.result-grid{{grid-template-columns:1fr 1fr}}.stat .v{{font-size:24px}}}}
</style>
</head>
<body><div class="wrap">
<section class="hero">
<div class="hero-top">
  <div class="hero-copy">
    <div class="eyebrow">HF TECHNICAL ALPHA · V2.4 CLOSE REFRESH</div>
    <h1>Korea Equity Alpha Screener</h1>
    <div class="sub">기준일 <b>{esc(summary.get('latest_signal_date','-'))}</b> · 생성 {esc(summary.get('generated_at','-'))}<br>KRX 정규장 일봉 종가 기준 · NXT 데이터 미사용 · 평일 15:50 KST 자동 계산 + 16:20 KST 보정 실행<br>종가 날짜 동기화 {fmt(close_align.get('coverage_pct',100),1)}% · 분석 {close_align.get('symbols_after_alignment',summary.get('symbols_scored',0))}/{close_align.get('symbols_before_alignment',summary.get('symbols_scored',0))}종목<br>KOSPI 시총 상위 {p.get('kospi_n',200)} + KOSDAQ 시총 상위 {p.get('kosdaq_n',150)} · Alpha와 Risk를 분리하고 진입 신호를 3단계로 분류</div>
  </div>
  <div class="refresh-box">
    <button id="refresh-btn" class="refresh-btn" type="button" onclick="checkForLatest(true)" aria-label="최신 데이터 새로고침"><span id="refresh-icon" class="refresh-icon">↻</span><span class="refresh-label">최신 데이터</span></button>
    <span class="update-chip">AUTO 15:50 · 16:20</span>
    <div class="update-meta">버튼은 새 배포본을 캐시 없이 확인합니다.<br><span id="last-check-text">마지막 확인: 방금</span></div>
  </div>
</div>
<div class="grid">
<div class="stat"><div class="v">{summary.get('confirmed_buy_count',0)}</div><div class="k">Confirmed Buy · 가장 엄격한 확정 신호</div></div>
<div class="stat"><div class="v">{summary.get('fresh_buy_count',0)}</div><div class="k">Fresh Buy · 초기 진입 후보</div></div>
<div class="stat"><div class="v">{summary.get('early_setup_count',0)}</div><div class="k">Early Setup · CCI 돌파 전 선행 후보</div></div>
<div class="stat"><div class="v">{summary.get('symbols_scored',0)}</div><div class="k">최종 분석 종목</div></div>
</div>
<div class="regime-grid">{regime_card('KOSPI', regimes.get('KOSPI',{}))}{regime_card('KOSDAQ', regimes.get('KOSDAQ',{}))}</div>
</section>

<h2>Signal Ladder</h2>
<div class="ladder">
<div class="ladder-card confirmed"><h3>🔥 Confirmed Buy</h3><p>Alpha ≥ {p.get('confirmed_alpha_threshold',75):.0f} · Entry ≥ 70 · CCI Cross ≤1D · +DI&gt;-DI · ADX ≥ {p.get('adx_threshold',20):.0f} · <b>Supertrend GOOD</b> · Flow ≥ 50. 확정 신호에서만 Supertrend를 하드 확인합니다.</p></div>
<div class="ladder-card fresh"><h3>🟢 Fresh Buy</h3><p>Alpha ≥ {p.get('fresh_alpha_threshold',60):.0f} · Entry ≥ 60 · CCI Cross ≤3D · CCI&gt;0 · +DI&gt;-DI · Flow ≥ 40. Supertrend BAD를 즉시 탈락시키지 않고 Entry 점수에서 감점해 초기 전환을 남깁니다.</p></div>
<div class="ladder-card early"><h3>🟡 Early Setup</h3><p>Alpha ≥ {p.get('early_alpha_threshold',50):.0f} · Entry ≥ 45 · -30&lt;CCI≤0 · CCI 3D Δ≥25 · +DI/-DI ≥0.85 · Flow≥40 · RS≥50. Supertrend 전환 전 후보도 감시할 수 있습니다.</p></div>
</div>

<h2>Model Architecture</h2>
<div class="model-grid">
<div class="model-card"><strong>Trend {w.get('trend',30)}%</strong><p>DMI 방향 35% + ADX 강도 30% + ADX 가속 10% + Supertrend 25%. Supertrend는 별도 Alpha 버킷이 아니라 Trend 내부에서 중복 계산을 줄입니다.</p></div>
<div class="model-card"><strong>Momentum {w.get('momentum',25)}%</strong><p>CCI 0선 돌파 신선도 + 3일 기울기 + 과열을 제한한 CCI 레벨.</p></div>
<div class="model-card"><strong>Flow {w.get('flow',20)}%</strong><p>일봉 CVD proxy 기울기/EMA 위치 + 상대 거래대금. 실제 체결 CVD와는 구분.</p></div>
<div class="model-card"><strong>Relative Strength {w.get('relative_strength',25)}%</strong><p>KOSPI/KOSDAQ 벤치마크 대비 20·60일 초과수익률의 시장 내 percentile.</p></div>
</div>

<h2>🔥 Confirmed Buy</h2>
<div class="sub" style="margin-bottom:10px">확정성이 가장 높은 대신 발생 빈도는 낮게 설계한 신호.</div>
{confirmed_html}

<h2>🟢 Fresh Buy</h2>
<div class="sub" style="margin-bottom:10px">Confirmed에는 못 미치지만 추세가 만들어지는 초기에 잡기 위한 실전 핵심 후보. Confirmed 종목은 중복 표시하지 않습니다.</div>
{fresh_html}

<h2>🟡 Early Setup</h2>
<div class="sub" style="margin-bottom:10px">CCI가 아직 0선을 넘기 전이지만 모멘텀 가속, DMI 근접, Flow와 상대강도가 양호한 선행 감시 후보.</div>
{early_html}

<h2>전체 분석 종목 검색</h2>
<div class="sub" style="margin-bottom:10px">Top 60에 없어도 분석 완료된 전체 종목에서 종목명 또는 6자리 종목코드로 찾을 수 있습니다. 검색 결과에서 Alpha 구성과 기술적 상세값을 한 번에 확인하세요.</div>
<div class="search-panel">
  <div class="search-row">
    <div class="search-wrap">
      <input id="stock-search" placeholder="예: 삼성전자 또는 005930" autocomplete="off" oninput="onStockInput()" onkeydown="onStockKey(event)">
      <div id="stock-suggestions" class="suggestions"></div>
    </div>
    <select id="stock-market" onchange="onStockInput()"><option value="ALL">전체 시장</option><option value="KOSPI">KOSPI</option><option value="KOSDAQ">KOSDAQ</option></select>
    <button type="button" onclick="runStockSearch()">종목 조회</button>
  </div>
  <div class="search-hint">이 검색은 현재 스크리너가 분석한 전체 유니버스 {summary.get('symbols_scored',0)}개 종목을 대상으로 합니다.</div>
  <div id="stock-result" class="result-empty">종목명을 입력하면 전체 데이터에서 검색합니다.</div>
</div>

<h2>Alpha Ranking · Top 60</h2>
<div class="sub" style="margin-bottom:10px">전체 종목 중 Alpha Score 상위 60개입니다. 아래 필터는 Top 60 내부에서만 작동합니다.</div>
<div class="toolbar">
<input id="rank-search" placeholder="Top 60 내 종목명/코드 검색" oninput="filterRankRows()">
<select id="rank-market" onchange="filterRankRows()"><option value="ALL">전체 시장</option><option value="KOSPI">KOSPI</option><option value="KOSDAQ">KOSDAQ</option></select>
<select id="rank-alpha" onchange="filterRankRows()"><option value="0">Alpha 전체</option><option value="50">50+</option><option value="60">60+</option><option value="70">70+</option><option value="80">80+</option></select>
</div>
{top_html}

<div class="note"><b>왜 3단계인가?</b> Alpha 안에는 이미 CCI·DMI/ADX·Flow가 포함되어 있어 같은 요소를 모두 Hard Filter로 다시 요구하면 신호가 지나치게 줄어듭니다. 그래서 Confirmed만 엄격하게 유지하고 Fresh/Early는 단계적으로 완화합니다.<br>
<b>Alpha Score</b>는 예측확률이 아니라 0~100 범위의 기술적 랭킹 점수입니다. Trend 30% + Momentum 25% + Flow 20% + Relative Strength 25%이며 Risk는 별도입니다. Trend 내부는 DMI 35% + ADX 강도 30% + ADX 가속 10% + Supertrend 25%입니다.<br>
<b>Entry Score</b>는 진입 타이밍 점수입니다. CCI 신선도 30% + Supertrend 25% + DMI/ADX 20% + Flow 15% + 과열/이격 10%로 계산합니다. Supertrend는 기본 ATR {p.get('supertrend_period',10)} / Factor {p.get('supertrend_factor',3.0)} 설정입니다.<br>
<b>Early Alpha 기준이 낮은 이유</b>: CCI가 아직 0 이하인 돌파 전 단계는 Momentum과 Trend 점수가 구조적으로 낮아집니다. 따라서 Early는 Alpha {p.get('early_alpha_threshold',50):.0f} 이상에 RS·Flow·DMI 근접 조건을 추가해 품질을 보완합니다.<br>
<b>Regime</b>: 지수의 20/60일 이동평균 구조와 종목 breadth를 합쳐 RISK-ON / NEUTRAL / RISK-OFF로 분류하며 Alpha 자체를 깎지는 않습니다.<br>
<b>Flow</b>의 CVD는 Yahoo 일봉 OHLCV로 만든 proxy이며 실제 bid/ask 체결 CVD가 아닙니다. 이 임계값들은 합리적인 초기값이며 최종값은 단계별 신호 수와 1·5·10일 forward return 백테스트로 검증해야 합니다.</div>
</div>
<div id="refresh-toast" class="refresh-toast" role="status" aria-live="polite"></div>
<script>
const STOCKS = {stock_data_json};
let suggestionIndex = -1;
let currentMatches = [];

function escJs(v){{
  return String(v ?? '').replace(/[&<>"']/g, ch => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[ch]));
}}
function num(v,d=1){{ const n=Number(v); return Number.isFinite(n)?n.toLocaleString('ko-KR',{{minimumFractionDigits:d,maximumFractionDigits:d}}):'-'; }}
function price(v){{ const n=Number(v); return Number.isFinite(n)?Math.round(n).toLocaleString('ko-KR'):'-'; }}
function bn(v){{ const n=Number(v); return Number.isFinite(n)?Math.round(n/100000000).toLocaleString('ko-KR')+'억':'-'; }}
function crossLabel(age){{ const a=Number(age); if(!Number.isFinite(a)||a>5)return 'OLD'; if(a===0)return 'TODAY'; if(a===1)return '1D'; return a+'D'; }}
function badgeHtml(text, kind='muted'){{ return `<span class="badge ${{kind}}">${{escJs(text)}}</span>`; }}
function riskHtml(v){{ return badgeHtml(v, v==='LOW'?'good':(v==='HIGH'?'bad':'warn')); }}
function regimeHtml(v){{ return badgeHtml(v, v==='RISK-ON'?'good':(v==='RISK-OFF'?'bad':'warn')); }}
function supertrendHtml(v){{ return badgeHtml(String(v||'BAD').toUpperCase()==='GOOD'?'GOOD':'BAD', String(v||'BAD').toUpperCase()==='GOOD'?'good':'bad'); }}
function tierHtml(v){{ return badgeHtml(v, v==='CONFIRMED'?'strong':(v==='FRESH'?'fresh':(v==='EARLY'?'warn':'muted'))); }}
function stateHtml(v){{ return badgeHtml(v, v==='STRONG LONG'?'strong':(['LONG','POSITIVE'].includes(v)?'good':(['WEAK','BEARISH'].includes(v)?'bad':'muted'))); }}
function setupHtml(v){{ return badgeHtml(v, v==='A+'?'strong':(v==='A'?'good':(v==='B'?'fresh':(v==='EARLY'?'warn':'muted')))); }}

const CURRENT_GENERATED_AT = document.querySelector('meta[name="data-generated-at"]')?.content || '';
let refreshInFlight = false;
let toastTimer = null;
function showRefreshToast(message){{
  const el=document.getElementById('refresh-toast'); if(!el)return;
  el.textContent=message; el.classList.add('show');
  clearTimeout(toastTimer); toastTimer=setTimeout(()=>el.classList.remove('show'),2600);
}}
function setRefreshLoading(on){{
  const btn=document.getElementById('refresh-btn'); const icon=document.getElementById('refresh-icon');
  if(btn)btn.classList.toggle('loading',on); if(icon)icon.textContent=on?'⋯':'↻';
}}
function updateLastCheck(){{
  const el=document.getElementById('last-check-text');
  if(el)el.textContent='마지막 확인: '+new Date().toLocaleTimeString('ko-KR',{{hour:'2-digit',minute:'2-digit'}});
}}
async function checkForLatest(manual=false){{
  if(refreshInFlight)return; refreshInFlight=true; setRefreshLoading(true);
  try{{
    const url=new URL(window.location.href); url.searchParams.set('_refresh',Date.now().toString());
    const res=await fetch(url.toString(),{{cache:'no-store',headers:{{'Cache-Control':'no-cache'}}}});
    if(!res.ok) throw new Error('HTTP '+res.status);
    const htmlText=await res.text();
    const parsed=new DOMParser().parseFromString(htmlText,'text/html');
    const remoteGenerated=parsed.querySelector('meta[name="data-generated-at"]')?.content || '';
    updateLastCheck();
    if(remoteGenerated && remoteGenerated!==CURRENT_GENERATED_AT){{
      if(manual)showRefreshToast('새 종가 데이터가 확인되었습니다. 페이지를 갱신합니다.');
      const clean=new URL(window.location.href); clean.searchParams.delete('_refresh'); clean.searchParams.set('_v',Date.now().toString());
      setTimeout(()=>window.location.replace(clean.toString()), manual?450:0);
      return;
    }}
    if(manual)showRefreshToast('이미 최신 데이터입니다. · '+(CURRENT_GENERATED_AT||'업데이트 시간 확인 불가'));
  }}catch(err){{
    if(manual)showRefreshToast('최신 데이터 확인에 실패했습니다. 네트워크를 확인해 주세요.');
  }}finally{{ refreshInFlight=false; setRefreshLoading(false); }}
}}
// 페이지를 오래 열어둔 경우에도 5분마다 새 배포본을 확인합니다.
setInterval(()=>checkForLatest(false),5*60*1000);

function findStocks(q, market='ALL'){{
  q=(q||'').toLowerCase().replace(/\\s+/g,'').trim();
  if(!q) return [];
  return STOCKS.filter(s=>{{
    if(market!=='ALL' && s.market!==market) return false;
    const name=String(s.name||'').toLowerCase().replace(/\\s+/g,'');
    const ticker=String(s.ticker||'').padStart(6,'0');
    return name.includes(q) || ticker.includes(q);
  }}).sort((a,b)=>{{
    const aq=String(a.ticker||'').padStart(6,'0')===q || String(a.name||'').toLowerCase().replace(/\\s+/g,'')===q;
    const bq=String(b.ticker||'').padStart(6,'0')===q || String(b.name||'').toLowerCase().replace(/\\s+/g,'')===q;
    if(aq!==bq) return aq?-1:1;
    return Number(b.alpha_score||0)-Number(a.alpha_score||0);
  }});
}}

function onStockInput(){{
  const q=document.getElementById('stock-search').value;
  const market=document.getElementById('stock-market').value;
  const box=document.getElementById('stock-suggestions');
  suggestionIndex=-1;
  currentMatches=findStocks(q,market).slice(0,12);
  if(!q.trim() || currentMatches.length===0){{ box.style.display='none'; box.innerHTML=''; return; }}
  box.innerHTML=currentMatches.map((s,i)=>`<div class="suggestion" data-i="${{i}}" onmousedown="selectSuggestion(${{i}})"><div><b>${{escJs(s.name)}}</b><br><small>${{escJs(String(s.ticker).padStart(6,'0'))}} · ${{escJs(s.market)}}</small></div><small>Alpha ${{num(s.alpha_score,1)}} · Entry ${{num(s.entry_score,1)}} · ST ${{escJs(s.supertrend_status||'BAD')}} · #${{s.alpha_rank_all}}</small></div>`).join('');
  box.style.display='block';
}}
function selectSuggestion(i){{ const s=currentMatches[i]; if(!s)return; document.getElementById('stock-search').value=s.name; document.getElementById('stock-suggestions').style.display='none'; renderStock(s); }}
function onStockKey(e){{
  const box=document.getElementById('stock-suggestions');
  if(e.key==='ArrowDown' && currentMatches.length){{ e.preventDefault(); suggestionIndex=Math.min(suggestionIndex+1,currentMatches.length-1); refreshActiveSuggestion(); }}
  else if(e.key==='ArrowUp' && currentMatches.length){{ e.preventDefault(); suggestionIndex=Math.max(suggestionIndex-1,0); refreshActiveSuggestion(); }}
  else if(e.key==='Enter'){{ e.preventDefault(); if(suggestionIndex>=0)selectSuggestion(suggestionIndex); else runStockSearch(); }}
  else if(e.key==='Escape'){{ box.style.display='none'; }}
}}
function refreshActiveSuggestion(){{ document.querySelectorAll('#stock-suggestions .suggestion').forEach((el,i)=>el.classList.toggle('active',i===suggestionIndex)); }}
function runStockSearch(){{
  const q=document.getElementById('stock-search').value;
  const market=document.getElementById('stock-market').value;
  const matches=findStocks(q,market);
  document.getElementById('stock-suggestions').style.display='none';
  if(matches.length===0){{ document.getElementById('stock-result').className='result-empty'; document.getElementById('stock-result').innerHTML='해당 종목을 찾지 못했습니다. 현재 분석 유니버스에 포함된 종목인지 확인해 주세요.'; return; }}
  renderStock(matches[0]);
}}
function scoreBox(k,v,cls=''){{ return `<div class="score-box ${{cls}}"><div class="k">${{k}}</div><div class="v">${{num(v,1)}}</div><div class="bar"><i style="width:${{Math.max(0,Math.min(100,Number(v)||0))}}%"></i></div></div>`; }}
function item(k,v){{ return `<div class="result-item"><b>${{k}}</b><span>${{v}}</span></div>`; }}
function renderStock(s){{
  const ret=Number(s.daily_return_pct||0);
  const retCls=ret>0?'up':(ret<0?'down':'');
  const ticker=String(s.ticker||'').padStart(6,'0');
  const top60=Number(s.alpha_rank_all)<=60;
  const result=document.getElementById('stock-result');
  result.className='stock-card';
  result.innerHTML=`
    <div class="stock-head">
      <div class="stock-title"><h3>${{escJs(s.name)}}</h3><div class="meta">${{ticker}} · ${{escJs(s.market)}} · 기준일 ${{escJs(s.signal_date||'-')}}</div><div style="margin-top:9px">${{tierHtml(s.signal_tier)}} ${{setupHtml(s.setup_grade)}} ${{stateHtml(s.signal_state)}} ${{regimeHtml(s.regime)}} ${{supertrendHtml(s.supertrend_status)}}</div></div>
      <div class="stock-price"><strong>${{price(s.close)}}원</strong><span class="${{retCls}}">${{ret>=0?'+':''}}${{num(ret,2)}}%</span><div style="margin-top:8px"><span class="rank-pill">전체 Alpha #${{s.alpha_rank_all}}</span><span class="rank-pill">${{escJs(s.market)}} #${{s.alpha_rank_market}}</span>${{top60?'<span class="rank-pill">TOP 60</span>':''}}</div></div>
    </div>
    <div class="score-grid">
      ${{scoreBox('Alpha',s.alpha_score,'alpha-box')}}
      ${{scoreBox('Entry',s.entry_score)}}
      ${{scoreBox('Trend',s.trend_score)}}
      ${{scoreBox('Momentum',s.momentum_score)}}
      ${{scoreBox('Flow',s.flow_score)}}
      ${{scoreBox('Relative Strength',s.rs_score)}}
      ${{scoreBox('Risk',s.risk_score)}}
    </div>
    <div class="result-grid">
      ${{item('CCI',num(s.cci,1))}}
      ${{item('CCI 3D Δ',num(s.cci_delta3,1))}}
      ${{item('CCI Cross',crossLabel(s.cci_cross_age))}}
      ${{item('+DI / -DI',num(s.plus_di,1)+' / '+num(s.minus_di,1))}}
      ${{item('DMI Ratio',num(s.dmi_ratio,2)+'x')}}
      ${{item('ADX',num(s.adx,1))}}
      ${{item('ADX 3D Δ',num(s.adx_delta3,1))}}
      ${{item('Supertrend',supertrendHtml(s.supertrend_status))}}
      ${{item('ST Flip',crossLabel(s.supertrend_flip_age))}}
      ${{item('ST Dist / ATR',num(s.supertrend_distance_atr,2)+'x')}}
      ${{item('Entry Score',num(s.entry_score,1))}}
      ${{item('Dollar Vol',num(s.relative_dollar_volume,2)+'x')}}
      ${{item('ADV20',bn(s.avg20_trading_value))}}
      ${{item('RS20 excess',num(s.rs20_excess_pct,2)+'%')}}
      ${{item('RS60 excess',num(s.rs60_excess_pct,2)+'%')}}
      ${{item('RS20 percentile',num(s.rs20_percentile,1))}}
      ${{item('RS60 percentile',num(s.rs60_percentile,1))}}
      ${{item('ATR%',num(s.atr_pct,2)+'%')}}
      ${{item('20D vol ann.',num(s.vol20_ann_pct,1)+'%')}}
      ${{item('Risk Level',riskHtml(s.risk_level))}}
      ${{item('MA20',s.above_ma20?'Above':'Below')}}
      ${{item('MA60',s.above_ma60?'Above':'Below')}}
      ${{item('Active Trend',s.active_trend?'YES':'NO')}}
      ${{item('Signal Tier',tierHtml(s.signal_tier))}}
    </div>`;
}}

function filterRankRows(){{
  const q=(document.getElementById('rank-search')?.value||'').toLowerCase().trim();
  const market=document.getElementById('rank-market')?.value||'ALL';
  const minAlpha=parseFloat(document.getElementById('rank-alpha')?.value||'0');
  document.querySelectorAll('#rank-table tbody tr').forEach(tr=>{{
    const text=(tr.dataset.name||'')+' '+(tr.dataset.ticker||'');
    const okQ=!q||text.includes(q);
    const okM=market==='ALL'||tr.dataset.market===market;
    const okA=parseFloat(tr.dataset.alpha||'0')>=minAlpha;
    tr.style.display=(okQ&&okM&&okA)?'':'none';
  }});
}}

document.addEventListener('click',e=>{{ if(!e.target.closest('.search-wrap')) document.getElementById('stock-suggestions').style.display='none'; }});
</script>
</body></html>'''

    (docs / "index.html").write_text(page, encoding="utf-8")
    print("Generated docs/index.html")


if __name__ == "__main__":
    main()
