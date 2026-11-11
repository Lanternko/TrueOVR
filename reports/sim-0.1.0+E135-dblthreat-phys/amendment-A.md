# E-135 執行修訂 A（2026-10-30，m1 結果出來之前寫）

1. m1 的「v41 2025-26 同季重現」改成用現行引擎（sim 0.1.0，E-086 hook）打 30 隊單循環（E-117 rr-core 的配對、seed、輪替寫法），seed 20261028–30。
   原因：v41 管線是凍結的舊引擎（step4 adapter＋v41 model），有自己的來源雜湊檢查，不能套 ch1；處理組改的是現行引擎。
   判準不變：中鋒組減後衛組的隊友在場 FG% 誤差要縮小；球隊每場得分 RMSE（答案 OFF_RATING×PACE/100）不得變差超過 0.2。
   隊友在場 FG% 答案仍用 v41 驗證表的 onTeammateFG_actual（實際數據，與引擎無關），篩 actualMinutes ≥ 800。
2. 啟動前的本機冒煙測試（2026-10-30 13:45 左右）發現：ch1 開／關在 40 場、155 名球員的比分與隊友在場投籃上逐位相同。
   doubleThreat 有被呼叫（每場約 1.35 萬次、ch1 分支有走到），但現行引擎只透過 measuredScoringThreat = self + doubleThreat(p) − sourceDouble 用到它，
   而 sourceDouble 在載入時用同一個公式算，兩邊同時改、差值不變。teammateContext 的 dblPeer／doubleRate 這條路在 rotation-space 對局裡實測也沒有改變任何結果（沒有逐行追到它在哪裡被換掉）。
   這件事在 m1 跑之前就知道，照預註冊 m1 仍照跑一次留檔。

## 補記（m1 結果出來之後寫，2026-10-30 13:55）
- 5090 上 m1 單循環 1305 場有 25 場比分不同（本機 40 場剛好都沒碰到）；WinImp g0 的 ch1 4800 格全部不同。
- 解讀：真實球員有 creationContextMeasurement，doubleThreat 被 sourceDouble 抵銷，ch1 對他們不起作用；
  WinImp 的隊友與替補都是聯盟平均 profile（沒有量測錨點），ch1 改的是這些平均隊友的 doubleThreat，
  不是頂端長人自己的。原假設「長人的體格灌高自己的包夾威脅」在現行引擎裡不成立，b1 量到的會是另一條路徑。
- m1 依原判準通過，照預註冊跑全量（i=0..59，379 人，W=12，nice 19）。
