#!/usr/bin/env python3
"""
Inject Position Management UI into the already-generated docs/index.html.
Run AFTER build_page.py.
"""
from pathlib import Path
import json
import html
import pandas as pd

DOC = Path("docs/index.html")
CSV = Path("results/latest_position_management.csv")


def esc(x):
    return html.escape(str(x))


def price(x):
    try:
        return f"{int(round(float(x))):,}"
    except Exception:
        return "-"


def num(x, d=1):
    try:
        return f"{float(x):,.{d}f}"
    except Exception:
        return "-"


def status_badge(s):
    s = str(s)
    cls = {
        "STRONG HOLD": "pm-strong",
        "HOLD": "pm-hold",
        "WATCH": "pm-watch",
        "TAKE PROFIT": "pm-profit",
        "EXIT": "pm-exit",
        "STOP": "pm-stop",
    }.get(s, "pm-watch")
    return f"<span class='pm-badge {cls}'>{esc(s)}</span>"


def build_rows(df):
    if df.empty:
        return "<div class='pm-empty'>아직 추적 중인 포지션이 없습니다. Confirmed Buy가 발생하면 자동으로 여기에 등록됩니다.</div>"

    cards = []
    for _, r in df.iterrows():
        pnl = float(r.get("pnl_pct", 0) or 0)
        pnl_cls = "pm-up" if pnl > 0 else ("pm-down" if pnl < 0 else "")
        cards.append(f"""
        <article class="pm-card" data-status="{esc(r.get('position_status',''))}">
          <div class="pm-card-head">
            <div>
              <div class="pm-name">{esc(r.get('name','-'))}</div>
              <div class="pm-meta">{str(r.get('ticker','')).zfill(6)} · {esc(r.get('market',''))} · 진입 {esc(r.get('entry_date','-'))}</div>
            </div>
            {status_badge(r.get('position_status',''))}
          </div>
          <div class="pm-grid">
            <div><span>현재가</span><b>{price(r.get('close'))}원</b></div>
            <div><span>진입가</span><b>{price(r.get('entry_price'))}원</b></div>
            <div><span>수익률</span><b class="{pnl_cls}">{pnl:+.2f}%</b></div>
            <div><span>Exit Risk</span><b>{num(r.get('exit_risk'))} / 100</b></div>
            <div><span>Initial Stop</span><b>{price(r.get('initial_stop'))}원</b></div>
            <div><span>Trailing Stop</span><b>{price(r.get('trailing_stop'))}원</b></div>
            <div><span>최고 종가</span><b>{price(r.get('highest_close'))}원</b></div>
            <div><span>고점대비</span><b>{num(r.get('drawdown_from_peak_pct'),2)}%</b></div>
          </div>
          <div class="pm-reason"><b>판단</b> {esc(r.get('position_reason',''))}</div>
          <div class="pm-riskline">
            ST {num(r.get('exit_st_risk'))} · DMI {num(r.get('exit_dmi_risk'))} · ADX {num(r.get('exit_adx_risk'))} ·
            CCI {num(r.get('exit_cci_risk'))} · Alpha {num(r.get('exit_alpha_risk'))} · Regime {num(r.get('exit_regime_risk'))}
          </div>
        </article>
        """)
    return "".join(cards)


def main():
    if not DOC.exists():
        raise FileNotFoundError("docs/index.html not found. Run build_page.py first.")

    if CSV.exists() and CSV.stat().st_size > 0:
        try:
            df = pd.read_csv(CSV, dtype={"ticker": str})
        except pd.errors.EmptyDataError:
            df = pd.DataFrame()
    else:
        df = pd.DataFrame()

    counts = df["position_status"].value_counts().to_dict() if not df.empty else {}
    cards = build_rows(df)

    style = r"""
<style id="position-management-style">
.pm-section{margin-top:30px}
.pm-summary{display:grid;grid-template-columns:repeat(5,1fr);gap:9px;margin:12px 0}
.pm-stat{border:1px solid var(--line);background:var(--panel);border-radius:13px;padding:12px}
.pm-stat b{font-size:21px;display:block}.pm-stat span{font-size:10px;color:var(--muted)}
.pm-toolbar{display:flex;gap:7px;flex-wrap:wrap;margin:12px 0}
.pm-filter{border:1px solid var(--line);background:#0d141d;color:var(--muted);padding:8px 11px;border-radius:999px;cursor:pointer}
.pm-filter.active{color:var(--text);border-color:rgba(131,184,255,.5);background:rgba(131,184,255,.12)}
.pm-list{display:grid;grid-template-columns:repeat(2,1fr);gap:11px}
.pm-card{background:linear-gradient(145deg,#101923,#0b1118);border:1px solid var(--line);border-radius:17px;padding:16px}
.pm-card-head{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}
.pm-name{font-size:17px;font-weight:900}.pm-meta{font-size:10px;color:var(--muted);margin-top:3px}
.pm-badge{font-size:10px;font-weight:900;border-radius:999px;padding:6px 9px;border:1px solid var(--line)}
.pm-strong,.pm-hold{color:var(--green);border-color:rgba(83,212,154,.38);background:rgba(83,212,154,.08)}
.pm-watch{color:var(--yellow);border-color:rgba(241,198,106,.38);background:rgba(241,198,106,.08)}
.pm-profit{color:var(--cyan);border-color:rgba(101,212,232,.38);background:rgba(101,212,232,.08)}
.pm-exit,.pm-stop{color:var(--red);border-color:rgba(255,123,134,.42);background:rgba(255,123,134,.09)}
.pm-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:7px;margin-top:13px}
.pm-grid div{background:#0d151f;border:1px solid #1e2b3a;border-radius:10px;padding:9px}
.pm-grid span{display:block;color:var(--muted);font-size:9px;margin-bottom:4px}.pm-grid b{font-size:12px}
.pm-up{color:var(--green)}.pm-down{color:var(--red)}
.pm-reason{margin-top:10px;border-left:3px solid var(--accent);background:rgba(131,184,255,.06);padding:10px 11px;border-radius:8px;font-size:11px;line-height:1.6}
.pm-reason b{color:var(--accent);margin-right:6px}
.pm-riskline{margin-top:8px;color:var(--muted);font-size:9px}
.pm-empty{padding:28px;text-align:center;color:var(--muted);border:1px dashed var(--line);border-radius:15px}
@media(max-width:800px){.pm-list{grid-template-columns:1fr}.pm-summary{grid-template-columns:repeat(2,1fr)}.pm-grid{grid-template-columns:repeat(2,1fr)}}
</style>
"""

    section = f"""
<section class="pm-section" id="position-management">
<h2>📍 Position Management</h2>
<div class="sub">Confirmed Buy 발생일 종가를 가상 진입가로 기록하고, 이후 종가 기준으로 HOLD · WATCH · TAKE PROFIT · EXIT/STOP을 관리합니다. Exit Risk는 매도 확률이 아니라 기술적 청산 위험 점수입니다.</div>
<div class="pm-summary">
 <div class="pm-stat"><b>{counts.get('STRONG HOLD',0)+counts.get('HOLD',0)}</b><span>HOLD</span></div>
 <div class="pm-stat"><b>{counts.get('WATCH',0)}</b><span>WATCH</span></div>
 <div class="pm-stat"><b>{counts.get('TAKE PROFIT',0)}</b><span>TAKE PROFIT</span></div>
 <div class="pm-stat"><b>{counts.get('EXIT',0)}</b><span>EXIT</span></div>
 <div class="pm-stat"><b>{counts.get('STOP',0)}</b><span>STOP</span></div>
</div>
<div class="pm-toolbar">
 <button class="pm-filter active" onclick="pmFilter('ALL',this)">전체</button>
 <button class="pm-filter" onclick="pmFilter('STRONG HOLD,HOLD',this)">HOLD</button>
 <button class="pm-filter" onclick="pmFilter('WATCH',this)">WATCH</button>
 <button class="pm-filter" onclick="pmFilter('TAKE PROFIT',this)">TAKE PROFIT</button>
 <button class="pm-filter" onclick="pmFilter('EXIT,STOP',this)">EXIT / STOP</button>
</div>
<div class="pm-list">{cards}</div>
</section>
"""

    script = r"""
<script id="position-management-script">
function pmFilter(statuses,btn){
 const allowed=statuses==='ALL'?null:new Set(statuses.split(','));
 document.querySelectorAll('.pm-card').forEach(card=>{
   card.style.display=(!allowed||allowed.has(card.dataset.status))?'':'none';
 });
 document.querySelectorAll('.pm-filter').forEach(x=>x.classList.remove('active'));
 if(btn)btn.classList.add('active');
}
</script>
"""

    text = DOC.read_text(encoding="utf-8")

    # idempotent if run more than once in same workspace
    if 'id="position-management-style"' in text:
        print("[position-page] already injected")
        return

    text = text.replace("</head>", style + "\n</head>", 1)

    # Place it after Early Setup and before stock search if possible.
    marker = '<h2>전체 분석 종목 검색</h2>'
    if marker in text:
        text = text.replace(marker, section + "\n" + marker, 1)
    else:
        text = text.replace("</div>\n<div id=\"refresh-toast\"", section + "\n</div>\n<div id=\"refresh-toast\"", 1)

    text = text.replace("</body>", script + "\n</body>", 1)
    DOC.write_text(text, encoding="utf-8")
    print(f"[position-page] injected {len(df)} positions into docs/index.html")


if __name__ == "__main__":
    main()
