"""E-189 judgement analysis (j0, j1 + report-only D0/D1/F-130). cwd = repo root. Inputs: out/jud/{base,odd,even,odd2}-<seed>.json (copied from the 5090). numpy/scipy only, no subprocess.
j1 conventions fixed before looking at results: sim rate per player = 100*sum(nsc[pid])/sum(poss of rows with pid in d) over all 32 seeds; real = judged half (even games for attr-odd, odd for attr-even);
Pearson r on the 150 players; slope = weighted least squares of sim on real (the prereg's literal 'sim against real'), weights = real defensive possessions of the judged half; the reverse regression (real on sim) is reported too.
swap-average = arithmetic mean of the two halves (r and slope separately). Baseline: same 32 base ledgers vs each half, averaged the same way."""
import json, sys, glob, numpy as np
sys.stdout.reconfigure(encoding='utf-8')
D = 'reports/sim-0.1.3+E189-nsfoul-attr/'; J = D + 'out/jud/'; SEEDS = list(range(20261210, 20261242))
RH = json.load(open(D + 'real-halves.json', encoding='utf-8')); P150 = json.load(open(D + 'p150.json', encoding='utf-8'))
def load(tag, s): return json.load(open(J + f'{tag}-{s}.json', encoding='utf-8'))
def sim_rates(tag):
    ns, dp = {}, {}
    for s in SEEDS:
        for r in load(tag, s)['rows']:
            for p in r['d']:
                if p > 0: dp[p] = dp.get(p, 0) + r['poss']
            for k, v in r['nsc'].items():
                if int(k) > 0: ns[int(k)] = ns.get(int(k), 0) + v
    return {p: 100 * ns.get(p, 0) / dp[p] for p in dp}, dp
def wls(y, x, w):
    xm = np.average(x, weights=w); ym = np.average(y, weights=w); return float(np.sum(w * (x - xm) * (y - ym)) / np.sum(w * (x - xm) ** 2))
def j1(sim, half):
    ids = [str(p) for p in P150]; real = np.array([100 * RH[i]['ns'][half] / RH[i]['defposs'][half] for i in ids]); w = np.array([RH[i]['defposs'][half] for i in ids])
    y = np.array([sim[int(i)] for i in ids]); r = float(np.corrcoef(y, real)[0, 1])
    return {'r': r, 'slope_sim_on_real': wls(y, real, w), 'slope_real_on_sim': wls(real, y, w), 'sim_sd': float(y.std()), 'real_sd': float(real.std()), 'sim_mean': float(np.average(y, weights=w)), 'real_mean': float(np.average(real, weights=w))}
out = {}
SR = {t: sim_rates(t) for t in ('base', 'odd', 'even')}
# judged half: attr-odd (built on odd games, h=1) is judged on even games (h=0); attr-even judged on h=1.
res = {'odd': j1(SR['odd'][0], 0), 'even': j1(SR['even'][0], 1), 'base_vs_even_games': j1(SR['base'][0], 0), 'base_vs_odd_games': j1(SR['base'][0], 1)}
avg = lambda a, b, k: (a[k] + b[k]) / 2
res['E189_avg'] = {k: avg(res['odd'], res['even'], k) for k in ('r', 'slope_sim_on_real', 'slope_real_on_sim')}
res['base_avg'] = {k: avg(res['base_vs_even_games'], res['base_vs_odd_games'], k) for k in ('r', 'slope_sim_on_real', 'slope_real_on_sim')}
res['pass'] = {'r>=0.45': res['E189_avg']['r'] >= 0.45, 'slope_sim_on_real in 0.7-1.3': 0.7 <= res['E189_avg']['slope_sim_on_real'] <= 1.3, 'slope_real_on_sim in 0.7-1.3': 0.7 <= res['E189_avg']['slope_real_on_sim'] <= 1.3}
out['j1'] = res; print(json.dumps(res, indent=1))
# ---- j0
import csv
E = 'reports/E140-foul-on-recal/'
ids = [t['id'] for t in json.load(open(E + 'team-ids.json', encoding='utf-8'))]
rs = json.load(open('data/defense-source/advanced-teams.json', encoding='utf-8'))['data']['resultSets'][0]; ix = {h: i for i, h in enumerate(rs['headers'])}
col = lambda k: {str(r[ix['TEAM_ID']]): float(r[ix[k]]) for r in rs['rowSet']}; pace, net = col('PACE'), col('NET_RATING')
act = np.array([net[str(i)] * pace[str(i)] / 100 for i in ids])
def agg(tag, seeds=SEEDS):
    S = dict(poss=0, pts=0, fta=0, g=0); Mx, Nx = np.zeros((len(seeds), 30)), np.zeros((len(seeds), 30)); fta_for = np.zeros(30); fta_ag = np.zeros(30); gp = np.zeros(30)
    for si, s in enumerate(seeds):
        for r in load(tag, s)['records']:
            S['g'] += 2; S['poss'] += r['possA'] + r['possB']; S['pts'] += r['ptsA'] + r['ptsB']; S['fta'] += r['ftaA'] + r['ftaB']
            d = r['ptsA'] - r['ptsB']; a, b = r['a'], r['b']; Mx[si, a] += d; Nx[si, a] += 1; Mx[si, b] -= d; Nx[si, b] += 1
            fta_for[a] += r['ftaA']; fta_for[b] += r['ftaB']; fta_ag[a] += r['ftaB']; fta_ag[b] += r['ftaA']; gp[a] += 1; gp[b] += 1
    P = Mx / Nx; return {'poss': S['poss'] / S['g'], 'pts': S['pts'] / S['g'], 'fta': S['fta'] / S['g'], 'mae': float(np.abs(P.mean(0) - act).mean()), 'draw': fta_for / gp, 'give': fta_ag / gp, 'net': P.mean(0)}
A = {t: agg(t) for t in ('base', 'odd', 'even')}
j0 = {'repro_double_run_identical': json.dumps(load('odd', 20261210)['records']) == json.dumps(load('odd2', 20261210)['records'])}
for t in ('odd', 'even'):
    j0[t] = {k: {'base': A['base'][k], 'new': A[t][k], 'rel': A[t][k] / A['base'][k] - 1} for k in ('poss', 'pts', 'fta')}
    j0[t]['mae'] = {'base': A['base']['mae'], 'new': A[t]['mae'], 'delta': A[t]['mae'] - A['base']['mae']}
    j0[t]['within1pct'] = all(abs(j0[t][k]['rel']) < 0.01 for k in ('poss', 'pts', 'fta'))
    j0[t]['mae_ok_strict_0.143_delta'] = j0[t]['mae']['delta'] <= 0.143; j0[t]['mae_ok_loose_0.286'] = j0[t]['mae']['delta'] <= 0.286 and A[t]['mae'] <= 0.286 + A['base']['mae']
out['j0'] = j0; print(json.dumps(j0, indent=1))
# ---- F-130: team FT draw / give spread (sd across 30 teams of per-team mean FTA for / against, 32 seeds)
f130 = {t: {'draw_sd': float(A[t]['draw'].std(ddof=1)), 'give_sd': float(A[t]['give'].std(ddof=1)), 'draw_give_corr': float(np.corrcoef(A[t]['draw'], A[t]['give'])[0, 1])} for t in A}
out['f130'] = f130; print(json.dumps(f130, indent=1))
json.dump(out, open(D + 'analysis1.json', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
