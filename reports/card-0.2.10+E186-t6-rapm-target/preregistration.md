# E-186 預註冊：卡片迴歸目標 T6 混入 RAPM（T6R），修 Jalen Williams 與持球前鋒偏高

- 日期：2026-11-01。來源：使用者 `/goal 解決jalen williams被高估的問題`，在 F-125 診斷（JW 對 T6 殘差≈0，偏高來自目標本身）之後。依 R-117 第 5 條，此 goal 視為使用者換方向、重開額度（3 個實驗）；本實驗指向問題卡 F-125。
- 基準：card 0.2.10（`reports/card-0.2.10/`，凍結係數 `frozen.json`）；歷史原點沿用 E-179／E-180 的 0.2.9a 底三原點（2022-23、2023-24、2024-25），目標 T6（E-153 K6 口徑）。

## 0. 已揭露（lead 看過）
- F-113、F-117、F-118、F-125 全部數字；E-153 結果（T6 換目標讓下季 RAPM 吻合 −0.029）；卡對 RAPM ρ 0.78→0.70 發生在 0.2.8（換 T6）。
- 2025-26 JW 名次（MIN≥900，303 人）：卡 10、T6 23、DARKO 12、2K26 16、單季 RAPM 61、四季合併 RAPM 118。
- **沒看過任何 T6R 目標的卡片或名次。**唯一參數 w 事先固定，不掃描。

## 1. 改動
- **T6R**＝0.5·z(T6) ＋ 0.5·z(T0)，再轉回 T6 的每百回合尺度（乘 T6 的 sd、加 T6 的平均）。z 在每季、卡片擬合人群內計算；O、D 分別混，net＝O＋D。T0＝該原點季用的四季合併 RAPM（E-142 的 T0，即 0.2.7c 以前的目標；2025-26 用 `reports/impact-rapm/rapm.csv` 對應口徑）。
- 卡片迴歸每一個讀 T6 的地方（E-153 errata-1 列出的所有 `--rapm` 輸入、2025-26 primary／fitA／fitB）都換 T6R。其他（屬性、窗口、用人層、錨點規則）不動；係數依新目標重擬合（和 E-153 換目標相同做法）。
- usage 層 rapm1 不換（同 E-153 errata-1）。

## 2. 臂
| 臂 | 內容 |
|---|---|
| K6 | 現行（T6）。c0：2025-26 ranking 和 `reports/card-0.2.10/ranking.csv` 逐位元相同；歷史三原點和 E-179 用的卡逐位元相同。不同就停 |
| KR | 目標換 T6R，四原點 |

## 2.5 檢定力（第 0 階段，產生 KR 之前）
- 用 K6 三原點跑 a2 統計量的球員層 bootstrap（2000 次，seed 20261101），記 90% 區間半寬 h 為 MDE 參考，寫進 `phase0.md`。h > 0.20 就停（預期效果約 +0.1～0.2，量不出來），回報 lead。

## 3. 指標
人群：卡 MIN ≥ 900（2025-26）／歷史原點照 E-179 人群。
- **e_net**、**S_F(creation, e_net)**：照 E-179 定義（前鋒 SF／PF 內，creation 與「卡片名次減下季 RAPM 名次」殘差的 Spearman）。

## 4. 判定
硬條件（全過才算「修到、沒弄壞」）：
- **a1（使用者要修的事）**：2025-26 KR 卡，JW 名次 ≥ 16（＝ min(2K26 16, 單季 RAPM 61)，對稱於 R-007 不誤傷規則）。樣本內，只當使用者指定的修正檢查。
- **a2（系統性、時間上樣本外）**：三原點合併 S_F(KR) − S_F(K6) 的 bootstrap 90% 下界 > 0（前鋒 creation 偏高縮小）。
- **b（沒弄壞）**：c0 過；`npm test` 過；E-153 的綜合分 C（薪水 0.4／2K 0.3／下季 RAPM 0.15 口徑）三季合併 KR−K6 不低於 −2h_C（h_C＝K6 的 C bootstrap 90% 半寬）。
權衡／只報告（不能否決，R-042、L-099）：下季 RAPM ρ、薪水、2K、S_G、pass 的 S_all、前 20 名變動、關鍵球員表（JW、Jalen Johnson、Banchero、Edwards、Franz Wagner、Durant、Herb Jones、Dillon Brooks、SGA、Jokić、Wembanyama、Flagg、Knueppel）。
- a1、a2、b 全過＝修到、採用候選，交使用者 G5；a1 過 a2 不過＝JW 修到但系統性證據不足；a1 不過＝沒修到。

## 5. 限制
- 只寫 `reports/card-0.2.10+E186-t6-rapm-target/`；其他 reports 目錄、`src/`、網站、memory 不改。
- 三原點曾用於選 T6（E-142）；真樣本外是 2026-27 季末。
- 外部數據不轉載進 commit 的檔，只放彙總。
