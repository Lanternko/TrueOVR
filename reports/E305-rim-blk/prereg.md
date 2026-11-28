# E-305 預註冊：網站 RIM（護框）欄加入蓋帽次數（只改顯示欄）

- 日期：2026-11-10。角色：role-model／role-card 視需要，派工子 session 自做。標準由執行者自訂並直接凍結（R-165），**先 commit 再跑**。
- 來源：使用者 2026-11-10「護框應該加上蓋帽次數，wemby 應該斷檔第一」。現行 2026-27 RIM（`help`）Stewart 112.6 第 1、Wembanyama 109.5 第 2。蓋帽在 R-180（E-280 K3）只進 pred0 防守加分，沒進 RIM 欄。
- 範圍：**只改顯示欄 RIM**。ranking.csv、OVR／OFF／DEF、`help` 進模型的值都不動（要不要進 OVR 另案，避免和 K3 重複計蓋帽）。season_nav／viewer 線上行為不改（最多加預設關閉的旗標）。L-117：窗口＝四季滑動含本季，新秀用本季。

## 資料
- help：現行 RIM 同一份＝`live/<日期>/ranking.csv`（2026-27，資料截止日取最新）與 `reports/card-0.2.15/ranking.csv`（2025-26 卡片頁）的 `help` 欄，不重算。
- blk36：E-280 同一定義（每 36 分鐘蓋帽，四季窗口）。過去三～四季取 `reports/E227-lineup-transformer-r2/data/stats-<季>.csv`（blk36、minutes），本季取 `data/defense-seventh/2026-27/player-games.json` 的 BLK、MIN。季權重＝現行 help 窗口同一套 `rookie_defense.window_weights(c)`（c＝SLOTS·已賽場數／1230；卡片頁 c=0），每人除以自己有資料那幾季的最大權重（同 help 的 n_eff）。
- 小樣本縮收：blk36＝(Σw·BLK + K·μ)／(Σw·MIN_eff + K)×36，K＝200 分鐘（同 R-168 `blend_display.K_MIN`），μ＝名次人群的窗口加權每分鐘蓋帽率。
- rim contests／36（DV 臂第三成分）：repo 有 hustle 的 `CONTESTED_SHOTS_2PT`（2026-27 `tracking/hustle.json`）與 stats csv 的 `cont2pt36`（過去季）；用同一窗口與縮收。這是「2 分球 contest」，不限籃下 6 呎，只能當籃下 contest 的代理，報告註明。
- 名次人群＝`sn.mpg_pool`（本季場均 ≥ 15 分鐘；卡片頁用 ranking.csv 的 mpg 欄 ≥ 15）。z 的平均與標準差在名次人群內算，人群外有資料的人照人群分布算位置。blk 資料缺（沒有任何一季）者 z(blk)＝0（人群平均，同 E-280）。

## 臂
| 臂 | 分數（z 在人群內） |
|---|---|
| B0 | 現行 `help`（不動） |
| D30 | 0.7·z(help)＋0.3·z(blk36) |
| D50 | 0.5·z(help)＋0.5·z(blk36) |
| D70 | 0.3·z(help)＋0.7·z(blk36) |
| DV | z(help)、z(blk36)、z(contest2pt/36) 等權（各 1/3） |

顯示轉換（自訂，凍結）：合成分數再標準化（人群內 mean 0、sd 1，因為合成會縮小 sd），轉成 B0 同一把尺：顯示值＝人群內 B0 `help` 的平均＋標準差×合成 z。理由：`help` 不是百分位型能力值（season_nav 註解：mid／short／help／long 不換尺、`RESCALE_ATTRS` 不含 help，≥90 只有 1～4%），線上顯示就是 ranking.csv 原值；用百分位→display_scale 會把 help 的尺換掉、與 B0 不可比。B0 臂經此轉換恆等於現值。

## 驗收（凍結）
1. Wembanyama 在人群 RIM 第 1，且領先第 2 名 ≥ 5 顯示分。（卡片頁 2025-26 同樣報告，但不計入通過條件。）
2. RIM 對 EPM 防守（live：`reports/impact-epm-2026-27/epm-live.csv` 的 D；2025-26：`data/external-impact/epm_self/epm_2025-26.csv` 的 D）與 T 換人 DEF（`live/<日期>/t-swap.json` 的 −oppPts100；2025-26 沒有 T 換人值，略過並註明）的 Spearman，全體與 PF／C 子群，各臂 ρ 減 B0 的 ρ 都 ≥ −0.02（< −0.02 算變差）。**通過 2 ＝ 2026-27 的 EPM 與 T 四項、2025-26 的 EPM 兩項全部沒變差。** 兩邊都只取名次人群、且有對照值的人。
3. 前 15 名人工列出，報告標出明顯反直覺者（不計通過條件）。
- **選臂**：通過 1 與 2 的臂裡，取 PF／C 子群對 EPM 防守（2026-27）ρ 最高者；差 ≤ 0.003 視為並列，並列取 D50。沒有臂通過 → 報告「不採用」並列出各臂失敗項，不事後放寬。
- 產出：本目錄 `report.md`（`git add -f`）、腳本、`results.json`、B0 vs 選中臂 RIM 前 20 對照表、Stewart／Wembanyama 前後值。

## 已知背景（L-026）
開跑前使用者已說 Wembanyama 應斷檔第一，並看過現行 RIM 名次；權重網格（30／50／70）是使用者指定範圍，沒有在看結果後挑。
