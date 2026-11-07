# E-111 報告（role-card 子 session 回報，lead 存檔）

# 總評
**1/5 失敗**（前置 (L1) 不過，照預註冊停下；回測 (1)(2) 沒跑、沒看）

**這次目標**
新賽季頁從 inseason 0.2.5a 換成跟上 card 0.2.7（CARD_MODE=027），先過六道前置再跑回測。

**進步了什麼**
- (z) 0 人不符（E-107 時 1 人）；(s) stamina 不換尺後 9 項全過。
- (L1) 582 人裡 581 人和 card 0.2.7 差 ≤ 0.053；錨點、r_repl 差 0；UL 防守加成 582 人全對上。
- (c0) 025 逐位元不變；(c1) npm test 57/57。

**退步了什麼**
- (L1) Toumani Camara 開季 OVR 82.72 vs 卡 82.9，差 −0.180 > 0.1。
- 原因：H1 封頂用 RAPM pooledNet 名次；Camara 與 Sam Hauser 同分 3.501。卡片產生器（calibrate-wing.py attach_external_ranks）照 rapm.csv 列序（Camara 51、Hauser 52），賽中 OVRPipeline 照 playerId（相反），Camara 被封在第 52 名的值（pred 1.4678 vs 卡 1.4944）。同分名次差 1 的共 7 人，只有 Camara 卡在封頂上。寫成 L-067。

**直觀證據**
| 球員 | 卡 0.2.7 | 賽中 N=0 | 差 | RAPM 名次（賽中／卡） |
|---|---|---|---|---|
| Toumani Camara | 82.9 | 82.72 | −0.18 | 52／51 |
| 次差 Jaylen Clark | 62.4 | 62.45 | +0.05 | — |

**要你決定的事**
1. （建議）027 分支的 RAPM 名次改照產生器規則（同分照 rapm.csv 列序），025 不動，重凍結後再跑。
2. 放寬 (L1)：事後改門檻，不建議。
3. 暫停，維持 0.2.5a。

---
## 細節
- 前置數值：`prereq.json`；(s) 中位差見 `s-worker-025.json`／`s-worker-027.json`；L1 診斷 `s-worker-027.json` 的 `L1diag`。
- 偏差 D1–D12：`deviations.json`。D12：唯讀快照中 live/2026-10-28 的 card-roster-viewer.html、roster-viewer.html、publish_state.json 被另一個 session 的每日更新改過（05:25），與本實驗無關。
- run_c4_live.py sha256 → 02d135dd11af46574013e8be48b94c55583bb0cda64119e4c9f4b565e30478c7（只加 027 分支）。
- 新檔：live/build_prior_027.py、prior-2025-26-card027.json、build_usage_027.py、usage-2025-26-card027.json、pool-027.json；本目錄 build_pool_027.py、check_prereq.py、zones-027.json、out-025-pre／、out-025／、out-027／、logs／。
- 可疑處：同分排序問題在 025 線上版也存在（同一個 OVRPipeline），只是沒有逐人比對關卡沒被抓到。
