# E-277 預註冊：卡片 pred0 的 help（協防護框）位置係數改成 PG→C 單調遞增

- 日期：2026-11-09。角色：lead 自做（dispatch routing＝self）。來源：使用者 R-178 防守三步的第一步。標準由執行者自訂並直接凍結（R-165）。
- 狀態：已凍結（2026-11-09，凍結時尚未建任何新臂、沒看任何新臂的係數或結果）。
- 凍結前看過的：E-269 的 A0／A1 結果（A1＝help 全位置共用，合併 R² 變差）、A0 各原點 help 係數（U 字形）。這些是已知背景，不是本實驗的證據。

## 0. 背景（讀程式碼與 E-269 得到）
`calibrate_wing_t.py` 的 pred0：16 個屬性 z 值主效應全位置共用，另有 {long, short, pass, rebound, help} × 位置 dummy 交互（C 為基準），ridge λ=1。所以每個位置的 help 斜率＝主效應＋該位置交互。現行各原點斜率呈 U 字形（例：2022-23 每點 PG .053、SG .004、SF −.025、PF .052、C .047），SF／SG 的護框幾乎不算分，而 PG 卻很高，違反「越靠近籃框的位置，護框越重要」的籃球直覺（R-178）。

## 1. 臂（只改 pred0 中 help 的位置結構；其餘交互、bonus、align、H1、perGame、OVR 對應、用人層全部照 E-269／E-164 S 路徑重跑）
| 臂 | help 的位置結構 |
|---|---|
| A0 | 現行（直接用 E-269 的 `ranking-A0-*.csv`，已逐位元重現 E-164） |
| A1 | 參考：help 全位置共用（直接用 E-269 的 `ranking-A1-*.csv`） |
| **M1（主臂）** | 保序（isotonic）：help 欄改為基底 z_help ＋ 4 個累加欄 z_help·1[位置序 ≥ k]（k＝SG、SF、PF、C；位置序 PG<SG<SF<PF<C），累加欄係數 δ_k ≥ 0 → 斜率 PG ≤ SG ≤ SF ≤ PF ≤ C。全部欄 ridge λ=1（同原檔），有界最小平方（scipy `lsq_linear` bvls） |
| M2 | M1 ＋ 基底（＝PG 斜率）≥ 0：護框對任何位置都不扣分 |
| M3 | 線性趨勢：z_help ＋ z_help·(位置序 − 2)，趨勢係數 ≥ 0（每往籃框一個位置，斜率加同一個量）|

- M1–M3 都只動 help；其他四個交互（long、short、pass、rebound）不變。
- 擬合資料、權重、s2 迭代、z 標準化、500 次 bootstrap、CV 打分口徑全部沿用原檔。
- 四個原點 2022-23、2023-24、2024-25、2025-26 各自重建整張卡（E-164 S 路徑，T6 候選用 `cands/pre-L102/`）。
- 本機無視窗執行（每卡約數十秒、輸入只在本機 repo；子程序 `CREATE_NO_WINDOW`）。只寫 `reports/E277-help-monotone/`；原檔、`src/`、正式卡、線上版本唯讀。

## 2. 驗收（R-178 分層：結構目標＋OVR 不弄壞＋對齊客觀指標；單季防守 RAPM 只報告）
樣本外折同 E-269：卡原點 t → 下季 t+1，完整季三折（2022-23→23-24、23-24→24-25、24-25→25-26），合併＝依人數加權。人群同 E-269（MIN ≥ 500、名字唯一）。DEF 分＝onBall＋help＋pressure 三項貢獻（從各臂 ranking 的 pred0 逐位置最小平方還原係數）＋ defenseBonus − 人群平均，同 E-269／`season_nav.off_def` 做法。

採用候選＝下列三條全成立（每臂各自判定）：
1. **S1 結構到位**：四個原點、還原出的 help 斜率都滿足 PG ≤ SG ≤ SF ≤ PF ≤ C（容許 1e-6），且 C 斜率 > PG 斜率（不是全部壓平成共用）。
2. **S2 OVR 不弄壞**：卡片 ovr 對下季自製 EPM（net × 分鐘權重）的合併 ΔR²（對 A0）≥ −0.005，且每一個完整目標季 ΔR² ≥ −0.010。
3. **S3 DEF 對齊客觀防守指標不變差**：DEF 分對下季自製 EPM 防守分量（D × 分鐘權重，stintPoss ≥ 1000）的合併 Spearman Δρ（對 A0）≥ −0.010。

多臂都過：主臂 M1 優先；M1 不過才看 M2、M3 中 S3 Δρ 較高者。都不過：照 R-178 回報哪一條沒過、原因，並提下一步（不是「維持現行」了事）。

## 3. 只報告（不影響判定）
- 合併 ΔR² 的 bootstrap 90% 區間（每折重抽球員，2000 次，seed 20261277）。
- DEF 分對同季 Transformer 換人防守值（E-274 `d2-<t>.json`，取負；有 2022-23～2024-25 三個原點）的 Spearman ρ 與 Δρ。
- DEF 分對下季單季防守 RAPM（D × W，poss ≥ 1000）的 ρ 與 Δρ —— **只報告，不否決**（R-178：有體系偏誤，現行 DEF 摻 RAPM 加分）。
- 卡片 ovr 對下季 RAPM net 的 ΔR²（R-131，只報告）。
- 季中折（2025-26 原點 → 2026-27 EPM）ΔR²。
- 各臂各原點各位置的 help 斜率（每 10 點）；M2 是否被夾到 0；δ_k 有幾個被夾到 0。
- 例子表（2024-25 原點為主，因 VanVleet 2025-26 MIN < 500；2025-26 原點也列）：Kevin Durant、Fred VanVleet、Victor Wembanyama、Rudy Gobert、Anthony Davis、Bam Adebayo、Jarrett Allen、Alex Caruso、Stephen Curry、Amen Thompson、Trae Young 的 DEF 分、DEF 名次、OVR 名次；另列 A0 OVR 前十的 C。重點看 Durant 對 VanVleet 的 DEF 名次差、護框長人名次。球員一律全名（L-122）。
- 各臂對 A0 的 ovr 改動人數（|Δ| ≥ 3）與最大改動。

## 4. 偏離與限制
- 本實驗只做第一步（help 位置結構），不改 defenseBonus（只加不扣、按位置比的問題留第三步）、不加蓋帽／干擾／抄截（第二步）。所以 Durant 對 VanVleet 的名次即使改善，也不預期完全反轉；DEF 分中 defenseBonus 的比重不變。
- A0／A1 結果在 E-269 已看過；新臂未看過。樣本內 CV 分數只報告（R-007）。
