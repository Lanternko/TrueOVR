# v5 Path A — 2014-15..2020-21 補抓：來源、轉換、等價驗證

- 日期：2026-10-28
- 範圍：pbp、bio（身高、體重、年齡）、每季 four-factors，轉成 2021-22 的檔案格式後重跑 D0。
- 結果：見 `d0-gate.md`。只剩 2014-15 不能進鏈（缺 bio），Y3／Y5／Y6 可判定。
- 停在 D0：沒有建 RAPM 窗、卡片，沒有跑回測。

## 1. 規則（照任務 spec）

- 只用 NBA 官方端點原始輸出的公開存檔（GitHub raw）。
  - 沒有連 nba.com，沒有換 UA，沒有用 proxy。
- 下載檔只當資料讀：
  - 解壓到 `D:\Projects\temp\nba-old-seasons\{x,x2}`。
  - 不執行其中任何程式。Python 一律 `-I`。
- 沒有用其他季替代缺資料，沒有用現代身高體重回填，沒有讀 2026-27。
- 寫入範圍：
  - `data/defense-seventh/2014-15..2020-21/`
  - `reports/defense-seventh/2014-15..2020-21/`
  - `v5/pathA/`
  - `scripts/fetch_old_seasons_v5*`
- 沒有 commit。

## 2. 來源（逐層）

### 2.1 pbp

| 季 | 主來源（v3 / liveData） | 輔助來源（v2，取 EVENTNUM 對應欄位） |
|---|---|---|
| 2014-15 | `nbastatsv3_2014.tar.xz` `76a5398235900fd5b914eaeb1464e76fc05517184d04c503404a16a44d14f741`（8,073,464 B） | `nbastats_2014.tar.xz` `f6a48f32ed7887d6e1885354a9e46b8852040a9f9ce344eaa18e634803cd2eaf`（8,024,656 B） |
| 2015-16 | `nbastatsv3_2015` `7bbb1e8a1512dd2877be97cb73d990c424a2f7488137ca5d7a6285e2afea873e`（8,278,740） | `nbastats_2015` `217087b27259e34ec9c82a596335a36ce6580e5f9129e186e6a1b4f0dc592ebf`（8,307,212） |
| 2016-17 | `nbastatsv3_2016` `6c94890f389abe5af085ff19a26a80e7fe0d205c55dc201aefaa078a887540f4`（8,323,760） | `nbastats_2016` `fab9222699fd126e24a3aa01805013ad73a84aafd06f01b8b69f3f9f9b130d0f`（8,341,720） |
| 2017-18 | `nbastatsv3_2017` `e9fedc33337e6a34dc4373bc5138e742e6bbcf09477b34568d79588dead7e62c`（8,371,044） | `nbastats_2017` `efd8c7139acb737ebdc76e0b98b118cb6152caffc0077cf2c7b6ef25a580e50f`（8,361,064） |
| 2018-19 | `nbastatsv3_2018` `a8c05607863b0bb0da51ed65fc89866cbb5c1954f7951ce00ed05f2ad178097d`（8,680,224） | `nbastats_2018` `b5416e7d270011970e7934de0cabb41cf75c16f48b34c2b035e1a96760faa407`（8,705,484） |
| 2019-20 | `nbastatsv3_2019` `3fc651e4c294e231723fa097dca2cf938dd868ee2b9a6111f22ab9c0728e89dc`（7,529,968） | `nbastats_2019` `06c53b6e42be2698dbbf550260f46f9ca51ad495fb8e9964a0c24473a3fe7064`（7,504,672） |
| 2020-21 | `cdnnba_2020.tar.xz` `e45e1b4a70a33ce93525c58f04362b6c275f7e514789772d4a8360f22a13f4f2`（15,548,680，cdn.nba.com liveData） | – |

- **URL**：`https://github.com/shufinskiy/nba_data/raw/main/datasets/<name>.tar.xz`。
  - 每個 pbp 檔的 URL、`#gameId` 與 SHA256 都記在 `data/defense-seventh/<season>/manifest.json` 的 `sources`。
  - 封存檔 SHA 記在 `manifest.json` 的 `v5fetch.archives`。
- **2021-22 驗證用的封存檔**（只寫到 temp，沒有寫進 repo 的 2021-22 目錄）：
  - `nbastatsv3_2021` `f44ec8a4…`
  - `nbastats_2021` `54991541…`
  - `cdnnba_2021` `0c116aff…`
- **路徑選擇**：
  - 2020-21 用 liveData（`cdnnba_2020`），它和 2021-22 原檔同源。2021-22 等價驗證時，這條路的投籃分區與 bio 都是 0 差異（§5）。
  - 2014-15..2019-20 用 v3+v2。本輪沒有下載、也沒有查證這幾季的 cdnnba 存檔。

### 2.2 box（player-games／team-games）

- 來源：PR #5 的 `v5/history/box-games-<S>.csv.gz`，上游是 https://github.com/NocturneBear/NBA-Data-2010-2024。
- SHA：

  | 季 | SHA256 前 8 碼 |
  |---|---|
  | 2014-15 | 292a99d9 |
  | 2015-16 | 668d9084 |
  | 2016-17 | 44ddef7d |
  | 2017-18 | e5ecff7f |
  | 2018-19 | 17d34d3a |
  | 2019-20 | 19c82ce0 |
  | 2020-21 | 9d1382b5 |

  完整 SHA 在 `manifest.json` 的 `v5fetch.box`。
- 被交易球員：照 §R.7 第 1 條，逐場列保留原隊，季總分鐘跨隊加總。

### 2.3 bio

- 來源：Fekouto/ciencias_de_dados_nba `dados/perfis_por_temporada/<S>.csv`，是 leaguedashplayerbiostats 的逐季存檔。
- URL：`https://raw.githubusercontent.com/Fekouto/ciencias_de_dados_nba/HEAD/dados/perfis_por_temporada/<S>.csv`

| 季 | 來源 SHA256 | 列數 | 產出 `bio.json` SHA 前 16 |
|---|---|---|---|
| 2014-15 | **無來源**（存檔從 2015-16 開始） | – | – |
| 2015-16 | `35f139dd75571cc2f34181494d38745ee6b1a3eb7241be682438ac2ab645f234` | 476 | c10ded80fb8a8bf2 |
| 2016-17 | `62849534a4b15d5b288dc3ffca34a47d7c23fb40be75b0498830ad85359efa3b` | 486 | 74119aa891f5f7a4 |
| 2017-18 | `cc700f5fee5950f44da215fab7c35d2c2a7d8b7e34cf2778d82192f8adbe8199` | 540 | 4b882c54bbe91627 |
| 2018-19 | `e4e3eb5c45c1b229d1837fab49eda501bc954f4caed7538f469e349561a92c71` | 530 | d318592af485aa66 |
| 2019-20 | `bc6d9632211cfb3af2ca32ec92d7280a8f1083cf99155be7b98c34bf99417702` | 529 | 1d7ec83c040e2dcb |
| 2020-21 | `c693de71180ca978aa2da1093f84b29c5e58fee70dc97c77e4d1f5c200b86a98` | 540 | f8f690ac19da7145 |

- 2014-15 的查證：在 GitHub 樹狀清單中，`perfis_por_temporada/` 最早一檔是 `2015-16.csv`。清單存在 `D:\Projects\temp\nba-old-seasons\fekouto-tree.json`。
- 沒有找到其他「官方 leaguedashplayerbiostats 原始輸出」的 2014-15 公開存檔，所以**明說缺**，不湊。

### 2.4 four-factors

- 不是下載來的。由本機 stints 重算：
  - `scripts/fetch_old_seasons_v5_stints.js`：完整 factor 欄位的 stints，寫到 `reports/defense-seventh/<S>/stints-ff/`。
  - `scripts/fetch_old_seasons_v5_ff.py`：ridge、5-fold CV 與 λ 網格直接 import v3 `tools/four_factors_2022_25`，寫到 `data/defense-seventh/<S>/four-factors.csv` 與 `-summary.json`。
- 2021-22 重現檢查：
  - JS 版 stints 重現 v3 參考 stints 的 SHA `aad3227a…`。
  - ff 腳本餵 v3 參考 stints，重現 v3 `four-factors-2021-22.csv` 的 SHA `c94cb993…`。

### 2.5 程式 SHA256

| 檔 | SHA256 |
|---|---|
| `scripts/fetch_old_seasons_v5.py`（轉換器，記在每季 manifest） | `58953de1ad95b09c727cb05d4b621b14aef1d1692e5761afabd2a67433f67872` |
| `scripts/fetch_old_seasons_v5_equiv.py` | `faf898a49c532976d16f067a303f20b931b985ccf61da8aa4ef8a509d38cc89c` |
| `scripts/fetch_old_seasons_v5_attrs.py` | `bac35eacc4cc0b29979987b3d06176844cccaaff80d28aca43616e789d44a539` |
| `scripts/fetch_old_seasons_v5_stints.js` | `9180be1f815ef9eb00bbcef93fb5979443ee396722f7b1f532d3e4d57d3450cd` |
| `scripts/fetch_old_seasons_v5_ff.py` | `023c6edc133e5a7b124db1f3dad91debbdccf8df0aa1cbbd49d57c96ef033cff` |
| `scripts/fetch_old_seasons_v5_ffcmp.py` | `e38154a02f266f4f9c5af162036f2efd6c3191ecad0839210dbfc366b821606f` |
| `v5/pathA/d0_gate.py`（只加 3 行路徑偵測） | `020e113e34b5ab77ae50e64dc52d5c9bf861cb8514a76f62801ce2531006fc84` |

## 3. 轉換重點

- **v3+v2 合併**：v3 的 `actionNumber` 對 v2 的 `EVENTNUM`，從 v2 取：
  - 球員 ID
  - 換人的上下場球員
  - 籃板與犯規歸屬
- **v3 抄截／阻攻列**：
  - 問題：這些列與它所屬的投籃或失誤共用同一個 `actionNumber`。原樣寫出時，stints 的 shotMap 會把籃板對到阻攻列，進攻籃板機會跟著消失。
  - 修正：改用 `actionNumber + 100000`（`BLOCK_STEAL_AN_OFFSET`）。
  - 修正後 2021-22 同場次 orebRate r 從 0.977 升到 0.9995／0.9997。
- **2019-20**：
  - 0021901316–18 三場在 v2 沒有資料（`withoutV2=3`），只用 v3 轉。球員 ID 用姓名對 box 補，對不到 5 人次（`nameMiss=5`）。
  - pbp 從 PR #5 的 1,056 場補到 1,059 場。
- **逐季轉換統計**（`manifest.json` 的 `v5fetch.conversionStats`）：

| 季 | 來源 | pbp 場數 | bio 人數 | rebCounterVsInference | noTurnoverDropped | withoutV2 |
|---|---|---|---|---|---|---|
| 2014-15 | v3+v2 | 1,230 | – | 5 | 2 | 0 |
| 2015-16 | v3+v2 | 1,230 | 476 | 10 | 2 | 0 |
| 2016-17 | v3+v2 | 1,230 | 486 | 15 | 10 | 0 |
| 2017-18 | v3+v2 | 1,230 | 540 | 5 | 117 | 0 |
| 2018-19 | v3+v2 | 1,230 | 530 | 0 | 82 | 0 |
| 2019-20 | v3+v2 | 1,059 | 529 | 0 | 26 | 3 |
| 2020-21 | liveData | 1,080 | 540 | 0 | 0 | – |

## 4. 每季覆蓋與產出

| 季 | stints（PR #5 原樣）行 | stints-ff 有效場／失敗 | stints-ff 行 | PR #5 validLineupGames | ff stintSides | ff 球員 | four-factors.csv SHA 前 16 | stints-ff SHA 前 8 |
|---|---|---|---|---|---|---|---|---|
| 2014-15 | 37,384 | 1,217／13 | 37,475 | 1,218 | 70,343 | 492 | 1ce8ea66ad373ead | 8770c3d3 |
| 2015-16 | 37,729 | 1,216／14 | 37,628 | 1,222 | 70,550 | 476 | 370521b25b081295 | 89cf24bb |
| 2016-17 | 37,327 | 1,223／7 | 37,516 | 1,221 | 70,505 | 486 | 76038c4e815516d2 | c68dcd92 |
| 2017-18 | 36,760 | 1,219／11 | 37,021 | 1,210 | 70,061 | 540 | 6b0ebef46f0756a5 | 0d604fef |
| 2018-19 | 37,630 | 1,215／15 | 37,557 | 1,219 | 71,269 | 530 | 558079367d2714cc | f59d05c1 |
| 2019-20 | 33,397 | 1,047／12 | 33,460 | 1,046 | 63,295 | 529 | 0ce83ea4414dbe44 | d338bf9a |
| 2020-21 | 31,911 | 1,045／35 | 31,337 | 1,066 | 59,512 | 540 | 19af1c524e1f1101 | 4bbeab06 |

- **兩份 stints 的用途不同**：
  - `stints/stints.jsonl` 是 PR #5 gz 的原樣解壓，只有得分與回合。
    - 2020-21 原檔 SHA `6ccb8eb7…` 等於 gz 解壓的 SHA，沒有覆寫。
    - 這份是 D0 與日後 RAPM 用的。
  - `stints-ff/` 只給 four-factors 用。
- **xy 覆蓋**：七季兩分出手的 xy 都是 100%，area 欄位都是 0%（2021-22 也是 0%）。
- **目錄大小**：每季 `data/defense-seventh/<S>/` 約 234–364 MB。

## 5. 2021-22 等價驗證

方法：用同一個轉換器，把 2021-22 的封存檔轉到 temp，與 repo 既有的 2021-22 原檔比對。兩條路分開跑：
- v3+v2：舊季用的路徑。
- liveData：2020-21 用的路徑。

明細在 `v5/pathA/equiv/`：
- `equiv-2021-22.json`
- `attrs-*.json`
- `ffcmp-*.json`

### 5.1 原始層

| 項目 | liveData 路徑 | v3+v2 路徑 |
|---|---|---|
| pbp 投籃分區（596 人） | 0 人不同 | 89 人不同，最多差 2 球，r ≥ 0.999998（v3 來源修訂） |
| bio（605 人：身高、體重、AGE、AST%、OREB%／DREB%、GP） | 0 不同 | 0 不同 |
| player-games（26,039 列） | MIN 64 列差 ≤1（x:30 進位）；PLUS_MINUS 393 列差 ≤14；其餘全等 | 同左 |
| playerSeason MIN | 58 人不同，最多差 2 | 同左 |
| team-games（2,460 列） | TOV 3 列差 1 | 全等 |

- PLUS_MINUS 差異來自 box 來源不同（PR #5 上游與 nba.com box）。v4 卡片管線不讀 PLUS_MINUS。

### 5.2 15 項屬性（`v4/data/prior-2021-22.json` 對照，605 人）

格式：r／最大差／差 >1 人數。前三欄用 v3 既有 four-factors；後兩欄改用本輪重算的 four-factors。

| 屬性 | ref（原檔重跑） | liveData | v3+v2 | liveData + 自算 ff | v3+v2 + 自算 ff |
|---|---|---|---|---|---|
| long | 1／0／0 | 1／0／0 | 1／0／0 | 1／0／0 | 1／0／0 |
| mid | 1／0／0 | 1／0／0 | 0.99988／1.371／6 | 1／0／0 | 0.99988／1.371／6 |
| short | 1／0／0 | 1／0／0 | 0.99985／1.948／8 | 1／0／0 | 0.99985／1.948／8 |
| ft | 1／0／0 | 1／0／0 | 1／0／0 | 1／0／0 | 1／0／0 |
| drive | 1／0／0 | 1／0／0 | 1／0／0 | 1／0／0 | 1／0／0 |
| tovSkill | 1／0／0 | 1／0／0 | 1／0／0 | 1／0／0 | 1／0／0 |
| pass | 1／0／0 | 0.999997／0.249／0 | 同左 | 同左 | 同左 |
| rebound | 1／0／0 | 0.999998／0.498／0 | 同左 | 同左 | 同左 |
| physique | 1／0／0 | 1／0／0 | 1／0／0 | 1／0／0 | 1／0／0 |
| onBall | 常數 70 | 常數 70 | 常數 70 | 常數 70 | 常數 70 |
| help | 常數 70 | 常數 70 | 常數 70 | 常數 70 | 常數 70 |
| stamina | 1／0／0 | 0.999998／0.249／0 | 同左 | 同左 | 同左 |
| heightInches | 1／0／0 | 1／0／0 | 1／0／0 | 1／0／0 | 1／0／0 |
| creation | 1／0／0 | 0.999993／0.722／0 | 同左 | 同左 | 同左 |
| pressure | 1／0／0 | 1／0／0 | 1／0／0 | **0.9672／17.53／394** | **0.9547／18.77／423** |

- pbp、box、bio 這三層：14 項屬性與參考值幾乎一致。
  - liveData 路徑沒有人差超過 1。
  - v3+v2 路徑的 mid／short 有 6／8 人差超過 1，最多 1.95。原因是 v3 來源本身的投籃修訂。
- **pressure 是唯一明顯的差異**，來源是 four-factors 的有效場次樣本，見 5.3。

### 5.3 four-factors（對 v3 `four-factors-2021-22.csv`，602 人）

| 比較 | 有效場次 | 各 factor r 範圍 | defensePossessions |
|---|---|---|---|
| v3+v2，全樣本 | 1,221（ref 1,065） | 0.947–0.982 | r 0.994，最大差 1,313 |
| liveData，全樣本 | 1,167（ref 1,065） | 0.960–0.988 | r 0.997，最大差 1,062 |
| v3+v2，限 ref 同一組場次 | 1,065 | 0.9988–0.99999 | r 1.000，最大差 3 |
| liveData，限 ref 同一組場次 | 1,065 | 0.9990–0.9997 | r 0.99994 |

- 同一組場次下，演算法與資料轉換是等價的（r ≥ 0.999）。
- 全樣本的差異來自「哪些場次的陣容能完整重建」：
  - v3 參考檔在 2021-22 只有 1,065 場有效。
  - 新轉換有 1,167／1,221 場有效。
  - 多出的場次改變了 ridge 解，pressure 屬性最多差 18 分。
- 這不是錯誤，但代表**舊季的 pressure 與 2021-22 參考卡的 pressure 不是同一個樣本規則**。舊季不可能重現「v3 參考那組場次」，因為那組是 2021-22 特有的。

**失敗原因拆解**（`equiv/stints-*/preparation.json` 的 `failures`）：

| 來源 | 有效場 | 結構錯誤（時鐘倒退、節首先發不明等） | 只因分鐘不符 |
|---|---|---|---|
| 2021-22 參考（v3 derived） | 1,065 | 59 | 106（其中 105 場 ≤3 秒） |
| 本轉換 liveData | 1,167 | 59（與參考相同） | 4 |
| 本轉換 v3+v2 | 1,221 | 9 | 0 |

- 參考檔拿 nba.com box 的小數秒對 1.1 秒容忍。例如 0022100005 有一人差 1.44 秒，整場剔除。
- 舊季只有 PR #5 box（整數秒），這條規則在舊季無法重現。

### 5.5 pressure 樣本規則（2026-10-28 使用者決定：A，同一規則）

- **規則**：Path A 的每一季（2014-15..2021-22）都用同一條鏈產生 four-factors：
  1. `fetch_old_seasons_v5.py` 轉換的 pbp。
  2. `fetch_old_seasons_v5_stints.js` 做陣容重建；它用的分鐘檢查以 PR #5 box 為準（1.1 秒容忍，演算法未改）。
  3. `fetch_old_seasons_v5_ff.py`。
- **2021-22 另建 Path A 版**，放在 `v5/pathA/ff-2021-22/`。v3 的 `four-factors-2021-22.csv` 不動，D1–D3 照舊用 v3 版。
  - 路徑：liveData（`cdnnba_2021` `0c116aff…`），和 2020-21 同一路徑。
  - 用目前的轉換器（`58953de1…`）重新轉換到 `D:\Projects\temp\nba-old-seasons\pa2122\`。轉出的 `manifest.json` SHA 是 `2a8fc560…`。
  - stints-ff：`ff-2021-22/stints-ff/stints.jsonl`，SHA `f4ae7b41…`，1,167 場有效、35,406 段。與等價驗證時的 `equiv/stints-cdn` 逐位元相同。
  - four-factors：`ff-2021-22/four-factors.csv`，SHA `b3e5cd79107ea3c2b3ce407bb84f4c31e56b5a77dbae35beec0cbadc9a71ddcc`，605 人、67,228 stintSides。連跑兩次相同，也與 `equiv/ff-cdn` 相同。
- **影響**：
  - Path A 的 2021-22 卡（Y6 答案卡，以及 W 先驗若在 Path A 內用到）的 pressure 改用這份。
  - 與 v3 卡相比，pressure 的中位差 1.74 分、最大差 17.5 分，394／605 人差超過 1 分。
  - 其餘 14 項不變（§5.2 的 liveData 欄）。
- **日後建卡時**：2021-22 的 `ff_path` 要明確指向 `v5/pathA/ff-2021-22/four-factors.csv`。`d0_gate.py` 的自動偵測仍然先找 v3 檔，只用來判斷存不存在，不決定卡片用哪份。

### 5.4 rimShare

- 每條路徑（含 2021-22 原檔）的 rimShare 都是常數（r = None）。
- 原因：pbp 沒有 area 欄位，areaCoverage 是 0。
- 卡片管線的 15 項不用 rimShare，不影響建卡。

## 6. 缺少與風險

1. **pressure 依賴有效場次樣本**：見 5.3。已依使用者決定採同一規則（§5.5），2021-22 用 Path A 版 four-factors。剩下的不一致是：同一條鏈下，v3+v2 路徑（2014-15..2019-20）比 liveData 路徑（2020-21、2021-22）多保留約 50 場「時鐘倒退」的比賽，因為 v3 來源已修正時鐘。
2. **2014-15 bio 缺**：沒有合格來源，所以 2014-15 不能進鏈，Y0 失效。
3. **v3+v2 路徑的投籃分區**：與參考檔最多差 2 球，mid／short 屬性最多差 1.95。這是來源修訂，不修。
4. **PLUS_MINUS**：與 nba.com box 差最多 14，卡片不用。
5. **§5.6 降級照舊**：
   - tracking：onBall／help 用常數 70。
   - dependence：creation 用 x0，received 用 0.5。
   - shot-origin：short 用 shortBase。
   - 和 2021-22 先例相同。
6. **2019-20 三場只用 v3 轉**（0021901316–18）：5 人次的姓名對不到 ID。這幾人次在該場的分區計數會少算。
7. **2020-21 stints-ff 失敗 35 場**：多於其他季的 7–15 場，有效場次 1,045（PR #5 是 1,066）。只影響 four-factors 的樣本，不影響 RAPM 用的 `stints.jsonl`。

## 7. 決定性（重跑相同）

- 2019-20 重跑整條轉換到 `D:\Projects\temp\nba-old-seasons\det`：
  - 1,059 個 pbp 檔逐位元相同。
  - `league.json` 正規化路徑字串後相同。
  - `manifest.json` 用 `detcmp3.py` 做 JSON 路徑正規化後相同。
- four-factors 2019-20 重跑，SHA 相同（`0ce83ea4…`）。
- D0 連跑兩次，JSON SHA 相同（`f77070ea…`）。

## 8. 對 Y0–Y6 的影響

| 起點 | 第一輪 | 本輪 |
|---|---|---|
| Y0 | 失效 | 失效（2014-15 bio 缺） |
| Y1、Y2 | 失效 | 卡片可建；缺 RAPM 窗。暖身，依 §5.2 不判定 |
| **Y3** | 失效 | **可判定** |
| Y4 | 失效 | 可建；暖身（COVID），不判定 |
| **Y5** | 失效 | **可判定** |
| **Y6** | 失效 | **可判定** |
| V1／V2 | 從缺 | 可判定 |

D0 字面上仍不通過（`d0Pass=false`，2014-15 不能進鏈）。要不要進 RAPM 窗、卡片、回測，由使用者決定。
