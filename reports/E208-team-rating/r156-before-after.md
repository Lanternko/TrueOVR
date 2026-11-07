# R-156 前後對照：焦灼乘數重量改「在隊期間沒上場記 0 分鐘」

同一份傷兵資料（`--no-fetch`，injuries.json 不變）、同為 200 場／名單、同引擎；R-153 版＝改動前的 team-ratings.json（乘數只算有出賽場次），R-156 版＝本次改動。
全員＝近況版（不扣人），可用＝今日陣容版。Net＝對聯盟平均隊每場分差。

## 規則與近似

- 在隊期間＝球員該季替這隊第一場出賽（MIN>0）到最後一場出賽之間、這隊的所有比賽；季中交易的人分兩段各算各隊。期間內沒出現在 box score 的場次記 0 分鐘；焦灼場與全部場分子分母同規則；槽排名用含 0 的場均。資料、焦灼定義（分差 ≤5 或延長賽）、兩季合併、延長賽換算 48 分鐘皆不變。
- **近似**：歷史沒有傷兵資料，傷缺的場次也記 0。假設傷缺在焦灼與非焦灼場大致同比例出現，對「焦灼 ÷ 全部」的比值影響小；未另做傷兵推估。

## 11 槽乘數對照

| 槽 | R-153（只算出賽場次） | R-156（在隊期間含 0） | 全部場平均分鐘(R-156) | 樣本(全部/焦灼) |
|---|---|---|---|---|
| 1 | 1.0624 | 1.0572 | 31.07 | 3934/1048 |
| 2 | 1.0487 | 1.0464 | 29.03 | 4311/1134 |
| 3 | 1.0557 | 1.0428 | 27.28 | 3823/1007 |
| 4 | 1.0494 | 1.0344 | 25.12 | 4049/1067 |
| 5 | 1.0430 | 1.0505 | 23.78 | 3994/1082 |
| 6 | 1.0296 | 1.0181 | 21.66 | 3830/1009 |
| 7 | 1.0179 | 1.0338 | 20.31 | 3724/977 |
| 8 | 1.0156 | 1.0195 | 18.72 | 3754/978 |
| 9 | 1.0254 | 1.0175 | 16.29 | 3436/902 |
| 10 | 1.0368 | 0.9870 | 14.97 | 3735/959 |
| 11+ | 1.1088 | 0.9027 | 8.08 | 36135/9360 |

第 11+ 槽由 1.1088 降到 0.9027，不再高於前幾槽（原本的高估來自深板凳只在隊友犯滿或受傷時才上、一上就打比較久）。槽 10 由 1.0368 降到 0.987。11+ 槽低於 1 的解讀：深板凳在焦灼場被冷凍（符合 R-156 的前提）。

## 30 隊 Net 與排名

| 隊 | 傷兵 | R-153 全員 Net(排名) | R-153 可用 Net(排名) | R-156 全員 Net(排名) | R-156 可用 Net(排名) | 可用−全員 R-153 | 可用−全員 R-156 |
|---|---|---|---|---|---|---|---|
| MIN | 3 | +4.26 (8) | +9.93 (1) | +3.66 (10) | +8.97 (1) | +5.67 | +5.31 |
| CLE | 2 | +5.35 (6) | +8.61 (3) | +6.09 (7) | +8.88 (2) | +3.26 | +2.79 |
| LAL | 1 | +8.51 (1) | +8.51 (4) | +8.86 (1) | +8.86 (3) | +0.00 | +0.00 |
| MEM | 2 | +6.77 (5) | +8.38 (5) | +6.62 (3) | +8.53 (4) | +1.61 | +1.91 |
| BOS | 2 | +8.26 (2) | +8.64 (2) | +8.23 (2) | +8.15 (5) | +0.38 | -0.08 |
| OKC | 5 | +7.45 (4) | +5.44 (7) | +6.52 (5) | +6.86 (6) | -2.01 | +0.34 |
| SAS | 1 | +7.83 (3) | +7.83 (6) | +6.12 (6) | +6.12 (7) | +0.00 | +0.00 |
| DEN | 2 | +2.49 (11) | +2.49 (8) | +4.54 (9) | +4.54 (8) | +0.00 | +0.00 |
| DET | 2 | +3.56 (9) | +2.26 (10) | +6.54 (4) | +3.89 (9) | -1.30 | -2.65 |
| POR | 2 | +0.83 (13) | +1.97 (11) | -0.96 (17) | +2.26 (10) | +1.14 | +3.22 |
| HOU | 2 | +4.99 (7) | +0.00 (12) | +5.12 (8) | +1.80 (11) | -4.99 | -3.32 |
| MIA | 0 | -0.92 (18) | -0.92 (16) | +0.62 (13) | +0.62 (12) | +0.00 | +0.00 |
| NOP | 3 | -1.38 (19) | +2.31 (9) | -0.01 (15) | +0.34 (13) | +3.69 | +0.35 |
| CHA | 2 | -0.54 (16) | -0.54 (15) | +0.12 (14) | +0.12 (14) | +0.00 | +0.00 |
| NYK | 0 | -0.15 (14) | -0.15 (13) | -0.09 (16) | -0.09 (15) | +0.00 | +0.00 |
| GSW | 6 | -0.65 (17) | -1.15 (17) | -2.72 (19) | -0.10 (16) | -0.50 | +2.63 |
| UTA | 3 | +1.28 (12) | -3.47 (21) | +1.07 (12) | -1.45 (17) | -4.74 | -2.52 |
| ORL | 5 | -3.90 (22) | -2.13 (19) | -3.82 (22) | -2.21 (18) | +1.76 | +1.61 |
| TOR | 2 | +2.94 (10) | -1.57 (18) | +1.99 (11) | -2.79 (19) | -4.52 | -4.79 |
| PHI | 2 | -0.51 (15) | -0.51 (14) | -2.81 (20) | -2.81 (20) | +0.00 | +0.00 |
| PHX | 2 | -2.82 (20) | -3.51 (22) | -3.65 (21) | -3.30 (21) | -0.69 | +0.35 |
| DAL | 5 | -4.72 (24) | -4.30 (23) | -7.15 (29) | -3.73 (22) | +0.42 | +3.42 |
| BKN | 1 | -4.42 (23) | -3.08 (20) | -4.53 (23) | -3.98 (23) | +1.34 | +0.55 |
| ATL | 3 | -3.34 (21) | -4.84 (24) | -2.08 (18) | -4.40 (24) | -1.50 | -2.32 |
| CHI | 1 | -5.82 (26) | -5.82 (25) | -5.05 (24) | -5.05 (25) | +0.00 | +0.00 |
| MIL | 0 | -6.72 (28) | -6.72 (26) | -5.05 (25) | -5.05 (26) | +0.00 | +0.00 |
| LAC | 6 | -7.59 (29) | -7.34 (28) | -5.53 (27) | -6.05 (27) | +0.25 | -0.52 |
| IND | 11 | -6.54 (27) | -6.80 (27) | -6.51 (28) | -6.65 (28) | -0.26 | -0.14 |
| SAC | 3 | -9.31 (30) | -8.42 (29) | -10.61 (30) | -7.88 (29) | +0.89 | +2.73 |
| WAS | 6 | -5.21 (25) | -9.14 (30) | -5.53 (26) | -8.58 (30) | -3.92 | -3.06 |

**可用版 Net 比全員版高的隊數：R-153 版 11 隊 → R-156 版 12 隊。**（有傷兵的隊才有差；兩版名單相同者差為 0 不計）

R-153 高於者：BKN, BOS, CLE, DAL, LAC, MEM, MIN, NOP, ORL, POR, SAC
R-156 高於者：BKN, CLE, DAL, GSW, MEM, MIN, NOP, OKC, ORL, PHX, POR, SAC

## 輪替分鐘（OKC、BOS、MIN、MEM、POR）

### OKC 可用版（傷兵 5 人：Thomas Sorber(Out), Cason Wallace(Out), Chet Holmgren(Out), Jalen Williams(Out), Alex Caruso(Out), Nikola Topic(Out)）

| 球員 | OVR | R-153 分鐘 | R-156 分鐘 |
|---|---|---|---|
| Shai Gilgeous-Alexander | 107.9 | 36.0 | 36.0 |
| Ajay Mitchell | 76.8 | 31.2 | 31.5 |
| Jared McCain | 52.5 | 29.1 | 29.1 |
| Isaiah Hartenstein | 75.2 | 28.4 | 28.3 |
| Jaylin Williams | 80.3 | 21.3 | 21.7 |
| Aday Mara | 58.2 | 20.6 | 20.7 |
| Josh Dix |  | 18.7 | 19.3 |
| Kenrich Williams | 68.0 | 18.2 | 18.5 |
| Bennett Stirtz | 55.4 | 17.0 | 17.1 |
| Micah Peavy | 49.7 | 13.2 | 12.7 |
| Brooks Barnhizer | 53.2 | 6.2 | 5.1 |

### OKC 全員版（傷兵 5 人：Thomas Sorber(Out), Cason Wallace(Out), Chet Holmgren(Out), Jalen Williams(Out), Alex Caruso(Out), Nikola Topic(Out)）

| 球員 | OVR | R-153 分鐘 | R-156 分鐘 |
|---|---|---|---|
| Shai Gilgeous-Alexander | 107.9 | 26.3 | 27.5 |
| Jalen Williams | 90.9 | 24.5 | 25.6 |
| Chet Holmgren | 93.5 | 23.4 | 24.2 |
| Ajay Mitchell | 76.8 | 20.9 | 21.5 |
| Jared McCain | 52.5 | 19.2 | 20.3 |
| Isaiah Hartenstein | 75.2 | 18.6 | 19.3 |
| Alex Caruso | 84.3 | 14.2 | 15.2 |
| Jaylin Williams | 80.3 | 13.9 | 14.6 |
| Aday Mara | 58.2 | 13.7 | 14.3 |
| Josh Dix |  | 12.8 | 12.7 |
| Cason Wallace | 79.9 | 13.3 | 11.4 |
| Kenrich Williams | 68.0 | 13.3 | 11.3 |
| Bennett Stirtz | 55.4 | 12.3 | 10.5 |
| Micah Peavy | 49.7 | 9.4 | 8.1 |
| Brooks Barnhizer | 53.2 | 4.2 | 3.6 |

### BOS 可用版（傷兵 2 人：Paul George(Day-To-Day), Devin Carter(Out)）

| 球員 | OVR | R-153 分鐘 | R-156 分鐘 |
|---|---|---|---|
| Jayson Tatum | 94.3 | 36.0 | 36.0 |
| Derrick White | 87.8 | 31.3 | 31.9 |
| Payton Pritchard | 84.6 | 29.6 | 29.9 |
| Neemias Queta | 80.5 | 22.8 | 23.0 |
| Baylor Scheierman | 69.5 | 20.7 | 21.4 |
| Sam Hauser | 74.8 | 20.4 | 20.7 |
| Mitchell Robinson | 72.0 | 19.4 | 20.2 |
| Jordan Walsh | 60.2 | 16.1 | 16.5 |
| Hugo González | 63.5 | 13.0 | 13.2 |
| Luka Garza | 68.3 | 12.2 | 11.9 |
| Ron Harper Jr. | 45.5 | 6.1 | 5.1 |
| Mike Conley | 58.1 | 6.0 | 5.0 |
| Chris Cenac Jr. | 53.0 | 3.6 | 3.0 |
| Dillon Mitchell |  | 2.8 | 2.3 |

### BOS 全員版（傷兵 2 人：Paul George(Day-To-Day), Devin Carter(Out)）

| 球員 | OVR | R-153 分鐘 | R-156 分鐘 |
|---|---|---|---|
| Jayson Tatum | 94.3 | 32.6 | 33.3 |
| Paul George | 91.8 | 28.3 | 29.0 |
| Derrick White | 87.8 | 27.6 | 28.0 |
| Payton Pritchard | 84.6 | 25.8 | 26.1 |
| Neemias Queta | 80.5 | 19.9 | 20.5 |
| Sam Hauser | 74.8 | 17.7 | 18.5 |
| Baylor Scheierman | 69.5 | 17.9 | 18.2 |
| Mitchell Robinson | 72.0 | 17.0 | 17.5 |
| Jordan Walsh | 60.2 | 14.2 | 14.5 |
| Hugo González | 63.5 | 11.5 | 11.2 |
| Luka Garza | 68.3 | 11.4 | 9.5 |
| Ron Harper Jr. | 45.5 | 5.4 | 4.5 |
| Mike Conley | 58.1 | 5.3 | 4.4 |
| Chris Cenac Jr. | 53.0 | 3.2 | 2.6 |
| Dillon Mitchell |  | 2.4 | 2.0 |

### MIN 可用版（傷兵 3 人：Terrence Shannon Jr.(Day-To-Day), Anthony Edwards(Out), Donte DiVincenzo(Out)）

| 球員 | OVR | R-153 分鐘 | R-156 分鐘 |
|---|---|---|---|
| Jaden McDaniels | 82.0 | 36.0 | 36.0 |
| Jonathan Kuminga | 69.4 | 34.2 | 34.5 |
| Ayo Dosunmu | 81.3 | 33.8 | 33.8 |
| Rudy Gobert | 84.2 | 33.4 | 33.3 |
| LaMelo Ball | 75.2 | 28.8 | 29.4 |
| Joan Beringer | 57.4 | 19.8 | 19.7 |
| Trey Lyles | 63.7671 | 18.1 | 18.6 |
| Bones Hyland | 69.2 | 13.0 | 13.2 |
| Jaylen Clark | 56.0 | 12.1 | 12.1 |
| Cody Williams | 39.4 | 4.3 | 4.1 |
| Zyon Pullin | 56.7 | 3.6 | 3.0 |
| Isaiah Evans | 53.3 | 2.9 | 2.4 |

### MIN 全員版（傷兵 3 人：Terrence Shannon Jr.(Day-To-Day), Anthony Edwards(Out), Donte DiVincenzo(Out)）

| 球員 | OVR | R-153 分鐘 | R-156 分鐘 |
|---|---|---|---|
| Anthony Edwards | 94.5 | 29.6 | 30.1 |
| Jaden McDaniels | 82.0 | 28.9 | 29.5 |
| Jonathan Kuminga | 69.4 | 27.3 | 27.5 |
| Rudy Gobert | 84.2 | 26.3 | 27.1 |
| Ayo Dosunmu | 81.3 | 26.7 | 26.9 |
| LaMelo Ball | 75.2 | 22.6 | 22.8 |
| Terrence Shannon Jr | 63.2 | 18.8 | 19.5 |
| Joan Beringer | 57.4 | 15.5 | 15.9 |
| Trey Lyles | 63.7671 | 14.5 | 14.6 |
| Bones Hyland | 69.2 | 10.6 | 10.3 |
| Jaylen Clark | 56.0 | 10.4 | 8.6 |
| Cody Williams | 39.4 | 3.6 | 3.0 |
| Zyon Pullin | 56.7 | 2.9 | 2.4 |
| Isaiah Evans | 53.3 | 2.3 | 1.9 |

### MEM 可用版（傷兵 2 人：Quinten Post(Day-To-Day), Scotty Pippen Jr.(Day-To-Day)）

| 球員 | OVR | R-153 分鐘 | R-156 分鐘 |
|---|---|---|---|
| Cameron Boozer | 69.5 | 28.8 | 29.5 |
| Ty Jerome | 96.0 | 27.4 | 28.2 |
| Cedric Coward | 81.3 | 25.5 | 26.0 |
| Jaylen Wells | 68.4 | 25.0 | 25.3 |
| Jerami Grant | 49.2 | 21.6 | 22.3 |
| Javon Small | 75.0 | 17.2 | 17.9 |
| Zach Edey | 71.2 | 17.4 | 17.7 |
| Isaiah Stewart | 70.7 | 16.8 | 17.4 |
| Cam Spencer | 81.6 | 16.7 | 17.0 |
| GG Jackson | 48.5 | 14.8 | 14.5 |
| Kris Murray | 63.4 | 12.8 | 10.8 |
| Taylor Hendricks | 52.2 | 4.3 | 3.6 |
| Olivier-Maxence Prosper | 57.3 | 3.2 | 2.7 |
| Karim López |  | 3.2 | 2.7 |
| Carson Cooper |  | 3.1 | 2.6 |
| Jahmai Mashack | 35.8 | 2.1 | 1.8 |

### MEM 全員版（傷兵 2 人：Quinten Post(Day-To-Day), Scotty Pippen Jr.(Day-To-Day)）

| 球員 | OVR | R-153 分鐘 | R-156 分鐘 |
|---|---|---|---|
| Cameron Boozer | 69.5 | 25.7 | 26.7 |
| Ty Jerome | 96.0 | 24.4 | 25.5 |
| Cedric Coward | 81.3 | 22.7 | 23.5 |
| Jaylen Wells | 68.4 | 22.2 | 23.0 |
| Jerami Grant | 49.2 | 19.2 | 20.2 |
| Javon Small | 75.0 | 15.3 | 16.3 |
| Zach Edey | 71.2 | 15.5 | 16.1 |
| Isaiah Stewart | 70.7 | 15.0 | 15.8 |
| Cam Spencer | 81.6 | 14.8 | 15.4 |
| GG Jackson | 48.5 | 13.1 | 13.1 |
| Scotty Pippen Jr. | 74.7 | 13.6 | 11.6 |
| Quinten Post | 63.0 | 12.8 | 11.0 |
| Kris Murray | 63.4 | 11.4 | 9.7 |
| Taylor Hendricks | 52.2 | 3.8 | 3.3 |
| Olivier-Maxence Prosper | 57.3 | 2.9 | 2.5 |
| Karim López |  | 2.9 | 2.5 |
| Carson Cooper |  | 2.7 | 2.3 |
| Jahmai Mashack | 35.8 | 1.9 | 1.6 |

### POR 可用版（傷兵 2 人：Ja Morant(Out), Shaedon Sharpe(Out)）

| 球員 | OVR | R-153 分鐘 | R-156 分鐘 |
|---|---|---|---|
| Deni Avdija | 83.2 | 30.1 | 31.0 |
| Damian Lillard | 85.6044 | 27.2 | 28.0 |
| Toumani Camara | 79.0 | 25.3 | 25.8 |
| Jrue Holiday | 87.7 | 23.9 | 24.4 |
| Donovan Clingan | 72.1 | 22.2 | 23.1 |
| Scoot Henderson | 52.3 | 19.8 | 20.8 |
| Sidy Cissoko | 60.0 | 20.1 | 20.6 |
| Robert Williams III | 76.1 | 15.1 | 15.7 |
| Chris Youngblood | 48.2 | 10.0 | 10.3 |
| Vít Krejčí | 67.5 | 9.2 | 9.1 |
| Yang Hansen | 49.3 | 9.8 | 8.2 |
| Micah Potter | 56.1 | 8.0 | 6.8 |
| Branden Carlson | 51.9 | 7.8 | 6.6 |
| Jayson Kent | 49.5 | 6.9 | 5.8 |
| John Tonje | 51.8 | 4.5 | 3.8 |

### POR 全員版（傷兵 2 人：Ja Morant(Out), Shaedon Sharpe(Out)）

| 球員 | OVR | R-153 分鐘 | R-156 分鐘 |
|---|---|---|---|
| Deni Avdija | 83.2 | 27.4 | 28.3 |
| Damian Lillard | 85.6044 | 24.7 | 25.6 |
| Toumani Camara | 79.0 | 22.9 | 23.5 |
| Jrue Holiday | 87.7 | 21.6 | 22.6 |
| Ja Morant | 80.0 | 21.9 | 22.4 |
| Donovan Clingan | 72.1 | 19.9 | 20.4 |
| Sidy Cissoko | 60.0 | 18.1 | 19.1 |
| Scoot Henderson | 52.3 | 18.0 | 18.7 |
| Robert Williams III | 76.1 | 13.8 | 14.3 |
| Chris Youngblood | 48.2 | 9.2 | 9.1 |
| Vít Krejčí | 67.5 | 8.9 | 7.6 |
| Yang Hansen | 49.3 | 8.9 | 7.5 |
| Micah Potter | 56.1 | 7.3 | 6.2 |
| Branden Carlson | 51.9 | 7.1 | 6.0 |
| Jayson Kent | 49.5 | 6.3 | 5.3 |
| John Tonje | 51.8 | 4.1 | 3.4 |
