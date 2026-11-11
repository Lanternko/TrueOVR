# E-285 預註冊：Transformer 輸入加逼失誤與有球／無球／一般犯規，重訓看排名

- 日期：2026-11-09。角色：lead 自做。標準由執行者自訂並直接凍結（R-165）。
- 狀態：已凍結（凍結時尚未訓練任何新權重）。
- 背景：E-283／E-284 把壓迫分量與犯規拆開進卡片 pred0 都變差；使用者要的是把新能力值**加進陣容 Transformer 的輸入**再看排名（R-178 (b)：Transformer 驗收看 stint 誤差與比賽 Brier）。
- E-227 R2-stats 已含 stl36、deflections36、charges36、pf36、blk36 與 pressure，所以真正新增的是 4 欄（逐季、和 stats 同口徑，見 `build_extra.py`）：
  - mtov36：對位逼失誤（E-071 分量，k 收縮到 0；2021-22 無追蹤資料 → 整季遮罩）
  - fOn36：有球犯規（shooting、take、transition take、clear-path）
  - fOff36：無球犯規（loose ball、away-from-play）
  - fGen36：一般犯規（無 descriptor）；犯規率 500 分鐘收縮到該季聯盟率；<200 分鐘遮罩

## 臂（同環境 5090、同程式、同 seed 0–4 重訓）
| 臂 | 輸入 |
|---|---|
| R2-stats（基準）| E-227 R2-stats 41 欄 |
| R2-statsX | 41 欄 ＋ 上面 4 欄 ＝ 45 欄 |
架構、超參數（lr 0.001、wd 0.1）、資料（2021-22～2025-26 split=train，folds 1–4 訓練、fold 0 早停）全照 E-227。

## 驗收（只跑一次 e285_eval.py）
樣本外：測試集（5 季 split=test 20% 場次，從未進訓練）＋前向 2026-27（目前所有場次，用 2025-26 特徵）。
採用候選＝全部成立：
1. 測試集淨值 MSE（5 seed 平均預測）ΔMSE（X − 基準）點估計 < 0。
2. 前向 2026-27 ΔMSE 點估計 ≤ 0。
3. 測試集比賽 Brier（k 在 fold 0 擬合）Δ ≤ 0。
4. 護欄：測試集 ptsSide、tovLL、orbLL 各自 Δ ≤ +0.0002。
「顯著改善」另外看：測試 ΔMSE 90% 區間上界 < 0（E-227 的 MDE 是 15.36，預期達不到，只報告）。

## 只報告
- 2025-26 ≥1000 分鐘母體的換人值（淨、進攻、防守）兩臂名次：前 20、防守前 20、指名球員（Durant、Curry、Wembanyama、Gobert、Davis、Adebayo、Allen、Hartenstein、Caruso、Amen Thompson、Trae Young、Lopez、Herbert Jones、JJJ、Jokić、Towns）、兩臂 Spearman、名次變動最大者。
- 新 4 欄與既有防守欄的排列重要性（測試集 MSE 上升）、5 seed MSE 分布。
