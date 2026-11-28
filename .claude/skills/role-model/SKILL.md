---
name: role-model
description: basketball-autochess 模擬引擎：改 src/ 的機率模型、防守、球權、輪替並跑模擬量測。派工 task 指定 role-model 時用。
---

# 模擬引擎（role-model）

## 開工
讀 `memory/handoff.md`、`digest.md`（先跑 `python memory/build_digest.py`；lessons／rulings 摘要；L-001–L-012 是引擎坑，細節 grep `lessons.md`）、spec 指定的 E 條目；防守相關先讀 R-010、F-017。

## 負責
- 只改 spec 列出的檔案；新行為預設關閉，用版本旗標切換，舊版本保持凍結可重現。
- 量測：同版本、同人群、同 seed 才比（G3）；至少 8 個 seed，平均與差值用群集標準誤或 team＋seed 聯合重抽（L-024）。
- 每份輸出記錄 sim 版本、seed、資料 sha256（G2）。
- 重度模擬（多 seed 全季、掃描）在 5090 跑，本機只跑 `npm test` 與小量測。

## 指令
```bash
npm test
npm run test:defense
npm run simulate:season
```
各防守批次有自己的 `npm run ability:<批次>:*` 與 `npm run test:ability-<批次>`（見 `package.json`）。

## 不准
- 不改已凍結的版本或能力卡（例如 `nba-defense-v3`、第八批 v5 凍結檔）。
- 不在已看過答案的季上挑參數再稱盲測（L-026）。
- 不自己把 E 狀態改成採用；採用是主管的決定。

## 交付
- `npm test` 通過（G1）的輸出。
- 報告寫在 `reports/<資料夾>/`，開頭先給直觀結論與數字。
- 對應 E 條目填「結果」；新事實追加 F；handoff 寫明產出路徑。
