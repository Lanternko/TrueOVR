#!/bin/bash
# usage: chain246.sh <ARM:V328|W246> <WIN:328|246> (repo root)；ARM 的 tail／usage／def-L 用同窗口版
set -e
ARM=$1; WIN=$2; P="reports/card-0.2.15-fit"; F="reports/card-0.2.12c-fit246"   # card 0.2.15：defL／usage 沿用 fit246；tail 換 creation＝持球進攻合成值
export E185_WORK="$(pwd)/$P/work/$ARM/A" E185_TAIL_U="$(pwd)/$P/tail-${ARM}full-crtpnr.csv" E202_ARM=$ARM
export DEFL_DIR="$(pwd)/$F/defL-$WIN" E207_USAGE="$(pwd)/$F/usage-window-c82-$WIN.csv"
python -I -B -X utf8 $P/build_kg.py cards KG 2025-26 </dev/null
python -I -B -X utf8 $P/run_i.py KG </dev/null
python -I -B -X utf8 $P/finalize.py $ARM </dev/null
