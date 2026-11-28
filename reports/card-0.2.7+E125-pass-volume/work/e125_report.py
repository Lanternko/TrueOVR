"""E-125 報告數字：p1、16 人表、pass/OVR 排名變動、simulatedPer36、高個前十。全部由 results-e125.json、work/P*/ranking.csv、pool-P*/raw-*.json、a0-pass-P*.json 重算。"""
import csv, json, sys
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
HERE = Path(__file__).resolve().parent; OUT = HERE.parent
sys.path.insert(0, str(OUT.parents[0] / 'ovr-v61-shrink-history-2025-26'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import build_attrs as B
res = json.loads((OUT / 'results-e125.json').read_text(encoding='utf-8'))
fit = json.loads((OUT / 'astvol-fit.json').read_text(encoding='utf-8'))
def rk(path):
    rows = list(csv.DictReader(open(path, encoding='utf-8')))
    return rows
R0, R5 = rk(HERE / 'P0/ranking.csv'), rk(HERE / 'P50/ranking.csv')
def passrank(rows):
    o = sorted(range(len(rows)), key=lambda i: -float(rows[i]['pass'])); rr = {}
    # 同分取平均名次
    i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and float(rows[o[j+1]]['pass']) == float(rows[o[i]]['pass']): j += 1
        for k in range(i, j+1): rr[rows[o[k]]['name']] = (i + j) / 2 + 1
        i = j + 1
    return rr
pr0, pr5 = passrank(R0), passrank(R5)
ovr0 = {r['name']: int(r['rank']) for r in R0}; ovr5 = {r['name']: int(r['rank']) for r in R5}
d0 = {r['name']: r for r in R0}; d5 = {r['name']: r for r in R5}
# p1
def pool_vals(season_file, tag):
    raw = json.loads(Path(OUT / f'pool-{tag}/{season_file}').read_text(encoding='utf-8'))
    a = raw['attrs']['pass']; info = raw['poolInfo']
    return {p: v for p, v in a.items() if info[p]['GP'] >= 30 and info[p]['MIN'] / max(info[p]['GP'], 1) >= 20}
base = B.bench_rows('base'); idx = {str(r['PLAYER_ID']): r for r in base}
def last(tag):
    a = json.loads((OUT / f'a0-pass-{tag}.json').read_text(encoding='utf-8'))['r']
    return {p: v for p, v in a.items() if p in idx and idx[p]['GP'] >= B.POOL[0] and idx[p]['MIN'] / idx[p]['GP'] >= B.POOL[1]}
def p1(tag):
    ss = ['2022-23', '2023-24', '2024-25']
    vals = {s: pool_vals(f'raw-{s}.json', tag) for s in ss}; vals['2025-26'] = last(tag)
    keys = ss + ['2025-26']; out = {}
    for a, b in zip(keys, keys[1:]):
        c = sorted(set(vals[a]) & set(vals[b]))
        out[f'{a}->{b}'] = {'n': len(c), 'spearman': float(spearmanr([vals[a][p] for p in c], [vals[b][p] for p in c])[0])}
    return out
P1 = {'P0': p1('P0'), 'P50': p1('P50')}
# AST% 近似（標準公式，隊合計用 base 列加總；交易球員用其列的 TEAM_ID，僅供對照）
tm = {}
for r in base:
    t = tm.setdefault(r['TEAM_ID'], {'MIN': 0, 'FGM': 0}); t['MIN'] += r['MIN']; t['FGM'] += r['FGM']
def astpct(r):
    t = tm[r['TEAM_ID']]; den = (r['MIN'] / (t['MIN'] / 5)) * t['FGM'] - r['FGM']
    return 100 * r['AST'] / den if den > 0 else None
byname = {r['PLAYER_NAME']: r for r in base}
NAMES = ['Giannis Antetokounmpo','Joel Embiid','Nikola Jokić','Luka Dončić','James Harden','Tyrese Haliburton','Trae Young','Cade Cunningham','Josh Giddey','LaMelo Ball','Isaiah Collier','Stephon Castle','Draymond Green','Domantas Sabonis','Shai Gilgeous-Alexander','Cam Spencer']
named = []
for n in NAMES:
    if n not in d0: named.append({'name': n, 'missing': True}); continue
    b = byname.get(n); a = astpct(b) if b else None
    named.append({'name': n, 'passRank': [pr0[n], pr5[n]], 'passVal': [float(d0[n]['pass']), float(d5[n]['pass'])], 'ovrRank': [ovr0[n], ovr5[n]], 'ovr': [float(d0[n]['ovr']), float(d5[n]['ovr'])],
                  'ast36': (b['AST'] / (b['MIN'] / 36)) if b else None, 'astPctApprox': a, 'MIN': float(d0[n]['MIN'])})
top = lambda rr, k=20: [n for n, _ in sorted(rr.items(), key=lambda kv: kv[1])[:k]]
passTop = {'P0': top(pr0), 'P50': top(pr5)}
ovrTop = {'P0': top(ovr0), 'P50': top(ovr5)}
movers = sorted([{'name': n, 'passRank': [pr0[n], pr5[n]], 'MIN': float(d0[n]['MIN'])} for n in pr0 if float(d0[n]['MIN']) >= 1000 and abs(pr0[n] - pr5[n]) >= 30], key=lambda x: x['passRank'][1] - x['passRank'][0])
ovrMov = [n for n in ovr0 if abs(ovr0[n] - ovr5[n]) >= 10]
sim = {n: float(d5[n]['simulatedPer36']) - float(d0[n]['simulatedPer36']) for n in d0}
sv = sorted(sim.values()); med = float(np.median(sv))
big10 = sorted(sim.items(), key=lambda kv: -abs(kv[1]))[:10]
tall = lambda R: [r['name'] for r in sorted(R, key=lambda r: -float(r['heightInches']))[:0]]
def bigs(R):
    t = [r for r in R if float(r['heightInches']) >= 82]  # >=6'10"
    return [(r['name'], int(r['rank'])) for r in sorted(t, key=lambda r: int(r['rank']))[:10]]
out = {'p1': P1, 'p1Min': {k: min(v[k]['spearman'] for k in v) for k, v in P1.items()}, 'named': named, 'passTop20': passTop, 'ovrTop20': ovrTop,
       'passMovers30_MIN1000': movers, 'ovrMovers10': {'count': len(ovrMov), 'N': len(ovr0)}, 'simulatedPer36Delta': {'median': med, 'meanAbs': float(np.mean(np.abs(sv))), 'top10AbsChange': big10},
       'topBigsP0': bigs(R0), 'topBigsP50': bigs(R5), 'astvolFit': {k: fit[k] for k in fit if k not in ('fit',)} if False else {k: v for k, v in fit.items() if k in ('k','lam','kh','prior','trainMae','trainN','trainA','shrinkCheck2025_26')},
       'results': {'checks': {k: res['arms']['P50']['checks'][k] for k in ('c0', 'c1', 'm1', 'm2', 'm3', 'r1p')} , 'eval': {k: res['arms']['P50']['eval'][k] for k in ('dRho_N_W', 'dRho_Q_W', 'dRho_N_lin', 'dRho_Q_lin')}, 'anchors': res['reportOnly']['anchors'], 'evaluate_gates': res['evaluate_gates']}}
(OUT / 'results.json').write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding='utf-8')
print(json.dumps({k: out[k] for k in ('p1', 'p1Min', 'ovrMovers10', 'simulatedPer36Delta', 'topBigsP0', 'topBigsP50', 'astvolFit')}, ensure_ascii=False, indent=1))
for x in named: print(x)
print('passTop', passTop); print('ovrTop', ovrTop); print('movers', len(movers))
for m in movers: print(m)
