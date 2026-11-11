# inseason 0.2.9 2026-27 即時結果（資料截至 2026-10-30）

- OVR：賽中 C4（inseason 0.2.9），先驗 card 0.2.9（live/prior-2025-26-card027b.json）；N = 該球員 2026-27 已打場數。
- 資料：2026-10-20..2026-10-30、81 場、80 份 PBP；缺 PBP：0022600101。
- git HEAD：`8147f57ee98b`；c=1.0（凍結）、G=82、f = min(N/82, 1)。
- 排名 442 人（有先驗卡且已出賽，加上在現役名單上但還沒出賽的 68 人，N=0、OVR＝先驗）；沒有先驗卡 58 人（`no-prior.csv`，不給 OVR）；有先驗卡、沒出賽也不在現役名單 140 人（不列入）。
- N 分布：N=0: 68 人, N=1: 23 人, N=2: 45 人, N=3: 27 人, N=4: 58 人, N=5: 130 人, N=6: 91 人。
- 3PT 欄 = threeValue（R-024，顯示用、不進 OVR）：vol＝合併（2025-26＋2026-27）3PA/MIN×36；acc＝(k·上季 abilityC＋本季 3PM)/(k＋本季 3PA)，k=294.667（本季沒有出手難度資料，用原始命中）；rep＝合併聯盟 3P%（0.3588）−0.03；value＝vol×(acc−rep)，在合併 MIN≥500 且有先驗卡的 327 人池內取百分位並套 attr()。`long` 欄仍在 ranking.csv 並進 OVR 計算，只是表格不顯示。
- E-128（CARD_MODE=027b，預設）：先驗 x0＝card 0.2.7b 產生器的未四捨五入能力值（尾巴原樣、不夾 99）；屬性迴歸＝rebase-027a e123a primary 的 summary.json；賽中觀測值對 live/pool-027b.json 的合併池映射（pass 換 E-125 量×率合成值＋合併池，視窗不收縮、z 常數凍結自 2025-26 卡片端；其餘 8 欄同 pool-027），99 以上與 40 以下照 E-101 尾巴；help 照 E-123 D1 尾巴（不夾 99）；drive、onBall、pressure、presDisplay、physique、heightInches 凍結；防守加成＝UL 值（同 027）。
- 降級的資料層見 `../README.md`。`simulatedPer36` 空白（此流程不跑模擬）。
- `lastOVR` = 同一逐點管線對先驗卡算出的 OVR（ΔOVR 的基準）；`formalOVR` = card 0.2.9 `ranking.csv` 同名球員的 OVR（只供對照）。
- OVR 為每場（R-028，E-064 副版）：g = (預測每 36 分鐘淨值 − r_repl)·MPG_hat/36，r_repl＝-1.0296（替補水準 PR10），兩段映射錨點 PR1/PR50/PR99＝-0.5300/0.9668/3.9710（card 0.2.9 summary.json 同組）。MPG_hat = MPG0 + w·(本季場均分鐘 − MPG0)，w＝stamina 的 C4 w（stamina 最小樣本 1 場）；沒有本季視窗紀錄的 208 人（含沒出賽者，不在排名內）退回 MPG0。`ovrPer36` 是同一預測的每 36 分鐘 OVR。
- card 0.2.4 用人層（E-091，R-044 = 用人回歸＋當季 RAPM 目標）：p＝上面屬性迴歸的每 36 預測（`predictedPer36`，C4 照常更新），predNew＝b0 + b1·p + b2·L + b3·a + b4·y + b5·v + b6·y·L + b7·v·L + b8·y·d·L（`predNew` 欄）；L、a、y、v、d 與 has 旗標凍結在 2025-26 全季（`usage-2025-26-card029.json`，payload sha256 ec903c76809e…，年齡不加一歲），has=False 或不在卡內者 predNew＝p；係數 b0=-0.1401、b1=0.6233（E-084 results.json）。MPG0＝card 0.2.4 ranking.csv 的 mpg 欄（mpgAvail，依名字配對），卡裡沒有的人退回 MIN／GP。
- E-095（CARD_MODE=025）：分鐘權重 mpg/36 改為飽和 W(mpg)=(1−e^(−mpg/15))/(1−e^(−36/15))（card 0.2.5，R-047），錨點／r_repl 取 E-089 results.json report_only.card.new。
- E-128：用人層係數、r_repl、錨點取 reports/ovr-inseason-2026-27/live/usage-2025-26-card029.json（rebase-027a e123a pipeline 重跑，錨點對 rebase-027a/work/cards-result.json 核對）；分鐘權重 W 同 card 0.2.5。

## 檢查 (a)：f=0、k 取上界 → 與上季卡一致（c4_v5 T1 同款）

| 項目 | 結果 |
|---|---|
| 逐球員 \|OVR 差\| 最大值（門檻 <0.5） | 0.045107 → 通過 |
| 本檔 live_predict 與 c4_v5.c4_predict（f=0, k 上界）屬性最大差 | 0.000e+00 |
| 本檔 live_predict（f=0, c=1）與 fit_w_grid_v4.c2_predict 屬性最大差（T2 同款，門檻 1e-9） | 2.842e-14 |
| 逐點管線 A 參考與原管線差（建構時檢查，門檻 1e-8） | 1.03e-11 |
| 重建的 2025-26 映射 vs 上季卡 long／ft 最大差（只由 box 決定，應接近 0） | 19.863 ／ 22.555 |
| lastOVR vs 正式卡 OVR（同名 442 人）最大差 | 0.09999999999999432 |

## 檢查 (b)：ΔOVR = 賽中 OVR − lastOVR

- 人數 442；\|ΔOVR\| 中位數 1.109、平均 1.724、最大 11.257。
- \|ΔOVR\| >= 1.0 的人：230 人：Shai Gilgeous-Alexander（N=5，-3.37）、Victor Wembanyama（N=5，+1.16）、Kawhi Leonard（N=2，-1.48）、Jayson Tatum（N=5，+2.11）、Nikola Jokić（N=5，-4.18）、Ty Jerome（N=5，+4.99）、Jalen Williams（N=3，+1.89）、Jamal Murray（N=5，-1.01）、Stephen Curry（N=5，-1.18）、Franz Wagner（N=5，+2.38）、Paul George（N=5，+1.23）、Joel Embiid（N=5，-1.25）、Paul Reed（N=6，+7.50）、Matisse Thybulle（N=6，+3.65）、Jaylen Brown（N=5，-1.99）、Michael Porter Jr.（N=5，-4.91）、Brandin Podziemski（N=4，+2.09）、Kevin Durant（N=6，-4.26）、Derrick White（N=5，-1.11）、Jaden McDaniels（N=6，+2.64）、Jalen Brunson（N=6，-1.83）、De'Aaron Fox（N=5，-1.57）、Cooper Flagg（N=5，+2.12）、Zion Williamson（N=5，-1.33）、Trae Young（N=6，+6.40）、Lauri Markkanen（N=4，-1.12）、Dejounte Murray（N=4，+2.65）、Desmond Bane（N=5，-1.06）、Onyeka Okongwu（N=6，-1.42）、Trey Murphy III（N=5，-3.47）、Payton Pritchard（N=5，-2.87）、Walker Kessler（N=6，-1.52）、Collin Gillespie（N=4，-2.17）、Dylan Harper（N=5，+6.04）、Moussa Diabaté（N=6，+1.27）、Neemias Queta（N=5，-1.51）、Jaylin Williams（N=5，-1.16）、Mikal Bridges（N=6，-4.97）、Ryan Rollins（N=5，-3.19）、Isaiah Joe（N=3，-2.54）、Josh Hart（N=6，-2.80）、Pelle Larsson（N=6，+1.30）、Luke Kornet（N=5，-2.56）、Domantas Sabonis（N=5，+2.23）、Tre Jones（N=6，-4.63）、RJ Barrett（N=5，+1.44）、Jalen Smith（N=6，+2.05）、Ayo Dosunmu（N=6，-1.30）、Jaxson Hayes（N=4，+4.24）、Cason Wallace（N=3，-2.04）、Daniel Gafford（N=6，+1.15）、Grayson Allen（N=6，-2.56）、Cameron Johnson（N=2，-2.99）、Davion Mitchell（N=6，+2.21）、Nickeil Alexander-Walker（N=6，-1.54）、Keon Ellis（N=5，+3.03）、Kyshawn George（N=6，+1.95）、Jalen Duren（N=2，-3.71）、Sam Merrill（N=5，-1.49）、Myles Turner（N=5，-1.11）、VJ Edgecombe（N=5，-1.11）、Devin Vassell（N=5，+1.13）、Ja'Kobe Walter（N=5，+3.99）、Ivica Zubac（N=3，-4.02）、LaMelo Ball（N=6，-2.38）、Jabari Smith Jr.（N=6，+1.37）、Aaron Wiggins（N=6，+4.83）、Duncan Robinson（N=6，+1.75）、Clint Capela（N=5，+1.57）、Gary Payton II（N=6，-1.56）、Miles McBride（N=6，-3.07）、Ronald Holland II（N=6，-1.50）、Dru Smith（N=4，-2.26）、Jakob Poeltl（N=5，-3.50）、Collin Sexton（N=5，-2.87）、Cam Spencer（N=5，-2.60）、DeMar DeRozan（N=5，-5.13）、Kevin Huerter（N=6，-1.33）、Herbert Jones（N=5，-1.13）、Isaiah Jackson（N=5，+2.37）、Saddiq Bey（N=5，-4.24）、James Harden（N=5，-1.86）、Precious Achiuwa（N=5，+6.09）、Marvin Bagley III（N=5，-2.19）、Zach Edey（N=4，-2.40）、Al Horford（N=5，-1.23）、Collin Murray-Boyles（N=5，-1.45）、Terrence Shannon Jr（N=6，+8.76）、Keldon Johnson（N=5，-1.21）、Gui Santos（N=5，+1.01）、Kelly Oubre Jr.（N=6，-3.90）、Josh Giddey（N=6，-4.11）、Jose Alvarado（N=2，-1.17）、Anthony Black（N=3，-1.19）、Luka Garza（N=5，-2.55）、Sam Hauser（N=5，-1.94）、Scotty Pippen Jr.（N=5，-1.17）、Ziaire Williams（N=4，+5.63）、De'Anthony Melton（N=6，-1.56）、Kel'el Ware（N=5，-2.18）、Tristan da Silva（N=5，+1.70）、Aaron Nesmith（N=5，-3.85）、Jay Huff（N=5，-2.23）、Luke Kennard（N=3，-2.52）、Quentin Grimes（N=6，-3.44）、Moritz Wagner（N=5，+3.89）、Hugo González（N=5，-1.08）、Jock Landale（N=6，-2.71）、Kris Murray（N=2，-3.84）、Bobby Portis Jr.（N=6，-3.41）、John Collins（N=6，-2.61）、Andrew Wiggins（N=6，-6.66）、Terance Mann（N=1，-3.39）、Daniss Jenkins（N=6，+7.03）、Donovan Clingan（N=4，-3.07）、Caleb Martin（N=2，+2.17）、Quenton Jackson（N=6，+1.48）、Marcus Smart（N=3，-1.15）、Ace Bailey（N=5，+2.53）、Alex Sarr（N=6，-3.71）、Zaccharie Risacher（N=6，+5.47）、Bones Hyland（N=6，-2.21）、Zach Collins（N=4，-5.91）、Tyler Kolek（N=4，+2.90）、Ryan Dunn（N=4，-2.02）、Jaylen Wells（N=5，+1.11）、Reed Sheppard（N=4，-3.43）、Micah Potter（N=2，-2.48）、AJ Green（N=5，-3.77）、Steven Adams（N=1，-3.43）、Jonathan Kuminga（N=6，+2.77）、Josh Minott（N=4，-2.63）、Jamaree Bouyea（N=2，-4.01）、Kasparas Jakučionis（N=5，+3.29）、Sidy Cissoko（N=4，+2.82）、Jaylon Tyson（N=5，-4.15）、Egor Dëmin（N=4，-2.90）、Peyton Watson（N=5，-1.35）、Joan Beringer（N=6，+7.45）、Jared McCain（N=5，+2.35）、Noa Essengue（N=5，+11.26）、Tyrese Proctor（N=4，+1.99）、Ben Sheppard（N=1，-1.73）、Craig Porter Jr.（N=3，-5.50）、CJ McCollum（N=6，-5.59）、Nikola Vučević（N=5，-9.96）、Isaiah Stewart（N=4，-2.90）、Buddy Hield（N=6，+1.72）、Jamison Battle（N=5，+3.96）、Matas Buzelis（N=6，-3.52）、Deandre Ayton（N=6，-9.06）、Jalen Slawson（N=5，-4.10）、Danny Wolf（N=2，-1.40）、Brice Sensabaugh（N=5，-4.42）、Jordan McLaughlin（N=2，+1.22）、Derik Queen（N=5，-2.90）、Kobe Sanders（N=5，+2.07）、Vít Krejčí（N=4，-4.50）、Jaylen Clark（N=5，-2.69）、Isaac Okoro（N=6，-6.76）、Kyle Kuzma（N=5，+1.64）、Bennedict Mathurin（N=5，-8.87）、Marcus Sasser（N=6，+2.17）、Kyle Filipowski（N=3，-5.21）、Larry Nance Jr.（N=6，+2.73）、Bilal Coulibaly（N=6，-4.18）、Jamal Cain（N=5，+2.64）、Ryan Kalkbrenner（N=6，-2.02）、Nique Clifford（N=4，-6.80）、Kyle Anderson（N=3，-2.20）、Tim Hardaway Jr.（N=6，-8.06）、Corey Kispert（N=2，-2.92）、Max Christie（N=6，-3.28）、Olivier-Maxence Prosper（N=1，-2.32）、Khris Middleton（N=5，-3.79）、Brandon Williams（N=6，-2.94）、Branden Carlson（N=1，+1.02）、Leaky Black（N=2，-7.57）、Anfernee Simons（N=6，-4.69）、Myron Gardner（N=3，-2.88）、Dennis Schröder（N=6，+4.63）、Chaney Johnson（N=5，+1.44）、Jase Richardson（N=5，+1.69）、Simone Fontecchio（N=3，-4.60）、Jonathan Mogbo（N=3，+3.64）、Scoot Henderson（N=4，-3.85）、Malik Monk（N=4，-2.37）、Cam Whitmore（N=2，-1.29）、Justin Edwards（N=1，-2.42）、Harrison Barnes（N=4，-6.17）、Jarace Walker（N=6，-3.09）、Jabari Walker（N=3，-1.00）、Kevon Looney（N=4，+1.47）、Jake LaRavia（N=5，-4.18）、Taylor Hendricks（N=2，-1.61）、Jayson Kent（N=1，+2.60）、Oscar Tshiebwe（N=2，+1.41）、Jae'Sean Tate（N=4，-3.04）、Elijah Harkless（N=1，-1.00）、Alex Morales（N=3，+2.25）、Chris Mañon（N=2，+1.75）、John Tonje（N=1，+1.86）、Mohamed Diawara（N=1，-1.02）、Jamal Shead（N=5，-2.71）、Jerami Grant（N=5，-6.48）、Svi Mykhailiuk（N=5，-1.97）、Leonard Miller（N=6，-1.78）、Taurean Prince（N=2，-1.77）、Isaiah Collier（N=5，-2.64）、Klay Thompson（N=6，-1.20）、DeAndre Jordan（N=2，-1.46）、Royce O'Neale（N=6，-10.80）、Tre Mann（N=2，+2.30）、James Wiseman（N=3，+1.79）、Tre Johnson（N=5，-2.91）、Jericho Sims（N=2，+1.47）、Nick Richards（N=3，+2.69）、GG Jackson（N=5，-1.85）、Yang Hansen（N=2，-2.04）、Daeqwon Plowden（N=4，-4.86）、Jordan Poole（N=4，-2.84）、Cody Williams（N=4，+2.50）、Tidjane Salaün（N=5，-1.72）、Jordan Clarkson（N=5，+3.21）、Noah Clowney（N=5，-6.05）、Jaden Hardy（N=3，+3.26）、Caleb Love（N=1，+3.93）、Ben Saraf（N=1，+2.19）、Bub Carrington（N=6，-8.39）、Nolan Traore（N=5，-1.78）。
- 有屬性被更新的（屬性：人次）：stamina 250, pass 186, rebound 186, creation 186, tovSkill 184, short 171, ft 142, long 128, foulDraw 102, mid 20。

依 N 分組的 \|ΔOVR\|：

| N | 人數 | 中位數 | 最大 |
|---|---|---|---|
| 0 | 68 | 0.000 | 0.000 |
| 1 | 23 | 1.001 | 3.932 |
| 2 | 45 | 0.928 | 7.567 |
| 3 | 27 | 1.890 | 5.501 |
| 4 | 58 | 0.996 | 6.796 |
| 5 | 130 | 1.474 | 11.257 |
| 6 | 91 | 1.833 | 10.803 |

ΔOVR 最高 10 人：

| 球員 | 隊 | N | lastOVR | OVR | ΔOVR |
|---|---|---|---|---|---|
| Noa Essengue | CHI | 5 | 51.1 | 62.4 | +11.26 |
| Terrence Shannon Jr | MIN | 6 | 61.9 | 70.7 | +8.76 |
| Paul Reed | DET | 6 | 74.9 | 82.4 | +7.51 |
| Joan Beringer | MIN | 6 | 55.3 | 62.7 | +7.44 |
| Daniss Jenkins | DET | 6 | 59.7 | 66.7 | +7.03 |
| Trae Young | WAS | 6 | 73.0 | 79.4 | +6.40 |
| Precious Achiuwa | SAC | 5 | 64.9 | 71.0 | +6.09 |
| Dylan Harper | SAS | 5 | 72.5 | 78.5 | +6.04 |
| Ziaire Williams | LAL | 4 | 63.4 | 69.0 | +5.63 |
| Zaccharie Risacher | DAL | 6 | 59.9 | 65.4 | +5.47 |

ΔOVR 最低 10 人：

| 球員 | 隊 | N | lastOVR | OVR | ΔOVR |
|---|---|---|---|---|---|
| Royce O'Neale | CHA | 6 | 59.0 | 48.2 | -10.80 |
| Nikola Vučević | ORL | 5 | 71.5 | 61.6 | -9.96 |
| Deandre Ayton | WAS | 6 | 69.8 | 60.7 | -9.06 |
| Bennedict Mathurin | NOP | 5 | 67.8 | 59.0 | -8.87 |
| Bub Carrington | WAS | 6 | 42.0 | 33.6 | -8.39 |
| Tim Hardaway Jr. | MIA | 6 | 66.2 | 58.2 | -8.06 |
| Leaky Black | SAC | 2 | 65.2 | 57.6 | -7.57 |
| Nique Clifford | SAC | 4 | 65.1 | 58.3 | -6.80 |
| Isaac Okoro | CHI | 6 | 66.3 | 59.6 | -6.76 |
| Andrew Wiggins | MIA | 6 | 73.6 | 66.9 | -6.66 |

\|ΔOVR\| 最大 10 人的屬性變動明細（x0→x̂；觀測 y 已做 usage 調整）：

- Noa Essengue（CHI，N=5，ΔOVR +11.26）：（無屬性變動）
- Royce O'Neale（CHA，N=6，ΔOVR -10.80）：long 85.6→80.9（觀測 64.0、n=30、k=161、w=0.219）；pass 65.3→56.4（觀測 38.4、n=103、k=264、w=0.333）；rebound 75.2→72.5（觀測 63.0、n=103、k=522、w=0.226）；stamina 74.8→48.8（觀測 43.3、n=6、k=1、w=0.825）；creation 43.9→47.3（觀測 53.0、n=103、k=218、w=0.371）
- Nikola Vučević（ORL，N=5，ΔOVR -9.96）：stamina 75.0→47.2（觀測 40.0、n=5、k=1、w=0.796）
- Deandre Ayton（WAS，N=6，ΔOVR -9.06）：short 86.5→84.3（觀測 77.4、n=23、k=103、w=0.242）；stamina 70.6→45.3（觀測 40.0、n=6、k=1、w=0.825）
- Bennedict Mathurin（NOP，N=5，ΔOVR -8.87）：short 55.1→58.7（觀測 73.8、n=15、k=90、w=0.195）；tovSkill 53.9→52.1（觀測 42.2、n=53、k=496、w=0.151）；stamina 81.9→48.5（觀測 40.0、n=5、k=1、w=0.797）
- Terrence Shannon Jr（MIN，N=6，ΔOVR +8.76）：long 77.2→77.1（觀測 76.9、n=29、k=57、w=0.384）；short 61.9→63.3（觀測 66.4、n=18、k=50、w=0.318）；ft 74.1→71.6（觀測 69.2、n=28、k=30、w=0.517）；tovSkill 73.2→68.2（觀測 56.9、n=87、k=257、w=0.308）；pass 59.6→62.4（觀測 65.6、n=136、k=193、w=0.457）；rebound 47.9→53.2（觀測 62.5、n=136、k=301、w=0.362）；stamina 40.0→47.4（觀測 49.0、n=6、k=1、w=0.827）；creation 74.5→76.2（觀測 78.0、n=136、k=167、w=0.490）；foulDraw 78.3→84.1（觀測 91.8、n=51、k=83、w=0.427）
- Bub Carrington（WAS，N=6，ΔOVR -8.39）：long 85.1→83.4（觀測 76.4、n=24、k=149、w=0.201）；tovSkill 41.6→46.5（觀測 85.6、n=50、k=1194、w=0.111）；pass 87.6→81.7（觀測 71.3、n=119、k=265、w=0.360）；rebound 53.0→49.5（觀測 38.8、n=119、k=525、w=0.244）；stamina 72.2→45.6（觀測 40.0、n=6、k=1、w=0.825）；creation 79.4→67.4（觀測 49.4、n=119、k=218、w=0.400）
- Tim Hardaway Jr.（MIA，N=6，ΔOVR -8.06）：long 85.6→80.0（觀測 57.0、n=25、k=164、w=0.196）；ft 77.3→74.2（觀測 66.6、n=13、k=42、w=0.291）；tovSkill 107.9→105.4（觀測 87.5、n=52、k=920、w=0.123）；pass 42.4→41.6（觀測 40.2、n=110、k=263、w=0.346）；rebound 44.8→46.3（觀測 51.2、n=110、k=517、w=0.236）；stamina 67.4→44.8（觀測 40.0、n=6、k=1、w=0.825）；creation 52.2→52.6（觀測 53.3、n=110、k=217、w=0.385）
- Leaky Black（SAC，N=2，ΔOVR -7.57）：stamina 76.6→62.3（觀測 53.4、n=2、k=1、w=0.616）
- Paul Reed（DET，N=6，ΔOVR +7.51）：short 85.6→83.5（觀測 79.8、n=38、k=87、w=0.356）；ft 56.1→59.9（觀測 68.0、n=13、k=36、w=0.318）；tovSkill 54.6→51.7（觀測 40.6、n=83、k=498、w=0.205）；pass 63.3→60.5（觀測 57.2、n=161、k=225、w=0.460）；rebound 95.6→93.5（觀測 89.6、n=161、k=388、w=0.345）；stamina 40.0→63.0（觀測 67.8、n=6、k=1、w=0.826）；creation 59.9→56.9（觀測 53.8、n=161、k=190、w=0.498）；foulDraw 77.9→72.2（觀測 62.9、n=54、k=109、w=0.381）
