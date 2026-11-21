# v55 修正 B 預先登錄：禁區「吃餅」長人被高估

寫作時間：2026-10-19，**在任何評估用模擬開始之前**。
此檔一經寫下即為判定依據，底下的門檻與樣本外切分不會因為結果不好而事後修改。
凍結的隨附檔：`frozen-groups.json`（球員分組與 EB 超參數）、`shot-origin.json`（出手來源分割）。

分支：`codex/ovr-step2-resample`。基準：v54（`reports/ovr-v54-2025-26/`、`reports/ovr-v54-shrinkage-2025-26/`）。

---

## 0. 任務給的三個歸因，先經過原始碼核對

任務列的三個成因裡有兩個指錯了位置。這一節先把實際機制寫清楚，因為後面的設計是照實際
機制做的，不是照任務敘述做的。這一節的內容會原樣進入 `report.md`。

### 0.1 「`usageFromEv` 用期望得分 softmax 分配出手，命中率越高拿到越多球，效率不隨球量衰減」——不成立（死碼）

`src/probability_model.js` 的 `usageFromEv` 在整個 repo 裡除了自己的定義與兩行註解外沒有
任何引用。模擬板走的鏈是
`reports/ovr-v54-2025-26/worker.mjs` → `reports/player-impact-v53/engine.mjs` → v47 → v45
→ v41 → `reports/defense-tenth/step4-rebounds-turnover-time/adapter.mjs`，
而 `reports/player-impact-v41/engine.mjs` 把出手分配整段換掉了：

| v41 行 | 原本 | 換成 |
|---|---|---|
| L14 | `M.handlingWeights(ls[off])` | `creationPlan.weights` |
| L15 | `M.shootRate(p.ev,passesLeft)` | `creationPlan.rows[hi].shoot` |
| L18 | 接球候選的 EV 權重 | `creationPlan.rows[hi].receivers` |

`creationPlan` 由 `p.opportunityMeasurement` 的**實測每分鐘機會率**
（`terminalOpportunityRate` / `receiveOpportunityRate` / `selfOpportunityRate`）經
`elasticLineup` 的冪次重整得到，重整用的指數與球員屬性無關。球量被釘在實際使用率附近，
**沒有**效率→球量的反饋迴路。

所以任務的修法 (a)（usage 衰減、或拿實際 USG 當 softmax 的先驗／上限）會是在修一個這塊板
上不存在的迴路。**本次不做 (a)**，理由留此備查。

### 0.2 「模擬沒有區分自主出手與被餵出手」——成立，而且有兩層

**第一層：唯一的自主出手品質判別器是結構性失效的。** `src/probability_model.js`：

```js
const assistBoost = assist === null
  ? 1 + tanhEff(handler.handle ?? M, C.HANDLE_SCALE) * C.HANDLE_IMPACT
  : 1;
```

`scripts/build_season_league.js` 對 2025-26 每一位球員都寫死 `handle: 70`，而 70 正是
`ATTR_MIDPOINT`，`tanhEff(70) = 0`，於是**全聯盟每個人的 `assistBoost` 都剛好等於 1**。
自主出手與被餵出手之間唯一的品質差，在這塊板上完全沒有作用。

**第二層：模擬逼吃餅長人自己創造機會，而他們用的是實測（幾乎全為被餵）的命中率。**
`src/timed_game.js:177-234`：`assist` 只有在傳球迴圈跑過之後才非 null，第一次觸球就出手的
球一律 `assist === null`。也就是說**在模擬裡「自主出手」的定義恰好是「出手前沒有傳球」**。
而 `centeredMake`（`reports/player-impact-v14/model.mjs`）又把命中率水準釘在實測總和上：

```js
value = p.make[z] + m.rates[z] - m.sourceBase[z] - context[z]
```

兩者相乘的後果是：模擬給 Karlo 這類人遠高於現實比例的「沒傳球就自己出手」，而這些球用的是
他「被餵進去」的禁區命中率。**這是本次要修的主要機制。**

模擬端的 attempt-level 餵球占比會在 c 的校正跑裡用 origin ledger 實測（見 3.1）。先前
`diag/sim-assist-split.mjs` 量到的 0.463 是**被助攻命中數 ÷ 總出手數**而不是餵球出手占比
（引擎的 emit 是 `assist: made&&usedAssist?passer:null`，未命中一律記 null），該數字作廢。

### 0.3 「v54 的禁區 EB 收縮 `k_short`≈80 太弱」——位置錯了

由 0.2 引的 `centeredMake` 可知，命中率的**水準**由實測 `m.rates[z]` 決定，卡片只透過
「新卡片的 make − 被凍結的 v53 卡片 `sourceBase`」這個差分進入。Karlo 的
`rates.long` 0.391125 vs `sourceBase.long` 0.391093、`rates.short` 0.6555 vs
`sourceBase.short` 0.6660——差分極小。把 `k_short` 從 80 加大，效果會被 `rates` 吃掉。
**正確的槓桿是收縮 `shootingMeasurement.rates` 本身**，即下面的 B2。

另外查到兩個重要事實（`reports/player-impact-v9/input.mjs:15`）：

```js
q = (made + 100*prior[z]) / (a + 100)      // prior[z] = 聯盟 attempt-weighted 平均
rates[z] = logistic(logit(q) + shotDelta)
```

1. `rates` **已經**有 100 次偽計數的收縮，Karlo 的禁區 fresh 出手約 100 次，他現在已被收掉
   約一半。
2. 先驗是**聯盟**平均而非分位置平均。所以反直覺地，**改用分位置先驗會把長人往上拉而不是
   往下壓**（C/PF 的禁區命中率先驗 ≈0.66 高於聯盟 ≈0.60）。B2 因此只動可靠度權重、不動
   先驗口徑。

---

## 1. 資料：餵球／自主出手分割（已完成，在模擬之前）

### 1.1 repo 內有什麼、沒有什麼

| 需求 | 狀態 | 來源 |
|---|---|---|
| 逐球員逐區「被助攻的命中數」 | **有**，四季齊全 | `data/defense-a-source/pbp`（2025-26，1227 場）、`data/defense-seventh/<season>/pbp`（2024-25 / 2023-24 / 2022-23，1229 / 1230 / 1230 場），`actions[].assistPersonId` |
| 出手層級的創造模式（命中與未命中都有） | **有** | 同上的 `descriptor`（cutting / alley-oop / driving / pullup / step back / putback / tip…）× `subType`（Layup / DUNK / Jump Shot） |
| %AST、USG%、AST_RATIO、POSS | **有** | `data/benchmark-source/advanced.json`（Karlo：MIN 14.7、AST_PCT 0.079、TS 0.696、USG 0.128、POSS 1942） |
| touches、drives、potential assists（tracking） | **沒有** | 需要 `leaguedashptstats`（`PtMeasureType=Possessions` / `Drives` / `Passing`），本地無快取，本次不抓 |
| 可用代理 | 用 | PBP `descriptor` / `qualifiers`（本次主力）、AST_PCT、USG_PCT、禁區出手占比 |

**關鍵的不可觀測性：NBA play-by-play 只在命中的球上記助攻，所以「被助攻的出手數」本身不可
觀測。** 作法是兩階段硬分割（`prepare-origin.mjs`）：

1. 用聯盟層級算出每個 (區域, `descriptor`, `subType`) 類別的「命中球被助攻比例」q_k。
2. 把 q_k > 0.5 的整個類別判為 **餵球 (fed)**、其餘判為 **自主 (self)**。

每一球的歸屬只看自己的動作類型、不看進不進，所以兩邊的命中率是直接觀測、沒有「只看命中球」
的抽樣偏誤。命中球 <30 的稀有類別退回同區聯盟平均傾向。禁區的 `putback` / `tip` 另計並從
分割中剔除（模擬器的補籃走 `syntheticProbability` 另一條路）。

區域用幾何分類（`xLegacy`/`yLegacy`，Restricted Area ∪ Paint-non-RA = `short`）。驗證：
禁區出手 106285 vs 官方 dashboard 106161（+0.12%）、命中 61336 vs 61333（0.00%）；若改用
live feed 的 `area` 字串只有 103349（−2.65%，有 2404 球 dashboard 算禁區而 live feed 標
Mid-Range），故採幾何分類。

### 1.2 分割結果（四季穩定）

| 季 | 區 | fed 出手 | fed FG% | self 出手 | self FG% | 差 | fed 占比 |
|---|---|---:|---:|---:|---:|---:|---:|
| 2025-26 | short | 42395 | .681 | 54012 | .492 | **+.189** | .440 |
| 2024-25 | short | 43620 | .666 | 52477 | .488 | **+.178** | .454 |
| 2023-24 | short | 44170 | .651 | 54292 | .505 | **+.146** | .449 |
| 2022-23 | short | 43218 | .662 | 55072 | .505 | **+.157** | .440 |
| 2025-26 | long | 70350 | .368 | 20391 | .331 | +.038 | .775 |
| 2025-26 | mid | 4991 | .415 | 16577 | .417 | −.003 | .231 |

**結論：這是個禁區現象。** 三分差只有 .038、中距離差 ≈ 0（四季分別 −.003 / +.004 /
−.000 / −.017）。所以 **B1 只作用在 `short` 區**——這是資料決定的範圍，不是事後縮小。

### 1.3 球員層與 EB 超參數（已凍結於 `frozen-groups.json`）

2025-26、非補籃禁區出手 ≥40 的 417 人：fed 占比 s_i 分位
.06 / .21 / .30 / .43 / .62 / .80 / .98（p0/p10/p25/p50/p75/p90/p100）。
d_i = fedFG% − selfFG%：attempt-weighted 平均 **d̄ = .1852**、觀測變異 .012578、
平均抽樣變異 .011138 ⇒ **τ² = .001440**。

**這個 τ² 很小，是本次最重要的統計發現之一：d_i 在球員間的觀測離散幾乎全部是抽樣雜訊，
餵球／自主的命中率差是個聯盟層級的結構效應，不是球員技能。** 因此 EB 會把 D̃_i 幾乎全部收
到 d̄（例：Karlo 的可靠度 ≈0.05 ⇒ D̃ ≈ .192；Gobert ≈0.16 ⇒ D̃ ≈ .223）。這是保守而且正確
的結果：**真正的判別變數是 s̃_i**（Karlo .821、Jaxson Hayes .879 vs Dončić .138、
Harden .127），它的離散大且量測精確。

點名球員（2025-26，非補籃禁區）：

| 球員 | 出手 | s̃_i | raw d_i | v54 板名次 |
|---|---:|---:|---:|---:|
| Jaxson Hayes | 206 | .879 | .328 | 154 |
| Karlo Matković | 109 | .821 | .258 | 20 |
| Charles Bassey | 32 | .684 | .500（樣本不足） | 35 |
| Rudy Gobert | 321 | .850 | .398 | 12 |
| Luka Dončić | 524 | .138 | .122 | 7 |
| James Harden | 448 | .127 | .154 | 38 |

---

## 2. 假設

- **H1（主假設）** 模擬板高估吃餅長人的主因是「出手來源錯配」：模擬逼他們自主創造出遠高於
  現實比例的禁區出手，而他們沿用實測（幾乎全為被餵）的禁區命中率。把命中率依出手來源拆開
  後，高 s̃_i 球員的模擬貢獻會下降，低 s̃_i 的持球創造者不受影響或略升。
- **H2** `rates` 現行的 100 次偽計數對低出手量球員仍過於信任原始率；提高可靠度權重會改善
  替補桶（<800 分鐘）對 RAPM 的排序相關。
- **H3（樣本外）** H1 若是真結構，只用 2022-23～2024-25 的 PBP 估 s_i、d_i（完全不碰
  2025-26 的 PBP），套在 2025-26 板上仍應看到同方向的效果。

---

## 3. 要改的參數與程式

新行為**預設關閉**；v53、v54 必須能逐位元重現。

### 3.1 B1 — 出手來源分割（對應任務的修法 b）

新檔 `src/source_shot_origin.js`，匯出 `attachShotOrigin()` 與 `shotOriginAdjustment()`。
`src/probability_model.js` 只加一處，把調整量加進 `makeShort`：

```
adj_i(assist) = D̃_i * ( [assist !== null] - s̃_i ) + c
```

- **只作用在 `short` 區**；`opts.putback === true` 時不作用。
- 在球員**自己的實際來源組合**下期望值恰為 0（c=0 時），所以不需要重新校正個人水準；只有
  當模擬給他的餵球占比低於現實時才整體轉負。這同時修掉 0.2 節那個結構性失效的 `assistBoost`。
- `s̃_i = (fedA_i + 25·s̄) / (A_i + 25)`，`s̄` 為該季聯盟餵球占比（2025-26 = .4398）。
  偽計數 25 為預先登錄值，不調。
- `D̃_i = d̄ + τ²/(τ²+v_i)·(d_i − d̄)`，`v_i = p_f(1−p_f)/n_fed + p_s(1−p_s)/n_self`
  （用聯盟 p_f、p_s 以穩定估計），τ² 與 d̄ 取 `frozen-groups.json` 的凍結值。
- `A_i = 0`（毫無非補籃禁區出手）者：`s̃ = s̄`、`D̃ = d̄`。
- **`c` 是單一個聯盟水準常數**，用意是避免整體命中率水準漂移：模擬普遍餵得比現實少，若不
  校正會讓全聯盟禁區命中率一起下滑、傷到球隊層。c 的定法：在 2025-26 **球隊層**（真實
  陣容）跑一顆種子的校正跑，用新增的 origin ledger 逐出手累加 `D̃_i([fed]−s̃_i)`，取
  attempt-weighted 平均後取負號。**c 在評估跑開始之前定下來、寫進報告、之後凍結**，四季
  共用同一個 c（跨季差異寫進報告的風險段）。
- 預設關閉的機制：`shotOriginAdjustment()` 在 `handler.shotOriginMeasurement` 不存在時回傳
  0，而只有 v55 的 input 會掛上這個欄位。v41 的機率記憶化 cache key 已經含 `a`（assist），
  所以逐 assist 的調整對 cache 是安全的。
- 附帶效果（預期，非門檻）：自主出手的 EV 下降會經 `creationPlan.rows[hi].shoot` 與
  `best()` 讓吃餅長人多傳一點球。

### 3.2 B2 — `shootingMeasurement.rates` 的可靠度收縮（對應任務的修法 c，改打正確位置）

不動 `reports/player-impact-v9/input.mjs`（凍結的 v9 產物，改它會動到 v53/v54）。改在 v55
的 input 裡用同一條公式、同一個 `shotDelta`、同一個聯盟先驗重算 `rates`，只把偽計數從
100 換成 **K = 200**（三個區都換，可靠度與區域無關）。

- 先驗口徑**不變**（維持聯盟 attempt-weighted 平均，理由見 0.3 的反直覺發現）。
- 朝 attempt-weighted 聯盟平均收縮近似保水準，所以球隊層受到的衝擊有限。
- K=200 是預先登錄的唯一主值，不在評估資料上調。

### 3.3 變體

| 變體 | B1 | B2 | s_i、d_i 的資料 | 用途 |
|---|---|---|---|---|
| `B1` | ✓ | ✗ | 2025-26 | 歸因 |
| `B2` | ✗ | ✓ | — | 歸因 |
| `B12` | ✓ | ✓ | 2025-26 | **主判定** |
| `B12_oos` | ✓ | ✓ | 僅 2022-23 + 2023-24 + 2024-25 | 樣本外 |

---

## 4. 樣本外切分

`s_i`、`d_i`、τ²、d̄、s̄ 全部只用 **2022-23 + 2023-24 + 2024-25** 的 PBP 估（三季出手直接
相加），完全不碰 2025-26 的 PBP，再套到 2025-26 的板上評估 → 變體 `B12_oos`。
三季都沒有資料的新人（Maluach、Beringer、Cardwell、Queta 之外的新進者等）落回**三季合併**
的聯盟先驗 s̄、d̄，不是 2025-26 的值。

誠實先寫明三個限制：

1. B2 的 `rates` 收縮本質上是**同季**的可靠度運算（v54 本來就是這樣做），無法樣本外化。
   `B12_oos` 只把 B1 的輸入樣本外化。
2. 目標端：`pooledNet` 混入 2025-26，`lastSeasonNet` 就是 2025-26。但本次**沒有任何參數是
   對 RAPM 擬合的**（s_i、d_i、τ²、K 全部來自 box / PBP），所以目標端沒有過擬合通道；
   `B12_oos` 檢的是**輸入端的時間外推**。
3. `reports/ovr-v55-bench-prior-2025-26/` 已記錄一個結構性限制：同時滿足
   `sourceMinutes < 800` 與 `pooledPoss ≥ 5000` 的球員有 **0 人**，所以 <800 桶無法對多季
   目標做樣本外驗證；該桶的樣本外檢查一律用 `lastSeasonNet`（`lastSeasonPoss ≥ 500`，n=170）。

---

## 5. 驗收門檻（任務給定，逐字沿用）

判定一律用**實際交付的 v2（EB 收縮後）欄位**，並同時列出 raw 欄位供檢視。口徑與
`reports/ovr-v55-bench-prior-2025-26/report.md` 完全一致：
多季 = `pooledNet`（`pooledPoss ≥ 5000`）；單季 = `lastSeasonNet`（`lastSeasonPoss ≥ 500`）；
分組 = sourceMinutes `<800` / `800-1300` / `1300+` / 全體。

| # | 門檻 | v54 基準 |
|---|---|---|
| A1 | 多季 RAPM 全體 ρ ≥ **0.424** | 0.424 |
| A2 | 單季 RAPM 全體 ρ ≥ **0.515** | 0.515 |
| A3 | `<800` 桶在**兩種** RAPM 目標都改善 | 多季 0.169、單季 0.434 |
| A4 | 吃餅長人模擬名次明顯下降（定義見下） | Karlo 20、Bassey 35、Jaxson Hayes 154 |
| A5 | 2025-26 球隊層勝場 MAE **不差於 6.29** | 6.29（net RMSE 2.70；v53 為 4.56 / 2.02） |
| A6 | 守備 ρ 併列回報（**非**門檻） | 0.303（v54 報告的 v2 欄為 0.302） |

**A4 的「明顯」在此定義為兩條同時成立：**

1. **Karlo Matković 的 v2 名次下降 ≥ 10 名**（20 → ≥30）。
2. **吃餅組的平均名次變化比創造組低至少 10 名**
   （`mean(Δrank_finisher) − mean(Δrank_creator) ≤ −10`，Δ 定義為 v54 名次 − v55 名次，
   正值代表上升）。分組已凍結於 `frozen-groups.json`：
   吃餅組 = 2025-26 非補籃禁區出手 ≥60 且 s̃_i ≥ 0.75（**40 人**，含 Kalkbrenner .901、
   Kornet .900、Robert Williams III .895、Clingan .885、Jaxson Hayes .879、Mark Williams .868、
   Poeltl .862、Hartenstein .861、Gobert .850、Karlo .821、Zubac .777…）；
   創造組 = 禁區出手 ≥200 且 s̃_i ≤ 0.25（**27 人**，含 Harden .127、Dončić .138、
   Brunson .139、Garland .153、LaMelo .155、SGA .247…）。

   Charles Bassey **不設個別硬門檻**：他 2025-26 只有 153 分鐘、非補籃禁區出手 32 次，落在
   最小樣本回退規則內（s̃ 被收到 .684），蒙地卡羅雜訊本來就會蓋過效果。他的名次變化照樣
   回報。

**整體判定規則：A1～A5 全部成立才算「通過」；任一項不成立就寫「不通過」，報告保留並說明。**
主判定看 `B12`；`B1`、`B2` 用於歸因，`B12_oos` 用於樣本外。

---

## 6. 執行與重現性協議

- **板**：582 人、30 對手、8 samples、seed 20261016，與 v54 同一 harness
  （`run.mjs` / `worker.mjs` 只換 input）。輸出
  `reports/ovr-v55-finisher-fix-2025-26/<variant>/checkpoint-both-s8.jsonl`。
- **收縮**：本目錄的 `shrink.py` / `shrink_v2.py`，與 v54 / v55-bench-prior 同一估計式，
  只把 `OUT` 指到本目錄、`BUCKETS` 增加合併的 `1300+` 桶，並對**所有**變體都算
  `bucketSpearmanVsPooledRAPM` 與 `bucketSpearmanVsLastSeasonRAPM`（v55-bench-prior 只對
  `AC_oos` 算後者）。v54 的基準數字會用同一支腳本重算一次，確保是同口徑比較；報告同時列出
  我重算的值與任務提供的值。
- **球隊層**：四季 × 3 顆種子（20261012 / 13 / 14，取自
  `reports/player-impact-v47/protocol.json`），輸出寫到**本目錄底下**的 `team/runs/`，
  不寫 `reports/player-impact-v5x-team/runs/`，也不碰頂層 `runs/`。評分用
  `reports/player-box-audit/experiment/score.py` 的 `box.score`，與 v54 同一支。
- **平行性檢查（跑評估之前必須通過，結果寫進報告）**：
  1. 不掛 `shotOriginMeasurement` 且 K=100 時，板上一場比賽的 box score 與 v54 逐位元相同。
  2. K=100 重算的 `rates` 與 v54 的 `rates` 逐位元相同。
- **5090**：重度運算原則要求跑在 5090（`ssh kojiek@140.122.184.29`）。本次執行時該機
  22 埠連不上（`ping` 通、port 22 Connection timed out，即 sshd 不可達，非額度或憑證問題），
  已依限制**不自動重試、不切換帳號**，只做低頻背景探測。實測單人成本為 960 場 / 36.9 秒
  （`diag/time-one.mjs`），582 人全板單 worker 約 6 小時、10 workers 約 40–60 分鐘，本機
  可負擔。**若到執行時 5090 仍不通，就在本機跑，並在報告的風險段明寫此偏離。**
