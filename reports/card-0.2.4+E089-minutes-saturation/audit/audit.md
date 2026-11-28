# E-089 稽核（role-audit）

稽核日期：2026-10-29。稽核者：獨立派工 session，不是產出者。repo HEAD `ed7811e`。

## 結論（先看這裡）

- **這次稽核的目標**：用自己重寫的程式重算 E-089（卡片分鐘權重 mp/36 → 飽和曲線 W）的 m1–m3，判斷「預註冊六條全過」站不站得住。
- **對得上的**：
  - 四個 Δρ（N_W、N_lin、Q_W、Q_lin）點估計和 90% 區間，我自己實作的 W、g_c、四個答案、ρ、bootstrap 算出來**四位小數全部一樣**（差 0.0000）。
  - c0：`--minutes linear` 的 ranking 與 card 0.2.4 逐位元相同（sha256 一致）。
  - 改動範圍：`sat15` 只動了預註冊 §2 說的兩處（g_c、card_from 的 g），其餘差異是開關、單元檢查、輸出路徑與報告段。
  - W 四個單元值全對。
  - 卡片：582 人全部用我自己的 W 重算 OVR，和 `ranking.csv` **一個不差**（OVR 差 0.0、名次差 0）。Caruso 103 → 39、78.9 → 85.9 屬實。
  - 流程：預註冊 18:57:38 早於結果 19:05:47；三份 run log 的 m1–m3 數字完全相同；用最終版 `e089.py` 在 audit/ 重跑，`ranking.csv` sha256 與原檔相同。
- **對不上或有疑慮的**（都不影響「通過」結論）：
  1. **§6 唯讀目錄的合併 sha 我重算不出來**：報告寫的 `867054e7…0295` 沒說是怎麼算的，我試了四種常見算法都對不上；而且 `data/` 之後被別的工作改過（見下方 §6）。改用「檔案修改時間 + git 狀態」替代，結果是 E-089 期間沒有任何唯讀檔被改。
  2. `ro_after.txt` 的時間是 19:05:03，比最後一次輸出（`ranking.csv` 19:05:47、`results.json` 19:05:55）早；不過 `e089.py` 的寫檔路徑只有 `HERE`／`work/`（見下），所以不會寫進唯讀目錄。
  3. 看不到 `e089.py` 在 run.log、run2.log 當下的版本（沒有留副本）。「run3 沒改到 m1–m3」是靠三份 log 的數字相同加上最終版重跑相同來佐證，不是直接比對舊版程式。
  4. 判讀上的提醒（不是錯誤）：m1 的主量尺和新定義用同一個 W（預註冊已揭露），所以 m1 的進步有一部分是量尺同向；但完全不用 W 的線性量尺（N_lin、Q_lin）也沒變差（+0.0087、+0.0051），所以「沒弄壞」站得住。Q_W、Q_lin 的區間含 0，只能說「沒變差」，不能說「變準」。
- **總評：大致達成 有部分退步**，意思是 **E-089 的通過結論站得住**。預註冊 m1–m3 的數字我獨立重現（三條硬門檻都過，下界離門檻很遠）。「有部分退步」指的是 E-089 本身對名單的副作用（Dyson 17 → 18、Maxey 12 → 26 等，屬產出者已列的只報告項，不是稽核疑慮），以及上面第 1、3 點的流程證據缺口。

## 對照表

| # | 檢查 | 產出者的值 | 我的值 | 對得上？ |
|---|---|---|---|---|
| 1 | c0：linear ranking vs card 0.2.4 | sha256 `af37ce25…7203` 相同 | `work/linear/ranking.csv`、`reports/card-0.2.4/ranking.csv`、audit 重跑版三者 sha256 全為 `af37ce25…7203`；最大差 0.0 | 對 |
| 2 | 改動範圍 | 只換兩處 mp/36 → W(mp) | 自己 `diff --strip-trailing-cr`：第 406、457 行兩處＋開關／單元檢查／輸出路徑／評估與報告段；沒有超出 §2 的實質改動 | 對 |
| 3a | m1 Δρ_{N_W} | +0.0096 [+0.0020, +0.0176] | +0.0096 [+0.0020, +0.0176] | 對（點估計差 <0.0001，端點差 <0.0001） |
| 3b | m2 Δρ_{N_lin} | +0.0087 [+0.0011, +0.0168] | +0.0087 [+0.0011, +0.0168] | 對 |
| 3c | m3 Δρ_{Q_W} | +0.0066 [−0.0005, +0.0141] | +0.0066 [−0.0005, +0.0141] | 對 |
| 3d | 只報告 Δρ_{Q_lin} | +0.0051 [−0.0022, +0.0130] | +0.0051 [−0.0022, +0.0130] | 對 |
| 3e | 三條門檻 | m1 下界 > −0.02、m2 > −0.05、m3 > −0.05 全過 | 下界 +0.0020、+0.0011、−0.0005，全過 | 對 |
| 4 | W(0)、W(36)、W(5)、W(20) | 0、1、0.31175、0.80987 | 0、1、0.311750、0.809873 | 對 |
| 5a | Caruso | 103 → 39 名、78.9 → 85.9 | 39 名、OVR 85.9（g 2.4512） | 對 |
| 5b | Dyson Daniels | 17 → 18 名、92.4 → 90.8 | 18 名、90.8（g 2.8225） | 對 |
| 5c | 隨機 5 人（seed 7）＋全部 582 人 | — | 5 人 OVR、名次皆同；全員 OVR 最大差 0.0、名次不同 0 人 | 對 |
| 6a | 預註冊早於結果 | 18:57:38 < 19:05:47 | stat：預註冊 18:57:38.82、ranking 19:05:47.79、results 19:05:55.05；預註冊 sha256 `0fa1b15c…2fbe` 相符 | 對 |
| 6b | 凍結後沒改門檻、曲線、人群 | 三次 run | run2.log 與 run3.log 完全相同；run.log 與 run2.log 只差 verdict 一行（c1 從待定變通過）；門檻、W、人群的數字沒變 | 對（見疑慮 3） |
| 6c | §6 唯讀目錄 sha | `867054e7…0295` 跑前跑後相同 | 算法不明，重算不出同一個值；替代檢查：六個 reports 唯讀目錄 0 個檔案比預註冊新、git status 乾淨 | **沒法判定原值；替代檢查沒問題** |
| 7 | 輸出檔 sha256 不變 | — | ranking.csv `73b1d635…050a`、results.json `7e36f0d6…d371`、preregistration.md `0fa1b15c…2fbe`，與驗收值一致 | 對 |

---

## 細節與證據

### 做法與獨立程度

`audit/audit_recalc.py`（執行約 20 秒，輸出 `audit_recalc.json`）：

- **自己實作**：W、g_c = (pn − r) × W(mp)、四個答案、Spearman ρ（自己寫平均名次，不用 scipy）、bootstrap、卡片 g／替補水準 PR10／錨點 PR1·50·99／two_segment／四捨五入／排名。
- **當資料來源用**：呼叫 `e089.py` 的 `load_data`、`build_pools`（E-075 pools）、`classify`、`scope_feats`（讀 CSV、組特徵），以及 `pipeline()` 只取「用人回歸預測 pn、pred_new」。回歸係數不受分鐘權重影響（只換 g，不換回歸），c0 已證明 linear 重現 card 0.2.4。所以**用人回歸本身和替補水準 r 的輸入不是獨立重算的**，這是本稽核的範圍限制。我用兩個檢查把這個依賴框住：
  - 我用 pn、r、mp 自己算的線性 g_lin，和產出者線性模式的 g_c 最大差 4.4e−16（兩個方向都是），代表 pn、r、mp 取對了。
  - 答案要的 netN（rapm1 net）、net（pooledNet）、mpg_ev 我從 D 直接取，並確認和管線給的陣列逐位相同。
- 未呼叫 `e089.py`／`e084.py` 的 `rho`、`e089_eval`、`card_from`、`two_segment`、`w_sat`。
- 解讀（預註冊 §3 沒寫清楚、照 E-084 evaluate 段）：
  - 人群 `pools['AB']`（389 人）、`pools['BA']`（388 人）；master = 兩者姓名聯集（395 人，排序）。
  - N 系列只用有 rapm1 的人（本次兩邊都是全員有）；Q 系列用整個 pool。
  - bootstrap：`default_rng(1)`，每次 `ix = rng.integers(0, 395, 395)`，兩個方向、候選與基準共用同一個 ix；每個方向先算 ρ，再 AB／BA 平均；Δ = 候選平均 − 基準平均；區間是 2000 次 Δ 的第 5、95 百分位。
  - 答案方向：g_c 用 fit 半季資料（pn、mp 取自 fit 半季特徵），答案用 ev 半季（mpg_ev、RAPM）。
  - 因為我的 bootstrap 抽樣順序和產出者一樣，連區間端點都逐位相同。若抽樣順序不同，端點應有小差距；四位小數完全一樣表示我們的解讀一致，不是巧合以外的獨立驗證。

### 1. c0

```
sha256sum audit/rerun/work/linear/ranking.csv work/linear/ranking.csv reports/card-0.2.4/ranking.csv
af37ce25169c64b5e747afe066b42747c187b5d2ef20ffb3cc454e3ba95b7203   （三者全同）
diff audit/rerun/work/linear/c0.json work/linear/c0.json   → 無差異
```
`audit/rerun/` 是把 `e089.py` 複製過去、只改 `ROOT` 一行（`diff` 驗證只有這一行不同）後完整重跑的結果，輸出沒有覆蓋原檔。重跑的 `ranking.csv` sha256 = `73b1d635…050a`，與原檔相同；`results.json` sha 不同，只因 `inputs_sha256` 的鍵是檔案路徑（自動比對：只有那 4 個路徑鍵不同，其餘全部值相同）。

### 2. 改動範圍

```
diff --strip-trailing-cr reports/card-0.2.3+E084-current-target/e084.py reports/card-0.2.4+E089-minutes-saturation/e089.py
```
e084.py 有 CRLF，e089.py 是 LF，直接 diff 會整檔都不同；`diff-e084.txt`（395 行）已處理這點，內容和我的結果一致。diff 區塊：

| 位置 | 內容 | 是否在 §2 內 |
|---|---|---|
| 1–8 行 | docstring | 是（說明） |
| 57a57,67 | `MINUTES` 開關、`w_sat()`、`wmin()` | 是 |
| 406 | `g_c = (pn - rr) * sf['mp'] / 36` → `* wmin(sf['mp'])` | 是（半季候選） |
| 457 | `g = (pr - r) * mp / 36` → `* wmin(mp)` | 是（card_from） |
| 677 起 | 刪 `run_c0`／`run_season`／`season_eval` 相關評估與 E-084 報告段；新增 `unit_checks`、`run_minutes`、`e089_eval`、`report_only`、`read_gates`、`run_e089` | 開關／單元檢查／評估／輸出路徑／只報告項；沒有碰回歸特徵、POOL_MIN、PR10、two_segment、年齡項 |

另外確認：`g_b`（E-084 原本的基準欄 `sf['p']…mpg0/36`）沒動；`wmin` 在 `linear` 時回傳 `mp/36`，與原式相同。**沒有超出 §2 的實質改動。**

`e089.py` 寫檔位置只有 `HERE/ranking.csv`、`HERE/results.json`、`W/linear/`（`W = HERE/'work'`），都在 E-089 目錄內。

### 3. m1–m3（`audit_recalc.py` 輸出）

```
Δρ_N_W:   +0.0096 [+0.0020, +0.0176]  (cand 0.4952, base 0.4856)
Δρ_N_lin: +0.0087 [+0.0011, +0.0168]  (cand 0.4934, base 0.4847)
Δρ_Q_W:   +0.0066 [-0.0005, +0.0141]  (cand 0.5925, base 0.5858)
Δρ_Q_lin: +0.0051 [-0.0022, +0.0130]  (cand 0.5936, base 0.5885)
```
產出者 `results.json`／`work/linear/…` 對應值：+0.009560 [+0.002004, +0.017641]（m1）等，與我的一致到小數第 4 位。三條門檻的下界離門檻最近的是 m3（−0.0005 對 −0.05），沒有邊緣問題。

### 4. W 單元值

W(0)=0、W(36)=1、W(5)=0.311750012、W(20)=0.809872871（我的實作，公式照預註冊 §0）。

### 5. 卡片抽驗

我的流程：pred_new（用人回歸，取自管線）→ r = 池內（MIN ≥ 500，378 人）PR10 = −1.27245 → g = (pred − r) × W(mpg) → 錨點 PR1 −0.8153、PR50 1.2506、PR99 3.4429（與報告 §2.8 相同）→ two_segment → 四捨五入到 0.1 → 依未四捨五入的 OVR 排序。

| 球員 | mpg | g（我） | g（csv） | OVR 我／csv | 名次 我／csv | card 0.2.4 OVR／名次 |
|---|---|---|---|---|---|---|
| Alex Caruso | 17.90 | 2.4512 | 2.4512 | 85.9／85.9 | 39／39 | 78.9／103 |
| Dyson Daniels | 33.15 | 2.8225 | 2.8225 | 90.8／90.8 | 18／18 | 92.4／17 |
| Julian Phillips | 5.62 | 0.4689 | 0.4689 | 58.6／58.6 | 332／332 | 55.9／345 |
| Devin Vassell | 30.51 | 1.5417 | 1.5417 | 73.9／73.9 | 155／155 | 76.1／134 |
| Mason Plumlee | 3.57 | 0.1686 | 0.1686 | 54.3／54.3 | 405／405 | 52.9／410 |
| Paul George | 30.68 | 2.3488 | 2.3488 | 84.5／84.5 | 50／50 | 85.2／54 |
| Moussa Diabaté | 26.01 | 2.1529 | 2.1529 | 81.9／81.9 | 75／75 | 80.5／88 |

（隨機 5 人 = `random.Random(7).sample(ranking.csv 檔案順序的姓名, 5)`；「隨機怎麼抽」預註冊沒定義，這是我的解讀。）
全部 582 人：OVR 最大差 0.0，gRepl 最大差 5.0e−5（csv 四位小數的捨入），名次不同 0 人。同一程式用線性權重重放 card 0.2.4，OVR 也是 0.0 差，說明我的卡片流程本身正確。

只用公開 csv 反推（不碰管線）：Caruso 的 (pred − r) = 1.5905 × 36 / 17.90 = 3.1988，× W(17.90) = 2.4512，與 csv 相同。

### 6. 流程

```
stat：preregistration.md 18:57:38.82；preregistration.sha256 18:57:39.41；ranking.csv 19:05:47.79；results.json 19:05:55.05
sha256sum preregistration.md = 0fa1b15c…2fbe（與 preregistration.sha256 及驗收值相同）
run.log／run2.log／run3.log
```
- `diff run.log run2.log`：只差 verdict（「待 c1」→「通過」）與尾行 `exit 0`；m1、m2、m3、Q_lin 的數字完全相同。c1 的 `npm-test.exit` 在 run.log 之後（19:03:58）才寫出，符合設計（c1 待定）。
- `diff run2.log run3.log`：**完全相同**。run3 只改 `read_gates()`（只報告項），`e089.py` 的修改時間 19:05:38 在 run2（19:04:29）之後、run3（19:05:55）之前，和報告一致。
- `evaluation.json` 的閘門：card-0.2.4 16/19（carusoGate、big14of16、allFourStayTop10 沒過），E089 18/19（只剩 allFourStayTop10）——與報告一致，只報告，不是判定條件。
- 凍結後 prereg 沒被改：sha 與 prereg 目前內容相符，且 `e089.py` 在開頭用 `preregistration.sha256` 驗證。

**§6 唯讀目錄 sha（疑慮 1）**

- `work/ro_before.txt`／`ro_after.txt` 都是 `867054e7…0295`，但沒有記錄算法。我試了：
  - 所有檔案 `sha256sum`（排序）再取 sha：`ac7d2893…b7df`
  - 逐目錄分別算再合併：`33177677…175b`、`331f8165…5fd6630`
  - 其他排序與 cat 版：`cb26fd14…`、`63c7105d…`、`b2eae0fc…`、`3e84ce42…`（git ls-files）

  全部不等於 `867054e7…`。
- 另外 `data/` 現在已經不同於 E-089 當時：有 5 個檔案（`data/defense-seventh/2026-27/*`、`data/season-source-2026-27/*`，修改時間 2026-10-29 19:19）比 `results.json`（19:05:55）新。這是別的工作（2026-27 賽季資料更新）改的；`e089.py` 讀的是 `data/season-source/`、`data/benchmark-source/`（2025-26），不是這幾個目錄。所以就算算法已知，現在的合併 sha 也不一定等於當時的值。
- 替代檢查（有做、結果乾淨）：
  - 六個 reports 唯讀目錄：0 個檔案比預註冊新；`git status --porcelain` 無輸出；現值合併 sha（`find | sort | sha256sum` 算法）`230a6553…78c8`。
  - `data/` 在 [預註冊, results.json] 時間窗內被修改的檔案：0 個。
  - `e089.py` 的寫檔只有 `HERE`、`work/linear/`。
- 判定：**沒法重現原 sha；但沒有任何證據顯示唯讀目錄在 E-089 期間被改**。請產出者之後把算法寫進 `work/`（建議存成腳本）。

### 沒做到／限制

- 不獨立重擬用人回歸（係數、pn、r 的輸入來自 `e089.py` 的管線），見「做法」。
- 沒有重跑 `npm test`（G1）：這次任務限定不改任何檔，且 `npm-test.exit` 為 0、`npm-test.log` 存在（19:03:58）；我只讀了 exit 檔，沒有重跑。
- evaluate 19 閘我只讀了 `evaluation.json` 與 `results.json` 的值，沒有重跑 `evaluate.mjs`。
- G5（使用者抽查）不在本稽核範圍。

### 檔案

- `audit/audit_recalc.py`、`audit/audit_recalc.json`：獨立重算。
- `audit/rerun/`：完整重跑 `e089.py`（只改 ROOT 一行）的輸出，供比對。
