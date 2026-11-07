# card／inseason 0.2.12 spec：TO 改用持球時間上線（R-139，E-203）

用 role-card skill。cwd `D:\Projects\CODING\basketball-autochess`。使用者 2026-11-02 看完 E-202 結果說「直接採用」（R-139）：不先送 role-audit、不再回測，直接上線兩頁。

## 要做什麼
在目前正式版（`reports/ovr-inseason-2026-27/live/CURRENT.json`：card 0.2.11／inseason 0.2.11，檔名沿用 0210j，R-137；**開工先讀它的 note 全文，照裡面的換版規矩做**）之上，只換 `tovSkill` 定義，其他不變，全部係數重擬合（不設下限）。新定義＝E-202 預註冊 §1（`reports/card-0.2.10j+E202-to-possession/preregistration.md`）＋子代理實作時的詮釋（同目錄 `report.md` 末段「與預註冊不同或自行詮釋之處」），照抄，不另改。

### 卡片端（2025-26）
- 直接採用 E-202 KT 臂的建法與產物：`reports/card-0.2.10j+E202-to-possession/`（`tov_raw.py`、`e202_common.py`、`build_kg.py`、`run_i.py`、`finalize.py`；`work/KT/final/out/ranking.csv` sha 29ca32eb…）。正式版放 `reports/card-0.2.12/`（build 腳本仿 `reports/card-0.2.10j/build_0210j.py`），重建結果須與 KT final ranking.csv 逐位元組相同。
- 依 CURRENT note 重取凡是依卡片池重算的東西（用人層 usage、先驗 prior、OVR 映射錨點、3PT 池等）；照 L-109 重跑 `reports/E121-rookie-scale/build_2k_start.py` 重解新秀 δ。

### 賽中端（2026-27）
- 每日抓 NBA.com tracking `leaguedashptstats`，`PtMeasureType=Possessions`、`PerMode=Totals`、本季整季（參數照 `reports/handle-E069/fetch-tracking.mjs`；寫法照 `scripts/fetch_gravity.mjs`，新檔 `scripts/fetch_possessions.mjs`）→ `data/defense-seventh/2026-27/possessions.json`。`daily_inseason_update.py` 加 `step_fetch_possessions()`，仿 `step_fetch_gravity`：失敗不擋發布、沿用上次的檔、記 log。
- 賽中 `tovSkill`：分子沿用 window8 的逐場權重失誤；持球分鐘＝過去季 TIME_OF_POSS（handle-E069 raw）與本季（possessions.json）各季 TOP ×（該人該季窗口權重分鐘 ÷ 該季分鐘），和卡片同一式。收縮、z 的池與平均標準差、0–99 映射一律凍結成卡片端的值（仿 gravity 的 `gravity-pool-card0210j.json` 凍結池，新檔例如 `tov-pool-card0212.json`）。沒有任何持球資料的人（含本季還沒抓到的新秀）照預註冊 §1 第 6 點。
- 開關：環境變數 `TOV_POSS=0` 重現 0.2.11（卡片與賽中 ranking.csv 逐位元組相同）。

### 版號
**PATCH 0.2.12**（card／inseason）：E-202 前 100 名移動 ≥10 名 34 人 > R-109 的 25 人。檔名、資料夾用 0212。

### 網站
- `scripts/season_nav.py` ATTR_TIPS 的 `tovSkill` 說明改成：每<b>持球分鐘</b>的失誤少、且<b>持球時間</b>長（各半）；不持球的人失誤少不算數。
- `tov_rows`（TO 格子提示）改成顯示：失誤／場、持球分鐘／場（池內名次）、每持球分鐘失誤（PR、名次）。卡片頁用 2025-26 tracking，新賽季頁用本季 possessions.json。函式說明同步改。
- OFF 提示貢獻欄（`OD_OFF`）的 tovSkill 依新係數。
- PATCH_NOTES 新開 0.2.12 一格，照檔內撰寫要旨，例如「TO 改成看持球時間：持球多又少丟球才高分（Brunson ○→1、Hauser 1→○）。｜…」，名次照實際結果填，其餘收進 hover。
- 重建卡片頁與新賽季頁。

## 限制
- 共用 checkout：別的 session 對 `scripts/season_nav.py`、`scripts/build_card_viewer.py`、`scripts/build_inseason_viewer.py`、`memory/*`、`TODO.md` 有**未 commit 或已 stage 未 commit 的改動**。不要覆蓋或 commit 它們：commit 時只放自己的改動（以 `git show HEAD:<檔>` 為底套用自己的修改 → `git hash-object -w` → 用**暫時的 GIT_INDEX_FILE** 組 tree，`git commit-tree`＋`git update-ref`，不要動共用 index 裡別人 stage 的東西；工作樹也套用同樣修改，保留別人的改動）。建頁面若要排除別人未 commit 的內容，照 `reports/card-0.2.10i/progress.md` #6 暫換 commit 版、建完還原。不要 `git add -A`（L-047）。開工先 `git pull`，push 前再 pull。
- `reports/` 被 gitignore，新檔用 `git add -f`。
- 子程序 `creationflags=subprocess.CREATE_NO_WINDOW`、`stdin=DEVNULL`；長指令 `</dev/null` 加 timeout；超過約 2 分鐘用背景。重算超過本機輕量改到 5090（`ssh kojiek@100.97.181.15`）。
- 不改 `src/` 模擬。不碰金鑰。每完成一步在 `reports/card-0.2.12/progress.md` 追加一行。

## 驗收（全過才發布）
- c0：`TOV_POSS=0` 時卡片與賽中 ranking.csv 與 0.2.11 逐位元組相同。
- 卡片新版與 E-202 KT final 逐位元組相同。
- `npm test` 全過（含 live_current_gate、rookie_start_gate）；新版自檢腳本（仿 `check_inseason_0210j.py`）。
- CURRENT.json 更新（note 開頭寫 0.2.12 段）、舊版建構腳本與凍結檔照規矩 git mv 到 `_retired/`。
- commit、push 後立刻發 gh-pages（`python -I scripts/daily_inseason_update.py` 完整流程），curl 確認線上兩頁版號 0.2.12、TO 提示有持球分鐘。
- 每日排程只是 daily 腳本多一步，不新增排程；若改到排程動作，照 `C:\Users\柯子捷\.claude\CLAUDE.md` 更新 registry.json 並跑 `audit.ps1` 要 FAIL=0。
- memory：experiments 的 E-203 狀態改完成並寫結果一行；handoff「目前基準」加 0.2.12 一行、把 E-202 那行移掉。R-139 lead 已寫。只放自己的段落。

## 回報（最後訊息）
CLAUDE.md 六段（第一行 `# 總評`）。直觀證據：兩頁各一張表，0.2.11→0.2.12 的 TO、TO 名次、OVR 名次：前 10 名＋Brunson、Cade、Harden、Luka、Jokić、Hauser、Hardaway Jr.、Kornet、Jarrett Allen；前 100 名移動 ≥10 名人數；線上網址與版號；commit hash。
