#!/bin/bash
# usage: runloop.sh <worktree-name> <START> <out.csv> <logfile>
name=$1; start=$2; out=$3; log=$4
export PYTHONIOENCODING=utf-8 E211_START=$start E211_CUTOFF="2026-11-02 12:00"
export E211_ROOT="D:/Projects/CODING/_wt/$name"
last=""
for i in $(seq 1 15); do
  python -I /d/Projects/CODING/basketball-autochess/reports/E211-rookie-gap-attribution/run_h.py "$out" > "$log" 2>&1
  if grep -q "^has_creation_override" "$log"; then echo DONE >> "$log"; exit 0; fi
  miss=$(grep -o "FileNotFoundError.*" "$log" | grep -o "reports[^']*" | sed 's#\\#/#g' | head -1)
  d=$(echo "$miss" | cut -d/ -f1-2)
  if [ -z "$d" ] || [ "$d" == "$last" ]; then echo GIVEUP >> "$log"; exit 1; fi
  last=$d
  (cd /d/Projects/CODING && E211_ROOT="D:/Projects/CODING/_wt/$name" python -I _wt/sync_missing.py "$d" | tail -1)
done
