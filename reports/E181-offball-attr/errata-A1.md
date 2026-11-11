# E-181 errata A1：第 2 階段改用上一季判定（R-113）

- 日期：2026-11-01。狀態：已核可（2026-11-01，使用者「核可」）。凍結的 `preregistration.md`（sha256 1e3c8e86…）不改，本檔核可後取代其 §3「第 2 階段」。
- 原因：E-181 凍結的同時，使用者在 E-180 裁定 R-113：「用上季 不要一直跟我扯資料不夠要等」——驗證修正用手上已有的最近一季當判定資料。E-181 原本寫等 2026-27 RAPM（最早 2027-02-15），和 R-113 衝突。
- 第 1 階段（§3 不劣於檢查：c0、npm test、s1、s2、s3）不變。

## 第 2 階段（取代）：2024-25 原點 → 2025-26 RAPM，和第 1 階段一次跑完
- 卡片：2024-25 歷史原點。K0h＝0.2.9a 底，照 E-177 K0h 建法；c0h：重建後與 `reports/card-0.2.9a+E177-bbref-position-shares/ranking-K0-2024-25.csv` 逐位元相同，不同就停。O1h／O2h＝同一原點加 offBall（／offBallAcc），取值窗口與季別照該原點 creation 的同一取法（L-091 問題兩邊一致，不另修）。
- 答案：`reports/card-0.2.7+E126-tank-next-season/rapm-2025-26.json` 的 `net`、`O`，乘 `wfun(2025-26 mpg)`；人群照 E-179 §2。
- 無球組 Q：K0h 能力值中 offBall 百分位 ≥ 60 且 creation 百分位 ≤ 50（三臂同一份分組）。e_net＝pct(net×W)−pct(OVR)。bootstrap 2000 次，seed 20261181，90% 區間；臂間差在同一組重抽上算。
- 判定（門檻與原 §3 相同）：
  - p0：K0h 的 Q 組平均 e_net 上界 < 0。不成立 → 判「低估沒出現，不加屬性」。
  - 臂 X ∈ {O1, O2} 採用候選：① Q 組平均 e_net，X−K0 下界 > 0；② Spearman(OVR, net×W)，X−K0 下界 > −0.01；③ 第 1 階段過。都是候選選 O1。
- 只報告：e_O 版本；Q 組按位置拆；另兩個原點（2022-23、2023-24）同一套統計量；例子球員（原 §3 名單）。
- 揭露：2025-26 RAPM 在 E-179／E-180 看過 pass、creation 的分組殘差；offBall 與 Q 組對它的殘差沒看過。能力值是 2025-26 現值（L-091），結果是「有揭露的樣本內」，不是乾淨的樣本外。
- 產出改為：`e181_build.py`、`offball-raw.csv`、`ranking-{K0,O1,O2}-2025-26.csv`、`ranking-{K0h,O1h,O2h}-2024-25.csv`、`results.json`、`report.md`（六段格式）。
