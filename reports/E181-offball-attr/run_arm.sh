#!/bin/bash
# 用法（repo root）：bash <本檔> <臂> <原點>…  → 每個原點 cards + run；log 在 logs/
E=reports/E181-offball-attr
arm=$1; shift
for t in "$@"; do
  timeout 1200 python -I -B -X utf8 $E/e181_build.py cards $arm $t > $E/logs/cards-$arm-$t.log 2>&1 </dev/null || { echo "cards $arm $t FAIL"; exit 1; }
  timeout 1200 python -I -B -X utf8 $E/e181_build.py run $arm $t > $E/logs/run-$arm-$t.log 2>&1 </dev/null || { echo "run $arm $t FAIL"; exit 1; }
  echo "$arm $t done"
done
