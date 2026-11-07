# 球星重疊遞減驗證：預註冊（跑模擬前凍結）

日期：2026-11-02。role-model（派工 20261102-185900-33a028）。依 `spec.md`（lead 寫），診斷，不改引擎。凍結後不得改；之後任何偏離一律寫進 report.md 的「偏離」段。（L-026）

## 問題與假設
模型的「球星重疊損失 OL」大的隊，實際淨效率是否系統性高於模型預測（殘差 R＝實際 − 模型）？若是，引擎對多個創造者／高用量同場的遞減扣太重。

H1：Spearman(OL, R) > 0。

## 輸入（沿用 E-208，不重做能力值）
- 引擎：sim 0.1.4（`makeRunner` → v53 impactEngine 鏈，`options()` 不動）；repo HEAD 見 `.sha256`；src/ 在此 HEAD 無未提交改動。
- 2025-26：P′ 能力值（`E208-team-rating/lib.mjs` variant `P`，`pprime-day0.json`）。2024-25：P″（`lib2425.mjs` variant `Q`，`pprime-day0-2425.json`）。兩季污染程度不同，2025-26 只當同向確認。
- 代表輪替：該隊整季各場 (c) 分鐘（`minutes-2526.json`／`minutes-2425.json` 的 hrC／arC）逐人平均（缺席場記 0）→ 前 10 人 → `minutes_rules.norm` 縮到 240 分鐘（cap 48）。2025-26 用 inputs.json 的 1230 場，2024-25 用 inputs-2425.json 的 1104 場（我們有的場數）。
- 輸出 `lineups.json`（`prep_lineups.py` 產，只用輸入，未看任何模擬結果；已含在 sha256 清單內）。

## 偏離 spec 的地方（跑前先講）
1. **球星排序用「OVR 代理」不是卡片 OVR**：2024-25 沒有對應的卡片 OVR（現行卡 0.2.12c 只有 2025-26 的 582 人，且是季末版），為了兩季同一定義，球星＝代表輪替中 ≥20 分鐘者，依 E-208 (d) 同一個代理（10 項引擎能力值 long、mid、short、ft、drive、tovSkill、pass、rebound、onBall、help 的未加權平均，已套用 P′／P″ 差值）取前 4 名，同分以 pid 小者先。描述性核對：2025-26 代理球星與 card 0.2.12c 同條件前 4 名的重疊數會報在 report.md，不重跑。
2. **2024-25 的實際淨效率**：`advanced-teams.json` 只有 2025-26。2024-25 用 `inputs-2425.json` 的 `actual2425[team].net`（E-208 以箱分數推算的 NET，覆蓋同一批 1104 場）。2025-26 用 `advanced-teams.json` 的 NET_RATING（官方，82 場）。兩季各減聯盟 30 隊平均。
3. 模型淨效率用「每場淨勝分」（spec 字面）；實際用每 100 回合 NET。兩者差一個 pace 比例（≈1），另報「模型也換成每 100 回合」的版本當描述，不當判定。
4. 每隊代表輪替都有 ≥5 人 ≥20 分鐘，不需處理不足 4 人的情形（`lineups.json` 檢查：nEligible 最少 5）。

## 設計
- 變體（每隊 7 個，同一隊各變體共用 seed，主客依 `s&1` 輪換，`seedOf(s, 500+隊序)`）：
  - `v0`：十人全換成聯盟平均 profile（`avgTeam().roster[2]`＝`xAvg.profiles[2]`，playerId 負值，分鐘不變）。
  - `v1..v4`：只留第 j 顆球星，其餘九人換平均。
  - `v4all`：四顆都留，其餘六人換平均。
  - `full`：十人全在（模型隊）。
- 對手：聯盟平均隊（`avgTeam()`）。
- seed 數：**每個變體每隊 1000 場**（≥200；放大是因為 OL＝Σ單人 − 四人 − 3·v0 含五個噪音項，200 場的單隊 SE 預估 ≈3 分，比 OL 的隊間差異還大）。
- 單人增益 g_j＝mean(vj) − mean(v0)；四人增益 g4＝mean(v4all) − mean(v0)。
- **OL＝Σg_j − g4**；OLr＝OL ÷ Σg_j（Σg_j ≤ 1 的隊不算 OLr）。
- 模型淨效率＝mean(full) 減 30 隊平均；實際淨效率減 30 隊平均；**R＝實際 − 模型**。
- 運算：5090，`run.mjs`（sha256 見清單），輸出 `results/S2526-*.json`、`results/S2425-*.json`。

## 判定（寫死）
- **主檢定 H1 通過**：2024-25 的 Spearman(OL,R) > 0 且 90% bootstrap CI（以隊重抽、5000 次、percentile 5%–95%、rng seed 20261102）下界 > 0；**且** 2025-26 的 Spearman(OL,R) > 0。其餘為不通過（含 CI 含 0）。
- 次要：兩季合併 60 個隊季，OL 前 10 名的平均 R 減後 10 名的平均 R（90% CI，同法重抽隊季）。
- OLr 同樣的 Spearman，只描述。
- 描述（不當判定）：
  - OL 的 MC 噪音：每隊逐 seed OL 的標準誤中位數對 OL 隊間標準差；奇偶 seed 分半的 Spearman。
  - 偏相關：Spearman(OL,R) 受「模型強弱」混淆的檢查——Spearman(model,R)、Spearman(OL,model)、控制 model 後的 OL–R 偏相關（秩殘差法）、實際對模型的回歸斜率。若 OL 與 model 高度相關且 model 與 R 相關，主檢定要附上這個警語。
  - 高用量人數：球星中 `opportunityMeasurement.selfOpportunityRate` ≥ 582 人池第 70 百分位者算「創造者／高用量」；報人數與 OL 的 Spearman（`names.json`）。
  - 機制：引擎中造成遞減的位置（創造者邊際遞減、球權分配、spacing）列程式位置與機制說明，讀碼為主，不改碼、不另跑模擬。
- 例子：OL 最大的 5 個隊季（隊名、季、OL、模型 vs 實際淨效率）。
- 結論措辭：通過＝「在此量法下重疊損失大的隊實際比模型好，指向遞減過重」，仍需另做因果檢驗才能改引擎；不通過＝照實寫。不事後換球星定義或 seed 數。

## 檔案與雜湊
見 `preregistration.sha256`（含本檔、腳本、lineups.json、names.json、E-208 輸入、引擎入口檔）。
