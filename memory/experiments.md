# 實驗登記（experiments）

模擬版本、卡片版本、預註冊、回測與量測。讀寫規則見 [README.md](README.md)。逐份細節在 `reports/<資料夾>/`。

欄位（固定）：
- **ID**：`E-001` 起，只追加。
- **日期**
- **內容**：在試什麼。
- **設定**：版本、資料、人群、seed、預註冊檔；跑在哪（本機／5090）。
- **結果**：量到的數字與判定。
- **狀態**：`採用`｜`不採用`｜`停止`｜`參考`｜`進行中`。改狀態時括號註明日期與原因。
- **相關**：其他 ID。
- **來源**：commit、報告路徑。

範例：

```
### E-999
- 日期：2026-10-28
- 內容：賽中 OVR C4 回測
- 設定：preregistration-v5（凍結）、起點 Y5／Y6
- 結果：V1、V2 通過
- 狀態：採用
- 相關：F-019
- 來源：commit 560ddcc
```

2026-10-28 建立時由 git log 與報告搬入；只寫到能從 commit 訊息與 `reports/status/status.md` 確認的程度，細節以報告為準。防守批次（E-003、E-008–E-010）沒有獨立 commit（都在 b8dabc6 一次歸檔），日期取自報告檔的修改日期。

---

### E-001
- 日期：2026-09-05
- 內容：數值模型 v0.4：機率模型、模擬引擎、51 項驗證、OVR 逆推。
- 設定：本機。
- 結果：51 項驗證；踩過的坑見 L-001–L-012。
- 狀態：採用
- 相關：L-001–L-012
- 來源：commit 8d18901

### E-002
- 日期：2026-10-16
- 內容：模型 v14–v51 研究歸檔（球權、防守、輪替、進攻罰球等）。
- 設定：`reports/model-evolution-20261016/`；`docs/*-v45.md`…`*-v51.md`。
- 結果：球隊勝場 MAE v14 5.73 … v41 6.67（`reports/status/status.md` 球隊表）。
- 狀態：參考
- 相關：無
- 來源：commit b8dabc6

### E-003
- 日期：2026-10-12
- 內容：防守第 1–6 批（defense-runs、a、b1、third…sixth）。
- 設定：`reports/defense-*`；`npm run test:defense*`、`test:ability-sixth`。
- 結果：見各批報告。
- 狀態：參考
- 相關：E-008
- 來源：`reports/defense-runs/`…`reports/defense-sixth/`

### E-004
- 日期：2026-10-16
- 內容：OVR 第 1 步：v47 位置基準事後校正。
- 設定：`reports/ovr-v47-2025-26/`、`ovr-2025-26-positional/`。
- 結果：見報告。
- 狀態：參考
- 相關：E-005
- 來源：commit 000359f

### E-005
- 日期：2026-10-16
- 內容：OVR 第 2 步：可靠度收縮與本機加樣本驗證腳本。
- 設定：本機。
- 結果：見報告。
- 狀態：參考
- 相關：E-004
- 來源：commit 7254a33

### E-006
- 日期：2026-10-16
- 內容：期望產出 OVR 原型（2025-26）。
- 設定：`reports/ovr-expected-2025-26/`。
- 結果：見報告。
- 狀態：參考
- 相關：E-007
- 來源：commit 5b7b520

### E-007
- 日期：2026-10-16
- 內容：模擬校準的能力值 OVR（4 組種子）；新增「創造」能力值。
- 設定：`reports/ovr-calibrated-2025-26/`。
- 結果：查明中距離與持球防守不值分的原因（F-024）。
- 狀態：參考
- 相關：F-024、L-024
- 來源：commit d0b4b07、018c023、62a8be0

### E-008
- 日期：2026-10-12
- 內容：防守第七批：校準收尾、2024-25 跨季盲測、前季先驗。
- 設定：單一日曆截止日、25／41／55 切分、相同 20 seed；`npm run ability:seventh:*`、`npm run test:ability-seventh`。
- 結果：v4 收尾驗收未過，2024-25 改善未穩定重現；前季先驗沒有可靠改善。正式基準維持 v3。
- 狀態：不採用
- 相關：F-017、E-009
- 來源：`reports/defense-seventh/closeout.md`

### E-009
- 日期：2026-10-12
- 內容：防守第八批 A（重新分析與控制組）與 B（固定殘差倍率 c(25)=0.500000、c(41)=0.424513、c(55)=0，v5 凍結規格）。
- 設定：`reports/defense-eighth/a/closeout.md`、`b/closeout.md`、`b/v5-freeze.json`；`npm run test:ability-eighth-a`、`test:ability-eighth-b`。
- 結果：倍率在已看過答案的開發季選出，不算盲測（L-026）；simple 目標斜率超出預定範圍，未完成分散校準。
- 狀態：參考
- 相關：E-010、L-026
- 來源：README「已知限制」

### E-010
- 日期：2026-10-12
- 內容：防守第八批 C：兩個盲測季（2023-24、2022-23）。
- 設定：嚴格可用 1063／1079 場；共同日曆 25／41／55、每版本 20 seed；跨季配對 franchise＋seed 聯合重抽 20,000 次 95%／99.8% 區間；`npm run test:ability-eighth-c`。
- 結果：只有 v4cal 對 v4 的 net RMSE 改善跨季確認；v4 對 v3 在 K25 確認退步；v5 對 v4、v4cal 對 simple／simplecal 分不出。正式基準維持 v3。完成後停下，未開始下一批。
- 狀態：不採用
- 相關：F-017、R-010
- 來源：`reports/defense-eighth/c/closeout.md`

### E-011
- 日期：2026-10-16
- 內容：真實影響力驗收：在場／不在場與 RAPM 腳本。
- 設定：本機；`reports/impact-rapm/`、`reports/player-impact-validation/`。
- 結果：RAPM 結果見報告。
- 狀態：採用（RAPM 成為驗收參考）
- 相關：E-012
- 來源：commit 0757b71、cee0a67

### E-012
- 日期：2026-10-16
- 內容：以 RAPM 校準 box score OVR（RAPM 支援 box score 先驗），最終 OVR 第一版。
- 設定：`reports/ovr-rapm-calibrated-2025-26/`、`ovr-final-2025-26/`。
- 結果：修正 box score 先驗未收縮的錯誤。
- 狀態：參考
- 相關：E-011、E-013
- 來源：commit f4d2804、0bf073c、1f7377e

### E-013
- 日期：2026-10-16
- 內容：卡片 OVR 公式：以能力值預測最終 OVR。
- 設定：`reports/ovr-card-2025-26/`。
- 結果：見報告。
- 狀態：參考
- 相關：E-012
- 來源：commit f0dccee

### E-014
- 日期：2026-10-16
- 內容：v52 外線防守診斷。
- 設定：`reports/player-impact-v52/`。
- 結果：持球防守接回效果小（F-022）。
- 狀態：參考
- 相關：F-022
- 來源：commit e0ae5dc

### E-015
- 日期：2026-10-16
- 內容：四因素 RAPM：量測哪些防守是可重現的個人能力。
- 設定：`reports/impact-rapm/`。
- 結果：見報告（F-023）。
- 狀態：參考
- 相關：F-023
- 來源：commit e2a5038、db2d55a、3aeccb9

### E-016
- 日期：2026-10-17
- 內容：v53 防守壓力：逼出抄截以外的失誤、放大命中率壓制；期望分差用運氣記帳降雜訊。
- 設定：先 4 組種子判斷不了，再 8 組種子；平均運氣用群集標準誤。
- 結果：機制 1 有效、機制 2 不需要；v53 採用，卡片能力值改以 v53 期望分差校準，新增「壓迫」。
- 狀態：採用
- 相關：L-024、E-017
- 來源：commit 9b8aea9、a2ec37a、f690fc7、9558520、936ae3f、bd70818、63fb7af

### E-017
- 日期：2026-10-18
- 內容：v53 全季球隊量測。
- 設定：30 隊全季；`reports/player-impact-v53-team/`。
- 結果：2025-26 勝場 MAE 4.56、淨分 RMSE 2.019（壓迫係數樣本內）。
- 狀態：採用
- 相關：F-012
- 來源：commit a764cdb

### E-018
- 日期：2026-10-18
- 內容：卡片 OVR 混合目標（sim＋RAPM），預註冊。
- 設定：`reports/ovr-blended-2025-26/`。
- 結果：α=0.5 通過關卡，正式板改用（選項 B）；ρRAPM 因此部分樣本內。
- 狀態：採用（2026-10-20 由 E-026 取代）
- 相關：L-022、E-026
- 來源：commit 36c82a1、f4bbb8c

### E-019
- 日期：2026-10-18
- 內容：混合版卡片 OVR 的替補可靠度收縮，預註冊。
- 設定：`reports/ovr-blended-bench-shrinkage/`。
- 結果：G1、G2 未通過（G2 是平方誤差，不是 Brier，L-025）。
- 狀態：不採用
- 相關：L-025
- 來源：commit 1559e6b、964e814、e2a0e29

### E-020
- 日期：2026-10-18
- 內容：卡片屬性小樣本收縮，預註冊。
- 設定：`reports/ovr-shrinkage-2025-26/`。
- 結果：關卡 3 未過。
- 狀態：不採用
- 相關：無
- 來源：commit ac4b1a7

### E-021
- 日期：2026-10-18
- 內容：v53 模擬板可靠度收縮。
- 設定：`reports/ovr-v53-shrinkage-2025-26/`。
- 結果：第一版不採用；修正版（先發不收縮）採用。v53 收縮修正版樣本外 ρ 0.356／0.246。
- 狀態：採用（修正版）
- 相關：E-016
- 來源：commit 8061da5

### E-022
- 日期：2026-10-18
- 內容：v54：三分／禁區命中率改用可靠度加權收縮（EB），球員層與球隊層模擬（5090 遠端）。
- 設定：`reports/ovr-v54-*`、`reports/player-impact-v54-team/`。
- 結果：個人 ρ 提高，但球隊 2025-26 勝場 MAE 變差（F-013）；收束，卡片板仍為 v53 校準。
- 狀態：不採用（收束）
- 相關：F-013
- 來源：commit 896e132、5364ab8、23bc68e

### E-023
- 日期：2026-10-19
- 內容：v55 板凳屬性建構（多季加權＋角色條件先驗）。
- 設定：`reports/ovr-v55-bench-prior-2025-26/`。
- 結果：AC 通過預設門檻，但替補 AC 樣本外補驗不通過。
- 狀態：不採用
- 相關：無
- 來源：commit 71b9c29、23bc68e

### E-024
- 日期：2026-10-19
- 內容：v55 卡片修正三方向：B（吃餅長人禁區出手來源，B1／B2／B12）、C1（originShare 第 16 屬性）、D1（屬性建構層 long 去膨脹 `--attr-deflate`）。
- 設定：預設關閉；`reports/ovr-v55-finisher-fix-2025-26/`、`ovr-v55-card-origin-attr-2025-26/`、`ovr-v55-attr-deflate-2025-26/`；7 人驗收表。
- 結果：B12／C1／D1 樣本外 ρ 約 0.455–0.458，Karlo 掉名未過；C1 係數 0.031（SE 0.079）與 0 無法區分（L-023）。
- 狀態：不採用
- 相關：L-023、F-014
- 來源：commit 7393f8f、2f729a2、17cac74、e78dee1

### E-025
- 日期：2026-10-19
- 內容：2K27 評分＋2K19–27 逐年總評 × 卡片 OVR × v54 模擬板 × RAPM 對照。
- 設定：`reports/ovr-v55-2k27-compare/`。
- 結果：吃餅長人高估（F-014）；2K 成為外部基準。
- 狀態：參考
- 相關：F-014
- 來源：commit c85ea85

### E-026
- 日期：2026-10-20
- 內容：v55 卡片修正 E 系列：低分鐘收縮（E1）、吃餅折扣（E2）、合併（E3）。
- 設定：`reports/ovr-v55-card-E-2025-26/`；E2-λ0.4＝只打折 `short`：`effective_short = 70 + (short−70) × (s̃ + 0.4×(1−s̃))`，s̃＝自創禁區出手比例；PF/C 且 `creation` 在 [55,65] 斜坡內折扣線性減弱，≥65 幾乎不打折（固定規則，非回歸係數）。
- 結果：E2-λ0.4 首次同時過 Karlo 掉名與 ρ 門檻（樣本外 0.457／0.245、2K 0.478）；副作用 Gobert 第 91（F-015）。
- 狀態：採用（2026-10-21 由 E-029 取代）
- 相關：F-015、R-001、R-006
- 來源：commit 1609313、ef11e80

### E-027
- 日期：2026-10-20
- 內容：v56：在 E2-λ0.4 上疊加 PF/C 防守加分修正 Gobert 防守低估。
- 設定：`reports/ovr-v56-card-defense-2025-26/`；F2 γ=0.5（用 RAPM pooledD）。
- 結果：樣本外 ρ 0.474／0.273、2K 0.488。
- 狀態：採用（之後由 E-028、E-029 取代）
- 相關：F-015、R-006
- 來源：commit e483017

### E-028
- 日期：2026-10-20
- 內容：v57 G3 卡片（γ=1.0、δ=0.25）。
- 設定：`reports/ovr-v57-card-2025-26/`。
- 結果：樣本內 ρRAPM 0.843／0.697；樣本外 0.555／0.401；2K 0.530。
- 狀態：參考（v58 在它上面加封頂）
- 相關：E-029、L-016
- 來源：`reports/status/status.md`

### E-029
- 日期：2026-10-21
- 內容：v58 H1-m0：v57 G3＋2K 名次封頂（封頂只讀 RAPM），加入 RAPM 分半樣本外驗收。
- 設定：`reports/ovr-v58-holdout-2025-26/`、`ovr-v58-codex/`、`ovr-v58-ds-high/`。
- 結果：19/19 硬門檻全過；樣本外 0.563／0.391、2K 0.537；前十長人只有 Wemby／Giannis／Jokić／Chet。
- 狀態：採用（目前正式卡片）
- 相關：F-011、R-012
- 來源：commit f2f2bbb

### E-030
- 日期：2026-10-21
- 內容：補量測：模擬板與舊卡片層補樣本外 ρ 與對 2K27 ρ，新增卡片球隊指標與版本趨勢。
- 設定：`reports/ovr-metrics-backfill-2025-26/`。
- 結果：見 `reports/status/status.md`。
- 狀態：採用
- 相關：F-011
- 來源：commit bb9e8e4

### E-031
- 日期：2026-10-27
- 內容：v5 §R.3：重建 D1／D2 答案卡，RAPM 改為含目標季、最多四季；2023-24 答案卡重建；主卡恢復三季 D1。
- 設定：`reports/ovr-inseason-2026-27/v5/`。
- 結果：見報告。
- 狀態：採用
- 相關：E-033
- 來源：commit 9bee696、c8d3d48、6ff3a9b

### E-032
- 日期：2026-10-28
- 內容：v5 延伸回測資料：2010-11～2023-24 box 與 stint 歷史檔。
- 設定：`v5/history`（PR #5）。
- 結果：2021-22 stint 來源與 cdn 版不同（F-021）。
- 狀態：採用
- 相關：F-021
- 來源：commit ce2bff6

### E-033
- 日期：2026-10-28
- 內容：v5 Path A 賽中 OVR 判定：C4（單調收縮）vs C3（λ 混合）vs A（上季卡）。
- 設定：`preregistration-v5.md` §2–§3、`preregistration-v5-errata-c4.md`（凍結）、`disclosure-pointwise-ovr.md`；主判定 Y5、Y6，敏感度 Y3，次要 D1–D3。
- 結果：C4 與 C3 都通過，照 errata 順序上線 C4。Y3 因 |E_eff|=1 降為敏感度（L-019）。
- 狀態：採用
- 相關：F-019、F-020、L-019、R-008
- 來源：commit 560ddcc；`reports/ovr-inseason-2026-27/v5/pathA/README.md`

### E-034
- 日期：2026-10-28
- 內容：賽中 RAPM（C4R）。
- 設定：`v5/pathA/preregistration-rapm-inseason.md`（凍結，使用者核可）；`v5/tools/rapm_inseason_pathA.py`。
- 結果：R1 先決檢定 Y6 N=82 不過（最大 |net| 差 1.268、onlyRef=2），照 §4 整輪停止；G1–G3 沒算，沒看任何 C4R 誤差數字。
- 狀態：停止
- 相關：F-021、L-018、R-008
- 來源：commit 560ddcc；`reports/ovr-inseason-2026-27/v5/pathA/README-rapm-inseason.md`

### E-035
- 日期：2026-10-16（git log，b8dabc6；報告未寫日期）
- 內容：防守第九批步驟 1 提案：以真實強度為底、加上陣容差（Δ陣容）。
- 設定：只有提案，未實作；偏好選項見 proposal.md。
- 結果：規劃估計淨分 RMSE 降約 0.15–0.40、勝場 MAE 降約 0.15–0.50，報告明寫是規劃估計、未量測。
- 狀態：參考
- 相關：E-036、F-026
- 來源：reports/defense-ninth/proposal.md；commit b8dabc6

### E-036
- 日期：prereg 2026-10-13T00:39:47.300Z（報告內文）；檔案入庫 2026-10-16
- 內容：防守第九批步驟 2：四季開發診斷（Δsim-v3、Δsim-v4、Δseg、Δnaive）。
- 設定：四季全部已看過答案；K25/K41/K55；聯合 95% 區間（球隊＋種子 bootstrap 20000）；SHA 3b6261c7…5954e。
- 結果：三 K 合併 RMSE 對 naive 4.182：sim-v3 4.142、sim-v4 3.951、seg 3.675。Δseg 對最小者差 K25 -0.501 [-0.825,-0.128]、K41 -0.595 [-0.978,-0.128]、K55 -0.506 [-0.973,-0.023]。符合開發門檻：sim-v3、sim-v4、seg；尚非盲測確認。解讀檔建議 Δseg 為唯一主盲測候選，只有它的 95% 聯合區間在 0 以下，99.8% 區間跨 0。
- 狀態：參考
- 相關：E-035、E-037、F-026
- 來源：reports/defense-ninth/development/closeout.md、interpretation.md；commit b8dabc6

### E-037
- 日期：2026-10-16（git log）
- 內容：防守第九批盲測資料可行性探測（2021-22、2018-19、2017-18 端點 HEAD）。
- 設定：CDN 回 403／403，Stats 15 秒逾時；對照用已知可用網址也回 403。沒有下載任何資料。
- 結果：「三季盲測可行性仍有條件」；探測無法分辨「不存在」與「被擋」。
- 狀態：參考
- 相關：F-027
- 來源：reports/defense-ninth/development/feasibility.md；commit b8dabc6

### E-038
- 日期：2026-10-16（git log）
- 內容：防守第十批步驟 1：「純球員卡」向性稽核。
- 設定：只量測，步驟 2、3 未跑。
- 結果：凍結 v3 的近框保護與防守籃板主路徑被區段防守訊號取代，不符合新「純球員卡」定義；四個方向欄位皆 70。
- 狀態：參考
- 相關：E-039
- 來源：reports/defense-tenth/step1/report.md；commit b8dabc6

### E-039
- 日期：2026-10-16（git log）
- 內容：防守第十批步驟 2：純卡四季診斷（240 補跑 = 4 季 x 3 K x 20 種子，種子 20261012–31）。
- 設定：純卡 vs v3 vs v1 vs simple；四季皆已看過答案。
- 結果：淨分 RMSE（純卡/v3/v1/simple）K25 4.933/4.526/4.917/4.225、K41 5.014/4.766/4.998/4.294、K55 5.370/4.977/5.497/4.555。純卡減 simple：K25 0.708 [-0.087,1.453]、K41 0.719 [0.046,1.434]、K55 0.815 [0.149,1.573]。勝場 MAE 三 K 點估計都較差但聯合區間含 0。關掉區段訊號使防守 RMSE 三 K 顯著升高。結論：不採用純卡取代 simple。
- 狀態：不採用
- 相關：F-025、E-038
- 來源：reports/defense-tenth/step2/report.md；commit b8dabc6

### E-040
- 日期：規則 2026-10-13T04:18:13.407Z（報告內文）
- 內容：防守第十批步驟 3-A：跨季純卡，半盲（protocol tenth-cross-personal-v1）。
- 設定：SHA 8296c18e…5bd；三季皆已看過答案，只稱半盲，未改凍結版本。
- 結果：prior minutes 對均值回歸對照：淨分 RMSE 差 0.956 [0.022,1.957]（顯著較差）、勝場 MAE 差 1.353 [-0.287,3.157]。真實分鐘診斷：淨分 -0.384 [-1.293,0.587]、勝場 -0.928 [-2.455,0.724]，皆不可分辨。
- 狀態：不採用
- 相關：F-025
- 來源：reports/defense-tenth/step3-a/report.md:7；commit b8dabc6

### E-041
- 日期：登記 2026-10-13T05:22:10.790Z、曲線鎖定 05:24:01.159Z（報告內文）
- 內容：防守第十批步驟 3-A2：分層診斷與年齡曲線（L1/L2/L3、P3）。
- 設定：SHA fa301dfa…67cd；P3 是唯一只用前季個人資料的新預測版本，仍屬已看過答案的半盲。
- 結果：2025-26 淨分 L2−L1 -0.475 [-1.020,0.111]、L3−L2 0.080 [-0.367,0.489]、P3−A -0.053 [-0.398,0.304]；勝場 MAE -1.063 [-2.003,-0.070]、0.077 [-0.700,0.927]、0.150 [-0.615,0.868]。淨分三項皆不可分辨。「完成A2即停下，B/C未開始。」
- 狀態：參考
- 相關：E-040
- 來源：reports/defense-tenth/step3-a2/report.md；commit b8dabc6

### E-042
- 日期：T0 2026-10-13T07:39:42.310Z、T1 06:34:58.236Z、T2 06:56:53.816Z（報告內文）
- 內容：防守第十批步驟 4 的 T0/T1/T2 診斷（t2-supplement、t2b 只是球員描述表，無獨立結論）。
- 設定：T0 純卡排名線；T1 凍結 v3/v1/A2 排名線；T2 防守來源端點（575 個成功，嚴格覆蓋 86.42–96.59%）。
- 結果：T0：純卡 1/4 季通過淨分排名線（各季淨分 RMSE 2.857、2.470、3.061、3.647），含區段訊號的 v3 也是 1/4。T1：2025–26 凍結 v3 通過兩條排名線；v1 不通過；A2 的 L1、L2 三季皆未過。T2：直接防守事件與近框壓制最值得作新卡來源；官方個人防守效率、原始在場效率、三分命中率差不適合直接當可攜防守能力。
- 狀態：參考
- 相關：E-039、E-043
- 來源：reports/defense-tenth/step4-t0、step4-t1、step4-t2 的 report.md；commit b8dabc6

### E-043
- 日期：2026-10-14（登記時間戳，步驟 4 rebounds 系列 05:43–08:55）
- 內容：防守籃板與進攻籃板的前置稽核：dreb（pure-dreb-rate-1）、body、opportunity、components（oreb-components-offline-1）、context、talent。
- 設定：四季皆已看過答案、20 種子、樣本內。
- 結果：dreb 未達後續研究條件，維持 T0 純卡基準（淨分 RMSE 差 -0.180 [-0.380,+0.039]；DREB RMSE 差 -0.659 [-0.807,-0.468] pp）。body：身高體重可分開保留，現有來源不足以估力量、彈跳、觸球高度。opportunity：守恆成立，缺口是位置標籤代替機會。components：三個候選皆未過門檻，不接入引擎（2025–26 OREB/36 MAE：carry-over 0.3338、加機會 0.3200、加取得率 0.3178、兩者 0.3187）。context：角色與隊友代理都沒有可確認的 OREB 價值（0.35151 對 0.35391–0.35512）。talent：沒有證據把選秀體測寫進卡或引擎。
- 狀態：不採用
- 相關：E-044
- 來源：reports/defense-tenth/step4-rebounds*/report.md（本體、-body、-opportunity、-components、-context、-talent）；commit b8dabc6

### E-044
- 日期：2026-10-14（git log；報告時間戳未逐份核對）
- 內容：OREB 取得率候選（step4-rebounds-oreb）與個人分配（-allocation）。
- 設定：四季、20 種子、樣本內。
- 結果：oreb：OREB 率去均值 MAE 2.0695→0.4600 pp（差 -1.6095 [-1.8982,-1.2832]）；淨分 RMSE 3.0748→2.5546（差 -0.5202 [-0.8236,-0.2047]）；勝場 MAE 5.5500→5.0575（差 -0.4925 [-0.9921,+0.0058]，區間跨 0）。allocation：個人 OREB36 MAE 0.4605→0.0956（-0.3650 [-0.3902,-0.3312]）；淨分 RMSE 2.5546→2.5704（+0.0158，區間跨 0）。兩者保留為獨立開關。
- 狀態：採用
- 相關：E-043、E-047
- 來源：reports/defense-tenth/step4-rebounds-oreb、-allocation 的 report.md；commit b8dabc6

### E-045
- 日期：2026-10-14 至 10-15（登記時間戳，nonshoot-foul 為 2026-10-15T01:51:06.728994）
- 內容：OREB 之後的診斷與單因子試驗：after、paths、zone-reader、state-time、possession-value、putback-risk、turnover-types、nonshoot-foul。
- 設定：多為量測；單因子試驗皆不改基準。
- 結果：after 量測：模擬補籃近框出手 15.121 對真實 31.700；到下一個結果的時間 4.528s 對 2.552s。zone-reader：10,767 筆矛盾中距離標籤改為近框、969 筆未知。putback-risk、turnover-types：不採用。nonshoot-foul：「局部修正有效，保留為獨立候選；基準不變」。
- 狀態：參考
- 相關：E-044、E-046
- 來源：reports/defense-tenth/step4-rebounds-{after,paths,zone-reader,state-time,possession-value,putback-risk,turnover-types,nonshoot-foul}/report.md；commit b8dabc6

### E-046
- 日期：2026-10-14T20:09 至 2026-10-15T03:39（登記時間戳；clock-competing 為 2026-10-15T03:39:51.367263）
- 內容：補籃時間與時鐘系列：putback-time、clock、turnover-time、clock14、rim-calibration、clock-sources、clock-state、rim-clock、clock-competing。
- 設定：單因子；clock-competing SHA 101e648f…d4e。
- 結果：putback-time 不採用（淨分 RMSE 2.5704→2.5263，差 -0.0441 [-0.1808,+0.0978]）。clock 未過候選門檻（2.5704/2.5263/2.5544）。turnover-time：時序辨識改善、準確度未顯著（2.5544→2.5553，勝場 MAE 5.0525→4.9375）。clock14：推翻「把 0.73% 補成新的 14 秒違例」，時間相容只有 12–19%。rim-calibration：pEffective=0.211278187，未過驗收，不升基準。clock-sources 只找到 2 例官方重播；clock-state 現有資料無法辨識碰框，不改引擎。clock-competing：計數、漂移、無退步閘門過，時序診斷未過，保留實驗選項、基準不升。
- 狀態：不採用
- 相關：E-045、E-047
- 來源：reports/defense-tenth/step4-rebounds-{putback-time,clock,turnover-time,clock14,rim-calibration,clock-sources,clock-state,rim-clock,clock-competing}/report.md；commit b8dabc6

### E-047
- 日期：2026-10-15（git log 最後入庫 2026-10-16，b8dabc6）
- 內容：防守第十批收束（step4-rebounds-closeout）。
- 設定：預設組合 `pure-oreb-turnover-time-1`。
- 結果：可選時鐘淨分 RMSE 2.5553→2.5592（+0.0039 [-0.1199,+0.1321]）、勝場 MAE 4.9375→4.9775，故不入預設。「本輪已收束」；「不再為時鐘開新一輪」；補籃／重攻是下一個候選，「目前未證實收益，不自動開始」。四季皆已看過答案，是重現成績，不是事前或換隊預測。
- 狀態：停止
- 相關：E-044、E-046、F-026
- 來源：reports/defense-tenth/step4-rebounds-closeout/report.md:63-68；commit b8dabc6

### E-048
- 日期：2026-10-28（報告內文用 seed 20261028；comparison.json 修改時間 2026-10-28 17:28）
- 內容：v59 第一階段：3PT 拉回目標改為「依出手頻率預測的三分%」。
- 設定：擬合只用 2010-11～2023-24；回測為 2025-26 前 41 場特徵對後 41 場 3P%，後 41 場 3PA>=50 共 313 人；配對 bootstrap 2000 次。
- 結果：勝出 (b) 只用出手頻率（k=407.396）；3PA 加權中位絕對誤差 3.37→3.21 pp，改善 0.16 pp，但 90% 區間 [-0.50, 0.25] pp 含 0，證據偏弱。(c) 加罰球% 為 3.28 pp，未比 (b) 低 0.05 pp，不採用 (c)。Portis 3PT 98.5→85.6、排名第 2→第 9。報告沒有寫是否升為正式卡。
- 狀態：不採用（2026-10-28，改善在雜訊內且 Giannis 掉出前十；使用者改走 v62，見 E-056）
- 相關：E-033、E-056
- 來源：reports/ovr-v59-3pt-prior-2025-26/report.md:3-5；未追蹤（.gitignore）

### E-049
- 日期：2026-10-27（S1-report.md 內文，第 2 輪）
- 內容：賽中 OVR S1：2024-25 先驗重建。
- 設定：preregistration §2.2、§6.2；依使用者裁決改 sanity 判準後重跑，先驗內容與第 1 輪完全相同。
- 結果：S1 全數通過。569 人（要求 >=550）；15 項覆蓋率 100%；與 personal-cards 9 項 box 能力值 Spearman 0.9908–1.0000；撤掉參考檔校準後逐項中位絕對差最大 2.430（short，門檻 <=5）。
- 狀態：參考
- 相關：E-050
- 來源：reports/ovr-inseason-2026-27/S1-report.md；未追蹤（.gitignore）

### E-050
- 日期：2026-10-27（backtest/report.md 內文）
- 內容：賽中 OVR v1 回測 S2–S6（預註冊 preregistration.md，日期 2026-10-26）：收縮版 C 對先驗 A 與觀測 B。
- 設定：k 由 2022-25 季內分半信度反解；N=3/5/10/20。
- 結果：§4.4 判「未勝出」，五條門檻第 3、4 條過，第 1、2、5 條未過。C 在 4 個 N 的 ρ 都贏 A；N=10 輸 B（ρ 0.8044 對 0.8054、OVR MAE 5.669 對 5.712）；N=20 輸更多（0.8253 對 0.8456、5.459 對 5.159）。80% 區間覆蓋率 0.42／0.55。正式維持先驗，不發布區間，S7 不做。
- 狀態：不採用
- 相關：E-051
- 來源：reports/ovr-inseason-2026-27/backtest/report.md:1-12；未追蹤（.gitignore）

### E-051
- 日期：2026-10-27（preregistration-v2.md 與 v2/report.md 內文）
- 內容：賽中 OVR v2：k 含跨季漂移 δ²，加 OVR 區間與 A/B 退路（種子 20261026，未做 S7）。
- 設定：只用 2023-24→2024-25 的 δ²；2025-26 只在 S4 之後當答案。
- 結果：不採用 C_v2；五條門檻第 1、2、5 條未過，§2.5 退化條款（Σδ² <= 0.05·Σσ²）成立，走 §4.4 退路，一律顯示 A（A/B 退路）。
- 狀態：不採用
- 相關：E-050、E-052
- 來源：reports/ovr-inseason-2026-27/v2/report.md；preregistration-v2.md；未追蹤（.gitignore）

### E-052
- 日期：2026-10-27（preregistration-v3.md 與 v3/report.md 內文）
- 內容：賽中 OVR v3：逐能力值逐 N 的今年訊號權重 w_a(N)＋多起點 expanding window 回測（補抓 2021-22）。
- 設定：種子 20261026；候選依 §2.5 選 C2；2021-22 的 mid/short/creation 層不可行（§4.3）。
- 結果：不採用 v3，維持 v2 退路（一律顯示 A）。§7 指標 1 有 3 格失敗（D2 N=3、D2 N=10、D3 N=3）；指標 2 全過；80% 覆蓋率 0.46／0.49 遠低於 [0.70,0.90]，ε_ovr raw 13.70／8.77／6.68 > 3.0，不發布區間。
- 狀態：不採用
- 相關：E-051、E-053
- 來源：reports/ovr-inseason-2026-27/v3/report.md；未追蹤（.gitignore）

### E-053
- 日期：2026-10-27（preregistration-v4.md、v4/report.md 內文；檔案修改 2026-10-27 06:25）
- 內容：賽中 OVR v4：收縮候選 C3（λ 混合）＋座標補回 2021-22 mid＋經驗分位區間（P0→P7）。
- 設定：種子 20261026；λ 依 §2.3 機械選出，每步連跑兩次比對 SHA。
- 結果：G3 = false。D2 N=3 C3 4.4647 > A 4.4596；N=5 4.5321 > 4.5262；N=10 4.8021 > 4.4596；D3 N=3 5.9522 > 5.8366；其餘 4 格過。C3 在 D2 反而輸給 A 與 v3 的 C2。F0 未執行，`v4/frozen/params-2026-27.json` 與 `FROZEN.sha256` 不存在。後續由 v5 勘誤（preregistration-v4-errata-v5.md，2026-10-28）改答案 RAPM 欄。
- 狀態：不採用
- 相關：E-052、E-031、E-033
- 來源：reports/ovr-inseason-2026-27/v4/report.md:24,81,86；未追蹤（.gitignore）

### E-054
- 日期：2026-10-28
- 內容：v60 切入 A 階段：卡片 `drive` 拆成 `foulDraw`（原 FTA/FGA 百分位）與新 `drive`（非助攻突破，PBP descriptor 類別加權近似）。只改卡片，模擬未拆。
- 設定：2025-26 前 41 場切點（每隊約 38.3 場，engine-signals 574 場）；v58 H1-m0 校準流程與 evaluate.mjs 19 項門檻。
- 結果：Gobert 切入第 3→第 196（drive 53.8、foulDraw 99），SGA 18→2、Brunson 98→14。OVR 對 v58 ρ 0.9999、最大變動 0.7，Gobert OVR 維持 84.9。evaluate 19/19。App 重跑 ranking 雜湊 79D0CB17… 吻合。回歸裡新 drive 係數 −0.013（SE 0.072），價值歸 foulDraw（+0.074/10 點），見 TODO.md。
- 狀態：參考（待使用者決定是否升正式卡；模擬端拆分屬 B 階段）
- 相關：E-029、R-015、R-016
- 來源：reports/ovr-v60-drive-split-2025-26/；未追蹤（.gitignore）

### E-055
- 日期：2026-10-28
- 內容：v61 低分鐘球員膨脹修正：比率型屬性（rebound、pass、tovSkill、foulDraw、drive 等）改為往球員自己的歷史（上季）拉回，沒有歷史才往聯盟平均拉回。不設最少出場分鐘篩選（R-014）。
- 設定：派工 20261028-173721-31b6f1（role-card、worker 帳號）；long 欄應與 v60 相同。
- 結果：rebound、pass、tovSkill、foulDraw、drive、mid、short、ft 八欄先往本人前 3 季歷史拉回（k、λ、kh 各欄擬合；歷史季回測，2025-26 前 41→後 41 為測試）。測試集 MAE 八欄都是「往本人歷史」最低，對聯盟平均版的區間全不含 0；對另一候選在 drive、mid 含 0。long 與 v60 逐人相同（lead 重算 582 人 0 差）。evaluate 19/19；16 名長人達標 15/16（v60 16/16）；對 2K27 ρ 0.5376→0.5092（樣本外訊號，變差）；對 RAPM ρ 0.8520→0.8685（樣本內，R-007 不算證據）。抽查：Darius Brown II 籃板 99→53.5、名次 172→359；Colby Jones 107→316；但 N'Faly Dante 513→222（歷史好）、Taj Gibson 293→513；MIN<100 的 79 人名次中位 369→316、前 200 人數 12→8。傷停明星組只有 Holiday（27→27），樣本不足。ranking.csv sha256 6238984a…a62c，子 session 重跑一致、lead 重算一致。子 session 另加 kh 參數（spec 外）；2024-25 用本機存檔。
- 狀態：參考（2026-10-28，等使用者 G5 抽查；2K27 ρ 下降要判斷）
- 相關：E-054、R-014
- 來源：reports/ovr-v61-shrink-history-2025-26/

### E-056
- 日期：2026-10-28
- 內容：v62 3PT 第二階段（卡片端）：研究投籃難度（持球自投／接球、防守距離）與出手量對 3PT 屬性的影響。
- 設定：派工 20261028-173433-e327a1（role-card、worker 帳號）；資料抓不到就回報失敗，不硬做。
- 結果：資料取自 stats.nba.com CatchShoot／PullUp＋最近防守者距離四段，manifest 1101 筆，2025-26 切點與 seventh-base 30/30 相同。擬合季選法勝出 (b)（v59 方法）；難度調整 (c)、(c)+出手量 (d) 都沒比 (b) 低 0.05 pp。測試集中位誤差 (a) 3.387、(b) 3.155、(c) 3.362、(d) 3.381 pp，中位差的 90% 區間全含 0；(b)−(a) MAE −0.178 [−0.32, −0.05] 是唯一有訊號的比較。控制難度後出手量沒有額外預測力。直覺驗收未過：(b) 下 Curry 13、Edwards 26、Knueppel 2、LaMelo 52；(c) 下 27／7／5／72；加「承擔分數」旋鈕 w 0–40 都無法四人同時進前 15（LaMelo 實際 36.8%、期望 34.9%）。前十長人門檻未過（Giannis 掉出）。子 session 撞 max_turns 60 截斷，但 report.md 已產出；雜湊未由 lead 重跑。
- 狀態：參考（2026-10-28，直覺驗收未過；等使用者決定 3PT 的定義是「命中能力」還是「投射威脅／承擔」）
- 相關：E-048、R-017
- 來源：reports/ovr-v62-3pt-difficulty-2025-26/

### E-057
- 日期：2026-10-28
- 內容：`card 0.1.1+E057` 三分價值（預註冊，公式在派工前凍結）：卡片顯示的 3PT 與 OVR 改用新屬性 `threeValue`，模擬用的 `long` 不動（模擬已用 `shotProfile.threeRate` 決定出手量，`long` 混入出手量會重複計算）。
- 設定：準度 acc = v62 方法 (c) 的 abilityC（2025-26 全季、依出手類型調整難度、k=294.667，`reports/ovr-v62-3pt-difficulty-2025-26/new-long.json`）；出手量 vol = v62 `Ds.feat('r36')`（每 36 分鐘 3PA，含偽分鐘拉回）；替補水準 rep = 聯盟三分命中率 mu − 0.03；value = vol × (acc − rep)；`threeValue` = value 在 MIN≥500 池內的百分位，套用卡片既有的 `attr()`（40–99）。基準卡 = card 0.1.1（`reports/ovr-v61-shrink-history-2025-26/ranking.csv`）。主要版本：OVR 迴歸裡用 `threeValue` 取代 `long`；次要版本（參考）：兩者並列。rep ±0.02 只當敏感度參考，不得用來挑版本（L-026）。
- 驗收（事先訂定）：(1) Curry、Edwards、Knueppel、LaMelo 在 MIN≥500 池的 threeValue 名次都 ≤15；(2) Portis 的名次比基準卡 `long` 名次後退（不設門檻，R-020）；(3) 主要版本 OVR 對 2K27 的 Spearman 高於基準 0.5092（樣本外，決定 MINOR 或 PATCH，R-019）；(4) 前十長人門檻與 evaluate.mjs 其他門檻不比基準差；(5) `npm test` 過。
- 結果：App 內 sonnet 子代理執行；lead 抽查 evaluation.json 與 ranking.csv 數字相符。驗收 5 項過 3 項：(1) 過，threeValue 池內 Curry 1、Knueppel 2–3（同分排序差異）、Edwards 7、LaMelo 10；(2) 過，Portis long 第 2 → threeValue 第 18（Kennard 1→25）；(3) 未過，主要版本（取代 long）2K27 ρ 0.4956 < 0.5092；(4) 未過，noMobleyTop10 失敗（Mobley 進 OVR 第 10，前十長人 4→5 人），其餘 18 門檻持平；(5) 過，npm test 57/0。次要版本（並列）2K27 ρ 0.5175、19/19 門檻，但它是看結果前就標為參考的版本，不能事後改當主要版本（L-026）。RAPM ρ 0.8785／0.8684 為樣本內。對照重跑 v61 位元組相同（sanity-v61-repro/）。
- 狀態：不採用進 OVR（2026-10-28，主要版本驗收未過）；threeValue 本身可作為顯示用屬性，並列版需另行預註冊樣本外檢驗
- 相關：E-056、R-017、R-019、R-020
- 來源：使用者 2026-10-28

### E-058
- 日期：2026-10-28
- 內容：`card 0.1.1+E058` 單防／協防拉回（預註冊）：`onBall`（最近防守者時對手三分命中率差，`leaguedashptdefend` 3 Pointers）與 `help`（6 呎內）現在用 k=200 往 0 拉回（`scripts/.seventh-base-2025-26-25.js:24`），雜訊太大。例：Luka 128 次被防三分、對手低 4.8 pp（約 1.1 個抽樣標準差；更正：正式卡是全季 418 次、約 2 個標準差，見 L-029）→ onBall 83、全聯盟第 9；他的 pooledD 是 478 人第 246。
- 設定：方法 (a) 現行 k=200 往 0；(b) 往 0、k 用擬合季最大概似估計；(c) 往本人前兩季（衰減 λ 擬合或固定 0.5，二選一寫明）、k 與 kh 擬合；(d) 先驗中心 = 本人前一季以前的 pooledD 換算值、k 擬合（會汙染 RAPM ρ，只看 2K27 ρ）。擬合季 2023-24、2024-25：每隊第 41 場前預測之後的對手命中率（按被防出手數加權的 log-likelihood）；測試季 2025-26 同切法。選擇規則：擬合季分數最好者勝，與更簡單的方法差距 < 0.5% 相對 log-lik 時選簡單的（a<b<c<d）。只用一次測試季，不得看測試季再換方法（L-026）。卡片用 2025-26 全季（正式卡的窗，`scripts/build_season_league.js:100-106`，輸入 `data/benchmark-source/defense-long.json`／`defense-rim.json`）＋勝出方法重算 onBall／help，基準卡 = card 0.1.1。（2026-10-28 更正：原寫「前 25 場」是 lead 把回測卡 `.seventh-base-2025-26-25.js` 誤當正式卡，見 L-029；回測設計不變。）另附參考表：Luka 與 pooledD 前 15 名的 FREQ（被防三分出手佔對手三分出手比）對同位置隊友，只作參考，不進驗收。
- 驗收（事先訂定）：(1) 勝出方法在測試季的加權 log-lik 優於 (a)，附 bootstrap 90% 區間；(2) OVR 對 2K27 Spearman 不低於基準 0.5092 − 0.005；高於 0.5092 才算變準（R-019）；(3) evaluate.mjs 其他門檻不比基準差；(4) 直覺抽查：Luka onBall 池內（MIN≥500）名次 > 30；(5) `npm test` 過。
- 結果（2026-10-28，`reports/card-0.1.1+E058-defense-shrink/`，lead 已核對 evaluation.json、fit_results.json）：擬合季 log-lik 合計 (a) −1.31526、(b) −1.31462（long k≈2081／short k≈98）、(c) −1.31415（λ=0.5 固定；long k≈2195 kh≈1618、short k≈147 kh≈155）；(d) 不可用（rapm.csv 沒有逐季窗）。依選擇規則差距 < 0.5% → 主勝出 (a)＝現行，驗收 (1)(4) 不過。備選 (c) 測試季勝過 (a) +0.00128 [0.00098, 0.00160]，主要來自 rim；2K27 ρ 0.5007（不過 (2)），RAPM ρ 0.8697（樣本內），19/19 閘，Luka onBall 9→39。關鍵發現：三分區測試季所有方法都不贏「人人聯盟平均」（null），(c) 只是輸得最少 → 對手三分命中差幾乎沒有可預測的個人成分。偏離：2023-24 只有前一季歷史（沒抓 2021-22）；FREQ 用 NBA 定義（被防出手中 3PA 比例），無隊內對手 3PA 總數。
- 狀態：不採用（2026-10-28，主勝出＝現行、備選 (c) 2K27 ρ 未過）；選擇規則的 0.5% 門檻設計有誤，見 L-030
- 相關：E-055、R-019
- 來源：使用者 2026-10-28

### E-059
- 日期：2026-10-28
- 內容：`card 0.1.1+E059` onBall 改成看可延續的行為（預註冊）：E-058 顯示對手三分命中差在測試季沒有任何方法贏過「人人聯盟平均」，現行 onBall 基本是雜訊。改用 defense-tenth step4-t2 的建議：三分干擾／36（換隊相鄰季 r 0.72）、對位負擔（PARTIAL_POSS 加權對手 USG，r 0.65），加上使用者提的「被針對程度」（對手透過對位選擇打他的程度）。help 不動。
- 設定：資料用 `reports/defense-tenth/step4-t2/raw/<season>/`（hustle、matchups，四季全季，已有 sha256）。三個分量：(i) C3＝CONTESTED_SHOTS_3PT/36，往同位置組（G／F／C，取主位置）平均拉回、k=500 分鐘；(ii) B＝對位負擔，往全聯盟平均拉回、k=1000 PARTIAL_POSS；(iii) T＝被針對＝對位 FGA／100 PARTIAL_POSS 減同位置組平均，k=1000 拉回，越高越差。T 先過穩定性門檻才納入：只用擬合季（2022-23→2023-24、2023-24→2024-25 相鄰季，兩季各 ≥500 分鐘）r ≥ 0.5，不過就丟掉、不再找替代。合成：onBall_z＝z(C3, 同位置組內)＋z(B)－z(T)（T 不過時只用前兩項），等權、不擬合權重；再用正式卡同一個百分位池與 attr() 對應到 40–99。卡片窗＝2025-26 全季（`scripts/build_season_league.js`），基準卡＝card 0.1.1，OVR 依 v61 流程重擬。只改卡片，模擬端 onBall 語意另列 TODO。
- 驗收（事先訂定）：(0) 新 onBall 在擬合季的相鄰季 r ≥ 0.5（同時列舊 onBall 的 r 對照），不過就停，不建卡；(1) OVR 對 2K27 Spearman ≥ 0.5092 − 0.005；高於 0.5092 才算變準（R-019）；(2) evaluate.mjs 其他門檻不比基準差（基準 19/19）；(3) 直覺抽查：Luka onBall 池內（MIN≥500）名次 > 30；(4) `npm test` 過。另列參考（不進驗收）：onBall 新舊前 15、pooledD 前 15 的新名次、OVR 前 20 差異、RAPM 樣本內 ρ。只看一次 2025-26，不得看結果再改分量、k 或權重（L-026）。
- 結果（2026-10-28，`reports/card-0.1.1+E059-onball-contest/`，lead 已核對 evaluation.json、stability.json，並自己重做 2K27 ρ 配對 bootstrap）：(0) 新 onBall 相鄰季 r 0.770／0.746（舊 onBall 0.067／0.105）；T 的 r 0.822／0.790，納入。(1) 2K27 ρ 0.5124（基準 0.5092，+0.0032；lead 配對 bootstrap 2000 次 90% 區間 [−0.0036, +0.0106]，P(差≤0)=0.22，在雜訊內）。(2) 19/19（bigPass 14/16，基準 15/16）。(3) Luka onBall 9→269。(4) npm test 57 過。不換 onBall 的重跑與 v61 byte-identical。樣本內 RAPM ρ 0.8657（基準 0.8685）。抽查問題：Wembanyama onBall 14→373（分在 F 組；T 的 z +3.26。原先 lead 說是「協防出手被算進對位」，查欄位後更正：matchups 有獨立的 HELP_FGA，MATCHUP_FGA 不含協防；真正原因是他被列 F 卻守中鋒，T 拿 F 組平均 20.3 比，而他守的中鋒本來就每回合出手多，C 組平均 26.5，他 27.2），Embiid 186→339、Gobert 215→312；外線防守者 Caruso 254→20、Herbert Jones 113→5、Ausar Thompson 214→6、Dyson Daniels 第 2。偏離 10 點見 report.md（位置取 PLAYER_POSITION 首字母、7 人缺分量給 70 等）。
- 狀態：預註冊驗收全過（2026-10-28）；+0.0032 是否算 R-019 的「變準」與 Wembanyama 的 T 問題，待使用者裁定
- 相關：E-058、R-019、L-029、L-030
- 來源：使用者 2026-10-28 GO

### E-060
- 日期：2026-10-28
- 內容：`card 0.1.1+E060` 修正 E-059 的「被針對」T（預註冊）。E-059 的 T＝對位 FGA／100 回合減同位置組平均，位置組錯置時會誤判：Wembanyama 被列 F 卻守中鋒，onBall 14→373。改成和位置無關的定義：T＝實際對位 FGA 減「這些對手平常的出手率」預期值，也就是對手在他面前是不是比平常更愛出手。
- 設定：沿用 E-059 的資料、C3、B、合成方式（z(C3)＋z(B)－z(T)）、k、百分位池與 attr()，只換 T。對每位防守者 d：預期 FGA＝Σ_o PARTIAL_POSS(d,o)×r_o；r_o＝進攻者 o 當季所有對位的 ΣMATCHUP_FGA／ΣPARTIAL_POSS，計算時排除 d 自己的那幾列（leave-one-out）。T_raw＝100×(實際 FGA－預期 FGA)／ΣPARTIAL_POSS(d)，往 0 拉回，k=1000 回合；z 的母體＝當季 MIN≥500。T 照樣先過擬合季相鄰季 r ≥ 0.5 才納入，不過就只用 z(C3)＋z(B)。lead 預註冊前已看過 E-059 的 Wembanyama 數字，所以下面 (5) 屬於看過問題才設的抽查，只當必要條件，不當變準的證據。
- 驗收（事先訂定）：(0) 新 onBall 擬合季相鄰季 r ≥ 0.5；(1) 2K27 ρ ≥ 0.5092 − 0.005；「變準」要對基準 card 0.1.1 做配對 bootstrap（2000 次、以球員重抽），90% 區間下界 > 0 才算（L-031）；(2) evaluate.mjs 其他門檻不比基準差（19/19）；(3) Luka onBall 池內（MIN≥500）名次 > 30；(4) `npm test` 過；(5) Wembanyama、Gobert、Embiid 的 onBall 池內名次都 ≤ 200。另列參考：與 E-059 並排的 onBall 前 15、pooledD 前 15、OVR 前 20 差異。只看一次 2025-26，不得看結果再改（L-026）。
- 結果（`reports/card-0.1.1+E060-onball-targeting/`，lead 已核對 evaluation.json、bootstrap.json）：(0) 過，新 onBall 相鄰季 r 0.808／0.785，T r 0.905／0.884；(1) 過，2K27 ρ 0.5181，差 +0.0089，bootstrap 90% 區間 [+0.0003, +0.0181]，P(差≤0)=0.045，按 L-031 算「變準」但很勉強；(2) 過，19/19；(3) 過，Luka onBall 9→276；(4) 過；(5) **不過**：Wembanyama 344、Gobert 356、Embiid 368（zT 各 +2.54、+2.12、+1.33），Holmgren 63→332、Brook Lopez 141→371。OVR：Luka 3→8、Kawhi 10→4、Wembanyama 維持 5。v61 重現逐位元相同。
- 診斷（lead 事後看，不算證據）：長人的超額出手主要來自守其他長人：Wembanyama 對 Draymond Green 106 回合 33 次出手（平常 13/100）、Nurkić 103 回合 28 次（平常 15/100）、Adebayo 60 回合 25 次。長人在籃下對位，對手的補籃與禁區出手都記在他頭上；對手的「平常出手率」大多是被外線防守者守時量到的，所以長人永遠顯得「被針對」。Caruso 則是 −3.5/100。T 這個概念對外線有用，對內線是結構偏差，不是能力。
- 狀態：不採用（2026-10-28，預註冊驗收 (5) 不過）→ 採用（2026-10-28，使用者裁定 (5) 與 onBall 定義矛盾，見 R-022）
- 相關：E-059、L-031、R-019
- 來源：使用者 2026-10-28「先修長人」

### E-061
- 日期：2026-10-28
- 內容：`card 0.1.1+E061` 被針對的 T 只看三分出手（預註冊）。E-060 的 T 算全部出手，長人守長人時對手籃下補籃、禁區出手多，造成結構偏差（Wembanyama 344、Gobert 356）。改成只問「對手在他面前是不是比平常更愛投三分」，衡量外線被針對的程度，籃下出手不計入。
- 設定：除了 T 以外，全部沿用 E-060（資料、C3、B、合成 z(C3)＋z(B)－z(T)、k、百分位池、attr()、leave-one-out）。T3：預期 3PA＝Σ_o PARTIAL_POSS(d,o)×r3_o；r3_o＝進攻者 o 當季所有對位的 ΣMATCHUP_FG3A／ΣPARTIAL_POSS，排除 d 自己的那幾列。T3_raw＝100×(實際 MATCHUP_FG3A－預期)／ΣPARTIAL_POSS(d)，往 0 拉回，k=1000 回合；z 的母體＝當季 MIN≥500。T3 先過擬合季相鄰季 r ≥ 0.5 才納入，不過就只用 z(C3)＋z(B)。lead 預註冊前看過 E-060 長人的全出手分解，沒看過任何人的三分版 T。這是同一問題的第三次嘗試（E-059、E-060、E-061），所以 (1) 的「變準」就算達標，也只記錄、不當 MINOR 的依據，要等另一個樣本外檢驗。
- 驗收（事先訂定）：(0) 新 onBall 擬合季相鄰季 r ≥ 0.5；(1) 2K27 ρ ≥ 0.5092 − 0.005；「變準」以基準 card 0.1.1 做配對 bootstrap（2000 次、以球員重抽、seed 1），90% 區間下界 > 0；同時列出對 E-060 的配對差，只參考；(2) evaluate.mjs 19/19；(3) Luka onBall 池內（MIN≥500）名次 > 30；(4) `npm test` 過；(5) Wembanyama、Gobert、Embiid 的 onBall 池內名次都 ≤ 200（必要條件，看過問題才設）。另列參考：Holmgren、Brook Lopez、Jarrett Allen、Bam Adebayo 名次；和 E-059、E-060 並排的 onBall 前 15、OVR 前 20 差異。只看一次 2025-26，不得看結果再改（L-026）。
- 結果（`reports/card-0.1.1+E061-onball-3pt-targeting/`，lead 已核對 evaluation.json、bootstrap.json）：(0) 過，新 onBall 相鄰季 r 0.799／0.810，T3 r 0.836／0.806（納入）；(1) ρ 門檻過，2K27 ρ 0.5143（+0.0050），但「變準」不過：90% 區間 [−0.0022, +0.0123]，P=0.128；對 E-060 差 −0.0039 [−0.0075, −0.0004]，比 E-060 差；(2) 19/19（bigPass 14/16，基準 15/16）；(3) 過，Luka 9→316；(4) 過；(5) **不過**：Wembanyama 369、Gobert 326、Embiid 361（Wembanyama zT3 +3.24）。Holmgren 299、Brook Lopez 366、Jarrett Allen 357、Adebayo 263。OVR 前 20 名單和 E-060 相同；Luka OVR 回到 3、Wembanyama 5→8。v61 重現逐位元相同。
- 診斷（事後，不算證據）：長人守禁區，對手就改投外線，三分版 T 一樣把「站在籃下」當成「被針對」。E-059～E-061 三版 T 都讓長人掉到 300 名後，問題不在 T 的細節，而是外線單防指標本來就不適用於守禁區的人。
- 狀態：不採用（2026-10-28，預註冊驗收 (5) 與「變準」不過）
- 相關：E-059、E-060、L-026、L-031、R-019
- 來源：使用者 2026-10-28「預註冊 E-061」

### E-062
- 日期：2026-10-28
- 內容：`inseason 0.1.0+E062` 投籃類視窗觀測值的虛擬出手改以球員自己為中心（預註冊）。現行 `shooting()` 先加 100 次聯盟平均虛擬出手，C4 再往 x0 收縮，小樣本時好射手必降（Maxey FT 24/28 → y 71.5、x0 90.9）。
- 設定：`reports/ovr-inseason-2026-27/v5/pathA/preregistration-e062-shooting-center.md`（凍結）。候選 C4s（中心＝forward(x0)、m0=100）、C4r（m0=0）；其他沿用 E-033，δ² 與 c 照凍結程序重估。主判定 Y5、Y6，N=3/5/10/20；(0) 重現 E-033、(1) V1∧V2、(2) 每格 MAE 差 ≤ +0.05、(3) 合併 MAE 差 bootstrap 90% 上界 < 0 才算變準。
- 結果（`reports/ovr-inseason-2026-27/v5/pathA/backtest-e062/`，lead 已核對 verdict.json 與 results.csv）：(0) 過，開關關掉時 results.csv 與 E-033 逐位元相同；(1) 兩候選都過；(2) 兩候選都不過，Y6 全面變差：C4／C4s／C4r MAE Y6 N10 5.589／5.886／5.885、N20 5.147／5.452／5.481（Y5 小幅改善，N20 C4r 5.578）；(3) 合併差 C4s +0.0845 [+0.0104, +0.1633]（顯著變差）、C4r +0.0483 [−0.0287, +0.1294]。重估 c：C4s Y3–Y5 0.7、Y6 0.35；C4r 1.4（D 組 2）。三分位：Y6 高組 C4 本來就高估（+3.22／+2.69），C4s 推到 +3.75／+3.46 → 賽中「好射手偏低」有一大部分是真實的回歸平均，雙重收縮在預測整季卡上是有益的。賽中參考重算（`live/2026-10-27-e062/`，未部署）：C4s 對現行 ΔOVR ≤−1 0 人、≥+1 7 人；Maxey 79.0→80.1、Jerome 80.0→81.3、Kessler 78.6→78.4。偏離預註冊（已揭露）：開關實際裝在 `v4/tools/inseason_common_v4.window_cards`；δ² 由先驗卡→答案卡算、不用視窗 y，所以三版 δ² 相同、只有 c 重估；bootstrap 以每起點重抽球員、8 格等權平均。注意本 ID 與下方「模擬改吃 E-060 onBall」撞號。
- 狀態：不採用（2026-10-28，閘門 (2)(3) 不過；上線維持 C4）
- 相關：E-033、R-009、L-026、L-031、L-032
- 來源：使用者 2026-10-28「預註冊回測」

### E-063
- 日期：2026-10-28
- 內容：（原登記為 E-062，與上方賽中投籃 E-062 撞號，2026-10-28 改號；報告目錄仍為 `reports/player-impact-e062-team/`）模擬改吃 E-060 的 onBall（預註冊）。卡片 v55～0.1.1 一直只改顯示用 OVR，模擬讀的 `data/season-league.json` 還是 v53 時代的 onBall（對手三分命中差）。這次只換 onBall，其他屬性與引擎不動，量球隊準度。
- 設定：沿用 `reports/player-impact-v54-team/` 的整季球隊流程（v47 協定、v53 引擎、壓迫係數、spread scale 1、seed 20261012／13／14、四季 2022-23～2025-26）。在 loadInput 之後把每季名單球員的 onBall 換成該季的 E-060 onBall：attr(percentile(zC3+zB−zT, 該季卡片池))，分量用 `reports/card-0.1.1+E060-onball-targeting/components-<season>.csv`，卡片池定義同 build_card.py（GP≥30 且 MIN/GP≥20，用該季 base）。缺分量的人 onBall 不變（保留原值，不給 70）。基準＝`reports/player-impact-v53-team/runs`（不重跑；另抽一個 v53 run 重跑，需逐位元相同）。
- 驗收（事先訂定）：(1) `npm test` 過；(2) 主指標＝四季合併 winsMAE 差（E062−v53）：每季每 seed 配對，以球隊在季內重抽做 bootstrap（2000 次、seed 1）。90% 區間上界 ≤ +0.25 勝 → 「不比基準差」，接進模擬（PATCH）；區間上界 < 0 → 「變準」，MINOR 候選（R-019）；上界 > +0.25 → 不接；(3) 每季聯盟三分%差 ≤ 0.5 個百分點、每場得分差 ≤ 1.0，否則不接；(4) 2025-26 單季與 netRMSE 另列參考。只跑一次，不得看結果再改（L-026）。
- 接進模擬的做法（驗收過才做）：`scripts/build_season_league.js` 的 onBall 改讀 E-060 2025-26 onBall 的資料檔，重產 `data/season-league.json`，確認和舊檔只差 onBall 欄。
- 結果（`reports/player-impact-e062-team/`，App 內 sonnet 子代理在 5090 執行；lead 核對 scores.json 與 13 個 run 檔）：(1) 過，57/0（未改 src）；(2) 不過，合併 winsMAE 差 +0.378 [−0.053, +0.831]，上界 > +0.25 → 不接；各季 +0.51／+0.69／−0.67／+0.98，netRMSE 四季都變差；(3) 不過，聯盟三分% 四季都高 0.62–0.86 pp（得分差 0.44–0.82 在門檻內）。新 onBall 讓整體外線防守變弱（全聯盟三分% 約 +0.7 pp）。v53 重跑 1 個 run 逐位元相同。偏離（已揭露）：2022-23～2024-25 無 base 檔，卡片池改用 defense-tenth step4-t2 的 advanced 檔 GP／MIN；`freshDefenseMeasurement.sourceOnBall` 未換；5090 環境 `basketball-e062-20261028` 換成本機 src。
- 狀態：不接進模擬（2026-10-28，驗收 (2)(3) 不過）；卡片顯示仍用 E-060 onBall（R-022），模擬維持 v53 onBall
- 相關：E-060、R-019、R-022
- 來源：使用者 2026-10-28「接進模擬並發版」

### E-064
- 日期：2026-10-28
- 內容：`card 0.1.2+E064`／`inseason 0.1.1+E064` OVR 改為每場影響力、含上場時間（預註冊，R-025、R-026）。每 36 的 pred 乘 MPG/36，再用每場錨點（MIN≥500 池 PR1/50/99）映射；基準＝聯盟平均，另列替補水準（PR10）副版。賽中 MPG 用 stamina 的 C4 權重 w 更新。
- 設定：`reports/card-0.1.2+E064-pergame/preregistration.md`（凍結，sha256 c86a2811f57d0ddd34d2dd0ee1b024181e79f4ea1af5973a95697d089dc93985）。卡片：(c0) 重現 0.1.2、(c1) npm test、(c2) RAPM 分半 A→B／B→A，答案＝RAPM_另一半 × MPG_另一半（2025-26 依 gameId 奇偶），ρ(OVR_game)−ρ(OVR_36) 90% 下界 > 0、(c3) ρ(OVR_game)−ρ(MPG) 下界 > 0。賽中：候選 G1（最低樣本 1 場，主）／G5（5 場）／G0（不更新），Y5、Y6 × N=3/5/10/20 對每場答案卡；(0) 重現 E-033、(1) V1∧V2、(2) G1 對 G0 每格 ≤ +0.05、(3) 合併 bootstrap 90% 上界 < 0。
- 結果（App 內 sonnet 子代理執行；lead 核對 verdict.json，並自己從 fitA／fitB pergame-main.csv＋rapm-A/B＋mpg-A/B 重算 ρ，兩方向 game−36 差 +0.0096／+0.0118，對自報 +0.0099／+0.0118）：
  - 卡片端 `reports/card-0.1.2+E064-pergame/` 全過：(c0) ranking.csv sha256 與 0.1.2 相同；(c1) 57/0；(c2) ρ 0.5953 對 0.5844，差 +0.0109 [+0.0011, +0.0205]（勉強過）；(c3) 對 MPG 0.4012 差 +0.1941 [+0.1300, +0.2618]。
  - 卡片端只報告：替補水準副版 ρ 0.6025，對主版差 +0.0072 [−0.0143, +0.0278]（不顯著）；2K27 ρ 主版 0.444、副版 0.695、每 36 0.518、MPG 單獨 0.798。反轉診斷：MIN≥500 池裡 MPG≥20 的人有 77 位低於 MPG<12 組中位數（副版 27 位）。Jerome #47→#64（2025-26 MPG 22.6）、Maxey #70→#44、Kessler #104→#80；前十長人仍 4 位。
  - 賽中端 `v5/pathA/backtest-e064/`：(0) 過（4 位小數逐格相同）；(2)(3) G1、G5 都過，G1 對 G0 合併 −0.314 [上界 −0.182]、G1 對 G5 −0.114 [上界 −0.060]；(1) 三者都不過：G1 V1 N=3 U 0.592（>0.50）、Y5 T_s 0.429，V2 Y5 N10 >10 人數 54 對 A 52；G5 只輸 V2 Y5 N10（54 對 52）；G0 同格 56 對 52 也不過。依凍結規則採 G0（只換單位、不更新上場時間）；退路 G0 本身沒過 (1)，規則沒要求，見 L-035。
  - 賽中參考 `live/2026-10-28-e064/`（G0，未部署；`run_c4_live.py` 加 `E064_MODE`，預設關時與 2026-10-27 頁面逐位元相同）：ΔOVR ≤−1 125 人、≥+1 72 人；Jerome 83.4→79.3、Maxey 79.8→81.4、Kessler 74.6→74.3；Caruso 98.3→85.9；低分鐘新人被拉向 70（Lanier 42.4→59.5、Bronny 40.6→57.0），是平均基準的副作用。
  - 偏離（已揭露 20 條，重點）：賽中錨點池用 3 位小數 predictedPer36；live 的凍結摘要已是 card 0.1.2（另一 session 的 37f7d62，inseason 0.1.2），所以 live 錨點用卡片端主版錨點；子代理沒寫 report.md，內容只在 verdict.json 與回報。
- 狀態：卡片端過關、賽中依規則採 G0（2026-10-29）。2026-10-29 使用者裁定 R-028：改採副版基準＋賽中 G1，版本 card／inseason 0.2.0。2026-10-29 已上線：gh-pages 2870ddb（首頁 inseason 0.2.0a、2025-26.html card 0.2.0），產物 `reports/card-0.2.0/`；lead 抓線上頁核對版號、Jerome 85.4（MPG_hat 29.4）、Maxey 86.9、Caruso 82.3、Jokić 108.4；對前一版 0.1.2a ΔOVR ≤−1 199 人、≥+1 119 人、|Δ|≥5 106 人
- 相關：R-025、R-026、F-029、E-033、E-060、E-062、E-065、L-026、L-031、L-035
- 來源：使用者 2026-10-28「每場，含上場時間」

### E-065
- 日期：2026-10-28
- 內容：OVR 對 R-025 定義的進出勝場測試。模擬器照字面量「球員打 2025-26 場均分鐘＋四個聯盟平均隊友」對「同分鐘換成平均 profile」的每場勝場差（WinImp），對照 card 0.1.2 OVR；另檢驗 defenseBonus 是否高估（White 99.0、Caruso pred0 −0.31＋defenseBonus 3.86→98.9）。
- 設定：`reports/card-0.1.2+E065-inout-wins/preregistration.md`（凍結，sha256 01ff0b679cde0c6fc935f79ab4f11f64697f4b1876bebc5495d99c65eaa68b5e，git HEAD 37f7d62）。答案沿用 E-064 §3.2（RAPM 分半 pooledNet × MPG 另一半，pooledPoss≥2500、兩半各 ≥5 場）。V1：ρ(WinImp)−ρ(OVR) bootstrap 90% 下界 > −0.02 不輸、> 0 較好；V2：前 60 名 defenseBonus≥1 組名次殘差 90% 下界 > 0 → 高估。示範（不作判準）：BOS 拿掉 White、White 加入中位數球隊，對照 Luka／Wemby／Caruso。
- 結果（2026-10-29，lead 自算 `verdict_e065.py` → `verdict.json`；WinImp 由 sonnet 子代理在 5090 跑，baseSeed 20261028、30 對手 × 16 樣本 × 2 邊、379 人，HEAD b660a02，src 與 37f7d62 相同）：
  - V1 不過：ρ(WinImp) 0.414／0.351 對 ρ(OVR 0.1.2) 0.759／0.765（AB n=345／BA n=344），差 −0.345 [−0.421, −0.268]／−0.414 [−0.488, −0.335]。定義版明顯比現行卡差。
  - V2 字面通過：defenseBonus≥1 組殘差 +27.0 [14.4, 39.8]／+19.0 [10.0, 28.5]；但 <1 組也是 +15.7／+16.0（前 60 名整體回歸平均），高減低只有約 +11／+3，預註冊沒設對照，不能算「defenseBonus 高估」的證據。
  - 比較對象有洩漏：OVR 0.1.2 的 align／defenseBonus 用全季 RAPM，對分半答案是樣本內。事後（探索性，不作判準）改用 E-064 fitA／fitB（只用一半 RAPM 擬合的卡）：ρ 0.584／0.596，WinImp 仍輸（差 90% CI [−0.254, −0.083]／[−0.320, −0.162]）；屬性 pred0×MPG 0.534／0.504 也贏 WinImp。fit 卡前 60 名高減低 CI [1.8, 61.6]／[−2.0, 60.2]，方向一致但一邊未過 0。
  - 個人：White 樣本外不被高估（fit 卡池內第 6.5，答案第 4／第 6）；Kenrich 兩方向都高估（fit 71→答案 112、47→109）；Caruso 只有 AB 高估（2.5→116），BA 反而低估（85.5→15）。
  - WinImp 本身：前五 Jokić 16.6、SGA 15.5、Wemby 15.1、Giannis 11.6、Gobert 10.5；White 第 29（6.6±2.6）、Caruso 第 163；偏好長人（Mark Williams OVR 457→WinImp 13、Sengun 241→15）；ρ(WinImp, OVR)=0.543。
  - 示範：White 拿掉 BOS −0.6±1.7 勝、加入中位數隊 PHX +3.1；Luka −6.9／+7.1；Wemby −10.1／+13.0；Caruso +1.0／−0.5（拿掉與加入不對稱，示範只作參考）。
  - 位置版（副表，2026-10-29 事後補記，探索性）：主版四個隊友是同一個全聯盟平均人（不分位置，缺控衛與內線）；位置版隊友＝PG/SG/SF/PF/C 各位置平均 profile（`winimp-core.mjs` variant 'pos'，沿用 v53 workloadTeam）。位置版 ρ 0.291／0.317，比主版 0.414／0.351 更差。主版長人偏差部分來自缺內線：Sengun 8.2→1.3、Mark Williams 8.5→4.4；但位置版仍高估護框長人（Mitchell Robinson OVR 115→第 8、Kalkbrenner 384→第 12）。White 位置版只有 0.6 勝（主版 6.6）。兩種隊友都是「位置平均」，不是使用者說的「各司其職、OVR 70」基準；要測後者需另設計基準陣容。
  - 結論：模擬器照 R-025 字面做的勝場貢獻目前預測力比卡片差、且有長人偏差；在模擬器修好前不能拿來當 OVR。defenseBonus 高估只在個人層看得到（Kenrich、Caruso 單向），群體層證據不足。
- 狀態：完成（H1 否定；H2 未確立）
- 相關：R-025、R-026、F-029、E-064、E-027、L-026、R-007、L-036
- 來源：使用者 2026-10-28「OVR99的球員要有這個強度」「GO」

### E-066
- 日期：2026-10-29
- 內容：卡片能力值兩題合併預註冊（R-029、R-030）。A：同季上半季逐場依日期指數衰減加權（H＝∞／60／30 天），處理 McCain 型季中變化；B：E-055 收縮目標 m 改成依 MPG 分組（<12、12–20、20–28、≥28）的條件平均（B1 本組、B2 一律 MPG<12 組＝往聯盟底層拉），沒有歷史與 drive 缺值的退回值也跟著換。
- 設定：`reports/card-0.2.0+E066-recency-target/preregistration.md`（凍結，sha256 6f940f553fd4dcb13d9d89a4145c5d71de8bfe0025b55c2093bbce3cbdf1747c）。沿用 E-055 回測（前季＋上半季→下半季、MIN_D2、測試 2025-26），候選只用擬合季選、測試季判一次。A：合併相對 MAE 90% 上界 < 0 且每屬性 ≤ +1%；B：無歷史族群合併相對 MAE 90% 上界 < 0、全體 ≤ +0.5%。卡片層 (c0) 重現 card 0.2.0、(c1) npm test、(c2) E-064 RAPM 分半每場 ρ 差 90% 下界 > −0.02、(c3) evaluate 閘數不減；G5 名單含 Topić、McCain、雷霆輪替。
- 結果：兩題都不過，卡片維持 card 0.2.0（`report.md`；role-audit 獨立重算 `audit/audit.md` 結論成立）。
  - A：擬合季選 H\*=60（只好 −0.17%）；測試季 (A1) 合併相對 MAE −0.10%，90% [−0.58%, +0.40%]，不過；(A2) 每屬性 ≤ +0.82%，過。只報告：季對季中途換隊者五項平均好 1.1%、未換隊者差 0.6%；測試季上半季僅 6 人換隊，驗不出交易後加權。
  - B：擬合季 B1 +0.72%、B2 +2.39%，兩個都比現行差，依字面選 B1；(B1) 無歷史族群 mid 15 人、drive 20 人 <30，樣本不足（只報告 +6.6%，變差）；(B2) 全體 +1.98%，90% [+0.77%, +3.23%]，不過。未選的 B2 全體 +3.58%。
  - 卡片層沒做；(c0) 只做回測層重現（開關全關對 `backtest.json` 全同），卡片層 ranking.csv 未驗。
  - audit：點估計獨立吻合；e066 對歷史季上半季也加權（預註冊沒寫），改成只加權當季，A1 上界 +0.0044，判定不變。程序上沒有看測試季後改參數的跡象（L-026）。
- 狀態：完成（不採用，2026-10-29）
- 相關：R-029、R-030、E-055、E-064、L-026、L-037
- 來源：使用者 2026-10-29「寫預註冊」

### E-067
- 日期：2026-10-29
- 內容：長人偏袒檢查的固定量尺。之後卡片或模擬每個版本都用同一支腳本、同一判準。S＝mean(殘差|C) − mean(殘差|PG/SG)，殘差＝答案名次 − 模型名次（正＝高估），答案與人群同 E-064 §3.2；兩方向 90% 下界都 > 0 → 偏袒長人。模擬改版宣稱修掉長人偏袒，須 (b1) 判定不再是偏袒長人、(b2) 兩方向 S 都變小、(b3) WinImp ρ 兩方向平均掉不超過 0.02。
- 設定：`reports/bias-check-E067/preregistration.md`（凍結，sha256 2dc539163a49db8d2d9191ca75f854344cae0fd8427dc698d29794bd6383177d），腳本 `bias_check.py` → `baseline.json`。卡片一律用半季擬合卡（L-036）。
- 結果（基準線，lead 自算）：
  - card 0.1.2 fit 卡：未偵測到偏袒。S +3.0 [−17.6, 23.9]／+13.1 [−7.3, 33.3]；前 20 名 C 的人數：模型 4/3，答案 4。
  - WinImp 主版：偏袒長人。S +81.8 [59.9, 104.3]／+95.2 [71.1, 119.2]；C 組平均高估約 +75 名；前 20 名 C 的人數：模型 11，答案 4。
  - WinImp 位置版：偏袒長人。S +37.5 [9.9, 65.5]／+50.1 [22.5, 77.4]；另外 PG 組大幅低估（−72／−66），等於五個位置平均隊友裡已經有控衛，候選 PG 的邊際價值被壓低。
  - 第二答案 2K27（只列）：三個模型的 S 都更大（fit 卡 +22.6／+17.2，區間含 0），RAPM 答案沒有比 2K27 更偏愛長人。
- 狀態：完成（量尺凍結；模擬改版的驗收目標＝把 WinImp 主版／位置版的 S 壓下來）
- 相關：E-065、E-064、L-036、L-026、R-025
- 來源：使用者 2026-10-29「照這個順序」


### E-068
- 日期：2026-10-29
- 內容：製造犯規（FD）定義比較，探索性、事後（使用者看到 SGA 不在 FD 榜前段才提出），不作採用依據（R-007、L-026）。候選：rate＝FTA/FGA（現行）、vol＝FTA/36、mix＝0.5·z(rate)＋0.5·z(vol)，都取池內百分位（GP≥30 且 MPG≥20，1–99），原始值、未做 v61 歷史拉回。
- 設定：`reports/fd-volume-compare-2025-26/compare_fd.py` → `results.json`、`report.md`。價值檢驗：FD 只用一半比賽（gameId 偶／奇，同 RAPM 分半），答案＝另一半 RAPM pooledNet（pooledPoss≥2500 且在池內，n 242／241），OLS 控制 card 0.2.0 其他 14 屬性（全季值，三候選共用）。
- 結果（lead 自算）：
  - 排行：SGA rate 第 55、vol 第 8、mix 第 17；Luka 59／5／18、Embiid 51／6／14；Gobert 18／103／32、Adams 24／148／46。vol 前 15 名幾乎都是持球主攻，rate 前 15 名多是長人與低出手量的人。池內 Spearman rate~vol 0.868。
  - 穩定度（2024-25→2025-26，n 178）：rate Spearman 0.832、vol 0.844、mix 0.840，差不多。
  - 價值：三個候選都沒有可分辨的增量價值。FD_A→RAPM_B 係數／10 點 rate −0.029（SE 0.052）、vol −0.064（0.065）、mix −0.033（0.057）；FD_B→RAPM_A rate +0.029（0.056）、vol +0.014（0.068）、mix +0.029（0.060）；ΔR² 都 ≤ 0.003。卡片全季 foulDraw 在同一迴歸也是 ≈0（−0.024／−0.007）。
  - 未拉回的原始榜會混進低分鐘的人（Alex Antetokounmpo 1.875 FTA/FGA、27 FTA/36）；正式卡有 v61 拉回，不會這樣。
- 診斷（不算證據）：v60（E-054）回歸給 foulDraw +0.074/10 點，是 calibrate-wing 的樣本內擬合；這裡改成半樣本外、控制其他屬性後消失。資料沒有偏好哪個定義，選 rate 或 vol 是語意問題：rate 量「每次出手換到多少罰球」，vol 量「總共製造多少罰球」。
- 狀態：完成（探索；卡片未改）
- 相關：E-054、R-007、L-026、TODO.md 切入 B 階段
- 來源：使用者 2026-10-29「SGA怎麼沒有在造犯規的排行榜？」→「試做比較」

### E-069
- 日期：2026-10-29
- 內容：handle（控球）依 R-032 量測，並在模擬裡拆分失誤。現況：模擬 handle 全員 70，tovSkill 是總失誤率。第一階段（卡片）：控球失誤 ÷ 持球分鐘，收縮後與持球量（TIME_OF_POSS/36）各占 0.5 合成 handle；傳球失誤率做成 passSec。第二階段（模擬）：失誤拆成控球與傳球兩段，create 與出手品質改用 CRT，包夾脫困改用 handle＋pass。
- 設定：凍結預註冊 `reports/handle-E069/preregistration.md`（sha256 fc6e375e…）。判定：第一階段 (h1)(h2)(h3)；第二階段 (m0)–(m3)，(m3)＝E-067 的 b1–b3。
- 結果（第一階段，role-card 產出，lead 抽查 results.json／handle.csv 相符）：
  - 補充 1（sha256 eb84d28b…）：只看過次數表後，把 out-of-bounds 依 description 拆開，offensive foul 用同刻 foul 的 descriptor=='charge' 判定。對不上比例各季 ≤0.03%。
  - (h1) 通過：方法 c（k 64、λ 0.2、kh 256），測試季 MAE 差 −0.0261，90% CI [−0.0334, −0.0191]，n 361。
  - (h2) 通過：方法 c，MAE 差 −0.00208，90% CI [−0.00260, −0.00162]，n 441。
  - (h3) 通過：card 0.2.0 的 sha256 前後相同。
  - handle 對 2K27 Ball Handle ρ 0.739（池內 n 249）。池內 handle 與 vol 的 ρ 0.85、與穩定度 0.90，vol 與穩定度 0.58。
  - passSec 對 2K27 Pass Accuracy ρ −0.47：每次傳球失誤率最低的是少傳、傳安全球的人（Hauser 99、Gobert 96），最高的是 Luka、Westbrook（40）。適合當模擬的每次傳球風險，不適合當卡片上的「傳球好壞」。
  - G5：Brunson 99、SGA 98.8、Luka 96.9、Pritchard 96.4、Westbrook 95、White 94.3、Jokić 82.6、Caruso 79.9、McCain 77.3、Hauser 69.2、Gobert 45.6。Haliburton 2025-26 沒有出賽紀錄。
- 結果（第二階段，role-model 產出，lead 抽查 `sim/m2.json` 相符）：
  - (m0) 通過：3 個 seed 逐位元相同。
  - (m1) 通過：57 passed。
  - (m2) 不過：tov36 MAE 0.167 → 0.320，差 +0.152，90% CI [+0.128, +0.178]，n 378。全聯盟 TOV 誤差 −1.2% → +4.2%（other 類用常數，少 3.9%）。
  - creationDependence 三分組的平均誤差：
    - 低：−0.130 → +0.182，從低估翻成高估；
    - 中：−0.003 → +0.018；
    - 高：+0.058 → +0.002。
  - 校準：kCtl 0.004377（每持球秒），kPass 0.08706（每次傳球）。
  - (m3) 不過（VPN 斷線後遠端 nohup 續跑完成，379 人，E-065 同 seed，lead 自算 `bias-check-e069.json`）：
    - 主版：仍偏袒長人，S AB 81.8→106.1、BA 95.2→118.1，ρ 平均 0.382→0.333（b1、b2、b3 都不過）；
    - 位置版：翻成偏袒後衛，S AB 37.5→−50.8、BA 50.1→−38.2，ρ 0.304→0.278（b1、b2 過，b3 −0.026 不過）；
    - 2K27 ρ：主版 0.484→0.451，位置版 0.297→0.389；
    - G5 名次（主版）：Brunson 61→24、Caruso 163→359、White 29→90。
  - 報告：`reports/handle-E069/sim/report.md`、`results.json`。
  - 附帶發現（不算證據）：
    - v41 驗證路徑本來就繞過 `src` 的失誤公式，拆分寫在 `reports/handle-E069/sim/engine.mjs`；
    - E069 開關會讓 v53 死球壓迫乘數對失誤失效。
  - `src/` 的改動存成 `sim/src-e069.patch`，src 已還原。
- 狀態：完成（第二階段 m2 不過 → 依 §4.2 記錄結果，模擬不變；handle、passSec 卡片端數字保留在 handle.csv，尚未接入正式卡）
- 相關：R-032、E-067、E-055、E-066、L-026、L-036
- 來源：使用者 2026-10-29「handle要想辦法測量，例如看持球佔有 + 控球失誤」→ 定義討論 →「GO」

### E-072
- 編號：原記為 E-069，與 handle 實驗撞號，2026-10-29 改號；報告目錄與預註冊內文仍寫 E069（預註冊凍結不改）。
- 日期：2026-10-29
- 內容：R-033 修法（使用者選「改替補水準」）。替補水準 r_repl 從「MIN≥500 池 pred 的 PR10」改成邊緣池 F（可上場 ≥20 場、出賽率 <0.5）的未收縮 pred 依分鐘加權平均 r_new；MPG 改用可上場場次（扣掉傷病等不可上場場次，教練決定、下放 G League、雙向未啟用都算可上場）；小樣本 pred 往 r_new 收縮（K=500 分鐘）。需要先抓 2025-26 每場 DNP 原因。
- 設定：`reports/card-0.2.0+E069-fringe-repl/preregistration.md`（凍結，sha256 a6c028db4101489af98650267bc18057aa5e51b97be6caecbd97b525c8527c78）。判定：(c0) 重現 card 0.2.0、(c1) npm test、(c2) E-064 RAPM 分半每場 ρ 差 90% 下界 > −0.02、(c3) evaluate 閘數不減、(R1) Sandfort < min(Drummond, Reed Sheppard)、(R2) F 的 OVR 中位數 < MIN≥1000 的 PR10。
- 結果：不通過（`reports/card-0.2.0+E069-fringe-repl/report.md`；尚未經 role-audit）。(c0) 重現 card 0.2.0 sha256 相同、(c1) npm test 57/57、(c2) ρ 差 +0.0037 [−0.0048, +0.0122] 過；(c3) evaluate 18/19→16/19（big14of16 降為 13/16、Mobley 進前十）不過；(R1) Sandfort 59.6 對 min(Drummond 50.2, Reed Sheppard 39.6) 不過；(R2) F 的 OVR 中位數 59.4 對 MIN≥1000 的 PR10 53.0 不過。
  - 關鍵數字：r_new = −1.03（MIN≥500 池 pred 的 PR≈27），比舊 r_repl −2.01 高。F 共 110 人、16,846 分鐘；F 裡已收縮的 pred 加權平均為 −0.97，和未收縮的 r_new 只差 0.06。
  - 解讀（lead）：小樣本的 pred 往聯盟平均拉，不是主因。即使不收縮，box score 推出來的能力值仍把健康卻 DNP 的人估在 MIN≥500 池約第 27 百分位，看不到教練不用他們的原因。替補水準往上移後，pred 低的常上場球員 g_r 更負（MIN≥1000 且 g_r<0 的人從 22 增到 58，Reed Sheppard 46.7→39.6），與 R-033 方向相反。K=250、1000 結論相同。
  - 資料：1230 場 box score 全到（`data/season-source/dnp-2025-26.json`）。沒列在分類表的原因碼 432 人次歸「不可上場」，其中無原因碼的 `INACTIVE|(none)` 354 人次；這部分若其實是雙向合約或 G League，A_p 會被低估。
- 狀態：完成（不通過，2026-10-29；交使用者裁定）
- 相關：R-033、R-028、E-064、E-066、L-026、L-037
- 來源：使用者 2026-10-29「改替補水準」

### E-070
- 日期：2026-10-29
- 內容：R-034 製造犯規改成以量為主（預註冊）。foulDraw＝池內百分位（0.75·z(vol)＋0.25·z(rate)），vol＝FTA/36 用 E-055 方法 (c) 收縮（k、λ、kh 只在擬合季重擬合，MIN_D2 300 分鐘），rate 沿用現行收縮後 FTA/FGA。卡片其他部分照 card 0.2.0 鏈路重算。
- 設定：`reports/card-0.2.0+E070-foul-volume/preregistration.md`（凍結，sha256 c3fe3cd7a049a6a33fb9cb892e1ccf77e77eb6bafb1033e7e539e6f5cc04c817，git HEAD c920fdf）。判定 (c0) w_vol=0 重現 card 0.2.0、(c1) npm test、(c2) E-064 RAPM 分半每場 ρ 差 90% 下界 > −0.02、(c3) evaluate 閘數不減；G5 名單 SGA、Luka、Embiid、Gobert 等 13 人只列表。
- 結果（`reports/card-0.2.0+E070-foul-volume/`，role-card 子代理；lead 抽驗 c0 逐位元、verdict.json、G5 名次；role-audit 2026-10-29 獨立重算成立，`audit/audit.md`：vol 擬合格點 argmin 相同、端對端重跑三組卡逐位元相同、c0–c3 全部重現、無事後調參；FD 名次差異只來自 99 分同分的排序）：(c0) 過，w_vol=0 的卡與 card 0.2.0 逐位元相同（per36 與 fitA 中間卡也與 E-064 相同）；(c1) 57 passed；(c2) 過，repl 每場 Δρ +0.0007 [−0.0009, +0.0022]；(c3) 18/19＝基準。vol 收縮後下半季 MAE 0.751（k=0 0.829）。foulDraw 係數／10 點 0.108→0.115（SE 0.046→0.050）；2K27 ρ 每場 0.6953→0.6987。OVR 平均變動 0.18、最大 1.2，前 20 只換第 20 名（Anunoby→Curry）。FD 名次 SGA 21→5、Luka 30→4、Embiid 13→2、Gobert 3→40、Adams 8→62。偏離預註冊 7 點已揭露於 report.md（z ddof=0、c0 保留原字串等，無參數調整）。
- 狀態：完成、通過（2026-10-29）；使用者「現在發 0.2.1」，但發布時 `reports/card-0.2.1/` 已被 E-071 P1 覆蓋（L-040），站上 0.2.1 不含 E-070；改由 card 0.2.2（0.2.0＋E-070＋E-071 P1）併入
- 相關：R-034、E-068、E-055、E-064、E-066、R-016、L-026
- 來源：使用者 2026-10-29「0.75 開始」

### E-071
- 日期：2026-10-29
- 內容：壓迫（pressure）改用個人逼失誤事件（預註冊）。現行 pressure＝four-factors RAPM 的 `tovNonSteal_defense`，雜訊大、含 RAPM 評估半的洩漏，網站又誤標「壓命中率」；模擬不讀它，只在 OVR 迴歸當特徵。新 force＝(z(STL/36)＋z(DEFL/36)＋z(對位失誤調整後/100poss)＋0.5·z(造進攻犯規/36))/3.5，各分量用 2024-25 動差法定 k 收縮；P1 只換 pressure 來源，P2 再加 foulDisc（−PF/36）。顯示用 PRES＝force − 0.25·z(PF)（顯示層，不進 OVR）。
- 設定：`reports/card-0.2.0+E071-pressure/preregistration.md`（凍結，sha256 ce64cd8ad67265aec20ef1653b05e588bf279c0f1f732c3c33235773ff604dde，git HEAD c920fdf）。判定 (c0) 重現 card 0.2.0、(c1) npm test、(c2) E-064 RAPM 分半每場 ρ 差 90% 下界 > −0.02、(c3) evaluate 閘數不減、(p1) force 相鄰季 Spearman ≥ 0.70；P2 要比 P1 的 ρ 差下界 > 0 才採。P0（拿掉 pressure）只報告，用來看洩漏優勢。
- 探索（lead 自算，事後，不算證據）：Diabaté PRES 99，但造進攻犯規 0、deflection 276 人第 223、對位失誤調整後 279 人第 112，Hornets 逼失誤率 30 隊第 25。逼失誤分量和犯規正相關（合成 r +0.19／+0.22，同位置內 +0.21～+0.42），兩者相鄰季都穩定（0.72～0.83），所以分成兩個屬性、只在顯示層合併。對位失誤欄 `MATCHUP_TOV` 存在（`leagueseasonmatchups`、`matchupsrollup`），調整後相鄰季 0.66、訊號佔變異約 0.77。
- 結果：P1（事件式 force 取代 tovNonSteal_defense）過 (c0) 逐位元重現、(c1) npm test、(c2) ρ 差 +0.0038 [−0.0055, +0.0135]、(c3) 18/19、(p1) 0.727；P2−P1 −0.0003 [−0.0018, +0.0013] 不採 P2。只是不變差，不是變準；P0（拿掉 pressure）−0.0122，屬性本身有用。2K27 每場 ρ 0.695→0.679（只報告）。stl 與 defl 相關 0.88。G5：Diabaté PRES 99→61.4、OVR 84.2→79.2（42→74 名）；Lowry 99→62.5；Dru Smith、Ausar Thompson 升到 99。audit（`audit/audit.md`）獨立重算全部逐位元相同；字面 k 敏感度 c2 +0.0016 [−0.0070, +0.0103]、p1 0.726，結論不變。
- 狀態：通過 G1–G4（2026-10-29，含勘誤 1）；使用者「採用 P1」，與 E-070 合併發為 card 0.2.2（R-039；合併關卡 c0a/c0b/c1/c2/c3 全過，見 `reports/card-0.2.2/gates.json`）
- 相關：R-022、R-031、E-067、E-070、L-026
- 來源：使用者 2026-10-29「去確認對位失誤。寫預註冊」
- 實作完成 2026-10-29：`reports/card-0.2.0+E071-pressure/report.md`（依採用規則 P1 過 c0–c3、p1；P2 − P1 CI 下界 −0.0018 不採 P2；結論由 lead 填）
- 勘誤 1（使用者 2026-10-29 核可）：§2.3 k 字面公式少乘 d 單位，改 k=σ₁²/τ²，見 `reports/card-0.2.0+E071-pressure/errata.md`（sha256 05dcd741…）。role-audit 重算中。

### E-073
- 日期：2026-10-29
- 內容：R-033／R-035／R-036 修法第二版。E-072 顯示 box score 看不到教練看到的東西，改成把用人當能力的直接證據：RAPM_另一半 ~ pred + ln(1+MPG_avail) + 出賽率 + 年輕(≤23)／老將(≥31) 與其和分鐘的交互項 + 年輕×練兵隊(勝率<0.35)×分鐘，交叉擬合（A 半特徵的係數只用 B 半答案估）。每場分五類：有出賽、輪休（REST 碼）、傷病／不可上場、疑似輪休（該隊有出賽 ≥10 場且平均 ≥24 分鐘、非連續 ≥3 場的教練決定）、教練不用；只有有出賽與教練不用算 A_p。
- 設定：`reports/card-0.2.0+E073-usage-evidence/preregistration.md`（凍結，sha256 db42fc16b50631a41189ca41756ad5a881e569ab60737208acd9d672c360f4de；第一版 eaca2e72… 派工前加 (R4) 後重凍，2026-10-29）。判定 (c0) 重現 card 0.2.0、(c1) npm test、(c2) RAPM 分半每場 ρ 差下界 > −0.02、(c3) evaluate ≥18/19、(c4) 用人特徵讓另一半 RAPM 預測變準（下界 > 0）、(R1) Sandfort < min(Drummond, Sheppard)、(R2) F 中位數 < MIN≥1000 PR10、(R3) 隊內 ρ(MIN, 每場 OVR) 中位數 ≥ 0.675、(R4) MIN<100 組 OVR PR90 < MIN≥1000 且 MPG 12–22 組中位數（card 0.2.0 現況 Oduro 72.8 vs 62.5，會不過）。(c4) 單獨沒過記「語意版」交使用者。
- 補充 1（`supplement-1.md`，sha256 f7b87296…f15a，派工後、看任何候選數字前）：R-035 基準 0.675 是 lead 原腳本不處理同分、中位數取 v[15] 的結果；(R3) 改用標準 Spearman 與標準中位數，門檻改成「≥ card 0.2.0 同算法值」（0.6608）。
- 結果：不通過，只有 (R1) 沒過（`reports/card-0.2.0+E073-usage-evidence/report.md`，ranking.csv sha256 9eeae54a…；role-card 子代理產出，lead 抽查 ranking.csv、results.json、c0 sha 相符；尚未經 role-audit）。
  - 過：(c0) sha 相同；(c1) 57/57；(c2) Δρ +0.0025 [−0.0144, +0.0182]；(c3) 18/19；**(c4) 用人特徵讓另一半 RAPM 預測變準 Δρ +0.0202 [+0.0022, +0.0373]**；(R2) F 中位數 52.5 < 53.9；(R3) 0.733 ≥ 0.661；(R4) MIN<100 的 PR90 57.8 < 63.25。
  - 不過：(R1) Sandfort 54.4，Drummond 57.3，Reed Sheppard 52.2。Sandfort 從 61.0 降到 54.4，但 Sheppard 只從 46.7 升到 52.2。
  - 卡片係數：p 0.88，L 1.11，出賽率 −2.00，年輕 +0.24，老將 +0.11，年輕×L −0.15，老將×L +0.17，年輕×練兵隊×L −0.38。最後三項的方向和 R-035 一致；但年齡項在 A→B 與 B→A 兩個方向正負相反，個別不穩。拿掉年齡項（s3）後 (c2)、(c4) 都不過。
  - 個案：Kennedy Chandler 78.3→69.8、Cody Williams 35.8→32.5、McCain 57.9→57.7、Drummond 48.7→57.3。敏感度 s1–s3 的 (R1) 都不過。疑似輪休 43 組、84 人次。
  - 唯讀檢查：只有 `data/*2026-27*` 的 5 個檔在 04:01 被改，是現季資料更新，不是 e073.py 寫的。
- 狀態：完成（不通過，只差 (R1)，2026-10-29）；使用者接受為 card 0.3.0 候選（R-038）；role-audit 重算成立（2026-10-29，`audit/audit.md`：582 列 OVR 最大差 0、c2/c4/R1–R4 全部重現；18 條未寫到之處無事後挑選；10 個替代變體 (R1) 都不過，c4 下界只有 s3 變負；間接相依：fitA/fitB 卡用 RAPM 半季校準，p_B 含 RAPM_B 資訊，屬預註冊字面結果）；待以當時正式卡重跑 c0–c3、R1–R4
- 相關：R-033、R-035、R-036、E-072、E-064、L-026、L-036、L-037
- 來源：使用者 2026-10-29「寫預註冊」「然後要分清楚DNP和輪休」；同日「高分鐘替補球員比低分鐘淘汰球員OVR低」→ (R4)

### E-074
- 日期：2026-10-29
- 內容：賽中 OVR（2026-27）改用 card 0.2.2 當先驗：x0 屬性、凍結迴歸係數、每場錨點與 r_repl 全換 0.2.2；pressure（= 逼失誤）維持凍結；foulDraw 賽中更新改 E-070 量為主公式（z／百分位母體凍結為 card 0.2.2 的 2025-26 母體）；頁面 PRES 標籤改「壓迫」加 tooltip。換版不擬合，版號 inseason 0.2.1（R-019 PATCH）。
- 設定：`reports/ovr-inseason-2026-27/e074-card022/spec.md`（sha256 658cefed…7776）。判定 (c0) 開關關掉逐位元重現 inseason 0.2.0c、(c1) npm test、(c2) N=0 先驗 OVR 對 card 0.2.2 每場 OVR Spearman ≥ 0.99、(c3) 版號與頁面標籤。
- 結果（2026-10-29，role-card；`reports/ovr-inseason-2026-27/e074-card022/report.md`）：c0 `CARD_MODE=020` ranking.csv／no-prior.csv 與已發佈 0.2.0c 逐位元相同（ranking sha256 7e6f1a53…）；c1 npm test 57/57；c2 N=0 先驗 OVR 對 card 0.2.2 每場 OVR Spearman 0.99999（362 人），r_repl −1.7593，兩份 summary 鍵與 card 0.1.2 版相同；c3 `probe_base_version()`＝inseason 0.2.1，頁面 PRES「壓迫」＋tooltip。前 20 名進 Maxey、Tatum，出 Markkanen、Davis；|ΔOVR| 中位數 1.20、最大 8.5，最大 10 人全由 pressure 換定義造成（Sheppard +8.5、Banchero −8.1、Nembhard −8.0、Mobley −6.3）。foulDraw 新公式使高出手量球員的視窗 y 大幅上升（Edwards 55→85、SGA 57→79）。新檔：`live/build_prior_022.py`、`live/prior-2025-26-card022.json`（sha256 0518184f…）、`CARD_MODE` 開關（預設 022）。
- 狀態：完成（2026-10-29 lead 審過：c0 兩檔 sha256 自行核對相符、diff 已讀、npm test 由 dispatcher 重跑 57/57）；待使用者核可 commit 與發佈（R-031）
- 相關：R-039、R-031、R-019、R-018、E-070、E-071、E-064、L-026
- 來源：使用者 2026-10-29「賽中改跟 card 0.2.2：寫 spec 派工，含 c0 重現與新版號」

### E-075
- 日期：2026-10-29
- 內容：E-073（用人當能力證據）移到正式卡 card 0.2.2 重跑；只換輸入（p 全季／半季、基準卡、(R4) MPG），方法照 E-073 凍結檔。(R1) 依 R-038 只報告。
- 設定：`reports/card-0.2.2+E073-usage-evidence/preregistration.md`（sha256 faec88da…bcd5）
- 結果（2026-10-29，role-card 子代理；lead 抽驗：預註冊 sha、c0 sha 9f5700c2… 逐位元、npm exit 0、results.json 判定值、e073→e075 diff 只改路徑／標籤與 R1 改只報告）：**語意版**。c0 逐位元重現 card 0.2.2；c1 57/57；c2 Δρ −0.0005 [−0.0186, +0.0159] 過；c3 18/19＝基準；**c4 Δρ +0.0160 [−0.0002, +0.0321] 不過（差 0.0002；E-073 時下界 +0.0022）**；R1（只報告）Sandfort 53.6 < Drummond 57.7、Sheppard 60.4，現在成立；R2 51.7 < 52.1；R3 0.747 ≥ 0.641；R4 57.8 < 63.5。敏感度：s1、s2 c4 也不過；s3 c2、c4、R1 不過。MIN 分組 OVR 中位數 <100／100–300／300–1000／≥1000 = 51.6／52.7／55.6／73.4（card 0.2.2：55.7／57.6／58.9／72.6）。對 E-073 card 逐人 OVR 最大差 8.2（Sheppard 52.2→60.4），|差|≥2 有 90 人。ranking.csv sha256 01aab81a…2215。
- 狀態：完成（語意版，2026-10-29）；使用者依機會成本接受為 card 0.2.3 候選（R-040，版號使用者定）；role-audit 重算成立（2026-10-29，`audit/audit.md`：582 列 OVR 最大差 0、係數差 2.7e-15、diff 無邏輯改動；c4 下界對蒙地卡羅敏感：seed 1–20 有 12 個為正、10000 次 +0.0004，係數隨 bootstrap 重擬合則 −0.021；樣本內 rhoRapm 0.829→0.775、rho2k 0.681→0.740、rhoDef 0.567→0.490 只報告）；G5 使用者通過（「不錯」，2026-10-29），已發布 card 0.2.3（gh-pages b053b26）
- 相關：E-073、R-038、R-039、R-033、R-035、R-036、L-026
- 來源：使用者 2026-10-29「等 0.2.2 再重跑」

### E-076
- 日期：2026-10-29
- 內容：模擬長人偏袒迴圈（`reports/sim-bias-loop/loop.md`）第一條引擎假設 H2「體格去重複」：physique（純尺寸百分位）同時進協防加成、籃板、補籃、籃下命中、出手拉向禁區，而 help／rebound／short 已含尺寸效果。新旗標 `physiqueMode`：`legacy`（預設，逐位元重現 E-065）、`dedup`（關協防加成、籃板權重、補籃乘數；保留 physEdge）、`dedup-all`（參考，連 physEdge 也關）。第 0 步先追 v53 patch 鏈實際活著的 physique 管道。常數只對聯盟總量校準（OREB%、二波得分、籃下允許命中率），不對 S／RAPM 調。量尺 E-067；另加球隊層 t1（30 隊循環賽淨分差對真實淨效率 RMSE 不顯著變差）。
- 設定：`reports/sim-0.1.0+E076-physique-dedup/preregistration.md`（sha256 aa32e7dc…9308）；基準 sim 0.1.0（src tree 6f6283a9…）；探針子集 seed 20261029 各位置 20 人；全量 379 人 baseSeed 20261028 在 5090 跑。
- 判定：(g0) legacy 逐位元重現、(g1) npm test、(b2) 四個 S 都變小、(b3) ρ 平均不降 >0.02、(t1) 球隊 RMSE 差 90% 上界 <+0.5 → 採用為 sim 0.1.1 候選；(b1) 不偏袒長人是迴圈停止條件。
- 狀態：進行中（2026-10-29 派工，dispatch 路由 self：main 7 天 98%，App 內 sonnet 子代理，role-model）
- 相關：E-065、E-067、R-022、R-025、L-026、L-036
- 來源：使用者 2026-10-29「寫預註冊並派工」（目標：降低模擬對長人的偏愛）
- 結果：2026-10-29 完成（`reports/sim-0.1.0+E076-physique-dedup/report.md`）。(g0) 10/10 逐位元一致；(g1) npm test 57/57、exit 0；(b2) 四個 S 都變小（主版 +72.2／+85.0 vs 81.8／95.2；位置版 +21.4／+34.0 vs 37.5／50.1）；(b3) ρ 平均主版 0.380 vs 0.382、位置版 0.329 vs 0.304；(t1) RMSE 差 −0.101，90% 區間 [−0.563, +0.340]，上界 <+0.5。(b1) 主版仍「偏袒長人」未達，位置版未偵測到偏袒；停止條件未達，迴圈繼續（lead 2026-10-29 勘誤原「觸發」字樣）。校準 `orbLogitDelta` −0.135：OREB% 0.2653 在容許內，二波得分 13.40 超出 ±1.0（−1.58，旋鈕衝突，L-043）。dedup 實際只改 `reboundContest` 一項（F-034）；S 改善小於區間寬度，C 的高估被推到 PF／SF（F-035）。dedup-all 僅報告。是否進 sim 0.1.1 由 lead 看五道關卡決定。

### E-077
- 日期：2026-10-29
- 內容：PHYS 只用身高＋體重/10（`scripts/build_season_league.js:120`、`scripts/build_benchmark_league.js:49`；README.md:165 寫「0.45/0.55 標準化加權」已過時）。檢定選秀體測 ape（臂展−赤腳身高）在 bio 身高、體重之外，能不能多解釋 OREB%、DREB%、BLK/36。依 PLAYER_ID 奇偶分半做 held-out ΔR²，以球員為單位 bootstrap 2000 次（seed 20261029）。
- 設定：`reports/E077-wingspan/preregistration.md`（看結果前寫，原 sha256 b04822d2…9089；編號由 E-076 改 E-077 後為 5ec87bbc…7515）；體測 `combine-anthro.json` 2000–2025 屆 1736 列（nba.com 網頁表格；stats API 不通）；偏離：2014-15 沒有 bio.json 被跳過，實際用 11 季。
- 結果（2026-10-29，App 自跑，未經 audit）：2591 個球員季、674 人，有體測的 450 人（68%）；ape 標準差 2.2 吋。ΔR²：OREB% +0.007 [−0.011, +0.021]、DREB% +0.009 [−0.006, +0.021]、**BLK/36 +0.050 [+0.022, +0.082] 過**。只有 1/3 過，所以照預註冊**不加進 PHYS**。每吋效果：OREB% +0.15 個百分點、DREB% +0.30 個百分點、BLK/36 +0.076（第 10 到第 90 百分位約差 0.46）。只報告：摸高的結果和 ape 相同（只有 BLK 過）；只看 2025-26 三者都不過；2025-26 護框對手命中率每吋 −0.84 個百分點，但 ΔR² 區間含 0。詳見 `results.md`。
- 狀態：完成（2026-10-29）；結論是 ape 不進 PHYS；若要用，候選是蓋帽屬性（需另立預註冊，且要處理沒體測的人：狀元與國際球員缺得多）
- 相關：E-076、L-026、R-007
- 來源：使用者 2026-10-29「測看看」（問：臂展能不能補進身材）

### E-078
- 日期：2026-10-29
- 內容：接 E-077，檢定 ape 在身高、體重之外，和抄截（假設 S：STL/36，11 季球員季）、整體防守嚇阻力（假設 D：四因素 RAPM 2022-26 的 pooledD、rimShare_defense、efg_defense，防守回合 ≥ 2000）有沒有關係。方法同 E-077（ID 奇偶分半 held-out ΔR²、bootstrap 2000 次、seed 20261029）。2025-26 護框命中差已在 E-077 看過，不列入判定。
- 設定：`reports/E078-wingspan-defense/preregistration.md`（看結果前寫，sha256 0ca99ad5…63bc）；沒有偏離。
- 結果（2026-10-29，App 自跑，未經 audit）：**S 不過、D 不過（0/3）**。ΔR²：STL/36 +0.010 [−0.039, +0.041]、pooledD +0.026 [−0.007, +0.055]、rimShare +0.022 [−0.004, +0.047]、efg +0.022 [−0.024, +0.058]。全樣本（樣本內）係數方向都一致為正，區間都不含 0：每吋 STL/36 +0.029、pooledD +0.145（差 6 吋約每百回合 +0.87 分）、rimShare +0.150、efg +0.061；只報告的 threeShare 每吋 −0.143（對手從籃下改投外線）。結論：效果存在但弱，樣本外預測不出來；RAPM 部分檢定力有限（n 609，基準 R² 0.01）。詳見 `results.md`。
- 狀態：完成（2026-10-29）；臂展唯一明確的訊號仍是 E-077 的蓋帽
- 相關：E-077、R-007、L-026
- 來源：使用者 2026-10-29「抄截大概也和臂展有關 或是整體防守嚇阻力」

### E-079
- 日期：2026-10-29
- 內容：RAPM 改用近期加權（季權重 d^(距最近一季季數)，λ 固定 3000）取代四季等權合併。第一階段只用舊季選 d（窗口前三季 → 目標 2017-18..2020-21，格點 d ∈ {1, 0.75, 0.5, 0.25, 0}），再在 2022-25 → 2025-26 檢驗一次 stint 回合加權 MSE（截距用目標季自身平均，比賽 bootstrap 2000、seed 20261029）。P 過才做第二階段：卡片管線所有讀 RAPM 的步驟改讀 d* 版（pooledPoss 保留不加權，人群不變）。
- 設定：`reports/card-0.2.3+E079-recency-rapm/preregistration.md`（凍結，sha256 bbdb9618dfdf27c304f7affd4daa282b1d4581607fc9556ac4cd00ebe3cb8ca8）。判定 (P) Δ 90% 上界 < 0；卡片層 (r0) d=1 重現三份 RAPM、(c0) 重現 card 0.2.3、(c1) npm test、(c2Q) E-064 舊量尺下界 > −0.02、(c2N) 新增現況量尺（另一半 2025-26 單季 RAPM × MPG）下界 > −0.02、(c3) ≥18/19、(R2)–(R4) 同 E-075。d* = 1 → 結束，記「等權合併已是最佳」。
- 已揭露：lead 看過 Banchero／Jalen Williams／Jalen Johnson 的卡片與 RAPM 值、年齡分組「卡片名次 − 2K 名次」事後探索（≤24 歲 +64、≥31 歲 −7.5）；沒看過任何前瞻數字。
- 不含：Jalen Williams 被標 PF（位置標籤）另案。
- 狀態：完成、不採用（2026-10-29）。P 未過，依預註冊停止，沒做第二階段，card 0.2.3 不變。d* = 0.25（選擇季平均 MSE 4158.614 vs d=1 4161.938）；主檢驗 2025-26 Δ +0.229，90% [−1.344, +1.799]。d=0（只看上一季）在 2025-26（Δ +2.734 [+0.540, +4.944]）和 2024-25 都顯著較差。λ 敏感度：CV 全選 3000，結果相同。事後觀察、不作判準：d=0.75 在 2025-26 的區間 [−1.259, −0.347] 會過，2024-25 上界 +0.010；要用必須另寫預註冊，用沒看過的季。報告 `reports/card-0.2.3+E079-recency-rapm/report.md`（results.json）。
- 相關：R-040、E-075、E-064、R-007、R-019、L-026、L-037
- 來源：使用者 2026-10-29「PF 好怪。paolo, jalen will, jalen johnson的排名都比預想中低很多」→「寫預註冊」

### E-080
- 日期：2026-10-29
- 內容：護框屬性 help（rim DFG% 差 <6 呎）改成位置平均收縮（k 用 shootingEB 同款動差法，擬合 2022-23..2024-25）＋多季百分位錨點（PR1/50/99 → 40/70/99），99 以上飽和尾巴 99 + 26·(1 − e^(−Δ/SD))（漸近 125），40 以下對稱飽和到 25；引擎 CURVE_DEF_RIM 改成同一對應的反函數。一個旗標切換。
- 設定：`reports/E080-rimd-scurve/preregistration.md`（凍結，sha256 83719b99d7106e81a8439abe6f4ea9ba4b5adf6ec2af59acfd591d9820a77da7）；開工條件：E-076 判定後；基準為開工時正式 card／sim。
- 判定：(h1) 用 2024-25 預測 2025-26 rim 差的 MSE 變小（不過則收縮退回現行、只做尺度）；(g0) 旗標關重現、(g1) npm test、(t1) 球隊 RMSE 上界 < +0.5、(b2') E-067 四個 S 不變大、(c2Q) 舊量尺下界 > −0.02、(c3) evaluate 閘數不減。
- 已揭露：Stewart 原值 123、z 4.82 與 F-030 的探索數字；沒看過任何收縮值、k、錨點或候選數字。
- 狀態：**未過**（2026-10-29，(b2') 不過；`reports/E080-rimd-scurve/report.md`）。不採用，不准在這份預註冊下換參數重跑
- 結果：
  - (h1) 過：Δ MSE −0.000479，90% [−0.000680, −0.000283]，用位置收縮。μ_g G 0.019／F −0.022／C −0.056，k 149.6。
  - (g0) 過：league、sim、卡片都逐位相同。
  - (g1) 過：旗標開、關都 57 passed。
  - (t1) 過：Δ −0.157，90% [−0.720, +0.362]。
  - **(b2') 不過**：WinImp 主版 S，AB 81.8 → 87.6、BA 95.2 → 99.9；位置版翻成負的（37.5 → −30.4、50.1 → −16.6）。
  - (c2Q) 過：Δ −0.0021，90% [−0.0053, +0.0010]。
  - (c3) 過：18/19 = 基準。
  - 只報告：
    - help > 99 的有 12 人（> 110 有 2 人）。Stewart 99（截斷）→ 115.7，全聯盟最高：k 149.6 < 200，收縮反而變弱。
    - 2K27 ρ 0.7401 → 0.7347。籃下 FG% 0.584 → 0.576。
  - 偏離：D1 2025-26 用卡片來源；D2 節點 25 改 26；D3–D7 見報告。
- 相關：F-030、E-067、E-076、E-079、R-007、L-026
- 來源：使用者 2026-10-29「參考我們baseball專案。用類似S型曲線 做校準，降低123這種誇張數字-》只留給歷史級強者」

### E-081
- 日期：2026-10-29
- 內容：card 0.2.3 的樣本外年齡偏差診斷（不改卡）。以 E-075 半季卡片 g_c 為卡片；答案 N（主）= 另一半只用 2025-26 比賽的 RAPM net（λ 3000）× 另一半 MPG，答案 Q（只報告）= E-064 舊量尺。殘差 u = pct(答案) − pct(卡片)，主統計量 S = Spearman(年齡, u)，兩方向平均，球員 bootstrap 2000、seed 1。
- 設定：`reports/card-0.2.3+E081-age-residual/preregistration.md`（凍結，sha256 9e1402e0681580de27e9a344cd3ea0c01f8b7ad40b6a5b5fc570c4566829296e）。判定：S 的 90% 上界 < 0 → 年輕被低估；下界 > 0 → 老將被低估；兩者皆非 → C 線結案。自檢 (k0) 重現 E-075 c2、(k1) 重現 rapm.csv lastSeason*。
- 已揭露：2K 年齡分組的事後探索、E-075 與 E-079 的全部數字；沒看過殘差 × 年齡。
- 狀態：完成，判定「年輕被低估」（2026-10-29）。lead 抽驗：results.json 與報告一致，預註冊 sha256 不變，(k0)(k1) 最大差 0。
  - 答案 N：S = −0.202，90% [−0.262, −0.141]（AB −0.225、BA −0.179）。分組 u 平均：≤23 +0.101 [+0.070, +0.134]、24–27 +0.003、28–30 −0.030、≥31 −0.094 [−0.149, −0.044]。
  - 答案 Q（只報告）：S = −0.021 [−0.078, +0.034]，沒有偏差；N − Q = −0.181 [−0.229, −0.133]。
  - 解讀：卡片對齊四季合併 RAPM（校準 r 與 E-075 訓練目標 pooledNet 都是），合併 RAPM 對成長中的年輕球員落後、對衰退中的老將偏高。人群 AB 389、BA 388、聯集 395，0 人因缺年齡排除。具名球員的 u 在兩方向正負相反，不解讀個人。
  - 下一步：修正預註冊 E-084。
- 相關：E-075、E-064、E-079、E-082、E-084、R-007、L-026
- 來源：使用者 2026-10-29「設置一個goal 。讓我們把這個任務（位置錯誤，跨季RAPM，新秀vs老將）完成」

### E-082
- 日期：2026-10-29
- 內容：位置從單一硬標籤改成 2025-26 先發秒數比例（投票邏輯同 protocol.mjs；先發 < 5 次維持 one-hot），用在 calibrate-wing 的三處：位置交互項、r 的位置置中、防守加成置中。模擬目標 y 不重跑。之後接 E-075 與 build_card_023。
- 設定：`reports/card-0.2.3+E082-position-shares/preregistration.md`（凍結，sha256 fc1462b8fd887cb5de05a160b5b9cededb0bb416273474773b062db81c98d10a）。判定：(s0) 比例最大位置 = 原標籤（不符 ≤ 3 人）、(c0) one-hot 重現 card 0.2.3、(c1) npm test、(c2Q) 下界 > −0.02、(c2N) 用 E-081 的 rapm1 單季分半答案、下界 > −0.02、(c3) ≥ 18/19、(R2)–(R4) 同 E-075。全過 → G5；(c2N) 下界 > 0 → MINOR，否則 PATCH。
- 已揭露：F-033 的單人反事實與邊界人數。
- 狀態：完成、不採用（2026-10-29）。只有 (R3) 沒過：隊內 MIN–OVR Spearman 30 隊中位數 0.7248 < card 0.2.3 的 0.7469。lead 抽驗：results.json 與回報一致，基準 0.7469 就是 card 0.2.3 summary.json 的值，預註冊 sha256 不變。
  - 其餘全過：(s0) 334 人不符 0；(c0) 逐位元重現；(c1) 57/57；(c2Q) Δρ −0.0008 [−0.0041, +0.0025]；(c2N) +0.0010 [−0.0028, +0.0048]；(c3) 18/19；(R2) 52.6 < 52.8；(R4) 58.2 < 62.6。
  - 三人：Banchero 69.9／205 → 69.6／208；Jalen Williams 79.6／80 → 80.4／75；Jalen Johnson 81.9／63 → 81.8／63。前 30 名各位置人數不變；全體平均 |ΔOVR| 0.62。
  - 解讀：比例混合對樣本外量尺幾乎沒有影響，對三人也幾乎沒影響（F-033 的單人改標是極端反事實，比例混合只移一部分）。位置不是三人偏低的主因。
- 相關：F-033、E-075、E-081、R-019、L-026、L-037
- 來源：同 E-081

### E-083
- 日期：2026-10-29
- 內容：RAPM 近期加權，d 寫死 0.75，以完全沒看過的 2026-27 檢驗一次（窗口 2023-24..2025-26 → 2026-27）。方法照 E-079 §2.2–§2.3。P 過才做卡片層（照 E-079 §3）。
- 設定：`reports/card-0.2.3+E083-recency-2026-27/preregistration.md`（凍結，sha256 abb3e2a61d436f1181cced223a5b6e9abe6c94eea6a98789c39b1a9796262001）。(P) Δ = MSE(0.75) − MSE(1) 的 90% 上界 < 0，比賽 bootstrap 2000、seed 20271029。
- 開工條件：2026-27 例行賽打完，stint 建好且比賽數 ≥ 1200；不做期中檢驗。
- 已揭露：d = 0.75 是看過 E-079 的 2025-26 結果後才挑的，所以這次只能用新季檢驗。
- 狀態：預註冊凍結，等 2026-27 季末
- 相關：E-079、L-026
- 來源：同 E-081

### E-084
- 日期：2026-10-29
- 內容：修正 E-081 的「年輕被低估」。E-075 用人回歸的訓練目標從 fit 半季 pooledNet（四季合併）改成 fit 半季只用 2025-26 的 RAPM net（E-081 的 rapm1），權重改 rapm1 poss；特徵、年齡項、人群、卡片組裝都不動，沒有可調參數。
- 設定：`reports/card-0.2.3+E084-current-target/preregistration.md`（凍結，sha256 a7a034b50b39b48471f8f65e85b23c5875eee02bd064cbf39f87a066e03bb6ca）。判定：(c0) pooled 重現 E-075／card 0.2.3、(c1) npm test、(b) ΔS_N 下界 > 0、(c2N) 下界 > −0.02、(c2Q) 下界 > −0.05、(c3) ≥ 18/19、(c4) 用單季 net 下界 > 0、(R2)–(R4)。全過 → G5；(c2N) 下界 > 0 → MINOR，否則 PATCH。和 E-082 都過時跑合併版（§5）。
- 已揭露：E-081 全部數字；修正方向是看過 N／Q 差異後才選的，評估是同季另一半（交叉擬合），不是沒看過的季。
- 狀態：**採用，發成 card 0.2.4**（2026-10-29，R-042、R-044）。原記錄：完成、不通過（2026-10-29）。只有 (c3) 沒過：evaluate 16/19 < 18/19，多掉 carusoGate（Caruso 名次 78 → 103，參考 94）與 big14of16（13/16：Wembanyama 6 對參考 5、Embiid 18 對 17.5、Anthony Davis 45 對 32）。兩閘的參考名次取自 2K 與四季合併 RAPM。lead 抽驗：results.json、evaluation.json 與回報一致，預註冊 sha256 不變。
  - 其餘全過：(c0) 逐位元重現；(c1) 57/57；(b) ΔS_N +0.127 [+0.107, +0.147]（S_N −0.202 → −0.075）；(c2N) +0.025 [+0.009, +0.039]；(c2Q) −0.017 [−0.030, −0.004]；(c4) +0.046 [+0.028, +0.065]；(R2)(R3)(R4) 過（R3 0.7645 ≥ 0.7469）。
  - 副作用：S_Q −0.021 → +0.137（用合併量尺看變成老將被低估）；pred_new 標準差 1.65 → 1.01，卡片更偏向分鐘。MIN≥1000 OVR 中位數：≤23 歲 62.2 → 67.3，≥31 歲 80.8 → 76.0。
  - 三人：Banchero 69.9／205 → 76.1／133；Jalen Williams 79.6／80 → 82.0／76；Jalen Johnson 81.9／63 → 84.3／62。
  - 機械判定是不通過；使用者依機會成本裁定為**通過（R-042）**，role-audit（Opus）重算成立（2026-10-29，`audit/audit.md`）：點估計、係數與 OVR 差 0；seed 2–5 區間最多移動 0.0013；rapm1 從 stints 獨立重擬合，差 6e-14；沒有洩漏。results.json、report.md 的 verdict 已改為「通過（R-042）」，原判定保留在 verdict_mechanical。G5 使用者通過，2026-10-29 發成 card 0.2.4（PATCH，R-044）。
  - 退步六人的原因（稽核）：LeBron、Davis、Curry、Gobert、Embiid 是當季 RAPM 本來就低（例：LeBron 當季第 173、四季第 44）；只有 Caruso 是分鐘權重變重（能力名次 10 → 11，MPG 17.9）。
  - 稽核列出的下一輪目標：(i) pred 分散度壓縮讓低分鐘高效率的人吃虧（Caruso 型）；(ii) 沿用 E-075 的設計，coef_AB 訓練特徵含 p_B，p_B 用評估半 rapm-B 擬合，是間接路徑，影響沒量；(iii) card 0.2.2 的 p 被上限截住，9 人同為 1.894；(iv) mpg-A／B 出賽數與 player-games 依奇偶重算的結果有 35 人不同。E-082 不通過，所以 §5 的合併版不跑。退步項列為下一輪目標，見 R-042。
- 相關：E-081、E-075、E-082、R-019、R-042、R-043、R-044、L-026、L-037
- 來源：同 E-081

### E-085
- 日期：2026-10-29
- 假設：physEdge 兩端都重複計分（持球者端與 `short`、防守端與 `help`）；置中後防守端體格對籃下命中的額外斜率接近 0，整條應關；關掉後 S 對樣本外答案下降。
- 做法：`reports/sim-0.1.0+E085-physedge/preregistration.md`（sha256 8f707a79…b693）。第 1 步用 stats.nba.com 逐對手的球員 RA 命中率估 β_phys（控 help），r = clamp(β_phys/β_model,0,1)，區間含 0 則 r=0；主版 `centered` physEdge = r×tanh((P̄−defTeamPhys)/45)；判定用 2022-23～2024-25 三季 pooled RAPM × MPG 的樣本外答案（o1、o2、t1），樣本內 S 只報告（dedup-all 已看過）。
- 結果（2026-10-29，role-model opus 子代理；lead 核對 sha、flags、g0、calibration、team-check、bias、bias-oos、npm log）：
  - β_phys = +0.0408 pp／點 [−0.0966, +0.1805]（控 help；β_help −0.769 [−0.936, −0.587]），β_model 0.2695；區間含 0 → **r = 0**，centered 等同 physEdge 全關（F-039）。先發五人版 +0.082 [−0.021, +0.173] 也含 0。
  - 判定：g0 過（10/10 逐位元）、g1 過（57/57，本機與 5090 乾淨樹）、m1 過、**o1 不過**（樣本外主版 57.1→35.2，配對差 +21.9 [14.8, 28.7]；位置版 22.3→**28.6**，配對差 −6.3 [−18.4, +5.3]）、o2 過（ρ 0.394→0.397、0.248→0.261）、t1 過（RMSE 差 −0.114 [−0.603, +0.382]）、b1 不過（兩版仍偏袒：35.2 [14.6, 56.0]、28.6 [2.6, 53.2]）。校準不需動（短距離命中 0.5807 vs 實際 0.5777，佔比 0.4788 vs 0.4844）。
  - 樣本外答案（2022-25 pooled RAPM × MPG，n=287）：legacy 主版 S 57.1／位置版 22.3；E-076 dedup 49.0（配對差 +8.1 [−0.3, 16.6]）／9.8（+12.5 [0.8, 23.9]），E-076 第一次有樣本外證據（F-035 狀態更新）。
  - 指名球員幾乎沒動：Mark Williams 13→20、Duren 9→11、Claxton 48→37；Smart 276.5→263、Dort 268→286、Herb Jones 228.5→255。長人高估主因不在 physEdge。
  - 事後只報告：模擬抽樣雜訊 σ ≈ 27–39 S 點（F-040、L-054），E-085 主版「明顯下降」在 1σ 內；o1 本來就不過，結論不受影響。
  - 偏離（lead 接受）：r 公式正負號對齊；P̄ 分鐘加權 69.7186；β 只量 RA 而引擎套 RA＋禁區；對手體格分鐘加權；npm test 另在 5090 乾淨樹重跑。report.md 由 lead 依子代理交回文字存檔（L-055）。
- 狀態：完成，**不採用**（2026-10-29）；迴圈繼續。報告 `reports/sim-0.1.0+E085-physedge/report.md`。
- 相關：E-076、E-067、E-065、E-086、F-034、F-035、F-039、F-040、R-041、L-026、L-054、L-055

### E-086
- 日期：2026-10-29
- 假設：探索性，無。問題：除 physEdge 外，哪些活管道在推高長人、推低後衛。
- 做法：`reports/sim-0.1.0+E086-param-screen/spec.md`。探針子集 100 人、30 對手 × 8 樣本，逐管道中和（doubleThreat phys、receiverWeights、reboundContest、contestHelp 斜率、出手來源、spacing／gravity 上限、onBall 壓迫、ctxPass 遞減、foulDraw、補籃率）量 ΔS／Δρ，對照兩 seed 噪音底線排序。結果只用來排假設順序，不採用。
- 結果（2026-10-29，同一子代理，5090 18:52–23:24）：
  - 規格噪音底線（兩 seed）avg |dS| 4.51、pos 5.09。依規格只有 ch3（+15.95）、ch5（−14.91）、ch8 pos（+21.59）「分得出來」，但 ch3 拆半正負翻轉（+15.95／−21.19，全量 379 人 −9.6）、ch5 換 E-085 基準剩 +2.0、ch8 方向與假設相反（PG 分數反而降）。
  - 事後算的配對模擬雜訊 σ8 ≈ 17（avg）／19（pos），規格底線只有它的 1/4；所有管道 z < 1.2。**篩查分不出任何管道，也不能排除任何管道**（F-040）。
  - 死碼：ch2（receiverWeights 只在非 volume 用）、ch7（onBall 固定 70）、contestHelp 字面分支；追加 ch7b（live-TOV 壓迫 ×2，−6.76）。
  - 重現：legacy／ch3／e085／e085+ch3 由既有全量 checkpoint 衍生，24,000/24,000 draw 相同；三套實作（E-076 dedup-all、E-085 centered、E-086）一致，先前「不可加」疑慮由雜訊解釋。
  - 建議下一輪：先修量尺（分差計分、加樣本、樣本 bootstrap），再用全量＋樣本外答案重驗 ch8、ch3、ch5、ch9。
- 狀態：完成（2026-10-29），結論「量尺雜訊太大，無法排序」。報告 `reports/sim-0.1.0+E086-param-screen/report.md`。
- 相關：E-085、E-076、E-067、F-040、R-041、L-054、L-055、loop.md H3–H7、H9

### E-087
- 日期：2026-10-29
- 假設：E-069 失敗是因為把失誤綁到持球秒數。只把實測 handle 用在「誰拿球」（`handlingScore` 的 handle 從 70 換成 `handle.csv`），失誤公式、create、assistBoost 都不動、不重新校準，個人失誤不會變差，長人偏袒會減輕。
- 做法：`reports/sim-0.1.0+E087-handle-share/preregistration.md`（sha256 f0814db3…f4d5）。閘：m0 開關關閉逐位元、m1 npm test、m2 tov36 MAE 非劣性（90% 上界 < +0.02）、m3 E-067 b1–b3 主版與位置版。前置 p0：確認 WinImp 與 v41 路徑真的呼叫 handlingWeights。
- 狀態：2026-10-29 停在 p0、未跑（L-046）。WinImp 與 v41 路徑 `shotSelection` 都是 `volume`，第一觸球走 `opportunityPlan` 實測率，`handlingWeights` 呼叫 0 次；換 handlingScore 對結果沒有任何作用。證據 `p0.json`。
- 附帶診斷（同季，不算證據）：`diag-allocation/report.md`。模擬分球對真實前場觸球 ρ 0.60，後衛 1.14、中鋒 0.77；持球後衛給太多（SGA 1.96、Dončić 1.73），長人給太少（Gobert 0.66），Hauser 0.75。分球沒有「把不持球的人當持球者」。lead 追查：每人 usage、助攻各組誤差 ±2%，觸球差距是定義不同（模擬只算有結果的觸球），不是分球偏差；列 loop.md H8，排除。失誤「分工」新預註冊沒寫：活鏈失誤已是兩段實測率（傳球段 passStolen、終結段 terminalRisk），前提不成立（L-046 重犯）。
- 相關：E-069、E-067、E-065、R-032、L-046

### E-088
- 日期：2026-10-29
- 假設：連續上場越久，投籃命中（相對出手期望）會下降；個人下降幅度是可量的特質，跨季對得上。
- 做法：`reports/card-0.2.4+E088-stamina-decline/preregistration.md`（凍結，sha256 d140585be5391c06a7ed09bcd7a87b8b3d98819aa44df387ab01062fdb6d26d8）。2022-23～2025-26 逐球重建連續上場分鐘 s；出手殘差 r = y − p̂（每季 logistic，只用出手區域、距離、類別），扣掉節次、關鍵時刻、分差、對手強度、主客場；個人斜率 b_i（每 10 分鐘），合格人季 FGA ≥ 400 且 s ≥ 6 分鐘的 FGA ≥ 100。前置閘 p0（活路徑體力計數，只報告）、p1（上場秒數對 box MIN）、p2、p3。判定：D1 r_cs 點估計 ≥ 0.20、下界 > 0、τ² > 0 → 用個人斜率；D2 上界 < 0.10，或 τ² ≤ 0 且點估計 < 0.20 → 人人同一體力；其餘停下交使用者。β 只報告，供第 B 階段校準引擎。
- 已揭露：lead 只看過逐球資料欄位與 stints.jsonl 格式，沒算過任何體力相關數字。
- 狀態：A 階段已跑（2026-10-29，lead 在 App 自己執行），**p3 沒過 → 停下交使用者**。p1 過（四季 99.1–99.2%）；p2 樣本內過（建構上必過，單雙場外推各區 ±1.5 pp 只報告）；p3 合格人季 145／135／124／105 < 150，卡在 s ≥ 6 分鐘的 FGA ≥ 100（只有 19% 出手在第 6 分鐘後，L-049）。描述數字（不構成判定）：聯盟 β = +0.51 pp/10min（90% +0.13～+0.82），打越久投得略好不是更差；同 stint 5–10 分鐘比 0–5 分鐘 +1.26 pp；舊季 β +0.71；罰球 +1.94、失誤率 −1.51；全場累計分鐘 −0.02。現行引擎是連續 10 分鐘 −1.3～−2.2 pp。個人：r_cs 0.021（−0.094～0.138，267 組），r_sh 0.028，τ² 3.6e-5（區間含 0），b_i 標準差 6.45 pp ≈ 平均 SE 6.42 pp；舊季 r_cs 0.021（−0.044～0.083，666 組）。規則機械判定 D3，但因 p3 不生效。「該季 FGA」先用樣本內出手、後改官方 FGA，兩者 p3 與判定相同（已揭露）。報告 `reports/card-0.2.4+E088-stamina-decline/report.md`。
- 相關：R-045、R-028、R-043、L-026、L-044、L-045、L-046、L-049
- 來源：使用者 2026-10-29

### E-089
- 日期：2026-10-29
- 假設：卡片每場值 g 的分鐘權重從 mpg/36 改成飽和 W(m) = (1 − e^(−m/15)) / (1 − e^(−36/15))（R-047）後，在同一價值定義的樣本外答案（另一半 rapm1 net × W(另一半 MPG)）上不變差，線性量尺沒有大幅退步。
- 做法：`reports/card-0.2.4+E089-minutes-saturation/preregistration.md`（凍結 2026-10-29，sha256 0fa1b15c0ce11096993b224851456abdb77eb17417ecaa55dd74257207a12fbe）。`e089.py` = `e084.py`（season 目標）加 `--minutes {linear,sat15}`，只改 g 的兩處；用人回歸特徵 L = log(1 + mpg) 不動。判定：(c0) linear 重現 card 0.2.4 sha256、(c1) npm test、(u) W 單元檢查、(m1) Δρ_{N_W} 下界 > −0.02、(m2) Δρ_{N_lin} 下界 > −0.05、(m3) Δρ_{Q_W} 下界 > −0.05；evaluate 19 閘只報告。
- 已揭露：lead 看過 card 0.2.4 全部欄位與 mpg 分布，只算過曲線在固定分鐘的值，沒算過任何候選數字。
- 狀態：**採用，發成 card 0.2.5（PATCH，R-048，2026-10-29）**。先前：完成、通過；role-audit 重算通過；G5 通過；待使用者定版號（2026-10-29）。audit（派工 20261029-193348-a83b00，`audit/audit.md`、`audit/audit_recalc.py`）自寫 W／g／四答案／bootstrap，Δρ 四值與 582 人卡片 OVR 逐位重現；用人回歸輸入仍取自 e089 管線（c0 與線性 g 差 4.4e−16 框住）。唯讀合併 sha 現在重算為 2ee6b8a1…，不等於 867054e7…，因為 data/ 有 13 檔在 19:19、19:42 被別的工作改過（晚於 E-089 19:05 跑完與 ro_after），reports 唯讀目錄 0 檔比預註冊新；下次唯讀 sha 要逐檔記錄而非只記合併值。G5：使用者看過 Caruso 103 → 39、Holmgren 11 → 6、Amen Thompson 4 → 10、Maxey 12 → 26，回「還行 可以接受」。先前狀態：完成、通過，待 role-audit 與 G5（2026-10-29，App 原地執行，使用者「你自己原地做」）。原記錄：預註冊草稿，待使用者核可。(c0) linear 重現 af37ce25…7203、(c1) npm test 57/57、(u) 過；(m1) Δρ_{N_W} +0.0096 [+0.0020, +0.0176]；(m2) Δρ_{N_lin} +0.0087 [+0.0011, +0.0168]；(m3) Δρ_{Q_W} +0.0066 [−0.0005, +0.0141]。只報告：Δρ_{Q_lin} +0.0051 [−0.0022, +0.0130]；evaluate 16/19 → 18/19（carusoGate、big14of16 轉過，剩 allFourStayTop10），ρ 2K27 0.748 → 0.738、四季 RAPM 0.746 → 0.779；Caruso 103 → 39 名，Dyson Daniels 17 → 18；MIN ≥ 1000 的 ρ(mpg, OVR) 0.749 → 0.657。卡片 `ranking.csv` sha256 73b1d6353142dd86327a022a19e939833c42a0aa0c69f3377201ffe411c0050a；報告 `report.md`。唯讀目錄雜湊跑前跑後相同。
- 相關：R-043、R-047、R-042、E-084、L-026
- 來源：使用者 2026-10-29

### E-090
- 日期：2026-10-29
- 假設：卡片 13 個屬性（long、mid、short、ft、drive、foulDraw、tovSkill、pass、rebound、physique、onBall、creation、pressure）在 40／99 截斷外的原始量值跨期穩定；通過的那一端改成飽和尾巴後，卡片樣本外不變差。百分位型用 E-080 同款 99 + 26·(1 − e^(−Δ/SD))（漸近 125）／40 以下到 25；曲線型拿掉 inverse() 的截斷、沿用引擎曲線到 150／0。中段逐位元不變。help（E-080）、stamina（E-088）排除。
- 做法：`reports/card-0.2.4+E090-onball-tail/preregistration.md`（凍結，sha256 e5ac5aa92d7e2328164536542fd9716381dd9a5e567d40f773fcb313962d7351）。順序：(a0) 每個屬性找出原始量並逐人重現現行值，不過就排除該屬性 → 先定 h1 資料來源（相鄰季 > 2025-26 兩半季 > 排除）→ (h1-top／h1-bot) 上期前（後）10% 的斜率 90% 下界 > 0，每端各判 → 卡片鏈用 `--tailSource` 重建（5090），(c0) 現行值重現 card 0.2.4 sha256、(c1) npm test、(c2N)(c2Q) Δρ 下界 > −0.02、(c3) evaluate ≥ 16/19。
- 已揭露：lead 看過 onBall 2025-26 池合成值分布與前 12 名、card 0.2.4 各屬性 ≥ 99／≤ 40 人數、賽中頁 onBall 分布、引擎曲線節點；粗估過 Dort、Daniels 的尾巴值。沒看過 onBall 以外的原始量、任何跨期數字、候選卡或 OVR。
- 狀態：預註冊凍結（2026-10-29 使用者核可「核可並凍結」），派工中（role-card）
- 相關：E-060、E-080、E-088、R-022、R-044、R-045、L-026
- 來源：使用者 2026-10-29「錨點 PR1->40 PR99->99 但是目前好像單項數值不能超越這個限制封頂，很多人單防都是99 分不出勝負」→「寫預註冊」→「擴大成全部屬性」

### E-091
- 日期：2026-10-29
- 假設：賽中 OVR（2026-27）改用 card 0.2.4 當先驗（inseason 0.2.1e → 0.2.2）：predNew（用人回歸）取代 p 進 g，MPG0 改 card 0.2.4 的 mpg 欄，r_repl／錨點改 E-084 results.json；用人特徵凍結在 2025-26，不擬合任何新參數。（spec 原編號 E-089，因 E-089／E-090 已被占用，改記 E-091。）
- 做法：`reports/ovr-inseason-2026-27/e089-card024/spec.md`；`live/run_c4_live.py` 新增 CARD_MODE=024（預設）；`live/build_usage_024.py` 呼叫 e084.py 重算凍結特徵 → `live/usage-2025-26-card024.json`。資料 cutoff 2026-10-28（sha256 606333d0…80be，67 PBP）。
- 結果：(c0) CARD_MODE=022 ranking.csv 188c8bed…、no-prior.csv e061bff3… 與 live/2026-10-28 逐位元相同；(c1) npm test 57/57；(c2) 368 人有限、t1 0.0444、lastOVR 對 card 0.2.4 ovr Spearman 0.999994、最大差 0.1；(c3) probe_base_version = inseason 0.2.2，但 HTML 不含字面「card 0.2.4」（season_nav.py 重寫來源文字，頁面顯示「先驗 正式卡 0.2.4」，禁改檔，待 lead 決定）；(c4) 582 人 ovr／mpg／gRepl 逐格重現、r_repl 與錨點差 0.0。0.2.1e→0.2.2：|ΔOVR| 中位數 2.80、最大 15.8、>10 分 15 人，最大 10 人幾乎全是用人項（Banchero +15.8、Keyonte George −15.6、Wells −15.0）；年輕 ≤23 中位數 +1.10、老將 ≥31 −0.60；前 20 進 Harper、出 Markkanen。MPG0 口徑差 >3 者 81 人（卡內 205）。r_repl −1.7593→−1.2724；錨點 PR1/50/99 −0.756/1.050/4.744 → −0.542/0.885/3.178。
- 狀態：完成，已採用並發布（2026-10-29 lead 審過：c0 兩檔 sha256、c2 lastOVR 對 card 0.2.4 最大差 0.1 自行重算，diff 已讀，npm test 自跑 57/57；(c3) 字面字串不過屬驗收寫法問題，頁面版本欄正確，接受）。完整發布 inseason 0.2.2a（gh-pages b39f4a3）；更新說明加「新賽季 0.2.2」一格後 --shell 重發（a9681d6）。注意：重抓後同截止日 2026-10-28 的資料 sha256 變成 31170cdc…（原 606333d0…），同 handoff 已記的「同截止日 sha 不同」問題，未查。
- 相關：R-044、E-074、E-084、R-019、R-031、L-026、L-050
- 來源：使用者 2026-10-29「將新賽季也跟上0.2.4」

### E-092
- 日期：2026-10-29
- 假設：教練看得到誰累了會掉，所以「以強度來看上場被限制」或「一次連續打不久」的人，整群合起來看連續上場越久退步得比較多。把個人斜率（E-088 量不出）改成整群交互作用，樣本量夠。
- 做法：`reports/card-0.2.4+E092-stamina-usage/preregistration.md`（凍結 2026-10-29，sha256 34f2ad4c3f970eee06bdc4c1b7a36e29973f0182f6b2b1b873c4416fe1978e46）。12 季合併，人群 GP ≥ 30、MPG ≥ 10、校正場次 ≥ 25；校正場次排除缺陣 ≥ 3 場後回來的前 3 場、犯規 ≥ 5、終場分差 ≥ 20。強度 a＝收縮 GmSc/36（k = 500 分鐘）。S1＝MPG_adj 對 a、a²、身高組、隊內同組較強人數、季別的殘差；S2＝完成 stint 平均長度對 MPG_adj、MPG_adj²、季別的殘差。r′ 沿用 E-088；人季固定效果 `r′ ~ s/10 + (s/10)·z_S`，γ 場次群集 bootstrap 2000 次。前置閘 p0（加 stint 輸出後事件檔不變）、p1（每季人群 ≥ 250）、p2（S2 每季合格 ≥ 200）。判定（D3 反向優先）：有效＝γ 95% 下界 > 0 且 r_cs(S) ≥ 0.5，至少一個有效 → D1；兩個 90% 上界都 < 0.30 pp/10min/SD → D2（上場時間和打久會不會掉無關，交使用者選人人 70 或遊戲設計規則）；任一 95% 上界 < 0 → D3 反向；其餘 D3。
- 已揭露：lead 看過 E-088 全部結果（含 b_i 與 MPG 相關 −0.02、身高分組 β），只算過曝光量（每季人數 349–387、第 6 分鐘後出手 17–24%）與 γ 的粗估標準誤（12 季約 0.13）；沒算過任何 S 或交互作用。可偵測最小效果約 0.36 pp/10min/SD，引擎內建差距約 0.17，量不出引擎那麼小的差距。
- 狀態：**完成，判定 D2**（2026-10-29，lead 在 App 執行；原記錄：預註冊凍結，待執行）。p0 12 季事件檔與 E-088 逐位元相同、p1／p2 每季 312–345 人；用同一 r′ 重算 E-088 主季 β 完全相同。S1 γ −0.26 pp/10min/SD（90% −0.47～+0.01，95% −0.52～+0.06），r_cs 0.64；S2 γ −0.08（90% −0.27～+0.09），r_cs 0.40；兩個 90% 上界都 < 0.30 → D2：上場時間多寡和打久會不會掉無關。S1 高的是防守側翼（Murray、Camara、Bridges、Brooks），低的是數據好的替補（Mamukelashvili、Huff），量到的是教練看重防守／角色。依 S1 三分組的 β 都是正的（+1.19／+0.46／+0.44）。執行中發現 2020-21 起節間換人記在下一節 0:00，造成每場約 8 段長度 0 的假 stint（L-052），凍結的 S2 有包含；事後去掉重算 γ −0.10（上界 +0.08），判定不變（`posthoc_s2.json`，只報告）。報告 `reports/card-0.2.4+E092-stamina-usage/report.md`。待使用者照 §7 D2 選人人 70 或遊戲設計規則。
- 相關：R-045、E-088、F-036、F-037、L-026、L-045、L-049、L-052
- 來源：使用者 2026-10-29「還是我們看強度和上場時間的關聯？…」→「GO」

### E-093
- 日期：2026-10-29
- 假設：體力退步可能不在命中率，而在影響力。場上的人連續打越久，球隊每百回合淨效率變差（可能在防守）；E-092 的 S1／S2 高的人掉得比較少。
- 做法：`reports/card-0.2.4+E093-stamina-impact/preregistration.md`（凍結 2026-10-29，sha256 4e7723e907bd12d6af64fe4c7f2b34f11042bbed3ca164e6cf78de55b06ac3a2）。資料用 RAPM 的陣容段落 `reports/defense-seventh/<季>/stints/stints.jsonl`，10 季（缺 2021-22、2025-26）；先刪長度 0 的段落再串 stint，每節 s 歸零，取段落中點。每季回合加權 RAPM（λ = 3000）加 F_off／F_def（場上每人 s/10 的和），以及 S1、S2 交互項 G（z 取自 E-092）；控制節 × 2 分鐘時段、分差組；排除第 4 節分差 ≥ 20。10 季以回合數加權合併，場次群集 bootstrap 1000 次。判定：聯盟 L-D（φ_D 95% 下界 > 0）、L-O（φ_O 95% 上界 < 0）、L-0（兩者都不成立且 Δ = φ_D − φ_O 的 90% 上界 < 0.60，即引擎大小）；個人：有效＝γ 95% 下界 > 0 且 r_cs ≥ 0.5，無關＝兩個 γ 的 90% 上界都 < 0.40 分／百回合／SD，反向優先。前置閘 p0（stint 對 E-092 每季吻合 ≥ 98%）、p1（每季回合 ≥ 18 萬）、p2（合成資料植入值回收）。
- 已揭露：lead 看過 E-088、E-092 全部結果與既有 RAPM；沒算過任何跟 s 有關的得分或失分。試算（`feasibility.py`，只用曝光量）：p0 吻合每季 99.85–99.95%（已看過），每季 21–25 萬回合；解析標準誤（假設每回合變異 1.25，不計群集）φ_O／φ_D 0.12、Δ 0.22、γ S1 0.14／S2 0.12。引擎換算 φ_O ≈ −0.6、φ_D = 0；個人體力差距約 0.07／SD，量不出。
- 狀態：預註冊凍結，待執行。**2026-10-29 跑完（lead 在 App，擬合在 5090）**：p0–p2 全過；聯盟照字面 L-D（φ_D +1.26 [+0.96, +1.59]），但 φ_O +4.08、Δ −2.82（打越久球隊淨效率反而好），個人 S1 γ +0.63（有效）、S2 γ −0.47（**反向 → 停下交使用者**）。穩健性翻面（R7 φ_D −2.49、R2 −0.97、2022-25 −0.39），判定被換人選擇效應主導，不能當體力證據（F-041、L-056）。lead 建議結案：體力不從資料來，照 E-092 D2，不加防守衰退。報告 `report.md`。
- 相關：R-045、E-088、E-092、F-036、F-037、F-041、L-026、L-045、L-049、L-052、L-056
- 來源：使用者 2026-10-29「如果不是命中率掉，而是影響力 或是正負值？」→「寫預註冊」

### E-094
- 日期：2026-10-29
- 假設：defenseBonus 的 taper（PR 90→96 線性歸 0）會讓屬性沒到頂的人靠加成跳過屬性頂尖的人（R-049：Wagner 跳過 Wembanyama、Cade）。T：w 換成天花板 bonus = min(max(0, centeredD), max(0, T96 − pred0))，加成最多推到 PR 96 那條線；S：centeredD 改讀 2025-26 單季防守 RAPM（和 card 0.2.4 的單季目標一致）；主候選 TS。三者樣本外都不變差。
- 做法：`reports/card-0.2.5+E094-defense-ceiling/preregistration.md`（凍結 2026-10-29，sha256 8878d8167be183170a43b81eebd28f406e6a27e563a0263755b4069495310526）。calibrate-wing.py 加 `--bonusShape`、`--defWindow`，跑 off／T／S／TS × primary／fitA／fitB，e094.py＝e089.py sat15 加 `--cardDir`。判定：(c0) off 重現 card 0.2.2 P1 三張卡與 card 0.2.5 sha256、(c1) npm test、(f1) 天花板結構檢查、(f2) 單季 D 對得上、(m1) Δρ_{N_W} 下界 > −0.02、(m2) Δρ_{Q_W} 下界 > −0.05、(m3) Δρ_{N_lin} 下界 > −0.05。R-049 名單只報告，交 G5。
- 已揭露：lead 看過 card 0.2.5 全部欄位、RAPM 合併與單季名次（Wagner、Wembanyama、Cade、Tatum、Banchero、魔術隊）、賽中頁前 10；沒算過任何候選數字。Tatum（pred0 第 42、522 分鐘）預期修不到。
- 狀態：預註冊凍結（2026-10-29 使用者核可「我核可，你就原地开始做」）；**2026-10-29 跑完，T、S、TS 三組判定全過（通過）**。c0 逐位元重現、npm test 57/57、f1 違規 0、f2 差 0；TS Δρ_{N_W} +0.0058 [−0.0036, +0.0156]、Q_W −0.0062 [−0.0148, +0.0022]、N_lin +0.0057；evaluate 18/19 → 19/19（三組）。R-049 只修到一半：Wagner #5 → T #9／S #11／TS #10，仍贏 Cade（T #17、TS #14）與 Tatum（#32–37），原因是 align（F-038）。副作用在 S：Herbert Jones #12 → #60、Embiid #13 → #35、ρRAPM 0.779 → 0.769；T 單獨副作用小、ρRAPM 0.783。lead 建議只採 T；待使用者選組、role-audit 重算、G5、版號（R-019）。報告 `report.md`，唯讀 23858 檔 0 變。
- 相關：R-049、R-042、E-084、E-089、E-079、L-026、R-007、F-038
- 來源：使用者 2026-10-29「寫 spec 修斷崖」

### E-095
- 日期：2026-10-29
- 假設：新賽季 OVR（inseason 0.2.4a，原名 0.2.2a）改用 card 0.2.5 的分鐘權重 W(m) = (1−e^(−m/15))/(1−e^(−36/15))（取代 m/36），並換成 card 0.2.5 的 ranking 和錨點之後，追蹤整季答案的能力不會變差。不主張變準：W 和線性的答案卡不是同一個目標，最多 PATCH。
- 做法：`reports/ovr-inseason-2026-27/e095-card025-minutes/preregistration.md`（原編號 E-094，和防守天花板重號，2026-10-29 改號）。`run_c4_live.py` 加 CARD_MODE=025（預設仍 024）；新回測 `backtest_e095.py` import `backtest_e064.py`，副版 RG1 加 `--minutes {linear,sat15}`，錨點與答案卡同式重算。前置：(c0) linear 重現 E-064 RG1、(c0L) 線上 024 不變、(c1) npm test、(u) W 單元值、(L1) 025 的 ref 轉換重現 card 0.2.5 ovr（每人差 ≤ 0.1）。判定：(1) RG1-sat15 對 W 答案卡過 v5 V1∧V2；(2) Y5、Y6 × N=3/5/10/20 每格 MAE 差 ≤ +0.05。(1) 過 (2) 不過時交使用者選。
- 已揭露：lead 看過 E-089 卡片端全部結果、線上 0.2.2a、E-064 和 E-091 結果，以及 `backtest_e064.py` 的結構；沒看過任何用 W 算的新賽季數字。
- 狀態：預註冊已凍結（2026-10-29，使用者「核可」），sha256 66000292…db71（`preregistration.sha256`）；凍結前只把採用後版號改成 inseason 0.2.5（R-050），判定沒動。2026-10-29 跑完：前置 (c0)(c0L)(c1)(u)(L1) 全過；(1) 過（RA 與字面 A 兩種基準都過）；(2) **不過**，8 格 MAE 差 +0.19～+0.29（門檻 ≤ +0.05），合併 +0.24 [+0.16, +0.32]，低分鐘三分位增幅最大（約 +0.4）。線上頁 024→025：|ΔOVR| 中位數 1.4、最大 6.8，Caruso 85→33 名。role-audit 獨立重算 8 格差 ≤ 1.4e-5，結論成立（`audit/audit.md`）。依預註冊不自動採用，交使用者選；**使用者選 A 採用（R-052）**，2026-10-29 發布 inseason 0.2.5a（gh-pages 0e9836d）。(1) 基準沒寫明見 L-053。
- 相關：R-047、R-048、R-019、R-023、R-031、E-064、E-089、E-091、L-026、L-034、L-048、L-050、L-053
- 來源：使用者 2026-10-29「曲線的部分都完成了嗎」→「寫預註冊」

### E-096
- 日期：2026-10-29
- 假設：屬性 99 以上改用 99 + 51·(1 − e^(−Δ/(1.96·SD)))，理論上限 150（命中率型在 100% 時剛好 150）；中／近距離另加量價屬性 midValue、shortValue（出手量 × 超出替補的命中率，照 E-057 三分），只顯示不進 OVR。取代 E-090 的 125 上限與曲線外延。
- 做法：`reports/card-0.2.5+E096-tail150/preregistration.md`，基準 card 0.2.5，判定 c0–c3 同 E-090＠0.2.5；量價屬性先過 h1v 才開尾巴。
- 已揭露：見預註冊 §0（lead 看過 E-090 全部結果、手算過 Giannis／Toppin／Hayes 的近距離、看過少數人中距離出手數）。
- 狀態：進行中（預註冊凍結 2026-10-29，使用者「你就先照那个方法做」，sha256 8deade79…09e1）
- 相關：E-090、E-057、R-020、R-024、L-026、R-007
- 來源：使用者 2026-10-29「用标准差是对的…封顶就设置在150」「中距离跟近距离…既要看产量，也要看命中率」

### E-097
- 日期：2026-10-29
- 假設：E-096 之上兩處改動：(1) mid、short 收縮先驗從位置平均改成聯盟平均（命中率與量價屬性都改，使用者「每個位置都應該一樣」）；(2) 所有屬性頂端的尺從全池 SD 改成池內前 10% 的 SD（量價分布右偏，全池 SD 把頂端距離放大，Giannis shortValue 137）。
- 做法：`reports/card-0.2.5+E097-topscale/preregistration.md`，基準 card 0.2.5，判定 c0–c3 同 E-096；mid／short 的 h1、h1v 用聯盟先驗重跑；e097s／e097p 拆解、e097v 只報告。
- 已揭露：見預註冊 §0（lead 看過 E-090、E-096 全部結果與 shortValue 分布）。
- 狀態：不採用（2026-10-29，使用者「我们先不采用」；預註冊凍結 sha256 f395ebc3…093d25df）。判定 c0–c3 全過（c2N −0.0047 [−0.0087, −0.0007]、c2Q −0.0043 [−0.0078, −0.0010]、evaluate 19/19），但兩個主目標都是反效果：Giannis shortValue 137.2→140.1；Kessler（整季 0 次中距離）mid 99→142.7，全聯盟第一，Gafford 129、Poeltl 120。原因：改動二的尺必然比全池 SD 小（L-057）；中鋒中距離偏高來自 PBP 把補籃標成 Mid-Range（F-042），不是位置先驗（L-058）。中距離 99 並列 13→0。報告 `reports/card-0.2.5+E097-topscale/report.md`，診斷 `diag/`。
- 相關：E-096、E-090、E-057、L-026、R-007
- 來源：使用者 2026-10-29「命中率应该不需要依照位置做加权」「137…有点太高了吧」「A」「中间点不能用中位数」「由你这边本地开始做」

### E-098
- 日期：2026-10-29
- 假設：長人偏袒（E-067 的 S）有一部分來自引擎裡長人沒有短處可被打。對位照陣容順序固定，沒有換防；持球者切入也不看防守者。加入以下兩件事，WinImp 的 S 會下降，且球隊層與卡片舊量尺不變差：(i) 擋拆換防，機率 0.12，換到高 ≥ 4 吋的防守者時用他的 switchD；(ii) 切入對抗，改成 drive − 防守者 driveD。driveD、switchD 從 matchups 個人殘差收縮而來，不分位置。
- 做法：`reports/E098-defense-four/preregistration.md`（第一階段；四項設計見同目錄 `design.md`）。判定 (h1') 穩定度 ≥ 0.30、(g0)、(g1)、(b3) S 兩方向下降、(t1)、(c2Q)、(c3)。
- 已揭露：lead 看過欄位名稱、F-030、E-080 全部結果；沒看過任何對位殘差、driveD／switchD 值或換防率。
- 狀態（原）：進行中（預註冊凍結 2026-10-29，sha256 81f974cc…47a9，使用者「原地開始做」；基準 sim 0.1.0＋card 0.2.3 卡片鏈，沿用 E-080 基準產出；E-076 未升版，若之後升版要在 0.1.1 重跑 g0／b3／t1）
- 結果：(h1') 兩分量都過：driveD 相鄰季 r̄ 0.764（k 333）、switchD 0.872（k 71）；但兩者都有強位置訊號（中鋒 46–57、側翼 82–98），可能量到角色而非能力。L-046 p0（3 人×16 samples，5090）：旗標關與 E-080 基準逐位元相同；全員 driveD=40、引擎內強制 driveDEff=40 都和基準逐位元相同，對照組全員 onBall=40 變動 46.5–47.5。→ §4 切入對抗兩式（:245 犯規、:368 籃下）在活的 WinImp 鏈是死碼（v45 fineSourcePlan 覆寫出手分布；有 freeThrowsPerAttempt 就改走 ftaRatio）。換防未實作、全量模擬未跑。報告 `reports/E098-defense-four/report.md`、`p0.json`、`h1.json`；worktree `basketball-autochess-e098` 未 commit。
- 狀態更新：前提不成立，停止（2026-10-30；不是閘門未過，b3 等判定沒有數字；等使用者決定另寫預註冊）
- 相關：E-080、E-076、E-067、E-060、F-030、F-031、R-022、R-051、R-053、L-026
- 來源：使用者 2026-10-29「护框墙的人就让他们护框墙……钉防外线的速度可能会比较慢」「一对一单防那个切入强的人也是他们的劣势」「网站上就显示四个数字，外线防守、内线防守、换防跟协防」

### E-099
- 日期：2026-10-29
- 假設：E-067 的長人偏袒量尺 S 用勝負計分、區間只重抽球員，模擬 draws 雜訊（F-040）沒算進去。改用既有 checkpoint 裡每格的分差（M）或運氣修正後分差（X）計分，並讓 bootstrap 同時重抽 480 個 (opp, i) 格子與球員，配對 ΔS 的 σ16 會縮到 ≤ 5，往後每輪 S 比較才有效力。
- 做法：`reports/bias-check-E099-scale/preregistration.md`。全部從 legacy／E-076 dedup／dedup-all／E-085 centered 四份 checkpoint 計算，不跑新模擬。g0 必須逐位重現 winimp.csv 與 E-067 baseline.json；計分方式只用雜訊（12 格平均 σ16(ΔS)）選，最小兩者相差 < 5% 取 X；判定只有 (n1) σ16 ≤ 5，不判 b1–b3、不改 E-076／E-085 判定。
- 已揭露：lead 看過四版本勝負計分下所有 S／ρ／區間與 F-040 雜訊；沒看過任何分差計分下的數字。
- 結果：g0 過（winsPer82 全員差 5e-6，E-067 baseline.json S／區間逐位重現）。雜訊選出 X（運氣修正後分差）：12 格平均 σ16(ΔS) W 39.2 → M 25.1 → X 19.4（縮 51%）。(n1) 不過：19.4 > 5，壓到 5 要 N ≈ 240 個樣本（現 16）。聯合重抽（球員＋480 格）後 W 計分的配對差 bootstrap SD 從只重抽球員的 6.3 變 36.0（約 6 倍），配對差排除 0 的格數 8/12 → 0/12；X 下 3/12（都是主版 legacy−centered）。X 與 W 的球員名次 Spearman 0.77–0.93，位置版在 X 下四版本 S 全為負（−40 到 −17），W 下全為正（F-044）。主版在 X 下 legacy S 99.1 [60.5, 128.6] 仍明顯偏袒長人。報告 `reports/bias-check-E099-scale/report.md`，數字 rescore.json／noise.json／choice.json，約 10.7 秒跑完。
- 狀態：完成（2026-10-30，預註冊凍結 2026-10-29 sha256 3986595c…2d8d；n1 不過，等使用者決定加樣本與以 X 為準）
- 相關：E-067、E-076、E-085、E-086、F-040、L-054、L-026、R-054、loop H9
- 來源：使用者 2026-10-29「先修」（在「修量尺 vs 直接進 R-041 第三步」之間選修量尺）

### E-100
- 日期：2026-10-30
- 假設：防守加成的 D 改成近期加權合併單季 RAPM，w_s = 0.75^(T−s) × a_s，a_s =（有出賽 + 教練不用）÷ 在名單上場次；傷停、輪休、疑似輪休降權，教練 DNP 不降（R-036 分類，照 E-075）。主候選 B2 比只衰減（B1）與現行四季等權聯合擬合（B0）更能預測下一季 stint。
- 做法：`reports/card-0.2.5+E100-defense-recency-injury/preregistration.md`（草稿）。缺賽原因碼只有 2019-20 起有（liveData 探測，更早回 403），補抓 2019-20、2020-21、2022-23..2024-25。第一階段舊季前瞻：目標 2022-23、2023-24、2024-25（三季窗口），(P1) MSE(B2)−MSE(B1) 上界 < 0、(P2) MSE(B2)−MSE(B0) 上界 < 0；第二階段卡片層以 E-094 T 為基準（c0、c1、f3、m1–m3）；第三階段 2026-27 季末確認（同 E-083 開工條件）。
- 已揭露：見預註冊 §1（E-094、E-079 全部結果；只探測過每季一場 box 的狀態碼）。
- 狀態：草稿（2026-10-30）；同日本機抓完 box score、數過曝光量並填 p2 門檻（2019-20 只有 76.4% 場次；三個舊季教練類碼改歸 C），等使用者核可凍結；使用者核可（G 聯盟／DND 碼歸 C、2019-20 覆蓋 75%），預註冊凍結 2026-10-30 sha256 941f621f…3f73；第一階段完成：P1 過（B2−B1 −0.254 [−0.370, −0.140]）、P2 沒過（B2−B0 −0.459 [−1.023, +0.108]），B3−B2 +0.042 量不出差別。照預註冊停在第一階段，等使用者決定要不要做第二階段（F-045，`report.md`）
- 相關：R-049、R-036、E-094、E-079、E-083、E-075、L-026、L-049
- 來源：使用者 2026-10-29「我們應該用遞減的吧…被教練 DNP 的話不算，必須是真的受傷」、2026-10-30「照預設」

### E-101
- 日期：2026-10-30
- 假設：E-096 之上三處改動：(1) PBP 分區修正，Mid-Range 但 shotDistance < 8 呎的出手（F-042 的補籃、補扣）改歸近距離，mid、short 收縮改向聯盟平均（R-055）；(2) 百分位、r99、r01 改對 2022-23 到 2025-26 四季合併池計算（R-056）；(3) 頂端的尺 S = max((r99 − r90)/1.044, SD_pool)，只壓縮不放大（合成分布方向自查見預註冊 §0，L-057）。
- 做法：`reports/card-0.2.5+E101-crossera/preregistration.md`，基準 card 0.2.5；判定 c-pre（分區一致性）、c0–c3 同 E-096，加 c4（> 140 的值 ≤ 2 個）；e101z（只修分區）、e101g（純差距尺）、e101w（長窗）只報告。
- 已揭露：見預註冊 §0（lead 看過 E-090、E-096、E-097 全部結果與四季 PBP 依距離的聯盟合計；沒算過任何跨季 PR90／PR99／差距，也沒算過修正分區後的球員值）。
- 狀態：通過，role-audit 重算成立（2026-10-30，`audit/audit.md`，抓到報告基準混用與 fitA／primary 兩處，已更正，L-060）；使用者 2026-10-30 選「A 進 G5」，G5 名單（`g5/g5-list.json`）使用者 2026-10-30「A」通過，**採用為正式卡 card 0.2.6（PATCH，R-060）**，`reports/card-0.2.6/`，2026-10-30 commit、push 並部署名單頁。原判定 2026-10-30；預註冊凍結 sha256 44d1eb0a…40f3e5，使用者「你執行」）。c-pre mid +0.0002／short +0.0001；c2N −0.0027 [−0.0069, +0.0015]、c2Q −0.0032 [−0.0067, +0.0004]；evaluate 19/19；> 140 的值 0 個。中距離準度 = 99 的人 13→1（Kessler 99→60.9，0 投），Giannis shortValue 137.2→129.0（唯一 > 120）。副作用：OVR 重擬後 mid 每 10 分價值 .206→.137、long .436→.382、short .389→.531（primary），Curry 第 23→32、Brunson 第 51→58、Duren 第 53→37（對 card 0.2.5）；對 card 0.2.5 有 303 人移動 ≥ 5 名。mid h1 頂底都不開（n=5）。foulDraw／drive／onBall 是每季標準化值，跨季池對它們無意義（F-046）。報告 `reports/card-0.2.5+E101-crossera/report.md`。
- 相關：E-096、E-097、F-042、R-055、R-056、R-060、L-057、L-026
- 來源：使用者 2026-10-30「我们可以用很多个年份的 PR 90到99来看」「先把它合并到近距离会比较好」「你執行」

### E-102
- 日期：2026-10-30
- 假設：E-099 顯示 X 計分下 16 樣本的配對差雜訊 σ16(ΔS) = 19.4 名次，要 N ≈ 240 才到 5。把 legacy 與 E-076 dedup 的 WinImp 樣本從 16 加到 240（同 seed 公式，i = 16..239），合併後 σ240(ΔS legacy − dedup) ≤ 5，往後版本比較才有效力。
- 做法：`reports/sim-0.1.0+E102-winimp-240/preregistration.md`。runner 複製自 E-076 core 加 sampleStart，5090 12 workers 依序跑 legacy、dedup；判定 (g0) 10 人重跑 i=0..15 逐位同舊 checkpoint、(n1) 6 格平均 σ240 ≤ 5；(n2) 只報告兩版本 X 計分的 S、聯合區間、ΔS。不判 E-076 b1–b3、不決定升版。
- 已揭露：lead 看過四版本 16 樣本下 W／X 的全部結果（E-067、E-099）；本實驗不選參數、不選版本。
- 狀態：預註冊凍結（2026-10-30，sha256 dfb80252…a8de）；同日全量啟動前追加修訂 A（使用者選第三案：只跑 avg、補到 N = 60、nice 19、8 workers，(n1) 改成 σ60 ≤ 10；sha256 41283531…8627），執行中（5090）。GPU 不採用：引擎 8k 行 JS 且執行時打補丁、分岔密集、重寫後無法逐位重現舊樣本。執行註記（2026-10-30）：預註冊漏寫 dedup 帶 E-076 候選的校準 orbLogitDelta −0.135（E-076 run-meta）；delta 0 時 g0 對不上，補上後 g0 10/10 逐位一致，lead 接受（屬候選定義，非事後選參）。2026-10-30 01:05 啟動 5090 `/home/kojiek/side_projects/basketball-e102-20261030`，legacy 接 dedup 一條 nohup 鏈，實測約 8.3 秒／人／樣本，預計 dedup 10/30 11:00–16:00 完成。**完成（2026-10-30 11:20）**：(g0) 過、(n1) 過（σ60(ΔS) X 8.18 ≤ 10；到 5 需 N ≈ 161）。X 計分 ΔS legacy−dedup 19.8／19.8／16.7，聯合區間三格都排除 0；S 仍大、前 20 中鋒 10 vs 答案 4（F-068）。報告 `reports/sim-0.1.0+E102-winimp-240/report.md`；等使用者：E-076 G5、量尺定案、下一步
- 相關：E-099、E-076、E-065、F-043、F-044、R-054、L-054、loop H9
- 來源：使用者 2026-10-30「那我們就加大樣本吧，然後加完你跟我說預計的運算時間要多久」

### E-103
- 日期：2026-10-30
- 假設：照 R-057，體力＝MPG − 0.3·max(0, 年齡−33) 的百分位（老將只輕扣：留得住的人體力本來就好）（OVR 改讀舊公式欄 `mpgRank`，數字不變）；疲勞消耗＝時間＋觸球（持球者與對位防守者各記一次，平均工作量時動作佔 1/3），累了掉 physique、drive、onBall、help（×(1−0.30f)），投籃小掉（×(1−0.10f)）。疲勞速度 λ 只用真實 stint 長度校準（heuristic 模式、教練換人在迴圈裡），要求 stint 長度（T1）、上場分鐘（T2）、從外面看不出退步（T3 β_sim ≥ −0.50 pp/10min）同時對上。
- 做法：`reports/sim-0.1.0+E103-stamina-workload/preregistration.md`（草稿）；`opt.fatigueModel` 預設 legacy 逐位元重現；校準 seed 20261030–33、驗證 seed 20261040–47，在 5090 跑。編號 E-102 已被 `reports/sim-0.1.0+E102-winimp-240/` 使用。
- 已揭露：見預註冊 §1（E-088／E-092／E-093 全部結果、真實 stint 長度分布＝T1 目標；沒跑過任何新模型模擬，也沒看過現行引擎 heuristic 模式的 stint 分布）。
- 結果：前置閘 p0、c0（逐場雜湊相同）、g1（57/57）、o1 卡片側（ranking.csv 73b1d635…050a 不變）、h0 過。**T1 失敗**：校準組沒有任何 λ 讓每項 ≤ 1，λ*＝0.5；驗證組 stint 中位數 ≥32 組 4.17（真實 7.00）、24–32 組 3.35（5.95），≥10 分鐘比例 0.5%（19%）。legacy 本身就是 3.97／3.24，換人太快是教練邏輯造成，不是疲勞速度（F-052）。T2 過（MAE 0.718 vs 0.731），T3 過（β_sim +0.26 [−0.95, +1.43]，legacy −1.88），但 R4 顯示 λ=0.5 的真實投籃疲勞本身就很小（+0.10）。觸球多的人 stint 沒比較短（≥32：4.14／4.17／4.19）。R5 淨勝分 RMSE 2.53→2.65 不顯著；R6、賽中 o1 沒跑。報告 `reports/sim-0.1.0+E103-stamina-workload/report.md`；程式在 worktree `D:/Projects/CODING/ba-e103` 分支 e103-stamina-workload，未 commit。
- 狀態：不採用（2026-10-30，T1 失敗依 §4.2 停下；預註冊凍結 sha256 cc389172…74a3，跑後相同）；下一步：使用者 2026-10-30 選 A（改換人邏輯），見 E-109
- 相關：R-057、R-045、E-088、E-092、E-093、F-036、F-041、L-056、L-052、S-002、S-003、L-026
- 來源：使用者 2026-10-30「分鐘和年齡作為體力…網站可以不顯示」「体力还是真实存在的…教练会换人」「照寫」

### E-104
- 日期：2026-10-30
- 假設：防守 D 改成四季聯合擬合加「逐場遞減」權重（聯盟時間，每季攤成 82 格，最近一場 1、四季前第一場 0）。L 線性 w = u、Q 二次 w = u²。不靠缺賽原因碼，只看有上場的片段。第一階段只防預測變差；第二階段看卡片名次是否比較符合人的印象（使用者：近期偏誤合理，波動大沒關係），由使用者在 G5 選組。
- 做法：`reports/card-0.2.5+E104-defense-pergame-decay/preregistration.md`（草稿）。第一階段目標 2022-23..2025-26、四季窗口，對 B0 分更準／打平／變差三級，(a1)(a2) 不是變差才進第二階段；第二階段以 E-094 T 為基準，TL、TQ × primary／fitA／fitB，m1–m3 照 R-042 權衡，R-049 不退步；J75（E-083 按季 0.75）只報告。
- 已揭露：見預註冊 §1（E-100、E-079、E-094 全部結果；沒算過任何逐場加權的擬合）。
- 狀態：草稿（2026-10-30）→ **凍結並跑完、等使用者 G5**（2026-10-30）。凍結前使用者「B」把曲線組 Q 改成半衰期 82 場 H（組名 TL／TH），sha256 4a470962…dd77。第一階段：L 對 B0 打平 −0.267 [−0.608, +0.100]（a1 過），H 變差 +0.860 [+0.384, +1.355]（a2 沒過，不進第二階段）。第二階段 TL 對 T：c0／c1／f1／f2 過，m1 +0.0052、m2 +0.0012、m3 +0.0053 皆過，evaluate 19/19；r1 沒過（Wagner #9、Wembanyama #4、Cade #17→#14），原因 F-047（封頂）。報告 `report.md`。
- 相關：E-100、F-045、F-047、E-079、E-083、E-094、R-049、R-058、R-042、L-026
- 來源：使用者 2026-10-30「只要用他有上場的時候來看就好…用每一天當做遞減的權重」「照預設的寫」「同時試兩個 arm…線性遞減…曲線遞減…更符合人類的期待」

### E-105
- 日期：2026-10-30
- 內容：名單卡片「近 5 場」加單場貢獻值（使用者選 A：自己擬合 box → RAPM）。每 36 分鐘 PTS、FGA、FTA、FG3M、OREB、DREB、AST、STL、BLK、TOV、PF 對 rapm1-A net 做加權最小平方（權重 poss，A 半上場 ≥ 300 分鐘，356 人；A／B＝int(GAME_ID)%2，同 E-081）。沒有可調參數。只顯示，不進 OVR。
- 做法：`scripts/fit_game_contribution.py` → `reports/game-contribution/{weights.json, baseline-2025-26.json, report.md}`；`scripts/enrich_roster_viewer.py` 每場算貢獻值、近 5 場用合計換算、和 2025-26 整季比（±1 上色），換算 OVR 傾向：把差值當 pred 變動，照 card 0.2.5 錨點（E-089 report_only.card.new）與 W(MPG) 換算，正文只寫升／降／持平與「明顯」（≥ 2.4），換算 OVR 放 tooltip（照 5 場直接換算會到 150，太誇張）。
- 結果：B 半樣本外，貢獻值對 rapm1-B 加權 r 0.444、Spearman 0.394；Game Score／36 只有 0.361／0.291；A 半 RAPM 本身預測 B 半 0.462／0.405（穩定度上限）。正負值／36 對 B 半 RAPM 0.868 不算數：是同一批比賽算的。樣本內 0.529 只供參考（R-007）。權重：STL +1.00、TOV −0.95、FG3M +0.30、AST +0.29、BLK +0.27、PTS +0.26、FGA −0.23、截距 −3.15。2025-26 近 5 場差值 SD 1.21（場均 ≥ 20 分鐘 291 人），2026-27 開季全聯盟分鐘加權平均差 −0.35。
- 狀態：已上線（2026-10-30）
- 相關：E-081、E-089、R-007、R-028、L-026
- 來源：使用者 2026-10-30「把它每一场比赛的贡献值把它列出来。这个准不准是一回事」→「先用 A」

### E-106
- 日期：2026-10-30
- 假設：防守加成拿掉「屬性分位置」打折（taper／ceiling），改成 defenseBonus = max(0, centeredD)，防守越好加越多；RAPM 名次封頂、align、回合門檻不動。整體一致性不明顯變差，屬性和防守都頂尖的人（Wembanyama）分數上升。lead 事前預期 Wagner 會往上、r1 大概率不過。
- 做法：`reports/card-0.2.5+E106-defense-bonus-monotone/preregistration.md`（2026-10-30 使用者「A」凍結，sha256 437ad6f2…a195）。組別 T（E-094 T 基準）、U（pooledD、不打折）、UL（E-104 逐場線性 D、不打折）× primary／fitA／fitB；m1–m3 照 R-042 權衡，r1 照實記錄。
- 已揭露：見預註冊 §1（card 0.2.5、E-094、E-104 全部結果；沒算過不打折的任何結果）。
- 結果：c0／c1（npm 57/0）／u1／f2 全過，evaluate T／U／UL 都 19/19，唯讀 732 檔不變。
  - U 對 T：m1 +0.0009 [−0.0015, +0.0032]、m2 −0.0015 [−0.0040, +0.0007]、m3 +0.0009 [−0.0016, +0.0033]；ρ2K 0.7351 → 0.7384；r1 沒過：Wagner 9 → 3、Wemby 4 → 1、Cade 17 → 19。
  - UL 對 T：m1 +0.0067 [+0.0018, +0.0118]、m2 +0.0011、m3 +0.0069；ρ2K 0.7346；r1 沒過：Wagner 4、Wemby 2、Cade 17。
  - Cade 的加成被 RAPM 名次封頂切回（RAPM #54），Wagner（RAPM #7）被放行到 Wemby 的 per36 值（F-049）。Curry 21 → 31、Luka 3 → 8、Durant 11 → 21；頂端 OVR 壓縮（SGA 113.5 → 102.1）。總評 2/5，`report.md`。
- 狀態：已跑（2026-10-30）；G5 使用者選 UL，R-058 放寬成只要不贏 Wemby（R-061），UL 放寬後 r1 成立。未進正式卡：要在 card 0.2.6 上重做
- 編號：另一個 session 同日也用了 E-106（偏袒分量帳，下一條）。本條較先寫、預註冊已用此號凍結，所以不改號；引用時寫「E-106 防守加成」以區分。
- 相關：E-094、E-104、F-038、F-047、R-049、R-058、R-042、L-026
- 來源：使用者 2026-10-30「不是應該防守越好的人，我們給他的分數就越多嗎？」→ 選「B」

### E-170
- 編號：原 E-106（同日兩個 session 撞號，本條較晚；2026-11-01 為通過 pre-commit 重複 ID 檢查改號，內容不變，舊文件提到的 E-106 依上下文判斷）
- 日期：2026-10-30
- 假設：無（描述性診斷）。問題：WinImp 主版長人偏袒（E-067 S ≈ +82／+95）來自哪些引擎分量。
- 做法：在活鏈函式上建中性情境（雙方五人都是聯盟平均描述子），把每位球員換進場，逐分量算每 100 回合期望淨分（確定性，不抽亂數），得到攻守各分量帳；檢核帳與 WinImp 的 Spearman ρ ≥ 0.8；再算各分量 C − 後衛差距，以及把該分量設成平均後的 S。不用模擬消融（F-040 雜訊）。輸出 `reports/E106-bias-ledger/`。
- 已揭露：lead 看過 E-067 基準 S、F-048 讀碼結果；沒看過任何分量帳數字。
- 結果：帳本代表得了 WinImp（Spearman 0.932，帳本 S 89.0／101.7 vs WinImp 81.8／95.2，偏袒在中性確定性帳裡就存在，不是模擬動態）。C − 後衛最大分量：進攻籃板 +1.75 分／場，只把它設成平均帳本 S 降到 17／30；其次防守籃板、護框 makeDef_ra、近距離命中、身材。隊友出手品質 context 反向（C −1.42，拿掉 S 升到 153／164）。外線防守分量（fresh logits、onBall、corner）全人群 0（F-049）。報告 `reports/E106-bias-ledger/report.md`。
- 狀態（原）：進行中（2026-10-30，App 內 Opus 子代理本機執行）
- 狀態更新：完成（2026-10-30；描述性，等使用者決定下一步）
- 相關：E-098、E-067、F-048、F-040、E-099、L-059
- 來源：使用者 2026-10-30 選「先診斷」（回「1」）

### E-107
- 日期：2026-10-30
- 假設：把 E-106 的 UL（防守加成不封頂 bonus = max(0, centeredD)，D 用 E-104 逐場線性、回合門檻 × 1/2）搬到正式卡 card 0.2.6（E-101 能力值）上，整體一致性（m1–m3）不明顯變差；Wembanyama 上升且 Wagner 仍在他後面（R-061）。lead 事前預期 Wemby #1–2、Wagner #3–5、Cade 大致不動、前 20 名換超過 3 人。
- 做法：`reports/card-0.2.6+E107-defense-UL/preregistration.md`（草稿）。組別 B6（card 0.2.6 原樣重建）、UL6 × primary／fitA／fitB；c0a／c0b 要重現 E-101 P1 卡與 card 0.2.6 ranking（a0a81ecb…6c91），c0c 要重現 E-106 UL。採用時一律 PATCH → card 0.2.7（L-026，非盲測）。
- 已揭露：見預註冊 §1（E-106 全部結果、card 0.2.6 名次；沒算過 0.2.6＋UL 的任何結果）。
- 結果：硬條件全過（c0a／c0b 重現 E-101 P1 卡與 card 0.2.6 ranking、c0c 重現 E-106 UL、npm test 57/57、u1、f2）。對 B6：m1 +0.0059 [+0.0009, +0.0111]、m2 +0.0016 [−0.0026, +0.0059]、m3 +0.0063 [+0.0011, +0.0116] 都過；r1' 過（Wagner #7、Wemby #3 → #2）。evaluate 19/19 → 18/19：big14of16 只剩 13/16（Embiid #17 → #24、Koloko #354 → #442 加成 1.47 → 0、Davis #40）。Luka #4 → #9、Durant #21 → #27、Derrick White #8 → #4；前 20 名只換 2 人；頂端 OVR 壓縮（SGA 107.3 → 104.0，PR99 錨點 3.51 → 4.12）。lead 事前預期 Wagner #3–5、前 20 換 > 3 人都錯（F-051）。總評 2/5，`reports/card-0.2.6+E107-defense-UL/report.md`。
- 狀態：凍結（2026-10-30，使用者「核可」；sha256 454e4cc4…a169），執行中
- 狀態更新：凍結（2026-10-30，使用者「凍結開跑」，sha256 344f860a…263c）並跑完；等使用者 G5：採用發 card 0.2.7（PATCH）、不採用、或先查 Embiid／Koloko。未 commit。
- 狀態更新：驗收通過、排隊待併版（2026-10-30，R-063）：照 PATCH 批次發版，維持 `card 0.2.6+E107`，不單獨發 0.2.7，等下一批改動一起出；名單頁仍是 0.2.6。
- 狀態更新：已採用（2026-10-30，R-065）：發 card 0.2.7（PATCH），`reports/card-0.2.7/`，名單頁 2025-26 改指 0.2.7；未做 role-audit。
- 編號：另一個 session 同日也用了 E-107（新賽季對齊 0.2.6，下一條）。本條較先寫、預註冊已用此號凍結，不改號；引用時寫「E-107 防守 UL」。
- 相關：E-106、E-104、E-101、R-061、R-060、R-019、F-049、F-051、L-026
- 來源：使用者 2026-10-30「b UL」→「先寫預註冊」

### E-171
- 編號：原 E-107（同日兩個 session 撞號，本條較晚；2026-11-01 為通過 pre-commit 重複 ID 檢查改號，內容不變，舊文件提到的 E-107 依上下文判斷）
- 日期：2026-10-30
- 假設：新賽季頁整套換成 card 0.2.6 的量尺（先驗 x0、賽中映射改四季合併池＋99 以上尾巴＋補籃分區、OVR 層換 E-101 擬合）後，追蹤整季答案不變差；最多 PATCH，採用後 inseason 0.2.6（R-050）。
- 做法：`reports/ovr-inseason-2026-27/e107-card026/preregistration.md`（照 E-095 模式）。基準 inseason 0.2.5a（CARD_MODE=025）；候選 CARD_MODE=026。前置 (c0) 025 逐位元不變、(c1) npm test、(u) 尾巴函式、(z) 分區、(L1) N=0 重現 card 0.2.6 每人 ≤ 0.1、(s) 量尺一致；判定 (1) RG1-026 過 v5 V1∧V2、(2) 8 格 MAE 差 ≤ +0.05（對 E-095 RG1-sat15）。
- 已揭露：lead 看過 E-101／card 0.2.6 全部結果、E-095 結果、線上 0.2.5a；沒看過任何 0.2.6 量尺的新賽季數字。只換先驗、賽中仍夾 99 會讓尾巴球員隨場數下修，所以賽中映射一起換。
- 狀態：預註冊已凍結（2026-10-30，使用者「核可凍結」），sha256 cb5b293d…f173（`preregistration.sha256`）；凍結前只改了凍結那一行，判定沒動。執行在前置條件停下（2026-10-30，App role-card 子代理）：(c0)(c1)(u) 過，(z)(L1)(s) 不過，依 §4 沒寫回測、沒看 (1)(2)。不過的原因：(z) 2025-26 有 1/582 人差 1 球（Daniss Jenkins，一次 area 缺值的上籃，賽中規則算 short，E-101 抽取略過）；(L1) 5 人超過 0.1，max 0.161（Ausar Thompson），是 ranking.csv 的 x0 四捨五入到 0.1 後移動 pointwise 封頂門檻所致，換未四捨五入的 attributes-e101.csv 時 max 0.054；(s) 只有 stamina 不過（中位 0.00→−3.43），預註冊把 stamina 改對四季池，但 card 0.2.6 的 stamina 是單季量尺。線上 026 對 0.2.5a（10-28 資料，只描述）368 人中位 |ΔOVR| 0.6、最多 3.8。產出 `e107-card026/report.txt`（.md 被子代理擋，L-055）、`results.json`、`prereq.json`、`deviations.json`（D1–D11）。完成，待 lead 審；要繼續需先出 errata 再凍結（L-063、L-064）。
- 相關：R-060、R-050、R-052、R-019、E-101、E-095、L-026、L-032、L-053、L-060、L-063、L-064
- 來源：使用者 2026-10-30「跟上 0.2.6」

### E-108
- 日期：2026-10-30
- 假設：外線防守的價值不在壓三分命中率（v45 已試、F-050），而在讓對手回合變差：M1 持球失誤、M2a 傳球失誤、M2b 被助攻比例下降、M3 拖到進攻時間剩 ≤ 6 秒才出手或違例。第一階段只量測：場上防守五人能否在留出比賽預測這四個量（v45 式隨機效果、σ 格點、留出 NLL），並跨季穩定。
- 做法：`reports/E108-perimeter-feature/preregistration.md`（2026-10-30 使用者「執行」凍結，sha256 db63d7b3…1042）。判定 (s0) 切段、(s1) 留出 NLL 低 ≥ 2 且 ≥ 2/3 季、(s2) 相鄰季 r ≥ 0.30。有訊號的量才另寫第二階段（引擎接點，各自 p0）。p0（`p0.json`）：v45 corner／arc 命中、three／cornerGivenThree 選擇四個位置在活鏈都是活的。
- 已揭露：見預註冊 §1；沒看過任何依防守者分組的失誤、助攻、出手時間數字。
- 狀態：第一階段在 s0 停下（2026-10-30）：每隊每場段數中位數 116–119，超過凍結範圍 90–115，因為進攻籃板後的「重置段」每場多約 17 段；沒有擬合、沒有看任何依防守者分組的數字（`s0.json` sha256 e471fa23…）。使用者「重跑」核可修正 A1：s0 只數非重置段，範圍不變，其他不變；修正後預註冊 sha256 3ec8ea1b…659a（`preregistration.sha256.A1`），修正後仍不過就停（L-062）。重跑完成（2026-10-30，App Sonnet 子代理，5090 `~/e108/`）：s0-A1 過（非重置段中位數 100–102）；s1 四量全過；s2 只有 M3 過（0.305），M1 0.278、M2a 0.291、M2b 0.247 無訊號（F-053）。lead 另算選模、s1、s2 一致。等使用者決定 M3 要不要進第二階段
- 相關：F-050、F-049、F-048、E-106、E-098、L-059、L-046、L-026
- 來源：使用者 2026-10-30「Add perimeter feature」＋三個機制（運球、傳球、拖時間）

### E-109
- 日期：2026-10-30
- 假設：E-103 的瓶頸是 heuristic 教練換人太快（F-052）。教練改成「累了才換、落後分鐘就多撐」（`rotationModel:'cycle'`：撐力＝體力＋κ×(應打−已打分鐘)，撐力 < e_out 才換，換上撐力較高的最佳替補；兩個參數 e_out∈{0.70…0.86}、κ∈{0.02…0.08}/分），在 legacy 疲勞下就能讓 stint 長度對上真實（T1）、分鐘不變差（T2），而且沒校準的「先發第一節第一段長度」也對得上（U1）。第 2 階段凍結教練參數，接回 E-103 工作量疲勞重做 λ 校準，T1–T3 同時過。這是「聰明教練團」的第一步：先做像真實的平均教練。
- 做法：`reports/sim-0.1.0+E109-coach-stints/preregistration.md`；`opt.rotationModel` 預設 legacy 逐位元重現；新 seed：校準 20261090–93、驗證 20261100–07；在 5090 跑；程式接在 worktree `D:/Projects/CODING/ba-e103`（E-103 改動預設關）。只在 heuristic 模式生效，budget／WinImp／卡片不動。
- 已揭露：見預註冊 §1（E-103 全部結果含 legacy stint 表；輪替程式碼與 legacy 疲勞公式手算；沒跑過新教練，也沒看過真實的先發第一段長度）。
- 結果：前置閘 p0、c0（逐場雜湊 25caf475…bccd8 不變）、g1（57/57）過。**校準組沒有任何一組讓 L 每項 ≤ 1 → 停下**；最好組 0.70／0.02 L＝5.57（legacy 38.2），只差 ≥32 組 ≥10 分鐘比例（0.11 vs 0.19）一項；中位數四組都在 ±1 內，U1 先發第一段 8.3 vs 7.9（沒校準）；T2 20 組都過。分布太窄（F-054）。驗證組與第 2 階段沒跑。DS 後端 402 餘額不足，改 App 內 Sonnet 子代理執行。報告 `reports/sim-0.1.0+E109-coach-stints/report.md`；程式在 worktree `ba-e103`，未 commit。
- 狀態：不採用（2026-10-30，§4.2 停止規則；預註冊凍結 sha256 24815420…bc21，跑後相同）；使用者 2026-10-30 選 A → E-112
- 相關：E-103、F-052、R-057、L-045、L-026、L-052
- 來源：使用者 2026-10-30「A」（另開實驗只改教練換人邏輯，再接工作量疲勞）

### E-110
- 日期：2026-10-30
- 假設：單場評分（E-105／R-062）漏掉防守；加入 NBA 單場 hustle（撥球、干擾出手、製造進攻犯規、地板球、掩護助攻）與防守對位（比進攻者平常少讓幾分、逼出失誤）後，樣本外對 RAPM 的相關比只用 box 高（H1），防守型球員評分名次往上（H2）。
- 做法：`reports/E110-defensive-rating/preregistration.md`（草稿）。2025-26 全部 1230 場抓 `boxscorematchupsv3`、`boxscorehustlev2`（存 `data/matchup-source/2025-26/`）；M0 box 11 項／M1 ＋hustle 5 項／M2 ＋對位 2 項，擬合同 E-105（加權最小平方，A→B 與 B→A）。判定 s1：M2（或 M1）對 M0 的 A→B Δr bootstrap 下界 > 0 且 B→A Δr > 0；s2（半盲）5 個防守者 ≥ 4 人名次往上。只顯示，不進 OVR；過了才另做第二階段（每日發布順便抓）。
- 已揭露：見預註冊 §1（E-105 全部結果、2026-10-30 評分對 OVR 名次差最大 12 人、單場穩定度 0.213／0.428；只看過 0022600003 一場的原始對位與 hustle）。
- 結果：`reports/E110-defensive-rating/report.md`、`results.json`、`ranking.csv`。c0（M0 重現 E-105，差 0）、c1、d0（1230／1230）、d1（100%）過；**d2 照字面不過**：對位部分回合合計 ÷ 該隊回合數中位數 4.64，因 partialPossessions 是每個進攻者各記（約 5×回合），÷5 後 0.928（F-055）。主判定（若 d2 改 ÷5 成立）：M2 A→B r 0.444→0.526（Δ +0.083，95% +0.026～+0.138）、B→A 0.501→0.592，s1 過；M1 只 +0.021（區間含 0）、B→A +0.003，s1' 不過；選 M2。s2：5 個防守者全部往上（Camara 218→88、Jones 183→140）。整季評分對 OVR Spearman 0.549→0.677；單場 r 0.213→0.222、5 場 0.428→0.439；單場 >10 4.0%→5.5%、=0 0.9%→2.1%。和事前預期相反：hustle 幾乎沒用，進步來自對位。受保護目錄 sha256 前後相同。
- 狀態：通過（2026-10-30，R-066：使用者同意 d2 改 ÷5、採用 M2；原為「d2 停下等裁定」）
- 相關：E-105、R-062、R-007、L-026、F-055、L-066
- 來源：使用者 2026-10-30「只看 box score 准吗？」→「第三项做得到吗？」→「A」（先寫預註冊）

### E-112
- 日期：2026-10-30
- 假設：E-109 的 `'cycle'` 教練中位數對了但分布太窄（F-054）。加「收尾不換」（比分差 ≤ 10 時，第 1–3 節最後 `cycleCloseWindow` 秒、第 4 節最後 `cycleQ4Window` 秒不因撐力低換下先發；第 4 節窗口內叫回體力 ≥ e_out 的先發），就能補上長 stint 與整節打滿，讓 T1 四組＋U1（先發第 1 節第一段中位數 7.90、打滿 0.0767，這次改成校準目標）共 10 項都 ≤ 1，且沒校準的 U2（第 3 節先發第一段）也對上。
- 做法：`reports/sim-0.1.0+E112-coach-closing/preregistration.md`；網格 e_out{0.70,0.74,0.78,0.82}×κ{0.02,0.04}×窗口{0,60,120}×Q4 窗口{0,300,480}＝72 組；新 seed：校準 20261120–23、驗證 20261130–37；閘 c1＝新參數全 0 時和 E-109 cycle 逐位元相同；第 2 階段同 E-109（接工作量疲勞重選 λ）。只在 heuristic 模式生效。
- 已揭露：見預註冊 §1（E-109 全部結果含 U1／R3／R6 真實值；rotation-curve.json 前 900 字元；沒看過 U2）。
- 結果：p0、c0、c1、g1 過。**校準組 72 組沒有一組 10 項全 ≤ 1 → 停下**；最好組 0.70／0.02／120／300 L＝5.41（同參數無收尾 9.60、legacy 60.69），只差 ≥32 組 ≥10 分鐘比例 0.112 vs 0.19（72 組最高 0.130，第 4 節窗口拉長會把 24–32 中位數推出 ±1）；U1 打滿 0.2%→4.2%；U2（校準組、未驗證）中位數 7.68 vs 7.85。F-058。報告 `reports/sim-0.1.0+E112-coach-closing/report.md`。
- 狀態：不採用（2026-10-30，§4.2 停止規則；預註冊凍結 sha256 06575ad8…e288，跑後相同）；擱置（2026-10-30，R-068：體力與換人列為 TODO）
- 相關：E-109、E-103、F-054、L-026、L-045、L-065
- 來源：使用者 2026-10-30「A」（新教練加收尾不換）

### E-111
- 日期：2026-10-30
- 假設：新賽季頁（inseason 0.2.5a）跟上 card 0.2.7（0.2.6 量尺＋防守 UL）後，追蹤誤差不變差（8 格 MAE 差 ≤ +0.05）且仍過 v5 V1∧V2。是 E-107 新賽季版（停在前置關卡）的 errata 重做，換號因 E-107 撞號。
- 做法：`reports/ovr-inseason-2026-27/e111-card027/preregistration.md`，繼承 E-107 新賽季版預註冊，改：x0 用未四捨五入值（修 L1）、OVR 層與防守加成照 card 0.2.7（UL6）、stamina 不換尺且不列入 (s)（使用者：體力不重要、要從網站拿掉）、area 缺值的出手照 E-101 跳過（修 z）、foulDraw 池用逐季 z。CARD_MODE=027，版號 inseason 0.2.7。
- 已揭露：E-107 新賽季版前置結果與 026 線上名次比較、card 0.2.7 summary；沒看過任何回測 (1)(2)。
- 結果：前置 (c0)(c1)(u)(z)(s) 過，(L1) 不過 → 照 §4 停下，回測 (1)(2) 沒跑、沒看。(c0) 025 對 live/2026-10-28 逐位元相同；(c1) npm test 57/0；(u) 尾巴差 0；(z) 2025-26 分區對 E-101 0 人不符、2026-27 <8 呎判 mid 0 球；(s) 9 項全過（stamina 只報告，中位差 0）。(L1) 582 人裡只有 Toumani Camara 差 −0.180（四捨五入後 82.7 vs 82.9），其餘 ≤ 0.053；錨點、r_repl、UL 防守加成（582 人 0 不符）都差 0。原因：H1 封頂的 RAPM 名次遇到 pooledNet 同分（Camara、Sam Hauser 都是 3.501）時，賽中 OVRPipeline 照 playerId 排、card 產生器照 rapm.csv 列序排，Camara 的 allowed 變成 52（卡是 51），被封在 Draymond 的 pred 1.4678（卡 1.4944）。共 7 人名次差 1，只有 Camara 受影響。報告 `reports/ovr-inseason-2026-27/e111-card027/report.md`、`prereq.json`、`deviations.json`（D1–D12）。
- 狀態：凍結（2026-10-30，使用者「1 … 0.2.7也順便合併 Go」，sha256 f20f34a4…739e）；實作中
- 狀態更新：停在前置（2026-10-30，role-card）：(L1) 不過（RAPM 名次同分排序，L-067），等 lead／使用者裁定修法後重凍結；(1)(2) 未看
- 狀態更新：回測完成（2026-10-30，role-card）：errata-1（sha256 1d243371…0c90，RAPM 名次同分照卡片產生器）只改 run_c4_live.py 027 分支（新 sha256 fe417d8a…a754），前置 6 項重跑全過；(1) V1∧V2 主判定 Y5、Y6 過（N=10／20 MAE 對 RA-027 降 0.29～1.06、>10 分的人數變少），Y3 敏感度也過；(2) 8 格 MAE 對 E-095 RG1-sat15 全部變小（差 −0.26～−0.77，門檻 ≤ +0.05；配對 bootstrap 90% 區間 −0.67～−0.33）→ 照 E-107 §4「(1)(2) 都過」交 role-audit 與使用者 G5。注意：歷史 027 卡只換 9 個合併池屬性、drive 用舊定義、(2) 兩邊答案卡不同尺度、回測錨點 r_repl −1.827 與賽中 usage027 的 −1.246 不同（deviations D13–D21）。線上 027 對 0.2.5a：368 人 |ΔOVR| 中位 1.1、最大 7.1；Dončić 2→9、Embiid 12→19、Curry 30→42、Queta 39→22、Wembanyama 3→1。見 `e111-card027/results.json`、`live-compare.json`、`report-v2.txt`
- 狀態更新：role-audit 重算成立（2026-10-30，`e111-card027/audit/audit.md`）：(1)(2)(L1)(c0) 數字一致、凍結在先；疑慮：(2) 不變差主要來自答案卡尺度壓縮（SD 10.7 vs 12.6），共同尺度 MAE/SD 下 Y5 變差 +0.11～+0.15、Y6 打平；歷史卡 onBall／help 固定 70（D15）。等使用者 G5。
- 狀態更新：**已採用**（2026-10-30，使用者「1」，R-069）：程式 commit 4289a62，gh-pages 9c7bd6f 上線 inseason 0.2.7（數據至 2026-10-28），線上頁已核對版號與更新說明
- 相關：E-107（新賽季版）、E-107（防守 UL）、E-101、E-095、R-065、R-050、L-063、L-064、L-026
- 來源：使用者 2026-10-30「跟上 0.2.6」→「核可凍結」→「1 然後體力不太重要…0.2.7也順便合併 Go」

### E-113
- 日期：2026-10-30
- 假設：評分 M2（R-066）的對位分數補上三項（對位列 helpBlocks 當補防阻攻、PTS_SAVED 的基準排除防守者自己、把被守者的助攻算進對位產出），樣本外對 RAPM 的相關比 M2 高；協防護框的長人（Gobert、Lopez、JJJ、Turner、Embiid）名次往上。lead 事前預期 Δr 0～+0.02，s1 不過的機率約六成。
- 做法：`reports/E113-help-defense/preregistration.md`（草稿）。只用已抓的 2025-26 對位資料，不抓新資料；M3（19 項）對 M2，A→B bootstrap 下界 > 0 且 B→A 點估計 > 0 才過；M3a／b／c 拆解只報告、不拿來選。
- 已揭露：E-110 全部結果與 lead 2026-10-30 的名次對照表（護框、防守者、高估名單都看過，s2 是半盲）。
- 狀態：凍結（2026-10-30，使用者「核可」；sha256 454e4cc4…a169），執行中
- 狀態更新：凍結（2026-10-30，使用者「A」，sha256 c1ef9562…afc7）；路由 self，改在 App 執行（未派 role-card）
- 狀態更新：**失敗**（2026-10-30）：硬條件 d3（對位 helpBlocks 整季全 0）、d4（V 2.75 > 2.6）不過，照預註冊停下，評分維持 M2。s1 名義數字 Δr +0.024／+0.014 無效；增益全來自助攻（M3c），排除自己無效（M3b）。見 `reports/E113-help-defense/report.md`、F-057、L-068
- 相關：E-110、E-105、R-066、F-055、L-026
- 來源：使用者 2026-10-30「如何修正？是否可以補正對位者的強度？如何測量補防」→ 三層做法選「A」

### E-114
- 日期：2026-10-30
- 假設：對位分數把被守者的助攻算進去（M4＝E-113 的 M3c），在沒看過的 2024-25 仍比 M2 準：季內 A／B 樣本外，以及 E-113 凍結的 2025-26 權重跨季套用，兩者都要更好。lead 事前預期 Δr +0.005～+0.02，s1 過的機率約五成。
- 做法：`reports/E114-assist-matchup/preregistration.md`（草稿）。先從現有 boxscore 組 2024-25 box，抓 1104 場對位與 hustle，算單季分半 RAPM；凍結前先做欄位檢查（L-068），結果填進 §1 給使用者看。
- 已揭露：E-110、E-113 全部結果（2025-26）；2024-25 只看過檔案清單。
- 狀態：草稿（2026-10-30），等使用者核可後才抓資料
- 相關：E-113、E-110、F-057、L-068、L-026
- 來源：使用者 2026-10-30「2」（E-113 報告的選項 2）

### E-115
- 日期：2026-10-30
- 假設：四因素 RAPM 的 eFG 防守（每季用另外三季擬合）當成命中模型的結構特徵，至少一區（尤其底角、弧頂）在出手層留出 NLL 比 v45 現行好，讓外線防守者拿到非零的命中防守分，並減少蓋帽率給中鋒的過度加分。lead 事前預期：外線過的機率約三成、籃下「加 R」約五成。
- 做法：`reports/E115-make-recalibration/preregistration.md`（草稿）。A 部分只做命中；籃板通道先做 p0，另寫預註冊。
- 已揭露：F-056 對帳全部結果（四季合併，含 2025-26）、v45 選模、E-106 帳本；沒看過留一季四因素 RAPM。
- 狀態：第一階段完成（2026-10-30，App Sonnet 子代理，5090 `~/e115/`；lead 重加總核對）：籃下、禁區 a1、a2 過；外線三區與中距離無訊號（F-059）。a3 規格有歧義（L-069）待使用者裁定；效果太小（中鋒 −0.03），lead 建議不進第二階段
- 相關：F-056、F-050、F-049、E-106、E-067、L-026、L-059
- 來源：使用者 2026-10-30「1」（F-056 報告的選項 1）

### E-116
- 日期：2026-10-30
- 假設：用順位分層的新秀平均當先驗卡（P2），新秀前 5～10 場的賽中 OVR 比替補級先驗（P0）或只看自己（P∅）更能預測剩下場次。
- 做法：`reports/E116-rookie-prior/preregistration.md`（草稿）。用 2025 選秀新秀在 2025-26 做留一法回測，比較 P0／P1／P2／P∅，判定後依結果選一組上線，讓 2026-27 頁的 42 個 2026 新秀都有 OVR。
- 已揭露：card 0.2.7 裡 55 個 2025 新秀的名次；2026-27 的 no-prior 名單。
- 狀態：草稿（2026-10-30），等使用者核可
- 狀態更新：草稿第二版（2026-10-30，使用者「按順位但是起點也不是很重要 趕快讓現有數據說話」）：只留順位分層一組；新秀 k＝σ²/τ²（新秀間變異，經驗貝氏），因為 n_prior=0 時現行 k_eff 取上界＝凍結在起點；回測只報告
- 狀態更新：凍結第三版（2026-10-30，使用者「A」＋「新秀每一順位都不同起點分吧 起點多少可以看前五季」）：起點＝2017–2021 五屆新秀（282 人，027 卡；2022–24 屆沒有 027 尺度的卡）各項能力對 ln(順位)＋位置的迴歸，落選當 61；τ²＝殘差變異；2025 屆變成真正樣本外回測。sha256 af3911d2…f85038。進行中
- 狀態更新：完成（2026-10-30），3/5：42 新秀都有 OVR、老將 368 列不變、npm test 過；2025 新秀樣本外 MAE N=10 新秀版 10.61／凍結 11.05／只看自己 9.99；頂順位被低估（Knueppel 85.5→65.0），起點尺度和 card 0.2.7 不合（creation +24.7、pass +13.9），見 F-060。等使用者決定上線。`reports/E116-rookie-prior/report.md`
- 狀態更新：上線（2026-10-30，使用者「1」，R-071）：daily 改跑 `live/run_c4_live_rookie.py`，名單頁 2027 頁新秀名字旁標「新秀先驗」（tooltip 寫已打場數）；gh-pages 7494587。尺度修正另開 E-121
- 相關：R-067、E-081、E-064
- 來源：使用者 2026-10-30「新秀要留 未來也要趕緊加入27的新秀」→ 選「B」

### E-117
- 日期：2026-10-30
- 假設：（描述性，不是候選）模擬關掉體力（`fatigue:false`，其他同 `budget` 模式正式 options）後，WinImp 名次、E-067 S、對答案 ρ，以及 30 隊互打的球隊淨分差／勝率 MAE、RMSE 會怎麼變。
- 做法：`reports/sim-0.1.0+E117-fatigue-off/spec.md`（sha256 6fcff6d0…9d99）；WinImp 同 E-065／E-076（379 人、baseSeed 20261028、30×16×2）；球隊同 E-076 t1（8 seed 20261028–35），差值 team＋seed 重抽 400 次 rngSeed 117；p0 驗證選項有接上（L-059）；在 5090 跑。
- 已揭露：見 spec §1（lead 沒跑過關體力；從公式推過預期主力略降、替補略升）。
- 結果：球隊淨分差 MAE 3.20→3.32（差 +0.12，90% [−0.24, +0.59]），勝率 MAE 0.087→0.093（差 +0.006，90% [−0.008, +0.021]），聯盟場均得分 117.5→119.1（真實 115.5）。主版 WinImp 名次 Spearman 0.91、平均名次差 36（獨立重跑雜訊下限 0.66／69），S（AB）81.8→79.7 仍偏長人，ρ 0.382→0.384。位置版 Spearman 0.77、平均名次差 56，S（AB）+37.5→−37.0（90% 區間不重疊），從偏長人翻成偏後衛；最高體力四分之一位置版升約 18 名，和「主力降」的推測相反。報告 `reports/sim-0.1.0+E117-fatigue-off/report.md`。
- 狀態：完成（2026-10-30，描述性；正式流程維持開體力）
- 相關：R-068、E-065、E-067、E-076、L-059、L-026
- 來源：使用者 2026-10-30「量 然後如果關體力 模擬的球隊賽季mae 會不會變動」

### E-118
- 日期：2026-10-30
- 假設：F：場上防守五人會影響對手投籃犯規（引擎現在只看持球者），而且跨季穩定；H：2025-26 對位命中率（扣掉進攻者自己的命中率）有可重現的個人差異。lead 事前預期 F 的 s1 過約八成、s2 過約六成；H 過約四成。
- 做法：`reports/E116-fouls-matchup/preregistration.md`（草稿）。F 沿用 E-108 的切段與模型；H 只量分半可靠度。
- 已揭露：F-053、F-056（含 RAPM 罰球分逐人）、F-059；沒看過依防守者分組的犯規或對位命中率。
- 狀態：已凍結（2026-10-30，使用者「執行」；sha256 見 `preregistration.sha256`），執行中。報告目錄沿用 `reports/E116-fouls-matchup/`（凍結檔內標題仍寫 E-116，和新秀先驗 E-116 撞號，2026-10-30 改號 E-118）
- 相關：E-108、E-115、F-056、L-069、L-062、L-026
- 來源：使用者 2026-10-30「罰球／然後逼對面輪轉 回合最後糟糕出手／逼對位人降低命中率 能否測到」

### E-119
- 日期：2026-10-30
- 假設：防守者在場時，對手回合時長（D1，連續秒數，控制進攻五人與防守五人）和第一次出手比 v45 預期命中更差（D2，v45 防守之外多出的壓制），兩者都有可重現的個人效果。lead 事前預期 D1 過約七成、D2 約三成。
- 做法：`reports/E119-clock-pressure/preregistration.md`（草稿）。沿用 E-108 切段；D2 的 offset 用 v45 不含該場的折擬合。
- 已揭露：F-053（含 M3 排名偏護框）、F-056、F-059；沒看過依防守者分組的時長或出手殘差。
- 狀態：已凍結（2026-10-30，使用者「執行」；sha256 見 `reports/E119-clock-pressure/preregistration.sha256`；凍結前補了 v45 logit 讀法與 D1 嶺迴歸細節），執行中
- 狀態更新：完成（2026-10-30，App Sonnet 子代理，5090 `~/e119/`；lead 從 fits 重加總核對）：D1 三關全過但效果小（SD 0.08 秒／段）、和 M3 r 0.85；D2 失敗（選 σ_d=0）（F-062）。預註冊 §7 仍寫 E117 目錄，是 lead 改號漏改的筆誤，實際用 E119
- 狀態更新：第一階段完成（2026-10-30，App Sonnet 子代理，5090 `~/e116/`；lead 從 375 個折擬合重加總、跨季 r 核對）：F 罰球 s1／s2／s3 全過；H 兩分 r 0.59 過、三分 r −0.19 不過（F-061）。使用者「罰球要」→ E-120；H2 控制位置（使用者「A」，`amendment-h2.md` sha256 25ab0b2f…28b8）：兩分 r 0.588→0.496，108 人，過 0.20；位置解釋變異 22%／16%

### E-120
- 日期：2026-10-30
- 假設：把 E-118 的防守者投籃犯規效果接進引擎後，帳本罰球分量和 RAPM ftRate 對得上（r ≥ 0.40），球隊層不變差。lead 預期 E-067 S 可能小幅變差（通道偏中鋒）。
- 做法：`reports/E120-foul-defense/preregistration.md`（草稿）；先做 p0。
- 狀態：已凍結（2026-10-30，使用者「A」：S 只報告，主判定 t1＋t2；sha256 見 `reports/E120-foul-defense/preregistration.sha256`），執行中
- 狀態更新：停止（2026-10-30）：p0、t1 過（r 0.593），t2 不過（淨分差 MAE +0.208 > 0.1），不是採用候選；WinImp 名次與 S 未跑；src 開關預設關、未 commit（F-065）
- 狀態更新：使用者 2026-10-30「接受停止」：不補跑 S／名次；開關保留預設關
- 狀態更新：事後診斷（2026-10-30，看過結果的探索）：t2 惡化大多是 8 seed 模擬雜訊，β 帶來的系統性部分只 +0.024（F-067、L-077）；判定不改
- 相關：E-118、F-061、F-056、E-067、R-070、L-059
- 來源：使用者 2026-10-30「罰球要」

### E-121
- 日期：2026-10-30
- 假設：新秀起點換成 card 0.2.7 的尺度後，2025 新秀回測 N=10 MAE ≤ E-116 v3 的 10.61，頂順位不再被壓低。
- 做法：`reports/E121-rookie-scale/preregistration.md`（草稿）。三路線擇一：A 用 0.2.7 流程重建五屆新秀季卡、B 只用 2025 屆 0.2.7 擬合、C 五屆形狀＋2025 屆水準位移（lead 建議）；B／C 用留一法；2026-12-31 前瞻檢查只報告。
- 已揭露：E-116 全部結果與逐人表。
- 狀態：草稿（2026-10-30），等使用者選路線
- 狀態更新：上線（2026-10-30，R-073 路線 D 簡化版）：起點＝2K 順位曲線換本站尺度−5，x0 齊頭平移（`reports/E121-rookie-scale/report.md`）；老將 0 列變動、npm test 57/0。2025 屆回看 N=10 MAE 11.33（E-116 10.61），看過答案只報告；準確度等 2026-12-31 前瞻
- 相關：E-116、F-060、R-071、R-073、F-063
- 來源：使用者 2026-10-30 選 E-116 報告的選項 1

### E-122
- 日期：2026-10-30
- 假設：把 E-119 D1 防守者時長效果加到引擎回合時長抽樣後，通道照設計作用（c1 r ≥ 0.50）、球隊層不變差（c2）。S 只報告。lead 預期名次變動很小。
- 做法：`reports/E122-clock-d1/preregistration.md`（草稿）；等 E-120 收尾才開工（同一個 src 檔）。
- 狀態：已凍結（2026-10-30，使用者「執行」；sha256 見 `reports/E122-clock-d1/preregistration.sha256`），等 E-120 收尾後開工
- 狀態更新：修正 A1（2026-10-30，使用者「先修正 c2」；看到 c2 前）：c2 改 32 seed＋雜訊底 N，通過＝ΔMAE ≤ 0.1+N（`reports/E122-clock-d1/amendment-a1.md` sha256 cc3399bb…3e03；L-077）；執行中
- 狀態更新：完成（2026-10-30）：p0／c1／c2 過，c2 改善在雜訊內且和 β 無關；c3 主版 S 降、位置版 S 升（F-079）。程式未 commit，等使用者裁定
- 相關：E-119、F-062、E-120、E-108（M3 不接）、R-070、L-059
- 來源：使用者 2026-10-30「B」（回合時長接 D1）

### E-123
- 日期：2026-10-30
- 假設：3PT（threeValue）、RIM（help）、PRES（pressure／presDisplay）照 E-101 框架（四季合併池、差距尺＋只壓縮保險、h1 過的那端才開）開 99 以上與 40 以下尾巴後，剛好 99 的並列（4／4／7／6 人）散開，卡片層不變差（m1–m3、c3 ≥ 18/19、c4 > 140 ≤ 2 個）。
- 做法：`reports/card-0.2.7+E123-tail-3pt-rim-pres/preregistration.md`（草稿）。基準 card 0.2.7。T（threeValue，只顯示）補抓 2022-23 追蹤投籃，抓不齊改三季池；H（help）沿用現行收縮、不用 E-080 位置收縮，f-eng 查引擎讀不讀 > 99；P（pressure）用 defense-tenth 現成的 2022-23、2023-24 hustle／matchups 重建 force，a0P 要逐人重現 E-071 force。變體 e123（主）、e123h、e123p（只報告）。
- 已揭露：三欄 2025-26 頂端名單與 99 並列人數、E-080／F-030（Stewart 原值 123、z 4.82）、E-071、E-057 全部結果；lead 手算 Stewart 可能 125–136。
- 狀態：已凍結（2026-10-30，使用者「Freeze and run」；sha256 bbaace39…2374，見 `reports/card-0.2.7+E123-tail-3pt-rim-pres/preregistration.sha256`）；2026-10-30 跑完，判定全過，總評 4/5；使用者採用（R-078），疊到 card 0.2.7a 重建（`rebase-027a/`：c0 只放 E-125 = 0.2.7a 逐位元，m1–m3 過，c3 18/19，c4 0，三欄和 e123 逐人相同；R-064 影響小：前 20 換 1 人、前 300 移動 ≥ 10 名 2 人），發為 **card 0.2.7b**（2026-10-30）
- 結果（`reports/card-0.2.7+E123-tail-3pt-rim-pres/report.md`，lead 已重算核對三欄 99 並列與 > 140）：剛好 99 的人 3PT 4→0（Curry 105.0）、RIM 4→0（Stewart 113.5、Wembanyama 108.7）、PRES 7→0（Thybulle 127.0）、presDisplay 6→0；> 140 為 0；c0 逐位元、m1–m3 ±0.001、c3 18/19。h1：T、P 底端沒過（維持 40），H 兩端過。副作用：Mobley 從第 22 名到第 29 名，Knueppel 進前 20、Anunoby 出。偏差 D1–D8；a0T 第一次 0.31 沒過，修重現 bug（3PA＝0 取聯盟先驗，D8）後才過，照字面違反 §3「不改規則重試」，交使用者裁定。
- 相關：E-090、E-096、E-101、E-080、E-071、E-057、R-024、R-055、R-056、R-072、F-046、L-072
- 來源：使用者 2026-10-30「為何 rim pres 3PT 的錨點沒修，最強的很多人都在 99 整」→「寫預註冊」

### E-124
- 日期：2026-10-30
- 假設：用人回歸拿掉 β8（y·d·L，年輕 × 練兵隊 × 分鐘；R-035 的「練新人打折」例外），其他 8 項重擬合後，樣本外 m1–m3 不明顯變差（門檻同 E-107）；只報告 y=d=1 組在另一半答案上有沒有被高估。
- 做法：`reports/card-0.2.7+E124-no-young-tank-discount/preregistration.md`（草稿）。基準 card 0.2.7（aebcadf1…c6b6）；複製 e094.py 只加 `drop_ydL`（k 9 → 8）；卡片輸入唯讀沿用 E-107 `cards/UL6`；組別 K9（重現 0.2.7）、K8。凍結前先只跑 K9 確認 c0（L-063）。
- 已揭露：card 0.2.7 全部欄位、E-073／E-075／E-084 係數（β8 AB −0.66 [−0.83, −0.48]）；lead scratch 估 Flagg 被扣約 −1.38／36 分、全聯盟 MIN≥1000 最多（推測，L-061）。看過 Flagg 才選方向，不是盲測，採用一律 PATCH（card 0.2.8），並要使用者改寫 R-035。
- 狀態：完成（2026-10-30）：c0／c0k／c1／u1 過；m1 −0.021 [−0.037, −0.006] 未過（門檻 −0.02），m2、m3 過；y=d=1 低估 15.4→−0.4，但 β4(y) 0.47→0.08 使好隊年輕人下滑（F-064）。lead 建議不採用 → 2026-10-30 使用者 G5「不採用」（R-082；E-127 支持保留 β8）。報告 `reports/card-0.2.7+E124-no-young-tank-discount/report.md`
- 相關：E-073、E-075、E-084、E-107、R-035、R-040、R-042、L-026、L-061、L-063
- 來源：使用者 2026-10-30「Cooper flagg的分數好低哦。OVR是不是懲罰高分刷子」→ lead 診斷 → 使用者「B」

### E-125
- 日期：2026-10-30
- 假設：pass 從只看 AST%（AST/astCh）改成 0.5·zs(AST/36，E-055 (c) 收縮)＋0.5·zs(AST%)（R-074，寫法照 foulDraw w075），四季池與 S 錨點照 E-101 重算，樣本外 m1–m3 不明顯變差（門檻同 E-107）。
- 做法：`reports/card-0.2.7+E125-pass-volume/preregistration.md`（草稿）。基準 card 0.2.7（aebcadf1…c6b6）；P0（w_vol=0）要逐位元重現 attributes-e101.csv 與 card 0.2.7；凍結前只准跑 P0 與 vol 擬合。
- 已揭露：card 0.2.7 全部欄位；2025-26 常規池官方 AST_PCT 前 15 名與 AST/36（Giannis AST% 第 9、AST/36 6.8）。沒看過任何 comp、新 pass、OVR 或 Δρ。
- 結果（`reports/card-0.2.7+E125-pass-volume/`，role-card Sonnet 子代理；lead 從 attributes／results.json 重算 c0a、c0、改動欄、具名 pass 值與 m1–m3、p1、npm test 成立）：c0a 逐位元（395e86a0…）、c0 逐位元（aebcadf1…）、c1 57/57、u1 只有 pass 欄變（575/582 列）。m1 +0.0004 [−0.0004, +0.0013]、m2 +0.0007 [−0.0002, +0.0017]、m3 +0.0004 [−0.0005, +0.0013]，三項全過；p1 相鄰季 0.927／0.931／0.896（P0 0.922／0.929／0.889）。evaluate 18/19＝基準；2K27 ρ 0.7359→0.7369。astvol k=5.66、λ=0.5、kh=8。pass 名次（582 人）：Giannis 10→25（值 97.7→96.2，頂端壓縮所以分數只降 1.4）、SGA 14→26、Embiid 96→121、Trae 3→2、Draymond 45→38、Kawhi 121→157。OVR 前 20 只換第 19 名（Knueppel 進、Ausar Thompson 出），動 ≥10 名只有 4 人。simulatedPer36 P0／P50 逐人相同：這條鏈的 cards 沿用既有模擬 per36，新 pass 只進 OVR 迴歸，沒進模擬（R-074 說也進模擬，要另走模擬重跑）。偏離：2025-26 pass 實際入口是 E-090 `a0.py`／`a0-raw.json`（預註冊寫 a0_e101.py），w=0 已逐位元重現。
- 狀態：完成、判定全過；已發 card 0.2.7a（2026-10-30，使用者「0,2,7a」，R-077；`reports/card-0.2.7a/`）
- 相關：R-074、R-034、E-070、E-101、E-107、L-026、L-063
- 來源：使用者 2026-10-30「giannis only has 5 assist, why he is leading in pass」→「same as 3pt, we need to mix ast and ast%」

### E-126
- 日期：2026-10-30
- 假設：S 季被 β8 打折的爛隊年輕人（y=d=1），S+1 季的單季 RAPM 高於 card 0.2.7 的預測，而且高出的幅度超過一般年輕人的進步（D＝爛隊年輕人殘差減好隊年輕人殘差）。用 D／E（E＝平均折扣量）判定「環境說成立」「折扣是真的」或「無定論」。
- 做法：`reports/card-0.2.7+E126-tank-next-season/preregistration.md`（草稿）。係數固定用 card 0.2.7 K9，不重擬合；季對為 2022-23→23-24、23-24→24-25、24-25→25-26；逐季 RAPM 用 rapm.py 換視窗。凍結前只准跑 phase 0 資料盤點（c0r、c0f、c0n）。
- 已揭露：E-124 全部結果；一般 NBA 常識（哪些隊擺爛）。沒算過任何逐季 RAPM 或殘差。
- 狀態：停止（2026-10-30）：phase 0 c0r、c0f 過，但舊季沒有能力值 p（只有 2025-26 建過），三組季對全排除，c0n＝0（L-074）。逐季單季 RAPM 2022-23～2025-26 已建好可重用（`rapm-<季>.json`）。報告 `reports/card-0.2.7+E126-tank-next-season/report.md`
- 相關：E-124、F-064、R-035、E-084、L-026、L-072

### E-127
- 日期：2026-10-30
- 假設：在 S 季年齡 ≤ 23 的人中，控制 S 季單季 RAPM 與年齡後，S 季在爛隊（d=1）的人 S+1 季 RAPM 比較高（γ > 0）。用 γ／E（E＝β8 平均折扣量）判定「環境說成立」「折扣是真的」或「無定論」。
- 做法：`reports/card-0.2.7+E127-tank-rapm-did/preregistration.md`（草稿）。WLS：R_{S+1} ~ 季對 + R_S + age + d，限 y=1；季對 2022-23→23-24、23-24→24-25、24-25→25-26；重用 E-126 逐季 RAPM。不需要 p。凍結前只准跑 phase 0（c0f、c0s、c0n，只准看人數）。
- 已揭露：E-124 全部結果；E-126 phase 0 輸出（人數、sha、c0r／c0f），沒看過任何 RAPM 值或變化。輸入路徑已逐一 ls 確認（L-074）。
- 狀態：完成（2026-10-30，errata-1 核可後重跑）：判定「折扣是真的」，γ/E −0.03 [−0.34, +0.25]，上界 < 0.5。β8 保留，見 F-066。報告 report.md（4/5）；第一次 phase 0 停下的報告是 report-phase0-stop.md
- 相關：E-126、E-124、F-064、R-035、L-026、L-074

### E-128
- 日期：2026-10-30
- 假設：新賽季頁從 inseason 0.2.7 跟上 card 0.2.7b（E-125 pass 量＋率、E-123 3PT／RIM／PRES 頂端開尾）後，N=0 重現 0.2.7b，追蹤誤差不變差（8 格 MAE 差 ≤ +0.05）且仍過 v5 V1∧V2。
- 做法：`reports/ovr-inseason-2026-27/e128-card027b/preregistration.md`（草稿），繼承 E-111＋errata-1，CARD_MODE='027b'。pass 逐場用 E-125 公式（賽中 zs 凍結 2025-26、池用逐季 zs，pool-027b 只動 pass）；help 新秀／老將路徑改 E-123 curve 尾巴（a99 0.095、S 0.0501，重用 e123.py）；pressure／presDisplay 凍結在 0.2.7b；threeValue 拿掉 99 封頂、頂端照 E-123 T；OVR 層照 rebase-027a e123a。新增關卡 (h) help 重算對 0.2.7b、(t) threeValue 對 0.2.7b。
- 已揭露：E-111 全部結果（含回測）、E-123／E-125 全部結果、card 0.2.7b 全部欄位、inseason 鏈盤點。無新自由參數，門檻沿用 E-111。
- 狀態：已凍結（2026-10-30，使用者「凍結並執行」；sha256 5536050e…2aa47，見 `e128-card027b/preregistration.sha256`），role-card 開工發現 §1.2 pass 規格缺口停下（未看結果）；errata-1（照 foulDraw 先例：賽中不收縮、zs 凍結自 2025-26 收縮值、池與歷史卡照 E-125 v61_season）使用者核可（「核可並續跑」）；續跑又在 §1.5 threeValue 停下（池與 acc 先驗），errata-2（凍結 E-123 T 四季池、acc 先驗用 three-value.csv）使用者核可；實作完成、(c0) 過，(h) 因 2025-26 原始表兩份不同停下（step4-t2 7 人差 0.1–0.15，卡片來源 0 人），errata-3（(h) 用卡片來源 data/benchmark-source/defense-rim.json，PAST_RAW 不改、列 TODO）使用者核可；前置 (t) 沒過（N=0 vol 來源不同，558/582 人差 >0.05），使用者裁定 3PT 改用季內遞減＋跨季斷層曲線（「3PT用這個曲線」，即 E-129 那條），errata-4（3PT 拆出 E-128、027b threeValue 照 027、(t) 改只報告；sha256 e5164d07…d292）使用者核可（「核可並續跑」），續跑回測 (1)(2)；3PT 等 E-129 定案另開實驗；回測 (2) 8 格全過、(1) Y5 N=10 V2 沒過（gt10 50 對 49，ciHi +0.17）→ 照規則不採用；使用者破例採用（R-085），上線 inseason 0.2.7b
- 結果（2026-10-30，role-card）：閘門 (1) 沒過 → 依 E-107 §4 不採用。V2 N=10 Y5 一格 gt10 人數 027b 50 > 對照 49（dMAE -0.209 過），其餘 V1／V2 全過；(2) 8 格全過（最大差 -0.273）。線上 027b 對 027 前 20 名 0 人進出，|ΔOVR| 中位 0.1、最大 2.0。檔案見 `e128-card027b/report.md`、`results.json`、`deviations.json`。
- 相關：E-111、E-123、E-125、R-050、R-064、R-072、R-075、R-076、R-078、L-026
- 來源：使用者 2026-10-30「要」（要不要另開 inseason 實驗讓新賽季頁也改用開尾後的公式）

### E-129
- 日期：2026-10-30
- 假設：把賽中 C4 的 b（用已打 N 場預測剩下比賽要信幾成）換成「季內平滑遞減、跨季乘 ρ、年輕人 ρ 較小」的權重曲線（T 族 27 格），或 c 分年齡（K 族 9 格，含基準），在沒選過參數的起點上 N=10/20 誤差比 C4 c=1 小、N=3/5 不變差。f＝N/G 不動。
- 做法：`reports/ovr-inseason-2026-27/e129-tl-season-step/preregistration.md`（草稿）。E-111 回測程式（CARD_MODE=027）；訓練 Y1、Y2、Y3 選單一 W*（12 格 MAE 平均最小，平手選保守），測試 Y5、Y6 只跑 W* 對基準；判定見 §2.4，採用則 inseason PATCH。草案第 4 項「d 改看本季戰績」因回測程式沒有 y/d 用人回歸、舊季無 p，移出本實驗。
- 已揭露：E-033／v5／E-111（含 C4 c=1 在 Y3/Y5/Y6 的 MAE）、E-124／E-127 全部結果、Flagg 2026-27 開季 4 場；lead 手算過 b_T 公式值，沒看過任何非基準格點的回測誤差。
- 狀態：凍結（2026-10-30，使用者「凍結開跑」；sha256 d61d8819…13ac，見 `e129-tl-season-step/preregistration.sha256`）；完成（2026-10-30）：判定「沒有改善」。W*＝K(c_young 0.25, c_vet 0.5)，四格合併 dMAE −0.006 [−0.054, +0.041]；T 族 27 組訓練全輸基準；年輕人 Y5 變好、Y6 變差。lead 建議不採用，等使用者 G5（F-070、L-078）。報告 `e129-tl-season-step/report.md`；不採用（2026-10-30，使用者，R-090）
- 相關：E-033、E-111、E-127、R-082、L-026、L-074
- 來源：使用者 2026-10-30「應該用 82*4 的那個 TL 權重」→「同賽季內曲線平滑，換賽季時曲線變陡」→「GO」

### E-130
- 日期：2026-10-30
- 假設：賽中防守加成拿掉 possW ≥ 2500 門檻（所有不到門檻的人，含 2026 新秀，照老將公式比位置平均）後，低樣本 centered D 對該季之後的 D 不比「給 0」差（MAE 差 ≤ +0.02），且 Spearman > 0。
- 做法：`reports/ovr-inseason-2026-27/e130-diq-no-gate/preregistration.md`（草稿）。開關 DEF_GATE（預設 2500 逐位元不變）；新秀 pos G／F 等用位置聯集算 posMeanD；新秀 OVR 也加 bonus。主判定在 2018-19／2020-21／2021-22，檢查點 10%／25% 聯盟進度，答案＝檢查點後單季擬合。和 E-128 改同檔，獨立 worktree 做、上線前等 E-128 合併。
- 已揭露：2026-10-28 頁沒有 DIQ 的 81 人名單、回合數、live D；posMeanD 五值。沒看過回測數字；無自由參數。
- 狀態：完成（2026-10-30），1/5 不採用：m1 兩檢查點都沒過（10% 差 +0.052、25% 差 +0.061，門檻 +0.02），三季全是正差；m2 ρ 0.070 險過。c0–c3 全過。程式改動留在 worktree `D:/Projects/CODING/ba-e130`（未 commit），報告 `e130-diq-no-gate/report.md`（在該 worktree）。見 F-069
- 相關：R-083、R-075、R-076、R-080、E-104、E-111、E-128
- 來源：使用者 2026-10-30「新秀沒有DIQ」→「也進 OVR」

### E-131
- 日期：2026-10-30
- 假設：卡片 OVR 迴歸拿掉 physique（身高＋體重/10 百分位），heightInches 與其他屬性留著、form／ridge 照原 CV 程序重選，樣本外 m1–m3 不明顯變差（門檻同 E-107／E-125）。
- 做法：`reports/card-0.2.7b+E131-no-physique/preregistration.md`。基準 card 0.2.7b（361bcac6…1105）；calibrate-wing.py 加 `--dropAttr`，K0 要逐位元重現 0.2.7b、K1 拿掉 physique；凍結後先跑 K0 的 c0。模擬引擎不動。
- 已揭露：card 0.2.7a／0.2.7b 全部欄位、0.2.7a 的 16 項係數（physique +0.231／10 分 SE 0.102，heightInches −0.752／10 吋 SE 0.518）；2025-26 bio × pooled RAPM 相關（體重 r +0.18、同身高下體重 r +0.11，448 人）。沒看過拿掉後的任何結果。方向由使用者選，不是盲測。
- 狀態：凍結（2026-10-30，使用者「凍結開跑」；sha256 bd56dc35…1263））。
- 結果（`reports/card-0.2.7b+E131-no-physique/report.md`，role-card Sonnet 子代理；lead 重算 c0 sha、屬性欄不變、具名名次、前 20、m1–m3 成立）：c0 逐位元、c1 57/57、u1 過；m1 +0.0015 [−0.0014, +0.0044]、m2 −0.0014、m3 +0.0013 全過；evaluate 18/19＝基準；2K27 ρ 0.738→0.733。heightInches 係數 −0.77→+0.10、rebound 0.03→0.10。前十不動，前 20 只換 1 人（Ausar 出、Anunoby 進）；Zion 43→65（81.8→79.8）、Randle 154→163、Herb Jones 16→19、Mobley 28→23；後衛沒升（SGA 105.0→104.6）。MIN≥1000 名次移動 ≥10 名 42 人，多在 200 名後。偏離 8 項見報告（ranking 仍輸出 physique 欄、預註冊寫的 −0.752 是 0.2.7a 值等），都不影響判定。
- 狀態：完成、判定全過（2026-10-30）；採用，發 card 0.2.7c（2026-10-30，R-084；R-064 前 300 名 36 人移動 ≥ 10 名本該 PATCH，使用者裁定 0.2.7c）
- 相關：E-125、E-123、E-076、E-085、F-034、F-039、R-002、R-042、R-064、L-026
- 來源：使用者 2026-10-30「phys 有什麼效果」→「所以說體格和影響力沒有正相關。不需要放在網站」→ 選項 2（連 OVR 也拿掉）

### E-132
- 日期：2026-10-30
- 假設：primary 卡讀的影響力改成自製先驗 RAPM（L2＝`rapm-prior.csv`，數據表先驗＋RAPM，類 LEBRON），在沒看過的季，卡片排序對該季純 RAPM × W(mpg) 比現行 K0 一致（Δρ 90% 下界 > 0）。
- 做法：`reports/card-0.2.7b+E132-lebron-target/preregistration.md`（草稿）。只換 primary 卡 `calibrate-wing.py --rapm`（回歸目標、align、封頂、defenseBonus），用人回歸的 rapm1 分半與 fitA／fitB 不換；K0 須逐位元重現 card 0.2.7b。階段 A 回測 2024-25 卡 → 2025-26（priors 要只用 ≤ 2024-25 重建，管線做不到就取消）；階段 B 前瞻 2025-26 卡凍結 → 2026-27 至 2027-01-31 的單季純 RAPM。rapm-prior 不准當答案（循環論證）。
- 已揭露：card 0.2.7a／0.2.7b、rapm.csv、rapm-prior.csv 全部欄位；E-012、E-079 結果。沒算過任何 L2 卡片結果。
- 狀態：凍結（2026-10-30，使用者「凍結開跑」；sha256 d6387bad…63b7，見 `preregistration.sha256`），派工中。原草稿含 L1（LEBRON），使用者 2026-10-30「只跑 L2」，凍結前拿掉。
- 結果（`reports/card-0.2.7b+E132-lebron-target/report.txt`，App Sonnet 子代理；lead 重算 c0 sha、具名名次、前 20、移動人數成立）：c0 逐位元（final 361bcac6…1105）、c1 57/57、d1、u1 過。**階段 A 取消**（calibrate-wing.py、fit.py 寫死 2025-26，補 2024-25 要改方法，`stageA-feasibility.md`），所以目前沒有任何樣本外證據；階段 B 卡已凍結（`prospective-freeze.json`，K0 primary be395339…、L2 0c0c0b4f…），2027-02 由 role-audit 算。預註冊缺口（lead 錯，L-079）：card 0.2.7b primary 的 defenseBonus 讀 `--defWindow season --defRapm def-L-primary.csv`，不經 `--rapm`，所以 L2 只換了目標、align、封頂三處；子代理照字面執行，寫 `errata-draft.md`。只報告：MIN≥1000 的 279 人中 124 人移動 ≥10 名；前 20 Herb Jones、Ausar 出，Murray、Maxey 進；防守型外線大降（Caruso 30→95、Herb Jones 16→72、Camara 34→83、Smart 59→107、Wagner 7→15），LeBron 75→54、Tatum 32→25、Reed Sheppard 235→176 升；evaluate 18/19→17/19（多掛 carusoGate）；2K27 ρ 0.738→0.742；樣本內對純 RAPM ρ 0.779→0.739（離開目標，非證據）。唯讀核對：`reports/ovr-rapm-calibrated-2025-26/fit.py` 執行中被別的 session 改（加 return 給 `reports/impact-epm-2026-27/epm_live.py` 用，輸出不變），2026-27 賽季資料 11 檔更新；兩張卡在變動前已產出，不影響。
- 狀態：完成，階段 A 取消、階段 B 待 2027-02（2026-10-30）；待使用者決定 errata 與要不要另立「連 defenseBonus 一起換」
- 相關：E-012、E-079、E-084、E-094、E-131、F-049、R-007、R-042、R-083、L-026
- 來源：使用者 2026-10-30「如果我們的 OVR 計算公式改成以 lebron 擬合 會怎麼樣」→「寫預註冊 spec」→「只跑 L2」

### E-133
- 日期：2026-10-30
- 假設：照使用者四原則改賽中 C4 的 b 段：δ² 分年齡（≤23／≥24，換季大降，無自由參數）＋本季逐場直線遺忘 w_j=max(0,1−s_a·j)，s_a=s0·u_a，u_a 依 δ²/σ² 相對值（不穩定項目忘得慢）。訓練選出的 W* 在沒跑過的 D1–D3 上 N=10/20 誤差比 C4 c=1 小、N=3/5 不變差。f＝N/G 不動；曲線形狀（指數）只報告。
- 做法：`reports/ovr-inseason-2026-27/e133-attr-decay/preregistration.md`（草稿）。候選 B0、M1、M2-a/b/c（s0 0.0025/0.005/0.01）；訓練 Y2、Y3、Y5、Y6（須過 c0x 鑑別力，L-078），測試 D1–D3 只跑 W* 對 B0；判定見 §2.4。
- 已揭露：E-033／v5／E-111／E-129 全部結果與 E-129 訓練格點表；reliability σ² 用 2022-25 估、與測試季重疊（基準同）。沒看過 D 起點在 027 下的誤差、分年齡 δ²、任何 M 候選結果。
- 狀態：凍結（2026-10-30，使用者「凍結開跑」；sha256 b01a4229…，見 `e133-attr-decay/preregistration.sha256`）；完成（2026-10-30）：W*＝B0（M1 J 只好 0.0003 算平手；M2 遺忘越快越差），依 §2.3 判「沒有改善」，不跑測試（F-071、L-080）。報告 `e133-attr-decay/report.md`；不採用（2026-10-30，使用者，R-090）
- 相關：E-033、E-111、E-129、F-070、L-026、L-074、L-078
- 來源：使用者 2026-10-30「go. so we agree that 1. per-game loss … 2. change season = huge loss 3. different attribute use different loss rate … 4. straight line first, curve undecided」

### E-134
- 日期：2026-10-30
- 假設：E-132 的 L2（卡片讀先驗 RAPM，這次 defenseBonus 也換成先驗版 def-L）用舊季滾動原點回測：t 季資料建卡，對 t+1 季純 RAPM × W(mpg) 的 ρ 比 K0 高。階段 0 只比輸入（數據表先驗 RAPM vs 純 RAPM 預測下一季，原點 2018-19～2024-25 扣 2021-22）；階段 1 卡片層（原點 2022-23～2024-25，alpha=1 兩臂同）。
- 做法：`reports/card-0.2.7c+E134-rolling-prior/preregistration.md`（草稿）。基準 card 0.2.7c；c0 參數化管線須逐位元重現正式卡。
- 已揭露：E-132 全部 2025-26 結果、使用者偏好（Tatum 升、Wagner 降）；沒看過任何舊季卡、先驗或跨季 ρ。
- 狀態：階段 0 完成，使用者 approve；階段 1 範圍 A 凍結（2026-10-30「凍結開跑」；sha256 631ee711…，見 `preregistration-stage1.sha256`）；deviation-1（舊季官方資料補抓，使用者「直接補抓官方資料」）、deviation-2（屬性層兩組共用、只當輔助證據，使用者「共用屬性層繼續」）；階段 1 完成（2026-10-30 20:41 凍結卡），判定「沒變差」，等使用者決定採不採用
- 結果（階段 0，2026-10-30）：變準。先驗 RAPM 預測下一季純 RAPM × W，合併 Δρ +0.033 [90% +0.018, +0.047]，n=2091，6/6 原點 >0（+0.049/+0.054/+0.016/+0.047/+0.010/+0.022）；不乘 W 同結論。H2（修正集中在低樣本）不成立，低樣本組太小。c1、leak、唯讀核對過；lead 從 players-*.csv 重算各原點 Δρ 相符。量的是數據表先驗做法，不是卡片；卡片層看階段 1。
- 結果（階段 1，2026-10-30）：沒變差，但 0/3 原點 >0。卡片 L2−K0 合併 Δρ −0.006 [90% −0.015, +0.003]，n=968（−0.0015／−0.0126／−0.0037）；不乘 W 同結論。K0 與 L2 卡名次相關 0.98，輸入層的 +0.033 進卡片後被屬性回歸稀釋到看不出。H2 低樣本組 −0.055（n=53，區間寬）。Caruso、Herbert Jones 被 L2 壓低（F-078）。c0、c0p、c0d、c1、leak、u1 過；lead 從 players-*.csv 重算三原點 ρ 與卡 sha256 相符。已知偏離：屬性層含 >t 資訊（兩組共用）、人群限屬性層 582 人。報告 `stage1/report.txt`
- 相關：E-012、E-079、E-111、E-126、E-132、L-079、R-007
- 來源：使用者 2026-10-30「we dont need to wait til next feb. we can use old data but start rolling forward」→「查完再寫」

### E-135
- 日期：2026-10-30
- 假設：護框長人的 `doubleThreat` 被體格項（0.25）推高，在場時隊友的被包夾率下降、命中率上升，這份隊友紅利算進他的 WinImp。拿掉體格項（E-086 ch1，固定移除）後，頂端長人的高估會變小（loop.md H10）。
- 做法：`reports/sim-0.1.0+E135-dblthreat-phys/preregistration.md`（草稿）。基準 sim 0.1.0 legacy，對照直接用 E-102 merged-legacy（60 樣本，X 計分）。閘：g0 關閉逐位元、g1 npm test、m1 同季重現 3 seed 中鋒隊友 FG% 誤差縮小且球隊得分 RMSE 不差超過 0.2、b1 OOS ΔS 聯合 90% 下界 > 0、b3 OOS ρ 不降超過 0.02。
- 已揭露：E-086 ch1 在 100 人 × 8 樣本 ΔS −3.70（分不出）；假設來自 `profile.py`（E-102 殘差對 v41 2025-26 同季逐人誤差，看過答案，不算證據）。
- 狀態：完成 1/5「失敗」（2026-10-30 18:01）：b1 不過（OOS ΔS 0.30，聯合 90% [−1.29, 1.92]），b3 過（ρ 0.417→0.414）；六個頂端長人名次幾乎不動（Gobert 7→7、Duren 9→9），前 20 中鋒 10→11。報告 `reports/sim-0.1.0+E135-dblthreat-phys/report.txt`（F-073、L-081）。不算長人偏袒修正；但使用者依奧坎剃刀裁定刪掉體格項，併進 sim 0.1.1（R-089，2026-10-30）。以下為執行中紀錄：凍結（2026-10-30，使用者「核可」；sha256 454e4cc4…a169）。g0 過、g1 過、m1 過（執行修訂 A：m1 改用現行引擎 30 隊單循環，見 amendment-A.md）；全量 5090 2026-10-30 13:52 開跑。注意：真實球員的 doubleThreat 被 sourceDouble 量測錨點抵銷，ch1 只改到平均隊友，原機制在現行引擎不成立（amendment-A 補記）
- 相關：E-086、E-102、E-076、E-087、F-068、L-023、L-026、R-041、loop.md H10
- 來源：使用者 2026-10-30 選「2」（找頂端長人被高估的原因，量尺用 60 樣本）

### E-136
- 日期：2026-10-30
- 假設：賽中 OVR 改成逐場卡爾曼濾波（每場 P+q_a、換季 P+δ²_a、指數權重 λ_a 由 θ 推出並夾在 [0.95,1]），顯示值改成能力估計 m（拿掉 f·y）。訓練選出的 W* 在 D1–D3 上，逐場 |ΔOVR| P95 比 C4 小一成以上、鋸齒比不變大，季末預測準度不變差（每格 ≤ +0.05）。
- 做法：`reports/ovr-inseason-2026-27/e136-kalman-display/preregistration.md`（草稿）。候選 B0、K0–K3（θ 0／0.25／0.5／1）；訓練 Y2、Y3、Y5、Y6，測試 D1–D3；沿用 E-133 程式。階段 B（卡片＝季末濾波狀態）另開實驗。
- 已揭露：E-033／v5／E-111／E-129／E-133 全部結果；沒看過任何方法的逐場跳動量、D1–D3 誤差。
- 狀態：凍結（2026-10-30，使用者「凍結開跑」；sha256 0c872cec…f9f6，見 `e136-kalman-display/preregistration.sha256`），phase 0 停下（lead spec 漏四個定義）；errata-1 使用者核可（「核可並續跑」，見 `errata-1.sha256`），續跑中；errata-2 草稿（2026-10-30，使用者選「E-136 加 errata-2」：每個 K 候選加雙胞胎 KjM，分鐘項也走逐場濾波，見 `errata-2.md`）使用者核可，另加 §1.1 KjM3（k_M ×3），共 13 候選（sha256 b35a7b34…f3ae，見 `errata-2.sha256`），續跑中；完成（2026-10-30）：判定「採用候選」，W*＝K0（只拿掉顯示的 f·y，能力估計與準度和 C4 逐位元相同）。S1 比值 0.782 [0.772, 0.792]、S2 0.943；θ>0、分鐘濾波都沒勝出；S4 D2 略差。role-audit 2026-10-30 判定站得住（4/5），但準度關卡對 K0 是恆等式，實際顯示值在 N=10/20 較慢（F-077、L-084）；等使用者 G5（F-076）。報告 `e136-kalman-display/report.md`、`report.txt`
- 相關：E-033、E-111、E-133、F-070、F-071、R-090、L-026、L-078、L-080
- 來源：使用者 2026-10-30「for the sake of consistency … we want the OVR to move consistency and promptly」（原則同 E-133 四條）→ lead 建議指數曲線 → 「寫草稿」

### E-137
- 日期：2026-10-30
- 假設：自製 EPM 的防守 box 先驗（現行 dreb、stl、blk、pf、height；onoffSaved 本季填 0）加入追蹤數據（破壞傳球、兩分／三分干擾、防守卡位、製造進攻犯規、六呎內命中壓制、對位負擔）後，t 季特徵預測 t+1 季純 RAPM D 的 Spearman ρ 比基準高。
- 做法：`reports/impact-epm+E137-tracking-def/preregistration.md`（草稿）。季對 2022-23→23-24、23-24→24-25、24-25→25-26，留一組季對擬合；答案 E-126 單季 RAPM D；人群 t 季 MIN ≥ 500 且 t+1 回合 ≥ 1000。判定：合併 Δρ 90% 下界 > 0 且 ≥ 2/3 季對 > 0 為變準。只顯示，不進 OVR。
- 已揭露：T2 穩定性表（特徵間跨季相關，含答案季）、四因素報告（2022-26 合併 RAPM D 拆解）、現行 box-weights 權重；沒看過任何追蹤特徵對單季 RAPM D 的相關。
- 狀態：草稿（2026-10-30），等使用者凍結
- 相關：E-126、E-134、R-062、R-086
- 來源：使用者 2026-10-30「防守只看抄截、阻攻太偏」→「先查資料覆蓋」→「寫預登記」；資料覆蓋見 `reports/defense-tenth/step4-t2/`

### E-138
- 日期：2026-10-30
- 假設：賽中顯示改成「K0＋線性／凸遺忘＋季末線性回歸單季卡」，預測之後 20 場表現比 B0、K0 準，單場跳動不超過 B0。
- 做法：`reports/ovr-inseason-2026-27/e138-recent-form-display/preregistration.md`（草稿）。13 候選（L／Q × H 30、60、120 × Rf、R4，加 F0R4）；爆發組（林來瘋、新秀、二年級生）追上場數不慢於 B0 是硬條件，訓練 Y2、Y3、Y5、Y6 選 W*，測試 D1–D3 只跑 W*、B0、K0。
- 已揭露：E-133／E-136 全部結果（季內遺忘對季末卡較差；D1–D3 B0、K0 軌跡）；沒看過任何方法對「之後 20 場」的誤差。
- 狀態：凍結（2026-10-30，使用者「Go」；sha256 f3d1e1d9…f394，見 `e138-recent-form-display/preregistration.sha256`）；phase 0 停下（c0n：N=60 要打滿 80 場，每格 0–53 人）；errata-1 使用者核可（選「1」：N=60 只報告，J 用 N=10、20、40；sha256 b93e060c…ba62）；訓練階段停下（2026-10-30）：7 候選比 B0 準 ≥0.01、其中 L120R4／Q60R4／Q120R4／F0R4 也較穩，但爆發組追上場數全部比 B0 慢（B0 14 場，它們 17–19），合格 0，§2.5 沒寫「有更準但沒合格」怎麼判，lead 從 train.csv 重算 J 一致；errata-2 使用者核可（「Allow 3 slower」：T ≤ B0＋3 場，看過訓練結果後放寬，已揭露；sha256 1c70cb3c…b12c），W*＝L120R4；完成（2026-10-30）：判定「反應太慢」（準度、穩定都過，爆發組 T 17 > B0＋3＝16），不採用（F-080）
- 相關：E-136、R-091、R-092、F-077
- 來源：使用者 2026-10-30「採用 k0+線性遺忘（或是保守一點用凸曲線）」

### E-139
- 日期：2026-10-30
- 假設：在 L120R4（E-138）上減輕開季先驗權重，爆發組追上場數不慢於 B0，同時比 B0 準、不比 B0 晃。
- 做法：`reports/ovr-inseason-2026-27/e139-prior-weight/preregistration.md`（草稿）。6 候選：全員乘 0.5／0.25（PA）、只對新秀／二年級／上季 MIN<1000 乘 0.5／0.25（PY）、先驗前 20／40 場線性淡出（PF）。訓練 Y2、Y3、Y5、Y6；測試 D1–D3 只跑 W*、B0、R0。
- 已揭露：D1–D3 第三次使用（看過 B0、K0、L120R4 軌跡與 5 名爆發球員例子，想法由此而來）；沒看過任何先驗乘數的數字。另加 2026-27 前瞻檢查。
- 狀態：草稿（2026-10-30），等使用者凍結
- 狀態更新：草稿第二版（2026-10-31，使用者「Add rookies」）：E-138 母體要上季卡，真新秀（Flagg、Boozer 型）全被排除。補真新秀層：x0 照 E-121 程序逐屆重建（不重擬合），基準 B0r＝線上 `eval_rookie`；新秀不參與選 W*，另設新秀關卡（J 上界 ≤ +0.10、T ≤ B0r、S1 ≤ B0r）決定新秀一起套或維持線上；phase 0 加 c0k（重現 2026 屆 x0）、c0b、c0n（人數不足改只報告）。揭露 D3 新秀看過 E-116／E-121 回看。等使用者凍結
- 狀態更新：已凍結（2026-10-31，使用者「凍結開跑」；sha256 bb10375e…c666，見 `preregistration.sha256`；git HEAD 1383c36），執行中（role-card）
- 狀態更新：phase 0 停在 c0k（2026-10-31）：平移前形狀等全同，差在每日錨點漂移（δ 最多 0.095）與新增 Karim López；老將 c0r／c0e／c0p 過。errata-1（使用者「B, defense frozen」）：c0k 只比平移前形狀、δ 改到 c0b 驗；新秀層所有臂防守兩項固定在 x0。沒看過任何候選數字。續跑中
- 狀態更新：完成（2026-10-31）：phase 0 全過（新秀訓練 148／測試 107 人）；訓練無合格者 → 判「沒有改善」，測試與新秀關卡依規定不跑。最接近 PY50（差在爆發組 16 場對 B0 14）。線上維持 B0（F-087）
- 相關：E-138、F-080、R-092、R-093、E-116、E-121
- 來源：使用者 2026-10-30「Draft E-139」

### E-140
- 日期：2026-10-31
- 假設：開防守者犯規 β 後，用一個犯規基準位移 c 和節奏乘數 pace 重校，能讓聯盟犯規率、回合數、得分回到關閉版水準（k1）。
- 做法：`reports/E140-foul-on-recal/preregistration.md`（sha256 見同目錄 `.sha256`）。校正 seed 20261100–115，判定 seed 20261028–059；球隊 MAE、t1、WinImp S 與名次只報告。
- 已揭露：看過 E-120／E-122 全部結果與聯盟平均漂移（得分 −0.23、回合 −0.05），沒看過重校後數字。
- 狀態：已凍結（2026-10-31，依使用者 R-094 指示由 lead 凍結並執行）
- 狀態更新：修正 A1（2026-10-31，任何結果產出前）：基準改現行 HEAD 引擎，關閉版對照全部重跑（`amendment-a1.md`，L-085）；執行中
- 狀態更新：完成（2026-10-31）：k0、k1 過，重校成立（F-096）；長人偏袒 S 不變、Holiday／Caruso／Smart 降。執行中發現 5090 harness 把 pace 蓋成絕對值 1，校正作廢重跑（cal-buggy/），判定全用修正版。引擎選項與 harness 未 commit
- 狀態更新：採用（2026-10-31，使用者「1」）：sim 0.1.2＝`reports/player-impact-v29/benchmark.mjs` 的 `options()` 預設帶 β、c=−0.03125、pace×0.99875；預設路徑重跑判定 seed 20261028–029 共 870 場與 rr-on 逐場相同，npm test 52 過。之後 E-140 harness 的 `--beta on` 會重複套用，不能再用
- 相關：R-094、E-120、E-122、F-065、F-067、F-079、L-082

### E-141
- 日期：2026-10-31
- 假設：新秀起點的齊頭扣分從 −5 減到 −2.5 或 0 後，真新秀前 0／5／10 場的賽中 OVR 對之後 20 場視窗卡更準（測試季 D1、D2 的 J 差 90% 上界 < 0）。
- 做法：`reports/E141-rookie-start-shift/preregistration.md`（草稿）。候選 B0r（−5）、S25（−2.5）、S0（0），S+25 只報告；訓練 Y2、Y3、Y5、Y6 選 s*（平手取扣多的），測試 D1、D2；x0 重建與真新秀定義沿用 E-139 §0.5，E-139 完成後才開跑。
- 已揭露：2025 屆（D3）E-116／E-121 回看的 MAE 與偏差（起點偏 −6.5、只看自己偏 −5）；2026 屆 5 場內只看自己 OVR（Boozer 76.5、Lendeborg 74.6 對線上 72.5、64.6）。沒看過任何 s ≠ −5 的數字。D3 只報告。
- 狀態：草稿（2026-10-31），等使用者凍結
- 狀態更新：已凍結（2026-10-31，使用者「凍結」；sha256 e53926ef…1455，見 `preregistration.sha256`；git HEAD 1383c36）。等 E-139 跑完再派 role-card
- 狀態更新：errata-1（2026-10-31，使用者「GO」，結果產出前）：E-139 新秀層程式還不存在，不等；照 E-139 §0.5 文字自己實作，c0k 仍為硬關卡，c0r 改只報告，新增 c0d 邊界說明（`errata-1.md`）。派 role-card 執行中
- 狀態更新：errata-2（2026-10-31，使用者「核可繼續」，候選結果產出前）：c0k 沒過（最大差 0.095），原因是 E-121 上線後 live 錨點改版、δ 重解不同，形狀與目標都對；c0k 換成 shape／target／solve 三項（`errata-2.md`）。繼續執行
- 狀態更新：完成（2026-10-31），2/5「維持 −5」：訓練選 s*＝−2.5（J 6.27→6.01），測試 D1/D2 65 人 J 6.52→6.23，但 90% 上界 +0.05 未過①，前十順位 5.10→6.13 未過②，③過。lead 從 rookie-players.csv 獨立重算一致。偏差分層相反（前十 +2.3、31 後 −5.5），見 F-086。線上不動
- 狀態更新：2026-10-31 使用者看 F-086 圖後直接裁定新起點曲線 73 − 5.9·ln 順位（R-096，產品決定、看過答案，非盲測），已上線
- 相關：E-116、E-121、E-139、R-073、F-060、F-063
- 來源：使用者 2026-10-31「調查一下新秀的起始點會不會太低」→「開實驗」

### E-142
- 日期：2026-10-31
- 假設：卡片迴歸目標從四季合併 RAPM 換成一體化數據（自製 EPM 式、EPM、LEBRON、DARKO、BPM、等權平均）後，測試季（2023-24、2024-25）綜合分 C＝0.4·薪水＋0.3·2K＋0.15·下季 RAPM＋0.15·模擬（模擬不穩則 0.45／0.35／0.2）比現行高。
- 做法：`reports/E142-card-target/preregistration.md`。迴歸設定照 0.2.7c 只換目標欄；外部數據放 gitignore，不轉載。
- 已揭露：2025-26 box 先驗與 0.2.7c 的 Flagg／Banchero／Knueppel 名次、F-072；沒看過任何外部一體化數據與候選卡片。
- 狀態：已凍結（2026-10-31，使用者「凍結」；sha256 dc1624bb…1c0c，見 `preregistration.sha256`；git HEAD e4d121f）。派 role-card 執行
- 狀態更新：errata-1（2026-10-31，使用者澄清「到合約第三年……薪水的權重要下降」，指標產出前）：M_sal 主指標改為在約非新秀約依合約年次加權 1／1／0.7／0.5／0.3，新簽約改只報告（`errata-1.md`，sha de5c389c…b817）。第 0 階段 c0／c0d／c0l 與 c0s 已派出
- 狀態更新：第 0 階段 c0／c0d／c0l 完成（commit 7b1e1b4）：T0 逐位元重現；T1／T4 DARKO／T5 BPM 留下，T2 EPM、T3 LEBRON 付費刪除；只剩 2022-23～2025-26 四原點。errata-2（2026-10-31，使用者「權重照舊，這個人沒有的話權重就分給其他項目」「先算不用等子代理」；sha d20e0a25…a064）：訓練 2022-23、測試 2023-24／2024-25；C 改為 OVR 對逐人合成參考分的 Spearman，缺項權重按比例重分配；判定一律用補齊後的 2K。第 1 階段暫時版、2K 補抓、c0s 三個子代理執行中
- 狀態更新：errata-3（2026-10-31，使用者「三折」；sha a34ce181…fb976，commit 56f0435）：2022-23／2023-24／2024-25 輪流測試，兩季選 T*。c0s 不過（名次 Spearman 0.985 過，但長人偏袒 S 區間寬 49–56 > 30；f94e322），模擬項不計。
- 狀態：完成（2026-10-31），判定 adopt：上線候選 T6（DARKO＋BPM 季內 z 平均）；三折 T*＝T6／T6／T4；樣本外 C +0.020（90% 下界 +0.0017）、薪水 +0.037、2K +0.037、下季 RAPM −0.033（容忍 0.05 內）。2025-26 主卡只換 RAPM 半，C 0.655 對 T0 0.667（只報告），Flagg 264→292 名（MIN≥500）。`report.md`、`phase1.json`。
- 狀態更新：稽核（2026-11-01，94b622b，`audit/audit.md`）：獨立重算逐位一致、雜湊與時序成立、2025-26 主卡只換 RAPM 半屬實。疑慮：結論依賴三折設計：改回 errata-2 單季訓練判不過（選 T4、RAPM 退超容忍）；舊 2K 檔下界貼 0。暫時版早 69 分鐘產出，無法用 git 證明沒人看過（lead 沒讀過；三折由使用者先提出）。等使用者裁定是否接受三折、是否等 2026-27 樣本外再上線
- 相關：R-093、F-064、F-070、F-072、F-068、E-134
- 來源：使用者 2026-10-31「比較各種 EPM lebron 或其他一體化數據的版本……metric 用薪水、小量rapm、模擬」「metric還有2k」

### E-143
- 日期：2026-10-31
- 假設：頂端長人（Gobert、Queta、Duren、M. Robinson、Clingan）在 sim 0.1.1 WinImp 的加分，有一組管道（防守／籃板／進攻／體格）單獨占一半以上（R ≥ 0.5 且 > 2se，≥ 3 人）。
- 做法：`reports/sim-0.1.1+E143-channel-ablation/preregistration.md`。把球員該組欄位換成同 slot 對照人（xAvg.profiles[slot]）的值，60 樣本 × 30 對手，人群用 E-135 ch1-60 的 379 人。8 人（主角 5＋Jokić、Dort、H. Jones）× 6 版，5090。
- 已揭露：E-135 名次、F-081～F-085；沒有可調參數、不碰答案。
- 狀態：完成（2026-10-31），4/5：籃板 5/5 人達標（R 0.51～0.87），防守 0/5（Gobert 0.37、Queta 0.40），進攻、體格 0/5。g0 逐位重現 E-135、g1 全關差 0、npm test 過。原編號 E-142 撞號（另一 session 的卡片目標實驗），結果產出前內容已凍結、事後只改編號，見 F-088
- 相關：F-084、F-085、F-081、E-135、loop H17
- 來源：使用者 2026-10-31「寫預註冊再跑」


### E-144
- 日期：2026-10-31
- 假設：E-143 籃板組的加分，有一塊（進攻籃板 individualOreb／防守籃板 rebound＋dreb 分配／補籃）占一半以上（≥ 3 個頂端長人）。
- 做法：`reports/sim-0.1.1+E144-rebound-split/preregistration.md`。同 E-143 替換法，版本 oreb／dreb／putback／reb3，8 人 × 60 樣本，5090。
- 已揭露：E-143 全部結果；開跑前 40 場機制檢查（只看方向）。
- 狀態：已凍結（2026-10-31，使用者「拆籃板三塊」）；完成 4/5（2026-10-31，F-093）
- 相關：E-143、F-088、F-081、loop H17
- 來源：使用者 2026-10-31「拆籃板三塊」

### E-145
- 日期：2026-10-31
- 假設：單場評分改成 M2＋負擔＋在場正負值、分鐘縮回、整場總量（M3）後，2025-26 B 半：單場評分 vs 球隊淨勝分、球員平均評分 vs 自製 EPM 都比 M2 高，用掉回合前 30 人的評分名次往前，且 DARKO／前後半季穩定度不退步。
- 做法：`reports/rating-m3/spec.md`（β 在 A 半格點選，params.json commit 後才算 B 半與 2026-27）。
- 已揭露：M2 整季口徑基準（單場 vs 淨勝分 0.284、vs 自製 EPM 0.772、DARKO 0.532、前後半季 0.602）；Caruso／SGA／Wemby 2026-27 單場拆解；2025-26 整季 M2 基準 SGA 8.3、Wemby 8.0、Caruso 7.0。沒看過任何 M3 候選的數字。
- 狀態：已凍結（2026-10-31，使用者「核准，派工」；spec sha256 41cea481…c762，見 `spec.sha256`）。派 role-card 執行
- 狀態更新：完成（2026-10-31，commit 87a8ca4 參數先凍、e41d609 報告），2/5「不採用」：T1 單場 vs 淨勝分 0.277→0.273、T2 vs 自製 EPM 0.679→0.667 兩條必過沒過，頁面維持 M2、R-062 不改。選中 β_u＝0、β_q＝0.2、K≈301 分鐘。見 F-089
- 相關：R-062、E-110、E-105、F-055、L-026
- 來源：使用者 2026-10-31「評分有點怪。高估防守專家、上場 2 分鐘拿 6 分，低估球隊主力得分手 SGA WEMBY」「往這三項靠」

### E-146
- 日期：2026-10-31
- 假設：單場評分改成 M2＋在場正負值、往聯盟平均輕縮回（K 取讓短時間場次不擠進前 6% 的最小值）、整場總量、拿掉負擔（M4）後，2025-26 B 半：單場 vs 淨勝分、平均 vs 自製 EPM 都不輸 M2，用掉回合前 30 人名次往前，30 投 6 中這類爛場給低分，DARKO／前後半季不退步。
- 做法：`reports/rating-m4/spec.md`（β_q 與 K 在 A 半照規則選，params.json commit 後才算 B 半與 2026-27）。
- 已揭露：E-145 全部 A／B 半結果（β_u 越大越差、β_q＝0.2 在格點上限、無 q 版 T1 0.154、K≈300 過重）。沒看過任何 M4 候選的數字。
- 狀態：已凍結（2026-10-31，使用者「GO」；spec sha256 見 `reports/rating-m4/spec.sha256`）。派 role-card 執行
- 狀態更新：完成（2026-10-31，commit d370f50 參數先凍、32d1641 報告與頁面），判定六項全過，lead 獨立重算 T1 0.478、T2 0.758、A4 0.4% 對得上。選中 β_q＝0.1（再大超過 q 佔比 30%）、K＝0（縮回實質關閉）。T1 進步大半來自 q（β_q＝0 版 T1 0.277）。頁面改 M4 已 commit，使用者「上線 M4」，gh-pages 2bbf664 發布，R-099 取代 R-062 評分部分
- 相關：E-145、F-089、R-062、L-026
- 來源：使用者 2026-10-31「主力球員的賽季平均是高分就好，可以接受他打不好就給低分（例如30投6中）」「GO」

### E-147
- 日期：2026-10-31
- 假設：卡片 usage 層的爛隊旗標 d 從「主隊全季勝率 < 0.35」改成和賽中相同的連續公式（+/- 混勝負，clip((0.40−s)/0.10)），並重擬合係數（D1）。這樣季末賽中卡會等於季末卡，外部指標也不會變差。
- 做法：`reports/card-0.2.7c+E147-continuous-d/preregistration.md`（sha 41fac408…9a47）、`e147.py`。唯讀匯入 e094，只替換 scope_feats 的 d。臂：K0（c0＝0.2.7c）、D1 主臂、D0（套 K0 係數，只用來診斷）。
- 已揭露：0.2.7c 的薪水／2K／EPM 相關；固定錨點粗估的變動。沒有可調參數。
- 狀態：完成（2026-10-31），判 2/5，預註冊的 (b) 沒過。
  - c0 逐位元過；一致性依構造成立；m1–m3 都過，點估計 +0.002～+0.006。
  - M2K ≤23 歲 0.4485→0.4379（−0.0106，門檻 −0.01）；其他持平。
  - b8 −0.464→−0.575（變重）。
  - Flagg 61.5→68.3；Fears／Queen／Missi +9～11；Rollins 86.2→76.0 掉出前 20、Giddey −6.7。
  - 等使用者決定。
- 狀態更新：2026-10-31 使用者「AB先上線」→ 採用為 card 0.2.7d（R-098，看過結果的裁定）
- 相關：F-090、R-097、E-124、E-127、R-082
- 來源：使用者 2026-10-31「卡也改連續 d」

### E-148
- 日期：2026-10-31
- 假設：把 M4 的正負值換成「非垃圾時間（第四節起比分差 ≥20 的段排除）裡在場每 36 淨分減全隊同期每 36 淨分」，並在 A 半用 EPM＋DARKO（不含淨勝分）選 β_q 後，2025-26 B 半：大勝場投很差的人評分低於自己中位數的比例 ≥70% 且高於 M4，垃圾時間刷分場擠進前 10% 的比例低於 M4，EPM／DARKO／穩定度／主力名次不退步。
- 做法：`reports/rating-m5/spec.md`（2025-26 stints `reports/defense-b1/stints.jsonl`；先過資料檢查 V0，再 A 半選參數、commit 後才算 B 半）。
- 已揭露：E-146 全部結果（β_q＝0.1 卡在 q 佔比上限、β_q＝0 版 T1 0.277／T2 0.702）、Mitchell 18 投 5 中 M4 7.3。沒看過任何相對正負值或扣垃圾時間的數字。
- 狀態：已凍結（2026-10-31，spec sha256 見 `reports/rating-m5/spec.sha256`）；使用者「核准，派工」
- 狀態更新：完成（2026-10-31，commit 4de54f7 參數先凍、2af406f 報告），判定 8 項 4 項不過、不採用：大勝爛場低於中位比例 0.40→0.67（門檻 0.70）、vs 自製 EPM 0.758→0.711、DARKO 0.534→0.485、前後半季 0.548→0.481、30 投 6 中類 0.807→0.773。頁面維持 M4。見 F-092
- 相關：E-146、R-099、F-091、L-026
- 來源：使用者 2026-10-31「正負值該怎麼調整」→ 選方案「3」（相對正負值再扣垃圾時間）

### E-149
- 日期：2026-10-31
- 假設：usage 層加一項 y·d·L·p（爛隊年輕人扣分隨能力 p 縮放），重擬合後能力高的爛隊年輕人（Flagg 等）扣得少，低能力刷子照扣，外部指標與 m1–m3 不退步。
- 做法：`reports/card-0.2.7d+E149-ydLp/preregistration.md`（sha bb16effd…d026，commit 4797c87 先凍結）、`e149.py`。唯讀匯入 e147，只替換 design()。臂：K0（c0＝0.2.7d）、Q1。
- 已揭露：0.2.7d 全部結果、Flagg 等人的 p。沒有可調參數。
- 狀態：完成（2026-10-31）。形式判定過（c0 逐位元、四個外部指標變動 ≤0.0005、m1–m3 都過），但效果不存在，建議不採用、等使用者決定。
  - b9_ydLp −0.011（全季）；兩個半季方向相反（AB −0.136、BA +0.113）。b8 −0.575→−0.587。
  - m1–m3 點估計 −0.005，90% 區間整段 < 0（小但一致地變差，仍在門檻內）。
  - Flagg 68.3→67.8；Rollins 76.0→75.5；Carrington 37.8→38.1。前 20 不變，前 300 移動 ≥10 名 1 人。
- 相關：E-147、F-094、R-098、L-026
- 狀態更新：2026-10-31 使用者「維持」→ 不採用，卡維持 0.2.7d
- 來源：使用者 2026-10-31「如何讓flagg賽季變高，但不影響其他爛隊刷子（acuff」→ 選方案「二」

### E-150
- 日期：2026-10-31
- 假設：在 M4 整場總量上加「扛出手量加分」B＝f·(2λ·E·TSA＋g·2(TS_lg−TS_repl)·E)。其中 E 是比平均多扛的出手回合，及格線 TS_lg−λE 會隨量下降，f 以 δ＝0.10 線性減免。2025-26 B 半檢查：高量有效率場高於本人中位比例 ≥80% 且高於 M4；高量略低效率場平均高於 M4；低量場不變；主力名次前進；30 投 6 中類仍低；EPM／DARKO／穩定度各不掉超過 0.03。
- 做法：`reports/rating-m6/spec.md`（sha256 見 `spec.sha256`）。λ＝0.003（A 半主力缺陣自然實驗，Wald −0.29pp／次，90% 區間 −0.76～+0.19）、g＝1、δ＝0.10 由使用者裁定固定；其他常數只用 A 半，params.json 先 commit 才算 B 半。
- 已揭露：E-145／146／148 全部結果；lead 用 2025-26 整季常數在 2026-27 單場看過 A–E 各版例子（Barnes 5.0→10.7、Brunson 3.8→5.1 等）。B 半沒看過任何 M6 數字。
- 狀態：已凍結（2026-10-31），使用者「執行」
- 狀態更新：完成（2026-10-31，commit 1aa5741 參數先凍；報告 `reports/rating-m6/report.md`）。判定 6 項，C2 不過：低量組 M6 不等於 M4，原因是 spec 寫法（TSA ≤12 含 32% E>0 的短時間場、a'/c' 重新定尺度）。其餘都過：C1 0.775→0.906、T3 37.5→25、T4 0.841、EPM 0.758→0.737、DARKO 0.534→0.563、前後半 0.548→0.659。依 spec 不採用，等使用者裁定。見 F-095
- 狀態更新：使用者 2026-10-31 回「A」：C2 判為 spec 寫法錯誤，採用 M6（R-101）。頁面已換成 M6，每日流程 dry-run 驗過。
- 相關：E-146、E-145、R-099、L-026
- 來源：使用者 2026-10-31 看 Barnes 41 分 M4 5.0：「34/19 效率很驚人吧」→「以平均出手、效率為及格分…可以疊加」→「扛產量命中率會下降…應該給更多額外加分」→「高出手的 46% 跟低出手的 46% 不給一樣的分數」→「執行」

### E-152
- 編號：2026-11-01 改號（原誤記 E-150，與評分 M6 撞號）；報告資料夾 `card-0.2.7d+E150-age-curve` 與 E-151 預註冊內的「E-150」都指本條
- 日期：2026-10-31
- 假設：usage 層年齡旗標從斷崖（≤23、≥31）改成連續 yc＝max(0,25−年齡)、vc＝max(0,年齡−29)（A1），或再加好隊年輕人項 yc·g·L（A2，g＝clip((s−0.60)/0.10)），外部指標與 m1–m3 不退步。
- 做法：`reports/card-0.2.7d+E150-age-curve/preregistration.md`（sha 17d30cbc…e7ba，commit 89156c6 先凍結）、`e150.py`。K0（c0＝0.2.7d）、A1、A2 候選，A1y（只改年輕側）只診斷。
- 已揭露：E-081 年齡分組殘差、Podz／Edwards／Flagg 名次、各隊 s。沒有可調參數。
- 狀態：完成（2026-10-31），兩個候選都不過，依規則維持 0.2.7d。
  - A1：Msal −0.013、Mdarko −0.012 超過門檻；m1–m3 平均 −0.001。LeBron 72→165、Curry 31→75、Durant 26→59；Flagg 230→310；Podz 41→53、Edwards 38→29。
  - A2：M2K ≤23 −0.025、Mepm −0.013 超過門檻；b9_ygL +0.106（好隊年輕人加更多，方向和假設相反）。Harper 53→10、Castle 63→12、Holland 112→19；Flagg 230→359；Podz 41→77。
  - A1y（只診斷，不能採用）：五個外部指標變動都在 0.01 內（最差 M2K ≤23 −0.007），m1–m3 約 0；Podz 41→54、Edwards 38→31、Flagg 230→307。
  - 連續年齡讓 b8_ydL 從 −0.575 縮到 −0.154，爛隊年輕刷子回升（Clayton 44.8→54.3、Raynaud 40.5→52.0）；Flagg 反降，因為 19 歲 yc＝6 讓年輕×時間與年輕×爛隊項放大。
- 相關：E-081、E-147、E-149、F-098、L-026
- 來源：使用者 2026-10-31「go」（年齡曲線＋好隊年輕人）


### E-151
- 日期：2026-11-01
- 假設：只把年輕旗標改連續（yc＝max(0,25−年齡)，老將仍 ≥31 二元；即 E-152 的 A1y），用 2026-27 沒看過的資料驗收時，年輕人（≤24）卡片 OVR 與當季 RAPM 的相關比 0.2.7d 高。
- 做法：`reports/card-0.2.7d+E151-young-curve/preregistration.md`（sha 2789202e…07e，commit 6820474 先凍結）、`e151_eval.py`（sha 72abd474…f4）；K0／A1y 排名複製進資料夾凍結。答案＝2026-27 純 RAPM（無先驗，rapm.py CV 選 λ），stints ≥450 場才評估（凍結時 74 場）。採用條件：年輕子群 Δρ ≥ +0.01、其 90% 下界 > −0.02、全體 Δρ ≥ −0.005。
- 已揭露：E-152 全部結果（A1y 是看過結果才挑的）；看過 2026-27 epm-live 前段與 Edwards／Podz 名次，未把 2026-27 數字對過卡片。
- 狀態：已凍結（2026-11-01），等 2026-27 達 450 場；每日排程 step_prereg_e151 達標自動跑一次（使用者「GO」）
- 相關：E-152、F-098、L-026
- 來源：使用者 2026-11-01「預註冊只改年輕側」

### E-153
- 日期：2026-11-01
- 假設：在 card 0.2.7d 底上把迴歸目標整個換成 T6（含 2025-26 的 B12 目標表那半），E-142 的結論（C 升、薪水／2K 不退、RAPM 退在容忍內）仍成立。
- 做法：`reports/card-0.2.7d+E153-t6-target/preregistration.md`（sha c98b87d9…b285）。K0＝0.2.7d、K0h＝歷史三原點 E-142 hist＋E-147 連續 d、K6＝目標全換 T6。判定照 E-142 errata-1～3，三季合併、無選擇。
- 已揭露：E-142 全部結果與稽核、0.2.7c 底 T6 關鍵球員名次。三季已用於選 T6，不是新樣本外；真樣本外等 2026-27。
- 狀態：已凍結（2026-11-01，使用者「GO」），派 role-card 執行
- 狀態更新：errata-1（2026-11-01，第 0 階段後 lead 決定；sha 2e6c162f…3329）：2025-26 目標 100% T6（B12 不用）、所有 --rapm 輸入換 T6、usage rapm1 不換。c0／c0h 逐位元過
- 狀態：完成（2026-11-01，537c578），判定 adopt 候選：三季 C +0.022（下界 +0.003）、薪水 +0.029、2K +0.043、下季 RAPM −0.029（容忍 0.05）。2025-26 Flagg 213→180、Banchero 159→63、Edwards 38→10、Knueppel 16→32、Herb Jones 19→145、Brooks 50→153；頂端 OVR 尺度變大（SGA 104.6→118.5）。等使用者裁定與 G5
- 相關：E-142、E-147、R-093、R-098、R-100
- 來源：使用者 2026-11-01「一定要把另一半的 B12 目標表也換成 T6；而且要在現行的 0.2.7d 上重做」→「GO」

### E-154
- 日期：2026-11-01
- 假設：壓迫（PRES）的抄截、deflection、造進攻犯規每 36 分鐘值被「上場時間短」「對位對象是替補」放大；用同一人跨季差分估出的校正（log 每場分鐘、對位對象平均每場分鐘），在樣本外讓分鐘變動大的人 force 排名更穩，卡片層不變差。
- 做法：`reports/card-0.2.7d+E154-pres-context/preregistration.md`（sha aa98efed…02e2）。基準 card 0.2.7d（696a8ac7…0649）。係數只用 2022-23→2023-24、2023-24→2024-25 估（90% 區間不含 0 才保留）；樣本外 2024-25→2025-26 分鐘變動 ≥ 25% 的人看穩定度（o1）；卡片層 c0／c1／m1–m3／c3／c4 照 E-123。
- 已揭露：Dru Smith 2025-26 deflection／36、抄截／36 都排第 1、每場 16.3 分鐘（第 272）、對位對象每場分鐘第 240；跨人 Spearman deflection 對每場分鐘 −0.17；跨人 OLS 係數（每場分鐘 −0.058、對手得分 +0.221）。沒看過同一人跨季變化與任何候選卡。
- 狀態：完成（2026-11-01），校正沒有樣本外證據，不採用
- 結果：三個成分只有造進攻犯規（chg）有分鐘相依（係數 −0.50，90% 區間 −0.89～−0.13）；抄截、deflection、對位對象分鐘的區間都含 0，歸 0。樣本外 o1 沒過（分鐘變動 ≥ 25% 的 77 人，誤差差值 90% 區間 −0.008～+0.005，上界 > 0），其餘關卡全過（c0 重現 0.2.7d 排名 sha 696a8ac7…，m1–m3、c3、c4、npm test 52 過）。Dru Smith presDisplay 124.9→122.8、排名 2→2，OVR 65.1 不變。預註冊不准改門檻或只留 defl 重跑。資料夾 `reports/card-0.2.7d+E154-pres-context/`（results.json、report.md）。
- 相關：E-071、E-123、E-147、E-153、R-050、L-026
- 來源：使用者 2026-11-01「dru smith 的 deflection 應該沒有那麼好。而且他上場時間很少，可能都是面對第三陣容」→「寫預註冊」

### E-155
- 日期：2026-11-01
- 假設：合併 RAPM 對年輕人的修正做成連續 max(0,25−年齡) 比斷崖 ≤23 準（A1y 的形狀），跨季留一季外回測成立。
- 做法：`reports/card-0.2.7d+E155-young-shape-backtest/preregistration.md`（commit 00d8e21 先凍結）、`e155.py`。代理測試：不重做卡片，預測量＝T 季往回四季合併 RAPM，答案＝T+1 單季 RAPM；4 個複製（2018-19→19-20、19-20→20-21、22-23→23-24、23-24→24-25），修正係數用其他三季 WLS 擬合。
- 已揭露：E-081、E-152；沒看過各季年齡殘差。
- 狀態：完成（2026-11-01），不成立。年輕子群（≤24）連續減斷崖四季平均 −0.005，只有 1/4 季為正（2023-24→24-25 +0.022；其餘 −0.000、−0.016、−0.024）；全體平均 −0.003。兩種修正都幾乎沒比不修正好（年輕子群 ρ 約 0.33–0.43，修正前後差 ≤0.02）。維持 0.2.7d；E-151 照原規則等 2026-27。
- 相關：E-151、E-152、E-081、F-099、L-026
- 來源：使用者 2026-11-01「你先用別的賽季回測啊」


### E-156
- 日期：2026-11-01
- 假設：E-144 頂端長人的進攻籃板加分，是因為模擬裡每多一個進攻籃板換到的分數比實測高。
- 做法：`reports/sim-0.1.1+E156-oreb-value/preregistration.md`。同 E-144 配對種子，base 對 oreb 版逐場記進攻籃板、二次進攻得分、運氣修正分差，5090。
- 狀態：已凍結（2026-11-01，使用者「量進攻籃板值幾分」）；完成 4/5（2026-11-01，F-101）
- 相關：E-144、F-093、F-075、F-081、loop H18
- 來源：使用者 2026-11-01「量進攻籃板值幾分」

### E-157
- 日期：2026-11-01
- 假設：（定義評估口徑，不選卡）評估加「下季自製 EPM × W(mpg)」0.15，成為評估口徑 v2（薪水 0.4、2K 0.3、下季 RAPM 0.15、下季 EPM 0.15、模擬 0.15 待穩定）；新增 ④ 下季 EPM 不差超過 0.05。
- 做法：`reports/card-0.2.8+E157-next-epm-metric/preregistration.md`（sha 4a3071fd…a883，commit 01d2c45 先凍結）、`eval_v2.py`（之後卡片實驗沿用）。
- 狀態：完成（2026-11-01，1481e4d）。c0 過（關掉 EPM 項與 E-153 C 完全一致）。v2 口徑下 0.2.8 對 0.2.7d：C +0.010（90% 區間 −0.008～+0.028，① 不過）、薪水 +0.029、2K +0.043、下季 RAPM −0.029、下季 EPM −0.041（②～④ 都過）。只報告，不改 R-102。診斷：Spearman(下季 EPM, t 季 T6) 約 0.68，遠高於下季 RAPM 對 T6 的約 0.38，EPM 項偏向 T6 類目標。
- 相關：E-142、E-153、R-102、L-026
- 來源：使用者 2026-11-01「為什麼沒有 EPM」→「先上線 028 然後 A B」

### E-158
- 日期：2026-11-01
- 假設：目標換 T6 後，usage 層的年輕×爛隊×時間折扣（y·d·L）改用 T6 擬合（Y1）或拿掉（Y0），年輕子群（≤23）排序變好、全體不退步。
- 做法：`reports/card-0.2.8+E158-young-under-T6/preregistration.md`（sha 922e3aa8…b2ce1，commit 01d2c45 先凍結）、`e158_build.py`、`e158_eval.py`。K＝0.2.8（c0 四原點逐位元過），評估口徑 v2，三季合併。
- 狀態：完成（2026-11-01，1fcd004），兩候選都過，依規則取 Y0；2026-11-01 使用者採用 Y0 → card 0.2.9（R-104）。
  - 年輕 C 差：Y1 +0.090（下界 +0.024）、Y0 +0.106（下界 +0.035）。全體 C：Y1 +0.029、Y0 +0.001。y·d·L 係數 K −0.585、Y1 −0.194。
  - 2025-26（K→Y1→Y0）：Flagg 180→93→75、Knueppel 32→86→82、Banchero 63→139→141、Castle 67→146→140、Harper 83→168→147、Podziemski 24→64→59；爛隊新秀大升（Kyshawn George 337→189→145、Sarr 351→250→198）。
  - 前 20：Y0 只換 1 人（A. Thompson 出、Durant 進）；Y1 換 4 人（LeBron、AD、Embiid、Durant 進）。前 300 移動 ≥10 名：Y1 148、Y0 160。
  - 子代理解讀待確認：Y1 的 rapm1 用整季 T6 同時套 A／B 半、T6 沒有的人丟掉（每半約 40 人）；E-157 seed 沿用 20261101。
- 相關：E-147、E-149、E-152、E-153、E-157、L-026
- 來源：使用者 2026-11-01「先上線 028 然後 A B」

### E-159
- 原編號 E-157（2026-11-01 寫預註冊時撞號，另一個 session 已用，改號；5090 上目錄仍叫 `sim-0.1.1+E157-posreb-shared`）
- 日期：2026-11-01
- 假設：模擬裡中鋒比 RAPM 高，有一部分是「這個位置大家都有的籃板價值」（RAPM 看不到，R-103 下不算偏差）；扣掉後長人偏袒 S 是否仍 > 0。
- 做法：`reports/sim-0.1.1+E159-posreb-shared/preregistration.md`（sha c2f041f7…3496）。每個位置的平均球員，籃板欄位用位置平均 vs 全聯盟平均，在 12／24／36 分鐘量 WinImp 差（5 位置 × 3 分鐘 × 2 版），依每人分鐘內插後從 E-135 base 逐格扣掉，再算 E-067 S（X 計分、OOS）。5090。
- 狀態：已凍結（2026-11-01，使用者「寫預註冊再量」）；完成 3/5（2026-11-01，F-102）
- 相關：R-103、R-041、E-135、E-144、E-156、F-093、F-101、L-086、loop H20
- 來源：使用者 2026-11-01「比平均球員」→「寫預註冊再量」

### E-161
- 日期：2026-11-01
- 假設：新賽季 OVR 凍結 stamina 能力值、只保留 MPG_hat 更新（R-105）之後，追蹤整季答案的能力不變差，開季前幾場的上場時間不再被算兩次。
- 做法：待寫預註冊（`reports/ovr-inseason-2026-27/e161-stamina-freeze/`）。`run_c4_live.py` 加開關，stamina 進 frozen 但 MPG_hat 的 w 照算；回測沿用 E-095 的 backtest 結構，早期場次（3／5／10 場）與整季各看一次。
- 狀態：預註冊凍結（2026-11-01 使用者「核可開跑」，`reports/ovr-inseason-2026-27/e161-stamina-freeze/preregistration.md`，sha256 5b8a67e9…f664）；結果 (1) 過、(2) 不過（8 格 5 格 MAE 變差超過 +0.05，最大 +0.116），不自動採用（2026-11-01，`e161-stamina-freeze/report.md`）；但評估目標答案卡本身含 stamina 重複計算，判定有循環偏誤（L-088），改走卡片層實驗待定；2026-11-01 STAMINA_FREEZE 開關已隨 inseason 0.2.9a 移除（stamina 不進第一層，凍結沒有對象；R-107）
- 相關：R-105、R-057、E-064、E-095
- 來源：使用者 2026-11-01「分鐘和體力只用其中一個……我傾向用分鐘」

### E-162
- 日期：2026-11-01
- 假設：卡片迴歸目標 T6 的進攻分量混入部分 PER（w＝0.15／0.30），高產量中效率子群（USG% ≥ P75、TS% 在 P25–P75）的排序變好、全體不退步。
- 做法：`reports/card-0.2.9+E162-per-volume/preregistration.md`（sha 5b3d6323…1025，commit 8147f57 先凍結）、`e162_build.py`、`e162_eval.py`。K＝0.2.9（c0 四原點逐位元過），評估口徑 v2，三季合併。
- 狀態：完成（2026-11-01），兩臂都不過，維持 0.2.9。子群 C 差 P15 −0.003、P30 −0.003（門檻 +0.01）；全體 C +0.001；護欄全過。2025-26 Flagg 75→77、Banchero 141→147、Jalen Green 168→158（K→P30）；前 300 移動 ≥10 名只有 P30 87 人。目標改 30% 排名幾乎不動。
- 相關：E-142、E-153、E-157、E-158、L-026
- 來源：使用者 2026-11-01「評分納入部分PER是不是就不用複雜公式」→「開實驗」


### E-164
- 日期：2026-11-01
- 假設：卡片 OVR 第一層（部件卡設計矩陣）拿掉 stamina、上場時間只留在用人層分鐘 L 與分鐘權重 W 之後，外部評估（評估口徑 v2：薪水、2K、下季 RAPM、下季 EPM）不明顯變差。
- 做法：`reports/card-0.2.9+E164-no-stamina/preregistration.md`。K＝card 0.2.9 重建（c0 四原點逐位元），S＝三張部件卡 `--dropAttr stamina`、用人層 Y0 重擬合；判定 全體 C ≥ −0.005、薪水／2K ≥ −0.02、下季 RAPM／EPM ≥ −0.05。
- 狀態：預註冊凍結（2026-11-01 使用者「核可開跑」，sha256 803139b0…a3d7）；完成（2026-11-01，role-card Sonnet 子代理，lead 核對 c0 四原點 sha、u1、唯讀 sha、JW／Chet 名次）：判定不過，只差薪水 −0.0216（門檻 −0.02）；C −0.0040、2K −0.0004、下季 RAPM +0.0099、下季 EPM +0.0102 都過。K 的 stamina 係數約 +0.27／10 分；拿掉後 heightInches −0.39→+0.05。2025-26：JW 17→10、Chet 16→11、Edwards 9→14、Barnes 12→19、Jokić 6→7；前 20 無進出，前 300 移動 ≥10 名 128 人。待使用者裁定（`reports/card-0.2.9+E164-no-stamina/report.md`）；已採用 2026-11-01（R-107），發 card／inseason 0.2.9a（字母版，R-108：前 20 名無進出、前 100 名移動 ≥10 名 23 人）；見 `reports/card-0.2.9a/report.md`
- 相關：R-105、E-161、L-088、E-131、E-158、R-057
- 來源：使用者 2026-11-01「就算體力很重要，但是重複計算了，不如整並到分鐘裡」→「GO」

### E-165
- 日期：2026-11-01
- 假設：單場評分用「M4 混 Game Score」（w＝0.15／0.30）能取代 M6 的扛出手量加分，E-150 判定項與 M6 相當。
- 做法：`reports/rating-m7-gmsc/preregistration.md`（sha 37b85536…f476，commit 3a34ae1；原 E-164 撞號改號）。2025-26 A 半定常數、B 半驗收，沿用 fit_rating_m6 eval 口徑。
- 狀態：完成（2026-11-01，params 8111de7 先凍），兩臂都不過 D1，維持 M6。G30 低效率大量場 6.18＝M6，但高量有效率場 C1 0.85 對 M6 0.91（Barnes 41 分 6.0 對 8.8）；G15 穩定度 0.615 對 0.659。簡單版把加分撒給所有大量出手，M6 集中給有效率的。報告 `reports/rating-m7-gmsc/report.md`
- 相關：E-150、R-101、E-162、F-106、L-026
- 來源：使用者 2026-11-01「評分納入部分PER是不是就不用複雜公式」→「開比較實驗」


### E-166
- 日期：2026-11-01
- 假設：把防守者投籃犯規 β 乘上 k，讓模擬非中鋒罰球防守散布追上實測（0.1.2 只有 44%），3D 防守側翼的低估會減少（非中鋒防守 RAPM ≥ 1.5 的 36 人平均少低估 ≥ 10 名），整體名次和球隊層不變差。lead 預期 j1 過約三成。
- 做法：`reports/sim-0.1.2+E166-ft-defense/preregistration.md`（草稿）。k 只用實測 stints 散布校正（候選 1、2、3、4、6），再照 E-140 重解 c、pace；判定 seed 20261028–059。
- 已揭露：F-103～F-105、E-118／E-120／E-140 全部結果。
- 狀態：已凍結（2026-11-01，使用者「凍結執行」；sha256 見 `preregistration.sha256`；修正 A1 在任何結果前：β 表乘 k 不改 src、答案名次照 od_split 原算法、j1 名單 `frozen-groups.json` 36 人）；2026-11-01 完成：不採用（j3 不過）。k=2、c=−0.05625、pace=0.998125；j1 36 人平均低估 90.6→79.0（過）、j2 Spearman 0.388→0.432（過）、j3 MAE +0.154（門檻 0.1，不過）；只報告 S 主版 +79／+93→+108／+120 變差。報告 `report.md`，F-111）
- 狀態更新：2026-11-01 使用者裁定犯規 k=2 要納入、球隊 MAE 變差改由重新擬合其他參數處理（R-115）；重擬合實驗待預註冊
- 狀態更新：2026-11-01 採用為 sim 0.1.3 預設（R-120）。E-184 造罰球重擬合選到 a=1（沒有可改的，F-127）；照 R-117 球隊 MAE 不否決。`benchmark.mjs` 預設路徑 2 seed 870 場和 E-166 rr-k 逐場相同
- 相關：F-105、E-140、R-094、L-026、H21
- 來源：使用者 2026-11-01「先補罰球防守」

### E-167
- 日期：2026-11-01
- 假設：M6 扛出手量加分改平滑（S1 斜坡 δ 0.10→0.20；S3 加分隨多扛量線性、不再二次；S13 兩者），「多進一球評分差多少」的尖端下降，E-150 判定項不輸 M6。
- 做法：`reports/rating-m8-smooth/preregistration.md`（sha 5063c477…0181e，commit e110b52）。M6 常數沿用，各臂只重定 a、c（params 6b4b541 先凍）；2025-26 B 半驗收；P1＝TSA ≥ 20 的單場把一顆沒進的兩分改進，評分變化 p90 ≤ 0.8×M6。
- 狀態：完成（2026-11-01），規則選 S13。P1 p90：M6 1.05、S1 0.75、S3 0.90（不過）、S13 0.67。S13 護欄全過（C1 0.869 對 0.906、穩定 0.638 對 0.659）。副作用：Barnes 41 分 19/34 從 8.8 掉到 6.8；S1 保住 Barnes 但 Brunson 12/28（TS 46%）從 5.1 升到 6.5。**等使用者**裁定換不換。報告 `reports/rating-m8-smooth/report.md`
- 相關：E-150、E-165、R-101、L-026
- 來源：使用者 2026-11-01「M6目前看起來更好。不過補正能不能更平滑」→「GO」

### E-168
- 日期：2026-11-01
- 假設：M6 加分斜坡改曲線（δ 0.20，f^p，C15 p=1.5、C2 p=2，對照 S1 p=1），起點同 S1、終點同 M6，「多進一球」尖端下降且低效率大量場不像 S1 多給。
- 做法：`reports/rating-m9-curve/preregistration.md`（sha f2d2ff20…2f1，commit 218fa0b）。M6 常數沿用、各臂重定 a、c（params 153cbf5 先凍）；2025-26 B 半；P1 同 E-167，另加低效率護欄（TSA≥25、TS<TS_lg−.08 平均 ≤ M6＋0.4，看過 E-167 S1 後訂，已揭露）。
- 狀態：完成（2026-11-01），沒有臂通過，規則維持 M6。P1 p90：M6 1.05、C15 0.84（門檻 0.837）、C2 0.90、S1 0.75；低效率平均：M6 6.18、C15 6.65、C2 6.42、S1 6.96（門檻 6.58）。其餘護欄全過，Barnes 不變。原因：曲線頂端坡度回到 M6，P1 跳動就在那段。**等使用者**裁定。報告 `reports/rating-m9-curve/report.md`
- 相關：E-167、R-101、L-026
- 來源：使用者 2026-11-01「改成曲線呢？」→「GO」

### E-169
- 日期：2026-11-01
- 假設：M6 加分斜坡改 S 形（smoothstep；Z1 T0−0.18→T0＋0.08、Z2 T0−0.15→T0＋0.05，對照 C2），兩端都緩，「多進一球」尖端下降且低效率大量場不多給。
- 做法：`reports/rating-m10-scurve/preregistration.md`（sha 4d282b4e…9440，commit 4011fce）。M6 常數沿用、各臂重定 a、c（params 349b914 先凍）；2025-26 B 半；規則同 E-168（P1 p90 ≤ 0.8×M6、低效率護欄 ≤ M6＋0.4、其他護欄）。
- 狀態：完成（2026-11-01），規則選 Z1（唯一全過）。P1 p90：M6 1.05、Z1 0.81、Z2 0.89、C2 0.90；低效率平均：M6 6.18、Z1 6.30。代價：TS 50–54% 大量場比 M6 少 0.7–1.2（假場 18/36 10.8→9.6），C1 不變、穩定 0.659→0.655。使用者 2026-11-01 採用（R-108），名單頁已換。報告 `reports/rating-m10-scurve/report.md`
- 相關：E-167、E-168、R-101、L-026
- 來源：使用者 2026-11-01「不然用S型曲線」→「GO」

### E-172
- 日期：2026-11-01
- 假設：Jalen Williams 卡 #17／賽中 #8 高於 RAPM #25，是因為 2025-26 只打 936 分鐘、壓迫／單防小樣本偏高。
- 做法：診斷，未預註冊。pres_drive.p_comps＋p_value 算他 2022-23～2026-27 逐季單季 pressure（常數凍結在 2025-26 卡片池）；賽中 OVR−正式卡 對能力值窗口差做 OLS（163 人）；formalOVR≥80 的賽中變動分布。腳本與報告 `reports/E172-jalen-williams-defense/`。
- 結果：假設被推翻。四個完整季 pressure 都 84–96（2024-25 96.4），2025-26 的 93.2 是他的常態（F-108）。賽中 +2.3 不是能力值窗口造成的（OLS R² 0.11，他的解釋量 −0.1），是 formalOVR≥80 裡最大的開季跳動（95 分鐘）；Butler 0 分鐘也 +1.3。
- 已揭露：lead 看過 JW 的逐季分解、賽中跳動分布；之後的預註冊不得用 JW 名次當門檻（L-026）。
- 狀態：診斷完成，下一步待使用者選（A 壓迫對 RAPM 防守的跨球員樣本外檢查；B 賽中第一場跳動來源）。
- 相關：F-108、E-173、E-071、E-123、R-110、R-107、L-026
- 勘誤：勘誤 2026-11-01：rapm-T6.csv 是 T6＝同季 DARKO＋BPM 合成，不是 RAPM；本條所稱 RAPM 名次／防守值實為 T6，見 E-173 §0
- 勘誤 2：2026-11-01：「賽中 +2.3 屬性窗口解釋不了」錯，當時只查了壓迫／切入窗口。實際是 2026-10-30 老將防守改四季窗口，help 69.8→77.9（0 場就有），一個屬性就占了 pred0 的 +0.295 中的 +0.292；3 場比賽反而讓它小降到 77.6。見 F-110
- 來源：使用者 2026-11-01「jalen williams 的分數太高」→「開實驗查防守」

### E-173
- 日期：2026-11-01
- 假設：卡片（目標 T6）系統性把壓迫高的人排得比他們下季 RAPM 高（總分與防守段都是）。
- 做法：`reports/E173-pressure-vs-rapm/preregistration.md`。E-153 K6 三個歷史原點（2022-23～2024-25）卡片，答案＝E-126 下季 RAPM（net×W(mpg)、D）；S＝Spearman(pressure, 殘差)，三季人數加權，球員重抽 2000 次 seed 20261101，90% 區間。兩個上界都 < 0 才判高估；判高估也不直接改卡。
- 已揭露：E-172 JW 逐季分解、E-153 整體結果；沒看過任何殘差與 pressure 的關係。三季已用於選 T6，不是全新樣本外。
- 狀態：已凍結（2026-11-01，使用者「核可凍結」；sha256 1f146432…fafc5，HEAD 36c177a）
- 狀態：完成（2026-11-01，App lead 自跑）：判定 no_systematic_bias。S_net_pressure +0.055 [−0.001, +0.109]、S_D +0.021 [−0.035, +0.076]，方向是壓迫高的人下季 RAPM 略好於卡。只報告：drive S_net −0.206 [−0.256, −0.154]，三季都負（F-109）。限制：歷史原點能力值是 2025-26 現值（L-091），本結果只算弱證據。報告 `reports/E173-pressure-vs-rapm/report.md`
- 相關：E-172、F-108、F-109、L-091、E-153、E-142、E-126、R-007、L-026
- 來源：使用者 2026-11-01「A 壓迫對 RAPM」
### E-174
- 日期：2026-11-01
- 假設：正式卡和新賽季卡統合成一條管線 card(t)：所有可更新屬性用同一個四季遞減窗口（R-076 權重，含本季），OVR 用一組凍結係數套上去；2025-26 卡＝card(季末)。季末樣本外（2023-24、2024-25，口徑 v2）不比現行差，賽中重播的開季跳動比 C4 小。
- 做法：設計 `reports/E174-unified-window-card/design.md`；預註冊草稿 `preregistration.md`（U 四季窗口 對 S 當季窗口，同擬合；測試季 2023-24、2024-25，口徑 v2）。使用者裁定 Q1 重擬合、Q2 2025-26 頁換新管線季末、Q3 開季不另外處理。
- 狀態：已凍結（2026-11-01，使用者「核可凍結」；sha256 0a9dc462…9210，HEAD b272863）；第 0 階段完成（`stage0-data.md`）；errata-1 凍結（2026-11-01 使用者「核可開跑」，sha f8652cba…f427：最早季 2022-23、缺追蹤資料的季權重 0、屬性一律照 0.2.9a 算法逐季重算）；第 1 階段開工前停下（`blocked.md`：窗口下百分位型屬性的算法沒定義），errata-2 凍結（2026-11-01 使用者「核可開跑」，sha 6e707967…2b03：量加權、快照季單季池、S 臂重現 |差|≤0.1 ≥99%）；第 1 階段再次停下（`stage1/blocked.md`）：0.2.9a 屬性本來就往前 3 季歷史拉回（F-115），S 臂設計前提錯（L-093）。被 E-175 取代（2026-11-01；沒有產生任何卡片或評估數字）
- 相關：R-076、R-110、R-107、R-050、R-064、L-091、L-026、E-142、E-157、E-164、E-139
- 來源：使用者 2026-11-01「之前已經說要用4季平滑曲線了。應該就不用區分正式 beta了」→「統合」

### E-175
- 日期：2026-11-01
- 假設：所有 V61 比率型屬性改成 R-076 滑動窗口（U）後，預測同季未來場次的屬性誤差不比現行按季分塊（V，V61 方法 c，＝0.2.9a）差；換季那天不再跳動。
- 做法：`reports/E175-sliding-window-card/preregistration.md`（草稿）。V61 backtest 框架，測試季 2025-26（主）、2024-25（次），切點 0／10／25／46.7／75%，R̄＝MAE(U)/MAE(V) 8 項平均；每切點 ≤1.02 且單項 ≤1.05 → adopt，合併上界 <1 → card 0.3.0。OVR 層只報告。
- 狀態：已凍結（2026-11-01，使用者「核可開跑」；sha256 15ba2d7d…36ad，HEAD 5255f37）；完成（2026-11-01）：重現 100%，判定 PATCH（card 0.2.10；合併 R̄ 1.004，上界 1.011 未過 MINOR），F-116。role-audit（額度停止，僅中間檔）：照預註冊「顯示出來的量」評 foulDraw／pass 組合值時 adopt 不成立（25% 切點 1.0215），使用者仍裁定上線（R-114，2026-11-01）；card／inseason 0.2.10 已上線（2026-11-01）
- 相關：E-174（被取代）、R-111、R-076、R-110、F-115、L-093、L-084、L-026
- 來源：使用者 2026-11-01「沿用正式卡是什麼意思？不是就是sliding window嗎？」→「GO」
### E-176
- 日期：2026-11-01
- 假設：Jalen Williams 進攻分（OFF +2.28，聯盟第 15～18）偏高，來自前鋒位置的傳球／自主進攻係數。
- 做法：樣本內診斷（R-007，只看方向）。`reports/E176-jw-offense/`：jw_off.py 逐屬性拆解＋外部進攻指標逐季名次＋2025-26 逐場；off_vs_ext.py 2025-26 全聯盟 OFF 名次對同季外部進攻（DARKO O、EPM O、OBPM 平均名次）殘差。
- 狀態：完成（2026-11-01，App lead 自跑）：見 F-113。未改卡。
- 相關：F-110、F-109、E-173、E-172
- 來源：使用者 2026-11-01「我們繼續查JW 進攻被高估」
### E-177
- 日期：2026-11-01
- 假設：卡片位置從「先發登錄硬標籤」改成 BBRef 上場位置比例（pct_1…pct_5），用在位置交互項、位置置中、防守加成置中三處；量尺不劣於 card 0.2.9a。
- 做法：`reports/card-0.2.9a+E177-bbref-position-shares/preregistration.md`。判定：① 綜合參考分 C 下界 > −0.01、② 下季 RAPM 下界 > −0.02、③ 隊內 MIN–OVR 中位數不低超過 0.02。c0 one-hot 逐位元重現 0.2.9a。
- 已揭露：F-033、E-082、E-176；BBRef 只看過 JW（SG 18、SF 51、PF 31%）。
- 狀態：已凍結（2026-11-01，使用者「核可凍結」；sha256 243341d1…）；2026-11-01 完成：不採用（②未過）
- 結果（2026-11-01）：前置條件全過（s0 99.7%、c0／c0h 逐位元、npm test）。①C +0.001（下界 −0.0085 過）、②下季 RAPM −0.013（下界 −0.0250 ＜ −0.02 不過）、③隊內中位數 0.645→0.653 過。2K +0.009、薪水持平；JW 88.2→88.0（進攻項 2.30→2.19，偏高不來自位置標籤）；前 20 進出 Brown、F.Wagner／出 Barnes、MPJ。報告 `reports/card-0.2.9a+E177-bbref-position-shares/report.md`，細節 `details.md`。
- 相關：F-033、E-082、E-176、F-113、E-153、E-164、L-026
- 來源：使用者 2026-11-01「重做位置份額」

### E-178
- 日期：2026-11-01
- 假設：防守方場上 ≥2 中鋒時，投籃犯規 logit 加 γ（實測雙中鋒對手多罰 +2.59／100，模擬 +0.34）。用實測 stints 校正 γ 後，模擬的雙中鋒額外淨分差（0.1.2 +2.60）會往實測 +0.83 靠近 ≥40%，WinImp 名次和球隊層不變差。lead 預期 j1 過約五成。
- 做法：`reports/sim-0.1.2+E178-twin-big-foul/preregistration.md`（草稿）。γ 候選 0.1～0.6，校正 seed 20261140–155，判定帳本 seed 20261160–175。
- 已揭露：F-103～F-105、F-111、F-112、F-114，E-118／E-120／E-140／E-166 全部結果。
- 狀態：凍結（2026-11-01 使用者「好」）；j0 過後在中鋒定義檢查停下（槽位標籤每邊恆 1 C，L-094），修正 A1 已凍結（2026-11-01 使用者「接著」）；完成「不採用」（2026-11-01，j1 不過，F-121、L-097）
- 相關：F-114、E-140、E-166、L-026、H21
- 來源：使用者 2026-11-01「籃下加互斥」→「雙長人犯規成本」
### E-179
- 日期：2026-11-01
- 假設：卡片（0.2.9a 底歷史原點）對下季 RAPM 系統性高估傳球、自主進攻高的前鋒（SF／PF），且比後衛嚴重。
- 做法：`reports/E179-forward-pass-vs-rapm/preregistration.md`。S_F(a, e_net) 上界 < 0 且 S_F−S_G 上界 < 0 才判前鋒高估；e_O 只報告；判高估也不直接改卡。
- 已揭露：E-176、E-177 同季殘差；E-173 drive；沒看過 pass／creation 對下季 RAPM 殘差。
- 狀態：已凍結（2026-11-01，使用者「好」；sha256 b0364660…）
- 狀態：完成（2026-11-01，App lead 自跑）：creation 判前鋒高估（S_F −0.35，F−G 差 −0.14 [−0.25, −0.03]）；pass 判不分位置都偏高（S_F −0.32、S_G −0.29，差 −0.03 [−0.15, +0.08]）。只報告：foulDraw 前鋒特有（差 −0.17）。限制：殘差設計使卡片重押的屬性普遍偏負，較可信的是組間差；L-091。報告 `reports/E179-forward-pass-vs-rapm/report.md`；F-117
- 相關：E-176、E-177、F-113、F-114、E-173、L-026
- 來源：使用者 2026-11-01「好」（驗證前鋒傳球係數）

### E-180
- 日期：2026-11-01
- 假設：把 pass 改成全位置共用斜率（臂 A），可縮小 E-179 的傳球偏高，且整體不變差。（2026-11-01 使用者選「A」，原臂 B 刪除。）
- 做法：`reports/E180-pass-pool-creation-interact/preregistration.md`。2025-26 卡做不劣於檢查（薪水、2K、隊內 MIN–OVR）；判定用 2024-25 原點卡對 2025-26 RAPM 的全人群 S(pass, 殘差)（有揭露的樣本內）。
- 狀態：已凍結（2026-11-01，使用者「核可」；sha256 50b34a14…）。使用者裁定改用上一季判定（R-113）：2024-25 原點卡對 2025-26 RAPM，一次跑完，不等 2026-27
- 狀態：完成，不採用（2026-11-01，派工 main 跑、lead 抽驗 c0／c0h sha 與 verdict）：p0 成立（K0h S_all(pass) −0.305）；① A−K0 +0.0009 [−0.0072, +0.0089] 不過；② +0.0006 過；s1 薪水下界 −0.0128 不過、2K 過；s2 −0.009 過。前鋒傳球偏高少、後衛多，互相抵消。JW 88.2/10 → 86.7/15（只報告）。F-118。報告 `reports/E180-pass-pool-creation-interact/report.md`
- 相關：E-179、F-117、L-095、L-091、L-026、E-177
- 來源：使用者 2026-11-01「寫修正預註冊」

### E-181
- 日期：2026-11-01
- 假設：新增「無球」能力值（每 36 分鐘被助攻進球得分；臂 O2 另加 catch-and-shoot eFG）進卡片 OVR 迴歸，可縮小無球型球員（offBall 高、creation 低）被低估，且整體不變差。
- 做法：`reports/E181-offball-attr/preregistration.md`。兩階段同 E-180：第 1 階段建卡做不劣於檢查（薪水、2K、隊內 MIN–OVR、offBall 係數 > 0）；第 2 階段原寫等 2026-27 RAPM；errata A1 改用上一季（R-113）。
- 已揭露：Simons 2026-27 逐日重算（只列例子）、E-179／F-117、E-180 草稿；沒看過任何無球原始值或改動後卡片。
- 狀態：已凍結（2026-11-01，使用者「核可」；sha256 1e3c8e86…，commit bb78df3 被同時進行的 E-180 凍結 commit 一起帶入）。errata A1（依 R-113 改用 2024-25 原點對 2025-26 RAPM、一次跑完）已核可（2026-11-01，sha256 fe0475c1…）；派 role-card 執行中；結果（2026-11-01，role-card 執行，待 lead 抽驗）：c0／c0h／npm test 皆過；第 1 階段 O1、O2 都過；第 2 階段 p0 字面不成立（K0h Q 組 e_net +0.090），判「低估沒出現，不加屬性」，不採用；e_net 符號疑點（反號後低估存在，但 O1 加屬性只動 0.001 個百分點、方向相反，仍非候選）見 reports/E181-offball-attr/details.md
- 狀態：完成（2026-11-01，lead 抽驗 c0 sha 與 results.json）：不採用。反號讀法下無球型確實低估約 9 個百分點，但加 offBall 係數 +0.039（SE 0.033）、Q 組只動 0.001 且方向相反；errata 符號錯見 L-096；F-119
- 相關：E-179、E-180、F-117、F-119、L-091、L-096、L-026、R-025
- 來源：使用者 2026-11-01「新增無球屬性？…製造空檔 把握空檔也是一個實力」→ 範圍選「A」

### E-182
- 日期：2026-11-01
- 假設：模擬裡投籃者的防守者固定是同格子的人，好防守側翼守不到對方主要得分手。實測好防守非中鋒每 100 回合面對的出手，比其他非中鋒多 ≥10%，模擬差距 ≤ 實測一半。診斷，只量不改。lead 預期約六成。
- 做法：`reports/sim-0.1.2-matchup-diag/preregistration.md`（草稿）。實測 2025-26 對位資料 1231 場；模擬 0.1.2 rr seed 20261190–191，observer 記格子防守者。
- 已揭露：F-103～F-105、F-111、F-112、F-114、F-121。
- 狀態：完成（2026-11-01），判讀 B：對位不是主因（F-122）
- 相關：F-112、F-103、H21
- 來源：使用者 2026-11-01「側翼」

### E-183
- 日期：2026-11-01
- 假設：pass 的「率」那一半從 AST/astCh（助攻份額）換成 AST/PASSES_MADE（傳球轉助攻，二項式經驗貝氏收縮），可縮小 pass 偏高（E-179、E-180、F-118），且整體不變差。
- 做法：`reports/E183-pass-conversion/preregistration.md`（已凍結）。臂 K0（0.2.9a）／Q；判定 2024-25 原點對 2025-26 RAPM（R-113），統計量照 E-180 §2b。
- 已揭露：E-179、E-180（K0h S_all(pass) 已看過）、F-118；只看過 JW、Jokić、Haliburton、LeBron 的 AST/PASS 原始值。
- 狀態：已凍結（2026-11-01，使用者「核可凍結」；sha 見 preregistration.sha256）。
- 狀態：完成，不採用（2026-11-01）。Q 的 S_all(pass, e_net) 只改善 +0.023 [−0.006, +0.048]，下界不 > 0，① 不過（② 整體不變差、2a 全過），Q 不是候選；報告 `reports/E183-pass-conversion/report.md`。

### E-184
- 日期：2026-11-01
- 假設：進攻方造犯規倍率 (FTA/FGA)/區域平均 重複計入出手區域，造罰球個人差距被放大；加指數 a<1 收回後，開著犯規 k=2 的 30 隊淨分差 MAE 回到 0.1.2 的 +0.1 以內，側翼少低估仍 ≥10 名。lead 預期 g1 過約五成。
- 做法：`reports/sim-0.1.2+E184-ftdraw-refit/preregistration.md`（草稿）。a 只用球員自己的輸入 FTA/FGA 校正（模擬對輸入斜率＝1），再照 E-140 重解 c、pace；判定新 seed 20261200–231。
- 已揭露：E-166 全部、F-123 事後拆解（判定 seed 20261028–059 的球隊分項）。
- 狀態：完成（2026-11-01）：沒有可改的。修正 A1（§0 的式子不在 harness 裡，改作用在 observedFoulInputs 的目標，L-101）；校正 a=1 斜率 1.063、a=0.85 0.933，選 a=1＝B2 本身，§2 判定不跑（F-127）。報告 `reports/sim-0.1.2+E184-ftdraw-refit/report.md`
- 相關：R-115、R-117、F-123、F-127、L-101、E-166、E-140、L-026
- 來源：使用者 2026-11-01「造罰球散布」

### E-185
- 日期：2026-11-01
- 假設：不是假設檢定（R-118 直接上線）。把 long、creation、threeValue、MPG 換成四季窗口，card／inseason 0.2.11 PATCH。
- 做法：long、creation 照 `reports/E175-sliding-window-card/stage1-methods.md` §2 已寫好的 U 版；MPG 的窗口長度只在 2024-25 選、2025-26 報告；係數／錨全凍結 0.2.9a。報告 `reports/card-0.2.11/report.md`。
- 狀態：完成（2026-11-01）：改名 card／inseason 0.2.12（0.2.11 被另一 session 先用於 0.2.10a），底是 card 0.2.10a（R-121）；自我檢查逐位元過（卡端與新賽季端）、npm test 全過、未發佈；R-122 把正式卡改成 0.2.10c（子 session 誤記為 0.2.10b，lead 2026-11-01 更正），OFFICIAL_CARD／導覽／卡片頁的 patch 未 commit（存 reports/card-0.2.12/work/patches），待決定是否改疊 0.2.10c。報告 `reports/card-0.2.12/report.md`
- 狀態：完成（2026-11-01，R-123 後改版號）：疊在 card 0.2.10c（KAU）上，字母版 card／inseason 0.2.10d（0.2.13 改名，不留）；自我檢查逐位元重建 0.2.10c 過、npm test 全過；窗口把 0.2.10c 壓下的 JW 帶回第 9 名（OVR 90.7），Franz Wagner 21→42。報告 `reports/card-0.2.10d/report.md`
- 相關：R-118、R-111、R-114、E-175
- 來源：使用者 2026-11-01「開始 sliding windows」

### E-186
- 日期：2026-11-01
- 假設：卡片迴歸目標從 T6（DARKO＋BPM）改成 T6R＝0.5·T6＋0.5·四季合併 RAPM（z 混合），JW 與「creation 高的前鋒」偏高縮小（F-117），整體不弄壞。
- 做法：`reports/card-0.2.10+E186-t6-rapm-target/preregistration.md`（sha 4528c722…a61c）。臂 K6（現行）／KR；w 固定 0.5 不掃描。硬條件：a1 JW 2025-26 名次 ≥16、a2 三原點 S_F(creation,e_net) 改善下界 >0、b 重現＋npm test＋C 不退超過 2 倍雜訊；其餘只報告。
- 已揭露：F-113／F-117／F-118／F-125、E-153 結果、JW 各量尺名次；沒看過任何 T6R 卡。
- 狀態：已凍結（2026-11-01，lead 依使用者 /goal 重開額度凍結，R-117 第 5 條）；派 role-card 執行
- 狀態：完成（2026-11-01，71052a6），沒修到：JW 10.5→12（門檻 ≥16）；a2 不過（S_F +0.017，下界 −0.008）；b 過。只報告：下季 RAPM ρ +0.034、C −0.022、只重擬合 JW 第 8。`report.md`
- 相關：F-125、F-117、F-118、E-153、E-142、R-117、R-042
- 來源：使用者 2026-11-01 `/goal 解決jalen williams被高估的問題`

### E-187
- 日期：2026-11-01
- 假設：T6R 目標（E-186）＋傳球全位置共用斜率（E-180 臂 A）一次聯合重擬合，JW 名次降到 16 以後，整體沒弄壞。
- 做法：`reports/card-0.2.10+E187-t6r-pass-pooled/preregistration.md`（sha 見同目錄）。硬條件 a1 JW ≥16、b npm test＋C ≥ −0.089＋下季 RAPM ρ ≥ −2h_R；其餘只報告。
- 已揭露：E-186、E-180 全部結果；組合是因兩者各自讓 JW 下降而選，無新可調數值。
- 狀態：已凍結（2026-11-01，lead，/goal 重開額度第 2 個）；派 role-card 執行
- 狀態：完成（2026-11-01，ae4a062），照 errata-1（R-119）a1 過：JW 10.5→11、前 25 名分段殘差 −1.04→−0.65；b 過（C −0.022、下季 RAPM ρ +0.035；npm test 只有他人 live 0.2.12 改動造成的 live gate 失敗）。副作用：JW OVR 87.3→88.7 反升、SGA 118.8→127.4、前 100 名 51 人移動 ≥10（Jalen Johnson 24→49.5、Banchero 125.5→205）。只共用斜率 KA：JW 11、殘差 −0.81、只 17 人大動。基準是 0.2.10，採用要改疊到 0.2.10a（0.2.10a JW 第 8.5）。待使用者 G5 選臂
- 狀態：改疊 0.2.10a（2026-11-01，修正後 T6 重建 2025-26，無新參數）：JW 名次 0.2.10a 8.5→KAU 10.5／KRU 10／KJU 10，只重擬合 8；分段殘差 −1.50→KAU −1.22／KRU −0.99／KJU −1.15；前 100 名大動 22／47／53。KAU 為採用候選（JW OVR 87.3→87.0、Wembanyama／Edwards 不受波及），待使用者 G5。
- 狀態：採用（2026-11-01，R-122）：KAU 上線為 card 0.2.10c（b 被 E-188 占用）。`reports/card-0.2.10a+E187-rebase/report.md`
- 相關：F-125、E-186、E-180、R-117

### E-188
- 日期：2026-11-01
- 假設：OVR 映射在 PR50 與 PR99 之間加 PR90、PR95 兩個錨點（≥99 與 <70 段不動），[90,99) 人數從 4 變成使用者選定值，名次逐位元不變。
- 做法：`reports/card-0.2.10a+E188-ovr-top-scale/preregistration.md`、`spec.md`。硬條件 a 人數落在選定值 ±2、b 名次逐位元同、≥99／<70 值不變、npm test；ΔOVR、賽中頁、全明星對照只報告。
- 已揭露：lead 已算過四組候選錨點在 0.2.10a 的人數（預註冊 §2），錨點由使用者從中選，不是盲測。
- 狀態：已凍結（2026-11-01，使用者選 S3：PR90→88、PR95→92，N＝19；預註冊 sha 8cf866fe…）；派 role-card 執行
- 狀態：完成（2026-11-01，lead 自己做，dispatch routing self）（0.2.10a 底）：a 過（[90,99) 4→20 人）；b 名次與其他欄逐位元同、<70／≥99 不變；產出 card 0.2.10b（未切 OFFICIAL_CARD）。副作用：70–88 段 ΔOVR 斜率 ×1.66、92–99 段 ×0.49。新賽季頁只出 live-patch.md。待使用者 G5／採用。`reports/card-0.2.10a+E188-ovr-top-scale/report.md`
- 狀態：改疊 0.2.10c（2026-11-01，使用者「採用」後發現 0.2.10c 已上線）：`reports/card-0.2.10a+E188-ovr-top-scale/work/on-0210c/`（原誤寫進 card-0.2.10d，已移出），[90,99) 23 人，a 區間 [17,21] 不過（換底卡造成，未調參）；名次與其他欄同 0.2.10c。未上線，待使用者決定 errata 或換臂。
- 狀態：errata-1（使用者「1」，R-124）：a 改只報告；套用腳本 `apply_to_card.py`（0.2.10c、0.2.10d 上都 23 人）。等 27 賽季 session 發布 0.2.10d 後做 0.2.10e。
- 狀態：上線 card／inseason 0.2.10e（2026-11-01）：`reports/card-0.2.10e/`（0.2.10d 底，ranking sha d7fd938b…，200 列 OVR 變、名次不變）；新賽季頁 `live/build_usage_0210e.py`＋`run_c4_live.e064_map` 四節點，2026-10-31 資料重跑名次逐人相同、90–99 6→24 人、99 以上 4 人不變；npm test 52/0。push／部署待使用者
- 相關：F-131、R-056、R-114、R-117、L-106、L-107

### E-189
- 日期：2026-11-01
- 假設：給每名防守者一個非投籃犯規屬性 γ（實測每 100 防守回合非投籃犯規率的對數、依信度收縮），讓模擬的非投籃犯規依場上防守者發生與歸屬，模擬逐人非投籃犯規率會追上實測（目前防守者身分不影響），中鋒罰球防守缺口（F-129，九成在這塊）縮小。lead 預期主目標過約七成。
- 做法：`reports/sim-0.1.3+E189-nsfoul-attr/preregistration.md`（草稿）。屬性用 2025-26 單數場建、雙數場判（再交換）；機制只有一種、無自由參數，聯盟非投籃犯規量與 c／pace 照 R-115 一次重解。
- 已揭露：F-129（D0、D1、D2 全部）、F-130、F-127、E-166、E-184 全部結果。
- 狀態：已凍結（2026-11-01，使用者「好，凍結」；預註冊 sha 8ba4c9ca…）
- 狀態更新：完成（2026-11-01）：j0 過；j1 字面不過（r 0.72 過、斜率 sim-on-real 0.54 不過，反向 0.95 過，預註冊方向有歧義待 lead 裁）→ 不提 sim 0.1.4；中鋒 D0/D1 沒改善；F-137，F-129 額度 1／3
- 狀態更新：lead 裁定 j1 照字面不過（2026-11-01），不採用，F-129 額度 1/3；中鋒罰球防守離散沒改善，屬性只修到逐人平均（F-137）。
- 狀態更新：使用者 2026-11-01 改判採用為 sim 0.1.4（R-131：機制本身變準即採用候選，中鋒差距屬 B 線、假設排除）；上線實作另派。
- 相關：R-125、R-117、R-115、F-129、F-130、E-166、L-026、L-087
- 來源：使用者 2026-11-01「加入非投籃犯規的屬性」

### E-190
- 日期：2026-11-01
- 假設：自主創造改成「自主跳投」（非助攻的三分＋10 呎外兩分，扣掉 10 呎內），切入與自主創造不再在定義上重疊（r 0.875→≤0.70），F-109 切入型球員被高估縮小，整體沒弄壞。
- 做法：`reports/card-0.2.10c+E190-creation-jumper/preregistration.md`（草稿）。基準 0.2.10c（KAU），只換 creation 定義、全部係數重擬合；一個臂，無新可調數值。
- 已揭露：F-132 現值、F-109、0.2.9a 係數；0.2.10c 的 drive／creation 係數 lead 沒看。
- 狀態：草稿，待使用者凍結（2026-11-01）
- 狀態：已凍結（2026-11-01，使用者「核可」；預註冊 sha 00ae636e…）；派 role-card
- 狀態：停在 c0（2026-11-01）：KAU 逐位元重現 0.2.10c，但舊 creation 無法用逐球重現（MIN≥500 最大差 17.6、r 0.958）——原值是模擬接球占比×FGA、多季合併池、單季值，預註冊三處寫錯（L-105）。a1／a2 未判定，不佔額度；待使用者核可 errata。`reports/card-0.2.10c+E190-creation-jumper/report.md`
- 狀態：errata-1 核可（2026-11-01，使用者「跑」；sha b5818db9…）：出手分切入 D／自主 J／補籃不計（R-126），加對照臂 KP；派 role-card
- 狀態：完成（2026-11-01），**不過**：a1 r(drive_D, creationJ) 0.72（門檻 0.70）、VIF 4.17（3.0）不過；a2 KJ−KP +0.011（0.05）不過；b 過（C +0.001、下季 RAPM ρ −0.001、npm test 52/0）。名次幾乎不動（前 100 名 3 人移動 ≥10）。F-132 額度用 1／3。F-133。`reports/card-0.2.10c+E190-creation-jumper/report.md`
- 相關：F-132、F-109、R-117、R-118、E-187
- 來源：使用者 2026-11-01「預註冊」

### E-191
- 日期：2026-11-01
- 假設：0.2.10d threeValue 窗口版離散度縮小（MIN≥500 標準差 17.6→15.6）是 PctMapper 池錯配（H1：池＝單季值＋窗口值），不是收縮常數 K 太大（H2）。
- 做法：`reports/E191-threevalue-dispersion/prereg.md`（先 commit，ae1d012）。臂 U0／P1（池每季換窗口值）／K½／K2；K 只在 2023-24→2024-25 選、2024-25→2025-26 確認；尺度比用全 582 人。
- 結果：規則判定維持現狀、不產生草案。尺度比（全 582 人）U0 1.05、P1 1.12（不在 [0.95,1.05]）；K2 選擇年最高但確認年輸 K 原值，K 不換（H2 不成立）。事後（不進判準）MIN≥500 人群：U0 0.889、P1 0.952，P1 在此人群會被採用（H1 部分成立，約補回六成缺口）。`reports/E191-threevalue-dispersion/report.md`
- 狀態：已完成（2026-11-01）；預註冊的尺度人群與 0.89 的人群（MIN≥500）不一致，是否用 MIN≥500 重新預註冊→E-191b（2026-11-01，`prereg-b.md`，commit 0743fce）：改判 2023-24／2024-25 兩個沒看過的季，MIN≥500；P1（0.959／0.955）與新臂 P1m（0.967／0.958）都過，採 P1m（兩季平均 0.963，現狀 0.932）；產出草案 `three-value-candidate.csv`；使用者 2026-11-01 核准「疊」（R-127），已上線為 card／inseason 0.2.10f（ranking.csv 與 0.2.10e 逐位元組相同，只有 three-value.csv 的 tv_main 變；賽中端用 TV_P1M 開關）；P1 在該人群的答案已看過，非盲測
- 相關：E-185、F-124、L-026、R-113
- 來源：使用者派工 2026-11-01（lead 假設 H1／H2）

### E-192
- 日期：2026-11-01
- 假設：用人層（Y0 的 L＝log1p(MIN÷可出賽場次)、a＝出賽÷可出賽）改成與其他特徵相同的四季滑動窗口後，2026-27 頁與 2025-26 卡片用同一套演算法，可拿掉「開季樣本少」提示；不預期改變前段名次。
- 做法：card／inseason 0.2.10g（直接上線，R-128）。窗口權重同 Win10；ap＝出賽＋教練決定未上場（疑似輪休規則同 BASE_OPTS），2022-23～2024-25 來自 boxes（avail-hist-0210g.json.gz）、2025-26 來自 dnp json、本季來自 boxes（只列 ACTIVE，C 偏低：L 平均 +0.021、a +0.016）；2021-22 以前沒有 boxes，窗口碰不到。Y0 係數沿用半季特徵擬合值，不重配。自我檢查：關窗口重現 0.2.10f ranking.csv／three-value.csv 逐位元組相同；賽中端關開關與線上 0.2.10f 逐位元組相同、c＝82 與卡片端特徵逐位相同。
- 結果：前 20 名進出 0、前 100 名移動 ≥10 名者 5 人（R-109：維持字母版號）；OVR 變動 ≥1 者 187 人。SGA 109.9→110.4、Jokić 107.0→107.4、Wembanyama 102.0→102.4、Flagg 65→62 名。`reports/card-0.2.10g/report.md`
- 狀態：已完成（2026-11-01），使用者核准上線（R-128）。限制：Y0 係數未窗口化；本季 C 少算；d 未實作；賽中端 30→31 歲年齡旗標翻轉造成 v 項 −0.22/36（約 −4～−6 OVR，Allen、Gordon、Kuzma、Martin）。
- 相關：R-128、E-175、E-185、E-188、E-191、R-118、R-109
- 來源：使用者派工 2026-11-01

### E-193
- 日期：2026-11-01
- 假設：賽中端年齡旗標改用開季當天年齡後，只有「開季後過生日」或「本季還沒上場、之前用到一年前的 2025-26 bio」的人會變，前段名次幾乎不動。
- 做法：inseason 0.2.10h（直接上線，R-129）。`scripts/fetch_birthdates_2026_27.mjs` 抓 592 人 DOB（Python urllib 會被 stats.nba.com 擋逾時，改用 node）→ birthdates.json；`window11.py` `Win11.age_flags` 預設用 age_start，`AGE_START=0` 回舊行為；meta.json 多 `ageStart`（開季日、DOB 人數、退回 bio 人數）。自檢 `live/check_inseason_0210h.py`。
- 結果：AGE_START=0 的 ranking.csv／no-prior.csv／pres-drive.json 與 0.2.10g 逐位元組相同。age_start≠本季 bio AGE 11 人，皆生日在 10-22～10-30（Booker、Brown、Vučević、Landale、Tate…）；y 或 v 改變 11 人（其中 8 人本季未上場、舊版用 2025-26 bio 少算一歲）：Porziņģis v 0→1（OVR 91.0→88.2，23→37 名）、Landale v 1→0（278→257 名）、Tate v 1→0、Pedulla y 1→0（54.5→54.8）。Grayson Allen、Gordon、Kuzma、Caleb Martin age_start＝31（不變）。前 20 名進出 0、前 100 名移動 ≥10 名 1 人，名次有變 47／484 人。`reports/E193-age-start/check.txt`
- 狀態：已完成（2026-11-01）。限制：卡片端仍用 2025-26 bio 年齡；之後新增球員（季中簽約、雙向轉正）要重跑 fetch 補 DOB，否則退回 bio 年齡（meta ageStart.fallback* 會記）。
- 相關：R-129、E-192、R-128、R-109
- 來源：使用者派工 2026-11-01

### E-194
- 日期：2026-11-01
- 問題：F-133 診斷（不佔 F-132 額度）：切入型球員被高估是 T6 目標造成還是卡片擬合造成、哪幾欄多給分、切入對下季 RAPM 值多少。結果用來決定「怎麼給分合理」（R-130），之後拆開＋給分一起上線（使用者 2026-11-01「等診斷一起上」）。
- 做法：`reports/F133-drive-scoring/spec.md`（D1 目標／擬合拆解、D2 各欄貢獻、D3 drive 對下季 RAPM 係數），用 E-190 KJ 卡。
- 狀態：完成（2026-11-01）：擬合端與目標端約各半，擬合端三季穩定、目標端不穩；drive 欄本身 ≈0，pass／ft／creation 給切入型球員最多分（F-136）。待使用者選給分方案。
- 相關：E-190、F-133、F-132、R-130、F-109

### E-195
- 日期：2026-11-01
- 問題：F-136 擬合端診斷（不佔額度）：卡片照 T6 擬合，為什麼還把切入型球員排得比 T6 高（Spearman −0.26，三季穩定）；沿管線（線性→位置交互→防守加成→align→封頂→OVR）與擬合池／權重／名次逐步拆。使用者 2026-11-01「查擬合端」。
- 做法：`reports/F136-fit-side/spec.md`，KJ 為主、KAU 對照。
- 狀態：完成（2026-11-01）：偏差不是擬合造成，是名次比較的均值回歸假象（值殘差 drive +0.02）；lead 補核下季 RAPM 值殘差 drive −0.04，和其他外線欄同級（F-138、L-112）。給分不用改，待使用者核可拆開直接上線。
- 相關：E-194、F-136、F-133、R-130

### E-196
- 日期：2026-11-01
- 問題：R-133 兩步（三分係數全位置共用；得分產量取代 creation、係數下限＝0.2.10g creation）在 card 0.2.10g 上的代價與效果；Klay 卡 314 對 T6 229、接球射手群樣本內平均殘差 −0.21。
- 做法：`reports/card-0.2.10g+E196-production/spec.md`。臂 S（只共用三分）、SP（S＋產量）。定義與係數下限開工前凍結於 spec，不看結果後改（L-026）。A 線：E-181 歷史設定（各季卡對下季 RAPM）無球組低估是否縮小；B 線只報告。
- 狀態：完成（2026-11-01）：G 與 0.2.10g 逐位元組相同。S（只共用三分）樣本外無效也沒壞。SP 樣本外無球組低估三季平均 +5.2→+4.5 百分位點（縮小 0.7，區間不含 0），ρ .394→.398 沒壞；但產量自由擬合係數只有 creation 的 40–54%，下限三張部件卡（歷史 9/9）全觸發。樣本內接球射手殘差 +22→+19 名、Klay 329→304、高量低效沒被抬；前 100 動≥10 名 15 人（DeRozan 68→98）。數字 `results.json`；待 lead 裁定。
- 相關：R-133、E-181、E-187、F-119、R-131
- 來源：使用者 2026-11-01「兩步都做」

### E-197
- 日期：2026-11-01
- 假設：切入／自主拆開（R-130、R-132）：drive→drive_D（帶 driving 描述的 10 呎內自主兩分，量 0.5＋效率 0.5）、creation→creationJ（自主跳投＋低位，不含切入上籃、補籃、空切；E-190 errata-1），兩欄走四季滑動窗口、卡片全部係數重擬合後，前段名次幾乎不動、Zion 類「切入重複算進自主」的人 creation 下修。
- 做法：card／inseason 0.2.10i（直接上線，不做預註冊回測，R-130）。卡片端 `reports/card-0.2.10i/`（drive_pool_D.py→make_tail_0210i.py→run_i.py→build_0210i.py）；賽中端開關集中在 `live/split_dc.py`（window8／window10 crJ／pres_drive D 類），`run_c4_live.py` `SPLIT_DC=0` 重現 0.2.10h（usage／prior／新秀 δ 讀 `_retired/`）；用人層、先驗、錨點重取；build_2k_start 重解 δ（L-109）；自檢 `live/check_inseason_0210i.py`。
- 結果：c0（SPLIT_DC=0）卡片 ranking／three-value／rapm-T6 與 0.2.10g、賽中 ranking.csv 與 HEAD 版程式（0.2.10h）逐位元組相同。卡片端 MIN≥500 前 20 名進出 0、前 100 名移動 ≥10 名 7 人（R-109 字母版）：Cameron Johnson 58→43、Bridges 53→41、Reed 93→79、Sengun 91→81、Tre Jones 39→49、Dosunmu 69→94、Avdija 97→107；Zion creation 86.8→63.4、Luka 104.6→113.1、Jokić drive 91.3→84.5。賽中端前 20 名進出 0、前 100 名移動 ≥10 名 7 人。新卡 creation 對 E-190 KJ 相關 0.953（E-190 是單季池、GP≥30／MPG≥20、聯盟 JSON 分鐘；本版四季窗口、player-games 分鐘）、drive 對 drive_D_U 0.9993（本版 past pool 用 D 類重算）。`reports/card-0.2.10i/progress.md`、`cmp.json`
- 狀態：已完成（2026-11-01），已上線（R-132）。
- 相關：R-130、R-132、E-190、E-194、E-195、F-138、R-109、L-109
- 來源：使用者派工 2026-11-01

### E-198
- 日期：2026-11-02
- 問題：加「無球引力」能力值（NBA.com AVGOFFBALLPERIMETERGRAVITYSCORE，2025-26；缺值 OLS 補）進卡片 OVR，全部係數重擬合、不設下限，接球射手組被低估是否縮小。
- 做法：`reports/card-0.2.10j+E198-gravity/{preregistration.md,spec.md}`（凍結 2026-11-02）。基準 card 0.2.10i KAU；樣本外用 2025-26 本季 RAPM＋分半（引力只有 2025-26 起，無歷史季）。
- 已揭露：F-139、E-181、E-196；引力名次前段（Curry 2026-27 第 1、Klay 兩季前 8；2025-26 無 Curry）。沒看過加入後的係數或卡片。
- 狀態：完成（2026-11-02，lead 抽驗 c0 sha 8b3e99d6、預註冊 sha、results.json judge）：A 不過（接球射手組低估 12→12 百分位點，MDE 8.3）；沒弄壞過。係數 +0.19/10 點但從 creation 分走；F-141。待使用者裁定
- 相關：F-140、R-134、F-139、E-181、E-196
- 來源：使用者 2026-11-02「取而代之的可以是無球跑動或引力 預期klay curry要上升」→「放」→「不設下限」

### E-199
- 日期：2026-11-02
- 問題：新賽季本季權重乘 k（1／2／4／8）後，開季 c=10、20 場時的賽中 OVR 對該季剩餘場次 RAPM 預測是否變準（F-142 額度第 1 個）。
- 做法：`reports/E199-inseason-speed/{preregistration.md,spec.md}`（凍結 2026-11-02，sha c0d303ee）。建置 2024-25 選 k*，驗證 2025-26 判 A；as-of 重建，目標 plain 剩餘場次 RAPM。
- 已揭露：現行本季佔比 3%／12%／23%／44%（c=5／20／41／82）；F-047 跨季前瞻快衰減較差。沒看過任何季內剩餘場次結果。
- 狀態：phase0 停下（2026-11-02 task 20261102-015430-3a8f5f；lead 抽驗 probe_mu.mjs）：NBA matchups 端點不吃 DateFrom/DateTo（三種條件回傳 sha 相同、全季 7,672 場），老將 onBall/help 無法 as-of；advanced、rim/three、hustle 可以。沒跑任何臂，不扣 F-142 額度。作廢（2026-11-02 使用者指出目標搞錯：要的是遺忘調陡＋季末四指標不歪，不是剩餘場次預測；由 E-201 取代，L-113）
- 相關：F-142、F-047、R-112、R-118
- 來源：使用者 2026-11-02「Open an issue card on speed」→「Write the spec」

### E-200
- 日期：2026-11-02
- 問題：把 E-198 的無球引力（gravity）上線到卡片（2025-26）與新賽季（2026-27）兩頁：每日抓本季引力、網站 GRV 欄取代主畫面切入的位置、更新說明。（spec 寫 E-199，該號已被 E-199 速度問題卡用掉，改記 E-200）
- 做法：`reports/card-0.2.10j/{spec.md,progress.md}`。卡片＝E-198 KG 臂定版（build_0210j.py，與 KG-final 逐位元相同）；賽中 `live/gravity_live.py`（2025-26＋本季 FRAMES 加權×四季窗口季權重，缺值 OLS，凍結池 gravity-pool-card0210j.json）、`scripts/fetch_gravity.mjs`＋daily step_fetch_gravity；新秀起點 build_2k_start 重解 δ。
- 已揭露：E-198 結果（A 不過，F-141）與 R-135（使用者接受、空間長人下降是對的）；不是新假設檢定，只是上線。
- 狀態：完成（2026-11-02）：GRAVITY=0 兩端逐位元重現 0.2.10i；check_inseason_0210j.py 全過；R-109 前 100 名移動 ≥10 名卡片頁 11 人、新賽季頁 10 人，前 20 各進出 1 人（Fox 進），字母版 0.2.10j。Klay 卡片 419→357、新賽季 343→316；Turner 108→123。
- 版號：2026-11-02 使用者升為 PATCH 0.2.11（R-137；原標 0.2.10j，檔名沿用）
- 相關：E-198、R-134、R-135、F-141、R-109
- 來源：使用者 2026-11-02「兩頁都上」

### E-201
- 日期：2026-11-02
- 問題：遺忘調陡（窗口 WIN 328→246／164／123，逐場線性形狀不變）後，新賽季 ΔOVR 是否更敏感，且 2025-26 季末 OVR 對 RAPM、EPM、2K、薪水四項的 ρ 都沒比現行低超過 2×雜訊（F-142 修訂版額度第 1 個）。
- 做法：`reports/E201-steeper-forgetting/{preregistration.md,spec.md}`（凍結 2026-11-02，sha 0576a637）。係數不重擬合，只換窗口。
- 已揭露：現行本季佔比；c≈5 老將 |ΔOVR| 中位數 0.59；F-047。沒看過任何調陡結果。
- 狀態：完成（2026-11-02 task 20261102-021317-e64072；lead 抽驗 results.json）：敏感度隨窗口縮短上升（老將 |ΔOVR|>2：46→53／67／75 人），RAPM、EPM、2K 都沒歪；薪水三臂都歪（W246 ρ 0.631→0.610，差 0.020＞2×h 0.018）→ 依預註冊排除，扣 F-142 額度 1。c0 線上 484 人、卡片 582 人差 0.0。限制：護欄 B 走卡片路線（onBall／help／壓迫／引力用單季值）；執行中 02:30 每日管線刷新 2026-27 資料（數據仍至 10-31）。使用者 2026-11-02 裁定採用 W246（R-140），上線見 E-204
- 相關：F-142、E-199、L-113、R-112、R-118
- 來源：使用者 2026-11-02「讓新賽季的數據更敏感…遺忘指數設陡一點…季末分數和四個檢查指標偏移不要太遠」→「GO」

### E-202
- 日期：2026-11-02
- 問題：TO 改成「每持球分鐘失誤率（收縮）0.5＋持球時間/36 0.5」、全部係數重擬合後，TO 對 2K27 Ball Handle 是否更準、TO 榜是否不再被不持球的人佔據，且整體 OVR 沒弄壞（F-143 額度第 1 個）。
- 做法：`reports/card-0.2.10j+E202-to-possession/{preregistration.md,spec.md}`（凍結 2026-11-02）。底 card 0.2.10j；收縮法沿用 E-069 方法 c 的選法、分子改全部失誤。
- 已揭露：現行 TO 前 30 有 19 人持球低於中位數；三種用球量名次（Jokić 球權 5／持球 58、Brunson 13／2）；失誤率與球權/36 相關 0.08。沒看過新 TO 的數值、係數或名次。
- 結果（role-card 子代理，lead 抽查 results.json／KT ranking 相符；969a835）：A 過（TO 對 2K27 Ball Handle ρ 0.08→0.79，MDE 0.088）；沒弄壞過（c0 逐位元、npm test、OVR 對本季 RAPM ρ 0.591→0.575，門檻 −0.114）；B 19→0。代價：TO 與 creation／pass 相關升到 0.72／0.78（VIF 5.4），OVR 對 EPM ρ 0.793→0.769，前 100 有 34 人移動 ≥10 名；Kornet OVR 名次 62→99、Jalen Williams 10→22。A 大幅通過部分是定義使然（2K Ball Handle 本身偏用球量，E-069 已見 0.74）。
- 狀態：完成（2026-11-02，待使用者裁定採用；未做 role-audit）
- 相關：F-143、R-136、R-032、E-069、E-198
- 來源：使用者 2026-11-02「用持球時間」

### E-203
- 日期：2026-11-02
- 問題：把 E-202 的新 TO（持球時間）上線到卡片（2025-26）與新賽季（2026-27）兩頁：每日抓本季 Possessions tracking、網站 TO 說明與提示卡、更新說明。
- 做法：`reports/card-0.2.12/spec.md`。卡片＝E-202 KT 定版；賽中用凍結池；`TOV_POSS=0` 重現 0.2.11。不是新假設檢定，只是上線。
- 狀態：完成（2026-11-02 上線）。結果：card／inseason 0.2.12 已 push（2991760、5041e99）並發布 gh-pages 7fc64c4；卡片 ranking.csv＝E-202 KT 定版逐位元組相同、TOV_POSS=0 重現 0.2.11 逐位元組相同、npm test 過；前 100 名移動≥10 名：卡片頁 34 人、新賽季頁 35 人。偏離：正式產物放 card-0.2.12-tov/（card-0.2.12/ 是舊廢棄夾）；新秀 tovSkill 混合斜坡 RAMP_MIN=1000 為自訂參數，非預註冊
- 相關：E-202、R-139、F-143
- 來源：使用者 2026-11-02「直接採用」

### E-204
- 日期：2026-11-02
- 問題：遺忘窗口 W246 上線到卡片（2025-26）與新賽季（2026-27）兩頁，接在 0.2.12 之後；補驗線上路線季末四項 ρ（只報告）。
- 做法：`reports/E204-window-246/spec.md`。`WIN_LEN=328` 重現 0.2.12。不是新假設檢定，只是上線。
- 狀態：完成（2026-11-02 task 20261102-043125-773d10；未發布時見 handoff）。結果：inseason／card 0.2.12b（兩頁同標，我的假設）；`WIN_LEN=328` 兩頁逐位元重現開工時線上版（484／582 人 OVR 差 0.0）；老將 |ΔOVR| 中位數 0.77→0.80、>2 的 43→53 人；前 20 名換 2（新賽季頁）／1（卡片頁）人、前 100 名移動≥10 名 15／14 人；季末四項 ρ（卡片路線）RAPM +0.008、EPM +0.000、2K27 +0.005、薪水 −0.016；npm test 過。`reports/E204-window-246/report.md`。偏離：usage／prior 檔不重取（load_usage 對 card-0.2.12b 仍核對 card-0.2.12-tov sha）；season_nav.py 未動（另一 session 的未 commit 改動，待辦清單在 report.md）
- 相關：E-201、R-140、F-142、E-203
- 來源：使用者 2026-11-02「Adopt W246」

### E-205
- 日期：2026-11-02
- 問題：0.2.12 TO 的持球時間佔一半，與 creation／pass 重複計分（VIF 5.4），中段持球者 OVR 偏高（Reaves 26→12、KPJ 32→17）。
- 做法：`reports/card-0.2.12+E205-to-weight/preregistration.md`（凍結 a29f657）：權重 0.75·z(−r)＋0.25·z(v)，全部係數重擬合；A＝VIF ≤3；保住 E-202 Ball Handle 增益；RAPM 不劣 2h；B＝F-143 ≤10。
- 狀態：完成（2026-11-02，f5d15ed／967bb72）。結果：A 沒過（VIF 5.37→4.10，門檻 3）；保住 E-202、沒弄壞、B 過；Reaves 12→12、KPJ 17→17 沒動（兩人每持球分鐘失誤本來就在池前 15，不是靠持球量）；前 100 名只 2 人動 ≥10。建議不採用，等使用者裁定
- 相關：R-141、E-202、F-143

### E-206
- 日期：2026-11-02
- 問題：0.2.12 TO 用每持球分鐘失誤，偏袒每次觸球拿很久的人（F-144：Reaves、KPJ）。
- 做法：`reports/card-0.2.12+E206-to-touches/preregistration.md`：r 分母換觸球次數（k、kh 依池觸球／持球分鐘換算），v 與權重不變，全部係數重擬合；A＝tovSkill 與每觸球秒數的相關下降 ≥ MDE；保住 E-202；RAPM 不劣 2h；B＝F-143 ≤10。
- 狀態：完成（2026-11-02，d6a95f2／9bb1b1b）。結果：四項硬條件都過（TO 與每觸球秒數相關 0.71→0.22；VIF 5.37→1.80；RAPM 小升）；但 Ball Handle ρ 0.79→0.50（仍過 E-202 門檻）；Reaves OVR 12→12、KPJ 17→16 幾乎不動（TO 名次 13→27、14→39）。待使用者裁定採用
- 相關：R-143、F-144、E-205、F-143

### E-207
- 日期：2026-11-02
- 問題：E-206 觸球分母上線到兩頁（card 0.2.12a／inseason 0.2.12b）。
- 做法：`reports/card-0.2.12b-touch/spec.md`。`TOV_TOUCH=0` 重現線上 0.2.12／0.2.12a。不是新假設檢定，只是上線。
- 狀態：完成（2026-11-02）。card／inseason 0.2.12c 上線（commit e92fae6，gh-pages 0540dcd）；疊在 W246 的 0.2.12b，池與係數在 328 窗口建（＝E-206 KC final 988b741f）再套到 W246 卡片路徑；TOV_TOUCH=0 兩端逐位元組重現 0.2.12b。**11-02 後續：池與係數已在 W246 重擬合**（使用者裁定原擬合在 328 窗口、套到 W246 不一致）：z 平均／標準差、收縮先驗、0–99 映射、全部 OVR 係數改 W246 擬合（底 `reports/card-0.2.12c-w246/`），版號維持 0.2.12c；卡片頁前100名移動≥10名 3 人（對舊 328 擬合），TOV_TOUCH=0 仍逐位元組同 0.2.12b；其他七項池仍 328 建。工作夾 `reports/card-0.2.12c-fit246/`。產物 `reports/card-0.2.12c/`、`reports/card-0.2.12c-w328/`，自檢 `live/check_inseason_0212c.py`
- 相關：R-144、E-206

### E-209
- 日期：2026-11-02
- 問題：R-096 新秀起點曲線 T(順位)=73−5.9·ln(順位) 在現行 inseason／card 0.2.12b 管線下還站不站得住；B 重播 2025-26 屆前 3/6/10/20 場與季末，看第 6 場加分留多少；C 把 2026 屆放進 B 的分布。派工編號 E-208，與 `reports/E208-team-rating` 撞號，本條改記 E-209，報告目錄仍是 `reports/E208-rookie-start-recheck/`。
- 做法：量測，不改任何線上檔。程式狀態＝git HEAD 7c588dc（0.2.12b），工作樹他人 0.2.12c 換版未用（四個模組改從 HEAD 載入）。A 為 E-141 真新秀 246 人（前20場視窗／季末，線上算法含 usage 層與只資料兩套）；B 為 D3 40 人（補 7 人）；C 為 2026 屆 42 人。補值／缺值逐項清單與 sha256 見 `reports/E208-rookie-start-recheck/report.md`。樣本內（R-007），沒有擬合新曲線參數（L-026）。
- 狀態：完成（2026-11-02）。結果：線上算法下曲線比實際陡很多（狀元、2–3 順位中位低於曲線，11 順位以後高過 3～13 分），且 2025-26 屆「只資料」第 6 場加分平均 −0.4，線上正值大半來自 usage 層（第6場 +5.0 → 季末 +8.9），推估 2026 屆 ≥90 分鐘組季末 Δ 約 +10～+11，不會回吐；新(只資料)對 E-141 舊值狀元 −11 的主要部分無法拆開，原因不確定。
- 相關：R-096、E-141、E-116
- 來源：派工 20261102-054542-36d76c 第 1、2 輪

### E-208
- 日期：2026-11-02
- 問題：能不能把全名單模擬變成球隊 ORtg／DRtg／Net、每場勝率、整季預測勝場，並贏過 B0（上季淨效率＋主場）。
- 做法：`reports/E208-team-rating/preregistration.md`（commit 7eec8cb，回測前）。H=2.5、σ=12 寫死；P′（部分污染）／I（樣本內）；(a) 實際名單分鐘／(b) 季前預期分鐘；每場 40 seed、評分 200 seed（5090）。
- 狀態：完成（2026-11-02）。P′(a) Brier 0.192 對 B0 0.247，CI 不含 0，通過；P′(b) 0.224 也贏 B0；勝場 MAE 4.2（a）／6.5（b）對 B0 10.9。標「部分污染，只當參考」，(a) 用事後名單。2026-27 前瞻已凍結（`forward-2026-27-frozen.json`），待之後對真實賽果。
- 相關：F-145、L-114、R-007、R-113、L-091
- 報告：`reports/E208-team-rating/report.md`

### E-210
- 日期：2026-11-02
- 問題：新秀鏈的 usage 層能不能從第 0 場就用「預期用球量」（候選 U1：pn = p + (1−w)(full_prior−p) + w(full−p)，w=min(N/10,1)，full_prior 用先驗分鐘 mpg0），拿掉 E-209 看到的前 10 場機械爬升（約 +9）；δ 依 build_2k_start 方法重解使 N=0 OVR＝T(順位)。
- 做法：`reports/E210-rookie-usage-start/`，shim `u1_lib.py`（原封呼叫 `chain_rookie` 三次重組），不動 live／src／CURRENT。程式＝HEAD 71e2d88（0.2.12c）；B 為 2025-26 屆 40 人重播、A 為 E-141 真新秀 246 人、live 兩版完整主流程。mpg0 用線上全體常數 14.3085（未看 2026 結果，L-026）。
- 狀態：完成（2026-11-02），未採用也未否決，等使用者裁定。機械爬升拿掉（合成「照預期」新秀 B0 前 10 場 +8.2、U1 0.00）；2025-26 屆前 6 場平均加分 +4.8 → +1.0、前 10 場 +8.9 → +2.9、季末 +9.1 → +6.0；2026 屆 ≥90 分鐘 14 人平均 Δ +7.8 → +6.3（剩下約 +2.1 是真分鐘、+4.3 是資料）。副作用：x0 平均再壓 4.3，歷屆真新秀前 20 場／季末普遍降約 3 分，高於曲線比例降（31–60 順位 85% → 66%）；Lendeborg 排名 59 → 95。老將 442×47 欄逐字相同。樣本內描述，不是準確度證據（R-007）；量測在 0.2.12c，與 E-209（0.2.12b）B0 差約 1。
- 相關：E-209、R-096、E-141、E-116、L-026、L-109
- 報告：`reports/E210-rookie-usage-start/report.md`

### E-211
- 日期：2026-11-02
- 問題：E-209（0.2.12b 只資料的前 20 場窗口 OVR）比 E-141 ans0 低 8–12 分（#1 −11.2、2–3 −10.8）；差在哪一版、哪個機制。
- 做法：`reports/E211-rookie-gap-attribution/`。worktree 重建 E-141 環境（9a1cf39＋凍結 card027 檔），逐版 checkpoint 用同一人群、同一量法（eval_rookie own、只資料）重算；程式不動 live／src／CURRENT。
- 狀態：完成（2026-11-02）。ans0 逐人逐位元重現（246/246，最大差 0.0）；終點與 E-209 A-players 只資料逐人一致。#1 66.5→55.3：量法差 −3.6、起點 R-096 +2.8、0.2.8 −4.9、**0.2.9a −9.9**、0.2.10h −1.0、0.2.11 +7.5、0.2.12b −2.2；2–3 62.5→51.8，0.2.9a 占 −12.7。0.2.9a 的 2×2 對調顯示是 pw／anchors 的函式下移約 11–13 分，窗口屬性本身沒變差。量法差 −3.8 未拆。樣本內描述（R-007）。
- 相關：E-209、E-141、E-164、R-096、R-107、R-007、L-026
- 報告：`reports/E211-rookie-gap-attribution/report.md`


### E-212
- 日期：2026-11-02
- 問題：（E-208 補做）E-208 的 2025-26 勝利在 ≤2023-24 屬性（P″）下重現嗎；近 10 場實際分鐘 (c)、能力排序 (d) 比季前預期 (b) 好嗎。
- 做法：`reports/E208-team-rating/`，預註冊 `preregistration-2024-25.md`（commit 0a30bdc，跑前）；5090 byte-exact 同步；bootstrap 2000、種子 20261102。
- 狀態：完成（2026-11-02）。2024-25 P″(b) Brier 0.2562 輸 B0 0.2391（CI 不含 0，方向相反）＝未通過；(c) 兩季都顯著優於 (b)，(d) 兩季都輸 (c)。2024-25 只有 1104／1230 場、官方資料抓不到改用 boxscore（偏離，已揭露）。2025-26 (b) 先前已看過。
- 相關：E-208（補做）、F-146、R-113、R-007
- 報告：`reports/E208-team-rating/report-2024-25.md`

### E-213
- 日期：2026-11-02
- 問題：（E-208 第二階段）把 (c)「最近 10 場實際用人」球隊評分接上每日傷病名單，並在網站發布球隊頁。
- 做法：`scripts/team_ratings_daily.py`（ESPN 傷病＋CDN 賽程＋(c) 今日陣容／近況兩版，sim 0.1.4、200 seeds）、`scripts/build_teams_page.py`（teams.html）、`daily_inseason_update.py` 新步驟（失敗不擋原頁）；不改 src／卡片／能力值算法／E-208 凍結檔。
- 狀態：完成（2026-11-02），已發布到 gh-pages（teams.html）。每日計算 104 秒。評分仍是模擬值，E-208 回測僅與上季淨效率打平，頁面已標「僅供參考」；未做新的樣本外檢驗。偏離：官方 PDF 後備未做（沿用上次檔並標日期）。
- 相關：E-208、E-212、R-113、L-115、L-116
- 報告：`reports/E208-team-rating/report-site.md`

### E-214
- 日期：2026-11-02
- 問題：（E-213 追加）ESPN 傷病名單失敗時，改用 NBA 官方傷病報告 PDF，而不是直接沿用前一份。
- 做法：`scripts/team_ratings_daily.py` 加官方 PDF 備援（順序 ESPN → 官方 PDF → 沿用前一份；`pdftotext -raw` 解析；`--injury-source auto|espn|pdf`）；`build_teams_page.py` 傷病日期優先顯示報告時間；測試 `test/team_ratings_gate.py`＋`test/fixtures/injury-report-2026-11-02_04_15AM.txt`。不改 src／卡片／凍結檔，不新增排程。
- 狀態：完成（2026-11-02）。`--injury-source pdf` 實測成功（04:15 ET 那份，83 人，同名球員隊伍與 ESPN 零不一致）；PDF 有 8 隊 NOT YET SUBMITTED、缺陣人數比 ESPN 少，只當備援不取代 ESPN。偏離：解析用 `-raw` 不是 `-layout`（-layout 會把列錯位）。
- 相關：E-213、L-115
- 報告：`reports/E208-team-rating/report-pdf-fallback.md`

### E-215
- 日期：2026-11-02
- 問題：（E-213 追加）球隊評分分鐘只平均球員有出場的比賽、最近沒出場的現役主力（自己平均 ≥15 分）補回、預測勝場依 ESPN 回歸日逐場換陣容；手機版看不到版本切換。
- 做法：`scripts/team_ratings_daily.py`（`own_avg`／`candidate_minutes`／`lineup_out`、逐場陣容狀態各模擬一次）、`scripts/build_teams_page.py`（切換列改 class `vctl`，傷兵顯示回歸日）、測試 `MinutesReturn`；不改 src／卡片／凍結檔／E-208 回測檔。
- 狀態：完成（2026-11-02）。切換列原本被 site_header 的 `.wrap>.ctrl{display:none}` 藏起來（桌面手機都看不到）。15 分鐘門檻今天補回 0 人（賽季才 7–8 場）；回歸日讓 POR 52.4→41.9、DET 46.4→54.1 等（POR 是引擎認為 Morant＋Sharpe 缺陣反而較強）。每日 161–173 秒（舊 104 秒）。網站規則修改，未做樣本外檢驗。
- 相關：E-213、E-214、L-115
- 報告：`reports/E208-team-rating/report-minutes-return.md`

### E-216
- 日期：2026-11-02
- 問題：（E-213 追加）上季整季缺陣、引擎卡和 live 排名都沒有的非新秀（Kyrie、Lillard、Haliburton、VanVleet 等）在球隊評分被當成平均球員。
- 做法：`scripts/team_ratings_daily.py`（`BASE_CARDS`／`load_base_cards`／`base_profiles`，`engine_inputs` 加 `base`）、`scripts/team_ratings_sim.mjs`、`scripts/build_teams_page.py`；底卡＝最近一張有他的賽季卡（2024-25 v5 -min → 2023-24），能力值相對該卡聯盟平均加在平均 profile 上，不做年齡調整；測試 `BaseCards`；不改 src／卡片／凍結檔。
- 狀態：完成（2026-11-02）。補 6 人（Kyrie、Lillard、Haliburton、VanVleet、Lyles、Niang），Hezonja 等無任何歷史卡仍為平均。DAL −5.8→−7.6、POR +4.1→+1.4、HOU +1.6→+0.4（今日 Net）。POR「拿掉 Morant 反而變好」仍成立：Morant 單人邊際 −4.3，與控球後場重疊只解釋約 1–2 分，交 lead。
- 相關：E-213、E-215、L-115
- 報告：`reports/E208-team-rating/report-missing-profiles.md`

### E-217
- 日期：2026-11-02
- 問題：模型的「球星重疊損失」OL 大的隊，實際淨效率是否系統性高於模型（R＝實際−模型）？若是代表引擎對多創造者同場遞減扣太重。
- 做法：預註冊（98a09b8）後，兩季（2024-25 P″、2025-26 P′）各 30 隊，每隊整季 (c) 分鐘代表輪替前 4 名 OVR 代理球星，單人／四人同場／全平均 共 7 變體各 1000 場（5090）；OL＝Σ單人增益−四人增益；主檢定 Spearman(OL,R)，隊重抽 5000 次 90% CI。不改引擎。
- 狀態：完成（2026-11-02），**H1 不通過**。2024-25 ρ=−0.111 [−0.376,+0.170]；2025-26 ρ=+0.025 [−0.318,+0.360]；合併前 10 後 10 的 R 差 −0.51 [−2.88,+1.73]。OL 本身多半是噪音（SE 中位數 1.6≈隊間 SD；奇偶分半 ρ 0.02／0.30），檢定力低，不能據此說遞減沒問題。OL 與創造者人數 ρ 0.54／0.32。OL 最大 5 隊：TOR 25-26、PHX 24-25、BOS 24-25、LAL 25-26、TOR 24-25。偏離：analyze.py 描述段補 7 位不在 582 人名單的球星姓名（判定邏輯未動）。
- 相關：E-208、E-213、L-026、R-007
- 報告：`reports/star-overlap/report.md`

### E-218
- 日期：2026-11-02
- 問題：開季前段讓老將 onBall／help 窗口裡的本季權重變大（×2、×4），對球隊剩餘賽季 DRtg 的預測會不會更準？（起因：76 人本季失分效率第 3，模型 DRtg 卻略差於平均）
- 做法：預註冊（f679143）後，2024-25（主、樣本外）與 2025-26（同向確認）每隊第 10、20 場快照；截至 D 的追蹤表用 stats.nba.com DateTo＋逐場 boxscorematchupsv3 重建（配對層與季總計差 ≈0）；E-208 組隊 (c) 輪替對平均隊 200 seed（5090），A0 現行／A1 ×2／A2 ×4。
- 狀態：完成（2026-11-02），**H1 不通過**。2024-25 ΔMAE A1 −0.058 [95% −0.140,+0.021]、A2 −0.091 [−0.247,+0.058]；2025-26 同向 −0.019／−0.031。次要：A2 讓快照 onBall 對剩餘賽季 onBall 的 MAE 小 0.35–0.76（四組 CI 都不含 0），help 改善小。2026-27 描述：A2 時 Maxey onBall 67→63、76 人 DRtg 第 13→15，加快更新不會讓 76 人變好。
- 相關：R-076、E-208、L-117、L-026
- 報告：`reports/defense-update-speed/report.md`

### E-220
- 日期：2026-11-03
- 問題：`fineSourcePlan` 三分 logit 全域位移 δ 能不能補上模擬 3PAr 對 2025-26 實際的缺口，且節奏偏慢（缺口約 3.3 回合）是不是同一個來源？
- 做法：預註冊 3（凍結 11-03 03:42，`reports/3par-logit-shift/freeze.json`）；變體只加 `SHIFT3`（logit 單位）；對手 C0 現行 av、C1 位置池；δ 網格 0→0.4 校準（seed 720），判定集 seed 721，30 隊 seed 540+ti；5090 跑，不改 `src/`。節奏＝FGA−OREB+TOV+0.44·FTA（與預註冊 2 的回合事件數不同，δ=0 缺口 3.28）。Kp＝(T−S)/(R_pace−S)。
- 狀態：完成（2026-11-03），**3/5**。δ*：C0 0.27、C1 0.10，判定集 3PAr 0.4152／0.4140（實際 0.4151），遷移成功。節奏 Kp＝0.08（C0）／0.05（C1），判「節奏不同源」。副作用 P0／E1／E3／E4／E5／E6 全過。機制：出手區不影響回合長度（準備與出手時間在抽區之前）；出手與進攻籃板同向增加在節奏公式裡抵銷。閘門（重現、SHIFT3=0 逐場相同、非 no-op）全過。
- 相關：E-219、R-146、F-148、L-026
- 報告：`reports/3par-logit-shift/report.md`

### E-221
- 日期：2026-11-03
- 問題：賽中窗口只加重本季最近幾場（u'＝u×(1＋b·exp(−距今場數/h))，最後 20% 季淡出、季末＝單季卡），能不能讓 OVR 跟著近況評分先漲、平庸後回落（F-142 第 3 次修訂指標 A1 追蹤度），而不弄壞季末卡（F-142 額度第 2 個）。
- 做法：`reports/E221-inseason-recent-boost/preregistration.md`（草稿）。9 候選 b∈{1,3,6}×h∈{5,10,20}＋B0；訓練 2023-24、2024-25 選 W*，測試 2025-26；A1＝Spearman(OVR_c−OVR_0, 近 10 場評分−上季評分)，c∈{5,10,20,30,41,60}；回落、爆發追趕、跳動、之後 20 場預測只報告；硬條件 npm test、b=0 逐位元重現、季末差 0、單場跳動 p95 ≤ 3×B0。不重擬合。
- 已揭露：2026-27 至 11-01 評分變化對 dOVR 相關 0.33 與 Sengun／Caruso／Edwards／Jokić 例子；E-138／E-139／E-201／E-204 全部結果；2025-26 第三次當測試季。沒看過任何加成候選數字。
- 狀態：已凍結（2026-11-03，使用者「凍結開跑」；sha256 1d8561e9…1e34，見 `preregistration.sha256`；HEAD b23adf6），執行中（role-card）
- 狀態更新：phase 0 停在 c0d（2026-11-03，role-card）：`RECENT_BOOST` 開關已做（`live/recent_boost.py`，關閉＝b0 逐位元相同）；c0n 過；c0d 不過——2022-23、2023-24 沒有 Z1 評分資料，訓練季 0 個可用；追蹤表項目（防守／壓迫／引力）沒有逐場列做不了 §1；線上管線回放寫死 2026-27；c0 對線上 11-01 檔 72／484 人不同（線上檔早於 0.2.12c 重擬合）。沒跑任何候選。errata-1 草稿等使用者核可（F-149）。`reports/E221-inseason-recent-boost/{phase0.json,errata-1.md}`
- 狀態更新：第 2 輪停在 B1 第一步（2026-11-03，role-card）：2024-25 的 season-source 與 defense-seventh 逐列不同（見 F-150、L-119），依勘誤「不同就停下回報」未轉換 2022-23／2023-24、未跑回放與候選；已做與此無關的 G1 修復（`test/team_ratings_gate.py` 改驗併入名單頁的排行檢視，`npm test` 退出碼 0）與 `recent_boost.py` 註解更正。凍結的預註冊與勘誤未改，F-142 額度未扣。
- 狀態更新：第 3 輪停在 phase 0 的 MDE（2026-11-03，role-card；使用者選 A＝訓練季評分用完整資料、errata-2 已凍結）：已做 Z1 評分重建（`work/scorer_x.py`，2022-23／2023-24 全 M0、2024-25 約 9.8% 列退回 M0）、A1 補丁含 pres_drive 的 drive 逐場出手（b=0 逐位元相同）、c0（同棵樹 off≡b=0）、c0n 過；停手原因＝預註冊 §4 MDE 定義 B0 對 b=0 兩臂逐位元相同 → 差恆 0 → MDE＝0（F-151、L-120），另 2023-24 窗口資料不齊依 §2 改只用 2024-25 訓練；已寫 `errata-3.md` 草稿等使用者裁定。尚未跑回放引擎、B0 的 A1 現值、候選與測試季；F-142 額度未扣（沒有候選結果）。
- 狀態更新：完成，**不採用**（2026-11-03，第 4 輪 role-card、lead 審）：MDE（errata-3 A1）＝0.101；訓練季 2024-25 A1：B0 0.387，b1 0.417–0.422、b3 0.445–0.451、b6 0.460–0.474（越強越高，但 b≥3 多數超過跳動 3× 上限）；依平手規則 W*＝b1h20。測試季 2025-26（M0 尺）A1 0.478→0.492，+0.015 < MDE → 照凍結規則不採用（成對 bootstrap 90% 區間 [+0.003, +0.026] 只報告：方向真實但很小）。只報告：回落比 0.89→0.69、爆發追趕 30→23 場、冷卻 25→14 場、單場跳動 p95 0.73→1.24、預測 ρ 0.224→0.210。前瞻 2026-27：Flagg +2.5、Sengun +0.8、Caruso +0.6、Garland −1.4、Jokić −0.6。lead 註：MDE 用單臂 bootstrap（含兩臂共有的抽人雜訊）約為成對區間的 8 倍，門檻過嚴（見 L-121）。result.md 由 lead 依 results.json 撰寫；未經 role-audit 重算。
- 相關：F-142、R-147、R-092、R-140、E-138、E-139、E-201、L-026
- 來源：使用者 2026-11-03「評分暴漲的場次，我也沒看到OVR跟著大漲」→「就算會回到原本水準，也應該先暴漲 再隨著平庸才回落」→ 選「B 放寬窗口權重」

### E-222
- 日期：2026-11-03
- 問題：E-221 選出的近期加成 b1h20，在沒看過的 2026-27 能否讓 OVR 追近況（A1）超過成對雜訊？（F-142 診斷，R-149，不扣額度）
- 做法：`reports/E222-recent-boost-diagnostic/preregistration.md`。兩臂 B0 vs b1h20；A1 只取 c=10、20（避開已看過的開季 6 場）；MDE_p＝2×成對 bootstrap 90% 半寬（訓練季 2024-25，看 2026-27 前寫入 mde.json）；30 隊都滿 20 場的第一次每日更新自動跑一次。
- 已揭露：E-221 全部結果、2026-27 至 11-01 的 8 人前瞻表；2026-27 A1 未算過。
- 狀態：已凍結（2026-11-03，使用者「只做診斷」；sha256 9e68be56…1c85），待觸發（約 2026-12 上旬）
- 狀態更新（2026-11-03）：MDE_p＝0.0300（訓練季 2024-25，成對半寬 0.0150；W*−B0 點估 +0.0176、90% 區間 [+0.0028, +0.0327]；n＝212 人；虛無試算 B0 對 B0 半寬 0、W* 對 B0 0.0150 通過）寫入 `mde.json`；觸發腳本 `e222_eval.py` 已掛 `scripts/daily_inseason_update.py`（step_prereg_e222，失敗不擋發布），目前回「未觸發」（各隊最少 4 場）；本機約 1 分鐘可跑完，不需 5090。c→g 用「所有球隊都打滿 c 場的最短聯盟場次前綴」。
- 相關：F-142、R-147、R-149、E-221、L-120、L-121


### E-223
- 日期：2026-11-03
- 問題：戰力排行改成 OVR×分鐘為主（M1／M2，R-152，F-153）能否讓缺陣高 OVR 球員使球隊變弱，且樣本外準度不比現行模擬 Net（M0）差？
- 做法：`reports/E223-team-rating/preregistration.md`（commit 66335fd，先於 2025-26）。訓練 2024-25（k＝10.61；a／b＝0.102／9.94；MDE_B 0.0100、MDE_W 1.25），樣本外 2025-26；OVR 用上季 v5 -min 卡（舊定義，季中不更新）；分鐘 R-151；傷病用 box score 實際缺陣；H＝2.5、σ＝12 凍結；5090 18 shards，S＝100／200。
- 結果：A 線達成（M2 r 0.981 對 M0 0.40）。樣本外 Brier B0 0.2473／M0 0.2024／M1 0.2168／M2 0.2113；勝場 MAE 10.89／3.81／7.83／7.09。硬條件勝場 MAE（≤+2.5）M1 +3.40、M2 +2.72 皆不過；B 線 M2 過（+0.0088）、M1 不過。2026-27 今日>c：M0 6、M1／M2 1。M0 的 2025-26 數字含 E-208 重度污染，比較對 M0 有利；未經 role-audit。
- 狀態：完成，硬條件未過，待使用者裁定（2026-11-03）；未上線
- 相關：F-153、R-152、E-208、R-151、L-041、L-121

### E-224
- 日期：2026-11-03
- 問題：戰力排行的評分對手（現行：10 個位置平均球員 × 24 分鐘，平均分差約 +6）換成「與真實球隊同結構的梯度隊」（輪替 36…10 分鐘、同一 OVR 階梯、最強球員位置 PG…C 輪換的五支隊），排名會變嗎？樣本外預測會變好嗎？
- 做法：`reports/E224-gradient-opponents/preregistration.md`（commit 2950d06，先於任何新對手模擬）；B5＝五支梯度隊各 20 場、A5＝拉平梯度對照；兩季（2024-25、2025-26）都未擬合參數；OLD 直接用 E-223 的 M0 模擬檔。模擬跑 5090，結果在 `reports/E224-gradient-opponents/work/`。
- 結果：H1、H2 過。B5−OLD Brier −0.0021（2024-25）／−0.0009（2025-26），遠小於 MDE 0.0100，90% 區間跨 0 → 無改善；Spearman ρ 0.997／0.998，最大名次變動 2 名 → 排名實質不變。梯度隊把分差總平均從 +5.5／+6.3 拉到 −0.4／+1.5。探索性：各隊對五支對手的分差標準差約 3 分。
- 狀態：完成（2026-11-03）；結論「直覺在此引擎不成立」（準度與排名不變），但使用者裁定因分數置中、表達更清楚而上線為球隊評分對手（R-158）
- 相關：E-208、E-223、R-151、R-153、L-083、L-041、R-007
- 備註：2026-11-03 同日另一對話曾用 E-224 暫編「模擬單人價值」，已改號 E-226（見 R-154 附近的改號裁定）。

### E-225
- 日期：2026-11-03
- 問題：Transformer（球員 embedding＋本季能力值／OVR，場上 10 人 self-attention）在留出場次上預測 stint 每回合淨值，是否明顯優於同特徵、無交互作用的加法 ridge（B1）？（F-155）
- 做法：`reports/E225-lineup-transformer/design.md`、`preregistration-draft.md`。資料 `build_dataset.py`（13 季 stints＋每季能力值表，大檔不進 git，sha256 在 `manifest.json`）；能力值用 v4 卡 2021-22～2025-26（OVR 的 RAPM 窗不含目標季）、e111 2017-21（無 OVR、無防守屬性）、2026-27 live；2014-17 無屬性。主訓練核心四季 2021-22～2024-25，主測試每季 20% 場次；前向 2025-26、2026-27 只報告；臂 A／A-prev（上季能力值）／A-ext（加 2017-21）／A-noattr。模型寬 64、2 層、4 頭、約 0.17M 參數；5090 估 3–4 GPU 小時。
- 已揭露：資料盤點、驗證折 fold 0 的 B0／B1-id／B1 MSE 與 bootstrap（MDE 草稿 22.2）、2023-24 smoke test（管線通、驗證損失下降）。測試場次與 2025-26／2026-27 未讀。
- 狀態：設計中（預註冊草稿待使用者核可）（2026-11-03）
- 狀態更新：第一版完成，**採用「配合學得到」結論**（2026-11-03，R-157 改為只用能力值、不放 OVR 與球員 ID；凍結 7b92328、結果 61bf18d）：測試 898 場淨值 MSE，T-min−B1-min −16.75 [−22.6, −11.1]、T-nomin−B1-nomin −24.87 [−30.4, −19.4]，MDE 11.23，判定 1、2 兩臂皆過；前向 2025-26 兩臂方向一致；上場時間沒有加分。只報告：個人價值與防守 RAPM 相關僅 0.21–0.25，防守側翼被低估、大球權得分手被抬高，五中鋒陣容被評 +13.5 → 第二輪 E-227。個人價值 v2（隨機真人隊友）見 `results/value-v2.json`。未經 role-audit。
- 相關：F-155、R-154、R-157、E-224、E-227、R-153、L-022、L-031

### E-227
- 日期：2026-11-03
- 問題：陣容 Transformer 補真實數據（hustle、護框／三分防守、對位、拆開的攻守籃板率、進階）後，留出場次預測是否比只有能力值明顯更準？防守側翼是否被看見？（F-155，R-159）
- 做法：`reports/E227-lineup-transformer-r2/preregistration.md`（凍結 2b37fac，使用者 2026-11-04 核可）。訓練 2021-22～2025-26 五季（2021-22 追蹤數據抓不到，遮罩）；三臂 R2-abil／R2-stats／R2-stats-rapm（RAPM 只用訓練場次擬合）；不放上場時間、不放球員 ID；5 seed。
- 已揭露：2021-25 測試場次 E-225 已讀過一次；2025-26 整季 E-225 前向讀過。
- 狀態：完成，**採用 R2-stats**（2026-11-04 使用者「採用並稽核」；結果 3db92f9）：測試 1,135 場，R2-stats−R2-abil −17.63 [−24.7, −10.3]（MDE 15.36）、R2-stats-rapm −18.66（MDE 14.21），判定 1、2 皆過；加 RAPM 只多 1.0（跨 0）。五中鋒偏好 +4.0→+0.2；價值與防守 RAPM 相關 0.28→0.40，但與 2K26、薪水、進攻 RAPM 相關下降；防守側翼仍偏低（Dean Wade 168／卡 102、Herb Jones 210／128、Draymond 197／128）；排列重要性第一是 stamina（＝場均分鐘百分位，F-156）。凍結後新場次 0 場。稽核完成（dffeac3，4/5 原結論站得住：判定 1、2 獨立重算相同、無測試洩漏；疑慮：stamina 帶回分鐘資訊，拿掉後排名 Spearman 0.944；第 7 名是 Scottie Barnes 不是 Harrison，L-122）。探索臂去 stamina 預測變差、防守側翼更低，保留 stamina（F-156 結案）。
- 相關：F-155、R-159、R-157、E-225、L-026、R-042
- 報告：`reports/E227-lineup-transformer-r2/report.md`

### E-228
- 日期：2026-11-04
- 問題：把陣容 Transformer（E-227 R2-stats 架構）當球隊評分引擎，在沒看過的 2025-26 預測每場勝負與季勝場，是否不比現行模擬 M0 差？
- 做法：T-2425＝同超參數只用 2021-22～2024-25 重訓（5 seed）；賽前特徵用 2024-25 整季；陣容與分鐘沿用 E-223 `work/lineups-2526.json`；每隊依分鐘抽 5 人陣容取平均淨值，勝率 Φ((margin±2.5)/12)，無擬合參數。判定草稿：Brier(T)−Brier(M0) 區間上界 < MDE_B 0.0100、勝場 MAE 退步 ≤ 1.25。前向 2026-27 只報告。`reports/E228-transformer-team-rating/`
- 已揭露：M0 的 2025-26 結果 E-223 已讀過（且含 E-208 污染，對 M0 有利）；T 的 2025-26 結果未讀。
- 狀態：完成，兩項判定未過（2026-11-04；凍結 6d55e32、errata-1 守門路徑）：2025-26 Brier T 0.2175／M0 0.2024（+0.015 [0.007, 0.023]），勝場 MAE 7.53／3.81；M0 用同季屬性（E-208 污染），T 只用上季特徵，與 E-223 M2（0.2113／7.09）同級；T＋M0 各半 Brier 0.2007（探索）。交使用者裁定，建議 2026-27 前向對決。`reports/E228-transformer-team-rating/report.md`
  - 2026-11-04 補做同資訊重比（T2425 換 2025-26 同季特徵，fc3cb5b）：T Brier 0.1883 對 M0 0.2024（−0.014 [−0.020, −0.008]），勝場 MAE 2.93 對 3.81；原未過是資訊不對等造成。採用見 R-160。
- 相關：E-227、E-223、E-224、R-153、R-158、F-155

### E-229
- 日期：2026-11-04
- 問題：2026-27 前向，兩者都用同季資訊、都在賽前記錄時，T（E-227 R2-stats 權重）的每場勝率是否不比現行模擬 M0 差？
- 做法：`reports/E229-transformer-vs-m0-forward/`。每日 M0 算完後 `predict_daily.py` 用同一份今日陣容與分鐘記錄開賽前 pT／pM0（掛在 `daily_inseason_update.py` 的 `step_e229_forward`，失敗只警告）。T 特徵：box 五欄本季與 2025-26 依 w＝min/(min+500) 混合（K 事前定死），hustle／追蹤等 21 欄每日沒抓、全程用 2025-26。評估：每隊滿 40 場（約 2027-01-19），只算凍結後記錄的比賽。判定草稿：J1 Brier(T)−Brier(M0) 90% 上界 < 0.013（E-228 子抽樣半寬）；J2 5 箱校準最大偏差 ≤ 0.15。
- 已揭露：E-228 結果；K=500 事前設定；21 欄停在上季。
- 狀態：進行中（2026-11-04 使用者核可凍結；MDE_B 0.013、CAL_MAX 0.15、min-games 400）；每日記錄中，約 2027-01-19 每隊滿 40 場時跑 `eval_forward.py`
  - 2026-11-04 更新：使用者否決等到 2027（L-123）；改用手上資料：E-228 同資訊重比與 E-229b 本季 107 場回測都是 T 較準，R-160 當天換上球隊評分。本條降為附加記錄，不再是換不換的門檻。
- 相關：E-228、E-227、E-223、R-153、R-158

### E-230
- 日期：2026-11-04
- 問題：夏季聯賽＋季前賽的出賽記錄，有沒有「選秀順位以外」的資訊能預測新秀前 20 場的表現？（新秀起點改用出賽記錄的第一步；沒記錄的照舊用順位）
- 做法：`reports/E230-sl-preseason-rookie-start/`。246 位 E-141 歷屆新秀，信號 D＝兩來源 game score/36 對聯盟水準的偏差、分鐘加權縮向 0（常數 100 分鐘）；M0＝a+c·ln(順位)、M1＝M0+b·D，留一屆交叉驗證，答案＝E-208 `win20`。判定 P1 配對 bootstrap 上界<0、P2 ≥5/7 屆、P3 七折 b>0。
- 已揭露：E-208 逐屆 `win20` 與順位的關係（樣本內）；沒看過任何新秀的 SL／PS 數字。
- 結果（2026-11-04，`report.md`）：預註冊 P1／P2／P3 全成立，效果量 0.36 < 0.5 → 「有訊號但太小」。MAE 12.05→11.69，P1 區間上界 −0.007（貼 0）、P2 剛好 5/7 屆（Y5、D1 退步）、b 七折皆 >0（約 1.2–1.6）。只用 SL 無訊號（改善 0.05），只用 PS 0.51，訊號來自季前賽；`win20C` 次要答案 4/7 屆，P2 不成立。`win20` 與順位幾乎無相關（r≈−0.01），M0 近乎常數。全樣本 b＝1.51、D 標準差約 2.8，典型位移 ±4；2026 屆顯示位移達 ±10，遠超樣本外改善所能支持，不套用。
- 揭露：預註冊 §2.1 把 `win20` 說成「與 ans0 同概念」不精確（errata 寫在報告）；`backtest.py` 首跑 PLAYER_ID 型別不合（int／str）導致涵蓋率 0，只修型別、完整重跑，未改公式、常數、判定。獨立 role-audit 未做。
- 狀態：已完成（2026-11-04），未 commit、未稽核；實驗結論＝順位曲線維持，SL／PS 不納入線上。**同日使用者核可後，僅季前賽位移以全 b=1.51 套用到線上（R-162，inseason 0.2.12e，推翻預註冊 §5；`PS_START=0` 回退）**。是否另開實驗（逐項起點；預註冊 §2.5 寫的「E-231」編號已被復出老將補卡佔用，要用時 `claim_id.py E` 領新號）待使用者決定
- 相關：E-208、E-141、E-116、R-073、R-096、R-113

### E-231
- 日期：2026-11-04
- 問題：2025-26 整季沒打、今年復出的老將（Lillard、Kyrie、Haliburton、VanVleet 等）進不了賽中排行，能不能「跳過受傷賽季、拿更早的賽季當先驗」補進來？
- 做法：`live/build_returning_vet_prior.py` 從 v5 卡（2024-25，其次 2023-24，sample.min≥800）補卡進 `prior-2025-26-card0212c-rv.json`，只補 6 人；補的卡年齡不明（無年齡加分）、gravity／foulDraw 等用中性 70，不進 H1 封頂／百分位／引力擬合池（`PW.EXCLUDE_T`、`cap_total_lift(pool)`、`fit_exclude`）；lastOVR 的分鐘基準用 v5 場均分鐘（`rvMpg`）。`RETURNING_VETS=0` 重現 0.2.12c。
- 結果（2026-11-04，使用者核定「改回照窗口」，最終版）：補卡球員的防守加成照滑動窗口算，跟其他老將一樣（窗口含 2024-25；中間一度改成歸零，使用者指出不一致後撤掉，L-124）。既有 484 人 OVR 與 `RETURNING_VETS=0` 同條件重跑逐位相同（最大差 0）、pointwiseCheck 1e-11、`live_current_gate`／`rookie_start_gate` 通過；新增 6 人：Lillard POR 97.1（#6，N=6）、Kyrie DAL 96.9（#8）、Haliburton IND 96.5（#9）、VanVleet HOU 88.1（#44）、Lyles MIN 69.1（#208）、Niang GSW 64.1（#259）。舊卡（v5 2024-25，刻度不同）Kyrie 90.3 #24、Lillard 85.6 #44、Haliburton 84.7 #51；本季 0 場的 lastOVR 為 94.6／92.1／92.9（Haliburton／Lillard／Kyrie）。已知疑點：防守加成（RAPM D 疑似受隊友影響，VanVleet pred0 −0.26 卻 +1.47）是全模型項、不是補卡專屬，未開實驗。補卡法回測（n=60，有連續兩季的球員拿前一季補卡 vs 實際當季卡）平均差 −0.11、平均絕對差 1.99、相關 0.969（樣本內診斷，R-007，不算證據）；偏差多在年輕進步者。
- 已揭露：版本設計前已看過 6 人的 v5 數字；沒調參。
- 限制：先驗卡是兩年前的；本季只有 4–8 場；v5 onBall 量尺（sd 6）與現行（17.4）不同；12 位沒有任何歷史卡的人（Hezonja、Dix、Ike 等）仍缺。
- 狀態：已實作（inseason 0.2.12d，卡仍是 0.2.12c；防守加成照窗口版，使用者 11-04 核可「改回照窗口」），未 commit、未發布
- 相關：L-124、R-161、R-064、R-109、E-207、F-125

### E-232
- 日期：2026-11-04
- 問題：卡片 OVR（15 項能力值對 RAPM 擬合出的公式）當陣容預測器，在 E-227 同一批留出場次上，預測 stint 淨值比 B1-abil 與 Transformer（R2-abil／R2-stats）差多少？（使用者 11-04 指出「擬合公式交給 Transformer」理論上同一件事，本實驗把這句話量出來）
- 做法：`reports/E232-ovr-as-lineup-predictor/preregistration-draft.md`。O1＝c＋b·(兩隊 5 人 OVR 加總差)，b、c 只用 split=train 回合加權最小平方法擬合；其餘臂讀 E-227 既有預測存檔；OVR 取 v4 卡（E-225 `players-*.csv` 的 `ovr`），不是現行 0.2.12c。判定 1：R2-abil−O1 ≤ −MDE 且成對 90% 區間上界 < 0；判定 2：O1 贏過 B0。MDE 凍結前在 train fold 0 量。
- 已揭露：測試場次 E-227 已讀過；B1／R2 對照數字已看過；v4 卡的擬合係數用 2022-23～2024-25 RAPM，與測試季重疊（樣本內，偏向 OVR），乾淨子集＝2025-26 測試場次（只報告）。
- 狀態：預註冊草稿已寫，未凍結、未讀測試、未派工；**2026-11-04 使用者改要求「乖乖用能力值 Transformer 算 OVR」，陣容比較版擱置，改做 E-234**
- 相關：E-227、E-225、R-160、F-156、L-026、L-041、R-042

### E-234
- 日期：2026-11-04
- 問題：15 項能力值 → 卡片 OVR，交給 Transformer 學（不給 RAPM 項），用 2023-24／2024-25／2025-26 當訓練集，輸出 2026-27 的 OVR 給使用者人工檢查（使用者 11-04 指定；探索性，無預註冊判定）。
- 做法：`reports/E234-attr-to-ovr-transformer/fit_final.py`、`fit_hold.py`。每個能力值一個 token（寬 64、2 層、4 頭、平均池化），5 seed 平均；ridge(λ=10) 並排；訓練用 v4 卡三季（RAPM 只取目標季之前）。輸出 `predict-2026-27.csv`（490 人）。
- 結果：留一季（MIN≥300）RMSE Transformer／ridge＝6.36／5.75、5.75／5.84、6.86／6.26，相關 0.84／0.86、0.88／0.87、0.83／0.86，Transformer 沒贏過加法 ridge；2026-27 對網站 0.2.12d 相關 0.83（ridge 0.86），Transformer 平均低 1.0，MIN≥100 的 254 人中 56 人差超過 10。
- 限制：2026-27 能力值定義是 0.2.12c／d（tovSkill、drive、creation 改版、四季窗含本季）而訓練是 v4，定義漂移；同定義的 2025-26 0.2.12c 卡 RMSE 7.9（比留一季 5.8–6.9 差）；OVR 的 RAPM／年齡項能力值無法解釋。
- 已揭露：留一季第一次跑被 25 分鐘超時砍斷，兩折結果取自第一次、2025-26 折與最終訓練重跑（同設定同 seed）；沒調參。
- 狀態：已完成，名單交使用者人工檢查，未稽核
- 相關：E-232、E-227、R-076、L-026

### E-236
- 日期：2026-11-04
- 問題：E-234 之後使用者指出「輸入才是問題」。(A) 把 RAPM 與位置當輸入，(B) 讓四季能力值定義一致，Transformer 預測 OVR 會不會變準（使用者 11-04 指定「AB」；探索性，無預註冊判定）。資料夾沿用工作名 `reports/E235-attr-rapm-to-ovr/`（領號拿到 E-236，資料夾改不了名）。
- 做法：`fit_a.py`。輸入組 V0＝15 項能力值；V1＋位置 one-hot；V2＋位置＋原始 RAPM（0.75·pooledNet、0.75·pooledD，按位置去中心，pooledPoss<1000 補 0，加有無 RAPM 旗標）；V2c／V1c＝去掉定義漂移的 drive、tovSkill、onBall、pressure。RAPM 窗口用各季卡當時的窗口。不放 pred／pred0／bonus／align（那是答案）。同 E-234 的 Transformer，3 seed 留一季，最終 5 seed；每組並排同輸入 ridge（含位置×五項交互的 ridge_inter）。名單 `predict-2026-27-A.csv`。
- 結果（留一季 MIN≥300 的 RMSE，Transformer／ridge）：V0 6.36／5.75、5.75／5.84（2025-26 見 E-234）；V1 6.20／5.72、5.74／5.84、6.51／6.27（位置幾乎沒幫助）；V2 4.40／4.39、3.91／4.35、4.66／4.76（ridge_inter 4.15、4.07、4.47）；V1c、V2c 比含漂移項差 0.8–1.4。2026-27 對網站 0.2.12d：V0 7.90、V1 7.88、V2 7.41（ridge 7.11）、V2c 7.79；留一季的 RAPM 增益在 2026-27 只剩約 0.5。
- 結論：RAPM 是留一季的大增益（約 −1.5 到 −2.0），但 OVR 本身由 RAPM 項（0.25·(r−pred0)＋防守加成）構成，所以主要是學回公式；Transformer 加 RAPM 後與同輸入 ridge 打平或小贏，沒有明顯贏。步驟 B：完整重算 2023-24／2024-25 成 0.2.12 不划算（`card_route_0212c.py` 寫死 PRIOR=2025-26 與凍結池；tovSkill 需 Possessions-FULL；NBA.com 引力 2023-24／2024-25 回 HTTP 500），「去掉四項」試過更差，不能當統一定義的替代。2026-27 仍差約 7 分，主因是網站 0.2.12d 的定義與窗口和 v4 不同（含本季四季窗），不是模型容量。
- 限制：S*（2026-27）用 v4 的 2021-22_2024-25 窗，網站卡窗含本季，口徑不同；v4 係數用 2022-23～2024-25 RAPM 擬合，對訓練季部分樣本內；位置只用 G→SG、F→PF 對應；Draymond 仍 98.8 對網站 74.8、Gobert 74 對 84、Porter Jr. 74 對 89，大落差沒被 RAPM 項修好。
- 已揭露：V2 的 2025-26 折第一次被逾時砍斷，重跑（同設定同 seed）；沒調參。
- 原始表可用性（11-04 查，唯讀，未建模）：2021-22～2025-26 每季逐場箱score（FGA／FGM／3P／FT／OREB／DREB／AST／TOV／MIN）對 v4 卡 playerId 100% 比得上（605／539／572／569／582 人）；PBP 投籃（區域、助攻者）涵蓋 534–589 人，且 PBP 2 分出手數與箱 FGA−3PA 中位數比 1.000（最低 0.95）。2021-22 PBP 無 `area` 欄（130k 筆），要用座標規則分區（v4 管線已有）。2026-27 只有 107 場箱score、106 場 PBP，489 張卡中 435 人有箱score（其餘為新秀／只有先驗）。onBall／help／pressure 來自追蹤／防守來源，不是箱score，無原始表可直接建；physique／heightInches 來自 bio。已確認（11-04）：2021-22～2024-25 的 v4 卡能力值來自該季自己的單季 prior（`prior-<S>.json`，含 `observed` 原始總數）＋前季 RAPM；2025-26 的能力值則是正式卡（card-H1-m0）屬性，不是同一條管線（prior 檔註明），且 `observed` 缺 mid／short 區間。
- 狀態：步驟 A、B 完成，名單交使用者人工檢查，未稽核；使用者 11-04 選步驟 C 的「原始＋防守三項」，轉 E-237
- 相關：E-234、E-232、R-076、R-114、L-026

### E-237
- 日期：2026-11-04
- 問題：E-236 之後，把消化過的 15 能力值換成原始出手數／命中數（箱score＋PBP shotDistance 三層）＋不變的 onBall／help／pressure／physique／height＋位置＋RAPM，Transformer 預測卡片 OVR 會不會比 E-236 的 V2 更準，且贏同輸入 ridge。使用者 11-04 指定（「A」）。
- 做法：預註冊草稿 `reports/E237-raw-inputs-to-ovr/preregistration-draft.md`（臂 R0–R4、同留一季切分、判定表兩類都要過、門檻 0.3 點）。2026-11-04 使用者「凍結並開跑」，已凍結；凍結時未跑任何 E-237 模型。
- 已知風險：2025-26 能力值來自正式卡而非 v3／v4 的單季 prior，原始特徵與能力值的對應在這季可能不同；2021-22 PBP 無 `area`，所以全部改用 `shotDistance`。
- 結果（留一季 MIN≥300，Transformer 三季平均 RMSE）：R0 4.39（基準）、R1 原始＋防守三項＋RAPM 5.16（各季比 R0 差 0.57／0.61／1.15）、R2 無 RAPM 6.58、R3 R1＋能力值 4.43、R4 R0＋MIN／GP 4.48；含交互 ridge R0 4.24、R1 5.23。規則1、規則2 都不過；R0 seed std 0.077。2026-27 對網站卡 R0 7.81、R1 10.18。
- 結論：原始出手／命中數不比消化後能力值好，Transformer 沒贏含交互 ridge，RAPM 是必要輸入；MIN／GP 不是隱藏輸入。判 1/5 不採用，E-234～E-237 線收。報告 `reports/E237-raw-inputs-to-ovr/report.md`、名單 `predict-2026-27-E237.csv`。
- 已揭露：R0 2024-25 為 4.22，E-236 V2 為 3.91（訓練列 MIN≥100 與 seed 差異，沒追）；R4 不含防守回合數；2026-27 僅 107 場，per-36 噪音大。
- 狀態：完成（2026-11-04），未稽核。
- 相關：E-236、E-234、L-026、R-007、F-159


### E-238
- 日期：2026-11-04
- 問題：使用者說 Luka、Maxey 無球三分出手快、產量高，且不能因無球多就扣開發分。NBA.com 接球／拔起／出手速度追蹤資料，能不能補進現有能力值（gravity、threeValue、creation）。
- 做法：預註冊 `reports/E238-offball-tracking/preregistration.md`（5 個追蹤特徵；H1 單特徵對下季 RAPM 殘差、H2 開發＋接球 A 組 vs 純開發 B 組、H3 留一季 ridge；評估口徑＝E-179）。2026-11-04 lead 自訂標準後凍結，凍結時未算任何特徵與殘差關係。
- 已知風險：單季特徵；quick（觸球 <2 秒占比）只是出手速度代理；H1 沒做多重比較校正；2026-27 只有 7 場，只報告不判定。
- 結果：H1 只有 quick（+0.27）過、H2 A 組比純開發少被高估 +0.11、H3 增益 −0.004 不過 → 判「只當個案顯示，不進 OVR」（F-158）。`reports/E238-offball-tracking/report.md`
- 狀態：完成（2026-11-04），未稽核。
- 相關：E-181、E-179、E-196、R-130、E-234、E-236、R-165、F-158

### E-239
- 日期：2026-11-04
- 問題：NBA.com 進攻追蹤全套（拔起、接球、切入、擋拆、handoff、Synergy 戰術、出手分割、hustle，71 個特徵，2013-14～2026-27）能不能補進卡片／OVR 漏掉的東西？哪些穩定到可當卡片格子？（使用者「開，全套多季」，接 E-238）
- 做法：預註冊 `reports/E239-tracking-full/preregistration.md`（lead 自訂標準、直接凍結，R-165）。H1 偏 Spearman（控制 pct(OVR)、pct(creation)，BH q=0.10）、H2 年對年穩定度、H3 留一季 ridge（control／E238／full／sel）；評估台沿用 E-179／E-238（卡 t 季 → 下季 RAPM，2022-23～2024-25）；窗口 w4 為主、w1 對照。抓取 `fetch_all.mjs` 466 檔 0 失敗，評估 `e239_eval.py`。
- 已知風險：只有三個評估季；2024-25 起 NBA 追蹤定義疑似斷層（drv_vol 7.25→10.55、paint_ppt 0.89→0.57、top_vol 3.08→5.23），四季窗口混新舊定義；沒測 Transformer／非線性；出手速度只有 quick 代理。
- 結果：H1 穩健訊號 0 個（w4 無通過；w1 只有 pu_vol）；H2 穩定（≥0.60）42 個、所有效率類（ppp、tov）<0.30 是雜訊；H3 full（71 特徵 λ=50）w4 增益 +0.095（三季皆正）、w1 +0.059，過門檻，但 sel（+0.014）與 E238（−0.004）不過 → 凍結規則判「只當卡片格子」，不進 OVR。`reports/E239-tracking-full/report.md`
- 狀態：完成（2026-11-04），未稽核。
- 相關：E-238、E-179、F-158、F-160、R-165

### E-240
- 日期：2026-11-05
- 問題：三分球的「量」與「率」拆法（出手量、收縮命中率、量×(率−替補)）比現行 `long`（只含準度）更能預測下季進攻 RAPM 嗎。使用者 11-05（E-237 之後）提出「換個量和率的價值預測性可能更好」，並指定一次測一項、先測三分。
- 做法：預註冊 `reports/E240-three-point-volume-rate/preregistration.md`（11-05 凍結，sha256 0d934e7f…）；E-179 人群（t=2022-23～2024-25，867 人次）；基底＝位置＋九項進攻屬性，ridge λ=10，留一季，答案＝下季 O×W；8 臂（A0–A7），有改進＝對 `long` R² 增益≥0.01、三折至少兩折為正、bootstrap 90% 下界>0。
- 結果：沒有任何一臂過線。A4（量＋率分開）R² 0.238 vs 現行 0.224（+0.014，區間 [−0.002, +0.030]，24-25 折 −0.006）；`long` 對完全不放三分只 +0.004；改善集中在後衛（+0.027），前鋒中鋒沒有。判定「維持現狀」。
- 結論：3/5 不採用；三分整體對下季進攻 RAPM 邊際貢獻小，不為 0.014 改卡。報告 `reports/E240-three-point-volume-rate/report.md`。
- 狀態：完成（2026-11-05），未稽核。
- 相關：E-237、E-238、E-179、E-057、F-161、R-165

### E-241
- 日期：2026-11-05
- 問題：三分能力值用不同「出手量／命中率」混合比例（s＝w·量百分位＋(1−w)·率百分位）時，用 Transformer 訓練哪個比例預測下季進攻 RAPM 最好。使用者 11-05 澄清 E-240 的意思是比例掃描而非固定拆法。
- 做法：預註冊 `reports/E241-three-point-blend-sweep/preregistration.md`（11-05 凍結，sha256 61abeeb6…）；E-179 人群 867 人次；基底＝位置＋九項進攻屬性＋一欄三分；w∈{0,.2,.4,.5,.6,.8,1}＋不放／`long`／量×率共 10 臂；Transformer（E-235 Net）3 折×5 種子平均，ridge 參考；判定＝最佳 w 對 `long` 增益≥max(0.01,2×種子 std)、兩折為正、bootstrap 下界>0、相鄰格也贏。
- 結果：機械判定過線，候選 w＝0.2（Transformer R² 0.059 vs `long` 0.011）；但 Transformer 絕對 R² 僅 0.00–0.06（ridge 0.22–0.24），單種子多為負、相鄰格跳動（w0.2→0.5：0.059→0.001），ridge 曲線倒 U 在 w＝0.5–0.6（0.238，只比 `long` 好 0.014）。
- 結論：2/5 不採用；候選不可信，卡片維持。報告 `reports/E241-three-point-blend-sweep/report.md`。
- 狀態：完成（2026-11-05），未稽核。
- 相關：E-240、E-237、E-179、E-057、F-162、R-165

### E-242
- 日期：2026-11-05
- 問題：改用真正的五打五陣容 Transformer（E-227 `LineupNet`，五季 111,499 個訓練 stints、fold 0 早停、5 顆種子）量測三分能力值「出手量／命中率」比例 w（含 7 個固定比例臂、單位變異數端到端可學習權重臂 `WL`、以及 `T0`／`T1`／`TV`），看哪個比例抽出的進攻影響力最能預測下季進攻 RAPM 與樣本外比賽得分。
- 做法：預註冊 `reports/E242-lineup-tf-three-blend/preregistration.md`（11-05 凍結，sha256 a9807019…）；固定其餘 14 項能力值，第 0 欄替換為單位變異數混合 $z_{\text{3PT}}(w)$；每臂訓練完後以 1000 組同位置隨機替換陣容抽出 E-179（867 人次）個人三分邊際進攻影響力 `off3_val`（M1：基底＋`off3_val` 預測下季 O×W）與個人總進攻影響力 `off_val`（M2：位置＋`off_val`），並評估五季 `split=test`（1,135 場、34,624 個 stints）單邊每百回合得分 MSE。
- 結果：徹底消除 E-241 過擬合雜訊（M1 單種子 std 僅 0.0006–0.0018），量出平滑倒 U 曲線：M1 R² 從 w＝0（0.2256）單調升至 **w＝0.6 最高（0.2328，w＝0.5 為 0.2324）** 再降至 w＝1（0.2294），與 E-241 ridge 最佳比例（0.5–0.6）完全吻合；M2 總進攻影響力在 **w＝0.6–0.8** 最高（0.1949–0.1962）；測試場次對戰得分 MSE 亦在 **w＝0.8** 最低（4628.61 vs 純率 W00 4633.52，成對差 −4.92，90% CI [−7.43, −2.34]）；自學權重臂 `WL` 5 顆種子穩定收斂至 **w＝0.342±0.025**。惟 M1 對 `T1` 增益 +0.0063 的 90% CI 為 [−0.0027, +0.0153]（跨零），依 L-041 停下交使用者裁定。
- 結論：4/5 停下交使用者裁定；報告 `reports/E242-lineup-tf-three-blend/report.md`。
- 狀態：完成（2026-11-05），未稽核。
- 相關：E-241、E-240、E-227、E-179、F-163、R-165

### E-244
- 日期：2026-11-05
- 問題：R-167 後使用者指定測罰球 `ft`：把 E-242 的陣容 Transformer（`LineupNet`）框架換成替換 `ft` 欄，量「罰球出手量 FTA/36 ／ 命中率 FT%」比例 w 是否比現行 `ft` 更能預測下季進攻 RAPM。
- 做法：預註冊 `reports/E244-ft-lineup-tf-blend/preregistration.md`（11-05 凍結，sha256 5b2f2fc3…）；10 臂（T0、T1、W00–W10 七格、WL）× 5 種子；收縮常數 k 每季用 beta-binomial 動差法估（約 23–28）；M1 基底不含 `ft`；判定門檻同 E-242，增益一律對 T1（R-167）。5090 `~/side_projects/pure_ovr/experiments/e244/`（首跑 6 路並行 OOM，缺 5 臂以 2 路補跑，無結果影響）。
- 結果：M1 R² T1 0.2226、W00 0.2227、W04 0.2242、W06 0.2253、W08（w*）0.2255、W10 0.2235、WL 0.2248（學出 w＝0.42±0.07）；w* 對 T1 增益 +0.0029，門檻 0.005 未過，90% CI [−0.0057, +0.0120]，三折 +0.0099／+0.0088／−0.0075。測試場次 `pts100_MSE` 所有臂都比 T1 差 0.5–1.1（T1 4628.2）。T0（不放罰球）R² 0.2197，罰球整欄對 R² 只貢獻 +0.003。
- 結論：2/5 不採用，`ft` 維持不動；報告 `reports/E244-ft-lineup-tf-blend/report.md`。
- 狀態：完成（2026-11-05），未稽核。
- 相關：E-242、F-164、R-167

### E-257
- 日期：2026-11-07
- 問題：球隊本季到目前的籃板率（進攻籃板率、讓對手進攻籃板率）能不能預測 T＋R-171 K10 殘差之後還剩的誤差？（POR 診斷第二輪：籃板 +3.2 分／場、F-081 模擬個人籃板影響只有實測一半；使用者「做」）
- 做法：預註冊 `reports/E257-rebound-rate/preregistration.md`（11cd2e9）；設計同 E-254（n/(n+5) 收縮置中、主減客、OLS 擬 B0 殘差），臂 SORB／SDRB／SREB，Bonferroni 98.33%；2026-27 前向 107 場。
- 結果：J1 不過，ΔBrier +0.0000／+0.0010／+0.0010；訓練段讓對手籃板率係數方向相反（+37±27）；整季 β 都在 1 個標準誤內（+3pp ≈ 0.3 分／場）。上一季籃板率對本季殘差相關 +0.07／+0.20（方向反）。POR 只再多 +0.4。1/5 不採用。`reports/E257-rebound-rate/report.md`
- 結論：籃板好的球隊打得比 T 好已經在殘差裡（R-171 已加回），籃板率沒有額外預測力；T 沒有系統性低估籃板。POR 剩下差距是 7 場樣本只採信約四成。
- 狀態：完成（2026-11-07），未稽核。
- 相關：E-254、E-256、E-253、R-171、F-081

### E-256
- 日期：2026-11-07
- 問題：R-171 殘差拆成三分命中／罰球命中／兩分命中（對上一季聯盟命中率，自己減對手）／其他，哪一部分會延續？分開收縮能否更準？（使用者問「怎麼知道是看錯還是會回落」）
- 做法：預註冊 `reports/E256-luck-split/preregistration.md`（8715446）；2025-26 季前凍結 T，10–12 月擬 β、1–4 月測；臂 TOT／SPLIT2／SPLIT4，Bonferroni 98.33%；2026-27 前向 107 場。
- 結果：J1 不過，三臂 ΔBrier +0.0003／+0.0012／+0.0028；J2 點估計 −0.0000～−0.0009。整季延續 β：三分 0.68±0.17、罰球 0.93±0.54、兩分 1.10±0.12、其他 1.03±0.09；隊層級前 7 場 vs 後段同成分相關三分 0.15、兩分 0.64。1/5 不採用。`reports/E256-luck-split/report.md`
- 結論：只有三分命中（含對手）明顯回落；兩分命中優勢與量／籃板／罰球率都會延續。POR 本季超出主要是結構型（其他 +8.1、兩分 +4.4），推翻 E-254 條目「兩分命中偏高、會回落」的說法（L-130）。
- 狀態：完成（2026-11-07），未稽核。
- 相關：E-253、E-254、R-171、R-172、L-130、E-239

### E-255
- 日期：2026-11-07
- 問題：擋拆持球（Synergy PRBallHandler）當新增第 16 欄能力值，量率混合比例多少、控制 creation 之後還有沒有價值、每點值多少勝？（使用者看完 POR 拆解問「擋拆怎麼加進屬性、每點值多少勝利貢獻」，「開實驗」）
- 做法：預註冊 `reports/E255-pnr-handler-lineup-tf/preregistration.md`（sha256 4db71551…，訓練前凍結）；E-245 LineupNet 框架，新增 pnr 欄（量＝POSS/36、率＝每回合得分收縮 k≈150–200），臂 T0／W00–W10／WL；M1＝基底（含 creation）＋offpnr_val 預測下季進攻 RAPM；閘門 cross_test（Synergy 季總量含 test 場次）。
- 結果：五道硬閘全過。w*＝0.6，M1 R² 0.2242→0.2388（+0.0146，CI [+0.002, +0.027]，三折全正，相鄰格皆正）；純量／純率幾乎無效；WL 學到 w＝0.77；直接 ridge +0.010；增益集中前鋒（0.174→0.207）。每點 +0.0059 進攻 RAPM，30 分鐘球員每 10 點 ≈ +0.10 勝。副作用：低回合球員率百分位虛高（Sochan 26 回合 78.8 分）。
- 結論：4/5 候選，待使用者裁定是否加 pnr 能力值；上線前要先修低回合門檻再驗一次。`reports/E255-pnr-handler-lineup-tf/report.md`
- 狀態：完成（2026-11-07），未稽核。
- 相關：E-245、E-242、E-239、E-254、R-166、R-130

### E-254
- 日期：2026-11-07
- 問題：球隊本季到目前的出手結構（三分出手佔比、中距離出手佔比、罰球率，進攻／防守端）能不能預測 T＋R-171 K10 殘差之後還剩的每場誤差？（POR 診斷：三分出手第 2、中距離第 30，屬性只有準度；使用者「Go」）
- 做法：預註冊 `reports/E254-shot-diet/preregistration.md`（eb6025e 凍結）；2025-26 用 E-228 pred-T-2526，10–12 月擬 OLS β、1–4 月測；4 臂 S3／SMID／SALL／SALLD，Bonferroni 97.5%；2026-27 前向 107 場（中距離用 leaguedashteamshotlocations DateTo 季累積）。
- 結果：J1 不過，四臂 ΔBrier +0.0000～+0.0017（全部 ≥ 0）；β 不穩（三分係數訓練段 +19、整季 +5±8；中距離 +0.5→−18±13）；季層級 30 隊相關 |r|≤0.19。硬套整季 β，POR 只 +0.5 分／場。判定 1/5 不採用。`reports/E254-shot-diet/report.md`
- 結論：出手選擇不是 T 的系統性缺口（跟著球員走、T 已隱含）；POR 進攻超出預期主要是擋拆／切入兩分命中偏高（`reports/por-offense-diag/report.md`），預期回落。
- 狀態：完成（2026-11-07），未稽核。
- 相關：E-253、R-171、R-172、F-172、E-240、E-239

### E-253
- 日期：2026-11-07
- 問題：戰力排行（T）不吃已打完比賽的結果（POR 本季進攻第一、淨效率第一，T 排第 14）。每隊「實際分差 − T 預期」累積殘差 ÷ (場數 + k) 加回下一場預測，會不會更準？
- 做法：預註冊 `reports/E253-actual-results-blend/preregistration.md`（commit e9ebda7 凍結）；臂 T0／K5／K10／K20／K40／K10c（殘差截 ±15）；J1 主測 2025-26 1230 場（E-228 T2425 季前特徵預測），Bonferroni 98% 區間；J2 前向 2026-27 E-246 107 場（線上 T1），採用臂點估計 ≤ 0。
- 結果：2025-26 Brier T0 0.2175 → K5 0.2007（−0.0168 [−0.0256, −0.0076]）、K10 0.2008、K20 0.2019、K40 0.2041，五臂全過；第 20 場時預測全季勝場 MAE 5.75 → 3.14。2026-27 K5 +0.0016（J2 不過），K10／K20／K40／K10c −0.0019～−0.0028，全跨零。套 K10 後 POR 14→9、HOU 4→1、MIN 8→2、BOS 1→5、DEN 6→10。
- 結論：3/5（J1 過、J2 不過），交使用者；報告 `reports/E253-actual-results-blend/report.md`。
- 狀態：完成（2026-11-07），未稽核；2026-11-07 使用者採用 K10（R-171）
- 相關：F-172、E-228、E-246、R-160、R-152、R-153

### E-246
- 日期：2026-11-05
- 問題：球隊評分 Transformer（e229_live）的 21 欄追蹤統計（hustle 9、rimthree 4、matchup 2、adv 6）一直只用 2025-26；照 box 同規則（w=min/(min+500)）混本季，本季每場勝負預測是否不比現行差？（使用者 11-05：官網 hustle 每天更新，不能不用）
- 做法：預註冊 `reports/E246-t-tracking-blend/preregistration.md`（commit 68603bc 凍結）；三臂 T0／T1（21 欄全混）／T1h（只混 hustle）；回測用 DateTo＝前一天的官網快照、matchup 用逐場 boxscorematchupsv3 加總；E-229b 同 107 場、同陣容、同種子。
- 結果：Brier T0 0.1966、T1 0.1939、T1h 0.1966；ΔBrier(T1−T0) −0.0027 [−0.0066, +0.0013]，過非劣性門檻；T1h 無差 → 改善來自 rimthree／matchup／adv。同日 30 隊淨值對實際分差相關 0.656→0.733（樣本內）；POR 21→19、MEM 16→16。
- 結論：4/5 建議採用 T1；報告 `reports/E246-t-tracking-blend/report.md`。
- 狀態：完成（2026-11-05），未稽核；2026-11-05 使用者採用 T1（R-169），線上 `BLEND_DEFAULT = TRACK_CLASSES`。
- 相關：E-229、E-229b、E-227、F-160、R-160

### E-245
- 日期：2026-11-05
- 問題：R-167 後使用者指定測中距離 `mid`：同 E-242／E-244 的 `LineupNet` 框架替換 `mid` 欄，量「中距離出手量 midA/36 ／ 命中率」比例 w 是否比現行 `mid` 更能預測下季進攻 RAPM。
- 做法：預註冊 `reports/E245-mid-lineup-tf-blend/preregistration.md`（11-05 凍結，sha256 75edae36…）；10 臂（T0、T1、W00–W10 七格、WL）× 5 種子；出手量／命中率取自逐場分區 CSV（2022-23 起；2021-22 無分區資料，混合臂退回卡片 `mid`）；命中率只收縮（k 用 beta-binomial 動差法、midA≥30、夾 [5,300]），無難度調整；M1 基底不含 `mid`；門檻同 E-244，增益一律對 T1。5090 `~/side_projects/pure_ovr/experiments/e245/`（GPU 被他人占 25–30 GB：6 路並行 OOM，改單 worker 重試；WL 的驗證與 E-179 球員值改分塊算，數值等價）。
- 結果：M1 R² T0 0.2154、T1 0.2170、W00 0.2185、W06 0.2234、W08（w*）0.2241、W10 0.2235、WL 0.2258（學出 w＝0.70±0.08）；w* 對 T1 增益 +0.0071（過 0.005），三折全正，90% CI [−0.0040, +0.0177] 跨零（c3 不過），相鄰格 +0.0064／+0.0066；測試場次 `pts100_MSE` W08 4628.8 vs T1 4628.6（差 +0.2 [−1.2, +1.6]），無改善。T1−T0 僅 +0.0016。
- 結論：3/5 不採用，`mid` 維持不動；報告 `reports/E245-mid-lineup-tf-blend/report.md`。
- 狀態：完成（2026-11-05），未稽核。
- 相關：E-242、E-244、F-165、R-167
