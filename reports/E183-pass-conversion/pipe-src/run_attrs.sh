#!/bin/bash
# 用法（repo root）：bash <本檔> <P50|Q>   P50＝重現 E-125（對照用）；Q＝conv
P=reports/E183-pass-conversion/work/pipe
if [ "$1" = Q ]; then export E183_CONV=1; fi
python -I -B -X utf8 $P/pool_data_p.py 0.5 </dev/null > reports/E183-pass-conversion/logs/pool-$1.log 2>&1 || { echo pool FAIL; exit 1; }
python -I -B -X utf8 $P/a0_p.py 0.5 </dev/null > reports/E183-pass-conversion/logs/a0-$1.log 2>&1 || { echo a0 FAIL; exit 1; }
python -I -B -X utf8 $P/build_e101_p.py 0.5 </dev/null > reports/E183-pass-conversion/logs/build-$1.log 2>&1 || { echo build FAIL; exit 1; }
echo done $1
