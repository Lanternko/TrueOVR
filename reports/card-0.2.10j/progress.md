- #1 卡片端（2026-11-02）：build_0210j.py：GRAVITY=0 → work/C-c0 ranking＝card-0.2.10i 逐位元（8b3e99d6…）；預設 → 本目錄 ranking.csv sha 4519d615…＝E-198 KG-final 逐位元；cards/K6、usage-features、gravity-raw/attr 已複製（沿用 E-198 產物，只重做 OVR 映射段）。
2. 2026-11-02 賽中 0.2.10i 參考夾 live/_cmp0210j-ref（HEAD 版 run_c4_live／rookie＋_retired 0210i 先驗暫放頂層，跑完還原）：版號 inseason 0.2.10i
3. 2026-11-02 GRAVITY=0 賽中 c0（live/_cmp0210j-c0）ranking.csv 與 0.2.10i 參考夾逐位元組相同；新版首跑 OK（gravity 欄進 ranking；權重 25-26 0.43／26-27 0.50，本季檔 288 人，OLS n=324）；build_2k_start 重解 δ（L-109）→ rookie-prior-2026.json
4. 2026-11-02 check_inseason_0210j.py 全部通過（c0 逐位元、先驗、(a)、R-109：卡片頁前 100 移動≥10 名 11 人、新賽季頁 10 人，前 20 各進出 1 人 → 字母版 0.2.10j）；log reports/card-0.2.10j/logs/check_0210j.log
5. 2026-11-02 網站：season_nav（GRV 取代切入位置、ATTR_TIPS、gravity_tip、OD_OFF＋gravity、OD_CARD→0.2.10j、更新說明一行）、build_card_viewer／build_inseason_viewer（GRV 欄＋提示卡、src 說明）；daily 加 step_fetch_gravity；CURRENT.json／README 換 0.2.10j；memory E-200（E-199 已被速度問題卡佔用）＋handoff
6. 2026-11-02 npm test 全過（52 passed、timed game、live_current_gate OK、rookie_start_gate OK）；log logs/npm-test.log
- 11-02 02:07 步驟7：選擇性 stage（season_nav／experiments 用 HEAD＋自己改動的 blob），commit
- 11-02 02:19 步驟8：commit b8b002f push；daily --force 發布（本季引力 288 人），gh-pages 95c1444，線上兩頁 GRV 與更新說明確認
