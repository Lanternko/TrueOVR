# inseason 0.2.7 2026-27 即時結果（資料截至 2026-10-28）

- OVR：賽中 C4（inseason 0.2.7），先驗 card 0.2.7（live/prior-2025-26-card027.json）；N = 該球員 2026-27 已打場數。
- 資料：2026-10-20..2026-10-28、68 場、67 份 PBP；缺 PBP：0022600101。
- git HEAD：`5acd8a0b6eb5`；c=1.0（凍結）、G=82、f = min(N/82, 1)。
- 排名 368 人（有先驗卡且已出賽）；沒有先驗卡 15 人（`no-prior.csv`，不給 OVR）；有先驗卡但 2026-27 還沒出賽 214 人（不列入）。
- N 分布：N=1: 38 人, N=2: 36 人, N=3: 51 人, N=4: 122 人, N=5: 121 人。
- 3PT 欄 = threeValue（R-024，顯示用、不進 OVR）：vol＝合併（2025-26＋2026-27）3PA/MIN×36；acc＝(k·上季 abilityC＋本季 3PM)/(k＋本季 3PA)，k=294.667（本季沒有出手難度資料，用原始命中）；rep＝合併聯盟 3P%（0.3588）−0.03；value＝vol×(acc−rep)，在合併 MIN≥500 且有先驗卡的 321 人池內取百分位並套 attr()。`long` 欄仍在 ranking.csv 並進 OVR 計算，只是表格不顯示。
- E-111（CARD_MODE=027，實驗中）：先驗 x0＝card 0.2.7 產生器的未四捨五入能力值（尾巴原樣、不夾 99）；屬性迴歸＝UL6 primary 的 summary.json；賽中觀測值對 live/pool-027.json 的 2022-23～2025-26 四季合併池映射（百分位型 GP≥30 且 MPG≥20；命中率型 MIN≥500），99 以上與 40 以下照 E-101 尾巴；分區照 E-101（有 area 欄的季 area 缺值的出手跳過、Mid-Range 且 shotDistance<8 → short）；foulDraw 合併池用各季自己的 z、賽中視窗仍用 2025-26 凍結的 z；stamina 照單季映射（不換尺）；drive、onBall、pressure、help、physique、heightInches 凍結；防守加成＝card 0.2.7 的 UL 值（凍結）。
- 降級的資料層見 `../README.md`。`simulatedPer36` 空白（此流程不跑模擬）。
- `lastOVR` = 同一逐點管線對先驗卡算出的 OVR（ΔOVR 的基準）；`formalOVR` = card 0.2.7 `ranking.csv` 同名球員的 OVR（只供對照）。
- OVR 為每場（R-028，E-064 副版）：g = (預測每 36 分鐘淨值 − r_repl)·MPG_hat/36，r_repl＝-1.2464（替補水準 PR10），兩段映射錨點 PR1/PR50/PR99＝-0.8313/1.2521/4.1201（card 0.2.7 summary.json 同組）。MPG_hat = MPG0 + w·(本季場均分鐘 − MPG0)，w＝stamina 的 C4 w（stamina 最小樣本 1 場）；沒有本季視窗紀錄的 214 人（含沒出賽者，不在排名內）退回 MPG0。`ovrPer36` 是同一預測的每 36 分鐘 OVR。
- card 0.2.4 用人層（E-091，R-044 = 用人回歸＋當季 RAPM 目標）：p＝上面屬性迴歸的每 36 預測（`predictedPer36`，C4 照常更新），predNew＝b0 + b1·p + b2·L + b3·a + b4·y + b5·v + b6·y·L + b7·v·L + b8·y·d·L（`predNew` 欄）；L、a、y、v、d 與 has 旗標凍結在 2025-26 全季（`usage-2025-26-card027.json`，payload sha256 fbc56b3e532c…，年齡不加一歲），has=False 或不在卡內者 predNew＝p；係數 b0=-1.1287、b1=0.5624（E-084 results.json）。MPG0＝card 0.2.4 ranking.csv 的 mpg 欄（mpgAvail，依名字配對），卡裡沒有的人退回 MIN／GP。
- E-095（CARD_MODE=025）：分鐘權重 mpg/36 改為飽和 W(mpg)=(1−e^(−mpg/15))/(1−e^(−36/15))（card 0.2.5，R-047），錨點／r_repl 取 E-089 results.json report_only.card.new。
- E-111：用人層係數、r_repl、錨點取 reports/ovr-inseason-2026-27/live/usage-2025-26-card027.json（UL6 pipeline 重跑，錨點對 phase2.json UL6 核對）；分鐘權重 W 同 card 0.2.5。

## 檢查 (a)：f=0、k 取上界 → 與上季卡一致（c4_v5 T1 同款）

| 項目 | 結果 |
|---|---|
| 逐球員 \|OVR 差\| 最大值（門檻 <0.5） | 0.039630 → 通過 |
| 本檔 live_predict 與 c4_v5.c4_predict（f=0, k 上界）屬性最大差 | 0.000e+00 |
| 本檔 live_predict（f=0, c=1）與 fit_w_grid_v4.c2_predict 屬性最大差（T2 同款，門檻 1e-9） | 2.842e-14 |
| 逐點管線 A 參考與原管線差（建構時檢查，門檻 1e-8） | 9.79e-12 |
| 重建的 2025-26 映射 vs 上季卡 long／ft 最大差（只由 box 決定，應接近 0） | 19.863 ／ 22.555 |
| lastOVR vs 正式卡 OVR（同名 368 人）最大差 | 0.10000000000000853 |

## 檢查 (b)：ΔOVR = 賽中 OVR − lastOVR

- 人數 368；\|ΔOVR\| 中位數 1.006、平均 1.455、最大 6.885。
- \|ΔOVR\| >= 1.0 的人：185 人：Victor Wembanyama（N=5，+1.16）、Nikola Jokić（N=4，-3.49）、Kawhi Leonard（N=2，-1.53）、Luka Dončić（N=4，+1.43）、Derrick White（N=4，-4.02）、Giannis Antetokounmpo（N=5，-2.63）、Lauri Markkanen（N=4，-4.10）、Joel Embiid（N=4，+2.15）、Dylan Harper（N=5，+5.65）、Dean Wade（N=3，+1.53）、Jalen Williams（N=3，+3.61）、Brandin Podziemski（N=3，+3.13）、Evan Mobley（N=4，-2.01）、Kevin Durant（N=5，-1.79）、Scottie Barnes（N=4，-2.09）、Ryan Rollins（N=5，-3.06）、Ty Jerome（N=4，+2.75）、Herbert Jones（N=4，-3.65）、Neemias Queta（N=4，-5.36）、Paul George（N=4，+1.25）、Alperen Sengun（N=4，+1.43）、Toumani Camara（N=3，-1.53）、Walker Kessler（N=5，+1.37）、Peyton Watson（N=4，+3.46）、Michael Porter Jr.（N=4，-1.62）、Jalen Suggs（N=3，+1.77）、Josh Giddey（N=5，-1.72）、Derrick Jones Jr.（N=4，+1.14）、Oso Ighodaro（N=1，-1.48）、Jalen Duren（N=2，-4.07）、Onyeka Okongwu（N=5，-1.38）、Mikal Bridges（N=5，-3.39）、Cameron Johnson（N=1，-3.53）、Karl-Anthony Towns（N=5，-1.16）、Trey Murphy III（N=4，-1.61）、Jonathan Kuminga（N=5，+4.57）、Domantas Sabonis（N=4，+4.75）、Pelle Larsson（N=5，+1.39）、Dejounte Murray（N=4，+2.29）、Rui Hachimura（N=3，+2.17）、Cason Wallace（N=3，-2.69）、Zach Edey（N=3，-1.16）、Daniel Gafford（N=5，+1.19）、RJ Barrett（N=4，+1.68）、Collin Murray-Boyles（N=4，-1.87）、Ja'Kobe Walter（N=4，+3.02）、Ivica Zubac（N=3，-2.45）、Paul Reed（N=5，+4.98）、Miles McBride（N=5，-4.23）、Andrew Nembhard（N=4，+1.20）、LaMelo Ball（N=5，-1.64）、Gui Santos（N=4，+3.47）、Duncan Robinson（N=5，+1.45）、James Harden（N=4，-1.31）、Jakob Poeltl（N=4，-1.66）、Josh Okogie（N=4，+1.05）、Matisse Thybulle（N=5，+2.57）、Matas Buzelis（N=5，-1.25）、Ronald Holland II（N=5，-2.17）、Payton Pritchard（N=4，-2.86）、Kasparas Jakučionis（N=5，+4.75）、Luke Kornet（N=5，-2.62）、Kelly Oubre Jr.（N=5，-2.80）、Kris Murray（N=1，-1.48）、Jaylon Tyson（N=4，-2.19）、Saddiq Bey（N=4，-3.26）、Isaiah Joe（N=3，-2.30）、Zach LaVine（N=4，+1.41）、Tre Jones（N=5，-3.52）、Trae Young（N=5，+2.65）、Aaron Nesmith（N=4，-2.09）、Kentavious Caldwell-Pope（N=5，+2.12）、Jaylin Williams（N=5，-2.01）、Cam Spencer（N=4，-2.11）、Jaxson Hayes（N=4，+3.50）、Sidy Cissoko（N=3，+3.17）、Keon Ellis（N=4，+2.68）、De'Andre Hunter（N=4，+1.12）、AJ Green（N=5，-3.87）、Andrew Wiggins（N=5，-1.85）、Mitchell Robinson（N=4，-1.19）、Daniss Jenkins（N=5，+4.71）、Justin Champagnie（N=4，+1.49）、Zaccharie Risacher（N=5，+3.26）、Kevin Huerter（N=5，-1.02）、Kel'el Ware（N=5，-1.49）、Jamal Shead（N=4，-1.36）、Al Horford（N=4，-1.22）、DeMar DeRozan（N=4，-1.57）、Kenrich Williams（N=5，-1.53）、Jordan Goodwin（N=3，-1.27）、Karlo Matković（N=3，-1.66）、Luke Kennard（N=2，-1.09）、Jay Huff（N=4，-2.15）、Marvin Bagley III（N=4，-2.78）、Quenton Jackson（N=5，+1.42）、Josh Minott（N=3，-2.10）、Isaac Okoro（N=5，-3.75）、Hugo González（N=4，-2.61）、Jose Alvarado（N=2，-1.64）、Aaron Wiggins（N=5，+3.81）、Isaiah Jackson（N=4，+1.75）、Collin Sexton（N=4，-2.07）、Zach Collins（N=3，-3.46）、Jock Landale（N=5，-2.28）、Nique Clifford（N=3，-5.76）、Leonard Miller（N=5，+4.29）、Clint Capela（N=4，-2.17）、Josh Green（N=3，+1.88）、Luka Garza（N=4，-2.48）、CJ McCollum（N=5，-4.83）、Adem Bona（N=5，-2.65）、Ziaire Williams（N=4，+2.36）、Jared McCain（N=5，+1.82）、Jalen Slawson（N=4，-3.02）、Nikola Vučević（N=4，-6.88）、Dennis Schröder（N=5，+3.89）、Scoot Henderson（N=3，-4.09）、Tim Hardaway Jr.（N=5，-2.07）、Terrence Shannon Jr（N=5，+4.96）、Harrison Barnes（N=4，-4.03）、Chaney Johnson（N=4，+4.97）、Deandre Ayton（N=5，-5.20）、Svi Mykhailiuk（N=5，-1.20）、Bennedict Mathurin（N=4，-3.64）、Joan Beringer（N=5，+5.82）、Jarred Vanderbilt（N=1，+1.23）、Tyler Kolek（N=3，+1.93）、Vít Krejčí（N=3，-3.17）、Leaky Black（N=2，-4.94）、Cedric Coward（N=3，+1.72）、Bones Hyland（N=5，-1.32）、Kyle Anderson（N=3，-2.37）、Larry Nance Jr.（N=5，+2.55）、Moritz Wagner（N=4，+1.01）、Kyshawn George（N=5，+2.73）、Craig Porter Jr.（N=2，-2.16）、Jamaree Bouyea（N=2，-1.32）、Jamal Cain（N=4，+2.13）、Trayce Jackson-Davis（N=4，+1.67）、Jabari Walker（N=3，-2.21）、Anthony Gill（N=1，-2.27）、Jaylen Clark（N=4，-3.79）、Bogdan Bogdanović（N=5，+1.96）、Jevon Carter（N=2，+1.83）、Dorian Finney-Smith（N=2，+1.23）、Marcus Sasser（N=5，+2.11）、Anfernee Simons（N=5，-3.87）、Micah Peavy（N=1，-1.49）、Noa Essengue（N=4，+4.68）、Justin Edwards（N=1，-2.52）、Jase Richardson（N=4，+1.22）、Myron Gardner（N=2，-1.15）、Corey Kispert（N=2，-1.96）、Simone Fontecchio（N=2，-3.10）、Kevon Looney（N=4，+1.57）、Jalen Pickett（N=2，-1.04）、Mike Conley（N=1，-1.14）、Jaylen Wells（N=4，+1.00）、Khaman Maluach（N=3，+1.85）、Oscar Tshiebwe（N=1，+1.69）、Jae'Sean Tate（N=4，-1.84）、Jamison Battle（N=4，+1.12）、Mohamed Diawara（N=1，-1.17）、Kobe Brown（N=2，-1.61）、Elijah Harkless（N=1，-2.57）、Mo Bamba（N=2，+1.02）、Jordan Poole（N=4，-1.11）、Nick Richards（N=2，+1.75）、Tre Mann（N=1，+1.57）、Gary Trent Jr.（N=1，+1.04）、Jordan Clarkson（N=4，+1.98）、Tyus Jones（N=4，+1.69）、Derik Queen（N=4，+1.02）、Caleb Love（N=1，+1.23）、Ace Bailey（N=5，+1.11）、Taylor Hendricks（N=1，+1.15）、Jordan Hawkins（N=1，+1.14）、Yang Hansen（N=1，-1.66）、Ryan Nembhard（N=2，+1.83）、Yves Missi（N=2，-2.23）、Will Riley（N=3，+5.84）、Ben Saraf（N=1，+2.36）、Jaden Hardy（N=2，+1.70）、Cody Williams（N=3，+5.87）。
- 有屬性被更新的（屬性：人次）：stamina 253, tovSkill 154, short 146, pass 141, rebound 141, creation 141, ft 126, long 101, foulDraw 70, mid 14。

依 N 分組的 \|ΔOVR\|：

| N | 人數 | 中位數 | 最大 |
|---|---|---|---|
| 1 | 38 | 0.847 | 3.532 |
| 2 | 36 | 1.031 | 4.944 |
| 3 | 51 | 1.156 | 5.870 |
| 4 | 122 | 1.121 | 6.885 |
| 5 | 121 | 0.970 | 5.820 |

ΔOVR 最高 10 人：

| 球員 | 隊 | N | lastOVR | OVR | ΔOVR |
|---|---|---|---|---|---|
| Cody Williams | MIN | 3 | 35.4 | 41.3 | +5.87 |
| Will Riley | WAS | 3 | 37.7 | 43.5 | +5.84 |
| Joan Beringer | MIN | 5 | 56.0 | 61.9 | +5.82 |
| Dylan Harper | SAS | 5 | 80.1 | 85.7 | +5.65 |
| Paul Reed | DET | 5 | 69.5 | 74.5 | +4.98 |
| Chaney Johnson | BKN | 4 | 57.8 | 62.8 | +4.97 |
| Terrence Shannon Jr | MIN | 5 | 58.4 | 63.4 | +4.96 |
| Domantas Sabonis | SAC | 4 | 72.7 | 77.5 | +4.75 |
| Kasparas Jakučionis | MIL | 5 | 67.8 | 72.5 | +4.75 |
| Daniss Jenkins | DET | 5 | 65.6 | 70.3 | +4.71 |

ΔOVR 最低 10 人：

| 球員 | 隊 | N | lastOVR | OVR | ΔOVR |
|---|---|---|---|---|---|
| Nikola Vučević | ORL | 4 | 71.1 | 64.2 | -6.88 |
| Nique Clifford | SAC | 3 | 71.7 | 65.9 | -5.76 |
| Neemias Queta | BOS | 4 | 87.6 | 82.2 | -5.36 |
| Deandre Ayton | WAS | 5 | 67.4 | 62.2 | -5.20 |
| Leaky Black | SAC | 2 | 66.0 | 61.1 | -4.94 |
| CJ McCollum | ATL | 5 | 70.2 | 65.3 | -4.83 |
| Miles McBride | NYK | 5 | 78.8 | 74.5 | -4.23 |
| Lauri Markkanen | UTA | 4 | 91.7 | 87.6 | -4.10 |
| Scoot Henderson | POR | 3 | 68.1 | 64.0 | -4.09 |
| Jalen Duren | DET | 2 | 82.3 | 78.3 | -4.07 |

\|ΔOVR\| 最大 10 人的屬性變動明細（x0→x̂；觀測 y 已做 usage 調整）：

- Nikola Vučević（ORL，N=4，ΔOVR -6.88）：stamina 75.0→48.6（觀測 40.0、n=4、k=1、w=0.755）
- Cody Williams（MIN，N=3，ΔOVR +5.87）：stamina 58.5→45.6（觀測 40.0、n=3、k=1、w=0.695）
- Will Riley（WAS，N=3，ΔOVR +5.84）：stamina 49.2→43.6（觀測 41.2、n=3、k=1、w=0.695）
- Joan Beringer（MIN，N=5，ΔOVR +5.82）：short 78.2→77.5（觀測 76.3、n=22、k=55、w=0.329）
- Nique Clifford（SAC，N=3，ΔOVR -5.76）：stamina 60.6→51.1（觀測 47.0、n=3、k=1、w=0.694）
- Dylan Harper（SAS，N=5，ΔOVR +5.65）：short 70.9→71.6（觀測 72.8、n=46、k=96、w=0.364）；ft 68.9→69.6（觀測 71.1、n=13、k=37、w=0.305）；tovSkill 71.1→73.8（觀測 88.3、n=111、k=966、w=0.158）；pass 87.1→85.6（觀測 83.5、n=161、k=254、w=0.425）；rebound 66.7→67.7（觀測 70.1、n=161、k=475、w=0.299）；stamina 52.1→77.7（觀測 84.3、n=5、k=1、w=0.796）；creation 88.4→90.0（觀測 91.8、n=161、k=209、w=0.470）；foulDraw 60.3→60.0（觀測 59.6、n=74、k=129、w=0.404）
- Neemias Queta（BOS，N=4，ΔOVR -5.36）：short 83.4→80.9（觀測 70.1、n=17、k=100、w=0.187）；ft 57.7→59.3（觀測 63.1、n=15、k=41、w=0.303）；stamina 61.4→48.5（觀測 44.3、n=4、k=1、w=0.754）
- Deandre Ayton（WAS，N=5，ΔOVR -5.20）：short 86.5→85.4（觀測 81.4、n=19、k=103、w=0.207）；stamina 70.6→46.3（觀測 40.0、n=5、k=1、w=0.795）
- Paul Reed（DET，N=5，ΔOVR +4.98）：short 85.6→83.4（觀測 78.4、n=29、k=87、w=0.297）；ft 56.1→59.8（觀測 68.0、n=13、k=36、w=0.309）；tovSkill 54.6→52.2（觀測 40.5、n=68、k=498、w=0.173）；pass 64.5→65.0（觀測 65.7、n=130、k=227、w=0.403）；rebound 95.6→94.6（觀測 92.3、n=130、k=388、w=0.297）；stamina 40.0→58.8（觀測 63.7、n=5、k=1、w=0.796）；creation 59.9→55.8（觀測 50.7、n=130、k=190、w=0.442）
- Chaney Johnson（BKN，N=4，ΔOVR +4.97）：stamina 40.6→41.0（觀測 41.2、n=4、k=1、w=0.765）
