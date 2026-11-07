2026-11-02 開工：工作樹 live/、season_nav 無他人改動；E-207 疊 0.2.12b(W246)→0.2.12c
- 2026-11-02 tov_live.py 觸球版（TOV_TOUCH、window_tch、freeze_touch）完成；tov-pool-card0212c.json 凍結，重現 KC tovSkill max|diff| 2e-8；fetch_possessions NEED 加 TOUCHES
- 2026-11-02 tov_live.CARD→card-0.2.12c-w328；build_0212c.py 建 328 底，ranking 與 KC final 逐位元組相同；window8 加 _tc
- 2026-11-02 run_c4_live.py 語法修好（CRLF 檔，ATTR_NOTE 0.2.12c 段）
- 2026-11-02 run_c4_live_rookie.py ROOKIE_JSON 加 TOV_TOUCH 分支；舊 rookie-prior 備份 _retired/rookie-prior-2026-0212b.json
- 2026-11-02 c0 卡片端：TOV_TOUCH=0 WIN_LEN=246 card_route_0212c→make_card 的 ranking.csv 與 card-0.2.12b 逐位元組相同
- 2026-11-02 reports/card-0.2.12c/ 以 w328 檔播種；make_card_0212c.py 改 SRC=card-0.2.12b、錨點取 w328；開跑 WIN_LEN=246 TOV_TOUCH=1 card_route → work/on246
- 2026-11-02 card-0.2.12c/ 建成（W246，sha 7083ced9…）；live 端 c0：TOV_TOUCH=0 ranking.csv 與 HEAD 碼同資料逐位元組相同（參考夾 live_ref 為暫時副本，之後刪）
- 2026-11-02 站台：season_nav／build_card_viewer／fetch_possessions 改完、npm test 過、daily --dry-run 兩頁建成（TO 提示含每百次觸球失誤）；準備 commit＋發布
2026-11-02 開工 E-207 W246 重擬合（派工）：新資料夾 reports/card-0.2.12c-fit246/，先做 tov-raw 的 W246 版並用 328 重現 KC 驗證方法
2026-11-02 tov_raw246.py 完成：FIT_WIN=328 重現 KC（見數字）；FIT_WIN=246 產 tov-raw-W246/tail-W246
2026-11-02 W246 輸入備齊：usage-window-c82-246、defL-246（primary/fitA/fitB 奇偶分半）、attrs-246、tov-raw-W246；各自 FIT_WIN=328 皆逐位元重現舊檔（tov-raw-KC、usage-window-c82、stage1 c0 def-L 三檔、tail-KC 屬性）
2026-11-02 整條擬合鏈（tail／usage／def-L／calibrate／pipe／finalize）以 FIT_WIN=328 重現 E-206 KC final 逐位元組：見下一行；W246 鏈已跑完（work/W246/final）
- 2026-11-02 card-0.2.12c-w246 底資料夾建好（final ranking 與 fit246 W246 final 逐位元相同）；下一步：tov_live 凍結 W246 池、repoint run_c4_live／make_card_0212c
2026-11-02 老 0.2.12c(328 擬合)的 ranking/summary/凍結池/先驗/usage 備份在 card-0.2.12c-fit246/old328fit/；tov_live、run_c4_live、build_prior/usage、make_card_0212c 已改指 W246 底
2026-11-02 tov-pool-card0212c.json 以 W246 重凍（window 246）；重現 W246 tovSkill max|diff| 1.4e-8
2026-11-02 prior-2025-26-card0212c／usage-2025-26-card0212c 以 W246 底重建（582 人 OVR 對得上、L/a 對 usage-window-c82-246 逐位相同）；開跑卡片端 card_route → work/on246fit
2026-11-02 card_route→make_card 重建 reports/card-0.2.12c/（W246 底）
2026-11-02 開跑 build_2k_start.py（L-109，新秀起點依 W246 底重建）；c0 TOV_TOUCH=0 卡片端 card_route → work/c0fit
2026-11-02 c0（卡片端）：TOV_TOUCH=0 WIN_LEN=246 重跑 → make_card ranking.csv 與 card-0.2.12b 逐位元組相同
- 2026-11-02 build_2k_start.py (L-109) 重跑完成；live 側 TOV_TOUCH=1/0 與 0.2.12b 參照（HEAD 程式）三組跑中（data/_inseason_build/fit246_*）
- 2026-11-02 live 側檢查：c0 逐位元組同 0.2.12b、f=0 檢查過、npm test 52/0 過；卡片頁前100名移動>=10名 9 人、新賽季頁 16 人（<=25，不升 PATCH）；跑 TOV_POSS=0 對 HEAD 程式比對
- 2026-11-02 TOV_POSS=0 對 HEAD 程式：預設窗口 246 的 ranking.csv 逐位元組相同（7d6c3091）；WIN_LEN=328 兩邊不同（25b2b45f vs c90c1b7c，defenseBonus／ovr 等 163 人不同），HEAD 與新程式同走 TOV_POSS=0 路徑、此差異非本次改動引入，未追（依派工：照實記錄不硬修）；絕對『重現 0.2.11』未驗（無 0.2.11 ranking 參照）
