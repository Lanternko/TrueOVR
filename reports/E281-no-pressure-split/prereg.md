# E-281 預註冊：pred0 拿掉 pressure，改用抄截／蓋帽／干擾三項（疊在 E-277 M1 上）

- 日期：2026-11-09。角色：lead 自做（dispatch routing＝self）。標準由執行者自訂並直接凍結（R-165）。
- 狀態：已凍結（2026-11-09，凍結時尚未建任何新臂）。
- 來源：使用者「把 press 拿掉，拆出單獨三項」。E-278 已看過：pressure 還在時，抄截四原點穩定為正、干擾 ≈0（和 pressure 共線）、蓋帽 2025-26 翻號。本實驗看拿掉 pressure 後三項各自該多少、DEF 會不會更合理。

## 1. 臂（pred0 設計拿掉 pressure：`--dropAttr pressure`；新欄全位置共用主效應，ridge λ=1；三項一律用**四季滑動窗口**（t−3～t 分鐘加權，最早 2021-22），與 pressure 原本的窗口口徑相同）
| 臂 | pred0 設計 |
|---|---|
| C0 | M1（含 pressure，＝E-277 `ranking-M1-*`）|
| **C1（主臂）** | M1 − pressure ＋ stl36、blk36、deflections36，三項 ≥ 0 |
| C2 | C1 不設符號限制 |
| C3 | M1 − pressure（不補任何項；看 pressure 本身值多少）|
| C4 | M1 − pressure ＋ stl36、deflections36 ≥ 0（蓋帽留給 E-280 決定）|

其他照 E-277／E-278。只寫 `reports/E281-no-pressure-split/`（calibrate 共用 `reports/E280-blk-weight/calibrate_wing_t_dx.py`）；本機無視窗。

## 2. 驗收（比較對象 C0）
DEF 分＝onBall＋help＋（該臂有的）三項貢獻（不含 pressure；係數由 ranking pred0 逐位置還原，自變數＝OD_ALL 去掉 pressure＋該臂新欄）＋defenseBonus−人群平均。C0 的 DEF 照 E-278（含 pressure）。
採用候選＝三條全成立：
1. **S1**：該臂新加的每一項，四原點擬合係數都 > 0（≥0 臂被夾到 0 也算不過）。C3 沒有新項，S1 視為不適用（只當參考，不當候選）。
2. **S2**：OVR 對下季 EPM 合併 ΔR² ≥ −0.005 且每折 ≥ −0.010。
3. **S3**：DEF 對下季 EPM 防守分量合併 Δρ ≥ −0.010。
「有進步」另外看：ΔR² > 0、DEF 對 EPM 防守 Δρ > 0、DEF 對同季 T Δρ > 0。
多臂候選：C1 優先，否則 S3 Δρ 最高者。都不是：照 R-178 回報哪條、為什麼、資料認為三項各該多少。

## 3. 只報告
三項係數（每 1 個 per-36、每 SD、bootstrap SE）各原點；對單季防守 RAPM Δρ（R-178 只報告）；季中折；ΔR² bootstrap 90% 區間（2000 次，seed 20261281）；例子表（同 E-278 名單）；ovr 改動人數。
