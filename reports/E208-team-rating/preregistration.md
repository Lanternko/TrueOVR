# E-208 球隊評分 v0（無傷病）預註冊

日期：2026-11-02（跑任何 2025-26 回測前寫）。規格：`spec.md`（含修訂 A，使用者裁定「A＋前瞻凍結」）。
分支 claude/project-thread-63h2fz。本檔與 `preregistration.sha256`（列出本檔與所有程式、輸入檔的 sha256）、`forward-2026-27-frozen.json` 一起在回測前 commit。

**限定語（所有結論都要帶）：P′ 版是「部分污染，只當參考，不單獨當證據」。真正的樣本外檢驗是 2026-27 前瞻凍結。**

## 1 引擎與球隊模型
- 引擎 sim 0.1.4（R-120、R-131）：`reports/E120-foul-defense/winimp-core-e120.mjs` 的 `makeRunner()`／`loadX()`，選項 `reports/player-impact-v29/benchmark.mjs` 的 `options()` 原樣（β×2、foulBaseShift −0.05625、pace ×0.998125、γ），不改任何係數；`src/` 預設不動。
- 球隊＝每隊前 10 人（依分鐘），分鐘正規化到 240、單人上限 48；沒有 `sourceRotations`，引擎走 `minuteBudgetSchedule`（預算輪替）。這和校準時用的 workloadRotation 路徑不同，是已知限制。
- 球員 profile＝引擎 `x.players`（ovrInput('both')，v47 輸入＋v53 壓迫，2025-26 量測物件）。引擎找不到 profile 的球員用 `xAvg.profiles[2]`（聯盟分鐘加權平均）代替，並記在結果的 `missing`。
- 平均隊＝`xAvg.profiles` 兩份（10 人各 24 分鐘）。
- ORtg／DRtg／Net（每 100 回合）：球隊對平均隊，S=200 場，主客各半（偶數 seed 球隊在前、奇數對調）；回合數用 POSSESSION 事件數。分數／回合加總後相除。
- 主場：引擎沒有主場優勢。固定 **H=2.5 分**（NBA 近年主場優勢量級，寫死，不看結果調）。每場勝率 p＝Φ((模擬平均分差(主−客)＋H)／σ)，**σ=12.0 寫死**（模型、B0、B-coin 共用）。
- 每場：S=40 seed，seed 規則 `seedOf(s,key)=(imul(s+1,7919)+imul(key+1,1000003))>>>0`，key＝比賽序號 i；`swap=(s+i)&1` 決定引擎內主客位置（引擎對稱，分差一律換算回主−客）。
- 整季預測勝場＝每場 p 加總（主隊 p，客隊 1−p）。

## 2 兩種分鐘
- (a) 主結果：每場實際上場名單與分鐘（`data/season-source/player-games.json`，前 10 人正規化到 240、上限 48）。等於完美傷病資訊。
- (b) 季前預期分鐘：只用前 10 場（每隊）出現的名單，分鐘用 2024-25 每場平均分鐘（`inputs.json` 的 `pre`；新人給 `replMpg=12.0`）。(b) 以「球隊 × 球隊 ordered pairs」870 組、S=40 的平均分差查表，套到每場。已知小洩漏：名單成員由 2025-26 前 10 場決定（含少數交易）。

## 3 能力值版本
- **I**：engine x.players 原樣（2025-26 profile）。**樣本內，不是證據（R-007）**。
- **P′**：能用窗口算的屬性改成 E-175 第 0 天（資料 ≤2024-25）的值，其餘沿用 2025-26。因引擎 profile 的屬性映射和 E-175 卡片映射不同尺度（corr 0.12–0.93），不能直接代入，改加差值：`attr_P′ = clamp(attr_x + (day0 − end), 0, 120)`，`end`＝同一套 E-175 窗口算到 2025-26 季末。差值由 `build_pprime.py` 產生（`pprime-day0.json`）。

逐欄清單（引擎 profile 的欄位）：

| 欄位 | P′ 狀態 |
|---|---|
| drive、ft、mid、pass、rebound、short、tovSkill | **乾淨**（E-175 第 0 天差值，窗口 ≤2024-25） |
| long | **污染**：E-185 四季窗口版沒有重算 ≤2024-25（偏離修訂 A） |
| creation、MPG（seasonMinutesPerGame）、foulDraw | **污染**：沒有重算（creation／foulDraw 不是引擎頂層欄位，MPG 引擎不吃分鐘預算以外的用法；分鐘由我們另給） |
| stamina、physique、heightInches、pos | 污染（2025-26 值；身高體型本質不變，影響小） |
| onBall、help、offBall、screen、handle、breakDbl | 污染（2025-26） |
| shotProfile 與全部 *Measurement／individualOreb 物件（防守、壓迫、籃板、罰球、接觸、補籃…） | **污染**（2025-26 量測；L-091：這些層只有 2025-26 值） |

## 4 洩漏稽核（引擎本身用 2025-26 校準的部分，對 I、P′ 都成立）
| 項目 | 狀態 |
|---|---|
| β×2（defenderFoulBeta）、foulBaseShift −0.05625、pace ×0.998125 | 用 2025-26 校準（R-120、R-131）→ 污染 |
| γ（`reports/sim-0.1.4/ns-foul-gamma-2025-26.json`） | 2025-26 → 污染 |
| E116 犯規擬合 `E116-fouls-matchup/fullfit-f-2025-26.json` | 2025-26 → 污染 |
| spaceCenter 合成中鋒 `player-impact-v20/2025-26-synthetic-center.json` | 2025-26 → 污染 |
| 補籃／籃板／失誤時間等 step4 校準檔（`defense-tenth/step4-*/2025-26/`） | 2025-26 → 污染 |
| measured-rotation out-of-fold 檔 | 本實驗不用（budget 模式），但引擎各係數在 2025-26 輪替下校準 |
| 平均隊 xAvg、替補平均 | 2025-26 分鐘加權 → 污染 |
| (a) 實際名單與分鐘 | 完美傷病／輪替資訊（不是洩漏，是上限情境） |
2024-25 對照回測：**不做**。能力值層（防守、壓迫、籃板等）沒有 ≤2023-24 版本（L-091），做出來也只是另一份污染版，不能當乾淨對照。

## 5 基準
- B0：2024-25 球隊 net（`inputs.json` base2425，與 2025-26 同一估計式）帶到 2025-26；預測分差(主−客)＝net_主−net_客＋H，p＝Φ(／σ)。
- B-coin：只有主場，p＝Φ(H／σ)≈0.583。

## 6 指標與判定
每場：Brier、log loss（p 夾在 [1e-6,1−1e-6]）、勝負命中率（p>.5）、分差 MAE（|預測分差−實際分差|）。30 隊：勝場 MAE；ORtg／DRtg／Net 對 `actual2526`（球隊逐場估計式，非官方）的 MAE（兩邊各減聯盟均值＝置中）與 Pearson r；官方 advanced-teams 數值當參考欄。
Bootstrap：2000 次，以「場」重抽，雙方同一組索引，rng seed 20261102，90% CI＝第 5／95 百分位；勝場 MAE 的差也用同樣索引重算。

**通過條件（主）：P′(a) 的 Brier 比 B0 小，且「P′(a)−B0」的 90% CI 不含 0。** 次要：P′(a) 勝場 MAE 比 B0 小。
結論措辭固定：通過＝「在 P′（部分污染）下通過，只當參考，不單獨當證據」；沒通過＝照實寫沒通過。依 R-113 用 2025-26 判定。I 版與 (b) 版為參考，不參與通過判定。跑完不得改設定再當主結果（L-026）。

## 7 G2／G3
- G2：引擎 sim 0.1.4；卡片版本 card 0.2.12b／inseason 0.2.12b（前瞻用）；E-175 窗口（RAPM 窗口標記：8 項屬性滑動窗口，四季，E-175）；輸入檔 sha256 見 `preregistration.sha256`，結束時重算一份寫進 report.md。
- G3：P 與 I 對同一場比賽用同一組 seed（key＝比賽序號），只有 profile 不同；B0／B-coin 無模擬。
- 5090 與本機的模擬輸出逐位元相同（rating:pre 4 seed 抽查，比對通過；5090 上先同步程式／輸入檔至本機位元組相同才跑）。

## 8 前瞻凍結（2026-27，真正的樣本外檢驗）
`forward-2026-27-frozen.json`（sha256 在 `forward-2026-27-frozen.sha256`）：能力值＝live inseason 0.2.12b／card 0.2.12b（對 x.players 加「live − card 0.2.12b」差值，新人用聯盟平均加差值），分鐘＝各隊目前 MPGhat 前 10 人，資料截止 2026-10-31，已賽 88 場。每隊 ORtg／DRtg／Net、對平均隊勝率、整季預測勝場＝已有 W＋(82−已賽)×對其餘 29 隊的平均勝率（repo 內沒有 2026-27 完整賽程，無法逐場）。凍結檔 commit 後不改；之後每週對真實賽果（本次不評）。

## 9 偏離 spec 的地方（事前寫明）
1. P′ 沒有重算 long、creation、MPG（foulDraw 非引擎欄位）。
2. profile 是引擎 x.players，不是 2025-26 官方卡片。
3. 輪替走 10 人 budget 模式，不是校準用的 workloadRotation。
4. 2024-25 乾淨對照回測不做（L-091）。
5. 前瞻沒有逐場賽程。
6. (b) 的名單來自前 10 場（小洩漏）。
