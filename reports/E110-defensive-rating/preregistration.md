# E-110 預註冊：單場評分加入防守對位與 hustle 資料

- 日期：2026-10-30。來源：使用者 2026-10-30 問「只看 box score 准吗？」→ lead 查出評分漏掉防守（Herbert Jones OVR 第 13 名、評分第 183 名）→ 使用者問「第三项做得到吗？防守对位的资料查得到吗？」→ lead 實測兩個端點都抓得到 → 使用者選「A」＝先寫預註冊。
- 版本：E-105 的延伸，只影響顯示用的評分（R-062），不進 OVR、不動卡片。
- git HEAD（寫本檔時）：6281caf。角色：實作 role-card；判讀 lead；稽核 role-audit。
- 狀態：**凍結**（2026-10-30，使用者「A」＝照草稿凍結；sha256 在 `preregistration.sha256`）。

## 0. 背景與假設

- 現在的評分（E-105）＝ 11 項 box score 每 36 分鐘 × 權重，權重對 2025-26 A 半 RAPM（rapm1-A net）做加權最小平方，B 半樣本外加權 r 0.444。A 半 RAPM 自己預測 B 半是 0.462，等於是上限附近。
- 漏掉防守：2025-26 上場 ≥ 1000 分鐘 279 人，整季評分對卡片 OVR 的 Spearman 0.55；防守型球員評分名次比 OVR 名次低很多（Herbert Jones 13 → 183、Camara 31 → 218、Brooks 41 → 236、Draymond 76 → 264、Zubac 91 → 257）。
- NBA 有兩個單場資料：
  - `boxscorematchupsv3`：每組「進攻者 × 防守者」的部分回合數、被守時得分、投籃、三分、失誤、罰球、投籃犯規、協防阻攻。
  - `boxscorehustlev2`：干擾出手、撥球（deflection）、製造進攻犯規、搶到地板球、卡位、掩護助攻。
- 假設：
  - H1：box ＋ hustle ＋ 對位一起擬合，樣本外對 RAPM 的相關比只用 box 高。
  - H2：防守型球員的整季評分名次會往上，接近他們的 OVR 名次。
- lead 事前預期（寫在看結果之前）：hustle（撥球、干擾出手）比對位得分穩定，大部分進步會來自 hustle；對位「少讓幾分」雜訊很大，權重可能很小甚至反號。整體 r 可能只多 0.01–0.04，s1 有相當機會不過。

## 1. lead 已看過的（揭露）

- E-105 全部結果（權重、A／B 半相關、`report.md`）。
- 2026-10-30 本機重算：整季評分對 OVR 的 Spearman 0.548、對淨影響 0.52；名次差最大的 12 人（上面 5 個防守者，以及 Dru Smith、Reed Sheppard、Bones Hyland、Keyonte George、Fontecchio、Filipowski 評分比 OVR 高很多）；OVR 前十名的評分名次；單場對其餘場次 r 0.213、5 場 r 0.428。
- 只看過**一場**的原始對位與 hustle 資料：2026-10-20 OKC @ SAS（GAME_ID 0022600003），SGA 和 Wembanyama 的前幾筆對位、SGA 的 hustle（干擾 8、撥球 2）。
- **沒看過**任何 2025-26 的對位或 hustle 數字，也沒算過它們和 RAPM 的任何相關。

## 2. 做法

### 2.1 抓資料（一次性）
- 2025-26 例行賽全部 1230 場（GAME_ID 取自 `data/season-source/player-games.json`），兩個端點各一次。
- 每次請求間隔 ≥ 1.2 秒，可中斷續抓（已抓的場次跳過）；失敗重試 3 次，仍失敗記在 `fetch-failures.json`。
- 只存需要的欄位，存到 `data/matchup-source/2025-26/`（`/data/` 本來就不進 git）；原始回應不留。
- 本機跑即可（網路等待為主，不是運算）；用 node，子程序無視窗。

### 2.2 特徵（全部換算每 36 分鐘，分母＝該球員該場 MIN）
| 組 | 特徵 |
|---|---|
| box（11） | 同 E-105：PTS、FGA、FTA、FG3M、OREB、DREB、AST、STL、BLK、TOV、PF |
| hustle（5） | DEFL（deflections）、CONTEST（contestedShots）、CHARGE（chargesDrawn）、LOOSE（looseBallsRecoveredTotal）、SCREEN_AST（screenAssists） |
| 對位（2） | PTS_SAVED、TOV_FORCED（定義如下） |

- PTS_SAVED：對防守者 d 的每筆對位（進攻者 o、部分回合 poss、o 得分 pts），`Σ (exp(o) × poss − pts)`。exp(o)＝o 在**同一半**所有對位裡的「得分 ÷ 部分回合」；同一半回合數 < 50 的進攻者用聯盟平均。
- TOV_FORCED：d 被對位的 matchupTurnovers 合計。
- 單場評分（第二階段才上線）的 exp(o) 用 o 的 2025-26 整季值，沒有就用聯盟平均；這不影響本實驗的判定。

### 2.3 組別
| 組 | 特徵數 |
|---|---|
| `M0`（基準） | box 11 |
| `M1` | box ＋ hustle ＝ 16 |
| `M2` | box ＋ hustle ＋ 對位 ＝ 18 |

- 擬合方式同 E-105：每人半季合計換算每 36 分鐘，對同一半 rapm1 net 做加權最小平方（權重＝該半 poss），人群＝該半上場 ≥ 300 分鐘。不加正則化、不限權重正負號，沒有可調參數。
- 兩個方向都做：A→B（A 半擬合、B 半檢驗，同 E-105）與 B→A。

## 3. 判定

### 硬條件（沒過就停下回報）
| 代號 | 內容 | 門檻 |
|---|---|---|
| c0 | M0 A→B 重現 E-105：權重與 `reports/game-contribution/weights.json` 相同、B 半加權 r 0.444 | 差 < 1e-6 |
| c1 | `npm test` | 全過 |
| d0 | 資料完整：兩端點都抓到的場次 | ≥ 1210／1230（98%） |
| d1 | 對位與 hustle 裡的球員都對得上 player-games 同場名單 | ≥ 99% 筆數 |
| d2 | 每隊每場：對位部分回合合計 ÷ 該隊該場回合數（team-games 推算） | 中位數在 0.85–1.15；超出就停，不自行改定義 |

### 主判定
- (s1) M2 對 M0：樣本外加權 Pearson 差 Δr。A→B 的 Δr 用球員 bootstrap（2000 次、seed 20261110）求 95% 區間，**下界 > 0**；B→A 的 Δr **點估計 > 0**。兩個都成立才算過。
- (s1') M1 對 M0 同樣算一次。
- 選哪組上線：
  - M2 過 s1 → 用 M2；但若 M1 也過、且 M2 的 A→B r 沒有比 M1 高 ≥ 0.01，就用比較簡單的 M1。
  - 只有 M1 過 → 用 M1。
  - 都沒過 → 維持 M0，本實驗記為失敗，不再換特徵重試（L-026）。

### 半盲條件（名單是看過結果後挑的，見 §1，不能稱盲測）
- (s2) 用選中那組的 A→B 權重算 2025-26 整季評分；Herbert Jones、Camara、Brooks、Draymond、Zubac 這 5 人裡，評分名次往上的 ≥ 4 人。沒過照實記錄，交使用者判斷。

### 只報告
- 各組權重表（正負號、每 36 多 1 個值多少）。
- 單場評分對其餘場次的 r、5 場對其餘場次的 r（M0 是 0.213／0.428，同樣人群：場均 ≥ 20 分鐘、≥ 10 分鐘的場次、出賽 ≥ 40 場）。
- 整季評分對 OVR 的 Spearman（M0 0.548）、OVR 前十名的評分名次、名次差最大 12 人（§1 那份名單）各組的名次。
- 單場評分超過 10 與等於 0 的比例（維持 0.75×(v＋7.5) 不變；M0 約 4%／1%）。

## 4. 不准做的事
- 不改評分換算（0.75、7.5、0 起跳）、不改 E-105 的人群門檻（300 分鐘）與 A／B 切法；不加第四組、不換特徵定義重跑。
- 不動 `reports/game-contribution/`、`reports/card-*`、`reports/impact-rapm/`；跑前跑後 sha256 唯讀核對。
- 不改名單頁、不改 `daily_inseason_update.py`（那是第二階段）。
- 子 session 不 commit。

## 5. 第二階段（本實驗過了、使用者 approve 後才做，另寫 spec）
- 每日發布順便抓當天每場的兩個端點（每場 2 次請求，約多 20–30 秒）；抓不到的場次退回 M0 並在 tooltip 註明。
- 名單頁評分改用選中那組權重；2025-26 基準重算。
- 預估：資料一季約十幾 MB，不用 5090。

## 6. 回報
- CLAUDE.md 六段；區間、閘門代號放第 6 段之後。
- 輸出到 `reports/E110-defensive-rating/`：`report.md`、`results.json`（各組權重、r、區間）、`ranking.csv`（2025-26 ≥ 1000 分鐘的人，M0／M1／M2 整季評分與名次、OVR 名次並列）。
- 收工更新 `memory/experiments.md` E-110、`memory/handoff.md` 自己那行；新事實寫 F。
