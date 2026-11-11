"""E-166 §2 judgement j0~j3 (+ report-only items). cwd = repo root. Reads E-140 baselines (import only) and this dir's runs."""
import csv, json, hashlib, sys
import numpy as np
from scipy.stats import spearmanr
sys.stdout.reconfigure(encoding='utf-8')
D, E = 'reports/sim-0.1.2+E166-ft-defense/', 'reports/E140-foul-on-recal/'
G = json.load(open(D + 'frozen-groups.json', encoding='utf-8')); cal = json.load(open(D + 'calibration.json', encoding='utf-8'))
RP = {r['name']: r for r in csv.DictReader(open('reports/sim-0.1.0+E085-physedge/rapm-2022-25.csv', encoding='utf-8')) if r['name']}
POS = {r['name']: r['pos'] for r in csv.DictReader(open('reports/sim-0.1.0+E076-physique-dedup/winimp-dedup.csv', encoding='utf-8-sig'))}
def ck(f):
    X, M = {}, {}
    for l in open(f, encoding='utf-8'):
        if not l.strip(): continue
        r = json.loads(l)['avg']; d = np.array(r['draws'], float); X[r['name']] = float((d[:, 4] - d[:, 5]).mean()); M[r['name']] = r['minutes']
    return X, M
rk = lambda v: (-v).argsort().argsort() + 1
def ranks(f):  # od_split algorithm (A1 point 2): answer = (pooledO + pooledD) * minutes/48 * 2, ranks within the frozen 276
    X, M = ck(f); N = G['population']; assert all(n in X for n in N), 'population missing'
    x = np.array([X[n] for n in N]); m = np.array([M[n] for n in N])
    ans = np.array([float(RP[n]['pooledO']) + float(RP[n]['pooledD']) for n in N]) * m / 48 * 2
    return dict(zip(N, rk(x))), dict(zip(N, rk(ans))), spearmanr(x, ans)[0], dict(zip(N, x))
b_sim, b_ans, b_rho, b_x = ranks(E + 'checkpoint-on.jsonl'); n_sim, n_ans, n_rho, n_x = ranks(D + 'checkpoint-k.jsonl')
gap = lambda s, a, grp: float(np.mean([s[n] - a[n] for n in grp]))
j1b, j1n = gap(b_sim, b_ans, G['j1']), gap(n_sim, n_ans, G['j1'])
out = {'calibration': {k: cal[k] for k in ('k', 'c', 'pace')}}
out['j1'] = {'base_mean_gap': j1b, 'new_mean_gap': j1n, 'improvement': j1b - j1n, 'pass': j1b - j1n >= 10}
out['j2'] = {'base_spearman': b_rho, 'new_spearman': n_rho, 'delta': n_rho - b_rho, 'pass': n_rho - b_rho >= -0.01}
# j3: E-140 analyze_rr_e140 T1_pace MAE
ids = [t['id'] for t in json.load(open(E + 'team-ids.json', encoding='utf-8'))]
rs = json.load(open('data/defense-source/advanced-teams.json', encoding='utf-8'))['data']['resultSets'][0]; ix = {h: i for i, h in enumerate(rs['headers'])}
col = lambda k: {str(r[ix['TEAM_ID']]): float(r[ix[k]]) for r in rs['rowSet']}; pace, net = col('PACE'), col('NET_RATING')
act = np.array([net[str(i)] * pace[str(i)] / 100 for i in ids])
def load(f): return [r for l in open(f, encoding='utf-8') if l.strip() for r in json.loads(l)['records']]
S1 = list(range(20261028, 20261060))
def mat(rec):
    assert sorted({r['seed'] for r in rec}) == S1 and len(rec) == len(S1) * 435
    Mx, Nx = np.zeros((32, 30)), np.zeros((32, 30))
    for r in rec: s = S1.index(r['seed']); d = r['ptsA'] - r['ptsB']; Mx[s, r['a']] += d; Nx[s, r['a']] += 1; Mx[s, r['b']] -= d; Nx[s, r['b']] += 1
    return Mx / Nx
mae = lambda P: float(np.abs(P.mean(0) - act).mean())
ron, rk2 = load(E + 'rr-on.jsonl'), load(D + 'rr-k.jsonl')
out['j3'] = {'base_mae': mae(mat(ron)), 'new_mae': mae(mat(rk2))}; out['j3']['delta'] = out['j3']['new_mae'] - out['j3']['base_mae']; out['j3']['pass'] = out['j3']['delta'] <= 0.1
r1 = load(D + 'rr-k1.jsonl'); key = lambda r: (r['seed'], r['a'], r['b'])
same = sorted(r1, key=key) == sorted(ron, key=key)
npm = open(D + 'npm-test.log', encoding='utf-8', errors='replace').read()
out['j0'] = {'k1_identical_to_rr_on': same, 'games': len(r1), 'npm_test_log_tail': npm.strip().splitlines()[-6:]}
lg = lambda rec: {'foulPer100': 100 * sum(r['foulShootA'] + r['foulShootB'] + r['foulAndA'] + r['foulAndB'] for r in rec) / sum(r['possA'] + r['possB'] for r in rec),
                  'possPerTeamGame': sum(r['possA'] + r['possB'] for r in rec) / (2 * len(rec)), 'ptsPerTeamGame': sum(r['ptsA'] + r['ptsB'] for r in rec) / (2 * len(rec)),
                  'ftaPerTeamGame': sum(r['ftaA'] + r['ftaB'] for r in rec) / (2 * len(rec))}
out['league_judge_seeds'] = {'base': lg(ron), 'new': lg(rk2)}
# report-only
row = lambda n: {'pos': POS.get(n, '?'), 'O': float(RP[n]['pooledO']), 'D': float(RP[n]['pooledD']), 'ans': int(b_ans[n]), 'base': int(b_sim[n]), 'new': int(n_sim[n]), 'xBase': b_x[n], 'xNew': n_x[n]}
out['j1_players'] = {n: row(n) for n in sorted(G['j1'], key=lambda n: b_ans[n])}
ex = ['Herbert Jones', 'Alex Caruso', 'Marcus Smart', 'Derrick White', 'Dyson Daniels', 'Draymond Green', 'Dillon Brooks', 'Rudy Gobert', 'Bam Adebayo', 'Jrue Holiday']
out['examples'] = {n: row(n) for n in ex if n in b_sim}
big = sorted([n for n in G['population'] if POS.get(n) == 'C'], key=lambda n: b_sim[n])[:10]
out['top10_bigs_by_base'] = {n: row(n) for n in big}
c_all = [n for n in G['population'] if POS.get(n) == 'C']
out['C_mean_gap'] = {'base': gap(b_sim, b_ans, c_all), 'new': gap(n_sim, n_ans, c_all), 'n': len(c_all)}
out['adopt'] = all(out[j]['pass'] for j in ('j1', 'j2', 'j3')) and same
json.dump(out, open(D + 'judgement.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=lambda v: v.item())
print(json.dumps({j: out[j] for j in ('calibration', 'j0', 'j1', 'j2', 'j3', 'C_mean_gap', 'adopt', 'league_judge_seeds')}, ensure_ascii=False, indent=1, default=lambda v: v.item()))
for n, r in list(out['j1_players'].items()): print(f"  {n:24s} {r['pos']:2s} D {r['D']:+.2f} ans {r['ans']:3d} | base {r['base']:3d} -> new {r['new']:3d}")
print('examples'); [print(f"  {n:24s} {r['pos']:2s} ans {r['ans']:3d} | base {r['base']:3d} -> new {r['new']:3d}") for n, r in out['examples'].items()]
print('bigs'); [print(f"  {n:24s} ans {r['ans']:3d} | base {r['base']:3d} -> new {r['new']:3d}") for n, r in out['top10_bigs_by_base'].items()]
