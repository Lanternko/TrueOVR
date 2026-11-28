# E-070 foulDraw 量化（report）

預註冊：`preregistration.md`（sha256 `c3fe3cd7a049a6a33fb9cb892e1ccf77e77eb6bafb1033e7e539e6f5cc04c817`，未改）。FD = 池內百分位(0.75·z(收縮後 FTA/36) + 0.25·z(收縮後 FTA/FGA))。池 = 252 人（GP>=30、MPG>=20、皆在 582 卡內）。

## 結論
c0-c3 全過。卡片端判定：**通過**，交使用者決定是否採用（不自動採用、未 commit、未動 memory/）。

| 關卡 | 內容 | 數值 | 結果 |
|---|---|---|---|
| c0 | w_vol=0 重現 card 0.2.0 | ranking.csv 逐位元相同 | 過 |
| c1 | npm test | exit 0，57 passed, 0 failed | 過 |
| c2 | RAPM 分半 ρ(候選)-ρ(card 0.2.0)，repl 每場 OVR | Δ=0.0007，90% CI [-0.0009, 0.0022]，下界 > -0.02 | 過 |
| c3 | evaluate.mjs 通過數 >= card 0.2.0 | 18/19 對 18/19 | 過 |

c2 細節（possScale 0.5 為主；人群 A→B 389 人、B→A 388 人、聯集 395；bootstrap 2000、seed 1、球員配對）：

| 變體 | Δ（兩方向平均） | 90% CI | A→B | B→A |
|---|---|---|---|---|
| repl（主） | 0.0007 | [-0.0009, 0.0022] | 0.0005 | 0.0009 |
| game | 0.0014 | [-0.0003, 0.0031] | 0.0033 | -0.0005 |
| 每 36 | 0.0006 | [-0.0012, 0.0024] | 0.0020 | -0.0008 |

敏感度 possScale 1.0（repl）：Δ=-0.0001，CI [-0.0017, 0.0015]，也過。差異全在 ±0.003 內，等同「不變差、也沒變好」。

c3 補充：未過的兩條（allFourStayTop10、strictFourBigsTop10）在兩張卡相同；ρ2K 0.6953→0.6987、ρRAPM（樣本內，僅參考，R-007）0.8139→0.8136、ρDef 0.5572→0.5551。

## 收縮檢查（2025-26，method (c) 的 FTA/36，k=8、λ=0.35、kh=4、位置先驗）
擬合季 2015-16..2024-25，訓練 n=3424。2025-26 預測下半季的 MAE（n=372）：收縮後 0.7507，k=0（不收縮）0.8286，只用上半季 0.8410。收縮比不收縮低 9.4%，比只用上半季低 10.7%，收縮有效。

## 只報告項目
### foulDraw 在 calibrate 的係數（每 10 點，per36）
| | 係數 | bootstrap SE |
|---|---|---|
| card 0.2.0 | 0.1083 | 0.0455 |
| E-070 | 0.1147 | 0.0500 |

係數幾乎沒動（+0.006，遠小於 SE）。

### 2K27 ρ（n=575）
| | 每場 | 每 36 |
|---|---|---|
| card 0.2.0 | 0.6953 | 0.5181 |
| E-070 | 0.6987 | 0.5203 |

### OVR 變動總覽
582 人平均絕對變動 0.18、最大 1.2、>1 分 2 人、>3 分 0 人；新舊 OVR 的 Spearman 0.9997。

### 前 20 名 OVR（舊→新）
| 名次 | 舊 | 新 |
|---|---|---|
| 1 | Shai Gilgeous-Alexander 112.8 | Shai Gilgeous-Alexander 112.6 |
| 2 | Nikola Jokić 108.4 | Nikola Jokić 108.6 |
| 3 | Luka Dončić 103.0 | Luka Dončić 103.1 |
| 4 | Derrick White 101.1 | Derrick White 101.3 |
| 5 | Kawhi Leonard 99.0 | Lauri Markkanen 99.0 |
| 6 | Lauri Markkanen 98.7 | Kawhi Leonard 98.9 |
| 7 | Kevin Durant 96.7 | Kevin Durant 96.8 |
| 8 | Franz Wagner 96.1 | Franz Wagner 96.2 |
| 9 | Victor Wembanyama 95.1 | Victor Wembanyama 95.2 |
| 10 | Giannis Antetokounmpo 95.1 | Giannis Antetokounmpo 95.0 |
| 11 | Evan Mobley 94.5 | Evan Mobley 94.6 |
| 12 | Donovan Mitchell 93.7 | Donovan Mitchell 93.7 |
| 13 | Chet Holmgren 93.0 | Chet Holmgren 93.0 |
| 14 | Jimmy Butler III 91.5 | Amen Thompson 91.6 |
| 15 | Amen Thompson 91.2 | Jimmy Butler III 91.6 |
| 16 | Joel Embiid 90.2 | Jamal Murray 90.2 |
| 17 | Jamal Murray 90.0 | Joel Embiid 90.1 |
| 18 | Herbert Jones 89.5 | Herbert Jones 89.4 |
| 19 | Cade Cunningham 88.3 | Cade Cunningham 88.8 |
| 20 | OG Anunoby 88.2 | Stephen Curry 88.4 |

前 20 名人選只差在第 20 名：舊 OG Anunoby 88.2、新 Stephen Curry 88.4。前十人選相同，只有 Kawhi／Markkanen 互換（5/6）。

### 變動最大的 15 人
| 球員 | 位 | MIN | FD 舊→新 | OVR 舊→新 | Δ | 名次 舊→新 |
|---|---|---|---|---|---|---|
| Shaedon Sharpe | SG | 1471 | 63.1→80.0 | 61.4→62.6 | +1.2 | 292→278 |
| Jalen Green | SF | 828 | 54.8→72.7 | 53.7→54.8 | +1.1 | 465→427 |
| Kevon Looney | C | 307 | 82.7→59.1 | 63.4→62.4 | -1.0 | 272→279 |
| Bez Mbeng | PG | 492 | 70.5→59.3 | 61.7→60.7 | -1.0 | 287→307 |
| Jericho Sims | C | 1318 | 84.3→56.6 | 49.7→48.8 | -0.9 | 538→545 |
| Malachi Smith | SF | 359 | 54.9→51.3 | 70.0→69.2 | -0.8 | 204→208 |
| Dominick Barlow | PF | 1689 | 84.7→67.4 | 67.6→66.8 | -0.8 | 232→243 |
| Brice Sensabaugh | SG | 1762 | 61.6→71.3 | 56.1→56.9 | +0.8 | 400→377 |
| Stephen Curry | PG | 1329 | 74.3→88.7 | 87.7→88.4 | +0.7 | 23→20 |
| Michael Porter Jr. | SF | 1689 | 62.8→79.0 | 82.6→83.3 | +0.7 | 52→50 |
| Adama Bal | PF | 241 | 62.7→57.6 | 69.7→69.0 | -0.7 | 206→212 |
| Jordan Poole | SG | 933 | 70.6→79.5 | 47.8→48.5 | +0.7 | 552→547 |
| Jeremiah Fears | PG | 2112 | 66.5→76.7 | 48.7→49.4 | +0.7 | 544→540 |
| Daeqwon Plowden | SF | 844 | 53.6→53.8 | 69.6→70.2 | +0.6 | 208→199 |
| Dylan Cardwell | C | 907 | 78.8→61.6 | 68.9→68.3 | -0.6 | 214→220 |

### foulDraw 前 20（582 卡，新）
（99.0 有多人並列，名次為排序順序，非嚴格）

| 名次 | 球員 | FD 新 | FD 舊 | 舊名次 | MIN |
|---|---|---|---|---|---|
| 1 | Giannis Antetokounmpo | 99.0 | 99.0 | 1 | 1039 |
| 2 | Joel Embiid | 99.0 | 97.6 | 13 | 1201 |
| 3 | Deni Avdija | 99.0 | 98.5 | 7 | 2199 |
| 4 | Luka Dončić | 98.8 | 95.2 | 30 | 2289 |
| 5 | Shai Gilgeous-Alexander | 98.5 | 96.4 | 21 | 2259 |
| 6 | Zion Williamson | 98.3 | 98.8 | 6 | 1841 |
| 7 | Jimmy Butler III | 98.1 | 99.0 | 2 | 1182 |
| 8 | Paolo Banchero | 97.8 | 97.8 | 11 | 2502 |
| 9 | Trae Young | 97.7 | 97.2 | 16 | 384 |
| 10 | Devin Booker | 97.6 | 95.0 | 32 | 2146 |
| 11 | Victor Wembanyama | 97.4 | 93.1 | 43 | 1866 |
| 12 | Jalen Duren | 97.1 | 98.1 | 10 | 1976 |
| 13 | James Harden | 96.9 | 96.7 | 20 | 2438 |
| 14 | Bennedict Mathurin | 96.7 | 97.1 | 18 | 1620 |
| 15 | Austin Reaves | 96.4 | 96.2 | 22 | 1762 |
| 16 | Nikola Jokić | 96.2 | 94.3 | 37 | 2265 |
| 17 | Brandon Williams | 96.0 | 95.7 | 26 | 1463 |
| 18 | Keyonte George | 95.7 | 94.1 | 38 | 1786 |
| 19 | Jaylen Brown | 95.5 | 87.5 | 91 | 2443 |
| 20 | Ja Morant | 95.4 | 90.2 | 66 | 568 |

### G5 抽查（13 人）
| 球員 | 位 | MIN | FD 舊→新 | FD 名次 舊→新 | OVR 舊→新 | OVR 名次 舊→新 |
|---|---|---|---|---|---|---|
| Shai Gilgeous-Alexander | PG | 2259 | 96.4→98.5 | 21→5 | 112.8→112.6 | 1→1 |
| Luka Dončić | PG | 2289 | 95.2→98.8 | 30→4 | 103.0→103.1 | 3→3 |
| Joel Embiid | C | 1201 | 97.6→99.0 | 13→2 | 90.2→90.1 | 16→17 |
| Giannis Antetokounmpo | PF | 1039 | 99.0→99.0 | 1→1 | 95.1→95.0 | 10→10 |
| Jalen Brunson | PG | 2590 | 78.1→89.1 | 179→52 | 82.1→82.4 | 57→54 |
| James Harden | PG | 2438 | 96.7→96.9 | 20→13 | 80.8→80.5 | 66→70 |
| Trae Young | PG | 384 | 97.2→97.7 | 16→9 | 67.5→67.4 | 234→235 |
| Jimmy Butler III | SF | 1182 | 99.0→98.1 | 2→7 | 91.5→91.6 | 14→15 |
| Rudy Gobert | C | 2380 | 99.0→91.3 | 3→40 | 86.6→86.7 | 27→27 |
| Steven Adams | C | 730 | 98.3→88.4 | 8→62 | 67.3→67.5 | 237→234 |
| Dwight Powell | C | 904 | 99.0→94.2 | 4→26 | 67.4→67.7 | 236→229 |
| Mason Plumlee | C | 171 | 99.0→88.8 | 5→59 | 56.3→56.4 | 390→389 |
| Alex Antetokounmpo | SF | 21 | 84.3→85.3 | 117→82 | 53.3→53.3 | 473→473 |

讀法：Luka（30→4）、SGA（21→5）、Embiid（13→2）、Brunson（179→52）的罰球製造升到應有位置；Gobert（3→40）、Adams（8→62）、Powell（4→26）、Plumlee（5→59）被拉下，仍在上段。OVR 影響都在 ±0.3 內，名次幾乎不動（Gobert 27→27、Luka 3→3）。原因是 foulDraw 在 calibrate 的係數小（約 0.11／10 點），FD 大改對 OVR 影響有限。

## 偏離預註冊
1. z 分數用 ddof=0（母體標準差），預註冊未寫明；池 = 252 人，皆在 582 卡內（attrs-check.json）。屬實作細節，在看任何結果前決定。
2. w_vol=0 的屬性檔保留 V61 原始 `new_foulDraw` 字串（重算會因讀 6 位小數的 CSV 差 4.98e-7，只影響捨入）；因此 c0 逐位元相同。w=0.75 版 FTA/FGA 項的 rate 同樣從 V61 CSV 的 6 位小數讀取。
3. c2 的答案與人群沿用 E-064 `evaluate_e064.py`（含 mpg-A/B 檔）；主指標取 repl 變體，因為 card 0.2.0 的每場 OVR 用 g_r。game／每 36 變體另列，結論相同。
4. 擬合半卡（fitA/fitB）用 possScale 0.5（與 E-064 輸出比對差 0.0）；possScale 1.0 只當敏感度。
5. `cards-w0/c0-switch-off` 是 `cards-w0/primary` 的重複跑（留存，不影響結果）。
6. `evaluate.mjs` 為 E060 版複本，只改 CANDIDATES 與輸出路徑；門檻與函式未改。
7. 沒有調過任何參數；未動 automations，故未跑 audit.ps1。

## 檔案
`e070_vol.py`、`run_cards.py`、`build_card.py`、`evaluate_e070.py`、`evaluate.mjs`、`report_items.py`、`make_report.py`；`vol-fit.json`、`attrs-check.json`、`c2.json`、`evaluation.json`、`report-items.json`、`verdict.json`、`inputs-sha256.json`、`npm-test.log`、`npm-test.exit`；`primary/ranking.csv`、`primary/summary.json`；`attributes-w0/`、`attributes-w075/`、`cards-w0/`、`cards-w075/`。
