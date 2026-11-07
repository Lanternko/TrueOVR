# E-166 罰球防守放大到實測散布（預註冊草稿）

- 日期：2026-11-01；來源：使用者「先補罰球防守」（看完 F-105 後選 B）
- 已看過：F-103～F-105 全部（含 sim 0.1.2 的罰球防守去雜訊散布只有實測 36～49%、中鋒 0）；E-118／E-120／E-140 全部結果（E-140：開 β 後 Holiday／Caruso／Smart 名次下降）。沒看過任何放大 β 後的數字。
- 基準：sim 0.1.2＝`reports/player-impact-v29/benchmark.mjs` 的 `options()`（β＝E-118 2025-26 整季擬合，`defenderFoulBeta`；c＝−0.03125；pace×0.99875）。β 目前每人 sd 0.023（logit），最小 −0.081、最大 +0.075，582 人。
- lead 事前預期：校正選到 k 3～4；j1 過約三成（E-140 開 β 時防守型側翼反而下降，放大可能更降）；j2、j3 過約六成。

## 0. 引擎
- 只加一個選項 `foulBetaScale` k（預設 1，不給時和 0.1.2 逐位元相同）：犯規式裡的 fb 改成 k×Σβ。其他不動。
- 只用在 harness（`options()` 外層覆寫），校正與判定期間不改 `benchmark.mjs`；採用後才改預設。

## 1. 校正 k（不用 RAPM，只用實測 stints）
- 量法：`reports/sim-0.1.1-wing-diag/poss-sim.mjs`＋`poss_ridge.py` 同一套（λ3000，每 100 防守回合，拆半去雜訊），校正 seed 20261103、20261104（沒用過），每個 k 跑兩個 seed 共 1740 場。
- 目標量：非中鋒 131 人「對手罰球次數 fta」的去雜訊散布比 模擬／實測（0.1.2 為 0.44）。
- 候選 k ∈ {1, 2, 3, 4, 6}；選比值最接近 1.00 的；差距相同選小的。k=6 仍 < 0.90 就用 6，並在報告寫明沒追上。
- 選定 k 後，照 E-140 §1 的程序重解 c 與 pace（seed 20261100–115，目標＝0.1.2 的聯盟每 100 回合投籃犯規、每隊每場回合；容差同 E-140）。k、c、pace 寫進 `calibration.json` 並算 sha256，之後才准跑 §2。

## 2. 判定（seed 20261028–20261059，32 個；harness 同 E-140）
- j0：k=1、c、pace 用 0.1.2 值時和 E-140 `rr-on.jsonl` 逐場相同；`npm test` 過。不過就停。
- j1（主）：WinImp（同 E-140 checkpoint harness，N、seed、人群相同；基準＝E-140 `checkpoint-on.jsonl`）。人群與名次算法同 F-103（`reports/sim-0.1.1-wing-diag/od_split.py`：276 人、2022-25 合併 ≥5000 回合；答案名次＝2022-25 RAPM pooledNet 名次）。非中鋒、防守 RAPM ≥ +1.5 的人（F-103 的 36 人，名單在跑前用 od_split 匯出凍結），平均「模擬名次 − 答案名次」比 0.1.2 少 ≥ 10 名。
- j2：276 人模擬 X 和 2022-25 RAPM pooledNet 的 Spearman 不比 0.1.2 低超過 0.01。
- j3：30 隊淨分差 MAE（E-140 算法）不比 0.1.2 差超過 0.1。
- 採用＝j0～j3 全過。任一不過就停、回報差多少，不改 k 重跑（L-026）。
- 只報告：側翼與中鋒 fta 散布比（判定 seed 重量一次）；E-067 S；前十長人名次；例子 H. Jones、Caruso、Smart、D. White、Daniels、Draymond、Brooks、Gobert、Adebayo。

## 3. 運算
- 5090（`kojiek@100.97.181.15`），新快照目錄；校正約 10 個 1740 場批次，判定同 E-140 規模。
