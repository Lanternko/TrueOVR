# E-204 報告：四季窗口 328→246 格上線（inseason／card 0.2.12b，R-140）

# 總評
**4/5 大致達成 有部分退步**

**這次目標**：把「四季滑動窗口」從 328 格縮成 246 格（約三季）上線到兩頁（新賽季頁、2025-26 卡片頁）；形狀、每人正規化與下限、係數、錨點、r_repl、MPG 窗口都不動。

**進步了什麼**
- 新賽季頁老將 |ΔOVR| 中位數 0.77→0.80、變動超過 2 的老將 43→53 人（277 位老將）：本季比賽的權重加快，與 E-201 W246 臂同方向。
- 季末四項檢查：對 RAPM ρ 0.575→0.583、2K27 0.766→0.770、EPM 0.769→0.770（皆小幅變好或持平）。
- `WIN_LEN=328` 兩頁都逐位元重現開工時的線上版（新賽季頁 484 人、卡片頁 582 人，OVR 差 0.0）。

**退步了什麼**
- 對薪水 ρ 0.643→0.627（−0.016）；R-140 使用者已接受。
- 前 100 名有 15（新賽季頁）／14（卡片頁）人移動 ≥10 名；前 20 名新賽季頁換 2 人、卡片頁換 1 人（皆在字母版門檻內）。
- 前 12 名 |ΔOVR| 中位數 0.31→0.295，略降（頂端幾乎沒受影響，不是退步但沒進步）。

**直觀證據**（新賽季頁前 12 名，0.2.12a→0.2.12b；資料到 2026-10-31，只打 3–7 場）

| 球員 | 0.2.12a | 0.2.12b |
|---|---|---|
| Shai Gilgeous-Alexander | 106.1 | 106.3 |
| Nikola Jokić | 103.5 | 102.4 |
| Luka Dončić | 102.5 | 101.9 |
| Victor Wembanyama | 102.1 | 102.1 |
| Kawhi Leonard | 98.2 | 98.2 |
| Giannis Antetokounmpo | 97.4 | 97.3 |
| Donovan Mitchell | 97.0 | 96.3 |
| Stephen Curry | 95.7 | 95.7 |
| Kevin Durant | 95.2 | 95.0 |
| Jayson Tatum | 95.0 | 94.8 |
| Anthony Edwards | 94.4 | 94.6 |
| Austin Reaves | 94.0 | 93.9 |

- 新賽季頁前 20 名：出 Desmond Bane、De'Aaron Fox；進 Tyrese Maxey、Jimmy Butler III。
- 卡片頁（2025-26 季末）前 20 名：出 Paul George；進 Jimmy Butler III。前 12 名名次不動（Reaves 12→13）。

**要你決定的事**
1. 版號：我兩頁都標 0.2.12b（字母版，符合 R-064／R-109 門檻）。原先 0.2.12a 只用在新賽季頁（gravity），你要不要把卡片頁標 0.2.12a、新賽季頁標 0.2.12b？
2. `scripts/season_nav.py` 要等另一個 session 收手後照下列清單補（更新說明加一段、「四季」字樣改三季、卡片頁路徑指向新資料夾）；網站上更新說明還沒有 E-204 那一段。

---

## 做法與檔案
- `reports/ovr-inseason-2026-27/live/win_len.py`：`WIN_LEN`（預設 246），`install()` 在 `run_c4_live_rookie.py` 與 `scripts/attr_cell_tips.py` 載入時呼叫；`WIN_LEN=328` 什麼都不改。
  池、映射器、收縮先驗仍用 328 建好再切 246（同 E-201）；`window10.sums10` 四季項、`rookie_defense`（onBall／help／壓迫／切入／引力季權重）、`defense_bonus`（防守 D 重擬合時間軸）、`window8/10/11` 的 `L.WIN` 都跟著 WIN_LEN；`tv_past_pool`（3PT 對照池）固定 328。
- `reports/E204-window-246/card_route.py`＋`make_card.py`：用線上管線的「卡片路線」（2025-26 當本季、c=82）算季末，轉成卡片格式 → `reports/card-0.2.12b/`。WIN_LEN=328 與 `card-0.2.12-tov/ranking.csv` 逐欄數值相同（字串格式只差小數位數）。
- `reports/E204-window-246/eval_e204.py` → `results.json`：c0 重現、老將統計、名次移動、季末四項 ρ（人群與口徑同 E-201）。
- 版本指向：`run_c4_live.py`（VERSION／CARD_VERSION／WIN_LEN=328 回退）、`CURRENT.json`、`live/README.md`、`scripts/build_card_viewer.py`（改讀 `card-0.2.12b/`、提示卡「近三季」）、`scripts/build_inseason_viewer.py`（提示卡「近三季」）。
- usage／prior 檔不重取（係數、r_repl、錨點不動）：`load_usage` 對 `card-0.2.12b` 仍核對 `card-0.2.12-tov` 的 ranking sha。
- 新秀起點：重跑 `build_2k_start.py`（δ 與開工時相同，`rookie_start_gate` 過）。

## 偏離與假設
- 版號 0.2.12b 兩頁同標是我的假設（見上）。
- 卡片頁的 3PT（threeValue）欄與 gravity 欄沿用 0.2.12 的檔（顯示用／引力卡片值，不進 OVR）。
- 2025-26 卡片頁 onBall／help／壓迫／引力維持單季先驗值（E-201 護欄 B 同做法）。
- 最終一次完整重跑與先前 W246 試跑只差 Trevon Brazile（N=5）OVR 56.9→57.0：新卡 mpg 欄取自新卡片檔。

## `scripts/season_nav.py` 待辦（本次沒動，行號為 HEAD 09764e6／當時內容，補之前重新 grep）
1. ~line 100 註解「兩頁已是同一條四季窗口管線」→「兩頁已是同一條滑動窗口管線（0.2.12b 起三季）」。
2. ~line 108–110 `PATCH_NOTES` 的 0.2.12 條目（註解「# 0.2.12a（賽中端字母版…」）：加一行 `# 0.2.12b（R-140，E-204）：四季窗口 328→246 格`，並在 0.2.12 條目的白話清單加一句，建議：「新賽季本季比賽的權重加快，舊資料更快淡出：能力值窗口由四季改為約三季。」（`patch_notes_html` 用 `(\d+\.\d+\.\d+)` 比對版號，字母版仍會落到 0.2.12 條目）。
3. ~line 117 `'能力值與用人改看近四季滑動窗口：…'` → 「近三季滑動窗口」。
4. ~line 136 `'能力值改跨四季比較：偏弱的一季可以沒人到 99。'`：這是對照池（仍 4 季，328），不用改。
5. ~line 249 註解「新賽季頁用人層也改四季窗口」→ 補「（0.2.12b 起約三季）」。
6. ~line 783 `OD_CARD = … 'reports/card-0.2.12-tov/ranking.csv'` → `'reports/card-0.2.12b/ranking.csv'`（名單頁 OD 提示貢獻欄讀卡片 ranking）；註解加「0.2.12b：窗口 246」。
7. `ATTR_TIPS` 中若有「近四季」字樣一併改「近三季」（grep 後確認；本次 `git grep 四季 scripts/season_nav.py` 只有上列 4 處）。
