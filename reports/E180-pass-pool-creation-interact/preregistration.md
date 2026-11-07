# E-180 預註冊：傳球改全位置共用斜率（修 E-179 的傳球偏高）

- 日期：2026-11-01。來源：使用者看完 E-179（creation 前鋒高估、pass 全位置偏高）後說「寫修正預註冊」。
- 基準：card 0.2.9a（`reports/card-0.2.9a/ranking.csv`；建卡管線＝E-164 S 臂，位置只在 `reports/card-0.2.9+E164-no-stamina/calibrate_wing_t.py` 讀，見 E-177 `phase0.md`）。
- 狀態：已凍結（2026-11-01，使用者「核可」，並裁定改用上一季判定）。
- 2026-11-01 使用者選「A」：只留臂 A，原草稿的臂 B（creation、foulDraw 加位置交互項）刪除。

## 0. 已揭露（lead 寫本檔前看過的東西）
- E-179（三個歷史原點對下季 RAPM）：creation 的前鋒−後衛殘差差 −0.14 [−0.25, −0.03]；pass 前鋒 −0.32、後衛 −0.29，差不顯著；foulDraw 差 −0.17（只報告）。這三季的下季 RAPM 對本問題已部分看過；使用者裁定仍用上一季判定（§2，R-113）。
- E-176／F-113：2025-26 同季外部進攻殘差（樣本內）。
- 卡片設計：`INTERACT = ['long', 'short', 'pass', 'rebound', 'help']`，位置虛擬變數 PG／SG／SF／PF（C 為基準），ridge 1.0。**creation、foulDraw 沒有位置交互項**，所以 E-179 看到的前鋒 creation 偏差不是交互項造成的；可能來源是 T6 目標本身、或和 pass 交互項共線（L-095）。
- 歷史原點的能力值是 2025-26 現值（L-091）。
- **沒看過**任何改動後的卡片、OVR、名次。臂 A 是結構改動，沒有可調數值；判定不得以 JW 或任何單一球員為條件，JW 只列在例子表。

## 1. 臂（只動 `INTERACT`，其餘照 0.2.9a）
| 臂 | INTERACT | 想法 |
|---|---|---|
| K0 | long, short, pass, rebound, help | 0.2.9a 原樣。c0：重建後 2025-26 ranking 與 `reports/card-0.2.9a/ranking.csv` 逐位元相同，不同就停 |
| A | long, short, rebound, help | 傳球不分位置，一條斜率（E-179：pass 偏高不分位置） |

不動：能力值、目標 T6、ridge、RAPM 混合、用人層、映射錨、r_repl、賽中管線、名單頁、`season_nav.off_def`。

## 2. 檢查與判定（一次跑完）
- 使用者裁定（2026-11-01，R-113）：「用上季，不要一直跟我扯資料不夠要等」→ 判定用上一季：2024-25 歷史原點卡對 2025-26 RAPM，不等 2026-27。
### 2a. 不劣於檢查（2025-26 現行卡）
- c0（K0 逐位元）、`npm test` 過。
- 2025-26 卡（MIN ≥ 500）：
  - s1：Spearman(OVR, 薪水 errata-1 權重) 與 Spearman(OVR, 2K `data/external-impact/2k/2k-merged-e142.csv`)，A−K0 的球員層 bootstrap（2000 次，seed 20261101）90% 下界 > −0.01。
  - s2：隊內 MIN–OVR Spearman 30 隊中位數，A 不低於 K0 超過 0.02。

### 2b. 判定（2024-25 原點 → 2025-26 RAPM）
- 卡片：2024-25 歷史原點，K0h＝0.2.9a 底現行標籤（照 E-177 K0h 建法，c0h：重建後與 `reports/card-0.2.9a+E177-bbref-position-shares/ranking-K0-2024-25.csv` 逐位元相同，不同就停）；Ah＝同一原點、INTERACT 拿掉 pass。
- 答案：`reports/card-0.2.7+E126-tank-next-season/rapm-2025-26.json` 的 `net`、`O`，乘 `wfun(2025-26 mpg)`；人群照 E-179 §2。
- 統計量照 E-179 §3（另加全人群 S_all(a, e_net)）：e_net＝pct(net×W)−pct(OVR)，前鋒 F＝SF/PF、後衛 G＝PG/SG（K0h 的硬標籤，兩臂同一份分組）；D_a＝S_F(a, e_net)−S_G(a, e_net)。bootstrap 2000 次，seed 20261101，90% 區間；臂間差在同一組重抽上算。
- 判定：
  - **前提 p0**：K0h 的 S_all(pass, e_net) 上界 < 0。不成立 → 判「偏差沒出現，不改卡」。
  - **A 採用候選**同時滿足：
    - ① S_all(pass, e_net)，A−K0 的下界 > 0（傳球偏高變小）；
    - ② Spearman(OVR, net×W)，A−K0 下界 > −0.01（整體不變差）；
    - ③ 2a 的 c0、s1、s2 都過。
  - 不是候選 → 不採用。
- 只報告：D_pass、D_creation、D_foulDraw（前鋒 creation 偏差 A 不一定處理得到，照實列）、S_F／S_G／S_C；e_O 版本；另兩個原點（2022-23、2023-24）同一套統計量；JW、Jalen Johnson、Paolo Banchero、Scottie Barnes、Franz Wagner、LeBron James 的兩臂 OVR／名次與 OFF 拆解（2025-26 卡）。
- 揭露：這一季在 E-179 已看過分組 S（pass 前鋒、後衛都偏負），S_all 與 A 臂沒看過；能力值是 2025-26 現值（L-091）。結果是「有揭露的樣本內」，不是乾淨的樣本外。

## 3. 只報告（2025-26 卡）
- 兩臂的係數表（pass、creation、foulDraw 各位置的有效斜率＝主效應＋交互項）。
- 前鋒內 pass 與 creation 的 Spearman（看共線）。
- 2025-26 前 20 名進出、OVR 變動最大的 20 人、上面例子球員。

## 4. 限制
- 只寫 `reports/E180-pass-pool-creation-interact/`；0.2.9a、E-164、E-153、E-142 目錄唯讀；不改 `src/`、不改賽中管線。
- T6 目標不動；若偏差來自 T6 本身，A 可能無效（那會是 p0 成立、① 不過）。前鋒 creation 偏差不在 A 的處理範圍。
- 0.2.9a、E-164、E-177 目錄唯讀。
- 回報用六段格式（CLAUDE.md）。

## 5. 產出
- `e180_build.py`、`e180_eval.py`、`ranking-{K0,A}-{2022-23,2023-24,2024-25,2025-26}.csv`、`results.json`、`report.md`。
