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
        return badge("B", "warn")
    if value == "WATCH":
        return badge("WATCH", "muted")
    return badge("-", "muted")


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
        f"<div><b>ADX</b><span>{fmt(r.get('adx'))}</span></div>"
        f"<div><b>ADX 3D Δ</b><span>{fmt(r.get('adx_delta3'))}</span></div>"
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
            f"<td>{fmt_price(r.get('close'))}</td>"
            f"<td class='{ret_class}'>{fmt(ret,2)}%</td>"
            f"<td class='alpha'>{score_cell(r.get('alpha_score'))}</td>"
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


def make_table(df, table_id):
    if df.empty:
        return "<div class='empty'>조건을 만족한 종목이 없습니다.</div>"
    return (
        f"<div class='table-wrap'><table id='{table_id}'><thead><tr>"
        "<th>#</th><th>종목</th><th>종가</th><th>등락</th><th>Alpha</th>"
        "<th>Trend</th><th>Momentum</th><th>Flow</th><th>RS</th><th>Risk</th>"
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


def main():
    results = Path("results")
    docs = Path("docs")
    docs.mkdir(exist_ok=True)

    summary = json.loads((results / "summary.json").read_text(encoding="utf-8"))
    all_df = pd.read_csv(results / "latest_all_scored.csv")
    buy = pd.read_csv(results / "latest_buy_signals.csv")
    top = all_df.sort_values("alpha_score", ascending=False).head(60)
    p = summary["parameters"]
    w = summary.get("weights", {})
    regimes = summary.get("regimes", {})

    buy_html = make_table(buy, "buy-table")
    top_html = make_table(top, "rank-table")

    page = f'''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="900">
<title>Korea Equity Alpha Screener V2</title>
<style>
:root{{--bg:#080b10;--panel:#0f151d;--panel2:#131c27;--line:#233042;--text:#edf3f8;--muted:#91a1b2;--accent:#83b8ff;--green:#53d49a;--red:#ff7b86;--yellow:#f1c66a;--purple:#bd8cff}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font-family:Inter,Pretendard,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
.wrap{{max-width:1500px;margin:0 auto;padding:24px}}.hero{{background:linear-gradient(145deg,#121c28,#0c1118);border:1px solid var(--line);border-radius:22px;padding:24px;box-shadow:0 20px 50px rgba(0,0,0,.22)}}
.eyebrow{{font-size:12px;letter-spacing:.14em;color:var(--accent);font-weight:800}}h1{{font-size:30px;margin:7px 0 8px}}h2{{font-size:20px;margin:30px 0 12px}}.sub,.muted{{color:var(--muted);font-size:13px;line-height:1.6}}
.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:18px}}.stat{{background:#0b1118;border:1px solid var(--line);border-radius:15px;padding:15px}}.stat .v{{font-size:25px;font-weight:800}}.stat .k{{font-size:12px;color:var(--muted);margin-top:4px}}
.regime-grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:14px}}.regime-card{{background:#0b1118;border:1px solid var(--line);border-radius:15px;padding:15px}}.regime-head{{display:flex;justify-content:space-between;align-items:center}}.regime-score{{font-size:26px;font-weight:800;margin:10px 0 4px}}
.model-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:12px}}.model-card{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:14px}}.model-card strong{{font-size:18px}}.model-card p{{margin:6px 0 0;color:var(--muted);font-size:12px;line-height:1.5}}
.toolbar{{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 12px}}input,select{{background:#0d141d;border:1px solid var(--line);color:var(--text);border-radius:10px;padding:9px 11px;outline:none}}input{{min-width:240px}}.table-wrap{{overflow:auto;border:1px solid var(--line);border-radius:16px;background:var(--panel)}}table{{width:100%;border-collapse:collapse;min-width:1380px}}th,td{{padding:11px 9px;border-bottom:1px solid #1e2a38;text-align:right;white-space:nowrap;vertical-align:middle}}th{{font-size:11px;color:var(--muted);background:#0b1118;position:sticky;top:0;z-index:2}}td{{font-size:12px}}th:nth-child(2),td.name{{text-align:left}}td.name b{{display:block;font-size:13px}}td.name small{{display:block;color:var(--muted);margin-top:3px}}tr:hover td{{background:#111a24}}tr:last-child td{{border-bottom:none}}
.metric{{min-width:72px}}.metric>span{{font-weight:800}}.alpha .metric>span{{color:var(--accent);font-size:14px}}.bar{{height:3px;background:#1b2735;border-radius:99px;margin-top:5px;overflow:hidden}}.bar i{{display:block;height:100%;background:linear-gradient(90deg,#5f91d9,#9ec8ff)}}
.badge{{display:inline-flex;align-items:center;border:1px solid var(--line);border-radius:999px;padding:4px 8px;font-size:10px;font-weight:800;letter-spacing:.03em}}.badge.good{{color:var(--green);border-color:rgba(83,212,154,.35);background:rgba(83,212,154,.07)}}.badge.bad{{color:var(--red);border-color:rgba(255,123,134,.35);background:rgba(255,123,134,.07)}}.badge.warn{{color:var(--yellow);border-color:rgba(241,198,106,.35);background:rgba(241,198,106,.07)}}.badge.strong{{color:var(--purple);border-color:rgba(189,140,255,.40);background:rgba(189,140,255,.09)}}.badge.muted{{color:#aeb9c6}}.up{{color:var(--green)}}.down{{color:var(--red)}}
details{{text-align:left}}summary{{cursor:pointer;color:var(--accent)}}.detail-grid{{position:absolute;right:26px;z-index:20;margin-top:8px;display:grid;grid-template-columns:repeat(3,150px);gap:8px;background:#0c121a;border:1px solid var(--line);border-radius:13px;padding:12px;box-shadow:0 16px 45px rgba(0,0,0,.45)}}.detail-grid div{{display:flex;flex-direction:column;gap:4px}}.detail-grid b{{font-size:10px;color:var(--muted)}}.detail-grid span{{font-size:12px}}
.note{{margin-top:24px;background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:17px;color:var(--muted);font-size:12px;line-height:1.75}}.empty{{padding:24px;text-align:center;color:var(--muted);background:var(--panel);border:1px dashed var(--line);border-radius:16px}}
@media(max-width:850px){{.wrap{{padding:12px}}h1{{font-size:24px}}.grid,.model-grid,.regime-grid{{grid-template-columns:1fr 1fr}}.detail-grid{{position:fixed;left:12px;right:12px;bottom:12px;grid-template-columns:repeat(2,1fr)}}}}@media(max-width:520px){{.grid,.model-grid,.regime-grid{{grid-template-columns:1fr}}}}
</style>
</head>
<body><div class="wrap">
<section class="hero">
<div class="eyebrow">HF TECHNICAL ALPHA · V2</div>
<h1>Korea Equity Alpha Screener</h1>
<div class="sub">기준일 {esc(summary.get('latest_signal_date','-'))} · 생성 {esc(summary.get('generated_at','-'))}<br>KOSPI 시총 상위 {p.get('kospi_n',200)} + KOSDAQ 시총 상위 {p.get('kosdaq_n',150)} · Alpha와 Risk를 분리해 표시</div>
<div class="grid">
<div class="stat"><div class="v">{summary.get('fresh_buy_count',0)}</div><div class="k">신규 매수 후보 · KOSPI {summary.get('fresh_buy_count_kospi',0)} / KOSDAQ {summary.get('fresh_buy_count_kosdaq',0)}</div></div>
<div class="stat"><div class="v">{summary.get('active_trend_count',0)}</div><div class="k">DMI + CCI 상승추세 유지</div></div>
<div class="stat"><div class="v">{summary.get('symbols_scored',0)}</div><div class="k">최종 분석 종목</div></div>
<div class="stat"><div class="v">≥ {p.get('buy_alpha_threshold',70):.0f}</div><div class="k">신규매수 Alpha threshold</div></div>
</div>
<div class="regime-grid">{regime_card('KOSPI', regimes.get('KOSPI',{}))}{regime_card('KOSDAQ', regimes.get('KOSDAQ',{}))}</div>
</section>

<h2>Model Architecture</h2>
<div class="model-grid">
<div class="model-card"><strong>Trend {w.get('trend',30)}%</strong><p>DMI 방향성 + ADX 강도 + ADX 가속도. ADX를 방향 신호가 아닌 추세 확신도로 사용.</p></div>
<div class="model-card"><strong>Momentum {w.get('momentum',25)}%</strong><p>CCI 0선 돌파 신선도 + 3일 기울기 + 과열을 제한한 CCI 레벨.</p></div>
<div class="model-card"><strong>Flow {w.get('flow',20)}%</strong><p>일봉 CVD proxy 기울기/EMA 위치 + 상대 거래대금. 실제 체결 CVD와는 구분.</p></div>
<div class="model-card"><strong>Relative Strength {w.get('relative_strength',25)}%</strong><p>KOSPI/KOSDAQ 벤치마크 대비 20·60일 초과수익률의 시장 내 percentile.</p></div>
</div>

<h2>오늘 신규 매수 후보</h2>
<div class="sub" style="margin-bottom:10px">최근 2거래일 CCI 0선 돌파 + DMI/ADX + Flow + Alpha 조건을 모두 통과한 종목.</div>
{buy_html}

<h2>Alpha Ranking · Top 60</h2>
<div class="toolbar">
<input id="search" placeholder="종목명 또는 종목코드 검색" oninput="filterRows()">
<select id="market" onchange="filterRows()"><option value="ALL">전체 시장</option><option value="KOSPI">KOSPI</option><option value="KOSDAQ">KOSDAQ</option></select>
<select id="alpha" onchange="filterRows()"><option value="0">Alpha 전체</option><option value="60">60+</option><option value="70">70+</option><option value="80">80+</option></select>
</div>
{top_html}

<div class="note"><b>Alpha Score</b>는 예측확률이 아니라 0~100 범위의 기술적 랭킹 점수입니다. Trend 30% + Momentum 25% + Flow 20% + Relative Strength 25%로 계산하며 Risk는 Alpha에서 분리합니다.<br>
<b>신규 매수 후보</b>: CCI가 오늘 또는 직전 거래일에 0선을 상향돌파하고, 현재 CCI &gt; 0, +DI &gt; -DI, ADX ≥ {p.get('adx_threshold',20)}, Flow ≥ 50, Alpha ≥ {p.get('buy_alpha_threshold',70)} 조건을 만족해야 합니다.<br>
<b>Regime</b>: 지수의 20/60일 이동평균 구조와 종목 breadth를 합쳐 RISK-ON / NEUTRAL / RISK-OFF로 분류합니다. Regime은 Alpha 자체를 깎지 않고 별도 conviction 정보로 제공합니다.<br>
<b>Flow</b>의 CVD는 Yahoo 일봉 OHLCV로 만든 proxy이며 실제 bid/ask 체결 CVD가 아닙니다.</div>
</div>
<script>
function filterRows(){{
  const q=(document.getElementById('search')?.value||'').toLowerCase().trim();
  const market=document.getElementById('market')?.value||'ALL';
  const minAlpha=parseFloat(document.getElementById('alpha')?.value||'0');
  document.querySelectorAll('#rank-table tbody tr').forEach(tr=>{{
    const text=(tr.dataset.name||'')+' '+(tr.dataset.ticker||'');
    const okQ=!q||text.includes(q);
    const okM=market==='ALL'||tr.dataset.market===market;
    const okA=parseFloat(tr.dataset.alpha||'0')>=minAlpha;
    tr.style.display=(okQ&&okM&&okA)?'':'none';
  }});
}}
</script>
</body></html>'''

    (docs / "index.html").write_text(page, encoding="utf-8")
    print("Generated docs/index.html")


if __name__ == "__main__":
    main()
