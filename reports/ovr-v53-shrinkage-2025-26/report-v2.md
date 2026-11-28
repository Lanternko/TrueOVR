# v53 收縮修正版（先發不收縮）：結果

預註冊見 `preregistration-v2.md`。執行：`python reports/ovr-v53-shrinkage-2025-26/shrink_v2.py`。
完整數字在 `summary-v2.json`，排名在 `ranking-v2.csv`。第一版結果見 `report.md`。

## 結論：四關全過，依預註冊採用

| 關卡 | 原始 | 第一版 | 修正版 | 通過 |
|---|---:|---:|---:|---|
| G1 全體平方誤差下降（95% CI） | — | 1.71 | 1.82 [0.62, 3.36] | ✓ |
| G1 m < 20（293 人）下降（95% CI） | — | 3.48 | 3.62 [1.22, 6.56] | ✓ |
| G1 m ≥ 20（289 人）下降 | — | −0.079 | 0（依設計） | — |
| G2 RAPM 淨值 ρ（414 人） | 0.363 | 0.413 | 0.398 | ✓ |
| G2 RAPM 防守 ρ | 0.256 | 0.277 | 0.276 | ✓ |
| G3 前 50 名 W < 500 人數 | 24 | 9 | 10（上限 12） | ✓ |
| G4 先發之間 Spearman | — | — | 1.000 | ✓ |

修正版對替補的預測，比第一版略好（3.62 對 3.48）。原因是 10–20 分鐘的過渡區收縮得比較少。

## 附帶報告

| 指標 | 原始 | 第一版 | 修正版 |
|---|---:|---:|---:|
| RAPM 淨值 ρ（≥ 1000 回合，513 人） | 0.363 | 0.427 | 0.412 |
| RAPM 防守 ρ（≥ 1000 回合） | 0.244 | 0.265 | 0.266 |
| 對半可靠度（Spearman–Brown） | 0.784 | 0.882 | 0.870 |
| 媒體共識 ρ | −0.389 | −0.397 | −0.390 |

- 先發的全榜名次中位數變動 27、最多 41。他們的分數不變，名次上升是因為替補退出前段。
- 從前 50 名外被拉進前 50 名的非先發只有 3 位：Javonte Green、Goga Bitadze、Kenrich Williams。
- 外部 ρ 比第一版低 0.01–0.015，這是不收縮先發的代價。

焦點球員（原始 → 第一版 → 修正版）：

| 球員 | 原始 | 第一版 | 修正版 |
|---|---:|---:|---:|
| Tosan Evbuomwan | 1 | 520 | 494 |
| Thanasis Antetokounmpo | 3 | 231 | 234 |
| Caleb Houstan | 4 | 149 | 158 |
| Jonathan Mogbo | 5 | 116 | 138 |
| Charles Bassey | 15 | 39 | 36 |
| Shai Gilgeous-Alexander | 2 | 1 | 1 |
| Victor Wembanyama | 11 | 5 | 5 |
| Nikola Jokić | 16 | 6 | 8 |
| Alex Caruso | 78 | 72 | 58 |
| Dyson Daniels | 115 | 68 | 84 |
| Derrick White | 142 | 97 | 106 |

修正版前 10：Shai Gilgeous-Alexander、Kawhi Leonard、Giannis Antetokounmpo、Ty Jerome、Wembanyama、Dončić、
Mitchell Robinson、Jokić、Zach Edey、Evan Mobley。

前 50 名仍有 10 位 W < 500：Ty Jerome、Edey、Kessler、Blake Hinson、Thybulle、Cormac Ryan、Bassey、
Alondes Williams、Myron Gardner、David Roddy。其中 Ty Jerome、Edey、Kessler 模擬上場 ≥ 20 分鐘，
依規則不收縮。他們的高排名來自模擬本身，不是小樣本雜訊。

## 限制

- 修正版不是盲測：規則的設計看過第一版的結果。預註冊只鎖定修正版的規則與關卡。
- 長人仍然偏多：前 30 名有十多位 C/PF。這是模擬的問題，收縮處理不到。
- 範圍只到排名後處理。卡片校準目標要不要改用修正版板，另案處理。
