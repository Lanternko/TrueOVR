"""E-274 步驟 1：每折球員池（t 季卡 MIN≥500 且名字唯一）→ pool-<t>.json。python -I -B -X utf8 reports/E274-def-display-transformer/e274_prep.py"""
import importlib.util, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
s = importlib.util.spec_from_file_location('e269_eval', ROOT / 'reports/E269-def-coef-pooling/e269_eval.py')
X = importlib.util.module_from_spec(s); sys.modules['e269_eval'] = X; s.loader.exec_module(X)
for t in ['2022-23', '2023-24', '2024-25']:
    d = X.load('A0', t)
    json.dump([str(p) for p in d['ids']], open(HERE / f'pool-{t}.json', 'w'))
    print(t, len(d['ids']))
