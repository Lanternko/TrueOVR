#!/bin/bash
# usage: calibrate.sh <kc0> <kp0>   (run from repo root on the 5090). League-total fixed-point calibration only.
cd "$(dirname "$0")/../../.."
kc=$1; kp=$2; SEEDS=20261012,20261013,20261014; OUT=reports/handle-E069/sim/runs
for i in 1 2 3 4 5 6; do
  tag=cal$i
  node reports/handle-E069/sim/run.mjs $OUT $tag $kc $kp $SEEDS 3 > $OUT/$tag.log 2>&1
  res=$(python3 reports/handle-E069/sim/tally.py $OUT/$tag-20261012.json $OUT/$tag-20261013.json $OUT/$tag-20261014.json)
  echo "iter $i kCtl=$kc kPass=$kp -> $res" | tee -a $OUT/calibration.log
  read ok nkc nkp < <(python3 - "$res" $kc $kp <<'P'
import json,sys
o=json.loads(sys.argv[1]);kc=float(sys.argv[2]);kp=float(sys.argv[3]);n=o['games']/1230
c=o['ctl']/n;p=o['pass']/n
ec=c/13686-1;ep=p/16910-1
print('1' if abs(ec)<=.01 and abs(ep)<=.01 else '0',kc*13686/c,kp*16910/p)
P
)
  echo "   ok=$ok next=$nkc,$nkp" | tee -a $OUT/calibration.log
  [ "$ok" = 1 ] && { echo "FINAL $kc $kp" | tee -a $OUT/calibration.log; exit 0; }
  kc=$nkc; kp=$nkp
done
echo "NOT CONVERGED $kc $kp" | tee -a $OUT/calibration.log
