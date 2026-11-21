# inseason 0.2.5 2026-27 即時結果（資料截至 2026-10-28）

- OVR：賽中 C4（inseason 0.2.5），先驗 card 0.2.5（live/prior-2025-26-card022.json）；N = 該球員 2026-27 已打場數。
- 資料：2026-10-20..2026-10-28、68 場、67 份 PBP；缺 PBP：0022600101。
- git HEAD：`5acd8a0b6eb5`；c=1.0（凍結）、G=82、f = min(N/82, 1)。
- 排名 368 人（有先驗卡且已出賽）；沒有先驗卡 57 人（`no-prior.csv`，不給 OVR）；有先驗卡但 2026-27 還沒出賽 214 人（不列入）。
- N 分布：N=1: 38 人, N=2: 36 人, N=3: 51 人, N=4: 122 人, N=5: 121 人。
- 3PT 欄 = threeValue（R-024，顯示用、不進 OVR）：vol＝合併（2025-26＋2026-27）3PA/MIN×36；acc＝(k·上季 abilityC＋本季 3PM)/(k＋本季 3PA)，k=294.667（本季沒有出手難度資料，用原始命中）；rep＝合併聯盟 3P%（0.3588）−0.03；value＝vol×(acc−rep)，在合併 MIN≥500 且有先驗卡的 321 人池內取百分位並套 attr()。`long` 欄仍在 ranking.csv 並進 OVR 計算，只是表格不顯示。
- card 0.2.5（能力值欄與 0.2.2 逐欄相同） 的屬性處理（E-074，換版不重擬合）：先驗屬性 x0、屬性迴歸係數（card-0.2.2/cards/P1/primary/summary.json）取自 card 0.2.2；pressure＝逼失誤 force（E-071 P1），賽中凍結；foulDraw 用 E-070 公式做 C4 更新：y＝百分位(0.75·z(FTA/36)＋0.25·z(FTA/FGA))，z 的平均／標準差與百分位對照母體凍結自 2025-26 池（GP≥30、MPG≥20，252 人；FTA/36 mean 3.7493 std 1.9723、FTA/FGA mean 0.2639 std 0.1057），不用 2026-27 資料重估，收縮 k／δ²／rel 沿用 drive 的；drive（PBP 版）、onBall（E-060）、pressure、help、physique、heightInches 凍結。PRES 欄顯示 presDisplay、tooltip 列逼失誤與犯規紀律（2025-26，不進 OVR）。
- 降級的資料層見 `../README.md`。`simulatedPer36` 空白（此流程不跑模擬）。
- `lastOVR` = 同一逐點管線對先驗卡算出的 OVR（ΔOVR 的基準）；`formalOVR` = card 0.2.5 `ranking.csv` 同名球員的 OVR（只供對照）。
- OVR 為每場（R-028，E-064 副版）：g = (預測每 36 分鐘淨值 − r_repl)·MPG_hat/36，r_repl＝-1.2724（替補水準 PR10），兩段映射錨點 PR1/PR50/PR99＝-0.8153/1.2506/3.4429（card 0.2.5 E-089 results.json 的 report_only.card.new（card 0.2.5） 同組）。MPG_hat = MPG0 + w·(本季場均分鐘 − MPG0)，w＝stamina 的 C4 w（stamina 最小樣本 1 場）；沒有本季視窗紀錄的 214 人（含沒出賽者，不在排名內）退回 MPG0。`ovrPer36` 是同一預測的每 36 分鐘 OVR。
- card 0.2.4 用人層（E-091，R-044 = 用人回歸＋當季 RAPM 目標）：p＝上面屬性迴歸的每 36 預測（`predictedPer36`，C4 照常更新），predNew＝b0 + b1·p + b2·L + b3·a + b4·y + b5·v + b6·y·L + b7·v·L + b8·y·d·L（`predNew` 欄）；L、a、y、v、d 與 has 旗標凍結在 2025-26 全季（`usage-2025-26-card024.json`，payload sha256 9c6b0c3ea52b…，年齡不加一歲），has=False 或不在卡內者 predNew＝p；係數 b0=-1.2093、b1=0.5395（E-084 results.json）。MPG0＝card 0.2.4 ranking.csv 的 mpg 欄（mpgAvail，依名字配對），卡裡沒有的人退回 MIN／GP。
- E-095（CARD_MODE=025）：分鐘權重 mpg/36 改為飽和 W(mpg)=(1−e^(−mpg/15))/(1−e^(−36/15))（card 0.2.5，R-047），錨點／r_repl 取 E-089 results.json report_only.card.new。

## 檢查 (a)：f=0、k 取上界 → 與上季卡一致（c4_v5 T1 同款）

| 項目 | 結果 |
|---|---|
| 逐球員 \|OVR 差\| 最大值（門檻 <0.5） | 0.049252 → 通過 |
| 本檔 live_predict 與 c4_v5.c4_predict（f=0, k 上界）屬性最大差 | 0.000e+00 |
| 本檔 live_predict（f=0, c=1）與 fit_w_grid_v4.c2_predict 屬性最大差（T2 同款，門檻 1e-9） | 2.842e-14 |
| 逐點管線 A 參考與原管線差（建構時檢查，門檻 1e-8） | 9.68e-12 |
| 重建的 2025-26 映射 vs 上季卡 long／ft 最大差（只由 box 決定，應接近 0） | 0.050 ／ 22.577 |
| lastOVR vs 正式卡 OVR（同名 368 人）最大差 | 0.10000000000000853 |

## 檢查 (b)：ΔOVR = 賽中 OVR − lastOVR

- 人數 368；\|ΔOVR\| 中位數 1.151、平均 1.597、最大 8.649。
- \|ΔOVR\| >= 1.0 的人：200 人：Shai Gilgeous-Alexander（N=5，-4.57）、Nikola Jokić（N=4，-2.47）、Franz Wagner（N=4，+1.09）、Chet Holmgren（N=3，-1.32）、Derrick White（N=4，-1.15）、Kawhi Leonard（N=2，-1.59）、Lauri Markkanen（N=4，-4.62）、Dylan Harper（N=5，+5.08）、Dyson Daniels（N=5，-1.25）、Dean Wade（N=3，+2.02）、Evan Mobley（N=4，-1.31）、Jamal Murray（N=4，-1.59）、Jayson Tatum（N=4，+2.21）、Ty Jerome（N=4，+4.73）、Tyrese Maxey（N=5，-1.02）、Kevin Durant（N=5，-4.07）、Stephen Curry（N=4，-2.42）、Herbert Jones（N=4，-4.98）、Desmond Bane（N=4，-1.60）、Ryan Rollins（N=5，-4.08）、Brandin Podziemski（N=3，+1.79）、Neemias Queta（N=4，-4.05）、Toumani Camara（N=3，-1.97）、Davion Mitchell（N=5，+1.28）、Moussa Diabaté（N=5，+1.96）、Derrick Jones Jr.（N=4，+2.36）、Jaren Jackson Jr.（N=4，-1.13）、Marcus Smart（N=2，-1.19）、Michael Porter Jr.（N=4，-2.29）、Ja Morant（N=3，+1.38）、Jalen Brunson（N=5，-2.17）、Jalen Suggs（N=3，+1.21）、Walker Kessler（N=5，-1.78）、Onyeka Okongwu（N=5，-2.19）、Cameron Johnson（N=1，-3.54）、Oso Ighodaro（N=1，-1.95）、Josh Giddey（N=5，-3.05）、Mikal Bridges（N=5，-4.41）、Jonathan Kuminga（N=5，+7.73）、Jalen Duren（N=2，-4.44）、Jalen Smith（N=5，+1.56）、Peyton Watson（N=4，+1.04）、Trey Murphy III（N=4，-2.33）、Dejounte Murray（N=4，+2.35）、Jaylen Brown（N=5，-1.65）、Pelle Larsson（N=5，+1.31）、Keegan Murray（N=2，-2.34）、Cason Wallace（N=3，-3.57）、Miles McBride（N=5，-3.49）、Collin Gillespie（N=3，-2.56）、Collin Murray-Boyles（N=4，-1.68）、Paul Reed（N=5，+8.65）、Ja'Kobe Walter（N=4，+3.73）、Daniel Gafford（N=5，+1.17）、Ivica Zubac（N=3，-4.17）、Josh Hart（N=5，-1.70）、John Collins（N=5，-1.49）、Anthony Black（N=2，-1.01）、Zach Edey（N=3，-2.13）、Kris Dunn（N=4，+1.20）、Donovan Clingan（N=3，-1.97）、RJ Barrett（N=4，+1.15）、Domantas Sabonis（N=4，+3.09）、Brook Lopez（N=4，+1.04）、Sam Hauser（N=4，-1.67）、Matas Buzelis（N=5，-1.77）、Trae Young（N=5，+5.80）、Payton Pritchard（N=4，-3.67）、LaMelo Ball（N=5，-2.76）、Ronald Holland II（N=5，-2.88）、Matisse Thybulle（N=5，+3.32）、Zach LaVine（N=4，+1.09）、James Harden（N=4，-2.62）、Jaylon Tyson（N=4，-2.65）、Luke Kornet（N=5，-3.19）、Keon Ellis（N=4，+3.12）、Isaiah Joe（N=3，-3.32）、Saddiq Bey（N=4，-3.19）、Jaylin Williams（N=5，-1.38）、Jakob Poeltl（N=4，-2.65）、Kasparas Jakučionis（N=5，+5.16）、Kelly Oubre Jr.（N=5，-4.03）、Kris Murray（N=1，-1.95）、Kentavious Caldwell-Pope（N=5，+1.32）、Sidy Cissoko（N=3，+2.62）、Tre Jones（N=5，-4.80）、Aaron Nesmith（N=4，-3.16）、Gui Santos（N=4，+2.70）、Jordan Walsh（N=4，+1.66）、AJ Green（N=5，-4.72）、Duncan Robinson（N=5，+1.32）、Jaime Jaquez Jr.（N=5，+1.03）、P.J. Washington（N=5，+1.69）、Cam Spencer（N=4，-2.87）、Grayson Allen（N=5，-1.11）、Jaxson Hayes（N=4，+5.28）、Andrew Wiggins（N=5，-2.83）、Isaiah Stewart（N=3，-1.82）、Kel'el Ware（N=5，-1.66）、Daniss Jenkins（N=5，+4.37）、DeMar DeRozan（N=4，-2.90）、Jordan Goodwin（N=3，-1.01）、Jose Alvarado（N=2，-1.77）、Ryan Dunn（N=3，-1.85）、Zaccharie Risacher（N=5，+2.79）、Quentin Grimes（N=5，-1.13）、Karlo Matković（N=3，-1.24）、Luke Kennard（N=2，-1.30）、Keldon Johnson（N=5，-1.02）、Isaac Okoro（N=5，-3.82）、Marvin Bagley III（N=4，-2.98）、Al Horford（N=4，-1.36）、Quenton Jackson（N=5，+1.46）、Josh Minott（N=3，-1.45）、Jay Huff（N=4，-1.80）、Aaron Wiggins（N=5，+3.41）、Kyle Kuzma（N=5，+1.19）、Adem Bona（N=5，-1.93）、Nique Clifford（N=3，-6.37）、Scoot Henderson（N=3，-2.16）、Jock Landale（N=5，-1.97）、Collin Sexton（N=4，-2.83）、Zach Collins（N=3，-4.59）、Bobby Portis Jr.（N=5，-1.65）、Jared McCain（N=5，+1.97）、Tristan da Silva（N=4，+1.21）、Leonard Miller（N=5，+4.07）、Reed Sheppard（N=4，-2.15）、CJ McCollum（N=5，-3.56）、Jalen Green（N=3，+1.25）、Isaiah Jackson（N=4，+1.65）、Kobe Sanders（N=4，+1.05）、Luka Garza（N=4，-2.49）、Jevon Carter（N=2，+2.35）、Steven Adams（N=1，-2.60）、Ryan Kalkbrenner（N=5，-1.70）、Nikola Vučević（N=4，-6.65）、Ziaire Williams（N=4，+2.45）、Hugo González（N=4，-1.16）、Dennis Schröder（N=5，+2.56）、Jalen Slawson（N=4，-3.22）、Jarred Vanderbilt（N=1，+1.38）、Joan Beringer（N=5，+6.66）、Bennedict Mathurin（N=4，-4.53）、Ben Sheppard（N=1，-1.34）、Harrison Barnes（N=4，-6.24）、Tim Hardaway Jr.（N=5，-3.55）、Terrence Shannon Jr（N=5，+4.08）、Jake LaRavia（N=4，-1.24）、Deandre Ayton（N=5，-4.73）、Chaney Johnson（N=4，+4.79）、Vít Krejčí（N=3，-3.64）、Moritz Wagner（N=4，+1.66）、Larry Nance Jr.（N=5，+2.96）、Leaky Black（N=2，-5.50）、Brandon Williams（N=5，-1.95）、Cedric Coward（N=3，+1.18）、Kyle Anderson（N=3，-2.46）、Jerami Grant（N=4，-2.33）、Jamal Cain（N=4，+2.54）、Craig Porter Jr.（N=2，-2.54）、Khaman Maluach（N=3，+4.91）、Anfernee Simons（N=5，-3.20）、Jabari Walker（N=3，-1.74）、Malik Monk（N=3，-1.68）、Khris Middleton（N=4，-1.70）、Kyshawn George（N=5，+1.95）、Marcus Sasser（N=5，+3.35）、Jaylen Clark（N=4，-3.95）、Trayce Jackson-Davis（N=4，+1.23）、Anthony Gill（N=1，-2.84）、Bogdan Bogdanović（N=5，+1.79）、Bones Hyland（N=5，-1.35）、Jase Richardson（N=4，+1.80）、Justin Edwards（N=1，-2.63）、Corey Kispert（N=2，-1.92）、Simone Fontecchio（N=2，-2.70）、Kevon Looney（N=4，+1.68）、Jalen Pickett（N=2，-1.34）、Myron Gardner（N=2，-1.18）、Mohamed Diawara（N=1，-1.74）、Egor Dëmin（N=4，-1.34）、Dorian Finney-Smith（N=2，-1.57）、Taurean Prince（N=2，-2.03）、Jae'Sean Tate（N=4，-3.09）、Jamison Battle（N=4，+1.16）、Noa Essengue（N=4，+2.71）、Jett Howard（N=2，-1.22）、Royce O'Neale（N=5，-3.41）、Kobe Brown（N=2，-1.75）、Jordan Poole（N=4，-1.12）、Jonathan Mogbo（N=3，-1.12）、Keyonte George（N=5，+1.26）、Caleb Love（N=1，+1.19）、Ryan Nembhard（N=2，+3.00）、Will Riley（N=3，+4.90）、Ben Saraf（N=1，+2.05）、Cody Williams（N=3，+5.07）、Jaden Hardy（N=2，+1.55）、Bub Carrington（N=5，-1.35）。
- 有屬性被更新的（屬性：人次）：stamina 253, tovSkill 153, short 146, pass 141, rebound 138, creation 138, ft 126, long 101, foulDraw 70, mid 14。

依 N 分組的 \|ΔOVR\|：

| N | 人數 | 中位數 | 最大 |
|---|---|---|---|
| 1 | 38 | 0.455 | 3.542 |
| 2 | 36 | 1.187 | 5.500 |
| 3 | 51 | 1.252 | 6.366 |
| 4 | 122 | 1.142 | 6.653 |
| 5 | 121 | 1.283 | 8.649 |

ΔOVR 最高 10 人：

| 球員 | 隊 | N | lastOVR | OVR | ΔOVR |
|---|---|---|---|---|---|
| Paul Reed | DET | 5 | 68.9 | 77.6 | +8.65 |
| Jonathan Kuminga | MIN | 5 | 72.3 | 80.0 | +7.73 |
| Joan Beringer | MIN | 5 | 56.5 | 63.1 | +6.66 |
| Trae Young | WAS | 5 | 68.8 | 74.6 | +5.80 |
| Jaxson Hayes | UTA | 4 | 66.1 | 71.4 | +5.28 |
| Kasparas Jakučionis | MIL | 5 | 68.0 | 73.2 | +5.16 |
| Dylan Harper | SAS | 5 | 86.0 | 91.1 | +5.08 |
| Cody Williams | MIN | 3 | 37.7 | 42.8 | +5.07 |
| Khaman Maluach | PHX | 3 | 54.6 | 59.6 | +4.91 |
| Will Riley | WAS | 3 | 39.5 | 44.4 | +4.90 |

ΔOVR 最低 10 人：

| 球員 | 隊 | N | lastOVR | OVR | ΔOVR |
|---|---|---|---|---|---|
| Nikola Vučević | ORL | 4 | 70.9 | 64.3 | -6.65 |
| Nique Clifford | SAC | 3 | 73.7 | 67.3 | -6.37 |
| Harrison Barnes | SAS | 4 | 68.7 | 62.4 | -6.24 |
| Leaky Black | SAC | 2 | 66.4 | 60.9 | -5.50 |
| Herbert Jones | NOP | 4 | 91.9 | 87.0 | -4.98 |
| Tre Jones | CHI | 5 | 77.7 | 72.9 | -4.80 |
| Deandre Ayton | WAS | 5 | 66.6 | 61.9 | -4.73 |
| AJ Green | MIL | 5 | 77.2 | 72.4 | -4.72 |
| Lauri Markkanen | UTA | 4 | 95.7 | 91.1 | -4.62 |
| Zach Collins | CHI | 3 | 71.2 | 66.6 | -4.59 |

\|ΔOVR\| 最大 10 人的屬性變動明細（x0→x̂；觀測 y 已做 usage 調整）：

- Paul Reed（DET，N=5，ΔOVR +8.65）：short 85.6→83.2（觀測 77.6、n=29、k=85、w=0.300）；ft 56.1→59.8（觀測 68.0、n=13、k=36、w=0.309）；tovSkill 56.2→53.5（觀測 40.4、n=68、k=498、w=0.173）；pass 64.4→65.0（觀測 65.9、n=130、k=226、w=0.404）；rebound 96.1→95.2（觀測 93.0、n=130、k=389、w=0.296）；stamina 40.0→58.8（觀測 63.7、n=5、k=1、w=0.796）；creation 59.8→55.0（觀測 48.9、n=130、k=191、w=0.442）
- Jonathan Kuminga（MIN，N=5，ΔOVR +7.73）：long 61.8→67.4（觀測 76.9、n=21、k=43、w=0.371）；short 67.8→64.5（觀測 56.6、n=25、k=76、w=0.294）；ft 57.2→59.2（觀測 61.7、n=19、k=28、w=0.443）；tovSkill 58.5→70.6（觀測 99.0、n=74、k=219、w=0.299）；pass 68.2→67.0（觀測 65.4、n=151、k=221、w=0.442）；rebound 86.3→81.1（觀測 70.5、n=151、k=375、w=0.331）；stamina 54.1→76.4（觀測 82.0、n=5、k=1、w=0.799）；creation 81.9→69.9（觀測 56.9、n=151、k=187、w=0.480）；foulDraw 89.8→88.2（觀測 86.2、n=50、k=76、w=0.432）
- Joan Beringer（MIN，N=5，ΔOVR +6.66）：short 86.2→82.5（觀測 75.4、n=22、k=52、w=0.339）
- Nikola Vučević（ORL，N=4，ΔOVR -6.65）：stamina 75.0→48.6（觀測 40.0、n=4、k=1、w=0.755）
- Nique Clifford（SAC，N=3，ΔOVR -6.37）：stamina 60.6→51.1（觀測 46.9、n=3、k=1、w=0.694）
- Harrison Barnes（SAS，N=4，ΔOVR -6.24）：stamina 62.8→45.6（觀測 40.0、n=4、k=1、w=0.754）
- Trae Young（WAS，N=5，ΔOVR +5.80）：long 63.5→60.4（觀測 56.9、n=37、k=47、w=0.474）；short 47.0→56.6（觀測 70.1、n=27、k=45、w=0.414）；ft 85.0→78.0（觀測 73.4、n=43、k=31、w=0.606）；tovSkill 46.7→61.5（觀測 83.4、n=157、k=274、w=0.403）；pass 99.0→98.9（觀測 98.9、n=180、k=169、w=0.546）；rebound 40.0→40.7（觀測 41.6、n=180、k=246、w=0.458）；stamina 61.5→91.6（觀測 98.9、n=5、k=1、w=0.806）；creation 90.0→83.2（觀測 78.2、n=180、k=148、w=0.576）；foulDraw 97.7→97.8（觀測 97.9、n=73、k=74、w=0.529）
- Leaky Black（SAC，N=2，ΔOVR -5.50）：stamina 76.6→62.4（觀測 53.5、n=2、k=1、w=0.616）
- Jaxson Hayes（UTA，N=4，ΔOVR +5.28）：short 83.7→82.5（觀測 78.2、n=17、k=83、w=0.210）；ft 50.3→54.3（觀測 66.0、n=11、k=40、w=0.255）；pass 41.6→49.9（觀測 65.9、n=108、k=241、w=0.343）；rebound 88.8→88.5（觀測 87.6、n=108、k=436、w=0.237）；stamina 40.0→62.0（觀測 69.1、n=4、k=1、w=0.755）
- Kasparas Jakučionis（MIL，N=5，ΔOVR +5.16）：ft 81.5→78.4（觀測 74.1、n=18、k=30、w=0.415）；tovSkill 61.7→58.8（觀測 45.7、n=65、k=433、w=0.183）；pass 76.8→80.1（觀測 85.6、n=114、k=229、w=0.374）；rebound 62.0→60.0（觀測 54.7、n=114、k=397、w=0.271）；stamina 40.0→47.5（觀測 49.4、n=5、k=1、w=0.797）；creation 53.5→50.0（觀測 45.1、n=114、k=193、w=0.410）
