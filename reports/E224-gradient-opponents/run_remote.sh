#!/bin/bash
# usage: run_remote.sh <jobs.json> <B5|A5> <tag>   （在 5090 repo 根執行；18 shards；完成寫 reports/E224-gradient-opponents/work/<tag>.DONE）
J=$1; M=$2; T=$3; N=18
NODE=/home/kojiek/.nvm/versions/node/v22.13.1/bin/node
D=reports/E224-gradient-opponents
mkdir -p $D/work/out-$T
pids=()
for s in $(seq 0 $((N-1))); do
  $NODE $D/e224_sim.mjs $J $M $s $N $D/work/out-$T/o-$s.json > $D/work/out-$T/l-$s.log 2>&1 &
  pids+=($!)
done
fail=0
for p in "${pids[@]}"; do wait $p || fail=1; done
if [ $fail -eq 0 ]; then touch $D/work/$T.DONE; else touch $D/work/$T.FAILED; fi
