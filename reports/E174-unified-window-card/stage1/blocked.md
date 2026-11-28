# E-174 階段 1 受阻（blocked）

日期 2026-11-01。未建任何屬性表、未改任何凍結檔、未寫 scripts/card_window.py。

## 卡住的原因
errata-2 §3 要求「S 臂（u=1、只有 t 季）重現 0.2.9a，每屬性 |diff|≤0.1 的人 ≥99%」。但 0.2.9a 的屬性演算法（V61／E-070：`reports/ovr-v61-shrink-history-2025-26/build_attrs.py`、`backtest.json` production，全部屬性 selected = 'c'）把每個比率往「前 3 季歷史目標 T」拉回：
`rate = (n + k·T)/(d + k)`，`T = (Σ λ^(j-1)·n_j + kh·m)/(Σ λ^(j-1)·d_j + kh)`（j=1 是最近一季）。
S 臂只有 t 季，定義上沒有歷史項（T 退化成 m），所以和 0.2.9a 官方值本質上就不同；這不是公式寫錯，是規格內部衝突。

另外兩點同樣讓 2025-26 重現做不到：
- errata-2 規定映射用「t 季自己的單季池」，但 0.2.9a 的 pressure（E-123 合併四季池）、drive（E-101）用的是合併池與凍結的 2025-26 值。
- 0.2.9a 的 long/mid/short/ft/drive/tovSkill/pass/rebound/foulDraw 來自 E-070／V61 管線（pergame、pbp-zones、pbp-drive 的 history/ 檔），不是 `season_attrs_v4.compute_attrs`（後者與 `card-0.2.9a/ranking.csv` 比，mid／short／ft／drive 在 0.1 內的人只有 0.3%–6%）。

## 可行性實測（只量差距，未擬合，不是最終重現檢查）
2025-26 全季資料、不帶歷史（T＝聯盟平均）、用 production 的 k，池內百分位映射，對 `attributes-new.csv` 的 new_ 值：

| 屬性 | |diff|≤0.1 的比例 | 最大差 | 中位差 |
|---|---|---|---|
| foulDraw | 3.3% | 25.9 | 2.43 |
| pass | 7.4% | 24.3 | 1.17 |
| rebound | 8.8% | 24.7 | 1.41 |
| tovSkill | 2.6% | 30.2 | 3.46 |

離 99% 門檻很遠，且差異來源（歷史目標）是結構性的。

## 需要使用者／lead 裁定（errata-3）
A. S 臂的「0.2.9a 重現」改定義為：同一個 V61 管線但把歷史項關掉（T＝m），對照基準由「0.2.9a 官方卡」改成「V61 管線無歷史版」；另需決定 2025-26 的 pressure／drive 池要用單季池還是 E-123／E-101 合併池。
B. 或承認 U 臂窗口本身就取代 V61 的 3 季歷史目標（窗口加權＝歷史），則 S 臂與 0.2.9a 不必重現，重現檢查改成 U 臂在 t 季＝只有單季時退化為 S 的一致性檢查。
C. 另外 2025-26 需 pbp 的屬性：`history/pbp-*-2025-26.csv.gz` 已存在，不必用官方卡值直接替代；errata-1 這一條是否仍要照做也請確認。

在裁定前不繼續建表（避免為過關而改公式）。
