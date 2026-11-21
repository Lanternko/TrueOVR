# 卡片屬性小樣本收縮（2025-26）結果

預註冊見 `preregistration.md`（寫於修改程式碼之前）。重現指令見 `evaluate.py` 檔頭。

## 結論：不採用（關卡 3 未通過）

| 關卡（α = 0.5） | 基準 | 收縮 | Δ（配對 bootstrap 95% CI） | 結果 |
|---|---|---|---|---|
| 1. 保留折 ρ_N | 0.4545 | 0.4560 | +0.0014 [−0.010, +0.013] | 通過 |
| 2. 保留折 ρ_D | 0.2534 | 0.2583 | +0.0050 [−0.006, +0.018] | 通過 |
| 3. 前 50 無 MIN < 500，且 Small 在 50 名後 | 6 位；Small 第 14 | 3 位；Small 第 19 | — | **未通過** |

兩個 ρ 差值的 CI 都包含 0，所以收縮對 RAPM 的預測力幾乎沒有影響，看不出變好或變差。
關卡 3 的兩個條件都沒有達到。

## 實作

- `scripts/build_season_league.js --shrink`：輸出到 `data/season-league-shrunk.json`。
  不加旗標時的輸出與現行 `data/season-league.json` 逐位元組相同（git diff 為空）。
- `calibrate.py` 與 `blend.py` 新增 `--league` 和 `--out` 參數。league 檔帶有 shrinkage
  說明時，calibrate.py 會收縮 creation。
- 基準以 `--out` 重跑，排名與 `reports/ovr-blended-2025-26/ranking.csv` 完全相同。
  原本的報告輸出沒有被覆寫。

動差法估出的虛擬分鐘數 k：

| 屬性 | k |
|---|---|
| drive | 139 |
| tovSkill | 2000（截到上限） |
| pass | 50（截到下限） |
| rebound | 50（截到下限） |
| creation | 500（τ² 或 σ² ≤ 0，用預設值） |

pass 和 rebound 的球員間真實差異（τ²）比抽樣雜訊大很多，所以 k 被截到下限，收縮很弱。
tovSkill 則幾乎全被拉到位置平均。

## 附帶報告

**calibrate.py**：兩邊都選 position-interactions、ridge 1。CV R² 從 0.459 降到 0.456。

**blend.py 保留折 sim R²**：

| α | 0 | 0.25 | 0.5 | 0.75 | 1 |
|---|---|---|---|---|---|
| 基準 | 0.459 | 0.451 | 0.409 | 0.331 | 0.212 |
| 收縮 | 0.456 | 0.448 | 0.406 | 0.325 | 0.201 |

收縮版用 blend.py 自己的選 α 規則會選 **0.25**，不是 0.5。原因是 sim R²(α = 0) 降了，
下限也跟著降到 0.406，而 α = 0.5 的 0.40570 剛好低於 0.40571。這個差距是捨入等級，
不代表收縮版適合較小的 α。關卡都是用固定 α = 0.5 判定的。

**前 50 名（α = 0.5 全資料擬合）**：MIN < 1000 的人數從 10 位降為 7 位。
完整排名在 `ranking-alpha05-{baseline,shrunk}.csv`。

| 球員 | MIN | 基準 | 收縮 |
|---|---|---|---|
| Norchad Omier | 24 | 23 | 74 |
| Charles Bassey | 153 | 42 | 66 |
| Obi Toppin | 424 | 39 | 51 |
| Walker Kessler | 154 | 41 | 43 |
| Ty Jerome | 339 | 20 | 24 |
| Dejounte Murray | 389 | 27 | 28 |
| Javon Small | 830 | 14 | 19 |
| Karlo Matković | 912 | 7 | 9 |

## 解讀

- **Omier、Bassey、Toppin 的問題確實是收縮能處理的。** 他們的高排名主要來自 tovSkill
  和 rebound 的極端百分位，tovSkill 的 k = 2000 把這部分壓掉了。
- **Jerome、Murray、Kessler 仍在前 50。** 收縮後 Jerome 的 pass 是 98.4，Murray 是 95.6；
  Kessler 的 rebound 是 96.1，drive 是 95.4。pass 和 rebound 的 k 只有 50，drive 的 k 是 139，
  對 150–400 分鐘的球員作用很小。所以他們的排名幾乎沒變。
- **Javon Small 只從第 14 降到第 19。** 他的分數主要來自 long 投籃屬性（84.2）和 pass。
  long 不在範圍內，pass 的收縮又很弱。
- **限制**：sim 目標（v53 s8 expected）是用未收縮的卡片模擬出來的，
  所以收縮版是在擬合舊屬性產生的目標。

## 可能的後續（未預註冊，需另開）

1. 用分半信度（split-half：同一季前後半或奇偶場）估 k，取代截到邊界的動差法。
   動差法對 pass 和 rebound 估出的 τ² 可能偏大，因為不同位置混在一起計算。
   這是 Jerome、Murray、Kessler 留在前 50 的直接原因。
2. 投籃屬性的 100 次出手收縮目前朝聯盟平均。可以改為朝位置平均，並重新估計
   虛擬出手數。這是 Small 和 Jerome 排名偏高的主要來源。
3. 在 blend 的擬合權重或卡片 OVR 裡直接加入上場時間的信度，例如乘上 m/(m+k)，
   而不是只在屬性層收縮。
4. 用收縮後的卡片重新模擬 sim 目標，消除上面的限制。
