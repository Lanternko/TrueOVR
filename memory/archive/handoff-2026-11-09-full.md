# 交接（handoff）

只記「目前狀態」，每次收工整份覆寫，不往下追加日期段。每條最多兩行，細節寫進 findings／experiments／rulings 或報告檔，這裡只放 ID 與路徑。UI 小改不進本檔（看 git log）。舊版全文在 `archive/`（最近一份 `handoff-2026-11-05-full.md`，含 11-05 前所有條目原文）。
**多個 session 同時改本檔與工作樹**：覆寫前先重讀一次，只改自己負責的條目。

- **更新**：2026-11-09 R-178／L-137 確立防守三階段分步修正與分層驗收規則（禁拿單季防守 RAPM 單一裁判鬼打牆；依序修：① `help` 位置係數 PG→C 由小到大遞增 → ② 干擾球／抄截／蓋帽獨立與係數 → ③ `DEF` 顯示欄對齊 Transformer／EPM 或加權）；2026-11-08 E-271 低效中距卡球＋慘 On/Off 扣分與「投進難球／強守弱攻隊友」雙重豁免四季輪流驗證（D／AR adopt_candidate、B 4/4 折正 +0.0148 顯著勝 U、A +0.0115 救回 Booker／Harden／Cade／Franz Wagner，F-176）；R-177 禁止「等季末」當驗證、改歷史季輪流驗證；E-268 高球權扣分四季輪流驗證 adopt_candidate；2026-11-07 card／inseason 0.2.13 加擋拆 pnr（R-173）；2026-11-05 球隊評分 T 的 21 欄追蹤統計改本季混合（R-169、E-246）；3PT／FT 顯示欄換量準混合（R-168，未 commit）；球員卡加追蹤量格子並發布（R-166）；11-04 E-239 追蹤全套、inseason 0.2.12e（R-161～R-165）；11-03 球隊評分換 Transformer（R-160）、近期加成 b3h20（R-150）。

## 目前基準（線上）
- **card／inseason 0.2.13**（11-07，R-173，E-258）：加能力值擋拆持球 pnr（Synergy 四季窗口含本季，量率各半、率只在 ≥50 回合者裡排）；卡片全部係數重擬合，正式卡 `reports/card-0.2.13/`；前 20 名不換人。回退 `PNR=0`（＝0.2.12e）。role-audit、G5 未做；副作用 Alexander-Walker 卡片 66→78 名。
- **inseason 0.2.12e**（11-04，已 commit）：復出老將補卡（R-161）＋新秀起點加季前賽位移（R-162）＋防守 D 個人場次軸（R-163）＋復出老將補進用人層 hi（R-164）。未修：復出老將 gravity＝70 佔位（L-127）。回退 `DEF_AXIS=calendar`、`RV_USAGE=0`、`RETURNING_VETS=0`、`PS_START=0`。
- **3PT／FT 顯示欄**（R-168，11-05，只改顯示、OVR 不動、未 commit／未發布）：3PT＝60% 量＋40% 率、FT＝只看命中率，PR99 以上每 SD +10 分；`scripts/blend_display.py`，兩頁已重建。
- **追蹤量格子**（R-166，11-05）：DRV／INS／CRT／PASS／3PT 提示卡加量類追蹤列，不進分數。`scripts/tracking_cells.py`；2026-27 資料是手動快照，重抓 `node scripts/fetch_tracking_cells.mjs <季> data/tracking-cells/<季>` 後重建頁面。
- **賽中近期加成 b=3、h=20**（R-150）；**card／inseason 0.2.12**（R-139，tovSkill 看持球時間）；**0.2.11**（R-137，引力 gravity）。回退旗標 `RECENT_BOOST=0`、`TOV_POSS=0`、`GRAVITY=0`。
- **網站**：trueovr.com；首頁 2026-27、`2025-26.html`；排行／賽程用乾淨路徑 `/rank/`、`/games/`。只改 UI 用 `python -I scripts/daily_inseason_update.py --shell` 立刻發布；每日排程 14:30／16:30＋22:30（registry `basketball-inseason-daily`）。能力值說明在 `season_nav.py` 的 `ATTR_TIPS`；新格子提示用 `sn.cell_tip()`。
- **球隊評分 T 追蹤統計本季混合**（R-169，11-05）：hustle／rimthree／matchup／adv 21 欄照 box 規則 w=min/(min+500) 混本季；`e229_live.BLEND_DEFAULT`，設 `()` 回退。回測 Brier −0.0027（區間跨 0，非劣）。`reports/E246-t-tracking-blend/report.md`
- **模擬 sim 0.1.3**（R-120）；防守 `nba-defense-v3`（R-010）；賽中 OVR C4（E-033）。

## 進行中（未稽核，待派 role-audit）
- **防守三階段分步修正（R-178、L-137，2026-11-09）**：推翻 E-274～E-276 拿單季防守 RAPM 當唯一死門檻的做法，改分三步推進：(1) **第一步**：協防護框（`help`）位置影響係數改為 PG → SG → SF → PF → C 由小到大單調排列（修掉現行 PG 0.43、SG 0.01、SF 0.03、PF 0.37、C 0.29 的 U 字形凹陷）；(2) **第二步**：將干擾球（deflections）、抄截（steals）、蓋帽（blocks）獨立出來，測定各自合理係數與是否進步；(3) **第三步**：決定網站 `DEF` 顯示欄對齊 Transformer、對齊 EPM 或加權混合（使 Durant > VanVleet 等直覺與客觀指標到位）。
- **E-274 DEF 顯示欄改 T 換人防守值**（11-08，1/5 不採用）：預測下季防守 RAPM ρ D0 0.422 > D3 0.397 > D2 0.367；D1 兩側加分 +0.004（EPM 防守 0.704→0.761）未過門檻，待使用者決定要不要當小改。`reports/E274-def-display-transformer/report.md`
- **E-275 DEF 欄蒸餾 T**（11-08，1/5 不採用）：能力值擬合 T 換人值，合併 ρ D7 0.404／D6 0.361／D5 0.322 都輸 D0 0.422；T 路線收掉。`reports/E275-def-distill-transformer/report.md`
- **E-276 抄截／干擾／蓋帽獨立欄位**（11-09，1/5 不採用）：D8 三項全加 0.417、只加蓋帽 D8c 0.429（三折都小贏）vs D0 0.422；抄截干擾係數不穩。壓迫拆四分量各自給權重 D11 0.408 更差，拆開只能當顯示（權重不變）。改四季窗口＋合併擬合 D12 0.415 仍輸，權重穩定後干擾最重、抄截≈0；凡用 RAPM 重擬合都在最後一折退步。診斷：換隊者上純 RAPM 掉到 0.239 但現行 DEF 0.444 不降，加分不是只吃體系；無加分時拆分量 +0.02。待使用者決定蓋帽＋D1 是否當顯示欄小改。`reports/E276-def-stl-blk-defl/report.md`
- **E-269 防守係數跨位置共用**（11-08，3/5，未稽核）：A1／A2／A4 共用樣本外變差；A3（分位置 ridge 收縮）過門檻 ΔR² +0.0074，但區間碰 0、不是防守帶來的。待使用者決定要不要做 A3 拆解實驗。起因：VanVleet DEF +1.78 中 1.32 來自 RAPM 加分、SF help 係數 ≈0。賽中 ranking.csv `MIN`→`MINprior`（L-136）。`reports/E269-def-coef-pooling/report.md`
- **得分型前鋒／低效中距高球權被高估追查**（11-08，E-259～E-271，未 commit；R-176 以 EPM／RAPM 為準）：E-268 純 `usg36` 扣分 U +0.008 但誤傷 Booker／Brunson／Harden／Cade／Franz Wagner／Flagg。**E-271** 納入中距急停少助攻＋低效＋當季 On/Off 慘，並設「投進難球＋強守弱攻隊友」雙重豁免（F-176）：`AR`（對 `usg36` 殘差化）+0.0085 與 `D` +0.0104 四關全過 `adopt_candidate`（通過 L-135 殘差檢驗），`A`（全套）+0.0115、`B` +0.0148（4/4 折全正，顯著勝 U +0.0070）；`A`/`AR` 救回 Booker（42→38）、Harden（121→115）、Cade（9→9）、Franz Wagner（22→21）、Durant（17→17），並對 Ingram（75→153）、Banchero（142→206）、DeRozan（77→103）、Jalen Green（173→253）重扣平均 60～62 名。 **E-272**（11-08，2/5 不採用）：bog 當 Transformer 輸入，陣容 Transformer 下季淨值 R² A +0.015／AR +0.014 未達門檻 0.016，球隊比賽 2025-26 Brier 全顯著變差（+0.003～+0.007）；H0 證實現行 Transformer 也高估這群人。bog 只留卡片層。
  未稽核。待使用者選採用臂（建議 `AR` 或 `A`）交 role-card 做 0.2.14 候選＋role-audit 稽核。`reports/E271-ineff-midrange-bog-penalty/report.md`
- **E-273 T 各版本同場次重測**（11-08，3/5，未稽核）：A 集合 132 場 Brier M0 0.2050→T0 0.1936→T1 0.1911→K10 0.1915／today 0.1909，各步區間跨 0；只有 2025-26 的 M0→T0 顯著。待每隊滿 20 場重跑。`reports/team-model-versions/report.md`、`reports/status/team_model_versions.json`
- **R-171 戰力排行混入本季實際表現**（11-07，E-253 K10）：殘差 ÷(場數+10) 加回 T 評分，`scripts/actual_blend.py`、回退 `ACTUAL_BLEND=0`；已發布（POR 14→9）。**R-172**：殘差改每天對今天的 T 重算（`today-margins.json`，避免和本季 OVR 更新重複計入，L-129）。K10 是看過前向才選，每隊滿 20 場用凍結 K10 前向複查一次（F-172）。
- **E-255／E-258 擋拆 pnr**：已上線 0.2.13（R-173）；待 role-audit 與 G5（前十長人／2K27 抽查）。`reports/E258-pnr-lowvol-gate/report.md`
- **POR 被低估追查**（11-07）：E-254 出手結構、E-256 殘差分運氣／結構、E-257 籃板率都不採用（1/5）；只有三分命中會回落（L-130），T 沒有系統性缺口，POR 剩下差距是 7 場只採信四成（R-171）。籃板輸入 T 本來就有、POR 今年籃板率與去年一樣（L-131）。`reports/por-offense-diag/`。
- **E-239 追蹤全套**（3/5）：單一特徵無穩健訊號；量類 42 個可當格子（已做）。待使用者：另開預註冊測定義一致子集（2024-25 起）進 OVR／Transformer；要不要每日抓追蹤（補 registry／audit）。`reports/E239-tracking-full/report.md`、F-160
- **E-240 三分量與率拆法**（11-05，3/5 不採用）：量＋率分開放對下季進攻 RAPM R² +0.014，未過預註冊門檻（F-161）。使用者指定一次測一項；待決定下一項（建議罰球，其次中距、切入），框架可直接換項。`reports/E240-three-point-volume-rate/report.md`
- **E-241 三分量率混合比例掃描（舊表格 TF）**（11-05，2/5 不採用）：570 筆球員表直接訓 Transformer 嚴重過擬合（R² 0–0.06）；已由 E-242 陣容 Transformer 取代（F-162）。`reports/E241-three-point-blend-sweep/report.md`
- **E-251 stint 層級確認**（11-05，4/5）：deflections 兩關都過（陣容網路沒看過的比賽淨誤差 −7.7、約 0.07%；下季防守 RAPM +0.020 三折全正），SHUF 與 C2R 對照乾淨；boxrebm、contested 未確認，結案。弱線索，抓手快型（Caruso）不抓護框型。已先加隱藏欄位 `deflP`（R-170，不顯示、不計分；賽中 `pres-drive.json`＋正式卡 `reports/card-0.2.12b/deflP-2025-26.csv`，未 commit）。下一步：待使用者決定是否另開預註冊把 pace 標準化干擾球併入 pressure（不獨立成屬性）。`reports/E251-stint-defense-tracking/report.md`（F-169）。
- **E-250 防守追蹤量 pace 標準化**（11-05，3/5）：contested 的球隊變差是對手出手量假象，標準化後歸零但無正向訊號（結案）；deflections 球員層級 +0.021（三折全正）、球隊無；boxrebm 球隊同季仍 +0.10 但對球員無用。使用者已選 A：stint 層級確認（E-251，見上一條）。`reports/E250-defense-tracking-pace/report.md`（F-168）。
- **E-249 防守追蹤量（球隊防守效率目標）**（11-05，3/5）：deflections 在球隊層級沒被證實（前向 +0.052、同季 +0.016 皆跨零）；boxreb 同季過（+0.110）但疑反向因果；前向只有 120 隊季、解析度不足無法判定。待使用者：是否開 stint 層級 LineupNet 確認（建議）。`reports/E248-defense-tracking-team/report.md`（F-167）。
- **E-247 防守追蹤量逐項**（11-05，3/5）：hustle 八項一次加一個預測下季防守 RAPM（基底 R² 0.135）；contested 2PT 不補（−0.003），deflections／36 +0.017 三折全正但八選一 BH 未過；待使用者決定要不要單假設確認 deflections（2019-20 起更多季）與擴大到護框／matchup 防守（F-166）。`reports/E247-defense-tracking-single/report.md`
- **E-252 近框 short 量率比例＋本季加權**（11-06，1/5 不採用，完成未稽核）：同 E-245 框架 8 種子，現行 `short` M1 R² 0.2131 最高，最佳混合 W06 −0.0030、最近季×2 −0.0042、單季 −0.0052，0/3 候選過；`short` 維持不動，F-170 額度 1/3，建議結案（F-171）。待使用者：是否結案、是否只換顯示欄（類 R-168）。`reports/E252-short-lineup-tf-blend/report.md`
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
- 等季末：E-083、E-127、E-141（2026-12-31）。（R-177 起「等季末」不能當驗證方案；這些項目下次碰到時改成歷史季輪流驗證。）

## 工作樹注意
- 共用 checkout：memory 條目檔與 `season_nav.py`、`build_*_viewer.py` 常混有別的 session 改動，只挑自己的段落。`reports/` 被 gitignore，要 `git add -f`。DeepSeek 餘額不足，auto_review 失效。

## 開放問題
- 長人偏袒量尺（E-102）；卡片 OVR 要不要接進對局（F-010）；體力與換人線擱置（R-068）。
