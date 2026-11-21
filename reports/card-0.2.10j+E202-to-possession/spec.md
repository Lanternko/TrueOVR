# E-202 派工 spec（role-card）

讀 `preregistration.md`（凍結，sha256 在 `preregistration.sha256`），照它做；跟它衝突時以預註冊為準，發現預註冊有錯就停下回報，不自己改。

## 步驟
1. **c0**：用 E-198 KG 流程（`reports/card-0.2.10j+E198-gravity/build_kg.py`、`run_i.py`、`reports/card-0.2.10j/build_0210j.py`）重現 card 0.2.10j，`ranking.csv` sha256 要等於 `reports/card-0.2.10j/summary.json` 的 `ranking_csv_sha256`。不等就停。
2. **phase0**：在 K0 上算 (a) tovSkill 對 2K27 Ball Handle Spearman 與 bootstrap 90% 半寬（＝MDE）；(b) 全體 OVR 對 2025-26 RAPM Spearman 與半寬 h；(c) F-143 現值（應為 19/30）。寫 `phase0.json`、`phase0.md`，**commit 之後**才做第 3 步。
3. **KT**：新 tovSkill（預註冊 §1 第 1–7 點）→ 寫 `tov-raw.csv`（每人 r、v、raw、tovSkill、topMissing）→ 換進 tail（同 E-198 換 gravity 的方式）→ 全部係數重擬合 → 用人層、r_repl、錨點、OVR 重算。
4. **評估**：`e202_eval.py` 算預註冊 §2 全部項目，寫 `results.json`、`report.md`。
5. `npm test`。

## 規則
- 只寫本目錄；`reports/` 被 gitignore，用 `git add -f`。只 commit 本目錄，不碰 memory/ 和其他人的改動。
- 跑子程序的 Python 要帶 `CREATE_NO_WINDOW`（使用者正在用電腦）；bootstrap 若超過 10 分鐘改到 5090。
- 不看 KT 結果之後回頭改定義或池（L-026）。

## 回報（給 lead）
照 CLAUDE.md 六段：`# 總評`（1–5 分）、**這次目標**、**進步了什麼**、**退步了什麼**、**直觀證據**（預註冊 §2 的球員表，K0→KT）、**要你決定的事**。另外列：A、沒弄壞、B 各自數字與是否過；commit hash。Δρ、區間放 report.md。
