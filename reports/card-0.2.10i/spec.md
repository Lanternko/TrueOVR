# card／inseason 0.2.10i spec：切入與自主拆開上線（R-130、R-132）

用 role-card skill。cwd `D:\Projects\CODING\basketball-autochess`。使用者 2026-11-01 已核准上線（「上線」），不做預註冊回測（定義問題，R-130；給分不改，F-138）。

## 要做什麼
在**目前正式版**（`reports/ovr-inseason-2026-27/live/CURRENT.json`：card 0.2.10g／inseason 0.2.10h；開工先讀它的 note 全文，照裡面的換版規矩做）之上，只換兩個能力值的定義：
- **creation → creationJ**：E-190 errata-1（`reports/card-0.2.10c+E190-creation-jumper/errata-1.md`；程式 `extract_classes.py`、`creation_classes.py`、`build_creation_jumper.py`）：計入三分、>10 呎兩分、低位（hook／turnaround 等非 driving 的自主出手）；不計 10 呎內帶 driving 描述的兩分、補籃、tip、空中接力、空切。助攻加權照 build_drive.py。
- **drive → drive_D**：同 errata-1（`drive_chain.py`）：帶 driving 描述的兩分、排除二次進攻／快攻；量 0.5＋效率 0.5（R-130：不改成只看效率）。
- 兩欄都用現行 creation 的四季滑動窗口（window10／E-175 U 臂權重），池與 to_attribute 照現行 creation／drive。
- 卡片端：同 E-190 KJ 的做法，**全部係數重擬合**（同 0.2.10g 的旗標）。之後依 CURRENT note 重取用人層（build_usage）、OVR 映射錨點、3PT 池等凡是依卡片池重算的東西；照 L-109 重跑 `reports/E121-rookie-scale/build_2k_start.py` 重解新秀 δ。
- 賽中端：每天用本季逐球資料重算 creationJ、drive_D（找現有 live 逐球來源，例如 `live/pres_drive.py`）；若本季逐球資料沒有需要的描述欄位，**停下回報**，不要換定義。
- 開關：環境變數（例如 `SPLIT_DC=0`）重現 0.2.10g／0.2.10h，ranking.csv 逐位元組相同。
- 版號：照 R-109 判字母版或升版（看前 20 名進出、前 100 名移動 ≥10 名人數）；暫定 card 0.2.10i／inseason 0.2.10i。
- 網站：`scripts/season_nav.py` ATTR_TIPS 改 drive（「帶球切入到 10 呎內的自主兩分，量與效率各半」）、creation（「自己創造的跳投與低位出手（不含切入上籃、補籃、空切）per36」）；OFF 提示裡的貢獻欄依新係數更新；PATCH_NOTES 加一條（名次變動照現行寫法：0–2 個代表＋其餘收進 hover）。重建卡片頁與新賽季頁。

## 限制
- 另一個 session 也在同一個 checkout 發版：開工先 `git pull`；commit 只 stage 自己改的檔（不要 `git add -A`，別人 stage 的東西先看清楚，不要帶進去，L-047）；push 前再 pull。
- 子程序 `creationflags=subprocess.CREATE_NO_WINDOW`、`stdin=DEVNULL`；長指令 `</dev/null` 加 timeout；重算若超過本機輕量（多 seed、掃描）改到 5090。
- 不改 `src/` 模擬。不碰金鑰。

## 驗收（全過才發布）
- c0：開關關閉時 card ranking.csv 與 `reports/card-0.2.10g/ranking.csv`、賽中輸出與 0.2.10h 逐位元組相同。
- 新定義在 2025-26 卡片的 drive／creation 欄與 E-190 KJ 一致（窗口不同處寫明差異來源）。
- `npm test` 全過（含 live_current_gate、rookie_start_gate）；新版自檢腳本（仿 check_inseason_0210h.py）。
- CURRENT.json 更新、舊版建構腳本與凍結檔照規矩 git mv 到 `_retired/`。
- commit、push 後立刻發 gh-pages（不等每日排程），確認線上頁版號已變。
- memory：experiments 追加 E 條目（完成）、rulings 不用新增（R-132 lead 已寫）、handoff 一行；共用 checkout 只 stage 自己的段落。

## 回報（最後訊息）
CLAUDE.md 六段（第一行 `# 總評`）。直觀證據：前 25 名與 E-190 那 15 人的 0.2.10g→新版名次、OVR、drive、creation；前 100 名移動 ≥10 名人數；線上網址與版號。

## 接手筆記（第 1 輪未完成，2026-11-01，lead 整理）
- 已確認：2026-27 逐球有需要欄位（n 15416、driving 3137），不觸發停止條件。
- 已產出：`extract_j.py` → `work/history/crJ-{2022-23..2025-26}.csv.gz`（creationJ 歷史逐場計數）；可直接用，先抽查再用。
- 卡片端模板：E-190 KJU 臂（`reports/card-0.2.10c+E190-creation-jumper/work/tails/tail-KJ-U.csv`、`creation-KP-KJ.csv`、`drive-D.csv`）。窗口替換點：`live/window10.py` 的 `_creation_r`、`_past('creation','pool')`；tail-U 的產法見 `reports/card-0.2.12/make_tail_U.py`。
- 賽中端 drive 走凍結管線 `live/pres_drive.py`（v61／E-090／E-101），不是 window8：drive_D 要整條重建（歷史計數、Tv／Te 三季先驗、z 統計、E-101 合併池含 2022-23～2025-26 的 D 類 raw）。這是本單範圍內，卡片頁與新賽季頁要同一套定義（R-128），不拆兩次發布。
- 風險：E-190 是單季池、本版是四季窗口，值不同要寫明；drive past_pool 在 tail-U 路徑沒重算；SPLIT_DC=0 必須完全走舊路徑（不要混用現行 pu 與當季 pu），否則 c0 會壞。
- 順序建議：先卡片端（tail→重擬合→ranking c0 與新版）→ 賽中端 creation（window10）→ pres_drive D 類重建 → 用人層／錨點／3PT 池／新秀 δ → 自檢 → npm test → 發布。每完成一段在 `progress.md` 記一行，額度不夠時下一個人能接。
