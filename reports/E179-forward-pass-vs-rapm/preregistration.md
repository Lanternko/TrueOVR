# E-179 預註冊：卡片是不是系統性高估「傳球、自主進攻高」的前鋒（對下季 RAPM）

- 日期：2026-11-01。來源：使用者看完 E-177（位置比例不採用，JW 幾乎沒變）後，對「寫預註冊驗證前鋒傳球係數」回「好」。
- 狀態：已凍結（2026-11-01，使用者「好」核可凍結）。

## 0. 已揭露（lead 寫本檔前看過的東西）
- E-176／F-113（同季、樣本內）：2025-26 卡 OFF 名次對同季外部進攻（DARKO O、EPM O、OBPM）平均名次的殘差，和 pass 的 Spearman：PF −0.51、SF −0.40、PG +0.04、SG +0.20；creation 是 PF −0.46、SF −0.28。外部指標和 T6 同源。
- E-177：位置換成 BBRef 比例後，SF／PF 同一個殘差是 −0.37／−0.41（同季）；JW OVR 88.2→88.0。
- E-173：K6 歷史原點對下季 RAPM，drive 的 S_net 為 −0.206（全位置，只報告）；pressure 沒有偏差。E-173 沒算 pass、creation。
- 卡片係數：PF 的傳球每 10 分值 0.533，SG 為 0.198（F-110）。
- **沒看過**任何 pass、creation 和「下季 RAPM 殘差」的關係，不論分不分位置。
- 判定不得以 JW 或任何單一球員為條件（L-026），他只列在例子表。

## 1. 問題
對下一季 RAPM 來說，卡片會不會把傳球、自主進攻高的**前鋒**（SF、PF）排得太高，而且比同樣條件的後衛更嚴重？下季 RAPM 沒有進卡片擬合，是時間上的樣本外。注意：這三季已經用來選 T6，所以不是全新的樣本外（同 E-173 §1）。

## 2. 資料（全部沿用現成檔，不重建卡片）
- 卡片：card 0.2.9a 底的三個歷史原點，`reports/card-0.2.9+E164-no-stamina/ranking-S-{t}.csv`，t＝2022-23、2023-24、2024-25（E-177 c0h 已確認它們就是 0.2.9a 底的 K0h）。欄位用 `ovr`、`pos`、`pass`、`creation`、`MIN`，以及算 OFF 要用的能力值欄。
- 答案：`reports/card-0.2.7+E126-tank-next-season/rapm-{t+1}.json` 的 `net`、`O`。條件照 E-173 §2：poss ≥ 1000、在 `pop_of(t)` 人群、有下季 mpg；net 和 O 都乘 `wfun(mpg)`。
- 人群：照 E-173 `e173_eval.py` 的 `season_data`（卡片 MIN ≥ 500、名字唯一對到 pop_of(t)）∩ 有下季 RAPM 的人。
- 位置組：用卡片的 `pos`（現行硬標籤）。前鋒 F＝{SF, PF}，後衛 G＝{PG, SG}，C 不進判定。

## 3. 統計量（每季各自算，三季以人數加權合併）
- pct(x)＝季內（全人群）名次 ÷ n，平手取平均名次。
- e_net＝pct(下季 net×W) − pct(ovr)。負值＝卡片排得比下季 RAPM 高。
- OFF：照 `scripts/season_nav.off_def` 的做法，在**該季卡片內**依位置把 pred0 回歸到 OD_ALL，取進攻段。e_O＝pct(下季 O×W) − pct(OFF)。
- 對 a ∈ {pass, creation}，每組（F、G）各自算 Spearman(a, e_net) 與 Spearman(a, e_O)。
- 差值 Δ_a＝S_F − S_G。
- 信賴區間：季內以球員重抽 2000 次，seed 20261101，90% 百分位區間。合併值在每次重抽後重算。

## 4. 判定（事先訂定，看結果後不改）
各屬性 a（pass、creation）分開判：
- **前鋒高估 a**：S_F(a, e_net) 的 90% 區間上界 < 0，**且** Δ_a(e_net) 的上界 < 0。
- **前後衛一樣（不分位置的偏差）**：S_F 上界 < 0，但 Δ_a 上界 ≥ 0。
- **沒有偏差**：S_F 上界 ≥ 0。
- e_O 版本只報告，不判定（OFF 是從 pred0 回推的，有拆解誤差）。
- 判成「前鋒高估」也**不直接改卡**。修法（降低前鋒傳球交互項、把交互項收縮到全位置共用係數等）要另外寫預註冊。

## 5. 前置條件（不過就停下回報，不出判定）
- c0：三份 ranking-S 的 sha256 等於 E-164 `results.json` 記錄的值。
- c1：每季人群 n ≥ 150，前鋒組 n ≥ 50，後衛組 n ≥ 50。
- c2：每季 OFF 回推的 pred0 誤差 > 0.02 的人 ≤ 5%。

## 6. 只報告
- 同一套統計量換成 drive、tovSkill、foulDraw（比較用）。
- C 組的 S。
- 例子：Jalen Williams、Jalen Johnson，以及三季合併「前鋒 pass 前 10 名」的 e_net、e_O。

## 7. 產出
`reports/E179-forward-pass-vs-rapm/`：
- `e179_eval.py`：從 repo root 用 `python -I -B -X utf8` 跑，本機輕量。
- `results.json`：含 c0–c2、三季各自與合併值、CI、判定。
- `report.md`：六段格式，查證細節放報告檔。
