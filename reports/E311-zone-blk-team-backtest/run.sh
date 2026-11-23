#!/bin/bash
# 5090：~/side_projects/pure_ovr/experiments/e311/reports/E311-zone-blk-team-backtest（gq 送出；重跑同指令自動接續）
set -e
cd "$(dirname "$0")"
PY=~/venvs/jev-hearthstone/bin/python
[ "$(sha256sum prereg.md | cut -d' ' -f1)" = "$(tr -d '\r\n ' < prereg.sha256)" ] || { echo prereg mismatch; exit 1; }
for last in 2023-24 2024-25; do for arm in B Z2 TG ZG; do $PY -I -X utf8 train.py --arm $arm --last $last; done; done
for arm in B Z2 TG ZG; do
  $PY -I -X utf8 predict.py --arm $arm --key 2425 --last 2023-24 --prior 2023-24 --out work/pred-$arm-2425-prior.json
  $PY -I -X utf8 predict.py --arm $arm --key 2526 --last 2024-25 --prior 2024-25 --out work/pred-$arm-2526-prior.json
  $PY -I -X utf8 predict.py --arm $arm --key 2425 --last 2023-24 --prior 2024-25 --out work/pred-$arm-2425-same.json
  $PY -I -X utf8 predict.py --arm $arm --key 2526 --last 2024-25 --prior 2025-26 --out work/pred-$arm-2526-same.json
done
touch DONE; echo ALLDONE
