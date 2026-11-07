# E-183 第 0 階段：K0h 的 pass 從哪來、Q 怎麼對應

預註冊 sha256 = fa7d5de97a737e4d5d18c83feb92da075baef3c833f2ee4f2a779f500c0716ff（開工時核對，與 `preregistration.sha256` 一致；`e183_eval.py` 每次執行再核對）。

## K0（0.2.9a）的 pass 路徑
1. 建卡時 `calibrate_wing_t.py --tailSource`（`run_t.py` 的 `SRC['tail']`）＝ `reports/card-0.2.7+E123-tail-3pt-rim-pres/rebase-027a/work/tail-e123a.csv`，用 playerId 覆蓋 13 個能力值，**四個原點（2022-23…2025-26）共用同一個檔**。
2. 該檔 pass 欄與 E-125 `attributes-P50.csv` 的 pass 欄逐位元相同（582 人 0 列不同；兩檔只差 pressure 欄 576 列）。
3. P50 的 pass＝每季 0.5·zs(AST/36 收縮)＋0.5·zs(AST/astCh 收縮)，四季（2022-23、2023-24、2024-25 由 `pool_data_p.py` 算，2025-26 由 `a0_p.py` 用卡片位置算）合併成池，每人的**卡片值＝2025-26 那一季的分數**在四季合併池上的百分位（含頂端尺 S）。
4. 結論（L-091）：K0h（2022-23／2023-24／2024-25 原點）的 pass 不是原點當季的助攻資料，而是 **2025-26 的現值**（池本身含四季，但每人只取 2025-26 的分數）。

## Q 的對應換法
- Q 的 pass 欄＝同一條路徑，只把每一季「率那一半」從收縮 AST/astCh 換成 conv_s（收縮 AST/PASSES_MADE）；量那一半（AST/36）、zs 池（GP≥30 且 MPG≥20）、四季合併池、頂端尺、`tail` 檔的其他 12 欄全部不動。
- 所以 Qh（各歷史原點）的 pass＝2025-26 的 conv_s 現值，用 2025-26 的追蹤資料（`handle-E069/raw/2025-26/Passing-FULL.json`）；和 K0h 用 2025-26 助攻資料同一季，**換法一致**，不用停。四季合併池裡 2022-23／2023-24／2024-25 的分數用各自那季的追蹤資料。
- 實作：`work/pipe/`（原始碼已複製到 `pipe-src/`）是 E-125 `work/` 的複本，只加 `conv.py` 與環境變數 `E183_CONV=1`（`pool_data_p.py`、`a0_p.py` 各加一段；`build_e101_p.py` 只改路徑與 TAG）。重現檢查：`E183_CONV` 不設時跑出的 `attributes-P50.csv` 與 E-125 原檔逐位元相同（`cmp` 無差異）。
- `tail-Q.csv`＝`tail-e123a.csv` 只把 pass 欄換成 `attributes-Q.csv` 的 pass（其餘 12 個能力值欄逐位元不變，檢查見 results.json）。
- 實作時需補的小決定（預註冊沒寫死，取最保守）：
  - k 的動差擬合：照 `build_season_league.js` 的 `fitShootingEB`（qualified＝PASSES_MADE≥200；pbar＝AST 總和／PASSES_MADE 總和；varRate＝母體變異 ddof=0；meanInvN＝1/n 平均）。
  - μ_pos 的位置：2025-26 用卡片硬標籤（`a0_p.py` 的 `pos_card`）；2022-23…2024-25 用 `E.pos_lookup(pos_by, p, s)`（該季位置，與原 AST/astCh 收縮同一個 `pos`），因為歷史季的球員多半沒有卡片標籤。
  - μ_pos 只用「在該季名單內且對得到追蹤資料」的人；位置組沒人時退回 pbar（實際未發生）。
  - 追蹤資料一季多列（換隊）時 PASSES_MADE、AST 各自加總（2025-26 的 Passing-FULL 每人一列，已檢查）。
