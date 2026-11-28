# E-174 第 0 階段：資料盤點

- 日期：2026-11-01，role-card。只盤點，不跑任何評估指標（薪水／2K／RAPM／EPM／eval_v2），不比較卡片好壞。
- 預註冊 `preregistration.md` 的 sha256 開頭 `0a9dc462c8173909…` 與 `preregistration.sha256` 一致，沒動。
- 約定：缺格在該季快照用聯盟平均並標記，不用現值或別季補（§2）。「當季值」＝同一人在不同季的值不同，且 2025-26 與正式卡逐值相同（`reports/ovr-inseason-2026-27/v4/cards/build-report.json` 的 2025-26 `sameSource: true`）。
- 抽查：`v4/cards/<季>.csv` 裡 Curry 的 long 跨季是 75.6／93.0／86.9／82.4／80.0，Jokić 的 drive 是 90.6／92.6／85.4／88.8／93.8（2021-22…2025-26），不是同一個現值。

## 1. 屬性 × 季 資料表

圖例：O＝可得且為當季值；X＝缺；△＝可得但有註記。

| 屬性 | 2021-22 | 2022-23 | 2023-24 | 2024-25 | 2025-26 | 來源與粒度 |
|---|---|---|---|---|---|---|
| long／mid／ft | O | O | O | O | O | box 逐場（`data/defense-seventh/<s>/player-games.json`；2025-26 在 `data/season-source/player-games.json`），投籃區域來自 pbp（2025-26 靠正式卡 `prior-2025-26.json`）。卡片存季總量百分位 |
| short | △ | O | O | O | O | 同上，加 E2 折扣要 `reports/ovr-v55-finisher-fix-2025-26/shot-origin.json`，該檔只有 2022-23..2025-26，**2021-22 沒有**（2021-22 卡怎麼處理未追查） |
| tovSkill | O | O | O | O | △ | 需 pbp 回合數。pbp 在 `data/defense-seventh/2021-22..2024-25/pbp`；**2025-26 repo 內找不到 pbp**，只有正式卡現成值 |
| pass／rebound | O | O | O | O | O | box 逐場＋team-games（AST%、REB%）；2025-26 用 `data/benchmark-source/advanced.json` 與正式卡。卡片取季總量 |
| creation | O | O | O | O | O | (1−sourceReceived)·FGA/MIN·36；sourceReceived 在 `reports/player-impact-v30/dependence-audit.json`（逐季覆蓋未核對） |
| foulDraw | O | O | O | O | O | FTA、FGA、MIN（box 可加總）。`season_attrs_v4` 與 `v4/cards/*.csv` 沒有這欄；公式在 `live/run_c4_live.py:617 foul_draw_y`，凍結常數是 2025-26 池的尺度。**現成程式沒有逐季重算，要新寫** |
| drive | O | O | O | O | O | FTA/FGA（`season_attrs_v4.raw_values`），box 逐場；賽中解凍版（`live/pres_drive.py`）另加未助攻得分權重，需 pbp，2022-23..2025-26 |
| onBall／help | X | O | O | O | O | `reports/defense-seventh/<s>/calendar-55/v3-league.json`，季總量。2021-22 沒有追蹤資料，`v4/cards/2021-22.csv` 這兩欄全是常數 70.0 |
| pressure | X | O | O | O | O | 正式卡路徑＝E-071 force→E-123 池百分位，原料 `reports/defense-tenth/step4-t2/raw/<s>/0-hustle.json` 等，季總量，2022-23..2025-26。**`v4/cards/<s>.csv` 的 pressure 是舊四因子版，不是 0.2.9a 的定義，不能直接用** |
| presDisplay | X | O | O | O | O | 同 pressure，只供顯示，不進回歸；`v4/cards` 沒有此欄 |
| foulDisc | △ | △ | △ | △ | △ | 只供顯示，不進回歸；逐季來源未盤點 |
| stamina（MPG） | O | O | O | O | O | box MIN/GP。不進卡，只給 Y0 用人層 |
| physique、heightInches | O | O | O | O | O | `bio.json`（2025-26 用 `data/benchmark-source/bio.json`）。每季快照，身高幾乎不變；physique 不進回歸 |
| 防守加成（E-104 TL） | X | O | O | O | O | stints 逐場：`reports/defense-seventh/{2022-23,2023-24,2024-25}/stints/stints.jsonl`，2025-26 在 `reports/defense-b1/stints.jsonl`；2021-22 沒有 stints。`live/defense_bonus.py` PAST＝2022-23..2025-26 |
| T6（DARKO＋BPM） | X | O | O | O | O | `data/external-impact/{darko,bpm}/…_<s>.csv`，球員×季總量；2021-22 的 DARKO、BPM、自製 EPM 都沒有 |
| eval-v2 薪水 | △ | O | O | O | O | 合約頁（E-142 phase0）。不跑 |
| eval-v2 2K | X | O | O | O | O | `data/external-impact/2k/2k-merged-e142.csv`，季固定值，有倖存者偏差。不跑 |
| eval-v2 下季 RAPM | X | O | O | O | X | `reports/card-0.2.7+E126-tank-next-season/rapm_season.py` 路徑；「下季」＝s+1，2025-26 的下季是未完賽的 2026-27，不算。不跑 |
| eval-v2 下季 EPM | X | O | O | O | X | `data/external-impact/epm_self/epm_<s>.csv`。同上。不跑 |

薪水、2K、RAPM、EPM 四列是依 E-142 phase0 的紀錄與檔案存在與否填的，沒有打開內容算覆蓋率（避免碰評估）。

- 2018-19..2020-21：box、pbp、stints、DARKO、BPM、自製 EPM 都有，但沒有追蹤資料（E-142 phase0 GAP-METHOD），onBall、help、pressure、presDisplay 全缺，建不了完整卡。
- 2026-27：約 80 場，無 T6 與下季答案，不進回測。

粒度：逐場可得的是 box、stints、pbp；只有季總量的是追蹤類（onBall／help 的 v3、pressure 的 hustle、matchups、rim、three）、T6、2K、bio。過去季只用季總量×該季平均 u（design §2）。

## 2. 每個屬性的重算路徑

| 屬性 | 程式與位置 | 原始檔 | 可重跑任意季？ | 指令 |
|---|---|---|---|---|
| long、mid、short、ft、drive、tovSkill、pass、rebound、creation、stamina、physique | `reports/ovr-inseason-2026-27/v4/tools/season_attrs_v4.py`：`season_paths`:35、`load_season`:129、`aggregate`:190、`raw_values`:217、`build_mapping`:288、`raw_with_box`:309、`compute_attrs`:316 | box、bio、pbp、team-games、v3、dependence-audit、shot-origin、`four-factors-2022-25.csv` | 2021-22..2024-25 可（`SEASONS` 常數只列 3 季，但 `load_season` 接受任何有 `data/defense-seventh/<s>/` 的季）。**2025-26 不行**（沒有該目錄與 pbp），只能用正式卡 `prior-2025-26.json` 現成值 | 見 2.1 |
| onBall、help | `season_attrs_v4.compute_attrs` 讀 v3-league；賽中版 `live/rookie_defense.py`（`window_weights`、`veteran`） | `reports/defense-seventh/<s>/calendar-55/v3-league.json` | 2022-23..2025-26 可；2021-22 沒檔，常數 70.0 | 同上 |
| pressure、presDisplay、drive（解凍版） | `live/pres_drive.py`（`--check` 對先驗卡）；原料 `build_force.season_raw` | `reports/defense-tenth/step4-t2/raw/<s>/` | 2022-23..2025-26 可 | `python -I -X utf8 reports/ovr-inseason-2026-27/live/pres_drive.py --check`（本階段沒跑） |
| foulDraw | `live/run_c4_live.py:617 foul_draw_y` 只有「累計→分數」，沒有逐季重算程式 | box（FTA、FGA、MIN） | 資料齊，程式要新寫 | — |
| 防守加成 | `live/defense_bonus.py`（E-104 `e104fit.py`） | stints | 2022-23..2025-26 可 | `python -I reports/ovr-inseason-2026-27/live/defense_bonus.py --check`（本階段沒跑，較重） |
| 三部件卡＋Y0 | `reports/card-0.2.9+E164-no-stamina/e164_build.py`（經 E153／E142 `build_card_t`） | `phase1-work/cands/{T1,T4,T5,T6}-<s>.pkl` | 這四季有候選檔；2021-22 沒有 T6 | 第 1 階段 |

### 2.1 輕量試跑（2023-24，只算屬性）

- 做法（`python -I`，無子程序）：載入 `season_attrs_v4` → `load_season('2023-24')` → `aggregate` → `raw_with_box` → `build_mapping` → `compute_attrs`。
- 結果：572 人、17.4 秒。與 `v4/cards/2023-24.csv` 逐人比：long、mid、short、ft、drive、tovSkill、creation、stamina、physique、onBall、help 最大差 0.0000（完全重現）。pass 最大差 24.4、rebound 17.0、pressure 43.3：這三欄卡片走另一條路徑，第 1 階段要沿用 `build_prior_v4.py` 與 `pres_drive.py`，不能用 `compute_attrs` 的預設輸出。

## 3. 缺格清單與影響人數

人數取自 `v4/cards/<s>.csv`（有卡的人）及其中 MIN≥500 者。

| 缺格 | 季 | 影響人數（有卡／MIN≥500） | 備註 |
|---|---|---|---|
| onBall、help 全缺（常數 70） | 2021-22 | 605／375 | 無追蹤資料 |
| onBall、help 該人不在 v3（預設 70.0） | 2022-23 | 79／23 | 預設不是聯盟平均的證據，第 1 階段要標記 |
| 同上 | 2023-24 | 49／5 | |
| 同上 | 2024-25 | 54／2 | |
| 同上 | 2025-26 | 5／0 | |
| pressure、presDisplay、防守加成 | 2021-22 | 全員 605／375 | 無追蹤檔、無 stints |
| short 的 E2 折扣 | 2021-22 | 全員（無 shot-origin） | 其他季有 |
| tovSkill 等需 pbp 的重算 | 2025-26 | 不是缺值，是不能由原始檔重現 | 正式卡現成值是當季值 |
| T6 | 2021-22 | 全員 | 該季不能當擬合季 |
| T6 個別缺人 | 2022-23..2025-26 | 少數（E-142 phase0 記載 DARKO、BPM 覆蓋都在 98% 以上） | 缺的人當季不進擬合 |
| 窗口不足四季 | 2022-23 起 | 2022-23 快照只有 1 季、2023-24 有 2 季、2024-25 有 3 季、2025-26 才滿 4 季 | 照 R-076 用實際季數正規化 |

## 4. 來源檔 sha256（G2）

筆數：box 與 pbp 每季 1230 場（2024-25 的 pbp 1229 場）。pbp 目錄雜湊＝逐檔相對路徑加逐檔 sha256 串接後再 sha256。

### 4.1 檔案

| 檔 | 位元組 | sha256 |
|---|---|---|
| `data/defense-seventh/2021-22/player-games.json` | 4405355 | `9b7eebe1f8da83de048c57586ff6b6d55ab0bbc38d7fa9e4975ace981a1f4921` |
| `data/defense-seventh/2021-22/bio.json` | 90427 | `f313f8c6ffa41777ea915cd6891565e9204b1404a27a79d79946ad3a323c6c52` |
| `data/defense-seventh/2021-22/team-games.json` | 390136 | `d92b3415d3ad0dd882d4b55135d01988a717ccb207aafe7521591896ca0fc945` |
| `data/defense-seventh/2022-23/player-games.json` | 4381258 | `f41f7f4b105af8d280381f0c3315219ee074b2329e5d9b5f979b6fc72dbd7f56` |
| `data/defense-seventh/2022-23/bio.json` | 80764 | `2b493e0aedcdfc610f9fe570ce0ca975a709753ad63e83fdddc31444d402927f` |
| `data/defense-seventh/2022-23/team-games.json` | 390421 | `732bbf1991c0ce13e3b70db5f2d7769dd66d5d05d4fabef6306963cff066e020` |
| `data/defense-seventh/2023-24/player-games.json` | 4471089 | `a33074c9c9b1f59e15f160464292b3ab9c791065ae542c20f2ed64f3e170afd5` |
| `data/defense-seventh/2023-24/bio.json` | 85622 | `1cb8eb0431bea1aaa43f1209571e39e9b2505a8c85cb14b356fddc54b9dfa1a6` |
| `data/defense-seventh/2023-24/team-games.json` | 390487 | `befe8941b51e8c2f440df88e2aea79aab63826d389ec258d5fe8e209967586c5` |
| `data/defense-seventh/2024-25/player-games.json` | 4456947 | `4c3f33c67ffaa1cf88ea01a7acaeef70af088e22f6020c3a02409989f6ad4ffa` |
| `data/defense-seventh/2024-25/bio.json` | 85325 | `945c9d37fb0409b0d023ef7c5514cc492a1805f14fc10a7b0f707fd5ae9881d3` |
| `data/defense-seventh/2024-25/team-games.json` | 391044 | `b4da45c024c655c64db220568813922ca1e6d37fbc23650ad7ed43f352b1e470` |
| `data/season-source/player-games.json` | 4516000 | `11fc5866b2f61b31e27659e14e4071924b5873ef0d2a4118a585c1a54be04357` |
| `data/season-source/team-games.json` | 391423 | `d5cb1a6dbd26a0ed71b24e7e18fcbc862afdf6d8bd8ea3814c5dadbf1989fb8a` |
| `data/benchmark-source/bio.json` | 87375 | `d319d00ed383c8a30793907fd0edd56fd26e8cdb19a74bbb0c2667790644196e` |
| `data/benchmark-source/advanced.json` | 222037 | `e8f021aaa7736d5c4e2a5d6d7ba978e7ed99319c4914447cea615d59802cb8a4` |
| `data/benchmark-source/base.json` | 173892 | `3e4ea6fa211c50d0686b8a45f15f1351dd9cfec2478487d0ec758b38802dff08` |
| `data/benchmark-source/shots.json` | 79530 | `860134b915ef78473a7aa548b59efde690cbc775eb001c172b5ea2853bb9ad40` |
| `data/benchmark-source/defense-long.json` | 50892 | `f8eab9476081dd17dc6aa316570a11ec3c5ce094e56618251510b5533641ba80` |
| `data/benchmark-source/defense-rim.json` | 51021 | `a1f515e58a406835406ed2671fa41506e85a3ccf944485b9c0fff2073d8f4820` |
| `data/season-source-2024-25/player-games.json` | 2446928 | `3869de6758ae4c454c2bf076357a99fbc5b56cbe756056b6d093b3c516d52aa5` |
| `reports/ovr-inseason-2026-27/data/four-factors-2022-25.csv` | 102865 | `a30f0b23953bc73ebfb3936a58095b10a157eab7ba0362ea4341a1777580bcf7` |
| `reports/player-impact-v30/dependence-audit.json` | 1002377 | `395d6d186079849ee242f6f10514f9d5180396a937f9436f3488a1249819ed17` |
| `reports/ovr-v55-finisher-fix-2025-26/shot-origin.json` | 530568 | `7844f1fd6acf87bd6bc811760a09ae459af22d850ca86bfd07ba0d97c50b023e` |
| `reports/defense-b1/stints.jsonl` | 38500370 | `5eff6aa81f37d0f3baef97be2fdc7346a05ffce5ccfa1f6e4456be229a296179` |
| `reports/defense-seventh/2022-23/stints/stints.jsonl` | 32054384 | `5936e16bbfcce88da4743cb72b828be2d602bdb67e470e549c68bd2d7c3eaec6` |
| `reports/defense-seventh/2023-24/stints/stints.jsonl` | 31041465 | `a83b1c42ba735810f2fd8dccd8355d2f41e4fd164389ee82fb4318b4a3d0adb6` |
| `reports/defense-seventh/2024-25/stints/stints.jsonl` | 32391568 | `8790976ac74edf2054470427c50984d35d8c8ab0abf72fd92b5105489cf74ac0` |
| `reports/card-0.2.5+E104-defense-pergame-decay/def-L-primary.csv` | 65792 | `c43396ea951fb7b12060c667e92b7acf26569209f2bc595c642e7a1d5f6aecc9` |
| `reports/defense-seventh/2022-23/calendar-55/v3-league.json` | 1004997 | `ab3f2679c2a9bc78c221e080d37d97b0f5f31ebca4dd06a2aa3a7995f9343c38` |
| `reports/defense-tenth/step4-t2/raw/2022-23/0-advanced.json` | 205592 | `5cce624bdcba6e4190c3520986006b5d8a87a0e1c11bdc2f268a7fb3815d3da2` |
| `reports/defense-tenth/step4-t2/raw/2022-23/0-hustle.json` | 66514 | `6f2077f4abf7348c37bcd6e89061cd258f9dc051af4d5666349f6eb56ff9a651` |
| `reports/defense-tenth/step4-t2/raw/2022-23/0-matchups.json` | 15359562 | `3132e001c1bcb2b8a19ff9c2948d08fab6423bb8f23462e73ddd43b82cdc6f30` |
| `reports/defense-tenth/step4-t2/raw/2022-23/0-rim.json` | 47614 | `493da838f618eb6cb3dc20d6bdf599b5b0c0abe2c625a5310b20af74db57f201` |
| `reports/defense-tenth/step4-t2/raw/2022-23/0-three.json` | 47383 | `ccaa5b707199f462e78ef4bd3a50aff48eae2cd514c4cc983dc7fe2c98d423aa` |
| `reports/defense-seventh/2023-24/calendar-55/v3-league.json` | 1051035 | `272f68ad60570c3fe38287b020d45e2b51080728e015d85b7f8f9bb3a8e26bec` |
| `reports/defense-tenth/step4-t2/raw/2023-24/0-advanced.json` | 217620 | `2a66adc5f1eccac6b23f60061e75115adfef8152c7b884dba7a940c4a372db23` |
| `reports/defense-tenth/step4-t2/raw/2023-24/0-hustle.json` | 70326 | `bf6e276af8dd0f153f1beb231f40fdd3a24ed4dba6702a49ba256aa21053bc35` |
| `reports/defense-tenth/step4-t2/raw/2023-24/0-matchups.json` | 15661985 | `a88e2182aff47c33681216da1d91da9830dcacf9bbe5707b17c708e135fb33f7` |
| `reports/defense-tenth/step4-t2/raw/2023-24/0-rim.json` | 50355 | `0bafefec8308a996943dc3c9ab5fb59472303d045e26b5c41ee91797dc285f1f` |
| `reports/defense-tenth/step4-t2/raw/2023-24/0-three.json` | 50063 | `a6b7491a6887cbc5a17d20b9254e9b05a93036957f15d835a327409df2a2abc5` |
| `reports/defense-seventh/2024-25/calendar-55/v3-league.json` | 1051832 | `78a50efecdfe343284d3983ea749afea54c7a0acddb3ce8ae1b7c117e6f4e37e` |
| `reports/defense-tenth/step4-t2/raw/2024-25/0-advanced.json` | 217295 | `6e97d8807369be5668940b190a901a24439b60b82fe6f393a953c33c8e523508` |
| `reports/defense-tenth/step4-t2/raw/2024-25/0-hustle.json` | 70193 | `e88b8dee6c689aebe1c01c0153a08c620dcefee8ca1f65eba2cd2679a07ad2ad` |
| `reports/defense-tenth/step4-t2/raw/2024-25/0-matchups.json` | 15823723 | `7f948fcc1cb5e4726d6f646e8789919a6a69917a999377e58440f416524486ea` |
| `reports/defense-tenth/step4-t2/raw/2024-25/0-rim.json` | 49790 | `f77cf8fa22690cffae5b3a41f8859bc265518d459d2f420fab596928e6198457` |
| `reports/defense-tenth/step4-t2/raw/2024-25/0-three.json` | 50355 | `d20747724685a885155fb354943f33f53942d3adb9aecbd357e4a0cb51c0a26a` |
| `reports/defense-seventh/2025-26/calendar-55/v3-league.json` | 1147968 | `5e5ab055e94458f4eeced9c762fb379b2ed7f035b3c5c40699cc87c18048b9f2` |
| `reports/defense-tenth/step4-t2/raw/2025-26/0-advanced.json` | 222409 | `182975df662b91cc08fc70f9978952a359604719b13d1a60776595db7e604ad5` |
| `reports/defense-tenth/step4-t2/raw/2025-26/0-hustle.json` | 71283 | `a2103c77db873ae61ca228350f4386571f10a88dd20eea32bbe4f0f1ce19b2da` |
| `reports/defense-tenth/step4-t2/raw/2025-26/0-matchups.json` | 16519085 | `198dba993daf6ea8905fc60e191ad77b8f8f0897dec6d99cd8a131279f5b9e20` |
| `reports/defense-tenth/step4-t2/raw/2025-26/0-rim.json` | 51379 | `479c58ed5fcfdba01c1f2119d208052fc27c1470affb9271fba1162ac81ce2e2` |
| `reports/defense-tenth/step4-t2/raw/2025-26/0-three.json` | 51255 | `44ce979729db7f13e6c60899f862760a91c3e809c13ebd5b9b07b911bb4f031c` |
| `data/external-impact/2k/2k-merged-e142.csv` | 76424 | `cb40f9a0c14e76e9d0ad10359015f882bcfe1c74b0e8b1021f3ce5b9287cdab4` |
| `reports/ovr-inseason-2026-27/v4/cards/2021-22.csv` | 115922 | `ee67beedfdac13a51e5bd9b2aa7adf45648c2dc3966304b108ad715e035466ff` |
| `reports/ovr-inseason-2026-27/v4/cards/2022-23.csv` | 107770 | `2fed78d1631ba81f7e6a88c634d2bc817b9efbd5eb8466e7c9620ef0b3f360c4` |
| `reports/ovr-inseason-2026-27/v4/cards/2023-24.csv` | 115309 | `73050d7679f4350e10ec27b17ac8db58d821531ffd8bf07913dfc0bb88a9515b` |
| `reports/ovr-inseason-2026-27/v4/cards/2024-25.csv` | 115109 | `b71a8fd0911eb6c4c09206bfab95fbf01ce885f3a9ce77c0ea4a8f8ae5f99dec` |
| `reports/ovr-inseason-2026-27/v4/cards/2025-26.csv` | 96095 | `8e89c5f4b515043a7a8ebb63a3ac7b7f52dc41bdab7cf5caa394d88a089f11c8` |

### 4.2 pbp 目錄雜湊

| 目錄 | 檔數 | sha256 |
|---|---|---|
| `data/defense-seventh/2021-22/pbp` | 1230 | `cd815b6ba8509debb989a58639d202df3a9f2c6f4af2d7f36ab32d7d1089b9dd` |
| `data/defense-seventh/2022-23/pbp` | 1230 | `13b43e929940ab4dbfaf8c5b94954040a6fd4dad56b457157bc9d5f84f09aa49` |
| `data/defense-seventh/2023-24/pbp` | 1230 | `c59622e430374e948622f6992bb8a8f61b35a2f0450d6f1be92546226077f2d8` |
| `data/defense-seventh/2024-25/pbp` | 1229 | `e1d90627edcb8c1c648369d2ed6ea331341545a141d8c41894eb93ca55e4f023` |

2025-26 的 pbp 在 repo 內找不到，無 sha。2026-27 不進回測，沒算。

### 4.3 T6 來源（`data/external-impact/`）

| 檔 | sha256 |
|---|---|
| `data/external-impact/darko/darko_2018-19.csv` | `cc5a25725a6db2e9bc4bba84879dee1c840e441cc1f63afcad4fc834324010ec` |
| `data/external-impact/darko/darko_2019-20.csv` | `32ebf11ae5fb7987c6ddc76992a0acf3fbfa1c8452e4aabf39a69926f06f25e4` |
| `data/external-impact/darko/darko_2020-21.csv` | `1975ad42c3ee7b711740c886bd53dd0ec8cc27e41b8b3abd9ab48c87d0e8c9c5` |
| `data/external-impact/darko/darko_2022-23.csv` | `b847be60b8457d8a25b25721fe967f2c3ec27d4d99600122890e1bc59a5b03ed` |
| `data/external-impact/darko/darko_2023-24.csv` | `d0ee094dbb4bc43a7bb8a1593db9ddc770ba61115a34e0ecc32554c0809f2d19` |
| `data/external-impact/darko/darko_2024-25.csv` | `6b4e53d5cdca91e1e992fb27abc8561c6613d2b336b705e6316944844f334992` |
| `data/external-impact/darko/darko_2025-26.csv` | `d144f747fcf145b9338c95937769a0f2097b1e3bcac2994d8fb28cd330fbce64` |
| `data/external-impact/bpm/bpm_2018-19.csv` | `f78da3a814952f69576a1147ef53ed6e00f2aba86d0844c95170bef8721fc40a` |
| `data/external-impact/bpm/bpm_2019-20.csv` | `e83490df71145b99e82de845c20b27b28626b2e8d61bdfe1d1448dc6f3e6e23d` |
| `data/external-impact/bpm/bpm_2020-21.csv` | `dfca0e2b018dfbf5aad5f5afa219e5c553d1141b91052a76657c3f63ff69f9b9` |
| `data/external-impact/bpm/bpm_2022-23.csv` | `b860cf527dc6b266429a50c9fd4a55f1d1c546ecdcbcf276b11a6df00a91f17a` |
| `data/external-impact/bpm/bpm_2023-24.csv` | `04e82fe0407d353fbcc2eea77397503f3dbb58d207eb9c2fe1306357ee31488f` |
| `data/external-impact/bpm/bpm_2024-25.csv` | `e8ee7a3d70d65c407b243e598ddbad547752a46ceb3c0e37a065e132f3079ac7` |
| `data/external-impact/bpm/bpm_2025-26.csv` | `c96c3c8fa391b5d3356763f0d0c89bc9c9e702385459edbac6f3818b7523747b` |
| `data/external-impact/epm_self/epm_2018-19.csv` | `3a6399e3cd39a39bb8f6fbab7641c9315bc7642cda40abb1d24f723f84016341` |
| `data/external-impact/epm_self/epm_2019-20.csv` | `d3c6282e6b3f9e3db49631e388807a7ae2b2e773b901a268e35651c44f8133a9` |
| `data/external-impact/epm_self/epm_2020-21.csv` | `3cf83a5c6bd4c08944480ac048ccfd45a0f94989d71d8b7c4c149b64f13a5870` |
| `data/external-impact/epm_self/epm_2022-23.csv` | `d61b64919ac0b4c8af9731387f833f0bf1b7034c8cf4ac3d2dc14b913d8a0c15` |
| `data/external-impact/epm_self/epm_2023-24.csv` | `24e6bbc5c2ec76c2aa991819cec509bf8a7cf8923a55a7a3e58c6fb36a0e577b` |
| `data/external-impact/epm_self/epm_2024-25.csv` | `68013febf47829c893b8aa7d8f518e518300406f0662794b2be97d9e353b5a4d` |
| `data/external-impact/epm_self/epm_2025-26.csv` | `4e62d7b0eeef1094dd98042c36a84f8c76310a209b897fe94142283070b68528` |

## 5. 最早季建議

- **最早完整季＝2022-23**：所有屬性、防守加成、T6 都齊，是第一個能建完整 card(t) 的快照。
- **2021-22**：只有 box、pbp、bio、team-games；沒有追蹤（onBall、help、pressure、presDisplay）、沒有 stints、沒有 shot-origin、沒有 T6。不能當擬合季。我建議不放進窗口（現有 PAST 四季就是 2022-23..2025-26，加一個缺半數屬性的季會讓同一窗口在不同屬性上季數不同），由 lead 決定。
- **2018-19..2020-21**：不能建卡（GAP-METHOD）。
- 窗口不足四季：測試季 2023-24 的窗口只有 2 季、2024-25 只有 3 季，用實際季數正規化（R-076）。測試季的「四季窗口」實際只有 2–3 季，U 對 S 的差異會比上線後小，報告要列為限制。

## 6. 對第 1 階段的提醒（沒有擋路的問題）

1. foulDraw 沒有逐季重算程式，要新寫（資料齊）。
2. `v4/cards` 的 pressure 不是 0.2.9a 的定義，要走 `pres_drive.py`／E-071 force 逐季算。
3. 2025-26 原始 pbp 不在 repo，需 pbp 的屬性只能用正式卡現成值（已確認為當季值）；不影響測試季，但影響 2025-26 季末 U 卡的可重現性。
4. 擬合季只有兩季：測試 2023-24 用 2022-23＋2025-26，測試 2024-25 用 2022-23＋2023-24（預註冊既定，樣本偏少）。
5. `season_attrs_v4.py` 的 `SEASONS` 常數只列三季，第 1 階段程式要自己傳季別。

## 7. 沒做的事

- 沒跑 `pres_drive.py --check`、`defense_bonus.py --check`（較重）。
- 沒核對 creation 的 sourceReceived 每季覆蓋、foulDisc 逐季來源、2021-22 short 的處理、評估四列的覆蓋率。
- 沒改任何既有檔案，只新增本檔。
