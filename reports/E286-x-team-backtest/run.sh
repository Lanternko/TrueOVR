#!/bin/bash
# 5090：~/side_projects/pure_ovr/experiments/e286/reports/E286-x-team-backtest
set -e
cd "$(dirname "$0")"
PY=~/venvs/jev-hearthstone/bin/python
[ "$(sha256sum prereg.md | cut -d' ' -f1)" = "$(tr -d "
 " < prereg.sha256)" ] || { echo prereg mismatch; exit 1; }
for last in 2023-24 2024-25; do for arm in B X; do $PY -I -X utf8 train.py --arm $arm --last $last; done; done
for arm in B X; do
  $PY -I -X utf8 predict.py --arm $arm --key 2425 --last 2023-24 --prior 2023-24 --out work/pred-$arm-2425-prior.json
  $PY -I -X utf8 predict.py --arm $arm --key 2526 --last 2024-25 --prior 2024-25 --out work/pred-$arm-2526-prior.json
  $PY -I -X utf8 predict.py --arm $arm --key 2425 --last 2023-24 --prior 2024-25 --out work/pred-$arm-2425-same.json
  $PY -I -X utf8 predict.py --arm $arm --key 2526 --last 2024-25 --prior 2025-26 --out work/pred-$arm-2526-same.json
done
echo ALLDONE
