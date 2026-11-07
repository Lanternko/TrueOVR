# card 0.2.10（E-175 滑動窗口卡上線，R-111／R-114 PATCH）

版本規則：前 20 名只進出各 1 人、前 100 名移動 >=10 名 18 人，屬 PATCH（R-114）。
內容：drive、foulDraw、ft、mid、pass、rebound、short、tovSkill 這 8 項屬性改用四季滑動窗口 U（c=82；R-076 window_weights；過去季收縮採 ovr-v61-shrink-history-2025-26 的方法 b）。其他屬性、RAPM 部件卡、用人層係數、OVR 錨（PR1/PR50/PR99）、H1 cap 參照、r_repl 全部凍結為 0.2.9a（lead 2026-11-01 裁定 B＋全凍結，不重擬合）。

## 建法與驗證
- 指令：`python -I -X utf8 reports/card-0.2.10/build_card_0210.py --rebuild`
- 自我核對：builder 餵 0.2.9a 的 V 屬性（`tail-V8.csv`）時，ranking 與 0.2.9a 逐位元相同（sha256 b7972182…7580ef）；work/self、work/V8 已驗。
- 輸出 `ranking.csv` sha256 84e9590b28161a23b589e1918ad410f09d6af51a119af8ee57f7beca1146e6c1。
- 所有輸入 sha256 記在 `summary.json`（sources_sha256、frozen_sources_sha256、rapm_inputs_sha256、part_card_sha256）；凍結值在 `frozen.json`（b0690645…8f5e5）。
- 未使用任何 2026-27 結果（L-026）。

## 對 0.2.9a（出賽 >=500 分鐘 379 人）
- 排名 Spearman 0.9951；OVR 差 平均 -0.12、sd 1.22、p90 |差| 2.0。
- 前 20：進 Embiid（23→18）；出 Michael Porter Jr.（20→40）。
- 前 100 名移動 >=10 名：18 人；前 300 名：94 人。

| 球員 | 0.2.9a 名次／OVR | 0.2.10 名次／OVR |
|---|---|---|
| Tatum | 8／92.8 | 8／92.7 |
| Jalen Williams | 10／88.2 | 11／87.3 |
| Flagg | 82／76.1 | 68／77.0 |
| Edwards | 14／87.5 | 13／86.8 |
| Banchero | 140／72.7 | 133／73.2 |
| Jokić | 7／93.4 | 7／93.5 |
| A. Davis | 21／84.6 | 21／84.8 |
| Embiid | 23／84.0 | 18／85.2 |

## 對 E-175 一階近似
一階近似：Spearman 0.979、A. Davis 22→13、Embiid 23→18、Flagg 87→72。
本卡 Embiid 23→18、Flagg 82→68，方向一致。A. Davis 維持 21：他被 RAPM 部件卡的上限綁住，屬性改變傳不進 OVR（與近似不同，近似沒有走完整用人層）。Porter Jr. 20→40 為近似清單沒有的大動，請 lead 留意（tail 對照：foulDraw 78.3→63.8、pass 69.0→55.6、short 93.5→91.2、ft 79.7→76.3，主因是 foulDraw 與 pass 窗口值明顯低於單季）。

## 已知限制
- 凍結 OVR 錨與 r_repl：8 項屬性分布改變後，錨沒有重新對齊（政策 B）；E-175 §3 已驗 8 項 SD 比在 [0.9,1.1]。
- 換季跳動見 E-175 report.md：季末到 2026-27 第 0 天 p90 |ΔOVR| V 4.78／U 3.46。
