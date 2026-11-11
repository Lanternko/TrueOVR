# v53 模擬板可靠度收縮：結果

預註冊見 `preregistration.md`（執行前寫成）。執行：`python reports/ovr-v53-shrinkage-2025-26/shrink.py`。
完整數字在 `summary.json`，收縮後排名在 `ranking.csv`。

## 結論：依預註冊不採用

| 關卡 | 結果 | 通過 |
|---|---|---|
| G1 全體平方誤差下降 | 7.876 → 6.165，下降 1.71，95% CI [0.52, 3.30] | ✓ |
| G1 m ≥ 20 分鐘不得變差 | 289 人，1.652 → 1.731，下降 −0.079 | ✗ |
| G2 RAPM 淨值 ρ（≥ 5000 回合，414 人） | 0.363 → 0.413 | ✓ |
| G2 RAPM 防守 ρ | 0.256 → 0.277 | ✓ |
| G3 前 50 名 W < 500 人數 | 24 → 9（上限 12） | ✓ |

G1 的第二個條件沒過，因此三關沒有全過，不採用收縮板。

## 擬合

- τ² = 3.73（每 36 分鐘），κ = 96.7。來源小樣本雜訊等於訊號的位置大約在來源 26 分鐘。
- 中位收縮係數 B：模擬上場 < 10 分鐘 0.36，10–20 分鐘 0.66，≥ 20 分鐘 0.83。

## 附帶報告

- pooledPoss ≥ 1000（513 人）：淨值 ρ 0.363 → 0.427，防守 ρ 0.244 → 0.265。
- 兩半排名的 Spearman–Brown 可靠度：0.784 → 0.882。
- 與季前媒體共識的 ρ：−0.389 → −0.397，幾乎沒變。負號來自排名的編碼方向。
- 以上分鐘加權的平方誤差下降為 +0.41。

焦點球員（原排名 → 收縮後排名）：

| 球員 | 原 | 收縮 |
|---|---:|---:|
| Tosan Evbuomwan | 1 | 520 |
| Thanasis Antetokounmpo | 3 | 231 |
| Caleb Houstan | 4 | 149 |
| Jonathan Mogbo | 5 | 116 |
| Charles Bassey | 15 | 39 |
| Shai Gilgeous-Alexander | 2 | 1 |
| Victor Wembanyama | 11 | 5 |
| Nikola Jokić | 16 | 6 |
| Alex Caruso | 78 | 72 |
| Dyson Daniels | 115 | 68 |
| Derrick White | 142 | 97 |

收縮後前 10：Shai Gilgeous-Alexander、Kawhi Leonard、Giannis Antetokounmpo、Luka Dončić、Wembanyama、
Jokić、Ty Jerome、Zach Edey、Mitchell Robinson、Evan Mobley。

前 50 名仍有 9 位 W < 500：Ty Jerome、Edey、Walker Kessler、Blake Hinson、Myron Gardner、
Jeremy Sochan、Bassey、Matisse Thybulle、Cormac Ryan。

## 為什麼先發變差

B 因人而異。來源分鐘少的先發（傷病、季中加入）被拉向角色先驗的幅度較大，先發之間的相對位置因此改變，
另一半種子的 x 不支持這個改變。

事後探索（**不是關卡，不改變上面的結論**）：把 κ 固定為 0，只收縮蒙地卡羅雜訊。
這時 m ≥ 20 的平方誤差下降是 −0.003，CI [−0.125, 0.130]，全體下降 1.81。
這表示先發的損失主要來自 κ 項。不過，G1 的設計本來就不會獎勵 κ（兩半共用來源樣本），
所以「κ = 0 在 G1 表現較好」並不代表 κ 是錯的。G3 的替補改善主要靠 κ。
要採用任何變體，必須另寫預註冊。

## 範圍

只做排名後處理，沒有改模擬、卡片公式或遊戲資料。
