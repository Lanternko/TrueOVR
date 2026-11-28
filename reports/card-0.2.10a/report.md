# card 0.2.10a（L-102／F-128：T6 補回 Jokić、Wembanyama）

# 總評
**2/5 主目標達成 但是有副作用**

**這次目標**：修 BPM 解析錯（BBRef 聯盟第一包在 `<strong>`，讀成空值），讓 Jokić、Wembanyama 回到 2025-26 T6 目標，卡片重建。

**進步了什麼**
- Jokić 第 7（93.5）→第 3（100.6），align 0→1.23。
- Wembanyama 有了目標，align 0→0.85（名次維持第 2）。
- 自我核對：舊候選檔重現 0.2.10 三份 --rapm 檔與 ranking.csv 逐位元相同（84e9590b…）。

**退步了什麼**
- H1 封頂（卡片名次不能高於 T6 名次，capMargin 0）以前沒有 Jokić 這個 T6 第 1 擋著；他回來後，SGA、Wembanyama、Jokić、Giannis 的 predictedPer36 全被壓到 5.386（Jokić 自己的自然值），前四名只剩用人層在分。
- SGA OVR 118.8→103.8（仍第 1）；Kawhi 102.2→94.1，第 3→第 6；Holmgren 10→13、Amen Thompson 28→39。前 20 名 15 人名次有動（沒人進出前 20）。
- 對四季 pooled RAPM 的 Spearman 0.6975→0.6957（379 人，MIN≥500）、前 25 名 0.591→0.576：沒變好（樣本內，只權衡）。

**直觀證據**

| 球員 | 0.2.10 名次／OVR | 0.2.10a 名次／OVR | pred/36 |
|---|---|---|---|
| SGA | 1／118.8 | 1／103.8 | 8.02→5.39 |
| Wembanyama | 2／105.4 | 2／100.9 | 6.20→5.39 |
| Jokić | 7／93.5 | 3／100.6 | 4.16→5.39 |
| Giannis | 4／101.3 | 4／99.2 | 5.77→5.39 |
| Dončić | 5／98.4 | 5／98.4 | 4.34→4.34 |
| Kawhi | 3／102.2 | 6／94.1 | 5.77→4.33 |

**要你決定的事**
- 上線與否：0.2.10a 直接上線（Jokić 第 3，但前段壓縮）／先不上，另開實驗處理 H1 封頂（例如 capMargin>0 或封頂只看名次不壓到同值，要預註冊）。
- E-186 用的是缺 Jokić 的 T6，要改用修正後候選檔重跑。

## 建法（G2）
- 解析修正：`reports/E142-card-target/c0d_collect.py` bpm_parse（`.*?</td>` 後去標籤）；同式的 `reports/salary-corr/proxy.py` 一起修。重產 `data/external-impact/bpm/bpm_*.csv`（舊檔 `pre-L102/`；逐格核對只有原本空格被補上：Jokić 四季、Wembanyama DBPM、Harden、Giannis 等聯盟第一，以及 games／mp 聯盟第一）；`phase1-work/cands/*.pkl` 重產（舊檔 `pre-L102/`；T1、T4 不變）。
- 2025-26 T6：504→506 人（+Jokić 12.74 第 1、+Wembanyama 9.90 第 4），其他人重標準化最多動 0.10。
- `make_t6_fixed.py` → `work/t6/{repro,fixed}`；`run_parts.py <tag> tail-U.csv <t6tag>`；`use_layer.py frozen`。屬性 tail-U.csv、frozen.json 與 0.2.10 同檔。
- 指令：`python -I -X utf8 reports/card-0.2.10a/build_card_0210a.py --rebuild`；ranking.csv sha256 a868f7b91924d58a73c06083e8a50bbd8bfabb149348518e2691fcdda8405763；輸入 sha 在 summary.json。
- 未使用任何 2026-27 結果。未接 status_snapshot／網站（OFFICIAL_CARD 仍是 0.2.10），npm test 沒跑（線上沒變）。
- 受影響、未重跑：E-142／E-153 目標回測（四季都缺 Jokić）、F-125 T6 前 25 名對照、進行中的 E-186。
