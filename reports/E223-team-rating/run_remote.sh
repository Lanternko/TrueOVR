#!/bin/bash
# usage: run_remote.sh <jobs.json> <tag>   （在 5090 repo 根執行；18 shards；完成寫 work/<tag>.DONE）
J=$1; T=$2; N=18
NODE=/home/kojiek/.nvm/versions/node/v22.13.1/bin/node
mkdir -p reports/E223-team-rating/work/out-$T
pids=()
for s in $(seq 0 $((N-1))); do
  $NODE reports/E223-team-rating/e223_sim.mjs $J $s $N reports/E223-team-rating/work/out-$T/o-$s.json > reports/E223-team-rating/work/out-$T/l-$s.log 2>&1 &
  pids+=($!)
done
fail=0
for p in "${pids[@]}"; do wait $p || fail=1; done
if [ $fail -eq 0 ]; then touch reports/E223-team-rating/work/$T.DONE; else touch reports/E223-team-rating/work/$T.FAILED; fi
