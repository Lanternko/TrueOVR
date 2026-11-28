# E-206 預註冊：TO 失誤率分母改成觸球次數

- 日期：2026-11-02。問題卡 F-143 第 3 個（最後一個）額度。起因 F-144：0.2.12 用「每持球分鐘失誤」，每次觸球拿很久的人失誤率被灌好看（Reaves 每觸球秒數全聯盟第 2）。使用者 2026-11-02「開觸球數實驗」（R-143）。
- 基準 K12：線上 card 0.2.12（`reports/card-0.2.12-tov/ranking.csv`，sha256 29ca32eb…）；建法＝E-202 KT 臂（`reports/card-0.2.10j+E202-to-possession/`），E-205 已把它做成可參數化（`reports/card-0.2.12+E205-to-weight/`）。
- 狀態：**已凍結**（2026-11-02）；sha256 見 `preregistration.sha256`（以 git HEAD 版 LF 計），之後不改，有錯寫 errata 給使用者核可。

## 0. 已揭露（lead 看過）
- F-144（2025-26 單季，持球/36≥5 的 64 人）：每持球分鐘失誤 → 每次觸球失誤名次：Reaves 24→45、KPJ 19→30、Brunson 3→12、Maxey 6→8、SGA 7→24、Luka 48→55、Harden 38→57、Cade 40→49、LaMelo 31→36。每觸球秒數：SGA 1、Reaves 2、Brunson 3、Harden 4、KPJ 5。
- E-205（持球權重 0.25）：VIF 5.37→4.10，Reaves 12→12、KPJ 17→17 不動。
- lead 沒看過觸球分母下的 tovSkill、係數、OVR 或名次。

## 1. 改動（只一個主臂）
| 臂 | 內容 |
|---|---|
| K12 | 線上 card 0.2.12（c0 先逐位元重現） |
| **KC** | 只把 r 的分母從持球分鐘換成**觸球次數**，其他全同 K12；**全部係數重擬合**（R-115，不設下限） |

KC 定義（凍結）：
1. 觸球次數：同一來源檔（`reports/handle-E069/raw/<季>/Possessions-FULL.json`）的 `TOUCHES`。窗口化同 K12 的持球分鐘：有效觸球＝Σ_季 TOUCHES_季 ×（該人該季窗口權重分鐘 ÷ 該季分鐘）。
2. r＝窗口失誤 ÷ 有效觸球。先驗、歷史目標、收縮同 E-069 方法 c 的式子與 λ＝0.2；虛擬量 k、kh 從「持球分鐘」換算成「觸球」：k_t＝64·ρ、kh_t＝256·ρ，ρ＝卡片池 2025-26 Σ TOUCHES ÷ Σ TIME_OF_POSS（資料決定、不調）。先驗 m＝同位置 2025-26 全季 TOV ÷ TOUCHES。
3. v（用球量）**不變**＝窗口持球分鐘 ÷ 窗口出賽分鐘 × 36。
4. raw＝0.5·z(−r)＋0.5·z(v)（權重同 K12，不調）；z 的池、0–99 轉換、topMissing（沒有 tracking 列：r＝先驗、v＝池第 10 百分位）全同 K12。
5. 其他 16 項、gravity、用人層、3PT 欄、H1 封頂、OVR 映射照 K12。

## 2. 判定
人群同 E-202（2025-26 MIN≥500）；bootstrap 球員層 2000 次，seed 20261102。phase0（只用 K12）先寫檔、commit，之後才跑 KC。

硬條件：
- **A（機制：不再偏袒拿球久的人）**：持球者子群（2025-26 MIN≥1000 且持球/36≥5，handle 原始檔單季）中，tovSkill 與 `AVG_SEC_PER_TOUCH` 的 Spearman，K12 − KC ≥ MDE_A（phase0 用 K12 bootstrap 該 ρ 的 90% 半寬）。
- **保住 E-202**：tovSkill 對 2K27 Ball Handle Spearman KC − 0.0798 ≥ 0.0879。
- **沒弄壞**：c0 逐位元重現 K12；`npm test` 過；全體 OVR 對 2025-26 RAPM Spearman KC − K12 ≥ −2h（h＝phase0 K12 的 90% 半寬）。

B（不擋採用）：F-143 TO 前 30 名中持球/36 低於池中位數的人數 ≤ 10。

只報告：
- tovSkill VIF 與對 creation、pass、gravity 相關；每 10 點 OVR 係數與 SE。
- 全體 OVR 對 2K27 OVR、EPM、薪水 ρ（0.2.11、K12、KC 三欄）；RAPM 分半兩半方向。
- 前 100 名移動 ≥10 名人數（KC 對 K12）、前 20 名進出；ρ 換算值。
- 球員表（0.2.11→K12→KC 的 TO、TO 名次、OVR、OVR 名次）：Austin Reaves、Kevin Porter Jr.、SGA、Brunson、Luka、Jokić、Cade、Harden、LaMelo Ball、Tyrese Maxey、Ty Jerome、Trae Young（若有）、Sam Hauser、Tim Hardaway Jr.、Luke Kornet、Jarrett Allen、Rudy Gobert。預期 Reaves、KPJ、SGA、Harden 的 TO 下降，Maxey、Brunson 留前段；只報告、不當門檻。

## 3. 限制
- 只寫 `reports/card-0.2.12+E206-to-touches/`；其他目錄唯讀。不改 `src/`、`scripts/`、網站、live/。
- 採用後才另做上線（每日抓取多存 TOUCHES、凍結池重算、網站說明改字、版號）。
- F-143 額度用完：本實驗不過就停在 0.2.12，不再在本卡提新假設，除非使用者重開額度（R-117）。

## 4. 回報
CLAUDE.md 六段；白話講 Reaves、KPJ 回到哪、TO 榜換成誰；Δρ、區間只寫 `report.md`。
