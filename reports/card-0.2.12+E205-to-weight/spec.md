# E-205 派工 spec（role-card）

讀 `preregistration.md`（凍結，sha256 在 `preregistration.sha256`），照它做；衝突時以預註冊為準，發現預註冊有錯就停下回報，不自己改。

## 步驟
1. **c0**：用 E-202 KT 流程（`reports/card-0.2.10j+E202-to-possession/` 的 `tov_raw.py`、`e202_common.py`、`build_kg.py`、`run_i.py`、`finalize.py`）重現 K12，`ranking.csv` sha256 要等於 29ca32eb65cfa40c465f9b8555912ae9829047cd87c497674d804f8f31f300a5。不等就停。權重做成參數（預設 0.5 重現 K12），不要改 E-202 目錄裡的檔，複製到本目錄再改。
2. **phase0**：K12 上算 VIF、Ball Handle ρ、RAPM ρ 與 bootstrap 90% 半寬 h、F-143 現值。寫 `phase0.json`、`phase0.md`，**commit 之後**才做第 3 步。
3. **KW**：權重 0.25 → `tov-raw.csv` → 換進 tail → 全部係數重擬合 → 用人層、r_repl、錨點、OVR 重算。
4. **評估**：`e205_eval.py` 算預註冊 §2 全部項目，寫 `results.json`、`report.md`（含「與預註冊不同或自行詮釋之處」段）。
5. `npm test`。

## 規則
- 只寫本目錄；`reports/` 被 gitignore，用 `git add -f`。只 commit 本目錄，用暫時 `GIT_INDEX_FILE` 組 tree（`git commit-tree`＋`git update-ref`），不要動共用 index，**不要 `git reset`、不要 `git add -A`**；別的 session 在 memory/、scripts/ 有未 commit 與已 stage 的改動。commit 後 push（push 前先 pull）。
- 子程序帶 `CREATE_NO_WINDOW`、`stdin=DEVNULL`；bootstrap 超過 10 分鐘改到 5090（`ssh kojiek@100.97.181.15`）。
- 看到 KW 結果之後不回頭改權重或定義（L-026）。

## 回報（給 lead）
CLAUDE.md 六段：`# 總評`（1–5）、**這次目標**、**進步了什麼**、**退步了什麼**、**直觀證據**（預註冊 §2 球員表）、**要你決定的事**。另列 A、保住 E-202、沒弄壞、B 各自數字與是否過；commit hash。
