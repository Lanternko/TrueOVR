# E-135 預註冊：包夾威脅拿掉體格項，頂端長人還會不會被高估

- 日期：2026-10-30。角色：lead 擬稿；使用者 2026-10-30「核可」後凍結，執行者照做。
- 起因：E-102（F-068）60 樣本 X 計分下，dedup 修到中段長人，頂端（Gobert、Duren、Queta、Clingan、M. Robinson、Barnes）沒動。使用者 2026-10-30 選「找頂端長人被高估的原因」。
- 基準：sim 0.1.0 legacy（E-076 dedup 暫不升，見 handoff）。

## 0. 已揭露（L-026）
- lead 看過 E-086 ch1（doubleThreat 體格權重 0）在 100 人 × 8 樣本的結果：avg ΔS −3.70，z 0.22，分不出來。
- 假設來自 `profile.py`／`profile.txt`：把 E-102 dedup 的 X 殘差（AB、OOS 兩組答案）對 v41 2025-26 同季重現的逐人誤差做 Spearman。這是看過答案後找方向，**不算證據**；本實驗不選參數，ch1 是固定移除（權重 0，其餘重新正規化，同 E-086 hooks），沒有可調係數（L-023 吃餅類用固定先驗）。

## 1. 假設
體格高的護框長人 `doubleThreat` 被體格項（0.25）推高。他在場時，`teammateContext.dblPeer` 與 `gravityScore` 取到他，所有隊友被包夾的機率下降、命中率上升；這份隊友紅利算在他的 WinImp 裡。

同季診斷（不算證據）：
| 組 | 隊友在場 FG% 模擬 − 真實（pp） |
|---|---|
| 後衛 141 人 | +0.70 |
| 前鋒 122 人 | +0.56 |
| 中鋒 64 人 | +1.36 |
| Gobert／Duren／Queta／Clingan／Robinson | +1.24／+1.63／+0.72／+1.87／+2.40 |
| Jokić／Embiid／Wembanyama | +0.41／−2.84／−1.73 |

中鋒內部，這項誤差越大殘差越大（ρ +0.39 AB、+0.47 OOS）。自己的得分、出手、罰球、usage 都對得上（v41 驗證表），所以不是分球問題（E-087 H8 已排除）。

## 2. 設計
- 改動：只有 ch1，`doubleThreat` 的 score 改為 (0.20·long + 0.10·mid + 0.45·short)/0.75；它同時影響 dblPeer、gravityScore、`measured_creation_context` 的 sourceDouble。不改 `src/`：沿用 E-086 `e086-hooks.mjs` 的 ch1 字串替換，套在 E-102 legacy runner 上，放本目錄 `winimp-core-135.mjs`。
- 人群、對手、seed、分鐘、輪替全同 E-102；樣本 i = 0..59（60 個，與 E-102 merged-legacy 同 (opp, i) 格）。對照組直接用 E-102 `merged-legacy.jsonl`，不重跑。
- 跑在 5090，workers 12，nice 19；預估約 5–6 小時。

## 3. 判定（凍結後不改）
| 條件 | 內容 |
|---|---|
| (g0) | 開關關閉時，id 最小 10 人 i = 0..15 的 draws 與 E-102 merged-legacy 逐位相同。不過就停。 |
| (g1) | `npm test` 全過（只驗 src 沒被動到）。 |
| (m1) 可觀測量 | 先跑：v41 2025-26 同季重現 3 seed，ch1 開／關。中鋒組「隊友在場 FG% 誤差」減後衛組的差距要縮小（報數字）；球隊每場得分 RMSE 不得比關閉差超過 0.2 分。m1 不過就停，不跑全量。 |
| (b1) 主判定 | X 計分，OOS 答案：ΔS（legacy − ch1）聯合 90% 區間（B 2000、rng 1、1800 格，E-099 做法）下界 > 0。 |
| (b2) | AB、BA 同樣的 ΔS 只報告。 |
| (b3) | OOS ρ 不比 legacy 低超過 0.02（點估計）。 |
| (r1) 只報告 | 六人（Gobert、Duren、Queta、Clingan、M. Robinson、Barnes）名次變化；前 20 名中鋒數；被低估的 3D 側翼（H. Jones、Dort）名次。 |

b1、b3 都過才算「這條管道確實推高長人」，進 G5；不自動升版。

## 4. 產出
本目錄：`winimp-core-135.mjs`、`g0-check.json`、`m1-season.json`、`checkpoint-ch1-60.jsonl`、`scale135.py`（import E-099 scale.py，不改它）、`rescore135.json`、`run-meta.json`（src tree、資料 sha256、預註冊 sha256）、報告（六段）。

## 5. 不准
- 改 `src/`、E-065／E-076／E-085／E-086／E-099／E-102 目錄內任何檔案。
- 看過 b1 後換權重、換答案、換樣本數。
- 把 AB／BA 的結果當證據（樣本內，R-007）。
