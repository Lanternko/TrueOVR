# E-070 稽核（role-audit，獨立 session）

稽核對象：foulDraw 改為 `0.75·z(shrunk FTA/36) + 0.25·z(shrunk FTA/FGA)` 的池內百分位。
依據只用預註冊、產出檔與腳本；沒有採用 report.md／verdict.json／memory 的結論文字。
稽核端所有腳本都在本目錄，沒有 import 產出方腳本；子程序皆 CREATE_NO_WINDOW；未改任何其他目錄、未 commit／push。

## 判定總表

| 項目 | 產出方 | 稽核重算 | 判定 |
|---|---|---|---|
| 預註冊 sha256 | c3fe3cd7…（凍結值） | 同（c3fe3cd7a049a6a3…） | 成立 |
| vol 擬合（訓練 2015-16..2024-25，N=3424） | position, λ=0.35, kh=4.0, k=8.0；MAE 0.70257 | 全格點（2 prior×6λ×13kh×26k）搜尋，argmin 同一組，MAE 0.70256855 | 成立 |
| 收縮檢查（2025-26，n=372） | 收縮 0.7507／k0 0.8286／前半 0.8410 | 0.75066／0.82863／0.84096 | 成立 |
| foulDraw 逐人重算 vs attributes-w075 | — | 最大差 4.98e-7（6 位小數捨入），差 >1e-5 者 0 人 | 成立 |
| foulDraw vs primary/ranking.csv（1 位小數） | — | 最大差 0.0499，差 >0.051 者 0 人 | 成立 |
| 整條鏈端對端重跑 | primary/fitA/fitB | 用稽核端自己的 foulDraw 檔跑 calibrate-wing，三組 ranking／pred／pergame-repl／summary 與產出方逐位元相同；自組 ranking.csv 與 primary/ranking.csv 逐位元相同 | 成立 |
| (c0) w_vol=0 | cards-w0 = card 0.2.0 | sha 22cd49cf…，cmp 與 reports/card-0.2.0/ranking.csv 相同；attributes-w0 與 V61 attributes-new.csv 全欄相同；cards-w0 的 fitA/fitB 與 E-064 入庫的 fitA/fitB 逐位元相同 | 過 |
| 只動 foulDraw | — | 能力欄 long…pressure（15 欄）0 人變動；pos、MIN 不變；w075 屬性檔對 V61 只有 new_foulDraw 一欄變（568 人）。ranking.csv 其餘變動欄為 rank、ovr、ovr36、gRepl、predictedPer36、pred0、pr、align（399）、defenseBonus（8 人，最大 0.135）——皆為重新擬合的衍生量 | 成立（見問題 4） |
| (c1) npm test | 57 passed, 0 failed | 稽核自跑 57 passed, 0 failed，exit 0 | 過 |
| (c2) Δρ（repl，possScale 0.5） | +0.00067，90% [-0.00089, +0.00225] | +0.00067，[-0.00089, +0.00225]；game +0.00143 [-0.00033, +0.00313]；ovr36 +0.00056 [-0.00124, +0.00243]；n：A→B 389、B→A 388、聯集 395 | 過（下界 -0.0009 > -0.02） |
| (c3) evaluate 過關數 | 兩者皆 18/19 | 複製 evaluate.mjs（只換輸出路徑）重跑：card 0.2.0 18/19、E070 18/19，兩者唯一未過同為 allFourStayTop10；evaluation.json 與產出方逐欄相同 | 過（≥ 持平） |
| fitA／fitB 只用一半 RAPM | — | rapm-A 與 rapm-B 為 gameId 奇偶分半：Jokić pooledPoss 20789 + 17803 = 38592 = 全量；兩檔球員數 864／863 vs 全量 877；run 指令帶 `--rapm rapm-{A|B}.csv --possScale 0.5 --mpgSource mpg-{A|B}.csv`；稽核端自己重跑同指令得到逐位元相同的卡 | 成立 |

c2 的 w0 對照有兩個來源，結果完全一致：產出方重建的 cards-w0/fit{A,B}，以及 E-064 當時入庫的 fit{A,B}（兩者逐位元相同）。
Bootstrap：2000 次、seed 1、球員配對、兩方向共用抽樣（聯集 395 人）；排名相關用自己寫的平均名次 Spearman。

## G5 名單（582 張卡；FD 名次為競賽名次，同值並列取小）

| 球員 | FD 舊→新 | FD 名次 舊→新 | OVR 舊→新 | OVR 名次 舊→新 |
|---|---|---|---|---|
| Shai Gilgeous-Alexander | 96.4→98.5 | 21→5 | 112.8→112.6 | 1→1 |
| Luka Dončić | 95.2→98.8 | 30→4 | 103.0→103.1 | 3→3 |
| Joel Embiid | 97.6→99.0 | 13→1 | 90.2→90.1 | 16→17 |
| Rudy Gobert | 99.0→91.3 | 1→40 | 86.6→86.7 | 27→27 |
| Steven Adams | 98.3→88.4 | 8→62 | 67.3→67.5 | 237→234 |
| Alex Antetokounmpo | 84.3→85.3 | 116→81 | 53.3→53.3 | 473→473 |

方向合理（高量球星上升、只靠低出手數撐高比率的大個子下降）。OVR 最大變動 +1.2／-1.0，457 人 OVR 有變；前 20 名只換一人（OG Anunoby 出、Stephen Curry 進）。
2K27 ρ 0.6953→0.6987、RAPM ρ 0.8139→0.8136、防守 ρ 0.5572→0.5551（皆為回報項）。

## 與預註冊的逐項對照

- 定義：rate 沿用現行；vol=FTA/36，以 E-055 方法 (c) 收縮（1–3 季歷史，λ、kh、k）；組合權重 0.75；池 GP≥30 且 MPG≥20（base.json，252 人，全在 582 卡內）；MIN_D2=300 分鐘（換成 /36 單位 300/36）。全部與腳本一致。
- k/λ/kh 只用 2025-26 之前的季擬合；稽核端的訓練季清單只到 2024-25，結果同產出方，無洩漏。
- w=0.75 為預註冊值，沒有掃描其他權重；無「看過結果再調參」證據（L-026）。
- 時序：preregistration.md mtime 03:20:22，早於 vol-fit.json（03:27:50）、卡（03:28）、evaluation（03:30）、c2（03:32）。

## 問題（依嚴重度）

1. 低：預註冊檔與整個 E-070 資料夾尚未進 git（untracked），「凍結早於結果」只能靠檔案 mtime 與 sha256 佐證，不能靠 commit。內容 sha 與凍結值相符，未發現被改動。建議收工 commit 時把預註冊先於結果的順序記入。
2. 低：預註冊沒寫 z 分數用母體標準差（ddof=0）。產出方與稽核端都用 ddof=0；若改 ddof=1，池內 z 整體等比縮放，百分位排序不變，只影響並列點，對結論無影響。
3. 低：kh=4.0 落在 KH_GRID 的下緣（格點沿用 V61，未擴大）；前五名 MAE 只差 0.0006（0.70257–0.70321），且 k=8 在內部。收縮檢查 0.7507 vs 0.8286 有餘裕，不影響結論。prior（position 0.70257 vs league 0.70382）按 E-055 規則以訓練 MAE 選，屬程序性，非調參。
4. 低：「只動 foulDraw」嚴格說是只動 foulDraw 輸入；ranking.csv 的 defenseBonus（8 人，≤0.135）與 align 等是重擬合的衍生量，不是能力欄。已確認 15 個能力欄與 pos、MIN 完全不變。
5. 低：npm test 在含未提交 src/probability_model.js 修改的工作樹上跑（該修改在派工前就存在，非 E-070 的產出），57/57 過。
6. 資訊：c2 的 Δρ 僅 +0.0007，區間跨 0，只能說「沒有變差」，不能說「變好」；通過標準是非劣（> -0.02）。possScale 1.0 敏感度沒有獨立重跑（回報項，未納入判定）。c2 的 RAPM 窗（2022-23..2025-26）與 vol 擬合訓練季重疊，但擬合目標是 FTA 預測 MAE、不是 RAPM，沒有答案洩漏。

## 結論

E-070 的所有數字都被獨立重算證實：foulDraw 逐人重算最大差在捨入內、擬合參數是格點全域最小、整條鏈端對端重跑逐位元相同、c0／c1／c2／c3 全過。沒有發現違反預註冊或事後調參。
判定：結果成立；採用與否由主管決定。
