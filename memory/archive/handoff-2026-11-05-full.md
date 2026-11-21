# 交接（handoff）

只記「目前狀態」，每次收工整份覆寫，不往下追加日期段。每條最多兩行，細節寫進 findings／experiments／rulings 或報告檔，這裡只放 ID 與路徑。UI 小改不進本檔（看 git log）。舊版全文在 `archive/`（最近一份 `handoff-2026-11-01-full.md`）。
**多個 session 同時改本檔與工作樹**：覆寫前先重讀一次，只改自己負責的條目。

- **更新**：2026-11-05 球員卡加追蹤量格子（R-166，未 commit／發布）；2026-11-04 E-239 追蹤全套完成；2026-11-04 預註冊自行定驗收標準並直接凍結開跑，跑完再回報達標與低於預期處（R-165 併入 R-011）；同日新秀起點加季前賽位移（R-162）＋復出老將補卡（R-161）一起發布，線上版號 inseason 0.2.12d（gh-pages c6c7803，數據至 11-02）；2026-11-03，球隊評分對手改 E-224 梯度隊（R-158，7bfd941，gh-pages 11-03 22:02 已上線）；同日賽中 OVR 近期加成 b3h20 上線（R-150，E-221／E-222，d4a43fc，gh-pages 46e288f）；同日回報格式拿掉五級文字標籤（R-148 併入 R-011）

## 目前基準（線上）
- **inseason 0.2.12e**（11-04 發布 gh-pages 09f38ad、已 commit）：0.2.12d 復出老將補卡（R-161，6 人）＋新秀起點加季前賽位移（R-162）＋防守 D 個人場次軸（R-163）＋復出老將補進用人層 hi（R-164）。未修：復出老將基準 gravity＝70 佔位（L-127）。回退 `DEF_AXIS=calendar`、`RV_USAGE=0`、`RETURNING_VETS=0`、`PS_START=0`。
- **佔位座標近框修正已上線**（F-157／L-128，11-04）：`window8._zone` 佔位座標歸 short，線上 2026-27 已重建（0.2.12e，gh-pages 88e72f0）；INS 提示卡新增「本季近框／低位／籃下／上籃／灌籃／補籃」列（`attr_cell_tips.season_near_rim`，只在 2026-27 賽季頁）；提示卡加寬到 330px、數值不換行。未 commit。
- **賽中近期加成 b=3、h=20**（R-150，11-03 上線）：本季逐場權重加重近期場次，最後 20% 季淡出、季末不變；`RECENT_BOOST=0` 回舊版。單場評分－上季平均 vs 當場 ΔOVR 相關 0.28→0.43、大場當場上漲 67%→79%（量法 scratch，未進報告）。`live/recent_boost.py`
- **card／inseason 0.2.12**（R-139，E-203，11-02 上線，gh-pages 7fc64c4）：tovSkill 改看持球時間（0.5·z(−每持球分鐘失誤)＋0.5·z(持球分鐘/36)），其餘不動；每日抓 `possessions.json`；`TOV_POSS=0` 重現 0.2.11。正式卡 `reports/card-0.2.12-tov/`。
- **card／inseason 0.2.11**（原 0.2.10j，R-137；R-134／R-135，E-200）：加能力值引力 gravity（主畫面 GRV 取代切入位置，每日抓本季引力），`GRAVITY=0` 重現 0.2.10i。`reports/card-0.2.10j/`、`live/gravity_live.py`
- **網站**：首頁 2026-27、`2025-26.html`（`build_card_viewer.py`、`enrich_roster_viewer.py`、共用 `season_nav.py`）。能力值說明文字在 `season_nav.py` 的 `ATTR_TIPS`，改屬性公式要一起改；新格子提示用 `sn.cell_tip()`。只改 UI 用 `python -I scripts/daily_inseason_update.py --shell` 立刻發布；每日排程 14:30／16:30＋22:30 補對位（registry `basketball-inseason-daily`）。
  - **網址（11-04）**：網站是 trueovr.com；排行／賽程用乾淨路徑 `/rank/`、`/rank/LAL/`、`/games/[日期/[場次/]]`，球隊只存 localStorage 不進網址。發布時 `add_spa_pages` 複製 `rank/`、`games/` 的 index.html，404.html 暫存深路徑再還原（`site_header.py` 早期腳本）。資源一律根路徑。
- **模擬 sim 0.1.3**（R-120，2026-11-01：0.1.2 的防守者投籃犯規 β×2、c −0.05625、pace ×0.998125，`benchmark.mjs` options()；0.1.2 以前的 WinImp 數字不能直接比，G3）；防守 `nba-defense-v3`（R-010）；賽中 OVR C4（E-033）、顯示值 B0。

## 進行中
- **E-239 進攻追蹤全套多季**（11-04 完成，3/5，未稽核）：單一特徵無穩健訊號，71 全放 ridge 留一季增益 +0.095（可能混 2024-25 定義斷層）；穩定「量」類 42 個可當卡片格子，效率類是雜訊。①卡片加追蹤量格子**使用者 11-05 核可已做**（R-166：量類加進 DRV／INS／CRT／PASS／3PT 提示卡，未 commit、未發布；2026-27 頁是 11-05 手動快照，`node scripts/fetch_tracking_cells.mjs <季> data/tracking-cells/<季>` 重抓後重建）；待使用者決定：②另開預註冊測定義一致子集進 OVR／Transformer ③要不要每日抓追蹤（要補 registry／audit）；並派 role-audit。`reports/E239-tracking-full/report.md`、F-160
- **E-238 無球追蹤特徵**（11-04 完成，未稽核）：接球／拔起／快出手占比補不進 OVR（H3 不過），判只當個案顯示；Luka 接球量中後段、拔起第 1。球員卡追蹤格已加（見 E-239、R-166）；待派 role-audit。`reports/E238-offball-tracking/report.md`、F-158
- **E-230 新秀起點用 SL／PS 記錄**（11-04 完成，未 commit、未稽核）：預註冊三條成立但改善 0.36 < 0.5 →「有訊號但太小」，訊號只來自季前賽，實驗結論＝順位曲線維持；但使用者 11-04 核可後 PS 位移已套用線上（R-162，見上「目前基準」）。待使用者決定要不要另開逐項起點實驗，並派 role-audit。`reports/E230-sl-preseason-rookie-start/report.md`
- **陣容 Transformer**：E-227 已採用；**R-160 球隊評分已換 T**（2026-11-04 上線，舊引擎備援＋每日另存 `team-ratings-m0.json`）；E-229 前向記錄只當附加。
- **E-234 能力值→OVR Transformer**（11-04 完成，未稽核）：三季 v4 卡訓練、預測 2026-27，名單 `reports/E234-attr-to-ovr-transformer/predict-2026-27.csv` 交使用者人工檢查；留一季沒贏 ridge，有定義漂移。E-232（OVR 當陣容預測器）使用者改要求後擱置，草稿仍在 `reports/E232-ovr-as-lineup-predictor/`。
- **E-236 能力值＋RAPM→OVR Transformer**（11-04 完成，未稽核）：加 RAPM 輸入留一季 RMSE 5.8→4.4／3.9／4.7，但主要是學回公式，2026-27 對網站卡仍差 7.4；名單 `reports/E235-attr-rapm-to-ovr/predict-2026-27-A.csv`（資料夾為工作名）。原始表已查：箱score＋PBP 投籃 2021-22～2025-26 對卡 playerId 100%／PBP 出手數吻合，步驟 C 可做；onBall／help／pressure 無原始表。使用者選步驟 C 原始＋防守三項混合 → **E-237 完成（11-04，1/5 不採用，未稽核）**：原始輸入 RMSE 5.16 比能力值 4.39 差，加 MIN／GP 也無增益（F-159）；名單 `reports/E237-raw-inputs-to-ovr/predict-2026-27-E237.csv` 待使用者人工檢查，可派 role-audit 重算 R0／R1。
- **E-222 診斷**（R-149 已被 R-150 推翻，保留作事後檢查）：MDE_p 0.030，每日更新在 30 隊滿 20 場時跑 `reports/E222-recent-boost-diagnostic/e222_eval.py` 一次；errata-1（c→g 改 15·c）未核可。剩餘落差：OVR 結構不看重部分高評分表現（Murray 16.9 分場 +0.2）
- **聯盟 3PAr 偏差**（11-03）：預註冊 1 來源不明；預註冊 2（E-219）位置池對手 K=0.62 部分原因；預註冊 3（E-220，F-148，R-146）3 分 logit 位移 δ*=0.27／0.10 補齊 3PAr 無副作用，但節奏只補 5–8%，同源不成立。使用者 11-03 裁定 δ 暫不進引擎；節奏偏慢下一步（查回合組成：失誤率、罰球率）未開。`reports/3par-logit-shift/report.md`；E-219 報告尚未稽核
- **E-208／E-213 球隊評分**（11-02）：`teams.html` 上線；傷病 ESPN→官方PDF（E-214）；缺陣球員補底卡 E-216。`reports/E208-team-rating/report-missing-profiles.md`
- **0.2.10 待辦**（R-114）：獨立 role-audit 沒做（F-116：組合值評 foulDraw／pass 不過，使用者知情上線）；換季跳動對 0.2.9a 沒量；Porter Jr. 20→40；G5。
- **E-151 年輕側年齡連續**：已預註冊（6820474），每日排程在 2026-27 stints 達 450 場時自動跑 `e151_eval.py` 一次（daily.log 會出現 WARNING「E-151 評估完成」）。不得提前拿卡片去比。

## 等使用者裁定
- **E-196／R-133 得分產量**（11-01 完成，未上線）：產量取代 creation 樣本外無球組低估 5.2→4.5，但係數全靠下限撐；待選。`reports/card-0.2.10g+E196-production/report.md`
- **網站品牌名**（11-01）：傾向 Pure.OVR（pureovr.com 可註冊），備選 hoopgrade、ovihoops；未買、社群帳號未查。`reports/site-naming/domains.md`
- **0.2.10a 後續**（R-121）：新賽季頁仍是舊 T6，等 0.2.12（以 0.2.10a 為底）一起修；H1 封頂壓前段（SGA 118.8→103.8）另議；E-142／E-153／E-186 用舊 T6 要重核。
- **R-117 停損**：JW、長人犯規兩條線只做診斷，不提新假設，除非使用者重開額度；全文見 rulings。
- **JW 偏高 F-125 已修（R-122，2026-11-01）**：正式卡改 **card 0.2.10c**＝0.2.10a 修正後 T6 重擬合＋傳球全位置共用斜率（E-187 KAU）；JW 第 9→12（MIN≥500）、分段殘差 −1.50→−1.22。新賽季頁仍 0.2.10 係數；**0.2.12 若要帶上本修正要改以 0.2.10c 為底**。2026-27 季末用本季 RAPM 做樣本外複查。`reports/card-0.2.10c/report.md`
- **ΔOVR 基準（R-112，2026-11-01）**：老將 lastOVR＝今天的模型但本季 0 場（窗口 cur=False、防守 D 逐人 leave-one-out、posMeanD 用賽中版），0 場的人 ΔOVR 全部 0；JW +2.34→+0.35。已發布。
- **E-162／F-106 產量評價**：卡相對 T6 不低估高用球者，只是相對薪水低估；選項：接受 T6、提高市場權重（另寫預註冊）、先放著。`reports/card-0.2.9+E162-per-volume/report.md`
- **賽中新秀 d 對不上**（R-097、F-090）：季末連續 d 和卡的二元 d 在 MEM／DAL／NOP／CHI／MIL 對不上。選項：卡也改連續 d，或拉長 R-092 回歸窗口。上季爛隊的年輕人開季普遍 +17～23，使用者說「晚點再改」。
- **E-139 開季先驗權重** 判「沒有改善」（F-087），線上維持 B0，下一步未定；卡片換版讓年輕球員單日跳 ±10–17，換版平滑還沒開實驗。
- **正負值沾光**（大勝時投不好的人評分偏高）：E-148 不過（F-092），下一步未定。
- E-132 errata（階段 B 2027-02 回來算）；E-134 階段 1 已完成；E-130 結案與否（worktree `D:/Projects/CODING/ba-e130`）；E-100 第二階段；E-114 草稿待核可；E-122 D1 未表態。
- 小項：TO 刪或改持球分母（R-032）、INS 拆分、foulDraw／drive／onBall 改原始值（F-046）、補籃另開能力值（R-056）、防守四項權重（R-053）、Hauser「護球」改名。

## 待辦（非決策）
- Edwards 卡 #38，但 DARKO #9／2K 95，開季 4 場 +16 而賽中 OVR 不升，待查。Podziemski 賽中 #20（卡 #41，約 +3 分來自 ≤23 歲加分）。
- 卡對 RAPM ρ 0.78→0.70（0.2.8 起）；2026-27 季後做真正的樣本外複查。
- sim 得分偏高 119.1 對 115.5（TODO）。E-090 狀態欄要改成被 E-101 取代。
- 等季末：E-083 跨季 RAPM d=0.75、E-127 換隊隔年變好、E-141 新秀曲線的前瞻檢查（2026-12-31）。

## 工作樹注意
- 共用 checkout：memory 條目檔、`scripts/season_nav.py`、`build_card_viewer.py`、`build_inseason_viewer.py` 常混有別的 session 的改動，只挑自己的段落 commit。`reports/` 被 gitignore，要 `git add -f`。
- 2026-11-01 時 memory 條目檔有大約 1,400 行沒 commit（多個 session 寫入），下次 commit memory 前先 `git diff` 確認。
- DeepSeek 餘額不足（402），auto_review 失效。

## 開放問題
- 長人偏袒量尺（E-102）：E-076 G5 升不升版、量尺與 b1 停止條件、H1 基準陣容。OVR 量「比平均球員」（R-103），籃板不算偏差。
- 卡片 OVR 要不要接進對局（F-010）；體力與換人線擱置（R-068）；Stewart help 99（E-080）。
