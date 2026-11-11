# card 0.2.12a／inseason 0.2.12b spec：TO 失誤率分母改觸球次數上線（R-144，E-207）

用 role-card skill。cwd `D:\Projects\CODING\basketball-autochess`。使用者 2026-11-02 看完 E-206 結果說「採用上線」（R-144）：不先送 role-audit、不再回測，直接上線兩頁。

## 要做什麼
在目前正式版（`reports/ovr-inseason-2026-27/live/CURRENT.json`：card 0.2.12／inseason 0.2.12a；**開工先讀它的 note 全文，照裡面的換版規矩做**）之上，只換 tovSkill 的 r 分母（持球分鐘 → 觸球次數），其他不變。新定義＝E-206 預註冊 §1（`reports/card-0.2.12+E206-to-touches/preregistration.md`）＋子代理實作詮釋（同目錄 `report.md`「與預註冊不同或自行詮釋之處」：換算係數 ρ 用 582 張卡片池 15.593），照抄，不另改。

### 卡片端（2025-26）
- 直接採用 E-206 KC 臂產物（`reports/card-0.2.12+E206-to-touches/work/KC/final/out/ranking.csv`，sha256 988b741f…）。正式版放本目錄 `reports/card-0.2.12b-touch/`（build 腳本仿 `reports/card-0.2.12-tov/build_0212.py`），重建結果須與 KC final 逐位元組相同。
- 依 CURRENT note 重取凡是依卡片池重算的東西（用人層 usage、先驗 prior、OVR 映射錨點、3PT 池等）；照 L-109 重跑 `reports/E121-rookie-scale/build_2k_start.py` 重解新秀 δ。

### 賽中端（2026-27）
- `data/defense-seventh/2026-27/possessions.json` 已存整份回應（含 `TOUCHES`）；`scripts/fetch_possessions.mjs` 的 `NEED` 加上 `TOUCHES`。
- `live/tov_live.py`：r 分母改窗口加權觸球（過去季 handle-E069 raw TOUCHES、本季 possessions.json，權重同持球分鐘），k、kh 乘同一個 ρ；v 仍用持球分鐘。收縮 t、z 平均與標準差、池 raw 分布、v 第 10 百分位、0–99 映射重新凍結成新檔（例如 `tov-pool-card0212b.json`），對卡片 tovSkill 重現到 1e-6 內。
- 新秀：沿用 RAMP_MIN＝300（R-142）線性遞增混合；先驗改同位置 TOV／TOUCHES。
- 開關：環境變數 `TOV_TOUCH=0` 重現 inseason 0.2.12a／card 0.2.12（ranking.csv 逐位元組相同）。`TOV_POSS=0` 仍要能重現 0.2.11。

### 版號
**字母版**（R-109：E-206 前 100 名移動 ≥10 名 8 人 < 25、前 20 名進出 1 人）：卡片 **card 0.2.12a**、賽中 **inseason 0.2.12b**（0.2.12a 已被引力補值用掉）。檔名、資料夾用 `0212b`／`touch` 字樣，避開 `_retired/` 既有的 `*0212*`、`*0212tov*` 檔名。

### 網站
- `scripts/season_nav.py` ATTR_TIPS 的 tovSkill 說明改成：每<b>次觸球</b>的失誤少、且<b>持球時間</b>長（各半）；不持球的人失誤少不算數。
- `tov_rows`（TO 格子提示）：失誤／場、持球分鐘／場（名次）、**每百次觸球失誤**（PR、名次）取代每持球分鐘失誤。卡片頁用 2025-26 tracking、新賽季頁用本季 possessions.json。
- OFF 提示貢獻欄（`OD_OFF`）的 tovSkill 依新係數。
- PATCH_NOTES：字母版併入 0.2.12 格（R-064，照 0.2.12a 引力那條的寫法），例如「TO 改看每次觸球的失誤：拿球拿很久不再加分（Harden 9 → 85 名、Luka 19 → 88 名）。｜…」名次照實際結果填，其餘收進 hover。
- 重建卡片頁與新賽季頁。

## 限制
- 共用 checkout：別的 session 對 `scripts/season_nav.py`、`scripts/build_*_viewer.py`、`memory/*`、`TODO.md` 常有未 commit 改動，**共用 index 常和 HEAD 不同步**。commit 一律：以 `git show HEAD:<檔>` 為底套用自己的修改 → `git hash-object -w` → 暫時 `GIT_INDEX_FILE`（`git read-tree HEAD`）＋`git update-index --cacheinfo` → `git commit-tree`＋`git update-ref`；commit 後只對自己碰的路徑跑 `git reset -q HEAD -- <路徑>`。工作樹也套用同樣修改、保留別人的改動。**絕不一般 `git commit`、`git add -A`、`git stash`、其他形式 `git reset`、`git checkout -- <別人的檔>`**（L-047）。
- 建頁面若要排除別人未 commit 的內容：照 `reports/card-0.2.10i/progress.md` #6 暫換 commit 版、建完還原；還原前先比對檔案沒被別人在建構期間改過（被改過就不還原、回報）。
- `reports/` 被 gitignore，新檔用 `git add -f`（或 temp index 的 `--add`）。
- 子程序 `creationflags=subprocess.CREATE_NO_WINDOW`、`stdin=DEVNULL`；長指令 `</dev/null` 加 timeout；超過約 2 分鐘用背景。重算超過本機輕量改到 5090（`ssh kojiek@100.97.181.15`）。
- 不改 `src/` 模擬。不碰金鑰。每完成一步在本目錄 `progress.md` 追加一行。

## 驗收（全過才發布）
- c0：`TOV_TOUCH=0` 時卡片與賽中 ranking.csv 與目前線上（card 0.2.12／inseason 0.2.12a）逐位元組相同。
- 卡片新版與 E-206 KC final 逐位元組相同（sha 988b741f…）。
- `npm test` 全過（含 live_current_gate、rookie_start_gate）；新版自檢腳本（仿 `check_inseason_0212tov.py`）。
- CURRENT.json 更新（note 開頭寫 0.2.12b 段）、舊版建構腳本與凍結檔照規矩 git mv 到 `_retired/`。
- commit、push 後立刻發 gh-pages（`python -I scripts/daily_inseason_update.py --force`），curl 確認線上兩頁版號（卡片頁 0.2.12a、新賽季頁 0.2.12b）、TO 提示有每百次觸球失誤。
- 每日排程只是 daily 腳本多存一欄，不新增排程；若改到排程動作，照 `C:\Users\柯子捷\.claude\CLAUDE.md` 更新 registry.json 並跑 `audit.ps1` 要 FAIL=0。
- memory：不用寫，lead 收尾時寫。

## 回報（最後訊息）
CLAUDE.md 六段（第一行 `# 總評`）。直觀證據：兩頁各一張表，舊→新的 TO、TO 名次、OVR 名次：前 10 名＋Reaves、KPJ、Harden、Luka、Cade、Maxey、Brunson、Kornet；前 100 名移動 ≥10 名人數；線上網址與版號；commit hash。
