# 總評

**4/5 大致達成 有部分退步**：體力機制已從引擎刪掉，新引擎和舊引擎 `fatigue:false` 逐位元相同。退步是一條舊的 memoized 研究引擎鏈（v14–v41）不能再跑。

- 日期：2026-10-30；sim 0.1.0 → **0.1.1**（R-088）
- 執行：App 內 Sonnet 子代理（role-model），在 worktree `.claude/worktrees/agent-ab18991181a92d44a`（分支 `worktree-agent-ab18991181a92d44a`，起點 7a2d0b0）實作與驗收；lead 獨立核對 c0、c3
- 規格：`spec.md`（sha256 0e962aeb…df9d5）

**這次目標**

把體力機制從模擬引擎刪乾淨，結果和舊引擎關體力時完全相同。

**進步了什麼**

- 刪掉的部分：
  - 8 個比賽引擎裡的體力消耗與恢復、每節恢復
  - `applyStamina`、`fatigueRate`
  - `STAMINA_MIN_EFF`／`MAX_EFF`
  - `simulation_engine.js` 的 `fatigue` 參數
  - `src/source_rotation_energy.js` 和它的測試
- 正式 WinImp harness（`player-impact-v29/benchmark.mjs`）拿掉 `fatigue:true`。
- 傳 `fatigue:true` 會直接報錯；傳 `false` 照常接受並忽略。
- 逐位元相同：
  - 120 場比賽事件雜湊相同。
  - `strength_benchmark`、`per36_report` 各 20 場相同。
  - E-117 單場（Jokić，108-122）相同。
  - 30 場循環賽相同。
  - 10 名球員 WinImp 和 E-117 關體力版逐值相同，例如 Jokić 17.126、SGA 14.136、Wembanyama 15.759。
- `npm test` 52 項通過。

**退步了什麼**

- 舊研究引擎 v14–v41 的 `memoized:true` 路徑會報 `Impact source anchor drift`：它用字串補丁，錨點正好是被刪掉的那行。
  - 會受影響的是 `player-impact-v1…v26` 的 OVR workers、`ovr-2025-26-latest`／`positional`、`wemby-robinson-cade` 診斷，最後一次改動都在 2026-10-16 以前。
  - 正式 WinImp 走非 memoized 路徑，不受影響（c3 已驗證）。
- 標籤字串 `energy-target-minutes-position-heuristic` 和結果欄 `fatigue:false` 保留：改名會讓每場雜湊變掉，就無法證明和舊引擎相同。
- 測試檔的固定雜湊和 11 筆 fixture 已換成舊引擎關體力的值。
- 得分偏高（場均 119.1，真實 115.5）沒處理，照使用者裁定列 TODO。

**直觀證據**

| 關卡 | 結果 |
|---|---|
| `npm test` | 52 項過 |
| 比賽事件 120 場 | 新舊雜湊 `604439d5…ddfe412a` 相同（lead 比對檔案逐位元相同） |
| E-117 單場 | 108-122 相同 |
| 循環賽 30 場 | 0 筆不同 |
| 10 人 WinImp | 和 `winimp-off.csv` 最大差 5×10⁻⁶（csv 只存 5 位小數） |

**要你決定的事**

1. approve sim 0.1.1，並合回主 checkout。主 checkout 的 `src/defense_fourth_game.js` 有 E-122 還沒 commit 的改動，合的時候只套用體力這部分。
2. 舊的 memoized 研究引擎鏈：建議接受不能再跑；要重現舊結果時 checkout 舊 commit。
3. 要不要 commit。

---

技術附錄：
- 關卡數字見 `gates.json`；改動見 `engine.diff`（21 檔）；起點 commit、耗時、偏離見 `run-meta.json`。
- 偏離：
  - c0 的聯盟檔改用追蹤中的 `data/season-league.json`。
  - c3 第一次背景啟動失敗，原樣重跑後通過。
  - `strength_benchmark`、`replay_accounting` 兩個測試檔在 worktree 缺未追蹤的資料，沒跑。

---

## 補充（2026-10-30）：doubleThreat 拿掉體格項併進 0.1.1（R-089）

- 依據 E-135（拿掉體格項量不出效果，F-073），使用者裁定依奧坎剃刀刪掉，併進本版。
- 改動：`src/constants.js` 的 `DOUBLE_THREAT_W` 拿掉 `phys`；`src/probability_model.js` doubleThreat 的得分項改成三項除以權重和（寫法同 E-086 ch1）。
- 驗收 p1（`p1.mjs`，`gates.json` 的 p1_doubleThreatPhysRemoved）：參考組＝改動前的 0.1.1＋E-086 ch1 hook。582 名球員的 doubleThreat、60 場循環賽、3 人×30 對手×2 樣本的 WinImp 180 格，新舊逐位元相同。
- 對照：改動前不加 hook 時，doubleThreat 值不同，但 60 場與 180 格都一樣，表示正式 WinImp 鏈在這些格子對這一項沒反應。
- `test/timed_game.js` 鎖住的原始引擎雜湊 e87f8dce… 改成 edec4342…；改動前的程式加 ch1 hook 跑同一測試，得到的就是 edec4342…。`npm test` 52 項通過。
- 主 checkout（0.1.1 已由別的 session 在 83ceb63 commit）同樣重做一次：改動前＋hook 與改動後的三組雜湊和 worktree 相同（`out/p1-main-*.json`），主 checkout `npm test` 52 項通過。改動見 `dblthreat-phys.diff`（3 檔）。worktree 裡也留有同樣改動（舊分支，不再使用）。
- 未 commit。
