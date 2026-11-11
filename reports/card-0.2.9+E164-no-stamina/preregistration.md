# E-164 預註冊：卡片 OVR 拿掉 stamina，上場時間只留在分鐘

- 日期：2026-11-01
- 來源：使用者 2026-11-01「分鐘和體力只用其中一個……我傾向用分鐘」（R-105）→ E-161 回測被抓出循環：答案卡自己也重複計算上場時間（L-088）→ 使用者「就算體力很重要，但是重複計算了，不如整並到分鐘裡」→「GO」。
- 基準：card 0.2.9（`reports/card-0.2.9/ranking.csv`，sha 03288908…6eae＝E-158 Y0）。
- 實驗版號：`card 0.2.9+E164`。採用後的版號照 R-064 由變動量決定，報告寫建議、使用者裁定。
- 角色：role-card 執行；role-audit 另開 session 重算。
- 凍結：2026-11-01 使用者「核可開跑」凍結；sha256 見 `preregistration.sha256`。之後不改，要改就寫 errata 給使用者核可。

## 0. 背景

卡片 OVR 的結構（F-106 盤點，`reports/card-0.2.9+E163-volume-diag/report.md`）：
能力值 → 部件卡 ridge（`calibrate_wing_t.py`，目標 T6）→ H1 align → 用人層 WLS [1, p, L, a, y, v, y·L, v·L]（L＝分鐘、a＝出賽率）→ 分鐘權重 W＝w_sat(mpg) → 校準映到 OVR。

上場時間進了兩次：
1. 第一層能力值有 stamina（整季場均分鐘百分位＋年齡），會抬高每 36 分鐘產值；
2. 用人層的 L 和分鐘權重 W 再按分鐘計一次。

網站已經不顯示體力（R-057）。這次在第一層把 stamina 拿掉，上場時間只留在分鐘（L、W），其餘不動。

假設：拿掉 stamina 之後，外部評估（薪水、2K、下季 RAPM、下季 EPM）不明顯變差。不主張變準；這是使用者為了「只算一次」做的結構選擇，不是盲測。

## 1. lead 已看過的（揭露）

- E-161 全部結果（新賽季回測：凍結 stamina 對整季答案卡 8 格 MAE 都變差；分鐘大增組被低估更多）。那次答案卡本身含 stamina，判定有循環偏誤（L-088）。
- 線上單人反事實：JW stamina 退回開季值，每 36 pred 2.891→2.627，可見 stamina 在第一層係數為正。
- E-131（拿掉 physique）的做法與結果；E-142、E-153、E-157、E-158、E-162 的結果；card 0.2.9 的名次。
- **沒看過**：card 0.2.9 部件卡的 stamina 係數數值、任何「拿掉 stamina」的卡或評估數字。

## 2. 臂

| 臂 | 內容 |
|---|---|
| K | card 0.2.9 原樣重建（E-158 Y0 路徑，同 E-162 的 K）。c0：2025-26 ranking 和 `reports/card-0.2.9/ranking.csv` 逐位元相同；三個歷史原點和 E-158 `ranking-Y0-<季>.csv` 逐位元相同。不同就停 |
| S | 同 K，只有三張部件卡（primary、fitA、fitB）的設計矩陣拿掉 stamina；form／ridge 照原 CV 程序重選（同 E-131）；之後用人層照 Y0 設計矩陣重擬合、校準照舊 |

實作規則：
- 照 E-131：在本資料夾放 `calibrate_wing_t.py` 的複本，加可重複的 `--dropAttr`（解析旗標後、建設計矩陣前從 ATTRS 移除；ranking 的能力值欄照舊全寫）。不改 E-142 原檔。
- **c0d**：複本不帶 `--dropAttr` 時，K 的部件卡要和原檔輸出逐位元相同。
- **u1**：S 的 ranking 能力值欄（含 stamina）和 K 逐位元相同，只有 OVR 相關欄可以不同。
- **u2**：開跑前 grep 卡片鏈（部件卡、H1 align、用人層、校準）所有讀 stamina 的地方，列成表寫進報告。除了第一層設計矩陣，如果還有別處用到 stamina，**停下回報 lead**，不自行決定要不要一起拿掉。

## 3. 評估（E-157 評估口徑 v2，`reports/card-0.2.8+E157-next-epm-metric/eval_v2.py`）

- 人群：卡 MIN ≥ 500、兩臂都有、逐人參考分有項目者。判定季 2022-23、2023-24、2024-25，依人數加權合併。
- S 對 K 的採用條件（全部成立才算過）：
  - (a) 全體 C 差 ≥ −0.005；
  - (b) ② 薪水 ≥ −0.02、②之二 2K ≥ −0.02、③ 下季 RAPM ≥ −0.05、④ 下季 EPM ≥ −0.05。
- 過：交 role-audit 重算，再交使用者 G5。不過：回報哪項差多少，交使用者選（仍照 R-105 採用／維持 0.2.9）。
- 採用與否最後由使用者裁定。

## 4. 只報告

- 全體 C 差的球員層 bootstrap 90% 區間（三季球員聯集重抽 2000 次，seed 20261104）。
- 2025-26 的 C、M_sal、M_2k。
- 依整季場均分鐘三分位（高／中／低），K→S 的平均 OVR 變化與名次變化。
- 關鍵球員表（2025-26，MIN ≥ 500，K／S 的 OVR 與名次）：Jalen Williams、Chet Holmgren、Nikola Jokić、Shai Gilgeous-Alexander、Victor Wembanyama、Cooper Flagg、Anthony Edwards，以及 K→S 升最多、降最多各 5 人。
- G5 預查：K 前十名長人（C／PF）在 S 的名次；前 20 名進出；前 300 名移動 ≥ 10 名人數（R-064 版號依據）。
- 部件卡係數：K 的 stamina 係數，以及 S 中其他屬性係數變化最大的 3 項。
- npm test。

## 5. 判定後才做

- 採用：
  - 發新卡（`reports/card-<版號>/`），名單頁 2025-26 改讀新卡；
  - 新賽季頁照 R-064 換基底：用人層由新卡重建（照 `build_usage_029.py`），N＝0 時要逐格重現新卡；
  - stamina 不進第一層之後，新賽季 stamina 的 C4 w 只剩給 MPG_hat 用，E-161 的 `STAMINA_FREEZE` 開關不再需要（另案清掉）；
  - status_snapshot、season_nav 更新說明、狀態板、handoff 一起更新（L-034）。
- 不採用：R-105 註明「卡片層拿掉 stamina 外部評估變差」，維持 0.2.9。

## 6. 不准

- 只寫 `reports/card-0.2.9+E164-no-stamina/`；card-0.2.9、E-142、E-153、E-158、E-162 目錄唯讀，執行前後 sha256 核對；不改 `src/`。
- 外部數據不轉載，只放彙總（R-062、R-093）。
- 看到結果後不改門檻、人群、判定季，也不改成「只在某層拿掉」（L-026）。
- 不 commit、不 push、不部署。
- 長時間的建卡在 5090 或本機都可（E-162 同流程在本機跑完），報告寫明在哪跑。
- 回報照 CLAUDE.md 六段格式，第一行 `# 總評`。
