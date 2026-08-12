#!/usr/bin/env python3
from __future__ import annotations
import html, json
from pathlib import Path
import pandas as pd

def esc(x):
    return html.escape(str(x))

def fmt(v, d=1):
    try: return f"{float(v):,.{d}f}"
    except: return "-"

def fmt_price(v):
    try: return f"{int(round(float(v))):,}"
    except: return "-"

def table_rows(df, mode="buy"):
    out=[]
    for i, (_, r) in enumerate(df.iterrows(), start=1):
        cvd = "강세" if bool(r.get("cvd_bull", False)) else "중립/약세"
        if mode == "buy":
            out.append(
                f"<tr><td>{i}</td><td class='name'>{esc(r['name'])}</td>"
                f"<td>{str(r['ticker']).zfill(6)}</td><td>{fmt_price(r['close'])}</td>"
                f"<td>{fmt(r['daily_return_pct'],2)}%</td><td>{fmt(r['cci'])}</td>"
                f"<td>{fmt(r['plus_di'])}</td><td>{fmt(r['minus_di'])}</td>"
                f"<td>{fmt(r['adx'])}</td><td>{cvd}</td>"
                f"<td class='score'>{fmt(r['signal_score'])}</td></tr>"
            )
        else:
            out.append(
                f"<tr><td>{i}</td><td class='name'>{esc(r['name'])}</td>"
                f"<td>{str(r['ticker']).zfill(6)}</td><td>{fmt_price(r['close'])}</td>"
                f"<td>{fmt(r['cci'])}</td><td>{fmt(r['adx'])}</td>"
                f"<td>{cvd}</td><td class='score'>{fmt(r['signal_score'])}</td></tr>"
            )
    return "".join(out)

def main():
    results=Path("results"); docs=Path("docs"); docs.mkdir(exist_ok=True)
    summary=json.loads((results/"summary.json").read_text(encoding="utf-8"))
    buy=pd.read_csv(results/"latest_buy_signals.csv")
    active=pd.read_csv(results/"latest_active_trends.csv").head(30)
    p=summary["parameters"]

    if buy.empty:
        buy_html="<div class='empty'>오늘 신규 매수 조건을 만족한 종목이 없습니다.</div>"
    else:
        buy_html=(
            "<div class='table-wrap'><table><thead><tr>"
            "<th>#</th><th>종목</th><th>코드</th><th>종가</th><th>등락률</th>"
            "<th>CCI</th><th>+DI</th><th>-DI</th><th>ADX</th><th>CVD</th><th>점수</th>"
            "</tr></thead><tbody>"+table_rows(buy,"buy")+"</tbody></table></div>"
        )

    if active.empty:
        active_html="<div class='empty'>현재 상승추세 유지 조건을 만족한 종목이 없습니다.</div>"
    else:
        active_html=(
            "<div class='table-wrap'><table><thead><tr>"
            "<th>#</th><th>종목</th><th>코드</th><th>종가</th>"
            "<th>CCI</th><th>ADX</th><th>CVD</th><th>점수</th>"
            "</tr></thead><tbody>"+table_rows(active,"active")+"</tbody></table></div>"
        )

    page=f'''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="900">
<title>KOSPI Signal Screener</title>
<style>
:root{{--bg:#0b0f14;--panel:#111820;--panel2:#151e28;--text:#e8edf2;--muted:#8ea0b3;--line:#24303d;--accent:#7db7ff;}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--text);font-family:Inter,Pretendard,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
.wrap{{max-width:1180px;margin:0 auto;padding:22px}} .hero{{background:linear-gradient(180deg,var(--panel2),var(--panel));border:1px solid var(--line);border-radius:18px;padding:22px;margin-bottom:18px}}
h1{{margin:0 0 8px;font-size:26px}} h2{{margin:26px 0 10px;font-size:19px}} .sub{{color:var(--muted);font-size:14px;line-height:1.6}}
.chips{{display:flex;flex-wrap:wrap;gap:8px;margin-top:15px}} .chip{{border:1px solid var(--line);background:#0f151c;border-radius:999px;padding:7px 11px;font-size:13px;color:#cbd6e2}}
.stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:16px}} .stat{{background:#0f151c;border:1px solid var(--line);border-radius:13px;padding:13px}}
.stat .v{{font-size:22px;font-weight:700}} .stat .k{{font-size:12px;color:var(--muted);margin-top:3px}}
.table-wrap{{overflow:auto;border:1px solid var(--line);border-radius:14px}} table{{width:100%;border-collapse:collapse;min-width:820px;background:var(--panel)}}
th,td{{padding:11px 10px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}} th{{font-size:12px;color:var(--muted);background:#0f151c;position:sticky;top:0}}
td{{font-size:13px}} th:nth-child(2),td.name{{text-align:left}} tr:last-child td{{border-bottom:none}} .score{{font-weight:700;color:var(--accent)}}
.empty{{border:1px dashed var(--line);border-radius:14px;color:var(--muted);padding:22px;text-align:center;background:var(--panel)}}
.note{{margin-top:22px;border:1px solid var(--line);border-radius:14px;background:var(--panel);padding:16px;color:var(--muted);font-size:13px;line-height:1.7}}
@media(max-width:700px){{.wrap{{padding:12px}}.stats{{grid-template-columns:1fr}}h1{{font-size:22px}}}}
</style>
</head>
<body>
<div class="wrap">
<section class="hero">
<h1>KOSPI CCI + DMI Signal Screener</h1>
<div class="sub">기준일 {esc(summary.get("latest_signal_date","-"))} · 생성 {esc(summary.get("generated_at","-"))}<br>KOSPI 시가총액 상위 {p.get("top_n",200)} 종목 대상</div>
<div class="chips">
<div class="chip">CCI({p.get("cci_period",9)}) 0선 상향돌파</div>
<div class="chip">+DI &gt; -DI</div>
<div class="chip">ADX({p.get("dmi_period",14)}) ≥ {p.get("adx_threshold",20)}</div>
<div class="chip">CVD = 참고 점수</div>
</div>
<div class="stats">
<div class="stat"><div class="v">{summary.get("fresh_buy_count",0)}</div><div class="k">신규 매수 신호</div></div>
<div class="stat"><div class="v">{summary.get("active_trend_count",0)}</div><div class="k">상승추세 유지</div></div>
<div class="stat"><div class="v">{summary.get("symbols_scored",0)}</div><div class="k">분석 완료 종목</div></div>
</div>
</section>
<h2>오늘 신규 매수 신호</h2>
{buy_html}
<h2>현재 상승추세 유지 종목</h2>
<div class="sub" style="margin-bottom:10px">점수 상위 30개만 표시합니다.</div>
{active_html}
<div class="note"><b>신호 정의</b>: CCI가 당일 처음 0선을 상향 돌파하고 +DI &gt; -DI, ADX 기준을 동시에 만족할 때 신규 신호로 분류합니다.<br>
<b>CVD</b>: 일봉 OHLCV 기반 proxy이며 실제 bid/ask 체결 CVD와 동일하지 않습니다.</div>
</div>
</body>
</html>'''
    (docs/"index.html").write_text(page,encoding="utf-8")
    print("Generated docs/index.html")

if __name__=="__main__":
    main()
