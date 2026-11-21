#!/bin/bash
# E-302：三份快照逐日重算（同一把尺，最後一天也重算；假截止日 2026-11-09）。用法：bash reports/E302-attr-anchor/run_hist.sh（repo 根目錄）
cd "$(dirname "$0")/../.." || exit 1
E=reports/E302-attr-anchor
export HIST_REMOTE=kojiek@100.97.181.15 HIST_WORKERS=1 HIST_REMOTE_WORKERS=5
for a in r0 ra rap; do
  ( timeout 7200 python -I -X utf8 $E/live-$a/ovr_history.py $E/today-$a </dev/null > $E/hist-$a.log 2>&1; echo "rc=$?" >> $E/hist-$a.log ) &
  sleep 20
done
wait
grep -H "rc=\|wrote\|失敗\|Error" $E/hist-*.log
