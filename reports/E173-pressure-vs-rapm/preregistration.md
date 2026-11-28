# E-173 預註冊：卡片是不是系統性高估「壓迫高」的球員（對下季 RAPM）

- 日期：2026-11-01。來源：使用者看完 E-172（Jalen Williams 偏高診斷）後選「A 壓迫對 RAPM」。
- 狀態：已凍結（2026-11-01，使用者「核可凍結」）。

## 0. 已揭露（lead 寫本檔前看過的東西）
- E-172：Jalen Williams 四季單季 pressure 84.0–96.4；他在 card 0.2.9 的 T6（同季 DARKO＋BPM 合成，不是 RAPM）排第 25。E-172 報告寫的「RAPM #25」是誤稱，實為 T6。
- E-153 的整體結果（三季 C、薪水、2K、下季 RAPM 的差與關鍵球員名次）。
- **沒看過**任何球員的「卡片名次 − 下季 RAPM 名次」殘差，也沒看過殘差和 pressure 的關係。
- 判定不得用 Jalen Williams 或任何單一球員的名次當條件（L-026）；他只列在報告當例子。

## 1. 問題
卡片 OVR（目標是 T6）會不會讓「抄截／干擾傳球多」的人排得比他們**下一季**的 RAPM 高？下季 RAPM 沒進卡片擬合，是時間上的樣本外。
注意：這三季在 E-142／E-153 已經用來選 T6，所以這不是全新的樣本外，回答的是「現行卡在這三季有沒有壓迫方向的系統偏差」。真正的新樣本外要等 2026-27。

## 2. 資料（全部沿用現成檔，不重建卡片）
- 卡片：E-153 K6 歷史原點 `reports/card-0.2.7d+E153-t6-target/work/K6-{t}/{t}/out/K0/ranking.csv`，t＝2022-23、2023-24、2024-25（與 card 0.2.9 同一套 K6 擬合；0.2.9 只多了用人層變更，不動能力值與 OVR 擬合層以外的欄）。欄位用 `ovr`、`pressure`、`defenseBonus`、`onBall`、`help`、`drive`。
- 答案：`reports/card-0.2.7+E126-tank-next-season/rapm-{t+1}.json`，取 `net`、`D`；條件照 E-142 `phase1_eval.build_ref`：poss ≥ 1000、在 `pop_of(t)` 人群、有下季 mpg。net 乘 `wfun(mpg)`（同 E-153 ③）；D 不乘。
- 人群：E-153 `e153_eval.py` 同一套（卡片 MIN ≥ 500、名字唯一對到 pop_of(t)）∩ 有下季 RAPM 的人。

## 3. 統計量（每季各自算）
- pct(x)＝季內名次 ÷ n（平手取平均名次），範圍 (0, 1]。
- e_net＝pct(下季 net×W(mpg)) − pct(ovr)：負值＝卡片排得比下季 RAPM 高。
- e_D＝pct(下季 D) − pct(defenseBonus)：只看防守那一段。
- **S_net**＝Spearman(pressure, e_net)；**S_D**＝Spearman(pressure, e_D)。
- 三季合併：各季值以人數 n 加權平均。
- 信賴區間：每季內以球員重抽，2000 次，seed 20261101，90% 百分位區間（合併值在每次重抽後重算）。
- **T_D**（只報告，不判定）：pressure ≥ 90 那組的平均 e_D 減其他人的平均 e_D，同一套重抽。

## 4. 判定（事先訂定，看結果後不改）
- **壓迫被高估**：S_net 與 S_D 的 90% 區間上界都 < 0。
- **壓迫被低估**：兩者下界都 > 0。
- **沒有系統偏差**：其他情況。此時 E-172 的落差視為 Jalen Williams 個人的情況，這條線結案，卡片不動。
- 判成「被高估」也**不直接改卡**：修法（壓迫權重、頂端尾巴、和 RAPM D 的混合）要另寫預註冊。

## 5. 前置條件（不過就停下回報，不出判定）
- c0：三季的 ranking.csv sha256 與 `reports/card-0.2.7d+E153-t6-target/results.json` 記錄的 `rank_sha256["K6-{t}"]` 相同。
- c1：每季人群中 pressure、defenseBonus 非空的比例 ≥ 95%。
- c2：每季人群 n ≥ 150。

## 6. 只報告（不進判定）
- 同一套 S_net、S_D 換成 onBall、help、drive（比較用）。
- 同季 T6 殘差版的 S（樣本內，R-007，只看方向）。
- 例子：Jalen Williams、以及三季合併 pressure 前 10 名的 e_net、e_D。

## 7. 產出
`reports/E173-pressure-vs-rapm/`：`e173_eval.py`（`python -I -B -X utf8` 從 repo root 跑，本機輕量）、`results.json`（含 c0–c2、三季各自與合併值、CI、判定）、`report.md`（六段格式，查證細節放報告檔）。
