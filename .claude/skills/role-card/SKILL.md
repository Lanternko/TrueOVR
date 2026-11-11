---
name: role-card
description: basketball-autochess 卡片：卡片 OVR、賽中 OVR、RAPM 校準、預註冊回測。派工 task 指定 role-card 時用。
---

# 卡片與賽中 OVR（role-card）

## 開工
讀 `memory/handoff.md`、`digest.md`（先跑 `python memory/build_digest.py`；lessons／rulings 摘要；R-001–R-007 是球員評價與驗收裁定，細節 grep `rulings.md`）；正式卡見 R-012，賽中 OVR 見 E-033、R-008。

## 負責
- 有預註冊就照凍結內容做：不改門檻、不換參數；發現預註冊有錯先停下，寫 errata 給使用者核可。
- 參數只在開發季選；驗收用沒看過的季或 RAPM 分半（G4、L-026）。讀 RAPM 的 align／封頂／混合目標，ρRAPM 只算樣本內（R-007、L-022）。
- 資料來源先核對 sha256 與筆數，不同來源不得混用（L-018、F-021）。
- OVR 不設範圍（R-005）；個別球員 2K27 或 RAPM 其一對得上即過（R-003）；檢查前十長人（R-002）；吃餅用固定先驗折扣（R-001、L-023）。

## 指令
```bash
python reports/status/status_snapshot.py
```
賽中 OVR 工具在 `reports/ovr-inseason-2026-27/v5/tools/`（例如 `backtest_pathA.py`、`c4_v5.py`），判定與預註冊在 `v5/pathA/`。

## 不准
- 不改已凍結的預註冊與正式卡；新版本另開資料夾。
- 不重跑 C4R、不提議下載 NocturneBear box，除非使用者重開（R-008）。
- 不自己把 E 狀態改成採用。

## 交付
- 回報依 R-004：中位誤差、差 >10 分人數、80% 區間命中、球員抽查表；ρ／MAE 放附錄。
- 卡片或模擬板有變：照 L-021 重跑 `status_snapshot.py`。
- 對應 E 條目填「結果」；新事實追加 F；handoff 寫明產出路徑。
- 新賽季反事實與版本差異只用 `live/run_c4_live_rookie.py`（`run_c4_live.py` 不能直接跑）；換版時更新 `live/CURRENT.json`、舊版建構腳本與凍結檔 `git mv` 到 `live/_retired/`，`npm test` 的 `test/live_current_gate.py` 會擋漏改（R-107）。
