# E-140 防守者犯規開啟＋聯盟基準重校（預註冊）

- 日期：2026-10-31；來源：使用者「犯規需要開 但是原本的節奏和犯規率要跟著改變」（R-094）
- 已看過：E-120 全部結果（F-065、F-067）、E-122 全部結果（F-079）、E-120／E-122 互打的聯盟平均：開犯規時每隊每場得分 −0.23、回合 −0.05（8 seed）。沒看過任何重校後的數字。
- 基準：主 checkout 現行 `src/defense_fourth_game.js`（含 E-120／E-122 兩個預設關選項）。E-122 的 D1 回合時長維持關（使用者未裁定）。

## 0. 引擎
- `defenderFoulBeta` 開：E-120 的 β（E-118 2025-26 擬合，`reports/E120-foul-defense/winimp-core-e120.mjs` 的 `loadBeta`），不改尺度。
- 新增兩個預設中性的校正量，不給值時和現行逐位元相同：
  - `foulBaseShift` c：犯規機率改成 `q' = q/(q+(1-q)·exp(-(fb-c)))`，fb＝場上五名防守者 β 總和。
  - 節奏乘數：沿用現有 `opt.pace`（預設 1）。
- c、pace 只能由 §1 的校正 seed 決定，決定後寫進 `calibration.json` 並算 sha256，之後才准跑 §2。

## 1. 校正（不判定）
- seed 20261100–20261115（16 個），30 隊互打 harness 同 E-122（`reports/E122-clock-d1/rr-*.mjs`），互打紀錄要多記每隊投籃犯規次數與罰球次數。
- 目標＝同 16 seed 關閉版（β 關、c=0、pace=1）的聯盟平均：
  1. 先固定 pace=1，二分法找 c，使聯盟每 100 回合投籃犯規次數和關閉版差 ≤0.5%。
  2. 再固定 c，二分法找 pace，使每隊每場平均回合和關閉版差 ≤0.1。
  3. 換了 pace 後再查一次犯規率；超過 0.5% 就再各迭代一輪，最多 3 輪。
- 校正目標是「關閉版的聯盟總量」，不是實際聯盟值（得分偏高 117.5 vs 115.5 是另案，TODO）。

## 2. 判定（seed 20261028–20261059，32 個）
- k0：β 關、c=0、pace=1 時和 E-122 的 `rr-off.jsonl` 逐場相同；`npm test` 過。不過就停。
- k1（唯一採用關卡）：判定 seed 上，開啟版對關閉版（沿用 E-122 `rr-off.jsonl`）：
  - 聯盟每 100 回合投籃犯規差 ≤1%；
  - 每隊每場回合差 ≤0.15；
  - 每隊每場得分差 ≤0.3。
  三項都過＝重校成立。不過就停，回報差多少，不改 c／pace 重跑（L-026）。
- 只報告、不判定（使用者已裁定犯規要開，這些是副作用）：
  - 30 隊淨分差 MAE（T1_pace，同 E-122 A1 算法）：開 vs 關、Δ、雜訊底 N（沿用 E-122 `rr-off2.jsonl`）、bootstrap 90% CI；每隊變化對先發五人 β 總和的迴歸（F-067 拆法）。
  - 個人帳本：罰球分量和 RAPM ftRate_defense×0.68 的相關（同 E-120 t1）。
  - WinImp（同 E-122 c3 harness，N、seed、人群相同；關閉版沿用 E-122 `checkpoint-off.jsonl`）：主版與位置版 E-067 S（AB／BA）、名次 Spearman、前十長人名次、防守型側翼例子（Daniels、Caruso、Smart、Dort、Holiday、D. White、Adebayo、Herbert Jones）。

## 3. 執行
- 重度運算全部在 5090（`ssh kojiek@100.97.181.15`，Tailscale），工作目錄 `~/e140/`。每個長作業用 `scripts/rjob.sh start` 開跑、`scripts/rjob.sh wait` 背景等待（L-082）；崩潰、中斷、卡住都要立刻處理，不准空等。
- 不 commit、不 push。
