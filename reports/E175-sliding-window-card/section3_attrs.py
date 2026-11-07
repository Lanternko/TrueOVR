"""E-175 §3 第一步：2025-26 季末 U 卡的 8 項屬性（同一條映射鏈），與 V（0.2.9a）比 SD。輸出 section3-attrs.csv、section3-attrs.json。"""
import csv, json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e175_lib as L, e175_card as C
H = Path(__file__).resolve().parent
D = L.Data(); inp = C.load_inputs()
V = C.card_chain(D, inp, 'V'); U = C.card_chain(D, inp, 'U')
pids, names = V['pids'], V['names']
mins = np.array([inp['rank_min'].get(n, 0) for n in names])
res = {'sd': {}}
for a in C.ATTRS8:
    v, u = V['mapped'][a], U['mapped'][a]
    m5 = mins >= 500
    res['sd'][a] = {'sdV': float(v.std()), 'sdU': float(u.std()), 'ratio': float(u.std() / v.std()),
                    'ratio_min500': float(u[m5].std() / v[m5].std()), 'n_min500': int(m5.sum()),
                    'meanDiff': float((u - v).mean()), 'maxAbsDiff': float(np.abs(u - v).max()), 'corr': float(np.corrcoef(u, v)[0, 1]),
                    'maeUV': float(np.abs(u - v).mean())}
    print(f"{a:9s} SD V={v.std():6.2f} U={u.std():6.2f} ratio={u.std()/v.std():.3f} (MIN>=500: {res['sd'][a]['ratio_min500']:.3f}) mean(U-V)={(u-v).mean():+.2f} corr={res['sd'][a]['corr']:.3f} MAE(U,V)={res['sd'][a]['maeUV']:.2f}")
res['allInBand'] = all(0.9 <= x['ratio'] <= 1.1 for x in res['sd'].values())
res['outOfBand'] = [a for a, x in res['sd'].items() if not 0.9 <= x['ratio'] <= 1.1]
print('all in [0.9,1.1]:', res['allInBand'], res['outOfBand'])
res['info'] = {'U': U['info'], 'V': V['info']}
(H / 'section3-attrs.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
with open(H / 'section3-attrs.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['playerId', 'name', 'MIN'] + [f'{a}_{x}' for a in C.ATTRS8 for x in ('V', 'U')])
    for i, p in enumerate(pids):
        w.writerow([p, names[i], mins[i]] + [round(float(V['mapped'][a][i] if x == 'V' else U['mapped'][a][i]), 4) for a in C.ATTRS8 for x in ('V', 'U')])
