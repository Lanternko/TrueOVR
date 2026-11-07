#!/bin/bash
# usage: remote_run.sh <job> <variant> <seeds> <tag>   (run from repo root on the 5090; 18 shards)
job=$1; v=$2; S=$3; tag=$4; N=18
mkdir -p reports/E208-team-rating/results
for ((s=0;s<N;s++)); do
  node reports/E208-team-rating/run.mjs "$job" "$v" $s $N "reports/E208-team-rating/results/${tag}-$s.json" $S </dev/null >"reports/E208-team-rating/results/${tag}-$s.log" 2>&1 &
done
wait
echo ALLDONE $tag
