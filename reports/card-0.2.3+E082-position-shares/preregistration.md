# E-082 預註冊：位置改用先發分鐘比例（取代單一位置標籤）

- 日期：2026-10-29。來源：使用者目標「位置錯誤，跨季RAPM，新秀vs老將」的 A 線。
- 版本：`card 0.2.3+E082`（R-018）。基準：正式卡 card 0.2.3（R-040）。
- git HEAD（寫本檔時）：d5e1936。角色：實作 role-card；判讀 lead。

## 0. 背景與假設

- 位置標籤的來源已查明：校準目標 `calibration-target-B12.csv` 的 position 欄，是 2025-26 官方 box score 中「先發秒數最多的位置」。產生邏輯在 `reports/ovr-2025-26-positional/protocol.mjs`：五個位置齊全的 box 照官方位置；只有 G/F/C 的 box，後衛依助攻率、前鋒依身高排。
  - 先發不到 5 次的球員，改用身高帶（`build_season_league.js` 的 `posOfHeight`）。
  - 標籤沒有錯：三人在官方 box 裡確實多半以 PF 先發。Jalen Williams 在五位置齊全的 box 中是 PF 19 場、SF 14 場。
- 卡片在三個地方用到位置，都是單一的硬標籤（`reports/card-0.2.0+E071-pressure/calibrate-wing.py`）：
  1. `design()` 的位置交互項：long、short、pass、rebound、help × 位置虛擬變數。
  2. `attach_rapm()`：r 減去該位置以 MIN 加權的 0.75·N 平均。
  3. `pos_mean_d()`：防守加成的 centeredD 減去該位置平均。
- H：不少先發球員分在兩個位置之間（五位置齊全的 box 中，有 5 次以上先發的 330 人裡，71 人最常打的位置佔不到 60%）。硬標籤在邊界上造成跳動。改成依先發秒數比例混合各位置之後，樣本外的每場量尺不會變差。

## 1. lead 已看過的（揭露）

- 單人反事實（只改校準端，card 0.2.2 P1 primary，`reports/diag-position-labels/`）：
  - 把 Jalen Williams 改標成 SF，pred +0.239，每場名次 70→61。
  - 把 Jalen Johnson 改標成 SF，pred +0.251，名次 74→61。
  - 把 Banchero 改標成 SF，pred +0.496，名次 326→233。
  - 主要來源是 PF 的防守加成置中值比 SF 高（Williams 0.083→0.504、Johnson 0.583→1.129）；Banchero 則是位置交互項。
  - v0 逐位元重現 card 0.2.2 P1 primary。
- 上面的邊界人數統計和前 25 名邊界名單。
- **沒看過**任何比例混合的結果、任何候選卡的樣本外數字。

## 2. 比例

- 秒數 s_ip：每個球員在 2025-26 每個先發位置上的先發秒數，投票邏輯完全照 `protocol.mjs`。來源是 `reports/defense-tenth/step4-t0/2025-26/bundle.json`；用 node 匯出 `roles` 的 `secondsBySlot`、`starts`、`lowConfidence`。
- 比例 = s_ip / Σ_p s_ip。`lowConfidence`（先發 < 5 次）或沒有投票的球員，比例是原標籤的 one-hot。
- (s0) 自檢：每個非 lowConfidence 球員比例最大的位置，必須等於 `calibration-target-B12.csv` 的 position。不符的超過 3 人就停下回報；3 人以內就列出名單，照比例做。
- 模擬目標 y（以原位置跑出來的）不重跑，這是本實驗的限制，要寫進報告。

## 3. 改動（複製的 `calibrate-wing.py`，用 `--posShares CSV` 開關，不帶時完全不變）

- `design()`：位置 p 的虛擬變數從 1[pos=p] 改成比例 π_ip，基準組（C）不變。
- `attach_rapm()`：μ_p = Σ_i MIN_i·π_ip·0.75·N_i / Σ_i MIN_i·π_ip（池同現在，poss ≥ BLEND_POSS）；r_i = 0.75·N_i − Σ_p π_ip·μ_p。
- `pos_mean_d()` 和 centeredD：同樣的加權方式。
- 其他用到 pos 的地方（例如 `--restrictPos`）不改，並在報告列出。
- 卡片管線：照 card 0.2.2 `run_cards.py` 的 P1 primary、fitA、fitB → E-075 `e075.py`（主規格，輸入路徑換成新卡）→ 照 `build_card_023.py` 組 ranking。屬性、迴歸形式、E-075 特徵全部不動。

## 4. 判定

| # | 條件 | 門檻 |
|---|---|---|
| (c0) | 開關關掉（one-hot）重現 | card 0.2.2 P1 三份輸出與 card 0.2.3 ranking.csv 的 sha256 相同，或共同欄位最大差 < 1e-9 |
| (c1) | G1 | `npm test` 過 |
| (c2Q) | 舊量尺不變差 | E-064 §3.2（另一半 pooledNet × 另一半 MPG），ρ(候選) − ρ(card 0.2.3) 的 90% 區間下界 > −0.02；兩方向平均，球員 bootstrap 2000、seed 1 |
| (c2N) | 現況量尺不變差 | 同上，答案改用另一半 2025-26 單季 RAPM net（E-081 輸出的 `reports/card-0.2.3+E081-age-residual/rapm1-{A,B}.csv`）× 另一半 MPG；下界 > −0.02；另報下界是否 > 0 |
| (c3) | evaluate 閘數不減 | ≥ card 0.2.3（18/19） |
| (R2)–(R4) | 同 E-075 | 基準是 card 0.2.3 |

- (c0) 不過：停下修程式，不看任何誤差數字。
- 全過：記為「通過」，交使用者做 G5、定版本。(c2N) 下界 > 0 → MINOR，否則 PATCH（R-019）。
- 任一不過：不採用。
- 不准看過結果後改比例定義、門檻或回退規則（L-026）。

## 5. 只報告

- 三人（Banchero、Jalen Williams、Jalen Johnson）的 OVR、名次與比例；前 20 名；OVR 變動最大的 20 人。
- 比例最大位置佔不到 60% 的球員，平均 |ΔOVR| 和其他人比。
- 各位置前 30／60／100 名人數，和 card 0.2.3 比。

## 6. 不准

- 唯讀，用 sha256 檢查（L-037）：`reports/impact-rapm/`、`reports/ovr-v58-holdout-2025-26/`、`reports/card-0.2.2/`、`reports/card-0.2.3/`、`reports/card-0.2.2+E073-usage-evidence/`、`reports/card-0.2.3+E081-age-residual/`、`reports/defense-tenth/`、`data/`。
- 新程式和新輸出只放 `reports/card-0.2.3+E082-position-shares/`，並附上和原檔的 diff。
- 不改模擬（`src/`）、屬性；不碰 memory/、live/、gh-pages；不部署、不 commit、不 push。
- 子程序帶 `CREATE_NO_WINDOW`。
