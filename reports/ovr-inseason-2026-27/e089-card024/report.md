# E-091（spec 資料夾 e089-card024）：賽中 OVR 改用 card 0.2.4（inseason 0.2.2）

執行：sonnet 子代理（role-card），2026-10-29。lead 審查與發布：同日。spec：`spec.md`。比對輸出：`compare.md`、`compare.json`、`out-022/`、`out-024/`。

## 結果（直觀）
- 前 20 名：進 Dylan Harper（85.7→90.5），出 Markkanen（88.1→90.3，#21）。
- ΔOVR（368 人）：|Δ| 中位數 2.80、最大 15.8；>5 分 67 人、>10 分 15 人；有號中位數 +1.10。
- 最大的變動幾乎全來自用人項（年輕球員的 y、y·L、y·d·L 項）：Banchero 59.8→75.6、Sheppard 53.0→66.7；Keyonte George 64.6→49.0、Jaylen Wells 70.7→55.7、Alex Sarr 69.7→55.3、Kyshawn George 75.1→60.9、Flagg 78.0→64.6、Coward 75.1→61.9、Dëmin 68.4→55.5、Ace Bailey 61.0→48.1。這些都是 card 0.2.4 正式卡本身的判斷（lastOVR 對正式卡最大差 0.1）。
- 年齡：≤23（98 人）中位數 +1.10、≥31（54 人）−0.60、中間 +1.60。
- MPG0 口徑（mpgAvail 對舊 MIN／GP）差 >3 的 81 人（卡內 205），最大 Plowden 26.4 對 10.6、DeAndre Jordan 16.6 對 2.5。R-042 已列的 mpg-A／B 問題，只報告。

## 驗收
| 項 | 結果 | 證據 |
|---|---|---|
| c0 CARD_MODE=022 重現 0.2.1e | 過 | ranking.csv 188c8bed…、no-prior.csv e061bff3… 與 live/2026-10-28 相同（lead 自算 sha256 相符） |
| c1 npm test | 過 | 57 passed（子代理與 lead 各跑一次） |
| c2 N=0 對 card 0.2.4 | 過 | 368 人有限；t1 0.0444；Spearman 0.999994；最大差 0.10（lead 自算 0.100） |
| c3 版號／頁面 | 版號過；字面字串不過 | probe_base_version＝inseason 0.2.2；season_nav 重寫來源文字，頁面顯示「版本 0.2.2a」「先驗 正式卡 0.2.4」（線上確認）。驗收寫法問題，L-050 |
| c4 凍結特徵重現 card 0.2.4 | 過 | 582 人 ovr／mpg／gRepl 逐格相同，r_repl 與錨點差 0.0（csv ovr 只有一位小數，未捨入差最大 0.04998） |

## 參數（全部取自 E-084，未擬合）
- 係數 coefficients.card：b0 −1.209302、b1_p 0.539534、b2_L 0.349699、b3_a 0.458909、b4_y 0.442726、b5_v 0.435908、b6_yL −0.030267、b7_vL −0.209532、b8_ydL −0.481471。
- r_repl −1.759309 → −1.272449；錨點 PR1／PR50／PR99 −0.7564／1.0495／4.7440 → −0.5415／0.8849／3.1778。
- has=False 0 人；MPG0 368 人全由 card 0.2.4 mpg 欄配對。

## 檔案
- 改：`live/run_c4_live.py`（CARD_MODE=024 預設）、`live/README.md`、`scripts/build_inseason_viewer.py`；lead 另改 `scripts/season_nav.py`（更新說明加新賽季 0.2.2）。
- 新：`live/build_usage_024.py`（sha256 f2c366d4…）、`live/usage-2025-26-card024.json`（sha256 833738e5…，payloadSha256 9c6b0c3e…）。
- out-024/ranking.csv sha256 0cd17341…。

## 發布
- 完整發布 inseason 0.2.2a（數據至 2026-10-28，gh-pages b39f4a3）；更新說明補一格後 --shell 重發（a9681d6）。
- 重抓後同截止日的 player-games sha256 為 31170cdc…（E-091 驗收用 606333d0…），原因未查。
