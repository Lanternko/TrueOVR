# E-301 預註冊：無球拆成「空檔射手」與「切入順下」兩格（2026-11-10 凍結）

- 起因：E-297（F-178）的等權單格 W-eq 夠穩定（年對年 0.70），但偏射手（Gordon 26、Gobert 19 百分位）。使用者 2026-11-10 裁定「拆兩格再測」。
- 範圍：只做網站顯示用的描述性能力值。不改 T、OVR、每日抓資料。
- 洩漏聲明：兩格的欄位分組在 E-297 報告裡就寫好了，當時已看過 2025-26 單欄和 OBPM／2K 的相關，所以 2025-26 只算半樣本內。**樣本外裁判是 2024-25**：用該季 OBPM、2K26 overall、E-164 `ranking-S-2024-25`（0.2.9a 歷史原點卡，`reports/E290-reb-bonus-0213a/stage/`）當 OVR 控制。E-297 沒看過這一季的任何外部對照。

## 兩格定義（固定，不再調）
- **SHOOT 空檔射手**：Synergy Spotup、OffScreen、Handoff，加上 CatchShoot 三分。
- **CUTROLL 切入順下**：Synergy Cut、PRRollman、OffRebound（補籃）、Transition。
- 不納入：SpeedDistance 跑動距離與速度、CatchShoot 出手量 cs3a36（E-297：和 2K／OBPM 負相關，而且不是能力）。

## 三種算法（臂）
- **V（量為主）**：
  - SHOOT＝z(spotup36)+z(offScr36)+z(handoff36)+0.5·z(cs3pct)
  - CUTROLL＝z(cut36)+z(roll36)+z(putback36)+z(trans36)+0.5·z(cutPPP)
  - 各自除以權重和。欄位沿用 E-297 `data/offball-<季>.csv`。
- **P（得分貢獻）**：每種 play type 的貢獻是 36·POSS·(PPP′−lgPPP)/分鐘，其中 PPP′＝(PTS+30·lgPPP)/(POSS+30)，lgPPP 是該季該 play type 全聯盟值。
  - SHOOT 加上 CatchShoot 三分：36·3·FG3A·(pct′−lg)/分鐘，pct′ 用 k=50 收縮。
  - 每格把各 play type 的貢獻加總。
  - 沒有 Synergy 列的球員記 0；沒有 CatchShoot 的記 0。
- **VP**：每格 z(V) 與 z(P) 平均。
- **參照**：E-297 W-eq 單格。
- 所有 z 都是季內、≥200 分鐘全聯盟尺。

## 母體
- 2025-26：E-297 的 value-ALL 母體（stint ≥1000 分鐘，N=276）。
- 2024-25：stats 分鐘 ≥1000。

## 驗收（每臂都要過 C1–C3；過的臂裡 2024-25 主指標最高者＝建議；同分取 V）
- **C1 穩定**：兩格的年對年 r（2024-25→2025-26，2025-26 母體且 2024-25 ≥200 分鐘）都要 ≥0.60。
- **C2 直覺**（2025-26，沿用 E-297 指名名單，不加新人）：
  - SHOOT 組 Klay Thompson、Buddy Hield、Duncan Robinson、Sam Hauser、Derrick White：在母體內的人裡，≥75% 要在 SHOOT ≥70 百分位。
  - CUTROLL 組 Aaron Gordon、Jarrett Allen、Rudy Gobert、Dereck Lively II、Josh Hart：同上，看 CUTROLL ≥70 百分位。
- **C3 契合**：兩格一起加到 OVR 之上，看對 OBPM 與 2K 的 ΔR² 平均（主指標）。
  - 2024-25 要 >0，且 ≥ W-eq 單格的 2024-25 值。
  - 2025-26 只報告。

## 只報告
兩格之間的相關、各格和 ΔT_off（E-297 ALL 臂）的 Spearman、指名球員（含持球型 Dončić、Trae、SGA、Harden）兩格百分位、兩格各自前 10 名。
