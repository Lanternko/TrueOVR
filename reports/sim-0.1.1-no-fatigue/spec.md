# sim 0.1.1 規格：從模擬引擎刪掉體力機制（patch）

- 日期：2026-10-30；使用者裁定「既然關掉體力不會變差，依奧坎剃刀刪了」「做成 patch，得分偏多以後再修」
- 依據：E-117（`reports/sim-0.1.0+E117-fatigue-off/report.md`）：關體力球隊賽季 MAE 3.20→3.32（雜訊內），主版 WinImp Spearman 0.91
- 性質：程式刪減，不是調參。**新引擎必須和舊引擎 `fatigue:false` 逐位元相同**，這是唯一的正確性標準
- 角色：App 內 Sonnet 子代理（role-model）在 git worktree 實作；lead 驗收後合回主 checkout

## 1. 要刪的

- `src/` 中所有體力機制：`energy` 狀態陣列、場上消耗／板凳恢復、每節 +0.12 恢復、`applyStamina`、`fatigueRate`、`STAMINA_MIN_EFF`／`STAMINA_MAX_EFF`、`simulation_engine.js` 的 `fatigue` 參數與只為 fatigue 存在的分支（`!fatigue` 時的快取變成無條件）。
- heuristic 換人分數 `ability*(0.55+0.45*s.energy[i])`：energy 恆為 1，化簡成等價式。化簡後若 c0 不逐位元相同，就保留 `ability*(0.55+0.45*1)` 這種寫法直到相同，不要為了好看犧牲逐位元。
- `src/source_rotation_energy.js` 與 `test/source_rotation_energy.js`：先 grep 誰在用；只被體力機制或研究腳本用就刪，正式路徑有用到就留並在回報說明。
- 選項驗證：`fatigue` 不再是選項。傳 `fatigue:false` 接受並忽略（相容舊腳本）；傳 `fatigue:true` 直接 throw `fatigue removed in sim 0.1.1`，避免舊腳本默默跑出不同東西。
- `reports/player-impact-v29/benchmark.mjs` 的 `options()`（正式 WinImp 鏈）：拿掉 `fatigue:true`。
- 測試：只測體力效果的測試刪掉；其他測試裡傳 `fatigue:false` 的參數可以留。

## 2. 不刪、不動

- 球員資料的 `stamina` 屬性（卡片 OVR 迴歸仍用它）、`data/`、卡片、網站、`scripts/build_*`。
- `src/defense_fourth_game.js` 主 checkout 有別的 session 未 commit 的 E-122 改動（`defenderClockBeta`、`defenderFoulBeta`）。你在 worktree 裡看不到它；合併由 lead 處理，你不要去主 checkout 改 src。
- 得分偏高（關體力後模擬場均 119.1，真實 115.5）：使用者說以後再修，這次不碰任何其他參數。
- `reports/` 下舊實驗的腳本與複製出來的引擎（sandbox、engine-dump）不改。

## 3. 驗收

| 代號 | 內容 |
|---|---|
| g1 | `npm test` 全過 |
| c0 | 舊引擎（worktree 起點 HEAD，`fatigue:false`）vs 新引擎：budget 模式 60 場＋heuristic 模式 60 場（照 E-109／E-112 c0 的場次與 seed 選法）逐場事件雜湊相同；`simulation_engine.js` 用 `fatigue:false` 的呼叫者（`strength_benchmark`、`per36_report`）各 20 場逐位元相同 |
| c1 | E-117 p0 那場（seed 20261028、Jokić、對手 0）新引擎比分 108-122 |
| c2 | E-117 `rr-off.jsonl` 抽前 30 場重跑逐場相同 |
| c3 | E-065 指定 10 人的 WinImp（同 E-117 g0 的 harness，改用新引擎、不傳 fatigue），winsPer82 和 `reports/sim-0.1.0+E117-fatigue-off/winimp-off.csv` 逐值相同（g0 在 E-117 本機跑過，太慢就上 5090：`ssh kojiek@100.97.181.15`，Tailscale） |
| d1 | `grep -rnE "energy|applyStamina|fatigueRate|STAMINA_(MIN|MAX)" src/` 只剩你說明過的保留項 |

任何一項不過：停下回報，不要硬改到過。

## 4. 產出（`reports/sim-0.1.1-no-fatigue/`）

`gates.json`（g1、c0–c3、d1 結果與雜湊）、`engine.diff`（`git diff` 起點..你的改動，含 src、test、benchmark.mjs）、`run-meta.json`（起點 commit、node 版本、耗時、偏離）、驗收腳本。不寫 .md（report 由 lead 寫）。不 commit、不 push。
