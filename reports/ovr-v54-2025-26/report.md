# v54：投籃屬性（三分／禁區）納入出手量——結果

本報告只陳述量化結果與限制，不建議是否採用、不切換任何對局實際使用的資料
（`data/season-league.json` 全程未被修改，見下方驗證）。

## 1. 設計

v53 的卡片 OVR 在把三分（`long`）與禁區（`short`）命中率從原始樣本收縮到位置先驗時，
固定使用虛擬樣本數 100（`(makes + 100·prior)/(attempts + 100)`）。這對出手量很少的球員會
過度拉向先驗，出手量很大的球員又收縮不足。

v54 只改這一步，只影響 `long`/`short`（`mid`/`ft` 不動）：

- 新增 CLI 旗標 `--shooting-eb`（`scripts/build_season_league.js`），不加旗標時輸出與現行
  `data/season-league.json` 逐位元組相同。
- 用 method-of-moments 估計每個分區（long/short）的可靠度：樣本量 ≥20 的球員，
  Var(p_i) = τ² + p̄(1−p̄)/n_i，解出 k_z = p̄(1−p̄)/τ² − 1，clamp 到 [50, 2000]；τ²≤0 時退回 k=500。
- 先驗均值 μ_pos 改用出手量加權、依卡片位置（PG/SG/SF/PF/C，`posOfHeight` 身高分帶）分組的
  原始命中率，而非全聯盟單一先驗。
- 收縮後命中率 = (makes + k_z·μ_pos)/(attempts + k_z)，再走原本的 `inverse()` 曲線查表轉成屬性值。
- k_z、τ²、各位置 μ 寫入輸出 JSON 的 `methodology.shootingReliability` 區塊。
- 限定 2025-26 球季（見第 5 節限制）。

估計結果（`data/season-league-v54.json` → `methodology.shootingReliability.zones`）：

| 分區 | k | τ² | p̄（聯盟平均） | 達標人數/總人數 |
|---|---:|---:|---:|---:|
| 三分（long） | 202.08 | 0.001135 | 0.3604 | 440/547 |
| 禁區（short） | 80.14 | 0.003006 | 0.5779 | 473/576 |

各位置先驗均值 μ_pos：

| 分區 | PG | SG | SF | PF | C |
|---|---:|---:|---:|---:|---:|
| 三分 | 0.3619 | 0.3642 | 0.3579 | 0.3510 | 0.3484 |
| 禁區 | 0.5391 | 0.5612 | 0.5699 | 0.6046 | 0.6259 |

三分的 k（202）比禁區的 k（80）大，代表三分命中率在球員間的真實差異（τ²）比禁區小，
因此同樣出手量下三分被拉向先驗的力道更強。

## 2. 卷動產物與重現命令

```bash
# 不加旗標：確認輸出與現行 data/season-league.json 逐位元組相同
node scripts/build_season_league.js
git diff --stat data/season-league.json   # 應為空

# 加旗標：產出新檔 data/season-league-v54.json（不覆寫 v53 產物）
node scripts/build_season_league.js --shooting-eb
```

## 3. 球隊層模擬：v53 vs v54

引擎、壓迫係數（pressure/tovNonSteal）、`reports/player-impact-v53/calibrate-spread.mjs` 的
既有 `spread.json` 全部維持 v53 原樣，唯一差異是 2025-26 卡片換成 v54。4 季 × 3 種子
（`reports/player-impact-v54-team/runs/`）：

```bash
node reports/player-impact-v54-team/run.mjs 2022-23 2023-24 2024-25 2025-26 --workers=12 --variant=v54
python reports/player-impact-v54-team/score.py
```

| 季別 | 版本 | 勝場 MAE | 淨分 RMSE | 得分/場 | 失誤/場 | 三分% |
|---|---|---:|---:|---:|---:|---:|
| 2022-23 | v53 | 4.022 | 1.646 | 116.48 | 13.92 | 36.08 |
| 2022-23 | v54 | 4.022 | 1.646 | 116.48 | 13.92 | 36.08 |
| 2023-24 | v53 | 4.089 | 1.383 | 116.26 | 13.40 | 36.73 |
| 2023-24 | v54 | 4.089 | 1.383 | 116.26 | 13.40 | 36.73 |
| 2024-25 | v53 | 4.778 | 2.188 | 115.61 | 13.91 | — |
| 2024-25 | v54 | 4.778 | 2.188 | 115.61 | 13.91 | — |
| **2025-26** | **v53** | **4.556** | **2.019** | **117.13** | **14.11** | **36.01** |
| **2025-26** | **v54** | **6.289** | **2.703** | **116.76** | **14.22** | **35.87** |

2022-23／2023-24／2024-25（v54 不改動的季別）9 組季別×種子全部與 v53 逐位元組相同
（`unaffectedSeasonsByteIdenticalToV53` 全為 `true`），確認範圍隔離正確。

**2025-26（v54 唯一改動的季別）勝場 MAE 由 4.556 上升到 6.289（+1.733），淨分 RMSE 由
2.019 上升到 2.703（+0.684）**——球隊層預測準確度在 v54 下變差。

## 4. 球員層模擬板：v53 vs v54

先用未改動的 `reports/ovr-v53-shrinkage-2025-26/shrink.py`、`shrink_v2.py` 重現 v53 已發表的
基準值（確認方法與環境正確後才信任 v54 數字）：

```bash
python reports/ovr-v53-shrinkage-2025-26/shrink.py
python reports/ovr-v53-shrinkage-2025-26/shrink_v2.py
```

重現結果與 `reports/status/status.md` 完全一致（原始 ρ_N/ρ_D = 0.362/0.256，
v2 收縮後 = 0.398/0.276），且 `git diff --stat` 對這兩個已提交的輸出檔案為空（逐位元組重現）。

v54 板（`reports/ovr-v54-2025-26/run.mjs --variant both --samples 8 --workers 18`，582 名球員，
全部在遠端 5090 完成）套用完全相同的收縮規則（`reports/ovr-v54-shrinkage-2025-26/shrink.py`、
`shrink_v2.py`，與 v53 版本唯一差異是讀取的 checkpoint 路徑）：

```bash
python reports/ovr-v54-shrinkage-2025-26/shrink.py
python reports/ovr-v54-shrinkage-2025-26/shrink_v2.py
```

對 pooledPoss ≥ 5000 的 414 名球員（與 RAPM 比較）：

| 版本 | 原始 ρ_N | 原始 ρ_D | v2 收縮後 ρ_N | v2 收縮後 ρ_D |
|---|---:|---:|---:|---:|
| v53 | 0.362 | 0.256 | 0.398 | 0.276 |
| v54 | 0.389 | 0.289 | 0.424 | 0.302 |
| 差 | +0.027 | +0.033 | +0.026 | +0.026 |

**球員層與外部 RAPM 的排名相關性在 v54 下全面提升**（原始與 v2 收縮後、淨值與防守都一致提升
約 0.026–0.033）——這與第 3 節球隊層準確度變差的方向相反，兩者是用不同標準衡量
（球隊層比對的是實際勝場/分差，球員層比對的是外部獨立估計的 RAPM 排名），
報告只陳述此對比，不嘗試調和或選邊。

## 5. 三分／禁區屬性變化最大的球員（前 20，依絕對變化排序）

完整列表見 `attribute-changes.json`；`reports/ovr-v54-2025-26/attribute-changes.mjs` 可重現。

### 三分（long）

| 球員 | 位置 | 屬性變化 | 三分出手 |
|---|---|---|---:|
| DeJon Jarreau | SG | 44.0 → 56.4 (+12.4) | 4/30 |
| AJ Johnson | SG | 43.1 → 54.6 (+11.5) | 12/57 |
| Javonte Cooke | SG | 48.3 → 59.1 (+10.8) | 3/23 |
| Walker Kessler | C | 80.7 → 69.9 (−10.8) | 6/8 |
| Ja Morant | PG | 41.7 → 51.8 (+10.1) | 20/85 |

### 禁區（short）

| 球員 | 位置 | 屬性變化 | 禁區出手 |
|---|---|---|---:|
| Kyle Lowry | PG | 69.8 → 52.8 (−17.0) | 0/0 |
| Walker Kessler | C | 78.4 → 91.5 (+13.1) | 20/29 |

（Kessler 的三分出手極少（6/8，異常高命中率）在 v53 固定 k=100 下被嚴重低估收縮力度，
v54 下被拉回位置先驗而下降；他的禁區出手量夠大，則因 v54 的 k_z=80 小於 v53 的 k=100，
收縮力度反而減弱，估計值被推離先驗、往上修正。這是本次 EB 方法設計上預期的行為方向。）

兩個案例在前次分析中已逐一核對：Karlo Matković（非前 20，用作抽查參照）
v53 long=81.006/short=98.350 → v54 long=73.934/short=99（短出手量極少，被強力拉向先驗）。

## 6. 模擬板排名位移（前 30，依絕對位移排序）

用各自版本的 v2 收縮排名（`ranking-v2.csv`）比較：

```bash
node reports/ovr-v54-2025-26/rank-shifts.mjs
```

| 球員 | v53 排名 | v54 排名 | 位移 |
|---|---:|---:|---:|
| Isaiah Crawford | 445 | 304 | +141 |
| Marcus Sasser | 287 | 414 | −127 |
| Thanasis Antetokounmpo | 234 | 357 | −123 |
| Joan Beringer | 294 | 411 | −117 |
| Mouhamadou Gueye | 363 | 248 | +115 |
| Dwight Powell | 243 | 354 | −111 |
| Zeke Nnaji | 414 | 307 | +107 |
| Jett Howard | 246 | 353 | −107 |
| Caleb Houstan | 158 | 262 | −104 |
| Collin Sexton | 125 | 226 | −101 |
| DeJon Jarreau | 488 | 389 | +99 |

完整前 30 名清單見 `rank-shifts.json`（30 筆）。多數大位移球員是邊緣輪換球員
（出手樣本小，EB 收縮對其影響最大），符合設計預期。

## 7. 限制

- **範圍限定 2025-26。** `scripts/build_season_league.js` 本身只產生 2025-26 的卡片（其它季別有
  各自的 guard）。其它季別（2022-23/2023-24/2024-25）的卡片由另一支獨立腳本
  `reports/defense-tenth/step4-t0/prepare.mjs` 產生；經檢查該腳本對 long/mid/short/ft 全部四個分區
  都採用與 v53 相同的「固定虛擬樣本數 100」公式（`p[z]=inverse((m+100*priors[z])/(n+100),curve)`）。
  要把 v54 的可靠度加權收縮延伸到歷史季別，需要另外修改這支腳本，本次任務範圍未涵蓋，
  也因此歷史季別的球隊層模擬逐位元組與 v53 相同（見第 3 節）。
- **`shotDelta` 疊加的等價性。** 每張卡片的 long/mid/short 值在被引擎使用前都會先經過一個
  只依賴卡片值本身、曲線與 shotDelta 的對數位移（logit shift），與其它球員或狀態無關。因此在
  `shooting-eb.mjs` 裡直接換上 v54 的 long/short 原始值、重新套用這個位移，數學上等價於從頭
  用 v54 的 season-league 重新產生 bundle.json——已用 Karlo Matković 的卡片逐位元組核對過
  （第 5 節）。
- **球隊層與球員層結論方向相反。** 2025-26 球隊層勝場/淨分預測準確度在 v54 下變差，
  但球員層與外部 RAPM 的排名相關性提升。本報告不嘗試解釋兩者孰優孰劣，也不據此建議
  是否採用 v54。
- **球員層模擬板只跑了 8 個種子**（`--samples 8`），與 v53 既有基準用的種子數一致，
  用於可比較性，不代表收斂到更多種子後數字不會再變。
- 遠端執行環境：5090（`140.122.184.29`，20 核，18 workers），部署細節與檔案雜湊見
  `deployment-5090.json`。

## 8. 重現摘要

```bash
# 卡片生成（本機）
node scripts/build_season_league.js                 # 確認與 data/season-league.json 無差異
node scripts/build_season_league.js --shooting-eb    # 產出 data/season-league-v54.json

# 球隊層模擬（遠端 5090，12 workers）
node reports/player-impact-v54-team/run.mjs 2022-23 2023-24 2024-25 2025-26 --workers=12 --variant=v54
python reports/player-impact-v54-team/score.py

# 球員層模擬板（遠端 5090，18 workers，約 2.5 小時）
node reports/ovr-v54-2025-26/run.mjs --variant both --samples 8 --workers 18

# v53/v54 收縮分析重現
python reports/ovr-v53-shrinkage-2025-26/shrink.py
python reports/ovr-v53-shrinkage-2025-26/shrink_v2.py
python reports/ovr-v54-shrinkage-2025-26/shrink.py
python reports/ovr-v54-shrinkage-2025-26/shrink_v2.py

# 屬性變化 / 排名位移
node reports/ovr-v54-2025-26/attribute-changes.mjs
node reports/ovr-v54-2025-26/rank-shifts.mjs

npm test
```

## 9. 收束（2026-10-19）

v54 到此收束，不再追加改動：

- **不切換對局資料。** 球員層與 RAPM 的 ρ 上升（v2 0.398→0.424），但 2025-26 球隊層勝場 MAE
  從 4.556 變差到 6.289，`data/season-league.json` 維持 v53。
- **替補屬性修正（A＋C）不併入。** v55 實驗（`reports/ovr-v55-bench-prior-2025-26/`）在多季
  pooled RAPM 上看似把 <800 分鐘的 ρ 從 0.17 拉到 0.30，但改用 2025-26 單季 RAPM 做樣本外檢驗後，
  AC 0.428、只用往年資料的 AC_oos 0.410，都不比 v54 的 0.434 好（v2，單季回合 ≥500，n=170），
  所以不採用。
- 審查表（`reports/status/status_snapshot.py`）已加入 v54 模擬板與 v54 球隊層兩列，前 20 的
  模擬名次改讀 v54 板；正式卡片 OVR 板不變。
- 後續改進（傳球價值、自主出手與被助攻完成的區分、Karlo 等長人）留到 v55。
