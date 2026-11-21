# 名單頁精簡檢視：合併能力值（spec）

2026-11-10，lead 定案。對象：trueovr.com 名單頁（2026-27 首頁與 `2025-26.html` 兩頁）。
只改顯示：`ranking.csv`、OVR、模擬用值、OFF／DEF 的算法一律不動。

## 0. 起點

工作樹裡已有上一輪未 commit 的篩選欄（`scripts/season_nav.py`、`scripts/site_header.py`：`.fbar`、`viewSeg`、`applyView()`、`LITE`、`lockCols()` 量兩種檢視）。**在它上面接著改，不要還原、不要重寫**。上一輪的截圖腳本 `reports/_fbar_tmp/shot.mjs` 可以照抄改用。

## 1. 欄位定義（10 個合併能力值，兩種檢視共用一套）

分兩層。第一層 4 個「大類」，第二層 6 個「細類」。現有每個能力值欄剛好歸到一個細類或大類，不重複。

| 層 | key | 表頭（英／中） | 組成（都用頁面上的最終顯示值） |
|---|---|---|---|
| 大類 | `offR` | OFF／進攻 | 現有 `off`（每 36 分鐘淨分）換尺，見 §2.2 |
| 大類 | `defR` | DEF／防守 | 現有 `def`（每 36 分鐘淨分）換尺，見 §2.2 |
| 大類 | `play` | PLAY／組織 | 0.70 `pass` ＋ 0.30 `tovSkill` |
| 大類 | `rebound` | REB／籃板 | 原欄，不變 |
| 細類（進攻） | `outside` | OUT／外線 | 0.55 `threeValue` ＋ 0.25 `mid` ＋ 0.20 `ft` |
| 細類（進攻） | `inside` | IN／內線 | 0.60 `short` ＋ 0.40 `foulDraw` |
| 細類（進攻） | `handle` | BALL／持球 | `creation`（0.2.15 起已是自主創造＋擋拆持球合成），原值 |
| 細類（進攻） | `offball` | OFFB／無球 | 0.40 `gravity` ＋ 0.30 `spot` ＋ 0.30 `cutroll` |
| 細類（防守） | `perim` | PER／外防 | 0.60 `onBall` ＋ 0.40 `pressure`（頁面顯示的那個壓迫值） |
| 細類（防守） | `help` | RIM／內防 | 原欄（含 D30 蓋帽），不變；中文表頭在兩種檢視都維持「護框」→ 精簡檢視的群組標題寫「內防」即可 |

不進任何合併值：`drive`（使用者 2026-11-02 裁定不上主畫面）、`dbon`（DIQ，已在 `def` 裡）、`physique`、`stamina`。

## 2. 合併算法（放新檔 `scripts/lite_cells.py`，純函式，Python 在建頁時算好寫進 DATA）

名次人群 pool＝場均 ≥ `season_nav.POOL_MPG`（15 分鐘）的人，跟提示卡 PR 同一群。

### 2.1 加權合併（`play`、`outside`、`inside`、`offball`、`perim`）
1. `raw = Σ w_i·v_i / Σ w_i`，缺值（None／沒有那一欄，例如 2025-26 頁沒有 `spot`／`cutroll`）的成分跳過、權重照剩下的重新歸一；全部缺 → None（顯示「—」）。
2. 還原分散度（平均會把分數往中間擠，頂尖的人到不了 99）：`m`＝pool 的 raw 平均，`s`＝pool 的 raw 標準差，`t`＝成分各自 pool 標準差的加權平均，`f = min(1.35, t/s)`；`value = m + (raw − m)·f`。
3. 下限 40，上限不設（可以超過 99，跟現有欄一樣）。存一位小數，顯示四捨五入成整數；等第模式（A+…F）照現有 `grade()`。

### 2.2 OFF／DEF 換尺（`offR`、`defR`）
`value = 70 + 10·(x − pool平均)/pool標準差`，下限 40、不設上限；`x` 是 None → None。現況大約：進攻 +5.6 → 107、−3.3 → 47；防守 +4.5 → 110。
兩種檢視的 OFF／DEF 欄都改顯示這個 40–99+ 值（配色、等第走一般能力值的 `cell()`），原本的「+4.8」淨分移到提示卡第一列。排序結果不變（單調）。原本的 `off`／`def` 欄位留在 DATA 裡不刪。

### 2.3 計算時機
必須在所有成分都已是最終顯示值之後（`display_rows` 換尺、FT 覆蓋、RIM D30 `rim_blk_live`、`presDisplay`、SPOT／CUT `offball_cells` 都做完）才算。兩頁（`build_inseason_viewer.py`、`build_card_viewer.py`）都要接上。

### 2.4 自檢
`python scripts/lite_cells.py --selftest` 要 exit 0，至少檢查：缺成分時權重重新歸一；全缺回 None；下限 40；`f` 上限 1.35；單一成分時 value＝原值；OFF 換尺單調。

## 3. 提示卡（滑鼠移上去／手機長按 450ms，沿用 `TIP_JS`、`cell_tip()`）

每個合併格子都要有 `p.tips[key]`，表頭要有 `ATTR_TIPS[key]`（寫給一般球迷看的一句話＋組成比例）。格子卡的列＝**先列成分分數，再列重要的個人原始數據**，總共最多 8 列。原始數據從成分既有的 `tips[k].rows` 用列名挑（值、PR、名次照抄），挑不到就跳過、不報錯：

| key | 成分列 | 接著挑的原始數據列（依序，取到 8 列為止） |
|---|---|---|
| `outside` | 三分、中距離、罰球 | 三分「命中率」、三分「出手量」、中距離「命中率」、中距離「出手量」、罰球「命中率」 |
| `inside` | 近框、製造犯規 | 近框「命中率」、近框「出手量」、「罰球量」、「罰球率」、「禁區觸球／36」 |
| `handle` | （單一成分，不列） | `creation` 卡的列照搬前 7 列（含自主出手、擋拆持球占比或擋拆回合／每回合得分、孤立占比） |
| `offball` | 引力、空檔射手、切入順下 | 「引力分數」、`spot` 卡前 2 列、`cutroll` 卡前 2 列 |
| `play` | 傳球、少失誤 | 「助攻量」、「助攻率」、「潛在助攻／36」、「每百次觸球失誤」、「失誤」 |
| `perim` | 單防、壓迫 | `onBall` 卡前 2 列、「抄截」、「干擾球」、「犯規」 |
| `offR` | 外線、內線、持球、無球、組織（各自的合併值） | 第一列放「每 36 分鐘淨分」＝原 `off`（帶正負號一位小數） |
| `defR` | 外防、內防、防守意識（DIQ，照現有格式） | 第一列放「每 36 分鐘淨分」＝原 `def` |
| `rebound`、`help` | 沿用現有提示卡 | — |

同一個列名在不同成分卡都有時（命中率、出手量），合併卡上要加前綴成「三分命中率」「中距離出手量」這樣，不能出現兩列同名。成分卡的註腳（foot）不搬，合併卡最多一行註腳。
詳細檢視裡原有欄位的提示卡完全不動。

## 4. 排版

### 4.1 精簡檢視（桌機、手機同一套欄位）
欄序：`#`｜球員｜位置｜球隊｜**OVR**｜OFF 進攻｜DEF 防守｜PLAY 組織｜REB 籃板‖OUT 外線｜IN 內線｜BALL 持球｜OFFB 無球‖PER 外防｜RIM 內防‖MPG
- 群組標題列（`tr.grp`）在精簡檢視也顯示：OVR 右邊四欄「大類」、接著四欄「進攻」、兩欄「防守」。‖ 處用現有的 `gl` 分隔線。
- 桌機：16 欄全部一次看到，不出現橫向捲軸；表格總寬維持跟詳細檢視一樣（上一輪 `lockCols()` 已處理，多出的寬度平均分給數字欄，不要全塞給球員欄）。
- 手機（390 寬）：`#`、球員、OVR 維持凍結；位置／球隊照現有手機規則隱藏；**不捲動的第一屏剛好是 OVR＋四個大類**，往右滑才是六個細類與 MPG。四個大類欄等寬。
- 身高、N、ΔOVR、FORM、DIQ 與所有原始能力值欄在精簡檢視隱藏。

### 4.2 詳細檢視
欄序：`#`｜球員｜位置｜球隊｜身高｜OVR｜OFF｜DEF‖外線[3PT MID FT]‖內線[INS FD]‖持球[CRT]‖無球[GRV SPOT CUT]‖組織[PASS TO]‖籃板[REB]‖外防[PER D PRES]‖內防[RIM DIQ]‖出場[MPG N ΔOVR FORM]
- 只是把現有欄位照 §1 的分類重排、換群組標題；每一欄的值、表頭字、提示卡都不變（除了 OFF／DEF 換成 §2.2 的尺）。合併值欄（PLAY、OUT、IN、BALL、OFFB、PER）在詳細檢視不出現。
- 改動點主要是 `REGROUP`／`GROUPS` 與 `head()` 的群組列 colspan、DIQ 接在 RIM 後、空列 colspan；每個字串取代都保留 `assert count == 1`。

### 4.3 預設與篩選欄
- 沒有 `localStorage['bbac.view']` 時：寬度 ≤ 640 預設精簡，其他預設詳細。使用者選過就照存的。
- 年份按鈕字樣改成「2026-27」「2025-26」（現在是 2027／2026）。
- 眉頭設定（齒輪）面板加一列「賽季」放兩個連結，讓「戰力排行」「賽程」檢視也能切賽季（上一輪把眉頭的賽季切換拿掉了）。篩選欄裡那組照舊。
- 排序：點合併值欄表頭照該值排序；切換檢視時若目前排序欄在新檢視看不到，退回 OVR 由高到低。
- 球員卡（上方大卡）的前三強項／最弱項 chip 照舊用原始能力值，不改。

## 5. 不要做
- 不碰 `memory/`、`src/`、`reports/E305-rim-blk/`、`ranking.csv` 產生鏈的數值。
- 不 commit、不 push、不發布（**不准跑 `daily_inseason_update.py --shell` 或任何會推 gh-pages 的指令**）；頁面只建到本機暫存目錄看。
- 不新增排程。headless Chrome／子程序不能閃黑窗（`windowsHide: true`、`CREATE_NO_WINDOW`）。
- 不順手重構 `season_nav.py`／`enrich_roster_viewer.py` 其他部分；增量修改。

## 6. 驗收（子 session 要附證據）
1. `python scripts/lite_cells.py --selftest` exit 0；`npm test` 結果（若只有 `test_records_match_gamelog` 因賽程資料被別的 session 改而失敗，照實寫，不要去修它）。
2. 兩頁都建得出來、console 無錯誤。
3. 截圖放 `reports/roster-lite-view/shots/`（原尺寸、不裁切）：桌機 1440×900 與手機 390×844 各拍：精簡、精簡往右捲到底（手機）、詳細、一張合併格子提示卡（`outside`）、一張 `handle` 提示卡、2025-26 頁精簡。
4. `reports/roster-lite-view/check.md`：列出 2026-27 頁 OVR 前 15 名與另外 5 個代表球員（Curry、Jokić、Wembanyama、Gobert、一名射手型替補）的 10 個合併值；每個合併欄 pool 的平均／標準差／最小／最大／≥99 的人數；用腳本斷言 Curry 的 `outside` 提示卡裡有「三分命中率」「三分出手量」、任一主力控衛的 `handle` 卡裡有含「擋拆」的列。
5. 手機精簡第一屏：用腳本量 `#tbl` 可視區右緣，確認 OVR＋四個大類欄完整落在 390 內、第五個數字欄（OUT）不在第一屏或只露一半以內。

## 7. 回報格式
一般收工說明即可（不是實驗）：改了哪些檔、每條驗收的結果與證據路徑、沒做到或有疑慮的地方、你覺得權重／尺度看起來怪的球員例子。
