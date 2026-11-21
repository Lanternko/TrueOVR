# E-289 預註冊：中鋒被低估，該加護框還是籃板？用陣容 Transformer 拆

- 日期：2026-11-09
- 來源：E-288（中鋒前瞻缺口 +0.060，CON 兩分干擾加分最好）後使用者問「要放寬護框還是籃板的價值？用 Transformer 測測看」。
- 依 R-165 自行定標準、直接凍結開跑；R-178 分層驗收（T 是陣容層裁判，OVR 加分另看前瞻台，不拿單季防守 RAPM 否決）；L-135 放對照。
- 狀態：已凍結（2026-11-09）。

## 0. 揭露
- 已看過：E-288 全部結果（CON +0.0071、BOX +0.0055、Mobley 進前十）；E-285 置換重要度 blk36 +0.9、stl36 +12.6；T 換人值 Allen 9、Hartenstein 12、Gobert 45（T 本來就看重角色中鋒）。
- 沒看過：護框組／籃板組在 T 裡各自值多少、和 OVR 名次差距的關係；RIMc／REBc 合成在前瞻台上的 Δρ。
- `rimDiff`、`rimFGA36` 是球員自己在籃下的出手（進攻），不算護框；`matchup` 兩欄是整體防守，不歸任何一組。

## 1. 特徵分組（T 的 41 欄，E-227 R2-stats）
| 組 | 欄位 |
|---|---|
| RIM 護框 | help、blk36、cont2pt36 |
| REB 籃板 | rebound、oreb36、dreb36、orebPct、drebPct、boxoutO36、boxoutD36 |
| CTRL 對照 | screenAst36（同樣是長人非出手貢獻，給量級參考） |
另報（不進判定）：REB_O＝oreb36、orebPct、boxoutO36；REB_D＝dreb36、drebPct、boxoutD36、rebound。

## 2. 方法
**M1 T 給每組多少分**：線上 T（`e229_live.make_ctx`，2026-11-07 live 目錄、同 `t_swap_live.py` 抽樣：3000 組、seed 20261108、名次人群）。每位名次人群球員算 net＝ownPts100 − oppPts100；再把該球員某組特徵設成聯盟平均（z＝0，遮罩不動）重算，credit_G＝net_full − net_noG。報告各位置、中鋒的平均 credit，以及代表中鋒。

**M2 OVR 少算哪一組（主判定，陣容層）**：名次人群內 gap＝pct(T net) − pct(線上 OVR)。OLS：gap ~ z(credit_RIM) + z(credit_REB) + z(credit_CTRL) + 位置虛擬變數；配對 bootstrap 2000 次（seed 20261289）取 β 與 β_RIM − β_REB 的 90% 區間。β>0＝T 認為這組值錢、OVR 沒給夠。

**M3 前瞻台（OVR 層）**：同 E-288 台子與四折、λ 網格、RMS 縮放到 CPOS、判定條件 1–4。特徵取卡片原點季 t 的 T 表（`E227 data/players-<t>.csv`、`stats-<t>.csv`，<200 分鐘缺值記 0）：
- RIMc＝clip(mean(z(help), z(blk36), z(cont2pt36)), 0, 1.5)
- REBc＝clip(mean(z(rebound), z(orebPct), z(drebPct)), 0, 1.5)
- 參考：CON（E-288 最佳）、CPOS（純中鋒對照）。

## 3. 判定
- **加護框**：M2 β_RIM 下界 > 0，且（β_RIM − β_REB 下界 > 0 或 β_REB 區間跨 0），且 M3 RIMc 的 Δρ_all ≥ REBc 的。
- **加籃板**：對稱。
- **兩者都加**：兩個 β 下界都 > 0，且 M3 兩臂都 ≥ +0.003。
- **都不加／層間不一致**：其他情形照實寫（例如 T 說護框、前瞻台說籃板）。
- M3 各臂另照 E-288 的 adopt_candidate／structural_partial／reject 判。
