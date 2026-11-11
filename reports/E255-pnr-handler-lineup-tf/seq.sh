#!/bin/bash
# E-255：GPU 有約 28GB 空閒，三條平行逐臂跑，遇錯（OOM）等 60 秒重試。
cd ~/side_projects/pure_ovr/experiments/e255
PY=~/venvs/jev-hearthstone/bin/python
export E225_STINT_DIR=/home/kojiek/side_projects/pure_ovr/experiments/e225/data PYTHONIOENCODING=utf-8 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
rm -f DONE FAILED
run() { for arm in "$@"; do for try in 1 2 3 4 5 6; do [ -f out-$arm.json ] && break
  $PY -I -B -X utf8 fit_e255.py $arm >> log-$1.txt 2>&1 || { echo "retry $arm $try" >> log-$1.txt; sleep 60; }; done; done; }
run T0 W04 W08 & run W00 W05 W10 & run W02 W06 WL & wait
n=$(ls out-*.json 2>/dev/null | wc -l)
if [ "$n" -ge 9 ]; then touch DONE; else touch FAILED; fi
