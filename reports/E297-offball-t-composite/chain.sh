#!/bin/bash
# E-297 5090 串接：單欄臂 seed 0-2 → 前向選擇（含 base、SEL 5 seed）→ 其餘 seed → eval → value（3 路平行）
set -u
cd ~/side_projects/pure_ovr/experiments/e297/reports/E297-offball-t-composite
PY=~/venvs/jev-hearthstone/bin/python
SINGLES=$(python3 -c "print(','.join('+'+c for c in ['cut36','cutPPP','offScr36','handoff36','spotup36','roll36','putback36','trans36','distOff36','speedOff','cs3a36','cs3pct']))")
$PY -I -X utf8 train.py --arms base --seeds 0,1,2 > train-base.log 2>&1
$PY -I -X utf8 train.py --arms "$SINGLES" --seeds 0,1,2 > train-singles.log 2>&1
$PY -I -X utf8 select_fwd.py > select.log 2>&1
$PY -I -X utf8 train.py --arms "base,$SINGLES,ALL" --seeds 0,1,2,3,4 > train-rest.log 2>&1
$PY -I -X utf8 eval.py > eval.log 2>&1
ARMS="base,$SINGLES,ALL,ALL#mask"
if $PY -c "import json;import sys;sys.exit(0 if json.load(open('results/sel.json'))['selected'] else 1)"; then ARMS="$ARMS,SEL"; fi
IFS=',' read -ra A <<< "$ARMS"; G0=""; G1=""; G2=""
for i in "${!A[@]}"; do case $((i % 3)) in 0) G0="$G0,${A[$i]}";; 1) G1="$G1,${A[$i]}";; 2) G2="$G2,${A[$i]}";; esac; done
$PY -I -X utf8 value.py --arms "${G0#,}" > value0.log 2>&1 &
$PY -I -X utf8 value.py --arms "${G1#,}" > value1.log 2>&1 &
$PY -I -X utf8 value.py --arms "${G2#,}" > value2.log 2>&1 &
wait
echo CHAIN_DONE > chain.done
