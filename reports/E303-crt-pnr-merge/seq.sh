#!/bin/bash
# E-303：四臂兩兩並行；OOM 等 60 秒重試。
B=~/side_projects/pure_ovr/experiments/e303
PY=~/venvs/jev-hearthstone/bin/python
export E225_STINT_DIR=/home/kojiek/side_projects/pure_ovr/experiments/e225/data PYTHONIOENCODING=utf-8 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd $B; rm -f DONE FAILED
run() { for arm in "$@"; do for try in 1 2 3 4 5 6; do [ -f out-$arm.json ] && break
  $PY -I -B -X utf8 fit_e303.py $arm >> log-$arm.txt 2>&1 || { echo "retry $arm $try" >> log-$arm.txt; sleep 60; }; done; done; }
run NOCRT MRG7 & run MRG5 MRG3 & wait
n=$(ls out-*.json 2>/dev/null | wc -l)
if [ "$n" -ge 4 ]; then touch DONE; else touch FAILED; fi
