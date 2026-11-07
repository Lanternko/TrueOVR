# scripts/archive

2026-10-30 工作區整理搬進來的，原文不改。**不要從這裡執行**：路徑相對 `scripts/`，搬回去才能跑。

| 子目錄 | 內容 | 為什麼搬 |
|---|---|---|
| `generated/` | 66 個點字首腳本（`.seventh-*`、`.eighth-*`）。是 `build_defense_seventh_base.js`、`run_defense_eighth_c_versions.js`、`run_defense_eighth_b_point.js`、`campaign_defense_eighth_a_controls.js`、`build_defense_eighth_v5_cards.js`、`prepare_defense_seventh_season.js`、`build_inseason_stints.js` 執行時寫出的暫時補丁副本，各報告的 provenance／manifest 記了它們的 sha256。 | 重跑產生器就會重產；`.gitignore` 現在擋 `scripts/.*`，新產生的不再進 git。 |
| `retired/` | 21 個 2026-10-16 之後沒再改、只有 `reports/` 內舊報告提到、程式與文件都沒引用的腳本（defense-third／seventh／ninth 時期的 diagnose、campaign、freeze、reproduce 等）。 | 讓 `scripts/` 只剩還在用的。要重現舊報告時搬回 `scripts/` 再跑。 |

沒搬的：`fetch_old_seasons_v5*.py`、`build_historical_stints.py`、`historical_rapm_windows.py`（2026-10-28，E-132 自製先驗 RAPM 在用）、`headshot_eyeline.py`（2026-10-30 剛加）。
