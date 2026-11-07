# E-225 資料盤點

產生：`python -I -X utf8 reports/E225-lineup-transformer/build_dataset.py`（本機 37 秒，純 Python）。數字來自 `inventory.json`，輸入／輸出 sha256 在 `manifest.json`。大檔在 `data/`（不進 git）。

## stints（上場片段）

| 季 | 來源 | stints | 場次 | 回合（兩邊合計） | 每段每邊回合 | 主切分 train／test 場次 |
|---|---|---:|---:|---:|---:|---|
| 2014-15 | defense-seventh/2014-15/stints-ff | 37,475 | 1,217 | 233,287 | 3.11 | 953／264 |
| 2015-16 | 同上格式 | 37,628 | 1,216 | 237,709 | 3.16 | 984／232 |
| 2016-17 | 〃 | 37,516 | 1,223 | 239,991 | 3.20 | 964／259 |
| 2017-18 | 〃 | 37,021 | 1,219 | 240,663 | 3.25 | 982／237 |
| 2018-19 | 〃 | 37,557 | 1,215 | 246,974 | 3.29 | 994／221 |
| 2019-20 | 〃 | 33,460 | 1,047 | 213,444 | 3.19 | 815／232 |
| 2020-21 | 〃 | 31,337 | 1,045 | 210,386 | 3.36 | 852／193 |
| 2021-22 | ovr-inseason-2026-27/v5/pathA/ff-2021-22/stints-ff | 35,406 | 1,167 | 232,831 | 3.29 | 940／227 |
| 2022-23 | defense-seventh/2022-23/stints | 33,132 | 1,108 | 223,612 | 3.37 | 877／231 |
| 2023-24 | defense-seventh/2023-24/stints | 32,053 | 1,093 | 218,804 | 3.41 | 874／219 |
| 2024-25 | defense-seventh/2024-25/stints | 33,396 | 1,104 | 221,881 | 3.32 | 883／221 |
| 2025-26 | defense-b1/stints.jsonl | 39,669 | 1,220 | 246,883 | 3.11 | 前向（整季） |
| 2026-27 | defense-seventh/2026-27/stints（至今） | 3,571 | 100 | 20,338 | 2.85 | 前向（至今） |

- spec 說缺 2021-22：其實有，在 `v5/pathA/ff-2021-22/stints-ff/`（35,406 段，欄位同 ff 格式）。`defense-seventh/2014-15…2020-21/stints/` 只有得分，要用同季的 `stints-ff/`。
- 欄位（所有季都有）：`period, seconds, lineups[2][5], id(game), teams[k].{teamId, players, defensivePossessions, opponent{points, fga, fgm, longA/M(三分), fta, ftm, tov, oreb, dreb, teamOreb, teamDreb, reboundOpportunities, …}}`。`teams[k].opponent` 是 k 防守時對手的帳，所以 X 的進攻數據取 `teams[對方].opponent`，X 的回合＝`teams[對方].defensivePossessions`；X 防守籃板＝`teams[X].opponent.dreb+teamDreb`（schema 見 `defense-seventh/2024-25/stints/stint-schema.json`）。2021-22 以前的 ff 格式沒有籃下／中距細分（shortA＝0），本實驗不用。
- 2021-22 起每季場次 1,093–1,167 場，少於 1,230（stint 重建時掉的場次，沒補）；2019-20／2020-21 是縮水季。
- 每段兩邊合計約 6.4 回合，跟 spec 說的約 6 回合一致。

## 每季能力值（本季）

| 季 | 來源 | OVR | 能力值 | pid 對應（依上場秒數） | 上季能力值對應 |
|---|---|---|---|---:|---:|
| 2014-15～2016-17 | **沒有**（主樹裡沒有這幾季的卡或屬性；只有某個 worktree 有 pathA prior 2015-16 起，不硬湊） | — | — | 0 | — |
| 2017-18～2020-21 | `ovr-inseason-2026-27/e111-card027/cards/prior-<季>-027.json`（v5 pathA 舊卡為底、9 個合併池屬性 027 映射，用該季自己的 box） | 無 | 15 項，但 onBall、help 全部同值（70），等於沒有防守屬性 | 100% | 2017-18 無；其餘 89% |
| 2021-22 | `ovr-inseason-2026-27/v4/cards/2021-22.csv` | 有（無 RAPM，純屬性） | 15 項；onBall、help 同值 | 100% | 89% |
| 2022-23～2024-25 | `v4/cards/<季>.csv` | 有（RAPM 窗只到目標季前一季） | 15 項全有鑑別力 | 100% | 89–90% |
| 2025-26 | `v4/cards/2025-26.csv` | 有（RAPM 2022-25） | 15 項 | 100% | 88% |
| 2026-27 | `live/<最新日>/ranking.csv`（建檔時 2026-11-02，季中每日變） | 有（live） | 15 項 | 97.8% | 92% |

- 能力值欄：long、mid、short、ft、drive、tovSkill、pass、rebound、physique、onBall、help、stamina、creation、pressure、heightInches＋OVR、位置。foulDraw、gravity 只有部分季有，不用。
- v4 卡是同一條管線的五季（屬性用本季 box、OVR 的 RAPM 只用目標季以前），跨季一致性最好，所以選它。v5 卡（只有 2023-24、2024-25）的 RAPM 窗**含目標季**，等於把同批比賽的在場結果放進 OVR，不用。
- 2017-18～2021-22 的 onBall／help 是常數（`attrDiscrimination500min`：sd 0），訓練時這兩欄遮罩成缺值；stamina 是分級值（同值比例約 1/3），保留。
- 上季能力值臂：用 s−1 季的同一來源；缺的人（新秀、新來的）遮罩成缺值，對應率約 89%。

## 可用季數結論

- **核心（本季 OVR＋能力值齊全、管線一致）：2021-22～2024-25 四季**，訓練池（80% 場次）約 72 萬回合、test（20%）約 18 萬回合。其中 2021-22 缺防守屬性。
- 擴充（只有屬性、沒 OVR、沒防守屬性）：2017-18～2020-21 四季，訓練池另 73 萬回合。
- 只有球員 ID：2014-15～2016-17。
- 前向：2025-26 整季（24.7 萬回合）、2026-27 至今（2 萬回合）。
