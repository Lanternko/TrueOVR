# E-135 m1: 30-team round robin x 3 seeds, ch1 vs legacy.
# (a) teammate on-court FG% error (sim - actual, percentage points) by role group; gap = mean(C) - mean(G); must shrink under ch1.
#     actual = v41 2025-26-player-validation.csv onTeammateFG_actual; players with actualMinutes >= 800 (same filter as profile.py).
# (b) team points per game RMSE vs OFF_RATING*PACE/100 (advanced-teams.json); ch1 must not be worse than legacy by > 0.2.
import csv, json, numpy as np
R = '../..'
ids = [t['id'] for t in json.load(open('../sim-0.1.0+E117-fatigue-off/team-ids.json', encoding='utf-8'))]
rs = json.load(open(R + '/data/defense-source/advanced-teams.json', encoding='utf-8'))['data']['resultSets'][0]
ix = {h: i for i, h in enumerate(rs['headers'])}
col = lambda k: {r[ix['TEAM_ID']]: float(r[ix[k]]) for r in rs['rowSet']}
ortg, pace = col('OFF_RATING'), col('PACE')
actPts = np.array([ortg[i] * pace[i] / 100 for i in ids])
V = {r['playerId']: r for r in csv.DictReader(open(R + '/reports/player-impact-v41/2025-26-player-validation.csv', encoding='utf-8-sig'))}
def load(m): return [json.loads(l) for l in open(f'm1-{m}.jsonl', encoding='utf-8') if l.strip()]
out = {'seeds': None, 'filter': 'actualMinutes>=800', 'modes': {}}
for m in ('legacy', 'ch1'):
    S = load(m); out['seeds'] = sorted(s['seed'] for s in S)
    P = np.zeros(30); N = np.zeros(30)
    for s in S:
        for g in s['games']: P[g['a']] += g['ptsA']; P[g['b']] += g['ptsB']; N[g['a']] += 1; N[g['b']] += 1
    pts = P / N; rmse = float(np.sqrt(((pts - actPts) ** 2).mean()))
    tm = {}
    for s in S:
        for p in s['onCourt']:
            t = tm.setdefault(str(p['id']), [0, 0]); t[0] += p['teammates']['fgm']; t[1] += p['teammates']['fga']
    err = {'G': [], 'F': [], 'C': []}; per = {}
    for pid, (fm, fa) in tm.items():
        v = V.get(pid)
        if not v or float(v['actualMinutes']) < 800 or fa == 0: continue
        e = 100 * fm / fa - float(v['onTeammateFG_actual']); err[v['roleGroup']].append(e); per[v['name']] = e
    mean = {k: float(np.mean(x)) for k, x in err.items()}
    out['modes'][m] = {'teamPtsRMSE': rmse, 'teamPtsMeanSim': float(pts.mean()), 'teamPtsMeanActual': float(actPts.mean()),
                       'teammateFGerr': mean, 'n': {k: len(x) for k, x in err.items()}, 'gapCminusG': mean['C'] - mean['G'],
                       'six': {n: per.get(n) for n in ['Rudy Gobert', 'Jalen Duren', 'Neemias Queta', 'Donovan Clingan', 'Mitchell Robinson', 'Scottie Barnes']}}
L, C = out['modes']['legacy'], out['modes']['ch1']
out['gate'] = {'gapShrinks': C['gapCminusG'] < L['gapCminusG'], 'rmseOk': C['teamPtsRMSE'] - L['teamPtsRMSE'] <= 0.2,
               'gapLegacy': L['gapCminusG'], 'gapCh1': C['gapCminusG'], 'rmseDiff': C['teamPtsRMSE'] - L['teamPtsRMSE']}
out['gate']['pass'] = out['gate']['gapShrinks'] and out['gate']['rmseOk']
A, B = load('legacy'), load('ch1')
out['bitIdenticalGames'] = all(a['games'] == b['games'] for a, b in zip(sorted(A, key=lambda s: s['seed']), sorted(B, key=lambda s: s['seed'])))
json.dump(out, open('m1-season.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(out['gate'], ensure_ascii=False), 'bitIdentical', out['bitIdenticalGames'])
for m in ('legacy', 'ch1'): print(m, {k: round(v, 3) for k, v in out['modes'][m]['teammateFGerr'].items()}, round(out['modes'][m]['teamPtsRMSE'], 3))
