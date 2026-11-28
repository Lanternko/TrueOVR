#!/bin/bash
# 用法（repo root）：bash <本檔> <K0|A>  → 四個原點依序 cards + run；log 在 logs/
E=reports/E180-pass-pool-creation-interact
for t in 2025-26 2024-25 2023-24 2022-23; do
  python -I -B -X utf8 $E/e180_build.py cards $1 $t > $E/logs/cards-$1-$t.log 2>&1 || { echo "cards $1 $t FAIL"; exit 1; }
  python -I -B -X utf8 $E/e180_build.py run $1 $t > $E/logs/run-$1-$t.log 2>&1 || { echo "run $1 $t FAIL"; exit 1; }
  echo "$1 $t done"
done
