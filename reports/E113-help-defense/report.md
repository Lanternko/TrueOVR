# 總評
**1/5 失敗**（兩道資料硬條件沒過，照預註冊停下；評分維持 M2）

**這次目標**
在評分 M2 的對位分數補上「補防阻攻」「排除自己的對手基準」「被守者的助攻」三項，讓護框長人和守王牌的人名次往上，且樣本外對 RAPM 更準。

**進步了什麼**
- 程式與基準都對：M2 完全重現 E-110（權重、r 差 0），`npm test` 57 項全過，保護的檔案跑前跑後 sha256 一致。
- 數字上 M3 比 M2 高（A→B r 0.526→0.551、B→A 0.592→0.606），但**這不算數**：硬條件沒過，照規定不能拿來判定。拆開看，增益**全部來自「助攻算進對位」**（M3c 0.551／0.606），排除自己的基準幾乎沒差（M3b 0.526／0.591）。
- 名次（只報告，硬條件沒過）：Embiid 133→106、Brook Lopez 158→152、Gobert 107→105、Herbert Jones 140→133；Westbrook 91→124、Dru Smith 17→32，賭抄截型反而往下（和 lead 預期相反）。

**退步了什麼**
- **補防阻攻量不到**：對位資料的 `helpBlocks` 整季 241,753 列全部是 0（`switchesOn`、`matchupPotentialAssists` 也全 0），NBA 這支 API 有欄位但沒填。HELP_BLK 權重是 0，M3a 和 M2 一模一樣。d3 不過。
- **V（一次助攻值幾分）超出我定的範圍**：算出 2.75，門檻寫 1.8～2.6。playerPoints 含罰球和三分，每個進球平均就是 2.75 分；是我寫預註冊時範圍抓錯，不是資料錯。d4 不過。
- 半盲條件也沒過：5 個護框長人只 3 人往上（Jaren Jackson 211→223、Myles Turner 192→215 反而掉）；Dillon Brooks 173→193 掉。
- 兩個漏洞都是我凍結前沒先查整季欄位合計造成的（只看過一場的前幾列），寫成 lesson。

**直觀證據**
| 球員 | M2 名次 | M3 名次 | OVR 名次 |
|---|---|---|---|
| Joel Embiid | 133 | 106 | 17 |
| Brook Lopez | 158 | 152 | 144 |
| Rudy Gobert | 107 | 105 | 46 |
| Jaren Jackson Jr. | 211 | 223 | 49 |
| Myles Turner | 192 | 215 | 111 |
| Herbert Jones | 140 | 133 | 14 |
| Dillon Brooks | 173 | 193 | 41 |
| Russell Westbrook | 91 | 124 | 202 |
| Dru Smith | 17 | 32 | 220 |

（≥1000 分鐘 279 人；名次用 A→B 權重算整季評分。）

**要你決定的事**
1. **E-113 記為失敗、評分維持 M2**（照預註冊，建議）。
2. 「助攻算進對位」這一項看起來有用，但已經看過答案，不能在同一季再當盲測。要追的話另開 E-114：只測這一項、V 改成資料算出不設範圍，用**沒看過的季**（要抓 2024-25 對位資料）做樣本外驗證。
3. 補防阻攻這條路在這支 API 走不通，要改抓逐球（play-by-play）資料自己算，屬第二層。

---

## 細節

### 硬條件
| 代號 | 結果 | 數字 |
|---|---|---|
| c0 | 過 | M2 A→B、B→A 權重最大差 0、r 差 0 |
| c1 | 過 | `npm test` 57 passed, 0 failed（`npm-test.log`） |
| d3 | **不過** | 每人 HELP_BLK ≤ BLK 比例 100%，但 Σ HELP_BLK ÷ Σ BLK = 0（不在 (0,1]） |
| d4 | **不過** | V：A 2.758、B 2.746（> 2.6）；排除自己後退回聯盟平均的回合比例 0.22%／0.24%（≤10% 過） |

整季 matchup 欄位合計：helpBlocks 0、switchesOn 0、matchupPotentialAssists 0、matchupAssists 55,806、shootingFouls 25,472、playerPoints 280,440、matchupFieldGoalsMade 101,913。

### s1（因硬條件不過，無效，只記錄）
- A→B Δr = +0.0245，bootstrap 95% [+0.00003, +0.0472]；B→A Δr = +0.0143。名義上兩條件都成立。
- 各組樣本外 r（A→B／B→A）：M2 0.5265／0.5918、M3 0.5510／0.6060、M3a 0.5265／0.5918、M3b 0.5264／0.5914、M3c 0.5509／0.6064。

### 權重（A→B，每 36 分鐘）
- BLK：M2 0.168 → M3 0.234；PTS_SAVED 0.247 → PROD_SAVED_LO 0.179；DEFL 0.220 → 0.191；HELP_BLK 0。完整見 `results.json` `weights_AB`／`weights_BA`。

### 只報告
- 整季評分對 card 0.2.6 OVR 的 Spearman：M2 0.677、M3 0.673；對四季 RAPM 防守名次：M2 0.409、M3 0.420。
- 單場評分 > 10／= 0：M2 5.5%／2.1%，M3 5.3%／2.0%。
- Coulibaly 27→27、Keldon Johnson 56→62。
- OVR 對照用 card 0.2.6（同 E-110 人群）；`results.json` 另附對 card 0.2.7 的 Spearman。

### 檔案
`e113.py`、`results.json`、`ranking.csv`、`npm-test.log`；預註冊 `preregistration.md`（sha256 c1ef9562…afc7，未改）。
