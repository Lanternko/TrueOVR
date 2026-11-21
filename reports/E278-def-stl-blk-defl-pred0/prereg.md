# E-278 預註冊：蓋帽／抄截／干擾獨立進卡片 pred0（R-178 第二步，疊在 E-277 M1 上）

- 日期：2026-11-09。角色：lead 自做（dispatch routing＝self）。標準由執行者自訂並直接凍結（R-165）。
- 狀態：已凍結（2026-11-09，凍結時尚未建任何新臂）。
- 凍結前看過的：E-276（三項加進 DEF 顯示欄、目標是單季防守 RAPM：蓋帽三季皆正、抄截／干擾正負跳）、E-277 M1 結果。都是背景，不是本實驗證據。
- 和 E-276 的差別：E-276 只改 DEF 顯示欄、拿單季防守 RAPM 擬合；本實驗把三項放進**卡片 pred0 本身**（擬合目標＝卡片原本的 RAPM 混合貢獻，與其他 16 個屬性同一個迴歸），看 OVR 和 DEF 會不會更合理。

## 1. 臂（基準＝E-277 M1；help 位置結構全部沿用 M1）
資料：`reports/E227-lineup-transformer-r2/data/stats-<原點>.csv` 的 `blk36`、`stl36`、`deflections36`（卡原點同季，不含未來資料），按名字對到卡片列；對不到或空值的填人群平均（z＝0），數量寫進 log 並報告。新欄在 design 內 z 標準化（全體列平均與標準差），全位置共用主效應，ridge λ=1。

| 臂 | pred0 設計 |
|---|---|
| B0 | M1（直接用 E-277 `ranking-M1-*.csv`）|
| B1 | M1 ＋ blk36、stl36、deflections36 三個主效應，不設符號限制 |
| **B2（主臂）** | B1 ＋ 三項係數 ≥ 0（多蓋、多抄、多干擾不扣分）|
| B3 | M1 ＋ 只有 blk36（≥ 0）|

其他全部（擬合資料、權重、s2、bonus、align、H1、perGame、OVR 對應、用人層、E-164 S 路徑、4 原點 2022-23～2025-26）照 E-277。只寫 `reports/E278-def-stl-blk-defl-pred0/`；本機無視窗執行。

## 2. 驗收（R-178 分層；比較對象一律是 B0＝M1）
DEF 分＝onBall＋help＋pressure＋（該臂有的）blk36／stl36／deflections36 貢獻（係數由各臂 ranking 的 pred0 逐位置最小平方還原，自變數＝season_nav OD_ALL 屬性＋該臂的新欄）＋ defenseBonus − 人群平均。樣本外折、人群、目標同 E-277。

採用候選＝三條全成立：
1. **S1 係數方向穩定**：該臂新加的每一項，四個原點擬合出的係數（還原值，每 1 個 per-36）同號且為正（B1 若有任一項不同號或為負，S1 不過，但仍報告「資料要多少」）。
2. **S2 OVR 不弄壞**：ovr 對下季自製 EPM 合併 ΔR²（對 B0）≥ −0.005，且每個完整目標季 ≥ −0.010。
3. **S3 DEF 對齊不變差**：DEF 對下季自製 EPM 防守分量合併 Δρ（對 B0）≥ −0.010。

「有進步」另外看（不擋候選，回報時講清楚）：ΔR² > 0、DEF 對 EPM 防守 Δρ > 0、DEF 對同季 T 換人防守值 Δρ > 0 各自成立幾項。
多臂都是候選：主臂 B2 優先；B2 不是候選時取 S3 Δρ 最高者。都不是：照 R-178 回報哪一條、為什麼，以及資料認為三項各該多少。

## 3. 只報告
- 三項係數（每 1 個 per-36 對 pred0 的分數，以及每 1 SD）各原點、bootstrap SE（原檔 500 次）。
- 合併 ΔR² bootstrap 90% 區間（2000 次，seed 20261278）；季中折 ΔR²；對下季 RAPM net ΔR²；DEF 對下季單季防守 RAPM Δρ（只報告，R-178）。
- 例子表（2024-25、2025-26 原點）：Kevin Durant、Stephen Curry、Victor Wembanyama、Rudy Gobert、Anthony Davis、Bam Adebayo、Jarrett Allen、Isaiah Hartenstein、Alex Caruso、Amen Thompson、Trae Young、Brook Lopez、Herbert Jones、Jaren Jackson Jr.，與 B0 OVR 前十的 C：DEF 名次、OVR 名次。
- 對 B0 的 ovr 改動人數（|Δ| ≥ 3）與最大改動；名字對不到的人數。

## 4. 限制
- pressure（force）本身已含抄截／干擾，三項和 pressure 共線；係數解讀要一起看 pressure 的係數變化。
- defenseBonus 結構不動（第三步）。
