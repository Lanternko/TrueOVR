# E-195 spec：卡片為什麼把切入型球員排得比 T6 還高（F-136 擬合端診斷，不佔額度）

用 role-card skill。cwd `D:\Projects\CODING\basketball-autochess`。只寫 `reports/F136-fit-side/`（含 `work/`、`logs/`）。

## 背景（已知，不要重查）
- E-194（`reports/F133-drive-scoring/`，F-136）：KJ 卡三歷史原點合併、MIN≥500，e_fit＝pct(T6 pooledNet) − pct(OVR)，Spearman(drive, e_fit) −0.257，三季 −0.29／−0.30／−0.20。drive 本身是擬合欄、係數 ≈0。線性迴歸的殘差照理和擬合欄不相關，所以偏差應出在「擬合池／權重」與「評估人群／名次」不同，或 pred0 之後的步驟（防守加成、align、H1 封頂、OVR 映射）。
- 重用 `reports/F133-drive-scoring/diag.py` 的載入（`load_season`、pred0 重建、t6 讀 `work/base-KJ-<季>/<季>/rapm-R.csv`），E-190 的 `work/` 只讀。

## 要做的事（KJ，三歷史原點；再用 KAU 同樣跑一次對照；bootstrap 球員層 2000 次、seed 20261101）
先寫 `diag_plan.md`（每步計算式、從哪個檔讀）才跑，跑完不改定義（L-026）。

1. **沿管線拆**：對同一批 MIN≥500 球員，依序算 Spearman(drive, pct(T6) − pct(S_k))：S0＝pred0 的純線性（不含位置交互）、S1＝pred0（含位置交互）、S2＝＋防守加成、S3＝align 後、S4＝H1 封頂後、S5＝最終 OVR。每一步的值要從卡建置程式實際讀或重建，重建不了就明說、不湊。指出偏差在哪一步出現／放大。
2. **擬合池 vs 評估人群**：讀卡建置的實際擬合池與權重（`summary.json`／建置程式），報：(a) 擬合池內、用擬合權重的加權相關 corr_w(drive, T6 − pred0)（應 ≈0，驗證）；(b) 同池不加權；(c) 擬合池∩MIN≥500 不加權；(d) 用值差（T6 − pred0，同單位）代替名次差。看偏差是權重、人群還是名次轉換造成。
3. **誰被推高**：drive 前 25% 的人在 1、2 各步的平均 e，加上前 10 名切入球員逐步的表（名次 T6 → S0 → … → OVR）。

## 限制
- 不改 `src/`、`scripts/`、網站、memory、`reports/card-*`、`live/`；不 commit、不 push、不 git add。
- 子程序 `creationflags=subprocess.CREATE_NO_WINDOW`、`stdin=DEVNULL`；長指令加 timeout。本機輕量即可。
- 不提採用、不改卡。

## 驗收
- `diag_plan.md`、`diag.py`、`results.json`、`report.md`；`python diag.py` 重跑 results.json 逐位元一致。
- KJ S5 那步的 Spearman 必須重現 E-194 的 −0.257（差 <1e-9）；2(a) 的加權相關 |r|<0.02，否則寫明為什麼。

## 回報（最後訊息）
CLAUDE.md 六段（第一行 `# 總評`）。白話：偏差在哪一步出現、占多少；是權重／人群／名次哪一個造成。**要你決定的事**列 2–3 個修法（例如改擬合權重、改評估人群、改映射），只描述不推薦採用。區間只寫 report.md。
