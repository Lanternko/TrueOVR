#!/bin/bash
# usage（5090，repo 根目錄）：bash reports/defense-update-speed/work/remote_desc.sh；描述用 2026-27 三臂 × 6 shards，結束寫 out/DONE-desc
O=reports/defense-update-speed/work/out; NODE=/home/kojiek/.nvm/versions/node/v22.13.1/bin/node
for a in A0 A1 A2; do for ((s=0;s<6;s++)); do
  timeout 3000 $NODE scripts/team_ratings_sim.mjs "$O/desc-in-$a.json" $s 6 "$O/desc-sim-$a-$s.json" 200 </dev/null >"$O/desc-sim-$a-$s.log" 2>&1 &
done; done
wait
echo ALLDONE > "$O/DONE-desc"
