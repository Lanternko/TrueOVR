# 總評
**3/5（建議部分採用：T 的 Z2 列為候選，sim 與顯示欄不改）**
核心結論：區域威懾（對手禁區出手佔比被壓低多少，rimDet＋threeDet）確實是現有屬性沒有的資訊。陣容 Transformer 加上兩欄後，樣本外 stint 誤差顯著下降，比賽 Brier 也變好。但換算成分數，這個通道很小：每壓低 1 個百分點只值每 100 回合 0.09 分，Wembanyama 全聯盟最高也只有約 0.8 分。所以 sim 整體幾乎不動（j2 −0.004，未過），RIM／DEF 顯示欄在凍結基準下也沒過門檻。

**關鍵數據與例子**

| 層 | 臂 | 結果 | 判定 |
|---|---|---|---|
| (a) T | R2-statsZ2（＋rimDet＋threeDet） | 測試 stint MSE −5.9（90% 區間 [−8.3, −3.4]）、2026-27 前向 −9.0、測試 Brier −0.0007、前向 Brier −0.003；三個護欄都沒變差 | **過** |
| (a) T | R2-statsZ（只加 rimDet） | 測試 MSE +1.9、進攻籃板 +0.00017 | 不過 |
| (b) sim | Z（choiceDefender 禁區／三分換成 rimDet／threeDet） | 276 人對 RAPM ρ 0.432→0.428、PF/C 0.292→0.285、30 隊 MAE 3.376→3.371；聯盟禁區出手每 100 回合 42.31→42.42 | 不過 |
| (c) RIM | RZ20（0.8·D30＋0.2·rimDet） | 凍結基準 D30：每項都沒退步，但 PF/C 對 EPM 防守只 +0.005（門檻 +0.01） | 不過 |
| (c) RIM | RZ20，改用網站現行 RG 當基準（只報告） | PF/C EPM +0.010、PF/C 對 T 換人 DEF +0.048、2025-26 PF/C −0.007 | 會過 |
| (c) DEF | DZ10／DZ20 | PF/C 對 EPM 防守 −0.009／−0.032 | 不過 |

- **球員例子**：
  - RIM 加 20% rimDet（RG 基準，2026-11-21）：Jokić 140→65 名，Queta 13→7，Wembanyama 維持第 1（118.4→119.8），Stewart 2→3，Gobert 11→12。PF/C 前十換掉 R. Williams、補進 Queta，其餘不變，沒有反直覺的名字。
  - sim 淨值變化：Jokić +0.61、Gobert +0.45、Stewart +0.49、Wembanyama +0.14；Poeltl −0.62。Draymond 145→137 名，離 RAPM 的第 6 名仍很遠。
- **為什麼 sim 不動**：被擋出禁區的出手約 84% 變成三分。三分每球 1.08 分，禁區每球 1.15 分，差距很小。換算下來 Wembanyama 0.78 分／100 回合、Kessler 0.44、Jokić 0.40、Gobert 0.08，量級遠小於 sim 在單人淨值上的其他誤差。威懾在 T 有用，主要是它和誰在場、誰的出手被趕走有交互，而不是平均省下的分數。
- **副作用與注意**：預註冊把 RIM 基準寫成「現行 D30」，但凍結前主線已把網站 RIM 換成 RG（R-196，工作樹落後 origin/main，L-153）。依凍結規則判 D30＝不過；RG 那欄只是報告，沒有事後放寬門檻。

**要你決定的事**
1. **T 的 Z2**（建議採用為候選）：照 E-285／E-286 的經驗，stint MSE 變好不保證球隊評分變好。下一步先跑 E-286 跨季球隊評分回測，並和 E-307 的 TG 合併成一臂一起測（兩者都是護框類欄位）。過了才換 `T_WEIGHTS`。
2. **RIM 要不要摻 20% rimDet**：
   - A（建議）：先不上，12 月後的比賽另寫預註冊，以 RG 為基準驗收一次。
   - B：直接上 RZ20（Jokić 回到 60 多名、Queta 進前十）。這是用報告欄位決定，不是凍結判定。
3. **sim、DEF 不改**：choiceDefender 維持原樣（只給建議，R-154）。DEF 欄不摻 rimDet。

---
產出：`results/t/eval.json`（T）、`results/judge.json`（sim）、`results/display-rg0.json`（凍結基準 D30）、`results/display-rg1.json`（RG 基準，只報告）；`results/display.json` 是基準漂移前的第一次執行，不用。sim 原始輸出 `checkpoint-Z.jsonl`／`rr-Z.jsonl` 在 5090 `~/side_projects/pure_ovr/experiments/e309/sim/reports/E309/`。決定性檢查：B 臂新 harness 重跑 10 人＋2 seed，和 E-166 逐位元相同。
