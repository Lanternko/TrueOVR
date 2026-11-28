> 實際編號 **E-091**（E-089／E-090 派工時已被其他 session 占用，L-050）。資料夾名沿用 e089-card024。

# E-089 spec：賽中 OVR 改用 card 0.2.4 當先驗（inseason 0.2.2）

用 role-card skill。lead 2026-10-29 寫，使用者同日「將新賽季也跟上0.2.4」。照 E-074（`../e074-card022/spec.md`）的換版作法。

## 目的
賽中頁（2026-27）目前是 inseason 0.2.1e：先驗屬性、迴歸係數、每場錨點都是 card 0.2.2。
正式卡已是 card 0.2.4（R-044）= card 0.2.2 + E-075 用人回歸（R-040）+ E-084 訓練目標改當季 RAPM（R-042）。
**能力值欄 0.2.4 與 0.2.2 逐欄相同**，差別只在 OVR 那一層：

```
p        = 屬性迴歸的每 36 預測（現在賽中算的 pred）
predNew  = b0 + b1·p + b2·L + b3·a + b4·y + b5·v + b6·y·L + b7·v·L + b8·y·d·L   （has=True；has=False 時 predNew = p）
g        = (predNew − r_repl) × mpg / 36       mpg = mpgAvail（可出賽場數修正後的場均，= card 0.2.4 ranking.csv 的 mpg 欄）
OVR      = 兩段式映射(g; PR1, PR50, PR99)
```
L = log1p(mpgAvail)、a = 出賽率（打了幾場／可出賽場數）、y = 年齡 ≤ 23、v = 年齡 ≥ 31、d = 主要球隊勝率 < 0.35；全部取 2025-26 全季。
係數、r_repl、錨點在 `reports/card-0.2.3+E084-current-target/results.json` 的 `coefficients.card` 與 `card`（`r_repl`、`anchors`）；特徵定義在同資料夾 `e084.py` 的 `scope_feats('full', …)`、`design()`、`AGE_Y, AGE_V, D_THR = 23, 31, 0.35`。

這是換版，不是新模型：**不擬合任何新參數，不看 2026-27 結果挑設定（L-026）**。版號 PATCH → inseason 0.2.2（R-019）。

## 已定的設計（不要改）
1. **用人特徵凍結在 2025-26**（L、a、y、v、d 都用 card 0.2.4 建卡時的值，年齡不加一歲）。賽中只讓 p 跟著 C4 更新：
   `predNew_live = b0 + b1·p_live + (其餘八項用凍結特徵)`；has=False（2025-26 沒有可出賽紀錄、新秀等）→ `predNew_live = p_live`（同卡片規則）。
   理由：分鐘已經透過 MPGhat 進每場 g；賽中再用 2026-27 分鐘重算 L 等於新模型，要另寫預註冊。
2. **MPG0 改成 card 0.2.4 的 mpg 欄**（mpgAvail），讓 N=0 時能重現正式卡。視窗 MPG_win 照舊是 2026-27 MIN／GP，MPGhat = MPG0 + w·(MPG_win − MPG0) 不變。先驗卡沒有的人照現行退回規則。
   已知限制（只報告）：MPG0 用可出賽場數、視窗用出賽場數，口徑不一（R-042 列的 mpg-A／B 問題）；報告 |mpgAvail − 舊 MPG0| > 3 的人數與最大 5 人。
3. **r_repl、PR1／PR50／PR99** 改用 E-084 `results.json` 的 `card.r_repl`、`card.anchors`（不是 card 0.2.2 的 `pergame-summary.json`）。
4. pressure、drive 維持凍結；foulDraw 照 E-074 的 E-070 公式與凍結常數（0.2.4 能力值跟 0.2.2 一樣，所以 x0 與 prior JSON 可以沿用 `prior-2025-26-card022.json`；若要另產 prior-2025-26-card024.json，屬性欄必須與 022 版逐位元相同，在報告中證明）。

## 可改／不准改
- 可改：`reports/ovr-inseason-2026-27/live/run_c4_live.py`、`scripts/build_inseason_viewer.py`、`reports/ovr-inseason-2026-27/live/README.md`；新增 `reports/ovr-inseason-2026-27/live/build_usage_024.py`（把每人凍結特徵與 has 旗標輸出成 `live/usage-2025-26-card024.json`，含 sha256 與來源檔 sha256）；本資料夾放報告與比對輸出。
- 用人特徵**直接 import／呼叫 `e084.py` 的函式重算**，不要重抄公式；算完要驗證：用這些特徵＋`coefficients.card`＋`card.r_repl`／`anchors` 套回 p，得到的 OVR 與 `reports/card-0.2.4/ranking.csv` 的 ovr 582 人最大差 < 1e-6（做不到就停下回報）。
- 不准改：`src/`、`reports/card-0.2.*/`、`reports/card-0.2.3+E084-current-target/`、`prior-2025-26-card012.json`、`prior-2025-26-card022.json`、`build_prior_0*.py`、`publish_state.json`、已發佈的 live 日期資料夾（`2026-10-27`、`2026-10-28` 等）、`scripts/season_nav.py`、`scripts/build_*_league.js`、`test/`（工作樹裡有別人未 commit 的改動，別碰）。
- 不 commit、不 push、不跑 `scripts/daily_inseason_update.py`（會發佈 gh-pages；lead 審完自己跑，R-031）。輸出寫到本資料夾的 `out-022/`、`out-024/`（run_c4_live.py 第一個參數是輸出資料夾名，相對 live/；用 `../e089-card024/out-024` 之類，不要寫進 live 日期資料夾）。
- 子程序一律 `creationflags=subprocess.CREATE_NO_WINDOW`；Python 用 `python -I`。

## 要做
- `CARD_MODE` 新增 `024` 並設為預設；`022` = 現行 inseason 0.2.1 行為（要能逐位元重現）、`020` 照舊。
- `024`：`VERSION = 'inseason 0.2.2'`、`CARD_VERSION = 'card 0.2.4'`、`FORMAL_RANKING = reports/card-0.2.4/ranking.csv`（先核對 sha256 與 `reports/card-0.2.4/summary.json` 的 `ranking_csv_sha256` 相同）。`probe_base_version` 讀檔案中第一個 VERSION 字面值，所以第一個字面值要是 `'inseason 0.2.2'`；改完實際呼叫 `daily_inseason_update.probe_base_version()` 確認。
- 在 `pw.predict` 之後、`e064_convert` 之前插入 predNew（live 與 ref、o1 三處都要；ref／o1 用 MPG0）。`e064_convert` 用新的 r_repl／錨點。
- ranking 輸出新增欄 `predNew`（4 位小數）；`predictedPer36` 照舊是 p。
- 頁面：來源說明文字改成 card 0.2.4（用人回歸＋當季 RAPM 目標），其他顯示不動。meta.json／README 說明改成實際狀態。

## 驗收（全部要過才算完成）
- (c0) 重現：`CARD_MODE=022`、用 live 最新已發佈資料（cutoff 2026-10-28，dataSha256 606333d0…80be，見 `live/publish_state.json`），輸出 ranking.csv／no-prior.csv 與 `live/2026-10-28/` 已發佈的逐位元相同（比 sha256；若含時間戳，比去掉時間戳後的球員列）。做不到就停下回報差在哪。
- (c1) `npm test` 全過（exit 0）。
- (c2) `CARD_MODE=024` 同一份資料：OVR 全為有限值、人數與 0.2.1e 相同；f=0、k 上界的檢查 (a)（`t1`，N=0 先驗 OVR 對 ref）最大差 < 0.5；N=0 先驗 OVR（lastOVR）對 `reports/card-0.2.4/ranking.csv` 的 ovr：Spearman ≥ 0.99，並列最大差 10 人。不到就是接錯，回報不要調。
- (c3) `probe_base_version()` 回 `inseason 0.2.2`；頁面 build 出來的來源文字含 `card 0.2.4`（grep 產出 HTML）。
- (c4) 凍結特徵套回重現 card 0.2.4 ovr 最大差 < 1e-6（見上）。
- 本機跑（單季、單次）。

## 回報（先直觀數字，R-004、L-020）
1. 0.2.1e → 0.2.2 前 20 名進／出（附 OVR）。
2. ΔOVR 絕對值中位數、最大 10 人（姓名、前後 OVR、年齡、mpgAvail 與舊 MPG0、主要原因：用人項／MPG0 改口徑／錨點）。
3. 年輕（≤23）與老將（≥31）ΔOVR 中位數。
4. (c0)–(c4) 證據（sha256、指令、輸出摘錄）。
5. 改了哪些檔、新檔 sha256。
附錄：係數、r_repl、錨點、has=False 人數。

## 收工寫 memory
- `memory/experiments.md` 追加 E-089（內容／設定／結果／狀態「完成，待 lead 審」／相關 R-044、E-074、E-084、R-019、R-031、L-026／來源：使用者 2026-10-29「將新賽季也跟上0.2.4」）。只追加 E-089。
- 遇到坑寫 `memory/lessons.md` 新 L（追加，下一號 L-049）。
- 不改 `handoff.md`、`rulings.md`（lead 做）。
