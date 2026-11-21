#!/bin/bash
# 5090 上從 repo 根目錄跑：reports/star-overlap/remote_run.sh <seeds> <workers>；結束寫 results/DONE
S=${1:-1000}; N=${2:-10}; export PATH=/home/kojiek/.nvm/versions/node/v22.13.1/bin:$PATH
mkdir -p reports/star-overlap/results; rm -f reports/star-overlap/results/DONE
for ((s=0;s<N;s++)); do
  ( for se in 2425 2526; do nice -n 10 node reports/star-overlap/run.mjs $se $s $N reports/star-overlap/results/S$se-$s.json $S </dev/null >reports/star-overlap/results/S$se-$s.log 2>&1; done ) &
done
wait
date -u +%FT%TZ > reports/star-overlap/results/DONE
