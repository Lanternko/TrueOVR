# E-128 errata-1：補齊 §1.2 pass 的規格

狀態：已核可凍結（2026-10-30，使用者「核可並續跑」）。核可後凍結，sha256 存在 `errata-1.sha256`。原預註冊（sha256 5536050e…2aa47）不改。

## 起因

role-card 開工核對時發現 §1.2 沒寫清楚 4 件事：

- 賽中視窗要不要做 E-055 收縮，要的話歷史用哪三季；
- 位置先驗用哪一季、哪一種位置；
- zs 凍結常數用收縮後的值還是原始值；
- 合併池和歷史答案卡的 pass 要回溯到哪一季。

role-card 照 §4 停下，沒有寫任何程式，也沒有看任何結果。

## 補法：完全照現行 foulDraw 的先例

依據是 `live/build_prior_026.py` 的 `foulDrawFreeze` 和 `run_c4_live.m26_foul_comp`。這次沒有新增任何自由選項。

1. **賽中視窗不做 E-055 收縮。**
   - 用原始值：`y_vol = AST/MIN·36`、`y_rate = AST/astCh`。`y_rate` 就是現行 `pb['pass']` 的 AST%。
   - 往 x0 收縮的工作由 C4 的 wt 負責，所有屬性都是這樣處理。foulDraw 的 vol 項本來就不收縮。
   - 所以賽中不需要歷史季，也不需要位置先驗。
2. **zs 凍結常數。**
   - 內容：mean 和 std（ddof=0），用卡片端 2025-26 的**收縮後**值計算。
   - 範圍：就是 `reports/card-0.2.7+E125-pass-volume/work/a0_p.py` 算 card pass 時的 zs 池，條件是 GP ≥ 30、MPG ≥ 20、在卡片名單內。
   - 這和 foulDrawFreeze「z 的 mean/std＝2025-26 池拉回後值」同一作法。
   - 寫進 `prior-2025-26-card027b.json` 的 `passFreeze`，欄位比照 `foulDrawFreeze`：wVol 0.5、wRate 0.5、vol mean/std、rate mean/std、pool、poolSize。
   - 檢查：用凍結常數套卡片端的收縮值，再經 pool-027b 的映射換算，要重現 card 0.2.7b 的 pass，每人差 ≤ 0.05。這項併入 (L1)。
3. **合併池 pool-027b 的 pass 欄。**
   - 每季照 E-125 建四季池的方式：`work/pool_data_p.py` 的 `v61_season(s, method='c')`。
   - 歷史用 engine `E.SEASONS` 裡最多前 3 季（`MAX_HIST=3`），有幾季算幾季。位置用 `E.pos_lookup(pos_by, p, s)`，位置先驗用該季自己的池，zs 也用該季自己的。
   - 不往 2019-20 以前補資料。
   - 檢查：併入 (u)。pool-027b 的 pass 欄要和 E-125 算 card 0.2.7a／0.2.7b 時用的合併池逐值相同，容許差 1e-9。
4. **回測的歷史答案卡和先驗卡。**
   - 該季的 pass 照第 3 點，用 `v61_season(s, 'c')` 算，再用各季自己的 zs 和合併池映射。
   - 不另外補歷史。
   - 某季缺 v61 資料時，照 E-111 對 drive 的作法沿用舊定義，並寫進 deviations。

## 不變

判定門檻、關卡清單、§3 只報告項、§4 不准，全部不變。
