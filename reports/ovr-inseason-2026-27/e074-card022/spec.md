# E-074 spec：賽中 OVR 改用 card 0.2.2 當先驗（inseason 0.2.1）

用 role-card skill。lead 2026-10-29 寫，使用者同日「賽中改跟 card 0.2.2：寫 spec 派工，含 c0 重現與新版號」。

## 目的
賽中頁（2026-27）目前是 inseason 0.2.0c，先驗屬性仍是 card 0.1.2、迴歸係數錨點是 card 0.1.2、每場 OVR 錨點是 card 0.2.0 階段的 E-064。
改成全部跟 card 0.2.2（R-039；reports/card-0.2.2/）。這是換版，不是新模型：**不擬合任何新參數，不看 2026-27 結果挑設定（L-026）**。版號 PATCH → inseason 0.2.1（R-019）。

## 可改／不准改
- 可改：`reports/ovr-inseason-2026-27/live/run_c4_live.py`、`scripts/build_inseason_viewer.py`、`reports/ovr-inseason-2026-27/live/README.md`；
  新增 `reports/ovr-inseason-2026-27/live/build_prior_022.py` 與其產出 `prior-2025-26-card022.json`；本資料夾 `reports/ovr-inseason-2026-27/e074-card022/` 放報告與比對輸出。
- 不准改：`src/`、`reports/card-0.2.2/`、`reports/ovr-inseason-2026-27/v5/`、`build_prior_012.py`、`prior-2025-26-card012.json`、`publish_state.json`、已發佈的 live 日期資料夾、`scripts/season_nav.py`、`src/probability_model.js`（後兩者有使用者未 commit 的改動，別碰）。
- 不 commit、不 push、不跑 `scripts/daily_inseason_update.py`（會發佈 gh-pages；lead 審完自己跑，R-031）。
- 子程序一律 `creationflags=subprocess.CREATE_NO_WINDOW`；Python 用 `python -I`。

## 要做
新增一個開關（環境變數，命名照現有 E062_MODE／E064_MODE 慣例，例如 `CARD_MODE`，預設 `022`；`020` = 現行行為）。`022` 時：

1. **先驗屬性 x0**：照 `build_prior_012.py` 的作法寫 `build_prior_022.py`，從 `reports/card-0.2.2/ranking.csv`（sha256 2102b2f6463405a3711827372cb0774af0d6b4f769d65d0403b938de1369059e，先核對）依姓名覆寫屬性欄，其餘欄位原樣保留。`pressure` 欄取 card 0.2.2 的 `pressure`（= 逼失誤 force，E-071 P1）。另外把 `presDisplay`、`foulDisc` 帶進 prior JSON（只供顯示）。
2. **迴歸係數與錨點**：`CARD_SUMMARY` 改讀 `reports/card-0.2.2/cards/P1/primary/summary.json`；`E064_ANCHORS_FILE` 改讀同資料夾的 `pergame-summary.json`（r_repl 應約 −1.7593，印出核對）；`FORMAL_RANKING` 改 `reports/card-0.2.2/ranking.csv`；`CARD_VERSION` = `card 0.2.2`。先確認這兩份 summary 的鍵與 card 0.1.2 版相同，不同就停下回報，不要自己補。
3. **pressure 維持凍結**（frozen 名單不變）：賽中不重算逼失誤。值變成 card 0.2.2 的 force。
4. **foulDraw 賽中更新改 E-070 公式**：原始量從 FTA/FGA 百分位改成 percentile(0.75·z(FTA/36) + 0.25·z(FTA/FGA))，z 的平均／標準差與百分位對照母體**照 card 0.2.2 建 foulDraw 時用的 2025-26 母體與門檻**（去 `reports/card-0.2.2/build_card_022.py` 與 E-070 產出找，凍結成常數寫進 meta），不用 2026-27 資料重估。C4 的收縮信度沿用原 foulDraw 的設定，不重估。找不到 card 0.2.2 的母體定義就停下回報。
5. **版號**：`022` 時 `VERSION = 'inseason 0.2.1'`。`probe_base_version` 用正規式讀檔案中第一個 VERSION 字面值，所以第一個字面值要改成 `'inseason 0.2.1'`，`020` 分支放後面（照現有 0.1.2 的寫法）；改完用 `daily_inseason_update.probe_base_version()` 實際呼叫一次確認回 `inseason 0.2.1`。
6. **頁面**（`build_inseason_viewer.py`）：PRES 標籤 `壓命中率` → `壓迫`；格子顯示 prior 的 `presDisplay`，tooltip「逼失誤 X｜犯規紀律 Y（2025-26）」；照 `scripts/build_card_viewer.py` 已上線的寫法（含 num-mode 那行在 apply_common 之後改）。來源說明文字改成 card 0.2.2。
7. meta.json／report.md 的說明文字（「card 0.1.2 的屬性處理」那段）改成實際狀態。

## 驗收（全部要過才算完成）
- (c0) 重現：`CARD_MODE=020`、同一份資料（用 live 最新已發佈的資料快照，dataSha256 912c955a…，cutoff 2026-10-27），輸出的 ranking／OVR 與目前已發佈 inseason 0.2.0c 逐位元相同（比 sha256；若檔內含時間戳，比去掉時間戳後的球員列）。做不到就停下回報差在哪，不要往下。
- (c1) `npm test` 全過。
- (c2) `CARD_MODE=022` 跑完同一份資料：OVR 全為有限值、人數與 0.2.0c 相同；`lastOVR`（N=0 的先驗 OVR）對 `reports/card-0.2.2/ranking.csv` 每場 OVR 的 Spearman ≥ 0.99（不到就是錨點／先驗接錯，回報不要調）。
- (c3) `probe_base_version()` 回 `inseason 0.2.1`；頁面 build 出來 PRES 標籤是「壓迫」、有 tooltip（grep 產出 HTML）。
- 所有計算本機跑即可（單季、單次，不是多 seed）。

## 回報（先直觀數字，R-004、L-020）
1. 0.2.0c → 0.2.1 前 20 名名單變化（進／出，附 OVR）。
2. OVR 變動絕對值中位數、最大 10 人（姓名、前後 OVR、主要是哪個屬性造成）。
3. foulDraw 新舊公式差最大的 5 人（原始 FTA/36、FTA/FGA、新舊值）。
4. (c0)–(c3) 各自的證據（sha256、指令、輸出摘錄）。
5. 改了哪些檔、新檔 sha256（prior-2025-26-card022.json、輸出 ranking）。
附錄：Spearman、r_repl、凍結常數。

## 收工寫 memory
- `memory/experiments.md` E-074：結果段與狀態（「完成，待 lead 審」），只改 E-074。
- 遇到坑寫 `memory/lessons.md` 新 L（追加）。
- 不改 `handoff.md`、`rulings.md`（lead 做）。
