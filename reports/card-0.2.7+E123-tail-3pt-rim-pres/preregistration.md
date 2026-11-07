# E-123 預註冊：3PT、RIM、PRES 開放 99 以上尾巴

日期：2026-10-30（使用者 2026-10-30「Freeze and run」核可凍結）。

- 基準卡：card 0.2.7（`reports/card-0.2.7/ranking.csv`，sha256 aebcadf1c3dfcbe6aaeed8c34fa5183cd35dbda546dd967faa5ebdf6649cc6b6）。
- 框架照 E-101（`reports/card-0.2.5+E101-crossera/preregistration.md`，已進正式卡 card 0.2.6／0.2.7）：用 2022-23 到 2025-26 四季合併池算錨點；頂端的尺 S = max((r99 − r90)/1.044, SD_pool)；頂端公式 `99 + 51·(1 − e^(−Δ/(1.96·S)))`，底端照 E-096。本實驗只把這套框架套到 E-090／E-101 漏掉的三欄，公式和常數不改。

## 0. 由來與使用者指示
- 使用者 2026-10-30：「為何 rim pres 3PT 的錨點沒修，最強的很多人都在 99 整」→「寫預註冊」。
- 查明的原因（lead，2026-10-30，只讀檔）：
  - **3PT**：網站顯示的是 `threeValue`（R-024，只顯示，不進 OVR），讀 card 0.1.1 時代凍結的 `reports/card-0.1.1+E057-three-value/three-value.csv`。E-096／E-101 只替 midValue、shortValue 開尾巴，漏了 threeValue。
  - **RIM（help）**：E-090 §1 排除，理由是「由 E-080 處理」。E-080 沒過（b2'），之後沒人補。
  - **PRES（pressure）**：E-090 h1 寫「force 只有 2024-25、2025-26，相鄰季 1 組 < 2，排除」。但 `reports/defense-tenth/step4-t2/raw/2022-23/`、`2023-24/` 的 `0-hustle.json`（DEFLECTIONS、CHARGES_DRAWN）和 `0-matchups.json`（逐對 MATCHUP_TOV、PARTIAL_POSS）都在硬碟上，所以排除的理由不成立（L-072）。
- 使用者先前的指示（沿用）：R-055（很多屬性到 140 不合理）、R-056（頂端錨點用多季合併的 PR90–PR99；120 分代表跨時代也突出；偏弱的季可以沒人到 99）。

### 已揭露（L-026）
- lead 看過的：
  - card 0.2.7 與新賽季頁（inseason 0.2.7，數據到 2026-10-28）三欄的頂端名單與剛好 99 的人數：threeValue 4 人（Curry、Knueppel、Murray、Isaiah Joe；新賽季頁 Curry、Murray、AJ Green），help 4 人（Wembanyama、Kalkbrenner、Isaiah Stewart、Holmgren），pressure 7 人／presDisplay 6 人（Thybulle、Goodwin、Dru Smith、Cason Wallace、Ausar Thompson、Caruso，pressure 另有 Paul Reed）。各欄第 5–10 名的值（98.0–98.9 左右）。
  - E-080 全部結果（另一種收縮下 help > 99 有 12 人，Stewart 115.7）；F-030 的 Stewart 原值 123、z 4.82；E-071 全部結果；E-057 全部結果。
  - 2022-23、2023-24 歷史檔的欄位名稱與列數（hustle 535／567 列、matchups 135,389／137,763 列、rim 530／562 列）。v62 追蹤投籃檔只有 2023-24、2024-25、2025-26 三季。
  - lead 手算過一個估計：如果 Stewart 在合併池仍約高出 r99 2.5 個 SD，套頂端公式大約 125–136。這只是在寫預註冊前提醒自己頂端可能很高，沒有拿來挑任何參數。
- lead 沒看過的：三欄在任何歷史季的值、任何跨季百分位或錨點、任何 h1 斜率、任何候選卡、OVR 或名次。
- 不是看結果挑的選擇：1.044、1.96、51、150、門檻 −0.02／−0.05、seed 20261029 都沿用 E-090／E-096／E-101／E-107；四季窗沿用 R-056／E-101。

## 1. 三個部分
| 部分 | 欄位 | 進不進 OVR | 判定方式 |
|---|---|---|---|
| T | threeValue（網站 3PT） | 不進（R-024） | 只看 §3 前置、h1v、c4（顯示層） |
| H | help（網站 RIM） | 進 OVR 迴歸；引擎另有 CURVE_DEF_RIM | 卡片層 §5 |
| P | pressure（卡片）＋ presDisplay（網站 PRES） | pressure 進 OVR 迴歸；presDisplay 只顯示；模擬不讀 | 卡片層 §5 |

三部分都照 E-101：2025-26 的百分位、r90、r99、r1 都對四季合併池計算（每個球員季算一筆，不去重）；h1 過的那一端才開尾巴，沒過的那端維持 99／40。中段值也會因為換成合併池而變動，這是 R-056 的既定做法，不另判。

## 2. 每季原始量（照「把該季當成當季」的同一套流程）
### 2.1 T：threeValue
- 公式照 E-057（`reports/card-0.1.1+E057-three-value/make_three_value.py`）：acc = v62 方法 (c) 難度調整能力（k = 294.667 凍結）；vol = v62 `Ds.feat('r36')`；rep = 該季聯盟三分命中率 mu − 0.03；value = vol × (acc − rep)。
- 季別：2023-24、2024-25、2025-26 用 `reports/ovr-v62-3pt-difficulty-2025-26/raw/` 現有檔。
- 2022-23：用 v62 `fetch_data.py` 的同一組端點補抓（C&S、pull-up、防守距離）。抓不齊（任一端點失敗或球員數少於 2023-24 的 90%）時，T 改用 2023-24 到 2025-26 三季池、h1v 用兩組相鄰季，照實寫進報告。這條退路在看結果前定死，不可因結果改回四季。
- 池：每季 MIN ≥ 500（同 E-057）。

### 2.2 H：help
- 原始量：rim 防守 FG% 差（`0-rim.json` 的 PLUSMINUS，FGA_LT_06），2022-23 到 2024-25 用 `reports/defense-tenth/step4-t2/raw/<季>/0-rim.json`，2025-26 用卡片現行來源 `data/benchmark-source/defense-rim.json`。
- 收縮與換算照 card 0.2.7 現行的 help 流程（E-058 defense-v3 的 `new_help`，經 `--defSource` 進 calibrate-wing）。**不用 E-080 的位置收縮**（E-080 不採用）。
- 池：照現行 help 的池（實作者在 a0 寫明）。

### 2.3 P：pressure、presDisplay
- force 公式照 E-071（`reports/card-0.2.0+E071-pressure/build_force.py`）：stl、defl、對位失誤調整後、0.5·chg 四分量，k 凍結在 E-071 `shrink.json`（含勘誤 1），每季在該季池內算 z。
- 2022-23、2023-24：hustle 與 matchups 用 `reports/defense-tenth/step4-t2/raw/<季>/0-hustle.json`、`0-matchups.json`；STL、PF、MIN 用 `leaguedashplayerstats`（Base、Totals），硬碟上沒有就照 E-071 `fetch.mjs` 補抓。
- presDisplay = force − 0.25·z(PF)，照現行 `presDisplay` 算法，用自己的四季合併池；頂端、底端開不開跟著 pressure 的 h1 結果。
- 注意 F-046：force 是每季標準化後的值，跨季合併池和單季池差不多。照 E-101 處理 onBall 的方式照做，報告寫明。

## 3. 前置關卡（任一沒過：該部分排除，維持現狀，其他部分照跑；不改規則重試）
| 代號 | 條件 |
|---|---|
| a0T | 用 §2.1 的程式重算 2025-26 threeValue，和 `three-value.csv` 的 `tv_main` 每人差 ≤ 0.05 |
| a0H | 用 §2.2 的程式重算 2025-26 help，和 card 0.2.7 `ranking.csv` 的 help 每人差 ≤ 0.05 |
| a0P | 用 §2.3 的程式重算 2024-25、2025-26 force，和 E-071 `force-2024-25.csv`、`force-2025-26.csv` 每人差 ≤ 1e-6；pressure、presDisplay 和 card 0.2.7 每人差 ≤ 0.05 |
| a0P' | 2022-23、2023-24 的 defense-tenth hustle 和 E-071 自抓的同端點格式一致（欄名、單位相同）；2024-25 兩份來源 DEFLECTIONS、CHARGES_DRAWN 逐列相同 |
| f-eng | 列出 `src/` 裡 help 進引擎的所有地方，確認卡片 help > 99 時引擎會截在 99，或活的 WinImp 鏈不讀卡片 help。做不到（會讀到 > 99）就把 H 排除並停下回報，不改 `src/`（E-080 就是在引擎端出問題） |

- 先寫 `sources.json`（每部分用哪些檔、人數、sha256），之後才准算任何斜率。

## 4. h1：跨季持續性（開尾巴前先做）
- 規則照 E-090 §5：相鄰季 2022-23→2023-24、2023-24→2024-25、2024-25→2025-26（T 退路時只有後兩組）；兩季 MIN 都 ≥ 500；每組配對內上期百分位 ≥ 90 為頂端、≤ 10 為底端；配對合併後，用下期對上期做 OLS 求斜率；同一人多組一起重抽 2000 次，seed 20261029；**90% 區間下界 > 0 才開那一端**。
- 至少要有兩組相鄰季，做不到的那一部分排除。
- 4 個檢定對象（threeValue、help、pressure，presDisplay 跟 pressure）× 2 端 = 6 個檢定，不做多重比較校正，由 §5 卡片層把關。
- 先寫 `h1-pairs.json` 並記 sha256，再跑斜率。

## 5. 判定
### 5.1 變體
| 變體 | 內容 | 角色 |
|---|---|---|
| cur | card 0.2.7 | 基準 |
| **e123** | H＋P 都套（合併池＋h1 通過的尾巴）；T 另算顯示值 | 主要，判定 |
| e123h | 只套 H | 只報告 |
| e123p | 只套 P | 只報告 |

卡片鏈照 card 0.2.7（E-107 UL6：`reports/card-0.2.6+E107-defense-UL/` 的 calibrate-wing `--tailSource` → 卡片鏈 → e094 pipeline），只把 help、pressure 換成本實驗的值。參數、seed、人群不改。e123h、e123p 的結果比較好，也不能改當主要版本（L-026）。

### 5.2 卡片層（e123 對 cur）
| 代號 | 條件 |
|---|---|
| c0 | `--tailSource` 指向現行值，重建出的 ranking.csv 和 card 0.2.7 逐位元相同（aebcadf1…c6b6）；不過就停下修程式，不看任何誤差數字 |
| c1 | `npm test` 全過 |
| m1 | Δρ_{N_W} 90% 下界 > −0.02（照 E-107） |
| m2 | Δρ_{Q_W} 90% 下界 > −0.05 |
| m3 | Δρ_{N_lin} 90% 下界 > −0.05 |
| c3 | evaluate.mjs 通過數 ≥ card 0.2.7 的 18/19 |
| c4 | 卡片所有球員的全部屬性（含 threeValue、presDisplay）裡，> 140 的值 ≤ 2 個（同 E-101） |

- 全過：H＋P 記為通過，交 G5。任一條沒過：記為未過，停下交使用者，不准拿掉某一部分或換參數重跑。
- T 只看 a0T、h1v、c4：過了就把 threeValue 記為可上線的顯示值，和 H＋P 的結果分開交 G5（T 不動 OVR）。

### 5.3 只報告
- 每部分：合併池的 r90、r99、(r99 − r90)/1.044 ÷ SD_pool、保險有沒有生效；2025-26 的 > 99、> 120、> 140、< 40 人數與名單，以及剛好 99 的人數（現在是 4／4／7／6）。
- 各季到 99 的人數（看哪季偏強、偏弱）。
- 指定球員：threeValue 看 Curry、Knueppel、Murray、Isaiah Joe、Edwards、Kennard、Portis；help 看 Wembanyama、Isaiah Stewart、Kalkbrenner、Holmgren、Mobley、Gobert；pressure／presDisplay 看 Thybulle、Caruso、Dru Smith、Cason Wallace、Ausar Thompson、Diabaté、Paul Reed。
- OVR 前 20 名對 card 0.2.7 的變動；R-061（Wagner 要排在 Wembanyama 後面）有沒有守住；ρ2K、ρRAPM（樣本內，R-007 不算證據）。
- e123h、e123p 的 m1–m3、c3、c4。

## 6. 偏離與限制（事先寫明）
- 引擎命中率／護框曲線不改，卡片 99 以上和模擬暫時脫鉤（同 E-096 §7）；不跑模擬，所以 E-080 的 b2'（長人偏袒）這次不測。
- 新賽季頁（inseason）不在本實驗內；跟上另走 inseason 實驗（R-050）。threeValue 的新賽季算法（上季加本季 3PA 合併）也一樣。
- T 的 2022-23 要補抓；抓不齊走 §2.1 退路。
- 沒做多重比較校正。

## 7. 寫入範圍與不准
- 只寫本資料夾；凍結時 lead 在 `memory/experiments.md` 追加 E-123（狀態「進行中」）。
- 不碰 `src/`、`scripts/`、`reports/card-0.2.7/`、`reports/defense-tenth/`、v62 `raw/` 原檔（補抓的 2022-23 寫到本資料夾）、名單頁、`live/`、gh-pages。
- 不 commit、不 push、不發布。

## 8. 回報
照 CLAUDE.md 六段（`# 總評` 放第一行、五級附分數 → 這次目標 → 進步 → 退步 → 直觀證據 → 要你決定的事）。用「誰從 99 變幾分」「剛好 99 的人從幾個變幾個」的講法；斜率、Δρ、區間、閘門代號放第 6 段之後。T 和 H＋P 的結論分開寫在同一份六段裡。
