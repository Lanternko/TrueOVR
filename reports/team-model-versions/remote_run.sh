#!/bin/bash
# E-273：5090 部分。用法 bash remote_run.sh deploy|launch|wait|pull（在 repo 根目錄執行）。
# 遠端目錄 ~/side_projects/pure_ovr/experiments/team-model-versions/tree/（與本機同構的最小樹）。
set -e
HOST=kojiek@100.97.181.15; D=side_projects/pure_ovr/experiments/team-model-versions; SEEDS="229 230 231 232 233"
case "$1" in
deploy)
  L=reports/ovr-inseason-2026-27/live
  FL=$(ls $L | grep '^2026-1[01]-[0-9][0-9]$' | sed "s#^#$L/#")
  tar czf /tmp/tmv.tgz reports/E227-lineup-transformer-r2/*.py reports/E227-lineup-transformer-r2/data reports/E227-lineup-transformer-r2/results/weights \
    reports/E228-transformer-team-rating/t_lib.py reports/E228-transformer-team-rating/results/weights reports/E229-transformer-vs-m0-forward/e229_live.py \
    reports/ovr-inseason-2026-27/v5/cards/2024-25-v5-min.csv reports/ovr-inseason-2026-27/v5/cards/2023-24-v5-min.csv \
    data/season-source-2026-27/player-games.json data/matchup-source/2026-27 \
    reports/team-model-versions/run_t.py reports/team-model-versions/snap reports/team-model-versions/work/games.json reports/team-model-versions/work/rots.json \
    $(for f in $FL; do echo $f/ranking.csv $f/meta.json; done)
  ssh $HOST "mkdir -p ~/$D/tree && cd ~/$D/tree && tar xzf -" < /tmp/tmv.tgz ;;
launch)   # 每個種子一個程序（3 執行緒），全部結束後寫 work/DONE
  ssh $HOST "cd ~/$D/tree/reports/team-model-versions && rm -f work/DONE && PY=~/venvs/jev-hearthstone/bin/python && \
    (for s in $SEEDS; do NTHREADS=3 nohup \$PY -I -X utf8 run_t.py \$s > work/seed_\$s.log 2>&1 & done; \
     nohup bash -c 'while pgrep -f run_t.py >/dev/null; do sleep 10; done; touch work/DONE' >/dev/null 2>&1 &)" ;;
wait)
  until ssh $HOST "test -e ~/$D/tree/reports/team-model-versions/work/DONE"; do sleep 60; done ;;
pull)
  for s in $SEEDS; do scp $HOST:$D/tree/reports/team-model-versions/work/seed_$s.json reports/team-model-versions/work/; scp $HOST:$D/tree/reports/team-model-versions/work/seed_$s.log reports/team-model-versions/work/remote_seed_$s.log; done ;;
*) echo "usage: $0 deploy|launch|wait|pull"; exit 2 ;;
esac
