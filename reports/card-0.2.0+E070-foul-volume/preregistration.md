# E-070 預註冊：製造犯規（foulDraw）改成以量為主

- 日期：2026-10-29（使用者裁定 R-034：「VOL應該比較重要 需要佔據超過70%的比例」→ 選 vol 0.75）
- 版本：`card 0.2.0+E070`（R-018）。換定義、不以變準為目標，預期是 PATCH；版本號在使用者看完結果後再定。
- 基準：`card 0.2.0`（`reports/card-0.2.0/`）。收縮沿用 E-055 方法 (c)（`reports/ovr-v61-shrink-history-2025-26/`）。
- 角色：role-card 實作；判讀由 lead；數字由 role-audit 另外重算。

## 1. 問題（lead 已看過的東西，已揭露）

card 0.2.0 的 foulDraw＝收縮後 FTA/FGA 的池內百分位，只看比率。SGA 在網站的製造犯規榜排不進前段，長人和出手少的人排在前面。

lead 看過 E-068（`reports/fd-volume-compare-2025-26/`，探索、未收縮、原始值）：
- 名次（rate／vol）：SGA 55／8、Luka 59／5、Embiid 51／6、Gobert 18／103、Adams 24／148。
- 相鄰季 Spearman：rate 0.832、vol 0.844。
- 半樣本外對 RAPM 的增量係數：兩種定義都 ≈0。

權重 0.75 是使用者的語意裁定（R-034），不是擬合出來的，本實驗不調它。**任何收縮後 vol 或合成 FD 的數字都還沒看過。**

## 2. 定義（寫死）

1. **rate**：沿用 card 0.2.0 的收縮後 FTA/FGA 比率（`build_attrs.py` 現行的 k、λ、kh、m，不重擬合）。
2. **vol**：FTA/36 = FTA ÷ (MIN/36)，n = FTA、d = MIN/36。用 E-055 方法 (c) 收縮：
   - rate_vol = (n1 + k·T)/(d1 + k)；T = (Σⱼ λ^(j−1)·nⱼ + kh·m)/(Σⱼ λ^(j−1)·dⱼ + kh)，j 取前 1–3 季。
   - k、λ、kh 用 `K_GRID`、`LAM_GRID`、`KH_GRID`；m 的「聯盟平均或同位置平均」照 E-055 規則選。全部只在 2025-26 以前的季，以 E-055 回測框架（前季＋上半季 → 下半季）最小化 MAE。這是程序，不是看結果調參。
   - 季別同 foulDraw（`ATTR_SEASONS['foulDraw']`）；下半季分母下限 `MIN_D2` = 300 分鐘（即 d ≥ 300/36）。
3. **合成**：FD = percentile_pool(0.75·z(vol) + 0.25·z(rate))。
   - z 用池內平均和標準差；池 = GP≥30 且 MPG≥20（和現行 foulDraw 相同）。
   - 百分位函式、1–99 封頂、池外的人也對池內分布取值，都和現行 foulDraw 相同。
4. 開關：w_vol = 0 時必須回到現行 foulDraw（見 c0）。

## 3. 判定

### 3.1 收縮檢查（只報告，不當閘門）
- vol 在測試季 2025-26 的下半季 MAE：收縮版 vs 不收縮（k=0）vs 只用上半季。
- 擬合出來的 k、λ、kh、m 的選法。

### 3.2 卡片層

照 card 0.2.0 鏈路重算：`build_attrs.py`（只換 foulDraw）→ `calibrate-wing.py --attrSource`（card 0.1.2 那份，含 E-060 onBall）→ 每場 OVR（card 0.2.0 的 r_repl 與錨點規則，在新池上重算 PR10／PR1／PR50／PR99）。fitA／fitB 卡照 E-064／E-066 的做法重建（只用一半 RAPM 擬合）。可以參考 `reports/card-0.2.0+E066-recency-target/e066.py` 的鏈路。

| # | 條件 | 門檻 |
|---|---|---|
| (c0) | w_vol=0 重現 card 0.2.0 | `reports/card-0.2.0/ranking.csv` 逐位元相同，或最大差 < 1e-9 |
| (c1) | G1 | `npm test` 過 |
| (c2) | 每場影響力樣本外不變差（G4） | 照 E-064 §3.2：RAPM 分半 A→B／B→A，答案＝RAPM_另一半 pooledNet × MPG_另一半，人群 pooledPoss≥2500 且兩半各 ≥5 場；ρ(候選) − ρ(card 0.2.0) 兩方向平均，90% 區間下界 > −0.02（以球員配對重抽 2000 次、seed 1） |
| (c3) | evaluate 閘數不減 | `evaluate.mjs` 通過數 ≥ card 0.2.0 |

只報告：
- foulDraw 在 calibrate 的係數（每 10 點）與 bootstrap SE，和 card 0.2.0 並排。
- 2K27 ρ（每場、每 36 都列）。
- OVR 前 20 名和 card 0.2.0 的差異；OVR 變動最大的 15 人。
- foulDraw 前 20 名（卡片 582 人內排名）。
- G5 抽查名單：SGA、Luka Dončić、Joel Embiid、Giannis、Jalen Brunson、James Harden、Trae Young、Jimmy Butler III、Rudy Gobert、Steven Adams、Dwight Powell、Mason Plumlee、Alex Antetokounmpo。列 FD 新／舊值、FD 名次、OVR 新／舊與名次。

採用規則：(c0)–(c3) 全過就記為「通過」，交使用者做 G5 並定版本。有任何一項不過，就記錄結果，卡片不變，回報使用者。

## 4. 不准

- 看過數字之後，改 0.75、z 的池、百分位函式、`MIN_D2`、門檻、季別或 seed（L-026）。
- 看過 G5 名單任何人的結果後，回頭改定義。
- 動現行輸出：`reports/card-0.2.0/`、`reports/ovr-v61-shrink-history-2025-26/`、`reports/card-0.1.1+E060-onball-targeting/`、`reports/card-0.1.2+E064-pergame/`、`reports/card-0.2.0+E066-recency-target/` 都唯讀。新輸出只寫到 `reports/card-0.2.0+E070-foul-volume/`。
- 動其他進行中實驗的目錄（`reports/handle-E069/`、`reports/card-0.2.0+E069-fringe-repl/`）。
- 動賽中名單、`live/`、gh-pages、每日排程、模擬（`src/`、`data/season-league*.json`）。
- 部署、commit、push。
