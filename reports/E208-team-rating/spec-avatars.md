# teams.html 加球隊隊徽與球員頭像 spec

lead：Claude Code App，2026-11-02。使用者：「能夠加上球員球隊頭像嗎」。

## 現有做法（照抄，不要另起爐灶）
- 名單頁已經在用 NBA CDN：
  - 隊徽：`https://cdn.nba.com/logos/nba/${teamId}/global/L/logo.svg`（`scripts/enrich_roster_viewer.py:363`），深色版 `global/D/logo.svg`（`scripts/season_nav.py:739`）。
  - 頭像：`https://cdn.nba.com/headshots/nba/latest/1040x760/${playerId}.png`，小圖可用 `260x190`；`loading="lazy"`、`onerror` 移除或隱藏。
  - 球隊 id 對照 `team_ids()` / `TEAM_IDS`、球隊配色 `TEAM_COLORS` 在 `scripts/enrich_roster_viewer.py`；眼睛高度對齊 `scripts/headshot_eyeline.py` → `assets/players/headshot-eyeline.json`（可選用，有就用）。
- 球隊頁由 `scripts/build_teams_page.py` 產生，資料在 `data/season-source-2026-27/team-ratings.json`（rotation 有 `pid`）。

## 要做的
1. 主表每列隊名前加隊徽（約 24px，深色主題用 D 版、淺色用 L 版或照名單頁做法）。
2. 展開的今日輪替：每位球員名字前加圓形或裁切的小頭像（約 32–40px，桌面與手機都要整齊，不要撐高列高太多）。缺陣名單也加頭像（對不上 playerId 的人不放圖、不要破圖）。
3. 圖片全部用 CDN 外連，不把圖片放進 repo／gh-pages。失敗時不顯示破圖示。
4. 手機版（照名單頁手機寫法）確認不會橫向捲動。
5. 重建頁面並發到 gh-pages：`python -I scripts/daily_inseason_update.py --shell`（或 E-213 用過的對應發布方式），push 後立刻發。
6. 截圖：桌面一張（展開灰熊）、手機一張，存 `reports/E208-team-rating/site-shots/teams-avatars-{desktop,mobile}.png`。不要把整張大圖讀進 context（要看就縮圖或裁切）。

## 限制
- 只改 `scripts/build_teams_page.py`（必要時抽共用函式到 `scripts/site_header.py` 或新檔），不改 `src/`、名單頁行為、凍結檔。
- **共用工作樹**：禁止 `git stash`／`checkout`／`reset`／`restore`（L-115）；只 stage 自己的檔；`git diff --cached` 確認才 commit。要改的檔若有別人未 commit 的改動，停下回報。
- 不用 `HANDOFF_OK=1`；pre-commit 擋 handoff 時照 E-214 做法（HEAD 版改一行、update-index），不動工作樹別人的版本。
- 本機子程序不閃黑窗。
- `npm test` 要過；commit＋push。

## 回報
不是實驗結果，不用六段格式。回：改了什麼、頁面網址、截圖路徑、commit／gh-pages hash、偏離 spec 之處。
