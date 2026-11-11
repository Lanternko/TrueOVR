# E-157 預註冊：評估指標加「下季自製 EPM」（評估口徑 v2）

- 日期：2026-11-01。來源：使用者 2026-11-01 問「為什麼沒有 EPM」→ lead 提「下季自製 EPM 當評估、同季不行」→ 使用者「先上線 028 然後 A B」（A＝本實驗）。
- 性質：**定義評估口徑，不選卡**。card 0.2.8 已由使用者裁定上線（R-102），本實驗的數字不回頭改那個裁定。

## 0. 已揭露（lead 看過）
- E-142、E-153 全部結果（薪水、2K、下季 RAPM 三項，0.2.7d 對 0.2.8）。
- 自製 EPM（`data/external-impact/epm_self/epm_<季>.csv`，E-142 的 T1）存在 2018-19～2025-26，沒看過它和任何卡片的相關。

## 1. 新指標
- **下季 EPM**：t 季卡片對 t+1 季自製 EPM 的 `net`（`epm_self/epm_<t+1>.csv`，`stintPoss` ≥ 1000）× W(t+1 mpg)。處理方式（人群對應、W 函數、Spearman）完全照 `reports/E142-card-target/phase1_eval.py` 的下季 RAPM 項，只換資料來源。
- 2025-26 原點沒有 t+1 季完整資料，故無此項（同下季 RAPM）。
- 不用同季 EPM：它和卡片吃同一季 box score，相關會因原料重疊偏高。

## 2. 評估口徑 v2（之後的卡片實驗沿用，除非另行預註冊）
- 逐人參考分 ref＝Σ w·p ÷ Σ w（只加總該人有的項，缺項按比例重分配）：薪水 0.4（errata-1 合約年次權重）、2K 0.3（`data/external-impact/2k/2k-merged-e142.csv`）、下季 RAPM × W(mpg) 0.15、**下季 EPM × W(mpg) 0.15**、模擬 0.15（仍要先過穩定度檢查；目前 c0s 不過，不列入）。
- C＝Spearman(OVR, ref)；各指標 M_x 照 E-142 口徑；新增 M_epm＝一般 Spearman。
- 檢查：① 主要差值 bootstrap 90% 下界；② 薪水不差超過 0.02；②之二 2K 不差超過 0.02；③ 下季 RAPM 不差超過 0.05；**④ 下季 EPM 不差超過 0.05**。
- 判定季 2022-23、2023-24、2024-25，依人數加權。

## 3. 要產出
1. 可重用的評估模組 `eval_v2.py`：輸入「臂名→各季 ranking.csv 路徑」，輸出各季與三季合併的 n、C、M_sal、M_2k、M_rapm、M_epm，以及兩臂差值的球員層 bootstrap（三季球員聯集重抽，2000 次，seed 由呼叫端給）。匯入 E-142 `phase1_eval.py` 的函式，不複製改寫口徑。
2. 用它跑 0.2.7d（E-153 K0／K0h）與 0.2.8（E-153 K6）：v2 口徑的 C 與各指標、差值與下界、①～④是否成立。**只報告**。
3. 診斷（只報告）：各季 Spearman(下季 EPM, 下季 RAPM)；Spearman(下季 EPM, t 季 T6)；Spearman(下季 RAPM, t 季 T6)。用來看 EPM 項有多偏向 T6 類目標。
4. c0：只用舊三項權重（關掉 EPM 項）時，eval_v2 重算 0.2.7d 與 0.2.8 的 C 要和 E-153 `results.json` 一致到 1e-9，不一致就停。

## 4. 限制
- 只寫 `reports/card-0.2.8+E157-next-epm-metric/`；E-142、E-153 目錄唯讀；不改 `src/`。
- 外部數據不轉載，只放彙總。
