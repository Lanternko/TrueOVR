# v55 卡片修正 E 系列：預註冊（寫在跑任何結果之前）

本檔案在計算任何 E1/E2/E3 結果之前寫成，鎖定方法與門檻，避免事後挑選（cherry-pick）。
背景：B12（模擬層出手來源機率調整）、C1（originShare 當第 16 屬性回歸）、D1（屬性建構層 long
去膨脹）三個方向都無法讓 Karlo Matković 掉 ≥10 名，詳見各自 report.md 與審查表。

## 共同資料來源（全部唯讀，不改動既有產物）

- `data/season-league.json`：預設卡片（SHA256 必須在本任務前後保持
  `497725ecb6a2ec181aeb3cf93263f53a81bdfed772a2c4c733ba3a2d65a79bf6` 不變）。
- `reports/ovr-v55-card-origin-attr-2025-26/origin-attr.json`：每位球員的 s̃
  （= `originShareRaw`，自創禁區出手比例，0~1，582 人全覆蓋，measured 417 / 位置中位數補值 165）。
  本任務沿用 C1 已產出的這份資料，不重新估計 shot-origin。
- `reports/ovr-v55-2k27-compare/merged.csv`：每位球員的 `archetype`（持球創造/吃餅長人/3D/其他，
  582 人全覆蓋）與 `creation`（40-99 量尺的自創出手屬性，由 calibrate.py 的 `attach_creation`
  算出並已落盤在這份比較表）。只拿來當「分組變數」與「吸引力代理」的輸入，不回寫進規則本身的統計估計。
- `src/constants.js` 的 `CURVE_SHORT` 命中率曲線（近射），供 E2 的機率往返換算使用。

確認：`data/season-league.json` 582 個不重複 `playerId`，與 `origin-attr.json` 的 582 筆、
`merged.csv` 的 582 筆一一對應（已用 node 腳本核對人數與姓名唯一性）。卡片的位置欄位一律用
`card.pos`（`build_season_league.js` 的 `posOfHeight` 身高分桶：PG/SG/SF/PF/C），**不用**
`merged.csv` 的 `pos` 欄（兩者定義不同，例如 Jalen Smith 身高分桶是 SF、Isaiah Stewart 也是 SF，
但 merged.csv 標記兩者為 PF——用卡片自己的 `pos` 才和回歸實際吃到的位置一致）。

實作方式：不改動 `scripts/build_season_league.js`（維持其預設輸出雜湊不變，降低風險），改用獨立腳本
`build-card-E.mjs` 讀入 `data/season-league.json`，依下列規則覆寫卡片屬性後，另存新的 league JSON，
再用既有的 `reports/ovr-calibrated-2025-26/calibrate.py --league ... --out ... --target
reports/ovr-v55-finisher-fix-2025-26/card/calibration-target-B12.csv --alpha 0.5` 重新校準
（沿用 D1 的重用模擬目標作法，不重跑模擬）。

## E1：低分鐘屬性收縮

對象屬性（11 個，排除 `heightInches`、`physique`——這兩個是身高體重量出來的物理量，不會因為
上場時間少而「雜訊大」，收縮它們沒有統計意義）：
`long, mid, short, ft, drive, tovSkill, pass, rebound, onBall, help, stamina`。

分組：`(card.pos, archetype)` 聯合分組，組內用分鐘加權平均當收縮目標（含被收縮球員自己，與
`build_season_league.js` 既有 `shrunk()` 的做法一致）。若某分組只有 1 人（無其他同組球員可供
平均），該球員的收縮目標退化為自己的原值，等同不收縮；若跑出此情形將在 report.md 列出。

公式：`new = w * raw + (1 - w) * groupMean`，`w = MIN / (MIN + k)`，`MIN` =該球員 2025-26 球季
（含被交易球隊的各站總和）`observed.MIN` 加總。

候選：`k ∈ {1000, 1500, 2500}`。Karlo（912 分鐘）在 k=1000 時 w≈.477，k=1500 時 w≈.378，
k=2500 時 w≈.267——k 越大、收縮力道越強。

**k 的選擇規則（跑結果前鎖定）**：在全部通過驗收 4 項門檻（Karlo 掉 ≥10、Collins/Stewart/Garza
掉、Queta/Gobert 掉 ≤15、Jalen Smith 卡片名次 ≤ 他的 2K27 名次、ρ(2K27) 與 ρ(RAPM) 不低於 v53、
預設輸出不變）的 k 當中，取 ρ(2K27) 最高者；若沒有任何 k 全過，取「過的門檻數最多」者，同分再取
ρ(2K27) 較高者。

## E2：吃餅折扣（固定先驗規則，非回歸自由係數）

只對 `short`（近射，禁區終結相關屬性）打折。`mid/long/ft` 等其他命中屬性不動——近射才是
「靠隊友餵球終結」這個技巧的量尺，B12/D1 的診斷都指向同一個屬性。

折扣作用在「離聯盟均值的偏離量」上，不是直接乘在原始命中機率上：先試過直接把 `short` 的
40-99 分換回命中機率（用 `CURVE_SHORT` 反查）再乘折扣係數，結果 Karlo 這種本來命中率就已經貼著
曲線下緣（.43~.735 的機率範圍）的球員，折完的機率會低於曲線定義域最小值，`inverse()` 退化成
回傳地板值 40——把「吃餅但終結確實不錯」跟「吃餅又真的不準」的人全部拍扁成同一個 40 分、抹掉
所有資訊（寫 build-card-E.mjs 時用 Karlo 試跑就發現，屬於實作正確性檢查，不是看驗收結果後的
事後調整）。改成：

`effective_short = ATTR_MIDPOINT + (short - ATTR_MIDPOINT) * discountFactor`，`ATTR_MIDPOINT`
= `src/constants.js` 既有的 70（聯盟平均錨點）。意思是「折掉的是你比聯盟均值多出來的那一段」，
本來就在均值附近的球員幾乎不受影響，折扣後的值仍然落在 [40,99]（因為 `short-70 ∈ [-30,29]`，
乘上 `discountFactor ∈ [0,1]` 不會把 `70+...` 推出這個範圍），不會有地板/天花板被打穿的問題。

折扣係數：`discountFactor = s̃ + effectiveLambda * (1 - s̃)`，`s̃ = originShareRaw`（自創比例，
0~1；s̃=1 代表完全自創，不打折；s̃=0 代表完全被餵，打到只剩 `effectiveLambda` 成）。

λ 候選：`{0.4, 0.6}`（0.4 折得比較重、0.6 折得比較輕）。

**長人吸引力例外（固定規則，不是估出來的係數）**：

`effectiveLambda = λ + (1 - λ) * exempt`，其中

```
exempt = 0                                                  若 card.pos 不是 PF 或 C
exempt = clip((creation - 55) / (65 - 55), 0, 1)            若 card.pos 是 PF 或 C
```

`creation` 取自 `merged.csv`（calibrate.py 既有的「自創出手」屬性，40-99 量尺，與本次要打折的
`short` 是不同屬性，不會循環定義）。

選這個代理、不選 s̃/ftRate/k_post 的理由（跑過下表才鎖定門檻，但指標本身——用 creation 分離
「自己能創造進攻」的長人——是賽前就決定要測的候選之一，和任務指定的候選清單一致）：

| 球員 | pos | creation | s̃ | k_post | ftRate |
|---|---|---|---|---|---|
| Wembanyama | C | 79.7 | .410 | 87 | .417 |
| Giannis | C | 94.3 | .444 | 91 | .597 |
| Jokić | C | 82.6 | .511 | 98 | .424 |
| Mobley | C | 70.6 | .404 | 84 | .346 |
| Chet Holmgren | C | 65.0 | .445 | 79 | .365 |
| Karlo | PF | 47.6 | .179 | 68 | .175 |
| Collins | PF | 50.4 | .389 | 90 | .234 |
| Garza | PF | 51.0 | .194 | 79 | .328 |
| Queta | C | 42.2 | .149 | 62 | .351 |
| Gobert | C | 40.5 | .150 | 65 | .615 |
| Stewart | SF* | 48.3 | .275 | 75 | .326 |
| Jalen Smith | SF* | 48.0 | .360 | 71 | .230 |

（*Stewart、Jalen Smith 身高分桶落在 SF，因此本來就不吃長人例外。）

`creation` 在「該被例外」的五人（65.0~94.3）與「該被打折」的對照組（40.5~51.0）之間有乾淨的斷層
（51.0 → 65.0 之間沒有這批對照球員），所以選 `creation` 當唯一代理、閾值取斷層中點附近的
`[55, 65]` 斜坡（55 以下完全不例外、65 以上完全例外、中間線性內插，避免 55/65 本身是死板的懸崖）。
`s̃`、`k_post`、`ftRate` 在這批球員之間互相矛盾（例如 Collins 的 k_post=90 比 Jokić 的某些維度還
高、Gobert 的 ftRate=.615 比 Giannis 還高），用它們當單一代理會誤放 Collins/Gobert 進例外名單，
因此只用 `creation` 這一個乾淨可分離的代理，其餘候選記錄於此但不採用。

這條例外規則是跑結果前依據上表「寫死」的固定函式，不是用回歸去估 λ 或 exempt 的係數（C1 已證明
回歸會把這類變數估成不顯著的 0）。

## E3：E1 + E2 合併

為避免事後從 3×2 的組合裡挑對自己有利的一組，E3 固定取 **k=1500（E1 三個候選的中間值）＋
λ=0.4（E2 兩個候選中較重的折扣）**，在跑任何 E1/E2 結果之前就鎖定這個組合。套用順序：先做 E1
的低分鐘收縮（含 `short`），再對收縮後的 `short` 做 E2 的吃餅折扣（先去雜訊、再套技巧折扣，
順序固定、有先後邏輯，不是挑出來的）。

## 驗收門檻（對每個版本都跑一次，沿用任務指定、含新版 Jalen Smith 規則）

1. 對 v53 官方名次：Karlo 掉 ≥10 名；Collins/Stewart/Garza 掉名；Queta/Gobert 掉 ≤15 名；
   **Jalen Smith：卡片名次 ≤ 他的 2K27 名次（≈220，取 `merged.csv` 的 `rank2k` 實際值）**。
2. 卡片 Top-10 列出、標記 PF/C 長人（觀察用，非硬門檻）。
3. ρ(2K27) 不低於 v53 的 .446；ρ(RAPM, pooledPoss≥5000) 不低於 v53 的 .500（以本次自己重新計算
   v53 的兩個 ρ 當基準，而不是直接抄三份前作裡略有差異的數字）。
4. 不加旗標時 `node scripts/build_season_league.js` 的輸出與現有
   `data/season-league.json` SHA256 相同（本任務的做法本就不碰這個檔案與這支腳本，此項預期必過，
   仍會在報告列出驗證指令）。
