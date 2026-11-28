"""E-184 §1: does the sim reproduce each player's input FTA/FGA? Weighted (sim FGA) least squares of sim FTA/FGA on input
shotProfile.freeThrowsPerAttempt, players with real 2025-26 FGA >= 300 (both box formats). Stop rule: a=1 slope in [0.95, 1.05].
usage: python -I slope184.py rr-a1-cal.jsonl   (cwd = repo root)"""
import glob, json, sys
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
D = 'reports/sim-0.1.2+E184-ftdraw-refit/'
real = {}
for f in glob.glob('data/defense-source/boxes/*.json'):
    d = json.load(open(f, encoding='utf-8'))['data']
    b = d.get('boxScoreTraditional') or d['game']
    for side in ('homeTeam', 'awayTeam'):
        for p in b[side]['players']:
            s = p['statistics']; r = real.setdefault(p['personId'], [0, 0])
            r[0] += s['fieldGoalsAttempted']; r[1] += s['freeThrowsAttempted']
sim = {}
lines = [json.loads(l) for l in open(D + sys.argv[1], encoding='utf-8')]
for l in lines:
    for pid, p in l['players'].items():
        s = sim.setdefault(int(pid), {'name': p['name'], 'fga': 0, 'fta': 0, 'ftr': p['ftr']})
        if s['ftr'] != p['ftr']: raise SystemExit('input ftr changed for ' + p['name'])
        s['fga'] += p['fga']; s['fta'] += p['fta']
rows = [(pid, s) for pid, s in sim.items() if real.get(pid, [0])[0] >= 300 and s['fga'] > 0]
x = np.array([s['ftr'] for _, s in rows]); y = np.array([s['fta'] / s['fga'] for _, s in rows]); w = np.array([s['fga'] for _, s in rows], float)
X = np.c_[np.ones_like(x), x]; W = np.diag(w)
b0, b1 = np.linalg.solve(X.T @ W @ X, X.T @ W @ y)
# player-level spread: sim vs input, and real FTA/FGA (from boxes) vs input as reference
ry = np.array([real[pid][1] / real[pid][0] for pid, _ in rows])
out = {'seeds': [l['seed'] for l in lines], 'players': len(rows), 'slope': float(b1), 'intercept': float(b0),
       'stop_rule_in_range': bool(0.95 <= b1 <= 1.05),
       'wmean_input': float(np.average(x, weights=w)), 'wmean_sim': float(np.average(y, weights=w)),
       'sd_input': float(x.std()), 'sd_sim': float(y.std()), 'sd_real_box': float(ry.std()), 'r_sim_input': float(np.corrcoef(x, y)[0, 1]),
       'top': sorted(({'name': s['name'], 'input': round(s['ftr'], 3), 'sim': round(s['fta'] / s['fga'], 3), 'real_box': round(real[pid][1] / real[pid][0], 3)}
                      for pid, s in rows), key=lambda t: -t['input'])[:12]}
json.dump(out, open(D + 'slope-' + sys.argv[1].replace('.jsonl', '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in out.items() if k != 'top'}, ensure_ascii=False))
for t in out['top']: print(t)
