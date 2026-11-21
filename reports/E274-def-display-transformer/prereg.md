# E-274 預註冊：網站 DEF 顯示欄改用 Transformer 換人防守值

- 日期：2026-11-08。角色：role-card。來源：使用者問 DEF 欄 KD 排在 Curry 後面（防守 RAPM 每季都比 Curry 好）。標準由執行者自訂並直接凍結（R-165）。凍結時尚未看任何臂的結果（只讀過程式碼與資料欄位）。
- **只動顯示欄，OVR、卡片、線上頁面一律不動。**

## 1. 目標與折
- 目標：t 季的 DEF 值預測 t+1 季防守 RAPM（`E126/rapm-<s>.json` 的 D × `P.wfun(mpg)`，poss ≥ 1000；D 符號用 net≈O+D 檢查，同 E-269）。
- 折（t→t+1）：2022-23→2023-24、2023-24→2024-25、2024-25→2025-26。
- 人群（所有臂共用同一批人，才能公平比）：t 季卡 MIN ≥ 500、名字唯一對得上 playerId（同 E-269 `load`）、t 季 RAPM（poss ≥ 1000）有值、t+1 季目標有值、在 T 的 t 季球員表裡。
- 主指標：Spearman ρ（逐折＋依人數加權合併）。
- 副指標（只報告）：t+1 季自製 EPM 的 D（`data/external-impact/epm_self`，stintPoss ≥ 1000）的 ρ；目標改用未乘 W 的原始 D 的 ρ；不要求 t 季 RAPM 的較大人群上 D0／D1／D2 的 ρ。

## 2. 臂（皆為「越大越好」的 DEF 值）
- **D0**：現行 DEF。照 `season_nav.off_def` 在 t 季卡（E-269 A0 `ranking-A0-<t>.csv`）重算：onBall＋help＋pressure 依分位置 pred0 係數的貢獻＋defenseBonus−人群平均 defenseBonus。
- **D1**：D0，但加分改兩側：defenseBonus 換成 centered＝0.75·D − 同位置平均（不截 0；D＝該卡 `def-L-primary.csv`，posMeanD 用 `defense_centered` 的反推規則；possW < 2500 者沒有 centered 就退回 defenseBonus），再減人群平均。
- **D2**：T 換人防守值。
  - 球員池＝t 季卡 MIN ≥ 500 且名字唯一的人（在 T 的 t 季球員表中者）。
  - 隨機陣容 3000 組（seed 20261108）：每組從池裡抽 10 個不重複的人＝4 隊友＋5 對手＋1 備用；**所有球員共用同一批陣容**。
  - 評分球員 x 換進隊友第 5 人；若 x 本來在該組的隊友或對手裡，用備用位補掉（x＝備用時不用處理）。位置依 `Ctx.hkey` 排序（E-225 身高規則）。
  - 值＝換進 x 時**對手每 100 回合得分**的平均（5 個 seed 網路平均；主客位置各算一次取平均，同 t_swap），**取負號**。
  - T 權重只用 ≤ t 季訓練：t＝2022-23 用 T2223（訓練季 2021-22、2022-23）；t＝2023-24 用 T2324（2021-22～2023-24）；t＝2024-25 用既有 T2425。T2223、T2324 照 `e228_train.py` 同設定（R2-stats cfg、lr 0.001、wd 0.1、folds 1-4 訓練 fold 0 早停、seed 0–4）在 5090 重訓，超參數不改。球員特徵＝t 季球員表（`base_feats(t)`）。
- **D3**：0.5·z(D2)＋0.5·z(t 季兩側 RAPM D)（z 在共用人群內；權重固定 0.5 不調）。
- **D4**：t 季兩側 RAPM D（`rapm-<t>.json` 的 D，符號同上）本身；持續性基準，不參與採用。

## 3. 採用門檻
D2 或 D3 要同時成立：(a) 合併 ρ 是 D0–D3 中最高；(b) 比 D0 高 ≥ +0.03；(c) 每一折都 ≥ D0。D2、D3 都沒過就不換（維持 D0）。D1 只當診斷（回答「兩側加分」本身有沒有用），若 D1 過 (a)(b)(c) 而 D2、D3 沒過，報告為「只改加分即可」。D4 若合併 ρ 最高照實寫（它是持續性基準，不是顯示欄候選）。

## 4. 例子（只報告）
2024-25→2025-26 折與本季 live（`e229_live.make_ctx` 與上線權重，池＝本季 MIN26 ≥ 150、在 `C.B`）：Kevin Durant、Stephen Curry、Fred VanVleet、Victor Wembanyama、Rudy Gobert、Alex Caruso、Amen Thompson、Alperen Sengun、Nikola Jokić、Trae Young、OVR 前十 pos＝C 的長人，列在各臂的 DEF 名次（live 只有 D0 的現值與 D2；沒有 RAPM 臂的季中值）。

## 5. 偏離與限制
- 重訓與 D2 抽樣跑 5090（`~/side_projects/pure_ovr/experiments/e274/`），其餘本機無視窗。
- 若某季訓練資料缺而做不到，該折 T 臂標「無」並寫明，不用含目標季的權重代替。
- 樣本內不算證據（R-007）：判定只看 t→t+1。
