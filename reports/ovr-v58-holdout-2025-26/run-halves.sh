#!/bin/sh
# 用 A 半 / B 半 RAPM 各自重擬合 E2、F2、G3、H1-m0（possScale 0.5 = 主要；1.0 = 敏感度）
H=reports/ovr-v58-holdout-2025-26
for fit in A B; do for sc in 0.5 1.0; do
  d=$H/fit$fit-scale$sc; common="--rapm $H/rapm-$fit.csv --possScale $sc"
  python $H/calibrate-wing.py --direction E2 $common --out $d/E2 >/dev/null
  python $H/calibrate-wing.py --direction G1 --gamma 0.5 --restrictPos PF,C $common --out $d/F2 >/dev/null
  python $H/calibrate-wing.py --direction G3 --gamma 1.0 --delta 0.25 $common --out $d/G3 >/dev/null
  python $H/calibrate-wing.py --direction H1 --capMargin 0 $common --out $d/H1-m0 >/dev/null
done; done
