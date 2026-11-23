# E-309 預註冊：區域威懾（對手禁區出手佔比）進 T／sim／RIM・DEF 顯示欄

- 日期：2026-11-23。標準由執行者自訂並直接凍結（R-165），先 commit 再跑。驗收分層（R-178）：不拿單季防守 RAPM 當唯一裁判。
- 來源：使用者 11-23 指出 Wembanyama 在場時對手 14 呎內出手佔比降 10.5%，現行模型只有對位威懾。四因子 RAPM（`reports/impact-rapm/four-factors.csv`）`rimShare_defense`＝對手出手中禁區佔比被壓低幾個百分點（2022-26：Wembanyama 5.97、Jokić 5.83、Queta 5.80、Draymond 4.77；分半信度 0.755）。
- 前置修正（已 commit c7c9a94f）：2026-27 stints 投籃分區全落中距（pbp 沒有 area），已用官方 qualifier 補，往季逐位元不變。

## 屬性：rimDet（隱藏，不上頁面）
- 定義：四因子同設計（每 stint 一側＝五攻＋五守，fga 加權 ridge），λ 固定 300（four-factors CV 選出值，不重選），只用 shortA/fga（rimDet）與 longA/fga（threeDet）兩因子；正值＝壓低對手該區佔比；單位百分點。`build_rimdet.py`，重現 four-factors.csv 2022-26 值（Wemby 5.969／Jokić 5.828／Draymond 4.767，相符）。
- 視窗（L-117 四季滑動含當季）：T 特徵 season s＝max(2022-23, s−3)..s，排除 E-225 測試雜湊場次；2021-22 沒有分區 stints → 整欄遮罩。sim＝2025-26＋2026-27 全場次（不和 2022-25 RAPM 答案重疊）。顯示＝2023-24..2026-27 全場次（含本季至 11-21 前後最新 stints）。
- 開跑前已量的重疊（2025-26，fga 權重 ≥ 2500、≥500 分鐘，Spearman）：rimDet 對 help 0.42（PF/C 0.47）、blk36 0.41、−rimDiff 0.43、身高 0.50；help＋身高＋blk36＋rimDiff 線性解釋 R² 0.34 → 大部分是新資訊。threeDet 對 rimDet −0.91（被擋出禁區的出手大多變三分）。**sim 已有同類通道**：v45 細區出手選擇模型的防守者 logit（choiceDefender，2025-26 單季、收縮＋蓋帽特徵），換算禁區佔比後和 rimDet Spearman 0.70、SD 1.22 vs 1.71 百分點（Jokić 1.48 vs 6.04）。

## (a) T 輸入（陣容 Transformer）
- 臂：R2-stats（E-227 41 欄，基準）、R2-statsZ（＋rimDet）、R2-statsZ2（＋rimDet＋threeDet）。同 E-285 框架（`z_lib.py` 只 monkeypatch、不改 E-227 凍結檔）、同超參數（tuning.json R2-stats：lr 0.001、wd 0.1）、同資料（2021-22～2025-26 split=train，folds 1-4 訓練、fold 0 早停）、seed 0–4，三臂同一環境重訓（G3），5090 gq。
- 評估只跑一次 `e309_eval.py`：測試集（5 季 split=test）＋前向 2026-27（E-225 stints-2026-27.csv.gz，用 2025-26 特徵）。
- 採用候選（各新臂分開判，全部成立）：1 測試淨值 ΔMSE（5 seed 平均預測，新−基準）點估計 < 0；2 前向 ΔMSE ≤ 0；3 測試比賽 Brier Δ ≤ 0（k 在 fold 0 擬合）；4 護欄 ptsSide、tovLL、orbLL 各 Δ ≤ +0.0002。兩臂都過 → 取測試 ΔMSE 較低者；差 < 0.5 取 Z（欄少）。「顯著」另看 90% 區間上界 < 0，只報告。

## (b) sim（模擬引擎 0.1.3，E-166 k=2 同一棵樹）
- 不另加一層（會和 choiceDefender 重複算），而是**替換**：每位防守者 choiceDefender.three／paintGivenTwo 換成 rimDet／threeDet（sim 窗）換算的 logit（`prep_sim.py`：用 choice-fit 2025-26 截距的聯盟分布線性換算；raGivenPaint、cornerGivenThree 不動）；以 supportedMinutes 加權置中到舊值平均（聯盟出手分布不變）；沒有 rimDet 的人原始值 0。位置平均輪廓照同位置球員分鐘加權平均差位移，xAvg 重算（`sim/core309.mjs`）。
- 臂：B＝原樣（E-166 `checkpoint-k.jsonl`、`rr-k.jsonl`，k=2、c=−0.05625、pace=0.998125）；Z＝替換。同 seeds、同人群（E-166 frozen-groups 276 人）。
- 決定性檢查（先跑）：B 臂用新 harness 重跑前 10 人與 2 個 round-robin seed，須和 E-166 檔逐位元相同，否則中止並回報。
- 判定：j2＝276 人 sim 淨值 X 對 2022-25 RAPM（pooledO＋pooledD）×分鐘 Spearman（E-166 judge 同算法）；j2c＝同算法 PF/C 子群；j3＝30 隊淨勝分 MAE（E-140 T1_pace）。**Z 通過＝j2Δ ≥ −0.01 且 j3Δ ≤ +0.1 且（j2Δ ≥ +0.005 或 j2cΔ ≥ +0.02）**。護欄：聯盟禁區出手佔比差 ≤ 0.3 個百分點（只報告超出者）。
- 只報告：解析換算淨值——每壓低 1 個百分點禁區佔比，對手每 100 回合少幾分＝FGA/100 回合 ×0.01×（禁區每球得分 −被擋出去的出手落點每球得分；落點比例＝threeDet 對 rimDet 的 fga 加權斜率，其餘落中距），每球得分取 2025-26 stints 實測。列 Wembanyama、Jokić、Queta、Gobert、Draymond 換算值，以及 sim 裡 X 的變化。

## (c) 顯示欄（2026-27 live，最新一天 `live/<日期>/`）
- 人群＝`t-swap.json` 的 pool；對照值＝EPM 防守（`reports/impact-epm-2026-27/epm-live.csv` 的 D）與 T 換人 DEF（−oppPts100）。rimDet 用顯示窗。
- RIM 臂：R0＝現行 D30（`scripts/rim_blk_live.compute`，0.7·z(help)＋0.3·z(blk36)）；RZ20＝0.8·D30 分數＋0.2·z(rimDet)；RZ35＝0.65·D30 分數＋0.35·z(rimDet)。z 在人群內；合成後人群內重標準化，套回 help 在人群的平均與標準差（同 E-305）。2025-26 卡片頁同樣三臂（rimDet 用 2022-23..2025-26 全場次、EPM 2025-26 D）當第二季。
- DEF 臂：D0＝現行 DEF（`season_nav.off_def`＋`blend_t`，和網站同一條路）；DZ10／DZ20＝(1−w)·z(DEF)＋w·z(rimDet)，w＝0.1／0.2，套回 DEF 在人群的平均與標準差。只做 2026-27。
- 通過（每臂）：對 EPM 防守、T DEF 的 Spearman（全體、PF/C）各項 Δρ（臂−基準）≥ −0.02（RIM 另含 2025-26 EPM 兩項），且 PF/C 對 EPM 防守 Δρ ≥ +0.01。通過者取 PF/C 對 EPM 防守 ρ 最高；差 ≤ 0.003 取權重小的。都不過 → 不採用，不事後放寬。
- 只報告：各臂 PF/C 前 10 名、Wembanyama／Jokić／Queta／Stewart／Gobert 名次，標出明顯反直覺者。

## 已知背景（L-026）
開跑前看過：rimDet 前 15 名（Wemby 6.36、Jokić 6.04、Queta 5.90、Valanciunas、Draymond…）與上面的重疊相關。沒看過 rimDet 對 EPM、T DEF、RAPM 的相關，也沒跑過任何臂。權重網格（0.2／0.35、0.1／0.2）與門檻在看結果前定。

## 產出
本目錄 `report.md`（`git add -f`）、腳本、`results/`（T eval.json、sim judge.json、display.json）；`memory/experiments.md` E-309。
