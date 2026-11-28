# inseason 0.2.12c 2026-27 即時結果（資料截至 2026-11-01）

- OVR：賽中 C4（inseason 0.2.12c），先驗 card 0.2.12c（live/prior-2025-26-card0212c.json）；N = 該球員 2026-27 已打場數。
- 資料：2026-10-20..2026-11-01、89 場、87 份 PBP；缺 PBP：0022600101, 0022600154。
- git HEAD：`71e2d88d2ff4`；c=1.0（凍結）、G=82、f = min(N/82, 1)。
- 排名 442 人（有先驗卡且已出賽，加上在現役名單上但還沒出賽的 60 人，N=0、OVR＝先驗）；沒有先驗卡 17 人（`no-prior.csv`，不給 OVR）；有先驗卡、沒出賽也不在現役名單 140 人（不列入）。
- N 分布：N=0: 60 人, N=1: 25 人, N=2: 41 人, N=3: 29 人, N=4: 41 人, N=5: 84 人, N=6: 130 人, N=7: 32 人。
- 3PT 欄 = threeValue（R-024，顯示用、不進 OVR）：vol＝合併（2025-26＋2026-27）3PA/MIN×36；acc＝(k·上季 abilityC＋本季 3PM)/(k＋本季 3PA)，k=294.667（本季沒有出手難度資料，用原始命中）；rep＝合併聯盟 3P%（0.3587）−0.03；value＝vol×(acc−rep)，在合併 MIN≥500 且有先驗卡的 1671 人池內取百分位並套 attr()。`long` 欄仍在 ranking.csv 並進 OVR 計算，只是表格不顯示。
- inseason 0.2.12c（R-144，E-207）：tovSkill 的失誤率分母由持球分鐘改觸球次數＝0.5·z(−每觸球失誤，窗口加權失誤對窗口加權觸球收縮，k 乘觸球／持球分鐘換算係數)＋0.5·z(持球分鐘/36)；觸球來源同持球分鐘（NBA.com tracking TOUCHES）；池、z、0–99 映射凍結於 live/tov-pool-card0212c.json；卡片全部係數重擬合（card 0.2.12c）。
- inseason 0.2.12（R-139，E-203）：tovSkill 改看持球時間＝0.5·z(−每持球分鐘失誤，窗口加權失誤對窗口加權持球分鐘收縮)＋0.5·z(持球分鐘/36)；持球分鐘＝NBA.com tracking TIME_OF_POSS（過去季 handle-E069 raw、本季 data/defense-seventh/2026-27/possessions.json 每天抓整季），收縮、z、0–99 映射凍結自卡片端（live/tov-pool-card0212.json、live/tov_live.py）；新秀（不在卡片名單）用本季整季值、本季 1000 分鐘內與起點線性混合；卡片全部係數重擬合（card 0.2.12）。
- inseason 0.2.10j（R-134／R-135）：加能力值引力（gravity）＝NBA.com 無球外線引力，2025-26 與本季依 FRAMES 加權、套四季窗口季權重；兩季都沒有的人用 OLS（3PA/36、3P%、USG%、位置）補；卡片全部係數重擬合（card 0.2.10j）。
- inseason 0.2.10i（R-130／R-132）：切入（drive）只算帶球切入到 10 呎內的自主兩分（量與效率各半），自主創造（creation）改成自己創造的跳投與低位出手（不含切入上籃、補籃、空切）per36；兩項都是四季滑動窗口，卡片全部係數重擬合（card 0.2.10i）。
- inseason 0.2.10g（E-192）：用人層的 L（上場強度）、a（出賽率）也改四季滑動窗口（權重同其他窗口項；y、v 用當下年齡），每天用當下窗口重算，不再凍結在 2025-26；係數同 0.2.10d，r_repl、錨點用新池重取。
- inseason 0.2.10f（E-191b）：3PT 欄（threeValue，顯示用）的對照池改成近三季各自窗口值＋本季窗口值（窗口加權 MIN≥500），ranking／OVR／名次同 0.2.10e。
- inseason 0.2.10e（E-188，R-124）：只換 OVR 映射（PR90→88、PR95→92，名次不變），屬性、係數同 0.2.10d。
- inseason 0.2.10d（E-185）：long、creation 也改四季滑動窗口（同 8 項的權重；long 是窗口 3PM／3PA 收縮到本季聯盟 3P%、creation 是窗口 FGA/MIN），threeValue、MPG_hat 同為窗口；係數、錨點、r_repl 用 card 0.2.10d 的 KAU 重擬合值（底 card 0.2.10c）。
- inseason 0.2.10（R-114）：drive、foulDraw、ft、mid、pass、rebound、short、tovSkill 八項＝E-175 四季滑動窗口（過去四季權重 window_w(c)，c＝82×已賽場數/1230；本季逐場線性遞減；收縮 k、先驗 m、映射皆凍結自 2025-26 U 鏈；live/window8.py），不再走 C4 的 x0+w(y−x0)；其餘屬性（stamina 等）仍走 C4。用人層係數、錨點、r_repl 取現行卡的重擬合值（usage 檔）。- 以下為舊版 E-128 說明（其餘屬性的先驗與映射仍適用）：E-128（CARD_MODE=027b，預設）：先驗 x0＝card 0.2.7b 產生器的未四捨五入能力值（尾巴原樣、不夾 99）；屬性迴歸＝rebase-027a e123a primary 的 summary.json；賽中觀測值對 live/pool-027b.json 的合併池映射（pass 換 E-125 量×率合成值＋合併池，視窗不收縮、z 常數凍結自 2025-26 卡片端；其餘 8 欄同 pool-027），99 以上與 40 以下照 E-101 尾巴；help 照 E-123 D1 尾巴（不夾 99）；pressure、presDisplay、drive 改四季窗口（老將，live/pres_drive.py）／本季值（新秀）；physique、heightInches 凍結；防守加成＝UL 值（同 027）。
- 降級的資料層見 `../README.md`。`simulatedPer36` 空白（此流程不跑模擬）。
- `lastOVR` = 同一逐點管線、本季 0 場（8 項屬性＝窗口 day0）算出的 OVR（ΔOVR 的基準，R-112）；`formalOVR` = card 0.2.12c `ranking.csv` 同名球員的 OVR（只供對照）。
- OVR 為每場（R-028，E-064 副版）：g = (預測每 36 分鐘淨值 − r_repl)·MPG_hat/36，r_repl＝-1.0334（替補水準 PR10），映射錨點 PR1/PR50/PR99＝-0.7310/0.9933/4.0667（card 0.2.12c summary.json 同組），PR90/PR95＝2.1873/2.5931（E-188 S3：PR50→70、PR90→88、PR95→92、PR99→99 分段線性）。MPG_hat＝窗口 MPG（Σu·MIN／Σu·GP，過去 1 季＋本季逐場線性遞減，E-185）；lastOVR 基準＝本季 0 場的窗口 MPG；窗口內沒出賽的 0 人退回 MPG0。`ovrPer36` 是同一預測的每 36 分鐘 OVR。
- card 0.2.4 用人層（E-091，R-044 = 用人回歸＋當季 RAPM 目標）：p＝上面屬性迴歸的每 36 預測（`predictedPer36`，C4 照常更新），predNew＝b0 + b1·p + b2·L + b3·a + b4·y + b5·v + b6·y·L + b7·v·L + b8·y·d·L（`predNew` 欄）；L、a 與 has 旗標＝四季滑動窗口（0.2.10g，E-192，live/window11.py，每天用當下窗口重算；y、v 用當下年齡；係數、錨點、r_repl 取 `usage-2025-26-card0212c.json`，payload sha256 7fe274c5410b…），has=False 或不在卡內者 predNew＝p；係數 b0=-0.7722、b1=0.6207（E-084 results.json）。MPG0＝card 0.2.4 ranking.csv 的 mpg 欄（mpgAvail，依名字配對），卡裡沒有的人退回 MIN／GP。
- E-095（CARD_MODE=025）：分鐘權重 mpg/36 改為飽和 W(mpg)=(1−e^(−mpg/15))/(1−e^(−36/15))（card 0.2.5，R-047），錨點／r_repl 取 E-089 results.json report_only.card.new。
- E-128：用人層係數、r_repl、錨點取 reports/ovr-inseason-2026-27/live/usage-2025-26-card0212c.json（rebase-027a e123a pipeline 重跑，錨點對 rebase-027a/work/cards-result.json 核對）；分鐘權重 W 同 card 0.2.5。

## 檢查 (a)：f=0、k 取上界 → 與上季卡一致（c4_v5 T1 同款）

| 項目 | 結果 |
|---|---|
| 逐球員 \|OVR 差\| 最大值（門檻 <0.5） | 0.000000 → 通過 |
| 本檔 live_predict 與 c4_v5.c4_predict（f=0, k 上界）屬性最大差 | 0.000e+00 |
| 本檔 live_predict（f=0, c=1）與 fit_w_grid_v4.c2_predict 屬性最大差（T2 同款，門檻 1e-9） | 1.421e-14 |
| 逐點管線 A 參考與原管線差（建構時檢查，門檻 1e-8） | 9.90e-12 |
| 重建的 2025-26 映射 vs 上季卡 long／ft 最大差（只由 box 決定，應接近 0） | 26.453 ／ 22.755 |
| lastOVR vs 正式卡 OVR（同名 442 人）最大差 | 7.0 |

## 檢查 (b)：ΔOVR = 賽中 OVR − lastOVR

- 人數 442；\|ΔOVR\| 中位數 0.897、平均 1.223、最大 6.535。
- \|ΔOVR\| >= 1.0 的人：202 人：Shai Gilgeous-Alexander（N=6，-1.38）、Giannis Antetokounmpo（N=6，-2.26）、Stephen Curry（N=5，+1.73）、Tyrese Maxey（N=7，+2.60）、Jalen Williams（N=3，-1.08）、Anthony Davis（N=6，+1.67）、Franz Wagner（N=6，-1.13）、Jalen Brunson（N=6，-1.67）、Jalen Suggs（N=3，-3.93）、Isaiah Joe（N=3，-1.04）、Ryan Rollins（N=6，-2.15）、Cooper Flagg（N=5，+3.63）、Tre Jones（N=6，-1.27）、Cameron Johnson（N=2，+3.23）、Matisse Thybulle（N=6，+2.17）、Cedric Coward（N=5，+3.13）、Pascal Siakam（N=6，-1.36）、Jaden McDaniels（N=7，+1.12）、Isaiah Hartenstein（N=6，-4.05）、Sam Merrill（N=6，+3.12）、Jaylin Williams（N=6，-1.97）、Nickeil Alexander-Walker（N=7，-1.00）、Dejounte Murray（N=4，-2.71）、Naz Reid（N=7，-1.11）、Domantas Sabonis（N=6，-2.42）、Scotty Pippen Jr.（N=5，-5.51）、Paul Reed（N=6，+2.23）、Jalen Duren（N=2，-1.52）、Josh Giddey（N=6，-3.29）、DeMar DeRozan（N=5，-1.04）、Javon Small（N=1，-2.96）、Ivica Zubac（N=3，-1.89）、Collin Sexton（N=5，-1.34）、Miles McBride（N=6，-1.24）、Obi Toppin（N=5，-3.67）、Dylan Harper（N=6，-2.45）、Robert Williams III（N=4，-2.33）、Zach LaVine（N=6，+1.46）、Collin Gillespie（N=4，-2.27）、Ja Morant（N=4，-4.24）、LaMelo Ball（N=7，-1.08）、Aaron Wiggins（N=7，+2.64）、Aaron Nesmith（N=5，-3.53）、Moussa Diabaté（N=7，-1.72）、Kelly Oubre Jr.（N=6，+1.50）、Pelle Larsson（N=6，+1.25）、Luke Kornet（N=6，-4.51）、Walker Kessler（N=6，-2.61）、Mitchell Robinson（N=5，-1.31）、Myles Turner（N=6，-1.96）、Jakob Poeltl（N=5，-2.95）、Jordan Goodwin（N=4，-1.91）、Mark Williams（N=0，-1.47）、Josh Okogie（N=5，+1.49）、De'Andre Hunter（N=6，-1.89）、Donovan Clingan（N=5，+2.71）、Zach Edey（N=5，-2.44）、Goga Bitadze（N=5，-1.07）、Sandro Mamukelashvili（N=6，-1.07）、Kyshawn George（N=6，-1.77）、Terance Mann（N=1，-1.14）、Nic Claxton（N=0，-1.11）、Dereck Lively II（N=0，-1.24）、Kasparas Jakučionis（N=6，+6.54）、Duncan Robinson（N=6，+1.33）、Josh Minott（N=4，+2.97）、Vít Krejčí（N=5，-1.16）、Ziaire Williams（N=4，-1.03）、Craig Porter Jr.（N=4，-1.75）、Bobby Portis Jr.（N=6，-1.17）、Naji Marshall（N=3，-1.04）、Keldon Johnson（N=6，-1.11）、Caris LeVert（N=0，-1.42）、Jalen Green（N=4，-4.77）、Dillon Brooks（N=4，-3.75）、Steven Adams（N=1，-1.68）、Marvin Bagley III（N=5，-1.01）、Bennedict Mathurin（N=6，-2.62）、Keyonte George（N=6，+2.08）、Brook Lopez（N=5，+1.38）、Egor Dëmin（N=4，-2.37）、Kenrich Williams（N=6，-3.02）、Khris Middleton（N=5，-1.65）、Danny Wolf（N=2，-3.51）、Will Richard（N=6，-1.08）、Clint Capela（N=6，-2.12）、Rui Hachimura（N=4，-3.79）、Zach Collins（N=4，-4.69）、Josh Green（N=4，+1.22）、Cormac Ryan（N=0，-1.54）、Luka Garza（N=6，-1.03）、Jaylen Wells（N=6，+2.10）、Hugo González（N=6，-3.32）、Tyrese Proctor（N=5，-2.61）、Grant Nelson（N=0，-1.29）、Kyle Filipowski（N=4，-1.16）、Brandon Williams（N=6，-2.05）、Malik Monk（N=5，-1.92）、Alex Sarr（N=6，+1.85）、Quinten Post（N=5，+1.09）、Harrison Barnes（N=4，-1.01）、Dylan Cardwell（N=0，-2.09）、Nikola Jović（N=5，+1.00）、Kel'el Ware（N=6，-1.52）、Deandre Ayton（N=6，-1.60）、Jalen Slawson（N=5，+3.45）、Jamaree Bouyea（N=2，-3.15）、Anfernee Simons（N=7，-1.35）、Jae'Sean Tate（N=5，+1.75）、Jarred Vanderbilt（N=2，-1.36）、Terrence Shannon Jr（N=7，+2.54）、Dorian Finney-Smith（N=3，+1.60）、Lawson Lovering（N=0，-2.35）、Isaac Okoro（N=6，-1.11）、Trayce Jackson-Davis（N=5，-1.02）、Daniss Jenkins（N=6，+1.01）、Tristan da Silva（N=6，-2.10）、Jarace Walker（N=6，-1.34）、Nique Clifford（N=5，-4.32）、Jock Landale（N=7，-2.23）、Bilal Coulibaly（N=6，-2.69）、Yanic Konan Niederhäuser（N=0，-1.40）、Mike Conley（N=1，+1.23）、Scoot Henderson（N=5，-3.87）、Sidy Cissoko（N=5，+3.09）、Kevon Looney（N=4，-2.47）、Jared McCain（N=6，-2.73）、Micah Potter（N=3，-1.30）、Adem Bona（N=7，-2.71）、David Jones Garcia（N=1，-2.42）、Justin Edwards（N=2，-1.02）、Jordan Poole（N=4，-5.59）、Svi Mykhailiuk（N=6，+2.77）、Gradey Dick（N=5，+1.27）、Mo Bamba（N=3，+1.11）、Zyon Pullin（N=2，-2.45）、Ousmane Dieng（N=5，-3.89）、Jeremiah Fears（N=6，-1.64）、Jordan McLaughlin（N=2，-1.87）、Joan Beringer（N=7，-1.61）、DeAndre Jordan（N=2，+1.14）、Chaney Johnson（N=5，-3.62）、Walter Clayton Jr.（N=5，-1.48）、Blake Wesley（N=1，-2.24）、Taurean Prince（N=2，-1.89）、Branden Carlson（N=2，-1.39）、Ariel Hukporti（N=0，-1.24）、Tony Bradley（N=1，-1.06）、Cam Whitmore（N=2，-3.38）、Tristan Enaruna（N=1，-1.17）、Jerami Grant（N=6，-2.63）、Alex Morales（N=3，-1.50）、Amari Williams（N=0，-1.02）、Jevon Carter（N=2，-3.79）、Riley Minix（N=1，-2.97）、Isaiah Collier（N=6，-2.81）、Leonard Miller（N=6，-2.90）、Trey Alexander（N=0，-1.36）、Tolu Smith（N=5，-2.60）、Rocco Zikarsky（N=0，-1.12）、Pacôme Dadiet（N=1，-1.72）、Jayson Kent（N=1，-1.70）、Bronny James（N=2，-2.21）、Dennis Schröder（N=7，-1.72）、Carter Bryant（N=6，-1.80）、GG Jackson（N=6，-3.35）、Andre Drummond（N=6，-1.32）、Julian Reese（N=1，-2.69）、Oscar Tshiebwe（N=3，+1.14）、Noa Essengue（N=5，-2.56）、John Tonje（N=1，-3.47）、Tre Johnson（N=5，-2.21）、Rasheer Fleming（N=2，-1.98）、LJ Cryer（N=4，-2.96）、Ron Harper Jr.（N=2，-5.17）、Daeqwon Plowden（N=5，+1.34）、Alijah Martin（N=4，-1.46）、Nikola Topić（N=0，-1.36）、Chris Youngblood（N=1，-3.52）、Khaman Maluach（N=4，-2.45）、Jase Richardson（N=6，-4.17）、Jericho Sims（N=2，-2.09）、Isaiah Crawford（N=5，-2.68）、Cam Christie（N=3，-3.57）、Liam McNeeley（N=3，-1.57）、Micah Peavy（N=2，-1.26）、Maxime Raynaud（N=0，-1.12）、RayJ Dennis（N=0，-1.10）、Jett Howard（N=2，-1.54）、Jordan Clarkson（N=5，+1.66）、Rayan Rupert（N=0，-1.05）、Tre Mann（N=2，-5.18）、Keshon Gilbert（N=0，-1.83）、Elijah Harkless（N=1，-3.98）、Chaz Lanier（N=2，-1.51）、Kam Jones（N=0，-1.05）、Jordan Hawkins（N=2，-3.03）、Jaden Hardy（N=3，-5.04）、AJ Johnson（N=1，-3.66）、Caleb Love（N=1，-1.01）、Ben Saraf（N=1，-4.77）、Jahmai Mashack（N=1，-2.15）。
- 有屬性被更新的（屬性：人次）：stamina 251。

依 N 分組的 \|ΔOVR\|：

| N | 人數 | 中位數 | 最大 |
|---|---|---|---|
| 0 | 60 | 0.633 | 2.350 |
| 1 | 25 | 1.695 | 4.771 |
| 2 | 41 | 1.138 | 5.183 |
| 3 | 29 | 0.807 | 5.039 |
| 4 | 41 | 1.009 | 5.589 |
| 5 | 84 | 0.745 | 5.515 |
| 6 | 130 | 0.898 | 6.535 |
| 7 | 32 | 0.852 | 2.708 |

ΔOVR 最高 10 人：

| 球員 | 隊 | N | lastOVR | OVR | ΔOVR |
|---|---|---|---|---|---|
| Kasparas Jakučionis | MIL | 6 | 64.2 | 70.8 | +6.54 |
| Cooper Flagg | DAL | 5 | 79.0 | 82.6 | +3.63 |
| Jalen Slawson | IND | 5 | 58.2 | 61.7 | +3.45 |
| Cameron Johnson | DEN | 2 | 78.7 | 81.9 | +3.23 |
| Cedric Coward | MEM | 5 | 78.4 | 81.5 | +3.13 |
| Sam Merrill | CLE | 6 | 77.4 | 80.5 | +3.12 |
| Sidy Cissoko | POR | 5 | 54.5 | 57.6 | +3.09 |
| Josh Minott | BKN | 4 | 67.1 | 70.0 | +2.97 |
| Svi Mykhailiuk | UTA | 6 | 54.1 | 56.9 | +2.77 |
| Donovan Clingan | POR | 5 | 69.4 | 72.1 | +2.71 |

ΔOVR 最低 10 人：

| 球員 | 隊 | N | lastOVR | OVR | ΔOVR |
|---|---|---|---|---|---|
| Jordan Poole | NOP | 4 | 62.7 | 57.1 | -5.59 |
| Scotty Pippen Jr. | MEM | 5 | 84.4 | 78.9 | -5.52 |
| Tre Mann | WAS | 2 | 50.6 | 45.4 | -5.18 |
| Ron Harper Jr. | BOS | 2 | 55.0 | 49.9 | -5.17 |
| Jaden Hardy | LAL | 3 | 44.9 | 39.9 | -5.04 |
| Jalen Green | PHX | 4 | 73.0 | 68.3 | -4.77 |
| Ben Saraf | BKN | 1 | 40.2 | 35.4 | -4.77 |
| Zach Collins | CHI | 4 | 70.6 | 65.9 | -4.69 |
| Luke Kornet | SAS | 6 | 79.0 | 74.5 | -4.51 |
| Nique Clifford | SAC | 5 | 63.9 | 59.6 | -4.32 |

\|ΔOVR\| 最大 10 人的屬性變動明細（x0→x̂；觀測 y 已做 usage 調整）：

- Kasparas Jakučionis（MIL，N=6，ΔOVR +6.54）：stamina 40.0→47.0（觀測 48.5、n=6、k=1、w=0.826）
- Jordan Poole（NOP，N=4，ΔOVR -5.59）：stamina 56.8→44.1（觀測 40.0、n=4、k=1、w=0.757）
- Scotty Pippen Jr.（MEM，N=5，ΔOVR -5.52）：stamina 44.7→40.9（觀測 40.0、n=5、k=1、w=0.806）
- Tre Mann（WAS，N=2，ΔOVR -5.18）：（無屬性變動）
- Ron Harper Jr.（BOS，N=2，ΔOVR -5.17）：（無屬性變動）
- Jaden Hardy（LAL，N=3，ΔOVR -5.04）：（無屬性變動）
- Jalen Green（PHX，N=4，ΔOVR -4.77）：stamina 63.6→66.6（觀測 67.6、n=4、k=1、w=0.759）
- Ben Saraf（BKN，N=1，ΔOVR -4.77）：stamina 43.2→41.8（觀測 40.0、n=1、k=1、w=0.428）
- Zach Collins（CHI，N=4，ΔOVR -4.69）：（無屬性變動）
- Luke Kornet（SAS，N=6，ΔOVR -4.51）：stamina 44.6→40.8（觀測 40.0、n=6、k=1、w=0.826）
