"""名單頁加料：卡片顯示 2025-26 例行賽真實場均、球隊配色、隊徽＋球員頭像；表格球隊欄加色標。

資料：data/season-source/player-games.json（stats.nba.com leaguegamelog，每人每場一列）。
依 PLAYER_NAME 跨隊合計；交易球員列出所有球隊。重跑會先移除舊的注入再寫入。
頭像直接連 NBA CDN（1040x760 約 200 KB，只載入被點選的那位；260x190 在高 DPI 螢幕會糊，使用者 2026-11-01），沒網路或沒照片就不顯示。

用法：python -I scripts/enrich_roster_viewer.py reports/ovr-v58-card-2025-26/roster-viewer.html [...]
"""
import csv
import html
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rating_m2  # noqa: E402
import rating_m10  # noqa: E402
import headshot_eyeline  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'data' / 'season-source' / 'player-games.json'
RAPM = ROOT / 'reports' / 'impact-rapm' / 'rapm-prior.csv'  # 2025-26 單季 box-prior RAPM（每 100 回合）
ONOFF = ROOT / 'reports' / 'impact-rapm' / 'onoff.csv'
IMPACT_LOADER = None  # 賽中頁（build_inseason_viewer.py）換成自己的載入函式；None＝沿用下面的 2025-26 資料
GC = ROOT / 'reports' / 'game-contribution' / 'm2'  # 評分 M2（R-066）：box＋hustle＋防守對位 → RAPM 權重、2025-26 基準、五色切點（scripts/fit_rating_m2.py）
CARD_SUMMARY = ROOT / 'reports' / 'card-0.2.7c' / 'summary.json'  # 正式卡 OVR 錨點（換算 OVR 傾向）
# 新秀篩選（使用者 2026-10-30）：該季選秀年＝新秀；2027 頁的 2026 新秀沒有先驗卡、不在名單上，按鈕自動隱藏
BIO = {'g5': (ROOT / 'data/defense-seventh/2026-27/bio.json', '2026'), 'season': (ROOT / 'data/benchmark-source/bio.json', '2025')}
# 身高旁加年齡、薪水（使用者 2026-11-01）：年齡＝上面 bio.json 的 AGE；薪水＝basketball-reference 合約頁該季 y1
# （reports/salary-corr/source，2026-10-30 抓、不進 git）；缺檔或對不到名字就不顯示
SALARY = {'g5': ROOT / 'reports/salary-corr/source/bref.html', 'season': ROOT / 'reports/salary-corr/source/bref2526.html'}

CSS = """
/* 表格 OVR 分級：金屬稀有度字色＋漸層細框（110+ 紫／100+ 紅／90+ 金／80+ 銀／70+ 銅；70 以下灰字無框；使用者 2026-11-01）。
   最高級原本是珍珠白，和銀太像，使用者看過對照後改成 100+ 紅、110+ 紫（知道紅會和屬性等第 F 紅同色）。
   漸層字要 -webkit-text-fill-color，不然被 td.ovr .ob 的 color 蓋掉變白字。框用 mask 挖空中間，選取列、排序欄的底色照常透出來 */
td.ovr .ob{position:relative;display:inline-block;min-width:2.4em;padding:1px 5px;border-radius:5px;text-align:center;color:var(--oc)}
td.ovr .ob::before{content:"";position:absolute;inset:0;border-radius:inherit;padding:1.5px;background:var(--of);pointer-events:none;
  -webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);-webkit-mask-composite:xor;mask-composite:exclude}
.ob.t6{--oc:#d2a8ff;--of:linear-gradient(135deg,#f0e0ff 0%,#b47aff 35%,#5a1fb8 70%,#e0c4ff 100%);box-shadow:0 0 10px rgba(170,100,255,.6);
  background:linear-gradient(135deg,#f3e6ff,#c896ff 45%,#a466ff);-webkit-background-clip:text;background-clip:text;color:transparent;-webkit-text-fill-color:transparent}
.ob.t5{--oc:#ff7a7a;--of:linear-gradient(135deg,#ffd0d0 0%,#ff4040 38%,#8a0f1f 70%,#ff9a9a 100%);box-shadow:0 0 6px rgba(255,60,60,.4)}
.ob.t4{--oc:#f2c94c;--of:linear-gradient(135deg,#fff0b0 0%,#e8b923 38%,#8a6400 70%,#f5d469 100%)}
.ob.t3{--oc:#d4dae3;--of:linear-gradient(135deg,#ffffff 0%,#b8c0cc 38%,#6b7380 70%,#dfe4ea 100%)}
.ob.t2{--oc:#c98a5a;--of:linear-gradient(135deg,#f0c49c 0%,#b8743f 38%,#6b3a17 70%,#d9a070 100%)}
.ob.t1{--oc:#8f96a3}
.ob.t1::before{display:none}
/* real box score */
.real{display:grid;grid-template-columns:repeat(auto-fill,minmax(64px,1fr));gap:4px;margin-top:2px}
.real .st{background:var(--panel-2);border:1px solid var(--line);border-radius:3px;padding:3px 6px;text-align:center}
.real .st b{display:block;font:700 1.15rem var(--f-disp);font-variant-numeric:tabular-nums;color:var(--fg)}
.real .st span{display:block;font-size:.68rem;color:var(--muted)}
.real-h{color:var(--muted);font-size:.72rem;letter-spacing:.08em}
.real.rx{display:flex;flex-wrap:wrap;align-items:center;gap:8px 18px}
.rx .rmain{display:flex;gap:4px}
.rx .rmain .st{min-width:68px;padding:4px 12px}
.rx .rmain .st b{font-size:1.7rem;line-height:1.1}
.rx .rsub{display:grid;gap:4px;font-size:.74rem;color:var(--muted)}
.rx .rsub>div{display:flex;flex-wrap:wrap;gap:2px 14px}
.rx .rsub b{margin-left:5px;font:600 .92rem var(--f-disp);font-variant-numeric:tabular-nums;color:var(--fg)}
/* 球員卡資訊列：手機藏標籤、較開季差值三色（season_nav._compact_facts） */
.facts i{font-style:normal}
.facts .sm{display:none}
.facts b.up{color:var(--g-a)}
.facts b.dn{color:var(--g-f)}
.facts b.flat{color:var(--muted)}
@media (max-width:640px){
  .facts{gap:2px 12px}
  .facts .lb{display:none}
  .facts .sm{display:inline}
}
/* 能力值欄一樣寬（使用者 2026-10-29）：原本被中文副標長短撐開 35–67px；副標縮小讓四字（製造犯規）也放得下一行 */
#tbl thead tr:last-child th[data-k]:not([data-k=name],[data-k=pos],[data-k=team],[data-k=ht],[data-k=ovr],[data-k=min],[data-k=gp],[data-k=dovr]){
  width:38px;min-width:38px;box-sizing:border-box;padding-left:1px;padding-right:1px}   /* 44→38（2026-11-03 桌機要 100% 就放得下）；48→44（使用者 2026-11-02：能力值欄太寬）；四字副標 .62rem 約 40px */
/* 分鐘／場數／較開季也固定寬（使用者 2026-10-30：表格 min-width 1060 多出來的寬度原本都分給這幾欄） */
#tbl thead tr:last-child th:is([data-k=min],[data-k=gp]){width:46px;box-sizing:border-box}
#tbl thead tr:last-child th[data-k=dovr]{width:54px;box-sizing:border-box}
/* 手機表格本來就左右捲，不用撐到 1060px，每欄照內容寬 */
@media (max-width:640px){#tbl{min-width:0;width:max-content}}
#tbl thead tr:last-child th[data-k]:not([data-k=name],[data-k=pos],[data-k=team],[data-k=ht],[data-k=ovr],[data-k=min],[data-k=gp],[data-k=dovr]) .zh{font-size:.58rem}
/* 名字欄不再整條金底（使用者 2026-10-29：醜、被列線切得斷裂）；改深色底，只有選中列金色 */
#tbl th.nm{background:#0a0d10;color:var(--muted)}
/* 球員、總評兩欄底色改成和表頭一樣黑（使用者 2026-11-02：像 x 軸標題） */
#tbl td.nm{background:#0a0d10;color:var(--fg);box-shadow:inset -1px 0 0 var(--line)}
/* 總評格本身不塗黑（桌機；使用者 2026-11-02：黑底蓋住金框）；手機總評格要釘住，底色在下面手機區塊 */
/* 左邊釘住的 # 球員 總評全黑，右邊能力值格子拉淺，一黑一淺才看得出哪邊能滑（使用者 2026-11-02） */
#tbl tbody td.no{background:#0a0d10}
/* 選中列總評格跟名字一起變金，但紅／金框裡面維持黑（使用者 2026-11-02） */
#tbl tbody tr.sel td.ovr,#tbl tbody tr.sel:hover td.ovr{background:var(--gold)}
#tbl tbody tr.sel td.ovr .ob{background:#0a0d10}
div.tbox{background:#1b232d}
#tbl tbody tr:hover td.nm{background:var(--panel-2)}
#tbl tbody tr.sel td.nm{background:var(--gold);color:var(--gold-ink)}
/* 桌機名字欄固定寬（使用者 2026-11-01：表格只畫目前這頁的人，換排序時名字欄跟著當頁最長名字變寬變窄）；
   160px（使用者 2026-11-02 收窄到剛好放下 Shai Gilgeous-Alexander，原 200px）：Giannis Antetokounmpo 約 138px 也放得下，最長的 Yanic Konan Niederhäuser 約 162px 會截成 … */
@media (min-width:641px){
  #tbl th.nm,#tbl td.nm{width:140px;min-width:140px;max-width:140px;box-sizing:border-box}
  /* 名字欄收緊後整張表也往中間縮（使用者 2026-11-02）：不再撐滿 1280／最小 1060，改成內容寬並置中 */
  .tbox{width:fit-content;max-width:100%;margin-inline:auto;overflow-x:hidden!important}
  #tbl{width:auto;min-width:0}
  #tbl td.nm{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  /* 桌機總評左邊的位置／球隊／身高也跟 # 球員一樣黑（使用者 2026-11-02） */
  #tbl tbody td:is(:nth-child(3),:nth-child(4),:nth-child(5)):not([colspan]){background:#0a0d10}
  #tbl tbody tr:hover td:is(:nth-child(3),:nth-child(4),:nth-child(5)):not([colspan]){background:var(--panel-2)}
  #tbl tbody tr.sel td:is(:nth-child(3),:nth-child(4),:nth-child(5)):not([colspan]){background:var(--gold);color:var(--gold-ink)}
}
/* 手機表格（使用者 2026-10-29）：拿掉 OVR 左邊的位置／球隊／身高；表格手勢由 JS 鎖方向（偏垂直就整段只上下捲，手抖不左右晃）；表頭與名字／OVR 欄的手勢捲整頁（2026-10-30） */
@media (max-width:640px){
  #tbl thead tr:last-child th:is([data-k=pos],[data-k=team],[data-k=ht]),#tbl tbody td:is(:nth-child(3),:nth-child(4),:nth-child(5)):not([colspan]),#tbl th.gx{display:none}
  .tbox{touch-action:none}
  /* 左右捲時群組標題（投籃…）的左框不滑到 OVR 上方：最左那格群組標題釘住，# 欄 28px 捲走後右緣剛好停在 OVR 右側 */
  #tbl th.noh,#tbl td.no{width:28px;min-width:28px;max-width:28px;box-sizing:border-box}
  #tbl tr.grp th:first-child{position:sticky;left:-28px;z-index:3;box-shadow:6px 0 6px -5px rgba(0,0,0,.7)}
}
/* 手機名字欄縮寫（使用者 2026-10-29：全名佔四成寬）：Stephen Curry → S. Curry，太長的截成 … */
#tbl td.nm .ns{display:none}
@media (max-width:640px){#tbl td.nm .nf{display:none}#tbl td.nm .ns{display:inline}}
/* E-116：2027 頁的 2026 新秀沒有先驗卡，起點由順位估 */
/* 使用者 2026-11-01：不寫「新秀先驗」字樣、不用 emoji；名字用淺藍漸層＋一道斜向冰面反光（使用者 2026-11-01 從六種紋路選 E）＋自製嫩芽圖示（mask，同一道漸層） */
#tbl td.nm.rk .nf,#tbl td.nm.rk .ns{background:linear-gradient(105deg,transparent 0 38%,rgba(255,255,255,.55) 46%,transparent 54%),linear-gradient(176deg,#e6f3fc 0%,#a8d0ec 45%,#6a9fc6 100%);-webkit-background-clip:text;background-clip:text;color:transparent;-webkit-text-fill-color:transparent}
#tbl td.nm .rkp{display:inline-block;width:13px;height:13px;margin-left:5px;vertical-align:-2px;cursor:help;background:linear-gradient(160deg,#e6f3fc 0%,#a8d0ec 45%,#6a9fc6 100%);-webkit-mask:var(--sprout) center/contain no-repeat;mask:var(--sprout) center/contain no-repeat;--sprout:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Cpath d='M7.1 8h1.8v7.2H7.1z'/%3E%3Cpath d='M7.9 10.2C7.9 5.8 5.2 3.2.6 3.2c0 4.4 2.8 7 7.3 7z'/%3E%3Cpath d='M8.1 8.6C8.1 3.6 11 .8 15.4.8c0 4.9-2.9 7.8-7.3 7.8z'/%3E%3C/svg%3E")}
#tbl tbody tr.sel td.nm.rk .nf,#tbl tbody tr.sel td.nm.rk .ns{background:none;color:inherit;-webkit-text-fill-color:currentColor}
#tbl tbody tr.sel td.nm .rkp{background:currentColor}
/* 手機表格（使用者 2026-10-29：很難用）：名字欄變窄可換行、列變矮；OVR 往右滑時釘在名字旁邊，長按不選字 */
@media (max-width:640px){
  #tbl td{padding:5px 3px;font-size:.92rem}
  #tbl th.nm,#tbl td.nm{width:76px;min-width:76px;max-width:76px;box-sizing:border-box;padding-left:6px}
  #tbl td.nm{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;line-height:1.1;font-size:.86rem}
  #tbl td.no{width:28px;font-size:.78rem}
  #tbl th[data-k="ovr"],#tbl td.ovr{position:sticky;left:76px;z-index:1;box-shadow:6px 0 6px -5px rgba(0,0,0,.7)}
  #tbl th[data-k="ovr"]{z-index:2}
  #tbl tbody td.ovr{background:#0a0d10;font-size:1rem}
  #tbl tbody td.ovr.sortcol{background:#0a0d10}
  #tbl tbody tr:hover td.ovr{background:var(--panel-2)}
  #tbl tbody{-webkit-user-select:none;user-select:none;-webkit-touch-callout:none}
}
/* team colors + headshot */
.card .tag{background:var(--card,var(--red));box-shadow:inset 0 -7px 0 var(--tc,transparent);position:relative;min-width:230px}
.card .tag::before{content:"";position:absolute;inset:0;pointer-events:none;background:linear-gradient(115deg,rgba(255,255,255,.34) 0%,rgba(255,255,255,.1) 38%,transparent 39%),radial-gradient(90% 50% at 20% 0%,rgba(255,255,255,.28),transparent 70%);box-shadow:inset 0 0 0 1.5px rgba(255,255,255,.4),inset 0 3px 6px rgba(255,255,255,.35),inset 0 -14px 24px rgba(0,0,0,.28)}  /* 玻璃質感：斜向反光＋亮色內緣＋底部壓暗，白/黑/任何隊色都靠透明度疊加 */
.tag .pos{background:var(--tc,#fff);color:#fff;position:relative;z-index:1}
.tag .rk{position:relative;z-index:1;color:var(--ink,#fff);text-shadow:0 0 8px var(--card,#000)}
.tag .logo{position:absolute;right:30px;top:50%;transform:translateY(-50%);height:150px;width:150px;object-fit:contain;opacity:.9;pointer-events:none}
.tag .shot{position:absolute;right:26px;bottom:7px;height:132px;width:auto;pointer-events:none}
/* 桌機（使用者 2026-11-01：頭像太小、隊徽位置不平衡）：頭像撐滿橫幅高度、置中（扣掉右側斜切）；
   隊徽縮成右上角小徽章，和左上位置、左下排名對角平衡 */
@media (min-width:641px){
  .tag .logo{top:12px;right:16px;transform:none;height:56px;width:56px;z-index:1}
  .tag .shot{left:0;right:auto;width:93%;height:calc(100% - 26px);object-fit:cover;object-position:50% 100%}
  .tag .rk{text-shadow:0 0 3px var(--card,#000),0 0 10px var(--card,#000),0 0 18px var(--card,#000)}  /* 排名壓在球衣上，白衣也要看得清楚 */
}
/* 手機卡片（使用者 2026-10-29：沒有頭像和隊徽；名字和頭像放一起；字太多，用減法）
   隊色橫幅左上放位置＋身高，右上角放排名（和位置同款隊色小標），名字（.tnm/.tht 只在手機顯示）和頭像；下面 OVR 圓環下方掛較開季箭頭，右邊影響力 2×2；
   資訊列其餘（球隊、分鐘、場數、防守加分）不顯示；真實數據只留得分／籃板／助攻三大格 */
.tag .tnm,.tag .tht{display:none}
.tag .tht i{font-style:normal;margin-left:7px;font-size:.85em;opacity:.85}
@media (max-width:640px){
  .card{grid-template-columns:auto 1fr;gap:8px 12px}
  .card .tag{display:flex;flex-direction:row;align-items:center;justify-content:flex-start;gap:8px;grid-column:1/-1;grid-row:1;margin:-12px -14px 0;min-width:0;height:100px;clip-path:none;padding:8px 14px}
  .tag .pos{align-self:flex-start;line-height:19px}
  .tag .tht{display:block;order:1;align-self:flex-start;font:700 1.05rem/21px var(--f-disp);color:var(--ink,#fff);position:relative;z-index:1}
  .tag .rk{position:absolute;top:10px;right:14px;z-index:3;font:700 1rem/19px var(--f-disp);text-shadow:none;background:var(--tc,#fff);color:#fff;padding:1px 8px;border-radius:3px}
  .tag .rk small{font-size:1em;opacity:1;margin:0}
  .tag .logo{right:14px;height:88px;width:88px;opacity:.9}
  .tag .shot{right:6px;height:94px}
  .tag .tnm{display:block;position:absolute;left:14px;right:136px;bottom:10px;z-index:1;font:800 1.35rem/.95 var(--f-disp);text-transform:uppercase;color:var(--ink,#fff);text-shadow:0 0 8px var(--card,#000);overflow-wrap:anywhere}
  .tag .tnm span{display:block;font-size:.8rem;font-weight:600;opacity:.85;margin-bottom:2px}
  .card .who>.nm{display:none}
  .card .ring{grid-column:1;grid-row:2;align-self:center}
  .card .ring svg{width:66px;height:66px}
  .card .who>.facts{grid-column:1;grid-row:3;align-self:start;justify-content:center;display:flex;margin-top:-4px}
  .facts>span:not(.f-d){display:none}
  .facts .f-d b{font:700 1.15rem var(--f-disp)}
  /* 卡片壓矮（使用者 2026-11-01：資訊不多可以更 compact）：影響力 2×2 一格一行（標籤左、數字右），
     得分／籃板／助攻／正負值移到影響力下面、和圓環同一側；框拿掉邊線改淡底 */
  .card .who>.strong{grid-column:2;grid-row:2;align-self:center;display:grid;grid-template-columns:repeat(2,1fr);gap:4px}
  .strong .chip{display:flex;flex-direction:row;justify-content:space-between;align-items:baseline;gap:4px;padding:5px 8px;border:0;border-radius:5px;background:rgba(255,255,255,.05);font-size:.7rem;color:var(--muted);letter-spacing:0;white-space:nowrap}
  .strong .chip i{margin:0;font:700 1rem var(--f-disp)}
  .strong .chip.dim{grid-column:1/-1}
  .card .who>.real{grid-column:2;grid-row:3/5;align-self:start;margin:0}
  .rx .rmain{flex:1;gap:4px}
  .rx .rmain .st{flex:1}
  /* 場數／分鐘併到 OVR 圓環下方，三大項縮小並補正負值（使用者 2026-10-29：省空間）；交易隊名手機不顯示 */
  .card .who>.real-h{grid-column:1;grid-row:4;justify-self:center;margin-top:-4px;white-space:nowrap;font-size:.7rem;letter-spacing:.02em}
  .real-h .rtm{display:none}
  .rx .rmain .st{min-width:0;padding:3px 2px;border:0;border-radius:5px;background:rgba(255,255,255,.05)}
  .rx .rmain .st b{font-size:1.05rem;line-height:1.15}
  .rx .rmain .st span{font-size:.62rem}
  .rx .rsub{display:none}
}
/* 桌機卡片：影響力四格改 2×2，和 OVR 圓環放同一側（使用者 2026-10-29：省空間）
   .who 拆開讓子元素直接排進 .card 格線：寬螢幕 2×2 在圓環左邊；窄一點（<1100px）疊在圓環下面，讓中間欄夠寬
   比照手機（使用者 2026-10-30）：資訊列拿掉，得分／籃板／助攻／正負值改大格、細項小字在旁；場數·分鐘掛在 OVR 圓環下 */
@media (min-width:641px){
  .card{grid-template-columns:auto minmax(0,1fr) auto auto;row-gap:10px}
  .card .tag{grid-column:1;grid-row:1/span 3}
  .card .who{display:contents}
  .card .who>*{grid-column:2;margin-inline:18px}
  .card .who>.nm{grid-row:1;margin-top:14px;align-self:end}
  .card .who>.facts{display:none}
  .card .who>.real{grid-row:2/span 2;align-self:start;margin-bottom:14px}
  .card .who>.strong{grid-column:3;grid-row:1/span 3;align-self:center;margin:14px 0;display:grid;grid-template-columns:repeat(2,1fr);gap:6px}
  .strong .chip{display:flex;flex-direction:column;align-items:center;min-width:84px;padding:6px 8px;font-size:.74rem;color:var(--muted);letter-spacing:0}
  .strong .chip i{margin:2px 0 0;font:700 1.3rem var(--f-disp)}
  .strong .chip.dim{grid-column:1/-1}
  .card .ring{grid-column:4;grid-row:1/span 2;align-self:end;padding:14px 22px 0}
  .card .who>.real-h{grid-column:4;grid-row:3;align-self:start;justify-self:center;margin:-4px 18px 14px;white-space:nowrap;letter-spacing:.02em}
  .real-h .rtm{display:none}
  /* 身高在名字旁；較開季掛圓環下 */
  .who .nm .nht{margin-left:10px;vertical-align:middle;font-size:1rem;font-weight:600;color:var(--muted);text-transform:none;white-space:nowrap}
  .who .nm .nht i{font-style:normal;margin-left:10px}
  .who .nm .nbio{display:inline-block;vertical-align:baseline;margin-left:14px;font-size:1rem;font-weight:600;color:var(--muted);text-transform:none;white-space:nowrap}
  .who .nm .nbio i{font-style:normal}
  .who .nm .nbio i+i{margin-left:10px}
  .who .nm .b1,.who .nm.tight .nbio{display:none}
  .who .nm.tight .b1{display:inline}
  .card .ring{flex-direction:column;gap:2px}
  .ring .rd{font:700 1.25rem var(--f-disp);font-variant-numeric:tabular-nums}
  .ring .rd.up{color:var(--g-a)}
  .ring .rd.dn{color:var(--g-f)}
  .ring .rd.flat{color:var(--muted)}
  .rx .rmain .st{min-width:74px}
  /* 細項一律排在大格下面（使用者 2026-10-30：寬螢幕上細項短的人（三分「—」）塞得進大格右邊、卡片變矮，
     換人時卡片高度跳、貼底的頭像眼線也跟著偏） */
  .rx .rsub{flex-basis:100%}
  .card .who>.g5{grid-column:1/-1;grid-row:4;margin:0 18px 14px}
}
.who .nm .nht,.who .nm .nbio,.ring .rd{display:none}
@media (min-width:641px){.who .nm .nht,.ring .rd{display:inline}.who .nm .nbio{display:inline-block}.who .nm.tight .nbio{display:none}}
@media (min-width:641px) and (max-width:1099px){
  .card{grid-template-columns:auto minmax(0,1fr) auto}
  .card .ring{grid-column:3;grid-row:1;padding:14px 18px 0}
  .card .who>.real-h{grid-column:3;grid-row:2;margin:-4px 18px 0}
  .card .who>.strong{grid-column:3;grid-row:3;align-self:start;margin:0 18px 14px}
  /* 中間欄窄：四大格平分寬度、字縮小，不壓到右邊影響力 */
  .rx .rmain{flex:1 1 100%}
  .rx .rmain .st{flex:1 1 0;min-width:0;padding:4px 6px}
  .rx .rmain .st b{font-size:1.4rem}
}
/* 641–899px 中間欄只剩 125–330px，名字／細項換行數因人而異、卡片高低不一（使用者 2026-10-30）：
   環、場數、影響力移到隊徽下面一列，中間欄拿到整寬 */
@media (min-width:641px) and (max-width:899px){
  .card{grid-template-columns:auto minmax(0,1fr)}
  .card .tag{min-width:0}
  .card .ring{grid-column:1;grid-row:4;justify-self:center;padding:0 18px}
  .card .who>.real-h{grid-column:1;grid-row:5;margin:-4px 18px 14px}
  .card .who>.strong{grid-column:2;grid-row:4/span 2;align-self:center;margin:0 18px 14px}
  .card .who>.g5{grid-row:6}
}
/* 展開至 50 人：表格不限高，跟著頁面捲（fitTable 設的行內 max-height 用 !important 蓋掉） */
/* 展開後在表格上捲＝整頁捲：拿掉 contain／none，捲動要傳給頁面（使用者 2026-11-01） */
.tbox.grow{max-height:none!important;overflow-y:visible;overscroll-behavior:auto}
/* 近 N 場逐場數據（使用者 2026-10-30：數據旁的 ▼ 展開，像 NBA box score） */
.rx .g5t{flex-basis:100%;display:flex;align-items:center;gap:6px;background:none;border:0;border-top:1px solid var(--line);padding:6px 0 0;
  color:var(--muted);font:600 .8rem var(--f-disp);letter-spacing:.04em;cursor:pointer;text-align:left}
.rx .g5t:hover{color:var(--fg)}
.rx .g5t i{display:inline-block;font-style:normal;font-size:.75em;transition:transform .15s}
.rx .g5t[aria-expanded="true"] i{transform:rotate(180deg)}
.card .g5{justify-self:start;min-width:0;max-width:100%;box-sizing:border-box;overflow-x:auto;border:1px solid var(--line);border-radius:3px;background:var(--panel-2);scrollbar-width:thin;scrollbar-color:#38424f transparent}
.g5 table{min-width:0;border-collapse:collapse;font-variant-numeric:tabular-nums;white-space:nowrap}
.g5 th{background:none;cursor:default;color:var(--muted);font:600 .7rem var(--f-disp);letter-spacing:.04em;text-align:right;padding:6px 10px;border-bottom:1px solid var(--line)}
.g5 td{text-align:right;padding:5px 10px;border-bottom:1px solid var(--line);color:var(--fg);font:500 .9rem var(--f-disp);letter-spacing:.02em}
.g5 :is(th,td):is(:nth-child(1),:nth-child(2)){text-align:left}
.g5 td:nth-child(5){font-weight:700}
.g5 td .w{color:var(--g-a);font-weight:700}
.g5 td .l{color:var(--g-f);font-weight:700}
.g5 tfoot td{color:var(--muted);border-bottom:0}
.g5 .up{color:var(--g-a)}
.g5 .dn{color:var(--g-f)}
.g5 .gcn{position:sticky;left:0;max-width:0;min-width:100%;box-sizing:border-box;padding:6px 10px 7px;border-top:1px solid var(--line);color:var(--muted);font-size:.74rem;line-height:1.5;white-space:normal}
.g5 .gcn b{font:600 .86rem var(--f-disp);font-variant-numeric:tabular-nums;color:var(--fg)}
.g5.sd .sdw{display:flex;flex-wrap:wrap;align-items:flex-start}
.g5.sd table{width:auto}
.g5.sd table+table{border-left:1px solid var(--line)}
.g5.sd :is(th,td):nth-child(2){text-align:right}
.g5.sd td:first-child{color:var(--muted)}
@media (max-width:640px){.g5.sd table{width:100%}.g5.sd table+table{border-left:0;border-top:1px solid var(--line)}}
.g5 .c5a,.g5 .gcn b.c5a{color:var(--g-a)}
.g5 .c5b,.g5 .gcn b.c5b{color:var(--g-b)}
.g5 .c5c,.g5 .gcn b.c5c{color:#a3abb5}
.g5 .c5d,.g5 .gcn b.c5d{color:#f09a8c}
.g5 .c5f,.g5 .gcn b.c5f{color:var(--g-f)}
@media (max-width:1099px){.g5 th,.g5 td{padding-inline:7px}}
@media (max-width:640px){
  .g5 td{font-size:.84rem}
  .g5 th,.g5 td{padding:5px 6px}
  /* 手機 ▼ 放正負值格右上角（使用者 2026-10-30）：右上切一個斜角變五角形，▼ 放在切掉的位置，不另佔一列
     ▼ 用正三角形（60°），缺角也切 60°（橫 16px、直 27.7px），▼ 左斜邊和缺角平行、留 3px 不碰框；展開時不翻轉，改變金色。
     格子改成無邊線淡底後（2026-11-01）缺角不用再補斜邊線 */
  .real.rx{position:relative}
  .rx .rmain .st:last-child{position:relative;clip-path:polygon(0 0,calc(100% - 16px) 0,100% 27.7px,100% 100%,0 100%)}
  .rx .g5t{position:absolute;top:-8.6px;right:-11.4px;width:30px;height:30px;padding:0;border:0;font-size:0;justify-content:center}
  .rx .g5t i,.rx .g5t[aria-expanded="true"] i{display:block;width:9px;height:7.8px;background:var(--muted);clip-path:polygon(0 0,100% 0,50% 100%);transform:none;transition:background .15s}
  .rx .g5t[aria-expanded="true"] i{background:var(--gold)}
}
.tabbr{color:var(--tt);font-weight:600}
/* 選中列是金底（使用者 2026-11-03：灰／黃／橘隊的縮寫變隊色後看不見）：縮寫改用兩個主題色中較深的那個 */
#tbl tbody tr.sel .tabbr{color:var(--dk,inherit)}
/* impact chips：RAPM 攻守淨（對聯盟平均）、在場減不在場（每 100 回合） */
.chip i.up{color:var(--g-a)}
.chip i.dn{color:var(--g-f)}
.chip i.flat{color:var(--muted)}
/* 手機篩選列（使用者 2026-10-29：卡片和表格要能同時看到，篩選擋在中間）：整排移到卡片上方，擠成一排、一樣高；
   位置改成點了才展開的下拉（.pbtn），球隊沒選時顯示「球隊」。桌機也把篩選列移到卡片上方（使用者 2026-10-30） */
.pbtn{display:none}
.wrap>.top{order:-2}
.wrap>.ctrl{order:-1}
@media (max-width:640px){
  .wrap>.ctrl{position:relative;flex-wrap:nowrap;gap:6px}
  .ctrl .lbl{display:none}
  .ctrl .tgrp{display:contents}
  .ctrl .pbtn,.ctrl .tpick summary,.ctrl input[type=search]{height:32px;box-sizing:border-box;padding:0 10px}
  .ctrl .pbtn,.ctrl .tpick summary,.ctrl .seg button{font:600 .85rem var(--f-disp);letter-spacing:.04em}
  .ctrl .pbtn{display:flex;align-items:center;gap:6px;flex:none;background:var(--panel);color:var(--muted);border:1px solid var(--line);border-radius:3px;cursor:pointer}
  .ctrl .pbtn::after{content:"▾";font-size:.8em;opacity:.8}
  .ctrl .pbtn.on{background:var(--gold);color:var(--gold-ink);border-color:var(--gold)}
  .ctrl.popen .pbtn:not(.on){color:var(--fg);border-color:var(--muted)}
  #teamPick:not(.on) summary{font-size:0}
  #teamPick:not(.on) summary::before{content:"球隊";font-size:.85rem}
  #teamPick summary::after{font-size:.7rem}
  .ctrl .seg{flex:none}
  .ctrl .seg button{height:30px;padding:0 10px}
  .ctrl input[type=search]{flex:1;min-width:0;width:auto;font-size:.85rem}
  #posSeg{display:none}
  .ctrl.popen #posSeg{display:flex;position:absolute;left:0;top:calc(100% + 6px);z-index:20;box-shadow:0 12px 32px rgba(0,0,0,.55)}
  .ctrl.popen #posSeg button{height:38px;padding:0 13px}
}
/* 玻璃卡片（使用者 2026-11-02：類似 iOS 27 的玻璃特效）：卡底放隊色光暈當背景，數字格／圖表／OVR 圈改成半透明＋模糊＋高光邊 */
.card{position:relative;border-radius:14px;border:1px solid rgba(255,255,255,.14);
  background:
    radial-gradient(75% 230px at 20% 0,color-mix(in srgb,var(--card,#2b3d5c) 70%,transparent),transparent 100%),
    radial-gradient(55% 230px at 100% 0,color-mix(in srgb,var(--tc,var(--card,#3a4a6a)) 50%,transparent),transparent 100%),
    linear-gradient(135deg,#1a2430,#0f1419);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.24),inset 0 -1px 0 rgba(255,255,255,.05),0 12px 32px rgba(0,0,0,.5)}
.card .chip,.card .real .st,.card .g5,.card .g5.hc>.g5in,.card .g5.hc>.ovc{
  background:linear-gradient(150deg,rgba(255,255,255,.15),rgba(255,255,255,.04) 55%,rgba(255,255,255,.08));
  -webkit-backdrop-filter:blur(14px) saturate(1.7);backdrop-filter:blur(14px) saturate(1.7);
  border:1px solid rgba(255,255,255,.17);border-radius:10px;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.3),inset 0 -1px 0 rgba(0,0,0,.25),0 4px 14px rgba(0,0,0,.22)}
.card .g5.hc{background:none;border:0;box-shadow:none;-webkit-backdrop-filter:none;backdrop-filter:none}
/* 走勢圖面板（使用者 2026-11-04：紅色暈染干擾折線）：隊色光暈移到右上，面板改深色底、不做 saturate，折線背景保持中性 */
.card .g5.hc>.ovc{background:linear-gradient(160deg,rgba(12,16,22,.72),rgba(12,16,22,.55));-webkit-backdrop-filter:blur(18px);backdrop-filter:blur(18px)}
.card .ring svg{background:radial-gradient(circle closest-side,rgba(255,255,255,.08) 74%,transparent 74.6%)}
.card .ring svg circle:first-child{fill:none;stroke:rgba(255,255,255,.2)}
.card .ring svg circle:nth-child(2){stroke-opacity:.82;filter:saturate(.8) brightness(1.1) drop-shadow(0 0 6px rgba(0,0,0,.3))}
/* 桌機卡片與頁首寬度跟著表格（使用者 2026-11-02）：--tw 由 JS 量 #tbl 的自然寬度，兩側各留 16px 內距 */
@media (min-width:641px){
  html[style*="--tw"] .wrap,html[style*="--tw"] .mast-in{max-width:min(1360px,calc(var(--tw) + 32px))}
}
"""

# [主色, 副色, 卡片底色, 背號字色]。主色、副色是官方配色（表格色標、卡片底帶）；
# 卡片底色多半避開主色，讓球衣和隊徽看得出來；OKC／BOS／MEM 依使用者指定用隊色的淺色版。
# 表格球隊縮寫的字色預設用卡片底色；卡片是灰／米色的隊另給第 5 欄（亮一點的隊色），不然跟預設灰字分不出來。
TEAM_COLORS = {
    'ATL': ['#E03A3E', '#C1D32F', '#C1D32F', '#111'], 'BOS': ['#007A33', '#BA9653', '#2E9E52', '#fff'],
    'BKN': ['#000000', '#FFFFFF', '#A9AEB4', '#111', '#FFFFFF'], 'CHA': ['#1D1160', '#00788C', '#A1A1A4', '#111', '#1FB5C4'],
    'CHI': ['#CE1141', '#000000', '#E6E6E6', '#111', '#EF3A55'], 'CLE': ['#860038', '#FDBB30', '#FDBB30', '#111'],
    'DAL': ['#00538C', '#B8C4CA', '#B8C4CA', '#111', '#3B95E0'], 'DEN': ['#0E2240', '#FEC524', '#FEC524', '#111'],
    'DET': ['#C8102E', '#1D42BA', '#BEC0C2', '#111', '#EF3A55'], 'GSW': ['#1D428A', '#FFC72C', '#FFC72C', '#111'],
    'HOU': ['#CE1141', '#C4CED4', '#C4CED4', '#111', '#EF3A55'], 'IND': ['#002D62', '#FDBB30', '#FDBB30', '#111'],
    'LAC': ['#C8102E', '#1D428A', '#BEC0C2', '#111', '#EF3A55'], 'LAL': ['#552583', '#FDB927', '#7C4DBF', '#fff'],
    'MEM': ['#5D76A9', '#12173F', '#7D9BC1', '#fff'], 'MIA': ['#98002E', '#F9A01B', '#41B6E6', '#111'],
    'MIL': ['#00471B', '#EEE1C6', '#EEE1C6', '#111', '#4CAF62'], 'MIN': ['#0C2340', '#78BE20', '#78BE20', '#111'],
    'NOP': ['#0C2340', '#C8102E', '#B4975A', '#111'], 'NYK': ['#006BB6', '#F58426', '#BEC0C2', '#111', '#F58426'],
    'OKC': ['#007AC1', '#EF3B24', '#4FA3E0', '#fff'], 'ORL': ['#0077C0', '#C4CED4', '#C4CED4', '#111', '#3BA2E6'],
    'PHI': ['#006BB6', '#ED174C', '#ED174C', '#fff'], 'PHX': ['#1D1160', '#E56020', '#F9AD1B', '#111'],
    'POR': ['#E03A3E', '#000000', '#BAC3C9', '#111', '#EF4B4F'], 'SAC': ['#5A2D81', '#63727A', '#A2AAAD', '#111', '#A57BE0'],
    'SAS': ['#000000', '#C4CED4', '#C4CED4', '#111'], 'TOR': ['#CE1141', '#000000', '#A1A1A4', '#111', '#EF3A55'],
    'UTA': ['#002B5C', '#F9A01B', '#F9A01B', '#111'], 'WAS': ['#002B5C', '#E31837', '#C4CED4', '#111', '#EF3A55'],
}

JS = r"""
// 手機表格用的縮寫名：名縮成首字母，姓（含 Jr. 等）照留
const shortName = n => { const i = n.indexOf(' '); return i > 0 ? n[0] + '. ' + n.slice(i + 1) : n; };
// OVR 分級：110 珍珠／100 紫／90 金／80 銀／70 銅／其他灰字無框（門檻同 Baseball_algo getRarityClass，配色見 CSS）
const ovrBadge = v => { const r = Math.round(v); return `<span class="ob t${r >= 110 ? 6 : r >= 100 ? 5 : r >= 90 ? 4 : r >= 80 ? 3 : r >= 70 ? 2 : 1}">${r}</span>`; };
// E-116：2027 頁（近 5 場）的新秀都是新秀先驗，起點由選秀順位估，打越多場越靠自己的數據
const rookieTag = p => REAL_VIEW === 'g5' && ROOKIES.has(p.name)
  ? `<span class="rkp" title="新秀：沒有上季卡，開季起點由選秀順位與位置估，已打 ${p.gp} 場，打越多場越看自己的數據" role="img" aria-label="新秀"></span>` : '';
// 交易球員的 team 是「舊/新」，最後一段是現在的球隊
const teamOf = t => TEAM_COLORS[t.split('/').pop()];
const lum = h => { const n = parseInt(h.slice(1), 16); return 0.299 * (n >> 16) + 0.587 * (n >> 8 & 255) + 0.114 * (n & 255); };
function teamVars(t) {
  const c = teamOf(t);
  // --dk：兩個主題色裡比較深的那個，選中列（金底）的縮寫用
  return c ? `--tc:${c[0]};--tc2:${c[1]};--card:${c[2]};--ink:${c[3]};--tt:${c[4] || c[2]};--dk:${lum(c[0]) <= lum(c[1]) ? c[0] : c[1]}` : '';
}
function teamCell(t) {
  return teamOf(t) ? `<span class="tabbr" style="${teamVars(t)}">${t}</span>` : t;
}
function headshot(p) {
  const r = REAL[p.name], tid = TEAM_IDS[p.team.split('/').pop()];
  const logo = tid ? `<img class="logo" alt="" src="https://cdn.nba.com/logos/nba/${tid}/global/L/logo.svg" onerror="this.remove()">` : '';
  // 眼線對齊（使用者 2026-10-30）：照片眼睛 y（0–190）往下移到 EYE_Y，底部同量裁掉；比 EYE_Y 還低的不動
  const d = r && r.ey ? (Math.max(0, EYE_Y - r.ey) / 190 * 100).toFixed(1) : 0;
  const fit = d > 0 ? ` style="transform:translateY(${d}%);clip-path:inset(0 0 ${d}% 0)"` : '';
  return logo + (r && r.id ? `<img class="shot" alt="" loading="lazy" src="https://cdn.nba.com/headshots/nba/latest/1040x760/${r.id}.png"${fit} onerror="this.remove()">` : '');
}
// 身高旁的年齡、薪水（使用者 2026-11-01）：22y、$12.3M（未滿百萬寫 $850K）
function bioTag(p) {
  const b = PROF[p.name];
  if (!b) return '';
  const sal = b.sal == null ? '' : b.sal >= 1e6 ? `$${(b.sal / 1e6).toFixed(1)}M` : `$${Math.round(b.sal / 1e3)}K`;
  return (b.age ? `<i>${b.age}y</i>` : '') + (sal ? `<i>${sal}</i>` : '');
}
// 姓後面的年齡薪水換到下一行、姓本身被切開、或起點超過數據框 → 改成三個都放名右邊（.nm.tight）
function fitBio() {
  document.querySelectorAll('.who .nm').forEach(nm => {
    const b = nm.querySelector('.nbio'), l = nm.querySelector('.last'), h = nm.querySelector('.nht');
    if (!b || !l || !h) return;
    nm.classList.remove('tight');
    if (!b.offsetParent || !b.textContent) return;
    const lr = l.getClientRects(), br = b.getBoundingClientRect();
    // 起點超過下方數據框（得分…正負值）右緣也算放不下（使用者 2026-11-01）
    const box = nm.parentElement.querySelector('.rmain');
    if (lr.length > 1 || br.top >= lr[lr.length - 1].bottom - 4 || (box && box.offsetParent && br.left > box.getBoundingClientRect().right))
      nm.classList.add('tight');
  });
}
let fitBioQ = 0;
const fitBioSoon = () => { if (!fitBioQ) fitBioQ = requestAnimationFrame(() => { fitBioQ = 0; fitBio(); }); };
document.addEventListener('DOMContentLoaded', () => {
  new MutationObserver(fitBioSoon).observe(document.body, {childList: true, subtree: true});
  addEventListener('resize', fitBioSoon);
  document.fonts && document.fonts.ready.then(fitBioSoon);
  fitBioSoon();
});
function realBox(p) {
  const r = REAL[p.name];
  if (!r) return '<div class="real-h">真實數據：找不到這位球員的 2025-26 例行賽紀錄</div>';
  // 在名單上但還沒出賽（傷兵等，gp 0）：照常排出各格、數字寫「—」，卡片高度才和別人一樣（使用者 2026-10-31）
  if (!r.gp) {
    const cell = l => `<span>${l}<b>—</b></span>`;
    return `<div class="real-h">本季尚未出賽</div>
      <div class="real rx"><div class="rmain">${['得分', '籃板', '助攻', '正負值'].map(l => `<div class="st"><b>—</b><span>${l}</span></div>`).join('')}</div>
      <div class="rsub"><div>${['命中率', '三分', '罰球', '真實命中'].map(cell).join('')}</div><div>${['抄截', '阻攻', '失誤'].map(cell).join('')}</div></div>
      <button type="button" class="g5t" style="visibility:hidden" tabindex="-1" aria-hidden="true"><i>▼</i>近 0 場比賽</button></div>`;
  }
  // 100% 以上（小樣本，如 1 場 TS 133%）不顯示小數，細項才不會比別人長、多換一行讓卡片變高
  const f1 = v => v.toFixed(1), pc = v => (v == null ? '—' : (v * 100).toFixed(v >= 1 ? 0 : 1) + '%');
  const pm = v => (v > 0 ? '+' : '') + v.toFixed(1);
  // 主次分明（使用者 2026-10-29：十二格一樣大太雜）：得分／籃板／助攻大格，其餘分三行小字
  const main = [['得分', f1(r.pts)], ['籃板', f1(r.reb)], ['助攻', f1(r.ast)], ['正負值', pm(r.pm)]];
  const sub = [[['命中率', pc(r.fg)], ['三分', pc(r.fg3)], ['罰球', pc(r.ft)], ['真實命中', pc(r.ts)]],
    [['抄截', f1(r.stl)], ['阻攻', f1(r.blk)], ['失誤', f1(r.tov)]]];
  // 標題只留場數和場均分鐘（使用者 2026-10-29：「例行賽真實數據」字太多）
  const n = r.g5.length, sv = REAL_VIEW === 'season', lab = sv ? '整季細項' : `近 ${n} 場比賽`;
  return `<div class="real-h">${r.gp} 場 · ${Math.round(r.mpg)} 分鐘${r.teams.length > 1 ? '<span class="rtm"> · ' + r.teams.join('/') + '</span>' : ''}</div>
      <div class="real rx"><div class="rmain">${main.map(([l, v]) => `<div class="st"><b>${v}</b><span>${l}</span></div>`).join('')}</div>
      <div class="rsub">${sub.map(g => `<div>${g.map(([l, v]) => `<span>${l}<b>${v}</b></span>`).join('')}</div>`).join('')}</div>
      <button type="button" class="g5t" aria-expanded="${G5_OPEN}" aria-label="${lab}" title="${lab}" onclick="toggleG5(this)"><i>▼</i>${lab}</button></div>
      <div class="g5${sv ? ' sd' : ''}"${G5_OPEN ? '' : ' hidden'}>${sv ? seasonLog(r) : gameLog(r, p)}</div>`;
}
// 近 N 場逐場（新到舊）：[日期, 對手, 勝負, 分鐘, 得分, 籃板, 助攻, 抄截, 阻攻, 失誤, 投進, 出手, 三分進, 三分出手, 罰進, 罰球, 正負值, 貢獻值]
let G5_OPEN = false;
function toggleG5(b) {
  G5_OPEN = !G5_OPEN;
  b.setAttribute('aria-expanded', String(G5_OPEN));
  document.querySelector('.card .g5').hidden = !G5_OPEN;
  if (typeof fitTable === 'function') fitTable();
}
// 整條都能點（使用者 2026-11-04）：桌機卡片「▼ 近 N 場比賽」那一整排（含中間空白與右邊「N 場 · 分鐘」）點了都展開；
// 手機的 ▼ 是角落小按鈕，改成點兩組四格也展開。排除連結、按鈕、表格
function g5Hit(e) {
  const c = e.target.closest && e.target.closest('.card');
  if (!c || e.target.closest('a,button,.g5')) return null;
  const b = c.querySelector('.g5t');
  if (!b || b.getAttribute('aria-hidden')) return null;
  // 手機（使用者 2026-11-04）：得分／籃板／助攻／正負值四格與影響力四格也能點
  if (innerWidth < 641) return e.target.closest('.rmain,.strong') ? b : null;
  if (e.target.closest('.strong')) return null;
  const r = b.getBoundingClientRect(), cr = c.getBoundingClientRect(), h = c.querySelector('.real-h');
  const hr = h && h.getBoundingClientRect();
  const inBand = e.clientY >= r.top && e.clientY <= (G5_OPEN ? r.bottom : cr.bottom) && e.clientX >= cr.left && e.clientX <= cr.right;
  const inH = hr && e.clientX >= hr.left && e.clientX <= hr.right && e.clientY >= hr.top && e.clientY <= hr.bottom;
  return inBand || inH ? b : null;
}
document.addEventListener('click', e => { const b = g5Hit(e); if (b) toggleG5(b); });
document.addEventListener('mousemove', e => {
  const c = e.target.closest && e.target.closest('.card');
  if (c) c.style.cursor = g5Hit(e) ? 'pointer' : '';
});
// 貢獻值（使用者 2026-10-30 選 A）：box score＋hustle＋防守對位換算的每 36 分鐘淨影響（M2，R-066；權重擬合 2025-26 RAPM），和 2025-26 整季比；
// OVR 傾向＝把差值當成 pred 的變動，照正式卡（card 0.2.7c）的錨點與分鐘權重 W(MPG) 換算（只顯示，不改 OVR）
// 數字寫絕對值，顏色看和自己平均的差（使用者 2026-10-30：同樣 +3，替補是進步、SGA 是退步）：
// 五色切點＝2025-26 全部比賽「貢獻值 − 自己整季平均」絕對值的 20／60 百分位，各色約兩成（使用者 2026-10-30 選單場、5 場分開切）：
// 單場（上場 ≥10 分鐘）與連續 5 場分開切；M2（R-066）重算為 ±0.8／±2.8、±0.4／±1.3（fit_rating_m2.py 注入 GC_CUT）。顏色是排名，不代表顯著
const [GC_CUT1, GC_CUT5] = GC_CUT;
const sg1 = v => (v > 0 ? '+' : '') + v.toFixed(1);
// 顯示成 0 起跳的「評分」（使用者 2026-10-30：正負號配紅字看不清；名稱改評分，避免和影響力、正負值混在一起，像賽事的 0–10 評分）：分數＝0.75×(貢獻值＋7.5)，低於 0 記 0。
// M2（R-066）2025-26 單場（≥10 分鐘）約 2% 到 0、約 6% 超過 10；聯盟平均 ≈ 5.8。顏色仍用原單位的差值切
const gcS = v => Math.max(0, v).toFixed(1); // Z1（E-169，M6 加分改 S 形）：資料端已是 0–10 評分
const GC_DEF = '評分 0–10（M6 S 形）：整場貢獻：box score＋防守對位＋在場正負值＋扛出手量加分（比平均多投又維持效率會加分，扛越多及格線越低，效率越接近及格線加分越平滑地變多）；上場越久影響越大；上場很短時往聯盟平均拉回。5.8＝聯盟平均單場，10 約是單場前 6%。正負值會沾到隊友與對手的運氣';
const gcCls = (d, [a, b]) => d >= b ? 'c5a' : d >= a ? 'c5b' : d > -a ? 'c5c' : d > -b ? 'c5d' : 'c5f';
function gcCell(v, b, cut, fb, tip) {
  if (v == null) return '<td>—</td>';
  return `<td${tip ? ` title="${tip}"` : fb ? ' title="這場抓不到防守對位資料，只用 box score 算"' : ''}><span class="${b == null ? '' : gcCls(v - b, cut)}">${gcS(v)}</span></td>`;
}
// 手寫的個別球員註解（使用者 2026-11-04）：接在 N 場平均評分／上季後面。數字會隨賽程變，改前先對照最新 g5
const GC_NOTE = {
  1630162: '*因為本季命中率下降＋失誤上升，所以即使得分很多，OVR仍不變', // Anthony Edwards
  1642843: '*由於上季球隊戰績差，加上效率很差，本季的初始OVR很低、爬升較慢', // Cooper Flagg
  1630163: '*傳球、三分、持球創造都很強，但近距離與中距離出手弱、防守與身體條件偏低，所以OVR被拉低', // LaMelo Ball
  1642844: '*新秀，起始值依選秀順位偏保守；中距離、三分、造犯規都偏弱，OVR隨比賽慢慢爬升', // Dylan Harper
  1627783: '*罰球與中距離偏弱、外圍壓迫偏低，拉低OVR（內線得分與籃板仍是強項）', // Pascal Siakam
};
const gcExtra = r => REAL_VIEW === 'g5' && GC_NOTE[r.id] ? `　<span class="gcx">${GC_NOTE[r.id]}</span>` : '';
function gcNote(r, p, n) {
  const c = r.gc;
  if (c.r == null) return '';
  // 說明只寫兩個數字（使用者 2026-10-30：太長）；五色怎麼切、換算 OVR 放 tooltip
  if (c.b == null) return `<div class="gcn" title="${GC_DEF}">${n} 場平均評分 <b>${gcS(c.r)}</b>　上季 —${gcExtra(r)}</div>`;
  const d = c.r - c.b, cls = gcCls(d, GC_CUT5);
  return `<div class="gcn" title="${GC_DEF}。顏色＝和自己 2025-26 平均比，照所有人的起伏五等分">` +
    `${n} 場平均評分 <b class="${cls}">${gcS(c.r)}</b>　上季 <b>${gcS(c.b)}</b>${gcExtra(r)}</div>`;
}
// 近 5 場逐項上色（使用者 2026-11-03）：五色，每項照它在 2025-26 單場分布的百分位（g[20]，Python item_cls；難拿的項目如阻攻 1 次就算高），中間 50% 灰。分項在 g[19]，順序同 Python ITEM_ORDER
const ITEM_C5 = {'-2': 'c5f', '-1': 'c5d', 0: 'c5c', 1: 'c5b', 2: 'c5a'};
const ITEM_LAB = ['基準', '得分', '籃板', '助攻', '抄截', '阻攻', '失誤', '防守追蹤', '正負值'];
const ITEM_COL = {4: 1, 5: 2, 6: 3, 7: 4, 8: 5, 9: 6, 16: 8}; // 表格欄 index → 分項 index
const itemSg = v => (v >= 0 ? '+' : '−') + Math.abs(v).toFixed(1);
function itemTd(g, i, txt) {
  const it = g[19] && g[19][ITEM_COL[i]];
  if (it == null) return `<td>${txt}</td>`;
  return `<td class="${ITEM_C5[g[20][ITEM_COL[i]]]}" title="這項 ${itemSg(it)} 分（顏色照 2025-26 單場這一項的分布）">${txt}</td>`;
}
function scoreTip(g) {
  const it = g[19], fb = g[18] ? '這場抓不到防守對位資料，只用 box score 算。' : '';
  if (!it) return fb;
  const tot = it.reduce((s, v) => s + v, 0);
  return fb + it.map((v, k) => `${ITEM_LAB[k]} ${itemSg(v)}`).join('、') + `；合計 ${tot.toFixed(1)}` + (tot < 0 ? '（負值顯示 0.0）' : '');
}
function gameLog(r, p) {
  const gs = r.g5;
  const pm = v => (v > 0 ? '+' : '') + v;
  const ma = (m, a) => `${m}-${a}`;
  const row = g => `<td>${g[0]}</td><td>${g[1]}</td><td><span class="${g[2] === 'W' ? 'w' : 'l'}">${g[2] === 'W' ? '勝' : '負'}</span></td>` +
    gcCell(g[17], r.gc.b, GC_CUT1, g[18], scoreTip(g)) + [4, 5, 6, 7, 8, 9].map(i => itemTd(g, i, g[i])).join('') +
    `<td>${ma(g[10], g[11])}</td><td>${ma(g[12], g[13])}</td><td>${ma(g[14], g[15])}</td>${itemTd(g, 16, pm(g[16]))}<td>${g[3]}</td>`;
  const n = gs.length, sum = i => gs.reduce((s, g) => s + g[i], 0), avg = i => (sum(i) / n).toFixed(1);
  // 平均列的投籃／三分／罰球改顯示 N 場合計命中率（使用者 2026-10-30），滑過看合計進球-出手
  const pct = (m, a) => `<td title="合計 ${sum(m)}-${sum(a)}">${sum(a) ? (sum(m) / sum(a) * 100).toFixed(1) + '%' : '—'}</td>`;
  // 貢獻值放在勝負後面、分鐘移到最右（使用者 2026-10-30）
  const head = ['日期', '對手', '勝負', '評分', '得分', '籃板', '助攻', '抄截', '阻攻', '失誤', '投籃', '三分', '罰球', '正負', '分鐘'];
  const gcTip = GC_DEF + '；顏色＝和自己 2025-26 平均比，照所有人的起伏五等分';
  return `<table><thead><tr>${head.map(h => `<th${h === '評分' ? ` title="${gcTip}"` : ''}>${h}</th>`).join('')}</tr></thead><tbody>${gs.map(g => `<tr>${row(g)}</tr>`).join('')}</tbody>` +
    `<tfoot><tr><td colspan="3">${n} 場平均</td>${gcCell(r.gc.r, r.gc.b, GC_CUT5)}${[4, 5, 6, 7, 8, 9].map(i => `<td>${avg(i)}</td>`).join('')}` +
    `${pct(10, 11)}${pct(12, 13)}${pct(14, 15)}<td>${pm(+avg(16))}</td><td>${avg(3)}</td></tr></tfoot></table>${gcNote(r, p, n)}`;
}
// 2026 頁下拉看整季細項（使用者 2026-10-30）：卡片上已有場均得分／命中率，這裡補進球-出手、前後場籃板、犯規與每 36 分鐘
function seasonLog(r) {
  const d = r.sd, k = 36 / r.mpg, f1 = v => v.toFixed(1), pc = v => (v == null ? '—' : (v * 100).toFixed(1) + '%');
  const rows = [['得分', r.pts], ['籃板', r.reb], ['進攻籃板', d.oreb], ['防守籃板', d.dreb], ['助攻', r.ast],
    ['抄截', r.stl], ['阻攻', r.blk], ['失誤', r.tov], ['犯規', d.pf]];
  const shots = [['投籃', d.fgm, d.fga, r.fg], ['三分', d.fg3m, d.fg3a, r.fg3], ['罰球', d.ftm, d.fta, r.ft]];
  const a = `<table><thead><tr><th></th><th>場均</th><th>每 36 分鐘</th></tr></thead><tbody>` +
    rows.map(([l, v]) => `<tr><td>${l}</td><td>${f1(v)}</td><td>${f1(v * k)}</td></tr>`).join('') + '</tbody></table>';
  const b = `<table><thead><tr><th></th><th>進-出手</th><th>命中率</th></tr></thead><tbody>` +
    shots.map(([l, m, t, p]) => `<tr><td>${l}</td><td>${f1(m)}-${f1(t)}</td><td>${pc(p)}</td></tr>`).join('') +
    `<tr><td>真實命中</td><td></td><td>${pc(r.ts)}</td></tr></tbody></table>`;
  const gc = d.gc == null ? '' : `<div class="gcn" title="${GC_DEF}">整季評分 <b>${gcS(d.gc)}</b>　場均 ${Math.round(r.mpg)} 分鐘</div>`;
  return `<div class="sdw">${a}${b}</div>${gc}`;
}
function impactChips(p) {
  const r = REAL[p.name], m = r && IMPACT[r.id];
  // 沒有 RAPM（新秀等）也排滿四格「—」，卡片高度才和別人一樣（使用者 2026-10-30）
  if (!m) return `<div class="strong">${['進攻影響', '防守影響', '淨影響', '在場增益'].map(lab =>
    `<span class="chip" title="無 2025-26 RAPM">${lab}<i class="flat">—</i></span>`).join('')}</div>`;
  const sg = v => (v > 0 ? '+' : '') + v.toFixed(1);
  const cls = v => (v >= 0.5 ? 'up' : v <= -0.5 ? 'dn' : 'flat');
  // 缺值也排一格「—」（還沒出賽的人沒有本季數據估計），四格才排滿
  const chip = (lab, v, tip) => v == null ? `<span class="chip" title="${tip}">${lab}<i class="flat">—</i></span>` : `<span class="chip" title="${tip}">${lab}<i class="${cls(v)}">${sg(v)}</i></span>`;
  return `<div class="strong">${chip('進攻影響', m.o, '2025-26 RAPM 進攻：在場時球隊每 100 回合多得幾分（控制隊友與對手，對聯盟平均）')}${
    chip('防守影響', m.d, '2025-26 RAPM 防守：在場時對手每 100 回合少得幾分（正值＝少失分）')}${
    chip('淨影響', m.o + m.d, '2025-26 RAPM 淨值＝進攻＋防守')}${
    chip('在場增益', m.onoff, '2025-26 他在場減不在場的球隊每 100 回合淨效率（扣掉球隊本身強弱；會受替補好壞影響）' + (m.on == null ? '' : '；在場時球隊淨效率 ' + sg(m.on)))}</div>`;
}
// 手機位置下拉：按鈕顯示目前位置，點了才展開位置列（#posSeg 每次 render 重建，用 observer 同步）
(() => {
  const seg = document.getElementById('posSeg'), ctrl = seg && seg.closest('.ctrl');
  if (!ctrl) return;
  const btn = document.createElement('button');
  btn.type = 'button'; btn.className = 'pbtn'; btn.setAttribute('aria-label', '選擇位置');
  seg.before(btn);
  const sync = () => {
    const b = seg.querySelector('[aria-pressed="true"]'), all = !b || b === seg.firstElementChild;
    btn.textContent = all ? '位置' : b.textContent;
    btn.classList.toggle('on', !all);
  };
  sync();
  new MutationObserver(sync).observe(seg, { childList: true, subtree: true, attributes: true });
  const close = () => { ctrl.classList.remove('popen'); btn.setAttribute('aria-expanded', 'false'); };
  btn.onclick = () => { const o = ctrl.classList.toggle('popen'); btn.setAttribute('aria-expanded', String(o)); };
  seg.addEventListener('click', e => { if (e.target.closest('button')) close(); });
  document.addEventListener('click', e => { if (!btn.contains(e.target) && !seg.contains(e.target)) close(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && ctrl.classList.contains('popen')) { close(); btn.focus(); } });
  const q = document.getElementById('q');
  if (q && matchMedia('(max-width:640px)').matches) q.placeholder = '搜尋';
})();
// 桌機表格不左右捲（使用者 2026-11-03）：視窗放不下整張表時整張等比縮小（zoom），不裁掉欄位；換頁／排序重畫後重算。
(() => {
  const box = document.querySelector('.tbox'), tbl = document.getElementById('tbl'); if (!box || !tbl) return;
  const mq = matchMedia('(min-width:641px)'), de = document.documentElement; let last = '';
  // 刷新時眉頭不跳（使用者 2026-11-03）：頁首 script 已先套上次存的 --tw；字型載完前量到的是備用字型寬度，有存值就先不改，載完再寫並存起來
  const TWK = 'bbac.tw:' + (/^\/(rank|games)\//.test(location.pathname) ? '/' : location.pathname), fontsOk = () => !document.fonts || document.fonts.status === 'loaded';
  let saved = null; try { saved = localStorage.getItem(TWK); } catch (e) {}
  // 可用寬度只看視窗寬（不看 .wrap：.wrap 寬度又由 --tw 決定，互相回饋會在 Ctrl+-／非整數縮放時來回抖）。
  // offsetWidth 是未縮放的整數自然寬度，不受 zoom 影響；--tw 也在這裡一起寫，值沒變就不寫。
  function run() {
    const w = tbl.offsetWidth, sb = box.offsetWidth - box.clientWidth;
    if (!w) return;  // 切到戰力排行時名單是 display:none，量到 0；這時重畫表格不能把 --tw／zoom 清掉（切回來卡片會變超寬），等 ResizeObserver 在顯示後重算
    let z = '', bw = '', tw = '';
    if (mq.matches) {
      tw = (w + sb) + 'px';
      const avail = Math.min(de.clientWidth, 1360) - 32 - sb;
      if (w > avail && avail > 0) { z = (avail / w).toFixed(3); bw = '100%'; }
    }
    const ok = fontsOk(), hold = !!(tw && saved && !ok);
    const key = z + '|' + bw + '|' + tw + '|' + ok;
    if (key === last) return;
    last = key; tbl.style.zoom = z; box.style.width = bw;
    if (hold) return;
    if (tw) de.style.setProperty('--tw', tw); else de.style.removeProperty('--tw');
    if (tw && ok && tw !== saved) try { localStorage.setItem(TWK, saved = tw); } catch (e) {}
  }
  // 全部同步算（MutationObserver 是 microtask，仍在繪製前）；rAF 會晚一格，背景分頁還會整個停掉
  addEventListener('resize', run); mq.addEventListener('change', run);
  new MutationObserver(run).observe(tbl.tBodies[0] || tbl, {childList: true});
  // 字型載入後自然寬度才定；ready 觸發當下 status 有時還不是 loaded（量不到也存不了），loadingdone 後下一輪再算一次
  if (document.fonts) { document.fonts.ready.then(run); document.fonts.addEventListener('loadingdone', () => setTimeout(run)); }
  if (window.ResizeObserver) new ResizeObserver(run).observe(tbl);  // 名單從 display:none 切回來（0→有寬度）時重算；值沒變 run 會直接略過，不會和 zoom 互相觸發
  run();
})();
// 閒置過久切回分頁表格各欄疊在左邊（使用者 2026-11-03，iOS Safari）：sticky 欄＋橫向捲動容器的繪圖層被系統回收後沒重建；
// 切回分頁（visibilitychange／pageshow／focus）時強制重排＋重建合成層，並把 scrollLeft 寫回去，不改版面值。
(() => {
  const box = document.querySelector('.tbox'); if (!box) return;
  let busy = 0;
  function repaint() {
    if (document.hidden || busy) return;
    busy = requestAnimationFrame(() => {
      const l = box.scrollLeft, t = box.style.transform;
      box.style.transform = 'translateZ(0)'; void box.offsetWidth;
      box.scrollLeft = l + 1; box.scrollLeft = l;
      requestAnimationFrame(() => { box.style.transform = t; busy = 0; });
    });
  }
  document.addEventListener('visibilitychange', repaint);
  addEventListener('pageshow', repaint); addEventListener('focus', repaint);
})();
// 手機表格手勢鎖方向（使用者 2026-10-29：往上滑時手會左右偏，表格跟著晃）：先移動 10px 才判方向，
// 水平量要大於垂直 1.5 倍才算左右捲，判定後整段手勢只動那一軸。放手後照速度慣性滑行。
// 表格自己捲只從數值格啟動（使用者 2026-10-30）：從表頭或 #／名字／OVR 欄開始的手勢上下捲整頁，不捲表格。
(() => {
  const box = document.querySelector('.tbox'); if (!box) return;
  const mq = matchMedia('(max-width:640px)'), LOCK = 10, RATIO = 1.5;
  let s = null, raf = 0;
  box.addEventListener('touchstart', e => {
    cancelAnimationFrame(raf); raf = 0; s = null;
    if (!mq.matches || e.touches.length > 1) return;
    const t = e.touches[0];
    const page = !!e.target.closest('thead,td.no,td.nm,td.ovr');
    s = {x: t.clientX, y: t.clientY, el: page ? document.scrollingElement : box, axis: page ? 'y' : null, hist: []};
    s.l = s.el.scrollLeft; s.tp = s.el.scrollTop;
  }, {passive: true});
  box.addEventListener('touchmove', e => {
    if (!s || e.touches.length > 1) return;
    const t = e.touches[0], dx = t.clientX - s.x, dy = t.clientY - s.y;
    if (!s.axis) {
      if (Math.hypot(dx, dy) < LOCK) return;
      s.axis = Math.abs(dx) > Math.abs(dy) * RATIO ? 'x' : 'y';
    }
    if (s.axis === 'x') s.el.scrollLeft = s.l - dx; else s.el.scrollTop = s.tp - dy;
    const now = performance.now();
    s.hist.push([now, s.axis === 'x' ? t.clientX : t.clientY]);
    while (s.hist.length > 2 && now - s.hist[0][0] > 100) s.hist.shift();
  }, {passive: true});
  const end = () => {
    const g = s; s = null;
    if (!g || !g.axis || g.hist.length < 2) return;
    const a = g.hist[0], b = g.hist[g.hist.length - 1], dt = b[0] - a[0];
    let v = dt > 0 && performance.now() - b[0] < 80 ? -(b[1] - a[1]) / dt : 0, last = performance.now();
    const step = now => {
      const d = now - last; last = now; v *= Math.pow(0.996, d);
      if (Math.abs(v) < 0.03) { raf = 0; return; }
      if (g.axis === 'x') g.el.scrollLeft += v * d; else g.el.scrollTop += v * d;
      raf = requestAnimationFrame(step);
    };
    if (Math.abs(v) > 0.1) raf = requestAnimationFrame(step);
  };
  box.addEventListener('touchend', end);
  box.addEventListener('touchcancel', () => { s = null; });
})();
"""

GCW = json.loads((GC / 'weights.json').read_text(encoding='utf-8'))
M6C = json.loads((ROOT / 'reports/rating-m6/params.json').read_text(encoding='utf-8'))['prod']

BEGIN, END = '<!-- real-stats:begin -->', '<!-- real-stats:end -->'


def aggregate():
    rs = json.loads(SRC.read_text(encoding='utf-8'))['data']['resultSets'][0]
    h = {k: i for i, k in enumerate(rs['headers'])}
    acc, games = {}, {}
    log_keys = ['MIN', 'PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'FGM', 'FGA', 'FG3M', 'FG3A', 'FTM', 'FTA', 'PLUS_MINUS']
    for row in rs['rowSet']:
        name = row[h['PLAYER_NAME']]
        a = acc.setdefault(name, {'id': row[h['PLAYER_ID']], 'gp': 0, 'teams': [], **{k: 0 for k in log_keys + ['OREB', 'DREB', 'PF']}})
        a['gp'] += 1
        games.setdefault(name, []).append(row)
        team = row[h['TEAM_ABBREVIATION']]
        if team not in a['teams']:
            a['teams'].append(team)
        for k in a:
            if k.isupper():
                a[k] += row[h[k]] or 0
    # 「上季」＝2025-26 各球員單場評分簡單平均（Z1，上線參數；E-169，使用者 2026-11-01 採用）
    s25 = rating_m10.Scorer('2025-26', 'Z1')
    acc25 = {}
    for pid_, mn_, sc_ in zip(s25.tab.pid, s25.tab.mn, s25.S):
        if mn_ > 0:
            acc25.setdefault(str(pid_), []).append(float(sc_))
    base = {k: {'m6': round(sum(v) / len(v), 3)} for k, v in acc25.items()}
    # SRC 指哪季（build_inseason_viewer 會換成 season-source-2026-27），對位資料就讀哪季；某場沒對位資料 → 該場用 M0
    season_ = '2025-26' if SRC.parent.name == 'season-source' else SRC.parent.name.removeprefix('season-source-')
    m6 = rating_m10.Scorer(season_, 'Z1')
    rater = rating_m2.Rater('2025-26' if SRC.parent.name == 'season-source' else SRC.parent.name.removeprefix('season-source-'))
    box = lambda r: m6.score(r[h['GAME_ID']], r[h['PLAYER_ID']])  # Z1 單場評分（0–10 尺度）
    pr = json.loads((rating_m10.OUT / 'params.json').read_text(encoding='utf-8'))['prod']
    assert pr['P4']['K'] == 0, '分項拆解假設 P4 沒有收縮（K=0）'
    bgc = rating_m10.bonus(m6.tab, pr['Z1'], *rating_m10.ARMS['Z1'])[1] * pr['Z1']['c']  # 扛量加分換成評分點數（逐列對應 m6.tab）
    parts = lambda r: item_parts(r, h, rater, pr, bgc[m6.idx[(r[h['GAME_ID']], r[h['PLAYER_ID']])]])
    ref = item_ref(pr)
    parts_cls = lambda r: (lambda p: [p, item_cls(p, ref)])(parts(r))
    out = {}
    for name, a in acc.items():
        n = a['gp']
        last = sorted(games[name], key=lambda r: (r[h['GAME_DATE']], r[h['GAME_ID']]), reverse=True)[:5]
        rm = sum(r[h['MIN']] or 0 for r in last)
        b = base.get(str(a['id']))
        pct = lambda m, t: round(m / t, 4) if t else None
        tsa = 2 * (a['FGA'] + 0.44 * a['FTA'])
        out[name] = {
            'id': a['id'], 'gp': n, 'teams': a['teams'],
            'mpg': round(a['MIN'] / n, 2), 'pts': round(a['PTS'] / n, 2), 'reb': round(a['REB'] / n, 2),
            'ast': round(a['AST'] / n, 2), 'stl': round(a['STL'] / n, 2), 'blk': round(a['BLK'] / n, 2),
            'tov': round(a['TOV'] / n, 2), 'pm': round(a['PLUS_MINUS'] / n, 2),
            'fg': pct(a['FGM'], a['FGA']), 'fg3': pct(a['FG3M'], a['FG3A']), 'ft': pct(a['FTM'], a['FTA']),
            'ts': pct(a['PTS'], tsa),
            # 每列最後兩格＝該場貢獻值（每 36 分鐘，沒上場為 null）、1＝該場沒有對位資料改用 M0
            # index 19＝評分分項（評分點數，順序見 ITEM_ORDER；加總＝截 0 前的評分）、20＝各分項五色等級（−2..2，見 item_cls）
            'g5': [game_row(r, h, log_keys) + ([round(box(r), 2), m6.fallback(r[h['GAME_ID']], r[h['PLAYER_ID']]), *parts_cls(r)] if r[h['MIN']] else [None, 0, None, None])
                   for r in last],
            # 貢獻值：r＝近 N 場合計換算每 36 分鐘，b＝2025-26 整季（沒有 2025-26 紀錄＝null）
            'gc': {'r': round(sum(box(r) for r in last if r[h['MIN']]) / sum(1 for r in last if r[h['MIN']]), 2) if rm else None,
                   'b': b['m6'] if b else None},
            # 整季細項（2026 頁下拉，使用者 2026-10-30）：場均進球／出手、前後場籃板、犯規，與整季貢獻值（分鐘加權）
            'sd': {k.lower(): round(a[k] / n, 2) for k in ['FGM', 'FGA', 'FG3M', 'FG3A', 'FTM', 'FTA', 'OREB', 'DREB', 'PF']}
                  | {'gc': round(sum(box(r) for r in games[name] if r[h['MIN']]) / sum(1 for r in games[name] if r[h['MIN']]), 2) if a['MIN'] else None},
        }
    return out


ITEM_ORDER = ['base', 'pts', 'reb', 'ast', 'stl', 'blk', 'tov', 'def', 'pm']  # 要和 JS 的 ITEM_LAB 同序
ITEM_GROUP = {'PTS': 'pts', 'FGA': 'pts', 'FTA': 'pts', 'FG3M': 'pts', 'OREB': 'reb', 'DREB': 'reb', 'AST': 'ast', 'STL': 'stl', 'BLK': 'blk', 'TOV': 'tov'}  # 其餘（PF、追蹤欄）→ def


def item_parts(r, h, rater, pr, bonus_pts):
    """一場評分拆成各項的評分點數（c·權重·次數；MIN 在 G=(x−R)·MIN/36 裡消掉），順序同 ITEM_ORDER，加總＝截 0 前的評分。
    得分＝PTS／FGA／FTA／FG3M 加扛量加分；防守＝PF＋追蹤欄；沒有對位資料的場次用 M0 權重（防守＝PF）。"""
    P, C = pr['P4'], pr['Z1']
    e = rater.extra(r[h['GAME_ID']])
    w, intercept = (rater.w['per36'], rater.w['intercept']) if e is not None else (rater.m0['per36'], rater.m0['intercept'])
    x = e.get(r[h['PLAYER_ID']], {}) if e is not None else {}
    out = dict.fromkeys(ITEM_ORDER, 0.0)
    out['base'] = C['a'] + C['c'] * (intercept - P['R']) * r[h['MIN']] / 36
    for k, b in w.items():
        out[ITEM_GROUP.get(k, 'def')] += C['c'] * b * ((r[h[k]] or 0) if k in h else x.get(k, 0))
    out['pts'] += float(bonus_pts)
    out['pm'] = C['c'] * P['bq'] * (r[h['PLUS_MINUS']] or 0)
    return [round(out[k], 3) for k in ITEM_ORDER]


ITEM_REF_MIN = 15  # 分項難度的參考分布：2025-26 上場 ≥ 15 分鐘的單場
ITEM_PCT = (0.10, 0.25, 0.75, 0.90)  # 五色切點（百分位）：中間 50% 灰，兩側各 15% 淺色、10% 深色（使用者 2026-11-03：依各項難易度、灰色區放大）


def item_ref(pr):
    """各分項在 2025-26（≥ ITEM_REF_MIN 分鐘）單場的評分點數，排序後的陣列，給 item_cls 查百分位。"""
    import numpy as np
    rs = json.loads((ROOT / 'data' / 'season-source' / 'player-games.json').read_text(encoding='utf-8'))['data']['resultSets'][0]
    h = {k: i for i, k in enumerate(rs['headers'])}
    sc, rater = rating_m10.Scorer('2025-26', 'Z1'), rating_m2.Rater('2025-26')
    bgc = rating_m10.bonus(sc.tab, pr['Z1'], *rating_m10.ARMS['Z1'])[1] * pr['Z1']['c']
    rows = [item_parts(r, h, rater, pr, bgc[sc.idx[k]]) for r in rs['rowSet']
            if (r[h['MIN']] or 0) >= ITEM_REF_MIN and (k := (r[h['GAME_ID']], r[h['PLAYER_ID']])) in sc.idx]
    return np.sort(np.array(rows), axis=0).T


def item_cls(parts, ref):
    """每個分項依它在參考分布的百分位（同值取中位名次，離散項目如抄截、阻攻不會被並列拉偏）分五級 −2..2；
    評分點數＝0（沒加也沒扣）一律 0。"""
    import numpy as np
    out = []
    for v, col in zip(parts, ref):
        if v == 0:
            out.append(0)
            continue
        q = (np.searchsorted(col, v - 1e-6) + np.searchsorted(col, v + 1e-6)) / 2 / len(col)
        out.append(-2 if q <= ITEM_PCT[0] else -1 if q <= ITEM_PCT[1] else 2 if q >= ITEM_PCT[3] else 1 if q >= ITEM_PCT[2] else 0)
    return out


def game_row(r, h, keys):
    """一場 → [M/D, 'vs BOS'／'@ BOS', W/L, 分鐘…正負值]（給卡片的近 5 場表）。"""
    _, m, d = r[h['GAME_DATE']][:10].split('-')
    mu = r[h['MATCHUP']].split()
    return [f'{int(m)}/{int(d)}', ('@ ' if mu[1] == '@' else 'vs ') + mu[-1], r[h['WL']]] + [r[h[k]] or 0 for k in keys]


def impact():
    """playerId → {o, d, on, onoff}：2025-26 單季 box-prior RAPM 攻守，與在場淨效率、在場減不在場（交易球員依在場回合加權）。"""
    if IMPACT_LOADER:
        return IMPACT_LOADER()
    out = {}
    for r in csv.DictReader(RAPM.open(encoding='utf-8')):
        out[int(r['playerId'])] = {'o': float(r['lastSeasonO']), 'd': float(r['lastSeasonD'])}
    acc = {}
    for r in csv.DictReader(ONOFF.open(encoding='utf-8')):
        if r['season'] != '2025-26':
            continue
        a = acc.setdefault(int(r['playerId']), [0.0, 0.0, 0.0])
        w = float(r['onPoss'])
        a[0] += w
        a[1] += w * float(r['onNet'])
        a[2] += w * float(r['onOffNet']) if r['onOffNet'] else 0
    for pid, (w, on, onoff) in acc.items():
        if pid in out and w > 0:
            out[pid].update(on=round(on / w, 2), onoff=round(onoff / w, 2))
    return out


def rookies(view):
    path, year = BIO[view]
    if not path.exists():
        return []
    d = json.loads(path.read_text(encoding='utf-8'))['data']['resultSets']
    rs = d[0] if isinstance(d, list) else d
    h = {k: i for i, k in enumerate(rs['headers'])}
    return sorted(r[h['PLAYER_NAME']] for r in rs['rowSet'] if str(r[h['DRAFT_YEAR']]) == year)


def profiles(view):
    """{名字: {'age': 年齡, 'sal': 薪水（美元）}}；名字未對到名單，inject 再用 fold 對。"""
    out = {}
    # 2027 頁還沒出賽的人不在本季 bio：先用上季 bio 年齡＋1 墊底，本季有的再蓋掉
    for v, plus in ([('season', 1), ('g5', 0)] if view == 'g5' else [(view, 0)]):
        path = BIO[v][0]
        if not path.exists():
            continue
        d = json.loads(path.read_text(encoding='utf-8'))['data']['resultSets']
        rs = d[0] if isinstance(d, list) else d
        h = {k: i for i, k in enumerate(rs['headers'])}
        for r in rs['rowSet']:
            if r[h['AGE']] is not None:
                out.setdefault(r[h['PLAYER_NAME']], {})['age'] = int(r[h['AGE']]) + plus
    sp = SALARY[view]
    if sp.exists():
        # 被裁球員有兩列（舊隊死錢＋新隊），取第一列（bref 依金額排序）
        for row in re.findall(r'<tr[^>]*>(.*?)</tr>', sp.read_text(encoding='utf-8'), re.S):
            m = re.search(r'data-stat="player"[^>]*>(?:<a[^>]*>)*([^<]+)', row)
            y = re.search(r'data-stat="y1"[^>]*>\$?([\d,]+)', row)
            if m and y:
                out.setdefault(html.unescape(m.group(1)), {}).setdefault('sal', int(y.group(1).replace(',', '')))
    return out


def pkey(name):
    """比對 NBA／bref／名單名字：去重音、標點、Jr./III 等字尾。"""
    return re.sub(r'\b(jr|sr|ii|iii|iv)\b|[^a-z ]', '', fold(name).replace('.', '').replace("'", '')).replace(' ', '')


def fold(name):
    return unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode().casefold()


def team_ids():
    rs = json.loads(SRC.read_text(encoding='utf-8'))['data']['resultSets'][0]
    h = {k: i for i, k in enumerate(rs['headers'])}
    return {row[h['TEAM_ABBREVIATION']]: row[h['TEAM_ID']] for row in rs['rowSet']}


def inject(path, real, view='g5'):
    """view：卡片下拉看什麼，'g5'＝近 5 場逐場（2027 頁），'season'＝整季細項（2026 頁）。"""
    s = path.read_text(encoding='utf-8')
    s = re.sub(re.escape(BEGIN) + r'.*?' + re.escape(END) + r'\n?', '', s, flags=re.S)
    names = json.loads(re.search(r'const DATA=(\{.*?\});\nconst COLS', s, re.S).group(1))
    col = names['cols'].index('name')
    roster = [r[col] for r in names['rows']]
    # 名單名字和 NBA 原始資料的重音可能不同（2026-27 源資料是 Moussa Cissé、卡片是 Moussa Cisse）：比對時忽略重音
    by_fold = {fold(n): n for n in real}
    by_roster = {fold(n): n for n in roster}
    sub = {n: real[by_fold[fold(n)]] for n in roster if fold(n) in by_fold}
    ids = {v['id'] for v in sub.values()}
    eye = headshot_eyeline.ensure(ids)
    sub = {n: {**v, 'ey': eye.get(str(v['id']))} for n, v in sub.items()}
    imp = {pid: v for pid, v in impact().items() if pid in ids}
    by_key = {}
    for n, v in profiles(view).items():
        by_key.setdefault(pkey(n), {}).update(v)
    prof = {n: by_key[pkey(n)] for n in roster if pkey(n) in by_key}
    js_json = lambda o: json.dumps(o, ensure_ascii=False, separators=(',', ':'))
    a = json.loads(CARD_SUMMARY.read_text(encoding='utf-8'))['anchors']
    block = (f'{BEGIN}\n<style>{CSS}</style>\n<script>const REAL={js_json(sub)};\nconst REAL_VIEW={js_json(view)};\n'
             f'const ROOKIES=new Set({js_json([by_roster[fold(n)] for n in rookies(view) if fold(n) in by_roster])});\nconst IMPACT={js_json(imp)};\n'
             f'const GC_ANC={js_json([a["PR1"], a["PR50"], a["PR99"]])};\nconst GC_CUT={js_json([M6C["cut1"], M6C["cut5"]])};\n'
             f'const PROF={js_json(prof)};\n'
             f'const TEAM_COLORS={js_json(TEAM_COLORS)};\nconst TEAM_IDS={js_json(team_ids())};\nconst EYE_Y={headshot_eyeline.TARGET};{JS}</script>\n{END}\n')
    assert s.count('<script>const DATA=') == 1
    s = s.replace('<script>const DATA=', block + '<script>const DATA=', 1)
    hook = '<div class="strong">${tops.map(t => chip(t[0], t[1])).join(\'\')}${chip(\'弱項 \' + low[0], low[1], true)}</div>'
    s = s.replace('${teamDot(p.team)}${p.team}', '${p.team}')  # 舊版注入
    s = s.replace('${headshot(p)}<span class="pos">', '${headshot(p)}<div class="tnm"><span>${esc(first)}</span>${esc(last)}</div><span class="tht">${ht(p.ht)}</span><span class="pos">')  # 舊版注入（橫幅名字前）
    # 能力值前三／弱項改成影響力（使用者 2026-10-29）；樣板可能已含 realBox
    s = s.replace(hook + '\n      ${realBox(p)}', hook)
    for old, new in [
        (hook, '${impactChips(p)}\n      ${realBox(p)}'),
        ("document.getElementById('card').innerHTML = `", "document.getElementById('card').style.cssText = teamVars(p.team);\n  document.getElementById('card').innerHTML = `"),
        ('<div class="tag"><span class="pos">', '<div class="tag" style="${teamVars(p.team)}">${headshot(p)}<div class="tnm"><span>${esc(first)}</span>${esc(last)}</div><span class="tht">${ht(p.ht)}</span><span class="pos">'),
        ("<td class=\"ovr${sc('ovr')}\">${p.ovr.toFixed(1)}</td>", "<td class=\"ovr${sc('ovr')}\" title=\"${p.ovr.toFixed(1)}\">${ovrBadge(p.ovr)}</td>"),  # 表格只顯示整數並分級上色（使用者 2026-11-01），滑過看小數
        ("<td class=\"sub${sc('team')}\">${p.team}</td>", "<td class=\"sub${sc('team')}\">${teamCell(p.team)}</td>"),
        ('<tr class="grp"><th colspan="6"></th>', '<tr class="grp"><th colspan="3"></th><th class="gx" colspan="3"></th>'),
        ('<td class="nm" title="${esc(p.name)}">${esc(p.name)}</td>',
         '<td class="nm${rookieTag(p) ? \' rk\' : \'\'}" title="${esc(p.name)}"><span class="nf">${esc(p.name)}</span><span class="ns">${esc(shortName(p.name))}</span>${rookieTag(p)}</td>'),
        # 「往下展開 20 人」每按一次多 20 人、越拉越長（使用者 2026-11-01）：改成每頁 20／50 人切換，再按一次收回；
        # 切換時保留目前看到的第一位所在的頁
        ('const SIZE = 20;', 'let SIZE = 20;'),
        ('<button class="more" id="more" type="button">往下展開 20 人</button>', '<button class="more" id="more" type="button">展開至 50 人</button>'),
        ('  m.hidden = end >= a.length;\n  m.onclick = () => { st.extra++; render(); };',
         "  m.hidden = SIZE === 20 && a.length <= 20;\n"
         "  m.textContent = SIZE === 20 ? '展開至 50 人' : '收回 20 人';\n"
         # 展開＝表格往下長、整頁捲，不要表格內捲軸（使用者 2026-11-01）；收回時捲回表格頂
         "  document.querySelector('.tbox').classList.toggle('grow', SIZE === 50);\n"
         "  m.onclick = () => { const top = st.page * SIZE; SIZE = SIZE === 20 ? 50 : 20; st.page = Math.floor(top / SIZE); st.extra = 0; const t = document.querySelector('.tbox'); t.scrollTop = 0; render(); tboxEdges(); if (SIZE === 20 && t.getBoundingClientRect().top < 0) t.scrollIntoView({ block: 'start' }); };"),
        # 展開至 50 人時表格比視窗高，換頁的 scrollIntoView('nearest') 會把畫面拉走、不能連按下一頁（使用者 2026-11-01）：
        # 展開時改成讓頁碼列留在原本的螢幕位置
        ("    b.onclick = () => { st.page = pg; st.extra = 0; render(); document.querySelector('.tbox').scrollIntoView({ block: 'nearest' }); };",
         "    b.onclick = () => {\n"
         "      const pe = document.getElementById('pages'), y0 = pe.getBoundingClientRect().top;\n"
         "      st.page = pg; st.extra = 0; render();\n"
         "      if (SIZE === 50) scrollBy(0, pe.getBoundingClientRect().top - y0);\n"
         "      else document.querySelector('.tbox').scrollIntoView({ block: 'nearest' });\n"
         "    };"),
        # 頁碼固定 7 格（號碼＋…），… 也佔一格同寬，「›」不再隨頁數左右跑，可以連按（使用者 2026-11-01）
        ("  const show = [...new Set([0, tot - 1, st.page - 1, st.page, st.page + 1])].filter(x => x >= 0 && x < tot).sort((a, b) => a - b);",
         "  const show = tot <= 7 ? [...Array(tot).keys()]\n"
         "    : st.page < 4 ? [0, 1, 2, 3, 4, tot - 1]\n"
         "    : st.page > tot - 5 ? [0, tot - 5, tot - 4, tot - 3, tot - 2, tot - 1]\n"
         "    : [0, st.page - 1, st.page, st.page + 1, tot - 1];"),
        ('.pages .gap{color:var(--muted);padding:5px 2px}',
         '.pages .gap{color:var(--muted);padding:5px 2px;width:34px;box-sizing:border-box;text-align:center}'),
    ]:
        if new not in s:
            assert s.count(old) == 1, old
            s = s.replace(old, new, 1)
    # 桌機（使用者 2026-11-01）：身高放名（SHAI）右邊、年齡薪水放姓後面；姓後面放不下時 fitBio() 把三個都搬到名右邊（.b1）
    s = s.replace('<span class="tht">${ht(p.ht)}</span>', '<span class="tht">${ht(p.ht)}${bioTag(p)}</span>')
    s = s.replace('<span class="first">${esc(first)}</span>${esc(last)}<span class="nht">${ht(p.ht)}</span>',
                  '<span class="first">${esc(first)}<span class="nht">${ht(p.ht)}<span class="b1">${bioTag(p)}</span></span></span>'
                  '<span class="last">${esc(last)}</span><span class="nbio">${bioTag(p)}</span>')
    path.write_text(s, encoding='utf-8')
    missing = [n for n in roster if n not in sub]
    print(f'{path}: {len(sub)}/{len(roster)} 人有真實數據；缺 {len(missing)}: {missing[:10]}')
    print(f'  年齡 {sum("age" in v for v in prof.values())}、薪水 {sum("sal" in v for v in prof.values())} 人；'
          f'缺薪水: {[n for n in roster if "sal" not in prof.get(n, {})][:10]}')


if __name__ == '__main__':
    real = aggregate()
    for p in sys.argv[1:]:
        inject(Path(p), real)
