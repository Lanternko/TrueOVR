# 卡片屬性小樣本收縮（2025-26）預註冊

寫於執行前（2026-10-18），在修改任何程式碼之前。基準：commit 36c82a1 的混合目標卡片 OVR
（`reports/ovr-blended-2025-26/blend.py`，α = 0.5，position-interactions、ridge 1）。

## 動機

`scripts/build_season_league.js` 把 per-minute 或比率類統計直接換成百分位（40–99），
沒有任何小樣本收縮。結果是低上場時間的球員拿到極端屬性：

- Norchad Omier（24 分鐘、6 場）：tovSkill 99、rebound 95.4，混合排名第 23。
- Javon Small（830 分鐘、RAPM 為負）：pass 89.8，混合排名第 14。
- 基準混合排名前 50 裡，MIN < 500 的球員有 6 位：Ty Jerome（339）、Omier（24）、
  Dejounte Murray（389）、Obi Toppin（424）、Walker Kessler（154）、Charles Bassey（153）。

## 收縮規則（在百分位映射之前套用）

適用的屬性是目前直接由比率統計排名的四項：drive（FTA/FGA）、tovSkill（−TOV / 使用回合）、
pass（AST_PCT）、rebound（REB_PCT）。此外還有 calibrate.py 推導的 creation
（自主出手數，每 36 分鐘）。

每項統計 x、每位球員 i（出場時間 m_i 用全季總分鐘）：

    x̃_i = (m_i · x_i + k · μ_pos(i)) / (m_i + k)

- pos：卡片位置，也就是建檔腳本依身高切出的 PG/SG/SF/PF/C。
- μ_pos：該位置所有 MIN > 0 球員的 x，以 MIN 加權平均。
- k（虛擬分鐘數）：每項統計各估一個，用經驗貝氏的動差法。假設
  E[(x_i − μ_pos)²] = τ² + σ²/m_i，取 MIN ≥ 50 的球員，用 OLS 把 (x_i − μ_pos)² 迴歸到
  [1, 1/m_i] 上，令 k = σ²/τ²，再截在 [50, 2000] 之間。若 τ² ≤ 0 或 σ² ≤ 0，就用 k = 500。
- 百分位池維持不變（GP ≥ 30 且 MPG ≥ 20）。池內球員也用收縮後的值排名，兩邊一致。
  池內球員都至少有 600 分鐘，受影響很小。

不在範圍內的項目：

- 投籃四項（long/mid/short/ft）：已有 100 次出手的收縮，朝聯盟平均。
- 防守兩項：已有 D_FGA/(D_FGA+200) 的收縮。
- stamina：它本身就是 MPG。
- physique：身材，不是抽樣統計量。
- pressure：來自 RAPM，已經過 ridge 收縮。

實作上用 `--shrink` 旗標，輸出到另一個檔案 `data/season-league-shrunk.json`。
不加旗標時的輸出必須與現行 `data/season-league.json` 完全相同。
calibrate.py 與 blend.py 加上 `--league` 與 `--out` 參數。league 檔帶有 shrinkage
方法說明時，calibrate.py 用同一個規則收縮 creation。

## 驗證協定

沿用 blend.py：5 折 × 10 次重複（種子 0–9），以球員為單位切折，α 網格 {0, 0.25, 0.5, 0.75, 1}。
評估對象是 pooledPoss ≥ 5000 的 414 位球員，目標檔與 RAPM 檔都不變。
基準與收縮版用同樣的種子、同樣的球員，只有卡片屬性不同。

## 關卡（事先固定，全部通過才採用）

比較在固定 α = 0.5 下進行（即目前採用的 α）：

1. **淨值不降**：保留折 ρ_N(收縮) − ρ_N(基準) ≥ 0（10 次重複平均的點估計）。
2. **防守不降**：保留折 ρ_D(收縮) − ρ_D(基準) ≥ 0（同上）。
3. **低分鐘球員離開前 50**：在全資料擬合（α = 0.5）的卡片排名裡，前 50 名沒有 MIN < 500 的球員，
   而且 Javon Small 排在 50 名之後。

附帶報告（不作關卡）：

- ρ 差值的配對 bootstrap 95% CI：把 10 次重複的 OOF 預測取平均，重抽 2000 次。
- sim R²。
- blend.py 自身的選 α 規則在收縮後會選哪一個 α。
- calibrate.py 重新選出的模型形式與 ridge。
- 前 50 名中 MIN < 1000 的人數（基準 10 位）。
- Omier、Small、Jerome、Murray、Matković 的排名變化，以及每 +10 屬性點的價值。

## 已知限制

- sim 目標（v53 s8 expected）是用未收縮的卡片模擬出來的。收縮後的輸入對應的是舊屬性產生的
  目標。低分鐘球員的 mc 很大、權重很低，所以影響有限，但這不是重新模擬的結果。
- 動差法估出的 k 是每項統計的單一值，不隨位置改變。
- 收縮只改卡片屬性，不改遊戲內 sim 的輸入。若採用，要另外決定是否以 `season-league-shrunk.json`
  取代遊戲資料。
