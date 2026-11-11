# 總評

**3/5（不建議採用；本探索只作對照，不改 E-227 判定）**

核心結論：把 stamina（＝場均分鐘百分位）從 R2-stats 拿掉，**沒有讓防守型外線變好，反而讓他們名次更低**；測試集淨值 MSE 比 R2-stats 差 6.0（90% CI 2.3～9.9），拿不到判定 1（−11.7，沒過 −15.4 的門檻）。分鐘資訊帶的訊號是真的有用，不是只在偏袒高分鐘球員。

> 事後探索：測試集已被 E-227 讀過，這份不是盲測、不是新證據，不改 E-227 任何判定；超參數沿用 R2-stats 選定組（lr 0.001、wd 0.1），未重調、同 5 個 seed。

**關鍵數據與例子**

| 測試集淨值 MSE（越低越好） | B0 | R2-abil | R2-stats | R2-stats-nost |
|---|---|---|---|---|
| MSE | 10176.7 | 10077.2 | 10059.6 | 10065.6 |

- nost 對 R2-abil：−11.7（CI −19.4～−3.9），仍比能力版好，但**沒達判定 1 的 −15.4 門檻**（R2-stats 是 −17.6，有過）。判定 2 三個守門指標（ptsSide、tovLL、orbLL）全部維持沒變差。
- nost 對 R2-stats：+6.0（CI 2.3～9.9），即拿掉 stamina 失去約三分之一的「統計欄位帶來的進步」。
- 個人價值名次（276 人，有卡 OVR 母體）：防守型外線沒被救回，反而更低：

| 球員 | R2-abil | R2-stats | R2-stats-nost |
|---|---|---|---|
| Draymond Green | 75 | 197 | 242 |
| Herbert Jones | 224 | 210 | 243 |
| Dean Wade | 216 | 168 | 176 |
| Tari Eason | 229 | 182 | 188 |

- 對 R2-stats 排名 Spearman 0.974，大結構幾乎一樣。升降最大：升（nost 較好）Marvin Bagley III 117→70、Jordan Miller 173→130、Simone Fontecchio 201→161、Daniss Jenkins 227→187、Brandon Williams 228→191、Corey Kispert 221→184、Brice Sensabaugh 223→186、Malik Monk 229→193（多為低分鐘球員）；降 Toumani Camara 113→175、Jabari Smith Jr. 165→221、Onyeka Okongwu 150→202、Kris Dunn 121→166、Dyson Daniels 77→122、Draymond Green 197→242、Marcus Smart 65→108、Jaden McDaniels 94→136（多為防守型）。
- 與外部指標（Spearman，nost / R2-stats）：卡 OVR 0.776 / 0.802、BPM 0.825 / 0.807、RAPM 進攻 0.656 / 0.626、RAPM 防守 0.351 / 0.402、2K26 0.493 / 0.528、薪水 0.49 / 0.49。進攻類（BPM、RAPM 進攻）略升，防守類（RAPM 防守、卡）下降，與上面防守型球員名次下滑一致。
- TOP20（nost，名字與 pid 取自資料檔）：1 Giannis Antetokounmpo(203507)、2 Victor Wembanyama(1641705)、3 Kawhi Leonard(202695)、4 Shai Gilgeous-Alexander(1628983)、5 Luka Dončić(1629029)、6 Nikola Jokić(203999)、7 Jimmy Butler III(202710)、8 Donovan Mitchell(1628378)、9 Stephen Curry(201939)、10 Anthony Edwards(1630162)、11 Jalen Duren(1631105)、12 Jarrett Allen(1628386)、13 Isaiah Hartenstein(1628392)、14 Kevin Durant(201142)、15 Scottie Barnes(1630567)、16 Day'Ron Sharpe(1630549)、17 Tyrese Maxey(1630178)、18 Cade Cunningham(1630595)、19 Karl-Anthony Towns(1626157)、20 Chet Holmgren(1631096)。

**要你決定的事**

- 建議：stamina 欄位保留，不做 nost 版本；把「stamina 偏袒」的疑慮結案，改用 F-156 記錄「stamina 實為分鐘百分位，拿掉它會讓防守型外線更差」。
- 若仍擔心高分鐘球員被獎勵，要做的是另一個、預先註冊的設計（例如分鐘當輸入但價值評估固定分鐘），不是從這個事後結果挑。要不要開，由你決定；我不建議現在開。

---

## 附錄（工程細節）
- 臂定義：R2-stats 去掉輸入欄 stamina 與其 mask（ATTRS index 11，剩 40 特徵、80 欄輸入），其餘（架構、超參數、5 seed、訓練/驗證切分、早停）完全沿用。
- 訓練在 5090 的 CPU 跑（`~/side_projects/pure_ovr/experiments/e227/explore-nostamina/`）：GPU 被他人佔滿（約 31 / 32 GB），重試 29 次 CUDA OOM 後改 CPU（CUDA_VISIBLE_DEVICES 清空）。CPU 與 GPU 數值有細微差：再現檢查 R2-stats seed 0 在 CPU valLoss 2.00621（bestEpoch 19），GPU 凍結值 2.00596（bestEpoch 19），一致。nost 五個 seed valLoss：2.00612、2.00616、2.00687、2.00626、2.00617。
- 評估：`ns_eval.py` 重用 `e227_eval` 的 metrics／draws_for／paired（B=2000、seed 20261103）；B0、R2-abil、R2-stats 的 MSE 與凍結 test-results.json 逐位相同（10176.70、10077.24、10059.61）。判定門檻取 R2-stats 的（mde-noise.json）：MDE 15.36；守門 ptsSide 0.0005、tovLL 0.00024、orbLL 0.00066。nost 對 R2-abil 守門點估計 −0.00050、−0.00039、−0.00115（全部不超過門檻）。
- 價值：`ns_value.py`（4000 抽樣、RandomState(225)、5 seed 平均，與 e227_value 同）在 5090 CPU 跑；報告 `ns_value_report.py` 是 e227_value_report 的複本，只寫入本目錄。
- 置換重要性（nost 臂，整欄打亂）最大：oppFGpct +11.3、long +11.1、stl36 +11.0、rebound +8.9、oreb36 +7.7、dreb36 +6.6。
- 凍結檔未動；memory/ 未動；未 commit／push。`npm test`：1 個既有失敗 `test/games_view_gate.py::test_ot_labels`（與本工作無關，E-227 報告已記載），其餘 22 個通過。
- 雜湊（sha256 前 16 碼）：ns_common 903faf27、ns_eval 54134d90、ns_train b74c842d、ns_value cadf6feb、ns_value_report 5dba602d、value-raw-nost 8ad63c1a、nost-test-results c6747bdd；權重 0:7f0f2a7e、1:ec654a12、2:d6e0eb50、3:300ed894、4:ef89ff11。
