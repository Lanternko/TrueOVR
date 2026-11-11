# E-074 報告：賽中 OVR 改用 card 0.2.2 當先驗（inseason 0.2.1）

2026-10-29，role-card。換版不是新模型：不擬合任何新參數，沒看 2026-27 結果調設定（L-026）。資料＝live 最新已發佈快照（player-games sha256 912c955a…，cutoff 2026-10-27，55 份 PBP）。
輸出：`out-020/`（CARD_MODE=020）、`out-022/`（CARD_MODE=022，含 roster-viewer.html）；比對 `analyze.py` → `compare.md`、`compare.json`。

## 直觀數字（R-004）
1. **前 20 名**：進 Tyrese Maxey（88.4，原 #24 86.9）、Jayson Tatum（88.2，原 #26 86.3）；出 Lauri Markkanen（原 90.8，現 #21 88.1）、Anthony Davis（原 87.9，現 #22 87.8）。
2. **OVR 變動**（362 人，0.2.0c → 0.2.1）：|Δ| 中位數 1.20、最大 8.5。最大 10 人幾乎都是 pressure（舊＝壓命中率，新＝逼失誤）造成：Sheppard +8.5（pressure 40.5→97.1）、Banchero −8.1（62.1→40.5）、Nembhard −8.0（90.5→46.3）、Maluach −7.9（93.7→44.0）、Queen +7.1（48.5→92.0）、Allen +6.4、Slawson +6.4、Mobley −6.3（88.7→49.0）、Fears +6.1、Dieng −6.1（94.2→44.5）。完整表見 `compare.md`。
3. **foulDraw 新舊公式**（視窗觀測值 y，達最小樣本 FGA≥50 的 42 人；|新−舊| 中位數 4.8）：差最大 5 人都是「罰球次數多、FTA/FGA 普通」的高出手量球員——Edwards（FTA/36 5.33、FTA/FGA 0.192）55.4→84.8、Miller（5.50、0.217）60.2→85.7、SGA（4.73、0.200）56.6→79.2、Porter Jr.（4.22、0.221）61.0→77.3、George（4.29、0.227）62.2→78.2。

## 驗收
| 項 | 結果 |
|---|---|
| c0 | `CARD_MODE=020`：ranking.csv sha256 7e6f1a53…a8be、no-prior.csv af9c9224…，與已發佈 `live/2026-10-27/` 兩檔逐位元相同；meta.json 僅差 version／baseVersion／dataSha256（發布流程補的鍵）與新增 cardMode |
| c1 | `npm test` 57 passed, 0 failed |
| c2 | lastOVR（N=0 先驗）對 card 0.2.2 每場 OVR：Spearman 0.99999（362 人，同名配對）；OVR 全有限；人數 362／55 無先驗，與 0.2.0c 相同；f=0 檢查最大差 0.043（<0.5）；lastOVR vs 正式卡最大差 0.1 |
| c3 | `probe_base_version()` → `inseason 0.2.1`；out-022/roster-viewer.html：`'PRES', '壓迫'` 1 處、「壓命中率」0 處、tooltip「逼失誤 ${p.force}｜犯規紀律 ${p.foulDisc}（2025-26）」在字串與數值模式格子都有 |

## 附錄
- summary 鍵：card 0.1.2 版與 card 0.2.2 P1 版 summary.json 展平後鍵集合相同；pergame-summary.json 鍵相同。r_repl＝−1.759309（約 −1.7593 ✓）；錨點 PR1/PR50/PR99＝−0.7564/1.0495/4.7440。
- foulDraw 凍結常數（`prior-2025-26-card022.json` 的 `foulDrawFreeze`）：池＝2025-26 GP≥30、MPG≥20 且在卡內，252 人；拉回後 FTA/36 mean 3.749332 std 1.972271；拉回後 FTA/FGA mean 0.263929 std 0.105734（ddof=0）；百分位對照池內 252 個合成值。用這組常數重算 582 人 foulDraw：對 E-070 new_foulDraw 最大差 5e-7，對 card 0.2.2 ranking.csv（1 位小數）最大差 0.05。權重 0.75／0.25。
- 實作取捨（假設）：z 常數取「拉回後」的卡片值（與 card 0.2.2 的 foulDraw 同尺度），賽中視窗是未拉回的原始比率，因此 y 比較極端；之後由 C4 的 k／δ²／rel（沿用 drive，未重估）收縮。小樣本時 y 對 x0 的拉力因此比舊公式略大，但被同一組 k 壓住。
- 舊公式的 y 是 FTA/FGA 對 2025-26 原始比率池的百分位（`rec['drive']`）。
- 凍結屬性不變：pressure、drive、physique、onBall、help、heightInches。frozen pressure 的值＝card 0.2.2 force。
- 頁面：PRES 格顯示 presDisplay（2025-26），tooltip 附（2025-26）；來源文字改 card 0.2.2。
- 檔案 sha256：prior-2025-26-card022.json 0518184f…0463；out-022/ranking.csv 2d57ff7d…56b3；run_c4_live.py 7ce2b897…07add；build_prior_022.py 7155551d…c1d；build_inseason_viewer.py 73d3ae25…009fc。
