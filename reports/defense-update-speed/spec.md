# 賽中防守更新速度回測 spec（role-card，預註冊回測）

lead：Claude Code App，2026-11-02。使用者選「1：做回測」。

## 起因
- 76 人本季 7 場，失分效率聯盟第 3，對手兩分命中率第 4。模型的 DRtg 卻是比平均差 1 分（`data/season-source-2026-27/team-ratings.json`）。
- 使用者觀察：Maxey 貼身施壓、LeBron 大小都能換。他懷疑防守值更新得太慢。
- 更正 App 的說法：App 先前看 live `meta.json` 的 `frozenAttrs`，跟使用者說防守「整季凍結」。這是錯的。依 R-076，老將的 onBall／help 用四季逐場遞減窗口，本季資料也在裡面，只是開季時本季權重很小；只有 physique 真的凍結。請把這件事追加成 lesson（L 檔尾最大號 +1）：判斷屬性是否凍結，要看 R-076 與 `run_c4_live_rookie.py` 的實際路徑，不能看 meta 的 frozenAttrs。
- 問題：開季前段若讓本季防守資料權重變大，對球隊之後防守的預測會不會更準？

## 第 0 步：可行性（先做，不通過就停下回報）
1. 找出老將 onBall／help 窗口實際怎麼算，並報告 2026-11-01 時本季在窗口裡的有效權重，以 76 人主力為例。
   - 檔案：`reports/ovr-inseason-2026-27/live/rookie_defense.py`、`run_c4_live_rookie.py`、`scripts/fetch_defense_tracking.mjs`。
2. 歷史季能否重建「開季第 N 場時」的防守追蹤表？例如 stats.nba.com 的追蹤端點帶 `DateTo` 抓截至某日的累計。
   - 先在本機試抓一個日期確認可行，再決定要不要批次抓。
   - 抓不到就停下回報，不要拿季總計代替。

## 設計（跑前寫 `preregistration.md`＋`.sha256` 並 commit，之後不得改；L-026）
- **季**：
  - 2024-25 是主檢定，樣本外。
  - 2025-26 是同向確認，部分污染。
  - 每季都在每隊打完第 10 場、第 20 場時各做一次快照。
- **臂**（只改老將 onBall／help 窗口裡本季的權重，其他照 R-076 現行管線；常數在跑前寫死，不看結果調）：
  - A0：現行。
  - A1：本季權重 ×2。
  - A2：本季權重 ×4。
  - 防守加成（DIQ）跟著同一組窗口值重算。
- **主目標**：快照之後該隊剩餘賽季的實際 DRtg，扣聯盟平均。
  - 模型 DRtg 用 E-208 的組隊方式：快照日 (c) 分鐘的輪替，對平均隊打。
  - 每隊每臂 ≥200 seed（換主客），同一隊各臂共用 seed（G3）。
  - 檔案在 `reports/E208-team-rating/`，先讀 `report.md`、`report-2024-25.md`。
- **主檢定 H1**：A1 或 A2 剩餘賽季 DRtg 的 MAE 比 A0 小。
  - 2024-25 的 MAE 差值，90% bootstrap CI（以隊重抽，5000 次）不含 0。
  - 2025-26 同方向。
  - 兩臂都測，算兩次比較；預註冊寫明怎麼處理多重比較。
- **次要**：
  - 屬性層：快照時的 onBall／help 對「剩餘賽季累計追蹤表算出的值」的 MAE。
  - 也報第 10 場、第 20 場分開的結果。
- **描述**（不當證據）：2026-27 截至最新資料，76 人在各臂下的 DRtg 與主力 onBall／help。使用者要知道 Maxey、LeBron 在快一點的更新下會變成多少。

## 運算
多 seed 模擬放 5090：`ssh kojiek@100.97.181.15`，長指令加 `</dev/null` 與 timeout。本機只跑輕量。

## 限制
- 不改 `src/`、引擎係數、正式卡、凍結檔、E-208 既有結果；新檔全放 `reports/defense-update-speed/`。
- 不改線上每日管線。通過與否都只回報，採用由使用者決定（G5）。
- 共用工作樹：
  - 禁止 `git stash`／`checkout`／`reset`／`restore`（L-115）。
  - 只 stage 自己的檔；`reports/` 用 `git add -f`。
- 不用 `HANDOFF_OK=1`；pre-commit 擋 handoff 照 E-214 做法（HEAD 版改一行＋update-index；8192 bytes 上限，超過就縮自己那行）。
- 子程序不閃黑窗（`CREATE_NO_WINDOW`）。
- 記錄 G2：引擎版本、卡版本、輸入 sha256。

## 收尾
- `report.md`：查證過程、CI、雜湊寫這裡。
- `memory/experiments.md` 追加新 ID（檔尾最大號 +1）；lesson 如上。
- `npm test` 過；commit＋push。
- 回覆用 CLAUDE.md「回報實驗結果」六段格式（第一行 `# 總評`）。第 0 步停下時不用六段，直接說卡在哪、有什麼替代方案。
