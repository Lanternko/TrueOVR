# v56 卡片修正：防守低估修正（以 Rudy Gobert 為案例）

本檔案在跑任何 F1/F2/F3 結果之前寫成，鎖定方法、候選值與門檻，避免事後 cherry-pick。
延續 [`reports/ovr-v55-card-E-2025-26/`](../ovr-v55-card-E-2025-26/)（E 系列），基準是現任正式卡片
**E2-λ0.4**（`reports/ovr-v55-card-E-2025-26/card-E2-lam0.4/ranking.csv`）。本任務**不修改吃餅折扣
本身**，只在 E2-λ0.4 之上疊加防守修正。

## 診斷（跑任何修正前）

### 1. 回歸公式裡防守屬性的權重從哪裡來

OVR 由 `reports/ovr-calibrated-2025-26/calibrate.py` 的加權最小平方回歸（ridge，form=
`position-interactions`，λ=1.0）產生：目標 `y` 是「v47 模擬每 36 分鐘貢獻」與「RAPM pooledNet
（位置置中）」的 `alpha=0.5` 混合；輸入是 15 個標準化屬性（`long,mid,short,ft,drive,tovSkill,pass,
rebound,physique,onBall,help,stamina,heightInches,creation,pressure`）＋對非中心位置（PG/SG/SF/PF，
C 為參考組）的 5 個屬性（`long,short,pass,rebound,help`）交乘項。**卡片屬性裡沒有獨立的「蓋帽/護框」
屬性**——2K27 的 `k_block`、`k_intd`、`k_perd`、`k_helpd` 只在 `merged.csv` 裡當比較欄位，從未進入
回歸；本遊戲引擎用 `help`（協防）＋`onBall`（單防）＋`rebound`（籃板）這三個既有屬性間接承載「護框」
這個籃球概念。

E2-λ0.4（`card-E2-lam0.4/summary.json`）裡，C／PF（參考組）的每 10 屬性點價值（`valuePer10AttributePoints`
主效應，單位＝每 36 分鐘模擬目標分，含 bootstrapSE）：

| 屬性 | per10 (C/PF 參考組斜率) | bootstrapSE |
|---|---|---|
| short | 0.570 | 0.172 |
| pass | 0.713(主效應，C 參考) | 0.110 |
| help | 0.477 | 0.127 |
| long | 0.413 | 0.167 |
| stamina | 0.385 | 0.038 |
| onBall | 0.209 | 0.087 |
| rebound | 0.148(主效應) +0.215(PF交乘)=0.363(PF) | — |
| heightInches | -0.560 | 0.527（不顯著，SE 比係數大） |

`help` 的斜率（0.477）其實不算小，接近 `short`（0.570）的八成；問題不在回歸係數本身被低估，而在
**屬性本身的聯盟離散度（標準差）嚴重不對稱**：`onBall` 的 SD 只有 5.80（全部 15 屬性裡最小），
`help` 的 SD 是 8.96，兩者都遠小於 `drive`(19.4)、`pass`(18.3)、`rebound`(18.3)、`tovSkill`(19.8)
這些進攻／籃板屬性。換句話說，即使 `onBall`/`help` 每一點的「價格」不便宜，聯盟裡這兩個屬性的
「貨量」（跨球員差異）被壓縮得很窄，頂尖防守者能靠它們賺到的總分因此被天花板鎖住——這是屬性建構層
（`build_season_league.js`）的問題，本任務依限制不得修改該腳本，故改從「回歸目標」與「獨立外部
驗證信號」兩個不動屬性建構層的角度處理。

### 2. RAPM pooledD 前 30 名在卡片／2K27／RAPM pooledNet 的名次對照

見 [`diagnose.mjs`](./diagnose.mjs)（唯讀腳本）產出的 [`diagnose-top30-pooledD.json`](./diagnose-top30-pooledD.json)。
重點發現：

- **防守低估不是「大個子」專屬問題，是「低進攻技巧、高防守價值」球員的普遍問題**：被卡片最嚴重低估
  （卡片名次遠差於 2K27／RAPM 名次）的前幾名其實是側翼／後衛防守專才——Herbert Jones（差 418 名）、
  Alex Caruso（差 302 名）、Marcus Smart（差 289 名）、Christian Koloko（差 378 名）、Matisse
  Thybulle（差 249 名），差距都遠大於 Gobert 的 59 名。
- Gobert（pooledD 聯盟第 3）卡片排 91，RAPM pooledNet 排 32、2K27 排 60.5——卡片比兩者都差，但差距
  （59 名）在這份前 30 名單裡只排在中段，不是最極端的案例。
- 進攻技巧尚可的防守長人（Wembanyama、Chet、Embiid、Anthony Davis、Aaron Gordon）卡片名次大致合理
  甚至略優於 RAPM／2K27，說明回歸本身認得出「防守＋進攻都強」的球員，真正系統性漏接的是「進攻技巧
  差、防守技巧／價值高」這個象限。

### 3. 本任務的修正範圍

**不**打算做「全聯盟防守屬性離散度重建」（那是屬性建構層的事，超出本任務「以 Gobert 為主要案例、
疊加在 E2 之上」的授權範圍，也會動到太多其他球員，風險不可控）。本任務只做**回歸目標**與**獨立
外部驗證信號**兩個不改變屬性本身、不改變吃餅折扣的修正，優先用固定先驗（不自由估係數，吸取 C1
教訓）。

## F1：校準目標防守加權（RAPM pooledD 在混合目標裡的權重提高）

沿用 `calibrate.py` 既有的 `attach_rapm`/`blended` 機制（`alpha=0.5` 不變，仍是模擬與 RAPM 各半），
但把原本 RAPM 那一半用的 `pooledNet` 換成 **`R_β = pooledO + (1+β)·pooledD`**——攻擾值不變，防守值
乘上 `(1+β)` 倍的固定係數。`β=0` 等於原本的 `pooledNet`（因為 `pooledO + pooledD = pooledNet`）。
其餘流程（位置置中、`BLEND_POSS=1000`、`BLEND_PER36=0.75`、`alpha=0.5`）完全不變，只換被置中的
那個量。**係數 `β` 是跑結果前選定的固定先驗，不是回歸自由估計出來的。**

候選：`β ∈ {0.5, 1.0}`（防守算 1.5 倍或 2 倍權重）。

風險（跑結果前已知，如實記錄）：這是全聯盟性修正，Karlo（PF，RAPM pooledD=+1.41，略高於 PF 聯盟
均值 0.29）、Isaiah Stewart（卡片位置 SF，pooledD=+0.80，略高於 SF 均值 0.21）本身防守數據並不差，
F1 有可能把他們的名次往回拉、侵蝕 E2 好不容易做到的「Karlo 掉 ≥10／Stewart 掉」門檻。Collins
（pooledD=-0.23）、Garza（pooledD=-1.30）防守數據在均值之下，F1 預期會強化（而非破壞）他們「掉名」
的門檻。

## F2：獨立防守加分項（直接用 RAPM pooledD 當外部驗證信號，固定係數加成，不進回歸）

只對 **`pos ∈ {PF, C}`** 且 **`pooledPoss ≥ 5000`**（與驗收門檻用的樣本池一致）的球員，在
回歸算出 `pred`（標準化後的每 36 分鐘預測值，percentile 映射到 OVR 之前）加上固定加成：

```
posMeanD(pos) = MIN 加權平均 pooledD，樣本池 pooledPoss ≥ BLEND_POSS(1000)，同 pos 分組
centeredD(player) = BLEND_PER36(0.75) × pooledD(player) − posMeanD(pos(player))
bonus(player) = γ × max(0, centeredD(player))        若 pos ∈ {PF,C} 且 pooledPoss ≥ 5000
bonus(player) = 0                                     其餘情況
pred_new = pred + bonus
```

**修正（跑任何結果前自查發現）：** 這裡的 `pos` 必須是 `calibrate.py` 迴歸與輸出 `ranking.csv` 實際
使用的 `pos`——即 `calibration-target-B12.csv` 的 `position` 欄位（`load()` 裡 `r['pos'] = r['position']`，
同一個欄位也決定 position-interaction 設計矩陣與最終 `ranking.csv` 的 `pos` 欄）。這**不是**
`data/season-league.json` 卡片原始的身高分桶 `p.pos`。兩者對 Isaiah Stewart／Jalen Smith 剛好不同：
身高分桶是 SF，但 `calibration-target-B12.csv`／`ranking.csv` 裡兩人都標記 **PF**（已用
`grep "Isaiah Stewart\|Jalen Smith" calibration-target-B12.csv` 與 `card-E2-lam0.4/ranking.csv`
直接核對）。先前草稿誤用身高分桶位置、誤判兩人會被 PF/C 條件排除，現已更正：以下風險表改用正確的
`ranking.csv` 位置（PF/C）重新計算 `centeredD`，`pos` 分組與 `BLEND_POSS=1000` 池也改用同一欄位，
與 `calibrate.py` 的 `attach_rapm` 分組邏輯完全一致。限定 `PF/C` 是因為本任務的診斷重點與使用者指定
案例都是大個子禁區防守，側翼／後衛的類似問題（Herbert Jones、Caruso 等）留給之後的任務，避免一次
修正牽動過多不在本次驗收範圍內的球員排名。

候選：`γ ∈ {0.5, 1.0}`。

跑結果前用 `ranking.csv`／回歸實際使用的 `pos` 欄位重新算出的 7 人防守代理值（`BLEND_PER36×pooledD
− posMeanD(pos)`，正值代表比同位置池均值更會防守；`posMeanD` 用 `BLEND_POSS=1000` 池、MIN 加權，
與 `calibrate.py::attach_rapm` 算 `mu` 的方式一致）：

| 球員 | pos（ranking.csv） | pooledPoss | pooledD | centeredD |
|---|---|---|---|---|
| Rudy Gobert | C | 35467 | 4.999 | **+3.175** |
| Neemias Queta | C | 11841 | 2.481 | +1.287 |
| Karlo Matković | PF | 6813 | 1.409 | +0.631 |
| Isaiah Stewart | PF | 21999 | 0.799 | +0.173 |
| Jalen Smith | PF | 18094 | 0.604 | +0.027 |
| John Collins | PF | 28189 | −0.229 | −0.598 |
| Luka Garza | C | 6670 | −1.296 | −1.546 |

Gobert 的 centeredD（+3.175）遠高於其餘入選球員，這正是本修正的目標。**Collins／Garza 為負值，
加成為 0，不受影響**（預期不干擾他們「掉名」的門檻）。**Stewart（+0.173）／Jalen Smith（+0.027）
確實會落入 PF/C 條件、拿到非零但很小的加成**（γ=1.0 時最多分別加 0.173／0.027 個 per36 單位，
相較於 E2-λ0.4 下兩人的 `predictedPer36`——Stewart 0.746、Jalen Smith 0.292——量級遠小於 1 成，
預期不足以逆轉他們「掉名」的方向，但跑完仍需實際檢查門檻，不能只憑事前估計斷定安全）。唯一需要
密切關注的風險仍是 **Karlo（PF，+0.631）**：γ 越大，Karlo 掉 ≥10 名的門檻風險越大（已知風險，如實
記錄，跑完看數據決定是否通過）。

## F3：F1 + F2 合併

固定取「F1 選出的代表 β」＋「F2 選出的代表 γ」疊加（先重新校準目標換 β、重跑回歸拿到新的 `pred`，
再對新 `pred` 加 F2 的固定加分項），避免從 2×2 組合裡事後挑對自己有利的一組。

## 代表版本選擇規則（F1、F2 各自獨立選，跑結果前鎖定）

同 E 系列既有規則：候選裡全部通過 9 項門檻（含下方新增的 rhoDef 僅供回報、不計入 9 項）者，取
ρ(2K27) 最高者代表該方向；若沒有任何候選全過，取「過門檻數最多」者，同分再取 ρ(2K27) 較高者。

## 驗收門檻（與任務指定一致，9 項＋ rhoDef 回報）

1. Gobert 名次 ≤ max(2K27 60.5, RAPM pooledNet 名次 29) = 60.5（2K27 或 RAPM 其一准即過，用
   `reports/status/status_snapshot.py` 的 `V55_CHECKS` 同一條件：`b <= ref`）。
2. E2 已過的 6 人門檻不可退步：Karlo 掉 ≥10（對 v53）；Collins／Stewart／Garza 比 v53 下降；
   Queta 名次 ≤ max(2K27, RAPM)=110.5；Jalen Smith 名次 ≤ 220。
3. ρ(2K27) ≥ 0.4746 − 0.005 = 0.4696；ρ(RAPM pooledNet, pooledPoss≥5000) ≥ 0.5290 − 0.005 = 0.5240。
   另外回報 `rhoDef`（OVR 對 `pooledD` 的 Spearman ρ，同一 pooledPoss≥5000 池）是否比 E2-λ0.4 的
   基準值上升（先計算 E2-λ0.4 的 rhoDef 當基準，F 系列跑完後比較）。
4. 前十名只能出現 Wembanyama／Giannis／Jokić／Chet 這四位長人（觀察用；多了其他長人要寫出來）。
5. 不加旗標時 `node scripts/build_season_league.js` 輸出與現有 `data/season-league.json` SHA256
   相同（`497725ecb6a2ec181aeb3cf93263f53a81bdfed772a2c4c733ba3a2d65a79bf6`）——本任務不碰這兩者，
   預期必過，仍會在報告列出驗證指令。

## 實作方式

新增 `reports/ovr-v56-card-defense-2025-26/calibrate-defense.py`，從
`reports/ovr-calibrated-2025-26/calibrate.py` 複製核心邏輯（唯讀原檔，不修改），加上
`--direction=F1|F2|F3` 與 `--beta`/`--gamma` 參數。輸入固定為
`reports/ovr-v55-card-E-2025-26/season-league-E2-lam0.4.json`（E2-λ0.4 的卡片 league，已內含吃餅
折扣，本任務不重做）、`--target reports/ovr-v55-finisher-fix-2025-26/card/calibration-target-B12.csv`、
`--alpha 0.5`，與官方卡片建構命令一致。輸出 `ranking.csv`/`summary.json` 格式對齊既有慣例，另寫
`evaluate.mjs`（唯讀）彙總 9 項門檻＋rhoDef 回報＋Top-10。
