# E-213 追加：官方傷病報告 PDF 備援 spec

lead：Claude Code App，2026-11-02。使用者裁定「補 PDF 備援」。

## 背景（不要重做）
- `scripts/team_ratings_daily.py` 的 `load_injuries()` 目前只抓 ESPN JSON；失敗就沿用前一份 `data/season-source-2026-27/injuries.json` 並標 `stale`。註解寫著「PDF 後備沒做（沒有 PDF 解析套件）」。
- 輸出格式見 `parse_espn()`／`attach_ids()`：每筆 `name, team(NBA tricode), status, …`，再用 playerId／正規化姓名對應，對不上進 `unmatched`。`is_out()` 決定 Out／Doubtful／Suspension 移出輪替。
- 測試在 `test/team_ratings_gate.py`。

## 要做的
1. **抓官方 PDF**：NBA 官方傷病報告（`https://ak-static.cms.nba.com/referee/injury/Injury-Report_<YYYY-MM-DD>_<HH_MM>{AM|PM}.pdf` 一類，先實際探測本季檔名格式，寫進註解）。從現在（美東時間）往回找最近一份存在的報告，最多往回 36 小時，HEAD／GET 失敗就換上一個時段。
2. **解析**：優先用 `pdftotext -layout`（本機在 `C:\Program Files\Git\mingw64\bin\pdftotext.exe`；用 `shutil.which` 找，找不到再試這個絕對路徑）；子程序必帶 `creationflags=subprocess.CREATE_NO_WINDOW`。都沒有才考慮 `pypdf`（若要裝，寫進 requirements／報告）。解析出 隊伍、球員（官方是「Last, First」要轉成「First Last」）、狀態（Out／Doubtful／Questionable／Probable／Available）、原因。表格跨頁、隊名／日期欄只在第一列出現（要往下沿用）都要處理。「NOT YET SUBMITTED」的隊伍跳過並記錄。
3. **接進 `load_injuries()`**：順序 ESPN → 官方 PDF → 沿用前一份。`source` 填 `'nba-official-pdf'`，另存 `pdfUrl`、報告時間。輸出 items 格式與 ESPN 版一致，走同一個 `attach_ids()`；Probable／Available 不算缺陣。
4. 加一個手動參數（例如 `--injury-source pdf`）可強制走 PDF，方便驗證。
5. **測試**：在 `test/team_ratings_gate.py` 加測試：用一份存進 `test/fixtures/` 的真實 PDF 文字輸出（不要存整份 PDF 若太大；存 pdftotext 結果 .txt）測解析：至少檢查筆數、某幾位球員的隊伍與狀態、「Last, First」轉換、跨頁沿用隊名。另測 ESPN 失敗時會走 PDF（mock fetch）。`npm test` 要過。
6. **實測一次**：`--injury-source pdf` 真的抓今天的 PDF 跑一遍，比對和 ESPN 版的差異（各隊缺陣人數、對不上的人數），寫進 `reports/E208-team-rating/report-pdf-fallback.md`。每日耗時不能明顯增加（ESPN 成功時不抓 PDF）。

## 限制
- 不改 `src/`、卡片、能力值、已凍結檔（`forward-2026-27-frozen*.json`）。
- 不新增排程。
- **共用工作樹**：絕不用 `git stash`／`checkout`／`reset`／`restore`（L-115）。開工先 `git status`，只 stage 自己改的檔；`git diff --cached` 確認後才 commit。若要改的檔有別人未 commit 的改動，停下回報。
- 不要整張讀大圖片進 context。
- 不用 `HANDOFF_OK=1`。
- 本機子程序不得閃黑窗。
- commit＋push 到目前分支；有改到網站輸出才需要重發 gh-pages（這次應該不用，除非頁面說明文字要改「來源：官方 PDF」顯示——若頁面已顯示 `source`，確認 PDF 來源時顯示得正確即可）。
- 收尾：`memory/experiments.md` 的 E-213 不改內容，另追加一行新 ID（檔尾最大號 +1）記這次；被抓到的錯寫 lesson。

## 回報
不是實驗結果，不用六段格式。回：做了什麼、探測到的 PDF 檔名格式、實測今天 PDF 與 ESPN 的差異（缺陣人數、對不上人數，特別注意 Doubtful 在 PDF 會出現而 ESPN 沒有）、測試結果、commit hash、偏離 spec 之處。
