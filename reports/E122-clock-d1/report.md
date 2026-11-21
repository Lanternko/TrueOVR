# E-122 回合時長 D1 接進引擎（第二階段）報告

預註冊 sha256 79f8189d…f066（已核）；修訂 A1 sha256 cc3399bb…3e03（已核）。A1 在看到任何 c2 結果之前收到（當時只看過 c1 進度行）。

## 改動
`src/defense_fourth_game.js` `empiricalDuration()`：選項 `defenderClockBeta`（預設關），對 origin 非 'retained' 且 clock≥30 秒的回合，加上場上 5 名防守者 β 之和（秒），再套原本上限。diff 僅此一處（工作樹另有 E-120 未提交的 defenderFoulBeta 改動，不屬本實驗）。LF 版 sha256 081f6523…1b283（改前 e7aa7b3e…e983）。`npm test` 目前 52 passed 0 failed（log: npm-test.log；先前 57，之後 HEAD 的 commit 改了測試數）。

## 關卡
- p0 過：關閉或 β 全 0 逐位相同（12 seed）；單一防守者 +2 秒使全時鐘回合平均 +1.84 秒、WinImp 淨分差差異 +1.14（SE 0.519）。揭露：「WinImp 有變」由我定義成配對差 > 2 SE；N=300 時 1.95 SE 差一點，改 N=1500 重跑才過（p0-N300.json 保留）。
- c1 過：n=304，r=0.649（門檻 0.50），斜率 0.895，每人防守回合 ≥ 8935。c1 跑到 287/304 時 runner 在佇列尾端對 undefined job 取 id 而崩潰（c1-run.mjs，已加 next<jobs.length 判斷），從 checkpoint 續跑完成；c1 定義未動。
- c2（A1）過：MAE 開 3.0442／關 3.2230／關第二組 3.1158，N=0.1072，Δ=−0.1788 ≤ 0.2072。bootstrap 90% CI [−0.464, +0.114]（跨 0）。8 seed 的 Δ=−0.1793（不作判定）。迴歸：球隊變化對先發 D1 β 和 斜率 0.067、r²=0.0015；只加系統部分 MAE 3.2198，只加殘差部分 3.0498。結論：改善落在雜訊內、與 β 無關，不能說是 β 帶來的。關閉版與 E-120 8 seed 關閉版逐位相同。
- c3（只報告）：關閉版 379 人與 E-065 winimp.csv 逐位相同。開 vs 關 Spearman 0.886，WinImp 平均 +0.79 勝/82，位移 sd 1.50（中位 SE 2.62）。E-067 S（主版）AB 81.8→52.7、BA 95.2→64.8（仍判偏袒長人）；位置版 AB 37.5→92.4、BA 50.1→104.3（變差）；ρ 平均 主版 0.382→0.397、位置版 0.304→0.324。
- 名次前→後：Daniels 90→29、Caruso 163→90、Smart 361→313、D. White 29→21、Holiday 48→32、Dort 351→292、H. Jones 295→331、Gobert 5→8、Wembanyama 3→5、Adebayo 55→121、Jokić 1→1、Brunson 61→74。位置平均（主版 前→後）C 4.58→4.27、PG 1.54→1.96、PF 0.95→1.64、SF 0.13→1.77、SG 0.27→1.68。

## 偏離與限制
- c3 worker 把所有 profile playerId 設 -1（避免 β 滲入 averageProfiles 的控制組），關閉版因此仍與 E-120/E-065 一致。
- c1 用事件重建首段時長（初始 [0..4]+換人事件）、每個候選單人 β 表。
- inputs sha256：本機工作檔為 CRLF，雜湊與 5090（LF）不同；以 5090 端為準，結尾核對全部相同（inputs-sha256-end.txt）；E120 judgement.json 在本機核對。
- 未 commit、未 push；E-067 位置版 S 變差未解釋（不調參，L-026）。
