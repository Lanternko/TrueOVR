# E-064 預註冊：OVR 改為每場影響力（含上場時間），卡片與賽中兩邊

- 日期：2026-10-28（使用者裁定 R-025、R-026「每場，含上場時間」）
- 版本：卡片 `card 0.1.2+E064`、賽中 `inseason 0.1.1+E064`（R-018）。這是使用者裁定的定義變更；版本號（PATCH 或 MINOR）由使用者在看完結果後定。R-009「v5 之後沒有 v6」不受影響：賽中只換 OVR 的單位與上場時間的更新，C4 方法不變。
- 基準：卡片 `card 0.1.2`（0.1.1＋E-060 onBall，`reports/card-0.1.1+E060-onball-targeting/primary/`）；賽中現行 C4（E-033，`reports/ovr-inseason-2026-27/v5/pathA/backtest/`，c=1，凍結管線 v58 H1-m0）。

## 1. 問題（lead 已看過的東西，已揭露）

- 看板模擬本身算的是每場貢獻：候選人上場 supportedMinutes 分鐘、其餘四位是平均球員，量和同分鐘平均球員的淨分差（F-029）。`calibrate-wing.py` 的 `load()` 用 y = 貢獻／m×36 換成每 36 分鐘，所以上場時間被拿掉了。
- 賽中 stamina（原始值＝MPG）要 5 場才更新（`SEASON_MIN_SAMPLE`）。Ty Jerome 2026-27 前 4 場的視窗 stamina 是 88.1（上季 52.3），被擋下後仍用 x0。
- lead 看過的資料：2026-27 賽中名單、Jerome／Maxey 逐項診斷，以及 E-033／E-062 已公開的回測數字。**每場版在任何回測季、在 RAPM 分半上的數字都還沒看過。**

## 2. 共同定義（寫死）

- 每 36 影響力 `pred`：沿用現行管線，算到 OVR 映射之前的最後一個值。卡片 0.1.2 是 calibrate-wing.py L421 映射前的 `pred`；賽中是 `pointwise_pipeline.PointwisePipeline.predict` 裡的 `pred`，也就是 pred0＋bonus＋align 再經 H1 封頂。迴歸、align、封頂、位置置中全部不動。
- 每場影響力：`g = pred × MPG / 36`。MPG＝出賽場次的平均分鐘（MIN／GP），所以缺陣場次不計入。
- 主版的基準是聯盟平均（pred＝0 時 g＝0），與看板模擬的同分鐘平均基準一致。
- 每場 OVR：`ovr = 40 + 30(g−q1)/(q50−q1)`（g ≤ q50）；否則 `70 + 29(g−q50)/(q99−q50)`。這是現行同一條兩段式映射，只是錨點換成每場的 q1、q50、q99。
- 卡片錨點：card 0.1.2 的 MIN≥500 池，各人 g 的 PR1、PR50、PR99。分位數算法與現行 `scaleAnchorsPer36` 相同。
- 賽中錨點：凍結摘要（`V2.FROZEN_SUMMARY`，v58 H1-m0 的 2025-26 卡）原本算 `scaleAnchorsPer36` 的那個池，改用 g 重算 PR1、PR50、PR99。算一次後所有起點共用，和現行每 36 錨點的用法一樣。
- 副版（只報告）是替補水準基準：`g_r = (pred − r_repl) × MPG / 36`，r_repl＝同一個 MIN≥500 池裡 pred 的 PR10。錨點規則同上，改用 g_r。
- 其他都不動：16 項能力值的定義、attr() 上限 99、看板目標、RAPM 檔、2K 封頂。

## 3. 卡片端

### 3.1 候選

`card 0.1.2+E064`：card 0.1.2 的 pred 乘上 2025-26 的 MPG/36，用每場錨點映射。開關預設關。

### 3.2 樣本外驗收（G4，照 v58-holdout 的做法）

- 重用 `reports/ovr-v58-holdout-2025-26/rapm-A.csv`、`rapm-B.csv`：四季合併後依 `int(gameId) % 2` 切成兩半，偶數 A、奇數 B。
- 用 RAPM A 擬合 card 0.1.2 管線，凡讀 RAPM 的步驟都換成 A，得到 fitA；用 B 得到 fitB。
- 預測分鐘只用擬合那一半的比賽。fitA 用 MPG_A，也就是 2025-26 偶數 gameId 場次的 MIN／GP；fitB 用 MPG_B。
- 答案用另一半。A→B：答案 = RAPM_B 的 pooledNet × MPG_B。B→A 對稱。預測和答案的比賽不重疊。
- 人群：v58-holdout 的共同人群（pooledPoss ≥ 2500），而且 2025-26 在 A、B 兩半各至少出賽 5 場。
- 指標：Spearman ρ，取 A→B 與 B→A 的平均。
- bootstrap：以球員配對重抽 2000 次、seed 1，兩個方向用同一組重抽。

| # | 條件 | 門檻 |
|---|---|---|
| (c0) | 開關關掉時重現 card 0.1.2 | `primary/ranking.csv` 的 OVR 逐位元相同，或最大差 < 1e-9 |
| (c1) | G1 | `npm test` 過 |
| (c2) | 每場 OVR 比每 36 OVR 更接近每場影響力 | ρ(OVR_game) − ρ(OVR_36)，90% 區間下界 > 0 |
| (c3) | 能力值在上場時間之外還有資訊 | ρ(OVR_game) − ρ(MPG 預測分鐘本身)，90% 區間下界 > 0 |

- (c0)–(c3) 全過：卡片端記為「通過」，交使用者定版本。
- (c3) 不過：記為「每場 OVR 幾乎等於上場時間」，不自動採用，交使用者決定。
- (c0) 不過：整輪停止，先修程式，不看任何誤差數字。

### 3.3 只報告

- 舊目標，也就是每 100 回合的 RAPM_B pooledNet：OVR_36 和 OVR_game 的 ρ（預期 game 版較低）。
- 2K27 ρ：OVR_game、OVR_36、副版都列。2K 不是每場定義，所以不設門檻。
- G5 抽查材料，主版與副版並排、對上 0.1.2：
  - 前 20 名；
  - 前十名裡長人有幾位；
  - Ty Jerome、Tyrese Maxey、Walker Kessler、Jokić 的 OVR 與名次。
- 副版的 (c2)、(c3) 數字。
- 反轉診斷：MIN≥500 池裡，有多少 MPG ≥ 20 的人，主版 OVR 低於 MPG < 12 那群人的主版 OVR 中位數。副版同樣報。
- creation 碰到 99 的人數（看板能力值本身，不改）。

## 4. 賽中端

### 4.1 候選（全部用每場 OVR）

| 候選 | 上場時間 MPG_hat | stamina 能力值 |
|---|---|---|
| **G1**（主） | `MPG0 + w·(MPG_win − MPG0)`，最低樣本 1 場 | 現行 C4 更新，最低樣本改 1 場 |
| G5 | 同上，最低樣本 5 場（未達時用 MPG0） | 現行（5 場） |
| G0 | MPG0（不更新） | 現行（5 場） |

- MPG0 取先驗卡那一季的 MIN／GP，MPG_win 取視窗內的 MIN／GP。
- w 用 stamina 這一項在 C4 的 w，也就是 `f + (1−f)·n/(n+c·k_eff)`，其中 n、k_eff、f、c 都照 stamina 的現值。w 不帶單位，所以可以直接套在 MPG 上，也不會碰到 attr() 的 99 上限。
- 其餘不動：其他 15 項能力值照現行 C4（含 E-062 不採用後的現狀、pressure 凍結），δ²、c、reliability.csv、起點鏈都不變。
- 答案卡（每場）：答案卡的能力值經現行答案卡的同一條管線得到 pred，乘上該季整季 MIN／GP 再除以 36，用 §2 的每場錨點映射。

### 4.2 判定（事先訂定）

- 主判定起點 Y5、Y6；N＝3、5、10、20；人群和 E-033 相同（同一個 P）。
- e = 預測每場 OVR − 答案卡每場 OVR。

| # | 條件 | 門檻 |
|---|---|---|
| (0) | 開關全關時重現 E-033 | C4 的 predictions-Y5／Y6.csv 逐位元相同，或最大差 < 1e-9 |
| (1) | 對先驗卡（每場版 A）仍過原閘門 | v5 §2 的 V1∧V2，原門檻不改 |
| (2) | 更新上場時間不比不更新差 | G1 對 G0，8 格每格 MAE 差 ≤ +0.05 |
| (3) | 更新上場時間「變準」 | G1 對 G0 的 8 格合併 MAE 差（Y5、Y6 等權），以球員配對 bootstrap 2000 次、seed 1；90% 區間上界 < 0 |

採用規則：

- G1 過 (0)–(3)：採用 G1。
- G1 不過但 G5 過：採用 G5。
- 兩者都不過：賽中每場版採用 G0，也就是只換單位、不更新上場時間，並記錄結果。
- G1 對 G5 的同組數字照列。G5 過、G1 也過時仍取 G1，因為 G1 是事先定好的主版，小樣本交給收縮處理。

只報告：

- 現行每 36 C4 對每場答案卡的 MAE，看單位換掉後差多少。
- 敏感度 Y3、次要 D1–D3 的 (1)(2)(3) 數字。
- 依 MPG0 分三組（各起點自己的三分位），N＝5、10 的有號平均 e 與 MAE。
- 副版（替補水準）的 8 格 MAE。

## 5. 判定後才做（不影響判定）

用採用的賽中候選，加上每場錨點，重算 2026-27 賽中名單（`live/run_c4_live.py` 加同一開關）。報告：

- ΔOVR 分布：≤−1 和 ≥+1 的人數，對照現行頁面；
- Ty Jerome、Maxey、Kessler 的前後值與逐項 MPG_hat；
- creation 碰到 99 的人數。

不部署，等使用者看。

## 6. 不准

- 看過任何每場版的數字之後，再改基準（平均／替補）、錨點規則、PR10、最低樣本（1／5）、人群、起點、MPG 定義或門檻（L-026）。
- 動現行輸出。`reports/card-0.1.1+E060-onball-targeting/`、`reports/ovr-v58-holdout-2025-26/`、`v5/pathA/backtest/`、`live/` 現行頁面檔都唯讀。新輸出寫到：
  - 卡片：`reports/card-0.1.2+E064-pergame/`
  - 賽中回測：`reports/ovr-inseason-2026-27/v5/pathA/backtest-e064/`
  - 賽中參考：`reports/ovr-inseason-2026-27/live/2026-10-28-e064/`
- 不改 creation 上限、位置置中、看板目標。這些另案處理，不綁在這次。
- 不部署、不 commit。
- 本輪不跑新的看板模擬，所以沒有 seed 數的要求。若實作發現必須重跑模擬，就停下回報，不自行加跑。
