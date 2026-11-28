# E-205 phase0（跑 KW 前；只用 K12）

- K12 ranking.csv sha256 `29ca32eb65cfa40c465f9b8555912ae9829047cd87c497674d804f8f31f300a5`（c0 重現＝card 0.2.12）。bootstrap 球員層 2000 次，seed 20261102。
- tovSkill 對 2K27 Ball Handle Spearman（n=376）= 0.7947（0.2.11 為 0.0798，E-202 MDE 0.0879）→ 保住 E-202 門檻：KW ≥ 0.1677。（K12 自身 90% 半寬 0.0325）
- 全體 OVR 對 2025-26 RAPM Spearman（n=379）= 0.5751，90% 半寬 **h = 0.0581** → 沒弄壞：KW − K12 ≥ **-0.1163**。
- tovSkill 對其他能力值 VIF = **5.37**（A 門檻 KW ≤ 3.0）；與 creation 相關 +0.72、pass +0.78、gravity +0.58。
- F-143 現值：TO 前 30 中持球/36 低於池中位數（2.861）的有 **0**/30（無資料 0；前 30 平均持球 7.69）；榜首 Jalen Brunson、Shai Gilgeous-Alexander、T.J. McConnell、Tyrese Maxey、Tyus Jones。
- 人群定義：2K 池＝卡片 MIN≥500 且 2K27 有 Ball Handle（姓名正規化比對）；RAPM 人群＝MIN≥500 且本季 RAPM poss≥1000（同 E-198）；F-143＝MIN≥500，持球/36＝handle.csv TIME_OF_POSS÷卡片 MIN×36，中位數取同人群
