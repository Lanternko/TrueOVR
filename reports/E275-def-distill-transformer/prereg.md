# E-275 預註冊：用能力值擬合 Transformer 換人防守值（蒸餾），當網站 DEF 顯示欄

- 日期：2026-11-08。角色：role-card。來源：使用者提議「把 T 當正確答案，用現有能力值去擬合 T 的排名」。標準由執行者自訂並直接凍結（R-165）。
- 凍結時已知 E-274 結果（D0 0.422、D2 0.367），所以本實驗的臂與門檻全部事前固定、不依結果調；擬合只用 t 季 T 值當標籤，不碰 t+1 季目標（L-026）。
- **只動顯示欄，OVR、卡片、線上頁面一律不動。**

## 1. 目標、折、人群
完全沿用 E-274（`reports/E274-def-display-transformer/prereg.md` §1）：t 季 DEF 值預測 t+1 季防守 RAPM×W 的 Spearman ρ，三折 22-23→23-24、23-24→24-25、24-25→25-26，同一共用人群（E-274 的 `com`），依人數加權合併。D0、D2 數值直接從 E-274 的同一程式重算。

## 2. 新臂（擬合標籤＝t 季 D2＝−T 換人後對手每 100 回合得分；擬合人群＝t 季 d2 有值的全部池內球員）
- **D5 三項蒸餾**：D2 ~ 位置截距 + onBall + help + pressure（OLS，跨位置共用斜率）。DEF＝擬合值（去掉位置截距後也報告，見 §4）。
- **D6 全能力值蒸餾**：D2 ~ 位置截距 + 卡片全部能力值 long, mid, short, ft, drive, foulDraw, tovSkill, pass, rebound, physique, onBall, help, stamina, heightInches, creation, pressure, foulDisc（17 項，OLS）。
- **D7 全能力值＋加分**：D6 再加 defenseBonus。
- 主判定值用「含位置截距的擬合值」（T 本身就分位置看高低，截距屬於 T 的判斷）。

## 3. 採用門檻（同 E-274）
D5／D6／D7 任一要同時成立：(a) 合併 ρ 是 D0、D5、D6、D7 中最高；(b) 比 D0 高 ≥ +0.03；(c) 每一折都 ≥ D0。都沒過就維持 D0。

## 4. 只報告
- 蒸餾忠實度：各臂與 D2 在 t 季的 ρ（樣本內）；把 t 季係數套到 t+1 季卡、和 t+1 季 D2 的 ρ（2022-23→2023-24、2023-24→2024-25 兩組有 t+1 的 D2）。
- 去位置截距版 D5/D6 的合併 ρ。
- D6 的標準化係數（哪些能力值 T 最看重）。
- 例子：2024-25 折 Durant、Curry、Wembanyama、Gobert、Caruso、Amen Thompson、Sengun、Jokić、Trae Young 在 D0／D2／D5／D6／D7 的名次。

## 5. 限制
全部本機輕量計算（讀 E-274 已產生的 d2-<t>.json 與 E-269 的 t 季卡），不重訓 T。
