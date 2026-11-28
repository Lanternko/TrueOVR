"""E-142 Phase 0 c0d：T1 自製 EPM 式（epm_live.py 方法套回舊季），只用 t 季以前的資料定先驗／權重／噪音，t 季只提供 box 與 stints。
  生涯先驗  t 季前最近 3 個有 stints 的季合併 RAPM（pooled O/D、poss）；
  box 先驗  同窗口 box 每百回合特徵（11 項＋log 場均分鐘）嶺迴歸對 pooled O/D，λ 由 5 折 CV 選；套到 t 季 box；
  合併      精度加權：生涯方差 c/poss，c ＝ Σ(窗口末季單季−pooled)² ÷ Σ(1/L−1/P)（L≥1000）；box 方差＝訓練殘差² − c/poss 的加權平均（下限 0.05）；
  RAPM      rapm.fit_rapm 只用 t 季 stints，先驗＝上列合併值。
與 epm_live.py 的差異：沒有 Poisson 抽樣收縮與角色先驗、沒有 height／receivedFgm／onoffSaved 特徵，權重不用 2025-26 凍結值而在窗口內重擬合。
用法：python -I t1_epm_old.py <季>   輸出 data/external-impact/epm_self/epm_<季>.csv 與 .json
"""
import csv, importlib.util, json, sys
from collections import defaultdict
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data/external-impact/epm_self'
ALL = ['2014-15', '2015-16', '2016-17', '2017-18', '2018-19', '2019-20', '2020-21', '2022-23', '2023-24', '2024-25', '2025-26']
SUM = ['PTS', 'FGM', 'FGA', 'FG3A', 'FTA', 'AST', 'TOV', 'OREB', 'DREB', 'STL', 'BLK', 'PF']


def _rapm():
    spec = importlib.util.spec_from_file_location('rapm_mod', ROOT / 'reports/impact-rapm/rapm.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def stints(s):
    return ROOT / ('reports/defense-b1/stints.jsonl' if s == '2025-26' else f'reports/defense-seventh/{s}/stints/stints.jsonl')


def games(s):
    return ROOT / ('data/season-source/player-games.json' if s == '2025-26' else f'data/defense-seventh/{s}/player-games.json')


def season_box(s):
    d = json.loads(games(s).read_text(encoding='utf-8'))['data']['resultSets'][0]
    h = {k: i for i, k in enumerate(d['headers'])}
    rows = [r for r in d['rowSet'] if r[h['MIN']]]
    team = defaultdict(lambda: defaultdict(float))
    for r in rows:
        t = team[r[h['TEAM_ID']]]
        t['poss'] += r[h['FGA']] - r[h['OREB']] + r[h['TOV']] + 0.44 * r[h['FTA']]
        t['min'] += r[h['MIN']]
    acc = {}
    for r in rows:
        t = team[r[h['TEAM_ID']]]
        a = acc.setdefault(r[h['PLAYER_ID']], {'name': r[h['PLAYER_NAME']], 'poss': 0.0, 'MIN': 0.0, 'GP': 0, **{k: 0.0 for k in SUM}})
        a['poss'] += r[h['MIN']] * t['poss'] / (t['min'] / 5)
        a['MIN'] += r[h['MIN']]
        a['GP'] += 1
        for k in SUM:
            a[k] += r[h[k]] or 0
    return {p: a for p, a in acc.items() if a['poss'] > 0}


def merge_box(bs):
    out = {}
    for b in bs:
        for p, a in b.items():
            o = out.setdefault(p, {'name': a['name'], 'poss': 0.0, 'MIN': 0.0, 'GP': 0, **{k: 0.0 for k in SUM}})
            for k in ['poss', 'MIN', 'GP'] + SUM:
                o[k] += a[k]
    return out


def feats(a):
    per = lambda k: a[k] / a['poss'] * 100
    return [per('PTS'), (a['FGA'] + 0.44 * a['FTA']) / a['poss'] * 100, per('FG3A'), per('FTA'), per('AST'), per('TOV'),
            per('OREB'), per('DREB'), per('STL'), per('BLK'), per('PF'), float(np.log(max(a['MIN'] / a['GP'], 3.0)))]


def wridge(X, y, w, lam):
    A = np.c_[np.ones(len(X)), X]
    P = lam * np.eye(A.shape[1])
    P[0, 0] = 0
    return np.linalg.solve(A.T @ (w[:, None] * A) + P, A.T @ (w * y))


def run(t):
    rapm = _rapm()
    prev = [s for s in ALL[:ALL.index(t)] if stints(s).exists()][-3:]
    assert len(prev) == 3, prev
    obs_w = list(rapm.observations(prev))
    pl_w = sorted({p for o in obs_w for p in o[2] + o[3]})
    pooled, info_p = rapm.fit_rapm(obs_w, pl_w)
    obs_l = [o for o in obs_w if o[0] == prev[-1]]
    pl_l = sorted({p for o in obs_l for p in o[2] + o[3]})
    last, _ = rapm.fit_rapm(obs_l, pl_l)
    c = {}
    for side in 'OD':
        num = den = 0.0
        for p, r in pooled.items():
            q = last.get(p)
            if not q or q['poss'] < 1000 or r['poss'] <= q['poss']:
                continue
            num += (q[side] - r[side]) ** 2
            den += 1 / q['poss'] - 1 / r['poss']
        c[side] = num / den
    box_w = merge_box([season_box(s) for s in prev])
    tr = [p for p in pooled if p in box_w and pooled[p]['poss'] >= 1000 and box_w[p]['GP'] >= 10]
    X = np.array([feats(box_w[p]) for p in tr])
    mu, sd = X.mean(0), X.std(0) + 1e-9
    Z = (X - mu) / sd
    w = np.array([min(pooled[p]['poss'], 20000) for p in tr])
    w = w / w.mean()
    fold = np.random.RandomState(0).randint(0, 5, len(tr))
    pp = np.array([pooled[p]['poss'] for p in tr])
    model, boxerr = {}, {}
    for side in 'OD':
        y = np.array([pooled[p][side] for p in tr])
        best = None
        for lam in [1, 10, 30, 100, 300, 1000]:
            sse = 0.0
            for f in range(5):
                m = fold != f
                b = wridge(Z[m], y[m], w[m], lam)
                sse += float(np.sum(w[~m] * (y[~m] - np.c_[np.ones((~m).sum()), Z[~m]] @ b) ** 2))
            if best is None or sse < best[0]:
                best = (sse, lam)
        b = wridge(Z, y, w, best[1])
        model[side] = (b, best[1])
        res = (y - np.c_[np.ones(len(Z)), Z] @ b) ** 2 - c[side] / pp
        boxerr[side] = max(0.05, float(np.average(res, weights=w)))
    box_t = season_box(t)
    prior = {}
    for p, a in box_t.items():
        z = (np.array(feats(a)) - mu) / sd
        pr = []
        for side in 'OD':
            b = model[side][0]
            bx = float(b[0] + z @ b[1:])
            vb = boxerr[side]
            q = pooled.get(p)
            if q is not None and q['poss'] > 0:
                vc = c[side] / q['poss']
                pr.append((bx / vb + q[side] / vc) / (1 / vb + 1 / vc))
            else:
                pr.append(bx)
        prior[p] = tuple(pr)
    obs_t = list(rapm.observations([t]))
    pl_t = sorted({p for o in obs_t for p in o[2] + o[3]})
    fit, info = rapm.fit_rapm(obs_t, pl_t, prior)
    OUT.mkdir(parents=True, exist_ok=True)
    rows = [(p, box_t[p]['name'] if p in box_t else '', fit[p]['O'], fit[p]['D'], fit[p]['net'], fit[p]['poss']) for p in pl_t]
    with open(OUT / f'epm_{t}.csv', 'w', encoding='utf-8', newline='') as fh:
        w_ = csv.writer(fh)
        w_.writerow(['playerId', 'name', 'O', 'D', 'net', 'stintPoss'])
        for r in rows:
            w_.writerow([r[0], r[1], round(r[2], 4), round(r[3], 4), round(r[4], 4), round(r[5], 1)])
    meta = {'season': t, 'windowSeasons': prev, 'rapmLambdaWindow': info_p.get('lambda'), 'rapmLambdaSeason': info.get('lambda'),
            'boxRidgeLambda': {s: model[s][1] for s in 'OD'}, 'trainingPlayers': len(tr), 'players': len(rows),
            'playersNoName': sum(1 for r in rows if not r[1])}
    (OUT / f'epm_{t}.json').write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding='utf-8')
    return meta


if __name__ == '__main__':
    print(json.dumps(run(sys.argv[1]), ensure_ascii=False))
