#!/bin/bash
# usage: chain.sh <ARM>  (repo root)
set -e
ARM=$1; P="reports/card-0.2.12+E206-to-touches"
export E185_WORK="$(pwd)/$P/work/$ARM/A" E185_TAIL_U="$(pwd)/$P/tail-$ARM.csv" E202_ARM=$ARM
python -I -B -X utf8 $P/build_kg.py cards KG 2025-26 </dev/null
python -I -B -X utf8 $P/run_i.py KG </dev/null
python -I -B -X utf8 $P/finalize.py $ARM </dev/null
