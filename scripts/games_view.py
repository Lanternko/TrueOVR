"""賽程檢視（使用者 2026-11-03）：嵌進名單頁當第三個檢視，和球員、戰力排行共用同一個眉頭，切換不重載。
架構照 rank_view.py：Shadow DOM 隔離樣式（色票與字型變數從名單頁繼承）、資料放獨立 JSON（build_games_data.py 產生），第一次進檢視（或閒置時預載）才 fetch；
box score 太大，按月分檔 games-box-YYYY-MM.json，點開某場才 fetch 該月（同月只抓一次）。
版面（使用者 2026-11-03 給三張參考圖）：橫向日期列（只列有賽事的日子，選中日置中，可滑動／箭頭翻頁）、單場卡片（隊徽在上、隊名、W-L、大比分、FINAL＋勝方三角）、
展開 box score（球員縮寫、欄位順序 MIN PTS REB AST FG 3PT FT STL BLK TO OREB DREB PF +/- 評分、TEAM TOTALS＋命中率）。gamelog 沒有先發／DNP，不分先發板凳、不列 DNP。
網址：/games/＝預設日（最近有已完賽場次的那天）；/games/2026-11-02/＝指定日；/games/2026-11-02/0022600172/＝展開某場。
對外 API：window.PureGames = {ensure(), open(date, gameId), hash()}，檢視切換由 site_header.JS 負責。"""
import json

# box 表欄位（標頭, 球員列／球隊合計的欄位鍵）：順序照參考圖，build_games_data.player_row／team_row 的鍵要對得上（gate 檢查）
BOX_COLS = [('MIN', 'min'), ('PTS', 'pts'), ('REB', 'reb'), ('AST', 'ast'), ('FG', 'fg'), ('3PT', 'tp'), ('FT', 'ft'), ('STL', 'stl'),
            ('BLK', 'blk'), ('TO', 'tov'), ('OREB', 'oreb'), ('DREB', 'dreb'), ('PF', 'pf'), ('+/-', 'pm'), ('評分', 'rt')]

STYLE = """@import url("https://fonts.googleapis.com/css2?family=Barlow+Condensed:ital,wght@1,700;1,800&family=Barlow+Condensed:wght@600;700&display=swap");
*{box-sizing:border-box}
:host{--nf:"Barlow Condensed","Arial Narrow",Impact,sans-serif;--blue:#4a90e2}
:host{display:block}
.gwroot{color:var(--fg);font-family:var(--f-body);font-size:14px}
.gww{max-width:1360px;margin:0 auto;padding-block:0 40px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));display:flex;flex-direction:column;gap:12px}
@media (min-width:641px){.gww{max-width:min(1360px,calc(var(--tw,1328px) + 32px))}}
.hd{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;border-bottom:3px solid var(--fg);padding-bottom:10px}
h1{font:italic 800 4.2rem/.85 var(--nf);text-transform:uppercase;margin:0;letter-spacing:-.01em}
h1 span{display:block;font:600 1rem var(--f-body);font-style:normal;letter-spacing:.3em;color:var(--muted);margin-top:8px;text-transform:none}
.dbar{display:flex;align-items:center;gap:6px;border-bottom:1px solid var(--line);padding:0 0 4px}  /* 日曆貼齊眉頭：眉頭自己有底線，這裡不再加頂線／上邊距 */
.strip{position:relative;flex:1;min-width:0;display:flex;overflow-x:auto;scrollbar-width:none;scroll-snap-type:x proximity;-webkit-overflow-scrolling:touch}
.strip::-webkit-scrollbar{display:none}
.strip::before,.strip::after{content:'';flex:0 0 calc(300% / 7)}  /* 頭尾各留 3 格空位：第一天／最後一天也能置中 */
.dc{flex:0 0 calc(100% / 7);scroll-snap-align:center;background:none;border:0;border-radius:6px;color:#8a929c;font:inherit;padding:8px 0 7px;cursor:pointer;text-align:center;line-height:1.15}
.dc:hover{background:#151b21}
.dc span{display:block;font:500 .95rem var(--f-body)}
.dc b{display:block;font:700 1.45rem var(--f-body);margin-top:2px}
.dc.on{color:var(--blue)}
.arw{flex:none;width:32px;height:44px;background:none;border:0;color:var(--muted);font:700 1.5rem/1 var(--f-body);cursor:pointer;border-radius:6px}
.arw:hover:not(:disabled){background:#151b21;color:var(--fg)}
.arw:disabled{opacity:.25;cursor:default}
.dx{flex:none;display:flex;gap:6px;align-items:center;padding-left:8px;border-left:1px solid var(--line)}
.dx button,.dx select{background:var(--panel);color:var(--fg);border:1px solid var(--line);border-radius:3px;font:600 .85rem var(--f-disp);letter-spacing:.04em;padding:5px 10px;cursor:pointer;min-height:32px}
.dx select{max-width:200px;padding-right:4px}
.dx button#latest{background:var(--gold);color:var(--gold-ink);border-color:var(--gold)}
.dx button#latest:disabled{background:var(--panel);color:var(--muted);border-color:var(--line);opacity:.5;cursor:default}
button:focus-visible,select:focus-visible,.gh:focus-visible,.dc:focus-visible{outline:2px solid var(--gold);outline-offset:1px}
.gl{display:flex;flex-direction:column;gap:8px}
.gm{--c1:124,133,145;--c2:124,133,145;position:relative;min-width:0;overflow:hidden;border:1px solid rgba(255,255,255,.14);border-radius:14px;background:#141a20;
  box-shadow:0 8px 24px rgba(0,0,0,.32)}
.gm.open{border-color:rgba(255,255,255,.28)}
.gh{background:radial-gradient(90% 260% at 0% 50%,rgba(var(--c1),.34) 0%,rgba(var(--c1),.14) 30%,rgba(var(--c1),0) 58%),radial-gradient(90% 260% at 100% 50%,rgba(var(--c2),.34) 0%,rgba(var(--c2),.14) 30%,rgba(var(--c2),0) 58%),linear-gradient(180deg,rgba(255,255,255,.11) 0%,rgba(255,255,255,.03) 48%,rgba(255,255,255,.05) 100%),#0a0e14;box-shadow:inset 0 1px 0 rgba(255,255,255,.2);display:grid;grid-template-columns:minmax(0,1fr) auto minmax(3rem,auto) auto minmax(0,1fr);align-items:center;gap:0 12px;padding:12px 20px;cursor:pointer;user-select:none}
.gh:hover{box-shadow:inset 0 0 0 999px rgba(255,255,255,.06)}
.tm{display:flex;align-items:center;justify-content:center;gap:10px;min-width:0}  /* 簡稱＋戰績擠在 icon 與比分之間：客隊 icon｜文字｜比分，主隊 比分｜文字｜icon */
.tm.home{flex-direction:row-reverse}
.tm .tx{display:flex;flex-direction:column;gap:1px;min-width:0}
.tm.away .tx{text-align:left}
.tm.home .tx{text-align:right}
.tm .lg{width:72px;height:72px;object-fit:contain}
.tm .nk{font:700 1.7rem/1.1 var(--f-body);letter-spacing:.04em;text-indent:.04em;color:var(--fg)}
.tm .rc{font:500 1.15rem/1.2 var(--f-body);color:#d3dae2;text-shadow:0 1px 2px rgba(0,0,0,.45);font-variant-numeric:tabular-nums}
.sc{font:700 3.6rem/1 var(--nf);font-variant-numeric:tabular-nums;color:var(--fg);width:1.6em;text-align:right}  /* 固定三位數寬：兩側等寬，中間的三角才會在兩個比分正中；客隊靠右、主隊靠左，數字都貼向中間 */
.sc.h{text-align:left}
.sc.lose{color:#7c858f}
.mid{text-align:center;font:700 1.2rem/1.25 var(--f-body);letter-spacing:.03em;text-indent:.03em;white-space:nowrap}
.mid .tri{display:inline-block;vertical-align:middle;width:0;height:0;border:8px solid transparent}
.mid .tri.l{border-left:0;border-right:12px solid var(--fg)}
.mid .tri.r{border-right:0;border-left:12px solid var(--fg)}
.mid{position:relative}
.mid .ot{font-weight:700;color:var(--fg)}
.mid .tri+.ot{position:absolute;left:50%;top:calc(50% + 11px);transform:translateX(-50%);font-size:.85rem;line-height:1;letter-spacing:.04em}  /* 延長賽標記：三角形正下方，不佔排版高度，三角才會維持在兩個比分的垂直正中 */
.mid .tbd{color:var(--fg);font-weight:700;font-size:1.5rem;line-height:1.1}
.mid .tbd+.ot{color:var(--muted);font-weight:500;font-size:.78rem}
.bh{text-align:center;color:var(--muted);font:500 .74rem var(--f-body);padding:0 0 6px;letter-spacing:.04em}
.bh span{position:relative;display:inline-block}
.bh i{position:absolute;left:100%;margin-left:.5em;font-style:normal}  /* 箭頭不佔排版寬度，文字本身才會至中 */
.bxw{border-top:1px solid var(--line);background:#10151a;padding:6px 20px 16px;display:flex;flex-direction:column;gap:14px;min-width:0}
.bt{display:flex;align-items:baseline;justify-content:space-between;gap:12px;margin:12px 0 8px;padding-bottom:10px;border-bottom:1px solid var(--line)}
.bt .tn{font:600 1.35rem var(--f-body);color:#7c858f;border-left:3px solid var(--line);padding-left:10px}
.bt .ts{font:700 2.4rem/1 var(--nf);color:#7c858f;font-variant-numeric:tabular-nums}
.bt.win .tn,.bt.win .ts{color:var(--fg)}
.bt.win .tn{border-left-color:var(--blue)}
.tbox{overflow-x:auto;-webkit-overflow-scrolling:touch;scroll-snap-type:x mandatory;scroll-padding-left:130px}  /* 捲動停在整欄邊界，不留半截欄位 */
th:not(.l){scroll-snap-align:start}
table{border-collapse:collapse;table-layout:fixed;width:100%;min-width:834px;font-variant-numeric:tabular-nums}  /* 固定欄寬：兩隊的表欄位對齊 */
th{color:var(--muted);font:600 .72rem var(--f-body);letter-spacing:.04em;padding:6px 2px;text-align:center;white-space:nowrap;width:44px}
th:nth-child(6),th:nth-child(7),th:nth-child(8){width:58px}
th.l{text-align:left;width:130px;padding-left:0;padding-right:6px;position:sticky;left:0;z-index:2;background:#10151a;box-shadow:6px 0 6px -4px #10151a}
td{padding:7px 2px;text-align:center;white-space:nowrap;font:500 .9rem var(--f-body);color:var(--fg)}
tbody tr.pl:nth-child(even) td{background:#0d1217}
td.l{text-align:left;position:sticky;left:0;z-index:1;background:#10151a;overflow:hidden;text-overflow:ellipsis;padding-left:0;padding-right:6px;box-shadow:6px 0 6px -4px #10151a}
tbody tr.pl:nth-child(even) td.l{background:#0d1217;box-shadow:6px 0 6px -4px #0d1217}
tr.dv td{padding:0;height:0;border-top:1px solid var(--line);background:none!important}
tr.tot td{border-top:1px solid var(--line);font-weight:700;padding-top:10px}
tr.tot td.l{font:700 .74rem var(--f-body);letter-spacing:.04em}
tr.pct td{color:var(--muted);font-size:.78rem;padding-top:0}
.pos{color:var(--g-a)}.neg{color:var(--g-f)}
.nob{color:var(--muted);padding:14px 0;font-size:.85rem}
.empty{color:var(--muted);padding:30px 0;text-align:center}
.note{color:var(--muted);font-size:.8rem;line-height:1.6;border-top:1px solid var(--line);padding-top:10px}
@media (max-width:640px){
  .gwroot{font-size:13px}
  h1{font-size:2.6rem}
  .gww{gap:10px}
  .dbar{flex-wrap:wrap}
  .arw{width:26px}
  .dc{flex-basis:20%}
  .strip::before,.strip::after{flex-basis:40%}
  .dc span{font-size:.8rem}.dc b{font-size:1.15rem}
  .dx{flex:1 1 100%;border-left:0;padding:4px 0 0;justify-content:flex-end}
  .gh{grid-template-columns:minmax(0,1fr) auto minmax(1.9rem,auto) auto minmax(0,1fr);gap:0 2px;padding:14px 8px 6px}
  .tm{gap:5px}
  .tm .lg{width:36px;height:36px}
  .tm .nk{font-size:1.05rem}.tm .rc{font-size:.8rem}
  .sc{font-size:3rem}
  .mid .tri{border-width:8px}.mid .tri.l{border-right-width:12px}.mid .tri.r{border-left-width:12px}
  .mid .tri+.ot{top:calc(50% + 11px);font-size:.8rem}
  .mid{font-size:.85rem}
  .bxw{padding:4px 10px 12px}
  th.l{width:92px}.tbox{scroll-padding-left:92px}table{min-width:666px}
  th{font-size:.66rem;width:36px}th:nth-child(6),th:nth-child(7),th:nth-child(8){width:48px}
  td{font-size:.82rem;padding:7px 1px}
  .bt .tn{font-size:1.05rem}.bt .ts{font-size:1.8rem}
}
.msg{color:var(--muted);padding:40px 16px;text-align:center}"""

BODY = """<div class="gwroot"><div class="msg" id="msg">載入中…</div>
<div class="gww" id="gww" hidden>
<div class="dbar"><button type="button" class="arw" id="sl" aria-label="往前翻">‹</button><div class="strip" id="strip" role="group" aria-label="選擇日期"></div><button type="button" class="arw" id="sr" aria-label="往後翻">›</button>
<div class="dx"><button type="button" id="latest">回到今天</button></div></div>
<div class="gl" id="gl"></div>
<div class="note" id="note"></div>
</div></div>"""

JS = r"""<script>(()=>{
const host=document.getElementById('gamesHost'),tpl=document.getElementById('gamesTpl');if(!host||!tpl)return;
const root=host.attachShadow({mode:'open'});root.append(tpl.content.cloneNode(true));
let D=null,loading=null,date=null,openId=null,want=null,built=false,pend=false;
const boxes={},ERR={err:true};   // 月份 → 'loading'｜{doc}｜ERR
const COLS=__COLS__;
const $=s=>root.querySelector(s),esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const CDN='https://cdn.nba.com/';
const logo=a=>'<img class="lg" alt="" loading="lazy" src="'+CDN+'logos/nba/'+D.teams[a].id+'/primary/L/logo.svg" onerror="this.style.visibility=\'hidden\'">';
// 球隊主色（官方主色；深色隊在深色底看不出來，改用提亮版或辨識度高的副色），給賽程卡片漸層用，格式 "r,g,b"
const TC={ATL:'#E03A3E',BOS:'#1E9B4F',BKN:'#9AA0A6',CHA:'#00A3B8',CHI:'#CE1141',CLE:'#A8174F',DAL:'#1E73BE',DEN:'#2D5DA8',DET:'#C8102E',GSW:'#2F63C0',
  HOU:'#CE1141',IND:'#2A5CA8',LAC:'#C8102E',LAL:'#7A45B8',MEM:'#5D76A9',MIA:'#B5123F',MIL:'#1B8A45',MIN:'#2B6AA8',NOP:'#2D5A9A',NYK:'#006BB6',
  OKC:'#007AC1',ORL:'#0077C0',PHI:'#006BB6',PHX:'#E56020',POR:'#E03A3E',SAC:'#7A47B0',SAS:'#A5ACB2',TOR:'#CE1141',UTA:'#4B7BD0',WAS:'#E31837'};
const TC2={ATL:'#C1D32F',BOS:'#BA9653',BKN:'#4A4F57',CHA:'#6A3FB5',CHI:'#3B424B',CLE:'#E0A21A',DAL:'#8E99A6',DEN:'#FEC524',DET:'#1D5FBF',GSW:'#FFC72C',
  HOU:'#8E9AA6',IND:'#FDBB30',LAC:'#1D5FBF',LAL:'#FDB927',MEM:'#F5B112',MIA:'#F9A01B',MIL:'#EEE1C6',MIN:'#78BE20',NOP:'#C8102E',NYK:'#F58426',
  OKC:'#EF6A3A',ORL:'#2C3138',PHI:'#ED174C',PHX:'#6A3FB5',POR:'#2C3138',SAC:'#6A7078',SAS:'#2C3138',TOR:'#8E99A6',UTA:'#F9A01B',WAS:'#2E67C0'};
const rgb=h=>[1,3,5].map(i=>parseInt(h.substr(i,2),16)),far=(x,y)=>Math.hypot(...rgb(x).map((v,i)=>v-rgb(y)[i]))>=130;
// 兩隊主色太像（例：TOR／LAC 都是紅）時換成其中一隊的副色，讓一場的兩側分得出來
const pair=(a,h)=>{const A=TC[a]||'#7c8591',H=TC[h]||'#7c8591',B=TC2[a]||A,K=TC2[h]||H,D=(x,y)=>Math.hypot(...rgb(x).map((v,i)=>v-rgb(y)[i]));let best=[A,H];if(!far(A,H))[[A,K],[B,H],[B,K]].forEach(p=>{if(D(...p)>D(...best))best=p});return best.map(c=>rgb(c).join(','))};
const MON=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'],WD=['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
const dp=d=>{const x=new Date(d+'T00:00:00Z');return {m:MON[x.getUTCMonth()]+' '+x.getUTCDate(),w:WD[x.getUTCDay()]}};
const sgn=v=>v>0?'+'+v:String(v);
const pct=s=>{const [m,a]=s.split('-').map(Number);return a?Math.round(100*m/a)+'%':'—'};
// 「今天」＝開賽時間（UTC+8）落在今天或更早的最後一個比賽日；美東晚上的場次在台灣是隔天早上。沒有開賽時間的日期當作美東日＋1 天開打
function today(){
  const k=t=>new Date(t+8*36e5).toISOString().slice(0,10),now=k(Date.now());
  const day=d=>{const ts=(D.games[d]||[]).map(g=>g.tip).filter(Boolean).map(t=>new Date(t).getTime());return ts.length?k(Math.min(...ts)):k(new Date(d+'T00:00:00Z').getTime()+16*36e5)};
  let r=D.dates[0]||D.latest;for(const d of D.dates){if(day(d)<=now)r=d;else break;}return r;
}
function hash(){return '/games/'+(date&&D&&!(date===today()&&!openId)?date+'/'+(openId?openId+'/':''):'')}
function sync(){if(/^\/games\//.test(location.pathname))history.replaceState(null,'',hash());}
function boxHtml(g){
  const b=boxes[date.slice(0,7)];
  if(!b||b==='loading')return '<div class="bxw"><div class="nob">載入 box score…</div></div>';
  if(b.err)return '<div class="bxw"><div class="nob">box score 載入失敗，收起再點一次重試。</div></div>';
  const x=b.doc.games[g.id];
  if(!x)return '<div class="bxw"><div class="nob">這場沒有 box score 資料（逐人數據還沒抓到）。</div></div>';
  const side=k=>{
    const a=g[k],t=x.team[k],ps=x[k],cell=(c,o)=>c[1]==='pm'?'<td class="'+(o.pm>0?'pos':o.pm<0?'neg':'')+'">'+sgn(o.pm)+'</td>':c[1]==='rt'?(o.rt==null?'<td>—</td>':'<td'+(o.fb?' title="這場抓不到防守對位資料，只用 box score 算"':'')+'>'+Math.max(0,o.rt).toFixed(1)+'</td>'):'<td>'+o[c[1]]+'</td>';
    const rows=ps.map((p,i)=>(i&&!p.st&&ps[i-1].st?'<tr class="dv"><td colspan="'+(COLS.length+1)+'"></td></tr>':'')+'<tr class="pl"><td class="l">'+esc(p.n)+'</td>'+COLS.map(c=>cell(c,p)).join('')+'</tr>').join('');
    const tot='<tr class="tot"><td class="l">TEAM TOTALS</td>'+COLS.map(c=>c[1]==='min'||c[1]==='pm'||c[1]==='rt'?'<td>—</td>':'<td>'+t[c[1]]+'</td>').join('')+'</tr>'
      +'<tr class="pct"><td class="l"></td>'+COLS.map(c=>'<td>'+(c[1]==='fg'?pct(t.fg)+'<br>FG':c[1]==='tp'?pct(t.tp)+'<br>3P':c[1]==='ft'?pct(t.ft)+'<br>FT':'')+'</td>').join('')+'</tr>';
    return '<div><div class="bt'+(g.winner===a?' win':'')+'"><span class="tn">'+esc(D.teams[a].name)+'</span><span class="ts">'+g.score[k]+'</span></div><div class="tbox"><table><thead><tr><th class="l">PLAYERS</th>'+COLS.map(c=>'<th>'+esc(c[0])+'</th>').join('')+'</tr></thead><tbody>'+rows+tot+'</tbody></table></div></div>';
  };
  return '<div class="bxw">'+side('away')+side('home')+'</div>';
}
function tipHtml(g){
  if(!g.tip)return '<span class="tbd">—</span>';
  const t=new Date(new Date(g.tip).getTime()+8*36e5),z=n=>String(n).padStart(2,'0');   // UTC+8 固定，不隨瀏覽器時區
  return '<span class="tbd">'+z(t.getUTCHours())+':'+z(t.getUTCMinutes())+'</span><div class="ot">'+(t.getUTCMonth()+1)+'/'+t.getUTCDate()+' UTC+8</div>';
}
function card(g){
  const pc=pair(g.away,g.home),fin=g.status==='final',w=fin?(g.winner===g.home?'home':'away'):'',op=openId===g.id;
  const tm=k=>'<div class="tm '+k+'">'+logo(g[k])+'<div class="tx"><div class="nk">'+esc(g[k])+'</div><div class="rc">'+esc(g.rec?g.rec[k]:'')+'</div></div></div>';
  const sc=k=>'<div class="sc'+(k==='home'?' h':'')+(fin&&w!==k?' lose':'')+'">'+(fin?g.score[k]:'')+'</div>';
  const mid=fin?'<div class="mid"><span class="tri '+(w==='away'?'l':'r')+'"></span>'+(g.ot?'<div class="ot">'+(g.ot>1?g.ot:'')+'OT</div>':'')+'</div>'
    :'<div class="mid">'+tipHtml(g)+'</div>';
  return '<div class="gm'+(op?' open':'')+'" data-id="'+g.id+'" style="--c1:'+pc[0]+';--c2:'+pc[1]+'"><div class="gh" role="button" tabindex="0" aria-expanded="'+op+'">'+tm('away')+sc('away')+mid+sc('home')+tm('home')+'</div>'
   +(op&&fin?boxHtml(g):'')+'</div>';
}
function build(){
  built=true;
  $('#strip').innerHTML=D.dates.map(d=>{const p=dp(d);return '<button type="button" class="dc" data-d="'+d+'" aria-pressed="false"><span>'+p.m+'</span><b>'+p.w+'</b></button>';}).join('');
}
function center(smooth){
  const s=$('#strip'),c=s.querySelector('.dc.on');if(!c)return;
  if(!s.clientWidth){pend=true;return;}   // 檢視還藏著（閒置預載）：量不到寬度，等 ResizeObserver
  const x=c.offsetLeft-(s.clientWidth-c.offsetWidth)/2;
  s.scrollTo({left:x,behavior:smooth&&Math.abs(x-s.scrollLeft)<s.clientWidth*3?'smooth':'auto'});   // 跳很遠（下拉選日期）就直接到位，不滑過上百格
}
function arrows(){const s=$('#strip');$('#sl').disabled=s.scrollLeft<=1;$('#sr').disabled=s.scrollLeft>=s.scrollWidth-s.clientWidth-1;}
function render(smooth){
  if(!built)build();
  const gs=D.games[date]||[];
  root.querySelectorAll('.dc').forEach(b=>{const on=b.dataset.d===date;b.classList.toggle('on',on);b.setAttribute('aria-pressed',String(on));});
  $('#latest').disabled=date===today();
  $('#gl').innerHTML=gs.length?gs.map(card).join(''):'<div class="empty">這天沒有賽事</div>';
  $('#note').innerHTML='比分與 box score 來自 NBA.com 官方 gamelog；W-L 是該場結束時的戰績（由 gamelog 逐場累計）；已完賽場次的日期以 gamelog 的比賽日（美東）為準，未開打場次取自賽程，開賽時間以 UTC+8 顯示。gamelog 沒有先發名單與 DNP，球員依上場分鐘排序。';
  center(smooth);
}
function go(d){date=d;openId=null;render(true);sync();}
function apply(){
  const w=want||{};want=null;
  date=w.d&&D.games[w.d]?w.d:today();
  const g=w.gid&&(D.games[date]||[]).find(x=>x.id===w.gid&&x.status==='final');
  openId=g?g.id:null;render(built);if(openId)fetchBox(date);
}
function fetchBox(d){
  const m=d.slice(0,7);
  if(boxes[m]&&boxes[m]!==ERR)return;
  boxes[m]='loading';
  fetch('/games-box-'+m+'.json',{cache:'no-cache'}).then(r=>{if(!r.ok)throw new Error(r.status);return r.json()}).then(doc=>({doc}),()=>ERR).then(v=>{boxes[m]=v;if(openId&&date.slice(0,7)===m){const y=scrollY;render(false);scrollTo(0,y);}});
}
function toggle(id){
  openId=openId===id?null:id;render(false);sync();
  if(openId)fetchBox(date);
}
$('#gl').addEventListener('click',e=>{const h=e.target.closest('.gh,.bh');if(!h)return;const m=h.closest('.gm'),g=(D.games[date]||[]).find(x=>x.id===m.dataset.id);if(g&&g.status==='final')toggle(g.id);});
$('#gl').addEventListener('keydown',e=>{if(e.key!=='Enter'&&e.key!==' ')return;const h=e.target.closest('.gh');if(!h)return;e.preventDefault();const id=h.parentElement.dataset.id;h.click();root.querySelector('.gm[data-id="'+id+'"] .gh')?.focus();});
$('#strip').addEventListener('click',e=>{const b=e.target.closest('.dc');if(b&&b.dataset.d!==date)go(b.dataset.d);});
$('#strip').addEventListener('scroll',arrows,{passive:true});
$('#sl').addEventListener('click',()=>{const s=$('#strip');s.scrollBy({left:-s.clientWidth*.85,behavior:'smooth'});});
$('#sr').addEventListener('click',()=>{const s=$('#strip');s.scrollBy({left:s.clientWidth*.85,behavior:'smooth'});});
$('#latest').addEventListener('click',()=>go(today()));
new ResizeObserver(()=>{if(pend&&$('#strip').clientWidth){pend=false;center(false);}arrows();}).observe($('#strip'));
function ensure(){
  if(!loading)loading=fetch('/games-data.json',{cache:'no-cache'}).then(r=>{if(!r.ok)throw new Error(r.status);return r.json()}).then(d=>{
    D=d;$('#msg').hidden=true;$('#gww').hidden=false;apply();
  }).catch(()=>{loading=null;$('#msg').textContent='賽程載入失敗，重新整理再試一次。';});
  return loading;
}
window.PureGames={ensure,hash,open(d,gid){want={d,gid};if(D)apply();}};
})()</script>""".replace('__COLS__', json.dumps(BOX_COLS))


def embed():
    """名單頁用：回傳 (宿主＋template 的 HTML, 腳本)。宿主放在 .wrap 前面，腳本放在眉頭腳本之前。"""
    tpl = '<template id="gamesTpl"><style>' + STYLE + '</style>' + BODY + '</template>'
    return '<div id="gamesHost"></div>' + tpl, JS
