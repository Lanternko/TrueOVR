"""E-175 健全性檢查：V 臂在 46.7% 切點的「比率層」MAE 對 backtest.json 方法 c 的測試 MAE（V61 以 half 欄切 H1／H2，這裡以日期序前 574 場切，應很接近）。"""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e175_lib as L, e175_card as C
D = L.Data(); inp = C.load_inputs(); bt = inp['bt']
by = L.positions_by(); S = L.TEST
posv = np.array([L.pos_lookup(by, p, S) for p in D.pids])
g = 574
res = {}
for a in ('ft', 'foulDraw', 'tovSkill', 'pass', 'rebound', 'mid', 'short'):
    fc = bt['production'][a]['fit']
    n, d = D.tab[S][a].agg(g, 10**9)
    sel = np.nonzero(d >= L.MIN_D2[a])[0]
    m = L.causal_prior(D, a, S, g, fc['prior'], posv)
    r = L.v_rate(D, a, S, g, fc, m)
    mae = float(np.abs(r[sel] - n[sel] / d[sel]).mean())
    res[a] = {'n': int(len(sel)), 'mae_mine': round(mae, 5), 'mae_backtest_json_c': round(bt['attrs'][a]['methods']['c']['mae'], 5), 'n_json': bt['attrs'][a]['n']}
    print(a, res[a])
Path(__file__).with_name('check_rate_level.json').write_text(json.dumps(res, indent=1), encoding='utf-8')
