# E-198 預註冊：加「無球引力」能力值進卡片 OVR

- 日期：2026-11-02。問題卡 F-140（無球射手被卡片低估）。使用者 2026-11-02：「取而代之的可以是無球跑動或引力，預期 klay curry 要上升」→ 看完「只顯示／放進 OVR」兩案後選「放」（R-134）。
- 基準：正式卡 card 0.2.10i（`reports/card-0.2.10i/ranking.csv`）；建法＝`reports/card-0.2.10i/` 的 KAU 臂（drive_D、creationJ）。
- 狀態：**已凍結**（2026-11-02，使用者「不設下限」）；sha256 見 `preregistration.sha256`（以 git HEAD 版 LF 計），之後不改，有錯寫 errata 給使用者核可。

## 0. 已揭露（lead 看過）
- NBA.com Gravity（`stats.nba.com/stats/gravityleaders`）只有 2025-26（234 人）與 2026-27（288 人，進行中）；2022-23～2024-25 回 500、沒有資料。2025-26 沒有 Curry（API 收錄門檻未公開）。
- 平均引力名次：2025-26 前段 Durant、Edwards、SGA、Dončić、Leonard、Klay；2026-27 第 1 是 Curry，Klay 也在前 8。無球外線引力前段同樣是持球明星（SGA、Durant、Dončić）。
- F-139（card 0.2.10g，樣本內）：引力強度和卡片低估量 ρ −0.21（引力高的人卡片本來就給多）；接球射手組內 ≈0；只有「無球外線幀數佔比」射手組內 +0.46（5 特徵中挑出、未校正）。
- E-181：加「被助攻得分」屬性係數 +0.039（SE 0.033），缺口沒縮小。E-196：得分產量自由擬合係數只有下限的四到五成。
- lead 沒看過加入引力後的係數、卡片或名次。

## 1. 改動（只一個主臂）
| 臂 | 內容 |
|---|---|
| KAU | 現行 0.2.10i（c0 先逐位元重現 ranking.csv） |
| **KG** | 新增能力值 `gravity`，其他全同 KAU；**全部係數重擬合**（R-115 耦合參數一起動） |

`gravity` 定義（凍結）：
1. 原始值＝`AVGOFFBALLPERIMETERGRAVITYSCORE`（無球、外線的平均引力），2025-26 整季。
2. 缺值（不在 API 名單的人，例如 Curry）：在有值的人上做 OLS，原始值 ~ 3PA/36 ＋ 3P% ＋ USG% ＋ 位置啞變數，拿預測值補；同時記 `gravityImputed=1`。
3. 轉成 0–99：池與百分位轉換照 creation（GP≥30、MPG≥20、`to_attribute`）。
4. 位置交互作用、align、H1 封頂、OVR 映射照 KAU。
5. 係數下限：**不設**，自由擬合（使用者 2026-11-02「不設下限」）；學不到就在 F-140 記「已知限制」。

## 2. 判定（R-117／R-131）
人群：2025-26 MIN≥500（約 379 人）；bootstrap 球員層 2000 次，seed 20261102。接球射手組＝long≥75 且 creation≤60（KAU 上定義，F-139 口徑）。

樣本外：引力沒有歷史季，不能用「各季卡對下季 RAPM」。改用 **2025-26 本季 RAPM**（卡片擬合目標是 DARKO＋BPM 的 T6，沒用到 RAPM）；另報 RAPM 分半（單雙場）兩半各算一次，看方向是否一致。限制：同季、DARKO 本身帶有 RAPM 資訊，算「半樣本外」；真樣本外留給 2026-27 季末本季 RAPM。

硬條件（只有兩類）：
- **A（機制）**：接球射手組對本季 RAPM 的平均名次殘差（百分位點，RAPM 名次 − 卡片名次）KG 比 KAU 縮小，縮小量 ≥ MDE（phase0 用 KAU 的 bootstrap 90% 半寬算，寫檔後才跑 KG）。殘差同時報 L-112 的價值殘差（標準化 RAPM 對標準化 OVR 回歸），名次殘差有均值回歸假象時以價值殘差為準。
- **沒弄壞**：c0 逐位元重現；`npm test` 過；全體對本季 RAPM Spearman KG − KAU ≥ −2h（h＝KAU 的 bootstrap 90% 半寬，phase0 先算）。

只報告（預期方向＋雜訊帶）：
- `gravity` 每 10 點 OVR 係數與 bootstrap SE；VIF（預期與 long、creation 相關）。
- 薪水、EPM、2K27、前 100 名移動 ≥10 名人數、前 20 名進出。
- 補值的人（`gravityImputed=1`）名次變化另列。
- 球員表（KAU→KG 名次、OVR、gravity）：Klay Thompson、Stephen Curry、Buddy Hield、Luke Kennard、Duncan Robinson、Sam Hauser、Michael Porter Jr.、SGA、Kevin Durant、Luka Dončić、Nikola Jokić、Rudy Gobert、Jalen Williams、Giannis Antetokounmpo、Josh Giddey。使用者預期 Klay、Curry 上升，只報告、不當門檻。

## 3. 限制
- 只寫 `reports/card-0.2.10j+E198-gravity/`；其他目錄唯讀。不改 `src/`、`scripts/`、網站、live/。
- 外部數據只放彙總，原始 Gravity JSON 沿用 `reports/F126-shot-difficulty/gravity-split/`。
- 採用後才另做：賽中 OVR 每日抓 2026-27 引力、網站欄位（取代切入的位置）與說明。

## 4. 使用者裁定（凍結前）
- 係數下限：F-139 顯示引力高的人卡片已經給多，自由擬合很可能接近 0（同 E-181）。選項 (a) 不設下限、(b) 照 R-133 設下限；使用者 2026-11-02 選 **(a) 不設下限**。

## 5. 回報
照 CLAUDE.md 六段（# 總評、這次目標、進步、退步、直觀證據、要你決定的事）；白話講接球射手被低估少了多少、Klay／Curry 名次；Δρ、區間只寫 `report.md`。
