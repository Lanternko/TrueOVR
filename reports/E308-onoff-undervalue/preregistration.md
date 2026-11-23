# E-308 預註冊：OVR 是否系統性低估高 On/Off 球員

凍結日 2026-11-23（R-165：Claude 自定標準直接凍結開跑；本檔 commit 後不改，改動只能另開段落註明日期與理由）。

## 問題
使用者看到 Wembanyama on/off +43 的影片，要用 on/off 檢查模型是否低估某些人（例：LaMelo Ball 2026-27 賽中 OVR 73.5、#144）。
要回答的是：**on/off 高於 OVR 預期的人，是模型漏掉了東西，還是 on/off 雜訊／環境造成的？**
on/off 樣本小（單季約 1000–5000 回合）、受替補與同場隊友影響，只當旁證（R-178）；所以主判定看「樣本外有沒有預測力」，不看樣本內相關。

## 資料（全部是現成檔，不另抓）
| 代號 | 內容 | 來源 |
|---|---|---|
| OVR | card 0.2.15（2025-26 正式卡，四季窗口 ≤2025-26）`ovr`；敏感度用 `ovr36` | `reports/card-0.2.15/ranking.csv`（用姓名對到 playerId：onoff.csv、rapm-prior.csv、賽中 ranking.csv） |
| OO_s | 第 s 季在場減不在場每 100 回合淨效率，2022-23～2025-26 | `reports/impact-rapm/onoff.csv`；同季多隊依在場回合加權 |
| RAPM | 四季合併 RAPM 淨值 `pooledNet` | `reports/impact-rapm/rapm-prior.csv` |
| DARKO | 2025-26 `dpm` | `data/external-impact/darko/darko_2025-26.csv` |
| Y1 | 2026-27 on/off（stints 到 2026-11-22） | `reports/defense-seventh/2026-27/stints/stints.jsonl`，算法同 `rapm.py onoff()` |
| Y2 | 2026-27 單季 RAPM 淨值（`rapm.py fit_rapm`，無先驗，λ 用 5 折 CV 選） | 同上 stints |
| 半季 | 2025-26 依 gameId 奇偶分兩半的 on/off | `reports/defense-b1/stints.jsonl` |

標準誤：每回合得分標準差取 1.15 → 單季 on/off 標準誤 ≈ 115·√(2/p＋2/q)（p、q＝在場／不在場每邊回合）。

## 人群
card 0.2.15 名單、對得到 playerId、2025-26 在場每邊 ≥1000 回合。H1 另要求 2026-27 在場每邊 ≥300、不在場每邊 ≥100 回合。

## 建構
- **OO4**：2022-23～2025-26 on/off 依每季在場回合加權平均；標準誤同法合成。
- **經驗貝氏收縮**：OO4* = m + τ²/(τ²+se²)·(OO4 − m)，m＝人群回合加權平均，τ²＝max(0, 人群變異 − 平均 se²)。
- **R_OO**：OO4* 對 OVR 做 OLS 後的殘差（＝OVR 沒解釋到的 on/off）。比較臂 **R_RAPM**（pooledNet 對 OVR 殘差）、**R_DARKO**（dpm 對 OVR 殘差）。
- 正殘差＝on/off（或 RAPM、DARKO）比 OVR 預期高，即「OVR 可能低估」。

## H1（主判定，樣本外）：R_OO 能不能預測 2026-27？
WLS：Y = a + b1·z(OVR) + b2·z(R_OO)，權重＝2026-27 在場每邊回合；Y 各做 Y1、Y2。
- 推論：以 2026-27 球隊為群集重抽 2000 次（seed 308），報 b2 的 90% 區間。
- 附表：同模型換 R_RAPM、R_DARKO；以及 Y = z(OVR)+z(R_OO)+z(R_RAPM) 看 on/off 在 RAPM 之外還有沒有東西。
- 附表：各預測量對 Y1、Y2 的 Spearman（OVR、ovr36、OO4*、pooledNet、DARKO）。
- 子群：留隊（2025-26 主隊＝2026-27 主隊）與換隊分開跑 b2。

## H2：殘差集中在哪一型？（類型在看結果前用屬性定義）
人群百分位定義（card 0.2.15 屬性）：
- **G1 創造型低效率持球者**：pos PG 或 SG，creation ≥ 第 75 百分位，且 (long+mid+short)/3 ≤ 中位數。
- **G2 3D 側翼**：pos SG 或 SF，long ≥ 第 60 百分位，max(onBall, pressure) ≥ 第 60 百分位，creation ≤ 中位數。
- **G3 護框長人**：pos C 或 PF，help ≥ 第 75 百分位。
- **G0 其他**。
每組報 R_OO 平均（樣本內）與 Y2、Y1 對 OVR 單變量殘差的平均（樣本外），群集重抽 90% 區間。

## H3：R_OO 本身穩不穩？
- 2025-26 奇偶場兩半各算 on/off，各自對 OVR 取殘差，兩半相關 r，Spearman-Brown 換成整季信度 2r/(1+r)；同法算原始 on/off 的信度對照。
- 逐年：2024-25 與 2025-26 單季 on/off 對 OVR 殘差的相關，留隊／換隊分開。

## 判定規則（凍結）
1. **模型漏掉東西**：Y2（RAPM）的 b2 90% 區間 > 0。只有 Y1 > 0、Y2 跨 0 → 「只在 on/off 裡持續，可能是環境／替補結構」，不算模型漏掉。
2. **雜訊為主**：Y1、Y2 的 b2 區間都跨 0，且 H3 整季殘差信度 < 0.3。
3. **環境**：H3 留隊相關明顯高於換隊（差 ≥ 0.15）且 H1 換隊子群 b2 跨 0 → 殘差主要跟著球隊走。
4. 類型集中：某組 Y2 樣本外殘差平均 90% 區間 > 0（或 < 0）才說該型被系統性低估（高估）。
5. 以上都用 card 0.2.15 `ovr`；`ovr36` 只當敏感度，不改判定。

## LaMelo 拆解（描述，不進判定）
- OVR 組成：pred0、defenseBonus、mixBonus、上場時間（mpg）與同位置（PG）人群比較；predictedPer36 名次 vs OVR 名次。
- 屬性貢獻：(屬性 − PG 人群平均)/10 × `card-0.2.15-w246 K6 valuePer10AttributePoints`（每 36 分鐘淨值）。
- 他歷年 on/off、標準誤、RAPM、DARKO；2026-27 賽中 OVR 組成（live ranking 的 pred0／defenseBonus／mixBonus／formBonus／MPGhat）。

## 不做
不改 OVR、不調參；結果只回答問題並提出下一步選項。
