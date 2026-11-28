#!/bin/bash
# 把 5090 上跑完的板拉回本機（只拉 checkpoint，不覆蓋本機程式碼）。
#   bash reports/ovr-v55-finisher-fix-2025-26/pull-5090.sh B12 [B1 ...]
set -eu
H=kojiek@140.122.184.29
R=side_projects/basketball-v55fix-20261019/reports/ovr-v55-finisher-fix-2025-26
L=reports/ovr-v55-finisher-fix-2025-26
for m in "$@"; do
  n=$(ssh -o BatchMode=yes $H "wc -l < $R/$m/checkpoint-both-s8.jsonl" | tr -d ' \r')
  if [ "$n" != "582" ]; then echo "$m: only $n/582 rows, skip"; continue; fi
  mkdir -p "$L/$m"
  ssh -o BatchMode=yes $H "cat $R/$m/checkpoint-both-s8.jsonl" > "$L/$m/checkpoint-both-s8.jsonl"
  echo "$m: pulled $(wc -l < "$L/$m/checkpoint-both-s8.jsonl") rows"
done
