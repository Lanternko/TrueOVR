#!/bin/bash
# E-312（5090）：~/side_projects/pure_ovr/experiments/e312（資料讀 ../e306）。gq 送出；中斷後同指令重跑自動接續。
set -e
cd "$(dirname "$0")"
PY=~/venvs/gtzan/bin/python
[ "$(sha256sum prereg.md | cut -d' ' -f1)" = "$(tr -d '\r\n ' < prereg.sha256)" ] || { echo prereg mismatch; exit 1; }
for test in mock cut; do for arm in B TG; do $PY -I -X utf8 e312_train.py --arm $arm --test $test >> train.log 2>&1; done; done
$PY -I -X utf8 e312_predict_mock.py >> predict.log 2>&1
touch DONE; echo ALLDONE
