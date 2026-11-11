# v56：防守低估修正（以 Rudy Gobert 為案例）

本報告為派工任務 20261020-121356-bf2b6b（第 1 輪）的交付。方法與門檻已在跑任何結果前寫入
[`preregistration.md`](./preregistration.md)，本文件只做結果彙報與驗收，不追加新假設。

## 背景

正式卡片 v55 E2-λ0.4（`reports/ovr-v55-card-E-2025-26/card-E2-lam0.4/`）的吃餅折扣（finish
discount）判定正確：Gobert 進攻確實弱，折扣不應放鬆。但 Gobert 排 91（OVR 77.9），遠低於 2K27
（60.5）與 RAPM pooledNet（32）兩個外部基準，顯示問題出在**防守沒被記到分**，不是折扣過頭。本任務
目標：只從「更好地計入防守價值」下手，不碰吃餅折扣。

## 診斷摘要（詳見 preregistration.md 第一節與 `diagnose.mjs`/`diagnose-top30-pooledD.json`）

1. `help`（協防）的回歸斜率（0.477/10 分）其實不算小，接近 `short`（0.570/10 分）；真正問題是
   `onBall`（SD=5.80）、`help`（SD=8.96）兩個防守屬性的聯盟離散度是 15 個屬性裡最小的兩個——即使
   單點「價格」不低，頂尖防守者能靠它們跟均值拉開的「量」被結構性壓縮，總分因此被鎖住。這是屬性
   建構層（`build_season_league.js`）的問題，本任務依限制不得修改該檔，故改從回歸目標與獨立外部
   防守信號切入。卡片屬性裡**沒有獨立的「蓋帽/護框」屬性**，2K27 的 `k_block` 等子評分從未進入
   回歸。
2. 比對 RAPM pooledD 前 30 名，發現「防守被低估」不是大個子專屬問題，側翼防守專才（Herbert Jones、
   Caruso、Marcus Smart 等）被低估的幅度遠大於 Gobert。本任務依授權範圍只處理「大個子禁區防守」
   這個象限（疊加在 E2 之上、以 Gobert 為案例），側翼防守留待後續任務。

## 方法：三個固定先驗修正方向

全部疊加在 E2-λ0.4 的卡片 league（`reports/ovr-v55-card-E-2025-26/season-league-E2-lam0.4.json`）
之上，用 `calibrate-defense.py`（複製自 `reports/ovr-calibrated-2025-26/calibrate.py`，原檔未改動）
實作：

- **F1**：RAPM 混合目標防守加權。`attach_rapm` 置中用的量從 `pooledNet` 換成
  `R_β = pooledO + (1+β)·pooledD`，`β` 為固定先驗，候選 `{0.5, 1.0}`。
- **F2**：獨立防守加分。對 `pos∈{PF,C}` 且 `pooledPoss≥5000` 的球員，在回歸 `pred` 上加
  `γ·max(0, BLEND_PER36·pooledD − posMeanD(pos))`（只加分不扣分），`γ` 為固定先驗，候選
  `{0.5, 1.0}`。**修正記錄**：preregistration.md 初稿誤用 `data/season-league.json` 的身高分桶
  position 分析風險，實際生效的 `pos` 是 `calibration-target-B12.csv`／`ranking.csv` 用的欄位，
  已在 preregistration.md 自查更正並重算 7 人 centeredD 代理值，才開始跑任何結果。
- **F3**：F1 的代表 `β` 換目標重新擬合之後，疊加 F2 的代表 `γ`。

選版規則（跑結果前鎖定）：候選裡全過 9 項門檻者，取 ρ(2K27) 最高者代表；若無人全過，取過門檻數
最多者，同分再取 ρ(2K27) 較高者。

## 驗收總表（9 項門檻；地板用本次 `evaluate.mjs` 自己量到的 E2-λ0.4 基準，而非舊報告文字裡的
歷史數字，見下方「基準數字差異」說明）

E2-λ0.4 基準：ρ(2K27)=0.4778，ρ(RAPM pooledNet)=0.5290，ρ(RAPM pooledD)=0.2972，8/9（Gobert 門檻
未過）。

| 候選 | Karlo掉≥10 | Collins掉 | Stewart掉 | Garza掉 | Queta門檻 | Gobert門檻 | JalenSmith≤220 | ρ2k地板 | ρRAPM地板 | 過關 |
|---|---|---|---|---|---|---|---|---|---|---|
| F1-β0.5 | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | 8/9 |
| F1-β1.0 | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | 7/9 |
| **F2-γ0.5** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **9/9** |
| F2-γ1.0 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 9/9 |
| F3(β0.5,γ0.5) | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 8/9 |

**F1 單獨無法同時滿足「Gobert 要上」與「Karlo 要掉」**：β 加大能救 Gobert，但 Karlo 自己的
pooledD 也偏高，同一個全域重擬合會把他也往上推，兩個門檻互相拖累（preregistration.md 已預先記錄
此風險）。**F3 證實了這個風險會疊加放大**：F1(β0.5) 與 F2(γ0.5) 單獨都能讓 Karlo 掉 ≥10
（分別掉 11、12 名），但合併後 Karlo 只掉 8 名（rank 15 vs v53 rank 7），兩個加分機制疊加讓他
的漲幅超過各自單獨的總和，F3 因此以一票之差（Karlo）未過。

**F2 兩個候選都 9/9 全過。** 依規則在全過的候選裡選 ρ(2K27) 最高者：

| | ρ2k | ρRAPM | ρDef | Karlo掉名次（v53→現在，安全邊際） | 前十名裡多出的長人 |
|---|---|---|---|---|---|
| F2-γ0.5 | **0.4878** | 0.5700 | 0.3624 | 7→19，掉12（邊際+2） | Mobley、Embiid、Aaron Gordon |
| F2-γ1.0 | 0.4868 | 0.5925 | 0.4048 | 7→17，掉10（邊際+0，貼著門檻） | Mobley、Embiid、Gobert本人、Aaron Gordon |

γ=0.5 的 ρ(2K27) 較高，且 Karlo 的安全邊際較大（γ=1.0 下 Karlo 剛好卡在掉 10 名的門檻線上，
抗雜訊能力弱），γ=1.0 甚至把 Gobert 本人推進前十（rank 8），觀感上像過度修正。**故依選版規則，
F2 的代表版本是 γ=0.5。**

### 最終建議：採用 F2（γ=0.5）

- Gobert：rank 91 → **rank 13**（OVR 77.9 → 87.3），2K27 門檻 60.5、RAPM 門檻 32，兩者皆輕鬆通過。
- 其餘 6 人門檻全數維持：Karlo 掉 12 名、Collins/Stewart/Garza 皆比 v53 下降、Queta rank 28
  （≤ 門檻 110.5）、Jalen Smith rank 152（≤ 220）。
- ρ(2K27) 0.4778→0.4878（↑）、ρ(RAPM pooledNet) 0.5290→0.5700（↑）、ρ(RAPM pooledD)
  0.2972→0.3624（↑，防守擬合確實變好）。
- 機制簡單、風險可控：只加分不扣分，限定 `pos∈{PF,C}` 且 `pooledPoss≥5000`，不碰吃餅折扣、不碰
  回歸係數本身，是三個方向裡對既有 6 人門檻侵蝕最小的做法。

**不建議採用 F1 或 F3**：F1 單獨存在 Karlo／Gobert 兩難，無法兩全；F3 把兩個機制疊加後驗證證實
Karlo 門檻會被衝破，風險比單獨使用 F2 更高且沒有額外好處（ρ 數字介於 F1、F2 之間，不比純 F2 更優）。

## Top-10 檢查（驗收項 4：只能有 Wembanyama/Giannis/Jokić/Chet）

**重要獨立核實**：E2-λ0.4 基準本身的 top-10 就已經包含 **Evan Mobley**——`card-E2-lam0.4/ranking.csv`
直接確認（`node reports/ovr-v56-card-defense-2025-26/evaluate.mjs` 印出的 `E2-lam0.4 top10`）。
這與上一輪 `reports/ovr-v55-card-E-2025-26/report.md` 文字敘述「沒有 Mobley」矛盾（該報告的表格
其實也列出 Mobley★，是文字摘要寫錯，不是數據本身的問題）——此為既有基準的已知狀態，非本次修正
造成。

E2-λ0.4 基準 top10：SGA, Wembanyama, Jokić, Dončić, Chet, **Mobley**, Giannis, Murray, Durant,
Leonard → 違規長人：Mobley。

F2-γ0.5 top10：Wembanyama, SGA, Chet, **Mobley**, Jokić, Dončić, Giannis, **Embiid**,
**Aaron Gordon**, Murray → 違規長人：Mobley、Embiid、Aaron Gordon（比基準多兩位）。

F2 讓更多「進攻防守都強」的長人（Embiid、Aaron Gordon）擠進前十，是防守權重提高後的合理副作用
（這些人本就不弱於進攻），但確實比基準更偏離「只有 4 人」的理想狀態，應如實標記，留待下一輪決定
是否需要額外處理「強力長人過度集中在前十」的問題。

## 基準數字差異說明

`reports/ovr-v55-card-E-2025-26/report.md` 記載 E2-λ0.4 的 ρ(2K27)=0.4746、ρ(RAPM)=0.5290。本次
用自己寫的 `evaluate.mjs` 重新量測同一份 `card-E2-lam0.4/ranking.csv`，得到 ρ(2K27)=0.4778（RAPM
一致，0.5290 不變）。差異出在 2K27 比對時是否排除 `rank2k` 欄位空值的球員（本次腳本明確過濾
`merged.get(name).rank2k` 為真值才納入 Spearman 計算）；由於是同一份 ranking.csv 用不同腳本量出
的些微差異（0.0032），不影響任何門檻判斷方向，門檻地板一律取本次 `evaluate.mjs` 自己量到的
E2-λ0.4 數字（見上方驗收總表），確保基準與候選用同一套量測口徑比較。

## SHA256 驗證（未修改既有產物）

```
$ sha256sum data/season-league.json
497725ecb6a2ec181aeb3cf93263f53a81bdfed772a2c4c733ba3a2d65a79bf6 *data/season-league.json
```
跑完全部方向後重新核對，與任務指定雜湊值相符，`data/season-league.json`、
`scripts/build_season_league.js`、`runs/`、既有 `reports/` 產物均未被本任務觸碰或修改。

## 假設與限制

1. F2 只處理 `pos∈{PF,C}` 的禁區防守，側翼/後衛防守低估問題（Herbert Jones、Caruso 等，低估幅度
   遠大於 Gobert）刻意排除在本次授權範圍外，留待後續任務獨立評估、獨立門檻。
2. `posMeanD` 與 bonus 的 `pos` 欄位採用 `calibrate.py`/`ranking.csv` 實際使用的位置（來自
   `calibration-target-B12.csv`），不是 `data/season-league.json` 卡片原始的身高分桶 `pos`——兩者
   對 Isaiah Stewart／Jalen Smith 不同（身高分桶 SF，但此處算 PF）。此為跑任何結果前就發現並更正
   的事實性錯誤，preregistration.md 已完整記錄更正過程。
3. Top-10 裡「多出的長人」（Mobley/Embiid/Aaron Gordon）是已知副作用，如實回報但未納入本次 9 項
   硬門檻的通過/失敗判定（任務書將其列為「觀察並回報」而非與其餘 8 項並列的硬性門檻）。
4. F2 的加分是「後處理」疊加在回歸預測值（`pred`）上，發生在 percentile 映射到 OVR 之前；未重新
   跑 CV 選模型形式／ridge（沿用 E2-λ0.4、官方卡片既定的 `position-interactions` / ridge=1.0），
   與官方卡片建構慣例一致。
