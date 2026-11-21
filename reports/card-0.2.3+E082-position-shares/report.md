# E-082 位置比例（先發秒數）報告

**判定：不通過，不採用（未過：R3）**

| # | 條件 | 結果 | 門檻 | 過？ |
|---|---|---|---|---|
| s0 | 比例最大位置 = 校準目標 position | 檢查 334 人，不符 0 | 不符 <= 3 | 過 |
| c0 | one-hot 重現 | card 0.2.2 P1 三份輸出+card/ranking.csv 資料檔逐位元相同（summary.json 僅 defenseBonusPosMeanD 鍵序不同，json 相等）；E-075 ranking sha 01aab81a 相同；組裝後 sha 933797d8 = card 0.2.3 | 相同 | 過 |
| c1 | npm test | exit 0（57 passed, 0 failed） | exit 0 | 過 |
| c2Q | 舊量尺（pooledNet × MPG） | Δρ -0.0008，90% 區間 [-0.0041, 0.0025]；ρ 候選 AB 0.6122／BA 0.5964，ρ 基準 AB 0.6125／BA 0.5978 | 下界 > -0.02 | 過 |
| c2N | 現況量尺（單季 RAPM net × MPG） | Δρ 0.0010，90% 區間 [-0.0028, 0.0048]；下界 > 0？否；ρ 候選 AB 0.4423／BA 0.4799，ρ 基準 AB 0.4419／BA 0.4783 | 下界 > -0.02 | 過 |
| c3 | evaluate 閘數 | 候選 18/19，card 0.2.3 18/19 | >= 18/19 | 過 |
| R2 | F 中位數 < MIN>=1000 的 PR10 | 52.6 < 52.8 | 同 E-075 | 過 |
| R3 | 隊內 Spearman 中位數 >= card 0.2.3 | 候選 0.7248，card 0.2.3 0.7469（30 隊） | 候選 >= 基準 | 不過 |
| R4 | MIN<100 組 PR90 < 12<=MPG<=22 組中位數 | 58.2 < 62.6 | 嚴格小於 | 過 |

母群：AB 389 人、BA 388 人、聯集 395 人（c2Q 與 c2N 相同；c2N 沒有人因 rapm1 缺資料被剔除）。

R3 不過的差距：候選 0.7248 比基準 0.7469 低 0.0221。依預註冊「任一未過 → 不採用」，不事後調整定義或門檻（L-026）。

## 讀法與「最字面解讀」
- 基準換成 card 0.2.3：c2Q／c2N 的基準 = 重現 card 0.2.3 的 one-hot 跑（off）的半季 g（E-075 的 cand），候選 = 比例跑（on）的半季 g，兩者對同一個 ans 算 ρ；兩跑的母群與 ans 完全相同（腳本 assert）。
- R3 基準取 card 0.2.3 ranking.csv 的隊內 Spearman 中位數（以 e075.py 同算法重算，0.7469 = off 跑的候選值）；R4 的 mpg_card 同樣取 card 0.2.3 ranking.csv 的 mpg。
- c2N 的 MPG：用 E-064 的 mpg-{A,B}.csv（與 c2Q 的 mpgh 同來源），net 用 rapm1-{A,B}.csv，依 playerId 對上；方向 AB（用 A 校準、B 評估）用 rapm1-B 與 mpg-B。rapm1 檔 sha256：A c52b1c3f3ab6b16d19d53a14d94b55347d5ec0e7841ec012c1325d0da6bde520、B 665217f7e8fef15c62aef19c68138a600783452f0c68d65d7059be900bd0b7fa。
- 比例定義全照預註冊：s_ip / Σs；lowConfidence（starts < 5 或無投票）或總秒數 0 → 原標籤 one-hot。s0 檢查 334 人（非 lowConfidence）0 不符；248 人 lowConfidence。
- 「比例最大位置佔不到 60%」群：預註冊寫 71 人（5 次以上先發的 330 人中），本次以 pos-shares.csv 數得 70 人（先決條件：非 lowConfidence、最大比例 < 0.6）。差 1 人，可能是預註冊統計的人群或 starts 門檻口徑略不同；未調整定義。
- 顯示用位置標籤（ranking.csv 的 pos 欄）一律是原硬標籤，比例只進校準；候選與 card 0.2.3 的 pos 欄 0 人不同。
- ranking.csv 組裝規則同 build_card_023.py（rank、ovr、mpg、gRepl 取自 E-075 式輸出，其餘取自 0.2.2 格式 ranking，列序 = 名次序），腳本 assemble.py。

## §5 只報告

### 三人
| 球員 | 位置標籤 | 先發 | 比例 | card 0.2.3 OVR／名次 | 候選 OVR／名次 | ΔOVR |
|---|---|---|---|---|---|---|
| Paolo Banchero | PF | 72 | SF 2.4%、PF 97.6% | 69.9／205 | 69.6／208 | -0.3 |
| Jalen Williams | PF | 33 | SF 40.5%、PF 59.5% | 79.6／80 | 80.4／75 | +0.8 |
| Jalen Johnson | PF | 72 | SF 5.7%、PF 94.3% | 81.9／63 | 81.8／63 | -0.1 |

### 前 20 名（候選；括號為 card 0.2.3 名次）
| 名次 | 球員 | 位置 | OVR | card 0.2.3 名次／OVR |
|---|---|---|---|---|
| 1 | Nikola Jokić | C | 106.2 | 1／106.0 |
| 2 | Shai Gilgeous-Alexander | PG | 103.4 | 2／102.9 |
| 3 | Derrick White | PG | 101.0 | 3／101.0 |
| 4 | Kawhi Leonard | SF | 99.5 | 6／98.5 |
| 5 | Luka Dončić | PG | 99.0 | 5／99.0 |
| 6 | Kevin Durant | SF | 98.5 | 4／99.1 |
| 7 | Giannis Antetokounmpo | PF | 94.7 | 8／94.2 |
| 8 | Joel Embiid | C | 94.0 | 7／94.4 |
| 9 | Lauri Markkanen | PF | 93.4 | 9／93.0 |
| 10 | Stephen Curry | PG | 92.5 | 10／92.3 |
| 11 | Jimmy Butler III | SF | 92.2 | 11／92.0 |
| 12 | Franz Wagner | SF | 91.9 | 12／92.0 |
| 13 | Tyrese Maxey | PG | 90.9 | 13／90.5 |
| 14 | Donovan Mitchell | SG | 90.6 | 19／89.2 |
| 15 | Pascal Siakam | PF | 89.9 | 20／89.1 |
| 16 | LeBron James | SF | 89.7 | 21／89.1 |
| 17 | Anthony Davis | C | 89.4 | 18／89.3 |
| 18 | Rudy Gobert | C | 89.3 | 16／89.3 |
| 19 | Jamal Murray | PG | 89.3 | 15／89.5 |
| 20 | Chet Holmgren | PF | 89.2 | 14／90.3 |

### OVR 變動最大的 20 人
| 球員 | 位置 | card 0.2.3 OVR／名次 | 候選 OVR／名次 | ΔOVR | 比例 |
|---|---|---|---|---|---|
| Patrick Williams | SF | 56.3／345 | 51.9／532 | -4.4 | SF 55%、PF 13%、C 31% |
| Gabe Vincent | PG | 51.3／525 | 55.0／381 | +3.7 | PG 44%、SG 41%、SF 14% |
| Taylor Hendricks | C | 48.5／557 | 51.6／536 | +3.1 | SG 6%、SF 19%、PF 33%、C 42% |
| Jericho Sims | C | 50.5／542 | 53.4／421 | +2.9 | SF 4%、PF 48%、C 49% |
| Jahmai Mashack | PG | 45.5／570 | 48.2／562 | +2.7 | PG 45%、SF 35%、C 20% |
| Jake LaRavia | PF | 62.8／269 | 65.4／248 | +2.6 | SG 25%、SF 19%、PF 55% |
| Deni Avdija | PG | 80.8／69 | 78.2／90 | -2.6 | PG 36%、SG 31%、SF 27%、PF 6% |
| Shaedon Sharpe | SG | 68.9／217 | 66.7／233 | -2.2 | PG 19%、SG 81% |
| Vít Krejčí | SF | 64.6／253 | 62.5／274 | -2.1 | SF 100% |
| Anfernee Simons | PG | 61.6／285 | 63.5／264 | +1.9 | PG 63%、SG 37% |
| Brice Sensabaugh | SG | 51.4／521 | 49.5／555 | -1.9 | PG 20%、SG 55%、SF 12%、PF 13% |
| Sidy Cissoko | SF | 63.5／264 | 61.6／284 | -1.9 | PG 35%、SF 62%、PF 3% |
| Nicolas Batum | PF | 63.7／262 | 65.6／245 | +1.9 | SF 30%、PF 70% |
| Nolan Traore | PG | 37.9／580 | 39.7／579 | +1.8 | PG 92%、SG 8% |
| Taurean Prince | SF | 64.4／256 | 62.6／272 | -1.8 | SF 76%、PF 24% |
| Leaky Black | SF | 68.8／218 | 67.0／227 | -1.8 | SG 13%、SF 51%、PF 36% |
| Jaden McDaniels | SF | 83.3／49 | 81.6／64 | -1.7 | SF 95%、PF 5% |
| Jalen Pickett | SG | 57.4／331 | 59.1／317 | +1.7 | PG 27%、SG 73% |
| DeJon Jarreau | SG | 58.9／316 | 57.2／339 | -1.7 | one-hot（lowConfidence） |
| Devin Booker | SG | 83.3／48 | 84.9／40 | +1.6 | PG 41%、SG 59% |

### 比例最大位置 < 60% 的球員 vs 其他人（平均 |ΔOVR|）
- < 60%：70 人，平均 0.887（最大 4.4）。
- 其他人（含 lowConfidence 的 one-hot）：512 人，平均 0.587（最大 2.2）；其中有比例的 264 人平均 0.532。
- 全體 582 人平均 |ΔOVR| 0.624；OVR 有變的 561 人。

### 各位置進前 30／60／100 的人數（card 0.2.3 → 候選，以硬標籤計）
| 前 N | PG | SG | SF | PF | C |
|---|---|---|---|---|---|
| 30 | 9 → 9 | 3 → 3 | 7 → 7 | 6 → 6 | 5 → 5 |
| 60 | 15 → 15 | 10 → 11 | 12 → 11 | 15 → 15 | 8 → 8 |
| 100 | 25 → 24 | 20 → 21 | 16 → 16 | 22 → 22 | 17 → 17 |

## 限制
- 模擬目標 y 仍是以原硬標籤位置跑出來的，未重跑（預註冊 §2）；比例只進校準迴歸的位置項與防守置中。
- 沒有用到 pos 而未改的地方：`calibrate-wing.py` 的 `--restrictPos`（只給 G 系列 sanity check，本實驗未使用）、輸出 csv 的 pos 欄與 `rows[...]["pos"]` 讀取（來源 `position`）、`--posShares` 未帶時的原路徑（attach_rapm 與 pos_mean_d 的 pos 分組）；e075 管線（e082.py）只在報告用 pos（bigsTop10、top20 的 pos 欄）。
- 唯一未決定性：card 0.2.2 原程式 `summary.json` 的 `defenseBonusPosMeanD` 鍵順序每次不同（集合迭代順序），值相等；off 跑與 card 0.2.2 的這個檔 bitwise 不同、json 相等（primary/summary.json、fitA/summary.json、fitB/summary.json）。

## 唯讀目錄 sha256 前後比對（L-037）
| 目錄 | 檔數 前→後 | sha256 相同？ |
|---|---|---|
| reports/impact-rapm | 11 → 11 | 是 |
| reports/ovr-v58-holdout-2025-26 | 49 → 49 | 是 |
| reports/card-0.2.2 | 57 → 57 | 是 |
| reports/card-0.2.3 | 6 → 6 | 是 |
| reports/card-0.2.2+E073-usage-evidence | 38 → 38 | 是 |
| reports/card-0.2.3+E081-age-residual | 3 → 15 | 否 |
| reports/defense-tenth | 5151 → 5151 | 是 |
| data | 23455 → 23455 | 是 |

`reports/card-0.2.3+E081-age-residual/` 前後不同：E-081（另一個 session）在本任務期間持續往該目錄寫檔（開工時 3 個檔，結束時 15 個）。本任務對它只讀 `rapm1-A.csv`、`rapm1-B.csv`（sha256 見上），沒有寫入。開工時 3 個檔的逐檔 sha 沒有另存，所以「其中原有檔案沒被改」無法逐檔證明，只能說本任務沒有任何寫入該目錄的程式。其餘 7 個目錄前後相同。
預註冊 sha256（fc1462b8…8d10a）核對：OK。

## 檔案
- 新程式：`export_shares.mjs`、`s0_check.py`、`calibrate-wing.py`（與原檔 diff：`calibrate-wing.diff`）、`run_cards.py`、`build_card.py`、`e082.py`（與 e075.py diff：`e082.diff`）、`assemble.py`、`evaluate.mjs`（與原檔 diff：`evaluate.diff`）、`c2.py`、`s5.py`、`hash_ro.py`、`make_results.py`。
- 輸出：`ranking.csv`（候選，sha256 18da220b382621b31d3fafbf0a80778485e7ad114bf968dfaa8843a61aa50ea0）、`evaluation.json`、`npm-test.exit`／`npm-test.log`、`pos-shares.csv`、`cards/{off,on}/`、`out/{off,on}/`、`work/`、`results.json`。
