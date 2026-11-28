# inseason 0.2.1 2026-27 即時結果（資料截至 2026-10-27）

- OVR：賽中 C4（inseason 0.2.1），先驗 card 0.2.2（live/prior-2025-26-card022.json）；N = 該球員 2026-27 已打場數。
- 資料：2026-10-20..2026-10-27、56 場、55 份 PBP；缺 PBP：0022600101。
- git HEAD：`175e26ad8563`；c=1.0（凍結）、G=82、f = min(N/82, 1)。
- 排名 362 人（有先驗卡且已出賽）；沒有先驗卡 55 人（`no-prior.csv`，不給 OVR）；有先驗卡但 2026-27 還沒出賽 220 人（不列入）。
- N 分布：N=1: 44 人, N=2: 34 人, N=3: 119 人, N=4: 165 人。
- 3PT 欄 = threeValue（R-024，顯示用、不進 OVR）：vol＝合併（2025-26＋2026-27）3PA/MIN×36；acc＝(k·上季 abilityC＋本季 3PM)/(k＋本季 3PA)，k=294.667（本季沒有出手難度資料，用原始命中）；rep＝合併聯盟 3P%（0.3589）−0.03；value＝vol×(acc−rep)，在合併 MIN≥500 且有先驗卡的 314 人池內取百分位並套 attr()。`long` 欄仍在 ranking.csv 並進 OVR 計算，只是表格不顯示。
- card 0.2.2 的屬性處理（E-074，換版不重擬合）：先驗屬性 x0、迴歸係數（card-0.2.2/cards/P1/primary/summary.json）、每場錨點與 r_repl 全部取自 card 0.2.2；pressure＝逼失誤 force（E-071 P1），賽中凍結；foulDraw 用 E-070 公式做 C4 更新：y＝百分位(0.75·z(FTA/36)＋0.25·z(FTA/FGA))，z 的平均／標準差與百分位對照母體凍結自 2025-26 池（GP≥30、MPG≥20，252 人；FTA/36 mean 3.7493 std 1.9723、FTA/FGA mean 0.2639 std 0.1057），不用 2026-27 資料重估，收縮 k／δ²／rel 沿用 drive 的；drive（PBP 版）、onBall（E-060）、pressure、help、physique、heightInches 凍結。PRES 欄顯示 presDisplay、tooltip 列逼失誤與犯規紀律（2025-26，不進 OVR）。
- 降級的資料層見 `../README.md`。`simulatedPer36` 空白（此流程不跑模擬）。
- `lastOVR` = 同一逐點管線對先驗卡算出的 OVR（ΔOVR 的基準）；`formalOVR` = card 0.2.2 `ranking.csv` 同名球員的 OVR（只供對照）。
- OVR 為每場（R-028，E-064 副版）：g = (預測每 36 分鐘淨值 − r_repl)·MPG_hat/36，r_repl＝-1.7593（替補水準 PR10），兩段映射錨點 PR1/PR50/PR99＝-0.7564/1.0495/4.7440（card 0.2.2 P1 primary 的 pergame-summary.json 同組）。MPG_hat = MPG0 + w·(本季場均分鐘 − MPG0)，w＝stamina 的 C4 w（stamina 最小樣本 1 場）；沒有本季視窗紀錄的 220 人（含沒出賽者，不在排名內）退回 MPG0。`ovrPer36` 是同一預測的每 36 分鐘 OVR。

## 檢查 (a)：f=0、k 取上界 → 與上季卡一致（c4_v5 T1 同款）

| 項目 | 結果 |
|---|---|
| 逐球員 \|OVR 差\| 最大值（門檻 <0.5） | 0.042536 → 通過 |
| 本檔 live_predict 與 c4_v5.c4_predict（f=0, k 上界）屬性最大差 | 0.000e+00 |
| 本檔 live_predict（f=0, c=1）與 fit_w_grid_v4.c2_predict 屬性最大差（T2 同款，門檻 1e-9） | 2.842e-14 |
| 逐點管線 A 參考與原管線差（建構時檢查，門檻 1e-8） | 9.68e-12 |
| 重建的 2025-26 映射 vs 上季卡 long／ft 最大差（只由 box 決定，應接近 0） | 0.050 ／ 22.577 |
| lastOVR vs 正式卡 OVR（同名 362 人）最大差 | 0.10000000000000853 |

## 檢查 (b)：ΔOVR = 賽中 OVR − lastOVR

- 人數 362；\|ΔOVR\| 中位數 1.703、平均 2.141、最大 10.332。
- \|ΔOVR\| >= 1.0 的人：243 人：Shai Gilgeous-Alexander（N=4，-3.63）、Franz Wagner（N=3，+2.44）、Derrick White（N=4，-3.55）、Kawhi Leonard（N=2，-4.23）、Joel Embiid（N=3，+1.00）、Kevin Durant（N=4，-3.56）、Victor Wembanyama（N=4，-1.02）、Amen Thompson（N=4，-2.01）、Tyrese Maxey（N=4，-1.38）、Jayson Tatum（N=4，+3.58）、Dean Wade（N=2，+5.68）、Lauri Markkanen（N=4，-7.19）、Anthony Davis（N=4，+1.05）、Paul George（N=4，+1.02）、Zion Williamson（N=3，+1.85）、Ty Jerome（N=4，+6.99）、Aaron Gordon（N=3，+1.42）、Stephen Curry（N=3，-5.54）、Desmond Bane（N=3，-2.18）、Dylan Harper（N=4，+6.02）、Anthony Edwards（N=4，-1.41）、Scottie Barnes（N=3，-2.71）、Pascal Siakam（N=4，-1.07）、Jrue Holiday（N=3，-2.10）、Davion Mitchell（N=4，+2.67）、Dyson Daniels（N=4，-2.33）、Marcus Smart（N=2，-2.41）、Jalen Williams（N=3，+1.57）、Herbert Jones（N=3，-7.55）、Jalen Brunson（N=4，-2.45）、Ryan Rollins（N=4，-3.24）、Jalen Suggs（N=3，+2.43）、Walker Kessler（N=4，-1.00）、Mikal Bridges（N=4，-2.27）、Toumani Camara（N=3，-4.19）、Michael Porter Jr.（N=4，-2.45）、Immanuel Quickley（N=3，-1.59）、Derrick Jones Jr.（N=3，+2.34）、Moussa Diabaté（N=4，+1.37）、Neemias Queta（N=4，-5.10）、Brandin Podziemski（N=2，+2.22）、Nickeil Alexander-Walker（N=4，-1.74）、Karl-Anthony Towns（N=4，+1.04）、Jaren Jackson Jr.（N=4，-2.17）、Onyeka Okongwu（N=4，-3.12）、Christian Braun（N=3，+1.34）、Dejounte Murray（N=3，+3.90）、Trey Murphy III（N=3，-1.90）、VJ Edgecombe（N=3，-1.19）、Kris Dunn（N=3，+2.38）、Jaylen Brown（N=4，-1.38）、Alperen Sengun（N=4，+1.06）、James Harden（N=3，-1.38）、Pelle Larsson（N=4，+1.97）、Naz Reid（N=4，+1.95）、Tari Eason（N=4，-1.13）、Cameron Johnson（N=1，-5.82）、Sion James（N=4，+1.86）、Cooper Flagg（N=3，-1.71）、Zach LaVine（N=4，+2.01）、Jonathan Kuminga（N=4，+3.30）、Keegan Murray（N=2，-3.61）、Rui Hachimura（N=3，+1.06）、Paul Reed（N=4，+4.77）、Darius Garland（N=3，+1.87）、Obi Toppin（N=4，+2.26）、Collin Gillespie（N=3，-3.07）、Cedric Coward（N=3，+2.13）、Miles McBride（N=4，-3.88）、Norman Powell（N=4，-1.54）、Trae Young（N=4，+9.48）、Kyshawn George（N=4，+1.92）、Kentavious Caldwell-Pope（N=4，+2.27）、Domantas Sabonis（N=4，+3.86）、Ivica Zubac（N=3，-5.33）、Oso Ighodaro（N=1，-1.96）、Peyton Watson（N=3，+1.57）、Zach Edey（N=3，-2.46）、Josh Giddey（N=4，-4.12）、Duncan Robinson（N=4，+1.08）、Andrew Wiggins（N=4，-2.38）、Jalen Duren（N=2，-4.74）、Keon Ellis（N=4，+2.76）、Jakob Poeltl（N=3，-1.06）、Matisse Thybulle（N=4，+3.21）、LaMelo Ball（N=4，-2.44）、DeMar DeRozan（N=3，-2.56）、Gui Santos（N=4，+1.87）、Sam Hauser（N=4，-1.80）、Collin Murray-Boyles（N=3，-1.04）、Payton Pritchard（N=4，-4.41）、Cason Wallace（N=3，-3.74）、Kasparas Jakučionis（N=4，+2.83）、Luke Kornet（N=4，-2.85）、Ja'Kobe Walter（N=3，+2.69）、Saddiq Bey（N=3，-3.50）、Josh Okogie（N=3，-2.01）、P.J. Washington（N=4，+4.15）、Isaiah Joe（N=3，-3.24）、Kris Murray（N=1，-2.17）、Jaylin Williams（N=4，-1.63）、Kelly Oubre Jr.（N=4，-4.45）、Jaylen Wells（N=4，+1.95）、Tre Jones（N=4，-4.86）、Donovan Clingan（N=3，-1.93）、Jaime Jaquez Jr.（N=4，+1.30）、Kenrich Williams（N=4，-2.27）、Aaron Nesmith（N=3，-3.89）、Cam Spencer（N=4，-2.95）、AJ Green（N=4，-5.41）、Ronald Holland II（N=4，-2.08）、Grayson Allen（N=4，-1.42）、Al Horford（N=3，-1.50）、Daniss Jenkins（N=4，+3.60）、Goga Bitadze（N=2，-1.53）、Isaiah Stewart（N=3，-2.34）、Jordan Goodwin（N=3，-1.80）、Sidy Cissoko（N=3，+3.33）、Egor Dëmin（N=4，-2.60）、Jose Alvarado（N=2，-2.66）、Baylor Scheierman（N=4，-1.03）、CJ McCollum（N=4，-3.53）、Luguentz Dort（N=4，-2.76）、Jaylon Tyson（N=3，-3.25）、Matas Buzelis（N=4，-3.34）、Luke Kennard（N=2，-2.45）、Karlo Matković（N=2，-4.11）、Kevin Huerter（N=4，-2.21）、Josh Minott（N=3，-4.64）、Leonard Miller（N=4，+1.83）、Keldon Johnson（N=4，-1.65）、Jaxson Hayes（N=3，+3.11）、Svi Mykhailiuk（N=4，-4.40）、Clint Capela（N=3，-4.59）、Marvin Bagley III（N=3，-5.52）、Jalen Slawson（N=3，-8.14）、Jevon Carter（N=1，-1.21）、Aaron Wiggins（N=4，+5.09）、Jay Huff（N=3，-2.59）、Kyle Kuzma（N=4，+3.71）、Isaac Okoro（N=4，-6.07）、Isaiah Jackson（N=3，+2.39）、Quentin Grimes（N=4，-4.13）、De'Anthony Melton（N=4，-1.02）、Keyonte George（N=4，+1.63）、Steven Adams（N=1，-5.01）、Ryan Dunn（N=3，-2.87）、Precious Achiuwa（N=4，+1.29）、Zach Collins（N=3，-6.51）、Scotty Pippen Jr.（N=4，-2.10）、Kel'el Ware（N=4，-1.92）、Kyle Anderson（N=2，-6.11）、Jock Landale（N=4，-2.27）、Nique Clifford（N=3，-8.67）、Luka Garza（N=4，-4.81）、Collin Sexton（N=3，-3.69）、Adem Bona（N=4，-1.32）、Joan Beringer（N=4，+3.48）、Dennis Schröder（N=4，+4.37）、Nikola Vučević（N=3，-10.33）、Daeqwon Plowden（N=4，-7.16）、Danny Wolf（N=1，-1.43）、Bogdan Bogdanović（N=4，-2.43）、Kevon Looney（N=4，-4.84）、Ziaire Williams（N=4，+3.15）、Tristan da Silva（N=3，+1.66）、Moritz Wagner（N=4，+1.22）、Zaccharie Risacher（N=4，+3.69）、Ryan Kalkbrenner（N=4，-1.83）、Harrison Barnes（N=4，-10.16）、Marcus Sasser（N=4，+3.12）、Anthony Gill（N=1，-5.04）、Dru Smith（N=2，-2.01）、Tim Hardaway Jr.（N=4，-6.20）、Jalen Green（N=3，+2.06）、Terrence Shannon Jr（N=4，+2.40）、Jamal Shead（N=3，-1.50）、Noa Essengue（N=3，+4.53）、Jared McCain（N=4，+1.29）、Charles Bassey（N=2，-1.68）、Hugo González（N=4，-1.32）、Vít Krejčí（N=3，-4.49）、Myron Gardner（N=2，-3.78）、Will Richard（N=4，-1.51）、Malevy Leons（N=3，-3.12）、Micah Potter（N=1，-1.03）、Brice Sensabaugh（N=4，-3.71）、Asa Newell（N=2，-3.01）、Jaylen Clark（N=3，-5.09）、Khaman Maluach（N=3，+3.23）、Ben Sheppard（N=1，-1.41）、Mo Bamba（N=1，+2.80）、Trayce Jackson-Davis（N=3，-1.79）、Kyle Filipowski（N=3，-4.88）、Craig Porter Jr.（N=2，-2.60）、Jalen Pickett（N=1，-2.50）、Scoot Henderson（N=3，-2.31）、Rasheer Fleming（N=2，-1.20）、Zeke Nnaji（N=1，-1.57）、Moussa Cisse（N=3，-4.17）、Jabari Walker（N=3，-1.71）、David Jones Garcia（N=1，-1.99）、Deandre Ayton（N=4，-5.10）、LJ Cryer（N=3，-1.62）、GG Jackson（N=4，-1.45）、Jae'Sean Tate（N=3，-4.77）、Bennedict Mathurin（N=3，-5.77）、Khris Middleton（N=3，-2.29）、Tolu Smith（N=3，-2.25）、Jerami Grant（N=4，-3.95）、Elijah Harkless（N=1，-1.94）、DaRon Holmes II（N=2，-1.69）、Brandon Williams（N=4，-1.70）、Dorian Finney-Smith（N=2，-1.93）、Leaky Black（N=2，-5.35）、Bones Hyland（N=4，-1.32）、Cam Whitmore（N=2，-1.01）、Malik Monk（N=3，-1.39）、Simone Fontecchio（N=2，-1.76）、Jake LaRavia（N=3，-2.32）、Isaiah Crawford（N=3，-1.72）、Reed Sheppard（N=3，-2.13）、Brooks Barnhizer（N=3，-1.34）、Anfernee Simons（N=4，-2.30）、Ryan Nembhard（N=2，+2.40）、Nick Richards（N=2，+2.30）、James Wiseman（N=3，+3.27）、Chaz Lanier（N=1，+1.33）、Royce O'Neale（N=4，-1.59）、Will Riley（N=3，+5.62）、Tre Mann（N=1，+2.97）、Jordan Clarkson（N=3，+4.38）、Jericho Sims（N=1，+3.28）、Cody Williams（N=3，+6.79）、Drake Powell（N=1，+1.16）、Noah Clowney（N=4，-1.39）、Ben Saraf（N=1，+3.09）、Jordan Poole（N=3，-1.07）、Caleb Love（N=1，+5.69）、Jordan Hawkins（N=1，+2.05）、Tyus Jones（N=3，+2.46）、Jaden Hardy（N=1，+2.77）、Nolan Traore（N=4，+2.97）。
- 有屬性被更新的（屬性：人次）：stamina 249, short 123, tovSkill 114, ft 108, pass 91, creation 90, rebound 88, long 61, foulDraw 41, mid 10。

依 N 分組的 \|ΔOVR\|：

| N | 人數 | 中位數 | 最大 |
|---|---|---|---|
| 1 | 44 | 0.996 | 5.816 |
| 2 | 34 | 1.970 | 6.106 |
| 3 | 119 | 1.871 | 10.332 |
| 4 | 165 | 1.653 | 10.156 |

ΔOVR 最高 10 人：

| 球員 | 隊 | N | lastOVR | OVR | ΔOVR |
|---|---|---|---|---|---|
| Trae Young | WAS | 4 | 65.1 | 74.6 | +9.48 |
| Ty Jerome | MEM | 4 | 79.8 | 86.8 | +6.99 |
| Cody Williams | MIN | 3 | 40.0 | 46.7 | +6.79 |
| Dylan Harper | SAS | 4 | 78.6 | 84.7 | +6.02 |
| Caleb Love | PHI | 1 | 39.1 | 44.7 | +5.69 |
| Dean Wade | PHI | 2 | 82.5 | 88.2 | +5.68 |
| Will Riley | WAS | 3 | 42.6 | 48.2 | +5.61 |
| Aaron Wiggins | ATL | 4 | 60.0 | 65.1 | +5.09 |
| Paul Reed | DET | 4 | 71.2 | 76.0 | +4.77 |
| Noa Essengue | CHI | 3 | 54.3 | 58.8 | +4.53 |

ΔOVR 最低 10 人：

| 球員 | 隊 | N | lastOVR | OVR | ΔOVR |
|---|---|---|---|---|---|
| Nikola Vučević | ORL | 3 | 72.4 | 62.1 | -10.33 |
| Harrison Barnes | SAS | 4 | 70.3 | 60.1 | -10.16 |
| Nique Clifford | SAC | 3 | 71.9 | 63.2 | -8.67 |
| Jalen Slawson | IND | 3 | 73.4 | 65.3 | -8.14 |
| Herbert Jones | NOP | 3 | 88.8 | 81.3 | -7.55 |
| Lauri Markkanen | UTA | 4 | 95.3 | 88.1 | -7.19 |
| Daeqwon Plowden | SAC | 4 | 68.8 | 61.6 | -7.16 |
| Zach Collins | CHI | 3 | 70.0 | 63.5 | -6.51 |
| Tim Hardaway Jr. | MIA | 4 | 66.1 | 59.9 | -6.20 |
| Kyle Anderson | TOR | 2 | 69.5 | 63.4 | -6.11 |

\|ΔOVR\| 最大 10 人的屬性變動明細（x0→x̂；觀測 y 已做 usage 調整）：

- Nikola Vučević（ORL，N=3，ΔOVR -10.33）：stamina 75.0→50.7（觀測 40.0、n=3、k=1、w=0.695）
- Harrison Barnes（SAS，N=4，ΔOVR -10.16）：stamina 62.8→45.6（觀測 40.0、n=4、k=1、w=0.754）
- Trae Young（WAS，N=4，ΔOVR +9.48）：long 63.5→62.7（觀測 61.7、n=30、k=47、w=0.419）；short 47.0→55.9（觀測 70.9、n=23、k=45、w=0.371）；ft 85.0→77.0（觀測 70.7、n=36、k=31、w=0.559）；tovSkill 46.7→63.3（觀測 93.5、n=130、k=274、w=0.355）；stamina 61.5→90.3（觀測 99.0、n=4、k=1、w=0.767）；creation 90.0→85.1（觀測 80.6、n=147、k=148、w=0.522）；foulDraw 97.7→97.9（觀測 98.2、n=61、k=74、w=0.480）
- Nique Clifford（SAC，N=3，ΔOVR -8.67）：stamina 60.6→51.1（觀測 46.9、n=3、k=1、w=0.694）
- Jalen Slawson（IND，N=3，ΔOVR -8.14）：stamina 56.4→44.8（觀測 40.0、n=3、k=1、w=0.709）
- Herbert Jones（NOP，N=3，ΔOVR -7.55）：stamina 74.6→50.5（觀測 40.0、n=3、k=1、w=0.696）
- Lauri Markkanen（UTA，N=4，ΔOVR -7.19）：long 66.4→66.7（觀測 67.8、n=28、k=136、w=0.211）；short 78.0→75.6（觀測 65.5、n=17、k=94、w=0.194）；ft 94.8→87.3（觀測 71.5、n=18、k=45、w=0.320）；tovSkill 96.9→96.2（觀測 90.2、n=68、k=966、w=0.111）；pass 54.3→52.7（觀測 49.6、n=114、k=249、w=0.347）；rebound 82.6→82.4（觀測 81.7、n=114、k=464、w=0.236）；stamina 95.7→80.5（觀測 75.6、n=4、k=1、w=0.757）；creation 69.4→60.6（觀測 46.7、n=114、k=207、w=0.387）
- Daeqwon Plowden（SAC，N=4，ΔOVR -7.16）：stamina 66.0→46.3（觀測 40.0、n=4、k=1、w=0.759）
- Ty Jerome（MEM，N=4，ΔOVR +6.99）：long 81.2→77.8（觀測 70.3、n=27、k=70、w=0.313）；short 60.9→65.3（觀測 72.1、n=30、k=53、w=0.392）；ft 88.7→81.0（觀測 75.1、n=33、k=28、w=0.567）；tovSkill 82.0→86.5（觀測 96.7、n=127、k=339、w=0.307）；pass 97.7→98.0（觀測 98.3、n=126、k=159、w=0.469）；rebound 54.5→51.8（觀測 47.5、n=126、k=226、w=0.389）；stamina 52.3→76.9（觀測 84.4、n=4、k=1、w=0.767）；creation 98.9→98.9（觀測 99.0、n=126、k=141、w=0.498）；foulDraw 83.9→90.0（觀測 96.5、n=79、k=92、w=0.488）
- Cody Williams（MIN，N=3，ΔOVR +6.79）：stamina 58.5→45.6（觀測 40.0、n=3、k=1、w=0.695）
