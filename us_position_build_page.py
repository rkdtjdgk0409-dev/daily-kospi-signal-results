#!/usr/bin/env python3
from __future__ import annotations

import html
from pathlib import Path

import pandas as pd

CSV = Path("us_results/latest_position_management.csv")
DOCS = Path("docs/us-position")


def esc(x):
    return html.escape(str(x))


def num(x, d=1):
    try:
        return f"{float(x):,.{d}f}"
    except Exception:
        return "-"


def price(x):
    try:
        return f"${float(x):,.2f}"
    except Exception:
        return "-"


def badge(s):
    s = str(s)
    cls = {
        "STRONG HOLD": "strong",
        "HOLD": "hold",
        "WATCH": "watch",
        "TAKE PROFIT": "profit",
        "EXIT": "exit",
        "STOP": "stop",
    }.get(s, "watch")
    return f'<span class="badge {cls}">{esc(s)}</span>'


def build_card(r):
    pnl = float(r.get("pnl_pct", 0) or 0)
    pnl_cls = "up" if pnl > 0 else ("down" if pnl < 0 else "")
    ticker = str(r.get("ticker", "")).upper()
    return f"""
    <article class="card" data-status="{esc(r.get('position_status',''))}" data-name="{esc(str(r.get('name','')).lower())}" data-ticker="{ticker.lower()}">
      <div class="head">
        <div><h3>{esc(r.get('name','-'))}</h3><p>{ticker} · {esc(r.get('market',''))} · Entry {esc(r.get('entry_date','-'))}</p></div>
        {badge(r.get('position_status',''))}
      </div>
      <div class="hero-grid">
        <div><span>Current</span><b>{price(r.get('close'))}</b></div>
        <div><span>Entry</span><b>{price(r.get('entry_price'))}</b></div>
        <div><span>Return</span><b class="{pnl_cls}">{pnl:+.2f}%</b></div>
        <div><span>Exit Risk</span><b>{num(r.get('exit_risk'))}</b></div>
      </div>
      <div class="levels">
        <div><span>Initial Stop</span><b>{price(r.get('initial_stop'))}</b></div>
        <div><span>Trailing Stop</span><b>{price(r.get('trailing_stop'))}</b></div>
        <div><span>Highest Close</span><b>{price(r.get('highest_close'))}</b></div>
        <div><span>From Peak</span><b>{num(r.get('drawdown_from_peak_pct'),2)}%</b></div>
      </div>
      <div class="reason"><b>Decision</b> {esc(r.get('position_reason',''))}</div>
      <div class="riskparts">
        ST {num(r.get('exit_st_risk'))} · DMI {num(r.get('exit_dmi_risk'))} ·
        ADX {num(r.get('exit_adx_risk'))} · CCI {num(r.get('exit_cci_risk'))} ·
        Alpha {num(r.get('exit_alpha_risk'))} · Regime {num(r.get('exit_regime_risk'))}
      </div>
    </article>
    """


def main():
    DOCS.mkdir(parents=True, exist_ok=True)
    if CSV.exists() and CSV.stat().st_size > 0:
        try:
            df = pd.read_csv(CSV, dtype={"ticker": str})
        except pd.errors.EmptyDataError:
            df = pd.DataFrame()
    else:
        df = pd.DataFrame()

    counts = df["position_status"].value_counts().to_dict() if not df.empty else {}
    cards = "".join(build_card(r) for _, r in df.iterrows()) if not df.empty else '<div class="empty">No tracked US positions yet. A CONFIRMED signal will be registered automatically.</div>'

    page = f"""<!doctype html>
<html lang="ko"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#07101f"><title>US Position Management</title>
<style>
:root{{--bg:#07101f;--panel:#0d182a;--line:#22324b;--text:#eef4ff;--muted:#8ea1bb;--blue:#4d8dff;--green:#38d488;--red:#ff6475;--yellow:#f8bc52;--cyan:#33d6c2}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font-family:Inter,Pretendard,system-ui,-apple-system,sans-serif}}
.wrap{{max-width:1280px;margin:auto;padding:22px}}.hero{{background:linear-gradient(145deg,#111f35,#091323);border:1px solid var(--line);border-radius:22px;padding:22px}}
.nav{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:18px}}.nav a{{text-decoration:none;color:var(--muted);border:1px solid var(--line);padding:9px 12px;border-radius:11px;font-weight:800}}
.nav a.active{{color:var(--blue);border-color:rgba(77,141,255,.45);background:rgba(77,141,255,.08)}}
.eyebrow{{font-size:11px;letter-spacing:.13em;color:var(--cyan);font-weight:900}}h1{{font-size:32px;margin:8px 0}}.sub{{color:var(--muted);font-size:12px;line-height:1.6}}
.summary{{display:grid;grid-template-columns:repeat(5,1fr);gap:9px;margin-top:18px}}.stat{{background:#091426;border:1px solid var(--line);border-radius:14px;padding:13px}}.stat b{{font-size:23px;display:block}}.stat span{{font-size:10px;color:var(--muted)}}
.toolbar{{display:flex;gap:8px;flex-wrap:wrap;margin:18px 0}}input,button{{font:inherit}}input{{flex:1;min-width:220px;background:#091426;color:var(--text);border:1px solid var(--line);border-radius:10px;padding:10px 12px}}
button{{border:1px solid var(--line);background:#101f36;color:var(--muted);padding:9px 12px;border-radius:999px;font-weight:800;cursor:pointer}}button.active{{color:var(--text);border-color:rgba(77,141,255,.5);background:rgba(77,141,255,.1)}}
.list{{display:grid;grid-template-columns:repeat(2,1fr);gap:11px}}.card{{background:linear-gradient(145deg,#111f35,#091323);border:1px solid var(--line);border-radius:17px;padding:16px}}
.head{{display:flex;justify-content:space-between;gap:10px}}h3{{margin:0;font-size:18px}}.head p{{margin:4px 0 0;color:var(--muted);font-size:10px}}
.badge{{font-size:10px;font-weight:900;border-radius:999px;padding:6px 9px;height:max-content;border:1px solid var(--line)}}.strong,.hold{{color:var(--green);border-color:rgba(56,212,136,.4);background:rgba(56,212,136,.08)}}.watch{{color:var(--yellow);border-color:rgba(248,188,82,.4);background:rgba(248,188,82,.08)}}.profit{{color:var(--cyan)}}.exit,.stop{{color:var(--red)}}
.hero-grid,.levels{{display:grid;grid-template-columns:repeat(4,1fr);gap:7px;margin-top:12px}}.hero-grid div,.levels div{{background:#091426;border:1px solid #1d304a;border-radius:10px;padding:9px}}
.hero-grid span,.levels span{{display:block;color:var(--muted);font-size:9px;margin-bottom:4px}}.hero-grid b{{font-size:16px}}.levels b{{font-size:11px}}.up{{color:var(--green)}}.down{{color:var(--red)}}
.reason{{margin-top:10px;border-left:3px solid var(--blue);background:rgba(77,141,255,.06);padding:10px;border-radius:8px;font-size:11px;line-height:1.6}}.reason b{{color:var(--blue)}}.riskparts{{margin-top:8px;color:var(--muted);font-size:9px}}
.empty{{grid-column:1/-1;text-align:center;padding:35px;color:var(--muted);border:1px dashed var(--line);border-radius:15px}}.note{{margin-top:20px;color:var(--muted);font-size:10px;line-height:1.7}}
@media(max-width:800px){{.wrap{{padding:12px}}h1{{font-size:25px}}.summary{{grid-template-columns:repeat(2,1fr)}}.list{{grid-template-columns:1fr}}.hero-grid,.levels{{grid-template-columns:repeat(2,1fr)}}}}
</style></head><body><div class="wrap"><section class="hero">
<div class="nav"><a href="../">한국 시장</a><a href="../us/">미국 시장</a><a class="active" href="./">포지션 관리</a><a href="../us-price-structure/">차트 구조</a></div>
<div class="eyebrow">US POSITION MANAGEMENT · DAILY CLOSE</div><h1>US Position Management</h1>
<div class="sub">미국 스크리너의 CONFIRMED 발생일 종가를 가상 진입가로 저장하고 이후 정규장 종가 기준으로 HOLD · WATCH · TAKE PROFIT · EXIT · STOP을 별도 추적합니다. 한국 포지션 상태와 완전히 분리된 state/us_position_state.json을 사용합니다.</div>
<div class="summary">
<div class="stat"><b>{counts.get('STRONG HOLD',0)+counts.get('HOLD',0)}</b><span>HOLD</span></div>
<div class="stat"><b>{counts.get('WATCH',0)}</b><span>WATCH</span></div>
<div class="stat"><b>{counts.get('TAKE PROFIT',0)}</b><span>TAKE PROFIT</span></div>
<div class="stat"><b>{counts.get('EXIT',0)}</b><span>EXIT</span></div>
<div class="stat"><b>{counts.get('STOP',0)}</b><span>STOP</span></div>
</div></section>
<div class="toolbar"><input id="q" placeholder="Ticker or company name" oninput="filterCards()"><button class="active" onclick="setStatus('ALL',this)">전체</button><button onclick="setStatus('STRONG HOLD,HOLD',this)">HOLD</button><button onclick="setStatus('WATCH',this)">WATCH</button><button onclick="setStatus('TAKE PROFIT',this)">TAKE PROFIT</button><button onclick="setStatus('EXIT,STOP',this)">EXIT / STOP</button></div>
<div class="list">{cards}</div>
<div class="note">미국 포지션 관리 페이지는 us_results/latest_all_scored.csv만 사용합니다. 한국 results/ 및 state/position_state.json과는 연결하지 않습니다.</div>
</div>
<script>
let status='ALL';
function setStatus(s,btn){{status=s;document.querySelectorAll('.toolbar button').forEach(x=>x.classList.remove('active'));btn.classList.add('active');filterCards();}}
function filterCards(){{const q=(document.getElementById('q').value||'').toLowerCase().replace(/\\s+/g,'');const allowed=status==='ALL'?null:new Set(status.split(','));document.querySelectorAll('.card').forEach(c=>{{const txt=((c.dataset.name||'')+(c.dataset.ticker||'')).replace(/\\s+/g,'');const okQ=!q||txt.includes(q);const okS=!allowed||allowed.has(c.dataset.status);c.style.display=(okQ&&okS)?'':'none';}});}}
</script></body></html>"""
    (DOCS / "index.html").write_text(page, encoding="utf-8")
    print("Generated docs/us-position/index.html")


if __name__ == "__main__":
    main()
