# card／inseason 0.2.10j spec：無球引力上線（R-134、R-135）

用 role-card skill。cwd `D:\Projects\CODING\basketball-autochess`。使用者 2026-11-02 已核准兩頁都上線（「兩頁都上」）；E-198 A 線不過，但使用者裁定結果可接受（R-135：空間長人下降是對的）。不再做回測。

## 要做什麼
在目前正式版（`reports/ovr-inseason-2026-27/live/CURRENT.json`：card 0.2.10i／inseason 0.2.10i；開工先讀它的 note 全文，照裡面的換版規矩做）之上，加一個能力值 `gravity`，其他定義不變，**全部係數重擬合，不設下限**。

### 卡片端（2025-26）
- 直接採用 E-198 KG 的建法與產物：`reports/card-0.2.10j+E198-gravity/`（`gravity_raw.py`、`build_kg.py`、`calibrate_wing_t.py`、`run_i.py`、`finalize.py`；`work/KG-final/out/ranking.csv` sha 4519d615…）。正式版放 `reports/card-0.2.10j/`，重建結果須與 KG-final ranking.csv 逐位元組相同。
- 依 CURRENT note 重取凡是依卡片池重算的東西（用人層、OVR 映射錨點、3PT 池等；照 L-109 重跑 `reports/E121-rookie-scale/build_2k_start.py` 重解新秀 δ）。

### 賽中端（2026-27）
- 每日抓 NBA.com `stats.nba.com/stats/gravityleaders?LeagueID=00&Season=2026-27&SeasonType=Regular+Season`（headers 同 `reports/F126-shot-difficulty/gravity-split/fetch_gravity_split.mjs`；curl 會被擋，node fetch 可以；python 若要呼叫 node 帶 `CREATE_NO_WINDOW`）。存到 live 資料夾，抓失敗就沿用上次成功的檔、記 log，不讓每日流程失敗。
- 賽中 `gravity` 原始值：2025-26 與 2026-27 的 `AVGOFFBALLPERIMETERGRAVITYSCORE` 依 `FRAMES` 加權混合，套現行四季窗口的季權重（只用有資料的季，權重重新正規化）。兩季都缺的人（含新秀）用 E-198 同一套 OLS 補值（3PA/36、3P%、USG%、位置），用本季可得資料擬合。池與 `to_attribute` 照 creation。
- 開關：環境變數 `GRAVITY=0` 重現 0.2.10i（卡片與賽中 ranking.csv 逐位元組相同）。

### 版號
照 R-109 判字母版或升版（前 20 名進出、前 100 名移動 ≥10 名人數）；暫定 card 0.2.10j／inseason 0.2.10j。

### 網站
- 引力欄放在原本切入的位置（進攻組第一欄，製造犯規前）：`scripts/season_nav.py` REGROUP 裡「切入不放主畫面」那條，改成把 `['drive', 'DRV', '切入']` 換成 `['gravity', 'GRV', '引力']`；`build_card_viewer.py`、`build_inseason_viewer.py` 的資料欄清單加 `gravity`；empty-row colspan 跟著對。
- ATTR_TIPS 加 `'gravity': ('引力', 'GRV', '<b>沒拿球</b>時防守人也不敢離開他的程度（NBA.com 無球外線引力）', [], None)`；格子提示若有細項就顯示原始引力值與是否為推估。
- OFF 提示的貢獻欄（`OD_OFF`）加 gravity，依新係數。
- PATCH_NOTES 的 0.2.10 格加一條，照檔內撰寫要旨：例如「加引力能力值：沒拿球時防守人也不敢離開的射手加分（Klay ○ → ○ 名）。｜…」，名次照實際結果填，其餘收進 hover。
- 頁面說明列（`<div class="src">`）照現行寫法補一句引力。
- 重建卡片頁與新賽季頁。

## 限制
- 共用 checkout：另一個 session 對 `scripts/season_nav.py`、`TODO.md`、`memory/rulings.md` 等有**未 commit 的改動**。不要覆蓋或 commit 它們：commit 時只 stage 自己的改動（以 `git show HEAD:<檔>` 為底套用自己的修改 → `git hash-object -w` → `git update-index --cacheinfo`；工作樹也要套用同樣修改，保留別人的改動）。建頁面時若要排除別人未 commit 的內容，照 0.2.10i 的做法暫換成 commit 版，建完還原（`reports/card-0.2.10i/progress.md` #6）。不要 `git add -A`（L-047）。開工先 `git pull`，push 前再 pull。
- `reports/` 被 gitignore，新檔用 `git add -f`。
- 子程序 `creationflags=subprocess.CREATE_NO_WINDOW`、`stdin=DEVNULL`；長指令 `</dev/null` 加 timeout；超過約 2 分鐘的指令用背景執行。重算若超過本機輕量改到 5090（`ssh kojiek@100.97.181.15`）。
- 不改 `src/` 模擬。不碰金鑰。每完成一步在 `reports/card-0.2.10j/progress.md` 追加一行，方便中斷後接手。

## 驗收（全過才發布）
- c0：`GRAVITY=0` 時卡片 ranking.csv 與 `reports/card-0.2.10i/ranking.csv`、賽中輸出與 0.2.10i 逐位元組相同。
- 卡片新版與 E-198 KG-final 逐位元組相同。
- `npm test` 全過（含 live_current_gate、rookie_start_gate）；新版自檢腳本（仿 `check_inseason_0210i.py`）。
- CURRENT.json 更新、舊版建構腳本與凍結檔照規矩 git mv 到 `_retired/`。
- commit、push 後立刻發 gh-pages（`python -I scripts/daily_inseason_update.py`，完整流程），curl 確認線上兩頁有 GRV 欄、版號已變。
- 每日排程：`scripts/daily_inseason_update.py` 會自動抓引力；若有新增排程或改到排程動作，照 `C:\Users\柯子捷\.claude\CLAUDE.md` 更新 `C:\Users\柯子捷\automations\registry.json` 並跑 `audit.ps1` 要 FAIL=0。
- memory：experiments 追加 E-199（完成）、handoff 一行；rulings 不用新增（R-134、R-135 lead 已寫）。只 stage 自己的段落。

## 回報（最後訊息）
CLAUDE.md 六段（第一行 `# 總評`）。直觀證據：前 25 名與 Klay、Curry、Hield、Kennard、Robinson、Hauser、Turner、Horford 的 0.2.10i→新版名次、OVR、gravity（兩頁各一張）；前 100 名移動 ≥10 名人數；線上網址與版號。
