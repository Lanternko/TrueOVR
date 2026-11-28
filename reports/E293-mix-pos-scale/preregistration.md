# E-293 預註冊：MIX 加分依位置縮放（PF 被高估）

- 日期：2026-11-09；來源：使用者看線上排名後指出 Chet（15→6）、Mobley（17→7）、Hartenstein（54→29）又被高估；E-289 M1：T 給籃板的價值 C +2.80、PF +0.68、SF −0.55（每 100 回合），而 0.2.14 MIX 加分不分位置、18 人碰上限。
- 依 R-165 自行定臂、門檻，凍結後直接跑；R-178 分層驗收（下季 EPM 前瞻台只報告、不當唯一否決）；L-026 看過結果不改參數；R-184 的 500 分鐘以下按比例打折保留。
- 狀態：已凍結（2026-11-09）。

## 0. 揭露（凍結前已看過）
- E-288～E-292 全部結果；0.2.13a／0.2.14 卡的名次；T（`live/2026-11-08/t-swap.json`）、EPM（`epm-live.csv` poss≥200）、2K27 的名次：Chet T 6、EPM 無（<200 回合）、2K 36；Mobley T 15、EPM 34、2K 26；Hartenstein T 44、EPM 17、2K 87。
- 尚未看過任何臂的加分或名次。

## 1. 臂（全部疊在 card 0.2.13a 上；bonus × min(1, MIN/500)）
加分元件取自 `live/mix-pool-card0214.json`（凍結尺，REBc、CON 定義同 0.2.14）。`P_MIX` 照 0.2.14（clip 1.5、三個縮放），`A_full = λ·sd·P_MIX`，λ=0.5。

| 臂 | 加分（打折前） | 說明 |
|---|---|---|
| A | A_full | 現行 0.2.14 基準（須重現 card-0.2.14 的 mixBonus，差 ≤ 0.001） |
| P1 | w(pos)·A_full，w：C=1、PF=0.68/2.80=0.243、PG/SG/SF=0 | E-289 M1 籃板價值比例（SF 為負，截在 0） |
| P2 | 1[pos=C]·A_full | 只給中鋒 |
| P3 | w(h)·A_full，w(h)＝身高在 (SF 平均身高, 0)、(PF 平均身高, 0.243)、(C 平均身高, 1) 之間線性內插，兩端截 0／1 | 連續位置：資料裡唯一乾淨的連續量是 `heightInches`（T 的位置排序 hkey 也是身高優先）；平均身高取卡片 MIN≥500 人群各標籤 |
| K | 不分位置，REBc、CON 改 clip(·, 0, 1.0)，三個縮放沿用 A | 對照：只壓上限 |

每臂三種 λ（重新校準）：
- **same**：同 λ=0.5、同 sd、同縮放（P 臂＝把 A 的加分乘位置權重）。
- **aligned**：把 MIN≥500 人群的總加分量乘回與 A 相同（c＝ΣA/Σ臂）。
- **bench**：E-290 前瞻台（4 折，2025-26 折＝card 0.2.13a，前三折＝E-164 歷史卡；下季 EPM）四折平均 Δρ 最大的 λ*（格子 {0,.05,.1,.2,.3,.5,.75,1,1.5,2}），臂的 P 不再縮放到 CPOS 均方根（λ 直接對應 A 的單位）；各折另報留一折 λ 的 Δρ。

## 2. 指標
1. 卡片（2025-26，582 人）新 OVR 與 T 淨值（ownPts100−oppPts100，名次人群 289）、EPM（poss≥200）、2K27 的 Spearman（各自可對到的人；T／EPM 用 playerId，2K 用正規化姓名）。對 A 的差做配對 bootstrap 2000 次（seed 20261293），90% 區間。
2. 位置缺口：卡片∩T 人群內 pct(T 淨值) − pct(OVR) 的 C、PF 平均；EPM 版同算（只報告）。
3. 代表球員名次：Chet、Mobley、Hartenstein、Gobert、Allen、Zubac、Edey、Wembanyama、AD、Giannis、Jokić、Towns、Adebayo、Jaren Jackson Jr.、Sabonis、Booker、Maxey、Durant；附 T／EPM／2K 名次。
4. 前十、0.2.13a 前 30 名掉 >10 名者、碰上限人數。
5. 前瞻台 Δρ_all（相對 0.2.13a 與相對 A），C 缺口，下季 RAPM（只報告）。

## 3. 判定（每個臂×λ 版本各自判；K 只當對照，不產卡）
`adopt_candidate`（全部成立）：
- L1 一致度：T、EPM、2K 三者都**不**出現「Δρ（對 A）< −0.005 且 90% 區間上界 < 0」。
- L2 中鋒修正保住：T 版 C 缺口 ≤ 0.5 × 0.2.13a 的 C 缺口（0.2.13a 缺口 ≤ 0 時此條略過）。
- L3 Chet、Mobley 回合理區間：卡片名次 ≥ max(11, 參考名次中位數 − 10) 且 ≤ 參考名次最大值 + 10。參考＝T、EPM、2K 有的名次（Chet：6、36 → 中位 21 → 門檻 11～46；Mobley：15、34、26 → 中位 26 → 門檻 16～44）。
- L4 前十：相對 0.2.13a 前十新增的 PF/C 只容許 R-182 名單（Wembanyama、Giannis、Jokić、Chet、Mobley）；0.2.13a 前 30 名掉 >10 名 ≤ 2（R-183）。
- L5 前瞻台：只報告，不否決。

候選優先序（不看分數挑）：P1 > P3 > P2；同臂 same > aligned > bench。取第一個 adopt_candidate 產 `reports/card-0.2.15-cand/`（照 build_cand2.py，只產候選、不動線上）。都不過就不產卡，報告寫哪條擋下。
