# card／inseason 0.2.9a（R-107，E-164 S 臂採用）

版本規則：前 20 名無進出、前 100 名移動 >=10 名 23 人，照 R-109（2026-11-01 字母版門檻改看前 100 名 ≤25 人）屬字母版 0.2.9a。
RAPM 窗：T6 目標（DARKO＋BPM 季內 z 平均）；資料 sha256 見 summary.json（ranking-S-2025-26.csv b7972182…7580ef）。

## 驗收
| 項目 | 指令 / 證據 | 結果 |
|---|---|---|
| c0 排名逐格 | `build_card_029a.py`（對 E-164 `ranking-S-2025-26.csv`，sha256 相同） | 過 |
| u1 能力值欄 | 同腳本，ATTR_COLS 對 card 0.2.9 | 過（含 stamina 顯示值） |
| 用人層重建 | `live/build_usage_029a.py`（ovr 1 位、mpg 2 位、gRepl 4 位） | 582 人 0 不符 |
| 包裝可載入 | `run_c4_live_rookie.py data/_scratch_029a`（logs/wrapper_run.log） | exit 0，442 人有排名；pointwiseCheck 1e-11；lastOVR 對正式卡 442 人最大差 0.1（四捨五入） |
| 直接執行被擋 | `python -I -X utf8 live/run_c4_live.py` | exit 1，訊息指向 rookie 包裝 |
| 舊 CARD_MODE | `test/live_current_gate.py`（029／028／027b 皆失敗） | 過 |
| G1 | `npm test`（logs/npm_test.log，含新閘門） | 52/0＋計時賽過＋閘門 4 項過；`test/daily_inseason_update.py` 10 項過 |
| audit.ps1 | FAIL=0 WARN=2 | 過 |

## 最新資料（截止 2026-10-30）新賽季 0.2.9a 對 live/2026-10-30（0.2.9）
| 球員 | 0.2.9 名次／OVR | 0.2.9a 名次／OVR |
|---|---|---|
| Jalen Williams | 8／90.3 | 8／90.5 |
| Jokić | 9／90.2 | 9／89.4 |
| Chet Holmgren | 16／87.2 | 12／88.1 |
| SGA | 1／114.9 | 1／115.6 |
| Wembanyama | 2／108.4 | 2／108.3 |

2025-26 正式卡（MIN>=500 名次）：Jalen Williams 17→10、Chet 16→11、Jokić 6→7、SGA 1、Wemby 2。

## 淘汰舊路徑
- `run_c4_live.py`：`CARD_MODE` 只收 `029a`；`STAMINA_FREEZE` 與程式移除；`__main__` 直接 SystemExit。
- 搬到 `live/_retired/`（24 檔，.py 頂端 SystemExit 守門）：build_prior_012/022/026/027、build_usage_024/026/027/027b/027d/028/029、pool-026/027、prior-…card012/022/026/027、usage-…card024/026/027/027b/027d/028/029。
- 留在頂層：CURRENT.json 所列（build_usage_029a、usage-…card029a、build_prior_027b、prior-…card027b、pool-027b）。
- 閘門：`test/live_current_gate.py`（接在 `npm test` 後）。
- 殘留：run_c4_live.py 內舊版本分支成為死碼（不會被觸發）；舊實驗目錄（E-107/111/128/116 等）的腳本仍引用舊檔名，重現請 checkout 當時 commit。

## 死碼清理

`reports/ovr-inseason-2026-27/live/run_c4_live.py` 刪掉舊版（CARD_MODE 非 029a）的分支與常數，1302 行 → 1137 行（-165）。CARD_MODE 仍只接受 029a；M27_MODE／M26_MODE／USAGE_MODE／SAT 相容旗標保留為 True（rookie 包裝檔會斷言、歷史腳本讀得到）；`run_c4_live_rookie.py` 做文字替換的行與 E-107／E-111 標記區塊原樣保留。

驗證：同一 HEAD 下，用清理前後的 run_c4_live.py 各跑一次 `run_c4_live_rookie.py`，6 個輸出檔全部一致：ranking.csv、no-prior.csv、pres-drive.json、rookies-detail.json、README.md 的 sha256 完全相同；meta.json 逐鍵相同（只有 JSON 鍵順序因雜湊隨機化不同，排序後一致）。`npm test` 52 passed 0 failed（`logs/dead-code-npm-test.log`），live_current_gate 通過；直接執行 run_c4_live.py 與 `CARD_MODE=029` 仍以非零結束。
