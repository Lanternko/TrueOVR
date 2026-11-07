# E-202 預註冊：TO（少失誤）改用持球時間當用球量

- 日期：2026-11-02。問題卡 F-143（TO 榜被不持球的人佔據）。使用者 2026-11-02：「少失誤的球權權重應該更重。不然得榜的都是一些不持球的中鋒」→ lead 比球權／USG／持球時間 →「用持球時間」（R-136）。
- 基準：正式卡 card 0.2.10j（`reports/card-0.2.10j/ranking.csv`，sha256 4519d615…）；建法＝E-198 KG 臂（`reports/card-0.2.10j+E198-gravity/`）。
- 狀態：**已凍結**（2026-11-02）；sha256 見 `preregistration.sha256`（以 git HEAD 版 LF 計），之後不改，有錯寫 errata 給使用者核可。

## 0. 已揭露（lead 看過）
- 現行 tovSkill＝TOV ÷（FGA＋0.44·FTA＋AST＋TOV），四季滑動窗口（E-175 U 臂，`window8.py`），只看比率、不看用球量。
- card 0.2.10j MIN≥500：TO 前 30 有 19 人持球時間/36 低於池中位數 2.86（handle.csv 2025-26）；榜首 Hauser、Hardaway Jr.、Bey、McBride、Trent Jr.。
- 2025-26 上場 ≥1000 分鐘 279 人：失誤率與球權/36 相關 0.08；球權/36、USG 近似、持球時間/36 名次：Brunson 13／17／2、SGA 7／5／8、Jokić 5／18／58、Embiid 10／4／84、Bam 59／44／132、Hardaway 192／168／270。
- 試算過「球權/36 ×（中位失誤率 − 自己失誤率）」的名次（SGA 25→3 等），**這個公式不採用**，只是讓使用者看方向。
- E-069 第一階段：handle＝0.5·z(−控球失誤每持球秒，方法 c 收縮)＋0.5·z(持球/36)，樣本外 (h1)(h2) 過，對 2K27 Ball Handle ρ 0.739（n 249）。
- lead 沒看過新 TO 的數值、係數、OVR 或名次。

## 1. 改動（只一個主臂）
| 臂 | 內容 |
|---|---|
| K0 | 現行 card 0.2.10j（c0 先逐位元重現 ranking.csv） |
| **KT** | 只換 `tovSkill` 定義，其他全同 K0；**全部係數重擬合**（R-115，同 E-198 KG 的流程、不設下限） |

`tovSkill`（KT）定義（凍結）：
1. 持球秒數：NBA.com tracking `PtMeasureType=Possessions` 的 `TIME_OF_POSS`（分鐘），來源 `reports/handle-E069/raw/<季>/Possessions-FULL.json`（2022-23～2025-26）。
2. 窗口：失誤分子沿用 E-175 U 臂逐場權重 w_g。持球時間只有整季數字，有效持球分鐘＝Σ_季 TOP_季 ×（Σ_{g∈季} w_g·MIN_g）／MIN_季（同一個人該季的窗口權重佔比）。出賽分鐘同樣用 Σ w_g·MIN_g。
3. 比率：r＝窗口失誤 ÷ 窗口持球秒數；收縮照 E-069 方法 c 的公式與 `rsec` 已選的值（`reports/handle-E069/results.json` fits.rsec：k 64、kh 256、λ 0.2、先驗＝位置），分子換成**全部失誤**（不拆控球／傳球，R-136 只改用球量）。
4. 用球量：v＝窗口持球分鐘 ÷ 窗口出賽分鐘 × 36。
5. 合成：raw＝0.5·z(−r)＋0.5·z(v)，z 用現行 tovSkill 的池（同 K0 的池定義）算平均與標準差；0–99 轉換用現行 tovSkill 的 `to_attribute`／尾巴規則。權重 0.5 是 E-069 的既定值，不調。
6. 沒有 tracking 列的人（窗口持球分鐘＝0）：r 收縮到先驗、v 取池第 10 百分位；記 `topMissing=1`。
7. 其他 16 項能力值、gravity、用人層特徵、3PT 欄、align、H1 封頂、OVR 映射照 K0。

## 2. 判定（R-117／R-131）
人群：2025-26 MIN≥500（約 379 人）；bootstrap 球員層 2000 次，seed 20261102。

硬條件（只有兩類）：
- **A（機制）**：`tovSkill` 對 2K27 Ball Handle 的 Spearman（池內，`reports/ovr-v55-2k27-compare/2k27_ratings.csv`）KT − K0 ≥ MDE。MDE＝phase0 用 K0 bootstrap 算出的 90% 半寬，**寫檔後才跑 KT**。2K 不參與建構。
- **沒弄壞**：c0 逐位元重現；`npm test` 過；全體 OVR 對 2025-26 本季 RAPM Spearman KT − K0 ≥ −2h（h＝K0 的 bootstrap 90% 半寬，phase0 先算）。

B（問題卡 F-143，不擋採用）：TO 前 30 名中持球時間/36 低於池中位數的人數，19 → ≤10 算解決。

只報告（預期方向＋雜訊帶）：
- `tovSkill` 每 10 點 OVR 係數與 bootstrap SE；與 creation、pass、gravity 的 VIF（預期和 creation 相關升高）。
- 全體 OVR 對 2K27 OVR、EPM、薪水 ρ；RAPM 分半（單雙場）兩半各算一次方向是否一致。
- 前 100 名移動 ≥10 名人數、前 20 名進出；`topMissing=1` 的人另列。
- 球員表（K0→KT 的 TO、TO 名次、OVR、OVR 名次、持球/36）：SGA、Jalen Brunson、Luka Dončić、Nikola Jokić、Joel Embiid、Bam Adebayo、Tyrese Haliburton（若有）、Jrue Holiday、Tyus Jones、Cade Cunningham、Trae Young、James Harden、Sam Hauser、Tim Hardaway Jr.、Dean Wade、Rudy Gobert、Jarrett Allen、Luke Kornet。預期持球主控 TO 上升、低用球射手與中鋒下降；只報告、不當門檻。

## 3. 限制
- 只寫 `reports/card-0.2.10j+E202-to-possession/`；其他目錄唯讀。不改 `src/`、`scripts/`、網站、live/。
- 採用後才另做：賽中 OVR 每日抓 2026-27 Possessions tracking（照 `scripts/fetch_gravity.mjs` 模式）、網站 TO 說明文字（`season_nav.py` 的 `ATTR_TIPS`、`tov_rows`）、新秀起點重解（R-096）。

## 4. 回報
照 CLAUDE.md 六段（# 總評、這次目標、進步、退步、直觀證據、要你決定的事）；白話講 TO 榜換成誰、持球主控和中鋒的 OVR 怎麼動；Δρ、區間只寫 `report.md`。
