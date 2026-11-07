# R-153 前後對照：分鐘改「教練近況分鐘 × 焦灼乘數」

同一份傷兵資料（`--no-fetch`，injuries.json 不變）、同為 200 場／名單、同引擎；R-151 版＝git HEAD（`d9031ae`）固定分鐘表 36/36/34/32/30/26/22/14/10，R-153 版＝本次改動。
全員＝近況版（不扣人），可用＝今日陣容版（Out/Doubtful/Questionable/Day-To-Day/Suspension 預先排除）。Net＝對聯盟平均隊每場分差。

## 30 隊 Net 與排名

| 隊 | 傷兵 | R-151 全員 Net(排名) | R-151 可用 Net(排名) | R-153 全員 Net(排名) | R-153 可用 Net(排名) | 可用−全員 R-151 | 可用−全員 R-153 |
|---|---|---|---|---|---|---|---|
| MIN | 3 | +4.41 (8) | +6.67 (4) | +4.26 (8) | +9.93 (1) | +2.26 | +5.67 |
| BOS | 2 | +6.53 (6) | +9.80 (1) | +8.26 (2) | +8.64 (2) | +3.27 | +0.38 |
| CLE | 2 | +8.99 (3) | +6.15 (5) | +5.35 (6) | +8.61 (3) | -2.84 | +3.26 |
| LAL | 1 | +9.45 (2) | +9.45 (2) | +8.51 (1) | +8.51 (4) | +0.00 | +0.00 |
| MEM | 2 | +8.06 (4) | +8.06 (3) | +6.77 (5) | +8.38 (5) | +0.00 | +1.61 |
| SAS | 1 | +4.72 (7) | +4.72 (8) | +7.83 (3) | +7.83 (6) | +0.00 | +0.00 |
| OKC | 5 | +10.93 (1) | +5.93 (6) | +7.45 (4) | +5.44 (7) | -5.00 | -2.01 |
| DEN | 2 | +1.66 (11) | +1.66 (10) | +2.49 (11) | +2.49 (8) | +0.00 | +0.00 |
| NOP | 3 | -1.08 (18) | -3.37 (21) | -1.38 (19) | +2.31 (9) | -2.29 | +3.69 |
| DET | 2 | +7.85 (5) | +4.47 (9) | +3.56 (9) | +2.26 (10) | -3.38 | -1.30 |
| POR | 2 | +2.15 (10) | +5.13 (7) | +0.83 (13) | +1.97 (11) | +2.98 | +1.14 |
| HOU | 2 | +2.47 (9) | +0.99 (11) | +4.99 (7) | +0.00 (12) | -1.48 | -4.99 |
| NYK | 0 | +0.29 (14) | +0.29 (12) | -0.15 (14) | -0.15 (13) | +0.00 | +0.00 |
| PHI | 2 | -1.96 (20) | -1.96 (18) | -0.51 (15) | -0.51 (14) | +0.00 | +0.00 |
| CHA | 2 | -0.23 (16) | -0.23 (14) | -0.54 (16) | -0.54 (15) | +0.00 | +0.00 |
| MIA | 0 | +0.16 (15) | +0.16 (13) | -0.92 (18) | -0.92 (16) | +0.00 | +0.00 |
| GSW | 6 | -1.01 (17) | -2.14 (19) | -0.65 (17) | -1.15 (17) | -1.13 | -0.50 |
| TOR | 2 | +0.70 (13) | -1.57 (15) | +2.94 (10) | -1.57 (18) | -2.28 | -4.52 |
| ORL | 5 | -4.58 (23) | -5.49 (24) | -3.90 (22) | -2.13 (19) | -0.91 | +1.76 |
| BKN | 1 | -2.87 (21) | -1.86 (17) | -4.42 (23) | -3.08 (20) | +1.02 | +1.34 |
| UTA | 3 | +1.25 (12) | -1.81 (16) | +1.28 (12) | -3.47 (21) | -3.06 | -4.74 |
| PHX | 2 | -4.30 (22) | -4.96 (23) | -2.82 (20) | -3.51 (22) | -0.66 | -0.69 |
| DAL | 5 | -7.50 (27) | -7.58 (27) | -4.72 (24) | -4.30 (23) | -0.08 | +0.42 |
| ATL | 3 | -1.25 (19) | -3.19 (20) | -3.34 (21) | -4.84 (24) | -1.94 | -1.50 |
| CHI | 1 | -4.68 (24) | -4.68 (22) | -5.82 (26) | -5.82 (25) | +0.00 | +0.00 |
| MIL | 0 | -7.14 (26) | -7.14 (25) | -6.72 (28) | -6.72 (26) | +0.00 | +0.00 |
| IND | 11 | -10.51 (30) | -8.16 (28) | -6.54 (27) | -6.80 (27) | +2.35 | -0.26 |
| LAC | 6 | -7.89 (28) | -7.50 (26) | -7.59 (29) | -7.34 (28) | +0.39 | +0.25 |
| SAC | 3 | -9.65 (29) | -11.78 (30) | -9.31 (30) | -8.42 (29) | -2.13 | +0.89 |
| WAS | 6 | -4.98 (25) | -10.31 (29) | -5.21 (25) | -9.14 (30) | -5.32 | -3.92 |

**可用版 Net 比全員版高的隊數：R-151 版 6 隊 → R-153 版 11 隊。**（有傷兵的隊才有差；兩版名單相同者差為 0 不計）

R-151 高於者：BOS, LAC, MIN, BKN, IND, POR
R-153 高於者：BOS, CLE, NOP, DAL, LAC, MIN, BKN, ORL, POR, SAC, MEM

## 輪替分鐘（OKC、MEM、BOS、MIN、POR）

### OKC 可用版（傷兵 5 人：Cason Wallace(Out), Chet Holmgren(Out), Jalen Williams(Out), Alex Caruso(Out), Nikola Topic(Out)）

| 球員 | OVR | R-151 分鐘 | R-153 分鐘 |
|---|---|---|---|
| Shai Gilgeous-Alexander | 108 | 36.0 | 36.0 |
| Ajay Mitchell | 77 | 36.0 | 31.2 |
| Jared McCain | 52 | 34.0 | 29.1 |
| Isaiah Hartenstein | 75 | 32.0 | 28.4 |
| Jaylin Williams | 80 | 30.0 | 21.3 |
| Aday Mara | 58 | 26.0 | 20.6 |
| Josh Dix |  | 22.0 | 18.7 |
| Kenrich Williams | 68 | 14.0 | 18.2 |
| Bennett Stirtz | 55 | 10.0 | 17.0 |
| Micah Peavy | 50 | — | 13.2 |
| Brooks Barnhizer | 53 | — | 6.2 |

### OKC 全員版（傷兵 5 人：Cason Wallace(Out), Chet Holmgren(Out), Jalen Williams(Out), Alex Caruso(Out), Nikola Topic(Out)）

| 球員 | OVR | R-151 分鐘 | R-153 分鐘 |
|---|---|---|---|
| Shai Gilgeous-Alexander | 108 | 36.0 | 26.3 |
| Jalen Williams | 91 | 36.0 | 24.5 |
| Chet Holmgren | 94 | 34.0 | 23.4 |
| Ajay Mitchell | 77 | 32.0 | 20.9 |
| Jared McCain | 52 | 30.0 | 19.2 |
| Isaiah Hartenstein | 75 | 26.0 | 18.6 |
| Alex Caruso | 84 | 22.0 | 14.2 |
| Jaylin Williams | 80 | 14.0 | 13.9 |
| Aday Mara | 58 | 10.0 | 13.7 |
| Cason Wallace | 80 | — | 13.3 |
| Kenrich Williams | 68 | — | 13.3 |
| Josh Dix |  | — | 12.8 |
| Bennett Stirtz | 55 | — | 12.3 |
| Micah Peavy | 50 | — | 9.4 |
| Brooks Barnhizer | 53 | — | 4.2 |

### MEM 可用版（傷兵 2 人：Quinten Post(Day-To-Day), Scotty Pippen Jr.(Day-To-Day)）

| 球員 | OVR | R-151 分鐘 | R-153 分鐘 |
|---|---|---|---|
| Cameron Boozer | 70 | 36.0 | 28.8 |
| Ty Jerome | 96 | 36.0 | 27.4 |
| Cedric Coward | 81 | 34.0 | 25.5 |
| Jaylen Wells | 68 | 32.0 | 25.0 |
| Jerami Grant | 49 | 30.0 | 21.6 |
| Zach Edey | 71 | 26.0 | 17.4 |
| Javon Small | 75 | 22.0 | 17.2 |
| Isaiah Stewart | 71 | 14.0 | 16.8 |
| Cam Spencer | 82 | 10.0 | 16.7 |
| GG Jackson | 48 | — | 14.8 |
| Kris Murray | 63 | — | 12.8 |
| Taylor Hendricks | 52 | — | 4.3 |
| Olivier-Maxence Prosper | 57 | — | 3.2 |
| Karim López |  | — | 3.2 |
| Carson Cooper |  | — | 3.1 |
| Jahmai Mashack | 36 | — | 2.1 |

### MEM 全員版（傷兵 2 人：Quinten Post(Day-To-Day), Scotty Pippen Jr.(Day-To-Day)）

| 球員 | OVR | R-151 分鐘 | R-153 分鐘 |
|---|---|---|---|
| Cameron Boozer | 70 | 36.0 | 25.7 |
| Ty Jerome | 96 | 36.0 | 24.4 |
| Cedric Coward | 81 | 34.0 | 22.7 |
| Jaylen Wells | 68 | 32.0 | 22.2 |
| Jerami Grant | 49 | 30.0 | 19.2 |
| Zach Edey | 71 | 26.0 | 15.5 |
| Javon Small | 75 | 22.0 | 15.3 |
| Isaiah Stewart | 71 | 14.0 | 15.0 |
| Cam Spencer | 82 | 10.0 | 14.8 |
| Scotty Pippen Jr. | 75 | — | 13.6 |
| GG Jackson | 48 | — | 13.1 |
| Quinten Post | 63 | — | 12.8 |
| Kris Murray | 63 | — | 11.4 |
| Taylor Hendricks | 52 | — | 3.8 |
| Olivier-Maxence Prosper | 57 | — | 2.9 |
| Karim López |  | — | 2.9 |
| Carson Cooper |  | — | 2.7 |
| Jahmai Mashack | 36 | — | 1.9 |

### BOS 可用版（傷兵 2 人：Paul George(Day-To-Day), Devin Carter(Out)）

| 球員 | OVR | R-151 分鐘 | R-153 分鐘 |
|---|---|---|---|
| Jayson Tatum | 94 | 36.0 | 36.0 |
| Derrick White | 88 | 36.0 | 31.3 |
| Payton Pritchard | 85 | 34.0 | 29.6 |
| Neemias Queta | 80 | 32.0 | 22.8 |
| Baylor Scheierman | 70 | 30.0 | 20.7 |
| Sam Hauser | 75 | 26.0 | 20.4 |
| Mitchell Robinson | 72 | 22.0 | 19.4 |
| Jordan Walsh | 60 | 14.0 | 16.1 |
| Hugo González | 64 | 10.0 | 13.0 |
| Luka Garza | 68 | — | 12.2 |
| Ron Harper Jr. | 46 | — | 6.1 |
| Mike Conley | 58 | — | 6.0 |
| Chris Cenac Jr. | 53 | — | 3.6 |
| Dillon Mitchell |  | — | 2.8 |

### BOS 全員版（傷兵 2 人：Paul George(Day-To-Day), Devin Carter(Out)）

| 球員 | OVR | R-151 分鐘 | R-153 分鐘 |
|---|---|---|---|
| Jayson Tatum | 94 | 36.0 | 32.6 |
| Paul George | 92 | 36.0 | 28.3 |
| Derrick White | 88 | 34.0 | 27.6 |
| Payton Pritchard | 85 | 32.0 | 25.8 |
| Neemias Queta | 80 | 30.0 | 19.9 |
| Baylor Scheierman | 70 | 26.0 | 17.9 |
| Sam Hauser | 75 | 22.0 | 17.7 |
| Mitchell Robinson | 72 | 14.0 | 17.0 |
| Jordan Walsh | 60 | 10.0 | 14.2 |
| Hugo González | 64 | — | 11.5 |
| Luka Garza | 68 | — | 11.4 |
| Ron Harper Jr. | 46 | — | 5.4 |
| Mike Conley | 58 | — | 5.3 |
| Chris Cenac Jr. | 53 | — | 3.2 |
| Dillon Mitchell |  | — | 2.4 |

### MIN 可用版（傷兵 3 人：Terrence Shannon Jr.(Day-To-Day), Anthony Edwards(Out), Donte DiVincenzo(Out)）

| 球員 | OVR | R-151 分鐘 | R-153 分鐘 |
|---|---|---|---|
| Jaden McDaniels | 82 | 36.0 | 36.0 |
| Jonathan Kuminga | 69 | 36.0 | 34.2 |
| Ayo Dosunmu | 81 | 34.0 | 33.8 |
| Rudy Gobert | 84 | 32.0 | 33.4 |
| LaMelo Ball | 75 | 30.0 | 28.8 |
| Joan Beringer | 57 | 26.0 | 19.8 |
| Trey Lyles | 64 | 22.0 | 18.1 |
| Bones Hyland | 69 | 14.0 | 13.0 |
| Jaylen Clark | 56 | 10.0 | 12.1 |
| Cody Williams | 39 | — | 4.3 |
| Zyon Pullin | 57 | — | 3.6 |
| Isaiah Evans | 53 | — | 2.9 |

### MIN 全員版（傷兵 3 人：Terrence Shannon Jr.(Day-To-Day), Anthony Edwards(Out), Donte DiVincenzo(Out)）

| 球員 | OVR | R-151 分鐘 | R-153 分鐘 |
|---|---|---|---|
| Anthony Edwards | 94 | 36.0 | 29.6 |
| Jaden McDaniels | 82 | 36.0 | 28.9 |
| Jonathan Kuminga | 69 | 34.0 | 27.3 |
| Ayo Dosunmu | 81 | 32.0 | 26.7 |
| Rudy Gobert | 84 | 30.0 | 26.3 |
| LaMelo Ball | 75 | 26.0 | 22.6 |
| Terrence Shannon Jr | 63 | 22.0 | 18.8 |
| Joan Beringer | 57 | 14.0 | 15.5 |
| Trey Lyles | 64 | 10.0 | 14.5 |
| Bones Hyland | 69 | — | 10.6 |
| Jaylen Clark | 56 | — | 10.4 |
| Cody Williams | 39 | — | 3.6 |
| Zyon Pullin | 57 | — | 2.9 |
| Isaiah Evans | 53 | — | 2.3 |

### POR 可用版（傷兵 2 人：Ja Morant(Out), Shaedon Sharpe(Out)）

| 球員 | OVR | R-151 分鐘 | R-153 分鐘 |
|---|---|---|---|
| Deni Avdija | 83 | 36.0 | 30.1 |
| Damian Lillard | 86 | 36.0 | 27.2 |
| Toumani Camara | 79 | 34.0 | 25.3 |
| Jrue Holiday | 88 | 32.0 | 23.9 |
| Donovan Clingan | 72 | 30.0 | 22.2 |
| Sidy Cissoko | 60 | 26.0 | 20.1 |
| Scoot Henderson | 52 | 22.0 | 19.8 |
| Robert Williams III | 76 | 14.0 | 15.1 |
| Chris Youngblood | 48 | 10.0 | 10.0 |
| Yang Hansen | 49 | — | 9.8 |
| Vít Krejčí | 68 | — | 9.2 |
| Micah Potter | 56 | — | 8.0 |
| Branden Carlson | 52 | — | 7.8 |
| Jayson Kent | 50 | — | 6.9 |
| John Tonje | 52 | — | 4.5 |

### POR 全員版（傷兵 2 人：Ja Morant(Out), Shaedon Sharpe(Out)）

| 球員 | OVR | R-151 分鐘 | R-153 分鐘 |
|---|---|---|---|
| Deni Avdija | 83 | 36.0 | 27.4 |
| Damian Lillard | 86 | 36.0 | 24.7 |
| Toumani Camara | 79 | 34.0 | 22.9 |
| Ja Morant | 80 | 32.0 | 21.9 |
| Jrue Holiday | 88 | 30.0 | 21.6 |
| Donovan Clingan | 72 | 26.0 | 19.9 |
| Sidy Cissoko | 60 | 22.0 | 18.1 |
| Scoot Henderson | 52 | 14.0 | 18.0 |
| Robert Williams III | 76 | 10.0 | 13.8 |
| Chris Youngblood | 48 | — | 9.2 |
| Vít Krejčí | 68 | — | 8.9 |
| Yang Hansen | 49 | — | 8.9 |
| Micah Potter | 56 | — | 7.3 |
| Branden Carlson | 52 | — | 7.1 |
| Jayson Kent | 50 | — | 6.3 |
| John Tonje | 52 | — | 4.1 |

## 檢查

R-153 版 30 隊 × 2 版：合計 240、人數 ≥7 時單人 ≤36 → 違規 0 個。
