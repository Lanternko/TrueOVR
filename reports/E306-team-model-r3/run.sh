#!/bin/bash
# E-306：六個訓練臂（各 5 seed，已完成的 seed 會跳過）＋測試 M 預測。中斷後同指令重跑自動接續。
cd ~/side_projects/pure_ovr/experiments/e306 || exit 1
PY=~/venvs/gtzan/bin/python
export E227_SRC=$PWD/e227_src
for arm in mock mockw3 cut cutw3 full fullw3; do
  $PY e306_train.py --arm $arm >> train.log 2>&1 || exit 1
done
[ -f results/pred-mock.json ] || $PY e306_predict_mock.py >> predict.log 2>&1 || exit 1
touch DONE
