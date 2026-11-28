# E-305 RIM（護框）欄加蓋帽：結果

預註冊 `prereg.md`（commit 1c21849，早於本結果）。腳本 `e305_rim_blk.py`，原始數字 `results.json`。2026-27 資料截止 2026-11-08（146 場，c=9.73）、名次人群 289 人（本季場均 ≥ 15 分鐘）；2025-26 卡片頁 400 人。blk36 沒有缺值（人群內 0 人補平均）。

## 判定（預註冊驗收 1／2）
Δρ＝該臂 Spearman 減 B0；< −0.02 算變差。2026-27 的 EPM 防守與 T 換人 DEF 各四項（全體／PF·C）、2025-26 的 EPM 兩項，全部要沒變差才過 2。

| 臂 | 驗收1 Wemby 第1且領先≥5 | live 領先差 | 驗收2 沒變差 | 變差項 | PF/C 對 EPM ρ（live） | 通過 |
|---|---|---|---|---|---|---|
| B0 | 否（Stewart 第1，Wemby 第2，差 3.1） | — | — | — | 0.4161 | — |
| D30 | 是 | 8.14 | 是 | — | 0.4 | **過** |
| D50 | 是 | 14.11 | 否 | 2026-27:EPM_D/PFC, 2026-27:T_DEF/PFC | 0.3909 | 不過 |
| D70 | 是 | 18.74 | 否 | 2026-27:EPM_D/PFC, 2026-27:T_DEF/PFC | 0.3809 | 不過 |
| DV | 是 | 6.23 | 否 | 2026-27:EPM_D/PFC, 2026-27:T_DEF/PFC | 0.3652 | 不過 |

**選臂（凍結規則：通過 1、2 者取 PF/C 對 EPM 防守 ρ 最高，並列取 D50）：D30。** 只有 D30 通過。

### Δρ 明細（臂 − B0）

| 臂 | 26-27 EPM 全體 | 26-27 EPM PF/C | 26-27 T 全體 | 26-27 T PF/C | 25-26 EPM 全體 | 25-26 EPM PF/C |
|---|---|---|---|---|---|---|
| D30 | +0.0262 | -0.0161 | +0.0270 | -0.0143 | +0.0431 | +0.0216 |
| D50 | +0.0452 | -0.0252 | +0.0426 | -0.0228 | +0.0789 | +0.0267 |
| D70 | +0.0561 | -0.0352 | +0.0460 | -0.0286 | +0.1074 | +0.0331 |
| DV | +0.0159 | -0.0509 | +0.0278 | -0.0393 | +0.0622 | -0.0061 |

B0 絕對值（26-27）：EPM 全體 0.4181、PF/C 0.4161（n=104）；T 全體 0.5876、PF/C 0.5253。25-26：EPM 全體 0.3464、PF/C 0.3836。2025-26 沒有 T 換人值，T 項略過。

## Stewart 與 Wembanyama 前後值（2026-27，RIM 顯示值／名次）

| 臂 | Wembanyama | Isaiah Stewart |
|---|---|---|
| B0 | 109.5（#2） | 112.6（#1） |
| D30 | 116.0（#1） | 107.9（#2） |
| D50 | 119.7（#1） | 103.9（#3） |
| D70 | 122.8（#1） | 99.5（#8） |
| DV | 111.4（#1） | 102.8（#4） |

2025-26 卡片頁：B0 Wemby 108.7（#3）／Stewart 113.5（#1）；D30 Wemby 117.6（#1）／Stewart 110.0（#3）。

## RIM 前 20：B0 vs D30（2026-27，名次人群）

| 名次 | B0 | 顯示值 | D30 | 顯示值 | D30 的 blk36 |
|---|---|---|---|---|---|
| 1 | Isaiah Stewart | 112.6 | Victor Wembanyama | 116.0 | 3.91 |
| 2 | Victor Wembanyama | 109.5 | Isaiah Stewart | 107.9 | 2.03 |
| 3 | Chet Holmgren | 107.4 | Chet Holmgren | 106.7 | 2.5 |
| 4 | Donovan Clingan | 101.1 | Donovan Clingan | 101.6 | 2.4 |
| 5 | Ryan Kalkbrenner | 96.9 | Walker Kessler | 99.3 | 2.77 |
| 6 | Walker Kessler | 95.2 | Jay Huff | 98.6 | 2.73 |
| 7 | Rudy Gobert | 95.0 | Ryan Kalkbrenner | 97.6 | 2.23 |
| 8 | Jay Huff | 94.5 | Daniel Gafford | 96.1 | 2.52 |
| 9 | Ivica Zubac | 93.8 | Robert Williams III | 95.5 | 2.68 |
| 10 | Neemias Queta | 92.8 | Rudy Gobert | 93.6 | 1.75 |
| 11 | Evan Mobley | 92.7 | Brook Lopez | 93.5 | 2.13 |
| 12 | Daniel Gafford | 92.6 | Khaman Maluach | 92.7 | 2.06 |
| 13 | Luke Kornet | 92.2 | Neemias Queta | 92.3 | 1.8 |
| 14 | Brook Lopez | 92.0 | Dylan Cardwell | 92.2 | 2.27 |
| 15 | Khaman Maluach | 91.5 | Evan Mobley | 92.0 | 1.77 |
| 16 | Robert Williams III | 90.6 | Luke Kornet | 91.3 | 1.72 |
| 17 | Jaren Jackson Jr. | 90.4 | Alex Sarr | 90.8 | 2.11 |
| 18 | Dylan Cardwell | 89.2 | Yves Missi | 90.8 | 2.19 |
| 19 | Alex Sarr | 88.4 | Myles Turner | 90.8 | 2.32 |
| 20 | Anthony Davis | 87.9 | Jaren Jackson Jr. | 90.6 | 1.82 |

### 前 15 名人工檢查（D30）
- 前四名 Wembanyama、Stewart、Holmgren、Clingan 與 B0 同一批，只是 Wembanyama 從第 2 升第 1（116.0 vs Stewart 107.9，領先 8.1）。
- 上升：Kessler 6→5、Huff 8→6、Gafford 12→8、Robert Williams III 16→9、Brook Lopez 14→11、Maluach 15→12——都是蓋帽量高的護框長人，合直覺。
- 下降：Gobert 7→10（blk36 只 1.75，他的護框靠籃下命中差，不靠蓋帽）、Kalkbrenner 5→7、Mobley 11→15、Kornet 13→16。Gobert 掉出前 8 是蓋帽權重的代價，不算明顯錯誤，但使用者可能會問。
- 明顯反直覺者：沒有人從前 15 掉到不合理位置；Stewart 仍第 2（help 本身 112.6，blk36 縮收後只有 2.03），這是 help 原值太高的結果，D30 只把他拉回 Wemby 後面。Zubac（B0 第 9，blk36 1.22）掉出前 20。
（25-26 卡片頁 D30 前 3＝Wembanyama 117.6、Holmgren 112.0、Stewart 110.0。）

## 說明與限制
- 顯示轉換：合成分數在人群內重標準化，再套 B0 人群的平均與標準差（B0 恆等於現值）。預註冊寫的「百分位→display_scale」不適用，因為 `help` 線上顯示是 ranking.csv 原值、不是百分位型（`RESCALE_ATTRS` 不含 help），已在 prereg.md 說明。
- 窗口與縮收：季權重同 help 的 `window_weights`（本季權重 0.49、2025-26 0.42、2024-25 0.30、2023-24 0.17、2022-23 0.05），每人除以自己有資料季的最大權重；blk36 向人群平均縮收（K=200 分鐘）。DV 的第三成分是 2 分球 contest／36（stats csv `cont2pt36`、hustle `CONTESTED_SHOTS_2PT`），不限籃下，只是代理。
- **D50／D70 只輸在 2026-27 的 PF/C 子群**（Δρ −0.025／−0.035，D50 差 0.005 過線）。2026-27 只有 10 場，EPM 防守與 T 值噪音大；2025-26 全季的 PF/C Δρ 隨蓋帽權重上升（D30 +0.022、D50 +0.027、D70 +0.033），全體 ρ 也一路升（live +0.026／+0.045／+0.056）。依凍結規則仍選 D30；若使用者想要更重的蓋帽，D50 是下一個合理選擇，需要再等樣本多一點（約 40 場後）重跑這支腳本。
- 檔案：`rim-display-2026-27-D30.json`＝D30 的 2026-27 每人 RIM 顯示值（名字→值），之後要上線的話直接讀。未改 `season_nav.py`、`ranking.csv`、OVR、DEF；沒有上線。
