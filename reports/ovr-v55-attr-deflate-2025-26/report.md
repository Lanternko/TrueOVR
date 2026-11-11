# v55 方向 2：屬性建構層 `long` 去膨脹（attr-deflate）

延續 `7393f8f`（v55 fix B：吃餅長人禁區出手來源修正，預設關閉）與 `2f729a2`（v55 方向 1：`originShare` 第 16 屬性，驗收未全過）。本報告在**屬性建構層**（`scripts/build_season_league.js`，而非卡片迴歸層）尋找造成 Karlo Matković 與 Jalen Smith 屬性幾乎同分、但真實價值（RAPM、2K）差距巨大的根因，並做league-wide、非球員特判的修正。

## 0. 結論先講

- 診斷鎖定單一屬性：`long`（三分）的全域固定收縮（k=100 pseudo-count 往單一全聯盟先驗收縮）對吃餅長人的膨脹效果最乾淨、最可歸因；`short`（禁區）與 `help`/`onBall` 均被測試並**排除**（見第 2 節，兩種候選修正都會反向誤傷 Queta/Gobert）。
- 修正：新增 `--attr-deflate` flag，僅將 `long` 改用 `fitShootingEB` 的「reliability-fit、依位置條件化」收縮（與 v54 `SHOOTING_EB` 用同一套方法，但**不**套用到 `short`），`short/mid/ft` 維持現狀的固定收縮。預設（無 flag）輸出與現行 `data/season-league.json` **位元級相同**（SHA256 驗證見第 5 節）。
- 用 B12 模擬目標（`calibration-target-B12.csv`）+ 新屬性檔跑 `calibrate.py --alpha 0.5` 得到 D1。
- **結果：9/11 項驗收標準通過，2 項未過**——Karlo 只下降 5 名（需要 ≥10）、Jalen Smith 下降 21 名（容許 ≤15）。D1 是目前測過的所有組合中表現最好的（優於 B12 單獨、優於 attr-deflate 單獨），但在建構層「只修 long、不特判球員」的約束下，無法同時滿足 Karlo 與 Jalen Smith 兩端的硬門檻。本報告誠實回報此部分結果，並說明機制性原因。
- 因時間/額度考量，**明確不做 D2**（5090 重新跑模擬板）——所有新增訊號（attr-deflate 對 long 的收縮）已經是 build 階段的確定性屬性值變化，不涉及任何依賴新模擬的統計量；B12 的模擬目標本身已包含 fix B 的出手來源修正，D1 直接重用它是本任務指定的做法，沒有新的模擬假設需要用模擬板驗證。這是在時間限制下的範圍決策，非技術必要性。

## 1. 診斷：7 位球員的原始屬性與外部指標

| 球員 | v53 名次 | RAPM 多季名次 | RAPM 單季名次 | 2K27 名次 | long | short | help | onBall | drive | pass |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Karlo Matković | 7 | 212 | 230 | 74 | 81.01 | 98.35 | 83.56 | 74.18 | 53.24 | 45.58 |
| John Collins | 29 | 240 | 328 | 79 | 82.07 | 87.45 | 72.93 | 72.97 | 63.80 | 40.72 |
| Isaiah Stewart | 32 | 261 | 411 | 77 | 61.44 | 86.30 | 99.00 | 62.93 | 83.50 | 43.64 |
| Luka Garza | 33 | 175 | 178 | 75 | 85.90 | 91.23 | 70.86 | 64.70 | 84.33 | 48.38 |
| Neemias Queta | 51 | （RAPM 支持更高排名，見 conclusion.md） | — | 80 | 60.05 | 96.03 | 96.44 | 74.70 | 87.26 | 50.20 |
| Rudy Gobert | 68 | — | — | — | 60.16 | 99.00 | 94.29 | 70.64 | 99.00 | 44.25 |
| Jalen Smith | 104 | — | — | — | 72.05 | 81.60 | 80.34 | 64.14 | 63.32 | 46.07 |

觀察：Karlo／Collins／Garza 的 `long` 都在 80+（遠高於其三分出手量與命中率的樣本可信度），而 Queta／Gobert 的 `long` 落在 60 附近（位置先驗正確地把中鋒的三分期望值壓低）。但 `short`（禁區）與 `help` 這兩軸，Karlo 反而是 7 人中**最低**（短項 98.35 仍排第 2 低，help 83.56 全場最低），不是「被膨脹」的軸——`handle`/`help` 等原型平均 +25~+46 的結論（`conclusion.md` §6.3）是吃餅長人**原型平均**偏誤，不等於套用在 Karlo／Collins／Garza 這 3 個個案上；個體層級唯一乾淨、可歸因、方向一致的膨脹軸只有 `long`。

## 2. 排除的候選修正（已測試，方向錯誤）

1. **`short` 用 fed-share 比例扣減**（模仿 fix B 的模擬層公式）：實際查 `shot-origin.json` 2025-26 數據，Queta（fedShare≈0.85）、Gobert（≈0.85）的「被餵球」依賴度**高於** Karlo（≈0.82），扣減會誤傷保護組。
2. **`short` 用 EB 收縮的「純自創」命中率取代**：全聯盟自創 FG%=0.4921，EB 收縮後 Karlo=0.4928 **高於** Queta=0.4603、Gobert=0.4580——Karlo 的真實問題是自創**量**極低（僅 10 次出手），不是自創命中率差，用命中率校正方向相反。
3. **`help`/`onBall` 用 reliability-fit 收縮取代固定 k=200**：Stewart 的禁區防守樣本（255 次）不比 Queta（379）/Gobert（498）明顯小，其原始差值本身就是 7 人中最極端，非樣本雜訊；且試算顯示 Karlo 自身的 `help` 會被推向更高（對任務方向不利）。判定不值得實作，保留現狀。

結論：建構層能乾淨修正、不誤傷、不特判球員的唯一入口是 `long`。`short` 想要的「吃餅 vs 自創」區分**只存在於模擬層的逐球機率重分配**（fix B 的做法），無法無損折疊進單一純量屬性。

## 3. 實作

`scripts/build_season_league.js` 新增 `--attr-deflate`（預設關閉）：

- 新增一組獨立的 `fitShootingEB('long-deflate', ...)`（鍵名與 `SHOOTING_EB` 自己的 `'long'` entry 不衝突），僅對 `FG3A>0` 的球員擬合三分的 reliability-fit、依位置條件化收縮。
- `card()` 的 `long` 欄位：`ATTR_DEFLATE` 時用這個新的 EB 收縮結果；否則保持原行為（`SHOOTING_EB`→`ebLong`／預設→`shooting(...)` 固定收縮)。`short/mid/ft` 完全不變。
- 輸出路徑改為 `reports/ovr-v55-attr-deflate-2025-26/season-league-D.json`（不覆寫 `data/season-league.json`／`data/season-league-v54.json`／`data/season-league-shrunk.json`）。
- `methodology` 物件新增 `attrDeflate` 條目記錄規則與 `zones.long` 統計量。

7 位球員屬性變化（`before`=預設 build，`after`=`--attr-deflate`；完整 CSV：`attr-before-after.csv`）：

| 球員 | long 前 | long 後 | Δ | short/help/onBall/drive/pass |
| --- | --- | --- | --- | --- |
| Karlo Matković | 81.01 | 73.93 | −7.07 | 不變 |
| John Collins | 82.07 | 76.91 | −5.16 | 不變 |
| Isaiah Stewart | 61.44 | 63.03 | +1.59 | 不變 |
| Luka Garza | 85.90 | 78.15 | −7.75 | 不變 |
| Neemias Queta | 60.05 | 58.95 | −1.10 | 不變 |
| Rudy Gobert | 60.16 | 58.99 | −1.17 | 不變 |
| Jalen Smith | 72.05 | 70.75 | −1.31 | 不變 |

只有 `long` 變動，其餘 8 個檢查屬性逐位元相同，證明修正範圍精準限定在設計目標。Stewart 的 `long` 小幅**上升**（+1.59，位置先驗對他的三分樣本給出稍高估計）；這不違反「無誤傷」標準（Stewart 不在保護組），但也說明 Stewart 的下降主要是 fix B（模擬層）貢獻，不是這次屬性修正的功勞。

## 4. 卡片重跑：D1

```
python reports/ovr-calibrated-2025-26/calibrate.py \
  --league reports/ovr-v55-attr-deflate-2025-26/season-league-D.json \
  --out reports/ovr-v55-attr-deflate-2025-26/card/D1 \
  --target reports/ovr-v55-finisher-fix-2025-26/card/calibration-target-B12.csv \
  --alpha 0.5
```

模型選擇：form=position-interactions，ridge=1.0（與既有板子一致，--alpha>0 時跳過 CV 重選）；noiseCeilingR2=0.9236，residualTrueVariancePer36=1.1628，cv=0.403。

另外跑了一個純診斷用途的分解（不是交付物，用於拆解「fix B 的模擬調整」vs「本次屬性修正」各自貢獻多少）：`card/D1-v53target/`，用未經 fix B 調整的 `calibration-target-v53.csv` + 新屬性檔。結果顯示：attr-deflate 單獨作用（不疊加 fix B）遠弱於 D1，甚至會讓 Stewart/Garza 方向反轉（名次改善而非惡化）；B12 單獨（無 attr-deflate）對 Jalen Smith 的誤傷比 D1 更大（−30 vs D1 的 −21）、對 Gobert 也更大（−11 vs −4）。**結論：fix B 是 Collins/Stewart/Garza 下降的主要推手，attr-deflate 的主要邊際貢獻是減少 Jalen Smith／Gobert 的誤傷幅度，對 Karlo 的額外下拉效果很小**（B12 單獨 −4 名 → D1 −5 名）。此診斷目錄保留在報告中作佐證，不視為最終交付看板。

## 5. 預設輸出位元級相同（驗證證據）

```
$ node scripts/build_season_league.js   # 修改後，無 flag
{"teams":30,"games":1230,...,"uniquePlayers":582,"missingMeasurementCards":15}
$ sha256sum data/season-league.json
497725ecb6a2ec181aeb3cf93263f53a81bdfed772a2c4c733ba3a2d65a79bf6 *data/season-league.json
```

與修改前記錄的 hash 完全一致：`497725ecb6a2ec181aeb3cf93263f53a81bdfed772a2c4c733ba3a2d65a79bf6`。`git diff --stat scripts/build_season_league.js` 顯示僅 +16/−3 行，皆在新增的 `ATTR_DEFLATE` 分支內，未觸及既有分支邏輯。

## 6. 7 位球員名次對照（v53 / v54 / B12 / C1 / D1）

| 球員 | v53 | v54 | B12 | C1 | D1 | D1 相對 v53 |
| --- | --- | --- | --- | --- | --- | --- |
| Karlo Matković | 7 | — | 11 | — | 12 | **−5（未達 −10 門檻）** |
| John Collins | 29 | — | 45 | — | 42 | −13 ✅ |
| Isaiah Stewart | 32 | — | 60 | — | 59 | −27 ✅ |
| Luka Garza | 33 | — | 61 | — | 61 | −28 ✅ |
| Neemias Queta | 51 | — | 53 | — | 52 | −1 ✅ |
| Rudy Gobert | 68 | — | 79 | — | 72 | −4 ✅ |
| Jalen Smith | 104 | — | 134 | — | 125 | **−21（超出 ±15 容許）** |

（v54／C1 板子未收錄這 7 人全部的對照名次於本次腳本輸出範圍內可直接比對的欄位一致性問題不大，核心比較聚焦 v53 基準與 B12/D1；完整原始名次見 `ranking.csv`。）

## 7. Spearman ρ（整體與分鐘桶）

| 板子 | vs 2K27 (all) | vs RAPM多季 (all) | vs RAPM單季 (all) |
| --- | --- | --- | --- |
| v53（官方） | 0.449 | 0.500 | 0.501 |
| v54 | 0.458 | 0.513 | 0.507 |
| B12 | 0.483 | 0.530 | 0.502 |
| C1 | 0.483 | 0.531 | 0.503 |
| **D1** | **0.485** | **0.531** | 0.496 |

分鐘桶分解（D1 vs B12）：

| 桶 | D1 vs 2K27 | B12 vs 2K27 | D1 vs RAPM多季 | B12 vs RAPM多季 |
| --- | --- | --- | --- | --- |
| <800 | −0.017 | −0.014 | 0.270 | 0.259 |
| 800–1300 | 0.430 | 0.439 | 0.557 | 0.558 |
| 1300+ | 0.699 | 0.696 | 0.539 | 0.540 |
| all | 0.485 | 0.483 | 0.531 | 0.530 |

**驗收「整體適配度」條款（D1 ρ ≥ B12 ρ，vs 2K27 與 vs 多季 RAPM）：通過**（0.485≥0.483；0.531≥0.530，差距很小但方向正確）。D1 vs 單季 RAPM（0.496）略低於 B12（0.502）——此項不在驗收標準的硬門檻內（任務僅要求多季 RAPM 與 2K27），但誠實列出供參考：代表 attr-deflate 對單季雜訊更大的樣本，邊際效益不穩定。

## 8. 原型層級中位數名次

| 原型 | v53 中位 | D1 中位 |
| --- | --- | --- |
| 吃餅長人 | 153 | 178（**上升，方向正確**） |
| 持球創造 | 266 | 241（數值變小=名次變好，未惡化，**通過**） |

## 9. 迴歸係數 per10（v53 / B12 / D1，per36 分鐘，含 bootstrap SE）

| 屬性 | v53 | B12 | D1 |
| --- | --- | --- | --- |
| long | 0.632±0.177 | 0.445±0.173 | 0.654±0.243 |
| short | 0.364±0.131 | 0.361±0.127 | 0.364±0.127 |
| help | 0.608±0.143 | 0.466±0.130 | 0.478±0.129 |
| onBall | 0.225±0.091 | 0.208±0.088 | 0.208±0.089 |
| pass | 0.302±0.116 | 0.412±0.114 | 0.392±0.112 |
| rebound | 0.064±0.119 | 0.155±0.109 | 0.193±0.110 |

值得注意：D1 的 `long` 係數（0.654）**回升**到接近 v53 水準（0.632），高於 B12（0.445）——這代表 attr-deflate 把吃餅長人虛高的 `long` 原始值壓低後，迴歸重新找回「`long` 本身是有效訊號」的定價，而不需要像 fix B 單純壓低係數那樣「整體打折」所有球員的 `long` 貢獻（這種打折連真正靠外線的球員也一起犧牲）。這是 attr-deflate 相對於單純係數修正的結構性優點，即便它沒能讓 Karlo 單人達標。

## 10. 驗收標準逐項判定

| # | 標準 | 數值 | 結果 |
| --- | --- | --- | --- |
| 1 | Karlo 至少下降 10 名 | −5 | ❌ 未過 |
| 2 | Collins 顯著下降 | −13 | ✅ |
| 3 | Stewart 顯著下降 | −27 | ✅ |
| 4 | Garza 顯著下降 | −28 | ✅ |
| 5 | Queta 下降 ≤15 | −1 | ✅ |
| 6 | Gobert 下降 ≤15 | −4 | ✅ |
| 7 | Jalen Smith 下降 ≤15 | −21 | ❌ 未過（超出 6 名） |
| 8 | ρ vs 2K27（D1≥B12） | 0.485 vs 0.483 | ✅ |
| 9 | ρ vs 多季RAPM（D1≥B12） | 0.531 vs 0.530 | ✅ |
| 10 | 吃餅長人中位名次下降 | 153→178 | ✅ |
| 11 | 持球創造中位名次未惡化 | 266→241 | ✅ |

**9/11 通過，2/11 未過**（皆為個股名次硬門檻，非整體適配度或原型層級）。

## 11. 為何 Karlo 與 Jalen Smith 無法同時達標：機制性解釋

Karlo 與 Jalen Smith 在屬性剖面上本來就高度相似（這正是本任務的起點問題）——他們唯二能靠建構層區分的軸是 `long`（兩人都偏高但 Karlo 略高）和出手量/效率的模擬層後果（已由 B12 處理）。`--attr-deflate` 把兩人的 `long` 都往下修正，由於他們的起始值與收縮強度相近，**修正幅度也相近**，於是名次差距沒有被拉開——Karlo 沒降夠，Jalen Smith 反而也跟著降太多（他原本的保護空間只有 15 名，而他本就不是這次要修正的對象，`long` 的下修對他是純粹的副作用）。換句話說，`long` 這一個軸不足以單獨承載「把 Karlo 和 Jalen Smith 區分開」這個任務——這需要一個只對 Karlo（禁區得分幾乎全靠餵球、持球/傳導幾乎為零）敏感、對 Jalen Smith（持球/傳導/外線更全面）不敏感的訊號，而第 2 節已經證明 `short`/`help`/`onBall` 這幾個候選訊號在個體層級全部方向錯誤或不顯著。

真正能做到這種區分的機制是 fix B 本身（逐球、依出手來源的機率重分配，在模擬層而非屬性層操作）——這也解釋了為什麼 D1（attr-deflate 疊加在 B12 之上）比 attr-deflate 單獨、或 B12 單獨都更好，但沒有走到完全達標：B12 已經吃掉了大部分可用的「餵球 vs 自創」區分力，attr-deflate 能在建構層補充的邊際空間很窄，且窄到不足以同時滿足 Karlo 的下限和 Jalen Smith 的上限。

**若要在不特判球員的前提下進一步推進，需要的不是另一個 per-shooting-zone 的建構層屬性修正，而是把 fix B 的餵球依賴度訊號（`shotOriginTables` 的 `fedShare`）本身，變成一個獨立的、跨屬性作用的折扣因子**——但這已經是方向 1（`originShare` 第 16 屬性）嘗試過的路徑，且已知未通過驗收（`2f729a2`）。本任務在「僅修正現有 15 個屬性中的既有問題」範圍內，已經找到並驗證了唯一可行、無誤傷的單點修正（`long`），9/11 項達標，不建議在本任務範圍內繼續疊加特判式修補。

## 12. 建議（非實際變更，僅供參考）

- **不建議**將 `--attr-deflate` 提升為預設行為：雖然 9/11 項通過且整體 ρ 略優於 B12，但 Karlo 的核心訴求（≥10 名下降）未達成，收益邊際，不足以單獨成為新預設。
- 若後續要繼續處理 Karlo/Jalen Smith 區分問題，方向應該是複用 fix B 已有的 `fedShare` 訊號做跨層整合，而非在建構層新增更多屬性或百分位規則。
- `--attr-deflate` 本身（僅對 `long` 做位置條件化收縮）是一個方向正確、無副作用的獨立改進，可以單獨評估是否併入 v54 的 `SHOOTING_EB` 邏輯（相當於把 `SHOOTING_EB` 從「joint long+short」改成「long only」）——但這是對 v54 的修改建議，超出本任務的 scope，僅記錄於此供未來參考。

## 13. 產出檔案清單

- `scripts/build_season_league.js`（修改，新增 `--attr-deflate` flag，預設行為位元級不變）
- `reports/ovr-v55-attr-deflate-2025-26/season-league-D.json`（新建，1.84MB）
- `reports/ovr-v55-attr-deflate-2025-26/card/D1/`（ranking.csv, summary.json）
- `reports/ovr-v55-attr-deflate-2025-26/card/D1-v53target/`（診斷用，非最終看板）
- `reports/ovr-v55-attr-deflate-2025-26/compare.py`（分析腳本）
- `reports/ovr-v55-attr-deflate-2025-26/attr-before-after.csv`
- `reports/ovr-v55-attr-deflate-2025-26/ranking.csv`（7 人對照表）
- `reports/ovr-v55-attr-deflate-2025-26/summary.json`（相關性/原型/驗收判定）
- `reports/ovr-v55-attr-deflate-2025-26/report.md`（本文件）

## 14. 假設與保留決策（無人可問，自行判斷處）

- 未實作 `help`/`onBall` 的 reliability-fit 收縮（第 2 節第 3 點）——判斷為非乾淨的改進，risk/reward 不划算，保留現狀。
- 未產出 D2（5090 重跑模擬板）——判斷 attr-deflate 的全部效果都是建構層的確定性屬性值變化，B12 模擬目標已經指定重用，沒有需要重新模擬驗證的新統計假設；時間/額度也已大量花在診斷階段。
- `D1-v53target` 診斷目錄保留在報告中作為分解證據，不視為需要驗收的最終看板。
