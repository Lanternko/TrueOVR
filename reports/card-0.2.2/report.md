# card 0.2.2 建卡報告（未發佈、未 commit）

card 0.2.2 = card 0.2.0 + E-070（foulDraw 以量為主，w075）+ E-071 P1（pressure 換成事件式 force，含勘誤 1）。
背景：已發佈的 `reports/card-0.2.1/` 標成 E-070，實際內容是 E-071 P1 疊在 card 0.2.0 上（沒有 E-070）。這版把兩個改動合在一起。
參數全部照 E-071 `run_cards.py` 的 COMMON／PART，只把 `--attrSource` 換成 E-070 w075；沒有調任何參數（L-026）。
詳細數字在 `gates.json`；生成流程：`run_cards.py` → `build_card_022.py` → `evaluate.mjs`、`npm test` → `evaluate_022.py`。

## 關卡

| 關卡 | 過／不過 | 數字 |
|---|---|---|
| c0a base 還原 E-070 | **過** | base 的 primary `ranking.csv`、`pergame-repl.csv` 與 `reports/card-0.2.0+E070-foul-volume/cards-w075/primary/` 逐位元相同（另外 pred.csv、pergame-main.csv、fitA、fitB 共 12 個檔也全相同）；base 的 card 版與 `E070/primary/ranking.csv` 逐位元相同（ovr 最大差 0.0） |
| c0b 只換 pressure | **過** | P1 對 base：除 pressure 與衍生欄（rank、ovr、predictedPer36、defenseBonus、align、pred0、pr、gRepl、ovr36）外，其他欄（name、pos、MIN 與 15 個屬性欄）全部相同，無意外欄位。foulDraw 欄與 E-071 P1 card 不同的人數 **568／582**（>0，E-070 有進去） |
| c1 `npm test` | **過** | exit 0，57 passed, 0 failed |
| c2 G4 RAPM 分半（合併版 − card 0.2.0） | **過** | ρ 差兩方向平均 **+0.0031**，90% 區間 **[−0.0061, +0.0127]**，下界 > −0.02 |
| c3 evaluate.mjs 通過數 | **過** | card 0.2.2 **18/19** ≥ card 0.2.0 **18/19**（E-070、card 0.2.1、base-switch-off 也都是 18/19） |

**全部通過。**

### c2 細節（同人群 395 人聯集；A→B 389、B→A 388；門檻 2500 回合、每半至少 5 場；bootstrap 2000 次、seed 1）
| 比較 | ρ 差（兩方向平均） | 90% 區間 | 備註 |
|---|---|---|---|
| 合併版 − card 0.2.0 | +0.0031 | [−0.0061, +0.0127] | **門檻項**，過 |
| 合併版 − E-070 primary | +0.0024 | [−0.0067, +0.0120] | 只報告（E-071 增量疊在 E-070 上） |
| 合併版 − E-071 P1（card 0.2.1 內容） | −0.0007 | [−0.0024, +0.0010] | 只報告 |
| E-070 − card 0.2.0 | +0.0007 | [−0.0009, +0.0022] | 只報告 |
| E-071 P1 − card 0.2.0 | +0.0038 | [−0.0055, +0.0135] | 與 E-071 verdict.json 的 P1-base（+0.0038）一致，確認方法複製正確 |

各方向 ρ（RAPM 另一半 × MPG）：A→B：card 0.2.0 0.6094、E-070 0.6099、合併 0.6172；B→A：0.5957、0.5966、0.5941。

## 前 20 名異動（超過 3 人要標「需 G4」；c2 本身就是 G4）

| 對照 | 進入 | 退出 | 人數 | 需 G4 |
|---|---|---|---|---|
| 已發佈 card 0.2.1 | Herbert Jones | Evan Mobley | 進 1／出 1 | 否 |
| card 0.2.0 | Stephen Curry、Tyrese Maxey | Evan Mobley、OG Anunoby | 進 2／出 2 | 否 |

card 0.2.2 前 20：1 SGA 109.8、2 Jokić 107.3、3 Dončić 102.9、4 White 101.0、5 Leonard 99.0、6 Durant 96.5、7 Wagner 96.3、8 Giannis 95.3、9 Markkanen 95.3、10 Holmgren 94.4、11 Wembanyama 93.8、12 Embiid 93.6、13 Amen Thompson 91.2、14 Curry 91.1、15 Butler 90.7、16 Mitchell 90.5、17 Cunningham 90.0、18 Murray 89.9、19 Maxey 89.7、20 Herbert Jones 88.8。
全體 OVR 最大改動：對 card 0.2.1 為 2.3，對 card 0.2.0 為 9.1。

## 只報告：2K27 每場 ρ（n=575，E-064 同一人群）
| 版本 | 每場（全量卡） | 每 36 | 半擬合平均（每場） |
|---|---|---|---|
| card 0.2.0 | 0.6952 | 0.5183 | 0.6967 |
| E-070 | 0.6989 | 0.5204 | 0.6980 |
| E-071 P1（card 0.2.1） | 0.6785 | 0.5174 | 0.6908 |
| **card 0.2.2** | **0.6810** | 0.5198 | 0.6943 |

evaluate.mjs（ρ2k／ρRAPM／ρDef）：card 0.2.0 0.6953／0.8139／0.5572；card 0.2.2 0.6810／0.8289／0.5667。2K27 ρ 比 card 0.2.0 低約 0.014（和 card 0.2.1 的下降同方向，E-070 沒有改變這點），RAPM 與防守 ρ 較高。

## 只報告：抽查表
括號為名次。PRES＝pressure 屬性（進 OVR）；presDisplay、foulDisc 為顯示欄（不進 OVR）。card 0.2.0 沒有後兩欄。

| 球員 | card 0.2.2 OVR | 0.2.2 PRES | presDisplay | foulDisc | foulDraw | card 0.2.1 OVR（PRES） | card 0.2.0 OVR（PRES） |
|---|---|---|---|---|---|---|---|
| Moussa Diabaté | 79.1（75） | 61.4 | 54.8 | 53.6 | 81.9（0.2.1：96.0） | 79.2（74）（61.4） | 84.2（42）（99.0） |
| Kyle Lowry | 53.2（508） | 62.5 | 65.9 | 75.4 | 54.0（66.8） | 53.4（499）（62.5） | 54.4（441）（99.0） |
| Luguentz Dort | 70.3（199） | 83.5 | 78.1 | 50.4 | 41.5（43.9） | 69.9（204）（83.5） | 71.3（178）（99.0） |
| Shai Gilgeous-Alexander | 109.8（1） | 81.2 | 88.4 | 88.2 | 98.5（96.4） | 109.9（1）（81.2） | 112.8（1）（85.1） |
| Dru Smith | 62.0（293） | 99.0 | 99.0 | 52.3 | 65.9（74.9） | 61.7（296）（99.0） | 61.4（291）（94.0） |
| Ausar Thompson | 82.4（53） | 99.0 | 99.0 | 46.1 | 77.4（84.2） | 82.2（56）（99.0） | 82.0（58）（93.8） |

E-070 加進來之後 foulDraw 改以量為主（多數人下調，例如 Diabaté 96.0→81.9；SGA 96.4→98.5 上調），對 OVR 的影響很小（抽查人物 OVR 變動 ≤ 0.4 vs card 0.2.1）。

## 輸出
- `ranking.csv`：582 人，P1 card 的欄位 + `foulDisc`、`presDisplay`（依姓名取自 `E071/force-2025-26.csv`）；對不到的人：**無**（兩欄皆 582／582 有值）。
- `summary.json`：version "card 0.2.2"、baseVersion "card 0.2.0"、變更、rRepl（PR10 of pred）−1.7593、錨點（PR1 −0.7564、PR50 1.0495、PR99 4.7440）、poolSize 378、來源檔 sha256（G2）、ranking_csv_sha256。
- 其餘：`cards/{base,P1}/{primary,fitA,fitB,card}/`、`evaluation.json`（evaluate.mjs）、`gates.json`、`npm-test.log`／`npm-test.exit`。
- 沒有改動 `reports/card-0.2.1/`、`card-0.2.0/`、`card-0.2.0+E070-foul-volume/`、`card-0.2.0+E071-pressure/`，也沒有改 scripts／src／memory。
- 注意：`/reports/` 在 `.gitignore`（第 7 行），所以 `git status` 看不到 `reports/card-0.2.2/`；工作樹的既有改動（memory／scripts／src）是任務前就有的。

## 假設與限制
- 「card 0.2.0」的 fitA／fitB 預測用 E-071 的 `cards/base`（E-071 c0 已驗證與 card 0.2.0 逐位元相同）。
- c3 的 card 0.2.2 候選讀最終的 `reports/card-0.2.2/ranking.csv`（含兩個顯示欄；evaluate.mjs 只按欄名讀取，不受影響）。
- 重度運算：整條流程本機 2 秒（建卡）＋數秒（評估），沒有使用 5090。
- 這版不發佈、不 commit；採用與否由 lead／使用者裁定。
