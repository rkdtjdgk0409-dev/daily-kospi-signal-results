#!/usr/bin/env python3
from __future__ import annotations

import html
import json
from pathlib import Path

import numpy as np
import pandas as pd


RESULTS = Path("us_results")
DOCS = Path("docs/us")


def esc(value: object) -> str:
    return html.escape(str(value if value is not None else ""))


def num(value: object, digits: int = 1) -> str:
    try:
        n = float(value)
        return f"{n:,.{digits}f}" if np.isfinite(n) else "-"
    except Exception:
        return "-"


def price(value: object) -> str:
    try:
        n = float(value)
        return f"${n:,.2f}" if np.isfinite(n) else "-"
    except Exception:
        return "-"


def badge(text: str, kind: str = "muted") -> str:
    return f'<span class="badge {kind}">{esc(text)}</span>'


def tier_badge(value: str) -> str:
    kind = {"CONFIRMED": "strong", "FRESH": "good", "EARLY": "warn"}.get(value, "muted")
    return badge(value, kind)


def regime_badge(value: str) -> str:
    kind = "good" if value == "RISK-ON" else ("bad" if value == "RISK-OFF" else "warn")
    return badge(value, kind)


def risk_badge(value: str) -> str:
    return badge(value, "good" if value == "LOW" else ("bad" if value == "HIGH" else "warn"))


def st_badge(value: str) -> str:
    return badge("GOOD" if str(value).upper() == "GOOD" else "BAD", "good" if str(value).upper() == "GOOD" else "bad")


def index_badges(row: pd.Series) -> str:
    parts = []
    if bool(row.get("in_sp500", False)):
        parts.append('<span class="index-chip sp">S&amp;P 500</span>')
    if bool(row.get("in_nasdaq100", False)):
        parts.append('<span class="index-chip ndx">NASDAQ-100</span>')
    return " ".join(parts)


def table_rows(frame: pd.DataFrame, limit: int | None = None) -> str:
    if limit is not None:
        frame = frame.head(limit)
    if frame.empty:
        return '<tr><td colspan="13" class="empty">해당 신호가 없습니다.</td></tr>'
    out = []
    for _, row in frame.iterrows():
        ticker = esc(row.get("ticker", ""))
        change = float(row.get("daily_return_pct", 0) or 0)
        change_class = "up" if change > 0 else ("down" if change < 0 else "")
        out.append(
            f'''<tr data-name="{esc(str(row.get('name','')).lower())}" data-ticker="{ticker.lower()}" data-index="{esc(row.get('market',''))}" data-sector="{esc(row.get('sector',''))}" data-alpha="{num(row.get('alpha_score'),2)}">
              <td class="rank">#{int(row.get('alpha_rank_all', 0) or 0)}</td>
              <td><button class="stock-link" onclick="openStock('{ticker}')"><b>{ticker}</b><span>{esc(row.get('name',''))}</span></button></td>
              <td class="indices">{index_badges(row)}</td>
              <td>{esc(row.get('sector','Unknown'))}</td>
              <td class="right"><b>{price(row.get('close'))}</b><span class="{change_class}">{change:+.2f}%</span></td>
              <td class="score">{num(row.get('alpha_score'))}</td>
              <td class="score">{num(row.get('entry_score'))}</td>
              <td>{num(row.get('cci'))}</td>
              <td>{num(row.get('plus_di'))} / {num(row.get('minus_di'))}</td>
              <td>{num(row.get('adx'))}</td>
              <td>{st_badge(row.get('supertrend_status','BAD'))}</td>
              <td>{num(row.get('rs_score'))}</td>
              <td>{risk_badge(str(row.get('risk_level','MED')))}</td>
            </tr>'''
        )
    return "".join(out)


def signal_section(title: str, subtitle: str, frame: pd.DataFrame, section_id: str) -> str:
    return f'''<section class="panel signal-panel" id="{section_id}">
      <div class="panel-head"><div><h2>{esc(title)}</h2><p>{esc(subtitle)}</p></div><span class="count">{len(frame)}</span></div>
      <div class="table-wrap"><table><thead><tr><th>Rank</th><th>Stock</th><th>Index</th><th>Sector</th><th class="right">Close</th><th>Alpha</th><th>Entry</th><th>CCI</th><th>+DI / -DI</th><th>ADX</th><th>ST</th><th>RS</th><th>Risk</th></tr></thead>
      <tbody>{table_rows(frame)}</tbody></table></div>
    </section>'''


def change_html(summary: dict) -> str:
    history = list(reversed(summary.get("constituent_history", [])))[:12]
    if not history:
        return '<div class="empty-card">저장된 편입·편출 변경 이력이 아직 없습니다. 최초 실행은 기준 스냅샷으로 저장됩니다.</div>'
    cards = []
    for event in history:
        added = event.get("added", [])
        removed = event.get("removed", [])
        add_html = " ".join(f'<span class="change add">+ {esc(x.get("ticker"))} {esc(x.get("name"))}</span>' for x in added) or '<span class="muted-text">없음</span>'
        remove_html = " ".join(f'<span class="change remove">− {esc(x.get("ticker"))} {esc(x.get("name"))}</span>' for x in removed) or '<span class="muted-text">없음</span>'
        detected = esc(str(event.get("detected_at", ""))[:16].replace("T", " "))
        cards.append(f'''<article class="change-card"><div class="change-head"><b>{esc(event.get('index',''))}</b><time>{detected} ET 감지</time></div><div><small>편입</small>{add_html}</div><div><small>편출</small>{remove_html}</div></article>''')
    return "".join(cards)


def regime_card(index_name: str, data: dict) -> str:
    short = "S&P 500" if index_name == "S&P 500" else "NASDAQ-100"
    return f'''<article class="regime-card"><div><span>{esc(short)}</span>{regime_badge(data.get('regime','NEUTRAL'))}</div>
      <strong>{num(data.get('benchmark_ret20_pct'))}% <small>20D</small></strong>
      <div class="regime-grid"><span>MA20 상회폭 <b>{num(100*float(data.get('breadth20',0)))}%</b></span><span>MA60 상회폭 <b>{num(100*float(data.get('breadth60',0)))}%</b></span><span>60D 수익률 <b>{num(data.get('benchmark_ret60_pct'))}%</b></span><span>점수 <b>{data.get('score',0)}/5</b></span></div>
    </article>'''


def main() -> None:
    summary = json.loads((RESULTS / "summary.json").read_text(encoding="utf-8"))
    all_scored = pd.read_csv(RESULTS / "latest_all_scored.csv")
    top = pd.read_csv(RESULTS / "latest_top_alpha.csv").head(60)
    confirmed = pd.read_csv(RESULTS / "latest_confirmed_buy.csv")
    fresh = pd.read_csv(RESULTS / "latest_fresh_buy.csv")
    early = pd.read_csv(RESULTS / "latest_early_setups.csv")
    DOCS.mkdir(parents=True, exist_ok=True)

    records = json.dumps(all_scored.replace({np.nan: None}).to_dict("records"), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    regimes = summary.get("regimes", {})
    counts = summary.get("universe_counts", {})
    generated = summary.get("generated_at", "")
    page = f'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="data-generated-at" content="{esc(generated)}"><meta name="theme-color" content="#07101f">
<title>US Equity Alpha Screener</title>
<style>
:root{{--bg:#07101f;--panel:#0d182a;--panel2:#111f35;--line:#22324b;--text:#eef4ff;--muted:#8ea1bb;--blue:#4d8dff;--cyan:#33d6c2;--green:#38d488;--red:#ff6475;--amber:#f8bc52;--purple:#9b87ff;--shadow:0 18px 50px rgba(0,0,0,.22)}}
*{{box-sizing:border-box}} body{{margin:0;background:radial-gradient(circle at 85% 0,#12264a 0,transparent 32%),var(--bg);color:var(--text);font:14px/1.5 Inter,Pretendard,system-ui,-apple-system,sans-serif}} button,input,select{{font:inherit}} a{{color:inherit}} .shell{{max-width:1480px;margin:auto;padding:22px}}
.hero{{border:1px solid var(--line);background:linear-gradient(135deg,rgba(15,31,57,.96),rgba(9,19,35,.94));border-radius:24px;padding:26px;box-shadow:var(--shadow);position:relative;overflow:hidden}} .hero:after{{content:"";position:absolute;right:-80px;top:-100px;width:300px;height:300px;border-radius:50%;background:rgba(77,141,255,.12);filter:blur(3px)}}
.topbar{{display:flex;align-items:center;justify-content:space-between;gap:16px;position:relative;z-index:1}} .eyebrow{{color:var(--cyan);font-weight:800;letter-spacing:.12em;font-size:12px}} h1{{font-size:clamp(26px,4vw,44px);line-height:1.1;margin:8px 0 10px}} .hero p{{color:var(--muted);max-width:760px;margin:0}} .actions{{display:flex;gap:9px;flex-wrap:wrap;justify-content:flex-end}} .btn{{border:1px solid var(--line);background:#101f36;color:var(--text);padding:10px 13px;border-radius:12px;text-decoration:none;cursor:pointer}} .btn.primary{{background:var(--blue);border-color:var(--blue);font-weight:800}} .btn.loading{{opacity:.65}}
.meta-line{{margin-top:18px;color:var(--muted);font-size:12px;display:flex;gap:18px;flex-wrap:wrap;position:relative;z-index:1}} .stats{{display:grid;grid-template-columns:repeat(6,1fr);gap:10px;margin-top:20px;position:relative;z-index:1}} .stat{{background:rgba(7,16,31,.56);border:1px solid var(--line);border-radius:15px;padding:14px}} .stat span{{display:block;color:var(--muted);font-size:11px}} .stat b{{display:block;font-size:23px;margin-top:4px}}
.grid-2{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:14px}} .panel{{background:var(--panel);border:1px solid var(--line);border-radius:20px;margin-top:14px;box-shadow:var(--shadow);overflow:hidden}} .panel-body{{padding:18px}} .panel-head{{padding:17px 19px;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between;gap:12px}} h2{{font-size:17px;margin:0}} .panel-head p{{color:var(--muted);font-size:12px;margin:3px 0 0}} .count{{min-width:34px;height:34px;display:grid;place-items:center;border-radius:11px;background:#182a45;color:#cfe0ff;font-weight:800}}
.regimes{{display:grid;grid-template-columns:1fr 1fr;gap:12px}} .regime-card{{background:var(--panel2);border:1px solid var(--line);border-radius:16px;padding:16px}} .regime-card>div:first-child{{display:flex;justify-content:space-between;align-items:center;font-weight:800}} .regime-card>strong{{font-size:26px;display:block;margin:13px 0}} .regime-card>strong small{{font-size:11px;color:var(--muted)}} .regime-grid{{display:grid;grid-template-columns:1fr 1fr;gap:7px;color:var(--muted);font-size:12px}} .regime-grid b{{color:var(--text)}}
.change-list{{display:grid;gap:9px;max-height:300px;overflow:auto}} .change-card{{background:var(--panel2);border:1px solid var(--line);border-radius:13px;padding:12px}} .change-head{{display:flex;justify-content:space-between;margin-bottom:8px}} .change-head time{{color:var(--muted);font-size:11px}} .change-card>div:not(.change-head){{display:grid;grid-template-columns:40px 1fr;gap:8px;margin-top:6px}} .change-card small{{color:var(--muted)}} .change{{display:inline-block;padding:3px 7px;border-radius:7px;margin:2px;font-size:11px}} .change.add{{color:#91f2be;background:rgba(56,212,136,.1)}} .change.remove{{color:#ff9aa6;background:rgba(255,100,117,.1)}} .empty-card{{color:var(--muted);padding:30px;text-align:center;border:1px dashed var(--line);border-radius:14px}}
.searchbar{{display:grid;grid-template-columns:1.4fr .8fr .8fr auto;gap:9px}} input,select{{width:100%;background:#091426;color:var(--text);border:1px solid var(--line);border-radius:11px;padding:11px 12px;outline:none}} input:focus,select:focus{{border-color:var(--blue)}} .result{{margin-top:12px}} .result-empty{{color:var(--muted);border:1px dashed var(--line);padding:22px;text-align:center;border-radius:13px}} .stock-card{{background:var(--panel2);border:1px solid var(--line);border-radius:16px;padding:17px}} .stock-head{{display:flex;justify-content:space-between;gap:12px}} .stock-head h3{{font-size:22px;margin:0}} .stock-head p{{color:var(--muted);margin:4px 0}} .stock-price{{text-align:right}} .stock-price b{{font-size:22px;display:block}} .score-grid{{display:grid;grid-template-columns:repeat(7,1fr);gap:8px;margin-top:15px}} .score-box{{background:#0a1628;border-radius:11px;padding:10px}} .score-box span{{color:var(--muted);font-size:10px;display:block}} .score-box b{{font-size:18px}} .details{{display:grid;grid-template-columns:repeat(6,1fr);gap:7px;margin-top:10px}} .detail{{border-top:1px solid var(--line);padding-top:8px}} .detail span{{display:block;color:var(--muted);font-size:10px}} .detail b{{font-size:12px}}
.table-tools{{padding:13px 18px;display:grid;grid-template-columns:1.4fr .8fr .6fr;gap:8px;border-bottom:1px solid var(--line)}} .table-wrap{{overflow:auto}} table{{width:100%;border-collapse:collapse;min-width:1120px}} th{{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em;text-align:left;padding:10px 9px;background:#0a1527;position:sticky;top:0}} td{{padding:11px 9px;border-top:1px solid rgba(34,50,75,.68);white-space:nowrap}} tbody tr:hover{{background:rgba(77,141,255,.055)}} .right{{text-align:right}} td.right span{{display:block;font-size:11px}} .stock-link{{border:0;background:none;color:var(--text);padding:0;text-align:left;cursor:pointer}} .stock-link span{{display:block;color:var(--muted);font-size:11px;max-width:180px;overflow:hidden;text-overflow:ellipsis}} .score{{color:#b9d2ff;font-weight:800}} .rank{{color:var(--muted)}}
.badge,.index-chip{{display:inline-block;border-radius:999px;padding:3px 7px;font-size:10px;font-weight:800;line-height:1.2}} .badge.good{{color:#8df0ba;background:rgba(56,212,136,.12)}} .badge.bad{{color:#ff9aa6;background:rgba(255,100,117,.12)}} .badge.warn{{color:#ffd48a;background:rgba(248,188,82,.12)}} .badge.strong{{color:#fff;background:#295ab8}} .badge.muted{{color:#aebdd0;background:#1c2a3f}} .index-chip.sp{{color:#a8c6ff;background:rgba(77,141,255,.14)}} .index-chip.ndx{{color:#a8f4e9;background:rgba(51,214,194,.13)}} .up{{color:var(--green)}} .down{{color:var(--red)}} .muted-text,.empty{{color:var(--muted)}} .footer{{color:var(--muted);font-size:11px;padding:24px 4px 50px}} #toast{{position:fixed;right:18px;bottom:18px;background:#182a45;border:1px solid var(--line);padding:11px 15px;border-radius:12px;opacity:0;transform:translateY(8px);transition:.2s;z-index:10}} #toast.show{{opacity:1;transform:none}}
@media(max-width:980px){{.stats{{grid-template-columns:repeat(3,1fr)}}.grid-2{{grid-template-columns:1fr}}.score-grid{{grid-template-columns:repeat(4,1fr)}}.details{{grid-template-columns:repeat(3,1fr)}}}}
@media(max-width:680px){{.shell{{padding:10px}}.hero{{padding:18px;border-radius:18px}}.topbar{{align-items:flex-start;flex-direction:column}}.actions{{width:100%;justify-content:flex-start}}.stats{{grid-template-columns:repeat(2,1fr)}}.regimes{{grid-template-columns:1fr}}.searchbar,.table-tools{{grid-template-columns:1fr}}.score-grid{{grid-template-columns:repeat(2,1fr)}}.details{{grid-template-columns:repeat(2,1fr)}}.stock-head{{flex-direction:column}}.stock-price{{text-align:left}}.panel{{border-radius:15px}}}}
</style></head><body><main class="shell">
<header class="hero"><div class="topbar"><div><span class="eyebrow">US MARKET · DAILY CLOSE</span><h1>US Equity Alpha Screener</h1><p>S&amp;P 500과 NASDAQ-100 전체 구성종목을 같은 기술적 신호 모델로 분석합니다. 중복 종목은 한 번만 계산하고 각 지수 편입·편출을 자동 추적합니다.</p></div><div class="actions"><a class="btn" href="../">한국 시장</a><button class="btn primary" id="refresh" onclick="checkLatest(true)">↻ 최신 데이터</button></div></div>
<div class="meta-line"><span>기준일 <b>{esc(summary.get('latest_signal_date','-'))}</b></span><span>생성 <b>{esc(generated[:16].replace('T',' '))} ET</b></span><span>모델 <b>{esc(summary.get('model_version',''))}</b></span><span>정규장 일봉·조정주가 기준</span></div>
<div class="stats"><div class="stat"><span>분석 종목</span><b>{summary.get('symbols_scored',0)}</b></div><div class="stat"><span>S&amp;P 500 편입 종목</span><b>{counts.get('S&P 500',0)}</b></div><div class="stat"><span>NASDAQ-100 편입 종목</span><b>{counts.get('NASDAQ-100',0)}</b></div><div class="stat"><span>CONFIRMED</span><b>{summary.get('confirmed_buy_count',0)}</b></div><div class="stat"><span>FRESH</span><b>{summary.get('fresh_buy_count',0)}</b></div><div class="stat"><span>EARLY</span><b>{summary.get('early_setup_count',0)}</b></div></div></header>

<div class="grid-2"><section class="panel"><div class="panel-head"><div><h2>시장 국면</h2><p>지수 추세 + 구성종목 MA20·MA60 breadth</p></div></div><div class="panel-body"><div class="regimes">{regime_card('S&P 500', regimes.get('S&P 500',{}))}{regime_card('NASDAQ-100', regimes.get('NASDAQ-100',{}))}</div></div></section>
<section class="panel"><div class="panel-head"><div><h2>지수 편입·편출 추적</h2><p>이전 검증 스냅샷과 최신 구성종목 비교 · 최근 12건</p></div></div><div class="panel-body change-list">{change_html(summary)}</div></section></div>

<section class="panel"><div class="panel-head"><div><h2>종목 검색</h2><p>티커·회사명으로 전체 유니버스 조회</p></div></div><div class="panel-body"><div class="searchbar"><input id="stock-search" placeholder="예: NVDA, Apple" onkeydown="if(event.key==='Enter')searchStock()"><select id="stock-index"><option value="ALL">모든 지수</option><option value="S&P 500">S&amp;P 500</option><option value="NASDAQ-100">NASDAQ-100</option></select><select id="stock-sector"><option value="ALL">모든 섹터</option></select><button class="btn primary" onclick="searchStock()">검색</button></div><div id="stock-result" class="result result-empty">검색할 종목을 입력하세요.</div></div></section>

{signal_section('CONFIRMED BUY','CCI 신규 돌파 + DMI/ADX + Supertrend + Entry + Flow + Alpha 모두 확인',confirmed,'confirmed')}
{signal_section('FRESH BUY','최근 3거래일 CCI 돌파 · 추세 초기 진입 후보',fresh,'fresh')}
{signal_section('EARLY SETUP','CCI 0선 아래에서 상승 가속 중인 사전 관찰 후보',early,'early')}

<section class="panel"><div class="panel-head"><div><h2>Alpha Top 60</h2><p>지수·섹터·최소 Alpha로 필터링</p></div><span class="count">60</span></div><div class="table-tools"><input id="rank-search" placeholder="티커 또는 회사명" oninput="filterTop()"><select id="rank-index" onchange="filterTop()"><option value="ALL">모든 지수</option><option value="S&P 500">S&amp;P 500</option><option value="NASDAQ-100">NASDAQ-100</option></select><select id="rank-alpha" onchange="filterTop()"><option value="0">Alpha 전체</option><option value="50">50 이상</option><option value="60">60 이상</option><option value="70">70 이상</option><option value="80">80 이상</option></select></div><div class="table-wrap"><table id="top-table"><thead><tr><th>Rank</th><th>Stock</th><th>Index</th><th>Sector</th><th class="right">Close</th><th>Alpha</th><th>Entry</th><th>CCI</th><th>+DI / -DI</th><th>ADX</th><th>ST</th><th>RS</th><th>Risk</th></tr></thead><tbody>{table_rows(top)}</tbody></table></div></section>

<p class="footer">본 페이지는 기술적 조건을 정리하는 연구용 스크리너이며 투자 권유가 아닙니다. CVD는 일봉 가격 방향×거래량 프록시이고 실제 체결 기반 CVD가 아닙니다. 지수 구성종목은 다중 소스 검증과 이전 스냅샷 안전장치를 사용하지만 공식 발표와 시간차가 생길 수 있습니다.</p></main><div id="toast"></div>
<script>
const STOCKS={records};
const GENERATED=document.querySelector('meta[name="data-generated-at"]').content;
const $=id=>document.getElementById(id);
const safe=v=>String(v??'').replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
const n=(v,d=1)=>Number.isFinite(Number(v))?Number(v).toLocaleString('en-US',{{minimumFractionDigits:d,maximumFractionDigits:d}}):'-';
const money=v=>Number.isFinite(Number(v))?'$'+Number(v).toLocaleString('en-US',{{minimumFractionDigits:2,maximumFractionDigits:2}}):'-';
const chip=(v,k='muted')=>`<span class="badge ${{k}}">${{safe(v)}}</span>`;
const st=v=>chip(String(v).toUpperCase()==='GOOD'?'GOOD':'BAD',String(v).toUpperCase()==='GOOD'?'good':'bad');
const risk=v=>chip(v,v==='LOW'?'good':(v==='HIGH'?'bad':'warn'));
const regime=v=>chip(v,v==='RISK-ON'?'good':(v==='RISK-OFF'?'bad':'warn'));
const indices=s=>(s.in_sp500?'<span class="index-chip sp">S&amp;P 500</span> ':'')+(s.in_nasdaq100?'<span class="index-chip ndx">NASDAQ-100</span>':'');
const field=(k,v)=>`<div class="detail"><span>${{k}}</span><b>${{v}}</b></div>`;
const score=(k,v)=>`<div class="score-box"><span>${{k}}</span><b>${{n(v)}}</b></div>`;

function renderStock(s){{
  const ret=Number(s.daily_return_pct||0), cls=ret>0?'up':(ret<0?'down':'');
  $('stock-result').className='result stock-card';
  $('stock-result').innerHTML=`<div class="stock-head"><div><h3>${{safe(s.ticker)}} · ${{safe(s.name)}}</h3><p>${{safe(s.sector)}} · ${{indices(s)}} · 기준일 ${{safe(s.signal_date)}}</p><div>${{chip(s.signal_tier,s.signal_tier==='CONFIRMED'?'strong':(s.signal_tier==='FRESH'?'good':(s.signal_tier==='EARLY'?'warn':'muted')))}} ${{regime(s.regime)}} ${{st(s.supertrend_status)}} ${{risk(s.risk_level)}}</div></div><div class="stock-price"><b>${{money(s.close)}}</b><span class="${{cls}}">${{ret>=0?'+':''}}${{n(ret,2)}}%</span><p>전체 Alpha #${{s.alpha_rank_all}}${{s.rank_sp500?' · S&amp;P #'+Math.round(s.rank_sp500):''}}${{s.rank_nasdaq100?' · NDX #'+Math.round(s.rank_nasdaq100):''}}</p></div></div>
  <div class="score-grid">${{score('Alpha',s.alpha_score)}}${{score('Entry',s.entry_score)}}${{score('Trend',s.trend_score)}}${{score('Momentum',s.momentum_score)}}${{score('Flow',s.flow_score)}}${{score('Relative Strength',s.rs_score)}}${{score('Risk',s.risk_score)}}</div>
  <div class="details">${{field('CCI',n(s.cci))}}${{field('CCI 3D Δ',n(s.cci_delta3))}}${{field('+DI / -DI',n(s.plus_di)+' / '+n(s.minus_di))}}${{field('ADX',n(s.adx))}}${{field('ST distance / ATR',n(s.supertrend_distance_atr,2)+'x')}}${{field('Relative volume',n(s.relative_dollar_volume,2)+'x')}}${{field('RS20 excess',n(s.rs20_excess_pct,2)+'%')}}${{field('RS60 excess',n(s.rs60_excess_pct,2)+'%')}}${{field('ATR',n(s.atr_pct,2)+'%')}}${{field('Volatility 20D ann.',n(s.vol20_ann_pct)+'%')}}${{field('S&P regime',regime(s.regime_sp500))}}${{field('NASDAQ regime',regime(s.regime_nasdaq100))}}</div>`;
  $('stock-result').scrollIntoView({{behavior:'smooth',block:'nearest'}});
}}
function openStock(ticker){{ $('stock-search').value=ticker; const s=STOCKS.find(x=>x.ticker===ticker); if(s)renderStock(s); }}
function searchStock(){{
  const q=$('stock-search').value.toLowerCase().replace(/\\s+/g,''), idx=$('stock-index').value, sector=$('stock-sector').value;
  const matches=STOCKS.filter(s=>(!q||String(s.ticker).toLowerCase().includes(q)||String(s.name).toLowerCase().replace(/\\s+/g,'').includes(q))&&(idx==='ALL'||String(s.market).includes(idx))&&(sector==='ALL'||s.sector===sector)).sort((a,b)=>Number(b.alpha_score)-Number(a.alpha_score));
  if(matches.length)renderStock(matches[0]); else {{$('stock-result').className='result result-empty';$('stock-result').textContent='현재 분석 유니버스에서 종목을 찾지 못했습니다.';}}
}}
function filterTop(){{
 const q=$('rank-search').value.toLowerCase(),idx=$('rank-index').value,min=Number($('rank-alpha').value);
 document.querySelectorAll('#top-table tbody tr').forEach(tr=>{{const okQ=!q||(tr.dataset.name+' '+tr.dataset.ticker).includes(q),okI=idx==='ALL'||tr.dataset.index.includes(idx),okA=Number(tr.dataset.alpha)>=min;tr.style.display=okQ&&okI&&okA?'':'none';}});
}}
const sectors=[...new Set(STOCKS.map(s=>s.sector).filter(Boolean))].sort(); sectors.forEach(v=>{{$('stock-sector').insertAdjacentHTML('beforeend',`<option value="${{safe(v)}}">${{safe(v)}}</option>`)}});
let toastTimer; function toast(msg){{const t=$('toast');t.textContent=msg;t.classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>t.classList.remove('show'),2800)}}
async function checkLatest(manual=false){{const btn=$('refresh');btn.classList.add('loading');try{{const u=new URL(location.href);u.searchParams.set('_refresh',Date.now());const res=await fetch(u,{{cache:'no-store'}});if(!res.ok)throw new Error();const doc=new DOMParser().parseFromString(await res.text(),'text/html');const remote=doc.querySelector('meta[name="data-generated-at"]')?.content||'';if(remote&&remote!==GENERATED){{toast('새 데이터가 확인되어 갱신합니다.');setTimeout(()=>location.reload(),450)}}else if(manual)toast('이미 최신 데이터입니다.')}}catch(e){{if(manual)toast('업데이트 확인에 실패했습니다.')}}finally{{btn.classList.remove('loading')}}}}
setInterval(()=>checkLatest(false),5*60*1000);
</script></body></html>'''
    (DOCS / "index.html").write_text(page, encoding="utf-8")
    print(f"Generated {DOCS / 'index.html'}")


if __name__ == "__main__":
    main()
