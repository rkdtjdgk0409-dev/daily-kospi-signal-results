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
<title>US Price Structure Scanner</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
:root{
  --bg:#070b14;--panel:#0e1526;--panel2:#121b30;--line:#24304a;
  --text:#e8eefb;--muted:#93a3bf;--good:#37d39a;--warn:#f7c65a;
  --bad:#ff6b78;--blue:#5ca8ff;--purple:#a78bfa
}
*{box-sizing:border-box}
body{
  margin:0;background:linear-gradient(180deg,#070b14,#0a1020 45%,#070b14);
  color:var(--text);font-family:Inter,Pretendard,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif
}
.wrap{max-width:1500px;margin:auto;padding:18px}
.top{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}
.title h1{font-size:24px;margin:0 0 6px}.title p{margin:0;color:var(--muted);font-size:13px}
.actions{display:flex;flex-wrap:wrap;gap:8px}
.btn,.market-link,.range-btn{
  border:1px solid var(--line);background:rgba(18,27,48,.8);color:var(--text);
  padding:9px 12px;border-radius:10px;text-decoration:none;font-size:13px;cursor:pointer
}
.btn:hover,.market-link:hover,.range-btn:hover{border-color:#4a5c82}
.cards{display:grid;grid-template-columns:repeat(6,minmax(120px,1fr));gap:10px;margin:16px 0}
.card{background:rgba(14,21,38,.88);border:1px solid var(--line);border-radius:14px;padding:13px}
.card .k{color:var(--muted);font-size:12px}.card .v{font-size:20px;font-weight:800;margin-top:4px}
.toolbar{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}
.search{min-width:240px;flex:1;background:#0d1424;border:1px solid var(--line);color:var(--text);border-radius:10px;padding:10px 12px}
.select{background:#0d1424;border:1px solid var(--line);color:var(--text);border-radius:10px;padding:10px}
.chips{display:flex;gap:7px;overflow:auto;padding:2px 0 10px}
.chip{white-space:nowrap;border:1px solid var(--line);background:#0d1424;color:var(--muted);padding:7px 10px;border-radius:999px;cursor:pointer;font-size:12px}
.chip.active{color:#fff;border-color:#5c72a7;background:#18233c}
.layout{display:grid;grid-template-columns:minmax(620px,1.15fr) minmax(420px,.85fr);gap:12px}
.panel{background:rgba(14,21,38,.9);border:1px solid var(--line);border-radius:14px;overflow:hidden}
.panelhead{padding:12px 14px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:center}
.tablewrap{overflow:auto;max-height:76vh}
table{border-collapse:collapse;width:100%;font-size:12px}
th{position:sticky;top:0;background:#121b30;color:#9fb0cc;text-align:left;padding:10px 8px;border-bottom:1px solid var(--line);z-index:2;cursor:pointer}
td{padding:9px 8px;border-bottom:1px solid rgba(36,48,74,.65);white-space:nowrap}
tr{cursor:pointer}tr:hover{background:#131e35}
.name{font-weight:750}.ticker{color:var(--muted);font-size:10px}
.grade{font-weight:900}.Aplus,.A{color:var(--good)}.B{color:var(--warn)}.C,.D{color:#93a3bf}
.bull{color:var(--good)}.bear{color:var(--bad)}.watch{color:var(--warn)}
.pill{display:inline-block;padding:4px 7px;border:1px solid var(--line);border-radius:999px;font-size:10px}
.detail{padding:14px}.hero{display:flex;justify-content:space-between;gap:10px}
.hero h2{margin:0;font-size:20px}.hero .setup{margin-top:5px;font-size:13px}
.scorebox{text-align:right}.scorebox strong{font-size:26px}
.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:12px 0}
.metric{background:#10192d;border:1px solid var(--line);border-radius:10px;padding:9px}
.metric .k{font-size:10px;color:var(--muted)}.metric .v{font-size:13px;font-weight:700;margin-top:4px}
.chartbar{display:flex;justify-content:space-between;gap:8px;align-items:center;margin:8px 0 4px}
.charthelp{font-size:10px;color:var(--muted)}
.range-buttons{display:flex;gap:5px;flex-wrap:wrap;justify-content:flex-end}
.range-btn{padding:5px 8px;border-radius:8px;font-size:10px}
.chart{height:395px;width:100%;touch-action:pan-y}
.sectiontitle{font-weight:800;font-size:13px;margin:14px 0 7px}
.bars{display:grid;gap:7px}
.barrow{display:grid;grid-template-columns:105px 1fr 38px;gap:8px;align-items:center;font-size:11px;color:var(--muted)}
.bar{height:7px;border-radius:99px;background:#1d2942;overflow:hidden}
.bar i{display:block;height:100%;background:linear-gradient(90deg,#5ca8ff,#37d39a);border-radius:99px}
.note{font-size:11px;color:var(--muted);line-height:1.55;background:#0b1221;border:1px solid var(--line);border-radius:10px;padding:10px;margin-top:12px}
.empty{padding:35px;text-align:center;color:var(--muted)}

@media(max-width:1050px){
  .cards{grid-template-columns:repeat(3,1fr)}
  .layout{grid-template-columns:1fr}
  .tablewrap{max-height:48vh}
  .chart{height:340px}
}
@media(max-width:600px){
  .wrap{padding:10px}.top{display:block}.actions{margin-top:10px}.title h1{font-size:20px}
  .cards{grid-template-columns:repeat(2,1fr)}.layout{display:block}.panel{margin-bottom:11px}
  .detail{padding:10px 7px}.metrics{grid-template-columns:repeat(2,1fr)}
  .metric{padding:8px}.metric .v{font-size:12px}
  .chartbar{align-items:flex-start}.charthelp{max-width:120px;line-height:1.35}
  .range-buttons{max-width:220px}.range-btn{padding:4px 7px}
  .chart{height:292px}.tablewrap{max-height:48vh}.hide-mobile{display:none}
}
</style>
</head>
<body><div class="wrap">
<div class="top">
  <div class="title"><h1>Price Structure Scanner</h1><p>매물대 · 지지/저항 · 프로 평행채널 · 삼각수렴 · 돌파 품질 · R/R</p></div>
  <div class="actions"><a class="market-link" href="../">한국 시장</a><a class="market-link" href="../us/">미국 시장</a><a class="market-link" href="../us-position/">포지션 관리</a><button class="btn" onclick="location.reload()">새로고침</button></div>
</div>
<div class="cards" id="cards"></div>
<div class="toolbar">
  <input id="search" class="search" placeholder="종목명 또는 코드 검색"/>
  <select id="market" class="select"><option value="ALL">전체 지수</option><option>S&amp;P 500</option><option>NASDAQ-100</option></select>
  <select id="grade" class="select"><option value="ALL">전체 등급</option><option>A+</option><option>A</option><option>B</option><option>C</option><option>D</option></select>
  <select id="sort" class="select"><option value="score">점수순</option><option value="rr1">R/R순</option><option value="breakout_quality">돌파품질순</option><option value="rvol">RVOL순</option><option value="rs_score">상대강도순</option></select>
</div>
<div class="chips" id="chips"></div>
<div class="layout">
  <section class="panel">
    <div class="panelhead"><strong>종목 스캔</strong><span id="count" style="color:var(--muted);font-size:11px"></span></div>
    <div class="tablewrap"><table><thead><tr><th>종목</th><th>등급</th><th>셋업</th><th>점수</th><th>구조</th><th>R/R</th><th>RVOL</th><th class="hide-mobile">돌파품질</th><th class="hide-mobile">RS</th></tr></thead><tbody id="tbody"></tbody></table></div>
  </section>
  <section class="panel" id="detailPanel"><div class="empty">왼쪽에서 종목을 선택하세요.</div></section>
</div>
<div class="note">
  차트에는 긴 과거 거래 데이터를 미리 포함해 두므로 마우스 휠/트랙패드/핀치로 축소하면 기존 화면 밖의 과거 캔들이 나타납니다.
  평행채널은 단순히 고점 2개·저점 2개를 잇지 않고, 가격 중심 추세를 robust regression으로 찾은 뒤 상·하단을 평행하게 만들고
  실제 swing touch, 채널 내부 체류율, 추세 강도, 최근 접촉, 이탈 횟수를 종합해 품질 기준을 통과한 채널만 표시합니다.
</div>
</div>

<script>
let DATA=[], FILTER='ALL', selectedTicker=null, CHART_N=0;
const SETUPS=['ALL','BREAKOUT_READY','CONFIRMED_BREAKOUT','TRENDLINE_BREAKOUT','TRIANGLE_BREAKOUT','RETEST_ENTRY','SUPPORT_BOUNCE','FAILED_BREAKOUT','SUPPORT_BREAKDOWN','COMPRESSION_WATCH'];
const labels={ALL:'전체',BREAKOUT_READY:'⚡ 돌파 임박',CONFIRMED_BREAKOUT:'🔥 저항 돌파',TRENDLINE_BREAKOUT:'↗ 추세선 돌파',TRIANGLE_BREAKOUT:'△ 삼각 돌파',RETEST_ENTRY:'✓ 리테스트',SUPPORT_BOUNCE:'🛡 지지 반등',FAILED_BREAKOUT:'⚠ 실패 돌파',SUPPORT_BREAKDOWN:'↓ 지지 이탈',COMPRESSION_WATCH:'◇ 수렴 관찰'};

function n(v,d=1){return v==null||Number.isNaN(+v)?'-':Number(v).toLocaleString('ko-KR',{maximumFractionDigits:d})}
function usd(v,d=0){return v==null||Number.isNaN(+v)?'-':'$'+Number(v).toLocaleString('ko-KR',{maximumFractionDigits:d})}
function pct(v){return v==null?'-':(v*100).toFixed(1)+'%'}
function setupClass(r){return r.direction==='BULLISH'?'bull':r.direction==='BEARISH'?'bear':'watch'}
function mobileMode(){return window.matchMedia('(max-width: 768px)').matches}

function initChips(){
  document.getElementById('chips').innerHTML=SETUPS.map(x=>`<button class="chip ${x==='ALL'?'active':''}" data-x="${x}">${labels[x]||x}</button>`).join('');
  document.querySelectorAll('.chip').forEach(b=>b.onclick=()=>{FILTER=b.dataset.x;document.querySelectorAll('.chip').forEach(x=>x.classList.toggle('active',x===b));render();});
}
function cards(meta){
  const rows=meta.rows||[];
  const c=[['분석 종목',rows.length],['A+ / A',rows.filter(x=>x.grade==='A+'||x.grade==='A').length],['Hard Filter',rows.filter(x=>x.hard_filter_pass).length],['돌파 임박',rows.filter(x=>x.setup==='BREAKOUT_READY').length],['확정 돌파',rows.filter(x=>['CONFIRMED_BREAKOUT','TRENDLINE_BREAKOUT','TRIANGLE_BREAKOUT'].includes(x.setup)).length],['평행채널',rows.filter(x=>x.parallel_channel).length]];
  document.getElementById('cards').innerHTML=c.map(x=>`<div class="card"><div class="k">${x[0]}</div><div class="v">${x[1]}</div></div>`).join('');
}
function filtered(){
  const q=document.getElementById('search').value.trim().toLowerCase(),m=document.getElementById('market').value,g=document.getElementById('grade').value,s=document.getElementById('sort').value;
  let a=DATA.filter(r=>(!q||r.name.toLowerCase().includes(q)||r.ticker.includes(q))&&(m==='ALL'||String(r.market||'').includes(m))&&(g==='ALL'||r.grade===g)&&(FILTER==='ALL'||r.setup===FILTER));
  a.sort((x,y)=>(Number(y[s])||-999)-(Number(x[s])||-999));return a;
}
function render(){
  const a=filtered();document.getElementById('count').textContent=`${a.length}개`;
  document.getElementById('tbody').innerHTML=a.map(r=>`<tr data-t="${r.ticker}"><td><div class="name">${r.name}</div><div class="ticker">${r.ticker} · ${r.market}</div></td><td class="grade ${r.grade==='A+'?'Aplus':r.grade}">${r.grade}${r.hard_filter_pass?' ✓':''}</td><td class="${setupClass(r)}"><span class="pill">${r.setup_label}</span></td><td><b>${n(r.score)}</b></td><td>${r.structure_code}</td><td>${n(r.rr1,2)}</td><td>${n(r.rvol,2)}</td><td class="hide-mobile">${n(r.breakout_quality)}</td><td class="hide-mobile">${n(r.rs_score)}</td></tr>`).join('');
  document.querySelectorAll('#tbody tr').forEach(tr=>tr.onclick=()=>loadDetail(tr.dataset.t));
}
async function loadDetail(t){
  selectedTicker=t;const p=document.getElementById('detailPanel');p.innerHTML='<div class="empty">불러오는 중...</div>';
  try{const d=await fetch(`data/details/${t}.json?ts=${Date.now()}`).then(r=>r.json());showDetail(d)}
  catch(e){p.innerHTML='<div class="empty">상세 데이터를 불러오지 못했습니다.</div>'}
}
function metric(k,v,cls=''){return `<div class="metric"><div class="k">${k}</div><div class="v ${cls}">${v}</div></div>`}

function showDetail(d){
  const a=d.analysis,m=d.meta,b=a.breakout_quality||{},tr=a.trade||{},tri=a.triangle||{},rs=a.relative_strength||{},sup=a.support||{},res=a.resistance||{},ch=a.parallel_channel||{};
  const comps=b.components||{};
  const channelMetric=ch.label?`${ch.label} · Q${n(ch.quality,0)} · ${ch.status_label||''}`:'-';
  document.getElementById('detailPanel').innerHTML=`<div class="detail">
    <div class="hero"><div><h2>${m.name} <span style="color:var(--muted);font-size:12px">${m.ticker}</span></h2><div class="setup ${a.direction==='BULLISH'?'bull':a.direction==='BEARISH'?'bear':'watch'}">${a.setup_label}</div></div><div class="scorebox"><strong class="${a.grade==='A+'?'Aplus':a.grade}">${a.grade}</strong><div>${n(a.score)} / 100</div></div></div>
    <div class="metrics">
      ${metric('현재가',usd(a.price,2))}${metric('시장 구조',a.structure?.code||'-')}${metric('Breakout Quality',n(b.score))}
      ${metric('RVOL',n(b.rvol,2))}${metric('20D 초과수익',pct(rs.excess_return))}${metric('R/R 1',n(tr.rr1,2),tr.rr1>=1.8?'bull':'')}
      ${metric('지지 구간',sup.low!=null?`${usd(sup.low,2)} ~ ${usd(sup.high,2)}`:'-')}
      ${metric('저항 구간',res.low!=null?`${usd(res.low,2)} ~ ${usd(res.high,2)}`:'-')}
      ${metric('평행채널',channelMetric,ch.direction==='ASCENDING'?'bull':ch.direction==='DESCENDING'?'watch':'')}
    </div>
    <div class="chartbar"><div class="charthelp">휠/핀치로 축소하면 더 과거 데이터가 보입니다.</div><div class="range-buttons"><button class="range-btn" onclick="setRangeBars(22)">1M</button><button class="range-btn" onclick="setRangeBars(66)">3M</button><button class="range-btn" onclick="setRangeBars(132)">6M</button><button class="range-btn" onclick="setRangeBars(252)">1Y</button><button class="range-btn" onclick="setRangeBars(CHART_N)">전체</button></div></div>
    <div id="chart" class="chart"></div>
    <div class="sectiontitle">Breakout Quality 구성</div><div class="bars">${Object.entries(comps).map(([k,v])=>`<div class="barrow"><span>${k}</span><div class="bar"><i style="width:${Math.min(100,v/20*100)}%"></i></div><b>${n(v)}</b></div>`).join('')}</div>
    <div class="sectiontitle">Trade Structure</div><div class="metrics">${metric('Entry',usd(tr.entry,2))}${metric('Stop / Invalidation',usd(tr.stop,2))}${metric('Target 1',usd(tr.target1,2))}${metric('Target 2',usd(tr.target2,2))}${metric('Risk (ATR)',n(tr.risk_atr,2))}${metric('Hard Filter',a.hard_filter_pass?'PASS':'WATCH',a.hard_filter_pass?'bull':'watch')}</div>
  </div>`;
  drawChart(a.chart,m.name);
}

function dateForX(bars,x){
  if(!bars.length)return null;
  let best=bars[0],dist=Math.abs(Number(best.x)-Number(x));
  for(const b of bars){
    const d=Math.abs(Number(b.x)-Number(x));
    if(d<dist){best=b;dist=d}
  }
  return best.date;
}
function addParallelChannel(traces,ann,bars,ch){
  if(!ch||!ch.label||!bars.length)return;
  const descending=ch.direction==='DESCENDING';
  const color=descending?'rgba(247,198,90,.98)':'rgba(55,211,154,.98)';
  const fill=descending?'rgba(247,198,90,.095)':'rgba(55,211,154,.085)';
  const xStart=dateForX(bars,ch.x0),xEnd=dateForX(bars,ch.x1);
  if(!xStart||!xEnd)return;

  traces.push({type:'scatter',mode:'lines',x:[xStart,xEnd],y:[ch.lower_y0,ch.lower_y1],line:{color,width:2.1},hoverinfo:'skip',showlegend:false});
  traces.push({type:'scatter',mode:'lines',x:[xStart,xEnd],y:[ch.upper_y0,ch.upper_y1],line:{color,width:2.1},fill:'tonexty',fillcolor:fill,hoverinfo:'skip',showlegend:false});
  traces.push({type:'scatter',mode:'lines',x:[xStart,xEnd],y:[ch.center_y0,ch.center_y1],line:{color,width:1.25,dash:'dash'},hoverinfo:'skip',showlegend:false});

  ann.push({x:xEnd,y:ch.current_center,text:`${ch.label} Q${Math.round(ch.quality)} · ${ch.status_label||''}`,showarrow:false,xanchor:'right',yanchor:'middle',bgcolor:descending?'rgba(247,198,90,.12)':'rgba(55,211,154,.12)',bordercolor:color,borderwidth:1,borderpad:3,font:{size:mobileMode()?9:10,color}});
}
function lineValue(line,x){
  if(!line||line.x1===line.x0)return null;
  const slope=(line.y1-line.y0)/(line.x1-line.x0);return line.y0+slope*(x-line.x0);
}
function lineTrace(line,bars,color,dash='dash'){
  if(!line||!bars.length)return null;
  const first=bars[0],last=bars[bars.length-1],y0=lineValue(line,first.x),y1=lineValue(line,last.x);
  if(y0==null||y1==null)return null;
  return {type:'scatter',mode:'lines',x:[first.date,last.date],y:[y0,y1],line:{color,width:1.5,dash},hoverinfo:'skip',showlegend:false};
}
function initialRange(c,bars){
  const n=bars.length, wanted=mobileMode()?(Number(c.initial_mobile_bars)||55):(Number(c.initial_desktop_bars)||100);
  return [Math.max(-.5,n-wanted-.5),n-.5];
}
function setRangeBars(count){
  if(!CHART_N)return;
  const c=Math.max(10,Math.min(Number(count)||CHART_N,CHART_N));
  Plotly.relayout('chart',{'xaxis.range':[Math.max(-.5,CHART_N-c-.5),CHART_N-.5]});
}
function drawChart(c,name){
  if(!c||!c.bars||!c.bars.length)return;
  const bars=c.bars,dates=bars.map(x=>x.date);CHART_N=bars.length;
  const traces=[],shapes=[],ann=[],x0=dates[0],x1=dates[dates.length-1],isMobile=mobileMode();

  addParallelChannel(traces,ann,bars,c.parallel_channel);

  traces.push({
    type:'candlestick',x:dates,open:bars.map(x=>x.open),high:bars.map(x=>x.high),low:bars.map(x=>x.low),close:bars.map(x=>x.close),
    name,increasing:{line:{color:'#37d39a',width:1.2},fillcolor:'#37d39a'},decreasing:{line:{color:'#ff6b78',width:1.2},fillcolor:'#ff6b78'},whiskerwidth:.45,showlegend:false
  });

  function zone(z,color,label){
    if(!z)return;
    shapes.push({type:'rect',xref:'x',yref:'y',x0,x1,y0:z.low,y1:z.high,fillcolor:color,opacity:.09,line:{width:1,color}});
    ann.push({x:x1,y:z.center,text:label,showarrow:false,xanchor:'right',font:{size:isMobile?9:10,color}});
  }
  zone(c.support,'#37d39a','SUPPORT');zone(c.resistance,'#ff6b78','RESIST');
  if(c.poc!=null)shapes.push({type:'line',xref:'x',yref:'y',x0,x1,y0:c.poc,y1:c.poc,line:{color:'#a78bfa',width:1,dash:'dot'}});

  if(c.triangle){
    const up=lineTrace(c.triangle.upper,bars,'#f7c65a','dot'),lo=lineTrace(c.triangle.lower,bars,'#5ca8ff','dot');
    if(up)traces.push(up);if(lo)traces.push(lo);
  }

  Plotly.newPlot('chart',traces,{
    paper_bgcolor:'transparent',plot_bgcolor:'transparent',font:{color:'#93a3bf'},
    margin:{l:8,r:isMobile?100:116,t:14,b:isMobile?34:38},
    xaxis:{
      type:'category',categoryorder:'array',categoryarray:dates,range:initialRange(c,bars),
      rangeslider:{visible:false},showgrid:true,gridcolor:'#18233a',zeroline:false,
      automargin:true,tickfont:{size:isMobile?9:10},fixedrange:false
    },
    yaxis:{
      gridcolor:'#18233a',side:'right',tickformat:',.2f',tickprefix:'$',
      separatethousands:true,ticks:'outside',ticklen:4,tickfont:{size:isMobile?10:11},
      automargin:true,zeroline:false,fixedrange:false
    },
    shapes,annotations:ann,showlegend:false,hovermode:'x',dragmode:isMobile?'pan':'zoom'
  },{
    displayModeBar:false,responsive:true,scrollZoom:true,doubleClick:'reset'
  });
}

['search','market','grade','sort'].forEach(id=>document.getElementById(id).addEventListener(id==='search'?'input':'change',render));
initChips();
fetch(`data/summary.json?ts=${Date.now()}`).then(r=>r.json()).then(meta=>{DATA=meta.rows||[];cards(meta);render();if(DATA.length)loadDetail(DATA[0].ticker)}).catch(()=>document.getElementById('tbody').innerHTML='<tr><td colspan="9">summary.json을 불러오지 못했습니다.</td></tr>');
</script></body></html>'''


def main() -> None:
    src = Path("us_price_structure_results")
    if not (src / "summary.json").exists():
        raise SystemExit(
            "us_price_structure_results/summary.json not found. "
            "Run us_price_structure_scanner.py first."
        )

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
