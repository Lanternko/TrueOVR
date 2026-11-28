# E-084 預註冊：用人回歸的訓練目標改成 2025-26 單季 RAPM（修正年輕被低估）

- 日期：2026-10-29。來源：使用者目標「位置錯誤，跨季RAPM，新秀vs老將」的 C 線。依 E-081 §4「年輕被低估 → lead 另寫修正預註冊」。
- 版本：`card 0.2.3+E084`（R-018）。基準：正式卡 card 0.2.3（R-040，`reports/card-0.2.3/ranking.csv`）。
- git HEAD（寫本檔時）：d5e1936。角色：實作 role-card；判讀 lead。

## 0. 背景與假設

- E-081 的結果（**lead 已看過，全部揭露**）：
  - 答案 N（另一半只用 2025-26 的 RAPM × MPG）：S = Spearman(年齡, u) = −0.202，90% 區間 [−0.262, −0.141]。
  - 分組 u 平均：≤23 歲 +0.101、24–27 歲 +0.003、28–30 歲 −0.030、≥31 歲 −0.094。
  - 答案 Q（E-064 舊量尺，四季合併 pooledNet）：S = −0.021 [−0.078, +0.034]，沒有偏差。
- 解讀：卡片對齊的是四季合併 RAPM。E-075 用人回歸（`reports/card-0.2.2+E073-usage-evidence/e075.py` 的 `pipeline()`）的訓練目標 y 是 fit 半季的 `pooledNet`，四季合併的 RAPM 對正在成長的年輕球員落後，對衰退中的老將偏高。E-075 已有年齡項（y、v、y·L、v·L、y·d·L），但它們學的是「怎麼像合併 RAPM」。
- H：訓練目標改成 fit 半季**只用 2025-26 比賽**擬合的 RAPM net 之後，年齡項會改學「怎麼像當季」。樣本外：
  - 年齡偏差變小。
  - 當季量尺（答案 N）不變差。
- 沒有可調參數：只換目標欄，特徵、迴歸形式、權重定義、人群都不動。
- 限制：這次修正是看過 E-081 的 N／Q 差異之後才選的。評估用的是同一季的另一半（交叉擬合，樣本外），但不是沒看過的季。報告要寫明這點，G5 由使用者抽查。

## 1. lead 已看過的（揭露）

- E-081 全部數字（如上），以及 `rapm1-A.csv`、`rapm1-B.csv` 的存在與欄位；沒有逐人看過 rapm1 的值。
- card 0.2.3 全部欄位；E-075 的 c2、c4；E-079 全部數字；F-033 的位置單人反事實。
- **沒看過**任何以 rapm1 為訓練目標的係數、卡片或樣本外數字。

## 2. 改動

- 複製 `e075.py` 為本目錄的 `e084.py`，加開關 `--target {pooled,season}`，預設 `pooled`。
  - 帶 `pooled` 時必須和 E-075 完全相同。
- `season` 時，`pipeline()` 訓練列只改兩件事：
  - `yv`：`rapm[fit][n]['pooledNet']` 換成 `reports/card-0.2.3+E081-age-residual/rapm1-{fit}.csv` 的 `net`。
  - `w`：`pooledPoss` 換成 rapm1 的 `poss`。
- 人群 `pools[ev+fit]` 不變。人群裡在 rapm1 找不到的球員，從**訓練列**剔除，並回報人數與名單。
- `coef['card']`（兩方向合併）照原式，同樣用 season 目標。
- 其他全部不動：
  - 特徵 p、L、a、y、v、d。
  - 年齡門檻 23／31，D_THR 0.35。
  - k = 9。
  - 置換人群 POOL_MIN、PR10 替補水準、two_segment 錨點、MPG 定義。
- 卡片組裝照 `reports/card-0.2.3/build_card_023.py`，輸入換成新卡。
- 敏感度 s1、s2、s3 照 E-075，同樣在 season 目標下跑，只報告。

## 3. 評估

全部用 E-081 的程式與定義（`reports/card-0.2.3+E081-age-residual/e081.py`），只把卡片 g_c 換成候選的半季值：

- 人群：E-075 `pools[dn]`。
- 答案 N 和 Q 的定義同 E-081。
- 球員 bootstrap 2000 次，seed 1，master 聯集。
- 兩方向平均。
- 候選和基準共用同一組抽樣。

## 4. 判定

| # | 條件 | 門檻 |
|---|---|---|
| (c0) | `--target pooled` 重現 | E-075 `results.json` 的 c2、c4 數值最大差 < 1e-9，且 card 0.2.3 `ranking.csv` sha256 相同（或共同欄位最大差 < 1e-9）。不過就停下修程式，不看任何誤差數字 |
| (c1) | G1 | `npm test` 過 |
| (b) | 年齡偏差變小 | ΔS = S_N(候選) − S_N(card 0.2.3) 的 90% 區間下界 > 0 |
| (c2N) | 當季量尺不變差 | ρ_N(候選) − ρ_N(card 0.2.3) 的 90% 區間下界 > −0.02 |
| (c2Q) | 合併量尺不大幅變差 | ρ_Q(候選) − ρ_Q(card 0.2.3) 的 90% 區間下界 > −0.05 |
| (c3) | evaluate 閘數不減 | ≥ card 0.2.3（18/19） |
| (c4) | 用人資訊樣本外有用 | ρ(候選 pn, 另一半 rapm1 net) − ρ(p, 另一半 rapm1 net)，兩方向平均，90% 區間下界 > 0（E-075 c4 的算法，net 換成單季） |
| (R2)–(R4) | 同 E-075 | 基準是 card 0.2.3 |

- (c2Q) 放寬到 −0.05，是因為這次刻意離開合併 RAPM，Q 下降一部分是預期的。這個門檻在看結果前就定死。
- 全過：記為「通過」，交使用者做 G5、定版本。(c2N) 下界 > 0 → MINOR，否則 PATCH（R-019）。
- (b) 過、但 (c2N) 或 (c2Q) 沒過：記為「偏差有修、準度有損」，不採用，停下交使用者。
- 其他任一沒過：不採用。
- 不准看過結果後改目標定義、權重、人群、門檻（L-026）。

## 5. 和 E-082 的關係（看結果前定死）

- E-084 的基準一律是 card 0.2.3，不等 E-082。
- E-082 和 E-084 都通過時，跑一次合併版：E-082 的比例卡當 p，再接 E-084 的 season 目標。
  - 合併版的判定照本檔 §4，基準仍是 card 0.2.3。
  - 合併版全過才採用合併版。
  - 合併版沒過時，各自的結果交使用者選，lead 不自己挑。

## 6. 只報告

- 候選的 S_N、S_Q，以及兩者的分組 u 平均，和 card 0.2.3 並排。
- 三組係數（AB、BA、card），和 E-075 並排。
- Banchero、Jalen Williams、Jalen Johnson 的 OVR、名次、年齡。
- 前 20 名；OVR 變動最大的 20 人。
- 各年齡組（≤23、24–27、28–30、≥31）MIN ≥ 1000 球員的 OVR 中位數，和 card 0.2.3 比。
- 預測值的離散度：pred_new 在 MIN ≥ 1000 球員中的標準差，和 card 0.2.3 比。
  - 單季半季 RAPM 收縮較大，預測尺度可能變窄，讓每場值更偏向分鐘。

## 7. 不准

- 唯讀，用 sha256 檢查（L-037）：
  - `reports/impact-rapm/`
  - `reports/ovr-v58-holdout-2025-26/`
  - `reports/card-0.2.2/`
  - `reports/card-0.2.3/`
  - `reports/card-0.2.2+E073-usage-evidence/`
  - `reports/card-0.2.3+E081-age-residual/`
  - `reports/card-0.2.3+E082-position-shares/`
  - `reports/defense-tenth/`
  - `data/`
- 新程式和新輸出只放 `reports/card-0.2.3+E084-current-target/`，附上和 `e075.py`、`e081.py` 的 diff。
- 不改模擬（`src/`）、屬性。
- 不碰 memory/、live/、gh-pages。
- 不部署、不 commit、不 push。
- 子程序帶 `creationflags=subprocess.CREATE_NO_WINDOW`。
