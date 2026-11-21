# E-161 預註冊：新賽季 OVR 上場時間只算一次（凍結 stamina、保留分鐘）

- 日期：2026-11-01
- 來源：使用者 2026-11-01 問「jalen williams 為什麼比 chet，jokic 高？」→「查收縮」→「分鐘和體力只用其中一個……我傾向用分鐘」（R-105）。
- 基準：inseason 0.2.9（`reports/ovr-inseason-2026-27/live/run_c4_live.py`，CARD_MODE=029，先驗 card 0.2.9）。
- 實驗版號：`inseason 0.2.9+E161`。不佔版號；採用後依 R-064 寫成 inseason 0.2.9-s1（先驗卡不變、新賽季自己的模型改動）。
- 角色：role-card 執行；結果由 role-audit 用另一個 session 重算。
- 凍結：**未凍結**。使用者核可後把 sha256 寫進 `preregistration.sha256` 和 experiments.md E-161，之後不改；要改就寫 errata 給使用者核可。

## 0. 背景與假設

inseason 0.2.9 的上場時間被用了兩次：

1. stamina 能力值：本季 MPG 百分位做觀測，C4 收縮 k_eff≈1.4 場（δ²=163.8、σ²=232.5），最小樣本 1 場（E-064 G1）。3 場就拿約 70% 權重，抬高每 36 產值。
2. MPG_hat = MPG0 + w·(本季場均分鐘 − MPG0)，w 就是上面 stamina 的 C4 w。抬高每場分鐘。

兩者來自同一個「本季打比較久」。網站已不顯示體力（R-057），體力數值本身就是分鐘＋年齡。

假設：stamina 能力值凍結在開季卡、只保留 MPG_hat 更新之後，追蹤整季答案的能力不變差。不主張變準（答案卡的 stamina 是整季 MPG 百分位，凍結之後 N 大時可能略差，這正是要量的）。不主張變準，所以不升 MINOR（R-064）。

沒有新參數、沒有擬合季：w 照舊（G1 的 stamina w），只是不寫回能力值（L-037 不適用）。

## 1. lead 已看過的（揭露）

- 線上 2026-10-30 快照的診斷（`live_predict` diag）：JW stamina x0 74.3→84.1（n=3、k=1.361、w=0.699），Chet 76.7→80.4，Jokić 96.9→98.6。
- 線上單人反事實：JW stamina 退回開季，每 36 pred 2.891→2.627；Jokić 3.774→3.729；Chet 不變。lead 據此估 JW 拿掉兩段約 86.9。
- E-064（G0／G1 選 G1）、E-095 的回測結構與結果。
- **沒看過**任何回測起點上「凍結 stamina＋G1 分鐘」的數字。

## 2. 改動（只加開關，預設值不變）

1. `run_c4_live.py`：新增環境變數 `STAMINA_FREEZE=1`（預設 0）。
   - 開啟時 stamina 不寫回能力值（等同進 frozen），但仍照現行公式算 stamina 的 C4 w（同一個 n、k、f），只給 MPG_hat 用。
   - 用人層、防守加成、其他 15 項能力值、錨點、W 都不動。
2. 新回測 `reports/ovr-inseason-2026-27/e161-stamina-freeze/backtest_e161.py`，只 import `v5/tools/backtest_e064.py`，不改它。
   - 新模式 `RG1F`：能力值用 `c4_run(..., frozen ∪ {'stamina'})`，MPG_hat 用 G1 的 w1（`c4_run(..., min_stamina=1)` 的 diag）。
   - 對照 `RG1`（E-064 原樣，副版公式）。答案卡、錨點、r_repl、人群全部沿用 E-064。

## 3. 評估

- 回測起點 Y5、Y6；N = 3、5、10、20，共 8 格；人群與 E-033／E-064 相同。
- e = 預測 OVR − 答案卡 OVR（副版、同一組 E-064 錨點）。
- 比較 RG1F 對 RG1；bootstrap 球員配對 2000 次，seed 1。

## 4. 判定表（事先訂定）

| # | 條件 | 門檻 |
|---|---|---|
| (c0) | RG1 重現 E-064 | RG1 預測與 E-064 輸出最大差 < 1e-9 |
| (c0L) | 線上預設不變 | `STAMINA_FREEZE` 未設時，2026-10-30 快照的 ranking.csv、no-prior.csv 和現行輸出逐位元相同 |
| (c1) | npm test | 全過 |
| (u) | 開關只動 stamina | `STAMINA_FREEZE=1` 時，線上快照每人除 stamina 外 15 項能力值與預設版差 0；stamina＝開季卡值；MPGhat 與預設版差 0 |
| (1) | 仍過原閘門 | RG1F 過 v5 §2 的 V1∧V2，原門檻不改 |
| (2) | 追蹤不變差 | 8 格每格 MAE(RG1F) − MAE(RG1) ≤ +0.05 |

採用規則：

- 前置 (c0)(c0L)(c1)(u) 任一不過：停下回報，不看 (1)(2)。
- (1)(2) 都過：交 role-audit 重算，再交使用者 G5（抽查線上頁前 20 與開季分鐘大增的人）。
- (1) 過、(2) 不過：不自動採用，回報哪幾格變差多少，交使用者選（仍為「不重複計算」採用／維持現狀／改試加強 stamina 收縮）。
- (1) 不過：不採用。

## 5. 只報告（不影響判定）

- 8 格合併 MAE 差的 bootstrap 90% 區間。
- 依「本季場均分鐘 − MPG0」三分位（分鐘大增／持平／大減），N = 3、5 的有號平均 e 與 MAE：看分鐘大增那組是否不再被高估。
- 線上 2026-10-30 快照 0.2.9 對 0.2.9+E161：|ΔOVR| 中位數、最大值、> 3 分人數；前 20 名進出；Jalen Williams、Chet Holmgren、Nikola Jokić 的 OVR 與名次。
- 敏感度：Y3 與 D1–D3 的 (1)(2) 數字。
- 限制：回測沒有用人層（predNew）與 E-104 防守加成，線上才有；線上差異只描述、不當證據（R-007）。

## 6. 判定後才做

- 採用：`run_c4_live.py` 預設開 `STAMINA_FREEZE`，VERSION 改 `inseason 0.2.9-s1`；先 `daily_inseason_update.py --dry-run` 再正式發布（L-048、R-031）；看 season_nav 版本欄驗收（L-050）；season_nav 更新說明加條目；狀態板與 handoff 一起更新（L-034）。
- 不採用：season_nav 新賽季說明註明「上場時間同時影響體力與分鐘」。

## 7. 不准

- 不改 `src/`、`reports/card-0.2.9/`、`v5/tools/` 既有檔、E-064／E-095 輸出；執行前後對這些檔做 sha256 核對。
- 輸出只寫 `reports/ovr-inseason-2026-27/e161-stamina-freeze/`；`run_c4_live.py` 只能加開關。
- 看到 (1)(2) 結果之後，不改門檻、人群、起點或 w（L-026）。
- 不 commit、不 push、不部署 gh-pages。
- 重度回測跑 5090。回報照 CLAUDE.md 六段格式，第一行 `# 總評`。
