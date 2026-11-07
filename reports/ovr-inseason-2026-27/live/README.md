> **現行版本：inseason 0.2.12b（card 0.2.12b；R-140，E-204：四季窗口由 328 格縮成 246 格，`win_len.py`，`WIN_LEN=328` 重現 0.2.12a／card 0.2.12；卡片端 `reports/card-0.2.12b/`；完整說明見 `CURRENT.json` note）。前一版 inseason 0.2.12（card 0.2.12；R-139 升 PATCH：tovSkill 改看持球時間，`tov_live.py`＋`tov-pool-card0212.json`，每天抓 `data/defense-seventh/2026-27/possessions.json`；`TOV_POSS=0` 重現 0.2.11；自檢 `check_inseason_0212tov.py`；完整說明見 `CURRENT.json` note）。前一版 inseason 0.2.11（card 0.2.11；原標 0.2.10j，R-137 升 PATCH，檔名沿用 0210j；＝0.2.10i＋能力值引力 gravity，NBA.com 無球外線引力，`gravity_live.py`，`GRAVITY=0` 重現 0.2.10i；自檢 `check_inseason_0210j.py`；完整說明見 `CURRENT.json` note）。以下是更早版本說明：inseason 0.2.10h（＝0.2.10g＋賽中端 y、v 年齡改用開季當天足歲，整季固定；`birthdates.json`＋`AGE_START=0` 重現 0.2.10g；卡片端不動，card 仍 0.2.10g）。前一版 inseason 0.2.10g（card 0.2.10g＝0.2.10f＋E-192：用人層 L（上場強度）、a（出賽率）改四季滑動窗口；`window11.py` 繼承 `window10.py`，權重同 E-175 U 臂，可出賽場次＝出賽＋教練決定未上場；賽中每天用當下窗口重算，y、v 用當下年齡，lastOVR 基準＝本季 0 場窗口；係數同 0.2.10d，r_repl、錨點用新池重取＝`usage-2025-26-card0210g.json`；`USAGE_WIN=0` 重現 0.2.10f，讀 `_retired/usage-2025-26-card0210f.json`、先驗卡改 card-0.2.10f；自檢 `check_inseason_0210g.py`，出缺勤快取 `build_avail_0210g.py`）。前一版 inseason 0.2.10f（card 0.2.10f＝0.2.10e＋E-191b P1m：3PT 欄對照池改近三季窗口值＋本季，`TV_P1M=0` 重現 0.2.10e；ranking／OVR 同 0.2.10e＝0.2.10d 換 E-188 OVR 映射）；以下為 0.2.10d 的結構說明（card 0.2.10d，E-185／R-118／R-123；long、creation、threeValue、MPG_hat 也用 E-175 四季滑動窗口，window10.py；8 項屬性同 0.2.10 的窗口；底是官方 card 0.2.10c，用人層係數、r_repl、錨點取 reports/card-0.2.10d/usage-features.json 的 KAU 重擬合值，不再凍結）**。唯一入口 `run_c4_live_rookie.py`；`run_c4_live.py` 不能直接執行。版本與檔案清單見 `CURRENT.json`；舊版建構腳本與凍結檔在 `_retired/`（重現請 checkout 當時 commit）；`WIN10=0` 關窗口、卡／用人層換 card 0.2.10c（讀 `reports/card-0.2.10d/work-selfcheck`，只供拆項）。以下是歷史說明。

# inseason 0.1.0 即時版（2026-27）

賽中 C4（E-033，c=1 凍結）用 2026-27 已打場次逐球員更新能力值與 OVR。先驗＝v5 先驗卡 2025-26（card 0.1.0）。

**現行（inseason 0.2.2，E-091）**：先驗換成 card 0.2.4（R-044）。能力值欄與 card 0.2.2 逐欄相同，所以仍讀 `prior-2025-26-card022.json`（pressure／foulDraw／屬性欄不變）；差別只在 OVR 那層：p（屬性迴歸每 36 預測，C4 照常更新）→ predNew = b0 + b1·p + b2·L + b3·a + b4·y + b5·v + b6·y·L + b7·v·L + b8·y·d·L（用人回歸，R-040；L、a、y、v、d 凍結在 2025-26 全季，由 `build_usage_024.py` 呼叫 `reports/card-0.2.3+E084-current-target/e084.py` 重算，輸出 `usage-2025-26-card024.json`；has=False → predNew = p）→ g = (predNew − r_repl)·MPGhat/36 → 兩段式映射。係數、r_repl、錨點取 E-084 `results.json`（`coefficients.card`、`card.r_repl`、`card.anchors`）；MPG0 改用 card 0.2.4 `ranking.csv` 的 mpg 欄（mpgAvail，依姓名對，卡內沒有的人退回 MIN/GP），MPG_win 仍是 2026-27 MIN/GP。ranking.csv 新增 `predNew` 欄（`predictedPer36` 仍是 p）。環境變數 `CARD_MODE=024`（預設）；`CARD_MODE=022` 逐位元重現 inseason 0.2.1e（已用 2026-10-28 資料驗證）；`CARD_MODE=020` 重現 0.2.0c。報告：`../e089-card024/report.md`。

**前一版（inseason 0.2.1，E-074）**：先驗＝card 0.2.2（`prior-2025-26-card022.json`，`build_prior_022.py` 由 `reports/card-0.2.2/ranking.csv` 轉成）；凍結迴歸係數／每場錨點取 `reports/card-0.2.2/cards/P1/primary/{summary,pergame-summary}.json`；pressure＝逼失誤（賽中凍結）；foulDraw 賽中更新用 E-070 公式（常數凍結在先驗 JSON 的 `foulDrawFreeze`）。（0.2.1 時 `CARD_MODE=022` 為預設；`CARD_MODE=020` 逐位元重現 inseason 0.2.0c（先驗 `prior-2025-26-card012.json`）。輸出資料夾名要給絕對路徑才不會落在 live/ 底下）。

## 怎麼跑
1. `node scripts/fetch_season_games.js 2026-27`（使用者已跑）→ `data/season-source-2026-27/`。
2. `node scripts/fetch_inseason_2026_27.js`：複製 player-games／team-games、重抓 bio、抓每場 PBP → `data/defense-seventh/2026-27/`。
3. `python -I reports/ovr-inseason-2026-27/live/run_c4_live.py [資料夾名]` → `live/<資料截止日>/{ranking.csv,no-prior.csv,meta.json,README.md}`。
4. `python -I scripts/build_inseason_viewer.py [日期]` → `live/<日期>/roster-viewer.html`。

規則：S* 的 δ²、rel 只用嚴格早於 S* 的起點（Y1..Y6、D1..D3；short／creation 不含 Y 起點，同 v5）；每人 f = min(自己的 GP/82, 1)；沒有先驗卡的人不給 OVR；2026-27 結果不回頭調任何參數（L-026）。

## 降級的資料層（C4 讀不到或讀到不完整的）
| 項目 | 狀況 | 影響 |
|---|---|---|
| four-factors、v3-league、dependence、shot-origin（2026-27） | 抓取腳本不抓 | pressure 凍結；onBall／help／physique／heightInches 本來就凍結，C4 不更新防守端屬性 |
| PBP 0022600101 | 來源檔只到第一節（比分 33,34 對 108,111），重抓一樣 | 該場不進 shots／PBP 衍生的樣本；box 仍計入。`fetch_inseason_2026_27.js` 因此 exit 1，預期內 |
| 2025-26 先驗卡 midA = shortA = defensePossessions = 0 | 先驗樣本為 0 | mid／short／pressure 的 k 一律取上界（保守，等於幾乎不動：w≈0.05） |
| 2025-26 凍結映射 | 既有檔沒涵蓋 2025-26 | 用 box 公式重建（同 build_season_cards 流程）；long／ft／drive／tovSkill／stamina 與上季卡差 ≤0.05（tovSkill 個別 1.45），pass 中位差 0.58、最大 5.9，rebound 中位 0.48、最大 4.3，creation 中位 3.4、最大 24（它依賴 ff／v3 層），mid 不可重現（先驗樣本 0，不影響） |
| δ² | D3 的 mid／short 配對因 2025-26 目標先驗樣本 0 而掉出 | 這兩項 δ² 用較少配對估 |
| 無先驗卡球員 | 55 人（新秀、沒進先驗卡者） | 只列 `no-prior.csv`，不給 OVR |
| N=0 的有先驗卡球員 | 220 人 | 不列入 ranking.csv |
| 逐點管線 pr／T | 固定為開季先驗卡 | ΔOVR 為「同一把尺」下的差 |

資料覆蓋：2026-10-20..2026-10-27、56 場、417 名球員、每人 1–4 場；樣本極小，OVR 變動多半是少數低 k 屬性（pass／creation／rebound／tovSkill／ft）的收縮結果，只看趨勢。

## 新秀起點（E-116 → E-121，2026-10-30）
- `build_rookie_prior.py` 產 E-116 起點；`reports/E121-rookie-scale/build_2k_start.py` 再把 x0 齊頭平移到「2K 順位曲線換本站尺度 −5」（R-073），覆寫 `rookie-prior-2026.json`。E-116 原版留在 `rookie-prior-2026-e116.json`。
- 重跑 `build_rookie_prior.py` 之後一定要接著重跑 `build_2k_start.py`（它讀的是 e116 備份，先刪備份才會改用新產的 E-116 版）。

## 新秀賽中防守（2026-10-30，使用者：一有數據就更新）
- `scripts/fetch_defense_tracking.mjs 2026-27` 每天重抓整季累計的防守追蹤表（rim、three、hustle、advanced、matchups）→ `data/defense-seventh/2026-27/tracking/`；daily 的 `step_fetch_tracking`，失敗沿用上次的表。
- `rookie_defense.py`：照 card 0.2.7 同一套公式算 onBall（E-060 r＝zC3＋zB−zT，組平均與 z 凍結在 2025-26；r→屬性用 2025-26 對照內插＋E-101 尾巴）與 help（inverse(PLUSMINUS·n/(n+200), CURVE_DEF_RIM)）。`--check` 拿 2025-26 原始表重算：onBall 575 人最大差 1.8e-13，help 576 人最大差 0.15（卡片四捨五入 0.1）。
- `run_c4_live_rookie.py`：新秀只要出賽（N>0）且表裡有值，onBall／help 直接換成當季值（w=1，不另收縮；公式本身已含樣本量收縮，零樣本的人約落在 onBall 66、help 71）。老將仍凍結在先驗卡；新秀 defenseBonus 仍是 0。

## 老將賽中防守（2026-10-30，使用者：「用 TUL 類似的做法」、四季窗口）
- `rookie_defense.veteran(c)`：onBall／help 改用四季窗口逐場線性遞減（E-104 TL 的權重搬到季總計）。窗口 328 格（每季 82 格），最近一格 u≈1、最舊 u≈0；本季已過 c＝聯盟已賽場數／1230·82 格，窗口跟著往後推，2022-23 慢慢滑出。追蹤表只有季總計，每季的原始量（守禁區出手、PLUSMINUS·n、三分干擾、MIN、matchup 回合等）乘上該季那段的平均 u 再相加，再除以「他自己有資料那幾季的權重和」（本季只算已過的 c/82 季；下限＝他各季權重的最大值），等於各季量的加權平均：全勤四季的人有效樣本約一季，只有 2025-26 的人＝卡片原值，只有本季幾場的人＝本季原始量（同新秀 R-075）。公式、z 凍結值、r→屬性對照同新秀。
- 開季（c=0）權重：2022-23 0.0625、2023-24 0.1875、2024-25 0.3125、2025-26 0.4375；2026-10-28 資料（68 場，c=4.5）本季 0.497。
- 往年原始表：`reports/defense-tenth/step4-t2/raw/<季>/0-*.json`；本季：`data/defense-seventh/2026-27/tracking/`。
- `run_c4_live_rookie.py` 在 main() 的 `live_predict` 之後插 `vet_defense`（記憶體替換，不改 run_c4_live.py）；算不出的人維持先驗卡。lastOVR 仍是先驗卡算的，所以 dOVR 含「單季卡 → 四季窗口」的換算差。新秀仍照 R-075（w=1 本季值）。
- 第一版整體 ÷2 會讓只打過一兩季的人多收縮（Maluach help 94.2 → 82.4），使用者選改成每人照實際季數正規化（R-076）；現在 Maluach 只受本季比賽影響（94.2 → 89.6）。

## 防守加成賽中重擬合（2026-10-30）
- 使用者要 defenseBonus 也解凍。daily 先跑 `scripts/build_inseason_stints.js`：沿用稽核過的整季程式 `fetch_defense_seventh_season.js`（只拿掉 1230 場檢查；box 補抓、pbp 用快取）與 `prepare_defense_b1.js`，產生 `reports/defense-seventh/2026-27/stints/stints.jsonl`（不跑整季驗證與 stint-zones）。失敗不擋發布，沿用上次的 stints。
- `defense_bonus.py`：E-104 L 形逐場線性擬合（λ 3000）只換時間軸。窗口是最近 328 格 [c, 328+c]，本季場次位置是 gameId 序號/1230·82，滑出窗口的 stint 權重 0。`--check`：c=0 時和 `def-L-primary.csv` 877 人 D、possW 完全相同。
- `run_c4_live_rookie.py` 的 `live_bonus` 把擬合結果寫到 `data/_inseason_build/def-L-live.csv`，換掉 M27_DEF 對應檔後重算 UL 加成。posMeanD、possW 門檻（≥500 算平均、≥2500 才有加成）、0.75 都照 card 0.2.7。檢查 (a)（f=0 → 先驗卡 OVR）用凍結加成，lastOVR 也仍是凍結加成，所以 dOVR 含加成變化。
- 新秀沒有先驗卡、不在 pipe 裡，加成仍是 0。possW 要到 2500 才有加成；開季第 5 場時新秀最多約 650。
- 10-28 資料（68 場，c≈4.53）：D 的變化幾乎都來自本季 4–5 場（只滑窗口時平均 |ΔD| 0.014，加上本季後是 0.14）。

## 名單頁 OVR 折線（2026-10-31）
- `ovr_history.py <今日輸出夾>`：用現行模型把 2026-27 資料截到每個比賽日（GAME_DATE ≤ d）逐日重算，寫 `ovr-history.json`（每人 start＝lastOVR、pts＝自己出賽日的 OVR），名單頁畫在近 5 場右邊。最後一天直接用當天 ranking.csv。
- 不串每日快照：各天版號不同、新秀起點改過，串起來會有假跳動。防守追蹤表只有季累計，過去的點沿用最新那份（只影響防守兩項）。
- 快取 `ovr-history-cache.json`（gitignore）：鍵＝版號＋本資料夾 *.py／*-2026.json 雜湊＋截斷資料 sha；全重算約 3–4 分（每日 10 天），命中約 3 秒。每日更新失敗只記警告、不擋發布。

## 壓迫、切入賽中解凍（2026-11-01）
- 模組 `live/pres_drive.py`，開關 `UNFREEZE_PD`（預設 1；設 0 時 `run_c4_live_rookie.py` 不呼叫它、不做任何替換，ranking.csv 逐位元同解凍前；`run_c4_live.py` 單跑本來就不受影響）。
- 老將：同 onBall／help 的四季窗口（`rookie_defense.window_weights(c)`、units 同一套、每人除以他有資料那幾季的權重和，下限＝他各季權重最大值）。窗口加的是**原始累計量**，再套卡片公式；常數全部凍結在 2025-26 或更早，沒有用 2026-27 結果調任何東西（L-026）。算不出的人維持先驗卡。
- 新秀（沒有先驗卡、本季有上場）：本季值 w=1（R-075），經 `xhat_of` 取代 pressure／drive；presDisplay 欄也換本季值。
- pressure／presDisplay（card 0.2.7b 實際路徑）：E-071 `build_force.py` 的 `season_raw`／`comps_of` 逐季算分量（stl、defl、chg：count 與 MIN/36；pf 同；mtov：每季用該季進攻方失誤率算期望值，(tov−exp, poss/100)），各季乘窗口權重相加。收縮 k＝E-071 `shrink.json`；收縮目標 m、池平均／標準差＝2025-26 卡片池（252 人，GP≥30 且 MPG≥20）；force＝(z_stl＋z_defl＋z_mtov＋0.5·z_chg)/3.5，disp＝force−0.25·z_pf；兩者對 E-123 四季合併池（`work/season-values.json`）取百分位，尾巴照 E-123 h1。本季原始表：base 由 `data/defense-seventh/2026-27/player-games.json` 加總、hustle／matchups 讀同資料夾 `tracking/`。
- drive（card 0.2.7b＝v61 方法 c＋E-101 合併池＋E-090 h1 尾巴）：每季量＝(nv 未助攻突破加權次數、MIN、pts、nW)，權重：被助攻進球 0、未助攻進球 1、失手＝該季該類別未助攻比例。往年讀 `ovr-v61-shrink-history-2025-26/history/`，本季用同一份 `extract_pbp.parse_game` 解析 `pbp/`，分鐘只算有 PBP 的場。窗口用各季**全季**量（卡片只用前 41 場是 v60 的包袱）。vol＝36·(nv＋k·Tv)/(MIN＋k)、eff＝(pts＋k·Te)/(nW＋k)，k＝90.51；Tv／Te＝卡片的每人歷史目標（2022-23～2024-25、λ＝0.5、kh＝32、同位置平均凍結在 2025-26 前 41 場），新秀用 G／F／C 合併位置平均；score＝0.5·z(vol)＋0.5·z(eff)，z 凍結在 2025-26 卡片池，對 E-101 合併池（913 值）取百分位。
- 檢視器：`run_c4_live_rookie.py` 多寫 `pres-drive.json`（窗口後的五個收縮分量），`scripts/build_inseason_viewer.py` 有這個檔就用它做 PRES 提示卡（PR 人群＝窗口有效分鐘 ≥1000 的老將），註記「老將四季加權含本季；新秀只看本季」；沒有就照舊用 2025-26 分量。`season_nav.ATTR_TIPS` 的 pressure、drive 第五欄同步改。
- 對照（`python -I -X utf8 pres_drive.py --check`：全部權重給 2025-26，drive 用前 41 場＝卡片定義）：pressure N=582 最大差 0.000、>0.1 的 0 人；presDisplay N=582 最大差 0.050（卡片存到 0.1 位）；drive N=509 最大差 0.034、>0.1 的 0 人（另 73 人 2025-26 前 41 場沒上場＝卡片預設 70，賽中維持先驗卡或由其他季補）。drive 中間 score 對 E-090 `a0-raw.json` 最大差 4e-15；0.034 是浮點同分在 913 人池裡差半個名次（30/49·50/913）。
- 往年各季套 2025-26 凍結常數後，和 E-123 各季自己常數的值會差幾分（例：Tatum 2022-23 45.2 vs 54.1），這是「常數凍結在 2025-26」的設計結果，沒有修。
- 2026-10-31 資料（81 場，c=5.40）的影響：老將 pressure／drive 582 人全部改窗口值，新秀 42 人全部有本季值；OVR 中位數 |Δ| 0.3、112／484 人變動 ≥1；變動最大的是上季樣本很少的人（Jalen Green 70.1→64.3、Tatum 96.5→92.9、Kessler 80.5→77.6、Jokić 90.2→92.7）；前 20 名 Jalen Johnson 進（22→19）、Curry 出（18→21）。
- 其他用 `RW.load_ns()` 的模組（e139、formula-gap、e136 live_demo）在預設開啟時結果也會跟著變。
