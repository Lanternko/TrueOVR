# E-175 步驟 1：0.2.9a 每個屬性的實際算法（L-093）

寫這份時還沒看任何 U 對 V 的比較數字。路徑都相對 repo 根目錄；行號是 2026-11-01 工作樹上的行號。
0.2.9a 的能力值欄 ＝ `reports/card-0.2.9a/build_card_029a.py:1-8` 拷自 0.2.9（能力值逐位元相同）＝ E-164 ＝ …＝ `reports/card-0.2.7+E125-pass-volume/attributes-P50.csv`（`build_e101_p.py 0.5`）。
實測：`attributes-P50.csv` 與 `…/rebase-027a/work/tail-e123a.csv` 的 long、mid、short、ft、drive、foulDraw、tovSkill、pass、rebound、physique、onBall、creation 12 欄最大差 0.0；對 `card-0.2.9a/ranking.csv` 最大差 0.05（四捨五入）。pressure 與 presDisplay 後來被 E-123 換掉（窗口，不在本實驗）。

## 0. 共同鏈

```
逐場 (分子, 分母)  →  V61 方法 c 收縮比率 rn  →  [foulDraw、pass：加量價分量的組合]  →  E-101 合併池映射 → 屬性值（40–99，尾端可到 150）
```

| 步驟 | 檔:行 |
|---|---|
| 分子／分母定義、H1／H2 分段 | `reports/ovr-v61-shrink-history-2025-26/engine.py:78-134`（`season_halves`；box 屬性 :90-95，mid／short :98-108，drive :109-132） |
| 每場可助攻／可搶板機會 astCh、rebCh | `…/prepare_pergame.py:66-72` |
| 歷史目標 T 與收縮 | `engine.py:186-194`（`hist_target`、`pred_c`）；`build_attrs.py:80-87`（`shrink`，生產用） |
| 2025-26 季末生產值（全季分子分母、卡片名單的聯盟／位置先驗） | `build_attrs.py:180-232`（箱型＋射擊類）、`:234-290`（drive） |
| 生產用參數 | `…/backtest.json` 的 `production`（方法 c；mid／short 先驗被 E-101 改為聯盟，見下） |
| 合併池映射 | `reports/card-0.2.7+E125-pass-volume/work/build_e101_p.py:70-149`（`Pool`、錨點、尾端）、`:183-200`（池）、`:239-285`（`build`） |
| 尾端開關 | `reports/card-0.2.4+E090-onball-tail/h1-results.json`、`reports/card-0.2.5+E101-crossera/h1-results.json`（mid、short 用後者） |

收縮式：`rate = (n_t + k·T)/(d_t + k)`，`T = (Σ_{j=1..3} λ^{j-1} n_j + kh·m)/(Σ λ^{j-1} d_j + kh)`，j=1 是最近一季的全季量；m ＝聯盟或同位置比率（`prior`）。
2025-26 季末那一刻 `n_t, d_t` ＝ 全季量；比率→屬性值的映射使用 2025-26 卡片池＋2022-23..2024-25 過去季的凍結池值（`reports/card-0.2.7+E125-pass-volume/pool-P50/raw-<季>.json`）。

## 1. V61 的 8 項

| 屬性 | 分子 / 分母（每場） | 參數（backtest.json production，方法 c） | 比率→屬性值 |
|---|---|---|---|
| ft | FTM / FTA | k=128, kh=64, λ=0.5, 位置先驗 | `CURVE_FT` 反函數；頂端開關 H1；池＝MIN≥500（`build_e101_p.py:193-200`, `:263-285`） |
| mid | PBP 中距離命中 / 出手（**E-101 修正分區**，`reports/card-0.2.5+E101-crossera/history/pbp-zones-*.csv.gz`） | k=181.02, kh=128, λ=1.0；**先驗改聯盟**（`a0_e101.py:57-60`，E-101 改動一） | 歷史目標在 PBP 尺度算好，再平移「聯盟 shots.json 命中率 − 聯盟 PBP 命中率」搬到卡片尺度（`build_attrs.py:194-210`）；分子分母用 `data/benchmark-source/shots.json` 全季；`CURVE_MID` 反函數＋尾端 |
| short | PBP 禁區＋油漆區非禁區命中 / 出手（同上） | k=181.02, kh=128, λ=0.5；先驗改聯盟 | 同 mid，`CURVE_SHORT`；再乘每人 E2 折扣 `70+(v−70)·discountFactor`（`build_e101_p.py:283-284`） |
| foulDraw | 組合 0.75·z(vol) + 0.25·z(rate)：rate＝FTA / FGA（k=181.02, kh=64, λ=0.5, 位置）；vol＝FTA / (MIN/36)（k=8, kh=4, λ=0.35, 位置，`reports/card-0.2.0+E070-foul-volume/vol-fit.json`） | | 組合分數取池內百分位（池＝base GP≥30 且 MPG≥20，`e070_vol.py:83-93`），再走合併池映射＋尾端 |
| tovSkill | TOV / (FGA + .44·FTA + AST + TOV)，**取負號**後取百分位 | k=724.08, kh=256, λ=0.35, 聯盟先驗 | 百分位型＋尾端 |
| pass | 組合 0.5·z(astvol) + 0.5·z(rate)：rate＝AST / astCh（k=128, kh=128, λ=0.65, 位置）；astvol＝AST / (MIN/36)（k=5.66, kh=8, λ=0.5, 位置，`reports/card-0.2.7+E125-pass-volume/astvol-fit.json`） | | `a0_p.py:98-106`；組合分數取百分位＋尾端 |
| rebound | REB / rebCh | k=512, kh=512, λ=1.0, 位置先驗 | 百分位型＋尾端 |
| drive | 兩分量：driveVol＝未助攻突破出手加權數 / 出賽分鐘（×36），driveEff＝突破得分 / 加權出手數；失手權重＝該類別未助攻進球比例（只用 H1 場）。各自收縮：vol k=90.51, kh=32, λ=0.5, 位置；eff 同 k、kh、λ，位置。**只用前 41 場（H1 574 場）**（`build_attrs.py:234-290`） | | 分數 0.5·z(vol)+0.5·z(eff)（池內 z；池＝GP41≥15 且 MPG41≥20），百分位＋尾端；沒有突破資料者 70 |

zs 的標準差是母體（ddof=0）；組合的池＝`bench base` 的 GP≥30 且 MPG≥20 且在卡片名單內者。

## 2. 不在 V61 清單的屬性（0.2.9a 怎麼算）與 U 版

U 版一律是：分子分母改成跨季窗口加權和（過去季＝季總量×`window_weights` 該季權重，本季＝逐場 u），再用 `(n_w + k·m)/(d_w + k)` 收縮到 m。這裡只寫規格；§2 不評，§3 OVR 層只用 8 項。

| 屬性 | 0.2.9a 現在 | U 版 |
|---|---|---|
| long | `scripts/build_season_league.js:110,114,117`：`p = (FG3M + 100·聯盟三分%)/(FG3A + 100)`，只用本季全季，`CURVE_3PT` 反函數，E-101 合併池＋尾端（`attributes-P50.csv`） | n_w＝窗口加權 FG3M，d_w＝窗口加權 FG3A，k=100，m＝本季聯盟三分% |
| physique | 身高(吋)＋體重(磅)/10 的百分位（`build_season_league.js:86-87,123`）；不隨時間變 | 不變（不是比率） |
| creation | `(1−creationDependence_sourceRole)·FGA/MIN·36` 百分位（`reports/card-0.2.0+E071-pressure/calibrate-wing.py:104,117`） | FGA/MIN 的窗口版；creationDependence 是外部來源的角色係數，維持現值 |
| onBall | R-076 四季窗口（`reports/ovr-inseason-2026-27/live/rookie_defense.py:241-262`；0.2.9a 季末：E-060 的 zC3+zB−zT） | 已是窗口，不比 |
| help、pressure、presDisplay、防守加成 | R-076、R-110 窗口 | 已是窗口，不比 |
| stamina | 0.2.9a 已拿掉（R-107） | — |

## 3. 重現（步驟 1 的判定）

本實驗自己寫的 V 臂程式（`e175_lib.py`、`e175_card.py`、`repro.py`，不 import V61 的 engine／build_attrs）：
- 輸入：V61 `history/pergame-*.csv.gz`、E-101 `history/pbp-zones-*.csv.gz`、V61 `history/pbp-drive-*.csv.gz`、`positions.csv`、E2 league JSON（名單、位置）、折扣 log、`data/benchmark-source/{base,shots}.json`、生產參數、凍結池值與開關。
- 結果見 `repro-result.json`／`repro.log`：582 人 × 8 項＝4656 格，|差| ≤ 0.1 的比例 100%（最大差 0.0500，來自 ranking.csv 四捨五入）；對全精度 `tail-e123a.csv` 最大差 1.6e-5。
- 比率層：ft、tovSkill、rebound 對 E-090 `a0-raw.json` 的 `p`／`r` 最大差 ≤ 1.1e-16；mid、short 的 a0-raw 是 V61 分區＋位置先驗，0.2.9a 改用 E-101 分區＋聯盟先驗，所以刻意不同。
