# E-078 預註冊：臂展和抄截、防守嚇阻力有沒有關係（身高體重之外）

寫於 2026-10-29，在看任何臂展與抄截、RAPM 的關係之前。之後只能改路徑與錯字。

## 背景
E-077 發現體測 ape（臂展 − 赤腳身高）在身高、體重之外只多解釋蓋帽，籃板沒有。使用者問：抄截、整體防守嚇阻力是不是也和臂展有關？

已經看過、因此**不列入判定**的：2025-26 護框對手命中差（E-077 的次要結果）。

## 共用設定（沿用 E-077）
- 體測：`reports/E077-wingspan/combine-anthro.json`。姓名比對、別名、同名取最新一屆、缺值指標 miss 都和 E-077 一樣。
- 主要暴露 ape；次要（只報告）reach = 站立摸高 − 赤腳身高。
- 基準模型：結果 ~ 身高 + 體重 + miss；測試模型：基準 + ape。
- 樣本外：依 PLAYER_ID 奇偶分半，A 擬合→B 評估、B→A，合併算 held-out R²；ΔR² = 測試 − 基準。
- 以球員為單位 bootstrap 2000 次，seed 20261029，報 95% 區間；同時報每吋 ape 的係數和區間。

## 假設 S：抄截
- 資料：E-077 的球員季（2015-16 到 2025-26，GP ≥ 30 且 MPG ≥ 20）。
- 結果：STL/36（2015-16 到 2024-25 用 game logs 加總；2025-26 用 benchmark-source base.json）。
- 判定：ΔR² 下界 > 0 就算過。
- 只報告：四因素 RAPM 的 steal_defense、tovNonSteal_defense（人群同假設 D）。

## 假設 D：整體防守嚇阻力
- 資料：`reports/impact-rapm/`，2022-23 到 2025-26 四季合併、每人一列。
- 人群：防守回合 ≥ 2000（rapm.csv 用 pooledPoss，four-factors.csv 用 defensePossessions）。
- 身高、體重：用該球員最新一季的 bio（2025-26 benchmark-source 優先，否則 defense-seventh 最近一季）。
- 三個結果（正值 = 防守較好）：
  1. pooledD（整體防守 RAPM）
  2. rimShare_defense（讓對手少攻擊籃下）
  3. efg_defense（讓對手命中率下降）
- 判定：三個裡至少兩個 ΔR² 下界 > 0，才算「臂展和整體防守嚇阻力有關」。
- 只報告：fgaPerPoss_defense、threeShare_defense、ftRate_defense。

## 不做
- 不依結果改門檻（GP、MPG、2000 回合）、變數定義或 seed。
- 不碰 src/ 和卡片。
