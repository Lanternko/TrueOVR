# F-126 資料可得性檢查（2026-11-01）

在內建瀏覽器的 nba.com 頁面裡直接 fetch 測的（Origin＝nba.com）。Python 直接抓要帶哪些 header、會不會被擋，還沒試。

## Shot Difficulty（xFG%）

| 端點 | 粒度 | 季數 | 備註 |
|---|---|---|---|
| `stats.nba.com/stats/shotqualityvideologs?GameID=…&PlayerID=…` | 單場單人，逐球 | 2025-26、2026-27（2025-26 季初／季中／季末三場抽查都有；2024-25 回 500） | 欄位：`shots`、`avgShotQuality`(xFG)、`fgPct`、`fgPctAboveExpected`、`avgMadeShotQuality`、`avgMissShotQuality`、`avgDefenderBallDistance`；`shotList[]` 每球 `eventNum`、`actionType`、`shotType`、`success`、`period`、`gameClock`、`shotQuality`、`locX/locY` |
| `stats.nba.com/stats/shotqualityleaders?LeagueID=00&Season=…&SeasonType=Regular+Season&TeamID=0` | 整季、達門檻球員 | 2025-26（125 人、FGA≥491）、2026-27（133 人） | GameID／DateFrom／LastNGames／Month 參數都無效（回傳不變）。另有 `AVGDEFENDERPRESSURESCORE`、`AVGDEFENSIVEHANDHEIGHT`、`AVGSHOOTERSPEED`、`FG3PCTABOVEEXPECTED` 等 |

要算全部球員只能逐場逐人抓 videologs：2025-26 約 1230 場 × 每場約 20 人 ≈ 2.5 萬次請求；還沒找到「單場全隊」的端點。

## Gravity

| 端點 | 粒度 | 季數 |
|---|---|---|
| `stats.nba.com/stats/gravityleaders?LeagueID=00&Season=…&SeasonType=Regular+Season` | 整季 | 2025-26（234 人、GP≥55）、2026-27（288 人） |

欄位：`FRAMES`、`AVGGRAVITYSCORE`，以及有球／無球 × 外線／禁區四種的幀數與分數。帶 GameID 參數，回傳不變，沒有單場資料。

## 觸發例子（使用者看過，不能當盲測，L-026）

2026-10-31 OKC @ HOU（0022600153），SGA：20 次出手，FG 50.0%、xFG 43.5%，高於預期 +6.5 pp，平均防守者距離 31.9 英寸。SGA 2025-26 整季 xFG 47.7%（FG 55.3%、+7.6）；2026-27 到 10/31 xFG 44.2%（128 FGA，+2.7）。Gravity 兩季都排第三。
