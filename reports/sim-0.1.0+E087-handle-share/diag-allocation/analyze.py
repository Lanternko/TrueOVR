# Diagnostic only (same-season data, not evidence). Joins sim allocation counts (collect.mjs, 3 seeds)
# with 2025-26 NBA tracking Possessions-FULL.json on playerId; population = v41 validation tov36_primary (n378).
# usage (repo root): python reports/sim-0.1.0+E087-handle-share/diag-allocation/analyze.py
import csv, json, math, sys
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
sys.stdout.reconfigure(encoding='utf-8')
D = Path('reports/sim-0.1.0+E087-handle-share/diag-allocation')
SEEDS = (20261012, 20261013, 20261014)
runs = [json.loads((D / 'runs' / f'alloc-{s}.json').read_text(encoding='utf-8')) for s in SEEDS]
n = len(runs)


def simavg(pid):
    o = dict(first=0., putback=0., recv=0., holdSec=0., seconds=0., tov=0.)
    for r in runs:
        p = r['players'].get(str(pid), {})
        for k in ('first', 'putback', 'recv', 'holdSec'):
            o[k] += p.get(k, 0) / n
        o['seconds'] += r['seconds'].get(str(pid), 0) / n
        o['tov'] += r['tov'].get(str(pid), 0) / n
    return o


# cross-check: E-069 off runs (same path/seeds) per-player seconds and tov
e069 = {}
for s in SEEDS:
    r = json.load(open(f'reports/handle-E069/sim/runs/off/off-{s}.json', encoding='utf-8'))
    for t in r['teams']:
        for p in t['players']:
            e = e069.setdefault(p['playerId'], [0, 0])
            e[0] += p['stats']['seconds'] / n
            e[1] += p['stats']['tov'] / n
d = json.loads(Path('reports/handle-E069/raw/2025-26/Possessions-FULL.json').read_text(encoding='utf-8'))['data']
rs = d['resultSets'][0] if isinstance(d['resultSets'], list) else d['resultSets']
real = {r[0]: dict(zip(rs['headers'], r)) for r in rs['rowSet']}
V = list(csv.DictReader(open('reports/player-impact-v41/2025-26-player-validation.csv', encoding='utf-8-sig')))
pop = [r for r in V if r['tov36_primary'] == 'True']
dep = np.array([float(r['creationDependence_sourceRole']) for r in pop])
q = np.quantile(dep, [1 / 3, 2 / 3])
terc = np.digitize(dep, q)
rows, lost, mism = [], [], 0
for r, tg in zip(pop, terc):
    pid = int(r['playerId'])
    s = simavg(pid)
    t = real.get(pid)
    e = e069.get(pid)
    if e is None or abs(e[0] - s['seconds']) > 1e-6 or abs(e[1] - s['tov']) > 1e-6:
        mism += 1
    if t is None or not t['MIN'] or s['seconds'] <= 0:
        lost.append(r['name'])
        continue
    sm = s['seconds'] / 60
    rm = t['MIN']
    tch = s['first'] + s['recv']
    rows.append(dict(
        playerId=pid, name=r['name'], group=r['roleGroup'], position=r['position'], depTercile=int(tg) + 1,
        creationDependence=float(r['creationDependence_sourceRole']), simMin=round(sm, 1), realMin=rm, realGP=t['GP'],
        sim_first36=s['first'] / sm * 36, sim_putback36=s['putback'] / sm * 36, sim_recv36=s['recv'] / sm * 36,
        sim_touch36=tch / sm * 36, sim_hold36=s['holdSec'] / sm * 36,
        sim_secPerTouch=s['holdSec'] / tch if tch else float('nan'),
        real_touch36=t['TOUCHES'] / rm * 36, real_front36=t['FRONT_CT_TOUCHES'] / rm * 36,
        real_top36=t['TIME_OF_POSS'] * 60 / rm * 36, real_secPerTouch=t['AVG_SEC_PER_TOUCH'],
        real_elbow36=t['ELBOW_TOUCHES'] / rm * 36, real_post36=t['POST_TOUCHES'] / rm * 36,
        real_paint36=t['PAINT_TOUCHES'] / rm * 36))


def arr(k, rr=None):
    return np.array([x[k] for x in (rows if rr is None else rr)], float)


# pooled scale factors (sim -> real units), minutes-weighted over the joined population
pairs = {'touch': ('sim_touch36', 'real_touch36'), 'front': ('sim_touch36', 'real_front36'),
         'first_vs_front': ('sim_first36', 'real_front36'), 'hold': ('sim_hold36', 'real_top36')}
scale = {k: float(np.sum(arr(b) * arr('realMin')) / np.sum(arr(a) * arr('simMin'))) for k, (a, b) in pairs.items()}
for x in rows:
    for k, (a, b) in pairs.items():
        rel = x[a] * scale[k] / x[b] if x[b] > 0 else float('nan')
        x[f'rel_{k}'] = rel
        x[f'logrel_{k}'] = math.log(rel) if rel > 0 else float('nan')


def stats(rr, k):
    a, b = pairs[k]
    s, t = arr(a, rr), arr(b, rr)
    rho = spearmanr(s, t).statistic
    lr = arr(f'logrel_{k}', rr)
    return dict(n=len(rr), rho=round(float(rho), 3), mae_raw=round(float(np.mean(np.abs(s - t))), 2),
                mae_scaled=round(float(np.mean(np.abs(s * scale[k] - t))), 2),
                meanSim=round(float(s.mean()), 2), meanReal=round(float(t.mean()), 2),
                rawRatio=round(float(s.mean() / t.mean()), 3), relRatio_geo=round(float(np.exp(np.nanmean(lr))), 3))


res = dict(label='診斷，同季資料，不算證據', seeds=SEEDS, games=[r['games'] for r in runs],
           population='v41 2025-26 tov36_primary', nPop=len(pop), nJoined=len(rows), joinLost=lost,
           seedAvgMismatchVsE069off=mism, scale=scale, tercileCuts=[float(v) for v in q], metrics={})
groups = {'all': rows, **{f'group_{g}': [x for x in rows if x['group'] == g] for g in 'GFC'},
          **{f'depTercile_{t}': [x for x in rows if x['depTercile'] == t] for t in (1, 2, 3)}}
for k in pairs:
    res['metrics'][k] = {gname: stats(rr, k) for gname, rr in groups.items()}
tot_sim = {k: sum(sum(p.get(k, 0) for p in r['players'].values()) for r in runs) / n / 2460
           for k in ('first', 'recv', 'holdSec', 'putback')}
tot_real = dict(touches=sum(t['TOUCHES'] for t in real.values()) / 2460,
                front=sum(t['FRONT_CT_TOUCHES'] for t in real.values()) / 2460,
                topSec=sum(t['TIME_OF_POSS'] for t in real.values()) * 60 / 2460)
res['perTeamGame'] = dict(sim=tot_sim, real=tot_real)
res['secPerTouch'] = dict(rho=round(float(spearmanr(arr('sim_secPerTouch'), arr('real_secPerTouch')).statistic), 3),
                          meanSim=round(float(np.nanmean(arr('sim_secPerTouch'))), 2),
                          meanReal=round(float(arr('real_secPerTouch').mean()), 2))
res['extraRho'] = {f'sim_first36~{k}': round(float(spearmanr(arr('sim_first36'), arr(k)).statistic), 3)
                   for k in ('real_touch36', 'real_front36', 'real_top36', 'real_elbow36', 'real_post36', 'real_paint36')}
res['extraRho']['sim_recv36~real_front36'] = round(float(spearmanr(arr('sim_recv36'), arr('real_front36')).statistic), 3)
KEEP = ('name', 'group', 'simMin', 'realMin', 'sim_first36', 'sim_recv36', 'sim_touch36', 'real_front36', 'real_touch36',
        'rel_front', 'sim_hold36', 'real_top36', 'rel_hold')


def pick(x):
    return {k: (round(x[k], 3) if isinstance(x[k], float) else x[k]) for k in KEEP}


srt = sorted(rows, key=lambda x: x['logrel_front'])
res['over15_front'] = [pick(x) for x in srt[::-1][:15]]
res['under15_front'] = [pick(x) for x in srt[:15]]
srt_h = sorted(rows, key=lambda x: x['logrel_hold'])
res['over15_hold'] = [pick(x) for x in srt_h[::-1][:15]]
res['under15_hold'] = [pick(x) for x in srt_h[:15]]
SPOT = ['Luka Dončić', 'Shai Gilgeous-Alexander', 'Jalen Brunson', 'Tyrese Haliburton', 'Nikola Jokić', 'Derrick White',
        'Sam Hauser', 'Rudy Gobert', 'Alex Caruso', 'Russell Westbrook', 'Payton Pritchard', 'Jared McCain',
        'Mark Williams', 'Alperen Sengun']
res['spot'] = {}
for nm in SPOT:
    last = nm.split()[-1]
    hit = next((x for x in rows if x['name'] == nm), None) or next(
        (x for x in rows if x['name'].split()[-1][:4] == last[:4] and x['name'][0] == nm[0]), None)
    if hit is None:
        vv = next((r for r in V if r['name'].split()[-1][:4] == last[:4] and r['name'][0] == nm[0]), None)
        inReal = any(nm.split()[-1] in t['PLAYER_NAME'] for t in real.values())
        res['spot'][nm] = 'not in joined population: ' + ('in validation csv, primary=' + vv['tov36_primary'] if vv else 'absent from v41 validation csv') + ('; present' if inReal else '; absent') + ' in 2025-26 tracking'
    else:
        res['spot'][nm] = pick(hit)
(D / 'results.json').write_text(json.dumps(res, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
with open(D / 'allocation.csv', 'w', encoding='utf-8', newline='') as fh:
    w = csv.DictWriter(fh, list(rows[0].keys()))
    w.writeheader()
    for x in sorted(rows, key=lambda x: -x['logrel_front']):
        w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in x.items()})
print(json.dumps({k: res[k] for k in ('nJoined', 'joinLost', 'seedAvgMismatchVsE069off', 'scale', 'tercileCuts',
                                      'perTeamGame', 'secPerTouch', 'extraRho')}, ensure_ascii=False, indent=1))
for k in pairs:
    print(k)
    for g, v in res['metrics'][k].items():
        print(' ', g, v)
for key in ('over15_front', 'under15_front', 'over15_hold', 'under15_hold'):
    print(key)
    for x in res[key]:
        print(' ', x['name'], x['group'], x['sim_touch36'], x['real_front36'], x['rel_front'], x['sim_hold36'], x['real_top36'], x['rel_hold'])
print('spot')
for k, v in res['spot'].items():
    print(' ', k, v)
