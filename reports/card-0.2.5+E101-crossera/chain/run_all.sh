#!/usr/bin/env bash
# E-101 卡片鏈：calibrate-wing → build_card_022 → e084 --target season → evaluate → compare（從 repo 根目錄執行）
set -u
D=reports/card-0.2.5+E101-crossera
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8
python -I -B $D/chain/run_cards.py e101,e101z,e101g,e101w > $D/cards.log 2>&1 </dev/null; echo "cards exit $?" > $D/season.exit
for v in e101 e101z e101g e101w; do
  python -I -B $D/chain/build_card_022.py $v >> $D/cards.log 2>&1 </dev/null; echo "build022 $v exit $?" >> $D/season.exit
  E090_VARIANT=$v python -I -B $D/chain/e084.py --target season > $D/season-$v.log 2>&1 </dev/null; echo "$v exit $?" >> $D/season.exit
done
node $D/chain/evaluate.mjs > $D/evaluate.log 2>&1 </dev/null; echo $? > $D/evaluate.exit
for v in e101 e101z e101g e101w; do
  E101_CAND=$v python -I -B $D/chain/compare.py > $D/compare-$v.log 2>&1 </dev/null; echo "compare $v exit $?" >> $D/season.exit
done
echo done >> $D/season.exit
