# inseason 0.2.2 2026-27 即時結果（資料截至 2026-10-28）

- OVR：賽中 C4（inseason 0.2.2），先驗 card 0.2.4（live/prior-2025-26-card022.json）；N = 該球員 2026-27 已打場數。
- 資料：2026-10-20..2026-10-28、68 場、67 份 PBP；缺 PBP：0022600101。
- git HEAD：`7dd87d07810f`；c=1.0（凍結）、G=82、f = min(N/82, 1)。
- 排名 368 人（有先驗卡且已出賽）；沒有先驗卡 57 人（`no-prior.csv`，不給 OVR）；有先驗卡但 2026-27 還沒出賽 214 人（不列入）。
- N 分布：N=1: 38 人, N=2: 36 人, N=3: 51 人, N=4: 122 人, N=5: 121 人。
- 3PT 欄 = threeValue（R-024，顯示用、不進 OVR）：vol＝合併（2025-26＋2026-27）3PA/MIN×36；acc＝(k·上季 abilityC＋本季 3PM)/(k＋本季 3PA)，k=294.667（本季沒有出手難度資料，用原始命中）；rep＝合併聯盟 3P%（0.3588）−0.03；value＝vol×(acc−rep)，在合併 MIN≥500 且有先驗卡的 321 人池內取百分位並套 attr()。`long` 欄仍在 ranking.csv 並進 OVR 計算，只是表格不顯示。
- card 0.2.4（能力值欄與 0.2.2 逐欄相同） 的屬性處理（E-074，換版不重擬合）：先驗屬性 x0、屬性迴歸係數（card-0.2.2/cards/P1/primary/summary.json）取自 card 0.2.2；pressure＝逼失誤 force（E-071 P1），賽中凍結；foulDraw 用 E-070 公式做 C4 更新：y＝百分位(0.75·z(FTA/36)＋0.25·z(FTA/FGA))，z 的平均／標準差與百分位對照母體凍結自 2025-26 池（GP≥30、MPG≥20，252 人；FTA/36 mean 3.7493 std 1.9723、FTA/FGA mean 0.2639 std 0.1057），不用 2026-27 資料重估，收縮 k／δ²／rel 沿用 drive 的；drive（PBP 版）、onBall（E-060）、pressure、help、physique、heightInches 凍結。PRES 欄顯示 presDisplay、tooltip 列逼失誤與犯規紀律（2025-26，不進 OVR）。
- 降級的資料層見 `../README.md`。`simulatedPer36` 空白（此流程不跑模擬）。
- `lastOVR` = 同一逐點管線對先驗卡算出的 OVR（ΔOVR 的基準）；`formalOVR` = card 0.2.4 `ranking.csv` 同名球員的 OVR（只供對照）。
- OVR 為每場（R-028，E-064 副版）：g = (預測每 36 分鐘淨值 − r_repl)·MPG_hat/36，r_repl＝-1.2724（替補水準 PR10），兩段映射錨點 PR1/PR50/PR99＝-0.5415/0.8849/3.1778（card 0.2.4 E-084 results.json 的 card 段 同組）。MPG_hat = MPG0 + w·(本季場均分鐘 − MPG0)，w＝stamina 的 C4 w（stamina 最小樣本 1 場）；沒有本季視窗紀錄的 214 人（含沒出賽者，不在排名內）退回 MPG0。`ovrPer36` 是同一預測的每 36 分鐘 OVR。
- card 0.2.4 用人層（E-089，R-044 = 用人回歸＋當季 RAPM 目標）：p＝上面屬性迴歸的每 36 預測（`predictedPer36`，C4 照常更新），predNew＝b0 + b1·p + b2·L + b3·a + b4·y + b5·v + b6·y·L + b7·v·L + b8·y·d·L（`predNew` 欄）；L、a、y、v、d 與 has 旗標凍結在 2025-26 全季（`usage-2025-26-card024.json`，payload sha256 9c6b0c3ea52b…，年齡不加一歲），has=False 或不在卡內者 predNew＝p；係數 b0=-1.2093、b1=0.5395（E-084 results.json）。MPG0＝card 0.2.4 ranking.csv 的 mpg 欄（mpgAvail，依名字配對），卡裡沒有的人退回 MIN／GP。

## 檢查 (a)：f=0、k 取上界 → 與上季卡一致（c4_v5 T1 同款）

| 項目 | 結果 |
|---|---|
| 逐球員 \|OVR 差\| 最大值（門檻 <0.5） | 0.044355 → 通過 |
| 本檔 live_predict 與 c4_v5.c4_predict（f=0, k 上界）屬性最大差 | 0.000e+00 |
| 本檔 live_predict（f=0, c=1）與 fit_w_grid_v4.c2_predict 屬性最大差（T2 同款，門檻 1e-9） | 2.842e-14 |
| 逐點管線 A 參考與原管線差（建構時檢查，門檻 1e-8） | 9.68e-12 |
| 重建的 2025-26 映射 vs 上季卡 long／ft 最大差（只由 box 決定，應接近 0） | 0.050 ／ 22.577 |
| lastOVR vs 正式卡 OVR（同名 368 人）最大差 | 0.10000000000000853 |

## 檢查 (b)：ΔOVR = 賽中 OVR − lastOVR

- 人數 368；\|ΔOVR\| 中位數 1.691、平均 2.286、最大 11.210。
- \|ΔOVR\| >= 1.0 的人：232 人：Shai Gilgeous-Alexander（N=5，-4.29）、Franz Wagner（N=4，+3.17）、Victor Wembanyama（N=5，+1.92）、Amen Thompson（N=5，-3.13）、Derrick White（N=4，-3.64）、Cade Cunningham（N=5，+1.07）、Joel Embiid（N=4，+1.94）、Tyrese Maxey（N=5，-1.26）、Kawhi Leonard（N=2，-4.32）、Jayson Tatum（N=4，+3.90）、Kevin Durant（N=5，-5.02）、Dylan Harper（N=5，+8.88）、Lauri Markkanen（N=4，-7.53）、Dyson Daniels（N=5，-3.66）、Zion Williamson（N=4，+1.41）、Aaron Gordon（N=4，+1.94）、Anthony Edwards（N=4，-1.51）、Desmond Bane（N=4，-2.13）、Scottie Barnes（N=4，-2.39）、Ty Jerome（N=4，+7.71）、Anthony Davis（N=5，+1.27）、Brandin Podziemski（N=3，+3.28）、VJ Edgecombe（N=4，-2.25）、Alperen Sengun（N=4，+1.13）、Davion Mitchell（N=5，+3.59）、Stephen Curry（N=4，-3.73）、Dean Wade（N=3，+3.64）、Jalen Brunson（N=5，-2.12）、Ryan Rollins（N=5，-6.43）、Michael Porter Jr.（N=4，-2.23）、Jalen Williams（N=3，+1.98）、Jalen Suggs（N=3，+3.15）、Moussa Diabaté（N=5，+3.03）、Brandon Miller（N=5，+2.17）、Immanuel Quickley（N=4，-2.15）、Christian Braun（N=4，+2.12）、Nickeil Alexander-Walker（N=5，-2.15）、Toumani Camara（N=3，-5.35）、Walker Kessler（N=5，-1.70）、Jalen Johnson（N=5，-1.22）、Derrick Jones Jr.（N=4，+3.00）、Trey Murphy III（N=4，-3.36）、Jrue Holiday（N=3，-2.27）、Deni Avdija（N=3，-1.26）、Jaren Jackson Jr.（N=4，-2.77）、Onyeka Okongwu（N=5，-3.45）、Peyton Watson（N=4，+1.59）、Dejounte Murray（N=4，+3.55）、Herbert Jones（N=4，-8.98）、Marcus Smart（N=2，-2.61）、Sion James（N=5，+2.08）、Josh Giddey（N=5，-4.86）、Mikal Bridges（N=5，-6.34）、Pelle Larsson（N=5，+2.70）、Keegan Murray（N=2，-4.45）、Neemias Queta（N=4，-5.54）、Jonathan Kuminga（N=5，+10.02）、Rui Hachimura（N=3，+1.48）、Domantas Sabonis（N=4，+4.72）、Darius Garland（N=4，+1.45）、Cameron Johnson（N=1，-7.33）、Trae Young（N=5，+7.69）、Zach LaVine（N=4，+2.35）、Kris Dunn（N=4，+1.94）、RJ Barrett（N=4，+1.21）、James Harden（N=4，-2.48）、Jalen Smith（N=5，+2.05）、Jalen Duren（N=2，-6.25）、Collin Gillespie（N=3，-3.50）、John Collins（N=5，-1.34）、Ja'Kobe Walter（N=4，+4.56）、Anthony Black（N=2，-2.37）、Oso Ighodaro（N=1，-2.78）、Ivica Zubac（N=3，-5.86）、Paul Reed（N=5，+11.21）、Donovan Clingan（N=3，-2.87）、Payton Pritchard（N=4，-5.18）、Daniel Gafford（N=5，+1.09）、Matas Buzelis（N=5，-2.35）、P.J. Washington（N=5，+2.09）、Sandro Mamukelashvili（N=5，+1.04）、Cason Wallace（N=3，-5.94）、Zach Edey（N=3，-2.94）、Day'Ron Sharpe（N=4，+1.32）、LaMelo Ball（N=5，-2.96）、Miles McBride（N=5，-5.75）、Sam Merrill（N=4，-1.21）、Duncan Robinson（N=5，+1.94）、Obi Toppin（N=5，+1.89）、Collin Murray-Boyles（N=4，-2.36）、Landry Shamet（N=5，+1.29）、Jaime Jaquez Jr.（N=5，+1.03）、Saddiq Bey（N=4，-4.73）、Kelly Oubre Jr.（N=5，-5.67）、Sam Hauser（N=4，-2.19）、Brook Lopez（N=4，+1.54）、Keon Ellis（N=4，+3.99）、Kentavious Caldwell-Pope（N=5，+2.25）、Grayson Allen（N=5，-1.05）、Matisse Thybulle（N=5，+5.07）、Jaylon Tyson（N=4，-3.59）、Aaron Nesmith（N=4，-4.77）、Andrew Wiggins（N=5，-3.32）、Gui Santos（N=4，+3.73）、DeMar DeRozan（N=4，-3.58）、Sidy Cissoko（N=3，+3.59）、Jaxson Hayes（N=4，+7.18）、Jakob Poeltl（N=4，-3.43）、Kasparas Jakučionis（N=5，+7.47）、Zaccharie Risacher（N=5，+4.72）、Luguentz Dort（N=5，-1.41）、Quentin Grimes（N=5，-1.51）、AJ Green（N=5，-6.70）、Tre Jones（N=5，-6.33）、Kris Murray（N=1，-2.82）、Daniss Jenkins（N=5，+6.15）、Jaylin Williams（N=5，-1.71）、Ronald Holland II（N=5，-3.38）、Luke Kornet（N=5，-3.84）、Jordan Walsh（N=4，+2.54）、Isaiah Joe（N=3，-4.03）、Cam Spencer（N=4，-3.67）、Kyle Kuzma（N=5，+1.77）、Kel'el Ware（N=5，-1.95）、Isaiah Stewart（N=3，-2.21）、Jordan Goodwin（N=3，-1.09）、Aaron Wiggins（N=5，+5.46）、Keldon Johnson（N=5，-1.16）、Precious Achiuwa（N=4，+1.98）、Jamal Shead（N=4，-1.25）、Tristan da Silva（N=4，+2.57）、Luke Kennard（N=2，-2.25）、Isaac Okoro（N=5，-5.64）、Al Horford（N=4，-2.45）、Bobby Portis Jr.（N=5，-1.88）、Jalen Green（N=3，+1.83）、Kevin Huerter（N=5，-1.20）、Jose Alvarado（N=2，-3.06）、CJ McCollum（N=5，-4.55）、Ryan Dunn（N=3，-3.17）、Scoot Henderson（N=3，-3.72）、Quenton Jackson（N=5，+2.37）、Dennis Schröder（N=5，+5.06）、Reed Sheppard（N=4，-3.34）、Jared McCain（N=5，+4.15）、Jay Huff（N=4，-3.31）、Kenrich Williams（N=5，-1.11）、Ziaire Williams（N=4，+4.52）、Collin Sexton（N=4，-4.60）、Marvin Bagley III（N=4，-4.85）、Jock Landale（N=5，-3.29）、Karlo Matković（N=3，-1.71）、Isaiah Jackson（N=4，+3.07）、Leonard Miller（N=5，+6.02）、Scotty Pippen Jr.（N=4，-1.47）、Adem Bona（N=5，-2.83）、Will Richard（N=5，-1.63）、Gary Payton II（N=5，-1.06）、Nique Clifford（N=3，-9.73）、Kobe Sanders（N=4，+1.84）、Josh Minott（N=3，-1.70）、Ryan Kalkbrenner（N=5，-3.05）、Zach Collins（N=3，-6.93）、Steven Adams（N=1，-4.54）、Jake LaRavia（N=4，-2.13）、Bennedict Mathurin（N=4，-8.35）、Jevon Carter（N=2，+3.01）、Tim Hardaway Jr.（N=5，-5.77）、Terrence Shannon Jr（N=5，+5.69）、Nikola Vučević（N=4，-10.88）、Jarred Vanderbilt（N=1，+2.02）、Cedric Coward（N=3，+2.12）、Ben Sheppard（N=1，-2.50）、Luka Garza（N=4，-3.09）、Kyshawn George（N=5，+2.86）、Hugo González（N=4，-1.46）、Joan Beringer（N=5，+6.48）、Jerami Grant（N=4，-3.94）、Chaney Johnson（N=4，+5.67）、Deandre Ayton（N=5，-8.47）、Jalen Slawson（N=4，-3.65）、Micah Potter（N=1，-1.60）、Harrison Barnes（N=4，-10.52）、Dru Smith（N=3，-1.30）、Brandon Williams（N=5，-3.19）、Moritz Wagner（N=4，+2.37）、Anfernee Simons（N=5，-3.89）、Vít Krejčí（N=3，-5.55）、Leaky Black（N=2，-10.46）、Larry Nance Jr.（N=5，+3.15）、Khaman Maluach（N=3，+5.47）、Marcus Sasser（N=5，+4.31）、Khris Middleton（N=4，-2.82）、Gradey Dick（N=4，+1.26）、Malik Monk（N=3，-2.67）、Jamal Cain（N=4，+2.66）、Kyle Anderson（N=3，-2.73）、Craig Porter Jr.（N=2，-3.38）、Buddy Hield（N=5，+1.17）、Jabari Walker（N=3，-1.68）、Bogdan Bogdanović（N=5，+1.94）、Trayce Jackson-Davis（N=4，+1.12）、Jaylen Clark（N=4，-3.85）、Anthony Gill（N=1，-2.96）、Bones Hyland（N=5，-1.72）、Jase Richardson（N=4，+1.93）、Jaylen Wells（N=4，+1.29）、Egor Dëmin（N=4，-1.79）、Corey Kispert（N=2，-2.65）、Justin Edwards（N=1，-2.68）、Simone Fontecchio（N=2，-3.14）、Kevon Looney（N=4，+1.31）、Taurean Prince（N=2，-3.19）、Jalen Pickett（N=2，-1.29）、Jamison Battle（N=4，+1.20）、Dorian Finney-Smith（N=2，-1.72）、Mohamed Diawara（N=1，-1.45）、Klay Thompson（N=5，-1.06）、Royce O'Neale（N=5，-4.71）、Jae'Sean Tate（N=4，-2.31）、Noa Essengue（N=4，+2.08）、Jett Howard（N=2，-1.12）、Kobe Brown（N=2，-1.73）、Caleb Love（N=1，+1.35）、Keyonte George（N=5，+1.72）、Ryan Nembhard（N=2，+3.51）、Walter Clayton Jr.（N=4，+1.59）、Will Riley（N=3，+6.90）、Ben Saraf（N=1，+2.32）、Cody Williams（N=3，+8.43）、Jaden Hardy（N=2，+1.71）、Drake Powell（N=1，+1.47）。
- 有屬性被更新的（屬性：人次）：stamina 253, tovSkill 153, short 146, pass 141, rebound 138, creation 138, ft 126, long 101, foulDraw 70, mid 14。

依 N 分組的 \|ΔOVR\|：

| N | 人數 | 中位數 | 最大 |
|---|---|---|---|
| 1 | 38 | 0.516 | 7.334 |
| 2 | 36 | 1.208 | 10.458 |
| 3 | 51 | 1.830 | 9.726 |
| 4 | 122 | 1.934 | 10.881 |
| 5 | 121 | 1.878 | 11.210 |

ΔOVR 最高 10 人：

| 球員 | 隊 | N | lastOVR | OVR | ΔOVR |
|---|---|---|---|---|---|
| Paul Reed | DET | 5 | 64.7 | 75.9 | +11.21 |
| Jonathan Kuminga | MIN | 5 | 69.7 | 79.7 | +10.02 |
| Dylan Harper | SAS | 5 | 81.6 | 90.5 | +8.88 |
| Cody Williams | MIN | 3 | 36.2 | 44.6 | +8.43 |
| Ty Jerome | MEM | 4 | 79.9 | 87.6 | +7.70 |
| Trae Young | WAS | 5 | 70.4 | 78.1 | +7.69 |
| Kasparas Jakučionis | MIL | 5 | 64.5 | 72.0 | +7.47 |
| Jaxson Hayes | UTA | 4 | 64.9 | 72.1 | +7.18 |
| Will Riley | WAS | 3 | 39.2 | 46.1 | +6.90 |
| Joan Beringer | MIN | 5 | 54.3 | 60.7 | +6.48 |

ΔOVR 最低 10 人：

| 球員 | 隊 | N | lastOVR | OVR | ΔOVR |
|---|---|---|---|---|---|
| Nikola Vučević | ORL | 4 | 72.9 | 62.0 | -10.88 |
| Harrison Barnes | SAS | 4 | 70.4 | 59.9 | -10.52 |
| Leaky Black | SAC | 2 | 69.4 | 59.0 | -10.46 |
| Nique Clifford | SAC | 3 | 73.9 | 64.2 | -9.73 |
| Herbert Jones | NOP | 4 | 89.9 | 80.9 | -8.98 |
| Deandre Ayton | WAS | 5 | 69.0 | 60.5 | -8.47 |
| Bennedict Mathurin | NOP | 4 | 70.7 | 62.3 | -8.35 |
| Lauri Markkanen | UTA | 4 | 97.8 | 90.3 | -7.53 |
| Cameron Johnson | DEN | 1 | 85.7 | 78.4 | -7.33 |
| Zach Collins | CHI | 3 | 69.9 | 63.0 | -6.93 |

\|ΔOVR\| 最大 10 人的屬性變動明細（x0→x̂；觀測 y 已做 usage 調整）：

- Paul Reed（DET，N=5，ΔOVR +11.21）：short 85.6→83.2（觀測 77.6、n=29、k=85、w=0.300）；ft 56.1→59.8（觀測 68.0、n=13、k=36、w=0.309）；tovSkill 56.2→53.5（觀測 40.4、n=68、k=498、w=0.173）；pass 64.4→65.0（觀測 65.9、n=130、k=226、w=0.404）；rebound 96.1→95.2（觀測 93.0、n=130、k=389、w=0.296）；stamina 40.0→58.8（觀測 63.7、n=5、k=1、w=0.796）；creation 59.8→55.0（觀測 48.9、n=130、k=191、w=0.442）
- Nikola Vučević（ORL，N=4，ΔOVR -10.88）：stamina 75.0→48.6（觀測 40.0、n=4、k=1、w=0.755）
- Harrison Barnes（SAS，N=4，ΔOVR -10.52）：stamina 62.8→45.6（觀測 40.0、n=4、k=1、w=0.754）
- Leaky Black（SAC，N=2，ΔOVR -10.46）：stamina 76.6→62.4（觀測 53.5、n=2、k=1、w=0.616）
- Jonathan Kuminga（MIN，N=5，ΔOVR +10.02）：long 61.8→67.4（觀測 76.9、n=21、k=43、w=0.371）；short 67.8→64.5（觀測 56.6、n=25、k=76、w=0.294）；ft 57.2→59.2（觀測 61.7、n=19、k=28、w=0.443）；tovSkill 58.5→70.6（觀測 99.0、n=74、k=219、w=0.299）；pass 68.2→67.0（觀測 65.4、n=151、k=221、w=0.442）；rebound 86.3→81.1（觀測 70.5、n=151、k=375、w=0.331）；stamina 54.1→76.4（觀測 82.0、n=5、k=1、w=0.799）；creation 81.9→69.9（觀測 56.9、n=151、k=187、w=0.480）；foulDraw 89.8→88.2（觀測 86.2、n=50、k=76、w=0.432）
- Nique Clifford（SAC，N=3，ΔOVR -9.73）：stamina 60.6→51.1（觀測 46.9、n=3、k=1、w=0.694）
- Herbert Jones（NOP，N=4，ΔOVR -8.98）：stamina 74.6→48.5（觀測 40.0、n=4、k=1、w=0.755）
- Dylan Harper（SAS，N=5，ΔOVR +8.88）：short 69.6→70.5（觀測 72.0、n=46、k=95、w=0.367）；ft 68.9→69.6（觀測 71.1、n=13、k=37、w=0.304）；tovSkill 73.6→76.0（觀測 88.7、n=111、k=964、w=0.158）；pass 88.0→86.5（觀測 84.5、n=161、k=253、w=0.427）；rebound 65.5→66.6（觀測 69.3、n=161、k=475、w=0.299）；stamina 52.1→77.7（觀測 84.3、n=5、k=1、w=0.796）；creation 90.3→91.9（觀測 93.8、n=161、k=209、w=0.469）；foulDraw 59.9→59.7（觀測 59.4、n=74、k=130、w=0.402）
- Deandre Ayton（WAS，N=5，ΔOVR -8.47）：short 85.4→84.4（觀測 80.4、n=19、k=102、w=0.209）；stamina 70.6→46.3（觀測 40.0、n=5、k=1、w=0.795）
- Cody Williams（MIN，N=3，ΔOVR +8.43）：stamina 58.5→45.6（觀測 40.0、n=3、k=1、w=0.695）
