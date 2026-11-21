# E-190 spec（role-card）

用 role-card skill。cwd `D:\Projects\CODING\basketball-autochess`。

## 要做什麼
照凍結的 `preregistration.md`（sha256 00ae636e…；驗證用 `git show HEAD:reports/card-0.2.10c+E190-creation-jumper/preregistration.md | sha256sum`，工作樹 CRLF 會不同）執行 E-190，不改預註冊。

1. **c0**：用 `reports/card-0.2.10a+E187-rebase/run_all.py` 臂 KAU 重建 2025-26 與三歷史原點（2022-23、2023-24、2024-25），2025-26 ranking.csv 須與 `reports/card-0.2.10c/ranking.csv` 逐位元相同（sha e46315bd…158b）。不同就停下回報，不往下做。
2. **creationJ 程式**：寫在本目錄（例如 `build_creation_jumper.py`）。逐球載入與助攻加權照抄 `reports/ovr-v60-drive-split-2025-26/build_drive.py`；先用同一套程式算「舊定義 creation」（全部出手）並和各原點 tail 屬性的 creation 欄比，差 <1e-6 才算 c0 過（若舊欄來源不是逐球、根本無法重現，停下回報差多少與原因，不自行換定義）。再算 creationJ（只計三分＋>10 呎兩分），窗口、池、to_attribute 照舊 creation。
3. **phase0**（看 KJ 前）：在 KAU 上算 h_R（下季 RAPM 名次 ρ 三季合併的球員層 bootstrap 90% 半寬，2000 次，seed 20261101）與 a2 用的 KAU Spearman(drive, 殘差)，寫 `phase0.md` 後才跑 KJ。殘差算法同 `reports/E173-pressure-vs-rapm/`（F-109）。
4. **KJ**：只換 creation→creationJ，四原點全部係數重擬合（同 KAU 的旗標，含 `--dropInteract pass`）。
5. 判定 a1／a2／b 與只報告項，全照預註冊 §2。

## 限制
- 只寫 `reports/card-0.2.10c+E190-creation-jumper/`（含 `work/`、`logs/`）。其他目錄唯讀；不改 `src/`、`scripts/`、網站、memory、`reports/card-0.2.10c/`、`reports/card-0.2.10d*`／`0.2.10e*`、`status_snapshot.py`、`build_card_viewer.py`、`live/`（另一個 session 在用）。
- 不 commit、不 push（lead 會審後處理）。
- 子程序一律 `creationflags=subprocess.CREATE_NO_WINDOW`、`stdin=DEVNULL`；長指令加 timeout。
- 看到結果後不改任何門檻或定義（L-026）。

## 驗收
- `npm test` 過（若失敗只來自他人 live 改動，寫明哪幾項、為什麼不是本實驗）。
- 產出：`phase0.md`、`results.json`、`report.md`、`work/KJ-*/out/ranking.csv`、所有輸入 sha256（G2）。

## 回報（給 lead 的最後訊息）
照 CLAUDE.md 六段：第一行 `# 總評`（五級＋分數），再 **這次目標**、**進步了什麼**、**退步了什麼**、**直觀證據**（預註冊的 15 人表：KAU→KJ 名次、OVR、drive、creation→creationJ）、**要你決定的事**。白話寫 a1（重疊從 0.875 到多少）、a2（切入型球員被高估少了多少）、b 各過不過；Δρ、區間、閘門代號只寫 report.md。另附一行：drive 與 creationJ 每 10 點的 OVR 係數（±SE）。
