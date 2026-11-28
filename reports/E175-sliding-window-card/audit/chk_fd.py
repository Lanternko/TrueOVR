"""E-175 稽核 3(e)：foulDraw 比率層 MAE 0.0544 vs 0.0516 的原因（H1 切法：日期序前574場 vs half 欄）。"""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ac
db = ac.DB(); inp = ac.load_inputs(); bt = inp['bt']
S = '2025-26'
by = ac.positions(); posv = [ac.pos_of(by, p, S) for p in db.pids]
h1 = db.h1[S]
res = {'games': int(db.G[S]), 'half1_games': int(h1.sum()), 'half1_is_first_574_by_date': bool(h1[:574].all() and not h1[574:].any()),
       'half1_positions_not_in_first574': int((~h1[:574]).sum()), 'half2_in_first574_count': int((~h1[:574]).sum()), 'half1_after574': int(h1[574:].sum())}

def mask_agg(t, m):
    return ac.Chain._mask_agg(db, S, t, m)

out = {}
for a in ('ft', 'foulDraw', 'tovSkill', 'pass', 'rebound', 'mid', 'short'):
    fc = bt['production'][a]['fit']
    row = {'json_c': bt['attrs'][a]['methods']['c']['mae'], 'n_json': bt['attrs'][a]['n']}
    for nm, m1 in (('date574', np.arange(db.G[S]) < 574), ('halfcol', h1)):
        m2 = ~m1
        n1, d1 = mask_agg(a, m1); n2, d2 = mask_agg(a, m2)
        sel = np.nonzero(d2 >= ac.MIN_D2[a])[0]
        # prior：H1 的聯盟／同位置
        mm = ac.prior(n1, d1, fc['prior'], posv)
        T = ac.hist_T(db, a, S, mm, fc['lam'], fc['kh'])
        r = ac.shrink(n1, d1, T, fc['k'])
        row[nm] = {'n': int(len(sel)), 'mae': float(np.abs(r[sel] - n2[sel] / d2[sel]).mean())}
    out[a] = row
    print(a, {k: (round(v['mae'], 5), v['n']) if isinstance(v, dict) else v for k, v in row.items()})
res['rate_level'] = out
# foulDraw 差異來源：半季分割是否是「前半季」?
import collections
res['note'] = 'half 欄是否為日期序前半'
print(res)
Path(__file__).with_name('audit_fd.json').write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding='utf-8')
