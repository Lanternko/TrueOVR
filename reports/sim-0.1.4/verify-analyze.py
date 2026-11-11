"""sim 0.1.4 multi-seed check: league per-team-game nsFT / FTA / pts / poss (+ nsFoul, foulPer100) on vs off, paired by seed.
Pass rule (from R-131 follow-up): |on/off - 1| < 1% for nsFT, FTA, pts, poss. Also per-team (30) FTA/pts differences on - off. Light, no subprocess."""
import json, glob, sys, numpy as np
sys.stdout.reconfigure(encoding='utf-8')
D = 'reports/sim-0.1.4/out-verify/'
K = ('nsFt', 'fta', 'pts', 'poss', 'nsFoul', 'foulShoot')
def load(arm):
    seeds = {}
    for f in sorted(glob.glob(D + arm + '-*.json')):
        j = json.load(open(f, encoding='utf-8')); S = {k: 0.0 for k in K}; T = {}; g = 0
        for r in j['records']:
            g += 2
            for side, t in (('A', r['a']), ('B', r['b'])):
                for k, src in (('nsFt', 'nsFt'), ('fta', 'fta'), ('pts', 'pts'), ('poss', 'poss'), ('nsFoul', 'nsFoul'), ('foulShoot', 'foulShoot')):
                    v = r[src + side] + (r['foulAnd' + side] if k == 'foulShoot' else 0); S[k] += v
                    T.setdefault(t, {q: [0.0, 0] for q in K}); T[t][k][0] += v; T[t][k][1] += 1
        seeds[j['seed']] = ({k: S[k] / g for k in K}, {t: {k: v[0] / v[1] for k, v in d.items()} for t, d in T.items()})
    return seeds
on, off = load('on'), load('off'); common = sorted(set(on) & set(off))
out = {'seeds': common, 'league': {}, 'team': {}}
for k in K:
    a = np.array([on[s][0][k] for s in common]); b = np.array([off[s][0][k] for s in common]); r = a / b - 1
    out['league'][k] = {'on': a.mean(), 'off': b.mean(), 'rel': a.mean() / b.mean() - 1, 'rel_se': r.std(ddof=1) / np.sqrt(len(r))}
out['league']['foulPer100'] = {arm: 100 * np.mean([d[s][0]['foulShoot'] / d[s][0]['poss'] for s in common]) for arm, d in (('on', on), ('off', off))}
for k in ('fta', 'pts', 'nsFt'):
    teams = sorted(on[common[0]][1]); dd = np.array([np.mean([on[s][1][t][k] for s in common]) - np.mean([off[s][1][t][k] for s in common]) for t in teams])
    out['team'][k] = {'mean_abs_diff': float(np.abs(dd).mean()), 'max_abs_diff': float(np.abs(dd).max()), 'sd_on': float(np.std([np.mean([on[s][1][t][k] for s in common]) for t in teams])),
                      'sd_off': float(np.std([np.mean([off[s][1][t][k] for s in common]) for t in teams]))}
out['pass'] = {k: abs(out['league'][k]['rel']) < 0.01 for k in ('nsFt', 'fta', 'pts', 'poss')}
json.dump(out, open('reports/sim-0.1.4/verify-multiseed.json', 'w', encoding='utf-8'), indent=1, default=float)
print(json.dumps(out, indent=1, default=float))
