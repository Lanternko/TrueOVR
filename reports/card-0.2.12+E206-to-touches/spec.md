# E-206 派工 spec（role-card）

讀 `preregistration.md`（凍結，sha256 在 `preregistration.sha256`），照它做；衝突時以預註冊為準，發現預註冊有錯就停下回報，不自己改。

## 步驟
1. **c0**：以 E-205 的參數化流程（`reports/card-0.2.12+E205-to-weight/`）為底，複製到本目錄再改；權重 0.5、分母持球分鐘時要重現 K12 `ranking.csv` sha256 29ca32eb65cfa40c465f9b8555912ae9829047cd87c497674d804f8f31f300a5。不等就停。分母做成參數（預設持球分鐘）。
2. **phase0**：K12 上算 A 的 ρ（tovSkill vs AVG_SEC_PER_TOUCH，持球者子群）與 bootstrap 90% 半寬 MDE_A；Ball Handle ρ；RAPM ρ 與 h；F-143；VIF；換算係數 ρ。寫 `phase0.json`、`phase0.md`，**commit 之後**才做第 3 步。
3. **KC**：觸球分母 → `tov-raw.csv` → 換進 tail → 全部係數重擬合 → 用人層、r_repl、錨點、OVR 重算。
4. **評估**：`e206_eval.py` 算預註冊 §2 全部項目，寫 `results.json`、`report.md`（含「與預註冊不同或自行詮釋之處」段）。
5. `npm test`。

## 規則
- 只寫本目錄；`reports/` 被 gitignore，用 `git add -f`。只 commit 本目錄：暫時 `GIT_INDEX_FILE`（`git read-tree HEAD`）＋`git commit-tree`＋`git update-ref`；commit 後只跑 `git reset -q HEAD -- reports/card-0.2.12+E206-to-touches`。**不要其他形式的 `git reset`、`git add -A`、`git stash`、`git checkout -- <別人的檔>`**；共用 index 常和 HEAD 不同步，絕不用一般 `git commit`。push 前 `git fetch` 確認可 fast-forward。
- 子程序帶 `CREATE_NO_WINDOW`、`stdin=DEVNULL`；bootstrap 超過 10 分鐘改到 5090（`ssh kojiek@100.97.181.15`）。
- 看到 KC 結果之後不回頭改定義（L-026）。

## 回報（給 lead）
CLAUDE.md 六段：`# 總評`（1–5）、**這次目標**、**進步了什麼**、**退步了什麼**、**直觀證據**（預註冊 §2 球員表）、**要你決定的事**。另列 A、保住 E-202、沒弄壞、B 各自數字與是否過；commit hash。
