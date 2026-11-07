# E-089 報告：卡片分鐘權重改成飽和曲線（card 0.2.4+E089）

- 日期：2026-10-29。執行：App 原地（使用者「你自己原地做」）。預註冊：`preregistration.md`，sha256 0fa1b15c0ce11096993b224851456abdb77eb17417ecaa55dd74257207a12fbe（凍結後才跑）。
- 改動：g = (pred − r) × W(mpg)，W(m) = (1 − e^(−m/15)) / (1 − e^(−36/15))（R-047）。其他全照 card 0.2.4。
- 判定：**通過**（預註冊 §4 六條全過）。下一步照預註冊：role-audit 獨立重算 → 使用者 G5；版號由使用者定（R-019）。
- 輸出 sha256：`ranking.csv` 73b1d635…050a、`results.json` 7e36f0d6…d371、`evaluation.json` a5f731fe…f262、`e089.py` 7907bfda…0f9。

## 1. 判定（§4）

| # | 條件 | 結果 | 過 |
|---|---|---|---|
| (c0) | `linear` 重現 card 0.2.4 | sha256 相同 af37ce25…7203，最大差 0 | ✓ |
| (c1) | `npm test` | 57 passed、0 failed；timed game 60 場過（`npm-test.log`） | ✓ |
| (u) | W(0)=0、W(36)=1、W(5)=0.31175、W(20)=0.80987 | 全對 | ✓ |
| (m1) | Δρ_{N_W} 下界 > −0.02 | **+0.0096** [+0.0020, +0.0176]（0.4952 vs 0.4856） | ✓ |
| (m2) | Δρ_{N_lin} 下界 > −0.05 | +0.0087 [+0.0011, +0.0168]（0.4934 vs 0.4847） | ✓ |
| (m3) | Δρ_{Q_W} 下界 > −0.05 | +0.0066 [−0.0005, +0.0141]（0.5925 vs 0.5858） | ✓ |

- 兩方向一致：N_W 的 AB +0.0095、BA +0.0096；Q_W 的 AB +0.0023、BA +0.0110。
- 合理性檢查：基準的 ρ_{N_lin}、ρ_{Q_lin} 和 E-084 `season_eval` 的候選值相同（同程式、同抽樣）。
- 人群：master 395 人；AB 389、BA 388 人，全部有 rapm1。bootstrap 2000 次，seed 1。
- 預期外的一點：連對分鐘線性的量尺（N_lin）也小幅變好，區間不含 0。原本預期它會吃虧（預註冊 §0）。

## 2. 只報告（§5）

### 2.1 Δρ_{Q_lin}

+0.0051 [−0.0022, +0.0130]（0.5936 vs 0.5885）。

### 2.2 evaluate 19 閘（R-042，只報告）

| | card 0.2.4 | E089 |
|---|---|---|
| 通過 | 16/19 | **18/19** |
| 沒過 | carusoGate、big14of16、allFourStayTop10 | allFourStayTop10 |
| ρ 2K27 | 0.7479 | 0.7383 |
| ρ 四季 RAPM | 0.7460 | 0.7790 |
| ρ 防守 | 0.4877 | 0.5377 |
| 側翼後衛 14 人 | 12/14 | 14/14 |
| 長人 16 人 | 13/16 | 15/16 |

- carusoGate：Caruso 103 → 39 名（參考 94）。
- big14of16：Wembanyama 6 → 4、Embiid 18 → 13 都轉過；剩 Anthony Davis 46（參考 32）。
- allFourStayTop10 兩版都沒過：前十的長人是 Jokić、Wembanyama、Holmgren、Markkanen（Markkanen 2K27 第 38、RAPM 第 11）。
- ρ 2K27 降 0.010，四季 RAPM 升 0.033。

### 2.3 指名球員

| 球員 | mpg | card 0.2.4 | E089 |
|---|---|---|---|
| Alex Caruso | 17.90 | 78.9（第 103） | **85.9（第 39）** |
| Dyson Daniels | 33.15 | 92.4（第 17） | 90.8（第 18） |

### 2.4 前 20 名

| # | 球員 | mpg | OVR | card 0.2.4 |
|---|---|---|---|---|
| 1 | Shai Gilgeous-Alexander | 33.2 | 110.3 | 1（110.0） |
| 2 | Nikola Jokić | 34.8 | 102.6 | 3（104.7） |
| 3 | Luka Dončić | 35.8 | 102.1 | 2（105.1） |
| 4 | Victor Wembanyama | 29.2 | 101.2 | 6（98.0） |
| 5 | Franz Wagner | 30.0 | 99.0 | 8（96.9） |
| 6 | Chet Holmgren | 29.0 | 97.6 | 11（94.9） |
| 7 | Derrick White | 34.1 | 97.2 | 5（99.0） |
| 8 | Kawhi Leonard | 32.1 | 96.7 | 9（96.8） |
| 9 | Lauri Markkanen | 34.4 | 95.7 | 7（97.8） |
| 10 | Amen Thompson | 37.4 | 95.2 | 4（99.9） |
| 11 | Giannis Antetokounmpo | 28.9 | 95.2 | 16（92.9） |
| 12 | Herbert Jones | 28.4 | 91.9 | 26（89.8） |
| 13 | Joel Embiid | 31.6 | 91.6 | 18（92.0） |
| 14 | Kevin Durant | 36.4 | 91.6 | 10（95.6） |
| 15 | Donovan Mitchell | 33.5 | 91.5 | 14（93.3） |
| 16 | Kon Knueppel | 31.5 | 91.1 | 19（91.4） |
| 17 | Cade Cunningham | 33.9 | 90.9 | 15（93.0） |
| 18 | Dyson Daniels | 33.2 | 90.8 | 17（92.4） |
| 19 | Jamal Murray | 35.4 | 90.3 | 13（93.6） |
| 20 | Ryan Rollins | 32.1 | 90.3 | 21（91.2） |

### 2.5 OVR 變動最大

- 上升前 10：Caruso +7.0（17.9 分）、Dean Wade +4.9（22.3）、Dylan Harper +4.4（22.6）、Paul Reed +4.2（11.1）、Brandon Clarke +4.1（10.2，MIN 20）、Clint Capela +4.1（11.4）、Josh Minott +4.0（12.1）、Aaron Holiday +3.8（9.8）、Goga Bitadze +3.7（12.5）、Jonathan Isaac +3.7（8.7）。
- 下降前 10：Toby Okani −5.2（36.2 分，MIN 217）、Tyrese Maxey −5.2（38.0）、Amen Thompson −4.7（37.4）、Kevin Durant −4.0（36.4）、Paolo Banchero −4.0（34.8）、James Harden −3.8（34.8）、Trey Murphy III −3.8（35.5）、Jalen Johnson −3.7（35.2）、Jabari Smith Jr. −3.6（35.1）、Andersson Garcia −3.5（33.8，MIN 169）。
- 完整 20+20 在 `results.json` 的 `report_only.largest_up20`／`largest_down20`。
- 方向和預期相同：低到中分鐘、效率高的上升；吃滿分鐘的下降。
- 小樣本的人兩邊都有：Clarke 20 分鐘、Okani 217、Garcia 169。pred 本身不穩，這次沒處理。

### 2.6 mpg 分組 OVR 中位數

| mpg | 人數 | card 0.2.4 | E089 |
|---|---|---|---|
| <10 | 187 | 51.8 | 52.5 |
| 10–15 | 72 | 57.6 | 59.5 |
| 15–20 | 70 | 63.3 | 64.6 |
| 20–25 | 70 | 70.0 | 69.4 |
| 25–30 | 96 | 76.9 | 76.1 |
| ≥30 | 87 | 85.3 | 83.6 |

- 分鐘的斜率變緩，但仍是單調遞增。
- mpg < 10 的人進前 150：兩版都是 0 人。

### 2.7 MIN ≥ 1000（279 人）

| | card 0.2.4 | E089 |
|---|---|---|
| ρ(mpg, OVR) | 0.749 | 0.657 |
| ρ(pred, OVR) | 0.950 | 0.987 |

OVR 更貼近每分鐘能力 pred，受分鐘的影響較小。這是 R-043 要的方向。

### 2.8 替補水準與錨點

| | card 0.2.4 | E089 |
|---|---|---|
| r（PR10） | −1.2724 | −1.2724（不變，r 由 pred 決定） |
| PR1 | −0.5415 | −0.8153 |
| PR50 | 0.8849 | 1.2506 |
| PR99 | 3.1778 | 3.4429 |

## 3. 唯讀與流程

- 唯讀目錄（§6 列的七個）合併 sha256 跑前跑後相同：867054e7…0295（`work/ro_before.txt`、`work/ro_after.txt`）。
- 沒改 `src/`、memory/（報告外）、live/、gh-pages；沒部署、沒 commit。
- 子程序（npm test、node evaluate.mjs）帶 `CREATE_NO_WINDOW`（`run_gates.py`）。
- 跑後修了一處只報告的程式錯：`read_gates()` 把閘門值當 dict 讀，`failed` 列表是空的。改成照 `hardKeys` 列出後重跑（`run3.log`）。判定和量尺數字不受影響；`diff-e084.txt` 已更新。

## 4. 留給 audit 與 G5

- audit：從 `e089.py` 獨立重算 m1–m3 與 c0。核對預註冊 sha 先於結果；核對 W 只換了兩處（`diff-e084.txt`）。
- G5（使用者抽查）：Caruso 39 名、前 20 的換位（Amen Thompson 4 → 10、Durant 10 → 14、Holmgren 11 → 6、Herbert Jones 26 → 12），以及 Maxey 12 → 26。
- 沒處理：小樣本球員的 pred 不穩（Okani、Garcia、Clarke）；這是另一個問題，不在 E-089 範圍。
