"""E-189 report-only WinImp items: Spearman(276, RAPM answer), 36 defensive non-centers mean rank gap, E-067 S (bias). Baseline = E-166 checkpoint-k.jsonl (sim 0.1.3 settings k=2). cwd = repo root.
E189 = mean of attr-odd and attr-even runs (point estimate winsPer82 = 82*mean(win draws diff); same as analyze166 point estimates, no bootstrap)."""
import csv, json, sys, importlib.util
import numpy as np
from scipy.stats import spearmanr
sys.stdout.reconfigure(encoding='utf-8')
D = 'reports/sim-0.1.3+E189-nsfoul-attr/'; E = 'reports/sim-0.1.2+E166-ft-defense/'
G = json.load(open(E + 'frozen-groups.json', encoding='utf-8'))
RP = {r['name']: r for r in csv.DictReader(open('reports/sim-0.1.0+E085-physedge/rapm-2022-25.csv', encoding='utf-8')) if r['name']}
rank = list(csv.DictReader(open('reports/card-0.1.1+E060-onball-targeting/primary/ranking.csv', encoding='utf-8-sig'))); POSR = {r['name']: r['pos'] for r in rank}
def ck(f, key='avg'):
    X, M, W = {}, {}, {}
    for l in open(f, encoding='utf-8'):
        if not l.strip(): continue
        r = json.loads(l)[key]; d = np.array(r['draws'], float); X[r['name']] = float((d[:, 4] - d[:, 5]).mean()); W[r['name']] = 82 * float((d[:, 6] - d[:, 7]).mean()); M[r['name']] = r['minutes']
    return X, M, W
rk = lambda v: (-v).argsort().argsort() + 1
N = G['population']
def res(X, M):
    x = np.array([X[n] for n in N]); m = np.array([M[n] for n in N]); ans = np.array([float(RP[n]['pooledO']) + float(RP[n]['pooledD']) for n in N]) * m / 48 * 2
    s, a = dict(zip(N, rk(x))), dict(zip(N, rk(ans))); return s, a, float(spearmanr(x, ans)[0])
gap = lambda s, a, grp: float(np.mean([s[n] - a[n] for n in grp]))
runs = {'base': E + 'checkpoint-k.jsonl', 'odd': D + 'out/wi-odd.jsonl', 'even': D + 'out/wi-even.jsonl'}
data = {k: ck(v) for k, v in runs.items()}
avg = lambda i: {n: (data['odd'][i][n] + data['even'][i][n]) / 2 for n in data['odd'][i]}
data['e189'] = (avg(0), data['odd'][1], avg(2))
out = {}
for k in ('base', 'odd', 'even', 'e189'):
    s, a, rho = res(data[k][0], data[k][1]); out[k] = {'spearman': rho, 'j36_gap': gap(s, a, G['j1'])}
    out[k]['rank'] = s
out['ans'] = a
# E-067 S
spec = importlib.util.spec_from_file_location('bias_check', 'reports/bias-check-E067/bias_check.py'); BC = importlib.util.module_from_spec(spec); spec.loader.exec_module(BC)
def model(W):
    return lambda ev: {n: (W[n], POSR.get(n, '?'), None) for n in W}
for k in ('base', 'e189'):
    rng = np.random.default_rng(BC.SEED); d = {dr: BC.measure(model(data[k][2]), ev, rng) for dr, ev in (('AB', 'B'), ('BA', 'A'))}
    out[k]['bias'] = {'verdict': BC.verdict(d), 'S': {dr: {'S': x['S'], 'CI90': x['CI90'], 'n': x['n'], 'rho': x['rho']} for dr, x in d.items()}}
# examples: centers / defenders ranks
ex = ['Jakob Poeltl', 'Daniel Gafford', 'Ace Bailey', 'Rudy Gobert', 'Alex Caruso', 'Herbert Jones']
out['examples'] = {n: {'ans': int(out['ans'][n]), 'base': int(out['base']['rank'][n]), 'e189': int(out['e189']['rank'][n])} for n in ex if n in out['ans']}
for k in ('base', 'odd', 'even', 'e189'): del out[k]['rank']
print(json.dumps({k: v for k, v in out.items() if k != 'ans'}, ensure_ascii=False, indent=1, default=float))
json.dump({k: v for k, v in out.items() if k != 'ans'}, open(D + 'winimp189.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)
