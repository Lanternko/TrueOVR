# E-187 phase 0（核對與檢定力）

- 預註冊 sha256：`preregistration.md` 8878c622…b24e 相符；`errata-1.md`（commit 7baba3f，R-119，KJ 結果產出前）79d7ee92…a1d9 相符（`results.json` 的 `prereg_sha256_ok`）。
- K6 沿用 E-186 的重現卡（歷史三原點 `reports/card-0.2.10+E186-t6-rapm-target/work/K6-<季>`，2025-26 為 `reports/card-0.2.10/ranking.csv`，sha 84e9590b…e6c1 重核相符）。
- 只讀 K6 算出 h：`e187_eval.py phase0` -> `phase0.json`。
  - h_C = 0.04468（與 E-186 phase0 同；−2h_C = −0.08936）。C 三季合併 K6 = 0.7070；n = 271／303／346。
  - h_R = 0.05963（K6 下季 RAPM ρ 三季合併 0.3988 的球員層 bootstrap 90% 半寬；seed 20261101、2000 次，跨季共用球員重抽，同 C）；−2h_R = −0.11925。n_rapm = 262／286／319。
- 實作：KJ／KA 的 pass 共用斜率＝E-180 臂 A 原樣（`calibrate_wing_t.py --dropInteract pass`，用 `reports/E180-pass-pool-creation-interact/calibrate_wing_t.py`，與 E-164 版只差這個旗標）；其餘流程同 E-186（`--dropAttr physique`、`--dropAttr stamina`、Y0 用人層連續 d、全部係數重擬合）；2025-26 用 0.2.10 的 `tail-U.csv`。

## 揭露（偏離與意外）
1. **順序**：八張卡（含 KJ）在 phase0 數字算出**之前**就建好（建卡與 phase0 同在背景批次後）；phase0 程式只開 K6 欄位，h 不受 KJ 影響。
2. **T6 目標檔被別的 session 重產**：`reports/E142-card-target/phase1-work/cands/T6-*.pkl` 在 17:20 被 L-102／F-128 的工作重產（補回 Jokić、Wembanyama；舊檔備份在 `cands/pre-L102/`）。KJ 用 E-186 的 T6R 檔（17:13，重產前），**不受影響**；KA 第一次建卡（17:25）讀到新 T6，已丟掉重建，改讀 `pre-L102/T6-*.pkl`（與 E-186 的 K6 同目標）。errata 的 K6 基準 −1.04 用 `pre-L102` 重現為 −1.0438，所以 a1 的分段殘差用 `pre-L102`；新 T6 的數字另列（`T6new`，只報告）。
3. **errata-1 在我開工後才 commit**（17:24）；`final` 第一次跑時還是用原預註冊的 a1（≥16），之後改成 errata 版本。只改判定式，沒有改任何卡、臂或 h。
4. `npm test`：node 測試 52 passed；整體 exit 1，是 `test/live_current_gate.py` 兩項失敗（live 程式被另一個 session 未 commit 改成 0.2.12，`CURRENT.json` 還是 0.2.10），與本資料夾無關。
