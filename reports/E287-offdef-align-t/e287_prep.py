"""E-287 步驟 1：每個原點 t 的球員池＋現行 OFF0／DEF0（E-277 M1 卡，R-179 基準）。
池＝t 季卡 MIN≥500 且名字唯一對上 playerId（同 E-269／E-274 規則）。輸出 pool-<t>.json、cur-<t>.json。
  python -I -B -X utf8 reports/E287-offdef-align-t/e287_prep.py"""
import csv, importlib.util, json, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
s = importlib.util.spec_from_file_location('e269_eval', ROOT / 'reports/E269-def-coef-pooling/e269_eval.py')
X = importlib.util.module_from_spec(s); sys.modules['e269_eval'] = X; s.loader.exec_module(X)
SN, P = X.SN, X.P
E277 = ROOT / 'reports/E277-help-monotone'


def cur(t):
    card = list(csv.DictReader(open(E277 / f'ranking-M1-{t}.csv', encoding='utf-8-sig')))
    coef = {}
    for ps in {r['pos'] for r in card}:
        g = [r for r in card if r['pos'] == ps]
        A = np.c_[np.ones(len(g)), [[float(r[a]) for a in SN.OD_ALL] for r in g]]
        coef[ps] = np.linalg.lstsq(A, np.array([float(r['pred0']) for r in g]), rcond=None)[0]
    q = [r for r in card if float(r['MIN']) >= 500]
    mu = {a: np.mean([float(r[a]) for r in q]) for a in SN.OD_ALL}
    mub = np.mean([float(r['defenseBonus']) for r in q])
    pop, _ = P.pop_of(t)
    n2 = {}
    for p, i in pop.items():
        n2.setdefault(P.norm(i['name']), []).append(p)
    out = {}
    for r in q:
        ids = n2.get(P.norm(r['name'])) or []
        if len(ids) != 1:
            continue
        c = lambda attrs: float(sum(coef[r['pos']][1 + SN.OD_ALL.index(a)] * (float(r[a]) - mu[a]) for a in attrs))
        out[str(ids[0])] = {'name': r['name'], 'pos': r['pos'], 'ovr': float(r['ovr']), 'MIN': float(r['MIN']),
                            'off0': c(SN.OD_OFF), 'def0': c(SN.OD_DEF) + float(r['defenseBonus']) - mub}
    return out


for t in ['2022-23', '2023-24', '2024-25', '2025-26']:
    d = cur(t)
    json.dump(sorted(d), open(HERE / f'pool-{t}.json', 'w'))
    json.dump(d, open(HERE / f'cur-{t}.json', 'w', encoding='utf-8'), ensure_ascii=False)
    print(t, len(d))
