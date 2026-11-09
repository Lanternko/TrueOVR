# 交接（handoff）

只記「目前狀態」，每次收工整份覆寫，不往下追加日期段。每條最多兩行，細節寫進 findings／experiments／rulings 或報告檔，這裡只放 ID 與路徑。UI 小改不進本檔（看 git log）。舊版全文在 `archive/`（最近一份 `handoff-2026-11-09-full.md`）。
**多個 session 同時改本檔與工作樹**：覆寫前先重讀一次，只改自己負責的條目。

- **更新**：2026-11-09 E-296 負 g 分鐘懲罰（3/5）、E-295／E-298、card／inseason 0.2.14a 上線（R-186）；更早的見 git log 與 `archive/handoff-2026-11-09-full.md`。

## 目前基準（線上）
- **card／inseason 0.2.14a**（11-09，R-186）：MIX 加分改 E-294 H（z 減半位置平均＋tanh＋C=1／PF=.243），m_pos 凍結、特徵每天混本季。卡 `reports/card-0.2.14a/`；回退 `MIX_H=0`＝0.2.14、`MIX_BONUS=0`＝0.2.13a。
- **inseason 0.2.12e**（11-04，已 commit）：復出老將補卡（R-161）＋新秀起點加季前賽位移（R-162）＋防守 D 個人場次軸（R-163）＋復出老將補進用人層 hi（R-164）。未修：復出老將 gravity＝70 佔位（L-127）。回退 `DEF_AXIS=calendar`、`RV_USAGE=0`、`RETURNING_VETS=0`、`PS_START=0`。
- **3PT／FT 顯示欄**（R-168，11-05，只改顯示、OVR 不動、未 commit／未發布）：3PT＝60% 量＋40% 率、FT＝只看命中率，PR99 以上每 SD +10 分；`scripts/blend_display.py`，兩頁已重建。
- **追蹤量格子**（R-166，11-05）：DRV／INS／CRT／PASS／3PT 提示卡加量類追蹤列，不進分數。`scripts/tracking_cells.py`；2026-27 資料是手動快照，重抓 `node scripts/fetch_tracking_cells.mjs <季> data/tracking-cells/<季>` 後重建頁面。
- **賽中近期加成 b=3、h=20**（R-150）；**card／inseason 0.2.12**（R-139，tovSkill 看持球時間）；**0.2.11**（R-137，引力 gravity）。回退旗標 `RECENT_BOOST=0`、`TOV_POSS=0`、`GRAVITY=0`。
- **網站**：trueovr.com；首頁 2026-27、`2025-26.html`；排行／賽程用乾淨路徑 `/rank/`、`/games/`。只改 UI 用 `python -I scripts/daily_inseason_update.py --shell` 立刻發布；每日排程 14:30／16:30＋22:30（registry `basketball-inseason-daily`）。OVR 折線 `ovr_history.py` 平行＋5090 分攤，歷史日去洩漏（L-134）。能力值說明在 `season_nav.py` 的 `ATTR_TIPS`；新格子提示用 `sn.cell_tip()`。
- **球隊評分 T 追蹤統計本季混合**（R-169，11-05）：hustle／rimthree／matchup／adv 21 欄照 box 規則 w=min/(min+500) 混本季；`e229_live.BLEND_DEFAULT`，設 `()` 回退。回測 Brier −0.0027（區間跨 0，非劣）。`reports/E246-t-tracking-blend/report.md`
- **模擬 sim 0.1.3**（R-120）；防守 `nba-defense-v3`（R-010）；賽中 OVR C4（E-033）。

## 進行中（未稽核，待派 role-audit）
- **防守三步（R-178、L-137）**：① `help` 位置係數改 PG→C 遞增（現行 U 字形 PG .43／SG .01／SF .03／PF .37／C .29）→ ② 干擾／抄截／蓋帽獨立定係數 → ③ `DEF` 顯示對齊 T／EPM／加權。驗收看結構＋代表球員＋EPM／T 對齊＋OVR 不壞，不拿單季防守 RAPM 單一否決。**第一步 E-277 完成（採用 M1）**：help 斜率變兩層台階 PG≈SG≈SF＜PF≈C，OVR ΔR² −0.004 在雜訊內；Durant 只升 20 名。使用者採用 M1（R-179）。**第二步 E-278 完成（2/5 無候選）**：2025-26 蓋帽係數翻負／歸零 S1 不過；抄截四原點穩定為正、干擾≈0；只加蓋帽臂 DEF 對 EPM 防守 +0.030 但缺 S1。**E-280 蓋帽每 SD 0.3 已採用（R-180）**；E-281 拿掉 pressure 不採用、干擾不進。E-282 抄截只宜 0.1（3/5）；E-283 拆 pressure 分量、E-284 有球／無球犯規，自由擬合都全面變差，保留合成 pressure。E-285 T 加逼失誤／犯規：stint MSE −2.6 但 E-286 跨季球隊評分兩季都變差（Brier +0.0027），X 版不進球隊評分；E-287 OFF/DEF 各混 0.5 T 已上線（R-181，每日 t_swap_live）。待裁定抄截 0.1，之後第三步。`reports/E280-blk-weight/report.md`E-274～E-276、E-269 舊結論（D0 ρ 0.422 最高）依 R-178 不再當否決依據。`reports/E276-def-stl-blk-defl/report.md`
- **E-298 主力權重**（11-09，2/5 待裁定）：加分×min(1,MPG/30) 線上 Avdija 74>Clingan 81，但 T／EPM 顯著變差；RW3 高估來自每 36 分＋小樣本防守，未處理。`reports/E298-core-weight/`
- **E-296 負 g 分鐘懲罰**（11-09，3/5）：A2-15-R adopt_candidate 待裁定；好表現掉分 26% 主因在每 36 估計，待開下一步。`reports/E296-neg-g-minutes/report.md`
- **E-271 低效中距＋慘 On/Off 扣分**（11-08，未 commit／未稽核）：`AR` +0.0085、`D` +0.0104 adopt_candidate，`A` 救回 Booker／Harden／Cade；待使用者選臂交 role-card 做 0.2.14。E-272 bog 進 T 不採用。`reports/E271-ineff-midrange-bog-penalty/report.md`
- **E-273 T 各版本同場次重測**（3/5）：各步區間跨 0，每隊滿 20 場重跑。`reports/team-model-versions/report.md`
- **R-171 戰力排行混入本季實際表現**（11-07，E-253 K10）：殘差 ÷(場數+10) 加回 T 評分，`scripts/actual_blend.py`、回退 `ACTUAL_BLEND=0`；已發布（POR 14→9）。**R-172**：殘差改每天對今天的 T 重算（`today-margins.json`，避免和本季 OVR 更新重複計入，L-129）。K10 是看過前向才選，每隊滿 20 場用凍結 K10 前向複查一次（F-172）。
- **E-239 追蹤全套**（3/5）：單一特徵無穩健訊號；量類 42 個可當格子（已做）。待使用者：另開預註冊測定義一致子集（2024-25 起）進 OVR／Transformer；要不要每日抓追蹤（補 registry／audit）。`reports/E239-tracking-full/report.md`、F-160
- **E-230 新秀起點 SL／PS**：訊號小，PS 位移已套用（R-162）。待使用者決定要不要逐項起點實驗。
- **陣容 Transformer**：R-160 球隊評分已換 T，舊引擎備援。E-234／E-236／E-237 能力值→OVR Transformer 皆不勝 ridge，名單在 `reports/E234-…`、`E235-…`、`E237-…` 待人工檢查。
- **E-222 診斷**：30 隊滿 20 場時跑 `reports/E222-recent-boost-diagnostic/e222_eval.py` 一次。
- **E-151 年輕側年齡連續**：已預註冊，stints 達 450 場自動跑 `e151_eval.py`；不得提前比。
- **聯盟 3PAr 偏差**（R-146）：δ 暫不進引擎；節奏偏慢下一步未開。**0.2.10 待辦**（R-114）：role-audit 沒做、G5。

## 等使用者裁定
- E-196／R-133 得分產量（未上線）、網站品牌名（已用 trueovr.com，舊候選作廢）、0.2.10a 後續（R-121）、R-117 停損、E-162／F-106 產量評價、賽中新秀 d 對不上（R-097）、E-139 換版平滑、正負值沾光（E-148）、小項。全文在 `archive/handoff-2026-11-05-full.md`。

## 待辦（非決策）
- **位置斷崖 E-295**：W1 斷崖消失，errata-1 後候選待核可（`card-0.2.14b-cand/`）。**audit-0.2.14b 4/5 建議採用**（獨立重算差 4e-15、前瞻台逐位元一致）；上線前補 3 人 BBRef 別名（L-147）、賽中改凍結 π＋身高表（`reports/audit-0.2.14b/`）
- **TODO T 版 DEF 進 OVR**：Durant 仍落後 VanVleet。
- Edwards 卡 #38 但 DARKO #9／2K 95；卡對 RAPM ρ 0.78→0.70，2026-27 季後做樣本外複查；sim 得分偏高 119.1 對 115.5。
- 等季末項 E-083、E-127、E-141：R-177 起改歷史季輪流驗證。

## 工作樹注意
- 共用 checkout：memory 條目檔與 `season_nav.py`、`build_*_viewer.py` 常混有別的 session 改動，只挑自己的段落。`reports/` 被 gitignore，要 `git add -f`。DeepSeek 餘額不足，auto_review 失效。

## 開放問題
- 長人偏袒量尺（E-102）；卡片 OVR 要不要接進對局（F-010）；體力與換人線擱置（R-068）。
