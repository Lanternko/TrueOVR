#!/bin/bash
set -e
cd "$(dirname "$0")"
PY=~/venvs/jev-hearthstone/bin/python
export E227_SRC=$PWD/frozen_src
$PY e287_swap.py --prior 2022-23 --weights results-T2223/weights/T2223-{}.pt --pool pool-2022-23.json --out t-2022-23.json
$PY e287_swap.py --prior 2023-24 --weights results-T2324/weights/T2324-{}.pt --pool pool-2023-24.json --out t-2023-24.json
$PY e287_swap.py --prior 2024-25 --weights w2425/T2425-{}.pt --pool pool-2024-25.json --out t-2024-25.json
$PY e287_swap.py --prior 2025-26 --weights wfull/R2-stats-{}.pt --pool pool-2025-26.json --out t-2025-26.json
echo ALLDONE
