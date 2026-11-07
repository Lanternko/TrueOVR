# E-077 預註冊：選秀體測臂展在身高體重之外有沒有額外解釋力

寫於 2026-10-29，在看任何臂展與表現的關係之前。之後只能改路徑與錯字。

## 問題
PHYS 目前 = 身高(吋) + 體重/10。臂展（選秀體測）在身高、體重之外，能不能多解釋籃板與蓋帽？

## 資料
- 臂展、赤腳身高、站立摸高：nba.com/stats/draft/combine-anthro，2000-01 至 2025-26 屆，存成 `combine-anthro.json`（含抓取時間與 sha256）。
- 表現：`data/defense-seventh/<季>/`（2014-15 至 2024-25 的 bio.json + player-games.json）與 `data/benchmark-source/`（2025-26）。
- 人群：每季 GP ≥ 30 且 MPG ≥ 20 的球員季。

## 變數
- 主要暴露：ape = 臂展 − 赤腳身高（吋）。沒參加或沒量的人 ape = 0（置中後），另加缺值指標 miss。
- 次要（只報告）：reach = 站立摸高 − 赤腳身高。
- 基準模型：結果 ~ 身高(bio) + 體重(bio) + miss
- 測試模型：基準 + ape
- 姓名比對：去重音、去 Jr/II/III、只留字母；人工別名：Edrice→Bam Adebayo、Alexandre→Alex Sarr、Carlton→Bub Carrington、Nicolas→Nic Claxton、Herbert→Herb Jones（雙向）。對不上 = 缺值。同名多筆取有量測的最新一筆。

## 結果變數
- 主要（12 季全有）：OREB%、DREB%（bio）、BLK/36（game logs 加總）。
- 次要（只 2025-26，只報告）：護框對手命中差（defense-rim，FGA_LT_06 ≥ 100）、RA 命中率（RA FGA ≥ 50）。

## 樣本外設計
- 依 PLAYER_ID 奇偶把「球員」分兩半（同一人所有季同一半）。A 擬合→B 評估，B 擬合→A 評估，兩邊合併算 held-out R²。
- 指標：ΔR² = R²(測試) − R²(基準)，held-out。
- 不確定性：以球員為單位 bootstrap 2000 次，seed 20261029，報 95% 區間。
- 敏感度（只報告）：只用有量測的人；只用 2025-26。

## 判定
- 單一結果「過」：ΔR² 95% 區間下界 > 0。
- 整體「值得加進 PHYS」：三個主要結果至少兩個過。
- 不論過不過都報告係數（每吋 ape 對結果的影響）與有量測的人數。

## 不做
- 不依結果改人群門檻、改變數定義、改 seed。
- 不碰 src/ 與卡片；這只回答「有沒有額外資訊」。
