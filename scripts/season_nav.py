"""名單頁的賽季切換列（靜態相對連結，沿用頁面既有 CSS 變數，不需 JS）。"""
import html
import json
import re
from pathlib import Path

# 標籤用年份（使用者 2026-10-29；11-04 拿掉 beta）：2027＝2026-27 賽中，2026＝2025-26 正式卡
PAGES = [('inseason', '2027', '/'), ('card', '2026', '/2025-26.html')]
# icon＝五格評分環、亮四格薄荷綠（使用者 2026-11-04 選 E4，取代 10-30 的金色籃球）；favicon 與版標同一張
# 眉頭只用環（RING，不帶外框，使用者 2026-11-04「外面的框好醜」）；favicon 仍帶深底方框，在分頁列上才看得清楚
RING = ('<g fill="none" stroke-width="9" transform="rotate(-86 32 32)">'
         '<circle cx="32" cy="32" r="19" stroke="#1f2a26" stroke-dasharray="19.87 4"/>'
         '<circle cx="32" cy="32" r="19" stroke="#3ddc97" stroke-dasharray="19.87 4 19.87 4 19.87 4 19.87 23.87"/></g>')
GAUGE = '<rect x=".5" y=".5" width="63" height="63" rx="14" fill="#0b0e12" stroke="#1e252e"/>' + RING
FAVICON = ('<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,'
           + ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
              + GAUGE + '</svg>').replace('"', "'").replace('#', '%23').replace('<', '%3C').replace('>', '%3E') + '">')
# 連結預覽（Discord／Threads／LINE 等）：縮圖 1200×630 由 scripts/build_og_image.py 產生，發布到網站根目錄
OG_TAGS = ('<meta property="og:type" content="website"><meta property="og:site_name" content="TrueOVR">'
           '<meta property="og:title" content="球員能力值 · TrueOVR">'
           '<meta property="og:description" content="NBA 球員評分、球隊戰力排行與賽程勝率">'
           '<meta property="og:url" content="https://trueovr.com/">'
           '<meta property="og:image" content="https://trueovr.com/og-image.png">'
           '<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">'
           '<meta name="twitter:card" content="summary_large_image">'
           '<meta name="twitter:image" content="https://trueovr.com/og-image.png">')
LOGO = '<svg class="logo" viewBox="0 0 64 64" aria-hidden="true">' + GAUGE + '</svg>'
CSS = """<style>
.top{position:relative;z-index:5}
.top{align-items:center}
.brand{display:flex;align-items:center;gap:10px}
.brand .logo{width:44px;height:44px;flex:none}
@media (max-width:640px){.brand .logo{width:36px;height:36px}}
.snav{display:flex;flex-wrap:wrap;align-items:center;gap:6px 10px;margin:6px 0 4px}
.snav .seg a{display:block;background:var(--panel);color:var(--muted);border-right:1px solid var(--line);font:600 .9rem var(--f-disp);letter-spacing:.04em;padding:6px 11px;text-decoration:none;white-space:nowrap}
.snav .seg a:last-child{border-right:0}
.snav .seg a[aria-current="page"]{background:var(--gold);color:var(--gold-ink)}
.snav .seg a:focus-visible{outline:2px solid var(--gold);outline-offset:1px}
.snav .note{color:var(--muted);font-size:.8rem}
.pnote summary{list-style:none;cursor:pointer;display:inline-flex;align-items:center;gap:6px;background:var(--panel);color:var(--muted);border:1px solid var(--line);border-radius:3px;font:600 .85rem var(--f-disp);letter-spacing:.04em;padding:5px 10px;user-select:none}
.pnote summary::-webkit-details-marker{display:none}
.pnote summary::after{content:"▾";font-size:.8em;opacity:.8}
.pnote summary:hover{color:var(--fg);border-color:var(--muted)}
.pnote summary:focus-visible{outline:2px solid var(--gold);outline-offset:1px}
.pnote[open] summary{color:var(--gold);border-color:var(--gold)}
.sright{display:flex;align-items:center;gap:8px}
/* 手機：A+／99 搬到更新說明旁邊、兩個一起靠右，搜尋欄變長（使用者 2026-10-30） */
@media (max-width:640px){
  .snav{display:grid;grid-template-columns:1fr auto;gap:6px 10px}
  .snav .seg{justify-self:start}
  .snav.has-note .seg{grid-column:1/-1}
  .snav .note{line-height:1.4}
  .snav .pnote summary{height:32px;box-sizing:border-box;padding:0 10px}
  .snav #modeSeg{flex:none}
  .snav #modeSeg button{height:30px;padding:0 10px;font:600 .85rem var(--f-disp);letter-spacing:.04em}
}
.pn{position:absolute;left:0;top:calc(100% + 6px);width:min(560px,100%);max-height:min(72vh,680px);overflow:auto;overscroll-behavior:contain;box-sizing:border-box;
  background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:14px;box-shadow:0 16px 40px rgba(0,0,0,.6);scrollbar-width:thin;scrollbar-color:#38424f transparent}
.pn h2{font:800 1.05rem var(--f-disp);letter-spacing:.06em;margin:0 0 10px;text-transform:uppercase}
.pn h2 span{color:var(--gold)}
.pn-now{background:var(--panel-2);border:1px solid var(--line);border-radius:5px;padding:9px 12px;margin-bottom:12px;color:var(--muted);font-size:.78rem;line-height:1.6}
.pn-now b{display:block;color:var(--gold);font:700 .72rem var(--f-disp);letter-spacing:.12em;margin-bottom:2px}
.pn-now dl{display:flex;flex-wrap:wrap;gap:6px 24px;margin:4px 0 0}
.pn-now dt{color:var(--muted);font-size:.7rem}
.pn-now dd{margin:0;color:var(--fg);font:700 .95rem var(--f-disp);font-variant-numeric:tabular-nums}
.pn-list{list-style:none;margin:0;padding:0;display:grid;gap:8px}
.pn-item{--acc:#5b6b7f;background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--acc);border-radius:5px;padding:9px 12px 10px}
.pn-item{--acc:var(--gold)}
.pn-item.cur{border-color:var(--acc);box-shadow:0 0 0 1px var(--acc) inset}
.pn-item header{display:flex;flex-wrap:wrap;align-items:center;gap:6px 8px}
.pn-ver{font:800 1.2rem var(--f-disp);color:var(--fg);font-variant-numeric:tabular-nums;letter-spacing:.02em}
.pn-cur{font:700 .68rem var(--f-disp);letter-spacing:.08em;padding:2px 6px;border-radius:3px;background:var(--gold);color:var(--gold-ink)}
.pn-item time{margin-left:auto;color:var(--muted);font:500 .75rem var(--f-disp);font-variant-numeric:tabular-nums}
.pn-item ul{margin:6px 0 0;padding-left:1.15em;color:#c9d3df;font-size:.82rem;line-height:1.6}
.pn-item li::marker{color:var(--acc)}
.pn-item li b{color:var(--fg);font-weight:700}
.pn-item .kw{font-weight:700}
.pn-item .kw-ovr{color:var(--gold)}
.pn-item .kw-off{color:#ff7a45}
.pn-item .kw-def{color:#4fa8ff}
.pn-item .kw-etc{color:#c39bff}
.pn-item .kw-num{color:var(--fg);font-weight:700;font-variant-numeric:tabular-nums}
.pn-item li{position:relative}
.pn-more{display:inline-block;margin-left:5px;padding:0 6px;border:1px solid var(--line);border-radius:3px;color:var(--muted);font-size:.75rem;line-height:1.3;cursor:help;vertical-align:1px}
.pn-more:hover,.pn-more:focus{color:var(--gold);border-color:var(--gold);outline:0}
.pn-tip{display:none;position:absolute;left:0;top:100%;z-index:2;margin-top:4px;padding:8px 12px;grid-template-columns:auto auto auto;gap:3px 16px;
  background:#e8ecf1;color:#1a2029;border-radius:4px;font:500 .78rem/1.45 var(--f-disp);font-variant-numeric:tabular-nums;white-space:nowrap;box-shadow:0 8px 22px rgba(0,0,0,.55);cursor:default}
.pn-tip span:nth-child(3n+1){font-weight:700}
.pn-tip i{font-style:normal;font-size:.68rem;font-weight:700;letter-spacing:.05em;color:#6b7684;margin-right:2px}
.pn-tip .up{color:#0f8a4a;font-weight:700}
.pn-tip .dn{color:#c8322b;font-weight:700}
.pn-more:hover .pn-tip,.pn-more:focus .pn-tip{display:grid}
.pn-foot{margin:12px 0 0;color:var(--muted);font-size:.72rem;line-height:1.5}
.legend{align-items:baseline}
.ovr-t{display:inline-flex;align-items:center;gap:5px;background:none;border:0;padding:0;color:var(--muted);font:inherit;cursor:pointer;text-align:left}
.ovr-t b{color:var(--fg);font-weight:600}
.ovr-t:hover,.ovr-t[aria-expanded="true"]{color:var(--fg)}
.ovr-t i{display:inline-block;font-style:normal;font-size:.72em;transition:transform .15s}
.ovr-t[aria-expanded="true"] i{transform:rotate(180deg);color:var(--gold)}
.ovr-how{flex-basis:100%;display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:8px 16px;margin-top:4px;padding:10px 14px;background:var(--panel);border:1px solid var(--line);border-radius:4px;color:var(--muted);font-size:.78rem;line-height:1.55}
.ovr-how[hidden]{display:none}
.ovr-how b{color:var(--fg);font-weight:600}
.ovr-how .oh-t{display:block;color:var(--gold);font:700 .78rem var(--f-disp);letter-spacing:.04em;margin-bottom:2px}
</style>
"""


# 更新說明（Patch Notes）撰寫要旨（使用者 2026-10-29～11-01）：
# - 每版一格，新的在上；字母小版本一律併入該基底版本的條目清單下面，不單獨開卡，也不寫版號與字母前綴（不寫 0.2.10a、0.2.7a 等，R-064）。
# - 只寫公式改動：最新那格用 ('card', 'inseason') 標示「目前」（舊格只留 ('card',)），不另開一格、不寫「已跟上／沒跟上」；只更新比賽資料、網頁 UI、欄位顯示都不寫（R-063）。
# - 不顯示「正式卡／新賽季」標籤：兩頁已是同一條滑動窗口管線（0.2.12b 起約三季）、同一個版號（R-111，使用者 2026-11-01「先拿掉標籤」）。
# - 用字精簡、只留重點：每條寫成「目標：改法（代表球員名次或數值變化）」（冒號前加粗），用球迷看得懂的話，不寫 E／R 編號、不寫「OVR 前 20 名換幾人」等流水帳；代價直接併入括號或分號後一句帶過，不另起一行「代價：」。
# - 名次變動主文只留 0～2 個代表（開這個議題的起因球員優先，例如 Jokić、Jalen Williams；窗口類這種全面小調整給 0 個），完整名單寫在「｜」後面收進 ⋯ hover，每人一列「球員/名次（或數值變化）/OVR 前 → 後」、以「；」分隔，主文提到的人也列進去（使用者 2026-11-01）。
# - 同一件事分好幾步做的（例如分批改成滑動窗口），合成一條寫，⋯ 名單也合併（使用者 2026-11-02）。
# - 被後續版本取代或撤銷的條目，前後加 `~...~` 顯示刪除線（`<s>`）。
PATCH_NOTES = [
    # 版號 0.2.10：前 20 名進出 1 人（Embiid 進、Porter Jr. 出）、前 100 名移動 >=10 名 18 人，照 R-109 屬 PATCH（係數全凍結、只換 8 項屬性來源）
    # 版號 0.2.11：照 R-109 前 20 名進出 1 人、前 100 名移動 >=10 名 11 人原屬字母版（0.2.10j），使用者 2026-11-02「引進了一個有趣的新能力值。把它升級為patch」（R-137）
    # 0.2.12a（賽中端字母版，使用者 2026-11-02「現在就上 0.2.11a」，因 0.2.12 同時上線改疊在 0.2.12）：gravity 補值依分鐘往進攻 EPM 收縮，併入 0.2.12 格（R-064）
    # 版號 0.2.12：照 R-109 前 20 名進出 4 人、前 100 名移動 >=10 名 34 人原屬字母版，使用者 2026-11-02「直接採用」E-202 KT 臂（R-139）
    # 0.2.12b（使用者 2026-11-02「Adopt W246」，R-140，E-204）：窗口 328→246 格，係數不重擬合，併入 0.2.12 格（R-064）
    # 0.2.12c（使用者 2026-11-02「採用上線」，R-144，E-207）：tovSkill 失誤率分母由持球分鐘改觸球次數，併入 0.2.12 格（R-064）
    (('card', 'inseason'), '0.2.12', '2026-11-02', [
        '新賽季反應加快：能力值窗口由四季改為約三季，本季比賽權重加大、舊資料更快淡出。｜Jokić/2 → 2/103.2 → 102.6；Paul George/20 → 24/92.0 → 90.3；Jimmy Butler III/21 → 20/92.0 → 92.0；Tyrese Maxey/35 → 31/88.4 → 89.4；Immanuel Quickley/57 → 87/82.9 → 79.5；Josh Hart/82 → 66/79.7 → 81.5',
        'TO 改成看持球時間與每次觸球的失誤：持球多又少丟球才高分（Reaves 386 → 30 名、Cade 471 → 71 名）；不太拿球的空間射手與長人 TO 大降（Hauser 1 → 54 名、Kornet 23 → 106 名）。｜Reaves/26 → 12/90.8 → 93.8；Cade/11 → 14/93.4 → 93.6；Brunson/27 → 30/90.7 → 89.2；Harden/159 → 143/73.7 → 75.2；Luka/4 → 3/101.7 → 101.8；Jokić/2 → 2/105.7 → 103.1；Hauser/160 → 169/73.6 → 73.1；Hardaway Jr./317 → 314/60.8 → 61.4；Kornet/62 → 71/82.5 → 80.9；Jarrett Allen/44 → 46/86.4 → 85.1',
        '新秀引力不再看幾分鐘的出手：本季沒有引力數據的人，上場越少越參考進攻影響力（Joshua Jefferson 248 → 404 名）。｜Joshua Jefferson/248 → 404/65.4 → 51.4；Ja’Kobi Gillespie/300 → 445/59.9 → 48.8；AJ Dybantsa/52 → 78/83.1 → 79.9；Dejounte Murray/78 → 98/80.0 → 78.3；Javon Small/92 → 123/78.7 → 76.4；Ivica Zubac/95 → 80/78.6 → 79.8']),
    (('card',), '0.2.11', '2026-11-02', [
        '加引力能力值：沒拿球時防守人也不敢離開的射手加分（Klay 419 → 357 名），空間長人略降（Turner 108 → 123 名）。｜Klay/419 → 357/55.9 → 57.9；Hield/259 → 240/65.7 → 66.7；Kennard/135 → 120/75.6 → 76.4；Duncan Robinson/208 → 199/69.6 → 70.4；Hauser/175 → 160/72.9 → 73.6；Turner/108 → 123/77.8 → 76.3；Fox/24 → 20/91.2 → 92.1；Bane/20 → 21/92.0 → 92.0',
        '能力值頂端改尺：前 10%＝88、前 5%＝92、前 1%＝97，再往上看領先多少；3PT 98 以上從 15 人變 5 人（Curry 128 → 126），OVR 與名次不變。']),
    (('card',), '0.2.10', '2026-11-01', [
        '能力值與用人改看近四季滑動窗口：中距離、近框、罰球、造犯規、傳球、籃板、少失誤、切入、三分、自主創造、上場分鐘、教練用人、出賽率都隨比賽更新，換季不再陡跳；3PT 欄也改用窗口比較基準，主力射手差距拉開（Curry 120.7 → 125.2）。｜Flagg/82 → 68/76.1 → 77.0；Embiid/23 → 18/84.0 → 85.2；Porter Jr./20 → 40/84.7 → 81.3；Sabonis/138 → 75/72.9 → 77.1；Jalen Williams/12 → 9/87.0 → 90.7；Franz Wagner/21 → 42/84.1 → 81.3；Sengun/101 → 96/78.3 → 78.9；Mamukelashvili/88 → 117/79.2 → 77.0',
        '修 BPM 漏讀榜首：補回聯盟第一（Jokić 7 → 3 名）。｜Jokić/7 → 3/93.5 → 100.6；Kawhi/3 → 6/102.2 → 94.1',
        '傳球加分不分位置：持球前鋒不再多加分（Jalen Williams 9 → 12 名）。｜Jalen Williams/9 → 12/93.3 → 87.0；Barnes/18 → 27/92.2 → 83.5；Reaves/26 → 21/89.5 → 84.7',
        '拉開明星 OVR 差距：不再擠在 85–93，名次與 99 以上不變（Maxey 85.5 → 92.0）。｜Maxey/21 → 21/85.5 → 92.0；Mitchell/7 → 7/93.2 → 96.0',
        '賽中年齡固定看開季當天：不再因季中過生日跳分。｜Landale/278 → 257/61.6 → 63.8；Porziņģis/23 → 37/91.0 → 88.2',
        '切入、自主創造拆開算：切入只算帶球切入的自主兩分，自主創造改看自己創造的跳投與低位（Zion 自主創造 87 → 63）。｜Cameron Johnson/58 → 43/83.8 → 86.6；Bridges/53 → 41/84.7 → 87.1；Paul Reed/93 → 79/78.7 → 79.9；Sengun/91 → 81/78.9 → 79.9；Tre Jones/39 → 49/88.0 → 85.9；Dosunmu/69 → 94/81.4 → 78.6；Avdija/97 → 107/78.5 → 77.6']),
    (('card',), '0.2.9', '2026-11-01', [
        '拿掉「年輕人在爛隊打折」：換新標準後這個折扣反而失準（Flagg 195 → 79 名）。｜Flagg/195 → 79/70.6 → 77.6；Banchero/65 → 158/79.8 → 72.7',
        '拿掉耐力對 OVR 的重複加分：上場時間只算一次（Jalen Williams 17 → 10 名）。｜Jalen Williams/17 → 10/86.9 → 88.2；Porziņģis/60 → 32/79.0 → 81.9；Edgecombe/101 → 150/75.2 → 72.3']),
    (('card',), '0.2.8', '2026-11-01', [
        'OVR 改以 DARKO＋BPM 為準：取代 RAPM（Edwards 38 → 10 名）；防守型角色球員下修（Herb Jones 19 → 156 名）。']),
    (('card',), '0.2.7', '2026-10-30', [
        '提高防守比重、越近的比賽份量越重：White 8 → 4 名。｜White/8 → 4/96.5 → 99.7；Wembanyama/3 → 2/101.7 → 103.7；Luka/4 → 9/100.8 → 95.2',
        '傳球看量也看率：每 36 分鐘助攻與助攻率各半。｜Trae Young/傳球 104 → 110/69.4 → 70.1',
        '3PT、RIM、PRES 突破 99 上限：Curry 3PT 105。｜Curry/3PT 105/82.5 → 82.5；Thybulle/PRES 127/70.7 → 70.5',
        'OVR 拿掉身高體重加分：只看場上表現（Zion 43 → 65 名）。｜Zion/43 → 65/81.8 → 79.8；Mobley/28 → 23/84.3 → 84.9',
        '~爛隊年輕人折扣改看淨勝分：不再以勝率 35% 一刀切。~｜Flagg/293 → 230/61.5 → 68.3；Rollins/15 → 106/86.2 → 76.0']),
    (('card',), '0.2.6', '2026-10-30', [
        '補籃、補扣改算近距離：不再墊高中距離（Kessler 中距離 99 → 61）。',
        '能力值改跨四季比較：偏弱的一季可以沒人到 99。',
        'OVR 重調權重：近距離加重、中距離減輕（Giannis 11 → 5 名；Curry 23 → 32 名）。']),
    (('card',), '0.2.5', '2026-10-29', [
        '上場時間權重改邊際遞減：高效率替補不再被埋沒（Caruso 103 → 39 名）。']),
    (('card',), '0.2.4', '2026-10-29', [
        '修正年輕球員被低估：教練用人改對照當季表現，不再被往年拖累。']),
    (('card',), '0.2.3', '2026-10-29', [
        'OVR 納入教練用人：計入上場時間、出賽率、年齡與發展聯盟紀錄；輪休不當成被冷凍（DNP）。']),
    (('card',), '0.2.2', '2026-10-29', [
        '製造犯規（FD）改以量為主：每 36 分鐘罰球數佔 75%、罰球率 25%。']),
    (('card',), '0.2.1', '2026-10-29', [
        '壓迫（PRES）改看實際逼失誤：直接算逼出的對手失誤並扣犯規，不再從 RAPM 拆解。']),
    (('card',), '0.2.0', '2026-10-29', [
        'OVR 改算每場價值：納入上場時間、以替補水準為基準，同效率下打得多分數更高。']),
    (('card',), '0.1.2', '2026-10-28', [
        '對位防守改看對手出手習慣：不再依賴位置標籤（修 Wembanyama 被標前鋒卻守中鋒的誤判）。']),
    (('card',), '0.1.1', '2026-10-28', [
        '切入與造犯規分家：拆成「切入」與「製造犯規」兩項。',
        '修正低分鐘球員虛胖：比率型能力值優先往本人上季拉回，無歷史才往聯盟平均。']),
    (('card',), '0.1.0', '', [
        '初始版本：建立正式卡與隨比賽更新的新賽季模型。']),
]


def _now_facts(now_text, current):
    """從原本的長說明抽出幾個重點（使用者 2026-10-29：原文太長不適合人讀）；抽不到的欄位就不顯示。"""
    pick = lambda pat: (m.group(1) if (m := re.search(pat, now_text)) else None)
    if current == 'card':
        facts = [('版本', pick(r'card (\d+\.\d+\.\d+)')), ('資料', pick(r'（(\d{4}-\d{2}) 整季')),
                 ('球員', pick(r'(\d+) 人'))]
    else:
        cutoff = pick(r'數據截至 (\d{4}-\d{2}-\d{2})')
        facts = [('版本', pick(r'inseason (\d+\.\d+\.\d+)')), ('開季起點', pick(r'開季起點 card (\d+\.\d+\.\d+)')),
                 ('數據截至', cutoff and cutoff[5:].replace('-', '/')), ('球員', pick(r'· (\d+) 人'))]
        if facts[1][1]:
            facts[1] = ('開季起點', '正式卡 ' + facts[1][1])
    facts = [(k, v + ' 人' if k == '球員' else v) for k, v in facts if v]
    if not facts:
        return html.escape(now_text)
    return '<dl>' + ''.join(f'<div><dt>{k}</dt><dd>{html.escape(v)}</dd></div>' for k, v in facts) + '</dl>'


# 內文裡的數值名稱上色、數字加粗（使用者 2026-10-29，參考 arammeta 海克斯說明）。
# 只分四色：OVR 金、進攻＋投籃橘紅、防守藍、其他紫（使用者 2026-10-30 換色）；粗體目標裡的也上色；新名稱出現在說明裡就加進對應組。
NOTE_TERMS = {
    'ovr': ['OVR'],
    'off': ['三分價值', '3PT', '3P準', '罰球數', '罰球率', '罰球線', 'FD 製造犯規', '製造犯規（FD）', '製造犯規', '造犯規',
            '切入', '衝框', '中距離', '近距離', '補籃', '補扣', '進攻型球員'],
    'def': ['壓迫（PRES）', '壓迫', '對位防守', '防守加分', '防守數據', '防守'],
    'etc': ['RAPM', '上場時間', '上場分鐘', '出賽率', '預測 MPG', '每場價值', '分鐘權重', '教練用人', '替補水準', '輪休'],
}
_TERM_CLASS = {t: c for c, ts in NOTE_TERMS.items() for t in ts}
_NOTE_TOKEN = re.compile('|'.join(map(re.escape, sorted(_TERM_CLASS, key=len, reverse=True)))
                         + r'|(?<![A-Za-z\d.])\d+(?:\.\d+)*(?:-\d{2})?%?')


def _note_fmt(text):
    out, at = '', 0
    for m in _NOTE_TOKEN.finditer(text):
        tok, cls = html.escape(m.group(0)), _TERM_CLASS.get(m.group(0))
        out += html.escape(text[at:m.start()]) + (f'<span class="kw kw-{cls}">{tok}</span>' if cls
                                                   else f'<strong class="kw-num">{tok}</strong>')
        at = m.end()
    return out + html.escape(text[at:])


def _note_line(x):
    x, _, more = x.partition('｜')   # ｜後面＝其餘名次變動，收進 hover 提示（使用者 2026-11-01）
    strike = x.startswith('~') and x.endswith('~')
    goal, sep, rest = (x.strip('~') if strike else x).partition('：')
    body = f'<b>{_note_fmt(goal)}</b>：{_note_fmt(rest)}' if sep else _note_fmt(goal)
    if strike:
        body = f'<s style="opacity:.55">{body}</s>'
    if more:   # 每人一列：球員/名次或數值變化/OVR 變化；OVR 漲綠跌紅
        rows = ''
        for row in more.split('；'):
            name, chg, ovr = row.split('/')
            a, b = (float(v) for v in ovr.split(' → '))
            chg = f'第 {chg} 名' if re.fullmatch(r'\d+ → \d+', chg) else chg
            rows += (f'<span>{html.escape(name)}</span><span>{html.escape(chg)}</span>'
                     f'<span class="{"up" if b > a else "dn" if b < a else ""}"><i>OVR</i> {html.escape(ovr)}</span>')
        body += f'<span class="pn-more" tabindex="0" aria-label="名次與 OVR 變動">⋯<span class="pn-tip" role="tooltip">{rows}</span></span>'
    return f'<li>{body}</li>'


def patch_notes_html(now_text, current):
    """now_text：原本 <div class="src"> 的版本說明，抽重點放最上面當「目前版本」；只標本頁那條線的版號（新賽季頁說明裡的先驗 card 版號不算）。"""
    cur = {(current, v) for v in re.findall(rf'\b{current} (\d+\.\d+\.\d+)', now_text)}
    items = []
    for tracks, ver, date, lines in PATCH_NOTES:
        is_cur = any((t, ver) in cur for t in tracks)
        items.append(
            f'<li class="pn-item{" cur" if is_cur else ""}"><header>'
            + f'<b class="pn-ver">{ver}</b>'
            + ('<span class="pn-cur">目前</span>' if is_cur else '')
            + (f'<time datetime="{date}">{date[5:].replace("-", "/")}</time>' if date else '')
            + '</header><ul>' + ''.join(_note_line(x) for x in lines) + '</ul></li>')
    return ('<details class="pnote"><summary>更新說明</summary><div class="pn" role="region" aria-label="更新說明">'
            '<h2>Patch <span>Notes</span></h2>'
            f'<div class="pn-now"><b>目前版本</b>{_now_facts(now_text, current)}</div>'
            f'<ol class="pn-list">{"".join(items)}</ol>'
            '<p class="pn-foot">2026 與 2027 兩頁共用同一套模型與版號。</p></div></details>'
            # 點面板外或按 Esc 關掉
            "<script>(()=>{const d=document.querySelector('.pnote');"
            "document.addEventListener('click',e=>{if(d.open&&!d.contains(e.target))d.open=false});"
            "d.addEventListener('keydown',e=>{if(e.key==='Escape'){d.open=false;d.querySelector('summary').focus()}})})();</script>")


def add_season_nav(html_str, current):
    """current：'inseason' 或 'card'。取代 <div class="src">…</div>，原說明收進切換列的「更新說明」（點開才看，使用者 2026-10-29）。"""
    assert current in ('inseason', 'card'), current
    links = ''.join(f'<a href="{href}"' + (' aria-current="page"' if key == current else '') + f'>{label}</a>'
                    for key, label, href in PAGES)
    note = ''   # 0.2.10g（使用者 2026-11-01）：新賽季頁用人層也改四季窗口（0.2.12b 起約三季），與 2025-26 頁同演算法，拿掉「開季樣本少」提示
    # 手機寬度把 #modeSeg 從控制列搬進 .sright，桌機搬回搜尋欄前面
    mover = ("<script>addEventListener('DOMContentLoaded',()=>{const m=document.getElementById('modeSeg'),"
             "r=document.querySelector('.sright'),q=document.getElementById('q'),mq=matchMedia('(max-width:640px)');"
             "if(!m||!r||!q)return;const f=()=>mq.matches?r.append(m):q.before(m);f();mq.addEventListener('change',f)})</script>")
    block = lambda m: (f'\n<nav class="snav{" has-note" if note else ""}" aria-label="賽季切換"><div class="seg">{links}</div>{note}'
                       f'<span class="sright">{patch_notes_html(m.group(1), current)}</span>{mover}</nav>')
    s, n = re.subn(r'<div class="src">(.*?)</div>', block, html_str, count=1, flags=re.S)
    assert n == 1, 'src div not found'
    # 版標：icon＋原標題（標題上方小字使用者 2026-10-30 要拿掉）；favicon 放 <head>
    s, n = re.subn(r'<h1>(.*?)</h1>', lambda m: f'<div class="brand">{LOGO}<h1>{m.group(1)}</h1></div>', s, count=1)
    assert n == 1, 'h1 not found'
    assert s.count('<meta charset="utf-8">') == 1
    s = s.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n' + FAVICON + OG_TAGS, 1)
    # 能力值顯示四捨五入成整數（使用者 2026-10-30）；等第仍用原值算，OVR、得分、DIQ 等其他數字保留小數
    for a, b in [('>${v}</td>`; }', '>${Math.round(v)}</td>`; }'), ('${grade(v)} ${v}</i>', '${grade(v)} ${Math.round(v)}</i>'),
                 ('` title="${v}"`', '` title="${Math.round(v)}"`')]:
        assert s.count(a) == 1, a
        s = s.replace(a, b)
    s = attr_tips(s, current)
    return s.replace('<nav class="snav', CSS + '<nav class="snav', 1) if CSS not in s else s


# 能力值顯示尺（使用者 2026-11-02「三分球 98 以上的人太多了」→「所有能力值一起改」→「用方案 B」）：百分位型能力值原本
# PR50～99 線性對到 70～99（attr()），PR97.3 就有 98。頁面顯示改成 PR50→70、PR90→88、PR95→92、PR99→97，
# 99 以上的尾巴整段 −2（接在 97），PR<50 不動。只改顯示：ranking.csv、OVR、模擬用值不變；off/def 要在換尺前算。
# mid／short／help／long 不是百分位尺（≥90 只有 1～4%），不換。ft 2026-11-05（R-168）起也是百分位型（只看命中率，blend_display.py），
# 但在 display_rows 之後才由 build_*_viewer 覆蓋，自己呼叫 display_scale，不在 RESCALE_ATTRS。
RESCALE_ATTRS = ('threeValue', 'drive', 'foulDraw', 'gravity', 'pass', 'tovSkill', 'creation', 'rebound',
                 'physique', 'stamina', 'onBall', 'pressure', 'presDisplay')
_SCALE_KNOTS = ((50, 70), (90, 88), (95, 92), (99, 97))


def display_scale(v):
    """attr() 值 → 顯示尺：70～99 段反推 PR 再分段線性；>99（尾巴）−2；<70、None 原樣。"""
    if v is None or v < 70:
        return v
    if v > 99:
        return v - 2
    p = (v - 70) * 49 / 29 + 50
    for (a, b), (c, d) in zip(_SCALE_KNOTS, _SCALE_KNOTS[1:]):
        if p <= c:
            return b + (p - a) * (d - b) / (c - a)
    return 97.0


def display_rows(rows):
    """ranking.csv 的列（dict，值為字串）換成顯示尺；空字串照舊。"""
    return [{**r, **{k: repr(display_scale(float(r[k]))) for k in RESCALE_ATTRS if r.get(k, '') != ''}} for r in rows]


# 能力值滑鼠提示（使用者 2026-11-01，版型仿 arammeta 增幅卡：名稱＋副標、說明、細線下列組成）。
# 公式照 card 0.2.7d／inseason 0.2.7d：threeValue、foulDraw 見 run_c4_live.py meta；pass E-125；pressure E-071；onBall E-060；short E-056。
# frz＝賽季中凍結（沿用 2026 卡），只在新賽季頁顯示。寫給一般球迷看：不放收縮常數、z 分數這類細節（使用者 2026-11-01）。
ATTR_TIPS = {
    'ovr': ('總評', 'Overall', '綜合進攻、防守與上場時間的<b>每場比賽影響力</b>',
            [('場上能力', '14 項進攻與防守能力值'), ('防守意識', 'DIQ（防守 RAPM）'), ('上場時間', '場均分鐘＋出賽率')], ''),
    'off': ('進攻', 'Offense', '每 36 分鐘比聯盟平均<b>多得幾分</b>',
            [('組成', '75% 進攻能力值 ＋ 25% 進攻影響力'), ('單位', '每 36 分鐘淨分（0＝平均）')], False),
    'def': ('防守', 'Defense', '每 36 分鐘比聯盟平均<b>少丟幾分</b>',
            [('組成', '單防 ＋ 護框 ＋ 壓迫 ＋ 防守意識'), ('單位', '每 36 分鐘淨分（0＝平均）')], False),
    'threeValue': ('三分', 'Three-Point', '<b>60%</b> 三分出手量 ＋ <b>40%</b> 三分命中率',
                   [('出手量 60%', '三分出手 / 36'), ('命中率 40%', '三分命中率')], ''),
    'mid': ('中距離', 'Mid-Range', '油漆區外到三分線內的<b>投籃命中率與數量</b>', [], ''),
    'short': ('近框', 'Inside Scoring', '油漆區內（含籃下）的<b>命中率與自主得分</b>',
              [('自主創造', '100% 計入'), ('被餵球（吃餅）', '打折計入')], ''),
    'ft': ('罰球', 'Free Throw', '<b>罰球命中率</b>（罰球沒有防守，只看準度；量已在造犯規）',
           [('命中率', '罰球命中率')], ''),
    'drive': ('切入', 'Drive', '<b>帶球切入</b>到 10 呎內的自主兩分（量與效率各半）', [], ''),
    'foulDraw': ('製造犯規', 'Foul Drawing', '<b>75%</b> 罰球量 ＋ <b>25%</b> 罰球率',
                 [('罰球量 75%', '罰球數 / 36'), ('罰球率 25%', '罰球數 ÷ 投籃出手')], ''),
    'gravity': ('引力', 'Gravity', '<b>沒拿球</b>時吸引防守貼防的程度', [], None),
    'pass': ('傳球', 'Passing', '<b>50%</b> 助攻量 ＋ <b>50%</b> 助攻率',
             [('助攻量 50%', '助攻 / 36'), ('助攻率 50%', '在場時隊友進球被他助攻的比例')], ''),
    'creation': ('自主創造', 'Shot Creation', '<b>自己創造</b>的跳投與低位出手量', [], ''),
    'rebound': ('籃板', 'Rebounding', '在場時搶下可搶籃板的<b>籃板率</b>', [], ''),
    'tovSkill': ('少失誤', 'Ball Security', '<b>每次觸球的失誤率</b>與<b>持球時間</b>各半；不持球、失誤少的人不算數',
                 [('每次觸球失誤 50%', '越少越高'), ('持球時間 50%', '每 36 分鐘的持球時間')], ''),
    'pressure': ('壓迫', 'Pressure', '<b>抄截、干擾、逼失誤、造進攻犯規</b>（扣犯規）',
                 [('抄截／干擾／逼失誤', '各 1 份'), ('造進攻犯規', '0.5 份'), ('犯規', '扣 0.25')], ''),
    'onBall': ('單防', 'On-Ball Defense', '外線<b>干擾出手 ＋ 對位負擔 ＋ 威懾力</b>',
               [('對位負擔', '防守對象的球權使用率'), ('威懾力', '降低對手出手意願')], ''),
    'help': ('護框', 'Rim Protection', '讓對手在<b>籃下 6 呎內</b>命中率降低多少', [], ''),
    'dbon': ('防守意識', 'Defensive IQ', '數據以外的<b>團隊防守影響力</b>（輪轉、站位、補防）',
             [('單位', '每百回合淨分（非 0–99）'), ('計入 OVR', '僅正分加分')], False),
}
# 浮動提示卡的規則（使用者 2026-11-01：原生 title 太醜，配色照抄 arammeta docs/assets/site.css 的 .aug-tip／.cf-stage-tip）：
# - 表頭（能力值說明）和格子（該球員的細項）用同一張卡；有卡的元素不再帶 title，避免兩個提示疊在一起。
# - 卡：底 #101114、1px rgba(255,255,255,.08) 邊、圓角 10px、雙層陰影；淡入 0.14s 加上移 3px；箭頭 6px 指向元素。
# - 版面由上到下：名稱（金 #f5d780）＋英文縮寫（灰）＋右側大數字 → 一句說明 → 細線下的細項表 → 更細的線下灰色註腳。
# - 細項表三欄：名稱（灰 #8b919a）｜數值（白 #e8eaed，數字等寬）｜PR（小灰字）。聯盟前十在數值後加金色「（#名次）」。
# - 「越少越好」的項目（犯規）數值旁寫（多）／（普通）／（少），PR 一律是越高越好。卡上不解釋 PR 與名次（使用者 2026-11-01）。
# - 預設放元素下方，放不下改上方；左右夾在視窗內 8px。捲動就收起。
# - 觸控（使用者 2026-11-01）：表頭點一下只排序，長按（450ms）才顯示說明；格子同樣只有長按才顯示（2026-11-02 使用者：點一下不該馬上跳）；長按一直顯示，點別處才收，捲動時跟著元素。
TIP_CSS = """<style>
.atip{position:fixed;z-index:60;left:0;top:0;width:min(330px,calc(100vw - 16px));padding:11px 12px 10px;background:#101114;border:1px solid rgba(255,255,255,.08);border-radius:10px;box-shadow:0 12px 28px rgba(0,0,0,.5),0 0 0 1px rgba(0,0,0,.4);color:#c2c7ce;font:400 12px/1.5 var(--f-body);text-align:left;pointer-events:none;opacity:0;transform:translateY(-3px);transition:opacity .14s cubic-bezier(.16,1,.3,1),transform .14s cubic-bezier(.16,1,.3,1)}
.atip.on{opacity:1;transform:none}
.atip::before{content:"";position:absolute;left:var(--ax,50%);margin-left:-6px;border:6px solid transparent}
.atip.below::before{bottom:100%;border-bottom-color:#101114}
.atip.above::before{top:100%;border-top-color:#101114}
.atip .h{display:flex;align-items:baseline;gap:8px}
.atip .n{font-weight:700;font-size:13px;color:#f5d780}
.atip .s{color:#7a808a;font-size:10.5px;font-weight:600;letter-spacing:.06em}
.atip .v{margin-left:auto;font-size:15px;font-weight:700;color:#e8eaed;font-variant-numeric:tabular-nums}
.atip .d{color:#c5cad3;margin-top:5px}
.atip .d b{color:#e8eaed;font-weight:600}
.atip .r{display:grid;grid-template-columns:auto 1fr;align-items:baseline;gap:4px 12px;border-top:1px solid rgba(255,255,255,.06);margin-top:9px;padding-top:8px;font-variant-numeric:tabular-nums}
.atip .r.r3{grid-template-columns:auto 1fr auto}
.atip .r span{color:#8b919a}
.atip .r b{color:#e8eaed;font-weight:600;text-align:right;white-space:nowrap}
.atip .r em{color:#7a808a;font:normal 10.5px var(--f-body);text-align:right}
.atip .rk{color:#f5d780;font-style:normal;font-weight:700}
.atip .f{color:#6b7280;font-size:10.5px;line-height:1.5;border-top:1px solid rgba(255,255,255,.05);margin-top:8px;padding-top:7px}
@media (hover:none){[data-tip],[data-ck]{-webkit-touch-callout:none;-webkit-user-select:none;user-select:none}}
@media (prefers-reduced-motion:reduce){.atip{transition:none}}
</style>
"""
# 表頭帶 data-tip（ATIP 說明）、格子帶 data-ck（該列球員 p.tips[k]）；同一個浮動卡跟著元素定位
TIP_JS = """<script>
(() => {
  let tip, cur = null, timer, pinned = false;
  const head = k => { const t = ATIP[k]; if (!t) return null;
    return { n: t[0], s: t[1], d: t[2], rows: t[3] }; };
  const cell = el => { const tr = el.closest('tr[data-n]'); if (!tr) return null;
    const n = decodeURIComponent(tr.dataset.n), p = P.find(q => q.name === n);
    return p && p.tips ? p.tips[el.dataset.ck] : null; };
  const row = ([a, b, pr, rk]) => `<span>${a}</span><b>${b}${rk ? `<i class="rk">（#${rk}）</i>` : ''}</b>` +
    (pr === undefined ? '' : `<em>${pr == null ? '' : 'PR ' + pr}</em>`);
  const place = el => {
    const r = el.getBoundingClientRect(), w = tip.offsetWidth, h = tip.offsetHeight;
    let y = r.bottom + 9, below = true;
    if (y + h > innerHeight - 8) { y = r.top - h - 9; below = false; }
    const x = Math.min(Math.max(8, r.left + r.width / 2 - w / 2), document.documentElement.clientWidth - w - 8);
    tip.style.left = x + 'px';
    tip.style.top = Math.max(8, y) + 'px';
    tip.style.setProperty('--ax', Math.min(Math.max(14, r.left + r.width / 2 - x), w - 14) + 'px');
    tip.classList.toggle('below', below); tip.classList.toggle('above', !below);
  };
  // ms：觸控點一下顯示多久後收起；0＝不自動收（長按）
  const show = (el, ms) => {
    const t = el.dataset.tip ? head(el.dataset.tip) : cell(el); if (!t) return;
    tip = tip || document.body.appendChild(Object.assign(document.createElement('div'), { className: 'atip' }));
    tip.setAttribute('role', 'tooltip');
    tip.innerHTML = `<div class="h"><span class="n">${t.n}</span><span class="s">${t.s}</span>${t.v != null ? `<b class="v">${t.v}</b>` : ''}</div>` +
      (t.d ? `<div class="d">${t.d}</div>` : '') +
      (t.rows.length ? `<div class="r${t.rows[0].length > 2 ? ' r3' : ''}">${t.rows.map(row).join('')}</div>` : '') +
      (t.foot && t.foot.length ? `<div class="f">${t.foot.join('<br>')}</div>` : '');
    cur = el; pinned = ms === 0;
    place(el);
    tip.classList.add('on');
    clearTimeout(timer);
    if (ms) timer = setTimeout(hide, ms);
  };
  const hide = () => { cur = null; pinned = false; clearTimeout(timer); if (tip) tip.classList.remove('on'); };
  const target = e => e.target.closest('[data-tip],[data-ck]');
  // 滑鼠：移上去就顯示
  document.addEventListener('pointerover', e => {
    if (e.pointerType === 'touch') return;
    const el = target(e);
    if (el !== cur) el ? show(el) : hide();
  });
  // 觸控：表頭與格子都是點一下不顯示（表頭排序、格子開球員卡），長按才顯示，一直顯示到點別處或捲動
  let press = null, eat = false, lastTouch = 0;
  document.addEventListener('pointerdown', e => {
    if (e.pointerType !== 'touch') return;
    lastTouch = Date.now();
    const el = target(e);
    if (pinned && el !== cur) hide();
    if (!el) return;
    press = { el, x: e.clientX, y: e.clientY, t: setTimeout(() => { press = null; eat = true; show(el, 0); }, 450) };
  });
  const cancel = () => { if (press) { clearTimeout(press.t); press = null; } };
  document.addEventListener('pointermove', e => {
    if (press && Math.hypot(e.clientX - press.x, e.clientY - press.y) > 10) cancel();
  });
  document.addEventListener('pointercancel', cancel);
  document.addEventListener('pointerup', cancel);
  // 長按之後的 click 不算點擊（表頭不排序）；長按不叫出系統選單
  document.addEventListener('click', e => { if (eat) { eat = false; e.preventDefault(); e.stopPropagation(); } }, true);
  document.addEventListener('contextmenu', e => { if (target(e) && Date.now() - lastTouch < 1500) e.preventDefault(); });
  document.addEventListener('focusin', e => { if (Date.now() - lastTouch < 800) return; const el = target(e); el ? show(el) : hide(); });
  document.addEventListener('focusout', () => { if (!pinned) hide(); });
  addEventListener('scroll', () => { if (pinned && cur) place(cur); else hide(); }, true);
})();
</script>
"""


def pr_rank(x, pool, low_good=False):
    """(PR, 名次)：PR＝pool 中比 x 差的百分比（越高越好）；名次 1＝最好，只回傳前十，其餘 None。"""
    worse = sum((q > x) if low_good else (q < x) for q in pool)
    rank = sum((q < x) if low_good else (q > x) for q in pool) + 1
    return round(100 * worse / len(pool)), (rank if rank <= 10 else None)


def cell_tip(n, s, v, rows, d='', foot=()):
    """格子提示卡（TIP_JS 讀 p.tips[k]）。rows：[名稱, 數值, PR 或 None, 前十名次或 None]。"""
    return {'n': n, 's': s, 'v': v, 'd': d, 'rows': [list(r) for r in rows], 'foot': list(foot)}


# 提示卡 PR／名次人群（使用者 2026-11-01）：只排除場均上場不夠的人（看頁面 MPG 欄），不看總分鐘、不分老將新秀
POOL_MPG = 15
NO_RANK_FOOT = f'*上場時間不足（場均未滿 {POOL_MPG} 分鐘），不列名次'


GRAVITY_IMPUTED = {'ols': '沒有 NBA.com 引力資料：用三分出手、三分命中率、用球率與位置推估',
                   'card-ols': '沒有 NBA.com 引力資料：沿用 2025-26 卡的推估（三分出手、命中率、用球率與位置）',
                   'rookie-g0': '新秀還沒有引力資料：先用 2025 屆新秀的中位數'}


def gravity_tip(v, raw, src, pool_raw, inpool=True, note=''):
    """GRV 格子提示卡（0.2.10j）：原始無球外線引力分數（NBA.com，越高越不敢離開他）＋PR／前十名次；推估的人註明。
    src：'api'／'2025-26'／'2026-27'／'2025-26+2026-27'＝實際資料，'ols'／'card-ols'／'rookie-g0'＝推估。"""
    rows = []
    if raw is not None and src not in ('rookie-g0',):
        pr, rk = pr_rank(raw, pool_raw)
        rows.append(('引力分數' + ('（推估）' if src in GRAVITY_IMPUTED else ''), f'{raw:.1f}', pr, rk if inpool and src not in GRAVITY_IMPUTED else None))
    foot = ([GRAVITY_IMPUTED[src]] if src in GRAVITY_IMPUTED else []) + ([] if inpool else [NO_RANK_FOOT])
    return cell_tip('引力', 'GRV', round(v), rows, d='<b>沒拿球</b>時吸引防守貼防的程度', foot=foot)


def mpg_pool(mpg):
    """{key: 場均分鐘} → 名次人群（key 集合）。"""
    return {k for k, m in mpg.items() if m >= POOL_MPG}


def tov_rows(src, key, pool, poss_src=None):
    """{key: TO 提示細項}，pool 人數。0.2.12c：tovSkill 看每次觸球的失誤（失誤 ÷ 觸球次數、持球分鐘各半），
    提示卡列：失誤／場、持球分鐘／場（名次）、每百次觸球失誤（PR、名次）。持球分鐘、觸球次數＝NBA.com tracking Possessions 的 TIME_OF_POSS、TOUCHES
    （卡片頁＝2025-26 整季檔；新賽季頁＝data/defense-seventh/2026-27/possessions.json），key 欄（PLAYER_NAME／PLAYER_ID）和 src 同一種。
    沒有持球分鐘的人只列失誤／場。PR／名次對 pool（key 集合）裡的人；不在 pool 的人只標 PR，不標名次。"""
    rs = json.loads(Path(src).read_text(encoding='utf-8'))['data']['resultSets'][0]
    h = {k: i for i, k in enumerate(rs['headers'])}
    tot = {}
    for r in rs['rowSet']:
        t = tot.setdefault(r[h[key]], [0, 0])
        t[0] += r[h['TOV']] or 0
        t[1] += 1
    pm, tc = {}, {}
    if poss_src and Path(poss_src).exists():
        d = json.loads(Path(poss_src).read_text(encoding='utf-8'))
        d = d.get('data', d)['resultSets']
        ps = d[0] if isinstance(d, list) else d
        ph = {k: i for i, k in enumerate(ps['headers'])}
        for r in ps['rowSet']:
            pm[r[ph[key]]] = pm.get(r[ph[key]], 0.0) + float(r[ph['TIME_OF_POSS']] or 0)
            tc[r[ph[key]]] = tc.get(r[ph[key]], 0.0) + float(r[ph['TOUCHES']] or 0)
    st = {}
    for k, (tov, gp) in tot.items():
        m, c = pm.get(k, 0.0), tc.get(k, 0.0)
        st[k] = (100 * tov / c if m > 0 and c > 0 else None, m / gp if m > 0 else None, tov / gp, k in pool)
    pool = [v for v in st.values() if v[3] and v[0] is not None]
    out = {}
    for k, (rate, pg, tg, inpool) in st.items():
        rows = [('失誤', f'{tg:.1f}/場', None, None)]
        if rate is not None:
            pr, rk = pr_rank(rate, [v[0] for v in pool], low_good=True)
            _, rk_p = pr_rank(pg, [v[1] for v in pool])
            rows += [('持球分鐘', f'{pg:.1f}/場', None, rk_p if inpool else None),
                     ('每百次觸球失誤', f'{rate:.1f}', pr, rk if inpool else None)]
        out[k] = rows
    return out, len(pool)


THREE_MIN_3PA36 = 2.0   # 命中率 PR／名次只比 per36 出手 ≥ 2 的人（投 3 中 2 不排第一）


def three_rows(src, key, pool):
    """{key: 3PT 提示細項}：三分進球-出手、命中率、出手量（/36、/場），player-games.json 加總。
    出手量 PR／名次對 pool；命中率只對 pool 裡 per36 出手 ≥ THREE_MIN_3PA36 的人。"""
    rs = json.loads(Path(src).read_text(encoding='utf-8'))['data']['resultSets'][0]
    h = {k: i for i, k in enumerate(rs['headers'])}
    tot = {}
    for r in rs['rowSet']:
        t = tot.setdefault(r[h[key]], [0, 0, 0, 0])
        for i, c in enumerate(('MIN', 'FG3M', 'FG3A')):
            t[i] += r[h[c]] or 0
        t[3] += 1
    st = {k: (m / a if a else None, 36 * a / mn, gp, m, a, k in pool) for k, (mn, m, a, gp) in tot.items() if mn > 0}
    vol = [v[1] for v in st.values() if v[5]]
    acc = [v[0] for v in st.values() if v[5] and v[0] is not None and v[1] >= THREE_MIN_3PA36]
    out = {}
    for k, (pct, p36, gp, m, a, inpool) in st.items():
        pr_v, rk_v = pr_rank(p36, vol)
        ok = pct is not None and p36 >= THREE_MIN_3PA36
        pr_a, rk_a = pr_rank(pct, acc) if ok else (None, None)
        out[k] = [('命中率', f'{100 * pct:.1f}%' if pct is not None else '—', pr_a, rk_a if inpool else None),
                  ('出手量', f'{p36:.1f}/36', pr_v, rk_v if inpool else None),
                  ('場均進球-出手', f'{m / gp:.1f}-{a / gp:.1f}', None, None),
                  ('合計', f'{m}-{a}', None, None)]
    return out


def three_tip(v, sub, season, inpool=True):
    foot = [f'命中率名次只比每 36 分鐘出手 ≥ {THREE_MIN_3PA36:g} 的人'] + ([] if inpool else [NO_RANK_FOOT])
    return cell_tip('三分', '3PT', round(v), sub, d='<b>60%</b> 三分出手量 ＋ <b>40%</b> 三分命中率', foot=foot)


def apply_cell_tips(s):
    """格子改用浮動提示卡：p.tips 有該欄就帶 data-ck、不帶 title（要在 apply_common 之後套）。"""
    for a, b in [
        ('function cell(k, v, first) {', 'function cell(k, v, first, tip) {'),
        ("""return `<td class="${cls.join(' ')}" title="${v}">${g}</td>`;""",
         """return `<td class="${cls.join(' ')}"${tip ? ` data-ck="${tip}"` : ` title="${v}"`}>${g}</td>`;"""),
        ("""cls.push(gcls(grade(v))); return `<td class="${cls.join(' ')}">${v}</td>`; }""",
         """cls.push(gcls(grade(v))); return `<td class="${cls.join(' ')}"${tip ? ` data-ck="${tip}"` : ''}>${v}</td>`; }"""),
        ("cell(k, p[k], j === 0)", "cell(k, p[k], j === 0, p.tips && p.tips[k] ? k : null)"),
    ]:
        assert s.count(a) == 1, a
        s = s.replace(a, b)
    return s


def attr_tips(s, current):
    tips = {k: [n, en, d, [list(x) for x in rows], frz] for k, (n, en, d, rows, frz) in ATTR_TIPS.items()}
    const = (f"const ATIP = {json.dumps(tips, ensure_ascii=False, separators=(',', ':'))};\n"
             f"const FRZ = {'true' if current == 'inseason' else 'false'};\n")
    for a, b in [
        ('title="依${zh}排序">', '${ATIP[k] ? ` data-tip="${k}"` : ` title="依${zh}排序"`}>'),
        ('function head() {', const + 'function head() {'),
        ('<nav class="snav', TIP_CSS + TIP_JS + '<nav class="snav'),
    ]:
        assert s.count(a) == 1, a
        s = s.replace(a, b)
    return s


# 兩個頁面共用的樣板修補：數值模式的格子也要帶等第顏色（文字仍顯示數字）。
COMMON_REPLACEMENTS = [
    ("""  if (st.mode === 'num') return `<td class="${cls.join(' ')}">${v}</td>`;""",
     """  if (st.mode === 'num') { cls.push(gcls(grade(v))); return `<td class="${cls.join(' ')}">${v}</td>`; }"""),
    # tovSkill 是每次使用球權的失誤率，不是運球能力（使用者 2026-10-29：HDL 改成 TO）
    ("['tovSkill', 'HDL', '護球']", "['tovSkill', 'TO', '少失誤']"),
    # help 只量籃下 6 呎內命中差、只管禁區，實際是護框（使用者 2026-10-29）；欄位名 help 等 E-080 後再改
    ("['help', 'HELP', '協防']", "['help', 'RIM', '護框']"),
    # 體力現在是上場分鐘＋年齡，和分鐘欄重複，網站不顯示（R-057）；資料仍留著給 OVR 和引擎用
    (", ['stamina', 'STA', '體力']]", "]"),
    # 樣板原本是 artifact（外層代加 viewport），單獨放上 gh-pages 後手機會用 980px 排版再縮放，
    # 切換球員時資訊列行數一變就整頁重算縮放、看起來被拉長抖動（使用者 2026-10-29，Amen Thompson）
    ('<meta charset="utf-8">', '<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1">'),
    # 資訊列每一項整塊換行，不要把「防守加分 +1.77」斷在中間
    ('.facts b{', '.facts>span{white-space:nowrap}\n.facts b{'),
    # 選中列原本整列金底＋深色字（!important），能力值顏色全被蓋掉；hover 時底色又被蓋回深色，整列變黑（使用者 2026-10-29）。
    # 改成每格保留原本顏色，選中列整列提亮成藍灰（名字格仍是金色，見 enrich_roster_viewer）。
    # 不用半透明金底：金疊深藍會混成橄欖綠，使用者 2026-10-29 嫌髒、廉價，demo 比較後選藍灰（A）
    ('tbody tr.sel td{background:var(--gold);color:var(--gold-ink)!important}',
     'tbody tr.sel td:not(.nm){background:#253040}\n'
     'tbody tr.sel:hover td:not(.nm){background:#2b3748}'),
    # 背景改冷炭：拿掉右上角藍色光暈，底色降彩度（使用者 2026-10-29 嫌雜色，demo 七個炭灰方向選 F）。
    # 排序欄金色淡底疊深色也會偏橄欖綠，改中性淡白
    ('  --bg:#0f1622; --panel:#18222f; --panel-2:#1f2b3a; --line:#2c3a4c;',
     '  --bg:#0d1014; --panel:#151a20; --panel-2:#1c222a; --line:#29313b;'),
    ('background-image:radial-gradient(1200px 500px at 85% -10%,#22324a 0%,transparent 60%);', ''),
    ('thead th{background:#0b1119;', 'thead th{background:#0a0d10;'),
    # 版心 1280→1360（使用者 2026-11-02：表格 1252px 加內距超過 1248px 內框，左右可滑）
    ('.wrap{max-width:1280px;', '.wrap{max-width:1360px;'),
    ('td.sortcol{background:rgba(242,194,48,.07)}', 'td.sortcol{background:rgba(255,255,255,.035)}'),
    ('fill="#0b1119" stroke="#2c3a4c"', 'fill="#0a0d10" stroke="#29313b"'),
    # 排序箭頭脫離排版、掛在文字左邊：原本佔寬，換排序欄時整張表寬度會跳（使用者 2026-11-02）
    ('thead th.sorted::before{content:"▼";font-size:.6rem;margin-right:2px}',
     'thead th.sorted::before{content:"▼";font-size:.6rem;position:absolute;transform:translateX(calc(-100% - 2px))}'),
    # 頁尾只留等第與 OVR 簡述，點 ▼ 展開詳細算法（使用者 2026-11-01）
    ('    <span>點欄位標題排序，再點一次反向</span>\n    <span>點任一列看球員卡</span>\n', ''),
    ('    <span>OVR 同分多半是 2K27 名次封頂造成的</span>',
     '    <button type="button" class="ovr-t" aria-expanded="false" onclick="const b=this.nextElementSibling,o=b.hidden;b.hidden=!o;this.setAttribute(\'aria-expanded\',o)">'
     'OVR：綜合<b>場上能力 ＋ 防守意識 ＋ 上場時間</b>的每場比賽影響力 <i>▼</i></button>\n'
     '    <div class="ovr-how" hidden>'
     '<div><span class="oh-t">1. 場上能力（14 項）</span>結合傳統數據、逐球紀錄與官方追蹤，不只看帳面產量，也區分<b>自主創造 vs 吃餅</b>、<b>無球牽制（引力）</b>、<b>持球保護</b>與<b>對位主將／護框降命中率</b>，拆成 14 項單項能力（頂尖可破 99）。</div>'
     '<div><span class="oh-t">2. 防守意識（DIQ）</span>抄截與阻攻只佔防守一小部分。DIQ 計算扣除隊友與對手強弱後，在場能幫球隊<b>少丟幾分</b>（跨季防守 RAPM 比同位置平均），補齊數據抓不到的<b>無球輪轉、站位與協防</b>。</div>'
     '<div><span class="oh-t">3. 上場時間與用人</span>結合<b>場均分鐘</b>與<b>出賽率</b>（區分正常輪休與被棄用 DNP）。同效率下，<b>能扛越多上場時間，單場價值越高</b>（邊際遞減）。</div>'
     '<div><span class="oh-t">4. 怎麼合成 OVR</span>將上述三項對齊進階指標（DARKO、BPM）校準權重，衡量<b>每場能幫球隊多贏幾分</b>；球員卡右側另列<b>實際在場影響</b>與<b>單場評分</b>供對照。全站<b>隨比賽逐場更新</b>並反映近期狀態（新秀以選秀順位為起點）。</div>'
     '</div>'),
] + [
    # 上場篩選拿掉（手機太擠，門檻也還是整季總分鐘），換成球隊篩選：仿 arammeta 的彈出格子（使用者 2026-10-29）
    ('''    <span class="lbl">上場</span>
    <div class="seg" id="minSeg"></div>''',
     '''    <span class="tgrp"><span class="lbl">球隊</span>
    <details class="tpick" id="teamPick"><summary aria-label="選擇球隊"></summary><div class="tpop"><div class="tgrid" id="teamGrid"></div></div></details></span>'''),
    ("pos: 'ALL', min: 0,", "pos: 'ALL', team: 'ALL', rk: false,"),
    ('p.min >= st.min', "(st.team === 'ALL' || p.team.split('/').pop() === st.team) && (!st.rk || ROOKIES.has(p.name))"),
    # 兩個 builder 已先把門檻改成場均 10／20／30 分鐘
    ("  seg('minSeg', [[0, '全部'], [10, '≥10'], [20, '≥20'], [30, '≥30']], 'min');\n", '  teamPick();\n'),
    ('放寬位置或上場分鐘試試', '放寬位置或球隊試試'),
    # 表格自己捲（使用者 2026-10-29：看低排名時頭像卡仍在畫面上）。高度＝卡片下方剩餘視窗，只在載入／縮放時算，
    # 點球員不改高度；換排序、篩選、頁才捲回頂。手機篩選移到卡片上方後卡片放得下，也照卡片下方剩餘高度算；
    # 手機表格捲動不傳給頁面、不回彈（使用者 2026-10-29：拖表格有時整頁一起動，捲到頂再拉會露出一大片空白）。
    ('.tbox{overflow-x:auto;', '.tbox{overflow:auto;max-height:70vh;overscroll-behavior:contain;'),
    # top:-1px：border-collapse 的半像素邊框會在表頭上緣留一條縫，捲過的列從縫裡露出來
    ('@media (prefers-reduced-motion', '''#tbl thead{position:sticky;top:-1px;z-index:3}
@media (max-width:640px){.tbox{overscroll-behavior:auto}}
@media (prefers-reduced-motion'''),
    ('  card(P.find(p => p.name === st.sel) || P[0]);', '''  const lk = [st.sort, st.asc, st.pos, st.team, st.rk, st.q, st.page].join('|');
  if (lk !== listKey) { listKey = lk; document.querySelector('.tbox').scrollTop = 0; }
  tboxEdges();
  card(P.find(p => p.name === st.sel) || P[0]);'''),
    ("document.getElementById('q').oninput", '''let listKey = '';
function fitTable() {
  // 手機以「卡片頂端貼齊視窗頂」為準：卡片＋篩選列以下的空間都給表格。
  // 桌機有固定眉頭（2026-11-02），改以頁面頂端為準：不捲頁面就看得到表格底，20 人在表格裡捲完（使用者 2026-11-02）
  // 近 N 場展開不壓縮表格（使用者 2026-11-04）：量位置時暫時收起，高度照收起時算，展開只把表格往下推
  const t = document.querySelector('.tbox'), g = document.querySelector('.card .g5'), gOpen = g && !g.hidden;
  if (gOpen) g.hidden = true;
  const tt = t.getBoundingClientRect().top;
  const above = innerWidth <= 640 ? tt - document.getElementById('card').getBoundingClientRect().top : tt + scrollY;
  if (gOpen) g.hidden = false;
  const h = Math.max(innerWidth <= 640 ? 240 : 300, innerHeight - above - 12);
  t.style.maxHeight = Math.round(h) + 'px';
  tboxEdges();
}
// 捲過表頭才浮出陰影；下面還有列時底部淡出
function tboxEdges() {
  const t = document.querySelector('.tbox');
  t.classList.toggle('scrolled', t.scrollTop > 0);
  t.classList.toggle('below', t.scrollTop + t.clientHeight < t.scrollHeight - 2);
}
document.querySelector('.tbox').addEventListener('scroll', tboxEdges, { passive: true });
// 手機：同一次滑動把表格捲到頂／底時不接著帶動整頁（iOS 會接著捲）；放開後「下一次」滑動若一開始就在頂／底，才讓整頁捲（使用者 2026-11-02）
(function () {
  const t = document.querySelector('.tbox');
  let y0 = 0, x0 = 0, startTop = false, startBot = false;
  const edges = () => [t.scrollTop <= 0, t.scrollTop + t.clientHeight >= t.scrollHeight - 1];
  t.addEventListener('touchstart', e => {
    y0 = e.touches[0].clientY; x0 = e.touches[0].clientX;
    [startTop, startBot] = edges();
  }, { passive: true });
  t.addEventListener('touchmove', e => {
    if (innerWidth > 640 || t.classList.contains('grow') || !e.cancelable) return;
    const dy = e.touches[0].clientY - y0, dx = e.touches[0].clientX - x0;
    if (Math.abs(dx) > Math.abs(dy)) return;
    const [top, bot] = edges();
    // 這次滑動開始時已在頂／底且往外拉 → 放行給整頁
    if ((dy > 0 && startTop) || (dy < 0 && startBot)) return;
    if ((dy > 0 && top) || (dy < 0 && bot)) e.preventDefault();
  }, { passive: false });
})();
addEventListener('resize', fitTable);
addEventListener('load', fitTable);
document.fonts && document.fonts.ready.then(fitTable);
// 欄寬照「全部球員」量一次就鎖住（table-layout:fixed）：自動排版會照這頁的內容算欄寬，
// 換排序換到 7'4"、三位數三分的人，整張表寬度就跟著跳（使用者 2026-11-02）
// 寬度鎖成欄寬總和（不是 min-width）：不然表格會跟著外框撐寬，外框又照表格寬算，越撐越寬。
// 只動這幾個屬性、量時除掉 zoom：桌機縮放（enrich_roster_viewer）寫在同一個 style 上。
function lockCols() {
  const t = document.getElementById('tbl'), SZ = SIZE, s = t.style, z = parseFloat(s.zoom) || 1, tm = [st.team, st.rk];
  t.querySelector('colgroup')?.remove();
  s.tableLayout = ''; s.width = 'min-content'; s.minWidth = '0';
  // 網址直接開某隊（/nets）時也照全部球隊量
  st.team = 'ALL'; st.rk = false; SIZE = 1e5; render(); SIZE = SZ; [st.team, st.rk] = tm;
  const ws = [...t.querySelectorAll('thead tr:last-child th')].filter(th => getComputedStyle(th).display !== 'none')
    .map(th => Math.ceil(th.getBoundingClientRect().width / z));
  t.insertAdjacentHTML('afterbegin', '<colgroup>' + ws.map(w => `<col style="width:${w}px">`).join('') + '</colgroup>');
  s.tableLayout = 'fixed'; s.width = ws.reduce((a, b) => a + b, 0) + 'px';
  render();
}
// 不在每次 resize 重鎖（使用者 2026-11-03：Ctrl+- 時整張先膨脹再收回、很卡＝拆掉欄寬重畫全部球員）。
// 瀏覽器縮放時 CSS 欄寬不變；只有跨手機／桌機分界（欄位顯示不同）才要重量。
matchMedia('(max-width:640px)').addEventListener('change', lockCols);
(document.fonts ? document.fonts.ready : Promise.resolve()).then(lockCols);

document.getElementById('q').oninput'''),
    # 手機卡片：右欄只放 OVR 會把左欄擠成一長條。改成名字＋資訊列在左、OVR 在右上，
    # 長處標籤與真實數據佔滿整寬（使用者 2026-10-29，Jokić）
    ('@media (prefers-reduced-motion', '''@media (max-width:640px){
  .card{grid-template-columns:1fr auto;gap:8px 10px;padding:12px 14px;align-items:start}
  .card .who{display:contents}
  .card .who>*{grid-column:1/-1}
  .card .who>.nm{grid-column:1;grid-row:1}
  .card .who>.facts{grid-column:1;grid-row:2;gap:2px 14px}
  .card .ring{grid-column:2;grid-row:1/3;padding:0;align-self:start}
}
@media (prefers-reduced-motion'''),
    # 表格捲軸（使用者 2026-10-29 要美化）：細、跟面板同色系、滑過才變亮。標準屬性 scrollbar-width／color
    # 給 Firefox、Chrome 121+、Safari 18.2+；不支援的舊 WebKit 才用 ::-webkit-scrollbar（Chrome 有標準屬性時會忽略它）。
    # 捲動提示照 Lea Verou／Roman Komarov 的捲動陰影：表頭捲過才有陰影、底部還有內容時淡出。
    # 儲存格有底色，背景漸層那招會被蓋掉，所以用 sticky 偽元素疊在上面。
    ('@media (prefers-reduced-motion', '''.tbox{scrollbar-width:thin;scrollbar-color:#38424f transparent}
.tbox:hover{scrollbar-color:#56616f transparent}
@supports not (scrollbar-color:auto){
  .tbox::-webkit-scrollbar{width:10px;height:10px}
  .tbox::-webkit-scrollbar-track,.tbox::-webkit-scrollbar-corner{background:transparent}
  .tbox::-webkit-scrollbar-thumb{background:#38424f;border-radius:10px;border:3px solid var(--panel)}
  .tbox:hover::-webkit-scrollbar-thumb{background:#56616f}
}
#tbl thead tr:last-child th{transition:box-shadow .15s}
.tbox.scrolled #tbl thead tr:last-child th{box-shadow:0 9px 10px -7px rgba(0,0,0,.75)}
.tbox::after{content:"";position:sticky;left:0;bottom:0;z-index:4;display:block;height:36px;margin-top:-36px;
  background:linear-gradient(rgba(21,26,32,0),var(--panel));pointer-events:none;opacity:0;transition:opacity .15s}
.tbox.below::after{opacity:1}
@media (prefers-reduced-motion'''),
    # 顯示切換直接用範例當標籤（使用者 2026-10-29）
    ("seg('modeSeg', [['grade', '等第'], ['num', '數值']], 'mode');", "seg('modeSeg', [['grade', 'A+'], ['num', '99']], 'mode');"),
    # A+／99 是網站設定：選了就存在瀏覽器（localStorage，同網域兩個賽季頁共用），切換賽季頁不變（使用者 2026-10-30）
    ("mode: 'grade',", "mode: (() => { try { return localStorage.getItem('bbac.mode') === 'num' ? 'num' : 'grade'; } catch (e) { return 'grade'; } })(),"),
    ("b.onclick = () => { st[key] = v;",
     "b.onclick = () => { st[key] = v; if (key === 'mode') try { localStorage.setItem('bbac.mode', v); } catch (e) {}"),
    ('function render() {', '''function setTeam(cur) {
  st.rk = cur === 'ROOKIE'; st.team = st.rk ? 'ALL' : cur; st.page = 0; st.extra = 0;
  // 記住上次選的球隊／新秀：在其他檢視點眉頭「球隊」時回到這隊（site_header）
  if (cur !== 'ALL') {
    document.getElementById('teamPick').dataset.last = cur;
    try { localStorage.setItem('bbac.lastTeam', cur); } catch (e) {}
  }
  // 選隊後球員卡顯示該隊（或新秀）依目前排序欄位排第一的人：預設排序＝OVR 最高（使用者 2026-11-03）
  if (st.rk || st.team !== 'ALL') {
    const top = list()[0];
    if (top) st.sel = top.name;
  }
}

function teamPick() {
  const d = document.getElementById('teamPick'), grid = document.getElementById('teamGrid');
  const logo = t => `<img alt="" src="https://cdn.nba.com/logos/nba/${TEAM_IDS[t]}/global/D/logo.svg" onerror="this.style.visibility='hidden'">`;
  if (!grid.childElementCount) {
    const teams = [...new Set(P.map(p => p.team.split('/').pop()))].filter(t => TEAM_IDS[t]).sort();
    // 新秀放在球隊面板裡、跟「全部球隊」並排（使用者 2026-10-30）；2027 頁沒有新秀時「全部球隊」佔整排
    grid.innerHTML = `<button type="button" class="all${ROOKIES.size ? ' half' : ''}" data-t="ALL">全部球隊</button>` +
      (ROOKIES.size ? '<button type="button" class="all half" data-t="ROOKIE">新秀</button>' : '') +
      teams.map(t => `<button type="button" data-t="${t}" title="${t}">${logo(t)}<span>${t}</span></button>`).join('');
    grid.onclick = e => {
      const b = e.target.closest('button[data-t]');
      if (!b) return;
      setTeam(b.dataset.t); d.open = false;
      render();
    };
    try {
      const l = localStorage.getItem('bbac.lastTeam');  // 兩個賽季頁共用；這頁沒有的（2027 頁的新秀）不用
      if (l && grid.querySelector(`[data-t="${CSS.escape(l)}"]`) && l !== 'ALL') d.dataset.last = l;
    } catch (e) {}
    // 面板靠左展開，超出螢幕右緣就往左推
    d.addEventListener('toggle', () => {
      if (!d.open) return;
      const pop = d.querySelector('.tpop');
      pop.style.left = '0';
      const over = pop.getBoundingClientRect().right - (document.documentElement.clientWidth - 12);
      if (over > 0) pop.style.left = -over + 'px';
    });
    document.addEventListener('click', e => { if (d.open && !d.contains(e.target)) d.open = false; });
    d.addEventListener('keydown', e => { if (e.key === 'Escape') { d.open = false; d.querySelector('summary').focus(); } });
  }
  const cur = st.rk ? 'ROOKIE' : st.team;
  // 回到全部球員時按鈕仍顯示上次選的球隊（不反白），存在瀏覽器裡下次開頁也記得（使用者 2026-11-04）
  const last = cur === 'ALL' && d.dataset.last, shown = last || cur;
  d.querySelector('summary').innerHTML = shown === 'ALL' ? '全部' : shown === 'ROOKIE' ? '新秀' : logo(shown) + shown;
  d.classList.toggle('on', cur !== 'ALL');
  d.classList.toggle('last', !!last);
  grid.querySelectorAll('button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.t === cur)));
}

function render() {'''),
    ('@media (prefers-reduced-motion', '''.tgrp{display:flex;gap:10px;align-items:center}
.tpick{position:relative}
.tpick summary{list-style:none;display:flex;align-items:center;gap:6px;background:var(--panel);color:var(--muted);border:1px solid var(--line);border-radius:3px;font:600 .9rem var(--f-disp);letter-spacing:.04em;padding:6px 11px;cursor:pointer;user-select:none}
.tpick summary::-webkit-details-marker{display:none}
.tpick summary::after{content:"▾";font-size:.8em;opacity:.8}
.tpick summary:focus-visible{outline:2px solid var(--gold);outline-offset:1px}
.tpick.on summary{background:var(--gold);color:var(--gold-ink);border-color:var(--gold)}
.tpick summary img{width:18px;height:18px;object-fit:contain;margin:-2px 0}
.tpop{position:absolute;left:0;top:calc(100% + 6px);z-index:20;width:min(360px,calc(100vw - 24px));background:var(--panel-2);border:1px solid var(--line);border-radius:6px;padding:10px;box-shadow:0 12px 32px rgba(0,0,0,.55)}
.tgrid{display:grid;grid-template-columns:repeat(6,1fr);gap:6px}
.tgrid button{display:flex;flex-direction:column;align-items:center;gap:2px;background:var(--panel);border:1px solid var(--line);border-radius:4px;padding:5px 2px 3px;cursor:pointer;color:var(--muted);font:600 .72rem var(--f-disp);letter-spacing:.04em}
.tgrid button img{width:30px;height:30px;object-fit:contain}
.tgrid button.all{grid-column:1/-1;font-size:.9rem;padding:7px}
.tgrid button.all.half{grid-column:span 3}
.tgrid button:hover{border-color:var(--muted);color:var(--fg)}
.tgrid button[aria-pressed="true"]{border-color:var(--gold);color:var(--gold-ink);background:var(--gold)}
@media (prefers-reduced-motion'''),
]


def apply_common(s):
    for a, b in COMMON_REPLACEMENTS:
        assert s.count(a) == 1, a
        s = s.replace(a, b)
    return _off_def_columns(_defense_iq_column(_compact_facts(s)))


# 進攻／防守分（使用者 2026-11-01）：把 OVR 迴歸第一層 pred0 拆開。pred0 在同位置內對能力值是線性的，
# 係數從正式卡 ranking.csv 照位置重擬合（R²＝1）；新秀 G／F 用 SG／SF 的係數（同 defense_centered 的 DPOS）。
# 分數＝每 36 分鐘比聯盟平均（正式卡 MIN ≥ 500）多幾分；防守另加 defenseBonus（扣同一群人的平均）。
# 籃板、身高兩邊都不算（約佔 OVR 差異一成三）。OVR 還有用人層（分鐘、出賽率），所以兩分相加不等於 OVR。
# 進攻再混進影響力（使用者 2026-11-01，同 OVR align 的比例）：T6（DARKO＋BPM）pooledPoss ≥ 5000 的人
# 進攻＝0.75×能力值進攻＋0.25×（0.75×pooledO 減同一群 MIN ≥ 500 的平均）；不夠回合的人只用能力值。
OD_CARD = Path(__file__).resolve().parents[1] / 'reports/card-0.2.12c/ranking.csv'  # 0.2.12c：tovSkill 失誤率分母改觸球次數，全部係數重擬合；0.2.12b：窗口 328→246 格；0.2.12：tovSkill 改看持球時間，全部係數重擬合；0.2.10j：加 gravity（無球外線引力），全部係數重擬合；0.2.10i：drive→drive_D、creation→creationJ（OFF 提示貢獻欄跟著換）
OD_OFF = ['long', 'mid', 'short', 'ft', 'drive', 'gravity', 'foulDraw', 'tovSkill', 'pass', 'creation']   # gravity：0.2.10j（每 10 點約 +0.19 per36）
OD_DEF = ['onBall', 'help', 'pressure']
OD_ALL = OD_OFF + OD_DEF + ['rebound', 'heightInches']
OD_IMP_W, OD_IMP_POSS = 0.25, 5000   # 同卡片 align 的權重與門檻


def off_def(rows, key, card_path=OD_CARD):
    """{rows[key]: (進攻分, 防守分)}；pred0 用卡片係數算回來差超過 0.02 的人給 (None, None)，回 (dict, 對不上人數)。card_path＝係數來源卡（新賽季頁用預設 0.2.10e，正式卡頁傳自己的卡）。"""
    import csv
    import numpy as np
    card = list(csv.DictReader(Path(card_path).open(encoding='utf-8')))
    if card and 'gravity' not in card[0]:   # 0.2.10j：卡片 ranking.csv 沒有 gravity 欄（與 E-198 KG 逐位元相同），從同資料夾 gravity-attr.csv 依姓名補
        ga = {g['name']: g['gravity'] for g in csv.DictReader((Path(card_path).parent / 'gravity-attr.csv').open(encoding='utf-8'))}
        for r in card:
            r['gravity'] = ga[r['name']]
        rows = [dict(r, gravity=ga.get(r['name'], '')) if 'gravity' not in r else r for r in rows]
    coef = {}
    for ps in {r['pos'] for r in card}:
        g = [r for r in card if r['pos'] == ps]
        X = np.c_[np.ones(len(g)), [[float(r[a]) for a in OD_ALL] for r in g]]
        coef[ps] = np.linalg.lstsq(X, np.array([float(r['pred0']) for r in g]), rcond=None)[0]
    q = [r for r in card if float(r['MIN']) >= 500]
    mu = np.array([sum(float(r[a]) for r in q) / len(q) for a in OD_ALL])
    dbm = sum(float(r['defenseBonus']) for r in q) / len(q)
    n_off, n_def = len(OD_OFF), len(OD_DEF)
    t6 = list(csv.DictReader((Path(card_path).parent / 'rapm-T6.csv').open(encoding='utf-8')))
    t6 = {k: 0.75 * float(t['pooledO']) for t in t6 if float(t['pooledPoss']) >= OD_IMP_POSS for k in (t['name'], t['playerId'])}
    t6m = [t6[r['name']] for r in q if r['name'] in t6]
    t6m = sum(t6m) / len(t6m)
    out, bad = {}, 0
    for r in rows:
        b = coef.get({'G': 'SG', 'F': 'SF'}.get(r['pos'], r['pos']))
        if b is None or any(r[a] == '' for a in OD_ALL + ['pred0', 'defenseBonus']):
            out[r[key]] = (None, None)
            bad += 1
            continue
        x = np.array([float(r[a]) for a in OD_ALL])
        if abs(b[0] + b[1:] @ x - float(r['pred0'])) > 0.02:
            out[r[key]] = (None, None)
            bad += 1
            continue
        c = b[1:] * (x - mu)
        o, imp = float(c[:n_off].sum()), t6.get(str(r.get('playerId', '')), t6.get(r.get('name')))
        if imp is not None:
            o = (1 - OD_IMP_W) * o + OD_IMP_W * (imp - t6m)
        out[r[key]] = (round(o, 2),
                       round(float(c[n_off:n_off + n_def].sum()) + float(r['defenseBonus']) - dbm, 2))
    return out, bad


# 表格 OVR 右邊加 OFF／DEF 兩欄（單位是每 36 分鐘淨分，不換等第，直接顯示 +x.x）
OD_TD = ("const odc = (p, k) => { const v = p[k]; return `<td class=\"${v == null ? '' : v >= 2 ? 'gA' : v >= 1 ? 'gB' : v >= 0 ? 'gC' : ''}"
         "${st.sort === k ? ' sortcol' : ''}\"${v != null && v >= 0 ? '' : ' style=\"color:var(--muted)\"'}>"
         "${v == null ? '—' : (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v).toFixed(1)}</td>`; };\n")


def _off_def_columns(s):
    # 原本的表頭空格與 OVR 格子字串要保留（enrich_roster_viewer.inject 之後還要找它們），新欄接在後面
    for a, b in [
        ('<tr class="grp"><th colspan="6"></th>', '<tr class="grp"><th colspan="6"></th><th colspan="2"></th>'),
        ("th('ovr', 'OVR', '總評');", "th('ovr', 'OVR', '總評') + th('off', 'OFF', '進攻') + th('def', 'DEF', '防守');"),
        ('function cell(k, v, first', OD_TD + 'function cell(k, v, first'),
        ("<td class=\"ovr${sc('ovr')}\">${p.ovr.toFixed(1)}</td>",
         "<td class=\"ovr${sc('ovr')}\">${p.ovr.toFixed(1)}</td>${odc(p, 'off')}${odc(p, 'def')}"),
    ]:
        assert s.count(a) == 1, a
        s = s.replace(a, b)
    s, n = re.subn(r'colspan="(\d+)" class="empty"', lambda m: f'colspan="{int(m.group(1)) + 2}" class="empty"', s)
    assert n == 1
    return s


# 重分組（使用者 2026-10-30「採用並重分組」，R-084）：PHYS 不顯示（E-131 後 OVR 也不用）；REB、TO、PRES 併成「球權」
# （搶回球權／不丟球權／逼對手丟球權）；DIQ 改接在 RIM 後面，防守組＝PER D、RIM、DIQ。
# 新賽季頁原本照舊；使用者 2026-10-31 要兩頁屬性一致，新賽季頁也套用（inseason 0.2.7d 起 OVR 也不用 physique）
REGROUP = [
    ("['pass', 'PASS', '傳球'], ['tovSkill', 'TO', '少失誤'], ['creation', 'CRT', '自主創造']]],",
     "['pass', 'PASS', '傳球'], ['creation', 'CRT', '自主創造']]],"),
    ("['身體', [['rebound', 'REB', '籃板'], ['physique', 'PHYS', '身體']]],",
     "['球權', [['rebound', 'REB', '籃板'], ['tovSkill', 'TO', '少失誤'], ['pressure', 'PRES', '壓迫']]],"),
    ("['help', 'RIM', '護框'], ['pressure', 'PRES', '壓迫']]],", "['help', 'RIM', '護框']]],"),
    ("if (k === 'pressure') h += th('dbon', 'DIQ', '防守意識');", "if (k === 'help') h += th('dbon', 'DIQ', '防守意識');"),
    # 切入不放主畫面（使用者 2026-11-02「切入既然是負分 那就不要列在主畫面了」；0.2.10i 係數每 10 點 −0.03）；仍算進 OFF／OVR
    # 0.2.10j（R-134／R-135）：原本切入的位置改放引力（進攻組第一欄、製造犯規前面）
    ("['drive', 'DRV', '切入'], ['foulDraw', 'FD', '製造犯規']", "['gravity', 'GRV', '引力'], ['foulDraw', 'FD', '製造犯規']"),
]


def regroup_attrs(s):
    for a, b in REGROUP:
        assert s.count(a) == 1, a
        s = s.replace(a, b)
    return s   # 0.2.10j：切入換成引力，欄數不變（0.2.10i 拿掉切入時的空列 colspan −1 一起撤掉）


# 防守意識是能力值，放表格防守組 PRES 右邊（使用者 2026-10-30），不放卡片資訊列（那列桌機整列藏掉）。
# 單位是防守 RAPM 分（不是 0–99），所以不換等第、直接顯示 +x.xx；0 顯示「—」。不進 ATTR，免得卡片前三／最弱排序被它佔掉。
DIQ_TD = ("const diq = p => `<td data-nodec class=\"${p.dbon >= 2 ? 'gA' : p.dbon >= 1 ? 'gB' : p.dbon > 0 ? 'gC' : ''}"
          "${st.sort === 'dbon' ? ' sortcol' : ''}\"${p.dbon > 0 ? '' : ' style=\"color:var(--muted)\"'}"
          " title=\"防守意識：真實比賽防守 RAPM 和同位置平均的差（負＝低於平均），補能力值量不到的輪轉、站位、補位；只有正的部分會加進 OVR\">"
          "${p.dbon == null ? '—' : (p.dbon > 0 ? '+' : p.dbon < 0 ? '−' : '') + Math.abs(p.dbon).toFixed(2)}</td>`;\n")


def defense_centered(rows, key, candidates, taper=()):
    """DIQ 欄顯示負分（使用者 2026-10-30）：centered＝0.75·D − posMeanD(pos)，possW ≥ 2500 才有值（同 run_c4_live.m27_ul_bonus）。
    taper＝走卡鏈的新秀 key（run_c4_live_rookie.chain_rookie，2026-10-31）：加成是 max(0, centered)·min(1, possW/2500)、
    possW > 0 就有值，顯示也乘同一個係數（正的部分＝實際加進 OVR 的量）。
    candidates＝[(def-L 檔, posMeanD 或 None)]；None 就從 defenseBonus > 0 的人反推 posMeanD＝median(0.75·D − bonus)
    （pipeline 平均的人群和 ranking.csv 不完全一樣，從 rows 重算會差一點）；該位置沒人有正加成才照 m27_ul_bonus 用 MIN 加權平均。
    第一個讓每個人 max(0, centered) 都等於 ranking.csv defenseBonus（±0.002）的候選勝出，回 {rows[key]: centered 或 None}；
    都對不上（例如 def-L-live.csv 已被隔天重擬合覆寫）回 None，頁面退回只顯示正值。"""
    import csv
    taper = set(taper)
    pos = lambda r: {'G': 'SG', 'F': 'SF'}.get(r['pos'], r['pos'])   # 新秀 G／F／C 照 run_c4_live_rookie.DPOS 查 posMeanD
    for path, pos_mean in candidates:
        if not path.exists():
            continue
        src = {r[key]: r for r in csv.DictReader(path.open(encoding='utf-8'))}
        d = {r[key]: (float(src[r[key]]['D']), float(src[r[key]]['poss'])) for r in rows if r[key] in src}
        mean = dict(pos_mean or {})
        for ps in {pos(r) for r in rows} - set(mean):
            back = sorted(0.75 * d[r[key]][0] - float(r['defenseBonus']) for r in rows
                          if pos(r) == ps and r[key] in d and r[key] not in taper and float(r['defenseBonus']) > 0)
            if back:
                mean[ps] = back[len(back) // 2]
                continue
            idx = [r for r in rows if pos(r) == ps and r[key] in d and d[r[key]][1] >= 500]
            w = sum(float(r['MIN']) for r in idx)
            mean[ps] = sum(float(r['MIN']) * 0.75 * d[r[key]][0] for r in idx) / w if w else 0.0
        out = {r[key]: (0.75 * d[r[key]][0] - mean[pos(r)]) * min(1.0, d[r[key]][1] / 2500) if r[key] in taper
               and r[key] in d and d[r[key]][1] > 0 else 0.75 * d[r[key]][0] - mean[pos(r)]
               if r[key] in d and d[r[key]][1] >= 2500 else None for r in rows}
        if all(abs(max(0.0, out[r[key]] or 0.0) - float(r['defenseBonus'])) <= 0.002 for r in rows):
            return out
    return None


def _defense_iq_column(s):
    for a, b in [
        ('colspan="${x[1].length}">${x[0]}</th>', 'colspan="${x[1].length + (x[0] === \'防守\' ? 1 : 0)}">${x[0]}</th>'),
        ("h += th(k, en, zh, i === 0 ? 'gl' : ''); });",
         "h += th(k, en, zh, i === 0 ? 'gl' : ''); if (k === 'pressure') h += th('dbon', 'DIQ', '防守意識'); });"),
        ('function cell(k, v, first', DIQ_TD + 'function cell(k, v, first'),
        (".join('')).join('')}\n      <td class=\"sub gl${sc('min')}\">",
         ".join('')).join('')}${diq(p)}\n      <td class=\"sub gl${sc('min')}\">"),
    ]:
        assert s.count(a) == 1, a
        s = s.replace(a, b)
    s, n = re.subn(r'colspan="(\d+)" class="empty"', lambda m: f'colspan="{int(m.group(1)) + 1}" class="empty"', s)
    assert n == 1
    return s


# 球員卡資訊列（使用者 2026-10-29：字太多；模擬每 36 分鐘淨值和下方 RAPM「淨影響」看起來同一件事卻不同數字）。
# 模擬值拿掉、改放 OVR 圓環的滑鼠提示；手機藏掉「球隊／身高」這類標籤；新賽季頁較開季差值用綠／灰／紅三色（不漸變）。
# 每格帶 class；手機版只留較開季（箭頭），身高移到隊色橫幅（使用者 2026-10-29：手機用減法）
FACT_LABELS = {'球隊 ': 'f-tm', '身高 ': 'f-ht', '場均 ': 'f-min', '已打 N=': 'f-gp', '出賽 ': 'f-gp'}
DELTA_OLD = "<span>開季卡 OVR <b>${p.last.toFixed(1)}</b>（<b>${(p.dovr > 0 ? '+' : '') + p.dovr.toFixed(2)}</b>）</span>"
# 手機版（.sm）只顯示箭頭＋絕對值，例如紅色 ▼4.3（使用者 2026-10-29）；桌機（.lb）照舊帶正負號
DELTA_NEW = ("<span class=\"f-d\" title=\"較開季卡 OVR ${p.last.toFixed(1)}\"><i class=\"lb\">開季卡 OVR <b>${p.last.toFixed(1)}</b>（</i>"
             "<b class=\"${p.dovr >= 1 ? 'up' : p.dovr <= -1 ? 'dn' : 'flat'}\">"
             "<i class=\"sm\">${p.dovr >= 0.05 ? '▲' : p.dovr <= -0.05 ? '▼' : '＝'}</i>"
             "<i class=\"lb\">${(p.dovr > 0 ? '+' : '') + p.dovr.toFixed(1)}</i>"
             "<i class=\"sm\">${Math.abs(p.dovr).toFixed(1)}</i></b>"
             "<i class=\"lb\">）</i></span>")
# 桌機卡片（使用者 2026-10-29）：身高寫在名字旁；第一排不放球隊，改成分鐘、場次、得分／籃板／助攻；
# 較開季比照手機掛在 OVR 圓環下（箭頭＋絕對值）；下方真實數據只留細項小字（版面在 enrich_roster_viewer.CSS）
NAME_OLD = '<div class="nm"><span class="first">${esc(first)}</span>${esc(last)}</div>'
NAME_NEW = '<div class="nm"><span class="first">${esc(first)}</span>${esc(last)}<span class="nht">${ht(p.ht)}</span></div>'
BIG3 = ("${(r => r && r.gp ? [['得分', r.pts], ['籃板', r.reb], ['助攻', r.ast]]"
        ".map(([l, v]) => `<span class=\"f-b\">${l} <b>${v.toFixed(1)}</b></span>`).join('') : '')(REAL[p.name])}")
RING_END = 'class="val">${p.ovr.toFixed(1)}</text></svg></div>'
RING_DELTA = ("class=\"val\">${p.ovr.toFixed(1)}</text></svg>"
              "<b class=\"rd ${p.dovr >= 1 ? 'up' : p.dovr <= -1 ? 'dn' : 'flat'}\" title=\"較開季卡 OVR ${p.last.toFixed(1)}\">"
              "${p.dovr >= 0.05 ? '▲' : p.dovr <= -0.05 ? '▼' : '＝'}${Math.abs(p.dovr).toFixed(1)}</b></div>")


def _compact_facts(s):
    s, n = re.subn(r'\n\s*<span>(?:新賽季預測|模擬)每 36 分鐘淨值 <b>\$\{p\.imp[^\n]*</span>', '', s)
    assert n == 1
    ring = '<div class="ring"><svg'
    assert s.count(ring) == 1
    s = s.replace(ring, '<div class="ring" title="模型用能力值模擬的每 36 分鐘淨值 ${(p.imp > 0 ? \'+\' : \'\') + p.imp.toFixed(2)}'
                        '（OVR 由此換算；下方「影響」是真實比賽的 RAPM，兩者不同）"><svg')
    # 圓環滿格＝當季最高 OVR（使用者 2026-10-29）；原本固定 99，OVR 破百的人全都滿圈
    fill = '(p.ovr - 40) / (99 - 40)'
    assert s.count(fill) == 1
    s = s.replace(fill, '(p.ovr - 40) / (OVR_TOP - 40)')
    top = 'const P = DATA.rows.map(r => Object.fromEntries(COLS.map((c, i) => [c, r[i]])));'
    assert s.count(top) == 1
    s = s.replace(top, top + '\nconst OVR_TOP = Math.max(...P.map(p => p.ovr));')
    for lab, c in FACT_LABELS.items():
        s = s.replace(f'<span>{lab}<b>', f'<span class="{c}"><i class="lb">{lab}</i><b>')
    # 防守加分改叫防守意識（使用者 2026-10-30）：真實防守 RAPM 高於同位置平均的部分，補能力值量不到的輪轉、站位
    s = s.replace('<span>防守加分 <b>', '<span class="f-x" title="真實比賽的防守影響力高於同位置平均的部分（防守 RAPM），'
                  '補能力值量不到的輪轉、站位、補位；只有正值，會加進 OVR">防守意識 <b>')
    assert s.count(NAME_OLD) == 1
    s = s.replace(NAME_OLD, NAME_NEW)
    s, n = re.subn(r'(<span class="f-gp">.*?</span>)', lambda m: m.group(1) + BIG3, s, count=1)
    assert n == 1
    assert s.count(DELTA_OLD) <= 1
    if DELTA_OLD in s:
        assert s.count(RING_END) == 1
        s = s.replace(RING_END, RING_DELTA)
    return s.replace(DELTA_OLD, DELTA_NEW)
