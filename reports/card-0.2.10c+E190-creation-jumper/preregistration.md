# E-190 預註冊：自主創造改成「自主跳投」，扣掉 10 呎內兩分（切入不再重複）

- 日期：2026-11-01。問題卡 F-132（額度 3，本實驗第 1 個）。使用者 2026-11-01：「切入和傳球、自主不一樣……切入只說他過人到禁區的速度很快、成功率很高，不一定代表運球晃出中距離空檔的能力很強」→ 要預註冊。
- 基準：正式卡 card 0.2.10c（`reports/card-0.2.10c/ranking.csv`，sha e46315bd…158b）；建法＝`reports/card-0.2.10a+E187-rebase/` 臂 KAU。
- 狀態：**已凍結**（2026-11-01，使用者「核可」）；sha256 見 `preregistration.sha256`，之後不改，有錯寫 errata 給使用者核可。

## 0. 已揭露（lead 看過）
- 0.2.10 tail-U.csv（2025-26，MIN≥500，379 人）：r(drive, creation) = 0.875；VIF drive 5.92、creation 5.68；drive 被其他能力值解釋 R² 0.83。
- 0.2.9a 係數（每 10 點，每 36 分）：drive −0.078（SE 0.060）、creation +0.244（SE 0.065）。0.2.10c 的 drive／creation 係數 lead **沒看**。
- 差最大的人：切入≫創造 Jordan Miller 90／73、Watford 94／73、Aaron Holiday 85／68；創造≫切入 Porter Jr. 44／75、Markkanen 46／69、Porziņģis 56／77、Bub Carrington 54／79。
- F-109：K6 歷史原點卡對下季 RAPM，Spearman(drive, 殘差) −0.206 [−0.256, −0.154]（三季都負）。限制 L-091：歷史原點能力值是 2025-26 現值。
- 定義（已讀程式）：drive＝`reports/ovr-v60-drive-split-2025-26/build_drive.py`：非助攻、2 分、距離 ≤10 呎、排除補籃／空中接力／空切／二次進攻／快攻；量 0.5＋效率 0.5。creation＝`calibrate_frozen.attach_creation`：(1 − creationDependence_sourceRole) × FGA／36，**含 10 呎內的自主上籃**——這就是重疊。
- 沒有新的可調數值：10 呎與助攻加權規則照抄 build_drive.py，池與 to_attribute 照抄 attach_creation。

## 1. 改動（只一個臂，不挑）
| 臂 | 內容 |
|---|---|
| KAU | 現行 0.2.10c（c0 先逐位元重現） |
| **KJ** | creation 換成 creationJ，其他全同 KAU；**全部係數重擬合**（R-117 第 4 條：drive 與 creation 係數耦合，一起動） |

creationJ 定義（凍結）：
1. 逐球資料用 build_drive.py 同一套載入與助攻加權：進球被助攻→0、進球沒被助攻→1、失手→該 (subType, descriptor) 類別進球中沒被助攻的比例。
2. 計入：所有三分出手＋距離 **>10 呎**的兩分出手。10 呎內兩分（含補籃、空中接力）一律不計。
3. 每 36 分鐘＝加權出手數 ×36／分鐘；季窗口與近季權重照目前 tail-U.csv creation 欄的窗口（R-118 四季滑動）；池與百分位轉換照 attach_creation（GP≥30、MPG≥20、`to_attribute`）。
4. 揭露：10 呎內的自主補籃從 creation 移出、不加到別欄（rebound／short 已部分涵蓋），不另開臂。

## 2. 判定（R-117：主目標修到＋沒弄壞，其餘只報告）
人群：2025-26 MIN≥500（同 §0 的 379 人口徑）；bootstrap 球員層 2000 次，seed 20261101。

硬條件：
- **a1（分開了）**：r(drive, creationJ) ≤ **0.70**，且 VIF(drive) ≤ **3.0**（13 項 tail 屬性＋help、heightInches 同 KAU 擬合用的欄）。
- **a2（重疊造成的偏差變小）**：三歷史原點（2022-23～2024-25）合併，Spearman(drive, 卡片對下季 RAPM 殘差) KJ − KAU ≥ **+0.05**（MDE：F-109 該值 90% 區間半寬 ≈ 0.05）。殘差算法同 F-109（`reports/E173-pressure-vs-rapm/`）。
- **b（沒弄壞）**：(0) c0：KAU 逐位元重現 0.2.10c，且用新程式重算「舊定義 creation」與 tail-U.csv creation 欄差 <1e-6；(1) `npm test` 過；(2) 綜合分 C 三季合併 KJ − KAU ≥ −0.089（−2h_C，h_C＝0.045 照 E-186 phase0）；(3) 下季 RAPM 名次 ρ 三季合併 KJ − KAU ≥ −2h_R，h_R＝KAU 該 ρ 的 bootstrap 90% 半寬（phase0 先算、寫檔後才跑 KJ）。

只報告：
- drive、creationJ 每 10 點的 OVR 係數與 bootstrap SE（回答「切入在 OVR 值多少」；**不設方向門檻**）。
- 薪水、2K、前 100 名移動 ≥10 名人數、F-118 傳球偏差、JW 名次與前 25 名分段殘差（F-125 護欄）。
- 球員表（KAU→KJ 名次、OVR、drive、creation→creationJ）：Jordan Miller、Trendon Watford、Aaron Holiday、Michael Porter Jr.、Lauri Markkanen、Kristaps Porziņģis、Stephen Curry、Shai Gilgeous-Alexander、Giannis Antetokounmpo、Ja Morant、Zion Williamson、Jalen Williams、LeBron James、Nikola Jokić、Anthony Edwards。

結論：a1、a2、b 全過＝修到，採用候選交使用者 G5；a1 過、a2 不過＝定義分開了但偏差沒變小（額度剩 2）；b 不過＝弄壞。真樣本外：2026-27 季末本季 RAPM 複查 a2。

## 3. 限制
- 只寫 `reports/card-0.2.10c+E190-creation-jumper/`；其他目錄唯讀。不改 `src/`、`scripts/`、網站、memory、`reports/card-0.2.10c/`。
- 另一個 session 在做 card 0.2.10d／0.2.10e（handoff），不碰那些目錄與 status_snapshot.py、build_card_viewer.py、live/。
- 外部數據只放彙總。
- 採用後才另做：網站 CRT 說明（`season_nav.ATTR_TIPS`）、新賽季頁接線。

## 4. 回報
照 CLAUDE.md 六段（# 總評、這次目標、進步、退步、直觀證據、要你決定的事），先講 a1／a2 用白話（例如「切入和自主創造的重疊從 0.88 降到 X」「切入型球員被高估少了幾成」）＋球員表；Δρ、區間、關卡代號放 `report.md`。
