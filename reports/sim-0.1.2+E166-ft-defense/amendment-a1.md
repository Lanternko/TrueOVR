# E-166 修正 A1（2026-11-01，凍結後、任何結果產出前）

1. §0 實作：不改 `src/`，在 harness 把 β 表每個值乘 k 後傳給 `defenderFoulBeta`。犯規式 fb＝Σβ，乘 k 和 fb×k 數學上相同。基底＝5090 `~/e140` 快照（E-140 harness，β 開、c、pace 乘數由 harness 給），k=1、c=−0.03125、pace=0.99875 就是 sim 0.1.2（E-140 已驗證和預設路徑逐場相同）。
2. j1、j2 的「答案名次」：照 F-103 的 `od_split.py` 原算法，即 2022-25 RAPM（pooledO＋pooledD）換成模擬上場分鐘的每場值，不是每 100 回合的 pooledNet。j2 的 Spearman 也對這個值。人群＝WinImp checkpoint 中 2022-25 合併 ≥5000 回合者（F-103 為 276 人）。
3. 校正用 poss-sim 改用 E-140 的 `engine-e140.mjs`、`rr-core.mjs` loadX／opponentTeam（和 E-140 rr 同一套），其餘照 §1。
4. c／pace 重解的目標檔＝E-140 `cal-c-0.031250-p0.998750.jsonl`（0.1.2 在校正 seed 20261100–115 的聯盟值）；起點 c=−0.03125、pace=0.99875，程序、容差同 E-140 cal-run。
