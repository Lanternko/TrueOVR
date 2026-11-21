# E-147 預註冊：卡片 usage 層的爛隊旗標 d 改連續（和賽中同公式）

- 日期：2026-10-31。來源：使用者「卡也改連續 d」（看完 Flagg G40→最後一場拆解後；F-090、R-097）。
- 基準：card 0.2.7c（E-131 K1，ranking sha 99466f36…1655）。

## 0. 已揭露
- 0.2.7c 對薪水、2K27、自製 EPM 式的 Spearman（`reports/salary-corr/corr-output.txt`）。
- 用固定錨點粗估的變動（不是正式卡）：35 個年輕人會變。例如 Fears +11.6、Queen +11.3、Flagg 61.5→70.1、Rollins 85.9→76.6、Giddey −6.4。
- 沒看過任何候選卡對外部指標的數字。
- 本實驗**沒有可調參數**：d 公式照搬線上 `run_c4_live_rookie.py:team_badness`，使用者 2026-10-31 已定。

## 1. 改動（只改這一處）
`e094.py` 的 `scope_feats` 原本是 `d = 1[主隊全季勝率 < 0.35]`。改為主隊全季：
- nr＝得失分差總和／(GP+10)
- wp＝(W+5)／(GP+10)
- s＝0.7·(0.5+0.033·nr)+0.3·wp
- d＝clip((0.40−s)/0.10, 0, 1)

其他照原樣：主隊＝該範圍上場分鐘最多的隊；半季擬合時 d 也用全季戰績；資料是 `data/season-source/team-games.json` 的 PLUS_MINUS、WL。

用唯讀匯入 e094 再替換函式的方式改，不動原檔。

## 2. 臂
| 臂 | 內容 |
|---|---|
| K0 | 0.2.7c 原樣重跑；c0：ranking 要和 0.2.7c 逐位元相同，不同就停 |
| D1（主臂） | 連續 d，pipeline 照常重擬合 usage 係數（卡本來每次建卡都重擬合） |
| D0（只診斷） | 連續 d，套 K0 的係數，不重擬合；只報告，不參與決定 |

## 3. 指標
人群：卡 MIN ≥ 500，外加子組 ≤23 歲（y=1，d 只透過 y·d·L 起作用）。全部用 Spearman：
- M2K：對 2K27 overall（`reports/ovr-v55-2k27-compare/2k27_ratings.csv`）
- Msal：對 log 2025-26 薪水，用 salary-corr 的 `salaries()`。只算 ≥24 歲：≤23 歲多半是新秀約，薪水反映的是順位
- Mepm：對自製 EPM 式（epm-live.csv 的 careerO+careerD）
- m1–m3：原 `e089_eval`（RAPM 分半樣本外）照原門檻報告
- 一致性：2025-26 季末用 `team_badness` 算出的 d，和卡的 d 每隊相等（差 < 1e-9）

## 4. 判定
D1 採用候選必須同時符合：
- (a) 一致性通過；
- (b) M2K（全體、≤23）、Msal、Mepm 的點估計都沒有降超過 0.01；
- (c) m1–m3 沒有比 K0 多掛任何一道門檻。

另外報告：b8 係數 K0→D1、Flagg 等人名次、前 20 換人、前 300 名移動 ≥10 名的人數（R-064）。

採用與否、版本號（0.2.7d？）由使用者決定。賽中老將 d 改成當下球隊是另一件事，不在本實驗內。
