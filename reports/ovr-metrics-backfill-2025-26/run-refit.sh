#!/bin/sh
# 讀 RAPM 的卡片層：全量重現（full）與 A/B 半重擬合（possScale 0.5，與 ovr-v58-holdout 主要設定相同）。
# 在 repo 根目錄執行：sh reports/ovr-metrics-backfill-2025-26/run-refit.sh
B=reports/ovr-metrics-backfill-2025-26
H=reports/ovr-v58-holdout-2025-26
B12T=reports/ovr-v55-finisher-fix-2025-26/card/calibration-target-B12.csv
for fit in full A B; do
  if [ $fit = full ]; then R=""; else R="--rapm $H/rapm-$fit.csv --possScale 0.5"; fi
  d=$B/fit-$fit
  python $B/calibrate.py --target reports/ovr-v53-2025-26/calibration-target-s8-expected.csv --alpha 0.5 $R --out $d/v53 >/dev/null
  python $B/calibrate.py --target $B12T --alpha 0.5 $R --out $d/B12 >/dev/null
  python $B/calibrate.py --target $B12T --alpha 0.5 --league reports/ovr-v55-attr-deflate-2025-26/season-league-D.json $R --out $d/D1 >/dev/null
  python $B/calibrate_c1.py --target $B12T --alpha 0.5 --league data/season-league.json $R --out $d/C1 >/dev/null
done
