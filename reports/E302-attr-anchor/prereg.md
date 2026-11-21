# E-302 預註冊：賽中能力值錨點（各項按穩定速度）對 OVR 錨點，加負 D 分鐘修正

日期：2026-11-10（凍結後開跑，R-165）

## 問題
1. Yang Hansen 類（D＝predNew − r_repl < 0 的替補）：g＝D·W(MPG)，上場越多扣越多；打得差又少上場反而接近替補水準（像加分）。E-296 A2-15-R 已證明可修（S1–S4 過）。
2. 錨點 vs 滑動窗口：E-299 OVR 錨點讓好表現掉分 26%→9%，但 OVR 不能由能力值算回、看不出哪項變強；錨點衰減照「自己第幾場」，傷停時凍住，最後 20% 才硬淡出。窗口能力值一致但反應慢。
本實驗用同一版本、同一人群、同一把尺逐日重算，正面比較「能力值錨點」與「OVR 錨點」。

## 程式版本
- 快照 HEAD（991736b，card／inseason 0.2.14c）的 `reports/ovr-inseason-2026-27/live/*.py` 與根目錄凍結檔到 `reports/E302-attr-anchor/live-{r0,ra,rap}/`。工作樹另有別的 session 未 commit 的 window8／pres_drive／run_c4_live_rookie 改動，不用。`run_c4_live.py` 的 REPORT 改指原 `reports/ovr-inseason-2026-27`（只讀 v4／v5 工具）。
- 三份只差 AA 補丁（r0 沒有；ra＝AA-max；rap＝AA-pure）。逐日重算用快照裡的 `ovr_history.py`，每天另存 predNew／MPGhat／g／mixBonus／各屬性。最後一天也重算（不讀線上 ranking）。

## 能力值錨點（AA）
- 套用：window8 的 ft、rebound、vol、foulDraw、astvol、pass、mid、short、driveVol、driveEff；window10 的 f3、cr、crJ、tpa（long、creation、threeValue 的來源）。
- 不套：tovSkill（TOV_POSS 另有持球分鐘分母）、mpg／ap／pl（用人層）、季累計追蹤表（onBall、help、pressure、gravity、pnr；沒有逐場資料）、防守 D。
- 每項窗口和拆成過去季 (n_p, d_p) 與本季 (n_c, d_c)（現行，含 b=3、h=20 加成）。s_win＝d_c／(d_p＋d_c)。
- 本季證據量 d_ev＝Σ 本季逐場 d·exp(−age／20)，age＝(g−1−gi)·82／1230（同 R-150 的核，聯盟場齡換球隊場次）；缺陣時 age 照日曆變大，d_ev 自然變小。
- λ0＝d_ev／(d_ev＋M_x)；fade＝clip((1230−g)／(0.2·1230), 0, 1)。
- 主臂 AA-max：s*＝s_win＋fade·max(0, λ0−s_win)（只加快、不比現行慢）。對照 AA-pure：s*＝s_win＋fade·(λ0−s_win)（慢穩定的項可以比現行慢）。
- 改寫：總分母 D＝d_p＋d_c 不變（收縮量不變），n′＝D·[(1−s*)·n_p／d_p＋s*·n_c／d_c]、d′＝D；d_p＝0 或 d_c＝0 不改。fade＝0（季末）時與現行逐位元相同＝卡片。

## 穩定點 M_x（2025-26 歷史季，不用 2026-27）
- 2025-26 逐場表（window8 `D.tab['2025-26']`、window10 `T10['2025-26']`），每人照自己的出賽順序奇偶分半；取該季 d 前 300 名。
- ρ_h＝兩半比率的 Pearson；M_x＝median(d_half)·(1−ρ_h)／ρ_h（d 的單位）。ρ_h ≤ 0.05 → M_x＝∞（λ0＝0，不加快）。

## 臂
| 臂 | 窗口 | 分鐘 | OVR 錨點 |
|---|---|---|---|
| A0 | r0 | 現行 g＝D·W(MPG) | 無 |
| M | r0 | A2-15-R | 無 |
| MR | r0 | A2-15-R | β0＝0.5、h＝10（E-299 主臂）＋缺陣衰減 |
| **MA（主臂）** | ra | A2-15-R | 無 |
| MAp | rap | A2-15-R | 無 |
| MAR | ra | A2-15-R | β0＝0.25、h＝10＋缺陣衰減 |
- 缺陣衰減（只 OVR 錨點臂）：β 再乘 0.5^(max(0, 距上一場天數 − 3)／14)。
- A2-15-R 與 PR1＝E-296 凍結值（`reports/E296-neg-g-minutes/part_a.json`）；s＝2.146＋11.295·rt＝E-299 凍結值（`map.json`）。

## 驗收（凍結）
- R1 結構：B1＝ρ(rt, 該場打完 ΔOVR) ≥ A0＋0.15，且好表現（rt ≥ 本人本季先前平均＋1、MIN ≥ 15）掉分率 ≤ 13%（同 E-299）。
- R2 前瞻（時間上樣本外）：ρ(當下 OVR, 之後最多 5 場分鐘加權 +/- 每 36) ≥ A0 − 0.01。
- R3 一致性：最後一天 N ≥ 3 的人 |OVR 錨點項| 中位（OVR 分）；MA／MAp＝0。
- 選擇：R1、R2 都過的臂裡依 MA → MAR → MR 的順序取第一個（能力值為主體）；都不過，取 R2 過且掉分率最低者，總評 ≤ 3。
- 只報：前 20 名重疊、最後一天 |Δ| 中位、單場最大跳動、Yang 逐日與 11/7 那場各屬性變動、MA 讓 B1 漲多少（能力值速度能解決的份量）、穩定點表、季末檢查（g＝G 時 s*＝s_win）、M 臂的 R-033 結構（D<0 多 2 分鐘 OVR 不降）。
- 不用 2026-27 結果改 M_x、β0、h、14 天；不回頭改臂。
