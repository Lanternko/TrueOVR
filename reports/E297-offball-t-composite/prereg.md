# E-297 預註冊：無球細項進 Transformer（逐項控制變量）與合併「無球」能力值

- 日期：2026-11-09。角色：lead 自做（dispatch routing＝self），重運算 5090 `~/side_projects/pure_ovr/experiments/e297/`。
- 標準由執行者自訂並直接凍結（R-165）。凍結時尚未用任何新欄訓練。
- 起因：使用者 2026-11-09「如果 CRT 不重要，看能不能換成無球」→「先看哪些信號影響勝負明顯，控制變量逐一測試，Transformer 加哪些細項無球變量能提升準度或和 BPM／2K 的契合度；最後決定無球各變量的權重，合併成網站顯示的能力值」。
- 現況：creation 在 E-227 R2-stats 測試置換重要度 −1.33（41 欄第 38）；卡片每 10 點 +0.116／36。引力 GRV 已是 NBA.com 無球外線 Gravity（不重做）。E-181「被助攻得分」學不到（和 long 重疊）。

## 無球細項（逐季、和 E-227 stats 同口徑：上場 <200 分鐘遮罩；季內 z 分數）
來源 `reports/E239-tracking-full/data/`（NBA.com Synergy offensive Totals、pt SpeedDistance、pt CatchShoot），分鐘用 E-227 `stats-<季>.csv` 的 minutes（SpeedDistance／CatchShoot 用自己檔內 MIN）。
| 欄 | 定義 |
|---|---|
| cut36 | Synergy Cut 回合 ×36／分鐘 |
| cutPPP | Cut 每回合得分，(PTS＋30·聯盟 PPP)/(POSS＋30) |
| offScr36 | Synergy OffScreen 回合／36 |
| handoff36 | Synergy Handoff 回合／36 |
| spotup36 | Synergy Spotup 回合／36 |
| roll36 | Synergy PRRollman 回合／36 |
| putback36 | Synergy OffRebound 回合／36 |
| trans36 | Synergy Transition 回合／36 |
| distOff36 | DIST_MILES_OFF ×36／MIN |
| speedOff | AVG_SPEED_OFF |
| cs3a36 | CATCH_SHOOT_FG3A ×36／MIN |
| cs3pct | 接球三分 (FG3M＋50·聯盟率)/(FG3A＋50) |
Synergy 名單沒有的人（NBA.com 只列有足夠回合者）量記 0、PPP 記聯盟值；SpeedDistance／CatchShoot 沒有的人遮罩。效率類只放 cutPPP、cs3pct 兩欄（E-239：Synergy PPP 年對年 <0.3）。掩護助攻 screenAst36 已在 R2-stats，不重複。

## 第一階段：訊號篩選（只用 fold 0，不碰測試集；只報告、不設門檻、不影響第二階段要跑哪些臂）
基準 R2-stats（本次 5090 同環境重訓 seed 0–4）在 fold 0 的淨值殘差（每 100 回合，回合加權）對「A 邊五人 z 和 − B 邊五人 z 和」做加權迴歸，報每欄斜率、以場為單位 bootstrap 90% 區間；同時報對實際淨值（不扣 T）的原始斜率。＝「T 已知之外還有沒有勝負訊號」與「原始勝負訊號」。

## 第二階段：控制變量逐項加入 T
同架構、同超參數（tuning.json R2-stats：lr 0.001、wd 0.1）、同資料切分（2021-22～2025-26 split=train，folds 1–4 訓練、fold 0 早停），5 seed。
| 臂 | 輸入 |
|---|---|
| base | R2-stats 41 欄 |
| +<欄>（12 臂） | 41 欄＋單一無球欄 |
| ALL | 41＋12 欄 |
| SEL | 41＋前向選擇欄 |
SEL 前向選擇（只看 fold 0）：每步對剩餘候選各訓 seed 0–2，取 3 seed 平均預測的 fold 0 淨值 MSE；最佳候選比目前少 ≥1.0 才加入，最多 6 欄。第一步直接用單欄臂的 seed 0–2。選完後 SEL 補到 5 seed。

### 評估（凍結後只跑一次 eval）
樣本外：測試集（5 季 split=test 20% 場次）＋前向 2026-27（用 2025-26 特徵）。每臂對 base：淨值 MSE（5 seed 平均預測）、成對 bootstrap（以場 2000 次）、比賽 Brier（k 在 fold 0 擬合）、ptsSide／tovLL／orbLL。ALL、SEL 在測試集做 12 欄置換重要度。

### 契合度（2025-26 上場 ≥1000 分鐘母體，E-285 換人值同算法 4000 組）
每臂 Spearman：淨值 vs BPM、進攻值 vs OBPM、淨值 vs 2K27 overall（`reports/ovr-v55-2k27-compare/2k27_ratings.csv`，姓名正規化對齊），Δ 對 base，以球員 bootstrap 2000 次報 90% 區間。

### 採用候選（主臂 SEL；ALL 與單欄臂只報告，單欄臂有多重比較，不單獨當採用依據）
- 準度路線 A：測試 ΔMSE＜0、前向 ΔMSE≤0、測試 Brier Δ≤0、三護欄各 ≤＋0.0002，全部成立。
- 契合度路線 B：三個 ΔSpearman 平均 ≥＋0.01、沒有任何一個 ＜−0.01，且測試 ΔMSE ≤＋2.0。
- A 或 B 成立 → 採用候選。

## 第三階段：合併「無球」顯示能力值的權重
母體 2025-26 ≥1000 分鐘。三組候選權重（12 欄 z，全聯盟尺；權重都 ≥0 並標準化成和為 1）：
- W-eq：10 個量欄各 1、cutPPP 與 cs3pct 各 0.5。
- W-imp：ALL 臂 fold 0 置換重要度（MSE 上升），負值記 0。
- W-dist：ALL 臂進攻換人值「實際無球欄」減「無球 12 欄全遮罩」的差 ΔT_off，對 12 欄 z 做非負最小平方。
評估（只報 2025-26 描述性）：(1) 加到卡片 0.2.14a OVR 之上對 OBPM、2K27 overall 的 ΔR²（兩者平均＝主指標）；(2) 和 ΔT_off 的 Spearman；(3) 2024-25→2025-26 同人年對年相關（≥0.60 才可用）。主指標最高且 (3) 過的那組＝建議顯示權重；同分取 W-eq（較簡單）。
只報告：指名無球型（Derrick White、Klay Thompson、Aaron Gordon、Buddy Hield、Duncan Robinson、Sam Hauser、Josh Hart、Mikal Bridges、Jarrett Allen、Rudy Gobert、Dereck Lively II）與持球型（Luka Dončić、Trae Young、Shai Gilgeous-Alexander、James Harden）的無球百分位；各位置平均。

## 不在本次範圍
網站換格子、OVR 換掉 creation、每日抓 Synergy／SpeedDistance（上線前要補 registry）——依結果另由使用者裁定。
