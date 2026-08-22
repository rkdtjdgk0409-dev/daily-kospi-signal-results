#!/usr/bin/env python3
from __future__ import annotations

import shutil
from pathlib import Path


HTML = r'''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
<meta name="theme-color" content="#0b1020" />
<title>Price Structure Scanner</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
:root{
  --bg:#070b14;--panel:#0e1526;--panel2:#121b30;--line:#24304a;
  --text:#e8eefb;--muted:#93a3bf;--good:#37d39a;--warn:#f7c65a;
  --bad:#ff6b78;--blue:#5ca8ff;--purple:#a78bfa
}
*{box-sizing:border-box}
body{
  margin:0;
  background:linear-gradient(180deg,#070b14,#0a1020 45%,#070b14);
  color:var(--text);
  font-family:Inter,Pretendard,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif
}
.wrap{max-width:1500px;margin:auto;padding:18px}
.top{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}
.title h1{font-size:24px;margin:0 0 6px}
.title p{margin:0;color:var(--muted);font-size:13px}
.actions{display:flex;flex-wrap:wrap;gap:8px}
.btn,.market-link{
  border:1px solid var(--line);background:rgba(18,27,48,.8);color:var(--text);
  padding:9px 12px;border-radius:10px;text-decoration:none;font-size:13px;cursor:pointer
}
.btn:hover,.market-link:hover{border-color:#4a5c82}
.cards{display:grid;grid-template-columns:repeat(6,minmax(120px,1fr));gap:10px;margin:16px 0}
.card{background:rgba(14,21,38,.88);border:1px solid var(--line);border-radius:14px;padding:13px}
.card .k{color:var(--muted);font-size:12px}
.card .v{font-size:20px;font-weight:800;margin-top:4px}
.toolbar{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}
.search{
  min-width:240px;flex:1;background:#0d1424;border:1px solid var(--line);
  color:var(--text);border-radius:10px;padding:10px 12px
}
.select{
  background:#0d1424;border:1px solid var(--line);color:var(--text);
  border-radius:10px;padding:10px
}
.chips{display:flex;gap:7px;overflow:auto;padding:2px 0 10px}
.chip{
  white-space:nowrap;border:1px solid var(--line);background:#0d1424;color:var(--muted);
  padding:7px 10px;border-radius:999px;cursor:pointer;font-size:12px
}
.chip.active{color:#fff;border-color:#5c72a7;background:#18233c}
.layout{display:grid;grid-template-columns:minmax(620px,1.15fr) minmax(420px,.85fr);gap:12px}
.panel{background:rgba(14,21,38,.9);border:1px solid var(--line);border-radius:14px;overflow:hidden}
.panelhead{
  padding:12px 14px;border-bottom:1px solid var(--line);
  display:flex;justify-content:space-between;align-items:center
}
.tablewrap{overflow:auto;max-height:76vh}
table{border-collapse:collapse;width:100%;font-size:12px}
th{
  position:sticky;top:0;background:#121b30;color:#9fb0cc;text-align:left;
  padding:10px 8px;border-bottom:1px solid var(--line);z-index:2;cursor:pointer
}
td{padding:9px 8px;border-bottom:1px solid rgba(36,48,74,.65);white-space:nowrap}
tr{cursor:pointer}
tr:hover{background:#131e35}
.name{font-weight:750}
.ticker{color:var(--muted);font-size:10px}
.grade{font-weight:900}
.Aplus,.A{color:var(--good)}
.B{color:var(--warn)}
.C,.D{color:#93a3bf}
.bull{color:var(--good)}
.bear{color:var(--bad)}
.watch{color:var(--warn)}
.pill{display:inline-block;padding:4px 7px;border:1px solid var(--line);border-radius:999px;font-size:10px}
.detail{padding:14px}
.hero{display:flex;justify-content:space-between;gap:10px}
.hero h2{margin:0;font-size:20px}
.hero .setup{margin-top:5px;font-size:13px}
.scorebox{text-align:right}
.scorebox strong{font-size:26px}
.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:12px 0}
.metric{background:#10192d;border:1px solid var(--line);border-radius:10px;padding:9px}
.metric .k{font-size:10px;color:var(--muted)}
.metric .v{font-size:13px;font-weight:700;margin-top:4px}
.chart{height:390px;width:100%}
.sectiontitle{font-weight:800;font-size:13px;margin:14px 0 7px}
.bars{display:grid;gap:7px}
.barrow{
  display:grid;grid-template-columns:105px 1fr 38px;gap:8px;
  align-items:center;font-size:11px;color:var(--muted)
}
.bar{height:7px;border-radius:99px;background:#1d2942;overflow:hidden}
.bar i{
  display:block;height:100%;background:linear-gradient(90deg,#5ca8ff,#37d39a);
  border-radius:99px
}
.note{
  font-size:11px;color:var(--muted);line-height:1.55;background:#0b1221;
  border:1px solid var(--line);border-radius:10px;padding:10px;margin-top:12px
}
.empty{padding:35px;text-align:center;color:var(--muted)}

@media(max-width:1050px){
  .cards{grid-template-columns:repeat(3,1fr)}
  .layout{grid-template-columns:1fr}
  .tablewrap{max-height:48vh}
  .chart{height:335px}
}
@media(max-width:600px){
  .wrap{padding:10px}
  .top{display:block}
  .actions{margin-top:10px}
  .title h1{font-size:20px}
  .cards{grid-template-columns:repeat(2,1fr)}
  .layout{display:block}
  .panel{margin-bottom:11px}
  .detail{padding:10px 8px}
  .metrics{grid-template-columns:repeat(2,1fr)}
  .metric{padding:8px}
  .metric .v{font-size:12px}
  .chart{height:285px}
  .tablewrap{max-height:48vh}
  .hide-mobile{display:none}
}
</style>
</head>
<body>
<div class="wrap">
  <div class="top">
    <div class="title">
      <h1>Price Structure Scanner</h1>
      <p>매물대 · 지지/저항 · 상승/하락 채널 · 삼각수렴 · 돌파 품질 · R/R 기반 차트 구조 분석</p>
    </div>
    <div class="actions">
      <a class="market-link" href="../">한국 지표</a>
      <a class="market-link" href="../us/">미국 시장</a>
      <a class="market-link" href="../position/">포지션 관리</a>
      <button class="btn" onclick="location.reload()">새로고침</button>
    </div>
  </div>

  <div class="cards" id="cards"></div>

  <div class="toolbar">
    <input id="search" class="search" placeholder="종목명 또는 코드 검색"/>
    <select id="market" class="select">
      <option value="ALL">전체 시장</option><option>KOSPI</option><option>KOSDAQ</option>
    </select>
    <select id="grade" class="select">
      <option value="ALL">전체 등급</option><option>A+</option><option>A</option>
      <option>B</option><option>C</option><option>D</option>
    </select>
    <select id="sort" class="select">
      <option value="score">점수순</option>
      <option value="rr1">R/R순</option>
      <option value="breakout_quality">돌파품질순</option>
      <option value="rvol">RVOL순</option>
      <option value="rs_score">상대강도순</option>
    </select>
  </div>

  <div class="chips" id="chips"></div>

  <div class="layout">
    <section class="panel">
      <div class="panelhead">
        <strong>종목 스캔</strong>
        <span id="count" style="color:var(--muted);font-size:11px"></span>
      </div>
      <div class="tablewrap">
        <table>
          <thead>
            <tr>
              <th>종목</th><th>등급</th><th>셋업</th><th>점수</th><th>구조</th>
              <th>R/R</th><th>RVOL</th><th class="hide-mobile">돌파품질</th>
              <th class="hide-mobile">RS</th>
            </tr>
          </thead>
          <tbody id="tbody"></tbody>
        </table>
      </div>
    </section>

    <section class="panel" id="detailPanel">
      <div class="empty">왼쪽에서 종목을 선택하세요.</div>
    </section>
  </div>

  <div class="note">
    캔들 차트의 날짜축은 실제 거래일만 이어 붙여 표시하므로 주말·휴장일 공백이 생기지 않습니다.
    모바일에서는 최근 거래 구간을 압축해 보여주되 추세선/채널은 현재 화면 범위까지 연장해 표시합니다.
    Volume Profile은 일봉 OHLCV를 가격 구간에 분배한 근사값이며, 등급은 자동 매수 명령이 아니라
    셋업의 구조적 품질을 뜻합니다.
  </div>
</div>

<script>
let DATA=[], FILTER='ALL', selectedTicker=null;
const SETUPS=[
  'ALL','BREAKOUT_READY','CONFIRMED_BREAKOUT','TRENDLINE_BREAKOUT',
  'TRIANGLE_BREAKOUT','RETEST_ENTRY','SUPPORT_BOUNCE','FAILED_BREAKOUT',
  'SUPPORT_BREAKDOWN','COMPRESSION_WATCH'
];
const labels={
  ALL:'전체',BREAKOUT_READY:'⚡ 돌파 임박',CONFIRMED_BREAKOUT:'🔥 저항 돌파',
  TRENDLINE_BREAKOUT:'↗ 추세선 돌파',TRIANGLE_BREAKOUT:'△ 삼각 돌파',
  RETEST_ENTRY:'✓ 리테스트',SUPPORT_BOUNCE:'🛡 지지 반등',
  FAILED_BREAKOUT:'⚠ 실패 돌파',SUPPORT_BREAKDOWN:'↓ 지지 이탈',
  COMPRESSION_WATCH:'◇ 수렴 관찰'
};

function n(v,d=1){
  return v==null||Number.isNaN(+v)
    ? '-'
    : Number(v).toLocaleString('ko-KR',{maximumFractionDigits:d});
}
function krw(v,d=0){
  return v==null||Number.isNaN(+v)
    ? '-'
    : '₩'+Number(v).toLocaleString('ko-KR',{maximumFractionDigits:d});
}
function pct(v){return v==null?'-':(v*100).toFixed(1)+'%'}
function setupClass(r){return r.direction==='BULLISH'?'bull':r.direction==='BEARISH'?'bear':'watch'}

function initChips(){
  document.getElementById('chips').innerHTML=SETUPS.map(
    x=>`<button class="chip ${x==='ALL'?'active':''}" data-x="${x}">${labels[x]||x}</button>`
  ).join('');
  document.querySelectorAll('.chip').forEach(b=>b.onclick=()=>{
    FILTER=b.dataset.x;
    document.querySelectorAll('.chip').forEach(x=>x.classList.toggle('active',x===b));
    render();
  });
}

function cards(meta){
  const rows=meta.rows||[];
  const c=[
    ['분석 종목',rows.length],
    ['A+ / A',rows.filter(x=>x.grade==='A+'||x.grade==='A').length],
    ['Hard Filter',rows.filter(x=>x.hard_filter_pass).length],
    ['돌파 임박',rows.filter(x=>x.setup==='BREAKOUT_READY').length],
    ['확정 돌파',rows.filter(x=>['CONFIRMED_BREAKOUT','TRENDLINE_BREAKOUT','TRIANGLE_BREAKOUT'].includes(x.setup)).length],
    ['Risk / 실패',rows.filter(x=>['FAILED_BREAKOUT','SUPPORT_BREAKDOWN','TRENDLINE_BREAKDOWN','TRIANGLE_BREAKDOWN'].includes(x.setup)).length]
  ];
  document.getElementById('cards').innerHTML=c.map(
    x=>`<div class="card"><div class="k">${x[0]}</div><div class="v">${x[1]}</div></div>`
  ).join('');
}

function filtered(){
  const q=document.getElementById('search').value.trim().toLowerCase();
  const m=document.getElementById('market').value;
  const g=document.getElementById('grade').value;
  const s=document.getElementById('sort').value;
  let a=DATA.filter(r=>
    (!q||r.name.toLowerCase().includes(q)||r.ticker.includes(q))&&
    (m==='ALL'||r.market===m)&&
    (g==='ALL'||r.grade===g)&&
    (FILTER==='ALL'||r.setup===FILTER)
  );
  a.sort((x,y)=>(Number(y[s])||-999)-(Number(x[s])||-999));
  return a;
}

function render(){
  const a=filtered();
  document.getElementById('count').textContent=`${a.length}개`;
  document.getElementById('tbody').innerHTML=a.map(r=>`
    <tr data-t="${r.ticker}">
      <td><div class="name">${r.name}</div><div class="ticker">${r.ticker} · ${r.market}</div></td>
      <td class="grade ${r.grade==='A+'?'Aplus':r.grade}">${r.grade}${r.hard_filter_pass?' ✓':''}</td>
      <td class="${setupClass(r)}"><span class="pill">${r.setup_label}</span></td>
      <td><b>${n(r.score)}</b></td><td>${r.structure_code}</td><td>${n(r.rr1,2)}</td>
      <td>${n(r.rvol,2)}</td><td class="hide-mobile">${n(r.breakout_quality)}</td>
      <td class="hide-mobile">${n(r.rs_score)}</td>
    </tr>
  `).join('');
  document.querySelectorAll('#tbody tr').forEach(tr=>tr.onclick=()=>loadDetail(tr.dataset.t));
}

async function loadDetail(t){
  selectedTicker=t;
  const p=document.getElementById('detailPanel');
  p.innerHTML='<div class="empty">불러오는 중...</div>';
  try{
    const d=await fetch(`data/details/${t}.json?ts=${Date.now()}`).then(r=>r.json());
    showDetail(d);
  }catch(e){
    p.innerHTML='<div class="empty">상세 데이터를 불러오지 못했습니다.</div>';
  }
}

function metric(k,v,cls=''){
  return `<div class="metric"><div class="k">${k}</div><div class="v ${cls}">${v}</div></div>`;
}

function showDetail(d){
  const a=d.analysis,m=d.meta,b=a.breakout_quality||{},tr=a.trade||{};
  const tri=a.triangle||{},rs=a.relative_strength||{},sup=a.support||{},res=a.resistance||{};
  const comps=b.components||{};

  document.getElementById('detailPanel').innerHTML=`
    <div class="detail">
      <div class="hero">
        <div>
          <h2>${m.name} <span style="color:var(--muted);font-size:12px">${m.ticker}</span></h2>
          <div class="setup ${a.direction==='BULLISH'?'bull':a.direction==='BEARISH'?'bear':'watch'}">${a.setup_label}</div>
        </div>
        <div class="scorebox">
          <strong class="${a.grade==='A+'?'Aplus':a.grade}">${a.grade}</strong>
          <div>${n(a.score)} / 100</div>
        </div>
      </div>

      <div class="metrics">
        ${metric('현재가',krw(a.price,0))}
        ${metric('시장 구조',a.structure?.code||'-')}
        ${metric('Breakout Quality',n(b.score))}
        ${metric('RVOL',n(b.rvol,2))}
        ${metric('20D 초과수익',pct(rs.excess_return))}
        ${metric('R/R 1',n(tr.rr1,2),tr.rr1>=1.8?'bull':'')}
        ${metric('지지 구간',sup.low!=null?`${krw(sup.low,0)} ~ ${krw(sup.high,0)}`:'-')}
        ${metric('저항 구간',res.low!=null?`${krw(res.low,0)} ~ ${krw(res.high,0)}`:'-')}
        ${metric('삼각수렴',tri.label||'-')}
      </div>

      <div id="chart" class="chart"></div>

      <div class="sectiontitle">Breakout Quality 구성</div>
      <div class="bars">
        ${Object.entries(comps).map(([k,v])=>`
          <div class="barrow">
            <span>${k}</span>
            <div class="bar"><i style="width:${Math.min(100,v/20*100)}%"></i></div>
            <b>${n(v)}</b>
          </div>
        `).join('')}
      </div>

      <div class="sectiontitle">Trade Structure</div>
      <div class="metrics">
        ${metric('Entry',krw(tr.entry,0))}
        ${metric('Stop / Invalidation',krw(tr.stop,0))}
        ${metric('Target 1',krw(tr.target1,0))}
        ${metric('Target 2',krw(tr.target2,0))}
        ${metric('Risk (ATR)',n(tr.risk_atr,2))}
        ${metric('Hard Filter',a.hard_filter_pass?'PASS':'WATCH',a.hard_filter_pass?'bull':'watch')}
      </div>
    </div>
  `;
  drawChart(a.chart,m.name);
}

/* ---------- Chart helpers ---------- */

function mobileMode(){
  return window.matchMedia('(max-width: 768px)').matches;
}

function visibleBars(allBars){
  const wanted=mobileMode()?52:92;
  return allBars.slice(Math.max(0,allBars.length-wanted));
}

function lineValue(line,x){
  if(!line||line.x1===line.x0)return null;
  const slope=(line.y1-line.y0)/(line.x1-line.x0);
  return line.y0+slope*(x-line.x0);
}

function fitLine(points){
  if(!points||points.length<2)return null;
  const xs=points.map(p=>Number(p.x));
  const ys=points.map(p=>Number(p.price));
  const n0=xs.length;
  const mx=xs.reduce((a,b)=>a+b,0)/n0;
  const my=ys.reduce((a,b)=>a+b,0)/n0;
  let num=0,den=0;
  for(let i=0;i<n0;i++){
    num+=(xs[i]-mx)*(ys[i]-my);
    den+=(xs[i]-mx)*(xs[i]-mx);
  }
  if(Math.abs(den)<1e-9)return null;
  const slope=num/den;
  const intercept=my-slope*mx;
  return {slope,intercept};
}

function quantile(values,q){
  const a=(values||[]).filter(Number.isFinite).sort((x,y)=>x-y);
  if(!a.length)return null;
  const pos=(a.length-1)*q;
  const base=Math.floor(pos);
  const rest=pos-base;
  return a[base+1]!==undefined?a[base]+rest*(a[base+1]-a[base]):a[base];
}

function typicalAtr(bars){
  const a=bars.map(b=>Number(b.atr)).filter(x=>Number.isFinite(x)&&x>0);
  return quantile(a,0.5)||0;
}

function tickSpec(dates){
  const desired=mobileMode()?5:8;
  if(dates.length<=desired){
    return {tickvals:dates,ticktext:dates.map(x=>x.slice(5).replace('-','/'))};
  }
  const idx=[];
  for(let i=0;i<desired;i++)idx.push(Math.round(i*(dates.length-1)/(desired-1)));
  const unique=[...new Set(idx)];
  return {
    tickvals:unique.map(i=>dates[i]),
    ticktext:unique.map(i=>dates[i].slice(5).replace('-','/'))
  };
}

function channelFromTrend(c,line,kind,visible){
  if(!line||!visible.length)return null;

  const firstX=visible[0].x;
  const lastX=visible[visible.length-1].x;
  const yFirst=lineValue(line,firstX);
  const yLast=lineValue(line,lastX);
  if(yFirst==null||yLast==null)return null;

  const atr=typicalAtr(visible);
  const sourceStart=Math.max(Number(line.x0||firstX),Number(c.bars?.[0]?.x||firstX));

  if(kind==='descending'){
    const lows=(c.pivot_lows||[]).filter(p=>p.x>=sourceStart&&p.x<=lastX).slice(-5);
    const fitted=fitLine(lows);
    let lowerFirst,lowerLast;

    if(fitted&&fitted.slope<0){
      lowerFirst=fitted.slope*firstX+fitted.intercept;
      lowerLast=fitted.slope*lastX+fitted.intercept;
    }else{
      const residuals=(c.bars||[])
        .filter(b=>b.x>=sourceStart&&b.x<=lastX)
        .map(b=>lineValue(line,b.x)-Number(b.low))
        .filter(x=>Number.isFinite(x)&&x>0);
      let width=quantile(residuals,0.78);
      if(width==null||width<=0)width=Math.max(atr*2.0,Math.abs(yLast)*0.035);
      if(atr>0)width=Math.min(Math.max(width,atr*1.2),atr*7.0);
      lowerFirst=yFirst-width;
      lowerLast=yLast-width;
    }

    if(!(lowerFirst<yFirst)||!(lowerLast<yLast))return null;
    return {
      kind,
      upper:[yFirst,yLast],
      lower:[lowerFirst,lowerLast],
      quality:Number(line.quality||0)
    };
  }

  const highs=(c.pivot_highs||[]).filter(p=>p.x>=sourceStart&&p.x<=lastX).slice(-5);
  const fitted=fitLine(highs);
  let upperFirst,upperLast;

  if(fitted&&fitted.slope>0){
    upperFirst=fitted.slope*firstX+fitted.intercept;
    upperLast=fitted.slope*lastX+fitted.intercept;
  }else{
    const residuals=(c.bars||[])
      .filter(b=>b.x>=sourceStart&&b.x<=lastX)
      .map(b=>Number(b.high)-lineValue(line,b.x))
      .filter(x=>Number.isFinite(x)&&x>0);
    let width=quantile(residuals,0.78);
    if(width==null||width<=0)width=Math.max(atr*2.0,Math.abs(yLast)*0.035);
    if(atr>0)width=Math.min(Math.max(width,atr*1.2),atr*7.0);
    upperFirst=yFirst+width;
    upperLast=yLast+width;
  }

  if(!(upperFirst>yFirst)||!(upperLast>yLast))return null;
  return {
    kind,
    upper:[upperFirst,upperLast],
    lower:[yFirst,yLast],
    quality:Number(line.quality||0)
  };
}

function addChannelTraces(traces,annotations,dates,channel){
  if(!channel)return;

  const descending=channel.kind==='descending';
  const lineColor=descending?'rgba(247,198,90,0.96)':'rgba(55,211,154,0.96)';
  const fillColor=descending?'rgba(247,198,90,0.095)':'rgba(55,211,154,0.085)';
  const label=descending?'하락 채널':'상승 채널';

  traces.push({
    type:'scatter',mode:'lines',
    x:[dates[0],dates[dates.length-1]],y:channel.lower,
    line:{color:lineColor,width:2},
    hoverinfo:'skip',showlegend:false
  });

  traces.push({
    type:'scatter',mode:'lines',
    x:[dates[0],dates[dates.length-1]],y:channel.upper,
    line:{color:lineColor,width:2},
    fill:'tonexty',fillcolor:fillColor,
    hoverinfo:'skip',showlegend:false
  });

  const labelY=(channel.upper[1]+channel.lower[1])/2;
  annotations.push({
    x:dates[dates.length-1],y:labelY,text:label,
    showarrow:false,xanchor:'right',yanchor:'middle',
    bgcolor:descending?'rgba(247,198,90,.12)':'rgba(55,211,154,.12)',
    bordercolor:lineColor,borderwidth:1,borderpad:3,
    font:{size:mobileMode()?9:10,color:lineColor}
  });
}

function lineAsTrace(line,visible,name,color,dash='solid'){
  if(!line||!visible.length)return null;
  const x0=visible[0].x,x1=visible[visible.length-1].x;
  const y0=lineValue(line,x0),y1=lineValue(line,x1);
  if(y0==null||y1==null)return null;
  return {
    type:'scatter',mode:'lines',
    x:[visible[0].date,visible[visible.length-1].date],
    y:[y0,y1],name,
    line:{color,width:1.6,dash},
    hoverinfo:'skip',showlegend:false
  };
}

function drawChart(c,name){
  if(!c||!c.bars||!c.bars.length)return;

  const bars=visibleBars(c.bars);
  const dates=bars.map(x=>x.date);
  const isMobile=mobileMode();
  const traces=[];
  const shapes=[];
  const ann=[];
  const x0=dates[0],x1=dates[dates.length-1];

  const descChannel=channelFromTrend(c,c.descending_trendline,'descending',bars);
  const ascChannel=channelFromTrend(c,c.ascending_trendline,'ascending',bars);

  const channels=[descChannel,ascChannel]
    .filter(Boolean)
    .filter(ch=>ch.quality===0||ch.quality>=48)
    .sort((a,b)=>b.quality-a.quality)
    .slice(0,2);

  channels.forEach(ch=>addChannelTraces(traces,ann,dates,ch));

  traces.push({
    type:'candlestick',
    x:dates,
    open:bars.map(x=>x.open),high:bars.map(x=>x.high),
    low:bars.map(x=>x.low),close:bars.map(x=>x.close),
    name:name,
    increasing:{line:{color:'#37d39a',width:1.25},fillcolor:'#37d39a'},
    decreasing:{line:{color:'#ff6b78',width:1.25},fillcolor:'#ff6b78'},
    whiskerwidth:.45,
    showlegend:false
  });

  function zone(z,color,label){
    if(!z)return;
    shapes.push({
      type:'rect',xref:'x',yref:'y',
      x0,x1,y0:z.low,y1:z.high,
      fillcolor:color,opacity:.10,
      line:{width:1,color}
    });
    ann.push({
      x:x1,y:z.center,text:label,showarrow:false,
      xanchor:'right',font:{size:isMobile?9:10,color}
    });
  }

  zone(c.support,'#37d39a','SUPPORT');
  zone(c.resistance,'#ff6b78','RESIST');

  if(c.poc!=null){
    shapes.push({
      type:'line',xref:'x',yref:'y',
      x0,x1,y0:c.poc,y1:c.poc,
      line:{color:'#a78bfa',width:1,dash:'dot'}
    });
  }

  if(c.triangle){
    const up=lineAsTrace(c.triangle.upper,bars,'삼각 상단','#f7c65a','dash');
    const lo=lineAsTrace(c.triangle.lower,bars,'삼각 하단','#5ca8ff','dash');
    if(up)traces.push(up);
    if(lo)traces.push(lo);
  }

  const ticks=tickSpec(dates);

  Plotly.newPlot('chart',traces,{
    paper_bgcolor:'transparent',
    plot_bgcolor:'transparent',
    font:{color:'#93a3bf'},
    margin:{
      l:8,
      r:isMobile?104:118,
      t:16,
      b:isMobile?34:38
    },
    xaxis:{
      type:'category',
      categoryorder:'array',
      categoryarray:dates,
      rangeslider:{visible:false},
      showgrid:true,
      gridcolor:'#18233a',
      zeroline:false,
      fixedrange:false,
      tickmode:'array',
      tickvals:ticks.tickvals,
      ticktext:ticks.ticktext,
      tickfont:{size:isMobile?9:10},
      automargin:true
    },
    yaxis:{
      gridcolor:'#18233a',
      side:'right',
      tickprefix:'₩',
      tickformat:',.0f',
      separatethousands:true,
      ticks:'outside',
      ticklen:4,
      tickfont:{size:isMobile?10:11},
      automargin:true,
      zeroline:false,
      fixedrange:false
    },
    shapes,
    annotations:ann,
    showlegend:false,
    hovermode:'x',
    dragmode:isMobile?'pan':'zoom'
  },{
    displayModeBar:false,
    responsive:true,
    scrollZoom:!isMobile
  });
}

['search','market','grade','sort'].forEach(
  id=>document.getElementById(id).addEventListener(id==='search'?'input':'change',render)
);
initChips();

fetch(`data/summary.json?ts=${Date.now()}`)
  .then(r=>r.json())
  .then(meta=>{
    DATA=meta.rows||[];
    cards(meta);
    render();
    if(DATA.length)loadDetail(DATA[0].ticker);
  })
  .catch(()=>{
    document.getElementById('tbody').innerHTML=
      '<tr><td colspan="9">summary.json을 불러오지 못했습니다.</td></tr>';
  });
</script>
</body>
</html>'''


def main() -> None:
    src = Path("price_structure_results")
    if not (src / "summary.json").exists():
        raise SystemExit(
            "price_structure_results/summary.json not found. "
            "Run price_structure_scanner.py first."
        )

    dst = Path("docs/price-structure")
    data = dst / "data"
    details = data / "details"
    details.mkdir(parents=True, exist_ok=True)

    shutil.copy2(src / "summary.json", data / "summary.json")
    if (src / "summary.csv").exists():
        shutil.copy2(src / "summary.csv", data / "summary.csv")

    for p in (src / "details").glob("*.json"):
        shutil.copy2(p, details / p.name)

    (dst / "index.html").write_text(HTML, encoding="utf-8")
    print(f"Built {dst / 'index.html'}")


if __name__ == "__main__":
    main()
