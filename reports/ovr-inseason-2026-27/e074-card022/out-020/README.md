# inseason 0.2.0 2026-27 即時結果（資料截至 2026-10-27）

- OVR：賽中 C4（inseason 0.2.0），先驗 card 0.2.0（live/prior-2025-26-card012.json）；N = 該球員 2026-27 已打場數。
- 資料：2026-10-20..2026-10-27、56 場、55 份 PBP；缺 PBP：0022600101。
- git HEAD：`175e26ad8563`；c=1.0（凍結）、G=82、f = min(N/82, 1)。
- 排名 362 人（有先驗卡且已出賽）；沒有先驗卡 55 人（`no-prior.csv`，不給 OVR）；有先驗卡但 2026-27 還沒出賽 220 人（不列入）。
- N 分布：N=1: 44 人, N=2: 34 人, N=3: 119 人, N=4: 165 人。
- 3PT 欄 = threeValue（R-024，顯示用、不進 OVR）：vol＝合併（2025-26＋2026-27）3PA/MIN×36；acc＝(k·上季 abilityC＋本季 3PM)/(k＋本季 3PA)，k=294.667（本季沒有出手難度資料，用原始命中）；rep＝合併聯盟 3P%（0.3589）−0.03；value＝vol×(acc−rep)，在合併 MIN≥500 且有先驗卡的 314 人池內取百分位並套 attr()。`long` 欄仍在 ranking.csv 並進 OVR 計算，只是表格不顯示。
- card 0.1.2 的屬性處理：foulDraw 用舊 drive 的同一個原始量（FTA/FGA 百分位）做 C4 更新；drive（改 PBP 版）、onBall（E-060 重定義）、pressure、help、physique、heightInches 凍結。
- 降級的資料層見 `../README.md`。`simulatedPer36` 空白（此流程不跑模擬）。
- `lastOVR` = 同一逐點管線對先驗卡算出的 OVR（ΔOVR 的基準）；`formalOVR` = card 0.2.0 `ranking.csv` 同名球員的 OVR（只供對照）。
- OVR 為每場（R-028，E-064 副版）：g = (預測每 36 分鐘淨值 − r_repl)·MPG_hat/36，r_repl＝-2.0148（替補水準 PR10），兩段映射錨點 PR1/PR50/PR99＝-0.6605/1.2369/4.7694（card 0.2.0 summary.json 同組）。MPG_hat = MPG0 + w·(本季場均分鐘 − MPG0)，w＝stamina 的 C4 w（stamina 最小樣本 1 場）；沒有本季視窗紀錄的 220 人（含沒出賽者，不在排名內）退回 MPG0。`ovrPer36` 是同一預測的每 36 分鐘 OVR。

## 檢查 (a)：f=0、k 取上界 → 與上季卡一致（c4_v5 T1 同款）

| 項目 | 結果 |
|---|---|
| 逐球員 \|OVR 差\| 最大值（門檻 <0.5） | 0.050463 → 通過 |
| 本檔 live_predict 與 c4_v5.c4_predict（f=0, k 上界）屬性最大差 | 0.000e+00 |
| 本檔 live_predict（f=0, c=1）與 fit_w_grid_v4.c2_predict 屬性最大差（T2 同款，門檻 1e-9） | 2.842e-14 |
| 逐點管線 A 參考與原管線差（建構時檢查，門檻 1e-8） | 9.24e-12 |
| 重建的 2025-26 映射 vs 上季卡 long／ft 最大差（只由 box 決定，應接近 0） | 0.050 ／ 22.577 |
| lastOVR vs 正式卡 OVR（同名 362 人）最大差 | 0.5999999999999943 |

## 檢查 (b)：ΔOVR = 賽中 OVR − lastOVR

- 人數 362；\|ΔOVR\| 中位數 1.961、平均 2.388、最大 11.603。
- \|ΔOVR\| >= 1.0 的人：255 人：Shai Gilgeous-Alexander（N=4，-5.61）、Franz Wagner（N=3，+2.56）、Derrick White（N=4，-3.25）、Evan Mobley（N=3，+1.27）、Donovan Mitchell（N=3，+1.44）、Victor Wembanyama（N=4，-1.20）、Kevin Durant（N=4，-3.45）、Kawhi Leonard（N=2，-6.20）、Joel Embiid（N=3，+1.06）、Lauri Markkanen（N=4，-7.92）、Amen Thompson（N=4，-2.14）、Dean Wade（N=2，+6.19）、Anthony Davis（N=4，+1.28）、Aaron Gordon（N=3，+1.58）、Jayson Tatum（N=4，+3.67）、Moussa Diabaté（N=4，+1.80）、Desmond Bane（N=3，-2.09）、Zion Williamson（N=3，+1.88）、Ty Jerome（N=4，+7.44）、Scottie Barnes（N=3，-2.98）、Anthony Edwards（N=4，-1.50）、Dylan Harper（N=4，+5.43）、Dyson Daniels（N=4，-2.67）、Davion Mitchell（N=4，+2.97）、Pascal Siakam（N=4，-1.11）、Stephen Curry（N=3，-4.37）、Mikal Bridges（N=4，-2.66）、Deni Avdija（N=3，-1.26）、Ryan Rollins（N=4，-3.71）、Jrue Holiday（N=3，-2.25）、Jalen Williams（N=3，+1.90）、Jalen Suggs（N=3，+2.79）、Marcus Smart（N=2，-2.58）、Brandin Podziemski（N=2，+2.57）、Jaden McDaniels（N=4，+1.08）、Immanuel Quickley（N=3，-2.50）、Toumani Camara（N=3，-4.72）、Derrick Jones Jr.（N=3，+2.59）、Karl-Anthony Towns（N=4，+1.31）、Zach LaVine（N=4，+2.86）、Herbert Jones（N=3，-8.58）、Neemias Queta（N=4，-5.67）、Christian Braun（N=3，+1.62）、Michael Porter Jr.（N=4，-2.29）、Nickeil Alexander-Walker（N=4，-1.96）、Domantas Sabonis（N=4，+5.01）、Cedric Coward（N=3，+2.82）、Jaren Jackson Jr.（N=4，-2.40）、Darius Garland（N=3，+2.71）、Jalen Brunson（N=4，-2.49）、Kris Dunn（N=3，+2.69）、James Harden（N=3，-1.29）、Dejounte Murray（N=3，+4.64）、Jaylen Brown（N=4，-1.63）、Jonathan Kuminga（N=4，+3.38）、Pelle Larsson（N=4，+2.15）、Naz Reid（N=4，+2.32）、Trey Murphy III（N=3，-2.34）、VJ Edgecombe（N=3，-1.29）、Walker Kessler（N=4，-1.93）、Cooper Flagg（N=3，-1.96）、Rui Hachimura（N=3，+1.25）、Trae Young（N=4，+9.87）、Cameron Johnson（N=1，-6.55）、Sion James（N=4，+2.05）、Onyeka Okongwu（N=4，-3.20）、Peyton Watson（N=3，+1.78）、Norman Powell（N=4，-2.13）、Andrew Wiggins（N=4，-3.12）、Keegan Murray（N=2，-3.85）、Alperen Sengun（N=4，+1.01）、Zach Edey（N=3，-3.01）、Obi Toppin（N=4，+2.68）、Ivica Zubac（N=3，-6.77）、Collin Gillespie（N=3，-3.37）、Kentavious Caldwell-Pope（N=4，+2.70）、Josh Giddey（N=4，-5.04）、Day'Ron Sharpe（N=4，+1.13）、Miles McBride（N=4，-4.31）、Paul Reed（N=4，+5.30）、Payton Pritchard（N=4，-5.33）、Oso Ighodaro（N=1，-2.19）、Jalen Duren（N=2，-5.34）、Matisse Thybulle（N=4，+3.99）、P.J. Washington（N=4，+2.75）、DeMar DeRozan（N=3，-2.84）、Saddiq Bey（N=3，-3.82）、Luke Kornet（N=4，-3.79）、Donovan Clingan（N=3，-2.55）、Keon Ellis（N=4，+3.89）、Jaylen Wells（N=4，+1.68）、Collin Murray-Boyles（N=3，-1.24）、Jakob Poeltl（N=3，-1.15）、Sam Hauser（N=4，-1.94）、AJ Green（N=4，-6.79）、Ayo Dosunmu（N=4，-1.05）、Duncan Robinson（N=4，+1.18）、Cason Wallace（N=3，-4.95）、Aaron Nesmith（N=3，-4.81）、Kris Murray（N=1，-2.57）、Kyle Kuzma（N=4，+4.03）、Ja'Kobe Walter（N=3，+2.96）、Jaime Jaquez Jr.（N=4，+1.48）、Isaiah Joe（N=3，-3.50）、Josh Okogie（N=3，-2.21）、Isaiah Stewart（N=3，-2.40）、Egor Dëmin（N=4，-1.22）、Keldon Johnson（N=4，-1.06）、Svi Mykhailiuk（N=4，-3.33）、Kelly Oubre Jr.（N=4，-4.93）、Gui Santos（N=4，+3.45）、Cam Spencer（N=4，-3.71）、Kenrich Williams（N=4，-3.03）、Luguentz Dort（N=4，-2.30）、CJ McCollum（N=4，-3.16）、Jordan Goodwin（N=3，-1.47）、Ronald Holland II（N=4，-2.74）、Jaylon Tyson（N=3，-2.93）、Daniss Jenkins（N=4，+3.81）、LaMelo Ball（N=4，-3.43）、Jaylin Williams（N=4，-2.56）、Al Horford（N=3，-2.27）、Tre Jones（N=4，-6.02）、Sidy Cissoko（N=3，+3.48）、Justin Champagnie（N=4，-1.01）、Keyonte George（N=4，+2.15）、Goga Bitadze（N=2，-2.45）、Baylor Scheierman（N=4，-1.13）、Jock Landale（N=4，-3.01）、Quentin Grimes（N=4，-3.92）、Kasparas Jakučionis（N=4，+3.89）、Jose Alvarado（N=2，-3.59）、Matas Buzelis（N=4，-3.78）、Isaac Okoro（N=4，-6.03）、Leonard Miller（N=4，+2.37）、Khaman Maluach（N=3，+8.60）、Karlo Matković（N=2，-4.86）、Jaxson Hayes（N=3，+3.32）、Isaiah Jackson（N=3，+2.97）、Luke Kennard（N=2，-2.49）、Kevin Huerter（N=4，-2.25）、Jevon Carter（N=1，-1.38）、Dennis Schröder（N=4，+5.37）、Joan Beringer（N=4，+4.95）、Adem Bona（N=4，-1.74）、Tim Hardaway Jr.（N=4，-6.87）、Marvin Bagley III（N=3，-6.56）、Nique Clifford（N=3，-9.82）、Jay Huff（N=3，-2.67）、Ryan Dunn（N=3，-3.33）、Clint Capela（N=3，-4.61）、Josh Minott（N=3，-5.08）、Grayson Allen（N=4，-2.40）、Scotty Pippen Jr.（N=4，-2.40）、Collin Sexton（N=3，-4.10）、Kel'el Ware（N=4，-2.05）、Kyle Anderson（N=2，-6.62）、Danny Wolf（N=1，-1.79）、Steven Adams（N=1，-5.18）、Nikola Vučević（N=3，-11.60）、Luka Garza（N=4，-5.21）、Daeqwon Plowden（N=4，-7.91）、Zach Collins（N=3，-6.76）、Aaron Wiggins（N=4，+4.58）、Bennedict Mathurin（N=3，-8.58）、Ace Bailey（N=4，+1.09）、Precious Achiuwa（N=4，+1.01）、Terrence Shannon Jr（N=4，+3.52）、Jared McCain（N=4，+1.96）、Jerami Grant（N=4，-4.84）、Anthony Gill（N=1，-6.24）、Jamal Shead（N=3，-1.64）、Bogdan Bogdanović（N=4，-2.64）、Ziaire Williams（N=4，+3.16）、Tristan da Silva（N=3，+1.72）、Ryan Kalkbrenner（N=4，-2.03）、Harrison Barnes（N=4，-11.26）、Dru Smith（N=2，-2.35）、Hugo González（N=4，-1.99）、Jalen Slawson（N=3，-8.49）、Kevon Looney（N=4，-4.82）、Noa Essengue（N=3，+5.89）、Marcus Sasser（N=4，+3.22）、Charles Bassey（N=2，-2.22）、Asa Newell（N=2，-4.38）、Ousmane Dieng（N=3，-2.01）、Zaccharie Risacher（N=4，+3.59）、Micah Potter（N=1，-1.39）、LJ Cryer（N=3，-3.50）、Tony Bradley（N=1，-1.57）、Ben Sheppard（N=1，-1.74）、Jalen Pickett（N=1，-3.81）、GG Jackson（N=4，-2.32）、Kyle Filipowski（N=3，-6.11）、Duop Reath（N=3，-1.05）、Liam McNeeley（N=2，-1.66）、Malik Monk（N=3，-3.02）、Ron Harper Jr.（N=1，-1.05）、Zeke Nnaji（N=1，-2.21）、Malevy Leons（N=3，-3.14）、Vít Krejčí（N=3，-4.37）、Jamison Battle（N=3，+1.19）、Mo Bamba（N=1，+2.97）、Bilal Coulibaly（N=4，-1.41）、Jalen Green（N=3，+1.96）、Myron Gardner（N=2，-3.42）、Anfernee Simons（N=4，-2.67）、Jase Richardson（N=3，+1.04）、Brandon Williams（N=4，-2.26）、Tolu Smith（N=3，-3.58）、Zyon Pullin（N=1，-1.05）、Jabari Walker（N=3，-2.26）、Craig Porter Jr.（N=2，-2.90）、DaRon Holmes II（N=2，-2.91）、Trayce Jackson-Davis（N=3，-1.67）、Will Richard（N=4，-1.21）、Deandre Ayton（N=4，-5.55）、Bones Hyland（N=4，-2.77）、Jaylen Clark（N=3，-3.80）、Elijah Harkless（N=1，-2.40）、Jae'Sean Tate（N=3，-5.21）、Rasheer Fleming（N=2，-1.08）、Taurean Prince（N=1，-2.10）、Dorian Finney-Smith（N=2，-2.74）、Jake LaRavia（N=3，-2.70）、David Jones Garcia（N=1，-1.86）、Mohamed Diawara（N=1，-1.90）、Brice Sensabaugh（N=4，-2.65）、Simone Fontecchio（N=2，-2.67）、Cam Christie（N=1，-1.25）、Moussa Cisse（N=3，-2.68）、Jamaree Bouyea（N=2，-1.53）、Scoot Henderson（N=3，-1.92）、Isaiah Crawford（N=3，-2.48）、Brooks Barnhizer（N=3，-2.55）、Khris Middleton（N=3，-1.87）、Leaky Black（N=2，-3.72）、Nick Richards（N=2，+1.27）、Will Riley（N=3，+1.47）、James Wiseman（N=3，+1.83）、Chaz Lanier（N=1，+1.08）、Tre Mann（N=1，+1.74）、Royce O'Neale（N=4，-1.29）、Jordan Clarkson（N=3，+3.59）、Jordan Poole（N=3，-1.22）、Noah Clowney（N=4，-1.57）、Caleb Love（N=1，+3.34）、Bub Carrington（N=4，-2.03）、Jordan Hawkins（N=1，+1.26）、Reed Sheppard（N=3，-1.53）、Tyus Jones（N=3，+1.96）、Cody Williams（N=3，+7.99）、Jaden Hardy（N=1，+2.06）、Ben Saraf（N=1，+3.49）、Nolan Traore（N=4，+2.30）。
- 有屬性被更新的（屬性：人次）：stamina 249, short 123, tovSkill 114, ft 108, pass 91, creation 90, rebound 88, long 61, foulDraw 42, mid 10。

依 N 分組的 \|ΔOVR\|：

| N | 人數 | 中位數 | 最大 |
|---|---|---|---|
| 1 | 44 | 1.254 | 6.546 |
| 2 | 34 | 2.470 | 6.623 |
| 3 | 119 | 2.088 | 11.603 |
| 4 | 165 | 2.031 | 11.264 |

ΔOVR 最高 10 人：

| 球員 | 隊 | N | lastOVR | OVR | ΔOVR |
|---|---|---|---|---|---|
| Trae Young | WAS | 4 | 67.5 | 77.4 | +9.87 |
| Khaman Maluach | PHX | 3 | 56.9 | 65.5 | +8.60 |
| Cody Williams | MIN | 3 | 35.8 | 43.8 | +7.99 |
| Ty Jerome | MEM | 4 | 77.9 | 85.4 | +7.44 |
| Dean Wade | PHI | 2 | 82.5 | 88.7 | +6.19 |
| Noa Essengue | CHI | 3 | 52.7 | 58.5 | +5.89 |
| Dylan Harper | SAS | 4 | 79.1 | 84.6 | +5.43 |
| Dennis Schröder | CHA | 4 | 59.0 | 64.4 | +5.37 |
| Paul Reed | DET | 4 | 69.3 | 74.6 | +5.30 |
| Domantas Sabonis | SAC | 4 | 74.9 | 79.9 | +5.01 |

ΔOVR 最低 10 人：

| 球員 | 隊 | N | lastOVR | OVR | ΔOVR |
|---|---|---|---|---|---|
| Nikola Vučević | ORL | 3 | 73.7 | 62.0 | -11.60 |
| Harrison Barnes | SAS | 4 | 70.5 | 59.2 | -11.26 |
| Nique Clifford | SAC | 3 | 73.3 | 63.4 | -9.82 |
| Bennedict Mathurin | NOP | 3 | 69.7 | 61.1 | -8.58 |
| Herbert Jones | NOP | 3 | 89.5 | 80.9 | -8.58 |
| Jalen Slawson | IND | 3 | 67.4 | 58.9 | -8.49 |
| Lauri Markkanen | UTA | 4 | 98.7 | 90.8 | -7.93 |
| Daeqwon Plowden | SAC | 4 | 69.7 | 61.7 | -7.91 |
| Tim Hardaway Jr. | MIA | 4 | 70.8 | 63.9 | -6.87 |
| AJ Green | MIL | 4 | 78.1 | 71.4 | -6.79 |

\|ΔOVR\| 最大 10 人的屬性變動明細（x0→x̂；觀測 y 已做 usage 調整）：

- Nikola Vučević（ORL，N=3，ΔOVR -11.60）：stamina 75.0→50.7（觀測 40.0、n=3、k=1、w=0.695）
- Harrison Barnes（SAS，N=4，ΔOVR -11.26）：stamina 62.8→45.6（觀測 40.0、n=4、k=1、w=0.754）
- Trae Young（WAS，N=4，ΔOVR +9.87）：long 63.5→62.7（觀測 61.7、n=30、k=47、w=0.419）；short 47.0→55.9（觀測 70.9、n=23、k=45、w=0.371）；ft 85.0→77.0（觀測 70.7、n=36、k=31、w=0.559）；tovSkill 46.7→63.3（觀測 93.5、n=130、k=274、w=0.355）；stamina 61.5→90.3（觀測 99.0、n=4、k=1、w=0.767）；creation 90.0→85.1（觀測 80.6、n=147、k=148、w=0.522）；foulDraw 97.2→98.0（觀測 98.9、n=61、k=74、w=0.480）
- Nique Clifford（SAC，N=3，ΔOVR -9.82）：stamina 60.6→51.1（觀測 46.9、n=3、k=1、w=0.694）
- Khaman Maluach（PHX，N=3，ΔOVR +8.60）：stamina 40.0→49.1（觀測 53.0、n=3、k=1、w=0.697）
- Bennedict Mathurin（NOP，N=3，ΔOVR -8.58）：stamina 81.9→52.7（觀測 40.0、n=3、k=1、w=0.696）
- Herbert Jones（NOP，N=3，ΔOVR -8.58）：stamina 74.6→50.5（觀測 40.0、n=3、k=1、w=0.696）
- Jalen Slawson（IND，N=3，ΔOVR -8.49）：stamina 56.4→44.8（觀測 40.0、n=3、k=1、w=0.709）
- Cody Williams（MIN，N=3，ΔOVR +7.99）：stamina 58.5→45.6（觀測 40.0、n=3、k=1、w=0.695）
- Lauri Markkanen（UTA，N=4，ΔOVR -7.93）：long 66.4→66.7（觀測 67.8、n=28、k=136、w=0.211）；short 78.0→75.6（觀測 65.5、n=17、k=94、w=0.194）；ft 94.8→87.3（觀測 71.5、n=18、k=45、w=0.320）；tovSkill 96.9→96.2（觀測 90.2、n=68、k=966、w=0.111）；pass 54.3→52.7（觀測 49.6、n=114、k=249、w=0.347）；rebound 82.6→82.4（觀測 81.7、n=114、k=464、w=0.236）；stamina 95.7→80.5（觀測 75.6、n=4、k=1、w=0.757）；creation 69.4→60.6（觀測 46.7、n=114、k=207、w=0.387）
