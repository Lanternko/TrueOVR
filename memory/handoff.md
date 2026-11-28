# 交接（handoff）

只記「目前狀態」，每次收工整份覆寫，不往下追加日期段。每條最多兩行，細節寫進 findings／experiments／rulings 或報告檔，這裡只放 ID 與路徑。UI 小改不進本檔（看 git log）。舊版全文在 `archive/`（最近一份 `handoff-2026-11-09-full.md`）。
**多個 session 同時改本檔與工作樹**：覆寫前先重讀一次，只改自己負責的條目。

- **更新**：11-28 E-316～E-334、R-201～R-202（`E333-4FAM` 球隊四家族 80 模型＋賽程校準＋`E334` 滾動多任務球員 OVR 全數上線）；11-27 E-313～E-315、R-199～R-200；更早見 git log。

## 目前基準（線上）
- **球隊模型 `E333-4FAM`（80 模型＋多季窗口＋年齡＋賽程校準）＋球員 `E334` 滾動多任務 OVR**（11-28，R-201／R-202，未稽核）：`SetPool_age`／`Ridge_age`／`D_add_age`／`M2_age` 四家族 × 20 全 5 季權重（44 欄含年齡曲線，4 季 LOSO C0 `0.20897`／C2 `0.20302`；回退 `T_WEIGHTS=E315-ENS-MD` 或 `E306-R3`、`SCHED_CALIB=0`、`MULTI_PRIOR=0`）。球員 `e334_ovr_live.py` 13 季 L=40 多季衰減 EPM 15 模型滾動融合（跨季 EPM*W `0.81`、盲測 GameBrier `0.1993`；回退 `E334_OVR=0`）。新秀補欄（`ROOKIE_FILL=0`）。研究契約 `memory/research_contract.md`、閉環方向 `memory/closed_directions.md`。
- **RIM 加蓋帽 RG**（11-23，R-196）：有效蓋帽扣干擾，只顯示；回退 `RIM_RG=0`＝D30。
- **card／inseason 0.3.0 / 0.2.15**（R-191、E-310）：CRT＋PNR 合併放 creation 欄，RAPM 殘差加權進 OVR；回退 `E310=0`、`CRTPNR=0`。
- **inseason 0.2.14d／c**（R-188、R-190）：D<0 分鐘修正＋近況＋MIX×min(1,W(MPG))；回退 `NEG_MIN=0`、`GAME_ANCHOR=0`、`MIX_MIN=0`。
- **inseason 0.2.12e**（11-04）：復出老將補卡與用人層 hi＋新秀季前賽位移＋防守 D 個人場次軸（未修：復出老將 gravity＝70，L-127）。
- **追蹤量格子**（R-166）；**賽中近期加成 b=3、h=20**（R-150）；**0.2.12 tovSkill**（R-139）；**0.2.11 gravity**（R-137）。
- **網站**：trueovr.com；首頁 2026-27、`2025-26.html`；`/rank/`、`/games/`；只改 UI 用 `daily_inseason_update.py --shell`。排程 14:30／16:30＋04:30。
- **模擬 sim 0.1.3**（R-120）；防守 `nba-defense-v3`（R-010）；賽中 OVR C4（E-033）。

## 進行中（未稽核，待派 role-audit）
- **防守三步（R-178、L-137）**：① `help` 位置係數改 PG→C 遞增（現行 U 字形 PG .43／SG .01／SF .03／PF .37／C .29）→ ② 干擾／抄截／蓋帽獨立定係數 → ③ `DEF` 顯示對齊 T／EPM／加權。驗收看結構＋代表球員＋EPM／T 對齊＋OVR 不壞，不拿單季防守 RAPM 單一否決。**第一步 E-277 完成（採用 M1）**：help 斜率變兩層台階 PG≈SG≈SF＜PF≈C，OVR ΔR² −0.004 在雜訊內；Durant 只升 20 名。使用者採用 M1（R-179）。**第二步 E-278 完成（2/5 無候選）**：2025-26 蓋帽係數翻負／歸零 S1 不過；抄截四原點穩定為正、干擾≈0；只加蓋帽臂 DEF 對 EPM 防守 +0.030 但缺 S1。**E-280 蓋帽每 SD 0.3 已採用（R-180）**；E-281 拿掉 pressure 不採用、干擾不進。E-282 抄截只宜 0.1（3/5）；E-283 拆 pressure 分量、E-284 有球／無球犯規，自由擬合都全面變差，保留合成 pressure。E-285 T 加逼失誤／犯規：stint MSE −2.6 但 E-286 跨季球隊評分兩季都變差（Brier +0.0027），X 版不進球隊評分；E-287 OFF/DEF 各混 0.5 T 已上線（R-181，每日 t_swap_live）。待裁定抄截 0.1，之後第三步。`reports/E280-blk-weight/report.md``reports/E276-def-stl-blk-defl/report.md`
- **E-304 新秀五位置**（11-10，4/5）：S5 已上線 inseason 0.2.15a（R-192，`ROOKIE_POS5=0` 回退）；硬標籤跳 2–4 分，W5 連續版為備案。
- **E-298／E-300 主力權重**（11-10）：E-300 M 已上線（0.2.14c），未稽核；對手籃板修正量太小不上。RW3（live 63）仍高於 Avdija（75）：每 36 分換算＋小樣本防守意識，另案。`reports/E300-mix-minutes-opp/report.md`
- **E-296／E-299／E-302 單場→OVR**（11-10）：MR 已上線（0.2.14d）；能力值加快無效（F-179）。Yang 剩下的扣分來自卡片中鋒係數，接 E-299 C 非負係數（需卡片鏈重跑）。`reports/E302-attr-anchor/report.md`
- **E-271 低效中距＋慘 On/Off 扣分**（11-08，未 commit／未稽核）：`AR` +0.0085、`D` +0.0104 adopt_candidate，`A` 救回 Booker／Harden／Cade；待使用者選臂交 role-card 做 0.2.14。E-272 bog 進 T 不採用。`reports/E271-ineff-midrange-bog-penalty/report.md`
- **E-273 T 各版本同場次重測**（3/5）：各步區間跨 0，每隊滿 20 場重跑。`reports/team-model-versions/report.md`
- **R-171／R-172 戰力排行混入本季實際表現**（K10，`scripts/actual_blend.py`，回退 `ACTUAL_BLEND=0`）：11-07～11-21 曾失效，R-195 修好；E-306 回測支持 K10，F-172 的滿 20 場複查仍待做。
- **E-239 追蹤全套**（3/5）：單一特徵無穩健訊號；量類 42 個可當格子（已做）。待使用者：另開預註冊測定義一致子集（2024-25 起）進 OVR／Transformer；要不要每日抓追蹤（補 registry／audit）。`reports/E239-tracking-full/report.md`、F-160
- **E-230 新秀起點 SL／PS**：訊號小，PS 位移已套用（R-162）。待使用者決定要不要逐項起點實驗。
- **陣容 Transformer**：R-160 球隊評分已換 T，舊引擎備援。E-234／E-236／E-237 能力值→OVR Transformer 皆不勝 ridge，名單在 `reports/E234-…`、`E235-…`、`E237-…` 待人工檢查。
- **E-222 診斷**：30 隊滿 20 場時跑 `reports/E222-recent-boost-diagnostic/e222_eval.py` 一次。
- **E-151 年輕側年齡連續**：已預註冊，stints 達 450 場自動跑 `e151_eval.py`；不得提前比。
- **聯盟 3PAr 偏差**（R-146）：δ 暫不進引擎；節奏偏慢下一步未開。**0.2.10 待辦**（R-114）：role-audit 沒做、G5。

## 等使用者裁定
- **E-308**（4/5）：OVR 漏的是 RAPM 殘差（樣本外），on/off 無額外訊號；待裁定殘差進 OVR。`reports/E308-onoff-undervalue/`
- E-196／R-133 得分產量（未上線）、網站品牌名（已用 trueovr.com，舊候選作廢）、0.2.10a 後續（R-121）、R-117 停損、E-162／F-106 產量評價、賽中新秀 d 對不上（R-097）、E-139 換版平滑、正負值沾光（E-148）、小項。全文在 `archive/handoff-2026-11-05-full.md`。

## 待辦（非決策）
- **TODO T 版 DEF 進 OVR**：Durant 仍落後 VanVleet。
- Edwards 卡 #38 但 DARKO #9／2K 95；卡對 RAPM ρ 0.78→0.70，2026-27 季後做樣本外複查；sim 得分偏高 119.1 對 115.5。
- 等季末項 E-083、E-127、E-141：R-177 起改歷史季輪流驗證。

## 工作樹注意
- 共用 checkout：memory 條目檔與 `season_nav.py`、`build_*_viewer.py` 常混有別的 session 改動，只挑自己的段落。`reports/` 被 gitignore，要 `git add -f`。DeepSeek 餘額不足，auto_review 失效。

## 開放問題
- 長人偏袒量尺（E-102）；卡片 OVR 要不要接進對局（F-010）；體力與換人線擱置（R-068）。
