"""名單頁眉頭（使用者 2026-11-02「重新設計眉頭，參考 arammeta」）：黏頂毛玻璃一列＝PUREOVR 字標｜球員・球隊・戰力排行・賽程分頁｜篩選・設定・搜尋。
2026-11-02「直接合併單頁」：2026-27 名單頁內嵌戰力排行檢視（rank_view.py），三個分頁共用同一個眉頭；用 body[data-view] 切檢視、
history.pushState＋popstate 管網址（/rank/、/rank/LAL/、/games/、/games/2026-11-02/[GAME_ID/]）、View Transition 讓底線滑過去；
2025-26 卡片頁沒有排行與賽程檢視，兩個分頁連到 /rank/、/games/（部署時各複製一份 index.html）。
原本的控制項（#posSeg、#teamPick、#modeSeg、#q、賽季切換、更新說明）在頁尾腳本裡原封搬進眉頭，事件與 render 不用改；
舊的 .top 標題列與 .ctrl 控制列只剩空殼，直接隱藏。add_season_nav 之後呼叫。"""
import re

from season_nav import RING

ICON = {
    'filter': '<path d="M4.2 4h15.6a1 1 0 0 1 .78 1.63L14.5 13.2v5.3a1 1 0 0 1-.55.9l-3 1.5A1 1 0 0 1 9.5 20v-6.8L3.42 5.63A1 1 0 0 1 4.2 4z" fill="currentColor" stroke="none"/>',
    'gear': '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
    'search': '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
}


def _svg(k, size=16):
    return (f'<svg viewBox="0 0 24 24" width="{size}" height="{size}" fill="none" stroke="currentColor" stroke-width="2" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICON[k]}</svg>')


SEASON = {'inseason': '2026-27', 'card': '2025-26'}

CSS = """<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Righteous&display=swap">
<style>
body{margin:0}  /* 名單頁原本留瀏覽器預設 8px，眉頭在球員／戰力排行兩頁之間會上下左右跳 */
.mast{--mbg:#030406;--mfg:#f3f5f8;--mfg2:#fff;position:sticky;top:0;z-index:50;background:rgba(3,4,6,.94);  /* 使用者 2026-11-03：眉頭用更深的黑 */
  -webkit-backdrop-filter:saturate(180%) blur(14px);backdrop-filter:saturate(180%) blur(14px);border-bottom:1px solid var(--line);transition:box-shadow .25s,border-color .25s}
.mast.scrolled{border-bottom-color:transparent;box-shadow:0 6px 22px -10px rgba(0,0,0,.6)}
.mast-in{display:flex;align-items:center;gap:16px;height:56px;max-width:1360px;margin:0 auto;box-sizing:border-box;
  padding:0 max(16px,env(safe-area-inset-right,0px)) 0 max(16px,env(safe-area-inset-left,0px))}
.mbrand{display:inline-flex;align-items:baseline;gap:9px;text-decoration:none;flex:none;width:206px}  /* 固定寬：Righteous 字型晚到時分頁不會被推動 */
.mbrand .mlogo{width:22px;height:22px;flex:none;align-self:center}  /* 五格評分環 icon（使用者 2026-11-04 選 E4）；裁到環本身、無外框，直徑略大於大寫字高、中心對齊 */
.mbrand b{font:400 1.6rem/1 "Righteous",var(--f-disp);letter-spacing:.02em;color:var(--mfg)}  /* 字標全白單色（使用者 2026-11-04）：顏色留給評分環 */
.mbrand:hover b{color:var(--mfg2)}
.mbrand small{font:600 .78rem var(--f-disp);letter-spacing:.06em;color:#dfe4ea;font-variant-numeric:tabular-nums}
.mtabs{position:relative;display:flex;align-items:center;gap:2px;margin:0 auto 0 8px}
.mtab,.mtabs .tpick summary{appearance:none;box-sizing:border-box;margin:0;border:0;background:none;color:var(--mfg);font:600 1.02rem/1 var(--f-body);letter-spacing:.02em;
  height:36px;padding:0 14px;border-radius:8px;cursor:pointer;white-space:nowrap;display:flex;align-items:center;gap:6px;transition:color .14s,background-color .14s}
.mtabs .tpick summary img{width:18px;height:18px;margin:0}
.mtab{text-decoration:none}
.mtab:hover,.mtabs .tpick summary:hover{color:var(--mfg2);background:color-mix(in srgb,var(--fg) 7%,transparent)}
.mtab[aria-selected="true"],.mtabs .tpick.on summary{color:var(--mfg2);background:var(--panel)}
.mtabs .tpick summary{border:0}
/* 選隊沿用 #teamPick 的舊規則（ID 選擇器，手機版會把「球隊」縮成 .85rem），這裡一律用 #teamPick 蓋回，選隊前後字級相同 */
/* 使用者 2026-11-03：實心三角形 ▾ 太淡又偏左，改成清楚的細 V 形箭頭（邊框畫的，任何字型都一樣粗） */
.mtabs #teamPick summary::after,.mtab-pick::after{content:"";display:inline-block;width:6px;height:6px;border:solid currentColor;border-width:0 1.6px 1.6px 0;transform:translateY(-2px) rotate(45deg);margin:0 0 0 8px;opacity:.85;flex:none}
.mtabs #teamPick:not(.on) summary{font-size:0;gap:0}
.mtabs #teamPick:not(.on) summary::before{content:"球隊";font-size:1.02rem;letter-spacing:.02em}
/* 「球隊」格固定最小寬（最寬的 GSW＋隊徽約 104px），選哪隊後面的「戰力排行」都不會被推動 */
.mtabs #teamPick summary,.mtab-pick{min-width:76px;justify-content:center}
/* 使用者 2026-11-03：選完球隊不要下箭頭，格子縮窄（只剩隊徽＋隊名）；選隊前後同寬（最小 76px） */
.mtabs #teamPick.on summary::after{display:none}
/* 使用者 2026-11-04：回到全部球員時仍顯示上次的球隊（隊徽＋隊名，不反白、不加箭頭），點了回到那隊 */
.mtabs #teamPick.last:not(.on) summary{font-size:1.02rem;gap:6px}
.mtabs #teamPick.last:not(.on) summary::before{content:none}
.mtabs #teamPick.last summary::after{display:none}
.mtabs .tpick.on summary{border:0;color:var(--mfg2)}
.mtabs .tpick summary:focus-visible,.mtab:focus-visible,.micon:focus-visible{outline:2px solid var(--gold);outline-offset:1px}
.mind{position:absolute;bottom:0;left:var(--ix,0);width:var(--iw,0);height:3px;border-radius:3px 3px 0 0;background:var(--gold);
  box-shadow:0 0 8px color-mix(in srgb,var(--gold) 50%,transparent);pointer-events:none}
html{scrollbar-gutter:stable}  /* 排行檢視比名單短，捲軸有無不同會讓眉頭橫向位移 */
body[data-view="rank"] .wrap,body[data-view="games"] .wrap{display:none}
body:not([data-view="rank"]) #rankHost,body:not([data-view="games"]) #gamesHost{display:none}
body[data-view="rank"] #mPosRow,body[data-view="rank"] .msearch,body[data-view="games"] #mPosRow,body[data-view="games"] .msearch{display:none}  /* 位置、搜尋只對球員檢視有意義；賽季切換在篩選裡，各檢視都留著 */
body[data-view="rank"] .mtabs #teamPick.on summary,body[data-view="games"] .mtabs #teamPick.on summary{color:var(--mfg);background:none}
.mtabs #teamPick[open] summary,body[data-view="rank"] .mtabs #teamPick[open].on summary,body[data-view="games"] .mtabs #teamPick[open].on summary{color:var(--gold-ink);background:var(--gold)}  /* 點開選隊：黃色高亮 */
.mind{view-transition-name:tab-ind}  /* 只給底線命名；.wrap 整頁快照太大 */
.mast.vt-running .mind{transition:none!important}  /* 切檢視時由 View Transition 負責滑動，不再疊 CSS 過渡 */
::view-transition-group(tab-ind){animation-duration:.22s;animation-timing-function:cubic-bezier(.2,.7,.2,1)}
::view-transition-old(root),::view-transition-new(root){animation-duration:.12s}
.mast:not(.ready) .mind{visibility:hidden}
.mast:not(.ready) .mtab[aria-selected="true"]{position:relative}
.mast:not(.ready) .mtab[aria-selected="true"]::before{content:"";position:absolute;left:0;right:0;bottom:0;height:3px;border-radius:3px 3px 0 0;background:var(--gold);
  box-shadow:0 0 8px color-mix(in srgb,var(--gold) 50%,transparent)}
.mast.ready .mind{transition:left .22s cubic-bezier(.2,.7,.2,1),width .22s cubic-bezier(.2,.7,.2,1)}
.macts{display:flex;align-items:center;gap:8px;flex:none}
.mpop{position:relative}
.mpop>summary{list-style:none}
.mpop>summary::-webkit-details-marker{display:none}
/* 使用者 2026-11-03：圖示用更飽和的純白，不要外框、不要文字說明 */
.micon{position:relative;display:inline-flex;align-items:center;justify-content:center;width:38px;height:38px;box-sizing:border-box;padding:0;background:transparent;color:#fff;
  border:0;border-radius:8px;cursor:pointer;transition:background-color .12s}
.micon>span{display:none}
.micon svg{width:21px;height:21px;stroke-width:2.2}
.micon:hover,.mpop[open]>.micon{background:rgba(255,255,255,.12)}
.micon:active{transform:scale(.96)}
.micon.dot::after{content:"";position:absolute;top:5px;right:5px;width:7px;height:7px;border-radius:50%;background:var(--gold);box-shadow:0 0 0 2px var(--mbg)}
.mpanel{position:absolute;right:0;top:calc(100% + 8px);z-index:20;min-width:220px;box-sizing:border-box;padding:12px;background:var(--panel-2);
  border:1px solid var(--line);border-radius:8px;box-shadow:0 14px 36px rgba(0,0,0,.6);display:grid;gap:12px}
.mrow{display:grid;gap:6px}
.mrow>b{color:var(--muted);font:600 .72rem var(--f-disp);letter-spacing:.12em;text-transform:uppercase}
.mrow .seg{justify-self:start}
.mrow .seg a{display:block;background:var(--panel);color:var(--muted);border-right:1px solid var(--line);font:600 .9rem var(--f-disp);letter-spacing:.04em;padding:6px 12px;text-decoration:none;white-space:nowrap}
.mrow .seg a:last-child{border-right:0}
.mrow .seg a[aria-current="page"]{background:var(--gold);color:var(--gold-ink)}
.mrow .seg{flex:none;width:max-content}
.mrow .seg button{height:32px;padding:0 12px;white-space:nowrap}
.mrow .pnote summary{height:32px;box-sizing:border-box;padding:0 12px}
.mast .pn{position:fixed;left:auto;right:max(16px,calc((100vw - 1360px)/2 + 16px));top:calc(var(--mh,57px) + 8px);width:min(560px,calc(100vw - 32px));max-height:calc(100vh - 80px)}
.msearch{position:relative;display:flex;align-items:center}
.msearch .sbox{display:none;position:absolute;right:0;top:calc(100% + 8px);z-index:20;width:300px;box-sizing:border-box;padding:10px;background:var(--panel-2);border:1px solid var(--line);border-radius:8px;box-shadow:0 14px 36px rgba(0,0,0,.6);align-items:center}
.msearch.open .sbox{display:flex}
.msearch .sbox>svg{position:absolute;left:20px;color:var(--muted);pointer-events:none}
.msearch #q{width:100%;height:36px;box-sizing:border-box;padding:0 10px 0 32px;background:var(--panel);border:1px solid var(--line);color:var(--fg);
  border-radius:6px;font:500 .88rem var(--f-body);transition:width .2s,border-color .12s}
.msearch #q:focus{outline:0;border-color:var(--gold)}
.wrap>.top,.wrap>.ctrl{display:none}
@media (min-width:641px){.wrap{padding-top:10px}}
@media (max-width:640px){
  .mast-in{flex-wrap:wrap;height:auto;padding-top:8px;padding-bottom:0;gap:0 10px}
  .mbrand b{font-size:1.4rem}
  .mbrand .mlogo{width:19px;height:19px}
  .mbrand{min-height:34px}  /* 和 .micon 同高：沒有右側按鈕的戰力排行頁，分頁列才不會比首頁高 */
  .macts{margin-left:auto;gap:6px}
  .mtabs{order:10;flex-basis:100%;margin:4px 0 0}
  .mtab,.mtabs .tpick summary{height:40px;padding:0 11px;font-size:15px}
  .mbrand{width:auto}
  .mtabs #teamPick:not(.on) summary::before,.mtabs #teamPick.last:not(.on) summary{font-size:15px}
  .mpanel{position:fixed;left:12px;right:12px;top:calc(var(--mh,96px) + 6px);min-width:0}
  /* 舊手機規則 #posSeg{display:none}（位置要點 .pbtn 才展開）在位置列搬進篩選面板後仍生效 → 面板開了卻空的（使用者 2026-11-02） */
  #mPos #posSeg{display:flex;position:static;box-shadow:none}
  #mPos #posSeg button{height:36px;padding:0 13px}
  .mast .pn{top:calc(var(--mh,96px) + 6px);right:12px;width:calc(100vw - 24px)}
  .msearch .sbox{position:fixed;width:auto;left:12px;right:12px;top:calc(var(--mh,96px) + 6px);z-index:20;padding:10px;background:var(--panel-2);border:1px solid var(--line);border-radius:8px;box-shadow:0 14px 36px rgba(0,0,0,.6)}
  .msearch #q,.msearch #q:focus{height:40px;font-size:16px}
  .mtabs .tpick .tpop{position:fixed;left:12px!important;right:12px;top:calc(var(--mh,96px) + 6px);width:auto}
}
@media (prefers-reduced-motion:reduce){.mast.ready .mind,.msearch #q{transition:none}}
</style>"""

# 頁尾腳本：搬元素、分頁底線、篩選小點、手機搜尋、捲動陰影
JS = """<script>(()=>{
const $=s=>document.querySelector(s),mast=$('.mast');if(!mast)return;
const tabs=$('.mtabs'),ind=$('.mind'),tp=$('#teamPick'),pos=$('#posSeg'),fb=$('#mFilter>summary');
if(tp){$('#mPickPh').replaceWith(tp);if(location.hash==='#team'){history.replaceState(null,'',location.pathname+location.search);setTimeout(()=>tp.open=true);}}
if(pos)$('#mPos').append(pos);
const season=$('.snav .seg');if(season)$('#mSeason').append(season);
const mode=$('#modeSeg');if(mode)$('#mMode').append(mode);
const pn=$('.snav .pnote');if(pn)$('#mNotes').append(pn);else $('#mNotes').closest('.mrow').remove();
const q=$('#q');if(q){$('.msearch .sbox').append(q);q.placeholder='搜尋球員或球隊';}
const pl=$('#mPlayers'),tr=$('#mTeams'),gm=$('#mGames'),PR=window.PureRank,PG=window.PureGames,T0=document.title,sy={},reduce=matchMedia('(prefers-reduced-motion:reduce)').matches;
const TITLE={rank:'戰力排行 · TrueOVR',games:'賽程 · TrueOVR'};
const parseHash=()=>{
  let m=/^\\/rank(?:\\/([A-Za-z]{2,4}))?\\/?$/.exec(location.pathname);if(m)return{v:'rank',arg:m[1]?m[1].toUpperCase():null};
  m=/^\\/games(?:\\/(\\d{4}-\\d{2}-\\d{2})(?:\\/(\\d{10}))?)?\\/?$/.exec(location.pathname);if(m)return{v:'games',arg:m[1]||null,gid:m[2]||null};
  return{v:'players'};
};
const avail=v=>v==='rank'?PR:v==='games'?PG:true;
let view=(v=>avail(v)?v:'players')(parseHash().v);
const sync=()=>{
  const on=tp&&tp.classList.contains('on');pl.setAttribute('aria-selected',String(!on&&view==='players'));tr.setAttribute('aria-selected',String(view==='rank'));gm.setAttribute('aria-selected',String(view==='games'));
  const t=view==='rank'?tr:view==='games'?gm:on?tp.querySelector('summary'):pl,a=tabs.getBoundingClientRect(),r=t.getBoundingClientRect();
  ind.style.setProperty('--ix',(r.left-a.left)+'px');ind.style.setProperty('--iw',r.width+'px');mast.style.setProperty('--mh',mast.offsetHeight+'px');
  const b=pos&&pos.querySelector('[aria-pressed="true"]');fb.classList.toggle('dot',!!b&&b!==pos.firstElementChild);
};
pl.onclick=()=>{const b=$('#teamGrid [data-t="ALL"]');if(b&&tp&&tp.classList.contains('on'))b.click();if(PR||PG)go('players',true);};
/* h：要帶進檢視的網址參數（rank：{arg}；games：{arg:日期,gid}）；undefined＝維持檢視目前的狀態 */
function show(v,h){
  if(v==='rank'){if(h)PR.open(h.arg);PR.ensure();}
  if(v==='games'){if(h)PG.open(h.arg,h.gid);PG.ensure();}
  if(v===view)return;
  sy[view]=scrollY;view=v;document.body.dataset.view=v;document.title=TITLE[v]||T0;sync();scrollTo(0,sy[v]||0);
}
function go(v,push,h){
  if(push&&v!==view)history.pushState(null,'',v==='rank'?'/rank/':v==='games'?PG.hash():'/');
  if(v===view||!document.startViewTransition||reduce)return show(v,h);
  mast.classList.add('vt-running');
  const t=document.startViewTransition(()=>show(v,h));
  t.ready.catch(()=>{});t.finished.catch(()=>{}).finally(()=>mast.classList.remove('vt-running'));
}
if(PR||PG){
  const tabClick=(el,v,h)=>el.addEventListener('click',e=>{if(e.metaKey||e.ctrlKey||e.shiftKey||e.altKey||e.button)return;e.preventDefault();go(v,true,h);});
  if(PR)tabClick(tr,'rank',{arg:null});
  if(PG)tabClick(gm,'games');
  /* 排行／賽程檢視下點「球隊」：先黃色高亮並展開選隊，選完才跳到球隊名單（使用者 2026-11-03） */
  const tg=$('#teamGrid');
  if(tg)tg.addEventListener('click',e=>{if(view!=='players'&&e.target.closest('button[data-t]')){sy.players=0;go('players',true);}});
  addEventListener('popstate',()=>{const h=parseHash(),v=avail(h.v)?h.v:'players';go(v,false,h);});
  document.body.dataset.view=view;if(TITLE[view])document.title=TITLE[view];
  const h0=parseHash();
  if(h0.v==='rank'&&PR){PR.open(h0.arg);PR.ensure();}
  else if(h0.v==='games'&&PG){PG.open(h0.arg,h0.gid);PG.ensure();}
  else(window.requestIdleCallback||setTimeout)(()=>{PR&&PR.ensure();PG&&PG.ensure();});
}
/* 點「球隊」：正在看某隊／新秀 → 展開選隊；在其他檢視（球員、排行、賽程）→ 回到上次選的球隊，沒選過才展開（使用者 2026-11-03、11-04） */
const ts=tp&&tp.querySelector('summary');
if(ts)ts.addEventListener('click',e=>{
  const on=tp.classList.contains('on');
  if(view==='players'&&on)return;
  if(on){e.preventDefault();tp.open=false;go('players',true);return;}
  const b=tp.dataset.last&&$(`#teamGrid [data-t="${tp.dataset.last}"]`);
  if(b){e.preventDefault();tp.open=false;b.click();}
});
const mo=new MutationObserver(sync);
if(tp)mo.observe(tp,{attributes:true,attributeFilter:['class'],childList:true,subtree:true});
if(pos)mo.observe(pos,{childList:true,subtree:true,attributes:true});
addEventListener('resize',sync);sync();requestAnimationFrame(()=>mast.classList.add('ready'));
if(document.fonts)document.fonts.ready.then(sync);
const pops=[...document.querySelectorAll('.mpop')];
pops.forEach(d=>d.addEventListener('toggle',()=>{if(d.open)pops.forEach(o=>o!==d&&(o.open=false));}));
pos&&pos.addEventListener('click',e=>{if(e.target.closest('button'))$('#mFilter').open=false;});
const ms=$('.msearch'),qd=()=>$('.msearch .sbtn').classList.toggle('dot',!!(q&&q.value.trim()));
q&&q.addEventListener('input',qd);
$('.msearch .sbtn').onclick=e=>{e.stopPropagation();const o=ms.classList.toggle('open');if(o)q&&q.focus();};
document.addEventListener('click',e=>{
  pops.forEach(d=>{if(d.open&&!d.contains(e.target))d.open=false;});
  if(!ms.contains(e.target))ms.classList.remove('open');
});
document.addEventListener('keydown',e=>{if(e.key!=='Escape')return;pops.forEach(d=>d.open=false);ms.classList.remove('open');});
const sc=()=>mast.classList.toggle('scrolled',scrollY>4);addEventListener('scroll',sc,{passive:true});sc();
})()</script>"""


def header_html(current):
    return (
        '<header class="mast"><div class="mast-in">'
        f'<a class="mbrand" href="/" aria-label="TrueOVR 首頁"><svg class="mlogo" viewBox="8 8 48 48" aria-hidden="true">{RING}</svg><b>TrueOVR</b><small>{SEASON[current]}</small></a>'
        '<nav class="mtabs" aria-label="主要分頁">'
        '<button type="button" class="mtab" id="mPlayers" aria-selected="true">球員</button>'
        '<span class="mtab mtab-pick" id="mPickPh">球隊</span>'
        '<span class="mind" aria-hidden="true"></span>'
        '<a class="mtab" id="mTeams" href="/rank/">戰力排行</a>'
        '<a class="mtab" id="mGames" href="/games/">賽程</a></nav>'
        '<div class="macts">'
        f'<details class="mpop" id="mFilter"><summary class="micon" aria-label="篩選">{_svg("filter", 15)}</summary>'
        '<div class="mpanel"><div class="mrow"><b>賽季</b><div id="mSeason"></div></div>'
        '<div class="mrow" id="mPosRow"><b>位置</b><div id="mPos"></div></div></div></details>'
        f'<details class="mpop" id="mSettings"><summary class="micon" aria-label="設定">{_svg("gear")}</summary>'
        '<div class="mpanel"><div class="mrow"><b>能力值顯示</b><div id="mMode"></div></div>'
        '<div class="mrow"><b>版本</b><div id="mNotes"></div></div></div></details>'
        f'<div class="msearch"><button type="button" class="micon sbtn" aria-label="搜尋">{_svg("search")}</button>'
        f'<div class="sbox">{_svg("search", 15)}</div></div>'
        '</div></div></header>'
    )


def add_masthead(html_str, current):
    assert current in SEASON, current
    # season_nav 的 #modeSeg 手機／桌機搬家腳本會把它搬回控制列，眉頭接手後拿掉
    s, n = re.subn(r"<script>addEventListener\('DOMContentLoaded',\(\)=>\{const m=document\.getElementById\('modeSeg'\).*?</script>",
                   '', html_str, count=1, flags=re.S)
    assert n == 1, 'modeSeg mover not found'
    # 能力值預設顯示 99 數字（使用者 2026-11-02「預設使用 99，而不是 A+」）；按過 A+ 的人仍記住 A+
    a = "localStorage.getItem('bbac.mode') === 'num' ? 'num' : 'grade'; } catch (e) { return 'grade'; }"
    assert s.count(a) == 1, 'mode default not found'
    s = s.replace(a, "localStorage.getItem('bbac.mode') === 'grade' ? 'grade' : 'num'; } catch (e) { return 'num'; }")
    assert s.count('<div class="wrap">') == 1, 'wrap not found'
    rank_html, rank_js = '', ''
    if current == 'inseason':  # 戰力排行、賽程檢視只有 2026-27 名單頁有；#rank／#games 直連時在首次繪製前先切好，不閃一下球員檢視
        import rank_view
        import games_view
        rank_html, rank_js = rank_view.embed()
        games_html, games_js = games_view.embed()
        # 路徑是 /rank/、/games/（部署時各複製一份 index.html，arammeta 做法）；404.html 把更深的路徑（/rank/LAL/、/games/日期/場次/）存進 sessionStorage 再轉回這裡還原；
        # 舊的 #rank／#games 連結直接改寫成路徑，不重新載入
        rank_html += games_html + (
            "<script>{try{const s=sessionStorage.getItem('bbac.spa');if(s){sessionStorage.removeItem('bbac.spa');"
            "if(s.indexOf(location.pathname)===0)history.replaceState(null,'',s+location.search+location.hash)}}catch(e){}"
            "const h=/^#(rank|games)(\\/.*)?$/.exec(location.hash);"
            "if(h&&!/^\\/(rank|games)\\//.test(location.pathname))history.replaceState(null,'','/'+h[1]+'/'+(h[2]?h[2].slice(1)+'/':''));"
            "const m=/^\\/(rank|games)\\//.exec(location.pathname);if(m)document.body.dataset.view=m[1]}</script>")
        rank_js += games_js
    # 刷新時眉頭不跳（使用者 2026-11-03）：--tw 要等表格畫好、字型載完才量得準，首格先套上次存下的值（enrich_roster_viewer 寫入）
    tw0 = "<script>try{const w=localStorage.getItem('bbac.tw:'+(/^\\/(rank|games)\\//.test(location.pathname)?'/':location.pathname));if(w)document.documentElement.style.setProperty('--tw',w)}catch(e){}</script>"
    s = s.replace('<div class="wrap">', CSS + tw0 + header_html(current) + '\n' + rank_html + '<div class="wrap">', 1)
    i = s.rfind('</body>')
    tail = rank_js + JS
    return s[:i] + tail + s[i:] if i >= 0 else s + tail
