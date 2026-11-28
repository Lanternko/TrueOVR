#!/bin/bash
# usage: chain246.sh <ARM:V328|W246> <WIN:328|246> (repo root)；ARM 的 tail／usage／def-L 用同窗口版
set -e
ARM=$1; WIN=$2; P="reports/card-0.2.12c-fit246"
export E185_WORK="$(pwd)/$P/work/$ARM/A" E185_TAIL_U="$(pwd)/$P/tail-${ARM}full.csv" E202_ARM=$ARM
export DEFL_DIR="$(pwd)/$P/defL-$WIN" E207_USAGE="$(pwd)/$P/usage-window-c82-$WIN.csv"
python -I -B -X utf8 $P/build_kg.py cards KG 2025-26 </dev/null
python -I -B -X utf8 $P/run_i.py KG </dev/null
python -I -B -X utf8 $P/finalize.py $ARM </dev/null
