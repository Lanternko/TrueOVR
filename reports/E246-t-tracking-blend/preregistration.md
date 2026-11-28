# E-246 預註冊：T 的 21 欄追蹤統計改用本季混合

日期：2026-11-05　狀態：凍結（R-165：Claude 自訂標準直接凍結開跑）

## 問題
球隊評分的 Transformer（E-227 R2-stats 權重，`e229_live`）26 欄統計裡，只有 box 5 欄混本季；hustle 9、rimthree 4、matchup 2、adv 6 共 21 欄全程用 2025-26。
每日流程其實已抓本季這幾類（`data/defense-seventh/2026-27/tracking/`、`data/matchup-source/2026-27/`）。把這 21 欄照 box 同一條規則混入本季，本季每場勝負預測是否不比現行差？

## 臂（權重、超參數、陣容分鐘全部不動，只換特徵表）
- **T0**：現行（21 欄只用 2025-26）。
- **T1**：21 欄全部混本季。
- **T1h**（分支臂）：只混 hustle 9 欄，其他 12 欄照 T0。

## 混合規則（事前定死，不調）
- 與 box 相同：`w = min_cur / (min_cur + 500)`，`值 = w·本季 + (1−w)·2025-26`；2025-26 沒值者以 2025-26 有值球員的均值代（向均值收縮）；本季沒出賽或本季該欄算不出來者只用 2025-26。
- 本季值公式同 `E227 build_data.py`，但不設 200 分鐘門檻（由 w 收縮取代）：
  - hustle：`leaguehustlestatsplayer` 累計 ÷ 本季分鐘 × 36。
  - rimthree：`leaguedashptdefend`（六呎內、三分）的 PCT−NS_PCT；出手 ÷ 分鐘 × 36。該類出手為 0 時該兩欄算不出來。
  - matchup：逐場 `boxscorematchupsv3`（每日 fetch_matchups 已抓）加總比賽日 < d 的場次：對手得分 ÷ partial poss、對手命中 ÷ 出手（leagueseasonmatchups 不吃 DateTo，所以改逐場加總）。
  - adv：`leaguedashplayerstats` Advanced 的 USG、AST%、TS、OREB%、DREB%、TM_TOV%。
- 本季分鐘＝player-games 比賽日 < d 的累計（同 box）。z 分數 mu／sd 照現行（2025-26 表內球員的混合後值）。

## 不偷看未來
- 回測每個比賽日 d 用 `DateTo = d 前一天` 重抓 hustle／rim／three／advanced（四端點已驗證吃 DateTo）；matchup 用逐場檔只加總 < d。
- 線上：每日流程在球隊評分前抓的整季累計（截至前一晚），matchup 同上逐場加總。
- 能力值資料夾、陣容分鐘沿用 E-229b `prep.py` 的規則（三臂相同）。

## 評估
- 場次：player-games／team-games 目前所有已完賽場次（重跑 E-229b prep，三臂同一份）。T 每場 N=2000、5 seed 平均，同 E-229b。
- 主要：Brier（主場勝率 Φ((margin+2.5)/12)）。bootstrap 10000 次、seed 20261105，90% 區間。
- 次要：logloss、預測分差與實際分差相關、MEM／POR 今日評分名次變化（只報不判）。

## 判定
- **採用 T1**：ΔBrier(T1−T0) 平均 ≤ 0，且 90% 上界 < 0.013（E-229 MDE_B，非劣性）。
- T1 未過但 T1h 過 → 報 T1h，由使用者決定。
- 兩者都不過 → 不採用，維持 T0。
- 已知限制：本季才約 8 場／隊，w 最多約 0.3–0.4，預期差異小；結論以「不比現行差」為主，不宣稱顯著變好。

## 已揭露
- 已看過：E-229b 的 T0 結果；MEM／POR 實際分差比模型高（觸發本實驗）。K=500 沿用 E-229 事前值，不因此調。
