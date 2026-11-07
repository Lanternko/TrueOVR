# v58 OVR 卡片候選評估報告

來源規格：`reports/ovr-v58-card-2025-26/preregistration.md`（鎖定，未修改；mtime `2026-10-21 10:04:51 +0800`，早於所有 `card-*/` 輸出）。
基準資料 SHA256（`data/season-league.json`）：`497725ecb6a2ec181aeb3cf93263f53a81bdfed772a2c4c733ba3a2d65a79bf6`（與預註冊一致，未變動）。
本輪只寫入 `reports/ovr-v58-card-2025-26/`；`reports/ovr-v57-card-2025-26/`、更早 reports、`scripts/`、`src/`、`data/`、`reports/player-impact-v53/calibrate-spread.mjs`、`reports/status/status.json` 均未修改；未 commit／branch／stash。

## 0. 結論先行

- **最終建議：H1-m0**（γ=1.0、δ=0.25、RAPM 總 lift 上限 margin=0）。
- **19/19 硬門檻全過**；ρ(2K27)=**0.5369** ≥ 0.4878 → **符合規則 4，建議取代 E2-λ0.4**。
- 前十為 SGA、Jokić、Wembanyama、Luka、Chet、White、Wagner、Giannis、Caruso、Kawhi；長人恰為 Wembanyama／Giannis／Jokić／Chet 四人，無 Mobley、無 Gordon。
- H3-m0 的 ρ2K=0.5400 較高，但 H3 的上限使用 2K27、ρ2K 屬部分自我實現；依預註冊 H3 條款（「若 H1 與 H3 都全過，優先 H1」）選 H1-m0。
- 這是**建議**；本輪未修改 v58 以外的官方卡片檔案。

## 1. 流程、時序與可重現性

### 1.1 時序（證明候選集在跑結果前鎖定）

| 產物 | mtime（+0800） |
|---|---|
| `diagnose.py` | 2026-10-21 10:03:48 |
| `diagnosis.json` | 2026-10-21 10:03:49 |
| `preregistration.md` | 2026-10-21 10:04:51 |
| `sanity-G3-repro/ranking.csv` | 2026-10-21 10:05:35 |
| `card-H1-m0/summary.json` | 2026-10-21 10:06:06 |
| `card-H4-phi0.5/ranking.csv` | 2026-10-21 10:06:10 |
| `evaluation.json`（重跑後） | 2026-10-21 10:08:51 |

`preregistration.md` 的 mtime 早於全部 8 個 `card-*/` 輸出；診斷在預註冊之前完成，候選集在跑任何候選前鎖定。

### 1.2 v57 G3 重現 sanity check

`sanity-G3-repro/`（`calibrate-wing.py --direction G3 --gamma 1.0 --delta 0.25`，無 cap）與 v57 `card-G3-delta0.25/ranking.csv` 對照：**582/582 列**，`maxPredDiff=0`、`rankDiffs=0`、top10 完全相同。這證明 v58 複製的管線在加入 cap 前與 v57 一致，後續差異不是複製錯誤。

### 1.3 evaluate.mjs 可重跑

`node reports/ovr-v58-card-2025-26/evaluate.mjs` 連續執行兩次，exit 0，`evaluation.json` 的 SHA256 兩次均為 `2baf61fc182c9a4c7aeb62984d1148ab50e1ba589d404108af81554fa212d33b`（byte-identical）。本報告所有數字均由該檔產生的 `evaluation.json` 讀出。

### 1.4 實作註記：tie epsilon 由 1e-9 改為 1e-12

預註冊寫 `T(A)` 取第 A 高值再減 `1e-9`；實作改用 `1e-12`。原因：`1e-9` 會讓固定點每輪只下降約 `1e-9`，永遠達不到「最大變動 < `1e-10`」的收斂條件（100 輪後仍不收斂）。`1e-12` 在 13 輪內收斂；cap 門檻只差 `1e-9`，遠小於 `ranking.csv` 的 3 位小數與實際名次間距。診斷腳本用 `1e-9` 做的靜態敏感度，其 top10 與實際 H1-m0／H1-m10／H3-m0／H3-m10 完全相同（見 2.6），可佐證此差異未改變結果。這是**實作偏離，不是候選變更**，在此完整揭露。

### 1.5 預註冊外探索

無。8 個候選就是預註冊鎖定的 8 個；沒有在看到結果後新增方向、改門檻或改候選值。唯一的偏離是 1.4 的 epsilon。

## 2. 診斷（預註冊前完成）

### 2.1 v57 G3 的缺口

G3-δ0.25 為 18/19，唯一失敗 **#18**：Giannis Antetokounmpo 第 14，被 Draymond Green（第 10）擠出前十。G3 前十為：

`1.White 2.Wagner 3.SGA 4.Jokić 5.Caruso 6.Gobert 7.Wembanyama 8.Holiday 9.Chet 10.Draymond`

Wembanyama／Jokić／Chet 都在前十，缺的不是「四長人都被壓低」，而是**額外的防守型長人被 defenseBonus 抬進前十**。

### 2.2 Draymond 為何被推到第 10

| 項目 | 數值 |
|---|---|
| pred0（base 回歸） | 0.827（pred0 名次 72） |
| defenseBonus | **2.356** |
| align | 0.239 |
| 總 lift | 2.595 |
| bonus 佔 lift 比例 | **90.8%** |
| pred0 的 PR | 82.76 |
| taper 權重 | 1.0（PR < 90，全額） |
| pred0+align 名次 | 49 |
| pred0+bonus 名次 | 12 |
| pred0+bonus+align 名次 | **10** |
| RAPM pooledNet 名次 | 46 |
| 2K27 名次 | 142 |

Draymond 的 pred0 只有第 72，但 PR 82.76 低於 taper 起點 90，γ=1.0 的防守 bonus 全額生效；bonus 一人就把他推到第 12，align 再補最後一腳到第 10。**問題不是 align 的方向，而是低 pred0 長人吃到過大的絕對 bonus。**

### 2.3 Giannis 的差距

Giannis 在 G3 的 pred 為 3.254（第 14），第 10 名 Draymond 為 3.423，差距 **0.169**。他的 align 為 0.564（δ=0.25），若只調 δ，需再加 `0.169 / (0.564/0.25) ≈ 0.075`，即 **δ≈0.325**。但 v57 已測 G3-δ0.4，Chet 被擠出前十（#18 仍失敗）。因此「只把 Giannis 拉高」不可行，必須**把擋在前面的球員壓低**。

### 2.4 其他被同類修正影響的球員

G3 排在 Giannis 前面的 13 人（依 pred 由高到低）：

| 名次 | 球員 | 位置 | pred | pred0 | bonus | align | RAPM | 2K27 |
|---|---|---|---|---|---|---|---|---|
| 1 | Derrick White | PG | 5.258 | 1.282 | 3.175 | 0.801 | 6 | 70.5 |
| 2 | Franz Wagner | SF | 4.898 | 0.972 | 3.040 | 0.886 | 7 | 47.5 |
| 3 | Shai Gilgeous-Alexander | PG | 4.884 | 4.593 | 0.000 | 0.291 | 2 | 2 |
| 4 | Nikola Jokić | C | 4.382 | 3.617 | 0.000 | 0.764 | 1 | 2 |
| 5 | Alex Caruso | SG | 4.293 | -0.684 | 3.860 | 1.116 | 9 | 94 |
| 6 | Rudy Gobert | C | 4.203 | 0.648 | 3.175 | 0.381 | 29 | 60.5 |
| 7 | Victor Wembanyama | C | 4.132 | 3.972 | 0.000 | 0.160 | 5 | 2 |
| 8 | Jrue Holiday | PG | 3.854 | 0.986 | 2.438 | 0.430 | 27 | 81 |
| 9 | Chet Holmgren | PF | 3.451 | 3.346 | 0.000 | 0.106 | 8 | 38 |
| 10 | Draymond Green | PF | 3.423 | 0.827 | 2.356 | 0.239 | 46 | 142 |
| 11 | Luka Dončić | PG | 3.353 | 3.377 | 0.000 | -0.025 | 16 | 5 |
| 12 | Jalen Suggs | PG | 3.351 | 0.803 | 2.443 | 0.105 | 85 | 110.5 |
| 13 | Ausar Thompson | SF | 3.279 | 0.070 | 2.474 | 0.735 | 28 | 47.5 |

這張表顯示：White／Wagner／Caruso／Gobert／Holiday／Draymond／Suggs／Ausar 都是「低 pred0 + 大 bonus」的受益者；其中 White／Wagner／Caruso 的 RAPM 名次（6／7／9）其實不差，真正的過譽集中在 Draymond（RAPM 46）、Suggs（85）、Gobert（29）、Holiday（27）、Ausar（28）。診斷共找到 **244 名**「有正向 lift 且卡片名次優於 RAPM 名次」的球員；問題是系統性的，不只 Draymond。

### 2.5 為何選「總 lift 上限」而不是只調 δ 或只砍 align

- **只調 δ**：需要 δ≈0.325；v57 的 δ=0.4 已把 Chet 擠出前十，無法在不破壞 #18 的情況下只靠 δ。
- **只砍向上 align（H4）**：Draymond 的 align 只佔 lift 的 9.2%，而 Giannis 的 align 是 0.564；砍掉向上 align 對 Giannis 的傷害大於 Draymond，差距反而擴大。H4 的實際結果也確認這點（見 5.4）。
- **只對 2K 名次差的球員封頂**：擋在前面的球員 2K 名次跨度是 47.5–142（Wagner／Ausar 47.5、Gobert 60.5、White 70.5、Holiday 81、Caruso 94、Suggs 110.5、Draymond 142），單純用 2K 門檻無法把 Draymond 和合法的側翼三人分開；而且 White／Wagner／Caruso 的 RAPM 名次本來就好，不該被當成過譽。這也是 H3 用 `min(2K,RAPM)` 共識版、而不是純 2K 版的原因。
- **平坦的修正上限**：要壓掉 Draymond 的 lift 需要約 2.4，但這個上限會同時砍到 White（lift 3.98）、Wagner（3.93）、Caruso（4.98）等 RAPM 名次本來就好的側翼，無法只針對 Draymond；而且數值看起來像事後調參。用外部名次決定上限比較有原則。

### 2.6 靜態敏感度（診斷，非候選輸出）

`diagnose.py` 直接對 G3 的既有 pred 做固定點上限（不重跑回歸、不重算 OVR、不寫 ranking.csv），RAPM margin 0／5／10 與 consensus margin 0／5／10 六組都讓四人留在前十。更關鍵的是，六組的 top10 與實際候選的對應**完全一致**：

| 靜態敏感度 | 對應實際候選 | top10 是否一致 |
|---|---|---|
| RAPM m=0 | H1-m0 | ✅ |
| RAPM m=10 | H1-m10 | ✅ |
| consensus m=0 | H3-m0 | ✅ |
| consensus m=10 | H3-m10 | ✅ |
| RAPM m=5 | （未列候選） | 與 m=10 相同 |
| consensus m=5 | （未列候選） | 與 m=10 相同 |

這表示候選值不是跑完才調出來的；靜態診斷在預註冊前就預見了實際 top10 的形狀。

## 3. 候選設計（預註冊鎖定，共 8 個）

| 方向 | 參考名次 | 上限作用對象 | 候選值 | 干預範圍 | 預期 |
|---|---|---|---|---|---|
| **H1** | RAPM | 總 lift（bonus+align） | m=0／10 | 最廣 | Draymond／Gobert／Holiday／Suggs／Ausar 被壓回 RAPM 附近；Giannis 進前十 |
| **H2** | RAPM | 只砍 defenseBonus | m=0／10 | 較窄 | 若只砍 bonus 就能修 #18，依「較小干預」可優先 |
| **H3** | `min(2K,RAPM)` | 總 lift | m=0／10 | 共識版 | 與 H1 在實際 bind 的球員上幾乎相同；ρ2K 部分自我實現 |
| **H4** | 無 | 不對稱 align | φ=0／0.5 | 對照組 | 預期不足以修 #18 |

### 3.1 上限語意

對有正向總 lift 且有外部名次的球員：

```
allowed = max(1, ceil(ref_rank - margin))
T(A)    = 候選自己 582 列 pred 分布中第 A 高的值（固定點迭代）
pred    = min(pred, max(pred0, T(allowed)))
```

四個重點：

1. **只砍向上的 lift**：`max(pred0, T)` 保證不會把球員壓到 pred0 以下。
2. **不是硬性名次上限**：若 pred0 本身已優於 `allowed`，cap 只會把 lift 歸零、保留 pred0；球員仍可能排在 `allowed` 之前。這是 H1 的設計限制，也是 Wembanyama／Chet／SGA 被 cap 但仍在前十的原因。
3. **固定點**：`T` 取決於 cap 後自己的分布，所以迭代到最大變動 < `1e-10`；H1-m0 共 13 輪。
4. **tie-break**：pred 由高到低；同值時 pred0 由高到低；再同值時 name 的 UTF-8 字典序。`T(A)` 減 `1e-12` 確保被 cap 的球員不會因浮點相等擠進前一名的位置（見 1.4 的 epsilon 說明）。

H1／H2／H3 只對 `pooledPoss ≥ 5000` 且有 RAPM／2K 名次的球員設限；H4 沒有 cap。

### 3.2 H1-m0 的 cap 實例

以下數值取自 H1-m0 最終分布（`T` 以 3 位小數顯示；實際門檻另有 `1e-12` 的 tie epsilon）：

| 球員 | ref | allowed | pred0 | 未 cap pred | T(allowed) | cap 後 pred | 名次 | 說明 |
|---|---|---|---|---|---|---|---|---|
| Draymond Green | 46 | 46 | 0.827 | 3.423 | 1.538 | 1.538 | 46 | 完整砍掉 lift |
| Rudy Gobert | 29 | 29 | 0.648 | 4.203 | 1.724 | 1.724 | 29 | 完整砍掉 lift |
| Derrick White | 6 | 6 | 1.282 | 5.258 | 3.346 | 3.346 | 6 | 壓到 RAPM 名次 |
| Victor Wembanyama | 5 | 5 | 3.972 | 4.132 | 3.346 | **3.972** | 3 | pred0 地板：只砍 align 0.160 |
| Chet Holmgren | 8 | 8 | 3.346 | 3.451 | 3.254 | **3.346** | 5 | pred0 地板：只砍 align 0.105 |
| Shai Gilgeous-Alexander | 2 | 2 | 4.593 | 4.884 | 4.382 | **4.593** | 1 | pred0 地板：只砍 align 0.291 |
| Nikola Jokić | 1 | 1 | 3.617 | 4.382 | 4.593 | 4.382 | 2 | pred < T(1)，未 cap |
| Giannis Antetokounmpo | 3 | 3 | 2.690 | 3.254 | 3.972 | 3.254 | 8 | pred < T(3)，未 cap |

這張表是理解 H1 的關鍵：Draymond／Gobert 被完整壓回；White 被壓到 RAPM 名次；Wembanyama／Chet／SGA 只被砍掉 align，因為 pred0 本身已高於門檻，cap 不能把他們壓到 pred0 以下；Jokić／Giannis 完全沒被 cap，Giannis 是靠其他人下移而進前十。

### 3.3 H3 的自我實現條款與 H4 的預期

- **H3** 的 `ref` 使用 `min(rank2k, RAPM)`，所以 ρ(2K27) 會部分機械性上升。預註冊在結果出來前已明文：「若 H1 與 H3 都全過，選版時**優先 H1**（ρ(2K27) 對 H1 仍是完全外部信號）。」這句話在本輪結果中正式觸發（見 4.4）。
- **H4** 只砍向上的 align。預註冊預期它不足以修 #18：Draymond 的 align 只有 0.239，而 Giannis 的 align 是 0.564；砍掉向上 align 對 Giannis 傷害更大。實際結果（18/19）確認。

## 4. 結果

### 4.1 19 項硬門檻矩陣（8 個候選）

門檻編號沿用預註冊：#1–18 加上 #20 的 ρDef 地板，共 19 項；#19 嚴格四長人是觀察項、#21–23 是回報項，不計入通過數。

| # | 門檻 | H1-m0 | H1-m10 | H2-m0 | H2-m10 | H3-m0 | H3-m10 | H4-φ0 | H4-φ0.5 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Karlo 掉名 ≥10 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 2 | Collins 下修 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 3 | Stewart 下修 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 4 | Garza 下修 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 5 | Queta ≤ max(2K,RAPM) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 6 | Gobert ≤ max(2K,RAPM) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 7 | Jalen Smith ≤220 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 8 | ρ(2K27) ≥0.4828 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 9 | ρ(RAPM) ≥0.5650 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 10 | 側翼後衛 ≥10/14 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 11 | Herbert Jones ≤142 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 12 | Caruso ≤94 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 13 | Marcus Smart ≤142 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 14 | 長人組 ≥14/16 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 15 | 前十長人 ≤5 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 16 | 前十無 Mobley | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 17 | 前十無 Gordon | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 18 | 四人留前十 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| 20 | ρDef ≥0.2972 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **通過數 / 19** | | **19/19** | **19/19** | **19/19** | **19/19** | **19/19** | **19/19** | **18/19** | **18/19** |

H1／H2／H3 六個候選全過；H4 兩個候選都只失敗 #18。**沒有任何候選在側翼門檻（#10–13）與長人門檻（#15–17）之間被迫取捨**——H1-m0 兩組都滿分。

### 4.2 ρ 值與保護組

| 候選 | 通過 | ρ(2K27) | ρ(RAPM) | ρ(Def) | 前十長人 | 嚴格四人 | 側翼14 | 長人16 | cap 人數 | 疊代 |
|---|---|---|---|---|---|---|---|---|---|---|
| **H1-m0** | **19/19** | **0.5369** | 0.8519 | 0.6605 | 4 | 是 | **14/14** | **16/16** | 105 | 13 |
| H1-m10 | 19/19 | 0.5359 | 0.8532 | 0.6698 | 4 | 是 | 13/14 | 15/16 | 75 | 7 |
| H2-m0 | 19/19 | 0.5320 | 0.8583 | 0.6677 | 4 | 是 | 14/14 | 14/16 | 73 | 5 |
| H2-m10 | 19/19 | 0.5316 | 0.8577 | 0.6726 | 4 | 是 | 13/14 | 14/16 | 63 | 6 |
| H3-m0 | 19/19 | **0.5400** | 0.8514 | 0.6645 | 4 | 是 | 14/14 | 16/16 | 80 | 8 |
| H3-m10 | 19/19 | 0.5385 | 0.8517 | 0.6730 | 4 | 是 | 13/14 | 15/16 | 56 | 6 |
| H4-φ0 | 18/19 | 0.5111 | 0.7775 | 0.6405 | 4 | 否 | 14/14 | 15/16 | — | — |
| H4-φ0.5 | 18/19 | 0.5216 | 0.8117 | 0.6707 | 4 | 否 | 14/14 | 15/16 | — | — |

樣本數：ρ2K n=575、ρRAPM／ρDef n=414（`pooledPoss ≥ 5000`）。

> **自我實現警告**：H1／H2／H3 的 cap、以及所有方向的 align 都使用 RAPM，ρ(RAPM) 會機械性上升，不能當作品質證據，也不能用於跨方向排序。H3 的 cap 使用 2K27，所以它的 ρ(2K27) 也部分自我實現；H1 的 cap 只用 RAPM，ρ(2K27) 對 H1 仍是完全外部信號。ρ(Def) 只作為地板（≥0.2972），不用於排序；H1-m0 的 0.6605 低於 G3 的 0.6969，是 cap 砍掉防守型 lift 的代價，但仍遠高於地板。

### 4.3 前十名單

> OVR 絕對值受卡片自己的 PR1/PR50/PR99 百分位映射影響，**跨卡不可比**；以下以名次為主。H1-m0 的 OVR 另列，供卡面參考。

| 卡片 | 前十（依名次） |
|---|---|
| E2-λ0.4（現官方） | SGA、Wembanyama、Jokić、Luka、Chet、Mobley、Giannis、Murray、Durant、Kawhi |
| F2-γ0.5（前正式備選） | Wembanyama、SGA、Chet、Mobley、Jokić、Luka、Giannis、Embiid、Gordon、Murray |
| G3-δ0.25（v57 最佳） | White、Wagner、SGA、Jokić、Caruso、Gobert、Wembanyama、Holiday、Chet、Draymond |
| **H1-m0（本輪建議）** | **SGA、Jokić、Wembanyama、Luka、Chet、White、Wagner、Giannis、Caruso、Kawhi** |
| H2-m0 | White、SGA、Jokić、Wagner、Caruso、Wembanyama、Chet、Luka、Giannis、Kawhi |
| H3-m0 | 與 H1-m0 完全相同 |
| H4-φ0.5 | White、SGA、Wagner、Wembanyama、Gobert、Jokić、Caruso、Holiday、Chet、Luka |

H1-m0 的完整前十與 OVR：

| 名次 | 球員 | 位置 | OVR |
|---|---|---|---|
| 1 | Shai Gilgeous-Alexander | PG | 109.9 |
| 2 | Nikola Jokić | C | 108.0 |
| 3 | Victor Wembanyama | C | 104.5 |
| 4 | Luka Dončić | PG | 99.1 |
| 5 | Chet Holmgren | PF | 99.0 |
| 6 | Derrick White | PG | 99.0 |
| 7 | Franz Wagner | SF | 99.0 |
| 8 | Giannis Antetokounmpo | PF | 98.2 |
| 9 | Alex Caruso | SG | 98.2 |
| 10 | Kawhi Leonard | SF | 96.8 |

長人恰為 Jokić（2）、Wembanyama（3）、Chet（5）、Giannis（8）四人；無 Mobley、無 Gordon。SGA 的 OVR 109.9 高於 G3 的 103.0，是因為 cap 壓縮了頂端分布、改變了百分位映射，不是 SGA 的 pred 變高（他的 pred 其實從 4.884 降到 4.593）。

### 4.4 方向內代表與跨方向選擇

**H1（RAPM 總 lift 上限）**
- m0 與 m10 都是 19/19、前十長人都是 4。
- ρ2K：m0 **0.5369** > m10 0.5359 → 依規則 1 由 m0 勝出。
- 保護組：m0 14/14、16/16；m10 13/14、15/16（m10 的 Wembanyama 第 6 超過 ref 5、SGA 第 3 超過 ref 2）。m0 不只 ρ2K 較高，保護組也更強。
- **代表：H1-m0**。

**H2（只砍 defenseBonus）**
- m0 與 m10 都是 19/19；ρ2K m0 0.5320 > m10 0.5316 → m0。
- 但 m0 的長人組只有 14/16（Wembanyama 6/5、Embiid 19/17.5），m10 的側翼組只有 13/14（SGA 3/2）。兩者都不如 H1-m0 的滿分。
- **代表：H2-m0**；干預較窄，但保護組與 ρ2K 都被 H1-m0 支配。

**H3（共識版）**
- m0 與 m10 都是 19/19；ρ2K m0 **0.5400** > m10 0.5385 → m0。
- H3-m0 的 top10 與 H1-m0 完全相同，保護組也是 14/14、16/16。
- 但 H3 的 cap 使用 2K27，ρ2K 部分自我實現（見 3.3）。
- **代表：H3-m0**。

**H4（不對稱 align）**
- φ0.5 與 φ0 都是 18/19；ρ2K φ0.5 0.5216 > φ0 0.5111 → φ0.5。
- 兩者都失敗 #18：Giannis 第 13（φ0.5）／第 14（φ0），多出的長人是 Gobert（第 5），不是 Draymond。這確認「砍向上 align」不是正確的槓桿。
- **代表：H4-φ0.5**。

**跨方向**

三個全過的方向代表：H1-m0（ρ2K 0.5369）、H2-m0（0.5320）、H3-m0（0.5400）。

- 若**字面**套用規則 2「取 ρ2K 最高」，會選 **H3-m0**。
- 但預註冊在 H3 段（結果出來前）已明文：「H3 的 ref 使用 2K27，會讓 ρ(2K27) 部分機械性上升（自我實現）。因此若 H1 與 H3 都全過，選版時**優先 H1**（ρ(2K27) 對 H1 仍是完全外部信號）。」
- 這是針對「H1 與 H3 都全過」這個具體情況的特定條款，優先於一般規則 2；而且規則 2 的理由（ρ2K 是外部判準）在 H3 上不成立。若把 H3 的 0.5400 當成獨立證據，會重複計算 2K 資訊。
- **最終建議：H1-m0**。若使用者要求嚴格按規則 2 的字面，替代是 H3-m0；但它的 ρ2K 優勢不能視為 external validation。

### 4.5 規則 4 符合性

規則 4：最終建議必須 (a) 19 項硬門檻全過，且 (b) ρ(2K27) ≥ 0.4878。

- **H1-m0：19/19，ρ2K=0.5369 ≥ 0.4878 → 符合。**
- 另有 H1-m10（0.5359）、H2-m0（0.5320）、H2-m10（0.5316）、H3-m0（0.5400）、H3-m10（0.5385）也符合形式條件；但依 4.4 的選版規則，最終建議是 H1-m0。
- H4-φ0.5（0.5216）與 H4-φ0（0.5111）雖然 ρ2K 也過 0.4878，但只有 18/19（#18 失敗），**不符合**規則 4。
- **建議：把官方卡片由 E2-λ0.4 切換為 H1-m0。** 本輪的寫入範圍只到 `reports/ovr-v58-card-2025-26/`，沒有修改任何官方卡片檔案；實際切換是後續動作。

### 4.6 H1-m0 的細節檢查

**七人名單**

| 球員 | v53 名次 | H1-m0 名次 | OVR | 2K27 | RAPM | 門檻 | 結果 |
|---|---|---|---|---|---|---|---|
| Karlo Matković | 7 | 70 | 80.6 | 294.5 | 212 | ≥17（v53+10） | ✅ |
| John Collins | 29 | 128 | 75.0 | 142 | 240 | >29 | ✅ |
| Isaiah Stewart | 32 | 166 | 73.8 | 194.5 | 261 | >32 | ✅ |
| Luka Garza | 33 | 140 | 74.6 | 255.5 | 174 | >33 | ✅ |
| Neemias Queta | — | 13 | 91.3 | 110.5 | 13 | ≤110.5 | ✅ |
| Rudy Gobert | — | 29 | 84.9 | 60.5 | 29 | ≤60.5 | ✅ |
| Jalen Smith | — | 134 | 74.9 | 220 | 65 | ≤220 | ✅ |

Karlo 從 v53 第 7 掉到第 70（掉 63 名），Collins／Stewart／Garza 也都下修；Queta 第 13、Gobert 第 29、Jalen Smith 第 134，全部在門檻內。

**側翼三人**

| 球員 | H1-m0 名次 | 2K27 | RAPM | ref=max | 結果 |
|---|---|---|---|---|---|
| Herbert Jones | 14 | 142 | 14 | 142 | ✅ |
| Alex Caruso | 9 | 94 | 9 | 94 | ✅ |
| Marcus Smart | 30 | 142 | 30 | 142 | ✅ |

側翼＋後衛 14 人 **14/14** 全過；長人 16 人 **16/16** 全過（完整名單見 Appendix B）。H1-m0 與 H3-m0 是僅有的兩個保護組都滿分候選（14/14、16/16）。

**G3 → H1-m0 關鍵球員對照**

| 球員 | G3 名次 | G3 pred | H1-m0 名次 | H1-m0 pred | pred0 | bonus | align | 名次變動 |
|---|---|---|---|---|---|---|---|---|
| Draymond Green | 10 | 3.423 | 46 | 1.538 | 0.827 | 2.356 | 0.239 | +36 |
| Rudy Gobert | 6 | 4.203 | 29 | 1.724 | 0.648 | 3.175 | 0.381 | +23 |
| Jrue Holiday | 8 | 3.854 | 27 | 1.724 | 0.986 | 2.438 | 0.430 | +19 |
| Jalen Suggs | 12 | 3.351 | 85 | 1.101 | 0.803 | 2.443 | 0.105 | +73 |
| Ausar Thompson | 13 | 3.279 | 28 | 1.724 | 0.070 | 2.474 | 0.735 | +15 |
| Derrick White | 1 | 5.258 | 6 | 3.346 | 1.282 | 3.175 | 0.801 | +5 |
| Franz Wagner | 2 | 4.898 | 7 | 3.346 | 0.972 | 3.040 | 0.886 | +5 |
| Alex Caruso | 5 | 4.293 | 9 | 3.254 | -0.684 | 3.860 | 1.116 | +4 |
| Giannis Antetokounmpo | 14 | 3.254 | 8 | 3.254 | 2.690 | 0.000 | 0.564 | −6 |
| Victor Wembanyama | 7 | 4.132 | 3 | 3.972 | 3.972 | 0.000 | 0.160 | −4 |
| Chet Holmgren | 9 | 3.451 | 5 | 3.346 | 3.346 | 0.000 | 0.106 | −4 |
| Nikola Jokić | 4 | 4.382 | 2 | 4.382 | 3.617 | 0.000 | 0.764 | −2 |
| Luka Dončić | 11 | 3.353 | 4 | 3.353 | 3.377 | 0.000 | -0.025 | −7 |
| Kawhi Leonard | 15 | 3.095 | 10 | 3.095 | 2.296 | 0.000 | 0.799 | −5 |
| Neemias Queta | 20 | 2.743 | 13 | 2.464 | 0.946 | 1.287 | 0.510 | −7 |

**cap 的干預幅度**

- summary 記錄 **105 人**的 lift 被削減；以 G3 對照，**98 人**排名改變。
- 削減 >0.1 有 84 人、>0.5 有 39 人、>1.0 有 17 人；最大的下降是 Gobert（−2.479）、Suggs（−2.250）、Holiday（−2.130）、White（−1.912）、Draymond（−1.885）。
- G3 前十有 **9 人**被 cap 觸及（White、Wagner、SGA、Caruso、Gobert、Wembanyama、Holiday、Chet、Draymond；Jokić 未被 cap）；H1-m0 的最終前十則有 **6 人**被 cap 觸及（SGA、Wembanyama、Chet、White、Wagner、Caruso），Jokić、Luka、Giannis、Kawhi 未被 cap。
- 這不是一個「最小改動」：H1-m0 大幅重排了 G3 的前十。它的理由是 G3 的前十被低 pred0 長人的 defenseBonus 主導；cap 把這些 lift 壓回外部名次，代價是 G3 前十有 9 人被 cap 觸及、ρDef 從 0.6969 降到 0.6605。
- SGA／Wembanyama／Chet 被 cap 但名次仍在前段，是因為 pred0 地板（見 3.2）；這不代表 cap 對他們「無效」，而是 cap 只能砍 lift、不能把 pred0 壓低。

## 5. 預註冊預測 vs 實際

### 5.1 H1

| 預測 | 實際 | 判定 |
|---|---|---|
| Draymond → 名次 ≥36/46 | 第 46 | ✅ |
| Gobert 29、Holiday 27、Suggs 85、Ausar 28 | 29／27／85／28 | ✅ |
| White／Wagner／Caruso 在 m=0 被壓到 RAPM 名次（6／7／9） | 6／7／9 | ✅ |
| White／Wagner／Caruso 在 m=10 不受影響 | 1／2／5 | ✅ |
| Giannis／Jokić 不受上限影響 | Giannis 未 cap、第 8；Jokić 未 cap、第 2 | ✅ |
| Wembanyama／Chet 不受上限影響 | **兩人都有 bind**：Wembanyama 砍掉 align 0.160、Chet 砍掉 align 0.105；但因 pred0 地板，兩人仍在第 3／5 | ⚠️ 機制預測失準，結果仍正確 |
| 風險：ρ(RAPM) 機械性上升 | 0.8519（G3 0.8424），確有上升；未用於排序 | ✅（已揭露） |

Wembanyama／Chet 的「不受上限影響」是預註冊中唯一明顯失準的機制預測：他們的 pred0 已經高於 RAPM 對應的門檻，但加上 align 後超過 `T(allowed)`，所以 cap 仍會砍掉 lift。因為 pred0 地板，砍完後他們仍留在前十；#18 的結果不受影響。此點必須揭露，不能說「四人完全沒被 cap」。

### 5.2 H2

| 預測 | 實際 | 判定 |
|---|---|---|
| 若只砍 bonus 就能修 #18，依「較小干預」可優先 | H2-m0 與 H2-m10 都 19/19，確實修好 #18 | ✅ |
| 「表現不輸 H1」才優先 | H2-m0 長人組 14/16（Wembanyama 6/5、Embiid 19/17.5），H1-m0 16/16；ρ2K 0.5320 < 0.5369 | ❌ 條件不成立，H1 仍優先 |
| 風險：align 仍可把 pred 推高，不是嚴格名次上限 | H2 的 top10 仍有 White 第 1、Wagner 第 4，高於其 RAPM 6／7；但 gate #10–13 只要求「不被低估」，所以仍過 | ✅（風險存在，未造成失敗） |

### 5.3 H3

| 預測 | 實際 | 判定 |
|---|---|---|
| 與 H1 在實際 bind 的球員上幾乎相同 | H3-m0 top10 與 H1-m0 完全相同；H3-m10 與 H1-m10 相同 | ✅ |
| ρ(2K27) 部分自我實現 | 0.5400 > H1-m0 0.5369；cap 使用 2K27 | ✅（已觸發 H1 優先條款） |

### 5.4 H4

| 預測 | 實際 | 判定 |
|---|---|---|
| 不足以修 #18 | 兩個 φ 都 18/19，失敗 #18 | ✅ |
| 砍向上 align 對 Giannis 傷害大於 Draymond | Giannis 第 13（φ0.5）／第 14（φ0），仍出前十；多出的長人是 Gobert 第 5 | ✅ |
| 作為最小干預對照 | 確認問題不在 align 的方向不對稱 | ✅ |

## 6. 偏誤、限制與風險

1. **ρ(RAPM) 自我實現**：H1／H2／H3 的 cap 或 align 使用 RAPM，ρ(RAPM) 會機械性上升；本報告只用它當地板，不用於跨方向排序。H1-m0 的 0.8519 高於 G3 的 0.8424，不能解讀為「更準」。
2. **H3 的 ρ(2K27) 部分自我實現**：H3 的 cap 使用 2K27，所以 0.5400 不能當作獨立的 external validation；這也是選 H1-m0 而不是 H3-m0 的原因。
3. **cap 不是硬性名次上限**：`max(pred0, T)` 的 pred0 地板意味著 pred0 本身已優於 `allowed` 的球員（SGA、Wembanyama、Chet）只會被砍 lift，名次仍可能優於 `allowed`。H1-m0 的 #18 是靠「其他人下移 + 四人本身夠高」通過，不是靠把四人硬壓到特定名次。
4. **外部名次的雜訊**：margin=0 假設 RAPM 名次沒有誤差，是較激進的版本；margin=10 允許 10 名誤差，同為 19/19，ρ2K 只低 0.0010，是較穩健的替代。依預註冊的 tie-break（ρ2K 優先於「較小干預」）選 m0；若使用者更重視外部名次雜訊的穩健性，H1-m10 是合理的備選。
5. **干預幅度大**：105 人被 cap、98 人排名改變、G3 前十有 9 人被 cap 觸及（H1-m0 前十則有 6 人）；這不是微調。H1-m0 的合理性建立在「defenseBonus 對低 pred0 長人的抬升是系統性高估」這個診斷上，而不是「越小越好」。
6. **OVR 絕對值不可跨卡比較**：PR1/PR50/PR99 是每張卡自己的分布；H1-m0 的 SGA 109.9 與 G3 的 103.0 不能直接比。卡面比較應看名次與 ρ。
7. **2K27 與 RAPM 都是外部基準，各有誤差**：`merged.csv` 的 2K 名次有小數（例如 70.5），RAPM 只納入 `pooledPoss ≥ 5000`；兩者都不是 ground truth。H1 只用 RAPM，H3 用兩者共識；本報告已分別揭露其偏誤。
8. **官方卡片切換是建議，不是本輪已執行**：本輪只寫 v58 目錄，沒有修改 `src/`、`data/` 或正式卡檔案；切換與否由使用者決定。

## 7. 與 G3／F2／E2 的整體對照

| 卡片 | 通過 | ρ(2K27) | ρ(RAPM) | ρ(Def) | 前十長人 | 嚴格四人 | 主要缺口 |
|---|---|---|---|---|---|---|---|
| E2-λ0.4（現官方） | 10/19 | 0.4778 | 0.5290 | 0.2972 | 5 | 否（Mobley） | 側翼／後衛與長人防守門檻、Gobert、ρ2K／ρRAPM 地板 |
| F2-γ0.5（前備選） | 12/19 | 0.4878 | 0.5700 | 0.3624 | 7 | 否（Mobley／Embiid／Gordon） | 側翼三人、前十長人過多、Mobley／Gordon |
| G3-δ0.25（v57 最佳） | 18/19 | 0.5299 | 0.8424 | 0.6969 | 5 | 否（Gobert／Draymond） | #18：Giannis 被 Draymond 擠出 |
| **H1-m0（本輪建議）** | **19/19** | **0.5369** | 0.8519 | 0.6605 | **4** | **是** | 無硬門檻缺口 |

H1-m0 相對 G3：+1 門檻、ρ2K +0.0070、ρDef −0.0364；前十拿掉 Gobert／Holiday／Draymond，加入 Luka／Giannis／Kawhi，四人齊聚且無多餘長人。相對 F2：+7 門檻、ρ2K +0.0491；相對 E2：+9 門檻、ρ2K +0.0591。代價是 cap 干預幅度大、絕對 OVR 不可跨卡比較（見第 6 節第 5、6 點）。

## Appendix A：8 個候選的完整前十

| 候選 | 前十（依名次） |
|---|---|
| H1-m0 | SGA、Jokić、Wembanyama、Luka、Chet、White、Wagner、Giannis、Caruso、Kawhi |
| H1-m10 | White、Wagner、SGA、Jokić、Caruso、Wembanyama、Chet、Luka、Giannis、Kawhi |
| H2-m0 | White、SGA、Jokić、Wagner、Caruso、Wembanyama、Chet、Luka、Giannis、Kawhi |
| H2-m10 | White、Wagner、SGA、Jokić、Caruso、Wembanyama、Chet、Luka、Ausar Thompson、Giannis |
| H3-m0 | SGA、Jokić、Wembanyama、Luka、Chet、White、Wagner、Giannis、Caruso、Kawhi |
| H3-m10 | White、Wagner、SGA、Jokić、Caruso、Wembanyama、Chet、Luka、Giannis、Kawhi |
| H4-φ0 | SGA、White、Wagner、Wembanyama、Gobert、Jokić、Holiday、Luka、Chet、Suggs |
| H4-φ0.5 | White、SGA、Wagner、Wembanyama、Gobert、Jokić、Caruso、Holiday、Chet、Luka |

## Appendix B：H1-m0 保護組完整名單

### B.1 側翼＋後衛 14 人（RAPM pooledD 前 30）

| 球員 | 位置 | H1-m0 名次 | ref=max(2K,RAPM) | 結果 |
|---|---|---|---|---|
| Alex Caruso | SG | 9 | 94 | ✅ |
| Derrick White | PG | 6 | 70.5 | ✅ |
| Franz Wagner | SF | 7 | 47.5 | ✅ |
| Herbert Jones | SG | 14 | 142 | ✅ |
| Ausar Thompson | SF | 28 | 47.5 | ✅ |
| Marcus Smart | SG | 30 | 142 | ✅ |
| Jalen Suggs | PG | 85 | 110.5 | ✅ |
| Jrue Holiday | PG | 27 | 81 | ✅ |
| Matisse Thybulle | SG | 132 | 294.5 | ✅ |
| Shai Gilgeous-Alexander | PG | 1 | 2 | ✅ |
| Ajay Mitchell | SG | 77 | 81 | ✅ |
| Dillon Brooks | SF | 56 | 81 | ✅ |
| Ronald Holland II | SF | 142 | 255.5 | ✅ |
| OG Anunoby | SF | 31 | 31 | ✅ |

### B.2 長人 16 人（RAPM pooledD 前 30）

| 球員 | 位置 | H1-m0 名次 | ref=max(2K,RAPM) | 結果 |
|---|---|---|---|---|
| Victor Wembanyama | C | 3 | 5 | ✅ |
| Rudy Gobert | C | 29 | 60.5 | ✅ |
| Draymond Green | PF | 46 | 142 | ✅ |
| Dean Wade | PF | 18 | 220 | ✅ |
| Chet Holmgren | PF | 5 | 38 | ✅ |
| Joel Embiid | C | 12 | 17.5 | ✅ |
| Jaren Jackson Jr. | PF | 62 | 62 | ✅ |
| Brook Lopez | C | 83 | 194.5 | ✅ |
| Jonathan Isaac | PF | 105 | 380 | ✅ |
| Aaron Gordon | PF | 21 | 70.5 | ✅ |
| Toumani Camara | PF | 51 | 110.5 | ✅ |
| Wendell Carter Jr. | C | 93 | 142 | ✅ |
| Christian Koloko | C | 215 | 428 | ✅ |
| Anthony Davis | C | 32 | 32 | ✅ |
| Jusuf Nurkić | C | 48 | 220 | ✅ |
| Tobias Harris | PF | 26 | 94 | ✅ |

## 8. 結論

H1-m0 以 **19/19、ρ(2K27)=0.5369** 通過規則 4，建議取代 E2-λ0.4。
H3-m0 的 0.5400 較高，但 cap 使用 2K27、屬部分自我實現，依預註冊 H3 條款仍優先 H1。
H1-m0 前十為 SGA／Jokić／Wembanyama／Luka／Chet／White／Wagner／Giannis／Caruso／Kawhi，長人恰為四人且無 Mobley、無 Gordon。
代價是 105 人被 cap 觸及、ρDef 由 0.6969 降至 0.6605，且絕對 OVR 受百分位映射影響、不可跨卡比較。
若優先考慮外部名次雜訊的穩健性，H1-m10 同為 19/19、ρ2K=0.5359，是較小干預的備選。
