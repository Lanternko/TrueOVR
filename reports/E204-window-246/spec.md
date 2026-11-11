# E-204 spec（role-card）：遺忘窗口 W246 上線（R-140）

用 role-card skill。cwd `D:\Projects\CODING\basketball-autochess`。不是新假設檢定，是上線；E-201 已驗過。

## 開工前提（不成立就停下回報，不要動手）
- E-203（card／inseason 0.2.12，新 TO）已上線：`reports/ovr-inseason-2026-27/live/CURRENT.json` 的 inseason／card 都是 0.2.12，且 git log 有 0.2.12 上線 commit。工作樹沒有別的 session 對 `live/`、`scripts/`、`reports/card-0.2.12/` 的未 commit 改動（`git status`）。

## 要做什麼
1. **以 0.2.12 為底**，把所有四季窗口的 WIN 由 328 改為 246（逐場線性形狀、每人正規化與下限、係數、錨點、r_repl 都不動；MPG 窗口本來就一季，不動）。改哪些地方照 `reports/E201-steeper-forgetting/phase0.md` 的盤點表（E-201 的 `work/e201_run.py` 是做法參考），現在的 0.2.12 程式碼若有新增讀 WIN 的地方也要一起改。用一個開關（例如 `WIN_LEN=328`）可重現 0.2.12。
2. **兩頁都換**：新賽季頁（live 管線）與 2025-26 卡片頁（卡片 build）。lastOVR 基準照 R-112 用同一個 WIN。
3. **版號**照 rulings R-064／R-109：前 20 名換 ≤2、前 100 名移動 ≥10 名 ≤25 人 → 字母版 0.2.12a；否則 PATCH 0.2.13（原預留給 T6 的版號再順延）。寫 `reports/card-<版號>/`（或 E204 目錄）放 cmp 結果；`CURRENT.json`、OFFICIAL_CARD、`build_card_viewer.py`、`season_nav.py` 版本指向照 0.2.12 上線時的做法（看 `git show` 0.2.12 上線 commit 改了哪些檔照做）。
4. **新秀起點重解**：換版後跑 `reports/E121-rookie-scale/build_2k_start.py`，`test/rookie_start_gate.py` 要過。
5. **網站**：更新說明加一段（白話：新賽季本季比賽的權重加快；四季窗口改三季；季末四項檢查中薪水略降，使用者 R-140 接受）。窗口說明文字在 `season_nav.py` 的 `ATTR_TIPS`／更新說明裡若寫「四季」要一起改。
6. **線上路線護欄補驗**（E-201 限制：護欄 B 走卡片路線）：用新版 2025-26 卡片算季末 OVR 對 RAPM、EPM、2K、薪水四項 ρ，和 0.2.12 比，只報告。
7. 發布：`python -I scripts/daily_inseason_update.py --shell`（記憶：名單頁改動 push 後立刻發 gh-pages）。

## 限制
- 不改 E-201 目錄、預註冊。不碰別的 session 的未 commit 改動。
- 可以 commit 與 push（使用者已裁定採用上線，R-140）；commit 只含本次改動，訊息寫 E-204／R-140。
- 子程序一律 `creationflags=subprocess.CREATE_NO_WINDOW`、`stdin=DEVNULL`；長指令加 timeout；不能閃黑窗。

## 驗收
- `npm test` 全過（含 live_current_gate、rookie_start_gate）。
- `WIN_LEN=328` 重現 0.2.12 兩頁 ranking（差 <0.05）。
- 新版老將 |ΔOVR| 分布與 E-201 W246 臂同方向（中位數 > 0.2.12）。
- 網站已發布，gh-pages commit hash 寫進回報。

## 回報
照 CLAUDE.md 六段（第一行 `# 總評`）。直觀證據放前 12 名 0.2.12→新版的 OVR、ΔOVR，以及前 20 名進出、季末四項 ρ 比較（白話）。收工更新 `memory/experiments.md` E-204 狀態、`handoff.md` 目前基準一條（只改自己的條目，L-047）。
