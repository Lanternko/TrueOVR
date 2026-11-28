# E-125 預註冊：傳球（pass）改成量率各半（AST/36 ＋ AST%）

- 日期：2026-10-30。來源：使用者問 Giannis 場均只有 5 次助攻為什麼傳球 97.7；lead 診斷後使用者裁定 R-074：「same as 3pt, we need to mix ast and ast%」，權重選 0.5／0.5，範圍選卡片＋OVR。
- 版本：`card 0.2.7+E125`（R-018）。基準：正式卡 card 0.2.7（R-065，`reports/card-0.2.7/ranking.csv`，sha256 aebcadf1c3dfcbe6aaeed8c34fa5183cd35dbda546dd967faa5ebdf6649cc6b6）。
- git HEAD（寫本檔時）：ce6439e。角色：實作 role-card；判讀 lead；稽核 role-audit。本機可跑（同 E-107）。
- 狀態：凍結（2026-10-30，使用者「凍結開跑」）。sha256 記在 `preregistration.sha256` 與 `memory/experiments.md` E-125。§2.2 改成凍結後第一步：P0 的 c0a、c0 過了才准跑 P50。

## 0. 背景與假設

### 現況
- card 0.2.7 的 pass 最後一次寫入來自 E-101 tail（`reports/card-0.2.6+E107-defense-UL/run_cards.py:23` 的 `--tailSource reports/card-0.2.5+E101-crossera/attributes-e101.csv`，`calibrate-wing.py` 的 `attach_tail`）。
- 定義：AST / astCh（逐場算的可助攻機會，分母同官方 AST%，`reports/ovr-v61-shrink-history-2025-26/engine.py:7-9,92`），E-055 方法 (c) 收縮（`reports/card-0.2.5+E101-crossera/work/pool_data.py:95-99`），2022-23～2025-26 四季合併池算百分位（R-056，`build_e101.py:177-185`），頂端尺 S＝max((r99−r90)/1.044, SD_pool)（`build_e101.py:83-88`）。
- 只看率不看量：吃球權多的人在場時隊友進球少，分母小，AST% 偏高。

### 改動（候選只有一個）
- 每季 pass 原始值改成 comp＝0.5·zs(vol)＋0.5·zs(rate)：
  - rate＝現行收縮後 AST/astCh（不改）。
  - vol＝AST／(MIN/36)，用 E-055 方法 (c) 收縮。k、λ、kh 用 E-070 `vol-fit.json` 的同一套擬合程序（`reports/card-0.2.0+E070-foul-volume/e070_vol.py` 的 `E.fit_attr`，同擬合季、同 MIN_D2、同位置先驗）對 AST 重擬合一次，存 `work/astvol-fit.json`；擬合只用擬合季，不看 2025-26 結果。
  - zs(x)＝(x − x[池].mean())／x[池].std()（ddof=0），池＝該季 GP ≥ 30 且 MPG ≥ 20（同 `pool_data.py:107-108` foulDraw 寫法）。
- 寫法照 foulDraw w075（`pool_data.py:104-110`）：每季（2022-23、2023-24、2024-25 與 2025-26）都換，然後照 E-101 原流程重算四季合併百分位、r99／r90／S 錨點與頂端尾巴。
- pass 是否走頂端尾巴（`build_e101.py:240` 的 `passed(H1,'pass','top')`）**沿用 card 0.2.7 的結果，不重跑 H1**。
- 其他 12 個 tail 屬性逐位元不動；`creation` 不讀 pass（`pool_data.py:148`），不動。

### 假設
- H1（沒弄壞）：pass 換成量率各半之後，樣本外排序一致性（m1–m3）不明顯變差。
- 不設任何球員名次目標（不寫「Giannis 要掉到第幾」），避免看答案挑參數（L-026）。

### lead 事前預期（看結果前寫）
- 高使用率、助攻量普通的人（Giannis、Embiid 類）pass 下降；Haliburton、Trae Young 這種量大的持球者不變或上升。
- pass 在 OVR 迴歸的權重不大、又和 creation 相關，預期 m1 點估計接近 0。

## 1. lead 已看過的（揭露）
- card 0.2.7 全部欄位（含 Giannis pass 97.7）。
- `data/benchmark-source` 2025-26 常規池（GP ≥ 30、MPG ≥ 20，252 人）的官方 AST_PCT 前 15 名，以及他們的場均分鐘、場均助攻、AST/36（Jokić 11.1、Giannis 6.8 等）。
- **沒看過**任何 comp、新 pass、OVR、名次或 Δρ。
- 不是盲測：方向是看過 Giannis 之後才選的（L-026），權重是使用者的語意裁定（R-074），不是調出來的。m1–m3 只證明「沒變差」；採用時版號 PATCH（card 0.2.8），除非使用者另有裁定。

## 2. 做法

### 2.1 程式（新目錄 `reports/card-0.2.7+E125-pass-volume/`）
- `work/pool_data_p.py`、`work/build_e101_p.py`、`work/a0_p.py`：由 E-101 `work/` 的同名檔複製。只加一個選項 `w_vol`（預設 0）：pass 的每季值與 2025-26 值改成 `w_vol·zs(vol) + (1−w_vol)·zs(rate)`。**w_vol=0 時一律直接用原 rate 值**，不做 zs 轉換，才能逐位元重現。其他一字不改，diff 存 `diff-e101.txt`。
- 組別：`P0`（w_vol=0，基準）、`P50`（w_vol=0.5，候選）。各輸出一份 `attributes-P0.csv`、`attributes-P50.csv`（格式同 `attributes-e101.csv`）。
- 卡片：由 E-107 `run_cards.py` 複製成 `run_cards_p.py`，只把 `--tailSource` 改指上面的檔案，其他旗標＝UL6 原樣，產 `cards/{P0,P50}/{primary,fitA,fitB}`。
- 名次與 m1–m3：由 E-107 `e107.py` 複製成 `e125.py`，唯讀匯入 `reports/card-0.2.5+E094-defense-ceiling/e094.py`，選項＝UL6 原樣；候選和基準共用同一組抽樣。
- `evaluate.mjs`：由 E-107 的複製，候選換成 E125-P0、E125-P50。
- 子程序帶 `creationflags=subprocess.CREATE_NO_WINDOW`。

### 2.2 凍結前先跑（L-063）
- role-card 先只跑 P0 與 vol 擬合（`astvol-fit.json`），回報 (c0)、(c0a) 與擬合係數給 lead。**P50 一行都不准跑**，等凍結後才跑。

## 3. 判定

### 硬條件（沒過就停下回報，不自己修）
| 代號 | 內容 | 門檻 |
|---|---|---|
| c0a | `attributes-P0.csv` | 和 `reports/card-0.2.5+E101-crossera/attributes-e101.csv` 逐位元相同 |
| c0 | P0 輸出的 ranking | 和 `reports/card-0.2.7/ranking.csv` 逐位元相同（sha256 aebcadf1…c6b6） |
| c1 | `npm test` | 全過 |
| u1 | P50 的 attributes | 除了 pass 欄，其他欄和 P0 逐位元相同 |

### 對 P0（照 R-042 權衡，不機械否決）
- 門檻同 E-107／E-124：
  - (m1) Δρ_{N_W} 90% 區間下界 > −0.02
  - (m2) Δρ_{Q_W} 90% 區間下界 > −0.05
  - (m3) Δρ_{N_lin} 90% 區間下界 > −0.05
- (p1) 新 pass 相鄰季 Spearman ≥ 0.70（同 E-071 p1；池＝相鄰兩季都在常規池的人）。
- 沒過：照實記錄是哪一條、差多少，交使用者；不准因此改權重、收縮、人群、門檻再試。

### G4 與版號（R-019）
- 前 20 名對 card 0.2.7 換掉超過 3 人時，m1–m3 就當作 G4 重跑（A／B 分半樣本外）。
- 採用時版號 PATCH（card 0.2.8），理由見 §1。新賽季頁不跟著改，要跟上另走 inseason 實驗（R-050）。

### 只報告
- evaluate.mjs 19 道門檻（card 0.2.7 是 18/19），照跑；前十長人（R-002 名單）。
- `astvol-fit.json` 的 k、λ、kh；vol 收縮前後的下半季 MAE（同 E-070 寫法）。
- 具名球員 pass、OVR 與名次（P0 → P50），並列 AST/36、AST%：
  - Giannis Antetokounmpo、Joel Embiid、Nikola Jokić、Luka Dončić、James Harden、Tyrese Haliburton、Trae Young、Cade Cunningham、Josh Giddey、LaMelo Ball、Isaiah Collier、Stephon Castle、Draymond Green、Domantas Sabonis、Shai Gilgeous-Alexander、Cam Spencer
- pass 前 20 名換了誰；pass 名次移動 ≥ 30 名的人數與名單（MIN ≥ 1000）。
- OVR 前 20 名換了誰；OVR 名次移動 ≥ 10 名的人數；OVR 錨點 PR1／PR50／PR99；對 2K27 的 ρ。
- 模擬端：P0 → P50 的 simulatedPer36 變化（全體中位、最大的 10 人）。

### 選不選
- 使用者在 G5 決定採用（發 card 0.2.8）或不採用。採用的不能稱盲測通過（L-026）。

## 4. 不准做的事
- 不改 w_vol=0.5 以外的任何東西：rate 定義、其他屬性、四季池、S 錨點算法、H1 頂端判定、OVR 迴歸、用人回歸、防守 UL、POOL_MIN。
- 不加第三組（例如 0.75／0.25、改用 potential assists）。要做另寫預註冊。
- 跑前跑後 sha256 唯讀核對（L-037）：
  - `reports/card-0.2.7/`
  - `reports/card-0.2.6+E107-defense-UL/`
  - `reports/card-0.2.5+E094-defense-ceiling/`
  - `reports/card-0.2.5+E101-crossera/`
  - `reports/card-0.2.0+E070-foul-volume/`
  - `reports/ovr-v61-shrink-history-2025-26/`
  - `reports/impact-rapm/`
  - `data/`
- 不碰 `reports/card-0.2.7+E123-tail-3pt-rim-pres/`、`reports/card-0.2.7+E124-no-young-tank-discount/`（其他 session 執行中）。
- 不改 `src/`、live/、名單頁、狀態板、memory/（memory 由 lead 收工寫）。不部署、不 commit、不 push。

## 5. 回報
- CLAUDE.md 六段（`# 總評` 開頭）；Δρ、區間、閘門代號放第 6 段之後。
- 報告正文寫成 `report.json` 或 `report.txt`（L-055），附 `results.json`、`ranking.csv`（P0、P50 並列）、`diff-e101.txt`、`astvol-fit.json`、唯讀核對 json。
- lead 寫 `report.md` 前，從 results.json 重算關鍵數字（L-065）。
