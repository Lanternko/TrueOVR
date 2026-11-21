# E-158 預註冊：目標換 T6 後，年輕球員修正要不要跟著改

- 日期：2026-11-01。來源：使用者 2026-11-01「先上線 028 然後 A B」（B＝本實驗：在 T6 目標下重新檢查年輕修正，針對 Flagg、Knueppel 這類被低估的年輕人）。
- 基準：card 0.2.8（`reports/card-0.2.8/ranking.csv`，sha 見該目錄 summary.json）；歷史三原點用 E-153 K6 的建法（`reports/card-0.2.7d+E153-t6-target/work/K6-<季>`）。

## 0. 已揭露（lead 看過）
- E-149、E-152、E-155 全部結果（爛隊年輕人扣分、年齡連續形狀，都不成立或不採用）。
- E-153 全部結果與 0.2.8 關鍵球員名次（Flagg 180、Knueppel 32、Banchero 63 等，2025-26）。
- E-157 只產出 0.2.7d／0.2.8 的數字，不含本實驗任何臂。
- **沒看過 Y0、Y1 的任何數字。**兩個候選都沒有可調參數。

## 1. 背景
0.2.8 的 usage 層（含年輕×爛隊×時間 y·d·L 的折扣，y＝≤23 旗標、d＝E-147 連續爛隊度）仍用合併 RAPM（rapm1）擬合（E-153 errata-1 §3）。目標已換成 T6，這層折扣是為了修正 RAPM 對爛隊年輕人的偏差而來，換目標後可能不需要，或該改用 T6 擬合。

## 2. 臂
| 臂 | 內容 |
|---|---|
| K | card 0.2.8 原樣。c0：2025-26 ranking 和 `reports/card-0.2.8/ranking.csv` 逐位元相同；三個歷史原點和 E-153 `work/K6-<季>` 的 ranking 逐位元相同。不同就停 |
| Y1 | usage 層的 rapm1 輸入也換成 T6（各原點用該原點的 T6 季值，季對應照 E-153 errata-1 §2 其他輸入的換法），重擬合 usage 層，其他不動 |
| Y0 | usage 層拿掉 y·d·L 這一項（設計矩陣刪掉該欄後重擬合），rapm1 不換，其他不動 |

找不到 rapm1 的 T6 對應、或 y·d·L 不是設計矩陣中可單獨刪除的一欄時，**停下回報 lead**，不要自行決定。

## 3. 評估（E-157 評估口徑 v2，用其 `eval_v2.py`）
- 人群：卡 MIN ≥ 500、三臂都有、逐人參考分有項目者。年輕子群＝該季 bio AGE ≤ 23。
- 判定季 2022-23、2023-24、2024-25，依人數加權合併。
- 每個候選對 K 的採用條件（全部成立才算過）：
  - (a) 年輕子群 C 差 ≥ +0.01，且其球員層 bootstrap（三季年輕球員聯集重抽，2000 次，seed 20261102）90% 下界 > −0.02；
  - (b) 全體 C 差 ≥ −0.005；
  - (c) 全體 ② 薪水 ≥ −0.02、②之二 2K ≥ −0.02、③ 下季 RAPM ≥ −0.05、④ 下季 EPM ≥ −0.05。
- 兩個都過：取年輕子群 C 差較大者；相差 < 0.005 時取 Y1（和目標一致、改動較少的理由）。都不過：維持 0.2.8。
- 採用與否最後由使用者裁定。

## 4. 只報告
- 2025-26 的 C、M_sal、M_2k（全體與年輕子群）。
- 關鍵球員表（MIN ≥ 500，2025-26，K／Y1／Y0 的 OVR 與名次）：Cooper Flagg、Kon Knueppel、Paolo Banchero、Dylan Harper、Stephon Castle、Ron Holland、Jaylen Wells、Anthony Edwards、Brandin Podziemski、Victor Wembanyama、Shai Gilgeous-Alexander、Nikola Jokić，以及 y·d·L 折扣最大的 5 個年輕人。
- 前 20 名進出；前 300 名移動 ≥ 10 名的人數；年輕子群前 30 名變動。
- npm test。

## 5. 限制
- 只寫 `reports/card-0.2.8+E158-young-under-T6/`；E-142、E-153、card-0.2.8 目錄唯讀；不改 `src/`。
- 外部數據不轉載，只放彙總。
