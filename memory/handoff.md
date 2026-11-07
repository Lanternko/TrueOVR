# 交接（handoff）

只記「目前狀態」，每次收工整份覆寫，不往下追加日期段。每條最多兩行，細節寫進 findings／experiments／rulings 或報告檔，這裡只放 ID 與路徑。UI 小改不進本檔（看 git log）。舊版全文在 `archive/`（最近一份 `handoff-2026-11-05-full.md`，含 11-05 前所有條目原文）。
**多個 session 同時改本檔與工作樹**：覆寫前先重讀一次，只改自己負責的條目。

- **更新**：2026-11-05 球隊評分 T 的 21 欄追蹤統計改本季混合（R-169、E-246）；3PT／FT 顯示欄換量準混合（R-168，未 commit）；球員卡加追蹤量格子並發布（R-166）；11-04 E-239 追蹤全套、inseason 0.2.12e（R-161～R-165）；11-03 球隊評分換 Transformer（R-160）、近期加成 b3h20（R-150）。

## 目前基準（線上）
- **inseason 0.2.12e**（11-04，已 commit）：復出老將補卡（R-161）＋新秀起點加季前賽位移（R-162）＋防守 D 個人場次軸（R-163）＋復出老將補進用人層 hi（R-164）。未修：復出老將 gravity＝70 佔位（L-127）。回退 `DEF_AXIS=calendar`、`RV_USAGE=0`、`RETURNING_VETS=0`、`PS_START=0`。
- **3PT／FT 顯示欄**（R-168，11-05，只改顯示、OVR 不動、未 commit／未發布）：3PT＝60% 量＋40% 率、FT＝只看命中率，PR99 以上每 SD +10 分；`scripts/blend_display.py`，兩頁已重建。
- **追蹤量格子**（R-166，11-05）：DRV／INS／CRT／PASS／3PT 提示卡加量類追蹤列，不進分數。`scripts/tracking_cells.py`；2026-27 資料是手動快照，重抓 `node scripts/fetch_tracking_cells.mjs <季> data/tracking-cells/<季>` 後重建頁面。
- **賽中近期加成 b=3、h=20**（R-150）；**card／inseason 0.2.12**（R-139，tovSkill 看持球時間）；**0.2.11**（R-137，引力 gravity）。回退旗標 `RECENT_BOOST=0`、`TOV_POSS=0`、`GRAVITY=0`。
- **網站**：trueovr.com；首頁 2026-27、`2025-26.html`；排行／賽程用乾淨路徑 `/rank/`、`/games/`。只改 UI 用 `python -I scripts/daily_inseason_update.py --shell` 立刻發布；每日排程 14:30／16:30＋22:30（registry `basketball-inseason-daily`）。能力值說明在 `season_nav.py` 的 `ATTR_TIPS`；新格子提示用 `sn.cell_tip()`。
- **球隊評分 T 追蹤統計本季混合**（R-169，11-05）：hustle／rimthree／matchup／adv 21 欄照 box 規則 w=min/(min+500) 混本季；`e229_live.BLEND_DEFAULT`，設 `()` 回退。回測 Brier −0.0027（區間跨 0，非劣）。`reports/E246-t-tracking-blend/report.md`
- **模擬 sim 0.1.3**（R-120）；防守 `nba-defense-v3`（R-010）；賽中 OVR C4（E-033）。

## 進行中（未稽核，待派 role-audit）
- **R-171 戰力排行混入本季實際表現**（11-07，E-253 K10）：殘差 ÷(場數+10) 加回 T 評分，`scripts/actual_blend.py`、回退 `ACTUAL_BLEND=0`；已發布（POR 14→9）。**R-172**：殘差改每天對今天的 T 重算（`today-margins.json`，避免和本季 OVR 更新重複計入，L-129）。K10 是看過前向才選，每隊滿 20 場用凍結 K10 前向複查一次（F-172）。
- **E-255 擋拆持球新能力值**（11-07，4/5 候選，未稽核）：LineupNet 量率混合 w＝0.6，下季進攻 RAPM R² +0.0146（五道閘全過），每 10 點 ≈ +0.10 勝（30 分鐘）；增益在前鋒。副作用：低回合球員率百分位虛高。待使用者：要不要加 pnr 欄（先修低回合門檻再驗）。`reports/E255-pnr-handler-lineup-tf/report.md`
- **POR 被低估追查**（11-07）：E-254 出手結構、E-256 殘差分運氣／結構、E-257 籃板率都不採用（1/5）；只有三分命中會回落（L-130），T 沒有系統性缺口，POR 剩下差距是 7 場只採信四成（R-171）。籃板輸入 T 本來就有、POR 今年籃板率與去年一樣（L-131）。`reports/por-offense-diag/`。
- **E-239 追蹤全套**（3/5）：單一特徵無穩健訊號；量類 42 個可當格子（已做）。待使用者：另開預註冊測定義一致子集（2024-25 起）進 OVR／Transformer；要不要每日抓追蹤（補 registry／audit）。`reports/E239-tracking-full/report.md`、F-160
- **E-240 三分量與率拆法**（11-05，3/5 不採用）：量＋率分開放對下季進攻 RAPM R² +0.014，未過預註冊門檻（F-161）。使用者指定一次測一項；待決定下一項（建議罰球，其次中距、切入），框架可直接換項。`reports/E240-three-point-volume-rate/report.md`
- **E-241 三分量率混合比例掃描（舊表格 TF）**（11-05，2/5 不採用）：570 筆球員表直接訓 Transformer 嚴重過擬合（R² 0–0.06）；已由 E-242 陣容 Transformer 取代（F-162）。`reports/E241-three-point-blend-sweep/report.md`
- **E-245 中距離 mid 量率比例**（11-05，3/5 不採用）：同框架換 `mid` 欄，w＝0.8 對現行 `mid` R² +0.0071、三折全正，但 90% CI 跨零、測試場次沒更準，`mid` 維持不動；三分／罰球／中距離量率系列到此為止，等使用者裁定（F-165）。`reports/E245-mid-lineup-tf-blend/report.md`
- **E-244 罰球 ft 量率比例**（11-05，2/5 不採用）：同 E-242 框架換 `ft` 欄，w* 對現行 `ft` 增益 +0.0029 未過門檻、測試場次沒更準，`ft` 維持不動（F-164）。`reports/E244-ft-lineup-tf-blend/report.md`
- **E-242 陣容 Transformer 三分量率比例量測**（11-05，4/5 停下交使用者裁定；11-05 裁定 `long` 維持不改，R-167）：改用五季 111,499 個 stints 訓練 `LineupNet`，消除過擬合並量出平滑倒 U 曲線——下季進攻 RAPM 最佳在 **w＝0.5–0.6**（0.2328 vs `long` 0.2265，與 ridge 一致），測試場次對戰得分 MSE 最佳在 **w＝0.8**（比純率 −4.92），自學權重 `WL` 收斂至 **w＝0.34±0.025**。因三季 867 人次 CI 跨零，待使用者裁定：三分要不要改採 w＝0.5–0.6，以及下一步要不要用同套 LineupNet 框架測罰球（F-163）。`reports/E242-lineup-tf-three-blend/report.md`
- **E-246**：完成未稽核。後續想法（未開）：量類進攻追蹤（持球／接球三分、擋拆、handoff，2024-25 起定義一致）當新欄重訓 T，需新預註冊。
- **E-238 無球追蹤**：補不進 OVR（H3 不過），只當個案顯示。F-158
- **E-230 新秀起點 SL／PS**：訊號小，PS 位移已套用（R-162）。待使用者決定要不要逐項起點實驗。
- **陣容 Transformer**：R-160 球隊評分已換 T，舊引擎備援。E-234／E-236／E-237 能力值→OVR Transformer 皆不勝 ridge，名單在 `reports/E234-…`、`E235-…`、`E237-…` 待人工檢查。
- **E-222 診斷**：30 隊滿 20 場時跑 `reports/E222-recent-boost-diagnostic/e222_eval.py` 一次。
- **E-151 年輕側年齡連續**：已預註冊，stints 達 450 場自動跑 `e151_eval.py`；不得提前比。
- **聯盟 3PAr 偏差**（R-146）：δ 暫不進引擎；節奏偏慢下一步未開。**0.2.10 待辦**（R-114）：role-audit 沒做、G5。

## 等使用者裁定
- E-196／R-133 得分產量（未上線）、網站品牌名（已用 trueovr.com，舊候選作廢）、0.2.10a 後續（R-121）、R-117 停損、E-162／F-106 產量評價、賽中新秀 d 對不上（R-097）、E-139 換版平滑、正負值沾光（E-148）、小項清單。全文在 `archive/handoff-2026-11-05-full.md`。

## 待辦（非決策）
- Edwards 卡 #38 但 DARKO #9／2K 95；卡對 RAPM ρ 0.78→0.70，2026-27 季後做樣本外複查；sim 得分偏高 119.1 對 115.5。
- 等季末：E-083、E-127、E-141（2026-12-31）。

## 工作樹注意
- 共用 checkout：memory 條目檔與 `season_nav.py`、`build_*_viewer.py` 常混有別的 session 改動，只挑自己的段落。`reports/` 被 gitignore，要 `git add -f`。DeepSeek 餘額不足，auto_review 失效。

## 開放問題
- 長人偏袒量尺（E-102）；卡片 OVR 要不要接進對局（F-010）；體力與換人線擱置（R-068）。
