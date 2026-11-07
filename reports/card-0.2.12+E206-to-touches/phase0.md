# E-206 phase0（跑 KC 前；只用 K12）

- K12 ranking.csv sha256 `29ca32eb65cfa40c465f9b8555912ae9829047cd87c497674d804f8f31f300a5`（c0 重現＝card 0.2.12）。bootstrap 球員層 2000 次，seed 20261102。
- tovSkill 對 2K27 Ball Handle Spearman（n=376）= 0.7947（0.2.11 為 0.0798，E-202 MDE 0.0879）→ 保住 E-202 門檻：KC ≥ 0.1677。（K12 自身 90% 半寬 0.0325）
- 全體 OVR 對 2025-26 RAPM Spearman（n=379）= 0.5751，90% 半寬 **h = 0.0581** → 沒弄壞：KC − K12 ≥ **-0.1163**。
- tovSkill 對其他能力值 VIF = **5.37**（只報告）；與 creation 相關 +0.72、pass +0.78、gravity +0.58。
- F-143 現值：TO 前 30 中持球/36 低於池中位數（2.861）的有 **0**/30（無資料 0；前 30 平均持球 7.69）；榜首 Jalen Brunson、Shai Gilgeous-Alexander、T.J. McConnell、Tyrese Maxey、Tyus Jones。
- **A 基準**：持球者子群（MIN≥1000 且持球/36≥5，n=64）tovSkill 對 AVG_SEC_PER_TOUCH Spearman（K12）= **0.7117**，bootstrap 90% 半寬 **MDE_A = 0.1113** → A 過門檻：K12 − KC ≥ 0.1113（即 KC ≤ 0.6004）。
- 換算係數 ρ（觸球／持球分鐘）：卡片池 2025-26 = 15.5929（z 池 252 人 15.0121）；k_t = 997.94、kh_t = 3991.78。
- 人群定義：2K 池＝卡片 MIN≥500 且 2K27 有 Ball Handle（姓名正規化比對）；RAPM 人群＝MIN≥500 且本季 RAPM poss≥1000（同 E-198）；F-143＝MIN≥500，持球/36＝handle.csv TIME_OF_POSS÷卡片 MIN×36，中位數取同人群
