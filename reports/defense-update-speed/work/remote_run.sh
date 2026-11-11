#!/bin/bash
# usage（5090，repo 根目錄）：bash reports/defense-update-speed/work/remote_run.sh <arms-季.json> <tag> [S=200]；18 shards，結束寫 out/DONE-<tag>
in=$1; tag=$2; S=${3:-200}; N=18; O=reports/defense-update-speed/work/out
NODE=/home/kojiek/.nvm/versions/node/v22.13.1/bin/node
for ((s=0;s<N;s++)); do
  timeout 3000 $NODE reports/defense-update-speed/work/run_arms.mjs "$in" $s $N "$O/sim-${tag}-$s.json" $S </dev/null >"$O/sim-${tag}-$s.log" 2>&1 &
done
wait
echo ALLDONE $tag > "$O/DONE-$tag"
