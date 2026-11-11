> 凍結：2026-11-04，使用者「核可凍結」。以下內容與 preregistration-draft.md 相同，凍結後不改；有錯寫 errata。

# E-228 預註冊草稿（尚未凍結）：陣容 Transformer 當球隊評分引擎

狀態：草稿。凍結前不得看 T 在 2025-26 任何比賽的預測對結果。M0 的 2025-26 結果已在 E-223 讀過（揭露見下）。

## 問題
Transformer（陣容 -> 淨勝分）當球隊評分引擎，在沒看過的賽季（2025-26）預測單場勝負與全季勝場，是否至少不輸現行 M0 模擬。

## 模型 T-2425
- 架構與超參數同 E-227 R2-stats（tuning.json selected：lr 0.001、wd 0.1，不重調）。
- 只用 2021-22 至 2024-25 的 train stints 重訓，5 個 seed（0-4）。權重 `results/weights/T2425-{0..4}.pt`，訓練記錄 `results/train-meta.json`。
- 訓練在 5090（GPU 滿載，改用 CPU 4 執行緒）。val loss 約 1.998-1.999。

## 賽前特徵（預測 2025-26）
- 用 2024-25 整季能力值與 stats 向量。上一季沒有的球員：mask 並補零向量（同 E-227）。
- 預測 2024-25（只做 dry run）用 2023-24 特徵。
- 陣容與分鐘：E-223 `work/lineups-2526.json` 原樣使用。

## 球隊淨值（無擬合參數）
1. 每隊每場依分鐘按比例抽 5 人（Gumbel top-5 / Plackett-Luce，不重複），位置依 E-225/E-227 的身高排序規則。
2. 兩隊餵 Transformer，主客雙向各一次取平均（orientation averaging），得主場視角每 100 回合淨值。
3. 抽 N=2000 次平均（rng `default_rng([228, game_i])`，5 個 seed 共用同批抽樣）。
4. 乘 (聯盟平均回合數/100)。回合數取上一季 train stints 的 sum(possa+possb)/2/場數（2025-26 用 2024-25：100.43）。
5. 5 個 seed 平均 = 該場預測 margin。
6. 勝率 Φ((margin ± H)/σ)，H=2.5、σ=12（同 E-223，clip 同 `fit_train`）。

## 比較對象與指標
- 比較對象：M0（E-223 既有模擬）、B0（E-223 基準）。
- 指標：單場 Brier、全季勝場 MAE（寫法同 E-223 `fit_train.features/brier`、`wins_mae`）。
- 配對 bootstrap：按場重抽，rng 種子 20261102，2000 次，取 5%/95%。

## 必過判定（R-117，只兩類）
- J1 不更差：Brier(T) - Brier(M0) 的 90% 區間上界 < MDE_B = 0.0100。
- J2 不壞：wins-MAE(T) - MAE(M0) 的點估計 <= MDE_W = 1.25。

## 只報告不判定
- T 是否贏 M0（Brier 差 90% 上界 < 0）；T vs B0。
- 50/50 平均 (T+M0)/2（探索性）。
- 30 隊排名 Spearman（對實際勝場）。
- 缺陣敏感度：借 F-153 A 線方法，`aline_t.py`（E-223 aline-jobs/meta 輸入；對手為 400 組隨機輪替抽樣；ΔNet 換算單場 margin；報 Pearson r，M0 的 r 取自 sims-a<key>；球季快照 cluster bootstrap）。

## 揭露
1. M0 的 2025-26 結果已在 E-223 讀過。
2. M0 在 2025-26 有 E-208 污染，對 M0 有利（所以 J1/J2 對 T 偏嚴）。
3. T 的 2025-26 預測結果尚未打開、未與賽果比對。`work/pred-T-2526.json` 已產生，未開啟，只記 sha256。
4. 2024-25 在 T-2425 訓練內，dry run 的 T-vs-M0 只是管線檢查，不是證據（R-007）。

## Dry run（2024-25，樣本內，僅管線檢查；`dryrun-2425.json`）
- Brier：B0 0.2391、M0 0.2457、T 0.2153（5 seed 平均；單 seed 0.2128-0.2197）、MIX 0.2181。
- wins MAE：T 6.01（單 seed 5.60-6.43）；M0 約 7.87（E-223 記錄）。
- margin 尺度：T 的 margin 標準差 8.9（M0 8.8，實際 16.2，與 M0 同級）；主場平均 +0.07（實際 +1.80；H=2.5 另外加）。
- T 與 M0 預測相關 0.55，與 B0 0.76。Spearman 對實際勝場：B0 0.56、M0 0.46、T 0.76（樣本內）。
- 取樣雜訊：單場 margin 跨 seed SD 約 1.07；抽樣雜訊（N=2000，換 rng 重跑）5-seed 平均 margin 差 SD 0.17、勝率差平均 0.0034（最大 0.018）。N=2000 的雜訊可忽略；seed 變異是主要雜訊，所以固定 5 seed 平均。

## 前瞻（凍結後）
用 T-full（E-227 R2-stats 權重、2025-26 特徵）每日記錄 2026-27 預測，只報告。

## 凍結時要 sha256 的檔案
`e228_train.py`、`t_lib.py`、`predict_t.py`、`eval_t.py`、`aline_t.py`、`results/weights/T2425-{0..4}.pt`、`results/train-meta.json`、`work/pred-T-2526.json`（只記雜湊、不開）、E-223 `work/lineups-2526.json` 與 `work/sims-2526*`、E-227 `manifest.json`、本檔。
`eval_t.py --key 2526` 在 `FREEZE.txt` 出現前會拒絕執行。

## 待使用者決定
- 是否接受 J1/J2 門檻與 H=2.5、σ=12（沿用 E-223，未重調）。
- 是否凍結並解鎖 2526 評估。

## 附：缺陣敏感度 dry run（2024-25，`aline-2425.json`，樣本內）
1162 次移除、130 個快照：Pearson r 對 x，T 0.78、M0 0.36（同列差 0.42）；T 的 margin 斜率約 11.7 分/單位 x；ΔT 的 seed 間 SD 0.32。僅報告，不判定。
