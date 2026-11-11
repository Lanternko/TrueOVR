#!/bin/bash
# usage: remote_run_mc.sh <runner> <job> <variant> <seeds> <tag>  (repo root on the 5090; 18 shards; env E208_S / E208_FWD pass through)
runner=$1; job=$2; v=$3; S=$4; tag=$5; N=18
mkdir -p reports/E208-team-rating/results
for ((s=0;s<N;s++)); do
  node reports/E208-team-rating/$runner "$job" "$v" $s $N "reports/E208-team-rating/results/${tag}-$s.json" $S </dev/null >"reports/E208-team-rating/results/${tag}-$s.log" 2>&1 &
done
wait
echo ALLDONE $tag
