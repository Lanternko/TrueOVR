# inseason 0.2.7b 2026-27 即時結果（資料截至 2026-10-28）

- OVR：賽中 C4（inseason 0.2.7b），先驗 card 0.2.7b（live/prior-2025-26-card027b.json）；N = 該球員 2026-27 已打場數。
- 資料：2026-10-20..2026-10-28、68 場、67 份 PBP；缺 PBP：0022600101。
- git HEAD：`5acd8a0b6eb5`；c=1.0（凍結）、G=82、f = min(N/82, 1)。
- 排名 368 人（有先驗卡且已出賽）；沒有先驗卡 57 人（`no-prior.csv`，不給 OVR）；有先驗卡但 2026-27 還沒出賽 214 人（不列入）。
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

- 人數 368；\|ΔOVR\| 中位數 1.042、平均 1.432、最大 6.954。
- \|ΔOVR\| >= 1.0 的人：192 人：Victor Wembanyama（N=5，+1.17）、Nikola Jokić（N=4，-2.83）、Derrick White（N=4，-1.12）、Kawhi Leonard（N=2，-1.90）、Giannis Antetokounmpo（N=5，-2.22）、Lauri Markkanen（N=4，-3.45）、Dylan Harper（N=5，+4.61）、Dean Wade（N=3，+1.56）、Neemias Queta（N=4，-3.35）、Jamal Murray（N=4，-1.48）、Ty Jerome（N=4，+3.80）、Evan Mobley（N=4，-1.11）、Tyrese Maxey（N=5，-1.33）、Ryan Rollins（N=5，-3.23）、Brandin Podziemski（N=3，+1.38）、Desmond Bane（N=4，-1.59）、Kevin Durant（N=5，-3.01）、Toumani Camara（N=3，-1.69）、Herbert Jones（N=4，-5.14）、Anthony Davis（N=5，-1.04）、Moussa Diabaté（N=5，+1.22）、Stephen Curry（N=4，-1.65）、Michael Porter Jr.（N=4，-2.45）、Josh Giddey（N=5，-2.06）、Derrick Jones Jr.（N=4，+1.26）、Jalen Brunson（N=5，-1.77）、Jalen Duren（N=2，-3.69）、Oso Ighodaro（N=1，-1.52）、Keegan Murray（N=2，-1.01）、Onyeka Okongwu（N=5，-1.54）、Cameron Johnson（N=1，-3.79）、Mikal Bridges（N=5，-3.64）、Ja Morant（N=3，+1.05）、Jonathan Kuminga（N=5，+4.68）、Walker Kessler（N=5，-2.17）、Trey Murphy III（N=4，-1.98）、Pelle Larsson（N=5，+1.02）、Day'Ron Sharpe（N=4，+1.01）、Jaylen Brown（N=5，-1.39）、Paul Reed（N=5，+6.95）、Cason Wallace（N=3，-2.75）、Dejounte Murray（N=4，+1.36）、Collin Murray-Boyles（N=4，-1.67）、Zach Edey（N=3，-1.73）、Ivica Zubac（N=3，-1.60）、RJ Barrett（N=4，+1.25）、Miles McBride（N=5，-3.19）、Domantas Sabonis（N=4，+2.65）、Ja'Kobe Walter（N=4，+3.23）、Josh Hart（N=5，-1.19）、Donovan Clingan（N=3，-1.53）、Trae Young（N=5，+3.98）、Sam Hauser（N=4，-1.31）、LaMelo Ball（N=5，-2.43）、Duncan Robinson（N=5，+1.15）、Matisse Thybulle（N=5，+2.62）、Saddiq Bey（N=4，-2.54）、Jaylin Williams（N=5，-1.11）、Jakob Poeltl（N=4，-2.14）、Ronald Holland II（N=5，-2.22）、Luke Kornet（N=5，-2.56）、Payton Pritchard（N=4，-2.86）、James Harden（N=4，-1.94）、Kasparas Jakučionis（N=5，+4.35）、Gui Santos（N=4，+2.15）、Matas Buzelis（N=5，-1.54）、Jaylon Tyson（N=4，-2.06）、Kris Murray（N=1，-1.52）、Kelly Oubre Jr.（N=5，-3.15）、Norman Powell（N=5，-1.12）、Isaiah Joe（N=3，-2.36）、Tre Jones（N=5，-3.68）、Jaxson Hayes（N=4，+4.10）、Jordan Walsh（N=4，+1.29）、Aaron Nesmith（N=4，-2.43）、Cam Spencer（N=4，-2.28）、Isaiah Stewart（N=3，-1.49）、Keon Ellis（N=4，+2.86）、Kentavious Caldwell-Pope（N=5，+1.46）、Grayson Allen（N=5，-1.19）、AJ Green（N=5，-3.57）、Sidy Cissoko（N=3，+2.42）、Andrew Wiggins（N=5，-2.22）、Kel'el Ware（N=5，-1.32）、Daniss Jenkins（N=5，+4.14）、Al Horford（N=4，-1.04）、Zaccharie Risacher（N=5，+2.85）、Ryan Dunn（N=3，-1.56）、Luke Kennard（N=2，-1.21）、Jay Huff（N=4，-1.62）、Quentin Grimes（N=5，-1.25）、Karlo Matković（N=3，-1.26）、Marvin Bagley III（N=4，-2.65）、DeMar DeRozan（N=4，-2.91）、Hugo González（N=4，-1.59）、Josh Minott（N=3，-1.47）、Kyle Kuzma（N=5，+1.20）、Isaac Okoro（N=5，-3.46）、Quenton Jackson（N=5，+1.43）、Tristan da Silva（N=4，+1.40）、Jose Alvarado（N=2，-1.65）、Aaron Wiggins（N=5，+3.48）、Keldon Johnson（N=5，-1.04）、Bobby Portis Jr.（N=5，-1.68）、Isaiah Jackson（N=4，+1.76）、Jock Landale（N=5，-2.06）、Adem Bona（N=5，-1.76）、CJ McCollum（N=5，-4.01）、Nique Clifford（N=3，-5.61）、Collin Sexton（N=4，-2.62）、Scoot Henderson（N=3，-2.06）、Leonard Miller（N=5，+4.21）、Ryan Kalkbrenner（N=5，-1.82）、Ziaire Williams（N=4，+2.55）、Reed Sheppard（N=4，-2.15）、Zach Collins（N=3，-4.27）、Luka Garza（N=4，-2.60）、Scotty Pippen Jr.（N=4，-1.28）、Jared McCain（N=5，+1.80）、Jalen Green（N=3，+1.32）、Nikola Vučević（N=4，-6.50）、Kobe Sanders（N=4，+1.06）、Steven Adams（N=1，-2.61）、Dru Smith（N=3，-1.15）、Jalen Slawson（N=4，-3.29）、Terrence Shannon Jr（N=5，+4.27）、Chaney Johnson（N=4，+5.34）、Jake LaRavia（N=4，-1.28）、Joan Beringer（N=5，+6.50）、Deandre Ayton（N=5，-4.97）、Dennis Schröder（N=5，+2.02）、Tim Hardaway Jr.（N=5，-3.44）、Ben Sheppard（N=1，-1.27）、Harrison Barnes（N=4，-5.88）、Tyler Kolek（N=3，+2.02）、Jarred Vanderbilt（N=1，+1.17）、Bennedict Mathurin（N=4，-4.34）、Vít Krejčí（N=3，-3.40）、Leaky Black（N=2，-5.44）、Cedric Coward（N=3，+1.19）、Bones Hyland（N=5，-1.96）、Larry Nance Jr.（N=5，+2.72）、Moritz Wagner（N=4，+1.40）、Kyle Anderson（N=3，-2.39）、Kyshawn George（N=5，+2.55）、Craig Porter Jr.（N=2，-2.58）、Jamal Cain（N=4，+2.50）、Jabari Walker（N=3，-1.75）、Buddy Hield（N=5，+1.01）、Marcus Sasser（N=5，+3.30）、Bogdan Bogdanović（N=5，+2.04）、Trayce Jackson-Davis（N=4，+1.27）、Jerami Grant（N=4，-2.27）、Jaylen Clark（N=4，-3.82）、Jamaree Bouyea（N=2，-2.11）、Anthony Gill（N=1，-2.80）、Malik Monk（N=3，-1.52）、Anfernee Simons（N=5，-3.38）、Khris Middleton（N=4，-1.55）、Jevon Carter（N=2，+1.14）、Brandon Williams（N=5，-1.53）、Micah Peavy（N=1，-1.21）、Khaman Maluach（N=3，+3.56）、Jase Richardson（N=4，+1.79）、Justin Edwards（N=1，-2.54）、Corey Kispert（N=2，-1.88）、Simone Fontecchio（N=2，-2.65）、Myron Gardner（N=2，-1.25）、Kevon Looney（N=4，+1.52）、Noa Essengue（N=4，+4.13）、Jalen Pickett（N=2，-1.24）、Elijah Harkless（N=1，-1.03）、Dorian Finney-Smith（N=2，-1.40）、Jamison Battle（N=4，+1.13）、Alex Sarr（N=5，+1.22）、Jae'Sean Tate（N=4，-2.46）、Taurean Prince（N=2，-1.71）、Mohamed Diawara（N=1，-1.23）、Jett Howard（N=2，-1.20）、Kobe Brown（N=2，-1.77）、Royce O'Neale（N=5，-3.35）、Jayson Kent（N=1，+1.06）、Jordan Poole（N=4，-1.04）、Caleb Love（N=1，+1.21）、Yang Hansen（N=1，-1.58）、Ryan Nembhard（N=2，+2.25）、Will Riley（N=3，+5.38）、Ben Saraf（N=1，+2.35）、Jarace Walker（N=5，-1.02）、Jaden Hardy（N=2，+1.54）、Cody Williams（N=3，+5.85）、Bub Carrington（N=5，-1.30）。
- 有屬性被更新的（屬性：人次）：stamina 253, tovSkill 154, short 146, pass 141, rebound 141, creation 141, ft 126, long 101, foulDraw 70, mid 14。

依 N 分組的 \|ΔOVR\|：

| N | 人數 | 中位數 | 最大 |
|---|---|---|---|
| 1 | 38 | 0.802 | 3.788 |
| 2 | 36 | 1.078 | 5.442 |
| 3 | 51 | 1.190 | 5.848 |
| 4 | 122 | 1.022 | 6.500 |
| 5 | 121 | 1.147 | 6.954 |

ΔOVR 最高 10 人：

| 球員 | 隊 | N | lastOVR | OVR | ΔOVR |
|---|---|---|---|---|---|
| Paul Reed | DET | 5 | 70.0 | 77.0 | +6.95 |
| Joan Beringer | MIN | 5 | 55.9 | 62.4 | +6.50 |
| Cody Williams | MIN | 3 | 35.6 | 41.5 | +5.85 |
| Will Riley | WAS | 3 | 38.3 | 43.7 | +5.38 |
| Chaney Johnson | BKN | 4 | 57.5 | 62.8 | +5.34 |
| Jonathan Kuminga | MIN | 5 | 73.0 | 77.7 | +4.68 |
| Dylan Harper | SAS | 5 | 80.3 | 84.9 | +4.60 |
| Kasparas Jakučionis | MIL | 5 | 68.2 | 72.5 | +4.35 |
| Terrence Shannon Jr | MIN | 5 | 58.6 | 62.8 | +4.27 |
| Leonard Miller | CHI | 5 | 61.4 | 65.6 | +4.21 |

ΔOVR 最低 10 人：

| 球員 | 隊 | N | lastOVR | OVR | ΔOVR |
|---|---|---|---|---|---|
| Nikola Vučević | ORL | 4 | 71.1 | 64.6 | -6.50 |
| Harrison Barnes | SAS | 4 | 67.4 | 61.5 | -5.89 |
| Nique Clifford | SAC | 3 | 71.5 | 65.9 | -5.61 |
| Leaky Black | SAC | 2 | 66.1 | 60.6 | -5.44 |
| Herbert Jones | NOP | 4 | 86.3 | 81.2 | -5.14 |
| Deandre Ayton | WAS | 5 | 67.3 | 62.4 | -4.97 |
| Bennedict Mathurin | NOP | 4 | 65.8 | 61.4 | -4.34 |
| Zach Collins | CHI | 3 | 69.4 | 65.1 | -4.27 |
| CJ McCollum | ATL | 5 | 70.0 | 66.0 | -4.01 |
| Jaylen Clark | MIN | 4 | 62.3 | 58.5 | -3.82 |

\|ΔOVR\| 最大 10 人的屬性變動明細（x0→x̂；觀測 y 已做 usage 調整）：

- Paul Reed（DET，N=5，ΔOVR +6.95）：short 85.6→83.4（觀測 78.4、n=29、k=87、w=0.297）；ft 56.1→59.8（觀測 68.0、n=13、k=36、w=0.309）；tovSkill 54.6→52.2（觀測 40.5、n=68、k=498、w=0.173）；pass 63.3→62.9（觀測 62.1、n=130、k=225、w=0.405）；rebound 95.6→94.6（觀測 92.3、n=130、k=388、w=0.297）；stamina 40.0→58.8（觀測 63.7、n=5、k=1、w=0.796）；creation 59.9→55.8（觀測 50.7、n=130、k=190、w=0.442）
- Joan Beringer（MIN，N=5，ΔOVR +6.50）：short 78.2→77.5（觀測 76.3、n=22、k=55、w=0.329）
- Nikola Vučević（ORL，N=4，ΔOVR -6.50）：stamina 75.0→48.6（觀測 40.0、n=4、k=1、w=0.755）
- Harrison Barnes（SAS，N=4，ΔOVR -5.89）：stamina 62.8→45.6（觀測 40.0、n=4、k=1、w=0.754）
- Cody Williams（MIN，N=3，ΔOVR +5.85）：stamina 58.5→45.6（觀測 40.0、n=3、k=1、w=0.695）
- Nique Clifford（SAC，N=3，ΔOVR -5.61）：stamina 60.6→51.1（觀測 47.0、n=3、k=1、w=0.694）
- Leaky Black（SAC，N=2，ΔOVR -5.44）：stamina 76.6→62.3（觀測 53.4、n=2、k=1、w=0.616）
- Will Riley（WAS，N=3，ΔOVR +5.38）：stamina 49.2→43.6（觀測 41.2、n=3、k=1、w=0.695）
- Chaney Johnson（BKN，N=4，ΔOVR +5.34）：stamina 40.6→41.0（觀測 41.2、n=4、k=1、w=0.765）
- Herbert Jones（NOP，N=4，ΔOVR -5.14）：stamina 74.6→48.5（觀測 40.0、n=4、k=1、w=0.755）
