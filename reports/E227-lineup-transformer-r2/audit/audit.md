# 總評

**4/5（原結論站得住）**

核心結論：判定 1、判定 2 兩臂（R2-stats、R2-stats-rapm）我用自己寫的特徵與指標程式獨立重算，數字與 `test-results.json` 完全相同，凍結時序與雜湊也沒被違反，所以「兩臂過關」成立。要打折的是兩件事：stamina 這欄其實是賽季場均分鐘的百分位（會把測試場次的上場時間帶回特徵），個人價值裡 Scottie Barnes 與 Kevin Porter Jr. 的高名次一部分靠它。

**關鍵數據與例子**

| 項目 | 報告 | 我重算 |
|---|---|---|
| 判定 1 R2-stats（對 R2-abil 的淨 MSE 差） | −17.625，90% 區間 [−24.73, −10.27] | −17.625，[−24.73, −10.27]（另一組 seed 777：[−25.07, −10.15]） |
| 判定 1 R2-stats-rapm | −18.661，[−25.56, −11.61] | 同 |
| 判定 2 R2-stats（得分側／失誤／進攻籃板） | −0.000637／−0.000419／−0.001340 | 同，三項皆越過門檻 |
| 測試集 | 34624 stint、1135 場 | 同 |

- **stamina 的來源**：`stamina = MPG`（`reports/ovr-inseason-2026-27/v4/tools/season_attrs_v4.py` 第 211、229 行）再轉百分位，與 2025-26 賽季總分鐘的 Spearman 為 0.704。也就是說 2025-26 的特徵含有測試場次的上場時間，報告開頭有揭露「季總量特徵含測試場次」，但沒有點出 stamina 是其中最強的一欄。分鐘數本身（`minutes`）沒有放進 26 欄統計，禁用欄位 grep 為空。
- **去掉 stamina 對個人價值的影響**（我重寫價值演算法，600 組抽樣，與報告的 Spearman 0.999，名次基本重現）：Scottie Barnes #7 → #16、Kevin Porter Jr. #17 → #37；Mitchell Robinson 反而 #15 → #9；Harrison Barnes #169 → #167 幾乎不動。整體排序去掉 stamina 後 Spearman 0.944，所以影響是有的但不是全部。
- **要注意的命名誤會**：你說的「Harrison Barnes 在 R2-stats 前 20 的 #7」，報告的 #7 其實是 **Scottie Barnes**（pid 1630567）。Harrison Barnes（pid 203084）在 R2-stats 是 #167，在 R2-abil #185。

三位球員最極端的特徵 z 值（2025-26，單欄歸零後的 100 回合淨值變化）：

| 球員 | 最極端 z | stamina 的貢獻 | 主要來源 |
|---|---|---|---|
| Scottie Barnes（#7） | stamina +2.06、long −1.47、pass +1.34、blk36 +1.34 | −2.85（全部特徵歸零是 −7.68） | stamina 單欄佔最大，其次 stl36、rebound，分散 |
| Kevin Porter Jr.（#17） | looseD36 +2.86、stl36 +2.28、astPct +2.15、stamina +1.95 | −2.73 | stl36（−3.05）與 stamina 並列，其餘分散 |
| Mitchell Robinson（#19） | boxoutO36 +5.76、oreb36 +4.48、orebPct +4.44、ft −3.34 | +0.51（反向） | 少數籃板／卡位欄（boxoutO36 −2.01、oreb36 −1.35），orebPct 歸零反而 +1.45 |

Mitchell Robinson 的 boxoutO36 z 值 5.76 是極端值，模型在這個範圍幾乎沒有訓練樣本，名次可信度偏低，而不是 stamina 的問題。Kevin Porter Jr. 去 stamina 後 #37 仍在前 40，且卡片名次本來就是 #14，方向不算突兀。Scottie Barnes 卡片名次 #29，R2-stats 給 #7 比較偏高，去 stamina 的 #16 更接近。

**要你決定的事**

1. **採用 R2-stats（你已裁定）**：我的判定是兩個檢定都站得住，沒有理由推翻。建議維持採用。
2. **要不要追加一個去掉 stamina 的臂做事後對照**：這是我最想要的補件，因為 stamina 把測試場次的分鐘數帶回特徵，判定 1 的 −17.6 裡有多少來自它目前沒量過。建議做（便宜，只重訓 R2-stats 去 stamina 一個臂，5 seed）；但這會是探索性比較，不能改判定結果（L-026）。不做的話，個人價值頁就在說明裡標「stamina 含分鐘資訊」。
3. 報告把 sha256 描述成對 LF 內容算，實際上 139 個檔裡 21 個是對 CRLF 內容算的，內容沒被改，只是文字敘述不準，建議報告更正一句。

---

# 附錄

## 關卡表

| 關卡 | 判定 | 證據路徑 |
|---|---|---|
| 1. 凍結早於讀測試；評估腳本與權重 sha256 對得上；凍結後沒動 | 過（附一條說明） | `audit/a1_hashes.py`：manifest 139 個雜湊全數對上 2b37fac 與 3db92f9（118 個直接對上，21 個要用 CRLF 內容才對上）。凍結 commit 2b37fac 時間 2026-11-04 00:41:53 早於結果 3db92f9（01:12:57）。結果 commit 還動了五支其他腳本，不屬於 E227 的設定與權重。 |
| 2. 判定 1、2 獨立重算 | 過 | `audit/a2_recompute.py`、`audit/a2_result.json`、`audit/a2_pred.npz`。自己寫的特徵與指標，只借 `LineupNet` 結構和 15 份權重。bootstrap 用同 seed 20261103 與另一組 777，結果一致。 |
| 3a. 測試切分一致、無 stint 層級交叉 | 過 | `a2_recompute.py` 的 assert：fold 欄位等於雜湊、train 與 test 場次集合不相交；測試列以 E-225 完整 stints 依雜湊重切。 |
| 3b. 禁用欄位 | 過 | `build_data.py` 第 5 行僅出現在 docstring；`e227_common.py` 的 STATS 26 欄不含 minutes。 |
| 3c. RAPM 只用訓練場次、fold 0 驗證用 excl-0 | 過 | `build_rapm.py` 第 1–7 行與第 39–40 行（以 `fold` 排除）；`data/rapm-<季>-excl*.csv`；測試場次從未寫入 data/。 |
| 3d. stamina 與季總量特徵樂觀性 | 有疑慮 | `season_attrs_v4.py` 第 211、229 行；`audit/a5_stamina.py`（stamina 與賽季總分鐘 Spearman 0.704）。預註冊有揭露季總量含測試場次，但沒單獨量化 stamina。 |
| 4. 三位球員合理性 | 過（個別疑慮見上） | `audit/a3_value.py`、`audit/a3_result.json`。 |
| 5. 報告 5 項數字重算 | 過 | MSE 表、守衛表（`a2_result.json`）；相關表 卡 OVR 0.786／0.802／0.802，BPM 0.789／0.807／0.812，RAPM off 0.707／0.626／0.638，RAPM def 0.282／0.402／0.395（`a3_value.py`、`a4_tables.py`）；防守側翼 Dean Wade #168、Tari Eason #182、Herbert Jones #210、Draymond Green abil #75 → stats #197（`a4_tables.py`）。2K26 與薪水兩列沒重算。 |

## 抓到的問題

- **L 候選（我不能改 memory/，交回主管登記）**：報告敘述「hash 對 LF 內容」與實際（21/139 為 CRLF）不符。
- **F 候選（待驗）**：stamina（MPG 百分位）把賽季場均分鐘帶回特徵；去掉後個人價值 Spearman 0.944，Scottie Barnes #7 → #16、Kevin Porter Jr. #17 → #37。對判定 1 的貢獻未量。
- **命名**：使用者口述的 Harrison Barnes #7 是 Scottie Barnes。

## 限制

- 我重寫的價值演算法用 600 組抽樣（報告 4000 組），名次有 ±數名的抽樣誤差（例：Mitchell Robinson 報告 #19，我 #15；Harrison Barnes 報告 #167，我 #169）。
- 單欄歸零敏感度是在固定 800 組抽樣上做，模型非線性，單欄貢獻相加不等於全歸零的變化。
- 2K26、薪水相關沒重算（需要 HTML 解析，與判定無關）。
- 我沒有重跑 `npm test`（本稽核只涉及 E227 報告檔）。

## 檔案

`a1_hashes.py`、`a2_recompute.py`（輸出 `a2_result.json`、`a2_pred.npz`）、`a3_value.py`（輸出 `a3_result.json`、`a3_value_mine.npy`）、`a4_tables.py`、`a5_stamina.py`。
