# E-107 預註冊：新賽季 OVR 跟上 card 0.2.6

- 日期：2026-10-30
- 來源：使用者 2026-10-30「跟上 0.2.6」（回覆「新賽季頁要不要另開 inseason 實驗跟上 card 0.2.6？」選 A：照 E-095 的作法寫預註冊，跑完給使用者看結果再上線）。
- 基準：**inseason 0.2.5a**（`reports/ovr-inseason-2026-27/live/run_c4_live.py`，CARD_MODE=025，先驗 card 0.2.5，R-052）。
- 實驗版號：`inseason 0.2.5a+E107`。不佔版號；採用後依 R-050 升為 **inseason 0.2.6**（跟先驗 card 0.2.6 同號），字母歸零。
- 角色：role-card 執行；role-audit 用另一個 session 重算。
- 凍結：**已凍結**（2026-10-30，使用者「核可凍結」）。sha256 寫在 `preregistration.sha256` 和 experiments.md 的 E-107，之後不改；要改就寫 errata 給使用者核可。

## 0. 背景與假設

card 0.2.6（E-101，R-060）改了**能力值本身**，這點和 card 0.2.5 不同（0.2.5 的能力值和 0.2.2 逐欄相同，只改了分鐘權重）。0.2.6 改了三件事：

1. 補籃、補扣從中距離改歸近距離：PBP 標成 Mid-Range 但 shotDistance < 8 的 2 分球算近距離。
2. 百分位、r90、r99、r01 改對 2022-23～2025-26 四季合併池計算。
3. 99 以上有尾巴：99 + 51·(1 − e^(−(r − r99)/(1.96·S)))，其中 S = max((r99 − r90)/1.044, SD_pool)。命中率型和量價型照 E-101 §3。底端的開關照 E-101。

之後 OVR 重新擬合。屬性迴歸用 `cards/e101/P1/primary/summary.json`，用人層用 `cards/e101/e084/results.json`。

新賽季頁現在的作法（子代理盤點，2026-10-30）：

- 賽中視窗值用凍結的 2025-26 單季映射（`setup()` 重建，池 GP ≥ 30 且 MPG ≥ 20），夾在 [40, 99]（`ovr_common.attr`、`v4_common.py` L276-277）。
- 2026-27 的 PBP 沒有 `area` 欄，所以 `zone_of` 走座標規則：禁區算 short，(0,0) 哨兵也算 short。
- 先驗 x0 是 `prior-2025-26-card022.json`，迴歸係數是 card 0.2.2 P1，用人層是 `usage-2025-26-card024.json`。

**只換先驗卡會出錯**：

- x0 有尾巴（例如 Giannis short 113），賽中觀測值最高卻只能到 99。
- C4 收縮會把頂端球員隨場數往下拉，造成系統性下修。
- 單季池和四季合併池的刻度也不同。

所以這次賽中觀測值的映射要一起換成 0.2.6 的量尺。

**假設**：新賽季頁整套換成 card 0.2.6 的量尺（先驗、賽中映射、OVR 層）之後，追蹤整季答案的能力不會變差。不主張變準，版號最多是 PATCH（R-019）。

這次沒有新的可調參數：

- 尾巴的 1.96、51、1.044、S 的取法、池的門檻、哪些端點開放，全部照 E-101 凍結的值。
- W 尺度 15 照 R-047。
- C4 的 c、k、δ²、w 照舊。

## 1. lead 已看過的（揭露）

- 看過：
  - E-101 全部卡片端結果。
  - card 0.2.6 的 ranking 和錨點：PR1／50／99 = −0.8131／1.2431／3.5110，r_repl −1.23835（`cards/e101/e084/results.json` 的 `card`）。
  - 各屬性 > 99 的人數：long 1、short 2、ft 2、drive 1、foulDraw 2、tovSkill 2、pass 4、rebound 3、physique 3、onBall 2、creation 2；mid、help、stamina、pressure 都是 0。
  - 線上 inseason 0.2.5a 的內容。
  - E-095 的全部結果，包括 (2) 不過、8 格 MAE 差 +0.19～+0.29。
  - 2026-27 第一場 PBP 的欄位：沒有 `area`，有 `shotDistance`、`xLegacy`、`yLegacy`。
- **沒看過**任何用 0.2.6 量尺算出的新賽季數字，包括回測和線上頁。

## 2. 改動（只加開關，預設值不變）

新增 `CARD_MODE='026'`，預設仍是 025，採用後才改預設。026 模式下有以下六項改動。

1. **先驗 x0**
   - 新增 `live/build_prior_026.py`，照 `build_prior_022.py`，從 `reports/card-0.2.6/ranking.csv` 依姓名覆寫 16 個屬性，產出 `live/prior-2025-26-card026.json`。
   - 先核對 ranking 的 sha256 與 `reports/card-0.2.6/summary.json` 的 `ranking_csv_sha256` 相同（a0a81ecb…6f91）。
   - 尾巴值原樣帶入，不夾 99。
   - foulDraw 的凍結重算檢查改對 0.2.6 的新量尺（見第 3 點），不能直接拿掉。
2. **OVR 層**
   - `CARD_DIR` 改指 `reports/card-0.2.5+E101-crossera/cards/e101/P1/primary`，屬性迴歸用其中的 `summary.json` 的 `formula`。
   - 用人層的係數改用 `cards/e101/e084/results.json` 的 `coefficients.card`。新增 `live/build_usage_026.py`（照 `build_usage_024.py`），產出 `live/usage-2025-26-card026.json`。用人特徵仍凍結在 2025-26。
   - r_repl 和錨點用同一份檔案的 `card`。
   - 分鐘權重沿用 W（scale 15）。
3. **賽中映射換成 0.2.6 量尺**（會更新的屬性：long、mid、short、ft、foulDraw、tovSkill、pass、rebound、creation、stamina）
   - **參考池**：用新賽季管線自己的原始值函式（`season_attrs_v4` 的 raw，以及 foulDraw 的 E-070 公式）分別算 2022-23、2023-24、2024-25、2025-26 四個整季，合併成池。
     - 每個球員季算一筆，不去重。
     - 池的門檻照 E-101：GP ≥ 30 且 MPG ≥ 20；命中率型、量價型用 MIN ≥ 500。
     - 池凍結成檔（`live/pool-026.json`，附 sha256）。
     - 不用 E-101 的 `pool/raw-*.json`：那是卡片端的原始值定義，和賽中的定義不一定相同。
   - **百分位型**：40／70／99 映射的 PR1／PR50／PR99 改對合併池算，99 以上照 E-101 的 `top_tail`。
   - **命中率型**（long、mid、short、ft）：照 E-101 §3，a99 照曲線，s = 1.96·S_p，S_p 用 MIN ≥ 500 合併池算。
   - 底端開關照 E-101：E-090 的 `h1-results.json` 加上 E-101 的 `h1-results.json`，同 `build_e101.py` 的 `passed()`。這裡只照抄，不重新判定。
   - `v4_common` 和 `ovr_common` 的 [40, 99] 夾值，只在 026 模式改成照開關放寬。其他模式逐位元不變。
   - 凍結屬性（physique、onBall、help、heightInches、pressure、drive）照舊不更新，x0 已帶 0.2.6 的值。
4. **分區**：`zone_of` 在 026 模式加上 E-101 規則，有 `area` 而且 `area == 'Mid-Range'` 且 `shotDistance < 8` 時判 short。
   - 2026-27 沒有 `area`，座標規則本來就把 8 呎內判成 short，所以預期這條在 2026-27 不起作用。
   - 會受影響的是參考池裡有 `area` 的季（2022-23 之後）。
5. **版號**：026 時 `VERSION = 'inseason 0.2.6'`、`CARD_VERSION = 'card 0.2.6'`、`FORMAL_RANKING = reports/card-0.2.6/ranking.csv`。
   - `probe_base_version` 讀第一個字面值，所以採用前第一個字面值不改。
   - 採用時才把第一個字面值換成 0.2.6，其他模式的值放在後面。
6. **回測**：新回測 `e107-card026/backtest_e107.py`，只 import `backtest_e064.py` 和 `backtest_e095.py`，兩者都不改。
   - 026 模式下，各起點的先驗卡和答案卡都用第 3、4 點的映射重建，屬性迴歸用 E-101 P1 primary 的 `formula`。
   - 錨點、r_repl、W 的算法同 E-095 sat15：錨點池重算，r_repl 是錨點池 pred 的第 10 百分位。
   - 參考池是第 3 點那個凍結的 2022-26 池。對 Y5（2019-20→2020-21）、Y6（2020-21→2021-22）來說，這個池是未來的季。它只決定刻度，不含答案；這點在報告裡揭露。

## 3. 評估

- 回測起點 Y5、Y6；N = 3、5、10、20，共 8 格。人群和 E-095 相同。
- e = 預測 OVR − 答案卡 OVR，兩者用同一套 026 映射和錨點。
- 照 L-053 寫明三者：

  | | 欄位／來源 |
  |---|---|
  | 候選 | RG1-026（G1 上場時間、W 權重、026 映射） |
  | 基準 | E-095 的 RG1-sat15（`e095-card025-minutes/predictions-sat15.csv`，即現行 0.2.5a 的作法） |
  | 答案卡 | 各自量尺的整季答案卡：候選對 026 答案卡，基準對 E-095 的 W 答案卡 |

- (1) 的同尺度先驗基準是 RA-026，也就是 026 先驗卡的每場 OVR。
- bootstrap：球員配對 2000 次，seed 1。

## 4. 判定表（事先訂定）

| # | 條件 | 門檻 |
|---|---|---|
| (c0) | 025 不變 | `CARD_MODE=025`，用已發佈的資料快照（cutoff 2026-10-28，dataSha256 e576b6b4…b98b），ranking.csv、no-prior.csv 與現行 0.2.5a 輸出逐位元相同 |
| (c1) | npm test | 全過 |
| (u) | 尾巴函式 | 拿 E-101 的合併池和 S，賽中映射函式對 `build_e101.py` 的 `top_tail` 重算 5 個點（r99、r99 + S、r99 + 3S、r99 + 10S、r99 − S）都 \|差\| < 1e-9；W 四個單元值同 E-095 |
| (z) | 分區 | 2025-26 整季 PBP 經 026 的 `zone_of`，每人 mid、short 出手數與 E-101 修正後的分區相同（`zones-check.json` 或 `a0-e101.json` 的出手數，0 人不符）；2026-27 已有場次裡 shotDistance < 8 卻判 mid 的出手為 0 |
| (L1) | N=0 重現 card 0.2.6 | ref 轉換（只用 x0 和 MPG0，不看本季）的 OVR 對 card 0.2.6 ranking 的 ovr，卡內每人 \|差\| ≤ 0.1；用到的錨點、r_repl 與 `cards/e101/e084/results.json` 的 `card` 差 0 |
| (s) | 量尺一致 | 2025-26 池內球員的整季視窗值經 026 映射得到 y，算 y − x0(0.2.6) 的中位數；再算 025 映射對 x0(0.2.2) 的同一個量。每個會更新的屬性，在「全部」和「x0 前 5%」兩組都要 \|中位差₀₂₆\| ≤ \|中位差₀₂₅\| + 2.0 |
| (1) | 仍過原閘門 | RG1-026 對 026 答案卡，過 v5 §2 的 V1∧V2，基準 RA-026，門檻不改 |
| (2) | 追蹤不變差 | 8 格每格 MAE(RG1-026) − MAE(RG1-sat15) ≤ +0.05 |

採用規則：

- 前置條件 (c0)(c1)(u)(z)(L1)(s) 任一不過：停下回報，不看 (1)(2)。
- 實作時發現某一步做不到，例如 2022-23 到 2024-25 的整季資料不能用新賽季原始值函式重算：停下回報，不要自行改作法。
- (1)(2) 都過：交 role-audit 重算，再交使用者 G5，抽查線上頁前 20 名和尾巴 > 99 的人。版號是 inseason 0.2.6。
- (1) 過、(2) 不過：不自動採用。回報哪幾格變差、差多少，交使用者選：
  - 為了和名單頁一致，仍然採用；
  - 或新賽季頁維持 0.2.5a，並在更新說明註明能力值量尺不同。
- (1) 不過：不採用，新賽季頁維持 0.2.5a。

## 5. 只報告（不影響判定）

- 8 格合併 MAE 差（Y5、Y6 等權）的 bootstrap 90% 區間。
- 拿掉第 2 節第 3 點（賽中映射維持單季、夾 99，只換先驗和 OVR 層）的同一個回測。這組用來看「只換先驗」會不會讓頂端隨場數下修：報告 x0 > 99 的人，在 N = 5、10、20 時的平均 e。
- 依 MPG0 三分位，N = 5、10 的有號平均 e 和 MAE。
- 線上頁（資料截至 2026-10-28，和 0.2.5a 同一份快照）026 對 025 的差異：
  - |ΔOVR| 中位數、最大值，> 10 分的人數；
  - 前 20 名進出；
  - 賽中有屬性 > 99 的人，列出姓名、屬性和值。
- 敏感度 Y3、次要 D1–D3 的 (1)(2) 數字。

## 6. 判定後才做

- 採用時：
  - 預設改成 026，第一個 VERSION 字面值改成 `inseason 0.2.6`（R-023、R-050）。
  - 先跑 `daily_inseason_update.py --dry-run`，再正式發布（L-048、R-031）。
  - 頁面驗收看 season_nav 產出的版本欄（L-050）。
  - season_nav 加一條新賽季 0.2.6 的更新說明，並改掉 card 0.2.6 條目最後一句「新賽季仍用 0.2.5」。
  - 狀態板和 handoff 一起更新（L-034）。
- 不採用時：season_nav 的新賽季說明註明「能力值仍用 card 0.2.5 的單季量尺」。

## 7. 不准

- 不改：
  - `src/`
  - `reports/card-0.2.*/`、`reports/card-0.2.5+E101-crossera/`
  - `v5/tools/`、`v4/tools/` 既有檔的預設行為（只能加 026 分支，其他模式要逐位元不變）
  - E-064、E-095 的回測輸出
  - `prior-2025-26-card022.json`、`usage-2025-26-card024.json`
  - 已發佈的 live 日期資料夾、`publish_state.json`
- 執行前後對唯讀檔做 sha256 核對。
- 輸出只寫 `reports/ovr-inseason-2026-27/e107-card026/` 和第 2 節列出的 live/ 新檔。
- 看到 (1)(2) 結果之後，不改門檻、池、尾巴常數、人群或起點（L-026）。
- 不 commit、不 push、不部署 gh-pages，等 lead 和使用者決定。
- 子程序一律帶 `CREATE_NO_WINDOW`，Python 用 `python -I`。
- 回報照 CLAUDE.md「回報實驗結果」的六段格式，第一行是 `# 總評`。名次和數值變化以 inseason 0.2.5a 為基準，並在句子裡寫明（L-060）。
