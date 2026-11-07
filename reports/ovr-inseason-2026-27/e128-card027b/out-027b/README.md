# inseason 0.2.7b 2026-27 即時結果（資料截至 2026-10-28）

- OVR：賽中 C4（inseason 0.2.7b），先驗 card 0.2.7b（live/prior-2025-26-card027b.json）；N = 該球員 2026-27 已打場數。
- 資料：2026-10-20..2026-10-28、68 場、67 份 PBP；缺 PBP：0022600101。
- git HEAD：`5acd8a0b6eb5`；c=1.0（凍結）、G=82、f = min(N/82, 1)。
- 排名 368 人（有先驗卡且已出賽）；沒有先驗卡 15 人（`no-prior.csv`，不給 OVR）；有先驗卡但 2026-27 還沒出賽 214 人（不列入）。
- N 分布：N=1: 38 人, N=2: 36 人, N=3: 51 人, N=4: 122 人, N=5: 121 人。
- 3PT 欄 = threeValue（R-024，顯示用、不進 OVR）：vol＝合併（2025-26＋2026-27）3PA/MIN×36；acc＝(k·上季 abilityC＋本季 3PM)/(k＋本季 3PA)，k=294.667（本季沒有出手難度資料，用原始命中）；rep＝合併聯盟 3P%（0.3588）−0.03；value＝vol×(acc−rep)，在合併 MIN≥500 且有先驗卡的 321 人池內取百分位並套 attr()。`long` 欄仍在 ranking.csv 並進 OVR 計算，只是表格不顯示。
- E-128（CARD_MODE=027b，實驗中）：先驗 x0＝card 0.2.7b 產生器的未四捨五入能力值（尾巴原樣、不夾 99）；屬性迴歸＝rebase-027a e123a primary 的 summary.json；賽中觀測值對 live/pool-027b.json 的合併池映射（pass 換 E-125 量×率合成值＋合併池，視窗不收縮、z 常數凍結自 2025-26 卡片端；其餘 8 欄同 pool-027），99 以上與 40 以下照 E-101 尾巴；help 照 E-123 D1 尾巴（不夾 99）；drive、onBall、pressure、presDisplay、physique、heightInches 凍結；防守加成＝UL 值（同 027）。
- 降級的資料層見 `../README.md`。`simulatedPer36` 空白（此流程不跑模擬）。
- `lastOVR` = 同一逐點管線對先驗卡算出的 OVR（ΔOVR 的基準）；`formalOVR` = card 0.2.7b `ranking.csv` 同名球員的 OVR（只供對照）。
- OVR 為每場（R-028，E-064 副版）：g = (預測每 36 分鐘淨值 − r_repl)·MPG_hat/36，r_repl＝-1.2728（替補水準 PR10），兩段映射錨點 PR1/PR50/PR99＝-0.8234/1.2758/4.1150（card 0.2.7b summary.json 同組）。MPG_hat = MPG0 + w·(本季場均分鐘 − MPG0)，w＝stamina 的 C4 w（stamina 最小樣本 1 場）；沒有本季視窗紀錄的 214 人（含沒出賽者，不在排名內）退回 MPG0。`ovrPer36` 是同一預測的每 36 分鐘 OVR。
- card 0.2.4 用人層（E-091，R-044 = 用人回歸＋當季 RAPM 目標）：p＝上面屬性迴歸的每 36 預測（`predictedPer36`，C4 照常更新），predNew＝b0 + b1·p + b2·L + b3·a + b4·y + b5·v + b6·y·L + b7·v·L + b8·y·d·L（`predNew` 欄）；L、a、y、v、d 與 has 旗標凍結在 2025-26 全季（`usage-2025-26-card027b.json`，payload sha256 e2fab234fa87…，年齡不加一歲），has=False 或不在卡內者 predNew＝p；係數 b0=-1.1356、b1=0.5640（E-084 results.json）。MPG0＝card 0.2.4 ranking.csv 的 mpg 欄（mpgAvail，依名字配對），卡裡沒有的人退回 MIN／GP。
- E-095（CARD_MODE=025）：分鐘權重 mpg/36 改為飽和 W(mpg)=(1−e^(−mpg/15))/(1−e^(−36/15))（card 0.2.5，R-047），錨點／r_repl 取 E-089 results.json report_only.card.new。
- E-128：用人層係數、r_repl、錨點取 reports/ovr-inseason-2026-27/live/usage-2025-26-card027b.json（rebase-027a e123a pipeline 重跑，錨點對 rebase-027a/work/cards-result.json 核對）；分鐘權重 W 同 card 0.2.5。

## 檢查 (a)：f=0、k 取上界 → 與上季卡一致（c4_v5 T1 同款）

| 項目 | 結果 |
|---|---|
| 逐球員 \|OVR 差\| 最大值（門檻 <0.5） | 0.040473 → 通過 |
| 本檔 live_predict 與 c4_v5.c4_predict（f=0, k 上界）屬性最大差 | 0.000e+00 |
| 本檔 live_predict（f=0, c=1）與 fit_w_grid_v4.c2_predict 屬性最大差（T2 同款，門檻 1e-9） | 2.842e-14 |
| 逐點管線 A 參考與原管線差（建構時檢查，門檻 1e-8） | 9.83e-12 |
| 重建的 2025-26 映射 vs 上季卡 long／ft 最大差（只由 box 決定，應接近 0） | 19.863 ／ 22.555 |
| lastOVR vs 正式卡 OVR（同名 368 人）最大差 | 0.09999999999999432 |

## 檢查 (b)：ΔOVR = 賽中 OVR − lastOVR

- 人數 368；\|ΔOVR\| 中位數 1.027、平均 1.470、最大 6.968。
- \|ΔOVR\| >= 1.0 的人：191 人：Victor Wembanyama（N=5，+1.17）、Nikola Jokić（N=4，-3.71）、Kawhi Leonard（N=2，-1.54）、Luka Dončić（N=4，+1.36）、Derrick White（N=4，-3.93）、Giannis Antetokounmpo（N=5，-2.85）、Lauri Markkanen（N=4，-4.25）、Joel Embiid（N=4，+2.18）、Dylan Harper（N=5，+5.62）、Dean Wade（N=3，+1.56）、Jayson Tatum（N=4，+1.01）、Jalen Williams（N=3，+3.41）、Brandin Podziemski（N=3，+3.11）、Anthony Davis（N=5，+1.02）、Evan Mobley（N=4，-1.11）、Kevin Durant（N=5，-1.87）、Scottie Barnes（N=4，-1.98）、Ryan Rollins（N=5，-3.09）、Herbert Jones（N=4，-3.73）、Ty Jerome（N=4，+2.80）、Neemias Queta（N=4，-5.39）、Paul George（N=4，+1.25）、Alperen Sengun（N=4，+1.50）、Toumani Camara（N=3，-1.56）、Walker Kessler（N=5，+1.55）、Peyton Watson（N=4，+3.15）、Michael Porter Jr.（N=4，-1.57）、Jalen Suggs（N=3，+1.53）、Josh Giddey（N=5，-1.59）、Oso Ighodaro（N=1，-1.52）、Onyeka Okongwu（N=5，-1.30）、Cameron Johnson（N=1，-3.65）、Mikal Bridges（N=5，-3.51）、Jalen Duren（N=2，-4.14）、Trey Murphy III（N=4，-1.66）、Karl-Anthony Towns（N=5，-1.33）、Jonathan Kuminga（N=5，+4.68）、Domantas Sabonis（N=4，+4.89）、Pelle Larsson（N=5，+1.14）、Dejounte Murray（N=4，+2.31）、Day'Ron Sharpe（N=4，+1.01）、Rui Hachimura（N=3，+1.84）、Zach Edey（N=3，-1.17）、Cason Wallace（N=3，-2.75）、RJ Barrett（N=4，+1.74）、Daniel Gafford（N=5，+1.46）、Collin Murray-Boyles（N=4，-1.98）、Ja'Kobe Walter（N=4，+3.10）、Paul Reed（N=5，+4.95）、Ivica Zubac（N=3，-2.49）、Miles McBride（N=5，-4.04）、LaMelo Ball（N=5，-1.64）、Andrew Nembhard（N=4，+1.19）、Gui Santos（N=4，+3.43）、Duncan Robinson（N=5，+1.51）、Jakob Poeltl（N=4，-1.70）、James Harden（N=4，-1.17）、Matisse Thybulle（N=5，+2.62）、Josh Okogie（N=4，+1.06）、Ronald Holland II（N=5，-2.22）、Kasparas Jakučionis（N=5，+4.72）、Payton Pritchard（N=4，-2.91）、Matas Buzelis（N=5，-1.36）、Luke Kornet（N=5，-2.73）、Trae Young（N=5，+2.53）、Kelly Oubre Jr.（N=5，-2.89）、Kris Murray（N=1，-1.52）、Saddiq Bey（N=4，-3.36）、Jaylon Tyson（N=4，-2.24）、Norman Powell（N=5，-1.11）、Isaiah Joe（N=3，-2.36）、Tre Jones（N=5，-3.61）、Jaylin Williams（N=5，-2.11）、Aaron Nesmith（N=4，-2.12）、Zach LaVine（N=4，+1.42）、Kentavious Caldwell-Pope（N=5，+2.13）、Cam Spencer（N=4，-2.17）、Jaxson Hayes（N=4，+3.67）、Sidy Cissoko（N=3，+3.22）、Keon Ellis（N=4，+2.72）、De'Andre Hunter（N=4，+1.02）、Isaiah Stewart（N=3，-2.12）、Mitchell Robinson（N=4，-1.25）、Andrew Wiggins（N=5，-1.96）、AJ Green（N=5，-3.91）、Daniss Jenkins（N=5，+4.31）、Justin Champagnie（N=4，+1.46）、Zaccharie Risacher（N=5，+3.25）、Kevin Huerter（N=5，-1.04）、Kel'el Ware（N=5，-1.53）、Jamal Shead（N=4，-1.39）、Al Horford（N=4，-1.30）、DeMar DeRozan（N=4，-1.69）、Luke Kennard（N=2，-1.01）、Kenrich Williams（N=5，-1.51）、Jay Huff（N=4，-2.29）、Marvin Bagley III（N=4，-2.88）、Karlo Matković（N=3，-1.81）、Kyle Kuzma（N=5，+1.01）、Quenton Jackson（N=5，+1.43）、Josh Minott（N=3，-2.04）、Isaac Okoro（N=5，-3.79）、Aaron Wiggins（N=5，+3.84）、Hugo González（N=4，-2.60）、Jose Alvarado（N=2，-1.63）、Keldon Johnson（N=5，-1.04）、Isaiah Jackson（N=4，+1.75）、Collin Sexton（N=4，-2.13）、Ryan Kalkbrenner（N=5，-1.09）、Jock Landale（N=5，-2.32）、Leonard Miller（N=5，+4.47）、Zach Collins（N=3，-3.59）、Nique Clifford（N=3，-5.85）、Clint Capela（N=4，-2.21）、Adem Bona（N=5，-2.68）、Josh Green（N=3，+1.83）、Luka Garza（N=4，-2.45）、CJ McCollum（N=5，-4.91）、Ziaire Williams（N=4，+2.36）、Jared McCain（N=5，+1.85）、Nikola Vučević（N=4，-6.97）、Dru Smith（N=3，-1.22）、Jalen Slawson（N=4，-3.07）、Dennis Schröder（N=5，+3.64）、Scoot Henderson（N=3，-3.96）、Terrence Shannon Jr（N=5，+5.07）、Tim Hardaway Jr.（N=5，-2.08）、Harrison Barnes（N=4，-4.30）、Chaney Johnson（N=4，+4.84）、Svi Mykhailiuk（N=5，-1.18）、Deandre Ayton（N=5，-5.24）、Bennedict Mathurin（N=4，-3.71）、Joan Beringer（N=5，+5.90）、Jarred Vanderbilt（N=1，+1.24）、Tyler Kolek（N=3，+1.89）、Vít Krejčí（N=3，-3.21）、Leaky Black（N=2，-5.04）、Cedric Coward（N=3，+1.73）、Bones Hyland（N=5，-1.40）、Larry Nance Jr.（N=5，+2.69）、Kyle Anderson（N=3，-2.39）、Craig Porter Jr.（N=2，-2.30）、Kyshawn George（N=5，+2.71）、Jamal Cain（N=4，+2.20）、Jamaree Bouyea（N=2，-1.36）、Trayce Jackson-Davis（N=4，+1.71）、Jabari Walker（N=3，-2.18）、Anthony Gill（N=1，-2.37）、Bogdan Bogdanović（N=5，+2.04）、Jevon Carter（N=2，+1.84）、Jaylen Clark（N=4，-3.82）、Brandon Williams（N=5，-1.05）、Marcus Sasser（N=5，+2.19）、Dorian Finney-Smith（N=2，+1.26）、Anfernee Simons（N=5，-3.96）、Micah Peavy（N=1，-1.52）、Noa Essengue（N=4，+5.01）、Justin Edwards（N=1，-2.63）、Jase Richardson（N=4，+1.26）、Corey Kispert（N=2，-2.03）、Myron Gardner（N=2，-1.17）、Kevon Looney（N=4，+1.73）、Simone Fontecchio（N=2，-3.01）、Mike Conley（N=1，-1.20）、Jalen Pickett（N=2，-1.08）、Royce O'Neale（N=5，-1.03）、Khaman Maluach（N=3，+2.00）、Oscar Tshiebwe（N=1，+1.72）、Jae'Sean Tate（N=4，-1.94）、Jamison Battle（N=4，+1.12）、Mohamed Diawara（N=1，-1.20）、Kobe Brown（N=2，-1.72）、Elijah Harkless（N=1，-2.59）、Mo Bamba（N=2，+1.14）、Jordan Poole（N=4，-1.10）、Nick Richards（N=2，+1.75）、Derik Queen（N=4，+1.01）、Tre Mann（N=1，+1.49）、Tyus Jones（N=4，+1.59）、Jordan Clarkson（N=4，+1.87）、Ace Bailey（N=5，+1.09）、Caleb Love（N=1，+1.21）、Taylor Hendricks（N=1，+1.15）、Jordan Hawkins（N=1，+1.10）、Yang Hansen（N=1，-1.61）、Ryan Nembhard（N=2，+1.82）、Yves Missi（N=2，-2.26）、Will Riley（N=3，+5.49）、Ben Saraf（N=1，+2.39）、Jaden Hardy（N=2，+1.67）、Cody Williams（N=3，+5.72）。
- 有屬性被更新的（屬性：人次）：stamina 253, tovSkill 154, short 146, pass 141, rebound 141, creation 141, ft 126, long 101, foulDraw 70, mid 14。

依 N 分組的 \|ΔOVR\|：

| N | 人數 | 中位數 | 最大 |
|---|---|---|---|
| 1 | 38 | 0.841 | 3.653 |
| 2 | 36 | 1.046 | 5.043 |
| 3 | 51 | 1.222 | 5.853 |
| 4 | 122 | 1.080 | 6.968 |
| 5 | 121 | 1.018 | 5.899 |

ΔOVR 最高 10 人：

| 球員 | 隊 | N | lastOVR | OVR | ΔOVR |
|---|---|---|---|---|---|
| Joan Beringer | MIN | 5 | 55.9 | 61.8 | +5.90 |
| Cody Williams | MIN | 3 | 35.6 | 41.4 | +5.72 |
| Dylan Harper | SAS | 5 | 80.3 | 85.9 | +5.62 |
| Will Riley | WAS | 3 | 38.3 | 43.8 | +5.49 |
| Terrence Shannon Jr | MIN | 5 | 58.6 | 63.6 | +5.07 |
| Noa Essengue | CHI | 4 | 52.0 | 57.0 | +5.01 |
| Paul Reed | DET | 5 | 70.0 | 74.9 | +4.95 |
| Domantas Sabonis | SAC | 4 | 72.7 | 77.6 | +4.89 |
| Chaney Johnson | BKN | 4 | 57.5 | 62.3 | +4.84 |
| Kasparas Jakučionis | MIL | 5 | 68.2 | 72.9 | +4.72 |

ΔOVR 最低 10 人：

| 球員 | 隊 | N | lastOVR | OVR | ΔOVR |
|---|---|---|---|---|---|
| Nikola Vučević | ORL | 4 | 71.1 | 64.1 | -6.97 |
| Nique Clifford | SAC | 3 | 71.5 | 65.7 | -5.85 |
| Neemias Queta | BOS | 4 | 87.7 | 82.3 | -5.39 |
| Deandre Ayton | WAS | 5 | 67.3 | 62.1 | -5.24 |
| Leaky Black | SAC | 2 | 66.1 | 61.0 | -5.04 |
| CJ McCollum | ATL | 5 | 70.0 | 65.1 | -4.91 |
| Harrison Barnes | SAS | 4 | 67.4 | 63.1 | -4.30 |
| Lauri Markkanen | UTA | 4 | 91.7 | 87.5 | -4.24 |
| Jalen Duren | DET | 2 | 82.2 | 78.1 | -4.14 |
| Miles McBride | NYK | 5 | 78.6 | 74.5 | -4.04 |

\|ΔOVR\| 最大 10 人的屬性變動明細（x0→x̂；觀測 y 已做 usage 調整）：

- Nikola Vučević（ORL，N=4，ΔOVR -6.97）：stamina 75.0→48.6（觀測 40.0、n=4、k=1、w=0.755）
- Joan Beringer（MIN，N=5，ΔOVR +5.90）：short 78.2→77.5（觀測 76.3、n=22、k=55、w=0.329）
- Nique Clifford（SAC，N=3，ΔOVR -5.85）：stamina 60.6→51.1（觀測 47.0、n=3、k=1、w=0.694）
- Cody Williams（MIN，N=3，ΔOVR +5.72）：stamina 58.5→45.6（觀測 40.0、n=3、k=1、w=0.695）
- Dylan Harper（SAS，N=5，ΔOVR +5.62）：short 70.9→71.6（觀測 72.8、n=46、k=96、w=0.364）；ft 68.9→69.6（觀測 71.1、n=13、k=37、w=0.305）；tovSkill 71.1→73.8（觀測 88.3、n=111、k=966、w=0.158）；pass 87.9→86.2（觀測 83.9、n=161、k=252、w=0.427）；rebound 66.7→67.7（觀測 70.1、n=161、k=475、w=0.299）；stamina 52.1→77.7（觀測 84.3、n=5、k=1、w=0.796）；creation 88.4→90.0（觀測 91.8、n=161、k=209、w=0.470）；foulDraw 60.3→60.0（觀測 59.6、n=74、k=129、w=0.404）
- Will Riley（WAS，N=3，ΔOVR +5.49）：stamina 49.2→43.6（觀測 41.2、n=3、k=1、w=0.695）
- Neemias Queta（BOS，N=4，ΔOVR -5.39）：short 83.4→80.9（觀測 70.1、n=17、k=100、w=0.187）；ft 57.7→59.3（觀測 63.1、n=15、k=41、w=0.303）；stamina 61.4→48.5（觀測 44.3、n=4、k=1、w=0.754）
- Deandre Ayton（WAS，N=5，ΔOVR -5.24）：short 86.5→85.4（觀測 81.4、n=19、k=103、w=0.207）；stamina 70.6→46.3（觀測 40.0、n=5、k=1、w=0.795）
- Terrence Shannon Jr（MIN，N=5，ΔOVR +5.07）：long 77.2→76.7（觀測 75.8、n=25、k=57、w=0.346）；short 61.9→62.9（觀測 65.2、n=17、k=50、w=0.299）；ft 74.1→71.9（觀測 69.5、n=24、k=30、w=0.475）；tovSkill 73.2→67.6（觀測 53.0、n=78、k=257、w=0.279）；pass 59.6→62.2（觀測 65.9、n=116、k=193、w=0.414）；rebound 47.9→52.4（觀測 61.9、n=116、k=301、w=0.322）；stamina 40.0→47.8（觀測 49.8、n=5、k=1、w=0.798）；creation 74.5→77.0（觀測 80.1、n=116、k=167、w=0.446）
- Leaky Black（SAC，N=2，ΔOVR -5.04）：stamina 76.6→62.3（觀測 53.4、n=2、k=1、w=0.616）
