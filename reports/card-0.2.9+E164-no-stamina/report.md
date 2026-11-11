# E-164 報告：卡片 OVR 拿掉 stamina（card 0.2.9+E164）

執行：role-card，全部在本機（Windows）跑，沒用 5090；每個原點的用人層約 5–6 秒，部件卡重建數分鐘。預註冊 sha256 803139b0…a3d7 核對相符、未改。

## 判定（預註冊 §3，S 對 K，判定季 2022-23／2023-24／2024-25 依人數加權）
| 項目 | S−K | 門檻 | 結果 |
|---|---|---|---|
| (a) 全體 C | −0.0040 | ≥ −0.005 | 過 |
| (b) ② 薪水 | −0.0216 | ≥ −0.02 | **不過**（差 0.0016） |
| (b) ②之二 2K | −0.0004 | ≥ −0.02 | 過 |
| (b) ③ 下季 RAPM | +0.0099 | ≥ −0.05 | 過 |
| (b) ④ 下季 EPM | +0.0102 | ≥ −0.05 | 過 |

整體不過（薪水一項）。依預註冊 §3：交使用者選（仍照 R-105 採用／維持 0.2.9）。
各季薪水 K→S：2022-23 0.752→0.719、2023-24 0.651→0.626、2024-25 0.678→0.667。人群 271／303／346 人。

## 只報告項目（§4）
- C 差 bootstrap 90% 區間（2000 次，seed 20261104）：[−0.0155, +0.0076]，跨零。
- 2025-26（人群 379）：C K 0.7142／S 0.7102；M_sal 0.5919／0.5900；M_2k 0.7685／0.7657。
- 整季場均分鐘三分位（2025-26，K 的 mpg，低／中／高 ＝ <=18.3／<=27.4／其餘）K→S 平均 OVR 變化與名次（正＝升）：低 +0.09／−0.3 名、中 +0.17／+2.6 名、高 −0.61／−2.3 名。三季歷史原點同向者 2022-23、2023-24（高分鐘組 −0.67 OVR、降 2–4 名）；2024-25 高分鐘組 −0.19。
- 關鍵球員（2025-26，MIN≥500，K→S 的 OVR／名次）：Jalen Williams 86.9/17 → 88.2/10；Chet Holmgren 87.0/16 → 87.9/11；Jokić 95.2/6 → 93.4/7；SGA 119.4/1 → 119.2/1；Wembanyama 106.4/2 → 107.0/2；Flagg 77.6/75 → 76.1/82；Edwards 88.7/9 → 87.5/14。
- 升最多 5 人：Quenton Jackson 235→186、Daniss Jenkins 283→235、Javon Small 149→104、Jordan Miller 201→165、Bryce McGowens 326→291。降最多 5 人：Royce O'Neale 286→335、VJ Edgecombe 101→150、Deandre Ayton 194→239、Rui Hachimura 202→238、Ace Bailey 248→280。
- G5 預查：K 前十名長人（C／PF）在 S：Wembanyama 2→2、Giannis 4→4、Jokić 6→7、Tatum 8→8、Barnes 12→19、Mobley 15→15、Holmgren 16→11、J. Williams 17→10、J. Johnson 21→28、A. Davis 22→21。前 20 名進出：無人進出（只是名次互換）。前 300 名移動 ≥10 名：128 人。
- 部件卡係數（每 10 點能力值的每 36 分，2025-26 原點，三張卡一致）：K 的 stamina 係數 primary +0.270、fitA +0.274、fitB +0.262。S 中變動最大的三項（primary）：heightInches −0.385→+0.053、onBall +0.024→+0.137、pass +0.223→+0.307（fitA／fitB 同三項）。form／ridge 重選結果不變（position-interactions、ridge 1.0）。
- npm test：52 passed, 0 failed（`logs/npm-test.log`）。

## 檢查
- c0：K 四原點逐位元相同（2025-26 對 `reports/card-0.2.9/ranking.csv`，sha 03288908…6eae；三個歷史原點對 E-158 `ranking-Y0-<季>.csv`）。
- c0d：不帶旗標的複本重建，部件卡與 ranking 和 E-153 K6 逐位元相同（2025-26 ranking e920a840…）。
- u1：S 與 K 的能力值欄（含 stamina）、MIN、mpg、pos 四原點逐格相同，不同的只有 OVR 相關欄。
- u2（stamina 讀取點）：整條評估鏈只有 `calibrate_wing_t.py` 第一層設計矩陣讀 stamina（ATTRS 與 line 65/66、271 取值、463 旗標、593/626 輸出）；`e094_t.py`（用人層）、H1 align、校準都不讀；`e134_build_season_league.mjs` 的 stamina（line 28、172）是產出能力值欄，不進 OVR；`check_t.py:10`、`sentinel_t.py:75`（註解）不影響。沒有觸發停止條件。
- 唯讀 sha：src、card-0.2.9、E142、E153、E158、E162、stage1、E157 共 2188 檔，前後逐檔相同（`readonly-sha-before/after.json`）。

## 偏離
1. 複本 `calibrate_wing_t.py` 第 42 行 `ROOT` 由 `parents[3]` 改 `parents[2]`（資料夾深度不同，否則找不到路徑）。不影響結果（c0d 逐位元通過）。`--dropAttr` 原檔就有，沒改旗標程式。
2. 歷史原點（2022-23～2024-25）的 pool 來自各臂自己的卡，2025-26 用固定的 rebase-027a 卡（沿 E-162 做法）。對 K 與 S 同樣，不影響 S 對 K 的比較。
3. `simulatedPer36` 來自 league 檔（與 K 相同）。

## 產出
`results.json`、`ranking-{K,S}-{2022-23,2023-24,2024-25,2025-26}.csv`、`e164_build.py`、`e164_eval.py`、`calibrate_wing_t.py`、`logs/`、`work/`。
