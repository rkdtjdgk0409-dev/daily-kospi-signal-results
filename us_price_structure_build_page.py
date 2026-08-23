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
<title>US Wave Structure Scanner</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
:root{
  --bg:#070b14;--panel:#0e1526;--panel2:#121b30;--line:#24304a;
  --text:#e8eefb;--muted:#93a3bf;--good:#37d39a;--warn:#f7c65a;
  --bad:#ff6b78;--blue:#5ca8ff;--purple:#a78bfa;--cyan:#2dd4bf
}
*{box-sizing:border-box}
body{margin:0;background:linear-gradient(180deg,#070b14,#0a1020 45%,#070b14);color:var(--text);font-family:Inter,Pretendard,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.wrap{max-width:1500px;margin:auto;padding:18px}
.top{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}
.title h1{font-size:24px;margin:0 0 6px}.title p{margin:0;color:var(--muted);font-size:13px;line-height:1.5}
.actions{display:flex;flex-wrap:wrap;gap:8px}
.btn,.market-link,.range-btn,.toggle-btn{border:1px solid var(--line);background:rgba(18,27,48,.8);color:var(--text);padding:9px 12px;border-radius:10px;text-decoration:none;font-size:13px;cursor:pointer}
.btn:hover,.market-link:hover,.range-btn:hover,.toggle-btn:hover{border-color:#4a5c82}
.cards{display:grid;grid-template-columns:repeat(6,minmax(120px,1fr));gap:10px;margin:16px 0}
.card{background:rgba(14,21,38,.88);border:1px solid var(--line);border-radius:14px;padding:13px}.card .k{color:var(--muted);font-size:12px}.card .v{font-size:20px;font-weight:800;margin-top:4px}
.toolbar{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}.search{min-width:240px;flex:1;background:#0d1424;border:1px solid var(--line);color:var(--text);border-radius:10px;padding:10px 12px}.select{background:#0d1424;border:1px solid var(--line);color:var(--text);border-radius:10px;padding:10px}
.chips{display:flex;gap:7px;overflow:auto;padding:2px 0 10px}.chip{white-space:nowrap;border:1px solid var(--line);background:#0d1424;color:var(--muted);padding:7px 10px;border-radius:999px;cursor:pointer;font-size:12px}.chip.active{color:#fff;border-color:#5c72a7;background:#18233c}
.layout{display:grid;grid-template-columns:minmax(620px,1.15fr) minmax(420px,.85fr);gap:12px}.panel{background:rgba(14,21,38,.9);border:1px solid var(--line);border-radius:14px;overflow:hidden}.panelhead{padding:12px 14px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:center}.tablewrap{overflow:auto;max-height:76vh}
table{border-collapse:collapse;width:100%;font-size:12px}th{position:sticky;top:0;background:#121b30;color:#9fb0cc;text-align:left;padding:10px 8px;border-bottom:1px solid var(--line);z-index:2}td{padding:9px 8px;border-bottom:1px solid rgba(36,48,74,.65);white-space:nowrap}tr{cursor:pointer}tr:hover{background:#131e35}.name{font-weight:750}.ticker{color:var(--muted);font-size:10px}.grade{font-weight:900}.Aplus,.A{color:var(--good)}.B{color:var(--warn)}.C,.D{color:#93a3bf}.bull{color:var(--good)}.bear{color:var(--bad)}.watch{color:var(--warn)}.pill{display:inline-block;padding:4px 7px;border:1px solid var(--line);border-radius:999px;font-size:10px}
.detail{padding:14px}.hero{display:flex;justify-content:space-between;gap:10px}.hero h2{margin:0;font-size:20px}.hero .setup{margin-top:5px;font-size:13px;font-weight:750}.scorebox{text-align:right}.scorebox strong{font-size:26px}.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:12px 0}.metric{background:#10192d;border:1px solid var(--line);border-radius:10px;padding:9px}.metric .k{font-size:10px;color:var(--muted)}.metric .v{font-size:13px;font-weight:700;margin-top:4px}
.scenario{background:#0b1221;border:1px solid #24304a;border-radius:12px;padding:12px;margin:11px 0}.scenario-title{font-weight:900;font-size:14px;margin-bottom:8px}.scenario-line{display:grid;grid-template-columns:30px 1fr;gap:7px;align-items:start;font-size:12px;line-height:1.55;margin-top:6px}.scenario-num{color:var(--cyan);font-weight:900}.scenario-key{color:var(--purple);font-weight:800}.scenario-levels{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}.level-pill{font-size:10px;border:1px solid var(--line);border-radius:999px;padding:5px 8px;background:#10192d;color:var(--muted)}
.chartbar{display:flex;justify-content:space-between;gap:8px;align-items:center;margin:8px 0 4px}.charthelp{font-size:10px;color:var(--muted)}.chart-controls{display:flex;gap:5px;flex-wrap:wrap;justify-content:flex-end}.range-btn,.toggle-btn{padding:5px 8px;border-radius:8px;font-size:10px}.toggle-btn.active{border-color:#5ca8ff;background:#172746;color:#fff}.chart{height:430px;width:100%;touch-action:pan-y}.sectiontitle{font-weight:800;font-size:13px;margin:14px 0 7px}.bars{display:grid;gap:7px}.barrow{display:grid;grid-template-columns:105px 1fr 38px;gap:8px;align-items:center;font-size:11px;color:var(--muted)}.bar{height:7px;border-radius:99px;background:#1d2942;overflow:hidden}.bar i{display:block;height:100%;background:linear-gradient(90deg,#5ca8ff,#37d39a);border-radius:99px}.note{font-size:11px;color:var(--muted);line-height:1.55;background:#0b1221;border:1px solid var(--line);border-radius:10px;padding:10px;margin-top:12px}.empty{padding:35px;text-align:center;color:var(--muted)}
@media(max-width:1050px){.cards{grid-template-columns:repeat(3,1fr)}.layout{grid-template-columns:1fr}.tablewrap{max-height:48vh}.chart{height:360px}}
@media(max-width:600px){.wrap{padding:10px}.top{display:block}.actions{margin-top:10px}.title h1{font-size:20px}.cards{grid-template-columns:repeat(2,1fr)}.layout{display:block}.panel{margin-bottom:11px}.detail{padding:10px 7px}.metrics{grid-template-columns:repeat(2,1fr)}.metric{padding:8px}.metric .v{font-size:12px}.chartbar{align-items:flex-start;display:block}.charthelp{margin-bottom:7px}.chart-controls{justify-content:flex-start}.chart{height:315px}.tablewrap{max-height:48vh}.hide-mobile{display:none}.scenario{padding:10px}}
</style>
</head>
<body><div class="wrap">
<div class="top">
  <div class="title"><h1>Price Structure Scanner</h1><p>엘리어트형 파동 · 하락/상승 평행채널 · 매물대 · Fibonacci · 돌파/리테스트 · 무효화/목표</p></div>
  <div class="actions"><a class="market-link" href="../">한국 시장</a><a class="market-link" href="../us/">미국 시장</a><a class="market-link" href="../us-position/">포지션 관리</a><button class="btn" onclick="location.reload()">새로고침</button></div>
</div>
<div class="cards" id="cards"></div>
<div class="toolbar">
  <input id="search" class="search" placeholder="종목명 또는 코드 검색"/>
  <select id="market" class="select"><option value="ALL">전체 지수</option><option>S&amp;P 500</option><option>NASDAQ-100</option></select>
  <select id="grade" class="select"><option value="ALL">전체 등급</option><option>A+</option><option>A</option><option>B</option><option>C</option><option>D</option></select>
  <select id="sort" class="select"><option value="score">종합점수순</option><option value="wave_confidence">파동신뢰도순</option><option value="rr1">R/R순</option><option value="rvol">RVOL순</option><option value="rs_score">상대강도순</option></select>
</div>
<div class="chips" id="chips"></div>
<div class="layout">
  <section class="panel">
    <div class="panelhead"><strong>종목 스캔</strong><span id="count" style="color:var(--muted);font-size:11px"></span></div>
    <div class="tablewrap"><table><thead><tr><th>종목</th><th>등급</th><th>파동/시나리오</th><th>점수</th><th>구조</th><th>신뢰도</th><th>R/R</th><th class="hide-mobile">RVOL</th><th class="hide-mobile">RS</th></tr></thead><tbody id="tbody"></tbody></table></div>
  </section>
  <section class="panel" id="detailPanel"><div class="empty">왼쪽에서 종목을 선택하세요.</div></section>
</div>
<div class="note">이 페이지의 파동 번호는 확정 예측이 아니라 <b>확인된 스윙 저점/고점 + 채널 전환 + 지지/저항 합류</b>를 기반으로 한 시나리오 카운트입니다. 특히 2파→3파 후보는 1파 시작 저점이 깨지면 무효화합니다. 기존 검색·필터·줌·모바일 조작 방식은 그대로 유지됩니다.</div>
</div>
<script>
let DATA=[], FILTER='ALL', selectedTicker=null, CHART_N=0, CHART_FUTURE=0, CURRENT_DETAIL=null;
let SHOW={wave:true,fib:true,channel:true,zones:true,forecast:true};
const SETUPS=['ALL','WAVE2_PULLBACK','WAVE3_ADVANCE','CHANNEL_REVERSAL','WAVE4_PULLBACK','WAVE5_ADVANCE','RESISTANCE_PAUSE','BASE_BUILDING','STRUCTURE_RISK'];
const labels={ALL:'전체',WAVE2_PULLBACK:'🔥 2파→3파',WAVE3_ADVANCE:'🚀 3파 진행',CHANNEL_REVERSAL:'↗ 채널 돌파',WAVE4_PULLBACK:'↘ 4파 조정',WAVE5_ADVANCE:'↗ 5파/연장',RESISTANCE_PAUSE:'⏸ 저항 숨고르기',BASE_BUILDING:'◇ 바닥 관찰',STRUCTURE_RISK:'⚠ 구조 훼손'};
function n(v,d=1){return v==null||Number.isNaN(+v)?'-':Number(v).toLocaleString('ko-KR',{maximumFractionDigits:d})}
function usd(v,d=2){return v==null||Number.isNaN(+v)?'-':'$'+Number(v).toLocaleString('ko-KR',{maximumFractionDigits:d})}
function pct(v){return v==null?'-':(Number(v)*100).toFixed(1)+'%'}
function setupClass(r){return r.direction==='BULLISH'?'bull':r.direction==='BEARISH'?'bear':'watch'}
function mobileMode(){return window.matchMedia('(max-width: 768px)').matches}
function initChips(){document.getElementById('chips').innerHTML=SETUPS.map(x=>`<button class="chip ${x==='ALL'?'active':''}" data-x="${x}">${labels[x]||x}</button>`).join('');document.querySelectorAll('.chip').forEach(b=>b.onclick=()=>{FILTER=b.dataset.x;document.querySelectorAll('.chip').forEach(x=>x.classList.toggle('active',x===b));render();});}
function cards(meta){const rows=meta.rows||[];const c=[['분석 종목',rows.length],['A+ / A',rows.filter(x=>x.grade==='A+'||x.grade==='A').length],['2파→3파',rows.filter(x=>x.setup==='WAVE2_PULLBACK').length],['3파 진행',rows.filter(x=>x.setup==='WAVE3_ADVANCE').length],['채널 돌파',rows.filter(x=>x.setup==='CHANNEL_REVERSAL').length],['저항 대기',rows.filter(x=>x.setup==='RESISTANCE_PAUSE').length]];document.getElementById('cards').innerHTML=c.map(x=>`<div class="card"><div class="k">${x[0]}</div><div class="v">${x[1]}</div></div>`).join('');}
function filtered(){const q=document.getElementById('search').value.trim().toLowerCase(),m=document.getElementById('market').value,g=document.getElementById('grade').value,s=document.getElementById('sort').value;let a=DATA.filter(r=>(!q||String(r.name).toLowerCase().includes(q)||String(r.ticker).toLowerCase().includes(q))&&(m==='ALL'||String(r.market||'').includes(m))&&(g==='ALL'||r.grade===g)&&(FILTER==='ALL'||r.setup===FILTER));a.sort((x,y)=>(Number(y[s])||-999)-(Number(x[s])||-999));return a;}
function render(){const a=filtered();document.getElementById('count').textContent=`${a.length}개`;document.getElementById('tbody').innerHTML=a.map(r=>`<tr data-t="${r.ticker}"><td><div class="name">${r.name}</div><div class="ticker">${r.ticker} · ${r.market}</div></td><td class="grade ${r.grade==='A+'?'Aplus':r.grade}">${r.grade}${r.hard_filter_pass?' ✓':''}</td><td class="${setupClass(r)}"><span class="pill">${r.setup_label}</span></td><td><b>${n(r.score)}</b></td><td>${r.structure_code}</td><td>${n(r.wave_confidence,0)}%</td><td>${n(r.rr1,2)}</td><td class="hide-mobile">${n(r.rvol,2)}</td><td class="hide-mobile">${n(r.rs_score)}</td></tr>`).join('');document.querySelectorAll('#tbody tr').forEach(tr=>tr.onclick=()=>loadDetail(tr.dataset.t));}
async function loadDetail(t){selectedTicker=t;const p=document.getElementById('detailPanel');p.innerHTML='<div class="empty">불러오는 중...</div>';try{const d=await fetch(`data/details/${t}.json?ts=${Date.now()}`).then(r=>r.json());CURRENT_DETAIL=d;showDetail(d)}catch(e){p.innerHTML='<div class="empty">상세 데이터를 불러오지 못했습니다.</div>'}}
function metric(k,v,cls=''){return `<div class="metric"><div class="k">${k}</div><div class="v ${cls}">${v}</div></div>`}
function toggleButton(key,label){return `<button class="toggle-btn ${SHOW[key]?'active':''}" onclick="toggleLayer('${key}')">${label}</button>`}
function toggleLayer(key){SHOW[key]=!SHOW[key];if(CURRENT_DETAIL)showDetail(CURRENT_DETAIL)}
function showDetail(d){const a=d.analysis,m=d.meta,w=a.wave||{},sc=w.scenario||{},sup=a.support||{},res=a.resistance||{},ch=a.parallel_channel||{},b=a.breakout_quality||{},tr=a.trade||{},rs=a.relative_strength||{},ez=w.entry_zone||{};const channelMetric=ch.label?`${ch.label} · Q${n(ch.quality,0)} · ${ch.status_label||''}`:'-';const setupCls=a.direction==='BULLISH'?'bull':a.direction==='BEARISH'?'bear':'watch';document.getElementById('detailPanel').innerHTML=`<div class="detail">
<div class="hero"><div><h2>${m.name} <span style="color:var(--muted);font-size:12px">${m.ticker}</span></h2><div class="setup ${setupCls}">${a.setup_label}</div></div><div class="scorebox"><strong class="${a.grade==='A+'?'Aplus':a.grade}">${a.grade}</strong><div>${n(a.score)} / 100</div></div></div>
<div class="metrics">${metric('현재가',usd(a.price))}${metric('파동 상태',w.label||'-',setupCls)}${metric('파동 신뢰도',`${n(w.confidence,0)}%`,w.confidence>=72?'bull':'')}${metric('지지 구간',sup.low!=null?`${usd(sup.low)} ~ ${usd(sup.high)}`:'-')}${metric('저항 구간',res.low!=null?`${usd(res.low)} ~ ${usd(res.high)}`:'-')}${metric('평행채널',channelMetric,ch.direction==='ASCENDING'?'bull':ch.direction==='DESCENDING'?'watch':'')}${metric('확인 가격',usd(sc.confirm_price))}${metric('무효화',usd(sc.invalidation_price),'bear')}${metric('목표 1 / 2',`${usd(sc.target1)} / ${usd(sc.target2)}`,'bull')}</div>
<div class="scenario"><div class="scenario-title">${w.label||'구조 시나리오'}</div><div class="scenario-line"><div class="scenario-num">01</div><div>${sc.thesis||'구조 확인 중'}</div></div><div class="scenario-line"><div class="scenario-num">02</div><div><span class="scenario-key">대응:</span> ${sc.action||'-'}</div></div><div class="scenario-levels"><span class="level-pill">Entry zone ${ez.low!=null?usd(ez.low)+' ~ '+usd(ez.high):'-'}</span><span class="level-pill">Confirm ${usd(sc.confirm_price)}</span><span class="level-pill">Invalid ${usd(sc.invalidation_price)}</span><span class="level-pill">RVOL ${n(b.rvol,2)}</span><span class="level-pill">RS ${n(rs.score)}</span><span class="level-pill">R/R ${n(tr.rr1,2)}</span></div></div>
<div class="chartbar"><div class="charthelp">주말 공백 없이 표시 · 휠/핀치 축소 시 과거 캔들 표시</div><div class="chart-controls">${toggleButton('wave','파동')}${toggleButton('fib','Fib')}${toggleButton('channel','채널')}${toggleButton('zones','매물대')}${toggleButton('forecast','예상경로')}<button class="range-btn" onclick="setRangeBars(66)">3M</button><button class="range-btn" onclick="setRangeBars(132)">6M</button><button class="range-btn" onclick="setRangeBars(252)">1Y</button><button class="range-btn" onclick="setRangeBars(CHART_N)">전체</button></div></div>
<div id="chart" class="chart"></div>
<div class="sectiontitle">판단 구성</div><div class="bars">${[['파동 신뢰도',w.confidence||0],['채널 전환',w.channel_transition?.score||0],['지지 강도',sup.strength||0],['돌파 품질',b.score||0],['상대강도',rs.score||0]].map(([k,v])=>`<div class="barrow"><span>${k}</span><div class="bar"><i style="width:${Math.min(100,Number(v)||0)}%"></i></div><b>${n(v)}</b></div>`).join('')}</div>
</div>`;drawChart(a.chart,m.name);}
function dateForX(bars,x){if(!bars.length)return null;let best=bars[0],dist=Math.abs(Number(best.x)-Number(x));for(const b of bars){const d=Math.abs(Number(b.x)-Number(x));if(d<dist){best=b;dist=d}}return best.date;}
function lineValue(line,x){if(!line||line.x1===line.x0)return null;const slope=(line.y1-line.y0)/(line.x1-line.x0);return line.y0+slope*(x-line.x0)}
function lineTrace(line,bars,color,dash='dash'){if(!line||!bars.length)return null;const first=bars[0],last=bars[bars.length-1],y0=lineValue(line,first.x),y1=lineValue(line,last.x);if(y0==null||y1==null)return null;return {type:'scatter',mode:'lines',x:[first.date,last.date],y:[y0,y1],line:{color,width:1.5,dash},hoverinfo:'skip',showlegend:false}}
function addParallelChannel(traces,ann,bars,ch){if(!SHOW.channel||!ch||!ch.label||!bars.length)return;const descending=ch.direction==='DESCENDING';const color=descending?'rgba(247,198,90,.98)':'rgba(55,211,154,.98)',fill=descending?'rgba(247,198,90,.10)':'rgba(55,211,154,.09)';const xStart=dateForX(bars,ch.x0),xEnd=dateForX(bars,ch.x1);if(!xStart||!xEnd)return;traces.push({type:'scatter',mode:'lines',x:[xStart,xEnd],y:[ch.lower_y0,ch.lower_y1],line:{color,width:2.0},hoverinfo:'skip',showlegend:false});traces.push({type:'scatter',mode:'lines',x:[xStart,xEnd],y:[ch.upper_y0,ch.upper_y1],line:{color,width:2.0},fill:'tonexty',fillcolor:fill,hoverinfo:'skip',showlegend:false});traces.push({type:'scatter',mode:'lines',x:[xStart,xEnd],y:[ch.center_y0,ch.center_y1],line:{color,width:1.0,dash:'dash'},hoverinfo:'skip',showlegend:false});ann.push({x:xEnd,y:ch.current_center,text:`${ch.label} · ${ch.status_label||''}`,showarrow:false,xanchor:'right',bgcolor:'rgba(10,16,32,.82)',bordercolor:color,borderwidth:1,borderpad:3,font:{size:mobileMode()?8:10,color}})}
function addWave(traces,ann,w){if(!SHOW.wave||!w||!w.points||!w.points.length)return;const pts=w.points;traces.push({type:'scatter',mode:'lines+markers',x:pts.map(p=>p.date),y:pts.map(p=>p.price),line:{color:'#f7c65a',width:2.1},marker:{size:5,color:'#e8eefb'},hoverinfo:'skip',showlegend:false});pts.forEach(p=>ann.push({x:p.date,y:p.price,text:p.wave==='0'?'LOW':`(${p.wave})`,showarrow:true,arrowhead:0,ax:0,ay:p.kind==='H'?-24:24,font:{size:10,color:'#e8eefb'},arrowcolor:'#93a3bf'}))}
function addFib(shapes,ann,bars,w){if(!SHOW.fib||!w||!w.fib||!w.fib.retracement||!bars.length)return;const pts=w.points||[],start=pts.length>1?pts[1].date:bars[Math.max(0,bars.length-80)].date,x1=bars[bars.length-1].date;const retr=w.fib.retracement;[['0.382','#a78bfa'],['0.500','#5ca8ff'],['0.618','#2dd4bf']].forEach(([k,color])=>{if(retr[k]==null)return;shapes.push({type:'line',xref:'x',yref:'y',x0:start,x1,y0:retr[k],y1:retr[k],line:{color,width:1,dash:'dot'}});ann.push({x:x1,y:retr[k],text:`Fib ${k}`,showarrow:false,xanchor:'right',font:{size:8,color}})});const ext=w.extensions||{};const extStart=pts.length>2?pts[2].date:start;[['1.000','#37d39a'],['1.272','#f7c65a'],['1.618','#ff9f43']].forEach(([k,color])=>{if(ext[k]==null)return;shapes.push({type:'line',xref:'x',yref:'y',x0:extStart,x1,y0:ext[k],y1:ext[k],line:{color,width:1,dash:'dash'}});ann.push({x:x1,y:ext[k],text:`EXT ${k}`,showarrow:false,xanchor:'right',font:{size:8,color}})})}
function futureBusinessDate(lastDate,steps){let d=new Date(lastDate+'T00:00:00');let added=0;while(added<steps){d.setDate(d.getDate()+1);const day=d.getDay();if(day!==0&&day!==6)added++}return d.toISOString().slice(0,10)}
function addForecast(traces,ann,bars,w){if(!SHOW.forecast||!w||!w.forecast||w.forecast.length<2||!bars.length)return;const last=bars[bars.length-1],xs=w.forecast.map(p=>{const delta=Math.max(0,Math.round(Number(p.x)-Number(last.x)));return delta===0?last.date:futureBusinessDate(last.date,delta)}),ys=w.forecast.map(p=>p.price);traces.push({type:'scatter',mode:'lines+markers',x:xs,y:ys,line:{color:'rgba(232,238,251,.9)',width:2,dash:'dot'},marker:{size:4,color:'#e8eefb'},hoverinfo:'skip',showlegend:false});w.forecast.forEach((p,i)=>ann.push({x:xs[i],y:ys[i],text:p.label||'',showarrow:false,yshift:i===w.forecast.length-1?10:0,font:{size:9,color:'#e8eefb'},bgcolor:'rgba(7,11,20,.7)'}))}
function initialRange(c,bars,futureCount=0){const n=bars.length,wanted=mobileMode()?(Number(c.initial_mobile_bars)||55):(Number(c.initial_desktop_bars)||100);return [Math.max(-.5,n-wanted-.5),n+futureCount-.5]}
function setRangeBars(count){if(!CHART_N)return;const c=Math.max(10,Math.min(Number(count)||CHART_N,CHART_N));Plotly.relayout('chart',{'xaxis.range':[Math.max(-.5,CHART_N-c-.5),CHART_N+CHART_FUTURE-.5]})}
function drawChart(c,name){if(!c||!c.bars||!c.bars.length)return;const bars=c.bars,dates=bars.map(x=>x.date),w=c.wave||{};CHART_N=bars.length;let futureCats=[];if(SHOW.forecast&&w.forecast&&w.forecast.length){const last=bars[bars.length-1];futureCats=w.forecast.map(p=>{const delta=Math.max(0,Math.round(Number(p.x)-Number(last.x)));return delta===0?last.date:futureBusinessDate(last.date,delta)}).filter(x=>!dates.includes(x));futureCats=[...new Set(futureCats)]}CHART_FUTURE=futureCats.length;const categoryDates=[...dates,...futureCats];const traces=[],shapes=[],ann=[],x0=dates[0],x1=dates[dates.length-1],isMobile=mobileMode();addParallelChannel(traces,ann,bars,c.parallel_channel);traces.push({type:'candlestick',x:dates,open:bars.map(x=>x.open),high:bars.map(x=>x.high),low:bars.map(x=>x.low),close:bars.map(x=>x.close),name,increasing:{line:{color:'#37d39a',width:1.2},fillcolor:'#37d39a'},decreasing:{line:{color:'#ff6b78',width:1.2},fillcolor:'#ff6b78'},whiskerwidth:.45,showlegend:false});function zone(z,color,label){if(!SHOW.zones||!z)return;shapes.push({type:'rect',xref:'x',yref:'y',x0,x1,y0:z.low,y1:z.high,fillcolor:color,opacity:.10,line:{width:1,color}});ann.push({x:x1,y:z.center,text:label,showarrow:false,xanchor:'right',font:{size:isMobile?8:10,color},bgcolor:'rgba(7,11,20,.65)'})}zone(c.support,'#37d39a','SUPPORT');zone(c.resistance,'#ff6b78','RESIST');if(SHOW.zones&&c.poc!=null)shapes.push({type:'line',xref:'x',yref:'y',x0,x1,y0:c.poc,y1:c.poc,line:{color:'#a78bfa',width:1,dash:'dot'}});addFib(shapes,ann,bars,w);addWave(traces,ann,w);addForecast(traces,ann,bars,w);Plotly.newPlot('chart',traces,{paper_bgcolor:'transparent',plot_bgcolor:'transparent',font:{color:'#93a3bf'},margin:{l:8,r:isMobile?92:118,t:14,b:isMobile?34:38},xaxis:{type:'category',categoryorder:'array',categoryarray:categoryDates,range:initialRange(c,bars,CHART_FUTURE),rangeslider:{visible:false},showgrid:true,gridcolor:'#18233a',zeroline:false,automargin:true,tickfont:{size:isMobile?9:10},fixedrange:false},yaxis:{gridcolor:'#18233a',side:'right',tickformat:',.2f',tickprefix:'$',separatethousands:true,ticks:'outside',ticklen:4,tickfont:{size:isMobile?10:11},automargin:true,zeroline:false,fixedrange:false},shapes,annotations:ann,showlegend:false,hovermode:'x',dragmode:isMobile?'pan':'zoom'},{displayModeBar:false,responsive:true,scrollZoom:true,doubleClick:'reset'})}
['search','market','grade','sort'].forEach(id=>document.getElementById(id).addEventListener(id==='search'?'input':'change',render));initChips();fetch(`data/summary.json?ts=${Date.now()}`).then(r=>r.json()).then(meta=>{DATA=meta.rows||[];cards(meta);render();if(DATA.length)loadDetail(DATA[0].ticker)}).catch(()=>document.getElementById('tbody').innerHTML='<tr><td colspan="9">summary.json을 불러오지 못했습니다.</td></tr>');
</script></body></html>'''


def main() -> None:
    src = Path("us_price_structure_results")
    if not (src / "summary.json").exists():
        raise SystemExit("us_price_structure_results/summary.json not found. Run us_price_structure_scanner.py first.")
    dst = Path("docs/us-price-structure")
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
