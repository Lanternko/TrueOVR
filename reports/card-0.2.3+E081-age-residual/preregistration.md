# E-081 預註冊：card 0.2.3 的樣本外年齡偏差診斷（新秀 vs 老將）

- 日期：2026-10-29。來源：使用者目標「位置錯誤，跨季RAPM，新秀vs老將」的 C 線。
- 性質：**診斷，不改卡**。結果只決定要不要另寫修正預註冊。
- 基準：正式卡 card 0.2.3（R-040，`reports/card-0.2.3/ranking.csv` sha256 933797d8…3ebc64）。它已含 E-075 的年齡特徵（≤23 歲、≥31 歲兩個虛擬變數）。
- git HEAD（寫本檔時）：d5e1936。角色：實作 role-card；判讀 lead。

## 0. 問題

把 card 0.2.3 放到樣本外量尺上，年輕球員是不是系統性比卡片表現好（被低估），或老將反過來？

## 1. lead 已看過的（揭露）

- card 0.2.3 全部欄位；Banchero、Jalen Williams、Jalen Johnson 的卡片與 RAPM 值。
- 事後探索：2K 前 100、MIN ≥ 1500 的球員中，「卡片名次 − 2K 名次」的年齡分組中位數為 ≤24 歲 +64、≥31 歲 −7.5。2K 不是答案，不作判準。
- E-075 的 c2、c4 結果；E-079 第一階段全部數字（包括 2025-26 單季 RAPM 對窗口 net 的球員層 ρ）。
- **沒看過**任何「樣本外殘差 × 年齡」的數字，也沒看過 2025-26 單季分半 RAPM。

## 2. 卡片與答案

- 卡片：card 0.2.3 在半季的版本，也就是 E-075（`reports/card-0.2.2+E073-usage-evidence/e075.py`）主規格在「半季評估」裡算出的 `cand` 每場值 g_c。方向 AB 是用 A 擬合、在 B 評估；BA 反過來。用複製的程式把它輸出，不改演算法。
  - (k0) 自檢：重算的 c2 數值和 E-075 `results.json` 相同（差 < 1e-9），不同就停下回報。
- 人群：每個方向都沿用 E-075 的 `pools[dn]`（照 E-064 §3.2：pooledPoss ≥ 2500，2025-26 兩半各至少 5 場）。
- 答案 N（主）：評估半季**只用 2025-26 比賽**擬合的 RAPM net（λ 3000，模型同 `reports/impact-rapm/rapm.py`；比賽依 `int(gameId) % 2` 分到 A／B，切法同 `reports/ovr-v58-holdout-2025-26/rapm-split.py`），乘上評估半季的 MPG（E-075 的 `D['mpgh'][ev]`）。
  - (k1) 自檢：用同一支程式擬合 2025-26 全季，必須重現 `reports/impact-rapm/rapm.csv` 的 lastSeason* 欄（最大差 < 1e-6）。不過就停下。
- 答案 Q（只報告）：E-064 舊量尺，也就是評估半季的 pooledNet × 評估半季 MPG（就是 E-075 的 `ans`）。四季合併的 RAPM 本身可能偏袒老將，所以只報告，不作判準。
- 年齡：E-075 的 `D['age']`（NBA bio 的 AGE 欄）。沒有年齡的球員排除，並回報人數。

## 3. 統計量

- 在每個方向的人群內，把答案和卡片 g_c 各自換成百分位名次（0–1，平均名次處理同分）。殘差 u = pct(答案) − pct(卡片)；u > 0 代表卡片低估。
- 主統計量 S = Spearman(年齡, u)，兩個方向各算後取平均。
- bootstrap：以球員重抽 2000 次，seed 1，抽法照 E-075 的 b2（master 名單聯集，兩個方向共用同一組抽樣）。
- 分組（只報告）：≤23、24–27、28–30、≥31 歲，各組 u 的平均與 90% 區間（同一組 bootstrap）。

## 4. 判定（答案 N）

| 結果 | 條件 | 下一步 |
|---|---|---|
| 年輕被低估 | S 的 90% 區間上界 < 0 | lead 另寫修正預註冊 |
| 老將被低估 | S 的 90% 區間下界 > 0 | lead 另寫修正預註冊 |
| 沒有可偵測的偏差 | 其他情況 | C 線結案，記「card 0.2.3 樣本外沒有年齡偏差」 |

- 另外報告（不作判準）：答案 Q 的 S 與分組；N 和 Q 的 S 差（用同一組 bootstrap）。
- 不准看過結果後改年齡分組、人群、答案定義或門檻（L-026）。

## 5. 不准

- 唯讀，用 sha256 檢查（L-037）：`reports/impact-rapm/`、`reports/ovr-v58-holdout-2025-26/`、`reports/card-0.2.2/`、`reports/card-0.2.3/`、`reports/card-0.2.2+E073-usage-evidence/`、`data/`。
- 新程式和新輸出只放 `reports/card-0.2.3+E081-age-residual/`。2025-26 分半單季 RAPM 輸出成 `rapm1-A.csv`、`rapm1-B.csv`（欄位：playerId、name、net、O、D、poss），之後 E-082 會用。
- 不改卡片、不碰 memory/、`src/`、live/、gh-pages；不 commit、不 push。
- 子程序一律帶 `creationflags=subprocess.CREATE_NO_WINDOW`。
