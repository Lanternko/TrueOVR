# E-195 診斷計畫（F-136 擬合端）— 跑前凍結

跑 `diag.py` 之前寫好；跑完不改定義（L-026）。只讀 E-190 的 `work/`；不改卡、不提採用。
唯一在計畫之前做過的事：用 `work/proto.py` 確認「在行程內重跑卡建置程式」能逐位元重現現成的 `summary.json` 係數（只看建置對不對，沒看任何診斷數字）。

## 0. 資料與重建
- 臂：KJ（閘門）與 KA（對照；E-190 的 `KAU` 歷史臂即 `KA-<季>`，`M.rpath('KA', t)`）。季：2022-23、2023-24、2024-25。
- 評估人群：`reports/card-0.2.10c+E190-creation-jumper/e190_eval.py` 的 `s_data(t, (arm,))`（MIN≥500、下季 RAPM poss≥1000 且有 mpg、名字對得到唯一 id），與 E-194 同一批。`n_full`＝人群人數；`ok`＝該球員在 `base-<arm>-<季>/<季>/rapm-R.csv` 有 T6 列的子群（`n_sub`）。
- T6 原始值 `T6raw`＝`rapm-R.csv` 的 `pooledNet`（E-194 的 T6）。
- 擬合池／權重重建：以 `base-<arm>-<季>/<季>/cards/K0/primary/run.log` 第 1 行的指令、`E134_CFG=base-<arm>-<季>/<季>/calib-primary.json`，在行程內載入 `reports/E180-pass-pool-creation-interact/calibrate_wing_t.py` 並跑 `main()`（輸出寫到 `work/rebuild-<arm>-<季>/`），攔截 `load()` 回傳的 `rows`（建置後 `rows[i]['y']`＝擬合目標、`['mc']`、`['poss']`、`['r']`、`['pos']`、`['MIN']`、`['card']`）。
  - 驗證：重建的 `summary.json` 係數與 `cards/K0/primary/summary.json` 差 <1e-9，重建的 `ranking.csv` sha256 與現成 primary 相同；不同就停。
  - 設計矩陣 `X`＝`cw.design(rows, 'position-interactions')`（14 欄 z＋PG/SG/SF/PF×{long,short,rebound,help}＝16 欄）；`b`＝summary 的 `coefficientsOnStandardized`、截距＝`intercept`；`s2`＝`residualTrueVariancePer36`；權重 `w = 1/(mc + s2)`（`mc` 為建置後的 `rows[i]['mc']`）。擬合池＝全部 `rows`（417／…人，MIN 不設門檻）。
  - 擬合目標 `y`（alpha=1）：`poss≥1000` 者＝`r`＝0.75·(pooledO+pooledD) − 該位置 MIN 加權平均；`poss<1000` 者＝`target-primary.csv` 的 0（無 RAPM 資料）。`T6fit`（同單位的 T6）：對 `rapm-R.csv` 有列的任何人，0.75·(pooledO+pooledD) − mu_pos，mu_pos 由有 `poss≥1000` 的列反推（mu＝0.75·N − r）。
- 各步值（每位評估球員）：
  - S0 純線性：`intercept + Σ_{j<14} b_j·z_j`（只用主效應 14 欄、不含位置交互，取建置後的 `X[:, :14]` 與同一組 `b`）。另列 S0r：同池、同 `y`、同 `w`、λ=1 但只用 14 欄主效應重擬合（補充，不在主鏈）。
  - S1 `pred0`：`intercept + X·b`（重建值）；與 ranking.csv 的 `pred0`（3 位小數）核對 |差|<0.001。
  - S2 `pred0 + defenseBonus`（ranking.csv 兩欄；bonusShape none，防守 RAPM 季窗，H1 封頂不動 bonus 本身）。
  - S3 `pred0 + defenseBonus + align`（未封頂，三欄相加）。
  - S4 `predictedPer36`（H1 封頂後，ranking.csv）。
  - S4m `ovr36`（per-36 兩段映射後，ranking.csv；理論上與 S4 同名次，列出核對用）。
  - S5 最終 `ovr`：`work/<arm>-<季>/out/ranking.csv` 的 `ovr`（用人層：(pred − r_repl)·wmin(mpg) 經兩段映射，`gRepl` 欄為映射前；E-194 用的就是這欄）。
  - S1–S4 取自重建的 ranking.csv（與 `cards/K0/primary` 相同）；S4m、S5、mpg、gRepl 取自 `out/ranking.csv`。以球員名字對齊。

## 1. 沿管線拆
對每個 S_k（k＝S0、S1、S2、S3、S4、S5，另附 S0r、S4m）：
- **V1（E-194 約定，閘門）**：`e_k = pct_sub(T6raw) − pct_full(S_k)[ok]`；`pct(x)=rankdata(x)/len(x)`；`rho_k = Spearman(drive[ok], e_k)`。
  - 季內：上式；跨季：以 `n_sub` 加權平均。
  - 閘門：KJ 的 S5 跨季值須等於 `reports/F133-drive-scoring/results.json` 的 `D1.pooled.S_drive_efit.point`（−0.25745208800738156），差 <1e-9。
- **V2**：兩邊 pct 都在子群內算：`e = pct_sub(T6raw) − pct_sub(S_k[ok])`（排除「子群 vs 全人群」的名次基準不同）。
- **V3**：T6 改用 `T6fit`（位置置中、×0.75），兩邊 pct 都在子群內（排除 T6 沒位置置中）。
- **VD 值差（S0–S4，同單位 per-36）**：`Pearson(drive[ok], T6fit[ok] − S_k[ok])` 與 `Spearman(drive[ok], T6fit[ok] − S_k[ok])`。
- 增量：`Δ_k = rho_k − rho_{k−1}`（k＝S0 時與 0 比；V1、V2、V3 各一份）。指出偏差出現／放大的步驟＝|Δ| 最大的步驟。
- 區間：球員層 bootstrap 2000 次、`np.random.default_rng(20261101)`；每季重抽評估人群 `idx_eval`（n_full 人）；跨季同權重；報 90% 區間與 SE。

## 2. 擬合池 vs 評估人群（各季＋跨季，跨季以各集合人數加權）
`drive` 取擬合設計的 z 欄（與屬性 drive 同序）。`res = y − pred0`（y＝上述擬合目標）。
- 集合 A＝擬合池全部 rows；A1＝A ∩ `poss≥1000`（目標為真 RAPM 者）；B＝A ∩ MIN≥500；B1＝B ∩ `poss≥1000`。
- 評估人群 E＝評估人群 ∩ ok（有 T6）；E1＝E ∩ `poss≥1000`。E 內 `res_E = T6fit − pred0`。
- **(a)** corr_w(drive, res)：集合 A，權重 w。
- **(b)** 同池不加權：集合 A 的 Pearson。
- **(c)** 擬合池 ∩ MIN≥500 不加權：集合 B 的 Pearson。
- **(d)** 值差代替名次差：在集合 E 與 E1，`Pearson(drive, T6fit − pred0)`（值）對 `Spearman(drive, pct_sub(T6fit) − pct_sub(pred0))`（名次）。
- 補充（拆原因用）：A1、B1 的加權／不加權 Pearson；E 以擬合權重 w 加權的 Pearson；E 的 `poss<1000` 人數、A 中 y=0 的人數與其權重占比。
- 驗收：(a) |r|<0.02；否則寫明為什麼。
- 區間：同 §1 的 bootstrap；A 類集合重抽 `idx_A`（擬合池 rows，原順序抽 `len(A)` 個，B／A1／B1 為同一抽樣的子集），E 類由 `idx_eval` 的抽樣取子集；擬合本身不重擬合（係數固定）。

## 3. 誰被推高
- drive 前 25%＝評估人群（全人群、該次抽樣）drive ≥ 第 75 百分位者；其餘為 rest。在 ok 子群內，對 V1 的 `e_k`（S0–S5）報：top 組平均 e、rest 組平均 e、差；跨季以三季球員串接後平均。
- 前 10 名切入球員：三季評估人群（限 ok）合併依 drive 降冪取前 10（同值依季、列序）；逐步表 `T6raw 名次 → S0 → S1 → S2 → S3 → S4 → S5 名次`（名次＝同季內由高到低，T6 在子群內、S_k 在全人群，標人數）。

## 輸出
`results.json`（`sort_keys`、固定格式，重跑逐位元一致）、`report.md`（含區間與完整表）、`logs/`。

## 附記（跑前補，尚未跑任何診斷數字）
- 管線事實：最終 OVR（out/ranking.csv）是「人層」輸出：g＝(pred − r_repl)·wmin(mpg) 再兩段映射（`mpg`、`gRepl`、`ovr36` 欄），其中 wmin／r_repl 來自用人層擬合（E-162 pipe 的 WLS 加權，見 `usage-dump.json`），**不在本診斷重建**。S4→S5 這一步只能「讀」不能「重建」；做法：S4m＝`ovr36`（per-36 映射，與 S4 同名次）對 S5 `ovr`（人層）的差，就是這一步。另報 `Spearman(drive, mpg)`（三季、整個評估人群）說明 mpg 與切入的關係。
- 主鏈 S0 取「建置後係數的主效應 14 欄」（截斷交互項）；S0r（同池同權重 λ=1 只用 14 欄重擬合）一併報，兩者都列在步驟表，不事後擇一當主結果。重擬合若把含交互的完整模型（同 X、y、w）重現不出建置係數（差 >1e-6）就停。
- `T6fit` 對任何在池內且 `N` 非 NaN 者定義；若評估人群有人 `rapm-R.csv` 有列但 `T6fit` 為 NaN，V3／VD 排除並記人數。

## 跑後補（post-hoc，第一次跑完看過結果之後加的，不是預註冊；只加量、不改上面任何定義）
- 為解釋「值差沒偏差、名次差有偏差」，在 `diag.py` 加 5 個量（欄名前綴 `PH_`）：Spearman(drive, T6raw)、Spearman(drive, S1／S4／S5)（皆在有 T6 子群）、sd(S1)/sd(T6fit)、Spearman(T6fit, S1)。報告裡標「跑後補」。
