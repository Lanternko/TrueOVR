# E-291 預註冊：MIX 加分上場時間收縮（平滑版，修 500 分鐘斷崖）

- 日期：2026-11-09；角色：role-card；派工來源：使用者裁定「做平滑版」。
- 背景：card 0.2.14-cand（E-290 MIX，R-183）加分只套 game log ≥500 分鐘的 380 人（L-138，`reports/audit-0.2.14-cand/report.md`）：Hukporti 498 分 +7.45、Jackson-Davis 496 分 0、Edey 0；18 人頂到上限 +7.6；2K27 名次相關 0.765→0.749。
- 非盲揭露：MIX、λ=0.5 是 E-290 看過結果後由 R-183 裁定；稽核已算過「不收縮全 582 人」變體（本實驗 C 臂）的前十與相關係數（差 ≤0.002）。本實驗只新增收縮規則，常數 500 沿用 R-169，不調參（L-026）。

## 方法（B 臂，凍結）
1. 卡：`reports/card-0.2.13a/ranking.csv`（582 人）。資料：卡欄 `rebound`、`MIN`；`reports/E227-lineup-transformer-r2/data/stats-2025-26.csv` 的 `orebPct`、`drebPct`、`minutes`；`data/tracking-cells/2025-26/hustle-2025-26.json` 的 `CONTESTED_SHOTS_2PT`、`MIN`（同人多列加總）。名字對應照稽核 `recompute.py`（NFKD 去重音、小寫、去標點與 Jr/II 等，要求唯一）。
2. 評估人群 EP：卡 MIN ≥ 500 且 stats 名字唯一對應（稽核得 379 人，同 A／E-290）。
3. 收縮：每個原始量 x 依**自己那份資料的分鐘數** m 收縮到同位置（卡 `pos`）平均：x' = w·x + (1−w)·μ_pos，w = m/(m+500)。
   - rebound 用卡 MIN；orebPct／drebPct 用 stats `minutes`；con2_36 = CONTESTED_SHOTS_2PT／MIN×36 用 hustle MIN（取消原本 MIN≥200 門檻，小樣本改由收縮處理）。
   - 某分量缺值（對不到或該列空）→ 該分量 w=0，即等於位置平均。
   - μ_pos 與 z 的平均／標準差：都用 EP 的**原值**（未收縮）。理由：(a) 與 A／E-290 用同一把尺，B 和 A 的差只來自收縮本身；(b) EP 都是 ≥500 分鐘的人，原值可靠；若用收縮值算標準差，標準差會隨分鐘分布縮小而把 z 放大，等於偷偷換尺。
4. 其餘照原版：REBc = clip(mean(z reb', z oreb', z dreb'), 0, 1.5)；CON = clip(z con', 0, 1.5)；兩分量各自 RMS 縮放到 P_ref = √(EP 中 C 佔比)，各半合併後再 RMS 縮放到 P_ref；**RMS 都在 EP 上、用 B 自己的值重算**（縮放是程序不是常數；這樣 EP 內加分平均大小與 A 相同，λ 意義不變）。bonus = λ·sd·P，λ=0.5，sd = EP 的 0.2.13a OVR 標準差（ddof=0，13.406）。套到全部 582 人。
5. 真的沒資料：stats 無唯一對應**且** hustle 無列（或 MIN=0）的人，加分記 0 並列名單（卡欄 rebound 是衍生屬性，不算原始數據）。
6. 新 OVR = round(ovr_0213a + bonus, 1)；同分依 0.2.13a 名次。

## 對照臂
- A：現行 card-0.2.14-cand（直接讀 `reports/card-0.2.14-cand/ranking.csv` 的 mixBonus）。
- B：上面的平滑版。
- C：不收縮、582 人全套（原 MIX 公式，CON 保留 hustle MIN≥200 門檻，缺值分量 z=0；即稽核 full582）。只當參考。

## 驗收門檻（B 全過才產 `reports/card-0.2.14-cand2/`）
- T1 前十：B 前十新增（相對 0.2.13a）的 PF/C 只能是 R-182 名單（Wembanyama、Giannis、Jokić、Chet、Mobley），且 B 與 A 前十名單的差（對稱差的一半＝換掉幾人）≤ 2，換進換出的長人都在 R-182 名單內。
- T2 0.2.13a 前 30 名（全卡名次）在 B 掉 > 10 名的人 ≤ 2（R-183）。
- T3 無斷崖：(a) 反事實連續性：每位球員把三種分鐘數都設成 499 與 501（比率不變）重算 B 加分，582 人最大差 ≤ 0.10 OVR（推導：w 的差 ≈ 2·500/1000² = 0.001，乘 z 範圍與縮放 ≈ 2×7.6 上限量級 < 0.05，留一倍餘裕）；(b) 實際分布：卡 MIN 在 [400, 600] 的人，OLS bonus ~ 1 + MIN + 1[MIN≥500] + 位置虛擬變數，階梯係數 |c| ≤ 1.0 OVR。A 的同兩數一併列出。
- T4 頂上限人數：B 中兩分量都被 clip 在 1.5（加分＝該臂最大值）的人數 < A 的 18 人。
- T5 外部尺：OVR 對 2K27 的 Spearman（卡 MIN ≥500、2K 對得到，約 376 人）與對本季 EPM net 的 Spearman（MIN ≥500、poss2627 ≥200，約 240 人），B 都 ≥ A − 0.005。
- 另報（不擋）：B 對 2K 的相關有沒有回升（回答稽核疑慮）；全卡（不限分鐘）對 2K27 的相關；各位置平均加分；代表球員表（Hukporti、Jackson-Davis、Edey、Paul Reed、Bitadze、Wembanyama、AD、Gobert、Booker、Durant 等）。

## E-290 前瞻台是否重跑（事先定規則）
- 對 EP 的 379 人算 |bonus_B − bonus_A| 的平均與最大。平均 ≤ 0.3 OVR：只在報告說明，不重跑。
- 平均 > 0.3：在本資料夾另寫腳本載入凍結 `e290_eval.py`（不改原檔、輸出寫本資料夾），新增 MIXs 臂＝每折 EP 內照第 3–4 步收縮（各折用該折卡 MIN、stats minutes、hustle MIN），同折、同 λ 網格、同 seed 20261290、2000 次 bootstrap；判準：MIXs 的 Δρ_all ≥ MIX − 0.003，且 E-290 第 1、2 條仍過。不過 → 不產卡（即使 T1–T5 全過），照實寫。

## 評分（三段式回報用）
- T1–T5 全過且 2K 相關回升 → 5/5；全過但 2K 未回升或副作用明顯 → 4/5；T3 過但其他任一條不過 → 2–3/5；T3 不過 → 1/5。
