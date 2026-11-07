# E-198 spec（role-card）

用 role-card skill。cwd `D:\Projects\CODING\basketball-autochess`。

## 要做什麼
照凍結的 `preregistration.md` 執行 E-198，不改預註冊（驗證：`git show HEAD:reports/card-0.2.10j+E198-gravity/preregistration.md | sha256sum` 要等於 `preregistration.sha256`；工作樹 CRLF 會不同）。

1. **c0**：用 `reports/card-0.2.10i/` 的建法（`build_0210i.py` 部件卡 → `run_i.py real` 用人層）在本目錄 `work/` 重建 KAU，ranking.csv 須與 `reports/card-0.2.10i/ranking.csv` 逐位元相同。不同就停下回報差在哪，不往下做。
2. **gravity 原始值**：讀 `reports/F126-shot-difficulty/gravity-split/gravity-2025-26.json`（`PLAYERID`、`AVGOFFBALLPERIMETERGRAVITYSCORE`）。缺值照預註冊 §1-2 用 OLS 補（3PA/36、3P%、USG%、位置啞變數；有值的人擬合），輸出 `gravity-raw.csv`（playerId、raw、imputed）。
3. **phase0**（跑 KG 前）：在 KAU 上算 h（全體對 2025-26 本季 RAPM Spearman 的 bootstrap 90% 半寬）與 A 線 MDE（接球射手組平均名次殘差的 bootstrap 90% 半寬），2000 次，seed 20261102；同時算價值殘差版（L-112）。寫 `phase0.md` 後才跑 KG。
   - 本季 RAPM：`reports/card-0.2.7+E126-tank-next-season/rapm-2025-26.json`（`players[pid].net`，poss≥1000）。RAPM 分半：若 repo 沒有現成單雙場分半，用 `reports/card-0.2.7+E126-tank-next-season/rapm_season.py` 同設定分單雙場重算（輕量；太重就到 5090）。
4. **KG**：加主效應屬性 `gravity`（0–99，池與 `to_attribute` 照 creation），其他全同 KAU，全部係數重擬合，**不設係數下限**。加屬性的寫法參考 E-181：`reports/E181-offball-attr/calibrate_wing_t.py` 的 `--offBallSource／--offBallCols`（複本放本目錄，不改原檔）。
5. 判定 A／沒弄壞與只報告項，全照預註冊 §2；薪水、EPM、2K27 的算法照 `reports/E142-card-target/phase1_eval.py`（`salary_terms`、`load_twok`；EPM 用 `data/external-impact/epm_self/epm_2025-26.csv`）。

## 限制
- 只寫 `reports/card-0.2.10j+E198-gravity/`（含 `work/`、`logs/`）。其他目錄唯讀；不改 `src/`、`scripts/`、網站、memory、`reports/card-0.2.10i/`、live/（另有 session 在用 `scripts/season_nav.py`、`TODO.md` 的未 commit 改動，不碰）。
- 不 commit、不 push（lead 審後處理）。
- 子程序一律 `creationflags=subprocess.CREATE_NO_WINDOW`、`stdin=DEVNULL`；長指令加 timeout。
- 看到結果後不改任何定義（L-026）。

## 驗收
- `npm test` 過（若失敗只來自他人 live 改動，寫明哪幾項、為什麼不是本實驗）。
- 產出：`gravity-raw.csv`、`phase0.md`、`results.json`、`report.md`、`work/KG-*/out/ranking.csv`、所有輸入 sha256（G2）。

## 回報（給 lead 的最後訊息）
照 CLAUDE.md 六段：第一行 `# 總評`（五級＋分數），再 **這次目標**、**進步了什麼**、**退步了什麼**、**直觀證據**（預註冊 §2 的 15 人表：KAU→KG 名次、OVR、gravity，補值的人標註）、**要你決定的事**。白話寫接球射手被低估少了多少、A 過不過；Δρ、區間只寫 report.md。另附一行：gravity 每 10 點 OVR 係數（±SE）。
