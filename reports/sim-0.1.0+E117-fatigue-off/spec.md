# E-117 規格：模擬關掉體力，WinImp 和球隊賽季誤差會怎麼變（描述性量測）

- 日期：2026-10-30（使用者「量」）
- 性質：**描述性診斷，不是採用候選**。不調任何參數，只比較體力開／關兩個版本。結果不直接改正式流程；要不要關體力，看完結果由使用者決定（R-068 的 TODO）。
- 軌道：`sim 0.1.0`，引擎＝HEAD 的 `src/`（`git log 45346b9..HEAD -- src/` 為空，src 和 45346b9 相同）
- 角色：lead 寫規格；App 內 Sonnet 子代理（role-model）實作與跑；lead 從 JSON 重算後寫報告

## 0. 要回答的問題

1. 體力關掉以後，WinImp 的球員名次會變多少？長人偏袒量尺 S（E-067）和對答案的 ρ 會變好還是變差？
2. 30 隊互打的模擬賽季，每隊淨分差和勝率對真實 2025-26 的誤差（MAE、RMSE）會不會變？

## 1. 已揭露

- lead 沒有跑過任何體力關閉的 WinImp 或球隊模擬。
- lead 從公式推過：正式流程（`budget` 模式）換人照排程，體力只讓場上的人隨時間打折（`applyStamina`，能力 × 1 − 0.3 × 疲勞）。stamina 99 打 7 分鐘約 ×0.94，stamina 40 約 ×0.92。stamina 目前等於場均分鐘排名，所以關掉以後預期主力略降、替補略升，幅度不知道。
- `reports/defense-a/variance.json` 有 heuristic 模式的 `noFatigue` 變異數探針，和這次的問題無關，沒拿來用。

## 2. 設定

- 體力開＝現行：`reports/player-impact-v29/benchmark.mjs` 的 `options()`，含 `fatigue:true`、`minuteMode:'budget'`。
- 體力關：同一組 options，最後再蓋上 `fatigue:false`，其他完全相同。
- **p0 先驗證選項有接上**（L-059）：同一個 seed 的單場，關體力的輸出要和開體力不同，而且全場每位球員的 energy 都維持 1（或 `applyStamina` 沒被呼叫）。p0 不過就停下回報。

### 2.1 WinImp

- 同 E-065／E-076：379 人（MIN ≥ 500）、baseSeed 20261028、30 對手 × 16 樣本 × 2 邊，主版 `avg` 和位置版 `pos` 都跑。harness 用 `reports/card-0.1.2+E065-inout-wins/` 的 winimp-core／run／worker（E-076 怎麼覆蓋 options 就照做）。
- 體力開的版本：先檢查 g0。用現在的 HEAD 重跑 E-065 指定的 10 名球員，winsPer82 要和 `reports/card-0.1.2+E065-inout-wins/winimp.csv` 完全一致。一致就沿用該 csv 當「開」的版本；不一致就全量重跑「開」的版本，並記進偏離。
- 產出 `winimp-off.csv`，欄位同 E-065。

### 2.2 球隊賽季

- 同 E-076 t1：`winimp-core.mjs` 的 `opponentTeam()` 30 隊互打循環賽，8 個 seed（20261028…20261035），體力開、關各跑一次。
- 每隊算兩個量，都和 2025-26 真實值比：
  - 模擬每場淨分差 vs 真實淨效率（同 E-076 的來源 `reports/sim-0.1.0+E076-physique-dedup/league-actuals.json`，或 E-076 用的同一份）。
  - 模擬勝率 vs 真實勝率。
- 每個量都報 MAE 和 RMSE。關減開的差值，用 team＋seed 聯合重抽 400 次（rngSeed 117）算 90% 區間。

## 3. 要報的數字（全部只報告，不設通過門檻）

| 代號 | 內容 |
|---|---|
| W1 | 主版、位置版：開與關的名次 Spearman；平均 \|名次差\|；名次變動最大的上升、下降各 10 人（附位置、場均分鐘、stamina） |
| W2 | 前 20 名名單的進出 |
| W3 | 依 stamina 四分位分組的平均名次變化（驗證「主力降、替補升」的推測） |
| W4 | E-067 量尺：關體力版的 S（主版、位置版、AB／BA），用 E-076 的 `bias_e076.py` 做法註冊新欄，不改 E-067 的數學 |
| W5 | 對答案的 ρ（E-064 AB／BA），開與關 |
| T1 | 球隊淨分差 MAE、RMSE，開與關，差值與 90% 區間 |
| T2 | 球隊勝率 MAE、RMSE，開與關，差值與 90% 區間 |
| T3 | 聯盟平均每場得分、每回合得分，開與關 |

## 4. 不做的事

- 不改 `src/`，不改正式的 WinImp 鏈、卡片、網站。
- 不調任何參數，不在看過結果後加其他版本（L-026）。
- 不 commit、不 push。

## 5. 產出

都放在 `reports/sim-0.1.0+E117-fatigue-off/`：`gates.json`（p0、g0）、`winimp-off.csv`、`team.json`（T1–T3）、`winimp-compare.json`（W1–W3、W5）、`bias.json`（W4）、`run-meta.json`（版本、seed、機器、耗時、sha256、偏離）、腳本。`report.md` 由 lead 寫。
