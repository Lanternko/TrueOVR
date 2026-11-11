# E-198 報告：加「無球引力」能力值進卡片 OVR（KAU → KG）

- 日期：2026-11-02；role-card；預註冊 `preregistration.md`（HEAD LF sha256 `52013c06…0950dc`，未改）。
- 結論：**A（機制）不過**；**沒弄壞過**。gravity 係數學得到（正、約 4.6 SE），但接球射手組被低估的量完全沒動。

## 1. 步驟與產物
| 步驟 | 產物 | 結果 |
|---|---|---|
| c0 | `work/KAU-final/out/ranking.csv` | sha `8b3e99d6…` ＝ `card-0.2.10i/ranking.csv` 逐位元（`work/KAU-final/result.json`）；部件卡 sha 同 0.2.10i A-real |
| gravity 原始值 | `gravity-raw.csv`、`gravity-attr.csv`、`work/gravity-impute.json` | 卡片 582 人：234 有值、348 OLS 補值（R² 0.725，殘差 SD 2.74）；0–99 池 252 人（GP≥30、MPG≥20，含補值 82 人），兩端尾巴開（同 creation 的 h1） |
| RAPM 分半 | `work/rapm-2025-26-{odd,even}.json`、`work/rapm-split.json` | 全季重算 c0 max\|Δnet\| 0；單場 607 場、雙場 613 場，λ 皆 3000 |
| phase0（KG 前） | `phase0.md`、`phase0.json` | h 0.0580、MDE_rank 8.26 點、MDE_value 0.2335 SD；S 組平均 pct(OVR) 43.0 → 無假象，A 主口徑＝名次殘差 |
| KG | `work/A/base-KG-2025-26/`、`work/B-KG/`、`work/KG-final/out/ranking.csv` | sha `4519d615…` |
| 判定 | `results.json`、`logs/eval.log` | 見 §2 |

腳本：`build_kg.py`（card-0.2.10d/build.py 複本，CAL→本目錄 E-181 版 calibrate、KG 臂加 `--offBallSource gravity-attr.csv --offBallCols gravity`）、`calibrate_wing_t.py`（E-181 複本，未改）、`run_i.py`（card-0.2.10i 複本，模式 KAU|KG）、`finalize.py`（E-188 OVR 映射）、`gravity_raw.py`、`rapm_split.py`、`e198_eval.py`。

實作小決定（預註冊沒寫到，跑 KG 前定）：3PA=0 的人 3P% 記 0；0–99 的池含補值的人（同 creation 池含池內所有人）；分半用全季同一人群（MIN≥500 且全季 poss≥1000，379 人）；A 縮小量＝sign(KAU 組平均)·(KAU − KG)；名次＝人群內 (r−1)/(n−1)×100；假象規則＝S 組 KAU 平均 pct(OVR) 偏離 50 超過 10 點才改以價值殘差判。

## 2. 判定
人群 379 人；接球射手組 S（KAU long≥75 且 creation≤60）29 人。bootstrap 2000 次，seed 20261102，配對重抽。

| 項目 | KAU | KG | KG − KAU（90% 區間） | 門檻 | 判定 |
|---|---|---|---|---|---|
| S 組名次殘差（點，正＝低估） | +11.97 [3.61, 20.14] | +11.97 [3.80, 19.92] | +0.005 [−0.71, +0.71] | 縮小 ≥ 8.26 | **A 不過**（縮小 −0.005） |
| S 組價值殘差（SD） | +0.263 [0.034, 0.501] | +0.258 [0.029, 0.493] | −0.005 [−0.018, +0.006] | （只報告）縮小 ≥ 0.2335 | 也不過（縮小 0.005） |
| 全體 ρ(OVR, 本季 RAPM) | 0.5876 [0.525, 0.641] | 0.5905 [0.528, 0.642] | +0.0030 [−0.003, +0.009] | ≥ −0.116（−2h） | **過** |
| c0 | — | — | — | 逐位元 | 過 |

分半（同方向檢查）：
| 半 | ρ KAU→KG | S 組名次殘差 | S 組價值殘差 |
|---|---|---|---|
| 單場 | 0.4892→0.4900 | +15.48→+15.49 | +0.388→+0.383 |
| 雙場 | 0.5079→0.5082 | +9.65→+9.66 | +0.132→+0.127 |

兩半方向一致：ρ 微升、S 組殘差不動（名次殘差的 KG−KAU 差只取決於卡片名次，三列相同）。

## 3. 只報告
- **gravity 每 10 點**（primary 部件卡，calibrate 內建 bootstrap SE）：+0.186 ± 0.040 per36；fitA +0.197 ± 0.040、fitB +0.182 ± 0.041。換成 OVR（KG 人群 OVR 對 predictedPer36 斜率 8.75）≈ **+1.63 ± 0.35 OVR／10 點**。
- 係數重分配（primary per36/10 點，KAU→KG）：creation 0.220→0.136、ft 0.110→0.065、long 0.398→0.369、foulDraw 0.197→0.172、rebound 0.076→0.185、heightInches 0.249→0.187；其他差 <0.02。
- VIF（gravity 對其他 14 項，MIN≥500）：R² 0.703，VIF 3.36。相關：creation 0.76、ft 0.67、drive 0.54、pass 0.48、long 0.30、rebound −0.50。gravity 主要是持球得分手的訊號；S 組（含 Horford、Turner、Collins 等空間型長人）gravity 中位約 60。
- 外部指標（MIN≥500）：薪水加權 ρ 0.6297→0.6308（262 人）；2K27 ρ 0.7592→0.7648（376 人）；EPM ρ 0.7942→0.7926（379 人）。
- 名次移動：KAU/KG 名次 ρ 0.997；前 100 名移動 ≥10 名 11 人（升：Pippen Jr. 90→68、Toppin 98→77、KAT 52→41；降：C. Johnson 44→63、Sexton 70→89、Gillespie 82→100、Rollins 80→98、Castle 100→119、Zubac 73→85、S. Barnes 25→36、Dosunmu 99→110）；前 20 名進 Fox、出 Bane。
- 補值的人（MIN≥500 有 145 人）：平均升 2.8 名、平均 |Δ| 8.5 名；升最多 Jerami Grant 480→430、Coulibaly 350→315、D. Carter 321→288；降最多 McGowens 365→418、S. Cooper 249→276。
- S 組 29 人平均升 1.7 名，有升有降：Jamison Battle 447→415、O'Neale 431→406、Nesmith 169→149；Turner 108→123、Collins 200→218、H. Barnes 270→286。

### 球員表（名次＝全 582 人；* ＝ gravity 補值）
| 球員 | KAU→KG 名次 | OVR | gravity | 本季 RAPM pct ／ 卡 pct KAU→KG（379 人內） |
|---|---|---|---|---|
| Klay Thompson | 419→357 | 55.9→57.9 | 98.1 | 21 ／ 15→22 |
| Stephen Curry* | 18→15 | 93.0→92.9 | 98.8 | 84 ／ 96→97 |
| Buddy Hield* | 259→240 | 65.7→66.7 | 85.3 | 22 ／ 40→43 |
| Luke Kennard | 135→120 | 75.6→76.4 | 85.9 | 54 ／ 66→71 |
| Duncan Robinson | 208→199 | 69.6→70.4 | 96.0 | 86 ／ 49→51 |
| Sam Hauser | 175→160 | 72.9→73.6 | 74.1 | 75 ／ 57→60 |
| Michael Porter Jr.* | 36→34 | 88.5→89.4 | 95.0 | 73 ／ 91→92 |
| Shai Gilgeous-Alexander | 1→1 | 109.6→108.5 | 110.8 | 100 ／ 100→100 |
| Kevin Durant | 16→13 | 93.2→93.2 | 105.2 | 71 ／ 96→97 |
| Luka Dončić | 4→4 | 102.1→101.7 | 99.0 | 89 ／ 99→99 |
| Nikola Jokić | 2→2 | 106.5→105.7 | 71.3 | 98 ／ 100→100 |
| Rudy Gobert | 63→61 | 82.9→82.5 | 35.3 | 85 ／ 84→84 |
| Jalen Williams* | 9→10 | 94.6→93.4 | 67.7 | 80 ／ 98→97 |
| Giannis Antetokounmpo* | 5→5 | 99.0→99.0 | 86.1 | 93 ／ 99→99 |
| Josh Giddey* | 145→124 | 74.9→76.2 | 85.4 | 49 ／ 64→69 |

使用者預期 Klay、Curry 上升：Klay 升 62 名（+2.0 OVR），Curry 升 3 名（OVR 不變）。但 Klay 本季 RAPM 只在 21 百分位，卡片原本沒有低估他；Robinson、Hauser 這種 RAPM 高、卡片中段的射手只升 9～15 名。

## 4. 解讀
- gravity 係數是真的（約 4.6 SE、三張部件卡一致），但主要從 creation、ft 分走權重：引力高的人本來就是持球得分手（F-139 ρ −0.21 同方向），卡片已經給了。淨效果名次幾乎不動（ρ 0.997），S 組殘差 +11.97→+11.97。
- 外部指標都在雜訊內（2K27 +0.006、EPM −0.002、薪水 +0.001）。
- 限制：同季 RAPM（DARKO 帶 RAPM 資訊）算半樣本外；gravity 只有 2025-26 一季，60% 卡片球員（多為低分鐘）是補值，補值主要靠 USG%，又把 gravity 推向 creation。真樣本外留給 2026-27 季末。
- 依預註冊 §1-5：學得到係數但沒修到低估 → F-140 記「已知限制」（lead 寫 memory）。

## 5. G1／G2
- npm test：exit 0（52 passed, 0 failed；Python 單元測試 OK），`logs/npm-test.log`。
- 輸入 sha256：`results.json` 的 `inputs_sha256`、`work/gravity-impute.json` 的 `sources_sha256`、`work/rapm-split.json`（stints `5eff6aa8…`）。卡片版本：KAU＝card 0.2.10i（`8b3e99d6…`），KG＝`work/KG-final/out/ranking.csv`（`4519d615…`）；RAPM 窗＝2025-26 單季（E-126 `rapm-2025-26.json` `7b757241…`）。
