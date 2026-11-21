# E-111 預註冊：新賽季 OVR 跟上 card 0.2.7（E-107 新賽季版的 errata 重凍結）

狀態：已凍結（2026-10-30，使用者「1 然後體力不太重要 即將從網站拔掉 只留做內部資料 / 0.2.7也順便合併 / Go」）。凍結後不改；sha256 存在 `preregistration.sha256`。

## 0. 這份是什麼

- 繼承 `reports/ovr-inseason-2026-27/e107-card026/preregistration.md`（凍結 sha256 cb5b293d…f173，下稱「E-107 預註冊」）全文，只改本檔列出的地方。沒寫到的照 E-107 預註冊。
- 換號原因：E-107 和另一個 session 的「E-107 防守 UL」撞號；E-107 新賽季版停在前置關卡（(z)(L1)(s) 不過，回測 (1)(2) 沒看過），本條是它的 errata 重做。
- 基準卡從 card 0.2.6 改成 **card 0.2.7**（R-065：0.2.6 + E-107 防守 UL），使用者要求一起合併。
- lead 已看過、因此不算盲測的東西：E-107 新賽季版的前置結果（`e107-card026/prereq.json`、`deviations.json`、`live-compare.json`：026 線上對 0.2.5a 的名次變動，含 stamina 錯誤）；card 0.2.7 的 summary（前 20 名換 Embiid、Knueppel 出，Queta、Rollins 入）。**沒看過任何回測 (1)(2) 的數字**，下面三個修正只針對前置關卡的機械原因，不碰回測。

## 1. 對 E-107 預註冊 §2 的修改

全部在新開關 `CARD_MODE='027'`（取代未上線的 026 分支，可沿用其程式；026 分支可刪或保留，預設仍是 025）。

1. **先驗 x0 來源（修 L1）**：x0 用**未四捨五入**的值。
   - 進攻與一般屬性：`reports/card-0.2.5+E101-crossera/` 裡 E-101 P1 primary 的未四捨五入屬性檔（E-107 子 session 找到的 `attributes-e101.csv`）。stamina、help、heightInches 等 E-101 沒有的欄，照 card 0.2.5 的來源補（E-107 子 session 的作法）。
   - card 0.2.7 的屬性欄與 0.2.6 相同（`reports/card-0.2.7/summary.json` 的 `columnsDifferentFromCard026` 只有 rank、ovr、predictedPer36、defenseBonus、gRepl、ovr36），要先核對這點，不同就停下回報。
   - 核對 `reports/card-0.2.7/ranking.csv` sha256 = `reports/card-0.2.7/summary.json` 的 `ranking_csv_sha256`（aebcadf1…c6b6），不寫死其他字串。
   - 產出 `live/build_prior_027.py`、`live/prior-2025-26-card027.json`。
2. **OVR 層改跟 card 0.2.7**：屬性迴歸、用人層係數、r_repl、錨點、防守加成都照產生 card 0.2.7 的流程（`reports/card-0.2.6+E107-defense-UL/` 的 UL6：`cards/UL6/primary` 與 `phase2.json`，錨點 PR1 −0.8313、PR50 1.2521、PR99 4.1201）。
   - 防守加成用 UL 公式（不封頂 max(0, centeredD)）。onBall、help 是凍結屬性，防守 D 在賽中也凍結在 card 0.2.7 的值（不做逐場更新），所以 N=0 與賽中的防守加成都應等於 0.2.7 的未四捨五入值。新賽季 PBP 要逐場更新 D 是之後另一個實驗。
   - 用人層檔：`live/build_usage_027.py` → `live/usage-2025-26-card027.json`。
3. **stamina 不換尺（修 s）**：stamina 不進四季合併池、不加尾巴，賽中映射照 025 模式的單季作法（card 0.2.6／0.2.7 的 stamina 本來就沒換尺）。使用者裁定體力不重要、即將從網站拿掉、只留內部資料。
4. **分區（修 z）**：有 `area` 欄的季（參考池 2022-23～2025-26），`area` 缺值的出手照 E-101 跳過（不算 mid 也不算 short）；`area == 'Mid-Range'` 且 `shotDistance < 8` 判 short。沒有 `area` 欄的季（2026-27）照座標規則。
5. **foulDraw 池（E-107 偏差 D5）**：合併池的 foulDraw 合成值用各季自己的 z（同 E-101 卡片端），不用 2025-26 凍結的 z。賽中視窗仍用 2025-26 凍結的 z（同現行）。
6. **版號**：027 時 `VERSION = 'inseason 0.2.7'`、`CARD_VERSION = 'card 0.2.7'`、`FORMAL_RANKING = reports/card-0.2.7/ranking.csv`；第一個字面值採用時才改（同 E-107 §2.5）。
7. **回測**：`e111-card027/backtest_e111.py`，規則同 E-107 §2.6，「026」一律讀成「027」。回測的答案卡與先驗卡的防守加成用 UL 公式，輸入照該季資料（同 card 0.2.7 的建卡流程）。

## 2. 對 E-107 預註冊 §4 判定表的修改

- (c0)：不變（025 對已發佈快照逐位元相同）。
- (u)：不變。
- (z)：條件不變，對照 E-101 的修正後分區，0 人不符。
- (L1)：改成「N=0 重現 **card 0.2.7**」：ref 轉換 OVR 對 card 0.2.7 ranking 的 ovr，卡內每人 |差| ≤ 0.1；錨點、r_repl 與 UL6 的值差 0（容許浮點 1e-9）。
- (s)：會更新的屬性改為 long、mid、short、ft、foulDraw、tovSkill、pass、rebound、creation（**stamina 不列入判定**，只報告它的中位差）；x0 改為 card 0.2.7 的未四捨五入值；定義細節採 E-107 偏差 D10 的作法（252 人池、各模式依自己 x0 取前 5%）。
- (1)：RG1-027 對 027 答案卡，過 v5 §2 的 V1∧V2，基準 RA-027，門檻不改。
- (2)：8 格每格 MAE(RG1-027) − MAE(RG1-sat15) ≤ +0.05，基準仍是 E-095 的 `predictions-sat15.csv`。
- 採用規則同 E-107 §4，版號換成 inseason 0.2.7。

## 3. 只報告（不影響判定）

- 同 E-107 §5，另加：027 線上對 0.2.5a 的名次變動（前 20 名進出、|ΔOVR| 中位與最大）；Embiid、Knueppel、Queta、Rollins、Wembanyama、Giannis、Dončić、Curry 的名次。
- E-107 偏差 D8（ft 合併池 r99 和 E-101 卡片端不同）照 E-107 §2.3 的設計保留，只報告。

## 4. 不准

- 同 E-107 §7。另外：不在看過 (1)(2) 後改映射、池或門檻；前置不過就停下回報，不自行再修。
