# E-069 預註冊：handle（控球）量測與模擬失誤拆分

- 日期：2026-10-29（使用者「GO」；定義依 R-032）
- 角色：第一階段 role-card（卡片端量 handle、passSec），第二階段 role-model（模擬端失誤拆分與 handle 用法）；lead 判讀，role-audit 重算。
- 版本：候選標籤 `card 0.2.0+E069`／`src+E069`。版本號在使用者看完結果後再定（R-018、R-019）。

## 1. 問題（lead 已看過的東西，已揭露）

- 模擬程式用 `p.handle ?? 70`，卡片沒有 handle 欄。lead 用 `ovrInput('both')` 確認 582 人全是 70，五個位置平均 profile 也是 70。
- 模擬裡 handle 用在四個地方：
  - 持球綜合 `HANDLING_W`（handle 0.40）；
  - 包夾脫困 `DOUBLE_CREATE_W`（handle 0.50）；
  - 自主創造 `create`（`probability_model.js:86`）；
  - 自主出手品質（`:299` `HANDLE_IMPACT`）。
- 失誤：每次觸球用 `interpolate(tovSkill, CURVE_TOV)`。tovSkill＝TOV/(FGA+.44FTA+AST+TOV)，是所有失誤的總和。
- Hauser 的 tovSkill 是 99。v41 驗證：模擬 TOV/36 0.89，實際 0.65。
- v41 的失誤誤差和 creationDependence 的 ρ＝0.25：自己創造出手的人被低估約 −0.14，中間組被高估約 +0.25。
- tracking Possessions（2025-26 整季）看過四人：
  - Luka：持球時間 518、每次觸球運球 4.1；
  - White：468／3.7；
  - Gobert：111／0.22；
  - Hauser：86／0.55。
- 任何候選版的回測或模擬數字都還沒看過。

## 2. 定義（R-032，寫死）

### 2.1 控球失誤 ctlTov（歸 handle）

PBP `actionType == 'turnover'`，subType（不分大小寫，去空白後比對）屬於下列之一：
- lost ball；
- traveling；
- double dribble；
- discontinued dribble；
- out of bounds lost ball；
- step out of bounds；
- backcourt；
- palming；
- offensive foul／offensive charge（只算 charge；illegal screen 不算）。

**不算**：bad pass、out of bounds bad pass（這兩項歸 passTov）；3 second、shot clock、5 second、8 second、kicked ball、lane violation、illegal screen、其他。

實作時要先列出各季 subType 的全部取值與次數，放在報告附錄：
- 上表沒列到、但次數占全部失誤 ≥ 1% 的取值，停下回報 lead，不自行歸類；
- 低於 1% 的取值一律歸「其他」。

### 2.2 傳球失誤 passTov（歸 PASS 類，新屬性 passSec）

- 分子：bad pass＋out of bounds bad pass。
- 分母：tracking Passing 的 `PASSES_MADE`＋passTov。

### 2.3 handle

- **穩定度率**：r_sec＝ctlTov ÷ 持球分鐘（tracking Possessions 的 `TIME_OF_POSS`，單位分鐘）。越低越好。
- **持球量**：vol＝TIME_OF_POSS ÷ MIN × 36。
- **收縮**：r_sec 用 E-055 的 b、c 兩種方法往同位置平均收縮（分母單位＝持球分鐘），k、λ、kh 在擬合季擬合。
  - 擬合季：2020-21..2024-25；測試季：2025-26。
  - 選法：只用擬合季 MAE 從 a、b、c 選一個（同 E-066 §2，不看測試季）。
- **合成**：handle_raw＝0.5·z(−r_sec 收縮後)＋0.5·z(vol)。
  - z 用卡片池（GP≥30 且 MPG≥20）的平均與標準差；
  - 再用 build_attrs 的同一套百分位對應函式，換到屬性尺度，和 tovSkill 同法。
  - 權重 0.5／0.5 是使用者裁定的定義（R-032），不回測、不調。
- **passSec**：passTov 率依同一套 a/b/c 流程收縮，取負號後轉成百分位屬性。

## 3. 第一階段：卡片端（role-card）

### 3.1 資料

- PBP：2020-21..2024-25 讀 `data/defense-seventh/<季>/pbp`，2025-26 讀 `data/defense-a-source`（同 `extract_pbp.py`）。
- tracking：照 `reports/player-impact-v21/fetch-tracking.mjs` 的參數抓 Possessions、Passing。
  - 每季抓「上半季」「下半季」兩段（DateFrom／DateTo），上半季＝依日期前 574/1230 場的日期範圍（同 E-055，邊界日期寫進報告）；
  - 另外抓整季一份。
  - 原始檔與 sha256 存 `reports/handle-E069/raw/`。
  - 抓不到時停下回報，不改用別的季或別的分母。

### 3.2 判定

| # | 條件 | 門檻 |
|---|---|---|
| (h1) | 穩定度可預測 | 測試季：r_sec（選定方法）預測下半季的 MAE，相對方法 a（不收縮）差的 90% 區間上界 < 0。球員配對 bootstrap 2000、seed 1，人群＝下半季持球分鐘 ≥ 20 |
| (h2) | passSec 可預測 | 同 (h1)，人群＝下半季傳球數 ≥ 150 |
| (h3) | 不動現有屬性 | card 0.2.0 其他屬性逐位元不變（新欄位另外加） |

只報告：
- handle、passSec 對 2K27 `Ball Handle`、`Pass Accuracy` 的 ρ；
- G5 名單的 handle、passSec、vol、r_sec 與名次：Luka、SGA、Brunson、Haliburton、Jokić、White、Hauser、Gobert、Caruso、Westbrook、Pritchard、McCain；
- 前 20 名與後 20 名（卡片池內）。

(h1) 不過時，穩定度改用方法 a 的原始率；(h2) 同理。這時記為「收縮未證實」，仍進入第二階段。屬性定義是裁定，不因 h 閘門不過而改。

## 4. 第二階段：模擬端（role-model，第一階段 lead 核對後才開工）

### 4.1 改動（開關 `E069`，預設關）

- **失誤拆兩段**：
  - 控球失誤 hazard 由 handle 決定，並乘上該次觸球的持球秒數；
  - 傳球失誤 hazard 由 passSec 決定，只在傳球動作發生；
  - tovSkill 不再進失誤公式。
- **其他三處**：
  - 自主創造 `create` 和自主出手品質 `HANDLE_IMPACT` 改用 creation（卡片 CRT）；
  - 包夾脫困改用 0.5·handle＋0.5·pass；
  - `HANDLING_W` 的 handle 權重不變，值改成新的 handle。
- **校準**：只准調兩個全聯盟純量，讓 2025-26 模擬的全聯盟控球失誤總數、傳球失誤總數各自對上實際（±2%）。不准逐人、逐位置調參。

### 4.2 判定

| # | 條件 | 門檻 |
|---|---|---|
| (m0) | 開關關閉時重現現行 | 同 seed 下，現行驗證輸出逐位元相同 |
| (m1) | G1 | `npm test` 過 |
| (m2) | 個人失誤更準 | 2025-26 v41 驗證人群的 tov36 MAE（開關開）相對現行的差，球員 bootstrap 90% 上界 < 0；全聯盟 TOV 總數誤差 ≤ 2% |
| (m3) | 長人偏袒 | E-067 §3 的 (b1)(b2)(b3)：WinImp 主版與位置版在 5090 用 E-065 同 seed 重跑，跟 E-067 基準線比 |

只報告：
- tov36 誤差依 creationDependence 三分組的平均；
- WinImp 兩版的 ρ；
- G5 名單的 WinImp 與名次；
- 2K27 ρ。

採用規則：
- (m0)–(m3) 全過：記為「通過」，交使用者做 G5 並定版本。
- (m2) 過、(m3) 沒過：記為「失誤改善，偏袒未修」，交使用者裁定，不自動採用（L-035）。
- 其餘情況：記錄結果，模擬不變。

## 5. 不准

- 看過任何數字後，改 subType 歸類、門檻、權重 0.5／0.5、季別、人群、seed 或校準方式（L-026）。
- 逐人或逐位置的校準。
- 動現行輸出：`reports/card-0.2.0/`、`reports/ovr-v61-shrink-history-2025-26/`、E-064／E-065／E-067 的目錄都唯讀。新輸出寫到 `reports/handle-E069/`。
- 動賽中名單、`live/`、gh-pages、每日排程；部署；commit。
- 第二階段的引擎改動一律放在開關後面，預設關閉。
