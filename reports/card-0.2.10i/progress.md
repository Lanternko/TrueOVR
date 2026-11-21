# 0.2.10i 進度（每段一行；接手的人從最後一行往下做）
- 第 1 輪（前一位）：確認 2026-27 逐球有 descriptor（n 15416、driving 3137）；extract_j.py → work/history/crJ-{2022-23..2025-26}.csv.gz。
- 第 2 輪 #1：抽查 crJ-2025-26 用 J 類 pu 重算分子，對 E-190 creation-KP-KJ.csv raw_J×MIN/36，582 人 max|差| 1.7e-12（過）。
- 第 2 輪 #2：drive_pool_D.py：OLD 重算 2022-23～2024-25 池值逐人＝E-101 raw（max 0.0）、2025-26 池＝E-090 a0-raw pool（231 人，2e-15）；D 類 → work/pool-drive-D.json。
- 第 2 輪 #3：live/split_dc.py（SPLIT_DC 開關）＋window8／window10 接上；make_tail_0210i.py c0（SPLIT_DC=0）drive |差| 0、creation repr 全同；real 寫 card-0.2.10i/tail-U.csv（creation 對 E-190 KJ 相關 0.953、drive 對 drive_D_U 0.9993）。
- 第 2 輪 #4：卡片端 A（build.py cards/run）→B（run_i.py）→C（build_0210i.py）完成；c0（舊 tail）ranking.csv＝card-0.2.10g 逐位元、錨點同；real ranking sha 8b3e99d6…，card-0.2.10i/ 已寫 cards/K6、summary。
- #5 賽中端（2026-11-01 23:5x）：run_c4_live.py SPLIT_DC 開關＋split_creation（新秀 creationJ）、window10 crJ、pres_drive D 類；先驗 build_prior_0210i、用人層 build_usage_0210i；舊檔進 _retired/（含 rookie-prior-2026-0210h.json 供 SPLIT_DC=0）；build_2k_start 重解 δ；c0 ranking sha ba5f884b… 與 HEAD 程式逐位元組相同；check_inseason_0210i.py 全過（前 100 名移動 ≥10 名 7 人）；npm test 全過（logs/npm-test.log）。下一步：網站 season_nav／build_card_viewer、發布。
- #6 發布（2026-11-01 23:55）：commit d8ac494 已 push（claude/project-thread-63h2fz）；gh-pages 3a13238「inseason 0.2.10i 數據至 2026-10-31」，線上首頁與 2025-26.html 已見新 DRV／CRT 說明與更新說明條目。頁面建構時 season_nav.py 暫換成 commit 版（不帶別的 session 未 commit 的 ATTR_TIPS 改寫），建完已還原。完成。
