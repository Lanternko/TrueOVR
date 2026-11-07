# E-255 預註冊：擋拆持球（PnR ball handler）當新能力值，陣容 Transformer 量「量／率」混合與每點價值

- 日期：2026-11-07。使用者看完 POR 進攻拆解後問「擋拆持球怎麼加進屬性、怎麼給分、每點擋拆屬性值多少勝利貢獻」，並說「開實驗」。標準依 R-165 自訂並直接凍結。
- 狀態：**已凍結**（凍結時未訓練、未評估任何臂；只跑過 `e255_prep.py --check` 的資料檢查，數字見下）。
- 框架沿用 E-245（`reports/E245-mid-lineup-tf-blend/`）：同 5 季 111,499 個 stints、同 20% test 切分、同 `LineupNet`（d=64, layers=2, heads=4, ff=128, dropout=0.1, norm_first；AdamW lr=1e-3, wd=0.1, batch=1024, max_epochs=60, patience=5）、5 顆種子 0–4、E-179 三季 867 人次、隨機替換法（RandomState(225)、M=1000）。

## 與 E-245 的差異
1. **不替換既有欄，而是新增第 16 欄 `pnr`**；其餘 15 欄維持現行卡片值（含 `creation`、`onBall`）。
2. 資料：E-239 已抓的 Synergy `syn-PRBallHandler-{季}.json`（季總量，跨隊相加），分鐘取 player-games 全季。
   - 量 `vol = POSS / MIN × 36`。
   - 率 `rate = (PTS + k·μ) / (POSS + k)`（每回合得分，向聯盟平均收縮）。`k = s2 / var_true`：每回合得分變異 `s2 = μ·(μ/score%) − μ²`（得分回合平均分×μ − μ²），`var_true` = POSS≥50 球員加權 var_obs − 平均 s2/n，夾 [20, 800]。
   - Synergy 沒列名的球員（擋拆回合太少）vol=0、rate=μ；百分位同分取平均名次。
3. 臂 9 個：`T0`（不放 pnr，等於現行）、`W00 W02 W04 W05 W06 W08 W10`（`z_pnr(w) = (w·ṽ+(1−w)·ã)/sqrt(w²+(1−w)²+2w(1−w)ρ)`，ṽ、ã 為季內百分位再 z）、`WL`（可學 w，前 3 epoch 固定 0.5）。
4. M1 = 位置＋`long`＋九項進攻屬性（mid, short, ft, drive, foulDraw, tovSkill, pass, **creation**, rebound）＋ LineupNet 個人擋拆邊際進攻影響力 `offpnr_val`（實際 pnr vs 聯盟平均 0），ridge λ=10，留一季預測下季進攻 RAPM（O）。T0 的 `offpnr_val`≡0，M1(T0) = 只有基底。

## 凍結前資料檢查（`--check`，不碰答案；百分位同分取平均名次後的數字）
| 季 | 有分鐘 | Synergy 列名 | k | μ | ρ(量,率) | r(creation, 量) | r(creation, 率) |
|---|---|---|---|---|---|---|---|
| 2021-22 | 605 | 302 | 201 | 0.877 | −0.14 | 0.46 | 0.11 |
| 2022-23 | 539 | 289 | 153 | 0.914 | −0.10 | 0.64 | 0.07 |
| 2023-24 | 571 | 282 | 154 | 0.907 | −0.16 | 0.53 | 0.10 |
| 2024-25 | 569 | 308 | 173 | 0.896 | −0.11 | 0.56 | 0.10 |
| 2025-26 | 582 | 319 | 141 | 0.881 | −0.07 | 0.69 | 0.12 |

- k≈150–200：擋拆每回合得分要約 150–200 個回合才有一半可信度，印證 E-239「效率類是雜訊」；量與 creation 高度相關（0.44–0.69），預期增益小。

## 已知風險／邊界（R-165 自決）
- **Synergy 只有季總量，無法排除 test 場次** → `split=test` 有同季洩漏，只報告；「沒弄壞」改用 `cross_test`（前一季球員表預測當季 test stints，無洩漏）。
- 單季值，不是卡片的四季窗口；M1 基底已含 creation、drive，對 pnr 的價值偏保守。
- O 為下季進攻 RAPM（每百回合）。

## 判定表（基準一律 T0）
令 `w*` = 7 個固定混合臂中 M1 R² 最高者。

| # | 類別 | 怎麼算 | 門檻 |
|---|---|---|---|
| 1 | 要修的目標 | M1 R²(w*) − M1 R²(T0) | ≥ max(0.005, 2σ_seed(w*)) |
| 2 | 要修的目標 | 三折逐折增益 | 至少兩折 >0 |
| 3 | 要修的目標 | 球員層成對 bootstrap 2000 次（seed 20261255）90% CI | 下界 >0 |
| 4 | 沒弄壞 | w* 相鄰格 M1 R² − T0 | 皆 >0 |
| 5 | 沒弄壞 | cross_test pts100_MSE(w*) − T0，場次成對 bootstrap（seed 20261107） | 點估 ≤ 2×σ_seed(T0) |
| 6 | 只報告 | 每點換算：基底＋擋拆分數 S（0–99），三季合併 ridge 係數（O／點）與 bootstrap 90% CI；勝場 ≈ 係數×點數×(MPG/48)×2.7 | — |
| 7 | 只報告 | 直接 ridge（不經 TF）各 w 增益、M2、WL 學到的 w、G/F/C 分組、split=test、代表球員名次 | — |

- 1–5 全過 → 候選（新增 pnr 能力值，交使用者裁定）；任一不過 → 不採用，pnr 只可當顯示格子（R-166 規則：量類可顯示）。
- 只寫 `reports/E255-pnr-handler-lineup-tf/` 與 5090 `~/side_projects/pure_ovr/experiments/e255/`；不動 `src/`、正式卡片。
