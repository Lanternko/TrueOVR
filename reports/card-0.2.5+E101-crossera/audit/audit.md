# 總評

**4/5 大致達成 有部分退步**

E-101 的「通過」結論站得住。我用自己寫的程式從原始資料重算，主要數字全部對得上。有問題的地方都在報告的寫法，計算本身沒有錯。

稽核日期：2026-10-30。稽核者是獨立派工 session，不是產出者。repo HEAD 是 `f196d30`。預註冊 sha256 是 `44d1eb0a35f7c5b16d3da2210f7e857a90cd94fe1a3ad22b07d4545d8740f3e5`。

**這次目標**

用自己重寫的程式重算 E-101（跨季合併錨點，加上 PBP 中距離／禁區分區修正）的 c-pre、屬性錨點、c4 上限、c2N、c2Q、c3 和卡片，並看 17 條偏差有沒有實質違反預註冊，藉此判斷「通過」站不站得住。

**進步了什麼**（核對成立的）

- **預註冊沒被改過**：sha256 和交付的值相同。預註冊檔 00:31 寫入，早於所有結果檔（00:35–00:58）。
- **分區修正我從原始 PBP 重新數過**：2025-26 全聯盟中距離命中率修正後 .41695，shots.json 是 .41675，差 +0.0002；禁區 .57783 對 .57774，差 +0.0001。兩個差都和 c-pre 的值一樣。沒修正前中距離差 +0.0296，修正確實有效。Kessler 2022-23 的中距離從 63 投 50 中變成 6 投 2 中，禁區出手從 348 變 405，和產出者的歷史檔相同。
- **合併錨點對得上**：short、ft、pass 三項的 r90、r99、S 完全相同，2025-26 前三名的值差 ≤0.0002。short 是 Giannis 113.0、Toppin 112.5、Kessler 95.3；ft 是 Curry 112.8、Spencer 100.3；pass 是 Jokić 107.8、McConnell 105.8、Young 104.4。
- **c4 上限**：e101 沒有任何值 >140，>120 的只有 Giannis shortValue 129.0，和產出者說的一樣。另外三個變體我也數過，數字都對得上（見細節）。
- **c2N、c2Q 精確重現**：我自己寫的 Spearman 加 bootstrap，點估計和 90% 區間到小數第四位都相同。換 seed 7、重抽 5000 次，結論也不變：區間含 0，所以是「沒變差」。
- **c3 和測試**：我在 audit/ 重跑 evaluate，E101 是 19/19，和原輸出逐位元相同。`npm test` 57/57 通過。
- **卡片**：582 人的 OVR 和名次我全部重算，一個不差。報告寫的移動人數（動 ≥5 名 303 人、≥10 名 133 人）、前十名重疊 9 人（Amen Thompson 掉出）都屬實。
- **大個子中距離虛高修掉了**：E-096 有 13 人中距離屬性頂到 99，其中多是 Kessler、Gafford、Poeltl、Lively 這類中鋒。E-101 只剩 SGA 一人。Kessler 從 99 降到 60.9，Durant 從 92.5 升到 94.5，Curry 從 81.1 升到 87.3。
- **偏差沒有實質違反**：#3、#4、#10、#17 都能在預註冊或前一版預註冊找到原文依據，#7、#9 是合理的定義和誠實揭露的限制。這輪計算鏈和 E-097 只差路徑和變體名稱；calibrate-wing.py 和 E-096、E-097 用的是同一份檔案（sha 相同）。
- **寫入範圍乾淨**：src/、live/、test/、V61 歷史、card-0.2.5、E-090、E-096、E-097 都沒有比預註冊新的修改。稽核前後的 git status 完全相同。

**退步了什麼**（對不上或還有疑慮的）

1. **報告比較的基準混用**：退步段寫「Curry 第 24→32（88.6→86.3）、Brunson 45→58」，這是拿 E-096 當基準。但這次決定要比的是卡片 0.2.5，照那個基準應該是 Curry 23→32（89.6→86.3）、Brunson 51→58。方向一樣，退步其實比報告寫的多一點。
2. **每 10 次出手價值表用的是 fitA，不是卡片實際用的 primary**：報告的 mid .168→.102、long .426→.376、short .410→.534 和 fitA 完全一樣。卡片用的 primary 是 mid .206→.137、long .436→.382、short .389→.531。方向相同，但每項變化大約只有 1 個標準誤。所以「中距離跟正負值的關聯變弱」這個解釋證據偏弱，只能當參考。
3. **偏差紀錄寫入時間晚於卡片**：deviations.json 是 00:52 寫的，卡片是 00:51 產出的，所以「決定在看結果之前」沒辦法用時間證明。不過 build_e101.py（00:45）早於卡片、c2 和 evaluate，work/tmp 也看不出有反覆試參數的痕跡。我判斷沒有違規，只是不能完全證明。
4. **ft 的錨點只有 2 人超過 99**（Curry、Spencer），保險 S 有生效。這不是錯，只是 ft 頂端的形狀主要由保險決定。
5. **人群少一人**：我的人群有 378 人，產出者是 379。差在 Asa Newell（上場 499.908 分鐘，ranking.csv 四捨五入成 500），這是沿用前一版的慣例。對 SD_pool 的影響約 6e-6，可以忽略。
6. **另一個 session 同時在改 repo**：scripts/enrich_roster_viewer.py、scripts/fit_game_contribution.py、data/_inseason_build/*、dnp 抓取紀錄，以及 gh-pages 的 a35cc44、2bac629、93978af，都是同一時段另一個名單頁 session 改的。E-101 的腳本只寫自己的資料夾，所以不能算到 E-101 頭上。但這表示「只看時間」的寫入範圍檢查不夠，要搭配寫檔路徑一起看。
7. **提醒**：midValue／shortValue 只是報告用的數字，沒有餵進卡片 OVR（--tailSource 只覆蓋 13 個屬性）。卡片名次的變動來自其他屬性的跨季錨點和分區修正，不是這兩個值。

**直觀證據**

| 檢查 | 產出者 | 我的重算 | 對得上？ |
|---|---|---|---|
| 預註冊 sha256 | 44d1eb0a…e5 | 44d1eb0a…e5 | 是 |
| c-pre 中距離（2025-26 聯盟） | +0.0002 | +0.000196（.416950 vs .416754） | 是 |
| c-pre 禁區 | +0.0001 | +0.000094（.577830 vs .577736） | 是 |
| Kessler 2022-23 中距離 | 6 投 2 中 | 6 投 2 中（原 63 投 50 中） | 是 |
| short 前三 | 113.0 / 112.5 / 95.3 | 113.046 / 112.457 / 95.285 | 是（差 ≤0.0002） |
| ft 前二 | 112.8 / 100.3 | 112.762 / 100.284 | 是 |
| pass 前三 | 107.8 / 105.8 / 104.4 | 107.771 / 105.812 / 104.385 | 是 |
| e101 值 >140 | 0 | 0 | 是 |
| e101 值 >120 | 1（Giannis short 129.0） | 1（129.04） | 是 |
| c2N | −0.0027 [−0.0069, +0.0015] | −0.00265 [−0.00688, +0.00150] | 是 |
| c2Q | −0.0032 [−0.0067, +0.0004] | −0.00318 [−0.00671, +0.00040] | 是 |
| c3 evaluate | 19/19 | 19/19（逐位元相同） | 是 |
| npm test | 過 | 57/57，exit 0 | 是 |
| 582 人 OVR／名次 | ranking.csv | 0 人不符 | 是 |
| 動 ≥5 名／≥10 名 | 303 / 133 | 303 / 133 | 是 |
| Curry 名次（對卡片 0.2.5） | 報告寫 24→32 | 23→32（89.6→86.3） | 否（基準混用） |
| Brunson 名次（對卡片 0.2.5） | 報告寫 45→58 | 51→58 | 否（基準混用） |
| 每 10 次中距離價值 | .168→.102 | fitA 相同；primary .206→.137 | 數字對，用的版本不同 |

抽查球員（卡片 0.2.5 → E-096 → E-101，格式為名次/OVR）：

| 球員 | 0.2.5 | E-096 | E-101 |
|---|---|---|---|
| Giannis | 11/95.2 | 6/98.4 | 5/99.0 |
| Duren | 53/84.3 | 54/83.6 | 37/85.5 |
| Kessler | 58/83.9 | 50/83.9 | 51/83.6 |
| Curry | 23/89.6 | 24/88.6 | 32/86.3 |
| Brunson | 51/84.5 | 45/84.2 | 58/83.2 |
| George | 50/84.5 | 46 | 50/83.6 |
| Wiggins | 158/73.8 | 154 | 155/73.5 |
| Wallace | 74/82.2 | 71 | 75/81.5 |
| Phillips | 332/58.6 | 325 | 332/58.3 |
| Battle | 407/54.1 | 408 | 405/53.9 |

前五人是指定的，後五人是 seed 7 隨機抽的。

**要你決定的事**

1. 「通過」站得住，要不要照原決定採用 E-101？稽核只給判定，不決定採用。
2. 要不要請產出者修報告？兩處要改：Curry 和 Brunson 改成以卡片 0.2.5 為基準，每 10 次出手價值表改用 primary（或註明用的是 fitA）。
3. 要不要寫成 lesson（建議寫）：「比較基準要寫明；做寫入範圍檢查時，同時有其他 session 在動 repo 就要看寫檔路徑，不能只看修改時間」。
4. Curry 和 Brunson 的退步要不要另外追？它們不影響這次的關卡判定，但都是使用者會抽查的球員。

---

## 關卡表

| 關卡 | 判定 | 證據路徑 |
|---|---|---|
| G1 `npm test` | 過 | `audit/npm-test-rerun.log`、`audit/npm-test-rerun.exit` |
| G2 版本、資料 sha | 過 | 預註冊 sha 自算相同；calibrate-wing.py sha `1e69769f…` 和 E-096、E-097 相同 |
| G3 同人群、同 seed、同重抽法 | 過 | `audit/a5_c2.json`（人群 389/388，master 395；default_rng(1)、2000 次） |
| G4 預註冊早於結果 | 過（偏差時間點沒法判定） | 預註冊 00:31 早於結果 00:35–00:58；deviations.json 00:52 晚於卡片 00:51 |
| c-pre 分區修正 | 過 | `audit/a1_zones.py` → `a1_zones.json` |
| 錨點重算 | 過 | `audit/a2_attrs.py` → `a2_attrs.json` |
| c4 上限 | 過 | `audit/a4_c4.py` → `a4_c4.json` |
| c2N、c2Q | 過（區間含 0＝沒變差） | `audit/a5_c2.py` → `a5_c2.json` |
| c3 | 過 | `audit/evaluation-rerun.json`、`audit/evaluate-rerun.log` |
| 卡片 | 過 | `audit/a6_cards.py` → `a6_cards.json` |
| 偏差 17 條 | 過（沒有實質違反） | 見下方「偏差審查」 |
| 寫入範圍 | 過（其他改動來自另一個 session） | `audit/git-status-before.txt`、`git-status-after.txt`（相同） |
| G5 使用者抽查 | 不歸稽核 | — |

## 細節與證據

### 做法與獨立程度
- 所有數字都由 audit/ 裡我自己寫的程式算出來，沒有呼叫 work/ 的腳本取數字。
- a5_c2.py 只借用 `chain/e084.py` 組資料（讀檔、對名字）。Spearman、bootstrap 和分位數都是我自己的程式。
- evaluate-rerun.mjs 是 chain/evaluate.mjs 的副本，只改了輸出路徑。這樣做是為了不覆蓋產出者的 evaluation.json。
- 執行方式：Python 用 `python -I -B`，加上 PYTHONDONTWRITEBYTECODE=1。沒跑模擬，也沒用 5090。

### 1. c-pre（a1_zones.json）
- 規則：兩分球的 area 是 'Mid-Range'，而且 shotDistance < 8 的，改算禁區。
- 資料來源：2025-26 用 data/defense-a-source 的 manifest；之前三季用 data/defense-seventh/<s>/pbp。
- 2025-26 中距離：修正後 .416950，shots.json .416754，差 +0.000196；沒修正時差 +0.0296。
- 2025-26 禁區：修正後 .577830，shots.json .577736，差 +0.0000940。
- 被改分區的出手數和 area-count 一致。

### 2. 錨點（a2_attrs.json）
- 方法：四季合併成一個人群。pct = 100·(less + 0.5·equal)/n；r99 = pct≥99 的最小值；S = max((r99−r90)/1.044, SD_pool)。
- r90、r99、gap、S 都和 tail-summary.json 相同，SD_pool 差約 6e-6（原因是人群 378 對 379）。
- 頂端比值：short 1.332，沒用到保險；ft 0.595，保險生效；pass 1.518。
- 之前三季的值讀自 pool/raw-<s>.json，我另外和 E-090 的 h1-pairs 交叉核對過。

### 3. c4（a4_c4.json，15 個屬性 × 4 個變體，582 人，沒有 NaN）

| 變體 | >140 | >120 的值 |
|---|---|---|
| e101 | 0 | Giannis shortValue 129.04 |
| e101g | 0 | Giannis shortValue 129.04 |
| e101z | 0 | Giannis shortValue 137.88、SGA midValue 131.80、Giannis foulDraw 121.23、Edey physique 120.81 |
| e101w | 0 | Giannis shortValue 129.04、Edey physique 120.70 |

### 4. c2（a5_c2.json）
- 公式：c2 = AB、BA 兩個方向的 Spearman(候選 g, 答案) 取平均，再減基準。
- bootstrap：2000 次，default_rng(1)，從 master 名單聯集重抽，取 5–95 百分位當 90% 區間。
- c2N：−0.0026544，[−0.006879, +0.001495]；換 seed 7、重抽 5000 次是 [−0.00694, +0.00139]。
- c2Q：−0.0031787，[−0.006709, +0.000397]；換 seed 7、重抽 5000 次是 [−0.00670, +0.00028]。

### 5. 卡片（a6_cards.json）
- OVR 計算：two_segment(gRepl)，錨點 PR1、PR50、PR99 取自 MIN≥500 人群，分位取 index round(p/100·(n−1))。582 人 0 不符。
- 和卡片 0.2.5 比：146 人升、378 人降、58 人不變，中位數 −0.3；動 ≥5 名 303 人，動 ≥10 名 133 人。和 E-096 比，動 ≥5 名 277 人。
- 中距離屬性 99 的人數：E-096 13 人 → E-101 只剩 SGA。Kessler 99→60.9、Gafford 99→73.6、Poeltl 99→78.4、Lively 99→68.6。
- h1：mid 頂端 b=0.41、不過；mid 底端不過；short 頂端 b=0.96、過；short 底端不過。這和偏差 #17（mid 兩端都關、short 底端關）一致。
- 每 10 次出手價值（E-096 → E-101）：

| 版本 | mid | long | short |
|---|---|---|---|
| fitA | .168→.102 | .426→.376 | .410→.534 |
| fitB | .199→.137 | — | .362→.489 |
| primary | .206→.137 | .436→.382 | .389→.531 |

  fitA 的標準誤：mid 約 .062–.070，long 約 .17，short 約 .14–.15。

### 6. 偏差審查（17 條）
- #3：E-097 預註冊第 24 行寫「k、kh、lam 照 V61 回測的擬合值不改」，沿用有依據。
- #4：符合 §1 的「其他屬性的 h1 照 E-090」。
- #7：用卡片自己的 POOL41 定義，合理。
- #9：分數標準化過的屬性看不出季節強弱，這是誠實揭露的限制，不是違規。
- #10：就是預註冊 §3 的原文「a99 照曲線不變」。
- #17：照 §1 的 h1 規則。mid 頂端 n=5，區間跨 0，所以 mid 兩端都關；short 底端也關。
- 計算鏈：E101 的 chain/ 和 E-097 的 diff 只有路徑和變體名稱不同。

### 7. 寫入範圍
- E-101 的腳本只寫 `reports/card-0.2.5+E101-crossera/`。
- 比預註冊新的非 E-101 檔案：scripts/enrich_roster_viewer.py（01:17）、scripts/fit_game_contribution.py（01:11）、scripts/__pycache__、data/_inseason_build/*、data/season-source/dnp-*/_fetch_log.json，以及 gh-pages 的 commit a35cc44（01:20）等。這些都屬於名單頁／賽季頁的另一個 session（對應 HEAD 的 f196d30「單場貢獻值 E-105」）。
- memory/ 是主管在 E-101 跑完後改的（experiments.md 第 1047 行有 E-101 條目）。
- reports/ 在 .gitignore 裡，所以 git status 看不到 E-101 的產出。

### 沒做到／限制
- 偏差是不是「看結果之前」決定的，沒辦法用時間戳證明（見退步 3）。
- 沒有逐一重算 13 個屬性的全部錨點，只重算了 short、ft、pass 三項；mid 和 long 只核對了分區數量和 h1。

### 檔案
`audit/` 裡的 a1_zones.py/json、a2_attrs.py/json、a4_c4.py/json、a5_c2.py/json、a6_cards.py/json、evaluate-rerun.mjs、evaluation-rerun.json、evaluate-rerun.log、npm-test-rerun.log、npm-test-rerun.exit、git-status-before.txt、git-status-after.txt。
