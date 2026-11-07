# E-113 預註冊：評分的防守對位補上補防與對手強度（第一層，不抓新資料）

- 日期：2026-10-30。來源：使用者看了評分／OVR／2K／RAPM 對照後問「如何修正？是否可以補正對位者的強度？如何測量補防」→ lead 列三層做法 → 使用者選「A」＝只做第一層（用手上的對位資料）。
- 版本：E-110 的延伸。基準是已上線的 M2（R-066，`reports/game-contribution/m2/`），只影響顯示用的評分，不進 OVR、不動卡片。
- git HEAD（寫本檔時）：b4375b3。角色：實作 role-card；判讀 lead；稽核 role-audit。
- 狀態：**凍結**（2026-10-30，使用者「A」＝照草稿凍結；sha256 在 `preregistration.sha256`）。

## 0. 背景與假設

- M2＝box 11 項＋hustle 5 項＋對位 2 項（PTS_SAVED、TOV_FORCED），對同一半 rapm1 net 加權最小平方。E-110 樣本外 r：A→B 0.526、B→A 0.592。
- lead 對照（2026-10-30，看過，見 §1）發現兩群人仍偏低：
  - 協防護框的長人：Gobert、Brook Lopez、Jaren Jackson、Myles Turner、Embiid，M2 名次比 M0 更低或仍在 100 名後，RAPM 防守卻在前 75（多數前 12）。
  - 守王牌型：Herbert Jones、Dillon Brooks，M2 名次仍在 140 名後，RAPM 淨值在前 50。
- 現有 PTS_SAVED 的三個漏洞（第一層能補的）：
  1. 補防沒算：對位資料只記「誰負責守誰」，補防阻攻記在對位列的 `helpBlocks`，M2 沒用。
  2. 基準含自己：exp(o) 用 o 在同一半**所有**對位的平均，包含 d 自己守 o 的回合；d 守得越好，基準越低，他省下的分數被低估。主要守王牌的人吃虧最多。
  3. 只算得分：d 守的人傳出的助攻（`matchupAssists`）沒算，放人傳球不扣分、逼人交球不加分。
- 假設：
  - H1：把三項一起補上（M3），樣本外對 RAPM 的相關比 M2 高。
  - H2：協防護框名單的評分名次往上。
- lead 事前預期（寫在看結果之前）：
  - helpBlocks 和 box 的 BLK 高度重疊，加進去後 BLK 權重會被分走，淨增益很小。
  - 排除自己的基準對 Herb、Brooks 這種守王牌的人有幫助，對整體 r 影響小。
  - 助攻併進對位可能讓雜訊變大。
  - 整體 Δr 估計 0～+0.02，s1 不過的機率大約六成。
  - 賭抄截型（Coulibaly、Westbrook、Keldon Johnson）第一層不會修好。

## 1. lead 已看過的（揭露）

- E-110 全部結果：`report.md`、`results.json`、`ranking.csv`（M0／M1／M2 權重、r、區間、整季名次）。
- 2026-10-30 lead 對照表（≥ 1000 分鐘 279 人，M2、M0、card 0.2.7 OVR、2K、四季 RAPM 淨值與防守名次）：
  - 防守者 18 人、護框者 20 人、「評分高估／低估」各前 15／10 人的名次（就是 §0 與 §3 半盲名單的來源）。
- 對位資料只看過一場的原始列（0022500001 的前幾筆），知道有 `helpBlocks`、`matchupAssists`、`matchupPotentialAssists`、`shootingFouls`、`switchesOn` 等欄位。
- d2 的 ÷5 比例（中位數 0.928，F-055）。
- **沒看過**：任何人的 helpBlocks、matchupAssists 合計；排除自己後的 exp；任何新特徵和 RAPM 的相關。

## 2. 做法

### 2.1 資料
- 只用已抓好的 `data/matchup-source/2025-26/`（1230 場，含 `matchups` 與 `hustle`）與 E-110 同一套 box、player-games、rapm1 A／B。不抓新資料。
- hustle 的兩分／三分干擾拆分當初沒存，**不在本實驗**（要重抓，屬第二層以後）。

### 2.2 新特徵（全部換算每 36 分鐘，分母＝該球員該場 MIN，同 E-110）
| 代號 | 定義 |
|---|---|
| HELP_BLK | 防守者 d 在所有對位列（`def`＝d）的 `helpBlocks` 合計 |
| PROD_SAVED_LO | `Σ (expP₋d(o) × poss − (pts + V × ast))`，見下 |

- `pts`＝對位列 `playerPoints`，`ast`＝對位列 `matchupAssists`，`poss`＝`partialPossessions`。
- V（一次助攻值幾分）＝同一半全聯盟對位列 `Σ playerPoints ÷ Σ matchupFieldGoalsMade`，由資料算出、不調。
- expP₋d(o)＝o 在同一半、**排除 d 守他的回合**後的 `Σ(pts + V × ast) ÷ Σ poss`；排除後回合數 < 50 用同一半聯盟平均。
- TOV_FORCED 不變（同 E-110）。

### 2.3 組別
| 組 | 特徵 | 數量 |
|---|---|---|
| `M2`（基準） | box 11＋hustle 5＋PTS_SAVED＋TOV_FORCED | 18 |
| `M3`（主判定） | box 11＋hustle 5＋**PROD_SAVED_LO**（取代 PTS_SAVED）＋TOV_FORCED＋**HELP_BLK** | 19 |

- 只報告的拆解（**不拿來選組**）：`M3a`＝M2＋HELP_BLK；`M3b`＝M2 但 PTS_SAVED 改排除自己（不含助攻）；`M3c`＝M2 但 PTS_SAVED 改含助攻（不排除自己）。
- 擬合方式、人群、A／B 切法、權重、不加正則化，全部同 E-110。兩個方向都做。

## 3. 判定

### 硬條件（沒過就停下回報）
| 代號 | 內容 | 門檻 |
|---|---|---|
| c0 | M2 A→B、B→A 重現 E-110：權重與 `reports/E110-defensive-rating/results.json` 的 `weights_AB`／`weights_BA` 相同，r 相同 | 差 < 1e-6 |
| c1 | `npm test` | 全過 |
| d3 | HELP_BLK 合理：整季每人 HELP_BLK ≤ box BLK 的人數比例；全聯盟 Σ HELP_BLK ÷ Σ BLK | ≥ 99% 的人；比值在 (0, 1] |
| d4 | V 在 1.8～2.6 之間；expP₋d 退回聯盟平均的對位回合比例 | V 在範圍內；退回比例 ≤ 10% |

- d3、d4 超出就停，不自行改定義。

### 主判定
- (s1) M3 對 M2：樣本外加權 Pearson 差 Δr。A→B 的 Δr 用球員 bootstrap（2000 次、seed 20261113）求 95% 區間，**下界 > 0**；B→A 的 Δr **點估計 > 0**。兩個都成立才算過。
- 過 → 評分可改用 M3（上線另寫 spec，使用者 approve 後才做）。
- 不過 → 維持 M2，本實驗記為失敗；**不改用 M3a／b／c 任何一個**，也不換特徵重試（L-026）。

### 半盲條件（名單是看過 M2 名次後挑的，見 §1，不能稱盲測）
- (s2) 用 M3 A→B 權重算 2025-26 整季評分，和 M2 比：
  - 護框：Gobert、Brook Lopez、Jaren Jackson Jr.、Myles Turner、Joel Embiid 這 5 人裡，名次往上的 ≥ 4 人。
  - 守王牌：Herbert Jones、Dillon Brooks 兩人都往上。
- 沒過照實記錄，交使用者判斷；不影響 s1。

### 只報告
- M3、M3a／b／c 的權重表與樣本外 r；BLK 權重在加 HELP_BLK 前後的變化。
- V 的值；HELP_BLK 前 15 名。
- 整季評分對 OVR 的 Spearman（M2 0.677）、對四季 RAPM 防守名次的 Spearman。
- 賭抄截名單 Coulibaly、Russell Westbrook、Keldon Johnson、Dru Smith 的名次（預期不會改善）。
- 單場評分 > 10 與 = 0 的比例（M2 5.5%／2.1%）。

## 4. 不准做的事
- 不改評分換算、人群門檻、A／B 切法；不加第五組、不改 V 或 50 回合門檻重跑。
- 不動 `reports/game-contribution/`（含 `m2/`）、`reports/E110-defensive-rating/`、`reports/card-*`、`reports/impact-rapm/`、`data/matchup-source/`；跑前跑後 sha256 唯讀核對。
- 不改名單頁、`enrich_roster_viewer.py`、`daily_inseason_update.py`。
- 本機跑即可（只有迴歸與 bootstrap）；子程序無視窗；子 session 不 commit。

## 5. 回報
- CLAUDE.md 六段；區間、閘門代號放第 6 段之後。
- 輸出到 `reports/E113-help-defense/`：`e113.py`、`report.md`、`results.json`（各組權重、r、區間、V、d3／d4 數字）、`ranking.csv`（≥ 1000 分鐘的人，M2／M3／M3a／M3b／M3c 整季評分與名次、OVR 名次並列）。
- 收工更新 `memory/experiments.md` E-113、`memory/handoff.md` 自己那行；新事實寫 F。
