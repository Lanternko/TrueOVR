# v55 卡片修正：把出手來源（originShare）加進卡片回歸的第 16 個屬性（C1）

接續 `reports/ovr-v55-finisher-fix-2025-26/report.md` §7.5「方向 1」：fix B 的禁區出手來源
調整只作用在**模擬**端，卡片回歸看的是 15 個聯盟共用屬性係數，看不到「這顆禁區出手是誰餵的」，
所以吃餅長人（Karlo Matković）和自創型長人（Jalen Smith）的屬性輪廓接近、一起被同一組
`help`/`long`/`pass` 重定價誤傷。方向 1 的做法：把 `s̃`（禁區被餵占比）映成卡片的第 16 個
屬性 `originShare = 1 − s̃`，讓回歸自己學會分辨兩種長人。

**結論先講：方向 1 效果非常小，驗收門檻沒有全過。** `originShare` 的回歸係數小且在
bootstrap 不確定性範圍內與 0 無法區分，加進模型後 `help`/`long`/`pass` 的係數幾乎原地不動，
Karlo 卡片名次只比 B12 多降 1 名（7→12，仍不到驗收要求的 10 名），Jalen Smith 仍被誤傷超過
容忍值（104→129，超過 15 名上限）。細節見下。

## 1. 方法

### 1.1 `originShare` 屬性怎麼算（`build-origin-attr.mjs`）

- **s̃ 來源**：直接重用 `src/source_shot_origin.js` 的 `shotOriginTables(origin, ['2025-26'])`
  （B12 用的同一支函式、同一組超參數 `pseudoAttempts=25`、`minAttempts=40`），不另外發明算法。
  已驗證 Karlo（0.8208）、Jalen Smith（0.6402）、Queta（0.8507）、Gobert（0.8497）、
  Hayes（0.8788）、Garza（0.8060）、Collins（0.6108）、Stewart（0.7251）的 `s̃` 與
  `reports/ovr-v55-finisher-fix-2025-26/report.md` 和 `preregistration.md` 點名的數字逐位對上。
- **「有量測」母體**：非補籃禁區出手 `fedA+selfA>=40` 且 `fedA>0` 且 `selfA>0`，2025-26 單季，
  與 `preregistration.md` §1.3 的 417 人定義逐字一致（`eb.players===417` 已驗證）。
- **原始值**：`originShareRaw = 1 − fedShare`（自創禁區比例）。
- **未量測球員補值（165 人，= 582 卡片球員 − 417 量測球員）**：角色條件先驗——同一張卡片位置
  （`data/season-league.json` 的 `pos`：PG/SG/SF/PF/C）裡，417 位已量測球員 `originShareRaw`
  的中位數。五個位置在 417 人裡都有覆蓋，**沒有用到全聯盟中位數退回**
  （`imputedByPositionMedian=165`、`imputedByOverallMedian=0`）。各位置中位數：
  PG 0.7238、SG 0.6179、SF 0.5130、PF 0.3695、C 0.2833（全聯盟中位數 0.5661，僅供對照，
  未被使用）。
- **百分位映射**：與 `scripts/build_season_league.js` 的 `percentile()`/`attr()` 逐行相同
  （PR1=40、PR50=70、PR99=99），`pool` 固定為 417 位已量測球員的 `originShareRaw`（不含被補值
  的 165 人，理由同其他衍生屬性如 `creation`/`pressure` 用「統計上可信子母體」當分位數基準再
  映射全部球員）。輸出：`origin-attr.json`（582 人，欄位 `fedShare`/`rimAttempts`/
  `originShareRaw`/`originShareAttr`/`imputationMethod`）。

### 1.2 卡片回歸（`calibrate_c1.py`）

直接載入 `reports/ovr-calibrated-2025-26/calibrate.py` 原始模組、monkeypatch `load()` 把
`originShareAttr`（依 `playerId` 對應）掛進每位球員的卡片字典、把 `'originShare'` 併入
`ATTRS`（15→16 個），其餘管線（CV 選模、ridge、bootstrap、位置交互項、輸出格式）完全不動
——差異只能歸因於這一個新屬性。`originShare` **沒有**加進 `INTERACT`（位置交乘項清單），只作
主效應，符合任務「加一個屬性」的範圍。

目標沿用既有的 `card/calibration-target-B12.csv`（= B1 = B12，582 人），與 B12 卡片用同一套
`α=0.5` RAPM 混合（`reports/ovr-v55-finisher-fix-2025-26/card/B12/summary.json` 證實官方 B12
就是用 `α=0.5`，故主跑比較基準定在這裡；§5 另外跑 `α=0.7` 當敏感度分析，不採用）：

```
python reports/ovr-v55-card-origin-attr-2025-26/calibrate_c1.py \
  --target reports/ovr-v55-finisher-fix-2025-26/card/calibration-target-B12.csv \
  --alpha 0.5 --league data/season-league.json \
  --out reports/ovr-v55-card-origin-attr-2025-26/card-C1
```

輸出即本目錄頂層的 `ranking.csv` / `summary.json`（`card-C1/` 內是相同內容的副本）。

## 2. 新屬性的回歸係數

| 屬性 | 標準化係數 b | 每 10 點屬性值 / 36 分鐘（per36） | bootstrap SE |
|---|---:|---:|---:|
| `originShare`（C1 新增） | **0.0514** | **0.031** | 0.079 |

SE（0.079）大於點估計（0.031），**這個屬性對卡片預測值幾乎沒有可辨識的邊際貢獻**——這是
「方向 1 效果有限」的根本原因：回歸認為 `originShare` 攜帶的資訊，大半已經被既有 15 個屬性
（尤其 `help`/`rebound`/`creation`）線性吸收掉了，留給它的獨立解釋力很小。

### `help` / `long` / `pass` 係數：加了 `originShare` 前後

比較基準用 `valuePer10AttributePoints`（每 10 點屬性值的 per-36 貢獻，與
`reports/ovr-v55-finisher-fix-2025-26/report.md` §5.5 同一張表、同一個量綱，任務點名的
「`help`(−0.142)、`long`(−0.188)、`pass`(+0.110)」就是這張表 B12 相對 v53 的 Δ）：

| 屬性 | v53（官方卡片） | B12（fix B，15 屬性） | C1（+originShare，16 屬性） | Δ(B12−v53) | Δ(C1−v53) | Δ(C1−B12) |
|---|---:|---:|---:|---:|---:|---:|
| `help` | 0.608 | 0.466 | 0.465 | −0.141 | −0.142 | **−0.001** |
| `long` | 0.632 | 0.445 | 0.445 | −0.188 | −0.187 | **0.000** |
| `pass` | 0.302 | 0.412 | 0.408 | +0.109 | +0.106 | **−0.003** |

加入 `originShare` 之後，`help`/`long`/`pass` 這三個造成誤傷的係數**幾乎原地不動**（變化在
千分位、落在 bootstrap 雜訊內）。也就是說新屬性沒有把「區分吃餅長人 vs 自創長人」的工作從
`help`/`long`/`pass` 手上接過來，這組聯盟共用係數對兩種長人仍然一視同仁地重定價。

## 3. Karlo / Jalen Smith：`s̃` 與新屬性值

| 球員 | `s̃`（fedShare） | `originShareAttr`（40–99） | 位置 | 卡片名次 v53 → B12 → C1 |
|---|---:|---:|---|---|
| Karlo Matković | 0.8208 | **41.52** | PF | 7 → 11 → **12** |
| Jalen Smith | 0.6402 | **51.21** | SF | 104 → 134 → **129** |

兩人的 `originShareAttr` 確實拉開了（41.5 vs 51.2，10 點差距，方向正確：Karlo 更吃餅、
Jalen Smith 更自創），但這個差距換算成 per-36 貢獻只有 `(51.21−41.52)/10 * 0.031 ≈ 0.030`
——相當於不到 0.1 名的名次移動量級，完全不足以抵銷 `help`/`long`/`pass` 重定價帶來的傷害
（Jalen Smith 光是 `help`+`long`+`pass` 三項淨傷害就有 −0.051−0.148−0.112≈−0.31，見 fix B
report.md §6.4 的逐項拆解）。

## 4. 驗收門檻 pass/fail 表

（`compare-c1.py` 產生，`compare-C1.json` 為完整輸出；下修/不誤傷門檻用 `delta = C1名次 − v53名次`）

| 驗收項目 | 門檻 | 實際值 | 結果 |
|---|---|---:|:---:|
| Karlo Matković 明顯下修 | 至少降 10 名 | 7→12，降 **5** 名 | **✗ 不過** |
| John Collins 明顯下修 | 方向下修 | 29→46，降 17 名 | ✓ |
| Isaiah Stewart 明顯下修 | 方向下修 | 32→61，降 29 名 | ✓ |
| Luka Garza 明顯下修 | 方向下修 | 33→64，降 31 名 | ✓ |
| Neemias Queta 不誤傷 | 降不超過 15 名 | 51→51，降 0 名 | ✓ |
| Rudy Gobert 不誤傷 | 降不超過 15 名 | 68→76，降 8 名 | ✓ |
| Jalen Smith 不誤傷 | 降不超過 15 名 | 104→129，降 **25** 名 | **✗ 不過** |
| 整體 ρ vs 多季 RAPM，C1 ≥ B12 | ≥ | C1=0.5311 vs B12=0.5297 | ✓（+0.0014） |
| 整體 ρ vs 2K27，C1 ≥ B12 | ≥ | C1=0.4805 vs B12=0.4803 | ✓（+0.0002） |
| 吃餅長人原型中位數下修 | 中位 Δ>0 | B12 中位 +22、C1 中位 **+20.5** | ✓（仍下修，但比 B12 弱） |
| 持球創造原型不惡化 | C1 中位 ≥ B12 中位（不更負） | B12 中位 −6、C1 中位 −6 | ✓（持平） |

**8 項通過、2 項不過**（Karlo 降幅不足、Jalen Smith 仍超容忍）。整體一致度（ρ vs RAPM/2K27）
確實比 B12 略好，原型層方向也對，但兩個最關鍵的個案門檻（Karlo 至少降 10 名、Jalen Smith 不
超降 15 名）都沒有達成——與 §2 的係數分析一致：新屬性的邊際貢獻太小，無法真正把兩人分開。

### 分鐘桶明細（ρ，`compare-C1.json` 完整版）

| 對照 | `<800` | `800-1300` | `1300+` | `all` |
|---|---:|---:|---:|---:|
| vs 2K27：B12 | −0.0173 | 0.4683 | 0.6920 | 0.4803 |
| vs 2K27：C1 | −0.0167 | 0.4695 | 0.6923 | 0.4805 |
| vs 多季 RAPM：B12 | 0.2595 | 0.5576 | 0.5398 | 0.5297 |
| vs 多季 RAPM：C1 | 0.2551 | 0.5581 | 0.5433 | 0.5311 |
| vs 單季 RAPM：B12 | 0.3247 | 0.4380 | 0.4884 | 0.5019 |
| vs 單季 RAPM：C1 | 0.3282 | 0.4369 | 0.4908 | 0.5033 |

分桶結果同樣是「整體略好、`<800` 低出手桶反而小幅變差（多季 RAPM −0.0044）」，量級都在
0.001–0.004，不構成實質差異。

## 5. α 敏感度（報告用，不採用）

官方 B12／本任務主跑都用 `α=0.5`。時間允許下額外跑 `α=0.7`（更偏向 RAPM 目標）供參考，
**不建議採用**，僅展示趨勢：

```
python reports/ovr-v55-card-origin-attr-2025-26/calibrate_c1.py \
  --target reports/ovr-v55-finisher-fix-2025-26/card/calibration-target-B12.csv \
  --alpha 0.7 --league data/season-league.json \
  --out reports/ovr-v55-card-origin-attr-2025-26/card-C1-alpha07
```

| 球員 | v53 | C1（α=0.5） | C1（α=0.7） |
|---|---:|---:|---:|
| Karlo Matković | 7 | 12 | 16（降 9 名，仍未達 10 名門檻） |
| John Collins | 29 | 46 | 50 |
| Isaiah Stewart | 32 | 61 | 98 |
| Luka Garza | 33 | 64 | 123 |
| Neemias Queta | 51 | 51 | 58 |
| Rudy Gobert | 68 | 76 | 70 |
| Jalen Smith | 104 | 129 | **169**（降 65 名，誤傷更嚴重） |

`α` 調高讓 Karlo 更接近門檻（降 9 名），但代價是 Jalen Smith 誤傷從 25 名惡化到 65 名，
而且其他下修對象（Stewart、Garza）也被拉得比 B12 更誇張，整體方向是「用更大的 RAPM 權重
掩蓋屬性模型分不清兩種長人的問題」而不是解決它，不建議當成修正手段。

## 6. 方向 1 是否應該成為新預設？

**不建議。** 理由：

1. 兩個最具體的個案驗收門檻（Karlo 降 10 名、Jalen Smith 不超降 15 名）都沒通過，而這兩個
   門檻正是本任務要解的核心問題。
2. `originShare` 的回歸係數統計上與 0 無法區分（SE 0.079 > 點估計 0.031），加入後對
   `help`/`long`/`pass` 幾乎零影響——不是「調整方向對但力度不夠」，而是回歸選擇幾乎不用這個
   新資訊，因為它與既有 15 個屬性（尤其 `rebound`/`creation`/`help`）高度共線，線性模型把
   `originShare` 能提供的獨立訊息判定為很小。
3. 整體一致度指標（ρ vs 2K27/RAPM）雖然 C1 ≥ B12，但差距（+0.0002 ~ +0.0014）在雜訊量級內，
   不構成有意義的整體提升；真正需要解決的是**個案**分離度，而這正是第 1 點說明失敗的地方。

`report.md` §7.5 原本列了三個方向；本任務執行的方向 1（把 `s̃` 當作卡片回歸的線性主效應輸入）
目前看來不足以解決問題。若要延續這個思路，比較有希望的後續（超出本任務範圍，留給後續任務）：
把 `originShare` 做成 `help`/`long` 的交乘項而非獨立主效應（讓回歸能學到「協防/中距離屬性的
價值本身要看這顆屬性是不是靠餵出來的」），或者乾脆放棄全聯盟共用係數的線性假設，改走
§7.5 其他兩個方向。

## 7. 產出檔案

- `build-origin-attr.mjs`：算 `originShare`（s̃→屬性）的腳本，輸出 `origin-attr.json`。
- `calibrate_c1.py`：16 屬性卡片回歸腳本（monkeypatch `reports/ovr-calibrated-2025-26/calibrate.py`）。
- `compare-c1.py`：C1 vs v53/v54/B12 的四向比較與驗收門檻腳本，輸出 `compare-C1.json`。
- `origin-attr.json`：582 位卡片球員的 `originShare`（含量測/補值標記與方法說明）。
- `card-C1/`、`card-C1-alpha07/`：`calibrate_c1.py` 的完整輸出（`ranking.csv` + `summary.json`）。
- 本目錄頂層 `ranking.csv` / `summary.json`：`card-C1/`（α=0.5，主跑）的副本，供任務要求的
  頂層產出位置。
- `compare-C1.json`：§4 驗收表、§4 分鐘桶明細、§5 原型層 Δrank 的完整機器可讀版本。

## 8. 未修改項（依任務限制）

未動 `runs/`、`data/season-league.json`、`reports/.../v53`、`v54`、`v55-bench-prior`、
`v55-finisher-fix` 下任何既有輸出；未動官方卡片或 `reports/status/status_snapshot.py`；
未 stage `reports/player-impact-v53/calibrate-spread.mjs`（既有未提交改動，與本任務無關）。
