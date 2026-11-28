# 卡片 OVR 的資料流追查：遊戲實際讀了什麼

寫於 2026-10-18，為了回答「把 α = 0.5 混合版接進遊戲」要改哪一個檔。
**本文只記錄追查結果與選項，不做採用決定，也沒有改動任何產物。**

## 結論

**可玩的遊戲完全沒有讀取、計算或顯示任何 OVR。** 這六層 OVR 產物沒有一個進入
`src/`、`data/`、`index.html` 或 `calculator.html`。唯一標著「遊戲現用」的地方是
`reports/status/status_snapshot.py` 裡的一個字串標籤，不是任何遊戲程式碼的輸入。

因此「讓遊戲改用混合版」這個動作目前無處可施。見下方「選項」。

## 遊戲執行時實際的資料流

    index.html
      └─ src/courtside.css
      └─ src/courtside.js        （type="module"）
           ├─ src/teams.js       ← 25 張卡、每張 16 個屬性
           └─ src/simulation_engine.js

    calculator.html
      └─ import { TEAMS, BASELINE, SMALLBALL, BIGBALL } from './src/teams.js'
         import { monteCarlo, simulateGame } from './src/simulation_engine.js'
         import { LEAGUE_TARGETS as T } from './src/constants.js'

查證（全部為全庫 grep 與逐檔閱讀）：

| 檔案 | 查什麼 | 結果 |
|---|---|---|
| `index.html`（27 行） | `ovr\|rating\|overall` | 0 筆 |
| `src/courtside.js` | `ovr\|overall\|rating\|cost\|費用\|星級` | 0 筆 |
| `src/teams.js` | 卡片欄位 | 16 個屬性（long, mid, short, ft, drive, tovSkill, pass, rebound, onBall, help, stamina, physique, offBall, screen, handle, breakDbl），**無 ovr 欄** |
| `calculator.html`（210 行） | `ovr` | 只出現在 `<title>` 與 `<h1>`（「OVR 計算器」）；腳本顯示屬性與模擬輸出，**不算 OVR** |
| `data/season-league.json` | 球員欄位 | 屬性、`shotProfile`、`seasonMinutesPerGame`、`observed`、`missingMeasurements`，**無 ovr 欄** |
| `data/card-costs.json` | 來源 | 自述 `"docs/卡牌設計.md §2 existing costs; diagnostics only, never rating inputs"`，25 個手設費用，不由任何 OVR 推導 |

`src/teams.js` 的檔頭是「teams.js — 測試卡表（自動產生，勿手改；改 gen_teams.mjs）」，
產生器也不寫入 OVR。

## 六層 OVR 產物，與它們各自的消費者

| # | 產生者 | 產物 | 誰讀它 |
|---|---|---|---|
| 1 | `scripts/validate_strength.js`（入口 `test/ovr.js`、`npm run validate:strength`） | `reports/strength-validation.{md,json}` | 無程式消費者。文件上這是**正式 OVR**（對 `data/benchmark-league.json` 固定對手池的勝率映射），但基準自 2026-10-12 起被標為失效待重建，且**不在 `npm test` 裡** |
| 2 | `reports/ovr-v53-2025-26/` | `calibration-target-s8-expected.csv` | 第 3、4 層的校準目標 |
| 3 | `reports/ovr-calibrated-2025-26/calibrate.py` | `ranking.csv`、`summary.json`（含 `formula` 區塊） | `reports/status/status_snapshot.py`（標為「遊戲現用」）、`reports/impact-rapm/rapm.py`（`calibratedOVR` 比較欄）、`reports/ovr-shrinkage-2025-26/evaluate.py` |
| 4 | `reports/ovr-blended-2025-26/blend.py` | `ranking.csv`、`summary.json`（**無** `formula` 區塊） | `reports/status/status_snapshot.py`（標為「未接進遊戲」） |
| 5 | `reports/ovr-final-2025-26/build.py` | 真實球員 OVR（box-prior RAPM） | `reports/ovr-card-2025-26/fit.py` 取其 `scaleAnchorsNetPer100` 與 `ranking.csv` |
| 6 | `reports/ovr-card-2025-26/fit.py` | `formula.json` | 唯一「能給任意卡片打分」的產物。目標是 `reports/impact-rapm/rapm-prior.csv` 的 lastSeasonNet/O/D，**不是 sim 目標** |

`scripts/legacy_net_ovr.js` 是已廢棄的淨分差 OVR，文件明示不得用作正式 OVR。

重點：**第 6 層不在第 3 層的下游。** 它只向 `calibrate.py` 借用 `design`、`attach_creation`、
`ATTRS`、`INTERACT`、`POS` 這些程式碼，校準目標是 RAPM 先驗。它的 `report.md` 寫「只適用於
虛構卡片。真實球員請用最終 OVR（`reports/ovr-final-2025-26`）」，`formula.json` 選的形式是
`linear`、14 個屬性（不含 `pressure`）。

## 兩層文件上的 OVR 定義並不相同

- `docs/OVR與球隊PR基準.md`：正式 OVR = 對固定對手池的**勝率**兩段映射
  （全 40 → 40、全 70 → 70、全 99 → 99），走 `data/benchmark-league.json`。
  帶 2026-10-12 的更正：舊基準失效，待重建。另註「卡片費用不進入模擬或映射」。
- `calibrate.py` / `blend.py`：OVR = 屬性的加權 ridge 迴歸預測的每 36 分鐘價值，
  再以 MIN ≥ 500 球員的 PR1 = 40 / PR50 = 70 / PR99 = 99 映射。

這兩套東西都叫 OVR，但不是同一個量，也沒有互相校準。
派工單說的「遊戲現用的 OVR」指的是後者（因為「遊戲現用」這個標籤只出現在
`status_snapshot.py` 的第 3 層那一列），但前者才是文件上的正式定義。

## 為什麼在此停下

派工單的任務 A 第 5 點：「若追查後發現遊戲根本沒讀這些 OVR，或接法有設計上的分歧
（例如 fictional cards 那條 fit.py 也要不要跟著改），**先停下**，回報資料流和選項，
不要自己決定。」

兩個條件同時成立：

1. 遊戲沒讀這些 OVR（上面的表）。
2. `fit.py` 那條存在設計分歧——它的目標已經是 RAPM 先驗，某個意義上「比 α = 0.5 更 RAPM」，
   所以「跟著改成混合版」對它不是一個定義明確的動作。

所以任務 A 的第 2、3、4、6 步（改產生流程、改 `status_snapshot.py` 標籤、重跑、寫
`adoption.md`）都沒有執行。驗收條件裡「遊戲實際使用的 OVR 切換為 α = 0.5 混合」本輪無法達成。

## 選項（待決定）

**A. 只改標籤。** `status_snapshot.py` 的「遊戲現用」指向 `ovr-blended-2025-26/ranking.csv`，
舊的第 3 層保留為「舊版（純 sim）」。
成本最低，但由於沒有遊戲程式碼消費這一列，這純粹是審查表的標籤變更——
把一個不準確的標籤換成另一個方向不同、同樣不準確的標籤。

**B. 讓混合版成為正式卡片板。** 給 `calibrate.py` 加 `--alpha`（或讓 `blend.py` 在選定的 α 上
輸出 `formula` 區塊），用它重新產生 `reports/ovr-calibrated-2025-26/` 的產物，
`status_snapshot.py` 自然跟著改。這才是「重用既有產生流程、不手改產物」的做法，
也讓第 3 層的 `summary.json` 繼續有 `formula` 區塊可用。代價是第 3 層的歷史產物被覆寫
（可改用 `--out` 寫到新目錄避開）。

**C. 連虛構卡片那條一起改。** 需要先決定 `fit.py` 的目標要變成什麼。
它現在是 RAPM 先驗（lastSeasonNet），不是 sim；要「混合」得先定義和什麼混合。
這是派工單點名的分歧，建議單獨一輪處理。

**D. 真的把 OVR 顯示進遊戲。** `src/teams.js` 加 `ovr` 欄或在 `calculator.html` 計算顯示。
這是新功能，不在本次派工範圍。還要先解決上面「兩層 OVR 定義不同」的問題——
要顯示的是勝率 OVR 還是迴歸 OVR。

建議順序：先決定 B 或 A（B 才有實質內容），C 另開一輪，D 需要先統一 OVR 定義。

## 本輪已驗證的基準

`npm test` 在未改動的工作樹上通過：`===== 57 passed, 0 failed =====`，
加上 timed_game 的 60 場全場測試（accounting、rotation、clock、FT、assists、overtime、
replay、legacy parity 全過）。離開碼 0。
