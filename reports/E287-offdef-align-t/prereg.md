# E-287 預註冊：網站 OFF／DEF 顯示欄和 Transformer 換人值掛鉤（R-178 防守第三步＋進攻同步）

日期 2026-11-09。使用者：「採用後 OFF 和 DEF 要和 Transformer 掛鉤」→ E-286 後同意開跑。只動顯示欄，OVR 不動。
T 用 B 版（E-227 R2-stats 架構；E-286 顯示 X 版跨季變差，不用）。

## 資料與人群
- 原點 t：2022-23、2023-24、2024-25、2025-26；卡＝E-277 M1（R-179 基準）`ranking-M1-<t>.csv`。
- 人群＝t 季卡 MIN ≥ 500 且名字唯一對上 playerId（E-269／E-274 同規則；`pool-<t>.json`）。
- 現行值（w=0）：OFF0＝pred0 進攻 11 項能力值貢獻（同 season_nav.off_def，不含 T6 影響力 25% 混合——歷史卡沒有逐季 T6，限制照寫）；DEF0＝onBall＋help＋pressure 貢獻＋defenseBonus−人群平均（同 off_def）。
- T 值：E-274 換人法（3000 組、seed 20261108、所有人同批陣容），同時記本隊每 100 回合得分（Toff＝減池平均）與對手得分（Tdef＝−(值−池平均)）。權重只用 ≤t 季：2022-23 T2223、2023-24 T2324、2024-25 T2425（E-228）、2025-26 E-227 R2-stats 線上權重。特徵＝t 季球員表。
- 混合：顯示值(w)＝(1−w)·z(現行)＋w·z(T)，z 在人群內；上線時再乘回現行的標準差、加回平均（單位不變，ρ 不受影響）。w ∈ {0, 0.25, 0.5, 0.75, 1}。

## 驗收（R-178 分層：EPM 為主、2K 與直覺為輔，單季 RAPM 不用）
- 主：t 季顯示值對 t+1 季自製 EPM 分量的 Spearman ρ（OFF↔O、DEF↔D；×P.wfun(mpg)、stintPoss ≥ 1000，同 E-277 epm_d），3 折（t＝2022-23～2024-25）依人數加權合併。
- **選 w（OFF、DEF 各自）**：合併 Δρ（對 w=0）≥ −0.010 且每折 Δρ ≥ −0.020 的 w 中取**最大的**（目的是盡量對齊 T，前提是不讓 EPM 對齊變差）；Δρ > +0.010 另記為「EPM 也變准」。
- 留一折檢查：只用兩折選 w，看第三折 Δρ 是否 ≥ −0.020。
- 輔（只報告）：t＝2025-26 對 2K27 綜合（防守＝Block、Steal、Interior Defense、Perimeter Defense、Help Defense IQ 平均；進攻＝Three-Point、Mid-Range、Close、Layup、Draw Foul、Ball Handle、Pass Accuracy、Pass Vision、Pass IQ、Shot IQ、Offensive Consistency 平均）的 ρ；對 T 本身的 ρ。
- 直覺檢查（2025-26，報告）：DEF Durant vs VanVleet、Durant vs Curry 名次；OVR 前十 C 的 DEF 名次；Caruso、Amen Thompson、Wembanyama、Gobert；OFF 前十名單。

## 評分
- 5：OFF、DEF 都選到 w ≥ 0.5 且留一折站得住、直覺檢查方向對；有任一 EPM 退步超門檻不給 5。
- 選到 w=0（T 一點都放不進去）＝1–2。

## 不做
- 不看結果後改格點、門檻、人群（L-026）；不調 T 超參數。
