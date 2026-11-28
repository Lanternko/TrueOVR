"""E-166 post-hoc diagnostic (R-115): split each team's net margin per game into FT points and field points,
real 2025-26 boxes vs sim k=1 (=0.1.2) and k=2. Measurement only, no parameters chosen. cwd = repo root."""
import glob, json, sys
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
D = 'reports/sim-0.1.2+E166-ft-defense/'
ids = [t['id'] for t in json.load(open('reports/E140-foul-on-recal/team-ids.json', encoding='utf-8'))]
pos = {str(i): k for k, i in enumerate(ids)}
K = ('pts', 'ftm', 'fta', 'oreb')
# real: per-game averages of own and opponent box totals
R = {k: np.zeros((30, 2)) for k in K}; G = np.zeros(30); MIN = np.zeros(30)
for f in glob.glob('data/defense-source/boxes/*.json'):
    d = json.load(open(f, encoding='utf-8'))['data']  # two box formats: boxscoretraditionalv3 and liveData game
    b = d.get('boxScoreTraditional') or d['game']
    gmin = 48 + 5 * (b['period'] - 4) if 'period' in b else int(b['homeTeam']['statistics']['minutes'].split(':')[0]) / 5
    for me, op in (('homeTeam', 'awayTeam'), ('awayTeam', 'homeTeam')):
        t = pos[str(b[me]['teamId'])]; s, o = b[me]['statistics'], b[op]['statistics']
        for k, src in zip(K, ('points', 'freeThrowsMade', 'freeThrowsAttempted', 'reboundsOffensive')):
            R[k][t] += (s[src], o[src])
        G[t] += 1; MIN[t] += gmin
assert G.sum() == 2460, G.sum()
ot = MIN / G / 48  # sim has no overtime; scale real per-game totals to 48 minutes
real = {k: (v[:, 0] - v[:, 1]) / G / ot for k, v in R.items()}
real['fg'] = real['pts'] - real['ftm']
def sim(f):
    S = {k: np.zeros(30) for k in K}; N = np.zeros(30)
    for l in open(f, encoding='utf-8'):
        for r in json.loads(l)['records']:
            for k in K:
                d = r[k + 'A'] - r[k + 'B']; S[k][r['a']] += d; S[k][r['b']] -= d
            N[r['a']] += 1; N[r['b']] += 1
    out = {k: v / N for k, v in S.items()}; out['fg'] = out['pts'] - out['ftm']; return out
s1, s2 = sim(D + 'rr-k1.jsonl'), sim(D + 'rr-k.jsonl')
mae = lambda a, b: float(np.abs(a - b).mean())
cor = lambda a, b: float(np.corrcoef(a, b)[0, 1])
res = {}
for k in ('pts', 'fg', 'ftm', 'fta', 'oreb'):
    res[k] = {'mae_k1': mae(s1[k], real[k]), 'mae_k2': mae(s2[k], real[k]), 'r_k1': cor(s1[k], real[k]), 'r_k2': cor(s2[k], real[k]),
              'sd_real': float(real[k].std()), 'sd_k1': float(s1[k].std()), 'sd_k2': float(s2[k].std())}
# where did the MAE change come from: change in |error| per team, and change in each component
e1, e2 = s1['pts'] - real['pts'], s2['pts'] - real['pts']
dft, dfg = s2['ftm'] - s1['ftm'], s2['fg'] - s1['fg']
res['shift'] = {'sd_dft': float(dft.std()), 'sd_dfg': float(dfg.std()), 'r_dft_dfg': cor(dft, dfg),
                # does the FT shift point toward the real FT gap? (k1 FT error vs FT shift)
                'r_dft_vs_k1_ft_error': cor(dft, real['ftm'] - s1['ftm']),
                'r_dfg_vs_k1_fg_error': cor(dfg, real['fg'] - s1['fg']),
                'r_dpts_vs_k1_pts_error': cor(dft + dfg, real['pts'] - s1['pts'])}
names = {t['id']: t['name'] for t in json.load(open('reports/E140-foul-on-recal/team-ids.json', encoding='utf-8'))}
res['teams'] = [{'team': names[ids[i]], 'real_pts': real['pts'][i], 'k1_pts': s1['pts'][i], 'k2_pts': s2['pts'][i],
                 'real_ft': real['ftm'][i], 'k1_ft': s1['ftm'][i], 'k2_ft': s2['ftm'][i],
                 'real_fg': real['fg'][i], 'k1_fg': s1['fg'][i], 'k2_fg': s2['fg'][i]} for i in range(30)]
json.dump(res, open(D + 'decomp.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)
for k in ('pts', 'fg', 'ftm', 'fta', 'oreb'):
    v = res[k]; print(f"{k:5s} MAE k1 {v['mae_k1']:.3f} k2 {v['mae_k2']:.3f} | r k1 {v['r_k1']:+.3f} k2 {v['r_k2']:+.3f} | sd real {v['sd_real']:.2f} k1 {v['sd_k1']:.2f} k2 {v['sd_k2']:.2f}")
print(res['shift'])
for t in sorted(res['teams'], key=lambda t: -abs(t['k2_pts'] - t['real_pts']) + abs(t['k1_pts'] - t['real_pts']))[:8]:
    print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in t.items()})
# offense vs defense side of FTA (own FTA drawn, opponent FTA allowed), per 48 min
def side(f):
    S = np.zeros((30, 2)); N = np.zeros(30)
    for l in open(f, encoding='utf-8'):
        for r in json.loads(l)['records']:
            S[r['a']] += (r['ftaA'], r['ftaB']); S[r['b']] += (r['ftaB'], r['ftaA']); N[r['a']] += 1; N[r['b']] += 1
    return S / N[:, None]
rs = R['fta'] / G[:, None] / ot[:, None]; a1, a2 = side(D + 'rr-k1.jsonl'), side(D + 'rr-k.jsonl')
res['fta_sides'] = {}
for j, nm in ((0, 'own_drawn'), (1, 'opp_allowed')):
    res['fta_sides'][nm] = {'sd_real': float(rs[:, j].std()), 'sd_k1': float(a1[:, j].std()), 'sd_k2': float(a2[:, j].std()),
                            'r_k1': cor(a1[:, j], rs[:, j]), 'r_k2': cor(a2[:, j], rs[:, j]),
                            'mae_k1_demeaned': mae(a1[:, j] - a1[:, j].mean(), rs[:, j] - rs[:, j].mean()), 'mae_k2_demeaned': mae(a2[:, j] - a2[:, j].mean(), rs[:, j] - rs[:, j].mean())}
    print(nm, {k: round(v, 3) for k, v in res['fta_sides'][nm].items()})
json.dump(res, open(D + 'decomp.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)
