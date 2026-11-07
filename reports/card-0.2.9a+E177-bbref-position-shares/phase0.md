# E-177 第 0 階段：0.2.9a 管線（E-164 S 臂）所有讀位置標籤的地方

管線：`e164_build.py`（S 臂＝--dropAttr stamina）→ `e153_build.py` → E142 `build_card_t.py` → stage1 → `calibrate_wing_t.py`（primary／fitA／fitB 三張部分卡）；Y0 用人層走 E-162 `e162_build.py`。
結論先講：**位置標籤只在 `reports/card-0.2.9+E164-no-stamina/calibrate_wing_t.py` 一個檔案裡被讀**，來源是目標 CSV 的 `position` 欄（`calibrate_wing_t.py:97` → `rows[i]['pos']`）。E-082 的三處都對得上，沒有 E-082 沒有的用處（用人層、mpg、映射錨、r_repl 都不讀 pos）。

## A. 改成比例的三處（對應 E-082 三處）
| # | E-082 的處 | 0.2.9a 管線位置（`calibrate_wing_t.py`） | E-177 改法 |
|---|---|---|---|
| 1 | 位置交互項 | `design()` 276–279：`d = 1[r['pos']==p]`，p∈POS[:-1]（PG..PF），乘 INTERACT 屬性（z 分數） | `d = pi_p`（比例） |
| 2 | r 置中（RAPM 混合） | `attach_rapm()` 173–178：每個 pos 內 MIN 加權平均 μ_pos，`r = 36·N − μ_pos`（poss ≥ BLEND_POSS） | `r = 36·N − Σ_p pi_p·μ_p`，μ_p＝以 pi_p·MIN 加權的平均 |
| 3 | 防守加成置中 posMeanD | `pos_mean_d_window()` 347–349（窗口版，用 Dw/possW）、`pos_mean_d()` 358–362（用 D/poss）；使用處 517、520 `centeredD = 36·D − posMeanD[r['pos']]`；摘要輸出 619 `posMeanD` | 同 #2 的比例加權平均；`centeredD = 36·D − Σ pi_p·posMeanD_p` |

## B. 讀 pos 但**維持硬標籤不動**（列出就好）
| 位置 | 內容 | 為什麼不動 |
|---|---|---|
| `calibrate_wing_t.py:97` | 從目標 CSV 讀 `position` 欄存入 `rows[i]['pos']` | 這是標籤來源；P 臂的 one-hot 退回（無 BBRef 列、MP<200、和為 0）也用它 |
| `calibrate_wing_t.py:406、408、416、418、632、635` | 把 pos 寫進 `pred.csv`／`ranking.csv` 的 `pos` 欄 | 只是輸出欄位，不進計算；P 臂的 ranking.csv 仍寫現行標籤，比例另存 `pos-shares-used.csv` |
| `calibrate_wing_t.py:531–532` | `--restrictPos`（G 系列 sanity check 用，`489` 行斷言正式建卡不得使用） | 正式管線 restrict_pos=None，不啟用 |
| `calibrate_wing_t.py:70` | `BLEND_FORM='position-interactions'` 常數 | 只是名稱 |
| `reports/card-0.2.7d+E153-t6-target/e153_build.py:44–46` | 寫 target-dummy.csv 時複製 B12 的 `position` 欄 | 只是搬運欄位 |
| `e164_eval.py`、`e162_eval.py`（96–101／122） | 評估報表列「前十長人」依 pos 篩 C／PF | 評估用，不是建卡 |
| `eval_v2.py`、`e164_build.py`、`e162_build.py`、E142 `build_card_t.py`、stage1 | 無 pos／position 讀取（grep 確認） | — |

## C. 不讀 pos（確認）
用人層（Y0／E-162）、mpg、映射錨、r_repl、能力值（`season_nav.off_def` 在管線之外）都不讀位置；賽中管線與名單頁不在本實驗範圍。

## D. 方法備註
- 指令：`grep -nE "\bpos\b|'pos'|\"pos\"|position"` 掃 E164／E162／E153／E142 目錄與 `scripts/build_card_029a.py`；其餘 `pos` 命中都是別的意思（評估程式的 index 字典 `pos = {...}`）。
- 目標 CSV 的 `position` 欄是歷史原點與 2025-26 目標檔既有的標籤（先發登錄多數位置，F-033）；本實驗沒有重追這欄是怎麼產生的，只在 P 臂以 BBRef 比例取代其用處 A1–A3。
- 與 E-082 差異：E-082 的比例是先發登錄比例，這裡是 BBRef 上場位置估計；E-082 為 0.2.3 底，這裡為 0.2.9a 底。
