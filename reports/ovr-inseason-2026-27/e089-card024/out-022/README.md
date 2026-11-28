# inseason 0.2.1 2026-27 即時結果（資料截至 2026-10-28）

- OVR：賽中 C4（inseason 0.2.1），先驗 card 0.2.2（live/prior-2025-26-card022.json）；N = 該球員 2026-27 已打場數。
- 資料：2026-10-20..2026-10-28、68 場、67 份 PBP；缺 PBP：0022600101。
- git HEAD：`7dd87d07810f`；c=1.0（凍結）、G=82、f = min(N/82, 1)。
- 排名 368 人（有先驗卡且已出賽）；沒有先驗卡 57 人（`no-prior.csv`，不給 OVR）；有先驗卡但 2026-27 還沒出賽 214 人（不列入）。
- N 分布：N=1: 38 人, N=2: 36 人, N=3: 51 人, N=4: 122 人, N=5: 121 人。
- 3PT 欄 = threeValue（R-024，顯示用、不進 OVR）：vol＝合併（2025-26＋2026-27）3PA/MIN×36；acc＝(k·上季 abilityC＋本季 3PM)/(k＋本季 3PA)，k=294.667（本季沒有出手難度資料，用原始命中）；rep＝合併聯盟 3P%（0.3588）−0.03；value＝vol×(acc−rep)，在合併 MIN≥500 且有先驗卡的 321 人池內取百分位並套 attr()。`long` 欄仍在 ranking.csv 並進 OVR 計算，只是表格不顯示。
- card 0.2.2 的屬性處理（E-074，換版不重擬合）：先驗屬性 x0、屬性迴歸係數（card-0.2.2/cards/P1/primary/summary.json）、每場錨點與 r_repl 全部取自 card 0.2.2；pressure＝逼失誤 force（E-071 P1），賽中凍結；foulDraw 用 E-070 公式做 C4 更新：y＝百分位(0.75·z(FTA/36)＋0.25·z(FTA/FGA))，z 的平均／標準差與百分位對照母體凍結自 2025-26 池（GP≥30、MPG≥20，252 人；FTA/36 mean 3.7493 std 1.9723、FTA/FGA mean 0.2639 std 0.1057），不用 2026-27 資料重估，收縮 k／δ²／rel 沿用 drive 的；drive（PBP 版）、onBall（E-060）、pressure、help、physique、heightInches 凍結。PRES 欄顯示 presDisplay、tooltip 列逼失誤與犯規紀律（2025-26，不進 OVR）。
- 降級的資料層見 `../README.md`。`simulatedPer36` 空白（此流程不跑模擬）。
- `lastOVR` = 同一逐點管線對先驗卡算出的 OVR（ΔOVR 的基準）；`formalOVR` = card 0.2.2 `ranking.csv` 同名球員的 OVR（只供對照）。
- OVR 為每場（R-028，E-064 副版）：g = (預測每 36 分鐘淨值 − r_repl)·MPG_hat/36，r_repl＝-1.7593（替補水準 PR10），兩段映射錨點 PR1/PR50/PR99＝-0.7564/1.0495/4.7440（card 0.2.2 P1 primary 的 pergame-summary.json 同組）。MPG_hat = MPG0 + w·(本季場均分鐘 − MPG0)，w＝stamina 的 C4 w（stamina 最小樣本 1 場）；沒有本季視窗紀錄的 214 人（含沒出賽者，不在排名內）退回 MPG0。`ovrPer36` 是同一預測的每 36 分鐘 OVR。

## 檢查 (a)：f=0、k 取上界 → 與上季卡一致（c4_v5 T1 同款）

| 項目 | 結果 |
|---|---|
| 逐球員 \|OVR 差\| 最大值（門檻 <0.5） | 0.051022 → 通過 |
| 本檔 live_predict 與 c4_v5.c4_predict（f=0, k 上界）屬性最大差 | 0.000e+00 |
| 本檔 live_predict（f=0, c=1）與 fit_w_grid_v4.c2_predict 屬性最大差（T2 同款，門檻 1e-9） | 2.842e-14 |
| 逐點管線 A 參考與原管線差（建構時檢查，門檻 1e-8） | 9.68e-12 |
| 重建的 2025-26 映射 vs 上季卡 long／ft 最大差（只由 box 決定，應接近 0） | 0.050 ／ 22.577 |
| lastOVR vs 正式卡 OVR（同名 368 人）最大差 | 0.10000000000000853 |

## 檢查 (b)：ΔOVR = 賽中 OVR − lastOVR

- 人數 368；\|ΔOVR\| 中位數 1.732、平均 2.228、最大 10.292。
- \|ΔOVR\| >= 1.0 的人：246 人：Nikola Jokić（N=4，-1.23）、Shai Gilgeous-Alexander（N=5，-4.88）、Franz Wagner（N=4，+2.87）、Derrick White（N=4，-3.55）、Joel Embiid（N=4，+1.64）、Victor Wembanyama（N=5，+1.13）、Kawhi Leonard（N=2，-4.23）、Kevin Durant（N=5，-5.44）、Cade Cunningham（N=5，+1.05）、Amen Thompson（N=5，-2.24）、Tyrese Maxey（N=5，-1.33）、Jayson Tatum（N=4，+3.58）、Lauri Markkanen（N=4，-7.19）、Anthony Davis（N=5，+1.12）、Stephen Curry（N=4，-3.78）、Paul George（N=4，+1.02）、Aaron Gordon（N=4，+1.65）、Ty Jerome（N=4，+6.99）、Dean Wade（N=3，+3.23）、Dylan Harper（N=5，+7.05）、Scottie Barnes（N=4，-2.01）、Desmond Bane（N=4，-2.11）、Anthony Edwards（N=4，-1.41）、Davion Mitchell（N=5，+2.82）、Jrue Holiday（N=3，-2.10）、Dyson Daniels（N=5，-2.54）、Marcus Smart（N=2，-2.41）、Moussa Diabaté（N=5，+2.69）、Jalen Williams（N=3，+1.57）、Jalen Brunson（N=5，-2.39）、Derrick Jones Jr.（N=4，+2.83）、Herbert Jones（N=4，-7.83）、Jalen Suggs（N=3，+2.43）、Toumani Camara（N=3，-4.19）、Michael Porter Jr.（N=4，-2.45）、Immanuel Quickley（N=4，-1.65）、Brandin Podziemski（N=3，+2.48）、Neemias Queta（N=4，-5.10）、Walker Kessler（N=5，-1.85）、Nickeil Alexander-Walker（N=5，-1.59）、Jaren Jackson Jr.（N=4，-2.17）、Onyeka Okongwu（N=5，-3.05）、Christian Braun（N=4，+1.48）、Ryan Rollins（N=5，-5.32）、Paul Reed（N=5，+7.28）、VJ Edgecombe（N=4，-1.44）、Jonathan Kuminga（N=5，+4.95）、Jaylen Brown（N=5，-1.34）、Kris Dunn（N=4，+1.79）、Alperen Sengun（N=4，+1.06）、Dejounte Murray（N=4，+3.06）、Pelle Larsson（N=5，+2.08）、Trey Murphy III（N=4，-3.12）、Mikal Bridges（N=5，-5.78）、Cameron Johnson（N=1，-5.82）、Jalen Smith（N=5，+1.78）、Zach LaVine（N=4，+2.01）、Keegan Murray（N=2，-3.61）、James Harden（N=4，-2.83）、Sion James（N=5，+1.29）、Rui Hachimura（N=3，+1.06）、Brandon Miller（N=5，+1.23）、Collin Gillespie（N=3，-3.07）、Cedric Coward（N=3，+2.13）、Kyshawn George（N=5，+2.43）、Daniel Gafford（N=5，+1.07）、John Collins（N=5，-1.42）、Miles McBride（N=5，-4.55）、Obi Toppin（N=5，+1.14）、Domantas Sabonis（N=4，+3.86）、Ivica Zubac（N=3，-5.33）、Oso Ighodaro（N=1，-1.96）、Trae Young（N=5，+8.97）、Duncan Robinson（N=5，+1.75）、Kentavious Caldwell-Pope（N=5，+1.89）、RJ Barrett（N=4，+1.22）、Josh Giddey（N=5，-3.67）、Zach Edey（N=3，-2.46）、Peyton Watson（N=4，+1.18）、Matisse Thybulle（N=5，+3.71）、Jalen Duren（N=2，-4.74）、Keon Ellis（N=4，+2.76）、Ja'Kobe Walter（N=4，+3.75）、Gui Santos（N=4，+1.87）、Sam Hauser（N=4，-1.80）、LaMelo Ball（N=5，-2.82）、Andrew Wiggins（N=5，-3.26）、Payton Pritchard（N=4，-4.41）、Cason Wallace（N=3，-3.74）、Collin Murray-Boyles（N=4，-1.52）、DeMar DeRozan（N=4，-3.45）、Kasparas Jakučionis（N=5，+2.54）、Luke Kornet（N=5，-3.11）、Jaylin Williams（N=5，-1.34）、Isaiah Joe（N=3，-3.24）、Saddiq Bey（N=4，-3.77）、Kris Murray（N=1，-2.17）、Jakob Poeltl（N=4，-2.75）、Jaxson Hayes（N=4，+8.07）、Daniss Jenkins（N=5，+5.24）、Kenrich Williams（N=5，-1.72）、Kelly Oubre Jr.（N=5，-4.66）、Jaylen Wells（N=4，+1.95）、Jaime Jaquez Jr.（N=5，+1.48）、Donovan Clingan（N=3，-1.93）、Tre Jones（N=5，-5.06）、P.J. Washington（N=5，+3.43）、Anthony Black（N=2，-1.15）、Aaron Nesmith（N=4，-3.62）、Cam Spencer（N=4，-2.95）、AJ Green（N=5，-5.29）、Grayson Allen（N=5，-1.31）、Isaiah Stewart（N=3，-2.34）、Al Horford（N=4，-1.76）、Luguentz Dort（N=5，-1.25）、Jordan Goodwin（N=3，-1.80）、Clint Capela（N=4，-1.16）、Ronald Holland II（N=5，-2.79）、Goga Bitadze（N=3，-2.20）、Sidy Cissoko（N=3，+3.33）、Karlo Matković（N=3，-2.07）、Egor Dëmin（N=4，-2.60）、Jose Alvarado（N=2，-2.66）、Baylor Scheierman（N=4，-1.03）、Matas Buzelis（N=5，-3.01）、Gary Payton II（N=5，-1.69）、Bobby Portis Jr.（N=5，-2.69）、Luke Kennard（N=2，-2.45）、Jaylon Tyson（N=4，-4.19）、Marvin Bagley III（N=4，-4.51）、Josh Minott（N=3，-4.64）、Keldon Johnson（N=5，-1.72）、Kevin Huerter（N=5，-2.43）、Quentin Grimes（N=5，-2.41）、Svi Mykhailiuk（N=5，-4.85）、Aaron Wiggins（N=5，+5.34）、CJ McCollum（N=5，-5.97）、Jalen Slawson（N=4，-8.50）、Jay Huff（N=4，-2.85）、Isaac Okoro（N=5，-6.28）、Keyonte George（N=5，+2.41）、Steven Adams（N=1，-5.01）、Ryan Dunn（N=3，-2.87）、Isaiah Jackson（N=4，+1.82）、Joan Beringer（N=5，+4.37）、Precious Achiuwa（N=4，+1.29）、Zach Collins（N=3，-6.51）、Scotty Pippen Jr.（N=4，-2.10）、Kyle Kuzma（N=5，+2.06）、Nique Clifford（N=3，-8.67）、Luka Garza（N=4，-4.81）、Jarred Vanderbilt（N=1，+1.03）、Kel'el Ware（N=5，-2.43）、Dennis Schröder（N=5，+4.78）、Jock Landale（N=5，-3.00）、Collin Sexton（N=4，-4.42）、Nikola Vučević（N=4，-10.29）、Kyle Anderson（N=3，-7.66）、Terrence Shannon Jr（N=5，+4.71）、Daeqwon Plowden（N=4，-7.16）、Danny Wolf（N=1，-1.43）、Adem Bona（N=5，-2.53）、Ace Bailey（N=5，+1.96）、Kevon Looney（N=4，-4.84）、Bogdan Bogdanović（N=5，-2.45）、Tristan da Silva（N=4，+1.90）、Ziaire Williams（N=4，+3.15）、Max Christie（N=5，-1.50）、Moritz Wagner（N=4，+1.22）、Marcus Sasser（N=5，+3.40）、Dru Smith（N=3，-1.86）、Zaccharie Risacher（N=5，+3.37）、Harrison Barnes（N=4，-10.16）、Anthony Gill（N=1，-5.04）、Buddy Hield（N=5，-1.11）、Tim Hardaway Jr.（N=5，-6.19）、Jamal Shead（N=4，-1.16）、Ryan Kalkbrenner（N=5，-2.21）、Jalen Green（N=3，+2.06）、Bryce McGowens（N=1，-3.89）、Noa Essengue（N=4，+4.43）、Will Richard（N=5，-1.10）、Hugo González（N=4，-1.32）、Vít Krejčí（N=3，-4.49）、Myron Gardner（N=2，-3.78）、Malevy Leons（N=3，-3.12）、Brice Sensabaugh（N=5，-3.69）、Micah Potter（N=1，-1.03）、Asa Newell（N=2，-3.01）、Jaylen Clark（N=4，-5.04）、Khaman Maluach（N=3，+3.23）、Ben Sheppard（N=1，-1.41）、Charles Bassey（N=3，-2.77）、Kyle Filipowski（N=3，-4.88）、Craig Porter Jr.（N=2，-2.60）、Tyrese Proctor（N=3，-1.21）、Scoot Henderson（N=3，-2.31）、Rasheer Fleming（N=2，-1.20）、Zeke Nnaji（N=1，-1.57）、Jalen Pickett（N=2，-2.77）、Mo Bamba（N=2，+1.79）、Jabari Walker（N=3，-1.71）、Moussa Cisse（N=4，-4.60）、David Jones Garcia（N=1，-1.99）、Jae'Sean Tate（N=4，-4.71）、Khris Middleton（N=4，-2.12）、LJ Cryer（N=3，-1.62）、GG Jackson（N=4，-1.45）、Jerami Grant（N=4，-3.95）、Elijah Harkless（N=1，-1.94）、Deandre Ayton（N=5，-5.64）、Bennedict Mathurin（N=4，-6.25）、DaRon Holmes II（N=2，-1.69）、Tolu Smith（N=4，-2.73）、Dorian Finney-Smith（N=2，-1.93）、Jake LaRavia（N=4，-1.56）、Brandon Williams（N=5，-1.86）、Leaky Black（N=2，-5.35）、Bones Hyland（N=5，-1.13）、Cam Whitmore（N=2，-1.01）、Malik Monk（N=3，-1.39）、Simone Fontecchio（N=2，-1.76）、Isaiah Crawford（N=4，-1.54）、Reed Sheppard（N=4，-2.87）、Anfernee Simons（N=5，-4.85）、Ryan Nembhard（N=2，+2.40）、Nick Richards（N=2，+2.30）、James Wiseman（N=3，+3.27）、Chaz Lanier（N=1，+1.33）、Will Riley（N=3，+5.62）、Tre Mann（N=1，+2.97）、Jericho Sims（N=2，+3.97）、Royce O'Neale（N=5，-3.23）、Jordan Clarkson（N=4，+3.64）、Cody Williams（N=3，+6.79）、Drake Powell（N=1，+1.16）、Jarace Walker（N=5，-1.21）、Noah Clowney（N=4，-1.39）、Ben Saraf（N=1，+3.09）、Caleb Love（N=1，+5.69）、Jordan Hawkins（N=1，+2.05）、Tyus Jones（N=4，+2.49）、Jaden Hardy（N=2，+3.46）、Gary Trent Jr.（N=1，+3.53）、Bub Carrington（N=5，-1.81）、Nolan Traore（N=4，+2.97）。
- 有屬性被更新的（屬性：人次）：stamina 253, tovSkill 153, short 146, pass 141, rebound 138, creation 138, ft 126, long 101, foulDraw 70, mid 14。

依 N 分組的 \|ΔOVR\|：

| N | 人數 | 中位數 | 最大 |
|---|---|---|---|
| 1 | 38 | 1.029 | 5.816 |
| 2 | 36 | 1.723 | 5.348 |
| 3 | 51 | 2.198 | 8.670 |
| 4 | 122 | 1.641 | 10.292 |
| 5 | 121 | 1.745 | 8.968 |

ΔOVR 最高 10 人：

| 球員 | 隊 | N | lastOVR | OVR | ΔOVR |
|---|---|---|---|---|---|
| Trae Young | WAS | 5 | 65.1 | 74.1 | +8.97 |
| Jaxson Hayes | UTA | 4 | 62.9 | 70.9 | +8.07 |
| Paul Reed | DET | 5 | 71.2 | 78.5 | +7.28 |
| Dylan Harper | SAS | 5 | 78.6 | 85.7 | +7.05 |
| Ty Jerome | MEM | 4 | 79.8 | 86.8 | +6.99 |
| Cody Williams | MIN | 3 | 40.0 | 46.7 | +6.79 |
| Caleb Love | PHI | 1 | 39.1 | 44.7 | +5.69 |
| Will Riley | WAS | 3 | 42.6 | 48.2 | +5.61 |
| Aaron Wiggins | ATL | 5 | 60.0 | 65.4 | +5.34 |
| Daniss Jenkins | DET | 5 | 65.7 | 70.9 | +5.24 |

ΔOVR 最低 10 人：

| 球員 | 隊 | N | lastOVR | OVR | ΔOVR |
|---|---|---|---|---|---|
| Nikola Vučević | ORL | 4 | 72.4 | 62.1 | -10.29 |
| Harrison Barnes | SAS | 4 | 70.3 | 60.1 | -10.16 |
| Nique Clifford | SAC | 3 | 71.9 | 63.2 | -8.67 |
| Jalen Slawson | IND | 4 | 73.4 | 64.9 | -8.50 |
| Herbert Jones | NOP | 4 | 88.8 | 81.0 | -7.83 |
| Kyle Anderson | TOR | 3 | 69.5 | 61.9 | -7.66 |
| Lauri Markkanen | UTA | 4 | 95.3 | 88.1 | -7.19 |
| Daeqwon Plowden | SAC | 4 | 68.8 | 61.6 | -7.16 |
| Zach Collins | CHI | 3 | 70.0 | 63.5 | -6.51 |
| Isaac Okoro | CHI | 5 | 71.0 | 64.7 | -6.28 |

\|ΔOVR\| 最大 10 人的屬性變動明細（x0→x̂；觀測 y 已做 usage 調整）：

- Nikola Vučević（ORL，N=4，ΔOVR -10.29）：stamina 75.0→48.6（觀測 40.0、n=4、k=1、w=0.755）
- Harrison Barnes（SAS，N=4，ΔOVR -10.16）：stamina 62.8→45.6（觀測 40.0、n=4、k=1、w=0.754）
- Trae Young（WAS，N=5，ΔOVR +8.97）：long 63.5→60.4（觀測 56.9、n=37、k=47、w=0.474）；short 47.0→56.6（觀測 70.1、n=27、k=45、w=0.414）；ft 85.0→78.0（觀測 73.4、n=43、k=31、w=0.606）；tovSkill 46.7→61.5（觀測 83.4、n=157、k=274、w=0.403）；pass 99.0→98.9（觀測 98.9、n=180、k=169、w=0.546）；rebound 40.0→40.7（觀測 41.6、n=180、k=246、w=0.458）；stamina 61.5→91.6（觀測 98.9、n=5、k=1、w=0.806）；creation 90.0→83.2（觀測 78.2、n=180、k=148、w=0.576）；foulDraw 97.7→97.8（觀測 97.9、n=73、k=74、w=0.529）
- Nique Clifford（SAC，N=3，ΔOVR -8.67）：stamina 60.6→51.1（觀測 46.9、n=3、k=1、w=0.694）
- Jalen Slawson（IND，N=4，ΔOVR -8.50）：stamina 56.4→43.8（觀測 40.0、n=4、k=1、w=0.767）
- Jaxson Hayes（UTA，N=4，ΔOVR +8.07）：short 83.7→82.5（觀測 78.2、n=17、k=83、w=0.210）；ft 50.3→54.3（觀測 66.0、n=11、k=40、w=0.255）；pass 41.6→49.9（觀測 65.9、n=108、k=241、w=0.343）；rebound 88.8→88.5（觀測 87.6、n=108、k=436、w=0.237）；stamina 40.0→62.0（觀測 69.1、n=4、k=1、w=0.755）
- Herbert Jones（NOP，N=4，ΔOVR -7.83）：stamina 74.6→48.5（觀測 40.0、n=4、k=1、w=0.755）
- Kyle Anderson（TOR，N=3，ΔOVR -7.66）：（無屬性變動）
- Paul Reed（DET，N=5，ΔOVR +7.28）：short 85.6→83.2（觀測 77.6、n=29、k=85、w=0.300）；ft 56.1→59.8（觀測 68.0、n=13、k=36、w=0.309）；tovSkill 56.2→53.5（觀測 40.4、n=68、k=498、w=0.173）；pass 64.4→65.0（觀測 65.9、n=130、k=226、w=0.404）；rebound 96.1→95.2（觀測 93.0、n=130、k=389、w=0.296）；stamina 40.0→58.8（觀測 63.7、n=5、k=1、w=0.796）；creation 59.8→55.0（觀測 48.9、n=130、k=191、w=0.442）
- Lauri Markkanen（UTA，N=4，ΔOVR -7.19）：long 66.4→66.7（觀測 67.8、n=28、k=136、w=0.211）；short 78.0→75.6（觀測 65.5、n=17、k=94、w=0.194）；ft 94.8→87.3（觀測 71.5、n=18、k=45、w=0.320）；tovSkill 96.9→96.2（觀測 90.2、n=68、k=966、w=0.111）；pass 54.3→52.7（觀測 49.6、n=114、k=249、w=0.347）；rebound 82.6→82.4（觀測 81.7、n=114、k=464、w=0.236）；stamina 95.7→80.5（觀測 75.6、n=4、k=1、w=0.757）；creation 69.4→60.6（觀測 46.7、n=114、k=207、w=0.387）
