# E-284 預註冊：有球犯規／無球犯規當能力值進卡片 pred0（基準 R-180）

- 日期：2026-11-09。角色：lead 自做（dispatch routing＝self）。標準由執行者自訂並直接凍結（R-165）。
- 狀態：已凍結（2026-11-09，凍結時尚未建任何新臂）。
- 來源：使用者「加入 無球犯規和有球犯規 能力值」。
- 凍結前看過的：E-283（拆壓迫時總犯規每 SD −0.32～−0.70，四原點同號）；本表與抄截、蓋帽、總犯規的相關（有球 vs 蓋帽 0.53、一般 vs 抄截 0.48）及各項前六名。係數全由資料自由擬合，不挑格點（L-026）。

## 1. 能力值（`foul_comps.py` → `foul-comps.json`）
逐回合資料（2021-22～2024-25 `data/defense-seventh/<季>/pbp`，2025-26 `data/defense-a-source/pbp`）防守方個人犯規：
- **有球 f_on**：shooting、take、transition take、clear-path。
- **無球 f_off**：loose ball、away-from-play。
- **一般 f_gen**：personal 無 descriptor（pbp 分不出有沒有球）。
- 不算：進攻犯規、技術、惡性、double。
每原點 t：t−3～t（最早 2021-22）次數與分鐘（E227 stats-<季>.csv，按 pid）相加，每 36 分鐘，向窗口聯盟率收縮 k＝500 分鐘。按名字對卡片列，對不到填平均。設計內 z 標準化、全位置共用主效應、ridge λ=1。

## 2. 臂（全部＝E-277 M1＋四季窗口 blk36 固定每 SD 0.3＋保留 pressure）
| 臂 | 新欄（係數自由、不設符號）|
|---|---|
| F0 | 無（＝E-280 `ranking-K3-*`）|
| **F1（主臂）** | f_on、f_off |
| F2 | f_on、f_off、f_gen |
| F3 | f_ball（＝有球＋一般，把一般犯規當有球）、f_off |

## 3. 驗收（比 F0；同 E-283）
DEF＝onBall＋help＋pressure＋blk36＋各新欄貢獻（ranking pred0 逐位置還原）＋defenseBonus−人群平均。
- S2：OVR 對下季 EPM 合併 ΔR² ≥ −0.005 且每折 ≥ −0.010。S3：DEF 對下季 EPM 防守合併 Δρ ≥ −0.010。
- 採用候選＝S2 且 S3。多臂候選：取 DEF 對 EPM 防守 Δρ 最高；與 F1 差 ≤0.003 取 F1。
- 每欄報四原點係數（每 SD）與是否同號；不同號標為不穩。

## 4. 只報告
DEF 對同季 T、單季防守 RAPM Δρ；季中折；ΔR² 90% 區間（2000 次，seed 20261284）；例子表同 E-280；OVR 改 ≥3 人數。
