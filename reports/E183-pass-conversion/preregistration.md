# E-183 預註冊：傳球的「率」改成傳球轉助攻（AST ÷ 傳球次數）

- 日期：2026-11-01。來源：E-180 不採用後，使用者說「助攻率和傳球變成助攻 意思不一樣」→「寫預註冊」。
- 基準：card 0.2.9a（`reports/card-0.2.9a/ranking.csv`；建卡管線＝E-164 S 臂，驅動照 E-180 `e180_build.py`）。
- 狀態：已凍結（2026-11-01，使用者「核可凍結」）。

## 0. 已揭露（lead 寫本檔前看過的東西）
- 現行 pass（E-125／R-074）＝池內百分位(0.5·zs(AST/36，收縮)＋0.5·zs(AST/astCh，收縮))。兩半都在量「助攻多少」：一半是量，一半是在場隊友進球中由他助攻的份額，都隨球權變大，沒有一半在量傳出去的球有多少變成助攻。
- E-179：pass 對下季 RAPM 殘差前鋒 −0.32、後衛 −0.29（三原點合併）。E-180：拿掉 pass 位置交互項沒有讓偏高變小；K0h（2024-25 原點）S_all(pass, e_net) 已看過，偏負。F-118 推測原因是 pass 量的是量不是效率。
- 傳球追蹤資料 `reports/handle-E069/raw/{2020-21…2025-26}/Passing-FULL.json`（NBA `leaguedashptstats` PtMeasureType=Passing，Totals；欄位 PASSES_MADE、AST、POTENTIAL_AST、AST_PTS_CREATED 等）。**只看過四人**的 AST／PASSES_MADE：JW 2024-25 0.112、2025-26 0.151（1200 次傳球，季中受傷）；Jokić 2024-25 0.132、2025-26 0.147；Haliburton 2024-25 0.125；LeBron 2024-25 0.145、2025-26 0.154。
- **沒看過**任何人改動後的 pass、OVR、名次，也沒看過 AST/PASS 和 RAPM 的關係。定義只有一個、權重沿用 0.5，沒有可調數值；判定不得以 JW 或任何單一球員為條件（L-026），JW 只列在例子表。

## 1. 臂
| 臂 | pass 定義 | 想法 |
|---|---|---|
| K0 | 0.5·zs(AST/36)＋0.5·zs(AST/astCh)（0.2.9a 原樣） | c0：重建後 2025-26 ranking 與 `reports/card-0.2.9a/ranking.csv` 逐位元相同；c0h：2024-25 原點與 `reports/E180-pass-pool-creation-interact/ranking-K0-2024-25.csv` 逐位元相同。不同就停 |
| Q | 0.5·zs(AST/36)＋0.5·zs(AST/PASSES_MADE) | 量那一半不動；率那一半換成「傳出去的球有多少變成助攻」 |

- AST/PASSES_MADE（下稱 conv）：
  - 來源：上面的 Passing-FULL.json，用 PLAYER_ID 對卡片人群；一季換隊有多列時，PASSES_MADE、AST 各自加總。
  - 收縮：二項式經驗貝氏，conv_s＝(AST＋k·μ_pos)/(PASSES_MADE＋k)。μ_pos＝該季同位置（卡片現行硬標籤）以傳球次數加權的 conv；k＝p̄(1−p̄)/τ² − 1，τ² 用動差法從 Var(conv_i)＝τ²＋p̄(1−p̄)/n_i 擬合（只用 PASSES_MADE ≥ 200 的人），夾在 [50, 2000]，τ² ≤ 0 時 k＝500。四季各自擬合 k（只用追蹤資料，不碰 RAPM）。寫法同 `scripts/build_season_league.js` 的 shootingReliability。
  - 對不到追蹤資料的人：conv_s＝μ_pos，列出人數。
  - zs、合併、四季合併池百分位、頂端尺都照 E-125 的 pass 寫法（`reports/card-0.2.7+E125-pass-volume/preregistration.md` §2），只把 AST/astCh 換成 conv_s。
- 歷史原點：K0h 的 pass 用哪一季的助攻資料，Q 就用同一季的追蹤資料。第 0 階段先寫 `phase0.md`，列出 K0h 的 pass 從哪個檔、哪一季來（L-091：歷史原點的能力值可能是 2025-26 現值），以及 Q 對應的換法；換法和 K0h 不一致就停下回報。
- 不動：其他能力值、INTERACT（含 pass 交互項）、目標 T6、ridge、RAPM 混合、用人層、映射錨、r_repl、賽中管線、名單頁、`season_nav.off_def`。

## 2. 檢查與判定（一次跑完，R-113）
### 2a. 不劣於檢查（2025-26 現行卡）
- c0、c0h、`npm test` 過。
- s0：2025-26 卡片人群（MIN ≥ 500）對到追蹤資料的人 ≥ 95%。
- 2025-26 卡（MIN ≥ 500）：
  - s1：Spearman(OVR, 薪水 errata-1 權重)、Spearman(OVR, 2K `data/external-impact/2k/2k-merged-e142.csv`)，Q−K0 的球員層 bootstrap（2000 次，seed 20261101）90% 下界 > −0.01。
  - s2：隊內 MIN–OVR Spearman 30 隊中位數，Q 不低於 K0 超過 0.02。

### 2b. 判定（2024-25 原點 → 2025-26 RAPM）
- 卡片：K0h、Qh＝2024-25 歷史原點的兩臂。
- 答案、人群、統計量全部照 E-180 §2b（`e180_eval.py`）：e_net＝pct(net×W)−pct(OVR)；S_all、S_F、S_G；bootstrap 2000 次、seed 20261101、90% 區間；臂間差在同一組重抽上算。
- pass 軸：每臂用**自己的** pass 欄算 S_all(pass, e_net)。另報告固定用 K0 的 pass 欄當軸的版本（看「原本的高傳球分球員」在 Q 下還被高估多少）。
- 判定：
  - **Q 採用候選**同時滿足：
    - ① S_all(pass, e_net)，Q−K0 下界 > 0（傳球偏高變小）；
    - ② Spearman(OVR, net×W)，Q−K0 下界 > −0.01（整體不變差）；
    - ③ 2a 全過。
  - 不是候選 → 不採用。不准因結果改權重、收縮、人群、門檻再試。
- 揭露：K0h 的 S_all(pass) 在 E-180 已看過；能力值可能是現值（L-091）。結果是「有揭露的樣本內」，不是乾淨的樣本外。

## 3. 只報告
- 另兩個原點（2022-23、2023-24）同一套統計量。
- k 擬合值、conv_s 前 20／後 20 名（2025-26）、conv_s 和 AST/astCh、AST/36 的 Spearman（看它是不是只是另一種量）。
- POTENTIAL_AST/PASSES_MADE、AST/POTENTIAL_AST 和 e_net 的 Spearman（不建卡，只看方向）。
- 2025-26 前 20 名進出、OVR 變動最大的 20 人。
- 例子（兩臂 pass、OVR、名次、OFF 拆解，2025-26 卡）：Jalen Williams、Jalen Johnson、Paolo Banchero、Scottie Barnes、Franz Wagner、LeBron James、Nikola Jokić、Tyrese Haliburton、Giannis Antetokounmpo。

## 4. 限制
- 只寫 `reports/E183-pass-conversion/`；0.2.9a、E-164、E-153、E-125、E-180 目錄唯讀；不改 `src/`、`scripts/`、賽中管線。
- 2025-26 追蹤資料是 E-069 在 2026-10-28 抓的，季中受傷的人（JW 1200 次傳球）收縮會拉得多；照實列，不另處理。
- 採用後才另案改名單頁說明與 `season_nav` 的 pass 描述。
- 回報用六段格式（CLAUDE.md）。

## 5. 產出
- `phase0.md`、`e183_build.py`、`e183_eval.py`、`conv-fit.json`、`ranking-{K0,Q}-{2022-23,2023-24,2024-25,2025-26}.csv`、`results.json`、`report.md`。
