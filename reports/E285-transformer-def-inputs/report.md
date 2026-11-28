# E-285 報告：Transformer 輸入加逼失誤與有球／無球／一般犯規

預註冊 `prereg.md`（sha256 見 prereg.sha256，訓練前凍結）。5090 `~/side_projects/pure_ovr/experiments/e285/`。

## 輸入
E-227 R2-stats 41 欄原本就有 stl36、deflections36、charges36、pf36、blk36、pressure；本次新增 4 欄（逐季）：mtov36、fOn36、fOff36、fGen36（`build_extra.py`）。兩臂同程式、同 seed 0–4 在 5090 重訓。

## 驗收（測試＝5 季 split=test；前向＝2026-27 用 2025-26 特徵）
| | 基準 R2-stats | R2-statsX | Δ（90% 區間） |
|---|---|---|---|
| 測試淨值 MSE | 10063.71 | 10061.09 | −2.63（−4.67, −0.44）✓ |
| 前向淨值 MSE | 11633.38 | 11627.29 | −6.10（−12.61, +0.87）✓ |
| 測試比賽 Brier | 0.20172 | 0.20202 | +0.0003 ✗ |
| 前向比賽 Brier | 0.20246 | 0.20043 | −0.0020 |
| 測試 ptsSide／tovLL／orbLL | | | +0.00006／−0.00001／+0.00012 ✓（≤ +0.0002）|

條件 1、2、4 成立，條件 3（測試 Brier Δ ≤ 0）差 0.0003 不成立 → 依預註冊**不是採用候選**。測試 MSE 改善 90% 區間不含 0，但遠小於 E-227 的 MDE 15.36。
5 seed 測試 MSE：基準 10050–10082、X 10053–10077（seed 間差距比兩臂差大）。

排列重要性（測試 MSE 上升）：mtov36 +3.3、fGen36 +2.3、fOn36 −0.6、fOff36 −0.3（後兩者沒用）；新 4 欄一起 +4.5。對照 stl36 +12.6、charges36 +2.1、pressure +1.5、blk36 +0.9。

## 換人值名次（2025-26 ≥1000 分鐘 276 人，4000 組抽樣）
兩臂 Spearman：淨 0.990、防守 0.984、進攻 0.993；平均名次移動 淨 8.3／防守 10.0。
| 球員 | 淨（基準→X） | 防守（基準→X） |
|---|---|---|
| Wembanyama | 1→1 | 1→1 |
| Jokić | 5→4 | 202→176 |
| Jarrett Allen | 9→7 | 8→6 |
| Curry | 11→15 | 117→111 |
| Hartenstein | 12→13 | 4→5 |
| Amen Thompson | 24→17 | 17→15 |
| Durant | 27→18 | 135→107 |
| Gobert | 45→34 | 12→11 |
| Adebayo | 90→74 | 50→27 |
| Brook Lopez | 208→208 | 63→48 |
| JJJ | 132→117 | 51→57 |
防守上升：Jamal Shead 124→73、Sion James 120→72、Dončić 92→58、Ronald Holland 53→25；下降：Gafford 69→110、Kornet 65→100、Poeltl 98→127、Luka Garza 174→224。
細表 `ranking.csv`、`rank-summary.json`；評估 `results/eval.json`。
