# E-181 預註冊：新增「無球」能力值（製造空檔＋把握空檔）

- 日期：2026-11-01。來源：使用者看完 Simons 兩場爆發反而 OVR 下滑的診斷後說「新增無球屬性？因為球隊已經有開發手了 角色不用重複 製造空檔 把握空檔也是一個實力」，範圍選 A（只進卡片，之後再談賽中與模擬）。
- 基準：card 0.2.9a（`reports/card-0.2.9a/ranking.csv`；建卡管線＝E-164 S 臂，與 E-180 K0 同一條）。
- 狀態：已凍結（2026-11-01，使用者「核可」）。

## 0. 已揭露（lead 寫本檔前看過的東西）
- Simons 2026-27 前 7 場逐日重算（樣本內、單一球員）：10/28、10/30 兩場 20／21 分、三分 11/18、各 1 助攻；pass 70.9→58.6、creation 91.6→83.9、long 73.7→76.2，OVR 61.3→57.1。creation＝(1−被助攻比例)×FGA/36，接球投進的球會壓低它。**Simons 只列在例子表，判定不得以他為條件。**
- E-179／F-117：creation（前鋒）與 pass（全位置）對下季 RAPM 偏高；F-084：**模擬**看不到無球等 box 外貢獻，3D 側翼在模擬排序被低估；但卡片 OVR 經 RAPM 校準，同批 3D 側翼名次不低（H. Jones OVR 17）——所以卡片端「無球型被低估」是待驗假設，p0 可能不成立。
- E-180 草稿（pass 共用斜率／creation 交互項）與本實驗互相獨立，各自以 0.2.9a 為基準。
- **沒看過**：任何無球原始值的分布、它和 RAPM／薪水／2K 的關係、任何加入後的卡片或名次。

## 1. 能力值定義（凍結，不得依結果調）
- **offBall 原始值**＝每 36 分鐘「被助攻進球得分」：play-by-play 中該球員投進且有隊友記助攻的投籃，兩分算 2、三分算 3，加總後 ÷ 上場分鐘 × 36。罰球不算。
  - 同時含「製造空檔」（要跑得出空位才拿得到傳球）與「把握空檔」（要投進才記得到）。只用 pbp，所有卡片季都有，不靠 catch-and-shoot 追蹤。
  - 取樣窗、季權重、收縮、百分位映射一律照 card 0.2.9a 對 `creation` 的同一套（同窗、同池、同 E-101 尾巴）；沒有 pbp 的球員／季照 creation 的缺值規則處理。
- **offBallAcc**（只在臂 O2）＝NBA tracking catch-and-shoot eFG%（`leaguedashptstats` PtMeasureType=CatchShoot, PerMode=Totals），向聯盟平均收縮，k＝150 次出手（固定）；映射照 `long`。
- 任一卡片季缺 pbp 或缺 tracking 就停下回報，不得換定義或補值。

## 2. 臂（只加預測變數，其餘照 0.2.9a）
| 臂 | 加入 OVR 迴歸的能力值 | 想法 |
|---|---|---|
| K0 | — | 0.2.9a 原樣。c0：重建後 2025-26 ranking 與 `reports/card-0.2.9a/ranking.csv` 逐位元相同，不同就停 |
| O1 | offBall（主效應，不加位置交互項） | 一個數字同時量製造與把握空檔 |
| O2 | offBall＋offBallAcc（皆主效應） | 把「接球投準」從 long 分出來 |

不動：其他能力值、目標 T6、ridge 1.0、`INTERACT`、RAPM 混合、用人層、映射錨、r_repl、賽中管線、名單頁、模擬（`src/`）。

## 3. 兩階段
### 第 1 階段（現在跑，只做不劣於檢查，不決定採用）
- c0（K0 逐位元）、`npm test` 過。
- 2025-26 卡（MIN ≥ 500）：
  - s1：Spearman(OVR, 薪水 errata-1 權重) 與 Spearman(OVR, 2K `data/external-impact/2k/2k-merged-e142.csv`)，X−K0 的球員層 bootstrap（2000 次，seed 20261181）90% 下界 > −0.01。
  - s2：隊內 MIN–OVR Spearman 30 隊中位數，X 不低於 K0 超過 0.02。
  - s3：offBall 的迴歸係數 > 0（無球得分多卻扣分代表定義或共線有問題）；≤ 0 該臂不採用。
- 第 1 階段不過的臂，直接不採用，不進第 2 階段。

### 第 2 階段（判定；2026-27 RAPM 到位才跑）
- 時點與答案照 E-180 §2：2026-27 例行賽 RAPM（E-126 `rapm_season.py` 作法），2025-26 卡人群中 poss ≥ 1000 達 250 人才跑，最早 2027-02-15；資料截止日寫進 results.json，之後不換日期重跑。`net` 乘 `wfun(2026-27 mpg)`，人群照 E-179 §2。
- 統計量：e_net＝pct(net×W)−pct(OVR)。**無球組 Q**＝K0 能力值中 offBall 百分位 ≥ 60 且 creation 百分位 ≤ 50 的人（分組在第 1 階段就用 K0 寫死，三臂同一份）。bootstrap 2000 次，seed 20261181，90% 區間；臂間差在同一組重抽上算。
- 判定：
  - **前提 p0**：K0 的 Q 組平均 e_net 上界 < 0（無球型在新資料確實被低估）。不成立 → 判「低估沒重現，不加屬性」。
  - **臂 X 採用候選**（X ∈ {O1, O2}）同時滿足：
    - ① Q 組平均 e_net，X−K0 下界 > 0（低估變小）；
    - ② Spearman(OVR, net×W)，X−K0 下界 > −0.01（整體不變差）；
    - ③ 第 1 階段已過。
  - O1、O2 都是候選時選 O1（少一個屬性）。都不是 → 不採用。
- 只報告：e_O 版本；Q 組按位置拆；例子球員 Anfernee Simons、Klay Thompson、Michael Porter Jr.、Sam Hauser、Duncan Robinson、Derrick White、Jalen Williams 的三臂 OVR／名次。

## 4. 只報告（第 1 階段）
- offBall 原始值前 30 名與分布；offBall 與 creation、long、pass 的 Spearman（看共線）。
- 三臂係數表；2025-26 前 20 名進出、OVR 變動最大的 20 人、上面例子球員。
- E-179 三個歷史原點對下季 RAPM 的 Q 組殘差——歷史原點其他能力值是 2025-26 現值（L-091），只當方向參考，不進判定。

## 5. 限制
- 只寫 `reports/E181-offball-attr/`；0.2.9a、E-164、E-180 目錄唯讀；不改 `src/`、不改賽中管線與名單頁。
- 「持球手太多就遞減」屬陣容搭配，不在本實驗（使用者選 A；卡片量的是搭四個平均隊友，R-025）。
- 被助攻得分也受隊友傳球品質與體系影響；本實驗不做隊友調整，若第 2 階段過了再另開。
- 第 2 階段要等數個月；這段時間正式卡維持 0.2.9a。回報用六段格式（CLAUDE.md）。

## 6. 產出
- 第 1 階段：`e181_build.py`、`offball-raw.csv`、`ranking-{K0,O1,O2}-2025-26.csv`、`stage1.json`、`stage1.md`。
- 第 2 階段：`e181_stage2.py`、`results.json`、`report.md`。
