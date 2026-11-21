# handoff 日誌歸檔（2026-10-28 ～ 2026-10-30）

從 handoff.md 移出的日期段落，原文未改。只用 grep 查，不整份讀；要找的結論應已寫進 findings／experiments／rulings／lessons 對應 ID。

## 2026-10-28 晚間更新
- 狀態板已切 card 0.1.2（0.1.1 + E-060 onBall）。E-063（模擬吃 E-060 onBall，原誤登 E-062）驗收不過，模擬維持 v53 onBall。
- R-024：E-057 threeValue 上線為 3PT 顯示欄（正式卡＋賽中），原 long 顯示為「3P準」，OVR 不變。賽中 inseason 0.1.1。
- 每日自動更新：`scripts/daily_inseason_update.py`（測試 `python -I test/daily_inseason_update.py`），排程 "Basketball Inseason Daily" 每天 14:30（主）＋16:30（補跑）pythonw；最後一場美東約 0:45–1:00 結束＝台北 EDT 12:45／EST 13:45，registry `basketball-inseason-daily`。狀態 `reports/ovr-inseason-2026-27/live/publish_state.json`，log `live/logs/daily.log`。首次發布 inseason 0.1.1a（gh-pages 1e53a79）已在線上確認。
- 注意：排程跑的是工作樹裡尚未 commit 的腳本（fetch_inseason_2026_27.js、build_inseason_viewer.py、daily_inseason_update.py 等），R-023 的「同 git HEAD 可重現」要等使用者同意 commit 後才成立。
- 2026-10-28 23:30：賽中先驗換成 card 0.1.2（inseason 0.1.2a，gh-pages 302b4a6），3P準 欄拿掉、新增 FD 製造犯規欄。drive 改 PBP 版、算不出本季值 → 凍結；foulDraw 用 FTA/FGA 百分位照 C4 更新（SGA ΔOVR −7.7 主要來自 foulDraw 96→82，未事後凍結）。f=0 檢查最大差 0.059；但 lastOVR 與 0.1.2 卡 ovr 有 2 人差 0.6–0.7（D.White、Caruso，pressure 高的防守者，原因未查），其餘 ≤0.4。見 L-034。
- 2026-10-29：網站加賽季切換（gh-pages a247ab8）：首頁＝2026-27 賽中，`2025-26.html`＝card 0.1.2 正式卡（`scripts/build_card_viewer.py`，共用 `scripts/season_nav.py`）；數值模式套等第色、3PT 副標「三分」、3P%/3PA 欄拿掉。每日發布一次提交兩檔。
- 未修：賽中 ΔOVR 對的是 lastOVR（White 98.3）不是正式卡 99.0，White 顯示 +0.55 實為 −0.1；要查 lastOVR 與正式卡差異原因，修好後 ΔOVR 改對 formalOVR。
- E-065 完成（2026-10-29）：WinImp（R-025 字面）V1 不過，ρ 0.41／0.35 輸卡片；事後用 fitA/fitB 卡仍輸。V2 字面過但無對照（L-036）。White 樣本外不高估；Kenrich 高估。輸出與 verdict_e065.py 未 commit。

## 2026-10-29 使用者抽查 McCain／收縮目標
- R-029：使用者把 McCain 排在 2026 雷霆第 8（Wallace 之後、Joe 之前）；card 0.2.0 是 57.9（#359），費城 37 場的 TS .506 對雷霆 30 場 .593，整季等權平均把他拉低。lead 用 box score 粗估雷霆段每 36 約 66，非正式卡。
- R-030：小樣本往聯盟平均收縮是高估，目標要依人而定（Topić 往 40、受傷 Giannis 往 80）。MIN<100 那組每 36 中位 65.8，高於 MIN 100–1000 各組（約 62.5）。
- E-066（近期加權＋小樣本收縮目標，R-029、R-030）已跑完並經 role-audit 重算：兩題都不過，卡片維持 card 0.2.0（`reports/card-0.2.0+E066-recency-target/report.md`、`audit/audit.md`）。McCain／Topić 的問題仍未解；B 方向（往同 MPG 組拉）在屬性回測上變差，下一步要從卡片層或別的機制處理。教訓見 L-037。

## 2026-10-29 名單卡片影響力
- 使用者要求：卡片「前三強項＋弱項」改成影響力。`scripts/enrich_roster_viewer.py` 新增 `impactChips`：進攻／防守／淨影響＝2025-26 單季 box-prior RAPM（`reports/impact-rapm/rapm-prior.csv` lastSeasonO/D，每 100 回合），團隊在場＝`onoff.csv` 2025-26 在場淨效率（交易球員依 onPoss 加權，tooltip 附在場減不在場）。賽中頁也用 2025-26 值（2026-27 無 RAPM）。已發布（gh-pages 30942278）。
- 新增 deploy-shell：`python -I scripts/daily_inseason_update.py --shell`，只改頁面（UI／顯示）時用，沿用最後發布那天的 live 資料重建兩頁並發布，不抓資料、不跑 C4、版號與 dataSha256 不動。改公式會動到數字，仍走完整流程並改版號（G2）。網站顯示改動 push 後就跑它，不等每日排程。
- 2026-10-29 每日完整發布曾停擺：E-080 未 commit 的 `CURVE_DEF_RIM = RIMD_SCURVE ? [...] : [...]` 讓 `ovr_common.py` 解析失敗（L-048）。41cf2bd 讓解析器照 JS 規則讀旗標（關閉取後一組，與 HEAD 及 node 載入值逐位元相同），已發 inseason 0.2.1e（數據至 2026-10-28，gh-pages 52bd2eb），排程恢復正常。另：共用 checkout 時 commit 一律帶路徑（L-047；a8440d1 混入 card 0.2.4 的 memory 改動）。
- 2026-10-29 新增收工提醒 Stop hook（腳本已 commit；設定檔 `.claude/settings.local.json` 只在本機）：`.claude/hooks/handoff_reminder.py`，註冊在本機 `.claude/settings.local.json`（pythonw 絕對路徑，只在這台機器生效）。session 改了 memory/ 以外的 repo 檔、跑了 scripts／reports 腳本或派工，之後沒更新 handoff.md 時，在工作告一段落的回合（App 是有 wrap_up 的回合）提醒一次；同一份工作不重複提醒，派工子 session 不檢查。
- E-067 長人偏袒量尺凍結並跑基準線（2026-10-29）：卡片（fit 卡）沒有偏袒；模擬 WinImp 主版、位置版都偏袒長人（S +82～95／+38～50），位置版還低估 PG。下一步轉回模擬引擎，驗收照 E-067 §3（b1–b3）。
- 2026-10-29 模擬長人偏袒迴圈建立（`reports/sim-bias-loop/loop.md`，假設帳本 H1–H6，S 只當驗收不當調參目標，每輪加球隊層 RMSE 正則化）。E-076（H2 體格去重複，`reports/sim-0.1.0+E076-physique-dedup/`，預註冊 sha256 aa32e7dc…9308）H1（基準陣容定義）待使用者裁定，裁定前主版與位置版並列、兩版都要過。**E-076 完成（2026-10-29，lead 已核對 sha、g0、bias.json、team-check、npm exit 0）**：預註冊五個採用關卡 (g0)(g1)(b2)(b3)(t1) 全過 → 依預註冊規則是 `sim 0.1.1` 候選，**等使用者 G5 決定**。但要知道：(1) 引擎追蹤（F-034，`engine-trace.md`）發現 v53 活鏈裡協防 physique 加成、PHYS_REB_WEIGHT、PUTBACK 都是死碼，dedup 實際只關了 `reboundContest` 的 0.3×physique 一項；(2) S 只降約 10 點，遠小於區間寬度，主版仍「偏袒長人」，C 的高估被推到 PF／PG（F-035）；(3) 二波得分校準沒達 ±1.0（L-043，旋鈕衝突）。dedup-all（參考，多關 physEdge）主版 S 降到 +9.5／+21.8 不再偏袒，但這是看過結果的事後資訊，要當新假設得另寫預註冊且不能只在同一批 379 人＋同一份 RAPM 上驗（L-026）。H1（基準陣容定義）仍待使用者裁定。 **使用者 2026-10-29 裁定迴圈繼續（R-041）**：先量 physEdge → 再篩其他參數 → 最後才新增參數。E-085（`reports/sim-0.1.0+E085-physedge/preregistration.md`，sha256 8f707a79…b693）：第 1 步用逐對手 RA 命中率估對手體格斜率（控 help）定 r，主版 centered physEdge，判定用 2022-25 三季 RAPM 樣本外答案；E-086（`reports/sim-0.1.0+E086-param-screen/spec.md`）探針子集逐管道中和篩查，只排序不採用。**兩者已完成（2026-10-29 深夜，App 內 opus 子代理；lead 核對 sha、flags、g0、calibration、team-check、bias、bias-oos、npm log，report.md 由 lead 存檔 L-055）**：
  - E-085 **不採用**：β_phys +0.041 [−0.097, +0.181] 含 0 → r = 0，physEdge 等同全關（F-039，資料不支持這條管道）；樣本外主版 S 57.1→35.2 但位置版 22.3→28.6，o1 不過，b1 不過；指名長人幾乎沒動，長人高估主因不在 physEdge。
  - E-086 **分不出任何管道**：兩 seed 噪音底線 4.5 只有配對模擬雜訊 σ8 ≈ 17 的 1/4，所有管道 z < 1.2；ch3 拆半翻號、ch5 換基準消失、ch8 pos 方向反。
  - 新發現 F-040：E-067 的 S 區間沒算模擬 draws 雜訊（配對 σ ≈ 27–39）；E-065／E-076／E-085 的「S 顯著下降」都要重新解讀（L-054）。E-076 dedup 在 2022-25 樣本外答案上 S 57.1→49.0 [−0.3, 16.6]／22.3→9.8 [0.8, 23.9]，是它第一次的樣本外證據，但同樣在雜訊內。
  - 使用者 2026-10-29「先修」→ R-054，立案 E-099 修量尺（`reports/bias-check-E099-scale/`，預註冊 sha256 3986595c…2d8d）。**E-099 完成（2026-10-30，App 內 sonnet 子代理，lead 核對 g0-check、choice、run-meta、sha、scale.py 確實呼叫 E-067 原版 measure；report.md 由 lead 存檔）**：g0 逐位重現；雜訊選出 X（運氣修正後分差），σ16(ΔS) 39.2 → 19.4；(n1) 不過，要約 240 個樣本。舊區間窄 6 倍，勝負計分下配對差排除 0 的格 8/12 → 0/12（F-043）；位置版 S 在 X 下翻成負、主版仍明顯偏袒長人（F-044）。沒改任何版本的判定。
  - **E-102 完成（2026-10-30 11:20）**：(n1) 過（σ60(ΔS) 8.2 ≤ 10）；X 計分 dedup 比 legacy 少偏袒長人 17～20 名次，三組答案都排除 0；S 仍大、前 20 中鋒 10 vs 答案 4，頂端長人沒動（F-068）。報告 `reports/sim-0.1.0+E102-winimp-240/report.md`。**等使用者**：(a) E-076 G5 升不升 sim 0.1.1；(b) 量尺定為 X＋聯合區間＋60 樣本、b1 改寫；(c) 下一步找頂端長人高估管道，或先把 centered／dedup-all 補到 60。以下為執行紀錄：（原執行中，2026-10-30 01:05 起，5090）：使用者「加大樣本吧」→ 看過時間後選第三案：legacy 與 dedup 只跑 avg、樣本 16 → 60、nice 19、8 workers，判定 σ60 ≤ 10（預註冊 `reports/sim-0.1.0+E102-winimp-240/`，修訂 A sha256 41283531…8627）。g0 10/10 逐位一致（dedup 帶 orbLogitDelta −0.135）。5090 目錄 `/home/kojiek/side_projects/basketball-e102-20261030`，進度與 kill 方式見本機同目錄 `launch-notes.txt`。跑完：把 i=0..15 舊 checkpoint 與新 i=16..59 合併，照 E-099 scale.py 算 σ60、S、聯合區間，寫 report。
  - （以下為 E-102 立案前的待決，(1) 已由 E-102 取代）(1) 要不要在 5090 把四個版本的樣本加到 240（現 16；約 15 倍時間）；(2) 量尺基準是否改成 X 計分＋聯合區間，b1 停止條件怎麼改寫；(3) 位置版 S 翻號要不要查原因；(4) E-076 的 G5（升 sim 0.1.1 或不升）；(5) H1 基準陣容定義仍未裁定。R-041 第三步「新增參數」在量尺定案前先不動。
  - 5090 工作目錄 `/home/kojiek/side_projects/basketball-e085-20261029`、`…/basketball-e076-20261029`，沒有殘留程序。
- Hauser HDL 99：HDL 是 tovSkill（TOV/(FGA+.44FTA+AST+TOV)），在模擬裡是每次觸球的失誤率；v41 驗證中他的模擬 TOV/36 是 0.89，實際 0.65，模擬已經高估他的失誤，所以數值不用改。問題在顯示名稱「護球」，建議改名，待使用者決定。

- E-071 壓迫（2026-10-29，`reports/card-0.2.0+E071-pressure/`）：P1 過 G1–G4、audit 獨立重算逐位元相同（含勘誤 1：k=σ₁²/τ²，使用者核可，L-039）。只是不變差、不是變準；Diabaté PRES 99→61.4、OVR 84.2→79.2。已採用並併入 card 0.2.2（R-039）。（E-069 撞號已處理：fringe-repl 改為 E-072。）
- 2026-10-29 E-069 第一階段完成：handle（R-032）h1、h2、h3 都過，對 2K27 Ball Handle ρ 0.74。passSec 對 2K Pass Accuracy ρ −0.47（Luka 40、Hauser 99），只當模擬的傳球風險用。下一步：使用者看過名單後，派第二階段（模擬失誤拆分，m3 在 5090 跑）。
- 2026-10-29 E-072（原 E-069 fringe-repl，`reports/card-0.2.0+E069-fringe-repl/`）不通過：(c3) 18→16/19、(R1) Sandfort 59.6 > Sheppard 39.6、(R2) 邊緣池中位數 59.4 > 53.0。r_new −1.03 比舊 r_repl −2.01 高；模型本身把健康 DNP 的人估在池內約 PR27，收縮不是主因。下一步等使用者裁定：分鐘／DNP 當直接證據（含 R-035 年齡例外）需新預註冊。DeepSeek 餘額不足（auto-review 402）。
- 2026-10-29 E-073 預註冊凍結（`reports/card-0.2.0+E073-usage-evidence/`，sha256 db42fc16…，派工前加 (R4) 低分鐘組 PR90 < 高分鐘替補中位數後重凍）：用人（分鐘、出賽率、年齡、練兵隊）當能力證據的交叉擬合回歸；DNP 與輪休分開（R-036）。已派（App 內 sonnet 子代理，dispatch 路由 self：main 帳號 7 天 98%、worker 已 2 任務、DeepSeek 402）。lead 已核對：McCain 低分是 pred PR26＋MPG 17.3，RAPM 整季 +0.08、半季 −0.23／+0.14，雷霆段在場 +4.2 但在場減不在場 −7.7，E-073 預期只部分改善；季後賽分鐘沒進資料，要另開題。R-034 撞號已處理：分鐘正相關改為 R-035（L-038）。
- 2026-10-29 E-073 結果：不通過，只有 (R1) 沒過（Sandfort 54.4 > Sheppard 52.2；Drummond 57.3）。(c4) 過，代表用人資訊在樣本外確實有預測力。(R2)(R3)(R4) 都過。等使用者裁定；尚未經 role-audit。
- 2026-10-29 E-069 第二階段：m2 不過（tov36 MAE 0.167→0.320，低創造依賴組從低估翻成高估），模擬不變，src 已還原（patch 在 sim/）。m3 因 5090 VPN 斷線未完成，只當資訊。下一步若再試：失誤 hazard 不要直接乘持球秒數（例如改成每次觸球的基準機率加上 handle 調整），要寫新預註冊。
- 2026-10-29 E-069 m3 補完：主版更偏袒長人（S +106／+118），位置版翻成偏袒後衛（S −51／−38），兩版 ρ 都降。失誤拆分整體不採用。報告在 reports/handle-E069/sim/report.md。
- handle 線收尾（2026-10-29，R-046）：E-087 停在 p0（活鏈不呼叫 handlingWeights，L-046）；分球診斷 H8 排除；失誤已是實測兩段，handle 模擬端擱置，只留卡片屬性。未 commit。

## 2026-10-30 名單卡片近 5 場與貢獻值
- 手機版近 5 場：正負值格切 60° 缺角放正三角形 ▼，展開變金色不翻轉；表格只從數值格啟動內部捲動；平均列的投籃／三分／罰球顯示合計命中率。都已發布。
- E-105 單場貢獻值已上線：近 5 場表多「貢獻」欄（box score 換算每 36 分鐘淨影響，權重擬合 2025-26 RAPM A 半，B 半樣本外 r 0.44），數字寫絕對值，顏色和自己 2025-26 平均比、五色五等分（使用者 2026-10-30 裁定：同樣 +3 替補是進步、SGA 是退步）。切點＝2025-26 全部比賽差值絕對值的 20／60 百分位：單場 ±0.7／±2.4、近 5 場 ±0.3／±1.1（分布圖 `reports/game-contribution/gc-delta-dist.png`）；**顯示名稱改「評分」、0 起跳（R-062）**：評分＝0.75×(貢獻值＋7.5)，低於 0 記 0（單場約 1% 到 0、約 4% 超過 10，聯盟平均 ≈5.6；整季平均擠在 5.2–6.6，最高 SGA／Jokić 8.3）。表下只寫「N 場平均評分 X　上季 Y」，切點與換算 OVR 放 tooltip；2026 頁下拉改「整季細項」（場均／每 36、進球-出手、前後場籃板、犯規、整季評分），2027 頁仍是近 5 場；貢獻欄放勝負後面、分鐘移到最右。A+／99 存在 localStorage `bbac.mode`（兩個賽季頁共用）；手機寬度 A+／99 由 `season_nav.py` 搬到更新說明旁靠右。顏色是排名不是顯著。只顯示，不進 OVR。要重擬權重跑 `python -I scripts/fit_game_contribution.py`（`reports/game-contribution/`，要 `git add -f`）。 **E-110 通過、評分已換 M2（R-066，2026-10-30）**：box＋hustle＋防守對位，權重／2025-26 基準／五色切點（±0.8／±2.8、±0.4／±1.3）在 `reports/game-contribution/m2/`（`python -I scripts/fit_rating_m2.py` 重算，會核對和 E-110 M2 權重相同）；共用邏輯 `scripts/rating_m2.py`。每日發布先跑 `node scripts/fetch_matchups.mjs 2026-27`（失敗不擋發布），沒對位資料的場次評分用 M0、格子加 * 與 tooltip。M0 舊檔 `reports/game-contribution/weights.json` 保留當退回用。
