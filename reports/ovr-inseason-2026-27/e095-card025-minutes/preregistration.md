# E-095 預註冊：新賽季 OVR 跟上 card 0.2.5 的分鐘權重

- 日期：2026-10-29
- 來源：使用者 2026-10-29「曲線的部分都完成了嗎」→「寫預註冊」；R-048 已寫明賽中要改用 W 必須另走 inseason 實驗。
- 基準：inseason 0.2.2a（`reports/ovr-inseason-2026-27/live/run_c4_live.py`，CARD_MODE=024，先驗為 card 0.2.4）。
- 實驗版號：`inseason 0.2.4a+E095`（inseason 0.2.2a 在 R-050 改名 0.2.4a，內容相同）。不佔版號；採用後新賽季跟先驗同號，升為 inseason 0.2.5。
- 改號：原編號 E-094，和防守天花板（card-0.2.5+E094）重號，2026-10-29 改成 E-095。
- 角色：role-card 執行；結果由 role-audit 用另一個 session 重算。
- 凍結：**已凍結**（2026-10-29，使用者「核可」）。sha256 寫在 `preregistration.sha256` 和 experiments.md 的 E-095 條目，之後不改；要改就寫 errata 給使用者核可。

## 0. 背景與假設

card 0.2.5 已把替補水準增益的分鐘權重從線性改成飽和曲線（R-047、R-048）：

- 舊：g = (pred − r_repl) × m / 36
- 新：g = (pred − r_repl) × W(m)，W(m) = (1 − e^(−m/15)) / (1 − e^(−36/15))

新賽季頁（`run_c4_live.py` 的 `e064_convert`，約第 384 行）仍是 `mpg / 36.0`，錨點也還是 card 0.2.4 的（E-084 results.json），所以新賽季頁和名單頁的分鐘權重不一致。

假設：新賽季 OVR 改用 W 之後，追蹤整季答案的能力不會變差。不主張變準：W 的答案卡和線性的答案卡不是同一個目標，所以這次最多是 PATCH，不升 MINOR（R-019）。

W 沒有可調參數（尺度 15 已由 R-047 定死），也沒有其他擬合，所以不需要選候選，也沒有擬合季（L-037 不適用）。

## 1. lead 已看過的（揭露）

- 卡片端 E-089 全部結果：Caruso 103 → 39 名；card 0.2.5 錨點 PR1/50/99 = −0.8153／1.2506／3.4429（E-089 `results.json` 的 `report_only.card.new`），r_repl −1.27245 不變。
- 線上新賽季頁 inseason 0.2.2a 的內容，以及 E-064、E-091 的結果。
- `backtest_e064.py` 的結構：錨點計算、副版 RA／RG0／RG1 = (pred − r_repl) × MPG / 36。
- **沒看過**任何用 W 算出的新賽季數字，包括回測和線上頁。

## 2. 改動（只加開關，預設值不變）

1. `run_c4_live.py`：
   - 新增 `CARD_MODE='025'`。`FORMAL_RANKING` 指向 `reports/card-0.2.5/ranking.csv`，sha256 核對改對 `reports/card-0.2.5/summary.json`（ranking 73b1d635…050a）。
   - 錨點與 r_repl 改讀 E-089 `results.json` 的 `report_only.card.new`。
   - `e064_convert` 的分鐘權重在 025 模式改用 W(mpg)。live、ref、o1 三處都會經過 `e064_convert`，三處一起換。
   - 用人回歸特徵（`usage-2025-26-card024.json`）、MPG0（card 的 mpg 欄）、w、其他 15 項能力值都照舊。card 0.2.5 沒有改用人回歸，ranking 的 mpg 欄和 0.2.4 相同，執行時要核對。
   - 預設仍是 024，採用之後才改預設。
2. 新回測 `reports/ovr-inseason-2026-27/e095-card025-minutes/backtest_e095.py`。只 import `backtest_e064.py`，不改它。
   - 分鐘模式 `--minutes {linear,sat15}`。
   - 錨點池與 `compute_anchors()` 相同，只把副版的 `(p − r_repl) × m / 36` 換成 `(p − r_repl) × W(m)`，PR1／50／99 重算。r_repl 沿用 E-064 回測自己算的值（`anchors.json` 的 rRepl = −1.813，錨點池 pred 第 10 百分位），不換成卡片的 −1.27245。
   - 答案卡用同一條式子：答案卡 pred、整季 MIN／GP、同一組 W 錨點。
   - 預測：RG1（G1 上場時間，副版公式）。linear 模式就是 E-064 的 RG1。
3. 單元檢查：W(0)=0、W(36)=1、W(5)≈0.31175、W(20)≈0.80987（|差| < 1e-5）。

## 3. 評估

- 回測起點 Y5、Y6；N = 3、5、10、20，共 8 格；人群和 E-033／E-064 相同（同一個 P）。
- e = 預測 OVR − 答案卡 OVR，兩邊都在同一個 40／70／99 映射上（`map_g`）。
- 比較：RG1-sat15（對 W 答案卡）和 RG1-linear（對線性答案卡）。
- bootstrap：球員配對 2000 次，seed 1。

## 4. 判定表（事先訂定）

| # | 條件 | 門檻 |
|---|---|---|
| (c0) | linear 模式重現 E-064 | RG1 的預測與答案卡逐位元相同，或最大差 < 1e-9；錨點 `repl` 與 E-064 `anchors.json` 相同 |
| (c0L) | 線上 024 模式不變 | 同一份資料快照下，ranking.csv、no-prior.csv 和現行 live 輸出逐位元相同 |
| (c1) | npm test | 全過 |
| (u) | W 單元檢查 | 第 2 節第 3 點四個值全過 |
| (L1) | 025 模式重現 card 0.2.5 | ref 轉換（只用 MPG0，不看本季）得到的 OVR 對 card 0.2.5 ranking 的 ovr，在卡內每人 \|差\| ≤ 0.1；用到的錨點與 E-089 `report_only.card.new` 差 0 |
| (1) | W 版仍過原閘門 | RG1-sat15 對 W 答案卡，過 v5 §2 的 V1∧V2，原門檻不改 |
| (2) | 追蹤不變差 | 8 格每格 MAE(RG1-sat15) − MAE(RG1-linear) ≤ +0.05 |

採用規則：

- 前置 (c0)(c0L)(c1)(u)(L1) 任一不過：停下回報，不看 (1)(2)。
- (1)(2) 都過：交 role-audit 重算，再交使用者 G5（抽查線上頁前 20 和低分鐘高效率的人）。版號依 R-050 為 inseason 0.2.5（跟先驗 card 0.2.5 同號）。
- (1) 過、(2) 不過：不自動採用。回報哪幾格變差、差多少，交使用者選：
  - 為了和名單頁一致仍採用；
  - 或新賽季頁維持 0.2.4，並在更新說明註明分鐘權重不同。
- (1) 不過：不採用，新賽季頁維持 0.2.4。

## 5. 只報告（不影響判定）

- 8 格合併 MAE 差（Y5、Y6 等權）的 bootstrap 90% 區間。目標不同，所以不拿來主張變準。
- 依 MPG0 三分位（各起點自己的三分位），N = 5、10 的有號平均 e 和 MAE。看低分鐘那組是不是改善最多。
- 線上頁（資料截至 2026-10-28，和 0.2.2a 同一份快照）的 025 對 024 差異：
  - |ΔOVR| 中位數、最大值，以及 > 10 分的人數；
  - 前 20 名進出；
  - 低分鐘高效率的例子（Caruso 型）和打滿分鐘的先發各舉 5 人。
- 敏感度 Y3 和次要 D1–D3 的 (1)(2) 數字。

## 6. 判定後才做

- 採用時：
  - `run_c4_live.py` 預設改成 025，VERSION 改成 `inseason 0.2.5`，字母歸零（R-023、R-050）；
  - 先跑 `daily_inseason_update.py --dry-run` 再正式發布（L-048），發布要完整（R-031）；
  - 頁面驗收看 season_nav 產出的版本欄（L-050）；
  - season_nav 更新說明加一條新賽季條目；
  - 狀態板和 handoff 一起更新（L-034）。
- 不採用時：在 season_nav 的新賽季說明註明「分鐘權重仍是線性（card 0.2.4）」。

## 7. 不准

- 不改 `src/`、`reports/card-0.2.4/`、`reports/card-0.2.5/`、E-089 目錄、`v5/tools/` 既有檔、E-064 回測輸出。執行前後對這些唯讀檔做 sha256 核對。
- 輸出只寫 `reports/ovr-inseason-2026-27/e095-card025-minutes/`；`run_c4_live.py` 只能加開關。
- 看到 (1)(2) 結果之後，不改門檻、尺度、人群或起點（L-026）。
- 不 commit、不 push、不部署 gh-pages，等 lead 和使用者決定。
- 回報照 CLAUDE.md「回報實驗結果」的六段格式，第一行是 `# 總評`。
