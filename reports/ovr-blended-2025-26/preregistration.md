# 卡片 OVR 混合目標（sim + RAPM）預註冊

寫於執行前（2026-10-18）。基準：`reports/ovr-calibrated-2025-26/calibrate.py`，目標
`reports/ovr-v53-2025-26/calibration-target-s8-expected.csv`，position-interactions、ridge 1，
交叉驗證 R² 0.459（已重現）。

## 動機

殘差分析（414 位 pooledPoss ≥ 5000 的球員）：

- 卡片 OVR 對 RAPM 的 Spearman：淨值 0.374，防守 0.205；sim 目標本身：淨值 0.362，防守 0.256。
- 同一組卡片屬性直接以交叉驗證擬合 RAPM（不含 stamina）可達到：淨值 0.44，防守 0.46。
  資訊在屬性裡，是目標與映射把它丟掉。
- 卡片把 sim 已抓到的防守側翼訊號再壓下去：Caruso 的 sim 排名 78，卡片排名 306；
  White 142 → 241；Daniels 115 → 330。改用平方項或位置交互作用，sim R² 會上升，
  但對 RAPM 的 ρ 不會上升。

## 目標

每位球員 i：

    t_i = (1 − α) · y_i + α · r_i      （pooledPoss ≥ 1000 的球員）
    t_i = y_i                          （其他球員）

- y_i：現行 sim 目標（每 36 分鐘、位置置中）。
- r_i = 0.75 · pooledNet_i − 該位置的平均。0.75 ≈ 每 36 分鐘 75 回合 / 100，把
  每百回合換成每 36 分鐘。該位置的平均以卡片 MIN 加權，算在 pooledPoss ≥ 1000 的球員上，
  跟 sim 的位置置中一致。
- 蒙地卡羅變異縮為 (1 − α)² · mc，s2 照原本方式重估。
- 模型形式與 ridge 固定為 position-interactions、λ = 1，讓比較只隔離 α 的效果。

α 網格（事先固定）：0、0.25、0.5、0.75、1。

## 驗證（球員保留折）

- 5 折 × 10 次重複（種子 0–9），以球員為單位切折。每折只在訓練球員上建 t、擬合，
  再預測保留球員。
- sim R²：保留折預測對原始 sim 目標 y 的加權 R²。權重採 α = 0 的權重，跟 calibrate.py
  的 cv_score 定義相同。
- ρ_N、ρ_D：保留折預測對 RAPM pooledNet、pooledD 的 Spearman，只算 pooledPoss ≥ 5000 的球員
  （與 v53 關卡同一組）。
- 每個 α 取 10 次重複的平均。

## 選 α 規則

選最大的 α，使 sim R² ≥ R²(α = 0) − 0.05（絕對值；約 0.459 → 不低於約 0.41）。

## 採用關卡（對選中的 α，全部通過才採用）

1. ρ_N(α) > ρ_N(0)，且配對 bootstrap 95% CI 下界 > 0。
2. ρ_D(α) > ρ_D(0)，且配對 bootstrap 95% CI 下界 > 0。
3. sim R² 條件即上面的選 α 規則。

配對 bootstrap 的做法：把 10 次重複的保留折預測取平均，對 ≥ 5000 回合的球員重抽 2000 次。

若沒有任何 α > 0 通過，就不採用，維持現行卡片公式。

## 附帶報告（不作關卡）

lastSeasonNet ρ、各位置 ρ、焦點球員排名（Caruso、White、Daniels、Jones、Smart、
Matković、Stewart、Robinson、Edey、Gobert），以及每 +10 屬性點的價值變化。

## 已知限制

- 「壓迫」屬性本身由四因素 RAPM 推得，與 RAPM 目標並非獨立。
- RAPM 涵蓋四季，sim 只看 2025-26。
- 混合後卡片 OVR 不再只反映遊戲內 sim 價值。卡片與遊戲內實際強度會有落差，屬於平衡面的取捨。
- 評估用的 RAPM 與訓練用的是同一個量。保留折只防止逐球員過擬合，不是獨立的外部驗證。
