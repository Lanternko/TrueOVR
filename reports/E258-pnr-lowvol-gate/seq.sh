#!/bin/bash
# E-258：三個變體子目錄各一條，逐臂跑；OOM 等 60 秒重試。
B=~/side_projects/pure_ovr/experiments/e258
PY=~/venvs/jev-hearthstone/bin/python
export E225_STINT_DIR=/home/kojiek/side_projects/pure_ovr/experiments/e225/data PYTHONIOENCODING=utf-8 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
rm -f $B/DONE $B/FAILED
run() { cd $B/$1; for arm in W04 W05 W06 W08; do for try in 1 2 3 4 5 6; do [ -f out-$arm.json ] && break
  $PY -I -B -X utf8 ../fit_e255.py $arm >> log.txt 2>&1 || { echo "retry $arm $try" >> log.txt; sleep 60; }; done; done; }
run G50 & run G100 & run REL & wait
n=$(ls $B/*/out-*.json 2>/dev/null | wc -l)
if [ "$n" -ge 12 ]; then touch $B/DONE; else touch $B/FAILED; fi
