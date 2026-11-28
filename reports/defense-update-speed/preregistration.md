# 預註冊：賽中防守更新速度回測（defense-update-speed）

凍結日 2026-11-02，跑任何模擬與比較前 commit；之後不得改（L-026）。spec：`spec.md`。角色 card。
雜湊：本檔 sha256 寫在 `preregistration.sha256`；程式與輸入的 sha256 寫在 `work/out/manifest.json`（本檔 commit 時一起 commit）。

## 1. 問題
開季前段讓老將 onBall／help 窗口裡的本季權重變大，對球隊之後的防守（剩餘賽季 DRtg）預測會不會更準？

## 2. 資料（第 0 步已確認可取得，見 report.md §0）
- 季：2024-25 主檢定（樣本外：這個問題與倍數是看 2026-27 才提出的，模型沒有用 2024-25 DRtg 擬合過）；2025-26 同向確認（部分污染：引擎底屬性、onBall 尺度與 z 凍結值都來自 2025-26）。
- 快照：每隊 leaguegamelog 官方場序的第 10、20 場，日期 D。
- 本季截至 D 的追蹤表：rim／three／hustle／advanced 用 stats.nba.com `DateTo=D`；matchups 的季累計端點不吃 DateTo，改用逐場 `boxscorematchupsv3` 累加 D 當天（含）以前的場次。
  逐場列的攻守方向用機械規則決定：全季逐場累加後，配對層 PARTIAL_POSS 與 `leagueseasonmatchups` 季總計絕對差總和較小的方向（不看任何結果）。另記錄兩者總量差，總量差 > 2% 視為重建失敗，停下回報。
- 窗口往年四季：2024-25 用 2020-21～2023-24；2025-26 用 2021-22～2024-25。2022-23 以後用 `reports/defense-tenth/step4-t2/raw` 現有季總計，2020-21、2021-22 新抓（同端點同參數）。
- c＝D 當天（含）以前聯盟已賽場數／1230·82（同 `run_c4_live_rookie.vet_defense`）。

## 3. 臂（常數寫死）
只改老將 onBall／help 窗口裡本季的權重 `ww[本季]`（`rookie_defense.window_weights` 的本季項）乘 k，其餘逐行同 `rookie_defense.veteran`（含每人 season_units 正規化）。
`work/build_arms.py --check` 已驗證 k=1 時與現行 `RD.veteran` 在 2026-11-01（92 場）918 人逐人差 0。
- A0：k=1（現行）
- A1：k=2
- A2：k=4

新秀（往年沒有資料）在三臂下相同（只用本季，k 同時放大分子與正規化除數）。
防守加成（DIQ／defenseBonus）：引擎 sim 0.1.4 的球員 profile 沒有 defenseBonus 欄（只進 OVR，不進模擬），所以對主目標（模擬 DRtg）沒有作用，不重擬合；這是對 spec「DIQ 跟著重算」的偏離，理由是它不影響本檢定的任何數字。

## 4. 主目標與主檢定 H1
- 模型 DRtg：E-208 組隊方式。屬性底＝E-208 2024-25 用 variant Q、2025-26 用 variant P；onBall／help 加上 `窗口值_k − card 0.2.7b 先驗卡值`（同 `team_ratings_daily.engine_inputs` 的 live − 卡片做法；沒有窗口值的人差值 0，引擎沒有 profile 的人用平均 profile、不加差值），clamp 0–120。
  輪替＝E-208 (c)：該隊 D 當天（含）以前最多 10 場 box 分鐘平均（`minutes_rules.rule_c`）。
  對 E-208 聯盟平均隊打 200 場，s&1 換主客，seed＝seedOf(s, 700＋隊序＋30·N序)，同一隊同一快照三臂共用 seed。DRtg＝100·失分／對手回合。
- 實際：D 之後該隊剩餘賽季的 DRtg（leaguegamelog 全部場次；回合＝兩隊 FGA−OREB+TOV+0.44FTA 平均）。
- 兩邊都扣同季同 N 的 30 隊平均（模型扣同臂的 30 隊平均）。
- MAE_k＝60 個 (隊, N) 的 |模型相對值 − 實際相對值| 平均。ΔMAE_k＝MAE_k − MAE_A0。
- Bootstrap：以隊重抽（同隊兩個快照一起），5000 次，numpy default_rng(20261102)；聯盟平均不重算。
- **多重比較**：兩臂各一次比較，Bonferroni：單臂判定用 95% CI（＝90% 雙尾的 α 0.10 分給兩臂）。另報 90% CI。
- **H1（臂 k）通過**＝2024-25 ΔMAE_k 的 95% CI 上界 < 0，且 2025-26 ΔMAE_k 點估計 < 0。任一臂通過即 H1 通過；兩臂都過時以 2024-25 ΔMAE 點估計較小者為建議臂。
- 不通過時不改倍數再試（L-026）。

## 5. 次要（不當閘門）
- 第 10、20 場分開的 ΔMAE（點估計＋90% CI）。
- 屬性層：每季每 N 取快照日的中位數 D；老將（往年四季有任一季資料）且 D 之後出場 ≥ 500 分鐘，
  快照時的窗口 onBall／help 對「D 之後剩餘賽季單季表（DateFrom=D+1 ＋ D 之後逐場 matchups）用同一公式算出的值」的 MAE，各臂與 Δ（以球員重抽 5000 次，90% CI）。
- 模型相對值與實際相對值的相關係數。

## 6. 描述（不當證據）
2026-27 截至 2026-11-01（92 場，c≈6.13）：各臂 76 人主力 onBall／help；30 隊用每日球隊評分同一套輸入（live 2026-11-01 ranking.csv − 先驗卡差值、team-ratings.json (c) 輪替），
各臂只把 onBall／help 差值加上 (窗口值_k − 窗口值_A0)，`scripts/team_ratings_sim.mjs` 200 seed，報 76 人相對聯盟平均的 DRtg 與名次。

## 7. 運算與 G2
模擬在 5090（18 workers）；記錄主機、目錄、commit、輸入 sha256。引擎 sim 0.1.4（E-208 lib），先驗卡 card 0.2.7b（`prior-2025-26-card027b.json`），onBall 尺度與 z 凍結於 2025-26（`rookie_defense`）。
不改 `src/`、正式卡、凍結檔、E-208 既有結果、線上每日管線。採用與否由使用者決定（G5）。
