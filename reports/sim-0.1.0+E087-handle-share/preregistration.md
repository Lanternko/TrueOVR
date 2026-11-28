# E-087 預註冊：handle 只決定「誰拿球」（sim 0.1.0+E087）

- 日期：2026-10-29。角色：lead 擬稿並凍結；role-model 實作、跑模擬、寫報告；role-audit 事後重算。
- 觸發：使用者 2026-10-29「想辦法套用控球吧 之前的失誤計算太大包大攬 我們現在只是把它分工而已」，核可本案（「派出opus」）。
- 基準：`sim 0.1.0`（src tree `6f6283a96756445dd90511d2eaa1951a5a7ba514`）。WinImp 引擎、輸入、seed 同 E-065／E-069 第二階段（`reports/handle-E069/sim/` 開關關閉時的路徑）。量尺：E-067。

## 1. 已揭露（lead 看過的東西）

- E-069 第二階段（`reports/handle-E069/sim/report.md`）：handle 同時改「誰拿球」和「失誤 hazard × 持球秒數」，m2 不過（tov36 MAE 0.167 → 0.320）、m3 兩版都不過；主版更偏袒長人，位置版翻成偏袒後衛。lead 看過 E-069 的 G5 名次與 2K27 ρ。
- lead 沒看過「只換 handlingScore 裡的 handle、失誤公式不動」這個組合的任何結果。
- `handle.csv`（E-069 第一階段，582 人，2025-26）：handle 範圍 40–99，平均 66.1、中位 62.95。handle 由 0.5·z(−控球失誤率) + 0.5·z(TIME_OF_POSS/MIN×36) 合成，**一半就是持球時間**，所以「模擬持球時間像不像真實 TIME_OF_POSS」是樣本內，只報告不判定。
- 現況：卡片沒有 handle 欄，模擬一律 `p.handle ?? 70`。WinImp 用 `shotSelection:'legacy'`，所以 `pickWeighted(M.handlingWeights(ls[off]))` 決定第一個觸球的人；`handlingScore = 0.40·handle + 0.30·pass + 0.15·drive + 0.15·tovSkill`（`HANDLING_W`）。handle 恆為 70 時，誰拿球其實由 pass、drive、tovSkill 決定，失誤少、很少持球的人（例如 Hauser）會被當成持球者。

## 2. 假設

E-069 的失敗來自「把失誤也綁到持球秒數」。只把 handle 用在分配持球、失誤公式照舊，應該能讓真正的持球者拿到球，不會讓個人失誤變差，也能減輕長人偏袒。

## 3. 設計

### 3.1 唯一改動
- 新旗標 `handleShare`：
  - `'off'`（預設）：逐位元等於現行。
  - `'measured'`（主版）：`handlingScore` 裡 `p.handle ?? M` 改成「該球員 `handle.csv` 2025-26 的 `handle`（依 playerId）；查不到用 70」。
- 權重 `HANDLING_W` 不變。`HANDLING_TEMP`、`FLOOR_MIX`、`CLAMP` 不變。
- 以下全部**不動**，handle 一律維持 70：
  - doubleThreat 的 `create`（`DOUBLE_CREATE_W`）；
  - `assistBoost`／`HANDLE_IMPACT`；
  - 失誤公式（`tovSkill` 曲線、on-ball 壓迫、包夾脫困、passSec 都不用）。
- **不重新校準任何常數**（包括全聯盟失誤總量）。改動之後總量的位移照實報告。

### 3.2 實作位置
- 同一個 checkout 有另一個 session 在改 `src/constants.js`（E-080 的 `RIMD_SCURVE` 旗標）。**不准改 `src/`**。做法跟 E-076／E-085 一樣：在本目錄寫 wrapper 或 source patch（anchor 漂移就丟錯），只換 `handlingScore` 這一處。
- 跑任何東西時 `RIMD_SCURVE` 不准設定。報告寫明 `git rev-parse HEAD:src`，並說明 working tree 的 src 差異（E-080 旗標，關閉時逐位元相同）有沒有影響。
- 5090 上要用跟本機相同的程式。用 `git archive HEAD src` 或複製本機檔案都可以，報告寫明用哪個，並附 sha256。

### 3.3 前置檢查（p0，不過就停下回報）
- 在 WinImp 路徑與 m2 用的 v41 驗證路徑各數一次：每場 `handlingWeights` 被呼叫幾次、`handlingScore` 裡讀 handle 的次數。任一路徑為 0（例如走的是 `creationPlan.weights`），停下回報，不要自己改路徑。
- 開 `'measured'` 後，同一個陣容的第一觸球分布要跟 `'off'` 不同。抽三個陣容列出來。

## 4. 判定（凍結後不改）

| # | 條件 | 內容 |
|---|---|---|
| (m0) | 開關關閉重現現行 | `'off'` 下 3 個 seed 逐位元相同；WinImp 10 名指定球員（沿用 E-076 `g0-compare.json` 那 10 人）winsPer82 與 `reports/card-0.1.2+E065-inout-wins/winimp.csv` 一致 |
| (m1) | 測試 | `npm test` 全過（在現行 working tree 上跑，記錄通過數） |
| (m2) | 個人失誤不變差（非劣性） | 2025-26 v41 驗證主人群（n 378，同 E-069 `sim/m2.py`）tov36 MAE（`'measured'` − `'off'`），球員 bootstrap 2000、seed 1，90% 上界 < +0.02 |
| (m3) | 長人偏袒 | E-067 的 b1–b3，主版（`winsPer82`）與位置版（`winsPer82_pos`）各判一次，基準線用 E-067 的現行值（主版 S +81.8／+95.2、ρ 0.382；位置版 S +37.5／+50.1、ρ 0.304）。b1 判定不是「偏袒長人」；b2 S 兩個方向都變小（絕對值）；b3 ρ 兩方向平均下降不超過 0.02 |

- 全過：記為「通過」，交使用者 G5 抽查後由 lead 寫 R 條目；不自動改 sim 預設。
- m2 過、m3 沒過：記為「失誤沒變差，偏袒未修」，不採用。
- m2 沒過：不採用。
- 位置版若從偏袒長人翻成偏袒後衛（b1 過但方向相反），判定照表，報告另外標出來。

### 只報告、不判定
- 模擬每人持球秒數（或觸球佔比）對真實 TIME_OF_POSS 的 ρ 與 MAE，`'off'`／`'measured'` 各一。**標明樣本內**（handle 有一半就是持球時間）。
- 全聯盟 TOV 總數誤差、tov36 依 creationDependence 三分組平均誤差（同 E-069 表）。
- 2K27 ρ（主版、位置版）。
- G5 名次（主版／位置版，前 → 後）：Luka Dončić、SGA、Jalen Brunson、Tyrese Haliburton、Nikola Jokić、Derrick White、Sam Hauser、Rudy Gobert、Alex Caruso、Russell Westbrook、Payton Pritchard、Jared McCain、Mark Williams、Alperen Sengun。
- 第一觸球佔比前 20 名（`'off'` vs `'measured'`）。

## 5. 執行

- 人群、seed：WinImp 379 人、E-065 的 `seeds.json`、baseSeed 與樣本數同 E-069 第二階段。
- 重度運算在 5090（`ssh kojiek@140.122.184.29`），nohup + checkpoint。ssh 逾時：跑一次 `Start-ScheduledTask -TaskName 'NTNU VPN Keepalive'`，等約 30 秒，看 `C:\Users\柯子捷\automations\logs\vpn-ntnu.log` 最後一行；還是不通就停下回報，不要重試迴圈，不要退回本機跑全量。
- 本機只跑 m0、m1、p0、小量 smoke。Python 子程序帶 `CREATE_NO_WINDOW`；背景指令加 `</dev/null` 與 `timeout`。
- 可以複製並改寫 `reports/handle-E069/sim/` 的工具（`m2.py`、`winimp-run.mjs`、`analyze-winimp.mjs`、`winimp-core.mjs`、`../bias_check.py`）。原檔唯讀。

## 6. 不准

- 看過任何 m2／m3 結果後再改 handle 的用法、權重、溫度或人群（L-026）。要改就停下回報，由 lead 寫新預註冊。
- 改 `src/`、`memory/`、`reports/` 其他實驗目錄、正式卡片、live 頁、gh-pages、排程。
- commit 或 push。
- 只寫入 `reports/sim-0.1.0+E087-handle-share/`。

## 7. 產出

`report.md`（判定表 + 只報告項 + 解讀，解讀標「不算證據」）、`results.json`、`m2.json`、`bias.json`、`winimp-measured.csv`、`p0.json`、`handleShare.patch` 或 wrapper 原始碼、`run-meta.json`（src tree、程式 sha256、seed、主機）。
